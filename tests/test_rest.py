"""Line 4505: resting runs one to nine days of the daily cycle.

    4505 IF SD THEN F9 = 0:JQ = P:P = 0:ZX = D:ZY = M:D = 0: FOR K1 = 1 TO SD: GOSUB 3100:
         & WIND: GOSUB 250: & CO,,X5: PRINT CE$TD$CC$: NEXT :SD = 0:D = ZX:M = ZY:P = JQ

It sets ``D = 0`` and then calls line 3100 **directly**, once per day. Calling the day
*loop* instead does nothing at all, because the loop's condition is line 3499,
``L0 = NOT D`` -- and ``D`` has just been set to zero. That is what the code did, so a
rest consumed no food, passed no day and left health untouched, however many times it
was repeated. Reported from play: FINDINGS.md 23.3.
"""

from __future__ import annotations

import pytest

from oregon import action, common, num, trail
from oregon.data.text import HEALTH


def rested(tmp_path, days="9", rounds=1, h="120"):
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.state import State
    from oregon.ui import ScriptedUI
    c = Context(ui=ScriptedUI([days] * rounds + [" "] * 400, allow_repeat=True,
                               max_prompts=4000),
                rng=ScriptedRnd("0.5 " * 20000),
                files=Files(tmp_path / "data"))
    st = State()
    st.NP = 5
    st.I[2] = num.parse("8")
    st.I[3] = num.parse("5")
    st.I[8] = num.parse("1000")
    st.PF = st.I[8]
    st.H = num.parse(h)
    st.TM = num.parse("3")          # warm
    st.W = num.parse("2")           # cool, dry
    st.P = num.parse("1")           # steady
    st.R = num.parse("1")           # filling
    c.st = st
    trail.speed(c)                  # line 650, as the segment start does
    before = (num.as_float(st.H), num.as_float(st.PF), common.date_text(c))
    for _ in range(rounds):
        action.do_rest(c)
    return c, before


def test_resting_passes_the_days(tmp_path):
    """Nine days, twice: the date must move eighteen days."""
    c, before = rested(tmp_path, rounds=2)
    st = c.st
    assert common.date_text(c) != before[2], "no day passed at all"
    assert st.AD.to_float() >= 19, f"nine days twice should reach the 19th: {st.AD}"


def test_resting_improves_health(tmp_path):
    """``H`` is 0 when perfect and higher is worse, so improving means falling. With no
    pace penalty, no events and a mild day, resting drives H down towards ten times the
    daily penalty."""
    c, before = rested(tmp_path, rounds=3)
    assert num.as_float(c.st.H) < before[0] - 20, (
        f"health did not improve: {before[0]} -> {num.as_float(c.st.H)}")
    assert c.st.health_band() < 3, (
        f"band still {HEALTH[c.st.health_band()]!r}")


def test_resting_consumes_food(tmp_path):
    """3230: ``PF = PF - FC`` and ``FC = NP * (4 - R)``, so five on filling rations
    eat 15 a day whatever else they are doing."""
    c, before = rested(tmp_path, days="9", rounds=2)
    assert num.as_float(c.st.PF) < before[1], "no food was eaten while resting"


def test_resting_costs_no_pace_penalty(tmp_path):
    """3220: ``ZP = (W > 5) + (W > 7) + P + P`` and the paper notes "pace is 0 while
    resting or delayed", so ZP is 0 on a dry mild rest."""
    c, _ = rested(tmp_path, days="9")
    assert num.as_float(c.st.ZP) == 0


def test_resting_leaves_the_wagon_where_it_was(tmp_path):
    """4505 saves ``D`` in ZX and ``M`` in ZY and restores both, and ``P`` in JQ."""
    c = rested(tmp_path, days="9")[0]
    st = c.st
    st.D = num.parse("50")
    st.M = num.parse("7")
    st.P = num.parse("2")
    action.do_rest(c)
    assert num.as_float(st.D) == 50 and num.as_float(st.M) == 7, "the wagon moved"
    assert num.as_float(st.P) == 2, "the pace was not restored"


def test_a_single_day_rest_is_the_same_as_a_delay(tmp_path):
    """``run_stopped_days`` had this right all along, which is why a one-day river
    delay visibly cost food and health while a nine-day rest did not."""
    c, before = rested(tmp_path, days="1")
    assert num.as_float(c.st.PF) < before[1]
