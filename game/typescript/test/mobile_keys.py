"""The phone keyboard path, in an emulated touch browser: after Play the hidden text field has the focus, text that arrives in it
(as a soft keyboard delivers it, with no key events) becomes game keys, Return ends an answer, and the on-screen keys work.
    python3 test/mobile_keys.py            (needs the built site/: python3 build-site.py)"""
import subprocess, time, hashlib, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parent.parent
srv = subprocess.Popen(["python3", "-m", "http.server", "8767", "--directory", str(ROOT / "site")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
bad = []
def check(ok, what):
    print("ok  " if ok else "FAIL", what)
    if not ok: bad.append(what)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if Path("/opt/pw-browsers/chromium").exists() else p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 800}, has_touch=True, is_mobile=True)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: bad.append(str(e)))
        pg.goto("http://localhost:8767/?fast")
        pg.wait_for_function("!document.getElementById('go').disabled", timeout=30000)
        pg.tap("#go"); time.sleep(1)
        check(pg.evaluate("document.activeElement && document.activeElement.id") == "kbd", "the typing field has the focus after Play")
        check(pg.evaluate("getComputedStyle(document.getElementById('pad')).display") == "block", "on-screen keys are shown on a touch screen")
        def shot():
            return hashlib.md5(pg.locator("#screen").screenshot()).hexdigest()
        pg.keyboard.insert_text(" "); time.sleep(.6)       # the title: any key
        a = shot()
        pg.keyboard.insert_text("1"); time.sleep(.6)
        t = shot()
        check(a != t, "a typed digit appears on the screen")
        pg.keyboard.insert_text("1"); time.sleep(.6)       # a second one is refused (one character) so nothing changes
        check(shot() == t, "a one-character answer does not run on until Return")
        pg.keyboard.press("Backspace"); time.sleep(.6)
        check(shot() != t, "Backspace takes it back")
        pg.keyboard.insert_text("1"); time.sleep(.3)
        pg.tap("#pad button[data-k=enter]"); time.sleep(1.2)
        check(shot() != t, "the on-screen Return sends the answer on")
        check(pg.evaluate("document.activeElement.id") == "kbd", "tapping an on-screen key keeps the keyboard up")
        b.close()
finally:
    srv.terminate()
sys.exit(1 if bad else 0)
