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

```fish
python -m oregon
```

Useful options:

```fish
python -m oregon --list                       # show the backend and the ROM
python -m oregon --seed 4242                  # fix the 16-bit seed
python -m oregon --trace /tmp/trail.log       # one line per game day
python -m oregon --inputs script.txt          # play from a list of answers
python -m oregon --data ~/.local/share/oregon # where the two files are kept
python -m oregon --num pure                   # the fast, non-exact backend
python -m oregon --no-interrupt               # never stop the daily cycle
```

`--seed` takes the 16-bit counter the keyboard routine keeps at `$78`/`$79`, which
is the only reseeding in the game (`MENU` 1015). Any game can be replayed from a seed,
so this is what a reference trace would be recorded against.

### Played from a script

`--inputs` takes one answer per line, in the order the game asks for them. A bare
line means "Return", which is how the original reads most prompts. Nothing is
displayed. An answer list that runs out is an error rather than a repeat, so a
transcription bug shows up instead of hiding:

```fish
printf '1\nZeke\n\nY\n4\n1\n4\n2\n1200\n3\n6\n4\n6\n5\n1\n1\n1\n\n' > game.txt
python -m oregon --seed 4242 --inputs game.txt --trace /tmp/trail.log
```

---

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
