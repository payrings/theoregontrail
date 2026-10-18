// Plays whole games through the TypeScript graphical front end with a self-playing keyboard and prints a
// hash of every frame, to compare with gfx_game_py.py.
//   node test/gfx_game.mjs ASSETS_FOLDER FIRST LAST [--wander] [--preset] [--frames FILE]
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
const D = fileURLToPath(new URL("../dist/", import.meta.url));
const { Assets } = await import(D + "gfx/assets.js");
const { GraphicalUI } = await import(D + "gfx/gui.js");
const screens = await import(D + "gfx/screens.js");
const { Context } = await import(D + "context.js");
const { playGame } = await import(D + "game.js");
const { AutoUI, ALLOWED } = await import(D + "ui.js");
const N = await import(D + "num.js");
const dialogue = await import(D + "dialogue.js");

let argv = process.argv.slice(2);
const wander = argv.includes("--wander"), preset = argv.includes("--preset");
let framesFile = null;
const fi = argv.indexOf("--frames");
if (fi >= 0) { framesFile = argv[fi + 1]; argv.splice(fi, 2); }
argv = argv.filter((a) => a !== "--wander" && a !== "--preset");
let answersFile = null;
const ai = argv.indexOf("--answers");
if (ai >= 0) { answersFile = argv[ai + 1]; argv.splice(ai, 2); }
let DUMP = null;
let STOP = null;
const si = argv.indexOf("--stop");
if (si >= 0) { STOP = Number(argv[si + 1]); argv.splice(si, 2); }
const di = argv.indexOf("--dump");
if (di >= 0) { DUMP = new Set(argv[di + 1].split(",").map(Number)); argv.splice(di, 2); }
const recorded = JSON.parse(readFileSync(answersFile, "utf8"));
const [folder, first, last] = [argv[0], Number(argv[1]), Number(argv[2])];

const files = new Map();
(function walk(d, rel) { for (const f of readdirSync(d)) { const p = d + "/" + f, r = rel ? rel + "/" + f : f; statSync(p).isDirectory() ? walk(p, r) : files.set(r, new Uint8Array(readFileSync(p))); } })(folder, "");
const assets = await Assets.load(files, async (b) => new Uint8Array(inflateSync(b)));
const doc = fileURLToPath(new URL("../data/dialogue.md", import.meta.url));
dialogue.setSource(readFileSync(doc, "utf8"));

const rgbHash = (im) => { const o = Buffer.alloc(im.w * im.h * 3); for (let i = 0; i < im.w * im.h; i++) { o[i * 3] = im.data[i * 4]; o[i * 3 + 1] = im.data[i * 4 + 1]; o[i * 3 + 2] = im.data[i * 4 + 2]; } return createHash("md5").update(o).digest("hex").slice(0, 8); };

class Backend {
  constructor() { this.keys = []; this.frames = []; this.t = 0; }
  show(img) {
    if (STOP !== null && this.frames.length > STOP) throw new Error("stop");
    if (DUMP && DUMP.has(this.frames.length)) { const o = Buffer.alloc(img.w * img.h * 3); for (let i = 0; i < img.w * img.h; i++) { o[i * 3] = img.data[i * 4]; o[i * 3 + 1] = img.data[i * 4 + 1]; o[i * 3 + 2] = img.data[i * 4 + 2]; } writeFileSync(`${process.env.GFX_DUMP_DIR || "."}/ts_${this.frames.length}.rgb`, o); }
    this.frames.push(rgbHash(img));
  }
  async read() { return this.keys.length ? this.keys.shift() : null; }
  async readTimeout() { return this.read(); }
  poll() { return null; }
  async pump() {}
  flush() {}
  now() { return this.t; }
  async sleep(s) { this.t += Math.max(0, s); }
}

class AutoGUI extends GraphicalUI {
  constructor() {
    super(assets, new Backend(), true);
    this.answers = [];
    this.dailyPause = 0.05;
    this.screens = screens;
    this.countsKeyboardTime = false;                  // real time must not seed the generator in a test (Python runs on a fake clock)
  }
  next() { return this.answers.length ? this.answers.shift() : ""; }
  answer(maxlen, ret = true) {
    const a = maxlen ? this.next().slice(0, maxlen) : this.next();
    this.backend.keys = [...a, ...(ret ? ["\r"] : [])];            // a line ends with Return
  }
  async key(allowed = "", maxlen = 1, def = "", ret = true) { this.answer(maxlen, ret); return super.key(allowed, maxlen, def, ret); }
  async yesNo(prompt = "") {
    let z = "";
    for (let i = 0; i < 64; i++) { z = this.next().slice(0, 3); if (z) break; }
    this.backend.keys = z ? [z[0]] : [];
    return super.yesNo(prompt);
  }
  async waitKey(allowed = "", prompt = "Press SPACE BAR to continue", opts = {}) { this.backend.keys = [" "]; return super.waitKey(allowed, prompt, opts); }
  async flipDisk(side, title = "OREGON TRAIL") { this.backend.keys = [" "]; return super.flipDisk(side, title); }
}

N.use("exact");
for (let seed = first; seed <= last; seed++) {
  const ui = new AutoGUI();
  ui.answers = [...recorded[String(seed)]];
  const c = new Context(ui);
  c.rng.seedFromKeyboard(seed);
  c.mem.keyboardCounter = seed;
  c.mem.poke(975, 1);                                 // the sound switch, as the Python main sets it for a graphical ui
  try { await playGame(c, preset); } catch (e) { console.error(seed, String(e.stack || e).slice(0, 600)); }
  const fr = ui.backend.frames;
  console.log(seed, fr.length, createHash("md5").update(fr.join("")).digest("hex").slice(0, 10));
  if (framesFile) writeFileSync(framesFile, fr.join("\n"));
}
