"""The reference trace of Appendix G, checked against the rebuild.

``tests/data/trace_10190.printer.txt`` is the parallel-printer output of the
original game running in LinApple with the instrumented disk images: nine lines
per day, labelled A to I, as the paper's Appendix G describes. It is seed
10,190 of the preset start, 196 days, and it is the game's own output, not the
rebuild's.

The file needs no ROM image, so this test runs anywhere. It compares the
rebuild's trace with the original's, value by value, allowing the half a unit
in the last digit the rebuild prints that the paper allows.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(__file__).resolve().parent / "data"
TRACE = DATA / "trace_10190.printer.txt"

# The field, and the format the rebuild prints it with (oregon/trace.py).
SPECS = [
    ("AD", "{:02d}"), ("AM", "{:02d}"), ("AY", "{:d}"),
    ("D", "{:.4g}"), ("M", "{:.5g}"), ("H", "{:.6g}"), ("FS", "{:.6g}"),
    ("H0", "{:d}"), ("HR", "{:d}"), ("W", "{:d}"), ("TM", "{:d}"), ("PP", "{:d}"),
    ("AR", "{:.6g}"), ("AS", "{:.6g}"), ("PF", "{:.7g}"),
    ("I2", "{:.6g}"), ("I3", "{:.6g}"), ("I4", "{:.8g}"),
    ("I5", "{:d}"), ("I6", "{:d}"), ("I7", "{:d}"),
    ("I8", "{:.8g}"), ("MY", "{:.7g}"),
]
# field -> the line and the place it has in the printer's block
BLOCK = {
    "AD": ("A", 0), "AM": ("A", 1), "AY": ("A", 2), "D": ("A", 3), "M": ("A", 4),
    "H": ("B", 0), "FS": ("B", 1), "H0": ("B", 2), "HR": ("B", 3),
    "W": ("C", 0), "TM": ("C", 1), "PP": ("C", 2), "AR": ("C", 3), "AS": ("C", 4),
    "PF": ("D", 0), "I2": ("D", 1), "I3": ("D", 2),
    "I4": ("E", 0), "I5": ("E", 1), "I6": ("E", 2), "I7": ("E", 3),
    "I8": ("F", 0), "MY": ("F", 1),
}
ONE = "{:d}"


def read_printer(path):
    """The printer's lines, nine to a day, as {letter: [values]}."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    days = []
    for i in range(0, len(lines) - 8, 9):
        block = {}
        for line in lines[i:i + 9]:
            m = re.match(r"^([A-I])\s?(.*)$", line)
            assert m, line
            block[m.group(1)] = m.group(2)
        assert len(block) == 9, lines[i:i + 9]
        days.append(block)
    return days


def read_rebuild(path):
    """The rebuild's own trace: one line per day, space-separated cells."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        rows.append(line.split(" "))
    return rows


def as_printed(value, spec):
    """The value as the rebuild prints it, so the two are compared as printed."""
    number = float(value)
    if "d" in spec and number == int(number):
        return spec.format(int(number))
    return spec.format(number)


def compare(days, rows):
    """The differences between the original's days and the rebuild's, if any."""
    wrong = []
    for day, (block, cells) in enumerate(zip(days, rows), start=1):
        for name, spec in SPECS:
            letter, place = BLOCK[name]
            want = as_printed(block[letter].split(",")[place], spec)
            got = cells[SPECS.index((name, spec))]
            if want != got:
                wrong.append(f"day {day}: {name}: original {want!r}, rebuild {got!r}")
        for letter, place in (("G", 23), ("H", 24)):
            want = "[" + ",".join(str(int(float(v))) for v in block[letter].split(",")) + "]"
            if want != cells[place]:
                wrong.append(f"day {day}: {letter}: original {want!r}, rebuild {cells[place]!r}")
        want = "".join(f"{int(float(v)):02x}" for v in block["I"].split(","))
        if want != cells[26]:
            wrong.append(f"day {day}: seed bytes: original {want!r}, rebuild {cells[26]!r}")
    return wrong


def test_the_rebuild_matches_the_original_on_every_day(tmp_path):
    """Seed 10,190: every logged value of every day agrees with the original."""
    trace = tmp_path / "rebuild.txt"
    done = subprocess.run(
        [sys.executable, "-m", "oregon", "--preset", "--demo", "--seed", "10190",
         "--num", "exact", "--trace", str(trace), "--data", str(tmp_path / "data")],
        cwd=ROOT, capture_output=True, text=True, timeout=1800)
    assert done.returncode == 0, done.stderr[-800:]
    rows = read_rebuild(trace)
    days = read_printer(TRACE)
    assert len(rows) == len(days) == 196, (len(rows), len(days))

    wrong = compare(days, rows)
    assert not wrong, "\n".join(wrong[:20])


def test_the_rebuild_matches_the_original_on_the_game_that_ends_in_a_grave(tmp_path):
    """Seed 1,234: the party dies on 6 September 1848, after Fort Walla Walla.

    This trace is not in the repository yet. It is recorded the same way as the
    other one: the original game runs in LinApple with the instrumented disk
    images, which print the day's values to the printer in slot 1, and the
    printer's file is copied here as ``trace_1234.printer.txt``. LinApple
    truncates its printer file when it opens it, so the run must be the only
    one in that session.
    """
    other = DATA / "trace_1234.printer.txt"
    if not other.is_file():
        pytest.skip("the trace of seed 1,234 has not been recorded yet")
    trace = tmp_path / "rebuild.txt"
    done = subprocess.run(
        [sys.executable, "-m", "oregon", "--preset", "--demo", "--seed", "1234",
         "--num", "exact", "--trace", str(trace), "--data", str(tmp_path / "data")],
        cwd=ROOT, capture_output=True, text=True, timeout=1800)
    assert done.returncode == 0, done.stderr[-800:]
    rows = read_rebuild(trace)
    days = read_printer(other)
    assert len(rows) == len(days) == 158, (len(rows), len(days))
    wrong = compare(days, rows)
    assert not wrong, "\n".join(wrong[:20])
