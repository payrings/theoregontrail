"""The graphical front end: the same ``UI`` the terminal and the tests use, drawn
as the Apple II screen.

It does what the ``&`` package did: a text window, a cursor, proportional letters
two dots apart, nine dots to a line, word wrap, pictures and boxes. The numbers
(where each window sits, where each line starts) are the ones in the BASIC listing
and were checked against screenshots of the original; see ``screens.py``.
"""

from __future__ import annotations

from ..ui import UI, allowed_chars, ALLOWED
from .canvas import Canvas, W, H

BLOCK = chr(127)            # the input cursor is character 127 of the font

__all__ = ["GraphicalUI"]


class GraphicalUI(UI):
    #: screens that draw themselves ask for this (see ``screens.py``)
    pictures = True
    counts_keyboard_time = True

    def __init__(self, assets, backend, show_daily: bool = True):
        super().__init__()
        self.assets = assets
        self.backend = backend
        self.cv = Canvas(assets)
        self.glyphs = assets.glyphs
        self.hsp, self.vsp = assets.hsp, 1
        self.show_daily_screen = show_daily
        self.daily_pause = 0.0
        self.win = (0, 0, W, H)
        self.cx = self.cy = 0
        self.hang = 0               # indent of wrapped lines
        self.slack = -1             # a word fits if cx + width <= window width - 1
        self.inverse = False        # INVERSE: dark letters on a white panel
        self.linebase = 0           # where the current line starts (the left edge for wrapping)
        from .sound import Sound
        self.sound = Sound(enabled=lambda: False)     # the program points it at memory byte 975

    # ------------------------------------------------------------- text model
    def width(self, s: str) -> int:
        g = self.glyphs
        return sum(g.get(c, (6,))[0] + self.hsp for c in s)

    def dfw(self, x, y, w, h):
        """``& DFW``: a text window, cursor at its top-left."""
        self.win = (x, y, w, h)
        self.cx = self.cy = 0
        self.linebase = 0
        self.hang = 0

    def co(self, x=None, y=None):
        """``& CO,x,y`` (window coordinates; a missing one is left alone)."""
        if x is not None:
            self.cx = x
            self.linebase = x
        if y is not None:
            self.cy = y

    def put(self, s: str):
        wx, wy, _, _ = self.win
        for ch in s:
            self.cx += self.cv.glyph(ch, wx + self.cx, wy + self.cy, self.inverse) + self.hsp

    def cell(self) -> int:
        """The advance of one digit: the width of a column when BASIC pads a number with spaces."""
        return self.width("0")

    def padded(self, s, n: int, newline: bool = False):
        """Print *s* right-aligned in *n* digit-wide columns (BASIC's ``RIGHT$("   " + s, n)``).

        The padding is counted in digit cells, not in space glyphs, so the right edge of a column of
        numbers stays straight in a font whose space is narrower than its digits.
        """
        s = str(s)[-n:]
        self.cx += self.cell() * (n - len(s))
        self.put(s)
        if newline:
            self.nl()

    def nl(self):
        self.cx = 0
        self.linebase = 0
        self.cy += 8 + self.vsp

    def line(self, s: str, newline: bool = True, centre: bool = False):
        if centre:
            self.cx = (self.win[2] - self.width(s)) // 2
        self.put(s)
        if newline:
            self.nl()

    def para(self, s: str, newline: bool = True, hang: int = 0, first: int = 0):
        """Print *s*, wrapping at the window's right edge; wrapped lines start at *hang*."""
        ww = self.win[2]
        toks, i = [], 0
        while i < len(s):
            j = i
            while j < len(s) and s[j] == " ":
                j += 1
            k = j
            while k < len(s) and s[k] != " ":
                k += 1
            toks.append((s[i:j], s[j:k]))
            i = k
        if self.cx == 0:
            self.cx = first
        for sp, w in toks:
            if self.cx > self.linebase and self.cx + self.width(sp + w) > ww + self.slack:
                self.nl()
                self.cx = self.linebase = hang
                sp = ""
            self.put(sp + w)
        if newline:
            self.nl()

    # -------------------------------------------------- the UI the game uses
    def print(self, text: str = ""):
        self.out.append(text)
        if text.endswith(" ") and text.strip():          # a prompt: the cursor stays
            self.para(text, newline=False, hang=self.hang)
        else:
            self.para(text, hang=self.hang)

    def clear(self):
        self.cv.clear()
        self.win = (0, 0, W, H)
        self.cx = self.cy = 0
        self.linebase = 0
        self.hang = 0
        self.vsp = 1
        self.inverse = False
        self.out.append("<clear>")

    def at(self, x: int, y: int):
        self.co(x, y)

    def window(self, *args):
        if len(args) == 4:
            self.dfw(*args)

    def wind(self, n: int = 0):
        if n == 0:
            self.win = (0, 0, W, H)
            self.cx = self.cy = 0

    def box(self, *args):
        if len(args) >= 4:
            self.cv.box(*args[:5])

    def indent(self, n: int):
        self.hang = abs(n) if n < 0 else 0

    def line_to(self):
        pass

    def centre(self, text: str):
        self.line(text, centre=True)

    # ----------------------------------------------------------------- input
    def refresh(self):
        self.backend.show(self.cv.render())

    def flush(self):
        self.backend.flush()

    def pump(self):
        """Let the window repaint and take in keys without reading any."""
        self.backend.pump()

    def poll_key(self):
        k = self.backend.poll()
        return "\r" if k in ("\r", "\n") else None

    def wait_key(self, allowed: str = "", prompt: str = "Press SPACE BAR to continue", y: int = 184,
                 tune: bool = False):
        """``& SPACE`` writes at 184 and makes no sound; the OREGON TRAIL program's own line 950 (and
        WIN's) writes at 182 and plays the tune while it waits (*tune*)."""
        self.window(0, 0, W, H)
        self.cv.clear_text(0, 180, W - 1, H - 1)
        self.co(0, y)
        self.line(prompt, centre=True)
        self.refresh()
        if tune:
            self.sound.waiting()                    # 955: IF PEEK (975) THEN & PT,1,1
        try:
            while True:
                k = self.backend.read()
                if k is None:
                    return ""
                if k == "\x13":                     # 957: Control-S flips the sound and goes round again
                    if tune:                         # only line 957 of a 950 wait watches for it
                        self.sound.toggle()
                        self.sound.stop()
                        self.sound.waiting()
                    continue
                return k
        finally:
            self.sound.stop()

    BLINK = 0.5                                     # seconds the cursor stays on or off

    def _read_blinking(self):
        """A key, ``None`` at the end of the input, or ``""`` after a blink interval."""
        reader = getattr(self.backend, "read_timeout", None)
        return reader(self.BLINK) if reader else self.backend.read()

    def key(self, allowed: str = "", maxlen: int = 1, default: str = "", ret: bool = True) -> str:
        """``& INP`` reads a line: the answer is typed, shown, and ends with Return.
        ``ret=False`` makes Return an ignored key and the first accepted key the
        answer (the store's item prompt takes 1 to 5 or the space bar, and nothing else)."""
        ok = allowed_chars(allowed) | ({"\r", "\n"} if ret else set()) if allowed else None
        wx, wy, _, _ = self.win
        x0, y0 = self.cx, self.cy
        got = []
        shown = True
        while True:
            # redraw the typed text and the cursor block after it (the block blinks)
            self.cv.clear_text(wx + x0, wy + y0, wx + x0 + 120, wy + y0 + 9)
            self.cx, self.cy = x0, y0
            self.put("".join(got) + (BLOCK if shown else ""))
            self.refresh()
            k = self._read_blinking()
            if k == "":                             # no key yet: blink
                shown = not shown
                continue
            shown = True
            if k is None:
                break
            if k in ("\r", "\n"):
                if ret:
                    break
                continue
            if k in ("\x7f", "\b"):
                if got:
                    got.pop()
                continue
            if not k.isprintable():                 # arrow keys and the like
                continue
            if len(got) >= maxlen or (ok and k not in ok):
                continue
            got.append(k)
            if maxlen == 1 and not ret:             # only the store's item prompt answers on the key itself
                break
        self.cv.clear_text(wx + x0, wy + y0, wx + x0 + 120, wy + y0 + 9)
        self.cx, self.cy = x0, y0
        self.put("".join(got))
        self.nl()
        return "".join(got)

    def yes_no(self, prompt: str = "") -> str:
        if prompt:
            self.print(prompt)
        x0, y0 = self.cx, self.cy
        wx, wy, _, _ = self.win
        self.cx, self.cy = x0, y0
        shown = True
        while True:
            self.cv.clear_text(wx + x0, wy + y0, wx + x0 + 12, wy + y0 + 9)
            self.cx, self.cy = x0, y0
            if shown:
                self.put(BLOCK)
            self.refresh()
            k = self._read_blinking()
            if k == "":
                shown = not shown
                continue
            if k is None:
                return "N"
            if k.upper() in ("Y", "N"):
                self.cv.clear_text(wx + x0, wy + y0, wx + x0 + 12, wy + y0 + 9)
                self.cx, self.cy = x0, y0
                self.put(k.upper())
                self.nl()
                return k.upper()

    def flip_disk(self, side: int, title: str = "OREGON TRAIL") -> str:
        other = 2 if side == 1 else 1
        self.clear()
        self.co(0, 80)
        self.line(f"Please insert side {other} of the {title} diskette.", centre=False)
        self.wait_key()
        return str(other)
