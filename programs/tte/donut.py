"""donut: a torus spins in the middle of the canvas, shaded in ASCII the way
Andy Sloane's donut.c does it. Then the camera closes in until its side
fills the canvas, and the text turns out to be written on it. Not one of
TTE's effects: written for this port."""
from __future__ import annotations

import math
import random

from tpy import int32, Own, copy

from easing import in_out_sine, out_sine
from engine import Terminal
from geometry import Coord
from graphics import Color, Direction, Gradient, hex_colors, shift_color_towards

LUMINANCE = [".", ",", "-", "~", ":", ";", "=", "!", "*", "#", "$", "@"]  # darkest to brightest
SHADE_STOPS = ["3a3a3a", "9a9a9a", "ffffff"]
TUBE_RADIUS = 1.0  # donut.c's R1
RING_RADIUS = 2.0  # R2: from the center of the hole to the center of the tube
DISTANCE = 5.0  # K2: from the viewer to the donut
THETA_STEP = 0.07  # around the tube's cross-section
PHI_STEP = 0.02  # around the ring
ROW_ASPECT = 0.5  # a terminal cell is about twice as tall as it is wide
SPIN_A = 0.04  # radians a frame about the x axis
SPIN_B = 0.02  # and about the z axis
APPROACH_FRAMES = 120  # flying in from far away, where the donut is a dot
SPIN_FRAMES = 210  # spinning, the approach included
FAR_SCALE = 0.5  # how big the donut is on screen from far away: one cell
ZOOM_FRAMES = 150
REVEAL_FROM = 0.7  # how far into the zoom the text starts to show
REVEAL_TO = 0.95  # and when all of it shows
TEXT_MIN_SHADE = 4  # the text stays legible where the surface is dark
FADE_TAIL_FRAMES = 25  # the fade, begun as the text shows, runs on this long after the zoom
FINAL_GRADIENT_STOPS = ["b4b4b4", "ffffff"]
FINAL_GRADIENT_STEPS = [12]
NOTHING = -1  # what a canvas cell shows, when it is not a character of the text
SURFACE = -2


class Donut:
    term: Terminal
    glow: list[int32]  # one character per canvas cell, top row first, drawn over the text
    shades: list[Color]  # per luminance character
    spin_scale: float  # donut.c's K1: how big the donut is on screen, spinning
    close_scale: float  # and once the camera has closed in
    theta_bin: float  # the grid the surface is swept on, and the text written on
    phi_bin: float
    theta_bins: int32
    phi_bins: int32
    written: dict[int32, int32]  # grid point -> the character written there
    reveal_at: dict[int32, float]  # character -> how far into the zoom it shows
    shown: list[int32]  # per canvas cell: a character of the text, SURFACE or NOTHING
    shown_shade: list[int32]  # and how brightly it is lit
    start_a: float  # the donut's angles when the zoom takes over
    start_b: float
    end_a: float  # and when the camera has closed in
    end_b: float
    a: float
    b: float
    frame_count: int32
    phase: str

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.glow = []
        self.shades = []
        self.spin_scale = 1.0
        self.close_scale = 1.0
        self.theta_bin = THETA_STEP
        self.phi_bin = PHI_STEP
        self.theta_bins = 1
        self.phi_bins = 1
        self.written = {}
        self.reveal_at = {}
        self.shown = []
        self.shown_shade = []
        self.start_a = 0.0
        self.start_b = 0.0
        self.end_a = 0.0
        self.end_b = 0.0
        self.a = 1.0
        self.b = 0.5
        self.frame_count = 0
        self.phase = "spin"
        self.build()

    def build(self) -> None:
        width = self.term.canvas.width()
        height = self.term.canvas.height()
        for line in range(height):
            for column in range(width):
                glow_char = self.term.add_character(" ", Coord(column + 1, height - line))
                self.term.chars[glow_char].layer = 1
                self.glow.append(glow_char)
                self.shown.append(NOTHING)
                self.shown_shade.append(0)
        # As large as the canvas allows: the donut's nearest edge, at
        # DISTANCE - (RING_RADIUS + TUBE_RADIUS), projects largest.
        reach = (RING_RADIUS + TUBE_RADIUS) / (DISTANCE - TUBE_RADIUS)
        across = (width / 2 - 1) / reach
        up = (height / 2 - 1) / (reach * ROW_ASPECT)
        self.spin_scale = max(1.0, min(across, up))
        stops = hex_colors(SHADE_STOPS)
        steps = [len(LUMINANCE) // 2]
        gradient = Gradient(stops, steps)
        for i in range(len(LUMINANCE)):
            self.shades.append(gradient.color_at_fraction(i / (len(LUMINANCE) - 1)))
        self.write_text()
        for char_id in self.term.characters():
            self.reveal_at[char_id] = random.uniform(REVEAL_FROM, REVEAL_TO)
        # The zoom keeps the spin's pace at first, then comes to rest facing
        # the camera, where the donut's angles are whole turns.
        self.start_a = self.a + SPIN_A * SPIN_FRAMES
        self.start_b = self.b + SPIN_B * SPIN_FRAMES
        self.end_a = self.next_turn(self.start_a, SPIN_A)
        self.end_b = self.next_turn(self.start_b, SPIN_B)

    def next_turn(self, angle: float, speed: float) -> float:
        """The first whole turn after `angle` far enough away to slow down for."""
        turn = 2 * math.pi
        end = math.ceil(angle / turn) * turn
        if end - angle < speed * ZOOM_FRAMES / 2:
            end += turn
        return end

    def write_text(self) -> None:
        """Close in on the donut's side, facing the camera, until it covers
        the canvas, and write the text on the surface there: every point of
        the front layer that lands in a cell of the text carries that cell's
        character."""
        width = self.term.canvas.width()
        height = self.term.canvas.height()
        scale = self.spin_scale
        covered = False
        tries = 0
        while not covered and tries < 40:
            scale *= 1.1
            tries += 1
            self.set_grid(scale)
            self.draw(0.0, 0.0, scale, 1, 1, True, 0.0)
            covered = NOTHING not in self.shown
        self.close_scale = scale
        nearest: list[float] = []
        for _ in range(width * height):
            nearest.append(0.0)
        points = self.surface(0.0, 0.0, scale, 1, 1)
        for point in points:
            cell = point[1]
            if cell >= 0:
                nearest[cell] = max(nearest[cell], point[2])
        for point in points:
            cell = point[1]
            if cell >= 0 and point[2] >= nearest[cell] * 0.97:
                home = Coord(cell % width + 1, height - cell // width)
                char_id = self.term.at(home)
                if not self.term.chars[char_id].is_fill:
                    self.written[point[0]] = char_id

    def set_grid(self, close_scale: float) -> None:
        """A grid on the surface fine enough to leave no gaps at the closest
        the camera gets."""
        self.theta_bin = min(THETA_STEP, 1.2 / close_scale)
        self.phi_bin = min(PHI_STEP, 0.6 / close_scale)
        self.theta_bins = int(2 * math.pi / self.theta_bin) + 1
        self.phi_bins = int(2 * math.pi / self.phi_bin) + 1

    def surface(self, a: float, b: float, scale: float, theta_every: int32,
                phi_every: int32) -> Own[list[tuple[int32, int32, float, float]]]:
        """donut.c's sweep over the torus, turned by `a` and `b`, at every
        `theta_every`-th and `phi_every`-th point of the grid: the grid point,
        the canvas cell it lands in (-1: off the canvas), its depth as 1/z,
        and how squarely it faces the light."""
        width = self.term.canvas.width()
        height = self.term.canvas.height()
        cos_a = math.cos(a)
        sin_a = math.sin(a)
        cos_b = math.cos(b)
        sin_b = math.sin(b)
        # The middle of a cell, so that from far away the donut is one dot.
        center_column = width // 2 + 0.5
        center_line = height // 2 + 0.5
        points: list[tuple[int32, int32, float, float]] = []
        for i in range(0, self.theta_bins, theta_every):
            theta = i * self.theta_bin
            cos_theta = math.cos(theta)
            sin_theta = math.sin(theta)
            circle_x = RING_RADIUS + TUBE_RADIUS * cos_theta
            circle_y = TUBE_RADIUS * sin_theta
            for j in range(0, self.phi_bins, phi_every):
                phi = j * self.phi_bin
                cos_phi = math.cos(phi)
                sin_phi = math.sin(phi)
                x = circle_x * (cos_b * cos_phi + sin_a * sin_b * sin_phi) - circle_y * cos_a * sin_b
                y = circle_x * (sin_b * cos_phi - sin_a * cos_b * sin_phi) + circle_y * cos_a * cos_b
                one_over_z = 1 / (DISTANCE + cos_a * circle_x * sin_phi + circle_y * sin_a)
                column = int(center_column + scale * one_over_z * x)
                line = int(center_line - scale * one_over_z * y * ROW_ASPECT)
                luminance = (cos_phi * cos_theta * sin_b - cos_a * cos_theta * sin_phi - sin_a * sin_theta
                             + cos_b * (cos_a * sin_theta - cos_theta * sin_a * sin_phi))
                cell = -1
                if 0 <= column < width and 0 <= line < height:
                    cell = line * width + column
                points.append((i * self.phi_bins + j, cell, one_over_z, luminance))
        return points

    def draw(self, a: float, b: float, scale: float, theta_every: int32, phi_every: int32,
             unlit: bool, reveal: float) -> None:
        """Work out what each canvas cell shows: the nearest point of the
        surface there, or the character written on it once the zoom is
        `reveal` of the way to that character's moment. Points facing away
        from the light are left out, as donut.c leaves them out, unless
        `unlit` or the text shows on them."""
        depth: list[float] = []
        for i in range(len(self.shown)):
            depth.append(0.0)
            self.shown[i] = NOTHING
        for point in self.surface(a, b, scale, theta_every, phi_every):
            cell = point[1]
            if cell < 0 or point[2] <= depth[cell]:
                continue
            showing = SURFACE
            if point[0] in self.written:
                char_id = self.written[point[0]]
                if reveal >= self.reveal_at[char_id]:
                    showing = char_id
            if point[3] <= 0 and showing == SURFACE and not unlit:
                continue
            depth[cell] = point[2]
            self.shown[cell] = showing
            self.shown_shade[cell] = max(0, min(int(point[3] * 8), len(LUMINANCE) - 1))

    def paint(self, fade: float) -> None:
        """Put what `draw` worked out on the canvas, the surface darkening
        and the text turning to its final colors by `fade`."""
        black = Color(0, 0, 0)
        final_colors = self.final_gradient()
        for cell in range(len(self.glow)):
            glow_char = self.glow[cell]
            showing = self.shown[cell]
            shade = self.shown_shade[cell]
            if showing == NOTHING:
                self.term.set_visible(glow_char, False)
                continue
            if showing == SURFACE:
                color = shift_color_towards(self.shades[shade], black, fade)
                self.term.chars[glow_char].set_appearance(LUMINANCE[shade], color)
            else:
                symbol = self.term.chars[showing].input_symbol
                lit = self.shades[max(shade, TEXT_MIN_SHADE)]
                home = copy(self.term.chars[showing].input_coord)
                color = shift_color_towards(lit, final_colors[home], fade)
                self.term.chars[glow_char].set_appearance(symbol, color)
            self.term.set_visible(glow_char, True)

    def final_gradient(self) -> Own[dict[Coord, Color]]:
        stops = hex_colors(FINAL_GRADIENT_STOPS)
        gradient = Gradient(stops, FINAL_GRADIENT_STEPS)
        return self.term.text_colors(gradient, Direction.VERTICAL)

    def every(self, step: float, bin: float) -> int32:
        return max(1, round(step / bin))

    def step(self) -> bool:
        if self.phase == "complete":
            return False
        self.frame_count += 1
        if self.phase == "spin":
            # The camera flies in, slowing to a stop: the donut looks as big
            # as the camera is near, so it stays a dot for a long while.
            far = self.spin_scale / FAR_SCALE
            distance = far + (1 - far) * out_sine(min(self.frame_count / APPROACH_FRAMES, 1.0))
            scale = self.spin_scale / distance
            self.draw(self.a, self.b, scale, self.every(THETA_STEP, self.theta_bin),
                      self.every(PHI_STEP, self.phi_bin), False, 0.0)
            self.paint(0.0)
            self.a += SPIN_A
            self.b += SPIN_B
            if self.frame_count == SPIN_FRAMES:
                self.phase = "zoom"
                self.frame_count = 0
        elif self.phase == "zoom":
            t = self.frame_count / ZOOM_FRAMES
            self.a = self.start_a + (self.end_a - self.start_a) * self.slow_down(t, SPIN_A, self.end_a - self.start_a)
            self.b = self.start_b + (self.end_b - self.start_b) * self.slow_down(t, SPIN_B, self.end_b - self.start_b)
            scale = self.spin_scale * (self.close_scale / self.spin_scale) ** in_out_sine(t)
            self.draw(self.a, self.b, scale, self.every(min(THETA_STEP, 1.2 / scale), self.theta_bin),
                      self.every(min(PHI_STEP, 0.6 / scale), self.phi_bin), False, t)
            self.paint(self.fade(self.frame_count))
            if self.frame_count == ZOOM_FRAMES:
                self.phase = "fade"
                self.frame_count = 0
                # From here on, the text exactly as it is, on the lit surface.
                for cell in range(len(self.glow)):
                    coord = copy(self.term.chars[self.glow[cell]].input_coord)
                    char_id = self.term.at(coord)
                    if not self.term.chars[char_id].is_fill:
                        self.shown[cell] = char_id
                    elif self.shown[cell] != NOTHING:
                        self.shown[cell] = SURFACE
        elif self.phase == "fade":
            self.paint(self.fade(ZOOM_FRAMES + self.frame_count))
            if self.frame_count == FADE_TAIL_FRAMES:
                self.finish()
        return True

    def fade(self, frame: int32) -> float:
        """How far the surface has darkened, and the text taken on its final
        colors, `frame` frames into the zoom: from when the text starts to
        show until the tail after the zoom is over."""
        start = REVEAL_FROM * ZOOM_FRAMES
        progress = (frame - start) / (ZOOM_FRAMES + FADE_TAIL_FRAMES - start)
        return in_out_sine(max(0.0, min(progress, 1.0)))

    def slow_down(self, t: float, speed: float, distance: float) -> float:
        """How far along its way an angle is, `t` of the way through the zoom:
        leaving at the spin's `speed`, arriving at rest (a cubic)."""
        pace = speed * ZOOM_FRAMES / distance
        return pace * t + (3 - 2 * pace) * t * t + (pace - 2) * t * t * t

    def finish(self) -> None:
        """Swap the painted canvas for the text itself, in its final colors."""
        final_colors = self.final_gradient()
        for glow_char in self.glow:
            self.term.set_visible(glow_char, False)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            character.set_appearance(character.input_symbol, final_colors[home])
            self.term.set_visible(char_id, True)
        self.phase = "complete"

    def frame(self) -> str:
        return self.term.render()
