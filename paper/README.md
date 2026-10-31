# The paper

*The Oregon Trail on the Apple II (1985): An Analysis of Source, Data and Algorithms
for Replication in Other Languages* — by G. Paganelli.

Read in this order:

| | |
| --- | --- |
| [`01-paper.md`](01-paper.md) | The paper: fourteen sections, an experiment over every seed (12.7) and a test of a whole-number port for the Commodore 64 (12.9), every claim carrying the BASIC line number that supports it. |
| [`02-appendices-d-to-g.md`](02-appendices-d-to-g.md) | Appendices D–G — the data tables decoded from `VAR.BIN`, the `&` command reference, the order of every random-number draw, and the remaining gaps. |
| [`figures/`](figures/) | The five figures of section 12.7, which compare the ROM's arithmetic with rounded floats and plain floats, and `experiment-figures.xlsx` with the same charts and their data; the two figures of section 12.9 (the Commodore 64 disk's rules against the ROM) and `disk-rules-figures.xlsx` with their data and Tables 31 to 33. |

The Python rebuild in `../game/python/` exists to test the paper's claims. What it reproduces,
what it does not, and how the experiment of section 12.7 was run are in
[`../game/python/README.md`](../game/python/README.md).

The Commodore 64 disk of section 12.9 is in [`../game/c64/`](../game/c64/).
