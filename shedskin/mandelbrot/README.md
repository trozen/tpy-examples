# mandelbrot

The Mandelbrot set rendered as ASCII art. ~43 lines.

![The Mandelbrot set as this example prints it](mandelbrot.png)

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

- Annotated `mandelbrot()` — `max_iterations: int32 = 1000`, returning `None`.
- `zi` and `zr` are initialised to `0.0` instead of `0`. A TurboPython local
  has one numeric type, and these are assigned floats inside the loop, so
  starting them from an integer literal is a compile error rather than a
  silent widening as in CPython. The same goes for the `t0` placeholder bound
  ahead of the timing loop.
- The `TIME` line is an f-string — see below.

Nothing else changed: the algorithm, the loop structure, the benchmark harness and
the output are the original's.

## TurboPython bugs worked around

- **No printf-style `%` formatting on `str`.** `print('TIME %.2f' %
  (time.time()-t0))` became an f-string. Tracked in tpy-lang's `TODO.md`
  ("printf-style `%` formatting on `str`").

## Notes

Output is byte-identical to CPython.

The program renders the fractal 200 times — the original's benchmark loop — and
prints the wall-clock time of the last 100 renders. Every render is identical; only
the closing `TIME` line varies between runs.
