# TODO

The migration backlog. Public, but it is a working document — the READMEs only ever
list examples that are fully working.

## First batch

Chosen for fidelity: small, deterministic, and importing only modules TurboPython
supports well today.

- [x] `mandelbrot` — 39 lines, `time`. ASCII fractal, pure arithmetic.
- [x] `voronoi` — 57 lines, `math`, `random`, `time`. Validates that `random` really
      is byte-identical to CPython on the same seed.
- [x] `adatron` — 178 lines, `math`, `time`. Numeric SVM; public domain.
- [x] `oliva2` — 147 lines, `random`, `time`. Reaction-diffusion sea-shell
      patterns; writes a PGM image.
- [ ] `dijkstra2` — blocked, see below. Preserved on `wip/dijkstra2`.
- [ ] `rubik2` — blocked, see below. Preserved on `wip/rubik2`.
- [x] `ant` — 147 lines, `random`, `time`. Ant Colony Optimization for TSP.
- [ ] `sieve` — see note below.

## Later

- [x] `path_tracing` — 409 lines, `math`, `random`, `sys`, `time`. Cornell-box path
      tracer; the first port to need runtime polymorphism (`@dynamic` protocol +
      `Box[Material]`).
- [x] `doom` — the GUI milestone. Needs an SDL2-backed `pygame` shim (kept local to
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

These need TurboPython work before a port is possible at all. Gaps that only change
*how* a program is written -- an idiom that has a TurboPython equivalent -- are no
longer blockers; see the fidelity policy in CLAUDE.md. Each of these should be filed
against tpy-lang.

- `life`, `sokoban`, `mastermind2` — need `collections.defaultdict` (Missing;
  needs macros).
- `sudoku5`, `life` — need `itertools` beyond the current ~35% (`chain`, `product`,
  `groupby`).
- `rsync` — needs `hashlib` beyond SHA-256 (currently ~20%).
- `othello`, `othello2` — need `sys.stdin` and `input()` for their interactive
  and UGI modes. Unreachable branches still have to typecheck.
- `collatz` — builds its lookup tables with self-assigning comprehensions
  (`lookup_c = [c + (i%2) for (i, c) in zip(lookup_multistep, lookup_c)]`). That form
  emits invalid C++ (`&*` applied to a value-typed slot), so it cannot be ported
  without restructuring. Int64 annotations were otherwise sufficient.
- `sieve` — uses extended slice assignment (`sieve[bottom::si] = ...`) and mutates
  the list it is iterating; also assigns `n` inside a loop then reuses it as a
  function-level loop variable.
- `minpng` — needs `struct.pack`; only `unpack`/`calcsize` are implemented.
- `brainfuck` — does `from sys import stdin` and `stdin.read(1)`; `sys.stdin` is
  Missing ("needs read-side protocol"). Was in the first batch until the roadmap was
  checked properly.

## Conventions

See [CLAUDE.md](CLAUDE.md) — porting workflow, hard rules, and the per-example
README template.
