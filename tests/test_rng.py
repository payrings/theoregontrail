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
