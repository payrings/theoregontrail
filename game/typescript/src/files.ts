/**
 * The two files the original keeps on disk (the Python rebuild's files.py), held behind a small
 * storage interface so the same code runs in memory (tests), in a folder (Node) and in the browser
 * (localStorage).
 *
 *   HISCORE.SEQ  thirty text fields ended by carriage returns: name, points, rating for each of ten
 *   TOMB.SEQ     one file per disk side; two 49-byte records, each of four carriage-return fields
 *                (segment code, miles, name, epitaph). A new stone is written at offset 0.
 */
import * as D from "./data.js";

export const TOMB_RECORD_SIZE = 49;
export const TOP_TEN_FIELDS = 30;
const EMPTY_TOMB = "0";

/** Where the bytes live. Names are "HISCORE.SEQ", "side1/TOMB.SEQ", "side2/TOMB.SEQ". */
export interface Storage {
  read(name: string): Uint8Array | null;
  write(name: string, data: Uint8Array): void;
}

export class MemoryStorage implements Storage {
  files = new Map<string, Uint8Array>();
  read(name: string): Uint8Array | null { const f = this.files.get(name); return f ? f.slice() : null; }
  write(name: string, data: Uint8Array): void { this.files.set(name, data.slice()); }
}

export type HiscoreEntry = [string, number, string];
export interface TombRecord { segment: number; miles: string; name: string; epitaph: string }

const ascii = (s: string): Uint8Array => Uint8Array.from(Array.from(s, (ch) => { const n = ch.charCodeAt(0); return n < 128 ? n : 63; }));

function asNumber(text: string): number {
  const t = (text || "").trim();
  if (!t) return 0;
  const n = Number(t);
  return Number.isFinite(n) ? n : 0;
}
/** a field as a whole number; one that is not a number counts as 0 */
function asInt(text: string): number {
  const n = asNumber(text);
  return Math.floor(n);
}

export function hiscoreFields(entries: HiscoreEntry[]): string[] {
  const out: string[] = [];
  for (const [name, points, rating] of entries) out.push(String(name), String(points), String(rating));
  while (out.length < TOP_TEN_FIELDS) out.push("");
  return out.slice(0, TOP_TEN_FIELDS);
}

export class Files {
  constructor(public store: Storage = new MemoryStorage()) {}

  private static join(fields: string[]): string { return fields.map((f) => f + "\r").join(""); }
  private static text(b: Uint8Array): string { return Array.from(b, (n) => String.fromCharCode(n)).join(""); }

  // ---------------------------------------------------------------- top ten
  readHiscore(): HiscoreEntry[] {
    const raw = this.store.read("HISCORE.SEQ");
    if (!raw) return [];
    const fields = Files.text(raw).split("\r");
    const entries: HiscoreEntry[] = [];
    for (let i = 0; i < 10; i++) {
      const chunk = fields.slice(i * 3, (i + 1) * 3);
      if (chunk.length < 3) break;
      entries.push([chunk[0], asInt(chunk[1]), chunk[2]]);
    }
    return entries;
  }
  writeHiscore(entries: HiscoreEntry[]): void {
    this.store.write("HISCORE.SEQ", ascii(Files.join(hiscoreFields(entries))));
  }
  /** MANAGEMENT 700: replace the list with the original ten */
  resetHiscore(): HiscoreEntry[] {
    this.writeHiscore(D.originalTopTen());
    return this.readHiscore();
  }

  // ------------------------------------------------------------- tombstones
  private tombName(side: number): string { return `side${side + 1}/TOMB.SEQ`; }
  private tombBytes(side: number): number[] {
    const raw = this.store.read(this.tombName(side));
    if (raw) return Array.from(raw);
    const empty = Array.from(ascii(EMPTY_TOMB + "\r" + EMPTY_TOMB + "\r"));
    while (empty.length < TOMB_RECORD_SIZE) empty.push(13);
    return empty.concat(empty);
  }
  /** `& TPTR, index * 49` then four `& TREED` reads; null when the record's segment code is 0 */
  readTombs(side: number, index = 0): TombRecord | null {
    const raw = this.tombBytes(side);
    let pos = index * TOMB_RECORD_SIZE;
    const fields: string[] = [];
    for (let k = 0; k < 4; k++) {
      let field = "";
      while (pos < raw.length && raw[pos] !== 0 && raw[pos] !== 13 && field.length < 240) {
        field += String.fromCharCode(raw[pos] & 0x7f);
        pos += 1;
      }
      pos += 1;
      fields.push(field);
    }
    const segment = asInt(fields[0]);
    if (segment === 0) return null;
    return { segment, miles: fields[1], name: fields[2], epitaph: fields[3] };
  }
  /** TOMB.LIB 50035: four fields at offset 0, nothing cut */
  writeTomb(side: number, segment: number, miles: string, name: string, epitaph: string): void {
    const record = Array.from(ascii(Files.join([String(segment), String(miles), String(name), String(epitaph)])));
    const raw = this.tombBytes(side);
    while (raw.length < record.length) raw.push(0);
    for (let i = 0; i < record.length; i++) raw[i] = record[i];
    this.store.write(this.tombName(side), Uint8Array.from(raw));
  }
  /** MANAGEMENT 250: only the record at offset 0 is blanked */
  eraseTombs(side: number): void {
    const raw = this.tombBytes(side);
    const blank = Array.from(ascii(EMPTY_TOMB + "\r" + EMPTY_TOMB + "\r"));
    for (let i = 0; i < blank.length; i++) raw[i] = blank[i];
    this.store.write(this.tombName(side), Uint8Array.from(raw));
  }
}
