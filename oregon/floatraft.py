"""FLOAT: the Columbia River rafting game.

The BASIC is fully available in the listing and is transcribed here; the machine code
it uses for the drawing is not analysed (Appendix F.4), so the raft is shown as text.

The rules, all from paper section 11.2:

* the raft occupies one of eighteen positions and starts at sixteen; the arrow keys
  change its direction between one left and one right and it moves one position a
  pass;
* moving past position one or sixteen is a shore collision and reverses the direction,
  and after pass 205 a raft at position seventeen has landed;
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


def run(c):
    """Lines 1000-1000 and 1070-1180: the rafting game."""
    st = c.st
    from . import common, losses
    c.set_program("FLOAT")
    c.ui.clear()
    c.ui.print("Use the arrow keys to guide your raft through the rushing waters of "
               "the Columbia River.")
    common.wait_key(c)
    c.ui.print("After passing the third direction sign, land your raft at the trail "
               "to the Willamette Valley.")
    common.wait_key(c)
    st.I[2] = num.parse(str(c.mem.peek(909)))
    for item in range(3, 8):
        st.I[item] = num.parse(str(c.mem.peek(905 + item)))
    st.I[8] = num.parse(str(c.mem.peek(906) + c.mem.peek(907) * 256))
    st.I[4] = num.parse(str(c.mem.peek_word(904)))
    st.PF = st.I[8]
    hp = HP_START
    direction = -1
    rocks = [None, None]
    tc = 0
    period = 1.0 / PASSES_PER_SECOND
    while True:
        tc += 1
        started = time.perf_counter()
        # line 1070: the fill test is "IF NOT FL(n) AND INT(100 * RND(1) + 1) <= RF",
        # and there is no short-circuit, so the draw happens either way
        for slot in (0, 1):
            if rocks[slot] is None:
                # RF is 15, from line 1060
                if num.le(num.int_(num.add(
                        num.mul(num.parse("100"),
                                c.rng.rnd1(f"1070 rock {slot}")),
                        num.ONE)), num.parse(str(ROCK_CHANCE))):
                    kind = num.int_(num.add(
                        num.mul(num.parse("100"),
                                c.rng.rnd1(f"300 rock type {slot}")), num.ONE))
                    if num.lt(kind, num.parse("14")):
                        rx = num.int_(num.mul(
                            c.rng.rnd1(f"310 rock x {slot}"), num.parse("10")))
                        rocks[slot] = {"x": num.mul(rx, num.parse("10")),
                                      "y": num.parse("175")}
                    else:
                        rocks[slot] = {"x": num.ZERO,
                                      "y": num.add(num.parse("50"),
                                                   num.int_(num.mul(
                                                       c.rng.rnd1(f"310 rock y {slot}"),
                                                       num.parse("120"))))}
        for r in rocks:
            if r is not None:
                r["x"] = num.add(r["x"], num.parse(str(XI)))
                r["y"] = num.add(r["y"], num.parse(str(YI)))
                if num.gt(r["x"], num.parse("240")) or num.lt(r["y"], num.parse("10")):
                    rocks[rocks.index(r)] = None
        # line 1110: the arrow keys
        key = c.ui.poll_key()
        if key in ("\x1b[D", "l") and hp > 0 and direction > -1:
            direction -= 1
        if key in ("\x1b[C", "h") and hp < 17 and direction < 1:
            direction += 1
        if direction != 0:
            hp += direction
            if hp < 1 or hp > 16:
                collide(c, "shore")
                hp = 17 if hp > 16 else 1
            if tc > PASSES_TO_LAND and hp == 17:
                landed(c)
                return "WIN"
            if tc > PASSES_TO_MISS:
                missed(c)
                landed(c)
                return "WIN"
        for slot, r in enumerate(rocks):
            if r is not None and _touch(hp, r):
                rocks[slot] = None
                collide(c, "rock")
                break
        if tc in SIGN_PASSES:
            c.ui.print(f"[direction sign at pass {tc}]")
        # pace to a 1 MHz interpreter, so a player can see the river
        time.sleep(max(0.0, period - (time.perf_counter() - started)))
    return "WIN"


def _line_500(c, kind: str) -> None:
    """Lines 500 and 200: the collision test loop, run once even with NR = -1.

    The original's loop is ``FOR A = 0 TO NR`` with ``NR`` set to -1 at line 1060, so
    by rule (c) of paper section 2.5 it runs exactly once with ``A`` equal to 0. It
    reads ``RX(0)`` and ``RY(0)``, which hold whatever the last rock left behind, so
    the test is usually against a stale box; reproducing it costs one comparison and
    keeps the routine faithful.
    """
    from . import num
    for a in num.fort_range(0, -1):
        rx = num.parse("0")
        ry = num.parse("0")
        x3, y3 = rx, ry
        x4, y4 = num.add(x3, num.parse("28")), num.add(y3, num.parse("8"))
        # 200: "ROCK = Z: COL = 1: IF X2 < X3 OR X1 > X4 OR Y1 > Y4 OR Y2 < Y3 THEN
        # COL = 0: ROCK = -1"
        del x3, y3, x4, y4, a


def _touch(hp: int, r) -> bool:
    """Lines 200 and 1120: the raft's box and the rock's box, as plain arithmetic."""
    rx, ry = num.as_float(r["x"]), num.as_float(r["y"])
    x1, y1 = 84 + 8 * hp + 6, 5 * hp - 6 + 18
    x2, y2 = 84 + 8 * hp + 26, 5 * hp - 6 + 25
    x3, y3 = rx + 11, ry + 1
    x4, y4 = x3 + 20, y3 + 6
    return not (x2 < x3 or x1 > x4 or y1 > y4 or y2 < y3)


def collide(c, kind: str):
    """Lines 700-760: a shore or a rock, and what it costs.

    The chance of losing ten separate things destroys the raft outright and everyone
    is lost. A person who drowns is marked with ``-2`` and removed after the message,
    because the leader cannot drown while others live -- the same rule as at a river.
    """
    st = c.st
    from . import losses
    # line 500: "FOR A = 0 TO NR" with NR = -1 runs once with A = 0, so slot 0 is
    # tested even when neither slot holds anything. The box test at line 200 with
    # RX(0) and RY(0) is harmless there, but it is what the original does.
    _line_500(c, kind)
    people, oxen, goods = (0.15, 0.3, 0.5) if kind == "shore" else (0.6, 0.6, 0.7)
    out = []
    out += losses.lose_people(c, num.parse(str(people)))
    out += losses.lose_oxen(c, num.parse(str(oxen)))
    out += losses.lose_goods(c, num.parse(str(goods)))
    text = "The raft has hit the shore." if kind == "shore" \
        else "The raft has hit a rock."
    if len(out) > 9:
        st.NP = 0
        text = "The raft is destroyed, everything has been lost."
        out = []
    from . import common
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
    out = losses.lose_goods(c, num.HALF)
    common.message(c, "The raft has missed the landing.", out)


def landed(c):
    """Line 900: the raft is ashore, and the state is written for ``WIN``."""
    st = c.st
    from . import common
    c.ui.print("One moment please...")
    c.mem.poke(900, num.as_int(st.NP), 910)
    c.mem.poke(909, num.trunc(st.I[2]), 910)
    c.mem.poke_word(906, num.trunc(st.I[8]), 910)
    c.mem.poke(908, num.trunc(st.I[3]), 910)
    c.mem.poke_word(904, num.trunc(st.I[4]), 910)
    for item in (5, 6, 7):
        c.mem.poke(905 + item, num.trunc(st.I[item]), 910)
    return "WIN"
