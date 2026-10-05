# The paper

*The Oregon Trail on the Apple II (1985): An Analysis of Source, Data and Algorithms
for Replication in Other Languages* — by G. Paganelli.

Read in this order:

| | |
| --- | --- |
| [`01-paper.md`](01-paper.md) | The paper: fourteen sections, every claim carrying the BASIC line number that supports it. |
| [`01-paper.docx`](01-paper.docx) | The same paper as a Word document. |
| [`02-appendix-d-dialogue.md`](02-appendix-d-dialogue.md) | Appendix D — the 51 dialogue records, as a research extract. |
| [`03-appendices-e-to-h.md`](03-appendices-e-to-h.md) | Appendices E–H — the data tables decoded from `VAR.BIN`, the `&` command reference, the order of every random-number draw, and the remaining gaps. |
| [`04-review.md`](04-review.md) | An independent peer review, verified against the source and by executing the ROM. Its findings corrected two statements in the paper itself (§8.1 and §12.2). |

Appendices **X**, **Y** and **Z** — the release 1.4 source listings, the on-screen
text, and the machine-code listings — are MECC's and Apple II emulator material and
are not redistributed here. The paper cites them by line number so that a reader
holding the disk can check every claim.

The Python translation in `../oregon/` exists to test the paper's claims. Its own
findings are in [`../FINDINGS.md`](../FINDINGS.md), and what it approximates or
leaves undone is in [`../GAPS.md`](../GAPS.md).
