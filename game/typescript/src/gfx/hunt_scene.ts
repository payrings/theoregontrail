/**
 * The hunting field, drawn from the sprites in hunt/hunt.json (the Python rebuild's graphics/hunt_scene.py).
 *
 * The sprites (the hunter's eight poses, the trees and grass, the animals) and the speeds were taken from
 * recordings of the original; they are MECC's pictures and live in the assets folder, not in the program.
 * What the program supplies is the rules:
 *  - Return starts and stops walking; the hunter walks the way he is facing, two dots across every eight
 *    ticks and one dot down every four (a tick is a sixtieth of a second);
 *  - the letter keys I O P / K ; / , . / point the rifle directly, the arrow keys turn it a step at a time,
 *    the space bar fires;
 *  - an animal appears from the paper's rule (the low byte of a draw from 0 to 999 below 2, room for it,
 *    fewer than four shots), crosses the field, and is shot if a bullet touches it; it then lies where it fell.
 * Not taken from the original (the movement was only watched): how the animals choose their paths, the speed
 * of the bullet and the length of the hunt (25 seconds, as in the recordings).
 */
import { H, W } from "./canvas.js";
import { clockOf, type Clock } from "./clock.js";
import { fillRect } from "./image.js";

const POSES = ["UL", "U", "UR", "R", "DR", "D", "DL", "L"];            // clockwise
const LETTERS: Record<string, string> = { i: "UL", o: "U", p: "UR", ";": "R", "/": "DR", ".": "D", ",": "DL", k: "L" };
const LEFT = "\x1c", UP = "\x1e", RIGHT = "\x1d", DOWN = "\x1f";
const VEC: Record<string, [number, number]> = { UL: [-1, -1], U: [0, -1], UR: [1, -1], R: [1, 0], DR: [1, 1], D: [0, 1], DL: [-1, 1], L: [-1, 0] };
const KIND: Record<number, string> = { 0: "deer", 1: "deer", 2: "bison", 3: "deer", 4: "rabbit", 5: "squirrel" };
const FRAME_TICKS: Record<string, number> = { rabbit: 4, squirrel: 3, deer: 4, bison: 8 };
export const TICKS = 60;                  // per second
export const HUNT_TICKS = 1500;           // 25 seconds

export interface HuntResult { meat: number; bullets: number; shots: number }
export interface PlayOptions { passes?: number; getkey?: (() => string | null) | null; live?: boolean; clock?: Clock }

export const available = (assets: any): boolean => !!(assets && typeof assets.hunt === "function" && assets.hunt());

/** the lit dots of a sprite, as canvas keys, in reading order */
function lit(rows: string[], x: number, y: number): [number, number][] {
  const out: [number, number][] = [];
  rows.forEach((row, r) => { for (let c = 0; c < row.length; c++) if (row[c] !== "." && x + c >= 0 && x + c < W && y + r >= 0 && y + r < H) out.push([x + c, y + r]); });
  return out;
}
const size = (rows: string[]): [number, number] => [rows.length ? rows[0].length : 0, rows.length];
const addDots = (dots: Set<number>, pts: [number, number][]): void => { for (const [x, y] of pts) dots.add(y * W + x); };

/** three or four trees and two or three tufts of grass, each on the 14-dot grid its picture was drawn on */
function scenery(data: any, below: (n: number) => number): [string, number, number][] {
  const trees = data.scenery.filter((s: any) => s.kind === "tree");
  const grass = data.scenery.filter((s: any) => s.kind === "grass");
  const out: [string, number, number][] = [];
  // both counts are drawn before either kind is placed, as the Python tuple evaluates them
  const plan: [any[], number, number, number][] = [[trees, 3 + below(2), 0, 125], [grass, 2 + below(2), 30, 140]];
  for (const [pool, n, ytop, yspan] of plan) {
    for (let i = 0; i < n; i++) {
      const s = pool[below(pool.length)];
      const x = 14 * below(19) + s.k - 14;
      out.push([s.image, x, ytop + below(yspan)]);
    }
  }
  return out;
}

function frameOf(data: any, a: any): string[] {
  const frames = data.animals[a.kind][a.dir > 0 ? "R" : "L"];
  return frames[Math.floor(a.n / FRAME_TICKS[a.kind]) % frames.length];
}

/** where it fell: the deer's own picture, or the animal turned over */
function corpse(data: any, a: any, rows: string[]): [number, number, string[]] {
  rows = a.kind === "deer" && data.lying?.deer ? data.lying.deer.rows : rows.slice().reverse();
  return [Math.trunc(a.x), Math.trunc(a.y), rows];
}

const touches = (rows: string[], c: number, r: number): boolean => r >= 0 && r < rows.length && c >= 0 && c < rows[r].length && rows[r][c] !== ".";

/**
 * Run one hunt. `below(n)` is the hunting module's own generator and `weights` its table of (lowest
 * weight, span) per animal type.
 */
export async function play(ui: any, data: any, bullets: number, below: (n: number) => number, types: number[],
                           weights: [number, number][], opts: PlayOptions = {}): Promise<HuntResult> {
  const passes = opts.passes ?? HUNT_TICKS;
  const cv = ui.cv;
  const clock = opts.clock ?? clockOf(ui);
  const getkey = opts.getkey ?? (() => ui.backend.poll());
  const live: boolean = opts.live ?? (ui.dailyPause > 0);
  const hunter = data.hunter;
  let pose = POSES[below(8)];
  let hx = 61 + 2 * below(70), hy = 20 + below(90);                    // odd, as the sprite's colours need
  let walking = false;
  let px = 0, py = 0;                                                  // tick counters for walking
  const scene = scenery(data, below);
  let animals: any[] = [];
  const dead: [number, number, string[]][] = [];
  let shots = 0, meat = 0, left = bullets;
  let bullet: { x: number; y: number; vx: number; vy: number } | null = null;
  const t0 = clock.now();
  let idle = 0;

  const bbox = (): [number, number, number, number] => {
    const h = hunter[pose];
    const [w, hh] = size(h.rows);
    return [hx + h.dx, hy + h.dy, w, hh];
  };

  for (let tick = 0; tick < passes + 6 * scene.length; tick++) {
    const revealed = Math.min(scene.length, Math.floor(tick / 6));
    const building = tick < 6 * scene.length;
    const k = getkey();
    if (!building) {
      if (k === "\r") walking = !walking;
      else if (k && k.toLowerCase() in LETTERS) pose = LETTERS[k.toLowerCase()];
      else if (k === LEFT || k === UP) pose = POSES[(POSES.indexOf(pose) + 7) % 8];
      else if (k === RIGHT || k === DOWN) pose = POSES[(POSES.indexOf(pose) + 1) % 8];
      else if (k === " " && left > 0 && shots < 4 && bullet === null) {
        left -= 1;
        const [vx, vy] = VEC[pose];
        const dots = lit(hunter[pose].rows, hx + hunter[pose].dx, hy + hunter[pose].dy);
        // the tip: furthest along the aim, then nearest the rifle's height (first such dot on a tie)
        let tip = dots[0], best: [number, number] | null = null;
        for (const p of dots) {
          const key: [number, number] = [p[0] * vx + p[1] * vy, -Math.abs(p[1] - hy - 8)];
          if (best === null || key[0] > best[0] || (key[0] === best[0] && key[1] > best[1])) { best = key; tip = p; }
        }
        bullet = { x: tip[0] + vx, y: tip[1] + vy, vx, vy };
      }
      // walking: two dots across every eight ticks, one dot down every four
      if (walking) {
        const [vx, vy] = VEC[pose];
        px += 1; py += 1;
        const [x0, y0, w, h] = bbox();
        if (vx && px % 8 === 0 && 6 <= x0 + 2 * vx && x0 + w + 2 * vx <= W) hx += 2 * vx;
        if (vy && py % 4 === 0 && 8 <= y0 + vy && y0 + h + vy <= 168) hy += vy;
      }
      // a new animal
      if (animals.length < 2 && shots < 4) {
        if ((below(1000) & 0xff) < 2) {
          const typ = types[below(types.length)];
          const kind = KIND[typ];
          const d = below(2) === 0 ? 1 : -1;
          const frames = data.animals[kind][d > 0 ? "R" : "L"];
          const [w] = size(frames[0]);
          const ay = 24 + below(130);
          const vy = (below(3) - 1) * 0.12;
          animals.push({ type: typ, kind, dir: d, n: 0, x: d > 0 ? -w : W, y: ay, vy, v: data.speed[kind] / TICKS });
        }
      }
      for (const a of animals.slice()) {
        a.x += a.dir * a.v; a.y += a.vy; a.n += 1;
        if (a.x < -40 || a.x > W + 20 || a.y < 0 || a.y > 175) animals.splice(animals.indexOf(a), 1);
      }
      // the bullet: four dots across and two down a tick, stopped by the first animal it touches
      if (bullet) {
        for (let step = 0; step < 2; step++) {
          bullet.x += 2 * bullet.vx;
          bullet.y += bullet.vy;
          const bx = Math.trunc(bullet.x), by = Math.trunc(bullet.y);
          if (!(-2 <= bx && bx < W + 2 && -2 <= by && by < H + 2)) { bullet = null; break; }
          for (const a of animals) {
            const rows = frameOf(data, a);
            const ax = Math.trunc(a.x), ay = Math.trunc(a.y);
            let hit = false;
            for (let dx = -1; dx <= 1 && !hit; dx++) for (let dy = -1; dy <= 1 && !hit; dy++) hit = touches(rows, bx - ax + dx, by - ay + dy);
            if (hit) {
              animals.splice(animals.indexOf(a), 1);
              shots += 1;
              const [low, span] = weights[a.type];
              meat += low + below(span);
              dead.push(corpse(data, a, rows));
              bullet = null;
              break;
            }
          }
          if (bullet === null) break;
        }
      }
      if (left === 0 && bullet === null) { idle += 1; if (idle > 90) break; }
      if (tick >= passes) break;
    }
    // draw
    if (live) {
      const due = t0 + tick / TICKS;
      const now = clock.now();
      if (now < due) await clock.sleep(due - now);
      else if (now - due > 0.05) continue;                              // behind: skip the picture, keep the rules
    } else if (tick % 60 !== 0 && tick !== passes - 1) continue;
    cv.clear();
    cv.backdrop("hunt", 0, 0);
    for (const [name, sx, sy] of scene.slice(0, revealed)) cv.image(name, sx, sy);
    if (!building) {
      const colours = cv.plain ? data.colours : null;                   // themed: coloured sprites
      if (colours) {
        const pal: Record<string, number[]> = {};
        for (const [key, v] of Object.entries<any>(colours.palette)) pal[key] = v;
        for (const [x, y, rows] of dead) cv.paintRows(rows, x, y, pal);
        for (const a of animals) cv.paintRows(frameOf(data, a), Math.trunc(a.x), Math.trunc(a.y), pal);
        if (bullet) {
          const bx = Math.trunc(bullet.x), by = Math.trunc(bullet.y);
          fillRect(cv.base, Math.max(0, bx), Math.max(0, by), Math.min(W, bx + 2), Math.min(H, by + 1), colours.bullet);
        }
        const h = hunter[pose];
        cv.paintRows(h.rows, hx + h.dx, hy + h.dy, pal);
      } else {
        for (const [x, y, rows] of dead) addDots(cv.dots, lit(rows, x, y));
        for (const a of animals) addDots(cv.dots, lit(frameOf(data, a), Math.trunc(a.x), Math.trunc(a.y)));
        if (bullet) {
          const bx = Math.trunc(bullet.x), by = Math.trunc(bullet.y);
          addDots(cv.dots, ([[bx, by], [bx + 1, by]] as [number, number][]).filter((p) => p[0] >= 0 && p[0] < W && p[1] >= 0 && p[1] < H));
        }
        const h = hunter[pose];
        addDots(cv.dots, lit(h.rows, hx + h.dx, hy + h.dy));
      }
    }
    ui.refresh();
  }
  return { meat, bullets: left, shots };
}
