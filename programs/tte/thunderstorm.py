"""thunderstorm: rain, lightning strikes that throw sparks, and text that glows where it is hit."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from easing import CubicBezier, in_circ, out_quint
from engine import EventKind, ParticlePool, Path, Scene, Terminal, randint
from geometry import Coord
from graphics import Color, Direction, Gradient, adjust_brightness, hex_color, hex_colors

LIGHTNING_COLOR = "68A3E8"
GLOWING_TEXT_COLOR = "EF5411"
TEXT_GLOW_TIME = 6
RAINDROP_SYMBOLS = ["\\", ".", ","]
SPARK_SYMBOLS = ["*", ".", "'"]
SPARK_GLOW_COLOR = "ff4d00"
SPARK_GLOW_TIME = 18
# TTE storms for 12 seconds of wall-clock time; this counts frames at its 60 fps.
STORM_FRAMES = 12 * 60
FINAL_GRADIENT_STOPS = ["8A008A", "00D1FF", "FFFFFF"]
FINAL_GRADIENT_STEPS = [12]
BACKGROUND = Color(0, 0, 0)


class Thunderstorm:
    term: Terminal
    rain_pool: ParticlePool
    spark_pool: ParticlePool
    raindrop_color: Color
    spark_gradient: Gradient
    strike_ids: set[int32]
    available_strike_chars: list[int32]
    pending_strike_chars: list[int32]
    active_strike_chars: list[int32]
    pending_glow_chars: list[int32]
    last_strike_char: int32
    reference_char: int32
    delay: int32
    strike_progression_delay: int32
    strike_in_progress: bool
    strike_branch_chance: float
    phase: str
    frames: int32  # frames rendered so far
    storm_start: int32

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.rain_pool = ParticlePool(RAINDROP_SYMBOLS)
        self.spark_pool = ParticlePool(SPARK_SYMBOLS, 2000)
        self.raindrop_color = hex_color("aaaaff")
        spark_stops = [hex_color(SPARK_GLOW_COLOR), BACKGROUND]
        self.spark_gradient = Gradient(spark_stops, [7])
        self.strike_ids = set()
        self.available_strike_chars = []
        self.pending_strike_chars = []
        self.active_strike_chars = []
        self.pending_glow_chars = []
        self.last_strike_char = -1
        self.reference_char = -1
        self.delay = 0
        self.strike_progression_delay = 0
        self.strike_in_progress = False
        self.strike_branch_chance = 0.05
        self.phase = "pre-storm"
        self.frames = 0
        self.storm_start = 0
        for raindrop in self.rain_pool.fill(self.term, 50):
            self.init_raindrop(raindrop)
        for spark in self.spark_pool.fill(self.term, 200):
            self.init_spark(spark, self.spark_gradient)
        self.build()

    def init_raindrop(self, char_id: int32) -> None:
        character = self.term.chars[char_id]
        character.layer = 1
        character.set_appearance(character.input_symbol, self.raindrop_color)

    def init_spark(self, char_id: int32, gradient: Gradient) -> None:
        character = self.term.chars[char_id]
        character.layer = 2
        glow = Scene("glow")
        glow.ease = in_circ
        for color in gradient.spectrum:
            glow.add_frame(character.input_symbol, SPARK_GLOW_TIME, color)
        character.add_scene(glow)

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        self.build_strike_characters(200)
        glowing = hex_color(GLOWING_TEXT_COLOR)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            symbol = character.input_symbol
            visible = final_colors[copy(character.input_coord)]
            storm = adjust_brightness(visible, 0.5)
            glow = Scene("glow")
            glow_gradient = Gradient([glowing, storm], [7])
            for color in glow_gradient.spectrum:
                glow.add_frame(symbol, TEXT_GLOW_TIME, color)
            character.add_scene(glow)
            # The text dims while the storm lasts and brightens again after it.
            fade = Scene("fade")
            fade_gradient = Gradient([visible, storm], [7])
            for color in fade_gradient.spectrum:
                fade.add_frame(symbol, 12, color)
            character.add_scene(fade)
            unfade = Scene("unfade")
            for color in reversed(fade_gradient.spectrum):
                unfade.add_frame(symbol, 12, color)
            character.add_scene(unfade)
            flash = Scene("flash")
            flash_color = adjust_brightness(visible, 1.7)
            flash_gradient = Gradient([storm, flash_color], [7], loop=True)
            for color in flash_gradient.spectrum:
                flash.add_frame(symbol, 6, color)
            character.add_scene(flash)
            self.term.set_visible(char_id, True)
            if self.reference_char < 0:
                self.reference_char = char_id

    def build_strike_characters(self, count: int32) -> None:
        for _ in range(count):
            strike_char = self.term.add_character("|", Coord(1, 1))
            self.strike_ids.add(strike_char)
            self.available_strike_chars.append(strike_char)

    def next_strike_char(self) -> int32:
        if not self.available_strike_chars:
            self.build_strike_characters(20)
        strike_char = self.available_strike_chars.pop()
        self.term.chars[strike_char].clear_scenes()
        return strike_char

    # -- lightning ------------------------------------------------------------

    def setup_lightning_strike(self, branch_neighbor: int32 = -1) -> None:
        """Lay out a bolt from the top of the canvas to the bottom, sometimes
        forking a branch off partway down."""
        if branch_neighbor >= 0:
            column = self.term.chars[branch_neighbor].coord.column
            row = self.term.chars[branch_neighbor].coord.row
        else:
            column = randint(1, self.term.canvas.right)
            row = self.term.canvas.top
        while row >= self.term.canvas.bottom:
            if not self.available_strike_chars:
                self.build_strike_characters(20)
            if branch_neighbor >= 0:
                neighbor_symbol = self.term.chars[branch_neighbor].input_symbol
                if neighbor_symbol == "/":
                    column += 1
                    symbol = random.choice(["|", "\\"])
                elif neighbor_symbol == "\\":
                    column -= 1
                    symbol = random.choice(["|", "/"])
                else:
                    delta = random.choice([-1, 1])
                    column += delta
                    symbol = "\\" if delta == 1 else "/"
            else:
                symbol = random.choice(["\\", "/", "|"])
            strike_char = self.next_strike_char()
            self.term.chars[strike_char].move_to(Coord(column, row))
            self.term.chars[strike_char].set_appearance(symbol, hex_color(LIGHTNING_COLOR))
            row -= 1
            if symbol == "\\":
                column += 1
            elif symbol == "/":
                column -= 1
            self.pending_strike_chars.append(strike_char)
            if random.random() < self.strike_branch_chance and branch_neighbor < 0:
                self.strike_branch_chance -= 0.01
                self.setup_lightning_strike(strike_char)
            branch_neighbor = -1
        self.strike_branch_chance = 0.05

    def lightning_strike(self) -> None:
        self.setup_lightning_strike()
        base_color = hex_color(LIGHTNING_COLOR)
        flash_color = adjust_brightness(base_color, 1.7)
        strike_gradient = Gradient([base_color, flash_color], [7], loop=True)
        fade_gradient = Gradient([base_color, BACKGROUND], [6])
        flash_ease = CubicBezier(0, 1.6, 1, random.uniform(-0.6, 0.4))
        for strike_char in self.pending_strike_chars:
            character = self.term.chars[strike_char]
            symbol = character.visual.symbol
            flash = Scene("flash")
            flash.ease = flash_ease
            for color in strike_gradient.spectrum:
                flash.add_frame(symbol, 6, color)
            character.add_scene(flash)
            fade = Scene("fade")
            for color in fade_gradient.spectrum:
                fade.add_frame(symbol, 2, color)
            character.add_scene(fade)
            character.layer = 1
        for char_id in self.term.characters():
            self.term.chars[char_id].set_scene_ease("flash", flash_ease)

    def step_lightning_strike(self) -> None:
        """Draw the bolt down a few characters a frame; when it lands, throw
        sparks and flash the bolt and the text."""
        if self.strike_progression_delay:
            self.strike_progression_delay -= 1
            return
        if not self.pending_strike_chars:
            return
        for _ in range(randint(1, 3)):
            if not self.pending_strike_chars:
                break
            strike_char = self.pending_strike_chars.pop(0)
            self.active_strike_chars.append(strike_char)
            self.term.set_visible(strike_char, True)
            self.strike_progression_delay = 1
            if not self.pending_strike_chars:
                impact_char = self.active_strike_chars[len(self.active_strike_chars) - 1]
                impact = copy(self.term.chars[impact_char].coord)
                for _ in range(randint(12, 18)):
                    self.emit_spark(impact)
                self.last_strike_char = strike_char
                for bolt_char in self.active_strike_chars:
                    self.term.chars[bolt_char].activate_scene("flash")
                    self.term.activate(bolt_char)
                self.active_strike_chars.clear()
                for char_id in self.term.characters():
                    self.term.chars[char_id].activate_scene("flash")
                    self.term.activate(char_id)

    def emit_spark(self, impact: Coord) -> None:
        spark, created = self.spark_pool.acquire(self.term)
        if spark < 0:
            return
        if created:
            self.init_spark(spark, self.spark_gradient)
        character = self.term.chars[spark]
        character.move_to(impact)
        # Each spark arcs out to one side and falls to the bottom of the canvas.
        path = Path(random.uniform(0.1, 0.25), hold_time=30)
        path.ease = out_quint
        distance = randint(4, 20)
        direction = random.choice([1, -1])
        target = Coord(impact.column + distance * direction, self.term.canvas.bottom)
        control_column = impact.column - (impact.column - target.column) // 2
        control = Coord(control_column, randint(1, self.term.canvas.top))
        path.add_curved_waypoint(target, control)
        character.activate_scene("glow")
        character.activate_path(character.add_path("spark", path))
        self.term.set_visible(spark, True)
        self.term.activate(spark)

    def strike_faded(self, strike_char: int32) -> None:
        """A bolt character has faded out: light up the text it hit and put it away."""
        self.term.set_visible(strike_char, False)
        hit = copy(self.term.chars[strike_char].coord)
        target = self.term.at(hit)
        if target >= 0 and self.term.chars[target].visible:
            self.term.chars[target].activate_scene("glow")
            self.pending_glow_chars.append(target)
        self.available_strike_chars.append(strike_char)
        if strike_char == self.last_strike_char:
            self.strike_in_progress = False

    # -- rain -----------------------------------------------------------------

    def rain(self) -> None:
        if self.delay:
            self.delay -= 1
            return
        for _ in range(randint(1, 6)):
            spawn_column = randint(1 - self.term.canvas.top, self.term.canvas.right)
            self.emit_raindrop(Coord(spawn_column - 1, self.term.canvas.top + 1))
        self.delay = randint(1, 7)

    def emit_raindrop(self, origin: Coord) -> None:
        raindrop, created = self.rain_pool.acquire(self.term)
        if created:
            self.init_raindrop(raindrop)
        character = self.term.chars[raindrop]
        character.move_to(origin)
        # Raindrops fall diagonally, one column right for each row down.
        fall = Path(random.uniform(0.5, 1.5))
        fall.add_waypoint(Coord(origin.column + self.term.canvas.top + 1,
                                self.term.canvas.bottom - 1))
        character.activate_path(character.add_path("fall", fall))
        self.term.set_visible(raindrop, True)
        self.term.activate(raindrop)

    # -- frames ---------------------------------------------------------------

    def step(self) -> bool:
        if not self.term.has_active() and self.phase == "complete":
            return False
        if self.phase == "pre-storm":
            for char_id in self.term.characters():
                self.term.chars[char_id].activate_scene("fade")
                self.term.activate(char_id)
            self.phase = "waiting"
        elif self.phase == "storm":
            self.rain()
            if not self.strike_in_progress and random.random() < 0.008:
                self.strike_in_progress = True
                self.lightning_strike()
            if self.strike_in_progress:
                self.step_lightning_strike()
            for char_id in self.pending_glow_chars:
                self.term.activate(char_id)
            self.pending_glow_chars.clear()
            if self.frames - self.storm_start >= STORM_FRAMES and not self.strike_in_progress:
                for char_id in self.term.characters():
                    self.term.chars[char_id].activate_scene("unfade")
                    self.term.activate(char_id)
                self.phase = "complete"
        self.update()
        self.frames += 1
        return True

    def update(self) -> None:
        self.term.tick()
        events = self.term.take_events()
        for event in events:
            char_id = event.char_id
            if event.kind == EventKind.PATH_COMPLETE:
                if self.rain_pool.owns(char_id):
                    self.rain_pool.reclaim(self.term, char_id)
                continue
            if self.spark_pool.owns(char_id):
                self.spark_pool.reclaim(self.term, char_id)
            elif char_id in self.strike_ids:
                if event.name == "flash":
                    self.term.chars[char_id].activate_scene("fade")
                else:
                    self.strike_faded(char_id)
            elif char_id == self.reference_char and event.name == "fade":
                # The text has dimmed: the storm begins.
                self.phase = "storm"
                self.storm_start = self.frames
        self.term.prune()

    def frame(self) -> str:
        return self.term.render()
