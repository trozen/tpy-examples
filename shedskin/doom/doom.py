import math
import sys
import time

from tpy import Int32

import pygame

from engine import WIDTH, HEIGHT, Map, render

'''
Minimal DOOM WAD renderer

Goals:
-show inner workings of DOOM engine
-without relying on any graphics library
-omit some optimizations for readability (most notably, visplanes)
-less than 1000 lines while following PEP8
-compile with Shedskin to run at 60 FPS

Copyright 2023 Mark Dufour, license unclear.

Based on Java implementation by Leonardo Ono:

https://github.com/leonardo-ono/JavaDoomWADMapRendererTests

Compile with Shedskin for good performance (shedskin -e doom && make)!

http://github.com/shedskin/shedskin

'''

DEFAULT_WAD = 'doom1.wad'
MAP = 'E1M1'


# In the original this is a closure inside main(), capturing vx/vy and the
# player. Here the captured values are passed in and returned, which keeps it a
# plain function.
def move_player(angle: float, accel: float, strafe: float,
                vx: float, vy: float) -> tuple[float, float]:
    ax = accel * math.cos(angle + strafe)
    ay = accel * math.sin(angle + strafe)
    vx2 = min(max(vx + ax, -4.0), 4.0)
    vy2 = min(max(vy + ay, -4.0), 4.0)
    return (vx2, vy2)


def dump(wad: str, frames: Int32, path: str) -> None:
    """Render headlessly and write the raw paletted framebuffer.

    No window, no SDL: this is what the example is verified with, since the
    frames are deterministic when the player does not move. The output is the
    renderer's own 8-bit buffer, so it can be compared byte for byte against
    the unmodified upstream engine running under CPython.
    """
    map_ = Map(wad, MAP)
    buf = render(map_, 0)
    for i in range(frames):
        buf = render(map_, i)

    checksum = 0
    for i in range(len(buf)):
        checksum = (checksum * 31 + Int32(buf[i])) & 0xffffff
    print(f'frames {frames} checksum {checksum}')

    out = open(path, 'wb')
    out.write(bytes(buf))
    out.close()


def main(wad: str, test: bool) -> None:
    screen = pygame.open_screen(WIDTH, HEIGHT, 'DOOM')

    map_ = Map(wad, MAP)
    player = map_.player
    pygame.set_palette(screen, map_.palette)
    frame_count = 0

    vx = 0.0
    vy = 0.0
    vz = 0.0
    va = 0.0

    delta = 1.0 / 60.0
    angular_accel = 30.0
    linear_accel = 0.4
    strafe = math.radians(90)
    prev = 0.0

    ingame = True
    while ingame:
        pygame.pump(screen)
        if screen.quit_requested or pygame.key_pressed(pygame.K_q):
            ingame = False

        ctrl = pygame.key_pressed(pygame.K_LCTRL)
        left = pygame.key_pressed(pygame.K_LEFT)
        right = pygame.key_pressed(pygame.K_RIGHT)

        # angular speed
        if not ctrl:
            if right:
                va -= angular_accel * delta
            if left:
                va += angular_accel * delta

            va = min(max(va, -30.0), 30.0)

        player.angle += va * delta
        va = va * (1.0 - 8.0 * delta)

        # linear speeds
        if ctrl:
            if left:
                vx, vy = move_player(player.angle, linear_accel, strafe, vx, vy)
            if right:
                vx, vy = move_player(player.angle, linear_accel, -strafe, vx, vy)

        if pygame.key_pressed(pygame.K_UP):
            vx, vy = move_player(player.angle, linear_accel, 0.0, vx, vy)

        if pygame.key_pressed(pygame.K_DOWN):
            vx, vy = move_player(player.angle, -linear_accel, 0.0, vx, vy)

        # update player
        player.x += vx
        player.y += vy
        vx *= 0.95
        vy *= 0.95
        if player.z < player.floor_h + 48:
            player.z += 0.1 * (player.floor_h + 48 - player.z)
            vz = 0.0
        else:
            vz -= 0.1
            player.z += max(-5.0, vz)
        player.update()

        # render!
        t0 = time.time()

        buf = render(map_, frame_count)
        pygame.present(screen, buf)

        if not test:
            pygame.tick(screen, 60)

        delta = (time.time()-t0)

        if not test and frame_count % 10 == 0:
            print(f'FPS {1/delta:.2f}')
        frame_count += 1

        if test:
            if frame_count == 200:  # pypy has stabilized
                prev = time.time()

            if frame_count == 400:
                print(f'TIME {time.time()-prev:.2f}')
                break

    pygame.close(screen)


if __name__ == '__main__':
    # doom.py [wad] [test | dump <frames>]
    wad = DEFAULT_WAD
    argv = sys.argv[1:]
    if len(argv) > 0 and argv[0] != 'test' and argv[0] != 'dump':
        wad = argv[0]
        argv = argv[1:]

    try:
        open(wad, 'rb').close()
    except FileNotFoundError:
        print(f"cannot open WAD '{wad}'")
        print('pass the path as the first argument; see README.md for where '
              'to get DOOM1.WAD')
        sys.exit(1)

    if len(argv) > 1 and argv[0] == 'dump':
        dump(wad, Int32(int(argv[1])), 'frame.raw')
    elif len(argv) > 0 and argv[0] == 'test':
        main(wad, True)
    else:
        main(wad, False)
