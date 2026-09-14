# sieve

Two prime sieves, Atkin's and Eratosthenes', each counting the primes below
ten million, ten times over. ~120 lines.

## Origin

Ported from
[shedskin/examples/sieve](https://github.com/shedskin/shedskin/tree/main/examples/sieve).

Attribution, verbatim from the source (there is no file header; each function
carries its own):

> ```
> # Code by Steve Krenzel, <Sgk284@gmail.com>, improved
> # Code: http://krenzel.info/?p=83
> # Info: http://en.wikipedia.org/wiki/Sieve_of_Atkin
> ```
>
> ```
> # Code from: <dickinsm@gmail.com>, Nov 30 2006
> # http://groups.google.com/group/comp.lang.python/msg/f1f10ced88c68c2d
> ```

The original states no license.

## Changes from the original

- **Both sieves return `Own[list[int]]`.** Each builds the list it returns, and
  TurboPython requires that transfer of ownership to be spelled out.
- **`primes: list[int] = [2, 3]`.** Without the annotation the literal would
  pin the element type to `int32`; the sieve works in `int`.
- **`return list(primes[:max(0, end - 2)])`** in the small-`end` early exit. A
  slice is a non-owning `Span`, so returning it as a list takes an explicit
  copy. The original returns the slice.
- **`int(0)`, `int(4)` in `x_max, x2, xd = int(sqrt((end-1)/4.0)), int(0),
  int(4)`** — see below.
- **The three `%`-formatted time lines are f-strings** — see below.

The sieves themselves are untouched, including the extended slice assignment
`sieve[bottom::si] = [0] * ...` inside `for si in sieve`, which mutates the
list being iterated. It never changes the list's length, so the iteration is
sound, and the compiler's warning about it is expected (see Notes).

## TurboPython bugs worked around

- **A literal-seeded local is not widened at a `for` rebind.** With the
  original `x2, xd = 0, 4` the two locals take the default `int32`, and the
  later `for xd in range(4, 8 * x_max + 2, 8)`, whose elements are `int`
  because `x_max` is, is rejected: `for-loop rebinds existing variable 'xd'
  of type 'int32' with elements of type 'int'`. The compiler retroactively
  widens such locals at most other kinds of use, but not at a loop rebind.
  Wrapping the literals in `int(...)` pins the type up front. Not filed
  upstream yet; restore the bare literals once fixed.
- **No printf-style `%` formatting on `str`.** The `time:` and `TIME` lines
  became f-strings. Tracked in tpy-lang's `TODO.md` ("printf-style `%`
  formatting on `str`").

## Notes

Output is byte-identical to the original's, verified by running the unmodified
upstream program under CPython: both count 664,579 primes in every run. Only
the `time:` and `TIME` lines differ, and the harness normalises both.

One build warning is expected: `Mutation of 'sieve' while borrowed (slice
assignment may invalidate references)` at the extended slice assignment in
`sieveOfEratostenes`. Reassigning a slice of a list while iterating it would be
unsafe if it reallocated; an extended slice assignment of equal length never
does, which is why the original is correct and the port keeps it.
