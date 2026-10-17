/**
 * The browser's half of the graphical front end: the picture goes to a <canvas> scaled up without smoothing,
 * and keys come from keydown events. Reading a key is a promise that resolves when one arrives, so the game
 * (which `await`s every question) simply waits.
 */
import type { Backend } from "../gfx/gui.js";
import type { Img } from "../gfx/image.js";

const G = globalThis as any;

const KEYS: Record<string, string> = {
  Enter: "\r", Backspace: "\x7f", ArrowUp: "\x1e", ArrowDown: "\x1f", ArrowLeft: "\x1c", ArrowRight: "\x1d", Escape: "\x1b",
};

export class BrowserBackend implements Backend {
  private queue: string[] = [];
  private waiting: ((k: string | null) => void) | null = null;
  private ctx: any;
  private frame: any = null;
  /** told on every key press, so audio may start (browsers allow it only after a gesture) */
  onKey: () => void = () => {};

  constructor(public canvas: any, target: any = G.window) {
    this.ctx = canvas.getContext("2d");
    this.ctx.imageSmoothingEnabled = false;
    target.addEventListener("keydown", (e: any) => this.keydown(e));
  }

  /** a key as the game sees it, or null for one it ignores */
  static translate(e: { key: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean }): string | null {
    if (e.ctrlKey && e.key.toLowerCase() === "s") return "\x13";                  // Control-S: the sound switch
    if (e.ctrlKey || e.metaKey || e.altKey) return null;
    if (e.key in KEYS) return KEYS[e.key];
    return e.key.length === 1 ? e.key : null;
  }

  private keydown(e: any): void {
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "BUTTON") && e.key !== "Enter") return;
    const k = BrowserBackend.translate(e);
    if (k === null) return;
    e.preventDefault();
    this.onKey();
    this.push(k);
  }

  /** a key from somewhere else (the on-screen buttons) */
  push(k: string): void {
    if (this.waiting) { const w = this.waiting; this.waiting = null; w(k); }
    else { this.queue.push(k); if (this.queue.length > 64) this.queue.shift(); }
  }

  show(img: Img): void {
    if (!this.frame) this.frame = this.ctx.createImageData(img.w, img.h);
    this.frame.data.set(img.data);
    this.ctx.putImageData(this.frame, 0, 0);
  }

  read(): Promise<string | null> {
    if (this.queue.length) return Promise.resolve(this.queue.shift() as string);
    return new Promise((resolve) => { this.waiting = resolve; });
  }

  readTimeout(seconds: number): Promise<string | null> {
    if (this.queue.length) return Promise.resolve(this.queue.shift() as string);
    return new Promise((resolve) => {
      const timer = G.setTimeout(() => { if (this.waiting === done) this.waiting = null; resolve(""); }, seconds * 1000);
      const done = (k: string | null): void => { G.clearTimeout(timer); resolve(k); };
      this.waiting = done;
    });
  }

  poll(): string | null { return this.queue.length ? (this.queue.shift() as string) : null; }
  flush(): void { this.queue.length = 0; }
  /** give the browser a turn to paint and to deliver key events */
  pump(): Promise<void> { return new Promise((r) => G.setTimeout(r, 0)); }
  sleep(seconds: number): Promise<void> { return new Promise((r) => G.setTimeout(r, Math.max(0, seconds) * 1000)); }
  now(): number { return G.performance.now() / 1000; }
}
