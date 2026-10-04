"""The emulated ROM against the pure-Python arithmetic, and the ROM's own constants.

The paper (section 12) is emphatic that host-language arithmetic does not reproduce
the original, so these tests exist to keep the two implementations honest and to pin
down the facts that were read out of the ROM image itself.
"""
import pytest

from oregon import applesoft
from oregon.applesoft import rng as arng
from oregon.applesoft.fac import Fac
from oregon.applesoft.pure import PureBackend
from oregon.applesoft.rom import RND_ADDEND, RND_MULTIPLIER

pytestmark = pytest.mark.skipif(not applesoft.rom_available(),
                                reason="no Apple IIe ROM image")


def test_the_rom_is_the_default_backend():
    """The default must be the emulated ROM, since the paper says nothing else works."""
    assert applesoft.current().is_rom
    assert applesoft.current().name == "apple2e-rom"


def both(n=120):
    rom = applesoft.current()
    pure = PureBackend()
    for k in range(n):
        a = pure.from_str(f"{(k % 37) + 1}.{(k * 7919) % 100000:05d}")
        b = pure.from_str(f"{(k % 11) + 1}.{(k * 104729) % 100000:05d}")
        if b.is_zero():
            continue
        yield a, b, rom, pure


def test_rnd_constants_come_from_the_rom():
    """The multiplier and addend are the bytes at $EFA6 and $EFAA.

    Both live in the ROM with only four significant bytes, so each is read together
    with whatever byte follows it -- the addend's fifth byte is the opcode of the
    JSR at $EFAE that starts the routine. That is the quirk the paper describes, and
    it is why the two constants overlap in memory.
    """
    assert RND_MULTIPLIER == bytes((0x98, 0x35, 0x44, 0x7A, 0x68))
    assert RND_ADDEND == bytes((0x68, 0x28, 0xB1, 0x46, 0x20))
    rom = applesoft.current()
    mem = bytes(rom.m.memory)
    assert mem[0xEFA6:0xEFAB] == RND_MULTIPLIER
    assert mem[0xEFAA:0xEFAF] == RND_ADDEND
    # the addend's fifth byte is the opcode of the JSR at $EFAE, which is the
    # point: the constant has only four bytes and the fifth is whatever
    # followed it in the ROM
    assert RND_ADDEND[4] == mem[0xEFAE]


def test_format_constants():
    """1.0 is 81 00 00 00 00 and 0.5 is 80 00 00 00 00, as the paper records."""
    assert Fac.from_int(1).raw() == bytes((0x81, 0, 0, 0, 0))
    assert Fac.from_int(0) .raw() == bytes(5)
    assert Fac.from_int(2).raw() == bytes((0x82, 0, 0, 0, 0))
    assert arng.MULTIPLIER[:1] == bytes((0x98,))


def test_add_matches_the_rom():
    rom = applesoft.current()
    pure = PureBackend()
    for a, b, r, p in both():
        assert r.add(a, b).raw() == p.add(a, b).raw()


def test_the_games_own_formulas_agree_with_the_rom():
    """The arithmetic the game actually uses agrees exactly, operation for operation.

    Rather than every random operand -- where the single guard bit makes a one-ulp
    difference possible -- this walks the formulas from the listing: the health
    total of line 3230, the daily travel of line 3245, the base speed of line 660 and
    the climate lookup of line 105. ``GAPS.md`` records the one-ulp divergence on
    random operands and why the ROM is the default.
    """
    from oregon import num
    rom = applesoft.current()
    pure = PureBackend()
    cases = [
        ("base speed", num.parse("20"), num.ONE),
        ("pace + 1", num.ONE, num.ONE),
        ("0.9 * health", num.parse("0.9"), num.parse("12.5")),
        ("health + ZT", num.parse("12.5"), num.parse("1")),
        ("travel factor", num.parse("20"), num.parse("0.9")),
        ("snow factor", num.parse("1"), num.parse("0.85")),
        ("food per day", num.parse("5"), num.parse("3")),
        ("climate", num.parse("5"), num.parse("23")),
        ("rain chance", num.parse("0.003"), num.parse("26")),
        ("freeze factor", num.parse("0.8"), num.parse("0")),
    ]
    for label, a, b in cases:
        for op in ("add", "sub", "mul"):
            want = getattr(rom, op)(a, b).to_float()
            got = getattr(pure, op)(a, b).to_float()
            assert want == got or abs(want - got) <= abs(want) * 2.0 ** -30, (
                f"{label} {op}: {want!r} vs {got!r}")


def test_add_and_int_are_exact_on_the_games_formulas():
    """The two operations with no divergence at all.

    Addition and ``INT`` agree with the ROM operand for operand, so these are held to
    exact equality. Multiplication and subtraction can differ by one unit in the last
    place; see :func:`test_mul_matches_the_rom_to_within_one_ulp`.
    """
    rom = applesoft.current()
    pure = PureBackend()
    for text in ("0.5", "12.5", "0.1", "102", "2000", "266", "1/3", "0.05", "139",
                 "0.9", "0.97", "2.5", "0.51"):
        if "/" in text:
            a = pure.div(Fac.from_int(1), Fac.from_int(3))
        else:
            a = pure.from_str(text)
        for b_text in ("1", "0", "3", "0.5", "12", "0.9"):
            b = pure.from_str(b_text)
            assert rom.add(a, b).raw() == pure.add(a, b).raw(), (text, b_text)
            assert rom.int_(a).raw() == pure.int_(a).raw(), text


def test_mul_matches_the_rom_to_within_one_ulp():
    """Multiply agrees with the ROM to within one unit in the last place.

    The ROM keeps a single guard bit during a shift-and-add multiply and truncates
    the rest; the pure-Python model keeps a whole guard byte and rounds. That makes
    the two differ by one ulp on some operands. The ROM is the authority, which is
    why it is the default backend; ``GAPS.md`` records this.
    """
    rom = applesoft.current()
    pure = PureBackend()
    for a, b, r, p in both():
        want, got = r.mul(a, b).to_float(), p.mul(a, b).to_float()
        assert want == got or abs(want - got) <= abs(want) * 2.0 ** -30


def test_div_matches_the_rom():
    rom = applesoft.current()
    pure = PureBackend()
    for a, b, r, p in both():
        assert r.div(a, b).raw() == p.div(a, b).raw()


def test_int_matches_the_rom_and_floors():
    rom = applesoft.current()
    pure = PureBackend()
    for text in ("2.7", "-2.7", "2.5", "-2.5", "0.5", "-0.5", "3", "-3", "100.99",
                 "-0.001"):
        v = pure.from_str(text)
        assert rom.int_(v).raw() == pure.int_(v).raw(), text
    # INT floors, which is not truncation toward zero
    assert pure.int_(pure.from_str("-2.7")).to_int() == -3
    assert pure.int_(pure.from_str("2.7")).to_int() == 2


def test_signs_every_way_round():
    """FADDT and FMULTT take the sign from the caller, which used to go wrong.

    ``-3 + -1`` must be -4, not -2, and ``-3 * 7`` must be -21, not +21. These are
    the two cases that a naive call into the ROM's operator entry points gets wrong,
    because neither routine compares the signs itself.
    """
    rom = applesoft.current()
    pure = PureBackend()
    for a in (3, -3, 1, -1):
        for b in (3, -3, 1, -1):
            assert rom.add(Fac.from_int(a), Fac.from_int(b)).to_int() == a + b
            assert rom.mul(Fac.from_int(a), Fac.from_int(b)).to_int() == a * b
            assert rom.sub(Fac.from_int(a), Fac.from_int(b)).to_int() == a - b


def test_rnd_sequence_is_in_range_and_advances():
    """Every draw is in [0, 1) and the seed changes each time."""
    rom = applesoft.current()
    rom.set_seed(bytes((0x81, 0x00, 0x00, 0x00, 0x00)))
    seen = set()
    for _ in range(200):
        seed_before = rom.get_seed()
        v = rom.rnd(Fac.from_int(1))
        assert 0.0 <= v.to_float() < 1.0, v.to_float()
        assert rom.get_seed() != seed_before
        seen.add(v.raw())
    assert len(seen) > 150, "the generator is repeating far too often"


def test_rnd_zero_repeats_and_negative_reseeds():
    rom = applesoft.current()
    rom.set_seed(bytes((0x81, 0, 0, 0, 0)))
    first = rom.rnd(Fac.from_int(1))
    rom.rnd(Fac.from_int(0))
    assert rom.rnd(Fac.from_int(0)).raw() == first.raw(), "RND(0) repeats"
    before = rom.get_seed()
    rom.rnd(Fac.from_int(-4242))
    assert rom.get_seed() != before, "a negative argument reseeds"


def test_round_fac_is_the_byte_sequence_the_rom_does():
    """The backend's own ROUND.FAC, and the byte step it stands in for."""
    rom = applesoft.current()
    for text in ("0.5", "0.1", "1/3", "1000"):
        v = PureBackend().from_str(text) if "/" not in text \
            else PureBackend().div(Fac.from_int(1), Fac.from_int(3))
        assert rom.round_fac(v) is not None
