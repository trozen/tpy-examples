# landing

The short programs shown in the code window on
[tpy-lang.org](https://tpy-lang.org). Unlike the ported programs in
`shedskin/`, these are not applications — each one is a single file written to
show one part of the language at a glance: the standard types, ownership,
pattern matching, async, classes, the stdlib, HTTP plus JSON, and an ASCII
mandelbrot.

They are real programs, not fragments. Every one compiles, and all but the two
that need the network run to completion.

## Constraints

These files are consumed by the website, which imposes limits the rest of the
gallery does not have:

- **Lines stay under 61 characters.** The code window is about that wide, and
  longer lines make it scroll sideways. Aim for 57 when editing, to keep a
  margin. The website's `verify_examples.py` fails the build on any line over
  61, so a too-wide edit is caught rather than shipped.
- **One file, one topic.** Each program opens with a one- or two-line comment
  saying what it shows. That comment is the only explanation a visitor gets.
- **No data files, no arguments.** Each runs as `tpy <name>.py` and nothing
  else.

Which files appear on the site, their order, and the label on each is decided
by `ORDER` in the website's `build_examples.py` — adding a file here does not
put it on the page.

## Running them

```bash
cd landing
tpy -O mandelbrot.py
```

`requests_demo.py` and `async_demo.py` are compiled but not run by the
website's checks, because they hit the network.

## Licensing

MIT, along with the rest of this repository outside `shedskin/` — see
[LICENSE](../LICENSE).
