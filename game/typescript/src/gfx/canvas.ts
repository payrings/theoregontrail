/**
 * A 280 x 192 picture made the way the Apple II made it (the Python rebuild's graphics/canvas.py).
 *
 * Pictures and boxes are plain colours. Text is kept as lit dots and coloured at the end by the Apple's
 * rule, so letters get the same green and violet fringes as the original: a lone dot takes the colour of
 * its column, a dot beside another is white, and a dark dot between two lit ones is filled in. A folder
 * with a theme.json switches the rule off.
 */
import type { Assets } from "./assets.js";
import { copyImage, crop, fillRect, newImage, paste, type Img } from "./image.js";

export const W = 280, H = 192;
type RGB = [number, number, number];
const WHITE: RGB = [255, 255, 254], VIOLET: RGB = [199, 52, 255], GREEN: RGB = [56, 203, 0], BLACK: RGB = [0, 0, 0];
export const COLOURS: Record<number, RGB> = { 0: [0, 0, 0], 1: GREEN, 2: VIOLET, 3: WHITE, 4: [0, 0, 0], 5: [242, 94, 0], 6: [13, 161, 255], 7: WHITE };

const key = (x: number, y: number): number => y * W + x;
const inRect = (k: number, x1: number, y1: number, x2: number, y2: number): boolean => {
  const x = k % W, y = (k - x) / W; return x >= x1 && x <= x2 && y >= y1 && y <= y2;
};

export interface Saved { x1: number; y1: number; x2: number; y2: number; crop: Img; dots: Set<number>; filled: Set<number> }

export class Canvas {
  base!: Img;
  dots = new Set<number>();
  filled = new Set<number>();
  plain: boolean;
  textColour: RGB;
  palette: Record<number, RGB>;

  constructor(public assets: Assets) {
    const theme = assets.theme;
    this.plain = !!theme;
    this.textColour = theme ? theme.textColour : WHITE;
    this.palette = { ...COLOURS, ...(theme ? theme.colours : {}) };
    this.clear();
  }

  clear(): void {
    this.base = newImage(W, H, BLACK);
    if (this.plain) {                                 // a themed folder may paint the empty screen
      const back = this.assets.screen("backdrop_default");
      if (back) paste(this.base, back, 0, 0, false);
    }
    this.dots = new Set();
    this.filled = new Set();
  }

  // ------------------------------------------------------------ drawing
  /** a picture's colours depend on its column: name_m<k>.png is the one for x mod 14 == k */
  image(name: string, x: number, y: number): boolean {
    const im = this.assets.image(`${name}_m${((x % 14) + 14) % 14}`) ?? this.assets.image(name);
    if (!im) return false;
    paste(this.base, im, x, y, true);
    return true;
  }

  /** a full-colour background from screens/backdrop_<name>.png (nothing without a theme) */
  backdrop(name: string, x = 0, y = 0): boolean {
    if (!this.plain) return false;
    const im = this.assets.screen(`backdrop_${name}`);
    if (!im) return false;
    paste(this.base, im, x, y, true);
    return true;
  }

  /** paint a coloured sprite: each character of `rows` keys the palette ('.' is transparent) */
  paintRows(rows: string[], x: number, y: number, palette: Record<string, readonly number[]>): void {
    for (let r = 0; r < rows.length; r++) for (let c = 0; c < rows[r].length; c++) {
      const ch = rows[r][c], X = x + c, Y = y + r;
      if (ch !== "." && X >= 0 && X < W && Y >= 0 && Y < H) {
        const rgb = palette[ch] ?? [255, 0, 255], d = key(X, Y) * 4;
        this.base.data[d] = rgb[0]; this.base.data[d + 1] = rgb[1]; this.base.data[d + 2] = rgb[2]; this.base.data[d + 3] = 255;
      }
    }
  }

  screen(name: string): boolean {
    const im = this.assets.screen(name);
    if (!im) return false;
    paste(this.base, im, 0, 0, false);
    this.dots.clear();
    return true;
  }

  /** & BOX: fill a rectangle (colour 0 clears it, text included) */
  box(x1: number, y1: number, x2: number, y2: number, colour = 0): void {
    x1 = Math.max(0, x1); x2 = Math.min(W - 1, x2); y1 = Math.max(0, y1); y2 = Math.min(H - 1, y2);
    if (x2 < x1 || y2 < y1) return;
    for (const d of [...this.dots]) if (inRect(d, x1, y1, x2, y2)) this.dots.delete(d);
    for (const d of [...this.filled]) if (inRect(d, x1, y1, x2, y2)) this.filled.delete(d);
    let lit: number | null = null;
    if (!this.plain) { if (colour === 1 || colour === 5) lit = 1; else if (colour === 2 || colour === 6) lit = 0; }
    if (lit !== null) {            // the Apple plots these on one parity of column only and fills the dark ones between
      let first = -1, last = -1;
      for (let x = x1; x <= x2; x++) if (x % 2 === lit) { if (first < 0) first = x; last = x; }
      if (first < 0) return;
      x1 = first; x2 = last;
    }
    if (this.plain) { fillRect(this.base, x1, y1, x2 + 1, y2 + 1, this.palette[colour]); return; }
    fillRect(this.base, x1, y1, x2 + 1, y2 + 1, COLOURS[colour]);
    if (lit !== null) for (let x = x1; x <= x2; x++) if (x % 2 !== lit) for (let y = y1; y <= y2; y++) this.filled.add(key(x, y));
  }

  /** HPLOT x1,y1 TO x2,y2 with the ROM's line routine: dx + dy + 1 dots, one across or one down at a time */
  line(x1: number, y1: number, x2: number, y2: number, colour: number): void {
    const rgb = this.palette[colour];
    const dx = Math.abs(x2 - x1), dy = Math.abs(y2 - y1);
    const sx = x2 >= x1 ? 1 : -1, sy = y2 >= y1 ? 1 : -1;
    let err = dx - dy, x = x1, y = y1;
    const both = !([0, 3, 4, 7].includes(colour) || this.plain);
    for (let step = 0; step < dx + dy + 1; step++) {
      for (const xx of both ? [x, x + 1] : [x]) {
        if (xx >= 0 && xx < W && y >= 0 && y < H) { const d = key(xx, y) * 4; this.base.data[d] = rgb[0]; this.base.data[d + 1] = rgb[1]; this.base.data[d + 2] = rgb[2]; this.base.data[d + 3] = 255; }
      }
      if (err >= 0) { x += sx; err -= dy; } else { y += sy; err += dx; }
    }
  }

  /** & TAKE: keep a rectangle of the screen */
  take(x1: number, y1: number, x2: number, y2: number): Saved {
    const dots = new Set<number>(), filled = new Set<number>();
    for (const d of this.dots) if (inRect(d, x1, y1, x2, y2)) dots.add(d);
    for (const d of this.filled) if (inRect(d, x1, y1, x2, y2)) filled.add(d);
    return { x1, y1, x2, y2, crop: crop(this.base, x1, y1, x2 + 1, y2 + 1), dots, filled };
  }

  /** & PUT: put back what take kept */
  put(s: Saved): void {
    paste(this.base, s.crop, s.x1, s.y1, false);
    for (const d of [...this.dots]) if (inRect(d, s.x1, s.y1, s.x2, s.y2)) this.dots.delete(d);
    for (const d of s.dots) this.dots.add(d);
    for (const d of [...this.filled]) if (inRect(d, s.x1, s.y1, s.x2, s.y2)) this.filled.delete(d);
    for (const d of s.filled) this.filled.add(d);
  }

  /** a dark dot between two lit dots of `colour` is lit too */
  fillGaps(colour: number, rect: [number, number, number, number]): void {
    if (this.plain) return;
    const rgb = COLOURS[colour], px = this.base.data;
    const is = (x: number, y: number): boolean => { const d = key(x, y) * 4; return px[d] === rgb[0] && px[d + 1] === rgb[1] && px[d + 2] === rgb[2]; };
    const [x1, y1, x2, y2] = rect;
    for (let y = y1; y <= y2; y++) for (let x = x1 + 1; x < x2; x++) {
      if (!is(x, y) && is(x - 1, y) && is(x + 1, y)) { const d = key(x, y) * 4; px[d] = rgb[0]; px[d + 1] = rgb[1]; px[d + 2] = rgb[2]; }
    }
  }

  /** remove letters from a rectangle and leave the pictures under them */
  clearText(x1: number, y1: number, x2: number, y2: number): void {
    for (const d of [...this.dots]) if (inRect(d, x1, y1, x2, y2)) this.dots.delete(d);
  }

  /** a white area made of lit dots, so that inverse letters cut dark ones out of it */
  panel(x1: number, y1: number, x2: number, y2: number): void {
    for (let y = Math.max(0, y1); y <= Math.min(H - 1, y2); y++) for (let x = Math.max(0, x1); x <= Math.min(W - 1, x2); x++) this.dots.add(key(x, y));
  }

  /** draw one letter with its top-left corner at (x, y); returns its width. An inverse letter removes dots. */
  glyph(ch: string, x: number, y: number, inverse = false): number {
    const g = this.assets.glyphs.get(ch) ?? this.assets.glyphs.get("?") ?? [6, 0, []] as [number, number, number[][]];
    const [w, yoff, rows] = g;
    for (let r = 0; r < rows.length; r++) for (let c = 0; c < rows[r].length; c++) {
      if (!rows[r][c]) continue;
      const X = x + c, Y = y + yoff + r;
      if (X < 0 || X >= W || Y < 0 || Y >= H) continue;
      const k = key(X, Y);
      if (inverse) {
        const ink = this.plain ? this.palette[0] : BLACK;
        if (this.dots.has(k)) { this.dots.delete(k); if (this.plain) this.setPixel(X, Y, ink); }
        else this.setPixel(X, Y, ink);
      } else this.dots.add(k);
    }
    return w;
  }

  setPixel(x: number, y: number, rgb: readonly number[]): void {
    if (x < 0 || x >= W || y < 0 || y >= H) return;
    const d = key(x, y) * 4; this.base.data[d] = rgb[0]; this.base.data[d + 1] = rgb[1]; this.base.data[d + 2] = rgb[2]; this.base.data[d + 3] = 255;
  }
  getPixel(x: number, y: number): RGB { const d = key(x, y) * 4; return [this.base.data[d], this.base.data[d + 1], this.base.data[d + 2]]; }

  // -------------------------------------------------------------- output
  render(): Img {
    const im = copyImage(this.base), px = im.data, d = this.dots;
    const set = (x: number, y: number, c: readonly number[]): void => { const o = key(x, y) * 4; px[o] = c[0]; px[o + 1] = c[1]; px[o + 2] = c[2]; px[o + 3] = 255; };
    if (this.plain) { for (const k of d) set(k % W, Math.floor(k / W), this.textColour); return im; }
    const has = (x: number, y: number): boolean => x >= 0 && x < W && d.has(key(x, y));
    for (const k of d) { const x = k % W, y = (k - x) / W; set(x, y, has(x - 1, y) || has(x + 1, y) ? WHITE : x % 2 === 0 ? VIOLET : GREEN); }
    for (const k of d) {                                // a dark dot between two lit ones
      const x = k % W, y = (k - x) / W;
      if (has(x + 2, y) && !has(x + 1, y) && x + 1 < W) set(x + 1, y, x % 2 === 0 ? VIOLET : GREEN);
    }
    const black = (x: number, y: number): boolean => { const o = key(x, y) * 4; return px[o] === 0 && px[o + 1] === 0 && px[o + 2] === 0; };
    for (const k of this.filled) {                       // the fill-in dots of a colour box stay only while both lit dots beside them do
      const x = k % W, y = (k - x) / W;
      if (x > 0 && x < W - 1 && !black(x, y)) { if (black(x - 1, y) || black(x + 1, y)) set(x, y, BLACK); }
    }
    return im;
  }
}
