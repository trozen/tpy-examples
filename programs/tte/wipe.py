"""wipe: the text is wiped onto the canvas diagonally, from the top left corner."""
from __future__ import annotations

from tpy import int32, Own, copy

from easing import SequenceEaser, in_out_circ
from engine import Grouping, Scene, Terminal
from graphics import Direction, Gradient, hex_colors

WIPE_DELAY = 0
FINAL_GRADIENT_STOPS = ["833ab4", "fd1d1d", "fcb045"]
FINAL_GRADIENT_STEPS = [12]
FINAL_GRADIENT_FRAMES = 3


class Wipe:
    term: Terminal
    groups: list[list[int32]]
    easer: SequenceEaser
    delay: int32

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.groups = []
        self.easer = SequenceEaser(0, in_out_circ)
        self.delay = WIPE_DELAY
        self.build()

    def build(self) -> None:
        self.groups = self.term.grouped(Grouping.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT)
        self.easer = SequenceEaser(len(self.groups), in_out_circ)
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        first = final_gradient.spectrum[0]
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            final_color = final_colors[copy(character.input_coord)]
            wipe_gradient = Gradient([first, final_color], FINAL_GRADIENT_STEPS)
            symbol = [character.input_symbol]
            wipe = Scene("wipe")
            wipe.apply_gradient_to_symbols(symbol, FINAL_GRADIENT_FRAMES, wipe_gradient)
            character.add_scene(wipe)

    def step(self) -> bool:
        if not self.term.has_active() and self.easer.is_complete():
            return False
        if self.delay == 0:
            self.easer.step()
            for group in range(self.easer.added_start, self.easer.added_end):
                for char_id in self.groups[group]:
                    self.term.chars[char_id].activate_scene("wipe")
                    self.term.set_visible(char_id, True)
                    self.term.activate(char_id)
            for group in range(self.easer.removed_start, self.easer.removed_end):
                for char_id in self.groups[group]:
                    character = self.term.chars[char_id]
                    character.deactivate_scene()
                    character.scenes[character.scene_index("wipe")].reset()
                    self.term.set_visible(char_id, False)
            self.delay = WIPE_DELAY
        else:
            self.delay -= 1
        self.term.tick()
        self.term.events.clear()
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
