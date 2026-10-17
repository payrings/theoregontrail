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
    before = st.PF                          # Q = PF (line 50010)
    # Line 4600 runs HUNT.LIB whatever the ammunition: with none, the routine
    # refuses to fire and the hunt ends with "You were unable to shoot any food."
    gfx = c.ui.pictures
    prefix = "b_oregon" if num.as_int(st.S) else "oregon"
    if gfx:
        from .graphics import screens
        screens.hunt_instructions(c.ui, prefix)
    else:
        c.ui.clear()
        c.ui.print("Hunting Instructions")
        c.ui.print()
        c.ui.print("Return Key: to start or stop walking")
        c.ui.print("Arrow Keys: to point the rifle")
        c.ui.print("Space Bar: to fire the rifle")
    common.wait_key(c)
    if bullets <= 0:
        session = {"meat": 0, "bullets": 0}
    elif gfx and c.ui.assets.hunt():
        from .graphics import hunt_scene
        h = HuntRng(_seed_bytes(c))
        session = hunt_scene.play(c.ui, c.ui.assets.hunt(), bullets, h.below,
                                  allowed_types(st.LM), ANIMALS,
                                  getkey=getattr(c.ui, "hunt_key", None))
    elif gfx:
        from .graphics import hunt_field
        h = HuntRng(_seed_bytes(c))
        session = hunt_field.play(c.ui, bullets, h.below, h.below, allowed_types(st.LM),
                                  ANIMALS, SESSION_PASSES,
                                  getkey=getattr(c.ui, "hunt_key", None),
                                  pause=getattr(c.ui, "hunt_pause", 0.0))
    else:
        session = hunt_session(c, st, bullets)
    got = num.parse(str(session["meat"]))
    # line 50011: L = INT (L / (2 - (L < 3))) -- a bag of three or more is halved
    got = num.int_(num.div(got, num.sub(num.TWO, num.bool_(num.lt(got, num.THREE)))))
    st.I[4] = num.parse(str(session["bullets"]))
    said = []                               # PRINT ...; keeps going on the same line
    out = said.append if gfx else c.ui.print
    if num.gt(got, num.ZERO):
        out("From the animals you shot, you got " + num.str_(got)
                   + " pound" + ("" if num.eq(got, num.ONE) else "s")
                   + " of meat.  ")
    full = not num.eq(got, num.ZERO) and num.ge(st.I[8], num.parse("2000"))
    if full:
        # 50013 ends GOTO 50020, which skips the three lines that follow it
        got = num.ZERO
        out("However, your wagon is full.")
    else:
        if not num.eq(got, num.ZERO) and num.gt(num.add(got, st.I[8]),
                                                num.parse("2000")):
            got = num.sub(num.parse("2000"), st.I[8])
            if not num.eq(got, num.ZERO) and num.le(got, num.parse(str(CARRY_LIMIT))):
                out("However, your wagon will only hold another "
                           + num.str_(got) + " pounds of food.")
        if num.gt(got, num.parse(str(CARRY_LIMIT))):
            out("However, you were only able to carry 100 pounds back to the "
                "wagon.")
            got = num.parse(str(CARRY_LIMIT))
        if num.eq(got, num.ZERO):
            out("You were unable to shoot any food.")
    if not gfx:
        c.ui.print()
    st.I[8] = num.add(before, got)
    st.PF = st.I[8]
    if gfx:
        screens.hunt_result(c.ui, "".join(said), prefix)
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
    # The threshold is 4, halved to 2 by argument five (LSR/ROR at $E58D). The test
    # at $E161 compares the high byte of the draw first and then subtracts the
    # threshold from the low byte only, so an animal appears when the LOW BYTE of a
    # number from 0 to 999 is below the threshold: 8 values in 1,000 (16 unhalved).
    spawn_threshold = 2
    for _ in range(SESSION_PASSES):
        # a new animal every attempt if there is room -- the draw is always made
        if len(animals) < MAX_ANIMALS and shots < MAX_SHOTS:
            if (h.below(1000) & 0xFF) < spawn_threshold:
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
