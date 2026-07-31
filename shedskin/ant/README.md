# ant

Ant Colony Optimization applied to the Travelling Salesman Problem. Ants walk the
city graph choosing paths with probability inversely proportional to distance,
deposit pheromone along the best tour found so far, and the pheromone evaporates
over time so later ants are drawn towards good routes without being trapped by
them. ~175 lines.

## Origin

Ported from
[shedskin/examples/ant](https://github.com/shedskin/shedskin/tree/main/examples/ant).

Attribution, verbatim from the source header:

> ```
> # ant.py
> # Eric Rollins 2008
> ```

The original states no license.

## Changes from the original

- **Signatures annotated** on all nine functions, plus element types on the two
  empty-list locals (`m`, `bestPath`) where the literal alone gives nothing to
  infer from.

- **`randomMatrix` fills each row before appending it.** The original appends `sm`
  to `m` and *then* fills it, relying on CPython aliasing the same list object.
  TurboPython containers own what they store, so appending first would store an
  empty row. Filling first is equivalent under both runtimes.

- **`wrappedPath` builds the rotated list directly** instead of `path[1:] +
  [path[0]]`. A slice is a non-owning `Span` in TurboPython and cannot be
  concatenated.

- **`bestPath = copy(path)`** rather than a bare assignment. The loop rebinds
  `path` on the next iteration, so the best-so-far needs its own storage;
  TurboPython requires that to be explicit. CPython aliases here, to the same
  effect.

- **`pathLength` spells out Neumaier compensated summation** instead of calling
  `sum()`. See below — this one is not cosmetic.

## TurboPython bugs worked around

- **`sum()` over floats does not match CPython.** CPython's `sum()` has used
  Neumaier compensated summation for floats since 3.12; TurboPython's accumulates
  naively. On this program the two differ by one ULP:

  ```
  CPython sum(vals) : 178.84921988630578
  naive accumulation: 178.84921988630575
  ```

  That is not a rounding curiosity here. The search keeps a tour when
  `pathLen > bestLen`, so a one-ULP difference flips the comparison, a different
  tour is retained, and the divergence compounds — 124 of 400 output lines
  differed, including completely different tours. Writing the compensated sum out
  by hand restores exact agreement.

  Revert to `sum()` once TurboPython's matches CPython.

## Notes

Output is byte-identical to CPython across all 200 runs, verified against the
unmodified upstream program.

The program solves the same 20-city problem 200 times with different ant seeds and
prints each tour and its length; the city distances themselves are fixed
(`cityDistanceSeed = 1`), so every run explores the same map.
