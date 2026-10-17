/** COMMON.LIB: the helpers every program shares (money and date strings, the wait for a key, messages, the disk side). */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import { RETURN_KEYS } from "./ui.js";

/** lines 200 / 250: V as dollars and cents */
export function money(_c: Context, v: N.Fac): string {
  const cents = N.trunc(N.add(N.mul(v, N.parse("100")), N.parse(".5")));
  return N.dollar(cents);
}
export const dollarText = (c: Context, v: N.Fac): string => "$" + money(c, v);
/** line 250 */
export function dateText(c: Context): string {
  const st = c.st;
  return `${D.MONTHS[N.asInt(st.AM) - 1]} ${N.str_(st.AD)}, ${N.str_(st.AY)}`;
}
export const waitKey = async (c: Context, prompt = "Press SPACE BAR to continue"): Promise<string> =>
  (await c.ui.waitKey("", prompt)) as string;
export const yesNo = async (c: Context, prompt = ""): Promise<string> => (await c.ui.yesNo(prompt)) as string;

/**
 * Lines 700 and 900: the framed box a message is printed in, then (optionally) a key. The graphical build
 * draws the box over the travel scene (trail.eventBox); the text build prints the lines.
 */
export async function message(c: Context, text: string, lines: string[] = [], wait = true, kind = 900, g = 0): Promise<string | null> {
  if (c.ui.pictures) {
    const trail = await import("./trail.js");
    await trail.eventBox(c, text, lines, kind, g);
    return wait ? (await c.ui.waitKey()) as string : null;
  }
  await c.ui.print(text);
  for (const t of lines) if (t) await c.ui.print("   " + t);
  return wait ? await waitKey(c) : null;
}

/** line 700: the message and nothing more */
export async function message700(c: Context, text: string): Promise<void> { await message(c, text, [], false, 700); }

/** lines 700-710: the message, a wait, and B from the key that ended it */
export async function message710(c: Context, text: string, g = 0): Promise<string | null> {
  const key = await message(c, text, [], true, 700, g);
  const st = c.st;
  if (!st.B) st.B = key !== null && RETURN_KEYS.includes(key) && !st.SD ? 1 : 0;
  return key;
}
/** lines 900-905: the message with its loss lines, a wait, then B = (key was Return) */
export async function message900(c: Context, text: string, lines: string[] = []): Promise<string | null> {
  const key = await message(c, text, lines);
  c.st.B = key !== null && RETURN_KEYS.includes(key) ? 1 : 0;
  return key;
}

export { RETURN_KEYS };

/** COMMON.LIB 33000: make sure the disk side the game expects is in */
export async function checkSide(c: Context, want: number): Promise<number> {
  want = want === 1 || want === 2 ? want : c.st.S + 1;
  if (want - 1 === c.st.S) return c.st.S;
  const got = (await c.ui.flipDisk(want, "OREGON TRAIL")) as string;
  c.st.S = /^\s*\d+\s*$/.test(String(got)) ? parseInt(String(got), 10) - 1 : c.st.S;
  return c.st.S;
}

/** COMMON.LIB 32120: the error message, a key, and back to the menu */
export async function errorHandler(c: Context, err: N.ApplesoftError): Promise<string> {
  await c.ui.clear();
  await c.ui.print(`Error ${err.code} at line #${err.line} in ${c.program}.`);
  await c.ui.print();
  await c.ui.print("Please report this error to MECC.");
  await c.ui.waitKey();
  return "MENU";
}
