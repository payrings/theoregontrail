# GAPS.md — everything approximated, replaced or missing

**The paper is the work; this file is the code's.** `paper/01-analysis.md` is the
research; this is the honest register of what the Python translation does not
reproduce, with the reason and the source reference, so that a reader never has to
guess which claims are tested and which are merely transcribed.

Ordered by how much it matters.

---

## 1. Parity: what is and is not achieved

**Achieved.** Every arithmetic operation the game performs is executed by a genuine
Apple IIe ROM (release 1.4's Applesoft, at `$D000`–`$F7FF`) running under a py65 6502
emulator. That means the real `FADDT`, `FSUBT`, `FMULTT`, `FDIVT`, `ROUND.FAC`,
`INT`/`QINT`, `MOVAF` and `RND` — the real alignment truncation, the real single
guard byte, the real shift-and-add multiply, the real `ROUND.FAC` rounding points
and the real generator, with its seed at `$C9`. The game never holds a host float for
state; it passes five bytes in and out of emulated memory.

**Achieved.** The two `RND` constants are read out of the ROM image rather than
guessed: the five bytes at `$EFA6` (`98 35 44 7A 68`) and at `$EFAA`
(`68 28 B1 46 20`). Both have only four significant bytes and each is read together
with the byte that follows it — the addend's fifth byte is the opcode of the `JSR`
at `$EFAE` itself. The addend works out at about 1.9 × 10⁻⁸ against products of order
10⁷, which is why the paper says "the addition has almost no effect".

**Achieved.** Decimal literals are converted by multiply-by-ten and add through the
ROM, so `.8` is `80 4C CC CC CD` and `.2` is `7E 4C CC CC CD`, both classic Applesoft
values and neither the nearest float.

**Not achieved — and not achievable from this ROM alone.** The paper (section 12.4)
notes that `STR$` and `PRINT` formatting live in the ROM's own number-to-text
routine, and `VAL` in its text-to-number routine. Neither entry point has been
isolated, so `oregon/applesoft/pure.py:format_applesoft` is a Python implementation
of the rules the Applesoft manual states. It is used for display only; the game's
money text does **not** go through it, because the money pattern
(`V = INT (V * 100 + .5)`, then `STR$` and `RIGHT$`) is reproduced byte for byte in
`oregon.applesoft.fac.str_dollar_int`. The residual exposure is `STR$(PF)`, the
pounds of food, and the fractional miles in a tombstone record. **Next step**: find
the `FOUT` and `FIN` entry points in this ROM and call them.

**Not achieved.** The extension byte is not carried between the operators of one
BASIC expression. Each operator here rounds as if its result had been stored in a
variable, which is what Applesoft does at a `LET` but not in the middle of an
expression. It shows: `1/3 + 1/3 + 1/3` is exactly `1.0` here, where the original's
single-guard-byte evaluation gives 0.9999999998. `num.Chain` exists for the
expressions where the original's own value matters and it is used for the health
total (line 3230), the daily travel (3245), the base speed (660), the climate lookup
(105) and the freeze factor (3225). The remaining exposure is the other long chains —
`FN W`, the accumulation of rain and snow (3240), and the event chances at 3160.

**Not a parity claim.** The `--num pure` backend is a fast path, not a second
authority. It is exact for addition and for `INT`; for multiplication and subtraction
it can differ from the ROM by one unit in the last place, because the ROM keeps a
single guard bit during a shift-and-add and truncates the rest while the Python model
keeps a whole guard byte and rounds. `tests/test_parity.py` measures this and
`tests/test_game.py::test_the_games_own_formulas_agree_with_the_rom` holds the
formulas the game itself uses to within one ulp. **Use `--num rom` for anything that
matters.** The ROM is the default.

---

## 2. Where the paper and the code disagree, and the code wins

| # | Paper | Code | What this does |
| --- | --- | --- | --- |
| A1 | §8.1: "the loop does not stop after the first event … so two events can occur on one day" | line 3180 ends with `L8 = 20` after **every** firing event, so `NEXT L8` leaves the loop | **At most one event per day.** `trail.event_loop` breaks after one. If the paper is right about the original's behaviour, this is the single most consequential divergence and it should be checked against a real run. |
| A2 | §9.3: rough fording, "each good has a 10% to 40% chance" | line 50070 draws `V = .1 + RND (1) * .3` **once**, then all six goods share it | one V per tipping; the draw order is tip?, V, then six goods draws |
| A3 | §4.2 item 4: "At a landmark with a second segment, the player chooses a branch" | line 2110 asks, but `Z$ = "3"` also shows the map and `IF Z = 3 THEN GOSUB 4200` | choice 3 shows the map and then takes the **first** segment |
| A4 | §10.1: the Barlow toll is paid "only if `MY > V`" | line 50020 is exactly that, so a party holding precisely the toll is refused | reproduced; `endl.the_dalles` |
| A5 | §2.3 Table 4 | the two layouts are as stated | reproduced exactly, including that `FLOAT` reads the oxen from 909 and the bullets from 904/905 while the store wrote the yokes to 905 and the boxes to 909 |
| A6 | §4.1: "The shortest route … is 1,771 miles to The Dalles and 1,871 by the Barlow Road" | summing Table 8's own miles along the shortest route gives **1,821** and **1,921** | the table is used as printed, since it is what `LM(Z,0)` holds; the paper's two totals are 50 miles short. Worth checking against a real run. |
| A7 | §8.2 event 2: "no routine exists / none" | line 3180's `ON … GOSUB` list names `10200`, which the program does not have | `RE(2) = 0` at 29001, so it cannot be reached; reaching it would be UNDEF'D STATEMENT. `events.fire` raises rather than silently running something else. |

---

## 3. Deliberately replaced

| What | Why | Where |
| --- | --- | --- |
| All graphics, pictures, images and sound | non-goal; the formats were never decoded (Appendix H, table H1) | the `PEEK 278,170` colour test at line 312 and every `& IMAGE`, `& PUT`, `& TAKE`, `& UIM`, `& DUN`, `& BOX` call site has no text equivalent. `GAPS.md` records them; the UI interface keeps the methods so the call sites stay visible. |
| `& CDN` disk-volume check | no disk | `common.check_side` prompts and changes `S`, which is the part that matters, because the two sides hold one grave each |
| `& INP`'s beep count `ZN` and the allowed-character set | no speaker, and the terminal filters instead | `ui.ALLOWED` keeps the sets the BASIC passes, for the record |
| The travel screen's six labels at columns 95, 70, 81, 95, 23, 20 | no hi-res screen | `trail.travel_screen` prints the same six labels and values one per line, in the listing's order |
| `MAP.LIB`'s plotted route | no map picture | `maplib.show` lists the landmarks passed, plus the miles to the next one |
| `B` as both the status-screen column array and the cannot-continue flag | cosmetic aliasing | the five label columns come from Appendix E.5 and are not aliased; the flag itself is modelled |
| `TEST FLOAT`, the developer's test program on side 2 | dead code | not implemented |
| `HELLO`, side-2 `HELLO`, `MENU` side 2's boot path | boot machinery | `flip.py` covers the two flip directions, which is the part with behaviour |

---

## 4. Approximations inside otherwise faithful code

| What | The honest description |
| --- | --- |
| `hunt.approximate_movement` | Animal **movement and hit testing were never analysed** (paper section 1.4, Appendix H table H1). This one function decides whether a shot connects; it is an approximation and says so in its own docstring. Everything the paper *does* specify is reproduced: six types and where they appear, the weights, at most two animals, no new animal after four shots, the 2500-pass session, one bullet per shot, firing refused at zero, and the hundred-pound carry limit. `hunt.HuntRng` is a **separate** generator because the routine reads the Applesoft seed and never writes it (Appendix G.6) — `tests/test_rng.py` checks that a hunt draws nothing from the game and leaves the seed bytes alone. The 2500-pass figure is taken from the paper, not derived from the bytes. |
| `floatraft` | The BASIC loop is transcribed; the drawing is text. The rock spawn, motion, box overlap and landing passes follow the listing. The **loss routines are shared with the river crossings** exactly as `FLOAT` 700-760 does, and the raft's ten-or-more-losses destruction is reproduced. The speed is not paced to a 1 MHz machine, because there is no interpreter to be slow. |
| The crossing animation | `RIVER.LIB` is preceded by `CROSS.LIB`, whose water marks use `RND` to place pixels. Appendix G.5 says 106 draws for the first half, then 122 for a successful crossing, none for a failed float or ferry, and 22 single draws each followed by 2 more for a failed ford — and that these advance the generator even though they change nothing. **These draws are not implemented.** Every subsequent draw is therefore offset by up to 228 numbers from the original. This is the largest known divergence in the draw sequence. |
| `RND`'s "2,500 passes" | The count is from the paper; Appendix Z's outer loop at `$E0C4` confirms at most two animals and a pass structure, but 2,500 is not derivable from the bytes and is treated as a constant of unknown origin. |
| `WIN`'s rating and the multiplier sentence | Transcribed from the listing. The paper's rating rule `R = (SC < 6000) + (SC < 3000)` is implemented as `win.rating`. |

---

## 5. Bugs reproduced on purpose

All nine from paper section 13, plus one more found in the source. Each is marked in
the code with the BASIC line that causes it.

| Bug | Where reproduced |
| --- | --- |
| No one falls ill or dies while waiting at a river | `trail.day_body` step 7 checks `W1`; `river.crossing` sets `W1 = 1`; `trail.event_loop` returns early when `SD` |
| The starve factor has no cap, so a very long wait kills the party at once | `trail.health_today`, line 3225 — `FS` rises by 0.8 a day and only halves on a good one |
| "Error 53 at line #50050" once the year passes 2055 | `mem.poke` raises `ApplesoftError(53, 50050)`; `endl.write_handover` POKEs 901 |
| The final screen shows the wrong century after 1899 | `win.run` prints `"18" + PEEK(901)` |
| A broken arm has no effect, and wipes any illness | `events.event_8` stores 0, which means healthy |
| A thief never takes money | `lf.thief` draws only items 2, 3, 4 and 8; the cash branch at line 52020 tests for item 0 and is dead |
| The Portland climate row is never used | `trail.climate_zone` produces five zones |
| A party with exactly the Barlow toll cannot pay | `endl.the_dalles` tests `MY > V` |
| February always has 28 days | `trail.advance_date`, `MONTH_DAYS` |
| **Found in the source, not in the paper:** on the trail leaving a fort, menu choice 8 "Buy supplies" runs the **hunt**, and choice 9 "Hunt for food" does nothing | line 4090's `Z = Z * (VAL(Z$) > 7) + VAL(Z$)` with `Z = 2` on the trail. `action.action_menu` reproduces it and says so. |
| **Found in the source:** `Q` is one variable used both as the map's landmark history (`Q(0 to 16)`) and as a scalar by `BUY.LIB` 50003 (the fort tier) and `TRADE.LIB` 50011 (the rounded holding) | modelled faithfully: `state.Q` is one array and both scalar uses write `Q(0)`. The consequences are that the map loses its first landmark, and an accepted trade **rounds the player's holding** -- `I(X+2) = Q - V`, so five and a half oxen become six minus whatever is taken. I first thought a fort tier would also make `TOMB.LIB` 50005 subscript outside `DIM H1(4)`; that is wrong, because line 3504 assigns `Q` from its own loop counter before using it, and `tests/test_rng.py` keeps the retraction. |
| **Found in the source:** the paper's §9.3 "rough" ford wording implies a per-good draw; the code draws one `V` for the whole crossing | A2 above |

---

## 6. Ambiguities in the code, and how each was resolved

These are listed in full in `PLAN.md` section 4.2 (B1 to B16). The two that most
affect the numbers:

**B1 — the climate zone before line 1000 sets it.** Line 29000 computes
`W = INT ((FN W (0) + 10) / 20)` and `FN W` reads `WC$(ZO)`, but `ZO` is not one of
the variables `VAR.BIN` restores (Appendix E.1), so it is 0. The initial temperature
class and the first month's rain chance therefore come from climate row 0 whatever
the departure month. `trail.load_state` sets `ZO = 0` and says so.

**B6 — `FOR L = 1 TO X` with a fractional oxen count.** `RIVER.LIB` 50185 loops over
the oxen, and the count can end in a half. Applesoft's `FOR` stops at the last whole
number below the limit, so five and a half oxen give five draws (Appendix G.5).
`river._lose_oxen` uses `range(int(x))`.

**B9 — which `& INP` argument is the length.** Appendix F says the order is *length*,
*allowed set*, *flag*, *variable*, while `MENU` 500 is written
`& INP,ZN,"-AZ-az '.-",ZZ,Z$` and `ZN` reads like a count. Cross-checking
`& INP,4,"-09",1,Z$` for a four-digit food prompt settles it: `ZN` is the length and
`ZZ` is the flag, so a name is at most nine characters.

---

## 7. What is finished, and what is not

Recorded plainly rather than left to be discovered.

* **The journey reaches Oregon.** `tests/test_playthrough.py` plays a whole game
  from the store to the Willamette Valley — the Kansas and Big Blu Rivers by
  fording, the ferry at the Green, the Shoshoni guide at the Snake, and the Barlow
  Toll Road at The Dalles — and asserts the distance, the day count, the hand-over
  and the health cap. It also asserts **determinism**: the same seed and answers
  give the same game, draw for draw.
* **All three endings are exercised.** `tests/test_endings.py` covers arrival and
  the score (including the profession multiplier and the rating bands), the raft,
  the whole party dying with a tombstone written, a death swapping the corpse into
  the last slot, a second disease killing without naming itself, and the top-ten
  list being rewritten in order.
* **The crossing animation's numbers are spent** — see section 4.

* **Every module is reached by a played game.** A constant generator never fires an
  event, so `PART.LIB`, `LF.LIB` and the rest were unreachable; with
  `rng.SequenceRnd` -- a deterministic but *varied* test generator that is not the
  game's -- four games of about half a second each between them reach `PART.LIB`,
  all three of `LF.LIB`, `HUNT.LIB`, `PACE.LIB`, `RATION.LIB`, `TALK.LIB`,
  `TRADE.LIB`, `BUY.LIB`, `MAP.LIB` and a gravesite. `tests/test_playthrough.py`
  asserts that, and also that four varied games reach Oregon, fire several hundred
  events, bury people, and leave every number inside the limits the game sets.
  Those four runs found, among others, the missing oxen path, a duplicated draw in
  `LF.LIB`, `TOMB.LIB` 50000 falling through into 50005, a division by zero when
  the last member dies, and the Barlow Road never writing the hand-over.

Still not exercised:

* `WIN`'s "would you like to make any changes?" loop is not driven to a second
  pass.
* The management program's tombstone erasure is tested at the file level but not
  through the menu.
* `FLOAT`'s landing at position 17 -- the win rather than the missed landing -- is
  reached by steering, and a scripted run has nothing to steer with, so every
  scripted raft misses the landing at pass 225.
* `TALK.LIB` reads its text at run time from `paper/02-appendix-d-dialogue.md`,
  because the dialogue is MECC's. A game played without that file raises a clear
  error at the first conversation rather than silently having nothing to say.
* The management program's teacher menu is reachable but the top-ten *insertion*
  routine (`win.insert`) has not been run against a real list.
* **A day-by-day trace from the original.** This is the one that would settle
  section 5's open questions — one event or two, and the 50 miles — and it needs the
  game running under an emulator. `oregon/trace.py` already writes the line format
  the comparison needs, including the five seed bytes.

---

## 8. Reference traces

There are none. Appendix H says so, and paper section 12.6 says the next step is to
execute the ROM and confirm the stored bytes of the constants, the first `RND` values
for a known seed, and a day-by-day comparison. The **constants** and the **generator**
are now confirmed — they were read out of this ROM and the sequence runs on it. What
is missing is a day-by-day comparison against the original, which needs the game
running under an emulator. `oregon/trace.py` writes exactly the line format that
comparison needs: the date, `D`, `M`, `H`, `FS`, `H0`, `HR`, `W`, `TM`, `PP`, `AR`,
`AS`, `PF`, `I(2)` to `I(8)`, `MY`, `H1()`, `H2()`, the event that fired, and the five
seed bytes at `$C9` to `$CD` in hexadecimal, one line per game day. The seed bytes are
what make a missing or an extra draw visible on the day it happens.

**No test in this repository compares against a "known good" output**, because none
exists. Every expectation is worked out by hand from the BASIC line named beside it.


---

## 9. Defects found by playing it, not by testing it

Added after the game was first run by hand. All of these were invisible to the
library tests because the tests drove a scripted screen, and all of them made the
game unplayable or misleading.

| What | Why it hid |
| --- | --- |
| **Every allowed-character set was read as a literal list instead of as characters and ranges.** `"-AZ-az '.-"` -- the set `MENU` 500 passes for a name -- is A to Z, a to z, a space, an apostrophe and a period. Read literally it is the four letters `A`, `Z`, `a`, `z`, so **the name prompt accepted almost nothing**: only `a` (and the two other letters) went in, and every other keystroke was ignored. The same mistake hid every menu: `"-14"` is 1 to 4, so the profession screen could not offer a carpenter or a farmer and the main menu could not reach "learn about the trail" or the top ten. | the scripted screen did not filter on the allowed set at all, so the scripted tests could not see it; and the scripted tests answered "1" anyway, which happened to be allowed |
| **ScriptedUI did not apply the allowed-character filter**, so no scripted test could ever have caught a wrong set. | it is a test double, and a convenient one ignores the very rule that was broken |
| **`tty.setcbreak` sets the terminal with `TCSAFLUSH`**, which discards pending input. Entering cbreak lazily, on the first read of a session, threw away any key pressed while the game was drawing -- intermittent, because it depended on which side of that call the keystroke fell. | only a real terminal; a pipe has no line discipline to flush |
| **A prompt that read one character raced its own Return.** It tried to *drain* the Return the player pressed, and usually lost the race, so the **next** prompt got a bare Return, rejected it, and sat there: every answer landed one prompt late. | same |
| The command line never asked for the departure month or read the hand-over back out of memory, so a journey began from an uninitialised state. | only the library path was tested |
| The main menu sent choice 1 to Management: line 1015 tests `A = 1`, the character code of **Control-A**, not the digit. | the scripted test answered "1" and went to Management, which is also a legitimate destination, so nothing looked wrong |
| The profession screen did not loop back on an invalid answer, though line 4025 ends with `GOTO 4005` for every answer. | only reachable with an invalid answer |
| **Matt's store printed its five bill lines without their numbers.** Line 3015 is ``PRINT L". "I$(L)``, so the number is printed with the line -- and it is the number the player types, because the reader at line 250 accepts 1 to 5 and nothing else. Without them there was nothing to select. | the scripted tests answered by position, not by what was on screen |
| **`USR (1)` at line 3030 is a flush, not a request for a key.** It followed "Press SPACE BAR to leave store", which is a label on a box; treating it as a wait put a "Press SPACE BAR to continue" in the middle of the store that the player never saw asked for, and the number they typed went to that instead. | only visible by hand, in a store |
| The article in *"You must trade for ..."* was the wrong way round: `T$(0)` is `"a "` and `T$(1)` is `"an "`, and `T$(B = 2)` picks between them, so the original says **"an ox"** and **"a wheel"**. | cosmetic |

The allowed-set reading is now `ui.allowed_chars`, and it applies to **both** user
interfaces, so a scripted test sees exactly what a player sees. It is guarded by:

* `tests/test_ui.py::test_an_allowed_set_is_characters_and_ranges` -- the reading
  itself: every letter in a name, and the right digits for every menu;
* `tests/test_ui.py::test_every_menu_prompt_allows_every_choice_it_offers` -- every
  prompt's set against the numbers its screen actually prints;
* `tests/test_ui.py::test_a_name_prompt_accepts_any_letters` -- the reported symptom,
  including that a name takes no digits;
* `tests/pty_check.py`, which types at the real game through a pty, types
  `Ebenezer` as the leader and chooses a **carpenter** rather than a banker;
* `tests/test_store.py`, which checks that the bill panel is numbered, that the
  item prompt follows the leave-store label with no keypress between them, and that
  the bill is the sum of the five lines.

A note for anyone writing another allowed set: a range is written **dash first**, so
1 to 5 is ``"-15"`` and not ``"1-5"``. Written the other way it means the literal
characters 1, dash and 5. Every set in the game is written the game's way.
