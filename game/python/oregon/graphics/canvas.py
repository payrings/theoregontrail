"""A 280 x 192 picture made the way the Apple II made it.

Pictures and boxes are plain colours. Text is kept as lit dots and coloured at the
end by the Apple's rule, so letters get the same green and violet fringes as the
original: a lone dot takes the colour of its column, a dot beside another is white,
and a dark dot between two lit ones is filled in.

An assets folder with a ``theme.json`` switches the rule off: text dots take one plain
colour, and boxes and lines use the theme's colours with no column rules.
"""

from __future__ import annotations

__all__ = ["Canvas", "COLOURS", "W", "H"]

W, H = 280, 192
WHITE = (255, 255, 254)
COLOURS = {0: (0, 0, 0), 1: (56, 203, 0), 2: (199, 52, 255), 3: WHITE,
           4: (0, 0, 0), 5: (242, 94, 0), 6: (13, 161, 255), 7: WHITE}
VIOLET, GREEN = (199, 52, 255), (56, 203, 0)


class Canvas:
    def __init__(self, assets):
        self.assets = assets
        self.Image = assets._Image
        theme = getattr(assets, "theme", None)
        self.plain = bool(theme)
        self.text_colour = theme["text_colour"] if theme else WHITE
        self.palette = {**COLOURS, **(theme["colours"] if theme else {})}
        self.clear()

    def clear(self):
        self.base = self.Image.new("RGB", (W, H), (0, 0, 0))
        if self.plain:                      # a themed folder may paint the empty screen
            back = self.assets.screen("backdrop_default")
            if back is not None:
                self.base.paste(back.convert("RGB"), (0, 0))
        self.dots = set()
        self.filled = set()          # dark dots the Apple fills in between two lit ones of a colour box

    # -------------------------------------------------------------- drawing
    def image(self, name: str, x: int, y: int) -> bool:
        # a picture's colours depend on its column, so a file may be drawn for one
        # position only: name_m<k>.png is the one for x mod 14 == k
        im = self.assets.image(f"{name}_m{x % 14}") or self.assets.image(name)
        if im is None:
            return False
        self.base.paste(im, (x, y), im)
        return True

    def backdrop(self, name: str, x: int = 0, y: int = 0) -> bool:
        """A full-colour background from ``screens/backdrop_<name>.png`` (nothing without a theme)."""
        if not self.plain:
            return False
        im = self.assets.screen(f"backdrop_{name}")
        if im is None:
            return False
        self.base.paste(im, (x, y), im)
        return True

    def paint_rows(self, rows, x, y, palette):
        """Paint a coloured sprite: each character of *rows* is a key of *palette*
        ('.' is transparent)."""
        px = self.base.load()
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                X, Y = x + c, y + r
                if ch != "." and 0 <= X < W and 0 <= Y < H:
                    px[X, Y] = palette.get(ch, (255, 0, 255))

    def screen(self, name: str) -> bool:
        im = self.assets.screen(name)
        if im is None:
            return False
        self.base.paste(im.convert("RGB"), (0, 0))
        self.dots.clear()
        return True

    def box(self, x1, y1, x2, y2, colour: int = 0):
        """``& BOX``: fill a rectangle (colour 0 clears it, text included)."""
        x1, x2 = max(0, x1), min(W - 1, x2)
        y1, y2 = max(0, y1), min(H - 1, y2)
        if x2 < x1 or y2 < y1:
            return
        self.dots = {d for d in self.dots if not (x1 <= d[0] <= x2 and y1 <= d[1] <= y2)}
        self.filled = {p for p in self.filled if not (x1 <= p[0] <= x2 and y1 <= p[1] <= y2)}
        if self.plain:
            lit = None
        elif colour in (1, 5):          # the Apple plots these on odd columns only, and the
            lit = 1               # dark ones between are filled in: so the colour runs
        elif colour in (2, 6):        # from the first lit column to the last
            lit = 0
        else:
            lit = None
        if lit is not None:
            xs = [x for x in range(x1, x2 + 1) if x % 2 == lit]
            if not xs:
                return
            x1, x2 = xs[0], xs[-1]
        if self.plain:                # themed: the colour as it is, on every column
            self.base.paste(self.palette[colour], (x1, y1, x2 + 1, y2 + 1))
            return
        self.base.paste(COLOURS[colour], (x1, y1, x2 + 1, y2 + 1))
        if lit is not None:
            self.filled.update((x, y) for x in range(x1, x2 + 1) if x % 2 != lit
                               for y in range(y1, y2 + 1))

    def line(self, x1, y1, x2, y2, colour: int):
        """``HPLOT x1,y1 TO x2,y2``. Only the colour's own columns are lit (blue and violet on
        even ones, green and orange on odd ones, black and white on all); call
        :meth:`fill_gaps` afterwards for the dark dots between two lit ones."""
        px = self.base.load()
        rgb = self.palette[colour]
        own = {1: 1, 5: 1, 2: 0, 6: 0}.get(colour)
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx, sy = (1 if x2 >= x1 else -1), (1 if y2 >= y1 else -1)
        # the ROM's line routine (HLIN, $F53A) steps one dot across or one dot down, never
        # both, and draws dx + dy + 1 dots
        err = dx - dy
        x, y = x1, y1
        for step in range(dx + dy + 1):
            for xx in ((x,) if colour in (0, 3, 4, 7) or self.plain else (x, x + 1)):
                if 0 <= xx < W and 0 <= y < H:
                    px[xx, y] = rgb
            if err >= 0:
                x += sx
                err -= dy
            else:
                y += sy
                err += dx

    def take(self, x1, y1, x2, y2):
        """``& TAKE``: keep a rectangle of the screen (pictures and lit dots)."""
        crop = self.base.crop((x1, y1, x2 + 1, y2 + 1))
        dots = {d for d in self.dots if x1 <= d[0] <= x2 and y1 <= d[1] <= y2}
        filled = {d for d in self.filled if x1 <= d[0] <= x2 and y1 <= d[1] <= y2}
        return (x1, y1, x2, y2, crop, dots, filled)

    def put(self, saved):
        """``& PUT``: put back what :meth:`take` kept."""
        x1, y1, x2, y2, crop, dots, filled = saved
        self.base.paste(crop, (x1, y1))
        self.dots = {d for d in self.dots if not (x1 <= d[0] <= x2 and y1 <= d[1] <= y2)} | dots
        self.filled = {d for d in self.filled if not (x1 <= d[0] <= x2 and y1 <= d[1] <= y2)} | filled

    def fill_gaps(self, colour: int, rect):
        """A dark dot between two lit dots of *colour* is lit too."""
        if self.plain:
            return
        px = self.base.load()
        rgb = COLOURS[colour]
        x1, y1, x2, y2 = rect
        for y in range(y1, y2 + 1):
            for x in range(x1 + 1, x2):
                if px[x, y] != rgb and px[x - 1, y] == rgb and px[x + 1, y] == rgb:
                    px[x, y] = rgb

    def clear_text(self, x1, y1, x2, y2):
        """Remove letters from a rectangle and leave the pictures under them."""
        self.dots = {d for d in self.dots if not (x1 <= d[0] <= x2 and y1 <= d[1] <= y2)}

    def panel(self, x1, y1, x2, y2):
        """A white area made of lit dots, so that inverse letters cut dark ones out of it."""
        self.dots.update((x, y) for x in range(max(0, x1), min(W - 1, x2) + 1)
                         for y in range(max(0, y1), min(H - 1, y2) + 1))

    def glyph(self, ch: str, x: int, y: int, inverse: bool = False) -> int:
        """Draw one letter with its top-left corner at (x, y); returns its width.
        An inverse letter removes dots instead of adding them."""
        w, yoff, rows = self.assets.glyphs.get(ch, self.assets.glyphs.get("?", (6, 0, [])))
        for r, row in enumerate(rows):
            for c, bit in enumerate(row):
                if bit and 0 <= x + c < W and 0 <= y + yoff + r < H:
                    if inverse:
                        if (x + c, y + yoff + r) in self.dots:
                            self.dots.discard((x + c, y + yoff + r))
                            if self.plain:            # themed: the ink shows through, not the picture
                                self.base.putpixel((x + c, y + yoff + r), self.palette[0])
                        else:                         # over a picture: a black dot
                            self.base.putpixel((x + c, y + yoff + r), self.palette[0] if self.plain else (0, 0, 0))
                    else:
                        self.dots.add((x + c, y + yoff + r))
        return w

    # ---------------------------------------------------------------- output
    def render(self):
        im = self.base.copy()
        px = im.load()
        d = self.dots
        if self.plain:
            for (x, y) in d:
                px[x, y] = self.text_colour
            return im
        for (x, y) in d:
            if (x - 1, y) in d or (x + 1, y) in d:
                px[x, y] = WHITE
            else:
                px[x, y] = VIOLET if x % 2 == 0 else GREEN
        for (x, y) in d:                       # a dark dot between two lit ones
            if (x + 2, y) in d and (x + 1, y) not in d and x + 1 < W:
                px[x + 1, y] = VIOLET if x % 2 == 0 else GREEN
        # the fill-in dots of a colour box stay only while both lit dots beside them do
        for (x, y) in self.filled:
            if 0 < x < W - 1 and px[x, y] != (0, 0, 0):
                if px[x - 1, y] == (0, 0, 0) or px[x + 1, y] == (0, 0, 0):
                    px[x, y] = (0, 0, 0)
            elif x in (0, W - 1) and px[x, y] != (0, 0, 0):
                pass
        return im
