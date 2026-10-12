#!/usr/bin/env python3
"""Play every seed under both arithmetic backends and write the results as CSV.

For each seed the game is played twice by the demo driver from the preset start:
once with the emulated Applesoft ROM (``rom``) and once with another arithmetic:
``float`` (plain host floating point, the default), ``rounded`` (host floating point
rounded to Applesoft's precision) or ``exact`` (the transcription of the ROM's
routines), one or several (paper section 12.7). Both games use the same random sequence, so
any difference comes from the arithmetic of the game's formulas.

Two files are written to the output folder:

``games.csv``   one row per game (two per seed): how it ended, the score, the
                survivors, the health, each member's state, the supplies left.
``pairs.csv``   one row per seed: whether the two games match, the first day
                they differ, and the differences in the main results.

    python compare_csv.py                      # all 65,536 seeds, into results/
    python compare_csv.py 0 9999               # a range
    python compare_csv.py 0 65535 8            # eight worker processes
    python compare_csv.py 0 65535 8 out_dir    # another folder
    python compare_csv.py 0 1999 8 out_dir rounded # ROM against another backend
    python compare_csv.py 0 65535 8 results exact,float,rounded
                                               # several, one folder each
    python compare_csv.py 0 1999 8 out_dir float rom_cache   # keep the ROM games

``python summarise_csv.py results/exact`` prints the main figures of a run.

It can be stopped and started again: seeds already in ``pairs.csv`` are skipped.
A ROM game takes a few seconds, so the full run takes many hours.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # the game/ folder
BACKENDS = ["rom", "float"]         # the second is set from the command line

GAME_FIELDS = [
    "seed", "backend", "ending", "route_end", "score", "rating", "days",
    "end_day", "end_month", "end_year", "miles", "last_landmark",
    "last_landmark_name", "survivors", "health", "health_class",
    "member_1", "member_2", "member_3", "member_4", "member_5",
    "sick_at_end", "illnesses_during_game", "oxen", "clothing", "bullets",
    "wheels", "axles", "tongues", "food", "money", "final_seed_bytes", "error",
]


def pair_fields(other):
    return [
        "seed", "trace_identical", "first_diff_day", "seed_bytes_equal_at_first_diff",
        "same_ending", "ending_rom", f"ending_{other}", "score_rom", f"score_{other}",
        "score_diff", "survivors_rom", f"survivors_{other}", "survivors_diff",
        "days_rom", f"days_{other}", "days_diff", "miles_rom", f"miles_{other}",
        "health_rom", f"health_{other}",
    ]


PAIR_FIELDS = pair_fields("float")


CACHE = None      # a folder for ROM games already played, set by main()


def play(seed, backend):
    """One game. A ROM game is kept in ``CACHE`` and read back when asked again,
    so that several backends can be compared with the same ROM games."""
    if backend == "rom" and CACHE is not None:
        f = CACHE / f"{seed}.json"
        if f.is_file():
            got = json.loads(f.read_text())
            return got["row"], got["days"]
        row, days = _play(seed, backend)
        if row.get("ending") not in ("ERROR", "TIMEOUT"):
            f.write_text(json.dumps({"row": row, "days": days}))
        return row, days
    return _play(seed, backend)


def _play(seed, backend):
    with tempfile.TemporaryDirectory() as tmp:
        trace = Path(tmp) / "trace.log"
        cmd = [sys.executable, "-m", "oregon", "--preset", "--seed", str(seed),
               "--num", backend, "--demo", "--trace", str(trace),
               "--data", str(Path(tmp) / "data")]
        row = {k: "" for k in GAME_FIELDS}
        row.update(seed=seed, backend=backend)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                                  cwd=str(ROOT))
        except subprocess.TimeoutExpired:
            row.update(ending="TIMEOUT", error="timeout")
            return row, []
        days = []
        if trace.exists():
            days = [l for l in trace.read_text().splitlines()
                    if l and not l.startswith("#")]
        found = [l for l in proc.stderr.splitlines() if l.startswith("SUMMARY ")]
        if proc.returncode != 0 or not found:
            tail = proc.stderr.strip().splitlines()
            row.update(ending="ERROR", error=tail[-1][:200] if tail else "no summary")
            return row, days
        s = json.loads(found[-1][len("SUMMARY "):])
        for i, m in enumerate(s.pop("members"), 1):
            row[f"member_{i}"] = m
        row.update({k: v for k, v in s.items() if k in row})
        row["final_seed_bytes"] = days[-1].split()[-1] if days else ""
        return row, days


def compare(seed, other, r, p, a, b):
    """The ``pairs.csv`` row for one seed: ROM game ``r``/``a`` against ``p``/``b``."""
    diff = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    if diff is None and len(a) != len(b):
        diff = min(len(a), len(b))
    seeds_equal = ""
    if diff is not None and diff < len(a) and diff < len(b):
        seeds_equal = int(a[diff].split()[-1] == b[diff].split()[-1])

    def d(key):
        try:
            return float(p[key]) - float(r[key])
        except (TypeError, ValueError):
            return ""

    return {
        "seed": seed,
        "trace_identical": int(diff is None),
        "first_diff_day": "" if diff is None else diff + 1,
        "seed_bytes_equal_at_first_diff": seeds_equal,
        "same_ending": int(r["ending"] == p["ending"]),
        "ending_rom": r["ending"], f"ending_{other}": p["ending"],
        "score_rom": r["score"], f"score_{other}": p["score"], "score_diff": d("score"),
        "survivors_rom": r["survivors"], f"survivors_{other}": p["survivors"],
        "survivors_diff": d("survivors"),
        "days_rom": r["days"], f"days_{other}": p["days"], "days_diff": d("days"),
        "miles_rom": r["miles"], f"miles_{other}": p["miles"],
        "health_rom": r["health"], f"health_{other}": p["health"],
    }


def play_seed(job):
    """Play one seed with the ROM once and with each other backend."""
    global CACHE
    seed, others, cache = job
    CACHE = Path(cache) if cache else None
    r, a = play(seed, "rom")
    out = {}
    for other in others:
        p, b = play(seed, other)
        out[other] = ([r, p], compare(seed, other, r, p, a, b))
    return out


def done_seeds(path):
    if not path.is_file():
        return set()
    with open(path, newline="") as fh:
        return {int(row["seed"]) for row in csv.DictReader(fh) if row.get("seed")}


def main(argv):
    lo = int(argv[1]) if len(argv) > 1 else 0
    hi = int(argv[2]) if len(argv) > 2 else 65535
    workers = int(argv[3]) if len(argv) > 3 else 2
    out = Path(argv[4]) if len(argv) > 4 else ROOT / "results"
    others = (argv[5] if len(argv) > 5 else "float").split(",")
    cache = argv[6] if len(argv) > 6 else ""        # a folder to keep ROM games in
    if cache:
        Path(cache).mkdir(parents=True, exist_ok=True)
    # one backend writes into the folder itself, several into a folder each
    folders = {o: (out / o if len(others) > 1 else out) for o in others}
    done = None
    for o, f in folders.items():
        f.mkdir(parents=True, exist_ok=True)
        got = done_seeds(f / "pairs.csv")
        done = got if done is None else (done & got)
    todo = [s for s in range(lo, hi + 1) if s not in done]
    print(f"{len(todo)} seeds to play ({len(done)} already done), {workers} workers, "
          f"ROM against {', '.join(others)}")
    if not todo:
        return
    files, writers = [], {}
    for o, f in folders.items():
        gp, pp = f / "games.csv", f / "pairs.csv"
        new_g, new_p = not gp.is_file(), not pp.is_file()
        gf, pf = open(gp, "a", newline=""), open(pp, "a", newline="")
        files += [gf, pf]
        gw, pw = csv.DictWriter(gf, GAME_FIELDS), csv.DictWriter(pf, pair_fields(o))
        if new_g:
            gw.writeheader()
        if new_p:
            pw.writeheader()
        writers[o] = (gw, pw, gf, pf, done_seeds(pp))
    start = time.time()
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            jobs = [(s, others, cache) for s in todo]
            for n, result in enumerate(pool.map(play_seed, jobs), 1):
                for o, (rows, pair) in result.items():
                    gw, pw, gf, pf, already = writers[o]
                    if pair["seed"] in already:     # this backend had it already
                        continue
                    gw.writerows(rows)
                    pw.writerow(pair)
                    gf.flush()
                    pf.flush()
                if n % 25 == 0 or n == len(todo):
                    rate = (time.time() - start) / n
                    left = rate * (len(todo) - n) / 3600
                    print(f"{n}/{len(todo)} seeds, {rate:.1f} s per seed, "
                          f"about {left:.1f} h left", flush=True)
    finally:
        for fh in files:
            fh.close()


if __name__ == "__main__":
    main(sys.argv)
