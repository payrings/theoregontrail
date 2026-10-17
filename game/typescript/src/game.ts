/**
 * One whole game, the way `python -m oregon` plays it (the Python rebuild's __main__.py): the menu, the
 * store and the trail, or the preset start; then WIN. The self-playing summary lives here too, so the
 * seed comparisons can read the end of a game as one record.
 */
import * as N from "./num.js";
import * as D from "./data.js";
import { Context } from "./context.js";
import * as T from "./trail.js";
import * as menu from "./menu.js";
import * as buy from "./buysupplies.js";
import * as win from "./win.js";
import * as C from "./common.js";

/** the carpenter preset: skip all menus, set up the game state directly; it ends by loading the trail state */
export function applyPreset(c: Context): void {
  const mem = c.mem, st = c.st;
  mem.poke(901, 48, 9000);
  mem.poke(915, 2, 4030);
  mem.pokeWord(913, 800 * 10, 4030);
  st.MY = N.parse("800");
  st.N = ["Zeke", "Jed", "Anna", "Mary", "Joey"];
  st.NP = 5;
  mem.putNames(["Zeke", "Jed", "Anna", "Mary", "Joey"]);
  mem.poke(902, 4, 6030);
  mem.poke(903, 1, 6000);
  st.AM = N.parse("4"); st.AD = N.parse("1"); st.AY = N.parse("1848");
  mem.poke(905, 9, 405);
  mem.pokeWord(906, 2000, 530);
  mem.poke(908, 10, 610);
  mem.poke(909, 50, 700);
  mem.poke(910, 3, 811);
  mem.poke(911, 3, 811);
  mem.poke(912, 3, 811);
  mem.pokeWord(913, 50 * 10, 5010);
  T.loadState(c);                 // the preset loads the journey state, and main loads it again
}

/**
 * Play one game on `c` from the start. Returns where the journey ended ("WIN", "FLOAT", "DIED" or "MENU").
 * An Applesoft error is a defined outcome: the message, a key, and back to the menu (COMMON.LIB 32120).
 */
export async function playGame(c: Context, preset = false): Promise<string> {
  let where = "MENU";
  try {
    if (preset) applyPreset(c);
    else {
      // the order is the original's: MENU fixes the year and takes the profession and the names, then BUY SUPPLIES
      // asks the month and sells, then OREGON TRAIL reads the hand-over back out of memory and travels
      await menu.mainMenu(c);
      await buy.departureMonth(c);
      buy.initState(c);
      await buy.store(c);
    }
    T.loadState(c);
    where = await T.run(c);
    if (where === "WIN" || where === "FLOAT") await win.run(c);      // END.LIB 50050 has already written the hand-over
  } catch (err) {
    if (!(err instanceof N.ApplesoftError)) throw err;
    await C.errorHandler(c, err);
    c.outcome = `ERROR ${err.code}`;
    where = "MENU";
  }
  return where;
}

const round = (x: number, p: number) => Number(x.toFixed(p));

/** the state at the end of a self-played game, as one record (nothing in the game reads it) */
export function summary(c: Context, where: string): Record<string, unknown> {
  const st = c.st;
  const alive = Math.max(0, N.asInt(st.NP));
  const members: string[] = [];
  for (let i = 0; i < 5; i++) {
    if (i >= alive) members.push("dead");
    else {
      const h1 = N.asInt(st.H1[i]);
      members.push(h1 > 0 && h1 < D.IL_NAMES.length ? D.IL_NAMES[h1] : "healthy");
    }
  }
  const outcome = (c.outcome || "").split(" ").filter((s) => s);
  const arrived = outcome.length > 0 && outcome[0] === "ARRIVED";
  const health = N.asFloat(st.H);
  const lm = Math.trunc(st.LM);
  const said = c.ui.out;
  return {
    ending: arrived ? "ARRIVED" : alive <= 0 ? "DIED" : "UNFINISHED",
    route_end: where,
    score: arrived ? parseInt(outcome[1], 10) : 0,
    rating: arrived ? outcome.slice(2).join(" ") : "",
    days: c.trace.days,
    end_day: N.asInt(st.AD), end_month: N.asInt(st.AM), end_year: N.asInt(st.AY),
    miles: round(N.asFloat(st.M), 4),
    last_landmark: lm,
    last_landmark_name: lm >= 0 && lm < D.LM_NAMES.length ? D.LM_NAMES[lm] : "",
    survivors: alive,
    health: round(health, 6),
    health_class: alive ? D.HEALTH[Math.min(3, Math.max(0, Math.floor(health / 35)))] : "",
    members,
    sick_at_end: members.filter((m) => m !== "dead" && m !== "healthy").length,
    illnesses_during_game: said.filter((line) => D.IL_NAMES.some((n) => line.trimEnd().endsWith(" has " + n + "."))).length,
    oxen: round(N.asFloat(st.I[2]), 4), clothing: round(N.asFloat(st.I[3]), 4), bullets: round(N.asFloat(st.I[4]), 4),
    wheels: N.asInt(st.I[5]), axles: N.asInt(st.I[6]), tongues: N.asInt(st.I[7]),
    food: round(N.asFloat(st.I[8]), 4), money: round(N.asFloat(st.MY), 4),
  };
}
