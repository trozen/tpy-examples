"""blackhole: a black hole forms, consumes the text as a starfield, collapses and explodes it back."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from easing import in_cubic, in_expo, in_out_sine, out_expo
from engine import EventKind, Path, Scene, Sync, Terminal, randint
from geometry import Coord, TERMINAL_ROW_SCALE, find_coords_on_circle
from graphics import Color, Direction, Gradient, choose_color, hex_color, hex_colors

BLACKHOLE_COLOR = "ffffff"
STAR_COLORS = ["ffcc0d", "ff7326", "ff194d", "bf2669", "702a8c", "049dbf"]
STAR_SYMBOLS = ["*", "'", "`", "¤", "•", "°", "·"]
UNSTABLE_SYMBOLS = ["◦", "◎", "◉", "●", "◉", "◎", "◦"]
FINAL_GRADIENT_STOPS = ["8a008a", "00d1ff", "ffffff"]
FINAL_GRADIENT_STEPS = [9]


class Blackhole:
    term: Terminal
    radius: int32
    ring: list[int32]  # the characters that form the black hole's ring
    in_ring: set[int32]
    awaiting_ring: list[int32]
    awaiting_consumption: list[int32]
    point_char: int32
    formation_delay: int32
    delay: int32
    phase: str
    final_colors: dict[Coord, Color]

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.radius = TERMINAL_ROW_SCALE * max(min(round(self.term.canvas.width() * 0.3),
                                                   round(self.term.canvas.height() * 0.2)), 3)
        self.ring = []
        self.in_ring = set()
        self.awaiting_ring = []
        self.awaiting_consumption = []
        self.point_char = -1
        self.formation_delay = 0
        self.delay = 0
        self.phase = "forming"
        self.final_colors = {}
        self.build()

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        self.final_colors = self.term.text_colors(final_gradient, Direction.DIAGONAL)
        self.prepare()
        self.formation_delay = max(100 // len(self.ring), 6)
        self.delay = self.formation_delay
        for char_id in self.ring:
            self.awaiting_ring.append(char_id)

    def prepare(self) -> None:
        """Pick the ring's characters and scatter the rest as stars."""
        star_stops = [hex_color("4a4a4d"), hex_color("ffffff")]
        star_gradient = Gradient(star_stops, [6])
        black = Color(0, 0, 0)
        ring_size = self.radius * 3 // TERMINAL_ROW_SCALE
        available = self.term.characters()
        while len(self.ring) < ring_size and available:
            char_id = available.pop(randint(0, len(available) - 1))
            self.ring.append(char_id)
            self.in_ring.add(char_id)
        center = self.term.canvas.center()
        positions = find_coords_on_circle(center, self.radius, len(self.ring))
        blackhole_color = hex_color(BLACKHOLE_COLOR)
        for i in range(len(self.ring)):
            character = self.term.chars[self.ring[i]]
            form = Path(0.7)
            form.ease = in_out_sine
            form.add_waypoint(positions[i])
            character.add_path("blackhole", form)
            dot = Scene("blackhole")
            dot.add_frame("*", 1, blackhole_color)
            character.add_scene(dot)
            # Round and round the ring, each character starting at its own place.
            rotation = Path(0.45, loop=True)
            for j in range(len(positions)):
                rotation.add_waypoint(positions[(i + j) % len(positions)])
            character.add_path("blackhole_rotation", rotation)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            self.term.set_visible(char_id, True)
            star_symbol = random.choice(STAR_SYMBOLS)
            star_color = choose_color(star_gradient.spectrum)
            star = Scene("star")
            star.add_frame(star_symbol, 1, star_color)
            character.add_scene(star)
            character.activate_scene("star")
            if char_id in self.in_ring:
                continue
            scattered = self.term.canvas.random_coord()
            character.move_to(scattered)
            # Stars fall into the singularity, fading to black on the way.
            fall = Path(random.uniform(0.17, 0.3))
            fall.ease = in_expo
            fall.add_waypoint(center)
            character.add_path("singularity", fall, scene="consumed")
            consumed = Scene("consumed", sync=Sync.DISTANCE)
            fade = Gradient([star_color, black], [10])
            for color in fade.spectrum:
                consumed.add_frame(star_symbol, 1, color)
            consumed.add_plain_frame(" ", 1)
            character.add_scene(consumed)
            self.awaiting_consumption.append(char_id)
        random.shuffle(self.awaiting_consumption)

    def collapse(self) -> None:
        """The ring swells, then falls into its center; one character flickers there."""
        center = self.term.canvas.center()
        positions = find_coords_on_circle(center, self.radius + 3 * TERMINAL_ROW_SCALE,
                                          len(self.ring))
        star_colors = hex_colors(STAR_COLORS)
        for char_id in self.ring:
            character = self.term.chars[char_id]
            swell = Path(0.2)
            swell.ease = in_expo
            swell_to = positions.pop(0)
            swell.add_waypoint(swell_to)
            fall = Path(0.3)
            fall.ease = in_expo
            fall.add_waypoint(center)
            if self.point_char < 0:
                point = Scene("point")
                for _ in range(3):
                    for symbol in UNSTABLE_SYMBOLS:
                        point.add_frame(symbol, 3, choose_color(star_colors))
                character.add_scene(point)
                character.add_path("collapse", fall, end_scene="point")
                self.point_char = char_id
            else:
                character.add_path("collapse", fall)
            character.activate_path(character.add_path("swell", swell, then="collapse"))
            self.term.activate(char_id)

    def explode(self) -> None:
        """Every character bursts out near its place, then settles into it."""
        star_colors = hex_colors(STAR_COLORS)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            around = find_coords_on_circle(home, 3 * TERMINAL_ROW_SCALE, 5)
            nearby = around[randint(0, 4)]
            burst = Path(randint(3, 4) / 10)
            burst.ease = out_expo
            burst.add_waypoint(nearby)
            settle = Path(randint(4, 6) / 100)
            settle.ease = in_cubic
            settle.add_waypoint(home)
            explode_color = choose_color(star_colors)
            flash = Scene("explode")
            flash.add_frame(character.input_symbol, 1, explode_color)
            character.add_scene(flash)
            cooling = Scene("cooling")
            final_color = self.final_colors[home]
            cooling_gradient = Gradient([explode_color, final_color], [10])
            symbol = [character.input_symbol]
            cooling.apply_gradient_to_symbols(symbol, 20, cooling_gradient)
            character.add_scene(cooling)
            character.add_path("settle", settle, scene="cooling")
            character.activate_scene("explode")
            character.activate_path(character.add_path("burst", burst, then="settle"))
            self.term.activate(char_id)

    def ring_is_still(self) -> bool:
        for char_id in self.ring:
            character = self.term.chars[char_id]
            if character.active_path >= 0 or character.active_scene >= 0:
                return False
        return True

    def step(self) -> bool:
        if not self.term.has_active() and self.phase == "complete":
            return False
        if self.phase == "forming":
            if self.awaiting_ring:
                if not self.delay:
                    char_id = self.awaiting_ring.pop(0)
                    character = self.term.chars[char_id]
                    character.layer = 1
                    character.activate_path_named("blackhole")
                    character.activate_scene("blackhole")
                    self.term.activate(char_id)
                    self.delay = self.formation_delay
                else:
                    self.delay -= 1
            elif not self.term.has_active():
                for char_id in self.ring:
                    self.term.chars[char_id].activate_path_named("blackhole_rotation")
                    self.term.activate(char_id)
                self.phase = "consuming"
        elif self.phase == "consuming":
            if self.awaiting_consumption:
                for char_id in self.awaiting_consumption:
                    self.term.chars[char_id].layer = 2
                    self.term.chars[char_id].activate_path_named("singularity")
                    self.term.activate(char_id)
                self.awaiting_consumption.clear()
            elif self.term.only_active_among(self.in_ring):
                self.phase = "collapsing"
        elif self.phase == "collapsing":
            self.collapse()
            self.phase = "exploding"
        elif self.phase == "exploding" and self.ring_is_still():
            self.explode()
            self.phase = "complete"
        self.term.tick()
        for event in self.term.take_events():
            if (event.kind == EventKind.PATH_COMPLETE and event.name == "collapse"
                    and event.char_id == self.point_char):
                self.term.chars[event.char_id].layer = 3
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
