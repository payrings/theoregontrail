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

    ``STR$`` has no leading space, so the result is ``800.00`` for $800, ``0.05`` for
    five cents and ``0.00`` for nothing.
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


def message(c: "Context", text: str, lines=None, wait: bool = True, kind: int = 900, g: int = 0):
    """Lines 700 and 900: the framed box a message is printed in, then a key.

    ``lines`` are the loss lines the routine prints indented beneath the message --
    at a river they are the goods lost, at a fire the goods burnt. They come from
    ``T$(0 to 10)`` in the original and are cleared as they are printed.
    """
    if c.ui.pictures:
        from . import trail
        trail.event_box(c, text, list(lines or []), kind, g)
        return c.ui.wait_key() if wait else None
    c.ui.print(text)
    for t in (lines or []):
        if t:
            c.ui.print("   " + t)
    if wait:
        return wait_key(c)
    return None


RETURN_KEYS = ("\r", "\n")


def message_700(c: "Context", text: str):
    """Line 700: the message box and nothing more. No wait, and ``B`` is untouched."""
    message(c, text, wait=False, kind=700)


def message_710(c: "Context", text: str, g: int = 0):
    """Line 710: ``GOSUB 700: GOSUB 41100 ... IF NOT B THEN B = FN B(Z) AND NOT SD``.

    41100 waits for a key (30000). ``FN B`` is ``PEEK (-16384) = 13``, the key that
    ended the wait, so Return sets ``B`` to 1 -- the action menu opens at line 3180 --
    unless ``B`` is already set or days are being stopped.
    """
    key = message(c, text, kind=700, g=g)
    st = c.st
    if not st.B:
        st.B = 1 if (key in RETURN_KEYS and not st.SD) else 0
    return key


def message_900(c: "Context", text: str, lines=None):
    """Lines 900-905: the message with its loss lines, a wait, then
    ``B = (PEEK (-16384) = 13)`` -- an assignment, so any other key clears ``B``."""
    key = message(c, text, lines)
    c.st.B = 1 if key in RETURN_KEYS else 0
    return key


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
