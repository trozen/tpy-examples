"""crumble: the text weakens and crumbles to dust, which is vacuumed up and set back in place."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from easing import out_bounce, out_quint
from engine import EventKind, Path, Scene, Sync, Terminal, randint
from geometry import Coord
from graphics import Color, Direction, Gradient, adjust_brightness, hex_colors

DUST_SYMBOLS = ["*", ".", ","]
FINAL_GRADIENT_STOPS = ["5ce1ff", "ff8c00"]
FINAL_GRADIENT_STEPS = [12]


class Crumble:
    term: Terminal
    pending: list[int32]
    unvacuumed: list[int32]
    fall_delay: int32
    max_fall_delay: int32
    min_fall_delay: int32
    fall_group_maxsize: int32
    reset: bool
    stage: str

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.pending = []
        self.unvacuumed = []
        self.fall_delay = 12
        self.max_fall_delay = 12
        self.min_fall_delay = 9
        self.fall_group_maxsize = 1
        self.reset = False
        self.stage = "falling"
        self.build()

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.DIAGONAL)
        white = Color(255, 255, 255)
        center = self.term.canvas.center()
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            symbol = character.input_symbol
            final_color = final_colors[home]
            weak = adjust_brightness(final_color, 0.65)
            dust = adjust_brightness(final_color, 0.55)
            self.term.set_visible(char_id, True)
            initial = Scene("initial")
            initial.add_frame(symbol, 1, weak)
            character.add_scene(initial)
            character.activate_scene("initial")
            # It fades, falls to the bottom as dust, is sucked up to the top
            # edge and dropped back into place, where it flashes white.
            fall = Path(0.65)
            fall.ease = out_bounce
            fall.add_waypoint(Coord(home.column, self.term.canvas.bottom))
            character.add_path("fall", fall)
            symbols = [symbol]
            weaken = Scene("weaken")
            weaken.apply_gradient_to_symbols(symbols, 4, Gradient([weak, dust], [9]))
            character.add_scene(weaken)
            top = Path(1)
            top.ease = out_quint
            top.add_curved_waypoint(Coord(home.column, self.term.canvas.top), center)
            character.add_path("top", top)
            back = Path(1)
            back.add_waypoint(home)
            character.add_path("input", back, end_scene="strengthen_flash")
            flash = Scene("strengthen_flash")
            flash.apply_gradient_to_symbols(symbols, 4, Gradient([final_color, white], [6]))
            character.add_scene(flash)
            strengthen = Scene("strengthen")
            strengthen.apply_gradient_to_symbols(symbols, 4, Gradient([white, final_color], [9]))
            character.add_scene(strengthen)
            dust_scene = Scene("dust", sync=Sync.DISTANCE)
            for _ in range(5):
                dust_scene.add_frame(random.choice(DUST_SYMBOLS), 1, dust)
            character.add_scene(dust_scene)
            self.pending.append(char_id)
        random.shuffle(self.pending)
        self.unvacuumed = self.term.characters()
        random.shuffle(self.unvacuumed)

    def step(self) -> bool:
        if self.stage == "complete":
            return False
        if self.stage == "falling":
            if self.pending:
                if self.fall_delay == 0:
                    # Ever bigger groups, ever faster, until the whole text is down.
                    for _ in range(randint(1, self.fall_group_maxsize)):
                        if self.pending:
                            char_id = self.pending.pop(0)
                            self.term.chars[char_id].activate_scene("weaken")
                            self.term.activate(char_id)
                    self.fall_delay = randint(self.min_fall_delay, self.max_fall_delay)
                    if randint(1, 10) > 4:
                        self.fall_group_maxsize += 1
                        self.min_fall_delay = max(0, self.min_fall_delay - 1)
                        self.max_fall_delay = max(0, self.max_fall_delay - 1)
                else:
                    self.fall_delay -= 1
            if not self.pending and not self.term.has_active():
                self.stage = "vacuuming"
        elif self.stage == "vacuuming":
            if self.unvacuumed:
                for _ in range(randint(3, 10)):
                    if self.unvacuumed:
                        char_id = self.unvacuumed.pop(0)
                        self.term.chars[char_id].activate_path_named("top")
                        self.term.activate(char_id)
            if not self.term.has_active():
                self.stage = "resetting"
        elif self.stage == "resetting":
            if not self.reset:
                # Its own name: tpy would reuse the vacuuming branch's declaration (README).
                for returning in self.term.characters():
                    self.term.chars[returning].activate_path_named("input")
                    self.term.activate(returning)
                self.reset = True
            if not self.term.has_active():
                self.stage = "complete"
        self.term.tick()
        for event in self.term.take_events():
            if event.kind != EventKind.SCENE_COMPLETE:
                continue
            character = self.term.chars[event.char_id]
            if event.name == "weaken":
                character.activate_path_named("fall")
                character.layer = 1
                character.activate_scene("dust")
            elif event.name == "strengthen_flash":
                character.activate_scene("strengthen")
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
