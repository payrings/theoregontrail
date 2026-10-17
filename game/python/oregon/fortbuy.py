"""BUY.LIB: buying at a fort.

Lines 50000-50035. The same seven goods as the store, at the same base prices, but
each one rises by a quarter for every step along the trail:

    Q = (LM > 2) + (LM > 4) + (LM > 7) + (LM > 10) + (LM > 12) + (LM > 13)

so Fort Kearney (``Q`` = 1) is 1.25 times the store price and the last forts
(``Q`` = 6) two and a half times. A purchase is refused if it cannot be afforded, or if it would take the
wagon over 20 oxen, 2000 pounds of food or 3 of a spare part. Ammunition is bought in
boxes of twenty -- ``K = 1 + 19 * (L = 3)`` -- and the cost is taken without rounding.
"""

from __future__ import annotations

from . import num
from .data import goods as G
from .data import text as T
from .ui import ALLOWED

__all__ = ["fort_store", "price", "tier", "purchase", "affordable", "too_dear"]

TIER_CUTS = (2, 4, 7, 10, 12, 13)


def tier(landmark: int) -> int:
    """Line 50003: how far along the trail this fort is."""
    return sum(1 for cut in TIER_CUTS if landmark > cut)


def price(item: int, q: int) -> num.Fac:
    """Line 50025: ``V = VAL(S$(L-1,1)): V = V + .25 * Q * V``.

    ``V`` is a variable, so both the price from the table and the marked-up price
    are stored values.
    """
    base = num.store(num.parse(str(G.PRICE[item])))
    return num.store(num.add(base, num.mul(num.mul(num.parse(".25"),
                                                   num.parse(str(q))), base)))


def fort_store(c):
    """Lines 50000-50035."""
    st = c.st
    from . import common
    # line 50003 sets the scalar Q to the fort's tier. Q and Q() are different
    # variables (paper 2.5, rule b), so the map's landmark history is untouched.
    st.Q = num.parse(str(tier(st.LM)))
    q = num.as_int(st.Q)
    pictures = c.ui.pictures
    if not pictures:
        c.ui.clear()
    # 50000: the fort's name, LM$(LM,0), and the date, TD$
    from .data import landmarks as L
    if not pictures:
        c.ui.print(L.LM_NAMES[st.LM])
        c.ui.print(common.date_text(c))
        c.ui.print()
        c.ui.print("You may buy:")
        c.ui.print()
        for i in range(7):
            c.ui.print(f"  {i + 1}. {G.NAME[i]}")
        c.ui.print("  8. Leave store")
        c.ui.print()
        for i in range(7):
            p = price(i, q)
            # 50005: PRINT RIGHT$ (" " + K$, 5)" per "S$(L,2) -- no dollar sign
            c.ui.print((" " + common.money(c, p))[-5:] + " per " + G.UNIT[i])
    first = True
    while True:
        if pictures:
            from .graphics import screens
            if first:
                goods = [(G.NAME[i], common.money(c, price(i, q)), G.UNIT[i]) for i in range(7)]
                screens.fort_list(c.ui, L.LM_NAMES[st.LM], common.date_text(c), goods,
                                  common.money(c, st.MY))
                first = False
            else:
                _ask(c)
        else:
            c.ui.clear()
            c.ui.print(f"You have {common.dollar_text(c, st.MY)} to spend.")
            c.ui.print("Which number? ")
        a = c.ui.key(ALLOWED["FORT"], 1, default="8")   # 50010: & INP,1,"-18"
        item = (int(a) if a and a.isdigit() else 8) - 1
        if item == 7:
            st.PF = st.I[8]
            return
        p = price(item, q)
        # line 50015: is one affordable?
        if not affordable(c, item, 1, p, q, ""):
            continue
        c.ui.print("How many " + G.UNIT[item] + G.PLURAL[item] + "? ")
        want = c.ui.key(ALLOWED["STORE_PART"] if item in (3, 4, 5)
                        else ALLOWED["STORE_FOOD"], 3 + (1 if item == 6 else 0),
                        default="1")
        n = int(want) if want and want.isdigit() else 0
        if not affordable(c, item, n, p, q, " many"):
            continue
        purchase(st, item, n, p)
        # Line 50025 ends GOTO 50010 and BUY.LIB has no GOSUB 650, so the speed is
        # not worked out again here; it keeps its old value until the next time the
        # speed routine runs.


def _ask(c):
    """The prompt window under the list, drawn again for each purchase."""
    from . import common
    ui = c.ui
    y = getattr(ui, "prompt_y", 150)
    ui.box(0, y, 279, 191, 0)
    ui.dfw(0, y, 279, 191 - y)
    ui.co(0, 0)
    ui.print(f"You have {common.dollar_text(c, c.st.MY)} to spend.")
    ui.print("Which number? ")


def purchase(st, item: int, n: int, p):
    """Line 50025: ``MY = MY - Z * V: I(L + 1) = I(L + 1) + Z * K``.

    ``K`` is 20 for ammunition, which is sold in boxes of twenty, and 1 otherwise.
    """
    k = 20 if item == 2 else 1
    st.MY = num.sub(st.MY, num.mul(num.parse(str(n)), p))
    st.I[item + 2] = num.add(st.I[item + 2], num.parse(str(n * k)))


def too_dear(st, n: int, p) -> bool:
    """Line 50026: ``T = 0: IF (Z * V) > MY + .001 THEN T = 1``.

    The cost is not stored (it is the left operand of the comparison, so it is
    rounded), while ``MY + .001`` is the live right operand.
    """
    cost = num.mul(num.parse(str(n)), p)
    return num.gt(cost, num.add(st.MY, num.parse(".001")))


def affordable(c, item: int, n: int, p, q: int, many: str = "") -> bool:
    """Lines 50030-50033: the four refusals.

    ``IF (Z * V) > MY + .001`` is the affordability test -- with the .001 so that a
    price like 0.2 times an odd number is not refused through a rounding artefact.
    The first check is of one unit and says "You cannot afford that."; the second is
    of the number asked for and says "You cannot afford that many." (``A$``).
    """
    st = c.st
    from . import common
    if too_dear(st, n, p):
        c.ui.print("You cannot afford that" + many + ".")
        common.wait_key(c)
        return False
    held = st.I[item + 2]
    if item == 0 and num.gt(num.add(held, num.parse(str(n))), num.parse("20")):
        c.ui.print("You may only take 20 oxen.")
        common.wait_key(c)
        return False
    if item == 6 and num.gt(num.add(held, num.parse(str(n))), num.parse("2000")):
        c.ui.print("Your wagon may only carry 2000 pounds of food.")
        common.wait_key(c)
        return False
    if item in (3, 4, 5) and num.gt(num.add(held, num.parse(str(n))), num.parse("3")):
        c.ui.print(f"Your wagon may only carry 3 {T.I_NAMES[item + 2]}.")
        common.wait_key(c)
        return False
    return True
