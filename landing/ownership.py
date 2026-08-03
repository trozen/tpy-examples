# Reference types are borrowed at parameters and returns:
# no copy, the caller keeps ownership. Own[T] transfers
# ownership -- use it when a function returns a value or
# keeps one past the call.
# tpy is the module for core TurboPython types
from tpy import Own

global_shelf: list[list[int]] = []

# just reads xs -- borrowing is enough
def total(xs: list[int]) -> int:
    return sum(xs)

# returns a new list -- Own hands the caller ownership
def squares(n: int) -> Own[list[int]]:
    return [i * i for i in range(n)]

# keeps xs after the call -- Own takes ownership
def store(xs: Own[list[int]]) -> None:
    global_shelf.append(xs)

def main() -> None:
    nums = squares(5)        # nums owns the new list
    print("total:", total(nums))  # borrowed, not moved
    store(nums)              # ownership moves out
    print("shelf:", global_shelf[0])

main()
