"""Applesoft's random generator, ``RND`` at ``$EFAE``.

The paper (section 12.3) says only that ``RND`` multiplies the seed by one
constant, adds a second, exchanges the first and last significand bytes and
renormalises into the range 0 to 1 -- and that both constants are stored in the
ROM with four bytes instead of five, so each is read together with the byte that
happens to follow it. With the ROM in hand the constants are simply read out of
it, and this module reproduces the whole routine from the ROM's own bytes::

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
    EFE0  JSR $E82E                                ; normalise left, keep the value
    EFE3  LDX #$C9 / LDY #$00 / JMP $EB2B          ; round, store to $C9, return

The normalise step at ``$E82E`` shifts the significand left until bit 31 is set
and lowers the exponent by the same amount, so the value is unchanged but the
exponent is forced to 128 -- which is what puts the result in ``[0.5, 1)``. The
lowest significand byte is cleared first, so only 31 significand bits survive the
swap; ``ROUND.FAC`` then rounds what is left.

This module exists so the pure-Python backend produces exactly the same sequence
as the emulated ROM. ``tests/test_parity.py`` checks that over thousands of draws.
"""

from __future__ import annotations

from .fac import Fac

__all__ = ["applesoft_rnd", "swap_significand", "normalise_to_half"]

MULTIPLIER = bytes((0x98, 0x35, 0x44, 0x7A, 0x68))   # $EFA6
ADDEND = bytes((0x68, 0x28, 0xB1, 0x46, 0x20))       # $EFAA


def swap_significand(b: bytes) -> bytes:
    """The ``EFCC`` step: exchange significand bytes 1 and 3, clear byte 4."""
    return bytes((b[0], b[3], b[2], b[1], 0x00))


def normalise_to_half(b: bytes) -> bytes:
    """The ``EFDC``/``$EFE0`` steps: force the exponent to 128, keeping the value.

    The guard byte takes the old exponent, exactly as ``$EFD8`` does, so that
    ``ROUND.FAC`` can still round correctly afterwards.
    """
    exp, s, m1, m2, m3 = b
    word = ((s & 0x7F) << 24) | (m1 << 16) | (m2 << 8) | m3
    ext = exp
    # $E82E: shift the significand left until bit 31 is set, and give up one
    # exponent for every eight bits shifted.
    while not (word & 0x80000000):
        word = ((word << 8) | ext) & 0xFFFFFFFF
        ext = 0
    shift = 0
    tmp = word
    # count how many whole bytes had to move
    for k in range(1, 5):
        if word >> (32 - 8 * k) & 0xFF:
            shift = k - 1
            break
    else:
        shift = 3
    exp_byte = 128 + shift
    s = (s & 0x80) | ((word >> 24) & 0x7F)
    return bytes((exp_byte, s, (word >> 16) & 0xFF, (word >> 8) & 0xFF, word & 0xFF))


def applesoft_rnd(backend, arg: Fac) -> Fac:
    """One ``RND`` call, reproducing ``$EFAE``.

    ``backend`` supplies the five-byte arithmetic (``add``, ``mul``, ``set_seed``,
    ``get_seed``). It is normally the pure-Python backend; when the emulated ROM
    is in use the ROM executes ``$EFAE`` itself and this function is not called.
    """
    neg = arg.is_negative()
    zero = arg.is_zero()
    if neg or (arg.exponent_byte() == 0):
        # $EFB2 branches to $EFCC for a negative argument, and $EB82 reports zero
        # as sign 0, which does not branch; either way FAC is the seed basis.
        fac = arg
    else:
        fac = Fac(backend.get_seed())
    if not neg and not zero:
        fac = backend.mul(fac, Fac(MULTIPLIER))
        fac = backend.add(fac, Fac(ADDEND))
    fac = Fac(swap_significand(fac.raw()))
    fac = Fac(normalise_to_half(fac.raw()))
    fac = backend.round_fac(fac)
    backend.set_seed(fac.raw())
    return fac