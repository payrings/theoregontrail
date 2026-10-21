"""The climate table and the ``FN W`` lookup.

``WC$(0 to 5)`` holds six strings of 24 characters, one temperature code and one
rain code for each month. Line 105:

    DEF FN W(Z) = ( NOT Z + .003 * Z) * ( ASC( MID$(WC$(ZO), AM * 2 + Z - 1, 1)) - 30) - 20 * NOT Z

so ``FN W(0)`` is the month's minimum temperature, the temperature code minus 50,
and ``FN W(1)`` is the daily chance of rain, 0.003 times the rain code minus 30.
The sixth row is the Portland data, which the code never selects (paper section
13); it is kept so the table can be checked against Table 13 in full.
"""

__all__ = ["WC", "fn_w", "min_temp", "rain_chance"]

# The six strings exactly as stored in VAR.BIN, 24 characters each.
WC = [
    ';+?,I8V?_NiNnElFdHY<K1@-',   # 0
    '5#:#B(O3Y<c?i9g4].Q(C#9#',   # 1
    "5#9#>'H.R3\\+e(c$X'M'?%8#",   # 2
    '1#6%>*I5R7[+c&a#W)L,=&3$',   # 3
    "<-B+H+P*X*_'h!f!]$R(F+>,",   # 4
    'DWIGLBQ5W3[.`#`(]/T?LTG^',   # 5  -- the Portland row, never read
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
