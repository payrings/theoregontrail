"""Expectations derived from the listing, not from the code.

Every other test in this suite checks the code against itself: it asserts what the
transcription does. These tests do the opposite. Each expectation here was worked out
by hand from the BASIC line quoted above it, and the test then says the code must
agree. Where the two differ, **the listing is right** -- the paper is the subject of
the analysis, not the authority for what the program does, and nothing here edits it.

Three kinds of test:

* **Conservation.** ``LF.LIB`` 50000 prints ``STR$(Y)`` and then does ``I(Y) = YY - X``.
  If a routine reports a quantity, the holding must fall by that quantity. A
  transcription can spend the right number of draws, keep every message, and still
  lose nothing -- and only a conservation law notices.
* **Unconditional statements.** An ``IF`` whose false branch simply falls off the end
  of the line still runs whatever follows it. ``RATION.LIB`` 50040 ends
  ``... GOSUB 650: RETURN``, so the speed is recalculated even when the answer was
  empty and ``R`` is unchanged.
* **Static shape.** Four of the defects in ``FINDINGS.md`` 18 and 19 were Python's own
  semantics leaking in: a short-circuiting ``and``, a literal where the listing has a
  variable. Those are visible in the source without running anything, so they are
  refused outright rather than waited for to show up as a wrong number.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

import pytest

from oregon import flip, lf, num, part, ration, river, tomb, trail

SRC = pathlib.Path(__file__).resolve().parent.parent / "oregon"


def fresh(tmp_path, answers=("1",), draws=4000, value="0.5"):
    """A context with a scripted screen and a constant-value generator."""
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.state import State
    from oregon.ui import ScriptedUI
    from oregon.ui import ScriptedUI
    c = Context(ui=ScriptedUI(list(answers) * 200, allow_repeat=True,
                            max_prompts=4000),
        rng=ScriptedRnd(" ".join([value] * draws)),
        files=Files(tmp_path / "data"))
    c.st = State()
    c.st.NP = 5
    c.st.I[2] = num.parse("8")
    for item in range(3, 9):          # all six goods held, so nothing is skipped
        c.st.I[item] = num.parse("10")
    c.st.I[4] = num.parse("50")
    c.st.I[8] = num.parse("1000")
    c.st.PF = num.parse("1000")
    c.st.MY = num.parse("1000")
    for i in range(5):
        c.st.N[i] = "P%d" % i
    return c


def quantities(text):
    """The leading number of every reported loss line."""
    out = []
    for line in text.replace(";", ".").split("."):
        line = line.strip()
        digits = ""
        for ch in line:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            out.append(int(digits))
    return out


def holdings(st):
    """``I(3)`` to ``I(8)`` -- the six goods 50205 loops over, food included."""
    return {i: num.as_float(st.I[i]) for i in range(3, 9)}


# ------------------------------------------------------- conservation of goods
#: ``LF.LIB`` 50000:
#: ``FOR Y = 3 TO 7:YY = I(Y): IF RND (1) < .5 AND YY THEN
#: X = INT ( RND (1) * YY + 1):I(Y) = YY - X: GOSUB 53000``
#:
#: The reported quantity is ``X``, so it is at least 1 and at most the whole holding,
#: and the holding must fall by exactly that much.
@pytest.mark.parametrize("value", ["0.05", "0.2", "0.5", "0.9"])
def test_a_reported_fire_loss_takes_the_goods_away(tmp_path, value):
    c = fresh(tmp_path, value=value)
    before = holdings(c.st)
    text = "\n".join(lf.fire(c))
    got = quantities(text)
    assert got, f"no loss reported at value={value}: {text!r}"
    assert all(q >= 1 for q in got), f"a loss of 0 at value={value}: {text!r}"
    after = holdings(c.st)
    assert sum(before.values()) - sum(after.values()) == sum(got), (
        f"value={value}: reported {got}, holdings moved "
        f"{sum(before.values()) - sum(after.values())}")


#: ``LF.LIB`` 52010: ``X = INT ( RND (1) * X + 1):I(Y) = YY - X:PF = PF - X * (Y = 8)``.
def test_a_reported_theft_takes_the_goods_away(tmp_path):
    c = fresh(tmp_path, value="0.05")
    before = holdings(c.st)
    text = "\n".join(lf.thief(c))
    got = quantities(text)
    after = holdings(c.st)
    assert sum(before.values()) - sum(after.values()) == sum(got), (
        f"reported {got}, holdings moved "
        f"{sum(before.values()) - sum(after.values())}")


#: ``RIVER.LIB`` 50205, shared verbatim with ``FLOAT`` 50205:
#: ``X = I(L): IF X AND RND (1) < V THEN Y = INT ( RND (1) * X + 1):I(L) = X - Y``.
@pytest.mark.parametrize("item", [3, 4, 5, 6, 7, 8])
def test_a_reported_river_loss_takes_that_good_away(tmp_path, item):
    c = fresh(tmp_path, value="0.05")
    out = river.losses(c, num.parse(".5"), item, "test")
    assert out is not None, "value=0.05 is below .5, so the good is lost"
    got = quantities(out)
    assert len(got) == 1, f"one good is lost per call, got {got}"
    assert 1 <= got[0] <= 50, (
        f"INT ( RND (1) * X + 1) is at least 1 and at most the holding: "
        f"reported {got[0]} of {num.as_float(c.st.I[item])}")


#: Nothing may be reported as lost that is not lost. This is the law that catches
#: ``INT (RND * 1 + 0)``: the draw is spent, the message is printed, and the holding
#: never moves.
def test_a_loss_is_never_reported_without_being_applied(tmp_path):
    for value in ("0.05", "0.3", "0.5", "0.7"):
        c = fresh(tmp_path, value=value)
        for item in range(3, 9):
            c.st.I[item] = num.parse("7")
            out = river.losses(c, num.parse(".5"), item, "test")
            if out is None:
                assert num.as_float(c.st.I[item]) == 7, "nothing reported, nothing lost"
                continue
            assert num.as_float(c.st.I[item]) < 7, (
                f"{out!r} was reported but the holding is still 7")


# ----------------------------------------------------- unconditional statements
#: ``RATION.LIB`` 50040:
#: ``& INP,1,"-13",0,Z$:Z$ = Z$ + "":Z = LEN (Z$):R = Z * VAL (Z$) + R * NOT Z:
#: & CO,X,Y: PRINT R: GOSUB 650: RETURN``
#:
#: ``GOSUB 650`` sits after the whole expression and before the RETURN, so it runs
#: whatever the answer was.
def test_changing_rations_recalculates_the_speed_even_on_an_empty_answer(tmp_path):
    c = fresh(tmp_path, answers=("",))
    c.st.R = num.parse("2")
    calls = []
    original = trail.speed
    try:
        trail.speed = lambda ctx: calls.append(1)
        ration.change(c)
    finally:
        trail.speed = original
    assert calls, "line 50040 runs GOSUB 650 whatever was answered"


def test_an_empty_answer_keeps_the_ration(tmp_path):
    """``R = Z * VAL (Z$) + R * NOT Z`` -- with nothing typed, ``Z`` is 0 and ``R``
    survives."""
    c = fresh(tmp_path, answers=("",))
    c.st.R = num.parse("3")
    ration.change(c)
    assert num.as_int(c.st.R) == 3


@pytest.mark.parametrize("answer,want", [("1", 1), ("2", 2), ("3", 3)])
def test_each_ration_sets_r(tmp_path, answer, want):
    c = fresh(tmp_path, answers=(answer,))
    c.st.R = num.parse("1")
    assert ration.change(c) == want
    assert num.as_int(c.st.R) == want


def test_a_digit_outside_the_allowed_set_is_refused(tmp_path):
    """``& INP,1,"-13",0,Z$`` admits only 1, 2 and 3, so 9 never reaches ``VAL``."""
    c = fresh(tmp_path, answers=("9", "2"))
    c.st.R = num.parse("1")
    ration.change(c)
    assert num.as_int(c.st.R) == 2


# -------------------------------------------- graves: FLIP.LIB 50030, TOMB 50035
#: ``TOMB.LIB`` 50035 writes ``STR$(NM * 100 + LM)`` and then ``STR$(D)``, so the
#: segment code is the landmark *reached* times a hundred plus the landmark *left*.
#: ``FLIP.LIB`` 50030 reads two records per side, each starting 49 bytes apart.
@pytest.mark.parametrize("side,nm,lm,miles", [
    (0, 1, 0, 83.0), (0, 9, 7, 190.0), (1, 17, 16, 100.0),
])
def test_a_grave_is_written_and_read_back_unchanged(tmp_path, side, nm, lm, miles):
    c = fresh(tmp_path)
    c.st.S = side
    c.st.NM = nm
    c.st.LM = lm
    c.st.D = num.parse(str(miles))
    tomb.write_record(c, 0, "Here lies Zeke")
    c.st.SN = [0, 0]
    c.st.ML = [0.0, 0.0]
    flip.read_graves(c)
    assert c.st.SN[side] == nm * 100 + lm, "SN(L) = VAL(NM * 100 + LM)"
    assert num.as_float(c.st.ML[side]) == miles, "ML(L) = VAL(D)"


def test_a_grave_on_one_side_does_not_appear_on_the_other(tmp_path):
    """The two records are indexed by side; ``50030`` loops ``L = 0 TO 1`` over sides,
    not over landmarks."""
    c = fresh(tmp_path)
    c.st.S = 1
    c.st.NM = 17
    c.st.LM = 16
    c.st.D = num.parse("100")
    tomb.write_record(c, 0, "epitaph")
    c.st.SN = [0, 0]
    c.st.ML = [0.0, 0.0]
    flip.read_graves(c)
    assert c.st.SN[0] == 0, "side one has no grave"
    assert c.st.SN[1] == 1716


# ------------------------------------------------ PART.LIB 42030 and 42100
#: ``42030 ... Z = I(B): IF Z THEN I(B) = Z - 1: A$ = A$ + "": GOSUB 42100: RETURN``
#:
#: One spare is consumed, and only when one is held.
def test_exactly_one_spare_is_consumed_when_a_part_breaks(tmp_path):
    c = fresh(tmp_path, answers=("n",))
    c.st.B = 5                       # 42100: B = 5 is a wagon wheel
    c.st.I[5] = num.parse("2")
    part.broken_part(c)
    assert num.as_float(c.st.I[5]) == 1, "one spare is used, not the whole stock"


def test_no_spare_is_consumed_when_none_is_held(tmp_path):
    c = fresh(tmp_path, answers=("n",))
    c.st.B = 5
    c.st.I[5] = num.ZERO
    part.broken_part(c)
    assert num.as_float(c.st.I[5]) == 0


def test_the_part_index_is_the_broken_item_not_the_spare_slot(tmp_path):
    """``S$(B - 2, 2)`` and ``I(B)``: ``B`` indexes both the name and the holding, so a
    wheel (B = 5) reads ``I(5)`` and never ``I(6)``."""
    c = fresh(tmp_path, answers=("n",))
    c.st.B = 5
    c.st.I[4] = num.parse("9")
    c.st.I[5] = num.parse("1")
    c.st.I[6] = num.parse("3")
    part.broken_part(c)
    assert num.as_float(c.st.I[4]) == 9, "bullets are untouched"
    assert num.as_float(c.st.I[6]) == 3, "axles are untouched"


# ------------------------------------------------------ static shape, generically
_DRAWS = ("rnd1", "below", "int_range", "int_span", "draw")


def _calls(node, names):
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                and sub.func.attr in names:
            out.append(sub)
    return out


def test_no_if_can_short_circuit_a_draw():
    """Applesoft evaluates both sides of AND and OR. ``FINDINGS.md`` 18.3, 18.4 and
    19.3 are all this one mistake: a state test joined to a draw with ``and`` or
    ``or``, so Python skips the draw when the state test is false.

    Only the operand order is checked, because that is what decides whether the draw
    survives. A draw as the *first* operand of a BoolOp is safe, since Python always
    evaluates it; a state test first is not.
    """
    offenders = []
    for path in sorted(SRC.glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            for sub in ast.walk(node.test):
                if not isinstance(sub, ast.BoolOp):
                    continue
                for i, side in enumerate(sub.values):
                    if i and _calls(side, _DRAWS):
                        offenders.append(f"{path.name}:{sub.lineno}")
    assert not offenders, ("a draw that Python's short-circuit can skip: "
                           + ", ".join(offenders))


def test_no_int_of_a_draw_uses_a_literal_one_and_zero():
    """``FINDINGS.md`` 19.1: four sites transcribed ``INT ( RND (1) * X + 1)`` -- X
    being the holding -- as ``INT(RND * 1 + 0)``, which is always zero, so every
    announced loss was announced and none was applied. The shape is recognisable.
    """
    offenders = []
    for path in sorted(SRC.glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "int_"):
                continue
            for call in _calls(node, ("add",)):
                for arg in call.args:
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) \
                            and arg.func.attr == "mul":
                        if any(isinstance(m, ast.Attribute) and m.attr == "ONE"
                               for m in arg.args):
                            offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, ("INT(RND * 1 + 0), which is always 0: "
                           + ", ".join(offenders))
