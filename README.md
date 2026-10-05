# The Oregon Trail on the Apple II (1985): An Analysis of Source, Data and Algorithms for Replication in Other Languages

**This repository is primarily a research paper.** Its subject is *The Oregon Trail*
for the Apple II, the 1985 MECC release by R. Philip Bouchard (design), John Krenz
(lead programmer), Charolyn Kapplinger (art), with Shirley Keran, Bob Granvin,
Roger Shimada and Steve Splinter.

The question the paper asks is simple: **can anybody else write this game again
from the evidence, and get the same behaviour?**

The paper answers it by reading the actual program. From the release 1.4
Applesoft BASIC source and the saved variable table it recovers the game state,
the formulas, the constants, the probability tables, the message text and the
machine-language routines, and gives each with the line number that defines it.
It also finds the places where the documented behaviour and the shipped
behaviour disagree — including two mistakes in the analysis itself, corrected
by running the code.

---

## The paper

| | |
| --- | --- |
| [`paper/01-paper.md`](paper/01-paper.md) | The paper. Fourteen sections covering set-up, the daily cycle, health, weather, the fifteen random events, rivers, forts, trading, endings, the two arcade games, and what the Applesoft ROM does to every number. |
| [`paper/02-appendix-d-dialogue.md`](paper/02-appendix-d-dialogue.md) | Appendix D — the 51 dialogue records, as a research extract. |
| [`paper/03-appendices-e-to-h.md`](paper/03-appendices-e-to-h.md) | Appendices E–H — the data tables decoded from `VAR.BIN`, the `&` command reference, the exact order of the random-number draws, and what is still missing. |
| [`paper/04-review.md`](paper/04-review.md) | An independent peer review of the paper, checked line by line against the source and, for section 12, by **executing** the ROM. It recommends acceptance subject to revision, and its findings are folded into what follows. |

### The short version of what the paper found

- **The game is a daily simulation with one number for everything.** A single
  health value, seven penalties a day, and the party is best described as a wagon
  losing a fight with a continent.
- **The random-number sequence is the game.** Every chance decision is a comparison
  against an `RND` value, so reproducing the game means reproducing *when* each
  number is drawn — which is why Appendix G lists the order of every draw.
- **Applesoft has no short-circuit evaluation.** `IF X AND RND(1) < V` spends a
  number even when `X` is false. Several rules depend on it.
- **The arithmetic cannot be reimplemented in a host language.** Section 12 shows
  that the rounding points, the single guard byte, the decimal-literal conversion
  and the generator all live in the Applesoft ROM, and that Python, float32 and
  `decimal` all diverge from it.
- **Several probable bugs are load-bearing.** Nine are listed in section 13. A
  broken arm has no effect, because injury number 0 *is* the value that means
  healthy. A thief never takes money. February always has 28 days, in a leap year.

### Corrections the review forced

The review found two errors in the paper's own reasoning, and both were confirmed
against the source and fixed:

- **§8.1 claimed two events can fire on one day.** Line 3180 ends the loop body with
  `L8 = 20`, so `NEXT L8` gives 21 and the loop ends. It is **one event a day**.
  A day costs `k + 1` draws, where `k` is the index of the event that fired.
- **§12.2 said literals are re-converted every time a line runs.** Applesoft
  converts a literal once, when the line is tokenised.

The review also gave the paper its missing §12.6 evidence: fifteen `RND` values
from a known seed, and the seed they leave behind. Those are reproduced exactly by
the code below, which is a direct test of the paper's central claim.

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
   syntax. Where the code and the paper disagreed, the code won and the paper was
   corrected — see `FINDINGS.md`, which records all of it, including where the
   review corrected both.

### What the translation confirmed, item by item

| The paper says | The code checked |
| --- | --- |
| `RND` multiplies the seed by one constant and adds another (§12.3) | `$EFA6` = `98 35 44 7A 68`, `$EFAA` = `68 28 B1 46 20`. The addend's fifth byte is the opcode of the `JSR` at `$EFAE`. |
| fifteen `RND` values from seed `81 00 00 00 00` (§12.6, outstanding) | all fifteen reproduced, and the final seed `7F 11 0D 1F 95` |
| `.8` is `80 4C CC CC CD`, `.2` is `7E 4C CC CC CD` (§12.2) | produced by the ROM's own decimal conversion, not by a Python literal |
| `ROUND.FAC` rounds when the guard byte is 80 or more (§12.2) | `7F 4C CC CC CD` becomes `… CE` at guard `$80`, unchanged at `$7F` |
| `1/3 + 1/3 + 1/3` under one (§12.4, rounding points) | `0.9999999997671694` |
| one event per day (§8.1, after correction) | the event loop breaks after one |
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
- `Q` is one variable used as the map's landmark history *and* as a scalar by the
  fort and the trader, so a purchase loses the map's first landmark and an accepted
  trade rounds the player's holding: five and a half oxen become six.

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

- **Appendices X, Y and Z** — the release 1.4 source listings, the on-screen text
  and the machine-code listings. They are MECC's and Apple II emulator material and
  are not redistributed here. Everything the paper and the code say about them is
  cited by line number so a reader with the disk can check it.
- **The Apple IIe ROM image** — Apple firmware, obtained as above.
- **The dialogue** — read at run time from `paper/02-appendix-d-dialogue.md`.

`GAPS.md` is the honest list of what is approximated, replaced or unfinished in the
translation. The paper is the document that matters; the code is the evidence.