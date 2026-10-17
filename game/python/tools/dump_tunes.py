#!/usr/bin/env python3
"""Read an Apple DOS 3.3 disk image (.dsk) you own and list or extract its files.

    python tools/dump_tunes.py SIDE_A.dsk                 # catalogue
    python tools/dump_tunes.py SIDE_A.dsk --extract DIR   # save every file into DIR
    python tools/dump_tunes.py SIDE_A.dsk --tunes         # table of every MS*.BIN / TS.BIN tune
    python tools/dump_tunes.py SIDE_A.dsk --tunes --summary   # lengths and counts only

The disk image is your own; nothing from it is included here, and what the tune table prints
is for your private use (keep it out of anything you publish).
The note names are approximate (pitch byte 1 is taken as about D#2, each step one semitone).
"""
import argparse, os, sys

TRACKS, SECTORS, SIZE = 35, 16, 256
DOS_ORDER = list(range(16))
PO_TO_DO = [0, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 15]
TYPES = {0: "T", 1: "I", 2: "A", 4: "B", 8: "S", 16: "R", 32: "a", 64: "b"}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
UNIT = 0.00576          # seconds per duration unit, from the original's timing loop
F1 = 76.8               # Hz of pitch byte 1 (about D#2), from the sound routine's loop count and the 1.02 MHz clock


def freq(p):
    return F1 * 2 ** ((p - 1) / 12) if p else 0.0


def note_name(p):
    """Nearest equal-tempered note for a pitch byte (0 is a rest). Approximate: good to about a semitone."""
    if not p:
        return "rest"
    midi = round(69 + 12 * __import__("math").log2(freq(p) / 440))
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


class Disk:
    def __init__(self, data):
        if len(data) != TRACKS * SECTORS * SIZE:
            sys.exit("not a 140 KB DOS 3.3 image")
        self.data = data
        self.order = DOS_ORDER
        if not self._vtoc_ok():
            self.order = PO_TO_DO
            if not self._vtoc_ok():
                sys.exit("cannot find a DOS 3.3 catalogue (is this a ProDOS or copy-protected image?)")

    def sector(self, t, s):
        phys = self.order[s] if self.order is DOS_ORDER else self.order.index(s)
        o = (t * SECTORS + phys) * SIZE
        return self.data[o:o + SIZE]

    def _vtoc_ok(self):
        v = self.sector(17, 0)
        return v[3] in (2, 3) and v[0x34] == 35 and v[0x35] == 16 and 0 < v[1] < 35

    def catalogue(self):
        v = self.sector(17, 0)
        t, s = v[1], v[2]
        seen = set()
        while t and (t, s) not in seen and t < TRACKS:
            seen.add((t, s))
            sec = self.sector(t, s)
            for i in range(7):
                e = sec[11 + 35 * i: 46 + 35 * i]
                if e[0] in (0, 0xFF):
                    continue
                name = bytes(b & 0x7F for b in e[3:33]).decode("latin-1").rstrip()
                yield name, e[2] & 0x7F, e[0], e[1], e[33] | (e[34] << 8)
            t, s = sec[1], sec[2]

    def read(self, tl, sl):
        out, seen = bytearray(), set()
        while tl and (tl, sl) not in seen and tl < TRACKS:
            seen.add((tl, sl))
            lst = self.sector(tl, sl)
            for k in range(12, 256, 2):
                t, s = lst[k], lst[k + 1]
                if t == 0 and s == 0:
                    out += bytes(SIZE)
                elif t < TRACKS and s < SECTORS:
                    out += self.sector(t, s)
            tl, sl = lst[1], lst[2]
        return bytes(out)


def file_bytes(disk, ftype, tl, sl):
    raw = disk.read(tl, sl)
    if TYPES.get(ftype) == "B" and len(raw) >= 4:
        n = raw[2] | (raw[3] << 8)
        return raw[4:4 + n], (raw[0] | (raw[1] << 8))
    return raw, None


def tune_pairs(body):
    """(pitch, duration) byte pairs after the four-byte header, until a byte of 128 or more."""
    pairs, i = [], 4
    while i + 1 < len(body) and body[i] < 128:
        pairs.append((body[i], body[i + 1]))
        i += 2
    return pairs


def show_tune(name, body, summary):
    pairs = tune_pairs(body)
    total = sum(d for _, d in pairs) * UNIT
    pitches = [p for p, _ in pairs if p]
    rng = f"{min(pitches)}-{max(pitches)}" if pitches else "-"
    print(f"\n{name}: {len(pairs)} notes, about {total:.1f} s, pitch bytes {rng}")
    if summary:
        return
    print(f"  {'#':>3}  {'pitch':>5}  {'note':>5}  {'Hz':>6}  {'dur':>4}  {'secs':>6}")
    for n, (p, d) in enumerate(pairs, 1):
        print(f"  {n:>3}  {p:>5}  {note_name(p):>5}  {freq(p):>6.1f}  {d:>4}  {d * UNIT:>6.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("image"); ap.add_argument("--extract", metavar="DIR")
    ap.add_argument("--tunes", action="store_true"); ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    disk = Disk(open(a.image, "rb").read())
    files = list(disk.catalogue())
    if a.extract:
        os.makedirs(a.extract, exist_ok=True)
        for name, ft, tl, sl, _ in files:
            body, _ = file_bytes(disk, ft, tl, sl)
            open(os.path.join(a.extract, name.replace("/", "_")), "wb").write(body)
        print(f"saved {len(files)} files to {a.extract}")
    if a.tunes:
        for name, ft, tl, sl, _ in files:
            u = name.upper()
            if u.startswith(("MS", "TS")) and u.endswith(".BIN") or u in ("TS", "TS.BIN"):
                body, _ = file_bytes(disk, ft, tl, sl)
                show_tune(name, body, a.summary)
    if not (a.extract or a.tunes):
        for name, ft, _, _, ln in files:
            print(f"{TYPES.get(ft, '?')}  {ln:>4}  {name}")


if __name__ == "__main__":
    main()
