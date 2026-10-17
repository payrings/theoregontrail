#!/usr/bin/env python3
"""Check the TypeScript game against the Python rebuild, seed by seed, with progress and an estimate.

    python3 verify.py --oracle rom     --first 0 --last 65535   # against the Apple IIe ROM (needs py65 + ROM)
    python3 verify.py --oracle exact   --first 0 --last 65535   # against the transcription of the ROM
    python3 verify.py --oracle rounded --first 0 --last 65535   # host doubles rounded to Applesoft's precision
    python3 verify.py --oracle float   --first 0 --last 65535   # plain host doubles
    python3 verify.py --oracle all     --first 0 --last 65535   # the four in turn

    --step N       every Nth seed (a quick pass: --step 64 is 1,024 seeds)
    --jobs N       worker processes, for both sides (default: every core this computer has)
    --state FILE   resume file (default verify-<oracle>.state): seeds already compared are skipped
    --mode M       what is played: `full` (menu, Matt's store, the whole trail; the default), `preset` (the fixed
                   carpenter start), `wander` (as full, but it also changes pace and rations, rests, trades, talks,
                   hunts, shops at forts and rafts) or `all` (the three in turn)

For each seed both programs play the same game and the sha-1 of the day-by-day trace (every cell of every
day, including the five RND seed bytes) and the final summary must agree. TypeScript has no ROM: against
`rom` and `exact` it uses its transcription of the ROM's routines; against `rounded` and `float` it uses
its own rounded and plain-double arithmetic.

A line on the terminal shows done/total, rate, elapsed time and the estimated time left; Ctrl-C stops and
the state file lets the next run carry on. Mismatches are written to verify-<oracle>.failures with the
first differing day, and the run ends with a tally.
"""
import argparse, hashlib, io, json, os, subprocess, sys, tempfile, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

TS = Path(__file__).resolve().parent              # game/typescript
GAME = TS.parent / "python"                        # the Python game it is compared with

KEYS = ["ending", "route_end", "score", "rating", "days", "end_day", "end_month", "end_year", "miles", "last_landmark",
        "survivors", "health", "members", "sick_at_end", "illnesses_during_game", "oxen", "clothing", "bullets",
        "wheels", "axles", "tongues", "food", "money"]


# talking to people reads the dialogue document; the TypeScript is told where this repository keeps it
_DOC = TS / "data" / "dialogue.md"
DIALOGUE = ["--dialogue", str(_DOC)] if _DOC.is_file() else []


def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-6
    return a == b


def ts_num(oracle):
    return oracle if oracle in ("rounded", "float") else "exact"


# ----------------------------------------------------------------------------- Python side
_booted = None


def _boot(oracle, extra):
    global _booted
    sys.path.insert(0, str(GAME))
    import warnings
    warnings.simplefilter("ignore")
    from oregon import applesoft
    applesoft.use(oracle)
    _booted = (oracle, tuple(extra))


def py_game(args):
    """Play one seed in this process. Returns (seed, summary or None, trace lines, error text)."""
    seed, oracle, extra = args
    if _booted is None:
        _boot(oracle, extra)
    # a new arithmetic backend for every game, as a new process would have: for `rom` that is a fresh
    # emulated machine, so nothing one game leaves in its memory can reach the next
    from oregon import applesoft
    applesoft.use(oracle)
    from oregon.__main__ import main
    with tempfile.TemporaryDirectory() as tmp:
        trace = Path(tmp) / "t.log"
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                main([*extra, "--seed", str(seed), "--demo", "--trace", str(trace), "--data", str(Path(tmp) / "d")])
            except SystemExit:
                pass
            except Exception as e:  # noqa: BLE001
                return seed, None, [], f"{type(e).__name__}: {e}"
        days = [l for l in trace.read_text().splitlines() if l and not l.startswith("#")] if trace.exists() else []
    found = [l for l in err.getvalue().splitlines() if l.startswith("SUMMARY ")]
    return seed, (json.loads(found[-1][8:]) if found else None), days, (err.getvalue().strip().splitlines() or [""])[-1]


def py_digest(args):
    seed, summary, days, err = py_game(args)
    return seed, summary, hashlib.sha1("\n".join(days).encode()).hexdigest(), len(days), err


# ----------------------------------------------------------------------------- TypeScript side
def ts_chunks(seeds, num, extra, jobs):
    """Run TypeScript over the seeds in a few node processes; yield (seed, summary, sha1) as lines arrive."""
    seeds = list(seeds)
    step = (seeds[1] - seeds[0]) if len(seeds) > 1 else 1
    k = max(1, min(jobs, len(seeds)))
    parts = [seeds[i::k] for i in range(k)]
    procs = []
    for part in parts:
        if not part:
            continue
        # a stride of k * step starting at the part's first seed
        cmd = ["node", str(TS / "dist" / "cli.js"), "--num", num, "--digest", str(part[0]), str(part[-1]), str(step * k)]
        cmd[2:2] = [a for a in extra if a in ("--preset", "--wander")] + DIALOGUE
        procs.append(subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True))
    return procs


def read_ts(procs):
    """Collect every digest line from the node processes into a dict (they are fast; Python is the slow side)."""
    table = {}
    for p in procs:
        for line in p.stdout:
            if line.startswith("D "):
                _, seed, rest = line.split(" ", 2)
                body, sha = rest.rsplit(" ", 1)
                table[int(seed)] = (json.loads(body), sha.strip())
            elif line.startswith("E "):
                table[int(line.split(" ", 2)[1])] = (None, line.strip())
        p.wait()
    return table


def first_difference(seed, oracle, extra):
    """Re-play one mismatching seed and find the first day on which the traces differ."""
    _, psum, pdays, perr = py_game((seed, oracle, extra))
    with tempfile.TemporaryDirectory() as tmp:
        trace = Path(tmp) / "t.log"
        p = subprocess.run(["node", str(TS / "dist" / "cli.js"), "--num", ts_num(oracle), *extra, *DIALOGUE, str(seed), str(trace)],
                           capture_output=True, text=True)
        tdays = trace.read_text().splitlines() if trace.exists() else []
    n = next((i for i, (a, b) in enumerate(zip(pdays, tdays)) if a != b), None)
    if n is None and len(pdays) != len(tdays):
        n = min(len(pdays), len(tdays))
    return {"seed": seed, "first_day": None if n is None else n + 1,
            "python": pdays[n] if n is not None and n < len(pdays) else None,
            "typescript": tdays[n] if n is not None and n < len(tdays) else None, "python_error": perr}


# ----------------------------------------------------------------------------- progress
def fmt_time(s):
    s = int(max(0, s))
    return f"{s // 3600}h{(s % 3600) // 60:02d}m{s % 60:02d}s" if s >= 3600 else f"{s // 60}m{s % 60:02d}s"


class Progress:
    def __init__(self, label, total, done0=0):
        self.label, self.total, self.done0 = label, total, done0
        self.t0 = time.time()
        self.win = []                      # (time, done) for a moving rate
        self.last = 0

    def update(self, done, bad, force=False):
        now = time.time()
        if not force and now - self.last < 0.5:
            return
        self.last = now
        self.win.append((now, done))
        self.win = [w for w in self.win if now - w[0] <= 60]
        t, d = self.win[0]
        rate = (done - d) / (now - t) if now > t and done > d else (done - self.done0) / max(1e-9, now - self.t0)
        left = (self.total - done) / rate if rate > 0 else float("inf")
        width = 30
        fill = int(width * done / max(1, self.total))
        bar = "#" * fill + "-" * (width - fill)
        eta = "?" if left == float("inf") else fmt_time(left)
        sys.stderr.write(f"\r{self.label} [{bar}] {done}/{self.total} {100 * done / max(1, self.total):5.1f}%  "
                         f"{rate:6.2f} games/s  elapsed {fmt_time(now - self.t0)}  left ~{eta}  differ {bad}   ")
        sys.stderr.flush()

    def finish(self):
        sys.stderr.write("\n")


# ----------------------------------------------------------------------------- one oracle
def run(oracle, seeds, jobs, extra, state_path, max_bad=50, label=""):
    done = {}
    if state_path.exists():
        for line in state_path.read_text().splitlines():
            r = json.loads(line)
            if r["ok"]:
                done[r["seed"]] = True
    todo = [s for s in seeds if s not in done]
    fails = Path(f"verify-{oracle}{label}.failures")
    print(f"\n== TypeScript ({ts_num(oracle)}) against Python {oracle}{label}: {len(seeds)} seeds, {jobs} worker processes"
          f"{f', {len(seeds) - len(todo)} already done' if len(todo) != len(seeds) else ''}", flush=True)
    if not todo:
        return 0
    ts_procs = ts_chunks(todo, ts_num(oracle), extra, jobs)
    ts = read_ts(ts_procs)
    prog = Progress(oracle + label, len(seeds), done0=len(seeds) - len(todo))
    bad = 0
    ndone = len(seeds) - len(todo)
    state = state_path.open("a")
    try:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            futs = [ex.submit(py_digest, (s, oracle, extra)) for s in todo]
            for f in as_completed(futs):
                seed, psum, psha, pn, perr = f.result()
                tsum, tsha = ts.get(seed, (None, "missing"))
                if psum is None or tsum is None:
                    ok = psum is None and tsum is None            # both stopped with an error: agreement
                else:
                    ok = psha == tsha and all(same(psum.get(k), tsum.get(k)) for k in KEYS)
                if not ok:
                    bad += 1
                    # the first few are analysed (a replay of the game on both sides); after that only noted
                    detail = first_difference(seed, oracle, extra) if bad <= 10 else {"seed": seed}
                    with fails.open("a") as fh:
                        fh.write(json.dumps(detail) + "\n")
                    if bad >= max_bad:
                        prog.update(ndone + 1, bad, force=True)
                        prog.finish()
                        print(f"{oracle}: stopping after {bad} differences (see {fails}); "
                              f"fix the cause first, or raise --max-failures", flush=True)
                        for fu in futs:
                            fu.cancel()
                        ex.shutdown(wait=False, cancel_futures=True)
                        return bad
                state.write(json.dumps({"seed": seed, "ok": ok}) + "\n")
                state.flush()
                ndone += 1
                prog.update(ndone, bad)
    except KeyboardInterrupt:
        prog.finish()
        print("stopped; run the same command again to carry on", flush=True)
        raise SystemExit(130)
    prog.update(ndone, bad, force=True)
    prog.finish()
    print(f"{oracle}: {ndone - bad} agree, {bad} differ" + (f"  (see {fails})" if bad else ""), flush=True)
    return bad


def check_build():
    """The compiled TypeScript must be newer than its sources, or the run would test an old build."""
    cli = TS / "dist" / "cli.js"
    newest = max((p.stat().st_mtime for p in (TS / "src").glob("*.ts")), default=0)
    if not cli.exists() or cli.stat().st_mtime < newest:
        print("typescript/dist is missing or older than typescript/src: building it (npx tsc) ...", flush=True)
        r = subprocess.run(["npx", "tsc"], cwd=TS)
        if r.returncode != 0 or not cli.exists() or cli.stat().st_mtime < newest:
            raise SystemExit("could not build the TypeScript; run `npm install && npx tsc` in typescript/ and try again")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--oracle", default="exact", choices=["rom", "exact", "rounded", "float", "all"])
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--last", type=int, default=65535)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--state")
    ap.add_argument("--max-failures", type=int, default=50, help="stop an oracle after this many differences")
    ap.add_argument("--mode", default="full", choices=["full", "preset", "wander", "all"])
    ap.add_argument("--preset", action="store_true", help="same as --mode preset")
    args = ap.parse_args()
    args.jobs = max(1, args.jobs)
    check_build()
    print(f"{os.cpu_count()} cores found; using {args.jobs} worker processes (change with --jobs N)")
    if args.preset:
        args.mode = "preset"
    flags = {"preset": ["--preset"], "full": [], "wander": ["--wander"]}
    modes = ["full", "preset", "wander"] if args.mode == "all" else [args.mode]
    seeds = list(range(args.first, args.last + 1, args.step))
    oracles = ["rom", "exact", "rounded", "float"] if args.oracle == "all" else [args.oracle]
    total_bad = 0
    t0 = time.time()
    for o in oracles:
        if o == "rom":
            sys.path.insert(0, str(GAME))
            try:
                from oregon.applesoft import rom_available
                if not rom_available():
                    print("rom: skipped (no py65 or no ROM image)")
                    continue
            except ImportError:
                print("rom: skipped (no py65)")
                continue
        for m in modes:
            label = "" if len(modes) == 1 and m == "full" else "-" + m
            total_bad += run(o, seeds, args.jobs, flags[m], Path(args.state or f"verify-{o}{label}.state"),
                             args.max_failures, label)
    print(f"\nfinished in {fmt_time(time.time() - t0)}; {total_bad} seeds differ in total")
    raise SystemExit(1 if total_bad else 0)


if __name__ == "__main__":
    main()
