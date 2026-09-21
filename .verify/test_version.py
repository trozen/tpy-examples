"""The pinned compiler and the version the docs promise must agree.

CLAUDE.md lists the places to update on a version bump; this makes forgetting
one a failing test rather than a stale README.

A release pins a tag and the docs name a PyPI version. A pre-release (a
`.devN` version) pins a commit instead, and the docs install from the submodule
because the pre-release is not on PyPI. They do not name the commit: the
submodule pointer already records it, and every version string is shared by
many pre-release commits anyway.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from conftest import REPO_ROOT, tpy

# `pip install "tpy-lang==0.5.1"`, `"tpy-lang[bundled]==0.5.1"`, ...
_INSTALL_PIN = re.compile(r"tpy-lang(?:\[\w+\])?==(\S+?)\"")
# `pip install .verify/tpy`, `".verify/tpy[bundled]"`, ...
_INSTALL_SUBMODULE = re.compile(r"pip install \"?\.verify/tpy")


@dataclass(frozen=True)
class Pin:
    version: str

    @property
    def prerelease(self) -> bool:
        return ".dev" in self.version


def pinned() -> Pin:
    r = tpy(["--version"], cwd=REPO_ROOT)
    m = re.fullmatch(r"tpy (\S+) \((\S+)\)\n?", r.stdout)
    assert m, f"unexpected `tpy --version` output: {r.stdout!r}"
    version, describe = m.groups()
    assert not describe.endswith("-dirty"), (
        "the .verify/tpy submodule has local changes; the recorded outputs "
        "would not come from the pinned commit"
    )
    if ".dev" not in version:
        # The submodule must sit exactly on the release tag: a commit past it
        # would still report the release number while the recorded outputs
        # came from something else.
        assert describe == f"v{version}", (
            f"the .verify/tpy submodule is at {describe}, not on the v{version} tag"
        )
    return Pin(version)


def test_readme_matches_pinned_compiler():
    pin = pinned()
    readme = (REPO_ROOT / "README.md").read_text()
    assert f"`tpy-lang` {pin.version} " in readme, "the Requirements bullet in README.md"
    installs = _INSTALL_PIN.findall(readme)
    if pin.prerelease:
        assert not installs, f"README.md pins a PyPI version {installs} for a pre-release"
        assert _INSTALL_SUBMODULE.search(readme), "no `pip install .verify/tpy` line in README.md"
    else:
        assert installs, "no `pip install \"tpy-lang==...\"` line in README.md"
        assert set(installs) == {pin.version}, f"README.md install lines pin {sorted(set(installs))}"


def test_claude_md_matches_pinned_compiler():
    pin = pinned()
    text = (REPO_ROOT / "CLAUDE.md").read_text()
    assert f"Examples target **tpy-lang {pin.version}**" in text
