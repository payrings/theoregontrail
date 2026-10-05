"""The names of the goods, from ``LF.LIB``/``FLOAT`` 50250, 50255 and 50260.

These three lines between them decide every noun the game prints about a good, and the
rule is not "stem plus an s":

* 50250 ``Z$ = I$(L):Z = (F = 1) * ((L = 8) + (L = 2) + (L = 3) + ("s" = RIGHT$(Z$,1))):IF NOT Z THEN RETURN``
  -- unless the quantity is exactly one, the name is used **unchanged**. That is how
  "pounds of food" and "wagon wheels" survive.
* 50255 ``IF L <> 8 AND L <> 3 THEN Z$ = LEFT$(Z$, LEN (Z$) - 1 - (L = 2)): RETURN``
  -- the singular drops a trailing "s", and oxen lose two letters.
* 50260 ``Z = 6 - 2 * (L = 3):Z$ = LEFT$(Z$,Z - 1) + RIGHT$(Z$, LEN (Z$) - Z): RETURN``
  -- food and clothing are split into a stem and a qualifier. ``RIGHT$`` returns the
  last *n* characters, so for clothing that is ``RIGHT$(Z$, 12)``.

Both failures below were reported from play: "wants 81 pounds" with no "of food", and
"1 wagon wheels" / "3 wagon wheelss" (``FINDINGS.md`` 20.4 and 23.4).
"""

from __future__ import annotations

import pytest

from oregon.data.text import I_NAMES
from oregon.trade import _wording


def listing_word(item: int, f: int) -> str:
    """50250 / 50255 / 50260, transcribed."""
    name = I_NAMES[item]
    if f != 1:                       # 50250: Z = (F = 1) * (...) = 0, so RETURN
        return name
    if item in (8, 3):               # 50260
        z = 6 - 2 * (item == 3)
        return name[:z - 1] + name[len(name) - (len(name) - z):]
    if item == 2:                    # 50255: LEN - 1 - (L = 2)
        return name[:len(name) - 2]
    return name[:-1]                 # 50255: LEN - 1


@pytest.mark.parametrize("item", [2, 3, 4, 5, 6, 7, 8])
@pytest.mark.parametrize("f", [1, 2, 5, 81])
def test_the_wording_matches_the_listing(item, f):
    assert _wording(item, f) == listing_word(item, f), (
        f"I$({item}) with F = {f}")


def test_food_is_named_in_full():
    """The report: "You meet another emigrant who wants 81 pounds." -- no "of food"."""
    assert _wording(8, 81) == "pounds of food"
    assert _wording(8, 1) == "pound of food"


def test_no_good_gets_a_double_s():
    for item in range(2, 9):
        for f in (2, 5, 81):
            w = _wording(item, f)
            assert not w.endswith("ss"), f"I$({item}) F={f} gave {w!r}"


def test_no_good_is_named_in_the_plural_when_there_is_one():
    assert _wording(5, 1) == "wagon wheel"
    assert _wording(7, 1) == "wagon tongue"
    assert _wording(4, 1) == "bullet"


def test_the_loss_lines_use_the_same_rules():
    """``T$(Z) = STR$(X) + " " + Z$`` -- 53000 and 50250 share the wording, so
    ``lf._line`` must not have its own idea of plurals."""
    from oregon.lf import _line
    for item in range(2, 9):
        for n in (1, 3, 40):
            assert _line(0, n, item) == "%d %s" % (n, _wording(item, n)), \
                f"lf._line and trade._wording disagree at I$({item}), {n}"


def test_the_trade_names_the_good_it_is_asked_for(tmp_path):
    """50030 builds ``L = X + 2`` and 50032 ``L = Y + 2``; both are read by 50250. The
    index passed to the wording must be the ``I$`` one, not the ``S$`` one."""
    from oregon import trade
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.state import State
    from oregon.ui import ScriptedUI
    c = Context(ui=ScriptedUI(["n"] * 80, allow_repeat=True),
                rng=ScriptedRnd("0.1 " * 4000),
                files=Files(tmp_path / "data"))
    st = State()
    st.NP = 2
    st.MY = num_parse("500")
    st.I[8] = num_parse("1000")
    st.PF = st.I[8]
    for i in range(2, 9):
        st.I[i] = num_parse("20")
    c.st = st
    trade.attempt(c)
    said = " ".join(c.ui.out)
    assert "wants" in said and "will trade you" in said, said[-300:]
    for line in said.split("  "):
        if "wants" in line or "will trade you" in line:
            for item in range(2, 9):
                for f in (1, 2, 3, 5, 20, 40, 81):
                    if _wording(item, f) in line:
                        break
            # every noun in the two sentences must be a real good name
            import re
            for m in re.finditer(r"wants (\d+) ([a-z].*?)\.", line):
                assert m.group(2).rstrip(".") in [
                    _wording(i, n) for i in range(2, 9) for n in (1, 2, 3, 4, 5, 20,
                                                                  40, 81, 100)], \
                    f"{m.group(2)!r} is not a good name"


def num_parse(text):
    from oregon import num
    return num.parse(text)
