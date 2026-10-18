/**
 * The screens that have a picture, laid out as the BASIC lays them out (the Python rebuild's
 * graphics/screens.py, function for function). Each function draws one whole screen on a GraphicalUI and
 * leaves the cursor where the game's next prompt goes. Every position comes from the listing (the
 * `& DFW`, `& CO`, `& BOX` and `& IMAGE` arguments). Pictures are looked up by name in the assets folder;
 * a missing one is skipped, so a folder with only some of the files still plays.
 *
 * Python keyword arguments are an options object as the last parameter. Drawing is synchronous; the few
 * screens that wait or pause (getting the menu, the tombstone bar, the river's strokes) are async.
 */
import { COORDINATES as MP } from "../maplib.js";
import type { GraphicalUI } from "./gui.js";
import type { Saved } from "./canvas.js";

type UI = GraphicalUI;
const GREEN = 1, VIOLET = 2, BLUE = 6, ORANGE = 5;
const floorDiv = (a: number, b: number): number => Math.floor(a / b);
const mod2 = (x: number): number => ((x % 2) + 2) % 2;

/** the title picture and the two borders (MENU 1000 and 6000) */
function frame(ui: UI): void {
  ui.cv.image("first_02", 1, 10);
  ui.cv.image("first_03", 8, 40);
  ui.cv.image("first_03", 8, 164);
}

/** MENU 1000-1015 */
export function title(ui: UI, soundWord: string): void {
  ui.clear();
  frame(ui);
  ui.dfw(32, 63, 245, 125);
  ui.vsp = 3;
  for (const t of ["You may:", "", "  1. Travel the trail", "  2. Learn about the trail",
    "  3. See the Oregon Top Ten", "  4. Turn sound " + soundWord, ""]) ui.line(t);
  ui.put("What is your choice? ");
}

/** MANAGEMENT 1000-1015: the teacher's menu (Control-A on the main menu) */
export function management(ui: UI, options: string[], version = "Version 1.4"): void {
  ui.clear();
  ui.line("The Oregon Trail", true, true);
  ui.line(version, true, true);
  ui.line("");
  ui.cv.line(0, 20, 279, 20, 6);
  ui.line("Management Options", true, true);
  ui.dfw(0, 60, 279, 151);
  ui.line("You may:");
  ui.line("");
  options.forEach((text, i) => { ui.co(20); ui.line(`${i + 1}. ${text}`); });
  ui.line("");
  ui.co(0);
  ui.put("What is your choice? ");
}

/** MENU 7000-7041. After the first, PRINT CF$ starts one line down. */
export function info(ui: UI, text: string, first = false): void {
  ui.clear();
  frame(ui);
  ui.dfw(20, 70, 240, 90);
  ui.cy = first ? 0 : 9;
  ui.para(text);
}

/** MENU 7400-7410 */
export function colours(ui: UI): void {
  ui.clear();
  frame(ui);
  ui.dfw(20, 70, 240, 90);
  ui.cy = 9;
  for (const s of ["You may use these colors to", "adjust your monitor or", "television."]) ui.line(s, true, true);
  [["Orange", ORANGE], ["Green", GREEN], ["Blue", BLUE], ["Violet", VIOLET]].forEach(([name, col], i) => {
    ui.cv.box(20 + 60 * i, 115, 70 + 60 * i, 145, col as number);
    ui.dfw(20 + 60 * i, 147, 50, 10);
    ui.line(name as string, true, true);
  });
}

/** MENU 7500 */
export function controlS(ui: UI): void {
  ui.clear();
  frame(ui);
  ui.dfw(20, 70, 240, 90);
  ui.cy = 18;
  ui.line("Control-S key", true, true);
  ui.nl();
  ui.para("You may turn the sound on or off during the program by pressing Control-S.");
}

/** MENU 2300 */
export function sound(ui: UI, word: string): void {
  ui.clear();
  frame(ui);
  ui.dfw(20, 90, 240, 70);
  ui.para(`The sound is now turned ${word}.`);
  ui.nl();
  ui.para("You may turn the sound on or off during the program by pressing Control-S.");
}

/** MENU 6015 */
export function namesLeader(ui: UI): void {
  ui.clear();
  ui.cv.image("first_01", 7, 0);
  ui.dfw(0, 102, 280, 89);
  ui.para("What is the first name of the wagon leader? ", false);
}

/** MENU 6020-6021: the four other names are typed on the numbered lines */
export function namesOthers(ui: UI, leader: string): void {
  ui.clear();
  ui.cv.image("first_01", 7, 0);
  ui.dfw(0, 102, 280, 89);
  ui.para("What are the first names of the four other members in your party? ");
  ui.nl();
  ui.namePos = [];
  for (let i = 0; i < 5; i++) {
    ui.put(`${i + 1}. `);
    ui.namePos.push([ui.cx, ui.cy]);
    if (i === 0) ui.put(leader);
    ui.nl();
  }
  ui.co(0, 81);
  ui.put("(Enter names or press Return)");
}

export function namesCursor(ui: UI, i: number): void { ui.co(ui.namePos[i][0], ui.namePos[i][1]); }

/** MENU 6020-6040 */
export function namesConfirm(ui: UI, names: string[]): void {
  ui.clear();
  ui.cv.image("first_01", 7, 0);
  ui.dfw(0, 102, 280, 89);
  ui.para("What are the first names of the four other members in your party? ");
  ui.nl();
  names.forEach((n, i) => ui.line(`${i + 1}. ${n}`));
  ui.co(0, 81);
  ui.put("Are these names correct? ");
}

// ------------------------------------------------------------------ Matt's store
/** BUY SUPPLIES 2010-2030 */
export function mattIntro(ui: UI, part: number): void {
  ui.clear();
  ui.dfw(0, 0, 280, 192);
  ui.cy = 18;
  ui.para("Hello, I'm Matt.  So you're going to Oregon!  I can fix you up with what you need:");
  ui.cv.image("first_04", 0, 50);
  ui.dfw(70, 60, 200, 131);
  const items = part === 1
    ? ["- a team of oxen to pull your wagon", "- clothing for both summer and winter"]
    : ["- plenty of food for the trip", "- ammunition for your rifles", "- spare parts for your wagon"];
  ui.cy = part === 1 ? 18 : 0;
  for (const it of items) { ui.para(it, true, 16); ui.nl(); }
}

function storeHeader(ui: UI, bars: number[]): void {
  ui.cv.box(50, 0, 279, 191);
  for (const y of bars) ui.cv.box(50, y, 270, y + 2, GREEN);
}

/** BUY SUPPLIES 3000-3030. `rows` are the five price strings, e.g. `$0.00`. */
export function shopList(ui: UI, rows: string[], total: string, money: string, date: string, verb: string): void {
  ui.clear();
  ui.cv.image("first_04", 0, 50);
  storeHeader(ui, [5, 47, 100]);
  ui.dfw(60, 10, 219, 181);
  ui.line("  Matt's General Store");
  ui.line("  Independence, Missouri");
  ui.nl();
  ui.co(199 - date.length * 8, ui.cy);
  ui.line(date);
  ui.nl();
  ui.cy -= 2;
  ["Oxen", "Food", "Clothing", "Ammunition", "Spare parts"].forEach((name, i) => {
    ui.co(0, ui.cy);
    ui.put(`${i + 1}. ${name}`);
    ui.co(135, ui.cy);
    ui.padded(rows[i], 8, true);
  });
  ui.dfw(0, 0, 280, 192);
  ui.co(111, 106);
  ui.put("Total bill: ");
  ui.padded(total, 8);
  ui.co(61, 135);
  ui.put("Amount you have: ");
  ui.padded(money, 8);
  ui.dfw(70, 150, 180, 41);
  ui.co(0, 23);
  ui.para("Press SPACE BAR to leave store");
  ui.co(0, 0);
  ui.para(`Which item would you like to ${verb}? `, false);
}

function itemBase(ui: UI, bill: string, picture: string, pos: [number, number]): void {
  ui.clear();
  ui.cv.image("first_04", 0, 50);
  ui.cv.box(50, 0, 279, 191);
  ui.cv.box(50, 5, 270, 7, GREEN);
  ui.dfw(60, 10, 219, 181);
  ui.line("  Matt's General Store");
  ui.line("  Independence, Missouri");
  ui.cv.box(50, 29, 270, 31, GREEN);
  ui.dfw(60, 40, 219, 151);
  ui.co(0, 142);
  ui.put("Bill so far: " + bill);
  ui.co(0, 0);
  ui.cv.image(picture, pos[0], pos[1]);
}

export function itemOxen(ui: UI, bill: string): void {
  itemBase(ui, bill, "oregon_08", [150, 140]);
  ui.nl(); ui.nl();
  ui.para("There are 2 oxen in a yoke; I recommend at least 3 yoke.  I charge $40 a yoke.");
  ui.nl();
  ui.line("How many yoke do you");
  ui.put("want? ");
}

export function itemFood(ui: UI, bill: string): void {
  itemBase(ui, bill, "oregon_02", [150, 140]);
  ui.para("I recommend you take at least 200 pounds of food for each person in your " +
    "family.  I see that you have 5 people in all.  You'll need flour, sugar, " +
    "bacon, and coffee.  My price is 20 cents a pound.");
  ui.nl();
  ui.para("How many pounds of food do you want? ", false);
}

/** BUY SUPPLIES 600 */
export function itemClothing(ui: UI, bill: string): void {
  itemBase(ui, bill, "oregon_05", [146, 140]);
  ui.nl(); ui.nl();
  ui.para("You'll need warm clothing in the mountains.  I recommend taking at least 2 " +
    "sets of clothes per person.  Each set is $10.00.");
  ui.nl();
  ui.para("How many sets of clothes do you want? ", false);
}

export function itemAmmo(ui: UI, bill: string): void {
  itemBase(ui, bill, "oregon_06", [149, 140]);
  ui.nl(); ui.nl(); ui.nl();
  ui.para("I sell ammunition in boxes of 20 bullets.  Each box costs $2.00.");
  ui.nl();
  ui.line("How many boxes do");
  ui.put("you want? ");
}

/** BUY SUPPLIES 800: the three prices, then the first question */
export function itemPartsIntro(ui: UI, bill: string, namesPrices: [string, string][]): void {
  itemBase(ui, bill, "oregon_03", [150, 133]);
  ui.para("It's a good idea to have a few spare parts for your wagon.  Here are the prices:");
  ui.nl();
  for (const [name, price] of namesPrices) {
    ui.co(8, ui.cy);
    ui.put(" " + name);
    ui.co(117, ui.cy);
    ui.line(`- $${price} each`);
  }
  ui.nl();
  partsQuestion(ui, namesPrices[0][0]);
}

/** BUY SUPPLIES 810: each question is asked in its own small window */
export function partsQuestion(ui: UI, name: string): void {
  ui.cv.box(60, 114, 278, 131);
  ui.dfw(60, 114, 219, 18);
  ui.put(`How many ${name}s? `);
}

// ------------------------------------------------------- messages over a picture
export interface MessageOptions { picture?: string; redraw?: boolean; centre?: boolean; lines?: string[] }

/**
 * A framed message over a full-screen picture (COMMON.LIB 41000; BUY SUPPLIES 2000 and 5020; the landmark
 * messages). `box` is [x1, y1, x2, y2] as the BASIC passes it: a black rectangle holding a three-dot white
 * frame with clipped corners, and the text eight dots in and six down.
 * Options: picture (default "l0"), redraw (default true), centre, lines (loss lines, indented three spaces).
 */
export function messageBox(ui: UI, text: string, box: readonly number[], opts: MessageOptions = {}): void {
  const { picture = "l0", redraw = true, centre = false, lines = [] } = opts;
  const [x1, y1, x2, y2] = box;
  if (redraw) { ui.clear(); ui.cv.screen(picture); }
  const cv = ui.cv;
  const xe = x2 + 2 - 2 * mod2(x2);
  cv.box(x1, y1, xe, y1 + 2);
  cv.box(x1 + (1 - mod2(x1)), y1 + 3, xe, y2 - 3);
  cv.box(x1, y2 - 2, xe, y2);
  cv.box(x1 + 1, y1 + 1, x2, y2 - 1, 3);
  cv.box(x1 + 4, y1 + 4, x2 - 3, y2 - 4);
  for (const [dx, dy] of [[1, 1], [2, 1], [1, 2]]) {
    cv.box(x1 + dx, y1 + dy, x1 + dx, y1 + dy);
    cv.box(x2 + 1 - dx, y1 + dy, x2 + 1 - dx, y1 + dy);
    cv.box(x1 + dx, y2 - dy, x1 + dx, y2 - dy);
    cv.box(x2 + 1 - dx, y2 - dy, x2 + 1 - dx, y2 - dy);
  }
  ui.dfw(x1 + 8, y1 + 6, x2 - x1 - 10, y2 - y1 - 10);
  if (text.endsWith(" ")) { ui.para(text.trimEnd(), false); ui.put(" "); }
  else if (centre) ui.line(text, true, true);
  else ui.para(text);
  for (const t of lines) ui.line("   " + t);
}

/** COMMON.LIB 41000 as the OREGON TRAIL program calls it: the left edge drops to a multiple of seven and
 *  the right one is seven-aligned plus six. Options as messageBox (picture is not used). */
export function box41000(ui: UI, text: string, x1: number, y1: number, x2: number, y2: number, opts: MessageOptions = {}): void {
  messageBox(ui, text, [floorDiv(x1, 7) * 7, y1, floorDiv(x2, 7) * 7 + 5, y2], { ...opts, redraw: false });
}

/** a short remark from Matt in the lower part of the store (BUY SUPPLIES 5000-5015) */
export function storeNote(ui: UI, text: string, window: readonly number[] = [60, 130, 219, 61]): void {
  const [x, y, w, h] = window;
  ui.cv.box(x, y, x + w - 1, y + h - 1);
  ui.dfw(x, y, w, h);
  ui.para(text);
}

// ============================================================ the journey's menus
function borders(ui: UI, y1: number, y2: number): void {
  ui.cv.image("oregon_10", 10, y1);
  ui.cv.image("oregon_10", 10, y2);
}

/** PACE.LIB 50000-50020 */
export function paceMenu(ui: UI, current: string, names: string[]): void {
  ui.clear();
  borders(ui, 10, 170);
  ui.dfw(0, 0, 280, 192);
  ui.co(0, 35);
  ui.line("Change pace", true, true);
  ui.line(`(currently "${current}")`, true, true);
  ui.nl();
  for (const t of ["The pace at which you travel", "can change.  Your choices are:"]) { ui.co(25, ui.cy); ui.line(t); }
  const zy = ui.cy;
  ui.dfw(40, zy, 239, 191 - zy);
  ui.nl();
  names.forEach((n, i) => ui.para(`${i + 1}. a ${n} pace`, true, 20));
  ui.para("4. find out what these different paces mean", true, 20);
  ui.nl();
  const y = ui.cy;
  ui.dfw(0, 0, 280, 192);
  ui.co(25, zy + y);
  ui.put("What is your choice? ");
}

export const RATION_PROMPT: [number, number] = [0, 164];

/** RATION.LIB 50000-50040 */
export function rationMenu(ui: UI, current: string, names: string[], descriptions: string[]): void {
  ui.clear();
  borders(ui, 0, 180);
  ui.dfw(0, 0, 280, 192);
  ui.co(0, 20);
  ui.line("Change food rations", true, true);
  ui.line(`(currently "${current}")`, true, true);
  ui.nl();
  const zy = ui.cy;
  ui.dfw(10, zy, 269, 191 - zy);
  ui.para("The amount of food the people in your party eat each day can change.  These amounts are:", false);
  ui.nl();
  const y = ui.cy;
  ui.dfw(30, zy + y, 249, 191 - zy - y);
  ui.nl();
  const n3 = Math.min(names.length, descriptions.length);
  for (let k = 0; k < n3; k++) {
    const i = k + 1;
    ui.para(`${i}. ${names[k]} - ${descriptions[k]}`, true, 20);
    if (i < 3) ui.nl();
  }
  ui.dfw(0, 0, 280, 192);
  ui.co(RATION_PROMPT[0], RATION_PROMPT[1]);
  ui.put("What is your choice? ");
}

/** TALK.LIB 50010 */
export function talk(ui: UI, speaker: string, text: string): void {
  ui.clear();
  borders(ui, 10, 160);
  ui.dfw(20, 40, 230, 151);
  ui.line(`${speaker} tells you:`);
  ui.nl();
  ui.para('"' + text + '"');
}

export const SUPPLY_LABELS = ["oxen", "sets of clothing", "bullets", "wagon wheels", "wagon axles", "wagon tongues", "pounds of food"];
export const SUPPLY_TITLE_Y = 9;

/**
 * OREGON TRAIL 4100-4110 and TRADE.LIB 50000-50050. `counts` are the seven holdings (oxen, clothing,
 * bullets, wheels, axles, tongues, food). With a trade the pictures move and the offer is written along
 * the bottom. Options: tradeText, offer.
 */
export function supplies(ui: UI, counts: readonly (string | number)[], money: string, opts: { tradeText?: string | null; offer?: string | null } = {}): void {
  const tradeText = opts.tradeText ?? null, offer = opts.offer ?? null;
  ui.clear();
  ui.dfw(0, 0, 280, 192);
  ui.co(0, SUPPLY_TITLE_Y);
  ui.line(tradeText !== null ? "Your Supplies" : "  Your Supplies", true, true);
  const cv = ui.cv;
  cv.image("oregon_02", 0, 30);
  cv.image("oregon_03", 20, 80);
  if (tradeText === null) {
    cv.image("oregon_08", 10, 140);
    cv.image("oregon_05", 82, 120);
    cv.image("oregon_06", 169, 130);
  } else {
    cv.image("oregon_08", 71, 110);
    cv.image("oregon_06", 169, 100);
  }
  ui.dfw(80, 30, 199, 161);
  const n = Math.min(SUPPLY_LABELS.length, counts.length);
  for (let i = 0; i < n; i++) {
    const y = ui.cy;
    ui.put(SUPPLY_LABELS[i]);
    ui.co(130, y);
    ui.padded(counts[i], 4, true);
  }
  if (tradeText === null) {
    const y = ui.cy;
    ui.put("money left");
    ui.co(120, y);
    ui.padded("$" + money, 8, true);
  } else {
    ui.dfw(0, 150, 279, 41);
    ui.para(tradeText);
    if (offer) { ui.co(0, 32); ui.put(offer); }
  }
}

/** BUY.LIB 50000-50010. `goods` are seven [name, price, unit] triples. */
export function fortList(ui: UI, place: string, date: string, goods: [string, string, string][], money: string): void {
  ui.clear();
  ui.dfw(0, 0, 280, 192);
  const z = Math.max(place.length, date.length);
  const half = Math.floor(z / 2 + 0.5) * 8;
  ui.cv.panel(130 - half, 1, 148 + half, 22);
  ui.inverse = true;
  ui.co(0, 4);
  ui.line(place, true, true);
  ui.line(date, true, true);
  ui.inverse = false;
  ui.co(0, ui.cy + 4);
  ui.nl();
  ui.line("You may buy:", false, false);
  ui.nl(); ui.nl();
  const y0 = ui.cy;
  goods.forEach(([name], i) => { ui.put("  " + `${i + 1}. ${name}`); ui.nl(); });
  ui.put("  8. Leave store");
  ui.nl();
  const zy = ui.cy + 9;
  ui.dfw(150, y0, 129, 191 - y0);
  for (const [, price, unit] of goods) { ui.padded(price, 5); ui.line(" per " + unit); }
  ui.promptY = zy;
  ui.dfw(0, zy, 279, 191 - zy);
  ui.line(`You have $${money} to spend.`);
  ui.put("Which number? ");
}

/** OREGON TRAIL 4005-4060. `status` are the four lines (Weather, Health, Pace, Rations). */
export function actionMenu(ui: UI, place: string, date: string, status: string[], options: string[]): void {
  ui.clear();
  ui.dfw(0, 0, 280, 192);
  ui.line(place, true, true);
  ui.line(date, true, true);
  ui.cv.panel(0, 25, 278, 69);
  ui.inverse = true;
  ui.dfw(0, 25, 280, 45);
  ui.co(10, 5);
  for (const t of status) { ui.co(10, ui.cy); ui.line(t); }
  ui.inverse = false;
  ui.dfw(0, 73, 280, 118);
  ui.line("You may:");
  ui.nl();
  options.forEach((t, i) => { ui.co(30, ui.cy); ui.line(`${i + 1}. ${t}`); });
  ui.nl();
  ui.co(0, 110);
  ui.put("What is your choice? ");
}

/**
 * MAP.LIB / OREGON TRAIL 4200: the map picture with the route drawn over it. `route` is Q(0) to Q(Q1 - 1)
 * (line 50000, black lines between the landmarks' map points) and `leg` is [LM, NM, D, DD] for line 50010,
 * the part of the current leg already covered.
 */
export function mapScreen(ui: UI, route: readonly number[] = [], leg: readonly number[] | null = null): void {
  ui.clear();
  ui.cv.screen("m0");
  for (let i = 0; i + 1 < route.length; i++) ui.cv.line(MP[route[i]][0], MP[route[i]][1], MP[route[i + 1]][0], MP[route[i + 1]][1], 4);
  if (leg) {
    const [lm, nm, d, dd] = leg;
    if (lm !== nm && dd) {
      const [x1, y1] = MP[nm], [x2, y2] = MP[lm];
      const z = d * (x2 - x1) / dd;                  // Z = D * (X2 - X1) / DD
      const x = z + x1;
      if (x2 !== x1) {
        const y = y2 - (y2 - y1) / (x2 - x1) * (x2 - x);
        ui.cv.line(x2, y2, Math.trunc(x), Math.trunc(y), 4);
      }
    }
  }
  ui.cv.box(0, 182, 279, 191);
}

/** FLIP.LIB (side 1) 50005: the lower part of the scene is kept, the strip and panel go, and the request
 *  is written in a window of its own. Returns what to put back. */
export function flipToSide2(ui: UI): Saved {
  const saved = ui.cv.take(0, 121, 279, 180);
  ui.cv.box(0, 111, 279, 191);
  ui.dfw(10, 140, 260, 51);
  ui.para("To continue on your journey to Oregon, please flip the diskette to side 2.");
  return saved;
}

/** FLIP.LIB (side 2) 50001-50005: six of the pictures round the request */
export function flipToSide1(ui: UI): void {
  ui.clear();
  ui.dfw(10, 70, 260, 121);
  ui.cy = 9;
  for (const [n, x, y] of [[2, 0, 30], [5, 100, 10], [6, 199, 40], [3, 0, 140], [8, 100, 110], [9, 200, 130]]) {
    ui.cv.image(`b_oregon_${String(n).padStart(2, "0")}`, x, y);
  }
  ui.para("Please insert side 1 of the Oregon Trail diskette.");
}

/** MENU SIDE 2 31000: `& WIND: PRINT CL$: & CO,,89: PRINT "Getting the Oregon Trail menu..."` */
export async function gettingMenu(ui: UI, text: string): Promise<void> {
  ui.clear();
  ui.dfw(0, 0, 280, 192);
  ui.co(0, 89);
  ui.line(text, true, true);
  ui.refresh();
  await ui.sleep(1.0);
}

/** HUNT.LIB 50000-50010 */
export function huntInstructions(ui: UI, prefix = "oregon"): void {
  ui.clear();
  ui.line("Hunting Instructions", true, true);
  ui.hsp = 1;
  ui.dfw(20, 30, 120, 151);
  for (const t of ["Return Key", "", "", "Arrow Keys", ...Array(7).fill(""), "Space Bar"]) ui.line(t);
  ui.dfw(110, 30, 169, 151);
  for (const t of ["To start or stop walking", "", "", "To point the rifle", "(novice hunters)", "",
    "", "To point the rifle", "(expert hunters)", "", "", "To fire the rifle"]) ui.line(t);
  ui.cv.image(`${prefix}_06`, 1, 145);
  ui.hsp = 2;
  ui.cv.image(`${prefix}_01`, 30, 78);
}

/** HUNT.LIB 50011-50020 */
export function huntResult(ui: UI, text: string, prefix = "oregon"): void {
  ui.clear();
  ui.dfw(20, 40, 220, 151);
  ui.para(text);
  ui.cv.image(`${prefix}_06`, 1, 145);
}

/** PART.LIB 42000: an unframed black rectangle over the scene, with the text in it */
export function partBox(ui: UI, text: string, question = true): void {
  ui.cv.box(0, 111, 278, 120, 3);
  ui.cv.box(7, 66, 272, 97);
  ui.dfw(15, 68, 250, 27);
  if (question) { ui.para(text.trimEnd(), false); ui.put(" "); }
  else ui.para(text);
}

/** PART.LIB: `& CO: PRINT CF$; text` -- the text window is cleared and written again */
export function partText(ui: UI, text: string): void {
  ui.dfw(15, 68, 250, 27);
  ui.cv.clearText(8, 67, 271, 96);
  ui.para(text);
}

/** TOMB.LIB 50010 and 50105: the stone, and the words cut in it in inverse type */
export function tombstone(ui: UI, name: string, epitaph: string | null = null): void {
  ui.clear();
  ui.cv.screen("ts");
  ui.dfw(56, 62, 150, 45);
  ui.inverse = true;
  ui.line("Here lies", true, true);
  ui.line(name, true, true);
  ui.line("");
  if (epitaph !== null) ui.para(epitaph);
  ui.inverse = false;
}

/** `& DFW,7 AT 0,163,279,28` and `PRINT CF$`: the bottom window, cleared */
export function tombWindow(ui: UI): void {
  ui.cv.box(0, 163, 279, 190);
  ui.dfw(0, 163, 279, 28);
}

export async function tombBar(ui: UI, y = 182): Promise<string> {
  ui.cv.box(0, 180, 279, 191);                       // 950: & BOX,0,180,279,191
  return ui.waitKey("", "Press SPACE BAR to continue", { y, tune: true });     // 50010 and 50040 end GOSUB 950
}

/** END.LIB 50000-50010 */
export function dallesMenu(ui: UI, first = true): void {
  if (first) {
    ui.clear();
    ui.cv.image("oregon_10", 10, 20);
    ui.cv.image("oregon_10", 10, 160);
  } else ui.cv.box(10, 50, 278, 149);                // 50040: & BOX
  ui.dfw(10, 50, 269, 100);
  for (const t of ["The trail divides here.", "You may:", "", "", "1. float down the Columbia River",
    "", "2. take the Barlow Toll Road", "", ""]) ui.line(t);
  ui.put("What is your choice? ");
}

/** END.LIB 50020: `& BOX: & CO: PRINT : PRINT : PRINT ...` */
export function dallesToll(ui: UI, text: string): void {
  ui.cv.box(10, 50, 278, 149);
  ui.dfw(10, 50, 269, 100);
  ui.nl();
  ui.nl();
  ui.para(text.trimEnd(), false);
  ui.put(" ");
}

// ================================================================ the Top Ten and the score
/** MENU 2005-2015 and MANAGEMENT 900-915: the list, three columns, ten rows. Returns the row after it. */
export function topTen(ui: UI, entries: readonly (readonly unknown[])[], _headings = true): number {
  ui.clear();
  ui.cv.image("first_05", 55, 0);
  ui.dfw(0, 0, 280, 192);
  ui.inverse = true;
  for (const [x1, x2, tx, label] of [[30, 69, 34, "Name"], [126, 177, 130, "Points"], [204, 255, 208, "Rating"]] as [number, number, number, string][]) {
    ui.cv.box(x1, 18, x2, 29, 3);
    ui.co(tx, 20);
    ui.put(label);
  }
  ui.inverse = false;
  let y = 38;
  for (const [name, points, rating] of entries.slice(0, 10)) {
    ui.co(0, y);
    ui.put(String(name));
    ui.co(139, y);
    ui.padded(points, 4);
    ui.co(189, y);
    ui.put(String(rating));
    y += 9;
  }
  ui.co(0, y + 9);
  return y + 9;
}

/** MENU 2200-2235: the three pages that say how the points are earned */
export function howPoints(ui: UI, page: number, scoreText: readonly (readonly [string, unknown])[]): void {
  ui.clear();
  if (page < 2) ui.cv.image("first_06", 45, 0);
  if (page === 0) {
    ui.dfw(0, 20, 279, 171);
    ui.para("Your most important resource is the people you have with you.  You receive " +
      "points for each member of your party who arrives safely; you receive more " +
      "points if they arrive in good health!", true, 10, 0);
    ui.nl();
    const top = 20 + ui.cy - 4;                       // the bars sit behind the headings, wherever the paragraph ends
    ui.cv.box(6, top, 81, top + 20, 3);
    ui.cv.box(136, top, 229, top + 20, 3);
    ui.inverse = true;
    ui.co(10, ui.cy);
    ui.put("Health of");
    ui.co(140);
    ui.put("Points per");
    ui.nl();
    ui.co(10);
    ui.put("  Party");
    ui.co(140);
    ui.put("  Person");
    ui.inverse = false;
    ui.nl();
    ui.nl();
    for (const [word, pts] of scoreText.slice(0, 4)) {
      ui.co(10, ui.cy);
      ui.put(word);
      ui.co(166);
      ui.put(String(pts));
      ui.nl();
    }
  } else if (page === 1) {
    ui.dfw(0, 20, 279, 171);
    ui.para("The resources you arrive with will help you get started in the new land.  " +
      "You receive points for each item you bring safely to Oregon.");
    ui.nl();
    const top = 20 + ui.cy - 4;
    ui.cv.box(6, top, 107, top + 20, 3);
    ui.cv.box(156, top, 249, top + 20, 3);
    ui.inverse = true;
    ui.co(10, ui.cy);
    ui.put("Resources of");
    ui.co(160);
    ui.put("Points per");
    ui.nl();
    ui.co(10);
    ui.put("   Party");
    ui.co(160);
    ui.put("   Item");
    ui.inverse = false;
    ui.nl();
    ui.nl();
    for (const [word, pts] of scoreText.slice(4)) {
      ui.co(10, ui.cy);
      ui.put(word);
      ui.co(190);
      ui.padded(pts, 2);
      ui.nl();
    }
  } else {
    ui.cv.image("first_03", 10, 30);
    ui.cv.image("first_03", 10, 160);
    ui.dfw(21, 60, 255, 131);
    ui.para("You receive points for your occupation in the new land.  Because more farmers " +
      "and carpenters were needed than bankers, you receive double points upon " +
      "arriving in Oregon as a carpenter, and triple points for arriving as a farmer.");
  }
}

/** WIN 1005-605: the Willamette Valley, the date, then the congratulations */
export function winArrival(ui: UI, date: string): void { landmarkScreen(ui, 17, "The Willamette Valley, Oregon", date); }

/** WIN 606-622: the points table. `rows` are [text, points] pairs, already worded. Returns the cursor row. */
export function winPoints(ui: UI, rows: readonly (readonly [string, unknown])[], total: number, redraw = true): number {
  if (redraw) {
    ui.clear();
    ui.dfw(0, 0, 280, 192);
    const label = "Points for arriving in Oregon";
    const z = Math.trunc((label.length / 2 + 0.5) * 8);
    ui.cv.box(139 - z, 0, 139 + z, 11, 3);
    ui.co(0, 2);
    ui.inverse = true;
    ui.line(label, true, true);
    ui.inverse = false;
    ui.nl();
    ui.nl();
  } else {
    ui.dfw(0, 0, 280, 192);
    ui.cv.clearText(0, 29, 279, 135);                 // 610 prints the lines again over the old ones
    ui.co(0, 29);
  }
  for (const [text, pts] of rows) {
    const y = ui.cy;
    ui.put(text);
    ui.co(245, y);
    ui.padded(pts, 4);
    ui.nl();
  }
  ui.nl();
  ui.co(185);
  ui.put("Total:");
  ui.co(237);
  ui.padded(total, 5);
  ui.nl();
  ui.nl();
  ui.nl();
  return ui.cy;
}

// ================================================================ the trail itself
export const LABEL_X = [95, 70, 81, 95, 23, 20];     // B(0 to 5): where each label starts (monospace font)
export const COLON_X = 131;                           // where every label's colon ends: the original's colons line up

export interface TravelOptions {
  prompt?: string | null; message?: string | null; box?: readonly number[];
  pictures?: readonly (readonly [string, number, number])[]; lines?: string[]; centre?: boolean; plainBox?: unknown;
}

/**
 * OREGON TRAIL 300-320 and 3246: the wagon on the prairie, with the six facts below. `side` is "prairie"
 * (disk side 1) or "mountains" (side 2); `ni` is the picture of the approaching landmark and `ix` where it
 * has got to; `ground` is the colour of the ground (3 snow, 5 dry, 1 grass). Options: prompt (the line above
 * the facts, "Press RETURN to size up the situation"), message (a framed remark drawn over the scene), box
 * (default [28, 60, 250, 97]), pictures ([name, x, y] triples), lines, centre.
 */
export function travel(ui: UI, side: string, ni: number, ix: number, wg: number, ground: number,
  labels: readonly string[], values: readonly string[], opts: TravelOptions = {}): void {
  const { prompt = null, message = null, box = [28, 60, 250, 97], pictures = [], lines = [], centre = false } = opts;
  ui.clear();
  const cv = ui.cv;
  cv.backdrop(`sky_${side}`, 0, 0);
  cv.image(`${side}_04`, 0, 13);
  if (cv.plain) cv.box(0, 29, 279, 59, 0);            // the landmark and the wagon move across black, as in the original
  cv.box(0, 60, 278, 110, ground);
  cv.backdrop(`ground_${ground}`, 0, 60);
  if (ni) cv.image(`${side}_${String(ni).padStart(2, "0")}`, ix, 31);
  if (!(cv.plain && pictures.some(([n]) => n === "part_04"))) cv.image(`${side}_${String(wg).padStart(2, "0")}`, 186, 32);   // (a stopped party's own picture replaces the team)
  for (const [name, px, py] of pictures) cv.image(name, px, py);
  cv.panel(0, 111, 278, 179);
  if (prompt) {
    cv.box(0, 111, 279, 120);
    ui.dfw(0, 0, 280, 192);
    const saved = ui.hsp;
    ui.hsp = 1;
    ui.co(0, 112);
    ui.line(prompt, true, true);
    ui.hsp = saved;
  }
  ui.dfw(0, 0, 280, 192);
  ui.inverse = true;
  let y = 125;
  const n = Math.min(LABEL_X.length, labels.length);
  for (let i = 0; i < n; i++) { ui.co(COLON_X - ui.width(labels[i] + ":"), y); ui.put(labels[i] + ":"); y += 9; }   // placed by width so the colons line up in any font
  y = 125;
  for (const value of values) {
    ui.dfw(135, 125, 144, 57);
    ui.co(0, y - 125);
    ui.put(value);
    y += 9;
  }
  ui.inverse = false;
  if (message) messageBox(ui, message, box, { redraw: false, centre, lines });
}

/** OREGON TRAIL 3260: each day the first four facts are written again in their window (CE$ clears the rest
 *  of the line first); a stopped day leaves the miles alone. */
export function updateValues(ui: UI, values: readonly string[]): void {
  values.forEach((v, i) => {
    const y = 125 + 9 * i;
    ui.cv.box(135, y, 278, y + 8);
    ui.cv.panel(135, y, 278, y + 8);
    ui.dfw(135, 125, 144, 57);
    ui.co(0, 9 * i);
    ui.inverse = true;
    ui.put(v);
    ui.inverse = false;
  });
}

/** OREGON TRAIL 300-305: the landmark's picture with its name and the date across a white strip */
export function landmarkScreen(ui: UI, lm: number, name: string, date: string): void {
  ui.clear();
  ui.cv.screen(`l${lm}`);
  ui.cv.panel(0, 160, 278, 179);
  ui.inverse = true;
  ui.dfw(0, 0, 280, 192);
  ui.co(0, 162);
  ui.line(name, true, true);
  ui.line(date, true, true);
  ui.inverse = false;
}

// ==================================================================== the rivers
/** RIVER.LIB 3500 and 50001: ornaments top and bottom, the river's name and the date */
export function riverPage(ui: UI, name: string, date: string, headerY = 9): void {
  ui.clear();
  ui.cv.image("oregon_10", 10, 30);
  ui.cv.image("oregon_10", 10, 160);
  ui.dfw(0, 0, 280, 192);
  ui.co(0, headerY);
  ui.line(name, true, true);
  ui.line(date, true, true);
}

/** options: window (default [20, 60, 220, 119]), blank (default true), question */
export function riverText(ui: UI, text: string, opts: { window?: readonly number[]; blank?: boolean; question?: boolean } = {}): void {
  const { window = [20, 60, 220, 119], blank = true, question = false } = opts;
  ui.dfw(window[0], window[1], window[2], window[3]);
  if (blank) ui.nl();
  if (question) { ui.para(text.trimEnd(), false); ui.put(" "); }
  else ui.para(text);
}

/** RIVER.LIB 50025, 50080, 50100: `& BOX: & CO,,50: PRINT ...` in the menu window. Options: centre (default true). */
export function riverNotice(ui: UI, lines: readonly string[], opts: { centre?: boolean } = {}): void {
  const centre = opts.centre ?? true;
  ui.cv.box(0, 48, 279, 158);
  ui.dfw(0, 48, 279, 111);
  ui.co(0, 50);
  for (const t of lines) { if (centre) ui.line(t, true, true); else ui.para(t); }
}

/** `& BOX: & WIND,6`: the small window (30,70,230,89) cleared and made current. From the menu (window 7) the
 *  whole menu area goes; from window 6 itself only its own. */
export function riverWindow6(ui: UI, whole = false): void {
  if (whole) ui.cv.box(0, 48, 279, 158);
  else ui.cv.box(30, 70, 259, 158);
  ui.dfw(30, 70, 230, 89);
}

/** 50025: `& WIND: & CO,,18: & CEL: PRINT TD$ CC$` -- the date again after a day's camp */
export function riverDate(ui: UI, date: string): void {
  ui.dfw(0, 0, 280, 192);
  ui.cv.clearText(0, 18, 279, 26);
  ui.co(0, 18);
  ui.line(date, true, true);
}

/** RIVER.LIB 50010-50015 */
export function riverMenu(ui: UI, weather: string, width: string, depth: string, options: readonly string[], prompt = "What is your choice? "): void {
  ui.cv.box(0, 48, 279, 158);
  ui.dfw(0, 48, 279, 111);
  ui.line("Weather: " + weather);
  ui.line("River width: " + width + " feet");
  ui.line("River depth: " + depth + " feet");
  ui.co(0, ui.cy + 4);
  ui.line("You may:");
  ui.co(0, ui.cy + 4);
  options.forEach((t, i) => ui.line(`${i + 1}. ${t}`));
  ui.nl();
  ui.put(prompt);
}

/** CROSS.LIB 50000-50110: the framed water, then the first half of the crossing */
export function riverFrame(ui: UI, name: string, date: string, sprite: number): void {
  ui.clear();
  ui.dfw(0, 0, 280, 192);
  ui.co(0, 0);
  ui.line(name, true, true);
  ui.line(date, true, true);
  const cv = ui.cv;
  const [x1, y1, x2, y2] = [54, 20, 222, 140];
  cv.box(x1, y1, x2, y2);
  const add = (x: number, y: number): void => { cv.dots.add(y * 280 + x); };
  for (const l1 of [1, 2, 3]) {
    for (let x = x1 + l1; x <= x2 - l1; x++) { add(x, y1 + 4 - l1); add(x, y2 - 4 + l1); }
    for (let y = y1 + 4 - l1; y <= y2 - 4 + l1; y++) { add(x1 + l1, y); add(x2 - l1, y); }
  }
  for (let y = y1 + 4; y < y2 - 3; y++) { add(x1 + 4, y); add(x2 - 4, y); }     // white plots a dot either side: the bars are four wide
  cv.image("river_05", 58, 24);
  cv.image(`river_${String(sprite).padStart(2, "0")}`, 102, 63);
}

/** true when a person is watching the window (a scripted run has no pause set) */
function live(ui: UI): boolean { return (ui.dailyPause ?? 0) > 0; }

/** one line of a crossing's animation, shown at once when someone is watching */
async function stroke(ui: UI, x1: number, y1: number, x2: number, y2: number, colour: number): Promise<void> {
  ui.cv.line(x1, y1, x2, y2, colour);
  if (live(ui)) { ui.refresh(); await ui.sleep(0.04); }
}

/** CROSS.LIB 50010: blue lines fill the lower right */
export async function riverFirstHalf(ui: UI): Promise<void> {
  for (let l = 0; l < 53; l++) await stroke(ui, 114 + 2 * l, 136, 218, 77 + l, 6);
  if (ui.cv.plain) {                                  // whole-colour fill: close the dots the 2-column steps leave
    for (let l = 0; l < 53; l++) ui.cv.line(115 + 2 * l, 136, 218, 77 + l, 6);
    ui.cv.line(114, 136, 218, 136, 6);
    const deep = ui.cv.palette[4], water = ui.cv.palette[6];
    for (let y = 77; y < 137; y++) for (let x = 114; x < 219; x++) {   // and any dot of the deep water still showing
      const p = ui.cv.getPixel(x, y);
      if (p[0] === deep[0] && p[1] === deep[1] && p[2] === deep[2]) ui.cv.setPixel(x, y, water);
    }
  }
}

/** CROSS.LIB 50060: blue lines across the wagon */
export async function riverTailFailedFord(ui: UI): Promise<void> {
  for (let l = 0; l < 22; l++) await stroke(ui, 80 + 2 * l, 71, 180, 100 - l, 6);
}

/** CROSS.LIB 50030: black lines clear the upper left */
export async function riverTailSuccess(ui: UI): Promise<void> {
  // a themed folder draws a smaller wagon, so the clearing runs on until it reaches it
  const n = ui.cv.plain ? 74 : 61;
  for (let l = 0; l < n; l++) await stroke(ui, 58, 24 + l, 58 + 2 * l, 24, 4);
}
