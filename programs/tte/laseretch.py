"""laseretch: a laser etches the text in along a winding path, throwing sparks."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from easing import out_sine
from engine import EventKind, ParticlePool, Path, Scene, Terminal, randint
from geometry import Coord
from graphics import Direction, Gradient, hex_color, hex_colors
from spanningtree import recursive_backtracker_order

ETCH_SPEED = 1
ETCH_DELAY = 1
COOL_GRADIENT_STOPS = ["ffe680", "ff7b00"]
LASER_GRADIENT_STOPS = ["ffffff", "376cff"]
SPARK_GRADIENT_STOPS = ["ffffff", "ffe680", "ff7b00", "1a0900"]
SPARK_COOLING_FRAMES = 7
SPARK_SYMBOLS = [".", ",", "*"]
FINAL_GRADIENT_STOPS = ["8a008a", "00d1ff", "ffffff"]
FINAL_GRADIENT_STEPS = [8]


class LaserEtch:
    term: Terminal
    pending: list[int32]
    beam: list[int32]
    sparks: ParticlePool
    position: Coord
    char_delay: int32

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.pending = []
        self.beam = []
        self.sparks = ParticlePool(SPARK_SYMBOLS)
        self.position = Coord(0, 0)
        self.char_delay = 0
        self.build()
        self.build_laser()

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        spark_yellow = hex_color("ffe680")
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            # Etched in as a hot spark, the character cools to its final color.
            cool_stops = hex_colors(COOL_GRADIENT_STOPS)
            final_color = final_colors[copy(character.input_coord)]
            cool_stops.append(final_color)
            cool_gradient = Gradient(cool_stops, [8])
            spawn = Scene("spawn")
            spawn.add_frame("^", 3, spark_yellow)
            for color in cool_gradient.spectrum:
                spawn.add_frame(character.input_symbol, 3, color)
            character.add_scene(spawn)
            character.activate_scene("spawn")
        start_coord = self.term.canvas.random_coord_in_text()
        self.pending = recursive_backtracker_order(self.term, self.term.at(start_coord))

    def build_laser(self) -> None:
        """A diagonal beam from the bottom left, its colors cycling up it, and
        a pool of sparks."""
        laser_stops = hex_colors(LASER_GRADIENT_STOPS)
        laser_gradient = Gradient(laser_stops, [6], loop=True)
        spark_stops = hex_colors(SPARK_GRADIENT_STOPS)
        spark_gradient = Gradient(spark_stops, [3, 8])
        for spark in self.sparks.fill(self.term, 2000):
            character = self.term.chars[spark]
            character.layer = 2
            glow = Scene("spark")
            for color in spark_gradient.spectrum:
                glow.add_frame(character.input_symbol, SPARK_COOLING_FRAMES, color)
            character.add_scene(glow)
        row = 0
        while row <= self.term.canvas.top:
            symbol = "/" if self.beam else "*"
            beam_char = self.term.add_character(symbol, Coord(row, row))
            character = self.term.chars[beam_char]
            character.layer = 2
            self.term.set_visible(beam_char, True)
            laser = Scene("laser", looping=True)
            for i in range(len(laser_gradient.spectrum)):
                # Each character of the beam starts one color further along.
                laser.add_frame(symbol, 3, laser_gradient.spectrum[(i + row) % len(laser_gradient.spectrum)])
            character.add_scene(laser)
            character.activate_scene("laser")
            self.beam.append(beam_char)
            self.term.activate(beam_char)
            row += 1

    def reposition(self, target: Coord) -> None:
        self.position = target
        for i in range(len(self.beam)):
            self.term.chars[self.beam[i]].move_to(Coord(target.column + i, target.row + i))
        self.emit_spark()

    def emit_spark(self) -> None:
        spark, _ = self.sparks.acquire(self.term)
        character = self.term.chars[spark]
        character.move_to(self.position)
        fall = Path(0.3)
        fall.ease = out_sine
        target = Coord(randint(self.position.column - 20, self.position.column + 20),
                       self.term.canvas.bottom)
        control = Coord(target.column, self.position.row + randint(-10, 20))
        fall.add_curved_waypoint(target, control)
        character.activate_path(character.add_path("fall", fall))
        character.activate_scene("spark")
        self.term.set_visible(spark, True)
        self.term.activate(spark)

    def step(self) -> bool:
        if not self.pending and not self.term.has_active():
            return False
        if not self.char_delay:
            for _ in range(ETCH_SPEED):
                if not self.pending:
                    break
                char_id = self.pending.pop(0)
                # The laser skips the gaps between words.
                while self.term.chars[char_id].is_fill and self.pending:
                    char_id = self.pending.pop(0)
                self.term.set_visible(char_id, True)
                self.term.activate(char_id)
                target = copy(self.term.chars[char_id].input_coord)
                self.reposition(target)
            self.char_delay = ETCH_DELAY
        else:
            self.char_delay -= 1
        if self.pending:
            for beam_char in self.beam:
                self.term.activate(beam_char)
        else:
            for beam_char in self.beam:
                self.term.chars[beam_char].deactivate_scene()
                self.term.set_visible(beam_char, False)
        self.term.tick()
        for event in self.term.take_events():
            if event.kind == EventKind.SCENE_COMPLETE and event.name == "spark":
                self.sparks.reclaim(self.term, event.char_id)
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
