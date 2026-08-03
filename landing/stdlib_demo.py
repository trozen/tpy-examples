# Many standard-library modules work out of the box.
import re
from argparse import ArgumentParser
from dataclasses import dataclass

@dataclass
class Address:
    user: str
    host: str

@dataclass
class Contact:
    id: int
    name: str
    address: Address

def main() -> None:
    parser = ArgumentParser(description="Add a contact.")
    parser.add_argument("--id", type=int, default=1)
    parser.add_argument("--name", default="Ada")
    parser.add_argument("--email", default="ada@acme.io")
    parser.add_argument("-v", "--verbose",
                        action="store_true")
    args = parser.parse_args()

    m = re.match(r"(\w+)@([\w.]+)", args.email)
    if m is not None:
        addr = Address(m.group(1), m.group(2))
        c = Contact(args.id, args.name, addr)
        print(c)
        if args.verbose:
            print("host:", c.address.host)

main()
