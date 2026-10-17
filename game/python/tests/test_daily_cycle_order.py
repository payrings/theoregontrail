"""Two details of the daily cycle that a day-by-day trace of the original exposed.

1. Line 3160 works out the day's event chances, and it has no ``IF NOT SD``:

       3160 RE(C0) = (AS > 30):RE(14) = P5 * (AR < .1):RE(C3) = .01 + H / 1500: ...

   so the chances are refreshed on a stopped day too. When an event loses days
   (lines 550-570, ``GOSUB 500``), the stopped days run inside that day's event
   loop, and the events still to be tested are tested against the chances of the
   last stopped day. Rain on a stopped day can therefore rule out "bad water"
   (``RE(14)``) for the rest of the loop.

2. Line 3499 is ``L0 = NOT D: NEXT L0: I(8) = PF``. The statements after
   ``NEXT L0`` run only when the loop ends, which is when ``D`` is exactly zero:
   on arrival, and after each stopped day. On a travelling day ``I(8)`` keeps the
   value it had.
"""

from __future__ import annotations

from oregon import num, trail


def _context(tmp_path, draws="0.999 "):
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.state import State
    from oregon.ui import ScriptedUI
    c = Context(ui=ScriptedUI([" "] * 400, allow_repeat=True, max_prompts=4000),
                rng=ScriptedRnd(draws * 5000),
                files=Files(tmp_path / "data"))
    st = State()
    st.NP = 5
    st.I[2] = num.parse("8")
    st.I[3] = num.parse("5")
    st.I[8] = num.parse("1000")
    st.PF = st.I[8]
    st.H = num.parse("20")
    st.TM = num.parse("3")
    st.W = num.parse("2")
    st.P = num.parse("1")
    st.R = num.parse("1")
    c.st = st
    trail.speed(c)
    return c


def test_event_chances_are_refreshed_on_a_stopped_day(tmp_path):
    c = _context(tmp_path)
    st = c.st
    st.SD = 1
    st.AR = num.parse(".5")             # wet ground: no bad water
    st.RE[14] = num.parse(".5")         # the chance left over from a dry morning
    drawn = len(c.rng.log)
    trail.event_loop(c)
    assert num.eq(st.RE[14], num.ZERO), "3160 must run on a stopped day as well"
    assert len(c.rng.log) == drawn, "no event may be tested on a stopped day"


def test_food_store_is_not_copied_on_a_travelling_day(tmp_path):
    c = _context(tmp_path)
    st = c.st
    st.D = num.parse("500")             # far from the next landmark
    assert trail.day_body(c)
    assert num.lt(st.PF, num.parse("1000")), "the party should have eaten"
    assert num.eq(st.I[8], num.parse("1000")), "I(8) must keep its value while D > 0"


def test_food_store_is_copied_on_arrival(tmp_path):
    c = _context(tmp_path)
    st = c.st
    st.D = num.parse("1")               # arrives today
    assert trail.day_body(c)
    assert st.D == num.ZERO
    assert num.eq(st.I[8], st.PF), "3499 copies PF into I(8) when the loop ends"
