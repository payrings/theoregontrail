#!/usr/bin/env python3
"""Compare the TypeScript core with the Python rebuild, seed by seed.

    python3 game/typescript/compare.py 0 49                 # seeds 0 to 49, day by day, against Python `exact`
    python3 game/typescript/compare.py --num rom 0 49       # against the Apple IIe ROM itself (needs py65 and the ROM)
    python3 game/typescript/compare.py 0 65535 16           # every 16th seed (the last number is the step)
    python3 game/typescript/compare.py --rows game/python/sample_games.csv  # TypeScript against the recorded `rom` rows
    node game/typescript/dist/cli.js --range 0 65535        # TypeScript alone: play every seed, print the tally

The TypeScript core does Applesoft's arithmetic with a transcription of the ROM's routines (src/fp.ts), so
it is compared with the Python rebuild's `exact` backend, which is held to the ROM, and with the ROM.

For each seed both programs play the preset demo game. The day-by-day traces must be identical
(every cell of every day, including the five RND seed bytes) and the final summaries must agree.
"""
import csv, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TS = Path(__file__).resolve().parent              # game/typescript
GAME = TS.parent / "python"                        # the Python game it is compared with

NUM = "exact"

# the TypeScript is told where this repository keeps the dialogue, whatever directory it is run from
DOC = TS / "data" / "dialogue.md"
DIALOGUE = ["--dialogue", str(DOC)] if DOC.is_file() else []

def TSNUM():
    """TypeScript has no ROM: `rom` and `exact` both mean its transcription of the ROM"""
    return NUM if NUM in ("rounded", "float") else "exact"

def py_game(seed):
    with tempfile.TemporaryDirectory() as tmp:
        trace = Path(tmp) / "t.log"
        p = subprocess.run([sys.executable, "-W", "ignore", "-m", "oregon", "--preset", "--seed", str(seed),
                            "--num", NUM, "--demo", "--trace", str(trace), "--data", str(Path(tmp) / "d")],
                           capture_output=True, text=True, cwd=GAME, timeout=900)
        days = [l for l in trace.read_text().splitlines() if l and not l.startswith("#")] if trace.exists() else []
        found = [l for l in p.stderr.splitlines() if l.startswith("SUMMARY ")]
        return (json.loads(found[-1][8:]) if found else None), days, p.stderr.strip().splitlines()[-1:] 

def ts_game(seed):
    with tempfile.TemporaryDirectory() as tmp:
        trace = Path(tmp) / "t.log"
        # --preset, as the Python side is run: without it the TypeScript plays the menu and the store, a different game
        p = subprocess.run(["node", str(TS / "dist" / "cli.js"), "--preset", "--num", TSNUM(), *DIALOGUE, str(seed), str(trace)],
                           capture_output=True, text=True, timeout=900)
        line = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ""
        days = trace.read_text().splitlines() if trace.exists() else []
        if line.startswith("SUMMARY "):
            return json.loads(line[8:]), days, None
        return None, days, line

KEYS = ["ending", "route_end", "score", "rating", "days", "end_day", "end_month", "end_year", "miles", "last_landmark",
        "survivors", "health", "members", "sick_at_end", "illnesses_during_game", "oxen", "clothing", "bullets",
        "wheels", "axles", "tongues", "food", "money"]

def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-6
    return a == b

def check(seed):
    ps, pd, perr = py_game(seed)
    ts, td, terr = ts_game(seed)
    if ps is None or ts is None:
        # both erroring is agreement of a kind, but report it
        return seed, ("both failed" if ps is None and ts is None else "one failed"), (perr, terr)
    first = next((i + 1 for i, (x, y) in enumerate(zip(pd, td)) if x != y), None)
    if first is None and len(pd) != len(td): first = min(len(pd), len(td)) + 1
    bad = [k for k in KEYS if not same(ps.get(k), ts.get(k))]
    if first is None and not bad:
        return seed, "match", ps["ending"]
    return seed, "DIFFER", {"first_day": first, "fields": bad, "py": pd[first - 1] if first and first <= len(pd) else None,
                            "ts": td[first - 1] if first and first <= len(td) else None}

def check_rows(path):
    """Play each `rom` row's seed in TypeScript and compare with the recorded row itself (no Python game run)."""
    rows = [r for r in csv.DictReader(open(path, newline="")) if r["backend"] == "rom"]
    bad = 0
    for r in rows:
        # the recorded rows are games from the preset start (README: "Every seed was played from one preset start")
        out = subprocess.run(["node", str(TS / "dist" / "cli.js"), "--preset", *DIALOGUE, r["seed"]], capture_output=True, text=True).stdout.strip()
        s = json.loads(out.splitlines()[-1][8:])
        diffs = []
        for k in ["ending", "route_end", "score", "rating", "days", "end_day", "end_month", "end_year", "last_landmark",
                  "survivors", "sick_at_end", "illnesses_during_game", "wheels", "axles", "tongues"]:
            if str(s[k]) != r[k]: diffs.append((k, s[k], r[k]))
        for k in ["miles", "health", "oxen", "clothing", "bullets", "food", "money"]:
            if abs(float(s[k]) - float(r[k])) > 1e-9: diffs.append((k, s[k], r[k]))
        if s["members"] != [r[f"member_{i}"] for i in range(1, 6)]: diffs.append(("members",))
        if s["final_seed_bytes"] != r["final_seed_bytes"]: diffs.append(("seed bytes", s["final_seed_bytes"], r["final_seed_bytes"]))
        print(r["seed"], "match" if not diffs else diffs)
        bad += bool(diffs)
    print(f"{len(rows)} rom rows, {bad} differ")

def main():
    global NUM
    args = sys.argv[1:]
    if args[:1] == ["--num"]:
        NUM, args = args[1], args[2:]
    if args[0] == "--rows":
        return check_rows(args[1])
    if args[0] == "--csv":
        want = "rom" if NUM == "exact" and "--num" not in sys.argv else NUM
        with open(args[1], newline="") as fh:
            seeds = sorted({int(r["seed"]) for r in csv.DictReader(fh) if r["backend"] == want})
    else:
        step = int(args[2]) if len(args) > 2 else 1
        seeds = range(int(args[0]), int(args[1]) + 1, step)
    tally = {}
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        for seed, verdict, info in ex.map(check, seeds):
            tally[verdict] = tally.get(verdict, 0) + 1
            if verdict != "match":
                print(seed, verdict, info, flush=True)
    print("seeds:", sum(tally.values()), tally)

main()
