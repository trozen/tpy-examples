"""Colors, gradients and the ANSI sequences that paint them."""
from __future__ import annotations

import math
import random
from enum import Enum

from tpy import int32, Own, ValueType

from geometry import Coord, TERMINAL_ROW_SCALE, find_normalized_distance_from_center
from rng import randint

_HEX_DIGITS = "0123456789abcdef"


class Color(ValueType):
    r: int32
    g: int32
    b: int32

    def __init__(self, r: int32, g: int32, b: int32) -> None:
        self.r = r
        self.g = g
        self.b = b

    def __eq__(self, other: Color) -> bool:
        return self.r == other.r and self.g == other.g and self.b == other.b


def _hex_byte(text: str, start: int32) -> int32:
    return _HEX_DIGITS.find(text[start]) * 16 + _HEX_DIGITS.find(text[start + 1])


def hex_color(text: str) -> Color:
    """Parse an RGB hex color such as "8A008A" or "#8a008a"."""
    digits = text.lower()
    if digits.startswith("#"):
        digits = digits[1:]
    return Color(_hex_byte(digits, 0), _hex_byte(digits, 2), _hex_byte(digits, 4))


def hex_colors(texts: list[str]) -> Own[list[Color]]:
    parsed: list[Color] = []
    for text in texts:
        parsed.append(hex_color(text))
    return parsed


def choose_color(colors: list[Color]) -> Color:
    """random.choice, for a list of colors (README, "TurboPython bugs worked around")."""
    return colors[randint(0, len(colors) - 1)]


def fg_sequence(color: Color) -> str:
    return f"\x1b[38;2;{color.r};{color.g};{color.b}m"


def shift_color_towards(start: Color, end: Color, factor: float) -> Color:
    return Color(round(start.r + (end.r - start.r) * factor),
                 round(start.g + (end.g - start.g) * factor),
                 round(start.b + (end.b - start.b) * factor))


def _hue_to_rgb(lightness_scaled: float, intensity: float, hue: float) -> float:
    if hue < 0:
        hue += 1
    if hue > 1:
        hue -= 1
    if hue < 1 / 6:
        return lightness_scaled + (intensity - lightness_scaled) * 6 * hue
    if hue < 1 / 2:
        return intensity
    if hue < 2 / 3:
        return lightness_scaled + (intensity - lightness_scaled) * (2 / 3 - hue) * 6
    return lightness_scaled


def adjust_brightness(color: Color, brightness: float) -> Color:
    """Scale a color's HSL lightness, as TTE does for fades and flashes."""
    red = color.r / 255
    green = color.g / 255
    blue = color.b / 255
    max_val = max(red, green, blue)
    min_val = min(red, green, blue)
    lightness = (max_val + min_val) / 2
    hue = 0.0
    saturation = 0.0
    if max_val != min_val:
        diff = max_val - min_val
        if lightness > 0.5:
            saturation = diff / (2 - max_val - min_val)
        else:
            saturation = diff / (max_val + min_val)
        if max_val == red:
            hue = (green - blue) / diff + (6 if green < blue else 0)
        elif max_val == green:
            hue = (blue - red) / diff + 2
        else:
            hue = (red - green) / diff + 4
        hue /= 6
    lightness = max(min(lightness * brightness, 1.0), 0.0)
    if saturation == 0:
        red = lightness
        green = lightness
        blue = lightness
    else:
        if lightness < 0.5:
            intensity = lightness * (1 + saturation)
        else:
            intensity = lightness + saturation - lightness * saturation
        lightness_scaled = 2 * lightness - intensity
        red = _hue_to_rgb(lightness_scaled, intensity, hue + 1 / 3)
        green = _hue_to_rgb(lightness_scaled, intensity, hue)
        blue = _hue_to_rgb(lightness_scaled, intensity, hue - 1 / 3)
    return Color(round(red * 255), round(green * 255), round(blue * 255))


class Direction(Enum):
    VERTICAL = 1
    HORIZONTAL = 2
    RADIAL = 3
    DIAGONAL = 4


class Gradient:
    """The colors between a list of stops, `steps` colors per transition."""
    spectrum: list[Color]

    def __init__(self, stops: list[Color], steps: list[int32], loop: bool = False) -> None:
        self.spectrum = []
        points: list[Color] = []
        for stop in stops:
            points.append(stop)
        if loop and len(stops) > 1:
            first = stops[0]
            points.append(first)
        start = points[0]
        self.spectrum.append(start)
        for i in range(len(points) - 1):
            # A short steps list repeats its last value for the remaining transitions.
            step_count = steps[i] if i < len(steps) else steps[len(steps) - 1]
            for step in range(1, step_count):
                fraction = step / step_count
                self.spectrum.append(shift_color_towards(points[i], points[i + 1], fraction))
            end = points[i + 1]
            self.spectrum.append(end)

    def color_at_fraction(self, fraction: float) -> Color:
        index = round(fraction * (len(self.spectrum) - 1))
        return self.spectrum[index]

    def angled_colors(self, min_row: int32, max_row: int32, min_column: int32,
                      max_column: int32, degrees: float) -> Own[dict[Coord, Color]]:
        """Like coordinate_colors, along a line at `degrees` from the horizontal
        (90 runs bottom to top), with rows scaled to look square."""
        angle = math.radians(degrees)
        dx = math.cos(angle)
        dy = math.sin(angle)
        low = 0.0
        high = 0.0
        first = True
        for row in range(min_row, max_row + 1):
            for column in range(min_column, max_column + 1):
                along = (column - min_column) * dx + (row - min_row) * TERMINAL_ROW_SCALE * dy
                if first or along < low:
                    low = along
                if first or along > high:
                    high = along
                first = False
        mapping: dict[Coord, Color] = {}
        for row in range(min_row, max_row + 1):
            for column in range(min_column, max_column + 1):
                along = (column - min_column) * dx + (row - min_row) * TERMINAL_ROW_SCALE * dy
                fraction = (along - low) / (high - low) if high > low else 0.0
                mapping[Coord(column, row)] = self.color_at_fraction(fraction)
        return mapping

    def coordinate_colors(self, min_row: int32, max_row: int32, min_column: int32,
                          max_column: int32, direction: Direction) -> Own[dict[Coord, Color]]:
        """Map every coordinate in the rectangle to a color along `direction`."""
        row_span = max_row - min_row
        column_span = max_column - min_column
        mapping: dict[Coord, Color] = {}
        for row in range(min_row, max_row + 1):
            for column in range(min_column, max_column + 1):
                coord = Coord(column, row)
                fraction = 0.0
                match direction:
                    case Direction.VERTICAL:
                        if row_span:
                            fraction = (row - min_row) / row_span
                    case Direction.HORIZONTAL:
                        if column_span:
                            fraction = (column - min_column) / column_span
                    case Direction.RADIAL:
                        fraction = find_normalized_distance_from_center(
                            min_row, max_row, min_column, max_column, coord)
                    case Direction.DIAGONAL:
                        diagonal_span = row_span * TERMINAL_ROW_SCALE + column_span
                        if diagonal_span:
                            fraction = ((row - min_row) * TERMINAL_ROW_SCALE
                                        + (column - min_column)) / diagonal_span
                mapping[coord] = self.color_at_fraction(fraction)
        return mapping
