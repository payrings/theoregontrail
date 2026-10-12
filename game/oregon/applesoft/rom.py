"""The Apple IIe ROM running under a 6502 emulator: the game's arithmetic engine.

This is the authoritative implementation of Applesoft's number handling. Every
addition, subtraction, multiplication and division, ``INT``, ``RND``, the
conversion of a decimal literal and the conversion of a number to text is performed
by genuine 6502 code from a genuine Apple IIe ROM image, operating on 5-byte FAC
values in emulated memory. The Python side moves the five bytes (and the extension
byte of a value that has not yet been stored) in and out of memory, adds the carry
that ``ROUND.FAC`` would add where the interpreter stores or pushes a value, and
compares two stored values on their bytes; ``FCOMP`` itself runs when the right
operand still carries an extension byte with bit 7 set.

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
    addend       $EFAA   68 28 B1 46 20

The addend is about 3.9e-8 against products of order 1e7, so it very nearly does
nothing -- also as the paper says. (The fifth byte of each constant is the next
byte in the ROM: the addend's is the opcode of the ``JSR`` at ``$EFAE``.) Seeding is ``RND(-n)``, and the value
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
TXTPTR = 0xB8    # the program text pointer, which CHRGET advances
CHRGET = 0xB1    # the 24-byte CHRGET routine the interpreter copies into zero page

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
E_FCOMP = 0xEBB2
E_FIN = 0xEC4A
E_INT = 0xEC23
E_RND = 0xEFAE
E_FOUT = 0xED34      # FOUT: FAC -> text at $0100, ended by a zero byte
STACK_TEXT = 0x0100

# Applesoft's own error numbers (the values ONERR leaves at 222)
ERR_OVERFLOW = 69
ERR_ILLEGAL_QUANTITY = 53
ERR_DIVISION_BY_ZERO = 133

# --- harness addresses ----------------------------------------------------
# $0300  JSR <target> ; RTS     -- the trampoline we jump through
# $03F0  JMP $03F0              -- the CPU parks here when the call returns
STUB = 0x0300
PARK = 0x03F0
SCRATCH = 0x0800        # five bytes for a memory operand
TEXT = 0x0810           # a decimal literal, for FIN to read

_ROM_SEARCH = Path(__file__).resolve().parents[2] / "rom" / "apple-rom"


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

    Applesoft's OVERFLOW is number 69. The game's own error handler (COMMON.LIB
    32000) reads the code from 222 and prints ``Error [code] at line #[line] in
    [program]. Please report this error to MECC.``, so the game treats one of
    these as a defined outcome rather than a Python failure.
    """

    def __init__(self, code: int, detail: str = ""):
        super().__init__(f"Applesoft error {code}{': ' + detail if detail else ''}")
        self.code = code


class RomBackend:
    """Arithmetic by executing a real Apple IIe ROM under py65."""

    name = "apple-rom"
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
        # CHRGET: the interpreter's character fetch, which FIN calls. The ROM holds
        # the routine as data and copies it into zero page when it starts; do the
        # same copy, finding it by its first nine bytes.
        template = bytes.fromhex("E6B8D002E6B9AD60EA")
        at = image.find(template)
        if at < 0:
            raise ValueError(f"{self.path}: the CHRGET routine was not found")
        self.m.memory[CHRGET:CHRGET + 0x18] = image[at:at + 0x18]
        self.calls = 0
        self._literals = {}          # text -> value; a literal converts the same way every time

    # ------------------------------------------------------------- plumbing
    def _run(self, target: int, *, x=None, y=None, a=None, carry=None,
             limit: int = 2_000_000):
        """Call a ROM routine at ``target`` and return when the CPU parks."""
        m = self.m
        if x is not None:
            m.x = x & 0xFF
        if y is not None:
            m.y = y & 0xFF
        if a is not None:
            m.a = a & 0xFF
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
        if carry is not None:
            flags = (flags | 0x01) if carry else (flags & ~0x01)
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
                if pc == PARK:
                    return
                if CHRGET <= pc < CHRGET + 0x18:
                    m.step()                  # CHRGET, copied into zero page
                    continue
                if pc < 0xC000:
                    return
                if not (0xE000 <= pc < 0xF000):
                    # every Applesoft error reaches ERROR at $D412 with its number
                    # in X (69 OVERFLOW, 133 DIVISION BY ZERO, 53 ILLEGAL QUANTITY)
                    code = m.x if pc == 0xD412 else ERR_ILLEGAL_QUANTITY
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
        """Load FAC with ``v``, including the extension byte it carries."""
        m = self.m
        r = v.b                      # the working bytes, not the stored ones
        m.memory[0x9D] = r[0]
        m.memory[0x9E] = r[1] | 0x80
        m.memory[0x9F] = r[2]
        m.memory[0xA0] = r[3]
        m.memory[0xA1] = r[4]
        m.memory[0xA2] = r[1]
        m.memory[0xAC] = v.ext

    def _result(self) -> Fac:
        """FAC as an operator leaves it: the five bytes and the live extension."""
        f = self.get_fac()
        if f.b[0] == 0:
            return Fac(bytes(5))
        return Fac(f.b, self.m.memory[EXT])

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
    # How the interpreter evaluates ``left (op) right`` (FRMEVL, $DD67):
    #
    # * ``left`` is the value computed before the operator. The interpreter
    #   pushes it on the stack through $DE20, which calls ``ROUND.FAC``, so it is
    #   rounded by its own extension byte before the operator sees it.
    # * ``right`` is whatever the next term left in FAC, and **its extension byte
    #   is still live**: nothing rounds it first. That is true of a value fresh from
    #   an operator (``A + B * C``, where the product is the right operand), of a
    #   parenthesised sum, and of a decimal literal, because ``FIN`` leaves
    #   ``.8`` as ``80 4C CC CC CC`` with $AC at ``80``. Only a variable arrives
    #   with $AC clear.
    # * The operator then pops ``left`` into ARGBUF ($DE43 to $DE59, which also
    #   sets the sign byte $AA and the sign comparison $AB) and jumps to FADDT,
    #   FSUBT, FMULTT or FDIVT with FAC as the right operand.
    #
    # ``_op`` does exactly that, so the sign handling, the alignment, the guard
    # byte and the carries are all the ROM's.
    def _op(self, left: Fac, right: Fac, entry: int) -> Fac:
        left = self.round_fac(left)
        m = self.m
        self.set_fac(right)
        lb = left.raw()
        m.memory[ARGBUF:ARGBUF + 5] = bytes(
            (lb[0], lb[1] | 0x80, lb[2], lb[3], lb[4]))
        m.memory[0xAA] = lb[1]
        m.memory[SIGN2] = lb[1] ^ m.memory[0xA2]
        self._run(entry)
        return self._result()

    def add(self, a: Fac, b: Fac) -> Fac:
        """``a + b``: FADDT at $E7C1."""
        return self._op(a, b, E_FADDT)

    def sub(self, a: Fac, b: Fac) -> Fac:
        """``a - b``: FSUBT at $E7AA, which is the interpreter's ``-`` operator.

        It complements FAC's sign (the right operand) and falls into FADDT.
        """
        return self._op(a, b, E_FSUBT)

    def mul(self, a: Fac, b: Fac) -> Fac:
        """``a * b``: FMULTT at $E982."""
        return self._op(a, b, E_FMULTT)

    def div(self, a: Fac, b: Fac) -> Fac:
        """``a / b``: FDIVT at $EA69, which divides ARGBUF by FAC.

        The divisor is the right operand, and FDIVT rounds it ($EA6B) before it
        divides, so the divisor's extension byte never takes part.
        """
        if b.is_zero():
            raise RomError(ERR_DIVISION_BY_ZERO, "division by zero")
        return self._op(a, b, E_FDIVT)

    # ------------------------------------------------------ constant forms
    def _const(self, a: Fac, b: Fac, target: int) -> Fac:
        self.set_fac(a)
        self._put_scratch(b)
        # $E9E3 (ARGBUF) takes the address in A (low) and Y (high)
        self._run(target, a=SCRATCH & 0xFF, y=SCRATCH >> 8)
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
        f = self.get_fac()
        # a zero exponent is zero whatever the other bytes hold (FCOMP and the
        # interpreter test only the exponent), so return the one zero there is
        return f if f.b[0] else Fac(bytes(5))

    def add_const(self, a: Fac, b: Fac) -> Fac:
        """``$E7BE`` loads ARGBUF from memory and adds; it is :meth:`add`."""
        return self.add(a, b)

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
            raise RomError(ERR_DIVISION_BY_ZERO, "division by zero")
        mag = self._const(self.abs_(b), self.abs_(a), E_FDIVC)
        return self.neg(mag) if (a.is_negative() != b.is_negative()) else mag

    # --------------------------------------------------------- sign and cast
    def neg(self, a: Fac) -> Fac:
        """Unary minus (NEGOP, $EED0): it flips FAC's sign and nothing else, so
        the extension byte stays."""
        if a.is_zero():
            return a
        b = bytearray(a.b)
        b[1] ^= 0x80
        return Fac(bytes(b), a.ext)

    def abs_(self, a: Fac) -> Fac:
        if not a.is_negative():
            return a
        return self.neg(a)

    def int_(self, a: Fac) -> Fac:
        """``INT`` ($EC23), run on FAC with whatever extension byte it carries."""
        if a.is_zero():
            return a
        self.set_fac(a)
        self._run(E_INT)
        return self._result()

    def round_fac(self, a: Fac) -> Fac:
        """``ROUND.FAC`` ($EB72), which is what a value goes through when it is
        stored in a variable or pushed on the evaluator's stack.

        It adds one to the significand when bit 7 of the value's own extension
        byte is set, and the value then has no extension left. A value that never
        had one (a variable's, an integer's) passes through unchanged. An earlier
        version set the byte to 80 first and so added a unit to every value stored.
        """
        if a.is_zero():
            return Fac(bytes(5))
        if not (a.ext & 0x80):
            return a if a.ext == 0 else Fac(a.b)
        self.set_fac(a)
        self._run(E_ROUND)
        return Fac(self.get_fac().b)

    def cmp(self, a: Fac, b: Fac) -> int:
        """Exact comparison of ``a`` with ``b``: -1, 0 or 1.

        Applesoft compares magnitude byte by byte with no tolerance, which is
        what the paper requires (section 12.4), so this is done on the bytes.

        As in the interpreter, ``a`` is the left operand and has been rounded, and
        ``b`` is the right operand, still in FAC. FCOMP ($EBB2) reads FAC's
        extension byte, so a right operand that carries one with bit 7 set is
        compared by the ROM itself; every other pair is compared on the bytes.
        """
        a = self.round_fac(a)
        if b.ext & 0x80 and not b.is_zero():
            self.set_fac(b)
            self._put_scratch(a)
            self._run(E_FCOMP, a=SCRATCH & 0xFF, y=SCRATCH >> 8)
            return -self._signed(self.m.a)
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
        self._run(E_RND)
        # $EFAE already rounds at $EB2B before storing the seed, so the value
        # in FAC is the one to return.
        return self.get_fac()

    # --------------------------------------------------------------- strings
    @staticmethod
    def _signed(v: int) -> int:
        """A byte as a signed number: 0, 1 or $FF as 0, 1 or -1."""
        return v - 256 if v >= 128 else v

    def from_str(self, s: str) -> Fac:
        """A decimal literal as the interpreter reads one: FIN at $EC4A.

        ``FIN`` converts the digits by repeated multiplication and division and
        leaves the result in FAC **unrounded**, with the leftover bits in $AC.
        ``.8`` comes out as ``80 4C CC CC CC`` with $AC at ``80``; a variable that
        is assigned it holds ``80 4C CC CC CD``. This returns the first, with its
        extension byte, because that is what the right-hand side of ``X + .8``
        sees. Anything that stores it, or uses it as a left operand, rounds it.
        """
        cached = self._literals.get(s)
        if cached is not None:
            return cached
        v = self._read_literal(s)
        self._literals[s] = v
        return v

    def _read_literal(self, s: str) -> Fac:
        t = s.strip()
        negative = False
        if t[:1] in ("+", "-"):
            negative = t[0] == "-"
            t = t[1:]
        if not t:
            return Fac(bytes(5))
        m = self.m
        text = t.encode("ascii") + b"\x00"
        m.memory[TEXT:TEXT + len(text)] = text
        m.memory[TXTPTR] = (TEXT - 1) & 0xFF         # CHRGET steps before it reads
        m.memory[TXTPTR + 1] = (TEXT - 1) >> 8
        self._run(CHRGET)
        first, carry = m.a, bool(m.p & 0x01)
        m.memory[0x9D:0xA3] = bytes(6)
        m.memory[EXT] = 0
        self._run(E_FIN, a=first, carry=carry)
        v = self._result()
        return self.neg(v) if negative else v

    def fmt(self, v: Fac) -> str:
        """The text the ROM's own ``FOUT`` builds for ``v`` (what ``STR$`` returns).

        FOUT leaves the text at $0100 and ends it with a zero byte. A positive number
        has no leading space; a negative one begins with ``-``.
        """
        m = self.m
        # FOUT works on FAC as it stands, extension byte included: STR$ of an
        # operator's result is formatted before any rounding (a variable's value
        # carries no extension byte, so it is formatted as stored)
        self.set_fac(v)
        self._run(E_FOUT)
        out = bytearray()
        i = STACK_TEXT
        while m.memory[i] and len(out) < 24:
            out.append(m.memory[i])
            i += 1
        return out.decode("ascii")
