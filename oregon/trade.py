"""TRADE.LIB: meeting another emigrant.

Lines 50000-50260. An attempt always costs a day, which the caller sets. Four draws
are made -- the good wanted, the good offered, the exchange ratio and the refusal
test -- and a fifth for "He" or "She" when the player actually holds what is wanted.

The ratio is ``Z = ZX / (ZY * (1 + 1.2 * RND (1)))``, so it is the value of the
wanted good over the value of the offered one, made worse by a random factor between
1 and 2.2. If it is 1 or more the emigrant wants one unit and offers ``INT(Z)``;
below 1 he wants ``INT(1 / Z)`` and offers one. Bullets are priced per bullet here
and per box in the shops, which is the division and multiplication by twenty at lines
50011 and 50025, and a bullets-for-food offer is multiplied by fifty on both sides.

An offer is refused if the player cannot afford it -- and **if the trade is accepted
the player's holding of the wanted good is set to the rounded figure minus the amount
taken**, so trading oxen rounds 5.5 up to 6.
"""

from __future__ import annotations

from . import num
from .data import goods as G

__all__ = ["attempt"]


def attempt(c):
    """Lines 50000-50040."""
    st = c.st
    from . import common
    from .trail import speed
    c.ui.clear()
    c.ui.print("Your Supplies")
    show_supplies(c)
    x = c.rng.int_range("50010 good wanted", 7)
    y = c.rng.int_range("50010 good offered", 7)
    if y == x:
        y = (y + 1) % 7
    zx = unit_value(x)
    zy = unit_value(y)
    z = num.div(zx, num.mul(zy, num.add(num.ONE,
                                      num.mul(num.parse("1.2"),
                                              c.rng.rnd1("50011 exchange ratio")))))
    v = num.ONE
    f = num.int_(z)
    if num.lt(z, num.ONE):
        v = num.int_(num.div(num.ONE, z))
        f = num.ONE
    if (x == 2 and y == 6) or (y == 2 and x == 6):
        v = num.mul(v, num.parse("50"))
        f = num.mul(f, num.parse("50"))
    # line 50027: "IF RND (1) > .95 OR Z THEN" -- one draw, and no short-circuit, so
    # the draw is spent whether or not the limit is already exceeded
    over = _over_limit(st, y, f)
    refuse = num.gt(c.rng.rnd1("50027 refusal test"), num.parse(".95")) or over
    if refuse:
        c.ui.print("No one wants to")
        c.ui.print("trade with you today.")
        common.wait_key(c)
        return False
    # line 50011 sets the *scalar* Q to the rounded holding and line 50035 stores
    # Q - V back into the inventory, so an accepted trade rounds what the party
    # gives away to a whole number (paper 13). Q and Q() are different variables
    # (paper 2.5, rule b), so the map's history is untouched.
    st.Q = num.int_(num.add(st.I[x + 2], num.HALF))
    q = st.Q
    want = v
    give = f
    # line 50030: "I = F:L = X + 2:F = V: GOSUB 50250" -- the name is read at
    # X + 2, so x is the S$ index and the I$ index is x + 2
    word = _wording(x + 2, num.as_int(want))
    c.ui.print(f"You meet another emigrant who wants {num.str_(want)[1:]} {word}.  ")
    if num.lt(q, want):
        c.ui.print("You don't have this.")
        common.wait_key(c)
        return False
    # line 50031: He or She
    who = "He"
    if num.gt(c.rng.rnd1("50031 he or she"), num.parse(".67")):
        who = "She"
    # Line 50032 sets "L = Y + 2" and then GOSUB 50250, which reads "Z$ = I$(L)".
    # The inventory names are indexed 1 to 8, so the index is Y + 2 -- passing Y
    # picked up I$(0), which is empty, and the sentence came out as
    # "She will trade you 1 ." with nothing named. FINDINGS.md 19.8, seen in play.
    from .lf import _line
    offered = _line(0, give, y + 2)
    c.ui.print(f"{who} will trade you {offered}.")
    c.ui.print("Are you willing to trade? ")
    if common.yes_no(c) != "Y":
        return False
    st.I[y + 2] = num.add(st.I[y + 2], give)
    st.I[x + 2] = num.sub(q, want)
    show_supplies(c)
    speed(c)
    st.PF = st.I[8]
    return True


def unit_value(item: int) -> num.Fac:
    """Line 50011: ``ZX = VAL(S$(X,1)) / (1 + 19 * (X = 2))``.

    Ammunition's table price is $2 for twenty bullets, so the trader works in
    individual bullets at a tenth of a cent.
    """
    base = num.parse(str(G.PRICE[item]))
    if item == 2:
        return num.div(base, num.parse("20"))
    return base


def _over_limit(st, item: int, amount) -> bool:
    held = num.add(st.I[item + 2], amount)
    if item in (3, 4, 5):
        return num.gt(held, num.parse("3"))
    if item == 6:
        return num.gt(held, num.parse("2000"))
    if item == 0:
        return num.gt(held, num.parse("20"))
    return False


#: ``LF.LIB``/``FLOAT`` 50250, 50255 and 50260, which between them give every good its
#: name. ``I$`` is 1-based and ``I$(8)`` is "pounds of food", so the name is never
#: assembled by appending an "s" to a stem:
#:
#: * 50250 -- ``Z = (F = 1) * ((L = 8) + (L = 2) + (L = 3) + ("s" = RIGHT$(Z$,1)))``,
#:   and ``IF NOT Z THEN RETURN``. With ``F`` not 1 the name is used **unchanged**,
#:   which is how "pounds of food" and "wagon wheels" come out right.
#: * 50255 -- ``IF L <> 8 AND L <> 3 THEN Z$ = LEFT$(Z$, LEN (Z$) - 1 - (L = 2))``:
#:   the singular of anything else drops its trailing "s", and oxen lose two letters.
#: * 50260 -- ``Z = 6 - 2 * (L = 3)`` splits the name into a stem and a qualifier:
#:   "pound of food", "sets of clothing".
def _wording(item: int, n: int) -> str:
    """*item* is the ``I$`` index, 2 to 8; *n* is ``F``, the quantity."""
    from .data.text import I_NAMES
    name = I_NAMES[item]
    if n == 1:                                  # 50250's Z is true, so 50255/50260 run
        if item == 8:                           # "pounds of food" -> "pound of food"
            return "pound of food"
        if item == 3:                           # 50260: Z = 6 - 2 = 4, so LEFT$(Z$,3)
            return "set of clothing"             # & RIGHT$(Z$, 16 - 4)
        if item == 2:                           # 50255: LEN - 1 - 1
            return "ox"
        return name[:-1] if name.endswith("s") else name
    return name


def show_supplies(c):
    """Line 50050: the inventory, each line rounded to the nearest whole."""
    st = c.st
    for item in range(2, 9):
        held = num.int_(num.add(st.I[item], num.HALF))
        from .data import text as T
        c.ui.print(f"{T.I_NAMES[item]}".ljust(24) + num.str_(num.parse(str(held))).rjust(6))
