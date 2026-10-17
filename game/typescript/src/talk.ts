/** TALK.LIB: the three people at each landmark (50000-50010). */
import * as N from "./num.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as dialogue from "./dialogue.js";

export async function talk(c: Context): Promise<[string, string]> {
  const st = c.st;
  const d = dialogue.load();
  const slot = N.asInt(st.A) % 3;
  const speaker = d.speaker(st.LM, slot);
  const text = d.text(st.LM, slot);
  if (c.ui.pictures) await c.ui.screens.talk(c.ui, speaker, text);
  else {
    await c.ui.clear();
    await c.ui.print(`${speaker} tells you:`);
    await c.ui.print();
    await c.ui.print('"' + text + '"');
  }
  await C.waitKey(c);
  return [speaker, text];
}
