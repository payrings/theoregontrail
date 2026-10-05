"""OREGON TRAIL 4000-4900: the action menu, and the eight things it can do.

The menu is offered at a landmark, and again at any moment on the trail if the
player presses Return (line 810). Which options appear depends on ``LL``:

* at a landmark (``LL = 0``): "Talk to people", and "Buy supplies" at a fort --
  both nested inside ``IF NOT LL`` at line 4040;
* on the trail (``LL = 1``): "Hunt for food", with ``Z = 2`` (line 4050).

Line 4090 dispatches with ``ON Z - 1 GOSUB 4100, 4200, 4300, 4400, 4500, 4900, 4700,
4800, 4600``, and ``Z`` is the choice plus two when the choice is above seven and
the party is on the trail. That lands correctly, and there is no bug here: the two
extra entries are printed only at a landmark, so on the trail there are eight
choices and the eighth is the hunt.

Choice 1 is "Continue on trail" and is handled before the dispatch: with no oxen it
sets ``B = 2`` and stays, and with a part still broken ``B`` is already set so the
menu explains what has to be traded for and the player must choose something else.
"""

from __future__ import annotations

from . import num
from .data import goods as G
from .data import landmarks as L
from .data import text as T
from .ui import ALLOWED

__all__ = ["action_menu", "show_supplies", "continue_trail"]


def action_menu(c):
    """Lines 4000-4095: draw the menu, read a choice, do it, and draw it again."""
    st = c.st
    from . import common
    st.F9 = 0
    st.SR = 0
    # line 4005: B = B * (B <> 1) -- a B of 1 means the player pressed Return
    if num.as_int(st.B) == 1:
        st.B = 0
    while True:
        header(c)
        options = []
        for i in range(7):
            options.append(T.ACTIONS[i])
        z = 0
        on_trail = bool(st.LL)
        if not on_trail:
            options.append(T.ACTIONS[7])                # Talk to people
        if L.LM_TYPE[st.LM] == 1:
            options.append(T.ACTIONS[8])                # Buy supplies, at a fort
        if on_trail:
            options.append(T.ACTIONS[9])                # Hunt for food
        for i, label in enumerate(options, 1):
            c.ui.print(f"{i}. {label}")
        c.ui.print()
        c.ui.print("What is your choice? ")
        a = c.ui.key("", 2, default="")
        x = int(a) if a and a.isdigit() else 0
        if not st.B and x == 1:
            st.B = 2 if num.eq(st.I[2], num.ZERO) else 0
            if not st.B:
                return "CONTINUE"
        if st.B and x == 1:
            # line 4070: T$(0) = "a ", T$(1) = "an ", then T$(B = 2) picks one.
            # So B = 2 gives "an ox" and B = 5 gives "a wheel": the article is
            # the wrong way round for oxen, which is in the shipped game.
            art = "an " if st.B == 2 else "a "
            what = G.UNIT[0] if st.B == 2 else G.UNIT[st.B - 2]
            c.ui.print("You must trade for " + art + what
                       + " to be able to continue.")
            common.wait_key(c)
            continue
        # line 4090: Z = Z * (X > 7) + X, then ON Z - 1
        z = (2 if on_trail else 0) + x if x > 7 else x
        handlers = {2: show_map, 3: do_pace, 4: do_rations, 5: do_rest,
                    6: do_trade, 7: do_talk, 8: do_buy, 9: do_hunt}
        h = handlers.get(z - 1)
        if h is not None:
            h(c)
        if st.SD > 0:
            from . import trail
            trail.run_stopped_days(c)
        if st.B and st.B != 1:
            # line 4090: a spare part that arrived is used up here
            if num.as_int(st.B) > 2 and 5 <= num.as_int(st.B) <= 7:
                item = num.as_int(st.B)
                if not num.eq(st.I[item], num.ZERO):
                    st.I[item] = num.sub(st.I[item], num.ONE)
            st.B = 0
        continue


def header(c):
    """Lines 4005-4030: the landmark, the date, and the four lines of status."""
    st = c.st
    from . import common
    c.ui.clear()
    name = L.short_name(st.LM)
    c.ui.print(name)
    c.ui.print(common.date_text(c))
    if num.gt(st.H, num.parse("139")):
        st.H = num.parse("139")
    c.ui.print("Weather: " + T.WEATHER[num.as_int(st.W)])
    c.ui.print("Health: " + T.HEALTH[st.health_band()])
    c.ui.print("Pace: " + T.PACE[num.as_int(st.P) - 1])
    c.ui.print("Rations: " + T.RATIONS[num.as_int(st.R) - 1])
    c.ui.print()
    # line 4030: the dialogue slot advances by one, wrapping, so the three speakers
    # come round in turn
    st.A = (st.A + 1) * (1 if st.A < 2 else 0)


# ------------------------------------------------------------------ the items
def show_supplies(c):
    """Lines 4100-4110: what is held.

    Each quantity is printed as ``INT (I(L) + .51)``, so five and a half oxen are
    shown as six.
    """
    st = c.st
    from . import common
    c.ui.clear()
    c.ui.print("  Your Supplies")
    for item in range(2, 9):
        held = num.int_(num.add(st.I[item], num.parse(".51")))
        c.ui.print(T.I_NAMES[item].ljust(24)
                   + num.str_(num.parse(str(held))).rjust(6))
    c.ui.print("money left".ljust(24) + ("$" + common.money(c, st.MY)).rjust(6))
    common.wait_key(c)


def show_map(c):
    """Line 4200."""
    from . import maplib
    maplib.show(c)


def do_pace(c):
    """Line 4300 and PACE.LIB."""
    from . import pace
    pace.change(c)


def do_rations(c):
    """Line 4400 and RATION.LIB."""
    from . import ration
    ration.change(c)


def do_rest(c):
    """Lines 4500-4510: one to nine days, with no travel and no pace penalty."""
    st = c.st
    from . import common, trail
    c.ui.print("How many days would you like to rest? ")
    a = c.ui.key(ALLOWED["REST"], 1, default="1")
    st.SD = int(a) if a and a.isdigit() else 1
    if st.SD:
        saved_d, saved_m, saved_p = st.D, st.M, st.P
        st.D = num.ZERO
        st.P = num.ZERO
        for _ in range(st.SD):
            trail.daily_cycle(c)
            c.ui.print(common.date_text(c))
        st.SD = 0
        st.D, st.M, st.P = saved_d, saved_m, saved_p
    return st.SD


def do_trade(c):
    """Lines 4900 and TRADE.LIB. A trade attempt always costs a day."""
    st = c.st
    from . import trade
    trade.attempt(c)
    st.SD = 1
    if num.lt(st.I[2], num.ZERO):
        st.I[2] = num.ZERO


def do_talk(c):
    """Line 4700 and TALK.LIB."""
    from . import talk
    talk.talk(c)


def do_buy(c):
    """Line 4800 and BUY.LIB."""
    from . import fortbuy
    fortbuy.fort_store(c)


def do_hunt(c):
    """Lines 4600 and HUNT.LIB. A hunt costs a day."""
    st = c.st
    from . import hunt
    hunt.go(c)
    st.SD = 1
