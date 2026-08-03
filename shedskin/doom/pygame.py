# tpy: link("SDL2")
'''
A minimal SDL2-backed stand-in for the handful of pygame calls the DOOM
renderer makes.

The renderer produces an 8-bit paletted framebuffer and needs four things from a
graphics library: a window, a way to push that framebuffer to it, keyboard
state, and a frame delay. That is all this provides -- it is not a pygame
emulation. The API is flat rather than pygame's nested one
(pygame.display.flip, pygame.time.Clock, ...), because reproducing pygame's
object model would be far more machinery than these few calls justify.

SDL2's symbols are declared directly with @native. SDL.h is deliberately not
included: only the functions below are used, so declaring them keeps the build
free of any dependency on SDL's headers being installed.
'''
from tpy import Char, Int32, Own, UInt8, UInt32, Ptr, readonly
from tpy.extern import native
from tpy.unsafe import unsafe_ptr, unsafe_load

# -- raw SDL2 declarations -------------------------------------------------
# Window/renderer/texture handles are opaque; Ptr[UInt8] stands in for the
# pointer without needing SDL's struct definitions.

@native("SDL_Init", binding="C")
def _sdl_init(flags: UInt32) -> Int32: ...

@native("SDL_Quit", binding="C")
def _sdl_quit() -> None: ...

@native("SDL_CreateWindow", binding="C")
def _sdl_create_window(title: Ptr[readonly[Char]], x: Int32, y: Int32,
                       w: Int32, h: Int32, flags: UInt32) -> Ptr[UInt8]: ...

@native("SDL_CreateRenderer", binding="C")
def _sdl_create_renderer(window: Ptr[UInt8], index: Int32,
                         flags: UInt32) -> Ptr[UInt8]: ...

@native("SDL_CreateTexture", binding="C")
def _sdl_create_texture(renderer: Ptr[UInt8], fmt: UInt32, access: Int32,
                        w: Int32, h: Int32) -> Ptr[UInt8]: ...

@native("SDL_UpdateTexture", binding="C")
def _sdl_update_texture(texture: Ptr[UInt8], rect: Ptr[UInt8],
                        pixels: Ptr[UInt32], pitch: Int32) -> Int32: ...

@native("SDL_RenderClear", binding="C")
def _sdl_render_clear(renderer: Ptr[UInt8]) -> Int32: ...

@native("SDL_RenderCopy", binding="C")
def _sdl_render_copy(renderer: Ptr[UInt8], texture: Ptr[UInt8],
                     srcrect: Ptr[UInt8], dstrect: Ptr[UInt8]) -> Int32: ...

@native("SDL_RenderPresent", binding="C")
def _sdl_render_present(renderer: Ptr[UInt8]) -> None: ...

@native("SDL_DestroyTexture", binding="C")
def _sdl_destroy_texture(texture: Ptr[UInt8]) -> None: ...

@native("SDL_DestroyRenderer", binding="C")
def _sdl_destroy_renderer(renderer: Ptr[UInt8]) -> None: ...

@native("SDL_DestroyWindow", binding="C")
def _sdl_destroy_window(window: Ptr[UInt8]) -> None: ...

@native("SDL_PollEvent", binding="C")
def _sdl_poll_event(event: Ptr[UInt8]) -> Int32: ...

@native("SDL_PumpEvents", binding="C")
def _sdl_pump_events() -> None: ...

@native("SDL_GetKeyboardState", binding="C")
def _sdl_get_keyboard_state(numkeys: Ptr[Int32]) -> Ptr[readonly[UInt8]]: ...

@native("SDL_GetTicks", binding="C")
def _sdl_get_ticks() -> UInt32: ...

@native("SDL_Delay", binding="C")
def _sdl_delay(ms: UInt32) -> None: ...

# -- SDL constants ---------------------------------------------------------
_INIT_VIDEO: Int32 = 0x20
_WINDOWPOS_CENTERED: Int32 = 0x2FFF0000
_WINDOW_SHOWN: Int32 = 0x4
_RENDERER_ACCELERATED: Int32 = 0x2
_PIXELFORMAT_ARGB8888: Int32 = 0x16362004
_TEXTUREACCESS_STREAMING: Int32 = 1
_QUIT: Int32 = 0x100
_EVENT_SIZE: Int32 = 56  # sizeof(SDL_Event); only the leading Uint32 is read

# Scancodes -- what SDL_GetKeyboardState is indexed by.
K_UP: Int32 = 82
K_DOWN: Int32 = 81
K_LEFT: Int32 = 80
K_RIGHT: Int32 = 79
K_LCTRL: Int32 = 224
K_q: Int32 = 20


class Screen:
    '''Holds the SDL handles and the buffers a frame is pushed through.

    Deliberately a plain data holder: the functions below do the SDL work.
    TurboPython emits method bodies inline in the generated header, above the
    @native extern declarations, so a method calling SDL would not compile --
    module-level functions land in the .cpp, after the declarations.
    '''
    window: Ptr[UInt8]
    renderer: Ptr[UInt8]
    texture: Ptr[UInt8]
    width: Int32
    height: Int32
    pixels: list[UInt32]
    lut: list[UInt32]
    event: list[UInt8]
    quit_requested: bool
    last_ticks: UInt32

    def __init__(self, width: Int32, height: Int32) -> None:
        self.window = None
        self.renderer = None
        self.texture = None
        self.width = width
        self.height = height
        self.pixels = [UInt32(0)] * (width * height)
        self.lut = [UInt32(0)] * 256
        self.event = [UInt8(0)] * _EVENT_SIZE
        self.quit_requested = False
        self.last_ticks = UInt32(0)


def open_screen(width: Int32, height: Int32, title: str) -> Own[Screen]:
    screen = Screen(width, height)
    _sdl_init(UInt32(_INIT_VIDEO))
    # str lowers to std::string_view; SDL wants a const char*.
    screen.window = _sdl_create_window(unsafe_ptr(title), _WINDOWPOS_CENTERED,
                                       _WINDOWPOS_CENTERED, width, height,
                                       UInt32(_WINDOW_SHOWN))
    screen.renderer = _sdl_create_renderer(screen.window, -1,
                                           UInt32(_RENDERER_ACCELERATED))
    screen.texture = _sdl_create_texture(screen.renderer,
                                         UInt32(_PIXELFORMAT_ARGB8888),
                                         _TEXTUREACCESS_STREAMING,
                                         width, height)
    screen.last_ticks = _sdl_get_ticks()
    return screen


def set_palette(screen: Screen, palette: list[tuple[Int32, Int32, Int32]]) -> None:
    '''Precompute index -> ARGB so a frame costs one lookup per pixel.'''
    for i in range(len(palette)):
        rgb = palette[i]
        screen.lut[i] = UInt32(0xff000000 | (rgb[0] << 16) |
                               (rgb[1] << 8) | rgb[2])


def present(screen: Screen, buf: bytearray) -> None:
    '''Expand the paletted framebuffer and push it to the window.'''
    for i in range(screen.width * screen.height):
        screen.pixels[i] = screen.lut[Int32(buf[i])]
    _sdl_update_texture(screen.texture, None, unsafe_ptr(screen.pixels),
                        screen.width * 4)
    _sdl_render_clear(screen.renderer)
    _sdl_render_copy(screen.renderer, screen.texture, None, None)
    _sdl_render_present(screen.renderer)


def pump(screen: Screen) -> None:
    '''Drain the event queue, noting a window-close request.'''
    while _sdl_poll_event(unsafe_ptr(screen.event)) != 0:
        kind = (Int32(screen.event[0]) | (Int32(screen.event[1]) << 8) |
                (Int32(screen.event[2]) << 16) | (Int32(screen.event[3]) << 24))
        if kind == _QUIT:
            screen.quit_requested = True


def key_pressed(scancode: Int32) -> bool:
    state = _sdl_get_keyboard_state(None)
    return Int32(unsafe_load(state, UInt32(scancode))) != 0


def tick(screen: Screen, fps: Int32) -> None:
    '''Sleep out the rest of the frame, like pygame's Clock.tick.'''
    frame_ms = 1000 // fps
    elapsed = Int32(_sdl_get_ticks() - screen.last_ticks)
    if elapsed < frame_ms:
        _sdl_delay(UInt32(frame_ms - elapsed))
    screen.last_ticks = _sdl_get_ticks()


def close(screen: Screen) -> None:
    _sdl_destroy_texture(screen.texture)
    _sdl_destroy_renderer(screen.renderer)
    _sdl_destroy_window(screen.window)
    _sdl_quit()
