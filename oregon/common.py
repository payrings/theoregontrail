"""COMMON.LIB: the helpers every program shares.

Lines 30000 to 41100. These are the small routines the BASIC calls from everywhere:
the money and date strings, the wait-for-a-key, the yes/no prompt, the box the
messages go in, the disk-side check and the error handler.
"""

from __future__ import annotations

from . import num
from .errors import ApplesoftError, handle

__all__ = ["money", "dollar_text", "date_text", "wait_key", "yes_no",
           "space_wait", "message", "error_handler", "check_side", "short_name"]


def money(c: "Context", v) -> str:
    """Lines 200 / 250: ``V = INT (V * 100 + .5)`` then the split into dollars and
    cents with ``STR$``.

    The result keeps the leading space ``STR$`` puts in front of a positive number,
    which is what the ``RIGHT$`` arithmetic in the callers expects, and zero comes
    out as ``" 0. 0"``, which the original prints.
    """
    cents = num.trunc(num.add(num.mul(v, num.parse("100")), num.parse(".5")))
    return num.dollar(cents)


def dollar_text(c: "Context", v) -> str:
    """The same, with the dollar sign the callers add."""
    return "$" + money(c, v)


def date_text(c: "Context") -> str:
    """Line 250: ``TD$ = M$(AM - 1) + " " + STR$(AD) + ", " + STR$(AY)``."""
    from .data import text as T
    st = c.st
    return (f"{T.MONTHS[num.as_int(st.AM) - 1]} {num.str_(st.AD)}, "
            f"{num.str_(st.AY)}")


def short_name(c: "Context", landmark: int | None = None) -> str:
    """Line 260: the landmark name without a leading ``the ``."""
    from .data import landmarks as L
    n = c.st.LM if landmark is None else landmark
    return L.short_name(n)


def wait_key(c: "Context", prompt: str = "Press SPACE BAR to continue"):
    """Line 950: clear the bottom line, prompt, and wait for any key.

    Control-S toggles the sound, which the loop at 956-957 watches for; the sound
    flag is kept so the state is right even though nothing is heard.
    """
    return c.ui.wait_key(prompt=prompt)


def space_wait(c: "Context"):
    """Line 30000: ``& SPACE: & QFH: RETURN`` -- a blank line and nothing else."""
    c.ui.print()


def yes_no(c: "Context", prompt: str = "") -> str:
    """COMMON.LIB 30120: ``& INP,3,"YESNOyesno",1,Z$``; returns ``"Y"`` or ``"N``."""
    return c.ui.yes_no(prompt)


def message(c: "Context", text: str, lines=None, wait: bool = True):
    """Lines 700 and 900: the framed box a message is printed in, then a key.

    ``lines`` are the loss lines the routine prints indented beneath the message --
    at a river they are the goods lost, at a fire the goods burnt. They come from
    ``T$(0 to 10)`` in the original and are cleared as they are printed.
    """
    c.ui.print(text)
    for t in (lines or []):
        if t:
            c.ui.print("   " + t)
    if wait:
        wait_key(c)


def error_handler(c: "Context", err: ApplesoftError) -> str:
    """COMMON.LIB 32120: print the error, wait for a key, go back to the menu."""
    return handle(c.ui, err, c.program)


def check_side(c: "Context", want: int) -> int:
    """COMMON.LIB 33000: make sure the disk side the game expects is in.

    The original reads the volume name and prompts until the right side is in. There
    is no disk here, so this is the same prompt and the same change of ``S``.
    """
    want = 1 if want in (1, 2) else (c.st.S + 1)
    if want - 1 == c.st.S:
        return c.st.S
    got = c.ui.flip_disk(want, "OREGON TRAIL")
    c.st.S = (int(got) - 1) if str(got).strip().isdigit() else c.st.S
    return c.st.S
