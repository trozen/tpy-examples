"""Minimal single-connection TCP echo server. Binds to a host:port,
accepts one client, echoes everything it sends back, closes, exits.

It handles one connection and exits, on purpose: this is the blocking
baseline. async_echo_server.py and stream_server.py are the same server
serving many clients at once.

Usage:
    tpy tcp_server.py
    tpy tcp_server.py --host 0.0.0.0 --port 9000
"""

from argparse import ArgumentParser
from socket import (
    socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR,
    create_server,
)


def main() -> None:
    parser = ArgumentParser(description="Single-connection TCP echo server.")
    parser.add_argument(
        "--host", default="127.0.0.1", help="bind address",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="bind port",
    )
    args = parser.parse_args()

    # create_server bundles socket + SO_REUSEADDR + bind + listen.
    server = create_server((args.host, args.port))
    print(f"listening on {server.getsockname()}")

    conn, peer = server.accept()
    print(f"accepted connection from {peer}")

    # Drain the client (one chunk at a time) and echo back. Loop exits
    # when recv returns empty bytes (peer's half-close -> EOF).
    total_bytes = 0
    while True:
        chunk = conn.recv(4096)
        if len(chunk) == 0:
            break
        total_bytes = total_bytes + len(chunk)
        conn.sendall(chunk)

    print(f"echoed {total_bytes} bytes, closing")
    conn.close()
    server.close()


main()
