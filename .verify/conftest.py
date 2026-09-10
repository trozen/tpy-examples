"""Discover the examples and refuse to run without the pinned compiler.

Every example in the gallery is found by walking the tree, so a new port is
verified the moment it lands, with no registration step. The compiler comes
from the `tpy` submodule through this directory's venv (see pyproject.toml);
the tests must never fall through to some other `tpy` on PATH, because then a
green run would say nothing about the version the examples claim to target.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest

VERIFY_DIR = Path(__file__).resolve().parent
REPO_ROOT = VERIFY_DIR.parent
COMPILER_DIR = VERIFY_DIR / "tpy"
EXPECTED_DIR = VERIFY_DIR / "expected"

# Per-example settings live in expected/<id>.json, next to the recording.
# An example with no file is built and run, and its stdout compared. Keys:
#   build_only    string -- why the example is built and linked but not run
#                 (needs a display, hits the network, ...)
#   output_files  {file name: sha256} for files the program writes next to
#                 itself, checked alongside stdout -- oliva2 prints only its
#                 elapsed time, the picture is the point. Write the hash as
#                 null and `make bless` fills it in.
CONFIG_KEYS = {"build_only", "output_files"}

# The originals print their elapsed time; that is the one line that may differ
# between runs (see CLAUDE.md, "Keep timing scaffolding").
_TIME_LINE = re.compile(r"^TIME \d+\.\d+$", re.MULTILINE)


@dataclass(frozen=True)
class Example:
    id: str          # "shedskin/ant", "landing/classes"
    source: Path     # the entry point
    build_only: str | None = None
    output_files: dict[str, str | None] = field(default_factory=dict)

    @property
    def cwd(self) -> Path:
        # Examples are self-contained and read their data files relative to
        # their own directory (CLAUDE.md: "run from inside its own directory").
        return self.source.parent

    @property
    def config(self) -> Path:
        return EXPECTED_DIR / f"{self.id}.json"

    @property
    def expected_stdout(self) -> Path:
        return EXPECTED_DIR / f"{self.id}.txt"

    def record_hashes(self, digests: dict[str, str]) -> None:
        # Rewrite the whole file so other keys survive; it is small and the
        # formatting is deterministic, so the diff is just the hashes.
        config = json.loads(self.config.read_text())
        config["output_files"] = {**self.output_files, **digests}
        self.config.write_text(json.dumps(config, indent=2) + "\n")


def _load(id: str, source: Path) -> Example:
    path = EXPECTED_DIR / f"{id}.json"
    if not path.exists():
        return Example(id, source)
    config = json.loads(path.read_text())
    unknown = set(config) - CONFIG_KEYS
    if unknown:
        raise pytest.UsageError(
            f"{path.relative_to(REPO_ROOT)}: unknown key(s) {sorted(unknown)}; "
            f"known: {sorted(CONFIG_KEYS)}"
        )
    return Example(
        id, source,
        build_only=config.get("build_only"),
        output_files=dict(config.get("output_files", {})),
    )


def discover() -> list[Example]:
    found = []
    for d in sorted((REPO_ROOT / "shedskin").iterdir()):
        entry = d / f"{d.name}.py"
        if entry.exists():
            found.append(_load(f"shedskin/{d.name}", entry))
    for f in sorted((REPO_ROOT / "landing").glob("*.py")):
        found.append(_load(f"landing/{f.stem}", f))
    return found


EXAMPLES = discover()


def normalize(stdout: str) -> str:
    return _TIME_LINE.sub("TIME <elapsed>", stdout)


def tpy(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["tpy", *args], cwd=cwd, capture_output=True, text=True, timeout=600,
    )


def pytest_addoption(parser):
    # `--bless` records only what has no recording yet, so recording a new
    # port cannot silently overwrite another example's drifted output;
    # `--bless=all` re-records everything, for a deliberate compiler bump.
    parser.addoption(
        "--bless", nargs="?", const="missing", default="", choices=["missing", "all"],
        help="record outputs under expected/: missing ones (default), or all",
    )


def pytest_configure(config):
    # Erroring here gives one clear message instead of a wall of failures from
    # tests that cannot do their job. Skipping would be worse: the suite would
    # report success having verified nothing.
    if not (COMPILER_DIR / "pyproject.toml").exists():
        raise pytest.UsageError(
            "the compiler submodule is not checked out -- run "
            "`git submodule update --init .verify/tpy` from the repo root"
        )
    found = shutil.which("tpy")
    if not found or VERIFY_DIR / ".venv" not in Path(found).resolve().parents:
        raise pytest.UsageError(
            f"`tpy` resolves to {found or 'nothing'}, not to this harness's venv "
            "-- run the tests through `make test` or `uv run pytest` in .verify/"
        )
    if not EXAMPLES:
        raise pytest.UsageError("no examples found under shedskin/ or landing/")


@pytest.fixture(scope="session", params=EXAMPLES, ids=[e.id for e in EXAMPLES])
def example(request) -> Example:
    return request.param


@pytest.fixture(scope="session")
def build_root(tmp_path_factory) -> Path:
    # One output tree for the session, shared by the build and run tests of
    # each example: tpy's up-to-date check makes the second invocation a
    # no-op rebuild, so the run test does not pay for the build twice.
    return tmp_path_factory.mktemp("build")


@pytest.fixture
def bless(request) -> str:
    return request.config.getoption("--bless")
