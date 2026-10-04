"""Compare the pure-Python backend with the emulated ROM, operand by operand."""
import random
import sys

sys.path.insert(0, "/home/xfx/oregon")
from oregon.applesoft.fac import Fac
from oregon.applesoft.pure import PureBackend
from oregon.applesoft.rom import RomBackend, RomError

rom = RomBackend()
pure = PureBackend()


def rnd_value(rng):
    kind = rng.randrange(6)
    if kind == 0:
        return Fac.from_int(rng.randrange(-2000, 2000))
    if kind == 1:
        return Fac.from_int(rng.randrange(0, 10))
    if kind == 2:
        return pure.from_str(f"{rng.randrange(0, 100)}.{rng.randrange(0, 999999)}")
    if kind == 3:
        return pure.from_str(f".{rng.randrange(1, 999999)}")
    if kind == 4:
        return pure.from_str(f"{rng.randrange(0, 3)}.{rng.randrange(0, 1000):03d}")
    # A normalised value: Applesoft never stores one with the significand's top
    # bit clear, and both backends assume that, so the corpus must not contain
    # any.
    while True:
        e = rng.randrange(1, 240)
        s = rng.randrange(0, 256)
        m = rng.randrange(0, 1 << 24)
        word = 0x80000000 | (s << 24) | m
        return Fac(bytes((e, (0x80 if rng.randrange(2) else 0x00) | ((word >> 24) & 0x7F),
                          (word >> 16) & 0xFF, (word >> 8) & 0xFF, word & 0xFF)))


def main(n=4000, seed=20261005):
    rng = random.Random(seed)
    ops = [("add", rom.add, pure.add), ("sub", rom.sub, pure.sub),
           ("mul", rom.mul, pure.mul)]
    bad = {k: 0 for k, _, _ in ops}
    bad["div"] = bad["int"] = 0
    examples = []
    for i in range(n):
        a, b = rnd_value(rng), rnd_value(rng)
        if b.is_zero():
            continue
        for name, ro, pu in ops + [("div", rom.div, pure.div)]:
            try:
                r1 = ro(a, b)
            except RomError:
                continue
            r2 = pu(a, b)
            if r1.raw() != r2.raw():
                bad[name] += 1
                if len(examples) < 12:
                    examples.append((name, " ".join(f"{x:02X}" for x in a.raw()),
                                     " ".join(f"{x:02X}" for x in b.raw()),
                                     " ".join(f"{x:02X}" for x in r1.raw()),
                                     " ".join(f"{x:02X}" for x in r2.raw())))
        i1, i2 = rom.int_(a), pure.int_(a)
        if i1.raw() != i2.raw():
            bad["int"] += 1
            if len(examples) < 12:
                examples.append(("int", " ".join(f"{x:02X}" for x in a.raw()), "",
                                 " ".join(f"{x:02X}" for x in i1.raw()),
                                 " ".join(f"{x:02X}" for x in i2.raw())))
    print(f"{n} random pairs")
    print("mismatches:", bad)
    for e in examples:
        print(f"  {e[0]:>4}  a={e[1]}  b={e[2]}  rom={e[3]}  pure={e[4]}")
    print("ROM calls:", rom.calls)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4000)
