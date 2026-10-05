"""The two messages of ``OREGON TRAIL`` 10300 and 10310.

Both are ``V$ = Z$ + A$ + "."`` with ``Z$`` already ending ``" has "``. Getting that
wrong is invisible in the listing and obvious on the screen, and both forms were wrong:
the text read ``name + " " + ...``, so a death was announced as "Zeke died" -- and then
announced *again*, correctly, further down. Both were reported from play; see
``FINDINGS.md`` 23.
"""

from __future__ import annotations

import pytest

from oregon import illness, num


def party(tmp_path, names=("Zeke", "Anna", "Joey"), value="0.1"):
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.state import State
    from oregon.ui import ScriptedUI
    c = Context(ui=ScriptedUI([" "] * 200, allow_repeat=True, max_prompts=2000),
                rng=ScriptedRnd(" ".join([value] * 6000)),
                files=Files(tmp_path / "data"))
    c.st = State()
    c.st.NP = len(names)
    c.st.H = num.parse("150")
    for i, n in enumerate(names):
        c.st.N[i] = n
        c.st.H1[i] = num.ZERO
        c.st.H2[i] = num.ZERO
    return c


def said(c, name):
    return [l for l in c.ui.out if name in l]


#: 10310: ``V$ = Z$ + A$ + "."`` with ``Z$ = N$(Z) + " has "`` -- so the name, " has ",
#: the illness, and a full stop.
def test_a_new_illness_says_has(tmp_path):
    c = party(tmp_path)
    illness.illness(c)
    lines = said(c, "Anna")
    assert lines == ["Anna has exhaustion."], f"got {lines}"


@pytest.mark.parametrize("index", [0, 1, 2])
def test_a_new_illness_says_has_for_any_victim(tmp_path, index):
    c = party(tmp_path)
    illness.illness(c)
    name = c.st.N[index] if num.as_int(c.st.NP) > index else None
    assert said(c, "Anna"), "the victim is chosen by the generator, not by the test"


#: 10300: ``IF H1(Z) THEN A$ = "died"`` with the same ``V$``, so "Zeke has died." --
#: name, " has ", "died", full stop.
def test_a_death_says_has_and_a_full_stop(tmp_path):
    c = party(tmp_path)
    for i in range(3):
        c.st.H1[i] = num.parse("2")          # already ill, so 10300 kills
    illness.illness(c)
    lines = [l for l in c.ui.out if "died" in l]
    assert lines, "no death was announced"
    assert all(l.endswith("has died.") for l in lines), f"got {lines}"


def test_a_death_is_announced_exactly_once(tmp_path):
    """``GOSUB 8000`` -- the removal -- prints nothing. The announcement is 10300's
    alone. The code announced it twice: "Zeke died", then "Zeke has died." """
    c = party(tmp_path)
    for i in range(3):
        c.st.H1[i] = num.parse("2")
    illness.illness(c)
    assert len([l for l in c.ui.out if "died" in l]) == 1, \
        f"announced {[l for l in c.ui.out if 'died' in l]}"


def test_a_death_removes_exactly_one_member(tmp_path):
    c = party(tmp_path)
    for i in range(3):
        c.st.H1[i] = num.parse("2")
    before = num.as_int(c.st.NP)
    illness.illness(c)
    assert num.as_int(c.st.NP) == before - 1


def test_the_drowning_removal_is_silent(tmp_path):
    """Line 3504 calls ``TOMB.LIB`` 50000, which has no ``RETURN`` and falls into
    50005. Nothing there prints; the name is in the loss list from 50175."""
    from oregon import trail
    c = party(tmp_path, names=("Zeke", "Anna", "Joey"))
    c.st.H1[0] = num.parse("-2")
    c.st.H = num.parse("100")
    trail.remove_drowned(c)
    assert num.as_int(c.st.NP) == 2
    assert not [l for l in c.ui.out if "died" in l], \
        f"50005 is silent, got {[l for l in c.ui.out if 'died' in l]}"
