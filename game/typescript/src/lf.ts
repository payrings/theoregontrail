/** LF.LIB: fire, the abandoned wagon and the thief; and the wording of a loss line (50250-50260). */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";

/** I$ index 2 to 8; n is F, the quantity. A plural keeps the name as it stands; only the singular is rewritten. */
export function wording(item: number, n: number): string {
  const name = D.I_NAMES[item];
  if (n === 1) {
    if (item === 8) return "pound of food";
    if (item === 3) return "set of clothing";
    if (item === 2) return "ox";
    return name.endsWith("s") ? name.slice(0, -1) : name;
  }
  return name;
}
export const line = (amount: N.Fac, item: number): string => `${N.asInt(amount)} ${wording(item, N.asInt(amount))}`;

/** line 50000: a fire in the wagon */
export function fire(c: Context): string[] {
  const st = c.st;
  const losses: string[] = [];
  let z = 0;
  for (let item = 3; item < 8; item++) {
    const held = st.I[item];
    // no short-circuit: the draw happens even when nothing is held
    if (c.rng.below(`50000 fire item ${item}`, N.HALF) && !held.isZero()) {
      const x = N.int_(N.add(N.mul(c.rng.rnd1(`50000 fire amount ${item}`), held), N.ONE));
      st.I[item] = N.sub(held, x);
      losses.push(line(x, item));
      st.T[z] = losses[losses.length - 1];
      z += 1;
    }
  }
  const held = st.PF;
  if (c.rng.below("50010 fire food", N.HALF) && !held.isZero()) {
    const x = N.int_(N.add(N.mul(c.rng.rnd1("50010 fire food amount"), held), N.ONE));
    st.PF = N.sub(held, x);
    st.I[8] = st.PF;
    losses.push(line(x, 8));
    st.T[z] = losses[losses.length - 1];
    z += 1;
  }
  return losses;
}

/** line 51000: an abandoned wagon */
export function abandonedWagon(c: Context): string[] {
  const st = c.st;
  const found: string[] = [];
  let z = 0;
  for (let item = 3; item < 8; item++) {
    if (!c.rng.below(`51010 found item ${item}`, N.HALF)) continue;
    let x = N.int_(N.add(N.mul(c.rng.rnd1(`51010 amount ${item}`), N.parse("3")), N.ONE));
    if (item === 4) x = N.add(x, N.mul(N.mul(x, N.ONE), N.parse("20")));
    if (item >= 5 && !N.lt(N.add(st.I[item], x), N.parse("4"))) continue;
    st.I[item] = N.add(st.I[item], x);
    found.push(line(x, item));
    st.T[z] = found[found.length - 1];
    z += 1;
  }
  return found;
}

/** line 52000: a thief in the night (never takes money). Returns the sentence in a list, or nothing. */
export function thief(c: Context): string[] {
  const st = c.st;
  st.I[8] = st.PF;
  let z = 0;
  let item = c.rng.intSpan("52000 which item", 2, 5);
  if (item === 5) item = 8;
  const held = st.I[item];
  if (!held.isZero()) {
    const most = N.store(N.add(N.mul(N.parse("100"), N.bool_(N.gt(held, N.parse("100")))),
      N.mul(held, N.bool_(N.lt(held, N.parse("101"))))));
    const x = N.int_(N.add(N.mul(c.rng.rnd1("52010 amount"), most), N.ONE));
    st.I[item] = N.sub(held, x);
    if (item === 8) st.PF = N.sub(st.PF, x);
    st.T[z] = line(x, item);
    z += 1;
    if (N.lt(st.I[item], N.ZERO)) st.I[item] = N.ZERO;
  }
  const shown = z ? ["A thief comes during the night and steals " + st.T[0] + "."] : [];
  st.T[0] = "";
  return shown;
}
