"""The game's error handler, as a defined outcome rather than a Python failure.

Every program sets ``ONERR GOTO 32000`` (paper section 2.4). The handler reads the
error number from 222 and the line from 218 and 219, resumes after a disk error,
and otherwise prints

    Error [code] at line #[line] in [program]. Please report this error to MECC.

waits for a key and goes back to the menu. The codes are Applesoft's own, and two of
them are part of the game's behaviour rather than faults:

``53`` ILLEGAL QUANTITY
    what a POKE of a value above 255 produces, which is why a party that reaches
    Oregon more than 255 years after 1800 stops with "Error 53 at line #50050"
    (paper section 13).

``6`` OVERFLOW
    what the 5-byte format produces when a result leaves its range. The freeze and
    starve factor ``FS`` has no cap (section 13), so a very long wait at a river can
    drive it out of range.

Both are raised as :class:`ApplesoftError` and handled by :func:`handle`, which
prints the message and returns to the menu, exactly as the original does.
"""

from __future__ import annotations

__all__ = ["ApplesoftError", "ERROR_NAMES", "handle", "ILLEGAL_QUANTITY", "OVERFLOW"]

ILLEGAL_QUANTITY = 53
OVERFLOW = 6
BAD_SUBSCRIPT = 5
OUT_OF_DATA = 4
DIVISION_BY_ZERO = 11

ERROR_NAMES = {
    4: "OUT OF DATA",
    5: "BAD SUBSCRIPT",
    6: "OVERFLOW",
    10: "DIVISION BY ZERO",
    11: "DIVISION BY ZERO",
    16: "STRING TOO LONG",
    53: "ILLEGAL QUANTITY",
    69: "OUT OF MEMORY",
    255: "BREAK",
}


class ApplesoftError(Exception):
    """An error raised by the game, carrying the code and the BASIC line.

    :attr:`line` is the BASIC line number the original would have reported, which
    is what makes this useful: a trace can be lined up against the listing.
    """

    def __init__(self, code: int, line: int, program: str, detail: str = ""):
        self.code = code
        self.line = line
        self.program = program
        self.detail = detail
        name = ERROR_NAMES.get(code, f"ERROR {code}")
        super().__init__(f"Error {code} ({name}) at line #{line} in {program}"
                         + (f": {detail}" if detail else ""))


def handle(ui, err: ApplesoftError, program: str | None = None) -> str:
    """COMMON.LIB 32120: print the message, wait for a key, go back to the menu.

    Returns what the menu should do next, which is always the menu, so a caller can
    ``return handle(ui, err)``.
    """
    pn = program or err.program
    ui.clear()
    ui.print(f"Error {err.code} at line #{err.line} in {pn}.")
    ui.print()
    ui.print("Please report this error to MECC.")
    ui.wait_key()
    return "MENU"
