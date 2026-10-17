/** RIVER.LIB and CROSS.LIB: crossing the river, and the draws the crossing animation spends. */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";
import * as lf from "./lf.js";
import { ALLOWED } from "./ui.js";

const TXT = D.RIVER_T;
const screens = (c: Context): any => c.ui.screens;

function spend(c: Context, count: number, tag: string): void {
  for (let i = 0; i < count; i++) c.rng.rnd1(`${tag} ${i}`);
}

/** line 50150 */
function conditions(c: Context): void {
  const st = c.st;
  const row = D.RC[st.RC];
  const p = (n: number) => N.parse(String(n));
  st.RD = N.store(N.div(N.int_(N.add(N.mul(N.add(p(row[0]), N.mul(st.AR, N.parse("2"))), N.parse("10")), N.parse(".5"))), N.parse("10")));
  st.RW = N.int_(N.add(p(row[1]), N.mul(N.parse("15"), st.AR)));
  st.RS = N.add(p(row[2]), st.AR);
  st.RB = row[3];
}

/** lines 50000-50030: the menu, and whichever way the player chooses */
export async function crossing(c: Context): Promise<void> {
  const st = c.st;
  st.RC = D.RC_RIVER_AT[st.LM];
  st.W1 = 1;
  conditions(c);
  for (let i = 0; i < 6; i++) st.T[i] = TXT[i];
  const gfx = c.ui.pictures;
  st.SR = 0 as any;
  const intro = "You must cross the river in order to continue.  The river at this point is currently "
    + N.str_(st.RW) + " feet across, and " + N.str_(st.RD) + " feet deep in the middle.";
  if (gfx) {
    await screens(c).riverPage(c.ui, D.shortName(st.LM), C.dateText(c));
    await screens(c).riverText(c.ui, intro);
  } else {
    await c.ui.clear();
    await c.ui.print(D.shortName(st.LM));
    await c.ui.print(C.dateText(c));
    await c.ui.print(intro);
  }
  await C.waitKey(c);
  const extra = D.RC[st.RC][5];
  const menu = [TXT[0], TXT[1]];
  const f = extra ? 1 : 0;
  if (extra) menu.push(TXT[extra + 3]);
  menu.push(TXT[2]);
  menu.push(TXT[3]);
  for (;;) {
    conditions(c);
    if (gfx) await screens(c).riverMenu(c.ui, D.WEATHER[N.asInt(st.W)], N.str_(st.RW), N.str_(st.RD), menu);
    else {
      await c.ui.print();
      await c.ui.print("Weather: " + D.WEATHER[N.asInt(st.W)]);
      await c.ui.print("River width: " + N.str_(st.RW) + " feet");
      await c.ui.print("River depth: " + N.str_(st.RD) + " feet");
      await c.ui.print();
      await c.ui.print("You may:");
      let i = 0;
      for (const label of menu) { i += 1; await c.ui.print(`${i}. ${label}`); }
      await c.ui.print();
      await c.ui.print("What is your choice? ");
    }
    const a = (await c.ui.key(ALLOWED.RIVER, 1, "")) as string;
    const v = /^\d+$/.test(a) ? parseInt(a, 10) : 0;
    if (v === 4 + f) { await information(c); continue; }
    if (v === 3 + f) {
      if (gfx) await screens(c).riverNotice(c.ui, ["You camp near the river for a day."]);
      else await c.ui.print("You camp near the river for a day.");
      await C.waitKey(c);
      st.SD = 1;
      await T.runStoppedDays(c);
      if (gfx) await screens(c).riverDate(c.ui, C.dateText(c));
      continue;
    }
    st.IX = N.ONE;
    const v2 = v === 3 && extra === 2 ? v + 1 : v;
    if (v2 === 1) { await ford(c); await animate(c, 2); await showResult(c); await buryDrowned(c); return; }
    if (v2 === 2) {
      if ((await floatCrossing(c)) === null) continue;
      await animate(c, 3); await showResult(c); await buryDrowned(c); return;
    }
    if (v2 === 3) {
      if ((await guide(c)) === null) continue;
      await animate(c, c.riverMethod); await showResult(c); await buryDrowned(c); return;
    }
    if (v2 === 4) {
      if (await ferry(c)) { await animate(c, 1); await showResult(c); await buryDrowned(c); return; }
      continue;
    }
  }
}

/** show what has been drawn so far and wait a second, when a person is watching */
async function hold(c: Context, seconds = 1.0): Promise<void> {
  if (c.ui.pictures && c.ui.dailyPause > 0) { await (c.ui as any).refresh?.(); await c.ui.sleep?.(seconds); }
}

/** line 3504: CROSS.LIB, run once RIVER.LIB has returned. method: 1 ferry, 2 ford, 3 float. */
async function animate(c: Context, method: number): Promise<void> {
  const gfx = c.ui.pictures;
  if (gfx) {
    await screens(c).riverFrame(c.ui, D.shortName(c.st.LM), C.dateText(c), method);
    await hold(c);
    await screens(c).riverFirstHalf(c.ui);
    await hold(c);
  }
  spend(c, 106, "CROSS first half");
  if (!c.riverLosses) {
    if (gfx) { await screens(c).riverTailSuccess(c.ui); await hold(c); }
    spend(c, 122, "CROSS success tail");
  } else if (method === 2) {
    if (gfx) {
      if ((c.ui as any).cv.plain) (c.ui as any).cv.image("river_04", 102, 63);   // a themed folder shows the wagon capsized
      else await screens(c).riverTailFailedFord(c.ui);
      await hold(c);
    }
    for (let g = 0; g < 22; g++) { spend(c, 1, `CROSS failed ford ${g} a`); spend(c, 2, `CROSS failed ford ${g} b`); }
  } else if (gfx) {
    (c.ui as any).cv.image("river_04", 102, 63);        // 50050
    await hold(c);
  }
}

async function information(c: Context): Promise<void> {
  const texts = [
    "To ford a river means to pull your wagon across a shallow part of the river, with the oxen still attached.",
    "To caulk the wagon means to seal it so that no water can get in.  The wagon can then be floated across like a boat.",
    "To use a ferry means to put your wagon on top of a flat boat that belongs to someone else.  The owner of the ferry will take your wagon across the river.",
  ];
  const gfx = c.ui.pictures;
  for (let which = 0; which < 3; which++) {
    if (gfx) { await screens(c).riverWindow6(c.ui, which === 0); (c.ui as any).para(texts[which]); }
    else { await c.ui.clear(); await c.ui.print(texts[which]); }
    await C.waitKey(c);
  }
}

function say(c: Context, text: string, lines: string[] = []): void {
  c.riverLosses = lines.length;
  lines.forEach((t, i) => { c.st.T[i] = t; });
  c.riverMessage = [text, [...lines]];
}

async function ford(c: Context, ix?: N.Fac): Promise<string> {
  const st = c.st;
  if (ix === undefined) ix = st.IX;
  st.IX = ix;
  let lines: string[] = [];
  if (N.lt(st.RD, N.parse("2.5"))) {
    if (st.RB === D.MUDDY) {
      if (c.rng.below("50060 stuck in mud", N.div(N.parse(".4"), ix))) {
        say(c, "You become stuck in the mud.  Lose 1 day.");
        st.SD = 1;
        await T.runStoppedDays(c);
        return "stuck";
      }
      say(c, "It was a muddy crossing, but you did not get stuck.");
      return "success";
    }
    if (st.RB === D.ROUGH) {
      if (c.rng.below("50070 wagon tips", N.div(N.parse(".16"), ix))) {
        const v = N.store(N.add(N.parse(".1"), N.mul(c.rng.rnd1("50070 loss chance"), N.parse(".3"))));
        lines = loseGoods(c, v);
        say(c, "The wagon tipped over" + (lines.length ? ".  You lose:" : " but you did not lose anything."), lines);
        return "tipped";
      }
      say(c, "It was a rough crossing, but you did not overturn.");
      return "success";
    }
    say(c, "You made the crossing successfully.");
    return "success";
  }
  if (N.lt(st.RD, N.parse("3"))) {
    say(c, "Your supplies got wet.  Lose 1 day.");
    st.SD = 1;
    await T.runStoppedDays(c);
    return "wet";
  }
  lines = loseGoods(c, N.store(N.div(N.div(st.RD, N.parse("10")), ix)));
  lines = lines.concat(loseOxen(c, N.store(N.div(N.div(N.sub(st.RD, N.ONE), N.parse("10")), ix))));
  lines = lines.concat(losePeople(c, N.store(N.div(N.div(N.sub(st.RD, N.parse("2.5")), N.parse("10")), ix)), lines.length));
  say(c, lines.length ? "The river is too deep to ford.  You lose:" : "You made the crossing successfully.", lines);
  return "deep";
}

async function floatCrossing(c: Context, ix?: N.Fac): Promise<boolean | null> {
  const st = c.st;
  if (ix === undefined) ix = st.IX;
  st.IX = ix;
  if (N.lt(st.RD, N.parse("1.5"))) {
    if (c.ui.pictures) await screens(c).riverNotice(c.ui, ["The river is too shallow", "to float across."]);
    else { await c.ui.clear(); await c.ui.print("The river is too shallow"); await c.ui.print("to float across."); }
    await C.waitKey(c);
    return null;
  }
  st.SD = 1;
  await T.runStoppedDays(c);
  let lines: string[] = [];
  const v = N.store(N.div(N.mul(N.bool_(N.gt(st.RD, N.parse("2.5"))), N.div(st.RS, N.parse("20"))), ix));
  if (c.rng.below("50085 wagon tips", v)) {
    lines = loseGoods(c, N.store(N.div(N.add(N.parse(".4"), N.div(st.RS, N.parse("25"))), ix)));
    lines = lines.concat(losePeople(c, N.store(N.div(N.div(N.sub(st.RS, N.parse("3")), N.parse("15")), ix)), lines.length));
  }
  if (lines.length) say(c, "The wagon tipped over while floating.  You lose:", lines);
  else say(c, "You had no trouble floating the wagon across.");
  return true;
}

async function ferry(c: Context): Promise<boolean> {
  const st = c.st;
  if (N.lt(st.RD, N.parse("2.5"))) {
    const text = "The ferry is not operating today because the river is to shallow.";
    if (c.ui.pictures) await screens(c).riverNotice(c.ui, [text], { centre: false });
    else { await c.ui.clear(); await c.ui.print(text); }
    await C.waitKey(c);
    return false;
  }
  const x = N.int_(N.add(N.mul(c.rng.rnd1("50101 ferry wait"), N.parse("5")), N.parse("2")));
  let v = N.parse("5");
  const offer = "The ferry operator says that he will charge you $" + C.money(c, v)
    + " and that you will have to wait " + N.str_(x) + " days.  Are you willing to do this? ";
  const gfx = c.ui.pictures;
  if (gfx) {
    await screens(c).riverWindow6(c.ui, true);
    (c.ui as any).para(offer.trimEnd(), false);
    (c.ui as any).put(" ");
  } else { await c.ui.clear(); await c.ui.print(offer); }
  const answer = await C.yesNo(c);
  if (answer === "Y" && N.lt(st.MY, v)) {
    const text = "You do not have enough money to pay for the ferry.";
    if (gfx) { await screens(c).riverWindow6(c.ui, false); (c.ui as any).para(text); }
    else await c.ui.print(text);
    await C.waitKey(c);
    return false;
  }
  if (answer === "N") return false;
  st.MY = N.sub(st.MY, v);
  st.SD = N.asInt(x);
  await T.runStoppedDays(c);
  let lines: string[] = [];
  v = N.store(N.add(N.mul(N.parse(".05"), N.bool_(N.gt(st.RS, N.parse("5")))), N.mul(N.parse(".1"), N.bool_(N.gt(st.RS, N.parse("10"))))));
  if (c.rng.below("50120 ferry breaks loose", v)) {
    lines = loseGoods(c, N.store(N.parse(".8")));
    lines = lines.concat(losePeople(c, N.store(N.parse(".2")), lines.length));
    lines = lines.concat(loseOxen(c, N.store(N.parse(".5"))));
    if (lines.length) say(c, "The ferry broke loose from moorings. You lose:", lines);
    else say(c, "Some trouble in crossing but nothing was lost.");
    return true;
  }
  say(c, "The ferry got your party and wagon safely across.");
  return true;
}

async function guide(c: Context): Promise<boolean | null> {
  const st = c.st;
  const x = N.int_(N.add(N.mul(c.rng.rnd1("50130 sets asked"), N.parse("2")), N.parse("2")));
  const gfx = c.ui.pictures;
  const offer = "A Shoshoni guide says that he will take your wagon across the river in exchange for " + N.str_(x) + " sets of clothing.";
  if (gfx) { await screens(c).riverWindow6(c.ui, true); (c.ui as any).para(offer); (c.ui as any).nl(); }
  else { await c.ui.clear(); await c.ui.print(offer); }
  if (N.lt(st.I[3], x)) {
    await c.ui.print("You don't have " + N.str_(x) + " sets of clothing.");
    await C.waitKey(c);
    return null;
  }
  await c.ui.print("Will you accept this ");
  await c.ui.print("offer? ");
  if ((await C.yesNo(c)) === "N") return null;
  st.IX = N.parse("5");
  st.I[3] = N.sub(st.I[3], x);
  const word = N.le(st.RD, N.parse("2.4")) ? "ford the river." : "float your wagon across.";
  if (gfx) { await screens(c).riverWindow6(c.ui, false); (c.ui as any).para("The Shoshoni guide will help you " + word); }
  else { await c.ui.clear(); await c.ui.print("The Shoshoni guide will help you " + word); }
  await C.waitKey(c);
  if (N.le(st.RD, N.parse("2.4"))) { c.riverMethod = 2; await ford(c, N.parse("5")); }
  else { c.riverMethod = 3; await floatCrossing(c, N.parse("5")); }
  return true;
}

// ------------------------------------------------------------ the loss routines
/** line 50205: one good lost with `chance`, to a random amount. A draw for each of the six goods, held or not. */
function losses(c: Context, chance: N.Fac, item: number, tag: string): string | null {
  const st = c.st;
  if (c.rng.below(`${tag} item ${item}`, chance) && !N.eq(st.I[item], N.ZERO)) {
    const x = st.I[item];
    const amount = N.int_(N.add(N.mul(c.rng.rnd1(`${tag} amount ${item}`), x), N.ONE));
    st.I[item] = N.sub(x, amount);
    return lf.line(amount, item);
  }
  return null;
}

export function loseGoods(c: Context, chance: N.Fac): string[] {
  const out: string[] = [];
  for (let item = 3; item < 9; item++) {
    const line = losses(c, chance, item, "50205 goods");
    if (line) out.push(line);
  }
  return out;
}
export function loseOxen(c: Context, chance: N.Fac): string[] {
  const st = c.st;
  const x = st.I[2];
  if (N.eq(x, N.ZERO)) return [];
  let lost = 0;
  const n = N.fortCount(1, x);
  for (let i = 0; i < n; i++) if (c.rng.below("50185 ox", chance)) lost += 1;
  if (!lost) return [];
  st.I[2] = N.sub(st.I[2], N.parse(String(lost)));
  if (N.lt(st.I[2], N.ZERO)) st.I[2] = N.ZERO;
  return [`${lost} ox${lost !== 1 ? "en" : ""}`];
}
export function losePeople(c: Context, chance: N.Fac, z = 0): string[] {
  const st = c.st;
  const out: string[] = [];
  const np = N.asInt(st.NP);
  const start = np > 1 ? 1 : 0;
  for (let i = start; i < np; i++) {
    if (c.rng.below(`50175 person ${i}`, chance)) {
      out.push(st.N[i] + " (drowned)");
      st.H1[i] = N.parse("-2");
      z += 1;
      chance = N.store(N.mul(chance, N.bool_(z < 11)));
    }
  }
  return out;
}

/** line 3504: GOSUB 900 -- the crossing's message and loss lines, a wait, and B from the key */
async function showResult(c: Context): Promise<void> {
  const pending = c.riverMessage;
  c.riverMessage = null;
  if (pending) {
    c.keepScreen = c.ui.pictures;       // the box goes over the water
    try { await C.message900(c, pending[0], pending[1]); }
    finally { c.keepScreen = false; }
  }
}

async function buryDrowned(c: Context): Promise<boolean> {
  const st = c.st;
  let any = false;
  for (let i = 0; i < N.asInt(st.NP); i++) if (N.eq(st.H1[i], N.parse("-2"))) any = true;
  if (!any) return false;
  await T.removeDrowned(c);
  return true;
}
