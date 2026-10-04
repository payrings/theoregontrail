"""All of the game's arithmetic, behind one interface.

Nothing outside this module may call a ``math`` function or use a float literal
for game state. Every number is an :class:`~oregon.applesoft.fac.Fac`, the 5-byte
Applesoft floating-point value, and every operation goes to the backend installed
by :mod:`oregon.applesoft`, which by default is a genuine Apple IIe ROM running
under a 6502 emulator.

The functions here mirror the BASIC operators one for one, so the game code can
be read against the listing:

    ``H = .9 * H + ZT + ZC + ZF + ZP + FS + H0 + HR``   (line 3230)

becomes::

    H = num.store(num.chain(H).mul(n09).add(ZT).add(ZC).add(ZF).add(ZP)
                  .add(FS).add(H0).add(HR))

Comparisons return 1 or 0 and are used arithmetically in the original, for
example ``RE(C0) = (AS > 30)``; :func:`bool_` and :func:`int_` provide those, and
:func:`b2i` turns a comparison into the 0 or 1 the original relies on.

The paper (section 12) is explicit that nothing may use a tolerance comparison and
that the rounding points are part of the original's behaviour, which is why
:func:`store` exists: it applies ``ROUND.FAC``, the rounding Applesoft performs when
a result reaches a variable.
"""

from __future__ import annotations

from .applesoft import fac as _fac
from .applesoft.fac import Fac

__all__ = [
    "Fac", "ZERO", "ONE", "HALF", "TWO", "THREE", "FOUR",
    "parse", "int_of", "as_int", "as_float", "trunc",
    "add", "sub", "mul", "div", "neg", "abs_", "int_", "store",
    "addc", "mulc", "divc", "cmp", "eq", "lt", "le", "gt", "ge",
    "bool_", "b2i", "chain", "Chain",
    "dollar", "str_", "backend", "rom_status", "use",
]

ZERO = _fac.ZERO
ONE = _fac.ONE
HALF = _fac.HALF
TWO = _fac.TWO
THREE = _fac.THREE
FOUR = _fac.FOUR

# The constants C0 to C4 and P5, from the saved variable table (Appendix E.1).
# The programmers held them in variables because Applesoft re-converts a literal
# every time its line runs; these are those variables.
C0, C1, C2, C3, C4, P5 = ZERO, ONE, TWO, THREE, FOUR, HALF

def parse(text) -> Fac:
    """A decimal literal, converted the way the ROM converts one.

    Accepts a string so the BASIC text can be quoted verbatim in the game code,
    and an int so small constants need no quotes.
    """
    if isinstance(text, Fac):
        return text
    if isinstance(text, int):
        return _fac.from_int(text)
    return _fac.from_str(str(text))


def int_of(v: Fac) -> int:
    """The value as a Python int, truncated toward zero.

    For the places where the original uses the value as a loop bound, an array
    index or a count -- ``INT``, ``PEEK``, array subscripts -- and not as a
    quantity that is carried forward.
    """
    return v.to_int()


def as_int(v) -> int:
    return v.to_int() if isinstance(v, Fac) else int(v)


def as_float(v) -> float:
    """A host float, for tests and trace output only. Never for game state."""
    return v.to_float() if isinstance(v, Fac) else float(v)


def trunc(v: Fac) -> int:
    """``INT``, as an int. Applesoft's ``INT`` floors; so does this."""
    return _fac.int_(v).to_int()


# Literals used all over the game, parsed through the backend so that each one
# becomes exactly what the ROM's decimal conversion makes of it.
n0 = ZERO
n005 = parse(".05")
n01 = parse(".1")
n015 = parse(".15")
n02 = parse(".2")
n025 = parse(".25")
n03 = parse(".3")
n04 = parse(".04")
n05 = parse(".05")
n06 = parse(".06")
n067 = parse(".067")
n07 = parse(".07")
n08 = parse(".08")
n09 = parse(".9")
n1 = ONE
n12 = parse("1.2")
n15 = parse("1.5")
n2 = TWO
n25 = parse("2.5")
n3 = THREE
n4 = FOUR
n5 = parse("5")
n8 = parse("8")
n10 = parse("10")
n40 = parse("40")
n50 = parse("50")
n95 = parse(".95")
n105 = parse(".105")
n24 = parse("24")
n139 = parse("139")
n1600 = parse("1600")
n2000 = parse("2000")




# ------------------------------------------------------------------ operators
def add(a: Fac, b: Fac) -> Fac:
    return _fac.add(a, b)


def sub(a: Fac, b: Fac) -> Fac:
    return _fac.sub(a, b)


def mul(a: Fac, b: Fac) -> Fac:
    return _fac.mul(a, b)


def div(a: Fac, b: Fac) -> Fac:
    return _fac.div(a, b)


def neg(a: Fac) -> Fac:
    return _fac.neg(a)


def abs_(a: Fac) -> Fac:
    return _fac.abs_(a)


def int_(a: Fac) -> Fac:
    return _fac.int_(a)


def addc(a: Fac, b: Fac) -> Fac:
    """``+`` against a constant loaded by the ROM from memory ($E7BE)."""
    return _fac.add_const(a, b)


def mulc(a: Fac, b: Fac) -> Fac:
    """``*`` against a constant loaded by the ROM from memory ($E97F)."""
    return _fac.mul_const(a, b)


def divc(a: Fac, b: Fac) -> Fac:
    """``/`` against a constant loaded by the ROM from memory ($EA66)."""
    return _fac.div_const(a, b)


def store(v: Fac) -> Fac:
    """Apply ``ROUND.FAC`` and keep the five bytes a variable holds."""
    return _fac.round_fac(v)


def cmp(a: Fac, b: Fac) -> int:
    return _fac.cmp(a, b)


def eq(a: Fac, b: Fac) -> bool:
    return cmp(a, b) == 0


def lt(a: Fac, b: Fac) -> bool:
    return cmp(a, b) < 0


def le(a: Fac, b: Fac) -> bool:
    return cmp(a, b) <= 0


def gt(a: Fac, b: Fac) -> bool:
    return cmp(a, b) > 0


def ge(a: Fac, b: Fac) -> bool:
    return cmp(a, b) >= 0


def bool_(b) -> Fac:
    """``(x = 1) * 1600``: an Applesoft comparison is 1 or 0."""
    return ONE if b else ZERO


def b2i(b) -> int:
    return 1 if b else 0


# --------------------------------------------------------------------- chains
class Chain:
    """One BASIC expression, evaluated left to right with the guard byte alive.

    Applesoft keeps the extension byte between the operators of one expression
    and rounds only when the result reaches a variable, so a long sum such as
    line 3230's must not be rounded part way through. This carries the working
    value from one operator to the next and :meth:`done` applies ``ROUND.FAC``.
    The backends already keep the guard byte between calls -- in the ROM case it
    simply stays in ``$AC`` -- so nothing extra is needed here beyond the
    bookkeeping that says where one expression ends.

        >>> c = chain(H).mul(n09).add(ZT)     # .9 * H + ZT
        >>> H = c.done()                      # ROUND.FAC, then store
    """

    __slots__ = ("v",)

    def __init__(self, v: Fac):
        self.v = v

    def add(self, x: Fac) -> "Chain":
        self.v = add(self.v, x)
        return self

    def sub(self, x: Fac) -> "Chain":
        self.v = sub(self.v, x)
        return self

    def mul(self, x: Fac) -> "Chain":
        self.v = mul(self.v, x)
        return self

    def div(self, x: Fac) -> "Chain":
        self.v = div(self.v, x)
        return self

    def addc(self, x: Fac) -> "Chain":
        self.v = addc(self.v, x)
        return self

    def mulc(self, x: Fac) -> "Chain":
        self.v = mulc(self.v, x)
        return self

    def done(self) -> Fac:
        return store(self.v)


def chain(v: Fac) -> Chain:
    return Chain(v)


# ------------------------------------------------------------------- text forms
def str_(v: Fac) -> str:
    """Applesoft's ``STR$``: a leading space when the value is positive."""
    return v.str_()


def dollar(cents: int) -> str:
    """The money pattern at lines 200, 250 and the rounding routine.

    ``V = INT (V * 100 + .5)`` turns the value into a whole number of cents, and
    the text is then cut into dollars and cents with ``STR$``. The leading space
    from ``STR$`` is kept, because ``RIGHT$`` counts it, and zero comes out as the
    odd ``" 0. 0"``, which the original does print.
    """
    return _fac.str_dollar_int(cents)


def backend() -> str:
    return _fac.backend_name()


def rom_status() -> str:
    from .applesoft import rom
    return rom.describe()


def use(which: str):
    """Choose the arithmetic backend: ``"rom"`` or ``"pure"``."""
    from . import applesoft
    return applesoft.use(which)