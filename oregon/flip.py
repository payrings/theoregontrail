"""FLIP.LIB: the disk flip at Fort Laramie.

The game needs side two of the disk from Fort Laramie onward, and the original makes
the player flip it: ``600 GOSUB 33000: & APP, "FLIP.LIB": GOSUB 50000``. The side two
copy asks for side one again before the top ten can be written.

There is no disk here, so :meth:`oregon.ui.UI.flip_disk` prompts and returns the
side, and the grave records for the new side are read again -- which is the part that
matters, since the two sides hold one grave each.
"""

from __future__ import annotations

from . import num

__all__ = ["to_side_2", "to_side_1"]


def to_side_2(c):
    """FLIP.LIB, side 1: ``S = 1``, prompt, then re-read the two grave records."""
    st = c.st
    c.ui.print("To continue on your journey to Oregon, please flip the diskette to "
               "side 2.")
    common_wait(c)
    st.S = 1
    read_graves(c)
    return st.S


def to_side_1(c):
    """FLIP.LIB, side 2: ask for side one again, which the top ten needs."""
    st = c.st
    c.ui.print("Please insert side 1 of the Oregon Trail diskette.")
    common_wait(c)
    st.S = 0
    read_graves(c)
    return st.S


def common_wait(c):
    from . import common
    common.wait_key(c)


def read_graves(c):
    """Line 50030 of FLIP.LIB and line 29004 of OREGON TRAIL."""
    st = c.st
    for side in (0, 1):
        rec = c.files.read_tombs(side)
        if rec:
            st.SN[side] = rec["segment"]
            st.ML[side] = rec["miles"]
