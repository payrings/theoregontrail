# Peer review — *The Oregon Trail on the Apple II (1985): An Analysis of Source, Data and Algorithms for Replication in Other Languages*

Reviewer: automated verification pass. Every finding below was checked against
the release 1.4 BASIC source listings and, for section 12,
against `rom/apple2e.rom` disassembled **and executed** under py65.

**Recommendation: accept subject to major revision.** One serious error (§8.1), one
table error that will mislead implementers (Table 12), and several smaller ones. The
paper's central thesis is correct and is now empirically supported.

---

## 1. Errors in the paper

### 1.1 §8.1 — "two events can occur on one day" is false, and is contradicted by the code printed on the same page

Paper:

> "The loop does not stop after the first event. It ends early only when `B` is above
> zero… Otherwise the remaining events are still tested, **so two events can occur on
> one day**."

Paper's own quoted source, `OREGON TRAIL` 3180:

```
3180 HR = 0: IF NOT SD THEN FOR L8 = C0 TO RE: IF RND (C1) < RE(L8) THEN … GOSUB 300: L8 = 20
```

Applesoft has no block structure: an `IF … THEN` clause runs to the end of the line.
So `L8 = 20` is **inside** the firing branch and runs unconditionally whenever an event
fires, whether or not `B > 0`. `NEXT` then sets `L8 = 21`, and the loop is
`FOR L8 = C0 TO RE` with `RE = 14` (Appendix E.1, Table E1), so `21 > 14` and the loop
ends. **At most one event fires per travelling day.**

This is the most consequential error in the paper, because it changes the draw count.
It is not "15 draws either way": the loop draws once per event *tested*, so a day is
`k + 1` draws where `k` is the index of the first event that fires, and 15 draws only
when nothing fires. Appendix G.3 ("1 per event tested, 15 if the loop runs to the end,
plus the event's own draws") already describes this correctly and needs no change.

**Fix:** rewrite the §8.1 prose. Delete "two events can occur on one day". Add the
explicit draw count.

### 1.2 Table 12 — the "Segments leaving landmarks" column is wrong for zones 2, 3 and 4

The column lists **landmark** numbers, not segment numbers. Deriving it from line 1000
(`ZO = (LM > 2) + (LM > 5) + (LM > 10) + (LM > 13)`) and Table 7:

| Zone | Paper says | Actual segments | Arrive at |
| --- | --- | --- | --- |
| 0 | 0 to 2 | 0–2 ✓ | Fort Kearney |
| 1 | 3 to 5 | 3–5 ✓ | Independence Rock |
| 2 | 6 to 10 | **6–11** | Fort Hall |
| 3 | 11 to 13 | **12–14** | the Blue Mountains |
| 4 | 14 to 16 | **15–18** | the Willamette Valley |

The prose in the same cells ("Independence Rock to Fort Hall") agrees only with 6–11, so
the column contradicts its own descriptions. An implementer using this column assigns
climate row 2 to segment 11 and row 3 to segment 14, both wrong — Fort Hall is zone 3
(`11 > 10`) and the Blue Mountains is zone 4 (`14 > 13`). Segment 15 and 16 both leave
the Blue Mountains; segment 18 only exists because The Dalles has an outgoing segment.

### 1.3 §9.3 Table 18 — the rough ford draws one chance, not one per good

Paper: "Rough: 16% chance of tipping, then **each good has a 10% to 40% chance** of a
random loss."

`RIVER.LIB` 50070:

```
50070 A$ = "It was a rough crossing…": IF RND (1) < .16 / IX THEN … V = .1 + RND (1) * .3: GOSUB 50205
50205 FOR L = 3 TO 8: X = I(L): IF X AND RND (1) < V THEN …
```

`V` is drawn **once per tipping** and reused for all six goods. Appendix G.5 has this
right. Table 18 as written costs a reimplementer six extra draws per tipping, which
desynchronises the whole `RND` stream.

### 1.4 §12.2 — literals are not re-converted on every execution

Paper: "Numeric constants in the program text are converted from decimal digits **every
time a line runs**."

They are not. Applesoft converts a literal once, when the line is tokenised, and stores
the resulting 5-byte FAC inline in the program text; `LIST` reconstructs the printed
form from those bytes. The sentence also contradicts the paper's own explanation for
holding `C0`–`C4` and `P5` in variables, which is about speed, not re-conversion.

Practical impact is nil — the same ROM routine yields the same bytes — but the statement
misdescribes what a replica must implement.

The *conclusion* drawn from it is correct, and I confirmed it against the ROM:
`.8 = 80 4C CC CC CD = 0.8000000000465661`, `.2 = 7E 4C CC CC CD = 0.20000000001164153`,
`.1 = 7D 4C CC CC CD = 0.10000000000582077` — none the nearest double.

### 1.5 §2.1 — "fourteen small BASIC libraries", then lists fifteen

`COMMON, RIVER, CROSS, BUY, TRADE, TALK, HUNT, MAP, PACE, RATION, PART, LF, TOMB, END,
FLIP` = 15, matching the 15 distinct `## …LIB` sections in the BASIC listings.

Related, minor: §2.1 says libraries are removed with `& DBL,50000,60000`. True for
thirteen of them; `PART.LIB` is appended and removed with `& DBL,42000,42900` (10800).

### 1.6 §1.1 — "sixteen landmarks" vs Table 7's "The 18 landmarks"

`LM$` holds 18 entries (0–17); 16 are intermediate. Both numbers are defensible but the
paper never says so, and the two figures sit two pages apart.

### 1.7 §8.2, event 2 — the dispatch entry does exist

Paper: "| 2 | (none) | 0 | no routine exists | **none** |". Line 3180's `ON … GOSUB` list
contains `10200`, and `OREGON TRAIL` has no such line (the listing jumps 10105 → 10300).
`RE(2) = 0` at 29001 makes it unreachable, but reaching it would be UNDEF'D STATEMENT,
not a no-op. Change "none" to "`10200`, absent from the program".

---

## 2. Section 12 verified by execution (the paper says this is unverified)

§12.6 states neither approach in §12.5 "has yet been run for this paper". I have now run
the ROM. **§12's content is sound**; only its status line and §12.2's last sentence need
changing.

**`ROUND.FAC` at `$EB72` — exactly as §12.2 describes:**

```
$EB72  A5 9D    LDA $9D
$EB74  F0 FB    BEQ $EB71      ; exponent 0 -> value is zero
$EB76  06 AC    ASL $AC
$EB78  90 F7    BCC $EB71      ; guard < $80 -> no increment
$EB7A  20 C6 E8 JSR $E8C6      ; add 1 to the significand
```

**`RND` at `$EFAE` — every step of §12.3 confirmed:**

```
$EFAE  JSR $EB82   FIXARG          $EFCC  LDX $A1/LDA $9E/STA $A1/STX $9E  swap $9E<->$A1
$EFB1  TAX/BMI     neg arg -> seed  $EFD4  LDA #$00/STA $A2               clear guard
$EFB4  MOVAF $C9   load seed       $EFD8  LDA $9D/STA $AC                 exp -> guard
$EFBB  TXA/BEQ $EFA5               $EFDC  LDA #$80/STA $9D                 force exp 128
$EFBE  FMULTT $EFA6                 $EFE0  JSR $E82E                      normalise
$EFC5  FADDT $EFAA                 $EFE3  round, store $C9, RTS
```

`$EFA5` is a bare `RTS`, so `RND (0)` returns the seed — which *is* the last value,
because `MOVAF` ran before the `TXA`/`BEQ` test. §12.3 correct.

**The two constants, and the "four bytes" point:**

```
$EFA6  98 35 44 7A 68  = 11879546.40625    multiplier
$EFAA  68 28 B1 46 20  = 3.9276778e-08     addend  <- 5th byte ($EFAE) is the JSR opcode
$EFAE  20 82 EB        JSR $EB82
```

Confirmed exactly, including that the addend's fifth byte is the opcode of the `JSR`
that begins the routine. Against products of order 10⁷ the addend is ~16 orders of
magnitude down, so "almost no effect" is if anything an understatement.

**First `RND` values for a known seed — this closes an open item in §12.6.**
15 consecutive `RND (1)` from seed `81 00 00 00 00`, all in [0,1), all distinct:

```
0.4072949116816744   0.608041618950665     0.25951706536579877
0.08268766026594676  0.35866158816497773   0.9610444016288966
0.5672113706823438   0.6001326921395957    0.33425431547220796
0.6068662970792502   0.6758213557768613    0.3164409970631823
0.036882334752590396 0.03491484130790923   0.2833032483467832
final seed $C9..$CD = 7F 11 0D 1F 95
```

`INT` at `$EC23` (exponent test, then `JSR $EBF2`) and `QINT` at `$EBF2` confirmed at
the addresses §12.4 gives. `1.0 = 81 00 00 00 00` and `0.5 = 80 00 00 00 00` confirmed.

**Recommendation:** put these numbers in §12.6, replace "have not been confirmed by
executing the ROM" in §1.4 and §12.6, and the paper's strongest section becomes its
best-evidenced one.

---

## 3. Verified correct (so the author knows the scope of the check)

Line-by-line against the listing, all confirmed: §2.3 **Table 4** (all 18 addresses, both
hand-over layouts, including the yokes/boxes versus oxen/bullets swap between 905/909 and
904/905) — this is the paper's most valuable single table; §2.2; §2.4; §3.1–§3.6; §4.1
Tables 7 and 8 internally consistent; §4.1's route totals 1,771 and 1,871 (see §4.1 below);
§4.2; **§4.3 Table 9**, including the day costs and the fact that the on-trail menu is
choices 1–8 with 8 = "Hunt for food" while a landmark gets 1–9 with 8 = Talk and 9 = Buy;
§4.4 (all four formulas, and exactly the seven `GOSUB 650` call sites the paper names);
§4.5's ten-step order; **§5.1 Table 10** term by term, including the clothing thresholds
implied by `5 - TM - TM - OP`; §5.2; §5.3 (10.3% at H = 139 checks out); §5.4; §5.5;
§6.1; §6.2 (the `MID$` position is 1-based and `AM * 2 + Z - 1` is right; the worked
example gives 9° and 0.039); §6.3 **Table 14**, all ten rows, including that
`TM < C2` turns light rain into snow and 1.6 / 6.4 inches; §6.4; §7; §8.2 Table 16 (all
fifteen chances, and the fixed/segment/daily split); §8.3; §9.1; §9.2; §9.3 Tables 17 and
18; §9.4 Table 19 (exact — six tiers, six multipliers, six food prices); §10.1–§10.4
including Table 22 against `MANAGEMENT` 20000/20010; §11.1's BASIC side; §11.2 including
Table 25; **§13, all nine bugs**; Appendix E.1 (`RE = 14`, `NP = 5`); Appendix G's draw
counts, which I checked line by line and which are right.

One trap worth recording, since a reviewer will hit it: `ON RB GOSUB 50060,50070` at
50035 is **1-based**, and `RB` is 0 smooth / 1 muddy / 2 rough, so smooth falls through
to `RETURN`, muddy gets 50060 and rough gets 50070. Tables 17 and 18 are mutually
consistent. Reading `ON … GOSUB` as 0-based makes both tables look wrong.

---

## 4. The working notes contain two wrong "corrections" of the paper

`FINDINGS.md` and `GAPS.md` are not the paper, but they propagate into the rebuild, so
they need fixing.

### 4.1 §5.3 / GAPS A6 — the paper's route totals are right; the note is wrong

`FINDINGS.md` §5.3 and `GAPS.md` A6 claim the paper's "1,771 and 1,871" is 50 miles short
and that the route should be 1,821 / 1,921. **The paper is correct.** Enumerating all
four legal paths through Tables 7 and 8:

| Route | To The Dalles | To the Willamette Valley |
| --- | --- | --- |
| 0–7, 10–14, **16** (Blue Mountains → The Dalles direct) | **1771** | **1871** |
| 0–7, 10–14, 15, 17 (via Fort Walla Walla) | 1821 | 1921 |
| 0–7, 8, 9, 11–14, 16 (Sublette cutoff) | 1857 | 1957 |
| 0–7, 8, 9, 11–14, 15, 17 | 1907 | 2007 |

The note's route is legal but is not the shortest, and the paper's wording — "by Green
River and straight to The Dalles" — names segment 16 explicitly. The rebuild uses the
mile table as printed, so it plays correctly; the defect is in the notes.

Related: `oregon/data/__init__.py:12` says the route lengths are checked by a test
against the paper's 1,771 / 1,871. **No such test exists.** Either add it or drop the
claim — it is exactly the check that would have caught the false finding.

### 4.2 §6.1 / GAPS §5 — the action-menu "swap" bug does not exist

`FINDINGS.md` §6.1 and `GAPS.md` §5 claim that on the trail leaving a fort, "Buy supplies"
runs the hunt and "Hunt for food" does nothing, and `oregon/action.py:47-52,74`
reproduces it. It is a misreading of Applesoft's line-scoped `IF`.

Line 4040 is a conditional *chain*, because there is no way to close an `IF` on one line:

```
4040 … NEXT : L = L + 1: Z = 0: IF NOT LL THEN PRINT L". "AQ$(7): L = L + 1: IF VAL (LM$(LM,1)) = 1 THEN PRINT L". "AQ$(8): L = L + 1
4050 IF LL THEN PRINT L". "AQ$(9): Z = 2: L = L + 1
```

Both `L = L + 1` statements and the second `IF` are **inside** `IF NOT LL THEN`. So:

- **At a landmark** (`LL = 0`): `L` 7→8, prints 8 = Talk, `L`→9; if a fort, prints
  9 = Buy, `L`→10. `Z$ = "-1" + STR$(L - 1)` = `"-19"`.
  Line 4090 gives `Z = 8` → `ON 7` → 4700 Talk; `Z = 9` → `ON 8` → 4800 Buy. Correct.
- **On the trail** (`LL = 1`): the whole chain is skipped, `L` stays 8. Line 4050 prints
  8 = "Hunt for food", `Z = 2`, `L`→9, so the accepted range is `"-18"`.
  Line 4090 gives `Z = 2 * 1 + 8 = 10` → `ON 9` → **4600, the hunt**. Correct.

There is no swap, "Buy supplies" is never offered on the trail at all, and hunting works.
The paper's Table 9 is right; the rebuild is wrong. This also means `GAPS.md`'s third
"bug found in the source, not in the paper" is spurious.

### 4.3 Smaller note errors

- `FINDINGS.md` §5.1: "fifteen draws either way". No — it is `k + 1` draws where `k` is
  the index of the first firing event, 15 only when nothing fires. `trail.py`'s docstring
  has this right; the note does not.
- `FINDINGS.md` §7: the bytes for `.9` are right (`80 66 66 66 66`) but the decoded value
  is **0.8999999999068677**, not 0.9000000074, and `.9 * 20` is **17.999999998137355**,
  not 18.0000000075. The error is below the literal, not above. A test asserts this
  "deliberately", so check what it asserts.
- `FINDINGS.md` §1.1: the multiplier is 1.19 × 10⁷, not "6.99 × 10⁶"; the addend is
  3.93 × 10⁻⁸, not "1.9 × 10⁻⁸".
- `README.md` says "76 tests"; there are 108, all passing.
- `action.py:67` comments that the article is wrong for oxen. `B = 2` gives
  `T$(1)` = `"an "` + `"ox"` = "an ox", which is right. The wrong one is `B = 6`
  ("a axle"). The code is faithful; the comment misdescribes it.

Credit where due: §11.3 retracts its own `Q`-subscript claim and keeps a test that holds
the retraction. That is the right instinct, and §4.2 and §4.3 above are the same move.

---

## 5. Completeness gaps in §13

§13 says "probably unintended", so this is not an error — but these are behaviourally
significant and belong in the paper, because the rebuild had to find them the hard way:

1. **`Q` is one variable used as an array and as three scalars.** `OREGON TRAIL` 29000
   does `DIM Q(16)` and `MAP.LIB` plots `Q(0…)` as the landmark history. But `BUY.LIB`
   50003 writes the fort tier to `Q(0)`, and `TRADE.LIB` 50011 writes the rounded holding
   to `Q(0)`. Consequences: **an accepted trade rounds the player's holding** — 50035 does
   `I(X+2) = Q - V`, so five and a half oxen become six minus whatever is taken — and a
   fort purchase loses the map's first landmark.
2. **`T$` is three things at once**: the travel screen's six values, `RIVER.LIB`'s six menu
   labels, and `LF.LIB`'s ten loss lines, with residue between uses. `LF.LIB` 52030 always
   prints `T$(0)`, so an empty theft reads *"A thief comes during the night and steals ."*
   with nothing after it. That is in the shipped game.
3. **`B` is two things**: the travel screen's five label columns and the cannot-continue
   flag. Cosmetic, but worth a line.
4. **Line 11505 re-selects a victim**: `ON (H1(Z) < 0) GOTO 11505` re-shifts `Z` without a
   new `RND` if the chosen slot holds a corpse. §5.4 does not mention it. No draw-count
   impact.
5. **`ZO` is not restored by `VAR.BIN`.** Appendix E.1's list does not include it, so it is
   0 at line 29000, and `FN W` reads `WC$(ZO)`. The consequence is that the initial
   temperature class and the first month's rain chance come from **climate row 0 whatever
   the departure month**. §3.6 and Table 6 present `INT ((FN W(0) + 10) / 20)` without this.
6. §11.2 omits the fourth moving marker at pass 175 (line 1146) and the erase at passes 97
   and 157 (line 1144).

---

## 6. Editorial

- **Appendix lettering is inconsistent.** The paper's "Appendices D to H" refers to the
  dialogue file as "Appendix E: Dialogue records" while the file is named
  "Appendix D Dialogue records.md", and the parenthetical "(Appendices G to J)" matches
  nothing. One scheme, applied to headings, filenames and cross-references.
- **§12.6 is stale** relative to the project's own `FINDINGS.md`, and now demonstrably so.
- §1.4's "they were not confirmed by executing the ROM" should be struck.

---

## 7. Bottom line

The paper is strongest exactly where replication is hardest and most valuable: the
hand-over address table (§2.3), the landmark/segment tables, the health and weather
formulas with their line numbers, the event chances, the river rules, and §12's account of
the number format. I checked all of those against the source and they are right, and §12
now has execution behind it.

Fix §8.1 first — it is a headline behavioural claim and it is wrong. Then Table 12, which
will actively mislead an implementer. Then §12.2's sentence about literal conversion.
Correct §4.1 and §4.2 above in the working notes, because one of them has made the
rebuild less faithful than the paper it was built from.

The parity argument itself — that no host-language arithmetic reproduces this game, and
that the ROM must run — is correct, and the project's own measurements support it. The
paper's remaining weakness is not the argument but the absence of the one artefact that
would settle everything else: a day-by-day trace from the original under emulation.
`oregon/trace.py` already emits the right line format, seed bytes included. That is still
the highest-value next step, and it is now the *only* one.