"""The 5-byte Applesoft floating-point value, and the interface to its arithmetic.

Number format (paper section 12.1, Table 26). Five bytes::

    byte 0   exponent: the value is multiplied by 2 ** (byte0 - 128).
             A byte0 of 0 means the value is zero.
    byte 1   bit 7 is the sign (0 positive, 1 negative). The significand's
             implicit leading 1 is *not* stored; it occupies the place of the
             sign bit.
    bytes 2-4 the low 31 bits of the significand.

Putting it together, with ``word`` the 32-bit word ``byte1..byte4`` read big
endian and ``e`` the exponent byte::

    value = (word | 0x80000000) * 2 ** (e - 160)

so ``81 00 00 00 00`` is 1.0 and ``80 00 00 00 00`` is 0.5, exactly as the paper
records from the game's own ``VAR.BIN``.

Arithmetic is *not* implemented here. Every operation goes through a backend
object so that the game can run on the emulated Apple IIe ROM (the default) or
on a pure-Python implementation of the same algorithms, which is held to
bit-equality with the ROM by the test suite. See :mod:`oregon.applesoft`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = [
    "Fac", "ZERO", "ONE", "HALF", "TWO", "THREE", "FOUR",
    "backend_name", "set_backend", "using_rom",
    "add", "sub", "mul", "div", "neg", "abs_", "int_", "round_fac", "cmp",
    "add_const", "mul_const", "div_const",
    "from_int", "from_str", "to_int", "to_float", "str_dollar_int",
]

_backend: Backend | None = None


@runtime_checkable
class Backend(Protocol):
    """What :mod:`oregon.applesoft` has to supply."""

    name: str
    is_rom: bool

    def add(self, a: Fac, b: Fac) -> Fac: ...
    def sub(self, a: Fac, b: Fac) -> Fac: ...
    def mul(self, a: Fac, b: Fac) -> Fac: ...
    def div(self, a: Fac, b: Fac) -> Fac: ...
    def neg(self, a: Fac) -> Fac: ...
    def abs_(self, a: Fac) -> Fac: ...
    def int_(self, a: Fac) -> Fac: ...
    def round_fac(self, a: Fac) -> Fac: ...
    def cmp(self, a: Fac, b: Fac) -> int: ...
    def add_const(self, a: Fac, b: Fac) -> Fac: ...
    def mul_const(self, a: Fac, b: Fac) -> Fac: ...
    def div_const(self, a: Fac, b: Fac) -> Fac: ...
    def from_str(self, s: str) -> Fac: ...
    def fmt_body(self, v: Fac) -> str: ...


def set_backend(b) -> None:
    """Install the arithmetic backend. Called by :mod:`oregon.applesoft`."""
    global _backend
    _backend = b


def _b() -> "Backend":
    if _backend is None:
        raise RuntimeError("no arithmetic backend installed")
    return _backend


def backend_name() -> str:
    return "unset" if _backend is None else _backend.name


def using_rom() -> bool:
    return _backend is not None and _backend.is_rom


class Fac:
    """An immutable 5-byte Applesoft value.

    Equality, ordering and hashing are *exact*: two values are equal when their
    five bytes are equal, which is what Applesoft's own comparison amounts to.
    The paper (section 12.4) is explicit that no tolerance may be used anywhere,
    because tests such as ``IF I(2) = INT (I(2))`` and ``PF = C0`` depend on it.
    """

    __slots__ = ("b",)

    def __init__(self, b):
        if isinstance(b, Fac):
            self.b = b.b
            return
        b = bytes(b)
        if len(b) != 5:
            raise ValueError("an Applesoft value is exactly five bytes")
        self.b = b

    # ------------------------------------------------------------------ form
    @staticmethod
    def zero() -> "Fac":
        return ZERO

    @staticmethod
    def from_int(n: int) -> "Fac":
        """See :func:`from_int`: an exact integer, no rounding involved."""
        return from_int(n)

    @staticmethod
    def from_str(s: str) -> "Fac":
        """See :func:`from_str`: a decimal literal, converted as the ROM does."""
        return from_str(s)

    def is_zero(self) -> bool:
        return self.b[0] == 0

    def is_negative(self) -> bool:
        return (self.b[1] & 0x80) != 0

    def exponent_byte(self) -> int:
        return self.b[0]

    def word(self) -> int:
        """The 32-bit significand word as stored, sign bit included."""
        return int.from_bytes(self.b[1:5], "big")

    def raw(self) -> bytes:
        return self.b

    def __repr__(self) -> str:
        return f"Fac({self.b.hex(' ')})"

    def __bool__(self) -> bool:
        return not self.is_zero()

    def __hash__(self) -> int:
        return hash(self.b)

    # ------------------------------------------------------------ comparison
    def __eq__(self, other) -> bool:
        if not isinstance(other, Fac):
            return NotImplemented
        return cmp(self, other) == 0

    def __ne__(self, other) -> bool:
        if not isinstance(other, Fac):
            return NotImplemented
        return cmp(self, other) != 0

    def __lt__(self, other) -> bool:
        return cmp(self, other) < 0

    def __le__(self, other) -> bool:
        return cmp(self, other) <= 0

    def __gt__(self, other) -> bool:
        return cmp(self, other) > 0

    def __ge__(self, other) -> bool:
        return cmp(self, other) >= 0

    # --------------------------------------------------------------- numbers
    def to_int(self) -> int:
        """The value truncated toward zero, as INT then a POKE would give it."""
        if self.b[0] == 0:
            return 0
        word = self.word() | 0x80000000
        shift = 160 - self.b[0]
        if shift <= 0:
            v = word << (-shift)
        elif shift >= 96:
            v = 0
        else:
            v = word >> shift
        return -v if self.is_negative() else v

    def to_float(self) -> float:
        """A host float. For tests, tracing and display only.

        Nothing in the game may use this to produce a value that game logic
        then consumes; the paper (section 12.4) is explicit that a 53-bit
        significand keeps bits the original discards.
        """
        if self.b[0] == 0:
            return 0.0
        word = self.word() | 0x80000000
        v = _ldexp(word, self.b[0] - 160)
        return -v if self.is_negative() else v

    def str_(self) -> str:
        """Applesoft's ``STR$`` form. A positive number gets a leading space."""
        return ("-" if self.is_negative() else " ") + _backend.fmt_body(self)


def _ldexp(word: int, e: int) -> float:
    """``word * 2 ** e`` without importing math, so this module stays pure."""
    if word == 0:
        return 0.0
    r = float(word)
    if e >= 0:
        for _ in range(e):
            r *= 2.0
    else:
        for _ in range(-e):
            r /= 2.0
    return r


# --------------------------------------------------------------- operations
def add(a: Fac, b: Fac) -> Fac:
    return _b().add(a, b)


def sub(a: Fac, b: Fac) -> Fac:
    return _b().sub(a, b)


def mul(a: Fac, b: Fac) -> Fac:
    return _b().mul(a, b)


def div(a: Fac, b: Fac) -> Fac:
    return _b().div(a, b)


def neg(a: Fac) -> Fac:
    return _b().neg(a)


def abs_(a: Fac) -> Fac:
    return _b().abs_(a)


def int_(a: Fac) -> Fac:
    """``INT``: floor, not truncation toward zero (paper, translation rules)."""
    return _b().int_(a)


def round_fac(a: Fac) -> Fac:
    """``ROUND.FAC`` at $EB72: round the extension byte into the significand."""
    return _b().round_fac(a)


def cmp(a: Fac, b: Fac) -> int:
    """``-1``, ``0`` or ``1``. Exact byte comparison, never a tolerance."""
    return _b().cmp(a, b)


def add_const(a: Fac, b: Fac) -> Fac:
    return _b().add_const(a, b)


def mul_const(a: Fac, b: Fac) -> Fac:
    return _b().mul_const(a, b)


def div_const(a: Fac, b: Fac) -> Fac:
    return _b().div_const(a, b)


# ------------------------------------------------------------ constructors
def from_int(n: int) -> Fac:
    """An integer as a 5-byte value, exactly when it fits in 32 bits.

    Applesoft builds integers by shifting the 16- and 32-bit machine values, so
    this builds the same normalised form: the significand's top bit is set and the
    exponent byte follows from it. That canonical shape matters because Applesoft
    compares values byte by byte, and so does :func:`cmp`.
    """
    if n == 0:
        return ZERO
    sign = 0x80 if n < 0 else 0x00
    a = abs(n)
    s = a << 1                      # so that s >> 1 is the significand
    e = 0
    b = s.bit_length()
    if b > 33:                      # more than 32 bits: round into place
        k = b - 33
        if (s >> (k - 1)) & 1:
            s = (s >> k) + 1
        else:
            s >>= k
        e = k
        if s.bit_length() > 33:
            s >>= 1
            e += 1
    elif b < 33:
        sh = 33 - b
        s <<= sh
        e = -sh
    word = s >> 1
    if s & 1:                       # the guard bit: round the significand
        word += 1
        if word > 0xFFFFFFFF:
            word >>= 1
            e += 1
    exp_byte = e + 160
    if exp_byte <= 0:
        return ZERO
    if exp_byte > 255:
        raise ValueError(f"{n} is outside the 5-byte Apple IIe format")
    word &= 0xFFFFFFFF
    return Fac(bytes((exp_byte, sign | ((word >> 24) & 0x7F), (word >> 16) & 0xFF,
                      (word >> 8) & 0xFF, word & 0xFF)))


def from_str(s: str) -> Fac:
    """A decimal literal converted the way Applesoft converts one.

    Applesoft accumulates the digits into a 5-byte value, multiplying by ten and
    adding each digit, then divides by ten once per fractional digit, rounding at
    each step. The paper (section 12.2) insists this matters: a literal such as
    ``.8`` is "whatever the ROM's own conversion routine produces, not
    necessarily the nearest representable value".
    """
    return _b().from_str(s)


def to_int(a: Fac) -> int:
    return a.to_int()


def to_float(a: Fac) -> float:
    return a.to_float()


def str_dollar_int(cents: int) -> str:
    """Helper for the ``V = INT (V * 100 + .5)`` money pattern.

    Applesoft builds the text as ``"0" + STR$(cents)``, then keeps the last two
    characters, then prepends ``STR$(INT(cents / 100))`` and a full stop. With a
    leading space from ``STR$`` that yields ``" 12.34"``; for zero it yields the
    odd ``" 0. 0"``, which the original does print. Both are reproduced.
    """
    # K$ is "0" + STR$(cents); its last two characters are the cents, and because
    # STR$ prefixes a space they are " 5" rather than "05" for a single-digit
    # figure. The dollars come from STR$(INT(cents / 100)).
    frac = (" " + str(cents))[-2:]
    return " " + str(cents // 100) + "." + frac


ZERO = Fac(bytes(5))
ONE = Fac(bytes((0x81, 0x00, 0x00, 0x00, 0x00)))
HALF = Fac(bytes((0x80, 0x00, 0x00, 0x00, 0x00)))
TWO = Fac(bytes((0x82, 0x00, 0x00, 0x00, 0x00)))
THREE = Fac(bytes((0x82, 0x40, 0x00, 0x00, 0x00)))
FOUR = Fac(bytes((0x83, 0x00, 0x00, 0x00, 0x00)))