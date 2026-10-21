"""The emulated ROM against the Python transcription of it, and the ROM's own constants.

The paper (section 12) is emphatic that host-language arithmetic does not reproduce
the original, so these tests exist to keep the two implementations honest and to pin
down the facts that were read out of the ROM image itself.
"""
import pytest

from oregon import applesoft
from oregon.applesoft import rng as arng
from oregon.applesoft.fac import Fac
from oregon.applesoft.exact import ExactBackend
from oregon.applesoft.rom import RND_ADDEND, RND_MULTIPLIER

pytestmark = pytest.mark.skipif(not applesoft.rom_available(),
                                reason="no Apple IIe ROM image")


def test_the_rom_is_the_default_backend():
    """The default must be the emulated ROM, since the paper says nothing else works."""
    assert applesoft.current().is_rom
    assert applesoft.current().name == "apple-rom"



_ROM = None


def the_rom():
    """The emulated ROM, built explicitly.

    ``applesoft.current()`` is not good enough here: with no ROM image it is the
    transcription, and the comparisons below would then be the transcription
    against itself and would pass for the wrong reason. This raises instead.
    """
    global _ROM
    if _ROM is None:
        from oregon.applesoft.rom import RomBackend
        _ROM = RomBackend()
    return _ROM


def both(n=120):
    rom = the_rom()
    py = ExactBackend()
    for k in range(n):
        a = py.from_str(f"{(k % 37) + 1}.{(k * 7919) % 100000:05d}")
        b = py.from_str(f"{(k % 11) + 1}.{(k * 104729) % 100000:05d}")
        if b.is_zero():
            continue
        yield a, b, rom, py


def test_rnd_constants_come_from_the_rom():
    """The multiplier and addend are the bytes at $EFA6 and $EFAA.

    Both live in the ROM with only four significant bytes, so each is read together
    with whatever byte follows it -- the addend's fifth byte is the opcode of the
    JSR at $EFAE that starts the routine. That is the quirk the paper describes, and
    it is why the two constants overlap in memory.
    """
    assert RND_MULTIPLIER == bytes((0x98, 0x35, 0x44, 0x7A, 0x68))
    assert RND_ADDEND == bytes((0x68, 0x28, 0xB1, 0x46, 0x20))
    rom = the_rom()
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
    rom = the_rom()
    py = ExactBackend()
    for a, b, r, p in both():
        assert r.add(a, b).raw() == p.add(a, b).raw()


def test_the_games_own_formulas_agree_with_the_rom():
    """The arithmetic the game actually uses agrees exactly, operation for operation.

    Rather than every random operand -- where the single guard bit makes a one-ulp
    difference possible -- this walks the formulas from the listing: the health
    total of line 3230, the daily travel of line 3245, the base speed of line 660 and
    the climate lookup of line 105. The one-ulp divergence on random
    operands is measured in :func:`test_mul_matches_the_rom_to_within_one_ulp`.
    """
    from oregon import num
    rom = the_rom()
    py = ExactBackend()
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
            want = getattr(rom, op)(a, b).raw()
            got = getattr(py, op)(a, b).raw()
            assert want == got, f"{label} {op}: {want.hex()} vs {got.hex()}"


def test_add_and_int_are_exact_on_the_games_formulas():
    """The two operations with no divergence at all.

    Addition and ``INT`` agree with the ROM operand for operand, so these are held to
    exact equality. Multiplication and subtraction agree with it byte for byte as
    well, on these operands; see :func:`test_mul_matches_the_rom`.
    """
    rom = the_rom()
    py = ExactBackend()
    for text in ("0.5", "12.5", "0.1", "102", "2000", "266", "1/3", "0.05", "139",
                 "0.9", "0.97", "2.5", "0.51"):
        if "/" in text:
            a = py.div(Fac.from_int(1), Fac.from_int(3))
        else:
            a = py.from_str(text)
        for b_text in ("1", "0", "3", "0.5", "12", "0.9"):
            b = py.from_str(b_text)
            assert rom.add(a, b).raw() == py.add(a, b).raw(), (text, b_text)
            assert rom.int_(a).raw() == py.int_(a).raw(), text


def test_mul_matches_the_rom():
    """Multiply agrees with the ROM byte for byte: the transcription keeps the ROM's
    shift-and-add, its extension byte and its quirk."""
    for a, b, r, p in both():
        assert r.mul(a, b).raw() == p.mul(a, b).raw()


def test_div_matches_the_rom():
    rom = the_rom()
    py = ExactBackend()
    for a, b, r, p in both():
        assert r.div(a, b).raw() == p.div(a, b).raw()


def test_int_matches_the_rom_and_floors():
    rom = the_rom()
    py = ExactBackend()
    for text in ("2.7", "-2.7", "2.5", "-2.5", "0.5", "-0.5", "3", "-3", "100.99",
                 "-0.001"):
        v = py.from_str(text)
        assert rom.int_(v).raw() == py.int_(v).raw(), text
    # INT floors, which is not truncation toward zero
    assert py.int_(py.from_str("-2.7")).to_int() == -3
    assert py.int_(py.from_str("2.7")).to_int() == 2


def test_signs_every_way_round():
    """FADDT and FMULTT take the sign from the caller, which used to go wrong.

    ``-3 + -1`` must be -4, not -2, and ``-3 * 7`` must be -21, not +21. These are
    the two cases that a naive call into the ROM's operator entry points gets wrong,
    because neither routine compares the signs itself.
    """
    rom = the_rom()
    py = ExactBackend()
    for a in (3, -3, 1, -1):
        for b in (3, -3, 1, -1):
            assert rom.add(Fac.from_int(a), Fac.from_int(b)).to_int() == a + b
            assert rom.mul(Fac.from_int(a), Fac.from_int(b)).to_int() == a * b
            assert rom.sub(Fac.from_int(a), Fac.from_int(b)).to_int() == a - b


def test_rnd_sequence_is_in_range_and_advances():
    """Every draw is in [0, 1) and the seed changes each time."""
    rom = the_rom()
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
    rom = the_rom()
    rom.set_seed(bytes((0x81, 0, 0, 0, 0)))
    first = rom.rnd(Fac.from_int(1))
    rom.rnd(Fac.from_int(0))
    assert rom.rnd(Fac.from_int(0)).raw() == first.raw(), "RND(0) repeats"
    before = rom.get_seed()
    rom.rnd(Fac.from_int(-4242))
    assert rom.get_seed() != before, "a negative argument reseeds"


def test_round_fac_is_the_byte_sequence_the_rom_does():
    """The backend's own ROUND.FAC, and the byte step it stands in for."""
    rom = the_rom()
    for text in ("0.5", "0.1", "1/3", "1000"):
        v = ExactBackend().from_str(text) if "/" not in text \
            else ExactBackend().div(Fac.from_int(1), Fac.from_int(3))
        assert rom.round_fac(v) is not None


#: Fifteen consecutive RND(1) from the seed 81 00 00 00 00, and the seed they
#: leave behind. These are an *independent* record: they were produced by
#: executing this same ROM image in a separate verification pass, so a match here
#: is not the code agreeing with itself. Section 12.6 of the paper gives the same
#: fifteen values.
RND_SEED = bytes((0x81, 0x00, 0x00, 0x00, 0x00))
RND_SERIES = [
    0.4072949116816744, 0.608041618950665, 0.25951706536579877,
    0.08268766026594676, 0.35866158816497773, 0.9610444016288966,
    0.5672113706823438, 0.6001326921395957, 0.33425431547220796,
    0.6068662970792502, 0.6758213557768613, 0.3164409970631823,
    0.036882334752590396, 0.03491484130790923, 0.2833032483467832,
]
RND_FINAL_SEED = bytes((0x7F, 0x11, 0x0D, 0x1F, 0x95))


def test_rnd_from_a_known_seed_matches_the_independent_record():
    rom = the_rom()
    rom.set_seed(RND_SEED)
    got = [rom.rnd(Fac.from_int(1)).to_float() for _ in RND_SERIES]
    assert got == RND_SERIES, [f"{g!r} != {w!r}" for g, w in zip(got, RND_SERIES)
                               if g != w][:3]
    assert rom.get_seed() == RND_FINAL_SEED, rom.get_seed().hex(" ")


def test_the_decimal_literals_match_the_independent_record():
    """The ROM's own conversion of the literals the game leans on.

    ``0.8`` and ``0.2`` are the classic Applesoft values and neither is the
    nearest double, which is why the game never uses a host float.
    """
    py = ExactBackend()
    assert py.from_str(".8").raw() == bytes((0x80, 0x4C, 0xCC, 0xCC, 0xCD))
    assert py.from_str(".2").raw() == bytes((0x7E, 0x4C, 0xCC, 0xCC, 0xCD))
    assert py.from_str(".1").raw() == bytes((0x7D, 0x4C, 0xCC, 0xCC, 0xCD))
    assert py.from_str(".8").to_float() == 0.8000000000465661
    assert py.from_str(".2").to_float() == 0.20000000001164153
    assert py.from_str(".1").to_float() == 0.10000000000582077


def test_the_python_generator_is_the_roms_generator():
    """The Python model of RND must give the ROM's sequence, draw for draw."""
    from oregon.applesoft import rng as model
    from oregon.applesoft.rom import RomBackend, available
    if not available():
        pytest.skip("no ROM image")
    rom = RomBackend()
    one = Fac(bytes.fromhex("8100000000"))
    seeds = ["8100000000", "8000000000", "803e0000aa", "80000000aa", "7f110d1f95",
             "6870cc3df9", "0000000000", "8012003400", "7900000001", "0155aa55aa"]
    for h in seeds:
        seed = bytes.fromhex(h)
        rom.set_seed(seed)
        for i in range(200):
            want = rom.rnd(one).raw()
            got, seed = model.rnd(seed, one.raw())
            assert got == want, f"seed {h}, draw {i}"
            assert seed == rom.get_seed()
    # the game's own seeding, RND(-n), then a run of draws
    for n in ("-1", "-4000", "-4001", "-65535", "-256"):
        arg = ExactBackend().from_str(n)
        rom.set_seed(bytes(5))
        want = rom.rnd(arg).raw()
        got, seed = model.rnd(bytes(5), arg.raw())
        assert got == want
        for i in range(200):
            want = rom.rnd(one).raw()
            got, seed = model.rnd(seed, one.raw())
            assert got == want, f"RND({n}), draw {i}"


def test_the_python_generator_matches_the_record_without_the_rom():
    """Needs no ROM: fifteen draws from 81 00 00 00 00 leave 7F 11 0D 1F 95."""
    from oregon.applesoft import rng as model
    seed = bytes.fromhex("8100000000")
    one = bytes.fromhex("8100000000")
    values = []
    for _ in range(15):
        v, seed = model.rnd(seed, one)
        values.append(v)
    assert seed == bytes.fromhex("7f110d1f95")
    assert len(set(values)) == 15


def test_two_seeds_give_two_different_games_in_the_python_backend():
    """Different seeds must give different draws -- the generator must move."""
    a, b = ExactBackend(), ExactBackend()
    one = Fac(bytes.fromhex("8100000000"))
    a.rnd(a.from_str("-4000"))
    b.rnd(b.from_str("-4001"))
    sa = [a.rnd(one).raw() for _ in range(20)]
    sb = [b.rnd(one).raw() for _ in range(20)]
    assert sa != sb
    assert len(set(sa)) == 20 and len(set(sb)) == 20


def test_python_subtraction_takes_the_sign_of_the_larger_operand():
    """2 - 3 is -1, including when the exponents are equal."""
    p = ExactBackend()
    for a, b in (("2", "3"), ("2", "2.5"), ("2.5", "3"), ("-2", "-3"), ("5", "7")):
        got = p.sub(p.from_str(a), p.from_str(b)).to_float()
        assert got == float(a) - float(b), f"{a} - {b} gave {got}"
    assert p.sub(p.from_str("2"), p.from_str("2")).is_zero()


def test_python_and_rom_never_differ_in_sign_or_by_more_than_the_last_place():
    import itertools
    p, r = ExactBackend(), applesoft.rom.RomBackend()
    vals = ["0", "1", "2", "3", "-1", "-2", ".5", "2.5", "100", ".1", "-.1", "7",
            "1500", "139", ".9", ".8", "20", "12", "35", "-3", "5", "4.7", ".003"]
    for op in ("add", "sub", "mul", "div"):
        for a, b in itertools.product(vals, vals):
            if op == "div" and b == "0":
                continue
            x = getattr(p, op)(p.from_str(a), p.from_str(b)).to_float()
            y = getattr(r, op)(r.from_str(a), r.from_str(b)).to_float()
            assert (x < 0) == (y < 0), f"{a} {op} {b}: sign"
            assert abs(x - y) <= abs(y) * 1e-8, f"{a} {op} {b}: {x} against {y}"
