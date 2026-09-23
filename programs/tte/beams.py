"""beams: beams of light sweep the rows and columns, leaving the text lit behind them."""
from __future__ import annotations

import random
from typing import Final

from tpy import int32, Own, copy

from engine import Grouping, Scene, Terminal, randint
from graphics import Color, Direction, Gradient, adjust_brightness, hex_colors

BEAM_ROW_SYMBOLS = ["▂", "▁", "_"]
BEAM_COLUMN_SYMBOLS = ["▌", "▍", "▎", "▏"]
BEAM_DELAY = 6
BEAM_ROW_SPEED_RANGE: Final[tuple[int32, int32]] = (15, 60)
BEAM_COLUMN_SPEED_RANGE: Final[tuple[int32, int32]] = (9, 15)
BEAM_GRADIENT_STOPS = ["ffffff", "00D1FF", "8A008A"]
BEAM_GRADIENT_STEPS = [2, 6]
BEAM_GRADIENT_FRAMES = 2
FINAL_GRADIENT_STOPS = ["8A008A", "00D1FF", "ffffff"]
FINAL_GRADIENT_STEPS = [12]
FINAL_GRADIENT_FRAMES = 4
FINAL_WIPE_SPEED = 3


class BeamGroup:
    """One row or column, lit character by character as a beam crosses it."""
    chars: list[int32]
    scene: str
    speed: float
    counter: float
    next_index: int32

    def __init__(self, term: Terminal, chars: list[int32], direction: str) -> None:
        if direction == "row":
            ordered = sorted(chars, key=lambda i: term.chars[i].input_coord.column)
            speed = randint(BEAM_ROW_SPEED_RANGE[0], BEAM_ROW_SPEED_RANGE[1]) * 0.1
        else:
            ordered = sorted(chars, key=lambda i: term.chars[i].input_coord.row)
            speed = randint(BEAM_COLUMN_SPEED_RANGE[0], BEAM_COLUMN_SPEED_RANGE[1]) * 0.1
        if random.choice([True, False]):
            ordered.reverse()
        self.chars = ordered
        self.speed = speed
        self.scene = "beam_" + direction
        self.counter = 0.0
        self.next_index = 0

    def complete(self) -> bool:
        return self.next_index == len(self.chars)


class Beams:
    term: Terminal
    groups: list[BeamGroup]
    pending: list[int32]
    active: list[int32]
    delay: int32
    phase: str
    wipe_groups: list[list[int32]]
    next_wipe: int32

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.groups = []
        self.pending = []
        self.active = []
        self.delay = 0
        self.phase = "beams"
        self.wipe_groups = []
        self.next_wipe = 0
        self.build()

    def build(self) -> None:
        self.wipe_groups = self.term.grouped(Grouping.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT)
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        beam_stops = hex_colors(BEAM_GRADIENT_STOPS)
        beam_gradient = Gradient(beam_stops, BEAM_GRADIENT_STEPS)
        for row in self.term.grouped(Grouping.ROW_TOP_TO_BOTTOM, include_fill=True):
            self.groups.append(BeamGroup(self.term, row, "row"))
        for column in self.term.grouped(Grouping.COLUMN_LEFT_TO_RIGHT, include_fill=True):
            self.groups.append(BeamGroup(self.term, column, "column"))
        for char_id in self.term.characters(include_fill=True):
            character = self.term.chars[char_id]
            symbol = [character.input_symbol]
            if character.is_fill:
                final_color = Color(0, 0, 0)
            else:
                final_color = final_colors[copy(character.input_coord)]
            faded_color = adjust_brightness(final_color, 0.3)
            fade_gradient = Gradient([final_color, faded_color], [10])
            brighten_gradient = Gradient([faded_color, final_color], [10])

            # A beam passes over the character, which then dims to wait for the wipe.
            row_scene = Scene("beam_row")
            row_scene.apply_gradient_to_symbols(BEAM_ROW_SYMBOLS, BEAM_GRADIENT_FRAMES,
                                                beam_gradient)
            row_scene.apply_gradient_to_symbols(symbol, 2, fade_gradient)
            character.add_scene(row_scene)
            column_scene = Scene("beam_column")
            column_scene.apply_gradient_to_symbols(BEAM_COLUMN_SYMBOLS, BEAM_GRADIENT_FRAMES,
                                                   beam_gradient)
            column_scene.apply_gradient_to_symbols(symbol, 2, fade_gradient)
            character.add_scene(column_scene)
            brighten_scene = Scene("brighten")
            brighten_scene.apply_gradient_to_symbols(symbol, FINAL_GRADIENT_FRAMES,
                                                     brighten_gradient)
            character.add_scene(brighten_scene)
        for i in range(len(self.groups)):
            self.pending.append(i)
        random.shuffle(self.pending)

    def light_next(self, group_id: int32) -> None:
        group = self.groups[group_id]
        group.counter -= 1
        char_id = group.chars[group.next_index]
        group.next_index += 1
        character = self.term.chars[char_id]
        if character.active_scene >= 0:
            # Already lit by a crossing beam: restart that beam rather than start a new one.
            character.scenes[character.active_scene].reset()
            character.activate_scene(group.scene)
            return
        self.term.set_visible(char_id, True)
        character.activate_scene(group.scene)
        self.term.activate(char_id)

    def step(self) -> bool:
        if self.phase == "complete" and not self.term.has_active():
            return False
        if self.phase == "beams":
            if not self.delay:
                if self.pending:
                    for _ in range(randint(1, 5)):
                        if self.pending:
                            self.active.append(self.pending.pop(0))
                self.delay = BEAM_DELAY
            else:
                self.delay -= 1
            for group_id in self.active:
                self.groups[group_id].counter += self.groups[group_id].speed
                for _ in range(int(self.groups[group_id].counter)):
                    if not self.groups[group_id].complete():
                        self.light_next(group_id)
            still_lighting: list[int32] = []
            for group_id in self.active:
                if not self.groups[group_id].complete():
                    still_lighting.append(group_id)
            self.active = still_lighting
            if not self.pending and not self.active and not self.term.has_active():
                self.phase = "final_wipe"
        elif self.phase == "final_wipe":
            if self.next_wipe < len(self.wipe_groups):
                for _ in range(FINAL_WIPE_SPEED):
                    if self.next_wipe == len(self.wipe_groups):
                        break
                    for char_id in self.wipe_groups[self.next_wipe]:
                        self.term.chars[char_id].activate_scene("brighten")
                        self.term.set_visible(char_id, True)
                        self.term.activate(char_id)
                    self.next_wipe += 1
            else:
                self.phase = "complete"
        self.term.tick()
        self.term.events.clear()
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
