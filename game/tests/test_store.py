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
    # 3015 prints the store's own I$(1 to 5), read from BUY SUPPLIES 29000
    assert panel[0].startswith("1. Oxen"), panel[0]
    assert panel[1].startswith("2. Food"), panel[1]
    assert panel[4].startswith("5. Spare parts"), panel[4]


def test_the_space_bar_prompt_does_not_wait(tmp_path):
    """``BUY SUPPLIES`` 3030:

    ``PRINT "Press SPACE BAR to leave store": Z = USR (1): & CO: PRINT "Which item
    would you like to "A$"? "``

    The USR routine the package installs (it starts at $86D1) returns at once for
    ``USR (1)`` after clearing the keyboard strobe; only arguments with bit 2 set,
    such as ``USR (5)``, wait. So nothing waits here: the space bar is read by the
    item prompt (line 252 accepts 1 to 5 or a space, and a space leaves the store).
    """
    from oregon.ui import ScriptedUI
    ui = ScriptedUI([""] + ["1", "4"] * 20 + [""], allow_repeat=True)
    asked = []
    real = ui.wait_key
    ui.wait_key = lambda prompt="", **kw: (asked.append(prompt), real(prompt, **kw))[1]
    store(ui, tmp_path)
    assert "Press SPACE BAR to leave store" in ui.out
    assert "Press SPACE BAR to leave store" not in asked, asked


def test_spare_parts_cost_ten_dollars_and_too_many_is_asked_again(tmp_path):
    """Lines 800 to 811: ``"- $"SP$(L,1)" each"`` with ``SP$(L,1) = "10"``, and an
    answer over 3 is followed by ``L = L - 1``, so the same part is asked again."""
    from oregon.ui import ScriptedUI
    ui = ScriptedUI(["1", "4", "5", "7", "2", "1", "1", ""] + [""] * 20,
                    allow_repeat=True)
    c, got = store(ui, tmp_path)
    said = "\n".join(ui.out)
    assert "- $10 each" in said and "- $200 each" not in said
    asked = [l for l in ui.out if l.startswith("How many wagon")]
    assert asked[:4] == ["How many wagon wheels? ", "How many wagon wheels? ",
                         "How many wagon axles? ", "How many wagon tongues? "], asked
    assert [c.mem.peek(a) for a in (910, 911, 912)] == [2, 1, 1]
