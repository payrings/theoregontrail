/** OREGON TRAIL 4000-4900: the action menu, and the eight things it can do. */
import { clockOf } from "./gfx/clock.js";
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";
import * as maplib from "./maplib.js";
import * as pace from "./pace.js";
import * as trade from "./trade.js";
import * as talk from "./talk.js";
import * as fortbuy from "./fortbuy.js";
import * as hunt from "./hunt.js";
import { ALLOWED } from "./ui.js";

const REST_DAY_SECONDS = 0.5;

/** lines 4000-4095: draw the menu, read a choice, do it, and draw it again */
export async function actionMenu(c: Context): Promise<string> {
  const st = c.st;
  st.F9 = 0;
  st.SR = 0 as any;
  if (N.asInt(st.B) === 1) st.B = 0;       // line 4005: B = B * (B <> 1) -- a B of 1 means Return was pressed
  for (;;) {
    await header(c);
    const options: string[] = [];
    for (let i = 0; i < 7; i++) options.push(D.ACTIONS[i]);
    let z = 0;
    const onTrail = !!st.LL;
    // 4040/4050: everything after the THEN belongs to the IF (paper 2.5, rule a)
    if (!onTrail) {
      options.push(D.ACTIONS[7]);                       // Talk to people
      if (D.LM_TYPE[st.LM] === 1) options.push(D.ACTIONS[8]);   // Buy supplies, at a fort
    } else { options.push(D.ACTIONS[9]); z = 2; }       // Hunt for food
    if (c.ui.pictures) await c.ui.screens.actionMenu(c.ui, ...(c.uiHeader as [string, string, string[]]), options);
    else {
      let i = 0;
      for (const label of options) { i += 1; await c.ui.print(`${i}. ${label}`); }
      await c.ui.print();
      await c.ui.print("What is your choice? ");
    }
    // 4060: the allowed set is built at run time -- "19" for nine options, "18" for eight
    const a = (await c.ui.key("-" + "1" + String(options.length), 2, "")) as string;
    const x = /^\d+$/.test(a) ? parseInt(a, 10) : 0;
    if (!st.B && x === 1) {
      st.B = N.eq(st.I[2], N.ZERO) ? 2 : 0;
      if (!st.B) return "CONTINUE";
    }
    if (st.B && x === 1) {
      // line 4070: B = 2 gives "an ox" and B = 5 gives "a wheel"
      st.T[0] = "a ";
      st.T[1] = "an ";
      const art = st.B === 2 ? st.T[1] : st.T[0];
      const what = st.B === 2 ? D.UNIT[0] : D.UNIT[st.B - 2];
      await c.ui.print("You must trade for " + art + what + " to be able to continue.");
      await C.waitKey(c);
      continue;
    }
    // line 4090: Z = Z * (X > 7) + X
    z = x > 7 ? z + x : x;
    const handlers: Record<number, (c: Context) => Promise<unknown>> = {
      2: showSupplies, 3: maplib.show, 4: pace.changePace, 5: pace.changeRations, 6: doRest,
      7: doTrade, 8: talk.talk, 9: fortbuy.fortStore, 10: doHunt,
    };
    const h = handlers[z];
    if (h) await h(c);
    if (st.SD > 0) await T.runStoppedDays(c);
    if (N.asInt(st.NP) <= 0) return "DIED";    // TOMB.LIB 50005: the menu never comes back
    // line 4090 ends IF I(B) THEN I(B) = I(B) - (B > 2): B = 0
    const b = N.asInt(st.B);
    if (b > 0 && !N.eq(st.I[b], N.ZERO)) {
      st.I[b] = N.sub(st.I[b], N.bool_(b > 2));
      st.B = 0;
    }
  }
}

/** lines 4005-4030: the landmark, the date, and the four lines of status */
async function header(c: Context): Promise<void> {
  const st = c.st;
  await c.ui.clear();
  const name = !st.LL ? D.shortName(st.LM) : "";
  if (N.gt(st.H, N.parse("139"))) st.H = N.parse("139");
  if (c.ui.pictures) {
    c.uiHeader = [name, C.dateText(c), [
      "Weather: " + D.WEATHER[N.asInt(st.W)], "Health: " + D.healthWord(st.healthBand()),
      "Pace: " + D.PACE[N.asInt(st.P) - 1], "Rations: " + D.RATIONS[N.asInt(st.R) - 1]]];
    st.A = (st.A + 1) * (st.A < 2 ? 1 : 0);
    return;
  }
  await c.ui.print(name);
  await c.ui.print(C.dateText(c));
  await c.ui.print("Weather: " + D.WEATHER[N.asInt(st.W)]);
  await c.ui.print("Health: " + D.healthWord(st.healthBand()));
  await c.ui.print("Pace: " + D.PACE[N.asInt(st.P) - 1]);
  await c.ui.print("Rations: " + D.RATIONS[N.asInt(st.R) - 1]);
  await c.ui.print();
  // line 4030: the dialogue slot advances by one, wrapping
  st.A = (st.A + 1) * (st.A < 2 ? 1 : 0);
}

/** lines 4100-4110: what is held; each quantity is printed as INT (I(L) + .51) */
async function showSupplies(c: Context): Promise<void> {
  const st = c.st;
  if (c.ui.pictures) {
    const counts: string[] = [];
    for (const i of [2, 3, 4, 5, 6, 7, 8]) counts.push(N.str_(N.parse(String(N.asInt(N.int_(N.add(st.I[i], N.parse(".51"))))))));
    await c.ui.screens.supplies(c.ui, counts, C.money(c, st.MY));
    await C.waitKey(c);
    return;
  }
  await c.ui.clear();
  await c.ui.print("  Your Supplies");
  for (let item = 2; item < 9; item++) {
    const held = N.int_(N.add(st.I[item], N.parse(".51")));
    await c.ui.print(D.I_NAMES[item].padEnd(24) + N.str_(N.parse(String(N.asInt(held)))).padStart(6));
  }
  await c.ui.print("money left".padEnd(24) + ("$" + C.money(c, st.MY)).padStart(6));
  await C.waitKey(c);
}

/** lines 4500-4510: one to nine days, with no travel and no pace penalty */
async function doRest(c: Context): Promise<number> {
  const st = c.st;
  if (c.ui.pictures) await c.ui.screens.box41000(c.ui, "How many days would you like to rest? ", 40, 60, 240, 88);
  else await c.ui.print("How many days would you like to rest? ");
  const a = (await c.ui.key(ALLOWED.REST, 1, "1")) as string;
  st.SD = /^\d+$/.test(a) ? parseInt(a, 10) : 1;
  if (st.SD) {
    // Line 4505 sets D = 0 and calls line 3100 directly, SD times -- not through the day loop.
    const savedD = st.D, savedM = st.M, savedP = st.P;
    st.F9 = 0;
    st.D = N.ZERO;
    st.P = N.ZERO;
    const live = c.ui.pictures && c.ui.dailyPause > 0;
    const clock = clockOf(c.ui);
    for (let i = 0; i < st.SD; i++) {
      const began = clock.now();
      if (!(await T.dayBody(c))) break;        // the last member died while resting
      // 4505: GOSUB 250: & CO,,X5: PRINT CE$ TD$ CC$ -- the new date replaces the one on the second line
      if (c.ui.pictures) {
        const u = c.ui as any;
        u.window(0, 0, 280, 192);
        u.cv.clearText(0, 9, 279, 16);
        u.co(0, 9);
        u.line(C.dateText(c), true, true);
      } else await c.ui.print(C.dateText(c));
      if (live) {                // a person is watching: each day lasts at least half a second
        (c.ui as any).refresh?.();
        while (clock.now() - began < REST_DAY_SECONDS) {
          await (c.ui as any).pump?.();
          await clock.sleep(0.05);
        }
      }
    }
    st.SD = 0;
    st.D = savedD; st.M = savedM; st.P = savedP;
    st.I[8] = st.PF;
  }
  return st.SD;
}

/** line 4900 and TRADE.LIB: a trade attempt always costs a day */
async function doTrade(c: Context): Promise<void> {
  const st = c.st;
  await trade.attempt(c);
  st.SD = 1;
  if (N.lt(st.I[2], N.ZERO)) st.I[2] = N.ZERO;
}

/** lines 4600 and HUNT.LIB: a hunt costs a day */
async function doHunt(c: Context): Promise<void> {
  await hunt.go(c);
  c.st.SD = 1;
}
