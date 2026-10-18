/**
 * The page: choose your files, then play. It builds the graphical front end on the canvas, loads the pictures
 * (and, if given, the tunes and the dialogue document) from the files the player chose, saves the top ten and
 * the tombstones in localStorage, and runs games the way the original's menu does: a game ends, the menu
 * comes back.
 */
import { Assets, AssetError } from "../gfx/assets.js";
import { browserInflate } from "../gfx/image.js";
import { GraphicalUI } from "../gfx/gui.js";
import * as screens from "../gfx/screens.js";
import { Sound, WebAudioOut } from "../gfx/sound.js";
import { Context } from "../context.js";
import { Files } from "../files.js";
import { playGame } from "../game.js";
import * as flip from "../flip.js";
import * as dialogue from "../dialogue.js";
import { LocalStorageStorage } from "./storage.js";
import { BrowserBackend } from "./backend.js";
import { forgetFiles, loadFiles, readChosen, saveFiles } from "./assetstore.js";

const G = globalThis as any;
const $ = (id: string): any => G.document.getElementById(id);

let chosen = new Map<string, Uint8Array>();
let usingBundled = false;                  // the files that come with the page, until the player chooses their own
const storage = new LocalStorageStorage();

function say(text: string, bad = false): void { const el = $("status"); el.textContent = text; el.className = bad ? "bad" : ""; }

/** what the chosen files add up to */
function describe(files: Map<string, Uint8Array>): string {
  let pics = 0, tunes = 0, doc = false, font = false;
  for (const [k, v] of files) {
    const p = k.replace(/\\/g, "/");
    if (/\.png$/i.test(p)) pics += 1;
    if (/font\/font\.json$/i.test(p)) font = true;
    if (/(^|\/)(ms\d+|ts)\.bin$/i.test(p)) tunes += 1;
    if (/\.(md|txt)$/i.test(p) && looksLikeDialogue(v)) doc = true;
  }
  return `${pics} pictures${font ? "" : " (no font yet)"}, ${tunes} tune files, dialogue ${doc ? "found" : "not found"}`;
}

function looksLikeDialogue(bytes: Uint8Array): boolean {
  const head = new TextDecoder().decode(bytes.subarray(0, 200000));
  return /^Landmark \d+ \(.*\), slot \d+$/m.test(head);
}

/** the dialogue records: the document among the files (the bundled one, or the player's own), or a placeholder line for each person when there is none */
function installDialogue(files: Map<string, Uint8Array>): boolean {
  for (const [k, v] of files) {
    if (/\.(md|txt)$/i.test(k) && looksLikeDialogue(v)) { dialogue.setSource(new TextDecoder().decode(v)); return true; }
  }
  let doc = "";
  for (let lm = 0; lm < 18; lm++) for (let slot = 0; slot < 3; slot++) {
    doc += `Landmark ${lm} (landmark), slot ${slot}\nSpeaker: A traveler\nText: Add the dialogue document to hear what people say here.\n\n`;
  }
  dialogue.setSource(doc);
  return false;
}

async function start(): Promise<void> {
  say("Reading the pictures...");
  let assets: Assets;
  try { assets = await Assets.load(chosen, browserInflate); }
  catch (e) { say(e instanceof AssetError ? e.message + ". Choose the folder that holds font/, images/ and screens/." : String(e), true); return; }
  const heard = installDialogue(chosen);
  $("setup").hidden = true;
  $("play").hidden = false;
  const canvas = $("screen");
  const backend = new BrowserBackend(canvas);
  const ui = new GraphicalUI(assets, backend, true);
  ui.screens = screens;
  ui.dailyPause = 1.0;                  // each day's scene stays up long enough to see; Return stops it
  ui.huntPause = 0.02;                  // a pass of the hunt, so the whole hunt takes up to a minute
  ui.byPace = true;                     // ... for a second at a steady pace, less when pushing harder
  if (new G.URLSearchParams(G.location.search).has("fast")) { ui.dailyPause = 0.01; ui.byPace = false; ui.huntPause = 0; }   // for the tests
  const out = new WebAudioOut();
  const sound = new Sound(() => false, out);
  sound.loadTuneFiles(chosen);
  ui.sound = sound;
  backend.onKey = () => sound.unlock();
  $("soundbtn").onclick = () => backend.push("\x13");
  // show the state on the button: the word that is current (on or off) is bold and underlined
  const showSound = () => {
    const on = !!sound.enabled();
    $("son").classList.toggle("cur", on);
    $("soff").classList.toggle("cur", !on);
  };
  G.setInterval(showSound, 150);
  backend.attachField($("kbd"));
  backend.focusField();                                     // we are inside the Play click: the phone may raise its keyboard now
  // the on-screen keys (shown on touch screens): they must not take the focus from the typing field
  const PAD: Record<string, string> = { left: "\x1c", up: "\x1e", down: "\x1f", right: "\x1d", space: " ", enter: "\r", back: "\x7f" };
  for (const b of G.document.querySelectorAll("#pad button")) {
    b.addEventListener("pointerdown", (e: any) => { e.preventDefault(); backend.onKey(); backend.push(PAD[b.dataset.k]); backend.focusField(); });
  }
  $("hint").textContent = heard ? "" : "Dialogue document not supplied: people have nothing to say yet.";
  if (G.__oregonSetup) G.__oregonSetup(ui, backend);   // a hook for the browser tests, before the first game starts
  const files = new Files(storage);
  let soundFlag = 1, first = true;
  for (;;) {
    const c = new Context(ui, files);
    c.mem.poke(975, soundFlag);                       // memory byte 975 is the sound switch (MENU 130)
    sound.enabled = () => !!c.mem.peek(975);
    sound.toggle = () => c.mem.poke(975, c.mem.peek(975) ? 0 : 1);
    try { await playGame(c, false); }
    catch (e) { showError(e); return; }
    soundFlag = c.mem.peek(975);
    first = false;
    await flip.backToMenu(c);                         // 31000: side 1 again if side 2 is in, then the menu
  }
  void first;
}

function showError(e: unknown): void {
  const el = $("error");
  el.hidden = false;
  el.textContent = "The game stopped: " + String((e as any)?.stack ?? e) + "\n\nReload the page to start again; your top ten and tombstones are kept.";
}

async function chooseFiles(list: any[]): Promise<void> {
  const added = await readChosen(list);
  if (usingBundled) { chosen = new Map(); usingBundled = false; }     // their own files replace the included ones
  for (const [k, v] of added) chosen.set(k, v);
  $("have").textContent = describe(chosen);
  $("go").disabled = ![...chosen.keys()].some((k) => /font\/font\.json$/i.test(k.replace(/\\/g, "/")));
  say(await saveFiles(chosen) ? "Saved in this browser; you will not need to choose them again." : "Could not keep the files in this browser; you will need to choose them again next time.");
}

/** the game files that ship with the page (data/manifest.json lists them); null when the page has none */
async function loadBundled(): Promise<Map<string, Uint8Array> | null> {
  try {
    const res = await G.fetch("data/manifest.json", { cache: "no-cache" });
    if (!res.ok) return null;
    const names: string[] = await res.json();
    const out = new Map<string, Uint8Array>();
    let done = 0;
    const queue = [...names];
    const worker = async (): Promise<void> => {
      for (let n = queue.shift(); n !== undefined; n = queue.shift()) {
        const r = await G.fetch("data/" + n.split("/").map(encodeURIComponent).join("/"));
        if (!r.ok) throw new Error(`${n}: ${r.status}`);
        out.set(n, new Uint8Array(await r.arrayBuffer()));
        say(`Loading the game... ${++done} of ${names.length}`);
      }
    };
    await Promise.all(Array.from({ length: 8 }, worker));
    return out;
  } catch (e) { say("The game files that come with this page could not be loaded: " + String(e), true); return null; }
}

async function main(): Promise<void> {
  $("folder").onchange = (e: any) => chooseFiles([...e.target.files]);
  $("loose").onchange = (e: any) => chooseFiles([...e.target.files]);
  $("go").onclick = () => start();
  $("forget").onclick = async () => { await forgetFiles(); chosen = new Map(); $("have").textContent = describe(chosen); $("go").disabled = true; say("Forgotten."); };
  $("resetscores").onclick = () => { if (G.confirm("Erase the saved top ten and tombstones?")) { storage.clear(); say("Erased."); } };
  const bundled = await loadBundled();
  if (bundled) {
    chosen = bundled;
    usingBundled = true;
    $("own").hidden = false;                          // choosing your own files stays possible, as an override
    $("go").disabled = false;
    say("Ready.");
    return;
  }
  $("own").hidden = false; $("own").open = true;      // no files came with the page: ask for them
  const saved = await loadFiles();
  if (saved) { chosen = saved; $("have").textContent = describe(chosen); $("go").disabled = ![...chosen.keys()].some((k) => /font\/font\.json$/i.test(k.replace(/\\/g, "/"))); say("Your files were kept from last time."); }
  else $("go").disabled = true;
}
main();
