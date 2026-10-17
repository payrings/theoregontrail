/**
 * What the game may ask of the screen and the keyboard (the Python rebuild's ui.py).
 *
 * Every method that waits for the person may return a promise, so a browser can answer when a key is
 * pressed; the self-playing front end answers at once. Game logic never touches a terminal or a page.
 */
export const RETURN_KEYS = ["\r", "\n"];

type Maybe<T> = T | Promise<T>;

/** the `& INP` character sets; a range is written dash-first, so 1 to 5 is "-15" */
export const ALLOWED = {
  YN: "YESNOyesno", NAMES: "-AZ-az '.-", TOPTEN: "-AZ-az .'-", EPITAPH: "-09-AZ-az ,.'-",
  DIGITS09: "-09", DIGITS19: "-19", CHOICE: "\x011234", PROFESSION: "-1234", MANAGE: "-15", MONTH: "-16",
  PACE: "-14", RATION: "-13", SEGMENT: "-13", DALLES: "-12", RIVER: "-15", FORT: "-18", REST: "-09",
  STORE_ITEM: "-15", STORE_YOKE: "-19", STORE_FOOD: "-09", STORE_CLOTHES: "-09", STORE_AMMO: "-09", STORE_PART: "-09",
} as const;

/** the characters an `& INP` set permits */
export function allowedChars(spec: string): Set<string> {
  const out = new Set<string>();
  let i = 0;
  const n = spec.length;
  while (i < n) {
    if (spec[i] === "-" && i + 2 < n) {
      let lo = spec.charCodeAt(i + 1), hi = spec.charCodeAt(i + 2);
      if (lo > hi) [lo, hi] = [hi, lo];
      for (let c = lo; c <= hi; c++) out.add(String.fromCharCode(c));
      i += 3;
    } else { out.add(spec[i]); i += 1; }
  }
  return out;
}

export interface UI {
  /** true only for the graphical front end, whose screens draw themselves */
  pictures: boolean;
  /** show the travel screen every day (a person can press Return to interrupt) */
  showDailyScreen: boolean;
  /** seconds a day's scene stays up; 0 for a script */
  dailyPause: number;
  /** everything printed, for the tests */
  out: string[];
  /** a real keyboard: the time spent waiting for a key feeds the seed (MENU 1015) */
  countsKeyboardTime?: boolean;
  /** the graphical screens (browser build) */
  screens?: any;
  print(text?: string): Maybe<void>;
  clear(): Maybe<void>;
  key(allowed?: string, maxlen?: number, def?: string, ret?: boolean): Maybe<string>;
  yesNo(prompt?: string): Maybe<string>;
  waitKey(allowed?: string, prompt?: string, opts?: { y?: number; tune?: boolean }): Maybe<string>;
  pollKey(): string | null;
  flipDisk(side: number, title?: string): Maybe<string>;
  /** let time pass (seconds): the browser waits, a script does not */
  sleep?(seconds: number): Maybe<void>;
  // the `&` drawing commands the text screens still mention; nothing to do in plain text
  at?(x: number, y: number): void;
  box?(...a: number[]): void;
  lineTo?(): void;
}

type Driver = AutoUI;
type Answer = string | string[] | ((d: Driver) => string);

function tradeAnswer(d: Driver): string {
  let offer = "";
  for (const line of d.out.slice(d.since)) if (line.includes("will trade you")) offer = line;
  if (!offer) return "Y";
  if (d.mustTrade && offer.includes(d.mustTrade)) return "Y";
  return offer.includes("food") ? "Y" : "N";
}

function riverAnswer(d: Driver): string {
  let depth: number | null = null;
  const choices = new Map<string, string>();
  for (const line of d.out.slice(d.since)) {
    const t = line.trim();
    let m = /^River depth:\s+([0-9.]+)\s+feet/.exec(t);
    if (m) depth = parseFloat(m[1]);
    m = /^(\d)\. (.*)/.exec(t);
    if (m) choices.set(m[2].toLowerCase(), m[1]);
  }
  if (depth === null) throw new Error("the river menu is on screen but its depth could not be read");
  d.riverAsks += 1;
  const pick = (word: string): string | null => {
    for (const [label, number] of choices) if (label.includes(word)) return number;
    return null;
  };
  const ford = pick("ford") || "1";
  const floating = pick("float") || pick("caulk") || "2";
  if (depth < 2.5) return ford;
  if (d.riverAsks > 1) return floating;
  return pick("ferry") || pick("indian") || pick("guide") || floating;
}

/** the action-menu lines on screen, as label -> number */
function menuChoices(d: Driver): Map<string, string> {
  const out = new Map<string, string>();
  for (const line of d.out.slice(d.since)) {
    const m = /^(\d+)\. (.*)$/.exec(line.trim());
    if (m) out.set(m[2], m[1]);
  }
  return out;
}

/**
 * The wandering policy: it also uses the pace and rations screens, rests, trades, talks, hunts, shops at
 * forts and floats down the Columbia, so the checks reach code the plain demo never runs. Which of those it
 * does at each action menu is fixed by how many menus it has seen, so a game is still a function of its seed.
 */
const WANDER_CYCLE = ["Change pace", "Change food rations", "Stop to rest", "Attempt to trade", "Talk to people",
  "Buy supplies", "Hunt for food", "Check supplies", "Look at map"];

function wanderAction(d: Driver): string {
  const choices = menuChoices(d);
  if (!choices.has("Continue on trail")) return "1";
  if (d.wanderQueue === null) {
    d.wanderMenus += 1;
    const n = d.wanderMenus;
    d.wanderQueue = WANDER_CYCLE.filter((_, i) => ((n * 2654435761) >>> (i + 3)) & 1);
  }
  while (d.wanderQueue.length) {
    const label = d.wanderQueue.shift() as string;
    const number = choices.get(label);
    if (number) return number;
  }
  d.wanderQueue = null;
  return choices.get("Continue on trail") as string;
}

function cycle(d: Driver, name: string, values: string[]): string {
  const k = d.counters.get(name) || 0;
  d.counters.set(name, k + 1);
  return values[k % values.length];
}

export class AutoUI implements UI {
  pictures = false;
  showDailyScreen = false;
  dailyPause = 0;
  out: string[] = [];
  since = 0;
  prompts = 0;
  maxPrompts = 4000;
  mustTrade = "";
  riverAsks = 0;
  rules: [string, Answer][];
  wander: boolean;
  wanderMenus = 0;
  wanderQueue: string[] | null = null;
  counters = new Map<string, number>();

  static readonly RIVER_FOLLOW_UPS = ["Are you willing to do this?", "Will you accept this"];

  constructor(wander = false) {
    this.wander = wander;
    if (wander) this.maxPrompts = 20000;
    const base: [string, Answer][] = [
      ["first name of the wagon leader", "Zeke"],
      ["Are these names correct", "Y"],
      ["Ask for advice", "2"],
      ["Which item would you like to", ["1", "2", "3", "4", "5", ""]],
      ["want?", ["4", "2000", "10", "6", "3", "3", "3"]],
      ["How many wagon", ["1", "1", "1"]],
      ["Would you like to look around?", "N"],
      ["River depth:", riverAnswer],
      ["Are you willing to do this?", "Y"],
      ["Will you accept this", "Y"],
      ["The trail divides here", ["1", "1"]],
      ["float down the Columbia River", "2"],
      ["to travel the Barlow road", "Y"],
      ["You must trade for", "7"],
      ["another emigrant", tradeAnswer],
      ["Broken wagon", "Y"],
      ["Change food rations", ["2", "3"]],
      ["Continue on trail", "1"],
      ["What is your choice?", "1"],
    ];
    let rules = base;
    if (wander) {
      const front: [string, Answer][] = [
        ["The pace at which you travel", (d) => cycle(d, "pace", ["2", "4", "1", "3", "2"])],
        ["The amount of food the people in your party", (d) => cycle(d, "rations", ["2", "3", "1"])],
        ["How many days would you like to rest", (d) => cycle(d, "rest", ["2", "5", "1", "9"])],
        ["Which number?", (d) => cycle(d, "fort", ["7", "1", "2", "8"])],
        ["Would you like to look around?", (d) => cycle(d, "look", ["Y", "N", "N", "Y"])],
        ["float down the Columbia River", (d) => cycle(d, "dalles", ["1", "2"])],
        ["Would you like to write", "Y"],
        ["What would you like on the tombstone?", "Rest here"],
        ["Would you like to make", "N"],
        ["You pass a gravesite", "Y"],
      ];
      // the store's own quantity prompts come first; the fort's "How many ...?" follow them
      const rest = base.map((r) => (r[0] === "Continue on trail" ? ["Continue on trail", wanderAction] as [string, Answer] : r));
      rules = [...front, ...rest.slice(0, 6), ["How many", (d) => cycle(d, "many", ["1", "50", "2", "20", "3"])], ...rest.slice(6)];
    }
    this.rules = rules.map(([n, a]) => [n, Array.isArray(a) ? [...a] : a] as [string, Answer]);
  }

  private ask(): string {
    const recent = this.out.slice(this.since).join("\n");
    for (const [needle, answer] of this.rules) {
      if (recent.includes(needle)) {
        const keep = answer === riverAnswer || AutoUI.RIVER_FOLLOW_UPS.includes(needle);
        if (!keep) this.riverAsks = 0;
        if (typeof answer === "function") return answer(this);
        if (Array.isArray(answer)) {
          if (answer.length) return String(answer.shift());
          continue;
        }
        return String(answer);
      }
    }
    return "";
  }

  print(text = ""): void {
    if (text.includes("You must trade for")) {
      for (const item of ["ox", "wheel", "axle", "tongue"]) if (text.includes(item)) this.mustTrade = item;
    }
    this.out.push(text);
  }
  clear(): void { this.out.push("<clear>"); }
  key(_allowed = "", maxlen = 1, _default = "", _ret = true): string {
    const a = this.ask();
    this.since = this.out.length;
    this.prompts += 1;
    if (this.prompts > this.maxPrompts) throw new Error(`the demo asked ${this.prompts} questions and gave up`);
    return maxlen ? a.slice(0, maxlen) : a;
  }
  yesNo(prompt = ""): string {
    if (prompt) this.print(prompt);
    for (let i = 0; i < 64; i++) {
      const z = this.key(ALLOWED.YN, 3);
      if (z) return z[0].toUpperCase();
    }
    return "N";
  }
  waitKey(): string { return " "; }
  pollKey(): string | null { return null; }
  flipDisk(side: number): string { return side === 1 || side === 2 ? String(2 - side) : String(side); }
  at(): void {}
  box(): void {}
  lineTo(): void {}
}
