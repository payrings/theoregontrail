"""The random-number interface, and the discipline that goes with it.

Every draw of ``RND`` in the game goes through an object of this kind, so that the
number and order of draws can be checked. Appendix G lists every draw the BASIC
code makes; three rules apply everywhere and are enforced by review and by
``tests/test_rng.py``:

* exactly the draws Appendix G lists, in the same order, including the ones whose
  result the original throws away;
* no draw added, removed, merged or reordered;
* **Applesoft has no short-circuit evaluation**, so a draw on the right of ``AND``
  or ``OR`` always happens. ``IF X AND RND (1) < V`` draws even when ``X`` is
  false -- ``LF.LIB`` 50000 and 50205 and ``FLOAT`` 1070 all do this -- and
  ``PART.LIB`` 42010 draws whether or not the player agreed to repair the wagon.

The hunting module has its **own** generator (paper 11.1, Appendix G.6) and never
advances the Applesoft seed; see :mod:`oregon.hunt`.
"""

from __future__ import annotations

from . import num
from .applesoft.fac import Fac

__all__ = ["Rnd", "SeededRnd", "ScriptedRnd", "CountingRnd", "DrawLog"]


class DrawLog:
    """A record of every draw, for the tests that check Appendix G."""

    __slots__ = ("entries",)

    def __init__(self):
        self.entries = []

    def note(self, tag: str, arg: Fac, value: Fac):
        self.entries.append((tag, arg.raw(), value.raw()))

    def clear(self):
        self.entries.clear()

    def tags(self):
        return [e[0] for e in self.entries]

    def count(self, tag: str | None = None) -> int:
        if tag is None:
            return len(self.entries)
        return sum(1 for e in self.entries if e[0] == tag)

    def since(self, mark: int):
        return self.entries[mark:]

    def __len__(self):
        return len(self.entries)


class Rnd:
    """The interface: ``rnd(arg)`` returns a Fac, and ``log`` records everything."""

    def __init__(self):
        self.log = DrawLog()

    # --- the three calls the game makes ----------------------------------
    def rnd1(self, tag: str = "") -> Fac:
        """``RND (1)``, the form the game uses everywhere."""
        v = self.rnd(num.ONE)
        self.log.note(tag or "RND(1)", num.ONE, v)
        return v

    def rnd(self, arg: Fac) -> Fac:
        """``RND (arg)``. A negative argument reseeds, as MENU 1015 does."""
        raise NotImplementedError

    def seed_from_keyboard(self, counter: int) -> Fac:
        """``Z = RND ( - (PEEK (78) + PEEK (79) * 256))``, MENU 1015.

        The argument is the 16-bit counter the keyboard routine keeps while it waits
        for a key, so the seed is fixed by how long the player took to press it.
        This is the only reseeding in the game.
        """
        return self.rnd(num.neg(num.parse(str(counter))))

    # --- convenience for the test harness ---------------------------------
    def below(self, tag: str, chance: Fac) -> bool:
        """``IF RND (1) < CHANCE THEN`` -- always one draw."""
        return num.lt(self.rnd1(tag), chance)

    def int_range(self, tag: str, n: int) -> int:
        """``INT (RND (1) * n)`` -- always one draw."""
        return num.trunc(num.mul(self.rnd1(tag), num.parse(str(n))))

    def int_span(self, tag: str, lo: int, hi: int) -> int:
        """``INT (RND (1) * (hi - lo + 1)) + lo`` -- one draw."""
        return lo + num.trunc(num.mul(self.rnd1(tag), num.parse(str(hi - lo + 1))))


class SeededRnd(Rnd):
    """The default: the emulated ROM's own ``RND``, with its five seed bytes.

    The seed bytes live in the arithmetic backend's memory, so the sequence is the
    original's, and the hunt's separate generator cannot disturb it.
    """

    def __init__(self):
        super().__init__()
        self.backend = num._fac._b()

    def rnd(self, arg: Fac) -> Fac:
        return self.backend.rnd(arg)

    @property
    def seed(self) -> bytes:
        return self.backend.get_seed()

    @seed.setter
    def seed(self, value: bytes):
        self.backend.set_seed(value)


class ScriptedRnd(Rnd):
    """Returns values from a list, for tests. Exhaustion is an error, not a wrap.

    A draw that runs off the end of the list means the game asked for more numbers
    than Appendix G says it should, which is exactly the kind of mistake these tests
    exist to catch.
    """

    def __init__(self, values):
        super().__init__()
        if isinstance(values, str):
            values = [float(v) for v in values.split()]
        self.values = list(values)
        self.i = 0
        self.reseeds = []

    def rnd(self, arg: Fac) -> Fac:
        if self.i >= len(self.values):
            raise AssertionError(
                f"ScriptedRnd ran out of values at draw {self.i}; the game asked "
                f"for more numbers than Appendix G lists")
        v = self.values[self.i]
        self.i += 1
        if arg.is_negative():
            # a reseed: remember it, and the value that follows is the first draw
            self.reseeds.append(self.values[self.i - 1])
        return num.parse(str(v))

    @property
    def remaining(self) -> int:
        return len(self.values) - self.i


class CountingRnd(Rnd):
    """Counts draws and returns a fixed value, for checking Appendix G."""

    def __init__(self, value: float = 0.5):
        super().__init__()
        self.count = 0
        self.value = value
        self.fac = num.parse(str(value))

    def rnd(self, arg: Fac) -> Fac:
        self.count += 1
        return self.fac