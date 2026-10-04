"""A day-by-day trace, in the form the paper says a reference trace should take.

Appendix H says a useful trace records, for each day: the date, ``D``, ``M``,
``H``, ``FS``, ``H0``, ``HR``, ``W``, ``TM``, ``PP``, ``AR``, ``AS``, ``PF``, the
inventory ``I(2)`` to ``I(8)``, ``MY``, ``H1()``, ``H2()``, any event fired, and the
five seed bytes at ``C9`` to ``CD`` in hexadecimal. The seed bytes are the point:
they make a missing or an extra ``RND`` draw visible on the day it happens, which is
the one thing that can be checked before any real trace exists.

No reference traces exist yet (Appendix H), so nothing here is compared with a real
run. When one is recorded from an emulator, this output is what it should be
compared against. Note that the seed bytes are the *emulated* Applesoft seed at
``$C9``, which the arithmetic backend holds.
"""

from __future__ import annotations

from . import num

__all__ = ["Tracer", "FIELDS"]

FIELDS = ("AD", "AM", "AY", "D", "M", "H", "FS", "H0", "HR", "W", "TM", "PP",
          "AR", "AS", "PF", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "MY",
          "H1", "H2", "EVENT", "SEED")


class Tracer:
    """Writes one line per game day, plus a line for anything notable."""

    def __init__(self, path=None, stream=None):
        self.path = path
        self.stream = stream
        self.days = 0
        self.events = 0
        self._fh = None
        if path is not None:
            self._fh = open(path, "w", encoding="utf-8")
        self._header_written = False

    # ------------------------------------------------------------------ core
    def _write(self, line: str):
        if self._fh is not None:
            if not self._header_written:
                self._fh.write("# " + " ".join(FIELDS) + "\n")
                self._header_written = True
            self._fh.write(line + "\n")
            self._fh.flush()
        if self.stream is not None:
            self.stream.write(line + "\n")

    def day(self, st, event: str = "", stopped: bool = False):
        """One line for one day of the daily cycle."""
        self.days += 1
        self._write(self.line(st, event, stopped))

    def line(self, st, event: str = "", stopped: bool = False) -> str:
        f = num.as_float
        # no spaces inside the brackets, so each list is one column and the
        # line has exactly one cell per name in FIELDS
        h1 = ",".join(str(num.as_int(st.H1[i])) for i in range(5))
        h2 = ",".join(str(num.as_int(st.H2[i])) for i in range(5))
        cells = [
            f"{num.as_int(st.AD):02d}",
            f"{num.as_int(st.AM):02d}",
            str(num.as_int(st.AY)),
            f"{f(st.D):.4g}",
            f"{f(st.M):.5g}",
            f"{f(st.H):.6g}",
            f"{f(st.FS):.6g}",
            str(num.as_int(st.H0)),
            str(num.as_int(st.HR)),
            str(num.as_int(st.W)),
            str(num.as_int(st.TM)),
            str(num.as_int(st.PP)),
            f"{f(st.AR):.6g}",
            f"{f(st.AS):.6g}",
            f"{f(st.PF):.7g}",
            f"{f(st.I[2]):.6g}",
            f"{f(st.I[3]):.6g}",
            f"{f(st.I[4]):.8g}",
            str(num.as_int(st.I[5])),
            str(num.as_int(st.I[6])),
            str(num.as_int(st.I[7])),
            f"{f(st.I[8]):.8g}",
            f"{f(st.MY):.7g}",
            f"[{h1}]",
            f"[{h2}]",
            (event or "-") + ("+" if stopped else ""),
            seed_bytes(),
        ]
        return " ".join(cells)

    def note(self, text: str):
        """Anything that is not a day: an event, a screen, a handler."""
        self._write("# " + text)

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None


def seed_bytes() -> str:
    """The five Applesoft RND seed bytes, in hexadecimal."""
    from .applesoft import fac
    try:
        return fac._b().get_seed().hex()
    except Exception:                          # noqa: BLE001
        return "--------"
