"""The picture and font files the graphical mode draws with.

The pictures are ordinary PNG files in an *assets folder* (``game/assets`` by
default, or the folder named by ``--assets``). They are not part of the program:
replace any of them with your own and the game uses the new one. The layout is:

``screens/<name>.png``
    full screens, 280 x 192 (``l0.png`` is the first landmark, ``m0.png`` the map).
``images/<table>_<NN>.png``
    small pictures, with transparency where the picture is black. ``first_02.png``
    is picture 2 of the table ``FIRST``. A picture may be any size; it is drawn
    with its top-left corner where the game puts it.
    A picture's colours depend on the column it is drawn at. ``first_02_m5.png`` is
    the version for a picture drawn where x mod 14 = 5; it is used when it exists and
    ``first_02.png`` is used otherwise.
``font/font.png`` and ``font/font.json``
    the letters: one bitmap per character and the width, offset and height of each.
``theme.json`` (optional)
    turns off the Apple's colour rules: ``{"plain_text": true, "text_colour": [r, g, b],
    "colours": {"0": [r, g, b], ...}}``. Letters are then drawn in one plain colour, and
    boxes and lines use the listed colours as they are, with no odd-column filling.
    Without the file the game keeps the Apple's colours.
``screens/backdrop_<name>.png``
    optional full-colour backgrounds drawn under the pictures (``sky_prairie``,
    ``ground_1`` ...); the game uses a flat colour where there is none.

Needs Pillow (``pip install pillow``).
"""

from __future__ import annotations

import json
import os

__all__ = ["Assets", "AssetError", "default_folder"]


class AssetError(RuntimeError):
    pass


def default_folder() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "assets"))


class Assets:
    def __init__(self, folder: str | None = None):
        try:
            from PIL import Image
        except ImportError as e:                       # pragma: no cover
            raise AssetError("the graphical mode needs Pillow: pip install pillow") from e
        self._Image = Image
        self.folder = folder or default_folder()
        if not os.path.isdir(self.folder):
            raise AssetError(f"assets folder not found: {self.folder}")
        self._cache = {}
        self.glyphs = self._load_font()
        self.theme = self._load_theme()

    # ----------------------------------------------------------------- pictures
    def _open(self, sub: str, name: str):
        key = (sub, name)
        if key not in self._cache:
            path = os.path.join(self.folder, sub, name + ".png")
            if not os.path.isfile(path):
                self._cache[key] = None
            else:
                self._cache[key] = self._Image.open(path).convert("RGBA")
        return self._cache[key]

    def image(self, name: str):
        """A small picture, or None if the folder has no file for it."""
        return self._open("images", name)

    def hunt(self):
        """The hunting field's sprites (``hunt/hunt.json``), or None if the folder has none."""
        if "hunt" not in self._cache:
            path = os.path.join(self.folder, "hunt", "hunt.json")
            try:
                with open(path, encoding="utf-8") as f:
                    self._cache["hunt"] = json.load(f)
            except (OSError, ValueError):
                self._cache["hunt"] = None
        return self._cache["hunt"]

    def screen(self, name: str):
        """A full screen, or None if the folder has no file for it."""
        return self._open("screens", name)

    # -------------------------------------------------------------------- theme
    def _load_theme(self):
        path = os.path.join(self.folder, "theme.json")
        try:
            with open(path, encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            return None
        theme = {"plain_text": bool(meta.get("plain_text", False)),
                 "text_colour": tuple(meta.get("text_colour", (255, 255, 254))),
                 "colours": {int(k): tuple(v) for k, v in meta.get("colours", {}).items()}}
        return theme

    # --------------------------------------------------------------------- font
    def _load_font(self):
        base = os.path.join(self.folder, "font")
        try:
            meta = json.load(open(os.path.join(base, "font.json"), encoding="utf-8"))
            sheet = self._Image.open(os.path.join(base, "font.png")).convert("RGBA")
        except OSError as e:
            raise AssetError(f"font files not found in {base}") from e
        self.hsp = int(meta.get("hsp", 2))
        px = sheet.load()
        out = {}
        for key, g in meta["glyphs"].items():
            rows = []
            for r in range(g["rows"]):
                rows.append([1 if px[g["x"] + c, g["y"] + r][3] > 127 else 0
                             for c in range(g["width"])])
            out[chr(int(key))] = (g["width"], g["yoff"], rows)
        return out
