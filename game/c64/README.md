# The Oregon Trail for the Commodore 64

The third implementation of the game: a port in C for the 6502, built with
[cc65](https://cc65.github.io/), delivered here **only as a disk image**. The source code
is not published. It was written and tested with the assistance of an AI model (Anthropic
Claude Sonnet 5.5; see the paper, section 1.3). Its place in the paper is section 12.9.

## Play it

You need the [VICE](https://vice-emu.sourceforge.io/) emulator (the `x64sc` program):

```
x64sc -autostart oregon_trail.d64
```

**Speed.** The pictures are read from the disk while you play. With true drive emulation
that is slow. Press Alt+W for warp mode while a picture loads, or switch off "True drive
emulation" (or switch on "Virtual device traps") in the settings.

The disk holds 104 files: `OREGON` (the game), `OREGON.1` to `OREGON.6` (parts loaded when
needed), `TALK0` to `TALK16` (the dialogue of the 17 landmarks) and 80 picture files.
Everything fits on one disk; there is no disk flip at Fort Laramie. 20 bytes of the
program's memory are free.

## How it differs from the Apple II game

- The rules, the order of the random draws and the original's bugs follow the Python
  rebuild and the paper (`../python/`, sections 2 to 11 and Appendix F). Bugs of the
  original are kept.
- **No sound.** The raft at The Dalles is simplified (three rapids with the original's
  loss rules). Hunting is the text version of the Python rebuild (no moving animals).
- The text is drawn over the pictures, and shows in capital letters (the C64 character set).
- The Top Ten and the graves are kept in memory for the session; nothing is written to the disk.
- The dialogue is the replacement dialogue shipped with the Python and TypeScript versions
  (`../python/data/dialogue.md`), not MECC's text. The pictures are those of the TypeScript
  version, converted for the C64; the travel scene is drawn anew.
- **Arithmetic: no floating point.** The disk keeps distances, health, rain and the like in
  whole thousandths (money in cents) and uses its own random number generator, so it does
  not repeat the Apple II's five-byte numbers. Section 12.9 measures how close this comes.

## How close is it to the Apple II game?

Section 12.9 of the paper compares the rules used on the disk with the original's
arithmetic, over every seed of the Apple II's random generator, with the same start and
the same fixed player as section 12.7. In short (62,880 games):

| | |
| --- | --- |
| Identical every day (seed bytes exact, other columns within tolerances) | 98.11% |
| Same ending (arrived in Oregon / all died) | 99.63% |
| Same final score | 99.35% |
| Mean days to the end, original's arithmetic and the disk's | 165.33 and 165.33 |

Most of the games that differ (999 of 1,191) differ at one place, the day on which the wagon
is judged to have arrived (1.1 × the day's miles against the distance left), where a tie
falls on the stored error of a five-byte number.

`results/` has the numbers: `diskrep_summary.txt`, `diskrep_byday.csv` and
`diskrep_games.csv.gz` (one row per game).

**What these results are, and are not.** They were obtained by compiling the disk's game
logic for a PC and running it, not on a C64 or in VICE. The reference is a C transcription
of the ROM's arithmetic that agreed with the original game's traces on all 65,536 seeds.
The test did not cover the screens, the pictures or the keys.
