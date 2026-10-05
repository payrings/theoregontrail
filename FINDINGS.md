# FINDINGS.md — what the ROM and the source actually do

Notes on the Python translation in `oregon/`, written from direct execution of a
real Apple IIe ROM and from the release 1.4 BASIC listings. They are the evidence
for the paper's claims, and where they disagree with it they say so.

It lives beside the code because it is about the code: it is the record of what the
translation found by executing a real Apple IIe ROM, and where that corrected the
paper or the review. The paper itself is in `paper/`.

Everything below was **checked by running something**, not inferred. Where a claim
came from reading the listing alone it says so. Every number quoted here is one this
project printed; the scripts are described in section 10 so any of them can be
re-run.

This file is deliberately fuller than `GAPS.md`. `GAPS.md` says what is not a
faithful transcription; this one says what was found.

---

## 1. The headline: the ROM answers the questions the paper could not

The paper (§12) is right that no host-language arithmetic reproduces this game, and
right that the only route to parity is executing the Applesoft ROM. With an image of
that ROM and a py65 6502 emulator, the gaps it leaves close — and a few of its own
conclusions turn out to be slightly off.

The paper's §12.6 says the next step is to confirm three things: the stored bytes of
the game's constants, the first `RND` values for a known seed, and a day-by-day
comparison. **The first two are now settled, from the ROM itself.** The third still
needs the original running.

### 1.1 The `RND` constants

The paper describes them only as prose: `RND` at `$EFAE` multiplies the seed by one
constant, adds a second, exchanges the first and last significand bytes and
renormalises; both constants are stored in the ROM with four bytes instead of five,
so each is read together with whatever byte follows it; and the addition has almost
no effect for that reason.

All of that is right, and the bytes are:

```
$EFA6   98 35 44 7A 68      the multiplier, five bytes at $EFA6
$EFAA   68 28 B1 46 20      the addend, five bytes at $EFAA
$EFAE   20 82 EB            JSR $EB82   <- the addend's fifth byte IS this opcode
```

The addend's fifth byte is `20`, the opcode of the `JSR` at `$EFAE` that begins the
routine. That is the paper's point made visible: the constant is only four bytes and
the ROM reads whatever the instruction stream put next.

Decoded, the multiplier is a 5-byte value with exponent byte `$98` (152) and
significand byte `$35`, about **1.19 × 10⁷**; the addend has exponent byte `$68`
(104) and significand byte `$28`, about **3.9 × 10⁻⁸**. The first significand byte
has an implied top bit, which is where my earlier figures went wrong by a factor of
two: I had 6.99 × 10⁶ and 1.9 × 10⁻⁸, each half the true value.

So the seed, which lies in [0.5, 1), produces products of order 10⁷ and the addend
is fifteen orders of magnitude below them. "Almost no effect" is a considerable
understatement, and any implementation that adds a plausible-looking constant gets a
subtly different generator.

### 1.2 `RND` itself, decoded

```
EFAE  JSR $EB82      ; FIXARG: A = 0 if FAC is zero, 1 if positive, $FF if negative
EFB1  TAX
EFB2  BMI $EFCC      ; a negative argument is itself the new seed basis
EFB4  LDA #$C9 / LDY #$00 / JSR $EAF9   ; FAC <- the five seed bytes at $C9
EFBB  TXA / BEQ $EFA5                   ; RND(0): the last value again
EFBE  LDA #$A6 / LDY #$EF / JSR $E97F   ; FAC *= the five bytes at $EFA6
EFC5  LDA #$AA / LDY #$EF / JSR $E7BE   ; FAC += the five bytes at $EFAA
EFCC  LDX $A1 / LDA $9E / STA $A1 / STX $9E   ; swap significand bytes 1 and 3
EFD4  LDA #$00 / STA $A2                      ; clear the lowest byte
EFD8  LDA $9D / STA $AC                        ; guard byte <- exponent
EFDC  LDA #$80 / STA $9D                       ; force the exponent to 128
EFE0  JSR $E82E                                ; normalise, keeping the value
EFE3  LDX #$C9 / LDY #$00 / JMP $EB2B          ; round, store to $C9, return
```

Two details worth having:

* `RND(0)` returns the previous value because `MOVAF` loaded FAC from `$C9` **before**
  the `TXA / BEQ` test. The "last value" and "the seed" are the same five bytes.
* Forcing the exponent to `$80` *before* normalising is what lands the result in
  [0.5, 1): the significand is shifted left until bit 31 is set and the exponent is
  lowered by the same amount, so the value is preserved and the exponent becomes
  128.

Measured: 200 consecutive draws from seed `81 00 00 00 00` all landed in [0, 1),
all advanced the seed, and **all 200 were distinct, with no adjacent repeat**. The
sequence does not show the short cycles Sander-Cederlof reports over long runs; this
is only 200 draws, so it neither confirms nor contradicts that.

---

## 2. The working FAC and a stored value are different byte layouts

This is the single thing that makes a ROM backend easy to get wrong, and it cost the
most time in this project.

A value **as Applesoft stores it in a variable** has the sign in bit 7 of byte 1 and
no implicit leading one:

```
3.0 stored   82 40 00 00 00      word = 0xC0000000, with bit 31 implied
```

The **working** FAC at `$9D`–`$A1` is not that. `MOVAF` at `$EAF9` takes the sign out
of byte 1 into a separate sign byte at `$A2` and puts the implicit one back:

```
stored 3.0                       82 40 00 00 00
after MOVAF, $9D..$A1           82 C0 00 00 00     <- bit 7 of byte 1 is now the implicit 1
                $A2              40                <- the sign lives here
                $AC              00                <- the guard is cleared on load
```

Verified by loading 3.0 and dumping the zero page; also verified in reverse, through
the ROM's own store routine at `$EB2B`, which writes back `82 40 00 00 00` for 3.0 and
`82 C0 00 00 00` for −3.0 — it takes bit 7 of byte 1 from `$A2` and bits 6..0 from the
working byte (`LDA $A2 / ORA #$7F / AND $9E`).

The practical consequence: **ARGBUF at `$A5`–`$A9` has the same layout as the working
FAC, with the sign again in `$AB`.** Writing a stored value straight into ARGBUF
loses the leading one and the result is wrong by a factor of two — which is exactly
the bug that made a first attempt at `FDIVT` return 3 instead of 0.333.

So, concretely:

| memory | byte 0 | byte 1 | sign | guard |
| --- | --- | --- | --- | --- |
| a variable | exponent | `sign | top 7 bits` | in byte 1 | none |
| working FAC `$9D` | exponent | `$80 | top 7 bits` | `$A2` | `$AC` |
| ARGBUF `$A5` | exponent | `$80 | top 7 bits` | `$AB` | — |

---

## 3. `ROUND.FAC` and the guard byte, measured

`ROUND.FAC` at `$EB72` is exactly as the paper says: if the extension byte at `$AC`
is 80 or more, add one to the significand, carrying into the exponent.

Measured on 0.4 (`7F 4C CC CC CD`):

```
guard $AC = $7F  ->  7F 4C CC CC CD      unchanged
guard $AC = $80  ->  7F 4C CC CC CE      one unit in the last place
```

**But the routines do not all leave the same guard.** This is the finding that
finally made the pure-Python backend agree with the ROM. The guard byte left in
`$AC` after each operation, and whether `ROUND.FAC` would therefore bump the result:

| operation | result | `$AC` left | rounds? |
| --- | --- | --- | --- |
| 1 + 0.1 | `81 0C CC CC CD` (1.1) | `D0` | yes |
| 1 − 0.1 | `80 66 66 66 66` (0.9) | `60` | no |
| 1 × 0.1 | `7D 4C CC CC CD` | `00` | no |
| 1 ÷ 3 | `7F 2A AA AA AB` | `80` | yes |
| 3 + 1 | `83 00 00 00 00` (4) | `00` | no |
| 3 ÷ 7 | `7F 5B 6D B6 DB` | `00` | no |

So: addition (and the subtract path inside it) leaves the alignment bits as a
rounding indicator; **multiplication leaves none at all**; division leaves one only
sometimes. A pure-Python model that rounds uniformly after every operation is
therefore wrong for multiply, and one that never rounds is wrong for add. The model
that works is the ROM's own: 32 significand bits plus exactly **one** guard bit,
where the guard is the bit immediately below the significand, rounded up when set.
33 bits, no more — a wider internal mantissa rounds from a different bit and
disagrees. That is why `oregon/applesoft/pure.py` uses `(sign, exponent, s33)`.

`1 ÷ 3` is the classic Applesoft `7F 2A AA AA AB` (with the round-up), and
`1 + 0.1` is `81 0C CC CC CD`, both correct.

---

## 4. The operator entry points are not the operators they look like

This is the second expensive finding. Calling `FADDT`, `FSUBT`, `FMULTT` and `FDIVT`
"as the operators" gives wrong answers, because **none of them compares signs** —
Applesoft's evaluator does that before calling.

**`FADDT` at `$E7C1`** branches only on the sign byte of *ARGBUF* (`$AB`):

```
$E7C1  D0 03        BNE $E7C6      ; ARGBUF positive -> add the magnitudes
$E7C3  4C 53 EB     JMP $EB53      ; ARGBUF "zero"   -> MOVAF instead
```

The result takes whatever sign is already in `$A2`. So `FADDT` computes
`|a| ± |b|` and the caller supplies both the operation and the result's sign.

**`FSUBT` at `$E7AA`** complements the sign byte of FAC and then sets ARGBUF's sign
byte to **zero** with `EOR $AA / STA $AB`. So it computes `|b| − a`, discarding `b`'s
sign entirely. Measured: `FSUBT` with FAC = 1 and ARGBUF = −3 returns 2, not −2.

**`FMULTT` at `$E982`** takes the result's sign from ARGBUF and ignores FAC's. Measured:
`−3 × 7` comes back as **+21**.

**`FDIVT` at `$EA69`** shifts ARGBUF left and subtracts FAC, so it computes
**ARGBUF ÷ FAC** — the other way round from the other operators.

All four verified against the ROM once the caller's bookkeeping is done properly:

```
3 − 1   = 2          1 − 3   = −2         −3 − 1  = −4
−3 + −1 = −4         −3 × 7  = −21        3 ÷ 7    = 0.4285714
−3 ÷ 7  = −0.4285714
```

The working approach in `oregon/applesoft/rom.py` is to settle the sign and the
magnitude comparison in Python, hand the ROM two **positive** magnitudes, and apply
the sign to the five bytes afterwards — which is what the interpreter does with its
own sign byte. The ROM still does the part that matters: the alignment, the guard
byte, the carries and the normalisation.

### 4.1 A second, quieter trap: the Z flag on entry

`FADDT`, `FMULTT` and `FDIVT` all begin by branching on the Z flag *before touching
memory*, because Applesoft's evaluator has just done a `LDA $9D`. Nothing else
guarantees that flag. Demonstrated directly:

```
FADDT with Z clear  ->  84 20 00 00 00     which is 3 + 7 = 10, correct
FADDT with Z set    ->  83 60 00 00 00     which is 7: the add was skipped and
                                             MOVAF ran instead
```

Without emulating that `LDA $9D`, results depend on whatever the previous ROM call
left behind. In this project it showed up as the third consecutive division
overflowing for no reason; `_run` now clears and sets Z and N from `$9D` before
every call.

---

## 5. Where the paper is wrong, and where the code is

The order of authority for this project is the BASIC first, then the paper. Six
places where they disagree.

### 5.1 RETRACTED — more than one event can fire on a day

**What I claimed.** That at most one event fires on a travelling day, because
line 3180 ends the loop body with `L8 = 20`, and `NEXT L8` then gives 21 against a
limit of `RE = 14`.

**Why it was wrong.** I read the line as Python reads it, with each `THEN` ending at
the next statement. Applesoft has no blocks: **everything after a `THEN` belongs to
the `IF`** (paper 2.5, rule a). Line 3180 is

```
3180 ... INVERSE : IF B > 0 THEN GOSUB 4000: GOSUB 300:L8 = 20
```

so `L8 = 20` is inside the `THEN` on `B`. It runs only when an event has fired
*and* `B` is above zero. On an ordinary day `B` is zero, the whole clause is skipped,
and the loop carries on to the next event. The paper's §8.1 is right and my reading
was wrong.

**Fixed** in `trail.event_loop`: the loop now breaks only when `B > 0` after an
event. A day therefore draws once per event *tested*, and several events can fire.

Test: `tests/test_applesoft_rules.py::test_more_than_one_event_can_fire_in_one_day`
and `::test_the_loop_stops_early_when_B_is_above_zero`.

### 5.2 The rough ford draws one chance, not one per good (§9.3)

The paper: *"Rough: 16% chance of tipping, then each good has a 10% to 40% chance of
a random loss."*

Line 50070 draws `V = .1 + RND (1) * .3` **once**, then calls the goods loop, so all
six goods share that one value. The draw order is: tip?, V, then six goods draws.

### 5.3 RETRACTED — the route is 1,771 miles, and the paper says so

**What I claimed.** That the shortest route sums to 1,821 miles to The Dalles and
1,921 by the Barlow Road, and that the paper's 1,771 and 1,871 were 50 miles short.

**Why it was wrong.** I summed segments 15 and 17, which go through Fort Walla
Walla: 55 + 120. The shortest route leaves the Blue Mountains on **segment 16**,
straight to The Dalles, 125 miles. Segments 0-7, 10-14 and 16 give

```
102 + 83 + 119 + 250 + 86 + 190 + 102 + 57 + 144 + 57 + 182 + 114 + 160 + 125
  = 1771
```

and with segment 18, the Barlow Road, 1,871. My error was reading the two routes as
the same one. The paper's figures stand.

Test: `tests/test_applesoft_rules.py::test_the_shortest_route_is_1771_miles`.

### 5.4 The climate table is indexed from one, not zero

Not an error in the paper, but a trap. Line 105:

```
DEF FN W(Z) = ( NOT Z + .003 * Z) * ( ASC( MID$(WC$(ZO), AM * 2 + Z - 1, 1)) - 30) - 20 * NOT Z
```

`MID$` counts from **one**, so the position `AM * 2 + Z - 1` is zero-based index
`AM * 2 + Z - 2`, and January's temperature is the *first* character of the row.
This implementation initially used `- 1` and every month's climate was shifted one
month later — a quiet error that changes the whole journey's difficulty curve and
would not have surfaced in any test that only checked self-consistency. It was caught
by testing `FN W(0)` for January against the paper's worked example (row 0, codes 59
and 43, so 9 degrees and 0.039 of rain).

### 5.5 RETRACTED — the map's third choice asks again

**What I claimed.** That choosing 3 at a branch shows the map and then falls
through to line 2200, taking the first segment.

**Why it was wrong.** Same rule (a). Line 1015 ends

```
1015 ... GOSUB 2100: IF Z = 3 THEN GOSUB 4200: GOSUB 190: GOTO 1015
```

so `GOSUB 190` and `GOTO 1015` are inside the `THEN`. Choice 3 shows the map and
returns to line 1015 to **ask again**; it never reaches line 2200.

**Fixed** in `trail.choose_segment`: choice 3 shows the map and loops.

Test: `tests/test_applesoft_rules.py::test_choosing_the_map_asks_again_rather_than_loading_a_segment`.

### 5.6 `& INP`'s first argument is the length, not a count

Appendix F gives the argument order as *length*, *allowed set*, *flag*, *variable*.
`MENU` 500 is written `& INP,ZN,"-AZ-az '.-",ZZ,Z$`, where `ZN` reads like a beep
count and `ZZ` is set to 1. Cross-checking `& INP,4,"-09",1,Z$` for the food prompt —
four digits of food, up to 2,000 — settles it: `ZN` is the maximum length and `ZZ` is
the flag, so a name is at most nine characters. Appendix F is right and the variable
names mislead.

---

## 6. Three bugs in the shipped code that neither the paper nor the appendices list

The paper's §13 lists nine probable bugs. Three more were found in the source while
transcribing it. All six of the interesting ones are reproduced.

### 6.1 RETRACTED — there is no swap in the action menu

**What I claimed.** That on the trail leaving a fort, menu choice 8 "Buy supplies"
runs the hunt and choice 9 "Hunt for food" does nothing, and that this was a bug in
the shipped code which the build reproduced.

**Why it was wrong.** Rule (a) again. Line 4040 ends

```
4040 ... Z = 0: IF NOT LL THEN PRINT L". "AQ$(7):L = L + 1: IF VAL (LM$(LM,1)) = 1 THEN PRINT L". "AQ$(8):L = L + 1
```

so **both** extra entries are inside `IF NOT LL`: "Talk to people" and "Buy supplies"
are printed only at a landmark, never on the trail. Line 4050 then prints "Hunt for
food" on the trail with `Z = 2`, and choice 8 gives `Z = 2 * 1 + 8 = 10`, so `ON Z - 1`
is `ON 9` and reaches 4600, the hunt. Correctly.

**Fixed**: the reproduced "bug" is gone from `action.action_menu` and its docstring.

Test: `tests/test_applesoft_rules.py::test_the_trail_menu_is_the_eight_choices_ending_in_the_hunt`.

### 6.2 RETRACTED — `Q` and `Q()` are two different variables

**What I claimed.** That `Q` is one variable used both as the map's landmark history
`Q(0 to 16)` and as a scalar by `BUY.LIB` 50003 and `TRADE.LIB` 50011, so a fort
purchase loses the map's first landmark and a drowning indexes `H1(6)` outside the
array.

**Why it was wrong.** Rule (b): **a simple variable and an array of the same name are
different things.** `BUY.LIB`'s `Q = ...` and `TRADE.LIB`'s `Q = ...` set the scalar
and never touch `Q()`. The map's history is unaffected.

**Fixed**: `state.Q` is now the scalar and `state.Q_arr` the array; `B_arr` holds
`B(0 to 5)`. The scalar is written by the fort and the trade as before.

The *rounding* an accepted trade does is real and is kept, because it follows from
the scalar: `Q = INT (I(X + 2) + .5)` tests what the party has, and `I(X + 2) = Q - V`
stores the rounded figure less the amount, so 5.5 oxen that trade one away leave 5.
That is now paper §13, bug ten. Likewise `T$` really is one array reused by several
routines, so the observation about residue in `T$(0)` stands.

Tests: `tests/test_rng.py::test_Q_and_the_array_are_two_separate_variables`,
`::test_an_accepted_trade_rounds_the_holding`,
`tests/test_applesoft_rules.py::test_the_state_separates_the_scalars_from_the_arrays`.

### 6.3 `LM$(n,2)` is a segment number, and 0 is not a sentinel

Table 7 gives landmark 0's outgoing segment as **0**, and line 2200 reads
`Z = VAL(LM$(LM, Z+1))` — a segment number, not a flag. Only the Willamette Valley,
which the game never asks, has no way out. An implementation that treats `0` as "no
segment" loses the first leg of the journey entirely. It cost a debugging session
here: the daily cycle spun without ever moving, because `D` was never loaded.

---

## 7. Other details worth recording

**The two hand-over layouts really are different.** The store writes the yokes of oxen
to 905 and the boxes of bullets to 909; `END.LIB` 50050 writes the **oxen to 909** and
the **bullets to 904/905**. `FLOAT` reads the oxen from 909 and the bullets from
904/905. Following paper §2.3's Table 4 literally is right, but the trap is real.

**`INT` at `$EC23` floors, including for a negative fraction.** Measured:
`INT(2.7)=2`, `INT(-2.7)=-3`, `INT(-0.5)=-1`, `INT(-3)=-3`. `QINT` at `$EBF2`
truncates, but `$EC23` corrects for the sign. The paper's translation rule ("`INT` is
floor, not truncation") is right.

**The literals are not the floats you would write.** The ROM's decimal conversion,
driven through real `FADDT`/`FMULTT`, gives:

| written | five bytes | value |
| --- | --- | --- |
| `.5` | `80 00 00 00 00` | exactly 0.5 |
| `.8` | `80 4C CC CC CD` | 0.800000000046 |
| `.2` | `7E 4C CC CC CD` | 0.200000000012 |
| `.1` | `7D 4C CC CC CD` | 0.100000000006 |
| `1/3` | `7F 2A AA AA AB` | 0.333333333256 |
| `2.5` | `82 20 00 00 00` | exactly 2.5 |

`.8` and `.2` are the classic Applesoft values and neither is the nearest float. And
`.9`, which line 3230 uses every day, is `80 66 66 66 66` = about **0.8999999999069**,
slightly *below* 0.9, so `.9 * 20` is **not** 18 — it is just under 18. A test asserts
that it is below, which is the direction the bytes give.

**No short-circuit.** Every `IF X AND RND (1) < V` spends a number whether or not `X`
holds — `LF.LIB` 50000 and 50205 and `FLOAT` 1070 all depend on it, and Appendix G
says so. The code reads it as `IF (X AND RND...)` with no short-circuit, which is why
the hunt's rock slots draw even when full.

**The `Q` at line 3160 for graves.** `RE(4) = (D < DL)`, and `DL` is only recomputed
at 3060 and after a grave is read. A stopped day does not change `D`, so a grave is
never missed.

---

## 8. The hunting module: what the ROM code does confirm

**Source, and its limits.** The hunting module lives on the Oregon Trail disk's
system tracks, not in the Apple IIe ROM — checked: at `$E04A` and `$E068` the IIe
ROM holds `14 30 02 70 F7 A9` and `9B D0 08 A5 82 C8 D1 9B`, which is Applesoft
code, where Appendix Z has the terrain and animal tables. So everything in this
section is read from **Appendix Z's disassembly of the disk**, not from anything
executed here, and none of it has been run. It is still worth recording, because
three of the paper's claims can be checked against the bytes independently.

* The outer loop at `$E0C4`–`$E0EF` walks a **two-entry** array (`LDX $E12E`,
  compare with 2, `INC $E12E`), confirming at most two animals on screen. It also
  decrements two counters at `$EDE5`/`$EDE6` and leaves when both reach zero,
  consistent with a fixed-length session — though 2,500 passes is not derivable from
  the bytes and is taken from the paper as a constant of unknown origin.
* The terrain table at `$E04A`–`$E067` is six bytes per climate zone:
  zone 0 = 0,1,2,6,7,8 (kinds A and C); zone 1 = 6,7,8,6,7,8 (C only);
  zone 2 = 3,4,5,12,13,14 (B and E); zone 3 = 9,10,11,12,13,14 (D and E);
  zone 4 = 3,4,5,3,4,5 (B only). That is exactly the paper's description of which
  object kinds each zone draws, read straight out of the data.
* The animal records at `$E068`–`$E097` are eight bytes each. Reading the two
  little-endian 16-bit fields of each as `base` and `span` gives
  `(100, 40)`, `(200, 200)`, `(1700, 300)`, `(120, 30)`, `(2, 8)`, `(3, 4)` — that is,
  the six types with **exactly** the weight ranges of the paper's Table 24, in the
  same order: 100–140, 200–400, 1700–2000, 120–150, 2–10, 3–7. Each record begins
  with a picture/animation index, and the bison's record starts `0B` where the rest
  start `03`.

  So the weight table can be derived from the bytes independently of the analysis
  that produced Table 24 — which is a genuine cross-check of the paper, though not
  an execution of the module.
* The private generator at `$F4D9`/`$F53F` reads the Applesoft seed at `$C9`–`$CD`
  into its own `$F5A0`, ors 1 into the low byte, then runs a 26-step
  rotate-and-subtract loop, and **never writes back to `$C9`**. That is why a hunt
  does not advance the game's sequence (Appendix G.6). It *is* seeded from the
  Applesoft seed, so a hunt's outcome depends on the game's seed — just not on how
  many numbers the game has drawn since.

Still not analysed, and therefore approximated in this rebuild: animal movement and
hit testing. `hunt.approximate_movement` is the one function that decides whether a
shot connects, and its docstring says so.

## 9. `FLOAT`: what the BASIC does that is easy to miss

* The rock fill test at line 1070 is `IF NOT FL(n) AND INT(100 * RND(1) + 1) <= RF`,
  and with no short-circuit the draw happens even when the slot is already full.
* `FL(0)` and `FL(1)` are the two rock slots, and `NR = -1` at line 1060. **RETRACTED
  claim:** I wrote that the collision loop at line 500, `FOR A = 0 TO NR`, never
  executes. It runs **once**, with `A = 0`, because the body always runs at least
  once (paper 2.5, rule c). It then reads `RX(0)` and `RY(0)`, which hold whatever
  the last rock left behind, so it compares the raft against a stale box. The
  substantive collisions still come from lines 1120 and 1130; the loop at 500 is
  redundant rather than dead. `floatraft._line_500` now performs it.
* `FOR L = 0 TO NP - 1` at line 750 likewise runs once when `NP` is 0, so with
  nobody alive the body still executes and indexes `H1(0)`.
* `FOR L = 1 TO X` at `RIVER.LIB` 50190, where `X` is the oxen count, runs **once**
  for any `X` below 1, so **half an ox gives one draw**. `range(int(X))` gives none,
  which was wrong. `num.fort_count` and `num.fort_range` now express the rule and
  `river._lose_oxen` uses them.
* The shore collision tests `HP < 1 OR HP > 16`, so a raft pushed past 16 lands at 17,
  which is also the landing position — being bounced off the right bank is how you
  land.
* Line 730: `IF Z > 9` destroys the raft outright and sets `NP = 0`, so ten or more
  separate losses in one collision is total loss.
* Line 750 removes the drowned after the message and shrinks `NP` inside the loop
  while iterating over it, so with more than one drowning the index runs ahead of the
  array. Reproduced as written.

---

## 10. How these were established

The checks are short scripts against the ROM. In outline:

1. **Disassembly** with `py65.disassembler.Disassembler`, fed the image at
   `$8000`–`$FFFF`. (`Disassembler` takes an `MPU`; `MPU.disassemble` is a list, not a
   method, which is an easy trap.) The image is 32 KB covering `$8000`–`$FFFF`, so a
   file offset is `address - 0x8000` — getting that wrong puts the ROM at the wrong
   place and every address looks like noise.
2. **Calling** a routine by pushing a return address, running `JSR target ; RTS` at
   `$0300`, and stepping until the CPU reaches a park loop at `$03F0`. The loop must
   test `pc != 0x300`, because `$0300 < $C000` and would otherwise look like an
   immediate return. Two py65 details that cost time: `MPU.memory` is a `list`, so a
   slice returns a list and needs `bytes(...)`; and `sp` is an offset into page one,
   so `sp = 0xFF` then `stPushWord` correctly writes `$01FE`/`$01FF`.
3. **Differential testing** of a pure-Python model against the ROM on thousands of
   operand pairs, which is what located the sign-convention bugs, the guard-byte
   semantics and the exponent errors. The pure model was wrong six separate times
   before it agreed; every fix was found by the ROM disagreeing.
4. **Reading the game's own routines** — `MENU` 6000 makes exactly ten draws whatever
   the values, `WIN` 630's rating is `(SC < 6000) + (SC < 3000)`, and the
   `INT (V * 100 + .5)` money pattern round-trips to `" 1234.56"`, `" 0. 0"` for zero
   and `" 0. 5"` for five cents.

Two lessons from getting my own instrumentation wrong, which cost about as much as
the findings did:

* `Fac.to_float()` originally dropped the sign, so `INT(-2.7)` appeared to return
  **+3** and the ROM looked badly broken. The ROM was right; the debug helper was
  wrong. Always confirm a surprising ROM result with an independent path before
  believing it.
* Files written from a shell heredoc left a stale `__pycache__` that produced
  `ImportError: cannot import name 'ScriptedRnd'` for a class that was plainly in
  the file. Clearing the cache fixed it immediately. If an import of a symbol you can
  see fails, clear the cache before reading anything else.

---

## 11. What is still open

1. **A day-by-day comparison against the original.** The trace facility
   (`oregon/trace.py`) writes the line format Appendix H asks for — date, `D`, `M`,
   `H`, `FS`, `H0`, `HR`, `W`, `TM`, `PP`, `AR`, `AS`, `PF`, `I(2)`–`I(8)`, `MY`,
   `H1()`, `H2()`, the event, and the five seed bytes at `$C9`–`$CD`. The seed bytes
   are the point: a missing or an extra draw shows up on the day it happens. This is
   the single thing that would settle §5.1 (one event or two) and §5.3 (the 50 miles).
2. **The `CROSS.LIB` animation draws.** Appendix G.5 says 106 draws for the first
   half of a crossing, then 122 for a success, none for a failed float or ferry, and
   22 single draws each followed by 2 more for a failed ford. They change nothing but
   advance the generator. **Not implemented**, so every draw after a river crossing
   is offset from the original by up to 228 numbers.
3. **`FOUT` and `FIN`.** The ROM's number-to-text and text-to-number routines would
   close the last parity gap — the number formatter is currently Python. The entry
   points are not yet isolated; `& INP`'s use of a ROM parse would point at one.
4. **`QD`/`QINT` for the 32-bit conversions.** `PEEK (906) + PEEK (907) * 256` and the
   16-bit `FN LO`/`FN HI` split are done in Python. They are exact, but confirming
   them against the ROM's own `FTOINT` would close the loop.
5. **The end-to-end journey — now done.** A scripted run plays the store, both
   first rivers by fording, the ferry at the Green, the Shoshoni guide at the
   Snake, and the Barlow Toll Road, and reaches the Willamette Valley in about
   150 days and 1,900-2,000 miles. Arrival, the raft and the party dying are
   covered too. What a run still does not reach is `PART.LIB`, `LF.LIB`,
   `HUNT.LIB`, `PACE.LIB`, `RATION.LIB` and `TALK.LIB`, because a scripted party
   meets no events; their draw sequences are counted in the tests instead. See
   `GAPS.md` section 7.

---

## 12. Two things the integration tests found that static reading had missed

Worth recording because both were invisible until the game was actually played.

**`L8 = 20` is not the only reason one event fires a day.** It is, but the *loop*
around it is not what I assumed either: with `L8 = 20` set inside the body, the
paper's claim in section 8.1 cannot be right. Separately, playing the journey
showed that after a river crossing the party can be left with **no oxen at all** --
the Green River at twenty feet always takes the last one -- and then the original's
line 1015, `ON B > 0 GOTO 4000`, puts the player in the action menu with no way out
until a trade or a fort supplies oxen. My first transcription fell through instead,
which left the wagon at speed zero and spun the daily cycle for ever, drawing
ninety thousand numbers before the test harness noticed. **`ON B > 0 GOTO 4000` is
load-bearing.**

**A duplicated draw survived an earlier fix.** `LF.LIB` 50010's amount draw was
written twice, which spent two numbers where Appendix G.4 lists one, shifting every
later number in the game. It was found by counting draws per fire rather than by
reading, and it is exactly the class of error the draw-count tests exist for. It is
now `tests/test_rng.py`'s subject matter and there is a comment at the call site.

A third, smaller one: `TOMB.LIB` 50000 has no `RETURN`, so `GOSUB 50000` runs 50000
*and* 50005 -- the whole death, not just the health cap. Reading 50000 in isolation
suggests otherwise.

---

## 13. An independent record of the generator

The paper's §12.6 lists as outstanding "the first `RND` values for a known seed".
Those numbers now exist from a separate execution of this same ROM image, and
**all fifteen match what `oregon/applesoft/rom.py` produces**, as does the seed
they leave behind:

```
seed 81 00 00 00 00, fifteen consecutive RND(1)
0.4072949116816744   0.608041618950665      0.25951706536579877
0.08268766026594676  0.35866158816497773    0.9610444016288966
0.5672113706823438   0.6001326921395957     0.33425431547220796
0.6068662970792502   0.6758213557768613     0.3164409970631823
0.036882334752590396 0.03491484130790923    0.2833032483467832
final seed $C9..$CD = 7F 11 0D 1F 95
```

That matters more than another self-consistent test: it is the generator checked
against something this code did not produce, so the multiply, the addend, the
significand byte swap and the renormalisation are all confirmed at once. It is
pinned in `tests/test_parity.py::test_rnd_from_a_known_seed_matches_the_independent_record`,
together with the ROM's conversion of `.8`, `.2` and `.1`.

## 14. Two terminal bugs worth recording

Both showed as *the keyboard is unresponsive*, and neither was visible from the
library tests, because both live in the line discipline.

**`tty.setcbreak` throws input away.** It calls `tcsetattr` with `TCSAFLUSH`, which
discards pending input. The terminal was being put into cbreak mode lazily, on the
first read of every session -- so a key pressed while the game was drawing was
dropped on the floor. It looked intermittent because it depended on which side of
that call the keystroke fell. The mode is now built by hand and set with
`TCSANOW`, which leaves pending input alone. This is almost certainly what the
player was hitting.

**A prompt that read one character raced its own Return.** The prompts took a
single character and then tried to *drain* the Return the player had pressed --
but the Return often arrived a moment after the drain ran, so the **next** prompt
was handed a bare Return, rejected it as not one of the allowed characters, and
sat there waiting. Every answer landed one prompt late, which reads exactly like a
dead keyboard. Fixed by reading to the end of the line, as a canonical terminal
and therefore the original always did: each Return belongs to exactly one prompt.

`tests/pty_check.py` drives the real game through a pty and checks that each
answer reaches the screen it should, and `tests/test_terminal_input.py` runs it
under pytest. A pipe would not have found either bug.


---

## 15. `& INP`'s allowed set is characters *and ranges*

The single fact behind several bugs, and the one worth remembering from this
project.

`& INP`'s third argument is not a list of permitted characters. It is a list of
characters **and inclusive ranges**, where `-` pairs the two characters either side
of it. `ui.allowed_chars` reads it that way:

```python
if spec[i] == "-" and i + 2 < len(spec):
    out.update(chr(c) for c in range(ord(spec[i+1]), ord(spec[i+2]) + 1))
    i += 3
```

Every set in the game then falls out, and the sets are exactly as the listings
print them -- nothing needs correcting:

| the listing | what it means |
| --- | --- |
| `"-AZ-az '.-"` (`MENU` 500) | every letter, a space, an apostrophe, a period -- and no digits, since a name takes none |
| `"-14"` (`MENU` 1015`, `MENU` 4025`) | 1 to 4: all four choices of the main menu and of the profession screen |
| `"-15"` (`MANAGEMENT` 1015) | 1 to 5 |
| `"-16"` (`BUY SUPPLIES` 6020) | 1 to 6 |
| `"-18"` (`BUY.LIB` 50010) | 1 to 8: the seven goods and leaving |
| `"-13"` (`OREGON TRAIL` 2120, `RATION.LIB` 50040) | 1 to 3 |
| `"-09"` (the store's quantities) | 0 to 9 |
| `"-19"` (`BUY SUPPLIES` 405) | 1 to 9 yoke |
| `"YESNOyesno"` | ten literal characters |

Two things follow that are worth writing down.

**Appendix X's `CHR$(1) + "-14"` needs no correction.** Read as a range it permits
1, 2, 3 and 4, so all four menu choices are reachable and the teacher menu is
Control-A. Read as a literal list it permits only 1 and 4, and the game could not
be played. That is why it looked like a slip in the listing when it is not one.

**And `RIVER.LIB` builds its set at run time**: line 50015 is
`Z$ = "-1" + STR$(Z)`, so a five-choice menu asks for `"-15"` -- a range, again, and
all five choices work.

The symptom this produced was, in the player's words, that the name prompt
"doesn't recognise most letters but 'a'": with the set read literally only `A`, `Z`,
`a` and `z` were permitted, `a` being the only lowercase letter anyone tries first.

## 16. Audit of the three Applesoft rules across the whole transcription

The paper's 2.5 lists three rules that govern how a line executes. All three had been
violated somewhere, because the code was first written the way Python reads. This is
the sweep of every line in the listing whose `IF` has a conditional or control-flow
tail, every name used as both a scalar and an array, and every `FOR`.

### 16.1 Rule (a): everything after `THEN` belongs to the `IF`

Fifty lines in the listing have an `IF` whose tail is itself conditional or control
flow. Every one of them is now read that way. The ones that changed behaviour:

| line | what the tail really does | code |
| --- | --- | --- |
| 3180 | `GOSUB 300` and `L8 = 20` are inside `IF B > 0` | `trail.event_loop` |
| 1015 | `GOSUB 190` and `GOTO 1015` are inside `IF Z = 3` | `trail.choose_segment` |
| 4040 | both extra entries are inside `IF NOT LL` | `action.action_menu` |
| 4060 | `B = 2 * (I(2) = 0)` then `IF NOT B` | `action.action_menu` |
| 811 | `L = L - 1` is inside `IF Z > 3` | `buysupplies` |
| 3504 | `GOSUB 190` is inside `IF Z` | `common.end_library` |
| 3200, 3206, 3240, 50195, 50014 | nested `IF`s whose own tails chain | `trail`, `lf`, `common` |

**One further misreading found by the sweep**, not in the six retractions: `BUY
SUPPLIES` line 811 is

```
811 IF Z > 3 THEN & CO: PRINT CF$: PRINT "Your wagon may only carry 3 "SP$(L,0)"s.": ...: & BOX:L = L - 1
```

`L = L - 1` is inside the `IF`, and `NEXT` then adds one, so an over-limit answer
returns to **the same part**. My code used a Python `for` loop with `continue`, which
moved on to the next part. It is now an index-based `while` that steps back.

### 16.2 Rule (b): a scalar and an array are different variables

Four names are used both ways in the listing: `Q`/`Q()`, `B`/`B()`, `RE`/`RE()` and
`Z`/`Z()`. All four are now separate fields.

* `Q` -- scalar (fort tier, trade rounding) and `Q()` the map's landmark history.
* `B` -- the cannot-continue flag; `B(0 to 5)` the travel screen's six label columns,
  which line 320 fills with `& CO, B(L)`.
* `RE` -- `RE(0 to 14)`, the per-event probabilities set up at lines 29001 and 3060.
* `Z` -- the ubiquitous mode selector; `Z()` is a scratch array used by `TOMB.LIB`
  and `MAP.LIB`.

`RE` needed no change: my `state.py` has `RE` as a list and there is no scalar `RE`.
The other three were conflated and are now split.

### 16.3 Rule (c): a `FOR` always runs its body once

Every `FOR` in the game logic was checked. Three were dead in my code because I used
Python `range`:

| line | loop | wrong | now |
| --- | --- | --- | --- |
| FLOAT 500 | `FOR A = 0 TO NR`, `NR = -1` | never ran | runs once, `A = 0` |
| FLOAT 750 | `FOR L = 0 TO NP - 1`, `NP = 0` | never ran | runs once, `L = 0` |
| RIVER 50190 | `FOR L = 1 TO X`, `X = 0.5` | no draw for half an ox | one draw |

`num.fort_count(lo, hi)` and `num.fort_range(lo, hi)` now express the rule once;
`river._lose_oxen` and `floatraft` use them.

**A second, unrelated bug the sweep turned up**: `trail.health_today` computed `ZP` as
"twice the pace *above* steady", so a party at steady pace took no pace penalty at all.
Line 3220 is `ZP = (W > 5) + (W > 7) + P + P` -- the pace added to itself, so steady
already costs 2 and only a stopped party has `P = 0`. Fixed, with a table test at
`tests/test_game.py::test_zp_is_twice_the_pace_plus_the_weather`.

## 17. The action menu, read again from the listing

Correcting my own earlier work, prompted by the paper's Table 9 and section 4.3.

**Line 2100 does not end the game at milestone 16.** I had claimed that in `GAPS.md`
and was wrong. `IF LM = 16 THEN & APP,"END.LIB": GOSUB 50000: GOSUB 190` runs
`END.LIB`; the ending is 50050. See `GAPS.md`, "Resolved".

**`LL` is 0 at a landmark and 1 on the trail**, so `IF NOT LL` at line 4040 is the
landmark case: "Talk to people", and "Buy supplies" at a landmark of type 1, are
printed at landmarks only. Line 4050's `IF LL` adds "Hunt for food" on the trail and
sets `Z = 2`. Line 4090 then computes `Z = Z * (VAL (Z$) > 7) + VAL (Z$)` and
dispatches `ON Z - 1 GOSUB 4100, 4200, 4300, 4400, 4500, 4900, 4700, 4800, 4600`,
so, keyed by `Z`:

| Z | target | option |
| --- | --- | --- |
| 1 | nothing -- `ON 0` does nothing (2.5) | 1 continue |
| 2 to 7 | 4100, 4200, 4300, 4400, 4500, 4900 | 2 to 7 |
| 8 | 4700 | 8, "Talk to people", at a landmark |
| 9 | 4800 | 9, "Buy supplies", at a fort |
| 10 | 4600 | 8 on the trail, "Hunt for food", because of the `Z = 2` |

**Two bugs this exposed**, both from my earlier retraction of the "menu swap" finding:
where I had only removed the claim, the code underneath still had it.

* `do_buy` was reachable from the **trail** menu. `if L.LM_TYPE[st.LM] == 1` was not
  nested under `if not on_trail`, so the very nesting I had retracted was still in the
  code. It now sits inside the landmark branch.
* The handler table was keyed by `z - 1` with nine entries, so **choice 2, "Check
  supplies", matched nothing** and silently did nothing. The table is now keyed by
  `Z`, from 2 to 10.

Test: `tests/test_applesoft_rules.py::test_the_trail_menu_is_the_eight_choices_ending_in_the_hunt`,
and the two menu shapes in `tests/test_landmark_tables.py` and
`tests/test_action_menu.py`.

**The test script answered menus by position**, so it broke as soon as the number of
options changed, and it broke silently: "Buy supplies" is the ninth option at a fort
and the eighth at Independence, so a hard-coded 9 opened the hunt instead. The driver
now resolves a menu option from its printed label (`Option` in `test_playthrough.py`),
which is why the position-based script had been hiding this.
