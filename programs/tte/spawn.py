"""spawn: white-blue flames flare up at the center, then a wave of fire
sweeps out over the canvas and burns out. Midway, in a burst of light, the
text appears as flickering plasma that settles and cools to its final colors. Not one of TTE's effects: written for this
port."""
from __future__ import annotations

import math
import random

from tpy import int32, Own, copy

from easing import out_sine
from engine import Scene, Terminal, randint
from geometry import Coord, TERMINAL_ROW_SCALE, find_length_of_line
from graphics import Color, Gradient, choose_color, hex_color, hex_colors, shift_color_towards

FLAME_COLORS = ["ffffff", "c8e6ff", "6fb1ff", "2f5fd0"]  # core to the tips
FLAME_SYMBOLS = ["█", "▓", "▒", "░"]
FLAME_FLICKER: list[float] = [0.15, 0.3, 0.5, 0.7]  # per shell: how often a cell shows a plasma glyph
SPARK_SYMBOLS = ["*", "+", "·", "°"]
SPARK_COLOR = "8cc4ff"
SECTORS = 32  # directions around the center, each with its own flame length
GROW_FRAMES = 46
HOLD_FRAMES = 8
FLARE_FRAMES = 14
BURST_AT = 4  # the wave frame on which the burst of light goes off
# The burst of light when the text appears: per frame, the symbol, its color
# and the share of the canvas it still covers.
BURST_SYMBOLS = ["█", "█", "▓", "▒", "░", "░"]
BURST_COLORS = ["ffffff", "ffffff", "e0f2ff", "b8dcff", "7fb3ff", "3d6fd0"]
BURST_COVER: list[float] = [1.0, 1.0, 0.8, 0.55, 0.3, 0.12]
PLASMA_SYMBOLS = ["░", "▒", "▓", "*", "+", "#", "%", "&", "@", "·"]
PLASMA_COLORS = ["ffffff", "d8f0ff", "9ad7ff", "7fdbff", "c9a6ff"]
PLASMA_FRAMES_MIN = 6  # flickers before a character settles
PLASMA_FRAMES_MAX = 12
INSTANT_CHANCE = 0.33  # characters that skip the plasma and show at once
COOL_STEP_MIN = 1  # frames per step of cooling, picked per character
COOL_STEP_MAX = 4
HOT_COLOR = "ffffff"
FINAL_GRADIENT_STOPS = ["3d7bff", "9ad7ff", "ffffff", "ffcc33"]
FINAL_GRADIENT_STEPS = [12]
FINAL_GRADIENT_ANGLE = 70.0  # degrees from the horizontal: a vertical gradient, leaning right


class Spawn:
    term: Terminal
    center: Coord
    base_radius: float  # how far the flames reach before the flare
    full_radius: float  # enough to reach every corner of the canvas
    radius: float  # the leading edge of the fire
    brightness: float  # 1 while the flames burn; the wave dims to 0 as it spreads
    band: float  # how deep the fire is behind its leading edge
    glow: list[int32]  # one character per canvas cell, drawn over the text
    glow_distance: list[float]
    glow_sector: list[int32]
    flame_length: list[float]  # per sector, as a multiple of the radius
    flame_colors: list[Color]
    frame_count: int32
    burst_frame: int32  # -1 before the burst
    phase: str

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.center = self.term.canvas.center()
        self.base_radius = max(2.0, min(self.term.canvas.width() / 5, self.term.canvas.height() * 1.0))
        self.full_radius = 0.0
        self.radius = 0.0
        self.brightness = 1.0
        self.band = self.base_radius
        self.glow = []
        self.glow_distance = []
        self.glow_sector = []
        self.flame_length = []
        self.flame_colors = []
        self.frame_count = 0
        self.burst_frame = -1
        self.phase = "grow"
        self.build()

    def build(self) -> None:
        self.flame_colors = hex_colors(FLAME_COLORS)
        for _ in range(SECTORS):
            self.flame_length.append(1.0)
        center = copy(self.center)
        for row in range(1, self.term.canvas.top + 1):
            for column in range(1, self.term.canvas.right + 1):
                coord = Coord(column, row)
                glow_char = self.term.add_character(" ", coord)
                self.term.chars[glow_char].layer = 1
                self.glow.append(glow_char)
                distance = find_length_of_line(center, coord)
                self.glow_distance.append(distance)
                self.full_radius = max(self.full_radius, distance)
                angle = math.atan2((row - center.row) * TERMINAL_ROW_SCALE, column - center.column)
                sector = int((angle + math.pi) / (2 * math.pi) * SECTORS) % SECTORS
                self.glow_sector.append(sector)
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors_at_angle(final_gradient, FINAL_GRADIENT_ANGLE)
        hot = hex_color(HOT_COLOR)
        plasma_colors = hex_colors(PLASMA_COLORS)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            # Flickering plasma when the fire leaves it (or, for some, the
            # character at once), then the character cooling from white-hot
            # at a pace of its own.
            cool = Scene("cool")
            if random.random() >= INSTANT_CHANCE:
                for _ in range(randint(PLASMA_FRAMES_MIN, PLASMA_FRAMES_MAX)):
                    symbol = random.choice(PLASMA_SYMBOLS)
                    color = choose_color(plasma_colors)
                    cool.add_frame(symbol, randint(1, 3), color)
            final_color = final_colors[home]
            pale_blue = plasma_colors[2]
            cooling = Gradient([hot, pale_blue, final_color], [4, 10])
            cool_step = randint(COOL_STEP_MIN, COOL_STEP_MAX)
            for color in cooling.spectrum:
                cool.add_frame(character.input_symbol, cool_step, color)
            character.add_scene(cool)

    def flicker(self) -> None:
        """Let each flame grow or shrink a little, keeping neighbours alike."""
        jittered: list[float] = []
        for length in self.flame_length:
            jittered.append(max(0.55, min(length + random.uniform(-0.25, 0.25), 1.5)))
        for i in range(SECTORS):
            before = jittered[(i - 1) % SECTORS]
            after = jittered[(i + 1) % SECTORS]
            self.flame_length[i] = (before + 2 * jittered[i] + after) / 4

    def draw_flames(self) -> None:
        spark_color = hex_color(SPARK_COLOR)
        black = Color(0, 0, 0)
        flaring = self.phase == "flare"
        for i in range(len(self.glow)):
            glow_char = self.glow[i]
            character = self.term.chars[glow_char]
            length = self.flame_length[self.glow_sector[i]]
            if flaring:
                # The wave keeps the flames' ragged edge, but not their spread.
                reach = self.radius + self.base_radius * (length - 1)
                inner = max(reach - self.band, 0.0)
            else:
                reach = self.radius * length
                inner = 0.0
            distance = self.glow_distance[i]
            lit = reach > inner and inner <= distance <= reach
            depth = 0.0
            if lit:
                # Hottest at the heart of the fire: the center while it burns
                # there, the middle of the wave once it flares.
                depth = (distance - inner) / (reach - inner)
                if flaring:
                    depth = abs(depth - 0.5) * 2
                if depth > 0.85:
                    # The ragged edges of the fire come and go.
                    lit = random.random() < 0.6
            if lit:
                shell = 0 if depth < 0.4 else (1 if depth < 0.65 else (2 if depth < 0.85 else 3))
                shade = shift_color_towards(black, self.flame_colors[shell], self.brightness)
                symbol = FLAME_SYMBOLS[shell]
                if random.random() < FLAME_FLICKER[shell]:
                    symbol = random.choice(PLASMA_SYMBOLS)
                character.set_appearance(symbol, shade)
                self.term.set_visible(glow_char, True)
            elif not flaring and self.radius > 0 and distance <= reach * 1.3 and random.random() < 0.15:
                symbol = random.choice(SPARK_SYMBOLS)
                character.set_appearance(symbol, spark_color)
                self.term.set_visible(glow_char, True)
            else:
                self.term.set_visible(glow_char, False)

    def reveal(self) -> None:
        """The text appears, all at once, under the burst of light."""
        for char_id in self.term.characters():
            self.term.chars[char_id].activate_scene("cool")
            self.term.set_visible(char_id, True)
            self.term.activate(char_id)

    def draw_burst(self, frame: int32) -> None:
        """The whole canvas flashes white, then breaks up and dims away,
        showing the wave through the gaps."""
        color = hex_color(BURST_COLORS[frame])
        for glow_char in self.glow:
            if random.random() < BURST_COVER[frame]:
                self.term.chars[glow_char].set_appearance(BURST_SYMBOLS[frame], color)
                self.term.set_visible(glow_char, True)

    def step(self) -> bool:
        if self.phase == "complete" and not self.term.has_active():
            return False
        self.frame_count += 1
        if self.phase == "grow":
            self.radius = self.base_radius * out_sine(self.frame_count / GROW_FRAMES)
            self.band = self.radius
            if self.frame_count == GROW_FRAMES:
                self.phase = "hold"
                self.frame_count = 0
        elif self.phase == "hold":
            if self.frame_count == HOLD_FRAMES:
                self.phase = "flare"
                self.frame_count = 0
        elif self.phase == "flare":
            # The fire sweeps out as a wave until it has passed every cell.
            end = self.full_radius + self.band + self.base_radius
            progress = self.frame_count / FLARE_FRAMES
            self.radius = self.base_radius + (end - self.base_radius) * out_sine(progress)
            self.brightness = 1 - progress
            if self.frame_count == BURST_AT:
                self.reveal()
                self.burst_frame = 0
            if self.frame_count == FLARE_FRAMES:
                self.radius = 0.0
                self.phase = "complete"
        if self.phase != "complete":
            self.flicker()
        self.draw_flames()
        if 0 <= self.burst_frame < len(BURST_SYMBOLS):
            self.draw_burst(self.burst_frame)
            self.burst_frame += 1
        self.term.tick()
        self.term.events.clear()
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
