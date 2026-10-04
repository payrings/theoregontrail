"""PACE.LIB: how hard the party travels.

Lines 50000-50070. Choosing a pace sets ``P`` and then calls line 650, which is what
recalculates the base speed. The three paces are 1 steady, 2 strenuous and 3
grueling, and the description screen explains what each costs.
"""

from __future__ import annotations

from . import num
from .data import text as T

__all__ = ["change", "DESCRIPTIONS"]

DESCRIPTIONS = [
    ("You travel about 8 hours a day, taking frequent rests.  You take care not to "
     "get too tired."),
    ("You travel about 12 hours a day, starting just after sunrise and stopping "
     "shortly before sunset.  You stop to rest only when necessary.  You finish each "
     "day feeling very tired."),
    ("You travel about 16 hours a day, starting before sunrise and continuing until "
     "dark.  You almost never stop to rest.  You do not get enough sleep at night.  "
     "You finish each day feeling absolutely exhausted, and your health suffers."),
]


def change(c):
    """Lines 50000-50030."""
    st = c.st
    from . import common, trail
    while True:
        c.ui.clear()
        c.ui.print("Change pace")
        c.ui.print(f'(currently "{T.PACE[num.as_int(st.P) - 1]}")')
        c.ui.print()
        c.ui.print("The pace at which you travel")
        c.ui.print("can change.  Your choices are:")
        c.ui.print()
        for i in range(1, 4):
            c.ui.print(f"{i}. a {T.PACE[i - 1]} pace")
        c.ui.print("4. find out what these different paces mean")
        c.ui.print()
        c.ui.print("What is your choice? ")
        a = c.ui.key("-14", 1, default="")
        if a == "4":
            describe(c)
            continue
        if a and a.isdigit() and a in "123":
            st.P = num.parse(str(len(a)))
            trail.speed(c)
            return num.as_int(st.P)


def describe(c):
    """Lines 50040-50070."""
    from . import common
    c.ui.clear()
    for i, text in enumerate(DESCRIPTIONS):
        c.ui.print(T.PACE[i] + " - " + text)
        c.ui.print()
    common.wait_key(c)
