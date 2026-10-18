/** OREGON TRAIL 10000 to 11400: the fifteen random events. Each draws exactly what Appendix F.4 lists. */
import * as N from "./num.js";
import * as D from "./data.js";
import type { Context } from "./context.js";
import * as C from "./common.js";
import * as T from "./trail.js";
import * as lf from "./lf.js";
import * as illness from "./illness.js";
import * as part from "./part.js";
import * as tomb from "./tomb.js";

export class UndefStatementError extends Error {}

const victim = (c: Context) => illness.chooseVictim(c, "10100 snakebite victim");

async function event0(c: Context) {
  c.eventPic = [["events_08", 130, 47]];
  await T.loseDays(c, "10000 snow bound days", 10, "Snow bound");
}
async function event1(c: Context) {
  const st = c.st;
  if (N.gt(st.TM, N.TWO)) {
    const who = victim(c);
    await C.message710(c, st.N[who] + " has " + D.IL_NAMES[D.SNAKEBITE] + ".");
    st.H1[who] = N.parse(String(D.SNAKEBITE));
    st.H2[who] = N.parse("10");
  }
}
/** line 10400: a grave the party passes */
async function event4(c: Context) {
  const text = "You pass a gravesite.  Would you like to look closer? ";
  if (c.ui.pictures) await T.scene(c, { prompt: c.st.LM !== c.st.NM, message: text, box: [0, 60, 278, 90] });
  else await c.ui.print(text);
  if ((await C.yesNo(c)) === "Y") await tomb.readGrave(c);
  T.findGrave(c);
}
async function event5(c: Context) {
  c.st.PF = N.add(c.st.PF, N.parse("30"));
  await C.message710(c, "Indians help find food.");
}
async function event6(c: Context) {
  const st = c.st;
  if (N.eq(st.TM, N.TWO) || N.eq(st.TM, N.parse("3"))) return;
  st.AR = N.add(st.AR, N.ONE);
  if (N.lt(st.TM, N.TWO)) {
    st.AR = N.sub(st.AR, N.ONE);
    st.AS = N.add(st.AS, N.parse("8"));
    c.eventPic = [["events_03", 105, 0]];
    await T.loseDays(c, "10602 blizzard days", 1, "Severe blizzard");
  } else {
    c.eventPic = [["events_01", 105, 0]];
    await T.loseDays(c, "10602 thunderstorm days", 1, "Severe thunderstorm");
  }
}
async function event7(c: Context) {
  const st = c.st;
  if (st.LM > 11 && N.lt(st.TM, N.parse("5"))) {
    if (c.rng.above("10700 fog delay", N.HALF)) await T.loseDays(c, "10700 fog days", 1, "Heavy fog");
    else await C.message710(c, "Heavy fog");
  } else if (st.LM <= 11 && N.gt(st.TM, N.parse("4"))) {
    c.eventPic = [["events_02", 118, 0]];
    await C.message710(c, "Hail storm.");
  }
}
async function event8(c: Context) {
  const st = c.st;
  if (c.rng.below("10800 part breaks", N.parse(".33"))) {
    st.B = N.trunc(N.add(N.int_(N.mul(c.rng.rnd1("10800 which part"), N.parse("3"))), N.parse("5")));
    await part.brokenPart(c);
    st.SD = 1;
    await T.runStoppedDays(c);
    if (!st.B) await c.ui.print("");
    return;
  }
  if (c.rng.below("10810 injury or ox", N.HALF)) {
    const who = victim(c);
    const which = N.trunc(N.mul(c.rng.rnd1("10830 arm or leg"), N.parse("2")));
    st.H1[who] = N.parse(String(which));
    st.H2[who] = N.parse("30");
    await C.message710(c, st.N[who] + " has " + D.IL_NAMES[which] + ".");
    return;
  }
  st.I[2] = N.sub(st.I[2], N.HALF);
  const word = !N.eq(st.I[2], N.int_(st.I[2])) ? "is injured." : "has died.";
  await C.message710(c, "One of the oxen " + word);
  T.speed(c);
  await T.checkOxen(c);
}
async function event9(c: Context) {
  let label = "Lose trail";
  if (c.rng.below("10900 which message", N.HALF)) label = "Wrong trail";
  await T.loseDays(c, "10900 lost trail days", 5, label);
}
async function event10(c: Context) {
  const st = c.st;
  if (c.rng.below("11000 rough or impassible", N.HALF)) {
    await C.message710(c, "Rough trail");
    st.HR = N.parse("10");
    return;
  }
  await T.loseDays(c, "11010 impassible days", 10, "Impassible trail");
}
async function event11(c: Context) {
  c.st.PF = N.add(c.st.PF, N.parse("20"));
  c.eventPic = [["events_06", 150, 32]];
  await C.message710(c, "Find wild fruit.");
}
async function event12(c: Context) {
  const st = c.st;
  const which = N.trunc(N.mul(c.rng.rnd1("11200 which"), N.parse("3")));
  if (which === 0) {
    const losses = lf.fire(c);
    if (losses.length) {
      c.eventPic = [["events_05", 184, 32]];
      await C.message900(c, "A fire in the wagon results in loss of:", losses);
    }
    return;
  }
  if (which === 1) {
    const who = victim(c);
    await T.loseDays(c, "11250 lost member days", 5, st.N[who] + " is lost");
    return;
  }
  await T.loseDays(c, "11275 stray ox days", 3, "Ox wanders off");
}
async function event13(c: Context) {
  if (c.rng.below("11300 thief or wagon", N.HALF)) {
    const stolen = lf.thief(c);
    if (stolen.length) {
      c.eventPic = [["events_07", 263, 35]];
      await C.message900(c, stolen[0], [""]);
    }
    T.speed(c);
    await T.checkOxen(c);
    return;
  }
  const found = lf.abandonedWagon(c);
  await C.message900(c, "You find an abandoned wagon" + (found.length ? " with the following:" : ", but it is empty."), found);
}
async function event14(c: Context) {
  const st = c.st;
  if (c.rng.below("11400 bad water", N.parse(".2"))) { st.HR = N.parse("20"); await C.message700(c, "Bad water"); return; }
  if (c.rng.below("11410 little water or grass", N.HALF)) { st.HR = N.parse("10"); await C.message700(c, "Very little water"); return; }
  await C.message700(c, "Inadequate grass");
}

/** line 3180's ON L8 + 1 GOSUB list. Entry 2 names a line the program lacks; RE(2) is 0 so it cannot be reached. */
export async function fire(c: Context, which: number): Promise<void> {
  const table: (((c: Context) => Promise<void>) | null)[] = [
    event0, event1, null, illness.illness, event4, event5, event6, event7, event8, event9, event10, event11, event12, event13, event14,
  ];
  const f = table[which];
  if (!f) throw new UndefStatementError("event 2 dispatches to 10200, which is not in the program: the original would raise UNDEF'D STATEMENT");
  await f(c);
}
