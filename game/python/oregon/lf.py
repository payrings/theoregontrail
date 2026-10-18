"""LF.LIB: fire, the abandoned wagon and the thief.

Lines 50000 to 53000. All three work the same way: they walk the goods, draw once
for each, and record what was lost or found in ``T$(0 to 10)``, which the caller
prints under the message.

The draws matter. ``IF RND (1) < .5 AND YY`` in the fire is **not** short-circuited,
so a draw happens for each of the five goods whether or not any of them is held, and
a second draw for the amount only when something is actually lost.
"""

from __future__ import annotations

from . import num
from .data import text as T

__all__ = ["fire", "abandoned_wagon", "thief", "pluralise"]


def pluralise(count: int, singular: str, plural_ending: str) -> str:
    """Lines 50250 and 53000: the wording of a loss line.

    One of the singular is plural, one is singular, and the rest take the table's
    plural ending; ``pounds of food`` and ``sets of clothing`` are both handled by
    taking the last character off and putting it back, which is what the BASIC does.
    """
    if count != 1:
        return singular + plural_ending
    return singular


def fire(c):
    """Line 50000: a fire in the wagon.

    Each of clothing, bullets, the three spare parts and then the food is a coin
    toss, and a loss is a random amount from 1 up to all of it.
    """
    st = c.st
    losses = []
    z = 0
    for item in range(3, 8):
        held = st.I[item]
        # no short-circuit: the draw happens even when nothing is held
        if c.rng.below(f"50000 fire item {item}", num.HALF) and not held.is_zero():
            # 50000: X = INT (RND (1) * YY + 1), YY the amount held -- one to all
            x = num.int_(num.add(
                num.mul(c.rng.rnd1(f"50000 fire amount {item}"), held), num.ONE))
            st.I[item] = num.sub(held, x)
            losses.append(_line(z, x, item))
            st.T[z] = losses[-1]                  # 53000: T$(Z) = STR$(X) + " " + Z$
            z += 1
    held = st.PF
    # not short-circuited: 50010 is "IF YY AND RND (1) < .5", so the coin-flip draw
    # happens even when no food is held
    if c.rng.below("50010 fire food", num.HALF) and not held.is_zero():
        # one draw for the amount: Appendix F.4 lists exactly one here, and this
        # line once drew twice, which shifted every later number in the game
        x = num.int_(num.add(
            num.mul(c.rng.rnd1("50010 fire food amount"), held), num.ONE))
        st.PF = num.sub(held, x)
        st.I[8] = st.PF
        losses.append(_line(z, x, 8))
        st.T[z] = losses[-1]
        z += 1
    return losses


def abandoned_wagon(c):
    """Line 51000: an abandoned wagon, half empty.

    A coin toss for each of the same five items, and one to three of each -- except
    ammunition, which is twenty-one, forty-two or sixty-three: line 51010 is
    ``X = X + X * (Y = 4) * 20``, the amount plus twenty times it. A spare part is
    only taken if the total stays within three.
    """
    st = c.st
    found = []
    z = 0
    for item in range(3, 8):
        if not c.rng.below(f"51010 found item {item}", num.HALF):
            continue
        # X = INT (RND (1) * 3 + 1), then X = X + X * (Y = 4) * 20
        x = num.int_(num.add(num.mul(c.rng.rnd1(f"51010 amount {item}"),
                                     num.parse("3")), num.ONE))
        if item == 4:                        # ammunition, in bullets
            x = num.add(x, num.mul(num.mul(x, num.ONE), num.parse("20")))
        # IF Y < 5 OR (I(Y) + X < 4): the spare parts are taken only up to three
        if item >= 5 and not num.lt(num.add(st.I[item], x), num.parse("4")):
            continue                          # would go over the limit of three
        st.I[item] = num.add(st.I[item], x)
        found.append(_line(z, num.as_int(x), item))
        st.T[z] = found[-1]
        z += 1
    return found


def thief(c):
    """Line 52000: a thief in the night.

    One of four items -- oxen, clothing, bullets or food -- and one to a hundred, or
    the whole holding if that is less. The cash branch at line 52020 tests for item
    zero, but the item is only ever 2, 3, 4 or 8, so **the thief never takes any
    money**; the paper lists that in section 13 and it is reproduced. Line 52030
    builds one sentence, ``A$ + " " + T$(0) + "."``, and clears ``T$(0)``; line 11330
    shows it only ``IF Z``, so an empty theft shows no message at all. Returns the
    sentence in a list, or an empty list.
    """
    st = c.st
    st.I[8] = st.PF
    stolen = []
    z = 0
    item = c.rng.int_span("52000 which item", 2, 5)
    if item == 5:
        item = 8                            # the BASIC adds three to a five
    held = st.I[item]
    if not held.is_zero():
        # 52010: X = 100 * (YY > 100) + YY * (YY < 101) -- the holding capped at
        # 100 -- then X = INT (RND (1) * X + 1), one to the cap
        # the formula as written: for a holding between 100 and 101 both terms count
        most = num.store(num.add(
            num.mul(num.parse("100"), num.bool_(num.gt(held, num.parse("100")))),
            num.mul(held, num.bool_(num.lt(held, num.parse("101"))))))
        x = num.int_(num.add(
            num.mul(c.rng.rnd1("52010 amount"), most), num.ONE))
        st.I[item] = num.sub(held, x)
        if item == 8:
            st.PF = num.sub(st.PF, x)
        stolen.append(_line(z, x, item))
        st.T[z] = stolen[-1]
        z += 1
        if num.lt(st.I[item], num.ZERO):
            st.I[item] = num.ZERO
    # 52030: A$ = A$ + " " + T$(0) + ".": T$(0) = "". The sentence is shown only
    # when something was taken (11330: IF Z THEN ... GOSUB 900)
    shown = ["A thief comes during the night and steals " + st.T[0] + "."] if z else []
    st.T[0] = ""
    return shown


def _line(z: int, amount, item: int) -> str:
    """``T$(Z) = STR$(X) + " " + Z$`` with the wording of 50250, 50255 and 50260.

    *item* is the ``I$`` index, 2 to 8. The wording is not "stem plus s": 50250 returns
    immediately unless the quantity is 1, so a plural keeps the name as it stands --
    "pounds of food", "wagon wheels" -- and only the singular is rewritten. Getting
    that wrong produced "1 wagon wheels" and "3 wagon wheelss". The rules live in :func:`oregon.trade._wording`, which this shares.
    """
    from .trade import _wording
    return f"{num.as_int(amount)} {_wording(item, num.as_int(amount))}"
