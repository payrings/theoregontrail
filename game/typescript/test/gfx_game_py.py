"""Plays whole games in the Python graphical mode with a self-playing keyboard and prints a hash of every
frame it draws, for comparison with gfx_game.mjs (the TypeScript front end).

  python3 gfx_game_py.py ASSETS_FOLDER FIRST LAST [--wander] [--preset] [--frames FILE]
"""
import hashlib, sys, time, io, json, os
from contextlib import redirect_stdout, redirect_stderr
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "python"))
import warnings; warnings.filterwarnings("ignore")
from oregon import applesoft
applesoft.use("exact")
from oregon.ui import AutoUI, ALLOWED
from oregon.graphics.assets import Assets
from oregon.graphics.gui import GraphicalUI


DUMP = None
STOP = None


class FakeClock:
    t = 0.0
    @classmethod
    def now(cls): return cls.t
    @classmethod
    def sleep(cls, s): cls.t += max(0.0, s)

time.sleep = FakeClock.sleep
time.monotonic = FakeClock.now
time.perf_counter = FakeClock.now


class Backend:
    def __init__(self, ui): self.keys, self.ui, self.frames = [], ui, []
    def show(self, img):
        if STOP is not None and len(self.frames) > STOP: raise SystemExit
        if DUMP is not None and len(self.frames) in DUMP: img.convert("RGB").save(os.path.join(os.environ.get("GFX_DUMP_DIR", "."), f"py_{len(self.frames)}.png"))
        self.frames.append(hashlib.md5(img.convert("RGB").tobytes()).hexdigest()[:8])
    def read(self): return self.keys.pop(0) if self.keys else None
    def read_timeout(self, s): return self.read()
    def poll(self): return None
    def pump(self): pass
    def flush(self): pass


class Recorder(AutoUI):
    """the text-mode self-player, remembering every answer it gives"""
    def __init__(self, quiet=True, wander=False):
        super().__init__(quiet=quiet, wander=wander)
        self.given = []

    def key(self, allowed="", maxlen=1, default=""):
        a = super().key(allowed, maxlen, default)
        self.given.append(a)
        return a


class AutoGUI(GraphicalUI):
    """the graphical front end, answering from a recorded list: the same questions in the same order"""
    def __init__(self, assets, answers):
        be = Backend(self)
        super().__init__(assets, be, show_daily=True)
        self.answers = list(answers)
        self.daily_pause = 0.05

    def _next(self):
        return self.answers.pop(0) if self.answers else ""

    def _answer(self, maxlen, allowed=""):
        a = self._next()[:maxlen] if maxlen else self._next()
        self.backend.keys = list(a) + (["\r"] if len(a) < maxlen or maxlen == 0 else [])
        return a

    def key(self, allowed="", maxlen=1, default="", ret=True):
        self._answer(maxlen)
        return super().key(allowed, maxlen, default, ret)

    def yes_no(self, prompt=""):
        z = ""
        for _ in range(64):
            z = self._next()[:3]
            if z: break
        self.backend.keys = [z[0]] if z else []
        return super().yes_no(prompt)

    def wait_key(self, allowed="", prompt="Press SPACE BAR to continue", y=184, tune=False):
        self.backend.keys = [" "]
        return super().wait_key(allowed, prompt, y, tune)

    def flip_disk(self, side, title="OREGON TRAIL"):
        self.backend.keys = [" "]
        return super().flip_disk(side, title)


if os.environ.get("GFXDBG"):
    from oregon import rng as _R
    _o = _R.SeededRnd.seed_from_keyboard
    def _sk(self, counter):
        sys.__stderr__.write(f"RESEED {counter}\n"); return _o(self, counter)
    _R.SeededRnd.seed_from_keyboard = _sk


def main():
    argv = sys.argv[1:]
    wander, preset = "--wander" in argv, "--preset" in argv
    def opt(name):
        nonlocal argv
        if name not in argv: return None
        i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
    global DUMP, STOP
    st = opt("--stop")
    STOP = int(st) if st else None
    d = opt("--dump")
    DUMP = {int(x) for x in d.split(",")} if d else None
    frames_file = opt("--frames")
    answers_file = opt("--answers")
    argv = [a for a in argv if a not in ("--wander", "--preset")]
    folder, first, last = argv[0], int(argv[1]), int(argv[2])
    assets = Assets(folder)
    import oregon.__main__ as M
    holder = {}
    def record(quiet=True, wander=False):
        ui = Recorder(quiet, wander)
        holder["rec"] = ui
        return ui
    answers = {}
    for seed in range(first, last + 1):
        flags = (["--preset"] if preset else []) + (["--wander"] if wander else [])
        # 1: the text game, to learn what the self-player answers
        applesoft.use("exact")                    # a fresh arithmetic backend, so no RND seed carries over from the last game
        M.AutoUI = record
        with tempfile_dir() as d, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            try:
                M.main(["--demo", "--seed", str(seed), "--data", d] + flags)
            except SystemExit:
                pass
        given = holder["rec"].given
        answers[seed] = given
        # 2: the same game in the graphical front end
        FakeClock.t = 0.0
        def make(quiet=True, wander=False):
            ui = AutoGUI(assets, given)
            holder["ui"] = ui
            return ui
        applesoft.use("exact")
        M.AutoUI = make
        with tempfile_dir() as d, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            try:
                M.main(["--demo", "--seed", str(seed), "--data", d] + flags)
            except SystemExit:
                pass
        fr = holder["ui"].backend.frames
        digest = hashlib.md5("".join(fr).encode()).hexdigest()[:10]
        print(seed, len(fr), digest, flush=True)
        if frames_file:
            open(frames_file, "w").write("\n".join(fr))
        if answers_file:
            json.dump(answers, open(answers_file, "w"))


class tempfile_dir:
    def __enter__(self):
        import tempfile; self.t = tempfile.TemporaryDirectory(); return self.t.name
    def __exit__(self, *a): self.t.cleanup()


main()
