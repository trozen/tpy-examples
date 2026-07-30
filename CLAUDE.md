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
3. Add type annotations, and a fixed-width integer type where one is genuinely
   needed, until it compiles: `tpy <name>.py`. Change nothing else. If it will not
   compile without restructuring the program, stop and defer the example — see
   **Fidelity gates what gets ported** below.
4. Verify it matches CPython — the two must produce the same output, modulo
   normalized nondeterminism (elapsed-time reports etc.):

   ```bash
   tpy <name>.py
   PYTHONPATH=<tpy-lang-checkout>/lib/cpy python3 <name>.py
   ```

   The `PYTHONPATH` is required: a ported example imports `tpy` types, and the
   CPython compatibility stubs in `lib/cpy` are **not** shipped in the `tpy-lang`
   wheel — they only exist in a source checkout (`tmp/tpy-lang/lib/cpy` here, also
   wrapped by that checkout's `run_cpython.sh`). Compare the two outputs line by
   line: only elapsed-time figures may differ, everything else must be byte-identical.

   Examples that bind native libraries directly cannot run under CPython at all.
   For those, read the ported source against the original line by line instead, and
   record in the example's README that CPython verification was not possible.
5. Write `shedskin/<name>/README.md` from the template below.
6. List it in `shedskin/README.md` as `| <name> | <one-line description> | <N> |`
   (name, description, line count). If it is the first, create the table there and
   remove the "None are listed yet" sentence.

## Hard rules

**Fidelity gates what gets ported.** Stay as close to the original as possible —
type annotations, an occasional fixed-width integer type, and little else. If a
missing TurboPython library or language feature would force you to restructure the
program, **stop and defer the example**. Do not rewrite it to fit. Record the gap in
`TODO.md` under "Blocked on compiler gaps" so it can be filed against tpy-lang; a
blocked example is useful pressure on the compiler roadmap, and a contorted example
published on the project's own website is an argument against TurboPython.

**Only fully working examples get published.** An example lands once it compiles,
runs to completion, and matches CPython's output — or, where CPython cannot run it
at all because of native bindings, once it has been verified by inspection per step
4. No placeholders, no "coming soon" rows, no status columns full of failures.

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

- <every deviation, including annotations added>

## TurboPython bugs worked around

- <deviation> — <upstream issue link>, revert once fixed.

(Omit this section if there were none.)
```

Add a **Run** section only if the example needs more than `tpy <name>.py` — extra
setup, downloaded assets, a system library. Otherwise the convention in
`README.md` covers it.

The public statement of these rules is the "How these ports are made" section of
`shedskin/README.md`. Keep the two in sync.

## Backlog

`TODO.md` holds the migration queue, the deferred infrastructure work, and the
examples blocked on compiler gaps.
