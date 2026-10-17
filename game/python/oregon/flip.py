"""FLIP.LIB: the disk flip at Fort Laramie.

The game needs side two of the disk from Fort Laramie onward, and the original makes
the player flip it: ``600 GOSUB 33000: & APP, "FLIP.LIB": GOSUB 50000``. The side two
copy asks for side one again before the top ten can be written.

There is no disk here, so :meth:`oregon.ui.UI.flip_disk` prompts and returns the
side, and the grave records for the new side are read again -- which is the part that
matters, since the two sides hold one grave each.
"""

from __future__ import annotations

__all__ = ["to_side_2", "to_side_1", "back_to_menu"]


def to_side_2(c):
    """FLIP.LIB, side 1: ``S = 1``, prompt, then re-read the two grave records."""
    st = c.st
    saved = None
    if c.ui.pictures:
        from .graphics import screens
        saved = screens.flip_to_side_2(c.ui)
    else:
        c.ui.print("To continue on your journey to Oregon, please flip the diskette to "
                   "side 2.")
    common_wait(c)
    if saved is not None:
        c.ui.cv.put(saved)                    # 50020: & PUT,0,Y5 + 10,49152
    st.S = 1
    read_graves(c)
    return st.S


def to_side_1(c):
    """FLIP.LIB, side 2: ask for side one again, which the top ten needs."""
    st = c.st
    if c.ui.pictures:
        from .graphics import screens
        screens.flip_to_side_1(c.ui)
    else:
        c.ui.print("Please insert side 1 of the Oregon Trail diskette.")
    common_wait(c)
    st.S = 0
    read_graves(c)
    return st.S


def back_to_menu(c):
    """MENU SIDE 2 line 31000: ``GOSUB 33000: NORMAL: ON S GOSUB 600 ... PRINT "Getting the Oregon
    Trail menu...": & RNH,"MENU"``. When side 2 is in (``S`` = 1) the player is asked for side 1
    again, then the menu is fetched."""
    if getattr(c.st, "S", 0):
        to_side_1(c)
    text = "Getting the Oregon Trail menu..."
    if c.ui.pictures:
        from .graphics import screens
        screens.getting_menu(c.ui, text)
    else:
        c.ui.print(text)


def common_wait(c):
    from . import common
    common.wait_key(c)


def read_graves(c):
    """Line 50030 of FLIP.LIB and line 29004 of OREGON TRAIL."""
    st = c.st
    for rec_no in (0, 1):                     # the two records of this side's file
        rec = c.files.read_tombs(st.S, rec_no)
        st.SN[rec_no] = rec["segment"] if rec else 0
        st.ML[rec_no] = rec["miles"] if rec else 0
