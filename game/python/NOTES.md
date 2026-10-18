# Notes on the Python rebuild

The paper in `../../paper/` is the research. This folder is a Python translation of the
1985 Apple II game, written to test whether the paper is enough to rebuild it. This
file records what the translation does and does not reproduce, and what the
comparison between the two arithmetic backends showed.

Where the code and the paper disagree, the BASIC listing of release 1.4 decides.

## 1. What is reproduced

- **The rules.** Set-up, the store, the daily cycle, health, weather, the fifteen
  random events, illness, rivers, forts, trading, hunting rules, the raft, the three
  endings, scoring and the top-ten list, translated line by line from the listing.
- **The data.** Landmarks, segment distances, climate rows, river data, prices and
  event probabilities are transcribed from `VAR.BIN` (paper Tables 7 and 8,
  Appendix D) and checked field by field in `tests/test_landmark_tables.py`.
- **The arithmetic** (`--num rom`, the default). Every add, subtract, multiply,
  divide, `INT`, `RND`, decimal literal and number-to-text conversion runs in a real
  Apple IIe ROM under the py65 6502 emulator. The game holds its numbers as five
  Applesoft bytes. Host floats are used only to show or record a value (the trace and
  the daily summary) and in the hunt, which draws no number from the generator.
  Where the interpreter rounds (when a value is stored in a variable or pushed as the
  left operand of an operator) the code rounds too, and the formulas are checked
  against the interpreter's own results in `tests/test_fidelity.py`.
- **The arithmetic without the ROM** (`--num exact`). The same routines, transcribed
  into Python from the disassembly (`oregon/applesoft/exact.py`): `FADDT`, `FSUBT`,
  `FMULTT` with its zero-byte quirk, `FDIVT`, `ROUND.FAC`, `INT`, `FCOMP`, `FIN` and
  `FOUT`, on the ROM's own working cells. `tests/test_exact.py` holds it to the ROM
  operand by operand, and `tools/exact_check.py` repeats the paper's larger comparison.
- **The random sequence.** The two `RND` constants are read from the ROM image
  (`98 35 44 7A 68` and `68 28 B1 46 20`). Seed `81 00 00 00 00` gives 0.4072949117
  first and seed `7F 11 0D 1F 95` after fifteen draws.
- **The order of the random draws**, including those the game spends on the river
  animation (106 always; then 122 for a clean crossing, 66 for a failed ford, none
  for a failed ferry or float).
- **The original's bugs**, on purpose (paper section 13): no illness while waiting
  at a river; the uncapped starve factor; error 53 after 2055; the wrong century
  after 1899; the broken arm that does nothing and clears an illness; the thief who
  never takes money; the unused Portland climate row; the Barlow toll refused when
  the money equals it (and the party returned silently to the choice); February always 28 days; the trade that rounds the holding;
  the theft that takes nothing and shows no message.

## 2. What is not reproduced

| What | Status |
|---|---|
| Graphics, pictures, the map and sound | Replaced by text. The picture formats were not decoded (paper Appendix G). |
| Hunting: animal movement and hit testing | **Approximated.** This part of the machine code was not analysed. `hunt.approximate_movement` decides whether a shot hits by a simple rule of its own. Spawn rules, weights, bullets, meat and the carry limit follow the listing and the machine code, including the comparison at $E161 that tests only the low byte of the draw, so an animal appears 8 times in 1,000 attempts (paper Table 23). |
| Rafting | The loop and the loss rules follow the listing; the display is text and the speed is not paced to a 1 MHz machine. |
| Number-to-text conversion (`STR$`, `PRINT`) | On the ROM backend it is the ROM's own `FOUT` ($ED34): nine significant digits, rounded, and no space before a positive number. `tests/data/str_cases.json` holds 327 values recorded from it. The `exact` backend transcribes `FOUT`; the `float` and `rounded` backends follow the same rules and can differ in the ninth digit. |
| The extension byte inside an expression | Carried as the interpreter carries it: the left operand of an operator is rounded by its own extension byte, the right operand keeps its own, and the result of an expression is rounded when it is stored. `num.Chain` and `num.store` mark where an expression ends; a local that stands for a BASIC variable is stored explicitly. |
| Disk handling | No disk. Side changes are a prompt. Each side's `TOMB.SEQ` is kept as `side1/TOMB.SEQ` and `side2/TOMB.SEQ` in the data folder, written and read as `TOMB.LIB` does (offset 0 written whole, records read at 0 and 49). |
| Screen layout | The travel screen prints label and value pairs, one per line. |
| Key timing | A Return that ends the wait at an event message sets `B` and opens the action menu, as on the Apple II (lines 710, 905, 570, 42100). Keys typed during travel are read only at the two daily checks (lines 3100 and 3190), not at the exact moment the original would see them. |
| Applesoft errors | OVERFLOW (69), DIVISION BY ZERO (133) and ILLEGAL QUANTITY (53) end the game with the original's message and return to the menu. When the error comes from the arithmetic the message gives line 0, because the rebuild does not track BASIC line numbers. |
| No oxen | As in the original (lines 21000, 1015 and 3180): `B` is set to 2 and the action menu opens until oxen are obtained. |
| Number-to-text conversion under `--num exact` | `FOUT` ($ED34) transcribed; the same text as the ROM's for 20,000 values in `tools/exact_check.py`. |

**Two traces from the original game.** Seeds 1234 and 10190 of the preset start were
played by the original in the LinApple emulator, from copies of the disk images changed
to play themselves and print each day's values (paper Appendix G), and compared with
`--preset --demo --seed N --num exact --trace FILE`: every logged value of every day
agreed, including the seed bytes (158 and 196 days). The first comparison found two
departures, both corrected: the event chances of line 3160 are recomputed on a stopped
day, and `I(8)` is copied from `PF` only when the daily loop ends (line 3499). The two
games include no hunting, trading, fort purchases, resting or raft. Every other test
expectation was worked out by hand from the BASIC line it names.

## 3. ROM arithmetic against simpler arithmetic

The full account, with tables and figures, is section 12.7 of the paper.

**Question.** If a version keeps the rules and the random sequence but does its sums
differently, is it the same game?

**Method.** Every seed number from 0 to 65,535 was played with `--num rom` and with
each of `--num exact`, `--num rounded` and `--num float`: 262,144 games. Preset start
(carpenter, 1 April 1848, 9 yoke of oxen, 2,000 pounds of food, 10 sets of clothing,
50 boxes of bullets, 3 of each spare part, 50 dollars). The preset is written into the
game's state, so it skips the draws of the name shuffle and of the store. It also
makes the opening draws of lines 29000 and 29004 twice (`apply_preset` loads the trail
state, and `main` loads it again), so the journey starts two draws further along the
sequence. It is not a position that purchases can reach: a seed here labels a random
sequence, not the game the original would play from that counter value. The game
plays itself with `--demo`: it never hunts, rests, buys or changes pace or rations; at
a river it fords under 2.5 feet, otherwise takes a ferry or guide if offered,
otherwise floats. Each game is compared day by day with the ROM's game of the same
seed, on the 26 values the trace prints (to four to eight significant digits) and the
five seed bytes.

**Repeated seeds.** 2,653 seed numbers give the same random sequence as the number
half their size (paper 12.6), and so the same game under every arithmetic. Leaving
them out gives 62,883 games, which the figures below count. Later merges repeat 94 to
148 more; counting distinct games instead moves no share by more than 0.02 of a point.

| Backend | Identical every day | Same ending | Same score | Arrived (backend, ROM) |
|---|---|---|---|---|
| `exact` (transcription of the ROM) | 100% | 100% | 100% | 22.86%, 22.86% |
| `rounded` (floats rounded to 32 bits) | 89.81% | 100% | 100% | 22.86%, 22.86% |
| `float` (plain 64-bit floats) | 45.11% | 98.44% | 97.34% | 22.73%, 22.86% |

**Reading.**

- Only the ROM's arithmetic, run or transcribed, reproduces every game.
- Rounded floats end every game as the ROM does, with the same score; one game in ten
  differs on some day in a last digit. In the seeds 0 to 999, where first differences
  were traced, 99 of the 103 games that differ first differ in the last printed digit
  of `FS`: the ROM adds the literal `.8` with its extension byte.
- Plain floats change the course of more than half the games, but the ending of only
  1.56% (533 arrive only under the ROM, 449 only under plain floats), and make the game
  very slightly harder (McNemar z = 2.68, p = .007).
- So a bit-exact copy needs Applesoft's arithmetic (paper section 12), and simpler
  arithmetic changes the game's difficulty very little.

**Limits.** One starting position and one way of playing. The low arrival rate
belongs to the demo player, which never hunts, buys, rests or changes pace. The first
difference is found on printed values, so a difference hidden by the printing is not
seen. Every arithmetic compared is the rebuild's, not the original.

**Files.** `compare_csv.py` writes `games.csv` (one row per game) and `pairs.csv`
(one row per seed) to the folder it is given, one subfolder per backend when several
are named; the full run takes many hours and its output is not kept in the
repository. `summarise_csv.py` prints the main figures of a run. `sample_games.csv`
and `sample_pairs.csv` hold a small sample in the same format.

## 4. Running it

All commands are run from this folder.

```
python -m oregon                      # play
python -m oregon --demo               # watch it play itself
python -m oregon --list               # show the arithmetic backend and the ROM
python -m pytest -q                   # the tests
python compare_csv.py 0 65535 8 results exact,float,rounded
                                      # the experiment: the ROM against the other
                                      # arithmetics, eight worker processes
python summarise_csv.py results/exact results/float results/rounded
```

Options: `--seed N` replays a game, `--num rom|exact|float|rounded` chooses the
arithmetic,
`--preset` skips the set-up, `--trace FILE` writes the daily trace, `--data DIR`
chooses where the two save files are kept.

The Apple IIe ROM image is Apple's and is not distributed. Place it at
`rom/apple-rom`.


## The graphical mode (`python -m oregon --graphics`)

`oregon/graphics/` is a second implementation of the `UI` interface. It models the
`&` package: a text window, a cursor, proportional letters (advance = width + 2
dots), nine dots to a line, word wrap (a word moves to the next line when
`cx + width > window width - 1`), boxes and pictures. Pictures are PNG files in an
assets folder; the font is `font/font.png` with `font/font.json`.

Screens with their own layout (`graphics/screens.py`), and how each was checked
against screenshots of the original:

| Screen | BASIC lines | Checked |
| --- | --- | --- |
| title menu | MENU 1000-1015 | dot for dot |
| the five information screens, colours, Control-S | MENU 7000-7500 | dot for dot |
| the party's names | MENU 6015-6040 | dot for dot, apart from the input cursor |
| Matt's two introduction screens | BUY SUPPLIES 2010-2030 | dot for dot |
| the price list and the oxen, food, ammunition and spare-parts screens | BUY SUPPLIES 3000-3030, 400-810 | dot for dot, apart from the input cursor |
| framed message over a landmark picture | COMMON.LIB 41000 | dot for dot |
| pace, food rations, advice from a townsperson, Your Supplies, a trade offer, the fort's price list, the action menu | PACE.LIB, RATION.LIB, TALK.LIB, OREGON TRAIL 4005-4110, TRADE.LIB, BUY.LIB | dot for dot, apart from the input cursor (Your Supplies differs by one dot) |
| the map with the route | OREGON TRAIL 4200, MAP.LIB 50000-50010 | 18 dots differ (see below) |
| the travel screen and the "From ... it is ... miles" message | OREGON TRAIL 300-320, 2200, 3246 | dot for dot (see below for one unexplained screenshot) |
| the arrival question over the scene, the South Pass arrival | OREGON TRAIL 1005-1006 | dot for dot, apart from the input cursor and a few dots at the frame's right edge (28 and 55 dots) |
| event boxes over the scene: snow, blizzard, thunderstorm, hail, wild fruit, thief, fire, ox, impassable trail with a second box for an illness | OREGON TRAIL 10000-11400, COMMON.LIB 700 and 900 | dot for dot for the blizzard, the ox and the thief (5 dots); for the impassable trail and the illness the facts panel and the second box agree and the first box's text sits one dot too far left |
| the rest prompt | OREGON TRAIL 4500 | 18 dots differ (frame edge) |
| the broken wagon part: question and result | PART.LIB 42000-42030 | 2 dots differ; the wagon picture is not among the image tables on the disks and is supplied with the assets |
| the river: crossing page, menu, ferry offer, animation | RIVER.LIB, CROSS.LIB | page and menu dot for dot, the ferry offer apart from the cursor; the animation screenshots were taken part-way through, so only the frame and the water are compared |
| the river's information pages, the camp, the refusals, the guide's offer, the failed ford | RIVER.LIB 50020-50145, CROSS.LIB 50060 | built from the listing, not compared |
| the tombstone and the epitaph | TOMB.LIB 50010-50105 | dot for dot for the stone with a name; 34 dots differ with an epitaph and the closing message |
| the flip requests | FLIP.LIB | side 2: dot for dot below the scene; side 1: 8 dots at the bar's left edge |
| the management options (Control-A) | MANAGEMENT 1000-1015 | 1 dot differs |
| the landmark picture with its name strip | OREGON TRAIL 300-305 | dot for dot |
| the trade offer | TRADE.LIB | dot for dot, apart from the input cursor |
| the arrival at Oregon, the congratulations box and the points table (with the profession's multiplier) | WIN 600-622 | compared with a recording: the table to 19 dots (the mouse pointer), the congratulations box to about 100 dots (the picture's colours at the box's black margin) |
| the Columbia raft: the two instruction boxes, the river, the raft, the rocks and the direction signs | FLOAT 1000-1180 | compared with a recording: the river, raft and rock pictures to the dot (the raft at its square 9, a rock at the screen position the listing gives); the instruction box to about 130 dots. Not compared: a collision, the shore, the landing |
| hunting instructions and result, the Top Ten, the three points pages, The Dalles menu | HUNT.LIB, MENU 2000-2230, END.LIB | built from the listing, not compared |
| sound switch, clothing, Matt's remarks, the two messages before the store | MENU 2300, BUY SUPPLIES 600, 5000-5020 | not yet compared (the box itself is checked) |

Lines drawn with `HPLOT ... TO` follow the ROM's line routine (`HLIN`): one step across or one
step down at a time, never both, `dx + dy + 1` dots, the error term starting at `dx - dy`.
The route on the map matches the screenshot this way and not with the usual diagonal line.

The picture of the approaching landmark is drawn at `IX = FX - 2 * D`, moving four dots
at a time, with `FX = 180 - offset` (Table E5; the offsets agree with the saved variable
table). Screenshots at 22 miles and at arrival match this dot for dot. One early screenshot
(82 miles, 20 miles travelled) shows the river further right than the formula gives and is
not explained; a second one at the same distance agrees with the formula.
The 'bottom line' of line 950 is at y = 182 and
that of `& SPACE` at y = 184; the graphical `wait_key` takes either.

Everything else is printed in the same font on a black screen. `tests/test_graphics.py`
runs on a made-up set of pictures, so it needs no assets.

**Timing.** Each day's scene stays on the screen for a second at a steady pace, half a second
at a strenuous pace and 0.3 s at a grueling one (`trail.DAY_SECONDS`); Return during that time
opens the action menu. The wagon is shown at each four-dot step. A river crossing shows each
line of its animation and holds the picture for a second between its stages.

**The raft.** The river, raft, rock and sign pictures (`float_raft.png`, `float_rock.png`,
`float_sign.png`, with the river itself from `b_river`) were copied from a recording; with the
instruction picture (`l16`) they are in the assets, not in the program. A pass of the loop takes
about 0.45 s on the original (the game here runs it twice as fast, `raft_scene.PASS_SECONDS`), measured from the rocks' steps (the paper's estimate of a few thousand
passes a second is for the machine code alone and does not describe the game). The signs enter
at (114, 168) and move six dots right and three up a pass; the raft is at (84 + 8 hp + 3, 5 hp - 6)
and a rock at (RX + 7, RY). The arrival point is `& IMAGE,6` (FLOAT 1146, 1149): it enters at (-8, 218) on pass 175 and moves six dots right and three up a pass, crossing the landing bank around passes 205-225. Its picture, `float_landing.png`, is two wavy wagon ruts redrawn from a screenshot of the original, not copied pixel for pixel. Not verified: the drawing order of the raft and a rock that overlap,
the sign's first pass (the recording shows it a few passes after the listing's 60, 120 and 170,
because a pass that draws more rocks takes longer), and the screens of a collision.

**The hunting field.** With a `hunt/` folder in the assets, `graphics/hunt_scene.py` draws the
hunter's eight poses, the trees and grass and the four animals from sprites copied off
screen recordings of the original; the keys, the spawn rule, the animals allowed at each
landmark, the weights and the two-animal and four-shot limits are the paper's. Taken from
the recordings: the sprites, the walking speeds and the hunter's walk. **Not verified:** how
the animals choose their paths, the bullet's speed, what the arrow keys do (here they turn
the rifle a step), the placing of the scenery, and the length of the hunt (25 s, not 2,500
passes). Without the `hunt/` folder, `graphics/hunt_field.py` draws plain shapes instead.


## Themed (full-colour) assets

A folder with `theme.json` switches off the Apple colour rules (`graphics/canvas.py`): text dots
take one plain colour (`text_colour`), boxes and lines use the theme's `colours` on every column
(no odd-column plotting, no fill-in dots), and an inverse letter cuts ink out of a panel rather
than letting the picture show through. A themed folder may also hold full-colour backgrounds in
`screens/` (`backdrop_default`, `backdrop_sky_<side>`, `backdrop_ground_<1|3|5>`, `backdrop_hunt`)
and a hunting file whose sprite rows use one letter per colour (`colours.palette`). Without
`theme.json` nothing changes: the original colours, the original rules.


## Sound (graphical mode)

`graphics/sound.py` plays two tunes of its own, written as soft 8-bit triangle waves and handed to the
system's audio player (`pw-play`, `paplay`, `aplay`, `afplay`, `ffplay` or `play`; `winsound` on
Windows; silent, with one message, if there is none). The BASIC calls `& PT` in two places only:
the wait for a key (`955`: tune 1, repeated until a key; here a two-second jingle, looped) and a
raft collision (`740`: four runs of tune 1; here four soft whumps (low noise, sinking a little), about two and a half
seconds in all). The original tune data lives in a disk
file that is not here, so the melodies are invented and their lengths are guesses. Memory byte
975 is the switch (menu choice 4, Control-S while waiting). Not verified: the original's tempo
and pitches; only the two events above are sounded.

**One tune a landmark.** The original loads a tune file each time it reaches a landmark (MAIN 1005:
`MS` + the landmark number + `.BIN`), `MS0` at the start, `TS.BIN` for the tombstone and `MS17`/`MS16`
at the end, and the key-wait plays whichever is in memory. `sound.TUNES` holds eighteen made-up
tunes and one for the tombstone, each fourteen steps long; `Sound.select` is called where the
original loads the file (`trail.run` on arriving, `tomb.all_dead`, `win.run`, `floatraft.landed`).

**Where the tune plays.** Only where the BASIC calls its own line 950, the one that reads `& PT,1,1`:
the landmark screen (MAIN 1010), the "From ... it is N miles to ..." screen (2200), the date bar on
arriving in Oregon (WIN 601) and the two tombstone waits (TOMB 50010, 50040). Every other
"Press SPACE BAR to continue" in the original is `& SPACE` (line 30000) and is silent, so
`GraphicalUI.wait_key` plays only with `tune=True` and the shop, menus, rivers and events stay quiet.

**Tune lengths.** The tune files on the disks give each tune's length (the pairs of pitch and
duration bytes, one duration unit being 256 passes of 23 cycles, about 5.76 ms): 8 s (MS11) to 37 s
(MS2), 16 s at the start and in Oregon, 19 s for the tombstone, and the raft's own tune (21 notes of
one unit, four times) about half a second. `graphics/tunes.py` composes a new tune of each length
from a seed, a key and a scale; only the lengths come from the disk files. A broken wheel is drawn by
`part_04.png` (the stopped party, the rear wheel gone); in the colour folder it replaces the team
instead of being drawn over it.
