/**
 * The game's arithmetic: Applesoft's five-byte numbers behind a choice of backends.
 *
 *   exact    the ROM's routines transcribed (fp.ts): the default, bit-equal to the Apple IIe ROM
 *   rounded  host doubles, every result and literal rounded to Applesoft's precision
 *   float    plain host doubles
 *
 * Mirrors `game/python/oregon/num.py`, `applesoft/fac.py`, `applesoft/exact.py` and `applesoft/hostfloat.py`.
 * Every number is a `Fac`. In `exact` it is the five bytes plus the extension byte ($AC) that an
 * operator's result carries until it is stored; in `float` it also holds the double.
 */
import { Fp, ApplesoftError, OVERFLOW, DIVISION_BY_ZERO, ILLEGAL_QUANTITY } from "./fp.js";
export { ApplesoftError, OVERFLOW, DIVISION_BY_ZERO, ILLEGAL_QUANTITY };

export class Fac {
  readonly b: number[];
  readonly ext: number;
  constructor(b: number[], ext = 0) { this.b = b; this.ext = ext; }
  isZero(): boolean { return this.b[0] === 0; }
  isNegative(): boolean { return (this.b[1] & 0x80) !== 0; }
  /** the five bytes a variable would hold: after ROUND.FAC */
  raw(): number[] { return this.ext & 0x80 ? xRoundFac(this).b : this.b; }
}

/** a value that carries a host double; `b` is it rounded to five bytes, for the few places that read bytes */
export class FloatFac extends Fac {
  readonly f: number;
  constructor(f: number) {
    let b: number[];
    try { b = toBytes(f); } catch { b = [255, f < 0 ? 0x80 : 0, 255, 255, 255]; }
    super(b);
    this.f = f;
  }
  isZero(): boolean { return this.f === 0; }
  isNegative(): boolean { return this.f < 0; }
  raw(): number[] { return this.b; }
}

const ZB = (): number[] => [0, 0, 0, 0, 0];
export const ZERO = new Fac(ZB());
export const ONE = new Fac([0x81, 0, 0, 0, 0]);
export const HALF = new Fac([0x80, 0, 0, 0, 0]);
export const TWO = new Fac([0x82, 0, 0, 0, 0]);
export const THREE = new Fac([0x82, 0x40, 0, 0, 0]);
export const FOUR = new Fac([0x83, 0, 0, 0, 0]);

// ======================================================================= backends
export interface Backend {
  name: string;
  add(a: Fac, b: Fac): Fac; sub(a: Fac, b: Fac): Fac; mul(a: Fac, b: Fac): Fac; div(a: Fac, b: Fac): Fac;
  neg(a: Fac): Fac; int_(a: Fac): Fac; roundFac(a: Fac): Fac; cmp(a: Fac, b: Fac): number;
  mulc(a: Fac, b: Fac): Fac; divc(a: Fac, b: Fac): Fac;
  fromInt(n: number): Fac; fromStr(s: string): Fac;
  asInt(v: Fac): number; asFloat(v: Fac): number; str_(v: Fac): string;
  /** the RND argument as five bytes, and the value RND returns from its new seed */
  rndArg(a: Fac): number[]; rndValue(seed: number[]): Fac;
}

// ---------------------------------------------------------------------- exact
const fp = new Fp();

function result(): Fac {
  const [b, ext] = fp.fac();
  return b[0] === 0 ? ZERO : new Fac(b, ext);
}

function xRoundFac(a: Fac): Fac {
  if (a.isZero()) return ZERO;
  if (!(a.ext & 0x80)) return a.ext === 0 ? a : new Fac(a.b);
  fp.loadFac(a.b, a.ext);
  fp.roundEb72();
  return new Fac(fp.fac()[0]);
}

function xOp(left: Fac, right: Fac, which: "faddt" | "fsubt" | "fmultt" | "fdivt"): Fac {
  left = xRoundFac(left);
  fp.loadFac(right.b, right.ext);
  fp.loadArg(left.raw());
  fp[which]();
  return result();
}
function xNeg(a: Fac): Fac {
  if (a.isZero()) return a;
  const b = a.b.slice();
  b[1] ^= 0x80;
  return new Fac(b, a.ext);
}
const xAbs = (a: Fac) => (a.isNegative() ? xNeg(a) : a);
function xInt(a: Fac): Fac {
  if (a.isZero()) return a;
  fp.loadFac(a.b, a.ext);
  fp.intEc23();
  return result();
}
function settle(): Fac {
  const z = fp.z;
  if (z[0xac] & 0x80) {
    let carried = true;
    for (const addr of [0xa1, 0xa0, 0x9f, 0x9e]) {
      z[addr] = (z[addr] + 1) & 0xff;
      if (z[addr]) { carried = false; break; }
    }
    if (carried) {
      z[0x9d] = (z[0x9d] + 1) & 0xff;
      if (z[0x9d] === 0) throw new ApplesoftError(OVERFLOW, 0, "rounding carried out of the range");
    }
  }
  return new Fac(fp.fac()[0]);
}
function xConstant(facValue: Fac, memValue: Fac, which: "fmultt" | "fdivt"): Fac {
  fp.loadFac(facValue.b, facValue.ext);
  fp.loadArg(memValue.raw());
  fp[which]();
  return settle();
}
function xMulc(a: Fac, b: Fac): Fac {
  if (a.isZero() || b.isZero()) return ZERO;
  const mag = xConstant(xAbs(a), xAbs(b), "fmultt");
  return a.isNegative() !== b.isNegative() ? xNeg(mag) : mag;
}
function xDivc(a: Fac, b: Fac): Fac {
  if (b.isZero()) throw new ApplesoftError(DIVISION_BY_ZERO, 0, "DIVISION BY ZERO");
  const mag = xConstant(xAbs(b), xAbs(a), "fdivt");
  return a.isNegative() !== b.isNegative() ? xNeg(mag) : mag;
}
function xCmp(a: Fac, b: Fac): number {
  a = xRoundFac(a);
  if ((b.ext & 0x80) && !b.isZero()) {
    fp.loadFac(b.b, b.ext);
    return -fp.fcomp(a.raw());
  }
  const x = a.raw(), y = b.raw();
  if (x.every((v, i) => v === y[i])) return 0;
  if (x[0] === 0) return y[1] & 0x80 ? 1 : -1;
  if (y[0] === 0) return x[1] & 0x80 ? -1 : 1;
  const sx = x[1] & 0x80, sy = y[1] & 0x80;
  if (sx !== sy) return sx ? -1 : 1;
  const mag = (v: number[]) => (BigInt(v[0]) << 31n) | (BigInt(((v[1] << 24) | (v[2] << 16) | (v[3] << 8) | v[4]) >>> 0) & 0x7fffffffn);
  const mx = mag(x), my = mag(y);
  if (mx === my) return 0;
  const less = mx < my;
  return sx ? (less ? 1 : -1) : less ? -1 : 1;
}
function xFromInt(n: number): Fac {
  if (n === 0) return ZERO;
  const sign = n < 0 ? 0x80 : 0;
  const a = BigInt(Math.abs(n));
  let s = a << 1n;
  let e = 0;
  const bits = s.toString(2).length;
  if (bits > 33) {
    const k = bits - 33;
    s = ((s >> BigInt(k - 1)) & 1n) ? (s >> BigInt(k)) + 1n : s >> BigInt(k);
    e = k;
    if (s.toString(2).length > 33) { s >>= 1n; e += 1; }
  } else if (bits < 33) {
    const sh = 33 - bits;
    s <<= BigInt(sh);
    e = -sh;
  }
  let word = s >> 1n;
  if (s & 1n) {
    word += 1n;
    if (word > 0xffffffffn) { word >>= 1n; e += 1; }
  }
  const exp = e + 160;
  if (exp <= 0) return ZERO;
  if (exp > 255) throw new Error(`${n} is outside the 5-byte format`);
  const w = Number(word & 0xffffffffn);
  return new Fac([exp, sign | ((w >>> 24) & 0x7f), (w >>> 16) & 0xff, (w >>> 8) & 0xff, w & 0xff]);
}
const xLiterals = new Map<string, Fac>();
function xFromStr(s: string): Fac {
  const cached = xLiterals.get(s);
  if (cached) return cached;
  let t = s.trim();
  let negative = false;
  if (t[0] === "+" || t[0] === "-") { negative = t[0] === "-"; t = t.slice(1); }
  if (!t) return ZERO;
  fp.fin(t);
  let v = result();
  if (negative) v = xNeg(v);
  xLiterals.set(s, v);
  return v;
}
function wordOf(v: Fac): number {
  return (((v.b[1] << 24) | (v.b[2] << 16) | (v.b[3] << 8) | v.b[4]) >>> 0 | 0x80000000) >>> 0;
}
function xAsInt(v: Fac): number {
  if (v.ext & 0x80) return xAsInt(xRoundFac(v));
  if (v.b[0] === 0) return 0;
  const word = wordOf(v);
  const shift = 160 - v.b[0];
  let n: number;
  if (shift <= 0) n = word * Math.pow(2, -shift);
  else if (shift >= 96) n = 0;
  else n = Math.floor(word / Math.pow(2, shift));
  return v.isNegative() ? -n : n;
}
function xAsFloat(v: Fac): number {
  if (v.ext & 0x80) return xAsFloat(xRoundFac(v));
  if (v.b[0] === 0) return 0;
  const x = wordOf(v) * Math.pow(2, v.b[0] - 160);
  return v.isNegative() ? -x : x;
}
function xStr(v: Fac): string {
  if (v.isZero()) return "0";
  fp.loadFac(v.b, v.ext);
  return fp.fout();
}

const exactBackend: Backend = {
  name: "exact",
  add: (a, b) => xOp(a, b, "faddt"), sub: (a, b) => xOp(a, b, "fsubt"), mul: (a, b) => xOp(a, b, "fmultt"),
  div(a, b) {
    if (b.isZero()) throw new ApplesoftError(DIVISION_BY_ZERO, 0, "DIVISION BY ZERO");
    return xOp(a, b, "fdivt");
  },
  neg: xNeg, int_: xInt, roundFac: xRoundFac, cmp: xCmp, mulc: xMulc, divc: xDivc,
  fromInt: xFromInt, fromStr: xFromStr, asInt: xAsInt, asFloat: xAsFloat, str_: xStr,
  rndArg: (a) => a.raw(), rndValue: (seed) => new Fac(seed.slice()),
};

// ------------------------------------------------------------- float and rounded
/** x rounded to the five-byte format as (exponent byte, 32-bit significand word, sign) or null for zero */
function toFac(x: number): { e: number; word: number; neg: boolean } | null {
  if (x === 0) return null;
  const a = Math.abs(x);
  let e = Math.floor(Math.log2(a)) + 1;
  let m = a / Math.pow(2, e);
  while (m >= 1) { m /= 2; e += 1; }
  while (m < 0.5) { m *= 2; e -= 1; }
  let word = Math.floor(m * 4294967296 + 0.5);
  if (word >= 4294967296) { word = Math.floor(word / 2); e += 1; }
  const exp = e + 128;
  if (exp <= 0) return null;
  if (exp > 255) throw new ApplesoftError(OVERFLOW, 0, "OVERFLOW");
  return { e: exp, word, neg: x < 0 };
}

function tenCmp(m: bigint, e: number, dexp: number): number {
  const [lnum, lden] = e >= 0 ? [m << BigInt(e), 1n] : [m, 1n << BigInt(-e)];
  const [rnum, rden] = dexp >= 0 ? [10n ** BigInt(dexp), 1n] : [1n, 10n ** BigInt(-dexp)];
  const a = lnum * rden, b = rnum * lden;
  return a > b ? 1 : a < b ? -1 : 0;
}

/** Applesoft's number to text (STR$/PRINT): nine significant digits, no leading space. */
export function fmtApplesoft(v: number): string {
  const f = toFac(v);
  if (f === null) return "0";
  const m = BigInt(f.word) | 0x80000000n;
  const e = f.e - 160;
  const [num_, den] = e >= 0 ? [m << BigInt(e), 1n] : [m, 1n << BigInt(-e)];
  let d10: number;
  if (num_ >= den) d10 = (num_ / den).toString().length - 1;
  else d10 = -(((den + num_ - 1n) / num_).toString().length);
  while (tenCmp(m, e, d10) < 0) d10 -= 1;
  while (tenCmp(m, e, d10 + 1) >= 0) d10 += 1;
  const k = 8 - d10;
  let n2: bigint, d2: bigint;
  if (k >= 0) { n2 = num_ * 10n ** BigInt(k); d2 = den; } else { n2 = num_; d2 = den * 10n ** BigInt(-k); }
  let scaled = (2n * n2 + d2) / (2n * d2);
  if (scaled >= 1000000000n) { scaled /= 10n; d10 += 1; }
  const digits = scaled.toString().replace(/0+$/, "") || "0";
  const sign = f.neg ? "-" : "";
  if (d10 >= -2 && d10 <= 8) {
    if (d10 < 0) return sign + "." + "0".repeat(-d10 - 1) + digits;
    if (digits.length <= d10 + 1) return sign + digits + "0".repeat(d10 + 1 - digits.length);
    return sign + digits.slice(0, d10 + 1) + "." + digits.slice(d10 + 1);
  }
  const mant = digits[0] + (digits.length > 1 ? "." + digits.slice(1) : "");
  return `${sign}${mant}E${d10 >= 0 ? "+" : "-"}${String(Math.abs(d10)).padStart(2, "0")}`;
}


/** x rounded to the 5-byte format: a 32-bit significand, half up */
function toBytes(x: number): number[] {
  const f = toFac(x);
  if (f === null) return ZB();
  return [f.e, ((f.word >>> 24) & 0x7f) | (f.neg ? 0x80 : 0), (f.word >>> 16) & 0xff, (f.word >>> 8) & 0xff, f.word & 0xff];
}
function bytesToDouble(b: number[]): number {
  if (b[0] === 0) return 0;
  const word = (((b[1] << 24) | (b[2] << 16) | (b[3] << 8) | b[4]) >>> 0 | 0x80000000) >>> 0;
  const v = word * Math.pow(2, b[0] - 160);
  return b[1] & 0x80 ? -v : v;
}
const fval = (v: Fac): number => (v instanceof FloatFac ? v.f : xAsFloat(v));

function hostBackend(name: string, make: (x: number) => Fac): Backend {
  const checked = (x: number): Fac => {
    if (!Number.isFinite(x)) throw new ApplesoftError(OVERFLOW, 0, "OVERFLOW");
    return make(x);
  };
  const neg = (a: Fac): Fac => (a.isZero() ? a : checked(-fval(a)));
  return {
    name,
    add: (a, b) => checked(fval(a) + fval(b)),
    sub: (a, b) => checked(fval(a) - fval(b)),
    mul: (a, b) => checked(fval(a) * fval(b)),
    div(a, b) {
      if (fval(b) === 0) throw new ApplesoftError(DIVISION_BY_ZERO, 0, "DIVISION BY ZERO");
      return checked(fval(a) / fval(b));
    },
    neg,
    int_: (a) => checked(Math.floor(fval(a))),
    roundFac: (a) => a,
    cmp: (a, b) => { const x = fval(a), y = fval(b); return (x > y ? 1 : 0) - (x < y ? 1 : 0); },
    mulc(a, b) { return checked(fval(a) * fval(b)); },
    divc(a, b) {
      if (fval(b) === 0) throw new ApplesoftError(DIVISION_BY_ZERO, 0, "DIVISION BY ZERO");
      return checked(fval(a) / fval(b));
    },
    fromInt: (n) => make(n),
    fromStr(s) { const t = s.trim(); return checked(t ? Number(t) : 0); },
    asInt: (v) => Math.trunc(fval(v)),
    asFloat: fval,
    str_: (v) => fmtApplesoft(bytesToDouble(toBytes(fval(v)))),
    rndArg: (a) => toBytes(fval(a)),
    rndValue: (seed) => checked(bytesToDouble(seed)),
  };
}
const floatBackend = hostBackend("float", (x) => new FloatFac(x));
const roundedBackend = hostBackend("rounded", (x) => new Fac(toBytes(x)));

let backend: Backend = exactBackend;
export function use(which: "exact" | "rounded" | "float" | string): Backend {
  if (which === "exact") backend = exactBackend;
  else if (which === "rounded") backend = roundedBackend;
  else if (which === "float") backend = floatBackend;
  else throw new Error(`unknown arithmetic ${which}; choose exact, rounded or float`);
  literals.clear();
  return backend;
}
export const backendName = (): string => backend.name;

// ================================================================== the interface
export const roundFac = (a: Fac): Fac => backend.roundFac(a);
export const store = roundFac;
export const add = (a: Fac, b: Fac): Fac => backend.add(a, b);
export const sub = (a: Fac, b: Fac): Fac => backend.sub(a, b);
export const mul = (a: Fac, b: Fac): Fac => backend.mul(a, b);
export const div = (a: Fac, b: Fac): Fac => backend.div(a, b);
export const neg = (a: Fac): Fac => backend.neg(a);
export const abs_ = (a: Fac): Fac => (a.isNegative() ? backend.neg(a) : a);
/** INT: floor */
export const int_ = (a: Fac): Fac => backend.int_(a);
export const addc = add;
export const mulc = (a: Fac, b: Fac): Fac => backend.mulc(a, b);
export const divc = (a: Fac, b: Fac): Fac => backend.divc(a, b);
export const cmp = (a: Fac, b: Fac): number => backend.cmp(a, b);
export const eq = (a: Fac, b: Fac) => cmp(a, b) === 0;
export const lt = (a: Fac, b: Fac) => cmp(a, b) < 0;
export const le = (a: Fac, b: Fac) => cmp(a, b) <= 0;
export const gt = (a: Fac, b: Fac) => cmp(a, b) > 0;
export const ge = (a: Fac, b: Fac) => cmp(a, b) >= 0;
export const bool_ = (b: boolean): Fac => (b ? ONE : ZERO);
export const b2i = (b: boolean): number => (b ? 1 : 0);
export const fromInt = (n: number): Fac => backend.fromInt(n);

const literals = new Map<string, Fac>();
export function fromStr(s: string): Fac {
  const cached = literals.get(s);
  if (cached) return cached;
  const v = backend.fromStr(s);
  literals.set(s, v);
  return v;
}
/** a decimal literal (string) or an integer, as the backend converts it */
export function parse(t: string | number | Fac): Fac {
  if (t instanceof Fac) return t;
  if (typeof t === "number") return fromInt(t);
  return fromStr(t);
}

/** the value truncated toward zero, as a loop bound, an index or a POKE takes it */
export function asInt(v: Fac | number): number {
  return typeof v === "number" ? Math.trunc(v) : backend.asInt(v);
}
/** INT as an integer (floor) */
export const trunc = (v: Fac): number => asInt(int_(v));
/** a host float, for the trace only */
export const asFloat = (v: Fac): number => backend.asFloat(v);
/** STR$: the text for the value as it stands */
export function str_(v: Fac): string {
  if (v.isZero()) return "0";
  return backend.str_(v);
}
/** RND: argument bytes, and the value from the new seed */
export const rndArg = (a: Fac): number[] => backend.rndArg(a);
export const rndValue = (seed: number[]): Fac => backend.rndValue(seed);

// ------------------------------------------------------------------ chains
export class Chain {
  constructor(public v: Fac) {}
  add(x: Fac) { this.v = add(this.v, x); return this; }
  sub(x: Fac) { this.v = sub(this.v, x); return this; }
  mul(x: Fac) { this.v = mul(this.v, x); return this; }
  div(x: Fac) { this.v = div(this.v, x); return this; }
  addc(x: Fac) { this.v = addc(this.v, x); return this; }
  mulc(x: Fac) { this.v = mulc(this.v, x); return this; }
  done(): Fac { return store(this.v); }
}
export const chain = (v: Fac) => new Chain(v);

/** How many times a FOR loop runs its body: at least once (paper section 2.5, rule c). */
export function fortCount(start: number, limit: Fac | number): number {
  const lo = Math.trunc(start), hi = asInt(limit);
  return hi >= lo ? hi - lo + 1 : 1;
}

/** `V` already a whole number of cents: lines 200 and 250 */
export function dollar(cents: number): string {
  return String(Math.floor(cents / 100)) + "." + ("0" + String(cents)).slice(-2);
}

/**
 * Python's format(x, ".<p>g"): correctly rounded (ties to even) from the exact binary value.
 * Used for the trace so that it can be compared line by line with the Python rebuild's.
 */
export function fmtG(x: number, p: number): string {
  if (x === 0) return Object.is(x, -0) ? "-0" : "0";
  if (!Number.isFinite(x)) return x > 0 ? "inf" : x < 0 ? "-inf" : "nan";
  if (p === 0) p = 1;
  const neg = x < 0;
  let a = Math.abs(x);
  // exact value as a fraction mant * 2**exp2
  const buf = new DataView(new ArrayBuffer(8));
  buf.setFloat64(0, a);
  const hi = buf.getUint32(0), lo = buf.getUint32(4);
  const expBits = (hi >>> 20) & 0x7ff;
  let mant = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo);
  let exp2: number;
  if (expBits === 0) exp2 = -1074; else { mant |= 1n << 52n; exp2 = expBits - 1075; }
  const [n0, d0] = exp2 >= 0 ? [mant << BigInt(exp2), 1n] : [mant, 1n << BigInt(-exp2)];
  // decimal exponent X with 10**X <= a < 10**(X+1)
  let X = Math.floor(Math.log10(a));
  const ge10 = (k: number) => (k >= 0 ? n0 >= 10n ** BigInt(k) * d0 : n0 * 10n ** BigInt(-k) >= d0);
  while (!ge10(X)) X -= 1;
  while (ge10(X + 1)) X += 1;
  const roundTo = (X2: number): bigint => {
    const k = p - 1 - X2;
    let [n2, d2] = k >= 0 ? [n0 * 10n ** BigInt(k), d0] : [n0, d0 * 10n ** BigInt(-k)];
    let q = n2 / d2; const r2 = (n2 % d2) * 2n;
    if (r2 > d2 || (r2 === d2 && (q & 1n) === 1n)) q += 1n;
    return q;
  };
  let q = roundTo(X);
  if (q >= 10n ** BigInt(p)) { X += 1; q = roundTo(X); }
  let digits = q.toString();
  let out: string;
  if (X < -4 || X >= p) {
    let m2 = digits[0] + (digits.length > 1 ? "." + digits.slice(1) : "");
    if (m2.includes(".")) m2 = m2.replace(/0+$/, "").replace(/\.$/, "");
    out = `${m2}e${X < 0 ? "-" : "+"}${String(Math.abs(X)).padStart(2, "0")}`;
  } else if (X >= 0) {
    const whole = digits.slice(0, X + 1), frac = digits.slice(X + 1).replace(/0+$/, "");
    out = frac ? `${whole}.${frac}` : whole;
  } else {
    const frac = ("0".repeat(-X - 1) + digits).replace(/0+$/, "");
    out = `0.${frac}`;
  }
  return (neg ? "-" : "") + out;
}
