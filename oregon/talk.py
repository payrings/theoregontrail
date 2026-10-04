"""TALK.LIB: the three people at each landmark.

Lines 50000-50010. The record is at ``(LM - S * 5) * 768 + A * 256``, so side one
holds landmarks 0 to 4 and side two 5 to 16, and ``A`` is the slot: it starts as a
random 0, 1 or 2 on arrival and advances by one each time the action menu is drawn,
so the three speakers come round in turn.

The dialogue itself is MECC's and is read from the reference document rather than
copied into this repository; see :mod:`oregon.data.dialogue`.
"""

from __future__ import annotations

from . import num
from .data import landmarks as L
from .data import text as T

__all__ = ["talk"]


def talk(c):
    """Lines 50000-50010."""
    st = c.st
    from . import common
    from .data import dialogue as DG
    d = DG.load()
    slot = num.as_int(st.A) % 3
    speaker = d.speaker(st.LM, slot)
    text = d.text(st.LM, slot)
    c.ui.clear()
    c.ui.print(f"{speaker} tells you:")
    c.ui.print()
    c.ui.print('"' + text + '"')
    common.wait_key(c)
    return speaker, text
