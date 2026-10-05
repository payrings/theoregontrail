# Appendices E to H: material for rebuilding the game

The main paper gives the rules. These appendices give what a rebuild needs beyond the rules, apart from the source code itself: the dialogue records, the data tables, the machine-language interface, and the order of random draws.

| Appendix | Content | Where |
| --- | --- | --- |
| D | The 51 dialogue records, with landmark, slot, speaker and text | its own tab, Appendix D |
| E | Data tables not already in the main paper | below |
| F | Reference for the `&` commands | below |
| G | Sequence of random draws | below |
| H | Reference traces | not yet available; see below |

Appendix D has its own tab and is set in code blocks because it must be exact to the character. It was produced directly from the game's files, not retyped.

## Appendix E: Data tables

These are the contents of the saved variable table `VAR.BIN` that the main paper does not already list. The landmark and segment tables are in section 4.1 of the paper, the climate codes in 6.2, the illness names in 5.3, the river data in 9.3 and the original top ten in 10.4. Data held in DATA lines (default names, month names, scoring text, river menu text) is in the BASIC source, which is not reproduced in this paper.

### E.1 Simple variables at start-up

**Table E1.** Values of the simple variables at start-up.

| Variable | Value | Variable | Value |
| --- | --- | --- | --- |
| `C0` | 0 | `NP` | 5 |
| `C1` | 1 | `P` | 1 |
| `C2` | 2 | `R` | 1 |
| `C3` | 3 | `H` | 0 |
| `C4` | 4 | `M` | 0 |
| `P5` | 0.5 | `LM` | 0 |
| `PQ` | 0.25 | `S` | 0 |
| `RE` | 14 | `AR` | 3 (replaced at line 29004) |
| `PA` | 12288 | `SA` | 15900 (replaced by 37380 at line 29004) |
| `SR` | 1 | `DF` | 1 |

Six string variables hold single control characters: `D$` code 4, `CC$` code 3, `CL$` code 12, `CM$` code 13 (carriage return), `CE$` code 5 and `CF$` code 6. `PN$` is "OREGON TRAIL" and `WW$` is "What is your choice? ".

Arrays that start empty or zero: `RE(0 to 14)`, `T$(0 to 10)`, `I(0 to 8)`, `H1(0 to 4)`, `H2(0 to 4)`, `N$(0 to 4)`.

### E.2 Text arrays

**Table E2.** Text arrays and their contents in index order.

| Array | Contents, in index order from 0 |
| --- | --- |
| `M$(0 to 11)` | January, February, March, April, May, June, July, August, September, October, November, December |
| `I$(0 to 8)` | (empty), Wagon, oxen, sets of clothing, bullets, wagon wheels, wagon axles, wagon tongues, pounds of food |
| `P$(0 to 2)` | steady, strenuous, grueling |
| `R$(0 to 2)` | filling, meager, bare bones |
| `H$(0 to 3)` | good, fair, poor, very poor |
| `W$(0 to 9)` | very cold, cold, cool, warm, hot, very hot, rainy, snowy, very rainy, very snowy |
| `AQ$(0 to 9)` | Continue on trail, Check supplies, Look at map, Change pace, Change food rations, Stop to rest, Attempt to trade, Talk to people, Buy supplies, Hunt for food |
| `IL$(0 to 8)` | a broken arm, a broken leg, a snakebite, exhaustion, typhoid, cholera, measles, dysentery, a fever |

### E.3 Goods table `S$(0 to 6, 0 to 3)`

Used by forts, trading and the broken-part messages.

**Table E3.** The goods table: name, base price, unit and plural ending of each good.

| Index | Name | Base price | Unit | Plural ending |
| --- | --- | --- | --- | --- |
| 0 | Oxen | 20 | ox | en |
| 1 | Clothing | 10 | set | s |
| 2 | Ammunition | 2.00 | box | es |
| 3 | Wagon wheels | 10 | wheel | s |
| 4 | Wagon axles | 10 | axle | s |
| 5 | Wagon tongues | 10 | tongue | s |
| 6 | Food | 0.20 | pound | s |

### E.4 Climate strings `WC$(0 to 5)`

The six strings exactly as stored, 24 characters each. Section 6.2 of the paper gives their character codes.

```
0: ;+?,I8V?_NiNnElFdHY<K1@-
1: 5#:#B(O3Y<c?i9g4].Q(C#9#
2: 5#9#>'H.R3\+e(c$X'M'?%8#
3: 1#6%>*I5R7[+c&a#W)L,=&3$
4: <-B+H+P*X*_'h!f!]$R(F+>,
5: DWIGLBQ5W3[.`#`(]/T?LTG^
```

### E.5 Screen position tables

These do not affect the simulation. A rebuild that redraws the map and travel screen needs them.

`MP%(landmark, 0 to 1)`: map x and y of each landmark, used by `MAP.LIB` to draw the route travelled.

**Table E4.** Map coordinates of each landmark.

| Landmark | x | y | Landmark | x | y |
| --- | --- | --- | --- | --- | --- |
| 0 | 245 | 139 | 9 | 134 | 108 |
| 1 | 235 | 136 | 10 | 124 | 104 |
| 2 | 226 | 126 | 11 | 110 | 101 |
| 3 | 207 | 122 | 12 | 93 | 102 |
| 4 | 185 | 120 | 13 | 80 | 87 |
| 5 | 170 | 114 | 14 | 70 | 76 |
| 6 | 155 | 100 | 15 | 69 | 66 |
| 7 | 143 | 108 | 16 | 55 | 71 |
| 8 | 132 | 117 | 17 | 45 | 70 |

`L%(next landmark - 1, 0 to 1)`: the picture number of the approaching landmark and a horizontal offset, used at line 3000 to place it on the travel screen.

**Table E5.** Picture number and horizontal offset of the approaching landmark on the travel screen.

| Index | Picture | Offset | Index | Picture | Offset |
| --- | --- | --- | --- | --- | --- |
| 0 | 8 | 78 | 9 | 9 | 64 |
| 1 | 8 | 78 | 10 | 10 | 70 |
| 2 | 5 | 50 | 11 | 14 | 78 |
| 3 | 6 | 36 | 12 | 11 | 56 |
| 4 | 7 | 50 | 13 | 15 | 56 |
| 5 | 6 | 36 | 14 | 12 | 56 |
| 6 | 7 | 56 | 15 | 13 | 112 |
| 7 | 8 | 56 | 16 | 16 | 50 |
| 8 | 14 | 78 |  |  |  |

`B(0 to 5)`: the column positions of the six status labels on the travel screen: 95, 70, 81, 95, 23, 20.

### E.6 Data files on disk

**Table E6.** Data files on disk and their formats.

| File | Format |
| --- | --- |
| `HISCORE.SEQ` | thirty text fields ended by carriage returns: name, points, rating for each of ten entries |
| `TOMB.SEQ` | two records 49 bytes apart, each of four fields ended by carriage returns: segment code, miles remaining, name, epitaph. An empty record has segment code 0 |
| `OREGON1.SEQ`, `OREGON2.SEQ` | dialogue records; see Appendix D |
| `VAR.BIN`, `PT.BIN` | saved variable table (4,516 bytes, loaded at 39170) and its 12 bytes of interpreter pointers (loaded at 105) |
| `L0.PCK` to `L17.PCK`, `M0.PCK`, `TS.PCK`, `RIVER.PCK` | packed pictures loaded by `& DUN`: landmark views, the map, the tombstone, the Columbia River |
| Files ending `.IMA`, `MS0.BIN` to `MS17.BIN`, `TS.BIN`, `DALLESUTIL.OBJ` | image sets, binary data loaded per landmark, and machine code; not analysed |

## Appendix F. The machine-language (&) commands

The BASIC programs call a machine-language package through the Applesoft ampersand hook. The package is not a file on the disk: it is loaded from the system tracks at boot, and its hunting part lives in language-card RAM. This appendix is based on a disassembly of that package. The command dispatcher holds a table of command names followed by a table of handler addresses; each handler was disassembled from its entry point and its argument list read from the calls it makes to the Applesoft expression evaluators (numeric, string, variable pointer, comma check). The disassembly and its interpretation were carried out with the AI model Claude Opus 5.5 (Medium), and have not been checked by running the code in an emulator. Argument lists are therefore reliable; descriptions of what a routine does with its arguments are a reading of the code and should be treated as such.

### F.1 Screen, window and text commands

**Table F1.** Screen, window and text commands, with their arguments and behaviour.

| Command | Arguments (from the code) | Behaviour |
| --- | --- | --- |
| BOX | x1, y1, x2, y2 \[, colour\] | Draws a rectangle on the hi-res screen; colour is optional. |
| DFT | n, address | Defines font n as the character set stored at address. |
| AFT | n | Makes font n the active font. |
| PARSE / NOPARSE | none | Turn on or off the interpretation of control codes inside printed text. |
| GCP | xvar, yvar | Returns the current text cursor position into two variables. |
| VSP, HSP, TSP | n | Set vertical, horizontal and tab spacing of the text output. |
| CEL | none | Clears from the cursor to the end of the line. |
| CEW | none | Clears from the cursor to the end of the window. |
| SPACE | n | Outputs n blank character cells. |
| CO | x, y | Moves the text cursor. |
| DFW | n AT x, y, w, h | Defines window n (1 to 7) with origin and size. |
| WIND | n | Selects window n (must be below 8) as the output window. |
| IN | n | Sets the left indent used for wrapped text. |
| SHIGH / CHIGH | none | Set and clear a highlight flag, so later text is drawn highlighted or normal. |
| HOOK / UNHOOK | none | Route or stop routing PRINT output through the hi-res text driver. |
| INP | length, allowed-characters string, flag, string variable | Line input of at most length characters, accepting only the allowed characters; result in the string variable. This is the input routine used for every prompt in the game. |

### F.2 Graphics and sound commands

**Table F2.** Graphics and sound commands, with their arguments and behaviour.

| Command | Arguments (from the code) | Behaviour |
| --- | --- | --- |
| DUN | "file" AT address, n | Loads a packed picture from disk and unpacks it. |
| UIM | n, address \[, var\] | Unpacks image n from a library at address; optionally returns the end address or length. |
| IMAGE | n, x, y | Draws image n of the current library at x, y. |
| PUT | x, y, address | Draws the bitmap block stored at address. |
| TAKE | x1, y1, x2, y2, address | Copies a screen rectangle into memory at address (the inverse of PUT). |
| DPC | x, y, var | Returns one byte for the screen position x, y; from the code this is most likely a pixel or collision test. Meaning not fully established. |
| PT | n \[, flag\] | Plays tune n; a key press interrupts it. |
| PN | pitch and duration values | Plays a single note. |
| IHUNT | none | Initialises the hunting module (calls its first entry point). |
| HUNT | n (16-bit), five one-byte values, var, var | Runs the hunting module. The handler copies the first six arguments into a fixed memory block, calls the module, and returns two results into the variables; see section 11.1. |

### F.3 Disk and program commands

**Table F3.** Disk and program commands, with their arguments and behaviour.

| Command | Arguments (from the code) | Behaviour |
| --- | --- | --- |
| RFL | "file" \[AT address\] | Reads a file into memory; a BASIC-type file is relocated to the program area. |
| RNH | "file" | Loads and runs a program or binary. |
| APP | "file" | Appends a BASIC file at the end of the program in memory. This is how the library modules are chained. |
| DBL | from, to | Deletes the program lines in the given range, freeing space before the next APP. |
| OPEN | name \[, var\] | Opens a file; the optional variable receives a status. |
| CLOSE | none | Closes the open file. |
| TREED | delimiter string, string variable \[, var\] | Reads text from the open file up to the delimiter into the string variable. Used for the dialogue records in Appendix D. |
| TWRITE | string | Writes a string to the open file. |
| TPTR | n | Sets the file position. |
| GTP | var | Returns the file position. |
| CDN | string variable | Reads the disk name into a string; used to tell which disk side is in the drive. |
| SET | n | Selects the disk side or drive expected by later disk commands. |
| CST | address | Stores an address used by the package (purpose not established from the entry code). |
| QFH | not established | The entry point could not be read with confidence. |

### F.4 Commands not in this package

PUTP, DPB and the doubled ampersand form are used only by the river-floating program, which loads its own machine-language file for them; that file was not disassembled, and their behaviour as described in the main paper is inferred from how the BASIC code uses them. The same holds for the USR calls. The packed picture, image-library and tune data formats were not decoded: a rebuild must supply its own graphics and sound, or run the original routines.

None of the commands in F.1 to F.3 calls the Applesoft random number routine or changes its seed, except that the hunting module reads the seed once to start its own generator (section 11.1). They therefore do not affect the sequence of random events in the BASIC code.

## Appendix G: Sequence of random draws

A rebuild matches the original only if it calls `RND` the same number of times in the same order. This appendix lists every draw made by the BASIC code. Two rules of the interpreter matter throughout.

- Applesoft evaluates both sides of `AND` and `OR`. In `IF X AND RND (1) < V`, the draw happens even when `X` is false.
- A draw multiplied by zero still happens, as in `RND (1) * 12 * ( PEEK (902) < 4)`.

The hunting routine was disassembled and makes no Applesoft draws (G.6). Draws inside the other machine-language routines are not known, but none is expected, since those routines handle display, input and files.

### G.1 Setup

**Table G1.** Random draws during setup, by step and program line.

| Step | Draws | Line |
| --- | --- | --- |
| Each main-menu keypress | reseed with the negative keyboard counter | `MENU` 1015 |
| Shuffle default names | 10 | `MENU` 6000 |
| Store | none |  |
| Initial snow | 1 | 29000 |
| Initial rain | 1 | 29004 |

### G.2 Each landmark

**Table G2.** Random draws at each landmark.

| Step | Draws | Line |
| --- | --- | --- |
| Arrival, including the start at Independence | 1 (first dialogue) | 1000 |

### G.3 Each day

**Table G3.** Random draws on each day, in order, with program lines.

| Order | Step | Draws | Line |
| --- | --- | --- | --- |
| 1 | Event loop, travelling days only | 1 per event tested, 15 if the loop runs to the end, plus the event's own draws (G.4) | 3180 |
| 2 | Weather change test | 1 | 3205 |
| 3 | If the weather changes | 2: temperature, then rain flag | 3205 |
| 4 | If the rain flag is set | 1: heavy or light | 3206 |
| 5 | If health exceeds 139 and not at a river | 2: disease, then victim | 3235, 10300, 11500 |

A stopped day (resting, a delay, waiting at a river) omits step 1. Days lost to an event run as stopped days nested inside that event, before the event loop continues.

### G.4 Inside each event

**Table G4.** Random draws inside each event, in order.

| Event | Draws, in order |
| --- | --- |
| 0 Snow bound | 1 (days lost) |
| 1 Snakebite | 1 (victim), only when warm or hotter |
| 3 Illness | 2: disease, victim |
| 4 Gravesite, 5 Indians help, 11 Wild fruit | none |
| 6 Severe storm | 1 (days lost), unless the weather is cool or warm |
| 7 Fog or hail | fog: 1 (delay or not), then 1 (days lost) if delayed; hail: none |
| 8 Breakdown or injury | 1 (part breaks?). If so: 1 (which part), then 1 (repair), drawn whether or not the player tries. If not: 1 (injury or ox?); for an injury, 1 (victim) then 1 (arm or leg) |
| 9 Lose trail | 1 (which message), 1 (days lost) |
| 10 Rough or impassible | 1 (which); if impassible, 1 (days lost) |
| 12 Fire, lost member, stray ox | 1 (which). Fire: for each of 5 goods 1 draw, plus 1 for the amount when a loss occurs; then 1 for food, plus 1 for the amount. Lost member: 1 (who), 1 (days). Stray ox: 1 (days) |
| 13 Abandoned wagon or thief | 1 (which). Thief: 1 (item), then 1 (amount) if any is held. Wagon: for each of 5 goods 1 draw, plus 1 for the amount when found |
| 14 Water and grass | 1 (bad water?); if not, 1 (little water or grass) |

### G.5 Rivers

**Table G5.** Random draws at river crossings, by step.

| Step | Draws |
| --- | --- |
| Ford, muddy bottom | 1 |
| Ford, rough bottom | 1; if the wagon tips, 1 (loss chance) then the goods-loss loop |
| Ford, 3 ft or more | goods-loss loop, then 1 per ox, then 1 per person other than the leader |
| Caulk and float | 1 (tips?), drawn even in shallow water; if it tips, the goods-loss loop, then 1 per person |
| Ferry | 1 (days to wait) when the offer is made; after boarding 1 (breaks loose?); if so the goods-loss loop, 1 per person, 1 per ox |
| Indian guide | 1 (sets of clothing asked) when the offer is made, then as for the method the guide chooses |
| Wait | a stopped day |
| Goods-loss loop (line 50205) | for each of the 6 goods, 1 draw, plus 1 for the amount when a loss occurs |
| Crossing animation (`CROSS.LIB`) | 106 draws for the first half. Then 122 for a successful crossing, none for a failed float or ferry, and 22 single draws each followed by 2 more for a failed ford |

The crossing animation uses `RND` to place its water marks. These draws change nothing in the game state, but they advance the generator, so a rebuild must make them.

### G.6 Other activities

**Table G6.** Random draws in other activities.

| Activity | Draws |
| --- | --- |
| Trade | 4: good wanted, good offered, exchange ratio, refusal test. Then 1 more ("He" or "She") if the player holds the goods wanted |
| Talk, buy, check supplies, map, change pace or rations | none |
| Hunt | none: the routine uses its own generator, seeded from the Applesoft seed bytes and the keyboard counter, and never writes the Applesoft seed; then a stopped day |
| Rest | a stopped day for each day |
| Raft, each pass | 2 (one per rock slot, drawn even when the slot is full); 2 more for each new rock (type, then position) |
| Raft, collision or missed landing | the same loss loops as at rivers |

The loop over oxen at rivers runs `FOR L = 1 TO X` with `X` the ox count, which may end in .5, so 5.5 oxen give 5 draws.

## Appendix H: Reference traces and remaining gaps

No reference traces exist yet. A trace is a day-by-day log of the game's variables recorded from the original running in an emulator, for a known seed and a fixed list of player inputs. It is the only way to test a rebuild for parity, and it should be added to this appendix once the original has been run under emulation (section 12.6 of the paper).

A useful trace records, for each day: the date, `D`, `M`, `H`, `FS`, `H0`, `HR`, `W`, `TM`, `PP`, `AR`, `AS`, `PF`, the inventory `I(2)` to `I(8)`, `MY`, `H1()`, `H2()`, any event fired, and the five seed bytes at addresses C9 to CD (hexadecimal). The seed bytes make a missing or extra draw visible on the day it happens.

Besides the source code itself, which is not reproduced because it remains under copyright, three things needed for a complete rebuild are not in the paper or these appendices.

**Table H1.** Remaining gaps, their consequences and what would close them.

| Gap | Consequence | What would close it |
| --- | --- | --- |
| The hunting routine `& HUNT` | arguments, animal types, weights, session length and random numbers are now known (section 11.1 of the paper); animal movement, hit testing and species pictures are not | further disassembly of the movement code and decoding of the animal pictures |
| Graphics, pictures and sound | the files are listed in E.6 but their formats were not analysed | decoding the packed-picture and image-set formats, or new artwork |
| The other `&` routines | Appendix F gives argument lists and behaviour read from the disassembly; data formats and the river-floating routines are not decoded | disassembly |

With the paper, Appendices D to G and the game's own source code, obtained as described in section 1.3 of the paper, a developer can rebuild every rule, table, message and decision of the game except hunting. Parity still requires running the original ROM routines, as section 12 of the paper explains.
