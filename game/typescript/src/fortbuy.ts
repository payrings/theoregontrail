/** BUY.LIB: buying at a fort (50000-50035). Each good rises by a quarter for every step along the trail. */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import { ALLOWED } from "./ui.js";

const TIER_CUTS = [2, 4, 7, 10, 12, 13];

/** line 50003: how far along the trail this fort is */
export function tier(landmark: number): number { return TIER_CUTS.filter((cut) => landmark > cut).length; }

/** line 50025: V = VAL(S$(L-1,1)): V = V + .25 * Q * V (both stored) */
export function price(item: number, q: number): N.Fac {
  const base = N.store(N.parse(D.PRICE_TEXT[item]));
  return N.store(N.add(base, N.mul(N.mul(N.parse(".25"), N.parse(String(q))), base)));
}

export async function fortStore(c: Context): Promise<void> {
  const st = c.st;
  st.Q = N.parse(String(tier(st.LM)));          // line 50003: the scalar Q (not the map's Q())
  const q = N.asInt(st.Q);
  const pictures = c.ui.pictures;
  if (!pictures) await c.ui.clear();
  if (!pictures) {
    await c.ui.print(D.LM_NAMES[st.LM]);
    await c.ui.print(C.dateText(c));
    await c.ui.print();
    await c.ui.print("You may buy:");
    await c.ui.print();
    for (let i = 0; i < 7; i++) await c.ui.print(`  ${i + 1}. ${D.GOODS_NAME[i]}`);
    await c.ui.print("  8. Leave store");
    await c.ui.print();
    for (let i = 0; i < 7; i++) {
      const p = price(i, q);
      await c.ui.print((" " + C.money(c, p)).slice(-5) + " per " + D.UNIT[i]);
    }
  }
  let first = true;
  for (;;) {
    if (pictures) {
      const S = c.ui.screens;
      if (first) {
        const goods = [0, 1, 2, 3, 4, 5, 6].map((i) => [D.GOODS_NAME[i], C.money(c, price(i, q)), D.UNIT[i]]);
        await S.fortList(c.ui, D.LM_NAMES[st.LM], C.dateText(c), goods, C.money(c, st.MY));
        first = false;
      } else await ask(c);
    } else {
      await c.ui.clear();
      await c.ui.print(`You have ${C.dollarText(c, st.MY)} to spend.`);
      await c.ui.print("Which number? ");
    }
    const a = (await c.ui.key(ALLOWED.FORT, 1, "8")) as string;       // 50010: & INP,1,"-18"
    const item = (/^\d+$/.test(a) ? parseInt(a, 10) : 8) - 1;
    if (item === 7) { st.PF = st.I[8]; return; }
    const p = price(item, q);
    if (!(await affordable(c, item, 1, p, ""))) continue;     // line 50015: is one affordable?
    await c.ui.print("How many " + D.UNIT[item] + D.GOODS_PLURAL[item] + "? ");
    const want = (await c.ui.key(item === 3 || item === 4 || item === 5 ? ALLOWED.STORE_PART : ALLOWED.STORE_FOOD,
      3 + (item === 6 ? 1 : 0), "1")) as string;
    const n = /^\d+$/.test(want) ? parseInt(want, 10) : 0;
    if (!(await affordable(c, item, n, p, " many"))) continue;
    purchase(c, item, n, p);
    // Line 50025 ends GOTO 50010 and BUY.LIB has no GOSUB 650, so the speed is not worked out again here.
  }
}

/** the prompt window under the list, drawn again for each purchase */
async function ask(c: Context): Promise<void> {
  const ui = c.ui;
  const y = (ui as any).promptY ?? 150;
  const g = ui as any;
  g.box(0, y, 279, 191, 0);
  g.dfw(0, y, 279, 191 - y);
  g.co(0, 0);
  await ui.print(`You have ${C.dollarText(c, c.st.MY)} to spend.`);
  await ui.print("Which number? ");
}

/** line 50025: MY = MY - Z * V: I(L + 1) = I(L + 1) + Z * K (K is 20 for ammunition) */
export function purchase(c: Context, item: number, n: number, p: N.Fac): void {
  const st = c.st;
  const k = item === 2 ? 20 : 1;
  st.MY = N.sub(st.MY, N.mul(N.parse(String(n)), p));
  st.I[item + 2] = N.add(st.I[item + 2], N.parse(String(n * k)));
}

/** line 50026: T = 0: IF (Z * V) > MY + .001 THEN T = 1 */
function tooDear(c: Context, n: number, p: N.Fac): boolean {
  const cost = N.mul(N.parse(String(n)), p);
  return N.gt(cost, N.add(c.st.MY, N.parse(".001")));
}

/** lines 50030-50033: the four refusals */
async function affordable(c: Context, item: number, n: number, p: N.Fac, many: string): Promise<boolean> {
  const st = c.st;
  if (tooDear(c, n, p)) {
    await c.ui.print("You cannot afford that" + many + ".");
    await C.waitKey(c);
    return false;
  }
  const held = st.I[item + 2];
  if (item === 0 && N.gt(N.add(held, N.parse(String(n))), N.parse("20"))) {
    await c.ui.print("You may only take 20 oxen.");
    await C.waitKey(c);
    return false;
  }
  if (item === 6 && N.gt(N.add(held, N.parse(String(n))), N.parse("2000"))) {
    await c.ui.print("Your wagon may only carry 2000 pounds of food.");
    await C.waitKey(c);
    return false;
  }
  if ((item === 3 || item === 4 || item === 5) && N.gt(N.add(held, N.parse(String(n))), N.parse("3"))) {
    await c.ui.print(`Your wagon may only carry 3 ${D.I_NAMES[item + 2]}.`);
    await C.waitKey(c);
    return false;
  }
  return true;
}
