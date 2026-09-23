"""sandstorm: sand blows across the canvas, and the text drifts in with it,
piling up from the bottom as restless letters; then, from the left, each
letter settles into place as the wind drops. Not one of TTE's effects:
written for this port."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from engine import EventKind, ParticlePool, Path, Scene, Terminal, randint
from geometry import Coord
from graphics import Gradient, adjust_brightness, choose_color, hex_colors

SAND_COLORS = ["d9ccb0", "cbbb9b", "bcab8a", "ab9b7c"]
WIND_SYMBOLS = ["*", "'", "`", "¤", "•", "°", "·", ".", ","]
WIND_DENSITY = 0.15  # grains blown in a frame, per canvas row
WIND_SPEED_MIN = 2.5  # cells a frame
WIND_SPEED_MAX = 4.0
WIND_SLOWDOWN = 0.5  # how much slower the last of the wind blows
WIND_DROP = 2  # rows a grain falls, at most, crossing the canvas
RAMP_FRAMES = 30  # frames until the text drifts in at full rate
DRIFT_RATE = 0.012  # characters drifting in a frame, as a share of the text
PILE_ROUGHNESS = 4.0  # rows by which the pile's surface is uneven
RESTLESS_FRAMES_MIN = 2  # how long a restless letter shows before it changes
RESTLESS_FRAMES_MAX = 7
SETTLE_START = 0.4  # the share of the text landed before the settling begins
SETTLE_SPEED = 0.5  # columns a frame the settling sweeps across
SETTLE_RAGGEDNESS = 2.0  # columns by which the settling front is uneven
SETTLE_FLICKERS_MIN = 2  # random letters shown before the right one
SETTLE_FLICKERS_MAX = 4
FINAL_GRADIENT_STOPS = ["f4ead4", "dcc59a", "b89a6c"]
FINAL_GRADIENT_STEPS = [12]
FINAL_GRADIENT_ANGLE = 20.0  # degrees from the horizontal


class Sandstorm:
    term: Terminal
    wind: ParticlePool
    letters: list[str]  # what the restless text flickers through
    drifting: list[int32]  # characters still to drift in, last first
    landed: set[int32]
    passed: set[int32]  # characters the settling has passed before they landed
    unsettled: list[tuple[float, int32]]  # where the settling reaches each character, by column
    settled: int32
    settle_front: float
    text_size: int32
    frame_count: int32
    phase: str

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.wind = ParticlePool(WIND_SYMBOLS)
        self.letters = []
        self.drifting = []
        self.landed = set()
        self.passed = set()
        self.unsettled = []
        self.settled = 0
        self.settle_front = 0.0
        self.text_size = len(self.term.input_ids)
        self.frame_count = 0
        self.phase = "drift"
        self.build()

    def build(self) -> None:
        text = self.term.characters()
        # The text is restless with its own letters; any character, if it has none.
        for char_id in text:
            symbol = self.term.chars[char_id].input_symbol
            if "a" <= symbol <= "z" or "A" <= symbol <= "Z":
                self.letters.append(symbol)
        if not self.letters:
            for char_id in text:
                self.letters.append(self.term.chars[char_id].input_symbol)
        sand_colors = hex_colors(SAND_COLORS)
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors_at_angle(final_gradient, FINAL_GRADIENT_ANGLE)
        # Sand piles up from the bottom, its surface uneven.
        pile: list[tuple[float, int32]] = []
        for char_id in text:
            character = self.term.chars[char_id]
            home = copy(character.input_coord)
            sand = choose_color(sand_colors)
            character.set_appearance(random.choice(WIND_SYMBOLS), sand)
            restless = Scene("restless", looping=True)
            for _ in range(6):
                letter = self.random_letter()
                restless.add_frame(letter, randint(RESTLESS_FRAMES_MIN, RESTLESS_FRAMES_MAX), sand)
            character.add_scene(restless)
            # Random letters, warming from sand to the final color, then the right one.
            final_color = final_colors[home]
            warming = Gradient([sand, final_color], [randint(SETTLE_FLICKERS_MIN, SETTLE_FLICKERS_MAX)])
            settle = Scene("settle")
            for i in range(len(warming.spectrum) - 1):
                settle.add_frame(self.random_letter(), 1, warming.spectrum[i])
            settle.add_frame(character.input_symbol, 1, final_color)
            character.add_scene(settle)
            pile.append((home.row + random.uniform(0.0, PILE_ROUGHNESS), char_id))
            self.unsettled.append((home.column + random.uniform(0.0, SETTLE_RAGGEDNESS), char_id))
        pile.sort()
        for i in range(len(pile) - 1, -1, -1):
            self.drifting.append(pile[i][1])
        self.unsettled.sort()
        self.unsettled.reverse()

    def random_letter(self) -> str:
        # Not random.choice: the pool can hold a single letter (README).
        return self.letters[randint(0, len(self.letters) - 1)]

    def launches(self, rate: float) -> int32:
        """A whole number a frame that averages out to `rate`."""
        whole = int(rate)
        if random.random() < rate - whole:
            whole += 1
        return whole

    def blow(self, strength: float) -> None:
        """A grain of sand, flying fast across the canvas, falling a little."""
        grain, _ = self.wind.acquire(self.term)
        sand = choose_color(hex_colors(SAND_COLORS))
        character = self.term.chars[grain]
        symbol = random.choice(WIND_SYMBOLS)
        shade = random.uniform(0.5, 1.0)
        character.set_appearance(symbol, adjust_brightness(sand, shade))
        row = randint(1, self.term.canvas.top + WIND_DROP)
        start = Coord(0, row)
        end = Coord(self.term.canvas.right + 1, row - randint(0, WIND_DROP))
        character.move_to(start)
        path = Path(random.uniform(WIND_SPEED_MIN, WIND_SPEED_MAX) * strength)
        path.add_waypoint(end)
        character.add_path("wind", path, start_layer=2)
        character.activate_path_named("wind")
        self.term.set_visible(grain, True)
        self.term.activate(grain)

    def drift_in(self, char_id: int32) -> None:
        """A character blows in with the sand, and drops onto the pile."""
        character = self.term.chars[char_id]
        home = copy(character.input_coord)
        start = Coord(0, home.row + randint(0, WIND_DROP))
        control = Coord(home.column // 2, start.row)
        path = Path(1.0)
        path.add_waypoint(start)
        path.add_curved_waypoint(home, control)
        path.set_speed(random.uniform(WIND_SPEED_MIN, WIND_SPEED_MAX))
        character.move_to(start)
        character.add_path("drift", path, end_scene="restless", start_layer=1, end_layer=0)
        character.activate_path_named("drift")
        self.term.set_visible(char_id, True)
        self.term.activate(char_id)

    def step(self) -> bool:
        if self.phase == "complete":
            return False
        self.frame_count += 1
        if self.phase != "calm":
            # The wind drops as the text settles, dying away with the last letter.
            calm = self.settled / self.text_size
            for _ in range(self.launches(self.term.canvas.top * WIND_DENSITY * (1 - calm))):
                self.blow(1 - calm * WIND_SLOWDOWN)
        if self.phase == "drift":
            strength = min(1.0, self.frame_count / RAMP_FRAMES)
            for _ in range(self.launches(max(1.0, self.text_size * DRIFT_RATE * strength))):
                if self.drifting:
                    self.drift_in(self.drifting.pop())
            if len(self.landed) >= self.text_size * SETTLE_START:
                self.settle_front += SETTLE_SPEED
            # A letter still on its way when the front passes settles as it lands.
            while self.unsettled and self.unsettled[len(self.unsettled) - 1][0] <= self.settle_front:
                reached = self.unsettled.pop()
                if reached[1] in self.landed:
                    self.term.chars[reached[1]].activate_scene("settle")
                else:
                    self.passed.add(reached[1])
        elif self.phase == "calm" and not self.term.has_active():
            self.phase = "complete"
        self.term.tick()
        for event in self.term.take_events():
            if event.kind == EventKind.PATH_COMPLETE and event.name == "wind":
                self.wind.reclaim(self.term, event.char_id)
            elif event.kind == EventKind.PATH_COMPLETE and event.name == "drift":
                self.landed.add(event.char_id)
                if event.char_id in self.passed:
                    self.term.chars[event.char_id].activate_scene("settle")
            elif event.kind == EventKind.SCENE_COMPLETE and event.name == "settle":
                self.settled += 1
                if self.settled == self.text_size:
                    self.phase = "calm"
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
