"""The rebuild's formulas against the real Applesoft interpreter.

``tests/data/fidelity.json`` was recorded by running the listing's own statements on
the Apple IIe ROM's BASIC interpreter (see ``fidelity_cases.py``). For every case the
rebuild's code is given the same inputs and must produce the same five bytes.

Each group is a place where the arithmetic is easy to get subtly wrong: the order of
the operands, whether a value has been stored in a variable before it is used, and
whether the working value is rounded at the right moment. Those are the mistakes the
review found (the findings B1, B2 and the unstored ``Z`` of line 3244), and none of
them shows up as a wrong-looking number, only as a last digit that differs.
"""
import json
import pathlib

import pytest

from oregon import applesoft

import fidelity_cases as FC

DATA = pathlib.Path(__file__).resolve().parent / "data" / "fidelity.json"
pytestmark = pytest.mark.skipif(
    not applesoft.rom_available() or not DATA.is_file(),
    reason="the recorded cases are checked on the ROM backend only")


def _doc():
    return json.loads(DATA.read_text())["groups"]


def test_every_group_has_recorded_cases():
    recorded = _doc()
    assert set(recorded) == set(FC.GROUPS), (
        "regenerate tests/data/fidelity.json: "
        f"{set(recorded) ^ set(FC.GROUPS)}")
    for name, g in recorded.items():
        assert len(g["cases"]) >= 40, name


@pytest.mark.parametrize("name", sorted(FC.GROUPS))
def test_the_code_matches_the_interpreter(name):
    g = _doc()[name]
    run = FC.GROUPS[name]["run"]
    wrong = []
    for case in g["cases"]:
        inputs = {k: FC.fac_from_hex(v) for k, v in case["in"].items()}
        got = run(inputs)
        for k, want in case["out"].items():
            have = FC.hexof(got[k])
            if have != want:
                wrong.append((k, want, have, case["in"]))
    assert not wrong, f"{len(wrong)} of {len(g['cases'])} differ; first: {wrong[0]}"
