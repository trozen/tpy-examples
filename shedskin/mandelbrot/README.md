# mandelbrot

The Mandelbrot set rendered as ASCII art. ~43 lines.

## Origin

Ported from
[shedskin/examples/mandelbrot](https://github.com/shedskin/shedskin/tree/main/examples/mandelbrot).

Attribution, verbatim from the source header:

> ```
> # By Daniel Rosengren, modified
> #   http://www.timestretch.com/FractalBenchmark.html
> ```

The original states no license.

## Changes from the original

- Annotated `mandelbrot()` — `max_iterations: Int32 = 1000`, returning `None`.
- `print('TIME %.2f' % (time.time()-t0))` became an f-string. TurboPython has no
  printf-style `%` formatting on `str`.
- `zi` and `zr` are initialised to `0.0` instead of `0` — see below.

Nothing else changed: the algorithm, the loop structure, the benchmark harness and
the output are the original's.

## TurboPython bugs worked around

- **`zi = 0` / `zr = 0` produced silently wrong results.** These locals are inferred
  as `Int32` from the integer literal, then assigned floats inside the loop. That
  compiles without error or warning, but the values are read back **truncated to
  integers** by the arithmetic in the following iteration. Every one of the 6,084
  points then tested as inside the set, and the program printed a solid block of
  `#`. Initialising them as `0.0` avoids it.

  Minimal reproducer:

  ```python
  z = 0
  for i in range(3):
      sq = z * z      # CPython: 0, 2.25, 9.0   TurboPython: 0, 1, 9
      z = z + 1.5
  ```

  Restore the original `0` once this is fixed.

## Notes

Output is byte-identical to CPython.

The program renders the fractal 200 times — the original's benchmark loop — and
prints the wall-clock time of the last 100 renders. Every render is identical; only
the closing `TIME` line varies between runs.
