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
    gfx = c.ui.pictures
    if hasattr(c.ui, "sound"):
        c.ui.sound.select("ts")               # 50010: & RFL, "TS.BIN" AT 51944
    if gfx:
        from .graphics import screens
        screens.tombstone(c.ui, st.N[who])
        screens.tomb_bar(c.ui)                # 50010 ends GOSUB 950
        screens.tomb_window(c.ui)
    else:
        c.ui.clear()
        c.ui.print("Here lies")
        c.ui.print(st.N[who])
        c.ui.print()
        common.wait_key(c)                    # 50010 ends GOSUB 950

    def say(*lines):                          # PRINT CF$ ...: the bottom window, cleared
        if gfx:
            screens.tomb_window(c.ui)
        for line in lines:
            c.ui.print(line)

    say("Would you like to write", "an epitaph? ")
    epitaph = ""
    if common.yes_no(c) == "Y":
        while True:
            say("What would you like on the tombstone? ")           # 50020
            epitaph = c.ui.key(ALLOWED["EPITAPH"], 29, default="")
            # line 50030 is "IF LEN (A$) THEN ...": an empty epitaph is not shown
            # and is not offered for change
            if not epitaph:
                break
            if gfx:
                screens.tombstone(c.ui, st.N[who], epitaph)
            else:
                c.ui.print(epitaph)
            say("Would you like to make", "changes? ")
            if common.yes_no(c) == "N":
                break
    write_record(c, who, epitaph)
    if gfx:
        screens.tomb_window(c.ui)
        c.ui.line("All of the people", centre=True)
        c.ui.line("in your party have died.", centre=True)
        screens.tomb_bar(c.ui)
    else:
        c.ui.clear()
        c.ui.print("All of the people")
        c.ui.print("in your party have died.")
        common.wait_key(c)
    c.outcome = "DIED"
    return "MENU"


def write_record(c, who: int, epitaph: str):
    """Line 50035: the four fields, at offset 0 of the current side."""
    st = c.st
    segment = num.as_int(st.NM) * 100 + num.as_int(st.LM)
    # ``STR$ (D)``: the text the ROM builds, nine significant digits
    c.files.write_tomb(st.S, segment, num.str_(st.D), st.N[who], epitaph)


def read_grave(c):
    """Lines 50100-50105: read and show the stone the party has reached."""
    st = c.st
    from . import common, trail
    rec = c.files.read_tombs(st.S, st.LN)  # 50100: & TPTR,LN * 49
    if not rec:
        trail.find_grave(c)
        return
    if c.ui.pictures:
        from .graphics import screens
        screens.tombstone(c.ui, rec["name"], rec["epitaph"])
        c.ui.wait_key()                       # 50105 ends GOSUB 41100
    else:
        c.ui.clear()
        c.ui.print("Here lies")
        c.ui.print(rec["name"])
        c.ui.print()
        c.ui.print(rec["epitaph"])
        common.wait_key(c)
    trail.find_grave(c)
