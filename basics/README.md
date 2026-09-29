# basics

Small original programs, each a single file, written for TurboPython rather than
ported. They are the first thing to run after installing `tpy`: nothing to
download, nothing to configure, output in a second or two.

| file | what it is | lines |
| ---- | ---------- | ----- |
| `hello.py` | prints a greeting and the compiler version | 6 |
| `brainfuck.py` | a Brainfuck interpreter running five embedded programs, including *99 Bottles of Beer* | 115 |
| `game_of_life.py` | Conway's Game of Life stepping a glider across a 10×8 grid | 79 |
| `mandelbrot.py` | the Mandelbrot set as ASCII art with a logarithmic character ramp | 47 |

Unlike `landing/`, these are not bound by the website's line-width limit, and
unlike `shedskin/` they have no original to stay faithful to: they are written
the way one would write them for TurboPython in the first place, which mostly
means plain Python with a few annotations.

## Running them

```bash
cd basics
tpy game_of_life.py
```

Each runs as `tpy <name>.py` with no arguments and no data files.

## Verification

Each one is run under CPython as well, with the compatibility stubs from a
`tpy-lang` source checkout on the path (see the porting notes in
[CLAUDE.md](../CLAUDE.md), the fallback route), and the two outputs must match.
`hello.py` prints the compiler version, so its recorded output changes on every
compiler bump; `mandelbrot.py` prints its elapsed time, which the harness
normalises.

## Licensing

MIT, along with the rest of this repository outside `shedskin/` — see
[LICENSE](../LICENSE).
