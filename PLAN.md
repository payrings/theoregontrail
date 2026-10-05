# PLAN.md — rebuilding The Oregon Trail (MECC, 1985, Apple II) in Python

The module map and the ambiguities found while transcribing. The paper itself is
in `paper/`; this is the working document behind the translation in `oregon/`.

Authority order used throughout: **Appendix X (BASIC source)** first, then the
paper, then Appendices D–H, then Appendix Z (machine code). Where the paper
disagrees with the code, the code wins and the difference is recorded in
`GAPS.md`.

---

## 1. What the sources give us, and what they do not

The BASIC for every rule, formula, table and message is available in
Appendix X. That covers: set-up, the store, the daily cycle, health, weather,
the fifteen events, rivers, forts, trading, talking, broken parts, fires /
thieves / abandoned wagons, tombstones, The Dalles, scoring and the top ten,
plus the whole of the BASIC part of the rafting game.

Three things are *not* available:

1. **The Applesoft ROM.** The paper (§12) is emphatic that no host-language
   arithmetic reproduces the original. Apple's ROM is copyrighted firmware.
2. **The machine-language parts**: `& HUNT` (the hunt) and the `&` commands
   used only by `FLOAT` (`PUTP`, `DPB`, the doubled `&` form, `USR`).
3. **The picture / image / tune data formats.**

### 1.1 How the parity requirement is met

The instruction is to use a Python Apple II emulator for algorithmic parity,
because Python arithmetic "will never get it right". Accepted — with the
following concrete mechanism, which the paper itself sanctions (§12.5, second
approach: *ROM routines called from Python*):

* A **6502 CPU emulator** (py65) executes the arithmetic. Every game operation
  is performed by 6502 code operating on 5-byte Applesoft values in emulated
  memory; the Python side never holds a host float for game state. This is
  literally the paper's recommended design, and it is the only way to honour the
  paper's warning about `math.isclose` and float32/float64 substitutions.
* Because Apple's ROM cannot be shipped, `oregon/applesoft/rom_arith.s` is a
  **6502 re-implementation of the documented Applesoft routines** (FADDT,
  FSUBT, FMULTT, FDIVT, ROUND.FAC, INT/QINT, the string conversions, and RND),
  written from the algorithms described in paper §12.2–12.3 and the published
  ROM disassembly comments that the paper cites. It implements the real
  algorithm: shift-and-add multiply, shift-subtract divide, alignment into the
  single extension byte with bits beyond it *discarded*, and rounding only at
  `ROUND.FAC` and at push points.
* The same routines are **also** implemented in pure Python
  (`applesoft/float32.py`) so that a full game can be simulated quickly. The two
  are held to bit-equality by a test that compares them over a large corpus of
  generated operands and operations. Where they ever differ, the 6502 one wins
  and the Python one is fixed.
* **If a real Apple II ROM is supplied** (drop the file in, pass `--rom`), the
  emulated 6502 switches to running the genuine ROM routines through the same
  interface. No game-logic change. The list of bytes I would like from a ROM is
  in §6 below.

So parity is *architecturally* achieved (right algorithms, right number format,
right rounding points, right RNG order) and is *empirically* complete the moment
the ROM constants are filled in. I will not claim bit-parity before then, and
`GAPS.md` says so.

### 1.2 Number format actually implemented

5 bytes, per paper Table 26 and §12.1:

* byte 0: exponent, value = significand × 2^(byte0 − 128); 0 means zero
* byte 1: sign in bit 7; the significand's implicit leading 1 is *not* stored,
  so bits 6..0 of byte 1 plus bytes 2–4 give a 31-bit fraction in [0.5, 1)
* plus the **extension byte** `AC` (guard byte), live only inside an
  expression, dropped when a result is stored

Overflow (|value| beyond the format) raises Applesoft **error 6 (OVERFLOW)**;
underflow gives zero. There are no infinities or NaNs.

---

## 2. Module layout

```
oregon/
  __main__.py        CLI: --seed N --trace FILE --inputs FILE --rom FILE --no-sound --auto
  num.py             THE numeric interface. Fac type, ops, str$/val/asc/mid, backend selection.
  applesoft/
    __init__.py      backend registry
    format.py        5-byte pack/unpack, extension byte, ASC/MID$ char codes
    float32.py       pure-Python bit-exact Applesoft arithmetic (fast path)
    rng.py           RND (algorithm documented; ROM constants isolated in ONE table)
    rom_arith.s      my 6502 re-implementation of the documented ROM routines
    cpu6502.py       py65 wrapper: assemble, call, marshal values in/out of memory
    rom.py           optional genuine-Apple-ROM backend (activated by --rom)
    pyfloat.py       host-float backend, differential testing only
  rng.py             RND *interface*: Seeded, Scripted, Counting, plus the draw log
  ui.py              UI *interface* + TerminalUI + ScriptedUI (the `&` commands)
  errors.py          ApplesoftError codes, the game's ONERR handler (COMMON.LIB 32000)
  mem.py             PEEK/POKE byte-level memory: 78/79, 900-917, 919, 955, 975, 1920+
  state.py           one State object, fields named as the BASIC variables
  files.py           TOMB.SEQ (two sides) and HISCORE.SEQ persistence
  trace.py           one line per game day, Appendix H field list
  data/              ALL tables, nothing scattered in logic
    landmarks.py climate.py rivers.py goods.py illnesses.py text.py hiscore.py dialogue.py
  menu.py       MENU (side 1) + MANAGEMENT + MENU (side 2)
  buysupplies.py BUY SUPPLIES
  trail.py       OREGON TRAIL lines 100-3499, 4000-4900, 8000, 10000-11400, 21000, 22000, 29000
  common.py      COMMON.LIB 30000-41100
  river.py       RIVER.LIB  + CROSS.LIB
  fortbuy.py     BUY.LIB
  trade.py       TRADE.LIB
  talk.py        TALK.LIB
  maplib.py      MAP.LIB
  pace.py        PACE.LIB
  ration.py      RATION.LIB
  part.py        PART.LIB
  lf.py          LF.LIB
  tomb.py        TOMB.LIB
  endl.py        END.LIB
  flip.py        FLIP.LIB (both sides)
  floatraft.py   FLOAT (the rafting game)
  win.py         WIN
```

Each function carries a comment naming the BASIC program and line range. `B`
(217 lines of it) is transcribed to `trail.py` in the same order as the
listing, so the two can be diffed by eye.

---

## 3. BASIC line → Python mapping

| BASIC | Python | Notes |
| --- | --- | --- |
| `MENU` 100–149 | `menu.boot` | sound flag, window setup |
| `MENU` 500 | `menu.input_name` | `& INP,9,"-AZ-az '.-",1,Z$` |
| `MENU` 1000–1020 | `menu.main_menu` | reseed at 1015, `ON A - 48 GOSUB` |
| `MENU` 2000–2235 | `menu.top_ten`, `menu.how_points` | DATA 29010 |
| `MENU` 2300 | `menu.toggle_sound` | `NOT PEEK(975)` |
| `MENU` 4000–4110 | `menu.profession` | 4030 money formula |
| `MENU` 5000 | `menu.flip_disk` | cosmetic |
| `MENU` 6000–6045 | `menu.party_names` | 10 draws, step-forward collision |
| `MENU` 7000–7500 | `menu.learn` | text screens |
| `MENU` 9000 | `menu.start` | `POKE 901,48` |
| `MANAGEMENT` 100–1015 | `menu.management` | options list |
| `MANAGEMENT` 200–305 | `menu.erase_tombs` | |
| `MANAGEMENT` 700–720 | `menu.reset_top_ten` | |
| `MANAGEMENT` 900–915 | `menu.show_top_ten` | |
| `BUY SUPPLIES` 100–199 | `buysupplies.init` | reads 900–914 |
| `BUY SUPPLIES` 200 | `buysupplies.money_str` | `V = INT(V*100+.5)` |
| `BUY SUPPLIES` 400–950 | `buysupplies.item_*` | 6 item prompts |
| `BUY SUPPLIES` 1000–1020 | `buysupplies.store` | `Z = (Z=0)*6 + Z` |
| `BUY SUPPLIES` 2000–2030 | `buysupplies.intro` | |
| `BUY SUPPLIES` 3000–3030 | `buysupplies.display` | |
| `BUY SUPPLIES` 4000 | `buysupplies.bill` | |
| `BUY SUPPLIES` 5000–5020 | `buysupplies.leave` | `MY = (MY-TB)*10` |
| `BUY SUPPLIES` 6000–6110 | `buysupplies.month` | `POKE 902, VAL(Z$)+2` |
| `OREGON TRAIL` 100–110 | `trail.init` | `LOMEM:39170`, VAR.BIN |
| `OREGON TRAIL` 190–260 | `trail.lib_remove`, `trail.money_str`, `trail.date_str` | |
| `OREGON TRAIL` 300–401 | `trail.travel_screen` | text status block |
| `OREGON TRAIL` 450–460 | `trail.find_grave` | `SN`, `ML`, `DL` |
| `OREGON TRAIL` 500–505 | `trail.run_stopped_days` | `D = 0` trick |
| `OREGON TRAIL` 550–570 | `trail.lose_days` | `INT(RND*Z+1)` |
| `OREGON TRAIL` 600 | `trail.flip_side1` | |
| `OREGON TRAIL` 650–660 | `trail.speed` | `BS`,`FC`,`OP`,`F0` |
| `OREGON TRAIL` 700–711 | `trail.message`, `trail.message_wait` | |
| `OREGON TRAIL` 800–820 | `trail.poll_key` | the travel interrupt |
| `OREGON TRAIL` 900–958 | `trail.box`, `trail.wait_key` | |
| `OREGON TRAIL` 1000–1016 | `trail.arrive`, `trail.main_loop` | |
| `OREGON TRAIL` 2100–2120 | `trail.choose_segment` | branch + map |
| `OREGON TRAIL` 2200 | `trail.load_segment` | `D`, `MD`, `NM` |
| `OREGON TRAIL` 3000–3060 | `trail.start_segment` | `SN`, `DD`, event chances |
| `OREGON TRAIL` 3100–3499 | `trail.daily_cycle` | the core loop |
| `OREGON TRAIL` 3500–3505 | `trail.river` | `W1 = 1` |
| `OREGON TRAIL` 4000–4095 | `trail.action_menu` | |
| `OREGON TRAIL` 4100–4110 | `trail.show_supplies` | `INT(I(L)+.51)` |
| `OREGON TRAIL` 4200–4900 | `trail.do_*` | menu dispatch |
| `OREGON TRAIL` 8000 | `trail.bury` | |
| `OREGON TRAIL` 10000–11400 | `trail.event_00` … `trail.event_14` | |
| `OREGON TRAIL` 11500–11505 | `trail.choose_victim` | |
| `OREGON TRAIL` 21000 | `trail.check_oxen` | |
| `OREGON TRAIL` 29000–29020 | `trail.load_state` | first 2 draws |
| `COMMON.LIB` 30000–33015 | `common.*` | error handler, disk-side check |
| `COMMON.LIB` 40000–41100 | `common.*`, `ui.box`, `ui.wait_key` | |
| `RIVER.LIB` 50000–50260 | `river.*` | |
| `CROSS.LIB` 50000–50110 | `cross.*` | animation draws (see GAPS) |
| `BUY.LIB` 50000–50035 | `fortbuy.*` | |
| `TRADE.LIB` 50000–50260 | `trade.*` | |
| `TALK.LIB` 50000–50010 | `talk.*` | |
| `HUNT.LIB` 50000–50020 | `hunt.*` | |
| `MAP.LIB` 50000–50015 | `maplib.*` | |
| `PACE.LIB` / `RATION.LIB` | `pace.*` / `ration.*` | |
| `PART.LIB` 42000–42100 | `part.*` | |
| `LF.LIB` 50000–53000 | `lf.*` | |
| `TOMB.LIB` 50000–51030 | `tomb.*` | |
| `END.LIB` 50000–50080 | `endl.*` | |
| `FLIP.LIB` | `flip.*` | |
| `FLOAT` 100–1000, 1070–1180 | `floatraft.*` | |
| `WIN` 100–1030 | `win.*` | |

---

## 4. Ambiguities, gaps and how each is resolved

### 4.1 Places where the paper is wrong and the code wins

| # | Paper says | Code says | Resolution |
| --- | --- | --- | --- |
| A1 | §8.1 "the remaining events are still tested, so two events can occur on one day" | line 3180 ends with `L8 = 20` after **every** firing event, so `NEXT L8` exits | **One event per day.** Reproduced. Recorded in GAPS.md. |
| A2 | §9.3 "Ford, rough: 16% chance of tipping, then each good has a 10% to 40% chance" | line 50070 draws `V = .1 + RND(1)*.3` **once**, then all six goods share it | one shared V per tipping; draw order = 1 (tip?) + 1 (V) + 6 goods draws |
| A3 | §9.4 / Table 19 "price is `V = V + .25*Q*V`" | identical, but `K = 1 + 19*(L = 3)` means ammunition is bought in **boxes of 20**; `I(L+1) += Z*K` | reproduce the box multiplier |
| A4 | §10.1 toll `$5 + 50c an ox` | line 50020 re-reads the *rounded* toll into `V`; exact-tie refuses | reproduced |
| A5 | §11.1 "at most two animals on screen; 2500 passes" | Appendix Z confirms a 2-animal outer loop at `E0C4`–`E0EF`; the 2500 figure is not derivable from the bytes | keep 2500 as a documented constant of unknown origin |
| A6 | §7 "an injury subtracts 0.5; a second injury … is reported as a death" | line 10820 does exactly that | ✓ agree |
| A7 | §2.3 Table 4: address 904/905 = "bullets, low/high" at end of journey, "yokes of oxen" at start | correct; `END.LIB` 50050 POKEs `909 = I(2)+.5` (oxen) and 904/905 = bullets, then 50070 POKEs 910–912 = spares | reproduce both layouts exactly, including that `FLOAT` reads `I(2)` from 909 and `I(4)` from 904/905 |
| A8 | §5.5 "TOMB.LIB … reduces NP by one and swaps the dead member with the last living one" | also leaves `H2(NP)` stale and marks the corpse `H1 = -1` | reproduce |

### 4.2 Genuine ambiguities in the code

| # | Problem | Proposed resolution |
| --- | --- | --- |
| B1 | Line 29000 uses `FN W(0)`, which reads `WC$(ZO)`, **before** `ZO` is ever assigned by line 1000. `ZO` is not in the VAR.BIN variable list (Appendix E.1), so it is 0. | treat `ZO = 0` (climate row 0) at 29000 and 29004. Makes the initial `W`/`TM` use the Kansas City row whatever the departure month. Flagged in GAPS.md. |
| B2 | `B` is simultaneously the travel-screen column array `B(0 to 5)` (Appendix E.5) and the cannot-continue flag. `B = 2` overwrites `B(0)`. | model `B` as one Applesoft variable with indexed slots; use a private copy of the five label columns for the text status block so the display stays sane. Aliasing itself is recorded, not reproduced, because it is purely cosmetic. |
| B3 | `Q` is simultaneously `DIM Q(16)` (landmark history for `MAP.LIB`) and a scalar in `BUY.LIB 50003` (fort tier), `TRADE.LIB 50011` (rounded holding) and `TOMB.LIB` caller 3504 (index of the drowned). A fort tier or a trade therefore corrupts `Q(0)`, which `MAP.LIB` uses as "landmark 0" and which `TOMB.LIB 50005` uses as the death index — and a value of 6 makes `H1(6)` a bad subscript (error 5). | model `Q` faithfully as one 0..16 array with the scalar aliasing, so the map's first point and the drowning-death index can both go wrong exactly as in the original, and let the error handler report a bad subscript if it happens. |
| B4 | `T$` is `DIM T$(0 to 10)` and is used as the travel-screen values, the river option strings and the loss-message list, all at different times, all with residue between uses. | one array; reproduce the residue (e.g. `T$(0)` in `LF.LIB 52030` prints a stale line if nothing was stolen — which the original does). |
| B5 | The original never draws the crossing animation's RND values with any state effect, but Appendix G.5 says 106/122/22 draws that "advance the generator". | the text port **must** make exactly those draws. `cross.py` will contain a `drain_animation_draws(n)` that calls `RND` the right number of times, with the counts in a table, and no visible output. |
| B6 | Appendix G.5: "The loop over oxen at rivers runs `FOR L = 1 TO X` with X the ox count, which may end in .5, so 5.5 oxen give 5 draws." | implement the loop as `for l in range(1, floor(x)+1)` semantics of Applesoft FOR with a fractional limit. |
| B7 | Appendix G.5 ferry: "1 (days to wait) when the offer is made". | the draw is at 50101, i.e. **before** the money check and before the player answers — reproduced. |
| B8 | Appendix G.4 event 8: "1 (part breaks?) … for an injury, 1 (victim) then 1 (arm or leg)" | confirmed by 10800/10810/10830; the 10810 draw happens whenever the part does not break. |
| B9 | `& INP n,"-AZ-az '.-",1,Z$` at MENU 500 — Appendix F says the argument order is *length*, *allowed*, *flag*, *var*, so `ZN`=9 is the **length** and `ZZ`=1 the flag. Appendix X's variable names suggest the opposite. | trust Appendix F: `ZN` is the max length (9), `ZZ` is the flag. Cross-checked against `& INP,4,"-09",1,Z$` for a 4-digit food prompt. |
| B10 | Episode-2 dialog: `W$(0 to 9)` from VAR.BIN vs `W$` used in `PACE.LIB`/`RATION.LIB`/`WIN`. | one `W$` array; the `P$`/`R$` name lists are separate and unambiguous. |
| B11 | `HUNT` argument 4 is the constant `1` "if non-zero, halves the chance that an animal appears (from 4 in 1,000 to 2 in 1,000 per attempt)" (paper §11.1, Appendix Z) | keep 1, and keep the spawn chance as a documented constant with a comment citing that both figures come from a *reading* of the disassembly, not from execution. |
| B12 | `RE(4) = (D < DL)` and `DL` is only recomputed at 3060 and 10410. If a grave is passed while the event loop is skipped (a stopped day), `D` does not change, so nothing is missed. | no action needed; verified. |
| B13 | `MENU 6045` writes the five names to 1920 with a zero terminator each; `OREGON TRAIL 29010` reads them back by scanning for the zero byte. If a name is empty the reader still terminates correctly (next byte is 0). | reproduce via `mem.py`, so empty names round-trip. |
| B14 | `WIN 601` prints `"18" + PEEK(901)`; after 1899 the century is wrong (paper Table 29). | reproduce. |
| B15 | `POKE 901, AY - 1800` with `AY - 1800 > 255` → error 53 (paper Table 29). | reproduce as a defined outcome: the handler prints the message and returns to the menu. |
| B16 | Error 255 (Control-C) handling at 32110 depends on `PEEK(919)`; `919` is set to 1 once the program has finished initialising. | model `919` faithfully; Control-C returns to the menu only after init. |

### 4.3 Things deliberately not reproduced

| # | Thing | Why |
| --- | --- | --- |
| C1 | Hi-res graphics, pictures, images, tunes, sound | non-goal; the formats were never decoded (Appendix H table H1). The `975` sound flag and every `& PT` call site are kept so state is right, but they produce no sound. |
| C2 | `& IN`, `& VSP`, `& HSP`, `& TSP`, `& CO`, `& CEL`, `& CEW`, `& BOX`, `& TAKE`, `& PUT`, `& IMAGE`, `& UIM`, `& DUN`, `& DFW`, `& WIND`, `& DFT`, `& QFH`, `& CSP` pixel geometry | graphics. The UI interface keeps every method so the call sites are visible and so a graphical backend could be added, but the terminal backend implements them as text equivalents (position, indent, clear-to-EOL). |
| C3 | The `& CDN` disk-volume check (`QN$`/`ZN$` matching) | no disk. Replaced by an explicit "flip" step that changes `S` and re-reads `TOMB.SEQ`, with the original's prompts. |
| C4 | Hunting animal **movement** and hit testing | not analysed (Appendix H). One clearly marked function, `hunt.approximate_movement()`, in the hunt module, with the paper's session rules and spawn rules honoured exactly. |
| C5 | `FLOAT`'s `& PUTP`, `& DPB`, doubled `&`, `USR` | not analysed (Appendix F.4). The BASIC around them is transcribed; the drawing is a text-mode approximation in `floatraft.py`. |
| C6 | `TEST FLOAT` (the developer's test program) | dead code on side 2. Listed in GAPS.md, not implemented. |
| C7 | `HELLO`, side-2 `HELLO`, `MENU` (side 2) boot paths | boot machinery. `menu.boot_side2()` exists as a no-op that just returns to side 1. |
| C8 | `MENU 7400/7410/7500` monitor-colour bars and the `Control-S` key | presentation only; the `975` toggle is implemented. |

---

## 5. Random-number discipline

`rng.py` exposes `Rnd` with `.rnd(arg)` and a **draw log**. Every call site is
annotated with the Appendix G table it belongs to. Rules enforced by hand and
by review, and checked by tests:

* exactly the draws Appendix G lists, in order, including discarded ones;
* no draw added, removed, merged or reordered;
* no draw inside a condition the original does not evaluate unconditionally —
  and, because Applesoft has **no short-circuit**, a draw on the right of `AND`
  or `OR` happens **always**. `IF X AND RND(1) < V` in `LF.LIB 50000` and
  `50205` and `FLOAT 1070` therefore draw even when `X` is 0;
* `IF A = 1 AND RND(1) < .5` in `PART.LIB 42010` draws even when the player
  declined to repair;
* the hunting module has its **own** generator (paper §11.1, Appendix G.6) and
  never advances the Applesoft seed.

`CountingRng` records every call so tests can assert the draw count for a given
day, event or river.

## 6. What I would like from a real Apple II ROM

In priority order, so a partial answer still helps:

1. The **complete Applesoft ROM** (` Applesoft .ROM`, the `$D000–$F7FF` image).
   With that, `--rom` runs the genuine FADDT/FSUBT/FMULTT/FDIVT/ROUND.FAC/
   QINT/RND and the string routines, and parity is by construction.
2. Failing that, just the bytes of the two `RND` constants: the 4-byte
   multiplier and the 4-byte addend that `RND` at `$EFAE` reads together with
   whatever byte follows them in the ROM (paper §12.3). Two 4-byte hex values
   plus their ROM addresses. These are the only game-visible constants I cannot
   derive, and they gate every outcome.
3. Failing that, the outputs of paper §12.6: the stored bytes of the game's own
   constants (`.8`, `.2`, `.1`, `2.5`, `3`, `4`, `.51`), and the first few
   `RND` values for one known seed.

## 7. Questions (asked, then answered by judgement — work continues)

1. *Should the default numeric backend be the 6502 emulator or the
   equivalent pure-Python one?* Judgement: pure Python by default (a full game
   in ~1 s instead of ~1 min), 6502 selected with `--num emu6502`, and a test
   asserting the two are bit-identical. The emulator is therefore always the
   authority and always exercised, but never in the hot loop by default.
2. *Does "Apple IIe emulator" mean a full Apple II emulator (ApplePy) or a 6502
   CPU emulator (py65)?* Judgement: py65. ApplePy needs a ROM, SDL2 and a
   display, and its value here would be exactly the ROM. The genuine-ROM path
   is kept behind `--rom` so ApplePy can be added later without touching game
   logic.
3. *Terminal interrupt model.* Judgement: `ui.poll_key()` is genuinely
   non-blocking (cbreak tty on POSIX, `None` when stdin is not a tty), so
   "press Return to stop and open the menu" works as in the original; `--auto`
   disables it for scripted runs.
4. *Data files.* Judgement: a local `data/` directory holding `TOMB.SEQ`
   (two 49-byte slots, one per side, in the paper's field order) and
   `HISCORE.SEQ` (thirty CR-terminated fields). Git-ignored.

## 8. Phase status

1. Plan — **done**, this file.
2. Foundations — `num`, `rng`, `ui`, `state`, `data`, `mem`, `errors`, `files`, `trace`, tests.
3. Set-up and store — `menu`, `buysupplies`.
4. Core journey — `trail` daily cycle, health, weather, events, pace, rations, rest, map, status.
5. Landmark activities — `river`, `fortbuy`, `trade`, `talk`, `part`.
6. Endings — `tomb`, `endl`, `floatraft`, `win`, top ten, management.
7. Hunting and rafting.
8. Review pass — every BASIC line implemented, replaced or listed in `GAPS.md`.