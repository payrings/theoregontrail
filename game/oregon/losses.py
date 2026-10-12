"""Re-export of the loss routines, so the river and the raft can share them.

The raft at ``FLOAT`` 700-710 uses the same three routines as ``RIVER.LIB`` with
different chances -- the shore takes people two times in thirteen and goods half the
time, a rock six times in ten for people and oxen and seven in ten for goods -- so
they live here rather than in the river.
"""

from __future__ import annotations

from .river import _lose_goods, _lose_oxen, _lose_people
from .lf import _line

__all__ = ["lose_goods", "lose_oxen", "lose_people", "line"]

lose_goods = _lose_goods
lose_oxen = _lose_oxen
lose_people = _lose_people
line = _line
