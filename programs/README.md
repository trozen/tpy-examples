# programs

Original TurboPython applications: complete programs with a command line and a
job to do, written for TurboPython rather than ported. Each lives in its own
directory, with the entry point at `<name>/<name>.py` and a README describing
what it is and how it is verified.

| | name | description | lines |
| - | ---- | ----------- | ----- |
| | [curl](curl/) | a curl-like HTTP and HTTPS client on `tplib.requests` | 145 |
| | [tte](tte/) | terminal text effects — a selection of TerminalTextEffects' effects, plus three of our own | 5535 |

## Running one

```bash
cd programs/<name>
tpy <name>.py [arguments]
```

Each README says what arguments the program takes. The harness builds every
program; the ones that need the network or a peer are not run by it, and their
README says how they were checked instead.

## Licensing

MIT, along with the rest of this repository outside `shedskin/` — see
[LICENSE](../LICENSE). `tte` is derived from TerminalTextEffects, which is also
MIT-licensed; its copyright and permission notice are in
[tte/README.md](tte/README.md).
