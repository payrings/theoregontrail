# The Oregon Trail in TypeScript: the whole game, in a browser

The full game, rebuilt a second time in a different language from the Python rebuild, to show that
the rules in the paper and the listing carry over, **and that Applesoft's own arithmetic can be
reproduced in another language**. It plays in a browser (the menu, Matt's store, the trail, rivers,
forts, hunting, the raft, the tombstones and the top ten, with the pictures and the sound), and it plays
whole games by itself from the command line, which is how it is checked.

## Play it

Anyone can play it from a web address, with nothing to install: the page is static files. The game's pictures
(the `assets/` folder, the pictures drawn for this rebuild), its dialogue (`data/dialogue.md`) and a manifest are
copied under the site's `data/`, and the
page fetches them when it opens. The player can point the page at another folder instead, and the game
plays the same either way. The music is made by the game itself (`src/gfx/sound.ts`), so it needs no files, and it
starts after the first key press, as browsers require.

    npm install                  # TypeScript (and its Node types); `npx tsc` alone also works
    npx tsc                      # builds dist/
    python3 build-site.py        # the folder to publish: site/ (index.html, dist/, data/)
    python3 -m http.server 8000 --directory site    # try it at http://localhost:8000/

**Publishing.** `.github/workflows/pages.yml` does the same on every push to `main` and deploys to GitHub Pages (set
Settings > Pages > Source to "GitHub Actions"). Any static host works: ES modules need `http(s)://`, not `file://`. The
browser needs `DecompressionStream` (Chrome 80, Firefox 113, Safari 16.4 or later).

**Your own files instead.** "Use my own files instead" on the first page takes a folder in the same layout (`screens/`,
`images/`, `font/`, `hunt/`, optional `theme.json`), tune files (`MS0.BIN` … `MS17.BIN`, `TS.BIN`, as saved by
`game/python/tools/dump_tunes.py --extract`) and a dialogue document. They are read by the page and kept only in that browser
(IndexedDB); nothing is uploaded. Without `data/` (a bare checkout served as it is) the page asks for them straight away.

Keys: letters and digits as asked, Return, Backspace, the arrow keys and Space in the hunt, Control-S for the sound (or
the button under the picture). The top ten and the tombstones are kept in `localStorage`; "Erase top ten & tombstones"
on the first page clears them.

**Rights.** The dialogue (`data/dialogue.md`) is replacement text written for this project; the original game's text is not
included. It is the same file, byte for byte, as `../python/oregon/data/dialogue.md`, and `verify.py` refuses to run if the
two differ. The pictures and the music are recreations too. A dialogue document in the same format (`Landmark N (name), slot S`,
then `Speaker:` and `Text:`) can replace it: `--dialogue FILE` on the command line, or "Use my own files" in the browser.

## What is in it

- **Arithmetic: the Apple IIe ROM's, transcribed.** Every number is Applesoft's five-byte value with its
  extension byte (`src/num.ts`). Addition, subtraction, multiplication, division, `INT`, `ROUND.FAC`,
  comparison, the decimal-literal converter and `STR$` (`FOUT`) are a line-for-line transcription of the
  ROM's routines (`src/fp.ts`), a port of the Python rebuild's `exact` backend; `RND` is the integer model of
  `$EFAE` (`src/rnd.ts`). No ROM byte is read or run. Two other backends exist for the comparison: `rounded`
  (host doubles rounded to Applesoft's precision) and `float` (plain doubles). `--num exact|rounded|float`.
- **Game logic** (`src/*.ts`): the menu, the store, the daily cycle, the fifteen events, illness and death, rivers
  (ford, float, ferry, guide), trading, talking, hunting, fort shops, resting, pace and rations, broken parts,
  fire and theft, the Barlow Road, the raft down the Columbia, graves and tombstones, the hand-over, the score
  and the top ten. Each function follows the Python rebuild and so the BASIC listing; line numbers are in the
  comments. All logic that can wait for a person is `async`; the numeric core stays synchronous.
- **Graphical front end** (`src/gfx/`): a 280 × 192 canvas made the way the Apple II made it (`canvas.ts`, with the
  Apple's colour rules for text, or a theme's plain colours), the screens laid out as the BASIC lays them out
  (`screens.ts`), the hunting field and the raft (`hunt_scene.ts`, `hunt_field.ts`, `raft_scene.ts`) and the
  sound (`sound.ts`: the extracted tunes, or made-up ones, through WebAudio). Nothing in `gfx/` touches the
  browser except through the small `Backend` and `AudioOut` interfaces, so the same drawing code runs in Node
  and its frames can be compared pixel for pixel with the Python rebuild.
- **Browser shell** (`src/browser/`, `index.html`): the canvas and key events, the file picker and its storage,
  `localStorage` saves.
- **Driver** (`src/ui.ts`, `src/cli.ts`): `AutoUI` answers each prompt from the text printed since the last
  answer, with the Python rebuild's rules in the same order; `--wander` adds the pace and rations screens,
  resting, trading, talking, hunting, fort shops and the raft, so a check reaches that code too.

## Check it

The same three layers as the Python rebuild, for every seed from 0 to 65,535 and every backend:

    python3 verify.py --oracle all --first 0 --last 65535 --mode all     # progress, rate, time left; resumable

`--oracle rom|exact|rounded|float`; `--mode full|preset|wander|all`; `--jobs N` (default: every core);
`--step N` for a quick pass. For each seed both programs play the same game and the sha-1 of the day-by-day
trace (every cell of every day, including the five `RND` seed bytes, which show a missing or extra draw on the
day it happens) and the final summary must agree. `rom` needs `py65` and the ROM image, so it can only run
where they are; against it the TypeScript is compared through the transcription.

    python3 compare.py 0 399                        # a day-by-day comparison against Python `exact`
    python3 compare.py --rows ../python/sample_games.csv   # against the games recorded from the ROM
    node dist/cli.js [--num B] [--preset] [--wander] SEED [TRACE]   # play one seed
    node dist/cli.js --screen 4000                  # ... and print everything the game said

**The graphics are checked frame by frame.** Python and TypeScript play the same game through their graphical
front ends, answering from one recorded list, and every frame either draws is hashed; the two lists must be
identical (this covers the menu, store, trail, rivers, hunts, rafts, tombstones, scores and every screen in
between, on a clock that only the game's own sleeps advance):

    test/gfx_compare.sh ASSETS FIRST LAST [--preset] [--wander]     # one game per seed, in parallel (JOBS=n)
    test/gfx_compare.sh assets 0 99                  # a themed (plain-colour) folder
    test/gfx_compare.sh ../python/assets 0 99                         # the Apple's own colour rules (font only)

`test/browser_play.py` drives a real browser (Playwright) through a recorded game on the built page (see its header). `test/gfx_hunt_raft.mjs` and `test/gfx_hunt_raft_py.py` compare the hunt and the raft scene by themselves.

## What this shows, and what it does not

It shows that the game's logic, with its draw order, its evaluation without short-circuits, its odd `FOR` loops
and Applesoft's rounding, ports to another language and reproduces the original's games, not only the
rebuild's; and that the screens, as the BASIC lays them out, come out the same dot for dot. The Python rebuild
was the reference while this was written, so it does not by itself show that someone could write the game from
the paper alone. Hunting is the paper's own approximation (animal movement and hit testing were never
analysed), in Python and here alike. The browser shell itself (canvas, key events, WebAudio, the file picker and
IndexedDB) is tested by driving a real browser through whole games, not by the seed comparisons.
