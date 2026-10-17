/** MENU (side 1) and MANAGEMENT: the title screen, the profession, the names and the top ten. */
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import { ALLOWED } from "./ui.js";
import type { HiscoreEntry } from "./files.js";

export const VERSION = "Version 1.4";
const S = (c: Context): any => c.ui.screens;

/** lines 1000-1020: the four choices, and the reseed that follows each */
export async function mainMenu(c: Context): Promise<string> {
  for (;;) {
    c.setProgram("MENU");
    if (c.ui.pictures) await S(c).title(c.ui, D.SOUND_WORDS[c.mem.peek(975) ? 0 : 1]);
    else {
      await c.ui.clear();
      await c.ui.print("The Oregon Trail");
      await c.ui.print(VERSION);
      await c.ui.print();
      await c.ui.print("You may:");
      await c.ui.print();
      await c.ui.print("  1. Travel the trail");
      await c.ui.print("  2. Learn about the trail");
      await c.ui.print("  3. See the Oregon Top Ten");
      await c.ui.print("  4. Turn sound " + D.SOUND_WORDS[c.mem.peek(975) ? 0 : 1]);
      await c.ui.print();
      await c.ui.print("What is your choice? ");
    }
    const a = (await c.ui.key(ALLOWED.CHOICE, 1)) as string;
    if (!a) continue;
    // The allowed set is CHR$(1) + "-14", so the answer is a character code: the teacher menu is opened by
    // the literal character 1 (Control-A), not by the digit 1.
    const code = a.charCodeAt(0);
    // Z = RND(-(PEEK(78) + PEEK(79) * 256)) -- the only reseeding in the game
    c.rng.seedFromKeyboard(c.mem.keyboardCounter);
    if (code === 1) {
      c.setProgram("MANAGEMENT");
      await c.ui.print("Getting Management Options...");
      await management(c);
      continue;
    }
    const digit = code - 48;
    if (digit === 2) await learn(c);
    else if (digit === 3) await topTen(c);
    else if (digit === 4) await toggleSound(c);
    else { await start(c); return "BUY SUPPLIES"; }
  }
}

/** line 2300: POKE 975, NOT PEEK(975) */
async function toggleSound(c: Context): Promise<void> {
  const on = c.mem.peek(975) ? 0 : 1;
  c.mem.poke(975, on);
  if (c.ui.pictures) await S(c).sound(c.ui, D.SOUND_WORDS[on]);
  else {
    await c.ui.clear();
    await c.ui.print("The sound is now turned " + D.SOUND_WORDS[on] + ".");
    await c.ui.print();
    await c.ui.print("You may turn the sound on or off during the program by pressing Control-S.");
  }
  await C.waitKey(c);
}

/** lines 4000-4030: be a banker, a carpenter or a farmer */
export async function profession(c: Context): Promise<number> {
  for (;;) {
    await c.ui.clear();
    await c.ui.print("Many kinds of people made the trip to Oregon.");
    await c.ui.print();
    await c.ui.print("You may:");
    await c.ui.print("1. Be a " + D.PROFESSIONS[0]);
    await c.ui.print("2. Be a " + D.PROFESSIONS[1]);
    await c.ui.print("3. Be a " + D.PROFESSIONS[2]);
    await c.ui.print("4. Find out the differences between these choices");
    await c.ui.print();
    await c.ui.print("What is your choice? ");
    const a = (await c.ui.key(ALLOWED.PROFESSION, 1)) as string;
    const z = /^\d+$/.test(a) ? parseInt(a, 10) : 0;
    if (z === 4) { await difficultyText(c); continue; }
    if (z >= 1 && z <= 3) {
      c.mem.poke(915, z, 4030);
      const dollars = [1600, 800, 400][z - 1];
      c.mem.pokeWord(913, dollars * 10, 4030);
      return z;
    }
  }
}

async function difficultyText(c: Context): Promise<void> {
  await c.ui.clear();
  await c.ui.print("Traveling to Oregon isn't easy!  But if you're a banker, you'll have more money for supplies and services than a carpenter or a farmer.");
  await c.ui.print();
  await c.ui.print("However, the harder you have to try, the more points you deserve!  Therefore, the farmer earns the greatest number of points and the banker earns the least.");
  await C.waitKey(c);
}

/** lines 6000-6015: the ten default names into random order (ten draws, always) */
export function shuffleNames(c: Context): string[] {
  const names: string[] = new Array(10).fill("");
  for (let k = 0; k < 10; k++) {
    let z = c.rng.intRange("MENU 6000 name slot", 10);
    while (names[z]) { z += 1; z = z < 10 ? z : 0; }
    names[z] = D.DEFAULT_NAMES[k];
  }
  return names;
}

/** lines 6015-6045: the five names, confirmed and written to memory */
export async function partyNames(c: Context, defaults?: string[]): Promise<string[]> {
  const pool = defaults ? [...defaults] : shuffleNames(c);
  const n = pool.slice(0, 5);
  const gfx = c.ui.pictures;
  if (gfx) await S(c).namesLeader(c.ui);
  else { await c.ui.clear(); await c.ui.print("What is the first name of the wagon leader? "); }
  let typed = (await c.ui.key(ALLOWED.NAMES, 9)) as string;
  n[0] = typed || n[0];
  if (gfx) await S(c).namesOthers(c.ui, n[0]);
  else {
    await c.ui.print();
    await c.ui.print("What are the first names of the four other members in your party? ");
    await c.ui.print();
    await c.ui.print("(Enter names or press Return)");
  }
  // a blank keeps the default *and stops the asking*
  for (let i = 1; i < 5; i++) {
    if (gfx) await S(c).namesCursor(c.ui, i);
    typed = (await c.ui.key(ALLOWED.NAMES, 9, "")) as string;
    if (!typed) break;
    n[i] = typed;
  }
  for (;;) {
    if (gfx) await S(c).namesConfirm(c.ui, n);
    else {
      await c.ui.print();
      for (let i = 0; i < 5; i++) await c.ui.print(`${i + 1}. ${n[i]}`);
      await c.ui.print();
      await c.ui.print("Are these names correct? ");
    }
    if ((await C.yesNo(c)) === "Y") break;
    c.ui.box?.(0, 183, 279, 191);           // line 6041 draws over line 6040's prompt
    c.ui.at?.(0, 81);
    await c.ui.print("Change which name? ");
    const a = (await c.ui.key(ALLOWED.MANAGE, 1)) as string;
    const which = /^\d+$/.test(a) ? parseInt(a, 10) - 1 : 0;
    if (which >= 0 && which <= 4) {
      await c.ui.print(" ");
      typed = (await c.ui.key(ALLOWED.NAMES, 9)) as string;
      if (typed) n[which] = typed;
    }
  }
  c.mem.putNames(n, 6045);
  return n;
}

// ------------------------------------------------------------------ top ten
export function readTopTen(c: Context): HiscoreEntry[] {
  if (!c.hiscore) {
    let entries = c.files.readHiscore();
    if (!entries.length) { entries = D.originalTopTen(); c.files.writeHiscore(entries); }
    c.hiscore = entries;
  }
  return c.hiscore;
}

/** line 2005: the list, then the offer to explain the points */
export async function topTen(c: Context, entries?: HiscoreEntry[], ratingOnly = false): Promise<void> {
  entries = entries ?? readTopTen(c);
  if (c.ui.pictures) {
    const y = await S(c).topTen(c.ui, entries);
    if (!ratingOnly) {
      await S(c).box41000(c.ui, "Would you like to see how points are earned? ", 20, y, 240, y + 30);   // 2015
      if ((await C.yesNo(c)) === "Y") await howPoints(c);
    }
    return;
  }
  await c.ui.clear();
  await c.ui.print("Name".padEnd(16) + "Points".padStart(8) + "Rating");
  await c.ui.print();
  for (const [name, points, rating] of entries.slice(0, 10)) {
    await c.ui.print(String(name).slice(0, 16).padEnd(16) + String(points).padStart(8) + "  " + String(rating));
  }
  await c.ui.print();
  if (!ratingOnly) {
    await c.ui.print("Would you like to see how points are earned? ");
    if ((await C.yesNo(c)) === "Y") await howPoints(c);
  }
}

/** lines 2200-2235: the three explanation screens */
async function howPoints(c: Context): Promise<void> {
  if (c.ui.pictures) {
    for (let page = 0; page < 3; page++) { await S(c).howPoints(c.ui, page, D.SCORE_TEXT); await C.waitKey(c); }
    return;
  }
  await c.ui.clear();
  await c.ui.print("Your most important resource is the people you have with you.  You receive points for each member of your party who arrives safely; you receive more points if they arrive in good health!");
  await c.ui.print();
  await c.ui.print("Health of        Points per");
  await c.ui.print("  Party             Person");
  for (const [word, points] of D.SCORE_TEXT.slice(0, 4)) await c.ui.print(`  ${word.padEnd(18)}${points}`);
  await C.waitKey(c);
  await c.ui.clear();
  await c.ui.print("The resources you arrive with will help you get started in the new land.  You receive points for each item you bring safely to Oregon.");
  await c.ui.print();
  await c.ui.print("Resources of        Points per");
  await c.ui.print("   Party               Item");
  for (const [word, points] of D.SCORE_TEXT.slice(4)) {
    const at = word.indexOf(" (each ");
    const unit = at >= 0 ? word.slice(0, at) : word;
    await c.ui.print(`   ${unit.padEnd(20)}${points}`);
  }
  await C.waitKey(c);
  await c.ui.clear();
  await c.ui.print("You receive points for your occupation in the new land.  Because more farmers and carpenters were needed than bankers, you receive double points upon arriving in Oregon as a carpenter, and triple points for arriving as a farmer.");
  await C.waitKey(c);
}

// --------------------------------------------------------------------- learn
const LEARN = [
  "Try taking a journey by covered wagon across 2000 miles of plains, rivers, and mountains.  Try!  On the plains, will you slosh your oxen through mud and water-filled ruts or will you plod through dust six inches deep?",
  "How will you cross the rivers?  If you have money, you might take a ferry (if there is a ferry).  Or, you can ford the river and hope you and your wagon aren't swallowed alive!",
  "What about supplies?  Well, if you're low on food you can hunt.  You might get a buffalo...you might.  And there are bear in the mountains.",
  "At the Dalles, you can try navigating the Columbia River, but if running the rapids with a makeshift raft makes you queasy, better take the Barlow Road.",
];
const LEARN_LAST = "If for some reason you don't survive -- your wagon burns, or thieves steal your oxen, or you run out of provisions, or you die of cholera -- don't give up!  Try again...and again...until your name is up with the others on The Oregon Top Ten.";

/** lines 7000-7041: the four screens that explain the journey */
async function learn(c: Context): Promise<void> {
  for (let n = 0; n < LEARN.length; n++) {
    if (c.ui.pictures) await S(c).info(c.ui, LEARN[n], n === 0);
    else { await c.ui.clear(); await c.ui.print(LEARN[n]); }
    await C.waitKey(c);
  }
  if (c.ui.pictures) await S(c).info(c.ui, LEARN_LAST);
  else await c.ui.print(LEARN_LAST);
  await C.waitKey(c);
  if (c.ui.pictures) {
    await S(c).colours(c.ui);
    await C.waitKey(c);
    await S(c).controlS(c.ui);
    await C.waitKey(c);
  }
}

/** line 9000: fix the year, take the profession and the names, hand over */
async function start(c: Context): Promise<void> {
  c.setProgram("MENU");
  c.mem.poke(901, 48, 9000);
  await profession(c);
  const n = await partyNames(c);
  for (let i = 0; i < 5; i++) c.st.N[i] = n[i];
  c.st.NP = 5;
  await c.ui.print();
  await c.ui.print(`Going back to 18${c.mem.peek(901)}...`);
  await C.waitKey(c);
}

// ----------------------------------------------------------------- MANAGEMENT
/** lines 1000-1015: the teacher menu */
async function management(c: Context): Promise<void> {
  for (;;) {
    c.setProgram("MANAGEMENT");
    if (c.ui.pictures) await S(c).management(c.ui, D.MANAGE_OPTIONS, VERSION);
    else {
      await c.ui.clear();
      await c.ui.print("The Oregon Trail");
      await c.ui.print(VERSION);
      await c.ui.print();
      await c.ui.print("Management Options");
      await c.ui.print("You may:");
      await c.ui.print();
      let i = 0;
      for (const opt of D.MANAGE_OPTIONS) { i += 1; await c.ui.print(`${i}. ${opt}`); }
      await c.ui.print();
      await c.ui.print("What is your choice? ");
    }
    const a = (await c.ui.key(ALLOWED.MANAGE, 1)) as string;
    const z = /^\d+$/.test(a) ? parseInt(a, 10) : 0;
    if (z === 1) await topTen(c, readTopTen(c));
    else if (z === 2) await topTen(c, D.originalTopTen());
    else if (z === 3) await eraseTopTen(c);
    else if (z === 4) await eraseTombs(c);
    else if (z === 5) return;
  }
}

/** line 700: the list is replaced by the original ten */
async function eraseTopTen(c: Context): Promise<void> {
  await c.ui.print("If you erase the current Top Ten list, the names and scores will be replaced by those on the original list.");
  await c.ui.print("Do you want to do this? ");
  if ((await C.yesNo(c)) === "N") return;
  c.hiscore = c.files.resetHiscore();
}

/** line 200: an empty record on each side, in turn */
async function eraseTombs(c: Context): Promise<void> {
  await c.ui.print("There may be a tombstone message on each side of the diskette.  If you erase these messages, they will not be replaced until team leaders die along the trail.");
  await c.ui.print("Do you want to do this? ");
  if ((await C.yesNo(c)) === "N") return;
  for (const side of [0, 1]) {
    await c.ui.clear();
    await c.ui.print(`Removing tombstones from side ${side === 0 ? "one" : "two"}...`);
    await C.checkSide(c, side + 1);
    c.files.eraseTombs(side);
  }
}
