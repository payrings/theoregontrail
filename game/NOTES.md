# Notes on the Python rebuild

The paper in `../paper/` is the research. This folder is a Python translation of the
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
  Appendix E) and checked field by field in `tests/test_landmark_tables.py`.
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
| Graphics, pictures, the map and sound | Replaced by text. The picture formats were not decoded (paper Appendix H). |
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
to play themselves and print each day's values (paper Appendix H), and compared with
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
