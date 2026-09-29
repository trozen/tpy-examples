# tplib

Walkthroughs of TurboPython's library surface: `tplib`, the standard library
built for a statically compiled language, and the Python stdlib modules the
runtime implements. Each file takes one type or one module and exercises it end
to end, with the expected result in a comment next to each print. They are
reference material in program form rather than applications; for those see
[`programs/`](../programs/README.md).

## Containers

| file | what it shows | lines |
| ---- | ------------- | ----- |
| `array_list.py` | `tplib.ArrayList[T, N]`: a list with fixed-capacity inline storage, so it never allocates — append, index, pop, `copy()`, construction from a `Span` and from `dict.items()` | 90 |
| `box.py` | `tplib.Box[T]`: an owning heap slot — `set`, explicit `clone()`, `take()` consuming the box, `str` versus `repr`, and covariance from `Box[Circle]` to `Box[Shape]` through a `@dynamic` protocol | 94 |

Both run as `tpy <name>.py` and their output is recorded by the harness.

## Sockets and asyncio

Three echo servers and their clients, from blocking sockets up to asyncio
streams, so the same job can be read at three levels of abstraction:

| server | client | what it shows | lines |
| ------ | ------ | ------------- | ----- |
| `tcp_server.py` | `tcp_client.py` | `socket`: `create_server`, `accept`, `recv`/`sendall`, half-close with `shutdown`. The server takes one connection and exits, on purpose — it is the blocking baseline | 52 + 48 |
| `async_echo_server.py` | `async_echo_client.py` | `asyncio` over raw sockets: `loop.sock_accept` / `sock_recv` / `sock_sendall`, one task per client on one thread | 62 + 48 |
| `stream_server.py` | `stream_client.py` | `asyncio` streams: `start_server`, `open_connection`, `StreamReader.readline`, `StreamWriter.drain` | 59 + 47 |

Any client works against any server. Run a pair in two terminals:

```bash
cd tplib
tpy tcp_server.py                       # terminal 1
tpy tcp_client.py --message "ping"      # terminal 2
```

All take `--host` and `--port` (default `127.0.0.1:8765`); the clients also take
`--message`. Servers stop on Ctrl-C.

The harness builds these but does not run them, since each needs its peer in
another process. The clients and the two lower-level servers use only plain
Python types, so they also run unchanged under CPython. `stream_server.py`
takes its streams as `Own[...]` — the handler runs as its own task, so it must
own what it reads from — and therefore imports from `tpy`.

## Licensing

MIT, along with the rest of this repository outside `shedskin/` — see
[LICENSE](../LICENSE).
