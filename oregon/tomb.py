"""TOMB.LIB: the gravestones.

Lines 50000 to 51030. When the last member dies the game shows a stone with the
leader's name and offers an epitaph of up to twenty-nine characters, then writes one
record to ``TOMB.SEQ`` on the current side: four fields, each ended by a carriage
return, being the segment, the miles remaining, the name and the epitaph. The record
is always written at offset 0, so each side keeps one current grave and the newest
replaces the older. The management program can erase them.

A later party meets the grave as event 4 when it is on the same segment and has
passed the recorded distance from the next landmark.
"""

from __future__ import annotations

from . import common, num
from .ui import ALLOWED

__all__ = ["all_dead", "read_grave"]


def all_dead(c, who: int):
    """Lines 50010-50040: the stone, the epitaph and the record."""
    st = c.st
    from . import common
    c.ui.clear()
    c.ui.print("Here lies")
    c.ui.print(st.N[who])
    c.ui.print()
    c.ui.print("Would you like to write")
    c.ui.print("an epitaph? ")
    epitaph = ""
    if common.yes_no(c) == "Y":
        while True:
            epitaph = c.ui.key(ALLOWED["EPITAPH"], 29, default="")
            if epitaph:
                c.ui.print(epitaph)
            c.ui.print("Would you like to make")
            c.ui.print("changes? ")
            if common.yes_no(c) == "N":
                break
    write_record(c, who, epitaph)
    c.ui.clear()
    c.ui.print("All of the people")
    c.ui.print("in your party have died.")
    common.wait_key(c)
    c.outcome = "DIED"
    return "MENU"


def write_record(c, who: int, epitaph: str):
    """Line 50035: the four fields, at offset 0 of the current side."""
    st = c.st
    from . import common
    common.check_side(c, st.S + 1)
    segment = num.as_int(st.NM) * 100 + num.as_int(st.LM)
    c.files.write_tomb(st.S, segment, num.as_float(st.D), st.N[who], epitaph)


def read_grave(c):
    """Lines 50100-50105: read and show the stone the party has reached."""
    st = c.st
    from . import common, trail
    rec = c.files.read_tombs(st.LN)
    if not rec:
        trail.find_grave(c)
        return
    c.ui.clear()
    c.ui.print("Here lies")
    c.ui.print(rec["name"])
    c.ui.print()
    c.ui.print(rec["epitaph"])
    common.wait_key(c)
    trail.find_grave(c)
