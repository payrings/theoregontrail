"""Behaviour of the listing that a second line-by-line review found the rebuild did
not reproduce. Each test names the line it checks."""
import pytest

from oregon import num
from test_listing_agreement import make, said  # noqa: E402


# ------------------------------------------------ OREGON TRAIL 3504, TOMB 50005
def test_drowned_members_leave_the_party_and_the_living_keep_their_illness(tmp_path):
    """3504 loops ``FOR L1 = 0 TO 4`` and 50005 restarts it (``L1 = 0``)."""
    from oregon import trail
    c = make(tmp_path)
    st = c.st
    st.NP = 5
    st.N = ["Zeke", "Jed", "Anna", "Mary", "Emily"]
    st.H1 = [num.ZERO, num.parse("-2"), num.parse("4"), num.ZERO, num.parse("-2")]
    st.H2 = [num.ZERO, num.ZERO, num.parse("7"), num.ZERO, num.ZERO]
    trail.remove_drowned(c)
    assert st.NP == 3
    alive = st.N[:3]
    assert "Jed" not in alive and "Emily" not in alive
    anna = alive.index("Anna")
    assert num.as_int(st.H1[anna]) == 4 and num.as_int(st.H2[anna]) == 7
    assert not any(num.eq(st.H1[i], num.parse("-2")) for i in range(3))


# ------------------------------------------------------- 700, 710, 900 and 570
def test_return_at_a_710_message_sets_b(tmp_path):
    """710: ``IF NOT B THEN B = FN B(Z) AND NOT SD`` after the wait."""
    from oregon import events
    c = make(tmp_path)
    c.ui.keys = ["\r"]
    c.st.B = 0
    events.event_5(c)                         # "Indians help find food."
    assert c.st.B == 1


def test_lost_days_run_before_the_wait(tmp_path, monkeypatch):
    """560 shows the message without a wait; 570 runs the days, then waits."""
    from oregon import trail
    order = []
    monkeypatch.setattr(trail, "run_stopped_days", lambda c: order.append("days"))
    c = make(tmp_path, values=[0.1])
    real = c.ui.wait_key
    c.ui.wait_key = lambda *a, **k: (order.append("wait"), real(*a, **k))[1]
    trail.lose_days(c, "test", 3, "Lose trail")
    assert order == ["days", "wait"]


def test_a_fire_that_burns_nothing_shows_nothing(tmp_path):
    """11210: ``IF Z > 0 THEN ... GOSUB 900``."""
    from oregon import events
    c = make(tmp_path, values=[0.1, 0.0], fill=0.9)    # the fire; nothing burns
    events.event_12(c)
    assert "fire" not in said(c)


def test_an_abandoned_wagon_says_whether_it_was_empty(tmp_path):
    """LF.LIB 51000 to 51030: ``A$ = A$ + Z$``."""
    from oregon import events
    c = make(tmp_path, values=[0.9], fill=0.9)         # the wagon; nothing found
    events.event_13(c)
    assert "You find an abandoned wagon, but it is empty." in said(c)


def test_water_and_grass_messages_do_not_wait(tmp_path):
    """11400 to 11420 use ``GOSUB 700``, which has no wait."""
    from oregon import events
    c = make(tmp_path, values=[0.9, 0.9])
    waits = []
    c.ui.wait_key = lambda *a, **k: waits.append(1) or " "
    events.event_14(c)
    assert "Inadequate grass" in said(c) and not waits


# ------------------------------------------------- OREGON TRAIL 3000 and 450
def test_starting_a_segment_does_not_write_a_grave(tmp_path):
    """3000 sets the scalar ``SN``; the array ``SN()`` holds the graves read at 29004."""
    from oregon import trail
    c = make(tmp_path)
    c.st.SN = [302, 0]
    c.st.NM, c.st.LM = 1, 0
    c.st.D = num.parse("102")
    trail.start_segment(c)
    assert c.st.SN == [302, 0]


# ------------------------------------------------------------ the demo driver
def test_the_demo_floats_when_the_ferry_cannot_be_paid_for(tmp_path):
    """The driver's rule: the ferry when offered, and otherwise the wagon floats."""
    from oregon.ui import AutoUI
    ui = AutoUI()
    menu = ["River depth: 4.5 feet", "You may:", "1. attempt to ford the river",
            "2. caulk the wagon and float it across", "3. take a ferry across",
            "4. wait to see if conditions improve", "5. get more information",
            "What is your choice? "]
    ui.out.extend(menu)
    assert ui.key("12345", 1) == "3"
    ui.out.append("The ferry operator says that he will charge you $5.00 and that "
                  "you will have to wait 3 days.  Are you willing to do this? ")
    assert ui.key("YN", 1) == "Y"
    ui.out.append("You do not have enough money to pay for the ferry.")
    ui.out.extend(menu)
    assert ui.key("12345", 1) == "2"


# ------------------------------------------------------------------ WIN 621
def test_the_cash_line_shows_the_amount(tmp_path):
    from oregon import win
    c = make(tmp_path)
    c.mem.poke_word(913, 123)
    c.mem.poke(917, 46)
    from oregon import common
    pt = win.read_items(c)
    assert common.money(c, pt[7][0]) == "123.46"      # 621: V = PT(7,0): GOSUB 250


# ------------------------------------------------------------------ HUNT.LIB
def test_a_hunt_with_no_bullets_still_runs_and_finds_nothing(tmp_path):
    """4600 runs HUNT.LIB whatever the ammunition."""
    from oregon import hunt
    c = make(tmp_path)
    c.st.I[4] = num.ZERO
    hunt.go(c)
    text = said(c)
    assert "Hunting Instructions" in text
    assert "You were unable to shoot any food." in text


# ------------------------------------------------------------- the arithmetic
def test_applesoft_error_numbers(tmp_path):
    """Overflow is 69 and division by zero 133, as ONERR leaves them at 222."""
    from oregon import applesoft
    if not applesoft.rom_available():
        pytest.skip("needs the ROM")
    from oregon.applesoft.rom import RomError
    applesoft.use("rom")
    with pytest.raises(RomError) as e:
        num.mul(num.parse("1E38"), num.parse("10"))
    assert e.value.code == 69
    with pytest.raises(RomError) as e:
        num.div(num.ONE, num.ZERO)
    assert e.value.code == 133


def test_str_of_an_operator_result_uses_the_live_extension_byte():
    """``PRINT A/B`` formats FAC before it is rounded; ``X = A/B: PRINT X`` after."""
    from oregon import applesoft
    from oregon.applesoft.fac import Fac
    if not applesoft.rom_available():
        pytest.skip("needs the ROM")
    applesoft.use("rom")
    a, b = Fac(bytes.fromhex("8810000000")), Fac(bytes.fromhex("8B1BE33333"))
    q = num.div(a, b)
    assert num.str_(q) == ".115467885"
    assert num.str_(num.store(q)) == ".115467886"
