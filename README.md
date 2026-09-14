# TurboPython Examples

A gallery of example programs for [TurboPython](https://tpy-lang.org) (`tpy`) — a
compiler that translates Python to C++.

Most are real programs someone wrote to get a job done, ported to build and run with
`tpy`; the rest are written here, to show one part of the language or library at a
time or as applications of their own. The point is to show what TurboPython does with
ordinary code, not to exercise the compiler with synthetic tests.

## Examples

- [`shedskin/`](shedskin/README.md) — programs ported from the
  [Shed Skin](https://github.com/shedskin/shedskin) project, a Python-to-C++
  compiler with goals close to TurboPython's. Third-party code, mixed licenses.
- [`landing/`](landing/README.md) — the short single-file programs shown in the
  code window on [tpy-lang.org](https://tpy-lang.org), each demonstrating one
  part of the language. Written for this project, MIT.
- [`basics/`](basics/README.md) — small single-file programs to run first: hello,
  a Brainfuck interpreter, Game of Life, an ASCII Mandelbrot. MIT.
- [`tplib/`](tplib/README.md) — walkthroughs of the library, one type or module
  per file: the `tplib` containers, sockets and asyncio. MIT.
- [`programs/`](programs/README.md) — original applications with a command line
  and a job to do, one directory each, starting with a curl-like HTTP client. MIT.

The gallery is still small. Examples are added in small batches, and one appears
only once it fully works: it compiles, runs to completion, and matches CPython's
output wherever CPython can run it. Examples still waiting on compiler work are
listed in [TODO.md](TODO.md).

## Requirements

- Linux or macOS
- Python 3.12+
- `tpy-lang` 0.6.0.dev0 — a pre-release; these examples target commit
  `31a87a5651` of the tpy-lang repository, checked out as the `.verify/tpy`
  submodule
- A C++23 compiler: g++ 13+ or clang++ 19+ — or none, if you use the bundled zig
  toolchain below

The pre-release is not on PyPI, so install it from the submodule:

```bash
git submodule update --init .verify/tpy
pip install .verify/tpy                # or: uv tool install .verify/tpy
```

If you don't have a suitable C++ compiler, install the bundled zig toolchain instead:

```bash
pip install ".verify/tpy[bundled]"     # or: uv tool install ".verify/tpy[bundled]"
```

See [tpy-lang.org](https://tpy-lang.org) for full installation instructions and the
language documentation.

## Running an example

Every ported example lives in its own directory and is self-contained, including any
data files it reads:

```bash
git clone https://github.com/trozen/tpy-examples
cd tpy-examples/shedskin/<example-name>
tpy <example-name>.py
```

`tpy` compiles the program to a native binary and runs it. The entry point is always
`<example-name>.py`, and `programs/` follows the same layout. Examples needing extra
setup say so in their own README. `landing/`, `basics/` and `tplib/` hold single
files rather than directories, run the same way from inside their directory.

The build is optimized by default. Useful flags:

```bash
tpy --debug <example-name>.py     # unoptimized, with debug info: builds faster
tpy --dump-code <example-name>.py # inspect the generated C++
```

### Running under CPython

Sources stay valid Python, so your editor and type checker still understand them.
But a ported example is not a drop-in CPython script: it imports TurboPython types
such as `int32`, and a few bind native libraries directly, which has no CPython
equivalent.

Both running an example under CPython and resolving its imports for a type checker
need compatibility stubs that currently ship only in a `tpy-lang` source checkout.
So the CPython comparison we run while porting cannot yet be reproduced from a
released package.

### Verifying the examples

`.verify/` is not an example directory. It holds the checks that keep the gallery
honest: every example is built against the pinned compiler, the ones that can run
unattended are run, and their output is compared with what was recorded when the
port was verified. `make test` runs it; see [.verify/README.md](.verify/README.md).

## Gallery

[<img src="shedskin/doom/doom.png" alt="DOOM's E1M1 rendered by the doom example" height="300">](shedskin/doom/)

E1M1, drawn by [`doom`](shedskin/doom/): a software BSP renderer in annotated
Python, on SDL2 through TurboPython's native bindings.

[<img src="shedskin/path_tracing/path_tracing.png" alt="A Cornell box rendered by the path_tracing example" height="300">](shedskin/path_tracing/)

A Cornell box, drawn by [`path_tracing`](shedskin/path_tracing/): a Monte Carlo
path tracer at ten thousand samples per pixel, with the material types
dispatching through a `@dynamic` protocol.

## Licensing

**The directory boundary is the license boundary.**

- **`shedskin/`** — third-party programs copied from the Shed Skin project, each
  under its own terms, passed through unchanged. Many carry an author attribution
  and no license statement at all; others are GPL-2, GPL-3, or custom. Provided
  as-is. **Check the individual example before reusing it.** See
  [shedskin/README.md](shedskin/README.md).
- **Everything else** — MIT, see [LICENSE](LICENSE). That covers everything this
  repository authors: the original examples in `landing/`, `basics/`, `tplib/` and
  `programs/`, the READMEs, and the harness. Copy it freely.
