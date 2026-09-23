"""highlight: a specular highlight runs diagonally across the text."""
from __future__ import annotations

from tpy import int32, Own, copy

from easing import SequenceEaser, in_out_circ
from engine import Grouping, Scene, Terminal
from graphics import Direction, Gradient, adjust_brightness, hex_colors

HIGHLIGHT_BRIGHTNESS = 1.75
HIGHLIGHT_WIDTH = 8
FINAL_GRADIENT_STOPS = ["8A008A", "00D1FF", "FFFFFF"]
FINAL_GRADIENT_STEPS = [12]


class Highlight:
    term: Terminal
    groups: list[list[int32]]
    easer: SequenceEaser

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.groups = []
        self.easer = SequenceEaser(0, in_out_circ)
        self.build()

    def build(self) -> None:
        self.groups = self.term.grouped(Grouping.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT)
        self.easer = SequenceEaser(len(self.groups), in_out_circ)
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            base = final_colors[copy(character.input_coord)]
            bright = adjust_brightness(base, HIGHLIGHT_BRIGHTNESS)
            # Up to the highlight, across its width, and back down.
            highlight_gradient = Gradient([base, bright, bright, base], [3, HIGHLIGHT_WIDTH, 3])
            character.set_appearance(character.input_symbol, base)
            highlight = Scene("highlight")
            for color in highlight_gradient.spectrum:
                highlight.add_frame(character.input_symbol, 2, color)
            character.add_scene(highlight)
            self.term.set_visible(char_id, True)

    def step(self) -> bool:
        if not self.term.has_active() and self.easer.is_complete():
            return False
        self.easer.step()
        for group in range(self.easer.added_start, self.easer.added_end):
            for char_id in self.groups[group]:
                self.term.chars[char_id].activate_scene("highlight")
                self.term.activate(char_id)
        self.term.tick()
        self.term.events.clear()
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
