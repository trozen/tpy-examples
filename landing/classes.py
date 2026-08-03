# Value types (int, float, bool, str) are copied. Reference
# types (classes, list, dict, set) are shared: a name or
# parameter refers to the same object.
class Account:
    def __init__(self, owner: str, balance: int) -> None:
        self.owner = owner
        self.balance = balance

    def deposit(self, amount: int) -> None:
        self.balance += amount

def topup(acc: Account, amount: int) -> None:
    acc.balance += amount

def main() -> None:
    a = Account("alice", 100)
    b = a                      # b is the same account
    b.deposit(50)              # change it through b...
    topup(a, 30)               # ...or through a function
    print(a.owner, a.balance)  # a sees both: alice 180

    x = 100
    y = x                      # y is an independent copy
    y += 1
    print("x:", x, "y:", y)    # x: 100 y: 101

main()
