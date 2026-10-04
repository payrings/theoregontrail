"""OREGON TRAIL: the journey itself.

This is the largest program in the game. The lines below follow the listing:

* 100-110    start-up: ``VAR.BIN``, the saved variable table, and the first two draws
* 190-460    the small helpers: library removal, the money and date strings, the
             travel screen, the gravesite test, the stopped-day routine
* 500-570    losing days to an event
* 600        the disk flip at Fort Laramie
* 650-660    speed: base speed, daily food, clothing per person, ration penalty
* 700-958    the message box and the wait for a key
* 1000-1016  arriving at a landmark, the action menu, choosing a segment
* 2100-2200  the branch at South Pass and the Blue Mountains; loading a segment
* 3000-3060  starting a segment
* 3100-3499  **the daily cycle**
* 3500-3505  a river crossing
* 4000-4095  the action menu
* 8000       burying the dead
* 10000-11400  the fifteen random events
* 11500-11505  choosing a victim
* 21000      the check for oxen
* 29000-29020  reading the hand-over and the two grave records

The daily cycle is the heart of the game and the order of its steps is the order of
its random draws, so it is transcribed step by step with the line numbers in place.
"""

from __future__ import annotations

from . import num
from .applesoft.fac import Fac
from .data import climate as CL
from .data import illnesses as ILL
from .data import landmarks as L
from .data import text as T

__all__ = ["run", "daily_cycle", "day_body", "speed", "weather", "arrive", "action_menu",
           "choose_segment", "load_segment", "event_loop", "event", "choose_victim",
           "lose_days", "run_stopped_days", "travel_screen", "find_grave",
           "load_state", "fn_w", "climate_zone"]

# The calendar, from line 3255. February always has 28 days even in 1848, which was a
# leap year; the paper lists it in section 13 and it is reproduced.
MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


# ------------------------------------------------------------------- helpers
def money(c):
    """Line 200."""
    from . import common
    return common.money(c, c.st.Z)


def date_text(c):
    """Line 250."""
    from . import common
    return common.date_text(c)


def short_name(c):
    """Line 260: the landmark name without a leading ``the ``."""
    return L.short_name(c.st.LM)


# ------------------------------------------------------------------ start-up
def load_state(c):
    """Lines 29000-29020: read the hand-over and the two grave records.

    The two draws here are the first of the journey, in this order:

    * line 29000, ``AS = RND (1) * 12 * (PEEK (902) < 4)`` -- snow on the ground,
      which is zero unless the party leaves in March. **The draw happens either
      way**, because Applesoft evaluates both sides of the ``*``.
    * line 29004, ``AR = 7 - PEEK (902) + RND (1)`` -- accumulated rain.

    ``W = INT ((FN W (0) + 10) / 20)`` at line 29000 reads ``WC$(ZO)`` before line
    1000 has ever set ``ZO``, and ``ZO`` is not one of the variables ``VAR.BIN``
    restores, so it is 0 and the Kansas City row is used whatever the month. See
    ``PLAN.md`` B1.
    """
    st = c.st
    st.MY = num.div(num.parse(str(c.mem.peek_word(913))), num.parse("10"))
    st.AM = num.parse(str(c.mem.peek(902)))
    st.AD = num.parse(str(c.mem.peek(903)))
    st.AY = num.parse(str(c.mem.peek(901) + 1800))
    st.ZO = 0
    st.AS = num.mul(c.rng.rnd1("29000 initial snow"),
                    num.parse("12"))
    if num.as_int(st.AM) >= 4:
        st.AS = num.ZERO                       # the draw happened; the product did not
    st.W = num.int_(num.div(num.add(fn_w(st, 0), num.parse("10")), num.parse("20")))
    # RE(7), RE(9), RE(12), RE(13), RE(1) and RE(2) are fixed for the whole game
    st.RE[7] = num.parse(".06")
    st.RE[9] = num.parse(".02")
    st.RE[12] = num.parse(".01")
    st.RE[13] = num.parse(".02")
    st.RE[1] = num.parse(".007")
    st.RE[2] = num.ZERO
    st.TM = st.W
    st.AR = num.add(num.parse(str(7 - num.as_int(st.AM))),
                    c.rng.rnd1("29004 initial rain"))
    st.Q1 = 1
    st.SN = [0, 0]
    st.ML = [0, 0]
    for side in (0, 1):
        rec = c.files.read_tombs(side)
        if rec:
            st.SN[side] = rec["segment"]
            st.ML[side] = rec["miles"]
    # I(3) to I(7) from 908 to 912, then the food, oxen and bullets
    for item in range(3, 8):
        st.I[item] = num.parse(str(c.mem.peek(905 + item)))
    st.I[8] = num.parse(str(c.mem.peek(906) + c.mem.peek(907) * 256))
    st.I[2] = num.parse(str(2 * c.mem.peek(905)))
    st.I[4] = num.parse(str(c.mem.peek(909) * 20))
    st.PF = st.I[8]
    st.N = c.mem.get_names(5)
    return st


def climate_zone(landmark: int) -> int:
    """Line 1000: ``ZO = (LM > 2) + (LM > 5) + (LM > 10) + (LM > 13)``.

    Five zones, so the Portland row of the climate table is never read. The paper
    lists that in section 13.
    """
    return L.zone_for(landmark)


def fn_w(st, which: int) -> Fac:
    """Line 105: the climate lookup.

    ``( NOT Z + .003 * Z) * ( ASC ( MID$(WC$(ZO), AM * 2 + Z - 1, 1)) - 30) - 20 * NOT Z``

    ``Z`` is 0 for the month's minimum temperature, which is the temperature code
    less 50, and 1 for the day's rain chance, which is 0.003 times the rain code less
    30.
    """
    row = CL.WC[st.ZO]
    # MID$ counts from one, so this zero-based index is one lower
    pos = num.as_int(st.AM) * 2 + which - 2
    code = ord(row[pos])
    if which == 0:
        return num.parse(str(code - 30 - 20))
    return num.mul(num.parse(str(code - 30)), num.parse(".003"))


# --------------------------------------------------------------------- speed
def speed(c):
    """Lines 650-660: everything that depends on pace, rations or the oxen.

    ``V = I(2) / 4: IF V > 1 THEN V = 1``
    ``FC = NP * (4 - R): BS = MD * V * (P + 1) / 2: OP = I(3) / NP: F0 = 2 * (R - 1)``

    Fewer than four oxen slows the wagon in proportion; the base speed is the
    segment's speed base, 20 miles a day before Fort Laramie and 12 after, times 1,
    1.5 or 2 for steady, strenuous or grueling. This runs at the start of a segment
    and after a change of pace or rations, a death, a trade, a theft or an ox injury
    -- **not** every day, so clothing lost in a fire does not change ``OP`` until one
    of those happens.
    """
    st = c.st
    v = num.div(st.I[2], num.parse("4"))
    if num.gt(v, num.ONE):
        v = num.ONE
    st.FC = num.mul(num.parse(str(st.NP)), num.sub(num.parse("4"), st.R))
    st.BS = num.div(num.mul(num.mul(st.MD, v), num.add(st.P, num.ONE)), num.parse("2"))
    st.OP = num.div(st.I[3], num.parse(str(st.NP)))
    st.F0 = num.mul(num.parse("2"), num.sub(st.R, num.ONE))
    st.Z = st.BS
    return st.BS


# -------------------------------------------------------------- the daily cycle
def run_stopped_days(c):
    """Line 500: run the daily cycle for ``SD`` days without travelling.

    ``SD`` days are run with ``D = 0``, so the loop at 3499 ends after one pass each
    time; ``P`` is set to 0 for the duration and restored afterwards, so a delay
    costs no pace penalty but still costs food, health and the weather. ``I(8)`` is
    copied from ``PF`` at the end.
    """
    st = c.st
    if not st.SD:
        return
    saved_d, saved_m, saved_p = st.D, st.M, st.P
    st.D = num.ZERO
    st.P = num.ZERO
    for _ in range(st.SD):
        day_body(c)
    st.SD = 0
    st.D, st.M, st.P = saved_d, saved_m, saved_p
    st.I[8] = st.PF


def lose_days(c, tag: str, most: int, label: str = "") -> int:
    """Lines 550-570: ``XX = INT (RND (1) * Z + 1)`` days lost, then run them.

    The message keeps the leading space ``STR$`` puts in front of a positive number,
    so it reads "Lose  3 days." with two spaces. The player may press Return while
    the message waits, which sets ``B`` and ends the event.
    """
    st = c.st
    xx = num.trunc(num.add(num.mul(c.rng.rnd1(tag), num.parse(str(most))), num.ONE))
    text = f"{label}.  Lose  {num.str_(num.parse(str(xx)))[1:]} day"
    if xx > 1:
        text += "s"
    text += "."
    from . import common
    common.message(c, text, wait=True)
    st.SD = xx
    run_stopped_days(c)
    if c.ui.poll_key() in ("\r", "\n"):
        st.B = 1
    return xx


# ------------------------------------------------------------------ the screen
def travel_screen(c):
    """Lines 300-401: the travel screen, as a block of text.

    The original draws it on the hi-res screen with six labels at the columns in
    ``B(0 to 5)`` -- 95, 70, 81, 95, 23 and 20 -- and six values above them. There is
    no hi-res screen here, so the same six labels and values are printed one per
    line, in the listing's order. The label list is read from the DATA line at 22000.

    Line 310 chooses the border colour from the weather: white when there is snow, the
    dry colour when the rain is 0.2 or less, green otherwise. That has no text
    equivalent and is noted in ``GAPS.md``.
    """
    st = c.st
    c.ui.print(f"{date_text(c)}")
    rows = [
        (T.TRAVEL_LABELS[1], date_text(c)),
        (T.TRAVEL_LABELS[2], T.WEATHER[num.as_int(st.W)]),
        (T.TRAVEL_LABELS[3], T.HEALTH[st.health_band()]),
        (T.TRAVEL_LABELS[4], num.str_(st.PF) + " pounds"),
        (T.TRAVEL_LABELS[5], num.str_(num.int_(st.D)) + " miles"),
        (T.TRAVEL_LABELS[6], num.str_(num.int_(st.M)) + " miles"),
    ]
    for label, value in rows:
        c.ui.print(f"  {label:<16}{value}")


def find_grave(c):
    """Lines 450-460: is there a grave ahead on this segment?

    ``DL = -1: FOR L4 = 0 TO 1: IF (SN(L4) = SN) AND (DL < ML(L4)) AND (ML(L4) < D)
    THEN LN = L4: DL = ML(L4)``

    ``SN`` is the segment the party is on, as ``NM * 100 + LM``, so a grave only
    counts if it was left on the same stretch. ``DL`` is the distance of the next
    one, or -1 when there is none, and line 3160 turns ``RE(4) = (D < DL)`` into
    today's chance of meeting it.
    """
    st = c.st
    st.DL = -1
    sn = num.as_int(st.NM) * 100 + num.as_int(st.LM)
    for i in (0, 1):
        if st.SN[i] == sn and st.ML[i] < num.as_float(st.D) and \
                num.as_float(st.ML[i]) > num.as_float(st.DL):
            st.LN = i
            st.DL = st.ML[i]
    return st.DL


# ---------------------------------------------------------------- the weather
def weather(c):
    """Lines 3205-3206: the day's weather.

    With probability one half the weather changes: ``TM = QT + INT (RND (1) * 41)``
    takes a new temperature between the month's minimum and forty degrees above it,
    then ``PP = (RND (1) < QP)`` draws the rain flag and ``W = INT ((TM + 10) / 20)``
    the temperature class. **Both draws happen whenever the weather changes**, and
    the first one happens whether or not it does.

    Line 3206 runs every day. If the rain flag is set it draws again for heavy
    precipitation, thirty per cent, so light and heavy alternate while the flag
    persists: ``W = 6 + Z + Z`` gives 6 rainy or 8 very rainy, and ``TR = .2 + .6 * Z``
    the inches.
    """
    st = c.st
    if c.rng.below("3205 weather change", num.HALF):
        st.TM = num.add(st.QT, num.int_(num.mul(c.rng.rnd1("3205 temperature"),
                                              num.parse("41"))))
        st.PP = num.ONE if c.rng.below("3205 rain flag", st.QP) else num.ZERO
        st.W = num.int_(num.div(num.add(st.TM, num.parse("10")), num.parse("20")))
        st.TM = st.W
    st.TR = num.ZERO
    st.TS = num.ZERO
    if not st.PP.is_zero():
        z = num.ONE if c.rng.below("3206 heavy rain", num.parse(".3")) else num.ZERO
        st.W = num.int_(num.add(num.parse("6"), num.add(z, z)))
        st.TR = num.add(num.parse(".2"), num.mul(num.parse(".6"), z))
        if num.lt(st.TM, num.TWO):
            # cold: it is snow instead, and eight times as much of it
            st.W = num.add(st.W, num.ONE)
            st.TS = num.mul(num.parse("8"), st.TR)
            st.TR = num.ZERO


def accumulate(c):
    """Line 3240: the rain and snow on the ground.

    ``AR = .9 * AR + TR: AS = .97 * AS + TS`` and then, if there is snow and the
    weather is warm or hotter, or very rainy, five units of snow melt and add half a
    unit of rain.
    """
    st = c.st
    st.AR = num.store(num.add(num.mul(num.parse(".9"), st.AR), st.TR))
    st.AS = num.store(num.add(num.mul(num.parse(".97"), st.AS), st.TS))
    if not st.AS.is_zero() and (num.gt(st.TM, num.TWO) or num.eq(st.W, num.parse("8"))):
        st.AR = num.add(st.AR, num.HALF)
        st.AS = num.sub(st.AS, num.parse("5"))
        if num.lt(st.AS, num.ZERO):
            st.AS = num.ZERO


def travel_today(c) -> Fac:
    """Lines 3244-3246: how far the wagon goes today.

    ``Z = 1 - AS / 40``, not below zero; ``V = BS * (C1 - .1 * H0) * NOT SD * Z``;
    and if ``1.1 * V > D`` then ``V = D``, so the party always arrives exactly. Speed
    falls by ten per cent for each sick or injured person and in proportion to the
    snow, reaching a standstill at forty units of snow; a stopped party does not move
    at all.
    """
    st = c.st
    z = num.sub(num.ONE, num.div(st.AS, num.parse("40")))
    if num.lt(z, num.ZERO):
        z = num.ZERO
    v = num.chain(st.BS).mul(num.sub(num.ONE, num.mul(num.parse(".1"),
                                                     num.parse(str(st.H0)))))
    v = v.mul(num.parse("0" if st.SD else "1")).mul(z).done()
    if num.gt(num.mul(v, num.parse("1.1")), st.D):
        v = st.D
    st.D = num.sub(st.D, v)
    st.M = num.add(st.M, v)
    st.V = v
    return v


def advance_date(c):
    """Lines 3255: the next day.

    February always has 28 days, even in 1848, and the year rolls over after
    December. The month also sets the climate again, though line 3100 does that every
    day anyway.
    """
    st = c.st
    ad = num.as_int(st.AD) + 1
    am = num.as_int(st.AM)
    ay = num.as_int(st.AY)
    if ad > MONTH_DAYS[am - 1]:
        ad = 1
        am += 1
        if am > 12:
            am = 1
            ay += 1
    st.AD = num.parse(str(ad))
    st.AM = num.parse(str(am))
    st.AY = num.parse(str(ay))
    st.QT = fn_w(st, 0)
    st.QP = fn_w(st, 1)


def health_today(c):
    """Lines 3207-3230: the seven penalties and the health total.

    ``ZT`` temperature, ``ZC`` clothing, ``ZF`` rations, ``ZP`` pace and weather,
    ``FS`` freezing and starving, ``H0`` the number sick and ``HR`` the day's events,
    added to nine tenths of yesterday's value.
    """
    st = c.st
    # 3207  ZT = TM - 3: if less than zero, 2 - TM
    zt = num.sub(st.TM, num.parse("3"))
    if num.lt(zt, num.ZERO):
        zt = num.sub(num.parse("2"), st.TM)
    st.ZT = zt
    # 3210  ZC = 5 - TM - TM - OP: if less than zero, 0
    zc = num.sub(num.sub(num.sub(num.parse("5"), st.TM), st.TM), st.OP)
    if num.lt(zc, num.ZERO):
        zc = num.ZERO
    st.ZC = zc
    # 3215  ZF = F0, or 8 when there is no food at all
    st.ZF = st.F0 if not num.eq(st.PF, num.ZERO) else num.parse("8")
    # 3220  ZP: twice the pace, plus one in rain or snow, plus two in heavy
    zp = num.parse("2" if st.P > num.ONE else ("4" if st.P > num.TWO else "0"))
    if num.gt(st.W, num.parse("5")):
        zp = num.add(zp, num.ONE)
    if num.gt(st.W, num.parse("7")):
        zp = num.add(zp, num.parse("2"))
    st.ZP = zp
    # 3225  the freeze and starve factor: +.8 on a bad day, halved on a good one
    x = num.gt(st.ZC, num.HALF)
    y = num.eq(st.PF, num.ZERO)
    z = num.mul(st.FS, num.HALF)
    if x or y:
        z = num.add(st.FS, num.parse(".8"))
    st.FS = z
    # 3230  H = .9 * H + ZT + ZC + ZF + ZP + FS + H0 + HR, then eat
    st.H = num.chain(st.H).mul(num.parse(".9")).add(st.ZT).add(st.ZC).add(st.ZF) \
        .add(st.ZP).add(st.FS).add(num.parse(str(st.H0))) \
        .add(num.parse(str(st.HR))).done()
    st.PF = num.sub(st.PF, st.FC)
    if num.lt(st.PF, num.ZERO):
        st.PF = num.ZERO
    return st.H


def count_ill(c):
    """Line 3200: every sick member loses a day, and recovers when it reaches zero."""
    st = c.st
    st.H0 = 0
    for i in range(5):
        if num.gt(st.H1[i], num.ZERO):
            st.H2[i] = num.sub(st.H2[i], num.ONE)
            st.H0 += 1
            if num.lt(st.H2[i], num.ONE):
                st.H1[i] = num.ZERO


def daily_cycle(c):
    """Lines 3100-3499: one day, in the order the listing gives.

    The order is the point: it fixes the order of the random draws. The steps are

    1. 3100 the month's minimum temperature and rain chance, and the travel
       interrupt, which polls the keyboard for Return;
    2. 3150 cap health at 139;
    3. 3160-3190 today's event chances and the random events;
    4. 3200 count down illnesses and count the sick;
    5. 3205-3206 the weather;
    6. 3207-3230 the health penalties and eating;
    7. 3235 a forced illness when health went above 139, away from a river;
    8. 3240 the rain and snow on the ground;
    9. 3244-3246 travel;
    10. 3250-3255 cap health again and advance the date.

    ``L0 = NOT D: NEXT L0`` at 3499 ends the loop only when ``D`` is exactly zero,
    which the clamp in step 9 guarantees.
    """
    st = c.st
    while st.D != num.ZERO:
        day_body(c)
    st.I[8] = st.PF


def day_body(c):
    """Lines 3100 to 3265: one day, whether or not the wagon moves.

    ``daily_cycle`` is this in a loop; ``run_stopped_days`` calls it once per
    stopped day, which is why it has to be separable -- the original reaches line
    3100 directly from line 500 rather than going round the loop.
    """
    st = c.st
    st.QT = fn_w(st, 0)
    st.QP = fn_w(st, 1)
    if not st.SD:
        poll_key(c)
    if num.gt(st.H, num.parse("139")):
        st.H = num.parse("139")
    event_loop(c)
    count_ill(c)
    weather(c)
    health_today(c)
    if not st.W1 and num.gt(st.H, num.parse("139")):
        from .illness import illness
        illness(c)
    accumulate(c)
    travel_today(c)
    if num.gt(st.H, num.parse("139")):
        st.H = num.parse("139")
    advance_date(c)
    c.trace.day(st, stopped=bool(st.SD))
    st.I[8] = st.PF


def poll_key(c):
    """Lines 800-810: press Return to stop and open the action menu.

    ``X = USR (C3)`` takes a key without waiting, and ``IF X = 141`` -- Return -- then
    the program opens the menu. No key means the party keeps travelling, which is
    what makes the daily cycle automatic.
    """
    if c.st.SD:
        return False
    if c.ui.poll_key() in ("\r", "\n"):
        from . import action
        action.action_menu(c)
        return True
    return False


# ------------------------------------------------------------- the event loop
def event_loop(c):
    """Lines 3180-3190: test the fifteen events, in order.

    ``HR = 0: IF NOT SD THEN FOR L8 = C0 TO RE: IF RND (1) < RE(L8) THEN ...``

    One draw per event tested, fifteen if the loop runs to the end, and the loop is
    skipped entirely on a stopped day -- resting, delayed or waiting at a river.

    **One event fires per day, not several.** The paper says the loop "does not stop
    after the first event ... so two events can occur on one day", but line 3180 ends
    with ``L8 = 20`` after every firing event, and ``NEXT L8`` then leaves the loop.
    The source has authority, so one event it is; see ``GAPS.md``.
    """
    st = c.st
    st.HR = num.ZERO
    if st.SD:
        return
    # 3160 the chances that change every day
    st.RE[0] = num.ONE if num.gt(st.AS, num.parse("30")) else num.ZERO
    st.RE[14] = num.mul(num.HALF, num.ONE if num.lt(st.AR, num.parse(".1")) else num.ZERO)
    st.RE[3] = num.add(num.parse(".01"), num.div(st.H, num.parse("1500")))
    st.RE[4] = num.ONE if num.lt(st.D, num.parse(str(st.DL))) else num.ZERO
    st.RE[5] = num.mul(num.parse(".05"),
                       num.ONE if num.eq(st.PF, num.ZERO) else num.ZERO)
    st.RE[6] = num.add(num.ONE if num.gt(st.W, num.parse("7")) else num.ZERO,
                       num.mul(num.parse(".15"),
                               num.ONE if num.lt(st.TM, num.TWO) else num.ZERO))
    for which in range(15):
        if not c.rng.below(f"3180 event {which}", st.RE[which]):
            continue
        from . import events
        events.fire(c, which)
        if num.gt(st.B, num.ZERO):
            from . import action
            action.action_menu(c)
        break                     # L8 = 20: at most one event a day


# ------------------------------------------------------------------- segments
def choose_segment(c):
    """Lines 2100-2120: South Pass and the Blue Mountains each lead two ways.

    ``IF NOT VAL (LM$(LM,3)) THEN RETURN`` -- no second segment, no question.
    """
    st = c.st
    from . import common
    if st.LM == 16:
        from . import endl
        endl.the_dalles(c)
        return
    travel_screen(c)
    second = L.LM_SEGMENT2[st.LM]
    if not second:
        # line 2105: no second segment, so no question -- line 2200 loads the only
        # one there is
        return L.LM_SEGMENT[st.LM]
    c.ui.print("The trail divides here.  You may:")
    c.ui.print()
    for i, seg in enumerate((L.LM_SEGMENT[st.LM], second), 1):
        dest = L.SEG_ENDS_AT[seg]
        c.ui.print(f"{i}. head for {L.LM_NAMES[dest]}")
    c.ui.print("3. see the map")
    c.ui.print()
    c.ui.print("What is your choice? ")
    from .ui import ALLOWED
    a = c.ui.key(ALLOWED["SEGMENT"], 1)
    choice = int(a) if a and a.isdigit() else 3
    if choice == 3:
        from . import maplib
        maplib.show(c)
        return L.LM_SEGMENT[st.LM]
    return second if choice == 2 else L.LM_SEGMENT[st.LM]


def load_segment(c, seg: int):
    """Line 2200: ``Z = VAL(LM$(LM,Z+1)): D = LM(Z,0): MD = LM(Z,1): NM = LM(Z,2)``."""
    st = c.st
    st.Z = num.parse(str(seg))
    st.D = num.parse(str(L.SEG_MILES[seg]))
    st.MD = num.parse(str(L.SEG_SPEED[seg]))
    st.NM = L.SEG_ENDS_AT[seg]
    from . import common
    c.ui.print()
    c.ui.print(num.str_(st.D) + " miles")
    c.ui.print(f"From {L.LM_NAMES[st.LM]} it is {num.str_(st.D)} miles to "
               f"{L.LM_NAMES[st.NM]}.")
    common.wait_key(c)


def start_segment(c):
    """Line 3000: ``PF = I(8)``, ``SN = NM * 100 + LM``, ``DD = D``, ``SD = 0``, then
    the speed routine and the segment's event chances."""
    st = c.st
    st.PF = st.I[8]
    st.Z = num.parse(str(st.NM * 100 + st.LM))
    st.SN[st.S] = st.Z.to_int()
    st.DD = st.D
    st.SD = 0
    speed(c)
    # line 3060: the chances that are set when a segment begins, so they do not
    # change part way along it
    st.RE[8] = num.add(num.parse(".04"),
                       num.mul(num.parse(".03"),
                               num.ONE if st.ZO > 2 else num.ZERO))
    st.RE[10] = num.mul(num.parse(".05"), num.ONE if st.ZO > 2 else num.ZERO)
    st.RE[11] = num.mul(num.parse(".04"),
                        num.ONE if (num.as_int(st.AM) > 4
                                    and num.as_int(st.AM) < 10) else num.ZERO)
    find_grave(c)


# --------------------------------------------------------------- the main loop
def run(c):
    """Lines 1000-1020: the journey, landmark by landmark.

    ``1000`` draws the first dialogue, ``1005`` asks whether to look around,
    ``1015`` forces the crossing at a river and then chooses the segment, and
    ``1016`` runs the daily cycle until the party arrives.
    """
    from . import common
    c.set_program("OREGON TRAIL")
    st = c.st
    while True:
        arrive(c)
        look_around = False
        if st.LM:
            from .ui import ALLOWED
            c.ui.print(f"You are now at {L.LM_NAMES[st.LM]}.  Would you like to "
                       f"look around? ")
            look_around = common.yes_no(c) == "Y"
            st.Q[st.Q1] = st.LM
            st.Q1 += 1
        if look_around:
            st.LL = 0
            from . import action
            action.action_menu(c)
            st.LL = 1
        # 1015: a river crossing, then the check for oxen, then the segment
        while True:
            if L.LM_TYPE[st.LM] == 2:
                from . import river
                river.crossing(c)
                if st.B > 0:
                    from . import action
                    action.action_menu(c)
                    continue
            if num.eq(st.I[2], num.ZERO):
                check_oxen(c)
            seg = choose_segment(c)
            break
        from . import endl
        if st.NM == 17:
            endl.arrive_willamette(c)
            return "WIN"
        # 1016: line 2200 loads the chosen segment, then line 3000 starts it
        st.LL = 1
        load_segment(c, seg)
        start_segment(c)
        travel_screen(c)
        daily_cycle(c)
        st.LM = st.NM
        if st.LM == 5:
            from . import flip
            flip.to_side_2(c)
        if st.LM == 17:
            from . import endl
            endl.arrive_willamette(c)
            return "WIN"


def arrive(c):
    """Lines 1000-1005: arrival at a landmark.

    ``A = INT (RND (1) * 3)`` picks the first of the three monologues, and
    ``ZO = (LM > 2) + (LM > 5) + (LM > 10) + (LM > 13)`` sets the climate zone, which
    holds for the segment that follows. **This draw happens at every landmark,
    including Independence**, which is what Appendix G.2 records.
    """
    st = c.st
    st.A = c.rng.int_range("1000 arrival dialogue", 3)
    st.ZO = climate_zone(st.LM)


def check_oxen(c):
    """Line 21000: no oxen, so the journey stops here until a trade supplies some."""
    st = c.st
    from . import common
    c.ui.print("You are unable to continue your journey.  You have no oxen to pull "
               "the wagon.")
    common.wait_key(c)
    st.B = 2
