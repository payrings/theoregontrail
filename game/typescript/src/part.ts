/** PART.LIB: the broken wagon part (42000-42100). The part is 5, 6 or 7; the repair succeeds half the time. */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";
import { RETURN_KEYS } from "./ui.js";

/** line 42100: GOSUB 400: GOSUB 30000: B = (PEEK (-16384) = 13) */
async function clearB(c: Context): Promise<void> {
  const key = await C.waitKey(c);
  c.st.B = RETURN_KEYS.includes(key) ? 1 : 0;
}

export async function brokenPart(c: Context): Promise<string> {
  const st = c.st;
  const item = N.asInt(st.B);
  const part = D.UNIT[item - 2];
  const gfx = c.ui.pictures;
  const S = c.ui.screens;
  if (gfx) {
    await T.scene(c, { prompt: false, pictures: [["part_04", 185, 29]] });     // 42000: & IMAGE,4,185,29
    await S.partBox(c.ui, `Broken wagon ${part}.  Would you like to try to repair it? `);
  } else await c.ui.print(`Broken wagon ${part}.  Would you like to try to repair it? `);
  const yes = (await C.yesNo(c)) === "Y";
  // the draw is made either way: Applesoft evaluates both sides of the AND
  const roll = c.rng.below("42010 repair succeeds", N.HALF);
  const say = async (text: string) => { if (gfx) await S.partText(c.ui, text); else await c.ui.print(text); };
  if (yes && roll) {
    await say(`You were able to repair the wagon ${part}.`);
    await clearB(c);
    return "repaired";
  }
  const said = "You " + (yes ? "were unable to" : "did not") + ` repair the broken wagon ${part}.`;
  const held = st.I[item];
  if (!held.isZero()) {
    st.I[item] = N.sub(held, N.ONE);
    await say(said + "  You must replace it with a spare part.");
    await clearB(c);
    return "replaced";
  }
  await say(said + "  You must replace it with a spare part.");
  await C.waitKey(c);
  await say(`Since you don't have a spare ${part}, you must trade for one.`);
  await C.waitKey(c);
  return "none";
}
