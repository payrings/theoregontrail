/**
 * Plays whole games by itself, as `python -m oregon --demo` does, and writes the day-by-day trace and a
 * one-line JSON summary.
 *
 *   node dist/cli.js [--num exact|rounded|float] [--preset] [--wander] SEED [TRACE_FILE]
 *   node dist/cli.js ... --range FIRST LAST            tally of endings
 *   node dist/cli.js ... --digest FIRST LAST [STEP]    one line per seed, for the comparison scripts
 *
 * Without --preset the game starts at the menu, buys its supplies at Matt's store and sets out. --wander
 * also uses the pace and rations screens, rests, trades, talks, hunts, shops at forts and rafts.
 */
import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import * as N from "./num.js";
import { Context } from "./context.js";
import { AutoUI } from "./ui.js";
import { playGame, summary } from "./game.js";
import * as dialogue from "./dialogue.js";

function flag(name: string): boolean {
  const at = process.argv.indexOf(name);
  if (at < 0) return false;
  process.argv.splice(at, 1);
  return true;
}
function option(name: string): string | null {
  const at = process.argv.indexOf(name);
  if (at < 0) return null;
  const v = process.argv[at + 1];
  process.argv.splice(at, 2);
  return v;
}

const num = option("--num");
if (num) N.use(num);
const preset = flag("--preset");
const wander = flag("--wander");
const showScreen = flag("--screen");

/** talking to people needs the dialogue document: data/dialogue.md, or the one named by --dialogue or OREGON_DIALOGUE */
{
  const given = option("--dialogue");
  const candidates = [given, process.env.OREGON_DIALOGUE, "data/dialogue.md", "game/typescript/data/dialogue.md"];   // the last two: run from here, or from the repository root
  for (const p of candidates) if (p && existsSync(p)) { dialogue.setSource(readFileSync(p, "utf8")); break; }
}

async function play(seed: number): Promise<{ c: Context; summary: Record<string, unknown> }> {
  const c = new Context(new AutoUI(wander));
  c.rng.seedFromKeyboard(seed);
  // the menu reseeds from the keyboard counter (MENU 1015), which a script never advances; holding it at the
  // seed makes that reseed the same seed
  c.mem.keyboardCounter = seed;
  const where = await playGame(c, preset);
  return { c, summary: summary(c, where) };
}

async function main(): Promise<void> {
  if (process.argv[2] === "--digest") {
    // one line per seed, "D <seed> <summary json> <sha1 of the trace>"
    const first = Number(process.argv[3]), last = Number(process.argv[4]), step = Number(process.argv[5] || 1);
    for (let s = first; s <= last; s += step) {
      try {
        const { c, summary: sm } = await play(s);
        const sha = createHash("sha1").update(c.trace.lines.join("\n")).digest("hex");
        console.log("D " + s + " " + JSON.stringify(sm) + " " + sha);
      } catch (err) { console.log("E " + s + " " + (err as Error).message.slice(0, 120)); }
    }
  } else if (process.argv[2] === "--range") {
    const first = Number(process.argv[3]), last = Number(process.argv[4]);
    const tally: Record<string, number> = {};
    let failed = 0;
    for (let s = first; s <= last; s++) {
      try {
        const { summary: sm } = await play(s);
        const key = String(sm.ending);
        tally[key] = (tally[key] || 0) + 1;
      } catch (err) { failed += 1; console.log(`seed ${s}: ${(err as Error).message.slice(0, 120)}`); }
    }
    console.log(`seeds ${first}-${last}:`, JSON.stringify(tally), failed ? `${failed} failed` : "none failed");
  } else {
    const seed = Number(process.argv[2]);
    const traceFile = process.argv[3];
    try {
      const { c, summary: s } = await play(seed);
      if (showScreen) console.log(c.ui.out.join("\n"));
      if (traceFile) writeFileSync(traceFile, c.trace.lines.join("\n") + (c.trace.lines.length ? "\n" : ""));
      console.log("SUMMARY " + JSON.stringify({ seed, ...s, final_seed_bytes: c.trace.lines.length ? c.trace.lines[c.trace.lines.length - 1].split(" ").pop() : "" }));
    } catch (err) {
      console.log("ERROR " + JSON.stringify({ seed, error: String((err as Error).message).slice(0, 200) }));
    }
  }
}
main();
