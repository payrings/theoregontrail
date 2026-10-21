"""Places where the rebuild once disagreed with the BASIC listing or the ROM.

Every test here drives the real module with scripted draws and checks what the
listing (or the Apple IIe ROM's own routine) does. They are grouped by the routine
that was wrong. Where the right answer is a number that only the interpreter can
give, the expected values are in ``tests/data`` and were recorded from the ROM
(``str_cases.json`` here, ``fidelity.json`` for the formulas).

None of these tests passed before the code was corrected; the comments say what
the old code did.
"""
import json
import pathlib

import pytest

from oregon import applesoft, num
from oregon.context import Context
from oregon.data import hiscore as HIS
from oregon.data import landmarks as L
from oregon.files import Files
from oregon.rng import ScriptedRnd
from oregon.ui import AutoUI, ScriptedUI

DATA = pathlib.Path(__file__).resolve().parent / "data"


def make(tmp_path, answers=(), values=None, fill=0.5, max_prompts=400):
    """A context whose draws are *values*, then *fill* for ever."""
    draws = list(values or []) + [fill] * 20000
    ui = ScriptedUI(list(answers), allow_repeat=True, max_prompts=max_prompts)
    return Context(ui=ui, rng=ScriptedRnd(draws), files=Files(tmp_path / "data"))


def said(c):
    return " ".join(c.ui.out)


def stub_days(monkeypatch):
    """Replace the daily cycle, so a test spends only the draws it scripts."""
    from oregon import trail
    days = []

    def run_stopped_days(c):
        days.append(c.st.SD)
        c.st.SD = 0

    monkeypatch.setattr(trail, "run_stopped_days", run_stopped_days)
    return days


# ===================================================================== arithmetic
def test_storing_a_value_does_not_add_a_unit_in_the_last_place():
    """ROUND.FAC ($EB72) adds one only when bit 7 of the extension byte is set.

    The result of an operation is already rounded, so storing it changes nothing.
    The old ``round_fac`` forced the bit, so ``20`` became ``85 20 00 00 01``.
    """
    twenty = num.parse("20")
    assert num.store(twenty).raw().hex() == "8520000000"
    assert num.store(num.mul(num.parse("4"), num.parse("5"))).raw().hex() == "8520000000"
    assert num.store(num.add(num.parse("12"), num.parse("8"))).raw().hex() == "8520000000"
    assert num.store(num.div(num.ONE, num.parse("3"))).raw().hex() == "7f2aaaaaab"


def test_a_chain_is_stored_once_at_the_end():
    chain = num.Chain(num.parse("4")).mul(num.parse("5")).done()
    assert chain.raw().hex() == "8520000000"


def test_str_matches_the_roms_number_to_text_routine():
    """FOUT ($ED34) rounds to nine digits and puts no space before a positive number.

    The recorded cases are the ROM's own output, so they are checked against the
    transcription of its routine: with a ROM image installed the comparison would
    be the ROM against itself.
    """
    cases = json.loads((DATA / "str_cases.json").read_text())["cases"]
    was = applesoft.current()
    applesoft.use("exact")
    try:
        wrong = []
        for case in cases:
            got = num.str_(applesoft.Fac(bytes.fromhex(case["fac"])))
            if got != case["text"]:
                wrong.append((case["fac"], case["text"], got))
    finally:
        applesoft.use("rom" if applesoft.rom_available() else "exact")
    assert not wrong, f"{len(wrong)} of {len(cases)} differ; first: {wrong[0]}"


def test_str_of_the_numbers_the_game_prints():
    """Examples from the screens: a depth, a distance, a date and a sum of money."""
    assert num.str_(num.div(num.parse("47"), num.parse("10"))) == "4.7"
    assert num.str_(num.div(num.ONE, num.parse("100"))) == ".01"
    assert num.str_(num.parse("5")) == "5"
    assert num.str_(num.ZERO) == "0"
    assert num.str_(num.parse("-5")) == "-5"
    assert num.str_(num.parse("12345.6789")) == "12345.6789"


def test_money_and_dates_have_no_stray_spaces(tmp_path):
    """Listing 200: ``K$ = "0" + STR$(V)`` then ``RIGHT$(K$, 2)`` for the cents."""
    from oregon import common
    c = make(tmp_path)
    assert common.money(c, num.parse("800")) == "800.00"
    assert common.money(c, num.ZERO) == "0.00"
    assert common.money(c, num.parse(".05")) == "0.05"
    assert common.money(c, num.parse("1234.567")) == "1234.57"
    c.st.AM, c.st.AD, c.st.AY = num.parse("4"), num.parse("1"), num.parse("1848")
    assert common.date_text(c) == "April 1, 1848"


def test_lost_days_read_naturally(tmp_path, monkeypatch):
    """Line 550: ``STR$(XX)`` has no leading space, so "Lose 1 day."."""
    from oregon import trail
    stub_days(monkeypatch)
    c = make(tmp_path, fill=0.0)
    trail.lose_days(c, "test", 1, "Heavy fog")
    assert "Heavy fog.  Lose 1 day." in said(c)


def test_the_river_menu_reads_naturally(tmp_path, monkeypatch):
    """"River depth: 4.7 feet" -- not four digits of noise after the point."""
    from oregon import river
    c = make(tmp_path, answers=["3", "3"], max_prompts=12)
    c.st.LM = 2

    def conditions(c):
        c.st.RW = num.parse("400")
        c.st.RD = num.div(num.parse("47"), num.parse("10"))
        c.st.RS = num.parse("4")
        c.st.RB = 0

    monkeypatch.setattr(river, "conditions", conditions)
    monkeypatch.setattr(river, "information", lambda c, which: None)
    with pytest.raises(AssertionError, match="looping"):
        river.crossing(c)
    text = said(c)
    assert "River depth: 4.7 feet" in text
    assert "400 feet across, and 4.7 feet deep" in text


# ================================================================== the top ten
@pytest.mark.parametrize("score,place", [(8000, 0), (7000, 1), (5000, 2), (3000, 3),
                                         (2945, 4), (300, 9)])
def test_a_new_score_goes_in_order_and_nothing_else_moves(tmp_path, score, place):
    """WIN 510-520: the entries below the new one move down one place, the last drops.

    A score equal to an old one goes below it (the test at 515 reads the entry that
    has just been copied down). The old code overwrote a surviving entry and
    duplicated its neighbour for every place but first.
    """
    from oregon import win
    c = make(tmp_path, answers=["NEW", "N"])
    out = win.insert(c, HIS.original(), score, "Greenhorn")
    old = [e[0] for e in HIS.original()]
    want = old[:place] + ["NEW"] + old[place:]
    assert [e[0] for e in out] == want[:10]
    assert [e[1] for e in out] == sorted((e[1] for e in out), reverse=True)


def test_changing_the_name_keeps_the_same_place(tmp_path):
    """Line 530 asks again for the *name*; the list is not rearranged a second time."""
    from oregon import win
    c = make(tmp_path, answers=["AAA", "Y", "BBB", "N"])
    out = win.insert(c, HIS.original(), 3000, "Adventurer")
    names = [e[0] for e in out]
    assert names.count("BBB") == 1 and "AAA" not in names
    assert names[3] == "BBB" and len(names) == 10 and len(set(names)) == 10


def test_an_empty_name_is_not_questioned(tmp_path):
    """The BASIC takes whatever INP returns; it has no "no name" check."""
    from oregon import win
    c = make(tmp_path, answers=["", "N"])
    out = win.insert(c, HIS.original(), 8000, "Trail guide")
    assert out[0][0] == "" and out[1][0] == "Stephen Meek"
    # the name, then line 530's "Would you like to make any changes?" -- nothing else
    assert c.ui.prompts == 2


# ================================================================== the raft game
@pytest.fixture
def raft(tmp_path, monkeypatch):
    """The rafting game with no waiting, a count of passes, and the collisions noted.

    The game looks at the keyboard once on every pass (``KEY = USR (3)``), so the
    number of times it does so is the number of passes.
    """
    from oregon import floatraft
    from test_endings import party
    monkeypatch.setattr(floatraft, "PASSES_PER_SECOND", 10 ** 9)
    state = {"pass": 0, "hits": []}

    def collide(c, kind):
        state["hits"].append((state["pass"], kind))
        return None

    def counted_party(**kw):
        c, ui = party(**kw)
        real = ui.poll_key

        def poll_key():
            state["pass"] += 1
            return real()

        ui.poll_key = poll_key
        return c, ui

    monkeypatch.setattr(floatraft, "collide", collide)
    return floatraft, counted_party, state


def test_an_unsteered_raft_bounces_off_each_bank_in_turn(raft):
    """Listing 400: ``COL = 0: IF HP < 1 OR HP > 16 THEN COL = 1: DIR = -DIR``.

    The raft starts at 16 heading left. It reaches 0 on pass 16, turns round, and
    reaches 17 seventeen passes later, and so on. The old code clamped the position
    and kept the direction, so it hit the left bank on every pass from the 16th.
    """
    floatraft, party, state = raft
    c, ui = party(value="0.9")
    assert floatraft.run(c) == "WIN"
    assert [p for p, _k in state["hits"]] == [16 + 17 * k for k in range(13)]
    assert {k for _p, k in state["hits"]} == {"shore"}


def test_a_raft_that_lands_is_not_dealt_with_as_a_collision(raft, monkeypatch):
    """Listing 1115 lands the raft before 1170 handles the shore.

    Three passes of waiting (right, nothing, nothing, left) put the raft at 17 on
    pass 206, which is after 205: it lands, and does not hit the bank.
    """
    floatraft, party, state = raft
    c, ui = party(value="0.9")
    # the two instruction screens take a key each before the first pass
    ui.keys = [" ", " ", "h", None, None, "l"]
    assert floatraft.run(c) == "WIN"
    assert [p for p, _k in state["hits"]] == [19 + 17 * k for k in range(11)]
    assert state["pass"] == 206


def _rock_run(raft, monkeypatch, draws):
    """Run the game with scripted draws; return ``(pass, x, y)`` for every rock tested."""
    floatraft, party, state = raft
    c, ui = party(value="0.9")
    c.rng = ScriptedRnd(list(draws) + [0.9] * 20000)
    seen = []
    monkeypatch.setattr(floatraft, "_overlap",
                        lambda box, rx, ry: seen.append((state["pass"], rx, ry)) or False)
    floatraft.run(c)
    return seen


def test_a_rock_on_the_bottom_edge_starts_at_x_as_drawn(raft, monkeypatch):
    """Listing 300: ``RX = INT (10 * RND (1))`` -- used as it stands, not times ten."""
    # pass 1: slot 0 fills (roll 1), type draw 0.05 is a bottom rock, x draw 0.55 -> 5
    seen = _rock_run(raft, monkeypatch, [0.0, 0.05, 0.55])
    assert seen[0] == (1, 5 + 8, 175 - 4)       # then moved once, 8 right and 4 up


def test_a_rock_leaves_when_it_reaches_x_240(raft, monkeypatch):
    """Listing 600 keeps a rock only while ``RX < 240 AND RY > 10``.

    A rock that starts at x = 0 is at 240 on pass 30 and is dropped then, so the slot
    can take a new rock on pass 31. With the old test (``RX > 240``) it was dropped a
    pass later and the new rock came a pass late.
    """
    # pass 1 fills slot 0 (a bottom rock at x = 0). Lines 1070 and 1075 draw for both
    # slots on every pass, filled or not (AND does not short-circuit), and 0.9 fills
    # nothing: 1 + 2 * 29 draws up to pass 30. On pass 31 slot 0 takes a left-edge rock.
    seen = _rock_run(raft, monkeypatch, [0.0, 0.05, 0.05] + [0.9] * 59 + [0.0, 0.5, 0.03])
    assert [p for p, rx, ry in seen if (rx, ry) == (8, 54 - 4)][0] == 31


def test_a_rock_leaves_when_it_reaches_y_10(raft, monkeypatch):
    """... and when ``RY`` reaches 10 (the old code dropped it only below 10)."""
    # type draw 0.5 is a left-edge rock; y = 50 + INT (120 * 0.03 + 1) = 54
    seen = _rock_run(raft, monkeypatch, [0.0, 0.5, 0.03])
    assert seen[-1][1:] == (8 * 11, 54 - 4 * 11)


# ================================================================== the journey loop
def test_the_river_is_crossed_once_on_arrival(tmp_path, monkeypatch):
    """Listing 1015: after the river, the oxen check and the action menu, the
    program goes on to the segment menu. It goes back to the river only when the
    map was chosen at a fork. The old loop did ``continue`` after the menu."""
    from oregon import action, river, trail

    class Stop(Exception):
        pass

    c = make(tmp_path, answers=["N"])
    c.st.LM = 9                                   # the Green River
    crossings = []

    def crossing(c):
        crossings.append(num.as_int(c.st.I[2]))
        if len(crossings) > 1:
            raise AssertionError("the river was crossed a second time")
        c.st.I[2] = num.ZERO                      # the river took every ox
        return True

    def action_menu(c):
        c.st.I[2] = num.parse("8")                # a trade supplied oxen
        c.st.B = 0

    def choose_segment(c):
        raise Stop

    monkeypatch.setattr(trail, "arrive", lambda c: None)
    monkeypatch.setattr(river, "crossing", crossing)
    monkeypatch.setattr(action, "action_menu", action_menu)
    monkeypatch.setattr(trail, "choose_segment", choose_segment)
    c.st.I[2] = num.parse("18")
    with pytest.raises(Stop):
        trail.run(c)
    assert crossings == [18]


# ===================================================================== action menu
def test_a_broken_part_cannot_be_skipped_by_looking_at_the_supplies(tmp_path):
    """Listing 4090: ``IF I(B) THEN I(B) = I(B) - (B > 2): B = 0``.

    B is cleared only when the oxen or the part have been obtained. The old menu
    cleared it after every choice, so "check supplies" then "continue" got through.
    """
    from oregon import action
    c = make(tmp_path, answers=["1", "2", "1"], max_prompts=14)
    st = c.st
    st.LL = 1
    st.B = 5                                      # a wheel is broken
    st.I[2] = num.parse("8")
    st.I[5] = num.ZERO                            # and there is no spare
    with pytest.raises(AssertionError, match="looping"):
        action.action_menu(c)
    assert num.as_int(st.B) == 5
    assert said(c).count("You must trade for a wheel") >= 2


def test_the_menu_lets_the_party_go_once_the_part_is_in_hand(tmp_path):
    from oregon import action
    c = make(tmp_path, answers=["2", "1"])
    st = c.st
    st.LL = 1
    st.B = 5
    st.I[2] = num.parse("8")
    st.I[5] = num.ONE                             # a spare arrived (by a trade)
    # "Continue" is refused while B is set; any other choice ends the pass, which
    # fits the part (I(B) is not zero) and clears B, and then "Continue" goes
    assert action.action_menu(c) == "CONTINUE"
    assert num.as_int(st.B) == 0 and num.as_int(st.I[5]) == 0


def test_a_broken_part_that_is_repaired_clears_the_flag(tmp_path):
    """Line 42100 assigns ``B = (PEEK (-16384) = 13)``, so B is 0 after a repair."""
    from oregon import part
    c = make(tmp_path, answers=["Y"], values=[0.1])
    c.st.B = 5
    assert part.broken_part(c) == "repaired"
    assert num.as_int(c.st.B) == 0


def test_a_part_replaced_from_the_spares_clears_the_flag(tmp_path):
    from oregon import part
    c = make(tmp_path, answers=["N"], values=[0.9])
    c.st.B = 6
    c.st.I[6] = num.parse("2")
    assert part.broken_part(c) == "replaced"
    assert num.as_int(c.st.B) == 0 and num.as_int(c.st.I[6]) == 1


def test_a_key_pressed_while_a_part_is_fitted_sets_the_flag_to_one(tmp_path):
    """The assignment is ``B = (PEEK (-16384) = 13)``: Return leaves 1."""
    from oregon import part
    c = make(tmp_path, answers=["Y"], values=[0.1])
    c.ui.keys = ["\r"]                             # Return ends the wait
    c.st.B = 5
    part.broken_part(c)
    assert num.as_int(c.st.B) == 1


def test_a_part_with_no_spare_leaves_the_flag_set_and_says_why(tmp_path):
    """Only the third ending skips line 42100: B stays at the part's number."""
    from oregon import part
    c = make(tmp_path, answers=["N"], values=[0.9])
    c.st.B = 7
    c.st.I[7] = num.ZERO
    assert part.broken_part(c) == "none"
    assert num.as_int(c.st.B) == 7
    text = said(c)
    assert "You must replace it with a spare part." in text
    assert "you must trade for one" in text


# ====================================================================== the events
def test_a_blizzard_leaves_the_rain_as_it_was(tmp_path, monkeypatch):
    """Listing 10602: ``AR = AR + 1`` comes first and the blizzard takes it off again."""
    from oregon import events
    stub_days(monkeypatch)
    c = make(tmp_path)
    c.st.AR, c.st.AS, c.st.TM = num.parse("5"), num.ZERO, num.ONE
    events.event_6(c)
    assert num.as_float(c.st.AR) == 5.0 and num.as_float(c.st.AS) == 8.0
    c.st.AR, c.st.TM = num.parse("5"), num.parse("4")
    events.event_6(c)
    assert num.as_float(c.st.AR) == 6.0            # a thunderstorm adds an inch


@pytest.mark.parametrize("draw,loses_a_day", [(0.3, False), (0.7, True)])
def test_fog_costs_a_day_on_a_draw_above_one_half(tmp_path, monkeypatch, draw, loses_a_day):
    """Listing 10700: ``Z = RND (1) > .5: ON Z + 1 GOSUB 710, 550``."""
    from oregon import events
    days = stub_days(monkeypatch)
    c = make(tmp_path, values=[draw, 0.0])
    c.st.LM, c.st.TM = 12, num.parse("3")
    events.event_7(c)
    assert bool(days) is loses_a_day
    assert "Heavy fog" in said(c)


def test_an_injured_ox_that_leaves_none_stops_the_wagon(tmp_path):
    """Listings 10825 and 21000: no oxen sets B = 2 and the menu takes over."""
    from oregon import events
    c = make(tmp_path, values=[0.9, 0.9])          # not a part, not an injury
    c.st.I[2] = num.HALF
    events.event_8(c)
    assert num.as_int(c.st.B) == 2
    assert "unable to continue" in said(c)


def test_a_thief_who_takes_the_last_ox_stops_the_wagon(tmp_path):
    """Listing 11370 ends in ``GOSUB 21000`` as well."""
    from oregon import events
    c = make(tmp_path, values=[0.1, 0.0, 0.0])     # the thief; oxen; one of them
    c.st.I[2] = num.ONE
    c.st.PF = c.st.I[8] = num.parse("100")
    events.event_13(c)
    assert num.as_int(c.st.B) == 2


@pytest.mark.parametrize("draw,bullets", [(0.0, 21), (0.4, 42), (0.7, 63)])
def test_ammunition_in_an_abandoned_wagon_is_21_42_or_63(tmp_path, draw, bullets):
    """Listing 51010: ``X = X + X * (Y = 4) * 20``."""
    from oregon import lf
    # items 3..7: not clothing, ammunition (amount drawn), then not the rest
    c = make(tmp_path, values=[0.9, 0.1, draw, 0.9, 0.9, 0.9])
    c.st.I[4] = num.ZERO
    lf.abandoned_wagon(c)
    assert num.as_int(c.st.I[4]) == bullets


def test_a_thief_who_takes_nothing_reports_nothing(tmp_path):
    """Listing 52030 clears ``T$(0)``; 11330 shows the message only ``IF Z``."""
    from oregon import lf
    c = make(tmp_path, values=[0.0])              # oxen, of which there are none
    c.st.I[2] = num.ZERO
    c.st.PF = c.st.I[8] = num.parse("100")
    c.st.T[0] = "attempt to ford the river"
    assert lf.thief(c) == []
    assert c.st.T[0] == ""


# ======================================================================== the hunt
@pytest.mark.parametrize("bag,carried", [(1, 1), (2, 2), (3, 1), (4, 2), (5, 2), (6, 3)])
def test_a_bag_of_three_pounds_or_more_is_halved(tmp_path, monkeypatch, bag, carried):
    """Listing 50011: ``L = INT (L / (2 - (L < 3)))``."""
    from oregon import hunt
    c = make(tmp_path)
    c.st.I[4] = num.parse("10")
    c.st.PF = c.st.I[8] = num.parse("100")
    monkeypatch.setattr(hunt, "hunt_session",
                        lambda c, st, bullets: {"meat": bag, "bullets": 9, "shots": 1})
    assert hunt.go(c) == carried
    assert num.as_int(c.st.PF) == 100 + carried


# ===================================================================== the rivers
def test_a_wagon_that_tips_while_floating_and_loses_nothing_had_no_trouble(
        tmp_path, monkeypatch):
    """Listing 50090 sets the tipped text only ``IF Z`` -- a loss was recorded."""
    from oregon import river
    stub_days(monkeypatch)
    c = make(tmp_path, values=[0.01], fill=0.9)
    st = c.st
    st.RD, st.RS, st.IX = num.parse("3"), num.parse("3"), num.ONE
    for i in range(3, 9):
        st.I[i] = num.ZERO
    st.NP = 5
    assert river.float_crossing(c) is True
    river._show_result(c)                         # line 3504 shows A$ (GOSUB 900)
    assert "You had no trouble floating the wagon across." in said(c)
    assert "tipped over" not in said(c)


def test_a_ferry_that_breaks_loose_and_loses_nothing_says_so(tmp_path, monkeypatch):
    """Listing 50120 ends ``IF NOT Z THEN A$ = "Some trouble in crossing ..."``."""
    from oregon import river
    stub_days(monkeypatch)
    c = make(tmp_path, answers=["Y"], values=[0.5, 0.01], fill=0.9)
    st = c.st
    st.RD, st.RS, st.IX, st.MY = num.parse("3"), num.parse("11"), num.ONE, num.parse("100")
    for i in range(2, 9):
        st.I[i] = num.ZERO
    assert river.ferry(c) is True
    river._show_result(c)                         # line 3504 shows A$ (GOSUB 900)
    assert "Some trouble in crossing but nothing was lost." in said(c)
    assert "broke loose" not in said(c)


def test_every_choice_at_a_river_starts_at_the_normal_risk(tmp_path, monkeypatch):
    """Listing 50030 begins ``IX = 1``; only the guide raises it, for that crossing."""
    from oregon import river
    c = make(tmp_path, answers=["1"])
    c.st.LM = 2
    c.st.IX = num.parse("5")
    seen = []

    def conditions(c):
        c.st.RW, c.st.RD, c.st.RS, c.st.RB = (num.parse("400"), num.parse("2"),
                                              num.parse("4"), 0)

    monkeypatch.setattr(river, "conditions", conditions)
    monkeypatch.setattr(river, "ford", lambda c, ix=None: seen.append(num.as_int(c.st.IX)))
    monkeypatch.setattr(river, "_animate", lambda c, m: None)
    monkeypatch.setattr(river, "_bury_drowned", lambda c: False)
    river.crossing(c)
    assert seen == [1]


# ========================================================================= the toll
@pytest.mark.parametrize("money,pays", [("15.00", False), ("15.01", True), ("14.99", False),
                                        ("15.004", False)])
def test_the_toll_is_taken_only_if_the_money_is_more_than_it(tmp_path, monkeypatch,
                                                              money, pays):
    """Listings 50015-50030: the toll at 20 oxen is $15.00 and ``MY > V`` decides.

    With exactly the toll the party is silently returned to the choice (paper 10.1).
    The money is first rounded to whole cents (``MY = INT (MY * 100 + .5) / 100``), so
    $15.004 is $15.00 and is refused too.
    """
    from oregon import endl, trail

    class Reached(Exception):
        pass

    def load_segment(c, seg):
        raise Reached

    monkeypatch.setattr(trail, "load_segment", load_segment)
    c = make(tmp_path, answers=["2", "Y"], max_prompts=10)
    c.st.I[2] = num.parse("20")
    c.st.MY = num.parse(money)
    if pays:
        with pytest.raises(Reached):
            endl.the_dalles(c)
    else:
        with pytest.raises(AssertionError, match="looping"):
            endl.the_dalles(c)
    assert "$15.00 to travel the Barlow road" in said(c)


# ========================================================================== forts
def _fort(tmp_path, answers, money="500"):
    from oregon import fortbuy
    c = make(tmp_path, answers=answers)
    c.st.LM, c.st.MY = 3, num.parse(money)
    for i in range(2, 9):
        c.st.I[i] = num.ZERO
    c.st.PF = c.st.I[8]
    fortbuy.fort_store(c)
    return c


def test_buying_at_a_fort_does_not_recalculate_the_speed(tmp_path, monkeypatch):
    """Listing 50025 ends ``GOTO 50010``; BUY.LIB has no ``GOSUB 650``."""
    from oregon import trail
    calls = []
    monkeypatch.setattr(trail, "speed", lambda c: calls.append(1))
    _fort(tmp_path, ["2", "3", "8"])
    assert calls == []


def test_ammunition_at_a_fort_comes_in_boxes_of_twenty(tmp_path):
    """Listing 50025: ``K = 1 + 19 * (L = 3)``."""
    c = _fort(tmp_path, ["3", "2", "8"])
    assert num.as_int(c.st.I[4]) == 40


def test_the_fort_says_when_the_whole_order_is_too_dear(tmp_path):
    """Listing 50020 sets ``A$ = " many"`` before 50030 prints its refusal."""
    c = _fort(tmp_path, ["2", "9", "8"], money="45")
    text = said(c)
    assert "You cannot afford that many." in text
    assert "You cannot afford that." not in text
    assert num.as_int(c.st.I[3]) == 0


def test_the_fort_names_the_spare_part_in_its_limit(tmp_path):
    """Listing 50033 prints ``I$(L + 1)``, the inventory name."""
    c = _fort(tmp_path, ["4", "4", "8"])
    assert "Your wagon may only carry 3 " in said(c)
    assert "Your wagon may only carry 3 wheel" not in said(c).replace("wagon wheels", "")


# ===================================================================== trading
def test_a_refused_offer_still_brings_the_food_total_up_to_date(tmp_path):
    """TRADE.LIB 50040 (``PF = I(8)``) is reached after "no" as well as after "yes"."""
    from oregon import trade
    # wants clothing (x = 1), offers wagon wheels (y = 3), ratio 1, no refusal
    c = make(tmp_path, answers=["N"], values=[0.2, 0.5, 0.0, 0.0, 0.0])
    st = c.st
    st.I[3] = num.parse("5")
    st.I[5] = num.ZERO
    st.PF, st.I[8] = num.parse("5"), num.parse("7")
    assert trade.attempt(c) is False
    assert num.as_int(st.PF) == 7


# ======================================================================= the tomb
def test_an_empty_epitaph_is_not_followed_by_a_question(tmp_path):
    """Listing 50030 skips "Would you like to make changes?" when ``LEN (A$)`` is 0."""
    from oregon import tomb
    c = make(tmp_path, answers=["Y", ""])           # an epitaph is wanted, none typed
    c.st.LM, c.st.NM = 8, 10
    c.st.D = num.parse("17.5")
    c.st.N = ["Zeke", "Jed", "Anna", "Mary", "Emily"]
    tomb.all_dead(c, 0)
    assert "changes?" not in said(c)


# ========================================================= smaller departures
def test_the_bonus_text_reads_doubled_and_tripled():
    """DATA at line 29000: the farmer's points are "doubled", the banker's "tripled"."""
    from oregon import win
    assert win.MULTIPLIER_TEXT == {1: "", 2: "doubled", 3: "tripled"}


def test_the_travel_screen_empties_the_text_array(tmp_path):
    """Line 320 prints T$(0) to T$(5) and sets each to "" as it goes."""
    from oregon import trail
    c = make(tmp_path)
    c.st.LL = 1
    for i in range(6):
        c.st.T[i] = "left over"
    trail.travel_screen(c)
    assert [c.st.T[i] for i in range(6)] == [""] * 6


def test_the_cents_are_poked_as_whole_cents(tmp_path):
    """Line 50070: ``POKE 917, (MY - INT (MY)) * 100 + .5`` -- $123.45 is 45."""
    from oregon import endl
    c = make(tmp_path)
    c.st.AY, c.st.MY = 1848, num.parse("123.45")
    endl.write_handover(c)
    assert (c.mem.peek_word(913), c.mem.peek(917)) == (123, 45)


# =================================================================== the demo driver
def _river_screen(depth):
    return ["Weather: warm", "River width: 400 feet", f"River depth: {depth} feet", "",
            "You may:", "1. attempt to ford the river", "2. caulk the wagon and float it",
            "3. take a ferry", "4. wait a day", "5. get more information"]


def _driver_on(lines):
    ui = AutoUI()
    ui.out.extend(lines)
    ui._since = 0
    return ui


@pytest.mark.parametrize("depth", ["2.2", "2.4", "1"])
def test_the_driver_fords_a_river_under_two_and_a_half_feet(depth):
    """Paper 12.7: "it fords when the water is under 2.5 feet deep"."""
    from oregon.ui import _river_answer
    assert _river_answer(_driver_on(_river_screen(depth))) == "1"


def test_the_driver_does_not_ford_a_deep_river():
    from oregon.ui import _river_answer
    assert _river_answer(_driver_on(_river_screen("4.7"))) == "3"      # the ferry


def test_the_driver_reads_the_depth_the_game_prints(tmp_path, monkeypatch):
    """End to end: the river menu the game draws is one the driver can read."""
    from oregon import river
    ui = AutoUI()
    c = Context(ui=ui, rng=ScriptedRnd([0.5] * 5000), files=Files(tmp_path / "data"))
    c.st.LM = 2
    fords = []

    def conditions(c):
        c.st.RW, c.st.RD, c.st.RS, c.st.RB = (num.parse("400"), num.parse("2.2"),
                                              num.parse("4"), 0)

    monkeypatch.setattr(river, "conditions", conditions)
    monkeypatch.setattr(river, "ford", lambda c, ix=None: fords.append(1))
    monkeypatch.setattr(river, "_animate", lambda c, m: None)
    monkeypatch.setattr(river, "_bury_drowned", lambda c: False)
    river.crossing(c)
    assert fords == [1]


def test_the_driver_stops_if_it_cannot_read_the_depth():
    """A rule chosen because "River depth:" is on screen must not silently fall through."""
    from oregon.ui import _river_answer
    lines = [s.replace("River depth:", "River depth") for s in _river_screen("2.2")]
    with pytest.raises(RuntimeError, match="depth"):
        _river_answer(_driver_on(lines))


def test_the_driver_has_no_rules_that_cannot_fire():
    """The game prints "Health: poor" and has no Food line, so those rules never could."""
    needles = [needle for needle, _ in AutoUI.RULES]
    assert not any(n.startswith("Health:") or n.startswith("Food:") for n in needles)


# ===================================================================== the tables
def test_the_willamette_valley_has_outgoing_segment_99():
    """VAR.BIN stores ``LM$(17,2)`` as "99"; the other last columns are "0"."""
    assert L.LM_SEGMENT[17] == 99
    assert len(L.LM_SEGMENT) == 18


# ======================================================================== graves
def test_a_grave_at_exactly_the_miles_run_is_not_ahead(tmp_path):
    """Listing 450: ``ML(L4) < D`` compares two stored values, bit for bit.

    The record holds the text ``STR$ (D)`` made. Compared as host floats, the grave of
    90.9 miles is *behind* a party whose D is that same stored number, because the
    stored number (90.90000000596) is a little over the double that the digits give.
    """
    from oregon import trail
    c = make(tmp_path)
    c.st.NM, c.st.LM = 8, 10
    c.st.SN = [810, 0]
    c.st.ML = [90.9, 0]
    c.st.D = num.store(num.parse("90.9"))
    trail.find_grave(c)
    assert num.as_float(c.st.DL) == -1.0
    c.st.D = num.store(num.parse("90.91"))
    trail.find_grave(c)
    assert num.as_float(c.st.DL) == pytest.approx(90.9)


def test_a_theft_that_takes_nothing_shows_nothing(tmp_path):
    """Listing 11330: ``IF Z THEN ... GOSUB 900`` -- no message when Z is 0."""
    from oregon import events
    c = make(tmp_path, values=[0.1, 0.0])           # the thief; oxen, of which none
    c.st.I[2] = num.ZERO
    events.event_13(c)
    assert "thief" not in said(c)


def test_a_theft_is_one_sentence(tmp_path):
    """Listing 52030: ``A$ = A$ + " " + T$(0) + "."``."""
    import re
    from oregon import events
    c = make(tmp_path, values=[0.1, 0.0, 0.0])
    c.st.I[2] = num.parse("6")
    events.event_13(c)
    assert re.search(r"steals \d+ \w+\.", said(c)), said(c)


@pytest.mark.parametrize("keys,b,left", [(["\r"], 1, []), ([" ", "\r"], 0, ["\r"])])
def test_b_is_set_by_the_key_that_ended_the_wait(tmp_path, keys, b, left):
    """Listing 42100: ``GOSUB 30000: B = (PEEK (-16384) = 13)``."""
    from oregon import part
    c = make(tmp_path)
    c.ui.keys = list(keys)
    part._clear_b(c)
    assert num.as_int(c.st.B) == b and c.ui.keys == left
