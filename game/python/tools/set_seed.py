#!/usr/bin/env python3
"""Change the seed in an instrumented Oregon Trail image.

The instrumented MENU (its new line 9100) reseeds the game with a literal:

    Z=RND(-10190):Z=RND(1):Z=RND(1)

The number is stored in the program area as text, the way every number in these
programs is, so the seed can be changed by replacing those digits. The digits
keep their length, which keeps the program's place in the disk image and the
image's own size, so nothing else in the file has to move.

    python3 set_seed.py IMAGE.dsk OLD NEW

NEW may be shorter than OLD, in which case it is padded with leading zeros:
"1234" becomes "01234", which the interpreter reads as 1234.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_tunes import Disk, file_bytes, TRACKS, SECTORS, DOS_ORDER  # noqa: E402


def chain(disk, tl, sl):
    """The file's sectors, in the order they are read."""
    out = []
    walked = set()
    while tl and (tl, sl) not in walked and tl < TRACKS:
        walked.add((tl, sl))
        lst = disk.sector(tl, sl)
        for k in range(12, 256, 2):
            t, s = lst[k], lst[k + 1]
            if t == 0 and s == 0:
                out.append(None)                     # a hole: 256 zero bytes
            elif t < TRACKS and s < SECTORS:
                out.append((t, s))
        tl, sl = lst[1], lst[2]
    return out


def physical(disk, t, s):
    """The byte offset in the image of a logical sector."""
    order = disk.order
    phys = order[s] if order is DOS_ORDER else order.index(s)
    return (t * SECTORS + phys) * 256


def main(image, old, new):
    old, new = str(old), str(new)
    if len(new) > len(old):
        raise SystemExit(f"{new!r} does not fit in {old!r}")
    new = new.rjust(len(old), "0")

    raw = bytearray(open(image, "rb").read())
    disk = Disk(bytes(raw))
    for name, ftype, tl, sl, length in disk.catalogue():
        if name.upper() != "MENU":
            continue
        body, _ = file_bytes(disk, ftype, tl, sl)
        # the seed sits just after RND ( - , that is 0xDB 0x28 0xC9
        mark = bytes([0xDB, 0x28, 0xC9])
        at = body.find(mark + old.encode())
        if at < 0:
            raise SystemExit(f"the seed {old!r} is not in {name}")
        if body.find(mark + old.encode(), at + 1) >= 0:
            raise SystemExit(f"the seed {old!r} is in {name} more than once")
        patched = body[:at + 3] + new.encode() + body[at + 3 + len(old):]

        # write the sectors back where they belong: a DOS 3.3 file's sectors are
        # interleaved over the disk, so each one goes back to its own place
        sectors = chain(disk, tl, sl)
        for n, sec in enumerate(sectors):
            chunk = patched[n * 256:(n + 1) * 256]
            if len(chunk) < 256:
                break
            if sec is None:
                continue
            off = physical(disk, *sec)
            raw[off:off + 256] = chunk
        open(image, "wb").write(bytes(raw))
        print(f"{image}: the seed in {name} is now {new} (the number {int(new)})")
        return
    raise SystemExit("no MENU on that disk")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
