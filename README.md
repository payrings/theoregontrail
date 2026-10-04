# The Oregon Trail (MECC, 1985) — a rebuild in Python

A private research rebuild of the 1985 Apple II release, transcribed from the
release 1.4 Applesoft BASIC. Every arithmetic operation is performed by a genuine
Apple IIe ROM running under a py65 6502 emulator, so the numbers are the original's
rather than an imitation of them.

**This is not finished, and `GAPS.md` says exactly what is not.** Read it before
drawing any conclusion from a run. Nothing here is distributed, and the reference
material in `docs/` is copyrighted and is never committed.

---

## What is here

| Path | What it is |
| --- | --- |
| `oregon/applesoft/` | the arithmetic: a 5-byte `Fac` value, the emulated-ROM backend, and a pure-Python one |
| `oregon/num.py` | the only interface game code uses for arithmetic |
| `oregon/rng.py` | `RND` behind an interface, with a draw log for the Appendix G tests |
| `oregon/ui.py` | the screen and keyboard, in two implementations: terminal and scripted |
| `oregon/state.py` | one object whose fields are the BASIC variable names |
| `oregon/mem.py`, `errors.py`, `files.py`, `trace.py` | `PEEK`/`POKE`, the error handler, the two disk files, the day-by-day trace |
| `oregon/data/` | every table, in one place, checked against the paper by the tests |
| `oregon/trail.py` and the `*.py` beside it | the programs and libraries, one module each |
| `tests/` | 76 tests, all of them worked out by hand from the listing |
| `PLAN.md` | the module map and every ambiguity found |
| `GAPS.md` | what is approximated, replaced, missing or wrong — **read this** |

---

## Setting up

The shell here is **fish**, so every command below is fish syntax.

```fish
mkdir -p ~/.venvs          # only if you keep environments outside the project
cd /home/xfx/oregon
```

Create the environment (Python 3.14.7 is installed; anything 3.12 or later works):

```fish
uv venv --python 3.14 .venv
source .venv/bin/activate.fish
uv pip install pytest py65
```

or, without `uv`:

```fish
python -m venv .venv
source .venv/bin/activate.fish
pip install pytest py65
```

### The ROM image

The arithmetic backend needs an Apple IIe ROM. It is not in the repository; put it
at `rom/apple2e.rom`, or point `OREGON_ROM` somewhere else:

```fish
set -x OREGON_ROM /path/to/apple2e.rom
```

To fetch one:

```fish
mkdir -p rom
curl -o rom/apple2e.rom https://a2go.applearchives.com/roms/apple2e.rom
```

The loader checks the image is 32 KB and that `ROUND.FAC` at `$EB72` begins `A5 9D`,
so a wrong file is refused rather than quietly misbehaving. Without a ROM the game
still runs, on the pure-Python backend, which is **not** bit-exact — see `GAPS.md`
section 1.

---

## Running it

Everything is already set up in this directory: the virtual environment exists and
`rom/apple2e.rom` is in place. Just:

```fish
cd /home/xfx/oregon
source .venv/bin/activate.fish
python -m oregon
```

Then answer with the number of the choice you want, and Return. A crossing takes a
few seconds to a few minutes depending on how much you fiddle.

### Check it first

```fish
python -m oregon --list
```

prints which arithmetic backend is in use and which ROM image it found:

```
arithmetic backend : apple2e-rom
Apple IIe ROM      : /home/xfx/oregon/rom/apple2e.rom (32768 bytes)
```

### Watch a whole game without playing it

The quickest way to see it work. The demo plays itself, quietly, from the store to
the Willamette Valley — about 170 days and 1,921 miles, a few seconds:

```fish
python -m oregon --demo
python -m oregon --demo --verbose-demo      # and show the screens
```

Add `--trace` to get one line per game day, which is the format a reference trace
would be compared against:

```fish
python -m oregon --demo --seed 4242 --trace /tmp/trail.log
tail -3 /tmp/trail.log
```

```
# AD AM AY  D  M    H      FS      H0 HR W TM PP AR        AS PF   I2 I3 I4  I5 I6 I7 I8   MY      H1               H2              EVENT SEED
02 05 1848 82 20 0   0      0       0  0  2  2  0  2.12082  0  985 8  6  120 1 1 1 1000 1138   [0,0,0,0,0]     [0,0,0,0,0]     -     7e456c06b2
18 10 1848 0  1921 139  47.4672 0  20 3  3  0  0.008488 0  0   5  7  120 0 0 0 0   1125.5 [0,0,0,-1,-1]   [0,30,0,0,0]    -     804e9054f4
```

### Options

| Option | What it does |
| --- | --- |
| `--seed N` | fix the 16-bit seed, which the original takes from the keyboard counter at `$78`/`$79`. Any game can be replayed from a seed. |
| `--demo` / `--verbose-demo` | play itself, quietly or with the screens shown |
| `--trace FILE` | write one line per game day |
| `--inputs FILE` | play from a list of answers, one per line — nothing is displayed |
| `--data DIR` | where `HISCORE.SEQ` and `TOMB.SEQ` are kept (default `data/`) |
| `--num rom\|pure` | the arithmetic backend; `rom` is the emulated Apple IIe and the default |
| `--no-interrupt` | never break out of the daily cycle, so the party travels on regardless |
| `--list` | show the backend and the ROM, then stop |

### Playing it

Press **Return** at any time during the journey to stop and open the action menu —
that is the original's "press Return to size up the situation", and it works here
because the terminal is put into cbreak mode so a single keypress is read without
waiting for a newline. `--no-interrupt` turns it off, which is what you want when
piping input.

The prompts that take a *line* of text rather than a single keypress are the party
names and the epitaph.

### Played from a script

`--inputs` takes one answer per line. The order of the questions changes with the
route — taking the first branch at South Pass skips Fort Bridger and so asks one
question fewer — which is why matching answers by position is fragile. The demo
mode exists instead of a hand-built script: it answers each prompt by what the
game printed, and is the honest way to replay a game.

```fish
python -m oregon --inputs my-answers.txt
```

## Tests

```fish
python -m pytest -q
```

Nothing here is compared with an "expected output" from the original, because no
reference trace exists (Appendix H). Every expectation is worked out by hand from
the BASIC line named beside it, and the tables are checked against numbers the paper
prints independently of the table.

The parity tests need the ROM and skip without it.

---

## How to read the code

The BASIC is the reference and the module names follow it, so a listing and this
source can be read side by side. Every function carries a comment naming the program
and the line range it implements, and the arithmetic goes through `num` so that no
game module touches a float or a `math` call.

Two conventions worth knowing:

* **No short-circuit.** Applesoft evaluates both sides of `AND` and `OR`, so a `RND`
  on the right always happens. `LF.LIB` 50000 and 50205 and `FLOAT` 1070 all rely on
  it. The tests pin this down.
* **One event a day.** Line 3180 ends with `L8 = 20`, so at most one event fires. The
  paper says otherwise; the source has authority. `GAPS.md` A1.

---

## Licensing

The game, its text, its dialogue and its data are the property of MECC and its
rights holder. This rebuild is for private study and is not to be redistributed.
Nothing of theirs is committed to this repository: `docs/` is git-ignored, and the
dialogue is read from it at run time rather than copied into the source.
