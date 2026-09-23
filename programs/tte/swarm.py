"""swarm: the text flies in as swarms, each roaming the canvas before it settles."""
from __future__ import annotations

import math
import random

from tpy import int32, Own, copy

from easing import in_out_quad, in_out_sine, out_sine
from engine import Path, Scene, Sync, Terminal, randint
from geometry import Coord, TERMINAL_ROW_SCALE, find_coords_in_circle, find_coords_on_circle
from graphics import Color, Direction, Gradient, choose_color, hex_color, hex_colors

BASE_COLORS = ["31a0d4"]
FLASH_COLOR = "f2ea79"
SWARM_SIZE = 0.1  # the share of the text in each swarm
SWARM_COORDINATION = 0.8  # the chance each member follows when one moves on
SWARM_AREA_COUNT_MIN = 2
SWARM_AREA_COUNT_MAX = 4
FINAL_GRADIENT_STOPS = ["31b900", "f0ff65"]
FINAL_GRADIENT_STEPS = [12]


class Swarm:
    term: Terminal
    swarms: list[list[int32]]
    current: list[int32]
    active_area: str
    call_next: bool

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.swarms = []
        self.current = []
        self.active_area = "0_swarm_area"
        self.call_next = True
        self.build()

    def make_swarms(self, swarm_size: int32) -> None:
        # Top to bottom, left to right, cut into swarms; a runt joins the one before.
        unswarmed = self.term.characters()
        unswarmed.reverse()
        while unswarmed:
            swarm: list[int32] = []
            for _ in range(swarm_size):
                if unswarmed:
                    swarm.append(unswarmed.pop())
            self.swarms.append(swarm)
        last = self.swarms.pop()
        if len(last) < swarm_size // 2:
            for char_id in last:
                self.swarms[len(self.swarms) - 1].append(char_id)
        else:
            self.swarms.append(last)

    def build(self) -> None:
        swarm_size = max(round(len(self.term.characters()) * SWARM_SIZE), 1)
        self.make_swarms(swarm_size)
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.HORIZONTAL)
        base_colors = hex_colors(BASE_COLORS)
        flash = hex_color(FLASH_COLOR)
        small_side = min(self.term.canvas.right, self.term.canvas.top)
        radius = TERMINAL_ROW_SCALE * max(small_side // 2, 1)
        area_radius = max(small_side // 6, 1) * TERMINAL_ROW_SCALE
        for swarm in self.swarms:
            # Out of the swarm's color to a bright flash and back, as it flies.
            base = choose_color(base_colors)
            swarm_gradient = Gradient([base, flash], [7])
            mirror: list[Color] = []
            for color in swarm_gradient.spectrum:
                mirror.append(color)
            for _ in range(10):
                mirror.append(flash)
            for color in reversed(swarm_gradient.spectrum):
                mirror.append(color)
            # The swarm roams from just off the canvas through a few areas,
            # each a hop of `radius` from the one before.
            spawn = self.term.canvas.random_coord_outside()
            area_count = randint(SWARM_AREA_COUNT_MIN, SWARM_AREA_COUNT_MAX)
            areas: dict[Coord, list[Coord]] = {}
            focus = copy(spawn)
            chosen = 0
            while chosen < area_count:
                candidates = find_coords_on_circle(focus, radius,
                                                   round(2 * math.pi * radius / TERMINAL_ROW_SCALE))
                random.shuffle(candidates)
                next_focus = Coord(0, 0)
                found = False
                for coord in candidates:
                    if self.term.canvas.coord_is_in_canvas(coord):
                        next_focus = coord
                        found = True
                        break
                if not found:
                    next_focus = self.term.canvas.random_coord()
                chosen += 1
                areas[focus] = find_coords_in_circle(focus, area_radius)
                focus = next_focus
            for char_id in swarm:
                home = copy(self.term.chars[char_id].input_coord)
                final_color = final_colors[home]
                self.prepare_character(char_id, spawn, mirror, areas, flash, final_color)

    def prepare_character(self, char_id: int32, spawn: Coord, mirror: list[Color],
                          areas: dict[Coord, list[Coord]], flash: Color, final_color: Color) -> None:
        character = self.term.chars[char_id]
        symbol = character.input_symbol
        character.move_to(spawn)
        flight = Scene("flash", sync=Sync.DISTANCE)
        for color in mirror:
            flight.add_frame(symbol, 1, color)
        character.add_scene(flight)
        names: list[str] = []
        paths: list[Path] = []
        area_number = 0
        for coords in areas.values():
            name = f"{area_number}_swarm_area"
            origin = Path(0.4)
            origin.ease = out_sine
            origin.add_waypoint(coords[randint(0, len(coords) - 1)])
            names.append(name)
            paths.append(origin)
            for _ in range(2):
                wander = Path(0.18)
                wander.ease = in_out_sine
                wander.add_waypoint(coords[randint(0, len(coords) - 1)])
                names.append(str(len(names)))
                paths.append(wander)
            area_number += 1
        home = Path(0.45)
        home.ease = in_out_quad
        home_coord = copy(character.input_coord)
        home.add_waypoint(home_coord)
        names.append(str(len(names)))
        paths.append(home)
        settle = Scene("settle")
        settle_gradient = Gradient([flash, final_color], [10])
        for color in settle_gradient.spectrum:
            settle.add_frame(symbol, 3, color)
        character.add_scene(settle)
        # One path after another, all the way home.
        for i in range(len(paths)):
            # Not a conditional expression: tpy binds that to a view of a
            # temporary here, which dangles (README).
            then = ""
            if i + 1 < len(names):
                then = names[i + 1]
            if names[i].endswith("_swarm_area"):
                character.add_path(names[i], paths.pop(0), then=then, scene="flash",
                                   start_layer=1, stop_scene=True)
            elif i == len(names) - 1:
                character.add_path(names[i], paths.pop(0), scene="flash",
                                   end_scene="settle", end_layer=0)
            else:
                character.add_path(names[i], paths.pop(0), then=then)

    def step(self) -> bool:
        if not self.swarms and not self.term.has_active():
            return False
        if self.swarms and self.call_next:
            self.call_next = False
            self.current = self.swarms.pop()
            self.active_area = "0_swarm_area"
            for char_id in self.current:
                self.term.chars[char_id].activate_path_named("0_swarm_area")
                self.term.set_visible(char_id, True)
                self.term.activate(char_id)
        if len(self.term.active_ids) < len(self.current):
            self.call_next = True
        # When one member reaches the next area, most of the swarm follows it there.
        for char_id in self.current:
            path = self.term.chars[char_id].active_path_name()
            if (path and path != self.active_area and path.endswith("_swarm_area")
                    and int(path[0]) > int(self.active_area[0])):
                self.active_area = path
                for other in self.current:
                    if other != char_id and random.random() < SWARM_COORDINATION:
                        self.term.chars[other].activate_path_named(self.active_area)
                break
        self.term.tick()
        self.term.events.clear()
        self.term.prune()
        return True

    def frame(self) -> str:
        return self.term.render()
