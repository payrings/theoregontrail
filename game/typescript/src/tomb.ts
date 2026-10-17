/** TOMB.LIB: the gravestones (50000 to 51030). */
import * as N from "./num.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";
import { ALLOWED } from "./ui.js";

const sound = (c: Context): any => (c.ui as any).sound;

/** lines 50010-50040: the stone, the epitaph and the record */
export async function allDead(c: Context, who: number): Promise<string> {
  const st = c.st;
  const gfx = c.ui.pictures;
  const S = c.ui.screens;
  sound(c)?.select?.("ts");                    // 50010: & RFL, "TS.BIN" AT 51944
  if (gfx) {
    await S.tombstone(c.ui, st.N[who]);
    await S.tombBar(c.ui);                     // 50010 ends GOSUB 950
    await S.tombWindow(c.ui);
  } else {
    await c.ui.clear();
    await c.ui.print("Here lies");
    await c.ui.print(st.N[who]);
    await c.ui.print();
    await C.waitKey(c);                        // 50010 ends GOSUB 950
  }
  const say = async (...lines: string[]) => {
    if (gfx) await S.tombWindow(c.ui);
    for (const l of lines) await c.ui.print(l);
  };
  await say("Would you like to write", "an epitaph? ");
  let epitaph = "";
  if ((await C.yesNo(c)) === "Y") {
    for (;;) {
      await say("What would you like on the tombstone? ");           // 50020
      epitaph = (await c.ui.key(ALLOWED.EPITAPH, 29, "")) as string;
      if (!epitaph) break;                     // 50030: IF LEN (A$) THEN ...
      if (gfx) await S.tombstone(c.ui, st.N[who], epitaph);
      else await c.ui.print(epitaph);
      await say("Would you like to make", "changes? ");
      if ((await C.yesNo(c)) === "N") break;
    }
  }
  writeRecord(c, who, epitaph);
  if (gfx) {
    await S.tombWindow(c.ui);
    (c.ui as any).line("All of the people", true, true);
    (c.ui as any).line("in your party have died.", true, true);
    await S.tombBar(c.ui);
  } else {
    await c.ui.clear();
    await c.ui.print("All of the people");
    await c.ui.print("in your party have died.");
    await C.waitKey(c);
  }
  c.outcome = "DIED";
  return "MENU";
}

/** line 50035: the four fields, at offset 0 of the current side */
export function writeRecord(c: Context, who: number, epitaph: string): void {
  const st = c.st;
  const segment = N.asInt(st.NM) * 100 + st.LM;
  // STR$ (D): the text the ROM builds, nine significant digits
  c.files.writeTomb(st.S, segment, N.str_(st.D), st.N[who], epitaph);
}

/** lines 50100-50105: read and show the stone the party has reached */
export async function readGrave(c: Context): Promise<void> {
  const st = c.st;
  const rec = c.files.readTombs(st.S, st.LN);        // 50100: & TPTR,LN * 49
  if (!rec) { T.findGrave(c); return; }
  if (c.ui.pictures) {
    await c.ui.screens.tombstone(c.ui, rec.name, rec.epitaph);
    await c.ui.waitKey();                            // 50105 ends GOSUB 41100
  } else {
    await c.ui.clear();
    await c.ui.print("Here lies");
    await c.ui.print(rec.name);
    await c.ui.print();
    await c.ui.print(rec.epitaph);
    await C.waitKey(c);
  }
  T.findGrave(c);
}
