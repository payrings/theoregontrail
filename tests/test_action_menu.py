"""The action menu's shape and dispatch, read from lines 4040, 4050 and 4090.

Table 9 of the paper: "Talk to people" is offered at landmarks, "Buy supplies" at
forts, and "Hunt for food" on the trail. ``LL`` is 0 at a landmark and 1 on the
trail, so line 4040's ``IF NOT LL`` is the landmark case and line 4050's ``IF LL``
is the trail's.
"""

from __future__ import annotations

import pytest

from oregon import action, num
from oregon.context import Context
from oregon.files import Files
from oregon.rng import ScriptedRnd
from oregon.state import State
from oregon.ui import ScriptedUI


@pytest.fixture
def c(tmp_path):
    """A context with its own scripted screen, so a menu can be drawn and read."""
    ctx = Context(ui=ScriptedUI(["1"] * 400, allow_repeat=True, max_prompts=400),
                  rng=ScriptedRnd(" ".join(["0.5"] * 20000)),
                  files=Files(tmp_path / "data"))
    ctx.st = party = State()
    party.NP = 5
    party.I[2] = num.parse("8")        # oxen, so "continue" is allowed
    party.I[8] = num.parse("1000")
    party.I[4] = num.parse("50")
    party.MY = num.parse("1000")
    return ctx


def _menu(c, lm, ll, answer="1"):
    """Draw the menu at a landmark (``ll = 0``) or on the trail (``ll = 1``),
    answering ``answer`` once and then letting the menu redraw."""
    c.st.LM = lm
    c.st.LL = ll
    c.ui.answers = [answer] + ["1"] * 200
    return action.action_menu(c)


def _options(c):
    out = []
    for line in c.ui.out:
        if len(line) > 2 and line[:1].isdigit() and line[1:2] == ".":
            out.append(line.split(".", 1)[1].strip())
    return out


def test_a_landmark_offers_talk(c):
    _menu(c, 4, 0)                              # Chimney Rock, type 0
    assert _options(c) == [
        "Continue on trail", "Check supplies", "Look at map", "Change pace",
        "Change food rations", "Stop to rest", "Attempt to trade",
        "Talk to people",
    ]


def test_a_fort_offers_talk_and_buying(c):
    _menu(c, 3, 0)                              # Fort Kearney, type 1
    assert _options(c)[-2:] == ["Talk to people", "Buy supplies"]


def test_the_trail_offers_the_hunt(c):
    _menu(c, 4, 1)
    assert _options(c)[-1] == "Hunt for food"
    assert "Buy supplies" not in _options(c)
    assert "Talk to people" not in _options(c)


def test_independence_is_a_fort_so_buying_is_offered(c):
    """Table 7 gives landmark 0 type 1, and lines 4040-4045 nest the entry in
    ``IF NOT LL`` but not inside the type test."""
    _menu(c, 0, 0)
    assert _options(c)[-2:] == ["Talk to people", "Buy supplies"]


@pytest.mark.parametrize("choice,name", [
    (2, "show_supplies"),
    (3, "show_map"),
    (4, "do_pace"),
    (5, "do_rations"),
    (6, "do_rest"),
    (7, "do_trade"),
    (8, "do_talk"),
    (9, "do_buy"),
])
def test_each_option_reaches_its_own_routine(c, monkeypatch, choice, name):
    """``ON Z - 1 GOSUB 4100, 4200, 4300, 4400, 4500, 4900, 4700, 4800, 4600``.

    Choice 2 used to match no handler at all and quietly did nothing, which no
    test noticed, because the menu simply came back.
    """
    called = []
    for routine in ("show_supplies", "show_map", "do_pace", "do_rations",
                    "do_rest", "do_trade", "do_talk", "do_buy", "do_hunt"):
        monkeypatch.setattr(action, routine,
                            (lambda r: lambda cc: called.append(r))(routine))
    _menu(c, 3, 0, answer=str(choice))          # Fort Kearney: nine options
    assert called == [name]


def test_the_trail_eighth_option_is_the_hunt(c, monkeypatch):
    called = []
    for routine in ("show_supplies", "show_map", "do_pace", "do_rations",
                    "do_rest", "do_trade", "do_talk", "do_buy", "do_hunt"):
        monkeypatch.setattr(action, routine,
                            (lambda r: lambda cc: called.append(r))(routine))
    _menu(c, 4, 1, answer="8")                  # on the trail: eight options
    assert called == ["do_hunt"]


@pytest.mark.parametrize("lm,ll,want", [
    (3, 0, "-19"),      # a fort: seven options, talk, buy
    (4, 0, "-18"),      # Chimney Rock: seven options and talk
    (4, 1, "-18"),      # on the trail: seven options and the hunt
])
def test_the_allowed_set_is_built_from_the_options_printed(c, monkeypatch, lm, ll, want):
    """Line 4060: ``Z$ = "-1" + STR$(Z)``, where ``Z`` is how many options were
    printed, so nine options ask for "19" and eight for "18" -- a range of one to
    the number of options, as FINDINGS 15 has it. That range is what keeps a ninth
    answer out of the trail's eight options; ``ON Z - 1`` with Z = 11 would simply
    do nothing (paper 2.5)."""
    asked = []
    real = c.ui.key

    def spy(allowed="", maxlen=1, default=""):
        asked.append(allowed)
        return real(allowed, maxlen, default)

    monkeypatch.setattr(c.ui, "key", spy)
    _menu(c, lm, ll)
    assert asked[0] == want
