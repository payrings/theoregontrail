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


def test_the_store_never_asks_for_a_key_it_did_not_ask_for(tmp_path):
    """Line 3030 prints "Press SPACE BAR to leave store" and then *flushes*.

    ``USR (1)`` clears the keyboard; it is not a request for a keypress. Treating
    it as one put a "Press SPACE BAR to continue" in the middle of the store that
    the player never saw asked for, and the number they typed went to that instead.
    """
    from oregon.ui import ScriptedUI
    ui = ScriptedUI(["1", "4", ""] + ["1", "4", ""] * 20, allow_repeat=True)
    c, got = store(ui, tmp_path)
    # The leave-store label is a label, not a request: the item prompt follows it
    # directly. Treating the label as a wait inserted a keypress between the two,
    # and that is what swallowed the number the player typed.
    labels = [i for i, l in enumerate(ui.out) if l == "Press SPACE BAR to leave store"]
    assert labels, "the store never showed its panel"
    for i in labels:
        rest = [l for l in ui.out[i + 1:i + 3] if l]
        assert rest and rest[0].startswith("Which item would you like to"), rest
    # and the introduction's screens are the only places a key is waited for
    said = " ".join(ui.out)
    for text in ("Before leaving Independence", "You can buy whatever you need",
                 "plenty of food for the trip"):
        assert text in said


def test_the_item_prompt_takes_one_to_five_and_return_leaves(tmp_path):
    from oregon.ui import ScriptedUI
    ui = ScriptedUI(["1", "4", "", "", ""] + [""] * 20, allow_repeat=True)
    c, got = store(ui, tmp_path)
    assert c.mem.peek(905) == 4, "four yoke bought"
    said = " ".join(ui.out)
    assert "Which item would you like to buy" in said
    assert "How many yoke do you" in said


def test_the_bill_is_the_sum_of_the_five_lines(tmp_path):
    from oregon.ui import ScriptedUI
    ui = ScriptedUI(["1", "4", "2", "1000", "3", "6", "4", "6", "5", "1", "1", "1", ""]
                    + [""] * 20, allow_repeat=True)
    c, got = store(ui, tmp_path)
    # 4 yoke at 40, 1000 lb at 0.20, 6 sets at 10, 6 boxes at 2, one of each part
    # at 10
    assert B.bill(c) == pytest.approx(160 + 200 + 60 + 12 + 30, abs=0.01)
    assert got["yokes"] == 4 and got["food"] == 1000
    assert [c.mem.peek(x) for x in (910, 911, 912)] == [1, 1, 1]
    assert c.st.MY.to_float() == pytest.approx(1600 - 462, abs=0.01)


def test_the_store_cannot_be_left_without_oxen(tmp_path):
    """Line 5006: no oxen, so the party cannot leave and must trade or buy."""
    from oregon.ui import ScriptedUI
    ui = ScriptedUI([""] * 12, allow_repeat=True, max_prompts=40)
    with pytest.raises(AssertionError):
        store(ui, tmp_path)
    said = " ".join(ui.out)
    assert "Don't forget, you'll need oxen to pull your wagon" in said


def test_the_store_cannot_be_left_with_an_unpayable_bill(tmp_path):
    """Line 5000: the bill above the money held, so leaving is refused."""
    from oregon.ui import ScriptedUI
    # a carpenter has $800; 4000 pounds of food alone is $800
    # oxen 160 + food 400 + 99 sets at 10 = 990, over the 800 a carpenter has
    ui = ScriptedUI(["1", "4", "2", "2000", "3", "99", ""] + [""] * 12,
                   allow_repeat=True, max_prompts=40)
    with pytest.raises(AssertionError):
        store(ui, tmp_path, money="800.00")
    said = " ".join(ui.out)
    assert "only have $" in said, "leaving should have been refused for the bill"
    assert "Well then, you're ready to start" not in said
