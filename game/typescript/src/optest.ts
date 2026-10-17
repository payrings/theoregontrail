// Dev check: replays operand/result lines produced by Python's `exact` backend (see compare.py).
import * as N from "./num.js";
import { readFileSync } from "node:fs";
const fromHex = (h: string) => Array.from({ length: 5 }, (_, i) => parseInt(h.slice(i * 2, i * 2 + 2), 16));
let bad = 0, n = 0;
for (const line of readFileSync(process.argv[2], "utf8").split("\n")) {
  if (!line) continue;
  const [ah, ae, bh, be, opn, ...rest] = line.split(" ");
  const want = rest.join(" ");
  const a = new N.Fac(fromHex(ah), parseInt(ae, 16));
  const b = bh === "-" ? N.ZERO : new N.Fac(fromHex(bh), parseInt(be, 16));
  let out: string;
  try {
    const hx = (r: N.Fac) => r.b.map((v) => v.toString(16).padStart(2, "0")).join("") + ":" + r.ext.toString(16).padStart(2, "0");
    if (opn === "cmp") out = String(N.cmp(a, b));
    else if (opn === "int_") out = hx(N.int_(a));
    else if (opn === "round") out = N.store(a).b.map((v) => v.toString(16).padStart(2, "0")).join("");
    else if (opn === "str_") out = N.str_(a);
    else out = hx((N as any)[opn](a, b));
  } catch (e: any) { out = "ERR" + (e.code ?? "?"); }
  n++;
  if (out !== want) { bad++; if (bad <= 10) console.log("DIFF", line, "got", out); }
}
console.log(`${n} checked, ${bad} differ`);
