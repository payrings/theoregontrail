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

from . import cross, num
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
    from . import common
    st.RC = river_of(st.LM)
    st.W1 = 1                       # line 3500; line 3504 clears it on departure
    # Line 3500 appends RIVER.LIB and line 3504 calls it; only when it returns does
    # 3504 go on to "& APP,"CROSS.LIB": GOSUB 50000". So the whole animation, both
    # halves, spends its numbers AFTER the crossing has been decided and its losses
    # drawn -- see _animate below. Spending the first half before the menu, as this
    # did, moved 106 draws in front of every river draw.
    conditions(c)
    # line 50000 reads the six menu texts into T$(0) to T$(5); they stay there until
    # the travel screen is next drawn, or a loss line is written over them
    for i in range(6):
        st.T[i] = TXT[i]
    gfx = c.ui.pictures
    st.SR = 0                                 # 50000: SR = 0
    intro = ("You must cross the river in order to continue.  The river at this "
             "point is currently " + num.str_(st.RW)
             + " feet across, and " + num.str_(st.RD) + " feet deep in the middle.")
    if gfx:
        from .graphics import screens
        screens.river_page(c.ui, L.short_name(st.LM), common.date_text(c))
        screens.river_text(c.ui, intro)
    else:
        c.ui.clear()
        c.ui.print(L.short_name(st.LM))
        c.ui.print(common.date_text(c))
        c.ui.print(intro)
    common.wait_key(c)                        # 50005: ... GOSUB 30000
    extra = R.RC[st.RC][5]
    menu = [TXT[0], TXT[1]]
    f = 1 if extra else 0
    if extra:
        menu.append(TXT[extra + 3])
    menu.append(TXT[2])                       # wait
    menu.append(TXT[3])                       # more information
    while True:
        conditions(c)
        if gfx:
            screens.river_menu(c.ui, T.WEATHER[num.as_int(st.W)], num.str_(st.RW),
                               num.str_(st.RD), menu)
        else:
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
        a = c.ui.key(ALLOWED["RIVER"], 1, default="")
        v = int(a) if a and a.isdigit() else 0
        if v == 4 + f:
            information(c)                    # 50020: GOSUB 50160, all three pages
            continue
        if v == 3 + f:
            # line 50025: a camp and a day
            if gfx:
                screens.river_notice(c.ui, ["You camp near the river for a day."])
            else:
                c.ui.print("You camp near the river for a day.")
            common.wait_key(c)
            st.SD = 1
            from . import trail
            trail.run_stopped_days(c)
            if gfx:
                screens.river_date(c.ui, common.date_text(c))      # 50025: & CEL: PRINT TD$
            continue
        # line 50030 begins IX = 1, so every choice from the menu starts at the normal
        # risk; only the Shoshoni guide raises it to 5, for that crossing
        st.IX = num.ONE
        # ... and goes on: the ferry is dispatched through the fourth slot
        v2 = v + 1 if (v == 3 and extra == 2) else v
        if v2 == 1:
            ford(c)
            _animate(c, 2)
            _show_result(c)
            _bury_drowned(c)
            return True
        if v2 == 2:
            if float_crossing(c) is None:
                continue
            _animate(c, 3)
            _show_result(c)
            _bury_drowned(c)
            return None
        if v2 == 3:
            if guide(c) is None:
                continue
            _animate(c, getattr(c, "river_method", 2))
            _show_result(c)
            _bury_drowned(c)
            return None
        if v2 == 4:
            if ferry(c):
                _animate(c, 1)
                _show_result(c)
                _bury_drowned(c)
                return None
            # The ferry was refused or declined: RIVER.LIB goes back to its menu
            # (ON F GOTO 50010) without returning, so CROSS.LIB is not reached and
            # no animation number is spent.
            continue


def _hold(c, seconds: float = 1.0):
    """Show what has been drawn so far and wait: one second between the frames of a
    crossing, when a person is watching."""
    if c.ui.pictures and getattr(c.ui, "daily_pause", 0) > 0:
        import time
        c.ui.refresh()
        time.sleep(seconds)


def _animate(c, method: int):
    """Line 3504: CROSS.LIB, run once RIVER.LIB has returned -- both halves.

    ``method`` is the listing's ``I``: 1 for the ferry, 2 for a ford, 3 for a float.
    CROSS.LIB 50010 always spends 106 numbers. Line 50020 then looks at ``Z``, the
    number of loss lines: with none it spends 122 more (50030); with losses it goes
    by the method (50040) -- 66 more after a ford (50060), none after a float or a
    ferry (50050).
    """
    gfx = c.ui.pictures
    if gfx:
        from . import common
        from .graphics import screens
        screens.river_frame(c.ui, L.short_name(c.st.LM), common.date_text(c), method)
        _hold(c)                                  # the river as it is, for a second
        screens.river_first_half(c.ui)
        _hold(c)
    cross.first_half(c)
    if not getattr(c, "river_losses", 0):
        if gfx:
            screens.river_tail_success(c.ui)          # 50030
            _hold(c)
        cross.tail(c, "success")
    elif method == 2:
        if gfx:
            if c.ui.cv.plain:                         # a themed folder shows the wagon capsized
                c.ui.cv.image("river_04", 102, 63)
            else:
                screens.river_tail_failed_ford(c.ui)  # 50060
            _hold(c)
        cross.tail(c, "failed-ford")
    else:
        if gfx:
            c.ui.cv.image("river_04", 102, 63)        # 50050
            _hold(c)
        cross.tail(c, "failed-float")


def information(c):
    """Lines 50160-50170: the ford, caulk and ferry pages, each with its wait."""
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
    gfx = c.ui.pictures
    for which in (0, 1, 2):
        if gfx:
            from .graphics import screens
            screens.river_window6(c.ui, whole=(which == 0))      # 50020: & BOX: & WIND,6
            c.ui.para(texts[which])
        else:
            c.ui.clear()
            c.ui.print(texts[which])
        common.wait_key(c)


def ford(c, ix=None):
    """Lines 50035-50075: fording, in the four cases.

    Returns what happened -- ``success``, ``stuck``, ``wet``, ``tipped`` or
    ``deep`` -- which is how :func:`crossing` knows how many numbers the
    animation should spend afterwards.
    """
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
                # Line 50060 loses a day and nothing else: "SD = 1:SR = 0: GOSUB 500:
                # Z = 0". A goods loss was invented here, with its draws.
                _say(c, "You become stuck in the mud.  Lose 1 day.")
                st.SD = 1
                from . import trail
                trail.run_stopped_days(c)
                return "stuck"          # a day lost, but the wagon is across
            _say(c, "It was a muddy crossing, but you did not get stuck.")
            return "success"
        if bottom == R.rough:
            if c.rng.below("50070 wagon tips", num.div(num.parse(".16"), ix)):
                # one V for the whole crossing, so every good shares the chance
                v = num.store(num.add(num.parse(".1"),
                                      num.mul(c.rng.rnd1("50070 loss chance"),
                                              num.parse(".3"))))      # V is a variable
                # Line 50070 calls 50205 with V as drawn: it is NOT divided by IX,
                # so the guide's one-fifth applies to the tipping chance only.
                lines = _lose_goods(c, v)
                _say(c, "The wagon tipped over" + (".  You lose:" if lines
                                                   else " but you did not lose anything."),
                     lines)
                return "tipped"
            _say(c, "It was a rough crossing, but you did not overturn.")
            return "success"
        _say(c, "You made the crossing successfully.")
        return "success"
    if num.lt(st.RD, num.parse("3")):
        _say(c, "Your supplies got wet.  Lose 1 day.")
        st.SD = 1
        from . import trail
        trail.run_stopped_days(c)
        return "wet"
    # line 50040: 3 feet or more
    # each ``V = ... / IX`` is an assignment, so V is the stored value every time
    lines = _lose_goods(c, num.store(num.div(num.div(st.RD, num.parse("10")), ix)))
    lines += _lose_oxen(c, num.store(num.div(
        num.div(num.sub(st.RD, num.ONE), num.parse("10")), ix)))
    lines += _lose_people(c, num.store(num.div(
        num.div(num.sub(st.RD, num.parse("2.5")), num.parse("10")), ix)), len(lines))
    _say(c, "The river is too deep to ford.  You lose:" if lines
          else "You made the crossing successfully.", lines)
    return "deep"


def float_crossing(c, ix=None):
    """Lines 50080-50095: caulking the wagon and floating it.

    Refused under 1.5 feet, one day, and above 2.5 feet the wagon tips with a
    chance of swiftness in twenty -- **the draw is made even in shallow water**, so
    the number is spent either way.
    """
    st = c.st
    from . import common
    from . import trail
    if ix is None:
        ix = st.IX
    st.IX = ix
    if num.lt(st.RD, num.parse("1.5")):
        if c.ui.pictures:
            from .graphics import screens
            screens.river_notice(c.ui, ["The river is too shallow", "to float across."])
        else:
            c.ui.clear()
            c.ui.print("The river is too shallow")
            c.ui.print("to float across.")
        common.wait_key(c)
        return None
    st.SD = 1
    trail.run_stopped_days(c)
    lines = []
    # V = (RD > 2.5) * (RS / 20) / IX
    v = num.store(num.div(num.mul(num.bool_(num.gt(st.RD, num.parse("2.5"))),
                                  num.div(st.RS, num.parse("20"))), ix))
    if c.rng.below("50085 wagon tips", v):
        lines = _lose_goods(c, num.store(num.div(
            num.add(num.parse(".4"), num.div(st.RS, num.parse("25"))), ix)))
        lines += _lose_people(c, num.store(num.div(
            num.div(num.sub(st.RS, num.parse("3")), num.parse("15")), ix)), len(lines))
    # 50090: IF Z THEN A$ = "The wagon tipped over while floating.  You lose:" -- the
    # wagon can tip and lose nothing, and then A$ still says there was no trouble
    if lines:
        _say(c, "The wagon tipped over while floating.  You lose:", lines)
    else:
        _say(c, "You had no trouble floating the wagon across.")
    return True


def ferry(c):
    """Lines 50100-50125: the ferry. True when the party is across."""
    st = c.st
    from . import common
    if num.lt(st.RD, num.parse("2.5")):
        text = ("The ferry is not operating today because the river is to "
                "shallow.")
        if c.ui.pictures:
            from .graphics import screens
            screens.river_notice(c.ui, [text], centre=False)
        else:
            c.ui.clear()
            c.ui.print(text)
        common.wait_key(c)
        return False
    # line 50101: the days of waiting are drawn before the player is asked
    x = num.int_(num.add(num.mul(c.rng.rnd1("50101 ferry wait"),
                                 num.parse("5")), num.parse("2")))
    v = num.parse("5")
    offer = ("The ferry operator says that he will charge you $"
             + common.money(c, v)
             + " and that you will have to wait " + num.str_(x)
             + " days.  Are you willing to do this? ")
    gfx = c.ui.pictures
    if gfx:
        from .graphics import screens
        screens.river_window6(c.ui, whole=True)               # 50101: & BOX: & WIND,6
        c.ui.para(offer.rstrip(), newline=False)
        c.ui.put(" ")
    else:
        c.ui.clear()
        c.ui.print(offer)
    answer = common.yes_no(c)
    if answer == "Y" and num.lt(st.MY, v):
        text = "You do not have enough money to pay for the ferry."
        if gfx:
            screens.river_window6(c.ui)                       # 50105: & CO: & CEW
            c.ui.para(text)
        else:
            c.ui.print(text)
        common.wait_key(c)
        return False
    if answer == "N":
        return False
    st.MY = num.sub(st.MY, v)
    st.SD = num.as_int(x)
    from . import trail
    trail.run_stopped_days(c)
    lines = []
    # V = .05 * (RS > 5) + .1 * (RS > 10)
    v = num.store(num.add(
        num.mul(num.parse(".05"), num.bool_(num.gt(st.RS, num.parse("5")))),
        num.mul(num.parse(".1"), num.bool_(num.gt(st.RS, num.parse("10"))))))
    if c.rng.below("50120 ferry breaks loose", v):
        lines = _lose_goods(c, num.store(num.parse(".8")))
        lines += _lose_people(c, num.store(num.parse(".2")), len(lines))
        lines += _lose_oxen(c, num.store(num.parse(".5")))
        # 50120 ends IF NOT Z THEN A$ = "Some trouble in crossing but nothing was lost."
        if lines:
            _say(c, "The ferry broke loose from moorings. You lose:", lines)
        else:
            _say(c, "Some trouble in crossing but nothing was lost.")
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
    x = num.int_(num.add(num.mul(c.rng.rnd1("50130 sets asked"),
                                 num.parse("2")), num.parse("2")))
    gfx = c.ui.pictures
    offer = ("A Shoshoni guide says that he will take your wagon across the river "
             "in exchange for " + num.str_(x) + " sets of clothing.")
    if gfx:
        from .graphics import screens
        screens.river_window6(c.ui, whole=True)               # 50130: & BOX: & WIND,6
        c.ui.para(offer)
        c.ui.nl()
    else:
        c.ui.clear()
        c.ui.print(offer)
    if num.lt(st.I[3], x):
        c.ui.print("You don't have " + num.str_(x) + " sets of clothing.")
        common.wait_key(c)
        return None
    c.ui.print("Will you accept this ")        # 50136: two PRINTs
    c.ui.print("offer? ")
    if common.yes_no(c) == "N":
        return None
    st.IX = num.parse("5")
    st.I[3] = num.sub(st.I[3], x)
    word = "ford the river." if num.le(st.RD, num.parse("2.4")) \
        else "float your wagon across."
    if gfx:
        screens.river_window6(c.ui)                           # 50145: & BOX: & WIND,6
        c.ui.para("The Shoshoni guide will help you " + word)
    else:
        c.ui.clear()
        c.ui.print("The Shoshoni guide will help you " + word)
    common.wait_key(c)
    which = 1 if num.le(st.RD, num.parse("2.4")) else 2
    if which == 1:
        c.river_method = 2
        ford(c, num.parse("5"))
    else:
        c.river_method = 3
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
        # Line 50205: Y = INT (RND (1) * X + 1), X the amount held -- one to all of
        # it, never zero, so it has to stay a five-byte value
        x = st.I[item]
        amount = num.int_(num.add(
            num.mul(c.rng.rnd1(f"{tag} amount {item}"), x), num.ONE))
        st.I[item] = num.sub(x, amount)
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
    below it, so five and a half oxen give five draws (Appendix F.5).
    """
    st = c.st
    x = st.I[2]
    if num.eq(x, num.ZERO):
        # 50185 is "Y = 0:X = I(2): IF NOT X THEN RETURN"
        return []
    lost = 0
    # 50190 is "FOR L = 1 TO X", and the body always runs at least once (paper 2.5,
    # rule c), so a party with half an ox still makes one draw.
    for _ in num.fort_range(1, num.as_int(x)):
        if c.rng.below("50185 ox", chance):
            lost += 1
    if not lost:
        return []
    st.I[2] = num.sub(st.I[2], num.parse(str(lost)))
    if num.lt(st.I[2], num.ZERO):
        st.I[2] = num.ZERO
    word = "ox" + ("en" if lost != 1 else "")
    return [f"{lost} {word}"]


def _lose_people(c, chance, z: int = 0) -> list:
    """Line 50175: the party drowns, the leader last.

    ``FOR L = (NP > 1) TO NP - 1`` -- so with more than one member alive the leader
    is skipped, and alone the leader can drown. Once ten have been lost the chance
    falls to nothing, because ``V = V * (Z < 11)``. ``Z`` is the count of loss lines so
    far in the whole crossing, goods and oxen included, so it is passed in.
    """
    st = c.st
    out = []
    np_ = num.as_int(st.NP)
    start = 1 if np_ > 1 else 0
    for i in range(start, np_):
        if c.rng.below(f"50175 person {i}", chance):
            out.append(st.N[i] + " (drowned)")
            st.H1[i] = num.parse("-2")
            z += 1
            chance = num.store(num.mul(chance, num.bool_(z < 11)))
    return out


def _say(c, text: str, lines=None):
    from . import common
    # Z in the listing: the number of loss lines the crossing produced. CROSS.LIB
    # 50020 tests it to choose the second half of the animation.
    c.river_losses = len(lines) if lines else 0
    for i, t in enumerate(lines or []):
        c.st.T[i] = t                      # T$(Z) = ... at 50175, 50195 and 50205
    # RIVER.LIB only sets A$; line 3504 shows it with GOSUB 900, after the stopped
    # days and after CROSS.LIB
    c.river_message = (text, list(lines or []))


def _show_result(c):
    """Line 3504: ``GOSUB 900`` -- the crossing's message and loss lines, a wait,
    and ``B = (PEEK (-16384) = 13)``."""
    from . import common
    pending = getattr(c, "river_message", None)
    c.river_message = None
    if pending:
        c.keep_screen = bool(c.ui.pictures)       # the box goes over the water
        try:
            common.message_900(c, pending[0], pending[1])
        finally:
            c.keep_screen = False


def _bury_drowned(c) -> bool:
    """OREGON TRAIL 3504: take the dead out of the party after a crossing.

    Anyone the river marked with ``-2`` is removed. If that would leave nobody,
    the tombstone sequence runs.
    """
    st = c.st
    if not any(num.eq(st.H1[i], num.parse("-2")) for i in range(num.as_int(st.NP))):
        return False
    from . import trail
    trail.remove_drowned(c)
    return True


