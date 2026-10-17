/** PACE.LIB and RATION.LIB: how hard the party travels, and how much it eats (50000-50070). */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";

export const PACE_DESCRIPTIONS = [
  "You travel about 8 hours a day, taking frequent rests.  You take care not to get too tired.",
  "You travel about 12 hours a day, starting just after sunrise and stopping shortly before sunset.  You stop to rest only when necessary.  You finish each day feeling very tired.",
  "You travel about 16 hours a day, starting before sunrise and continuing until dark.  You almost never stop to rest.  You do not get enough sleep at night.  You finish each day feeling absolutely exhausted, and your health suffers.",
];
export const RATION_DESCRIPTIONS = [
  "meals are large and generous.",
  "meals are small, but adequate.",
  "meals are very small; everyone stays hungry.",
];

/** lines 50000-50030 */
export async function changePace(c: Context): Promise<number> {
  const st = c.st;
  for (;;) {
    if (c.ui.pictures) {
      await c.ui.screens.paceMenu(c.ui, D.PACE[N.asInt(st.P) - 1], D.PACE);
      const a = (await c.ui.key("-14", 1, "")) as string;
      if (a === "4") { await describePace(c); continue; }
      if (a) st.P = N.parse(a);
      T.speed(c);
      return N.asInt(st.P);
    }
    await c.ui.clear();
    await c.ui.print("Change pace");
    await c.ui.print(`(currently "${D.PACE[N.asInt(st.P) - 1]}")`);
    await c.ui.print();
    await c.ui.print("The pace at which you travel");
    await c.ui.print("can change.  Your choices are:");
    await c.ui.print();
    for (let i = 1; i <= 3; i++) await c.ui.print(`${i}. a ${D.PACE[i - 1]} pace`);
    await c.ui.print("4. find out what these different paces mean");
    await c.ui.print();
    await c.ui.print("What is your choice? ");
    const a = (await c.ui.key("-14", 1, "")) as string;
    if (a === "4") { await describePace(c); continue; }
    // 50030: a digit was entered, so this is VAL(A$); with nothing typed P survives. GOSUB 650 runs either way.
    if (a) st.P = N.parse(a);
    T.speed(c);
    return N.asInt(st.P);
  }
}

/** lines 50040-50070 */
async function describePace(c: Context): Promise<void> {
  await c.ui.clear();
  for (let i = 0; i < 3; i++) {
    await c.ui.print(D.PACE[i] + " - " + PACE_DESCRIPTIONS[i]);
    await c.ui.print();
  }
  await C.waitKey(c);
}

/** lines 50000-50040 of RATION.LIB */
export async function changeRations(c: Context): Promise<number> {
  const st = c.st;
  if (c.ui.pictures) {
    await c.ui.screens.rationMenu(c.ui, D.RATIONS[N.asInt(st.R) - 1], D.RATIONS, RATION_DESCRIPTIONS);
    const a = (await c.ui.key("-13", 1, "")) as string;
    if (a) st.R = N.parse(a);
    T.speed(c);
    return N.asInt(st.R);
  }
  await c.ui.clear();
  await c.ui.print("Change food rations");
  await c.ui.print(`(currently "${D.RATIONS[N.asInt(st.R) - 1]}")`);
  await c.ui.print();
  await c.ui.print("The amount of food the people in your party eat each day can change.  These amounts are:");
  await c.ui.print();
  for (let i = 1; i <= 3; i++) await c.ui.print(`${i}. ${D.RATIONS[i - 1]} - ${RATION_DESCRIPTIONS[i - 1]}`);
  await c.ui.print();
  await c.ui.print("What is your choice? ");
  const a = (await c.ui.key("-13", 1, "")) as string;
  if (a) st.R = N.parse(a);
  T.speed(c);
  return N.asInt(st.R);
}
