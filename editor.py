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
# TODO: Add selection/copy/paste.
# TODO: Add undo.
# TODO: Add save without color.

UNDO_LEVELS = 10
DEFAULT_FILL = True
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
    SAVE_FILE = auto()
    REDRAW = auto()
    UNDO = auto()

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
        if w == dw and h == len(self.colordata_fg_r) // dw:
            self.whole_buffer = True

        if self.whole_buffer:
            # if it's the whole thing, just copy it
            self.data = copy.copy(data)
            self.colordata_fg_r = copy.copy(colordata.fg_r)
            if color_mode == ColorMode.DIRECT:
                self.colordata_fg_g = copy.copy(colordata.fg_g)
                self.colordata_fg_b = copy.copy(colordata.fg_b)
                self.colordata_bg_r = copy.copy(colordata.bg_r)
                self.colordata_bg_g = copy.copy(colordata.bg_g)
                self.colordata_bg_b = copy.copy(colordata.bg_b)
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

    def apply(self,
              dw : int, data : array,
              colordata_fg_r : array,
              colordata_fg_g : array,
              colordata_fg_b : array,
              colordata_bg_r : array,
              colordata_bg_g : array,
              colordata_bg_b : array):
        if self.whole_buffer:
            # if it's the whole thing, just return it
            return self.w, self.h, self.data, \
                   self.colordata_fg_r, self.colordata_fg_g, self.colordata_fg_b, \
                   self.colordata_bg_r, self.colordata_bg_g, self.colordata_bg_b
        else:
            cw = dw * 2
            sw = self.w * 2
            cx = self.x * 2
            # reverse of building the arrays?
            for i in range(len(self.colordata_fg_r) // self.w):
                data[((self.y + i) * (cw * 4)) +            cx:((self.y + i) * (cw * 4)) +            cx + sw] = \
                    self.data[i * (sw * 4)           :i * (sw * 4) +            sw]
                data[((self.y + i) * (cw * 4)) +  cw +      cx:((self.y + i) * (cw * 4)) +  cw +      cx + sw] = \
                    self.data[i * (sw * 4) +  sw     :i * (sw * 4) +  sw +      sw]
                data[((self.y + i) * (cw * 4)) + (cw * 2) + cx:((self.y + i) * (cw * 4)) + (cw * 2) + cx + sw] = \
                    self.data[i * (sw * 4) + (sw * 2):i * (sw * 4) + (sw * 2) + sw]
                data[((self.y + i) * (cw * 4)) + (cw * 3) + cx:((self.y + i) * (cw * 4)) + (cw * 3) + cx + sw] = \
                    self.data[i * (sw * 4) + (sw * 3):i * (sw * 4) + (sw * 3) + sw]

                colordata_fg_r[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w] = \
                    self.colordata_fg_r[i * self.w:i * self.w + self.w]
                if self.color_mode == ColorMode.DIRECT:
                    colordata_fg_g[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w] = \
                        self.colordata_fg_g[i * self.w:i * self.w + self.w]
                    colordata_fg_b[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w] = \
                        self.colordata_fg_b[i * self.w:i * self.w + self.w]
                    colordata_bg_r[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w] = \
                        self.colordata_bg_r[i * self.w:i * self.w + self.w]
                    colordata_bg_g[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w] = \
                        self.colordata_bg_g[i * self.w:i * self.w + self.w]
                    colordata_bg_b[(self.y + i) * dw + self.x:(self.y + i) * dw + self.x + self.w] = \
                        self.colordata_bg_b[i * self.w:i * self.w + self.w]

        return None, None, None, None, None, None, None, None, None


BLACK = 0
WHITE = 15
COLOR_PREVIEW = "𜶉𜶉"
CURSOR = "🯧🯦"
BLOCK = "██"

TILE_CURSOR = 7
TILE_INVERT = 14
TILE_TOPLEFT = 1
TILE_LEFT = 2
TILE_BOTTOMLEFT = 3
TILE_TOPRIGHT = 4
TILE_RIGHT = 5
TILE_BOTTOMRIGHT = 6
TILES = ("  ", "𜵊🮂", "▌ ", "𜷀▂", "🮂𜶘", " ▐", "▂𜷕", "🯧🯦", "𜵰𜴏", "𜵮🯦", "𜷤𜶿", "𜴢𜶫", "🯧𜶪", "𜷓𜷥",
         "██", "𜶖▆", "▐█", "𜴡🮅", "▆𜵈", "█▌", "🮅𜴍", "𜷂𜷖", "𜺠𜷓", "𜵲𜷖", "𜺫𜴢", "𜶿𜺣", "𜷂𜴶", "𜴏𜺨")
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
    lastcolor_fg_r = colordata_fg_r[cw * cy + cx]
    lastcolor_fg_g = colordata_fg_g[cw * cy + cx]
    lastcolor_fg_b = colordata_fg_b[cw * cy + cx]
    # only need R to determine transparency
    lastcolor_bg_r = colordata_bg_r[cw * cy + cx]
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
                lastcolor = ""
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
                # This is waaaaaay complicated and probably some remaining bugs
                if use_color:
                    ciy : int = (dy + iy) // 4
                    cix : int = (dx + ix) // 2
                    if color_mode == ColorMode.DIRECT:
                        if data[dw * (dy + iy) + (dx + ix)]:
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
                        if data[dw * (dy + iy) + (dx + ix)]:
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
                                    if color_r == BLACK:
                                        print(t.color(WHITE), end='')
                                    else:
                                        print(t.color(BLACK), end='')
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
                                    if color_r == BLACK:
                                        print(t.color(WHITE), end='')
                                    else:
                                        print(t.color(BLACK), end='')
                                lastcolor_bg_r = color_r
                                lastcolor_fg_r = color_fg_r
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
                            tile += TILE_TOPLEFT
                        elif (dy + iy) % 4 == 3:
                            tile += TILE_BOTTOMLEFT
                        else:
                            tile += TILE_LEFT
                    else:
                        if (dy + iy) % 4 == 0:
                            tile += TILE_TOPRIGHT
                        elif (dy + iy) % 4 == 3:
                            tile += TILE_BOTTOMRIGHT
                        else:
                            tile += TILE_RIGHT

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
        elif allow_transparent and key == ord('t'):
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
        elif allow_transparent and key == ord('t'):
            c = -1
            break

    clear_screen(t)
    return c

def get_default_colors(color_mode : ColorMode):
    # set to white on transparent
    if color_mode == ColorMode.DIRECT:
        return 255, 255, 255, -1, -1, -1

    return WHITE, 0, 0, -1, 0, 0

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

def make_undo(undos : list, undopos : int,
              x : int, y : int, w : int, h : int,
              dw : int, data : array,
              color_mode : ColorMode,
              colordata_fg_r : array,
              colordata_fg_g : array,
              colordata_fg_b : array,
              colordata_bg_r : array,
              colordata_bg_g : array,
              colordata_bg_b : array):
    undopos += 1
    if undopos == len(undos):
        undopos = 0

    # convert from pixels to character cells
    undos[undopos] = DataRect(x // 2, y // 4,
                              ((x + w) // 2) - (x // 2) + 1, ((y + h) // 4) - (y // 4) + 1,
                              dw // 2, data, color_mode,
                              colordata_fg_r, colordata_fg_g, colordata_fg_b,
                              colordata_bg_r, colordata_bg_g, colordata_bg_b)
    return undopos

def apply_undo(undos : list, undopos : int,
               dw : int, dh : int, data : array,
               color_mode : ColorMode,
               colordata_fg_r : array,
               colordata_fg_g : array,
               colordata_fg_b : array,
               colordata_bg_r : array,
               colordata_bg_g : array,
               colordata_bg_b : array):
    if undos[undopos] is None:
        return undopos, dw, dh, data, \
               colordata_fg_r, colordata_fg_g, colordata_fg_b, \
               colordata_bg_r, colordata_bg_g, colordata_bg_b

    new_dw, new_dh, new_data, \
        new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
        new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b = \
        undos[undopos].apply(dw // 2, data,
                             colordata_fg_r, colordata_fg_g, colordata_fg_b,
                             colordata_bg_r, colordata_bg_g, colordata_bg_b)
    undos[undopos] = None
    undopos -= 1
    if undopos < 0:
        undopos = len(undos) - 1
    if new_data is not None:
        # return the new one, convert dimensions in character cells to pixels
        return undopos, new_dw * 2, new_dh * 4, new_data, \
               new_colordata_fg_r, new_colordata_fg_g, new_colordata_fg_b, \
               new_colordata_bg_r, new_colordata_bg_g, new_colordata_bg_b

    # return back the originals
    return undopos, dw, dh, data, \
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
    undos : list[None | DataRect] = [None for x in range(UNDO_LEVELS)]
    undopos = 0

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
        ord('P'): KeyActions.PICK_COLOR,
        ord('S'): KeyActions.SAVE_FILE,
        ord('R'): KeyActions.REDRAW,
        ord('U'): KeyActions.UNDO
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
                        undopos = make_undo(undos, undopos,
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

                    undopos = make_undo(undos, undopos,
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
                        undopos = make_undo(undos, undopos,
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
                    undopos = make_undo(undos, undopos,
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
                    last_undopos = undopos
                    undopos, width, height, data, \
                        colordata_fg_r, colordata_fg_g, colordata_fg_b, \
                        colordata_bg_r, colordata_bg_g, colordata_bg_b = \
                        apply_undo(undos, undopos,
                                   width, height, data,
                                   color_mode,
                                   colordata_fg_r, colordata_fg_g, colordata_fg_b,
                                   colordata_bg_r, colordata_bg_g, colordata_bg_b)
                    if undopos == last_undopos:
                        print_status(t, "No more undos.")
                    else:
                        clear_screen(t)
                        refresh_matrix = True
                        print_status(t, "Undid.")
 

if __name__ == '__main__':
    main()
