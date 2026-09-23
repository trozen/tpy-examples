"""vhstape: lines of the text glitch and tear like a worn VHS tape, then it is redrawn."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from engine import EventKind, Grouping, Path, Scene, Sync, Terminal, randint
from geometry import Coord
from graphics import Color, Direction, Gradient, choose_color, hex_colors

GLITCH_LINE_COLORS = ["ffffff", "ff0000", "00ff00", "0000ff", "ffffff"]
NOISE_COLORS = ["1e1e1f", "3c3b3d", "6d6c70", "a2a1a6", "cbc9cf", "ffffff"]
SNOW_SYMBOLS = ["#", "*", ".", ":"]
GLITCH_LINE_CHANCE = 0.05
NOISE_CHANCE = 0.004
TOTAL_GLITCH_TIME = 600
FINAL_GRADIENT_STOPS = ["ab48ff", "e7b2b2", "fffebd"]
FINAL_GRADIENT_STEPS = [12]


class VHSTape:
    term: Terminal
    lines: list[list[int32]]  # the text's rows, bottom up; each glitches as a unit
    wave_top: int32  # 0: no glitch wave running
    wave_lines: list[int32]
    glitch_lines: list[int32]
    glitching_steps: int32
    phase: str
    to_redraw: list[int32]
    redrawing: bool

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.lines = []
        self.wave_top = 0
        self.wave_lines = []
        self.glitch_lines = []
        self.glitching_steps = 0
        self.phase = "glitching"
        self.to_redraw = []
        self.redrawing = False
        self.build()

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        glitch_colors = hex_colors(GLITCH_LINE_COLORS)
        noise_colors = hex_colors(NOISE_COLORS)
        for row in self.term.grouped(Grouping.ROW_BOTTOM_TO_TOP):
            self.build_line(row, final_colors, glitch_colors, noise_colors)
        for char_id in self.term.characters():
            self.term.set_visible(char_id, True)
            self.term.chars[char_id].activate_scene("base")
        for i in range(len(self.lines)):
            self.to_redraw.append(i)

    def build_line(self, chars: list[int32], final_colors: dict[Coord, Color],
                   glitch_colors: list[Color], noise_colors: list[Color]) -> None:
        offset = randint(4, 25)
        direction = random.choice([-1, 1])
        hold_time = randint(1, 50)
        white = Color(255, 255, 255)
        for char_id in chars:
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            symbol = character.input_symbol
            color = final_colors[home]
            # A glitch tears the character sideways, holds, then springs back;
            # a glitch wave pushes it right in two stages.
            glitch = Path(2, hold_time)
            glitch.add_waypoint(Coord(home.column + offset * direction, home.row))
            character.add_path("glitch", glitch, then="restore", scene="rgb_glitch_fwd")
            restore = Path(2)
            restore.add_waypoint(home)
            character.add_path("restore", restore, scene="rgb_glitch_bwd")
            wave_mid = Path(2)
            wave_mid.add_waypoint(Coord(home.column + 8, home.row))
            character.add_path("glitch_wave_mid", wave_mid, scene="rgb_glitch_fwd")
            wave_end = Path(2)
            wave_end.add_waypoint(Coord(home.column + 14, home.row))
            character.add_path("glitch_wave_end", wave_end, scene="rgb_glitch_fwd")

            base = Scene("base")
            base.add_frame(symbol, 1, color)
            character.add_scene(base)
            forward = Scene("rgb_glitch_fwd", sync=Sync.STEP)
            for glitch_color in glitch_colors:
                forward.add_frame(symbol, 1, glitch_color)
            character.add_scene(forward)
            backward = Scene("rgb_glitch_bwd", sync=Sync.STEP)
            for glitch_color in reversed(glitch_colors):
                backward.add_frame(symbol, 1, glitch_color)
            character.add_scene(backward)
            snow = Scene("snow")
            for _ in range(25):
                snow_symbol = random.choice(SNOW_SYMBOLS)
                snow.add_frame(snow_symbol, 2, choose_color(noise_colors))
            snow.add_frame(symbol, 1, color)
            character.add_scene(snow)
            final_redraw = Scene("final_redraw")
            final_redraw.add_frame("█", 6, white)
            final_redraw.add_frame(symbol, 1, color)
            character.add_scene(final_redraw)
            final_snow = Scene("final_snow")
            for _ in range(30):
                snow_symbol = random.choice(SNOW_SYMBOLS)
                final_snow.add_frame(snow_symbol, 2, choose_color(noise_colors))
            character.add_scene(final_snow)
        self.lines.append(copy(chars))

    # -- lines --------------------------------------------------------------

    def activate_line(self, line: int32) -> None:
        for char_id in self.lines[line]:
            self.term.activate(char_id)

    def line_movement_complete(self, line: int32) -> bool:
        for char_id in self.lines[line]:
            if self.term.chars[char_id].active_path >= 0:
                return False
        return True

    def lines_movement_complete(self, lines: list[int32]) -> bool:
        for line in lines:
            if not self.line_movement_complete(line):
                return False
        return True

    def restore(self, line: int32) -> None:
        for char_id in self.lines[line]:
            character = self.term.chars[char_id]
            speed = 40 / randint(20, 40)
            character.paths[character.path_index("restore")].set_speed(speed)
            character.activate_path_named("restore")

    def glitch(self, line: int32) -> None:
        for char_id in self.lines[line]:
            character = self.term.chars[char_id]
            glitch_speed = 40 / randint(20, 40)
            character.paths[character.path_index("glitch")].set_speed(glitch_speed)
            restore_speed = 40 / randint(20, 40)
            character.paths[character.path_index("restore")].set_speed(restore_speed)
            character.activate_path_named("glitch")

    def set_hold_time(self, line: int32, hold_time: int32) -> None:
        for char_id in self.lines[line]:
            character = self.term.chars[char_id]
            character.paths[character.path_index("glitch")].set_hold_time(hold_time)

    # -- the glitch wave ----------------------------------------------------

    def glitch_wave(self) -> None:
        """A band of three lines, torn right, that drifts up and down the text
        until it runs off the bottom."""
        if not self.wave_top:
            height = self.term.canvas.text_height()
            if height < 3:
                return
            self.wave_top = self.term.canvas.text_bottom + randint(max(3, round(height * 0.5)), height)
        if not self.lines_movement_complete(self.wave_lines):
            return
        if self.wave_lines:
            delta = 0
            if random.random() < 0.3:
                delta = 1 if random.random() < 0.3 else -1
            self.wave_top = max(2, min(self.wave_top + delta, self.term.canvas.text_top))
        new_lines: list[int32] = []
        for row in range(self.wave_top - 2, self.wave_top + 1):
            line = row - (self.term.canvas.text_bottom - 1)
            if 0 <= line < len(self.lines):
                new_lines.append(line)
        for line in self.wave_lines:
            if line not in new_lines:
                self.restore(line)
                self.activate_line(line)
        self.wave_lines = new_lines
        if self.wave_top < self.term.canvas.text_bottom + 2:
            for line in self.wave_lines:
                self.restore(line)
                self.activate_line(line)
            self.wave_top = 0
            self.wave_lines = []
            return
        wave_paths = ["glitch_wave_mid", "glitch_wave_end", "glitch_wave_mid"]
        for i in range(min(len(self.wave_lines), 3)):
            line = self.wave_lines[i]
            for char_id in self.lines[line]:
                self.term.chars[char_id].activate_path_named(wave_paths[i])
            self.activate_line(line)

    # -- frames ---------------------------------------------------------------

    def glitching(self) -> None:
        if not self.wave_lines or self.lines_movement_complete(self.wave_lines):
            self.glitch_wave()
        still_glitching: list[int32] = []
        for line in self.glitch_lines:
            if not self.line_movement_complete(line):
                still_glitching.append(line)
        self.glitch_lines = still_glitching
        if random.random() < GLITCH_LINE_CHANCE and len(self.glitch_lines) < 3:
            line = randint(0, len(self.lines) - 1)
            if line not in self.wave_lines and line not in self.glitch_lines:
                self.set_hold_time(line, randint(20, 75))
                self.glitch_lines.append(line)
                self.glitch(line)
                self.activate_line(line)
        if random.random() < NOISE_CHANCE:
            for line in range(len(self.lines)):
                for char_id in self.lines[line]:
                    self.term.chars[char_id].activate_scene("snow")
                if line not in self.wave_lines and line not in self.glitch_lines:
                    self.activate_line(line)
        self.glitching_steps += 1
        if self.glitching_steps >= TOTAL_GLITCH_TIME:
            for line in self.wave_lines:
                self.restore(line)
            for line in self.glitch_lines:
                self.restore(line)
            self.phase = "noise"

    def step(self) -> bool:
        if self.phase == "complete" and not self.term.has_active():
            return False
        if self.phase == "glitching":
            self.glitching()
        elif self.phase == "noise":
            if not self.term.has_active():
                # The tape dissolves into snow ...
                for char_id in self.term.characters():
                    self.term.chars[char_id].activate_scene("final_snow")
                    self.term.activate(char_id)
                self.phase = "redraw"
        elif self.phase == "redraw":
            if self.redrawing or not self.term.has_active():
                # ... and is redrawn a line a frame, from the top.
                self.redrawing = True
                if self.to_redraw:
                    line = self.to_redraw.pop()
                    for char_id in self.lines[line]:
                        self.term.chars[char_id].activate_scene("final_redraw")
                        self.term.activate(char_id)
                else:
                    self.phase = "complete"
        self.term.tick()
        for event in self.term.take_events():
            if event.kind == EventKind.SCENE_COMPLETE and event.name == "rgb_glitch_bwd":
                self.term.chars[event.char_id].activate_scene("base")
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
