"""burn: fire spreads through the text along a random spanning tree, trailing smoke."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from engine import EventKind, ParticlePool, Path, Scene, Terminal, randint
from geometry import Coord
from graphics import Direction, Gradient, hex_color, hex_colors
from spanningtree import prims_order

STARTING_COLOR = "837373"
BURN_COLORS = ["ffffff", "fff75d", "fe650d", "8a003c", "510100"]
BURN_SYMBOLS = ["'", ".", "▖", "▙", "█", "▜", "▀", "▝", "."]
SMOKE_SYMBOLS = [".", ",", "'", "`", "#", "*"]
SMOKE_POOL_SIZE = 2000
SMOKE_CHANCE = 0.5
FINAL_GRADIENT_STOPS = ["00c3ff", "ffff1c"]
FINAL_GRADIENT_STEPS = [12]


class Burn:
    term: Terminal
    link_order: list[int32]
    smoke: ParticlePool

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        # The fire starts at a random cell of the text.
        start_coord = self.term.canvas.random_coord_in_text()
        start = self.term.at(start_coord)
        self.link_order = []
        self.smoke = ParticlePool(SMOKE_SYMBOLS, SMOKE_POOL_SIZE)
        smoke_stops = [hex_color("504F4F"), hex_color("C7C7C7")]
        smoke_gradient = Gradient(smoke_stops, [9])
        for particle in self.smoke.fill(self.term, SMOKE_POOL_SIZE):
            character = self.term.chars[particle]
            smoke_scene = Scene("smoke")
            for color in smoke_gradient.spectrum:
                smoke_scene.add_frame(character.input_symbol, 10, color)
            character.add_scene(smoke_scene)
            character.layer = 2
        self.build(start)

    def build(self, start: int32) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        burn_stops = hex_colors(BURN_COLORS)
        fire_gradient = Gradient(burn_stops, [10])
        embers = fire_gradient.spectrum[len(fire_gradient.spectrum) - 1]
        self.link_order = prims_order(self.term, start)
        starting_color = hex_color(STARTING_COLOR)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            self.term.set_visible(char_id, True)
            character.set_appearance(character.input_symbol, starting_color)
            burn = Scene("burn")
            burn.apply_gradient_to_symbols(BURN_SYMBOLS, 4, fire_gradient)
            character.add_scene(burn)
            # Once burnt, the character cools from embers to its final color.
            final = Scene("final")
            final_color = final_colors[copy(character.input_coord)]
            cooling = Gradient([embers, final_color], [8])
            for color in cooling.spectrum:
                final.add_frame(character.input_symbol, 4, color)
            character.add_scene(final)

    def emit_smoke(self, burnt: int32) -> None:
        """Maybe send a wisp of smoke up from the character that just burnt."""
        if random.random() > SMOKE_CHANCE:
            return
        origin = copy(self.term.chars[burnt].input_coord)
        particle, _ = self.smoke.acquire(self.term)
        if particle < 0:
            return
        character = self.term.chars[particle]
        character.move_to(origin)
        character.scenes[0].reset()
        rise = Path(0.5)
        column = randint(origin.column - 4, origin.column + 4)
        rise.add_waypoint(Coord(column, self.term.canvas.top + 1))
        character.activate_path(character.add_path("rise", rise))
        character.activate_scene("smoke")
        self.term.set_visible(particle, True)
        self.term.activate(particle)

    def step(self) -> bool:
        if not self.link_order and not self.term.has_active():
            return False
        for _ in range(randint(2, 4)):
            if self.link_order:
                char_id = self.link_order.pop(0)
                if self.term.chars[char_id].is_fill:
                    continue
                self.term.chars[char_id].activate_scene("burn")
                self.term.activate(char_id)
        self.update()
        return True

    def update(self) -> None:
        self.term.tick()
        events = self.term.take_events()
        for event in events:
            if event.kind != EventKind.SCENE_COMPLETE:
                continue
            if event.name == "burn":
                self.term.chars[event.char_id].activate_scene("final")
                self.emit_smoke(event.char_id)
            elif event.name == "smoke":
                self.smoke.reclaim(self.term, event.char_id)
        self.term.prune()

    def frame(self) -> str:
        return self.term.render()
