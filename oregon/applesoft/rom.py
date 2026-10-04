"""The Apple IIe ROM running under a 6502 emulator: the game's arithmetic engine.

This is the authoritative implementation of Applesoft's number handling. Every
arithmetic operation is performed by genuine 6502 code from a genuine Apple IIe
ROM image, operating on 5-byte FAC values in emulated memory. The Python side
never computes a game value itself; it moves five bytes in and out of memory and
nothing else.

The paper (section 12) is explicit that no host-language arithmetic reproduces
the original: the rounding points, the single guard byte, the decimal-literal
conversion and `RND` all live in the Applesoft ROM. Executing the ROM is the
only way to get them right, so that is what this module does.

Entry points
------------
Every address below was read out of this ROM image and matches the ones the
paper quotes.

=================  ========  =================================================
routine            address   what it does
=================  ========  =================================================
``$EAF9``          MOVAF     ``FAC <- the 5 bytes at (ptr)``
``$EB2B``          MOVAF-S   ``ROUND.FAC``, then ``(ptr) <- FAC``, ptr in X/Y
``$E9E3``          ARGBUF    ``ARGBUF <- the 5 bytes at (ptr)``
``$E7C1``          FADDT     ``FAC <- FAC + ARGBUF``
``$E7AA``          FSUBT     ``FAC <- FAC - ARGBUF``
``$E982``          FMULTT    ``FAC <- FAC * ARGBUF``
``$EA69``          FDIVT     ``FAC <- FAC / ARGBUF``
``$E97F``          FMULTC    ``FAC <- FAC * (5 bytes at (ptr))``
``$E7BE``          FADDC     ``FAC <- FAC + (5 bytes at (ptr))``
``$EA66``          FDIVC     ``FAC <- FAC / (5 bytes at (ptr))``
``$EB72``          ROUND.FAC the rounding routine, paper table 27
``$EC23``          INT       the ``INT`` function
``$EBF2``          QINT      truncating conversion
``$EFAE``          RND       the generator; the seed lives at ``$C9``-``$CD``
=================  ========  =================================================

``RND`` decoded from this ROM
-----------------------------
The paper describes ``RND`` only in prose; here is what the bytes do::

    EFAE  JSR $EB82      ; FIXARG: A = 0 if FAC is zero, 1 if +, $FF if -
    EFB1  TAX
    EFB2  BMI $EFCC      ; a negative argument is itself the new seed basis
    EFB4  LDA #$C9 / LDY #$00 / JSR $EAF9   ; FAC <- the 5 seed bytes at $C9
    EFBB  TXA / BEQ $EFA5                   ; RND(0): the last value again
    EFBE  LDA #$A6 / LDY #$EF / JSR $E97F   ; FAC *= the 5 bytes at $EFA6
    EFC5  LDA #$AA / LDY #$EF / JSR $E7BE   ; FAC += the 5 bytes at $EFAA
    EFCC  LDX $A1 / LDA $9E / STA $A1 / STX $9E   ; swap significand bytes 1,3
    EFD4  LDA #$00 / STA $A2                      ; clear the lowest byte
    EFD8  LDA $9D / STA $AC                        ; guard byte <- exponent
    EFDC  LDA #$80 / STA $9D                       ; force exponent 128
    EFE0  JSR $E82E                                ; normalise down into [0.5,1)
    EFE3  LDX #$C9 / LDY #$00 / JMP $EB2B          ; round, store to $C9, return

The two constants are the bytes at ``$EFA6`` and ``$EFAA``. Both live in the ROM
with only four significant bytes, so each is read together with whatever byte
happens to follow it, which is exactly the quirk the paper reports. In this
image they are::

    multiplier   $EFA6   98 35 44 7A 68
    addend       $EFAA   7A 68 B1 46 20

The addend is about 0.005 against products of order 1e7, so it very nearly does
nothing -- also as the paper says. Seeding is ``RND(-n)``, and the value
returned is the seed just stored, which is why ``RND(0)`` repeats.
"""

from __future__ import annotations

import os
from pathlib import Path

from py65.devices.mpu6502 import MPU

from .fac import Fac

__all__ = ["RomBackend", "available", "rom_path", "describe",
           "RND_MULTIPLIER", "RND_ADDEND"]

# --- the two RND constants, read out of this ROM image --------------------
RND_MULTIPLIER = bytes((0x98, 0x35, 0x44, 0x7A, 0x68))   # the 5 bytes at $EFA6
RND_ADDEND = bytes((0x68, 0x28, 0xB1, 0x46, 0x20))       # the 5 bytes at $EFAA

# --- Applesoft zero-page locations ----------------------------------------
FAC = 0x9D       # the 5-byte FAC: exponent, sign, three significand bytes
ARGBUF = 0xA5    # the 5-byte ARGBUF
SIGN2 = 0xAB     # a second copy of the sign byte
EXT = 0xAC       # the extension (guard) byte
SEED = 0xC9      # the 5-byte RND seed
PTR_LO = 0x5E
PTR_HI = 0x5F

# --- ROM entry points -----------------------------------------------------
E_MOVAF = 0xEAF9
E_MOVAF_STORE = 0xEB2B
E_ARGBUF = 0xE9E3
E_FADDT = 0xE7C1
E_FSUBT = 0xE7AA
E_FMULTT = 0xE982
E_FDIVT = 0xEA69
E_FMULTC = 0xE97F
E_FADDC = 0xE7BE
E_FDIVC = 0xEA66
E_ROUND = 0xEB72
E_INT = 0xEC23
E_RND = 0xEFAE

# Applesoft's own error numbers
ERR_OVERFLOW = 6
ERR_ILLEGAL_QUANTITY = 53

# --- harness addresses ----------------------------------------------------
# $0300  JSR <target> ; RTS     -- the trampoline we jump through
# $03F0  JMP $03F0              -- the CPU parks here when the call returns
STUB = 0x0300
PARK = 0x03F0
SCRATCH = 0x0800        # five bytes for a memory operand

_ROM_SEARCH = Path(__file__).resolve().parents[2] / "rom" / "apple2e.rom"


def rom_path() -> Path:
    """The ROM image to use. Override with the ``OREGON_ROM`` environment variable."""
    env = os.environ.get("OREGON_ROM")
    return Path(env) if env else _ROM_SEARCH


def available() -> bool:
    return rom_path().is_file()


def describe() -> str:
    p = rom_path()
    if not p.is_file():
        return f"no ROM image at {p} (set OREGON_ROM to point at one)"
    return f"{p} ({p.stat().st_size} bytes)"


class RomError(Exception):
    """An Applesoft runtime error provoked by the emulated ROM.

    Applesoft's OVERFLOW is number 6. The game's own error handler (COMMON.LIB
    32000) reads the code from 222 and prints ``Error [code] at line #[line] in
    [program]. Please report this error to MECC.``, so the game treats one of
    these as a defined outcome rather than a Python failure.
    """

    def __init__(self, code: int, detail: str = ""):
        super().__init__(f"Applesoft error {code}{': ' + detail if detail else ''}")
        self.code = code


class RomBackend:
    """Arithmetic by executing a real Apple IIe ROM under py65."""

    name = "apple2e-rom"
    is_rom = True

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else rom_path()
        if not self.path.is_file():
            raise FileNotFoundError(
                f"no Apple IIe ROM image at {self.path}; set OREGON_ROM")
        image = self.path.read_bytes()
        if len(image) != 0x8000:
            raise ValueError(
                f"{self.path} is {len(image)} bytes; an Apple IIe image is "
                f"32768 bytes covering $8000-$FFFF")
        self.m = MPU()
        self.m.memory[0x8000:0x10000] = image
        # The image must really be an Apple IIe with Applesoft at $D000.
        if bytes(self.m.memory[0xEB72:0xEB74]) != bytes((0xA5, 0x9D)):
            raise ValueError(
                f"{self.path} does not look like an Apple IIe ROM: ROUND.FAC at "
                f"$EB72 should begin A5 9D, found "
                f"{bytes(self.m.memory[0xEB72:0xEB74]).hex(' ')}")
        # trampoline and park loop
        self.m.memory[STUB] = 0x20
        self.m.memory[STUB + 3] = 0x60
        self.m.memory[PARK] = 0x4C
        self.m.memory[PARK + 1] = PARK & 0xFF
        self.m.memory[PARK + 2] = PARK >> 8
        self.calls = 0

    # ------------------------------------------------------------- plumbing
    def _run(self, target: int, *, x=None, y=None, limit: int = 2_000_000):
        """Call a ROM routine at ``target`` and return when the CPU parks."""
        m = self.m
        if x is not None:
            m.x = x & 0xFF
        if y is not None:
            m.y = y & 0xFF
        m.memory[STUB + 1] = target & 0xFF
        m.memory[STUB + 2] = (target >> 8) & 0xFF
        # Several of these routines branch on the Z flag before touching memory:
        # FADDT ($E7C1), FMULTT ($E982) and FDIVT ($EA69) all start by testing
        # whether FAC is zero, and Applesoft's evaluator has always just done a
        # `LDA $9D`. Reproduce that, or the flag left by the previous call decides
        # the branch instead.
        e = m.memory[0x9D]
        flags = m.p & ~0xC2
        if e == 0:
            flags |= 0x02
        if e & 0x80:
            flags |= 0x80
        m.p = flags
        m.sp = 0xFF
        m.stPushWord(PARK)
        m.pc = STUB
        self.calls += 1
        for _ in range(limit):
            pc = m.pc
            # The floating-point routines live entirely in $E000-$EFFF and
            # return with RTS. Reaching anything else means either the call has
            # returned or the routine branched into an error handler, and those
            # two are told apart by address: the handlers sit at $D412
            # (overflow) and in the floating-point ROM at $C100-$CFFF.
            # $0300 is the trampoline itself, not yet inside the ROM.
            if pc != STUB:
                if pc < 0xC000:
                    return
                if not (0xE000 <= pc < 0xF000):
                    code = ERR_OVERFLOW if pc == 0xD412 else ERR_ILLEGAL_QUANTITY
                    raise RomError(code, f"${target:04X} branched to ${pc:04X}")
            m.step()
        raise RuntimeError(f"ROM call to ${target:04X} did not return")

    # ----------------------------------------------------------- FAC access
    # The working FAC and a stored variable are not the same five bytes. In the
    # working FAC the significand's implicit leading one *is* present, in the sign
    # position of byte 1, and the sign lives in a separate byte at $A2. A stored
    # value has the sign in byte 1 and no implicit one. $EAF9 (MOVAF) converts
    # stored -> working, and $EB43 converts back, so the conversions below are
    # those two routines bit for bit.
    def get_fac(self) -> Fac:
        m = self.m
        b = bytearray(5)
        b[0] = m.memory[0x9D]
        b[1] = (m.memory[0x9E] & 0x7F) | (m.memory[0xA2] & 0x80)
        b[2] = m.memory[0x9F]
        b[3] = m.memory[0xA0]
        b[4] = m.memory[0xA1]
        return Fac(bytes(b))

    def set_fac(self, v: Fac):
        m = self.m
        r = v.raw()
        m.memory[0x9D] = r[0]
        m.memory[0x9E] = r[1] | 0x80
        m.memory[0x9F] = r[2]
        m.memory[0xA0] = r[3]
        m.memory[0xA1] = r[4]
        m.memory[0xA2] = r[1]
        m.memory[0xAC] = 0

    def _ptr(self, addr: int) -> int:
        self.m.memory[PTR_LO] = addr & 0xFF
        self.m.memory[PTR_HI] = (addr >> 8) & 0xFF
        return addr & 0xFFFF

    def _put_scratch(self, v: Fac):
        self.m.memory[SCRATCH:SCRATCH + 5] = v.raw()

    # -------------------------------------------------------------- MOVAF in
    def movaf(self, v: Fac) -> Fac:
        self._put_scratch(v)
        self._run(E_MOVAF, x=SCRATCH & 0xFF, y=SCRATCH >> 8)
        return self.get_fac()

    # ----------------------------------------------------------- arithmetic
    @staticmethod
    def _magnitude_cmp(a: Fac, b: Fac) -> int:
        """-1, 0 or 1 comparing the magnitudes of two values, sign ignored."""
        ka = (a.exponent_byte(), a.word() | 0x80000000)
        kb = (b.exponent_byte(), b.word() | 0x80000000)
        return (ka > kb) - (ka < kb)

    def _mag_op(self, x: Fac, y: Fac, add: bool) -> Fac:
        """``x + y`` or ``x - y`` for **positive** x and y, done by the ROM.

        Keeping both operands positive removes the only part of FADDT that a
        caller has to arrange by hand: it branches on the sign byte of ARGBUF --
        clear to add the magnitudes, set to subtract them -- so setting that one
        byte chooses the operation and the ROM does the alignment, the guard byte
        and the carries.
        """
        m = self.m
        self.set_fac(x)                       # positive, so $A2 is zero
        ry = y.raw()
        m.memory[ARGBUF:ARGBUF + 5] = bytes(
            (ry[0], ry[1] | 0x80, ry[2], ry[3], ry[4]))
        m.memory[SIGN2] = 0x00 if add else 0x80
        m.memory[EXT] = 0
        self._run(E_FADDT)
        return self._settle()

    def _signed_add(self, a: Fac, b: Fac) -> Fac:
        """``a + b``.

        Applesoft's evaluator does the sign and magnitude bookkeeping itself and
        hands FADDT an operation it can carry out. Calling FADDT with arbitrary
        signs, as a plain implementation of ``+`` would, is wrong: it branches only
        on ARGBUF's sign byte, so ``-3 + -1`` comes back as -2, having subtracted
        the magnitudes. So the sign is settled here, the ROM adds or subtracts two
        positive magnitudes, and the sign is applied to the five bytes afterwards,
        which is what the ROM's own ``$A2`` sign byte does.
        """
        if a.is_zero():
            return b
        if b.is_zero():
            return a
        sa, sb = a.is_negative(), b.is_negative()
        if sa == sb:
            mag, sign = self._mag_op(self.abs_(a), self.abs_(b), True), sa
        else:
            c = self._magnitude_cmp(a, b)
            if c > 0:
                mag, sign = self._mag_op(self.abs_(a), self.abs_(b), False), sa
            elif c < 0:
                mag, sign = self._mag_op(self.abs_(b), self.abs_(a), False), sb
            else:
                mag, sign = Fac(bytes(5)), False
        return self.neg(mag) if sign else mag

    def _binary(self, a: Fac, b: Fac, target: int) -> Fac:
        """``FAC <- a (op) b``, with the ROM's own ARGBUF layout for ``b``.

        ARGBUF is not laid out like a stored value: the significand's implicit
        leading one occupies the sign position of byte 1, and the sign itself
        lives in a separate byte at ``$AB``. ``$E9E3`` builds exactly that when
        it loads ARGBUF from memory, so these entry points are given it directly.
        """
        self.set_fac(a)
        rb = b.raw()
        self.m.memory[ARGBUF:ARGBUF + 5] = bytes(
            (rb[0], rb[1] | 0x80, rb[2], rb[3], rb[4]))
        self.m.memory[SIGN2] = rb[1]
        self.m.memory[EXT] = 0
        self._run(target)
        return self._settle()

    def add(self, a: Fac, b: Fac) -> Fac:
        return self._signed_add(a, b)

    def sub(self, a: Fac, b: Fac) -> Fac:
        """``a - b``.

        Applesoft's evaluator does subtraction by negating the right operand and
        adding, and that is reproduced here. ``FSUBT`` at ``$E7AA`` is *not* that
        operator: it complements the sign byte of FAC and then zeroes ARGBUF's sign
        with ``EOR $AA``, so it computes ``|b| - a`` and loses the right operand's
        sign -- against the ROM, it turns ``-3 - 1`` into 2.
        """
        return self._signed_add(a, self.neg(b))

    def mul(self, a: Fac, b: Fac) -> Fac:
        """``a * b``.

        ``FMULTT`` at ``$E982`` takes the result's sign from ARGBUF's sign byte at
        ``$AB`` and ignores FAC's, so it cannot be called with a negative first
        operand: ``-3 * 7`` would come back as +21. The magnitudes are multiplied
        by the ROM and the sign is then the exclusive or of the two, applied to the
        five bytes, which is what the interpreter does with its own sign byte.
        """
        if a.is_zero() or b.is_zero():
            return Fac(bytes(5))
        mag = self._binary(self.abs_(a), self.abs_(b), E_FMULTT)
        return self.neg(mag) if (a.is_negative() != b.is_negative()) else mag

    def div(self, a: Fac, b: Fac) -> Fac:
        """``a / b``.

        ``FDIVT`` at ``$EA69`` is not symmetric with the other operators: the
        routine shifts ARGBUF left and subtracts FAC, so what it computes is
        ``ARGBUF / FAC``. The two operands therefore go in the other way round
        from FADDT, FSUBT and FMULTT.
        """
        if b.is_zero():
            raise ZeroDivisionError("Apple IIe: division by zero")
        mag = self._binary(self.abs_(b), self.abs_(a), E_FDIVT)
        return self.neg(mag) if (a.is_negative() != b.is_negative()) else mag

    # ------------------------------------------------------ constant forms
    def _const(self, a: Fac, b: Fac, target: int) -> Fac:
        self.set_fac(a)
        self._put_scratch(b)
        self._run(target, x=SCRATCH & 0xFF, y=SCRATCH >> 8)
        return self._settle()

    def _settle(self) -> Fac:
        """Apply ROUND.FAC to the result of an arithmetic routine.

        None of FADDT, FMULTT or FDIVT round: they leave the result in FAC with
        the guard byte at $AC and the interpreter's ``ROUND.FAC`` at $EB72 adds one
        to the significand when that byte is 80 or more. Applesoft rounds when the
        value reaches a variable, and every value this module returns is one, so
        the rounding is done here -- in bytes, which is what $EB72 plus ``ADD2``
        at $E8C6 and the carry increment at $E88F do. ``tests/test_parity.py``
        checks the byte sequence against the ROM's own ROUND.FAC.
        """
        m = self.m
        if m.memory[EXT] & 0x80:
            for addr in (0xA1, 0xA0, 0x9F, 0x9E):
                m.memory[addr] = (m.memory[addr] + 1) & 0xFF
                if m.memory[addr]:
                    break
            else:
                m.memory[0x9D] = (m.memory[0x9D] + 1) & 0xFF
                if m.memory[0x9D] == 0:
                    raise RomError(ERR_OVERFLOW, "rounding carried out of the range")
        return self.get_fac()

    def add_const(self, a: Fac, b: Fac) -> Fac:
        """``$E7BE`` loads ARGBUF from memory and adds, with the same sign
        convention as FADDT, so :meth:`_signed_add` is used instead."""
        return self._signed_add(a, b)

    def mul_const(self, a: Fac, b: Fac) -> Fac:
        if a.is_zero() or b.is_zero():
            return Fac(bytes(5))
        mag = self._const(self.abs_(a), self.abs_(b), E_FMULTC)
        return self.neg(mag) if (a.is_negative() != b.is_negative()) else mag

    def div_const(self, a: Fac, b: Fac) -> Fac:
        """``a / b``. ``$EA66`` loads ARGBUF from memory and ``$EA69`` divides
        ARGBUF by FAC, so ``b`` is the one that goes to memory, and the sign is
        applied here for the same reason as in :meth:`div`."""
        if b.is_zero():
            raise ZeroDivisionError("Apple IIe: division by zero")
        mag = self._const(self.abs_(b), self.abs_(a), E_FDIVC)
        return self.neg(mag) if (a.is_negative() != b.is_negative()) else mag

    # --------------------------------------------------------- sign and cast
    def neg(self, a: Fac) -> Fac:
        if a.is_zero():
            return a
        b = bytearray(a.raw())
        b[1] ^= 0x80
        return Fac(bytes(b))

    def abs_(self, a: Fac) -> Fac:
        if not a.is_negative():
            return a
        return self.neg(a)

    def int_(self, a: Fac) -> Fac:
        if a.is_zero():
            return a
        self.set_fac(a)
        self.m.memory[EXT] = 0
        self._run(E_INT)
        return self.get_fac()

    def round_fac(self, a: Fac) -> Fac:
        """``ROUND.FAC``: $EB72 with the extension byte set to its rounding value."""
        if a.is_zero():
            return a
        self.set_fac(a)
        self.m.memory[EXT] = 0x80
        self._run(E_ROUND)
        return self.get_fac()

    def cmp(self, a: Fac, b: Fac) -> int:
        """Exact comparison: -1, 0 or 1.

        Applesoft compares magnitude byte by byte with no tolerance, which is
        what the paper requires (section 12.4), so this is done on the bytes.
        """
        x, y = a.raw(), b.raw()
        if x == y:
            return 0
        if x[0] == 0:
            return 1 if (y[1] & 0x80) else -1
        if y[0] == 0:
            return -1 if (x[1] & 0x80) else 1
        sx, sy = x[1] & 0x80, y[1] & 0x80
        mx = ((x[0] << 31) | (int.from_bytes(x[1:5], "big") & 0x7FFFFFFF))
        my = ((y[0] << 31) | (int.from_bytes(y[1:5], "big") & 0x7FFFFFFF))
        if sx != sy:
            return -1 if sx else 1
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
        self.m.memory[SEED:SEED + 5] = bytes(seed)

    def get_seed(self) -> bytes:
        return bytes(self.m.memory[SEED:SEED + 5])

    def rnd(self, arg: Fac):
        """The ROM's ``RND``, with the argument in FAC as the evaluator leaves it."""
        self.set_fac(arg)
        self.m.memory[EXT] = 0
        self._run(E_RND)
        # $EFAE already rounds at $EB2B before storing the seed, so the value
        # in FAC is the one to return.
        return self.get_fac()

    # --------------------------------------------------------------- strings
    # Decimal-literal conversion is done in Python because Applesoft does it as
    # part of the tokenizer; see `num.parse`, which drives the ROM's own
    # multiply-and-add so that the digits are rounded by real ROM code.
    def from_str(self, s: str) -> Fac:
        from .pure import PureBackend
        return PureBackend().from_str(s)

    def fmt_body(self, v: Fac) -> str:
        from .pure import format_applesoft
        return format_applesoft(v)