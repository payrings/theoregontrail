"""The Python transcription of the ROM's arithmetic (``--num exact``), held to the
ROM operand by operand, and the host-float backends of paper section 12.8."""
import random

import pytest

from oregon import applesoft
from oregon.applesoft.fac import Fac

needs_rom = pytest.mark.skipif(not applesoft.rom_available(), reason="needs the ROM")


def _values(rng, n):
    def byte():
        return 0 if rng.random() < 0.25 else rng.randrange(256)

    out = []
    for _ in range(n):
        k = rng.randrange(3)
        if k == 0:
            v = Fac.from_int(rng.randrange(-3000, 3000))
        else:
            v = Fac(bytes([rng.randrange(0x70, 0x98), byte(), byte(), byte(), byte()]))
        if not v.is_zero() and rng.random() < 0.4:
            v = Fac(v.b, rng.choice([0x80, 0x7F, 0xFF, rng.randrange(256)]))
        out.append(v)
    return out


def _outcome(f):
    from oregon.applesoft.rom import RomError
    try:
        r = f()
    except RomError as e:
        return ("error", e.code)
    return (r.b, r.ext) if isinstance(r, Fac) else r


@needs_rom
@pytest.mark.parametrize("op", ["add", "sub", "mul", "div", "mul_const", "div_const",
                                "cmp", "int_", "round_fac"])
def test_exact_matches_the_rom(op):
    from oregon.applesoft.exact import ExactBackend
    from oregon.applesoft.rom import RomBackend
    rom, ex = RomBackend(), ExactBackend()
    rng = random.Random(1985)
    vals = _values(rng, 800)
    for a, b in zip(vals[::2], vals[1::2]):
        if op in ("int_", "round_fac"):
            got = _outcome(lambda: getattr(ex, op)(a))
            want = _outcome(lambda: getattr(rom, op)(a))
        else:
            got = _outcome(lambda: getattr(ex, op)(a, b))
            want = _outcome(lambda: getattr(rom, op)(a, b))
        assert got == want, (op, a, b)


@needs_rom
def test_the_multiply_quirk_is_reproduced():
    """After two zero bytes in a row in the multiplier, FMULTT shifts one bit too far."""
    from oregon.applesoft.exact import ExactBackend
    from oregon.applesoft.rom import RomBackend
    a, b = Fac(bytes.fromhex("884d000000")), Fac(bytes.fromhex("8fdd0000a3"))
    want = RomBackend().mul(a, b)
    assert ExactBackend().mul(a, b).raw() == want.raw() == bytes.fromhex("97b0f90041")


@needs_rom
def test_literals_convert_as_fin_does():
    from oregon.applesoft.exact import ExactBackend
    from oregon.applesoft.rom import RomBackend
    rom, ex = RomBackend(), ExactBackend()
    for s in (".8", ".2", ".1", "1.1", "2.5", "1.25", ".9", "105", ".005", "0",
              "1848", "3.14159", "1E5", "1E-5", "12.345678"):
        r, e = rom.from_str(s), ex.from_str(s)
        assert (r.b, r.ext) == (e.b, e.ext), s


def test_one_point_one_times_twenty():
    """The exact product is 22 plus a quarter of a unit, so the correctly rounded 22 is right."""
    from oregon.applesoft.exact import ExactBackend
    ex = ExactBackend()
    eleven = ex.round_fac(ex.from_str("1.1"))
    assert ex.round_fac(ex.mul(eleven, Fac.from_int(20))).raw() == Fac.from_int(22).raw()


def test_rounding_to_applesoft_precision():
    from oregon.applesoft.hostfloat import to_fac, applesoft_round
    assert to_fac(0.8).raw() == bytes.fromhex("804ccccccd")
    assert to_fac(-1.0).raw() == bytes.fromhex("8180000000")
    assert to_fac(22.0).raw() == Fac.from_int(22).raw()
    # 1.1 held at Applesoft's precision, times 20, rounds back to 22
    assert applesoft_round(applesoft_round(1.1) * 20) == 22.0
    assert applesoft_round(1.1) * 20 != 22.0    # unless the product is rounded


def test_float_backends_play_a_game(tmp_path):
    """Both host-float backends run the game to an end."""
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for b in ("float", "rounded"):
        p = subprocess.run([sys.executable, "-m", "oregon", "--preset", "--seed", "6",
                            "--num", b, "--demo", "--data", str(tmp_path / b)],
                           cwd=root, capture_output=True, text=True, timeout=600)
        assert p.returncode == 0, p.stderr[-500:]
        assert "SUMMARY" in p.stderr


@needs_rom
def test_number_to_text_matches_fout():
    """FOUT ($ED34) transcribed: the same text as the ROM's, extension byte included."""
    from oregon.applesoft.exact import ExactBackend
    from oregon.applesoft.rom import RomBackend
    rom, ex = RomBackend(), ExactBackend()
    rng = random.Random(1848)
    vals = [v for v in _values(rng, 400)] + [rom.round_fac(rom.from_str(s)) for s in (
        "520.2", ".8", "1E9", "999999999", "1E-9", "123456789", "-0.5", "1848")]
    for v in vals:
        assert ex.fmt(v) == rom.fmt(v), v
