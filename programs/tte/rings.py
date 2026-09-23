"""rings: the text forms spinning rings that disperse and re-form, then settles back into place."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from easing import out_cubic, out_quad, out_sine
from engine import EventKind, Path, Scene, Terminal, randint
from geometry import Coord, TERMINAL_ROW_SCALE, find_coords_in_rect, find_coords_on_circle
from graphics import Color, Direction, Gradient, hex_colors

RING_COLORS = ["ab48ff", "e7b2b2", "fffebd"]
RING_GAP = 0.1  # the gap between rings, as a share of the canvas's smaller side
SPIN_DURATION = 200
SPIN_SPEED_MIN = 0.25
SPIN_SPEED_MAX = 1.0
DISPERSE_DURATION = 200
SPIN_DISPERSE_CYCLES = 3
START_DURATION = 100
FINAL_GRADIENT_STOPS = ["ab48ff", "e7b2b2", "fffebd"]
FINAL_GRADIENT_STEPS = [12]


class Ring:
    """Characters spinning round a circle, each chasing the one ahead."""
    coords: list[Coord]  # counter-clockwise
    color: Color
    speed: float
    chars: list[int32]
    last_path: dict[int32, str]  # the ring path each character was on when it dispersed

    def __init__(self, coords: Own[list[Coord]], color: Color) -> None:
        self.coords = coords
        self.color = color
        self.speed = random.uniform(SPIN_SPEED_MIN, SPIN_SPEED_MAX)
        self.chars = []
        self.last_path = {}


class Rings:
    term: Terminal
    rings: list[Ring]
    ring_chars: set[int32]
    outsiders: list[int32]  # characters that don't fit on a ring
    ring_gap: int32
    condense_count: int32
    initial_disperse_done: bool
    spin_time: int32
    disperse_time: int32
    cycles: int32
    start_time: int32
    phase: str

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.rings = []
        self.ring_chars = set()
        self.outsiders = []
        smaller = min(self.term.canvas.top, self.term.canvas.right)
        self.ring_gap = int(max(round(smaller * RING_GAP), 1))
        self.condense_count = 0
        self.initial_disperse_done = False
        self.spin_time = SPIN_DURATION
        self.disperse_time = DISPERSE_DURATION
        self.cycles = SPIN_DISPERSE_CYCLES
        self.start_time = START_DURATION
        self.phase = "start"
        self.build()

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        ring_colors = hex_colors(RING_COLORS)
        pending: list[int32] = []
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            start = Scene("start")
            start.add_frame(character.input_symbol, 1, final_colors[home])
            character.add_scene(start)
            back = Path(0.8)
            back.ease = out_quad
            back.add_waypoint(home)
            character.add_path("home", back)
            character.activate_scene("start")
            self.term.set_visible(char_id, True)
            pending.append(char_id)
        random.shuffle(pending)
        # Rings grow outwards from the center until most of one would be off the canvas.
        center = self.term.canvas.center()
        for radius_scale in range(1, max(self.term.canvas.right, self.term.canvas.top), self.ring_gap):
            radius = radius_scale * TERMINAL_ROW_SCALE
            coords = find_coords_on_circle(center, radius, 7 * radius_scale)
            inside = 0
            for coord in coords:
                if self.term.canvas.coord_is_in_canvas(coord):
                    inside += 1
            if inside / len(coords) < 0.25:
                break
            color = ring_colors[len(self.rings) % len(ring_colors)]
            self.rings.append(Ring(coords, color))
        for ring_number in range(len(self.rings)):
            for _ in range(len(self.rings[ring_number].coords)):
                if pending:
                    self.add_to_ring(ring_number, pending.pop(0), final_colors)
        for char_id in self.term.characters():
            if char_id not in self.ring_chars:
                away = Path(0.8)
                away.ease = out_sine
                away_to = self.term.canvas.random_coord_outside()
                away.add_waypoint(away_to)
                self.term.chars[char_id].add_path("external", away)
                self.outsiders.append(char_id)

    def add_to_ring(self, ring_number: int32, char_id: int32,
                    final_colors: dict[Coord, Color]) -> None:
        ring = self.rings[ring_number]
        character = self.term.chars[char_id]
        symbol = [character.input_symbol]
        final_color = final_colors[copy(character.input_coord)]
        ring_color = copy(ring.color)
        spin = Scene("gradient")
        spin.apply_gradient_to_symbols(symbol, 3, Gradient([final_color, ring_color], [8]))
        character.add_scene(spin)
        # Alternate rings turn opposite ways; each character starts at its own place.
        coords: list[Coord] = []
        for coord in ring.coords:
            coords.append(coord)
        if ring_number % 2:
            coords.reverse()
        start = len(ring.chars)
        count = len(coords)
        for i in range(count):
            step = Path(ring.speed)
            step.add_waypoint(coords[(start + i) % count])
            character.add_path(str(i), step, then=str((i + 1) % count))
        ring.last_path[char_id] = "0"
        disperse = Scene("disperse")
        disperse.apply_gradient_to_symbols(symbol, 10, Gradient([ring_color, final_color], [8]))
        character.add_scene(disperse)
        ring.chars.append(char_id)
        self.ring_chars.add(char_id)

    def make_disperse_path(self, char_id: int32, origin: Coord) -> None:
        """A loop of five random points in a square round `origin`, where the
        character drifts while its ring is dispersed."""
        coords = find_coords_in_rect(origin, self.ring_gap)
        drift = Path(0.14, loop=True)
        for _ in range(5):
            drift.add_waypoint(coords[randint(0, len(coords) - 1)])
        character = self.term.chars[char_id]
        character.remove_path("disperse")
        character.add_path("disperse", drift)

    def disperse(self, ring: Ring) -> None:
        for char_id in ring.chars:
            character = self.term.chars[char_id]
            current = character.active_path_name()
            ring.last_path[char_id] = current if current else "0"
            position = copy(character.coord)
            self.make_disperse_path(char_id, position)
            character.activate_path_named("disperse")
            character.activate_scene("disperse")

    def spin(self, ring: Ring) -> None:
        """Back onto the ring, where each character left it, and spinning again."""
        for char_id in ring.chars:
            character = self.term.chars[char_id]
            last = ring.last_path[char_id]
            target = copy(character.paths[character.path_index(last)].first_waypoint)
            condense = Path(0.1)
            condense.add_waypoint(target)
            self.condense_count += 1
            name = f"condense{self.condense_count}"
            character.activate_path(character.add_path(name, condense, then=last))
            character.activate_scene("gradient")

    def step(self) -> bool:
        if self.phase == "complete":
            return False
        if self.phase == "start":
            if not self.start_time:
                self.phase = "disperse"
            else:
                self.start_time -= 1
        elif self.phase == "disperse":
            if not self.initial_disperse_done:
                self.initial_disperse_done = True
                for ring in self.rings:
                    for char_id in ring.chars:
                        character = self.term.chars[char_id]
                        ring_start = copy(character.paths[character.path_index("0")].first_waypoint)
                        self.make_disperse_path(char_id, ring_start)
                        first_drift = copy(character.paths[character.path_index("disperse")].first_waypoint)
                        initial = Path(0.3)
                        initial.ease = out_cubic
                        initial.add_waypoint(first_drift)
                        character.add_path("initial", initial, then="disperse")
                        character.activate_scene("disperse")
                        character.activate_path_named("initial")
                        self.term.activate(char_id)
                for char_id in self.outsiders:
                    self.term.chars[char_id].activate_path_named("external")
                    self.term.activate(char_id)
            elif not self.disperse_time:
                self.phase = "spin"
                self.cycles -= 1
                self.spin_time = SPIN_DURATION
                for ring in self.rings:
                    self.spin(ring)
            else:
                self.disperse_time -= 1
        elif self.phase == "spin":
            if not self.spin_time:
                if not self.cycles:
                    self.phase = "final"
                    for char_id in self.term.characters():
                        character = self.term.chars[char_id]
                        self.term.set_visible(char_id, True)
                        character.activate_path_named("home")
                        self.term.activate(char_id)
                        if character.has_path("external"):
                            continue
                        character.activate_scene("disperse")
                else:
                    self.disperse_time = DISPERSE_DURATION
                    for ring in self.rings:
                        self.disperse(ring)
                    self.phase = "disperse"
            else:
                self.spin_time -= 1
        elif self.phase == "final" and not self.term.has_active():
            self.phase = "complete"
        self.term.tick()
        for event in self.term.take_events():
            if event.kind == EventKind.PATH_COMPLETE and event.name == "external":
                self.term.set_visible(event.char_id, False)
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
