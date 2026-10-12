"""Applesoft's floating-point routines, transcribed into Python.

This is not an emulator: no ROM byte is read or executed at run time (the few
constants the routines use are copied into the code). Each routine below was
written from a disassembly of the Apple IIe ROM, instruction by instruction, as
Python statements on the same zero-page cells, the accumulator, the X and Y
registers and the carry flag. The point is to show that a program written in
another language can do Applesoft's arithmetic bit for bit, provided it copies
the ROM's algorithms exactly rather than computing an exact result and rounding
it. ``tests/test_exact.py`` holds it to the ROM operand by operand.

The cells are the ROM's own:

======  ========================================================
$9D-A2  FAC: exponent, four significand bytes (top bit set), sign
$AC     FAC extension byte: bits below the last place
$A5-AA  ARG: exponent, four significand bytes (top bit set), sign
$AB     sign comparison (``$A2 XOR $AA``)
$92     extension of the larger operand during an addition
$A4     sign extension used by the shift routine
$62-65  RESULT, the product or quotient being built
$99-9C  FIN's digit counters and flags
$A3     FIN's sign
======  ========================================================
"""

from __future__ import annotations

__all__ = ["Fp", "FpError"]


class FpError(Exception):
    """An Applesoft error: ``code`` is the number the ROM leaves in X at $D412."""

    def __init__(self, code: int, msg: str = ""):
        super().__init__(msg or f"Applesoft error {code}")
        self.code = code


OVERFLOW = 0x45          # 69
DIVISION_BY_ZERO = 0x85  # 133


class Fp:
    """The floating-point state of the interpreter and its routines."""

    def __init__(self):
        self.z = bytearray(256)
        self.a = self.x = self.y = 0
        self.c = 0

    # ------------------------------------------------------------- helpers
    def _adc(self, v: int) -> int:
        r = self.a + v + self.c
        self.c = r >> 8
        self.a = r & 0xFF
        return self.a

    def _sbc(self, v: int) -> int:
        r = self.a - v - (1 - self.c)
        self.c = 1 if r >= 0 else 0
        self.a = r & 0xFF
        return self.a

    def _ror(self, addr: int):
        v = self.z[addr]
        self.z[addr] = (v >> 1) | (self.c << 7)
        self.c = v & 1

    def _rol(self, addr: int):
        v = self.z[addr]
        self.z[addr] = ((v << 1) & 0xFF) | self.c
        self.c = v >> 7

    def _asl(self, addr: int):
        v = self.z[addr]
        self.z[addr] = (v << 1) & 0xFF
        self.c = v >> 7

    def _lsr(self, addr: int):
        v = self.z[addr]
        self.z[addr] = v >> 1
        self.c = v & 1

    def _inc(self, addr: int) -> int:
        self.z[addr] = (self.z[addr] + 1) & 0xFF
        return self.z[addr]

    # ------------------------------------------------------ ERROR ($D412)
    @staticmethod
    def _error(code: int):
        raise FpError(code)

    # ------------------------------------------------ load and store FAC
    def load_fac(self, five: bytes, ext: int = 0):
        """FAC from a value's five bytes, as $EAF9 (MOVFM) does, then $AC."""
        z = self.z
        z[0x9D] = five[0]
        z[0xA2] = five[1]
        z[0x9E] = five[1] | 0x80
        z[0x9F], z[0xA0], z[0xA1] = five[2], five[3], five[4]
        z[0xAC] = ext

    def load_arg(self, five: bytes):
        """ARG from memory, as $E9E3 does; also sets $AB. Leaves A = $9D."""
        z = self.z
        z[0xA9], z[0xA8], z[0xA7] = five[4], five[3], five[2]
        z[0xAA] = five[1]
        z[0xAB] = five[1] ^ z[0xA2]
        z[0xA6] = five[1] | 0x80
        z[0xA5] = five[0]
        self.a = z[0x9D]

    def fac(self) -> tuple[bytes, int]:
        """FAC as a stored value's five bytes (sign in byte 1), and $AC."""
        z = self.z
        if z[0x9D] == 0:
            return bytes(5), 0
        return bytes((z[0x9D], (z[0x9E] & 0x7F) | (z[0xA2] & 0x80),
                      z[0x9F], z[0xA0], z[0xA1])), z[0xAC]

    # ------------------------------------------------ FSUBT ($E7AA)
    def fsubt(self):
        z = self.z
        z[0xA2] ^= 0xFF
        z[0xAB] = z[0xA2] ^ z[0xAA]
        self.a = z[0x9D]
        self.faddt()

    # ------------------------------------------------ FADDT ($E7C1)
    def faddt(self):
        z = self.z
        if z[0x9D] == 0:                 # E7C1 BNE / E7C3 JMP $EB53
            self._copy_arg_to_fac()
            return
        self.x = z[0xAC]                 # E7C6
        z[0x92] = self.x
        self.x = 0xA5                    # E7CA
        self.a = z[0xA5]                 # E7CC
        self._fadd_e7ce()

    def _fadd_e7ce(self):
        z = self.z
        self.y = self.a                  # E7CE TAY
        if self.a == 0:                  # BEQ $E79F: ARG is zero, FAC stands
            return
        self.c = 1                       # E7D1 SEC
        self._sbc(z[0x9D])               # E7D2 SBC $9D
        if self.a == 0:                  # E7D4 BEQ $E7FA
            return self._fadd_e7fa()
        if self.c == 0:                  # E7D6 BCC $E7EA
            self.y = 0                   # E7EA
            z[0xAC] = 0
        else:
            z[0x9D] = self.y             # E7D8
            self.y = z[0xAA]
            z[0xA2] = self.y
            self.a ^= 0xFF               # E7DE EOR #$FF
            self._adc(0)                 # E7E0 ADC #$00 (C is set)
            self.y = 0
            z[0x92] = 0
            self.x = 0x9D
        # E7EE CMP #$F9 ; BMI $E7B9
        r = (self.a - 0xF9) & 0xFF
        self.c = 1 if self.a >= 0xF9 else 0
        if r & 0x80:
            self._shift_e8f0()           # E7B9 JSR $E8F0 ; BCC $E7FA
            return self._fadd_e7fa()
        self.y = self.a                  # E7F2 TAY
        self.a = z[0xAC]                 # E7F3 LDA $AC
        self._lsr((1 + self.x) & 0xFF)   # E7F5 LSR $01,X
        self._shift_e907()               # E7F7 JSR $E907
        return self._fadd_e7fa()

    def _fadd_e7fa(self):
        z = self.z
        if not (z[0xAB] & 0x80):         # E7FA BIT $AB ; BPL $E855
            return self._fadd_e855()
        self.y = 0x9D                    # E7FE
        if self.x != 0xA5:               # E800 CPX #$A5 ; BEQ $E806
            self.y = 0xA5
        self.c = 1                       # E806 SEC
        self.a ^= 0xFF                   # EOR #$FF
        self._adc(z[0x92])               # ADC $92
        z[0xAC] = self.a
        x, y = self.x, self.y
        for k, dst in ((4, 0xA1), (3, 0xA0), (2, 0x9F), (1, 0x9E)):
            self.a = z[(y + k) & 0xFF]
            self._sbc(z[(x + k) & 0xFF])
            z[dst] = self.a
        if self.c == 0:                  # E829 BCS $E82E ; JSR $E89E
            self._complement_e89e()
        self._normalize_e82e()

    def _fadd_e855(self):
        z = self.z
        self._adc(z[0x92])               # E855 ADC $92
        z[0xAC] = self.a
        for fa, aa in ((0xA1, 0xA9), (0xA0, 0xA8), (0x9F, 0xA7), (0x9E, 0xA6)):
            self.a = z[fa]
            self._adc(z[aa])
            z[fa] = self.a
        self._e88d()

    # ------------------------------------------------ NORMALIZE ($E82E)
    def _normalize_e82e(self):
        z = self.z
        self.y = 0                       # E82E LDY #$00
        self.a = 0                       # TYA
        self.c = 0                       # CLC
        while True:
            self.x = z[0x9E]             # E832 LDX $9E
            if self.x != 0:              # BNE $E880
                break
            z[0x9E] = z[0x9F]
            z[0x9F] = z[0xA0]
            z[0xA0] = z[0xA1]
            z[0xA1] = z[0xAC]
            z[0xAC] = self.y
            self._adc(8)                 # E848 ADC #$08
            if self.a == 0x20:           # CMP #$20 ; BNE $E832
                self._zero_e84e()
                return
        # E880 BPL $E874: the N flag is bit 7 of $9E (from LDX or from ROL)
        n = z[0x9E] & 0x80
        while not n:
            self._adc(1)                 # E874 ADC #$01
            self._asl(0xAC)
            self._rol(0xA1)
            self._rol(0xA0)
            self._rol(0x9F)
            self._rol(0x9E)
            n = z[0x9E] & 0x80
        self.c = 1                       # E882 SEC
        self._sbc(z[0x9D])               # SBC $9D
        if self.c:                       # BCS $E84E
            self._zero_e84e()
            return
        self.a ^= 0xFF                   # EOR #$FF
        self._adc(1)                     # ADC #$01
        z[0x9D] = self.a
        self._e88d()

    def _zero_e84e(self):
        self.a = 0
        self.z[0x9D] = 0
        self.z[0xA2] = 0

    def _e88d(self):
        z = self.z
        if self.c == 0:                  # E88D BCC $E89D
            return
        if self._inc(0x9D) == 0:         # E88F INC $9D ; BEQ $E8D5
            self._error(OVERFLOW)
        self._ror(0x9E)
        self._ror(0x9F)
        self._ror(0xA0)
        self._ror(0xA1)
        self._ror(0xAC)

    # ------------------------------------------------ COMPLEMENT ($E89E)
    def _complement_e89e(self):
        z = self.z
        z[0xA2] ^= 0xFF
        self._complement_e8a4()

    def _complement_e8a4(self):
        z = self.z
        for addr in (0x9E, 0x9F, 0xA0, 0xA1, 0xAC):
            z[addr] ^= 0xFF
        self._increment_e8c2()

    def _increment_e8c2(self):
        z = self.z
        for addr in (0xAC, 0xA1, 0xA0, 0x9F, 0x9E):
            if self._inc(addr) != 0:
                return

    def _increment_e8c6(self):
        """$E8C6: add one to the significand (ROUND.FAC's step). Z reports a wrap."""
        z = self.z
        for addr in (0xA1, 0xA0, 0x9F, 0x9E):
            if self._inc(addr) != 0:
                return False
        return True

    # ------------------------------------------------ SHIFT RIGHT ($E8DA-$E912)
    def _shift_byte_e8dc(self):
        z, x = self.z, self.x
        z[0xAC] = z[(x + 4) & 0xFF]
        z[(x + 4) & 0xFF] = z[(x + 3) & 0xFF]
        z[(x + 3) & 0xFF] = z[(x + 2) & 0xFF]
        z[(x + 2) & 0xFF] = z[(x + 1) & 0xFF]
        z[(x + 1) & 0xFF] = z[0xA4]

    def _shift_e8da(self):
        """SHIFT.RIGHT1: X = RESULT - 1, then as $E8DC."""
        self.x = 0x61
        self._shift_byte_e8dc()
        self._shift_e8f0()

    def _shift_e8f0(self):
        """$E8F0: shift the operand at X right by -A bits (A negative)."""
        z = self.z
        while True:
            self._adc(8)                 # E8F0 ADC #$08
            if self.a & 0x80 or self.a == 0:   # BMI / BEQ $E8DC
                self._shift_byte_e8dc()
                continue
            break
        self._sbc(8)                     # E8F6 SBC #$08
        self.y = self.a                  # TAY
        self.a = z[0xAC]                 # LDA $AC
        if self.c:                       # BCS $E911
            self.c = 0
            return
        self._shift_bits_e8fd()

    def _shift_bits_e8fd(self):
        z, x = self.z, self.x
        while True:
            self._asl((x + 1) & 0xFF)    # E8FD ASL $01,X
            if self.c:                   # BCC $E903
                self._inc((x + 1) & 0xFF)
            self._ror((x + 1) & 0xFF)    # E903
            self._shift_e907(first=False)
            return

    def _shift_e907(self, first: bool = True):
        """$E905/$E907 and the loop: Y counts up from a negative bit count."""
        z, x = self.z, self.x
        while True:
            if not first:
                self._ror((x + 1) & 0xFF)    # E905 ROR $01,X
            first = False
            self._ror((x + 2) & 0xFF)        # E907
            self._ror((x + 3) & 0xFF)
            self._ror((x + 4) & 0xFF)
            v = self.a                       # E90D ROR A
            self.a = (v >> 1) | (self.c << 7)
            self.c = v & 1
            self.y = (self.y + 1) & 0xFF     # E90E INY
            if self.y == 0:                  # BNE $E8FD
                break
            self._asl((x + 1) & 0xFF)        # E8FD
            if self.c:
                self._inc((x + 1) & 0xFF)
            self._ror((x + 1) & 0xFF)        # E903
        self.c = 0                           # E911 CLC

    # ------------------------------------------------ FMULTT ($E982)
    def fmultt(self):
        z = self.z
        if z[0x9D] == 0:                 # E982 BNE / JMP $E9E2 (RTS)
            return
        if not self._add_exponents_ea0e():
            return
        z[0x62] = z[0x63] = z[0x64] = z[0x65] = 0
        for addr in (0xAC, 0xA1, 0xA0, 0x9F):
            self.a = z[addr]
            self._multiply1_e9b0()
        self.a = z[0x9E]
        self._multiply2_e9b5()
        self._copy_result_eae6()

    def _multiply1_e9b0(self):
        if self.a != 0:
            self._multiply2_e9b5()
        else:
            self._shift_e8da()

    def _multiply2_e9b5(self):
        z = self.z
        v = self.a                       # E9B5 LSR A
        self.c = v & 1
        self.a = (v >> 1) | 0x80         # ORA #$80
        while True:
            self.y = self.a              # E9B8 TAY
            if self.c:                   # BCC $E9D4
                self.c = 0
                for r, g in ((0x65, 0xA9), (0x64, 0xA8), (0x63, 0xA7), (0x62, 0xA6)):
                    self.a = z[r]
                    self._adc(z[g])
                    z[r] = self.a
            for r in (0x62, 0x63, 0x64, 0x65, 0xAC):   # E9D4
                self._ror(r)
            self.a = self.y              # TYA
            v = self.a                   # LSR A
            self.c = v & 1
            self.a = v >> 1
            if self.a == 0:              # BNE $E9B8
                return

    def _add_exponents_ea0e(self) -> bool:
        """$EA0E. Returns False when the product or quotient underflows to zero."""
        z = self.z
        self.a = z[0xA5]
        if self.a == 0:                  # BEQ $EA31: zero, pop and clear FAC
            self._zero_e84e()
            return False
        self.c = 0
        self._adc(z[0x9D])               # EA13 ADC $9D
        if self.c == 0:                  # BCC $EA1B
            if not (self.a & 0x80):      # EA1B BPL $EA31
                self._zero_e84e()
                return False
            self.c = 0
        else:
            if self.a & 0x80:            # BMI $EA36
                self._error(OVERFLOW)
            self.c = 0                   # CLC
        self._adc(0x80)                  # EA1D ADC #$80
        z[0x9D] = self.a
        if self.a == 0:                  # BNE $EA26 ; JMP $E852: STA $A2, RTS
            z[0xA2] = 0                  # the routine carries on with a zero exponent
            return True
        z[0xA2] = z[0xAB]                # EA26
        return True

    def _copy_result_eae6(self):
        z = self.z
        z[0x9E], z[0x9F], z[0xA0], z[0xA1] = z[0x62], z[0x63], z[0x64], z[0x65]
        self._normalize_e82e()

    # ------------------------------------------------ FDIVT ($EA69)
    def fdivt(self):
        """ARG / FAC. A zero divisor is error 133."""
        z = self.z
        if z[0x9D] == 0:                 # EA69 BEQ $EAE1
            self._error(DIVISION_BY_ZERO)
        self.round_eb72()                # EA6B
        self.a = 0                       # EA6E
        self.c = 1
        self._sbc(z[0x9D])
        z[0x9D] = self.a
        if not self._add_exponents_ea0e():
            return
        if self._inc(0x9D) == 0:         # EA78 INC $9D ; BEQ $EA36
            self._error(OVERFLOW)
        self.x = 0xFC                    # EA7C LDX #$FC
        self.a = 0x01                    # LDA #$01
        state = "ea80"
        while True:
            if state == "ea80":
                # compare ARG with FAC, byte by byte from the top (CPY sets C)
                cmpc = 1
                for g, f in ((0xA6, 0x9E), (0xA7, 0x9F), (0xA8, 0xA0), (0xA9, 0xA1)):
                    cmpc = 1 if z[g] >= z[f] else 0
                    if z[g] != z[f]:
                        break
                self.c = cmpc
                state = "ea96"
            if state == "ea96":
                saved_c = self.c         # PHP
                v = self.a               # ROL A
                self.a = ((v << 1) & 0xFF) | self.c
                self.c = v >> 7
                if self.c:               # BCC $EAA3
                    self.x = (self.x + 1) & 0xFF   # INX
                    z[(0x65 + self.x) & 0xFF] = self.a
                    if self.x == 0:      # BEQ $EAD1
                        self.a = 0x40
                        state = "eaa3"
                    elif not (self.x & 0x80):   # BPL $EAD5
                        for _ in range(6):
                            self.a = (self.a << 1) & 0xFF
                        z[0xAC] = self.a
                        self.c = saved_c # PLP
                        self._copy_result_eae6()
                        return
                    else:
                        self.a = 0x01    # EAA1
                        state = "eaa3"
                else:
                    state = "eaa3"
            if state == "eaa3":
                self.c = saved_c         # PLP
                if self.c:               # BCS $EAB4: subtract FAC from ARG
                    self.y = self.a
                    for g, f in ((0xA9, 0xA1), (0xA8, 0xA0), (0xA7, 0x9F), (0xA6, 0x9E)):
                        self.a = z[g]
                        self._sbc(z[f])
                        z[g] = self.a
                    self.a = self.y
                # EAA6: shift ARG left
                self._asl(0xA9)
                self._rol(0xA8)
                self._rol(0xA7)
                self._rol(0xA6)
                if self.c:               # BCS $EA96
                    state = "ea96"
                elif z[0xA6] & 0x80:     # BMI $EA80
                    state = "ea80"
                else:                    # BPL $EA96
                    state = "ea96"

    # ------------------------------------------------ ROUND.FAC ($EB72)
    def round_eb72(self):
        z = self.z
        if z[0x9D] == 0:
            return
        self._asl(0xAC)
        if not self.c:
            return
        if not self._increment_e8c6():
            return
        if self._inc(0x9D) == 0:         # $E88F
            self._error(OVERFLOW)
        self.c = 1                       # the carry out of the increment
        self._ror(0x9E)
        self._ror(0x9F)
        self._ror(0xA0)
        self._ror(0xA1)
        self._ror(0xAC)

    # ------------------------------------------------ $EB63: round, FAC to ARG
    def _fac_to_arg_eb63(self):
        z = self.z
        self.round_eb72()
        for k in range(6, 0, -1):
            z[0xA4 + k] = z[0x9C + k]
        z[0xAC] = 0
        self.x = 0
        self.a = z[0x9D]

    def _copy_arg_to_fac(self):
        """$EB53: FAC = ARG, extension cleared."""
        z = self.z
        z[0xA2] = z[0xAA]
        for k in range(5, 0, -1):
            z[0x9C + k] = z[0xA4 + k]
        z[0xAC] = 0

    # ------------------------------------------------ FCOMP ($EBB2)
    def fcomp(self, five: bytes) -> int:
        """Compare FAC with a value in memory: 1 if FAC is larger, 0, or -1 ($FF)."""
        z = self.z
        if five[0] == 0:                 # EBBC BEQ $EB82: the sign of FAC
            return self._sign_eb82()
        if (five[1] ^ z[0xA2]) & 0x80:   # EBC2 BMI $EB86
            return self._sign_eb86()
        if five[0] != z[0x9D]:
            self.c = 1 if five[0] >= z[0x9D] else 0
            return self._fcomp_ebe9()
        if (five[1] | 0x80) != z[0x9E]:
            self.c = 1 if (five[1] | 0x80) >= z[0x9E] else 0
            return self._fcomp_ebe9()
        if five[2] != z[0x9F]:
            self.c = 1 if five[2] >= z[0x9F] else 0
            return self._fcomp_ebe9()
        if five[3] != z[0xA0]:
            self.c = 1 if five[3] >= z[0xA0] else 0
            return self._fcomp_ebe9()
        self.c = 1 if 0x7F >= z[0xAC] else 0      # EBDF LDA #$7F ; CMP $AC
        self.a = five[4]
        self._sbc(z[0xA1])               # EBE5 SBC $A1
        if self.a == 0:                  # BEQ $EC11 (RTS with A = 0)
            return 0
        return self._fcomp_ebe9()

    def _fcomp_ebe9(self) -> int:
        a = self.z[0xA2]
        if self.c:                       # BCC $EBEF ; EOR #$FF
            a ^= 0xFF
        return -1 if (a & 0x80) else 1   # $EB88: ROL, then $FF or $01

    def _sign_eb82(self) -> int:
        if self.z[0x9D] == 0:
            return 0
        return self._sign_eb86()

    def _sign_eb86(self) -> int:
        return -1 if (self.z[0xA2] & 0x80) else 1

    # ------------------------------------------------ INT ($EC23) and QINT ($EBF2)
    def int_ec23(self):
        z = self.z
        if z[0x9D] >= 0xA0:              # EC25 CMP #$A0 ; BCS RTS
            return
        self._qint_ebf2()
        z[0xAC] = self.y                 # EC2C STY $AC
        self.a = z[0xA2]
        z[0xA2] = self.y
        self.a ^= 0x80                   # EOR #$80
        v = self.a                       # ROL A
        self.a = ((v << 1) & 0xFF) | self.c
        self.c = v >> 7
        z[0x9D] = 0xA0
        z[0x0D] = z[0xA1]
        if self.c == 0:                  # $E829: BCS $E82E ; JSR $E89E
            self._complement_e89e()
        self._normalize_e82e()

    def _qint_ebf2(self):
        z = self.z
        self.a = z[0x9D]
        if self.a == 0:                  # BEQ $EC40
            z[0x9E] = z[0x9F] = z[0xA0] = z[0xA1] = 0
            self.y = 0
            return
        self.c = 1
        self._sbc(0xA0)                  # EBF7 SBC #$A0
        if z[0xA2] & 0x80:               # BIT $A2 ; BPL $EC06
            self.x = self.a
            z[0xA4] = 0xFF
            self._complement_e8a4()
            self.a = self.x
        self.x = 0x9D                    # EC06
        if (self.a - 0xF9) & 0x80:       # CMP #$F9 ; BPL $EC12
            self.c = 1 if self.a >= 0xF9 else 0
            self._shift_e8f0()           # EC0C JSR $E8F0
            z[0xA4] = self.y             # STY $A4
            return
        self.y = self.a                  # EC12 TAY
        self.a = z[0xA2] & 0x80
        self._lsr(0x9E)
        self.a |= z[0x9E]
        z[0x9E] = self.a
        self._shift_e907()               # EC1D JSR $E907
        z[0xA4] = self.y                 # STY $A4

    # ------------------------------------------------ FIN ($EC4A) arithmetic
    def _mul10_ea39(self):
        z = self.z
        self._fac_to_arg_eb63()          # EA39 JSR $EB63
        self.x = self.a                  # TAX
        if self.a == 0:                  # BEQ $EA4F
            return
        self.c = 0
        self._adc(2)                     # ADC #$02
        if self.c:                       # BCS $EA36
            self._error(OVERFLOW)
        self.x = 0
        z[0xAB] = 0
        self._fadd_e7ce()                # JSR $E7CE: 4 x FAC + FAC
        if self._inc(0x9D) == 0:         # INC $9D ; BEQ $EA36
            self._error(OVERFLOW)

    def _div10_ea55(self):
        z = self.z
        self._fac_to_arg_eb63()          # EA55 JSR $EB63
        z[0xAB] = 0                      # LDX #$00 ; STX $AB
        self.load_fac(bytes((0x84, 0x20, 0, 0, 0)))   # $EAF9 from $EA50: 10
        self.fdivt()

    def _add_digit_ecd5(self, digit: int):
        z = self.z
        self._fac_to_arg_eb63()          # ECD6 JSR $EB63
        self.a = digit                   # PLA
        self._float_eb93()               # JSR $EB93
        z[0xAB] = z[0xAA] ^ z[0xA2]
        self.x = z[0x9D]
        self.a = z[0x9D]
        self.faddt()                     # JMP $E7C1

    def _float_eb93(self):
        """$EB93: FAC = the unsigned byte in A, normalised."""
        z = self.z
        z[0x9E] = self.a
        z[0x9F] = 0
        self.x = 0x88
        self.c = 0 if (z[0x9E] & 0x80) else 1   # EB9B EOR #$FF ; ROL A
        z[0xA1] = z[0xA0] = 0
        z[0x9D] = self.x
        z[0xAC] = 0
        z[0xA2] = 0
        if self.c == 0:                  # $E829
            self._complement_e89e()
        self._normalize_e82e()

    def fin(self, text: str):
        """Convert a decimal literal as $EC4A does; FAC holds the result.

        Only the forms a program's constants take are handled: digits, one
        decimal point, and an exponent written with ``E``.
        """
        z = self.z
        for k in range(0xA3, 0x98, -1):  # EC4C..EC51: clear $99-$A3
            z[k] = 0
        z[0xAC] = 0                      # the interpreter leaves $AC clear here
        s = text.strip().upper()
        i = 0
        if i < len(s) and s[i] in "+-":
            if s[i] == "-":
                z[0xA3] = 0xFF
            i += 1
        while i < len(s) and s[i].isdigit():
            if z[0x9B] & 0x80:           # ECC2 BIT $9B ; INC $99 after the point
                z[0x99] = (z[0x99] + 1) & 0xFF
            self._mul10_ea39()
            self._add_digit_ecd5(ord(s[i]) - 0x30)
            i += 1
            if i < len(s) and s[i] == "." and not (z[0x9B] & 0x80):
                z[0x9B] = 0x80           # EC98 ROR $9B with C set
                i += 1
        if i < len(s) and s[i] == "." and not (z[0x9B] & 0x80):
            z[0x9B] = 0x80
            i += 1
            while i < len(s) and s[i].isdigit():
                z[0x99] = (z[0x99] + 1) & 0xFF
                self._mul10_ea39()
                self._add_digit_ecd5(ord(s[i]) - 0x30)
                i += 1
        if i < len(s) and s[i] == "E":
            i += 1
            neg = False
            if i < len(s) and s[i] in "+-":
                neg = s[i] == "-"
                i += 1
            e = 0
            while i < len(s) and s[i].isdigit():
                e = e * 10 + (ord(s[i]) - 0x30)
                if e >= 100:
                    raise FpError(OVERFLOW)
                i += 1
            z[0x9A] = (-e) & 0xFF if neg else e
        if i != len(s):
            raise ValueError(f"not a numeric literal: {text!r}")
        # EC9E: decimal exponent minus the digits after the point
        self.a = z[0x9A]
        self.c = 1
        self._sbc(z[0x99])
        z[0x9A] = self.a
        if self.a != 0:
            if self.a & 0x80:
                while True:
                    self._div10_ea55()
                    if self._inc(0x9A) == 0:
                        break
            else:
                while True:
                    self._mul10_ea39()
                    z[0x9A] = (z[0x9A] - 1) & 0xFF
                    if z[0x9A] == 0:
                        break
        if z[0xA3] & 0x80:               # $EED0: negate
            if z[0x9D]:
                z[0xA2] ^= 0xFF


    # ------------------------------------------------ FOUT ($ED34)
    _K_1E9 = bytes.fromhex("9E6E6B2800")        # $ED14
    _K_HIGH = bytes.fromhex("9E6E6B27FD")       # $ED0F
    _K_LOW = bytes.fromhex("9B3EBC1FFD")        # $ED0A
    _K_HALF = bytes.fromhex("8000000000")       # $EE64
    _DECADES = bytes.fromhex(                   # $EE69: -1E8, 1E7, -1E6, ... -1
        "FA0A1F00" "00989680" "FFF0BDC0" "000186A0" "FFFFD8F0"
        "000003E8" "FFFFFF9C" "0000000A" "FFFFFFFF")

    def fout(self) -> str:
        """Number to text as $ED34 builds it at $0100; returns the text."""
        z = self.z
        buf = bytearray(48)                     # $00FF onwards: buf[k] is $00FF + k

        y = 0
        if z[0xA2] & 0x80:                      # ED39 BIT $A2 ; BPL $ED41
            y = 1
            buf[y] = 0x2D                       # "-"
        z[0xA2] = 0x2D                          # ED41 STA $A2: the sign is dropped
        z[0xAD] = y
        y += 1                                  # ED45 INY
        if z[0x9D] == 0:                        # ED48 ; JMP $EE57
            buf[y] = 0x30
            buf[y + 1] = 0
            return self._fout_text(buf)
        a = 0
        if z[0x9D] <= 0x80:                     # CPX #$80 ; BEQ / BCS
            self.load_arg(self._K_1E9)          # ED57 JSR $E97F: FAC * 1E9
            self.fmultt()
            a = 0xF7
        z[0x99] = a
        state = "ed62"
        while True:
            if state == "ed62":
                r = self.fcomp(self._K_HIGH)
                if r == 0:
                    state = "ed89"
                    continue
                if r > 0:
                    state = "ed7f"
                    continue
                state = "ed6d"
            if state == "ed6d":
                r = self.fcomp(self._K_LOW)
                if r != 0 and r > 0:            # BEQ $ED78 ; BPL $ED86
                    state = "ed86"
                    continue
                self._mul10_ea39()              # ED78
                z[0x99] = (z[0x99] - 1) & 0xFF
                if z[0x99] != 0:
                    state = "ed6d"
                    continue
                state = "ed7f"
            if state == "ed7f":
                self._div10_ea55()
                z[0x99] = (z[0x99] + 1) & 0xFF
                if z[0x99] != 0:
                    state = "ed62"
                    continue
                state = "ed86"
            if state == "ed86":
                self.load_arg(self._K_HALF)     # $E7A0: FAC + .5
                self.faddt()
                state = "ed89"
            if state == "ed89":
                self._qint_ebf2()
                break
        # ED8C: where the point goes, and the exponent to print
        x = 1
        self.c = 0
        self.a = z[0x99]
        self._adc(0x0A)
        if self.a & 0x80:                       # BMI $ED9E
            self.c = 1
        else:
            if self.a >= 0x0B:                  # CMP #$0B ; BCS $ED9F (C set)
                self.c = 1
            else:
                self.c = 0                      # (CMP left C clear)
                self._adc(0xFF)                 # ED99 ADC #$FF
                x = self.a
                self.a = 0x02
                self.c = 1                      # ED9E SEC
        self._sbc(0x02)                         # ED9F SBC #$02
        z[0x9A] = self.a
        z[0x99] = x
        if x == 0 or (x & 0x80):                # TXA ; BEQ $EDAA ; BPL $EDBD
            y = z[0xAD]
            y += 1
            buf[y] = 0x2E                       # "."
            if x != 0:
                y += 1
                buf[y] = 0x30                   # "0"
            z[0xAD] = y
        # EDBD: the digits, by adding the decades in turn
        y = 0
        x = 0x80
        while True:
            while True:                         # EDC1
                self.c = 0
                for k, addr in ((3, 0xA1), (2, 0xA0), (1, 0x9F), (0, 0x9E)):
                    self.a = z[addr]
                    self._adc(self._DECADES[y + k])
                    z[addr] = self.a
                x = (x + 1) & 0xFF              # INX
                n = x & 0x80
                if self.c:                      # BCS $EDE5 ; BMI $EDC1
                    if n:
                        continue
                    break
                if not n:                       # BPL $EDC1
                    continue
                break                           # BMI $EDE7
            self.a = x                          # EDE7 TXA
            if self.c:                          # BCC $EDEE
                self.a ^= 0xFF
                self._adc(0x0A)
            self._adc(0x2F)                     # EDEE ADC #$2F
            y += 4
            z[0x83] = y
            yy = z[0xAD] + 1
            x = self.a
            buf[yy] = self.a & 0x7F             # the digit
            z[0x99] = (z[0x99] - 1) & 0xFF
            if z[0x99] == 0:
                yy += 1
                buf[yy] = 0x2E                  # "."
            z[0xAD] = yy
            y = z[0x83]
            x = (x ^ 0xFF) & 0x80               # EE0D
            if y == 0x24:
                break
        # EE17: drop trailing zeros, and a point left at the end
        y = z[0xAD]
        while True:
            ch = buf[y]
            y -= 1
            if ch != 0x30:
                break
        if ch != 0x2E:
            y += 1
        if z[0x9A] == 0:                        # EE28 LDX $9A ; BEQ $EE5A
            buf[y + 1] = 0
            return self._fout_text(buf)
        e = z[0x9A]
        sign = 0x2B
        if e & 0x80:
            e = (-e) & 0xFF
            sign = 0x2D
        buf[y + 2] = sign                       # EE36 STA $0101,Y
        buf[y + 1] = 0x45                       # "E"
        tens = e // 10
        buf[y + 4] = 0x30 + e % 10
        buf[y + 3] = 0x30 + tens
        buf[y + 5] = 0
        return self._fout_text(buf)

    @staticmethod
    def _fout_text(buf: bytearray) -> str:
        out = bytearray()
        for b in buf[1:]:                       # the text starts at $0100
            if b == 0:
                break
            out.append(b)
        return out.decode("ascii")

# ====================================================================== backend
from .fac import Fac  # noqa: E402


class ExactBackend:
    """Applesoft arithmetic in Python, transcribed from the ROM (see the module).

    The interface and the evaluator's conventions are those of
    :class:`oregon.applesoft.rom.RomBackend`: the left operand of an operator is
    rounded, the right operand keeps its extension byte, and an operator's result
    carries the live extension byte until it is stored. ``RND`` is the integer
    model in :mod:`oregon.applesoft.rng`, exact on every state the game reaches,
    rather than a transcription of the routine at ``$EFAE``.
    """

    name = "python-exact"
    is_rom = False

    def __init__(self):
        self.fp = Fp()
        self._seed = bytes(5)
        self._literals = {}

    # -------------------------------------------------------------- plumbing
    def _result(self) -> Fac:
        b, ext = self.fp.fac()
        if b[0] == 0:
            return Fac(bytes(5))
        return Fac(b, ext)

    def _op(self, left: Fac, right: Fac, which: str) -> Fac:
        left = self.round_fac(left)
        fp = self.fp
        fp.load_fac(right.b, right.ext)
        fp.load_arg(left.raw())
        try:
            getattr(fp, which)()
        except FpError as e:
            from .rom import RomError
            raise RomError(e.code, "Applesoft error") from None
        return self._result()

    def add(self, a: Fac, b: Fac) -> Fac:
        return self._op(a, b, "faddt")

    def sub(self, a: Fac, b: Fac) -> Fac:
        return self._op(a, b, "fsubt")

    def mul(self, a: Fac, b: Fac) -> Fac:
        return self._op(a, b, "fmultt")

    def div(self, a: Fac, b: Fac) -> Fac:
        if b.is_zero():
            from .rom import RomError
            raise RomError(DIVISION_BY_ZERO, "division by zero")
        return self._op(a, b, "fdivt")

    # ------------------------------------------------------ constant forms
    def _settle(self) -> Fac:
        """The ROM backend's rounding of a constant-form result, byte for byte."""
        z = self.fp.z
        if z[0xAC] & 0x80:
            for addr in (0xA1, 0xA0, 0x9F, 0x9E):
                z[addr] = (z[addr] + 1) & 0xFF
                if z[addr]:
                    break
            else:
                z[0x9D] = (z[0x9D] + 1) & 0xFF
                if z[0x9D] == 0:
                    from .rom import RomError
                    raise RomError(OVERFLOW, "rounding carried out of the range")
        b, _ = self.fp.fac()
        return Fac(b)

    def _const(self, fac_value: Fac, memory_value: Fac, which: str) -> Fac:
        fp = self.fp
        fp.load_fac(fac_value.b, fac_value.ext)
        fp.load_arg(memory_value.raw())
        try:
            getattr(fp, which)()
        except FpError as e:
            from .rom import RomError
            raise RomError(e.code, "Applesoft error") from None
        return self._settle()

    def add_const(self, a: Fac, b: Fac) -> Fac:
        return self.add(a, b)

    def mul_const(self, a: Fac, b: Fac) -> Fac:
        if a.is_zero() or b.is_zero():
            return Fac(bytes(5))
        mag = self._const(self.abs_(a), self.abs_(b), "fmultt")
        return self.neg(mag) if (a.is_negative() != b.is_negative()) else mag

    def div_const(self, a: Fac, b: Fac) -> Fac:
        if b.is_zero():
            from .rom import RomError
            raise RomError(DIVISION_BY_ZERO, "division by zero")
        mag = self._const(self.abs_(b), self.abs_(a), "fdivt")
        return self.neg(mag) if (a.is_negative() != b.is_negative()) else mag

    # --------------------------------------------------------- sign and cast
    def neg(self, a: Fac) -> Fac:
        if a.is_zero():
            return a
        b = bytearray(a.b)
        b[1] ^= 0x80
        return Fac(bytes(b), a.ext)

    def abs_(self, a: Fac) -> Fac:
        return self.neg(a) if a.is_negative() else a

    def int_(self, a: Fac) -> Fac:
        if a.is_zero():
            return a
        self.fp.load_fac(a.b, a.ext)
        self.fp.int_ec23()
        return self._result()

    def round_fac(self, a: Fac) -> Fac:
        if a.is_zero():
            return Fac(bytes(5))
        if not (a.ext & 0x80):
            return a if a.ext == 0 else Fac(a.b)
        fp = self.fp
        fp.load_fac(a.b, a.ext)
        try:
            fp.round_eb72()
        except FpError as e:
            from .rom import RomError
            raise RomError(e.code, "Applesoft error") from None
        b, _ = fp.fac()
        return Fac(b)

    def cmp(self, a: Fac, b: Fac) -> int:
        a = self.round_fac(a)
        if b.ext & 0x80 and not b.is_zero():
            self.fp.load_fac(b.b, b.ext)
            return -self.fp.fcomp(a.raw())
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
        from .rng import applesoft_rnd
        return applesoft_rnd(self, arg)

    # --------------------------------------------------------------- strings
    def from_str(self, s: str) -> Fac:
        cached = self._literals.get(s)
        if cached is not None:
            return cached
        t = s.strip()
        negative = False
        if t[:1] in ("+", "-"):
            negative = t[0] == "-"
            t = t[1:]
        if not t:
            return Fac(bytes(5))
        try:
            self.fp.fin(t)
        except FpError as e:
            from .rom import RomError
            raise RomError(e.code, "Applesoft error") from None
        v = self._result()
        v = self.neg(v) if negative else v
        self._literals[s] = v
        return v

    def fmt(self, v: Fac) -> str:
        """``FOUT`` on the value as it stands, extension byte included."""
        if v.is_zero():
            return "0"
        self.fp.load_fac(v.b, v.ext)
        return self.fp.fout()
