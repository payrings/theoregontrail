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
from .data import goods as G
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
            x = num.trunc(num.add(
                num.mul(c.rng.rnd1(f"50000 fire amount {item}"), num.ONE), num.ZERO))
            st.I[item] = num.sub(held, x)
            losses.append(_line(z, x, item))
            z += 1
    held = st.PF
    if not held.is_zero() and c.rng.below("50010 fire food", num.HALF):
        x = num.trunc(num.add(num.mul(c.rng.rnd1("50010 fire food amount"),
                                      num.ONE), num.ZERO))
        x = num.trunc(num.add(num.mul(c.rng.rnd1("50010 fire food amount"), num.ONE),
                              num.ZERO))
        st.PF = num.sub(held, x)
        st.I[8] = st.PF
        losses.append(_line(z, x, 8))
        z += 1
    return losses


def abandoned_wagon(c):
    """Line 51000: an abandoned wagon, half empty.

    A coin toss for each of the same five items, and one to three of each -- except
    ammunition, which is twenty-one, forty-two or sixty-three. A spare part is only
    taken if the total stays within three.
    """
    st = c.st
    found = []
    z = 0
    for item in range(3, 8):
        if not c.rng.below(f"51010 found item {item}", num.HALF):
            continue
        x = c.rng.int_span(f"51010 amount {item}", 1, 3)
        if item == 4:                        # ammunition, in bullets
            x = x * 20
        if item >= 5 and num.as_float(num.add(st.I[item], num.parse(str(x)))) >= 4:
            continue                          # would go over the limit of three
        st.I[item] = num.add(st.I[item], num.parse(str(x)))
        found.append(_line(z, x, item))
        z += 1
    return found


def thief(c):
    """Line 52000: a thief in the night.

    One of four items -- oxen, clothing, bullets or food -- and one to a hundred, or
    the whole holding if that is less. The cash branch at line 52020 tests for item
    zero, but the item is only ever 2, 3, 4 or 8, so **the thief never takes any
    money**; the paper lists that in section 13 and it is reproduced. The message
    also lists ``T$(0)`` whether or not anything was taken, so an empty theft reads
    "...steals ." with nothing after it.
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
        most = 100 if num.gt(held, num.parse("100")) else held
        x = num.trunc(num.add(
            num.mul(c.rng.rnd1("52010 amount"), num.ONE), num.ZERO))
        st.I[item] = num.sub(held, x)
        if item == 8:
            st.PF = num.sub(st.PF, x)
        stolen.append(_line(z, x, item))
        z += 1
        if num.lt(st.I[item], num.ZERO):
            st.I[item] = num.ZERO
    st.T[0] = stolen[0] if stolen else ""
    return stolen


def _line(z: int, amount, item: int) -> str:
    """``T$(Z) = STR$(X) + " " + Z$`` with the wording of the goods table."""
    n = num.as_int(amount)
    word = T.I_NAMES[item]
    if item == 8:
        text = ("pound" if n == 1 else "pounds") + " of food"
    elif item == 3:
        text = ("set" if n == 1 else "sets") + " of clothing"
    elif item == 2:
        text = "ox" + ("en" if n != 1 else "")
    elif item == 4:
        text = "bullet" + ("s" if n != 1 else "")
    else:
        text = word + ("s" if n != 1 else "")
    return f"{n} {text}"
