/** END.LIB: The Dalles, and the hand-over to WIN (50000 to 50080). */
import * as N from "./num.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";
import * as floatraft from "./floatraft.js";
import { ALLOWED } from "./ui.js";

export const TOLL_BASE = 5;

/** lines 50015, 50020 and 50060: V = INT (V * 100 + .5) / 100 */
export function roundToCents(v: N.Fac): N.Fac {
  return N.store(N.div(N.int_(N.add(N.mul(v, N.parse("100")), N.parse(".5"))), N.parse("100")));
}
/** line 50020: V = 5 + INT (I(2) + .5) * .5, then rounded to cents */
export function barlowToll(st: Context["st"]): N.Fac {
  const toll = N.store(N.add(N.parse(String(TOLL_BASE)), N.mul(N.int_(N.add(st.I[2], N.parse(".5"))), N.parse(".5"))));
  return roundToCents(toll);
}

/** lines 50000-50040: the choice, and the toll */
export async function theDalles(c: Context): Promise<string> {
  const st = c.st;
  const gfx = c.ui.pictures;
  let first = true;
  for (;;) {
    if (gfx) { await c.ui.screens.dallesMenu(c.ui, first); first = false; }
    else {
      await c.ui.clear();
      await c.ui.print("The trail divides here.");
      await c.ui.print("You may:");
      await c.ui.print();
      await c.ui.print("1. float down the Columbia River");
      await c.ui.print();
      await c.ui.print("2. take the Barlow Toll Road");
      await c.ui.print();
      await c.ui.print("What is your choice? ");
    }
    const a = (await c.ui.key(ALLOWED.DALLES, 1, "2")) as string;
    if (a === "1") {
      writeHandover(c);
      await floatraft.run(c);
      if (N.asInt(st.NP) <= 0) return "DIED";     // the raft was lost with everyone on it
      return "FLOAT";
    }
    st.MY = roundToCents(st.MY);                  // line 50015
    const toll = barlowToll(st);
    const pay = "You must pay $" + C.money(c, toll) + " to travel the Barlow road.  Are you willing to do this? ";
    if (gfx) await c.ui.screens.dallesToll(c.ui, pay);
    else { await c.ui.clear(); await c.ui.print(pay); }
    const answer = await C.yesNo(c);
    if (answer === "Y" && N.gt(st.MY, toll)) {
      st.MY = N.sub(st.MY, toll);
      st.LM = 16; st.LL = 1;
      await T.loadSegment(c, 18);
      T.startSegment(c);
      await T.travelScreen(c);
      await T.dailyCycle(c);
      if (N.asInt(st.NP) <= 0) return "DIED";
      st.LM = 17;
      writeHandover(c);
      return "WIN";
    }
    // 50030: the message appears only when the player wanted the road and cannot afford it
    if (answer === "Y" && N.lt(st.MY, toll)) {
      await c.ui.print();
      await c.ui.print("You do not have enough cash.");
      await C.waitKey(c);
    }
  }
}

/** lines 50050-50070: the end-of-journey memory layout */
export function writeHandover(c: Context): void {
  const st = c.st, mem = c.mem;
  mem.poke(900, N.asInt(st.NP), 50050);
  mem.poke(901, N.asInt(st.AY) - 1800, 50050);
  mem.poke(902, N.asInt(st.AM), 50050);
  mem.poke(903, N.asInt(st.AD), 50050);
  mem.poke(909, N.trunc(N.add(st.I[2], N.parse(".5"))), 50050);
  mem.pokeWord(906, N.trunc(st.I[8]), 50050);
  mem.poke(908, N.trunc(st.I[3]), 50050);
  mem.pokeWord(904, N.trunc(st.I[4]), 50050);
  mem.poke(916, st.healthBand(), 50050);
  mem.putNames(st.N.slice(0, N.asInt(st.NP)), 50060);
  st.MY = roundToCents(st.MY);
  for (const item of [5, 6, 7]) mem.poke(905 + item, N.trunc(st.I[item]), 50070);
  mem.pokeWord(913, N.trunc(st.MY), 50070);
  const cents = N.add(N.mul(N.sub(st.MY, N.int_(st.MY)), N.parse("100")), N.parse(".5"));
  mem.poke(917, N.trunc(cents), 50070);
}
