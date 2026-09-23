"""fireworks: shells of characters launch, burst and fall into place as the text."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from easing import in_out_quart, out_circ, out_expo
from engine import Path, Scene, Sync, Terminal, randint
from geometry import Coord, extrapolate_along_ray, find_coords_in_circle
from graphics import Color, Direction, Gradient, choose_color, hex_colors

FIREWORK_COLORS = ["88f7e2", "44d492", "f5eb67", "ffa15c", "fa233e"]
FIREWORK_SYMBOL = "o"
FIREWORK_VOLUME = 0.05  # the share of the text in each shell
LAUNCH_DELAY = 45
EXPLODE_DISTANCE = 0.2
FINAL_GRADIENT_STOPS = ["8a008a", "00d1ff", "ffffff"]
FINAL_GRADIENT_STEPS = [12]


class Fireworks:
    term: Terminal
    shells: list[list[int32]]
    volume: int32
    explode_distance: int32
    launch_delay: int32

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.shells = []
        self.volume = max(1, round(FIREWORK_VOLUME * len(self.term.characters())))
        self.explode_distance = min(15, max(1, round(self.term.canvas.right * EXPLODE_DISTANCE)))
        self.launch_delay = 0
        self.prepare_paths()
        self.prepare_scenes()

    def prepare_paths(self) -> None:
        """Group the text into shells, each launched from a random point on the
        bottom edge, bursting at its apex and falling to the text."""
        shell: list[int32] = []
        origin = Coord(0, 0)
        burst: list[Coord] = []
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            if len(shell) == self.volume or not shell:
                # TTE starts with an empty shell, which is launched last.
                self.shells.append(shell)
                shell = []
                origin_column = randint(0, self.term.canvas.right - 1)
                origin_row = randint(home.row, self.term.canvas.top)
                origin = Coord(origin_column, origin_row)
                burst = find_coords_in_circle(origin, self.explode_distance)
            character.move_to(Coord(origin.column, self.term.canvas.bottom))
            apex = Path(0.35)
            apex.ease = out_expo
            apex.add_waypoint(origin)
            explode = Path(random.uniform(0.2, 0.4))
            explode.ease = out_circ
            burst_to = burst[randint(0, len(burst) - 1)]
            explode.add_waypoint(burst_to)
            bloom_control = extrapolate_along_ray(origin, burst_to, self.explode_distance // 2)
            bloom = Coord(bloom_control.column, max(1, bloom_control.row - 7))
            explode.add_curved_waypoint(bloom, bloom_control)
            fall = Path(0.6)
            fall.ease = in_out_quart
            fall.add_curved_waypoint(home, Coord(bloom.column, 1))
            character.add_path("apex", apex, then="explode", end_scene="bloom", start_layer=2)
            character.add_path("explode", explode, then="fall", start_layer=2)
            character.add_path("fall", fall, scene="fall", start_layer=2, end_layer=0)
            character.activate_path_named("apex")
            shell.append(char_id)
        if shell:
            self.shells.append(shell)

    def prepare_scenes(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.HORIZONTAL)
        firework_colors = hex_colors(FIREWORK_COLORS)
        white = Color(255, 255, 255)
        for shell in self.shells:
            shell_color = choose_color(firework_colors)
            shell_gradient = Gradient([shell_color, white, shell_color], [5])
            for char_id in shell:
                character = self.term.chars[char_id]
                launch = Scene("launch", looping=True)
                launch.add_frame(FIREWORK_SYMBOL, 2, shell_color)
                launch.add_frame(FIREWORK_SYMBOL, 1, white)
                character.add_scene(launch)
                bloom = Scene("bloom", sync=Sync.STEP)
                for color in shell_gradient.spectrum:
                    bloom.add_frame(character.input_symbol, 2, color)
                character.add_scene(bloom)
                fall = Scene("fall")
                final_color = final_colors[copy(character.input_coord)]
                fall_gradient = Gradient([shell_color, final_color], [15])
                symbol = [character.input_symbol]
                fall.apply_gradient_to_symbols(symbol, 10, fall_gradient)
                character.add_scene(fall)
                character.activate_scene("launch")

    def step(self) -> bool:
        if not self.shells and not self.term.has_active():
            return False
        if self.shells and self.launch_delay <= 0:
            shell = self.shells.pop()
            for char_id in shell:
                self.term.set_visible(char_id, True)
                self.term.activate(char_id)
            self.launch_delay = int(LAUNCH_DELAY * random.uniform(0.5, 1.5))
        self.launch_delay -= 1
        self.term.tick()
        self.term.events.clear()
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
