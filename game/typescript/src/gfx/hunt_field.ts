/**
 * The hunting field for the graphical mode when the assets folder has no hunt sprites (the Python
 * rebuild's graphics/hunt_field.py).
 *
 * A stand-in. The original draws the field and moves the animals in machine code the paper did not
 * analyse, so this field, its hunter and its animals are plain shapes, and the movement and the aim are
 * a plausible game of my own. What is the paper's: the keys, the spawn rule, which animals may appear at
 * each landmark, the weights, at most two animals on the screen and four shots, and 2,500 passes.
 */
import { clockOf, type Clock } from "./clock.js";

export const ARROWS: Record<string, string> = { Up: "\x1e", Down: "\x1f", Left: "\x1c", Right: "\x1d" };
const UP = "\x1e", DOWN = "\x1f", LEFT = "\x1c", RIGHT = "\x1d";

const HUNTER: [number, number] = [140, 165];
const GROUND_TOP = 55, GROUND_BOTTOM = 175;
/** type -> [colour, width, height, legs]: bigger weights, bigger animals */
const LOOK: Record<number, [number, number, number, number]> = { 0: [2, 12, 6, 2], 1: [3, 15, 8, 2], 2: [5, 22, 11, 2], 3: [3, 12, 6, 2], 4: [3, 5, 3, 0], 5: [5, 4, 3, 0] };
const SPEED: Record<number, number> = { 0: 2, 1: 2, 2: 1, 3: 3, 4: 3, 5: 2 };

interface Animal { type: number; dir: number; x: number; y: number; v: number }
interface Field { animals: Animal[]; bullets: number; shots: number; aim: number; walking: boolean; scroll: number; trees: number[] }

const mod = (a: number, n: number): number => ((a % n) + n) % n;

function drawAnimal(cv: any, a: Animal): void {
  const [colour, w, h, legs] = LOOK[a.type];
  const x = Math.trunc(a.x), y = Math.trunc(a.y);
  cv.box(x, y, x + w - 1, y + h - 1, colour);                           // body
  const head = Math.max(2, Math.floor(h / 2));
  const hx = a.dir > 0 ? x + w : x - head;
  cv.box(hx, y - 1, hx + head - 1, y + head - 2, colour);               // head
  for (let k = 0; k < legs; k++) { const lx = x + 2 + k * (w - 5); cv.box(lx, y + h, lx + 1, y + h + 2, colour); }
}

function drawTree(cv: any, x: number, y: number): void {
  cv.box(x + 3, y + 8, x + 4, y + 16, 5);                               // trunk
  cv.box(x, y, x + 7, y + 8, 1);                                        // leaves
}

function draw(ui: any, st: Field): void {
  const cv = ui.cv;
  ui.clear();
  cv.box(0, GROUND_TOP, 279, GROUND_BOTTOM, 1);
  for (const tx of st.trees) {
    const sx = mod(tx - st.scroll, 320) - 20;
    if (-8 < sx && sx < 280) drawTree(cv, sx, GROUND_TOP - 12);
  }
  for (const a of st.animals) drawAnimal(cv, a);
  const [hx, hy] = HUNTER;
  cv.box(hx - 2, hy - 8, hx + 2, hy, 3);                                // the hunter
  cv.box(hx - 1, hy - 12, hx + 1, hy - 9, 5);
  const ang = st.aim * Math.PI / 8;
  const ex = hx + Math.trunc(30 * Math.sin(ang)), ey = hy - 6 - Math.trunc(30 * Math.cos(ang));
  cv.line(hx, hy - 6, ex, ey, 3);                                       // the rifle
  ui.dfw(0, 0, 280, 192);
  ui.co(0, 181);
  ui.put(`Bullets: ${st.bullets}  Shot: ${st.shots}  ` + (st.walking ? "Walking" : "Standing"));
}

/** does the shot along the rifle's line pass through this animal? */
function hit(st: Field, a: Animal): boolean {
  const [, w, h] = LOOK[a.type];
  const [hx, hy] = HUNTER;
  const ang = st.aim * Math.PI / 8;
  const dx = Math.sin(ang), dy = -Math.cos(ang);
  const cx = a.x + w / 2 - hx, cy = a.y + h / 2 - (hy - 6);
  const along = cx * dx + cy * dy;
  if (along <= 0) return false;
  const across = Math.abs(cx * dy - cy * dx);
  return across <= Math.max(w, h) / 2 + 2;
}

export interface FieldOptions { getkey?: (() => string | null) | null; pause?: number; clock?: Clock }

/** run one hunt on the screen; `spawnDraw` and `kindDraw` are the hunting module's own generator */
export async function play(ui: any, bullets: number, spawnDraw: (n: number) => number, kindDraw: (n: number) => number,
                           types: number[], weights: [number, number][], passes = 2500, opts: FieldOptions = {}): Promise<{ meat: number; bullets: number; shots: number }> {
  const getkey = opts.getkey ?? (() => ui.backend.poll());
  const pause = opts.pause ?? 0.02;
  const clock = opts.clock ?? clockOf(ui);
  const st: Field = { animals: [], bullets, shots: 0, aim: 0, walking: false, scroll: 0, trees: [12, 70, 131, 188, 247, 301] };
  let meat = 0;
  for (let n = 0; n < passes; n++) {
    const k = getkey();
    let fired = false;
    if (k === "\r") st.walking = !st.walking;
    else if (k === LEFT || k === UP) st.aim = mod(st.aim - 1, 16);
    else if (k === RIGHT || k === DOWN) st.aim = mod(st.aim + 1, 16);
    else if (k === " " && st.bullets > 0 && st.shots < 4) {
      st.bullets -= 1;
      fired = true;
      const h = st.animals.find((a) => hit(st, a));
      if (h) {
        st.animals.splice(st.animals.indexOf(h), 1);
        st.shots += 1;
        const [low, span] = weights[h.type];
        meat += low + kindDraw(span);
      }
    }
    // the paper's spawn rule: the low byte of a draw 0-999 below 2, room for another
    if (st.animals.length < 2 && st.shots < 4) {
      if ((spawnDraw(1000) & 0xff) < 2) {
        const kind = types[spawnDraw(types.length)];
        const side = spawnDraw(2);
        const y = GROUND_TOP + 8 + spawnDraw(GROUND_BOTTOM - GROUND_TOP - 45);
        st.animals.push({ type: kind, dir: side === 0 ? 1 : -1, x: side === 0 ? -20 : 285, y, v: 1 + spawnDraw(SPEED[kind]) });
      }
    }
    if (st.walking) st.scroll += 1;
    for (const a of st.animals.slice()) {
      a.x += a.dir * a.v * (n % 2 ? 1 : 0) - (st.walking ? 1 : 0);
      if (a.x < -30 || a.x > 310) st.animals.splice(st.animals.indexOf(a), 1);
    }
    if (pause > 0 && n % 2 === 0) { draw(ui, st); ui.refresh(); }
    if (fired && (st.bullets === 0 || st.shots >= 4)) {
      if (pause > 0) await clock.sleep(0.8);                            // the last shot is seen before it ends
      break;
    }
    if (pause > 0) await clock.sleep(pause);
  }
  return { meat, bullets: st.bullets, shots: st.shots };
}
