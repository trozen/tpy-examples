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

Examples target **tpy-lang 0.6.0.dev0**, a pre-release at commit `31a87a5651`.
That commit is pinned as the `.verify/tpy` submodule. When it changes, move the
submodule to the new commit and update the version and commit here and in
`README.md` — the Requirements bullet and, on a release, both `pip install`
blocks. `make test` fails while the three disagree.

## Local setup

Porting needs two checkouts. The first is the Shed Skin repository, a local working
copy rather than a dependency of the published examples, so `tmp/` is gitignored
and the path is a convention rather than a guarantee:

```bash
mkdir -p tmp
git clone https://github.com/shedskin/shedskin tmp/shedskin
```

The second is the `tpy-lang` source checkout pinned as the `.verify/tpy` submodule
(`git submodule update --init .verify/tpy`). The verification harness needs it as
the compiler to test against, and the fallback route in step 4 needs its CPython
compatibility stubs in `lib/cpy`, which are not in the released wheel.

If the Shed Skin checkout is missing, stop and ask — do not port from memory or from
a web copy. If the submodule is not checked out you can still port, but you cannot
complete step 7, so the example cannot be published.

## Porting an example

1. Copy the original from `tmp/shedskin/examples/<name>/` into `shedskin/<name>/`,
   along with any data files it reads from `../testdata/`.
2. Fix the data-file paths to be local — each example is self-contained.
3. Get it compiling with `tpy --debug <name>.py` — the unoptimized build is
   quicker to iterate on. See **Fidelity where it doesn't hurt** below for how far to go.
4. Verify the port against the original. This is done once, here, and it is what
   makes the output recorded in step 7 worth anything: the harness can only
   replay what tpy did, it cannot tell a faithful port from a plausible-looking
   wrong one. The two outputs must match line for line: only elapsed-time figures
   may differ, everything else must be byte-identical. Proving that the compiler
   agrees with CPython is not the goal — that is tpy-lang's own test suite's job.

   **Preferred — run the unmodified original under CPython** and compare its
   output with the port's:

   ```bash
   tpy <name>.py
   python3 tmp/shedskin/examples/<name>/<name>.py
   ```

   The Shed Skin originals are plain Python, so this needs nothing beyond the
   Shed Skin checkout, and it tests exactly the claim the gallery makes — that the
   port does what the original does — without any pressure to keep the port
   CPython-runnable.

   **Fallback — run the port itself under CPython.** For programs with no runnable
   original to compare against (the `landing/` files, original examples added
   later). Works only while the port stays ordinary Python plus annotations:

   ```bash
   tpy <name>.py
   PYTHONPATH=$(git rev-parse --show-toplevel)/.verify/tpy/lib/cpy python3 <name>.py
   ```

   The `PYTHONPATH` is required: the program imports `tpy` types, and the CPython
   compatibility stubs in `lib/cpy` are **not** shipped in the `tpy-lang` wheel —
   they exist only in the source checkout (also wrapped by that checkout's
   `run_cpython.sh`). The path is given from the repository root because the
   command runs from inside `landing/` or `shedskin/<name>/`.

   Record in the example's README which route was used. Only when neither is
   possible — a GUI or native-binding example with no comparable output — read the
   ported source against the original line by line instead, and say so in the
   README.
5. Write `shedskin/<name>/README.md` from the template below.
6. List it in `shedskin/README.md` as `| <name> | <one-line description> | <N> |`
   (name, description, line count). If it is the first, create the table there and
   remove the "None are listed yet" sentence.
7. Record its output for the verification harness: `make test` picks the example
   up automatically and fails for want of a recorded output, then `make bless`
   records it. `make bless` touches only examples with no recording, so it cannot
   overwrite another example's output by accident; `make bless-all` re-records
   everything and is for compiler bumps. Bless only after step 4 has passed — the
   recorded output is the verified output. If the example cannot run unattended,
   or writes a file worth checking, say so in `.verify/expected/<category>/<name>.json`
   first (`build_only` with a reason, or `output_files`; see `.verify/conftest.py`).
   See **Verification** below.

## The `landing/` directory

Everything above concerns `shedskin/`. `landing/` holds the short single-file
programs shown in the code window on tpy-lang.org, and its rules are different:
one file per language topic, opening with a one- or two-line comment saying what
it shows, no data files, no arguments, run as `tpy <name>.py`.

**Lines stay under 61 characters** — the width of the code window on the site.
Aim for 57 when editing. The website repository's `verify_examples.py` fails on
any line over 61, so the constraint is enforced there rather than here.

`landing/` is consumed by the website, which means an edit here is not live until
the website repository picks it up: it regenerates `docs/examples.js` with
`build_examples.py` and bumps its submodule pointer at this repository. Which
files appear, in what order, under what label is decided by `ORDER` in that
repository's `build_examples.py` — adding a file here does not put it on the
page. See `landing/README.md`.

## Hard rules

The rules in this section govern `shedskin/`; `landing/` is covered above.

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
runs to completion, and its output matches the original by one of the two routes in step
4 — or, where neither is possible, once it has been verified by inspection. No
placeholders, no "coming soon" rows, no status columns full of failures.

**Forward-referencing annotations only matter for examples that run under CPython.**
TurboPython resolves them regardless. But CPython evaluates class- and module-level
annotations at runtime, so `neighs: list[Rc[Node]]` inside `class Node`, or a global
annotated with a class declared further down, raises `NameError` there. If the
example is verified by running the port itself under CPython (step 4, fallback
route), quote the annotation or add `from __future__ import annotations`. If it is
verified against the unmodified original instead, leave it alone — the import is
noise.

**Never strip original copyright or license notices.** These are third-party
programs under their own terms, and many carry an author line and nothing more —
keep whatever is there, verbatim. See `shedskin/README.md`.

**Entry point is always `<dir>/<dir>.py`**, run from inside its own directory. For
multi-module examples, rename the module containing `main` to `<dir>.py` and leave
the other modules' names alone.

**Keep timing scaffolding.** Most originals print elapsed time; leave it in and
normalize it away when comparing output. Do not delete it.

**Workarounds are temporary and must be labelled.** If a TurboPython bug, or a
missing piece of Python, forces a deviation, list it under **TurboPython bugs
worked around** in the example's README, so it can be reverted when the compiler
is fixed. That section is for anything that stopped the port from using a feature
the original uses; genuine TurboPython idioms (ownership, annotations, `int32`)
stay under **Changes from the original**. Point at the upstream issue if there is
one; tpy-lang tracks bugs in its `BUGS.md` and gaps in its `TODO.md`, so name the
entry there, or say "not filed upstream yet".

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

- **<what could not be used>** — <how the port works around it>. <Tracked in
  tpy-lang's `BUGS.md`/`TODO.md` ("<entry title>") | Not filed upstream yet>;
  revert once fixed.

(Omit this section if there were none.)
```

Add a **Run** section only if the example needs more than `tpy <name>.py` — extra
setup, downloaded assets, a system library. Otherwise the convention in
`README.md` covers it.

The public statement of these rules is the "How these ports are made" section of
`shedskin/README.md`. Keep the two in sync.

## Verification

`.verify/` is the test harness, not an example directory: it builds every example
against the pinned compiler, runs the ones that can run unattended, and compares
their output with what was recorded when the port was verified. `make test` runs
it; `make bless` records outputs. `.verify/README.md` has the details. CPython
parity itself is not automated here — that is tpy-lang's job — which is why
blessing must follow the manual check in step 4.

## Backlog

`TODO.md` holds the migration queue, the deferred infrastructure work, and the
examples blocked on compiler gaps.
