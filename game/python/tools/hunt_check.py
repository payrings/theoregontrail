"""Run the hunting module of The Oregon Trail (release 1.4) under py65 and check
the claims of section 11.1 of the paper against it.

The module's bytes are not shipped in the public repository. They are read from
the private Appendix Z (Part 2, the lines of hex that start with an address, from
$D000 to $FEFF):

    python tools/hunt_check.py "../../paper/Appendix Z (private) Machine-code listings.txt"

What is run: the entry at $E003 ("& HUNT"), exactly as the BASIC command calls
it, with the argument block at $8A3F. The Apple II hardware is stubbed:
$C000 (keyboard), $C010 (strobe), $C030 (speaker). The screen is ordinary RAM.
Nothing about the pictures is checked, only the logic.

What is checked (each prints one line):
  1. a hunt with no key pressed ends after 2,500 passes
  2. the terrain objects placed are 4 to 7
  3. the terrain table (E04A) and the animal records (E068)
  4. the spawn chance per attempt, halved and not halved
  5. the animal types drawn (types 3, 4 and 5 always; 0, 1 and 2 by the flags)
  6. once four animals are shot no animal appears
  7. the space bar fires and takes one bullet
  8. the Applesoft seed bytes ($C9 to $CD) are read but never written
  9. the same seed and keyboard counter give the same hunt
"""
import collections
import random
import re
import sys

from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory


def load_module(path):
    """Read the hex bytes of Part 2 ($D000-$FEFF) from the listing."""
    text = open(path, encoding="latin-1").read().split("\n")
    start = next(i for i, ln in enumerate(text) if ln.startswith("PART 2 - THE HUNTING MODULE"))
    end = next(i for i, ln in enumerate(text) if ln.startswith("PART 3 - "))
    rx = re.compile(r"^([0-9A-F]{4}): ((?:[0-9A-F]{2} )+)")
    mem = {}
    for ln in text[start:end]:
        m = rx.match(ln)
        if m:
            a = int(m.group(1), 16)
            for i, t in enumerate(m.group(2).split()):
                mem[a + i] = int(t, 16)
    if min(mem) != 0xD000 or max(mem) != 0xFEFF or len(mem) != 0xFF00 - 0xD000:
        raise SystemExit("the listing does not hold the whole of $D000-$FEFF")
    return mem


BLOCK = 0x8A3F      # argument block: bullets (2 bytes), 3 flags, halve flag, zone
SENTINEL = 0x0300   # where the module returns to


class Hunt:
    def __init__(self, module, seed=(1, 2, 3, 4, 5), counter=0x1234, bullets=50,
                 flags=(1, 1, 1), half=1, zone=0):
        ram = [0] * 65536
        for k, v in module.items():
            ram[k] = v
        self.ram = ram
        self.mem = ObservableMemory(ram)
        self.key = None
        self.mem.subscribe_to_read([0xC000], lambda a: (self.key | 0x80) if self.key is not None else 0)
        self.mem.subscribe_to_read([0xC010], self._strobe)
        self.mem.subscribe_to_write([0xC010], lambda a, v: self._strobe(a))
        self.mpu = MPU(self.mem)
        for i, v in enumerate(seed):
            ram[0xC9 + i] = v
        ram[0x4E], ram[0x4F] = counter & 255, counter >> 8
        ram[0xE6] = 0x20                       # Applesoft's high-resolution page
        for i, v in enumerate([bullets & 255, bullets >> 8, *flags, half, zone]):
            ram[BLOCK + i] = v
        self.passes = 0

    def _strobe(self, a):
        self.key = None
        return 0

    def run(self, max_passes=None, hooks=None, keys=None, max_steps=80_000_000):
        m = self.mpu
        hooks, keys = hooks or {}, keys or {}
        ret = SENTINEL - 1                     # as if by JSR $E003
        m.sp = 0xFD
        self.ram[0x100 + m.sp] = ret >> 8
        m.sp -= 1
        self.ram[0x100 + m.sp] = ret & 255
        m.sp -= 1
        m.a, m.y, m.x, m.pc = BLOCK & 255, BLOCK >> 8, 0, 0xE003
        steps = 0
        while m.pc != SENTINEL and steps < max_steps:
            if m.pc in hooks:
                hooks[m.pc](self)
            if m.pc == 0xE0A1:                 # top of the main loop
                if max_passes and self.passes >= max_passes:
                    break
                self.passes += 1
                if self.passes in keys:
                    self.key = keys[self.passes]
            m.step()
            steps += 1
            if m.pc < 0xD000 and m.pc != SENTINEL:
                raise RuntimeError("left the module at $%04X" % m.pc)
        return m.pc == SENTINEL

    def word(self, a):
        return self.ram[a] | (self.ram[a + 1] << 8)


def rng_args(s):
    r = random.Random(s)
    return dict(seed=[r.randrange(256) for _ in range(5)], counter=r.randrange(65536))


def main(path):
    mod = load_module(path)

    h = Hunt(mod)
    done = h.run()
    print("1. no key: finished=%s, passes=%d" % (done, h.passes))

    counts = collections.Counter()
    for s in range(120):
        h = Hunt(mod, zone=s % 5, **rng_args(s))
        n = [0]
        h.run(max_passes=1, hooks={0xE350: lambda hh: n.__setitem__(0, n[0] + 1)})
        counts[n[0]] += 1
    print("2. terrain objects per hunt (120 hunts):", dict(sorted(counts.items())))

    print("3. terrain table E04A, zone: entries")
    for z in range(5):
        print("     ", z, [mod[0xE04A + z * 6 + i] for i in range(6)])
    for t in range(6):
        r = [mod[0xE068 + t * 8 + i] for i in range(8)]
        base, rng = r[2] | r[3] << 8, r[4] | r[5] << 8
        print("      animal type %d: weight shot %d to %d" % (t, base, base + rng))

    for half in (1, 0):
        att = sp = 0
        for s in range(12):
            h = Hunt(mod, flags=(0, 0, 0), half=half, **rng_args(s))
            c = collections.Counter()
            h.run(max_passes=600, hooks={0xE12F: lambda hh: c.update(a=1), 0xE159: lambda hh: c.update(s=1)})
            att, sp = att + c["a"], sp + c["s"]
        print("4. halve flag %d: %d spawns in %d attempts = %.4f per attempt" % (half, sp, att, sp / att))

    types = collections.Counter()
    for s in range(12):
        h = Hunt(mod, flags=(1, 1, 1), half=0, zone=2, **rng_args(s))
        h.run(max_passes=600, hooks={0xE16B: lambda hh: types.update([hh.mpu.a])})
    print("5. animal types drawn, all three flags on:", dict(sorted(types.items())))

    sp = att = 0
    for s in range(6):
        h = Hunt(mod, half=0, zone=2, **rng_args(s))
        c = collections.Counter()
        h.run(max_passes=500, hooks={0xE0A1: lambda hh: hh.ram.__setitem__(0xEDD5, 4) if hh.passes == 2 else None,
                                     0xE12F: lambda hh: c.update(a=1), 0xE159: lambda hh: c.update(s=1)})
        att, sp = att + c["a"], sp + c["s"]
    print("6. four animals already shot: %d attempts, %d spawns" % (att, sp))

    for key, name in ((0xA0, "space"), (0x8D, "return")):
        h = Hunt(mod, bullets=50)
        h.run(max_passes=40, keys={10: key})
        print("7. %s pressed once: bullets 50 -> %d" % (name, h.word(0xEDCC)))

    h = Hunt(mod, seed=(11, 22, 33, 44, 55), counter=777)
    h.run()
    print("8. Applesoft seed bytes after a full hunt:", [h.ram[i] for i in range(0xC9, 0xCE)],
          "(started as [11, 22, 33, 44, 55])")

    a, b, c = (Hunt(mod, seed=(1, 2, 3, 4, 5), counter=n) for n in (100, 100, 101))
    steps = []
    for x in (a, b, c):
        n = [0]
        x.run(max_passes=300, hooks={0xE0A1: lambda hh, n=n: n.__setitem__(0, n[0] + 1)})
        steps.append(tuple(x.ram[0xEDE8:0xEDEA]) + (x.word(0xEDD4),))
    print("9. same inputs same state: %s; counter +1 differs: %s" % (steps[0] == steps[1], steps[0] != steps[2]))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
