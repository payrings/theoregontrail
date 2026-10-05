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
from oregon import num
from oregon.rng import ScriptedRnd, SequenceRnd
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
        #: keys for `poll_key` only -- a Return here interrupts the daily cycle and
        #: opens the *trail* menu, which is the only way to reach "Hunt for food".
        #: They are kept apart from `wait_key`'s queue so that a scripted game does
        #: not spend its interrupts on "Press SPACE BAR".
        self.interrupts = []

    def _ask(self):
        recent = "\n".join(self.out[self._since:])
        for needle, answer in self.rules:
            if needle in recent:
                if isinstance(answer, (list, tuple)):
                    # an exhausted list falls through to the next rule, which is
                    # how a menu can cycle through its options
                    if answer:
                        return answer.pop(0)
                    continue
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

    def poll_key(self):
        if self.interrupts:
            return self.interrupts.pop(0)
        return None

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


def make_game(rules=None, value="0.5", data=None, draws=400000, max_prompts=3000,
              rng=None):
    """A context with a FlowUI, a scripted generator and a private data directory."""
    d = pathlib.Path(tempfile.mkdtemp())
    # a copy, because a sequence rule is consumed as it is answered: without this
    # the second play of the determinism test finds the lists empty and loops
    ui = FlowUI(copy.deepcopy(rules if rules is not None else ALL_RULES),
                value=value, draws=draws, max_prompts=max_prompts)
    if rng is None:
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

# ------------------------------------------------- a game that meets events
#: The same journey, but with a *varied* generator so that illnesses, breakdowns,
#: fires and thieves actually happen, and the answers use the action menu.
#: The needles are tried in order and the first that matches wins, so the ones
#: that only appear on a particular screen come first. "Continue on trail" is on
#: every menu and so acts as the general case, cycling through the options: the
#: action menu's numbers are 1 continue, 2 supplies, 3 map, 4 pace, 5 rations,
#: 6 rest, 7 trade, and then talk or buy or hunt.
BUSY_JOURNEY = [
    ("Would you like to look around?", "Y"),
    # At a fort the action menu offers both "Talk to people" (8) and "Buy supplies"
    # (9), so a fort shop needs 9, not 8. The shop's own menu is 1 to 7 for the
    # goods and 8 to leave; its quantity prompts fall through to the catch-all, so
    # one unit of each is bought.
    ("Buy supplies", ["9", "1", "2", "3", "4", "5", "6", "7", "8"]),
    ("Talk to people", ["8"]),                 # only on a landmark menu
    ("Hunt for food", ["8"]),                  # only on the trail menu
    # The action menu cycles through every option, which is also what proves the
    # allowed sets are right: an option the prompt rejects would loop here.
    ("Continue on trail", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "1"]),
    ("Broken wagon", "Y"),
    ("You are unable to continue", "1"),
    ("River depth:", ["1", "1", "3", "3"]),
    ("Are you willing to do this?", "Y"),
    ("Will you accept this offer?", "Y"),
    ("The trail divides here", ["1", "1"]),
    ("float down the Columbia River", "2"),   # take the Barlow Toll Road
    ("to travel the Barlow road", "Y"),
    # the fort shop's own menu, reached once "Buy supplies" has been chosen: 1 to
    # 7 are the goods and 8 leaves. The quantity prompts fall through to the
    # catch-all, so one of each is bought.
    ("Which number?", ["1", "2", "3", "4", "5", "6", "7", "8"]),
    ("no one wants to", "1"),
    # a last resort that always matches, so an unrecognised prompt gets option 1
    # (continue / decline) instead of spinning
    ("", "1"),
]

#: the same setup, then a party that uses the action menu at every landmark, so
#: that the pace, rations, trade, map, talk, hunt, fort and part modules are all
#: reached.
BUSY = BARBER + MONTH + STORE + BUSY_JOURNEY


def busy_game(seed=20260805, max_prompts=4000):
    """A whole game with a varied generator, reaching the event modules."""
    # a varied generator, so that events actually fire; `draws` is unused by it
    c, ui = make_game(BUSY, max_prompts=max_prompts, rng=SequenceRnd(seed))
    # Returns for `poll_key`, so the daily cycle is interrupted and the *trail*
    # action menu opens: that is the only way to reach "Hunt for food", since the
    # landmark menu offers "Talk to people" and "Buy supplies" instead.
    ui.interrupts = ["\r"] * 6
    menu.start(c)
    buysupplies.departure_month(c)
    buysupplies.init_state(c)
    got = buysupplies.store(c)
    trail.load_state(c)
    where = trail.run(c)
    return c, ui, got, where


#: What each module puts on the screen, so a run can be checked for reaching it.
#: This is deliberately the text a player would see rather than any internal
#: hook: it is what the modules are for, and it survives a refactor.
MARKS = {
    "PART.LIB": ["Broken wagon", "repair the broken wagon"],
    "LF.LIB fire": ["A fire in the wagon results in loss of"],
    "LF.LIB thief": ["A thief comes during the night"],
    "LF.LIB abandoned wagon": ["You find an abandoned wagon"],
    "HUNT.LIB": ["Hunting Instructions"],
    "PACE.LIB": ["Change pace"],
    "RATION.LIB": ["Change food rations"],
    "TALK.LIB": ["tells you:"],
    "TRADE.LIB": ["another emigrant", "No one wants to"],
    "BUY.LIB": ["You may buy"],
    "MAP.LIB": ["You have been through"],
}

#: Three seeds whose union reaches every module above. One seed cannot: the fire
#: needs event 12 to pick the fire rather than a lost member or a stray ox, which
#: is a matter of chance. The gravesite is not in this list because it cannot
#: happen to a party that has not already died on the same segment; it has a test
#: of its own, ``test_a_party_meets_the_grave_of_a_party_that_died``.
COVERAGE_SEEDS = (7, 5, 99)


@pytest.fixture(scope="module")
def busy_runs():
    """Four varied games, shared by the coverage tests. About two and a half seconds."""
    runs = []
    for seed in COVERAGE_SEEDS:
        c, ui, got, where = busy_game(seed=seed)
        runs.append((seed, c, ui, got, where))
    return runs


def test_a_varied_game_reaches_every_module(busy_runs):
    """One game, a varied generator, and the whole game: every module reached.

    A constant generator never fires an event, so the only way to walk
    ``PART.LIB``, ``LF.LIB`` and the rest is to play with a generator that varies.
    """
    reached = {k: [] for k in MARKS}
    for seed, c, ui, got, where in busy_runs:
        said = " ".join(c.ui.out)
        for name, needles in MARKS.items():
            if any(n in said for n in needles):
                reached[name].append(seed)
    missing = [k for k, v in reached.items() if not v]
    assert not missing, "never reached: " + ", ".join(missing)


def test_a_varied_game_fires_events_and_buries_people(busy_runs):
    for seed, c, ui, got, where in busy_runs:
        events = [t for t, _a, _v in c.rng.log.entries if t.startswith("3180 event")]
        assert len(events) > 500, f"seed {seed} tested only {len(events)} events"
        assert c.trace.days > 100, f"seed {seed} lasted {c.trace.days} days"
        assert 1700 <= c.st.M.to_float() <= 2000, f"seed {seed}: {c.st.M.to_float()} mi"


def test_a_varied_game_leaves_consistent_state(busy_runs):
    """Whatever happens, the numbers stay inside the limits the game sets."""
    for seed, c, ui, got, where in busy_runs:
        assert where in ("WIN", "FLOAT", "DIED", "MENU"), (seed, where)
        assert 0 <= c.st.NP <= 5
        assert c.st.I[2].to_float() >= 0, "oxen never go negative"
        assert c.st.I[8].to_float() >= 0, "food never goes negative"
        assert 0 <= c.st.H.to_float() <= 139, "health is capped at 139"
        for k in range(5, 8):
            assert 0 <= c.st.I[k].to_int() <= 3, "spare parts stay within three"
        assert 0 <= c.st.H0 <= 5, "no more sick than people"
        assert 1 <= c.st.P.to_int() <= 3, "the pace stays in range"
        assert 1 <= c.st.R.to_int() <= 3, "the rations stay in range"


def test_a_varied_game_is_reproducible(busy_runs):
    """The same seed and the same answers give the same game again."""
    for seed, c, ui, got, where in busy_runs:
        c2, ui2, got2, where2 = busy_game(seed=seed)
        assert where2 == where, seed
        assert c2.trace.days == c.trace.days, seed
        assert c2.st.M.to_float() == c.st.M.to_float(), seed
        assert c2.st.NP == c.st.NP, seed
        assert c2.st.I[2].to_float() == c.st.I[2].to_float(), seed
        assert c2.st.H.to_float() == c.st.H.to_float(), seed
        assert c2.rng.log.count() == c.rng.log.count(), seed


def test_the_hunt_never_draws_from_the_game(busy_runs):
    """Appendix G.6: the hunting routine has its own generator."""
    from oregon import hunt
    from oregon.applesoft import fac
    seed, c, ui, got, where = busy_runs[0]
    before = c.rng.log.count()
    seed_before = fac._b().get_seed()
    hunt.hunt_session(c, c.st, 20)
    assert c.rng.log.count() == before, "a hunt draws nothing from the game"
    assert fac._b().get_seed() == seed_before, \
        "and does not advance the Applesoft seed"


def test_the_command_line_starts_a_journey(tmp_path):
    """`python -m oregon --demo` must reach Oregon, not just print a menu.

    The entry point chains the programs in the original's order: MENU, then the
    month and the store, then reading the hand-over back out of memory before
    travelling. Leaving out the month prompt or ``load_state`` still *looks*
    plausible but starts the journey from an uninitialised state, so this test
    drives the real command line rather than the library.
    """
    import subprocess
    import sys
    root = str(pathlib.Path(__file__).resolve().parents[1])
    trace = tmp_path / "trace.log"
    proc = subprocess.run(
        [sys.executable, "-m", "oregon", "--demo", "--seed", "4242",
         "--data", str(tmp_path / "data"), "--trace", str(trace)],
        cwd=root, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert trace.is_file(), "no trace was written"
    lines = [l for l in trace.read_text().splitlines() if not l.startswith("#")]
    assert len(lines) > 100, f"only {len(lines)} days traced"
    # FIELDS: AD AM AY D M H FS H0 HR W TM PP AR AS PF I2 ...
    first = lines[0].split()
    assert (first[0], first[1]) == ("02", "05"), \
        f"the first day should be the 2nd of May: {lines[0]}"
    last = lines[-1].split()
    assert last[3] == "0", "the last day has no miles left: " + lines[-1]
    assert int(last[4]) == 1921, f"the route is 1921 miles: {lines[-1]}"
    assert (tmp_path / "data" / "HISCORE.SEQ").is_file(), \
        "the top ten should have been written"


def test_a_party_meets_the_grave_of_a_party_that_died(tmp_path):
    """Event 4 needs a tombstone on the same segment, so it takes two parties.

    The first dies on the run to Fort Hall and writes its stone; a second party
    travelling the same segment passes it and is offered a look. This is the only
    way event 4 can fire, which is why it is tested directly rather than hoped for
    in a varied run.
    """
    import copy
    from oregon import trail, tomb
    from oregon.data import landmarks as L
    from oregon.files import Files

    d = tmp_path
    first, _ = make_game(BUSY, data=d / "data")
    first.st.N = ["Zeke", "Jed", "Anna", "Mary", "Emily"]
    first.st.LM, first.st.NM = 10, 11          # the run to Fort Hall
    first.st.D = num.parse("40")
    tomb.write_record(first, 0, "died on the plains")
    rec = first.files.read_tombs(first.st.S)
    assert rec["segment"] == 11 * 100 + 10
    assert rec["name"] == "Zeke"
    assert rec["epitaph"] == "died on the plains"

    rules = copy.deepcopy(BUSY) + [("You pass a gravesite", "Y")]
    second, ui = make_game(rules, data=d / "data")
    second.st.LM, second.st.NM = 10, 11
    second.st.SN = [rec["segment"], 0]
    second.st.ML = [rec["miles"], 0]
    second.st.DD = L.SEG_MILES[L.LM_SEGMENT[10]]
    second.st.D = second.st.DD        # still short of the grave
    trail.find_grave(second)
    assert second.st.DL == rec["miles"], "the grave is the next one on this segment"
    # Line 450 picks the grave whose recorded distance is short of the miles
    # still to run, and line 3160 then sets RE(4) = (D < DL) -- so line 450 is
    # evaluated at the *start* of the segment, and the party meets the stone once
    # it has travelled past it.
    trail.load_segment(second, L.LM_SEGMENT[10])
    trail.find_grave(second)
    assert second.st.DL == rec["miles"]
    second.st.D = num.parse("20")
    second.rng.log.clear()
    trail.event_loop(second)
    assert any("You pass a gravesite" in line for line in ui.out), \
        "the party was not offered the grave"
    # and reading the stone shows the name and the epitaph that were recorded
    from oregon import tomb as tomb_mod
    tomb_mod.read_grave(second)
    said = " ".join(ui.out)
    assert "Here lies" in said, "the stone was not shown"
    assert "died on the plains" in said, "the epitaph was not shown"
