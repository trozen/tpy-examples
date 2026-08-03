# Structural pattern matching over a union of types
# (algebraic data), compiled to a jump over a tagged
# union. Each arm destructures a variant by position;
# the result is read with no default arm, so the compiler
# proves the arms are exhaustive -- drop one and it won't
# compile.
from dataclasses import dataclass

@dataclass
class Circle:
    radius: float

@dataclass
class Rect:
    width: float
    height: float

@dataclass
class Triangle:
    base: float
    height: float

type Shape = Circle | Rect | Triangle

def main() -> None:
    shapes: list[Shape] = [
        Circle(1.0), Rect(2.0, 3.0), Triangle(4.0, 5.0),
    ]
    for s in shapes:
        match s:
            case Circle(r):
                a = 3.14159 * r ** 2
            case Rect(w, h):
                a = w * h
            case Triangle(b, h):
                a = 0.5 * b * h
        print(f"{a:.2f}")

main()
