# The Oregon Trail on the Apple II (1985): An Analysis of Source, Data and Algorithms for Replication in Other Languages

By G. Paganelli - rift-demote-fence@duck.com

**This repository is primarily a research paper on  *The Oregon Trail*
for the Apple II**, specifically version 1.4, the 1985 MECC release by R. Philip Bouchard (design), John Krenz
(lead programmer), Charolyn Kapplinger (art), with Shirley Keran, Bob Granvin,
Roger Shimada and Steve Splinter.

The question the paper asks is simple: **can anyone else write this game again
based on this paper and its artefacts, and get the same behaviour?**

The paper answers it by documenting the actual BASIC code, the machine code, variables, algorithms, tables, and various data. It also finds the places where the documented behaviour and the program behaviour disagree.

---

## The paper

| | |
| --- | --- |
| [`paper/01-paper.md`](paper/01-paper.md) | The paper. Fourteen sections covering set-up, the daily cycle, health, weather, the fifteen random events, rivers, forts, trading, endings, the two arcade games, and what the Applesoft ROM does to every number. |
| [`paper/01-paper.docx`](paper/01-paper.docx) | The same paper as a Word document. |
| [`paper/02-appendix-d-dialogue.md`](paper/02-appendix-d-dialogue.md) | Appendix D — the 51 dialogue records, as a research extract. |
| [`paper/03-appendices-e-to-h.md`](paper/03-appendices-e-to-h.md) | Appendices E–H — the data tables decoded from `VAR.BIN`, the `&` command reference, the exact order of the random-number draws, and what is still missing. |
| [`paper/04-review.md`](paper/04-review.md) | An independent review of the paper, checking its claims line by line against the source and, for section 12, by **executing** the ROM. |

`paper/` is the reference and is not modified by this work. Where this translation
disagrees with it, the BASIC listing decides and the disagreement is recorded in
`FINDINGS.md` with the line number; none of the paper's text, dialogue or game data is
reproduced here beyond what the analysis needs to cite.

### The short version of what the paper found

- **The game is a daily simulation with one number for everything.** A single
  health value, seven penalties a day, and the party is best described as a wagon
  losing a fight with a continent.
- **The random-number sequence is the game.** Every chance decision is a comparison
  against an `RND` value, so reproducing the game means reproducing *when* each
  number is drawn — which is why Appendix G lists the order of every draw.
- **At most one event fires on a travelling day.** `L8 = 20` ends the body of the
  loop at line 3180, and Applesoft has no block structure, so an `IF ... THEN` clause
  runs to the end of the line. Line 3180 is
  `IF B > 0 THEN GOSUB 4000: GOSUB 300:L8 = 20`, so `L8 = 20` is inside the `THEN` and
  runs only when an event has fired *and* `B` is above zero. On an ordinary day `B` is
  zero, the clause is skipped and the loop goes on to the next event, so **several
  events can fire on one day**, each spending its own draw.
- **Applesoft has no short-circuit evaluation.** `IF X AND RND(1) < V` spends a
  number even when `X` is false. Several rules depend on it.
- **The arithmetic cannot be reimplemented in a host language.** Section 12 shows
  that the rounding points, the single guard byte, the decimal-literal conversion
  and the generator all live in the Applesoft ROM, and that Python, float32 and
  `decimal` all diverge from it. A constant is converted from its digits **every time
  the statement runs** — the programs cache 0 to 4 and 0.5 in variables for speed, not
  for correctness — and the conversion is still the ROM's, so `.8` is
  `80 4C CC CC CD` and not the nearest float. Likewise the sign comparison of the
  floating-point routines is the ROM's, in the outer entries `FADD $E7BE`, `FSUB $E7A7`,
  `FMULT $E97F` and `FDIV $EA66`, not something the transcription performs.
- **Several probable bugs are load-bearing.** The eleven listed in section 13 are the
  only ones this transcription reproduces, and it reproduces nothing else it has not
  traced back to a line. A broken arm has no effect, because injury number 0 *is* the
  value that means healthy. A thief never takes money. February always has 28 days, in
  a leap year. An accepted trade rounds the holding, and prints nothing when there is
  nothing to trade.

---

## History

How the work went, month by month.

- **March 2025** — Extracted the Applesoft BASIC files from version 1.4 and converted
  them into `.txt`; analysis of the Applesoft BASIC files.
- **April 2025** — Modified the Applesoft BASIC files to extract various data; hacked
  the BASIC files to accelerate the game and observe it under different conditions.
- **April 2025** — Used Google Gemini 2.5 Pro to attempt to determine the purpose of
  the variables, and of `PEEK` and `POKE`.
- **April 2025** — First attempt to code a simple Python version of the game without
  AI.
- **April 2025** — Second attempt to code a simple Python version of the game with
  AI.
- **June 2025** — First draft version of the paper, written by hand with the help of
  Google Gemini 2.5 Pro.
- **September 2025** — Used Google Gemini 2.5 Pro to analyse the BASIC code and the
  variables in depth, with the aid of the game's engineer's book.
- **February 2026** — Second draft version of the paper, mostly corrected by Google
  Gemini 3.1 Pro, with all the findings gained so far.
- **October 2026** — First official version of the paper, reviewed and corrected by
  Claude Opus 5.5 (Medium), which includes an analysis of the assembly code by Claude.
- **October 2026** — First attempt to create a Python-based version of the game, based
  on the paper and the related artefacts, using Space Bunny Alpha.

---

## The Python translation

> **This is secondary.** It exists to **prove the paper's findings are correct**,
> not to be a better game.

A from-scratch Python transcription of the release 1.4 BASIC, one module per
program and library, with every function commented with the line numbers it
implements. Two things about it are worth knowing, because they are the paper's
own argument made real:

1. **All arithmetic is performed by a genuine Apple IIe ROM** running under a
   py65 6502 emulator. The game never holds a host float: it passes five bytes into
   emulated memory and calls the ROM's own `FADDT`, `FMULTT`, `FDIVT`,
   `ROUND.FAC`, `INT` and `RND`. That is the only way to reproduce the original,
   which is what §12 argues.
2. **The ROM answered questions the paper could only describe.** The two `RND`
   constants, read out of the image; the operator entry points' calling
   conventions; the guard byte each routine leaves; and the `& INP` allowed-set
   syntax. Where the code and the paper disagreed, the code won. `FINDINGS.md`
   records every such case with the evidence.

### What the translation confirmed, item by item

| The paper says | The code checked |
| --- | --- |
| `RND` multiplies the seed by one constant and adds another (§12.3) | `$EFA6` = `98 35 44 7A 68`, `$EFAA` = `68 28 B1 46 20`. The addend's fifth byte is the opcode of the `JSR` at `$EFAE`. |
| fifteen `RND` values from seed `81 00 00 00 00` (§12.6) | all fifteen reproduced, and the final seed `7F 11 0D 1F 95` |
| `.8` is `80 4C CC CC CD`, `.2` is `7E 4C CC CC CD` (§12.2) | produced by the ROM's own decimal conversion, not by a Python literal |
| `ROUND.FAC` rounds when the guard byte is 80 or more (§12.2) | `7F 4C CC CC CD` becomes `… CE` at guard `$80`, unchanged at `$7F` |
| `1/3 + 1/3 + 1/3` under one (§12.4, rounding points) | `0.9999999997671694` |
| more than one event can fire on a day (§8.1) | line 3180's `L8 = 20` is inside `IF B > 0`, so the loop only stops early once `B` is above zero |
| `Q` and `Q()` are different variables (§2.5) | separate fields; a fort purchase no longer disturbs the map |
| a `FOR` always runs its body once (§2.5) | `FOR L = 1 TO X` with `X = 0.5` gives one draw, so half an ox is one draw |
| the route is 1,771 miles to The Dalles, 1,871 with the Barlow Road (§4.1) | segments 0–7, 10–14 and 16 sum to 1,771; Fort Walla Walla gives 1,821, and segment 18 adds 100 to either, for 1,871 and 1,921 |
| `LM$` and `LM()` come from `VAR.BIN`, Tables 7 and 8 (§4.1) | every field transcribed and checked by `tests/test_landmark_tables.py`, which is how the type of landmark 0 and the name of landmark 9 were found to be wrong |
| the `RND` constants are of magnitude 1.19 × 10⁷ and 3.9 × 10⁻⁸ (§12.3) | decoded from `$EFA6` and `$EFAA`, the implied top bit included |
| the routing bug that makes "an ox" and "a wheel" (§13) | reproduced |

### What the translation found that the paper did not say

- The climate zone is set from the **landmark**, so the segments per zone are
  0–2, 3–5, **6–11**, **12–14**, 15–18 — the paper's table gives landmark numbers
  where it means segment numbers.
- `ON B > 0 GOTO 4000` at line 1015 is load-bearing: fording the Green River at
  twenty feet always takes the last oxen, and the party is then held at the action
  menu until a trade supplies more. The table is right; the consequence is not
  stated anywhere.
- Event 2 dispatches to `10200`, a line the program does not have. `RE(2) = 0`, so it
  cannot be reached, but the original would raise UNDEF'D STATEMENT.
- An accepted trade rounds the holding, because `TRADE.LIB` sets the scalar `Q` to
  `INT (I(X + 2) + .5)` and then stores `Q - V`. Five and a half oxen that trade one
  away leave five. The original does this; `Q` and `Q()` being separate variables is
  why it does not also corrupt the map.
- The three rules in §2.5 are the ones most easily got wrong, and all three had been
  violated before this translation was re-audited line by line. `FINDINGS.md` §16
  records the sweep and what it changed; §17 records a second pass over the action
  menu, which found that retracting a claim is not the same as fixing the code: the
  buy option was still reachable from the trail menu, and "Check supplies" matched
  no handler at all.

Full record, including the places the code is an approximation and what is still
unfinished, in **[`GAPS.md`](GAPS.md)**. The module map and every ambiguity in the
source are in **[`PLAN.md`](PLAN.md)**.

---

## Installing the Python code

The code needs Python 3.12 or later and one small dependency, `py65`. It also
needs **an Apple IIe ROM image**, which is Apple firmware and is *not* distributed
here.

```fish
git clone https://github.com/payrings/theoregontrail.git
cd theoregontrail

python -m venv .venv
source .venv/bin/activate.fish          # fish; on bash use .venv/bin/activate
pip install -r requirements.txt
```

Then get a ROM image — for example:

```fish
mkdir -p rom
curl -o rom/apple2e.rom https://a2go.applearchives.com/roms/apple2e.rom
```

Check that the arithmetic engine came up:

```fish
python -m oregon --list
```

```
arithmetic backend : apple2e-rom
Apple IIe ROM      : .../rom/apple2e.rom (32768 bytes)
```

### Playing it

```fish
python -m oregon            # play it
python -m oregon --demo     # watch it play itself to Oregon, quietly
```

Type the number of a choice and press Return. Press **Return** during the journey to
stop and open the action menu, which is what the original's "press RETURN to size
up the situation" does.

Useful options: `--seed N` replays a specific game, `--trace FILE` writes one line
per game day, `--inputs FILE` plays from a list of answers, `--data DIR` chooses
where the two save files live, `--num pure` selects a faster arithmetic backend that
is **not** bit-exact, and `--no-interrupt` stops travel being interruptible.

### Tests

```fish
python -m pytest -q          # 134 tests
python tests/pty_check.py     # types at the game through a terminal
python tools/parity_check.py # the ROM against pure Python, operand by operand
```

`tools/parity_check.py` is section 12.4 of the paper made runnable: it compares
the emulated ROM with a host-language implementation over thousands of operand
pairs, so a reader can see the divergence rather than take it on trust.

No test compares against a recorded run of the original, because none exists
(Appendix H). Every expectation is worked out by hand from the BASIC line beside it,
and the tables are checked against numbers the paper prints independently of the
table.

---

## What is not in this repository

- **Appendices with the BASIC code and machine code** — the release 1.4 source listings, the on-screen text
  and the machine-code listings. They are MECC's and Apple II emulator material and
  are not redistributed here. Everything the paper and the code say about them is
  cited by line number so a reader with the disk can check it.
- **The Apple IIe ROM image** — Apple firmware, obtained as above.
- **The dialogue** — read at run time from `paper/02-appendix-d-dialogue.md`.

`GAPS.md` is the honest list of what is approximated, replaced or unfinished in the
translation. The paper is the document that matters; the code is the evidence.
