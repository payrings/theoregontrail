"""The two files the original keeps on disk, in a local data directory.

``HISCORE.SEQ``
    thirty text fields ended by carriage returns: name, points, rating for each of
    ten entries (``WIN`` 540).

``TOMB.SEQ``
    one file on each disk side, kept here as ``side1/TOMB.SEQ`` and
    ``side2/TOMB.SEQ``. The game reads two records from the current side's file, at
    offsets 0 and 49 (``OREGON TRAIL`` 29004, ``FLIP.LIB`` 50030, ``TOMB.LIB``
    50100), each of four carriage-return terminated fields: the segment code, the
    miles remaining, the name and the epitaph. ``& TREED`` reads a field up to its
    carriage return. An empty record has a segment code of 0. A new tombstone is
    always written at offset 0 (``TOMB.LIB`` 50035), field after field with nothing
    cut, so a long record runs on past byte 49 into the second record; the newest
    grave replaces the older (paper section 10.2).

The field order is the paper's, and the readers accept the fields as plain text so a
file written by the original would read back. Nothing is written unless the game
writes it: the store's fresh directory holds an empty top ten, which the management
program then resets to the original list exactly as the original does.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["Files", "TOMB_RECORD_SIZE", "TOP_TEN_FIELDS", "tomb_fields",
           "hiscore_fields"]

TOMB_RECORD_SIZE = 49
TOP_TEN_FIELDS = 30

_EMPTY_TOMB = "0"


def tomb_fields(segment: int, miles, name: str, epitaph: str):
    """The four fields of a tombstone record, in the paper's order.

    The first two go through ``STR$`` in the original. The ROM builds that text with
    no space before a positive number, so the fields are written as they are; the
    miles arrive as the text ``STR$ (D)`` gives (nine significant digits).
    """
    return [str(segment), str(miles), str(name), str(epitaph)]


def hiscore_fields(entries):
    """Thirty fields: name, points, rating for each of ten entries."""
    out = []
    for name, points, rating in entries:
        out.extend([str(name), str(points), str(rating)])
    while len(out) < TOP_TEN_FIELDS:
        out.append("")
    return out[:TOP_TEN_FIELDS]


class Files:
    """The two files, held in a directory of their own."""

    def __init__(self, directory: Path | str = "data"):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.tomb = self.tomb_file(0)
        self.hiscore = self.dir / "HISCORE.SEQ"

    # ------------------------------------------------------------------ CRs
    @staticmethod
    def _split(text: str):
        return [f for f in text.split("\r")]

    @staticmethod
    def _join(fields) -> str:
        return "".join(f + "\r" for f in fields)

    # -------------------------------------------------------------- top ten
    def read_hiscore(self):
        """Read the thirty fields into ten ``(name, points, rating)`` entries."""
        if not self.hiscore.is_file():
            return []
        # newline="" so Python's universal newlines does not turn the record
        # separators -- carriage returns -- into newlines before they are split
        fields = self._split(self.hiscore.read_text(
            encoding="utf-8", errors="replace", newline=""))
        entries = []
        for i in range(10):
            chunk = fields[i * 3:(i + 1) * 3]
            if len(chunk) < 3:
                break
            name, points, rating = (chunk + ["", "", ""])[:3]
            entries.append([name, _as_int(points), rating])
        return entries

    def write_hiscore(self, entries):
        self.hiscore.write_text(self._join(hiscore_fields(entries)),
                               encoding="utf-8")

    def reset_hiscore(self):
        """MANAGEMENT 700: replace the list with the original ten."""
        from .data import hiscore as data
        self.write_hiscore(data.original())
        return self.read_hiscore()

    # ------------------------------------------------------------ tombstones
    def tomb_file(self, side: int) -> Path:
        """``TOMB.SEQ`` on disk side ``side + 1``."""
        d = self.dir / f"side{side + 1}"
        d.mkdir(parents=True, exist_ok=True)
        return d / "TOMB.SEQ"

    def _tomb_bytes(self, side: int) -> bytearray:
        p = self.tomb_file(side)
        if p.is_file():
            return bytearray(p.read_bytes())
        # two empty records, as MANAGEMENT 250 writes them
        empty = (_EMPTY_TOMB + "\r" + _EMPTY_TOMB + "\r").encode("ascii")
        return bytearray(empty.ljust(TOMB_RECORD_SIZE, b"\r") * 2)

    def read_tombs(self, side: int, index: int = 0):
        """``& TPTR, index * 49`` then four ``& TREED`` reads, from the file on disk
        side ``side + 1``; None when the record's segment code is 0."""
        raw = self._tomb_bytes(side)
        pos = index * TOMB_RECORD_SIZE
        fields = []
        for _ in range(4):
            field = bytearray()
            while pos < len(raw) and raw[pos] not in (0, 13) and len(field) < 240:
                field.append(raw[pos] & 0x7F)
                pos += 1
            pos += 1                            # past the carriage return
            fields.append(field.decode("ascii", errors="replace"))
        segment = _as_int(fields[0])
        if segment == 0:
            return None                     # an empty record has a segment code of 0
        return {"segment": segment, "miles": _as_number(fields[1]),
                "name": fields[2], "epitaph": fields[3]}

    def write_tomb(self, side: int, segment: int, miles, name: str, epitaph: str):
        """TOMB.LIB 50035: ``& TPTR,0`` and four ``& TWRITE``s, nothing cut."""
        record = self._join(tomb_fields(segment, miles, name, epitaph)).encode(
            "ascii", errors="replace")
        raw = self._tomb_bytes(side)
        if len(raw) < len(record):
            raw.extend(b"\0" * (len(record) - len(raw)))
        raw[0:len(record)] = record
        self.tomb_file(side).write_bytes(bytes(raw))

    def erase_tombs(self, side: int):
        """MANAGEMENT 250: ``& TPTR,0: & TWRITE,"0" + CM$ + "0" + CM$`` -- only the
        record at offset 0 is blanked."""
        raw = self._tomb_bytes(side)
        blank = (_EMPTY_TOMB + "\r" + _EMPTY_TOMB + "\r").encode("ascii")
        raw[0:len(blank)] = blank
        self.tomb_file(side).write_bytes(bytes(raw))

    def erase_all_tombs(self):
        self.erase_tombs(0)
        self.erase_tombs(1)


def _as_int(text: str) -> int:
    """A field as a whole number; a field that is not one counts as 0.

    Fields are stripped in case a file written elsewhere carries spaces. The miles
    field of a tombstone can be fractional -- ``STR$(D)`` is written straight into
    the record at ``TOMB.LIB`` 50035 -- so :func:`_as_number` handles that case and
    this one is only for the points and the segment code.
    """
    n = _as_number(text)
    return int(n) if n == int(n) else int(n // 1)


def _as_number(text: str) -> float:
    t = (text or "").strip()
    if not t:
        return 0.0
    try:
        return float(t)
    except ValueError:
        return 0.0
