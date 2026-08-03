# Many ordinary Python programs run as-is under
# TurboPython -- compiled native, often more than
# an order of magnitude faster than CPython.
WIDTH, HEIGHT, MAX_ITER = 64, 28, 90
CHARS = " .:-=+*#%@"

def escape(cx: float, cy: float) -> int:
    x, y = 0.0, 0.0
    for i in range(MAX_ITER):
        if x * x + y * y > 4.0:
            return i
        x, y = x * x - y * y + cx, 2.0 * x * y + cy
    return MAX_ITER

def main() -> None:
    for row in range(HEIGHT):
        cy = -1.2 + 2.4 * row / HEIGHT
        for col in range(WIDTH):
            cx = -2.4 + 3.2 * col / WIDTH
            idx = escape(cx, cy) % len(CHARS)
            print(CHARS[idx], end="")
        print("")

main()
