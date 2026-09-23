# Verification harness

Not examples. This directory checks that every program in the gallery still
builds and runs against the compiler version the gallery says it targets.

- `tpy/` — the compiler, as a git submodule pinned to that version. The
  submodule commit *is* the pin; `pyproject.toml` installs it into `.venv/`.
- `test_examples.py` — builds every example in every category (the list is
  `CATEGORIES` in `conftest.py`) with `tpy`, runs all but the few that need a
  display, the network or a peer process, and
  compares stdout (elapsed-time lines normalised) and any written files with
  `expected/`.
- `test_version.py` — the pinned version must match what `README.md` and
  `CLAUDE.md` promise.
- `expected/` — recorded outputs, one per runnable example, plus an optional
  `<example>.json` with per-example settings: `build_only` (a reason string;
  the example is built and linked but not run), `args` (command-line
  arguments to run it with, for a program whose bare run only prints its
  usage) and `output_files` (files the program writes, mapped to their sha256;
  write `null` and `make bless` fills it in). See `conftest.py` for the full
  list.

## Running

From the repository root:

```bash
git submodule update --init .verify/tpy   # once; needs access to the repo
make test
```

`make test` needs a system C++ compiler (g++ 13+ or clang++ 19+). The bundled zig
toolchain the root README offers is not installed into this venv, so it does not
cover the harness.

`make bless` records outputs for examples that have none yet, and leaves existing
recordings alone, so recording a new port cannot quietly overwrite another
example's drifted output. Do it only after the example has been checked against
its original (CLAUDE.md, porting step 4): the recorded output is the verified
output, and blessing it from a broken compiler would only lock the breakage in.
`make bless-all` re-records everything; review the diff before committing it.

The recordings were made on x86-64 Linux. The floating-point examples (oliva2,
path_tracing, adatron, ant) may differ in the last digit on another architecture
or with a compiler that contracts multiply-add by default, as clang does on
arm64. A hash or stdout mismatch on such a machine is not on its own evidence of
a regression.

Bumping the compiler is: check out the new tag (or, for a pre-release, the new
commit) in `tpy/`, update the version in `README.md` and `CLAUDE.md`, run
`make test`, and `make bless-all` if outputs legitimately changed.
