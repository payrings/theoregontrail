/**
 * FLOAT: the Columbia River rafting game (lines 1000 and 1070-1180, with collisions at 700-760).
 *
 * The BASIC is transcribed; the machine code it draws with was not analysed, so in text the raft is
 * only reported. The rules are paper section 11.2: eighteen raft positions starting at sixteen; one
 * direction change per key; two rock slots each filled on a fifteen per cent chance per pass (the draw is
 * made even when the slot is full); after pass 205 a raft at position seventeen has landed (tested before
 * the collision); after pass 225 the landing is missed; ten losses destroy the raft.
 */
import * as N from "./num.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as river from "./river.js";
import * as RS from "./gfx/raft_scene.js";
import { clockOf } from "./gfx/clock.js";

/** the original runs a few thousand passes a second on a 1 MHz machine */
export const PASSES_PER_SECOND = 4000;
export const HP_START = 16;
export const PASSES_TO_LAND = 205;
export const PASSES_TO_MISS = 225;
export const SIGN_PASSES = [60, 120, 170];
const ROCK_CHANCE = 15;                  // in a hundred
const XI = 8, YI = -4;

/** the keys the listing tests for: LE = 136 and U = 139 steer left; R = 149 and D = 138 steer right */
const LEFT_KEYS = ["\x1b[D", "\x1b[A", "\x08", "\x0b", "l", "\x1c", "\x1e"];
const RIGHT_KEYS = ["\x1b[C", "\x1b[B", "\x15", "h", "\x1d", "\x1f"];

function readKey(c: Context): string | null {
  let key = c.ui.pollKey();
  if (key === "\x1b") {
    const a = c.ui.pollKey();
    const b = a === "[" ? c.ui.pollKey() : null;
    key = b ? "\x1b[" + b : null;
  }
  return key;
}

/** line 1110: FN RX(Z) = 84 + 8 * Z, FN RY(Z) = 5 * Z - 6 */
function geometry(hp: number): [number, number, number, number] {
  const x = 84 + 8 * hp, y = 5 * hp - 6;
  return [x + 6, y + 18, x + 26, y + 25];
}

/** line 200: the raft's box against a rock's, built at line 1120 from the rock's position */
function overlap(raft: number[], rx: number, ry: number): boolean {
  const [x1, y1, x2, y2] = raft;
  const x3 = rx + 11, y3 = ry + 1;
  const x4 = x3 + 20, y4 = y3 + 6;
  return !(x2 < x3 || x1 > x4 || y1 > y4 || y2 < y3);
}

interface Rock { fl: boolean; rx: number; ry: number }

/** lines 300 and 310: a rock appears */
function newRock(c: Context, slot: number, rocks: Rock[]): void {
  const n = N.store(N.int_(N.add(N.mul(N.parse("100"), c.rng.rnd1(`300 rock type ${slot}`)), N.ONE)));
  if (N.lt(n, N.parse("14"))) {
    rocks[slot].ry = 175;
    rocks[slot].rx = N.asInt(N.int_(N.mul(N.parse("10"), c.rng.rnd1(`310 rock x ${slot}`))));
  } else {
    rocks[slot].rx = 0;
    rocks[slot].ry = 50 + N.asInt(N.int_(N.add(N.mul(N.parse("120"), c.rng.rnd1(`310 rock y ${slot}`)), N.ONE)));
  }
  rocks[slot].fl = true;
}

export async function run(c: Context): Promise<string> {
  const st = c.st;
  c.setProgram("FLOAT");
  const S = c.ui.screens;
  const scene = !!(c.ui.pictures && RS.available(c.ui));
  const clock = clockOf(c.ui);
  const texts = ["Use the arrow keys to guide your raft through the rushing waters of the Columbia River.",
    "After passing the third direction sign, land your raft at the trail to the Willamette Valley."];
  if (c.ui.pictures) {
    for (let i = 0; i < texts.length; i++) {
      await S.messageBox(c.ui, texts[i], [7, 62, 257, 109], { picture: "l16", redraw: i === 0 });
      await c.ui.waitKey();
    }
  } else {
    await c.ui.clear();
    await c.ui.print(texts[0]);
    await C.waitKey(c);
    await c.ui.print(texts[1]);
    await C.waitKey(c);
  }
  const P = (n: number) => N.parse(String(n));
  st.I[2] = P(c.mem.peek(909));
  for (let item = 3; item < 8; item++) st.I[item] = P(c.mem.peek(905 + item));
  st.I[8] = P(c.mem.peek(906) + c.mem.peek(907) * 256);
  st.I[4] = P(c.mem.peekWord(904));
  st.PF = st.I[8];
  let hp = HP_START;
  let direction = -1;
  const rocks: Rock[] = [{ fl: false, rx: 0, ry: 0 }, { fl: false, rx: 0, ry: 0 }];
  let rock = -1;
  let col = false;
  let tc = 0;
  const period = scene ? (c.ui.dailyPause > 0 ? RS.PASS_SECONDS : 0) : 1 / PASSES_PER_SECOND;
  let signs: number[] = [];
  let landing: number | null = null;
  // line 1050: the first box is the whole picture; line 1110 narrows it once the raft has moved
  const x0 = 84 + 8 * hp, y0 = 5 * hp - 6;
  let box: number[] = [x0, y0, x0 + 35, y0 + 25];
  for (;;) {
    tc += 1;
    const started = clock.now();
    // lines 1070 and 1075: no short-circuit, so the draw is made on every pass
    for (const slot of [0, 1]) {
      const roll = N.int_(N.add(N.mul(N.parse("100"), c.rng.rnd1(`1070 rock ${slot}`)), N.ONE));
      if (!rocks[slot].fl && N.le(roll, P(ROCK_CHANCE))) newRock(c, slot, rocks);
    }
    for (const r of rocks) if (r.fl) { r.rx += XI; r.ry += YI; }          // lines 1080 and 1085
    const key = readKey(c);                                              // lines 1090 and 1100
    if (hp > 0 && key !== null && LEFT_KEYS.includes(key)) direction = Math.max(direction - 1, -1);
    if (hp < 17 && key !== null && RIGHT_KEYS.includes(key)) direction = Math.min(direction + 1, 1);
    if (direction !== 0) {                                               // line 1110
      hp += direction;
      col = false;
      if (hp < 1 || hp > 16) { col = true; direction = -direction; }
      box = geometry(hp);
    }
    if (tc > PASSES_TO_LAND && hp === 17) { await landed(c); return "WIN"; }   // lines 1115 and 1116
    if (tc > PASSES_TO_MISS) { await missed(c); await landed(c); return "WIN"; }
    for (const slot of [0, 1]) {                                          // lines 1120 and 1130
      if (!col && rocks[slot].fl) {
        rock = slot;
        col = overlap(box, rocks[slot].rx, rocks[slot].ry);
        if (!col) rock = -1;
      }
    }
    if (scene && tc === RS.LANDING_PASS) landing = -1;
    if (SIGN_PASSES.includes(tc)) {
      if (scene) signs.push(-1);
      else await c.ui.print(`[direction sign at pass ${tc}]`);
    }
    for (const slot of [1, 0]) {                                          // lines 1160 and 1165
      const r = rocks[slot];
      if (r.fl && !(r.rx < 240 && r.ry > 10)) r.fl = false;
    }
    if (col) {                                                           // line 1170
      const kind = rock === -1 ? "shore" : "rock";
      if (rock !== -1) rocks[rock].fl = false;                           // 710: FL(ROCK) = 0
      if ((await collide(c, kind)) === "MENU") return "DIED";
      col = false;
      box = geometry(hp);
    }
    if (scene) {
      signs = signs.map((n) => n + 1).filter((n) => n < RS.SIGN_STEPS);
      if (landing !== null) landing += 1;
      RS.draw(c.ui, hp, rocks.filter((r) => r.fl).map((r) => [r.rx, r.ry]),
        signs.map((n) => RS.signPosition(n)), landing === null ? null : RS.landingPosition(landing));
    }
    // pace to the original's loop, so a player can see the river
    if (period > 0) await clock.sleep(Math.max(0, period - (clock.now() - started)));
  }
}

/** lines 700-760: a shore or a rock, and what it costs */
async function collide(c: Context, kind: string): Promise<string | null> {
  const st = c.st;
  const shore = kind === "shore";
  let out: string[] = [];
  out = out.concat(river.losePeople(c, N.store(N.parse(shore ? ".15" : ".6")), out.length));
  out = out.concat(river.loseOxen(c, N.store(N.parse(shore ? ".3" : ".6"))));
  out = out.concat(river.loseGoods(c, N.store(N.parse(shore ? ".5" : ".7"))));
  let text = kind === "shore" ? "The raft has hit the shore." : "The raft has hit a rock.";
  if (out.length) text += "  You have lost:";                 // 720: IF Z THEN Z$ = ...
  if (out.length > 9) {
    st.NP = 0;
    text = "The raft is destroyed, everything has been lost.";
    out = [];
  }
  const sound = (c.ui as any).sound;
  if (sound) {                                                 // 740: IF PEEK (975) THEN FOR S1 = 0 TO 3: & PT,1: NEXT
    const lasts: number = sound.collision?.() ?? 0;
    const clock = clockOf(c.ui);
    const t0 = clock.now();
    while (clock.now() - t0 < lasts) {
      await (c.ui as any).pump?.();
      await clock.sleep(0.02);
    }
  }
  await C.message(c, text, out);
  // line 750 is "FOR L = 0 TO NP - 1", and the body runs once even when NP is 0
  const n = N.fortCount(0, N.asInt(st.NP) - 1);
  for (let i = 0; i < n; i++) {
    if (N.eq(st.H1[i], N.parse("-2"))) {
      st.H1[i] = N.neg(N.ONE);
      st.NP = N.asInt(st.NP) - 1;
      st.N[i] = st.N[N.asInt(st.NP)];
    }
  }
  if (N.asInt(st.NP) <= 0) {
    await C.message(c, "Everyone in the party has died.");
    c.outcome = "DIED";
    return "MENU";
  }
  return null;
}

/** lines 950-960: the raft missed the landing, and lands anyway */
async function missed(c: Context): Promise<void> {
  const out = river.loseGoods(c, N.store(N.parse(".5")));
  if (out.length) await C.message(c, "The raft has missed the landing.  You have lost:", out);
}

/** line 900: the raft is ashore, and the state is written for WIN */
async function landed(c: Context): Promise<string> {
  const st = c.st;
  (c.ui as any).sound?.select?.("ms16");                       // 900: & RFL, "MS16.BIN" AT 1153
  await c.ui.print("One moment please...");
  c.mem.poke(900, N.asInt(st.NP), 910);
  c.mem.poke(909, N.trunc(st.I[2]), 910);
  c.mem.pokeWord(906, N.trunc(st.I[8]), 910);
  c.mem.poke(908, N.trunc(st.I[3]), 910);
  c.mem.pokeWord(904, N.trunc(st.I[4]), 910);
  for (const item of [5, 6, 7]) c.mem.poke(905 + item, N.trunc(st.I[item]), 910);
  return "WIN";
}
