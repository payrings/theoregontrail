"""Compare the Python transcription of the ROM's arithmetic with the emulated ROM.

This repeats the comparisons reported in paper section 12.6:

    python tools/exact_check.py            # 20,000 operand pairs, literals, FOUT
    python tools/exact_check.py 2000       # a quicker run

1. Operations. Random pairs of values, a quarter of whose bytes are zero and half
   of which carry an extension byte (as a right operand can), through every
   operation of the interface: ``add``, ``sub``, ``mul``, ``div``, the constant
   forms of ``mul`` and ``div``, ``cmp``, ``INT`` and ``ROUND.FAC``. The results
   are compared byte for byte, extension byte included, and so are the error
   numbers.
2. Literals. Every constant written as a decimal literal in the game's code,
   with 4,000 random literals, converted by ``FIN``.
3. Number to text. Random values, with and without an extension byte, through
   ``FOUT``.

Every count of differences should be zero. It needs the ROM image and py65.
"""
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from oregon.applesoft.exact import ExactBackend  # noqa: E402
from oregon.applesoft.fac import Fac  # noqa: E402
from oregon.applesoft.rom import RomBackend, RomError  # noqa: E402

rom, exact = RomBackend(), ExactBackend()


def operations(n, seed=13):
    rng = random.Random(seed)

    def byte():
        return 0 if rng.random() < 0.25 else (
            255 if rng.random() < 0.05 else rng.randrange(256))

    def val():
        k = rng.randrange(5)
        if k == 0:
            v = Fac.from_int(rng.randrange(-3000, 3000))
        elif k == 1:
            e = (rng.choice([0, rng.randrange(1, 256)]) if rng.random() < .02
                 else rng.randrange(0x60, 0xA8))
            v = Fac(bytes([e, byte(), byte(), byte(), byte()]))
        else:
            v = Fac(bytes([rng.randrange(0x70, 0x98), byte(), byte(), byte(), byte()]))
        if v.b[0] == 0:
            v = Fac(bytes(5))
        if rng.random() < 0.5 and not v.is_zero():
            v = Fac(v.b, rng.choice([0x80, 0x7F, 0xFF, rng.randrange(256)]))
        return v

    def run(b, f):
        try:
            x = f(b)
            return (x.b.hex(), x.ext) if isinstance(x, Fac) else x
        except RomError as ex:
            return ("error", ex.code)

    ops = {
        "add": lambda b, x, y: b.add(x, y), "sub": lambda b, x, y: b.sub(x, y),
        "mul": lambda b, x, y: b.mul(x, y), "div": lambda b, x, y: b.div(x, y),
        "mul_const": lambda b, x, y: b.mul_const(x, y),
        "div_const": lambda b, x, y: b.div_const(x, y),
        "cmp": lambda b, x, y: b.cmp(x, y), "int": lambda b, x, y: b.int_(x),
        "round": lambda b, x, y: b.round_fac(x),
    }
    bad = {k: 0 for k in ops}
    for _ in range(n):
        x, y = val(), val()
        for k, f in ops.items():
            if run(rom, lambda b: f(b, x, y)) != run(exact, lambda b: f(b, x, y)):
                bad[k] += 1
                if bad[k] <= 3:
                    print(f"  {k}: {x!r} {y!r}")
    print(f"operations: {n:,} pairs, differences {bad}")


def literals(seed=5):
    found = set()
    for f in (ROOT / "oregon").rglob("*.py"):
        found |= set(re.findall(r'parse\("([-+]?[0-9.]+(?:E[-+]?\d+)?)"\)', f.read_text()))
    rng = random.Random(seed)
    lits = set(found)
    for _ in range(4000):
        k = rng.randrange(4)
        if k == 0:
            s = str(rng.randrange(0, 100000))
        elif k == 1:
            s = "." + str(rng.randrange(1, 10 ** rng.randrange(1, 9))).zfill(rng.randrange(1, 9))
        elif k == 2:
            s = f"{rng.randrange(0, 1000)}.{rng.randrange(0, 10 ** rng.randrange(1, 6))}"
        else:
            s = f"{rng.randrange(1, 10)}E{rng.choice(['', '-'])}{rng.randrange(0, 37)}"
        lits.add(s)
    bad = 0
    for s in sorted(lits):
        r, e = rom.from_str(s), exact.from_str(s)
        if (r.b, r.ext) != (e.b, e.ext):
            bad += 1
            print(f"  {s}: {r!r} {e!r}")
    print(f"literals: {len(lits):,} ({len(found)} from the game's code), differences {bad}")


def number_to_text(n, seed=2):
    rng = random.Random(seed)

    def byte():
        return 0 if rng.random() < .25 else rng.randrange(256)

    bad = 0
    for _ in range(n):
        k = rng.randrange(4)
        if k == 0:
            v = Fac.from_int(rng.randrange(-100000, 100000))
        elif k == 1:
            v = rom.round_fac(rom.from_str(f"{rng.randrange(0, 2000)}.{rng.randrange(0, 100)}"))
        else:
            v = Fac(bytes([rng.randrange(0x01, 0x100), byte(), byte(), byte(), byte()]))
        if v.b[0] == 0:
            v = Fac(bytes(5))
        if not v.is_zero() and rng.random() < .3:
            v = Fac(v.b, rng.randrange(256))
        out = []
        for b in (rom, exact):
            try:
                out.append(b.fmt(v))
            except RomError as ex:
                out.append(("error", ex.code))
        if out[0] != out[1]:
            bad += 1
            if bad <= 5:
                print(f"  {v!r}: {out[0]} {out[1]}")
    print(f"number to text: {n:,} values, differences {bad}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    operations(n)
    literals()
    number_to_text(n)
