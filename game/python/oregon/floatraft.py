"""FLOAT: the Columbia River rafting game.

The BASIC is fully available in the listing and is transcribed here; the machine code
it uses for the drawing is not analysed (Appendix E.4), so the raft is shown as text.

The rules, all from paper section 11.2:

* the raft occupies one of eighteen positions and starts at sixteen; the arrow keys
  change its direction between one left and one right and it moves one position a
  pass;
* moving past position one or sixteen is a shore collision: the direction is reversed
  (line 400) and the raft is left where it is, at 0 or 17, for the next pass to bring
  back; after pass 205 a raft at position seventeen has landed, and that is tested
  before the collision is dealt with;
* two rock slots, each filled on a fifteen per cent chance per pass -- the draw is
  made even when the slot is already full -- and each rock moves eight pixels right
  and four up and is removed when it leaves the screen;
* after pass 225 the raft has missed the landing: goods are lost with a chance of one
  half and it lands anyway;
* a collision loses people, oxen and goods, with ten or more separate losses
  destroying the raft entirely.

The loss routines are the same ones the river crossings use.
"""

from __future__ import annotations

import time

from . import num

__all__ = ["run", "HP_START", "PASSES_TO_LAND", "PASSES_TO_MISS", "SIGN_PASSES",
           "PASSES_PER_SECOND"]

#: The paper (11.2) notes that the speed of this game depends on how fast the
#: interpreter runs its loop, and that a replica must pace the loop to match a
#: 1 MHz machine. The inner loop here is a few hundred 6502 cycles on the original,
#: which is a few thousand passes a second.
PASSES_PER_SECOND = 4000

HP_START = 16
PASSES_TO_LAND = 205
PASSES_TO_MISS = 225
SIGN_PASSES = (60, 120, 170)
ROCK_CHANCE = 15            # in a hundred
XI, YI = 8, -4


#: the arrow keys, as the terminal delivers them, and the keys the listing tests for
#: (``LE`` = 136 and ``U`` = 139 steer left; ``R`` = 149 and ``D`` = 138 steer right)
LEFT_KEYS = ("\x1b[D", "\x1b[A", "\x08", "\x0b", "l", "\x1c", "\x1e")
RIGHT_KEYS = ("\x1b[C", "\x1b[B", "\x15", "h", "\x1d", "\x1f")


def _read_key(c):
    """``KEY = USR (3)``: one key if one is waiting; an arrow arrives as ESC [ x."""
    if c.ui.pictures:
        return c.ui.backend.poll()               # the window's arrow keys arrive as one character
    key = c.ui.poll_key()
    if key == "\x1b":
        a = c.ui.poll_key()
        b = c.ui.poll_key() if a == "[" else None
        key = "\x1b[" + b if b else None
    return key


def _geometry(hp: int):
    """Line 1110: the raft's box. ``FN RX(Z) = 84 + 8 * Z``, ``FN RY(Z) = 5 * Z - 6``."""
    x, y = 84 + 8 * hp, 5 * hp - 6
    return x + 6, y + 18, x + 26, y + 25            # X1, Y1, X2, Y2


def _overlap(raft, rx: int, ry: int) -> bool:
    """Line 200: the raft's box against a rock's, which line 1120 builds from the
    rock's position: ``X3 = RX + 11, Y3 = RY + 1, X4 = X3 + 20, Y4 = Y3 + 6``."""
    x1, y1, x2, y2 = raft
    x3, y3 = rx + 11, ry + 1
    x4, y4 = x3 + 20, y3 + 6
    return not (x2 < x3 or x1 > x4 or y1 > y4 or y2 < y3)


def _new_rock(c, slot: int, rocks):
    """Lines 300 and 310: a rock appears.

    ``N = INT (100 * RND (1) + 1)``; below 14 it is on the bottom edge,
    ``RY = 175`` and ``RX = INT (10 * RND (1))`` -- **as it stands**, not times ten.
    Otherwise it enters at the left, ``RX = 0`` and
    ``RY = 50 + INT (120 * RND (1) + 1)``.
    """
    n = num.store(num.int_(num.add(num.mul(num.parse("100"),
                                           c.rng.rnd1(f"300 rock type {slot}")),
                                   num.ONE)))
    if num.lt(n, num.parse("14")):
        rocks[slot]["ry"] = 175
        rocks[slot]["rx"] = num.as_int(num.int_(num.mul(
            num.parse("10"), c.rng.rnd1(f"310 rock x {slot}"))))
    else:
        rocks[slot]["rx"] = 0
        rocks[slot]["ry"] = 50 + num.as_int(num.int_(num.add(num.mul(
            num.parse("120"), c.rng.rnd1(f"310 rock y {slot}")), num.ONE)))
    rocks[slot]["fl"] = True


def run(c):
    """Lines 1000 and 1070-1180: the rafting game, one pass a trip round the loop.

    The order of a pass is the listing's: the fill test for each rock slot (1070,
    1075), the rocks move (1080, 1085), the key (1090, 1100), the raft moves and may
    hit a bank (1110, 400), **then the landing** (1115, 1116), then the rocks are
    tested against the raft (1120, 1130), dropped if they have left the river (1160,
    1165), and last of all a collision is dealt with (1170).
    """
    st = c.st
    from . import common, losses
    c.set_program("FLOAT")
    from .graphics import raft_scene
    scene = c.ui.pictures and raft_scene.available(c.ui)
    texts = ("Use the arrow keys to guide your raft through the rushing waters of "
             "the Columbia River.",
             "After passing the third direction sign, land your raft at the trail "
             "to the Willamette Valley.")
    if c.ui.pictures:
        from .graphics import screens
        for i, text in enumerate(texts):
            screens.message_box(c.ui, text, (7, 62, 257, 109), picture="l16", redraw=(i == 0))
            c.ui.wait_key()
    else:
        c.ui.clear()
        c.ui.print(texts[0])
        common.wait_key(c)
        c.ui.print(texts[1])
        common.wait_key(c)
    st.I[2] = num.parse(str(c.mem.peek(909)))
    for item in range(3, 8):
        st.I[item] = num.parse(str(c.mem.peek(905 + item)))
    st.I[8] = num.parse(str(c.mem.peek(906) + c.mem.peek(907) * 256))
    st.I[4] = num.parse(str(c.mem.peek_word(904)))
    st.PF = st.I[8]
    hp = HP_START
    direction = -1
    # FL(0), FL(1) and RX(), RY(): a slot keeps its position after the rock is gone
    rocks = [{"fl": False, "rx": 0, "ry": 0}, {"fl": False, "rx": 0, "ry": 0}]
    rock = -1                  # ROCK: the slot the last box test hit, or -1
    col = False                # COL
    tc = 0
    period = ((raft_scene.PASS_SECONDS if getattr(c.ui, "daily_pause", 0) > 0 else 0.0)
              if scene else 1.0 / PASSES_PER_SECOND)
    signs = []                                  # passes since each sign entered
    landing = None                              # passes since the arrival point entered (1146)
    # line 1050: X1 = X: Y1 = Y: X2 = X + 35: Y2 = Y + 25 -- the first box is the
    # whole picture; line 1110 narrows it only once the raft has moved
    x, y = 84 + 8 * hp, 5 * hp - 6
    raft = (x, y, x + 35, y + 25)
    while True:
        tc += 1
        started = time.perf_counter()
        # lines 1070 and 1075: "IF NOT FL(n) AND INT (100 * RND (1) + 1) <= RF".
        # Applesoft has no short-circuit, so the draw is made on every pass whether
        # or not the slot is already full.
        for slot in (0, 1):
            roll = num.int_(num.add(num.mul(num.parse("100"),
                                            c.rng.rnd1(f"1070 rock {slot}")),
                                    num.ONE))
            if not rocks[slot]["fl"] and num.le(roll, num.parse(str(ROCK_CHANCE))):
                _new_rock(c, slot, rocks)
        # lines 1080 and 1085
        for r in rocks:
            if r["fl"]:
                r["rx"] += XI
                r["ry"] += YI
        # lines 1090 and 1100: the steering is limited to one left or one right
        key = _read_key(c)
        if hp > 0 and key in LEFT_KEYS:
            direction = max(direction - 1, -1)
        if hp < 17 and key in RIGHT_KEYS:
            direction = min(direction + 1, 1)
        # line 1110. Line 400 sets COL and turns the raft round when it leaves the
        # river, but it does not put it back inside: HP stays at 0 or 17
        if direction != 0:
            hp += direction
            col = False
            if hp < 1 or hp > 16:
                col = True
                direction = -direction
            raft = _geometry(hp)
        # lines 1115 and 1116: the landing comes before any collision is handled
        if tc > PASSES_TO_LAND and hp == 17:
            landed(c)
            return "WIN"
        if tc > PASSES_TO_MISS:
            missed(c)
            landed(c)
            return "WIN"
        # lines 1120 and 1130: "IF NOT COL THEN IF FL(n) THEN ... GOSUB 200"
        for slot in (0, 1):
            if not col and rocks[slot]["fl"]:
                rock = slot
                col = _overlap(raft, rocks[slot]["rx"], rocks[slot]["ry"])
                if not col:
                    rock = -1
        if tc == raft_scene.LANDING_PASS and scene:
            landing = -1
        if tc in SIGN_PASSES:
            if scene:
                signs.append(-1)
            else:
                c.ui.print(f"[direction sign at pass {tc}]")
        # lines 1160 and 1165 (slot 1 first): a rock stays only while RX < 240 AND
        # RY > 10
        for slot in (1, 0):
            r = rocks[slot]
            if r["fl"] and not (r["rx"] < 240 and r["ry"] > 10):
                r["fl"] = False
        # line 1170
        if col:
            kind = "shore" if rock == -1 else "rock"
            if rock != -1:
                rocks[rock]["fl"] = False          # 710: FL(ROCK) = 0
            if collide(c, kind) == "MENU":
                return "DIED"
            col = False
            raft = _geometry(hp)
        if scene:
            signs = [n + 1 for n in signs if n + 1 < raft_scene.SIGN_STEPS]
            if landing is not None:
                landing += 1
            raft_scene.draw(c.ui, hp, [(r["rx"], r["ry"]) for r in rocks if r["fl"]],
                            [raft_scene.sign_position(n) for n in signs],
                            None if landing is None else raft_scene.landing_position(landing))
        # pace to the original's loop, so a player can see the river
        time.sleep(max(0.0, period - (time.perf_counter() - started)))


def collide(c, kind: str):
    """Lines 700-760: a shore or a rock, and what it costs.

    The chance of losing ten separate things destroys the raft outright and everyone
    is lost. A person who drowns is marked with ``-2`` and removed after the message,
    because the leader cannot drown while others live -- the same rule as at a river.
    """
    st = c.st
    from . import losses
    # (FLOAT line 500, the box-test loop over NR, is never called from the listing.)
    shore = kind == "shore"
    out = []
    out += losses.lose_people(c, num.store(num.parse(".15" if shore else ".6")), len(out))
    out += losses.lose_oxen(c, num.store(num.parse(".3" if shore else ".6")))
    out += losses.lose_goods(c, num.store(num.parse(".5" if shore else ".7")))
    text = "The raft has hit the shore." if kind == "shore" \
        else "The raft has hit a rock."
    if out:
        text += "  You have lost:"                       # 720: IF Z THEN Z$ = ...
    if len(out) > 9:
        st.NP = 0
        text = "The raft is destroyed, everything has been lost."
        out = []
    from . import common
    sound = getattr(c.ui, "sound", None)
    if sound is not None:                  # 740: IF PEEK (975) THEN FOR S1 = 0 TO 3: & PT,1: NEXT
        lasts = sound.collision()
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < lasts:
            if hasattr(c.ui, "pump"):
                c.ui.pump()
            time.sleep(0.02)
    common.message(c, text, out)
    # line 750 is "FOR L = 0 TO NP - 1", and the body runs once even when NP is 0
    for i in num.fort_range(0, num.as_int(st.NP) - 1):
        if num.eq(st.H1[i], num.parse("-2")):
            st.H1[i] = num.neg(num.ONE)
            st.NP = num.as_int(st.NP) - 1
            st.N[i] = st.N[num.as_int(st.NP)]
    if num.as_int(st.NP) <= 0:
        common.message(c, "Everyone in the party has died.")
        c.outcome = "DIED"
        return "MENU"
    return None


def missed(c):
    """Lines 950-960: the raft missed the landing, and lands anyway."""
    from . import losses, common
    out = losses.lose_goods(c, num.store(num.parse(".5")))
    # 950: IF Z THEN A$ = A$ + "  You have lost:": GOSUB 800 -- with nothing lost
    # there is no message at all
    if out:
        common.message(c, "The raft has missed the landing.  You have lost:", out)


def landed(c):
    """Line 900: the raft is ashore, and the state is written for ``WIN``."""
    st = c.st
    from . import common
    if hasattr(c.ui, "sound"):
        c.ui.sound.select("ms16")                # 900: & RFL, "MS16.BIN" AT 1153
    c.ui.print("One moment please...")
    c.mem.poke(900, num.as_int(st.NP), 910)
    c.mem.poke(909, num.trunc(st.I[2]), 910)
    c.mem.poke_word(906, num.trunc(st.I[8]), 910)
    c.mem.poke(908, num.trunc(st.I[3]), 910)
    c.mem.poke_word(904, num.trunc(st.I[4]), 910)
    for item in (5, 6, 7):
        c.mem.poke(905 + item, num.trunc(st.I[item]), 910)
    return "WIN"
