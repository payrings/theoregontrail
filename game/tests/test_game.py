"""The game's own arithmetic, checked against the formulas in the listing.

Every expectation here is worked out by hand from the BASIC line named beside it.
Nothing here is an "expected output" from the original -- no reference trace exists
(Appendix H) -- so these are checks of the transcription, not of parity.
"""
import pytest

from oregon import num
from oregon.state import State


@pytest.fixture
def st():
    s = State()
    s.I[2] = num.parse("8")       # eight oxen
    s.I[3] = num.parse("10")      # ten sets of clothing
    s.I[8] = num.parse("1000")    # a thousand pounds
    s.NP = 5
    return s


def test_speed_caps_the_oxen_factor_at_one(game, st):
    """Line 650-660. Eight oxen is four or more, so the factor is one."""
    game.st = st
    st.MD = num.parse("20")
    st.P = num.ONE
    st.R = num.ONE
    bs = __import__("oregon.trail", fromlist=["x"]).speed(game)
    assert bs.to_float() == 20.0, "20 miles a day before Fort Laramie, steady"
    assert st.FC.to_int() == 15, "five people on filling rations eat fifteen a day"
    assert st.F0.to_int() == 0


def test_speed_falls_with_the_oxen_and_rises_with_the_pace(game, st):
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    st.MD = num.parse("20")
    st.P = num.ONE
    trail.speed(game)
    steady = st.BS.to_float()
    st.P = num.TWO                       # strenuous: times 1.5
    trail.speed(game)
    assert st.BS.to_float() == pytest.approx(steady * 1.5)
    st.P = num.parse("3")                # grueling: times 2
    trail.speed(game)
    assert st.BS.to_float() == pytest.approx(steady * 2.0)
    st.I[2] = num.parse("2")              # two oxen: the factor is 2/4
    st.P = num.ONE
    trail.speed(game)
    assert st.BS.to_float() == pytest.approx(steady * 0.5)


def test_daily_food_for_each_ration_setting(game, st):
    """``FC = NP * (4 - R)``: three, two or one a head."""
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    for r, want in ((1, 15), (2, 10), (3, 5)):
        st.R = num.parse(str(r))
        trail.speed(game)
        assert st.FC.to_int() == want, f"rations {r}"
    st.R = num.parse("3")
    trail.speed(game)
    assert st.F0.to_int() == 4, "bare bones is a penalty of four"


def test_clothing_per_person(game, st):
    """``OP = I(3) / NP``: ten sets among five is two each."""
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    st.P = num.ONE
    trail.speed(game)
    assert st.OP.to_float() == 2.0


def test_the_climate_zone_from_line_1000():
    """``ZO = (LM > 2) + (LM > 5) + (LM > 10) + (LM > 13)``, five zones."""
    trail = __import__("oregon.trail", fromlist=["x"])
    assert [trail.climate_zone(n) for n in (0, 2, 3, 5, 6, 10, 11, 13, 14, 17)] == \
        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]


def test_the_climate_lookup_matches_the_paper():
    """Line 105. Row 0 in January: codes 59 and 43, so 9 degrees and 0.039."""
    trail = __import__("oregon.trail", fromlist=["x"])
    s = State()
    s.ZO = 0
    s.AM = num.parse("1")
    assert trail.fn_w(s, 0).to_int() == 9
    assert trail.fn_w(s, 1).to_float() == pytest.approx(0.039, abs=1e-9)


def test_health_is_ninety_percent_of_yesterday_plus_the_penalties(game, st):
    """Line 3230: ``H = .9 * H + ZT + ZC + ZF + ZP + FS + H0 + HR``.

    With a warm, dry day at steady pace on filling rations, every term but ZP is
    zero and ZP is twice the pace, so 20 becomes 20 * .9 + 2.
    """
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    st.P = num.ONE
    st.R = num.ONE
    st.FC = num.ZERO
    st.TM = num.parse("3")                 # warm: no temperature penalty
    st.W = num.parse("3")                  # and no weather penalty
    st.AS = num.ZERO
    st.PF = num.parse("1000")
    st.BS = num.parse("20")
    trail.speed(game)
    st.FC = num.ZERO                   # do not eat, so only the arithmetic shows
    st.H = num.parse("20")
    trail.health_today(game)
    # 20 * .9 = 18, and ZP is twice the pace, so 2 more
    assert st.ZP.to_float() == 2.0, "ZP is P added to itself"
    assert st.H.to_float() == pytest.approx(20.0, rel=1e-9)


def test_zp_is_twice_the_pace_plus_the_weather(game, st):
    """Line 3220: ``(W > 5) + (W > 7) + P + P``."""
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    st.PF = num.parse("1000")
    st.I[3] = num.parse("10")
    for pace, weather, want in ((1, 3, 2), (2, 3, 4), (3, 3, 6),
                                (1, 6, 3), (1, 8, 4), (1, 9, 4),
                                (3, 9, 8)):
        st.P = num.parse(str(pace))
        st.W = num.parse(str(weather))
        trail.health_today(game)
        assert st.ZP.to_float() == want, (pace, weather, st.ZP.to_float())


def test_the_roms_point_nine_is_below_nine_tenths():
    """``.9`` is ``80 66 66 66 66`` — about 0.8999999999069, not 0.9.

    It is below nine tenths, and it is not the nearest float to nine tenths. Note
    that ``20 * .9`` nevertheless rounds to exactly 18, because the shortfall is
    smaller than the last bit at that magnitude; an earlier claim here that the
    product came out above 18 was wrong in both the direction and the magnitude.
    """
    from oregon import num
    v = num.parse(".9")
    assert v.raw() == bytes((0x80, 0x66, 0x66, 0x66, 0x66))
    assert 0.8999 < v.to_float() < 0.9
    assert v.to_float() != 0.9
    assert num.mul(num.parse("20"), v).to_float() == 18.0


def test_the_health_bands(game, st):
    """``INT (H / 35)``: good, fair, poor, very poor."""
    game.st = st
    for h, band in ((0, 0), (34, 0), (35, 1), (69, 1), (70, 2), (104, 2), (105, 3),
                    (139, 3)):
        st.H = num.parse(str(h))
        assert st.health_band() == band, h


def test_travel_stops_exactly_at_the_next_landmark(game, st):
    """Line 3245-3246: the last day of a segment arrives exactly."""
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    st.D = num.parse("20")
    st.M = num.parse("0")
    st.BS = num.parse("20")
    st.H0 = 0
    st.SD = 0
    st.AS = num.ZERO
    for _ in range(4):
        trail.travel_today(game)
    assert st.D.is_zero(), "D must land on exactly zero"
    assert st.M.to_float() == 20.0


def test_travel_slows_for_the_sick_and_the_snow(game, st):
    """Line 3245: a tenth off for each sick person, and the snow factor."""
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    st.D = num.parse("100")
    st.M = num.ZERO
    st.BS = num.parse("20")
    st.AS = num.ZERO
    st.H0 = 0
    trail.travel_today(game)
    assert st.M.to_float() == pytest.approx(20.0)
    st.D = num.parse("100")
    st.M = num.ZERO
    st.H0 = 2
    trail.travel_today(game)
    assert st.M.to_float() == pytest.approx(20.0 * 0.8)
    st.D = num.parse("100")
    st.M = num.ZERO
    st.H0 = 0
    st.AS = num.parse("20")               # half the speed
    trail.travel_today(game)
    assert st.M.to_float() == pytest.approx(10.0)
    st.AS = num.parse("40")               # no travel at all
    st.D = num.parse("100")
    st.M = num.ZERO
    trail.travel_today(game)
    assert st.M.is_zero()


def test_the_victim_is_never_the_leader_while_others_live(game, st):
    """Lines 11500-11505."""
    illness = __import__("oregon.illness", fromlist=["x"])
    game.st = st
    from oregon.rng import ScriptedRnd
    seen = set()
    for i in range(60):
        game.rng = ScriptedRnd(["0.0"])
        seen.add(illness.choose_victim(game))
    assert 0 not in seen, "the leader cannot fall ill while others live"
    st.NP = 1
    game.rng = ScriptedRnd(["0.0"])
    assert illness.choose_victim(game) == 0, "alone, the leader can"


def test_the_calendar_gives_february_twenty_eight_days(game, st):
    """Line 3255, and the leap year the original ignores (paper section 13)."""
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    st.AD = num.parse("28")
    st.AM = num.TWO
    st.AY = num.parse("1848")
    trail.advance_date(game)
    assert num.as_int(st.AD) == 1
    assert num.as_int(st.AM) == 3
    assert num.as_int(st.AY) == 1848


def test_the_calendar_rolls_the_year_over(game, st):
    trail = __import__("oregon.trail", fromlist=["x"])
    game.st = st
    st.AD = num.parse("31")
    st.AM = num.parse("12")
    st.AY = num.parse("1848")
    trail.advance_date(game)
    assert (num.as_int(st.AD), num.as_int(st.AM), num.as_int(st.AY)) == (1, 1, 1849)
