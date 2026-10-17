import * as N from "./num.js";
import { Rnd } from "./rnd.js";
import type { UI } from "./ui.js";
import { Files } from "./files.js";

/** A BASIC array of numbers: assigning to an element stores the value (ROUND.FAC). */
function facArray(items: N.Fac[]): N.Fac[] {
  return new Proxy(items, {
    set(t, p, v) {
      (t as any)[p] = v instanceof N.Fac && v.ext ? N.store(v) : v;
      return true;
    },
  });
}

/**
 * The state, named as the BASIC names its variables (paper Appendix A).
 *
 * Assigning a number to any field is a BASIC assignment, and Applesoft rounds a value
 * (ROUND.FAC) as it stores it in a variable: an operator's result still carries its extension
 * byte, and `newState()` wraps the object so that a field never holds one.
 */
export class State {
  C0 = N.ZERO; C1 = N.ONE; C2 = N.TWO; C3 = N.THREE; C4 = N.FOUR; P5 = N.HALF;
  S = 0;                       // disk side
  AD = N.ONE; AM = N.ONE; AY = N.ONE;      // the date
  AR = N.parse("3"); AS = N.ZERO; W = N.ZERO; TM = N.ZERO; QT = N.ZERO; QP = N.ZERO;
  TR = N.ZERO; TS = N.ZERO; PP = N.ZERO; ZO = 0;
  H = N.ZERO; H0 = 0; HR = N.ZERO; FS = N.ZERO; ZT = N.ZERO; ZC = N.ZERO; ZF = N.ZERO; ZP = N.ZERO;
  NP = 5;
  H1: N.Fac[] = [N.ZERO, N.ZERO, N.ZERO, N.ZERO, N.ZERO];
  H2: N.Fac[] = [N.ZERO, N.ZERO, N.ZERO, N.ZERO, N.ZERO];
  N: string[] = ["", "", "", "", ""];
  LM = 0; NM = 0; MD = N.ONE; D = N.ZERO; DD = N.ZERO; M = N.ZERO; BS = N.ZERO; V = N.ZERO;
  SD = 0; P = N.ONE; R = N.ONE;
  FC = N.ZERO; F0 = N.ZERO; OP = N.ZERO; W1 = 0; LL = 0; IX = N.ONE;
  I: N.Fac[] = new Array(9).fill(N.ZERO);
  MY = N.ZERO; PF = N.ZERO;
  RE: N.Fac[] = new Array(15).fill(N.ZERO);
  A = 0; F9 = 0; B = 0; SR: N.Fac = N.ONE;
  SN: number[] = [0, 0]; ML: N.Fac[] | number[] = [0, 0]; DL: N.Fac = N.neg(N.ONE); LN = 0;
  RC = 0; RD = N.ZERO; RW = N.ZERO; RS = N.ZERO; RB = 0;
  T: string[] = new Array(11).fill("");
  Q: N.Fac = N.ZERO; Q_arr: number[] = new Array(17).fill(0); Q1 = 1;
  Z: N.Fac = N.ZERO;
  /** INT(H / 35): 0 good, 1 fair, 2 poor, 3 very poor */
  healthBand(): number { return N.trunc(N.div(this.H, N.parse("35"))); }
}

export function newState(): State {
  const st = new State();
  st.I = facArray(st.I); st.H1 = facArray(st.H1); st.H2 = facArray(st.H2); st.RE = facArray(st.RE);
  return new Proxy(st, {
    set(t, p, v) {
      if (v instanceof N.Fac) { if (v.ext) v = N.store(v); }
      else if (Array.isArray(v) && v.length && v[0] instanceof N.Fac) v = facArray(v);
      (t as any)[p] = v;
      return true;
    },
  });
}

/** PEEK and POKE: the hand-over between the programs, locations 900 to 917 and the names at 1920 */
export class Memory {
  b = new Uint8Array(0x10000);
  program = "OREGON TRAIL";
  /** the 16-bit counter the keyboard routine keeps at 78 and 79 while it waits for a key */
  keyboardCounter = 0;
  peek(a: number): number { return this.b[a & 0xffff]; }
  peekWord(a: number): number { return this.peek(a) + this.peek(a + 1) * 256; }
  poke(a: number, v: number, line = 0): void {
    const n = Math.trunc(v);
    if (n < 0 || n > 255) throw new N.ApplesoftError(N.ILLEGAL_QUANTITY, line, `POKE ${a},${n}`);
    this.b[a & 0xffff] = n;
  }
  pokeWord(a: number, v: number, line = 0): void {
    const n = Math.trunc(v);
    if (n < 0 || n > 65535) throw new N.ApplesoftError(N.ILLEGAL_QUANTITY, line, `16-bit store of ${n} at ${a}`);
    this.poke(a, n % 256, line); this.poke(a + 1, Math.floor(n / 256), line);
  }
  putNames(names: string[], line = 6045): void {
    let at = 1920;
    for (const name of names) {
      for (const ch of name) { this.poke(at, ch.charCodeAt(0), line); at += 1; }
      this.poke(at, 0, line); at += 1;
    }
  }
  getNames(count = 5): string[] {
    let at = 1920; const names: string[] = [];
    for (let i = 0; i < count; i++) {
      let s = "";
      for (;;) {
        if (at > 4000) break;
        const b = this.peek(at);
        if (b) { s += String.fromCharCode(b); } else { at += 1; break; }
        at += 1;
      }
      names.push(s);
    }
    return names;
  }
}

/** One line per game day, in the form the paper's Appendix H gives for a reference trace. */
export class Tracer {
  days = 0;
  lines: string[] = [];
  constructor(private rng: Rnd) {}
  day(st: State, stopped = false): void {
    this.days += 1;
    this.lines.push(this.line(st, "", stopped));
  }
  line(st: State, event = "", stopped = false): string {
    const f = (v: N.Fac, p: number) => N.fmtG(N.asFloat(v), p), i = (v: N.Fac | number) => String(N.asInt(v));
    const h1 = st.H1.slice(0, 5).map(i).join(",");
    const h2 = st.H2.slice(0, 5).map(i).join(",");
    const cells = [
      String(N.asInt(st.AD)).padStart(2, "0"), String(N.asInt(st.AM)).padStart(2, "0"), i(st.AY),
      f(st.D, 4), f(st.M, 5), f(st.H, 6), f(st.FS, 6), i(st.H0), i(st.HR), i(st.W), i(st.TM), i(st.PP),
      f(st.AR, 6), f(st.AS, 6), f(st.PF, 7),
      f(st.I[2], 6), f(st.I[3], 6), f(st.I[4], 8), i(st.I[5]), i(st.I[6]), i(st.I[7]), f(st.I[8], 8),
      f(st.MY, 7), `[${h1}]`, `[${h2}]`, (event || "-") + (stopped ? "+" : ""), this.rng.seedHex(),
    ];
    return cells.join(" ");
  }
}

export class Context {
  st = newState();
  mem = new Memory();
  rng = new Rnd();
  trace: Tracer;
  program = "OREGON TRAIL";
  outcome: string | null = null;
  // what the river routines leave for one another
  riverLosses = 0;
  riverMessage: [string, string[]] | null = null;
  riverMethod = 2;
  files: Files;
  /** the top ten as read, kept for the session */
  hiscore: [string, number, string][] | null = null;
  /** pictures the next message box shows over the travel scene (graphical mode) */
  eventPic: [string, number, number][] | null = null;
  keepScreen = false;
  uiHeader: [string, string, string[]] | null = null;
  scene: { fx: number; ix: number; wg: number; moved: boolean } | null = null;
  storeVerb = "buy";
  constructor(public ui: UI, files?: Files) {
    this.trace = new Tracer(this.rng);
    this.files = files ?? new Files();
    // A person at a keyboard takes time that means something: it advances the counter that MENU 1015
    // seeds the generator from. A script answers at once, so it is left alone and stays deterministic.
    if (ui.countsKeyboardTime) {
      for (const name of ["key", "waitKey", "yesNo"] as const) {
        const inner = (ui[name] as (...a: any[]) => any).bind(ui);
        (ui as any)[name] = async (...a: any[]) => {
          const t0 = performance.now();
          try { return await inner(...a); }
          finally {
            const ms = Math.floor(performance.now() - t0);
            if (ms) this.mem.keyboardCounter = (this.mem.keyboardCounter + ms) & 0xffff;
          }
        };
      }
    }
  }
  setProgram(name: string): void { this.mem.program = name; this.program = name; }
}
