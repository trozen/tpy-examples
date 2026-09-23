"""print: the text is printed line by line, a print head returning for each new line."""
from __future__ import annotations

from tpy import int32, Own, copy

from easing import in_out_quad
from engine import EventKind, Grouping, Path, Scene, Terminal
from geometry import Coord
from graphics import Color, Direction, Gradient, hex_colors

PRINT_SPEED = 2
PRINT_HEAD_RETURN_SPEED = 1.5
FINAL_GRADIENT_STOPS = ["02b8bd", "c1f0e3", "00ffa0"]
FINAL_GRADIENT_STEPS = [12]
PRINT_SYMBOLS = ["█", "▓", "▒", "░"]


def all_fill(term: Terminal, char_ids: list[int32]) -> bool:
    for char_id in char_ids:
        if not term.chars[char_id].is_fill:
            return False
    return True


class Row:
    """One line of the text, printed at the bottom of the canvas and pushed up
    as later lines are printed."""
    untyped: list[int32]
    typed: list[int32]

    def __init__(self) -> None:
        self.untyped = []
        self.typed = []

    def typed_blank(self, term: Terminal) -> bool:
        return all_fill(term, self.typed)

    def untyped_blank(self, term: Terminal) -> bool:
        return all_fill(term, self.untyped)

    def move_up(self, term: Terminal) -> None:
        for char_id in self.typed:
            column = term.chars[char_id].coord.column
            row = term.chars[char_id].coord.row
            term.chars[char_id].move_to(Coord(column, row + 1))


class Printer:
    term: Terminal
    head: int32
    rows: list[Row]
    current: int32
    typing: bool
    last_column: int32

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.head = self.term.add_character("█", Coord(1, 1))
        self.rows = []
        self.current = 0
        self.typing = True
        self.last_column = 0
        self.build()

    def build(self) -> None:
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.DIAGONAL)
        white = Color(255, 255, 255)
        for line in self.term.grouped(Grouping.ROW_TOP_TO_BOTTOM, include_fill=True):
            row = Row()
            # A blank line prints as one space; others stop at their last character.
            printed: list[int32] = []
            right_extent = 0
            for char_id in line:
                character = self.term.chars[char_id]
                if not character.is_fill:
                    right_extent = max(right_extent, character.input_coord.column)
            for char_id in line:
                if right_extent == 0 and printed:
                    break
                if right_extent == 0 or self.term.chars[char_id].input_coord.column <= right_extent:
                    printed.append(char_id)
            for char_id in printed:
                character = self.term.chars[char_id]
                home = copy(character.input_coord)
                character.move_to(Coord(home.column, 1))
                final_color = final_colors.get(home, white)
                gradient = Gradient([white, final_color], [5])
                symbols = [PRINT_SYMBOLS[0], PRINT_SYMBOLS[1], PRINT_SYMBOLS[2], PRINT_SYMBOLS[3],
                           character.input_symbol]
                typed = Scene("typed")
                typed.apply_gradient_to_symbols(symbols, 3, gradient)
                character.add_scene(typed)
                character.activate_scene("typed")
                row.untyped.append(char_id)
            self.rows.append(row)

    def next_row(self) -> None:
        """Push the printed lines up a row and send the print head back."""
        for i in range(self.current + 1):
            self.rows[i].move_up(self.term)
        previous = self.current
        self.current += 1
        row = self.rows[self.current]
        if not self.rows[previous].typed_blank(self.term) and not row.untyped_blank(self.term):
            # Start the line at its first character rather than at the margin.
            left_extent = self.term.canvas.right
            for char_id in row.untyped:
                if not self.term.chars[char_id].is_fill:
                    left_extent = min(left_extent, self.term.chars[char_id].input_coord.column)
            kept: list[int32] = []
            for char_id in row.untyped:
                column = self.term.chars[char_id].input_coord.column
                if left_extent <= column <= self.term.canvas.text_right:
                    kept.append(char_id)
            row.untyped = kept
        head = self.term.chars[self.head]
        head.move_to(Coord(self.last_column, 1))
        self.term.set_visible(self.head, True)
        head.clear_paths()
        carriage_return = Path(PRINT_HEAD_RETURN_SPEED)
        carriage_return.ease = in_out_quad
        first_column = self.term.chars[row.untyped[0]].input_coord.column
        carriage_return.add_waypoint(Coord(first_column, 1))
        head.activate_path(head.add_path("carriage_return", carriage_return))
        self.term.activate(self.head)

    def step(self) -> bool:
        if not self.term.has_active() and not self.typing:
            return False
        row = self.rows[self.current]
        if self.term.chars[self.head].active_path >= 0:
            pass
        elif row.untyped:
            for _ in range(min(len(row.untyped), PRINT_SPEED)):
                char_id = row.untyped.pop(0)
                row.typed.append(char_id)
                self.term.set_visible(char_id, True)
                self.term.activate(char_id)
                self.last_column = self.term.chars[char_id].input_coord.column
        elif self.current + 1 < len(self.rows):
            self.next_row()
        else:
            self.typing = False
        self.term.tick()
        for event in self.term.take_events():
            if event.kind == EventKind.PATH_COMPLETE and event.char_id == self.head:
                self.term.set_visible(self.head, False)
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
