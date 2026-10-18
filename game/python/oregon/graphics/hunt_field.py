"""The hunting field for the graphical mode.

**A stand-in.** The original draws the field and moves the animals in machine code that
the paper did not analyse (section 1.4, Appendix G), and its sprites are not among the
pictures on the disks. So this field, its hunter and its animals are drawn here in plain
shapes, and the animals' movement and the aim are a plausible game of my own. What *is*
the paper's: the keys (Return starts and stops walking, the arrow keys point the rifle,
the space bar fires), the spawn rule, which animals may appear at each landmark, the
weights, at most two animals on the screen and four shots, and a hunt of 2,500 passes.
"""

from __future__ import annotations

import math
import time

__all__ = ["play", "ARROWS"]

# the arrow keys as the Tk backend delivers them (control characters nothing else uses)
UP, DOWN, LEFT, RIGHT = "\x1e", "\x1f", "\x1c", "\x1d"
ARROWS = {"Up": UP, "Down": DOWN, "Left": LEFT, "Right": RIGHT}

HUNTER = (140, 165)
GROUND_TOP, GROUND_BOTTOM = 55, 175
# type -> (colour, width, height, legs): bigger weights, bigger animals
LOOK = {0: (2, 12, 6, 2), 1: (3, 15, 8, 2), 2: (5, 22, 11, 2),
        3: (3, 12, 6, 2), 4: (3, 5, 3, 0), 5: (5, 4, 3, 0)}
SPEED = {0: 2, 1: 2, 2: 1, 3: 3, 4: 3, 5: 2}      # dots per pass, at most


def _draw_animal(cv, a):
    colour, w, h, legs = LOOK[a["type"]]
    x, y = int(a["x"]), int(a["y"])
    cv.box(x, y, x + w - 1, y + h - 1, colour)                     # body
    head = max(2, h // 2)
    hx = x + w if a["dir"] > 0 else x - head
    cv.box(hx, y - 1, hx + head - 1, y + head - 2, colour)         # head
    for k in range(legs):
        lx = x + 2 + k * (w - 5)
        cv.box(lx, y + h, lx + 1, y + h + 2, colour)


def _draw_tree(cv, x, y):
    cv.box(x + 3, y + 8, x + 4, y + 16, 5)                         # trunk
    cv.box(x, y, x + 7, y + 8, 1)                                  # leaves


def _draw(ui, st):
    cv = ui.cv
    ui.clear()
    cv.box(0, GROUND_TOP, 279, GROUND_BOTTOM, 1)
    for tx in st["trees"]:
        sx = (tx - st["scroll"]) % 320 - 20
        if -8 < sx < 280:
            _draw_tree(cv, sx, GROUND_TOP - 12)
    for a in st["animals"]:
        _draw_animal(cv, a)
    hx, hy = HUNTER
    cv.box(hx - 2, hy - 8, hx + 2, hy, 3)                          # the hunter
    cv.box(hx - 1, hy - 12, hx + 1, hy - 9, 5)
    ang = st["aim"] * math.pi / 8
    ex, ey = hx + int(30 * math.sin(ang)), hy - 6 - int(30 * math.cos(ang))
    cv.line(hx, hy - 6, ex, ey, 3)                                 # the rifle
    ui.dfw(0, 0, 280, 192)
    ui.co(0, 181)
    ui.put(f"Bullets: {st['bullets']}  Shot: {st['shots']}  "
           + ("Walking" if st["walking"] else "Standing"))


def _hit(st, a):
    """Does the shot along the rifle's line pass through this animal?"""
    colour, w, h, legs = LOOK[a["type"]]
    hx, hy = HUNTER
    ang = st["aim"] * math.pi / 8
    dx, dy = math.sin(ang), -math.cos(ang)
    cx, cy = a["x"] + w / 2 - hx, a["y"] + h / 2 - (hy - 6)
    along = cx * dx + cy * dy
    if along <= 0:
        return False
    across = abs(cx * dy - cy * dx)
    return across <= max(w, h) / 2 + 2


def play(ui, bullets, spawn_draw, kind_draw, types, weights, passes=2500,
         getkey=None, pause=0.02):
    """Run one hunt on the screen. Returns ``{"meat", "bullets", "shots"}``.

    *spawn_draw(n)* and *kind_draw(n)* are the hunting module's own generator;
    *weights* is the table of (lowest weight, span) per type.
    """
    getkey = getkey or ui.backend.poll
    st = {"animals": [], "bullets": bullets, "shots": 0, "aim": 0, "walking": False,
          "scroll": 0, "trees": [12, 70, 131, 188, 247, 301]}
    meat = 0
    for n in range(passes):
        k = getkey()
        fired = False
        if k == "\r":
            st["walking"] = not st["walking"]
        elif k in (LEFT, UP):
            st["aim"] = (st["aim"] - 1) % 16
        elif k in (RIGHT, DOWN):
            st["aim"] = (st["aim"] + 1) % 16
        elif k == " " and st["bullets"] > 0 and st["shots"] < 4:
            st["bullets"] -= 1
            fired = True
            hit = next((a for a in st["animals"] if _hit(st, a)), None)
            if hit:
                st["animals"].remove(hit)
                st["shots"] += 1
                low, span = weights[hit["type"]]
                meat += low + kind_draw_span(spawn_draw, span)
        # the paper's spawn rule: the low byte of a draw 0-999 below 2, room for another
        if len(st["animals"]) < 2 and st["shots"] < 4:
            if (spawn_draw(1000) & 0xFF) < 2:
                kind = types[spawn_draw(len(types))]
                side = spawn_draw(2)
                st["animals"].append({
                    "type": kind, "dir": 1 if side == 0 else -1,
                    "x": -20 if side == 0 else 285,
                    "y": GROUND_TOP + 8 + spawn_draw(GROUND_BOTTOM - GROUND_TOP - 45),
                    "v": 1 + spawn_draw(SPEED[kind])})
        if st["walking"]:
            st["scroll"] += 1
        for a in list(st["animals"]):
            a["x"] += a["dir"] * a["v"] * (1 if n % 2 else 0) - (1 if st["walking"] else 0)
            if a["x"] < -30 or a["x"] > 310:
                st["animals"].remove(a)
        if pause > 0 and n % 2 == 0:
            _draw(ui, st)
            ui.refresh()
        if fired and (st["bullets"] == 0 or st["shots"] >= 4):
            if pause > 0:
                time.sleep(0.8)                    # the last shot is seen before it ends
            break
        if pause > 0:
            time.sleep(pause)
    return {"meat": meat, "bullets": st["bullets"], "shots": st["shots"]}


def kind_draw_span(draw, span):
    return draw(span)
