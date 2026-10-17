"""The hunting field, drawn from the sprites in ``assets/hunt/hunt.json``.

The sprites (the hunter's eight poses, the trees and grass, the animals) and the
speeds were taken from recordings of the original; they are MECC's pictures and live
in the assets folder, not in the program. What the program supplies is the rules:

* Return starts and stops walking; the hunter walks the way he is facing, two dots
  across every eight ticks and one dot down every four (a tick is a sixtieth of a
  second);
* the letter keys I O P / K ; / , . / point the rifle directly, the arrow keys turn it a
  step at a time, the space bar fires;
* an animal appears from the paper's rule (the low byte of a draw from 0 to 999 below
  2, room for it, fewer than four shots), crosses the field, and is shot if a bullet
  touches it; it then lies where it fell.

**Not taken from the original** (the movement was not analysed, only watched): how the
animals choose their paths, the speed of the bullet and the length of the hunt (25
seconds, as in the recordings).
"""

from __future__ import annotations

import time

__all__ = ["play", "available"]

POSES = ["UL", "U", "UR", "R", "DR", "D", "DL", "L"]       # clockwise
LETTERS = {"i": "UL", "o": "U", "p": "UR", ";": "R", "/": "DR", ".": "D", ",": "DL", "k": "L"}
LEFT, UP, RIGHT, DOWN = "\x1c", "\x1e", "\x1d", "\x1f"
VEC = {"UL": (-1, -1), "U": (0, -1), "UR": (1, -1), "R": (1, 0),
       "DR": (1, 1), "D": (0, 1), "DL": (-1, 1), "L": (-1, 0)}
KIND = {0: "deer", 1: "deer", 2: "bison", 3: "deer", 4: "rabbit", 5: "squirrel"}
FRAME_TICKS = {"rabbit": 4, "squirrel": 3, "deer": 4, "bison": 8}
TICKS = 60                      # per second
HUNT_TICKS = 1500               # 25 seconds
W, H = 280, 192


def available(assets) -> bool:
    return bool(getattr(assets, "hunt", None) and assets.hunt())


def _lit(rows, x, y):
    return {(x + c, y + r) for r, row in enumerate(rows) for c, ch in enumerate(row)
            if ch != "." and 0 <= x + c < W and 0 <= y + r < H}


def _size(rows):
    return len(rows[0]) if rows else 0, len(rows)


def _scenery(data, below):
    """Three or four trees and two or three tufts of grass, each on the 14-dot grid its
    picture was drawn on (its colours depend on the column)."""
    trees = [s for s in data["scenery"] if s["kind"] == "tree"]
    grass = [s for s in data["scenery"] if s["kind"] == "grass"]
    out = []
    for kind, pool, n, ytop, yspan in (("tree", trees, 3 + below(2), 0, 125),
                                      ("grass", grass, 2 + below(2), 30, 140)):
        for _ in range(n):
            s = pool[below(len(pool))]
            x = 14 * below(19) + s["k"] - 14
            out.append((s["image"], x, ytop + below(yspan)))
    return out


def play(ui, data, bullets, below, types, weights, passes=HUNT_TICKS, getkey=None,
         live=None):
    """Run one hunt. Returns ``{"meat", "bullets", "shots"}``.

    *below(n)* is the hunting module's own generator and *weights* its table of
    (lowest weight, span) per animal type.
    """
    cv = ui.cv
    getkey = getkey or ui.backend.poll
    live = (getattr(ui, "daily_pause", 0) > 0) if live is None else live
    hunter = data["hunter"]
    pose = POSES[below(8)]
    hx, hy = 61 + 2 * below(70), 20 + below(90)           # odd, as the sprite's colours need
    walking = False
    px = py = 0                                           # tick counters for walking
    scenery = _scenery(data, below)
    animals, dead, shots, meat, bullet = [], [], 0, 0, None
    left = bullets
    t0 = time.monotonic()
    idle = 0
    last_drawn = -1

    def bbox():
        h = hunter[pose]
        w, hh = _size(h["rows"])
        return hx + h["dx"], hy + h["dy"], w, hh

    for tick in range(passes + 6 * len(scenery)):
        revealed = min(len(scenery), tick // 6)
        building = tick < 6 * len(scenery)
        k = getkey()
        if not building:
            if k == "\r":
                walking = not walking
            elif k and k.lower() in LETTERS:
                pose = LETTERS[k.lower()]
            elif k in (LEFT, UP):
                pose = POSES[(POSES.index(pose) - 1) % 8]
            elif k in (RIGHT, DOWN):
                pose = POSES[(POSES.index(pose) + 1) % 8]
            elif k == " " and left > 0 and shots < 4 and bullet is None:
                left -= 1
                vx, vy = VEC[pose]
                lit = _lit(hunter[pose]["rows"], hx + hunter[pose]["dx"], hy + hunter[pose]["dy"])
                tip = max(lit, key=lambda p: (p[0] * vx + p[1] * vy, -abs(p[1] - hy - 8)))
                bullet = {"x": float(tip[0] + vx), "y": float(tip[1] + vy), "vx": vx, "vy": vy}
            # walking: two dots across every eight ticks, one dot down every four
            if walking:
                vx, vy = VEC[pose]
                px += 1
                py += 1
                x0, y0, w, h = bbox()
                if vx and px % 8 == 0 and 6 <= x0 + 2 * vx and x0 + w + 2 * vx <= W:
                    hx += 2 * vx
                if vy and py % 4 == 0 and 8 <= y0 + vy and y0 + h + vy <= 168:
                    hy += vy
            # a new animal
            if len(animals) < 2 and shots < 4:
                if (below(1000) & 0xFF) < 2:
                    typ = types[below(len(types))]
                    kind = KIND[typ]
                    d = 1 if below(2) == 0 else -1
                    frames = data["animals"][kind]["R" if d > 0 else "L"]
                    w, _ = _size(frames[0])
                    animals.append({"type": typ, "kind": kind, "dir": d, "n": 0,
                                    "x": float(-w if d > 0 else W), "y": float(24 + below(130)),
                                    "vy": (below(3) - 1) * 0.12,
                                    "v": data["speed"][kind] / TICKS})
            for a in animals[:]:
                a["x"] += a["dir"] * a["v"]
                a["y"] += a["vy"]
                a["n"] += 1
                if a["x"] < -40 or a["x"] > W + 20 or a["y"] < 0 or a["y"] > 175:
                    animals.remove(a)
            # the bullet: four dots across and two down a tick (as seen in the recordings,
            # a slope of two across to one down), stopped by the first animal it touches
            if bullet:
                for _ in range(2):
                    bullet["x"] += 2 * bullet["vx"]
                    bullet["y"] += bullet["vy"]
                    bx, by = int(bullet["x"]), int(bullet["y"])
                    if not (-2 <= bx < W + 2 and -2 <= by < H + 2):
                        bullet = None
                        break
                    for a in animals:
                        rows = _frame(data, a)
                        ax, ay = int(a["x"]), int(a["y"])
                        if any((bx - ax + dx, by - ay + dy) in _mask(rows)
                               for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                            animals.remove(a)
                            shots += 1
                            low, span = weights[a["type"]]
                            meat += low + below(span)
                            dead.append(_corpse(data, a, rows))
                            bullet = None
                            break
                    if bullet is None:
                        break
            if left == 0 and bullet is None:
                idle += 1
                if idle > 90:
                    break
            if tick >= passes:
                break
        # draw
        if live:
            due = t0 + tick / TICKS
            now = time.monotonic()
            if now < due:
                time.sleep(due - now)
            elif now - due > 0.05:
                continue                                   # behind: skip the picture, keep the rules
        elif tick % 60 and tick != passes - 1:
            continue
        cv.clear()
        cv.backdrop("hunt", 0, 0)
        for name, sx, sy in scenery[:revealed]:
            cv.image(name, sx, sy)
        if not building:
            colours = data.get("colours") if cv.plain else None      # themed: coloured sprites
            if colours:
                pal = {k: tuple(v) for k, v in colours["palette"].items()}
                for x, y, rows in dead:
                    cv.paint_rows(rows, x, y, pal)
                for a in animals:
                    cv.paint_rows(_frame(data, a), int(a["x"]), int(a["y"]), pal)
                if bullet:
                    bx, by = int(bullet["x"]), int(bullet["y"])
                    cv.base.paste(tuple(colours["bullet"]), (max(0, bx), max(0, by), min(W, bx + 2), min(H, by + 1)))
                h = hunter[pose]
                cv.paint_rows(h["rows"], hx + h["dx"], hy + h["dy"], pal)
            else:
                for x, y, rows in dead:
                    cv.dots.update(_lit(rows, x, y))
                for a in animals:
                    cv.dots.update(_lit(_frame(data, a), int(a["x"]), int(a["y"])))
                if bullet:
                    bx, by = int(bullet["x"]), int(bullet["y"])
                    cv.dots.update(p for p in ((bx, by), (bx + 1, by)) if 0 <= p[0] < W and 0 <= p[1] < H)
                h = hunter[pose]
                cv.dots.update(_lit(h["rows"], hx + h["dx"], hy + h["dy"]))
        ui.refresh()
    return {"meat": meat, "bullets": left, "shots": shots}


_MASKS = {}


def _mask(rows):
    key = id(rows)
    m = _MASKS.get(key)
    if m is None:
        m = {(c, r) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != "."}
        _MASKS[key] = (m, rows)
        return m
    return m[0]


def _frame(data, a):
    frames = data["animals"][a["kind"]]["R" if a["dir"] > 0 else "L"]
    return frames[(a["n"] // FRAME_TICKS[a["kind"]]) % len(frames)]


def _corpse(data, a, rows):
    """Where it fell: the deer's own picture, or the animal turned over."""
    if a["kind"] == "deer" and data.get("lying", {}).get("deer"):
        rows = data["lying"]["deer"]["rows"]
    else:
        rows = rows[::-1]
    return int(a["x"]), int(a["y"]), rows
