"""Matt's store: the numbered panel, and what the prompt accepts.

Two bugs are guarded here. The five bill lines were printed without their numbers,
though line 3015 is ``PRINT L". "I$(L)`` and the number is what the player types;
and ``USR (1)`` at line 3030 -- a *flush* of the keyboard -- was being treated as a
request for a key, so the store asked twice.
"""
import pytest

from oregon import buysupplies as B
from oregon import num
from oregon.files import Files
from oregon.ui import ALLOWED, allowed_chars


def store(ui, tmp_path, money="1600.00"):
    from oregon.context import Context
    from oregon.rng import ScriptedRnd
    c = Context(ui=ui, rng=ScriptedRnd("0.5 " * 5000), files=Files(tmp_path))
    c.mem.poke_word(913, int(float(money) * 10))
    B.init_state(c)
    return c, B.store(c)


def test_the_five_lines_are_numbered(tmp_path):
    """Line 3015 prints the number with each line, and that is the choice."""
    from oregon.ui import ScriptedUI
    # buy oxen first: line 5006 will not let the party leave without them, so a
    # bare Return on an empty store is refused and the panel comes round again
    ui = ScriptedUI(["1", "4", ""] + ["1", "4", ""] * 20, allow_repeat=True)
    c, got = store(ui, tmp_path)
    import re
    panel = [l for l in ui.out if re.match(r"^\d\. ", l)]
    assert len(panel) >= 5, [l for l in ui.out if "$" in l]
    for n, line in enumerate(panel[:5], 1):
        assert line.strip().startswith(f"{n}. "), line
    assert panel[0].startswith("1. oxen"), panel[0]
    assert "pounds of food" in panel[1]
    assert "spare wagon parts" in panel[4]


def test_the_store_waits_for_one_key_at_the_space_bar_prompt(tmp_path):
    """``BUY SUPPLIES`` 3030:

    ``PRINT "Press SPACE BAR to leave store": Z = USR (1): & CO: PRINT "Which item
    would you like to "A$"? "``

    ``USR (1)`` **waits for a key**. Line 950 uses it for "Press SPACE BAR to
    continue", and ``WIN`` 956 is the routine itself: ``Z = USR (2): IF Z < 128 THEN
    955`` -- it loops until a key arrives with the high bit set, which is any ordinary
    key, space included.

    This test previously asserted the opposite -- that ``USR (1)`` clears the keyboard
    and nothing waits -- and blamed the wait for swallowing the player's number. That
    diagnosis was wrong, and it is why the bug survived: pressing space at the store
    did nothing, and Return worked only because it was answering the *next* question.
    Reported from play; see ``FINDINGS.md`` 22.
    """
    from oregon.ui import ScriptedUI
    ui = ScriptedUI([""] + ["1", "4"] * 20 + [""], allow_repeat=True)
    asked = []
    real = ui.wait_key
    ui.wait_key = lambda prompt="", **kw: (asked.append(prompt), real(prompt, **kw))[1]
    store(ui, tmp_path)
    assert "Press SPACE BAR to leave store" in asked, (
        f"line 3030 waits for a key after that prompt; waits asked for: {asked!r}")
