"""The supplies screen, and the event hardship term of the health sum.

Both were broken by one thing: ``str()`` on a ``Fac`` had no implementation, so it
fell back to ``__repr__`` and produced ``Fac(85 20 00 00 00)``. Feeding that back
through ``num.parse`` -- a natural-looking way to get a plain number out of a ``Fac``
-- yields **0**.

So every holding on both supplies screens printed as zero, and a party that had bought
oxen, food and clothing appeared to own nothing; and ``HR``, the event hardship term
of ``H = .9 * H + ZT + ZC + ZF + ZP + FS + H0 + HR``, contributed nothing at all, so
the hardship an event caused never reached the health figure. Reported from play:
FINDINGS.md 25.
"""

from __future__ import annotations

import pytest

from oregon import action, num, trade, trail


def stocked(tmp_path):
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.state import State
    from oregon.ui import ScriptedUI
    c = Context(ui=ScriptedUI(["1"] * 40, allow_repeat=True),
                rng=ScriptedRnd("0.5 " * 8000), files=Files(tmp_path / "data"))
    st = State()
    st.NP = 5
    st.I[2] = num.parse("8")
    st.I[3] = num.parse("5")
    st.I[4] = num.parse("50")
    st.I[5] = num.parse("2")
    st.I[6] = num.parse("1")
    st.I[7] = num.parse("3")
    st.I[8] = num.parse("1000")
    st.PF = st.I[8]
    st.MY = num.parse("640")
    c.st = st                     # Context builds its own State; use ours
    return c


def test_a_fac_stringifies_to_its_number():
    """``Fac.__str__`` must give text ``num.parse`` can read back."""
    for text, want in (("20", 20.0), ("0", 0.0), (".5", 0.5), ("-2.7", -2.7),
                       ("139", 139.0), ("1000", 1000.0)):
        v = num.parse(text)
        assert num.as_float(num.parse(str(v))) == pytest.approx(want), text


def test_repr_still_shows_the_bytes():
    """The byte form is kept for debugging; only ``str`` changed."""
    assert repr(num.parse("20")) == "Fac(85 20 00 00 00)"


def test_the_supplies_screen_shows_what_is_held(tmp_path):
    c = stocked(tmp_path)
    action.show_supplies(c)
    said = " ".join(c.ui.out)
    for name, want in (("oxen", 8), ("sets of clothing", 5), ("bullets", 50),
                       ("wagon wheels", 2), ("wagon axles", 1),
                       ("wagon tongues", 3), ("pounds of food", 1000)):
        line = [l for l in c.ui.out if l.strip().startswith(name)]
        assert line, f"{name} missing from the screen"
        assert line[0].split()[-1] == str(want), (
            f"{name}: printed {line[0]!r}, held {want}")


def test_no_line_reads_zero_when_something_is_held(tmp_path):
    c = stocked(tmp_path)
    action.show_supplies(c)
    for line in c.ui.out[2:-1]:
        assert not line.split()[-1] == "0", f"{line!r} reads zero"


def test_the_trades_own_supplies_screen_agrees(tmp_path):
    """TRADE.LIB 50050 prints the same list, and it had the same defect."""
    c = stocked(tmp_path)
    trade.show_supplies(c)
    said = " ".join(c.ui.out)
    assert "8" in said and "1000" in said, said


def test_the_event_hardship_reaches_the_health_sum(tmp_path):
    """``HR`` is 10 or 20 when that day's event was ``Rough trail``, ``Bad water`` or
    ``Very little water``, and 0 otherwise (3180, 11000, 11400, 11410)."""
    c = stocked(tmp_path)
    st = c.st
    st.TM = num.parse("3")
    st.W = num.parse("2")
    st.P = num.parse("1")
    st.FS = num.ZERO
    st.H0 = 0
    st.PF = num.parse("1000")
    st.I[3] = num.parse("5")
    trail.speed(c)
    st.FC = num.ZERO

    def health(hr):
        st.H = num.parse("100")
        st.HR = hr
        trail.health_today(c)
        return num.as_float(st.H)

    without = health(num.ZERO)
    with20 = health(num.parse("20"))
    with10 = health(num.parse("10"))
    assert with20 - without == pytest.approx(20.0), (
        f"HR = 20 changed health by {with20 - without}")
    assert with10 - without == pytest.approx(10.0), (
        f"HR = 10 changed health by {with10 - without}")
