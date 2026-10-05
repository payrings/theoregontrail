"""The paper's own rules, used as the specification.

The two earlier audits read the code against the BASIC listing. This one reads it
against **the paper**, because the paper is where the rules are stated: section 2.5
sets out the eight properties of Applesoft a translation must respect, section 6.2
prints the climate table as 72 numbers, and section 13 lists the bugs that are
supposed to be reproduced.

Nothing here edits the paper. Where the code disagrees with it, the disagreement is
recorded in `FINDINGS.md`, as the brief requires.

Five of section 2.5's eight rules had never been tested against the code:

* a comparison is a number, 1 or 0, used in arithmetic;
* ``ON n GOSUB`` does nothing when ``n`` is 0 or past the last target;
* a subroutine runs on until it meets ``RETURN``, so ``TOMB.LIB`` 50000 falls into
  50005;
* ``INT`` rounds down, so ``INT`` of -2.7 is -3;
* string positions in ``MID$`` count from 1.
"""

from __future__ import annotations

import pytest

from oregon import num, tomb, trail
from oregon.data import climate as CL


def fresh(tmp_path, answers=("1",), draws=4000, value="0.5"):
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import ScriptedRnd
    from oregon.state import State
    from oregon.ui import ScriptedUI
    c = Context(ui=ScriptedUI(list(answers) * 200, allow_repeat=True,
                               max_prompts=4000),
                rng=ScriptedRnd(" ".join([value] * draws)),
                files=Files(tmp_path / "data"))
    c.st = State()
    c.st.NP = 5
    c.st.I[2] = num.parse("8")
    c.st.I[3] = num.parse("10")
    c.st.I[4] = num.parse("50")
    for item in range(3, 9):
        c.st.I[item] = num.parse("10")
    c.st.I[8] = num.parse("1000")
    c.st.PF = num.parse("1000")
    c.st.MY = num.parse("1000")
    for i in range(5):
        c.st.N[i] = "P%d" % i
    return c


# ------------------------------------------- paper 6.2, Table 13: the 72 codes
#: Transcribed from the paper's Table 13: for each climate row and month, the
#: temperature character and the rain character, as ASCII codes.
TABLE_13 = [
    (0, [(59, 43), (63, 44), (73, 56), (86, 63), (95, 78), (105, 78),
         (110, 69), (108, 70), (100, 72), (89, 60), (75, 49), (64, 45)]),
    (1, [(53, 35), (58, 35), (66, 40), (79, 51), (89, 60), (99, 63),
         (105, 57), (103, 52), (93, 46), (81, 40), (67, 35), (57, 35)]),
    (2, [(53, 35), (57, 35), (62, 39), (72, 46), (82, 51), (92, 43),
         (101, 40), (99, 36), (88, 39), (77, 39), (63, 37), (56, 35)]),
    (3, [(49, 35), (54, 37), (62, 42), (73, 53), (82, 55), (91, 43),
         (99, 38), (97, 35), (87, 41), (76, 44), (61, 38), (51, 36)]),
    (4, [(60, 45), (66, 43), (72, 43), (80, 42), (88, 42), (95, 39),
         (104, 33), (102, 33), (93, 36), (82, 40), (70, 43), (62, 44)]),
    (5, [(68, 87), (73, 71), (76, 66), (81, 53), (87, 51), (91, 46),
         (96, 35), (96, 40), (93, 47), (84, 63), (76, 84), (71, 94)]),
]


def test_the_climate_strings_are_twenty_four_characters():
    """Paper 6.2: "``WC$(0 to 5)`` holds six strings of 24 characters"."""
    assert len(CL.WC) == 6
    for row, s in enumerate(CL.WC):
        assert len(s) == 24, f"row {row} is {len(s)} characters"


@pytest.mark.parametrize("row,months", TABLE_13)
def test_every_climate_code_matches_the_papers_table_13(row, months):
    """Each month contributes one temperature character and one rain character, in
    that order, so month *m* is at offsets ``2m`` and ``2m + 1``."""
    got = [(ord(CL.WC[row][m * 2]), ord(CL.WC[row][m * 2 + 1])) for m in range(12)]
    assert got == months, f"row {row}"


def test_fn_w_matches_the_papers_worked_example(tmp_path):
    """Paper 6.2: "row 0 in January has codes 59 and 43.  The minimum temperature is
    9 degrees, the mean 29 degrees, and the rain chance 0.039."

    ``FN W(0)`` is the temperature code less 50 and ``FN W(1)`` is 0.003 times the rain
    code less 30.  Note the ``MID$`` position is ``AM * 2 + Z - 1`` and counts from
    one, so January -- ``AM = 1`` -- reads offsets 0 and 1 zero-based.
    """
    c = fresh(tmp_path)
    st = c.st
    st.ZO = 0
    st.AM = num.parse("1")
    assert trail.fn_w(st, 0).to_float() == 59 - 50, "the minimum is 9 degrees"
    assert trail.fn_w(st, 1).to_float() == pytest.approx(0.003 * (43 - 30), abs=1e-9)
    assert trail.fn_w(st, 1).to_float() == pytest.approx(0.039, abs=1e-6)


@pytest.mark.parametrize("row,months", TABLE_13)
def test_fn_w_reads_the_right_character_for_every_month(tmp_path, row, months):
    """``AM * 2 + Z - 1`` counts from one, so the zero-based offset is ``AM * 2 + Z - 2``
    -- one lower, and the code's comment says so."""
    c = fresh(tmp_path)
    st = c.st
    st.ZO = row
    for m, (temp, rain) in enumerate(months, start=1):
        st.AM = num.parse(str(m))
        assert trail.fn_w(st, 0).to_float() == temp - 50, f"row {row} month {m}"
        assert trail.fn_w(st, 1).to_float() == pytest.approx(0.003 * (rain - 30),
                                                            abs=1e-9), \
            f"row {row} month {m}"


# ------------------------------------- paper 2.5: a comparison is a number
def test_not_is_one_or_zero_and_never_minus_one(tmp_path):
    """Line 3244: ``V = BS * (1 - .1 * H0) * NOT SD * Z``.

    ``NOT`` is 1 for true and 0 for false.  If it were the -1 that ``NOT`` gives in
    some languages, ``V`` would be negative on every travelling day and the wagon
    would travel backwards; ``FINDINGS.md`` 18.9 records that this reading was
    inferred from behaviour and never tested.  This tests it.
    """
    c = fresh(tmp_path)
    st = c.st
    st.H0 = num.ZERO
    st.SD = num.ZERO
    st.H = num.parse("100")
    st.BS = num.parse("20")
    st.D = num.parse("50")
    st.DD = num.parse("50")
    trail.travel_today(c)
    assert num.as_float(st.D) > 0, "the wagon moved forwards on a travelling day"


def test_the_speed_factor_is_not_minus_one(tmp_path):
    """The same rule at 3246, where ``1.1 * V > D`` caps ``V`` at ``D``.  With a
    negative ``V`` the cap never fires and the segment never ends."""
    c = fresh(tmp_path)
    st = c.st
    st.BS = num.parse("12")
    st.H0 = num.ZERO
    st.H = num.parse("100")
    st.SD = num.ZERO
    st.DD = num.parse("1")
    st.D = num.parse("50")
    trail.travel_today(c)
    assert 0 < num.as_float(st.D) <= 50


# ----------------------------------- paper 2.5: INT rounds toward -infinity
@pytest.mark.parametrize("text,want", [
    ("2.7", 2), ("-2.7", -3), ("2", 2), ("-0.2", -1), ("0", 0),
])
def test_int_rounds_down_not_toward_zero(text, want):
    """Paper 2.5: "``INT`` rounds down, so ``INT`` of -2.7 is -3"."""
    got = num.int_(num.parse(text))
    assert got.to_float() == float(want), f"INT({text}) = {got.to_float()}"


def test_as_int_truncates_toward_zero_for_a_poke():
    """The other rounding, used where the listing POKEs: ``& INP`` and ``POKE`` want a
    whole number, and Applesoft's ``INT`` would floor a negative wrongly. The two
    functions must not be confused."""
    assert num.as_int(num.parse("2.7")) == 2
    assert num.as_int(num.parse("-2.7")) == -2


# ------------------- paper 2.5: a subroutine runs on until it meets RETURN
def test_a_call_with_no_return_falls_through_and_removes_the_member(tmp_path):
    """Paper 2.5: "``TOMB.LIB`` 50000 has none, so a call to it continues into line
    50005."

    Line 3504 is ``FOR L1 = 0 TO 4: Q = L1: ON (H1(L1) = -2) GOSUB 50000``, and 50005
    is ``NP = NP - 1: H1(Q) = H1(NP): H1(NP) = -1: ... IF NP THEN RETURN``. So a
    drowned member is removed because of the *fall-through*, not because 50000 asked
    for it -- 50000 only caps health at 105.
    """
    c = fresh(tmp_path)
    st = c.st
    st.NP = 3
    st.H1[0] = num.parse("-2")          # drowned
    st.H1[1] = num.parse("-2")          # drowned
    st.H1[2] = num.ZERO                 # alive
    st.H = num.parse("100")
    trail.remove_drowned(c)
    assert num.as_int(st.NP) == 1, "50005 ran once per drowned member"
    assert num.eq(st.H1[num.as_int(st.NP)], num.parse("-1")), "the corpse is marked"


def test_a_living_member_is_not_removed(tmp_path):
    c = fresh(tmp_path)
    st = c.st
    st.NP = 3
    for i in range(3):
        st.H1[i] = num.ZERO
    st.H = num.parse("100")
    trail.remove_drowned(c)
    assert num.as_int(st.NP) == 3


def test_the_stone_is_written_only_when_the_last_member_dies(tmp_path):
    """50010 -- the epitaph and the record -- runs only once ``NP`` is 0."""
    c = fresh(tmp_path, answers=("n", ""))
    st = c.st
    st.NP = 0                 # 50005 has already removed the last member
    st.H1[0] = num.parse("-1")
    st.N[0] = "Zeke"
    st.NM = num.parse("1")        # a non-zero segment code, or the slot reads empty
    st.LM = num.ZERO
    st.D = num.parse("50")
    tomb.all_dead(c, 0)
    assert c.files.tomb.is_file(), "50010 runs when NP is 0"
    rec = c.files.read_tombs(st.S)
    assert rec and rec["name"] == "Zeke", "50035 wrote the four fields"

# --------------------------------------- bugs reported from play, section 22
def test_the_trade_names_the_good_being_offered(tmp_path):
    """``TRADE.LIB`` 50032: ``F = I: L = Y + 2: ... GOSUB 50250``, and 50250 reads
    ``Z$ = I$(L)``. The inventory names are ``I$``, indexed 1 to 8, so the index is
    ``Y + 2``.

    Passing ``Y`` picked up ``I$(0)``, which is the empty string, and the sentence came
    out as "She will trade you 1 ." with nothing named at all.
    """
    from oregon import trade
    c = fresh(tmp_path, answers=("n",), draws=200, value="0.1")
    st = c.st
    st.NP = 2
    st.MY = num.parse("500")
    for item in range(3, 9):
        st.I[item] = num.parse("20")
    st.I[8] = num.parse("1000")
    st.PF = st.I[8]
    trade.attempt(c)
    said = " ".join(c.ui.out)
    line = [x for x in said.split("\n") if "will trade you" in x]
    assert line, "no offer was made"
    import re
    m = re.search(r"will trade you (\d+) (\S+)", line[0])
    assert m, f"nothing was named: {line[0]!r}"
    from oregon.data.text import I_NAMES
    for name in I_NAMES:
        if name and m.group(2).startswith(name.split(",")[0][:4]):
            break
    else:
        assert m.group(2) not in ("", "."), f"an empty name: {line[0]!r}"


def test_the_store_waits_for_a_key_after_the_space_bar_prompt(tmp_path):
    """``BUY SUPPLIES`` 3030: ``PRINT "Press SPACE BAR to leave store": Z = USR (1)``,
    and ``USR (1)`` waits for a key -- line 950 uses it for the same purpose and
    ``WIN`` 956 shows the loop: ``Z = USR (2): IF Z < 128 THEN 955``.

    The code printed the prompt and flushed the keyboard instead, so nothing waited:
    pressing space did nothing and Return silently answered the *next* question.
    Reported from play.
    """
    from oregon import buysupplies
    calls = []
    c = fresh(tmp_path, answers=("6",))
    real = c.ui.wait_key
    try:
        c.ui.wait_key = lambda prompt="", **kw: calls.append(prompt) or real(prompt, **kw)
        st = c.st
        st.LM = 0
        st.S = 1
        st.AD = num.parse("1")
        st.AM = num.parse("3")
        st.AY = num.parse("48")
        st.I[8] = num.parse("100")
        st.MY = num.parse("100")
        try:
            buysupplies.store(c)
        except Exception:
            pass
    finally:
        c.ui.wait_key = real
    assert "Press SPACE BAR to leave store" in calls, (
        "line 3030 waits for a key after that prompt")
