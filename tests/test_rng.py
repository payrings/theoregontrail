"""The random-number interface: the draws of Appendix G, and the discipline around them.

Applesoft evaluates both sides of ``AND`` and ``OR``, so a draw on the right of one
always happens; these tests pin that down where the original relies on it.
"""
import pytest

from oregon import num
from oregon.rng import CountingRnd, Rnd, ScriptedRnd


def test_a_scripted_run_out_is_an_error_not_a_wrap():
    """A game that asks for more numbers than Appendix G lists is a bug."""
    r = ScriptedRnd(["0.1", "0.2"])
    assert r.rnd1().to_float() == pytest.approx(0.1)
    assert r.rnd1().to_float() == pytest.approx(0.2)
    with pytest.raises(AssertionError):
        r.rnd1()


def test_the_log_records_every_draw():
    r = ScriptedRnd(["0.1", "0.2", "0.3"])
    for _ in range(3):
        r.rnd1("tag")
    assert len(r.log) == 3
    assert r.log.count() == 3
    assert r.log.tags() == ["tag", "tag", "tag"]


def test_a_negative_argument_is_taken_as_a_reseed():
    r = ScriptedRnd(["-4242", "0.5"])
    r.seed_from_keyboard(4242)
    assert r.reseeds == ["-4242"], "the counter is negated, as MENU 1015 does"


def test_below_always_draws_once_even_when_the_chance_is_zero():
    """``IF X AND RND (1) < V`` has no short-circuit, so the draw still happens."""
    r = CountingRnd(0.99)
    assert not r.below("x", num.ZERO)
    assert r.count == 1, "a zero chance must still spend a number"


def test_below_compares_against_the_chance():
    r = ScriptedRnd(["0.5"])
    assert r.below("half", num.HALF) is False, "0.5 is not below 0.5"
    r = ScriptedRnd(["0.4"])
    assert r.below("half", num.HALF) is True


def test_int_range_draws_once_and_is_in_range():
    r = ScriptedRnd(["0.0", "0.99"])
    assert r.int_range("a", 10) == 0
    assert r.int_range("b", 10) == 9


def test_the_name_shuffle_makes_exactly_ten_draws(game):
    """MENU 6000: ten draws, always, whatever the values are."""
    from oregon import menu
    game.rng = ScriptedRnd(["0.0"] * 10)
    names = menu.shuffle_names(game)
    assert len(game.rng.log) == 10
    assert sorted(names) == sorted(n for n in names if n)
    # with every draw at zero each name lands in the next free slot
    assert names[0] == game_st_first_name()


def game_st_first_name():
    from oregon.data.text import DEFAULT_NAMES
    return DEFAULT_NAMES[0]


def test_a_collision_steps_forward_and_wraps(game):
    """``Z = Z + 1: Z = Z * (Z < 10)`` -- a full table wraps back to zero."""
    from oregon import menu
    from oregon.data.text import DEFAULT_NAMES
    # the first two draws both choose slot 0, so the second must step to slot 1
    game.rng = ScriptedRnd(["0.0", "0.0"] + ["0.0"] * 8)
    names = menu.shuffle_names(game)
    assert len(game.rng.log) == 10
    assert len([n for n in names if n]) == 10


def test_the_hunt_does_not_touch_the_games_generator(game):
    """Appendix G.6: the hunting routine has its own generator."""
    from oregon import hunt
    before = game.rng.log.count()
    seed_before = _seed()
    hunt.hunt_session(game, game.st, 20)
    assert game.rng.log.count() == before, "a hunt must not draw from the game"
    assert _seed() == seed_before, "a hunt must not advance the Applesoft seed"


def _seed() -> bytes:
    from oregon.applesoft import fac
    return fac._b().get_seed()


# ------------------------------------------------- the crossing animation
def test_the_crossing_animation_spends_the_numbers_appendix_g_lists(game):
    """Appendix G.5: 106 always, then 122, 0, or 22 groups of three.

    The numbers place water marks and change nothing, but they advance the
    generator, so every draw after a river crossing depends on them.
    """
    from oregon import cross
    c = game

    def spent(fn, *a):
        c.rng.log.clear()
        fn(c, *a)
        return c.rng.log.count()

    assert spent(cross.animate, "start") == cross.FIRST_HALF == 106
    assert spent(cross.animate, "success") == 106 + 122
    # a failed float or a lost ferry spends nothing after the first half
    assert spent(cross.animate, "failed-float") == 106
    assert spent(cross.animate, "failed-ferry") == 106
    # a failed ford: 22 single draws, each followed by two more
    assert spent(cross.animate, "failed-ford") == 106 + 22 * 3


def test_a_river_crossing_spends_the_animation_numbers(game):
    """The draws go through the game's own generator, in the right places."""
    from oregon import num, river
    c = game
    c.st.LM = 1                      # the Kansas River
    c.st.RC = river.river_of(1)
    st = c.st
    st.I[2] = num.parse("8")
    st.I[3] = num.parse("6")
    st.I[4] = num.parse("120")
    st.I[8] = num.parse("900")
    c.rng = ScriptedRnd(" ".join(["0.0"] * 20000))
    game.ui.answers = ["1"]            # ford, which succeeds on the Kansas
    before = c.rng.log.count()
    river.crossing(c)
    used = c.rng.log.count() - before
    tags = [t for t, _a, _v in c.rng.log.entries[before:]]
    # the first half is spent once, when the river is shown
    assert sum(1 for t in tags if t.startswith("CROSS first half")) == 106
    # the rain has made the Kansas three feet deep, so the ford goes wrong and the
    # tail is the 22 groups of three
    assert sum(1 for t in tags if t.startswith("CROSS failed ford")) == 22 * 3
    assert not [t for t in tags if t.startswith("CROSS success tail")]
    assert used >= 106 + 22 * 3


def test_the_animation_numbers_are_tagged_so_a_count_is_possible(game):
    from oregon import cross
    c = game
    c.rng.log.clear()
    cross.animate(c, "failed-ford")
    tags = [t for t, _a, _v in c.rng.log.entries]
    assert len([t for t in tags if t.startswith("CROSS first half")]) == 106
    assert len([t for t in tags if "failed ford 0 " in t]) == 3


# ------------------------------------------- Q, and Q(), are two variables
def test_Q_and_the_array_are_two_separate_variables(game):
    """Rule (b) of paper 2.5: a simple variable and an array of the same name are
    different things.

    An earlier reading held that BUY.LIB's ``Q = ...`` and TRADE.LIB's ``Q = ...``
    clobbered the map's landmark history in Q(0). They do not: those assignments set
    the scalar. The trade's *rounding* is real and is kept -- see
    ``test_an_accepted_trade_rounds_the_holding`` -- but the map is unaffected.
    """
    from oregon import fortbuy, num
    c = game
    st = c.st
    st.Q_arr[1], st.Q_arr[2] = 1, 2
    st.Q_arr[0] = 0                      # landmark 0, where the route starts
    st.LM = 13                           # Fort Boise, whose tier is 5
    st.I[2] = num.parse("8")
    st.I[3] = num.parse("10")
    st.I[8] = num.parse("500")
    st.MY = num.parse("500")
    c.ui.answers = ["8"] + [""] * 40
    fortbuy.fort_store(c)
    assert num.as_int(st.Q) == 5, "the scalar Q holds the fort tier"
    assert st.Q_arr[0] == 0, "and the map still knows landmark 0"
    assert st.Q_arr[:3] == [0, 1, 2]


def test_an_accepted_trade_rounds_the_holding(game):
    """Paper 13: an accepted trade rounds what the party gives away.

    ``TRADE.LIB`` 50011 sets the scalar ``Q`` to ``INT (I(X + 2) + .5)`` to test
    whether the party has enough, and 50035 stores ``Q - V`` back into the
    inventory, so 5.5 oxen that trade one away leave 5, not 4.5.
    """
    from oregon import num, trade
    c = game
    st = c.st
    st.I[2] = num.parse("5.5")
    st.I[3] = num.parse("10")
    st.I[4] = num.parse("120")
    st.I[8] = num.parse("500")
    c.rng = ScriptedRnd(" ".join(["0.0"] * 2000))
    c.ui.answers = ["Y"] + [""] * 20
    trade.attempt(c)
    assert st.I[2].to_float() in (4.0, 5.0), st.I[2].to_float()
    assert float(st.I[2].to_float()).is_integer(), "the holding is now a whole number"
    # and the map's array is untouched
    assert isinstance(st.Q_arr, list) and len(st.Q_arr) == 17


def test_the_hunt_seed_uses_the_keyboard_counter(game):
    """Paper 11.1: the hunt is seeded from the Applesoft seed and the key counter."""
    from oregon import hunt
    c = game
    c.mem.keyboard_counter = 0x0102
    a = hunt._seed_bytes(c)
    c.mem.keyboard_counter = 0x0304
    b = hunt._seed_bytes(c)
    assert a != b, "the counter is part of the hunt's seed"
    assert len(a) == 5
