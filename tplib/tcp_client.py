"""Minimal TCP client. Connects to a peer, sends a message,
prints the response.

Run against the companion `tcp_server.py` in a second terminal, or
against any TCP service that echoes / speaks HTTP on localhost.

Usage:
    # Terminal 1:
    tpy tcp_server.py
    # Terminal 2:
    tpy tcp_client.py
    tpy tcp_client.py --host 192.168.1.10 --port 9000 --message "ping"
"""

from argparse import ArgumentParser
from socket import socket, AF_INET, SOCK_STREAM, SHUT_WR


def main() -> None:
    parser = ArgumentParser(description="Send a message over TCP and print the echoed reply.")
    parser.add_argument(
        "--host", default="127.0.0.1", help="server address",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="server port",
    )
    parser.add_argument(
        "--message", default="hello from tpy client", help="payload to send",
    )
    args = parser.parse_args()

    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((args.host, args.port))
    print(f"connected to {sock.getpeername()}")

    sock.sendall(args.message.encode() + b"\n")
    # Half-close write side so the server sees EOF and stops recv'ing.
    sock.shutdown(SHUT_WR)

    # Read the echoed reply (up to 4 KiB in one go -- fine for this demo).
    reply = sock.recv(4096)
    print(f"got {len(reply)} bytes from server:")
    print(reply.decode())

    sock.close()


main()
