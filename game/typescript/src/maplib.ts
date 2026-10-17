/** MAP.LIB: the route travelled (50000-50015). */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";

/** MP%(landmark, 0 to 1): the x and y of each landmark on the map */
export const COORDINATES: Record<number, [number, number]> = {
  0: [245, 139], 1: [235, 136], 2: [226, 126], 3: [207, 122], 4: [185, 120], 5: [170, 114], 6: [155, 100],
  7: [143, 108], 8: [132, 117], 9: [134, 108], 10: [124, 104], 11: [110, 101], 12: [93, 102], 13: [80, 87],
  14: [70, 76], 15: [69, 66], 16: [55, 71], 17: [45, 70],
};

export async function show(c: Context): Promise<number[]> {
  const st = c.st;
  const pictures = c.ui.pictures;
  if (pictures) {
    const hist: number[] = [];
    for (let i = 0; i < Math.max(0, Math.min(st.Q1, 17)); i++) hist.push(N.asInt(st.Q_arr[i]));
    await c.ui.screens.mapScreen(c.ui, hist, [st.LM, st.NM, N.asFloat(st.D), N.asFloat(st.DD)]);
  } else {
    await c.ui.clear();
    await c.ui.print("The Oregon Trail");
    await c.ui.print();
  }
  const visited: number[] = [];
  const upto = Math.max(1, Math.min(st.Q1 - 1, 17));
  for (let i = 0; i < upto; i++) {
    const n = N.asInt(st.Q_arr[i]);
    if (n && n >= 0 && n < 18 && !visited.includes(n)) visited.push(n);
  }
  if (!visited.includes(st.LM)) visited.push(st.LM);
  if (!pictures) {
    await c.ui.print("You have been through:");
    for (const n of visited) await c.ui.print("  " + D.LM_NAMES[n]);
    await c.ui.print();
    await c.ui.print(`Next landmark: ${D.LM_NAMES[st.NM]}`);
    await c.ui.print(`Miles to it:  ${N.str_(st.D)}`);
    await c.ui.print(`Miles travelled so far: ${N.str_(st.M)}`);
  }
  await C.waitKey(c);
  return visited;
}
