"""The objects a running game passes around: state, randomness, screen, files.

The BASIC passes them the way the hardware does -- through memory, through
``& APP``-ed libraries that share every variable -- so here they are one object
that every module takes. :class:`Context` holds:

``st``
    the state, named as the BASIC variables are (:mod:`oregon.state`);
``rng``
    the random interface (:mod:`oregon.rng`);
``ui``
    the screen and keyboard (:mod:`oregon.ui`);
``files``
    ``HISCORE.SEQ`` and ``TOMB.SEQ`` (:mod:`oregon.files`);
``mem``
    the byte memory the programs hand over through (:mod:`oregon.mem`);
``trace``
    the day-by-day log (:mod:`oregon.trace`).
"""

from __future__ import annotations

from .files import Files
from .mem import Memory
from .rng import SeededRnd
from .state import State
from .trace import Tracer
from .ui import TerminalUI

__all__ = ["Context", "new_game"]


class Context:
    def __init__(self, ui=None, rng=None, files=None, mem=None, trace=None,
                 data_dir="data"):
        self.ui = ui if ui is not None else TerminalUI()
        self.rng = rng if rng is not None else SeededRnd()
        self.files = files if files is not None else Files(data_dir)
        self.mem = mem if mem is not None else Memory()
        self.trace = trace if trace is not None else Tracer()
        self.st = State()
        self.program = "OREGON TRAIL"      # PN$, for the error handler
        self.quit = False
        self.outcome = None                # set when the game ends

    def set_program(self, name: str):
        self.mem.program = name
        self.program = name


def new_game(**kw) -> Context:
    return Context(**kw)
