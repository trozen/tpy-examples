"""The effect engine: characters, their scenes and paths, and the terminal they live on.

Every character lives in one list owned by the Terminal and is known everywhere
else by its index in that list. Effects keep lists of indices, never references
to characters, so there is no shared ownership to manage.

A character animates by playing a Scene (a sequence of frames: symbol, color,
duration) and moves by following a Path (waypoints joined by straight or
curved segments). When a scene or path finishes, the character reports an
Event; the effect reads the events after each tick and decides what happens
next.
"""
from __future__ import annotations

import random
from enum import Enum
from typing import Callable

from tpy import int32, Own, ValueType, copy

from geometry import (Coord, find_coord_on_bezier_curve, find_length_of_bezier_curve,
                      find_length_of_line, interpolate_coord)
from graphics import Color, Direction, Gradient, fg_sequence
from rng import randint

RESET = "\x1b[0m"


def _format_symbol(symbol: str, fg: Color, colored: bool) -> str:
    if colored:
        return fg_sequence(fg) + symbol + RESET
    return symbol


class Visual(ValueType):
    """What a character looks like: a symbol, optionally painted in a color.

    `colored` stands in for an optional color (README, "TurboPython bugs
    worked around")."""
    symbol: str
    fg: Color
    colored: bool
    formatted: str

    def __init__(self, symbol: str, fg: Color, colored: bool = True) -> None:
        self.symbol = symbol
        self.fg = fg
        self.colored = colored
        self.formatted = _format_symbol(symbol, fg, colored)


def plain_visual(symbol: str) -> Visual:
    return Visual(symbol, Color(0, 0, 0), False)


class Frame(ValueType):
    visual: Visual
    duration: int32

    def __init__(self, visual: Visual, duration: int32) -> None:
        self.visual = visual
        self.duration = duration


def _cyclic_distribution(larger: int32, smaller: int32) -> Own[list[int32]]:
    """For each index into the larger sequence, the index of its partner in the
    smaller one, spreading the smaller sequence evenly over the larger."""
    repeat_factor = larger // smaller
    overflow_count = larger % smaller
    overflow_used = False
    smaller_index = 0
    current_repeat = 0
    pairing: list[int32] = []
    for _ in range(larger):
        if current_repeat >= repeat_factor:
            if overflow_count:
                if overflow_used:
                    smaller_index += 1
                    current_repeat = 0
                    overflow_used = False
                else:
                    overflow_used = True
                    overflow_count -= 1
            else:
                smaller_index += 1
                current_repeat = 0
        current_repeat += 1
        pairing.append(smaller_index)
    return pairing


class Sync(Enum):
    NONE = 1
    STEP = 2  # the frame follows the share of the path's steps taken
    DISTANCE = 3  # ... or of its distance covered


class Scene:
    """A named sequence of frames. Played frame by frame; or, with an easing
    function, sampled at eased positions along its total duration; or, when
    synced, showing the frame that matches the character's progress along the
    path it is following."""
    name: str
    frames: list[Frame]
    sync: Sync
    looping: bool
    ease: Callable[[float], float] | None
    frame_index: int32
    ticks: int32
    done: bool
    easing_total_steps: int32
    easing_current_step: int32
    frame_end_steps: list[int32]

    # `sync` comes last: a default skipped over by keyword is resolved in the
    # caller's module, where Sync may not be imported (README).
    def __init__(self, name: str, looping: bool = False, sync: Sync = Sync.NONE) -> None:
        self.name = name
        self.frames = []
        self.sync = sync
        self.looping = looping
        self.ease = None
        self.frame_index = 0
        self.ticks = 0
        self.done = False
        self.easing_total_steps = 0
        self.easing_current_step = 0
        self.frame_end_steps = []

    def add_visual(self, visual: Visual, duration: int32) -> None:
        self.frames.append(Frame(visual, duration))
        self.easing_total_steps += duration
        self.frame_end_steps.append(self.easing_total_steps)

    def add_frame(self, symbol: str, duration: int32, fg: Color) -> None:
        self.add_visual(Visual(symbol, fg), duration)

    def add_plain_frame(self, symbol: str, duration: int32) -> None:
        self.add_visual(plain_visual(symbol), duration)

    def apply_gradient_to_symbols(self, symbols: list[str], duration: int32,
                                  gradient: Gradient) -> None:
        """One frame per color or per symbol, whichever is more, pairing the
        shorter list out evenly across the longer."""
        colors = gradient.spectrum
        if len(symbols) >= len(colors):
            pairing = _cyclic_distribution(len(symbols), len(colors))
            for i in range(len(symbols)):
                self.add_frame(symbols[i], duration, colors[pairing[i]])
        else:
            pairing = _cyclic_distribution(len(colors), len(symbols))
            for i in range(len(colors)):
                self.add_frame(symbols[pairing[i]], duration, colors[i])

    def reset(self) -> None:
        self.frame_index = 0
        self.ticks = 0
        self.done = False
        self.easing_current_step = 0

    def visual_at(self, index: int32) -> Own[Visual]:
        return self.frames[index].visual

    def advance(self) -> int32:
        """Step the scene one tick; returns the index of the frame to show."""
        if self.ease is not None:
            return self._advance_eased()
        shown = self.frame_index
        self.ticks += 1
        if self.ticks == self.frames[self.frame_index].duration:
            self.ticks = 0
            self.frame_index += 1
            if self.frame_index == len(self.frames):
                self.frame_index = 0
                if not self.looping:
                    self.done = True
        return shown

    def _advance_eased(self) -> int32:
        progress = self.easing_current_step / max(self.easing_total_steps - 1, 1)
        factor = 0.0
        if self.ease is not None:
            factor = self.ease(progress)
        final_step = max(self.easing_total_steps - 1, 0)
        step = max(min(round(factor * final_step), final_step), 0)
        # The frame whose span of steps contains `step` (bisect_right).
        shown = 0
        while self.frame_end_steps[shown] <= step:
            shown += 1
        self.easing_current_step += 1
        if self.easing_current_step == self.easing_total_steps:
            if self.looping:
                self.easing_current_step = 0
            else:
                self.done = True
        return shown


class Segment(ValueType):
    start: Coord
    end: Coord
    curved: bool
    control: Coord
    distance: float

    def __init__(self, start: Coord, end: Coord, curved: bool, control: Coord) -> None:
        self.start = start
        self.end = end
        self.curved = curved
        self.control = control
        self.distance = (find_length_of_bezier_curve(start, control, end) if curved
                         else find_length_of_line(start, end))


class Path:
    """Waypoints a character travels through at `speed` cells per tick.

    Activating a path prepends a segment from wherever the character is to the
    first waypoint, so the same path can be started from anywhere."""
    speed: float
    ease: Callable[[float], float] | None
    hold_time: int32
    loop: bool
    segments: list[Segment]
    has_origin: bool
    first_waypoint: Coord
    first_curved: bool
    first_control: Coord
    last_end: Coord
    waypoint_count: int32
    total_distance: float
    last_distance_reached: float
    current_step: int32
    max_steps: int32
    hold_time_remaining: int32

    def __init__(self, speed: float, hold_time: int32 = 0, loop: bool = False) -> None:
        self.speed = speed
        self.ease = None
        self.hold_time = hold_time
        self.loop = loop
        self.segments = []
        self.has_origin = False
        self.first_waypoint = Coord(0, 0)
        self.first_curved = False
        self.first_control = Coord(0, 0)
        self.last_end = Coord(0, 0)
        self.waypoint_count = 0
        self.total_distance = 0.0
        self.last_distance_reached = 0.0
        self.current_step = 0
        self.max_steps = 0
        self.hold_time_remaining = hold_time

    def _add_waypoint(self, coord: Coord, curved: bool, control: Coord) -> None:
        self.waypoint_count += 1
        if self.waypoint_count > 1:
            start = copy(self.last_end)
            segment = Segment(start, coord, curved, control)
            self.total_distance += segment.distance
            self.segments.append(segment)
            self.max_steps = round(self.total_distance / self.speed)
        self.last_end = coord
        if self.waypoint_count == 1:
            self.first_waypoint = coord
            self.first_curved = curved
            self.first_control = control

    def set_speed(self, speed: float) -> None:
        self.speed = speed

    def set_hold_time(self, hold_time: int32) -> None:
        self.hold_time = hold_time

    def progress(self, sync: Sync) -> float:
        """How far along the path the character is, for a synced scene."""
        if sync == Sync.STEP:
            return max(self.current_step, 1) / max(self.max_steps, 1)
        total = max(self.total_distance, 1.0)
        remaining = max(self.total_distance - self.last_distance_reached, 1.0)
        reached = max(total - remaining, 1.0)
        return reached / total

    def add_waypoint(self, coord: Coord) -> None:
        self._add_waypoint(coord, False, coord)

    def add_curved_waypoint(self, coord: Coord, control: Coord) -> None:
        self._add_waypoint(coord, True, control)

    def start_from(self, origin: Coord) -> None:
        first = copy(self.first_waypoint)
        control = copy(self.first_control)
        segment = Segment(origin, first, self.first_curved, control)
        self.total_distance += segment.distance
        if self.has_origin:
            self.total_distance -= self.segments[0].distance
            self.segments[0] = segment
        else:
            self.segments.insert(0, segment)
            self.has_origin = True
        self.current_step = 0
        self.hold_time_remaining = self.hold_time
        self.max_steps = round(self.total_distance / self.speed)

    def step(self) -> Own[Coord]:
        if not self.max_steps or self.current_step >= self.max_steps or not self.total_distance:
            return self.segments[len(self.segments) - 1].end
        self.current_step += 1
        progress = self.current_step / self.max_steps
        if self.ease is not None:
            progress = self.ease(progress)
        distance_to_travel = progress * self.total_distance
        self.last_distance_reached = distance_to_travel
        active = len(self.segments) - 1
        for i in range(len(self.segments)):
            if distance_to_travel <= self.segments[i].distance:
                active = i
                break
            distance_to_travel -= self.segments[i].distance
        else:
            distance_to_travel += self.segments[active].distance
        segment = self.segments[active]
        if segment.distance == 0:
            factor = 0.0
        elif self.ease is not None:
            factor = distance_to_travel / segment.distance
        else:
            factor = min(distance_to_travel / segment.distance, 1.0)
        if segment.curved:
            return find_coord_on_bezier_curve(segment.start, segment.control, segment.end, factor)
        return interpolate_coord(segment.start, segment.end, factor)


class EventKind(Enum):
    SCENE_COMPLETE = 1
    PATH_COMPLETE = 2


class Event(ValueType):
    """Character `char_id` finished the scene or path it was playing (`name`)."""
    char_id: int32
    kind: EventKind
    name: str

    def __init__(self, char_id: int32, kind: EventKind, name: str) -> None:
        self.char_id = char_id
        self.kind = kind
        self.name = name


class Character:
    id: int32
    input_symbol: str
    input_coord: Coord
    coord: Coord
    visual: Visual
    layer: int32
    visible: bool
    is_fill: bool
    active: bool  # in the terminal's list of animating characters
    scenes: list[Scene]
    active_scene: int32
    paths: list[Path]
    path_names: list[str]
    path_next: list[str]
    path_scene: list[str]
    path_end_scene: list[str]
    path_stop_scene: list[bool]
    path_start_layer: list[int32]
    path_end_layer: list[int32]
    active_path: int32

    def __init__(self, id: int32, symbol: str, coord: Coord, is_fill: bool) -> None:
        self.id = id
        self.input_symbol = symbol
        self.input_coord = coord
        self.coord = coord
        self.visual = plain_visual(symbol)
        self.layer = 0
        self.visible = False
        self.is_fill = is_fill
        self.active = False
        self.scenes = []
        self.active_scene = -1
        self.paths = []
        self.path_names = []
        self.path_next = []
        self.path_scene = []
        self.path_end_scene = []
        self.path_stop_scene = []
        self.path_start_layer = []
        self.path_end_layer = []
        self.active_path = -1

    def move_to(self, coord: Coord) -> None:
        self.coord = coord

    def return_home(self) -> None:
        home = copy(self.input_coord)
        self.coord = home

    # -- appearance ---------------------------------------------------------

    def set_appearance(self, symbol: str, fg: Color) -> None:
        self.visual = Visual(symbol, fg)

    def set_symbol(self, symbol: str) -> None:
        """Change the symbol, keeping the color."""
        fg = copy(self.visual.fg)
        self.visual = Visual(symbol, fg, self.visual.colored)

    def add_scene(self, scene: Own[Scene]) -> int32:
        self.scenes.append(scene)
        return len(self.scenes) - 1

    def scene_index(self, name: str) -> int32:
        for i in range(len(self.scenes)):
            if self.scenes[i].name == name:
                return i
        raise KeyError(name)

    def activate_scene(self, name: str) -> None:
        self.active_scene = self.scene_index(name)
        scene = self.scenes[self.active_scene]
        self.visual = scene.visual_at(scene.frame_index)

    def deactivate_scene(self) -> None:
        self.active_scene = -1

    def clear_scenes(self) -> None:
        self.scenes.clear()
        self.active_scene = -1

    def set_scene_ease(self, name: str, ease: Callable[[float], float]) -> None:
        self.scenes[self.scene_index(name)].ease = ease

    def _step_animation(self, events: list[Event]) -> None:
        if self.active_scene < 0:
            return
        scene = self.scenes[self.active_scene]
        if scene.sync != Sync.NONE:
            last = len(scene.frames) - 1
            if self.active_path < 0:
                # The path is done, so the scene is too.
                shown = last
                scene.done = True
            else:
                progress = self.paths[self.active_path].progress(scene.sync)
                shown = max(min(round(last * progress), last), 0)
        else:
            shown = scene.advance()
        self.visual = scene.visual_at(shown)
        if scene.done:
            scene.reset()
            if not scene.looping:
                self.active_scene = -1
                events.append(Event(self.id, EventKind.SCENE_COMPLETE, scene.name))

    # -- motion -------------------------------------------------------------

    def add_path(self, name: str, path: Own[Path], then: str = "", scene: str = "",
                 end_scene: str = "", stop_scene: bool = False, start_layer: int32 = -1,
                 end_layer: int32 = -1) -> int32:
        """Give the character a path. When it is started, the character plays
        `scene` and moves to `start_layer`; when it ends, it stops its scene if
        `stop_scene`, sets off along path `then`, plays `end_scene` and moves to
        `end_layer`. These happen within the tick, as TTE's events do (README)."""
        self.paths.append(path)
        self.path_names.append(name)
        self.path_next.append(then)
        self.path_scene.append(scene)
        self.path_end_scene.append(end_scene)
        self.path_stop_scene.append(stop_scene)
        self.path_start_layer.append(start_layer)
        self.path_end_layer.append(end_layer)
        return len(self.paths) - 1

    def path_index(self, name: str) -> int32:
        for i in range(len(self.path_names)):
            if self.path_names[i] == name:
                return i
        raise KeyError(name)

    def clear_paths(self) -> None:
        self.paths.clear()
        self.path_names.clear()
        self.path_next.clear()
        self.path_scene.clear()
        self.path_end_scene.clear()
        self.path_stop_scene.clear()
        self.path_start_layer.clear()
        self.path_end_layer.clear()
        self.active_path = -1

    def has_path(self, name: str) -> bool:
        return name in self.path_names

    def remove_path(self, name: str) -> None:
        if name not in self.path_names:
            return
        index = self.path_index(name)
        if self.active_path == index:
            self.active_path = -1
        elif self.active_path > index:
            self.active_path -= 1
        del self.paths[index]
        self.path_names.pop(index)
        self.path_next.pop(index)
        self.path_scene.pop(index)
        self.path_end_scene.pop(index)
        self.path_stop_scene.pop(index)
        self.path_start_layer.pop(index)
        self.path_end_layer.pop(index)

    def active_path_name(self) -> str:
        return self.path_names[self.active_path] if self.active_path >= 0 else ""

    def activate_path(self, index: int32) -> None:
        self.active_path = index
        self.paths[index].start_from(self.coord)
        if self.path_start_layer[index] >= 0:
            self.layer = self.path_start_layer[index]
        if self.path_scene[index]:
            self.activate_scene(self.path_scene[index])

    def activate_path_named(self, name: str) -> None:
        self.activate_path(self.path_index(name))

    def deactivate_path(self) -> None:
        self.active_path = -1

    def _move(self, events: list[Event]) -> None:
        if self.active_path < 0:
            return
        path = self.paths[self.active_path]
        self.coord = path.step()
        if path.current_step != path.max_steps:
            return
        if path.hold_time_remaining:
            path.hold_time_remaining -= 1
            return
        if path.loop and len(path.segments) > 1:
            self.activate_path(self.active_path)
            return
        finished = self.active_path
        name = self.path_names[finished]
        then = self.path_next[finished]
        end_scene = self.path_end_scene[finished]
        stop_scene = self.path_stop_scene[finished]
        end_layer = self.path_end_layer[finished]
        self.active_path = -1
        events.append(Event(self.id, EventKind.PATH_COMPLETE, name))
        if stop_scene:
            self.deactivate_scene()
        if then:
            self.activate_path_named(then)
        if end_scene:
            self.activate_scene(end_scene)
        if end_layer >= 0:
            self.layer = end_layer

    # -- lifecycle ----------------------------------------------------------

    def is_animating(self) -> bool:
        return self.active_scene >= 0 or self.active_path >= 0

    def tick(self, events: list[Event]) -> None:
        self._move(events)
        self._step_animation(events)


class Grouping(Enum):
    ROW_TOP_TO_BOTTOM = 1
    ROW_BOTTOM_TO_TOP = 2
    COLUMN_LEFT_TO_RIGHT = 3
    DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT = 4
    DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT = 5


class Canvas:
    """The area effects draw in, and the bounds of the text inside it."""
    top: int32
    right: int32
    bottom: int32
    left: int32
    text_top: int32
    text_right: int32
    text_bottom: int32
    text_left: int32

    def __init__(self, top: int32, right: int32) -> None:
        self.top = top
        self.right = right
        self.bottom = 1
        self.left = 1
        self.text_top = 0
        self.text_right = 0
        self.text_bottom = 0
        self.text_left = 0

    def include_text(self, coord: Coord) -> None:
        if self.text_left == 0:
            self.text_left = coord.column
            self.text_right = coord.column
            self.text_top = coord.row
            self.text_bottom = coord.row
            return
        self.text_left = min(self.text_left, coord.column)
        self.text_right = max(self.text_right, coord.column)
        self.text_top = max(self.text_top, coord.row)
        self.text_bottom = min(self.text_bottom, coord.row)

    def width(self) -> int32:
        return self.right - self.left + 1

    def height(self) -> int32:
        return self.top - self.bottom + 1

    def random_coord(self) -> Coord:
        column = randint(self.left, self.right)
        row = randint(self.bottom, self.top)
        return Coord(column, row)

    def random_coord_outside(self) -> Coord:
        """A random cell just beyond one of the canvas's four edges."""
        above = Coord(randint(self.left, self.right), self.top + 1)
        below = Coord(randint(self.left, self.right), self.bottom - 1)
        left = Coord(self.left - 1, randint(self.bottom, self.top))
        right = Coord(self.right + 1, randint(self.bottom, self.top))
        edges = [above, below, left, right]
        return edges[randint(0, 3)]

    def center(self) -> Coord:
        return Coord(self.left + (self.right - self.left) // 2,
                     self.bottom + (self.top - self.bottom) // 2)

    def text_height(self) -> int32:
        return self.text_top - self.text_bottom + 1 if self.text_bottom else 0

    def coord_is_in_canvas(self, coord: Coord) -> bool:
        return (self.left <= coord.column <= self.right
                and self.bottom <= coord.row <= self.top)

    def coord_is_in_text(self, coord: Coord) -> bool:
        return (self.text_left <= coord.column <= self.text_right
                and self.text_bottom <= coord.row <= self.text_top)

    def random_coord_in_text(self) -> Coord:
        column = randint(self.text_left, self.text_right)
        row = randint(self.text_bottom, self.text_top)
        return Coord(column, row)


def split_characters(text: str) -> Own[list[str]]:
    """Split text into characters by decoding its UTF-8 bytes one sequence at a
    time; TurboPython strings index by byte (README)."""
    data = text.encode()
    characters: list[str] = []
    i = 0
    while i < len(data):
        lead = data[i]
        width = 1
        if lead >= 0xF0:
            width = 4
        elif lead >= 0xE0:
            width = 3
        elif lead >= 0xC0:
            width = 2
        characters.append(data[i:i + width].decode())
        i += width
    return characters


def text_rows(text: str, tab_width: int32 = 4) -> Own[list[list[str]]]:
    """The text as rows of single-cell characters, tabs expanded to spaces."""
    rows: list[list[str]] = []
    lines = text.replace("\r", "").split("\n")
    for line in lines:
        row: list[str] = []
        characters = split_characters(line)
        for character in characters:
            if character == "\t":
                row.append(" ")
                while len(row) % tab_width:
                    row.append(" ")
            else:
                row.append(character)
        rows.append(row)
    while len(rows) > 1 and not rows[len(rows) - 1]:
        rows.pop()
    return rows


class Terminal:
    """Owns every character, tracks which are visible and animating, and
    renders a frame of the canvas.

    The canvas is the size of the text, clipped to the terminal. Characters for
    the text come first, then one "fill" character for every empty cell, then
    whatever an effect adds (particles, lightning)."""
    canvas: Canvas
    chars: list[Character]
    input_ids: list[int32]
    fill_ids: list[int32]
    by_coord: dict[Coord, int32]
    visible_ids: list[int32]
    active_ids: list[int32]
    events: list[Event]

    def __init__(self, text: str, max_width: int32, max_height: int32) -> None:
        rows = text_rows(text)
        width = 1
        for row in rows:
            width = max(width, len(row))
        self.canvas = Canvas(min(len(rows), max_height), min(width, max_width))
        self.chars = []
        self.input_ids = []
        self.fill_ids = []
        self.by_coord = {}
        self.visible_ids = []
        self.active_ids = []
        self.events = []
        for i in range(len(rows)):
            coord_row = len(rows) - i
            for j in range(len(rows[i])):
                coord = Coord(j + 1, coord_row)
                if rows[i][j] == " " or coord_row > self.canvas.top or j + 1 > self.canvas.right:
                    continue
                char_id = len(self.chars)
                self.chars.append(Character(char_id, rows[i][j], coord, False))
                self.input_ids.append(char_id)
                self.by_coord[coord] = char_id
                self.canvas.include_text(coord)
        for row in range(1, self.canvas.top + 1):
            for column in range(1, self.canvas.right + 1):
                coord = Coord(column, row)
                if coord not in self.by_coord:
                    char_id = len(self.chars)
                    self.chars.append(Character(char_id, " ", coord, True))
                    self.fill_ids.append(char_id)
                    self.by_coord[coord] = char_id

    def add_character(self, symbol: str, coord: Coord) -> int32:
        char_id = len(self.chars)
        self.chars.append(Character(char_id, symbol, coord, False))
        return char_id

    def text_colors(self, gradient: Gradient, direction: Direction) -> Own[dict[Coord, Color]]:
        """The gradient laid over the text's bounding box, one color per cell."""
        return gradient.coordinate_colors(self.canvas.text_bottom, self.canvas.text_top,
                                          self.canvas.text_left, self.canvas.text_right,
                                          direction)

    def text_colors_at_angle(self, gradient: Gradient, degrees: float) -> Own[dict[Coord, Color]]:
        """The gradient laid over the text's bounding box at an angle."""
        return gradient.angled_colors(self.canvas.text_bottom, self.canvas.text_top,
                                      self.canvas.text_left, self.canvas.text_right, degrees)

    def at(self, coord: Coord) -> int32:
        """The text or fill character at `coord`, or -1 outside the canvas."""
        return self.by_coord.get(coord, -1)

    # -- selecting characters -----------------------------------------------

    def characters(self, include_fill: bool = False) -> Own[list[int32]]:
        """Text characters (and, optionally, fill), top to bottom, left to right."""
        keyed: list[tuple[int32, int32, int32]] = []
        for char_id in self.input_ids:
            coord = copy(self.chars[char_id].input_coord)
            keyed.append((-coord.row, coord.column, char_id))
        if include_fill:
            for char_id in self.fill_ids:
                coord = copy(self.chars[char_id].input_coord)
                keyed.append((-coord.row, coord.column, char_id))
        ids: list[int32] = []
        for key in sorted(keyed):
            ids.append(key[2])
        return ids

    def grouped(self, grouping: Grouping, include_fill: bool = False) -> Own[list[list[int32]]]:
        """Characters split into rows, columns or diagonals, in the order named."""
        # Bottom to top, then left to right: the order within each group.
        keyed: list[tuple[int32, int32, int32]] = []
        for char_id in self.characters(include_fill):
            coord = copy(self.chars[char_id].input_coord)
            keyed.append((coord.row, coord.column, char_id))
        groups: dict[int32, list[int32]] = {}
        for entry in sorted(keyed):
            row = entry[0]
            column = entry[1]
            key = 0
            match grouping:
                case Grouping.ROW_TOP_TO_BOTTOM:
                    key = -row
                case Grouping.ROW_BOTTOM_TO_TOP:
                    key = row
                case Grouping.COLUMN_LEFT_TO_RIGHT:
                    key = column
                case Grouping.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT:
                    key = column - row
                case Grouping.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT:
                    key = row + column
            if key not in groups:
                groups[key] = []
            groups[key].append(entry[2])
        result: list[list[int32]] = []
        for key in sorted(groups.keys()):
            result.append(copy(groups[key]))
        return result

    def neighbors(self, char_id: int32) -> Own[list[int32]]:
        """The characters north, south, west and east of `char_id`, where they exist."""
        coord = copy(self.chars[char_id].input_coord)
        found: list[int32] = []
        column = coord.column
        row = coord.row
        for neighbor_coord in [Coord(column, row + 1), Coord(column, row - 1),
                               Coord(column - 1, row), Coord(column + 1, row)]:
            neighbor = self.at(neighbor_coord)
            if neighbor >= 0:
                found.append(neighbor)
        return found

    # -- state ----------------------------------------------------------------

    def set_visible(self, char_id: int32, visible: bool) -> None:
        character = self.chars[char_id]
        if character.visible == visible:
            return
        character.visible = visible
        # visible_ids stays sorted by id: characters are painted in creation order.
        low = 0
        high = len(self.visible_ids)
        while low < high:
            middle = (low + high) // 2
            if self.visible_ids[middle] < char_id:
                low = middle + 1
            else:
                high = middle
        if visible:
            self.visible_ids.insert(low, char_id)
        else:
            self.visible_ids.pop(low)

    def activate(self, char_id: int32) -> None:
        if not self.chars[char_id].active:
            self.chars[char_id].active = True
            self.active_ids.append(char_id)

    def deactivate(self, char_id: int32) -> None:
        if self.chars[char_id].active:
            self.chars[char_id].active = False
            self.active_ids.remove(char_id)

    def tick(self) -> None:
        """Advance every animating character by one frame, collecting events."""
        for char_id in self.active_ids:
            self.chars[char_id].tick(self.events)

    def take_events(self) -> Own[list[Event]]:
        taken: list[Event] = []
        for event in self.events:
            taken.append(event)
        self.events.clear()
        return taken

    def prune(self) -> None:
        """Forget characters that have stopped animating."""
        still_active: list[int32] = []
        for char_id in self.active_ids:
            character = self.chars[char_id]
            if character.is_animating():
                still_active.append(char_id)
            else:
                character.active = False
        self.active_ids = still_active

    def only_active_among(self, allowed: set[int32]) -> bool:
        """Whether every animating character is one of `allowed`."""
        for char_id in self.active_ids:
            if char_id not in allowed:
                return False
        return True

    def has_active(self) -> bool:
        return len(self.active_ids) > 0

    # -- output -------------------------------------------------------------

    def render(self) -> str:
        """The canvas as text, top row first, painted lowest layer first."""
        height = self.canvas.top
        width = self.canvas.right
        cells: list[list[str]] = []
        for _ in range(height):
            blank_row: list[str] = []
            for _ in range(width):
                blank_row.append(" ")
            cells.append(blank_row)
        min_layer = 0
        max_layer = 0
        for char_id in self.visible_ids:
            min_layer = min(min_layer, self.chars[char_id].layer)
            max_layer = max(max_layer, self.chars[char_id].layer)
        for layer in range(min_layer, max_layer + 1):
            for char_id in self.visible_ids:
                character = self.chars[char_id]
                if character.layer != layer:
                    continue
                row = character.coord.row
                column = character.coord.column
                if 1 <= row <= height and 1 <= column <= width:
                    cells[row - 1][column - 1] = character.visual.formatted
        lines: list[str] = []
        for row_cells in reversed(cells):
            lines.append("".join(row_cells))
        return "\n".join(lines)


class ParticlePool:
    """Recycles effect-added characters (raindrops, sparks, smoke).

    acquire() hands out a returned particle, reset, or creates a new one while
    the pool is under `max_size` (None: no limit); the second value says
    whether it is new and so still needs setting up. A particle goes back with
    reclaim()."""
    symbols: list[str]
    max_size: int32 | None
    members: set[int32]
    available: list[int32]

    def __init__(self, symbols: list[str], max_size: int32 | None = None) -> None:
        self.symbols = copy(symbols)
        self.max_size = max_size
        self.members = set()
        self.available = []

    def owns(self, char_id: int32) -> bool:
        return char_id in self.members

    def _create(self, term: Terminal) -> int32:
        char_id = term.add_character(random.choice(self.symbols), Coord(0, 0))
        self.members.add(char_id)
        return char_id

    def fill(self, term: Terminal, count: int32) -> Own[list[int32]]:
        """Create `count` particles up front; returns them for setting up."""
        created: list[int32] = []
        for _ in range(count):
            char_id = self._create(term)
            self.available.append(char_id)
            created.append(char_id)
        return created

    def acquire(self, term: Terminal) -> tuple[int32, bool]:
        if self.available:
            char_id = self.available.pop()
            character = term.chars[char_id]
            character.deactivate_path()
            character.deactivate_scene()
            character.clear_paths()
            return (char_id, False)
        if self.max_size is not None and len(self.members) >= self.max_size:
            return (-1, False)
        return (self._create(term), True)

    def reclaim(self, term: Terminal, char_id: int32) -> None:
        term.set_visible(char_id, False)
        term.chars[char_id].deactivate_path()
        term.chars[char_id].deactivate_scene()
        term.deactivate(char_id)
        if char_id not in self.available:
            self.available.append(char_id)
