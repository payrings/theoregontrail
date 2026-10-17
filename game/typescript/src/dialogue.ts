/**
 * The 51 monologues, read from the reference document at run time and never copied into this
 * repository. The document is the player's own: the browser build reads it from the folder they pick,
 * the command line from a path.
 *
 * Landmark records: three per landmark, each a speaker and a text. The record read is at byte offset
 * (LM - S * 5) * 768 + A * 256, where S is the disk side and A the slot.
 */
export type Record3 = [string, string] | null;

export class Dialogue {
  constructor(public records: Map<number, Record3[]> = new Map()) {}
  get(landmark: number, slot: number): Record3 {
    const row = this.records.get(landmark);
    if (!row || slot < 0 || slot >= row.length) return null;
    return row[slot];
  }
  speaker(landmark: number, slot: number): string { return this.get(landmark, slot)?.[0] ?? ""; }
  text(landmark: number, slot: number): string { return this.get(landmark, slot)?.[1] ?? ""; }
  get size(): number { let n = 0; for (const v of this.records.values()) n += v.length; return n; }
}

const HEAD = /^Landmark (\d+) \((.*?)\), slot (\d+)$/;
const SPEAKER = /^\s*Speaker:\s*(.*)$/;
const TEXT = /^\s*Text:\s*(.*)$/;

/** read the records out of the appendix's text */
export function parse(source: string): Dialogue {
  const records = new Map<number, Record3[]>();
  let landmark: number | null = null, slot: number | null = null;
  let speaker: string | null = null, text: string | null = null;
  const store = () => {
    if (landmark === null || slot === null) return;
    let row = records.get(landmark);
    if (!row) { row = [null, null, null]; records.set(landmark, row); }
    row[slot] = [speaker ?? "", text ?? ""];
  };
  for (const raw of source.split(/\r?\n/)) {
    let m = HEAD.exec(raw);
    if (m) {
      if (landmark !== null) store();
      landmark = parseInt(m[1], 10); slot = parseInt(m[3], 10); speaker = text = null;
      continue;
    }
    m = SPEAKER.exec(raw);
    if (m) { speaker = m[1].trim(); continue; }
    m = TEXT.exec(raw);
    if (m) text = m[1].trim();
  }
  if (landmark !== null) store();
  return new Dialogue(records);
}

let loaded: Dialogue | null = null;
/** give the game the text of the dialogue document */
export function setSource(source: string): void { loaded = parse(source); }
export function available(): boolean { return loaded !== null; }
export function load(): Dialogue {
  if (!loaded) throw new Error("the dialogue records were not loaded. They are MECC's text and are not redistributed here: give the game your copy of the reference document.");
  return loaded;
}
