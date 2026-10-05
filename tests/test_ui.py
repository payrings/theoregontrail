"""The screen and keyboard interface.

One test here is a whole class of bug: a prompt filters on an allowed-character
set, and if that set does not cover the choices the screen prints, a choice becomes
unreachable. It happened -- the profession screen offers 1 to 4 and allowed only
``-``, ``1`` and ``4``, so a carpenter and a farmer could not be chosen at all, and
the main menu could not reach "learn about the trail" or the top ten.
"""
import pytest

from oregon import num
from oregon.context import Context
from oregon.rng import ScriptedRnd
from oregon.state import State
from oregon.ui import ALLOWED, ScriptedUI, allowed_chars

DIGITS = set("0123456789")


def offered_choices(out):
    """The numbers a screen offers, from lines like ``1. Be a banker``."""
    import re
    found = []
    for line in out:
        m = re.match(r"^\s*(\d)\. ", line)
        if m:
            found.append(m.group(1))
    return found


def test_every_menu_prompt_allows_every_choice_it_offers():
    """The check that would have caught it.

    ``& INP`` ignores a character outside its allowed set and waits for another, so
    a set that does not cover the screen's choices makes those choices
    unreachable. Each entry here is a screen and the prompt that answers it.
    """
    screens = [
        ("profession", ["1. Be a banker from Boston", "2. Be a carpenter from Ohio",
                        "3. Be a farmer from Illinois",
                        "4. Find out the differences"], "PROFESSION"),
        ("main menu", ["1. Travel the trail", "2. Learn about the trail",
                       "3. See the Oregon Top Ten", "4. Turn sound on"], "CHOICE"),
        ("management", ["1. See the current Top Ten list",
                        "2. See the original Top Ten list",
                        "3. Erase the current Top Ten list",
                        "4. Erase the tombstone messages",
                        "5. Return to main menu"], "MANAGE"),
        ("month", ["1. March", "2. April", "3. May", "4. June", "5. July",
                   "6. Ask for advice"], "MONTH"),
        ("pace", ["1. a steady pace", "2. a strenuous pace",
                  "3. a grueling pace",
                  "4. find out what these different paces mean"], "PACE"),
        ("branch", ["1. head for Independence Rock", "2. head for Fort Bridger",
                    "3. see the map"], "SEGMENT"),
        ("rations", ["1. filling", "2. meager", "3. bare bones"], "RATION"),
        ("dalles", ["1. float down the Columbia River",
                    "2. take the Barlow Toll Road"], "DALLES"),
        ("fort", [f"{i}. good" for i in range(1, 8)] + ["8. Leave store"], "FORT"),
        ("rest", ["1"], "REST"),
    ]
    problems = []
    for label, lines, key in screens:
        choices = offered_choices(lines)
        allowed = allowed_chars(ALLOWED[key])
        for choice in choices:
            if choice not in allowed:
                problems.append(f"{label}: choice {choice} is not in {key}")
    assert not problems, problems


def test_an_allowed_set_is_characters_and_ranges():
    """``-AZ`` means A to Z. Reading it as a literal list is the whole bug.

    ``MENU`` 500 passes ``"-AZ-az '.-"`` for a name. Taken literally that is the
    four letters A, Z, a and z, so a name prompt accepted almost nothing -- which is
    exactly what was reported. As ranges it is every letter, plus a space, an
    apostrophe and a period.
    """
    names = allowed_chars(ALLOWED["NAMES"])
    assert all(ch in names for ch in
               "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert " " in names and "'" in names and "." in names
    assert "5" not in names, "a name takes no digits, as in the original"
    # "-14" is a range, so a four-choice menu allows all four
    assert set(allowed_chars(ALLOWED["PROFESSION"]) & DIGITS) == set("1234")
    assert set(allowed_chars(ALLOWED["MANAGE"]) & DIGITS) == set("12345")
    assert set(allowed_chars(ALLOWED["MONTH"]) & DIGITS) == set("123456")
    assert set(allowed_chars(ALLOWED["FORT"]) & DIGITS) == set("12345678")
    assert set(allowed_chars(ALLOWED["RIVER"]) & DIGITS) == set("12345")
    assert set(allowed_chars(ALLOWED["DIGITS09"]) & DIGITS) == set("0123456789")
    assert set(allowed_chars(ALLOWED["DIGITS19"]) & DIGITS) == set("123456789")
    assert set(allowed_chars("YESNOyesno")) == set("YESNOyesno")


def test_an_inverted_range_is_tolerated():
    """A range written backwards must not raise or silently allow nothing."""
    assert allowed_chars("Z-A") == allowed_chars("A-Z")
    assert "-" in allowed_chars("Z-A")


MONEY = {"1": 1600, "2": 800, "3": 400}


@pytest.mark.parametrize("answer,want", sorted(MONEY.items()))
def test_every_profession_is_reachable(answer, want, tmp_path):
    """1 banker, 2 carpenter, 3 farmer.

    The profession screen's allowed set used to be ``-14``, so ``2`` and ``3`` were
    unreachable and a player could only ever be a banker.
    """
    from oregon import menu
    from oregon.files import Files
    ui = ScriptedUI([answer] + [""] * 20, allow_repeat=True)
    c = Context(ui=ui, rng=ScriptedRnd("0.5 " * 5000), files=Files(tmp_path))
    got = menu.profession(c)
    assert got == int(answer)
    assert c.mem.peek(915) == int(answer)
    assert c.mem.peek_word(913) == want * 10, "the money is stored times ten"


def test_the_fourth_choice_explains_the_professions(tmp_path):
    """Choice 4 is the explanation screen, and it must not be taken as a trade."""
    from oregon import menu
    from oregon.files import Files
    ui = ScriptedUI(["4", "N", "2"] + [""] * 20, allow_repeat=True)
    c = Context(ui=ui, rng=ScriptedRnd("0.5 " * 5000), files=Files(tmp_path))
    assert menu.profession(c) == 2
    assert c.mem.peek_word(913) == 800 * 10


def test_the_terminal_reads_a_whole_line_per_prompt():
    """A prompt must consume exactly one Return, or answers drift by one."""
    ui = ScriptedUI([], allow_repeat=True)
    # the scripted side reads positionally, so this checks the interface contract:
    # one call, one answer, no leftovers
    ui.answers = ["2"]
    assert ui.key(ALLOWED["PROFESSION"], 1) == "2", \
        "an answer must survive the prompt's own allowed set"
    assert ui.i == 1, "the prompt consumed more than its own answer"


def test_the_river_menu_allows_five_choices():
    """RIVER.LIB offers 1 to 5: ford, float, ferry or guide, wait, more."""
    from oregon import river
    digits = allowed_chars(ALLOWED["RIVER"]) & DIGITS
    assert digits == set("12345"), sorted(digits)
    assert len(river.TXT) == 6, "TXT(0) to TXT(5) is the river's option text"


def test_the_fort_shop_allows_every_good_plus_leaving():
    digits = allowed_chars(ALLOWED["FORT"]) & DIGITS
    assert digits == set("12345678"), sorted(digits)


def test_an_unmatched_prompt_reports_rather_than_looping():
    ui = ScriptedUI([], allow_repeat=False, max_prompts=5)
    for _ in range(10):
        with pytest.raises(AssertionError):
            ui.key("1", 1)


def test_a_name_prompt_accepts_any_letters():
    """The bug this was written for: only ``a`` was recognised.

    ``"-AZ-az '.-"`` is a range list, so it must take every letter in either case,
    plus a space, an apostrophe and a period -- and nothing else, since a name takes
    no digits.
    """
    ui = ScriptedUI(["Ebenezer"], allow_repeat=True)
    assert ui.key(ALLOWED["NAMES"], 9) == "Ebenezer"
    ui = ScriptedUI(["o'brien"], allow_repeat=True)
    assert ui.key(ALLOWED["NAMES"], 9) == "o'brien"
    ui = ScriptedUI(["Mary-Jane"], allow_repeat=True)
    assert ui.key(ALLOWED["NAMES"], 9) == "Mary-Jane"
    # and a digit is not a name character, so it is ignored and the prompt waits
    ui = ScriptedUI(["4Zeke\n"], allow_repeat=True)
    assert ui.key(ALLOWED["NAMES"], 9) == "Zeke"


def test_the_top_ten_and_epitaph_sets():
    ui = ScriptedUI(["Ebenezer"], allow_repeat=True)
    assert ui.key(ALLOWED["TOPTEN"], 15) == "Ebenezer"
    ui = ScriptedUI(["Over the mountains, 1849"], allow_repeat=True)
    assert ui.key(ALLOWED["EPITAPH"], 29) == "Over the mountains, 1849"


def test_the_store_item_prompt_takes_one_to_five():
    """Line 250's reader: anything outside 1 to 5, or a space, is ignored.

    Spelled the way the game spells a range -- dash first, so ``"-15"``. Written
    ``"1-5"`` it would mean the literal characters 1, dash and 5, and only two of
    the five items could be chosen.
    """
    from oregon.ui import ALLOWED as A
    assert sorted(allowed_chars(A["STORE_ITEM"]) & DIGITS) == list("12345")
    ui = ScriptedUI(["3"], allow_repeat=True)
    assert ui.key(A["STORE_ITEM"], 1, default="") == "3"
    ui = ScriptedUI(["6"], allow_repeat=True)
    assert ui.key(A["STORE_ITEM"], 1, default="") == "", "6 is not a choice"
    ui = ScriptedUI([""], allow_repeat=True)
    assert ui.key(A["STORE_ITEM"], 1, default="") == "", "a bare Return leaves"
