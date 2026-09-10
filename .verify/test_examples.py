"""Build every example against the pinned compiler, and run the ones that can
run, comparing what they print (and write) with the recorded outputs.

`tpy -O` is used because that is how the READMEs tell people to run the
examples. A failure prints the tail of the compiler's or the program's stderr,
or the first line that differs from the recording.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from conftest import REPO_ROOT, Example, normalize, tpy

_BLESS_HINT = "verify the example against its original (CLAUDE.md, step 4), then `make bless`"


def _tail(text: str, n: int = 30) -> str:
    return "\n".join(text.strip().splitlines()[-n:]) or "(no stderr)"


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _first_difference(actual: str, expected: str) -> str | None:
    # Reported by hand rather than left to pytest's assertion diff: on the
    # 15k-line mandelbrot recording the built-in ndiff takes minutes, which
    # makes a real regression look like a hang.
    a, e = actual.splitlines(), expected.splitlines()
    for i, (x, y) in enumerate(zip(a, e), 1):
        if x != y:
            return f"line {i} differs:\n  expected: {y!r}\n  actual:   {x!r}"
    if len(a) != len(e):
        return f"{len(e)} lines recorded, {len(a)} produced"
    return None


def _record(path: Path, text: str, bless: str) -> bool:
    """Write the recording if blessing allows it; True if it was written."""
    if bless == "all" or (bless == "missing" and not path.exists()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return True
    return False


def test_build(example: Example, build_root):
    r = tpy(["-b", "-O", "-o", str(build_root / example.id), example.source.name],
            cwd=example.cwd)
    assert r.returncode == 0, f"build failed:\n{_tail(r.stderr)}"


def test_run(example: Example, build_root, bless):
    if example.build_only:
        pytest.skip(f"build only: {example.build_only}")
    for name in example.output_files:
        (example.cwd / name).unlink(missing_ok=True)

    r = tpy(["-O", "-o", str(build_root / example.id), example.source.name],
            cwd=example.cwd)
    assert r.returncode == 0, f"exited with {r.returncode}:\n{_tail(r.stderr)}"

    actual = normalize(r.stdout)
    for name in example.output_files:
        assert (example.cwd / name).exists(), (
            f"{name} is listed in {_rel(example.config)} but the program did not write it"
        )
    digests = {name: hashlib.sha256((example.cwd / name).read_bytes()).hexdigest()
               for name in example.output_files}

    if _record(example.expected_stdout, actual, bless):
        pass
    elif not example.expected_stdout.exists():
        pytest.fail(f"no recorded output at {_rel(example.expected_stdout)} -- {_BLESS_HINT}")
    else:
        diff = _first_difference(actual, example.expected_stdout.read_text())
        if diff:
            pytest.fail(f"stdout differs from {_rel(example.expected_stdout)}: {diff}")

    to_record = {name: d for name, d in digests.items()
                 if bless == "all" or (bless == "missing" and example.output_files[name] is None)}
    if to_record:
        example.record_hashes(to_record)
    for name, digest in digests.items():
        if name in to_record:
            continue
        recorded = example.output_files[name]
        if recorded is None:
            pytest.fail(f"no recorded hash for {name} in {_rel(example.config)} -- {_BLESS_HINT}")
        if digest != recorded:
            pytest.fail(f"{name} differs from the hash recorded in {_rel(example.config)}")
