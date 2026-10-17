/** OREGON TRAIL: the journey itself -- load, the daily cycle, the event loop, segments and landmarks. */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import { ALLOWED, RETURN_KEYS } from "./ui.js";
import * as events from "./events.js";
import * as illness from "./illness.js";
import * as river from "./river.js";
import * as action from "./action.js";
import * as maplib from "./maplib.js";
import * as endl from "./endl.js";
import * as flip from "./flip.js";

// The calendar, from line 3255. February always has 28 days, even in 1848, which was a leap year.
const MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

const screens = (c: Context): any => c.ui.screens;
const sound = (c: Context): any => (c.ui as any).sound;

export const dateText = (c: Context): string => C.dateText(c);

// ------------------------------------------------------------------ start-up
/** lines 29000-29020: read the hand-over and the two grave records. The two draws here are the first of the journey. */
export function loadState(c: Context): void {
  const st = c.st, mem = c.mem;
  const P = (n: number) => N.parse(String(n));
  st.MY = N.div(P(mem.peekWord(913)), N.parse("10"));
  st.AM = P(mem.peek(902));
  st.AD = P(mem.peek(903));
  st.AY = P(mem.peek(901) + 1800);
  st.ZO = 0;
  st.AS = N.mul(c.rng.rnd1("29000 initial snow"), N.parse("12"));
  if (N.asInt(st.AM) >= 4) st.AS = N.ZERO;       // the draw happened; the product did not
  st.W = N.int_(N.div(N.add(fnW(c, 0), N.parse("10")), N.parse("20")));
  st.RE[7] = N.parse(".06"); st.RE[9] = N.parse(".02"); st.RE[12] = N.parse(".01");
  st.RE[13] = N.parse(".02"); st.RE[1] = N.parse(".007"); st.RE[2] = N.ZERO;
  st.TM = st.W;
  st.AR = N.add(P(7 - N.asInt(st.AM)), c.rng.rnd1("29004 initial rain"));
  st.Q1 = 1;
  st.SN = [0, 0]; st.ML = [0, 0];
  // FOR L = 0 TO 1: & TPTR,L * 49: & TREED ... -- the two records of the current side's TOMB.SEQ
  for (const recNo of [0, 1]) {
    const rec = c.files.readTombs(st.S, recNo);
    if (rec) { st.SN[recNo] = rec.segment; (st.ML as any[])[recNo] = rec.miles; }
  }
  for (let item = 3; item < 8; item++) st.I[item] = P(mem.peek(905 + item));
  st.I[8] = P(mem.peek(906) + mem.peek(907) * 256);
  st.I[2] = P(2 * mem.peek(905));
  st.I[4] = P(mem.peek(909) * 20);
  st.PF = st.I[8];
  st.N = mem.getNames(5);
}

/** line 105: the climate lookup */
export function fnW(c: Context, which: number): N.Fac {
  const st = c.st;
  const row = D.WC[st.ZO];
  const pos = N.asInt(st.AM) * 2 + which - 2;
  const code = row.charCodeAt(pos);
  if (which === 0) return N.parse(String(code - 30 - 20));
  // .003 * Z is the left operand of the outer *, so .003 comes first
  return N.mul(N.parse(".003"), N.parse(String(code - 30)));
}

/** lines 650-660 */
export function speed(c: Context): N.Fac {
  const st = c.st;
  let v = N.store(N.div(st.I[2], N.parse("4")));     // V is a variable
  if (N.gt(v, N.ONE)) v = N.ONE;
  st.FC = N.mul(N.parse(String(st.NP)), N.sub(N.parse("4"), st.R));
  st.BS = N.div(N.mul(N.mul(st.MD, v), N.add(st.P, N.ONE)), N.parse("2"));
  st.OP = N.div(st.I[3], N.parse(String(st.NP)));
  st.F0 = N.mul(N.parse("2"), N.sub(st.R, N.ONE));
  st.Z = st.BS;
  return st.BS;
}

// -------------------------------------------------------------- the daily cycle
/** line 500: run the daily cycle for SD days without travelling */
export async function runStoppedDays(c: Context): Promise<void> {
  const st = c.st;
  if (!st.SD) return;
  const savedD = st.D, savedM = st.M, savedP = st.P;
  st.D = N.ZERO; st.P = N.ZERO;
  const n = st.SD;
  for (let i = 0; i < n; i++) if (!(await dayBody(c))) break;
  st.SD = 0;
  st.D = savedD; st.M = savedM; st.P = savedP;
  st.I[8] = st.PF;
}

/** lines 550-570 */
export async function loseDays(c: Context, tag: string, most: number, label = ""): Promise<number> {
  const st = c.st;
  const xx = N.trunc(N.add(N.mul(c.rng.rnd1(tag), N.parse(String(most))), N.ONE));
  let text = `${label}.  Lose ${N.str_(N.parse(String(xx)))} day`;
  if (xx > 1) text += "s";
  text += ".";
  await C.message700(c, text);               // 560: GOSUB 700 -- no wait
  st.SD = xx;
  await runStoppedDays(c);                   // 570: SD = XX: GOSUB 500
  const key = await C.waitKey(c);
  st.B = RETURN_KEYS.includes(key) ? 1 : 0;  // B = (PEEK (-16384) = 13)
  return xx;
}

// ------------------------------------------------------------------ the screen
/** lines 300-401: the travel screen, as a block of text (or the scene, in the graphical build) */
export async function travelScreen(c: Context, daily = false): Promise<void> {
  const st = c.st;
  const half = daily ? N.HALF : N.ZERO;
  if (c.ui.pictures) { await scene(c, { daily, prompt: st.LM !== st.NM }); return; }
  await c.ui.print(`${dateText(c)}`);
  const rows: [string, string][] = [
    [D.TRAVEL_LABELS[1], dateText(c)],
    [D.TRAVEL_LABELS[2], D.WEATHER[N.asInt(st.W)]],
    [D.TRAVEL_LABELS[3], D.healthWord(st.healthBand())],
    [D.TRAVEL_LABELS[4], N.str_(st.PF) + " pounds"],
    [D.TRAVEL_LABELS[5], N.str_(N.int_(N.add(st.D, half))) + " miles"],
    [D.TRAVEL_LABELS[6], N.str_(N.int_(N.add(st.M, half))) + " miles"],
  ];
  for (const [label, value] of rows) await c.ui.print("  " + label.padEnd(16) + value);
  if (st.LL) for (let i = 0; i < 6; i++) st.T[i] = "";
}

/** the six figures of the travel screen (lines 315-320) */
export function sceneValues(c: Context, daily = false): string[] {
  const st = c.st;
  const half = daily ? N.HALF : N.ZERO;
  return [dateText(c), D.WEATHER[N.asInt(st.W)], D.healthWord(st.healthBand()),
    N.str_(st.PF) + " pounds",
    N.str_(N.int_(N.add(st.D, half))) + " miles",
    N.str_(N.int_(N.add(st.M, half))) + " miles"];
}

/** line 3000: FX = 180 - L%(NM - 1, 1): IX = FX - D * 2 */
export function sceneStart(c: Context): void {
  const st = c.st;
  const off = st.NM ? D.SCENERY[Math.min(st.NM - 1, D.SCENERY.length - 1)][1] : 0;
  const fx = 180 - off;
  c.scene = { fx, ix: fx - 2 * N.asInt(st.D), wg: 1, moved: false };
}

export interface SceneOptions {
  daily?: boolean; prompt?: boolean; message?: string | null; box?: [number, number, number, number];
  values?: string[]; pictures?: [string, number, number][]; lines?: string[]; centre?: boolean;
}

/** lines 300-320 and the loop at 3246: draw the travel screen (graphical build only) */
export async function scene(c: Context, o: SceneOptions = {}): Promise<void> {
  const st = c.st;
  const daily = o.daily ?? false, prompt = o.prompt ?? true;
  st.SR = N.ONE;                       // line 310: SR = 1
  if (!c.scene) sceneStart(c);
  const sc = c.scene!;
  // 3246: VP = INT(((FX - D * C2 - IX) / C4) + .5), and each step moves the picture four dots
  const vp = Math.trunc((sc.fx - N.asFloat(st.D) * 2 - sc.ix) / 4 + 0.5);
  const ni = st.NM ? D.SCENERY[Math.min(st.NM - 1, D.SCENERY.length - 1)][0] : 0;
  const side = st.NM <= 5 ? "prairie" : "mountains";
  const ground = N.asFloat(st.AS) >= 1 ? 3 : (N.asFloat(st.AR) <= 0.2 ? 5 : 1);
  const live = daily && c.ui.pictures && c.ui.dailyPause > 0;
  const draw = async () => {
    await screens(c).travel(c.ui, side, sc.moved ? ni : 0, sc.ix, sc.wg, ground,
      D.TRAVEL_LABELS.slice(1), o.values ?? sceneValues(c, daily),
      { prompt: prompt ? D.TRAVEL_LABELS[0] : null, message: o.message ?? null,
        box: o.box ?? [28, 60, 250, 97], pictures: o.pictures ?? [], lines: o.lines ?? [], centre: o.centre ?? false });
  };
  for (let i = 0; i < Math.max(0, vp); i++) {
    sc.wg = (sc.wg % 3) + 1;
    sc.ix += 4;
    sc.moved = true;
    if (live) { await draw(); await (c.ui as any).refresh?.(); await c.ui.sleep?.(0.05); }
  }
  await draw();
  if (live) await (c.ui as any).refresh?.();
}

/** lines 700 and 900: a framed message over the travel scene, and the event's picture */
export async function eventBox(c: Context, text: string, lines: string[] = [], kind = 900, g = 0): Promise<void> {
  const st = c.st;
  const pics = c.eventPic ? [...c.eventPic] : [];
  let box: [number, number, number, number], centre: boolean;
  if (kind === 900) {
    const b = [28, 60, 238, 90 + 9 * lines.length];
    box = [b[0], b[1], Math.floor(b[2] / 7) * 7 + 5, b[3]];
    centre = false;
  } else {
    const x = 6 + Math.trunc(text.length / 2 * 8);
    const x1 = x < 140 ? 139 - x : 0;
    const x2 = x < 140 ? 139 + x : 279;
    box = [Math.floor(x1 / 7) * 7, 60 + g, Math.floor(x2 / 7) * 7 + 5, 80 + g];     // 700: Y1 = 60 + G
    centre = true;
  }
  if (c.keepScreen || (g && st.SD)) {
    await screens(c).messageBox(c.ui, text, box, { redraw: false, centre, lines });
    return;
  }
  await scene(c, { prompt: st.LM !== st.NM && !g, pictures: pics, message: text, box, lines, centre });
}

/** line 3504: take the party left by a river crossing */
export async function removeDrowned(c: Context): Promise<string | null> {
  const st = c.st;
  const minusTwo = N.parse("-2");
  let l1 = 0;
  while (l1 <= 4) {
    st.Q = N.parse(String(l1));
    if (N.eq(st.H1[l1], minusTwo)) {
      if ((await illness.die(c, l1, false)) === "DIED") return "DIED";
      l1 = 0;
    }
    l1 += 1;
  }
  return null;
}

/** lines 450-460: is there a grave ahead on this segment? */
export function findGrave(c: Context): N.Fac {
  const st = c.st;
  st.DL = N.neg(N.ONE);
  const sn = N.asInt(st.NM) * 100 + N.asInt(st.LM);
  for (const i of [0, 1]) {
    const ml = graveMiles((st.ML as any[])[i]);
    if (st.SN[i] === sn && N.lt(st.DL, ml) && N.lt(ml, st.D)) { st.LN = i; st.DL = ml; }
  }
  return st.DL;
}
/** ML(L4) or DL as the variable holds it: VAL of the text, stored */
export function graveMiles(v: N.Fac | number | string): N.Fac {
  if (v instanceof N.Fac) return v;
  return N.store(N.parse(typeof v === "string" ? String(Number(v)) : String(v)));
}

/** lines 3205-3206 */
export function weather(c: Context): void {
  const st = c.st;
  if (c.rng.below("3205 weather change", N.HALF)) {
    st.TM = N.add(st.QT, N.int_(N.mul(c.rng.rnd1("3205 temperature"), N.parse("41"))));
    st.PP = c.rng.below("3205 rain flag", st.QP) ? N.ONE : N.ZERO;
    st.W = N.int_(N.div(N.add(st.TM, N.parse("10")), N.parse("20")));
    st.TM = st.W;
  }
  st.TR = N.ZERO; st.TS = N.ZERO;
  if (!st.PP.isZero()) {
    const z = c.rng.below("3206 heavy rain", N.parse(".3")) ? N.ONE : N.ZERO;
    st.W = N.int_(N.add(N.add(N.parse("6"), z), z));
    st.TR = N.add(N.parse(".2"), N.mul(N.parse(".6"), z));
    if (N.lt(st.TM, N.TWO)) {
      st.W = N.add(st.W, N.ONE);
      st.TS = N.mul(N.parse("8"), st.TR);
      st.TR = N.ZERO;
    }
  }
}

/** line 3240 */
function accumulate(c: Context): void {
  const st = c.st;
  st.AR = N.store(N.add(N.mul(N.parse(".9"), st.AR), st.TR));
  st.AS = N.store(N.add(N.mul(N.parse(".97"), st.AS), st.TS));
  if (!st.AS.isZero() && (N.gt(st.TM, N.TWO) || N.eq(st.W, N.parse("8")))) {
    st.AR = N.add(st.AR, N.HALF);
    st.AS = N.sub(st.AS, N.parse("5"));
    if (N.lt(st.AS, N.ZERO)) st.AS = N.ZERO;
  }
}

/** lines 3244-3246 */
function travelToday(c: Context): N.Fac {
  const st = c.st;
  let z = N.store(N.sub(N.ONE, N.div(st.AS, N.parse("40"))));
  if (N.lt(z, N.ZERO)) z = N.ZERO;
  let v = N.chain(st.BS).mul(N.sub(N.ONE, N.mul(N.parse(".1"), N.parse(String(st.H0)))));
  v = v.mul(N.parse(st.SD ? "0" : "1")).mul(z);
  let vv = v.done();
  if (N.gt(N.mul(N.parse("1.1"), vv), st.D)) vv = st.D;
  st.D = N.sub(st.D, vv);
  st.M = N.add(st.M, vv);
  st.V = vv;
  return vv;
}

/** line 3255 */
function advanceDate(c: Context): void {
  const st = c.st;
  let ad = N.asInt(st.AD) + 1, am = N.asInt(st.AM), ay = N.asInt(st.AY);
  if (ad > MONTH_DAYS[am - 1]) {
    ad = 1; am += 1;
    if (am > 12) { am = 1; ay += 1; }
  }
  st.AD = N.parse(String(ad)); st.AM = N.parse(String(am)); st.AY = N.parse(String(ay));
  st.QT = fnW(c, 0);
  st.QP = fnW(c, 1);
}

/** lines 3207-3230 */
function healthToday(c: Context): N.Fac {
  const st = c.st;
  let zt = N.sub(st.TM, N.parse("3"));
  if (N.lt(zt, N.ZERO)) zt = N.sub(N.parse("2"), st.TM);
  st.ZT = zt;
  let zc = N.sub(N.sub(N.sub(N.parse("5"), st.TM), st.TM), st.OP);
  if (N.lt(zc, N.ZERO)) zc = N.ZERO;
  st.ZC = zc;
  st.ZF = !N.eq(st.PF, N.ZERO) ? st.F0 : N.parse("8");
  let zp = N.add(N.bool_(N.gt(st.W, N.parse("5"))), N.bool_(N.gt(st.W, N.parse("7"))));
  zp = N.add(N.add(zp, st.P), st.P);
  st.ZP = zp;
  const x = N.gt(st.ZC, N.HALF), y = N.eq(st.PF, N.ZERO);
  let z = N.mul(st.FS, N.HALF);
  if (x || y) z = N.add(st.FS, N.parse(".8"));
  st.FS = z;
  st.H = N.chain(N.parse(".9")).mul(st.H).add(st.ZT).add(st.ZC).add(st.ZF)
    .add(st.ZP).add(st.FS).add(N.parse(String(st.H0))).add(st.HR).done();
  st.PF = N.sub(st.PF, st.FC);
  if (N.lt(st.PF, N.ZERO)) st.PF = N.ZERO;
  return st.H;
}

/** line 3200 */
function countIll(c: Context): void {
  const st = c.st;
  st.H0 = 0;
  for (let i = 0; i < 5; i++) {
    if (N.gt(st.H1[i], N.ZERO)) {
      st.H2[i] = N.sub(st.H2[i], N.ONE);
      st.H0 += 1;
      if (N.lt(st.H2[i], N.ONE)) st.H1[i] = N.ZERO;
    }
  }
}

/** lines 3100-3499: one day after another until the segment's miles are gone */
export async function dailyCycle(c: Context): Promise<void> {
  const st = c.st;
  while (N.cmp(st.D, N.ZERO) !== 0) if (!(await dayBody(c))) break;
  st.I[8] = st.PF;
}

/** lines 800-810: press Return to stop and open the action menu */
export async function pollKey(c: Context): Promise<boolean> {
  if (c.st.SD) return false;
  const k = c.ui.pollKey();
  if (k !== null && RETURN_KEYS.includes(k)) { await action.actionMenu(c); return true; }
  return false;
}

/** how long a day's scene stays on the screen, by pace (P = 1 steady, 2 strenuous, 3 grueling) */
const DAY_SECONDS: Record<number, number> = { 1: 1.0, 2: 0.5, 3: 0.3 };
export function daySeconds(c: Context): number {
  if ((c.ui as any).byPace) return DAY_SECONDS[N.asInt(c.st.P)] ?? DAY_SECONDS[1];
  return c.ui.dailyPause;
}

/** hold the day's scene; Return in that time opens the action menu on a travelling day. False if the last member died in it. */
async function dayPause(c: Context): Promise<boolean> {
  const st = c.st;
  const pause = daySeconds(c);
  if (pause <= 0) return true;
  let elapsed = 0;
  const step = 0.05;
  while (elapsed < pause - 1e-9) {
    const k = st.SD ? null : c.ui.pollKey();       // (a stopped day reads no key)
    if (!st.SD && k !== null && RETURN_KEYS.includes(k)) {
      await action.actionMenu(c);
      if (N.asInt(st.NP) <= 0) return false;
      break;
    }
    if (st.SD) await (c.ui as any).pump?.();         // keep the window alive on a stopped day
    await c.ui.sleep?.(step);
    elapsed += step;
  }
  return true;
}

/** lines 3100 to 3265: one day, whether or not the wagon moves. False when the party has all died. */
export async function dayBody(c: Context): Promise<boolean> {
  const st = c.st;
  c.eventPic = null;
  st.QT = fnW(c, 0);
  st.QP = fnW(c, 1);
  if (!st.SD) {
    await pollKey(c);
    if (N.asInt(st.NP) <= 0) return false;
  }
  if (N.gt(st.H, N.parse("139"))) st.H = N.parse("139");
  await eventLoop(c);
  if (N.asInt(st.NP) <= 0) return false;
  if (!st.SD) {
    await pollKey(c);                          // 3190 ends ... GOSUB 800
    if (N.asInt(st.NP) <= 0) return false;
  }
  countIll(c);
  weather(c);
  healthToday(c);
  if (!st.W1 && N.gt(st.H, N.parse("139"))) {
    await illness.illness(c);
    if (N.asInt(st.NP) <= 0) return false;     // the forced illness killed the last member (3235)
  }
  accumulate(c);
  travelToday(c);
  if (N.gt(st.H, N.parse("139"))) st.H = N.parse("139");
  advanceDate(c);
  if (st.SD && c.ui.pictures && N.asInt(st.SR)) {
    await screens(c).updateValues(c.ui, sceneValues(c).slice(0, 4));        // 3260: IF SR THEN ...
    if (c.ui.dailyPause > 0) await (c.ui as any).refresh?.();
    await dayPause(c);
  }
  if (!st.SD && c.ui.showDailyScreen) {
    await travelScreen(c, true);
    if (!(await dayPause(c))) return false;    // the last member died in the menu
  }
  c.trace.day(st, !!st.SD);
  if (N.cmp(st.D, N.ZERO) === 0) st.I[8] = st.PF;
  return true;
}

/** lines 3180-3190: test the fifteen events, in order */
async function eventLoop(c: Context): Promise<void> {
  const st = c.st;
  st.RE[0] = N.gt(st.AS, N.parse("30")) ? N.ONE : N.ZERO;
  st.RE[14] = N.mul(N.HALF, N.lt(st.AR, N.parse(".1")) ? N.ONE : N.ZERO);
  st.RE[3] = N.add(N.parse(".01"), N.div(st.H, N.parse("1500")));
  st.RE[4] = N.lt(st.D, graveMiles(st.DL)) ? N.ONE : N.ZERO;
  st.RE[5] = N.mul(N.parse(".05"), N.eq(st.PF, N.ZERO) ? N.ONE : N.ZERO);
  st.RE[6] = N.add(N.gt(st.W, N.parse("7")) ? N.ONE : N.ZERO,
    N.mul(N.parse(".15"), N.lt(st.TM, N.TWO) ? N.ONE : N.ZERO));
  st.HR = N.ZERO;
  if (st.SD) return;
  for (let which = 0; which < 15; which++) {
    if (!c.rng.below(`3180 event ${which}`, st.RE[which])) continue;
    await events.fire(c, which);
    if (N.asInt(st.NP) <= 0) return;           // the last member died: TOMB.LIB never returns
    if (st.B > 0) { await action.actionMenu(c); break; }   // L8 = 20 ends the loop
  }
}

// ------------------------------------------------------------------- segments
/** lines 2100-2120: South Pass and the Blue Mountains each lead two ways. null means "see the map" (back to 1015). */
async function chooseSegment(c: Context): Promise<number | null> {
  const st = c.st;
  await travelScreen(c);
  const second = D.LM_SEGMENT2[st.LM];
  if (!second) return D.LM_SEGMENT[st.LM];
  if (c.ui.pictures) {
    await screens(c).box41000(c.ui, "The trail divides here.  You may:", 0, 60, 279, 154);
    await c.ui.print();
  } else {
    await c.ui.print("The trail divides here.  You may:");
    await c.ui.print();
  }
  let i = 0;
  for (const seg of [D.LM_SEGMENT[st.LM], second]) { i += 1; await c.ui.print(`${i}. head for ${D.LM_NAMES[D.SEG_ENDS_AT[seg]]}`); }
  await c.ui.print("3. see the map");
  await c.ui.print();
  await c.ui.print("What is your choice? ");
  const a = (await c.ui.key(ALLOWED.SEGMENT, 1)) as string;
  const choice = /^\d+$/.test(a) ? parseInt(a, 10) : 1;
  if (choice === 3) { await maplib.show(c); return null; }
  return choice === 2 ? second : D.LM_SEGMENT[st.LM];
}

/** line 2200 */
export async function loadSegment(c: Context, seg: number): Promise<void> {
  const st = c.st;
  st.Z = N.parse(String(seg));
  st.D = N.parse(String(D.SEG_MILES[seg]));
  st.MD = N.parse(String(D.SEG_SPEED[seg]));
  st.NM = D.SEG_ENDS_AT[seg];
  if (c.ui.pictures) {
    // 2200 prints the distance in the "Next landmark" place and draws the message over the scene
    sceneStart(c);
    const values = sceneValues(c);
    values[3] = N.str_(st.I[8]) + " pounds";
    await scene(c, { prompt: false, values, box: [28, 60, 250, 97 + (st.LM === 1 ? 9 : 0)],
      message: `From ${D.LM_NAMES[st.LM]} it is ${N.str_(st.D)} miles to ${D.LM_NAMES[st.NM]}.` });
    await c.ui.waitKey("", "Press SPACE BAR to continue", { y: 182, tune: true });      // 2200 ends GOSUB 950
    return;
  }
  await c.ui.print();
  await c.ui.print(N.str_(st.D) + " miles");
  await c.ui.print(`From ${D.LM_NAMES[st.LM]} it is ${N.str_(st.D)} miles to ${D.LM_NAMES[st.NM]}.`);
  await C.waitKey(c);
}

/** line 3000 */
export function startSegment(c: Context): void {
  const st = c.st;
  st.PF = st.I[8];
  st.DD = st.D;
  st.SD = 0;
  if (c.ui.pictures) sceneStart(c);
  speed(c);
  const one = (b: boolean) => (b ? N.ONE : N.ZERO);
  st.RE[8] = N.add(N.parse(".04"), N.mul(N.parse(".03"), one(st.ZO > 2)));
  st.RE[10] = N.mul(N.parse(".05"), one(st.ZO > 2));
  st.RE[11] = N.mul(N.parse(".04"), one(N.asInt(st.AM) > 4 && N.asInt(st.AM) < 10));
  findGrave(c);
}

/** line 21000: no oxen, so the journey stops here until a trade supplies some */
export async function checkOxen(c: Context): Promise<void> {
  const st = c.st;
  if (!N.eq(st.I[2], N.ZERO)) return;
  await c.ui.print("You are unable to continue your journey.  You have no oxen to pull the wagon.");
  await C.waitKey(c);
  st.B = 2;
}

/** lines 1000-1005: A = INT(RND(1) * 3) and the climate zone */
function arrive(c: Context): void {
  const st = c.st;
  st.A = c.rng.intRange("1000 arrival dialogue", 3);
  st.ZO = D.zoneFor(st.LM);
}

/** lines 1000-1020: the journey, landmark by landmark */
export async function run(c: Context): Promise<string> {
  c.setProgram("OREGON TRAIL");
  const st = c.st;
  for (;;) {
    arrive(c);
    if (st.LM) sound(c)?.select?.(`ms${st.LM}`);      // 1005: & RFL, "MS" + STR$ (LM) + ".BIN"
    let lookAround = st.LM === 0;
    if (st.LM) {
      const ask = `You are now at ${D.LM_NAMES[st.LM]}.  Would you like to look around? `;
      if (c.ui.pictures) await scene(c, { prompt: false, message: ask, box: [21, 60, 257, 98] });
      else await c.ui.print(ask);
      lookAround = (await C.yesNo(c)) === "Y";
      st.Q_arr[st.Q1] = st.LM;
      st.Q1 += 1;
    }
    if (lookAround) {
      st.LL = 0;
      if (c.ui.pictures) {
        await screens(c).landmarkScreen(c.ui, st.LM, D.shortName(st.LM), dateText(c));
        await c.ui.waitKey("", "Press SPACE BAR to continue", { y: 182, tune: true });      // 1010: GOSUB 950
      } else await C.waitKey(c);                       // 1010: GOSUB 300: GOSUB 950
      await action.actionMenu(c);
      st.LL = 1;
      if (N.asInt(st.NP) <= 0) return "DIED";
    }
    let seg: number | null;
    for (;;) {
      if (D.LM_TYPE[st.LM] === 2) {
        await river.crossing(c);
        st.PF = st.I[8];                 // line 3505
        st.W1 = 0;                       // line 3504: "GOSUB 50000:W1 = 0"
        if (N.asInt(st.NP) <= 0) return "DIED";
      }
      await checkOxen(c);
      if (st.B > 0) {
        await action.actionMenu(c);
        if (N.asInt(st.NP) <= 0) return "DIED";
      }
      if (st.LM === 16) return await endl.theDalles(c);
      seg = await chooseSegment(c);
      if (seg === null) continue;        // GOTO 1015
      break;
    }
    if (st.NM === 17) { endl.writeHandover(c); return "WIN"; }
    // 1016: line 2200 loads the chosen segment, then line 3000 starts it
    st.LL = 1;
    await loadSegment(c, seg);
    startSegment(c);
    await travelScreen(c);
    await dailyCycle(c);
    if (N.asInt(st.NP) <= 0) return "DIED";
    st.LM = st.NM;
    if (st.LM === 5) await flip.toSide2(c);
    if (st.LM === 17) { endl.writeHandover(c); return "WIN"; }
  }
}
