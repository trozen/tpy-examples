"""The pinned compiler and the version the docs promise must agree.

CLAUDE.md lists the places to update on a version bump; this makes forgetting
one a failing test rather than a stale README.
"""
from __future__ import annotations

import re

from conftest import REPO_ROOT, tpy

# `pip install "tpy-lang==0.5.1"`, `"tpy-lang[bundled]==0.5.1"`, ...
_INSTALL_PIN = re.compile(r"tpy-lang(?:\[\w+\])?==(\S+?)\"")


def pinned_version() -> str:
    r = tpy(["--version"], cwd=REPO_ROOT)
    m = re.fullmatch(r"tpy (\S+) \((\S+)\)\n?", r.stdout)
    assert m, f"unexpected `tpy --version` output: {r.stdout!r}"
    version, describe = m.groups()
    # The submodule must sit exactly on the release tag: a commit past it, or
    # a dirty tree, would still report the release number while the recorded
    # outputs came from something else.
    assert describe == f"v{version}", (
        f"the .verify/tpy submodule is at {describe}, not on the v{version} tag"
    )
    return version


def test_readme_matches_pinned_compiler():
    v = pinned_version()
    readme = (REPO_ROOT / "README.md").read_text()
    assert f"`tpy-lang` {v} " in readme, "the Requirements bullet in README.md"
    installs = _INSTALL_PIN.findall(readme)
    assert installs, "no `pip install \"tpy-lang==...\"` line in README.md"
    assert set(installs) == {v}, f"README.md install lines pin {sorted(set(installs))}"


def test_claude_md_matches_pinned_compiler():
    v = pinned_version()
    text = (REPO_ROOT / "CLAUDE.md").read_text()
    assert f"Examples target **tpy-lang {v}**" in text
