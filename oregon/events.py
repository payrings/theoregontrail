"""OREGON TRAIL 10000 to 11400: the fifteen random events.

Each is one function, named for the number the listing gives it, and each draws
exactly what Appendix G.4 lists -- no more, no fewer, and including the draws whose
result is thrown away. Remember that Applesoft has no short-circuit: a draw on the
right of ``AND`` or ``OR`` happens whatever the left side says.
"""

from __future__ import annotations

from . import num
from .data import illnesses as ILL

__all__ = ["fire", "UndefStatementError", "EVENT_COUNT",
           "unreachable_event"]

#: line 3180 tests RE(0) to RE(14) -- fifteen events
EVENT_COUNT = 15

#: RE(2) is set to 0 at line 29001, so event 2 can never fire
unreachable_event = 2


# --------------------------------------------------------------------- 0
def event_0(c):
    """Line 10000: snow bound. Ten days is the most, one the least."""
    from . import trail
    trail.lose_days(c, "10000 snow bound days", 10, "Snow bound")


# --------------------------------------------------------------------- 1
def event_1(c):
    """Line 10100: a snakebite, but only when it is warm or hotter.

    ``IF TM > C2`` -- warm, hot or very hot -- then a member is bitten for ten days.
    In the cold the draw still happens, so the seed advances either way.
    """
    st = c.st
    from . import common
    if num.gt(st.TM, num.TWO):
        who = _victim(c)
        text = st.N[who] + " has " + ILL.IL_NAMES[ILL.SNAKEBITE] + "."
        common.message(c, text)
        st.H1[who] = num.parse(str(ILL.SNAKEBITE))
        st.H2[who] = num.parse("10")


def _victim(c):
    from . import illness
    return illness.choose_victim(c, "10100 snakebite victim")


# --------------------------------------------------------------------- 3
def event_3(c):
    """Line 10300: illness."""
    from . import illness
    illness.illness(c)


# --------------------------------------------------------------------- 4
def event_4(c):
    """Line 10400: a grave the party passes. Offered, then read if the player agrees."""
    from . import common, trail
    c.ui.print("You pass a gravesite.  Would you like to look closer? ")
    if common.yes_no(c) == "Y":
        from . import tomb
        tomb.read_grave(c)
    trail.find_grave(c)


# --------------------------------------------------------------------- 5
def event_5(c):
    """Line 10500: Indians help find food. Thirty pounds, and no other effect."""
    st = c.st
    from . import common
    st.PF = num.add(st.PF, num.parse("30"))
    common.message(c, "Indians help find food.")


# --------------------------------------------------------------------- 6
def event_6(c):
    """Line 10600: a severe storm.

    Nothing at all in cool or warm weather: ``IF TM = C2 OR TM = C3 THEN RETURN``,
    which happens before the days-lost draw, so in that weather this event costs no
    number at all. Below that a blizzard puts eight units of snow down and costs a
    day; above it a thunderstorm adds an inch of rain and costs a day.
    """
    st = c.st
    from . import trail
    if num.eq(st.TM, num.TWO) or num.eq(st.TM, num.parse("3")):
        return
    if num.lt(st.TM, num.TWO):
        st.AR = num.sub(st.AR, num.ONE)
        st.AS = num.add(st.AS, num.parse("8"))
        trail.lose_days(c, "10602 blizzard days", 1, "Severe blizzard")
    else:
        st.AR = num.add(st.AR, num.ONE)
        trail.lose_days(c, "10602 thunderstorm days", 1, "Severe thunderstorm")


# --------------------------------------------------------------------- 7
def event_7(c):
    """Line 10700: heavy fog past Fort Hall, a hail storm before it.

    Fog: ``Z = RND (1) > .5`` draws whether or not the party is delayed, and a
    further draw picks the days lost when it is. Hail: a message and nothing else, so
    no number is spent.
    """
    st = c.st
    from . import common, trail
    # LM is the landmark number, a plain integer
    if st.LM > 11 and num.lt(st.TM, num.parse("5")):
        # line 10700: the draw happens first, then ON Z + 1 chooses delay or not
        z = c.rng.below("10700 fog delay", num.HALF)
        if not z:
            common.message(c, "Heavy fog")
        else:
            trail.lose_days(c, "10700 fog days", 1, "Heavy fog")
    elif st.LM <= 11 and num.gt(st.TM, num.parse("4")):
        common.message(c, "Hail storm.")


# --------------------------------------------------------------------- 8
def event_8(c):
    """Line 10800: a breakdown, an injury, or a dead ox.

    A third of the time a wheel, an axle or a tongue breaks; the rest is a coin toss
    between a member breaking a limb and an ox being injured. An ox loses half, and
    the injury that brings the count to a whole number is reported as a death.
    """
    st = c.st
    from . import common, part, trail
    if c.rng.below("10800 part breaks", num.parse(".33")):
        st.B = num.trunc(num.add(
            num.mul(c.rng.rnd1("10800 which part"), num.parse("3")), num.parse("5")))
        part.broken_part(c)
        st.SD = 1
        trail.run_stopped_days(c)
        if not st.B:
            c.ui.print("")
        return
    if c.rng.below("10810 injury or ox", num.HALF):
        who = _victim(c)
        which = num.trunc(num.mul(c.rng.rnd1("10830 arm or leg"), num.parse("2")))
        # the broken arm's number is 0, and 0 means healthy: the injury has no effect
        # and it wipes any illness the member already had (paper section 13)
        st.H1[who] = num.parse(str(which))
        st.H2[who] = num.parse("30")
        common.message(c, st.N[who] + " has " + ILL.IL_NAMES[which] + ".")
        return
    st.I[2] = num.sub(st.I[2], num.HALF)
    # a second injury makes the count whole again, and is reported as a death
    word = "is injured." if not num.eq(st.I[2], num.int_(st.I[2])) else "has died."
    common.message(c, "One of the oxen " + word)
    trail.speed(c)


# --------------------------------------------------------------------- 9
def event_9(c):
    """Line 10900: lose the trail, or take the wrong one. One to five days."""
    from . import trail
    label = "Lose trail"
    if c.rng.below("10900 which message", num.HALF):
        label = "Wrong trail"
    trail.lose_days(c, "10900 lost trail days", 5, label)


# -------------------------------------------------------------------- 10
def event_10(c):
    """Line 11000: a rough trail, or one that cannot be passed.

    Rough adds ten to the day's hardship; impassible costs one to ten days.
    """
    from . import trail
    st = c.st
    from . import common
    if c.rng.below("11000 rough or impassible", num.HALF):
        common.message(c, "Rough trail")
        st.HR = num.parse("10")
        return
    trail.lose_days(c, "11010 impassible days", 10, "Impassible trail")


# -------------------------------------------------------------------- 11
def event_11(c):
    """Line 11100: wild fruit. Twenty pounds."""
    st = c.st
    from . import common
    st.PF = num.add(st.PF, num.parse("20"))
    common.message(c, "Find wild fruit.")


# -------------------------------------------------------------------- 12
def event_12(c):
    """Line 11200: a fire in the wagon, a member lost, or an ox that wanders off."""
    st = c.st
    from . import common, lf, trail
    which = num.trunc(num.mul(c.rng.rnd1("11200 which"), num.parse("3")))
    if which == 0:
        losses = lf.fire(c)
        common.message(c, "A fire in the wagon results in loss of:", losses)
        return
    if which == 1:
        who = _victim(c)
        st.T[0] = st.N[who] + " is lost"
        trail.lose_days(c, "11250 lost member days", 5, st.T[0])
        return
    trail.lose_days(c, "11275 stray ox days", 3, "Ox wanders off")


# -------------------------------------------------------------------- 13
def event_13(c):
    """Line 11300: an abandoned wagon, or a thief."""
    st = c.st
    from . import common, lf, trail
    if c.rng.below("11300 wagon or thief", num.HALF):
        found = lf.abandoned_wagon(c)
        common.message(c, "You find an abandoned wagon", found)
        trail.speed(c)
        return
    stolen = lf.thief(c)
    common.message(c, "A thief comes during the night and steals", stolen)
    trail.speed(c)


# -------------------------------------------------------------------- 14
def event_14(c):
    """Line 11400: bad water, very little water, or inadequate grass.

    Twenty per cent bad water costs twenty points of hardship, and of the rest half
    is very little water for ten. Inadequate grass has no effect at all.
    """
    st = c.st
    from . import common
    if c.rng.below("11400 bad water", num.parse(".2")):
        st.HR = num.parse("20")
        common.message(c, "Bad water")
        return
    if c.rng.below("11410 little water or grass", num.HALF):
        st.HR = num.parse("10")
        common.message(c, "Very little water")
        return
    common.message(c, "Inadequate grass")


def fire(c, which: int):
    """Dispatch one event, as line 3180's ON L8 + 1 GOSUB list does.

    The list names ``10200``, and the program has no such line: the listing jumps
    from 10105 to 10300. Line 29001 sets ``RE(2) = 0``, so the chance of reaching
    it is nil, but if it were ever reached the original would raise UNDEF'D
    STATEMENT rather than quietly do something else. That is what happens here.
    """
    if which == 2:
        raise UndefStatementError(
            "event 2 dispatches to 10200, which is not in the program: the "
            "original would raise UNDEF'D STATEMENT. RE(2) is 0 so it cannot "
            "be reached.")
    return _EVENTS[which](c)


class UndefStatementError(Exception):
    """Reached a GOSUB target that is not in the program."""


#: the ON list of line 3180, with 2 as the entry the program lacks
_EVENTS = [event_0, event_1, None, event_3, event_4, event_5, event_6, event_7,
           event_8, event_9, event_10, event_11, event_12, event_13, event_14]
