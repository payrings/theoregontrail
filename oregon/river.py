"""RIVER.LIB: crossing the river.

Lines 50000 to 50260. Four landmarks are rivers and each has its own depth, width,
swiftness and bottom. The current depth rises with the accumulated rain, so waiting
at the river can make it worse, and the whole routine is re-read every time the menu
is drawn (line 50150).

The five ways across are:

* **ford**, safe under 2.5 feet on a smooth bottom; muddy, a four in ten chance of
  sticking for a day; rough, a sixteen in one hundred chance of tipping, and then each
  good lost with the same chance for all of them;
* **caulk and float**, refused under 1.5 feet, costs a day, and above 2.5 feet the
  wagon tips with a chance of swiftness in twenty;
* **ferry**, refused under 2.5 feet, $5 and two to six days' wait;
* **an Indian guide**, 2 or 3 sets of clothing, and every risk divided by five;
* **wait**, one stopped day, and then the menu again.

The Green's depth of 20 feet and the Snake's of 6 mean neither can ever be forded.
"""

from __future__ import annotations

from . import num
from .data import landmarks as L
from .data import rivers as R
from .data import text as T
from .ui import ALLOWED

__all__ = ["crossing", "conditions", "losses"]

# T$(0 to 5), read from the DATA statement at line 51000
TXT = R.T


def conditions(c):
    """Line 50150: the river as it is now.

    ``RD = INT ((RC(RC,0) + AR * 2) * 10 + .5) / 10`` gives the depth to one
    decimal; the width gains fifteen feet a unit of rain and the swiftness one.
    """
    st = c.st
    row = R.RC[st.RC]
    st.RD = num.store(num.div(
        num.int_(num.add(num.mul(num.add(num.parse(str(row[0])),
                                      num.mul(st.AR, num.parse("2"))),
                             num.parse("10")),
                         num.parse(".5"))), num.parse("10")))
    st.RW = num.int_(num.add(num.parse(str(row[1])),
                             num.mul(num.parse("15"), st.AR)))
    st.RS = num.add(num.parse(str(row[2])), st.AR)
    st.RB = row[3]
    return st.RD, st.RW, st.RS


def river_of(landmark: int) -> int:
    """``RC = (LM = 2) + 2 * (LM = 9) + 3 * (LM = 12)``."""
    return R.RC_RIVER_AT[landmark]


def crossing(c):
    """Lines 50000-50030: the menu, and whichever way the player chooses."""
    st = c.st
    from . import common, losses
    st.RC = river_of(st.LM)
    st.W1 = 1                       # line 3500: no one falls ill while waiting here
    conditions(c)
    c.ui.clear()
    c.ui.print(L.short_name(st.LM))
    c.ui.print(common.date_text(c))
    c.ui.print("You must cross the river in order to continue.  The river at this "
               "point is currently " + num.str_(st.RW)
               + " feet across, and " + num.str_(st.RD) + " feet deep in the middle.")
    extra = R.RC[st.RC][5]
    menu = [TXT[0], TXT[1]]
    f = 1 if extra else 0
    if extra:
        menu.append(TXT[extra + 3])
    menu.append(TXT[2])                       # wait
    menu.append(TXT[3])                       # more information
    while True:
        conditions(c)
        c.ui.print()
        c.ui.print("Weather: " + T.WEATHER[num.as_int(st.W)])
        c.ui.print("River width: " + num.str_(st.RW) + " feet")
        c.ui.print("River depth: " + num.str_(st.RD) + " feet")
        c.ui.print()
        c.ui.print("You may:")
        for i, label in enumerate(menu, 1):
            c.ui.print(f"{i}. {label}")
        c.ui.print()
        c.ui.print("What is your choice? ")
        a = c.ui.key("-18", 2, default="")
        v = int(a) if a and a.isdigit() else 0
        if v == 4 + f:
            information(c, v - 3 - f)
            continue
        if v == 3 + f:
            # line 50025: a camp and a day
            c.ui.print("You camp near the river for a day.")
            common.wait_key(c)
            st.SD = 1
            from . import trail
            trail.run_stopped_days(c)
            continue
        # line 50030: the ferry is dispatched through the fourth slot
        v2 = v + 1 if (v == 3 and extra == 2) else v
        ix = num.ONE
        if v2 == 1:
            return ford(c)
        if v2 == 2:
            if float_crossing(c) is None:
                continue
            return None
        if v2 == 3:
            if guide(c) is None:
                continue
            return None
        if v2 == 4:
            if ferry(c):
                return None
            continue


def information(c, which: int):
    """Lines 50160-50170."""
    from . import common
    texts = {
        0: "To ford a river means to pull your wagon across a shallow part of the "
           "river, with the oxen still attached.",
        1: "To caulk the wagon means to seal it so that no water can get in.  The "
           "wagon can then be floated across like a boat.",
        2: "To use a ferry means to put your wagon on top of a flat boat that "
           "belongs to someone else.  The owner of the ferry will take your wagon "
           "across the river.",
    }
    c.ui.clear()
    c.ui.print(texts.get(which, texts[0]))
    common.wait_key(c)


def ford(c, ix=None):
    """Lines 50035-50075: fording, in the four cases."""
    st = c.st
    from . import common, losses
    if ix is None:
        ix = st.IX
    st.IX = ix
    lines = []
    if num.lt(st.RD, num.parse("2.5")):
        bottom = st.RB
        if bottom == R.muddy:
            if c.rng.below("50060 stuck in mud", num.div(num.parse(".4"), ix)):
                lines = _lose_goods(c, num.parse(".5"))
                _say(c, "You become stuck in the mud.  Lose 1 day.")
                st.SD = 1
                from . import trail
                trail.run_stopped_days(c)
                return True
            _say(c, "It was a muddy crossing, but you did not get stuck.")
            return True
        if bottom == R.rough:
            if c.rng.below("50070 wagon tips", num.div(num.parse(".16"), ix)):
                # one V for the whole crossing, so every good shares the chance
                v = num.add(num.parse(".1"),
                            num.mul(c.rng.rnd1("50070 loss chance"), num.parse(".3")))
                lines = _lose_goods(c, num.div(v, ix))
                _say(c, "The wagon tipped over" + (".  You lose:" if lines
                                                   else " but you did not lose anything."))
            else:
                _say(c, "It was a rough crossing, but you did not overturn.")
            return True
        _say(c, "You made the crossing successfully.")
        return True
    if num.lt(st.RD, num.parse("3")):
        _say(c, "Your supplies got wet.  Lose 1 day.")
        st.SD = 1
        from . import trail
        trail.run_stopped_days(c)
        return True
    # line 50040: 3 feet or more
    lines = _lose_goods(c, num.div(num.div(st.RD, num.parse("10")), ix))
    lines += _lose_oxen(c, num.div(num.div(num.sub(st.RD, num.ONE), num.parse("10")),
                                   ix))
    lines += _lose_people(c, num.div(num.div(num.sub(st.RD, num.parse("2.5")),
                                          num.parse("10")), ix))
    _say(c, "The river is too deep to ford.  You lose:" if lines
          else "You made the crossing successfully.", lines)
    return True


def float_crossing(c, ix=None):
    """Lines 50080-50095: caulking the wagon and floating it.

    Refused under 1.5 feet, one day, and above 2.5 feet the wagon tips with a
    chance of swiftness in twenty -- **the draw is made even in shallow water**, so
    the number is spent either way.
    """
    st = c.st
    from . import common, losses
    from . import trail
    if ix is None:
        ix = st.IX
    st.IX = ix
    if num.lt(st.RD, num.parse("1.5")):
        c.ui.clear()
        c.ui.print("The river is too shallow")
        c.ui.print("to float across.")
        common.wait_key(c)
        return None
    st.SD = 1
    trail.run_stopped_days(c)
    lines = []
    v = num.div(num.mul(num.ONE if num.gt(st.RD, num.parse("2.5")) else num.ZERO,
                        num.div(st.RS, num.parse("20"))), ix)
    if c.rng.below("50085 wagon tips", v):
        lines = _lose_goods(c, num.div(
            num.add(num.parse(".4"), num.div(st.RS, num.parse("25"))), ix))
        lines += _lose_people(c, num.div(num.div(num.sub(st.RS, num.parse("3")),
                                               num.parse("15")), ix))
        _say(c, "The wagon tipped over while floating.  You lose:", lines)
        return True
    _say(c, "You had no trouble floating the wagon across.")
    return True


def ferry(c):
    """Lines 50100-50125: the ferry. True when the party is across."""
    st = c.st
    from . import common, losses
    if num.lt(st.RD, num.parse("2.5")):
        c.ui.clear()
        c.ui.print("The ferry is not operating today because the river is to "
                   "shallow.")
        common.wait_key(c)
        return False
    # line 50101: the days of waiting are drawn before the player is asked
    x = num.trunc(num.add(num.mul(c.rng.rnd1("50101 ferry wait"),
                                  num.parse("5")), num.parse("2")))
    v = num.parse("5")
    c.ui.clear()
    c.ui.print("The ferry operator says that he will charge you $"
               + common.money(c, v)
               + " and that you will have to wait " + num.str_(x)
               + " days.  Are you willing to do this? ")
    answer = common.yes_no(c)
    if answer == "Y" and num.lt(st.MY, v):
        c.ui.print("You do not have enough money to pay for the ferry.")
        common.wait_key(c)
        return False
    if answer == "N":
        return False
    st.MY = num.sub(st.MY, v)
    st.SD = num.as_int(x)
    from . import trail
    trail.run_stopped_days(c)
    lines = []
    v = num.add(num.mul(num.parse(".05"), num.ONE if num.gt(st.RS, num.parse("5"))
                        else num.ZERO),
                num.mul(num.parse(".1"), num.ONE if num.gt(st.RS, num.parse("10"))
                        else num.ZERO))
    if c.rng.below("50120 ferry breaks loose", v):
        lines = _lose_goods(c, num.parse(".8"))
        lines += _lose_people(c, num.parse(".2"))
        lines += _lose_oxen(c, num.parse(".5"))
        _say(c, "The ferry broke loose from moorings. You lose:", lines)
        return True
    _say(c, "The ferry got your party and wagon safely across.")
    return True


def guide(c):
    """Lines 50130-50145: a Shoshoni guide for two or three sets of clothing.

    The guide fords when the river is 2.4 feet or less and floats above that, and
    every risk is divided by five -- ``IX = 5``.
    """
    st = c.st
    from . import common
    x = num.trunc(num.add(num.mul(c.rng.rnd1("50130 sets asked"),
                                  num.parse("2")), num.parse("2")))
    c.ui.clear()
    c.ui.print("A Shoshoni guide says that he will take your wagon across the river "
               "in exchange for " + num.str_(x) + " sets of clothing.")
    if num.lt(st.I[3], x):
        c.ui.print("You don't have " + num.str_(x) + " sets of clothing.")
        common.wait_key(c)
        return None
    c.ui.print("Will you accept this offer? ")
    if common.yes_no(c) == "N":
        return None
    st.IX = num.parse("5")
    st.I[3] = num.sub(st.I[3], x)
    word = "ford the river." if num.le(st.RD, num.parse("2.4")) \
        else "float your wagon across."
    c.ui.clear()
    c.ui.print("The Shoshoni guide will help you " + word)
    common.wait_key(c)
    which = 1 if num.le(st.RD, num.parse("2.4")) else 2
    if which == 1:
        ford(c, num.parse("5"))
    else:
        float_crossing(c, num.parse("5"))
    return True


# ------------------------------------------------------------ the loss routines
def losses(c, chance, item: int, tag: str):
    """Line 50205: one good lost with *chance*, to a random amount.

    ``FOR L = 3 TO 8: X = I(L): IF X AND RND (1) < V THEN ...`` -- no short-circuit,
    so a draw happens for **each of the six goods** even when none is held, and a
    second draw for the amount only when something is lost.
    """
    st = c.st
    got = None
    if c.rng.below(f"{tag} item {item}", chance) and not num.eq(st.I[item], num.ZERO):
        amount = num.trunc(num.add(
            num.mul(c.rng.rnd1(f"{tag} amount {item}"), num.ONE), num.ZERO))
        st.I[item] = num.sub(st.I[item], amount)
        from .lf import _line
        got = _line(0, amount, item)
    return got


def _lose_goods(c, chance) -> list:
    """Line 50205: the loop over goods 3 to 8."""
    st = c.st
    out = []
    for item in range(3, 9):
        line = losses(c, chance, item, "50205 goods")
        if line:
            out.append(line)
    return out


def _lose_oxen(c, chance) -> list:
    """Line 50185: ``FOR L = 1 TO X`` with X the oxen count.

    The limit can end in a half, and Applesoft's FOR stops at the last whole number
    below it, so five and a half oxen give five draws (Appendix G.5).
    """
    st = c.st
    x = num.as_float(st.I[2])
    if x <= 0:
        return []
    lost = 0
    for _ in range(int(x)):
        if c.rng.below("50185 ox", chance):
            lost += 1
    if not lost:
        return []
    st.I[2] = num.sub(st.I[2], num.parse(str(lost)))
    if num.lt(st.I[2], num.ZERO):
        st.I[2] = num.ZERO
    word = "ox" + ("en" if lost != 1 else "")
    return [f"{lost} {word}"]


def _lose_people(c, chance) -> list:
    """Line 50175: the party drowns, the leader last.

    ``FOR L = (NP > 1) TO NP - 1`` -- so with more than one member alive the leader
    is skipped, and alone the leader can drown. Once ten have been lost the chance
    falls to nothing, because ``V = V * (Z < 11)``.
    """
    st = c.st
    out = []
    np_ = num.as_int(st.NP)
    start = 1 if np_ > 1 else 0
    for i in range(start, np_):
        if c.rng.below(f"50175 person {i}", chance):
            out.append(st.N[i] + " (drowned)")
            st.H1[i] = num.parse("-2")
            chance = num.mul(chance, num.ONE if len(out) < 11 else num.ZERO)
    return out


def _say(c, text: str, lines=None):
    from . import common
    common.message(c, text, lines)
