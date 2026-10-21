# Appendices D to G: material for rebuilding the game

The main paper gives the rules. These appendices give what a rebuild needs beyond the rules, apart from the source code itself: the data tables, the machine-language interface, and the order of random draws.

| Appendix | Content | Where |
| --- | --- | --- |
| D | Data tables not already in the main paper | below |
| E | Reference for the `&` commands | below |
| F | Sequence of random draws | below |
| G | Reference traces | two games, and how they were recorded; see below |

## Appendix D: Data tables

These are the contents of the saved variable table `VAR.BIN` that the main paper does not already list. The landmark and segment tables are in section 4.1 of the paper, the climate codes in 6.2, the illness names in 5.3, the river data in 9.3 and the original top ten in 10.4. Data held in DATA lines (default names, month names, scoring text, river menu text) is in the BASIC source, which is not reproduced in this paper.

### D.1 Simple variables at start-up

**Table D1.** Values of the simple variables at start-up.

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

The table also holds three leftover values that play does not use before setting them: `DI` 0, `L` 6 and `L1` 2.

Six string variables hold single control characters: `D$` code 4, `CC$` code 3, `CL$` code 12, `CM$` code 13 (carriage return), `CE$` code 5 and `CF$` code 6. `PN$` is "OREGON TRAIL" and `WW$` is "What is your choice? ".

Arrays that start empty or zero: `RE(0 to 14)`, `T$(0 to 10)`, `I(0 to 8)`, `H1(0 to 4)`, `H2(0 to 4)`, `N$(0 to 4)`.

### D.2 Text arrays

**Table D2.** Text arrays and their contents in index order.

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

### D.3 Goods table `S$(0 to 6, 0 to 3)`

Used by forts, trading and the broken-part messages.

**Table D3.** The goods table: name, base price, unit and plural ending of each good.

| Index | Name | Base price | Unit | Plural ending |
| --- | --- | --- | --- | --- |
| 0 | Oxen | 20 | ox | en |
| 1 | Clothing | 10 | set | s |
| 2 | Ammunition | 2.00 | box | es |
| 3 | Wagon wheels | 10 | wheel | s |
| 4 | Wagon axles | 10 | axle | s |
| 5 | Wagon tongues | 10 | tongue | s |
| 6 | Food | 0.20 | pound | s |

### D.4 Climate strings `WC$(0 to 5)`

The six strings exactly as stored, 24 characters each. Section 6.2 of the paper gives their character codes.

```
0: ;+?,I8V?_NiNnElFdHY<K1@-
1: 5#:#B(O3Y<c?i9g4].Q(C#9#
2: 5#9#>'H.R3\+e(c$X'M'?%8#
3: 1#6%>*I5R7[+c&a#W)L,=&3$
4: <-B+H+P*X*_'h!f!]$R(F+>,
5: DWIGLBQ5W3[.`#`(]/T?LTG^
```

### D.5 Screen position tables

These do not affect the simulation. A rebuild that redraws the map and travel screen needs them.

`MP%(landmark, 0 to 1)`: map x and y of each landmark, used by `MAP.LIB` to draw the route travelled.

**Table D4.** Map coordinates of each landmark.

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

**Table D5.** Picture number and horizontal offset of the approaching landmark on the travel screen.

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

### D.6 Data files on disk

**Table D6.** Data files on disk and their formats.

| File | Format |
| --- | --- |
| `HISCORE.SEQ` | thirty text fields ended by carriage returns: name, points, rating for each of ten entries |
| `TOMB.SEQ` | two records 49 bytes apart, each of four fields ended by carriage returns: segment code, miles remaining, name, epitaph. An empty record has segment code 0 |
| `OREGON1.SEQ`, `OREGON2.SEQ` | dialogue records, three per landmark; see section 9.1 of the paper (the text is not reproduced) |
| `VAR.BIN`, `PT.BIN` | saved variable table (4,516 bytes, loaded at 39170) and its 12 bytes of interpreter pointers (loaded at 105) |
| `L0.PCK` to `L17.PCK`, `M0.PCK`, `TS.PCK`, `RIVER.PCK` | packed pictures loaded by `& DUN`: landmark views, the map, the tombstone, the Columbia River |
| Files ending `.IMA`, `MS0.BIN` to `MS17.BIN`, `TS.BIN`, `DALLESUTIL.OBJ` | image sets, binary data loaded per landmark, and machine code; not analysed |

## Appendix E: The machine-language (&) commands

The BASIC programs call a machine-language package through the Applesoft ampersand hook. The package is not a file on the disk: it is loaded from the system tracks of side 1 at boot, to address 6000 (hexadecimal), and its hunting part lives in language-card RAM. This appendix is based on a disassembly of that package from the release 1.4 disk. The package has 45 commands: its name table (8FB0 to 9054) and its handler address table (9055 to 90AE) hold 45 entries each. Tables E1 to E3 list 46 names, which differ from the package's in three places that are explained in E.4. A table of command names is followed by a table of handler addresses, and the dispatcher skips one optional comma after the name before it jumps to the handler. Each handler was disassembled from its entry point and its argument list read from the calls it makes to the Applesoft expression evaluators (numeric, string, variable pointer, comma check). The disassembly and its interpretation were carried out with the AI model Claude Opus 5.5 (High), and, apart from the hunting module (E.2 and section 11.1 of the paper), have not been checked by running the code in an emulator. Argument lists follow from those calls; descriptions of what a routine does with its arguments are a reading of the code and should be treated as such. In the tables, square brackets mark an argument that may be left out, and a default is given where the code supplies one.

### E.1 Screen, window and text commands

**Table E1.** Screen, window and text commands, with their arguments and behaviour.

| Command | Arguments (from the code) | Behaviour |
| --- | --- | --- |
| BOX | \[x1, y1 \[, x2, y2 \[, c\]\]\] | With no arguments, clears the current window. With arguments, fills a rectangle on the hi-res screen; the coordinates are relative to the current window. A second corner that is left out is taken from the width and height of the current window. The colour c follows HCOLOR: the code keeps its two low bits and sets the palette bit for 4 or more, without checking the range. Left out, it is the background colour of the current text mode, black after NORMAL and white after INVERSE. The listings use it to clear areas, to draw bars and to draw the filled boxes behind headings. |
| DFT | n, address | Registers the data table stored at address in slot n. The listings use only two slots: 7 for the picture library drawn by IMAGE, and 15 for tune data. The command is never used to set the text font. The game's text is drawn with a proportional font built into the package itself, with capitals 7 pixels tall and strokes two pixels wide. |
| AFT | \[n\] | Selects slot n (0 to 6; any other value is an error; 0 if left out) as the active character set for text. Never used in the listings. |
| PARSE / NOPARSE | none | Clear and set a flag in the text driver (bit 7 of a byte that HOOK clears), which the output hook reads at 6134 (hexadecimal). With the flag clear, as after HOOK, printed text goes through a word buffer and wraps at the edge of the window; with it set, each character is drawn as it arrives. Control codes are handled before the flag is tested, so the flag does not switch their interpretation. Never used in the listings. |
| GCP | \[xvar\] \[, yvar\] | Returns the text cursor position: x (0 to 279) into the first variable and y into the second. Either may be left out, so `& GCP,,Y` returns only y. |
| VSP, HSP, TSP | \[n \[, slot\]\] | Set three spacings of the text: VSP the space between lines, HSP the space between letters, and TSP extra space added above each line (it enters the line advance and the top of each glyph). The value n is a byte; left out, it is 1 for VSP, 2 for HSP and 0 for TSP. It is stored in the header of the character set in the given slot, or of the active character set if no slot is given. TSP is never used in the listings. |
| CEL | none | Clears from the cursor to the right edge of the window on the current line; positions are relative to the window. |
| CEW | none | Clears from the cursor to the end of the window: the rest of the current line and every line below it. |
| SPACE | \[n\] | With no argument, selects window 0, prints "Press SPACE BAR to continue" on its bottom line, waits, and then restores the previous window, cursor and indent. With an argument of 1 or more, the prompt is printed in the current window instead. Return or the space bar ends the wait. The listings use only the form with no argument, in the subroutine at line 30000, which many routines call when they wait. |
| CO | \[x\] \[, y\] | Moves the text cursor to x and y, relative to the current window; x is a 16-bit value and is not checked against 279, and y is a byte. A coordinate that is left out keeps its current value, so `& CO,,110` changes only y. With no arguments the cursor goes to the top left of the window. |
| HT | n | Moves the cursor to the left edge of the window, then n tab steps to the right; a step is the character width given in the character set's header plus the horizontal spacing set by HSP. Never used in the listings. |
| VT | n | Moves the cursor to line n of the window, counting from 0. Never used in the listings. |
| DFW | n AT x, y, w, h | Defines window n (1 to 7; window 0 cannot be redefined) with origin x (0 to 279) and y (0 to 191), width w (a 16-bit value) and height h (a byte). |
| WIND | \[n\] | Selects window n (0 to 7; 0 if left out) as the output window. |
| IN | \[n\] | After sending a control code to the driver, sets the indent of printed text to n (0 if left out). Any value whose high byte is 0 or 255 is accepted and its low byte is read as a signed number, so 200 becomes -56; the value is stored as a sign and a magnitude, and -128 becomes 0. A positive indent applies only to the first line printed after each control code, so wrapped lines are not indented. A negative value, as in `& IN, - 16` before the bulleted lists, gives a hanging indent. |
| SHIGH / CHIGH | none | Set and clear a highlight flag (bit 7 of a byte that HOOK clears). By their names they draw later text highlighted or normal; the flag is also added to the default colour of BOX. Never used in the listings. |
| HOOK | none | Routes PRINT output and keyboard input through the hi-res text driver. It resets the text state (character set 0, indent 0, highlight off), selects hi-res page 1 unless page 2 is already selected, and selects window 0. |
| UNHOOK | none | Gives the screen output and the keyboard back to the system: it prints a carriage return and calls the monitor routines that reset the output and input vectors. It does not switch the display to the text screen. Never used in the listings. |
| INP | \[length\], \[set\], \[flag\], string variable | Line input of at most length characters (16 if left out), accepting only the characters in set (any printable character if left out); the result goes to the string variable. The set is a list of single characters and ranges: a dash followed by two characters stands for every character from the first to the second. The set written as dash, 1, 4 therefore allows the digits 1 to 4. The sets used for names allow A to Z, a to z, the space, the apostrophe, the full stop and the dash; the set used for the epitaph adds the digits and the comma. The driver skips the two characters after a dash when it scans the set for the three characters it treats specially (code 1, escape and the question mark), which agrees with this reading of a dash. The flag (1 if left out) is the least number of characters that must be typed before Return is accepted (comparison at 7237), so 0 allows an empty answer: the leader's name is asked with 1 and the other names with 0 (`MENU` 6015 and 6021). A length of 0 takes a single keystroke with no Return. This is the input routine used for every prompt in the game. |

### E.2 Graphics and sound commands

**Table E2.** Graphics and sound commands, with their arguments and behaviour.

| Command | Arguments (from the code) | Behaviour |
| --- | --- | --- |
| DUN | "file" \[AT address, n\] | Reads a packed picture file from the disk and unpacks it straight onto the current hi-res page, column by column (192 rows, then the next column), after skipping the first 4 bytes of the file. The address is a disk buffer and n the number of 256-byte sectors read into it at a time, so 16 gives a buffer of 4 kilobytes; without AT, a default buffer and one sector are used. n must not be zero. The decoder reads control bytes whose top two bits give the kind of run: 00, a literal run of the bytes that follow; 01, one byte repeated; 10, a pair of bytes repeated in turn; 11, the end of the picture. The low six bits, plus one, give the length of a literal run and the number of repeats in the other two. This is a reading of the loader and was not tested on a file. |
| UIM | n, address \[, var\] | Unpacks image n of the picture library registered in slot 7 by DFT and writes it, with a 6-byte header, at address. The optional variable receives the length written, which the listings add to the address to find where the next image can go. |
| IMAGE | n, x, y | Draws image n of the picture library registered in slot 7 by DFT at x, y. |
| PUT | x, y, address | Draws the bitmap block stored at address. |
| TAKE | x1, y1, x2, y2, address | Copies a screen rectangle into memory at address (the inverse of PUT). |
| DPC | x, y, var | Returns into the variable the colour code, 0 to 3, of the pair of pixels at (x AND 254, y) on the current hi-res page; x must be below 280 and y below 192. It is used once in the listings (statement 312 of `OREGON TRAIL`), after an image is drawn. |
| PT | \[n \[, flag\]\] | Plays tune n from the tune data registered in slot 15 by DFT. With no flag, or flag 0, the tune plays to its end; with a non-zero flag, a key press stops it. The listings use `& PT,1` and `& PT,1,1`. |
| PN | \[n\] | Plays a single note of the tune data, where PT plays notes in a loop until the tune ends; n selects the entry in the same way as in PT. Never used in the listings. |
| HUNT | n (16-bit), five one-byte values, var, var | Runs the hunting module. The handler copies the first six arguments into a block of nine bytes, calls the module at E003 (hexadecimal), and returns two results: the first variable receives the 16-bit word at offset 7 of the block, and the second receives the first argument as the module has left it. See section 11.1. The module reads offsets 0 to 6 of the block (bullets, three true-or-false values, the halving value and the climate zone) and writes offsets 0 and 1 (bullets left) and 7 and 8 (live weight shot). Run under an emulator, the routine behaved as section 11.1 describes. |
| IHUNT | none | Switches language-card bank 2 on, calls E000 in the hunting module, and switches the card back to ROM. The module's entry at E000 jumps to F621, which is a return instruction, so the command does nothing. No program on either side of the disk calls it; all the set-up of a hunt is done on each call of HUNT, at E547. |

### E.3 Disk and program commands

**Table E3.** Disk and program commands, with their arguments and behaviour.

| Command | Arguments (from the code) | Behaviour |
| --- | --- | --- |
| RFL | "file" \[AT address\] | Reads a file into memory, at address if AT is given. A BASIC-type file is relocated to the program area, its variables are cleared (the ROM's CLEAR routine), and it is left unstarted. |
| RNH | \["file" \[AT address\]\] | Loads and starts a file, reading the name and the optional AT address as RFL does. A BASIC program runs from its first line, and a binary file is called at its load address. With no file name, the binary loaded last is called again; every use in the listings gives a name. |
| APP | "file" | Appends a BASIC file at the end of the program in memory. This is how the library modules are chained. |
| DBL | from \[, to\] | Deletes the program lines in the given range, freeing space before the next APP. If the second number is left out (or is 0), only the line `from` is deleted; every use in the listings gives both. |
| OPEN | name \[, var\] | Opens a file; the optional variable receives a byte returned by the open routine. No use in the listings gives the variable. |
| CLOSE | none | Closes the open file. |
| TREED | delimiter string, string variable \[, var\] | Reads text from the open file into the string variable, up to the first of the characters in the delimiter string (at most 240 characters). The optional variable receives the position in the delimiter string of the character that ended the item, counting from 1, or 0 if the limit was reached. At the end of the file the item read so far is returned with 255, and an empty read is an error. Used for the dialogue records (section 9.1 of the paper). |
| TWRITE | string | Writes a string to the open file. |
| TPTR | n | Sets the file position (a 16-bit value). The listings calculate it as a record number multiplied by the record length. |
| GTP | var | Returns the file position (a 16-bit value). Never used in the listings. |
| CDN | string variable | Reads a 30-character label, the name of the first entry in the disk's catalogue, into the string variable. The programs take the disk name from characters 2 to 13 and the side number from character 20, and repeat the call until the expected side is in the drive. |
| SET | n; or slot, drive \[, volume\] | With one argument, selects one of two stored sets of disk values for later disk commands: `& SET,1` or `& SET,2`, which the programs write as 1 + S, where S is the disk side. `& SET,0` changes nothing, and any other single value is an error. With two or three arguments it stores the values directly, which appear to be a slot (1 to 7), a drive (1 or 2) and a volume number (0 if left out). |
| CST | address | Stores an address (a 16-bit value) for the package's own use; the purpose was not established. The listings call it 13 times, with the constants 14848 and 50800 or the variable `ST`, next to calls that load or draw pictures. |
| QFH | none | Takes no argument. It runs a routine that walks the table of variables and the strings they point to, and so appears to be a replacement for Applesoft's string garbage collection; this was not traced further. The programs call it 15 times. |

### E.4 Commands not in this package, and commands never used

PUTP and DPB are used only by the river-floating program, which loads its own machine-language file for them; that file was not disassembled. The doubled ampersand form, also used only there, is handled by this package: it restores the ampersand vector that the package replaced when it was installed (60BE). The same holds for the USR calls. Ten commands in the package are never called by a program on either side of the disk: AFT, PARSE, NOPARSE, TSP, SHIGH, CHIGH, UNHOOK, PN, GTP and IHUNT. The image-library and tune data formats were not decoded, and the packed picture format was read from its loader only (DUN in E.2): a rebuild must supply its own graphics and sound, or run the original routines.

**HT, VT and IHUNT.** Table E1 lists HT and VT, but neither name is in the package's name table, and the handler address table has no entry for either, so they cannot be called as `&` commands. Their rows describe behaviour that the first reading of the code attributed to them; it has not been tied to a handler, and no program uses either, so a rebuild can ignore both. IHUNT is in the package's tables and is in Table E2. With HT and VT removed and IHUNT added, the 46 names of E.1 to E.3 become the package's 45.

None of the commands in E.1 to E.3 calls the Applesoft random number routine or changes its seed, except that the hunting module reads the seed bytes to start its own generator (section 11.1). They therefore do not affect the sequence of random events in the BASIC code.

## Appendix F: Sequence of random draws

A rebuild matches the original only if it calls `RND` the same number of times in the same order. This appendix lists every draw made by the BASIC code. Two rules of the interpreter matter throughout.

- Applesoft evaluates both sides of `AND` and `OR`. In `IF X AND RND (1) < V`, the draw happens even when `X` is false.
- A draw multiplied by zero still happens, as in `RND (1) * 12 * ( PEEK (902) < 4)`.

Two further rules decide whether a draw happens at all (section 2.5 of the paper). When the condition of an `IF` is false, every statement after `THEN` on that line is skipped, including any draw. And the body of a `FOR` loop always runs at least once, so a loop that contains a draw makes one even when its limit is below its starting value.

The hunting routine was disassembled, and a scan of its code finds no call to the Applesoft random number routine (F.6). Draws inside the other machine-language routines are not known, but none is expected, since those routines handle display, input and files.

### F.1 Setup

**Table F1.** Random draws during setup, by step and program line.

| Step | Draws | Line |
| --- | --- | --- |
| Each completed main-menu choice | reseed with the negative keyboard counter | `MENU` 1015 |
| Shuffle default names | 10 | `MENU` 6000 |
| Store | none |  |
| Initial snow | 1 | 29000 |
| Initial rain | 1 | 29004 |

### F.2 Each landmark

**Table F2.** Random draws at each landmark.

| Step | Draws | Line |
| --- | --- | --- |
| Arrival, including the start at Independence | 1 (first dialogue) | 1000 |

### F.3 Each day

**Table F3.** Random draws on each day, in order, with program lines.

| Order | Step | Draws | Line |
| --- | --- | --- | --- |
| 1 | Event loop, travelling days only | 1 per event tested, 15 if the loop runs to the end, plus the event's own draws (F.4) | 3180 |
| 2 | Weather change test | 1 | 3205 |
| 3 | If the weather changes | 2: temperature, then rain flag | 3205 |
| 4 | If the rain flag is set | 1: heavy or light | 3206 |
| 5 | If health exceeds 139 and not at a river | 2: disease, then victim | 3235, 10300, 11500 |

A stopped day (resting, a delay, waiting at a river) omits step 1. Days lost to an event run as stopped days nested inside that event, before the event loop continues.

### F.4 Inside each event

**Table F4.** Random draws inside each event, in order.

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

### F.5 Rivers

**Table F5.** Random draws at river crossings, by step.

| Step | Draws |
| --- | --- |
| Ford under 2.5 ft, smooth bottom | none (`ON RB GOSUB` with `RB` = 0) |
| Ford under 2.5 ft, muddy bottom | 1; if the wagon sticks, a stopped day |
| Ford under 2.5 ft, rough bottom | 1; if the wagon tips, 1 (loss chance) then the goods-loss loop |
| Ford, 2.5 to under 3 ft | a stopped day (supplies wet) |
| Ford, 3 ft or more | goods-loss loop, then 1 per ox, then the person loop |
| Caulk and float | a stopped day, then 1 (tips?), drawn even when the water is too shallow for it to tip; if it tips, the goods-loss loop, then the person loop |
| Ferry | 1 (days to wait) when the offer is made; after boarding, the days of waiting as stopped days, then 1 (breaks loose?); if so the goods-loss loop, the person loop, then 1 per ox |
| Indian guide | 1 (sets of clothing asked) when the offer is made, then as for the method the guide chooses |
| Wait | a stopped day |
| Goods-loss loop (line 50205) | for each of the 6 goods, 1 draw, plus 1 for the amount when a loss occurs |
| Person loop (line 50175) | 1 per person other than the leader; 1 for the leader alone when no one else is alive |
| Crossing animation (`CROSS.LIB`) | 106 draws for the first half. Then 122 for a clean crossing (one with no loss lines), none for a failed float or ferry, and 66 for a failed ford (22 groups of three: one draw, then two more) |

The crossing animation uses `RND` to place its water marks. These draws change nothing in the game state, but they advance the generator, so a rebuild must make them.

### F.6 Other activities

**Table F6.** Random draws in other activities.

| Activity | Draws |
| --- | --- |
| Trade | 4: good wanted, good offered, exchange ratio, refusal test. Then 1 more ("He" or "She") if the offer is not refused (line 50027) and the player holds the goods wanted. Then a stopped day, whatever the outcome (line 4900 sets `SD = 1`) |
| Talk, buy, check supplies, map, change pace or rations | none |
| Hunt | none: the routine uses its own generator, seeded from the Applesoft seed bytes and the keyboard counter, and never writes the Applesoft seed; then a stopped day |
| Rest | a stopped day for each day |
| Raft, each pass | 2 (one per rock slot, drawn even when the slot is full); 2 more for each new rock (type, then position) |
| Raft, collision | the person loop, then 1 per ox, then the goods-loss loop (`FLOAT` 700 and 710, in that order, which no river method uses) |
| Raft, missed landing | the goods-loss loop only (`FLOAT` 950) |

The loop over oxen at rivers runs `FOR L = 1 TO X` with `X` the ox count, which may end in .5, so 5.5 oxen give 5 draws. Half an ox gives 1 draw, because the body of a FOR loop always runs once.

## Appendix G: Reference traces and remaining gaps

The constants of the random number generator and its first fifteen values for a known seed were recorded from the ROM (section 12.6 of the paper), which gives a rebuild a first check on its generator. A trace tests the game itself. It is a day-by-day log of the game's variables recorded from the original running in an emulator, for a known seed and a fixed list of player inputs, and it is the only way to test a rebuild for parity. Two traces were recorded, for seeds 1,234 and 10,190 of the preset start of section 12.7 of the paper, and are described at the end of this section.

A useful trace records, for each day: the date, `D`, `M`, `H`, `FS`, `H0`, `HR`, `W`, `TM`, `PP`, `AR`, `AS`, `PF`, the inventory `I(2)` to `I(8)`, `MY`, `H1()`, `H2()`, any event fired, and the five seed bytes at addresses C9 to CD (hexadecimal). The seed bytes make a missing or extra draw visible on the day it happens.

The rebuild's preset start (section 12.7 of the paper) is a position the store cannot reach, and it makes the opening draws of lines 29000 and 29004 twice. A trace for comparison with that start must write the same position into memory and make two extra draws after reseeding, before the journey begins.

**Emulators for a trace.** The emulator needs a Disk II drive and 64 KB of memory: the game loads its programs, libraries and `&` package from disk, and the hunting routine runs from language-card RAM (section 11.1 of the paper). An Apple II Plus with a 16 KB language card serves as well as an Apple IIe. The game's start-up code identifies the model and the memory fitted and accepts the II Plus, and the `&` package converts lower-case letters to capitals on that machine, which cannot display them. A published description of release 1.4 lists a 64K Apple II Plus among the machines it requires (4am, 2022). The arithmetic is the same on both. Between D000 and F7FF (hexadecimal), the Applesoft part of the ROM, the II Plus and IIe images differ only in the code for typed lines, `LIST`, print positioning and cassette loading and saving, in one byte after the entry jumps at E000, and in the area F775 to F7FF, which the IIe uses for its own versions of some of these routines. Every routine named in section 12 of the paper, including `RND` and the conversions to and from text, is byte-identical. With the II Plus Applesoft in place of the IIe's, `tools/exact_check.py` found no difference between the transcription and the ROM in 20,000 operand pairs, 3,528 literals and 20,000 conversions to text, and seeds 0 to 299 of the experiment of section 12.7 played exactly as under the IIe image, record for record and including the final seed bytes. A trace recorded in a 64 KB Apple II Plus emulator, such as Reinette II Plus Dot Py (Ferreira, 2023), can therefore be compared directly with the rebuild.

**The two traces.** Copies of the release 1.4 disk images were changed so that the game plays itself and logs each day, and were run in the LinApple emulator (LinApple contributors, n.d.) with a parallel printer card in slot 1, whose output the emulator writes to a text file. Only the BASIC programs were changed:

- At the first pass through the menu, the generator is reseeded with `RND (-n)` and two draws are made, the preset position of section 12.7 of the paper is written into the hand-over memory (section 2.3 of the paper), the five names are stored, and the store is skipped.
- Each question that the rebuild's player answers (section 12.7 of the paper) receives the same answer in place of the keyboard input, and the keyboard checks of the daily cycle always find no key. The river-crossing and part-repair answers follow the same rules, and at The Dalles the Barlow Toll Road is taken and paid for.
- After the date advances (line 3255), a subroutine prints the date, `D`, `M`, `H`, `FS`, `H0`, `HR`, `W`, `TM`, `PP`, `AR`, `AS`, `PF`, `I(2)` to `I(8)`, `MY`, `H1()`, `H2()` and the five seed bytes to the printer. It saves and restores the output vector at addresses 54 and 55, so the screen is unaffected. The event fired is not logged.

The disk sides were swapped by hand at Fort Laramie, where the game asks for side 2 (line 1016). The changed images are not distributed, because the programs remain under copyright; the two logs themselves are, as `game/python/tests/data/trace_10190.printer.txt` and `game/python/tests/data/trace_1234.printer.txt`, and `game/python/tests/test_reference_trace.py` replays each of them against the rebuild. The rebuild's trace (`--preset --demo --seed N --num exact`, or `--num rom`) was compared with each log, value by value, allowing half a unit in the last digit that the rebuild prints. The first comparison, of seed 1,234, agreed until 24 July 1848 and then differed in the weather and the seed bytes. It exposed two departures of the rebuild from the listing: the event chances of line 3160 were not recomputed on a stopped day, so an event that lost days inside the event loop left the remaining events with the morning's chances; and `PF` was copied to `I(8)` every day instead of only when the daily loop ends. With both corrected, every logged value of every day agreed, including the seed bytes, in both games:

**Table G1.** The two reference traces.

| Seed | Days logged | Ending |
| --- | --- | --- |
| 1,234 | 158 | the party dies on 6 September 1848, after passing Fort Walla Walla |
| 10,190 | 196 | the party reaches Oregon by the Barlow Toll Road on 14 October 1848, with a score of 2,158 |

The two games cover one start and one player. They do not include hunting, trading, purchases at forts, resting or the raft, and a trace of any of these would need other changes to the programs.

Besides the source code itself, which is not reproduced because it remains under copyright, three things needed for a complete rebuild are not in the paper or these appendices.

**Table G2.** Remaining gaps, their consequences and what would close them.

| Gap | Consequence | What would close it |
| --- | --- | --- |
| The hunting routine `& HUNT` | arguments, animal types, weights, session length, terrain, the chance of an animal appearing and random numbers are known and were checked by running the routine (section 11.1 of the paper); animal movement, hit testing and species pictures are not | further disassembly of the movement code and decoding of the animal pictures; a run that fires at animals and compares the weight returned |
| Graphics, pictures and sound | the files are listed in D.6 but their formats were not analysed; the run-length scheme of the packed pictures is read from its loader in E.2 and was not tested on a file | decoding the packed-picture and image-set formats, or new artwork |
| The other `&` routines | Appendix E gives argument lists and behaviour read from the disassembly; data formats and the river-floating routines are not decoded | disassembly |

With the paper, Appendices D to G and the game's own source code, obtained as described in section 1.3 of the paper, a developer can rebuild every rule, table, message and decision of the game except hunting. Parity also requires Applesoft's arithmetic, from the original ROM routines or a faithful transcription of them, as section 12 of the paper explains.
