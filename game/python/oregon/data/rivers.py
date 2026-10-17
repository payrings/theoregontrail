"""The four rivers, in the array ``RC``.

Four landmarks are river crossings: the Kansas (1), the Big Blue (2), the Green (9)
and the Snake (12). ``RC = (LM = 2) + 2 * (LM = 9) + 3 * (LM = 12)`` turns the
landmark into the row, so Kansas is 0, Big Blue 1, Green 2 and Snake 3.

Columns: 0 depth in feet, 1 width in feet, 2 swiftness, 3 the bottom
(0 smooth, 1 muddy, 2 rough), 4 unused, 5 the extra option
(0 none, 1 an Indian guide, 2 a ferry).

The depths are the point of the table. The Green is 20 feet and the Snake 6, so
neither can ever be forded; the wagon clears about 2.5 feet and supplies get wet
between 2.5 and 3 (paper section 9.3).
"""

__all__ = ["RC", "RC_RIVER_AT", "BOTTOM_NAMES", "smooth", "muddy", "rough",
           "current_conditions"]

#                depth  width  swift  bottom  unused  extra
RC = [
    [1, 600, 3, 0, 3, 2],      # 0 the Kansas River crossing, landmark 1
    [1, 220, 2, 1, 2, 0],      # 1 the Big Blue River crossing, landmark 2
    [20, 400, 5, 2, 12, 2],    # 2 the Green River crossing, landmark 9
    [6, 1000, 7, 2, 9, 1],     # 3 the Snake River crossing, landmark 12
]

RC_RIVER_AT = {1: 0, 2: 1, 9: 2, 12: 3}

BOTTOM_NAMES = ["smooth", "muddy", "rough"]

smooth, muddy, rough = 0, 1, 2

# The menu text, read by RIVER.LIB 50000 from its DATA statement at 51000. T$(0) and
# T$(1) are always offered; T$(2) is "wait", T$(3) is "more information", T$(4) is
# "hire an Indian to help" and T$(5) is "take a ferry across".
T = [
    "attempt to ford the river",
    "caulk wagon and float it across",
    "wait to see if conditions improve",
    "get more information",
    "hire an Indian to help",
    "take a ferry across",
]


def current_conditions(river: int, rain):
    """Line 50150, in ``Fac`` arithmetic -- see :func:`oregon.trail.river_conditions`.

    ``RD = INT ((RC(RC,0) + AR * 2) * 10 + .5) / 10``   depth, to one decimal
    ``RW = INT (RC(RC,1) + 15 * AR)``                    width
    ``RS = RC(RC,2) + AR``                               swiftness
    """
    return (river, rain)
