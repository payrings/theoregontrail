/** OREGON TRAIL 10300 and TOMB.LIB 50000: falling ill and dying. */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";
import * as tomb from "./tomb.js";

/** lines 11500-11505: pick the member who falls ill or dies (the leader cannot while others live) */
export function chooseVictim(c: Context, tag = "11500 victim"): number {
  const np = N.asInt(c.st.NP);
  if (np <= 0) return 0;
  let z = N.trunc(N.mul(c.rng.rnd1(tag), N.parse(String(np))));
  z = z < np - 1 ? z + 1 : 0;
  while (z < 0) z = 0;
  if (np > 1 && z === 0) z = 1;
  return z;
}

/** line 10300: a disease, and what it does to whoever draws it */
export async function illness(c: Context): Promise<void> {
  const st = c.st;
  st.HR = N.parse("20");
  // V = INT (RND (1) * 6) + 3 -- the INT is taken first and 3 is added to it
  const disease = N.trunc(N.add(N.int_(N.mul(c.rng.rnd1("10300 disease"), N.parse("6"))), N.parse("3")));
  const who = chooseVictim(c);
  const name = st.N[who];
  if (!N.eq(st.H1[who], N.ZERO)) {
    await C.message710(c, name + " has " + D.DEATH_SENTENCE + ".", 20);
    st.H1[who] = N.parse("-1");
    await die(c, who);
    return;
  }
  await C.message710(c, name + " has " + D.IL_NAMES[disease] + ".", 20);
  st.H1[who] = N.parse(String(disease));
  st.H2[who] = N.parse("10");
}

/** line 8000 and TOMB.LIB 50000-50005: the death. Returns "DIED" when nobody is left. */
export async function die(c: Context, who: number, speed = true): Promise<string | null> {
  const st = c.st;
  if (N.gt(st.H, N.parse("105"))) st.H = N.parse("105");
  const np = N.asInt(st.NP);
  if (np <= 0) return null;
  const after = np - 1;
  st.H1[who] = st.H1[after];
  st.H1[after] = N.parse("-1");
  st.H2[who] = st.H2[after];
  [st.N[who], st.N[after]] = [st.N[after], st.N[who]];
  st.NP = after;
  if (after <= 0) { await tomb.allDead(c, who); return "DIED"; }
  if (speed) T.speed(c);
  return "died";
}
