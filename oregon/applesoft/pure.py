"""Pure-Python Applesoft arithmetic: the fast path, held equal to the ROM.

Same algorithms as :mod:`oregon.applesoft.rom`, in Python, so a whole game can be
simulated quickly. The test suite compares the two operand by operand and treats
the ROM as the authority; if they ever disagree the Python side is the one that
is wrong.

The algorithms are the ROM's:

* **addition and subtraction** align the smaller operand by shifting it right and
  *discard* what falls below the guard bit -- the paper's "alignment loses
  bits: one extension byte, with bits beyond it dropped";
* **multiplication** is shift-and-add over a four-byte accumulator, like
  ``FMULTT`` at ``$E982``, then normalises;
* **division** is shift-and-subtract, like ``FDIVT`` at ``$EA69``;
* every result is rounded by ``ROUND.FAC`` at ``$EB72``, which adds one to the
  significand when the guard is 80 or more, carrying into the exponent. A result
  only reaches a variable after that, which is why rounding happens here.

**The working representation.** A value is ``(sign, exponent, s)`` where ``s`` is
a 33-bit integer: bit 32 is the top of the significand and bit 0 is the single
guard bit, so ``value = -sign * (s >> 1) * 2 ** exponent`` and
``exponent = byte0 - 160``. Thirty-three bits is exactly Applesoft's working
precision -- 32 significand bits plus one guard bit -- which is the whole reason
this agrees with the ROM: a wider internal mantissa would round from a different
bit.

Decimal literals accumulate digits with multiply-by-ten and add, then divide by
ten per fractional digit, rounding at each step, as the ROM does. ``0.8`` is
therefore exactly what the ROM's conversion produces, which the paper insists is
not necessarily the nearest representable value. ``0.8`` comes out as
``80 4C CC CC CD`` and ``0.2`` as ``7E 4C CC CC CD``, both classic.
"""

from __future__ import annotations

from .fac import Fac

__all__ = ["PureBackend", "format_applesoft", "OverflowArithmetic"]

BITS = 33                       # significand (32) plus one guard bit
TOP = 1 << (BITS - 1)           # 2**32
MASK33 = (1 << BITS) - 1
INT_OVERFLOW = 6                # Applesoft's OVERFLOW error number


class OverflowArithmetic(Exception):
    """A result that leaves the 5-byte format. Applesoft calls this error 6."""


def _to33(v: Fac):
    """``(sign, exponent, s)`` for a stored value; ``s == 0`` when zero.

    A stored value is ``word * 2 ** (byte0 - 160)`` and the working form shifts
    the significand up one place to make room for the guard bit, so ``s`` is
    ``word << 1`` and the exponent is unchanged.
    """
    if v.is_zero():
        return 0, 0, 0
    word = v.word() | 0x80000000
    return (1 if v.is_negative() else 0), v.exponent_byte() - 160, word << 1


def _from33(neg: int, e: int, s: int) -> Fac:
    """Assemble a value, applying ROUND.FAC and the format's limits."""
    if s == 0:
        return Fac(bytes(5))
    word = s >> 1               # the 32 stored significand bits
    if s & 1:                   # ROUND.FAC: the guard was 80 or more
        word += 1
        if word > 0xFFFFFFFF:  # the increment carried out of the top
            word >>= 1
            e += 1
    exp_byte = e + 160
    if exp_byte <= 0:
        return Fac(bytes(5))   # underflow: the format has no denormals
    if exp_byte > 255:
        raise OverflowArithmetic("Apple IIe floating point overflow")
    word &= 0xFFFFFFFF
    return Fac(bytes((exp_byte, (0x80 if (neg & 1) else 0x00) | ((word >> 24) & 0x7F),
                      (word >> 16) & 0xFF, (word >> 8) & 0xFF, word & 0xFF)))


def _norm(neg: int, e: int, s: int):
    """Shift until ``s`` has exactly 33 bits, adjusting the exponent."""
    if s == 0:
        return (0, 0, 0)
    b = s.bit_length()
    if b < BITS:
        sh = BITS - b
        s <<= sh
        e -= sh
    elif b > BITS:
        sh = b - BITS
        s >>= sh                  # truncation: the guard keeps bit sh of t
        e += sh
    return (neg, e, s)


class PureBackend:
    """Applesoft arithmetic in Python. See :mod:`oregon.applesoft.rom`."""

    name = "pure-python"
    is_rom = False

    def __init__(self):
        self._seed = bytes(5)

    # ------------------------------------------------------------- sign help
    def neg(self, a: Fac) -> Fac:
        if a.is_zero():
            return a
        b = bytearray(a.raw())
        b[1] ^= 0x80
        return Fac(bytes(b))

    def abs_(self, a: Fac) -> Fac:
        return self.neg(a) if a.is_negative() else a

    # ------------------------------------------------- guard-carrying arithmetic
    def add_g(self, a: Fac, b: Fac):
        """``FADDT`` at ``$E7C1``, returning ``(sign, exponent, s33)``."""
        na, ea, ma = _to33(a)
        nb, eb, mb = _to33(b)
        if ma == 0:
            return (nb, eb, mb)
        if mb == 0:
            return (na, ea, ma)
        if na != nb:
            # opposite signs: subtract the smaller magnitude from the larger
            if ea < eb:
                ea, eb, ma, mb = eb, ea, mb, ma
                na ^= 1
            d = ea - eb
            if d >= BITS + 1:
                return (na, ea, ma)
            if d:
                mb >>= d
            return _norm(na, ea, ma - mb)
        # Same sign: add the magnitudes, aligning the smaller by shifting it right
        # and discarding what falls below the guard bit. After the swap ea is the
        # larger exponent, so the sum is expressed at ea.
        if ea < eb:
            ea, eb, ma, mb = eb, ea, mb, ma
        d = ea - eb
        if d >= BITS + 1:
            return (na, ea, ma)
        if d:
            mb >>= d
        t = ma + mb
        if t > MASK33:               # carried out of the top: shift down one
            t >>= 1                  # the bit that falls off is the guard's
            ea += 1                  # neighbour and the exponent takes a step
        return _norm(na, ea, t)

    def sub_g(self, a: Fac, b: Fac):
        """``FSUBT`` at ``$E7AA``: complement the sign, then add."""
        return self.add_g(a, self.neg(b))

    def mul_g(self, a: Fac, b: Fac):
        """``FMULTT`` at ``$E982``: shift-and-add, truncated to 33 bits."""
        na, ea, ma = _to33(a)
        nb, eb, mb = _to33(b)
        if ma == 0 or mb == 0:
            return (0, 0, 0)
        t = ma * mb
        k = t.bit_length() - BITS
        if k < 0:
            k = 0
        s = t >> k
        guard = (t >> (k - 1)) & 1 if k else 0
        s = (s & ~1) | guard
        # (s >> 1) * 2**e must equal (ma/2 * mb/2) * 2**(ea+eb) = t * 2**(ea+eb-2)
        return _norm(na ^ nb, ea + eb + k - 1, s)

    def div_g(self, a: Fac, b: Fac):
        """``FDIVT`` at ``$EA69``: shift-and-subtract, truncated to 33 bits."""
        na, ea, ma = _to33(a)
        nb, eb, mb = _to33(b)
        if mb == 0:
            raise ZeroDivisionError("Apple IIe: division by zero")
        if ma == 0:
            return (0, 0, 0)
        t = (ma << BITS) // mb
        if t == 0:
            return (0, 0, 0)
        # value = (t / 2**BITS) * 2**(ea - eb), expressed at (t >> 1)
        return _norm(na ^ nb, ea - eb - (BITS - 1), t)

    # ------------------------------------------------- rounded public methods
    def add(self, a: Fac, b: Fac) -> Fac:
        n, e, s = self.add_g(a, b)
        return _from33(n, e, s)

    def sub(self, a: Fac, b: Fac) -> Fac:
        n, e, s = self.add_g(a, self.neg(b))
        return _from33(n, e, s)

    def mul(self, a: Fac, b: Fac) -> Fac:
        n, e, s = self.mul_g(a, b)
        return _from33(n, e, s)

    def div(self, a: Fac, b: Fac) -> Fac:
        n, e, s = self.div_g(a, b)
        return _from33(n, e, s)

    # -------------------------------------------------- constant-operand forms
    def add_const(self, a: Fac, b: Fac) -> Fac:
        return self.add(a, b)

    def mul_const(self, a: Fac, b: Fac) -> Fac:
        return self.mul(a, b)

    def div_const(self, a: Fac, b: Fac) -> Fac:
        return self.div(a, b)

    # ------------------------------------------------------------------ INT
    def int_(self, a: Fac) -> Fac:
        """``INT`` floors. ``$EC23`` converts toward zero, then adjusts the sign."""
        if a.is_zero():
            return a
        n = a.to_int()
        # INT floors: when the value is negative and not already whole, step down.
        if a.is_negative() and n != a.to_float():
            n -= 1
        return Fac.from_int(n)

    def round_fac(self, a: Fac) -> Fac:
        """With no guard bit held there is nothing to add; a no-op."""
        return a

    # ------------------------------------------------------------ comparison
    def cmp(self, a: Fac, b: Fac) -> int:
        """Exact byte comparison, -1 / 0 / 1. No tolerance, ever."""
        x, y = a.raw(), b.raw()
        if x == y:
            return 0
        if x[0] == 0:
            return 1 if (y[1] & 0x80) else -1
        if y[0] == 0:
            return -1 if (x[1] & 0x80) else 1
        sx, sy = x[1] & 0x80, y[1] & 0x80
        if sx != sy:
            return -1 if sx else 1
        mx = (x[0] << 31) | (int.from_bytes(x[1:5], "big") & 0x7FFFFFFF)
        my = (y[0] << 31) | (int.from_bytes(y[1:5], "big") & 0x7FFFFFFF)
        if mx == my:
            return 0
        # For a negative value the larger magnitude is the smaller number, so the
        # answer is the other way round.
        less = mx < my
        return (1 if less else -1) if sx else (-1 if less else 1)

    # ------------------------------------------------------------------ RND
    def set_seed(self, seed: bytes):
        if len(seed) != 5:
            raise ValueError("the Applesoft RND seed is five bytes")
        self._seed = bytes(seed)

    def get_seed(self) -> bytes:
        return self._seed

    def rnd(self, arg: Fac) -> Fac:
        """``RND`` at ``$EFAE``, reproduced from the ROM's own bytes."""
        from .rng import applesoft_rnd
        return applesoft_rnd(self, arg)

    # -------------------------------------------------------------- literals
    def from_str(self, s: str) -> Fac:
        """A decimal literal, converted the way the ROM converts one."""
        t = s.strip()
        if not t:
            return Fac(bytes(5))
        neg = False
        i = 0
        if t[0] in "+-":
            neg = t[0] == "-"
            i = 1
        digits = []
        frac = 0
        dot = False
        while i < len(t):
            c = t[i]
            if c.isdigit():
                digits.append(ord(c) - 48)
                if dot:
                    frac += 1
            elif c == "." and not dot:
                dot = True
            else:
                break
            i += 1
        if not digits:
            return Fac(bytes(5))
        ten = Fac.from_int(10)
        v = Fac(bytes(5))
        for d in digits:
            v = self.mul(v, ten)
            v = self.add(v, Fac.from_int(d))
        for _ in range(frac):
            v = self.div(v, ten)
        return self.neg(v) if neg else v

    # ------------------------------------------------------------ formatting
    def fmt_body(self, v: Fac) -> str:
        return format_applesoft(v)

    def str_(self, v: Fac) -> str:
        return ("-" if v.is_negative() else " ") + format_applesoft(v)


def format_applesoft(v: Fac) -> str:
    """Applesoft's number to text, **without** the leading sign column.

    ``Fac.str_`` puts the sign column in front of this, so that is where the sign
    belongs; returning it here as well would double it for a negative value.

    **Not validated against the ROM** -- see ``GAPS.md``. These are the rules the
    Applesoft manual states: at most nine significant digits, no trailing zeros in
    the fraction, no decimal point on a whole number, a leading zero for a value
    below one, and exponential notation once the decimal point would fall outside
    the printed field. The game's own money text does not come through here --
    that is :func:`oregon.applesoft.fac.str_dollar_int`, which reproduces the
    ``INT (V * 100 + .5)`` pattern exactly -- so what remains here is the handful
    of places that print a quantity such as the pounds of food held.
    """
    if v.is_zero():
        return "0"
    m = v.word() | 0x80000000
    e = v.exponent_byte() - 160            # value == m * 2**e
    # the power of two of the leading digit, and from it the decimal exponent
    p2 = m.bit_length() - 1 + e
    dexp = int(p2 * 0.30102999566398120)
    # correct the estimate: 10**dexp must be at most the value, and the value must
    # be less than 10**(dexp + 1)
    while _ten_cmp(m, e, dexp) < 0:
        dexp -= 1
    while _ten_cmp(m, e, dexp + 1) >= 0:
        dexp += 1
    digits = []
    mm, ee = m, e
    for _ in range(12):
        shift = ee if ee >= 0 else -ee
        d = mm >> shift if shift < 96 else 0
        digits.append(d)
        rem = mm - (d << shift) if shift < 96 else mm
        if rem == 0:
            break
        mm = rem * 10
        while mm.bit_length() > 48:
            mm >>= 4
            ee += 4
    # The digits run from 10**dexp downwards, so a leading zero is the integer
    # part of a fraction rather than a significant digit, and trailing zeros were
    # cut by the nine-digit limit rather than by the value.
    while len(digits) > 1 and digits[0] == 0:
        digits.pop(0)
    if len(digits) > 9:
        digits = digits[:9]           # at most nine significant digits
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
    s = "".join(str(d) for d in digits)
    if -9 <= dexp <= 8:
        # Applesoft prints a fraction without its leading zero: PRINT .5 shows .5
        if dexp < 0:
            return "." + "0" * (-dexp - 1) + s
        if len(s) > dexp + 1:
            return s[:dexp + 1] + "." + s[dexp + 1:]
        return s
    mant = s[0] + ("." + s[1:] if len(s) > 1 else "")
    return f"{mant}E{'+' if dexp >= 0 else '-'}{abs(dexp)}"


def _ten_cmp(m: int, e: int, dexp: int) -> int:
    """Compare ``m * 2**e`` with ``10 ** dexp``; -1, 0 or 1.

    Exact, by turning both sides into integer fractions and cross-multiplying.
    Only the *sign* is wanted here, so no float ever touches the answer.
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
