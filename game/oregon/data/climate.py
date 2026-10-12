"""The climate table and the ``FN W`` lookup.

``WC$(0 to 5)`` holds six strings of 24 characters, one temperature code and one
rain code for each month. Line 105:

    DEF FN W(Z) = ( NOT Z + .003 * Z) * ( ASC( MID$(WC$(ZO), AM * 2 + Z - 1, 1)) - 30) - 20 * NOT Z

so ``FN W(0)`` is the month's minimum temperature, the temperature code minus 50,
and ``FN W(1)`` is the daily chance of rain, 0.003 times the rain code minus 30.
The sixth row is the Portland data, which the code never selects (paper section
13); it is kept so the table can be checked against Table 13 in full.
"""

__all__ = ["WC", "AM_CODES", "RAIN_CODES", "fn_w", "min_temp", "rain_chance"]

# The six strings exactly as stored in VAR.BIN, 24 characters each.
WC = [
    ';+?,I8V?_NiNnElFdHY<K1@-',   # 0
    '5#:#B(O3Y<c?i9g4].Q(C#9#',   # 1
    "5#9#>'H.R3\\+e(c$X'M'?%8#",   # 2
    '1#6%>*I5R7[+c&a#W)L,=&3$',   # 3
    "<-B+H+P*X*_'h!f!]$R(F+>,",   # 4
    'DWIGLBQ5W3[.`#`(]/T?LTG^',   # 5  -- the Portland row, never read
]

# The same table as codes, which is how the paper prints it (Table 13). Kept
# separately so the test can check the strings against it without re-deriving.
AM_CODES = [
    [59, 63, 73, 86, 95, 105, 110, 108, 100, 89, 75, 64],
    [53, 58, 66, 79, 89, 99, 105, 103, 93, 81, 67, 57],
    [53, 57, 62, 72, 82, 92, 101, 99, 88, 77, 63, 56],
    [49, 54, 62, 73, 82, 91, 99, 97, 87, 76, 61, 51],
    [60, 66, 72, 80, 88, 95, 104, 102, 93, 82, 70, 62],
    [68, 73, 76, 81, 87, 91, 96, 96, 93, 84, 76, 71],
]
RAIN_CODES = [
    [43, 44, 56, 63, 78, 78, 69, 70, 72, 60, 49, 45],
    [35, 35, 40, 51, 60, 63, 57, 52, 46, 40, 35, 35],
    [35, 35, 39, 46, 51, 43, 40, 36, 39, 39, 37, 35],
    [35, 37, 42, 53, 55, 43, 38, 35, 41, 44, 38, 36],
    [45, 43, 43, 42, 42, 39, 33, 33, 36, 40, 43, 44],
    [87, 71, 66, 53, 51, 46, 35, 40, 47, 63, 84, 94],
]


def fn_w(zone: int, month: int, which: int):
    """``FN W(Z)``: 0 for the minimum temperature, 1 for the rain chance.

    Kept here as plain integers because it is only used to build the data and to
    check it; the game's own copy lives in :mod:`oregon.trail` and works in
    ``Fac``, because that is what the arithmetic has to be done in.
    """
    ch = ord(WC[zone][month * 2 + which - 2])
    if which == 0:
        return (1 + 0.0) * (ch - 30) - 20
    return 0.003 * (ch - 30)


def min_temp(zone: int, month: int) -> int:
    return fn_w(zone, month, 0)


def rain_chance(zone: int, month: int) -> float:
    return fn_w(zone, month, 1)
