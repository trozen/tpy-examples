"""Easing functions: map progress in [0, 1] to eased progress, which may overshoot."""
from __future__ import annotations

import math
from typing import Callable

from tpy import int32, ValueType


def in_circ(progress: float) -> float:
    return 1 - math.sqrt(1 - progress ** 2)


def out_quint(progress: float) -> float:
    return 1 - (1 - progress) ** 5


def out_sine(progress: float) -> float:
    return math.sin(progress * math.pi / 2)


def in_out_sine(progress: float) -> float:
    return -(math.cos(math.pi * progress) - 1) / 2


def in_cubic(progress: float) -> float:
    return progress ** 3


def in_expo(progress: float) -> float:
    if progress == 0:
        return 0.0
    return 2.0 ** (10 * progress - 10)


def out_expo(progress: float) -> float:
    if progress == 1:
        return 1.0
    return 1 - 2.0 ** (-10 * progress)


def out_circ(progress: float) -> float:
    return math.sqrt(1 - (progress - 1) ** 2)


def out_quad(progress: float) -> float:
    return 1 - (1 - progress) * (1 - progress)


def out_cubic(progress: float) -> float:
    return 1 - (1 - progress) ** 3


def out_bounce(progress: float) -> float:
    n1 = 7.5625
    d1 = 2.75
    if progress < 1 / d1:
        return n1 * progress ** 2
    if progress < 2 / d1:
        return n1 * (progress - 1.5 / d1) ** 2 + 0.75
    if progress < 2.5 / d1:
        return n1 * (progress - 2.25 / d1) ** 2 + 0.9375
    return n1 * (progress - 2.625 / d1) ** 2 + 0.984375


def in_out_quad(progress: float) -> float:
    if progress < 0.5:
        return 2 * progress ** 2
    return 1 - (-2 * progress + 2) ** 2 / 2


def in_out_quart(progress: float) -> float:
    if progress < 0.5:
        return 8 * progress ** 4
    return 1 - (-2 * progress + 2) ** 4 / 2


def in_out_circ(progress: float) -> float:
    if progress < 0.5:
        return (1 - math.sqrt(1 - (2 * progress) ** 2)) / 2
    return (math.sqrt(1 - (-2 * progress + 2) ** 2) + 1) / 2


class SequenceEaser:
    """Reveals a sequence of `count` items along an easing curve over
    `total_steps` steps. After each step(), items [added_start, added_end)
    have just been revealed and [removed_start, removed_end) just hidden
    (only a curve that turns back hides any)."""
    count: int32
    ease: Callable[[float], float]
    total_steps: int32
    current_step: int32
    eased: float
    shown: int32
    added_start: int32
    added_end: int32
    removed_start: int32
    removed_end: int32

    def __init__(self, count: int32, ease: Callable[[float], float],
                 total_steps: int32 = 100) -> None:
        self.count = count
        self.ease = ease
        self.total_steps = total_steps
        self.current_step = 0
        self.eased = 0.0
        self.shown = 0
        self.added_start = 0
        self.added_end = 0
        self.removed_start = 0
        self.removed_end = 0

    def is_complete(self) -> bool:
        return self.current_step >= self.total_steps

    def step(self) -> None:
        if self.current_step < self.total_steps:
            self.current_step += 1
            self.eased = max(0.0, min(self.ease(self.current_step / self.total_steps), 1.0))
        previous = self.shown
        length = int(self.eased * self.count)
        if self.is_complete() and abs(self.eased - 1.0) <= 1e-12:
            length = self.count
        self.added_start = previous
        self.added_end = max(length, previous)
        self.removed_start = min(length, previous)
        self.removed_end = previous
        self.shown = length


class CubicBezier(ValueType):
    """A CSS-style cubic-bezier easing curve through (0, 0), (x1, y1), (x2, y2), (1, 1)."""
    x1: float
    y1: float
    x2: float
    y2: float

    def __init__(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def sample_curve_x(self, t: float) -> float:
        return 3 * self.x1 * (1 - t) ** 2 * t + 3 * self.x2 * (1 - t) * t ** 2 + t ** 3

    def sample_curve_y(self, t: float) -> float:
        return 3 * self.y1 * (1 - t) ** 2 * t + 3 * self.y2 * (1 - t) * t ** 2 + t ** 3

    def sample_curve_derivative_x(self, t: float) -> float:
        return (3 * (1 - t) ** 2 * self.x1 + 6 * (1 - t) * t * (self.x2 - self.x1)
                + 3 * t ** 2 * (1 - self.x2))

    def __call__(self, progress: float) -> float:
        if progress <= 0:
            return 0.0
        if progress >= 1:
            return 1.0
        # Solve x(t) = progress by Newton's method, falling back to bisection
        # whenever a Newton step would leave the bracket.
        lower = 0.0
        upper = 1.0
        t = progress
        for _ in range(50):
            x_est = self.sample_curve_x(t)
            if x_est == progress:
                break
            if x_est < progress:
                lower = t
            else:
                upper = t
            derivative = self.sample_curve_derivative_x(t)
            candidate = t - (x_est - progress) / derivative if derivative > 0 else -1.0
            if not lower < candidate < upper:
                candidate = (lower + upper) / 2
            if abs(candidate - t) <= 1e-12:
                t = candidate
                break
            t = candidate
        return self.sample_curve_y(t)
