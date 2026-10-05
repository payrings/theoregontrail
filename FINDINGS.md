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
code, where the machine-code listings have the terrain and animal tables. So everything
in this section is read from **that disassembly of the disk**, not from anything
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

**`CHR$(1) + "-14"` in the BASIC needs no correction.** Read as a range it permits
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

## 18. A second audit of the code against the listing

I re-read the transcription against the BASIC, module by module, looking only for
places where the code and the listing disagree. This found seven defects I had not
seen. Every one below was then checked by hand against the listing text and, where a
draw was involved, by counting draws at run time. **No code was changed** — this
section records what is wrong, so that it is fixed deliberately rather than by
accident.

Six of the seven are cases where Python's own semantics were allowed to leak in:
a short-circuit `and`, an `if/elif` chain standing in for an `ON` with fewer targets,
a loop-back the listing does not have, and a scalar written into an array.

### 18.1 A river is crossed twice after the action menu — `trail.py`

Line 1015 is
`ON LM$(LM,1) = "2" GOSUB 3500:Z = 1:...:GOSUB 21000: ON B > 0 GOSUB 4000: GOSUB 2100: IF Z = 3 THEN GOSUB 4200: GOSUB 190: GOTO 1015`
and line 1016 is `GOSUB 2200:LL = 1: GOSUB 3000:LM = NM: ...`.

The only way back to 1015 is choice 3, because `GOTO 1015` is inside
`IF Z = 3 THEN` (rule a). After `ON B > 0 GOSUB 4000` the menu returns and 1015 simply
runs off the end into 1016, which loads the segment. **The crossing at the top of
1015 happens once per landmark visit.**

`trail.run` wraps the whole block in `while True:` and `continue`s after the action
menu, which re-enters `if L.LM_TYPE[st.LM] == 2: river.crossing(c)`. Fording the Green
River at twenty feet takes every ox, the menu then supplies more, and the party fords
the same river again: a second `CROSS.LIB` spend, a second decision, a second set of
losses and drownings. Verified by counting crossings with the menu stubbed to grant
oxen — the call sequence was `9, 9, 9, 9 …`, the second crossing immediately after the
menu.

### 18.2 Event 12 invents an event, and spends a draw on it — `events.py`

Line 11200 is `ON INT ( RND (1) * 3) GOTO 11250,11275`. **Two** targets, and
`INT(RND(1)*3)` is 0, 1 or 2. An `ON n GOTO` with `n` past the end does nothing at all
(paper 2.5), so with probability about one third the original does nothing.

`events.event_12` falls out of both `if`s into
`trail.lose_days(c, "11275 stray ox days", 3, "Ox wanders off")`. So a fire event
sometimes produces a stray ox and one to three lost days that the original never
produces, and `lose_days` spends an extra `INT(RND(1)*3+1)` that shifts every later
number in the game.

### 18.3 The repair draw is short-circuited — `part.py`

Line 42010 is `IF (Z$ = "Y") AND ( RND (1) < .5) THEN …`. Applesoft evaluates both
sides, so the toss is made whether or not the player agreed.

`part.py` has `if yes and c.rng.below("42010 repair succeeds", num.HALF)`, and Python
short-circuits, so declining the repair spends no number. Verified: one draw when the
answer is `y`, none when it is `n`. The line's own comment says the draw is made
either way, so the comment is right and the code is not.

This is reachable from event 8, whose part-break branch is `.33`.

### 18.4 The fire draw is skipped when there is no food — `lf.py`

Line `LF.LIB` 50010 is `NEXT :YY = PF: IF YY AND RND (1) < .5 THEN …`, and again both
sides are evaluated: the toss happens even when `PF` is 0.

`lf.fire` has `if not held.is_zero() and c.rng.below("50010 fire food", num.HALF)` —
zero test first, so with no food the toss is skipped. Verified: a fire with `PF = 0`
spends five numbers, with `PF = 100` spends six. The listing requires six either way.

The tell is the line just above it, `50000`, which correctly spends its toss **first**
(`c.rng.below(...) and not held.is_zero()`). The two lines of the same routine were
written opposite ways round.

### 18.5 The scalar `SN` is written into the array `SN()` — `trail.py`

Line 29000 declares `DIM Q(16),SN(1),ML(1)`, and line 3000 assigns `SN = NM * 100 + LM`
to the **scalar**. The array `SN(0)`/`SN(1)` holds the two tombstone records, written by
`FLIP.LIB` 50030 and read by line 450: `IF (SN = SN(L4)) AND (DL < ML(L4)) AND
(ML(L4) < D)`.

`start_segment` does `st.SN[st.S] = st.Z.to_int()` — it puts the current segment code
into the tombstone slot for the current disk side. `find_grave` then compares
`st.SN[i]` against the segment it recomputed locally, so after any death on side `S`
the equality is trivially true and the remaining tests reduce to `ML[S] < D`. The party
therefore meets the same grave again on every later segment, and the record can never be
skipped. This is the same class of mistake as the `Q`/`Q()` aliasing retracted in 6.2,
and it was not previously listed anywhere.

### 18.6 The party can die at 3235 and the day carries on — `trail.py`

Line 3235 is `IF NOT W1 AND H > 139 THEN GOSUB 10300: INVERSE`. Line 10300 reaches
`TOMB.LIB` 50005, which falls into the tombstone routine and then `& RNH,"MENU"` —
**it never returns**. Lines 3240 to 3265 therefore never run.

`day_body` guards `NP <= 0` after `event_loop`, where that death does happen, but not
after `illness(c)`. When the disease kills the last member the code goes on to
`accumulate` and `travel_today`, and `speed()` computes `OP = I(3) / NP` with `NP = 0`,
which is Applesoft error 10. The code's own comment in `daily_cycle` names this hazard;
the guard is simply missing on this path.

### 18.7 An abandoned wagon gives twenty times the bullets, not twenty-one — `lf.py`

Line 51010 is `X = INT ( RND (1) * 3 + 1):X = X + X * (Y = 4) * 20: …`. For ammunition
(`Y = 4`) that is `X = X + 20X`, so **21, 42 or 63**.

`lf.abandoned_wagon` has `x = x * 20`, giving 20, 40 or 60. The neighbouring
`fortbuy` gets the *other* multiplier right — `BUY.LIB` 50025's `K = 1 + 19 * (L = 3)`,
so ammunition is bought in boxes of 20 — which is exactly what makes the 20 here look
plausible. The draw count is unaffected.

### 18.8 Four smaller things

* **Line 11300 has no `GOSUB 650`, and neither does `LF.LIB` 51030.** The abandoned-wagon
  branch of event 13 ends `GOSUB 51000: GOSUB 190: GOSUB 900: RETURN`, so clothing
  recovered from a find does not change `OP` until the next `GOSUB 650`. `events.py`
  calls `trail.speed(c)` in that branch, so the speed **is** recomputed. The thief branch
  at `LF.LIB` 52030 *does* end in `GOSUB 650`, and that one is right — the asymmetry is
  the tell. One day of `ZC` is smaller than it should be.
* **Line 11505's retry loop is missing.** `Z = (Z + 1) * (Z < (NP - 1)): ON (H1(Z) < 0)
  GOTO 11505: Z = Z + (NP > 1) * (Z = 0): RETURN` walks up past any member already dead.
  `illness.choose_victim` has `while z < 0: z = 0`, which can never fire, so the branch
  that was meant to be implemented is standing in as dead code. I could not construct a
  reachable state where `H1(Z) < 0` for `Z < NP`, so this is a silent omission rather
  than a wrong number, but it is an omission.
* **`events.event_1`'s docstring is wrong.** Line 10100 is `IF TM > C2 THEN GOSUB 11500:
  …`, so the victim draw is inside the `THEN` and **no** draw is spent when `TM <= 2`.
  The code is correct; the comment says the opposite. Left in place here rather than
  fixed, because it is the kind of sentence a later audit trusts.
* **Line 320 pairs labels and values differently.** It reads six labels from the DATA at
  22000 and prints six values from `T$(0 to 5)`, so row 0 shows "Press RETURN to size up
  the situation" above the **date**, and "Miles traveled" — the seventh datum — is never
  printed at all. `travel_screen` pairs each label with the value that belongs under it
  and omits the "Press RETURN…" row. Cosmetic, but `GAPS.md` 3 described it as "in the
  listing's order", which was not true; that entry is corrected.

### 18.9 Checked and found correct

Worth recording, because these are the places the audit expected to find trouble:
`trail.speed` (650-660) statement for statement; `find_grave` (450-455) apart from 18.5;
`start_segment` (3000-3060); the whole of 3100-3190 including `RE(0)`, `RE(14)`,
`RE(3)`, `RE(4)`, `RE(5)`, `RE(6)`, one draw per event tested, and the `FOR L8 = C0 TO RE`
bound of 15; `count_ill` (3200); `weather` (3205-3206) draw order and count;
`health_today` (3207-3230) all seven penalties; `accumulate` (3240), including the
`IF AS THEN :` colon; `travel_today` (3244-3246) left to right; `advance_date` (3255);
3499; 1000-1020 including the arrival draw at every landmark; 2100-2120; 2200; and events
0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13 and 14 statement for statement with their draw
orders.

One reading I want on the record rather than left as an inference: **Applesoft's `NOT`
is taken here as 1 for true and 0 for false.** Three places depend on it and agree with
each other — `3244`'s `NOT SD`, the `FN W(0) = code - 50` that makes July 60 °F and
January 9 °F, and `NOT W1` suppressing 3235 at a river. With the opposite reading `V`
would be negative on every travelling day and the game could not run at all, so the
reading is forced; but it is an inference from behaviour, not something checked against
the ROM, and it deserves a test of its own.

## 19. A third audit: the water modules, the store, the trader and the top ten

The same exercise over the modules section 18 did not reach. Nine more defects, again
verified by hand against the listing and, for the draws, by counting them. **No code was
changed.** The first is the worst thing found in this whole exercise.

### 19.1 Every loss is zero — `INT (RND (1) * X + 1)` was written `INT (RND * 1 + 0)`

The listing computes how much is lost from the amount held:

| line | library | expression |
| --- | --- | --- |
| 50205 | `RIVER.LIB` and `FLOAT` | `X = I(L): ... Y = INT ( RND (1) * X + 1): I(L) = X - Y` |
| 50000 | `LF.LIB` | `YY = I(Y): ... X = INT ( RND (1) * YY + 1): I(Y) = YY - X` |
| 50010 | `LF.LIB` | `YY = PF: ... X = INT ( RND (1) * YY + 1): PF = YY - X` |
| 52010 | `LF.LIB` | `X = 100 * (YY > 100) + YY * (YY < 101): X = INT ( RND (1) * X + 1)` |

In all four the multiplier is a **variable** — the holding, or the computed hundred —
and the addend is 1. The code has:

```python
amount = num.int_(num.add(
    num.mul(c.rng.rnd1(f"{tag} amount {item}"), num.ONE), num.ZERO))
```

at `river.py:337` (which serves `RIVER.LIB` *and* `FLOAT`, since both share the routine),
`lf.py:46`, `lf.py:55` and `lf.py:108`. `INT(RND * 1 + 0)` is **0 for every draw**.

So the game announces losses and applies none. Holding ten bullets and losing them
prints " 0 bullets" and leaves the ten where they were. This reaches every ford three
feet or deeper (`50040`), the rough-ford tip (`50070`), the float tip (`50085`), the
ferry breaking loose (`50120`), every wagon fire (`50000`, `50010`) and the thief
(`52010`). The draw *count* is right, which is why the existing tests pass: the number
is spent and then discarded.

The tell is that `trail.lose_days` gets line 550's `XX = INT ( RND (1) * Z + 1)` right —
it uses the variable and `+ 1`. Four sites were written as constants where four others
were not, and nothing in the suite could tell the difference.

### 19.2 The top-ten list is corrupted — `win.insert`

```
510 G = 0: FOR L = 9 TO 1 STEP - 1: IF SC > VAL (HI$(L,1)) THEN FOR L1 = 0 TO 2:HI$(L,L1) = HI$(L - 1,L1): NEXT
515 IF SC <= VAL (HI$(L,1)) THEN G = L: L = 0
520 NEXT: HI$(G,1) = "": HI$(G,2) = "": HI$(G,0) = "": ...
```

`L` is the **destination**: `HI$(L) ← HI$(L - 1)`, with `L` counting down from 9, so the
list shifts *down* and the leader stays at index 0. The loop runs 9 to 1 — index 0 is
never a destination.

```python
for i in range(9, -1, -1):
    if score > entries[i][1]:
        if i < 9:
            entries[i + 1] = list(entries[i])     # destination i+1, source i
        place = i
```

`i` is the **source**, so the shift runs the wrong way, the test is applied to the row
that is about to be overwritten rather than the row it is compared against, and index 0
is included. With a score of 5000 against Meek 7650 / Hastings 5694 / Sublette 4138 the
original produces `Meek, Hastings, PLAYER, Sublette` and the code produces
`Meek, PLAYER, Sublette, Sublette` — one row destroyed, one duplicated, one dropped.

`tests/test_endings.py` misses it because it seeds ten *equal* scores and uses a score
that beats all of them, so the loop always runs out at the top and the corruption is
invisible; it then asserts only that the list is sorted, which the corrupted list is.

This affects every arrival, not an edge case: the best a winning party can bring is
around 4,000 against a 7,650 top entry, so the mid-list path is the normal one.

### 19.3 The raft's fill-test draws vanish once a rock exists — `floatraft.py`

```
1070 TC = TC + C1: IF NOT FL(C0) AND INT (100 * RND (C1) + C1) <= RF THEN Z = C0: GOSUB 300
1075 IF NOT FL(C1) AND INT (100 * RND (C1) + C1) <= RF THEN Z = C1: GOSUB 300
```

No short-circuit, so **both** draws happen every pass whether or not the slot is full.
The code guards the whole body:

```python
for slot in (0, 1):
    if rocks[slot] is None:
        if num.le(num.int_(...c.rng.rnd1(f"1070 rock {slot}")...), ...):
```

so a pass with one rock alive spends two draws instead of four. Measured with a counting
generator: with no rocks ever spawning, 226 passes spend 452 draws and are correct; with
rocks spawning and surviving about thirty passes, the whole game spends **16** draws
where 452 are required. Every rock roll, every collision roll and the `950` loss roll
after that is then taken from a different point in the stream.

The comment two lines above the `if` states the correct rule, and so does the module
docstring. `tests/test_endings.py` asserts 226 draws per slot but runs at a generator
value where no rock ever spawns, so both slots are always empty and the short-circuit
never shows.

### 19.4 The fort store reads two digits where `& INP` allows one — `fortbuy.py`

`BUY.LIB` 50010 is `& INP,1,"-18",1,Z$` — **length 1**. `fortbuy.py:58` reads
`c.ui.key(ALLOWED["FORT"], 2, ...)`, so `12` is accepted, `L = 12`, and the price lookup
at `G.PRICE[11]` raises an uncaught `IndexError` instead of the listing's subscript
error being caught by `ONERR GOTO 32000` and shown on the game's error screen. Both
`TerminalUI` and `ScriptedUI` honour `maxlen`, so this is live in every front end.

### 19.5 The rock's row is one foot too high — `floatraft.py`

`310 RX(Z) = 0:RY(Z) = 50 + INT (120 * RND (1) + 1)` — the `+ 1` is **inside** the `INT`.
The code has `50 + INT(120 * RND)`, so the rock is placed at 50…169 instead of 51…170,
one foot nearer the top of the screen, which moves its collision box. The draw itself is
present and in the right place. The sibling rolls — `INT(100 * RND + 1)` at 300 and
`INT(10 * RND)` at 300 — are both right, so this one is isolated.

### 19.6 A rock is cleared before the collision test, and on the wrong inequality — `floatraft.py`

```
600 IF RX(Z) < 240 AND RY(Z) > 10 THEN RETURN
610 FL(Z) = 0: RETURN
```

called from `1160`/`1165`, i.e. **after** the collision test at `1120`/`1130`. The code
clears on `x > 240 or y < 10` (should be `x >= 240 or y <= 10`) and does it in the move
loop, before the collision loop. A rock born at `RX = 0` sits at exactly 240 after
thirty passes, since `XI = 8`; so the strict inequality and the ordering each change
which passes can produce a collision.

### 19.7 The crossing animation's draws are spent on the wrong side of the crossing — `river.py`

`OREGON TRAIL` 3504 is
`GOSUB 50000:W1 = 0: GOSUB 190: & APP,"CROSS.LIB": GOSUB 50000: GOSUB 190: GOSUB 900: …`

`RIVER.LIB` 50000 — the menu **and** the crossing — runs to completion first, and only
then is `CROSS.LIB` appended and called. `river.crossing` calls `cross.first_half(c)`
*before* the menu and `conditions`/`crossing`, and `cross.tail(...)` afterwards, so the
106 draws land before `50060`, `50070` and its `V` draw, `50101`, `50120` and `50130`
rather than after them. Every river draw is then taken from the wrong number.

`cross.py` asserts in a comment that the listing calls `CROSS.LIB` before the menu, which
3504 contradicts. Separately, `GAPS.md` says these draws "are **not** implemented" while
`cross.py` spends 106 / 122 / 66 — the two disagree, and that needs settling before
anyone calibrates against a trace.

### 19.8 The trader names the wrong goods — `trade.py`

`TRADE.LIB` 50030 sets `L = X + 2` and 50032 `L = Y + 2`, then both `GOSUB 50250`, which
reads `Z$ = I$(L)`. The inventory names are `I$`, whose indices are 2…8. `trade.py` passes
the `S$` index straight through: `_line(0, give, y)`. Indices 0 and 1 coincide with
`Wagon` and `oxen`, so the first two goods read correctly by luck and the rest do not:

| offered | prints | should print |
| --- | --- | --- |
| ammunition | `40 oxen` | `40 bullets` |
| wagon wheels | `1 set of clothing` | `1 wagon wheel` |
| food | `100 wagon axles` | `100 pounds of food` |

The inventory arithmetic beside it, `st.I[y + 2] += give`, is right. Wording only.

### 19.9 Four more cosmetic divergences

* `WIN` 29000 has `doubled`; `win.py` prints "double" ("your points are double").
* `BUY.LIB` 50020 sets `A$ = " many"` before the quantity prompt, and 50030 prints
  `"You cannot afford that"A$"."`. `fortbuy.py` always prints "You cannot afford that."
  — the two-unit pre-check at 50015 has no suffix, the quantity check should.
* `WIN` 621 prints `RIGHT$` of the cash figure after `"     $"`. `win.py:109` prints
  `"     $ cash"` with the amount missing.
* `RIVER.LIB` 50015 builds `Z$ = "-1" + STR$(Z)` from the option count, which is 4 at the
  Kansas and Big Blue and 5 elsewhere. `ALLOWED["RIVER"]` is `"-15"` everywhere, so a
  fifth answer is accepted at a four-choice river instead of being refused.

Also: `floatraft.py:101` clears a rock with `rocks.index(r)`, which finds by value — two
rocks at identical coordinates in one pass would clear slot 0 twice. Latent and rare, but
`enumerate` is in use twenty lines below. And `floatraft.py:193` indexes `N$(NP)` with
`NP` possibly -1, where Python wraps to the last name and Applesoft raises BAD SUBSCRIPT;
unreachable, noted only because it is a real semantic difference.

### 19.10 A GAPS entry that had become false

`GAPS.md` 5 carried a "bug reproduced on purpose": that `Q` is one variable used both as
the map's `Q()` and as a scalar, so a fort purchase makes the map plot a price tier. That
was retracted in 6.2 — `Q` and `Q()` are separate variables — and `state.py` now holds
`Q` and `Q_arr` apart. The GAPS row and the comment in `maplib.py` still described the
old behaviour as reproduced. Both are corrected: the row now records the retraction and
keeps only the part that is real, the trade's rounding of the holding.

### 19.11 Checked and found correct

`fortbuy.py` and `trade.py` draw counts and order: BUY.LIB 50000-50035 has **no** `RND`
at all and neither does the Python; `trade.py` spends exactly five in listing order
(50010 X, 50010 Y, 50011 ratio, 50027 refusal, 50031 He/She), and the 50027 toss is
correctly placed in the left operand so the refusal draw survives. `RIVER.LIB` 50060,
50070, 50085, 50101, 50120, 50130 each spend exactly one draw in the listing's order and
before the loss draws they gate; `50175`'s `FOR L = (NP > 1) TO NP - 1` start, the
`V = V * (Z < 11)` cap and the singular/plural rewrites are right. `win.py` has no draws,
as the original does not, and every `PEEK`, word split and points multiplier is exact.

## 20. A third audit, from new tests derived off the listing

The first two audits read the code against the listing. This one does something
different: it wrote a new test file, `tests/test_derivations.py`, in which every
expectation is worked out **from the BASIC line and not from the code**. The tests are
of three kinds the suite did not have:

* **Conservation laws.** `LF.LIB` 50000 prints `STR$(Y)` and then does `I(Y) = YY - X`.
  So if a routine reports a quantity, the holding must fall by that quantity. A
  transcription can spend exactly the right number of draws, keep every message, and
  still lose nothing -- and only a conservation law notices.
* **Unconditional statements.** An `IF` whose false branch falls off the end of the
  line still runs what follows. `RATION.LIB` 50040 ends `... GOSUB 650: RETURN`.
* **Static shape.** Four of the defects in 18 and 19 were Python's own semantics
  leaking in. Those are visible in the source without running anything, so two of the
  tests refuse the shapes outright and a third records how many `and` expressions
  remain to be argued with.

It found four more defects, one of them serious, and re-found 19.1 by an independent
route. **No code was changed**; nothing in the paper was touched.

### 20.1 Only the first ration can ever be chosen — `ration.py`

```
50040 … & INP,1,"-13",0,Z$:Z$ = Z$ + "":Z = LEN (Z$):R = Z * VAL (Z$) + R * NOT Z:
& CO,X,Y: PRINT R: GOSUB 650: RETURN
```

`R` is **`LEN(Z$)` times `VAL(Z$)`**, not `LEN(Z$)`. `Z` is the length of the answer and
`VAL` is the digit, so 1, 2 and 3 select rations 1, 2 and 3.

```python
st.R = num.parse(str(len(a)))
```

Only `LEN`. Answering "2" or "3" therefore sets `R = 1`. Since line 660 is
`FC = NP * (4 - R)`, the party always eats three pounds a head, and **rations 2 and 3
are unreachable in the finished game** — the player can open the screen, choose, and
watch nothing change. The new test found it immediately: `assert 1 == 2`.

This is the same shape as 19.1 — one term of a product kept, the other dropped — and
like 19.1 it is invisible to every draw-count test, because no draw is involved at all.

### 20.2 The speed is not recalculated on an empty answer — `ration.py`

Same line 50040. `GOSUB 650` sits after the whole expression and before the `RETURN`,
so it runs whatever was typed. The code calls `trail.speed(c)` only inside the branch
where a valid digit came back, so declining the question leaves `FC` stale.

### 20.3 The first grave written to disk side two lands in side one's slot — `files.py`

`FLIP.LIB` 50030 positions with `& TPTR, L * 49`, so the two records are 49 bytes apart.
`Files.write_tomb` does the same arithmetic:

```python
raw = bytearray(self.tomb.read_bytes()) if self.tomb.is_file() else bytearray()
off = side * TOMB_RECORD_SIZE                      # 49 for side two
raw[off:off + TOMB_RECORD_SIZE] = record...
```

When the file does not yet exist, `raw` is empty and Python **clamps the slice start to
the end of the buffer**: `bytearray()[49:98] = b"A" * 49` produces a 49-byte buffer
holding the record at offset **0**. Verified:

```
write side 2 only:  file is 49 bytes
read_tombs(0) = {'segment': 1716, 'miles': 100.0, 'name': 'Zeke', …}
read_tombs(1) = None
```

So a party whose first death happens on disk side two files the stone under side one:
`SN(0)` and `ML(0)` get the wrong segment, `find_grave` compares against the wrong slot,
and side two reads as having no grave at all. Writing side one first and then side two
works, which is why play is usually unaffected — landmarks 0 to 4 are on side one, so
most games write there first. A party whose first burial is on side two is not.

This is the only one of the twenty defects found that is a Python container-semantics
mistake rather than an Applesoft-reading mistake.

### 20.4 Three goods are pluralised wrongly — `lf._line`

```
50250 Z$ = I$(L):Z = (F = 1) * ((L = 8) + (L = 3) + ("s" = RIGHT$(Z$,1))): IF NOT Z THEN RETURN
50255 IF L <> 8 AND L <> 3 THEN Z$ = LEFT$(Z$, LEN(Z$) - 1 - (L = 2)): RETURN
50260 Z = 6 - 2 * (L = 3):Z$ = LEFT$(Z$,Z - 1) + RIGHT$(Z$, LEN(Z$) - Z): RETURN
```

The listing appends nothing when the name already ends in "s", and drops the trailing
"s" for the singular of anything that is not food or clothing. The names come from
`FLOAT` 25000: `Wagon, oxen, sets of clothing, bullets, wagon wheels, wagon axles,
wagon tongues, pounds of food` — so items 5, 6 and 7 all end in "s".

`_line` handles items 2, 3, 4 and 8 explicitly and falls through to
`word + ("s" if n != 1 else "")` for the rest, which gives **"1 wagon wheels"** and
**"3 wagon wheelss"**. Same for axles and tongues. The conservation test's failure
message is the evidence:

```
'0 sets of clothing\n0 bullets\n0 wagon wheelss\n0 wagon axless\n0 wagon tonguess\n0 pounds of food'
```

The two earlier audits recorded `_line` as correct; they checked items 3 and 8, where
the special forms apply, and did not try a plural of "wagon wheels".

### 20.5 19.1 confirmed again, and the static checks

The conservation law failed on exactly the defect 19.1 describes, from the opposite
direction — 19.1 was found by reading the expression, this time by noticing that
holdings did not move:

```
'0 sets of clothing' was reported but the holding is still 7
reported 0 of 50.0
```

Both static checks now fail on the four known short-circuits and constant
substitutions (18.3, 18.4, 19.1 ×4, 19.3), which is the intent: they are a standing
refusal, so a fifth instance cannot be added without the suite objecting. Once the code
is fixed they will pass on their own.

### 20.6 What the new tests could not check

`talk.talk` and the dialogue offsets are exercised only through the file layer, which
`GAPS.md` already records as a stand-in for `TALK.LIB` 50000's `(LM - S * 5) * 768 +
A * 256`, so a test of the arithmetic would be testing the test. The three tests that
did fail for the wrong reason — writing a grave to side two of a file that does not yet
exist — turned out to be finding 20.3, which is why the setup was kept.

Nothing here is fixed. 20.1 and 20.3 are the two that change what a player experiences.

## 21. A fourth audit, from the paper's own rules and tables

The three before this read the code against the BASIC listing. This one reads it
against **the paper**, because that is where the rules are stated. `paper/01-paper.md`
2.5 sets out eight properties of Applesoft a translation must respect; 6.1 and 6.2 give
the climate tables; 13 lists the bugs that are supposed to be reproduced. New file:
`tests/test_paper_rules.py`, whose every expectation is transcribed from the paper.

**No new code defect was found, and that is the result worth having.** Five of the
paper's eight rules had never been tested against the code at all. All five hold:

* **A comparison is a number, 1 or 0.** Line 3244's `V = BS * (1 - .1 * H0) * NOT SD * Z`
  multiplies by `NOT SD`. If `NOT` were the -1 of some languages, `V` would be negative
  on every travelling day. `FINDINGS.md` 18.9 recorded this reading as *inferred from
  behaviour, never tested*. It is now tested: the wagon moves forwards, and the
  `1.1 * V > D` cap at 3246 fires.
* **`ON n GOSUB` does nothing when `n` is 0 or past the last target.** `RIVER.LIB` 50030
  is `ON V GOSUB 50035, 50080, 50130, 50100` -- **four** targets -- while 50011 prints
  **five** choices wherever `RC(RC,5)` is set, the fifth being `T$(3)`, "get more
  information". So the fifth choice indexes past the end, spends nothing, and
  `ON F GOTO 50010` returns to the menu. The code has no branch for it, so the menu
  loop simply repeats, which is the same thing. Worth stating because it looks like a
  bug and is not one: **fixing it would be a divergence.**
  `V = V + (V = 3) * (RC(RC,5) = 2)` can only turn 3 into 4, so `V` never exceeds the
  fourth target.
* **A subroutine runs on until it meets `RETURN`.** `TOMB.LIB` 50000 has none, so a
  call falls into 50005 and the member is removed. Line 3504's
  `FOR L1 = 0 TO 4: Q = L1: ON (H1(L1) = -2) GOSUB 50000` therefore removes every
  drowned member, and `trail.remove_drowned` does. Tested at the right routine: my
  first attempt tested `tomb.all_dead`, which models 50010-50040 and never removes
  anybody -- the removal is its caller's, and `illness.die` does it before calling.
* **`INT` rounds down.** `num.int_(-2.7)` is -3, and `num.as_int`, which is what `POKE`
  wants, truncates toward zero instead. They are different functions and must not be
  confused.
* **String positions in `MID$` count from 1.** Line 105's
  `MID$ (WC$(ZO), AM * 2 + Z - 1, 1)` is a zero-based offset of `AM * 2 + Z - 2`, which
  is what `trail.fn_w` uses, and its comment says why.

**The paper's Table 13 matches the code in all 72 entries.** Six strings of 24
characters, one temperature character and one rain character per month, transcribed
from the paper's table and compared: no disagreement, including the paper's worked
example -- row 0 in January, codes 59 and 43, minimum temperature 9 degrees and rain
chance 0.039.

There is a second `FN W` in the listing, under `MENU` rather than `OREGON TRAIL`, and
it is a different function: `VAL ( MID$ ( WC$(ZO), (AM) * 2 + 1 + Z, 1))`. The code
implements the `OREGON TRAIL` one, which is the one the paper's 6.2 quotes. Worth
recording because the two differ in both the offset and the arithmetic, and picking the
wrong one would shift every temperature.

### 21.1 Two documents the paper caught

* **`GAPS.md` 5 said "All nine from paper section 13".** The paper's table now has
  **eleven** rows: the trade that rounds the holding, and the thief that names no item.
  The count was a leftover from before those were added, and it understated what the
  code reproduces. Corrected, with the note that it should not be read as a shortfall.
* **`trail.remove_drowned`'s docstring still argued the retracted `Q` claim.** It ended
  "What `Q`'s double life really costs is the map -- see `GAPS.md`", which 6.2 retracted
  and which `GAPS.md` 5 no longer says. The routine is unaffected -- line 3504 assigns
  `Q` from its own loop counter before using it -- so the comment was simply wrong.

### 21.2 One ambiguity in the paper's Table 12, recorded rather than resolved

Table 12 gives the climate zone by "segments leaving landmarks": zone 0 covers segments
0 to 2, zone 1 segments 3 to 5, zone 2 segments 6 to 10, zone 3 segments 11 to 13, zone
4 segments 14 to 16. Line 1000 computes the zone from the **landmark**,
`ZO = (LM > 2) + (LM > 5) + (LM > 10) + (LM > 13)`, which gives 0-2, 3-5, 6-10, 11-13,
14-17 by landmark.

Those agree only while landmarks and segments are numbered alike, and they stop being
alike at South Pass: the Green River route skips Fort Bridger, so segment 8 never
happens and segment *n* leaves landmark *n+1* from there on. On that route the code
gives zone 2 to segments 6, 7, 10 and 11, where the table says 6 to 10.

The header "segments leaving landmarks" is the ambiguity: the ranges are landmark
ranges. The code follows the listing, which is unambiguous. This is recorded in
`GAPS.md` so that a reader comparing the code with Table 12 does not conclude the code
is wrong, and **the paper is not edited** -- if the table is meant to be read as
segments, that is the author's call.

## 22. Two bugs found by playing it, not by testing it

Both reported from a real session, and both had passed every test in the suite. They
are recorded here rather than in 18 to 20 because the method was different: nobody was
reading the listing, somebody was pressing keys.

### 22.1 "Press SPACE BAR to leave store" did not wait — `buysupplies.py`

`BUY SUPPLIES` 3030:

```
3030 … PRINT "Press SPACE BAR to leave store":Z = USR (1): & CO: PRINT "Which item would you like to "A$"? ";: GOSUB 250: …
```

**`USR (1)` waits for a key.** Line 950 uses it for "Press SPACE BAR to continue", and
`WIN` 955-957 is the routine itself: `955 IF PEEK (975) THEN & PT,1,1`,
`956 Z = USR (2): IF Z < 128 THEN 955`, `957 IF Z = 147 THEN …`. So `USR (1)` is
"get a key", `USR (2)` is "peek the keyboard", and 956 loops until a key arrives with
the high bit set -- which is any ordinary key. **Space satisfies it.** Return does too.

The code printed the prompt and then called `ui.flush()`, on the reading that `USR (1)`
clears the keyboard. The effect is exactly what was reported: the store said "Press
SPACE BAR to leave store", pressing space did nothing whatever, and Return appeared to
work -- because Return was not leaving the store at all, it was answering the *next*
question, "Which item would you like to buy?". The player was answering one prompt late
and reading it as a dead key.

Worse, there was a test asserting the wrong reading.
`test_the_store_never_asks_for_a_key_it_did_not_ask_for` said `USR (1)` "clears the
keyboard; it is not a request for a keypress", and blamed the wait for swallowing the
player's number: "Treating the label as a wait inserted a keypress between the two, and
that is what swallowed the number the player typed." The observation was right and the
diagnosis was wrong. A test that encodes a misreading does not merely fail to catch the
bug -- it **argues for keeping it**, and this one did. It is replaced by
`test_the_store_waits_for_one_key_at_the_space_bar_prompt`, which spies on `wait_key`
and asserts the prompt is asked for.

### 22.2 "She will trade you 1 ." — nothing named

`TRADE.LIB` 50032 is `F = I: L = Y + 2: Z$ = "He": IF RND (1) > .67 THEN Z$ = "She":
PRINT Z$" will trade you ";: GOSUB 50250: PRINT F" "Z$"."`, and 50250 opens with
`Z$ = I$(L)`. The inventory names are `I$`, indexed **1 to 8**:

```
I_NAMES = ['', 'Wagon', 'oxen', 'sets of clothing', 'bullets',
           'wagon wheels', 'wagon axles', 'wagon tongues', 'pounds of food']
```

so the index is `Y + 2`. The code passed `Y` -- the `S$` index, 0 to 6. For `Y = 0` that
is `I$(0)`, **the empty string**, and the sentence came out as

```
You meet another emigrant who wants 176 pounds.
She will trade you 1 .
```

with nothing at all named. `Y = 1` gives `I$(1)` = "Wagon", so it read as "1 Wagon"
where the original says "1 oxen". The inventory arithmetic beside it,
`st.I[y + 2] += give`, was always right; only the wording was wrong.

This is 19.8, found by reading. The report adds something reading could not: that the
failure mode is not a *mis*name but *no* name, because index 0 of that particular table
is the empty string that the data format leaves for one-based indexing. A test asserting
"the name is one of the goods" would have passed for `Y = 1`. The test now extracts the
name and requires it to be non-empty.

## 23. Three more from playing it: the death messages, and a seed that never moved

All three reported from a real session. The first two are one root cause, and the
third explains an observation that had been sitting in plain sight.

### 23.1 A death was announced twice, and the first announcement was wrong

The report was three consecutive screens:

```
 Zeke has a snakebite.
 Zeke died
 Zeke has died.
```

`OREGON TRAIL` 10300 and 10310 are the only places a person is named, and both are one
expression:

```
10300 … Z$ = N$(Z) + " has ":A$ = IL$(V): IF H1(Z) THEN A$ = "died":V$ = Z$ + A$ + ".":H1(Z) = -1: GOSUB 710:Q = Z: GOSUB 8000: …
10310 V$ = Z$ + A$ + ".": GOSUB 710:H1(Z) = V:H2(Z) = 10: ON NOT SD GOSUB 400: RETURN
```

`Z$` is the name **plus " has "**, and the full stop is added once. So the two messages
are "Zeke has *disease*." and, when an illness is already running, "Zeke has died." --
and then `GOSUB 8000`, which is `GOSUB 33000: & APP,"TOMB.LIB": GOSUB 50000: GOSUB 190:
GOSUB 650: RETURN` and **prints nothing**.

The code had all three wrong:

| where | was | should be |
| --- | --- | --- |
| `illness`, illness branch | `name + " " + IL_NAMES[d]` | `name + " has " + IL_NAMES[d] + "."` -- "Zeke exhaustion." |
| `illness`, death branch | `name + " " + "died"` | `name + " has died."` |
| `die` | printed `"{name} has died."` | printed nothing -- 10300 had already said it |

So a member who died got "Zeke died" from the first and "Zeke has died." from the
second: **the right sentence, immediately preceded by the wrong one.** The disease
branch had dropped the same " has ", which is why the illness message read "Zeke
exhaustion."; it went unnoticed because the snakebite in the report came from the
*event* at 10100, which builds its own text and does it correctly.

The drowning path is silent in both the listing and the code, and now there is a test
saying so: line 3504's `GOSUB 50000` falls into 50005, which removes the member and
prints nothing -- the name is in the loss list from 50175.

### 23.2 Why the same member died on the same day twice

The report noted that Zeke died at the start of the game "just like in the previous
game", and suspected the generator. **The generator was reseeded identically every
run.**

`MENU` 1015 is the only reseeding in the game:

```
1015 … & INP,1, CHR$ (1) + "-14",1,Z$: … Z = RND (-( PEEK (78) + PEEK (79) * 256)): …
```

and on the Apple II addresses 78 and 79 are the counter the keyboard routine keeps
**while it waits for a key**. The paper's 3.1 says as much: the seed is fixed by how long
the player took to press the key, which is the whole reason two playthroughs differ.

`Memory.keyboard_counter` read those two bytes correctly, and **nothing ever advanced
them**. Only the test suite set the value. So `seed_from_keyboard` was handed the same
number on every run, the generator started from the same state, and every game was the
same game -- same events, same member, same day.

`Context.__init__` now wraps `key`, `wait_key` and `yes_no` so the counter advances by
the time each prompt actually took, in milliseconds. A scripted front end answers
instantly, so the counter stays put and **the tests remain deterministic**; an
interactive one varies, and two runs of the same answers now diverge.

That last point is the design constraint worth recording: a faithful fix here would
have made the test suite non-reproducible if it had counted prompts instead of elapsed
time.

### 23.3 What was *not* wrong

Worth stating, because the report raised it. The opening sequence is correct:
`10900 A$ = "Lose trail":Z = 5: IF RND (1) < .5 THEN A$ = "Wrong trail"` then
`GOSUB 550`, where `XX = INT ( RND (1) * Z + 1)` gives 1 to 5 days -- "Lose trail.  Lose
4 days." is the listing's own text and its own range.

And the death that followed is not a balance bug. Line 3235 is
`IF NOT W1 AND H > 139 THEN GOSUB 10300`, and 3150 caps health at 139 -- so the forced
illness fires only when 3230's `H = .9 * H + …` has pushed health **back above** 139
during the day. A party in good health is made ill on purpose. Zeke had a snakebite
from an event (`H1 = 2`), so 10300's `IF H1(Z) THEN A$ = "died"` killed him on the same
day's check. Correct, and the same in the original.

## 24. Resting did nothing, and the goods had no names

Three reports in one session: the goods were misnamed, resting never improved health,
and the supplies screen read all zeros. Two were real bugs; the third is worth
explaining, because it is the formula behaving correctly.

### 24.1 Resting passed no days at all — `action.do_rest`

```
4505 IF SD THEN F9 = 0:JQ = P:P = 0:ZX = D:ZY = M:D = 0: FOR K1 = 1 TO SD: GOSUB 3100:
     & WIND: GOSUB 250: & CO,,X5: PRINT CE$TD$CC$: NEXT :SD = 0:D = ZX:M = ZY:P = JQ
```

It sets `D = 0` and then calls **line 3100 directly**, once per day. The code called
`trail.daily_cycle`, whose condition is line 3499 -- `L0 = NOT D: NEXT L0` -- and `D` had
just been set to zero, so the loop body never ran.

The effect was that a rest was completely inert: no day passed, no food was eaten, no
date changed, and health stood still. Nine days, then nine days again, gave exactly the
same game. `run_stopped_days` had it right already -- it calls `day_body` -- which is
why a one-day river delay visibly cost food and health while a nine-day rest did
nothing. Two paths to the same place, one of them wrong.

Fixed to follow 4505: save `D`, `M`, `P`, zero `D` and `P`, run `day_body` `SD` times
with `F9 = 0`, restore, and copy `PF` back into `I(8)`. Nine days twice now moves the
date eighteen days, eats 270 pounds of food and takes health from 120 ("very poor") to
18 ("good"), because `H` is **0 when perfect and higher is worse**, and resting removes
the pace penalty, the events and the travel.

### 24.2 "wants 81 pounds" — the goods were named by appending an "s"

`trade._wording` was `G.UNIT[item] + G.PLURAL[item]`, which cannot produce "pounds of
food" or "wagon wheels" at all. Three listing lines decide every one of these nouns, and
the rule is not "stem plus s":

```
50250 Z$ = I$(L):Z = (F = 1) * ((L = 8) + (L = 2) + (L = 3) + ("s" = RIGHT$(Z$,1))): IF NOT Z THEN RETURN
50255 IF L <> 8 AND L <> 3 THEN Z$ = LEFT$(Z$, LEN (Z$) - 1 - (L = 2)): RETURN
50260 Z = 6 - 2 * (L = 3):Z$ = LEFT$(Z$,Z - 1) + RIGHT$(Z$, LEN (Z$) - Z): RETURN
```

Unless the quantity is exactly one, the name is used **unchanged** -- which is how
"pounds of food" and "wagon wheels" come out right. Only the singular is rewritten, and
food and clothing are split into a stem and a qualifier. All seven goods, both numbers:

| `I$(L)` | one | many |
| --- | --- | --- |
| 2 | `ox` | `oxen` |
| 3 | `set of clothing` | `sets of clothing` |
| 4 | `bullet` | `bullets` |
| 5 | `wagon wheel` | `wagon wheels` |
| 6 | `wagon axle` | `wagon axles` |
| 7 | `wagon tongue` | `wagon tongues` |
| 8 | `pound of food` | `pounds of food` |

`lf._line` had its own pluraliser and was wrong in the same way -- "1 wagon wheels" and
"3 wagon wheelss", finding 20.4 -- so it now shares this one implementation.
`tests/test_wording.py` checks all fourteen combinations against a transcription of the
three lines, and checks that the two modules cannot drift apart again.

The call site also had an off-by-one: 50030 builds `L = X + 2` and 50032 `L = Y + 2`, so
the index is the `I$` one, and the code passed the `S$` index. For `Y = 0` that read
`I$(0)`, the empty string, which is the "She will trade you 1 ." of 22.2.

### 24.3 `P5` is 0.5, and I nearly "fixed" it

`3225 Z = FS * P5: IF X OR Y THEN Z = FS + .8`, with `X = (ZC > P5)` at 3215. `P5` looks
like `PEEK(5)`, which is 2 -- and `FS * 2` would double the starve factor every good day
until health collapsed. The paper settles it: 5.2 says "On a day with no food, or with a
clothing penalty above **0.5**, `FS` rises by 0.8. On any other day it **halves**."

So `P5` is one of the authors' symbolic constants -- `C0`, `C1`, `C2`, `C4` and `P5` --
and it is 0.5. The code is right. Recorded because the trap is real: `P5` is the only
one of those names that does not look like the constant it stands for.

### 24.4 The supplies screen is not a bug

The report that everything reads 0 while the money is still there is **consistent with
the formula**. `PF` falls by `FC = NP * (4 - R)` every day, and the party in that
transcript was at "very poor" health in May with 0 food -- a party that bought almost
nothing from the store has starved by then. `PF` is copied back into `I(8)` when the day
loop returns (3499), and the display rounds each holding with `INT (I(L) + .51)` (4110),
which is what `show_supplies` does.

Checked directly: `init_state`, then the store, then `trail.load_state` -- the order
`__main__` uses -- leaves `I(2)` to `I(8)` as `[4, 1, 1000, 1, 0, 0, 1000]`. The store
writes 905 to 912 correctly and the values come back. So the screen was telling the
truth; the party was broke.

One thing that *would* have been a bug, and is not: the store does not credit `I` as it
sells, it POKEs 905 to 912, and `29005` reads them back. A version that skipped
`load_state` after the store would show exactly the all-zero screen that was reported.
