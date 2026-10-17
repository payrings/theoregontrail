/**
 * Applesoft's floating-point routines, transcribed.
 *
 * This is a line-for-line port of `game/python/oregon/applesoft/exact.py`, which was itself written from
 * a disassembly of the Apple IIe ROM and is held to the ROM operand by operand. No ROM byte is read
 * or executed here. The cells are the ROM's own:
 *
 *   $9D-A2  FAC: exponent, four significand bytes (top bit set), sign
 *   $AC     FAC extension byte
 *   $A5-AA  ARG
 *   $AB     sign comparison; $92 extension of the larger operand in an addition
 *   $A4     sign extension used by the shift routine; $62-65 the product or quotient being built
 *   $99-9C  FIN's digit counters and flags; $A3 FIN's sign
 */

export class ApplesoftError extends Error {
  code: number;
  line: number;
  constructor(code: number, line = 0, message = "") {
    super(message || `Applesoft error ${code}`);
    this.code = code;
    this.line = line;
  }
}
export const OVERFLOW = 0x45;          // 69
export const DIVISION_BY_ZERO = 0x85;  // 133
export const ILLEGAL_QUANTITY = 53;

const K_1E9 = [0x9e, 0x6e, 0x6b, 0x28, 0x00];
const K_HIGH = [0x9e, 0x6e, 0x6b, 0x27, 0xfd];
const K_LOW = [0x9b, 0x3e, 0xbc, 0x1f, 0xfd];
const K_HALF = [0x80, 0, 0, 0, 0];
const DECADES = [
  0xfa, 0x0a, 0x1f, 0x00, 0x00, 0x98, 0x96, 0x80, 0xff, 0xf0, 0xbd, 0xc0, 0x00, 0x01, 0x86, 0xa0,
  0xff, 0xff, 0xd8, 0xf0, 0x00, 0x00, 0x03, 0xe8, 0xff, 0xff, 0xff, 0x9c, 0x00, 0x00, 0x00, 0x0a,
  0xff, 0xff, 0xff, 0xff,
];

export class Fp {
  z = new Uint8Array(256);
  a = 0; x = 0; y = 0; c = 0;

  // ------------------------------------------------------------- helpers
  private adc(v: number): number {
    const r = this.a + v + this.c;
    this.c = r >> 8;
    this.a = r & 0xff;
    return this.a;
  }
  private sbc(v: number): number {
    const r = this.a - v - (1 - this.c);
    this.c = r >= 0 ? 1 : 0;
    this.a = r & 0xff;
    return this.a;
  }
  private ror(addr: number): void {
    const v = this.z[addr];
    this.z[addr] = (v >> 1) | (this.c << 7);
    this.c = v & 1;
  }
  private rol(addr: number): void {
    const v = this.z[addr];
    this.z[addr] = ((v << 1) & 0xff) | this.c;
    this.c = v >> 7;
  }
  private asl(addr: number): void {
    const v = this.z[addr];
    this.z[addr] = (v << 1) & 0xff;
    this.c = v >> 7;
  }
  private lsr(addr: number): void {
    const v = this.z[addr];
    this.z[addr] = v >> 1;
    this.c = v & 1;
  }
  private inc(addr: number): number {
    this.z[addr] = (this.z[addr] + 1) & 0xff;
    return this.z[addr];
  }
  private error(code: number): never {
    throw new ApplesoftError(code);
  }

  // ------------------------------------------------ load and store FAC
  loadFac(five: ArrayLike<number>, ext = 0): void {
    const z = this.z;
    z[0x9d] = five[0];
    z[0xa2] = five[1];
    z[0x9e] = five[1] | 0x80;
    z[0x9f] = five[2]; z[0xa0] = five[3]; z[0xa1] = five[4];
    z[0xac] = ext;
  }
  loadArg(five: ArrayLike<number>): void {
    const z = this.z;
    z[0xa9] = five[4]; z[0xa8] = five[3]; z[0xa7] = five[2];
    z[0xaa] = five[1];
    z[0xab] = five[1] ^ z[0xa2];
    z[0xa6] = five[1] | 0x80;
    z[0xa5] = five[0];
    this.a = z[0x9d];
  }
  /** FAC as a stored value's five bytes, and $AC */
  fac(): [number[], number] {
    const z = this.z;
    if (z[0x9d] === 0) return [[0, 0, 0, 0, 0], 0];
    return [[z[0x9d], (z[0x9e] & 0x7f) | (z[0xa2] & 0x80), z[0x9f], z[0xa0], z[0xa1]], z[0xac]];
  }

  // ------------------------------------------------ FSUBT ($E7AA)
  fsubt(): void {
    const z = this.z;
    z[0xa2] ^= 0xff;
    z[0xab] = z[0xa2] ^ z[0xaa];
    this.a = z[0x9d];
    this.faddt();
  }

  // ------------------------------------------------ FADDT ($E7C1)
  faddt(): void {
    const z = this.z;
    if (z[0x9d] === 0) { this.copyArgToFac(); return; }
    this.x = z[0xac];
    z[0x92] = this.x;
    this.x = 0xa5;
    this.a = z[0xa5];
    this.faddE7ce();
  }

  private faddE7ce(): void {
    const z = this.z;
    this.y = this.a;
    if (this.a === 0) return;
    this.c = 1;
    this.sbc(z[0x9d]);
    if (this.a === 0) { this.faddE7fa(); return; }
    if (this.c === 0) {
      this.y = 0;
      z[0xac] = 0;
    } else {
      z[0x9d] = this.y;
      this.y = z[0xaa];
      z[0xa2] = this.y;
      this.a ^= 0xff;
      this.adc(0);
      this.y = 0;
      z[0x92] = 0;
      this.x = 0x9d;
    }
    const r = (this.a - 0xf9) & 0xff;
    this.c = this.a >= 0xf9 ? 1 : 0;
    if (r & 0x80) {
      this.shiftE8f0();
      this.faddE7fa();
      return;
    }
    this.y = this.a;
    this.a = z[0xac];
    this.lsr((1 + this.x) & 0xff);
    this.shiftE907(true);
    this.faddE7fa();
  }

  private faddE7fa(): void {
    const z = this.z;
    if (!(z[0xab] & 0x80)) { this.faddE855(); return; }
    this.y = 0x9d;
    if (this.x !== 0xa5) this.y = 0xa5;
    this.c = 1;
    this.a ^= 0xff;
    this.adc(z[0x92]);
    z[0xac] = this.a;
    const x = this.x, y = this.y;
    const pairs: [number, number][] = [[4, 0xa1], [3, 0xa0], [2, 0x9f], [1, 0x9e]];
    for (const [k, dst] of pairs) {
      this.a = z[(y + k) & 0xff];
      this.sbc(z[(x + k) & 0xff]);
      z[dst] = this.a;
    }
    if (this.c === 0) this.complementE89e();
    this.normalizeE82e();
  }

  private faddE855(): void {
    const z = this.z;
    this.adc(z[0x92]);
    z[0xac] = this.a;
    const pairs: [number, number][] = [[0xa1, 0xa9], [0xa0, 0xa8], [0x9f, 0xa7], [0x9e, 0xa6]];
    for (const [fa, aa] of pairs) {
      this.a = z[fa];
      this.adc(z[aa]);
      z[fa] = this.a;
    }
    this.e88d();
  }

  // ------------------------------------------------ NORMALIZE ($E82E)
  private normalizeE82e(): void {
    const z = this.z;
    this.y = 0;
    this.a = 0;
    this.c = 0;
    for (;;) {
      this.x = z[0x9e];
      if (this.x !== 0) break;
      z[0x9e] = z[0x9f];
      z[0x9f] = z[0xa0];
      z[0xa0] = z[0xa1];
      z[0xa1] = z[0xac];
      z[0xac] = this.y;
      this.adc(8);
      if (this.a === 0x20) { this.zeroE84e(); return; }
    }
    let n = z[0x9e] & 0x80;
    while (!n) {
      this.adc(1);
      this.asl(0xac);
      this.rol(0xa1);
      this.rol(0xa0);
      this.rol(0x9f);
      this.rol(0x9e);
      n = z[0x9e] & 0x80;
    }
    this.c = 1;
    this.sbc(z[0x9d]);
    if (this.c) { this.zeroE84e(); return; }
    this.a ^= 0xff;
    this.adc(1);
    z[0x9d] = this.a;
    this.e88d();
  }

  private zeroE84e(): void {
    this.a = 0;
    this.z[0x9d] = 0;
    this.z[0xa2] = 0;
  }

  private e88d(): void {
    if (this.c === 0) return;
    if (this.inc(0x9d) === 0) this.error(OVERFLOW);
    this.ror(0x9e); this.ror(0x9f); this.ror(0xa0); this.ror(0xa1); this.ror(0xac);
  }

  // ------------------------------------------------ COMPLEMENT ($E89E)
  private complementE89e(): void {
    this.z[0xa2] ^= 0xff;
    this.complementE8a4();
  }
  private complementE8a4(): void {
    const z = this.z;
    for (const addr of [0x9e, 0x9f, 0xa0, 0xa1, 0xac]) z[addr] ^= 0xff;
    this.incrementE8c2();
  }
  private incrementE8c2(): void {
    for (const addr of [0xac, 0xa1, 0xa0, 0x9f, 0x9e]) if (this.inc(addr) !== 0) return;
  }
  /** $E8C6: add one to the significand. Returns true if it wrapped */
  private incrementE8c6(): boolean {
    for (const addr of [0xa1, 0xa0, 0x9f, 0x9e]) if (this.inc(addr) !== 0) return false;
    return true;
  }

  // ------------------------------------------------ SHIFT RIGHT ($E8DA-$E912)
  private shiftByteE8dc(): void {
    const z = this.z, x = this.x;
    z[0xac] = z[(x + 4) & 0xff];
    z[(x + 4) & 0xff] = z[(x + 3) & 0xff];
    z[(x + 3) & 0xff] = z[(x + 2) & 0xff];
    z[(x + 2) & 0xff] = z[(x + 1) & 0xff];
    z[(x + 1) & 0xff] = z[0xa4];
  }
  private shiftE8da(): void {
    this.x = 0x61;
    this.shiftByteE8dc();
    this.shiftE8f0();
  }
  private shiftE8f0(): void {
    const z = this.z;
    for (;;) {
      this.adc(8);
      if ((this.a & 0x80) || this.a === 0) { this.shiftByteE8dc(); continue; }
      break;
    }
    this.sbc(8);
    this.y = this.a;
    this.a = z[0xac];
    if (this.c) { this.c = 0; return; }
    this.shiftBitsE8fd();
  }
  private shiftBitsE8fd(): void {
    const x = this.x;
    this.asl((x + 1) & 0xff);
    if (this.c) this.inc((x + 1) & 0xff);
    this.ror((x + 1) & 0xff);
    this.shiftE907(false);
  }
  private shiftE907(first: boolean): void {
    const x = this.x;
    for (;;) {
      if (!first) this.ror((x + 1) & 0xff);
      first = false;
      this.ror((x + 2) & 0xff);
      this.ror((x + 3) & 0xff);
      this.ror((x + 4) & 0xff);
      const v = this.a;
      this.a = (v >> 1) | (this.c << 7);
      this.c = v & 1;
      this.y = (this.y + 1) & 0xff;
      if (this.y === 0) break;
      this.asl((x + 1) & 0xff);
      if (this.c) this.inc((x + 1) & 0xff);
      this.ror((x + 1) & 0xff);
    }
    this.c = 0;
  }

  // ------------------------------------------------ FMULTT ($E982)
  fmultt(): void {
    const z = this.z;
    if (z[0x9d] === 0) return;
    if (!this.addExponentsEa0e()) return;
    z[0x62] = z[0x63] = z[0x64] = z[0x65] = 0;
    for (const addr of [0xac, 0xa1, 0xa0, 0x9f]) {
      this.a = z[addr];
      this.multiply1E9b0();
    }
    this.a = z[0x9e];
    this.multiply2E9b5();
    this.copyResultEae6();
  }
  private multiply1E9b0(): void {
    if (this.a !== 0) this.multiply2E9b5(); else this.shiftE8da();
  }
  private multiply2E9b5(): void {
    const z = this.z;
    const v = this.a;
    this.c = v & 1;
    this.a = (v >> 1) | 0x80;
    for (;;) {
      this.y = this.a;
      if (this.c) {
        this.c = 0;
        const pairs: [number, number][] = [[0x65, 0xa9], [0x64, 0xa8], [0x63, 0xa7], [0x62, 0xa6]];
        for (const [r, g] of pairs) {
          this.a = z[r];
          this.adc(z[g]);
          z[r] = this.a;
        }
      }
      for (const r of [0x62, 0x63, 0x64, 0x65, 0xac]) this.ror(r);
      this.a = this.y;
      const w = this.a;
      this.c = w & 1;
      this.a = w >> 1;
      if (this.a === 0) return;
    }
  }
  private addExponentsEa0e(): boolean {
    const z = this.z;
    this.a = z[0xa5];
    if (this.a === 0) { this.zeroE84e(); return false; }
    this.c = 0;
    this.adc(z[0x9d]);
    if (this.c === 0) {
      if (!(this.a & 0x80)) { this.zeroE84e(); return false; }
      this.c = 0;
    } else {
      if (this.a & 0x80) this.error(OVERFLOW);
      this.c = 0;
    }
    this.adc(0x80);
    z[0x9d] = this.a;
    if (this.a === 0) { z[0xa2] = 0; return true; }
    z[0xa2] = z[0xab];
    return true;
  }
  private copyResultEae6(): void {
    const z = this.z;
    z[0x9e] = z[0x62]; z[0x9f] = z[0x63]; z[0xa0] = z[0x64]; z[0xa1] = z[0x65];
    this.normalizeE82e();
  }

  // ------------------------------------------------ FDIVT ($EA69)
  fdivt(): void {
    const z = this.z;
    if (z[0x9d] === 0) this.error(DIVISION_BY_ZERO);
    this.roundEb72();
    this.a = 0;
    this.c = 1;
    this.sbc(z[0x9d]);
    z[0x9d] = this.a;
    if (!this.addExponentsEa0e()) return;
    if (this.inc(0x9d) === 0) this.error(OVERFLOW);
    this.x = 0xfc;
    this.a = 0x01;
    let state = "ea80";
    let savedC = 0;
    for (;;) {
      if (state === "ea80") {
        let cmpc = 1;
        const pairs: [number, number][] = [[0xa6, 0x9e], [0xa7, 0x9f], [0xa8, 0xa0], [0xa9, 0xa1]];
        for (const [g, f] of pairs) {
          cmpc = z[g] >= z[f] ? 1 : 0;
          if (z[g] !== z[f]) break;
        }
        this.c = cmpc;
        state = "ea96";
      }
      if (state === "ea96") {
        savedC = this.c;
        const v = this.a;
        this.a = ((v << 1) & 0xff) | this.c;
        this.c = v >> 7;
        if (this.c) {
          this.x = (this.x + 1) & 0xff;
          z[(0x65 + this.x) & 0xff] = this.a;
          if (this.x === 0) {
            this.a = 0x40;
            state = "eaa3";
          } else if (!(this.x & 0x80)) {
            for (let i = 0; i < 6; i++) this.a = (this.a << 1) & 0xff;
            z[0xac] = this.a;
            this.c = savedC;
            this.copyResultEae6();
            return;
          } else {
            this.a = 0x01;
            state = "eaa3";
          }
        } else {
          state = "eaa3";
        }
      }
      if (state === "eaa3") {
        this.c = savedC;
        if (this.c) {
          this.y = this.a;
          const pairs: [number, number][] = [[0xa9, 0xa1], [0xa8, 0xa0], [0xa7, 0x9f], [0xa6, 0x9e]];
          for (const [g, f] of pairs) {
            this.a = z[g];
            this.sbc(z[f]);
            z[g] = this.a;
          }
          this.a = this.y;
        }
        this.asl(0xa9);
        this.rol(0xa8);
        this.rol(0xa7);
        this.rol(0xa6);
        if (this.c) state = "ea96";
        else if (z[0xa6] & 0x80) state = "ea80";
        else state = "ea96";
      }
    }
  }

  // ------------------------------------------------ ROUND.FAC ($EB72)
  roundEb72(): void {
    const z = this.z;
    if (z[0x9d] === 0) return;
    this.asl(0xac);
    if (!this.c) return;
    if (!this.incrementE8c6()) return;
    if (this.inc(0x9d) === 0) this.error(OVERFLOW);
    this.c = 1;
    this.ror(0x9e); this.ror(0x9f); this.ror(0xa0); this.ror(0xa1); this.ror(0xac);
  }

  private facToArgEb63(): void {
    const z = this.z;
    this.roundEb72();
    for (let k = 6; k >= 1; k--) z[0xa4 + k] = z[0x9c + k];
    z[0xac] = 0;
    this.x = 0;
    this.a = z[0x9d];
  }
  private copyArgToFac(): void {
    const z = this.z;
    z[0xa2] = z[0xaa];
    for (let k = 5; k >= 1; k--) z[0x9c + k] = z[0xa4 + k];
    z[0xac] = 0;
  }

  // ------------------------------------------------ FCOMP ($EBB2)
  fcomp(five: ArrayLike<number>): number {
    const z = this.z;
    if (five[0] === 0) return this.signEb82();
    if ((five[1] ^ z[0xa2]) & 0x80) return this.signEb86();
    if (five[0] !== z[0x9d]) { this.c = five[0] >= z[0x9d] ? 1 : 0; return this.fcompEbe9(); }
    if ((five[1] | 0x80) !== z[0x9e]) { this.c = (five[1] | 0x80) >= z[0x9e] ? 1 : 0; return this.fcompEbe9(); }
    if (five[2] !== z[0x9f]) { this.c = five[2] >= z[0x9f] ? 1 : 0; return this.fcompEbe9(); }
    if (five[3] !== z[0xa0]) { this.c = five[3] >= z[0xa0] ? 1 : 0; return this.fcompEbe9(); }
    this.c = 0x7f >= z[0xac] ? 1 : 0;
    this.a = five[4];
    this.sbc(z[0xa1]);
    if (this.a === 0) return 0;
    return this.fcompEbe9();
  }
  private fcompEbe9(): number {
    let a = this.z[0xa2];
    if (this.c) a ^= 0xff;
    return a & 0x80 ? -1 : 1;
  }
  private signEb82(): number {
    return this.z[0x9d] === 0 ? 0 : this.signEb86();
  }
  private signEb86(): number {
    return this.z[0xa2] & 0x80 ? -1 : 1;
  }

  // ------------------------------------------------ INT ($EC23) and QINT ($EBF2)
  intEc23(): void {
    const z = this.z;
    if (z[0x9d] >= 0xa0) return;
    this.qintEbf2();
    z[0xac] = this.y;
    this.a = z[0xa2];
    z[0xa2] = this.y;
    this.a ^= 0x80;
    const v = this.a;
    this.a = ((v << 1) & 0xff) | this.c;
    this.c = v >> 7;
    z[0x9d] = 0xa0;
    z[0x0d] = z[0xa1];
    if (this.c === 0) this.complementE89e();
    this.normalizeE82e();
  }
  qintEbf2(): void {
    const z = this.z;
    this.a = z[0x9d];
    if (this.a === 0) {
      z[0x9e] = z[0x9f] = z[0xa0] = z[0xa1] = 0;
      this.y = 0;
      return;
    }
    this.c = 1;
    this.sbc(0xa0);
    if (z[0xa2] & 0x80) {
      this.x = this.a;
      z[0xa4] = 0xff;
      this.complementE8a4();
      this.a = this.x;
    }
    this.x = 0x9d;
    if ((this.a - 0xf9) & 0x80) {
      this.c = this.a >= 0xf9 ? 1 : 0;
      this.shiftE8f0();
      z[0xa4] = this.y;
      return;
    }
    this.y = this.a;
    this.a = z[0xa2] & 0x80;
    this.lsr(0x9e);
    this.a |= z[0x9e];
    z[0x9e] = this.a;
    this.shiftE907(true);
    z[0xa4] = this.y;
  }

  // ------------------------------------------------ FIN ($EC4A) arithmetic
  private mul10Ea39(): void {
    const z = this.z;
    this.facToArgEb63();
    this.x = this.a;
    if (this.a === 0) return;
    this.c = 0;
    this.adc(2);
    if (this.c) this.error(OVERFLOW);
    this.x = 0;
    z[0xab] = 0;
    this.faddE7ce();
    if (this.inc(0x9d) === 0) this.error(OVERFLOW);
  }
  private div10Ea55(): void {
    const z = this.z;
    this.facToArgEb63();
    z[0xab] = 0;
    this.loadFac([0x84, 0x20, 0, 0, 0]);
    this.fdivt();
  }
  private addDigitEcd5(digit: number): void {
    const z = this.z;
    this.facToArgEb63();
    this.a = digit;
    this.floatEb93();
    z[0xab] = z[0xaa] ^ z[0xa2];
    this.x = z[0x9d];
    this.a = z[0x9d];
    this.faddt();
  }
  private floatEb93(): void {
    const z = this.z;
    z[0x9e] = this.a;
    z[0x9f] = 0;
    this.x = 0x88;
    this.c = (z[0x9e] & 0x80) ? 0 : 1;
    z[0xa1] = z[0xa0] = 0;
    z[0x9d] = this.x;
    z[0xac] = 0;
    z[0xa2] = 0;
    if (this.c === 0) this.complementE89e();
    this.normalizeE82e();
  }

  /** Convert a decimal literal as $EC4A does; FAC holds the result. */
  fin(text: string): void {
    const z = this.z;
    for (let k = 0xa3; k > 0x98; k--) z[k] = 0;
    z[0xac] = 0;
    const s = text.trim().toUpperCase();
    let i = 0;
    const isDigit = (ch: string | undefined) => ch !== undefined && ch >= "0" && ch <= "9";
    if (i < s.length && (s[i] === "+" || s[i] === "-")) {
      if (s[i] === "-") z[0xa3] = 0xff;
      i += 1;
    }
    while (i < s.length && isDigit(s[i])) {
      if (z[0x9b] & 0x80) z[0x99] = (z[0x99] + 1) & 0xff;
      this.mul10Ea39();
      this.addDigitEcd5(s.charCodeAt(i) - 0x30);
      i += 1;
      if (i < s.length && s[i] === "." && !(z[0x9b] & 0x80)) {
        z[0x9b] = 0x80;
        i += 1;
      }
    }
    if (i < s.length && s[i] === "." && !(z[0x9b] & 0x80)) {
      z[0x9b] = 0x80;
      i += 1;
      while (i < s.length && isDigit(s[i])) {
        z[0x99] = (z[0x99] + 1) & 0xff;
        this.mul10Ea39();
        this.addDigitEcd5(s.charCodeAt(i) - 0x30);
        i += 1;
      }
    }
    if (i < s.length && s[i] === "E") {
      i += 1;
      let neg = false;
      if (i < s.length && (s[i] === "+" || s[i] === "-")) { neg = s[i] === "-"; i += 1; }
      let e = 0;
      while (i < s.length && isDigit(s[i])) {
        e = e * 10 + (s.charCodeAt(i) - 0x30);
        if (e >= 100) throw new ApplesoftError(OVERFLOW);
        i += 1;
      }
      z[0x9a] = neg ? (-e) & 0xff : e;
    }
    if (i !== s.length) throw new Error(`not a numeric literal: ${text}`);
    this.a = z[0x9a];
    this.c = 1;
    this.sbc(z[0x99]);
    z[0x9a] = this.a;
    if (this.a !== 0) {
      if (this.a & 0x80) {
        for (;;) {
          this.div10Ea55();
          if (this.inc(0x9a) === 0) break;
        }
      } else {
        for (;;) {
          this.mul10Ea39();
          z[0x9a] = (z[0x9a] - 1) & 0xff;
          if (z[0x9a] === 0) break;
        }
      }
    }
    if (z[0xa3] & 0x80) {
      if (z[0x9d]) z[0xa2] ^= 0xff;
    }
  }

  // ------------------------------------------------ FOUT ($ED34)
  fout(): string {
    const z = this.z;
    const buf = new Uint8Array(64);
    let y = 0;
    if (z[0xa2] & 0x80) { y = 1; buf[y] = 0x2d; }
    z[0xa2] = 0x2d;
    z[0xad] = y;
    y += 1;
    if (z[0x9d] === 0) {
      buf[y] = 0x30;
      buf[y + 1] = 0;
      return foutText(buf);
    }
    let a = 0;
    if (z[0x9d] <= 0x80) {
      this.loadArg(K_1E9);
      this.fmultt();
      a = 0xf7;
    }
    z[0x99] = a;
    let state = "ed62";
    for (;;) {
      if (state === "ed62") {
        const r = this.fcomp(K_HIGH);
        if (r === 0) { state = "ed89"; continue; }
        if (r > 0) { state = "ed7f"; continue; }
        state = "ed6d";
      }
      if (state === "ed6d") {
        const r = this.fcomp(K_LOW);
        if (r !== 0 && r > 0) { state = "ed86"; continue; }
        this.mul10Ea39();
        z[0x99] = (z[0x99] - 1) & 0xff;
        if (z[0x99] !== 0) { state = "ed6d"; continue; }
        state = "ed7f";
      }
      if (state === "ed7f") {
        this.div10Ea55();
        z[0x99] = (z[0x99] + 1) & 0xff;
        if (z[0x99] !== 0) { state = "ed62"; continue; }
        state = "ed86";
      }
      if (state === "ed86") {
        this.loadArg(K_HALF);
        this.faddt();
        state = "ed89";
      }
      if (state === "ed89") {
        this.qintEbf2();
        break;
      }
    }
    let x = 1;
    this.c = 0;
    this.a = z[0x99];
    this.adc(0x0a);
    if (this.a & 0x80) {
      this.c = 1;
    } else if (this.a >= 0x0b) {
      this.c = 1;
    } else {
      this.c = 0;
      this.adc(0xff);
      x = this.a;
      this.a = 0x02;
      this.c = 1;
    }
    this.sbc(0x02);
    z[0x9a] = this.a;
    z[0x99] = x;
    if (x === 0 || (x & 0x80)) {
      y = z[0xad];
      y += 1;
      buf[y] = 0x2e;
      if (x !== 0) { y += 1; buf[y] = 0x30; }
      z[0xad] = y;
    }
    y = 0;
    x = 0x80;
    for (;;) {
      for (;;) {
        this.c = 0;
        const cells: [number, number][] = [[3, 0xa1], [2, 0xa0], [1, 0x9f], [0, 0x9e]];
        for (const [k, addr] of cells) {
          this.a = z[addr];
          this.adc(DECADES[y + k]);
          z[addr] = this.a;
        }
        x = (x + 1) & 0xff;
        const n = x & 0x80;
        if (this.c) {
          if (n) continue;
          break;
        }
        if (!n) continue;
        break;
      }
      this.a = x;
      if (this.c) {
        this.a ^= 0xff;
        this.adc(0x0a);
      }
      this.adc(0x2f);
      y += 4;
      z[0x83] = y;
      let yy = z[0xad] + 1;
      x = this.a;
      buf[yy] = this.a & 0x7f;
      z[0x99] = (z[0x99] - 1) & 0xff;
      if (z[0x99] === 0) { yy += 1; buf[yy] = 0x2e; }
      z[0xad] = yy;
      y = z[0x83];
      x = (x ^ 0xff) & 0x80;
      if (y === 0x24) break;
    }
    y = z[0xad];
    let ch: number;
    for (;;) {
      ch = buf[y];
      y -= 1;
      if (ch !== 0x30) break;
    }
    if (ch !== 0x2e) y += 1;
    if (z[0x9a] === 0) {
      buf[y + 1] = 0;
      return foutText(buf);
    }
    let e = z[0x9a];
    let sign = 0x2b;
    if (e & 0x80) { e = (-e) & 0xff; sign = 0x2d; }
    buf[y + 2] = sign;
    buf[y + 1] = 0x45;
    const tens = Math.floor(e / 10);
    buf[y + 4] = 0x30 + (e % 10);
    buf[y + 3] = 0x30 + tens;
    buf[y + 5] = 0;
    return foutText(buf);
  }
}

function foutText(buf: Uint8Array): string {
  let out = "";
  for (let i = 1; i < buf.length; i++) {
    if (buf[i] === 0) break;
    out += String.fromCharCode(buf[i]);
  }
  return out;
}
