/**
 * The picture and font files the graphical mode draws with (the Python rebuild's graphics/assets.py).
 * They are read from a folder the player chooses and kept only in the browser; nothing here ships with
 * the program. Layout (all paths relative to the chosen folder):
 *   screens/<name>.png    full 280 x 192 screens (l0 first landmark, m0 the map, backdrop_<name> backgrounds)
 *   images/<table>_<NN>[_m<k>].png   small pictures, transparent where black; _m<k> is the version for x mod 14 = k
 *   font/font.png + font/font.json   the letters
 *   hunt/hunt.json        the hunting field's sprites (optional)
 *   theme.json            optional: plain text and fixed colours instead of the Apple's colour rules
 */
import { decodePng, type Img, type Inflate } from "./image.js";

export type Glyph = [number, number, number[][]];     // width, y offset, rows of 0/1
export interface Theme { plainText: boolean; textColour: [number, number, number]; colours: Record<number, [number, number, number]> }

export class AssetError extends Error {}

const text = (b: Uint8Array): string => new TextDecoder().decode(b);

export class Assets {
  hsp = 2;
  glyphs = new Map<string, Glyph>();
  theme: Theme | null = null;
  private pics = new Map<string, Img>();
  private json = new Map<string, any>();

  /** `files` maps a path inside the folder ("images/first_02.png") to its bytes */
  static async load(files: Map<string, Uint8Array>, inflate: Inflate): Promise<Assets> {
    const a = new Assets();
    const norm = new Map<string, Uint8Array>();
    for (const [k, v] of files) norm.set(k.replace(/\\/g, "/").replace(/^\.?\//, ""), v);
    // a folder chosen in a browser carries its own name in front; drop whatever precedes the known folders
    const roots = new Map<string, number>();
    for (const k of norm.keys()) { const m = /^(.*?\/)?(screens|images|font|hunt)\//.exec(k); if (m) roots.set(m[1] ?? "", (roots.get(m[1] ?? "") ?? 0) + 1); }
    const root = [...roots].sort((x, y) => y[1] - x[1] || x[0].length - y[0].length)[0]?.[0] ?? "";    // the folder holding most of them
    const under = (k: string): string | null => (k.startsWith(root) ? k.slice(root.length) : null);
    for (const [k, v] of norm) {
      const rel = under(k);
      if (!rel) continue;
      if (/^(screens|images)\/[^/]+\.png$/.test(rel)) a.pics.set(rel.replace(/\.png$/, ""), await decodePng(v, inflate));
      else if (rel === "font/font.png") a.pics.set("font/font", await decodePng(v, inflate));
      else if (rel === "font/font.json" || rel === "hunt/hunt.json" || rel === "theme.json") {
        try { a.json.set(rel, JSON.parse(text(v))); } catch { /* an unreadable file counts as missing */ }
      }
    }
    a.loadFont();
    a.loadTheme();
    return a;
  }

  private loadFont(): void {
    const meta = this.json.get("font/font.json"), sheet = this.pics.get("font/font");
    if (!meta || !sheet) throw new AssetError("font files not found (font/font.png and font/font.json)");
    this.hsp = Number(meta.hsp ?? 2);
    for (const [key, g] of Object.entries<any>(meta.glyphs)) {
      const rows: number[][] = [];
      for (let r = 0; r < g.rows; r++) {
        const row: number[] = [];
        for (let c = 0; c < g.width; c++) row.push(sheet.data[((g.y + r) * sheet.w + g.x + c) * 4 + 3] > 127 ? 1 : 0);
        rows.push(row);
      }
      this.glyphs.set(String.fromCharCode(Number(key)), [g.width, g.yoff, rows]);
    }
  }

  private loadTheme(): void {
    const meta = this.json.get("theme.json");
    if (!meta) return;
    const colours: Record<number, [number, number, number]> = {};
    for (const [k, v] of Object.entries<any>(meta.colours ?? {})) colours[Number(k)] = v as [number, number, number];
    this.theme = { plainText: !!meta.plain_text, textColour: (meta.text_colour ?? [255, 255, 254]) as [number, number, number], colours };
  }

  /** a small picture, or null */
  image(name: string): Img | null { return this.pics.get("images/" + name) ?? null; }
  /** a full screen, or null */
  screen(name: string): Img | null { return this.pics.get("screens/" + name) ?? null; }
  /** the hunting field's sprites, or null */
  hunt(): any | null { return this.json.get("hunt/hunt.json") ?? null; }
  /** any file of the folder as parsed JSON (the sprite sheet path etc.) */
  raw(name: string): Img | null { return this.pics.get(name) ?? null; }
}
