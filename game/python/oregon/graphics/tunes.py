"""Made-up tunes, one for each tune file the original loads, each as long as the original's.

The original loads a tune file on reaching each landmark (``MS1`` to ``MS16``), ``MS0`` at the
start, ``MS17`` for Oregon and ``TS`` for the tombstone, and plays it through while it waits for a
key. The lengths below were worked out from those files (the notes in each, and the player's
timing in the machine code); the notes here are not theirs: each tune is composed by a small
program from a seed, a key and a scale, so it is new, mellow and the right length.

Form: two-bar phrases of sixteen steps (A, B, A, C ...), a soft held bass note under each bar,
the last phrase coming to rest on the tonic. ``MS0`` keeps the opening lullaby that was already
chosen as its first phrase.
"""

from __future__ import annotations

import random

__all__ = ["STEP", "SECONDS", "melody_and_bass", "names"]

STEP = 0.17                      # seconds in one step

#: how long each original tune plays (seconds), from its tune file
SECONDS = {
    "ms0": 16.4, "ms1": 16.3, "ms2": 37.3, "ms3": 25.9, "ms4": 22.1, "ms5": 16.6, "ms6": 33.2,
    "ms7": 24.8, "ms8": 16.6, "ms9": 29.5, "ms10": 12.4, "ms11": 8.3, "ms12": 20.7, "ms13": 12.4,
    "ms14": 29.5, "ms15": 27.2, "ms16": 16.5, "ms17": 16.6, "ts": 18.7,
}

MAJOR = [0, 2, 4, 7, 9]
MINOR = [0, 3, 5, 7, 10]
SUS = [0, 2, 5, 7, 9]            # an open, hymn-like colour

#: key (semitones from A4 of the tonic), scale, seed: a different mood for each place
SETTINGS = {
    "ms0": (-9, MAJOR, 11),  "ms1": (-7, MAJOR, 12),  "ms2": (-4, SUS, 13),   "ms3": (-2, MAJOR, 14),
    "ms4": (-5, MINOR, 15),  "ms5": (-9, SUS, 16),    "ms6": (-7, MINOR, 17), "ms7": (0, MAJOR, 18),
    "ms8": (-4, MAJOR, 19),  "ms9": (-2, SUS, 20),    "ms10": (-9, MINOR, 21), "ms11": (-5, MAJOR, 22),
    "ms12": (-7, SUS, 23),   "ms13": (-2, MINOR, 24), "ms14": (-4, SUS, 25),  "ms15": (-9, MAJOR, 26),
    "ms16": (-5, SUS, 27),   "ms17": (-9, MAJOR, 28), "ts": (-12, MINOR, 29),
}

BARS = [[2, 1, 1, 2, 2], [1, 1, 2, 2, 2], [2, 2, 1, 1, 2], [3, 1, 2, 2], [2, 2, 2, 2],
        [1, 1, 1, 1, 2, 2], [4, 2, 2], [2, 1, 1, 4], [3, 1, 4], [2, 2, 4]]
SLOW_BARS = [[4, 4], [2, 2, 4], [3, 1, 4], [2, 2, 2, 2], [4, 2, 2]]


def names():
    return list(SECONDS)


def _degree_to_semis(root, scale, degree):
    return root + 12 * (degree // 5) + scale[degree % 5]


def _phrase(rng, slow, end_degree, start=None):
    """Sixteen steps as (degree or None, steps): two bars that wander by step and settle."""
    bank = SLOW_BARS if slow else BARS
    out = []
    d = start if start is not None else rng.choice([0, 2, 4])
    for bar in range(2):
        rhythm = rng.choice(bank)
        for i, length in enumerate(rhythm):
            last = bar == 1 and i == len(rhythm) - 1
            if last:
                d = end_degree
            else:
                d += rng.choice([-2, -1, -1, 0, 1, 1, 2])
                d = max(0, min(7, d))
            if rng.random() < 0.06 and not last and i > 0:
                out.append((None, length))
            else:
                out.append((d, length))
    return out


def _vary(rng, phrase, end_degree):
    """The same phrase with its last few notes remade."""
    keep = len(phrase) - 3
    head = phrase[:keep]
    d = next((x for x, _ in reversed(head) if x is not None), 0)
    tail = []
    for i, (_, length) in enumerate(phrase[keep:]):
        if i == len(phrase) - keep - 1:
            d = end_degree
        else:
            d = max(0, min(7, d + rng.choice([-2, -1, 1, 2])))
        tail.append((d, length))
    return head + tail


def melody_and_bass(name: str):
    """``(melody, bass)``: each a list of (semitones from A4 or None, steps)."""
    root, scale, seed = SETTINGS[name]
    rng = random.Random(seed)
    total = round(SECONDS[name] / STEP)
    slow = name == "ts"
    phrases_n = max(1, total // 16)
    extra = total - 16 * phrases_n
    a = _phrase(rng, slow, 2)
    if name == "ms0":                                   # the lullaby chosen at the start, in this key
        a = [(0, 1), (2, 1), (3, 1), (2, 1), (4, 2), (3, 2), (2, 1), (1, 1), (0, 3), (None, 1)]
    b = _phrase(rng, slow, 4)
    c = _phrase(rng, slow, 3, start=4)
    pool = {"A": a, "B": b, "C": c}
    form = ["A", "B", "A", "C"]
    seq = []
    for i in range(phrases_n):
        key = form[i % 4]
        ph = pool[key]
        if i >= 4:
            ph = _vary(rng, ph, {"A": 2, "B": 4, "C": 3}[key])
        seq.append(ph)
    # the last phrase comes home: its last note becomes the tonic, held through the spare steps
    last = list(seq[-1])
    while last and last[-1][0] is None:
        last.pop()
    d, length = last[-1]
    last[-1] = (0, length + extra + (16 - sum(s for _, s in last) if sum(s for _, s in last) < 16 else 0))
    seq[-1] = last
    melody = []
    for ph in seq:
        melody += [(None if d is None else _degree_to_semis(root, scale, d), n) for d, n in ph]
    # pad or trim exactly to the target
    have = sum(n for _, n in melody)
    if have < total:
        s, n = melody[-1]
        melody[-1] = (s, n + total - have)
    bass = []
    bars = total // 8
    for i in range(bars):
        deg = 0 if i % 4 in (0, 3) else (4 if i % 4 == 1 else 3)
        bass.append((_degree_to_semis(root, scale, deg) - 12, 8))
    if total - 8 * bars:
        bass.append((root - 12, total - 8 * bars))
    return melody, bass
