"""BUY.LIB: buying at a fort.

Lines 50000-50035. The same seven goods as the store, at the same base prices, but
each one rises by a quarter for every step along the trail:

    Q = (LM > 2) + (LM > 4) + (LM > 7) + (LM > 10) + (LM > 12) + (LM > 13)

so Fort Kearney is one and a half times the store price and Fort Walla Walla two and
a half times. A purchase is refused if it cannot be afforded, or if it would take the
wagon over 20 oxen, 2000 pounds of food or 3 of a spare part. Ammunition is bought in
boxes of twenty -- ``K = 1 + 19 * (L = 3)`` -- and the cost is taken without rounding.
"""

from __future__ import annotations

from . import num
from .data import goods as G
from .ui import ALLOWED

__all__ = ["fort_store", "price", "tier"]

TIER_CUTS = (2, 4, 7, 10, 12, 13)


def tier(landmark: int) -> int:
    """Line 50003: how far along the trail this fort is."""
    return sum(1 for cut in TIER_CUTS if landmark > cut)


def price(item: int, q: int) -> num.Fac:
    """Line 50025: ``V = VAL(S$(L-1,1)): V = V + .25 * Q * V``."""
    base = num.parse(str(G.PRICE[item]))
    return num.add(base, num.mul(num.mul(num.parse(".25"), num.parse(str(q))), base))


def fort_store(c):
    """Lines 50000-50035."""
    st = c.st
    from . import common
    q = tier(st.LM)
    c.ui.clear()
    c.ui.print("You may buy:")
    c.ui.print()
    for i in range(7):
        c.ui.print(f"  {i + 1}. {G.NAME[i]}")
    c.ui.print("  8. Leave store")
    c.ui.print()
    for i in range(7):
        p = price(i, q)
        c.ui.print(f"  {common.dollar_text(c, p)} per {G.UNIT[i]}")
    while True:
        c.ui.clear()
        c.ui.print(f"You have {common.dollar_text(c, st.MY)} to spend.")
        c.ui.print("Which number? ")
        a = c.ui.key(ALLOWED["FORT"], 2, default="8")
        item = (int(a) if a and a.isdigit() else 8) - 1
        if item == 7:
            st.PF = st.I[8]
            return
        p = price(item, q)
        # line 50015: is one affordable?
        if not affordable(c, item, 1, p, q):
            continue
        c.ui.print("How many " + G.UNIT[item] + G.PLURAL[item] + "? ")
        want = c.ui.key(ALLOWED["STORE_PART"] if item in (3, 4, 5)
                        else ALLOWED["STORE_FOOD"], 3 + (1 if item == 6 else 0),
                        default="1")
        n = int(want) if want and want.isdigit() else 0
        if not affordable(c, item, n, p, q):
            continue
        k = 1
        if item == 2:
            k = 20                       # ammunition, in bullets
        st.MY = num.sub(st.MY, num.mul(num.parse(str(n)), p))
        st.I[item + 2] = num.add(st.I[item + 2], num.parse(str(n * k)))
        from . import trail
        trail.speed(c)


def affordable(c, item: int, n: int, p, q: int) -> bool:
    """Lines 50030-50033: the four refusals.

    ``IF (Z * V) > MY + .001`` is the affordability test -- with the .001 so that a
    price like 0.2 times an odd number is not refused through a rounding artefact.
    """
    st = c.st
    from . import common
    cost = num.mul(num.parse(str(n)), p)
    if num.gt(cost, num.add(st.MY, num.parse(".001"))):
        c.ui.print("You cannot afford that.")
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
        c.ui.print(f"Your wagon may only carry 3 {G.UNIT[item]}.")
        common.wait_key(c)
        return False
    return True
