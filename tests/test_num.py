"""The numeric interface: the format, the money pattern, and the arithmetic.

Each expectation is worked out by hand from the BASIC line it comes from, and the
arithmetic checks run against the emulated ROM, which is the default.
"""
import pytest

from oregon import num
from oregon.applesoft.fac import Fac


def test_the_number_format_is_five_bytes_and_the_cap_is_139():
    assert Fac.from_int(1).raw() == bytes((0x81, 0, 0, 0, 0))
    assert Fac.from_int(0).raw() == bytes(5)
    # 139 is 0.54296875 * 2**8, so the exponent byte is 136
    assert num.parse("139").raw() == bytes((0x88, 0x0B, 0x00, 0x00, 0x00))


def test_int_is_floor_not_truncation():
    assert num.trunc(num.parse("2.7")) == 2
    assert num.trunc(num.parse("-2.7")) == -3
    assert num.trunc(num.parse("-0.5")) == -1


def test_the_money_pattern_rounds_to_the_nearest_cent():
    """Line 200: ``V = INT (V * 100 + .5)``, then ``RIGHT$`` for the cents."""
    for value, want in (("1234.56", " 1234.56"),
                        ("1234.564", " 1234.56"),
                        ("1234.567", " 1234.57"),
                        ("0", " 0. 0"),
                        ("0.05", " 0. 5"),
                        ("1.05", " 1.05"),
                        ("2", " 2.00"),
                        ("1600", " 1600.00")):
        got = num.dollar(num.trunc(num.add(
            num.mul(num.parse(value), num.parse("100")), num.parse(".5"))))
        assert got == want, (value, got, want)


def test_the_constants_hold_what_var_bin_holds():
    """C0 to C4 and P5 are 0, 1, 2, 3, 4 and 0.5 (Appendix E.1)."""
    assert num.C0.raw() == bytes(5)
    assert num.C1.to_int() == 1
    assert num.C2.to_int() == 2
    assert num.C3.to_int() == 3
    assert num.C4.to_int() == 4
    assert num.P5.raw() == bytes((0x80, 0, 0, 0, 0))


def test_the_games_own_inconstants_are_what_the_rom_produces():
    """The literals the game leans on, as the ROM's conversion makes them.

    ``0.8`` is ``80 4C CC CC CD`` and ``0.2`` is ``7E 4C CC CC CD`` -- both classic
    Applesoft values, and neither the nearest float. The paper is explicit that this
    matters, which is why they go through the backend rather than a Python literal.
    """
    assert num.parse("0.8").raw() == bytes((0x80, 0x4C, 0xCC, 0xCC, 0xCD))
    assert num.n08.raw() == bytes((0x7D, 0x23, 0xD7, 0x0A, 0x3E))   # .08
    assert num.n02.raw() == bytes((0x7E, 0x4C, 0xCC, 0xCC, 0xCD))
    assert num.parse("0.5").raw() == bytes((0x80, 0, 0, 0, 0))
    assert num.parse("2.5").raw() == bytes((0x82, 0x20, 0, 0, 0))


def test_a_third_is_the_classic_applesoft_third():
    third = num.div(num.ONE, num.parse("3"))
    assert third.raw() == bytes((0x7F, 0x2A, 0xAA, 0xAA, 0xAB))


def test_three_thirds_reaches_exactly_one():
    """Each operator rounds as if stored, so three thirds lands on 1.0 exactly.

    Applesoft keeps one guard byte across the whole of ``1/3 + 1/3 + 1/3`` and gets
    0.9999999998 instead; rounding each operator is the documented deviation, and
    ``Chain`` is there for the expressions where the original's own value matters.
    ``GAPS.md`` records it.
    """
    third = num.div(num.ONE, num.parse("3"))
    total = num.add(num.add(third, third), third)
    assert total.raw() == Fac.from_int(1).raw()
    chained = num.chain(third).add(third).add(third).done()
    assert chained.to_float() == pytest.approx(1.0, abs=1e-6)


def test_comparisons_are_exact_and_ordered():
    pairs = [("1", "2", -1), ("2", "1", 1), ("1", "1", 0), ("-1", "1", -1),
             ("1", "-1", 1), ("0", "1", -1), ("1000", "999", 1),
             ("0.5", "0.5", 0)]
    for a, b, want in pairs:
        assert num.cmp(num.parse(a), num.parse(b)) == want, (a, b)


def test_a_comparison_is_one_or_zero_for_the_arithmetic_that_uses_it():
    """``(Z = 1) * 1600`` and ``(AS > 30)``: a comparison has the value 1 or 0."""
    assert num.b2i(num.gt(num.parse("31"), num.parse("30"))) == 1
    assert num.b2i(num.gt(num.parse("30"), num.parse("30"))) == 0
    assert num.mul(num.bool_(True), num.parse("1600")).to_int() == 1600
    assert num.mul(num.bool_(False), num.parse("1600")).to_int() == 0


def test_a_chain_keeps_the_guard_byte_between_operators():
    """``.9 * H + ZT + ZC`` must be one expression, rounded once at the end."""
    chained = num.chain(num.parse("266")).mul(num.n09).add(num.parse("4")).done()
    stepped = num.store(num.add(num.mul(num.parse("266"), num.n09), num.parse("4")))
    assert chained.raw() == stepped.raw()


def test_an_overflow_is_a_defined_error_not_a_python_crash():
    """The format has no infinities, so a result out of range is Applesoft error 6."""
    from oregon.applesoft.pure import OverflowArithmetic, PureBackend
    huge = Fac(bytes((0xFE, 0x7F, 0xFF, 0xFF, 0xFF)))
    with pytest.raises(OverflowArithmetic):
        PureBackend().mul(huge, huge)


def test_underflow_gives_zero_as_the_format_does():
    from oregon.applesoft.pure import PureBackend
    tiny = num.parse("0.0000000000000000000000000001")
    assert num.mul(tiny, tiny).is_zero()


def test_str_gives_a_leading_space_for_a_positive_number():
    assert num.str_(num.parse("1234")) == " 1234"
    assert num.str_(num.parse("-3.5")) == "-3.5"
    assert num.str_(num.ZERO) == " 0"
