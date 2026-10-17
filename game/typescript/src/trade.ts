/** TRADE.LIB: meeting another emigrant (50000-50260). An attempt always costs a day, which the caller sets. */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";
import * as lf from "./lf.js";

/** line 50011: ZX = VAL(S$(X,1)) / (1 + 19 * (X = 2)), stored */
export function unitValue(item: number): N.Fac {
  return N.store(N.div(N.parse(D.PRICE_TEXT[item]), N.add(N.ONE, N.mul(N.parse("19"), N.bool_(item === 2)))));
}
function overLimit(st: Context["st"], item: number, amount: N.Fac): boolean {
  const held = N.add(st.I[item + 2], amount);
  if (item === 3 || item === 4 || item === 5) return N.gt(held, N.parse("3"));
  if (item === 6) return N.gt(held, N.parse("2000"));
  if (item === 0) return N.gt(held, N.parse("20"));
  return false;
}

/** line 50050: the inventory, each line rounded to the nearest whole */
export async function showSupplies(c: Context): Promise<void> {
  const st = c.st;
  for (let item = 2; item < 9; item++) {
    const held = N.int_(N.add(st.I[item], N.HALF));
    await c.ui.print(D.I_NAMES[item].padEnd(24) + N.str_(N.parse(String(N.asInt(held)))).padStart(6));
  }
}

/** the graphical Your Supplies page with the trader's words along the bottom */
async function screen(c: Context, text: string, offer: string | null = null): Promise<void> {
  const st = c.st;
  const counts: string[] = [];
  for (let i = 2; i < 9; i++) counts.push(N.str_(N.parse(String(N.asInt(N.int_(N.add(st.I[i], N.HALF)))))));
  await c.ui.screens.supplies(c.ui, counts, "", { tradeText: text, offer });
}

/** lines 50000-50040 */
export async function attempt(c: Context): Promise<boolean> {
  const st = c.st;
  const pic = c.ui.pictures;
  if (!pic) {
    await c.ui.clear();
    await c.ui.print("Your Supplies");
    await showSupplies(c);
  }
  const x = c.rng.intRange("50010 good wanted", 7);
  let y = c.rng.intRange("50010 good offered", 7);
  if (y === x) y = (y + 1) % 7;
  const zx = unitValue(x), zy = unitValue(y);
  const z = N.store(N.div(zx, N.mul(zy, N.add(N.ONE, N.mul(N.parse("1.2"), c.rng.rnd1("50011 exchange ratio"))))));
  st.Q = N.int_(N.add(st.I[x + 2], N.parse(".5")));
  let v = N.ONE;
  let f = N.int_(z);
  if (N.lt(z, N.ONE)) { v = N.int_(N.div(N.ONE, z)); f = N.ONE; }
  if ((x === 2 && y === 6) || (y === 2 && x === 6)) { v = N.mul(v, N.parse("50")); f = N.mul(f, N.parse("50")); }
  // line 50027: one draw, and no short-circuit, so the draw is spent whether or not the limit is exceeded
  const over = overLimit(st, y, f);
  const refuse = N.gt(c.rng.rnd1("50027 refusal test"), N.parse(".95")) || over;
  if (refuse) {
    if (pic) await screen(c, "No one wants to trade with you today.");
    else { await c.ui.print("No one wants to"); await c.ui.print("trade with you today."); }
    await C.waitKey(c);
    return false;
  }
  const q = st.Q, want = v, give = f;
  const meet = `You meet another emigrant who wants ${N.str_(want)} ${lf.wording(x + 2, N.asInt(want))}.  `;
  if (!pic) await c.ui.print(meet);
  if (N.lt(q, want)) {
    if (pic) await screen(c, meet + "You don't have this.");
    else await c.ui.print("You don't have this.");
    await C.waitKey(c);
    return false;
  }
  const who = N.gt(c.rng.rnd1("50031 he or she"), N.parse(".67")) ? "She" : "He";
  const offered = lf.line(give, y + 2);
  if (pic) await screen(c, meet + `${who} will trade you ${offered}.`, "Are you willing to trade? ");
  else { await c.ui.print(`${who} will trade you ${offered}.`); await c.ui.print("Are you willing to trade? "); }
  if ((await C.yesNo(c)) !== "Y") { st.PF = st.I[8]; return false; }
  st.I[y + 2] = N.add(st.I[y + 2], give);
  st.I[x + 2] = N.sub(q, want);
  if (pic) { await screen(c, ""); await C.waitKey(c); }
  else await showSupplies(c);
  T.speed(c);
  st.PF = st.I[8];
  return true;
}
