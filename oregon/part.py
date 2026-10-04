"""PART.LIB: the broken wagon part.

Lines 42000 to 42100. The part is 5, 6 or 7 -- a wheel, an axle or a tongue, which is
the index into the inventory -- and the player is offered the chance to repair it. The
repair succeeds half the time.

**The draw at line 42010 happens whether or not the player agreed to try.**
``IF (Z$ = "Y") AND (RND (1) < .5) THEN`` has no short-circuit in Applesoft, so the
number is spent either way; Appendix G.4 records exactly that.

If the repair fails, a spare part is used. With none left the player must trade for
one, and ``B`` stays set so the action menu keeps explaining that.
"""

from __future__ import annotations

from . import num
from .data import goods as G

__all__ = ["broken_part"]


def broken_part(c):
    """Lines 42000-42100."""
    st = c.st
    from . import common
    item = num.as_int(st.B)
    part = G.UNIT[item - 2]
    c.ui.print(f"Broken wagon {part}.  Would you like to try to repair it? ")
    yes = common.yes_no(c) == "Y"
    # the draw is made either way: Applesoft evaluates both sides of the AND
    if yes and c.rng.below("42010 repair succeeds", num.HALF):
        c.ui.print(f"You were able to repair the wagon {part}.")
        common.wait_key(c)
        return "repaired"
    c.ui.print("You " + ("were unable to" if yes else "did not")
               + f" repair the broken wagon {part}.")
    held = st.I[item]
    if not held.is_zero():
        st.I[item] = num.sub(held, num.ONE)
        c.ui.print(f"You must replace it with a spare part.")
        common.wait_key(c)
        return "replaced"
    c.ui.print(f"Since you don't have a spare {part}, you must trade for one.")
    common.wait_key(c)
    return "none"
