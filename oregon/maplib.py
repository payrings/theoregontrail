"""MAP.LIB: the route travelled.

Lines 50000-50015. The original draws the trail so far on the map picture from the
landmark history in ``Q(0 to Q1 - 1)``, plus the part of the current segment not yet
covered, and then waits for a key. The coordinates in Appendix E.5 are kept in
:mod:`oregon.data.landmarks`, so this draws the same route as text.
"""

from __future__ import annotations

from . import num
from .data import landmarks as L

__all__ = ["show", "coordinates"]

# MP%(landmark, 0 to 1): the x and y of each landmark on the map.
COORDINATES = {
    0: (245, 139), 1: (235, 136), 2: (226, 126), 3: (207, 122), 4: (185, 120),
    5: (170, 114), 6: (155, 100), 7: (143, 108), 8: (132, 117), 9: (134, 108),
    10: (124, 104), 11: (110, 101), 12: (93, 102), 13: (80, 87), 14: (70, 76),
    15: (69, 66), 16: (55, 71), 17: (45, 70),
}


def coordinates(landmark: int):
    return COORDINATES[landmark]


def show(c):
    """Lines 50000-50015, as a list of the landmarks already passed."""
    st = c.st
    from . import common
    c.ui.clear()
    c.ui.print("The Oregon Trail")
    c.ui.print()
    visited = []
    for i in range(0, max(1, min(st.Q1 - 1, 17))):
        n = st.Q[i]
        if n and n not in visited:
            visited.append(n)
    if st.LM not in visited:
        visited.append(st.LM)
    c.ui.print("You have been through:")
    for n in visited:
        c.ui.print("  " + L.LM_NAMES[n])
    c.ui.print()
    c.ui.print(f"Next landmark: {L.LM_NAMES[st.NM]}")
    c.ui.print(f"Miles to it:  {num.str_(st.D)}")
    c.ui.print(f"Miles travelled so far: {num.str_(st.M)}")
    common.wait_key(c)
    return visited
