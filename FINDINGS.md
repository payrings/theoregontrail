# FINDINGS.md — what the ROM and the source actually do

Private research notes for the Python rebuild in this directory. Written from
direct execution of a real Apple IIe ROM and from the release 1.4 BASIC listings.

It lives in the repository root rather than in `docs/` because `docs/` holds the
copyrighted reference material and is git-ignored; these notes are my own and
belong with the code they describe.

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

Decoded, the addend is a 5-byte value with exponent byte `$68` (104) and significand
byte `$28` — about **1.9 × 10⁻⁸**. The multiplier is `$98` (152), magnitude about
**6.99 × 10⁶**. So the seed, which lies in [0.5, 1), produces products of order 10⁷
and the addend is eleven orders of magnitude below them. "Almost no effect" is an
understatement, and any implementation that adds a plausible-looking constant will
get a subtly different generator.

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

### 5.1 One event a day, not two (§8.1)

The paper: *"The loop does not stop after the first event. It ends early only when
`B` is above zero … Otherwise the remaining events are still tested, so two events
can occur on one day."*

The code, line 3180, ends the body of the event loop with:

```
L8 = 20
```

unconditionally — it is a separate statement after the `IF B > 0 THEN GOSUB 4000`,
not inside it. `NEXT L8` then makes `L8 = 21`, and the loop is `FOR L8 = C0 TO RE`
with `RE = 14`, so 21 > 14 and the loop ends. **At most one event fires per day.**
`trail.event_loop` breaks after one.

This is the most consequential divergence in the rebuild, because it changes the
whole draw sequence: fifteen draws either way, but which events get tested. If the
paper is right about the shipped game, this needs revisiting.

### 5.2 The rough ford draws one chance, not one per good (§9.3)

The paper: *"Rough: 16% chance of tipping, then each good has a 10% to 40% chance of
a random loss."*

Line 50070 draws `V = .1 + RND (1) * .3` **once**, then calls the goods loop, so all
six goods share that one value. The draw order is: tip?, V, then six goods draws.

### 5.3 The route is 1,821 miles, not 1,771 (§4.1)

The paper's Table 8 gives the segment lengths; summing them along the shortest route
(0,1,2,3,4,5,6,7,10,11,12,13,14,15,17) gives:

| | miles |
| --- | --- |
| via the Green River to The Dalles | **1,821** |
| then segment 18, the Barlow Road | **1,921** |
| via Fort Bridger instead (0..7,8,9,11..15,17) | 1,964 |
| **the paper states** | **1,771 and 1,871** |

Exactly 50 miles out on both totals, so it looks like a single arithmetic slip rather
than a different table. The game uses `LM(Z,0)`, so the table is what plays. Worth
checking against a real run.

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

### 5.5 The map's third choice takes the first segment

Line 2110 offers ". see the map" as choice 3 and sets `Z$ = "3"`. Line 1015 then runs
`IF Z = 3 THEN GOSUB 4200`, which shows the map, and falls through to line 2200 with
`Z` still 1 — so **choice 3 shows the map and then takes the first segment**, not the
second. Reproduced.

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

### 6.1 The action menu swaps "Buy supplies" for the hunt when leaving a fort

Line 4040 builds the menu, and line 4090 dispatches:

```
Z = Z * ( VAL(Z$) > 7) + VAL(Z$)
ON Z - 1 GOSUB 4100,4200,4300,4400,4500,4900,4700,4800,4600
```

`Z` is 0 at a landmark and **2 on the trail**. Leaving a fort on the trail, the menu
shows both "Buy supplies" (choice 8) and "Hunt for food" (choice 9), and:

```
choice 8:  Z = 2 * 1 + 8 = 10  ->  ON 9  ->  4600, the hunt
choice 9:  Z = 2 * 1 + 9 = 11  ->  ON 10 ->  past the end of the list, nothing happens
```

So on the trail leaving a fort, **"Buy supplies" runs the hunting game and "Hunt for
food" does nothing at all.** At a landmark the same two choices dispatch correctly
(`Z = 8` → `ON 7` → buy; `Z = 9` → `ON 8` → hunt), which is why it went unnoticed.
`action.action_menu` reproduces it and says so in the function.

### 6.2 `Q` is one variable used as an array *and* as three scalars

`OREGON TRAIL` 29000 does `DIM Q(16)` and uses `Q(0 to Q1-1)` as the landmark history
that `MAP.LIB` plots. But:

* `BUY.LIB` 50003 does `Q = (LM > 2) + (LM > 4) + ...` — the fort's price tier,
  which writes `Q(0)`;
* `TRADE.LIB` 50011 does `Q = INT(I(X+2) + .5)` — the player's rounded holding,
  also `Q(0)`;
* the caller at `OREGON TRAIL` 3504 does `Q = L1` in a loop to index the drowned
  member, and `TOMB.LIB` 50005 uses `Q` as that index.

Two consequences, one real and one cosmetic. **The real one is a trade**: line
50035 does `I(X+2) = Q - V`, so an accepted trade writes the *rounded* figure back
into the holding -- five and a half oxen become six minus whatever was taken. The
cosmetic one is that **a fort purchase loses the map's first landmark**, since
`MAP.LIB` plots from `Q(0)`.

I also thought a third followed: that a fort tier of 6 sitting in `Q` when a party
drowns would make `TOMB.LIB` 50005 subscript outside `DIM H1(4)` and raise error 5.
It does not. Line 3504 is `FOR L1 = 0 TO 4: Q = L1: ON (H1(L1) = -2) GOSUB 50000` —
the subscript is `L1`, and `Q` is assigned from the loop counter before it is used,
so it can never be stale there. `GOSUB 50000` has no `RETURN`, so it falls through
into 50005 and buries the member as intended.
`tests/test_rng.py::test_the_Q_loop_overwrites_itself_so_there_is_no_bad_subscript`
keeps the claim retracted.

`state.Q` is one array and both scalar uses write `Q(0)`, so all of this is
reproduced rather than tidied away.

`B` has the same shape — the travel screen's five label columns (`B(0 to 5)`,
Appendix E.5) and the cannot-continue flag (2, 5, 6, 7, or 1 for "Return pressed") —
but the damage there is cosmetic, so the label columns are kept separate.

`T$` is a third: it is the travel screen's six values, `RIVER.LIB`'s six menu labels
and `LF.LIB`'s ten loss lines, all at once, with residue between uses. `LF.LIB` 52030
always prints `T$(0)`, so an empty theft reads *"A thief comes during the night and
steals ."* with nothing after it. That is in the shipped game.

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
`.9`, which line 3230 uses every day, is `80 66 66 66 66` = 0.9000000074, so
`.9 * 20` is **not** 18 — it is 18.0000000075. A test asserts this deliberately.

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
* `FL(0)` and `FL(1)` are the two rock slots; `NR = -1` at line 1060, so the collision
  loop at line 500 (`FOR A = 0 TO NR`) **never executes**. Rock collisions come only
  from lines 1120 and 1130. Dead code in the original.
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
