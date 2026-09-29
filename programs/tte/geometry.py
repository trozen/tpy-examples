"""Coordinates, and the line and curve maths that character paths are built on.

Canvas coordinates are 1-based, with row 1 at the bottom. Terminal cells are
about twice as tall as they are wide, so distances scale rows by
TERMINAL_ROW_SCALE to keep diagonal motion even.
"""
from __future__ import annotations

import math

from tpy import int32, Own, ValueType

TERMINAL_ROW_SCALE = 2

_BEZIER_LENGTH_TOLERANCE = 0.0001
_BEZIER_LENGTH_MAX_DEPTH = 12


class Coord(ValueType):
    column: int32
    row: int32

    def __init__(self, column: int32, row: int32) -> None:
        self.column = column
        self.row = row

    def __eq__(self, other: Coord) -> bool:
        return self.column == other.column and self.row == other.row

    def __hash__(self) -> int:
        return hash((self.column, self.row))


def find_length_of_line(start: Coord, end: Coord) -> float:
    column_diff = float(end.column - start.column)
    row_diff = float((end.row - start.row) * TERMINAL_ROW_SCALE)
    return math.hypot(column_diff, row_diff)


def interpolate_coord(start: Coord, end: Coord, t: float) -> Coord:
    x = (1 - t) * start.column + t * end.column
    y = (1 - t) * start.row + t * end.row
    return Coord(round(x), round(y))


def find_coord_on_bezier_curve(start: Coord, control: Coord, end: Coord, t: float) -> Coord:
    # De Casteljau for one control point: lerp each leg, then lerp the results.
    ax = (1 - t) * start.column + t * control.column
    ay = (1 - t) * start.row + t * control.row
    bx = (1 - t) * control.column + t * end.column
    by = (1 - t) * control.row + t * end.row
    x = (1 - t) * ax + t * bx
    y = (1 - t) * ay + t * by
    return Coord(round(x), round(y))


def _bezier_length(xs: list[float], ys: list[float], depth: int32) -> float:
    chord = math.dist([xs[0], ys[0]], [xs[2], ys[2]])
    polygon = (math.dist([xs[0], ys[0]], [xs[1], ys[1]])
               + math.dist([xs[1], ys[1]], [xs[2], ys[2]]))
    if depth >= _BEZIER_LENGTH_MAX_DEPTH or polygon - chord <= _BEZIER_LENGTH_TOLERANCE:
        return (polygon + chord) / 2
    # Split the curve in two at t=0.5 and measure each half.
    mx0 = (xs[0] + xs[1]) / 2
    my0 = (ys[0] + ys[1]) / 2
    mx1 = (xs[1] + xs[2]) / 2
    my1 = (ys[1] + ys[2]) / 2
    cx = (mx0 + mx1) / 2
    cy = (my0 + my1) / 2
    return (_bezier_length([xs[0], mx0, cx], [ys[0], my0, cy], depth + 1)
            + _bezier_length([cx, mx1, xs[2]], [cy, my1, ys[2]], depth + 1))


def find_length_of_bezier_curve(start: Coord, control: Coord, end: Coord) -> float:
    xs = [float(start.column), float(control.column), float(end.column)]
    ys = [float(start.row * TERMINAL_ROW_SCALE), float(control.row * TERMINAL_ROW_SCALE),
          float(end.row * TERMINAL_ROW_SCALE)]
    return _bezier_length(xs, ys, 0)


def find_normalized_distance_from_center(bottom: int32, top: int32, left: int32, right: int32,
                                         coord: Coord) -> float:
    center_column = (left + right) / 2
    center_row = (bottom + top) / 2
    max_distance = math.hypot((right - left) / 2, (top - bottom) / 2 * TERMINAL_ROW_SCALE)
    if max_distance == 0:
        return 0.0
    distance = math.hypot(coord.column - center_column,
                          (coord.row - center_row) * TERMINAL_ROW_SCALE)
    return distance / max_distance


def find_coords_on_circle(origin: Coord, radius: int32, coords_limit: int32 = 0) -> Own[list[Coord]]:
    """Up to `coords_limit` distinct points spread evenly around a circle,
    squashed vertically to look round in a terminal."""
    points: list[Coord] = []
    if not radius:
        points.append(origin)
        return points
    if not coords_limit:
        coords_limit = round(2 * math.pi * radius)
    angle_step = 2 * math.pi / coords_limit
    row_radius = radius // TERMINAL_ROW_SCALE
    seen: set[Coord] = set()
    for i in range(coords_limit):
        angle = angle_step * i
        x = origin.column + radius * math.cos(angle)
        y = origin.row + row_radius * math.sin(angle)
        point = Coord(round(x), round(y))
        if point not in seen:
            points.append(point)
            seen.add(point)
    return points


def find_coords_in_circle(center: Coord, radius: int32) -> Own[list[Coord]]:
    """Every cell inside a circle, squashed vertically like find_coords_on_circle."""
    coords: list[Coord] = []
    if not radius:
        coords.append(center)
        return coords
    a_squared = radius ** 2
    b_squared = (radius / TERMINAL_ROW_SCALE) ** 2
    for x in range(center.column - radius, center.column + radius + 1):
        x_component = (x - center.column) ** 2 / a_squared
        max_y_offset = int((b_squared * (1 - x_component)) ** 0.5)
        for y in range(center.row - max_y_offset, center.row + max_y_offset + 1):
            coords.append(Coord(x, y))
    return coords


def find_coords_in_rect(origin: Coord, distance: int32) -> Own[list[Coord]]:
    """Every cell of the square `distance` cells either side of `origin`."""
    coords: list[Coord] = []
    if not distance:
        coords.append(origin)
        return coords
    for column in range(origin.column - distance, origin.column + distance + 1):
        for row in range(origin.row - distance, origin.row + distance + 1):
            coords.append(Coord(column, row))
    return coords


def extrapolate_along_ray(origin: Coord, target: Coord, offset: float) -> Coord:
    """The point `offset` further on along the line from `origin` through `target`."""
    distance = find_length_of_line(origin, target)
    if distance == 0:
        return target
    t = 1 + offset / distance
    column = (1 - t) * origin.column + t * target.column
    row = (1 - t) * origin.row + t * target.row
    return Coord(round(column), round(row))
