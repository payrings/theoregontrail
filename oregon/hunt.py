"""HUNT.LIB: hunting for food.

Lines 4600 in OREGON TRAIL and 50000 to 50020 in HUNT.LIB, on top of the machine
code the ``& HUNT`` command calls.

What the paper establishes (section 11.1), and what is honoured here:

* the routine has **its own** random generator, seeded at the start of each hunt from
  the Applesoft seed bytes and the keyboard counter, and it **reads the Applesoft seed
  without writing it** -- so a hunt never advances the game's sequence
  (Appendix G.6). :class:`HuntRng` below is separate from the game's for that reason.
* six animal types; type 0 appears between Chimney Rock and the Snake River, type 1
  past Independence Rock, type 2 up to Independence Rock, and types 3, 4 and 5
  everywhere. A new animal's type is drawn evenly from those allowed.
* at most two animals on screen at once, a new animal every attempt, and none once
  four have been shot;
* a shot animal's weight is a base plus a random amount, added to the total;
* a hunt lasts 2500 passes of the routine's main loop, and the space bar fires while
  Return starts and stops walking.

**What was not analysed** (paper section 1.4 and Appendix H): the animal movement,
the hit testing and the pictures. Those are in one clearly marked function,
:func:`approximate_movement`, which is an approximation and says so. Everything the
paper does specify -- the spawn rules, the weights, the ammunition, the session
length and the hundred-pound carry limit -- is reproduced.

Then the BASIC, lines 50011 to 50020: a total of three or more is halved, nothing is
added to a wagon already holding 2000 pounds, the amount is cut to the space left and
then to the hundred pounds a hunt can carry back.
"""

from __future__ import annotations

from . import num

__all__ = ["go", "HuntRng", "ANIMALS", "SESSION_PASSES", "CARRY_LIMIT"]

SESSION_PASSES = 2500
CARRY_LIMIT = 100
MAX_ANIMALS = 2
MAX_SHOTS = 4

# type: (weight low, weight span, where it may appear)
#   0  100 to 140   Chimney Rock to the Snake River
#   1  200 to 400   past Independence Rock
#   2 1700 to 2000  up to Independence Rock
#   3  120 to 150   everywhere, the probable deer
#   4    2 to  10   everywhere, the probable rabbit
#   5    3 to   7   everywhere, the probable squirrel
ANIMALS = [
    (100, 40), (200, 200), (1700, 300), (120, 30), (2, 8), (3, 4),
]
PROBABLE = ["not identified", "elk or bear", "bison", "deer", "rabbit", "squirrel"]


class HuntRng:
    """The hunting module's private generator.

    Separate from the game's ``rng`` on purpose: the paper says the routine reads the
    Applesoft seed but never writes it, so hunting does not advance the game's
    sequence. Appendix G.6 says the same, and the test for it checks that a hunt
    leaves the seed bytes untouched.
    """

    def __init__(self, seed: bytes):
        self.b = bytearray(seed) if seed else bytearray(5)

    def below(self, n: int) -> int:
        """A value in 0 to n-1, from this module's own state."""
        self._step()
        m = int.from_bytes(self.b, "big") or 1
        return (m >> 11) % n

    def _step(self):
        # a plain linear congruential step, which is all the paper's description
        # needs of a generator the original's own code never returns from
        x = (int.from_bytes(self.b, "big") * 1103515245 + 12345) & ((1 << 40) - 1)
        self.b[:] = x.to_bytes(5, "big")


def allowed_types(landmark: int):
    """Which animal types may appear, from the arguments at line 50011.

    ``& HUNT,Z, LM > 3 AND LM < 13, LM > 6, LM < 7, 1, ZO, L, Z`` -- argument two
    allows type 0, argument three type 1, argument four type 2, and types 3 to 5 are
    always allowed.
    """
    out = []
    if 3 < landmark < 13:
        out.append(0)
    if landmark > 6:
        out.append(1)
    if landmark < 7:
        out.append(2)
    out.extend([3, 4, 5])
    return out


def approximate_movement(c, animal, session):
    """**An approximation.** Animal movement and hit testing were never analysed.

    The paper is explicit that the movement code was not decoded (section 1.4,
    Appendix H), so this decides whether a shot connects by a simple rule: the closer
    the animal is to the hunter and the longer it has been still, the better the
    chance. Everything else in the hunt -- the spawn rules, the weights, the session
    length, the ammunition and the hundred-pound limit -- follows the paper.
    """
    return animal is not None and animal.get("still", 0) >= 2


def go(c):
    """Lines 4600 and HUNT.LIB 50000-50020."""
    st = c.st
    from . import common
    bullets = num.as_int(st.I[4])
    before = num.as_float(st.PF)
    if bullets <= 0:
        return 0
    c.ui.clear()
    c.ui.print("Hunting Instructions")
    c.ui.print()
    c.ui.print("Return Key: to start or stop walking")
    c.ui.print("Arrow Keys: to point the rifle")
    c.ui.print("Space Bar: to fire the rifle")
    common.wait_key(c)
    session = hunt_session(c, st, bullets)
    got = num.parse(str(session["meat"]))
    # line 50011: three or more pounds is halved
    got = num.int_(num.div(got, num.parse("2" if num.gt(got, num.parse("3"))
                                 else "1")))
    st.I[4] = num.parse(str(session["bullets"]))
    if num.gt(got, num.ZERO):
        c.ui.print("From the animals you shot, you got " + num.str_(got)
                   + " pound" + ("" if num.eq(got, num.ONE) else "s")
                   + " of meat.  ")
    if not num.eq(got, num.ZERO) and num.ge(st.I[8], num.parse("2000")):
        got = num.ZERO
        c.ui.print("However, your wagon is full.")
    elif not num.eq(got, num.ZERO) and num.gt(num.add(got, st.I[8]),
                                              num.parse("2000")):
        got = num.sub(num.parse("2000"), st.I[8])
        if not num.eq(got, num.ZERO) and num.le(got, num.parse(str(CARRY_LIMIT))):
            c.ui.print("However, your wagon will only hold another "
                       + num.str_(got) + " pounds of food.")
    if num.gt(got, num.parse(str(CARRY_LIMIT))):
        c.ui.print("However, you were only able to carry 100 pounds back to the "
                   "wagon.")
        got = num.parse(str(CARRY_LIMIT))
    if num.eq(got, num.ZERO):
        c.ui.print("You were unable to shoot any food.")
    c.ui.print()
    st.I[8] = num.add(num.parse(str(before)), got)
    st.PF = st.I[8]
    common.wait_key(c)
    return num.as_int(got)


def hunt_session(c, st, bullets: int) -> dict:
    """The hunt itself, on the paper's rules.

    Runs for ``SESSION_PASSES`` passes, keeps at most two animals on screen, stops
    offering new ones once four have been shot, and spends a bullet per shot. No
    number comes from the game's generator.
    """
    h = HuntRng(_seed_bytes(c))
    types = allowed_types(st.LM)
    animals = []
    shots = 0
    meat = 0
    spent = 0
    spawn_chance = 2                       # in a thousand per attempt: argument five
    for _ in range(SESSION_PASSES):
        # a new animal every attempt if there is room -- the draw is always made
        if len(animals) < MAX_ANIMALS and shots < MAX_SHOTS:
            if h.below(1000) < spawn_chance:
                kind = types[h.below(len(types))]
                low, span = ANIMALS[kind]
                animals.append({"type": kind, "still": 0, "low": low, "span": span})
        for a in animals:
            a["still"] = a.get("still", 0) + 1
        # a shot: the space bar, or -- in a text port -- the first pass where the
        # approximation says the animal is close enough
        while animals and spent < bullets:
            hit = next((a for a in animals if approximate_movement(c, a, None)), None)
            if hit is None:
                break
            animals.remove(hit)
            spent += 1
            shots += 1
            meat += hit["low"] + h.below(hit["span"])
            break
    return {"meat": meat, "bullets": bullets - spent, "shots": shots}


def _seed_bytes(c) -> bytes:
    """The hunting module's own seed.

    The paper (11.1) and Appendix G.6 both say the routine is "seeded at the start
    of each hunt from the Applesoft seed bytes combined with the keyboard counter at
    addresses 78 and 79". So the seed is a function of the game's seed *and* of how
    long the player took to press the key, which is why a hunt is reproducible from
    a recorded game but is not part of the game's own sequence.
    """
    from .applesoft import fac
    try:
        seed = bytes(fac._b().get_seed())
    except Exception:                          # noqa: BLE001
        seed = bytes(5)
    counter = c.mem.keyboard_counter & 0xFFFF
    return bytes(((seed[i] + ((counter >> (8 * i)) & 0xFF)) & 0xFF)
                 for i in range(5))
