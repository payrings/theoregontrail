#!/usr/bin/env python3
"""Print the main figures of a run of ``compare_csv.py``.

    python summarise_csv.py results              # one backend's folder
    python summarise_csv.py results/exact results/float results/rounded

Each folder holds the ``games.csv`` and ``pairs.csv`` that ``compare_csv.py``
wrote for the ROM against one other backend. Seeds are counted once per
distinct game: two seeds are one game when every recorded value of both games
and the whole ``pairs.csv`` row (apart from the seed) are the same.
The paper's tables in section 12.7 count 62,883 seeds (all seeds except the
2,653 first-call doubles), while this script's headline figures count distinct
games. The figures are printed for the distinct games and, in brackets, for
all the seeds in the folder.
"""

from __future__ import annotations

import csv
import math
import statistics
import sys
from pathlib import Path


def load(folder: Path):
    games, pairs = {}, {}
    with open(folder / "games.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            games.setdefault(int(r["seed"]), {})[r["backend"]] = r
    with open(folder / "pairs.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            pairs[int(r["seed"])] = r
    seeds = sorted(s for s in pairs if s in games and len(games[s]) == 2)
    others = {b for s in seeds for b in games[s] if b != "rom"}
    if len(others) != 1:
        raise SystemExit(f"{folder}: expected the ROM and one other backend, found {others}")
    return games, pairs, seeds, others.pop()


def distinct(games, pairs, seeds, other):
    seen, out = set(), []
    for s in seeds:
        rec = tuple(tuple(v for k, v in games[s][b].items() if k not in ("seed", "backend"))
                    for b in ("rom", other))
        row = tuple(v for k, v in pairs[s].items() if k != "seed")
        if (rec, row) not in seen:
            seen.add((rec, row))
            out.append(s)
    return out


def figures(games, pairs, seeds, other):
    n = len(seeds)
    rom = [games[s]["rom"] for s in seeds]
    oth = [games[s][other] for s in seeds]
    arr_r = sum(r["ending"] == "ARRIVED" for r in rom)
    arr_o = sum(r["ending"] == "ARRIVED" for r in oth)
    r_only = sum(a["ending"] == "ARRIVED" and b["ending"] != "ARRIVED" for a, b in zip(rom, oth))
    o_only = sum(b["ending"] == "ARRIVED" and a["ending"] != "ARRIVED" for a, b in zip(rom, oth))
    ident = sum(pairs[s]["trace_identical"] == "1" for s in seeds)
    same_end = sum(pairs[s]["same_ending"] == "1" for s in seeds)
    same_score = sum(a["score"] == b["score"] for a, b in zip(rom, oth))
    errors = sum(r["ending"] in ("ERROR", "TIMEOUT") for r in rom + oth)
    first = [int(pairs[s]["first_diff_day"]) for s in seeds if pairs[s]["first_diff_day"]]

    def mean(xs):
        xs = [float(x) for x in xs if x not in ("", None)]
        return statistics.mean(xs) if xs else float("nan")

    z = p = float("nan")
    if r_only + o_only:
        z = (o_only - r_only) / math.sqrt(r_only + o_only)
        p = math.erfc(abs(z) / math.sqrt(2))
    return {
        "games": n,
        "errors or timeouts": errors,
        "identical every day": ident,
        "differ somewhere": n - ident,
        "same ending": same_end,
        "different ending": n - same_end,
        "same score": same_score,
        "arrived (rom)": arr_r,
        f"arrived ({other})": arr_o,
        "arrived under rom only": r_only,
        f"arrived under {other} only": o_only,
        "McNemar z, p": (z, p),
        "mean days (rom)": mean(r["days"] for r in rom),
        f"mean days ({other})": mean(r["days"] for r in oth),
        "mean score of arrivals (rom)": mean(r["score"] for r in rom if r["ending"] == "ARRIVED"),
        f"mean score of arrivals ({other})": mean(r["score"] for r in oth if r["ending"] == "ARRIVED"),
        "median first differing day": str(statistics.median(first)) if first else "-",
    }


def show(value, n):
    if isinstance(value, tuple):
        return ", ".join("-" if math.isnan(v) else f"{v:.3f}" for v in value)
    if isinstance(value, float):
        return "-" if math.isnan(value) else f"{value:.2f}"
    if isinstance(value, int) and n:
        return f"{value:,} ({100 * value / n:.2f}%)"
    return str(value)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return
    for folder in map(Path, argv[1:]):
        games, pairs, seeds, other = load(folder)
        dist = distinct(games, pairs, seeds, other)
        f_d = figures(games, pairs, dist, other)
        f_a = figures(games, pairs, seeds, other)
        print(f"\n{folder}: ROM against {other}; {len(seeds):,} seeds, "
              f"{len(dist):,} distinct games")
        for k in f_d:
            nd, na = f_d["games"], f_a["games"]
            whole = k == "games"
            print(f"  {k:<34} {show(f_d[k], 0 if whole else nd):>22}"
                  f"   [{show(f_a[k], 0 if whole else na)}]")


if __name__ == "__main__":
    main(sys.argv)
