/**
 * Applesoft's RND ($EFAE) as an exact integer model: the multiply-and-add on the five seed bytes,
 * including the shift-and-add multiply's treatment of zero bytes, the alignment shifts of the
 * addition, normalisation and rounding. Ported from the Python rebuild's applesoft/rng.py, which
 * was checked against the emulated ROM for every seed the game can reach.
 */
import * as N from "./num.js";

const MULT = [0x98, 0x35, 0x44, 0x7a, 0x68];
const ADDC = [0x68, 0x28, 0xb1, 0x46, 0x20];

type EMX = [number, number, number]; // exponent, 32-bit significand, extension byte

function unpack(b: ArrayLike<number>): EMX {
  const e = b[0];
  if (e === 0) return [0, 0, 0];
  return [e, (((b[1] | 0x80) << 24) | (b[2] << 16) | (b[3] << 8) | b[4]) >>> 0, b[1] >> 7];
}
function normalise(e: number, m: number, x: number): EMX {
  let s = 0;
  while (m >>> 24 === 0) {
    m = ((m << 8) | x) >>> 0; x = 0; s += 8;
    if (s === 32) return [0, 0, 0];
  }
  while (!(m & 0x80000000)) {
    m = ((m << 1) | (x >> 7)) >>> 0; x = (x << 1) & 0xff; s += 1;
  }
  if (s >= e) return [0, 0, 0];
  return [e - s, m, x];
}
function fmult(e1: number, m1: number, x1: number, e2: number, m2: number): EMX {
  if (e1 === 0 || e2 === 0) return [0, 0, 0];
  const e = e1 + e2 - 128;
  if (e <= 0) return [0, 0, 0];
  if (e > 255) throw new Error("overflow");
  let res = 0, ext = 0, carry = 0;
  for (const byte of [x1, m1 & 0xff, (m1 >>> 8) & 0xff, (m1 >>> 16) & 0xff, (m1 >>> 24) & 0xff]) {
    if (byte === 0) {
      ext = res & 0xff; res = res >>> 8;
      if (!carry) { ext = ((res & 1) << 7) | (ext >> 1); res = res >>> 1; }
      carry = 0;
      continue;
    }
    carry = 1;
    for (let k = 0; k < 8; k++) {
      let c = 0;
      if ((byte >> k) & 1) { res += m2; c = res > 0xffffffff ? 1 : 0; res = res >>> 0; }
      ext = ((res & 1) << 7) | (ext >> 1);
      res = ((c << 31) | (res >>> 1)) >>> 0;
    }
  }
  return normalise(e, res, ext);
}
function shr(m: number, x: number, n: number, keepExt: boolean): [number, number] {
  if (n >= 8) {
    while (n >= 8) { x = m & 0xff; m = m >>> 8; n -= 8; }
  } else if (!keepExt) x = 0;
  for (let i = 0; i < n; i++) { x = ((m & 1) << 7) | (x >> 1); m = m >>> 1; }
  return [m, x];
}
function fadd(e1: number, m1: number, x1: number, e2: number, m2: number): EMX {
  if (e2 === 0) return [e1, m1, x1];
  if (e1 === 0) return [e2, m2, 0];
  let ms: number, xs: number, argx: number, e: number, base: number;
  if (e2 < e1) { [ms, xs] = shr(m2, 0, e1 - e2, false); argx = x1; e = e1; base = m1; }
  else if (e2 > e1) { [ms, xs] = shr(m1, x1, e2 - e1, true); argx = 0; e = e2; base = m2; }
  else { ms = m2; xs = 0; argx = x1; e = e1; base = m1; }
  const t = xs + argx;
  let x = t & 0xff;
  let s = base + ms + (t >> 8);
  if (s > 0xffffffff) {
    x = ((s & 1) << 7) | (x >> 1); s = Math.floor(s / 2); e += 1;
    if (e > 255) throw new Error("overflow");
  }
  return [e, s, x];
}
function roundPack(e: number, m: number, x: number): number[] {
  if (e === 0) return [0, 0, 0, 0, 0];
  if (x & 0x80) {
    m += 1;
    if (m > 0xffffffff) { m = 0x80000000; e += 1; }
  }
  return [e, (m >>> 24) & 0x7f, (m >>> 16) & 0xff, (m >>> 8) & 0xff, m & 0xff];
}

/** One RND call on five seed bytes: returns the new seed (which is also the value). */
export function rndStep(seed: number[], arg: number[]): number[] {
  const [ea, ma, sa] = unpack(arg);
  let e: number, m: number, x: number;
  if (ea && sa) { e = ea; m = ma; x = 0; }
  else {
    [e, m] = unpack(seed);
    if (ea === 0) return seed.slice();
    [e, m, x] = fmult(e, m, 0, ...(unpack(MULT).slice(0, 2) as [number, number]));
    [e, m, x] = fadd(e, m, x, ...(unpack(ADDC).slice(0, 2) as [number, number]));
  }
  const b1 = (m >>> 24) & 0xff, b4 = m & 0xff;
  m = ((b4 << 24) | (m & 0x00ffff00) | b1) >>> 0;
  x = e; e = 0x80;
  [e, m, x] = normalise(e, m, x);
  return roundPack(e, m, x);
}

/** The generator: five seed bytes, and RND(x) for the arguments the game uses. */
export class Rnd {
  seed: number[] = [0, 0, 0, 0, 0];
  rnd(arg: N.Fac): N.Fac {
    this.seed = rndStep(this.seed, N.rndArg(arg));
    return N.rndValue(this.seed);
  }
  rnd1(_tag = ""): N.Fac { return this.rnd(N.ONE); }
  below(tag: string, chance: N.Fac): boolean { return N.lt(this.rnd1(tag), chance); }
  above(tag: string, value: N.Fac): boolean { return N.gt(this.rnd1(tag), value); }
  /** INT(RND(1) * n) */
  intRange(tag: string, n: number): number { return N.trunc(N.mul(this.rnd1(tag), N.parse(String(n)))); }
  /** INT(RND(1) * (hi - lo + 1)) + lo */
  intSpan(tag: string, lo: number, hi: number): number { return lo + N.trunc(N.mul(this.rnd1(tag), N.parse(String(hi - lo + 1)))); }
  /** Z = RND(-(PEEK(78) + PEEK(79) * 256)) */
  seedFromKeyboard(counter: number): N.Fac { return this.rnd(N.neg(N.parse(String(counter)))); }
  seedHex(): string { return this.seed.map((b) => b.toString(16).padStart(2, "0")).join(""); }
}
