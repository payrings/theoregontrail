# The Oregon Trail on the Apple II (1985): An Analysis of Source, Data and Algorithms for Replication in Other Languages

by Giacomo Paganelli (<paganelli.act@gmail.com>)

Published 4 October 2026

**Abstract:** This paper provides a detailed analysis of the 1985 Apple IIe version of The Oregon Trail, developed by MECC. By examining the original Applesoft BASIC source code and, in part, its machine code, contextualised by the lead designer's book, a technical study on game variables and extracted game data, this research deconstructs the core game mechanics. The focus is on a detailed understanding of the algorithms governing game setup, resource management, travel simulation, health and weather models, random events, player interactions, mini-games (hunting and rafting) and game conclusion. The objective is to enable developers to replicate these mechanics with high fidelity. The paper also argues that exact algorithmic parity with the original educational software classic cannot be obtained by rewriting its arithmetic in another language: it requires executing the original Applesoft ROM routines, in a 6502 emulator such as py65 or a full Apple II emulator such as ApplePy.

**Keywords:** The Oregon Trail; MECC; Apple II; Applesoft BASIC; 6502; game preservation; software archaeology; algorithm analysis; emulation; floating-point arithmetic; educational software

## 1. Introduction

### 1.1 Historical context

The Oregon Trail began in 1971 as a text game written in two weeks by Don Rawitsch, Bill Heinemann and Paul Dillenberger for a Minneapolis history class. It ran in HP Time-Shared BASIC on an HP 2100 minicomputer reached by teleprinter. Rawitsch joined the Minnesota Educational Computing Consortium (MECC) in 1974, re-entered the game, and MECC released it on its timeshare network in 1975. An Apple II version followed in 1980 in the collection Elementary Volume 6 (“The Oregon Trail (1971 video game),” n.d.).

The version studied here is the redesign made between October 1984 and July 1985 and released for the Apple II in 1985 (Minnesota Educational Computing Consortium \[MECC\], 1985). R. Philip Bouchard was lead designer, John Krenz lead programmer and Charolyn Kapplinger the artist, with Shirley Keran (research), Bob Granvin (programming), Roger Shimada (assembly language, the hunting game) and Steve Splinter (the rafting game) (Bouchard, 2016; “The Oregon Trail (1985 video game),” n.d.). The program headers name Krenz as programmer of the main modules and Splinter as programmer of `FLOAT`.

The redesign replaced the two-week turns of the original with a daily simulation between sixteen landmarks, and added river crossings, trading, hunting and rafting games, tombstones and a scored ending. One popular belief needs correcting: the phrase "You have died of dysentery" does not appear in this game. The program prints "\[name\] has dysentery." and, separately, "\[name\] has died." It never states a cause of death, as the designer's book confirms (Bouchard, 2016).

### 1.2 Objective

The objective is to document the game's algorithms exactly enough to replicate them: every state variable, formula, probability and data table, with the program line that defines it. A second objective is to state what is required for algorithmic parity, meaning that a replica given the same random seed and the same player inputs passes through the same internal states as the original. Section 12 shows that this second goal cannot be met by translation alone.

### 1.3 Sources and method

The primary source is the Applesoft BASIC source of release 1.4 (the management screen reads "Version 1.4", last update 87/02/24), read as text listings. Data that the programs load at run time, namely the landmark, segment, river, climate and illness tables, were decoded from the file `VAR.BIN`. The dialogue, high-score and tombstone files were read directly from disk.

Secondary sources are Bouchard's (2016) book on the game's design and a technical study of a long-wait exploit (moralrecordings, 2025). Where the book describes a design intention that the shipped code does not follow, this paper reports the code and notes the difference. Details of the Applesoft interpreter come from the published commented disassembly of its ROM (“Applesoft BASIC,” n.d.; McFadden, n.d.; Sander-Cederlof, n.d.).

The game's own 6502 machine code (the `&` command package and the hunting routine) was disassembled and analysed with the assistance of an AI model, Claude Opus 5.5 (Medium), developed by Anthropic. The findings in section 11.1 and Appendix F come from that analysis. They are a static reading of the code and were not verified by execution.

Two AI models assisted with the analysis of the BASIC source: Google Gemini 3.1 Pro (Extended Thinking), and Anthropic Claude Opus 5.5 (Medium). Both models were also used to assist with the analysis of the data files, the checking of sources, and the drafting and editing of the text of this paper. The author directed the work, wrote the earlier versions of the paper that the models then revised, and is responsible for its content.

Line numbers below refer to the release 1.4 listings. Program names are written as they appear on disk: `MENU`, `BUY SUPPLIES`, `OREGON TRAIL`, `FLOAT`, `WIN`, and the libraries `RIVER.LIB`, `TRADE.LIB` and so on.

The source code is not reproduced in this paper because it remains under copyright and cannot be distributed. A reader can obtain the same listings by extracting the BASIC programs, along with any other file, from the game's disks with CiderPress II (<https://ciderpress2.com/>) and by running the game in an emulator such as AppleWin (<https://github.com/AppleWin/AppleWin>), which is the method used for this paper. Readers who do so act under their own responsibility, not the author's.

### 1.4 Limits of this analysis

The machine-language routines reached through the `&` command were disassembled and read at their entry points, which establishes their argument lists and general function (Appendix F). The hunting routine was analysed in more depth (section 11.1), though its graphics and movement code were not. The routines used only by the river-floating program, and the picture, image and tune data formats, were not decoded. The claims in section 12 about the interpreter's arithmetic were read from the published ROM disassembly (Sander-Cederlof, n.d.) and have since been confirmed by executing the ROM; see 12.6. The machine code of the game itself has still not been run, so section 11's findings about the hunting routine remain a reading of the disassembly rather than an observation of play.

### 1.5 Design intentions behind the mechanics

The designer's book (Bouchard, 2016) explains why each mechanic exists. These reasons help a replicator judge which details matter. All statements in this subsection are the book's.

**Table 1.** Design reasoning behind each game mechanic, as given in the designer's book.

| Mechanic | Design reasoning |
| --- | --- |
| Two nested cycles | Bouchard wanted the real geography of the trail, so the journey became a chain of landmarks, "like beads on a string", with most activities attached to them. He did not want to jump from landmark to landmark, because supplies can run out and incidents happen in between. He therefore added a daily cycle inside the landmark cycle, "a cycle within a cycle", in which speed, location and the state of the party are computed every day. |
| Automatic travel with an override | Asking the player what to do every day would mean about 150 halts in a five-month journey. Travel therefore runs by itself, and the player can interrupt it at any time. |
| Professions | The three difficulty levels differ only in starting cash. The team chose to present them as occupations; the middle one was a shopkeeper in the alpha version and became a carpenter. |
| Departure month | In the 1971 game every trip began on the same date. For real emigrants, leaving too early meant snow and no grass, and leaving too late meant snow in the mountains. Giving the player this choice is what made a climate model necessary. |
| Climate model | The aim was realistic temperature and rainfall for the place and season from the simplest workable model: zones based on present-day climate data for towns near the trail. |
| Cutoffs | Three real cutoffs were kept: the Sublette Cutoff past Fort Bridger, the route past Fort Walla Walla, and the Barlow Toll Road past the Columbia gorge. Skipping a fort saves days but loses the chance to buy. |
| Death by second illness | A person dies on catching a second disease before recovering from the first, and the second disease is never reported. This removed the need for a separate death formula, tied the death rate to general health, and avoided tracking several diseases per person. |
| Disease names | "Heat exhaustion" and "mountain fever" became "exhaustion" and "a fever" after testers found them odd in cool weather or on the plains. |
| River crossings | A wagon has about 30 inches of clearance, hence the 2.5-foot fording limit. An early draft had a second break point at 5 feet; it was replaced by losses that rise smoothly with depth. |
| Indian guide | The guide first halved the risks. Testers still had accidents and judged the guide useless, so the reduction was raised to 80%. |
| Meat limit | Bouchard wanted to show the difference between small and large game, to make players reflect on wasteful hunting, and to keep the wagon's load plausible. He settled on 100 pounds carried back per hunt after trying other values. |
| Hunting difficulty | Adults found hunting too hard. Bouchard kept it, reasoning that a first-time hunter is not an expert, and observed that children became proficient after three or four hunts. |
| Tombstones | Ten saved gravestones would have interrupted play too often. Two were approved, one on each side of the disk, with the newest replacing the old one. |
| Scoring | No score is shown unless the party reaches Oregon, so that a new player concentrates on survival. Survivors count most, then their health, then goods and cash. A multiplier for the harder professions allowed a single high-score list, which also suited the limited disk space. |

Bouchard (2016) also states the health model as designed. The shipped code differs from that description in four places, and a replica should follow the code.

**Table 2.** Differences between the book's description of the health model and the shipped code.

| Item | Book's description | Shipped code |
| --- | --- | --- |
| Daily chance of illness | 0% to 40%, by health | 1% to 10.3% (section 5.3) |
| Penalty with no food | add 6 | add 8 (section 5.1) |
| Clothing needed to avoid a penalty | 2 sets a person in cold, 4 in very cold | 3 in cold, 5 in very cold, 1 in cool (section 5.1) |
| Climate zones | six, the last based on Portland | five; the Portland row is never read (section 6.1) |

## 2. Architecture and data flow

### 2.1 Programs and libraries

The game is five chained BASIC programs plus fourteen small BASIC libraries, spread over two disk sides. The player flips the disk on reaching Fort Laramie (line 1016).

**Table 3.** Programs and libraries, with disk side and role.

| Program | Side | Role |
| --- | --- | --- |
| `MENU` | 1 | Title menu, profession, party names, top ten, random seed |
| `MANAGEMENT` | 1 | Teacher options: view or reset the top ten, erase tombstones |
| `BUY SUPPLIES` | 1 | Departure month and Matt's General Store |
| `OREGON TRAIL` | 1 and 2 | The journey: landmarks, daily cycle, events, menus |
| `FLOAT` | 2 | Columbia River rafting game |
| `WIN` | 2 | Scoring and top-ten entry |

The libraries are `COMMON.LIB` (input, error handling, disk checks), `RIVER.LIB`, `CROSS.LIB`, `BUY.LIB`, `TRADE.LIB`, `TALK.LIB`, `HUNT.LIB`, `MAP.LIB`, `PACE.LIB`, `RATION.LIB`, `PART.LIB`, `LF.LIB` (fire, abandoned wagon, thief), `TOMB.LIB`, `END.LIB` and `FLIP.LIB`. Each occupies lines 42000 or 50000 upward. `OREGON TRAIL` appends one with `& APP`, calls it with `GOSUB 50000`, then removes it with `& DBL,50000,60000`. Because a library runs inside the main program, it shares all of its variables.

The `&` commands are machine-language extensions for graphics, windows, input, disk files and program chaining. `& RNH` runs another program; `& RFL` loads a binary file at an address; `& OPEN`, `& TPTR`, `& TREED` and `& TWRITE` read and write text files at a byte offset. Appendix F lists every command with the arguments and behaviour read from a disassembly of the package.

### 2.2 The saved variable table

`OREGON TRAIL` does not build its data tables with DATA statements. Line 100 sets `LOMEM: 39170`, loads the file `VAR.BIN` at 39170 and loads `PT.BIN` at address 105, the interpreter's variable pointers. Together these restore a complete, pre-built variable table: the constants `C0` to `C4` and `P5`, the landmark and segment arrays, river data, climate strings, illness names and all menu text. A replica must take its data from `VAR.BIN`; the tables are reproduced in sections 4, 6, 8 and 9.

### 2.3 State passed between programs

Running a new program clears all BASIC variables, so state is passed in memory locations 900 to 917 with POKE and PEEK, and party names as zero-terminated ASCII from address 1920. Values above 255 are split with `FN HI(Z) = INT (Z / 256)` and `FN LO(Z) = Z - FN HI(Z) * 256`.

There are two different layouts, and they must not be confused.

**Table 4.** Memory addresses used to pass state between programs, at the start and end of the journey.

| Address | Start of journey (written by `MENU` and `BUY SUPPLIES`) | End of journey (written by `END.LIB` and `FLOAT`) |
| --- | --- | --- |
| 900 | not written; party size 5 comes from `VAR.BIN` | people alive (NP) |
| 901 | 48 | year minus 1800 |
| 902 | month (3 to 7) | month |
| 903 | day (1) | day |
| 904 | wagon flag (1) | bullets, low byte |
| 905 | yokes of oxen | bullets, high byte |
| 906, 907 | pounds of food, low and high | pounds of food, low and high |
| 908 | sets of clothing | sets of clothing |
| 909 | boxes of bullets | oxen, as `I(2) + .5` |
| 910, 911, 912 | spare wheels, axles, tongues | spare wheels, axles, tongues |
| 913, 914 | money times 10, low and high | whole dollars, low and high |
| 915 | profession (1 banker, 2 carpenter, 3 farmer) | unchanged |
| 916 | not used | health band, `INT (H / 35)` |
| 917 | not used | cents, `(MY - INT (MY)) * 100 + .5` |

Other fixed locations: 919 is a flag the error handler reads to decide how to treat Control-C; 975 holds the sound setting; 955 is a disk-configuration flag tested before asking the player to flip the disk.

### 2.4 Error handling

Every program sets `ONERR GOTO 32000`. The handler reads the error code from address 222 and the line number from 218 and 219, resumes after disk errors 1 to 15, and otherwise prints "Error \[code\] at line #\[line\] in \[program\]. Please report this error to MECC." The codes are Applesoft's own. Code 53 is ILLEGAL QUANTITY, which is what a POKE of a value above 255 produces (see section 13).

## 3. Game setup

### 3.1 Main menu and the random seed (`MENU` 1000 to 1020)

The menu offers four choices: travel the trail, learn about the trail, see the top ten, and turn sound on or off. Control-A opens the management program. Immediately after the player's keypress, line 1015 reseeds the random generator:

`Z = RND ( - ( PEEK (78) + PEEK (79) * 256))`

Locations 78 and 79 are a 16-bit counter that the system's keyboard routine increments while it waits for a key. The seed is therefore one of at most 65,536 values, fixed by how long the player took to press the key. This is the only reseeding in the game. A replica that accepts this 16-bit value as an input can, in principle, replay any game.

### 3.2 Profession and money (`MENU` 4000 to 4030)

The player chooses banker, carpenter or farmer. Line 4030 stores the choice at 915 and the starting money, times ten, at 913 and 914:

`Z = ((Z = 1) * 1600 + (Z = 2) * 800 + (Z = 3) * 400) * 10`

In Applesoft a true comparison has the value 1 and a false one 0, so this yields $1,600, $800 or $400. Money is stored times ten because the hand-over uses whole numbers.

### 3.3 Party names (`MENU` 6000 to 6045)

Ten default names (Zeke, Jed, Anna, Mary, Joey, Beth, John, Sara, Henry, Emily) are placed in random order. For each name the program draws `INT (RND (1) * 10)` and, if that slot is taken, steps forward to the next free slot, wrapping from 9 to 0. The number of random draws is always ten, but the resulting order depends on them. The player then types the leader's name and up to four others; blanks keep the shuffled defaults. Line 6045 writes the five names from address 1920, each ended by a zero byte.

### 3.4 Departure month (`BUY SUPPLIES` 6000 to 6030)

The year is fixed at 1848 (`MENU` 9000 stores 48 at 901). The player picks March to July as options 1 to 5; line 6030 stores the option plus 2 at 902, and the day is set to 1.

### 3.5 Matt's General Store (`BUY SUPPLIES` 400 to 5020)

**Table 5.** Items sold at Matt's General Store, with prices, input limits and storage addresses.

| Item | Price | Input limit | Stored at |
| --- | --- | --- | --- |
| Oxen | $40 a yoke (2 oxen) | 1 to 9 yoke | 905 |
| Food | $0.20 a pound | up to 2,000 pounds | 906, 907 |
| Clothing | $10 a set | up to 99 sets | 908 |
| Ammunition | $2 a box of 20 bullets | up to 99 boxes | 909 |
| Spare wheels, axles, tongues | $10 each | up to 3 of each | 910, 911, 912 |

The bill is the sum of the five lines (line 4000). The player cannot leave if the bill exceeds the money held (line 5000) or with no oxen (line 5006). On leaving, line 5010 stores the remaining money times ten:

`MY = (MY - TB) * 10: POKE 913, FN LO(MY): POKE 914, FN HI(MY)`

Amounts are shown through the rounding routine at line 200, `V = INT (V * 100 + .5)`, which rounds to the nearest cent before the digits are cut into dollars and cents. The same routine appears in `OREGON TRAIL` and `WIN`.

### 3.6 Initial state of the journey (`OREGON TRAIL` 29000 to 29020)

On loading, the main program reads the hand-over values and sets its starting state.

**Table 6.** Initial values of the main program's variables at the start of the journey.

| Variable | Initial value |
| --- | --- |
| Money `MY` | (PEEK(913) + PEEK(914) \* 256) / 10 |
| Oxen `I(2)` | 2 times the yokes |
| Bullets `I(4)` | 20 times the boxes |
| Food `I(8)` and `PF` | the pounds bought |
| People `NP`, pace `P`, rations `R`, health `H` | 5, 1 (steady), 1 (filling), 0, from `VAR.BIN` |
| Snow on the ground `AS` | `RND (1) * 12` if leaving in March, else 0 |
| Accumulated rain `AR` | `7 - month + RND (1)` |
| Weather `W` and `TM` | `INT (( FN W(0) + 10) / 20)`, the class of the month's minimum temperature |
| Fixed event chances | see section 8 |

The two `RND` calls on lines 29000 and 29004 are the first of the journey, in that order.

## 4. Landmarks, segments and the daily travel cycle

### 4.1 Two tables: landmarks and segments

The trail is held in two arrays that are indexed differently. `LM$(0 to 17, 0 to 3)` describes the 18 landmarks. `LM(0 to 18, 0 to 2)` describes the 19 trail segments. A landmark names the segment or segments that leave it; a segment names the landmark it ends at.

**Table 7.** The 18 landmarks, with type and outgoing segments.

| No. | Landmark `LM$(n,0)` | Type `LM$(n,1)` | Segment out `LM$(n,2)` | Second segment `LM$(n,3)` |
| --- | --- | --- | --- | --- |
| 0 | Independence | 1 | 0 | none |
| 1 | the Kansas River crossing | 2 | 1 | none |
| 2 | the Big Blue River crossing | 2 | 2 | none |
| 3 | Fort Kearney | 1 | 3 | none |
| 4 | Chimney Rock | 0 | 4 | none |
| 5 | Fort Laramie | 1 | 5 | none |
| 6 | Independence Rock | 0 | 6 | none |
| 7 | South Pass | 0 | 7 | 8 |
| 8 | Fort Bridger | 1 | 9 | none |
| 9 | Green River crossing | 2 | 10 | none |
| 10 | Soda Springs | 0 | 11 | none |
| 11 | Fort Hall | 1 | 12 | none |
| 12 | the Snake River crossing | 2 | 13 | none |
| 13 | Fort Boise | 1 | 14 | none |
| 14 | the Blue Mountains | 0 | 15 | 16 |
| 15 | Fort Walla Walla | 1 | 17 | none |
| 16 | The Dalles | 0 | 18 | none |
| 17 | the Willamette Valley | 0 | none | none |

Type 1 is a fort (buying allowed), type 2 a river crossing, type 0 neither.

**Table 8.** The 19 trail segments, with miles, speed base, end landmark and route.

| Segment | Miles `LM(s,0)` | Speed base `LM(s,1)` | Ends at landmark `LM(s,2)` | Route |
| --- | --- | --- | --- | --- |
| 0 | 102 | 20 | 1 | Independence to Kansas River |
| 1 | 83 | 20 | 2 | Kansas River to Big Blue River |
| 2 | 119 | 20 | 3 | Big Blue River to Fort Kearney |
| 3 | 250 | 20 | 4 | Fort Kearney to Chimney Rock |
| 4 | 86 | 20 | 5 | Chimney Rock to Fort Laramie |
| 5 | 190 | 12 | 6 | Fort Laramie to Independence Rock |
| 6 | 102 | 12 | 7 | Independence Rock to South Pass |
| 7 | 57 | 12 | 9 | South Pass to Green River |
| 8 | 125 | 12 | 8 | South Pass to Fort Bridger |
| 9 | 162 | 12 | 10 | Fort Bridger to Soda Springs |
| 10 | 144 | 12 | 10 | Green River to Soda Springs |
| 11 | 57 | 12 | 11 | Soda Springs to Fort Hall |
| 12 | 182 | 12 | 12 | Fort Hall to Snake River |
| 13 | 114 | 12 | 13 | Snake River to Fort Boise |
| 14 | 160 | 12 | 14 | Fort Boise to Blue Mountains |
| 15 | 55 | 12 | 15 | Blue Mountains to Fort Walla Walla |
| 16 | 125 | 12 | 16 | Blue Mountains to The Dalles |
| 17 | 120 | 12 | 16 | Fort Walla Walla to The Dalles |
| 18 | 100 | 12 | 17 | The Dalles to Willamette Valley (Barlow Road) |

The shortest route, by Green River and straight to The Dalles, is 1,771 miles to The Dalles and 1,871 by the Barlow Road.

### 4.2 The landmark cycle (lines 1000 to 1020, 2100 to 2200)

1. On arrival, line 1000 draws `A = INT (RND (1) * 3)`, the first dialogue to offer, and sets the climate zone (section 6).
2. The player may look around, which opens the action menu (line 4000).
3. At a river landmark, line 1015 forces the crossing routine before departure (section 9.3).
4. At a landmark with a second segment, the player chooses a branch (line 2110). At The Dalles the choice is made in `END.LIB` (section 10).
5. Line 2200 loads the chosen segment: `D = LM(Z,0)`, `MD = LM(Z,1)`, `NM = LM(Z,2)`.
6. Line 3000 runs the daily cycle until `D` is zero, then sets `LM = NM`. At landmark 17 the game ends.

### 4.3 The action menu (lines 4000 to 4900)

**Table 9.** Action menu options, with their effects and the days they use.

| Option | Effect | Days used |
| --- | --- | --- |
| Continue on trail | leaves the menu; refused with no oxen or an unreplaced broken part | 0 |
| Check supplies, look at map | display only | 0 |
| Change pace, change rations | sets `P` or `R` to 1, 2 or 3, then recalculates speed | 0 |
| Stop to rest | 1 to 9 days of the daily cycle with pace 0 and no travel | 1 to 9 |
| Attempt to trade | section 9.2 | 1 |
| Talk to people (at landmarks) | section 9.1 | 0 |
| Buy supplies (at forts) | section 9.4 | 0 |
| Hunt for food (on the trail) | section 11.1 | 1 |

### 4.4 Speed (lines 650 to 660)

`V = I(2) / 4: IF V > 1 THEN V = 1`

`FC = NP * (4 - R): BS = MD * V * (P + 1) / 2: OP = I(3) / NP: F0 = 2 * (R - 1)`

Base speed `BS` is the segment's speed base (20 miles a day before Fort Laramie, 12 after), scaled down if there are fewer than four oxen, and multiplied by 1, 1.5 or 2 for steady, strenuous or grueling pace. This routine also sets daily food use `FC`, clothing per person `OP` and the ration penalty `F0`. It runs at the start of a segment and after a change of pace or rations, a death, a trade, a theft or an ox injury. It does not run daily, so clothing lost in a fire or a river does not change `OP` until the next of those occasions.

### 4.5 The daily cycle (lines 3100 to 3499)

Each day runs in this fixed order. The order matters because it fixes the sequence of `RND` calls.

1. Read the month's base temperature `QT` and rain chance `QP` (line 3100).
2. Cap health at 139 (line 3150).
3. Set the day-dependent event chances and run the random-event loop, unless the party is stopped (lines 3160 to 3190; section 8).
4. Count down illnesses and count the sick (line 3200; section 5).
5. Generate weather (lines 3205 to 3206; section 6).
6. Compute the health penalties, the starvation factor and health; eat (lines 3207 to 3230).
7. If health exceeds 139 and the party is not at a river, force an illness (line 3235).
8. Update accumulated rain and snow (line 3240).
9. Travel (lines 3244 to 3246): `Z = 1 - AS / 40`, not below 0, then `V = BS * (C1 - .1 * H0) * NOT SD * Z: IF 1.1 * V > D THEN V = D`, then `D = D - V: M = M + V`.
10. Cap health again, advance the date (lines 3250 to 3255).

Speed falls by 10% for each sick or injured person and in proportion to snow on the ground, reaching zero at 40 units of snow. A stopped party (`SD` not zero) does not move. If the day's travel would bring the party within 10% of the remaining distance, it arrives exactly. The loop ends when `D` is exactly zero.

The calendar gives February 28 days in every year, although 1848 was a leap year, and rolls the year over after December.

## 5. Health, illness and death

### 5.1 The party health value (line 3230)

One number, `H`, describes the whole party. Zero is perfect and higher is worse.

`H = .9 * H + ZT + ZC + ZF + ZP + FS + H0 + HR`

Each day keeps 90% of yesterday's value and adds seven penalties. `H` is capped at 139 at the start and end of each day and whenever the status screen is drawn (lines 3150, 3250, 4010). The screen shows `INT (H / 35)` as good (0 to 34), fair (35 to 69), poor (70 to 104) or very poor (105 to 139).

**Table 10.** Terms of the daily party health calculation, with formulas and line numbers.

| Term | Meaning | Formula | Line |
| --- | --- | --- | --- |
| `ZT` | temperature | 0 for cool or warm; 1 for cold or hot; 2 for very cold or very hot. `ZT = TM - 3`, or `2 - TM` if that is negative | 3207 |
| `ZC` | clothing | `5 - TM - TM - OP`, not below 0, where `TM` is the temperature class 0 to 5 and `OP` is sets of clothing per person | 3210 |
| `ZF` | rations | `2 * (R - 1)`: 0 filling, 2 meager, 4 bare bones; 8 when there is no food | 3215 |
| `ZP` | pace and weather | `(W > 5) + (W > 7) + P + P`: twice the pace, plus 1 in rain or snow, plus 2 in heavy rain or snow. Pace is 0 while resting or delayed | 3220 |
| `FS` | freezing and starving | see 5.2 | 3225 |
| `H0` | illness | the number of party members currently sick or injured, 0 to 5 | 3200 |
| `HR` | event hardship | 0, or 10 or 20 set by that day's events (section 8) | 3180 |

Note that the clothing term uses the temperature class, not the weather code, so rain does not change it. `H0` is a count, not a constant: line 3200 adds 1 only for a member whose illness value is above zero.

### 5.2 The freeze and starve factor (lines 3215 to 3230)

`X = (ZC > P5): Y = (PF = C0)`

`Z = FS * P5: IF X OR Y THEN Z = FS + .8`

`FS = Z`

On a day with no food, or with a clothing penalty above 0.5, `FS` rises by 0.8. On any other day it halves. It has no upper limit. After ten bad days it adds 8 a day to health; one good day halves that.

### 5.3 Individual illness (lines 3200, 10100, 10300, 10830)

Two arrays hold each member's state. `H1(n)` is 0 for healthy or the number of the illness; `H2(n)` is the days left. Each day line 3200 reduces `H2` by one for every sick member and clears the illness when it falls below 1.

**Table 11.** Illnesses and injuries, with source and duration in days.

| Number | Name `IL$(n)` | Source | Days |
| --- | --- | --- | --- |
| 0 | a broken arm | injury, event 8 | 30 (but see section 13) |
| 1 | a broken leg | injury, event 8 | 30 |
| 2 | a snakebite | event 1 | 10 |
| 3 | exhaustion | event 3 | 10 |
| 4 | typhoid | event 3 | 10 |
| 5 | cholera | event 3 | 10 |
| 6 | measles | event 3 | 10 |
| 7 | dysentery | event 3 | 10 |
| 8 | a fever | event 3 | 10 |

The illness routine at line 10300 is reached in two ways: as random event 3, with daily chance `.01 + H / 1500` (1% at perfect health, 10.3% at 139); and from line 3235 on any day when health is above 139 before the cap, outside river crossings. The routine sets `HR = 20`, draws a disease `INT (RND (1) * 6) + 3` and then a victim. The six diseases are equally likely.

### 5.4 Choosing a victim (lines 11500 to 11505)

`Z = INT (RND (1) * NP)`

`Z = (Z + 1) * (Z < (NP - 1)): ... Z = Z + (NP > 1) * (Z = 0)`

`NP` is the number of people alive. The draw is shifted by one place with wrap-around, and a result of 0, the leader, is changed to 1 while anyone else is alive. The leader therefore cannot fall ill or die until the rest of the party is dead.

### 5.5 Death (lines 10300, 8000; `TOMB.LIB` 50000 to 50005)

If the chosen victim already has an illness, the victim dies; the new disease is never named. Otherwise the victim gets the disease for 10 days. This is the only way a party member dies on the trail, apart from drowning.

On a death, `TOMB.LIB` lowers health to 105 if it was higher, reduces `NP` by one and swaps the dead member with the last living one, so the living always occupy positions 0 to `NP - 1`. When `NP` reaches zero the game ends with the tombstone sequence (section 10.2).

## 6. Weather

### 6.1 Climate zones (line 1000)

`ZO = (LM > 2) + (LM > 5) + (LM > 10) + (LM > 13)`

The zone is set on arrival at each landmark and holds for the segment that follows. The code produces five zones, numbered 0 to 4.

**Table 12.** Climate zones, the segments they cover and the climate row each uses.

| Zone | Segments leaving landmarks | Climate row used |
| --- | --- | --- |
| 0 | 0 to 2: Independence to Fort Kearney | 0 |
| 1 | 3 to 5: Fort Kearney to Independence Rock | 1 |
| 2 | 6 to 10: Independence Rock to Fort Hall | 2 |
| 3 | 11 to 13: Fort Hall to the Blue Mountains | 3 |
| 4 | 14 to 16: the Blue Mountains to the end | 4 |

Bouchard (2016) describes six zones based on Kansas City, North Platte, Casper, Lander, Boise and Portland, with different boundaries. The climate table does hold six rows, but the code never selects row 5, so the Portland data is unused. A replica should follow the code.

### 6.2 The climate table and `FN W` (line 105)

`WC$(0 to 5)` holds six strings of 24 characters: for each month, one character for temperature and one for rain. The value is the character's ASCII code.

`DEF FN W(Z) = ( NOT Z + .003 * Z) * ( ASC ( MID$ (WC$(ZO),AM * 2 + Z - 1,1)) - 30) - 20 * NOT Z`

`FN W(0)` gives the month's minimum temperature `QT`, the temperature code minus 50. `FN W(1)` gives the daily rain chance `QP`, 0.003 times (the rain code minus 30). The table below gives the ASCII codes as temperature, rain for each month.

**Table 13.** Climate table: temperature and rain codes for each month, by climate row.

| Row | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 59,43 | 63,44 | 73,56 | 86,63 | 95,78 | 105,78 | 110,69 | 108,70 | 100,72 | 89,60 | 75,49 | 64,45 |
| 1 | 53,35 | 58,35 | 66,40 | 79,51 | 89,60 | 99,63 | 105,57 | 103,52 | 93,46 | 81,40 | 67,35 | 57,35 |
| 2 | 53,35 | 57,35 | 62,39 | 72,46 | 82,51 | 92,43 | 101,40 | 99,36 | 88,39 | 77,39 | 63,37 | 56,35 |
| 3 | 49,35 | 54,37 | 62,42 | 73,53 | 82,55 | 91,43 | 99,38 | 97,35 | 87,41 | 76,44 | 61,38 | 51,36 |
| 4 | 60,45 | 66,43 | 72,43 | 80,42 | 88,42 | 95,39 | 104,33 | 102,33 | 93,36 | 82,40 | 70,43 | 62,44 |
| 5 (unused) | 68,87 | 73,71 | 76,66 | 81,53 | 87,51 | 91,46 | 96,35 | 96,40 | 93,47 | 84,63 | 76,84 | 71,94 |

Example: row 0 in January has codes 59 and 43. The minimum temperature is 9 degrees, the mean 29 degrees, and the rain chance 0.039.

### 6.3 Daily generation (lines 3205 to 3206)

`IF RND (C1) < P5 THEN TM = QT + INT ( RND (C1) * 41): PP = ( RND (C1) < QP): W = INT ((TM + 10) / 20): TM = W`

`TR = C0: TS = C0: IF PP THEN Z = ( RND (C1) < .3): W = 6 + Z + Z: TR = .2 + .6 * Z: IF TM < C2 THEN W = W + C1: TS = 8 * TR: TR = C0`

With probability one half the weather changes: a new temperature between the month's minimum and 40 degrees above it, a new rain flag, and a temperature class `TM` from 0 to 5. Otherwise yesterday's class and rain flag stand. The second line runs every day. If the rain flag is set it draws again for heavy precipitation (30%), so light and heavy can alternate while the flag persists.

**Table 14.** Values of the weather variable W, as displayed and the conditions that produce them.

| `W` | Shown as | Condition |
| --- | --- | --- |
| 0 to 5 | very cold, cold, cool, warm, hot, very hot | no precipitation; temperature below 10, 10 to 29, 30 to 49, 50 to 69, 70 to 89, 90 and over |
| 6 | rainy | light precipitation, class 2 or above; 0.2 inch |
| 7 | snowy | light precipitation, class 0 or 1; 1.6 inches of snow |
| 8 | very rainy | heavy precipitation, class 2 or above; 0.8 inch |
| 9 | very snowy | heavy precipitation, class 0 or 1; 6.4 inches of snow |

### 6.4 Rain and snow on the ground (line 3240)

`AR = .9 * AR + TR: AS = .97 * AS + TS`

`IF AS THEN IF TM > C2 OR W = 8 THEN AR = AR + P5: AS = AS - 5: IF AS < C0 THEN AS = C0`

Accumulated rain loses 10% a day and snow 3%. When there is snow and the weather is warm or hotter, or very rainy, 5 units of snow melt and add 0.5 to the rain.

These two values feed the rest of the game. Snow slows travel and, above 30, makes the party snowbound. Rain raises river depth, width and swiftness. Rain below 0.1 enables the water and grass events. The travel screen is drawn white when snow is 1 or more, in the dry colour when rain is 0.2 or less, and green otherwise (line 310).

## 7. Resources

Inventory is the array `I(2)` to `I(8)`: oxen, sets of clothing, bullets, wagon wheels, wagon axles, wagon tongues and pounds of food. Element 1 is labelled "Wagon" and is not used in play. Money is the separate variable `MY`.

**Table 15.** Resources, how they change and their limits.

| Resource | How it changes | Limits |
| --- | --- | --- |
| Food `I(8)`, working copy `PF` | Falls daily by `FC = NP * (4 - R)`: 3, 2 or 1 pounds a person for filling, meager or bare-bones rations, not below 0 (line 3230). Rises by hunting, buying, trading, wild fruit (+20) and help from Indians (+30). | 2,000 pounds |
| Oxen `I(2)` | An injury subtracts 0.5; a second injury makes a whole number again and is reported as a death (line 10820). Lost in rivers, to thieves and on the raft. Fewer than 4 slows travel; none stops it. | 20 |
| Clothing `I(3)` | Lost to fire, thieves, rivers and the raft; paid to the Shoshoni guide. Sets per person enter the clothing penalty. | none after the store |
| Bullets `I(4)` | Used in hunting; lost to fire, thieves and rivers. Bought in boxes of 20. | none |
| Spare parts `I(5)` to `I(7)` | One is used when a part breaks and cannot be repaired (section 8). | 3 of each |
| Money `MY` | Spent at forts, on ferries ($5) and the Barlow toll. | none |

During the daily cycle the food total lives in `PF`; it is copied back to `I(8)` when the cycle returns (line 3499). Displays round each quantity with `INT (I(L) + .51)` (line 4110), so 5.5 oxen are shown as 6.

With no oxen, or with a broken part and no spare, the variable `B` is set and the player cannot continue until a trade supplies what is missing (lines 4060 to 4090, 21000).

## 8. Random events

### 8.1 The event loop (line 3180)

`HR = 0: IF NOT SD THEN FOR L8 = C0 TO RE: IF RND (C1) < RE(L8) THEN ... ON L8 + C1 GOSUB 10000,10100,...,11400: INVERSE: IF B > 0 THEN GOSUB 4000: GOSUB 300: L8 = 20`

Each travelling day the program tests fifteen events in order, 0 to 14, drawing one random number for each. An event fires when the draw is below its chance `RE(n)`. The loop is skipped entirely on a stopped day (resting, delayed, waiting).

**At most one event fires on a travelling day.** `L8 = 20` is the last statement of the loop body, and Applesoft has no block structure, so an `IF ... THEN` clause runs to the end of the line: `L8 = 20` executes whenever an event fires, whether or not `B` is above zero. `NEXT L8` then sets `L8 = 21`, and the loop runs `FOR L8 = C0 TO RE` with `RE = 14`, so `21 > 14` ends it. `B` matters only for whether the action menu is opened afterwards, not for whether the loop continues.

The consequence for the draw count is worth stating, because it is easy to assume fifteen: the loop draws once per event *tested*, so a travelling day costs `k + 1` draws, where `k` is the index of the event that fired, and fifteen only when none fires. The events after `k` are not tested and spend nothing.

### 8.2 The fifteen events

**Table 16.** The fifteen random events, with daily chance, effect and line numbers.

| No. | Event | Daily chance `RE(n)` | Effect | Lines |
| --- | --- | --- | --- | --- |
| 0 | Snow bound | 1 if snow `AS` exceeds 30 | lose 1 to 10 days | 10000 |
| 1 | Snakebite | 0.007, only when warm or hotter | a member is bitten for 10 days | 10100 |
| 2 | (none) | 0 | no routine exists | none |
| 3 | Illness | `.01 + H / 1500` | section 5.3; `HR = 20` | 10300 |
| 4 | Gravesite | 1 on passing a saved tombstone | offer to read it | 10400 |
| 5 | Indians help find food | 0.05 when food is 0 | +30 pounds | 10500 |
| 6 | Severe storm | `(W > 7) + .15 * (TM < C2)` | nothing in cool or warm weather. In cold: blizzard, snow +8, lose 1 day. In heat: thunderstorm, rain +1, lose 1 day | 10600 |
| 7 | Fog or hail | 0.06 | past landmark 11 and not very hot: heavy fog, 50% lose 1 day. Up to landmark 11 and very hot: hail storm, message only | 10700 |
| 8 | Breakdown or injury | 0.04, or 0.07 in zones 3 and 4 | 33%: a wheel, axle or tongue breaks, lose 1 day. Of the rest, half: a member breaks an arm or leg; half: an ox is injured | 10800 |
| 9 | Lose trail or wrong trail | 0.02 | lose 1 to 5 days | 10900 |
| 10 | Rough or impassible trail | 0.05 in zones 3 and 4, else 0 | 50%: rough trail, `HR = 10`. 50%: impassible trail, lose 1 to 10 days | 11000 |
| 11 | Find wild fruit | 0.04 from May to September | +20 pounds | 11100 |
| 12 | Fire, lost member, or stray ox | 0.01 | equal thirds: fire in the wagon; a member is lost, lose 1 to 5 days; an ox wanders off, lose 1 to 3 days | 11200 |
| 13 | Abandoned wagon or thief | 0.02 | half each | 11300 |
| 14 | Water and grass | 0.5 when rain `AR` is below 0.1 | 20%: bad water, `HR = 20`. Of the rest, half: very little water, `HR = 10`; half: inadequate grass, no effect | 11400 |

Chances 1, 2, 7, 9, 12 and 13 are fixed at start-up (line 29001). Chances 8, 10 and 11 are set when a segment begins (line 3060), so they do not change mid-segment. The rest are recomputed daily (line 3160).

### 8.3 Details of individual events

- **Days lost** (line 550): `XX = INT (RND (1) * Z + 1)`, then that many stopped days of the daily cycle.
- **Broken part** (`PART.LIB`): the part is `INT (RND (1) * 3) + 5`. The player may try a repair, which succeeds half the time. Otherwise a spare is used; with no spare the player must trade for one.
- **Fire** (`LF.LIB` 50000): for each of clothing, bullets and the three kinds of parts, and then for food, there is a 50% chance of losing a random amount from 1 to all of it.
- **Abandoned wagon** (`LF.LIB` 51000): for each of the same five items, a 50% chance of finding 1 to 3 (bullets: 21, 42 or 63). Parts are added only if the total stays within 3.
- **Thief** (`LF.LIB` 52000): one of oxen, clothing, bullets or food is chosen, and a random amount from 1 up to the lesser of the holding and 100 is taken.
- **Gravesite** (line 450): the party passes a grave when it is on the same segment as a saved tombstone and has reached its recorded distance from the next landmark.

## 9. Talking, trading, rivers and forts

### 9.1 Talking to people (`TALK.LIB`)

Each landmark has three monologues, stored as 256-byte records in `OREGON1.SEQ` (landmarks 0 to 4) and `OREGON2.SEQ` (landmarks 5 to 16). The record read is at byte offset `(LM - S * 5) * 768 + A * 256`, where `S` is 0 or 1 for the disk side. `A` starts as a random 0, 1 or 2 on arrival and advances by one, wrapping, each time the action menu is drawn (line 4030), so the three speakers come round in turn. Each record holds a speaker and text of up to 255 characters, with an overflow field for longer text.

### 9.2 Trading (`TRADE.LIB`)

A trade attempt always costs one day (line 4900). The seven tradable goods and their unit values are oxen 20, clothing 10, bullets 0.10, wheels 10, axles 10, tongues 10 and food 0.20.

1. Draw the good wanted, `X = INT (RND (1) * 7)`, and the good offered, `Y`, the same way; if they match, `Y` moves on by one, wrapping.
2. Compute the exchange ratio `Z = ZX / (ZY * (1 + 1.2 * RND (1)))`, the value of the wanted good over the value of the offered good, worsened by a random factor between 1 and 2.2.
3. If `Z` is 1 or more, the emigrant wants 1 unit and offers `INT (Z)`. If less, he wants `INT (1 / Z)` and offers 1. A bullets-for-food pair is multiplied by 50 on both sides.
4. No offer is made if `RND (1) > .95`, or if accepting would exceed a carrying limit (3 spare parts, 2,000 pounds of food, 20 oxen).
5. If the player lacks the goods wanted, the offer is shown and withdrawn. Otherwise the player may accept, and the two quantities are exchanged.

### 9.3 River crossings (`RIVER.LIB`, `CROSS.LIB`)

Four landmarks are rivers. The array `RC(river, column)` holds their base data.

**Table 17.** Base data for the four rivers in the array RC.

| River | Depth (col 0) | Width (col 1) | Swiftness (col 2) | Bottom (col 3) | Extra option (col 5) |
| --- | --- | --- | --- | --- | --- |
| Kansas (landmark 1) | 1 | 600 | 3 | 0 smooth | 2 ferry |
| Big Blue (landmark 2) | 1 | 220 | 2 | 1 muddy | 0 none |
| Green (landmark 9) | 20 | 400 | 5 | 2 rough | 2 ferry |
| Snake (landmark 12) | 6 | 1000 | 7 | 2 rough | 1 Indian guide |

Column 4 holds 3, 2, 12 and 9 and is never read. Current conditions depend on accumulated rain (line 50150):

`RD = INT ((RC(RC,0) + AR * 2) * 10 + .5) / 10: RW = INT (RC(RC,1) + 15 * AR): RS = RC(RC,2) + AR: RB = RC(RC,3)`

Depth is the base plus twice the rain, to one decimal; width the base plus 15 times the rain; swiftness the base plus the rain.

**Table 18.** River crossing choices and the rules that decide their outcomes.

| Choice | Rule | Lines |
| --- | --- | --- |
| Ford, depth under 2.5 ft | Safe on a smooth bottom. Muddy: 40% chance of sticking, lose 1 day. Rough: 16% chance of tipping, then each good has a 10% to 40% chance of a random loss. | 50035, 50060, 50070 |
| Ford, 2.5 to under 3 ft | Supplies get wet; lose 1 day. | 50037 |
| Ford, 3 ft or more | Each good is lost in part with chance depth/10; each ox dies with chance (depth - 1)/10; each person except the leader drowns with chance (depth - 2.5)/10. | 50040 |
| Caulk and float | Refused under 1.5 ft. Costs 1 day. If depth exceeds 2.5 ft the wagon tips with chance swiftness/20; then goods are lost with chance 0.4 + swiftness/25 and people drown with chance (swiftness - 3)/15. | 50080 to 50085 |
| Ferry | Refused under 2.5 ft. Costs $5 and a wait of 2 to 6 days. Breaks loose with chance 0.05 if swiftness exceeds 5, plus 0.10 if it exceeds 10; then goods 0.8, people 0.2, oxen 0.5. | 50100 to 50120 |
| Indian guide | Costs 2 or 3 sets of clothing. The guide fords if depth is 2.4 ft or less, otherwise floats, and every risk above is divided by 5. | 50130 to 50145 |
| Wait | One stopped day of the daily cycle, then the menu again. | 50025 |

A partial loss of a good is `INT (RND (1) * X + 1)` of the `X` held (line 50205). With base depths of 20 and 6 feet, the Green and Snake rivers can never be forded safely.

While the party is at a river the flag `W1` is 1. Days spent waiting are full daily cycles: food is eaten, weather changes, and health is recalculated and capped. Two things are suppressed. Random events are skipped because the party is stopped, and the forced illness at line 3235 is skipped because `W1` is set. No one can fall ill or die while waiting at a river, however long the wait. Resting on the trail is different: there `W1` is 0 and the forced illness still applies.

### 9.4 Forts (`BUY.LIB`)

Forts sell the same seven goods at prices that rise with distance. The tier is

`Q = (LM > 2) + (LM > 4) + (LM > 7) + (LM > 10) + (LM > 12) + (LM > 13)`

and each price is `V = V + .25 * Q * V`.

**Table 19.** Fort price tiers, multipliers and food price per pound.

| Fort | Tier `Q` | Price multiplier | Food per pound |
| --- | --- | --- | --- |
| Fort Kearney | 1 | 1.25 | $0.25 |
| Fort Laramie | 2 | 1.50 | $0.30 |
| Fort Bridger | 3 | 1.75 | $0.35 |
| Fort Hall | 4 | 2.00 | $0.40 |
| Fort Boise | 5 | 2.25 | $0.45 |
| Fort Walla Walla | 6 | 2.50 | $0.50 |

Base prices are $20 an ox, $10 a set of clothing, $2 a box of 20 bullets, $10 a spare part and $0.20 a pound of food. A purchase is refused if `(Z * V) > MY + .001`, or if it would exceed 20 oxen, 2,000 pounds of food or 3 of a spare part (lines 50030 to 50033). The cost `Z * V` is subtracted from `MY` without rounding.

## 10. Ending the game

### 10.1 The Dalles and arrival (`END.LIB`)

At The Dalles the player chooses between rafting the Columbia River and the Barlow Toll Road. The toll is

`V = 5 + INT (I(2) + .5) * .5`

that is, $5 plus 50 cents an ox. It is paid only if `MY > V`; a party holding exactly the toll is told nothing and returned to the choice. The road is then travelled as segment 18, 100 miles.

Choosing the river, or arriving at the Willamette Valley by road, runs line 50050, which writes the end-of-journey layout of section 2.3 and chains to `FLOAT` or `WIN`. `FLOAT` writes the same layout again after the raft trip (line 910).

### 10.2 Death of the party and tombstones (`TOMB.LIB`)

When the last member dies, the game shows a tombstone with the leader's name and offers an epitaph of up to 29 characters. It then writes one record to the text file `TOMB.SEQ` on the current disk side (line 50035): four fields, each ended by a carriage return.

**Table 20.** Fields of the tombstone record written to TOMB.SEQ.

| Field | Content |
| --- | --- |
| 1 | `NM * 100 + LM`: the segment, as next landmark and last landmark |
| 2 | `D`: miles remaining to the next landmark |
| 3 | the leader's name |
| 4 | the epitaph |

The file is read at start-up and after the disk flip, two records at offsets 0 and 49 (lines 29004, `FLIP.LIB` 50030). New tombstones are always written at offset 0, so each side keeps one current grave. A later party on the same segment meets it as event 4. The management program can erase the tombstones.

### 10.3 Scoring (`WIN` 130 to 140, 625)

**Table 21.** Points awarded for each scoring item.

| Item | Points |
| --- | --- |
| Each person alive | 500 in good health, 400 fair, 300 poor, 200 very poor: `500 - 100 * PEEK (916)` |
| Wagon | 50 |
| Each ox | 4 |
| Each spare part | 2 |
| Each set of clothing | 2 |
| Bullets | 1 per 50, `INT (bullets / 50)` |
| Food | 1 per 25 pounds, `INT (food / 25)` |
| Cash | 1 per 5 dollars, `INT (cash / 5)` |

The total is multiplied by the profession number: 1 for a banker, 2 for a carpenter, 3 for a farmer. The final screen prints the date as the month, the day and "18" followed by the stored year byte (line 601).

### 10.4 The top ten (`WIN` 400 to 540, 630)

The rating is `R = (SC < 6000) + (SC < 3000)`: Trail guide at 6,000 points or more, Adventurer from 3,000 to 5,999, Greenhorn below 3,000. A score above the tenth entry is inserted in order and the list is rewritten to `HISCORE.SEQ`, a text file of thirty fields (name, points, rating) separated by carriage returns.

The original list, from the management program's DATA lines (20000 to 20010), is:

**Table 22.** The original top ten list, with points and ratings.

| Name | Points | Rating |
| --- | --- | --- |
| Stephen Meek | 7650 | Trail guide |
| David Hastings | 5694 | Adventurer |
| Andrew Sublette | 4138 | Adventurer |
| Celinda Hines | 2945 | Greenhorn |
| Ezra Meeker | 2052 | Greenhorn |
| William Vaughn | 1401 | Greenhorn |
| Mary Bartlett | 937 | Greenhorn |
| William Wiggins | 615 | Greenhorn |
| Charles Hopper | 396 | Greenhorn |
| Elijah White | 250 | Greenhorn |

## 11. Mini-games

### 11.1 Hunting (`HUNT.LIB`)

Hunting costs one day (line 4600). The game itself is a machine-language routine:

`& HUNT,Z,LM > 3 AND LM < 13,LM > 6,LM < 7,1,ZO,L,Z`

It receives the bullets held, three true-or-false values derived from the landmark number, a constant 1 and the climate zone, and returns a quantity in `L` and the bullets left in `Z`.

According to Bouchard (2016), the hunter can face and walk in 8 directions, with extra frames for walking. The animals were cut from eleven kinds to six to fit in memory. A shot animal is shown by flipping its picture upside down. The landscape is built at random from terrain objects suited to the region, three images of each. The book's examples show a bison on the prairie east of the Rockies and a rabbit in the conifer forests of the far West.

The routine itself is about 5 kilobytes of 6502 machine code, held outside the file system on the disk's system tracks and installed in the upper memory bank at address E000 (hexadecimal). It was disassembled for this paper and analysed with Claude Opus 5.5 (Medium). The findings below come from that code; the graphics were not decoded, so species names are matched by weight and region and are marked as probable.

**Arguments.** The command passes a block of nine bytes.

**Table 23.** Arguments passed to the hunting routine and their use.

| Argument | Use in the routine |
| --- | --- |
| `Z` (bullets) | starting bullet count; one is used per shot, and firing is refused at zero |
| `LM > 3 AND LM < 13` | if true, animal type 0 can appear |
| `LM > 6` | if true, animal type 1 can appear |
| `LM < 7` | if true, animal type 2 can appear |
| `1` | if non-zero, halves the chance that an animal appears (from 4 in 1,000 to 2 in 1,000 per attempt) |
| `ZO` | climate zone; selects the terrain objects |
| `L` (returned) | total live weight of the animals shot |
| `Z` (returned) | bullets left |

**Animals.** Types 3, 4 and 5 can always appear. A new animal's type is drawn evenly from the types allowed. When an animal is shot, its weight is a base plus a random amount, added to the total.

**Table 24.** Hunting animal types, where they appear, weight shot and probable species.

| Type | Where | Weight shot, pounds | Probable species |
| --- | --- | --- | --- |
| 0 | from Chimney Rock to the Snake River | 100 to 140 | not identified |
| 1 | past Independence Rock | 200 to 400 | elk or bear |
| 2 | up to Independence Rock | 1,700 to 2,000 | bison |
| 3 | everywhere | 120 to 150 | deer |
| 4 | everywhere | 2 to 10 | rabbit |
| 5 | everywhere | 3 to 7 | squirrel |

**Session.** A hunt lasts 2,500 passes of the routine's main loop. At most two animals are on screen at once. Once four animals have been shot, no more appear. The space bar fires and Return starts or stops walking.

**Terrain.** Each hunt places 4 to 7 terrain objects at random positions. Each zone draws from six entries of a table of object pictures: zone 0 uses object kinds A and C, zone 1 kind C only, zone 2 kinds B and E, zone 3 kinds D and E, and zone 4 kind B only, where A to E are the five kinds of object, three pictures each.

**Random numbers.** The routine has its own generator. It is seeded at the start of each hunt from the Applesoft seed bytes combined with the keyboard counter at addresses 78 and 79. It reads the Applesoft seed but never writes it, so hunting does not advance `RND`. Its results, however, depend on how long the player took at earlier keypresses.

The BASIC code then computes the meat (lines 50011 to 50020):

`L = INT (L / (2 - (L < 3)))`

A returned value of 3 or more is halved; a value under 3 is kept. If the wagon already holds 2,000 pounds, nothing is added. Otherwise the amount is cut to the space left, and then to at most 100 pounds, the most the hunters can carry back.

### 11.2 Rafting (`FLOAT`)

The raft game is written in BASIC. It reads the end-of-journey layout, then runs a loop in which the counter `TC` rises by one each pass (lines 1070 to 1180).

- **Raft.** The raft occupies one of 18 positions `HP` from 0 to 17 and starts at 16. The arrow keys change its direction `DIR` between -1 and +1, and it moves one position per pass. Moving past position 1 or 16 counts as hitting the shore and reverses the direction (line 400).
- **Rocks.** There are two rock slots. Each pass, an empty slot is filled if `INT (100 * RND (C1) + C1) <= 15`, a 15% chance. A rock moves 8 pixels right and 4 up per pass and is removed on leaving the screen.
- **Collision.** The raft's box and each rock's box are tested for overlap (lines 200, 1120 to 1130).
- **Landing.** Signs appear at passes 60, 120 and 170. After pass 205 the raft lands if it is at position 17. After pass 225 it has missed the landing: goods are lost with chance 0.5, and it lands anyway.

**Table 25.** Chances of loss in a rafting collision, by collision type.

| Collision | People drown | Each ox lost | Each good partly lost |
| --- | --- | --- | --- |
| Shore | 0.15 | 0.3 | 0.5 |
| Rock | 0.6 | 0.6 | 0.7 |

The loss routines are the same as at river crossings, and the leader again cannot drown while others live. If ten or more separate losses occur in one collision, the raft is destroyed and everyone is lost (line 730). If everyone drowns, the game returns to the menu.

The speed of this game depends on how fast the interpreter runs the loop, so a replica must pace the loop to match a 1 MHz machine.

## 12. The numerical environment and algorithmic parity

Algorithmic parity cannot be achieved by reimplementing the game's arithmetic. It can be achieved only by executing the original Applesoft ROM routines, in a 6502 emulator such as py65 (Naberezny, n.d.) or in a full Apple II emulator such as ApplePy (Tauber, n.d.). This section explains why. Addresses below are hexadecimal.

### 12.1 The number format

Every Applesoft number is a 5-byte floating-point value, including loop counters, flags and array indexes. Integer variables marked with `%` are converted to this format for any calculation.

**Table 26.** Parts of the 5-byte Applesoft floating-point format.

| Part | Size | Detail |
| --- | --- | --- |
| Exponent | byte 1 | power of two plus 128; an exponent byte of 0 means the value is zero |
| Sign | top bit of byte 2 | 0 positive, 1 negative |
| Significand | 32 bits | the top bit is always 1, so it is not stored and its place holds the sign; the other 31 bits fill bytes 2 to 5 |

The significand is a fraction from 0.5 up to 1, so the value is the significand times 2 to the power (exponent byte minus 128). The constant 1.0 is stored as `81 00 00 00 00` and 0.5 as `80 00 00 00 00`, as the game's own `VAR.BIN` shows. Precision is 32 bits, about 9.6 decimal digits. There are no infinities or not-a-number values: overflow stops the program with an OVERFLOW error, and underflow gives zero.

### 12.2 How the interpreter rounds

Calculations take place in a register called FAC (addresses 9D to A2) with an extra eighth byte of precision, the extension byte at AC. Three behaviours follow from the ROM code.

- **Rounding, not truncation.** The routine `ROUND.FAC` at EB72 adds one to the significand when the extension byte is 80 hex or more. It runs when a result is stored in a variable.
- **Rounding at pushes.** When an expression needs to set a partial result aside, the evaluator rounds it to 32 bits before pushing it on the stack (DE20). A partial result that is used at once keeps its extension byte. The same formula can therefore give different last bits depending on the order of its terms.
- **Alignment loses bits.** In addition, the smaller operand is shifted right into the extension byte, and bits shifted beyond it are discarded.

A numeric constant in the program text is converted from its decimal digits **once**, when the line is tokenised, and the resulting 5-byte value is stored inline; `LIST` reconstructs the printed form from those bytes rather than from the digits. Nothing is re-converted when the line runs. The reason the programmers nevertheless held 0, 1, 2, 3, 4 and 0.5 in the variables `C0` to `C4` and `P5` is speed: an expression using a variable does not have to tokenise and convert a literal at all.

The conversion itself is still the ROM's, and a replica must use it rather than a host-language parse. A constant such as `.8` is whatever that routine produces, not necessarily the nearest representable value: `.8` is `80 4C CC CC CD` and `.2` is `7E 4C CC CC CD`.

### 12.3 The random number generator

`RND` at EFAE keeps a 5-byte seed at C9 to CD. For a positive argument it multiplies the seed by one constant, adds a second, exchanges the first and last significand bytes, and renormalises the result into the range 0 to 1. Both constants are stored in the ROM with four bytes instead of five, so each is read together with the byte that happens to follow it. The published disassembly (Sander-Cederlof, n.d.) notes that the addition has almost no effect for that reason. Sander-Cederlof (1984) found that the sequence can fall into short cycles.

A negative argument makes the argument itself the basis of the new seed, which is how `MENU` seeds the game. `RND (0)` returns the last value again.

Every chance decision in the game is a comparison of a `RND` value with a threshold, or `INT` of a `RND` value times a range. If the generator is not reproduced bit for bit, the first event of the journey already differs.

### 12.4 Why reimplementation fails

A replica that computes in the host language must reproduce all of the following exactly. Each is a place where a port can diverge without any visible error.

**Table 27.** Numerical risks for a replica and what must be matched for each.

| Risk | What must be matched |
| --- | --- |
| Rounding points | Which partial results are rounded and which keep the extension byte depends on the evaluator's internal order, not on the formula as written |
| Guard precision | One extension byte, with bits beyond it dropped during alignment; not the same as rounding an exact result |
| Constants | The ROM's decimal-to-binary conversion of each literal, repeated at run time |
| Multiply and divide | The ROM's own shift-and-add loops and their handling of the extension byte |
| `RND` | The short constants read with their neighbouring bytes, the byte exchange and the renormalisation |
| `INT` and comparisons | The ROM's conversion routine (`QINT` at EBF2) and exact byte comparison; no tolerance |
| Number to text | `STR$` and `PRINT` formatting, used in the money routine and in file records |
| Errors | ILLEGAL QUANTITY, OVERFLOW and the game's error handler |
| Machine-language parts | The hunting game and all `&` routines, which no translation of the BASIC covers |

The obvious substitutes do not meet these requirements.

**Table 28.** Substitute number formats and why each does not give parity.

| Substitute | Why it does not give parity |
| --- | --- |
| Python `float` (64-bit) | 53-bit significand; keeps bits the original discards |
| `numpy.float32` | 24-bit significand; fewer bits than the original |
| 64-bit result with the low 21 bits set to zero | Truncates where the ROM rounds. It stores different values for the game's own constants `.8`, `.2` and `.1` |
| `decimal` at 9 digits | Rounds in base 10; the original rounds in base 2 |
| `mpmath` at 32 bits | Rounds an exact result to nearest-even; ignores the extension byte, the evaluator's rounding points and the ROM's constant conversion |
| A hand-written 5-byte class | Possible in principle, since the ROM is deterministic and disassembled, but it is a reimplementation of every routine above and inherits every risk in the first table |

Tolerance comparisons such as `math.isclose` must not be used anywhere. The original compares exactly, and tests such as `IF I(2) = INT (I(2))` and `PF = C0` depend on it.

### 12.5 The two valid approaches

**Full emulation.** Run the unmodified disk images in an Apple II emulator driven from Python, such as ApplePy. The Python program supplies keystrokes, including the timing that sets the seed, and reads the game state from emulated memory. The pointer at address 69 gives the start of the variable table (39170 decimal in the main program); each simple variable is seven bytes, two for the name and five for the value. This approach reimplements nothing. It covers the BASIC, the ROM, the `&` routines and the hunting game, and it has parity by construction.

**ROM routines called from Python.** Load the Applesoft ROM into a 6502 emulator such as py65 and call its routines for every numeric operation: the operator entries FADDT (E7C1), FSUBT (E7AA), FMULTT (E982) and FDIVT (EA69), `ROUND.FAC` (EB72), `INT` (EC23), `RND` (EFAE), and the conversion and formatting routines. The Python program holds only the game's control flow and passes five-byte values, never host floats. This gives the original arithmetic but still requires a faithful transcription of the BASIC, including the order of operations inside each expression, and it cannot cover the machine-language parts.

Full emulation is the only approach with no reimplementation risk. The second approach is acceptable for the BASIC-only parts of the game when a native Python structure is needed, for example for large-scale simulation. Both need an Apple II ROM image, which is Apple's copyrighted firmware and must be obtained separately.

### 12.6 Status of verification

The statements in 12.2 and 12.3 come from the published commented disassembly of the ROM (Sander-Cederlof, n.d.). The ROM has since been executed, and two of the three items below are settled.

**The stored bytes of the constants.** `.8` converts to `80 4C CC CC CD`, `.2` to `7E 4C CC CC CD`, `.1` to `7D 4C CC CC CD`, `.9` to `80 66 66 66 66`, and `1.0` to `81 00 00 00 00`. None is the nearest representable value, which is the point of 12.2.

**The two constants in `RND`,** read out of the image: five bytes at `$EFA6` are `98 35 44 7A 68`, the multiplier, and five at `$EFAA` are `68 28 B1 46 20`, the addend. The addend is about 1.9 times 10 to the minus 8 against products of order 10 to the 7, which is why it has almost no effect; its fifth byte, `20`, is the opcode of the `JSR` at `$EFAE` that begins the routine, which is what "each is read together with the byte that happens to follow it" means in practice.

**Fifteen values of `RND` from a known seed,** starting from `81 00 00 00 00`:

```
0.4072949116816744   0.608041618950665      0.25951706536579877
0.08268766026594676  0.35866158816497773    0.9610444016288966
0.5672113706823438   0.6001326921395957     0.33425431547220796
0.6068662970792502   0.6758213557768613     0.3164409970631823
0.036882334752590396 0.03491484130790923    0.2833032483467832
```

which leave the seed at `$C9`–`$CD` as `7F 11 0D 1F 95`.

Still outstanding is the third item: a day-by-day comparison of state against the running game, which needs the disk image rather than the ROM.

## 13. Bugs and quirks a replica must keep

Nine behaviours of the shipped code are probably unintended. A faithful replica reproduces them; full emulation reproduces them automatically.

**Table 29.** Probably unintended behaviours of the shipped code, with cause and location.

| Behaviour | Cause | Where |
| --- | --- | --- |
| No one falls ill or dies while waiting at a river, however long | Events are skipped on stopped days, and the forced illness is disabled while `W1` is 1 | Lines 3180, 3235, 3500; `RIVER.LIB` 50025 |
| After a very long wait the party dies at once | The starve factor `FS` has no cap. It keeps rising by 0.8 a day and then holds health at 139 for many days after food returns, because it only halves daily | Lines 3225 to 3235 |
| The game stops with "Error 53 at line #50050" if the year passes 2055 | `POKE 901,AY - 1800` with a value over 255 raises Applesoft's ILLEGAL QUANTITY error, code 53 | `END.LIB` 50050 |
| The final screen shows the wrong century after 1899 | The year is printed as "18" followed by the stored byte, so 1905 appears as 18105 | `WIN` 601 |
| A broken arm has no effect | The injury number 0 is stored as the member's illness, and 0 means healthy. The same line overwrites any illness the member already had | Line 10830 |
| A thief never takes money | The cash branch tests for item 0, but the item drawn is always 2, 3, 4 or 8 | `LF.LIB` 52000 to 52020 |
| The Portland climate row is never used | The zone number stops at 4 | Line 1000 |
| A party with exactly the Barlow toll cannot pay | The test is `MY > V` | `END.LIB` 50020 |
| February always has 28 days | Fixed month lengths; 1848 was a leap year | Line 3255 |

The long-wait behaviour was documented by moralrecordings (2025), in whose test a wait of 14,272 game years left `FS` at 4,166,608.55078125 (bytes `96 7E 4F 42 34`). The party then died within days of crossing, and a modified game that survived crashed with Error 53 at The Dalles. The study notes that 207 years is the longest journey that avoids the crash and 51 years the longest that shows the right century.

That `FS` value is not an exact multiple of 0.8. A rounding model of the addition puts it about 0.02% below the exact sum for the same number of days, because 0.8 cannot be represented exactly and each addition is rounded. It is an ordinary accumulation of rounding, not a failure of the number format. At that size the format still resolves steps of 1/1024, so additions of 0.8 continue normally.

## 14. Conclusion

The 1985 Oregon Trail is a daily simulation driven by a small set of formulas: one health value with seven penalties, a five-zone climate model, fifteen random events tested in order, and depth-based river risks. All of them are fully recoverable from the BASIC source and the saved variable table, and this paper gives each with its line number.

Replicating the rules is therefore straightforward. Replicating the game's exact behaviour is not. Every outcome depends on the interpreter's random number generator and on arithmetic whose rounding rules, constant conversion and evaluation order live in the Applesoft ROM. Imitating that arithmetic with masked 64-bit floats (Institute of Electrical and Electronics Engineers \[IEEE\], 1985), the `decimal` module or a custom class does not match the ROM, and each adds reimplementation risk.

Algorithmic parity requires running the original ROM routines: either the whole game in an Apple II emulator such as ApplePy, or the ROM's arithmetic and `RND` routines under a 6502 emulator such as py65 beneath a transcription of the BASIC. Only the first carries no reimplementation risk. A replica built any other way can be faithful to the rules and probabilities documented here, but should not claim parity.

Three pieces of work remain: executing the ROM to confirm the behaviour described in section 12, completing the analysis of the hunting routine's movement and graphics, and analysing the other `&` routines.

## Appendix A: Variables

Applesoft recognises only the first two characters of a variable name, and all variables are global. Short names such as `Z`, `Z$`, `L`, `V`, `X` and `Y` are reused as scratch variables throughout.

**Table A1.** Variables and their meanings.

| Variable | Meaning |
| --- | --- |
| `AD`, `AM`, `AY` | day, month, year |
| `AR`, `AS` | accumulated rain; snow on the ground |
| `B` | cannot-continue flag: 2 for no oxen, 5 to 7 for a broken part, 1 for Return pressed |
| `BS`, `V` | base speed; miles travelled today |
| `C0` to `C4`, `P5` | the constants 0, 1, 2, 3, 4 and 0.5 |
| `D`, `DD`, `M` | miles left in the segment; segment length; total miles travelled |
| `F0`, `FC` | ration penalty; pounds of food eaten per day |
| `FS` | freeze and starve factor |
| `H`, `H0`, `HR` | party health; number sick; event hardship |
| `H1()`, `H2()` | each member's illness number and days left |
| `I()`, `I$()` | inventory quantities and names, 2 to 8 |
| `IL$()` | illness names, 0 to 8 |
| `IX` | risk divisor at rivers: 1, or 5 with a guide |
| `LM`, `NM` | current landmark; next landmark |
| `LM$()`, `LM()` | landmark table; segment table |
| `MD` | the segment's speed base, 20 or 12 |
| `MY` | money in dollars |
| `N$()`, `NP` | party names; number alive |
| `OP` | sets of clothing per person |
| `P`, `R` | pace and rations, 1 to 3 |
| `PF` | pounds of food during the daily cycle |
| `PP`, `QP`, `QT` | rain flag; month's rain chance; month's minimum temperature |
| `RC()`, `RD`, `RW`, `RS`, `RB` | river base data; current depth, width, swiftness, bottom |
| `RE`, `RE()` | highest event number (14); event chances |
| `SD` | stopped days remaining |
| `SN()`, `ML()`, `DL` | saved tombstone segment and distance; distance of the next grave |
| `TM`, `W` | temperature class 0 to 5; weather code 0 to 9 |
| `TR`, `TS` | today's rain and snow |
| `W1` | 1 while at a river crossing |
| `WC$()` | climate strings |
| `ZC`, `ZF`, `ZP`, `ZT` | clothing, ration, pace and temperature penalties |
| `ZO` | climate zone, 0 to 4 |

## Appendix B: DEF FN functions

**Table B1.** DEF FN functions, with where each is defined, its definition and its use.

| Function | Defined in | Definition | Use |
| --- | --- | --- | --- |
| `FN HI(Z)` | all main programs except WIN | `INT (Z / 256)` | high byte for POKE |
| `FN LO(Z)` | all main programs except WIN | `Z - FN HI(Z) * 256` | low byte for POKE |
| `FN X(Z)` | all main programs | `INT (Z / 7) * 7` | aligns a screen column to a 7-pixel byte boundary |
| `FN B(Z)` | `OREGON TRAIL` | `( PEEK ( - 16384) = 13)` | true if Return is waiting at the keyboard; the argument is unused |
| `FN W(Z)` | `OREGON TRAIL` | see section 6.2 | climate lookup |
| `FN W(Z)` | `MENU`, `BUY SUPPLIES` | `VAL ( MID$ (WC$(ZO),(AM) * 2 + 1 + Z,1))` | defined but never called |
| `FN P(Z)` | `MENU` | `PEEK (Z) + PEEK (Z + 1) * 256` | reads a two-byte value |
| `FN RX(Z)`, `FN RY(Z)` | `FLOAT` | `84 + 8 * Z`, `5 * Z - 6` | raft screen position from `HP` |

## Appendix C: PEEK and POKE addresses

These are all the fixed addresses the BASIC code reads or writes. The machine-language routines may use others.

**Table C1.** Fixed addresses read or written by the BASIC code, with their use.

| Address | Use |
| --- | --- |
| 78, 79 | keyboard wait counter, read once to seed `RND` (`MENU` 1015) |
| 216 | error-trap flag, cleared by the error handler |
| 218, 219 | line number of the last error |
| 222 | code of the last error |
| 230 | high-resolution page selector, set in `FLOAT` and side 2 `MENU` |
| 900 to 917 | state hand-over; see section 2.3 |
| 919 | initialisation flag read by the error handler |
| 955 | disk-configuration flag, compared with 254 before a flip prompt |
| 975 | sound on or off |
| 1012 | power-up byte, cleared before a restart |
| 1920 onward | party names, zero-terminated; this is ordinary text-screen memory, unused while the game shows graphics |
| -16384 | keyboard data, tested for Return |
| -4, -3 | reset vector, used to restart |

## Appendices D to H

Further material for rebuilding the game is in the following tabs of this document. Appendix D holds the dialogue records (Appendix E: Dialogue records), with the game's original spelling. Appendices E to H (Appendices G to J) hold the remaining data tables (E), the `&` command reference (F), the sequence of random draws (G) and the status of reference traces (H).

## References

Applesoft BASIC. (n.d.). In *Wikipedia*. Retrieved October 4, 2026, from <https://en.wikipedia.org/wiki/Applesoft_BASIC>

Bouchard, R. P. (2016). *You have died of dysentery: The creation of The Oregon Trail – the iconic educational game of the 1980s* (1st ed.) \[Kindle edition\]. <https://www.amazon.com.au/You-Have-Died-Dysentery-educational-ebook/dp/B01B8JMKMC>

Institute of Electrical and Electronics Engineers. (1985). *IEEE standard for binary floating-point arithmetic* (ANSI/IEEE Std 754-1985).

McFadden, A. (n.d.). *Applesoft BASIC ROM disassembly*. 6502disassembly.com. Retrieved October 4, 2026, from <https://6502disassembly.com/a2-rom/Applesoft.html>

Minnesota Educational Computing Consortium. (1985). *The Oregon Trail* (Release 1.4; Product A-157) \[Computer software and source listings for the Apple II\].

moralrecordings. (2025, January 11). *Can you complete the Oregon Trail if you wait at a river for 14272 years: A study*. <https://moral.net.au/writing/2025/01/11/waiting_for_oregon/>

Naberezny, M. (n.d.). *py65* \[Computer software\]. <https://pypi.org/project/py65/>

Sander-Cederlof, B. (1984, May). Analysis of the Applesoft random number generator. *Apple Assembly Line, 4*(8). <https://www.txbobsc.com/aal/1984/aal8405.html>

Sander-Cederlof, B. (n.d.). *S-C DocuMentor: Applesoft* \[Commented disassembly of the Applesoft ROM; segments E7A0, EB72, DD7B, EE8D and D260 consulted\]. Retrieved October 4, 2026, from <https://www.txbobsc.com/scsc/scdocumentor/E7A0.html>

Tauber, J. (n.d.). *ApplePy* \[Computer software\]. <https://speakerdeck.com/jtauber/applepy-an-apple-emulator-in-python>

The Oregon Trail (1971 video game). (n.d.). In *Wikipedia*. Retrieved October 4, 2026, from [https://en.wikipedia.org/wiki/The\_Oregon\_Trail\_(1971\_video\_game)](https://en.wikipedia.org/wiki/The_Oregon_Trail_%281971_video_game%29)

The Oregon Trail (1985 video game). (n.d.). In *Wikipedia*. Retrieved October 4, 2026, from [https://en.wikipedia.org/wiki/The\_Oregon\_Trail\_(1985\_video\_game)](https://en.wikipedia.org/wiki/The_Oregon_Trail_%281985_video_game%29)
