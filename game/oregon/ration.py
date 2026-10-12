"""RATION.LIB: how much the party eats.

Lines 50000-50040. Choosing rations sets ``R`` and calls line 650, which sets ``FC``,
the pounds a day: ``FC = NP * (4 - R)``, so three a head on filling, two on meager
and one on bare bones.
"""

from __future__ import annotations

from . import num
from .data import text as T

__all__ = ["change", "DESCRIPTIONS"]

DESCRIPTIONS = [
    "meals are large and generous.",
    "meals are small, but adequate.",
    "meals are very small; everyone stays hungry.",
]


def change(c):
    """Lines 50000-50040."""
    st = c.st
    from . import trail
    c.ui.clear()
    c.ui.print("Change food rations")
    c.ui.print(f'(currently "{T.RATIONS[num.as_int(st.R) - 1]}")')
    c.ui.print()
    c.ui.print("The amount of food the people in your party eat each day can "
               "change.  These amounts are:")
    c.ui.print()
    for i in range(1, 4):
        c.ui.print(f"{i}. {T.RATIONS[i - 1]} - {DESCRIPTIONS[i - 1]}")
    c.ui.print()
    c.ui.print("What is your choice? ")
    a = c.ui.key("-13", 1, default="")
    # 50040: "Z = LEN(Z$): R = Z * VAL(Z$) + R * NOT Z: ... GOSUB 650: RETURN".
    # A digit was entered, so this is VAL(Z$); with nothing typed, Z is 0 and R
    # survives. GOSUB 650 runs whatever the answer was.
    if a:
        st.R = num.parse(a)
    trail.speed(c)
    return num.as_int(st.R)
