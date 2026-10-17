/** FLIP.LIB: the disk flip at Fort Laramie. There is no disk, so it is the prompt and the re-reading of the graves. */
import type { Context } from "./context.js";
import * as C from "./common.js";

/** FLIP.LIB, side 1: S = 1, prompt, then re-read the two grave records */
export async function toSide2(c: Context): Promise<number> {
  const st = c.st;
  let saved: unknown = null;
  if (c.ui.pictures) saved = await c.ui.screens.flipToSide2(c.ui);
  else await c.ui.print("To continue on your journey to Oregon, please flip the diskette to side 2.");
  await C.waitKey(c);
  if (saved !== null) (c.ui as any).cv.put(saved);       // 50020: & PUT,0,Y5 + 10,49152
  st.S = 1;
  readGraves(c);
  return st.S;
}

/** FLIP.LIB, side 2: ask for side one again, which the top ten needs */
export async function toSide1(c: Context): Promise<number> {
  const st = c.st;
  if (c.ui.pictures) await c.ui.screens.flipToSide1(c.ui);
  else await c.ui.print("Please insert side 1 of the Oregon Trail diskette.");
  await C.waitKey(c);
  st.S = 0;
  readGraves(c);
  return st.S;
}

/** MENU SIDE 2 line 31000: side 1 again if side 2 is in, then the menu */
export async function backToMenu(c: Context): Promise<void> {
  if (c.st.S) await toSide1(c);
  const text = "Getting the Oregon Trail menu...";
  if (c.ui.pictures) await c.ui.screens.gettingMenu(c.ui, text);
  else await c.ui.print(text);
}

/** line 50030 of FLIP.LIB and line 29004 of OREGON TRAIL */
export function readGraves(c: Context): void {
  const st = c.st;
  for (const recNo of [0, 1]) {
    const rec = c.files.readTombs(st.S, recNo);
    st.SN[recNo] = rec ? rec.segment : 0;
    (st.ML as any[])[recNo] = rec ? rec.miles : 0;
  }
}
