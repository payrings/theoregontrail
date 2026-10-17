/** The game's tables: landmarks and segments, rivers, climate, goods, text. */

export const LM_NAMES = [
  "Independence", "the Kansas River crossing", "the Big Blue River crossing", "Fort Kearney",
  "Chimney Rock", "Fort Laramie", "Independence Rock", "South Pass", "Fort Bridger",
  "Green River crossing", "Soda Springs", "Fort Hall", "the Snake River crossing", "Fort Boise",
  "the Blue Mountains", "Fort Walla Walla", "The Dalles", "the Willamette Valley",
];
/** 0 neither, 1 a fort, 2 a river */
export const LM_TYPE = [1, 2, 2, 1, 0, 1, 0, 0, 1, 2, 0, 1, 2, 1, 0, 1, 0, 0];
export const LM_SEGMENT = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 17, 18, 99];
export const LM_SEGMENT2 = [0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0, 16, 0, 0, 0];
export const SEG_MILES = [102, 83, 119, 250, 86, 190, 102, 57, 125, 162, 144, 57, 182, 114, 160, 55, 125, 120, 100];
export const SEG_SPEED = [20, 20, 20, 20, 20, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12];
export const SEG_ENDS_AT = [1, 2, 3, 4, 5, 6, 7, 9, 8, 10, 10, 11, 12, 13, 14, 15, 16, 16, 17];

export const zoneFor = (lm: number) => +(lm > 2) + +(lm > 5) + +(lm > 10) + +(lm > 13);
export function shortName(n: number): string {
  const name = LM_NAMES[n];
  return name.slice(0, 4).toLowerCase() === "the " ? name.slice(4) : name;
}

/** depth, width, swiftness, bottom (0 smooth, 1 muddy, 2 rough), unused, extra option (1 guide, 2 ferry) */
export const RC = [
  [1, 600, 3, 0, 3, 2],
  [1, 220, 2, 1, 2, 0],
  [20, 400, 5, 2, 12, 2],
  [6, 1000, 7, 2, 9, 1],
];
export const RC_RIVER_AT: Record<number, number> = { 1: 0, 2: 1, 9: 2, 12: 3 };
export const MUDDY = 1, ROUGH = 2;
export const RIVER_T = [
  "attempt to ford the river", "caulk wagon and float it across", "wait to see if conditions improve",
  "get more information", "hire an Indian to help", "take a ferry across",
];

/** WC$(0 to 5): one temperature code and one rain code per month */
export const WC = [
  ";+?,I8V?_NiNnElFdHY<K1@-",
  "5#:#B(O3Y<c?i9g4].Q(C#9#",
  "5#9#>'H.R3\\+e(c$X'M'?%8#",
  "1#6%>*I5R7[+c&a#W)L,=&3$",
  "<-B+H+P*X*_'h!f!]$R(F+>,",
  "DWIGLBQ5W3[.`#`(]/T?LTG^",
];

/** name, base price, unit, plural ending */
export const GOODS: [string, number, string, string][] = [
  ["Oxen", 20.0, "ox", "en"], ["Clothing", 10.0, "set", "s"], ["Ammunition", 2.0, "box", "es"],
  ["Wagon wheels", 10.0, "wheel", "s"], ["Wagon axles", 10.0, "axle", "s"],
  ["Wagon tongues", 10.0, "tongue", "s"], ["Food", 0.2, "pound", "s"],
];
/** the price as Python prints it (str of a float), which the converter reads */
export const PRICE_TEXT = ["20.0", "10.0", "2.0", "10.0", "10.0", "10.0", "0.2"];
export const UNIT = GOODS.map((g) => g[2]);

export const IL_NAMES = ["a broken arm", "a broken leg", "a snakebite", "exhaustion", "typhoid", "cholera", "measles", "dysentery", "a fever"];
export const SNAKEBITE = 2;
export const DEATH_SENTENCE = "died";

export const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export const I_NAMES = ["", "Wagon", "oxen", "sets of clothing", "bullets", "wagon wheels", "wagon axles", "wagon tongues", "pounds of food"];
export const PACE = ["steady", "strenuous", "grueling"];
export const RATIONS = ["filling", "meager", "bare bones"];
export const HEALTH = ["good", "fair", "poor", "very poor"];
export const WEATHER = ["very cold", "cold", "cool", "warm", "hot", "very hot", "rainy", "snowy", "very rainy", "very snowy"];
export const ACTIONS = ["Continue on trail", "Check supplies", "Look at map", "Change pace", "Change food rations", "Stop to rest", "Attempt to trade", "Talk to people", "Buy supplies", "Hunt for food"];
export const TRAVEL_LABELS = ["Press RETURN to size up the situation", "Date", "Weather", "Health", "Food", "Next landmark", "Miles traveled"];
export const RATINGS = ["Trail guide", "Adventurer", "Greenhorn"];
export const healthWord = (band: number) => (band >= 0 && band < HEALTH.length ? HEALTH[band] : "");

export const GOODS_NAME = GOODS.map((g) => g[0]);
export const GOODS_PLURAL = GOODS.map((g) => g[3]);

export const DEFAULT_NAMES = ["Zeke", "Jed", "Anna", "Mary", "Joey", "Beth", "John", "Sara", "Henry", "Emily"];
export const SCORE_TEXT: [string, number][] = [
  ["good", 500], ["fair", 400], ["poor", 300], ["very poor", 200],
  ["wagon", 50], ["ox", 4], ["spare wagon part", 2], ["set of clothing", 2],
  ["bullets (each 50)", 1], ["food (each 25 pounds)", 1], ["cash (each 5 dollars)", 1],
];
export const PROFESSIONS = ["banker from Boston", "carpenter from Ohio", "farmer from Illinois"];
export const MANAGE_OPTIONS = [
  "See the current Top Ten list", "See the original Top Ten list", "Erase the current Top Ten list",
  "Erase the tombstone messages", "Return to main menu",
];
export const MONTH_CHOICES = ["March", "April", "May", "June", "July"];
export const SOUND_WORDS = ["off", "on"];
export const STORE_PART_NAMES: [string, number][] = [["wagon wheel", 10], ["wagon axle", 10], ["wagon tongue", 10]];
export const STORE_MONTHS = ["February", "March", "April", "May", "June", "July"];
export const STORE_ITEMS = ["Covered wagon", "Oxen", "Food", "Clothing", "Ammunition", "Spare parts"];

const ORIGINAL_TOP_TEN: [string, number, string][] = [
  ["Stephen Meek", 7650, "Trail guide"], ["David Hastings", 5694, "Adventurer"],
  ["Andrew Sublette", 4138, "Adventurer"], ["Celinda Hines", 2945, "Greenhorn"],
  ["Ezra Meeker", 2052, "Greenhorn"], ["William Vaughn", 1401, "Greenhorn"],
  ["Mary Bartlett", 937, "Greenhorn"], ["William Wiggins", 615, "Greenhorn"],
  ["Charles Hopper", 396, "Greenhorn"], ["Elijah White", 250, "Greenhorn"],
];
export function originalTopTen(): [string, number, string][] { return ORIGINAL_TOP_TEN.map((e) => [...e] as [string, number, string]); }

/** L%(NM - 1, 0 to 1): the picture number and offset of the landmark being approached (graphical mode only) */
export const SCENERY: [number, number][] = [[8, 78], [8, 78], [5, 50], [6, 36], [7, 50], [6, 36], [7, 56], [8, 56], [14, 78],
  [9, 64], [10, 70], [14, 78], [11, 56], [15, 56], [12, 56], [13, 112], [16, 50]];
