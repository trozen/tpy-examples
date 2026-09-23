"""matrix: digital rain falls down the canvas, then fills it and resolves into the text."""
from __future__ import annotations

import random
from typing import Final

from tpy import int32, Own, copy

from engine import Grouping, Scene, Terminal, randint
from geometry import Coord
from graphics import (Color, Direction, Gradient, adjust_brightness, choose_color, hex_color,
                      hex_colors)

RAIN_SYMBOLS = ["2", "5", "9", "8", "Z", "*", ")", ":", ".", '"', "=", "+", "-", "¦", "|", "_",
                "ｦ", "ｱ", "ｳ", "ｴ", "ｵ", "ｶ", "ｷ", "ｹ", "ｺ", "ｻ", "ｼ", "ｽ", "ｾ", "ｿ", "ﾀ", "ﾂ",
                "ﾃ", "ﾅ", "ﾆ", "ﾇ", "ﾈ", "ﾊ", "ﾋ", "ﾎ", "ﾏ", "ﾐ", "ﾑ", "ﾒ", "ﾓ", "ﾔ", "ﾕ", "ﾗ",
                "ﾘ", "ﾜ"]
HIGHLIGHT_COLOR = "dbffdb"
RAIN_COLOR_GRADIENT = ["92be92", "185318"]
RAIN_FALL_DELAY_RANGE: Final[tuple[int32, int32]] = (2, 15)
RAIN_COLUMN_DELAY_RANGE: Final[tuple[int32, int32]] = (3, 9)
# TTE rains for 15 seconds of wall-clock time. Counting frames instead, at
# TTE's 60 per second, makes a run the same whatever the terminal's speed.
RAIN_FRAMES = 15 * 60
SYMBOL_SWAP_CHANCE = 0.005
COLOR_SWAP_CHANCE = 0.001
RESOLVE_DELAY = 3
FINAL_GRADIENT_STOPS = ["92be92", "336b33"]
FINAL_GRADIENT_STEPS = [12]
FINAL_GRADIENT_FRAMES = 3


class RainColumn:
    """One column of the canvas, raining down: characters top to bottom."""
    chars: list[int32]
    pending: list[int32]
    visible: list[int32]
    phase: str
    base_fall_delay: int32
    fall_delay: int32
    length: int32
    hold_time: int32
    drop_chance: float

    def __init__(self, term: Terminal, chars: Own[list[int32]]) -> None:
        self.chars = chars
        self.chars.reverse()
        self.pending = []
        self.visible = []
        self.phase = "rain"
        self.base_fall_delay = 0
        self.fall_delay = 0
        self.length = 0
        self.hold_time = 0
        self.drop_chance = 0.08
        self.setup(term, "rain")

    def setup(self, term: Terminal, phase: str) -> None:
        self.pending.clear()
        self.phase = phase
        for char_id in self.chars:
            term.set_visible(char_id, False)
            self.pending.append(char_id)
            term.chars[char_id].return_home()
        self.visible.clear()
        if phase == "fill":
            self.base_fall_delay = randint(max(RAIN_FALL_DELAY_RANGE[0] // 3, 1),
                                                  max(RAIN_FALL_DELAY_RANGE[1] // 3, 1))
        else:
            self.base_fall_delay = randint(RAIN_FALL_DELAY_RANGE[0], RAIN_FALL_DELAY_RANGE[1])
        self.fall_delay = 0
        if phase == "rain":
            self.length = randint(max(1, int(len(self.chars) * 0.1)), len(self.chars))
        else:
            self.length = len(self.chars)
        self.hold_time = 0
        if self.length == len(self.chars):
            self.hold_time = randint(20, 45)

    def trim(self, term: Terminal, rain_colors: Gradient) -> None:
        if not self.visible:
            return
        term.set_visible(self.visible.pop(0), False)
        if len(self.visible) > 1:
            # The new tail of the column fades out.
            tail = term.chars[self.visible[0]]
            count = len(rain_colors.spectrum)
            shade = rain_colors.spectrum[random.randrange(count - 3, count)]
            tail.set_appearance(tail.visual.symbol, adjust_brightness(shade, 0.65))

    def drop(self, term: Terminal) -> None:
        still_on_canvas: list[int32] = []
        for char_id in self.visible:
            character = term.chars[char_id]
            character.move_to(Coord(character.coord.column, character.coord.row - 1))
            if character.coord.row < term.canvas.bottom:
                term.set_visible(char_id, False)
            else:
                still_on_canvas.append(char_id)
        self.visible = still_on_canvas

    def resolve_next(self) -> int32:
        return self.visible.pop(randint(0, len(self.visible) - 1))

    def tick(self, term: Terminal, rain_colors: Gradient, highlight: Color) -> None:
        if not self.fall_delay:
            if self.pending:
                # The newest drop is highlighted; the one before it takes a rain color.
                next_id = self.pending.pop(0)
                term.chars[next_id].set_appearance(random.choice(RAIN_SYMBOLS), highlight)
                if self.visible:
                    previous = term.chars[self.visible[len(self.visible) - 1]]
                    previous.set_appearance(previous.visual.symbol,
                                            choose_color(rain_colors.spectrum))
                term.set_visible(next_id, True)
                self.visible.append(next_id)
            elif self.visible:
                head = term.chars[self.visible[len(self.visible) - 1]]
                if head.visual.colored and head.visual.fg == highlight:
                    head.set_appearance(head.visual.symbol, choose_color(rain_colors.spectrum))
                if self.hold_time:
                    self.hold_time -= 1
                elif self.phase == "rain":
                    if random.random() < self.drop_chance:
                        self.drop(term)
                    self.trim(term, rain_colors)
            if len(self.visible) > self.length:
                self.trim(term, rain_colors)
            self.fall_delay = self.base_fall_delay
        else:
            self.fall_delay -= 1
        for char_id in self.visible:
            character = term.chars[char_id]
            symbol = character.visual.symbol
            if random.random() < SYMBOL_SWAP_CHANCE:
                symbol = random.choice(RAIN_SYMBOLS)
            if random.random() < COLOR_SWAP_CHANCE:
                character.set_appearance(symbol, choose_color(rain_colors.spectrum))
            else:
                character.set_symbol(symbol)


class Matrix:
    term: Terminal
    columns: list[RainColumn]
    pending: list[int32]
    active: list[int32]
    full: list[int32]
    rain_colors: Gradient
    highlight: Color
    column_delay: int32
    resolve_delay: int32
    frames: int32  # frames rendered so far
    final_frame_shown: bool
    rain_complete: bool
    phase: str

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.columns = []
        self.pending = []
        self.active = []
        self.full = []
        rain_stops = hex_colors(RAIN_COLOR_GRADIENT)
        self.rain_colors = Gradient(rain_stops, [6])
        self.highlight = hex_color(HIGHLIGHT_COLOR)
        self.column_delay = 0
        self.resolve_delay = RESOLVE_DELAY
        self.frames = 0
        self.final_frame_shown = False
        self.rain_complete = False
        self.phase = "rain"
        self.build()

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.RADIAL)
        highlight = copy(self.highlight)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            final_color = final_colors[copy(character.input_coord)]
            resolve = Scene("resolve")
            resolve_gradient = Gradient([highlight, final_color], [8])
            for color in resolve_gradient.spectrum:
                resolve.add_frame(character.input_symbol, FINAL_GRADIENT_FRAMES, color)
            character.add_scene(resolve)
        columns = self.term.grouped(Grouping.COLUMN_LEFT_TO_RIGHT, include_fill=True)
        while columns:
            self.pending.append(len(self.columns))
            self.columns.append(RainColumn(self.term, columns.pop(0)))
        random.shuffle(self.pending)

    def step(self) -> bool:
        if self.phase == "rain" or self.phase == "fill":
            self.rain()
        elif self.phase == "resolve":
            self.resolve()
        if (self.full or self.active or self.term.has_active() or self.pending
                or not self.rain_complete):
            self.update()
            return True
        if not self.final_frame_shown:
            self.final_frame_shown = True
            self.update()
            return True
        return False

    def rain(self) -> None:
        if not self.column_delay:
            if self.phase == "rain":
                for _ in range(randint(1, 3)):
                    if self.pending:
                        self.active.append(self.pending.pop(0))
                self.column_delay = randint(RAIN_COLUMN_DELAY_RANGE[0],
                                                   RAIN_COLUMN_DELAY_RANGE[1])
            else:
                while self.pending:
                    self.active.append(self.pending.pop(0))
                self.column_delay = 1
        else:
            self.column_delay -= 1
        for column_id in self.active:
            column = self.columns[column_id]
            column.tick(self.term, self.rain_colors, self.highlight)
            if not column.pending:
                if column.phase == "fill":
                    if column_id not in self.full:
                        self.full.append(column_id)
                elif not column.visible:
                    column.setup(self.term, self.phase)
                    self.pending.append(column_id)
        still_raining: list[int32] = []
        for column_id in self.active:
            if self.columns[column_id].visible:
                still_raining.append(column_id)
        self.active = still_raining
        if self.phase == "fill" and not self.pending:
            filled = True
            for column_id in self.active:
                if self.columns[column_id].pending or self.columns[column_id].phase != "fill":
                    filled = False
            if filled:
                self.phase = "resolve"
                self.active.clear()
        if self.phase == "rain" and self.frames > RAIN_FRAMES:
            # Time's up: let the rain drain away and fill every column instead.
            self.rain_complete = True
            self.phase = "fill"
            for column_id in self.active:
                self.columns[column_id].hold_time = 0
                self.columns[column_id].drop_chance = 1.0
            for column_id in self.pending:
                self.columns[column_id].setup(self.term, self.phase)

    def resolve(self) -> None:
        for column_id in self.full:
            column = self.columns[column_id]
            column.tick(self.term, self.rain_colors, self.highlight)
            if not column.visible:
                continue
            if self.resolve_delay:
                self.resolve_delay -= 1
                continue
            for _ in range(randint(1, 4)):
                if column.visible:
                    char_id = column.resolve_next()
                    if self.term.chars[char_id].is_fill:
                        self.term.set_visible(char_id, False)
                    else:
                        self.term.chars[char_id].activate_scene("resolve")
                        self.term.activate(char_id)
            self.resolve_delay = RESOLVE_DELAY
        still_resolving: list[int32] = []
        for column_id in self.full:
            if self.columns[column_id].visible:
                still_resolving.append(column_id)
        self.full = still_resolving

    def update(self) -> None:
        self.frames += 1
        self.term.tick()
        self.term.events.clear()
        self.term.prune()

    def frame(self) -> str:
        return self.term.render()
