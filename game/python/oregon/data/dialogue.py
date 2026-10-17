"""The 51 monologues, read from the reference document rather than copied here.

Appendix D holds the dialogue as ``OREGON1.SEQ`` and ``OREGON2.SEQ``: three
256-byte records for each of the seventeen landmarks that have any, each record a
speaker and a text separated by a carriage return. The record read is at byte offset
``(LM - S * 5) * 768 + A * 256``, where ``S`` is the disk side -- 0 for
landmarks 0 to 4, 1 for 5 to 16 -- and ``A`` is the slot.

The text is MECC's. It is loaded at run time from the appendix in ``paper/``, and
this repository does not redistribute it: the published copy of Appendix D is a
research extract, and the full dialogue is MECC's. :func:`load` raises if the
document is not there, because talking to people is part of playing the game and a
silent empty list would be worse than a clear failure.

The speaker and the text are kept exactly as the reference has them, spelling and
spacing included, because the on-screen text is part of what is being reproduced.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["Dialogue", "load", "available", "source_path", "count"]

# Where to look for the dialogue, in order: the copy beside the code, then the
# published appendix.
# ``_HERE`` is the ``game/python`` folder; the paper sits at the top of the
# repository, two levels up.
_HERE = Path(__file__).resolve().parents[2]
_REPO = _HERE.parent.parent
_CANDIDATES = (
    _REPO / "paper" / "02-appendix-d-dialogue.md",
    _HERE / "paper" / "02-appendix-d-dialogue.md",
    _REPO / "docs" / "Appendix D Dialogue records.md",
    _HERE / "docs" / "Appendix D Dialogue records.md",
)


def _find() -> Path | None:
    for path in _CANDIDATES:
        if path.is_file():
            return path
    return None

_HEAD = re.compile(r"^Landmark (\d+) \((.*?)\), slot (\d+)$")
_SPEAKER = re.compile(r"^\s*Speaker:\s*(.*)$")
_TEXT = re.compile(r"^\s*Text:\s*(.*)$")


class Dialogue:
    """``dialogue[landmark][slot]`` is ``(speaker, text)`` or None."""

    def __init__(self, records=None):
        self.records = records or {}

    def __getitem__(self, landmark):
        return self.records.get(landmark, [])

    def get(self, landmark: int, slot: int):
        row = self.records.get(landmark)
        if not row or slot < 0 or slot >= len(row):
            return None
        return row[slot]

    def speaker(self, landmark: int, slot: int) -> str:
        rec = self.get(landmark, slot)
        return rec[0] if rec else ""

    def text(self, landmark: int, slot: int) -> str:
        rec = self.get(landmark, slot)
        return rec[1] if rec else ""

    def landmarks(self):
        return sorted(self.records)

    def __len__(self):
        return sum(len(v) for v in self.records.values())


def source_path() -> Path | None:
    """The document the dialogue is read from, or None if it is not present."""
    return _find()


def available() -> bool:
    return _find() is not None


def count() -> int:
    return len(load().records)


def load(path: Path | None = None) -> Dialogue:
    """Read the records out of the appendix."""
    p = Path(path) if path else _find()
    if p is None or not p.is_file():
        where = ", ".join(str(c) for c in _CANDIDATES)
        raise FileNotFoundError(
            f"the dialogue records were not found. They are MECC's text and are "
            f"not redistributed here; put Appendix D at one of: {where}")
    records: dict[int, list] = {}
    landmark = slot = None
    speaker = text = None
    for raw in p.read_text(encoding="utf-8").splitlines():
        m = _HEAD.match(raw)
        if m:
            if landmark is not None:
                _store(records, landmark, slot, speaker, text)
            landmark, slot = int(m.group(1)), int(m.group(3))
            speaker = text = None
            continue
        m = _SPEAKER.match(raw)
        if m:
            speaker = m.group(1).strip()
            continue
        m = _TEXT.match(raw)
        if m:
            text = m.group(1).strip()
    if landmark is not None:
        _store(records, landmark, slot, speaker, text)
    return Dialogue(records)


def _store(records, landmark, slot, speaker, text):
    if landmark is None or slot is None:
        return
    row = records.setdefault(landmark, [None, None, None])
    row[slot] = (speaker or "", text or "")
