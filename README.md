# TurboPython Examples

A gallery of example programs for [TurboPython](https://tpy-lang.org) (`tpy`) — a
compiler that translates Python to C++.

Each one is a real program someone wrote to get a job done, ported to build and run
with `tpy`. The point is to show what TurboPython does with ordinary code, not to
exercise the compiler with synthetic tests.

## Examples

- [`shedskin/`](shedskin/README.md) — programs ported from the
  [Shed Skin](https://github.com/shedskin/shedskin) project, a Python-to-C++
  compiler with goals close to TurboPython's. Third-party code, mixed licenses.

The first batch is still being ported, so the gallery is small for now. Examples are
added in small batches, and one appears only once it fully works: it compiles, runs
to completion, and matches CPython's output wherever CPython can run it. Examples
still waiting on compiler work are listed in [TODO.md](TODO.md).

More categories will follow, including original TurboPython examples with no Shed
Skin counterpart — starting with CPython extension modules written in TurboPython.

## Requirements

- Linux or macOS
- Python 3.12+
- `tpy-lang` 0.5.1 — the version these examples target
- A C++23 compiler: g++ 13+ or clang++ 19+ — or none, if you use the bundled zig
  toolchain below

```bash
pip install "tpy-lang==0.5.1"          # or: uv tool install "tpy-lang==0.5.1"
```

If you don't have a suitable C++ compiler, install the bundled zig toolchain instead:

```bash
pip install "tpy-lang[bundled]==0.5.1" # or: uv tool install "tpy-lang[bundled]==0.5.1"
```

See [tpy-lang.org](https://tpy-lang.org) for full installation instructions and the
language documentation.

## Running an example

Every example lives in its own directory and is self-contained, including any data
files it reads:

```bash
git clone https://github.com/trozen/tpy-examples
cd tpy-examples/shedskin/<example-name>
tpy -O <example-name>.py
```

`tpy` compiles the program to a native binary and runs it. The entry point is always
`<example-name>.py`. Examples needing extra setup say so in their own README.

Use `-O` to see what TurboPython actually does — it is roughly 3x faster than the
default unoptimized build, which exists for quick edit-run cycles.

Useful flags:

```bash
tpy <example-name>.py             # unoptimized: builds faster, runs slower
tpy --dump-code <example-name>.py # inspect the generated C++
```

### Running under CPython

Sources stay valid Python, so your editor and type checker still understand them.
But a ported example is not a drop-in CPython script: it imports TurboPython types
such as `Int32`, and a few bind native libraries directly, which has no CPython
equivalent.

Both running an example under CPython and resolving its imports for a type checker
need compatibility stubs that currently ship only in a `tpy-lang` source checkout.
So the CPython comparison we run while porting cannot yet be reproduced from a
released package.

## Licensing

**The directory boundary is the license boundary.**

- **`shedskin/`** — third-party programs copied from the Shed Skin project, each
  under its own terms, passed through unchanged. Many carry an author attribution
  and no license statement at all; others are GPL-2, GPL-3, or custom. Provided
  as-is. **Check the individual example before reusing it.** See
  [shedskin/README.md](shedskin/README.md).
- **Everything else** — MIT, see [LICENSE](LICENSE). That covers everything this
  repository authors: the READMEs, any scripts, and original examples added later.
  Copy it freely.
