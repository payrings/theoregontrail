/** WIN: the end of the journey (lines 100 to 1030): the score, the top ten, and the menu. */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as menu from "./menu.js";
import { ALLOWED } from "./ui.js";
import type { HiscoreEntry } from "./files.js";

const MULTIPLIER_TEXT: Record<number, string> = { 1: "", 2: "doubled", 3: "tripled" };
const PROFESSION_NAME: Record<number, string> = { 1: "banker", 2: "carpenter", 3: "farmer" };
const S = (c: Context): any => c.ui.screens;

type Pt = [number, number][];

/** lines 130-140: the eight scoring items, read from the hand-over memory */
export function readItems(c: Context): { pt: Pt; cash: N.Fac } {
  const mem = c.mem;
  const pt: Pt = Array.from({ length: 8 }, () => [0, 0] as [number, number]);
  const people = mem.peek(900);
  pt[0][0] = people; pt[0][1] = people * (500 - 100 * mem.peek(916));
  pt[1][0] = 1; pt[1][1] = 50;
  pt[2][0] = mem.peek(909); pt[2][1] = pt[2][0] * 4;
  pt[3][0] = mem.peek(910) + mem.peek(911) + mem.peek(912); pt[3][1] = pt[3][0] * 2;
  pt[4][0] = mem.peek(908); pt[4][1] = pt[4][0] * 2;
  pt[5][0] = mem.peekWord(904); pt[5][1] = Math.floor(pt[5][0] / 50);
  pt[6][0] = mem.peekWord(906); pt[6][1] = Math.floor(pt[6][0] / 25);
  // PT(7,0) = PEEK (913) + PEEK (914) * 256 + PEEK (917) / 100, PT(7,1) = INT (PT(7,0) / 5)
  const raw = N.add(N.parse(String(mem.peekWord(913))), N.div(N.parse(String(mem.peek(917))), N.parse("100")));
  const cash = N.store(raw);                // PT(7,0) is an array element: stored
  pt[7][0] = 0;                             // (the amount itself is returned beside the table)
  pt[7][1] = N.trunc(N.div(raw, N.parse("5")));     // ... while PT(7,1) is worked from the unstored sum
  return { pt, cash };
}

/** lines 610-621: the eight lines of the table as the program words them */
function winRows(c: Context, pt: Pt, cash: N.Fac): [string, number][] {
  const pl = ["", "s", "s", "en"];
  const n4 = (n: number) => String(n).padStart(4);
  return [
    ["   " + pt[0][0] + (pt[0][0] > 1 ? " people" : " person") + " in " + D.HEALTH[c.mem.peek(916)] + " health", pt[0][1]],
    ["   " + pt[1][0] + " wagon", pt[1][1]],
    [n4(pt[2][0]) + " ox" + pl[pt[2][0] !== 1 ? 3 : 0], pt[2][1]],
    [n4(pt[3][0]) + " spare wagon part" + pl[pt[3][0] !== 1 ? 1 : 0], pt[3][1]],
    [n4(pt[4][0]) + " set" + pl[pt[4][0] !== 1 ? 1 : 0] + " of clothing", pt[4][1]],
    [n4(pt[5][0]) + " bullet" + pl[pt[5][0] !== 1 ? 2 : 0], pt[5][1]],
    [n4(pt[6][0]) + " pounds of food", pt[6][1]],
    ["     $" + C.money(c, cash) + " cash", pt[7][1]],
  ];
}

const total = (pt: Pt): number => pt.reduce((s, r) => s + r[1], 0);
/** line 630: R = (SC < 6000) + (SC < 3000) */
const rating = (score: number): number => (score < 6000 ? 1 : 0) + (score < 3000 ? 1 : 0);

/** lines 1000-1030: the congratulations, the score, the list and the menu */
export async function run(c: Context): Promise<string> {
  c.setProgram("WIN");
  (c.ui as any).sound?.select?.("ms17");                // WIN 100: & RFL, "MS17.BIN" AT 51944
  let entries: HiscoreEntry[] = c.files.readHiscore();
  if (!entries.length) entries = D.originalTopTen();
  const { pt, cash } = readItems(c);
  let score = total(pt);
  const gfx = c.ui.pictures;
  // line 601: "18" then the stored year byte
  const date = `${D.MONTHS[c.mem.peek(902) - 1]} ${c.mem.peek(903)}, 18${c.mem.peek(901)}`;
  const congrats = "Congratulations!  You have made it to Oregon!  Let's see how many points you have received.";
  if (gfx) {
    await S(c).winArrival(c.ui, date);
    await c.ui.waitKey("", "Press SPACE BAR to continue", { y: 182, tune: true });      // 601: GOSUB 950
    await S(c).box41000(c.ui, congrats, 14, 60, 253, 108);
  } else {
    await c.ui.clear();
    await c.ui.print("The Willamette Valley, Oregon");
    await c.ui.print(date);
    await C.waitKey(c);
    await c.ui.clear();
    await c.ui.print(congrats);
  }
  await C.waitKey(c);
  let shown = false;
  for (;;) {
    if (gfx) {
      const ny = await S(c).winPoints(c.ui, winRows(c, pt, cash), score, !shown);
      const profession = c.mem.peek(915);
      if (!shown && profession > 1) {
        shown = true;
        (c.ui as any).dfw(20, ny, 239, 191 - ny);
        (c.ui as any).para(`For going as a ${PROFESSION_NAME[profession]}, your points are ${MULTIPLIER_TEXT[profession]}.`);
        await C.waitKey(c);
        for (const row of pt) row[1] *= profession;
        score *= profession;
        continue;
      }
      await C.waitKey(c);                              // 630: GOSUB 30000
      break;
    }
    await c.ui.clear();
    await c.ui.print("Points for arriving in Oregon");
    await c.ui.print();
    await c.ui.print("   " + pt[0][0] + (pt[0][0] !== 1 ? " people" : " person") + " in " + D.HEALTH[c.mem.peek(916)] + " health".padEnd(24) + String(pt[0][1]).padStart(8));
    await c.ui.print("   " + pt[1][0] + " wagon".padEnd(28) + String(pt[1][1]).padStart(8));
    await c.ui.print("   " + pt[2][0] + (pt[2][0] !== 1 ? " oxen" : " ox").padEnd(28) + String(pt[2][1]).padStart(8));
    await c.ui.print("   " + pt[3][0] + " spare wagon part" + (pt[3][0] !== 1 ? "s" : "").padEnd(28) + String(pt[3][1]).padStart(8));
    await c.ui.print("   " + pt[4][0] + " set" + (pt[4][0] !== 1 ? "s" : "") + " of clothing".padEnd(28) + String(pt[4][1]).padStart(8));
    await c.ui.print("   " + pt[5][0] + " bullet" + (pt[5][0] !== 1 ? "s" : "").padEnd(28) + String(pt[5][1]).padStart(8));
    await c.ui.print("   " + pt[6][0] + " pounds of food".padEnd(28) + String(pt[6][1]).padStart(8));
    // 621: V = PT(7,0): GOSUB 250: PRINT "     $"K$" cash"
    await c.ui.print(("     $" + C.money(c, cash) + " cash").padEnd(28) + String(pt[7][1]).padStart(8));
    await c.ui.print("   Total:".padEnd(28) + String(score).padStart(8));
    await c.ui.print();
    const profession = c.mem.peek(915);
    if (!shown && profession > 1) {
      shown = true;
      await c.ui.print(`For going as a ${PROFESSION_NAME[profession]}, your points are ${MULTIPLIER_TEXT[profession]}.`);
      await C.waitKey(c);
      for (const row of pt) row[1] *= profession;
      score *= profession;
      continue;
    }
    break;
  }
  const rate = rating(score);
  c.outcome = `ARRIVED ${score} ${D.RATINGS[rate]}`;
  if (score > (entries.length > 9 ? entries[9][1] : -1)) {
    // WIN 2000-2020: the top-ten screen and the "Type your name" line are shown before the name entry (WIN 530)
    await menu.topTen(c, entries, true);
    if (gfx) (c.ui as any).dfw(20, 140, 230, 51);                     // 2015: & DFW,7 AT 20,140,230,51
    await c.ui.print("Congratulations!  Type your name as you would like to see it on the Oregon Top Ten list.");
    entries = await insert(c, entries, score, D.RATINGS[rate]);
    c.files.writeHiscore(entries);
    c.hiscore = null;
  } else {
    if (gfx) {
      await menu.topTen(c, entries, true);
      (c.ui as any).dfw(20, 140, 230, 51);
    } else await c.ui.clear();
    await c.ui.print(`You have accumulated ${score} points.  This is not enough to qualify for the Oregon Top Ten.`);
    await C.waitKey(c);
  }
  await menu.topTen(c, entries);
  return "MENU";
}

/** lines 510 and 515: where the new score goes, and the list with room made (a tie goes below the old entry) */
export function placeInList(entries: HiscoreEntry[], score: number): { list: [string, number | string, string][]; g: number } {
  const hi: [string, number | string, string][] = entries.map((e) => [...e] as [string, number, string]);
  while (hi.length < 10) hi.push(["", 0, ""]);
  let g = 0;
  for (let l = 9; l >= 1; l--) {
    if (score > Number(hi[l][1])) hi[l] = [...hi[l - 1]];
    if (score <= Number(hi[l][1])) { g = l; break; }
  }
  return { list: hi, g };
}

/** lines 510-530: the entry goes into the list in order, and the name is typed */
async function insert(c: Context, entries: HiscoreEntry[], score: number, rate: string): Promise<HiscoreEntry[]> {
  const placed = placeInList(entries, score);
  const list = placed.list;
  const g = placed.g;
  list[g] = ["", score, rate];                // HI$(G,1) = STR$(SC), HI$(G,2) = R$(R)
  const gfx = c.ui.pictures;
  if (gfx) await S(c).topTen(c.ui, [...list.slice(0, g), ["", "", ""], ...list.slice(g + 1)]);     // 520: GOSUB 700
  for (;;) {
    let y = 0;
    if (gfx) {
      y = 38 + 9 * g;
      const u = c.ui as any;
      u.dfw(0, 0, 280, 192);
      u.cv.clearText(0, y, 279, y + 8);
      u.co(0, y);
    }          // 530: & CO,,ZZ + G * 9: & CEL
    list[g][0] = (await c.ui.key(ALLOWED.TOPTEN, 15, "")) as string;
    if (gfx) {
      const u = c.ui as any;
      u.co(139, y);
      u.put(String(list[g][1]).padStart(4));
      u.co(189, y);
      u.put(String(list[g][2]));
      u.cv.box(20, 140, 249, 190);            // & WIND,7: & BOX
      u.dfw(20, 140, 230, 51);
    }
    await c.ui.print("Would you like to make any changes? ");
    if ((await C.yesNo(c)) !== "Y") break;
  }
  return list.map((e) => [e[0], Number(e[1]), e[2]] as HiscoreEntry);
}
