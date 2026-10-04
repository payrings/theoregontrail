"""The two files the original keeps on disk, in a local data directory.

``HISCORE.SEQ``
    thirty text fields ended by carriage returns: name, points, rating for each of
    ten entries (``WIN`` 540).

``TOMB.SEQ``
    two records 49 bytes apart, one per disk side, each of four carriage-return
    terminated fields: the segment code, the miles remaining, the name and the
    epitaph. An empty record has a segment code of 0, which is how the reader at
    ``OREGON TRAIL`` 29004 and ``FLIP.LIB`` 50030 tells an unused slot from a grave.
    A new tombstone is always written at offset 0, so each side keeps one current
    grave and the newest replaces the older (paper section 10.2).

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

    The first two go through ``STR$`` in the original, which prefixes a space to a
    positive number; the leading space is dropped on the way in because the reader
    strips it again, and nothing in the game depends on the space.
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
        self.tomb = self.dir / "TOMB.SEQ"
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
    def read_tombs(self, side: int):
        """The four fields of one side's record, or None when that slot is empty."""
        if not self.tomb.is_file():
            return None
        raw = self.tomb.read_bytes()
        off = side * TOMB_RECORD_SIZE
        chunk = raw[off:off + TOMB_RECORD_SIZE].decode("ascii", errors="replace")
        fields = self._split(chunk)
        while len(fields) < 4:
            fields.append("")
        segment = _as_int(fields[0])
        if segment == 0:
            return None                     # an empty record has a segment code of 0
        return {"segment": segment, "miles": _as_number(fields[1]),
                "name": fields[2], "epitaph": fields[3]}

    def write_tomb(self, side: int, segment: int, miles, name: str, epitaph: str):
        """TOMB.LIB 50035: always at offset 0, so the newest replaces the older."""
        fields = tomb_fields(segment, miles, name, epitaph)
        record = self._join(fields)
        if len(record) > TOMB_RECORD_SIZE:
            record = record[:TOMB_RECORD_SIZE - 1] + "\r"
        raw = bytearray(self.tomb.read_bytes()) if self.tomb.is_file() else bytearray()
        off = side * TOMB_RECORD_SIZE
        raw[off:off + TOMB_RECORD_SIZE] = record.encode(
            "ascii", errors="replace").ljust(TOMB_RECORD_SIZE, b"\r")
        self.tomb.write_bytes(bytes(raw))

    def erase_tombs(self, side: int):
        """MANAGEMENT 250: write an empty record, which has a segment code of 0."""
        raw = bytearray(self.tomb.read_bytes()) if self.tomb.is_file() else bytearray()
        blank = (_EMPTY_TOMB + "\r" + _EMPTY_TOMB + "\r").encode("ascii")
        off = side * TOMB_RECORD_SIZE
        raw[off:off + TOMB_RECORD_SIZE] = blank.ljust(TOMB_RECORD_SIZE, b"\r")
        self.tomb.write_bytes(bytes(raw))

    def erase_all_tombs(self):
        self.erase_tombs(0)
        self.erase_tombs(1)


def _as_int(text: str) -> int:
    """A field as a whole number; a field that is not one counts as 0.

    ``STR$`` prefixes a space to a positive number, so fields are stripped. The
    miles field of a tombstone can be fractional -- ``STR$(D)`` is written straight
    into the record at ``TOMB.LIB`` 50035 -- so :func:`_as_number` handles that
    case and this one is only for the points and the segment code.
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
