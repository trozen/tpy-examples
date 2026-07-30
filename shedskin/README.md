# Shed Skin examples, ported to TurboPython

Programs from the [Shed Skin](https://github.com/shedskin/shedskin) project's
[examples collection](https://github.com/shedskin/shedskin/tree/main/examples),
ported to compile and run with [TurboPython](https://tpy-lang.org).

Shed Skin does something genuinely hard: whole-program type inference over
*unannotated* Python. For close to two decades it has been showing that ordinary
Python programs can compile into fast native code, and it was a direct inspiration
for TurboPython — this collection especially, being 80+ non-trivial, self-contained
programs that people wrote to get something done, which is a far better test of a
compiler than any amount of synthetic code.

Ports are taken from upstream revision
[`690673b0`](https://github.com/shedskin/shedskin/tree/690673b0/examples)
(`v0.9.12-412-g690673b0`).

> ⚠️ These programs are **not ours**, and the repository's MIT license does not
> cover them. See [Licensing](#licensing) before reusing any of it.

## Running

```bash
cd <example-name>
tpy <example-name>.py
```

The entry point is always `<example-name>.py`. Examples needing extra setup say so
in their own README. See the [repository README](../README.md#running-an-example)
for requirements and build flags.

## Examples

Examples are added in small batches, and appear here only once they fully work.
None are listed yet — the first batch is in progress.

---

## Licensing

These programs are not ours. Each carries its own terms, and they are not
consistent: many have an author attribution and no license statement at all, and the
rest are a mix of GPL-2, GPL-3, and custom notices. We pass each one through
unchanged, exactly as Shed Skin distributes it — we add no license of our own, and
each program reaches you under whatever terms it already carried. Provided **as-is,
with no warranty**. The repository's MIT license does **not** apply to anything in
this directory.

Before you reuse any of this code, check that example's source header and its
README, and satisfy yourself about its terms. Note that for many of them there is no
license statement to check.

If you are the author of one of these programs and want it removed or corrected,
please open an issue.

Every ported file keeps the original's copyright and license notice intact, such as
it is, and each example's README records both its origin and what we changed.

## How these ports are made

The goal is to stay **as close to the original as possible**. In practice that
means adding type annotations, occasionally picking a fixed-width integer type, and
little else. Where more than that was needed, the example's README says exactly
what changed and why.

Specifically, each example's README documents:

- **Origin** — the upstream path, author, and license notice, verbatim from the
  source.
- **Changes from the original** — every deviation, including annotations added.
- **TurboPython bugs worked around** — with a link to the upstream issue, if any.
  These are meant to be temporary; when the compiler is fixed, the workaround goes.

Nondeterministic output, such as elapsed-time reports, is normalized away before
comparing against CPython — never removed from the program.

Ports that would require restructuring the original are deliberately not done, which
usually means TurboPython is still missing a library or language feature. Those gaps
get filed against the compiler instead, and the example waits for it to catch up.
