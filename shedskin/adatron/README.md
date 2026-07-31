# adatron

An Adatron support vector machine with a polynomial kernel, classifying proteins by
subcellular location. ~204 lines.

## Origin

Ported from
[shedskin/examples/adatron](https://github.com/shedskin/shedskin/tree/main/examples/adatron).

Attribution and license, verbatim from the source header:

> ```
> # Adatron SVM with polynomial kernel
> # placed in the public domain by Stavros Korokithakis
> ```

The `testdata/` files are the original's, carried over unchanged.

## Changes from the original

This port needed more than the others in this directory. Every change is listed.

**Annotations** — the bulk of the diff, and the expected cost:

- Signatures on all seven functions and both methods.
- `Protein` gained class-level field declarations. TurboPython stores fields inline
  and has no `__dict__`, so every attribute must be declared.
- Explicit element types where a literal would otherwise pin a narrower type:
  `labels: list[Int32] = [-1] * 4` (otherwise `list[IntLiteral(-1)]`),
  and likewise for `bias`, `labelalphas`, `max_differences`, `alphas`, `betas`,
  `predictions` and `current_predictions`.
- `PROTEINS: "list[Protein]" = []`. The annotation is **quoted deliberately**:
  module-level variable annotations are evaluated at runtime by CPython, and the
  declaration precedes `class Protein`, so an unquoted form raises `NameError`
  under CPython while compiling fine under TurboPython.

**Working around missing language and library features:**

- `for line in protfile:` became `for line in protfile.readlines():` — file objects
  are not iterable yet.
- `name, mass, ... = line.strip().split("\t")` became an indexed tuple. Unpacking
  is supported for tuples, not lists, and `split()` returns a list.
- `sorted(self.local_composition.items())` became `sorted(...keys())` with the value
  looked up in the body — tuples do not satisfy `Comparable`. The next loop in the
  original already uses `sorted(...keys())`, so this matches the file's own idiom,
  and `value` still leaks into that loop exactly as it did before.
- `max(current_predictions)` became `sorted(current_predictions)[-1]` — `max()` has
  only two- and three-argument scalar overloads; there is no iterable form.
- `PROTEINS = []` in `main()` became `PROTEINS.clear()`. Rebinding a non-value-type
  global is rejected; clearing in place is the equivalent.
- `train_adatron` and `calculate_error` gained terminal `return` statements.
  TurboPython requires a return on every path; the original relies on Python's
  implicit `return None`, and both added returns are unreachable.
- `str(...)` around `AMINOACIDS` and `sequence` element access — indexing a `str`
  yields a `Char`, and the composition dictionaries are keyed by `str` so their keys
  can be sorted (`Char` does not satisfy `Comparable`).
- `print("Starting iteration %s..." % iteration)` and the closing `TIME` line became
  f-strings; there is no printf-style `%` formatting on `str`.

The algorithm, control flow, data files and output are the original's — including
the quirk in `create_vector` where the second loop appends the stale `value` from
the first, which is reproduced rather than fixed.

## Notes

Output is byte-identical to CPython.

Two build warnings are expected and correct: `local_composition` and
`global_composition` are assigned in `extract_composition()` rather than directly in
`__init__`, so TurboPython notes they are default-constructed where CPython would
not have created the attributes yet. Since `__init__` calls `extract_composition()`
before anything reads them, behaviour matches.
