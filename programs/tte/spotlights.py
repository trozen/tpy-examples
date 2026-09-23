"""spotlights: spotlights search the dark text, then converge and light it all up."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from easing import in_out_quad, in_out_sine
from engine import Path, Terminal
from geometry import Coord, find_coords_in_circle, find_length_of_line
from graphics import Color, Direction, Gradient, adjust_brightness, hex_colors

BEAM_WIDTH_RATIO = 2.0
BEAM_FALLOFF = 0.3
SEARCH_DURATION = 550
SEARCH_SPEED_MIN = 0.35
SEARCH_SPEED_MAX = 0.75
SPOTLIGHT_COUNT = 3
FINAL_GRADIENT_STOPS = ["ab48ff", "e7b2b2", "fffebd"]
FINAL_GRADIENT_STEPS = [12]


class Spotlights:
    term: Terminal
    spotlights: list[int32]
    bright: dict[int32, Color]
    dark: dict[int32, Color]
    illuminated: set[int32]
    illuminate_range: int32
    search_duration: int32
    searching: bool
    complete: bool

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.spotlights = []
        self.bright = {}
        self.dark = {}
        self.illuminated = set()
        self.illuminate_range = 1
        self.search_duration = SEARCH_DURATION
        self.searching = True
        self.complete = False
        self.build()

    def make_spotlight(self) -> None:
        """An invisible spotlight that sweeps between ten random points,
        each at least a quarter of the canvas from the last, forever."""
        minimum_distance = self.term.canvas.right // 4
        start = self.term.canvas.random_coord_outside()
        spotlight = self.term.add_character("O", start)
        self.spotlights.append(spotlight)
        targets: list[Coord] = []
        last = self.term.canvas.random_coord()
        targets.append(last)
        for _ in range(10):
            candidate = self.term.canvas.random_coord()
            while find_length_of_line(last, candidate) < minimum_distance:
                candidate = self.term.canvas.random_coord()
            targets.append(candidate)
            last = candidate
        character = self.term.chars[spotlight]
        for i in range(len(targets)):
            sweep = Path(random.uniform(SEARCH_SPEED_MIN, SEARCH_SPEED_MAX))
            sweep.ease = in_out_quad
            control = self.term.canvas.random_coord_outside()
            target = targets[i]
            sweep.add_curved_waypoint(target, control)
            character.add_path(str(i), sweep, then=str((i + 1) % len(targets)))
        center = Path(0.5)
        center.ease = in_out_sine
        middle = self.term.canvas.center()
        center.add_waypoint(middle)
        character.add_path("center", center)

    def build(self) -> None:
        for _ in range(SPOTLIGHT_COUNT):
            self.make_spotlight()
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            bright = final_colors[copy(character.input_coord)]
            dark = adjust_brightness(bright, 0.2)
            self.bright[char_id] = bright
            self.dark[char_id] = dark
            self.term.set_visible(char_id, True)
            character.set_appearance(character.input_symbol, dark)
        smallest = min(self.term.canvas.right, self.term.canvas.top)
        self.illuminate_range = max(int(min(smallest // BEAM_WIDTH_RATIO, smallest)), 1)
        for spotlight in self.spotlights:
            self.term.chars[spotlight].activate_path_named("0")
            self.term.activate(spotlight)

    def illuminate(self) -> None:
        """Light the characters within range of a spotlight, fading towards
        the edge of its beam, and darken the ones it has left."""
        range_ = self.illuminate_range
        in_range: set[int32] = set()
        for spotlight in self.spotlights:
            position = copy(self.term.chars[spotlight].coord)
            for coord in find_coords_in_circle(position, range_):
                char_id = self.term.at(coord)
                if char_id >= 0 and not self.term.chars[char_id].is_fill:
                    in_range.add(char_id)
        for char_id in self.illuminated:
            if char_id not in in_range:
                character = self.term.chars[char_id]
                character.set_appearance(character.input_symbol, self.dark[char_id])
        for char_id in in_range:
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            distance = -1.0
            for spotlight in self.spotlights:
                position = copy(self.term.chars[spotlight].coord)
                length = find_length_of_line(position, home)
                if distance < 0 or length < distance:
                    distance = length
            if distance > range_ * (1 - BEAM_FALLOFF):
                brightness = max(1 - (distance - range_ * (1 - BEAM_FALLOFF))
                                 / (range_ * BEAM_FALLOFF), 0.2)
                character.set_appearance(character.input_symbol,
                                         adjust_brightness(self.bright[char_id], brightness))
            else:
                character.set_appearance(character.input_symbol, self.bright[char_id])
        self.illuminated = in_range

    def step(self) -> bool:
        if self.complete:
            return False
        self.illuminate()
        if self.searching:
            self.search_duration -= 1
            if not self.search_duration:
                for spotlight in self.spotlights:
                    self.term.chars[spotlight].activate_path_named("center")
                self.searching = False
        moving = False
        for spotlight in self.spotlights:
            if self.term.chars[spotlight].active_path >= 0:
                moving = True
        if not moving:
            # Converged: one spotlight is left, and its beam widens over the text.
            while len(self.spotlights) > 1:
                self.spotlights.pop()
            self.illuminate_range += 1
            if self.illuminate_range > max(self.term.canvas.right, self.term.canvas.top) // 1.5:
                self.complete = True
        self.term.tick()
        self.term.events.clear()
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
