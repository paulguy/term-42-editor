#!/usr/bin/env python

from array import array
import itertools
import sys
from enum import Enum, auto

import blessed

ZOOMED_X = 4
ZOOMED_PAD = 4
PREVIEW_SPACING = 4
PREVIEW_X = ZOOMED_X + (ZOOMED_PAD * 2 + 1) * 2 + PREVIEW_SPACING

CHARS4 = array('w', ' 𜺨𜴀▘𜴉𜴊🯦𜴍𜺣𜴶𜴹𜴺▖𜵅𜵈▌𜺫🮂𜴁𜴂𜴋𜴌𜴎𜴏𜴷𜴸𜴻𜴼𜵆𜵇𜵉𜵊𜴃𜴄𜴆𜴇𜴐𜴑𜴔𜴕𜴽𜴾𜵁𜵂𜵋𜵌𜵎𜵏▝𜴅𜴈▀𜴒𜴓𜴖𜴗𜴿𜵀𜵃𜵄▞𜵍𜵐▛'
                    '𜴘𜴙𜴜𜴝𜴧𜴨𜴫𜴬𜵑𜵒𜵕𜵖𜵡𜵢𜵥𜵦𜴚𜴛𜴞𜴟𜴩𜴪𜴭𜴮𜵓𜵔𜵗𜵘𜵣𜵤𜵧𜵨🯧𜴠𜴣𜴤𜴯𜴰𜴳𜴴𜵙𜵚𜵝𜵞𜵩𜵪𜵭𜵮𜴡𜴢𜴥𜴦𜴱𜴲𜴵🮅𜵛𜵜𜵟𜵠𜵫𜵬𜵯𜵰'
                    '𜺠𜵱𜵴𜵵𜶀𜶁𜶄𜶅▂𜶬𜶯𜶰𜶻𜶼𜶿𜷀𜵲𜵳𜵶𜵷𜶂𜶃𜶆𜶇𜶭𜶮𜶱𜶲𜶽𜶾𜷁𜷂𜵸𜵹𜵼𜵽𜶈𜶉𜶌𜶍𜶳𜶴𜶷𜶸𜷃𜷄𜷇𜷈𜵺𜵻𜵾𜵿𜶊𜶋𜶎𜶏𜶵𜶶𜶹𜶺𜷅𜷆𜷉𜷊'
                    '▗𜶐𜶓▚𜶜𜶝𜶠𜶡𜷋𜷌𜷏𜷐▄𜷛𜷞▙𜶑𜶒𜶔𜶕𜶞𜶟𜶢𜶣𜷍𜷎𜷑𜷒𜷜𜷝𜷟𜷠𜶖𜶗𜶙𜶚𜶤𜶥𜶨𜶩𜷓𜷔𜷗𜷘𜷡𜷢▆𜷤▐𜶘𜶛▜𜶦𜶧𜶪𜶫𜷕𜷖𜷙𜷚▟𜷣𜷥█')

class KeyActions(Enum):
    NONE = auto()
    QUIT = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    TOGGLE = auto()
    RESIZE = auto()
    GRID = auto()
    ZOOMED_COLOR = auto()
    CLEAR = auto()
    HOME = auto()
    EDGE = auto()
    COLOR_MODE = auto()
    SELECT_FG_COLOR = auto()
    SELECT_BG_COLOR = auto()
    PUT_COLOR = auto()
    PICK_COLOR = auto()

class ColorMode(Enum):
    C16 = auto()
    C256 = auto()
    DIRECT = auto()

BLACK = 0
WHITE = 15
COLOR_PREVIEW = "𜶉𜶉"
CURSOR = "🯧🯦"
BLOCK = "██"

TILES = ("  ", "𜵊🮂", "▌ ", "𜷀▂", "🮂𜶘", " ▐", "▂𜷕", "🯧🯦", "𜵰𜴏", "𜵮🯦", "𜷤𜶿", "𜴢𜶫", "🯧𜶪", "𜷓𜷥")
def display_zoomed_matrix(t : blessed.Terminal,
                          x : int, y : int, pad : int,
                          dx : int, dy : int,
                          dw : int, dh : int,
                          colors : dict[bool],
                          grid : bool, use_color : bool,
                          color_mode : ColorMode,
                          data : array,
                          colordata_fg_r : array,
                          colordata_fg_g : array,
                          colordata_fg_b : array,
                          colordata_bg_r : array,
                          colordata_bg_g : array,
                          colordata_bg_b : array):
    dx -= pad
    dy -= pad
    cx = dx // 2
    cy = dy // 4
    cw = dw // 2

    lastcolor_r : int = None
    lastcolor_g : int = None
    lastcolor_b : int = None
    lastcolor : str = ""

    for iy in range(pad * 2 + 1):
        print(t.move_xy(x, y + iy), end='')

        for ix in range(pad * 2 + 1):
            tile = 0

            if dy + iy < 0:
                # if above the top, print normals
                if ix == 0 and iy == 0:
                    # only print the attribute once
                    print(t.normal, end='')
                    lastcolor = ""
            elif dx + ix < 0:
                # if to the left print normals
                if ix == 0:
                    # only print once
                    print(t.normal, end='')
                    lastcolor = ""
            elif dx + ix == dw:
                # if to the right print normals
                print(t.normal, end='')
            elif dx + ix > dw:
                # only print once
                pass
            elif dy + iy == dh:
                # if past the bottom, print normals
                if ix == 0:
                    # only print once
                    print(t.normal, end='')
                    lastcolor = ""
            elif dy + iy > dh:
                # only print once
                pass
            else:
                # set color
                if use_color:
                    ciy : int = (dy + iy) // 4
                    cix : int = (dx + ix) // 2
                    if color_mode == ColorMode.DIRECT:
                        if data[dw * (dy + iy) + (dx + ix)]:
                            color_r = colordata_fg_r[cw * ciy + cix]
                            color_g = colordata_fg_g[cw * ciy + cix]
                            color_b = colordata_fg_b[cw * ciy + cix]
                            if len(lastcolor) == 0 or \
                               color_r != lastcolor_r or \
                               color_g != lastcolor_g or \
                               color_b != lastcolor_b:
                                print(t.on_color_rgb(color_r, color_g, color_b), end='')
                                print(t.color_rgb(max(0, 255 - color_r - 64),
                                                  max(0, 255 - color_g - 64),
                                                  max(0, 255 - color_b - 64)), end='')
                                lastcolor_r = color_r
                                lastcolor_g = color_g
                                lastcolor_b = color_b
                                lastcolor = "#"  # Tag with some non-empty string
                        else:
                            color_r = colordata_bg_r[cw * ciy + cix]
                            color_g = colordata_bg_g[cw * ciy + cix]
                            color_b = colordata_bg_b[cw * ciy + cix]
                            if len(lastcolor) == 0 or \
                               color_r != lastcolor_r or \
                               color_g != lastcolor_g or \
                               color_b != lastcolor_b:
                                print(t.on_color_rgb(color_r, color_g, color_b), end='')
                                print(t.color_rgb(max(0, 255 - color_r - 64),
                                                  max(0, 255 - color_g - 64),
                                                  max(0, 255 - color_b - 64)), end='')
                                lastcolor_r = color_r
                                lastcolor_g = color_g
                                lastcolor_b = color_b
                                lastcolor = "#"  # Tag with some non-empty string
                    else:
                        if data[dw * (dy + iy) + (dx + ix)]:
                            color_r = colordata_fg_r[cw * ciy + cix]
                            if len(lastcolor) == 0 or \
                               color_r != lastcolor_r:
                                print(t.on_color(color_r), end='')
                                if color_r == BLACK:
                                    print(t.color(WHITE), end='')
                                else:
                                    print(t.color(BLACK), end='')
                                lastcolor_r = color_r
                                lastcolor = "#"  # Tag with some non-empty string
                        else:
                            color_r = colordata_bg_r[cw * ciy + cix]
                            if len(lastcolor) == 0 or \
                               color_r != lastcolor_r:
                                print(t.on_color(color_r), end='')
                                if color_r == BLACK:
                                    print(t.color(WHITE), end='')
                                else:
                                    print(t.color(BLACK), end='')
                                lastcolor_r = color_r
                                lastcolor = "#"  # Tag with some non-empty string
                else:
                    color = colors[data[dw * (dy + iy) + (dx + ix)]]
                    if color != lastcolor:
                        print(color, end='')
                    lastcolor = color

                if grid:
                    if (dx + ix) % 2 == 0:
                        if (dy + iy) % 4 == 0:
                            tile = 1
                        elif (dy + iy) % 4 == 3:
                            tile = 3
                        else:
                            tile = 2
                    else:
                        if (dy + iy) % 4 == 0:
                            tile = 4
                        elif (dy + iy) % 4 == 3:
                            tile = 6
                        else:
                            tile = 5

            if ix == pad and iy == pad:
                tile += 7
            print(TILES[tile], end='')

def display_matrix(t : blessed.Terminal,
                   color_mode : ColorMode,
                   x : int, y : int,
                   w : int, h : int,
                   cx : int, cy : int,
                   dw : int, data : array,
                   colordata_fg_r : array,
                   colordata_fg_g : array,
                   colordata_fg_b : array,
                   colordata_bg_r : array,
                   colordata_bg_g : array,
                   colordata_bg_b : array):
    # unlike the above, this one should never be given arguments to read out of bounds

    # convert between cell coordinates to data coordinates
    dx = cx * 2
    dy = cx * 4
    # get width in cells
    cw = dw // 2

    if color_mode == ColorMode.DIRECT:
        lastcolor_fg_r = colordata_fg_r[cy * cw + cx]
        lastcolor_fg_g = colordata_fg_g[cy * cw + cx]
        lastcolor_fg_b = colordata_fg_b[cy * cw + cx]
        lastcolor_bg_r = colordata_bg_r[cy * cw + cx]
        lastcolor_bg_g = colordata_bg_g[cy * cw + cx]
        lastcolor_bg_b = colordata_bg_b[cy * cw + cx]
        print(t.on_color_rgb(lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b), end='')
        print(t.color_rgb(lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b), end='')
    else:
        lastcolor_fg_r = colordata_fg_r[cy * cw + cx]
        lastcolor_bg_r = colordata_bg_r[cy * cw + cx]
        print(t.on_color(lastcolor_bg_r), end='')
        print(t.color(lastcolor_fg_r), end='')

    for iy in range(h):
        print(t.move_xy(x, y + iy), end='')
        ry = iy * 4
        for ix in range(w):
            rx = ix * 2
            if color_mode == ColorMode.DIRECT:
                color_fg_r = colordata_fg_r[((cy + iy) * cw) + (cx + ix)]
                color_fg_g = colordata_fg_g[((cy + iy) * cw) + (cx + ix)]
                color_fg_b = colordata_fg_b[((cy + iy) * cw) + (cx + ix)]
                color_bg_r = colordata_bg_r[((cy + iy) * cw) + (cx + ix)]
                color_bg_g = colordata_bg_g[((cy + iy) * cw) + (cx + ix)]
                color_bg_b = colordata_bg_b[((cy + iy) * cw) + (cx + ix)]
                if color_fg_r != lastcolor_fg_r or \
                   color_fg_g != lastcolor_fg_g or \
                   color_fg_b != lastcolor_fg_b:
                    print(t.color_rgb(color_fg_r, color_fg_g, color_fg_b), end='')
                    lastcolor_fg_r = color_fg_r
                    lastcolor_fg_g = color_fg_g
                    lastcolor_fg_b = color_fg_b
                if color_bg_r != lastcolor_bg_r or \
                   color_bg_g != lastcolor_bg_g or \
                   color_bg_b != lastcolor_bg_b:
                    print(t.on_color_rgb(color_bg_r, color_bg_g, color_bg_b), end='')
                    lastcolor_bg_r = color_bg_r
                    lastcolor_bg_g = color_bg_g
                    lastcolor_bg_b = color_bg_b
            else:
                # paletted modes use the R channel for color value
                color_fg_r = colordata_fg_r[((cy + iy) * cw) + (cx + ix)]
                color_bg_r = colordata_bg_r[((cy + iy) * cw) + (cx + ix)]
                if color_fg_r != lastcolor_fg_r:
                    print(t.color(color_fg_r), end='')
                    lastcolor_fg_r = color_fg_r
                if color_bg_r != lastcolor_bg_r:
                    print(t.on_color(color_bg_r), end='')
                    lastcolor_bg_r = color_bg_r

            # offset LSB to RSB goes top left -> bottom left, top right -> bottom right
            cell = 0
            if bool(data[((dy + ry) * dw) + (dx + rx)]):
                cell += 1
            if bool(data[((dy + ry + 1) * dw) + (dx + rx)]):
                cell += 2
            if bool(data[((dy + ry + 2) * dw) + (dx + rx)]):
                cell += 4
            if bool(data[((dy + ry + 3) * dw) + (dx + rx)]):
                cell += 8
            if bool(data[((dy + ry) * dw) + (dx + rx + 1)]):
                cell += 16
            if bool(data[((dy + ry + 1) * dw) + (dx + rx + 1)]):
                cell += 32
            if bool(data[((dy + ry + 2) * dw) + (dx + rx + 1)]):
                cell += 64
            if bool(data[((dy + ry + 3) * dw) + (dx + rx + 1)]):
                cell += 128
            print(CHARS4[cell], end='')

def update_matrix(t : blessed.Terminal,
                  color_mode : ColorMode,
                  x : int, y : int,
                  dx : int, dy : int,
                  dw : int, data : array,
                  colordata_fg_r : array,
                  colordata_fg_g : array,
                  colordata_fg_b : array,
                  colordata_bg_r : array,
                  colordata_bg_g : array,
                  colordata_bg_b : array):
    # largely the same function as above, but for 1 character

    dx = dx // 2 * 2
    dy = dy // 4 * 4
    cx = dx // 2
    cy = dy // 4
    cw = dw // 2

    if color_mode == ColorMode.DIRECT:
        print(t.color_rgb(colordata_fg_r[cy * cw + cx], colordata_fg_g[cy * cw + cx], colordata_fg_b[cy * cw + cx]), end='')
        print(t.on_color_rgb(colordata_bg_r[cy * cw + cx], colordata_bg_g[cy * cw + cx], colordata_bg_b[cy * cw + cx]), end='')
    else:
        # paletted modes use the R channel for color value
        print(t.color(colordata_fg_r[cy * cw + cx]), end='')
        print(t.on_color(colordata_bg_r[cy * cw + cx]), end='')

    # offset LSB to RSB goes top left -> bottom left, top right -> bottom right
    cell = 0
    if bool(data[(dy * dw) + dx]):
        cell += 1
    if bool(data[((dy + 1) * dw) + dx]):
        cell += 2
    if bool(data[((dy + 2) * dw) + dx]):
        cell += 4
    if bool(data[((dy + 3) * dw) + dx]):
        cell += 8
    if bool(data[(dy * dw) + (dx + 1)]):
        cell += 16
    if bool(data[((dy + 1) * dw) + (dx + 1)]):
        cell += 32
    if bool(data[((dy + 2) * dw) + (dx + 1)]):
        cell += 64
    if bool(data[((dy + 3) * dw) + (dx + 1)]):
        cell += 128
    print(t.move_xy(x + cx, y + cy), end='')
    print(CHARS4[cell], end='')

def inkey_numeric(t : blessed.Terminal):
    key = t.inkey()

    try:
        return False, t._keymap[key]
    except KeyError:
        pass

    return True, ord(key)

def print_status(t : blessed.Terminal, text : str, row : int = 0):
    print(t.normal, end='')
    print(t.move_xy(0, row), end='')
    print(text, end='')
 
def prompt(t : blessed.Terminal, text : str):
    inp = array('w')

    print_status(t, text)
    print()
    while True:
        is_text, key = inkey_numeric(t)
        if is_text:
            inp.append(chr(key))
            print(chr(key), end='')
        else:
            if key == t.KEY_ENTER:
                break
            elif key == t.KEY_ESCAPE:
                return None
            elif key == t.KEY_BACKSPACE:
                # TODO: make this display correctly
                pass
                #inp = inp[:-1]
                #print(t.backspace, end='')
                #print(t.cursor_left, end='')
                #print(t.delete_character, end='')
        sys.stdout.flush()
    # TODO: Make this work
    print(t.move_xy(0, 0), end='')
    print(t.delete_line, end='')
    print(t.move_xy(0, 1), end='')
    print(t.delete_line, end='')
    sys.stdout.flush()

    return inp.tounicode()

def prompt_yn(t : blessed.Terminal, text : str) -> bool:
    ans = prompt(t, f"{text} (y/n)")
    if ans is None or ans[0].lower() != 'y':
        return False

    return True

def clear_screen(t : blessed.Terminal):
    print(t.normal, end='')
    print(t.clear, end='')

def select_color_rgb(t : blessed.Terminal,
                     r : int, g : int, b : int):
    orig_r = r
    orig_g = g
    orig_b = b
    clear_screen(t)

    while True:
        print(t.normal, end='')
        print(t.move_xy(0, 0), end='')
        print(r, end='')
        print(t.move_xy(4, 0), end='')
        print(g, end='')
        print(t.move_xy(8, 0), end='')
        print(b, end='')
        print(t.move_xy(6, 1), end='')
        print(t.color_rgb(r, g, b), end='')
        print(BLOCK, end='')
        sys.stdout.flush()

        _, key = inkey_numeric(t)
        if key == t.KEY_ENTER:
            break
        elif key == t.KEY_ESCAPE:
            r = orig_r
            g = orig_g
            b = orig_b
            break
        elif key == ord('a'):
            if r > 0:
                r -= 1
        elif key == ord('s'):
            if g > 0:
                g -= 1
        elif key == ord('d'):
            if b > 0:
                b -= 1
        elif key == ord('q'):
            if r < 255:
                r += 1
        elif key == ord('w'):
            if g < 255:
                g += 1
        elif key == ord('e'):
            if b < 255:
                b += 1
        elif key == ord('A'):
            r -= 10
            if r < 0:
                r = 0
        elif key == ord('S'):
            g -= 10
            if g < 0:
                g = 0
        elif key == ord('D'):
            b -= 10
            if b < 0:
                b = 0
        elif key == ord('Q'):
            r += 10
            if r > 255:
                r = 255
        elif key == ord('W'):
            g += 10
            if g > 255:
                g = 255
        elif key == ord('E'):
            b += 10
            if b > 255:
                b = 255

    clear_screen(t)
    return r, g, b

def select_color(t : blessed.Terminal, c : int, color_mode : ColorMode):
    x = 0
    y = 0
    width = 4
    height = 4
    if color_mode == ColorMode.C256:
        width = 16
        height = 16

    clear_screen(t)

    while True:
        print(t.color(BLACK), end='')
        for cy in range(height):
            print(t.move_xy(0, cy), end='')
            for cx in range(width):
                print(t.on_color(cy * width + cx), end='')
                print("  ", end='')

        print(t.move_xy(x * 2, y), end='')
        if x == 0 and y == 0:
            print(t.color(WHITE), end='')
        else:
            print(t.color(BLACK), end='')
        print(t.on_color(y * width + x), end='')
        print(CURSOR, end='')
        sys.stdout.flush()
        _, key = inkey_numeric(t)
        if key == t.KEY_ENTER:
            c = y * width + x
            break
        elif key == t.KEY_ESCAPE:
            break
        elif key == t.KEY_LEFT:
            if x > 0:
                x -= 1
        elif key == t.KEY_RIGHT:
            if x < width - 1:
                x += 1
        elif key == t.KEY_UP:
            if y > 0:
                y -= 1
        elif key == t.KEY_DOWN:
            if y < height - 1:
                y += 1

    clear_screen(t)
    return c

def get_default_colors(color_mode : ColorMode):
    # set to white on black
    if color_mode == ColorMode.DIRECT:
        return 255, 255, 255, 0, 0, 0

    return WHITE, 0, 0, 0, 0, 0

def get_color_str(t : blessed.Terminal,
                  color_mode : ColorMode,
                  fg_r : int, fg_g : int, fg_b : int,
                  bg_r : int, bg_g : int, bg_b : int):
    if color_mode == ColorMode.DIRECT:
        return f"{t.on_color_rgb(bg_r, bg_g, bg_b)}{t.color_rgb(fg_r, fg_g, fg_b)}"

    return f"{t.on_color(bg_r)}{t.color(fg_r)}"

def new_color_data(color_mode : ColorMode, width : int, height : int):
    temp_fg_r, temp_fg_g, temp_fg_b, temp_bg_r, temp_bg_g, temp_bg_b = get_default_colors(color_mode)
    colordata_fg_r = array('i', itertools.repeat(temp_fg_r, (width // 2) * (height // 4)))
    colordata_fg_g = array('i', itertools.repeat(temp_fg_g, (width // 2) * (height // 4)))
    colordata_fg_b = array('i', itertools.repeat(temp_fg_b, (width // 2) * (height // 4)))
    colordata_bg_r = array('i', itertools.repeat(temp_bg_r, (width // 2) * (height // 4)))
    colordata_bg_g = array('i', itertools.repeat(temp_bg_g, (width // 2) * (height // 4)))
    colordata_bg_b = array('i', itertools.repeat(temp_bg_b, (width // 2) * (height // 4)))

    return colordata_fg_r, colordata_fg_g, colordata_fg_b, colordata_bg_r, colordata_bg_g, colordata_bg_b


def main():
    width : int = 20
    height : int = 20
    x : int = 0
    y : int = 0
    grid : bool = True
    zoomed_color : bool = False
    color_mode : ColorMode = ColorMode.DIRECT
    max_color_mode : ColorMode = ColorMode.DIRECT
    fg_r : int = 0
    fg_g : int = 0
    fg_b : int = 0
    bg_r : int = 0
    bg_g : int = 0
    bg_b : int = 0
    color_str : str = None
    refresh_matrix = True

    t = blessed.Terminal()

    KEY_ACTIONS = {
        ord('Q'): KeyActions.QUIT,
        t.KEY_LEFT: KeyActions.MOVE_LEFT,
        t.KEY_RIGHT: KeyActions.MOVE_RIGHT,
        t.KEY_UP: KeyActions.MOVE_UP,
        t.KEY_DOWN: KeyActions.MOVE_DOWN,
        ord('a'): KeyActions.MOVE_LEFT,
        ord('d'): KeyActions.MOVE_RIGHT,
        ord('w'): KeyActions.MOVE_UP,
        ord('s'): KeyActions.MOVE_DOWN,
        ord(' '): KeyActions.TOGGLE,
        ord('r'): KeyActions.RESIZE,
        ord('g'): KeyActions.GRID,
        ord('z'): KeyActions.ZOOMED_COLOR,
        ord('X'): KeyActions.CLEAR,
        t.KEY_HOME: KeyActions.HOME,
        ord('h'): KeyActions.HOME,
        ord('e'): KeyActions.EDGE,
        ord('M'): KeyActions.COLOR_MODE,
        ord('c'): KeyActions.SELECT_FG_COLOR,
        ord('C'): KeyActions.SELECT_BG_COLOR,
        ord('p'): KeyActions.PUT_COLOR,
        ord('P'): KeyActions.PICK_COLOR
    }

    COLORS = {
        False: f"{t.color(WHITE)}{t.on_color(BLACK)}",
        True:  f"{t.color(BLACK)}{t.on_color(WHITE)}"
    }

    if t.number_of_colors == 256:
        max_color_mode = ColorMode.C256
    elif t.number_of_colors < 256:
        max_color_mode = ColorMode.C16
    color_mode = max_color_mode
    fg_r, fg_g, fg_b, bg_r, bg_g, bg_b = get_default_colors(color_mode)

    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)

    data = array('i', itertools.repeat(0, width * height))
    # fill with some pattern to show it's working
    for i in range(0, width * height, 3):
        data[i] = 1
    colordata_fg_r, colordata_fg_g, colordata_fg_b, \
        colordata_bg_r, colordata_bg_g, colordata_bg_b = \
        new_color_data(color_mode, width, height)

    with t.cbreak(), t.fullscreen(), t.hidden_cursor():
        while True:
            if refresh_matrix:
                display_matrix(t, color_mode, PREVIEW_X, 2, width // 2, height // 4, 0, 0, width, data,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b)
                refresh_matrix = False

            print(t.move_xy(0, 2), end='')
            print(color_str, end='')
            print("𜶉𜶉", end='')
            display_zoomed_matrix(t, ZOOMED_X, 2, ZOOMED_PAD,
                                  x, y, width, height,
                                  COLORS, grid, zoomed_color, color_mode, data,
                                  colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                  colordata_bg_r, colordata_bg_g, colordata_bg_b)
            print_status(t, f"{color_mode.name} {x}, {y}", 1)
            sys.stdout.flush()
            _, key = inkey_numeric(t)

            # convert to an action
            try:
                key = KEY_ACTIONS[key]
            except KeyError:
                key = KeyActions.NONE

            print(t.move_xy(0, 0), end='')
            match key:
                case KeyActions.QUIT:
                    ans = prompt_yn(t, "Quit?")
                    if ans:
                        break
                case KeyActions.MOVE_LEFT:
                    x -= 1
                case KeyActions.MOVE_RIGHT:
                    x += 1
                case KeyActions.MOVE_UP:
                    y -= 1
                case KeyActions.MOVE_DOWN:
                    y += 1
                case KeyActions.TOGGLE:
                    if x >= 0 and x < width and y >= 0 and y < height:
                        data[width * y + x] = not data[width * y + x]
                        update_matrix(t, color_mode, PREVIEW_X, 2, x, y, width, data,
                                      colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                      colordata_bg_r, colordata_bg_g, colordata_bg_b)
                case KeyActions.RESIZE:
                    newwidth = prompt(t, "New Width?")
                    if newwidth is None:
                        continue
                    try:
                        newwidth = int(newwidth)
                    except ValueError:
                        print_status(t, "Width must be an integer.")
                        continue
                    if newwidth < 2 or newwidth % 2 != 0:
                        print_status(t, "Width must be non-zero and divisible by 2.")
                        continue
                    newheight = prompt(t, "New Height?")
                    if newheight is None:
                        continue
                    try:
                        newheight = int(newheight)
                    except ValueError:
                        print_status(t, "Height must be an integer.")
                        continue
                    if newheight < 4 or newheight % 4 != 0:
                        print_status(t, "Height must be non-zero and divisible by 4.")
                        continue
                    newdata = array('i', itertools.repeat(0, newwidth * newheight))
                    newcolordata_fg_r, newcolordata_fg_g, newcolordata_fg_b, \
                        newcolordata_bg_r, newcolordata_bg_g, newcolordata_bg_b = \
                        new_color_data(color_mode, width, height)
                    smallestwidth = min(width, newwidth)
                    smallestheight = min(height, newheight)
                    for y in range(smallestheight):
                        newdata[newwidth * y:newwidth * y + smallestwidth] = data[width * y:width * y + smallestwidth]
                    for y in range(smallestheight // 4):
                        newcolordata_fg_r[(newwidth // 2) * y:(newwidth // 2) * y + (smallestwidth // 2)] = \
                            colordata_fg_r[(width // 2) * y:(width // 2) * y + (smallestwidth // 2)]
                        newcolordata_fg_g[(newwidth // 2) * y:(newwidth // 2) * y + (smallestwidth // 2)] = \
                            colordata_fg_g[(width // 2) * y:(width // 2) * y + (smallestwidth // 2)]
                        newcolordata_fg_b[(newwidth // 2) * y:(newwidth // 2) * y + (smallestwidth // 2)] = \
                            colordata_fg_b[(width // 2) * y:(width // 2) * y + (smallestwidth // 2)]
                        newcolordata_bg_r[(newwidth // 2) * y:(newwidth // 2) * y + (smallestwidth // 2)] = \
                            colordata_bg_r[(width // 2) * y:(width // 2) * y + (smallestwidth // 2)]
                        newcolordata_bg_g[(newwidth // 2) * y:(newwidth // 2) * y + (smallestwidth // 2)] = \
                            colordata_bg_g[(width // 2) * y:(width // 2) * y + (smallestwidth // 2)]
                        newcolordata_bg_b[(newwidth // 2) * y:(newwidth // 2) * y + (smallestwidth // 2)] = \
                            colordata_bg_b[(width // 2) * y:(width // 2) * y + (smallestwidth // 2)]
                    data = newdata
                    colordata_fg_r = newcolordata_fg_r
                    colordata_fg_g = newcolordata_fg_g
                    colordata_fg_b = newcolordata_fg_b
                    colordata_bg_r = newcolordata_bg_r
                    colordata_bg_g = newcolordata_bg_g
                    colordata_bg_b = newcolordata_bg_b
                    width = newwidth
                    height = newheight
                    clear_screen(t)
                    refresh_matrix = True
                    x = min(x, width)
                    y = min(y, height)
                    print_status(t, f"Image resized to {x}, {y}.")
                case KeyActions.GRID:
                    grid = not grid
                    if grid:
                        print_status(t, f"Grid toggled on.")
                    else:
                        print_status(t, f"Grid toggled off.")
                case KeyActions.ZOOMED_COLOR:
                    zoomed_color = not zoomed_color
                    if zoomed_color:
                        print_status(t, f"Zoomed view color toggled on.")
                    else:
                        print_status(t, f"Zoomed view color toggled off.")
                case KeyActions.CLEAR:
                    ans = prompt_yn(t, "This will clear the image, are you sure?")
                    if ans:
                        data = array('i', itertools.repeat(0, width * height))
                        colordata_fg_r, colordata_fg_g, colordata_fg_b, \
                            colordata_bg_r, colordata_bg_g, colordata_bg_b = \
                            new_color_data(color_mode, width, height)
                        clear_screen(t)
                        refresh_matrix = True
                        print_status(t, f"Image cleared.")
                    else:
                        print_status(t, f"Clear canceled.")
                case KeyActions.HOME:
                    x = 0
                    y = 0
                    print_status(t, f"Returned to home.")
                case KeyActions.EDGE:
                    if x < 0:
                        x = 0
                    elif x >= width:
                        x = width - 1
                    if y < 0:
                        y = 0
                    elif y >= height:
                        y = height - 1
                    print_status(t, f"Found nearest edge.")
                case KeyActions.COLOR_MODE:
                    ans = prompt_yn(t, "This will clear the image, are you sure?")
                    if ans:
                        ans = prompt(t, "Which color mode to switch to? (D=DIRECT, 1=16, 2=256)")
                        if ans[0].lower() == 'D':
                            if color_mode == ColorMode.DIRECT:
                                print_status(t, "Already in DIRECT color mode.")
                                continue
                            else:
                                color_mode = ColorMode.DIRECT
                        elif ans[0] == '1':
                            if color_mode == ColorMode.C16:
                                print_status(t, "Already in 16 color mode.")
                                continue
                            else:
                                color_mode = ColorMode.C16
                        elif ans[0] == '2':
                            if color_mode == ColorMode.C256:
                                print_status(t, "Already in 256 color mode.")
                                continue
                            else:
                                color_mode = ColorMode.C256
                        else:
                            print_status(t, "Unrecognized response.")
                            continue
                        data = array('i', itertools.repeat(0, width * height))
                        colordata_fg_r, colordata_fg_g, colordata_fg_b, \
                            colordata_bg_r, colordata_bg_g, colordata_bg_b = \
                            new_color_data(color_mode, width, height)
                        fg_r, fg_g, fg_b, bg_r, bg_g, bg_b = get_default_colors(color_mode)
                        clear_screen(t)
                        refresh_matrix = True
                        if color_mode == ColorMode.C16:
                            print_status(t, "Changed to 16 color mode.")
                        elif color_mode == ColorMode.C256:
                            print_status(t, "Changed to 256 color mode.")
                        else:
                            print_status(t, "Changed to DIRECT color mode.")
                case KeyActions.SELECT_FG_COLOR:
                    if color_mode == ColorMode.DIRECT:
                        fg_r, fg_g, fg_b = select_color_rgb(t, fg_r, fg_g, fg_b)
                        print_status(t, f"Foreground color RGB {fg_r}, {fg_g}, {fg_b} selected.")
                    else:
                        fg_r = select_color(t, fg_r, color_mode)
                        print_status(t, f"Foreground color index {fg_r} selected.")
                    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)
                    # screen was cleared so needs to be drawn
                    refresh_matrix = True
                case KeyActions.SELECT_BG_COLOR:
                    if color_mode == ColorMode.DIRECT:
                        bg_r, bg_g, bg_b = select_color_rgb(t, bg_r, bg_g, bg_b)
                        print_status(t, f"Background color RGB {fg_r}, {fg_g}, {fg_b} selected.")
                    else:
                        bg_r = select_color(t, bg_r, color_mode)
                        print_status(t, f"Background color index {fg_r} selected.")
                    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)
                    # screen was cleared so needs to be drawn
                    refresh_matrix = True
                case KeyActions.PUT_COLOR:
                    if color_mode == ColorMode.DIRECT:
                        colordata_fg_r[((y // 4) * (width // 2)) + (x // 2)] = fg_r
                        colordata_fg_g[((y // 4) * (width // 2)) + (x // 2)] = fg_g
                        colordata_fg_b[((y // 4) * (width // 2)) + (x // 2)] = fg_b
                        colordata_bg_r[((y // 4) * (width // 2)) + (x // 2)] = bg_r
                        colordata_bg_g[((y // 4) * (width // 2)) + (x // 2)] = bg_g
                        colordata_bg_b[((y // 4) * (width // 2)) + (x // 2)] = bg_b
                    else:
                        colordata_fg_r[((y // 4) * (width // 2)) + (x // 2)] = fg_r
                        colordata_bg_r[((y // 4) * (width // 2)) + (x // 2)] = bg_r
                    update_matrix(t, color_mode, PREVIEW_X, 2, x, y, width, data,
                                  colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                  colordata_bg_r, colordata_bg_g, colordata_bg_b)
                case KeyActions.PICK_COLOR:
                    if color_mode == ColorMode.DIRECT:
                        fg_r = colordata_fg_r[((y // 4) * (width // 2)) + (x // 2)]
                        fg_g = colordata_fg_g[((y // 4) * (width // 2)) + (x // 2)]
                        fg_b = colordata_fg_b[((y // 4) * (width // 2)) + (x // 2)]
                        bg_r = colordata_bg_r[((y // 4) * (width // 2)) + (x // 2)]
                        bg_g = colordata_bg_g[((y // 4) * (width // 2)) + (x // 2)]
                        bg_g = colordata_bg_b[((y // 4) * (width // 2)) + (x // 2)]
                    else:
                        fg_r = colordata_fg_r[((y // 4) * (width // 2)) + (x // 2)]
                        bg_r = colordata_bg_r[((y // 4) * (width // 2)) + (x // 2)]
                    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)
 

if __name__ == '__main__':
    main()
