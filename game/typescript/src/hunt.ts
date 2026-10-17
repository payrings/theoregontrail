/**
 * HUNT.LIB: hunting for food (4600 in OREGON TRAIL, 50000 to 50020 in HUNT.LIB).
 *
 * The routine has its own random generator, seeded at the start of each hunt from the Applesoft seed
 * bytes and the keyboard counter, and it reads the Applesoft seed without writing it -- so a hunt never
 * advances the game's sequence. Animal movement and hit testing were never analysed (the paper says so):
 * the text session uses a stated approximation; the spawn rules, weights, ammunition, session length and
 * the hundred-pound carry limit follow the paper.
 */
import * as N from "./num.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as HS from "./gfx/hunt_scene.js";
import * as HF from "./gfx/hunt_field.js";

export const SESSION_PASSES = 2500;
export const CARRY_LIMIT = 100;
const MAX_ANIMALS = 2;
const MAX_SHOTS = 4;

/** type: [weight low, weight span]. 0 Chimney Rock to the Snake River; 1 past Independence Rock; 2 up to it; 3-5 everywhere */
export const ANIMALS: [number, number][] = [[100, 40], [200, 200], [1700, 300], [120, 30], [2, 8], [3, 4]];

/** the hunting module's private generator: a plain linear congruential step on five bytes */
export class HuntRng {
  b: number[];
  constructor(seed: number[]) { this.b = seed.length ? seed.slice(0, 5) : [0, 0, 0, 0, 0]; }
  private value(): bigint { let v = 0n; for (const x of this.b) v = (v << 8n) | BigInt(x); return v; }
  private step(): void {
    const x = (this.value() * 1103515245n + 12345n) & ((1n << 40n) - 1n);
    for (let i = 4; i >= 0; i--) this.b[4 - i] = Number((x >> BigInt(8 * i)) & 0xffn);
  }
  below = (n: number): number => {
    this.step();
    const m = this.value() || 1n;
    return Number((m >> 11n) % BigInt(n));
  };
}

/** & HUNT,Z, LM > 3 AND LM < 13, LM > 6, LM < 7, 1, ZO, L, Z */
export function allowedTypes(landmark: number): number[] {
  const out: number[] = [];
  if (landmark > 3 && landmark < 13) out.push(0);
  if (landmark > 6) out.push(1);
  if (landmark < 7) out.push(2);
  out.push(3, 4, 5);
  return out;
}

interface Animal { type: number; still: number; low: number; span: number }

/** the approximation: a shot connects once the animal has been still for two passes */
function approximateMovement(animal: Animal | null): boolean { return animal !== null && (animal.still ?? 0) >= 2; }

/** the hunting module's own seed: the game's seed bytes plus the keyboard counter, byte by byte */
function seedBytes(c: Context): number[] {
  const seed = c.rng.seed;
  const counter = c.mem.keyboardCounter & 0xffff;
  return [0, 1, 2, 3, 4].map((i) => (seed[i] + (i < 4 ? (counter >> (8 * i)) & 0xff : 0)) & 0xff);
}

export interface Session { meat: number; bullets: number; shots?: number }

/** the hunt itself, on the paper's rules; no number comes from the game's generator */
export function huntSession(c: Context, bullets: number): Session {
  const st = c.st;
  const h = new HuntRng(seedBytes(c));
  const types = allowedTypes(st.LM);
  const animals: Animal[] = [];
  let shots = 0, meat = 0, spent = 0;
  const spawnThreshold = 2;
  for (let pass = 0; pass < SESSION_PASSES; pass++) {
    if (animals.length < MAX_ANIMALS && shots < MAX_SHOTS) {
      if ((h.below(1000) & 0xff) < spawnThreshold) {
        const kind = types[h.below(types.length)];
        const [low, span] = ANIMALS[kind];
        animals.push({ type: kind, still: 0, low, span });
      }
    }
    for (const a of animals) a.still += 1;
    while (animals.length && spent < bullets) {
      const hit = animals.find((a) => approximateMovement(a));
      if (!hit) break;
      animals.splice(animals.indexOf(hit), 1);
      spent += 1;
      shots += 1;
      meat += hit.low + h.below(hit.span);
      break;
    }
  }
  return { meat, bullets: bullets - spent, shots };
}

/** lines 4600 and HUNT.LIB 50000-50020 */
export async function go(c: Context): Promise<number> {
  const st = c.st;
  const bullets = N.asInt(st.I[4]);
  const before = st.PF;                         // Q = PF (line 50010)
  const gfx = c.ui.pictures;
  const S = c.ui.screens;
  const prefix = N.asInt(st.S) ? "b_oregon" : "oregon";
  if (gfx) await S.huntInstructions(c.ui, prefix);
  else {
    await c.ui.clear();
    await c.ui.print("Hunting Instructions");
    await c.ui.print();
    await c.ui.print("Return Key: to start or stop walking");
    await c.ui.print("Arrow Keys: to point the rifle");
    await c.ui.print("Space Bar: to fire the rifle");
  }
  await C.waitKey(c);
  let session: Session;
  if (bullets <= 0) session = { meat: 0, bullets: 0 };
  else if (gfx && HS.available((c.ui as any).assets)) {
    const h = new HuntRng(seedBytes(c));
    session = await HS.play(c.ui as any, (c.ui as any).assets.hunt(), bullets, h.below, allowedTypes(st.LM), ANIMALS,
      { getkey: (c.ui as any).huntKey });
  } else if (gfx) {
    const h = new HuntRng(seedBytes(c));
    session = await HF.play(c.ui as any, bullets, h.below, h.below, allowedTypes(st.LM), ANIMALS, SESSION_PASSES,
      { getkey: (c.ui as any).huntKey, pause: (c.ui as any).huntPause ?? 0 });
  } else session = huntSession(c, bullets);
  let got = N.parse(String(session.meat));
  // line 50011: L = INT (L / (2 - (L < 3))) -- a bag of three or more is halved
  got = N.int_(N.div(got, N.sub(N.TWO, N.bool_(N.lt(got, N.THREE)))));
  st.I[4] = N.parse(String(session.bullets));
  const said: string[] = [];
  const out = async (t: string) => { if (gfx) said.push(t); else await c.ui.print(t); };
  if (N.gt(got, N.ZERO)) {
    await out("From the animals you shot, you got " + N.str_(got) + " pound" + (N.eq(got, N.ONE) ? "" : "s") + " of meat.  ");
  }
  const full = !N.eq(got, N.ZERO) && N.ge(st.I[8], N.parse("2000"));
  if (full) {
    got = N.ZERO;                               // 50013 ends GOTO 50020
    await out("However, your wagon is full.");
  } else {
    if (!N.eq(got, N.ZERO) && N.gt(N.add(got, st.I[8]), N.parse("2000"))) {
      got = N.sub(N.parse("2000"), st.I[8]);
      if (!N.eq(got, N.ZERO) && N.le(got, N.parse(String(CARRY_LIMIT)))) {
        await out("However, your wagon will only hold another " + N.str_(got) + " pounds of food.");
      }
    }
    if (N.gt(got, N.parse(String(CARRY_LIMIT)))) {
      await out("However, you were only able to carry 100 pounds back to the wagon.");
      got = N.parse(String(CARRY_LIMIT));
    }
    if (N.eq(got, N.ZERO)) await out("You were unable to shoot any food.");
  }
  if (!gfx) await c.ui.print();
  st.I[8] = N.add(before, got);
  st.PF = st.I[8];
  if (gfx) await S.huntResult(c.ui, said.join(""), prefix);
  await C.waitKey(c);
  return N.asInt(got);
}
