"""Random integers drawn exactly as CPython draws them."""
from __future__ import annotations

import random

from tpy import int32


def randint(a: int32, b: int32) -> int32:
    """random.randint, drawing from the generator exactly as CPython does.

    For a one-value range CPython still draws random bits, rejection-sampling
    one bit until it is 0; TurboPython's random module returns without drawing.
    Drawing the bits here keeps both runs on CPython's random stream (README,
    "TurboPython bugs worked around")."""
    if a == b:
        while random.getrandbits(1):
            pass
        return a
    return random.randint(a, b)
