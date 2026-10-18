"""Drive a real browser (Chromium through Playwright) through a whole game on the built page, answering from a recorded
list of answers, and take screenshots as it goes:

    python3 test/record_answers.py 1 --wander > /tmp/answers.json
    python3 test/browser_play.py /tmp/answers.json SECONDS ASSETS_FOLDER [DIALOGUE_FILE] [OUTPUT_DIR]

It shows that the page loads the files it is given, reads keys, draws, sleeps and runs a game to the end without an
error, and that it asks the same questions in the same order as the Node harness (`test/gfx_game.mjs`). The hook
`window.__oregonSetup` is the page's own test hook; nothing else in the page knows it is being tested.
"""
import sys, time, subprocess, os, json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = str(Path(__file__).resolve().parent.parent)
answers = open(sys.argv[1]).read()
ASSETS = sys.argv[3] if len(sys.argv) > 3 else str(Path(ROOT) / "assets")
DOC = sys.argv[4] if len(sys.argv) > 4 else str(Path(ROOT) / "data" / "dialogue.md")
OUT = sys.argv[5] if len(sys.argv) > 5 else "."
srv = subprocess.Popen(["python3", "-m", "http.server", "8766", "--directory", ROOT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
INIT = """
window.__shots = 0;
window.__oregonSetup = (ui, backend) => {
  window.__ui = ui; ui.countsKeyboardTime = false;
  const answers = %s; let i = 0;
  window.__tr = [];
  const next = () => { window.__tr.push(ui.out.slice(-1)[0] + " => " + (answers[i] ?? "<none>")); return i < answers.length ? answers[i++] : ""; };
  backend.poll = () => null;
  const stall = () => new Promise(() => {});
  backend.read = async () => (backend.queue.length ? backend.queue.shift() : (i >= answers.length ? stall() : null));
  backend.readTimeout = async () => (backend.queue.length ? backend.queue.shift() : (i >= answers.length ? stall() : null));
  ui.key = async function (allowed = "", maxlen = 1, def = "", ret = true) {
    if (i >= answers.length) { window.__done = true; return stall(); }
    const a = maxlen ? next().slice(0, maxlen) : next();
    backend.queue = [...a, ...(ret ? ["\\r"] : [])];
    return Object.getPrototypeOf(ui).key.call(ui, allowed, maxlen, def, ret);
  };
  ui.yesNo = async function (prompt = "") {
    let z = ""; for (let k = 0; k < 64; k++) { z = next().slice(0, 3); if (z) break; }
    backend.queue = z ? [z[0]] : [];
    return Object.getPrototypeOf(ui).yesNo.call(ui, prompt);
  };
  const w = ui.waitKey; ui.waitKey = async function (...a) { backend.queue = [" "]; return w.apply(ui, a); };
  const f = ui.flipDisk; ui.flipDisk = async function (...a) { backend.queue = [" "]; return f.apply(ui, a); };
  window.__answered = () => i;
};
""" % answers
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1100, "height": 800})
        logs = []
        pg.on("console", lambda m: logs.append(m.text))
        pg.on("pageerror", lambda e: logs.append("PAGEERROR " + str(e)))
        pg.add_init_script(INIT)
        pg.goto("http://localhost:8766/index.html?fast")
        pg.set_input_files("#folder", ASSETS)
        pg.set_input_files("#loose", DOC)
        time.sleep(1.5)
        pg.click("#go")
        t0 = time.time(); n = 0
        while time.time() - t0 < float(sys.argv[2]):
            time.sleep(8); n += 1
            pg.screenshot(path=f"{OUT}/run{n:02d}.png")
            if pg.is_visible("#error"): break
            print(n, pg.evaluate("window.__answered()"), pg.evaluate("!!window.__done"), flush=True)
            if pg.evaluate("!!window.__done"): break
        pg.screenshot(path=f'{OUT}/final.png')
        open(f'{OUT}/browser_trace.txt','w').write('\n'.join(pg.evaluate('window.__tr')))
        print(logs[:10])
        print(pg.inner_text("#error") if pg.is_visible("#error") else "no error")
        b.close()
finally:
    srv.kill()
