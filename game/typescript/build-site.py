#!/usr/bin/env python3
"""Build the folder to publish: index.html, the compiled game, and the files it plays with.

    python3 build-site.py [OUT]            # default OUT: site/
    python3 build-site.py --assets DIR --dialogue FILE

The game's pictures (assets/), its dialogue (data/dialogue.md) and a manifest listing them
go under data/, where the page fetches them. The music is made by the game itself, so there are no tune files.
Run `npx tsc` first.
"""
import json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
assets = Path(opt("--assets", HERE / "assets"))
dialogue = Path(opt("--dialogue", HERE / "data" / "dialogue.md"))
out = Path(args[0]) if args else HERE / "site"

if not (HERE / "dist" / "browser" / "main.js").is_file():
    sys.exit("dist/ is missing: run `npx tsc` in typescript/ first")
if out.exists():
    shutil.rmtree(out)
(out / "dist").mkdir(parents=True)
shutil.copy(HERE / "index.html", out / "index.html")
for f in (HERE / "dist").rglob("*.js"):
    rel = f.relative_to(HERE / "dist")
    if rel.name in ("cli.js", "optest.js"):          # command-line tools, not part of the page
        continue
    (out / "dist" / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(f, out / "dist" / rel)
names = []
(out / "data").mkdir(parents=True, exist_ok=True)
if assets.is_dir():
    for f in sorted(assets.rglob("*")):
        if f.is_file() and f.name != ".DS_Store":
            rel = "assets/" + f.relative_to(assets).as_posix()
            (out / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, out / "data" / rel)
            names.append(rel)
else:
    print(f"note: no pictures found at {assets}; the page will ask the player "
          "for the folder that holds font/, images/ and screens/", file=sys.stderr)
if dialogue.is_file():
    shutil.copy(dialogue, out / "data" / "dialogue.md")
    names.append("dialogue.md")
else:
    print("note: no dialogue document found; people will have placeholder lines", file=sys.stderr)
(out / "data" / "manifest.json").write_text(json.dumps(names))
(out / ".nojekyll").write_text("")
print(f"{out}: {len(names)} data files, {sum(1 for _ in (out / 'dist').rglob('*.js'))} scripts")
