// The raft must answer the arrow keys in the graphical front end: the same raft run twice, once with no keys
// and once pressing Right, must not draw the same pictures. (A raft that ignores its keys draws the same ones.)
//   node test/raft_steer.mjs ASSETS_FOLDER
import { readFileSync, readdirSync, statSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
const D = fileURLToPath(new URL("../dist/", import.meta.url));
const { Assets } = await import(D + "gfx/assets.js");
const { GraphicalUI } = await import(D + "gfx/gui.js");
const screens = await import(D + "gfx/screens.js");
const { Context } = await import(D + "context.js");
const raft = await import(D + "floatraft.js");
const files = new Map();
(function walk(d, rel) { for (const f of readdirSync(d)) { const p = d + "/" + f, r = rel ? rel + "/" + f : f; statSync(p).isDirectory() ? walk(p, r) : files.set(r, new Uint8Array(readFileSync(p))); } })(process.argv[2], "");
const assets = await Assets.load(files, async (b) => new Uint8Array(inflateSync(b)));

async function play(keyFor) {
  const frames = [];
  let pass = 0;
  const be = {
    show(img) { frames.push(createHash("md5").update(img.data).digest("hex").slice(0, 8)); },
    poll() { pass++; return keyFor(pass); },
    async read() { return " "; }, async readTimeout() { return " "; }, async pump() {}, flush() {}, async sleep() {},
  };
  const ui = new GraphicalUI(assets, be);
  ui.screens = screens;
  ui.dailyPause = 0;
  const c = new Context(ui, undefined);
  await raft.run(c);
  return createHash("md5").update(frames.join("")).digest("hex");
}
const none = await play(() => null);
const right = await play((n) => (n === 3 ? "\x1d" : null));
const left = await play((n) => (n === 3 ? "\x1c" : null));
console.log("no keys", none, "\nright  ", right, "\nleft   ", left);
const ok = none !== right && right !== left;
console.log(ok ? "ok: the raft follows its keys" : "FAIL: the raft ignores its keys");
process.exit(ok ? 0 : 1);
