# curl

A curl-like HTTP and HTTPS client on `tplib.requests`: fetches a URL and prints
the response, with a focused subset of curl's flags. ~145 lines.

## Run

```bash
tpy curl.py http://example.com/
tpy curl.py -X POST -d '{"k":1}' -H "Content-Type: application/json" http://api.test/items
tpy curl.py -i -u user:pass http://api.test/     # headers too, with basic auth
tpy curl.py -m 5 http://api.test/slow            # give up after five seconds
tpy curl.py -o out.bin http://api.test/blob      # body to a file
tpy curl.py -L http://api.test/redirects-here    # follow redirects
tpy curl.py --cacert ca.pem https://api.test/    # trust an extra CA
tpy curl.py -k https://self-signed.test/         # skip certificate checks
```

The flags follow curl: `-X` method (default `GET`, or `POST` when `-d` is
given), `-d` body, `-H` header (repeatable), `-u` basic auth, `-i` include the
response headers, `-L` follow redirects, `-m` timeout in seconds, `-o` write
the body to a file, `--cacert` and `-k` for TLS. So do the exit codes: 0 on any
HTTP response, 7 when the connection fails, 28 on timeout, 60 on a certificate
problem, 1 for anything else.

TLS verifies against the vendored Mozilla roots plus the system CA bundle by
default, so public and system-trusted hosts need no flags.

## What it shows

- `tplib.requests` end to end: `requests.request` with method, body, headers,
  auth, timeout, redirects and TLS verification in one call, and the response's
  `status_code`, `reason`, `headers`, `content` and `text`.
- `argparse` with repeatable options (`action="append"`) and flags.
- Exception handling ordered most-specific first — `SSLError` and
  `ConnectionError` before `RequestException`, `Timeout` before it too — so the
  reason for a failure reaches the user instead of a generic message.
- A union-typed local where the API takes one: the body is
  `bytes | dict[str, str] | None`, the timeout `float | None`, and `verify`
  `bool | str`, matching the parameters they are passed to.
- `sys.exit(main())` turning the returned status into the process exit code.

## Verification

Not run by the harness: it needs a server. It was checked by hand against a
local `python3 -m http.server`: a plain `GET`, `-i`, `-o`, a 404, a refused
connection (exit code 7) and `-m` all behave as described above. There is no
CPython comparison, since `tplib.requests` has no CPython counterpart.
