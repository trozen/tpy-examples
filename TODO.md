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
- [x] `sieve` — 120 lines, `math`, `time`. Two prime sieves; the extended slice
      assignment that blocked it works now.

## Later

- [x] `path_tracing` — 409 lines, `math`, `random`, `sys`, `time`. Cornell-box path
      tracer; the first port to need runtime polymorphism (`@dynamic` protocol +
      `Box[Material]`).
- [x] `doom` — the GUI milestone. Needs an SDL2-backed `pygame` shim (kept local to
      the example at first) plus a separately downloaded `DOOM1.WAD`. A verbatim
      `doom.py` running on native SDL2 is the strongest showcase in the corpus.
- [x] Check harness — `.verify/`: build every example against the pinned compiler,
      run the runnable ones, compare with recorded outputs. CPython parity stays a
      manual step at port time; automating it belongs in tpy-lang, not here.
- [ ] Wire `make test` into CI once the `tpy-lang` repository is public — until
      then Actions cannot fetch the `.verify/tpy` submodule.
- [ ] Speedup numbers per example. Deferred until the harness can measure both runs
      systematically on one machine; ad-hoc laptop numbers age badly.
- [ ] Decide whether the `pygame` shim becomes shared repo infrastructure, or moves
      upstream into tpy-lang proper. Revisit at the second GUI example.
- [x] Original TurboPython examples as sibling categories: `basics/` (small single
      files), `tplib/` (library walkthroughs) and `programs/` (applications), seeded
      from the tpy-lang checkout's `examples/`.
- [ ] CPython extension modules written in TurboPython, as a `programs/` entry.
- [ ] `programs/tte`: more of TerminalTextEffects' effects, if wanted; the ones
      left are the less showy ones (binarypath, bouncyballs, bubbles,
      colorshift, errorcorrect, middleout, orbittingvolley, overflow, pour,
      rain, random_sequence, scattered, slice, slide, smoke, spray, sweep,
      synthgrid, unstable, waves).

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
- `minpng` — needs `struct.pack`; only `unpack`/`calcsize` are implemented.
- `brainfuck` — does `from sys import stdin` and `stdin.read(1)`; `sys.stdin` is
  Missing ("needs read-side protocol"). Was in the first batch until the roadmap was
  checked properly.

## To file against tpy-lang

Compiler bugs and gaps found while writing examples, not yet in tpy-lang's
`BUGS.md` or `TODO.md`. Each is worked around in the example named, and listed
in that example's README; file them, then revert the workaround once fixed.

Nothing outstanding. collatz's two list gaps went to the tpy-lang release
session on 2026-09-29 and are filed as
`prebound-list-rebound-in-loop-from-comprehension`, together with a proposal to
allow lossless `int32` -> `int64` widening, which would drop most of collatz's
`int64(...)` conversions (recorded on tpy-lang's "Sub-default-int arithmetic"
decision entry). Everything found so far has an upstream entry, named in the
README of the example that works around it. The exception is the list of
smaller code-generator gaps in `programs/tte`'s README, most of which were never
filed one by one.

## Conventions

See [CLAUDE.md](CLAUDE.md) — porting workflow, hard rules, and the per-example
README template.
