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
object so that the game can run on the emulated Apple IIe ROM (the default), on
a Python transcription of the ROM's routines that the test suite holds to
bit-equality with it, or on the other arithmetics compared in paper section 12.
See :mod:`oregon.applesoft`.
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
    def fmt(self, v: Fac) -> str: ...


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

    __slots__ = ("b", "ext")

    def __init__(self, b, ext=None):
        """``b`` is the five bytes, or another value to copy.

        ``ext`` is the extension byte (``$AC``) that Applesoft keeps beside the
        working value: the bits below the last place of the significand. A value
        that has just come out of an operator or a decimal literal still carries
        it, and the interpreter uses it when that value is the right-hand operand
        of the next operator. A value in a variable has been through ``ROUND.FAC``
        and carries none (``ext`` 0). The extension is not part of the five bytes,
        so it takes no part in equality or hashing.
        """
        if isinstance(b, Fac):
            self.b = b.b
            self.ext = b.ext if ext is None else ext
            return
        b = bytes(b)
        if len(b) != 5:
            raise ValueError("an Applesoft value is exactly five bytes")
        self.b = b
        self.ext = 0 if ext is None else ext

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
        return self.raw()[0]

    def word(self) -> int:
        """The 32-bit significand word as stored, sign bit included."""
        return int.from_bytes(self.raw()[1:5], "big")

    def raw(self) -> bytes:
        """The five bytes a variable would hold: the value after ``ROUND.FAC``.

        ``b`` is the working value an operator left in FAC. When it carries an
        extension byte with bit 7 set, storing it adds one to the significand, and
        this is the sum. The backends use ``b`` and ``ext`` to carry on a
        calculation; everything that reads a number reads this.
        """
        if self.ext & 0x80:
            return _b().round_fac(self).b
        return self.b

    def __repr__(self) -> str:
        if self.ext:
            return f"Fac({self.b.hex(' ')} ext {self.ext:02X})"
        return f"Fac({self.b.hex(' ')})"

    def __str__(self) -> str:
        """The number, as text.

        Without this, ``str()`` falls back to ``__repr__`` and yields
        ``Fac(85 20 00 00 00)``, which :func:`oregon.num.parse` reads as **0**.
        That is not a cosmetic slip: ``num.parse(str(x))`` is a natural-looking way to
        get a plain number out of a ``Fac``, and it was used in three places. Every
        holding on both supplies screens printed as zero, so a party that had bought
        oxen, food and clothing appeared to own nothing; and ``HR``, the event
        hardship term of the health sum, contributed nothing at all, which is why
        health never moved. ``repr`` keeps the byte form for debugging.
        """
        f = self.to_float()
        return str(int(f)) if f == int(f) else repr(f)

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
    def _stored(self) -> "Fac":
        """The value as a variable would hold it: ``ROUND.FAC`` applied to the
        bytes and the extension byte. Python code that reads a number out of an
        operator's result wants this one, not the half-finished working value."""
        return _b().round_fac(self) if self.ext & 0x80 else self

    def to_int(self) -> int:
        """The value truncated toward zero, as INT then a POKE would give it."""
        if self.ext & 0x80:
            return self._stored().to_int()
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
        if self.ext & 0x80:
            return self._stored().to_float()
        if self.b[0] == 0:
            return 0.0
        word = self.word() | 0x80000000
        v = _ldexp(word, self.b[0] - 160)
        return -v if self.is_negative() else v

    def str_(self) -> str:
        """Applesoft's ``STR$``: the text ``FOUT`` builds for the value as it stands.

        There is **no** leading space for a positive number; a negative one begins
        with ``-``. (``FOUT`` at $ED34 returns ``5`` for 5; the ROM was run to check.)
        An operator's result is formatted with its extension byte, as ``STR$ (A/B)``
        is; a variable's value has none.
        """
        return _backend.fmt(self)


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
    """The money text of lines 200 and 250: ``V`` is already a whole number of cents.

    ``K$ = "0" + STR$(V): K$ = STR$(INT(V / 100)) + "." + RIGHT$(K$, 2)``. ``STR$`` has
    no leading space, so five cents is ``0.05``, no cents is ``0.00`` and $800 is
    ``800.00``.
    """
    return str(cents // 100) + "." + ("0" + str(cents))[-2:]


ZERO = Fac(bytes(5))
ONE = Fac(bytes((0x81, 0x00, 0x00, 0x00, 0x00)))
HALF = Fac(bytes((0x80, 0x00, 0x00, 0x00, 0x00)))
TWO = Fac(bytes((0x82, 0x00, 0x00, 0x00, 0x00)))
THREE = Fac(bytes((0x82, 0x40, 0x00, 0x00, 0x00)))
FOUR = Fac(bytes((0x83, 0x00, 0x00, 0x00, 0x00)))