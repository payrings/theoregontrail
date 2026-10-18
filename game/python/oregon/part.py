"""PART.LIB: the broken wagon part.

Lines 42000 to 42100. The part is 5, 6 or 7 -- a wheel, an axle or a tongue, which is
the index into the inventory -- and the player is offered the chance to repair it. The
repair succeeds half the time.

**The draw at line 42010 happens whether or not the player agreed to try.**
``IF (Z$ = "Y") AND (RND (1) < .5) THEN`` has no short-circuit in Applesoft, so the
number is spent either way; Appendix F.4 records exactly that.

If the repair fails, a spare part is used. With none left the player must trade for
one, and ``B`` stays set so the action menu keeps explaining that.

Both other endings go through line 42100, ``GOSUB 400: GOSUB 30000:
B = (PEEK (-16384) = 13)``, which **assigns** ``B``: it becomes 0 (or 1 when the key
last pressed was Return), so the wagon can go on. Only the third ending, with no
spare, skips that line and leaves ``B`` at the part's number.
"""

from __future__ import annotations

from . import num
from .data import goods as G

__all__ = ["broken_part"]


def _clear_b(c):
    """Line 42100: ``GOSUB 400: GOSUB 30000: B = (PEEK (-16384) = 13)``."""
    from . import common
    key = common.wait_key(c)
    c.st.B = 1 if key in ("\r", "\n") else 0


def broken_part(c):
    """Lines 42000-42100."""
    st = c.st
    from . import common
    item = num.as_int(st.B)
    part = G.UNIT[item - 2]
    gfx = c.ui.pictures
    if gfx:
        from . import trail
        from .graphics import screens
        trail.scene(c, prompt=False, pictures=[("part_04", 185, 29)])     # 42000: & IMAGE,4,185,29
        screens.part_box(c.ui, f"Broken wagon {part}.  Would you like to try to repair it? ")
    else:
        c.ui.print(f"Broken wagon {part}.  Would you like to try to repair it? ")
    yes = common.yes_no(c) == "Y"
    # the draw is made either way: Applesoft evaluates both sides of the AND
    repair_roll = c.rng.below("42010 repair succeeds", num.HALF)
    if gfx:
        _say = lambda text: screens.part_text(c.ui, text)
    else:
        _say = c.ui.print
    if yes and repair_roll:
        _say(f"You were able to repair the wagon {part}.")
        _clear_b(c)
        return "repaired"
    # line 42030 prints both sentences in one PRINT
    said = "You " + ("were unable to" if yes else "did not") \
        + f" repair the broken wagon {part}."
    held = st.I[item]
    if not held.is_zero():
        st.I[item] = num.sub(held, num.ONE)
        _say(said + "  You must replace it with a spare part.")
        _clear_b(c)
        return "replaced"
    # the sentence about a spare part is printed before the test for one (line
    # 42030 prints, then "Z = I(B): IF Z THEN ..."), so it appears with none too;
    # 42040 then waits for a key, says why, and waits again
    _say(said + "  You must replace it with a spare part.")
    common.wait_key(c)
    _say(f"Since you don't have a spare {part}, you must trade for one.")
    common.wait_key(c)
    return "none"
