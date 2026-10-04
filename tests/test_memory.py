"""The two hand-over layouts, the illegal-quantity error, and the files."""
import pytest

from oregon import num
from oregon.errors import ApplesoftError
from oregon.files import Files, TOMB_RECORD_SIZE, hiscore_fields, tomb_fields
from oregon.mem import Memory
from oregon.trace import FIELDS, Tracer


def test_the_names_round_trip_through_address_1920():
    """MENU 6045 writes them zero-terminated; OREGON TRAIL 29010 reads them back."""
    m = Memory()
    m.put_names(["Zeke", "Jed", "", "Mary", "Emily"], 6045)
    assert m.get_names() == ["Zeke", "Jed", "", "Mary", "Emily"]


def test_an_empty_name_still_terminates_correctly():
    m = Memory()
    m.put_names(["", "B", "", "D", ""], 6045)
    assert m.get_names() == ["", "B", "", "D", ""]


def test_the_start_layout_is_what_the_store_writes():
    """Table 4: money times ten at 913, yokes at 905, food across 906 and 907."""
    m = Memory()
    m.poke_word(913, 16000, 4030)          # $1600.00 times ten
    assert m.peek_word(913) == 16000
    assert num.div(num.parse(str(m.peek_word(913))), num.parse("10")).to_float() == 1600.0
    m.poke(905, 4)                          # four yoke
    m.poke_word(906, 1200)                  # a thousand pounds of food
    assert m.peek(906) + m.peek(907) * 256 == 1200


def test_the_end_layout_puts_the_oxen_at_909_and_the_bullets_at_904():
    """The two layouts really are different, which is the trap in paper 2.3."""
    m = Memory()
    m.poke(909, 8)                          # the end layout: oxen
    m.poke_word(904, 120)                   # and the bullets
    assert m.peek(909) == 8
    assert m.peek_word(904) == 120
    assert m.peek(905) == 0, "905 is the high byte of the bullet count here"


def test_a_poke_above_255_is_applesoft_illegal_quantity():
    """``POKE 901, AY - 1800`` past 2055 stops the program (paper section 13)."""
    m = Memory("OREGON TRAIL")
    with pytest.raises(ApplesoftError) as exc:
        m.poke(901, 256, 50050)
    assert exc.value.code == 53
    assert exc.value.line == 50050
    assert "Error 53 (ILLEGAL QUANTITY) at line #50050 in OREGON TRAIL" \
        in str(exc.value)
    m.poke(901, 255, 50050)                # 2055 is still fine


def test_a_negative_poke_is_also_illegal():
    m = Memory()
    with pytest.raises(ApplesoftError):
        m.poke(900, -1)


def test_the_keyboard_counter_is_the_seed_source():
    m = Memory()
    m.keyboard_counter = 4242
    assert m.peek(78) == 4242 % 256
    assert m.peek(79) == 4242 // 256
    assert m.keyboard_counter == 4242


def test_the_top_ten_is_thirty_carriage_terminated_fields():
    from oregon.data import hiscore as HIS
    fields = hiscore_fields(HIS.original())
    assert len(fields) == 30
    assert fields[0] == "Stephen Meek" and fields[1] == "7650"
    assert fields[2] == "Trail guide"


def test_the_top_ten_round_trips(tmp_path):
    from oregon.data import hiscore as HIS
    f = Files(tmp_path)
    f.write_hiscore(HIS.original())
    back = f.read_hiscore()
    assert len(back) == 10
    assert back[0] == ["Stephen Meek", 7650, "Trail guide"]
    assert back[-1] == ["Elijah White", 250, "Greenhorn"]
    assert f.reset_hiscore() == back


def test_a_tombstone_is_four_fields_on_each_side(tmp_path):
    f = Files(tmp_path)
    assert f.read_tombs(0) is None, "an unwritten slot has a segment code of zero"
    f.write_tomb(0, 1603, 42.5, "Zeke", "gone west")
    assert f.read_tombs(1) is None
    rec = f.read_tombs(0)
    assert rec == {"segment": 1603, "miles": 42.5, "name": "Zeke",
                   "epitaph": "gone west"}
    f.write_tomb(1, 1604, 10, "Jed", "")
    assert f.read_tombs(1)["name"] == "Jed"
    assert f.read_tombs(0)["name"] == "Zeke", "the sides are separate"


def test_the_records_are_49_bytes_apart():
    assert TOMB_RECORD_SIZE == 49
    assert tomb_fields(1, 2, "a", "b") == ["1", "2", "a", "b"]


def test_erasing_a_tombstone_clears_only_that_side(tmp_path):
    f = Files(tmp_path)
    f.write_tomb(0, 1, 2, "Zeke", "")
    f.write_tomb(1, 3, 4, "Jed", "")
    f.erase_tombs(0)
    assert f.read_tombs(0) is None
    assert f.read_tombs(1) is not None


def test_the_trace_has_one_line_per_day_and_the_papers_fields():
    from oregon.state import State
    tr = Tracer()
    st = State()
    tr.day(st, "travel")
    tr.day(st, "rest", stopped=True)
    assert tr.days == 2
    line = tr.line(st, "travel")
    cells = line.split()
    assert len(cells) == len(FIELDS), "one column per name in Appendix H"
    assert cells[0].isdigit() and cells[1].isdigit(), "the date comes first"
    assert cells[-1] == "0000000000", "the five seed bytes come last"
    assert cells[-2] == "travel"
    assert tr.line(st, "rest", stopped=True).split()[-2].endswith("+")
