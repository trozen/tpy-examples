# TODO

The migration backlog. Public, but it is a working document — the READMEs only ever
list examples that are fully working.

## First batch

Chosen for fidelity: small, deterministic, and importing only modules TurboPython
supports well today.

- [ ] `mandelbrot` — 39 lines, `time`. ASCII fractal, pure arithmetic.
- [ ] `collatz` — 100 lines, `time`. Integer work; candidate for `Int64` vs `int`.
- [ ] `sieve` — 120 lines, `math`, `time`. Shed Skin's own headline benchmark.
- [ ] `voronoi` — 57 lines, `math`, `random`, `time`. Validates that `random` really
      is byte-identical to CPython on the same seed.
- [ ] `dijkstra2` — 110 lines, `heapq` (~92%). Exercises a supported stdlib module
      beyond the builtins.

## Later

- [ ] `doom` — the GUI milestone. Needs an SDL2-backed `pygame` shim (kept local to
      the example at first) plus a separately downloaded `DOOM1.WAD`. A verbatim
      `doom.py` running on native SDL2 is the strongest showcase in the corpus.
- [ ] Check harness: run each example under CPython and `tpy`, normalize timing
      output, diff. Deferred until a few examples exist — it should be shaped by
      real ports, not guessed at. Then wire it into CI.
- [ ] Speedup numbers per example. Deferred until the harness can measure both runs
      systematically on one machine; ad-hoc laptop numbers age badly.
- [ ] Decide whether the `pygame` shim becomes shared repo infrastructure, or moves
      upstream into tpy-lang proper. Revisit at the second GUI example.
- [ ] Original TurboPython examples as a sibling category — starting with writing
      CPython extension modules in TurboPython.

## Blocked on compiler gaps

These need TurboPython work before a faithful port is possible. Each should be
filed against tpy-lang rather than worked around here.

- `life`, `sokoban`, `mastermind2` — need `collections.defaultdict` (Missing;
  needs macros).
- `sudoku5`, `life` — need `itertools` beyond the current ~35% (`chain`, `product`,
  `groupby`).
- `rsync` — needs `hashlib` beyond SHA-256 (currently ~20%).
- `brainfuck` — does `from sys import stdin` and `stdin.read(1)`; `sys.stdin` is
  Missing ("needs read-side protocol"). Was in the first batch until the roadmap was
  checked properly.

## Conventions

See [CLAUDE.md](CLAUDE.md) — porting workflow, hard rules, and the per-example
README template.
