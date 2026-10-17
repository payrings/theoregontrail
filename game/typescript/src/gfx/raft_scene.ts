/**
 * The Columbia River raft, drawn from the pictures in the assets folder (the Python rebuild's
 * graphics/raft_scene.py). The river (b_river), the raft, the rocks and the direction signs are MECC's
 * pictures and are read from the folder the player chooses. Positions are the listing's (line 1110 for the
 * raft) or were measured on a recording:
 *  - the raft's picture is drawn at (84 + 8 * hp + 3, 5 * hp - 6);
 *  - a rock's picture is drawn at (RX + 7, RY);
 *  - a direction sign enters at the bottom of the river, at (114, 168), and moves six dots right and three
 *    up a pass for twenty-two passes.
 * Measured, not in the listing: a pass of the loop takes about 0.45 s on the original (this game runs it
 * twice as fast), and the signs appear on the passes the listing names, 60, 120 and 170.
 */
export const SIGN_START: [number, number] = [114, 168];
export const SIGN_STEP: [number, number] = [6, -3];
export const SIGN_STEPS = 23;
export const PASS_SECONDS = 0.225;           // twice the original's pace

/** the arrival point -- FLOAT 1146 and 1149: it comes up the river from the bottom left and crosses the landing bank near passes 205 to 225 */
export const LANDING_PASS = 175;
export const LANDING_START: [number, number] = [-8, 218];

export function available(ui: any): boolean {
  const a = ui?.assets;
  return !!(a && a.image("float_raft") && a.image("float_rock") && a.screen("b_river"));
}

export function signPosition(passesSinceStart: number): [number, number] | null {
  if (passesSinceStart >= 0 && passesSinceStart < SIGN_STEPS) return [SIGN_START[0] + SIGN_STEP[0] * passesSinceStart, SIGN_START[1] + SIGN_STEP[1] * passesSinceStart];
  return null;
}

/** where the arrival point is `passesSinceStart` passes after pass 175, or null once it has left the screen */
export function landingPosition(passesSinceStart: number): [number, number] | null {
  if (passesSinceStart < 0) return null;
  const x = LANDING_START[0] + SIGN_STEP[0] * passesSinceStart, y = LANDING_START[1] + SIGN_STEP[1] * passesSinceStart;
  return x < 280 && y > -22 ? [x, y] : null;
}

/** one picture of the river: `rocks` are [RX, RY] pairs, `signs` the positions */
export function draw(ui: any, hp: number, rocks: number[][], signs: ([number, number] | null)[] = [], landing: [number, number] | null = null): void {
  const cv = ui.cv;
  cv.clear();
  cv.screen("b_river");
  for (const [rx, ry] of rocks) cv.image("float_rock", rx + 7, ry);
  for (const s of signs) if (s) cv.image("float_sign", s[0], s[1]);
  if (landing !== null) cv.image(ui.assets.image("float_landing") ? "float_landing" : "float_sign", landing[0], landing[1]);
  cv.image("float_raft", 84 + 8 * hp + 3, 5 * hp - 6);
  ui.refresh();
}
