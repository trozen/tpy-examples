# collatz

Finds the Collatz (3x+1) delay records below ten million. ~102 lines.

## Origin

Ported from
[shedskin/examples/collatz](https://github.com/shedskin/shedskin/tree/main/examples/collatz).

Attribution, verbatim from the source header:

> ```
> # copyright mark dufour 2023
> ```

The original states no license.

## Changes from the original

- Annotated the two functions: `step(n: int64, extra: bool = False) -> int64`
  and `main() -> None`.
- **The 64-bit integers are spelled out.** Shed Skin builds this program with
  `--int64`, which makes every integer 64-bit. In TurboPython an unannotated
  integer literal is an `int32`, and an `int32` and an `int64` do not mix in one
  expression: `K - c`, `n >> K` and `steps += ...` are refused when their operands
  differ in width. So the values that meet the collatz numbers are annotated
  `int64`: `N`, `K`, the two lookup tables `lookup_multistep` and `lookup_c`,
  and the `steps` counter of the search loop. Everything else is inferred from
  those.
- `t0` is initialised before the timing loop. The original assigns it only at
  `n == 5`, which the compiler cannot prove is always reached.
- The two formatted lines became f-strings — see below.

The algorithm, the lookup tables, the benchmark harness and the output are the
original's.

## TurboPython bugs worked around

- **No printf-style `%` formatting on `str`.** The `numbers/second` and `TIME`
  lines became f-strings. Tracked in tpy-lang's `TODO.md` ("printf-style `%`
  formatting on `str`").
- **A list the program later rebinds from a comprehension can't start as
  `[0] * n` or `list(range(...))`.** Both tables are rebound in the `for k in
  range(K)` loop, so they start as comprehensions instead:
  `[i for i in range(0, 2**K)]` for `list(range(0, 2**K))`, and
  `[0 for _ in lookup_multistep]` for `[0] * len(lookup_multistep)`.
  Tracked in tpy-lang's `BUGS.md`
  (`prebound-list-rebound-in-loop-from-comprehension`), which covers both seeds.

## Notes

Verified against the unmodified original under CPython: the 541 lines of output
are identical, apart from the `numbers/second` and `TIME` figures, which depend
on elapsed time.

The program searches below ten million ten times — the original's benchmark loop —
printing each record as it is found, and the throughput of each search. The
original's header says its results were checked against the published list at
[ericr.nl/wondrous/delrecs.html](http://www.ericr.nl/wondrous/delrecs.html).
