"""Record what the self-player answers in a text-mode game, for replay in the graphical front ends:
   python3 record_answers.py SEED [--wander] [--preset] > answers.json"""
import io, json, os, sys, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "python"))
from contextlib import redirect_stdout, redirect_stderr
from oregon import applesoft
applesoft.use("exact")
from oregon.ui import AutoUI
import oregon.__main__ as M
import tempfile

class Recorder(AutoUI):
    def __init__(self, quiet=True, wander=False):
        super().__init__(quiet=quiet, wander=wander); self.given = []
    def key(self, allowed="", maxlen=1, default=""):
        a = super().key(allowed, maxlen, default); self.given.append(a); return a

holder = {}
def make(quiet=True, wander=False):
    holder["u"] = Recorder(quiet, wander); return holder["u"]
M.AutoUI = make
seed = sys.argv[1]; flags = [a for a in sys.argv[2:]]
with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    try: M.main(["--demo", "--seed", seed, "--data", d] + flags)
    except SystemExit: pass
print(json.dumps(holder["u"].given))
