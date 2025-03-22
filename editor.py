#!/usr/bin/env python

from array import array
import itertools
import sys
from enum import Enum, auto
import pathlib
import re
import copy
import math
import signal

import blessed

# TODO: Add line and (maybe? probably not) flood fill.
# TODO: More selection functions.
#         shift 1px - pixels
#         Maybe affine transforms?
# TODO: Maybe add preview viewport.
# TODO: Various screen refresh bugs.
# TODO: Maybe revamped paste for affine pasting? also multiple named clipboards
# TODO: Maybe replace foreground/background color
# TODO: Save filename.

# TODO: undo quirk undoing a color put on top row
# TODO: another undo quirk with undoing pastes
#   Undo quirks might be finally resolved due to finding/fixing some bugs in related functions
#   but i'll leave them here just in case they crop up again.

UNDO_LEVELS = 100
DEFAULT_FILL = False
DEFAULT_WIDTH = 128
DEFAULT_HEIGHT = 128
ZOOMED_X = 4
ZOOMED_PAD = 4
PREVIEW_SPACING = 4
FAST_COLOR_VALUE = 10
PREVIEW_X = ZOOMED_X + (ZOOMED_PAD * 2 + 1) * 2 + PREVIEW_SPACING

CHARS4 = array('w', ' 𜺨𜴀▘𜴉𜴊🯦𜴍𜺣𜴶𜴹𜴺▖𜵅𜵈▌𜺫🮂𜴁𜴂𜴋𜴌𜴎𜴏𜴷𜴸𜴻𜴼𜵆𜵇𜵉𜵊𜴃𜴄𜴆𜴇𜴐𜴑𜴔𜴕𜴽𜴾𜵁𜵂𜵋𜵌𜵎𜵏▝𜴅𜴈▀𜴒𜴓𜴖𜴗𜴿𜵀𜵃𜵄▞𜵍𜵐▛'
                    '𜴘𜴙𜴜𜴝𜴧𜴨𜴫𜴬𜵑𜵒𜵕𜵖𜵡𜵢𜵥𜵦𜴚𜴛𜴞𜴟𜴩𜴪𜴭𜴮𜵓𜵔𜵗𜵘𜵣𜵤𜵧𜵨🯧𜴠𜴣𜴤𜴯𜴰𜴳𜴴𜵙𜵚𜵝𜵞𜵩𜵪𜵭𜵮𜴡𜴢𜴥𜴦𜴱𜴲𜴵🮅𜵛𜵜𜵟𜵠𜵫𜵬𜵯𜵰'
                    '𜺠𜵱𜵴𜵵𜶀𜶁𜶄𜶅▂𜶬𜶯𜶰𜶻𜶼𜶿𜷀𜵲𜵳𜵶𜵷𜶂𜶃𜶆𜶇𜶭𜶮𜶱𜶲𜶽𜶾𜷁𜷂𜵸𜵹𜵼𜵽𜶈𜶉𜶌𜶍𜶳𜶴𜶷𜶸𜷃𜷄𜷇𜷈𜵺𜵻𜵾𜵿𜶊𜶋𜶎𜶏𜶵𜶶𜶹𜶺𜷅𜷆𜷉𜷊'
                    '▗𜶐𜶓▚𜶜𜶝𜶠𜶡𜷋𜷌𜷏𜷐▄𜷛𜷞▙𜶑𜶒𜶔𜶕𜶞𜶟𜶢𜶣𜷍𜷎𜷑𜷒𜷜𜷝𜷟𜷠𜶖𜶗𜶙𜶚𜶤𜶥𜶨𜶩𜷓𜷔𜷗𜷘𜷡𜷢▆𜷤▐𜶘𜶛▜𜶦𜶧𜶪𜶫𜷕𜷖𜷙𜷚▟𜷣𜷥█')


t = blessed.Terminal()
need_winch : bool = False
need_cont : bool = False
interrupted : bool = False
orig_winch = None
orig_cont = None

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
    SELECT_TILES = auto()
    SELECT_PIXELS = auto()
    CONFIRM = auto()
    CANCEL = auto()
    PASTE = auto()
    LINE = auto()
    HELP = auto()

    # for prompt
    BACKSPACE = auto()

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
    OPERATION = auto()
    TOOL_MODE = auto()
    RECT = auto()
    CIRCLE = auto()

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
    ord('i'): KeyActions.PICK_COLOR,
    ord('S'): KeyActions.SAVE_FILE,
    ord('R'): KeyActions.REDRAW,
    ord('u'): KeyActions.UNDO,
    ord('U'): KeyActions.REDO,
    ord('v'): KeyActions.SELECT_TILES,
    ord('V'): KeyActions.SELECT_PIXELS,
    ord('P'): KeyActions.PASTE,
    ord('H'): KeyActions.HELP
}

KEY_ACTIONS_DESCRIPTIONS = {
    KeyActions.QUIT: "Quit",
    KeyActions.MOVE_LEFT: "Move Left",
    KeyActions.MOVE_RIGHT: "Move Right",
    KeyActions.MOVE_UP: "Move Up",
    KeyActions.MOVE_DOWN: "Move Down",
    KeyActions.TOGGLE: "Toggle Pixel",
    KeyActions.RESIZE: "Resize Image",
    KeyActions.GRID: "Toggle zoomed view grid",
    KeyActions.ZOOMED_COLOR: "Toggle zoomed view color",
    KeyActions.CLEAR: "Clear Image",
    KeyActions.HOME: "Return to home position (0, 0)",
    KeyActions.EDGE: "Find nearest edge from outside canvas",
    KeyActions.COLOR_MODE: "Select color mode (16, 256, DIRECT RGB)",
    KeyActions.SELECT_FG_COLOR: "Select foreground color",
    KeyActions.SELECT_BG_COLOR: "Select background color",
    KeyActions.PUT_COLOR: "Put color in to cell",
    KeyActions.PICK_COLOR: "Pick color from cell",
    KeyActions.SAVE_FILE: "Save",
    KeyActions.REDRAW: "Redraw Screen",
    KeyActions.UNDO: "Undo",
    KeyActions.REDO: "Redo",
    KeyActions.SELECT_TILES: "Tiles selection mode/functions",
    KeyActions.SELECT_PIXELS: "Pixels selection mode/functions",
    KeyActions.PASTE: "Paste from clipboard",
    KeyActions.HELP: "Print this help"
}

KEY_ACTIONS_SELECT_TILES = {
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
    ord('c'): KeyActions.COPY,
    ord('f'): KeyActions.RECT
}

KEY_ACTIONS_SELECT_TILES_DESCRIPTIONS = {
    KeyActions.MOVE_LEFT: "Move other corner left",
    KeyActions.MOVE_RIGHT: "Move other corner right",
    KeyActions.MOVE_UP: "Move other corner up",
    KeyActions.MOVE_DOWN: "Move other corner down",
    KeyActions.CANCEL: "Leave seleciton mode",
    KeyActions.ZOOMED_COLOR: "Toggle zoomed view color",
    KeyActions.COPY: "Copy tiles to clipboard",
    KeyActions.RECT: "Fill tiles with selected color"
}

KEY_ACTIONS_SELECT_PIXELS = {
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
    ord('o'): KeyActions.OPERATION,
    ord('m'): KeyActions.TOOL_MODE,
    ord('r'): KeyActions.RECT,
    ord('c'): KeyActions.CIRCLE
}

KEY_ACTIONS_SELECT_PIXELS_DESCRIPTIONS = {
    KeyActions.MOVE_LEFT: "Move other corner left",
    KeyActions.MOVE_RIGHT: "Move other corner right",
    KeyActions.MOVE_UP: "Move other corner up",
    KeyActions.MOVE_DOWN: "Move other corner down",
    KeyActions.CANCEL: "Leave seleciton mode",
    KeyActions.ZOOMED_COLOR: "Toggle zoomed view color",
    KeyActions.OPERATION: "Cycle pixel operations (Set, Clear, Invert)",
    KeyActions.TOOL_MODE: "Cycle cool modes (Outline, Fill)",
    KeyActions.RECT: "Draw a rectangle fit to the selection box",
    KeyActions.CIRCLE: "Draw a circle fit to the selection box"
}

KEY_ACTIONS_PROMPT = {
    t.KEY_ENTER: KeyActions.CONFIRM,
    t.KEY_ESCAPE: KeyActions.CANCEL,
    t.KEY_BACKSPACE: KeyActions.BACKSPACE
}

KEY_ACTIONS_PROMPT_DESCRIPTIONS = {
    KeyActions.CONFIRM: "Confirm entered text",
    KeyActions.CANCEL: "Cancel entering text if applicable",
    KeyActions.BACKSPACE: "Delete last character"
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

KEY_ACTIONS_COLOR_RGB_DESCRIPTIONS = {
    KeyActions.CONFIRM: "Confirm Selection",
    KeyActions.CANCEL: "Cancel Selection and keep original color",
    KeyActions.INC_RED: "Increase Red 1",
    KeyActions.INC_GREEN: "Increase Green 1",
    KeyActions.INC_BLUE: "Increase Blue 1",
    KeyActions.DEC_RED: "Decrease Red 1",
    KeyActions.DEC_GREEN: "Decrease Green 1",
    KeyActions.DEC_BLUE: "Descrease Blue 1",
    KeyActions.INC_FAST_RED: f"Increase Red {FAST_COLOR_VALUE}",
    KeyActions.INC_FAST_GREEN: f"Increase Green {FAST_COLOR_VALUE}",
    KeyActions.INC_FAST_BLUE: f"Increase Blue {FAST_COLOR_VALUE}",
    KeyActions.DEC_FAST_RED: f"Decrease Red {FAST_COLOR_VALUE}",
    KeyActions.DEC_FAST_GREEN: f"Decrease Green {FAST_COLOR_VALUE}",
    KeyActions.DEC_FAST_BLUE: f"Decrease Blue {FAST_COLOR_VALUE}",
    KeyActions.TRANSPARENT: "Select transparent color if applicable"
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

KEY_ACTIONS_COLOR_DESCRIPTIONS = {
    KeyActions.MOVE_LEFT: "Move other corner left",
    KeyActions.MOVE_RIGHT: "Move other corner right",
    KeyActions.MOVE_UP: "Move other corner up",
    KeyActions.MOVE_DOWN: "Move other corner down",
    KeyActions.CONFIRM: "Confirm Selection",
    KeyActions.CANCEL: "Leave seleciton mode",
    KeyActions.TRANSPARENT: "Select transparent color if applicable"
}

HELPS = {
    "Main": (KEY_ACTIONS, KEY_ACTIONS_DESCRIPTIONS, None),
    "Tiles Selection Mode": (KEY_ACTIONS_SELECT_TILES, KEY_ACTIONS_SELECT_TILES_DESCRIPTIONS, None),
    "Pixels Selection Mode": (KEY_ACTIONS_SELECT_PIXELS, KEY_ACTIONS_SELECT_PIXELS_DESCRIPTIONS, None),
    "Text Prompt": (KEY_ACTIONS_PROMPT, KEY_ACTIONS_PROMPT_DESCRIPTIONS, None),
    "RGB Color Selection": (KEY_ACTIONS_COLOR_RGB, KEY_ACTIONS_COLOR_RGB_DESCRIPTIONS, None),
    "Palette Color Selection": (KEY_ACTIONS_COLOR, KEY_ACTIONS_COLOR_DESCRIPTIONS,
                                "When selecting a color, transparency is only available for background colors.")
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
    NONE = auto()
    C16 = auto()
    C256 = auto()
    DIRECT = auto()

class FillMode(Enum):
    SET = auto()
    CLEAR = auto()
    INVERT = auto()

FILL_MODE_CYCLE = {
    FillMode.SET: FillMode.CLEAR,
    FillMode.CLEAR: FillMode.INVERT,
    FillMode.INVERT: FillMode.SET
}

class ToolMode(Enum):
    OUTLINE = auto()
    FILL = auto()

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
            self.colordata_bg_r = copy.copy(colordata_bg_r)
            if color_mode == ColorMode.DIRECT:
                self.colordata_fg_g = copy.copy(colordata_fg_g)
                self.colordata_fg_b = copy.copy(colordata_fg_b)
                self.colordata_bg_g = copy.copy(colordata_bg_g)
                self.colordata_bg_b = copy.copy(colordata_bg_b)
        else:
            # build up the arrays of data to store locally
            self.data = array('i', itertools.repeat(0, (w * 2) * (h * 4)))
            self.colordata_fg_r = array('i', itertools.repeat(0, w * h))
            self.colordata_bg_r = array('i', itertools.repeat(0, w * h))
            if color_mode == ColorMode.DIRECT:
                self.colordata_fg_g = array('i', itertools.repeat(0, w * h))
                self.colordata_fg_b = array('i', itertools.repeat(0, w * h))
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
                self.colordata_bg_r[i * self.w:i * self.w + self.w] = \
                    colordata_bg_r[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]
                if color_mode == ColorMode.DIRECT:
                    self.colordata_fg_g[i * self.w:i * self.w + self.w] = \
                        colordata_fg_g[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]
                    self.colordata_fg_b[i * self.w:i * self.w + self.w] = \
                        colordata_fg_b[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w]
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
            return w, h, self.data, self.color_mode, \
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
                colordata_bg_r[(y + i) * dw + x:(y + i) * dw + x + w] = \
                    self.colordata_bg_r[i * self.w:i * self.w + w]
                if self.color_mode == ColorMode.DIRECT:
                    colordata_fg_g[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_fg_g[i * self.w:i * self.w + w]
                    colordata_fg_b[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_fg_b[i * self.w:i * self.w + w]
                    colordata_bg_g[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_bg_g[i * self.w:i * self.w + w]
                    colordata_bg_b[(y + i) * dw + x:(y + i) * dw + x + w] = \
                        self.colordata_bg_b[i * self.w:i * self.w + w]

        return None, None, None, None, None, None, None, None, None, None

COLOR_PREVIEW = "𜶉𜶉"
CURSOR = "🯧🯦"
BLOCK = "██"

TILE_CURSOR = 20
TILE_INVERT = 40
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
TILE_TUBE_HORIZONTAL = 13
TILE_TUBE_VERTICAL = 14
TILE_TUBE_LEFT = 15
TILE_TUBE_RIGHT = 16
TILE_TUBE_TOP = 17
TILE_TUBE_BOTTOM = 18
TILE_TUBE_1 = 19
TILES = ("  ", "𜵊🮂", "▌ ", "𜷀▂", "🮂𜶘", " ▐", "▂𜷕", "🮂🮂", "▂▂", "𜺨 ", "𜺣 ", " 𜺫", " 𜺠", "𜶮𜶮", "▌▐", "𜷂𜶮", "𜶮𜷖", "𜵊𜶘", "𜷀𜷕", "𜷂𜷖",
         "🯧🯦", "𜵰𜴏", "𜵮🯦", "𜷤𜶿", "𜴢𜶫", "🯧𜶪", "𜷓𜷥", "𜴢𜴏", "𜷓𜶿", "𜴠🯦", "𜵙🯦", "🯧𜴎", "🯧𜶄", "𜷖𜷂", "𜵮𜶪", "█𜷂", "𜷖█", "𜵰𜶫", "𜷤𜷥", "██", 
         "██", "𜶖▆", "▐█", "𜴡🮅", "▆𜵈", "█▌", "🮅𜴍", "▆▆", "🮅🮅", "𜷥█", "𜶫█", "█𜷤", "█𜵰", "𜴳𜴳", "▐▌", "🯧𜴳", "𜴳🯦", "𜶖𜵈", "𜴡𜴍", "🯧🯦",
         "𜷂𜷖", "𜺠𜷓", "𜵲𜷖", "𜺫𜴢", "𜶿𜺣", "𜷂𜴶", "𜴏𜺨", "𜶿𜷓", "𜴏𜴢", "𜷁𜷖", "𜶇𜷖", "𜷂𜷔", "𜷂𜵜", "🯦🯧", "𜵲𜴶", " 🯧", "🯦 ", "𜺠𜺣", "𜺫𜺨", "  ")

def display_zoomed_matrix(t : blessed.Terminal,
                          x : int, y : int, pad : int,
                          dx : int, dy : int,
                          dw : int, dh : int,
                          selecting : bool,
                          select_x : int, select_y : int,
                          colors : dict[bool],
                          grid : bool, use_color : bool,
                          select_pixels : bool,
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

        lastcolor_r : int = -1
        lastcolor_g : int = -1
        lastcolor_b : int = -1
        lastcolor_fg_r : int = -1
        lastcolor_fg_g : int = -1
        lastcolor_fg_b : int = -1
        # only need R to determine transparency
        lastcolor_bg_r : int = -1

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
                    if use_color:
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

                    if selecting:
                        sx1 = min(dx + pad, select_x)
                        sy1 = min(dy + pad, select_y)
                        sx2 = max(dx + pad, select_x)
                        sy2 = max(dy + pad, select_y)
                        if not select_pixels:
                            sx1 = sx1 // 2 * 2
                            sy1 = sy1 // 4 * 4
                            sx2 = sx2 // 2 * 2 + 1
                            sy2 = sy2 // 4 * 4 + 3

                        sx1 = max(0, sx1)
                        sy1 = max(0, sy1)
                        sx2 = min(dw - 1, sx2)
                        sy2 = min(dh - 1, sy2)

                        if px == sx1:
                            if sx1 == sx2:
                                if py == sy1:
                                    if sy1 == sy2:
                                        tile += TILE_TUBE_1
                                    else:
                                        tile += TILE_TUBE_TOP
                                elif py > sy1 and py < sy2:
                                    tile += TILE_TUBE_VERTICAL
                                elif py == sy2:
                                    tile += TILE_TUBE_BOTTOM
                            elif sy1 == sy2 and py == sy1:
                                tile += TILE_TUBE_LEFT
                            else:
                                if py == sy1:
                                    if sy1 == sy2:
                                        tile += TILE_TUBE_LEFT
                                    else:
                                        tile += TILE_TOPLEFT
                                elif py > sy1 and py < sy2:
                                    tile += TILE_LEFT
                                elif py == sy2:
                                    tile += TILE_BOTTOMLEFT
                        elif px > sx1 and px < sx2:
                            if py == sy1:
                                if sy1 == sy2:
                                    tile += TILE_TUBE_HORIZONTAL
                                else:
                                    tile += TILE_TOP
                            elif py == sy2:
                                tile += TILE_BOTTOM
                        elif px == sx2:
                            if py == sy1:
                                if sy1 == sy2:
                                    tile += TILE_TUBE_RIGHT
                                else:
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

def make_cell_inverted(data : array, dx : int, dy : int, dw : int,
                       cross_x : int, cross_y : int,
                       left : bool, right : bool, up : bool, down : bool,
                       max_y : int = 4, max_x : int = 2):
    # slower function for drawing boxes/lines
    # always invert cross point
    # left, right, up, down - extend lines from cross point outward
    # max_y - clip vertical line at Y, extend horizontal lines from this point
    # max_x - fill in any space on the right side between the extended lines
    cell : int = 0
    # offset LSB to RSB goes top left -> bottom left, top right -> bottom right
    if bool(data[(dy * dw) + dx]) ^ \
       ((cross_x == 0 and (cross_y == 0 or up)) or
        (cross_x == 1 and left and cross_y == 0)):
        cell += 1
    if bool(data[((dy + 1) * dw) + dx]) ^ \
       ((cross_x == 0 and (cross_y == 1 or
                           (up and cross_y > 1) or
                           (down and cross_y < 1 and max_y >= 1) or
                           (left and cross_y < 1 and max_y == 1))) or
        (cross_x == 1 and left and (cross_y == 1 or max_y == 1 or
                                    (cross_y < 1 and max_y > 1 and max_y < 4 and max_x != 1)))):
        cell += 2
    if bool(data[((dy + 2) * dw) + dx]) ^ \
       ((cross_x == 0 and (cross_y == 2 or
                           (up and cross_y > 2) or
                           (down and cross_y < 2 and max_y >= 2) or
                           (left and cross_y < 2 and max_y == 2))) or
        (cross_x == 1 and left and (cross_y == 2 or max_y == 2 or
                                    (cross_y < 2 and max_y > 2 and max_y < 4 and max_x != 1)))):
        cell += 4
    if bool(data[((dy + 3) * dw) + dx]) ^ \
       ((cross_x == 0 and (cross_y == 3 or
                           (down and cross_y < 3 and max_y >= 3) or
                           (left and cross_y < 3 and max_y == 3))) or
        (cross_x == 1 and left and (cross_y == 3 or max_y == 3))):
        cell += 8
    if bool(data[(dy * dw) + (dx + 1)]) ^ \
       ((cross_x == 1 and (cross_y == 0 or
                           (up and cross_y > 0))) or
        (cross_x == 0 and ((right and cross_y == 0) or
                           (up and max_y < 4 and max_y >= 0)))):
        cell += 16
    if bool(data[((dy + 1) * dw) + (dx + 1)]) ^ \
       ((cross_x == 1 and (cross_y == 1 or
                           (up and cross_y > 1) or
                           (down and cross_y < 1 and max_y >= 1))) or
        (cross_x == 0 and ((right and (cross_y == 1 or max_y == 1 or
                                       (max_x == 1 and cross_y < 1 and max_y > 1 and max_y < 4))) or
                           (up and max_y < 4 and max_y >= 1)))):
        cell += 32
    if bool(data[((dy + 2) * dw) + (dx + 1)]) ^ \
       ((cross_x == 1 and (cross_y == 2 or
                           (up and cross_y > 2) or
                           (down and cross_y < 2 and max_y >= 2))) or
        (cross_x == 0 and ((right and (cross_y == 2 or max_y == 2 or
                                       (max_x == 1 and cross_y < 2 and max_y > 1 and max_y < 4))) or
                           (up and max_y < 4 and max_y >= 2)))):
        cell += 64
    if bool(data[((dy + 3) * dw) + (dx + 1)]) ^ \
       ((cross_x == 1 and (cross_y == 3 or
                           (down and cross_y < 3 and max_y >= 3))) or
        (cross_x == 0 and right and (cross_y == 3 or max_y == 3))):
        cell += 128

    return cell
 
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

    # start at requested data start and clamp to wanted end or the actual data array dimensions
    for iy in range(cy, min(cy + h, len(colordata_fg_r) // cw)):
        # subtract range start here.  it's simpler than adding it everywhere else
        print(t.move_xy(x + cx, y + iy), end='')
        for ix in range(cx, min(cx + w, cw)):
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
                color_fg_r = colordata_fg_r[iy * cw + ix]
                color_bg_r = colordata_bg_r[iy * cw + ix]
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

            cell = make_cell(data, ix * 2, iy * 4, dw)
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

def pixels_to_occupied_wh(x : int, y : int, w : int, h : int):
    # convert from pixels to character cells which the dimensions occupy
    cw = ((x + w) // 2) - (x // 2) + 1
    if (x + w) % 2 == 0:
        cw -= 1
    ch = ((y + h) // 4) - (y // 4) + 1
    if (y + h) % 4 == 0:
        ch -= 1

    return cw, ch

def print_next_color(t, cbx : int, cby : int, cw : int, color_mode : ColorMode,
                     colordata_fg_r : array,
                     colordata_fg_g : array,
                     colordata_fg_b : array,
                     colordata_bg_r : array,
                     colordata_bg_g : array,
                     colordata_bg_b : array,
                     lastcolor_fg_r : array,
                     lastcolor_fg_g : array,
                     lastcolor_fg_b : array,
                     lastcolor_bg_r : array,
                     lastcolor_bg_g : array,
                     lastcolor_bg_b : array) -> (int, int, int, int, int, int):
    normaled : bool = False
    if lastcolor_fg_r is None:
        lastcolor_fg_r = colordata_fg_r[cby * cw + cbx]
        lastcolor_fg_g = colordata_fg_g[cby * cw + cbx]
        lastcolor_fg_b = colordata_fg_b[cby * cw + cbx]
        lastcolor_bg_r = colordata_bg_r[cby * cw + cbx]
        lastcolor_bg_g = colordata_bg_g[cby * cw + cbx]
        lastcolor_bg_b = colordata_bg_b[cby * cw + cbx]
        if lastcolor_bg_r < 0:
            print(t.normal, end='')
        else:
            if color_mode == ColorMode.DIRECT:
                print(t.on_color_rgb(lastcolor_bg_r, lastcolor_bg_b, lastcolor_bg_g), end='')
            else:
                print(t.on_color(lastcolor_bg_r), end='')
        if color_mode == ColorMode.DIRECT:
            print(t.color_rgb(lastcolor_fg_r, lastcolor_fg_b, lastcolor_fg_g), end='')
        else:
            print(t.color(lastcolor_fg_r), end='')
    else:
        color_fg_r = colordata_fg_r[cby * cw + cbx]
        color_fg_g = colordata_fg_g[cby * cw + cbx]
        color_fg_b = colordata_fg_b[cby * cw + cbx]
        color_bg_r = colordata_bg_r[cby * cw + cbx]
        color_bg_g = colordata_bg_g[cby * cw + cbx]
        color_bg_b = colordata_bg_b[cby * cw + cbx]
        if color_bg_r != lastcolor_bg_r or \
           color_bg_g != lastcolor_bg_g or \
           color_bg_b != lastcolor_bg_b:
            if color_bg_r < 0:
                print(t.normal, end='')
                normaled = True
            else:
                if color_mode == ColorMode.DIRECT:
                    print(t.on_color_rgb(color_bg_r, color_bg_b, color_bg_g), end='')
                else:
                    print(t.on_color(color_bg_r), end='')
            lastcolor_bg_r = color_bg_r
            lastcolor_bg_g = color_bg_g
            lastcolor_bg_b = color_bg_b
        if color_fg_r != lastcolor_fg_r or \
           color_fg_g != lastcolor_fg_g or \
           color_fg_b != lastcolor_fg_b or \
           normaled:
            if color_mode == ColorMode.DIRECT:
                print(t.color_rgb(color_fg_r, color_fg_b, color_fg_g), end='')
            else:
                print(t.color(color_fg_r), end='')
            lastcolor_fg_r = color_fg_r
            lastcolor_fg_g = color_fg_g
            lastcolor_fg_b = color_fg_b

    return lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
           lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b

def update_matrix_rect(t : blessed.Terminal,
                       color_mode : ColorMode,
                       x : int, y : int,
                       w : int, h : int,
                       dx : int, dy : int,
                       dw : int, data : array,
                       colordata_fg_r : array,
                       colordata_fg_g : array,
                       colordata_fg_b : array,
                       colordata_bg_r : array,
                       colordata_bg_g : array,
                       colordata_bg_b : array,
                       bx : int, by : int,
                       bw : int, bh : int,
                       draw_box : bool):
    # get everything in terms of character cells
    dx : int = dx // 2 * 2
    dy : int = dy // 4 * 4
    cx : int = dx // 2
    cy : int = dy // 4
    cw : int = dw // 2
    dh : int = len(data) // dw
    ch : int = dh // 4

    sx1 : int = bx % 2
    sy1 : int = by % 4
    sx2 : int = (bx + bw - 1) % 2
    sy2 : int = (by + bh - 1) % 4

    # get the occupied bounds of the box in character cells
    cbx : int = bx // 2
    cby : int = by // 4
    cbw, cbh = pixels_to_occupied_wh(bx, by, bw, bh)
    # clamp to data boundaries
    if cbx < 0:
        cbx = 0
        sx1 = 0
    if cby < 0:
        cby = 0
        sy1 = 0
    if cbx + cbw - 1 >= cw:
        cbw = cw - cbx
        sx2 = 1
    if cby + cbh - 1 >= ch:
        cbh = ch - cby
        sy2 = 3

    lastcolor_fg_r : int | None = None
    lastcolor_fg_g : int | None = None
    lastcolor_fg_b : int | None = None
    lastcolor_bg_r : int | None = None
    lastcolor_bg_g : int | None = None
    lastcolor_bg_b : int | None = None

    cell : int = 0
    if cbx < cx + w and cbx + cbw - 1 >= cx:
        # if the box isn't totally off a side
        if cby >= cy and cby < cy + h:
            # if the top line resides in the view
            # top left corner
            if cbx >= cx:
                # if top left corner resides in visible area
                # move to position
                print(t.move_xy(x + cbx - cx, y + cby - cy), end='')
                lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                    lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                    print_next_color(t, cbx, cby, cw, color_mode,
                                     colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                     colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                     lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                     lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                if draw_box:
                    if cbh == 1:
                        if cbw == 1:
                            if bw == 1:
                                cell = make_cell_inverted(data, cbx * 2, cby * 4, dw,
                                                          sx1, sy1, False, False, False, True,
                                                          sy2, sx2)
                            else:
                                cell = make_cell_inverted(data, cbx * 2, cby * 4, dw,
                                                          sx1, sy1, False, True, False, True,
                                                          sy2, sx2)
                        else:
                            cell = make_cell_inverted(data, cbx * 2, cby * 4, dw,
                                                      sx1, sy1, False, True, False, True,
                                                      sy2)
                    else:
                        if cbw == 1:
                            if bw == 1:
                                cell = make_cell_inverted(data, cbx * 2, cby * 4, dw,
                                                          sx1, sy1, False, False, False, True)
                            else:
                                cell = make_cell_inverted(data, cbx * 2, cby * 4, dw,
                                                          sx1, sy1, False, True, False, True,
                                                          3, 1)
                        else:
                            cell = make_cell_inverted(data, cbx * 2, cby * 4, dw,
                                                  sx1, sy1, False, True, False, True)
                else:
                    cell = make_cell(data, cbx * 2, cby * 4, dw)
                print(CHARS4[cell], end='')
            else:
                # otherwise, move to far left
                print(t.move_xy(x, y + cby - cy), end='')
            # top
            if cbw > 2 and \
               ((cbx + 1 >= cx and cbx + 1 < cx + w) or \
                (cbx + cbw - 1 < cx and cbx + cbw - 1 < cx + w)):
                # if any of the top line resides within view
                # and the selection is wide enough
                # draw clamped within view
                if draw_box:
                    if cbh == 1:
                        for i in range(max(cx, cbx + 1), min(cx + w, cbx + cbw - 1)):
                            lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                                lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                                print_next_color(t, i, cby, cw, color_mode,
                                                 colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                                 colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                                 lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                                 lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                            cell = make_cell_inverted(data, i * 2, cby * 4, dw,
                                                      0, sy1, True, True, False, False,
                                                      sy2)
                            print(CHARS4[cell], end='')
                    else:
                        for i in range(max(cx, cbx + 1), min(cx + w, cbx + cbw - 1)):
                            lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                                lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                                print_next_color(t, i, cby, cw, color_mode,
                                                 colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                                 colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                                 lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                                 lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                            cell = make_cell_inverted(data, i * 2, cby * 4, dw,
                                                      0, sy1, True, True, False, False)
                            print(CHARS4[cell], end='')
                else:
                    for i in range(max(cx, cbx + 1), min(cx + w, cbx + cbw - 1)):
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, i, cby, cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell(data, i * 2, cby * 4, dw)
                        print(CHARS4[cell], end='')
            if cbw > 1 and (cbx + cbw - 1 >= cx and cbx + cbw - 1 < cx + w):
                # if top right corner resides in visible area
                # and the selection is wide enough
                # top right corner
                lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                    lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                    print_next_color(t, (cbx + cbw - 1), cby, cw, color_mode,
                                     colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                     colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                     lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                     lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                if draw_box:
                    if cbh == 1:
                        cell = make_cell_inverted(data, (cbx + cbw - 1) * 2, cby * 4, dw,
                                                  sx2, sy1, True, False, False, True,
                                                  sy2, sx2)
                    else:
                        cell = make_cell_inverted(data, (cbx + cbw - 1) * 2, cby * 4, dw,
                                                  sx2, sy1, True, False, False, True)
                else:
                    cell = make_cell(data, (cbx + cbw - 1) * 2, cby * 4, dw)
                print(CHARS4[cell], end='')

        if cbh > 1 and (cby + cbh - 1 >= cy and cby + cbh - 1 < cy + h):
            # if the bottom line resides in the view
            # bottom left corner
            if cbx >= cx:
                # if bottom left corner resides in visible area
                # move to position
                print(t.move_xy(x + cbx - cx, y + cby + cbh - 1 - cy), end='')
                lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                    lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                    print_next_color(t, cbx, (cby + cbh - 1), cw, color_mode,
                                     colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                     colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                     lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                     lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                if draw_box:
                    if cbw == 1:
                        if bw == 1:
                            cell = make_cell_inverted(data, cbx * 2, (cby + cbh - 1) * 4, dw,
                                                      sx1, sy2, False, False, True, False,
                                                      4, sx2)
                        else:
                            cell = make_cell_inverted(data, cbx * 2, (cby + cbh - 1) * 4, dw,
                                                      sx1, sy2, True, True, True, False,
                                                      sy2, sx2)
                    else:
                        cell = make_cell_inverted(data, cbx * 2, (cby + cbh - 1) * 4, dw,
                                                  sx1, sy2, False, True, True, False)
                else:
                    cell = make_cell(data, cbx * 2, (cby + cbh - 1) * 4, dw)
                print(CHARS4[cell], end='')
            else:
                # otherwise, move to far left
                print(t.move_xy(x, y + cby - cy), end='')
            # bottom
            if cbw > 2 and \
               ((cbx + 1 >= cx and cbx + 1 < cx + w) or \
                (cbx + cbw - 1 < cx and cbx + cbw - 1 < cx + w)):
                # if any of the top line resides within view
                # and the selection is wide enough
                # draw clamped within view
                if draw_box:
                    for i in range(max(cx, cbx + 1), min(cx + w, cbx + cbw - 1)):
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, i, (cby + cbh - 1), cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell_inverted(data, i * 2, (cby + cbh - 1) * 4, dw,
                                                  0, sy2, True, True, False, False)
                        print(CHARS4[cell], end='')
                else:
                    for i in range(max(cx, cbx + 1), min(cx + w, cbx + cbw - 1)):
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, i, (cby + cbh - 1), cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell(data, i * 2, (cby + cbh - 1) * 4, dw)
                        print(CHARS4[cell], end='')
            if cbw > 1 and (cbx + cbw - 1 >= cx and cbx + cbw - 1 < cx + w):
                # if top right corner resides in visible area
                # and the selection is wide enough
                # bottom right corner
                lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                    lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                    print_next_color(t, (cbx + cbw - 1), (cby + cbh - 1), cw, color_mode,
                                     colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                     colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                     lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                     lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                if draw_box:
                    cell = make_cell_inverted(data, (cbx + cbw - 1) * 2, (cby + cbh - 1) * 4, dw,
                                              sx2, sy2, True, False, True, False)
                else:
                    cell = make_cell(data, (cbx + cbw - 1) * 2, (cby + cbh - 1) * 4, dw)
                print(CHARS4[cell], end='')

    if cby + 1 < cy + h and cby + cbh - 1 > cy:
        # if the lines aren't totally off top or bottom
        if cbw == 1:
            if cbx >= cx and cbx < cx + w:
                if bw == 1:
                    for i in range(max(cy, cby + 1), min(cy + h, cby + cbh - 1)):
                        print(t.move_xy(x + cbx - cx, y + i), end='')
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, cbx, i, cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell_inverted(data, cbx * 2, i * 4, dw,
                                                  sx1, 0, False, False, True, True)
                        print(CHARS4[cell], end='')
                else:
                    for i in range(max(cy, cby + 1), min(cy + h, cby + cbh - 1)):
                        print(t.move_xy(x + cbx - cx, y + i), end='')
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, cbx, i, cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell_inverted(data, cbx * 2, i * 4, dw,
                                                  sx1, 0, True, True, True, True,
                                                  3, 1)
                        print(CHARS4[cell], end='')
        else:
            # left
            if cbx >= cx and cbx < cx + w:
                if draw_box:
                    for i in range(max(cy, cby + 1), min(cy + h, cby + cbh - 1)):
                        print(t.move_xy(x + cbx - cx, y + i), end='')
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, cbx, i, cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell_inverted(data, cbx * 2, i * 4, dw,
                                                  sx1, 0, False, False, True, True)
                        print(CHARS4[cell], end='')
                else:
                    for i in range(max(cy, cby + 1), min(cy + h, cby + cbh - 1)):
                        print(t.move_xy(x + cbx - cx, y + i), end='')
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, cbx, i, cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell(data, cbx * 2, i * 4, dw)
                        print(CHARS4[cell], end='')
            # right
            if cbx + cbh - 1 > cx and cbx + cbh - 1 < cx + w:
                if draw_box:
                    for i in range(max(cy, cby + 1), min(cy + h, cby + cbh - 1)):
                        print(t.move_xy(x + (cbx + cbw - 1) - cx, y + i), end='')
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, (cbx + cbw - 1), i, cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell_inverted(data, (cbx + cbw - 1) * 2, i * 4, dw,
                                                  sx2, 0, False, False, True, True)
                        print(CHARS4[cell], end='')
                else:
                    for i in range(max(cy, cby + 1), min(cy + h, cby + cbh - 1)):
                        print(t.move_xy(x + (cbx + cbw - 1) - cx, y + i), end='')
                        lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b, \
                            lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b = \
                            print_next_color(t, (cbx + cbw - 1), i, cw, color_mode,
                                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                             colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                             lastcolor_fg_r, lastcolor_fg_g, lastcolor_fg_b,
                                             lastcolor_bg_r, lastcolor_bg_g, lastcolor_bg_b)
                        cell = make_cell(data, (cbx + cbw - 1) * 2, i * 4, dw)
                        print(CHARS4[cell], end='')

def inkey_numeric(t : blessed.Terminal):
    global interrupted

    key = ""
    while len(key) == 0:
        key = t.inkey(0.5)
        if interrupted:
            return False, None

    try:
        return False, t._keymap[key]
    except KeyError:
        pass

    return True, ord(key)

def print_status(t : blessed.Terminal, text : str, row : int = 0):
    global interrupted

    if not interrupted:
        print(t.move_xy(0, row), end='')
        if row == 0:
            print(t.normal, end='')
            print(t.on_color(4), end='')
            print(t.color(11), end='')
        else:
            print(t.normal, end='')
            print(t.reverse, end='')
        print(t.ljust(text), end='')
 
def prompt(t : blessed.Terminal,
           text : str):
    global interrupted

    if interrupted:
        return None
    inp = array('w')

    print_status(t, text)
    # clear second line
    print_status(t, "", 1)
    print(t.move_xy(0, 1), end='')
    sys.stdout.flush()
    while True:
        is_text, key = inkey_numeric(t)
        if interrupted:
            return None

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
                case KeyActions.BACKSPACE:
                    if len(inp) > 0:
                        # not ideal, but fullscreen mode seems to have limitations?
                        inp = inp[:-1]
                        print(t.move_xy(0, 1), end='')
                        print_status(t, "", 1)
                        print(t.move_xy(0, 1), end='')
                        print(inp.tounicode(), end='')
        sys.stdout.flush()
    print(t.normal, end='')

    return inp.tounicode()

def prompt_yn(t : blessed.Terminal, text : str, default : bool = False) -> bool:
    if default:
        ans = prompt(t, f"{text} ([Y]/n)")
    else:
        ans = prompt(t, f"{text} (y/[N])")

    if ans is None or len(ans) == 0:
        # interruption will return default!
        return default

    if default:
       if ans[0].lower() == 'n':
           return False

       return True
    else:
       if ans[0].lower() == 'y':
           return True

    return False

def clear_screen(t : blessed.Terminal):
    print(t.normal, end='')
    print(t.clear, end='')

def select_color_rgb(t : blessed.Terminal,
                     r : int, g : int, b : int,
                     allow_transparent : bool):
    global interrupted

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
        if interrupted:
            # abort selection without change
            r = orig_r
            g = orig_g
            b = orig_b
            break

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
                r -= FAST_COLOR_VALUE
                r = max(0, r)
            case KeyActions.DEC_FAST_GREEN:
                g -= FAST_COLOR_VALUE
                g = max(0, g)
            case KeyActions.DEC_FAST_BLUE:
                b -= FAST_COLOR_VALUE
                b = max(0, b)
            case KeyActions.INC_FAST_RED:
                r += FAST_COLOR_VALUE
                r = min(255, r)
            case KeyActions.INC_FAST_GREEN:
                g += FAST_COLOR_VALUE
                g = min(255, g)
            case KeyActions.INC_FAST_BLUE:
                b += FAST_COLOR_VALUE
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
    global interrupted

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
        if interrupted:
            break

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
              color : bool,
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
            if color:
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
                if color:
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
            if color:
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
                    if color_mode is None:
                        if fg_r is None or bg_r is None:
                            # assume an image with no color codes
                            color_mode = ColorMode.NONE
                    if fg_g is None:
                        # make sure the arrays have sensible numerical values
                        if color_mode == ColorMode.NONE:
                            fg_r, fg_g, fg_b, bg_r, bg_g, bg_b = get_default_colors(color_mode)
                        else:
                            _, fg_g, fg_b, _, bg_g, bg_b = get_default_colors(color_mode)

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

    if color_mode == ColorMode.NONE:
        color_mode = ColorMode.C256
        max_color = fg_r

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
    cw, ch = pixels_to_occupied_wh(x, y, w, h)

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
        return 0, 0, 0, 0, dw, dh, data, color_mode, \
               colordata_fg_r, colordata_fg_g, colordata_fg_b, \
               colordata_bg_r, colordata_bg_g, colordata_bg_b

    # make redo
    if len(redos) >= UNDO_LEVELS:
        del redos[0]
    undo = undos.pop(-1)
    w, h = undo.get_dims()
    if undo.whole_buffer:
        redos.append(make_copy(0, 0, dw, dh, dw, data, color_mode,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b))
    else:
        # dimensions have been converted to character cells
        redos.append(make_copy(undo.x * 2, undo.y * 4, w * 2, h * 4,
                               dw, data, color_mode,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b))

    new_dw, new_dh, new_data, new_color_mode, \
        new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
        new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b = \
        undo.apply(dw // 2, data,
                   colordata_fg_r, colordata_fg_g, colordata_fg_b,
                   colordata_bg_r, colordata_bg_g, colordata_bg_b)
    if new_data is not None:
        # return the new one, convert dimensions in character cells to pixels
        return undo.x * 2, undo.y * 4, new_dw * 2, new_dw * 4, new_dw * 2, new_dh * 4, \
               new_data, new_color_mode, \
               new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
               new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b

    # return back the originals
    return undo.x * 2, undo.y * 4, w * 2, h * 4, \
           dw, dh, data, color_mode, \
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
        return 0, 0, 0, 0, dw, dh, data, color_mode, \
               colordata_fg_r, colordata_fg_g, colordata_fg_b, \
               colordata_bg_r, colordata_bg_g, colordata_bg_b

    # make undo
    if len(undos) >= UNDO_LEVELS:
        del undos[0]
    redo = redos.pop(-1)
    w, h = redo.get_dims()
    if redo.whole_buffer:
        undos.append(make_copy(0, 0, dw, dh, dw, data, color_mode,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b))
    else:
        # dimensions have been converted to character cells
        undos.append(make_copy(redo.x * 2, redo.y * 4, w * 2, h * 4,
                               dw, data, color_mode,
                               colordata_fg_r, colordata_fg_g, colordata_fg_b,
                               colordata_bg_r, colordata_bg_g, colordata_bg_b))

    new_dw, new_dh, new_data, new_color_mode, \
        new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
        new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b = \
        redo.apply(dw // 2, data,
                   colordata_fg_r, colordata_fg_g, colordata_fg_b,
                   colordata_bg_r, colordata_bg_g, colordata_bg_b)
    if new_data is not None:
        # return the new one, convert dimensions in character cells to pixels
        return redo.x * 2, redo.y * 4, new_dw * 2, new_dh * 4, new_dw * 2, new_dh * 4, \
               new_data, new_color_mode, \
               new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
               new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b

    # return back the originals
    return redo.x * 2, redo.y * 4, w * 2, h * 4, \
           dw, dh, data, color_mode, \
           colordata_fg_r, colordata_fg_g, colordata_fg_b, \
           colordata_bg_r, colordata_bg_g, colordata_bg_b

def get_max_color(colordata_fg : array,
                  colordata_bg : array):
    max_color : int = 0
    for f, b in zip(colordata_fg, colordata_bg):
        max_color = max(max_color, f)
        max_color = max(max_color, b)

    return max_color

def can_convert(color_mode : ColorMode,
                new_color_mode : ColorMode,
                colordata_fg : array,
                colordata_bg : array):
    # can't convert to or from DIRECT as this would be lossy and
    # quantization/dithering modes won't likely be implemented
    # can't convert 256 colors down to 16 if more than the base
    # 16 colors were used.
    if color_mode == ColorMode.DIRECT or \
       new_color_mode == ColorMode.DIRECT:
        return "Can't convert to or from DIRECT color mode."
    elif color_mode == ColorMode.C256 and \
         new_color_mode == ColorMode.C16 and \
         get_max_color(colordata_fg, colordata_bg) > 15:
        return "Colors above 15 were used."

    return None

def get_xywh(x1 : int, y1 : int,
             x2 : int, y2 : int,
             width : int, height : int,
             clamp : bool = True) -> (int, int, int, int):
    # get top left (1) and bottom right (2)
    sx1 : int = min(x1, x2)
    sy1 : int = min(y1, y2)
    sx2 : int = max(x1, x2)
    sy2 : int = max(y1, y2)

    if clamp:
        # clamp
        sx1 : int = max(0, sx1)
        sy1 : int = max(0, sy1)
        sx2 : int = min(width - 1, sx2)
        sy2 : int = min(height - 1, sy2)

    w : int = sx2 - sx1 + 1
    h : int = sy2 - sy1 + 1

    return sx1, sy1, w, h

def fill_rect(data : array,
              dw : int, dh : int,
              x : int, y : int,
              w : int, h : int,
              mode : FillMode):
    match mode:
        case FillMode.SET:
            for ty in range(max(0, y), min(dh, y + h)):
                for tx in range(max(0, x), min(dw, x + w)):
                    data[ty * dw + tx] = 1
        case FillMode.CLEAR:
            for ty in range(max(0, y), min(dh, y + h)):
                for tx in range(max(0, x), min(dw, x + w)):
                    data[ty * dw + tx] = 0
        case FillMode.INVERT:
            for ty in range(max(0, y), min(dh, y + h)):
                for tx in range(max(0, x), min(dw, x + w)):
                    data[ty * dw + tx] ^= 1

def draw_rect(data : array, dw : int,
              x : int, y : int,
              w : int, h : int,
              mode : FillMode):
    match mode:
        case FillMode.SET:
            for tx in range(max(0, x), min(dw, x + w)):
                data[y * dw + tx] = 1
                data[(y + h - 1) * dw + tx] = 1
            for ty in range(max(0, y + 1), min(dh, y + h - 1)):
                data[ty * dw + x] = 1
                data[ty * dw + (x + w - 1)] = 1
        case FillMode.CLEAR:
            for tx in range(max(0, x), min(dw, x + w)):
                data[y * dw + tx] = 0
                data[(y + h - 1) * dw + tx] = 0
            for ty in range(max(0, y + 1), min(dh, y + h - 1)):
                data[ty * dw + x] = 0
                data[ty * dw + (x + w - 1)] = 0
        case FillMode.INVERT:
            for tx in range(max(0, x), min(dw, x + w)):
                data[y * dw + tx] ^= 1
                data[(y + h - 1) * dw + tx] ^= 1
            for ty in range(max(0, y + 1), min(dh, y + h - 1)):
                data[ty * dw + x] ^= 1
                data[ty * dw + (x + w - 1)] ^= 1

def fill_circle(data : array,
                dw : int, dh : int,
                x : int, y : int,
                w : int, h : int,
                mode : FillMode):
    if x < dw and x + w >= 0:
        hw : float = (w / 2.0) - 0.5
        hh : float = (h / 2.0) - 0.5
        hx : float = x + (w / 2.0)
        hy : float = y + (h / 2.0)
        quarter : float = math.pi * 0.5
        points : int = w + h
        div : float = quarter / points
        largest_x : float = -1.0
        last_largest_x : float = -1.0
        last_y : int = 0
        bottom_offset : int = 0
        if h % 2 == 0:
            hy -= 0.5
            hh -= 0.5
            last_y = -1
            bottom_offset = 1

        if mode == FillMode.SET:
            if h % 2 == 1:
                if int(hy) >= 0 and int(hy) < dh:
                    for i in range(max(0, int(hx - hw)), min(dw, int(hx + hw + 1))):
                        data[int(hy) * dw + i] = 1

            for i in range(points + 1):
                px = math.cos(div * i) * hw
                py = math.sin(div * i) * hh
                largest_x = max(px, largest_x)
                ipy : int = int(hy + py) - 1 + bottom_offset
                if int(py) != last_y:
                    if largest_x >= 0:
                        # draw bottom
                        if ipy >= 0 and ipy < dh:
                            for j in range(max(0, int(hx - largest_x)), min(dw, int(hx + largest_x) + 1)):
                                data[(int(hy + py) - 1 + bottom_offset) * dw + j] = 1
                        # draw top
                        ipy = int(hy - py) + 1
                        if ipy >= 0 and ipy < dh:
                            for j in range(max(0, int(hx - largest_x)), min(dw, int(hx + largest_x) + 1)):
                                data[(int(hy - py) + 1) * dw + j] = 1
                    last_y = int(py)
                    last_largest_x = largest_x
                    largest_x = px
            # draw top and bottom lines
            if y + h - 1 >= 0 and y + h - 1 < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[(y + h - 1) * dw + i] = 1
            if y >= 0 and y < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[y * dw + i] = 1
        elif mode == FillMode.CLEAR:
            if h % 2 == 1:
                if int(hy) >= 0 and int(hy) < dh:
                    for i in range(max(0, int(hx - hw)), min(dw, int(hx + hw + 1))):
                        data[int(hy) * dw + i] = 0

            for i in range(points + 1):
                px = math.cos(div * i) * hw
                py = math.sin(div * i) * hh
                largest_x = max(px, largest_x)
                ipy : int = int(hy + py) - 1 + bottom_offset
                if int(py) != last_y:
                    if largest_x >= 0:
                        # draw bottom
                        if ipy >= 0 and ipy < dh:
                            for j in range(max(0, int(hx - largest_x)), min(dw, int(hx + largest_x) + 1)):
                                data[(int(hy + py) - 1 + bottom_offset) * dw + j] = 0
                        # draw top
                        ipy = int(hy - py) + 1
                        if ipy >= 0 and ipy < dh:
                            for j in range(max(0, int(hx - largest_x)), min(dw, int(hx + largest_x) + 1)):
                                data[(int(hy - py) + 1) * dw + j] = 0
                    last_y = int(py)
                    last_largest_x = largest_x
                    largest_x = px
            # draw top and bottom lines
            if y + h - 1 >= 0 and y + h - 1 < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[(y + h - 1) * dw + i] = 0
            if y >= 0 and y < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[y * dw + i] = 0
        else: # invert
            if h % 2 == 1:
                if int(hy) >= 0 and int(hy) < dh:
                    for i in range(max(0, int(hx - hw)), min(dw, int(hx + hw + 1))):
                        data[int(hy) * dw + i] ^= 1

            for i in range(points + 1):
                px = math.cos(div * i) * hw
                py = math.sin(div * i) * hh
                largest_x = max(px, largest_x)
                ipy : int = int(hy + py) - 1 + bottom_offset
                if int(py) != last_y:
                    if largest_x >= 0:
                        # draw bottom
                        if ipy >= 0 and ipy < dh:
                            for j in range(max(0, int(hx - largest_x)), min(dw, int(hx + largest_x) + 1)):
                                data[(int(hy + py) - 1 + bottom_offset) * dw + j] ^= 1
                        # draw top
                        ipy = int(hy - py) + 1
                        if ipy >= 0 and ipy < dh:
                            for j in range(max(0, int(hx - largest_x)), min(dw, int(hx + largest_x) + 1)):
                                data[(int(hy - py) + 1) * dw + j] ^= 1
                    last_y = int(py)
                    last_largest_x = largest_x
                    largest_x = px
            # draw top and bottom lines
            if y + h - 1 >= 0 and y + h - 1 < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[(y + h - 1) * dw + i] ^= 1
            if y >= 0 and y < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[y * dw + i] ^= 1

def draw_circle(data : array,
                dw : int, dh : int,
                x : int, y : int,
                w : int, h : int,
                mode : FillMode):
    if x < dw and x + w >= 0:
        hw : float = (w / 2.0) - 0.5
        hh : float = (h / 2.0) - 0.5
        hx : float = x + (w / 2.0)
        hy : float = y + (h / 2.0)
        quarter : float = math.pi * 0.5
        points : int = w + h
        div : float = quarter / points
        largest_x : float = -1.0
        last_largest_x : float = -1.0
        last_y : int = 0
        bottom_offset : int = 0
        if h % 2 == 0:
            hy -= 0.5
            hh -= 0.5
            last_y = -1
            bottom_offset = 1

        if mode == FillMode.SET:
            if h % 2 == 1:
                if int(hy) >= 0 and int(hy) < dh:
                    if int(hx - hw) >= 0:
                        data[int(hy) * dw + int(hx - hw)] = 1
                    if int(hx + hw) < dw:
                        data[int(hy) * dw + int(hx + hw)] = 1

            for i in range(points + 1):
                px = math.cos(div * i) * hw
                py = math.sin(div * i) * hh
                largest_x = max(px, largest_x)
                ipy : int = int(hy + py) - 1 + bottom_offset
                if int(py) != last_y:
                    if largest_x >= 0:
                        # draw bottom
                        if ipy >= 0 and ipy < dh:
                            # draw left side
                            ipx1 : int = int(hx - last_largest_x)
                            ipx2 : int = int(hx - largest_x)
                            if ipx2 > ipx1:
                                ipx1 += 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy + py) - 1 + bottom_offset) * dw + j] = 1
                            # draw right side
                            ipx1 = int(hx + largest_x)
                            ipx2 = int(hx + last_largest_x)
                            if ipx2 > ipx1:
                                ipx2 -= 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy + py) - 1 + bottom_offset) * dw + j] = 1
                        # draw top
                        ipy = int(hy - py) + 1
                        if ipy >= 0 and ipy < dh:
                            # draw left side
                            ipx1 : int = int(hx - last_largest_x)
                            ipx2 : int = int(hx - largest_x)
                            if ipx2 > ipx1:
                                ipx1 += 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy - py) + 1) * dw + j] = 1
                            # draw right side
                            ipx1 = int(hx + largest_x)
                            ipx2 = int(hx + last_largest_x)
                            if ipx2 > ipx1:
                                ipx2 -= 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy - py) + 1) * dw + j] = 1
                    last_y = int(py)
                    last_largest_x = largest_x
                    largest_x = px
            # draw top and bottom lines
            if y + h - 1 >= 0 and y + h - 1 < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[(y + h - 1) * dw + i] = 1
            if y >= 0 and y < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[y * dw + i] = 1
        elif mode == FillMode.CLEAR:
            if h % 2 == 1:
                if int(hy) >= 0 and int(hy) < dh:
                    if int(hx - hw) >= 0:
                        data[int(hy) * dw + int(hx - hw)] = 0
                    if int(hx + hw) < dw:
                        data[int(hy) * dw + int(hx + hw)] = 0

            for i in range(points + 1):
                px = math.cos(div * i) * hw
                py = math.sin(div * i) * hh
                largest_x = max(px, largest_x)
                ipy : int = int(hy + py) - 1 + bottom_offset
                if int(py) != last_y:
                    if largest_x >= 0:
                        # draw bottom
                        if ipy >= 0 and ipy < dh:
                            # draw left side
                            ipx1 : int = int(hx - last_largest_x)
                            ipx2 : int = int(hx - largest_x)
                            if ipx2 > ipx1:
                                ipx1 += 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy + py) - 1 + bottom_offset) * dw + j] = 0
                            # draw right side
                            ipx1 = int(hx + largest_x)
                            ipx2 = int(hx + last_largest_x)
                            if ipx2 > ipx1:
                                ipx2 -= 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy + py) - 1 + bottom_offset) * dw + j] = 0
                        # draw top
                        ipy = int(hy - py) + 1
                        if ipy >= 0 and ipy < dh:
                            # draw left side
                            ipx1 : int = int(hx - last_largest_x)
                            ipx2 : int = int(hx - largest_x)
                            if ipx2 > ipx1:
                                ipx1 += 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy - py) + 1) * dw + j] = 0
                            # draw right side
                            ipx1 = int(hx + largest_x)
                            ipx2 = int(hx + last_largest_x)
                            if ipx2 > ipx1:
                                ipx2 -= 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy - py) + 1) * dw + j] = 0
                    last_y = int(py)
                    last_largest_x = largest_x
                    largest_x = px
            # draw top and bottom lines
            if y + h - 1 >= 0 and y + h - 1 < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[(y + h - 1) * dw + i] = 0
            if y >= 0 and y < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[y * dw + i] = 0
        else: # invert
            if h % 2 == 1:
                if int(hy) >= 0 and int(hy) < dh:
                    if int(hx - hw) >= 0:
                        data[int(hy) * dw + int(hx - hw)] ^= 1
                    if int(hx + hw) < dw:
                        data[int(hy) * dw + int(hx + hw)] ^= 1

            for i in range(points + 1):
                px = math.cos(div * i) * hw
                py = math.sin(div * i) * hh
                largest_x = max(px, largest_x)
                ipy : int = int(hy + py) - 1 + bottom_offset
                if int(py) != last_y:
                    if largest_x >= 0:
                        # draw bottom
                        if ipy >= 0 and ipy < dh:
                            # draw left side
                            ipx1 : int = int(hx - last_largest_x)
                            ipx2 : int = int(hx - largest_x)
                            if ipx2 > ipx1:
                                ipx1 += 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy + py) - 1 + bottom_offset) * dw + j] ^= 1
                            # draw right side
                            ipx1 = int(hx + largest_x)
                            ipx2 = int(hx + last_largest_x)
                            if ipx2 > ipx1:
                                ipx2 -= 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy + py) - 1 + bottom_offset) * dw + j] ^= 1
                        # draw top
                        ipy = int(hy - py) + 1
                        if ipy >= 0 and ipy < dh:
                            # draw left side
                            ipx1 : int = int(hx - last_largest_x)
                            ipx2 : int = int(hx - largest_x)
                            if ipx2 > ipx1:
                                ipx1 += 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy - py) + 1) * dw + j] ^= 1
                            # draw right side
                            ipx1 = int(hx + largest_x)
                            ipx2 = int(hx + last_largest_x)
                            if ipx2 > ipx1:
                                ipx2 -= 1
                            if ipx2 >= 0 and ipx1 < dw:
                                for j in range(max(0, ipx1), min(dw, ipx2 + 1)):
                                    data[(int(hy - py) + 1) * dw + j] ^= 1
                    last_y = int(py)
                    last_largest_x = largest_x
                    largest_x = px
            # draw top and bottom lines
            if y + h - 1 >= 0 and y + h - 1 < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[(y + h - 1) * dw + i] ^= 1
            if y >= 0 and y < dh:
                for i in range(max(0, int(hx - last_largest_x + 1)), min(dw, int(hx + last_largest_x))):
                    data[y * dw + i] ^= 1

def keycode_to_name(key):
    if key == ord(' '):
        return "SPACE"
    elif key in t._keycodes:
        return t._keycodes[key][4:]

    key = chr(key)
    if key.isupper():
        return f"Shift+{key}"

    return key.upper()

def print_help(t):
    for h in HELPS.keys():
        print(h)
        print(f"{'':-<{len(h)}}")

        h = HELPS[h]
        for key in h[0].keys():
            action = h[0][key]
            keys = []
            for key2 in h[0].keys():
                if h[0][key2] == action:
                    if len(keys) == 0 and key2 != key:
                        # detect if key has already been done
                        break
                    keys.append(key2)
            if len(keys) == 0:
                continue
            for key in keys:
                if key == keys[-1]:
                    print(f"{keycode_to_name(key)}: ", end='')
                else:
                    print(f"{keycode_to_name(key)}, ", end='')
            print(h[1][action])
        print()
        if h[2] is not None:
            print(h[2])
            print()

    print("Press any key to return . . .")
    with t.cbreak():
        _ = t.inkey()

def handler_winch(signum, frame):
    global need_winch
    global interrupted

    interrupted = True
    need_winch = True
    if callable(orig_winch):
        orig_winch(signum, frame)

def handler_cont(signum, frame):
    global need_cont
    global interrupted

    interrupted = True
    need_cont = True
    if callable(orig_cont):
        orig_cont(signum, frame)

def main():
    global need_winch
    global need_cont
    global orig_winch
    global orig_cont
    global interrupted

    width : int = DEFAULT_WIDTH
    height : int = DEFAULT_HEIGHT
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
    refresh_matrix : None | tuple[int] = None
    undos : list[None | DataRect] = []
    redos : list[None | DataRect] = []
    clipboard : None | DataRect = None
    selecting : bool = False
    select_x : int = -1
    select_y : int = -1
    select_pixels : bool = False
    cancel : bool = False
    last_x : int = -1
    last_y : int = -1
    tool_operation : FillMode = FillMode.SET
    tool_mode : ToolMode = ToolMode.OUTLINE
    running : bool = True
    need_help : bool = False
    first : bool = True

    if t.number_of_colors == 256:
        max_color_mode = ColorMode.C256
    elif t.number_of_colors < 256:
        max_color_mode = ColorMode.C16

    if len(sys.argv) > 1:
        width, height, color_mode, data, \
            colordata_fg_r, colordata_fg_g, colordata_fg_b, \
            colordata_bg_r, colordata_bg_g, colordata_bg_b = \
            load_file(t, max_color_mode, sys.argv[1])
    else:
        color_mode = max_color_mode

        data = array('i', itertools.repeat(0, width * height))
        if DEFAULT_FILL:
            # fill with some pattern to show it's working
            for i in range(0, width * height, 3):
                data[i] = 1

        colordata_fg_r, colordata_fg_g, colordata_fg_b, \
            colordata_bg_r, colordata_bg_g, colordata_bg_b = \
            new_color_data(color_mode, width, height)

    fg_r, fg_g, fg_b, bg_r, bg_g, bg_b = get_default_colors(color_mode)

    color_str = get_color_str(t, color_mode, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b)

    #global logfile
    #logfile = open("log.txt", 'w')

    orig_winch = signal.getsignal(signal.SIGWINCH)
    orig_cont = signal.getsignal(signal.SIGCONT)
    signal.signal(signal.SIGWINCH, handler_winch)
    signal.signal(signal.SIGCONT, handler_cont)

    while running:
        refresh_matrix = (0, 0, width, height)

        with t.cbreak(), t.fullscreen(), t.hidden_cursor():
            while True:
                if refresh_matrix is not None:
                    print(t.normal, end='')
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

                    cw, ch = pixels_to_occupied_wh(refresh_matrix[0], refresh_matrix[1], refresh_matrix[2], refresh_matrix[3])
                    cx = refresh_matrix[0] // 2
                    cy = refresh_matrix[1] // 4
                    display_matrix(t, color_mode, PREVIEW_X, 2, cw, ch, cx, cy,
                                   width, data,
                                   colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                   colordata_bg_r, colordata_bg_g, colordata_bg_b)
                    if first:
                        first = False
                        print_status(t, "Ready. (Shift+H for Help)")
                    else:
                        print_status(t, "Ready.")
                    refresh_matrix = None

                if selecting or cancel:
                    # light redraw after each keypress in select mode
                    bx, by, bw, bh = get_xywh(last_x, last_y,
                                              select_x, select_y,
                                              width, height)
                    if not select_pixels:
                        bw, bh = pixels_to_occupied_wh(bx, by, bw, bh)
                        bx = bx // 2 * 2
                        by = by // 4 * 4
                        bw = bw * 2
                        bh = bh * 4
                    update_matrix_rect(t, color_mode, PREVIEW_X, 2, width // 2, height // 4, 0, 0,
                                       width, data, colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                       colordata_bg_r, colordata_bg_g, colordata_bg_b, bx, by, bw, bh, False)

                    if not cancel:
                        bx, by, bw, bh = get_xywh(x, y,
                                                  select_x, select_y,
                                                  width, height)
                        if not select_pixels:
                            bw, bh = pixels_to_occupied_wh(bx, by, bw, bh)
                            bx = bx // 2 * 2
                            by = by // 4 * 4
                            bw = bw * 2
                            bh = bh * 4
                        update_matrix_rect(t, color_mode, PREVIEW_X, 2, width // 2, height // 4, 0, 0,
                                           width, data, colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                           colordata_bg_r, colordata_bg_g, colordata_bg_b, bx, by, bw, bh, True)
                    else:
                        selecting = False
                        cancel = False
                        print_status(t, "Left selection mode.")

                if not selecting:
                    # draw cursor
                    if last_x >= 0 and last_x < width and last_y >= 0 and last_y < width:
                        update_matrix_rect(t, color_mode, PREVIEW_X, 2, width // 2, height // 4, 0, 0,
                                           width, data, colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                           colordata_bg_r, colordata_bg_g, colordata_bg_b, last_x, last_y, 1, 1, False)
                    if x >= 0 and x < width and y >= 0 and y < width:
                        update_matrix_rect(t, color_mode, PREVIEW_X, 2, width // 2, height // 4, 0, 0,
                                           width, data, colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                           colordata_bg_r, colordata_bg_g, colordata_bg_b, x, y, 1, 1, True)

                print(t.move_xy(0, 2), end='')
                print(color_str, end='')
                print("𜶉𜶉", end='')
                display_zoomed_matrix(t, ZOOMED_X, 2, ZOOMED_PAD,
                                      x, y, width, height,
                                      selecting, select_x, select_y,
                                      COLORS, grid, zoomed_color,
                                      select_pixels, color_mode, data,
                                      colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                      colordata_bg_r, colordata_bg_g, colordata_bg_b)
                disp_x : int = x
                disp_y : int = y
                if selecting and not select_pixels:
                    disp_x = x // 2
                    disp_y = y // 4
                if color_mode == ColorMode.DIRECT:
                    bgstr = "Transparent"
                    if bg_r >= 0:
                        bgstr = f"{bg_r} {bg_g} {bg_b}"
                    print_status(t, f"{color_mode.name} {disp_x}, {disp_y}  {fg_r} {fg_g} {fg_b}  {bgstr}", 1)
                else:
                    bgstr = "Transparent"
                    if bg_r >= 0:
                        bgstr = f"{bg_r}"
                    print_status(t, f"{color_mode.name} {disp_x}, {disp_y}  {fg_r}  {bgstr}", 1)

                sys.stdout.flush()
                _, key = inkey_numeric(t)
                last_x = x
                last_y = y

                if not interrupted:
                    if selecting:
                        if not select_pixels:
                            key = key_to_action(KEY_ACTIONS_SELECT_TILES, key)
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
                                    cancel = True
                                case KeyActions.ZOOMED_COLOR:
                                    zoomed_color = not zoomed_color
                                    if zoomed_color:
                                        print_status(t, f"Zoomed view color toggled on.")
                                    else:
                                        print_status(t, f"Zoomed view color toggled off.")
                                case KeyActions.COPY:
                                    bx, by, bw, bh = get_xywh(x, y,
                                                              select_x, select_y,
                                                              width, height)

                                    clipboard = make_copy(bx, by, bw, bh, width, data, color_mode,
                                                          colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                                          colordata_bg_r, colordata_bg_g, colordata_bg_b)
                                    #print_status(t, f"Copied. {sx1} {sy1} {sx2} {sy2} {cw} {ch} {clipboard.get_dims()}")
                                    print_status(t, f"Copied.")
                                case KeyActions.RECT:
                                    bx, by, bw, bh = get_xywh(x, y,
                                                              select_x, select_y,
                                                              width, height)
                                    bw, bh = pixels_to_occupied_wh(bx, by, bw, bh)
                                    bx //= 2
                                    by //= 4

                                    make_undo(undos, redos,
                                              bx * 2, by * 4, bw * 2, bh * 4, width, data,
                                              color_mode,
                                              colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                              colordata_bg_r, colordata_bg_g, colordata_bg_b)

                                    for ty in range(by, by + bh):
                                        for tx in range(bx, bx + bw):
                                            if color_mode == ColorMode.DIRECT:
                                                colordata_fg_r[ty * (width // 2) + tx] = fg_r
                                                colordata_fg_g[ty * (width // 2) + tx] = fg_g
                                                colordata_fg_b[ty * (width // 2) + tx] = fg_b
                                                colordata_bg_r[ty * (width // 2) + tx] = bg_r
                                                colordata_bg_g[ty * (width // 2) + tx] = bg_g
                                                colordata_bg_b[ty * (width // 2) + tx] = bg_b
                                            else:
                                                colordata_fg_r[ty * (width // 2) + tx] = fg_r
                                                colordata_bg_r[ty * (width // 2) + tx] = bg_r

                                    refresh_matrix = (bx * 2, by * 4, bw * 2, bw * 4)
                            bx, by, bw, bh = get_xywh(x, y,
                                                      select_x, select_y,
                                                      width, height)
                            bw, bh = pixels_to_occupied_wh(bx, by, bw, bh)
                            print_status(t, f"Selecting tiles {select_x // 2} {select_y // 4} S: {bw} {bh}")
                        else: # pixels selection
                            key = key_to_action(KEY_ACTIONS_SELECT_PIXELS, key)
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
                                    cancel = True
                                case KeyActions.ZOOMED_COLOR:
                                    zoomed_color = not zoomed_color
                                    if zoomed_color:
                                        print_status(t, f"Zoomed view color toggled on.")
                                    else:
                                        print_status(t, f"Zoomed view color toggled off.")
                                case KeyActions.OPERATION:
                                    tool_operation = FILL_MODE_CYCLE[tool_operation]
                                case KeyActions.TOOL_MODE:
                                    if tool_mode == ToolMode.OUTLINE:
                                        tool_mode = ToolMode.FILL
                                    else:
                                        tool_mode = ToolMode.OUTLINE
                                case KeyActions.RECT:
                                    bx, by, bw, bh = get_xywh(x, y,
                                                              select_x, select_y,
                                                              width, height)

                                    make_undo(undos, redos,
                                              bx, by, bw, bh, width, data,
                                              color_mode,
                                              colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                              colordata_bg_r, colordata_bg_g, colordata_bg_b)

                                    if tool_mode == ToolMode.OUTLINE:
                                        draw_rect(data, width, height, bx, by, bw, bh, tool_operation)
                                    else:
                                        fill_rect(data, width, height, bx, by, bw, bh, tool_operation)

                                    refresh_matrix = (bx, by, bw, bh)
                                case KeyActions.CIRCLE:
                                    bx, by, bw, bh = get_xywh(x, y,
                                                              select_x, select_y,
                                                              width, height,
                                                              False)

                                    make_undo(undos, redos,
                                              bx, by, bw, bh, width, data,
                                              color_mode,
                                              colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                              colordata_bg_r, colordata_bg_g, colordata_bg_b)

                                    if tool_mode == ToolMode.OUTLINE:
                                        draw_circle(data, width, height, bx, by, bw, bh, tool_operation)
                                    else:
                                        fill_circle(data, width, height, bx, by, bw, bh, tool_operation)

                                    bx, by, bw, bh = get_xywh(x, y,
                                                              select_x, select_y,
                                                              width, height)
                                    refresh_matrix = (0, 0, width, height)
                                    #refresh_matrix = (bx, by, bw, bh)

                            bx, by, bw, bh = get_xywh(x, y,
                                                      select_x, select_y,
                                                      width, height,
                                                      False)
                            tool_mode_str = "Outline"
                            if tool_mode == ToolMode.FILL:
                                tool_mode_str = "Fill"
                            tool_operation_str = "Set"
                            if tool_operation == FillMode.CLEAR:
                                tool_operation_str = "Clear"
                            elif tool_operation == FillMode.INVERT:
                                tool_operation_str = "Invert"
                            print_status(t, f"Sel Pixels {select_x} {select_y} S: {bw} {bh} M: {tool_mode_str} O: {tool_operation_str}")

                        continue

                    key = key_to_action(KEY_ACTIONS, key)
                    match key:
                        case KeyActions.QUIT:
                            ans = prompt_yn(t, "Quit?")
                            if not ans:
                                print_status(t, "Returned.")
                            else:
                                running = False
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
                            refresh_matrix = (0, 0, width, height)
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
                                refresh_matrix = (0, 0, width, height)
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
                            new_color_mode = None
                            ans = prompt(t, "Which color mode to switch to? (D=DIRECT, 1=16, 2=256)")
                            if ans is None:
                                print_status(t, "Mode change canceled.")
                                continue

                            if ans[0].lower() == 'd':
                                if color_mode == ColorMode.DIRECT:
                                    print_status(t, "Already in DIRECT color mode.")
                                    continue
                                else:
                                    new_color_mode = ColorMode.DIRECT
                            elif ans[0] == '1':
                                if color_mode == ColorMode.C16:
                                    print_status(t, "Already in 16 color mode.")
                                    continue
                                else:
                                    new_color_mode = ColorMode.C16
                            elif ans[0] == '2':
                                if color_mode == ColorMode.C256:
                                    print_status(t, "Already in 256 color mode.")
                                    continue
                                else:
                                    new_color_mode = ColorMode.C256
                            else:
                                print_status(t, "Unrecognized response.")
                                continue

                            msg = can_convert(color_mode, new_color_mode, colordata_fg_r, colordata_bg_r)
                            if msg is not None:
                                ans = prompt_yn(t, f"{msg} OK TO CLEAR?")
                                if not ans:
                                    print_status(t, "Mode change canceled.")
                                    continue

                            make_undo(undos, redos,
                                      0, 0, width, height, width, data,
                                      color_mode,
                                      colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                      colordata_bg_r, colordata_bg_g, colordata_bg_b)

                            color_mode = new_color_mode
                            data = array('i', itertools.repeat(0, width * height))
                            colordata_fg_r, colordata_fg_g, colordata_fg_b, \
                                colordata_bg_r, colordata_bg_g, colordata_bg_b = \
                                new_color_data(color_mode, width, height)
                            fg_r, fg_g, fg_b, bg_r, bg_g, bg_b = get_default_colors(color_mode)
                            clear_screen(t)
                            refresh_matrix = (0, 0, width, height)
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
                            refresh_matrix = (0, 0, width, height)
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
                            refresh_matrix = (0, 0, width, height)
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

                                ans = prompt_yn(t, "With color?", True)
                                color = True
                                if not ans:
                                    color = False

                                save_file(t, path, color, data, width, color_mode,
                                          colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                          colordata_bg_r, colordata_bg_g, colordata_bg_b)
                                print_status(t, "File saved.")
                            else:
                                print_status(t, "Save canceled.")
                        case KeyActions.REDRAW:
                            clear_screen(t)
                            refresh_matrix = (0, 0, width, height)
                        case KeyActions.UNDO:
                            undos_len = len(undos)
                            undo_x, undo_y, undo_w, undo_h, \
                                width, height, data, color_mode, \
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
                                refresh_matrix = (undo_x, undo_y, undo_w, undo_h)
                                print_status(t, "Undid.")
                        case KeyActions.REDO:
                            redos_len = len(redos)
                            redo_x, redo_y, undo_w, undo_h, \
                                width, height, data, color_mode, \
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
                                refresh_matrix = (undo_x, undo_y, undo_w, undo_h)
                                print_status(t, "Redone.")
                        case KeyActions.SELECT_TILES:
                            if x < 0 or x > width - 1 or y < 0 or y > height - 1:
                                print_status(t, "Out of range.")
                            else:
                                selecting = True
                                select_pixels = False
                                select_x = x
                                select_y = y
                                print_status(t, "Entered tiles selection mode.")
                        case KeyActions.SELECT_PIXELS:
                            selecting = True
                            select_pixels = True
                            select_x = x
                            select_y = y
                            print_status(t, "Entered pixels selection mode.")
                        case KeyActions.PASTE:
                            if clipboard != None:
                                w, h = clipboard.get_dims()
                                if clipboard.color_mode != color_mode and \
                                   (clipboard.color_mode == ColorMode.DIRECT or
                                    color_mode == ColorMode.DIRECT or
                                    (clipboard.color_mode == ColorMode.C256 and
                                     color_mode == ColorMode.C16 and
                                     get_max_color(clipboard.colordata_fg_r, clipboard.colordata_bg_r) > 15)):
                                    print_status(t, "Clipboard and current color modes are incompatible.")
                                    continue

                                # the width and height given by the clipboard are in character cells
                                # so x and y need to be the top left of the character cell so the
                                # area being undone is the correct size/position
                                make_undo(undos, redos,
                                          x // 2 * 2, y // 4 * 4, w * 2, h * 4, width, data,
                                          color_mode,
                                          colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                          colordata_bg_r, colordata_bg_g, colordata_bg_b)

                                # apply wants dimensions in character cells
                                # this is normally abstracted
                                clipboard.apply(width // 2, data,
                                                colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                                colordata_bg_r, colordata_bg_g, colordata_bg_b,
                                                x // 2, y // 4)
                                refresh_matrix = (x, y, w * 2, h * 4)
                                print_status(t, "Pasted.")
                            else:
                                print_status(t, "Clipboard is empty.")
                        case KeyActions.HELP:
                            need_help = True
                            break

                if need_cont:
                    # need to fully reinitialize the terminal state and redraw
                    need_cont = False
                    need_winch = False
                    interrupted = False
                    clear_screen(t)
                    refresh_matrix = (0, 0, width, height)
                    # running is True so will loop back around
                    break
                elif need_winch:
                    # need redraw
                    need_winch = False
                    interrupted = False
                    clear_screen(t)
                    refresh_matrix = (0, 0, width, height)
                    continue

        if need_help:
            need_help = False
            print_help(t)


if __name__ == '__main__':
    main()
