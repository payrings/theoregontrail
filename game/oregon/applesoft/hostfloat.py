"""Host floating point: the arithmetic a straightforward port would use.

Two backends for the experiment of paper section 12.8, which asks how close a
port that does *not* emulate Applesoft's arithmetic comes to the ROM's.

``float``
    Python's 64-bit floats, with nothing else changed: literals are read by
    ``float()``, every result keeps its 53-bit significand, ``INT`` is
    ``math.floor`` and comparisons are exact. The generator, the evaluation of
    both sides of ``AND`` and ``OR``, and the ``FOR`` rule are the game's own and
    are kept, because they belong to the program, not to the arithmetic.

``rounded``
    The same, with one change: every result, and every literal, is rounded to
    Applesoft's precision, a 32-bit significand, half up, and to its exponent
    range (half away from zero). This is the kind of small adjustment a port can
    make in any language with one helper function, without emulating the ROM's
    routines.

Neither carries an extension byte, and neither reproduces the ROM's truncation
during alignment or its multiply loop: that is the point of the comparison.
"""

from __future__ import annotations

import math

from .fac import Fac

__all__ = ["FloatBackend", "RoundedFloatBackend", "to_fac", "applesoft_round"]

OVERFLOW = 69
DIVISION_BY_ZERO = 133


def _error(code: int):
    from .rom import RomError
    raise RomError(code, "Applesoft error")


def to_fac(x: float) -> Fac:
    """``x`` rounded to the 5-byte format: a 32-bit significand, half up."""
    if x == 0.0:
        return Fac(bytes(5))
    m, e = math.frexp(abs(x))           # abs(x) = m * 2**e, 0.5 <= m < 1
    word = math.floor(m * 4294967296.0 + 0.5)
    if word >= 1 << 32:
        word >>= 1
        e += 1
    exp_byte = e + 128
    if exp_byte <= 0:
        return Fac(bytes(5))
    if exp_byte > 255:
        _error(OVERFLOW)
    sign = 0x80 if x < 0 else 0x00
    return Fac(bytes((exp_byte, sign | ((word >> 24) & 0x7F), (word >> 16) & 0xFF,
                      (word >> 8) & 0xFF, word & 0xFF)))


def applesoft_round(x: float) -> float:
    """The helper a port needs: ``x`` at Applesoft's precision, as a host float."""
    return to_fac(x).to_float()


class FloatFac(Fac):
    """A value that carries a host float. ``b`` holds it rounded to five bytes,
    for the few places that read bytes (the ``RND`` argument, hashing)."""

    __slots__ = ("f",)

    def __init__(self, f: float):
        try:
            b = to_fac(f).b
        except Exception:               # beyond the 5-byte range: keep a marker
            b = bytes((255, 0x80 if f < 0 else 0, 255, 255, 255))
        super().__init__(b)
        self.f = f

    def to_float(self) -> float:
        return self.f

    def to_int(self) -> int:
        return int(self.f)              # toward zero, as Fac.to_int

    def is_zero(self) -> bool:
        return self.f == 0.0

    def is_negative(self) -> bool:
        return self.f < 0.0

    def raw(self) -> bytes:
        return self.b

    def __repr__(self) -> str:
        return f"FloatFac({self.f!r})"


def _f(v: Fac) -> float:
    return v.to_float()


class FloatBackend:
    """Plain 64-bit floats."""

    name = "host-float"
    is_rom = False

    def __init__(self):
        self._seed = bytes(5)

    def _make(self, x: float) -> Fac:
        if math.isinf(x) or math.isnan(x):
            _error(OVERFLOW)
        return FloatFac(x)

    # ----------------------------------------------------------- operators
    def add(self, a, b):
        return self._make(_f(a) + _f(b))

    def sub(self, a, b):
        return self._make(_f(a) - _f(b))

    def mul(self, a, b):
        return self._make(_f(a) * _f(b))

    def div(self, a, b):
        if _f(b) == 0.0:
            _error(DIVISION_BY_ZERO)
        return self._make(_f(a) / _f(b))

    add_const = add
    mul_const = mul
    div_const = div

    def neg(self, a):
        return a if a.is_zero() else self._make(-_f(a))

    def abs_(self, a):
        return self.neg(a) if a.is_negative() else a

    def int_(self, a):
        return self._make(float(math.floor(_f(a))))

    def round_fac(self, a):
        return a                         # a variable holds the float as it is

    def cmp(self, a, b) -> int:
        x, y = _f(a), _f(b)
        return (x > y) - (x < y)

    # ------------------------------------------------------------------ RND
    def set_seed(self, seed: bytes):
        self._seed = bytes(seed)

    def get_seed(self) -> bytes:
        return self._seed

    def rnd(self, arg):
        from .rng import rnd
        value, seed = rnd(bytes(self._seed), bytes(to_fac(_f(arg)).b))
        self._seed = seed
        return self._make(Fac(value).to_float())

    # --------------------------------------------------------------- strings
    def from_str(self, s: str):
        t = s.strip()
        return self._make(float(t) if t else 0.0)

    def fmt(self, v) -> str:
        return format_applesoft(to_fac(_f(v)))


class RoundedFloatBackend(FloatBackend):
    """64-bit floats, with every result rounded to Applesoft's precision."""

    name = "rounded-float"

    def _make(self, x: float) -> Fac:
        if math.isinf(x) or math.isnan(x):
            _error(OVERFLOW)
        return to_fac(x)


# ----------------------------------------------------------------- text
def format_applesoft(v: Fac) -> str:
    """Applesoft's number to text, as ``FOUT`` ($ED34) builds it.

    A positive number has **no** leading space and a negative one a leading ``-``;
    that is the text ``STR$`` returns and ``PRINT`` shows. The value is rounded to
    nine significant digits (half up), trailing zeros are dropped, a whole number has
    no decimal point, and a fraction has no leading zero. A value whose rounded form
    lies from 0.01 up to but not including 1E+9 is written in full; anything else
    is written as a mantissa, ``E``, a sign and at least two digits of exponent, for
    example ``1.2E-03`` and ``1E+09``.

    The ROM scales the value by repeated multiplication or division by ten in its
    own floating point before it rounds; this works from the exact binary value, so
    it can differ from the ROM in the ninth digit for a value that needs more than
    nine to write. For the game's values -- whole numbers and quantities with a few
    decimals -- the two agree. The ``exact`` backend transcribes FOUT itself.
    """
    if v.is_zero():
        return "0"
    m = v.word() | 0x80000000
    e = v.exponent_byte() - 160            # value == m * 2**e, exactly
    # the exact value as a fraction, then 9 significant digits of it
    if e >= 0:
        num_, den = m << e, 1
    else:
        num_, den = m, 1 << (-e)
    # decimal exponent of the leading digit: 10**d10 <= value < 10**(d10 + 1)
    d10 = len(str(num_ // den)) - 1 if num_ >= den else -len(str((den + num_ - 1) // num_)) 
    while _ten_cmp(m, e, d10) < 0:
        d10 -= 1
    while _ten_cmp(m, e, d10 + 1) >= 0:
        d10 += 1
    # scaled = value * 10**(8 - d10), rounded half up to an integer of 9 digits
    k = 8 - d10
    if k >= 0:
        n2, d2 = num_ * 10 ** k, den
    else:
        n2, d2 = num_, den * 10 ** (-k)
    scaled = (2 * n2 + d2) // (2 * d2)
    if scaled >= 10 ** 9:                   # rounding carried into a tenth digit
        scaled //= 10
        d10 += 1
    digits = str(scaled).rstrip("0") or "0"
    sign = "-" if v.is_negative() else ""
    if -2 <= d10 <= 8:
        if d10 < 0:
            return sign + "." + "0" * (-d10 - 1) + digits
        if len(digits) <= d10 + 1:
            return sign + digits + "0" * (d10 + 1 - len(digits))
        return sign + digits[:d10 + 1] + "." + digits[d10 + 1:]
    mant = digits[0] + ("." + digits[1:] if len(digits) > 1 else "")
    return f"{sign}{mant}E{'+' if d10 >= 0 else '-'}{abs(d10):02d}"


def _ten_cmp(m: int, e: int, dexp: int) -> int:
    """Compare ``m * 2**e`` with ``10 ** dexp``; -1, 0 or 1.

    Exact, by turning both sides into integer fractions and cross-multiplying.
    """
    if e >= 0:
        lnum, lden = m << e, 1
    else:
        lnum, lden = m, 1 << (-e)
    if dexp >= 0:
        rnum, rden = 10 ** dexp, 1
    else:
        rnum, rden = 1, 10 ** (-dexp)
    a = lnum * rden
    b = rnum * lden
    return (a > b) - (a < b)
