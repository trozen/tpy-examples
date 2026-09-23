"""expand: the text expands out of a single point at the center of the canvas."""
from __future__ import annotations

from tpy import Own, copy

from easing import in_out_quart
from engine import EventKind, Path, Scene, Sync, Terminal
from graphics import Direction, Gradient, hex_colors

MOVEMENT_SPEED = 0.35
FINAL_GRADIENT_STOPS = ["8A008A", "00D1FF", "FFFFFF"]
FINAL_GRADIENT_STEPS = [12]


class Expand:
    term: Terminal

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.build()

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        first = final_gradient.spectrum[0]
        center = self.term.canvas.center()
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            character.move_to(center)
            home = copy(character.input_coord)
            path = Path(MOVEMENT_SPEED)
            path.ease = in_out_quart
            path.add_waypoint(home)
            self.term.set_visible(char_id, True)
            self.term.activate(char_id)
            # Moving characters are drawn over the ones already home.
            character.layer = 1
            character.activate_path(character.add_path("expand", path))
            # The color follows the character out from the center.
            final_color = final_colors[home]
            gradient = Gradient([first, final_color], [10])
            symbol = [character.input_symbol]
            scene = Scene("expand", sync=Sync.DISTANCE)
            scene.apply_gradient_to_symbols(symbol, 5, gradient)
            character.add_scene(scene)
            character.activate_scene("expand")

    def step(self) -> bool:
        if not self.term.has_active():
            return False
        self.term.tick()
        for event in self.term.take_events():
            if event.kind == EventKind.PATH_COMPLETE:
                self.term.chars[event.char_id].layer = 0
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
