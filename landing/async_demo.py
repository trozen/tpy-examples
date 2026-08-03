# A tiny async HTTP server. Run it, then open
# http://127.0.0.1:8080 in a browser or curl it.
# Stop it with Ctrl-C.
import asyncio
import time
from asyncio import StreamReader, StreamWriter
from tpy import Own

async def handle(reader: Own[StreamReader],
                 writer: Own[StreamWriter]) -> None:
    await reader.readline()         # the request line
    now = int(time.time())
    writer.write(b"HTTP/1.1 200 OK\r\n")
    writer.write(b"Content-Type: text/html\r\n")
    writer.write(b"Connection: close\r\n\r\n")
    writer.write(b"<h1>Hello from TurboPython</h1>")
    writer.write(f"<p>epoch time: {now}</p>".encode())
    await writer.drain()
    writer.close()

async def serve() -> None:
    addr = "127.0.0.1"
    port = 8080
    server = await asyncio.start_server(
        handle, addr, port)
    print(f"serving on http://{addr}:{port} ...")
    await server.serve_forever()

def main() -> None:
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("shutting down")

main()
