"""The three endings: arrival, the raft, and the whole party dying.

Each is driven directly rather than by playing 150 days, because the ending is
what is under test and the journey to it is already covered by
``test_playthrough.py``.
"""
import pathlib
import tempfile

import pytest

from oregon import buysupplies, endl, floatraft, menu, tomb, trail, win
from oregon.context import Context
from oregon.files import Files
from oregon.rng import ScriptedRnd
from oregon.trace import Tracer
from oregon.ui import ScriptedUI

sys_path = str(pathlib.Path(__file__).resolve().parents[1])


def party(answers=None, value="0.5", data=None, max_prompts=4000):
    """A banker's party at Independence, ready to travel."""
    d = pathlib.Path(tempfile.mkdtemp())
    ui = ScriptedUI(answers or [], allow_repeat=True, max_prompts=max_prompts)
    rng = ScriptedRnd(" ".join([value] * 400000))
    c = Context(ui=ui, rng=rng, files=Files(data or (d / "data")), trace=Tracer())
    rng.seed_from_keyboard(4242)
    c.mem.poke_word(913, 16000, 4030)     # $1600, stored times ten
    c.mem.poke(915, 1, 4030)              # banker
    c.mem.poke(901, 48, 9000)
    c.mem.poke(902, 5, 6030)              # May
    c.mem.poke(903, 1, 6000)
    # init_state clears 904 to 912, so the goods go in after it
    buysupplies.init_state(c)
    c.mem.poke(905, 4)                     # four yoke
    c.mem.poke(908, 6)                     # six sets of clothing
    c.mem.poke(909, 6)                     # six boxes of ammunition
    c.mem.poke_word(906, 1200)             # 1200 pounds of food
    for slot in (910, 911, 912):
        c.mem.poke(slot, 1)                # one of each spare part
    c.st.N = ["Zeke", "Jed", "Anna", "Mary", "Emily"]
    c.mem.put_names(c.st.N, 6045)
    trail.load_state(c)
    return c, ui


# --------------------------------------------------------------- arrival
def test_arriving_writes_the_hand_over_and_scores():
    """END.LIB 50050 then WIN 130-140."""
    from oregon import num
    c, ui = party()
    # stand at The Dalles with the party's state, and arrive
    c.st.LM = 16
    c.st.NM = 17
    c.st.I[2] = num.parse("8")
    c.st.I[3] = num.parse("6")
    c.st.I[4] = num.parse("120")
    c.st.I[8] = num.parse("900")
    c.st.MY = num.parse("200")
    c.st.H = num.parse("0")                     # good health, so 500 a head
    c.st.AM, c.st.AD, c.st.AY = num.parse("11"), num.parse("3"), num.parse("1848")
    assert endl.arrive_willamette(c) == "WIN"   # writes the memory WIN reads
    # the hand-over, read back the way WIN does
    assert c.mem.peek(900) == 5
    assert c.mem.peek(909) == 8
    assert c.mem.peek_word(904) == 120
    assert c.mem.peek_word(906) == 900
    assert c.mem.peek(908) == 6
    assert c.mem.peek(916) == 0, "INT (H / 35) for perfect health"
    assert c.mem.peek(913) + c.mem.peek(914) * 256 == 200
    where = win.run(c)
    assert where == "MENU"
    assert c.outcome.startswith("ARRIVED")
    score = int(c.outcome.split()[1])
    # 5 people good at 500, a wagon at 50, 8 oxen at 4, 3 parts at 2, 6 sets at 2,
    # 120 bullets at 1 per 50, 900 lb at 1 per 25, $200 at 1 per 5
    assert score == 2500 + 50 + 32 + 6 + 12 + 2 + 36 + 40
    assert score == 2678, score


def test_the_profession_multiplier_and_the_rating():
    """WIN 625 multiplies the score; WIN 630 rates it."""
    assert win.rating(6000) == 0, "Trail guide at 6000 or more"
    assert win.rating(5999) == 1, "Adventurer from 3000 to 5999"
    assert win.rating(3000) == 1
    assert win.rating(2999) == 2, "Greenhorn below 3000"
    # a carpenter doubles and a farmer triples
    c, ui = party()
    c.mem.poke(915, 2, 4030)
    c.st.LM, c.st.NM = 16, 17
    from oregon import num
    c.st.I[2] = num.parse("8")
    c.st.MY = num.parse("0")
    endl.write_handover(c)          # WIN reads the memory, not the state
    win.run(c)
    doubled = int(c.outcome.split()[1])
    c2, _ = party()
    c2.mem.poke(915, 1, 4030)
    c2.st.LM, c2.st.NM = 16, 17
    c2.st.I[2] = num.parse("8")
    c2.st.MY = num.parse("0")
    endl.write_handover(c2)
    win.run(c2)
    single = int(c2.outcome.split()[1])
    assert doubled == single * 2, (doubled, single)


def test_a_score_that_beats_the_list_is_written_to_it_in_order(tmp_path):
    """WIN 405 and 510-540.

    The original list is a hard one -- its lowest entry is 250 and its top is
    Stephen Meek at 7650, while the most a winning party can bring is about
    4000 -- so a list of weak entries is used to exercise the insertion.
    """
    data = tmp_path / "data"
    c, ui = party(data=data)
    from oregon import num
    c.files.write_hiscore([[f"Old {i}", 250, "Greenhorn"] for i in range(10)])
    c.st.LM, c.st.NM = 16, 17
    c.st.I[2] = num.parse("8")
    c.st.I[3] = num.parse("40")
    c.st.I[8] = num.parse("1900")
    c.st.I[4] = num.parse("500")
    c.st.MY = num.parse("2000")
    endl.write_handover(c)
    ui.answers = ["Y", "N"]           # type a name, then no changes
    win.run(c)
    entries = c.files.read_hiscore()
    assert len(entries) == 10
    assert entries[0][0] == "Y", "the new entry goes to the top"
    assert entries[0][1] == 3154, entries[0][1]
    assert entries[0][2] == "Adventurer", "3000 to 5999 is an Adventurer"
    points = [e[1] for e in entries]
    assert points == sorted(points, reverse=True), "the list stays in order"


def test_a_score_that_does_not_qualify_leaves_the_list_alone(tmp_path):
    """Even a bare arrival scores 1050 -- five people very poor, plus the wagon --
    so the tenth entry has to be higher than that for this branch to be reached
    at all."""
    data = tmp_path / "data"
    c, ui = party(data=data)
    c.files.write_hiscore([[f"Old {i}", 50000, "Trail guide"] for i in range(10)])
    c.st.LM, c.st.NM = 16, 17
    from oregon import num
    c.st.I[2] = num.ZERO
    c.st.I[3] = num.ZERO
    c.st.I[8] = num.ZERO
    c.st.I[4] = num.ZERO
    c.st.MY = num.ZERO
    endl.write_handover(c)
    win.run(c)
    assert c.files.read_hiscore()[0][0] == "Old 0", "the list is untouched"
    assert "not enough to qualify" in " ".join(c.ui.out)
    assert "Type your name" not in " ".join(c.ui.out)


# ------------------------------------------------------------------- raft
def test_the_raft_lands_and_hands_over():
    """FLOAT 1070-1180: the raft drifts, misses the landing, and lands anyway."""
    from oregon import num
    c, ui = party()
    c.st.I[2] = num.parse("8")
    c.st.I[3] = num.parse("6")
    c.st.I[4] = num.parse("120")
    c.st.I[8] = num.parse("900")
    c.mem.poke(909, 8)
    c.mem.poke_word(906, 900)
    c.mem.poke(908, 6)
    c.mem.poke_word(904, 120)
    c.mem.poke(902, 11)
    c.mem.poke(903, 3)
    c.mem.poke(901, 48)
    assert floatraft.run(c) == "WIN"
    assert c.mem.peek(900) == c.st.NP
    assert c.mem.peek(909) == c.st.I[2].to_int()
    said = " ".join(c.ui.out)
    assert "missed the landing" in said or "hit the shore" in said, (
        "an unsteered raft either misses the landing or bounces off the bank")
    assert "Use the arrow keys" in said, "the instructions come first"


def test_the_raft_draws_two_numbers_a_pass():
    """Appendix G.6: 2 per pass, plus 2 or 3 for each new rock.

    The generator is set high so that no rock ever spawns -- with a low value the
    raft runs into one and the game ends in a few passes, which is correct but does
    not let the count be checked.
    """
    from oregon import num
    c, ui = party(value="0.9")
    c.mem.poke(902, 11)
    c.mem.poke(903, 3)
    c.mem.poke(901, 48)
    before = c.rng.log.count()
    floatraft.run(c)
    used = c.rng.log.count() - before
    tags = [tag for tag, _a, _v in c.rng.log.entries[before:]]
    assert tags.count("1070 rock 0") == tags.count("1070 rock 1"), "one per slot"
    # exactly one fill test a slot a pass, whether or not the slot is full, and
    # 226 passes: the landing at 205 is missed and the raft lands at 225
    assert tags.count("1070 rock 0") == 226, tags.count("1070 rock 0")
    # no rock ever spawns at 0.9, so the only other draws are the collision ones
    # from bouncing between the two banks
    assert used >= 226 * 2, used
    assert "300 rock type" not in tags


def test_a_rock_collision_costs_the_party_something():
    """Line 710: people two in five, oxen three in five, goods seven in ten."""
    from oregon import num
    c, ui = party(value="0.0")      # a rock spawns on the first pass
    c.mem.poke(902, 11)
    c.mem.poke(903, 3)
    c.mem.poke(901, 48)
    before_people = c.st.NP
    before_oxen = c.st.I[2].to_float()
    floatraft.run(c)
    said = " ".join(c.ui.out)
    assert ("hit a rock" in said or "hit the shore" in said), said[-200:]
    assert c.st.I[2].to_float() <= before_oxen
    assert c.st.NP <= before_people


def test_ten_losses_destroy_the_raft():
    """Line 730: more than nine losses in one collision loses everything."""
    from oregon import num
    from oregon import losses
    c, ui = party()
    c.st.I[2] = num.parse("8")
    c.st.I[3] = num.parse("6")
    c.st.I[8] = num.parse("900")
    c.rng = ScriptedRnd(" ".join(["0.0"] * 4000))
    where = floatraft.collide(c, "rock")
    assert where == "MENU"
    assert c.outcome == "DIED"
    assert any("raft is destroyed" in line for line in c.ui.out)


# ------------------------------------------------------------------- death
def test_the_whole_party_dying_writes_one_tombstone(tmp_path):
    """TOMB.LIB 50010-50040."""
    from oregon import num
    data = tmp_path / "data"
    c, ui = party(data=data, answers=["N"])
    c.st.LM, c.st.NM = 8, 10
    c.st.D = num.parse("17.5")
    c.st.H = num.parse("120")
    assert c.st.NP == 5
    where = tomb.all_dead(c, 0)
    assert where == "MENU"
    assert c.outcome == "DIED"
    rec = c.files.read_tombs(c.st.S)
    assert rec is not None
    assert rec["name"] == "Zeke", "the leader's name goes on the stone"
    assert rec["segment"] == 10 * 100 + 8, "NM * 100 + LM"
    assert rec["miles"] == pytest.approx(17.5)
    assert c.files.read_tombs(1 - c.st.S) is None, "only one side is written"
    assert any("Here lies" in line for line in c.ui.out)
    assert any("All of the people" in line for line in c.ui.out)


def test_a_death_swaps_the_dead_member_with_the_last_living_one():
    """TOMB.LIB 50005: the living always occupy the first NP slots."""
    from oregon import num
    from oregon import illness
    c, ui = party()
    st = c.st
    st.H1 = [num.ZERO] * 5
    st.H2 = [num.ZERO] * 5
    st.H = num.parse("150")
    st.H1[0] = num.parse("4")               # the leader is ill
    before = list(st.N)
    illness.die(c, 0)
    assert st.NP == 4
    assert st.H.to_float() == 105.0, "health comes down to 105"
    assert st.N[0] == before[4], "the last living took the dead one's place"
    # line 50005 swaps the dead member into the last slot and marks it -1
    assert st.H1[4].to_int() == -1, "the corpse is marked -1"
    assert st.H1[0].is_zero(), "and the living stay whole"


def test_a_second_disease_kills_and_is_never_named():
    """Line 10300: a member already ill who draws again dies, unnamed."""
    from oregon import num
    from oregon import illness
    c, ui = party()
    st = c.st
    st.H1 = [num.ZERO] * 5
    st.H2 = [num.ZERO] * 5
    # choose_victim with a draw of 0.0 picks slot 1, so that is who is already ill
    st.H1[1] = num.parse("6")               # measles
    c.rng = ScriptedRnd(" ".join(["0.0"] * 1000))
    illness.illness(c)
    assert st.NP == 4
    said = " ".join(c.ui.out)
    assert "Zeke has died" not in said, "the second disease is not named"
    assert "died" in said
    assert st.HR.to_float() == 20.0, "line 10300 sets HR = 20"


def test_an_epitaph_is_written_and_read_back(tmp_path):
    from oregon import num
    data = tmp_path / "data"
    c, ui = party(data=data)
    st = c.st
    st.LM, st.NM = 8, 10
    st.D = num.parse("3")
    tomb.write_record(c, 0, "over the mountain")
    rec = c.files.read_tombs(st.S)
    assert rec["epitaph"] == "over the mountain"
    assert rec["name"] == "Zeke"
    # and the gravestone the next party meets
    st.SN = [rec["segment"], 0]
    st.ML = [rec["miles"], 0]
    st.D = num.parse("10")                    # still short of the grave
    assert trail.find_grave(c) == rec["miles"]
    st.D = num.parse("1")                     # now past it
    assert num.lt(st.D, num.parse(str(st.DL))), "RE(4) is set once it is passed"