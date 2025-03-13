#!/usr/bin/env python

from array import array
import itertools
import sys
from enum import Enum, auto
import pathlib
import re
import copy

import blessed

# TODO: Add line and fill.
# TODO: Add save without color.
# TODO: Visible selection area on the preview. (toggleable)
# TODO: Visible box outline on the preview. (toggleable)
# TODO: Separate cell and pixel selection modes with different functions.
# TODO: Allow upgrading a 16 color mode to 256 color mode or downgrading 256 color mode to 16 color mode if it would be lossless.
# TODO: undo quirk undoing a color put on top row ( needs investigating ... )

UNDO_LEVELS = 100
DEFAULT_FILL = True
ZOOMED_X = 4
ZOOMED_PAD = 4
PREVIEW_SPACING = 4
PREVIEW_X = ZOOMED_X + (ZOOMED_PAD * 2 + 1) * 2 + PREVIEW_SPACING

CHARS4 = array('w', ' 𜺨𜴀▘𜴉𜴊🯦𜴍𜺣𜴶𜴹𜴺▖𜵅𜵈▌𜺫🮂𜴁𜴂𜴋𜴌𜴎𜴏𜴷𜴸𜴻𜴼𜵆𜵇𜵉𜵊𜴃𜴄𜴆𜴇𜴐𜴑𜴔𜴕𜴽𜴾𜵁𜵂𜵋𜵌𜵎𜵏▝𜴅𜴈▀𜴒𜴓𜴖𜴗𜴿𜵀𜵃𜵄▞𜵍𜵐▛'
                    '𜴘𜴙𜴜𜴝𜴧𜴨𜴫𜴬𜵑𜵒𜵕𜵖𜵡𜵢𜵥𜵦𜴚𜴛𜴞𜴟𜴩𜴪𜴭𜴮𜵓𜵔𜵗𜵘𜵣𜵤𜵧𜵨🯧𜴠𜴣𜴤𜴯𜴰𜴳𜴴𜵙𜵚𜵝𜵞𜵩𜵪𜵭𜵮𜴡𜴢𜴥𜴦𜴱𜴲𜴵🮅𜵛𜵜𜵟𜵠𜵫𜵬𜵯𜵰'
                    '𜺠𜵱𜵴𜵵𜶀𜶁𜶄𜶅▂𜶬𜶯𜶰𜶻𜶼𜶿𜷀𜵲𜵳𜵶𜵷𜶂𜶃𜶆𜶇𜶭𜶮𜶱𜶲𜶽𜶾𜷁𜷂𜵸𜵹𜵼𜵽𜶈𜶉𜶌𜶍𜶳𜶴𜶷𜶸𜷃𜷄𜷇𜷈𜵺𜵻𜵾𜵿𜶊𜶋𜶎𜶏𜶵𜶶𜶹𜶺𜷅𜷆𜷉𜷊'
                    '▗𜶐𜶓▚𜶜𜶝𜶠𜶡𜷋𜷌𜷏𜷐▄𜷛𜷞▙𜶑𜶒𜶔𜶕𜶞𜶟𜶢𜶣𜷍𜷎𜷑𜷒𜷜𜷝𜷟𜷠𜶖𜶗𜶙𜶚𜶤𜶥𜶨𜶩𜷓𜷔𜷗𜷘𜷡𜷢▆𜷤▐𜶘𜶛▜𜶦𜶧𜶪𜶫𜷕𜷖𜷙𜷚▟𜷣𜷥█')


t = blessed.Terminal()

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
    SAVE_FILE = auto()
    REDRAW = auto()
    UNDO = auto()
    REDO = auto()
    SELECT = auto()
    CONFIRM = auto()
    CANCEL = auto()
    PASTE = auto()

    # for select_color_rgb
    INC_RED = auto()
    INC_GREEN = auto()
    INC_BLUE = auto()
    DEC_RED = auto()
    DEC_GREEN = auto()
    DEC_BLUE = auto()
    INC_FAST_RED = auto()
    INC_FAST_GREEN = auto()
    INC_FAST_BLUE = auto()
    DEC_FAST_RED = auto()
    DEC_FAST_GREEN = auto()
    DEC_FAST_BLUE = auto()
    TRANSPARENT = auto()

    # for selection
    COPY = auto()

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
    ord('P'): KeyActions.PICK_COLOR,
    ord('S'): KeyActions.SAVE_FILE,
    ord('R'): KeyActions.REDRAW,
    ord('u'): KeyActions.UNDO,
    ord('U'): KeyActions.REDO,
    ord('v'): KeyActions.SELECT,
    ord('V'): KeyActions.PASTE
}

KEY_ACTIONS_SELECT = {
    t.KEY_LEFT: KeyActions.MOVE_LEFT,
    t.KEY_RIGHT: KeyActions.MOVE_RIGHT,
    t.KEY_UP: KeyActions.MOVE_UP,
    t.KEY_DOWN: KeyActions.MOVE_DOWN,
    ord('a'): KeyActions.MOVE_LEFT,
    ord('d'): KeyActions.MOVE_RIGHT,
    ord('w'): KeyActions.MOVE_UP,
    ord('s'): KeyActions.MOVE_DOWN,
    t.KEY_ESCAPE: KeyActions.CANCEL,
    ord('z'): KeyActions.ZOOMED_COLOR,
    ord('c'): KeyActions.COPY
}

KEY_ACTIONS_PROMPT = {
    t.KEY_ENTER: KeyActions.CONFIRM,
    t.KEY_ESCAPE: KeyActions.CANCEL
}

KEY_ACTIONS_COLOR_RGB = {
    t.KEY_ENTER: KeyActions.CONFIRM,
    t.KEY_ESCAPE: KeyActions.CANCEL,
    ord('q'): KeyActions.INC_RED,
    ord('w'): KeyActions.INC_GREEN,
    ord('e'): KeyActions.INC_BLUE,
    ord('a'): KeyActions.DEC_RED,
    ord('s'): KeyActions.DEC_GREEN,
    ord('d'): KeyActions.DEC_BLUE,
    ord('Q'): KeyActions.INC_FAST_RED,
    ord('W'): KeyActions.INC_FAST_GREEN,
    ord('E'): KeyActions.INC_FAST_BLUE,
    ord('A'): KeyActions.DEC_FAST_RED,
    ord('S'): KeyActions.DEC_FAST_GREEN,
    ord('D'): KeyActions.DEC_FAST_BLUE,
    ord('t'): KeyActions.TRANSPARENT
}

KEY_ACTIONS_COLOR = {
    t.KEY_ENTER: KeyActions.CONFIRM,
    t.KEY_ESCAPE: KeyActions.CANCEL,
    t.KEY_LEFT: KeyActions.MOVE_LEFT,
    t.KEY_RIGHT: KeyActions.MOVE_RIGHT,
    t.KEY_UP: KeyActions.MOVE_UP,
    t.KEY_DOWN: KeyActions.MOVE_DOWN,
    ord('a'): KeyActions.MOVE_LEFT,
    ord('d'): KeyActions.MOVE_RIGHT,
    ord('w'): KeyActions.MOVE_UP,
    ord('s'): KeyActions.MOVE_DOWN,
    ord('t'): KeyActions.TRANSPARENT
}

def key_to_action(key_actions : dict[int, KeyActions], key : int) -> KeyActions:
    # convert to an action
    try:
        return key_actions[key]
    except KeyError:
        pass

    return KeyActions.NONE

DEFAULT_BG = 0 # BLACK
DEFAULT_FG = 15 # WHITE
COLORS = {
    False: f"{t.color(DEFAULT_FG)}{t.on_color(DEFAULT_BG)}",
    True:  f"{t.color(DEFAULT_BG)}{t.on_color(DEFAULT_FG)}"
}

class ColorMode(Enum):
    C16 = auto()
    C256 = auto()
    DIRECT = auto()

class DataRect:
    def __init__(self,
                 x : int, y : int,
                 w : int, h : int,
                 dw : int, data : array,
                 color_mode : ColorMode,
                 colordata_fg_r : array,
                 colordata_fg_g : array,
                 colordata_fg_b : array,
                 colordata_bg_r : array,
                 colordata_bg_g : array,
                 colordata_bg_b : array):
        self.x = x
        self.y = y
        self.w = w
        self.color_mode = color_mode
        self.whole_buffer = False
        if w == dw and h == len(colordata_fg_r) // dw:
            self.whole_buffer = True

        if self.whole_buffer:
            # if it's the whole thing, just copy it
            self.data = copy.copy(data)
            self.colordata_fg_r = copy.copy(colordata_fg_r)
            if color_mode == ColorMode.DIRECT:
                self.colordata_fg_g = copy.copy(colordata_fg_g)
                self.colordata_fg_b = copy.copy(colordata_fg_b)
                self.colordata_bg_r = copy.copy(colordata_bg_r)
                self.colordata_bg_g = copy.copy(colordata_bg_g)
                self.colordata_bg_b = copy.copy(colordata_bg_b)
        else:
            # build up the arrays of data to store locally
            self.data = array('i', itertools.repeat(0, (w * 2) * (h * 4)))
            self.colordata_fg_r = array('i', itertools.repeat(0, w * h))
            if color_mode == ColorMode.DIRECT:
                self.colordata_fg_g = array('i', itertools.repeat(0, w * h))
                self.colordata_fg_b = array('i', itertools.repeat(0, w * h))
                self.colordata_bg_r = array('i', itertools.repeat(0, w * h))
                self.colordata_bg_g = array('i', itertools.repeat(0, w * h))
                self.colordata_bg_b = array('i', itertools.repeat(0, w * h))
            cw = dw * 2
            sw = self.w * 2
            cx = self.x * 2
            for i in range(h):
                self.data[i * (sw * 4)           :i * (sw * 4) +            sw] = \
                    data[((self.y + i) * (cw * 4)) +            cx:((self.y + i) * (cw * 4)) +            cx + sw]
                self.data[i * (sw * 4) +  sw     :i * (sw * 4) +  sw +      sw] = \
                    data[((self.y + i) * (cw * 4)) +  cw +      cx:((self.y + i) * (cw * 4)) +  cw +      cx + sw]
                self.data[i * (sw * 4) + (sw * 2):i * (sw * 4) + (sw * 2) + sw] = \
                    data[((self.y + i) * (cw * 4)) + (cw * 2) + cx:((self.y + i) * (cw * 4)) + (cw * 2) + cx + sw]
                self.data[i * (sw * 4) + (sw * 3):i * (sw * 4) + (sw * 3) + sw] = \
                    data[((self.y + i) * (cw * 4)) + (cw * 3) + cx:((self.y + i) * (cw * 4)) + (cw * 3) + cx + sw]

                self.colordata_fg_r[i * self.w:i * self.w + self.w] = \
                    colordata_fg_r[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]
                if color_mode == ColorMode.DIRECT:
                    self.colordata_fg_g[i * self.w:i * self.w + self.w] = \
                        colordata_fg_g[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]
                    self.colordata_fg_b[i * self.w:i * self.w + self.w] = \
                        colordata_fg_b[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]
                    self.colordata_bg_r[i * self.w:i * self.w + self.w] = \
                        colordata_bg_r[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]
                    self.colordata_bg_g[i * self.w:i * self.w + self.w] = \
                        colordata_bg_g[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]
                    self.colordata_bg_b[i * self.w:i * self.w + self.w] = \
                        colordata_bg_b[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]

    def get_dims(self):
        return self.w, len(self.colordata_fg_r) // self.w

    def apply(self,
              dw : int, data : array,
              colordata_fg_r : array,
              colordata_fg_g : array,
              colordata_fg_b : array,
              colordata_bg_r : array,
              colordata_bg_g : array,
              colordata_bg_b : array,
              x : int = -1, y : int = -1):
        other_dest : bool = False
        # dw, x and y should be given in characer cell dimensions
        w, h = self.get_dims()
        if x >= 0:
            if y == -1:
                raise ValueError("X and Y should both or neither be set.")
            if x + w > dw:
                w = dw - x
            dh = len(colordata_fg_r) // dw
            if y + h > dh:
                h = dh - y
            other_dest = True
        else:
            x = self.x
            y = self.y

        if not other_dest and self.whole_buffer:
            # if it's the whole thing, just return it
            return w, h, self.data, \
                   self.colordata_fg_r, self.colordata_fg_g, self.colordata_fg_b, \
                   self.colordata_bg_r, self.colordata_bg_g, self.colordata_bg_b
        else:
            cw = dw * 2
            sw = self.w * 2
            cx = x * 2
            # reverse of building the arrays?
            for i in range(h):
                data[((y + i) * (cw * 4)) +            cx:((y + i) * (cw * 4)) +            cx + (w * 2)] = \
                    self.data[i * (sw * 4)           :i * (sw * 4) +            (w * 2)]
                data[((y + i) * (cw * 4)) +  cw +      cx:((y + i) * (cw * 4)) +  cw +      cx + (w * 2)] = \
                    self.data[i * (sw * 4) +  sw     :i * (sw * 4) +  sw +      (w * 2)]
                data[((y + i) * (cw * 4)) + (cw * 2) + cx:((y + i) * (cw * 4)) + (cw * 2) + cx + (w * 2)] = \
                    self.data[i * (sw * 4) + (sw * 2):i * (sw * 4) + (sw * 2) + (w * 2)]
                data[((y + i) * (cw * 4)) + (cw * 3) + cx:((y + i) * (cw * 4)) + (cw * 3) + cx + (w * 2)] = \
                    self.data[i * (sw * 4) + (sw * 3):i * (sw * 4) + (sw * 3) + (w * 2)]

                colordata_fg_r[(y + i) * dw + x:(y + i) * dw + x + w] = \
                    self.colordata_fg_r[i * self.w:i * self.w + w]
                if self.color_mode == ColorMode.DIRECT:
                    colordata_fg_g[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_fg_g[i * self.w:i * self.w + w]
                    colordata_fg_b[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_fg_b[i * self.w:i * self.w + w]
                    colordata_bg_r[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_bg_r[i * self.w:i * self.w + w]
                    colordata_bg_g[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_bg_g[i * self.w:i * self.w + w]
                    colordata_bg_b[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_bg_b[i * self.w:i * self.w + w]

        return None, None, None, None, None, None, None, None, None

COLOR_PREVIEW = "𜶉𜶉"
CURSOR = "🯧🯦"
BLOCK = "██"

TILE_CURSOR = 13
TILE_INVERT = 26
TILE_TOPLEFT = 1
TILE_LEFT = 2
TILE_BOTTOMLEFT = 3
TILE_TOPRIGHT = 4
TILE_RIGHT = 5
TILE_BOTTOMRIGHT = 6
TILE_TOP = 7
TILE_BOTTOM = 8
TILE_CORNER_TOPLEFT = 9
TILE_CORNER_BOTTOMLEFT = 10
TILE_CORNER_TOPRIGHT = 11
TILE_CORNER_BOTTOMRIGHT = 12
TILES = ("  ", "𜵊🮂", "▌ ", "𜷀▂", "🮂𜶘", " ▐", "▂𜷕", "🮂🮂", "▂▂", "𜺨 ", "𜺣 ", " 𜺫", " 𜺠",
         "🯧🯦", "𜵰𜴏", "𜵮🯦", "𜷤𜶿", "𜴢𜶫", "🯧𜶪", "𜷓𜷥", "𜴢𜴏", "𜷓𜶿", "𜴠🯦", "𜵙🯦", "🯧𜴎", "🯧𜶄",
         "██", "𜶖▆", "▐█", "𜴡🮅", "▆𜵈", "█▌", "🮅𜴍", "▆▆", "🮅🮅", "𜷥█", "𜶫█", "█𜷤", "█𜵰",
         "𜷂𜷖", "𜺠𜷓", "𜵲𜷖", "𜺫𜴢", "𜶿𜺣", "𜷂𜴶", "𜴏𜺨", "𜶿𜷓", "𜴏𜴢", "𜷁𜷖", "𜶇𜷖", "𜷂𜷔", "𜷂𜵜",)
def display_zoomed_matrix(t : blessed.Terminal,
                          x : int, y : int, pad : int,
                          dx : int, dy : int,
                          dw : int, dh : int,
                          select_x : int, select_y : int,
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

    lastcolor : str = ""

    if dy > dh:
        # if past the bottom, print normals
        print(t.normal, end='')

    for iy in range(pad * 2 + 1):
        print(t.move_xy(x, y + iy), end='')

        if dx > dw:
            # if to the right print normals
            print(t.normal, end='')
            lastcolor = ""

        for ix in range(pad * 2 + 1):
            px = dx + ix
            py = dy + iy
            tile = 0

            if py < 0:
                # if above the top, print normals
                if ix == 0 and iy == 0:
                    # only print the attribute once
                    print(t.normal, end='')
                    lastcolor = ""
            elif px < 0:
                # if to the left print normals
                if ix == 0:
                    # only print once
                    print(t.normal, end='')
                    lastcolor = ""
            elif px == dw:
                # if to the right print normals
                print(t.normal, end='')
                lastcolor = ""
            elif px > dw:
                # only print once
                pass
            elif py == dh:
                # if past the bottom, print normals
                if ix == 0:
                    # only print once
                    print(t.normal, end='')
                    lastcolor = ""
            elif py > dh:
                # only print once
                pass

            if px >= -1 and px <= dw and py >= -1 and py <= dh:
                if px > -1 and px < dw and py > -1 and py < dh:
                    # set color
                    # This is waaaaaay complicated and probably some remaining bugs
                    if use_color:
                        lastcolor_r : int = None
                        lastcolor_g : int = None
                        lastcolor_b : int = None
                        lastcolor_fg_r = colordata_fg_r[cw * cy + cx]
                        lastcolor_fg_g = colordata_fg_g[cw * cy + cx]
                        lastcolor_fg_b = colordata_fg_b[cw * cy + cx]
                        # only need R to determine transparency
                        lastcolor_bg_r = colordata_bg_r[cw * cy + cx]

                        ciy : int = py // 4
                        cix : int = px // 2
                        if color_mode == ColorMode.DIRECT:
                            if data[dw * py + px]:
                                # pixel on (foreground)
                                color_r = colordata_fg_r[cw * ciy + cix]
                                color_g = colordata_fg_g[cw * ciy + cix]
                                color_b = colordata_fg_b[cw * ciy + cix]
                                color_bg_r = colordata_bg_r[cw * ciy + cix]
                                if len(lastcolor) == 0 or \
                                   color_r != lastcolor_r or \
                                   color_g != lastcolor_g or \
                                   color_b != lastcolor_b or \
                                   color_bg_r != lastcolor_bg_r:
                                    if color_bg_r < 0:
                                        # backgrond is still transparent
                                        print(t.normal, end='')
                                        # set foreground color but select inverted tiles
                                        print(t.color_rgb(color_r, color_g, color_b), end='')
                                    else:
                                        print(t.on_color_rgb(color_r, color_g, color_b), end='')
                                        print(t.color_rgb(max(0, 255 - color_r - 64),
                                                          max(0, 255 - color_g - 64),
                                                          max(0, 255 - color_b - 64)), end='')
                                    lastcolor_bg_r = color_bg_r
                                    lastcolor_fg_r = color_r
                                    lastcolor_fg_g = color_g
                                    lastcolor_fg_b = color_b
                                    lastcolor_r = color_r
                                    lastcolor_g = color_g
                                    lastcolor_b = color_b
                                    lastcolor = "#"  # Tag with some non-empty string
                                if lastcolor_bg_r < 0:
                                    tile += TILE_INVERT
                            else:
                                # pixel off (background)
                                color_r = colordata_bg_r[cw * ciy + cix]
                                color_g = colordata_bg_g[cw * ciy + cix]
                                color_b = colordata_bg_b[cw * ciy + cix]
                                color_fg_r = colordata_fg_r[cw * ciy + cix]
                                color_fg_g = colordata_fg_g[cw * ciy + cix]
                                color_fg_b = colordata_fg_b[cw * ciy + cix]
                                if len(lastcolor) == 0 or \
                                   color_r != lastcolor_r or \
                                   color_g != lastcolor_g or \
                                   color_b != lastcolor_b or \
                                   (color_r < 0 and (color_fg_r != lastcolor_fg_r or
                                                     color_fg_g != lastcolor_fg_g or
                                                     color_fg_b != lastcolor_fg_b)):
                                    if color_r < 0:
                                        # transition to transparent background
                                        print(t.normal, end='')
                                        # set foreground
                                        print(t.color_rgb(color_fg_r, color_fg_g, color_fg_b), end='')
                                    else:
                                        print(t.on_color_rgb(color_r, color_g, color_b), end='')
                                        print(t.color_rgb(max(0, 255 - color_r - 64),
                                                          max(0, 255 - color_g - 64),
                                                          max(0, 255 - color_b - 64)), end='')
                                    lastcolor_bg_r = color_r
                                    lastcolor_fg_r = color_fg_r
                                    lastcolor_fg_g = color_fg_g
                                    lastcolor_fg_b = color_fg_b
                                    lastcolor_r = color_r
                                    lastcolor_g = color_g
                                    lastcolor_b = color_b
                                    lastcolor = "#"  # Tag with some non-empty string
                        else:
                            if data[dw * py + px]:
                                # pixel on (foreground)
                                color_r = colordata_fg_r[cw * ciy + cix]
                                color_bg_r = colordata_bg_r[cw * ciy + cix]
                                if len(lastcolor) == 0 or \
                                   color_r != lastcolor_r or \
                                   color_bg_r != lastcolor_bg_r:
                                    if color_bg_r < 0:
                                        print(t.normal, end='')
                                        print(t.color(color_r), end='')
                                    else:
                                        print(t.on_color(color_r), end='')
                                        if color_r == DEFAULT_BG:
                                            print(t.color(DEFAULT_FG), end='')
                                        else:
                                            print(t.color(DEFAULT_BG), end='')
                                    lastcolor_bg_r = color_bg_r
                                    lastcolor_fg_r = color_r
                                    lastcolor_r = color_r
                                    lastcolor = "#"  # Tag with some non-empty string
                                if lastcolor_bg_r < 0:
                                    tile += TILE_INVERT
                            else:
                                # pixel off (background)
                                color_r = colordata_bg_r[cw * ciy + cix]
                                color_fg_r = colordata_fg_r[cw * ciy + cix]
                                if len(lastcolor) == 0 or \
                                   color_r != lastcolor_r or \
                                   (color_r < 0 and color_fg_r != lastcolor_fg_r):
                                    if color_r < 0:
                                        print(t.normal, end='')
                                        print(t.color(color_fg_r), end='')
                                    else:
                                        print(t.on_color(color_r), end='')
                                        if color_r == DEFAULT_BG:
                                            print(t.color(DEFAULT_FG), end='')
                                        else:
                                            print(t.color(DEFAULT_BG), end='')
                                    lastcolor_bg_r = color_r
                                    lastcolor_fg_r = color_fg_r
                                    lastcolor_r = color_r
                                    lastcolor = "#"  # Tag with some non-empty string
                    else:
                        color = colors[data[dw * py + px]]
                        if color != lastcolor:
                            print(color, end='')
                        lastcolor = color

                    if select_x >= 0:
                        sx1 = min(dx + pad, select_x) // 2 * 2
                        sy1 = min(dy + pad, select_y) // 4 * 4
                        sx2 = max(dx + pad, select_x) // 2 * 2 + 1
                        sy2 = max(dy + pad, select_y) // 4 * 4 + 3

                        sx1 = max(0, sx1)
                        sy1 = max(0, sy1)
                        sx2 = min(dw - 1, sx2)
                        sy2 = min(dh - 1, sy2)

                        if px == sx1:
                            if py == sy1:
                                tile += TILE_TOPLEFT
                            elif py > sy1 and py < sy2:
                                tile += TILE_LEFT
                            elif py == sy2:
                                tile += TILE_BOTTOMLEFT
                        elif px > sx1 and px < sx2:
                            if py == sy1:
                                tile += TILE_TOP
                            elif py == sy2:
                                tile += TILE_BOTTOM
                        elif px == sx2:
                            if py == sy1:
                                tile += TILE_TOPRIGHT
                            elif py > sy1 and py < sy2:
                                tile += TILE_RIGHT
                            elif py == sy2:
                                tile += TILE_BOTTOMRIGHT
                    elif grid:
                        if px % 2 == 0:
                            if py % 4 == 0:
                                tile += TILE_TOPLEFT
                            elif py % 4 == 3:
                                tile += TILE_BOTTOMLEFT
                            else:
                                tile += TILE_LEFT
                        else:
                            if py % 4 == 0:
                                tile += TILE_TOPRIGHT
                            elif py % 4 == 3:
                                tile += TILE_BOTTOMRIGHT
                            else:
                                tile += TILE_RIGHT
                else:
                    if px == -1:
                        if py == -1:
                            tile += TILE_CORNER_BOTTOMRIGHT
                        elif py == dh:
                            tile += TILE_CORNER_TOPRIGHT
                        elif py > -1 and py < dh:
                            tile += TILE_RIGHT
                    elif px == dw:
                        if py == -1:
                            tile += TILE_CORNER_BOTTOMLEFT
                        elif py == dh:
                            tile += TILE_CORNER_TOPLEFT
                        elif py > -1 and py < dh:
                            tile += TILE_LEFT
                    elif px > -1 and px < dw:
                        if py == -1:
                            tile += TILE_BOTTOM
                        elif py == dh:
                            tile += TILE_TOP

            if ix == pad and iy == pad:
                tile += TILE_CURSOR
            print(TILES[tile], end='')

def make_cell(data : array, dx : int, dy : int, dw : int):
    cell : int = 0
    # offset LSB to RSB goes top left -> bottom left, top right -> bottom right
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

    return cell
 
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

    # get width in cells for colordata lookup
    cw = dw // 2

    if color_mode == ColorMode.DIRECT:
        lastcolor_fg_r = colordata_fg_r[cy * cw + cx]
        lastcolor_fg_g = colordata_fg_g[cy * cw + cx]
        lastcolor_fg_b = colordata_fg_b[cy * cw + cx]
        lastcolor_bg_r = colordata_bg_r[cy * cw + cx]
        lastcolor_bg_g = colordata_bg_g[cy * cw + cx]
        lastcolor_bg_b = colordata_bg_b[cy * cw + cx]
        if lastcolor_bg_r < 0:
            print(t.normal, end='')
        else:
            print(t.on_color_rgb(lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b), end='')
        print(t.color_rgb(lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b), end='')
    else:
        lastcolor_fg_r = colordata_fg_r[cy * cw + cx]
        lastcolor_bg_r = colordata_bg_r[cy * cw + cx]
        if lastcolor_bg_r < 0:
            print(t.normal, end='')
        else:
            print(t.on_color(lastcolor_bg_r), end='')
        print(t.color(lastcolor_fg_r), end='')

    for iy in range(h):
        print(t.move_xy(x, y + iy), end='')
        for ix in range(w):
            if color_mode == ColorMode.DIRECT:
                color_fg_r = colordata_fg_r[((cy + iy) * cw) + (cx + ix)]
                color_fg_g = colordata_fg_g[((cy + iy) * cw) + (cx + ix)]
                color_fg_b = colordata_fg_b[((cy + iy) * cw) + (cx + ix)]
                color_bg_r = colordata_bg_r[((cy + iy) * cw) + (cx + ix)]
                color_bg_g = colordata_bg_g[((cy + iy) * cw) + (cx + ix)]
                color_bg_b = colordata_bg_b[((cy + iy) * cw) + (cx + ix)]
                if color_bg_r != lastcolor_bg_r or \
                   color_bg_g != lastcolor_bg_g or \
                   color_bg_b != lastcolor_bg_b:
                    if color_bg_r < 0:
                        print(t.normal, end='')
                        # fg color gets unset, so assure it'll always
                        # think it's changed and needs to be retransmitted
                        lastcolor_fg_r = -1
                    else:
                        print(t.on_color_rgb(color_bg_r, color_bg_g, color_bg_b), end='')
                    lastcolor_bg_r = color_bg_r
                    lastcolor_bg_g = color_bg_g
                    lastcolor_bg_b = color_bg_b
                if color_fg_r != lastcolor_fg_r or \
                   color_fg_g != lastcolor_fg_g or \
                   color_fg_b != lastcolor_fg_b:
                    print(t.color_rgb(color_fg_r, color_fg_g, color_fg_b), end='')
                    lastcolor_fg_r = color_fg_r
                    lastcolor_fg_g = color_fg_g
                    lastcolor_fg_b = color_fg_b
            else:
                # paletted modes use the R channel for color value
                color_fg_r = colordata_fg_r[((cy + iy) * cw) + (cx + ix)]
                color_bg_r = colordata_bg_r[((cy + iy) * cw) + (cx + ix)]
                if color_bg_r != lastcolor_bg_r:
                    if color_bg_r < 0:
                        print(t.normal, end='')
                        lastcolor_fg_r = -1
                    else:
                        print(t.on_color(color_bg_r), end='')
                    lastcolor_bg_r = color_bg_r
                if color_fg_r != lastcolor_fg_r:
                    print(t.color(color_fg_r), end='')
                    lastcolor_fg_r = color_fg_r

            cell = make_cell(data, (cx + ix) * 2, (cy + iy) * 4, dw)
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

    bg_r = colordata_bg_r[cy * cw + cx]
    if color_mode == ColorMode.DIRECT:
        if bg_r < 0:
            print(t.normal, end='')
        else:
            print(t.on_color_rgb(bg_r,
                                 colordata_bg_g[cy * cw + cx],
                                 colordata_bg_b[cy * cw + cx]), end='')
        print(t.color_rgb(colordata_fg_r[cy * cw + cx],
                          colordata_fg_g[cy * cw + cx],
                          colordata_fg_b[cy * cw + cx]), end='')
    else:
        # paletted modes use the R channel for color value
        if bg_r < 0:
            print(t.normal, end='')
        else:
            print(t.on_color(colordata_bg_r[cy * cw + cx]), end='')
        print(t.color(colordata_fg_r[cy * cw + cx]), end='')

    print(t.move_xy(x + cx, y + cy), end='')
    cell = make_cell(data, dx, dy, dw)
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
 
def prompt(t : blessed.Terminal,
           text : str):
    inp = array('w')

    print_status(t, text)
    print()
    while True:
        is_text, key = inkey_numeric(t)
        if is_text:
            inp.append(chr(key))
            print(chr(key), end='')
        else:
            key = key_to_action(KEY_ACTIONS_PROMPT, key)
            match key:
                case KeyActions.CONFIRM:
                    break
                case KeyActions.CANCEL:
                    return None
                # TODO: make backspace work
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
                     r : int, g : int, b : int,
                     allow_transparent : bool):
    orig_r = r
    orig_g = g
    orig_b = b
    if r < 0:
        r = 0
        g = 0
        b = 0
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
        key = key_to_action(KEY_ACTIONS_COLOR_RGB, key)
        match key:
            case KeyActions.CONFIRM:
                break
            case KeyActions.CANCEL:
                r = orig_r
                g = orig_g
                b = orig_b
                break
            case KeyActions.DEC_RED:
                if r > 0:
                    r -= 1
            case KeyActions.DEC_GREEN:
                if g > 0:
                    g -= 1
            case KeyActions.DEC_BLUE:
                if b > 0:
                    b -= 1
            case KeyActions.INC_RED:
                if r < 255:
                    r += 1
            case KeyActions.INC_GREEN:
                if g < 255:
                    g += 1
            case KeyActions.INC_BLUE:
                if b < 255:
                    b += 1
            case KeyActions.DEC_FAST_RED:
                r -= 10
                r = max(0, r)
            case KeyActions.DEC_FAST_GREEN:
                g -= 10
                g = max(0, g)
            case KeyActions.DEC_FAST_BLUE:
                b -= 10
                b = max(0, b)
            case KeyActions.INC_FAST_RED:
                r += 10
                r = min(255, r)
            case KeyActions.INC_FAST_GREEN:
                g += 10
                g = min(255, g)
            case KeyActions.INC_FAST_BLUE:
                b += 10
                b = min(255, b)
            case KeyActions.TRANSPARENT:
                if allow_transparent:
                    r = -1
                    g = -1
                    b = -1
                    break

    clear_screen(t)
    return r, g, b

def select_color(t : blessed.Terminal,
                 c : int, color_mode : ColorMode,
                 allow_transparent : bool):
    x = 0
    y = 0
    width = 4
    height = 4
    if color_mode == ColorMode.C256:
        width = 16
        height = 16
    if c >= 0:
        x = c % width
        y = c // width

    clear_screen(t)

    while True:
        print(t.color(DEFAULT_BG), end='')
        for cy in range(height):
            print(t.move_xy(0, cy), end='')
            for cx in range(width):
                print(t.on_color(cy * width + cx), end='')
                print("  ", end='')

        print(t.move_xy(x * 2, y), end='')
        if x == 0 and y == 0:
            print(t.color(DEFAULT_FG), end='')
        else:
            print(t.color(DEFAULT_BG), end='')
        print(t.on_color(y * width + x), end='')
        print(CURSOR, end='')
        sys.stdout.flush()
        _, key = inkey_numeric(t)
        key = key_to_action(KEY_ACTIONS_COLOR, key)
        match key:
            case KeyActions.CONFIRM:
                c = y * width + x
                break
            case KeyActions.CANCEL:
                break
            case KeyActions.MOVE_LEFT:
                if x > 0:
                    x -= 1
            case KeyActions.MOVE_RIGHT:
                if x < width - 1:
                    x += 1
            case KeyActions.MOVE_UP:
                if y > 0:
                    y -= 1
            case KeyActions.MOVE_DOWN:
                if y < height - 1:
                    y += 1
            case KeyActions.TRANSPARENT:
                if allow_transparent:
                    c = -1
                    break

    clear_screen(t)
    return c

def get_default_colors(color_mode : ColorMode):
    # set to white on transparent
    if color_mode == ColorMode.DIRECT:
        return 255, 255, 255, -1, -1, -1

    return DEFAULT_FG, 0, 0, -1, 0, 0

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

def save_file(t : blessed.Terminal,
              path : pathlib.Path,
              data : array, dw : int,
              color_mode : ColorMode,
              colordata_fg_r : array,
              colordata_fg_g : array,
              colordata_fg_b : array,
              colordata_bg_r : array,
              colordata_bg_g : array,
              colordata_bg_b : array):
    # very similar to display_matrix
    with path.open('w') as out:
        # get width in cells for colordata lookup
        cw = dw // 2

        for iy in range(len(data) // dw // 4):
            # print on every line, because it's normaled at the end of each line
            if color_mode == ColorMode.DIRECT:
                lastcolor_fg_r = colordata_fg_r[iy * cw]
                lastcolor_fg_g = colordata_fg_g[iy * cw]
                lastcolor_fg_b = colordata_fg_b[iy * cw]
                lastcolor_bg_r = colordata_bg_r[iy * cw]
                lastcolor_bg_g = colordata_bg_g[iy * cw]
                lastcolor_bg_b = colordata_bg_b[iy * cw]
                if lastcolor_bg_r < 0:
                    out.write(t.normal)
                else:
                    out.write(t.on_color_rgb(lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b))
                out.write(t.color_rgb(lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b))
            else:
                lastcolor_fg_r = colordata_fg_r[iy * cw]
                lastcolor_bg_r = colordata_bg_r[iy * cw]
                if lastcolor_bg_r < 0:
                    out.write(t.normal)
                else:
                    out.write(t.on_color(lastcolor_bg_r))
                out.write(t.color(lastcolor_fg_r))

            for ix in range(dw // 2):
                if color_mode == ColorMode.DIRECT:
                    color_fg_r = colordata_fg_r[iy * cw + ix]
                    color_fg_g = colordata_fg_g[iy * cw + ix]
                    color_fg_b = colordata_fg_b[iy * cw + ix]
                    color_bg_r = colordata_bg_r[iy * cw + ix]
                    color_bg_g = colordata_bg_g[iy * cw + ix]
                    color_bg_b = colordata_bg_b[iy * cw + ix]
                    if color_bg_r != lastcolor_bg_r or \
                       color_bg_g != lastcolor_bg_g or \
                       color_bg_b != lastcolor_bg_b:
                        if color_bg_r < 0:
                            out.write(t.normal)
                            # fg color gets unset, so assure it'll always
                            # think it's changed and needs to be retransmitted
                            lastcolor_fg_r = -1
                        else:
                            out.write(t.on_color_rgb(color_bg_r, color_bg_g, color_bg_b))
                        lastcolor_bg_r = color_bg_r
                        lastcolor_bg_g = color_bg_g
                        lastcolor_bg_b = color_bg_b
                    if color_fg_r != lastcolor_fg_r or \
                       color_fg_g != lastcolor_fg_g or \
                       color_fg_b != lastcolor_fg_b:
                        out.write(t.color_rgb(color_fg_r, color_fg_g, color_fg_b))
                        lastcolor_fg_r = color_fg_r
                        lastcolor_fg_g = color_fg_g
                        lastcolor_fg_b = color_fg_b
                else:
                    # paletted modes use the R channel for color value
                    color_fg_r = colordata_fg_r[iy * cw + ix]
                    color_bg_r = colordata_bg_r[iy * cw + ix]
                    if color_bg_r != lastcolor_bg_r:
                        if color_bg_r < 0:
                            out.write(t.normal)
                            lastcolor_fg_r = -1
                        else:
                            out.write(t.on_color(color_bg_r))
                        lastcolor_bg_r = color_bg_r
                    if color_fg_r != lastcolor_fg_r:
                        out.write(t.color(color_fg_r))
                        lastcolor_fg_r = color_fg_r

                cell = make_cell(data, ix * 2, iy * 4, dw)
                out.write(CHARS4[cell])
            out.write(t.normal)
            out.write('\n')

def load_file(t : blessed.Terminal,
              max_color_mode : ColorMode,
              filename : str):
    color_mode : ColorMode | None = None
    max_color = 0
    max_row_len = 0
    rows = []
    colordata_fg_r_rows = []
    colordata_fg_g_rows = []
    colordata_fg_b_rows = []
    colordata_bg_r_rows = []
    colordata_bg_g_rows = []
    colordata_bg_b_rows = []

    # make these parseable
    color_rgb_re = re.compile(t.caps['color_rgb'].re_compiled.pattern.replace("\\d+", "(\\d+)"))
    on_color_rgb_re = re.compile(t.caps['on_color_rgb'].re_compiled.pattern.replace("\\d+", "(\\d+)"))
    color256_re = re.compile(t.caps['color256'].re_compiled.pattern.replace("\\d+", "(\\d+)"))
    on_color256_re = re.compile(t.caps['on_color256'].re_compiled.pattern.replace("\\d+", "(\\d+)"))
    set_a_attributes1_re = re.compile(t.caps['set_a_attributes1'].re_compiled.pattern.replace("\\d+", "(\\d+)"))

    with open(filename, 'r') as infile:
        for line in infile.readlines():
            fg_r = None
            fg_g = None
            fg_b = None
            bg_r = None
            bg_g = None
            bg_b = None

            # 4 rows at a time
            rows.append(array('i'))
            rows.append(array('i'))
            rows.append(array('i'))
            rows.append(array('i'))
            colordata_fg_r_rows.append(array('i'))
            colordata_fg_g_rows.append(array('i'))
            colordata_fg_b_rows.append(array('i'))
            colordata_bg_r_rows.append(array('i'))
            colordata_bg_g_rows.append(array('i'))
            colordata_bg_b_rows.append(array('i'))

            pos = 0
            while True:
                if pos == len(line):
                    break

                # find color code
                match = t._caps_compiled_any.match(line[pos:])
                groupdict = match.groupdict()
                if groupdict['MISMATCH'] is not None:
                    if fg_r is None or bg_r is None:
                        raise ValueError("Couldn't find color code!")
                    if fg_g is None:
                        # make sure the arrays have sensible numerical values
                        fg_g = 0
                        fg_b = 0
                        bg_g = 0
                        bg_b = 0

                    colordata_fg_r_rows[-1].append(fg_r)
                    colordata_fg_g_rows[-1].append(fg_g)
                    colordata_fg_b_rows[-1].append(fg_b)
                    colordata_bg_r_rows[-1].append(bg_r)
                    colordata_bg_g_rows[-1].append(bg_g)
                    colordata_bg_b_rows[-1].append(bg_b)

                    cell = CHARS4.index(line[pos])
                    # offset LSB to RSB goes top left -> bottom left, top right -> bottom right
                    rows[-4].append(cell & 1)
                    rows[-3].append((cell & 2) >> 1)
                    rows[-2].append((cell & 4) >> 2)
                    rows[-1].append((cell & 8) >> 3)
                    rows[-4].append((cell & 16) >> 4)
                    rows[-3].append((cell & 32) >> 5)
                    rows[-2].append((cell & 64) >> 6)
                    rows[-1].append((cell & 128) >> 7)
                elif groupdict['sgr0'] is not None:
                    # normal (transparent bg)
                    bg_r = -1
                    bg_g = -1
                    bg_b = -1
                    # also technically rewrites fg color
                    # but this doesn't support default terminal foreground color
                elif groupdict['color_rgb'] is not None:
                    if color_mode is None:
                        color_mode = ColorMode.DIRECT
                    else:
                        if color_mode != ColorMode.DIRECT:
                            raise ValueError("Conflicting color code types!")

                    r, g, b = color_rgb_re.match(line[pos:pos+match.span()[1]]).groups()
                    fg_r = int(r)
                    fg_g = int(g)
                    fg_b = int(b)
                elif groupdict['on_color_rgb'] is not None:
                    if color_mode is None:
                        color_mode = ColorMode.DIRECT
                    else:
                        if color_mode != ColorMode.DIRECT:
                            raise ValueError("Conflicting color code types!")

                    r, g, b = on_color_rgb_re.match(line[pos:pos+match.span()[1]]).groups()
                    bg_r = int(r)
                    bg_g = int(g)
                    bg_b = int(b)
                elif groupdict['color256'] is not None:
                    if color_mode is None:
                        color_mode = ColorMode.C256
                    else:
                        if color_mode != ColorMode.C256:
                            raise ValueError("Conflicting color code types!")

                    r = color256_re.match(line[pos:pos+match.span()[1]]).groups()
                    fg_r = int(r)
                    max_color = max(max_color, fg_r)
                elif groupdict['on_color256'] is not None:
                    if color_mode is None:
                        color_mode = ColorMode.C256
                    else:
                        if color_mode != ColorMode.C256:
                            raise ValueError("Conflicting color code types!")

                    r = on_color256_re.match(line[pos:pos+match.span()[1]]).groups()
                    bg_r = int(r)
                    max_color = max(max_color, bg_r)
                elif groupdict['set_a_attributes1'] is not None:
                    attrib, = set_a_attributes1_re.match(line[pos:pos+match.span()[1]]).groups()
                    attrib = int(attrib)

                    if (attrib >= 30 and attrib <= 37) or \
                       (attrib >= 40 and attrib <= 47) or \
                       (attrib >= 90 and attrib <= 97) or \
                       (attrib >= 99 and attrib <= 107):
                        if color_mode is None:
                            color_mode = ColorMode.C256
                        else:
                            if color_mode != ColorMode.C256:
                                raise ValueError("Conflicting color code types!")

                        if attrib >= 30 and attrib <= 37:
                            fg_r = attrib - 30
                            max_color = max(max_color, fg_r)
                        elif attrib >= 40 and attrib <= 47:
                            bg_r = attrib - 40
                            max_color = max(max_color, bg_r)
                        elif attrib >= 90 and attrib <= 97:
                            fg_r = attrib - 90 + 8
                            max_color = max(max_color, fg_r)
                        elif attrib >= 100 and attrib <= 107:
                            bg_r = attrib - 100 + 8
                            max_color = max(max_color, bg_r)

                pos += match.span()[1]

            max_row_len = max(max_row_len, len(colordata_fg_r_rows[-1]))

    cwidth = max_row_len
    width = cwidth * 2
    height = len(colordata_fg_r_rows) * 4

    if color_mode == ColorMode.C256 and max_color <= 15:
        color_mode = ColorMode.C16

    # allocate the structures
    data = array('i', itertools.repeat(0, width * height))
    colordata_fg_r, colordata_fg_g, colordata_fg_b, \
        colordata_bg_r, colordata_bg_g, colordata_bg_b = \
        new_color_data(color_mode, width, height)

    # copy the data in to them
    for i in range(height // 4):
        colordata_fg_r[cwidth * i:cwidth * i + len(colordata_fg_r_rows[i])] = colordata_fg_r_rows[i][:]
        colordata_fg_g[cwidth * i:cwidth * i + len(colordata_fg_g_rows[i])] = colordata_fg_g_rows[i][:]
        colordata_fg_b[cwidth * i:cwidth * i + len(colordata_fg_b_rows[i])] = colordata_fg_b_rows[i][:]
        colordata_bg_r[cwidth * i:cwidth * i + len(colordata_bg_r_rows[i])] = colordata_bg_r_rows[i][:]
        colordata_bg_g[cwidth * i:cwidth * i + len(colordata_bg_g_rows[i])] = colordata_bg_g_rows[i][:]
        colordata_bg_b[cwidth * i:cwidth * i + len(colordata_bg_b_rows[i])] = colordata_bg_b_rows[i][:]
        data[width * 4 * i              :width * 4 * i               + len(rows[i * 4    ])] = \
            rows[i * 4    ][:]
        data[width * 4 * i + (width * 1):width * 4 * i + (width * 1) + len(rows[i * 4 + 1])] = \
            rows[i * 4 + 1][:]
        data[width * 4 * i + (width * 2):width * 4 * i + (width * 2) + len(rows[i * 4 + 2])] = \
            rows[i * 4 + 2][:]
        data[width * 4 * i + (width * 3):width * 4 * i + (width * 3) + len(rows[i * 4 + 3])] = \
            rows[i * 4 + 3][:]

    return width, height, color_mode, data, \
        colordata_fg_r, colordata_fg_g, colordata_fg_b, \
        colordata_bg_r, colordata_bg_g, colordata_bg_b

def make_copy(x : int, y : int, w : int, h : int,
              dw : int, data : array,
              color_mode : ColorMode,
              colordata_fg_r : array,
              colordata_fg_g : array,
              colordata_fg_b : array,
              colordata_bg_r : array,
              colordata_bg_g : array,
              colordata_bg_b : array):
    # convert from pixels to character cells which the dimensions occupy
    cw = w // 2 + (w % 2)
    ch = h // 4
    if ((y + h) % 4) - (y % 4) > 0:
        ch += 1
    return DataRect(x // 2, y // 4, cw, ch,
                    dw // 2, data, color_mode,
                    colordata_fg_r, colordata_fg_g, colordata_fg_b,
                    colordata_bg_r, colordata_bg_g, colordata_bg_b)

def make_undo(undos : list[None | DataRect],
              redos : list[None | DataRect],
              x : int, y : int, w : int, h : int,
              dw : int, data : array,
              color_mode : ColorMode,
              colordata_fg_r : array,
              colordata_fg_g : array,
              colordata_fg_b : array,
              colordata_bg_r : array,
              colordata_bg_g : array,
              colordata_bg_b : array):
    if len(undos) >= UNDO_LEVELS:
        del undos[0]

    redos.clear()
    undos.append(make_copy(x, y, w, h, dw, data, color_mode,
                           colordata_fg_r, colordata_fg_g, colordata_fg_b,
                           colordata_bg_r, colordata_bg_g, colordata_bg_b))

def apply_undo(undos : list[None | DataRect],
               redos : list[None | DataRect],
               dw : int, dh : int, data : array,
               color_mode : ColorMode,
               colordata_fg_r : array,
               colordata_fg_g : array,
               colordata_fg_b : array,
               colordata_bg_r : array,
               colordata_bg_g : array,
               colordata_bg_b : array):
    if len(undos) == 0:
        # just return what was given, no change
        return dw, dh, data, \
               colordata_fg_r, colordata_fg_g, colordata_fg_b, \
               colordata_bg_r, colordata_bg_g, colordata_bg_b

    # make redo
    if len(redos) >= UNDO_LEVELS:
        del redos[0]
    undo = undos.pop(-1)
    if undo.whole_buffer:
        redos.append(make_copy(0, 0, dw, dh, dw, data, color_mode,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b))
    else:
        # dimensions have been converted to character cells
        redos.append(make_copy(undo.x * 2, undo.y * 4, undo.w * 2, len(undo.colordata_fg_r) // undo.w * 4,
                               dw, data, color_mode,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b))

    new_dw, new_dh, new_data, \
        new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
        new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b = \
        undo.apply(dw // 2, data,
                   colordata_fg_r, colordata_fg_g, colordata_fg_b,
                   colordata_bg_r, colordata_bg_g, colordata_bg_b)
    if new_data is not None:
        # return the new one, convert dimensions in character cells to pixels
        return new_dw * 2, new_dh * 4, new_data, \
               new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
               new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b

    # return back the originals
    return dw, dh, data, \
           colordata_fg_r, colordata_fg_g, colordata_fg_b, \
           colordata_bg_r, colordata_bg_g, colordata_bg_b

def apply_redo(undos : list[None | DataRect],
               redos : list[None | DataRect],
               dw : int, dh : int, data : array,
               color_mode : ColorMode,
               colordata_fg_r : array,
               colordata_fg_g : array,
               colordata_fg_b : array,
               colordata_bg_r : array,
               colordata_bg_g : array,
               colordata_bg_b : array):
    if len(redos) == 0:
        # just return what was given, no change
        return dw, dh, data, \
               colordata_fg_r, colordata_fg_g, colordata_fg_b, \
               colordata_bg_r, colordata_bg_g, colordata_bg_b

    # make undo
    if len(undos) >= UNDO_LEVELS:
        del undos[0]
    redo = redos.pop(-1)
    if redo.whole_buffer:
        undos.append(make_copy(0, 0, dw, dh, dw, data, color_mode,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b))
    else:
        # dimensions have been converted to character cells
        undos.append(make_copy(redo.x * 2, redo.y * 4, redo.w * 2, len(redo.colordata_fg_r) // redo.w * 4,
                               dw, data, color_mode,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b))

    new_dw, new_dh, new_data, \
        new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
        new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b = \
        redo.apply(dw // 2, data,
                   colordata_fg_r, colordata_fg_g, colordata_fg_b,
                   colordata_bg_r, colordata_bg_g, colordata_bg_b)
    if new_data is not None:
        # return the new one, convert dimensions in character cells to pixels
        return new_dw * 2, new_dh * 4, new_data, \
               new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
               new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b

    # return back the originals
    return dw, dh, data, \
           colordata_fg_r, colordata_fg_g, colordata_fg_b, \
           colordata_bg_r, colordata_bg_g, colordata_bg_b


def main():
    width : int = 20
    height : int = 20
    x : int = 0
    y : int = 0
    grid : bool = True
    zoomed_color : bool = True
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
    undos : list[None | DataRect] = []
    redos : list[None | DataRect] = []
    select_x : int = -1
    select_y : int = -1
    clipboard : None | DataRect = None

    if t.number_of_colors == 256:
        max_color_mode = ColorMode.C256
    elif t.number_of_colors < 256:
        max_color_mode = ColorMode.C16
    color_mode = max_color_mode
    fg_r, fg_g, fg_b, bg_r, bg_g, bg_b = get_default_colors(color_mode)

    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)

    if len(sys.argv) > 1:
        width, height, color_mode, data, \
            colordata_fg_r, colordata_fg_g, colordata_fg_b, \
            colordata_bg_r, colordata_bg_g, colordata_bg_b = \
            load_file(t, max_color_mode, sys.argv[1])
    else:
        data = array('i', itertools.repeat(0, width * height))
        if DEFAULT_FILL:
            # fill with some pattern to show it's working
            for i in range(0, width * height, 3):
                data[i] = 1

        colordata_fg_r, colordata_fg_g, colordata_fg_b, \
            colordata_bg_r, colordata_bg_g, colordata_bg_b = \
            new_color_data(color_mode, width, height)

    #global logfile
    #logfile = open("log.txt", 'w')

    with t.cbreak(), t.fullscreen(), t.hidden_cursor():
        while True:
            if refresh_matrix:
                for i in range(height // 4):
                    print(t.move_xy(PREVIEW_X - 1, 2 + i), end='')
                    print(TILES[TILE_RIGHT][1], end='')
                for i in range(height // 4):
                    print(t.move_xy(PREVIEW_X + width // 2, 2 + i), end='')
                    print(TILES[TILE_LEFT][0], end='')
                print(t.move_xy(PREVIEW_X - 1, 2 + (height // 4)), end='')
                print(TILES[TILE_CORNER_TOPRIGHT][1], end='')
                for i in range(width // 2): 
                    print(TILES[TILE_TOP][0], end='')
                print(TILES[TILE_CORNER_TOPLEFT][0], end='')
 
                display_matrix(t, color_mode, PREVIEW_X, 2, width // 2, height // 4, 0, 0, width, data,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b)
                refresh_matrix = False

            print(t.move_xy(0, 2), end='')
            print(color_str, end='')
            print("𜶉𜶉", end='')
            display_zoomed_matrix(t, ZOOMED_X, 2, ZOOMED_PAD,
                                  x, y, width, height,
                                  select_x, select_y,
                                  COLORS, grid, zoomed_color, color_mode, data,
                                  colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                  colordata_bg_r, colordata_bg_g, colordata_bg_b)
            if color_mode == ColorMode.DIRECT:
                bgstr = "Transparent"
                if bg_r >= 0:
                    bgstr = f"{bg_r} {bg_g} {bg_b}"
                print_status(t, f"{color_mode.name} {x}, {y}  {fg_r} {fg_g} {fg_b}  {bgstr}", 1)
            else:
                bgstr = "Transparent"
                if bg_r >= 0:
                    bgstr = f"{bg_r}"
                print_status(t, f"{color_mode.name} {x}, {y}  {fg_r}  {bgstr}", 1)
            sys.stdout.flush()
            _, key = inkey_numeric(t)

            print(t.move_xy(0, 0), end='')
            if select_x >= 0:
                key = key_to_action(KEY_ACTIONS_SELECT, key)
                match key:
                    case KeyActions.MOVE_LEFT:
                        x -= 1
                    case KeyActions.MOVE_RIGHT:
                        x += 1
                    case KeyActions.MOVE_UP:
                        y -= 1
                    case KeyActions.MOVE_DOWN:
                        y += 1
                    case KeyActions.CANCEL:
                        select_x = -1
                        select_y = -1
                        print_status(t, "Left selection mode.")
                    case KeyActions.ZOOMED_COLOR:
                        zoomed_color = not zoomed_color
                        if zoomed_color:
                            print_status(t, f"Zoomed view color toggled on.")
                        else:
                            print_status(t, f"Zoomed view color toggled off.")
                    case KeyActions.COPY:
                        # get top left (1) and bottom right (2)
                        sx1 = min(x, select_x)
                        sy1 = min(y, select_y)
                        sx2 = max(x, select_x) + 1
                        sy2 = max(y, select_y) + 1

                        # clamp
                        sx1 = max(0, sx1)
                        sy1 = max(0, sy1)
                        sx2 = min(width - 1, sx2)
                        sy2 = min(height - 1, sy2)

                        # get width, height
                        cw = sx2 - sx1
                        ch = sy2 - sy1
                        clipboard = make_copy(sx1, sy1, cw, ch, width, data, color_mode,
                                              colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                              colordata_bg_r, colordata_bg_g, colordata_bg_b)
                        print_status(t, f"Copied.")
                continue

            key = key_to_action(KEY_ACTIONS, key)
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
                        make_undo(undos, redos,
                                  x, y, 1, 1, width, data,
                                  color_mode,
                                  colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                  colordata_bg_r, colordata_bg_g, colordata_bg_b)

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
                    if newwidth == width and newheight == height:
                        print_status(t, "New width and height are the same.")
                        continue

                    make_undo(undos, redos,
                              0, 0, width, height, width, data,
                              color_mode,
                              colordata_fg_r, colordata_fg_g, colordata_fg_b,
                              colordata_bg_r, colordata_bg_g, colordata_bg_b)

                    newdata = array('i', itertools.repeat(0, newwidth * newheight))
                    newcolordata_fg_r, newcolordata_fg_g, newcolordata_fg_b, \
                        newcolordata_bg_r, newcolordata_bg_g, newcolordata_bg_b = \
                        new_color_data(color_mode, newwidth, newheight)
                    smallestwidth = min(width, newwidth)
                    smallestheight = min(height, newheight)
                    for i in range(smallestheight):
                        newdata[newwidth * i:newwidth * i + smallestwidth] = data[width * i:width * i + smallestwidth]
                    for i in range(smallestheight // 4):
                        newcolordata_fg_r[(newwidth // 2) * i:(newwidth // 2) * i + (smallestwidth // 2)] = \
                            colordata_fg_r[(width // 2) * i:(width // 2) * i + (smallestwidth // 2)]
                        newcolordata_fg_g[(newwidth // 2) * i:(newwidth // 2) * i + (smallestwidth // 2)] = \
                            colordata_fg_g[(width // 2) * i:(width // 2) * i + (smallestwidth // 2)]
                        newcolordata_fg_b[(newwidth // 2) * i:(newwidth // 2) * i + (smallestwidth // 2)] = \
                            colordata_fg_b[(width // 2) * i:(width // 2) * i + (smallestwidth // 2)]
                        newcolordata_bg_r[(newwidth // 2) * i:(newwidth // 2) * i + (smallestwidth // 2)] = \
                            colordata_bg_r[(width // 2) * i:(width // 2) * i + (smallestwidth // 2)]
                        newcolordata_bg_g[(newwidth // 2) * i:(newwidth // 2) * i + (smallestwidth // 2)] = \
                            colordata_bg_g[(width // 2) * i:(width // 2) * i + (smallestwidth // 2)]
                        newcolordata_bg_b[(newwidth // 2) * i:(newwidth // 2) * i + (smallestwidth // 2)] = \
                            colordata_bg_b[(width // 2) * i:(width // 2) * i + (smallestwidth // 2)]
                    data = newdata
                    colordata_fg_r = newcolordata_fg_r
                    colordata_fg_g = newcolordata_fg_g
                    colordata_fg_b = newcolordata_fg_b
                    colordata_bg_r = newcolordata_bg_r
                    colordata_bg_g = newcolordata_bg_g
                    colordata_bg_b = newcolordata_bg_b
                    width = newwidth
                    height = newheight
                    x = min(x, width)
                    y = min(y, height)
                    clear_screen(t)
                    refresh_matrix = True
                    print_status(t, f"Image resized to {width}, {height}.")
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
                        make_undo(undos, redos,
                                  0, 0, width, height, width, data,
                                  color_mode,
                                  colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                  colordata_bg_r, colordata_bg_g, colordata_bg_b)
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
                        fg_r, fg_g, fg_b = select_color_rgb(t, fg_r, fg_g, fg_b, False)
                        print_status(t, f"Foreground color RGB {fg_r}, {fg_g}, {fg_b} selected.")
                    else:
                        fg_r = select_color(t, fg_r, color_mode, False)
                        print_status(t, f"Foreground color index {fg_r} selected.")
                    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)
                    # screen was cleared so needs to be drawn
                    refresh_matrix = True
                case KeyActions.SELECT_BG_COLOR:
                    if color_mode == ColorMode.DIRECT:
                        bg_r, bg_g, bg_b = select_color_rgb(t, bg_r, bg_g, bg_b, True)
                        if bg_r < 0:
                            print_status(t, f"Transparent background selected.")
                        else:
                            print_status(t, f"Background color RGB {bg_r}, {bg_g}, {bg_b} selected.")
                    else:
                        bg_r = select_color(t, bg_r, color_mode, True)
                        if bg_r < 0:
                            print_status(t, f"Transparent background selected.")
                        else:
                            print_status(t, f"Background color index {bg_r} selected.")
                    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)
                    # screen was cleared so needs to be drawn
                    refresh_matrix = True
                case KeyActions.PUT_COLOR:
                    make_undo(undos, redos,
                              x, y, 1, 1, width, data,
                              color_mode,
                              colordata_fg_r, colordata_fg_g, colordata_fg_b,
                              colordata_bg_r, colordata_bg_g, colordata_bg_b)

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
                        bg_b = colordata_bg_b[((y // 4) * (width // 2)) + (x // 2)]
                    else:
                        fg_r = colordata_fg_r[((y // 4) * (width // 2)) + (x // 2)]
                        bg_r = colordata_bg_r[((y // 4) * (width // 2)) + (x // 2)]
                    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)
                case KeyActions.SAVE_FILE:
                    filename = prompt(t, "Filename?")
                    if filename is not None:
                        path = pathlib.Path(filename)
                        if path.exists():
                            ans = prompt_yn(t, "File exists, overwrite?")
                            if not ans:
                                print_status(t, "Save canceled.")
                                continue

                        save_file(t, path, data, width, color_mode,
                                  colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                  colordata_bg_r, colordata_bg_g, colordata_bg_b)
                        print_status(t, "File saved.")
                    else:
                        print_status(t, "Save canceled.")
                case KeyActions.REDRAW:
                    clear_screen(t)
                    refresh_matrix = True
                case KeyActions.UNDO:
                    undos_len = len(undos)
                    width, height, data, \
                        colordata_fg_r, colordata_fg_g, colordata_fg_b, \
                        colordata_bg_r, colordata_bg_g, colordata_bg_b = \
                        apply_undo(undos, redos,
                                   width, height, data,
                                   color_mode,
                                   colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                   colordata_bg_r, colordata_bg_g, colordata_bg_b)
                    if undos_len == len(undos):
                        print_status(t, "No more undos.")
                    else:
                        clear_screen(t)
                        refresh_matrix = True
                        print_status(t, "Undid.")
                case KeyActions.REDO:
                    redos_len = len(redos)
                    width, height, data, \
                        colordata_fg_r, colordata_fg_g, colordata_fg_b, \
                        colordata_bg_r, colordata_bg_g, colordata_bg_b = \
                        apply_redo(undos, redos,
                                   width, height, data,
                                   color_mode,
                                   colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                   colordata_bg_r, colordata_bg_g, colordata_bg_b)
                    if redos_len == len(redos):
                        print_status(t, "No more redos.")
                    else:
                        clear_screen(t)
                        refresh_matrix = True
                        print_status(t, "Redone.")
                case KeyActions.SELECT:
                    if x < 0 or x > width - 1 or y < 0 or y > height - 1:
                        print_status(t, "Out of range.")
                    else:
                        select_x = x
                        select_y = y
                        print_status(t, "Entered selection mode.")
                case KeyActions.PASTE:
                    if clipboard != None:
                        w, h = clipboard.get_dims()
                        make_undo(undos, redos,
                                  x, y, w, h, width, data,
                                  color_mode,
                                  colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                  colordata_bg_r, colordata_bg_g, colordata_bg_b)

                        clipboard.apply(width // 2, data,
                                         colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                         colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                         x // 2, y // 4)
                        refresh_matrix = True
                        print_status(t, "Pasted.")

if __name__ == '__main__':
    main()
