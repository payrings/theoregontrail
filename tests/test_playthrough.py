"""A whole game, played from a script, to each ending.

There is no reference trace to compare against (Appendix H), so these tests check
that the game *runs* to each ending without stalling, that the numbers move the way
the formulas say, and that the same seed and answers give the same game twice.
They are the tests that found the missing oxen at Fort Laramie and the action menu
swap at line 4090.

The answers are chosen by the text of the prompt rather than by position, because
the order of the questions changes with the route: taking the first branch at South
Pass skips Fort Bridger entirely, so there is one fewer question than there would
otherwise be. Matching on position made the test pass for the wrong reasons once
already.
"""
import copy
import pathlib
import tempfile

import pytest

from oregon import buysupplies, menu, trail, win
from oregon.context import Context
from oregon.files import Files
from oregon.rng import ScriptedRnd
from oregon.trace import Tracer
from oregon.ui import ALLOWED, ScriptedUI


class FlowUI(ScriptedUI):
    """Answers by what the game printed, with an explicit log for the tests.

    :attr:`log` records every prompt and answer so a test can assert on the flow,
    and :attr:`limit` stops a runaway game instead of hanging the suite.
    """

    def __init__(self, rules, value="0.5", draws=400000, max_prompts=3000, **kw):
        super().__init__(answers=[], max_prompts=max_prompts, **kw)
        self.rules = rules
        self.value = value
        self.draws = draws
        self.log = []
        #: rules match only what has been printed *since the last question*, so a
        #: prompt is recognised by the screen directly above it and never by an
        #: earlier one. Without this the profession screen still matched while the
        #: names were being typed, and the river menu matched while the ferry was
        #: being offered.
        self._since = 0

    def _ask(self):
        recent = "\n".join(self.out[self._since:])
        for needle, answer in self.rules:
            if needle in recent:
                if isinstance(answer, (list, tuple)):
                    return answer.pop(0) if answer else ""
                return answer
        # Nothing matched. Repeating the last answer keeps an unexpected prompt
        # from spinning, and the log makes it obvious in a failure.
        return self.log[-1][2] if self.log else ""

    def key(self, allowed="", maxlen=1, default=""):
        ask = self.out[-1].strip()[-60:] if self.out else ""
        a = self._ask()
        a = str(a)[:maxlen] if maxlen else str(a)
        self._since = len(self.out)
        self.prompts += 1
        if self.prompts > self.max_prompts:
            raise AssertionError(
                f"the game asked {self.prompts} questions, more than the "
                f"max_prompts of {self.max_prompts}: it is looping")
        self.log.append((ask, allowed, a))
        return a

    def yes_no(self, prompt=""):
        if prompt:
            self.print(prompt)
        return "Y" if str(self._ask()).upper()[:1] == "Y" else "N"


def make_game(rules, value="0.5", data=None):
    d = pathlib.Path(tempfile.mkdtemp())
    ui = FlowUI(rules, value=value)
    rng = ScriptedRnd(" ".join([value] * ui.draws))
    c = Context(ui=ui, rng=rng, files=Files(data or (d / "data")), trace=Tracer())
    rng.seed_from_keyboard(4242)
    return c, ui


#: The rules, in the order they are asked. A needle is matched against the last
#: twelve lines the game printed, so a prompt can be recognised by the screen it
#: sits on rather than by the words immediately above it. An answer may be a
#: string, or a list consumed one entry per time that prompt is asked -- which is
#: what the store needs, where the same question ("Which item would you like to
#: buy?") comes round five times with a different answer each time.
#:
#: Answers chosen to make a *plausible* journey rather than a lucky one: the Green
#: River at twenty feet and the Snake at six cannot be forded, so they use the
#: ferry and the guide, and The Dalles uses the Barlow Toll Road.
BARBER = [
    ("Be a banker", "1"),
    ("What is the first name of the wagon leader?", "Zeke"),
    ("Are these names correct?", "Y"),
]

MONTH = [
    ("Ask for advice", "4"),                   # May
]

STORE = [
    ("Which item would you like to buy?",
     ["1", "2", "3", "4", "5", ""]),            # oxen, food, clothes, ammo, parts
    ("want?", ["4", "1200", "6", "6"]),         # four yoke, 1200 lb, six of each
    ("How many wagon", ["1", "1", "1"]),        # one wheel, one axle, one tongue
]

JOURNEY = [
    ("Would you like to look around?", "N"),
    ("River depth:", ["1", "1", "3", "3"]),     # ford, ford, ferry, guide
    ("Are you willing to do this?", "Y"),        # the ferry
    ("Will you accept this offer?", "Y"),        # the Shoshoni guide
    ("The trail divides here", ["1", "1"]),      # branch 1 at both splits
    ("take the Barlow Toll Road", "2"),
    ("to travel the Barlow road", "Y"),
    ("Continue on trail", "1"),                 # if the action menu ever opens
    ("no one wants to", "1"),                   # declined trades
]

ALL_RULES = BARBER + MONTH + STORE + JOURNEY


def make_game(rules=None, value="0.5", data=None, draws=400000, max_prompts=3000):
    """A context with a FlowUI, a scripted generator and a private data directory."""
    d = pathlib.Path(tempfile.mkdtemp())
    # a copy, because a sequence rule is consumed as it is answered: without this
    # the second play of the determinism test finds the lists empty and loops
    ui = FlowUI(copy.deepcopy(rules if rules is not None else ALL_RULES),
                value=value, draws=draws, max_prompts=max_prompts)
    rng = ScriptedRnd(" ".join([value] * draws))
    c = Context(ui=ui, rng=rng, files=Files(data or (d / "data")), trace=Tracer())
    rng.seed_from_keyboard(4242)
    return c, ui


def play(rules=None, **kw):
    """Set up a party and travel: returns (context, ui, store result, where)."""
    c, ui = make_game(rules, **kw)
    menu.start(c)
    buysupplies.departure_month(c)
    buysupplies.init_state(c)
    got = buysupplies.store(c)
    money_after_store = c.st.MY.to_float()
    trail.load_state(c)
    where = trail.run(c)
    return c, ui, got, where, money_after_store


@pytest.fixture(scope="module")
def journey():
    """Play the journey once and share it: it is slow, and the answers are fixed."""
    c, ui, got, where, after_store = play()
    if where != "WIN":
        # say where it stopped rather than letting five tests fail identically
        pytest.fail(f"the journey stopped at {where}; prompts asked:\n" +
                    "\n".join(f"  {a!r} -> {b!r}" for _q, _a, b in ui.log[-12:]))
    return c, ui, got, where, after_store


def test_the_store_takes_the_money_and_leaves_the_goods(journey):
    c, ui, got, where, after_store = journey
    assert got["yokes"] == 4
    assert got["food"] == 1200
    # 160 + 240 + 50 + 12 + 30 is the bill of line 4000
    assert after_store == pytest.approx(1600 - 502, abs=0.01)
    # then the $5 ferry at the Green River and the Barlow toll come off
    toll = 5 + int(c.st.I[2].to_float() + 0.5) * 0.5
    assert c.st.MY.to_float() == pytest.approx(after_store - 5 - toll, abs=0.02)
    assert c.st.I[2].to_float() == 8.0, "four yoke is eight oxen"
    assert c.st.I[4].to_float() == 120.0, "six boxes is 120 bullets"
    assert [c.st.I[k].to_int() for k in (5, 6, 7)] == [1, 1, 1]


def test_the_journey_reaches_the_willamette(journey):
    c, ui, got, where, _ = journey
    assert where == "WIN", f"the journey stopped at {where}"
    assert c.st.LM == 17, "the Willamette Valley"
    assert c.trace.days > 80, "a five-month crossing is about 150 days"
    assert c.trace.days < 400, "and not absurdly long"


def test_the_party_travelled_a_plausible_distance(journey):
    c = journey[0]
    # segment 18, the Barlow Road, is 100 miles from The Dalles
    assert 1900 <= c.st.M.to_float() <= 2000, c.st.M.to_float()


def test_the_same_seed_and_answers_give_the_same_game(journey):
    """Determinism: replay the journey and compare the state."""
    c, ui, got, where, _ = journey
    c2, ui2, got2, where2, after2 = play()
    assert where2 == where
    assert after2 == journey[4]
    assert c2.trace.days == c.trace.days
    assert c2.st.M.to_float() == c.st.M.to_float()
    assert c2.st.H.to_float() == c.st.H.to_float()
    assert c2.rng.log.count() == c.rng.log.count(), "the same number of draws"


def test_the_hand_over_is_written_for_win(journey):
    """END.LIB 50050-50070, read back the way WIN does."""
    c = journey[0]
    assert c.mem.peek(909) == c.st.I[2].to_int(), "the oxen go to 909"
    assert c.mem.peek_word(904) == c.st.I[4].to_int(), "the bullets to 904"
    assert c.mem.peek(908) == c.st.I[3].to_int()
    assert c.mem.peek_word(906) == int(c.st.I[8].to_float())
    assert c.mem.peek(916) == c.st.health_band()
    assert c.mem.peek(901) == int(c.st.AY.to_float()) - 1800


def test_the_health_is_capped_and_the_band_is_valid(journey):
    c = journey[0]
    assert 0 <= c.st.H.to_float() <= 139, "line 3150 and 3250 cap it at 139"
    assert c.st.health_band() in (0, 1, 2, 3)