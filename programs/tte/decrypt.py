"""decrypt: the text is typed out as ciphertext, then decrypted character by character."""
from __future__ import annotations

import random

from tpy import int32, Own, copy

from engine import EventKind, Scene, Terminal, randint, split_characters
from graphics import Color, Direction, Gradient, choose_color, hex_colors

TYPING_SPEED = 2
CIPHERTEXT_COLORS = ["008000", "00cb00", "00ff00"]
FINAL_GRADIENT_STOPS = ["eda000"]
FINAL_GRADIENT_STEPS = [12]


# TTE builds these with chr() over code point ranges: keyboard characters,
# block elements, box drawing, and Latin-1 and Latin Extended letters.
KEYBOARD = ("!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ["
            "\\]^_`abcdefghijklmnopqrstuvwxyz{|}~")
BLOCKS = "█▉▊▋▌▍▎▏▐░▒▓▔▕▖▗▘▙▚▛▜▝▞▟"
BOX_DRAWING = ("─━│┃┄┅┆┇┈┉┊┋┌┍┎┏┐┑┒┓└┕┖┗┘┙┚┛├┝┞┟┠┡┢┣┤┥┦┧┨┩┪┫┬┭┮┯┰┱┲┳┴┵┶┷┸┹┺┻"
               "┼┽┾┿╀╁╂╃╄╅╆╇╈╉╊╋╌╍╎╏═║╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬╭╮╯╰╱╲╳╴╵╶╷"
               "╸╹╺╻╼╽╾")
LATIN = ("®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèé"
         "êëìíîïðñòóôõö÷øùúûüýþÿĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥ"
         "ĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠš"
         "ŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽžſƀƁƂƃƄƅƆƇƈƉƊƋƌƍƎƏƐƑƒƓƔƕƖƗƘƙƚƛƜƝ"
         "ƞƟƠơƢƣƤƥƦƧƨƩƪƫƬƭƮƯưƱƲƳƴƵƶƷƸƹƺƻƼƽƾƿǀǁǂǃ")


class Decrypt:
    term: Terminal
    typing_pending: list[int32]
    phase: str

    def __init__(self, term: Own[Terminal]) -> None:
        self.term = term
        self.typing_pending = []
        self.phase = "typing"
        self.build()

    def build(self) -> None:
        symbols = split_characters(KEYBOARD + BLOCKS + BOX_DRAWING + LATIN)
        cipher_colors = hex_colors(CIPHERTEXT_COLORS)
        final_stops = hex_colors(FINAL_GRADIENT_STOPS)
        final_gradient = Gradient(final_stops, FINAL_GRADIENT_STEPS)
        final_colors = self.term.text_colors(final_gradient, Direction.VERTICAL)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            typing = Scene("typing")
            for block in ["▉", "▓", "▒", "░"]:
                typing.add_frame(block, 2, choose_color(cipher_colors))
            symbol = random.choice(symbols)
            typing.add_frame(symbol, 1, choose_color(cipher_colors))
            character.add_scene(typing)
            self.typing_pending.append(char_id)
        for char_id in self.term.characters():
            character = self.term.chars[char_id]
            color = choose_color(cipher_colors)
            fast = Scene("fast_decrypt")
            for _ in range(80):
                fast.add_frame(random.choice(symbols), 2, color)
            character.add_scene(fast)
            slow = Scene("slow_decrypt")
            for _ in range(randint(1, 15)):
                symbol = random.choice(symbols)
                if randint(0, 100) <= 30:
                    duration = random.randrange(35, 60)
                else:
                    duration = random.randrange(3, 6)
                slow.add_frame(symbol, duration, color)
            character.add_scene(slow)
            discovered = Scene("discovered")
            white = Color(255, 255, 255)
            final_color = final_colors[copy(character.input_coord)]
            discovered_gradient = Gradient([white, final_color], [10])
            input_symbol = [character.input_symbol]
            discovered.apply_gradient_to_symbols(input_symbol, 5, discovered_gradient)
            character.add_scene(discovered)

    def step(self) -> bool:
        if self.phase == "typing":
            if self.typing_pending or self.term.has_active():
                if self.typing_pending and randint(0, 100) <= 75:
                    for _ in range(TYPING_SPEED):
                        if self.typing_pending:
                            char_id = self.typing_pending.pop(0)
                            self.term.set_visible(char_id, True)
                            self.term.chars[char_id].activate_scene("typing")
                            self.term.activate(char_id)
                self.update()
                return True
            for char_id in self.term.characters():
                self.term.chars[char_id].activate_scene("fast_decrypt")
                self.term.activate(char_id)
            self.phase = "decrypting"
        if self.term.has_active():
            self.update()
            return True
        return False

    def update(self) -> None:
        self.term.tick()
        events = self.term.take_events()
        for event in events:
            if event.kind != EventKind.SCENE_COMPLETE:
                continue
            # Each finished stage of decryption hands over to the next.
            if event.name == "fast_decrypt":
                self.term.chars[event.char_id].activate_scene("slow_decrypt")
            elif event.name == "slow_decrypt":
                self.term.chars[event.char_id].activate_scene("discovered")
        self.term.prune()

    def frame(self) -> str:
        return self.term.render()
