# The Oregon Trail on the Apple II (1985): An Analysis of Source, Data and Algorithms for Replication in Other Languages

By Giacomo Paganelli - rift-demote-fence@duck.com

**This repository is primarily a research paper on *The Oregon Trail*
for the Apple II**, specifically version 1.4, the 1985 MECC release by R. Philip Bouchard (design), John Krenz (lead programmer), Charolyn Kapplinger (art), with Shirley Keran, Bob Granvin, Roger Shimada and Steve Splinter.

The question the paper asks is simple: **can this game be replicated based on this paper and get the same behaviour, or even achieve algorithmic parity?**

The paper answers it by documenting the actual BASIC code, the machine code, variables, algorithms, tables, and various data. It also finds the places where the documented behaviour and the program behaviour disagree.

---
## The paper

| Files                                                            | Contents                                                                                                                                                                                                           |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [`paper/01-paper.md`](paper/01-paper.md)                         | The paper. Fourteen sections covering set-up, the daily cycle, health, weather, the fifteen random events, rivers, forts, trading, endings, the two arcade games, and what the Applesoft ROM does to every number. |
| [`paper/02-appendices-d-to-g.md`](paper/02-appendices-d-to-g.md) | Appendices D–G — the data tables decoded from `VAR.BIN`, the `&` command reference, the exact order of the random-number draws, and what is still missing.                                                         |

Where the Python rebuild and the paper disagree, the BASIC listing decides; none of
the paper's text, dialogue or game data is reproduced here beyond what the analysis
needs to cite.

## Replicas

| Folder                                 | Contents                                                                                                                                                                       |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [`game/python/`](game/python/)         | Everything about the Python rebuild of the game: the `oregon` package, its tests and tools, the experiment script with a small sample of its results.                          |
| [`game/typescript/`](game/typescript/) | The second implementation, in TypeScript: the whole game for a browser, with Applesoft's arithmetic transcribed from the ROM, checked seed by seed against the Python rebuild. |

## Funny facts

| Files           | Contents                                                                                                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [`20funnyfacts.md`](20funnyfacts.md) | 20 Oregon Trail curiosities I discovered while writing the paper and running the experiments!                                                                                                                                                   |

---

## History

How my work went, month by month.

- **March 2025** — Extracted the Applesoft BASIC files from version 1.4 and converted
  them into `.txt`; analysis of the Applesoft BASIC files.
- **April 2025** — Modified the Applesoft BASIC files to extract various data; hacked
  the BASIC files to accelerate the game and observe it under different conditions,
  running them in the AppleWin emulator.
- **April 2025** — Used Google Gemini 2.5 Pro to attempt to determine the purpose of
  the variables, and of `PEEK` and `POKE`.
- **April 2025** — First attempt to code a simple Python version of the game without
  AI.
- **April 2025** — Second attempt to code a simple Python version of the game with
  AI.
- **June 2025** — First draft version of the paper, written by hand with the help of
  Google Gemini 2.5 Pro.
- **September 2025** — Used Google Gemini 2.5 Pro to analyse the BASIC code and the
  variables in depth, with the aid of the lead designer's book.
- **February 2026** — Second draft version of the paper, mostly corrected by Google
  Gemini 3.1 Pro, with all the findings gained so far.
- **October 2026** — First official version of the paper, reviewed and corrected by
  Claude Opus 5.5 (High), which includes an analysis of the assembly code by Claude.
- **October 2026** — First attempt to create a Python-based version of the game, based
  on the paper and the related artefacts, using Space Bunny Alpha.
- **October 2026** — Independent review of the paper and the Python rebuild against the
  BASIC listings and the machine code, with corrections to both, by Claude Opus 5.5 (High).
- **October 2026** — Second full review of the code, the findings and the paper, with
  corrections to all three, by Claude Opus 5.5 (High); the experiment over all 65,536
  seeds (§12.7) was run on the rebuild as reviewed.
- **October 2026** — A Python transcription of the ROM's arithmetic, tested against the
  ROM, and a measurement of how close a port with simpler arithmetic comes to the
  ROM's (§12.6, §12.8), by Claude Opus 5.5 (High).
- **October 2026** — Day-by-day comparison of the rebuild with the original game running
  in the LinApple emulator, for two games, from copies of the disk images changed to play
  themselves and print each day's values; two departures of the rebuild found and
  corrected, and the experiment over all 65,536 seeds run again (§12.6, Appendix G),
  with Claude Opus 5.5 (High).
- **October 2026** — The rebuild's first, approximate Python model of the arithmetic
  removed from the code and the paper; the experiment reports the ROM against the
  transcription, rounded floats and plain floats (§12.7, §12.8), with Claude Opus 5.5
  (High).
- **October 2026** — Published a Typescript version of the game using Claude Sonnet 5.5, 
  which confirm the paper's thesis and accuracy, and runs on a web browser.
- October 2026 — Update the README and reorganised the repo.

---
## What is not in this repository

- **The Apple IIe ROM image**
- The BASIC listings
- The dialogues
- The artworks
- The machine code listings
