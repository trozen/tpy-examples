# Built-in types and idioms. An unannotated integer
# literal is Int32; `int` is arbitrary-precision.
def main() -> None:
    n = 6 * 7              # Int32 (default integer type)
    big: int = 2 ** 40     # int -> arbitrary precision int
    ratio = 22 / 7         # float
    ok = n > 40            # bool
    name = "TurboPython"   # str
    raw = b"\x01\x02\x03"  # bytes
    point = (3, 4)         # tuple

    nums = [5, 3, 8, 1, 9]
    evens = [x for x in nums if x % 2 == 0]   # list comp
    squares = {x: x * x for x in evens}       # dict comp
    thirds = {x % 3 for x in nums}            # set comp

    first, last = nums[0], nums[-1]   # negative index
    head = nums[:3]                   # slicing
    maybe: int | None = None          # Optional

    print(f"int32={n} big={big} ok={ok}")
    print("float:", ratio)
    print("str:", name.lower(), "bytes:", len(raw), raw[0])
    print("tuple:", point, "ends:", first, last)
    print("evens:", evens, "head:", head)
    print("squares:", squares, "thirds:", sorted(thirds))
    print("none?", maybe is None, "equals:", maybe)

main()
