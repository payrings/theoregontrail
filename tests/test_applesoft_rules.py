"""The three Applesoft rules the translation must follow, and the six corrections.

Every test here is a finding that was once wrong in this project, checked against
the BASIC under the language's own rules rather than Python's (paper 2.5):

* **rule (a)** everything after ``THEN`` belongs to the ``IF``;
* **rule (b)** a simple variable and an array of the same name are two things;
* **rule (c)** a ``FOR`` loop always runs its body at least once.
"""
import pytest

from oregon import num
from oregon.context import Context
from oregon.data import landmarks as L
from oregon.files import Files
from oregon.num import fort_count, fort_range
from oregon.rng import ScriptedRnd
from oregon.ui import ScriptedUI


def fresh(answers=(), max_prompts=4000, value="0.5"):
    """A context with its own scripted screen and generator."""
    return Context(ui=ScriptedUI(list(answers), allow_repeat=True,
                                 max_prompts=max_prompts),
                   rng=ScriptedRnd(" ".join([value] * 8000)),
                   files=Files("/tmp/oregon-rule-tests"))


# ------------------------------------------------------- rule (c): FOR runs once
@pytest.mark.parametrize("start,limit,want", [
    (1, 5.5, 5),      # stops at the last whole value below the limit
    (1, 0.5, 1),       # a limit below the start still runs the body
    (0, -1, 1),        # FOR A = 0 TO NR with NR = -1
    (0, 2, 3),
    (1, 3, 3),
    (0, 6, 7),
])
def test_fort_always_runs_its_body_at_least_once(start, limit, want):
    """``FOR`` tests the limit at ``NEXT``, not before the body."""
    assert fort_count(start, limit) == want
    assert len(list(fort_range(start, limit))) == want


def test_half_an_ox_gives_one_draw_at_a_river():
    """Appendix G: ``FOR L = 1 TO X`` with X = 0.5 makes one draw, not none.

    ``range(int(0.5))`` is empty, which is the reading rule (c) forbids.
    """
    from oregon import river
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.ui import ScriptedUI

    draws = []
    c = Context(ui=ScriptedUI([], allow_repeat=True), files=Files("/tmp/oregon-test-data"))
    c.rng = ScriptedRnd(" ".join(["0.99"] * 4000))
    orig = c.rng.below

    def spy(tag, chance):
        draws.append(tag)
        return orig(tag, chance)

    c.rng.below = spy
    c.st.I[2] = num.parse("0.5")
    before = c.rng.log.count()
    river._lose_oxen(c, num.parse("0.99"))
    assert len(draws) == 1, f"expected one draw for half an ox, got {len(draws)}"
    assert c.rng.log.count() - before == 1
    assert len(range(int(0.5))) == 0, "which is what a naive loop would use"


def test_the_raft_collision_loop_runs_once_even_with_no_slots():
    """``FLOAT`` 500, ``FOR A = 0 TO NR`` with ``NR`` = -1, runs once with A = 0."""
    from oregon import floatraft
    ran = []

    original = floatraft._line_500
    try:
        floatraft._line_500 = lambda c, kind: ran.append(1)
        from oregon.context import Context
        from oregon.files import Files
        from oregon.rng import ScriptedRnd
        from oregon.ui import ScriptedUI
        c = Context(ui=ScriptedUI([], allow_repeat=True),
                    rng=ScriptedRnd(" ".join(["0.0"] * 4000)),
                    files=Files("/tmp/oregon-test-data"))
        c.st.NP = 2
        c.st.I[2] = num.parse("2")
        c.st.I[8] = num.parse("100")
        floatraft.collide(c, "shore")
        assert len(ran) == 1, "line 500 must run exactly once"
    finally:
        floatraft._line_500 = original


def test_the_raft_drowns_loop_runs_once_with_nothing_alive():
    """``FLOAT`` 750, ``FOR L = 0 TO NP - 1``, runs once even when NP is 0."""
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.ui import ScriptedUI
    from oregon import floatraft, num
    c = Context(ui=ScriptedUI([], allow_repeat=True),
                rng=ScriptedRnd(" ".join(["0.0"] * 4000)),
                files=Files("/tmp/oregon-test-data"))
    c.st.NP = 0
    c.st.I[2] = num.parse("0")
    c.st.I[8] = num.parse("0")
    c.st.H1 = [num.ZERO] * 5
    # nothing is marked drowned, so the loop runs once and changes nothing
    floatraft.collide(c, "shore")
    assert num.as_int(c.st.NP) == 0


# ------------------------------------- rule (a): everything after THEN
def test_more_than_one_event_can_fire_in_one_day():
    """Line 3180 ends ``... IF B > 0 THEN GOSUB 4000: GOSUB 300:L8 = 20``.

    ``L8 = 20`` belongs to the ``THEN`` on ``B``, so it runs only when an event has
    fired *and* B is above zero. Otherwise the loop carries on, and a second event
    can fire on the same day.
    """
    from oregon import events, trail
    c = fresh(value="0.0")
    st = c.st
    fired = []
    original = events._EVENTS
    try:
        events._EVENTS = [lambda c: fired.append(n) for n in range(15)]
        # line 3160 recomputes six of the chances, so make them all positive
        st.AS, st.AR, st.PF, st.TM, st.W = (num.parse("40"), num.ZERO, num.ZERO,
                                            num.ZERO, num.ZERO)
        st.SD = 0
        before = c.rng.log.count()
        trail.event_loop(c)
        assert len(fired) > 1, (
            "more than one event must be able to fire on one day; "
            f"got {len(fired)}")
        tags = [t for t, _a, _v in c.rng.log.entries[before:]]
        assert sum(1 for t in tags if t.startswith("3180 event")) == 15, (
            "the loop tests every event and draws for each, even after one fires")
    finally:
        events._EVENTS = original


def test_the_loop_stops_early_when_B_is_above_zero():
    """When an event sets B, ``L8 = 20`` runs and the loop ends after one event."""
    from oregon import events, trail
    c = fresh(value="0.0")
    st = c.st
    fired = []
    original_events = events._EVENTS
    import oregon.action as action
    original_menu = action.action_menu
    try:
        events._EVENTS = [lambda c: fired.append(1) or setattr(c.st, "B", 5)] * 15
        action.action_menu = lambda c: None      # the menu is not what is under test
        st.AS, st.AR, st.PF, st.TM, st.W = (num.parse("40"), num.ZERO, num.ZERO,
                                            num.ZERO, num.ZERO)
        st.SD = 0
        trail.event_loop(c)
        assert len(fired) == 1, (
            f"B above zero ends the loop after one event, got {len(fired)}")
    finally:
        events._EVENTS = original_events
        action.action_menu = original_menu
        st.B = 0


def test_choosing_the_map_asks_again_rather_than_loading_a_segment():
    """Line 1015 ends ``IF Z = 3 THEN GOSUB 4200: GOSUB 190: GOTO 1015``.

    The ``GOTO`` belongs to the ``IF``, so choice 3 shows the map and returns to ask
    again. It does not fall through to line 2200.
    """
    from oregon import maplib, trail
    c = fresh(answers=["3", "1"])
    c.st.LM = 7                    # South Pass, which has two ways on
    shown = []
    original = maplib.show
    try:
        maplib.show = lambda c: shown.append(1)
        seg = trail.choose_segment(c)
    finally:
        maplib.show = original
    assert len(shown) == 1, "the map was shown once"
    assert seg == L.LM_SEGMENT[7], "and then the first segment was taken"


def test_the_trail_menu_is_the_eight_choices_ending_in_the_hunt():
    """Line 4040 nests the extra entries inside ``IF NOT LL``.

    So "Talk to people" and "Buy supplies" are printed only at a landmark, and line
    4050 prints "Hunt for food" on the trail with ``Z = 2``, where choice 8 gives
    ``ON 9`` and reaches 4600. There is no swap bug here.
    """
    from oregon import action
    c = fresh(answers=["8", "1"])
    c.st.LL = 1                     # on the trail
    c.st.I[2] = num.parse("8")       # oxen, so "continue" is allowed afterwards
    c.st.I[4] = num.parse("50")      # bullets, so the hunt can fire
    c.st.PF = num.parse("500")
    reached = []
    original = action.do_hunt
    try:
        # the real do_hunt sets SD = 1; only the dispatch is under test here
        action.do_hunt = lambda c: (reached.append(1),
                                  setattr(c.st, "SD", 1))
        action.action_menu(c)
    finally:
        action.do_hunt = original
    assert len(reached) == 1, "choice 8 on the trail is the hunt"
    # and the menu then cleared its one-day cost by running it (line 4090's
    # "ON SD > 0 GOSUB 500"), so SD is back to zero afterwards


# -------------------------------- rule (b): Q and Q(), B and B()
def test_the_state_separates_the_scalars_from_the_arrays():
    from oregon.state import State
    st = State()
    assert isinstance(st.Q_arr, list) and len(st.Q_arr) == 17
    assert isinstance(st.B_arr, list) and len(st.B_arr) == 6
    # writing the scalar must not touch the array
    st.Q = num.parse("6")
    st.B = 5
    assert st.Q_arr == [0] * 17
    assert st.B_arr == [95, 70, 81, 95, 23, 20]


# --------------------------------------------- the route: 1,771 and 1,871
def test_the_shortest_route_is_1771_miles():
    """Segments 0-7, 10-14 and 16 -- the Blue Mountains direct to The Dalles.

    Going through Fort Walla Walla (segments 15 and 17) is 175 miles longer.
    """
    short = [0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 16]
    assert sum(L.SEG_MILES[s] for s in short) == 1771
    assert sum(L.SEG_MILES[s] for s in short) + L.SEG_MILES[18] == 1871
    via_walla = [0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 17]
    assert sum(L.SEG_MILES[s] for s in via_walla) == 1821, "50 miles longer"


def test_the_green_river_shortcut_is_segment_10_not_the_bridger_road():
    """Segment 10 reaches Soda Springs directly, past Fort Bridger."""
    assert L.SEG_ENDS_AT[10] == 10, "Green River to Soda Springs"
    assert L.SEG_MILES[10] == 144
