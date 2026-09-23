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
- `collatz` — builds its lookup tables with self-assigning comprehensions
  (`lookup_c = [c + (i%2) for (i, c) in zip(lookup_multistep, lookup_c)]`). That form
  emits invalid C++ (`&*` applied to a value-typed slot), so it cannot be ported
  without restructuring. int64 annotations were otherwise sufficient.
- `minpng` — needs `struct.pack`; only `unpack`/`calcsize` are implemented.
- `brainfuck` — does `from sys import stdin` and `stdin.read(1)`; `sys.stdin` is
  Missing ("needs read-side protocol"). Was in the first batch until the roadmap was
  checked properly.

## To file against tpy-lang

Compiler bugs and gaps found while writing examples, not yet in tpy-lang's
`BUGS.md` or `TODO.md`. Each is worked around in the example named, and listed
in that example's README; file them, then revert the workaround once fixed.

- `chr()` above 127 compiles to `static_cast<char>`, one wrong byte, silently
  (`programs/tte`, decrypt).
- `random._randbelow(1)` returns without drawing, where CPython draws bits;
  `randint(a, a)`, `randrange(1)` and one-element `choice` put the random stream
  out of step with CPython's (`programs/tte`, `rng.randint`).
- A closure returned from a function, built from nested `def`s, captures the
  enclosing parameters by reference: silent use after return
  (`programs/tte`, `easing.CubicBezier`). Returning a callable-class instance
  as a `Callable` is refused (`return.callable_source`).
- A local bound to a `ValueType` record's field is refused
  (`field.result_type`), and so is such a field, or a `copy()` of one, as a call
  argument (`call.ctor_arg.record_f1`, `call.builtin_special`)
  (`programs/tte`, throughout).
- `list.sort(key=)` is missing; `sorted(key=lambda ...)` capturing `self` is
  refused (`lambda.self_capture`) (`programs/tte`, `Terminal.characters`).
- `int(text, 16)` is missing (`programs/tte`, `graphics.hex_color`).
- `random.choice` cannot infer its type argument for a list of records
  (`programs/tte`, `graphics.choose_color`).
- A pointer-form local named `char` is declared `char` and used as `char_`
  (`programs/tte`).
- `argparse` requires `choices=` to be a list literal, its `--help` leaves out
  a positional's `choices`, and `parser.print_help()` is refused inside an `if`
  (`programs/tte`).
- Const inference misses a mutating method call made through a local alias
  of a container element (`c = term.chars[i]; c.move_to(...)`), so the
  parameter is emitted `const` and the C++ build fails (`programs/tte`, print).
- Reading an element of an unannotated module-level list of float literals
  (`X = [0.15, 0.3]`, then `random() < X[i]`) is refused
  (`subscript.elem.other`); annotating it `list[float]` fixes it
  (`programs/tte`, spawn).
- A string local bound to a conditional expression whose arms are a list
  element and a string literal (`x = xs[i] if c else ""`) becomes a
  `std::string_view` of the temporary `std::string` that C++'s `?:` produces:
  a silent dangling view (`programs/tte`, swarm).
- A name first bound inside one `if` branch and reused as a `for` target in a
  sibling branch is emitted without a declaration there (`'x' was not
  declared in this scope`) (`programs/tte`, crumble).
- Subscripting the tuple a method call returns (`xs.pop()[1]`) is refused
  (`method.ret_type`) (`programs/tte`, sandstorm).
- `math.hypot` and `math.dist` fold `std::hypot`, which can differ from
  CPython's correctly rounded result in the last bit
  (`hypot(0.5625, 0.5859375)`). Not worked around: it moves a character on a
  curved path by a cell now and then (`programs/tte`, a draft of sandstorm).
- `own_iter()` over a temporary list still warns about copying elements into
  an `Own` parameter (`programs/tte`, matrix).

## Conventions

See [CLAUDE.md](CLAUDE.md) — porting workflow, hard rules, and the per-example
README template.
