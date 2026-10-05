"""The terminal input path, exercised through a pty.

This is the regression test for "the keyboard is unresponsive". Two bugs lived
there, both intermittent:

* ``tty.setcbreak`` sets the terminal with ``TCSAFLUSH``, which **discards pending
  input** -- so a key pressed while the game was drawing was thrown away.
* prompts read a single character and then raced to *drain* the Return that ended
  them; the next prompt was handed a bare Return instead, rejected it, and every
  answer arrived one prompt late.

Skipped if a pty cannot be opened or the game will not start, so the suite stays
usable where it cannot.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

pty_check = pytest.importorskip("pty_check")


@pytest.fixture
def pty_dir(tmp_path):
    return str(tmp_path / "data")


def test_a_game_can_be_typed_at_through_a_terminal(pty_dir):
    problems = pty_check.check(verbose=False, data=pty_dir)
    assert not problems, "\n".join(problems)
