"""CROSS.LIB: the crossing animation -- the numbers it spends, and nothing else.

Lines 50000 to 50110 of the listing draw random numbers only to place the water
marks on the screen. Those numbers change nothing at all, but they **advance the
generator**, so every draw the game makes after a river crossing is offset by
however many the animation spent. Appendix G.5 records the counts:

======================================  ==========================================
first half of the animation             106
then, for a successful crossing         122
then, for a failed float or a ferry      0
then, for a failed ford                 22 single draws, each followed by 2 more
======================================  ==========================================

So the total is 106 plus 122, or 106 plus 0, or 106 plus 22 groups of three.
That last reading is the natural one for "22 single draws each followed by 2
more", but the wording admits others; it is flagged in ``GAPS.md``.

There is no picture here, so :func:`animate` spends the numbers and returns. The
draws are tagged so a test can count them, and they go through the game's own
generator -- they must, or everything after the crossing diverges.

Where the calls belong, from the listing: ``RIVER.LIB`` 3500 appends ``CROSS.LIB``
and calls it *before* the crossing menu, so the first 106 are spent on every
river, and the rest only once the crossing has actually been attempted.
"""

from __future__ import annotations

__all__ = ["first_half", "tail", "animate", "FIRST_HALF", "SUCCESS_TAIL",
           "FAILED_FORD_GROUPS", "FORD_TAIL_PER_GROUP"]

FIRST_HALF = 106                  # every crossing
SUCCESS_TAIL = 122                # a crossing that ended with the party across
FAILED_FORD_TAIL = 22            # a ford that went wrong: groups, not a total
FORD_TAIL_PER_GROUP = 3            # one draw and then two more, per group


def _spend(c, count: int, tag: str):
    for i in range(count):
        c.rng.rnd1(f"{tag} {i}")


def first_half(c) -> int:
    """The 106 draws every crossing spends, before the menu is shown."""
    _spend(c, FIRST_HALF, "CROSS first half")
    return FIRST_HALF


def tail(c, outcome: str) -> int:
    """The draws after the crossing has been attempted.

    ``outcome`` is ``"success"``, ``"failed-ford"``, ``"failed-float"`` or
    ``"failed-ferry"``. A failed float or a lost ferry spends nothing at all here.
    """
    spent = 0
    if outcome == "success":
        _spend(c, SUCCESS_TAIL, "CROSS success tail")
        spent += SUCCESS_TAIL
    elif outcome == "failed-ford":
        for g in range(FAILED_FORD_TAIL):
            _spend(c, 1, f"CROSS failed ford {g} a")
            _spend(c, FORD_TAIL_PER_GROUP - 1, f"CROSS failed ford {g} b")
        spent += FAILED_FORD_TAIL * FORD_TAIL_PER_GROUP
    return spent


def animate(c, outcome: str = "start") -> int:
    """Both halves in one call: 106, then whatever ``outcome`` calls for.

    :func:`first_half` and :func:`tail` are what :mod:`oregon.river` uses, because
    the listing spends them at two different moments -- the first half when the
    river is shown and the tail once the outcome is known.
    """
    total = first_half(c)
    if outcome in ("start", None):
        return total
    return total + tail(c, outcome)