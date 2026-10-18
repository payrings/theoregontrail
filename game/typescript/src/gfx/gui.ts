/**
 * The graphical front end: the same UI the text tests use, drawn as the Apple II screen
 * (the Python rebuild's graphics/gui.py).
 *
 * It does what the `&` package did: a text window, a cursor, proportional letters two dots apart, nine
 * dots to a line, word wrap, pictures and boxes. The drawing methods are synchronous; only reading a key
 * waits, through the Backend. A browser backend answers from key events; the script backend (used by the
 * tests) answers from a list of keys and records each frame.
 */
import { ALLOWED, allowedChars, type UI } from "../ui.js";
import type { Assets } from "./assets.js";
import { Canvas, H, W } from "./canvas.js";
import type { Img } from "./image.js";

export const BLOCK = String.fromCharCode(127);          // the input cursor is character 127 of the font

/** where the finished picture goes and where the keys come from */
export interface Backend {
  show(img: Img): void;
  /** the next key; null at the end of a script's input */
  read(): Promise<string | null>;
  /** like read, but "" when no key came within `seconds` (the cursor blinks on this) */
  readTimeout(seconds: number): Promise<string | null>;
  /** a key without waiting, or null */
  poll(): string | null;
  /** let the window repaint and take in keys without reading any */
  pump(): Promise<void>;
  flush(): void;
  /** let time pass */
  sleep(seconds: number): Promise<void>;
}

export interface SoundPlayer {
  enabled: () => boolean;
  toggle: () => void;
  waiting(): void;
  stop(): void;
  select(name: string): void;
  collision?(): number;
  close?(): void;
}

export const silentSound = (): SoundPlayer => ({ enabled: () => false, toggle() {}, waiting() {}, stop() {}, select() {}, collision: () => 0, close() {} });

export class GraphicalUI implements UI {
  [extra: string]: any;
  pictures = true;
  countsKeyboardTime = true;
  showDailyScreen: boolean;
  dailyPause = 0;
  out: string[] = [];
  screens: any = null;                                  // set by the owner: the screens module
  cv: Canvas;
  glyphs: Assets["glyphs"];
  hsp: number;
  vsp = 1;
  win: [number, number, number, number] = [0, 0, W, H];
  cx = 0; cy = 0;
  hang = 0;                                             // indent of wrapped lines
  slack = -1;                                           // a word fits if cx + width <= window width - 1
  inverse = false;                                      // INVERSE: dark letters on a white panel
  linebase = 0;                                         // where the current line starts
  sound: SoundPlayer = silentSound();
  static readonly BLINK = 0.5;                          // seconds the cursor stays on or off

  constructor(public assets: Assets, public backend: Backend, showDaily = true) {
    this.cv = new Canvas(assets);
    this.glyphs = assets.glyphs;
    this.hsp = assets.hsp;
    this.showDailyScreen = showDaily;
  }

  // ---------------------------------------------------------- text model
  width(s: string): number {
    let w = 0;
    for (const ch of s) w += (this.glyphs.get(ch) ?? [6])[0] + this.hsp;
    return w;
  }
  /** & DFW: a text window, cursor at its top-left */
  dfw(x: number, y: number, w: number, h: number): void { this.win = [x, y, w, h]; this.cx = this.cy = 0; this.linebase = 0; this.hang = 0; }
  /** & CO,x,y (window coordinates; a missing one is left alone) */
  co(x?: number | null, y?: number | null): void {
    if (x !== undefined && x !== null) { this.cx = x; this.linebase = x; }
    if (y !== undefined && y !== null) this.cy = y;
  }
  put(s: string): void {
    const [wx, wy] = this.win;
    for (const ch of s) this.cx += this.cv.glyph(ch, wx + this.cx, wy + this.cy, this.inverse) + this.hsp;
  }
  /** the advance of one digit: the width of a column when BASIC pads a number with spaces */
  cell(): number { return this.width("0"); }
  /** print s right-aligned in n digit-wide columns (BASIC's RIGHT$("   " + s, n)); padding counts digit cells, not space glyphs */
  padded(s: unknown, n: number, newline = false): void {
    const t = String(s).slice(-n);
    this.cx += this.cell() * (n - t.length);
    this.put(t);
    if (newline) this.nl();
  }
  nl(): void { this.cx = 0; this.linebase = 0; this.cy += 8 + this.vsp; }
  line(s: string, newline = true, centre = false): void {
    if (centre) this.cx = Math.floor((this.win[2] - this.width(s)) / 2);
    this.put(s);
    if (newline) this.nl();
  }
  /** print s, wrapping at the window's right edge; wrapped lines start at `hang` */
  para(s: string, newline = true, hang = 0, first = 0): void {
    const ww = this.win[2];
    const toks: [string, string][] = [];
    let i = 0;
    while (i < s.length) {
      let j = i; while (j < s.length && s[j] === " ") j++;
      let k = j; while (k < s.length && s[k] !== " ") k++;
      toks.push([s.slice(i, j), s.slice(j, k)]);
      i = k;
    }
    if (this.cx === 0) this.cx = first;
    for (let [sp, w] of toks) {
      if (this.cx > this.linebase && this.cx + this.width(sp + w) > ww + this.slack) {
        this.nl(); this.cx = this.linebase = hang; sp = "";
      }
      this.put(sp + w);
    }
    if (newline) this.nl();
  }

  // ------------------------------------------------ the UI the game uses
  print(text = ""): void {
    this.out.push(text);
    if (text.endsWith(" ") && text.trim()) this.para(text, false, this.hang);    // a prompt: the cursor stays
    else this.para(text, true, this.hang);
  }
  clear(): void {
    this.cv.clear();
    this.win = [0, 0, W, H]; this.cx = this.cy = 0; this.linebase = 0; this.hang = 0; this.vsp = 1; this.inverse = false;
    this.out.push("<clear>");
  }
  at(x: number, y: number): void { this.co(x, y); }
  window(...a: number[]): void { if (a.length === 4) this.dfw(a[0], a[1], a[2], a[3]); }
  wind(n = 0): void { if (n === 0) { this.win = [0, 0, W, H]; this.cx = this.cy = 0; } }
  box(...a: number[]): void { if (a.length >= 4) this.cv.box(a[0], a[1], a[2], a[3], a[4] ?? 0); }
  indent(n: number): void { this.hang = n < 0 ? -n : 0; }
  lineTo(): void {}
  centre(text: string): void { this.line(text, true, true); }

  // --------------------------------------------------------------- input
  refresh(): void { this.backend.show(this.cv.render()); }
  flush(): void { this.backend.flush(); }
  async pump(): Promise<void> { await this.backend.pump(); }
  pollRaw(): string | null { return this.backend.poll(); }
  pollKey(): string | null { const k = this.backend.poll(); return k === "\r" || k === "\n" ? "\r" : null; }
  async sleep(seconds: number): Promise<void> { await this.backend.sleep(seconds); }

  /** & SPACE writes at 184 and makes no sound; the program's own line 950 (and WIN's) writes at 182 and
   *  plays the tune while it waits (`tune`). */
  async waitKey(_allowed = "", prompt = "Press SPACE BAR to continue", opts: { y?: number; tune?: boolean } = {}): Promise<string> {
    const y = opts.y ?? 184, tune = !!opts.tune;
    this.window(0, 0, W, H);
    this.cv.clearText(0, 180, W - 1, H - 1);
    this.co(0, y);
    this.line(prompt, true, true);
    this.refresh();
    if (tune) this.sound.waiting();                      // 955: IF PEEK (975) THEN & PT,1,1
    try {
      for (;;) {
        const k = await this.backend.read();
        if (k === null) return "";
        if (k === "\x13") {                                // 957: Control-S flips the sound and goes round again
          if (tune) { this.sound.toggle(); this.sound.stop(); this.sound.waiting(); }
          continue;
        }
        return k;
      }
    } finally { this.sound.stop(); }
  }

  private async readBlinking(): Promise<string | null> { return this.backend.readTimeout(GraphicalUI.BLINK); }

  /** `ret=false` makes Return an ignored key (the store's item prompt takes 1 to 5 or the space bar) */
  async key(allowed = "", maxlen = 1, _def = "", ret = true): Promise<string> {
    const ok = allowed ? new Set([...allowedChars(allowed), ...(ret ? ["\r", "\n"] : [])]) : null;
    const [wx, wy] = this.win;
    const x0 = this.cx, y0 = this.cy;
    const got: string[] = [];
    let shown = true;
    for (;;) {
      this.cv.clearText(wx + x0, wy + y0, wx + x0 + 120, wy + y0 + 9);
      this.cx = x0; this.cy = y0;
      this.put(got.join("") + (shown ? BLOCK : ""));
      this.refresh();
      const k = await this.readBlinking();
      if (k === "") { shown = !shown; continue; }
      shown = true;
      if (k === null) break;
      if (k === "\r" || k === "\n") { if (ret) break; continue; }
      if (k === "\x7f" || k === "\b") { got.pop(); continue; }
      if (k.length !== 1 || k < " " || k > "~") continue;          // arrow keys and the like
      if (got.length >= maxlen || (ok && !ok.has(k))) continue;
      got.push(k);
      if (maxlen === 1 && !ret) break;                              // only the store's item prompt answers on the key itself
    }
    this.cv.clearText(wx + x0, wy + y0, wx + x0 + 120, wy + y0 + 9);
    this.cx = x0; this.cy = y0;
    this.put(got.join(""));
    this.nl();
    return got.join("");
  }

  async yesNo(prompt = ""): Promise<string> {
    if (prompt) this.print(prompt);
    const x0 = this.cx, y0 = this.cy;
    const [wx, wy] = this.win;
    this.cx = x0; this.cy = y0;
    let shown = true;
    for (;;) {
      this.cv.clearText(wx + x0, wy + y0, wx + x0 + 12, wy + y0 + 9);
      this.cx = x0; this.cy = y0;
      if (shown) this.put(BLOCK);
      this.refresh();
      const k = await this.readBlinking();
      if (k === "") { shown = !shown; continue; }
      if (k === null) return "N";
      const u = k.toUpperCase();
      if (u === "Y" || u === "N") {
        this.cv.clearText(wx + x0, wy + y0, wx + x0 + 12, wy + y0 + 9);
        this.cx = x0; this.cy = y0;
        this.put(u);
        this.nl();
        return u;
      }
    }
  }

  async flipDisk(side: number, title = "OREGON TRAIL"): Promise<string> {
    const other = side === 1 ? 2 : 1;
    this.clear();
    this.co(0, 80);
    this.line(`Please insert side ${other} of the ${title} diskette.`, true, false);
    await this.waitKey();
    return String(other);
  }
}
export { ALLOWED };
