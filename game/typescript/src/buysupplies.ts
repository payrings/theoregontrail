/** BUY SUPPLIES: the departure month and Matt's General Store (lines 100 to 5020). */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import { ALLOWED } from "./ui.js";

const MAX_FOOD = 2000, MAX_PART = 3;
const S = (c: Context): any => c.ui.screens;
const p = (n: number): N.Fac => N.parse(String(n));

/** line 120: read the hand-over and clear 904 to 912 */
export function initState(c: Context): N.Fac {
  const st = c.st;
  st.MY = N.div(p(c.mem.peekWord(913)), N.parse("10"));
  for (let addr = 904; addr < 913; addr++) c.mem.poke(addr, 0, 120);
  for (let item = 2; item < 9; item++) st.I[item] = N.ZERO;
  return st.MY;
}

/** lines 910-950: what the store charges for each of the five lines */
export function lineValues(c: Context): N.Fac[] {
  const peek = (a: number) => c.mem.peek(a);
  return [
    N.store(N.mul(p(40), p(peek(905)))),
    N.store(N.mul(N.parse(".2"), N.add(N.mul(p(peek(907)), p(256)), p(peek(906))))),
    N.store(N.mul(p(10), p(peek(908)))),
    N.store(N.mul(p(2), p(peek(909)))),
    N.store(N.mul(p(10), N.add(N.add(p(peek(910)), p(peek(911))), p(peek(912))))),
  ];
}

/** lines 6000-6110: March to July, or a word of advice */
export async function departureMonth(c: Context): Promise<number> {
  c.mem.poke(903, 1, 6000);          // the day is the first of the month
  for (;;) {
    c.setProgram("BUY SUPPLIES");
    await c.ui.clear();
    await c.ui.print(`It is 18${c.mem.peek(901)}.  Your jumping off place for Oregon is Independence, Missouri.  You must decide which month to leave Independence.`);
    await c.ui.print();
    let i = 0;
    for (const name of D.MONTH_CHOICES) { i += 1; await c.ui.print(`   ${i}. ${name}`); }
    await c.ui.print("   6. Ask for advice");
    await c.ui.print();
    await c.ui.print("What is your choice? ");
    const a = (await c.ui.key(ALLOWED.MONTH, 1)) as string;
    if (a && /^\d+$/.test(a)) {
      const z = parseInt(a, 10);
      if (z === 6) { await advice(c); continue; }
      if (z >= 1 && z <= 5) { c.mem.poke(902, z + 2, 6030); return z + 2; }
    }
    await c.ui.print("What is your choice? ");
    await c.ui.key(ALLOWED.MONTH, 1);
  }
}

/** lines 6105-6110 */
async function advice(c: Context): Promise<void> {
  await c.ui.clear();
  await c.ui.print('You attend a public meeting held for "folks with the California - Oregon fever."  You\'re told:');
  await c.ui.print();
  await c.ui.print("If you leave too early, there won't be any grass for your oxen to eat.  ");
  await c.ui.print("If you leave too late, you may not get to Oregon before winter comes.  If you leave at just the right time, there will be green grass and the weather will still be cool.");
  await C.waitKey(c);
}

/** lines 1000-5020: buy until the player leaves */
export async function store(c: Context): Promise<{ yokes: number; food: number }> {
  await intro(c);
  c.storeVerb = "buy";                      // 1005: A$ = "buy"
  for (;;) {
    await showBill(c);
    if (!c.ui.pictures) {
      await c.ui.print("Press SPACE BAR to leave store");
      await c.ui.print("Which item would you like to " + c.storeVerb + "? ");
    }
    // Line 250's reader accepts 1 to 5 and nothing else, and a bare Return gives VAL(Z$) = 0, which line 1015 turns into leaving
    let a: string;
    if (c.ui.pictures) a = (await c.ui.key(ALLOWED.STORE_ITEM + " ", 1, "", false)) as string;
    else a = (await c.ui.key(ALLOWED.STORE_ITEM, 1, "")) as string;
    let z = a && /^\d+$/.test(a) ? parseInt(a, 10) : 0;
    if (z === 0) z = 6;
    if (z === 6) {
      if (await leave(c)) return { yokes: c.mem.peek(905), food: c.mem.peek(906) + c.mem.peek(907) * 256 };
      continue;
    }
    await buyItem(c, z);
  }
}

/** lines 2000-2030: Matt's introduction and the bill so far */
async function intro(c: Context): Promise<void> {
  const st = c.st;
  const msg1 = `Before leaving Independence, you should buy equipment and supplies.  You have $${C.money(c, st.MY)} in cash, but you don't have to spend it all now.`;
  const msg2 = "You can buy whatever you need at Matt's General Store.";
  if (c.ui.pictures) await S(c).messageBox(c.ui, msg1, [21, 84, 256, 140]);
  else { await c.ui.clear(); await c.ui.print(msg1); }
  await C.waitKey(c);
  if (c.ui.pictures) await S(c).messageBox(c.ui, msg2, [14, 112, 256, 140]);
  else await c.ui.print(msg2);
  await C.waitKey(c);
  if (c.ui.pictures) await S(c).mattIntro(c.ui, 1);
  else {
    await c.ui.print();
    await c.ui.print("Hello, I'm Matt.  So you're going to Oregon!  I can fix you up with what you need:");
    await c.ui.print();
    await c.ui.print("- a team of oxen to pull your wagon");
    await c.ui.print("- clothing for both summer and winter");
  }
  await C.waitKey(c);
  if (c.ui.pictures) await S(c).mattIntro(c.ui, 2);
  else {
    await c.ui.print("- plenty of food for the trip");
    await c.ui.print("- ammunition for your rifles");
    await c.ui.print("- spare parts for your wagon");
  }
  await C.waitKey(c);
}

/** line 4000: Z = 0: FOR L = 1 TO 6: ...: Z = Z + V: NEXT: TB = Z (stored at every step) */
export function bill(c: Context): N.Fac {
  let z = N.ZERO;
  for (const v of lineValues(c)) z = N.store(N.add(z, v));
  return z;
}

/** lines 3015-3020: the five lines, the total and the money held */
async function showBill(c: Context): Promise<void> {
  const st = c.st;
  if (c.ui.pictures) {
    await S(c).shopList(c.ui, lineValues(c).map((v) => C.dollarText(c, v)), C.dollarText(c, bill(c)), C.dollarText(c, st.MY),
      D.STORE_MONTHS[c.mem.peek(902) - 2] + " " + String(c.mem.peek(903)) + ", 18" + String(c.mem.peek(901)), c.storeVerb);
    return;
  }
  await c.ui.print("  Matt's General Store");
  await c.ui.print("  Independence, Missouri");
  await c.ui.print();
  await c.ui.print(D.STORE_MONTHS[c.mem.peek(902) - 2] + " " + String(c.mem.peek(903)) + ", 18" + String(c.mem.peek(901)));
  await c.ui.print();
  const values = lineValues(c);
  const names = D.STORE_ITEMS.slice(1);     // 3015: PRINT L". "I$(L), L = 1 to 5
  for (let n = 1; n <= 5; n++) await c.ui.print(`${n}. ${names[n - 1]}`.padEnd(24) + C.dollarText(c, values[n - 1]));
  await c.ui.print("Total bill: " + C.dollarText(c, bill(c)));
  await c.ui.print("Amount you have: " + C.dollarText(c, st.MY));
}

/** lines 400, 500, 600, 700 and 800: the five prompts */
async function buyItem(c: Context, z: number): Promise<void> {
  const pic = c.ui.pictures;
  const sofar = pic ? C.dollarText(c, bill(c)) : "";
  const num = (a: string) => (a && /^\d+$/.test(a) ? parseInt(a, 10) : 0);
  if (z === 1) {                                           // oxen, line 400
    if (pic) await S(c).itemOxen(c.ui, sofar);
    else {
      await c.ui.clear();
      await c.ui.print("There are 2 oxen in a yoke; I recommend at least 3 yoke.  I charge $40 a yoke.");
      await c.ui.print();
      await c.ui.print("How many yoke do you");
      await c.ui.print("want? ");
    }
    const a = (await c.ui.key(ALLOWED.STORE_YOKE, 1)) as string;
    c.mem.poke(905, num(a), 405);
  } else if (z === 2) {                                    // food, line 500
    for (;;) {
      if (pic) await S(c).itemFood(c.ui, sofar);
      else {
        await c.ui.clear();
        await c.ui.print("I recommend you take at least 200 pounds of food for each person in your family.  I see that you have 5 people in all.  You'll need flour, sugar, bacon, and coffee.  My price is 20 cents a pound.");
        await c.ui.print();
        await c.ui.print("How many pounds of food do you want? ");
      }
      const a = (await c.ui.key(ALLOWED.STORE_FOOD, 4)) as string;
      const want = num(a);
      if (want > MAX_FOOD) {
        if (pic) await S(c).storeNote(c.ui, "Your wagon may only carry 2000 pounds of food.", [60, 40, 219, 151]);
        else { await c.ui.print(); await c.ui.print("Your wagon may only carry 2000 pounds of food."); }
        await C.waitKey(c);
        continue;
      }
      c.mem.pokeWord(906, want, 530);
      break;
    }
  } else if (z === 3) {                                    // clothing, line 600
    if (pic) await S(c).itemClothing(c.ui, sofar);
    else {
      await c.ui.clear();
      await c.ui.print("You'll need warm clothing in the mountains.  I recommend taking at least 2 sets of clothes per person.  Each set is $10.00.");
      await c.ui.print();
      await c.ui.print("How many sets of clothes do you want? ");
    }
    const a = (await c.ui.key(ALLOWED.STORE_CLOTHES, 2)) as string;
    c.mem.poke(908, num(a), 610);
  } else if (z === 4) {                                    // ammunition, line 700
    if (pic) await S(c).itemAmmo(c.ui, sofar);
    else {
      await c.ui.clear();
      await c.ui.print("I sell ammunition in boxes of 20 bullets.  Each box costs $2.00.");
      await c.ui.print();
      await c.ui.print("How many boxes do");
      await c.ui.print("you want? ");
    }
    const a = (await c.ui.key(ALLOWED.STORE_AMMO, 2)) as string;
    c.mem.poke(909, num(a), 700);
  } else if (z === 5) {                                    // spare parts, line 800
    if (pic) await S(c).itemPartsIntro(c.ui, sofar, D.STORE_PART_NAMES);
    else {
      await c.ui.clear();
      await c.ui.print("It's a good idea to have a few spare parts for your wagon.  Here are the prices:");
      for (const [name, price] of D.STORE_PART_NAMES) await c.ui.print(`   ${name.padEnd(14)}- $${price} each`);
    }
    let i = 0;
    let again = false;
    while (i < 3) {                                        // 810: FOR L = 0 TO 2
      const name = D.STORE_PART_NAMES[i][0];
      if (pic) { if (i || again) await S(c).partsQuestion(c.ui, name); }
      else { await c.ui.print(); await c.ui.print(`How many ${name}s? `); }
      const a = (await c.ui.key(ALLOWED.STORE_PART, 1)) as string;
      const want = num(a);
      c.mem.poke(910 + i, want, 810);                      // POKE 910 + L, Z comes first
      if (want > MAX_PART) {
        // 811: the message, then L = L - 1, so the same part is asked again
        if (pic) await S(c).storeNote(c.ui, `Your wagon may only carry 3 ${name}s.`, [60, 114, 219, 18]);
        else await c.ui.print(`Your wagon may only carry 3 ${name}s.`);
        await C.waitKey(c);
        again = true;
        continue;
      }
      i += 1;
      again = false;
    }
  }
  await showBill(c);
}

/** lines 5000-5020: leave the store, or be told why not */
async function leave(c: Context): Promise<boolean> {
  const st = c.st;
  const total = bill(c);
  if (N.lt(st.MY, total)) {
    const said = "Okay, that comes to a total of " + C.dollarText(c, total) + ".  But I see that you only have $" + C.money(c, st.MY) + ".  We'd better go over the list again.";
    if (c.ui.pictures) await S(c).storeNote(c.ui, said);
    else { await c.ui.print(); await c.ui.print(said); }
    await C.waitKey(c);
    c.storeVerb = "change";                 // 5000: A$ = "change"
    return false;
  }
  if (!c.mem.peek(905)) {
    if (c.ui.pictures) await S(c).storeNote(c.ui, "Don't forget, you'll need oxen to pull your wagon.");
    else { await c.ui.print(); await c.ui.print("Don't forget, you'll need oxen to pull your wagon."); }
    await C.waitKey(c);
    return false;
  }
  // 5010: MY = (MY - TB) * 10, then FN LO and FN HI split it across 913 and 914
  const tenths = N.store(N.mul(N.sub(st.MY, total), N.parse("10")));
  c.mem.pokeWord(913, N.trunc(tenths), 5010);
  st.MY = N.div(tenths, N.parse("10"));
  if (c.ui.pictures) {
    (c.ui as any).cv.box(50, 0, 279, 191);
    await S(c).storeNote(c.ui, "Well then, you're ready to start.  Good luck!  You have a long and difficult journey ahead of you.", [60, 60, 190, 131]);
  } else {
    await c.ui.print();
    await c.ui.print("Well then, you're ready to start.  Good luck!  You have a long and difficult journey ahead of you.");
  }
  await C.waitKey(c);
  if (c.ui.pictures) {
    await S(c).messageBox(c.ui, "Now loading the wagon...", [42, 160, 231, 180]);
    await (c.ui as any).refresh?.();
  } else {
    await c.ui.print();
    await c.ui.print("Now loading the wagon...");
  }
  // line 5020 chains to OREGON TRAIL with & RNH, so the store never comes back
  return true;
}
