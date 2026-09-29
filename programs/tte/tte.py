"""tte: terminal text effects, after TerminalTextEffects by ChrisBuilds.

Plays an animated effect over some text, in place in the terminal:

    tpy tte.py                          # spawn, over a built-in demo text
    tpy tte.py -h                       # the options, and the other effects
    tpy tte.py beams                    # one effect, over the demo text
    tpy tte.py beams -i notes.txt       # ... over a file
    ls -l | tpy tte.py decrypt          # ... or over whatever is piped in
    tpy tte.py burn --seed 7            # the same run every time
    tpy tte.py --demo                   # every effect in turn

When stdout is not a terminal the frames are not drawn: each effect prints how
many frames it rendered and a digest of them, which is what the gallery's test
harness records.
"""
from __future__ import annotations

import os
import random
import sys
import time
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from typing import Protocol

from tpy import int32, int64

from beams import Beams
from blackhole import Blackhole
from crumble import Crumble
from burn import Burn
from decrypt import Decrypt
from donut import Donut
from engine import RESET, Terminal
from expand import Expand
from fireworks import Fireworks
from graphics import Color, fg_sequence, shift_color_towards
from highlight import Highlight
from laseretch import LaserEtch
from matrix import Matrix
from printer import Printer
from rings import Rings
from sandstorm import Sandstorm
from spawn import Spawn
from spotlights import Spotlights
from swarm import Swarm
from thunderstorm import Thunderstorm
from vhstape import VHSTape
from wipe import Wipe

EFFECTS = ["beams", "matrix", "decrypt", "burn", "thunderstorm", "expand", "highlight", "print",
           "vhstape", "wipe", "laseretch", "blackhole", "spotlights", "fireworks", "swarm",
           "crumble", "rings", "spawn", "sandstorm", "donut"]
FRAME_RATE = 60
SEPARATOR_SPEED = 3  # cells per frame
SEPARATOR_TRAIL = 8  # cells from the light to the dark trace

DEMO_TEXT = """\
╺┳╸╻ ╻┏━┓┏┓ ┏━┓┏━┓╻ ╻╺┳╸╻ ╻┏━┓┏┓╻
 ┃ ┃ ┃┣┳┛┣┻┓┃ ┃┣━┛┗┳┛ ┃ ┣━┫┃ ┃┃┗┫
 ╹ ┗━┛╹┗╸┗━┛┗━┛╹   ╹  ╹ ╹ ╹┗━┛╹ ╹

terminal text effects, compiled to C++ ({effect})

TurboPython compiles Python to C++. Add the type annotations
it needs, and the same program builds into a native binary,
with ownership the compiler checks rather than a runtime.

This demo is TerminalTextEffects, rewritten in TurboPython:
a selection of its effects and the engine beneath them,
rendering the very same frames as the original, byte for byte.

Every character here is an index into one list, every scene
and path a plain value handed over with Own. No reference
counting, no shared objects, nothing to collect.

Run with -h to see the options and the other effects."""


class Effect(Protocol):
    def step(self) -> bool: ...

    def frame(self) -> str: ...


class Screen:
    """Draws frames in place on a terminal, or, when stdout is not one, keeps
    a count and an FNV-1a digest of them instead."""
    tty: bool
    width: int32
    frame_rate: int32  # frames a second; 0 draws as fast as the terminal takes them
    rows: int32
    frames: int32
    digest: int64
    last_frame_time: float

    def __init__(self, tty: bool, width: int32, frame_rate: int32) -> None:
        self.tty = tty
        self.width = width
        self.frame_rate = frame_rate
        self.rows = 0
        self.frames = 0
        self.digest = 0
        self.last_frame_time = 0.0

    def begin(self, rows: int32, columns: int32) -> None:
        self.rows = rows
        self.frames = 0
        self.digest = 2166136261
        if self.tty:
            # Scroll a blank canvas into view and remember where it ends.
            sys.stdout.write("\x1b[?25l")
            for _ in range(rows):
                sys.stdout.write(" " * columns + "\n")
            sys.stdout.write("\x1b7")
            self.last_frame_time = time.monotonic()

    def show(self, frame: str) -> None:
        self.frames += 1
        if not self.tty:
            data = frame.encode()
            for byte in data:
                self.digest = ((self.digest ^ int64(byte)) * 16777619) & 0xFFFFFFFF
            return
        if self.frame_rate > 0:
            delay = 1 / self.frame_rate - (time.monotonic() - self.last_frame_time)
            if delay > 0:
                time.sleep(delay)
        self.last_frame_time = time.monotonic()
        sys.stdout.write(f"\x1b8\x1b7\x1b[{self.rows}A{frame}")
        sys.stdout.flush()

    def end(self, name: str, separator: bool) -> None:
        if not self.tty:
            print(f"{name}: {self.frames} frames, digest {self.digest:08x}")
            return
        sys.stdout.write("\n")
        if separator:
            self.separator()
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()

    def separator(self) -> None:
        """A rule across the terminal under the finished effect, drawn by a
        small light flying left to right and leaving a dark trace behind it."""
        head = Color(255, 255, 255)
        trace = Color(58, 58, 58)
        step = 0
        while step < self.width + SEPARATOR_TRAIL:
            line = ""
            for column in range(min(step + 1, self.width)):
                fade = min((step - column) / SEPARATOR_TRAIL, 1.0)
                shade = shift_color_towards(head, trace, fade)
                line += fg_sequence(shade) + "─" + RESET
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
            time.sleep(1 / FRAME_RATE)
            step += SEPARATOR_SPEED
        # The light moves several cells a frame, so it can leave the rule before
        # its tail has faded out: finish the whole rule in the trace color.
        sys.stdout.write("\r" + fg_sequence(trace) + "─" * self.width + RESET + "\n")


def play[E: Effect](effect: E, screen: Screen) -> None:
    while effect.step():
        screen.show(effect.frame())


def run(name: str, text: str, width: int32, height: int32, screen: Screen,
        separator: bool) -> None:
    term = Terminal(text, width, height)
    screen.begin(term.canvas.top, term.canvas.right)
    match name:
        case "beams":
            play(Beams(term), screen)
        case "matrix":
            play(Matrix(term), screen)
        case "decrypt":
            play(Decrypt(term), screen)
        case "burn":
            play(Burn(term), screen)
        case "thunderstorm":
            play(Thunderstorm(term), screen)
        case "expand":
            play(Expand(term), screen)
        case "highlight":
            play(Highlight(term), screen)
        case "print":
            play(Printer(term), screen)
        case "vhstape":
            play(VHSTape(term), screen)
        case "wipe":
            play(Wipe(term), screen)
        case "laseretch":
            play(LaserEtch(term), screen)
        case "blackhole":
            play(Blackhole(term), screen)
        case "spotlights":
            play(Spotlights(term), screen)
        case "fireworks":
            play(Fireworks(term), screen)
        case "swarm":
            play(Swarm(term), screen)
        case "crumble":
            play(Crumble(term), screen)
        case "rings":
            play(Rings(term), screen)
        case "spawn":
            play(Spawn(term), screen)
        case "sandstorm":
            play(Sandstorm(term), screen)
        case "donut":
            play(Donut(term), screen)
        case _:
            raise ValueError(f"unknown effect {name}")
    screen.end(name, separator)


def read_stdin() -> str:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(0, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks).decode()


def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()


def main() -> int32:
    parser = ArgumentParser(
        prog="tte",
        description="Play an animated effect over text, in place in the terminal. "
                    "After TerminalTextEffects by ChrisBuilds.",
        epilog="effects:\n"
               "  beams         beams of light sweep the rows and columns, lighting up the text\n"
               "  matrix        digital rain falls, fills the canvas and resolves into the text\n"
               "  decrypt       the text is typed out as ciphertext, then decrypted\n"
               "  burn          fire spreads through the text, trailing smoke\n"
               "  thunderstorm  rain and lightning; the text glows where lightning strikes\n"
               "  expand        the text expands out of a single point at the center\n"
               "  highlight     a specular highlight sweeps diagonally across the text\n"
               "  print         the text is printed line by line by a returning print head\n"
               "  vhstape       lines glitch and tear like a worn VHS tape, then are redrawn\n"
               "  wipe          the text is wiped in diagonally from the top left\n"
               "  laseretch     a laser etches the text in along a winding path, throwing sparks\n"
               "  blackhole     a black hole swallows the text as stars, collapses and explodes\n"
               "  spotlights    spotlights search the dark text, then converge and light it up\n"
               "  fireworks     shells of characters launch, burst and fall into place\n"
               "  swarm         the text flies in as swarms that roam the canvas before settling\n"
               "  crumble       the text crumbles to dust, is vacuumed up and set back in place\n"
               "  rings         the text spins as rings that disperse and re-form\n"
               "  spawn         flames flare up, and a burst of light brings in the text (default)\n"
               "  sandstorm     the text drifts in on a sandstorm, then settles from the left\n"
               "  donut         a donut flies in, spinning; up close, the text is written on it",
        formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("effect", nargs="?", default="", metavar="EFFECT",
                        help="the effect to play (listed below; default: spawn)")
    parser.add_argument("--demo", action="store_true",
                        help="play every effect in turn (or just EFFECT) over a built-in demo text")
    parser.add_argument("-i", "--input-file",
                        help="text to use (default: stdin if piped, else a built-in demo text)")
    parser.add_argument("--frame-rate", type=int32, default=60,
                        help="frames a second (default: 60; 0: as fast as possible)")
    parser.add_argument("--seed", type=int32,
                        help="random seed, for a repeatable run "
                             "(default: 0 when not on a terminal)")
    args = parser.parse_args()

    effect = args.effect
    if effect and effect not in EFFECTS:
        print(f"tte: unknown effect '{args.effect}' (see tte --help)", file=sys.stderr)
        return 2
    if not effect and not args.demo:
        effect = "spawn"

    tty = os.isatty(1)
    width = 80
    height = 24
    if tty:
        size = os.get_terminal_size(1)
        width = int32(size.columns)
        height = int32(size.lines)
    seed = args.seed
    if seed is None and not tty:
        seed = 0

    text = ""
    if args.demo:
        pass
    elif args.input_file is not None:
        text = read_file(args.input_file)
        if not text.strip():
            print(f"tte: {args.input_file} is empty", file=sys.stderr)
            return 1
    elif not os.isatty(0):
        text = read_stdin()

    names: list[str] = []
    for name in EFFECTS:
        if not effect or effect == name:
            names.append(name)
    screen = Screen(tty, width, args.frame_rate)
    for i in range(len(names)):
        name = names[i]
        # Seeding each effect makes its run the same whether played alone or in turn.
        if seed is not None:
            random.seed(seed)
        between = i < len(names) - 1
        if text.strip():
            run(name, text, width, height, screen, between)
        else:
            run(name, DEMO_TEXT.replace("{effect}", name), width, height, screen, between)
    return 0


if __name__ == "__main__":
    sys.exit(main())
