"""The 51 monologues, read from ``dialogue.md`` beside this module.

The original game keeps its dialogue in ``OREGON1.SEQ`` and ``OREGON2.SEQ``: three
256-byte records for each of the seventeen landmarks that have any, each record a
speaker and a text separated by a carriage return. The record read is at byte offset
``(LM - S * 5) * 768 + A * 256``, where ``S`` is the disk side -- 0 for landmarks 0
to 4, 1 for 5 to 16 -- and ``A`` is the slot (paper section 9.1).

The original text is MECC's and is not part of this repository. ``dialogue.md`` is
replacement dialogue written for this project, with the same shape: three records of
speaker and text for each landmark, none longer than the game's 240-character read.
The TypeScript rebuild ships a byte-identical copy of the file.

A different document in the same format can be used by setting the environment
variable ``OREGON_DIALOGUE`` to its path, or by passing a path to :func:`load`.
:func:`load` raises if no document is found, because talking to people is part of
playing the game and a silent empty list would be worse than a clear failure.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

__all__ = ["Dialogue", "load", "available", "source_path", "count"]

_HERE = Path(__file__).resolve().parent
#: the replacement dialogue that ships with the game
DEFAULT = _HERE / "dialogue.md"


def _find() -> Path | None:
    given = os.environ.get("OREGON_DIALOGUE")
    for path in (Path(given) if given else None, DEFAULT):
        if path is not None and path.is_file():
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
    """Read the records out of the dialogue document."""
    p = Path(path) if path else _find()
    if p is None or not p.is_file():
        raise FileNotFoundError(
            f"the dialogue records were not found: expected {DEFAULT}, "
            f"or a document named by OREGON_DIALOGUE")
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
