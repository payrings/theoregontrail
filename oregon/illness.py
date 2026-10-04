"""OREGON TRAIL 10300 and TOMB.LIB 50000: falling ill and dying.

Line 10300 is reached two ways: as random event 3, whose daily chance is
``.01 + H / 1500`` -- one per cent at perfect health and 10.3 per cent at the cap of
139 -- and from line 3235 on any day when health went above 139 before the cap,
somewhere that is not a river crossing.

The routine draws a disease from the six at random, then a victim. If the victim is
already ill the member dies and the second disease is never named; otherwise the
disease is given for ten days. On a death ``TOMB.LIB`` caps health at 105, drops the
party size by one and swaps the dead member with the last living one, so the living
always occupy the first ``NP`` slots.
"""

from __future__ import annotations

from . import num
from .data import illnesses as ILL

__all__ = ["illness", "choose_victim", "die", "check_party"]


def choose_victim(c, tag: str = "11500 victim"):
    """Lines 11500-11505: pick the member who falls ill or dies.

    ``Z = INT (RND (1) * NP)`` and then the draw is shifted up by one, wrapping, and
    a zero -- the leader -- becomes one while anyone else is alive. So the leader
    cannot fall ill or die until the rest of the party is gone.
    """
    st = c.st
    np_ = num.as_int(st.NP)
    if np_ <= 0:
        return 0
    z = num.trunc(num.mul(c.rng.rnd1(tag), num.parse(str(np_))))
    z = (z + 1) if z < (np_ - 1) else 0
    while z < 0:
        z = 0
    if np_ > 1 and z == 0:
        z = 1
    return z


def illness(c):
    """Line 10300: a disease, and what it does to whoever draws it."""
    st = c.st
    from . import common
    st.HR = num.parse("20")
    disease = num.trunc(num.add(
        num.mul(c.rng.rnd1("10300 disease"), num.parse("6")), num.parse("3")))
    who = choose_victim(c)
    name = st.N[who]
    if not num.eq(st.H1[who], num.ZERO):
        # a second disease while the first is still running: the member dies and the
        # new disease is never named (paper section 1.5, Table 1)
        st.T[0] = name + " " + ILL.DEATH_SENTENCE
        common.message(c, st.T[0])
        st.H1[who] = num.parse("-1")
        die(c, who)
        return
    st.T[0] = name + " " + ILL.IL_NAMES[disease]
    common.message(c, st.T[0])
    st.H1[who] = num.parse(str(disease))
    st.H2[who] = num.parse("10")


def die(c, who: int):
    """Line 8000 and TOMB.LIB 50000-50005: the death.

    Health is brought down to 105 if it was higher, ``NP`` drops by one, and the dead
    member's entries are swapped with the last living one so the living stay in the
    first ``NP`` slots. When nobody is left the tombstone sequence runs.
    """
    st = c.st
    from . import common
    if num.gt(st.H, num.parse("105")):
        st.H = num.parse("105")
    np_ = num.as_int(st.NP)
    if np_ <= 0:
        return
    np_after = np_ - 1
    st.H1[who] = st.H1[np_after]
    # the corpse is marked -1. Negating zero gives zero, so this cannot be
    # `num.neg(num.ONE)`: the marker has to be a real minus one.
    st.H1[np_after] = num.parse("-1")
    st.H2[who] = st.H2[np_after]
    st.N[who], st.N[np_after] = st.N[np_after], st.N[who]
    st.NP = np_after
    # OREGON TRAIL 8000 is "GOSUB 50000 ... GOSUB 190: GOSUB 650: RETURN", so the
    # speed routine runs *after* the death handling -- and TOMB.LIB 50005 returns
    # only "IF NP", so with nobody left it never comes back. Running line 650
    # first would divide the clothing by NP = 0, which in Applesoft is error 10.
    if np_after <= 0:
        from . import tomb
        tomb.all_dead(c, who)
        return "DIED"
    from . import trail
    trail.speed(c)
    common.message(c, f"{st.N[np_after]} has died.")
    return "died"


def check_party(c):
    """``IF NP THEN RETURN``: whether anyone is left."""
    return num.as_int(c.st.NP) > 0
