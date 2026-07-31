# tpy-examples

A curated gallery of example programs for [TurboPython](https://tpy-lang.org),
linked from the project website. The current work is porting programs from the
Shed Skin examples collection into `shedskin/`.

This is a **showcase**, not a test suite. tpy-lang has its own test suite; nothing
here exists to exercise the compiler. Everything published here works.

## TurboPython documentation

When writing or modifying `.py` files compiled by tpy:

- Start with `docs/TPY_FOR_AGENTS.md` — concise bootstrap covering the delta from
  regular Python, ownership rules, and idiomatic patterns. Read this before writing
  any TurboPython code.
- Consult `docs/TPY_LANGUAGE_FEATURES.md` for depth on specific features. Do not use
  a feature whose section is not marked **Working**.
- Check `docs/TPY_STDLIB_ROADMAP.md` before using a stdlib module — coverage is
  partial and some modules are missing or blocked. **This decides whether an
  example can be ported at all** (see the fidelity rule below).
- Before calling an API you have not already used in this repo, confirm its
  signature in `docs/TPY_API_REFERENCE.md`. Do not infer signatures from CPython.

`docs/` is generated and gitignored. If it is missing, or its version does not match
`tpy --version`, run:

```bash
tpy --install-agent-docs docs/
```

Examples target **tpy-lang 0.5.1**. When that changes, update it here and in
`README.md` — the Requirements bullet and both `pip install` blocks.

## Local setup

Porting needs two checkouts that are not part of this repository. They are local
working copies, not dependencies of the published examples, so `tmp/` is gitignored
and every path below is a convention rather than a guarantee:

```bash
mkdir -p tmp
git clone https://github.com/shedskin/shedskin tmp/shedskin
```

The second is a `tpy-lang` source checkout, needed only for the CPython
compatibility stubs in `lib/cpy` (they are not in the released wheel). Clone it to
`tmp/tpy-lang`, which is what the commands below assume.

If the Shed Skin checkout is missing, stop and ask — do not port from memory or from
a web copy. If the `tpy-lang` checkout is missing you can still port, but you cannot
complete step 4, so the example cannot be published.

## Porting an example

1. Copy the original from `tmp/shedskin/examples/<name>/` into `shedskin/<name>/`,
   along with any data files it reads from `../testdata/`.
2. Fix the data-file paths to be local — each example is self-contained.
3. Get it compiling with `tpy <name>.py` — the unoptimized build is quicker to
   iterate on. See **Fidelity where it doesn't hurt** below for how far to go.
4. Verify the output against CPython. Whichever route applies, the two outputs must
   match line for line: only elapsed-time figures may differ, everything else must
   be byte-identical.

   **Preferred — run the port itself under CPython.** Works when the port stays
   ordinary Python plus annotations:

   ```bash
   tpy -O <name>.py
   PYTHONPATH=tmp/tpy-lang/lib/cpy python3 <name>.py
   ```

   The `PYTHONPATH` is required: a ported example imports `tpy` types, and the
   CPython compatibility stubs in `lib/cpy` are **not** shipped in the `tpy-lang`
   wheel — they exist only in a source checkout (also wrapped by that checkout's
   `run_cpython.sh`).

   **Otherwise — run the unmodified original under CPython** and compare against
   it. Use this when the port uses constructs CPython cannot execute (`Rc`/`Ptr`
   auto-deref, native bindings) or when keeping it CPython-runnable would mean
   contorting the code:

   ```bash
   tpy -O <name>.py
   python3 tmp/shedskin/examples/<name>/<name>.py
   ```

   The Shed Skin originals are plain Python, so this keeps full output parity
   without forcing the port to be dual-target. Record in the example's README which
   route was used.

   Only when neither is possible — a GUI or native-binding example with no
   comparable output — read the ported source against the original line by line
   instead, and say so in the README.
5. Write `shedskin/<name>/README.md` from the template below.
6. List it in `shedskin/README.md` as `| <name> | <one-line description> | <N> |`
   (name, description, line count). If it is the first, create the table there and
   remove the "None are listed yet" sentence.

## Hard rules

**Fidelity where it doesn't hurt.** Prefer the original wording when the cost is an
annotation or a small equivalent substitution — that is the common case, and it is
the strongest thing the gallery can show. But fidelity is a preference, not a
constraint. Where TurboPython genuinely wants a different construction — shared
ownership through `Rc`/`Ptr`, an explicit loop where a missing builtin would
otherwise force a contortion — write the TurboPython version and **explain it in the
README**. Showing how a program is expressed in TurboPython is the point; proving
nothing changed is not.

What to avoid is the third path: a hybrid that is neither the original nor idiomatic
TurboPython, adopted only to dodge a compiler bug or to keep the file runnable under
CPython. Prefer a clean TurboPython example over a hacky dual-target one. If the only
way forward is contortion, defer the example instead and record the gap in `TODO.md`
so it can be filed against tpy-lang.

**Only fully working examples get published.** An example lands once it compiles,
runs to completion, and its output matches CPython by one of the two routes in step
4 — or, where neither is possible, once it has been verified by inspection. No
placeholders, no "coming soon" rows, no status columns full of failures.

**Forward-referencing annotations only matter for examples that run under CPython.**
TurboPython resolves them regardless. But CPython evaluates class- and module-level
annotations at runtime, so `neighs: list[Rc[Node]]` inside `class Node`, or a global
annotated with a class declared further down, raises `NameError` there. If the
example is verified by running the port itself under CPython (step 4, first route),
quote the annotation or add `from __future__ import annotations`. If it is verified
against the unmodified original instead, leave it alone — the import is noise.

**Never strip original copyright or license notices.** These are third-party
programs under their own terms, and many carry an author line and nothing more —
keep whatever is there, verbatim. See `shedskin/README.md`.

**Entry point is always `<dir>/<dir>.py`**, run from inside its own directory. For
multi-module examples, rename the module containing `main` to `<dir>.py` and leave
the other modules' names alone.

**Keep timing scaffolding.** Most originals print elapsed time; leave it in and
normalize it away when comparing output. Do not delete it.

**Workarounds are temporary and must be labelled.** If a TurboPython bug forces a
deviation, say so in the example's README with a link to the upstream issue, so it
can be reverted when the compiler is fixed.

**Never put speedup or benchmark numbers in a README.** The rationale, and the plan
for lifting this, are in `TODO.md`.

## Per-example README template

```markdown
# <name>

<One-line description.> ~<N> lines.

## Origin

Ported from [shedskin/examples/<name>](https://github.com/shedskin/shedskin/tree/main/examples/<name>).

Attribution and license, verbatim from the source header:

> <copyright / license notice as found — often an author line and nothing more;
> if there is no license statement, say so explicitly rather than leaving it out>

## Changes from the original

- <every deviation, including annotations added. Where a TurboPython idiom
  replaced a Python one, explain what it does and why — this section is the
  example's teaching material, not an apology.>

## TurboPython bugs worked around

- <deviation> — <upstream issue link>, revert once fixed.

(Omit this section if there were none.)
```

Add a **Run** section only if the example needs more than `tpy -O <name>.py` — extra
setup, downloaded assets, a system library. Otherwise the convention in
`README.md` covers it.

The public statement of these rules is the "How these ports are made" section of
`shedskin/README.md`. Keep the two in sync.

## Backlog

`TODO.md` holds the migration queue, the deferred infrastructure work, and the
examples blocked on compiler gaps.
