/**
 * Sound for the graphical mode (the Python rebuild's graphics/sound.py and tunes.py).
 *
 * The BASIC calls `& PT` in two places only: the wait for a key (line 955, the tune in memory, repeated
 * until a key) and a raft collision (line 740, four runs of tune 1). Control-S switches the sound on and
 * off (memory byte 975, read through `Sound.enabled`).
 *
 * Everything that makes samples is a pure function returning a Float32Array (testable in Node); only
 * `WebAudioOut` touches the browser, and it creates its AudioContext lazily, on the first key press.
 *
 * Which tune plays at a key-wait:
 *  - if the player supplied the tune files of a disk they own (MS0.BIN ... MS17.BIN and TS.BIN, as saved by
 *    `tools/dump_tunes.py --extract`), the original's own notes: four header bytes, then (pitch, duration)
 *    byte pairs until a byte of 128 or more; pitch p is 76.8 * 2^((p-1)/12) Hz (0 is a rest) and a duration
 *    unit is 0.00576 s (dump_tunes.py's figures, from the sound routine's timing loop). They are read at
 *    run time and kept only in memory;
 *  - otherwise a made-up tune of the same length, composed here from a seed, a key and a scale.
 * The raft's collision is always the made-up soft whumps.
 */

export const RATE = 22050;
export const STEP = 0.17;                  // seconds in one step of a made-up tune

// ------------------------------------------------------------------ Python's random, to compose the same tunes
/** Mersenne Twister as Python's `random.Random(seed)` uses it (seeded by init_by_array of the integer) */
export class PyRandom {
  private mt = new Uint32Array(624);
  private idx = 624;
  constructor(seed: number) {
    this.initGenrand(19650218);
    const key: number[] = [];
    let s = Math.abs(seed);
    do { key.push(s >>> 0); s = Math.floor(s / 4294967296); } while (s > 0);
    let i = 1, j = 0;
    const mt = this.mt;
    for (let k = Math.max(624, key.length); k > 0; k--) {
      mt[i] = ((mt[i] ^ Math.imul(mt[i - 1] ^ (mt[i - 1] >>> 30), 1664525)) + key[j] + j) >>> 0;
      i++; j++;
      if (i >= 624) { mt[0] = mt[623]; i = 1; }
      if (j >= key.length) j = 0;
    }
    for (let k = 623; k > 0; k--) {
      mt[i] = ((mt[i] ^ Math.imul(mt[i - 1] ^ (mt[i - 1] >>> 30), 1566083941)) - i) >>> 0;
      i++;
      if (i >= 624) { mt[0] = mt[623]; i = 1; }
    }
    mt[0] = 0x80000000;
    this.idx = 624;
  }
  private initGenrand(s: number): void {
    const mt = this.mt;
    mt[0] = s >>> 0;
    for (let i = 1; i < 624; i++) mt[i] = (Math.imul(mt[i - 1] ^ (mt[i - 1] >>> 30), 1812433253) + i) >>> 0;
  }
  private next32(): number {
    const mt = this.mt;
    if (this.idx >= 624) {
      for (let k = 0; k < 624; k++) {
        const y = (mt[k] & 0x80000000) | (mt[(k + 1) % 624] & 0x7fffffff);
        mt[k] = mt[(k + 397) % 624] ^ (y >>> 1) ^ (y & 1 ? 0x9908b0df : 0);
      }
      this.idx = 0;
    }
    let y = mt[this.idx++];
    y ^= y >>> 11; y ^= (y << 7) & 0x9d2c5680; y ^= (y << 15) & 0xefc60000; y ^= y >>> 18;
    return y >>> 0;
  }
  random(): number { const a = this.next32() >>> 5, b = this.next32() >>> 6; return (a * 67108864 + b) / 9007199254740992; }
  private randbelow(n: number): number {
    const k = 32 - Math.clz32(n);
    let r = this.next32() >>> (32 - k);
    while (r >= n) r = this.next32() >>> (32 - k);
    return r;
  }
  choice<T>(seq: readonly T[]): T { return seq[this.randbelow(seq.length)]; }
}

// ------------------------------------------------------------------------------------- made-up tunes
/** how long each original tune plays (seconds), from its tune file */
export const SECONDS: Record<string, number> = {
  ms0: 16.4, ms1: 16.3, ms2: 37.3, ms3: 25.9, ms4: 22.1, ms5: 16.6, ms6: 33.2, ms7: 24.8, ms8: 16.6, ms9: 29.5,
  ms10: 12.4, ms11: 8.3, ms12: 20.7, ms13: 12.4, ms14: 29.5, ms15: 27.2, ms16: 16.5, ms17: 16.6, ts: 18.7,
};
const MAJOR = [0, 2, 4, 7, 9], MINOR = [0, 3, 5, 7, 10], SUS = [0, 2, 5, 7, 9];
/** key (semitones from A4 of the tonic), scale, seed: a different mood for each place */
const SETTINGS: Record<string, [number, number[], number]> = {
  ms0: [-9, MAJOR, 11], ms1: [-7, MAJOR, 12], ms2: [-4, SUS, 13], ms3: [-2, MAJOR, 14], ms4: [-5, MINOR, 15],
  ms5: [-9, SUS, 16], ms6: [-7, MINOR, 17], ms7: [0, MAJOR, 18], ms8: [-4, MAJOR, 19], ms9: [-2, SUS, 20],
  ms10: [-9, MINOR, 21], ms11: [-5, MAJOR, 22], ms12: [-7, SUS, 23], ms13: [-2, MINOR, 24], ms14: [-4, SUS, 25],
  ms15: [-9, MAJOR, 26], ms16: [-5, SUS, 27], ms17: [-9, MAJOR, 28], ts: [-12, MINOR, 29],
};
const BARS = [[2, 1, 1, 2, 2], [1, 1, 2, 2, 2], [2, 2, 1, 1, 2], [3, 1, 2, 2], [2, 2, 2, 2], [1, 1, 1, 1, 2, 2], [4, 2, 2], [2, 1, 1, 4], [3, 1, 4], [2, 2, 4]];
const SLOW_BARS = [[4, 4], [2, 2, 4], [3, 1, 4], [2, 2, 2, 2], [4, 2, 2]];

export type Step = [number | null, number];            // semitones from A4 (or null for a rest), steps

export const tuneNames = (): string[] => Object.keys(SECONDS);
const degreeToSemis = (root: number, scale: number[], degree: number): number => root + 12 * Math.floor(degree / 5) + scale[degree % 5];

function phrase(rng: PyRandom, slow: boolean, endDegree: number, start: number | null = null): Step[] {
  const bank = slow ? SLOW_BARS : BARS;
  const out: Step[] = [];
  let d = start !== null ? start : rng.choice([0, 2, 4]);
  for (let bar = 0; bar < 2; bar++) {
    const rhythm = rng.choice(bank);
    rhythm.forEach((length, i) => {
      const last = bar === 1 && i === rhythm.length - 1;
      if (last) d = endDegree;
      else { d += rng.choice([-2, -1, -1, 0, 1, 1, 2]); d = Math.max(0, Math.min(7, d)); }
      // Python: `if rng.random() < 0.06 and not last and i > 0` -- random() is drawn first, always
      if (rng.random() < 0.06 && !last && i > 0) out.push([null, length]);
      else out.push([d, length]);
    });
  }
  return out;
}

function vary(rng: PyRandom, ph: Step[], endDegree: number): Step[] {
  const keep = ph.length - 3;
  const head = ph.slice(0, keep);
  let d = 0;
  for (let i = head.length - 1; i >= 0; i--) if (head[i][0] !== null) { d = head[i][0] as number; break; }
  const tail: Step[] = [];
  ph.slice(keep).forEach(([, length], i) => {
    if (i === ph.length - keep - 1) d = endDegree;
    else d = Math.max(0, Math.min(7, d + rng.choice([-2, -1, 1, 2])));
    tail.push([d, length]);
  });
  return head.concat(tail);
}

/** (melody, bass): each a list of (semitones from A4 or null, steps) */
export function melodyAndBass(name: string): [Step[], Step[]] {
  const [root, scale, seed] = SETTINGS[name];
  const rng = new PyRandom(seed);
  // Python's round() is banker's rounding; every length here divides to a non-half value
  const total = Math.round(SECONDS[name] / STEP);
  const slow = name === "ts";
  const phrasesN = Math.max(1, Math.floor(total / 16));
  const extra = total - 16 * phrasesN;
  let a = phrase(rng, slow, 2);
  if (name === "ms0") a = [[0, 1], [2, 1], [3, 1], [2, 1], [4, 2], [3, 2], [2, 1], [1, 1], [0, 3], [null, 1]];
  const b = phrase(rng, slow, 4);
  const c = phrase(rng, slow, 3, 4);
  const pool: Record<string, Step[]> = { A: a, B: b, C: c };
  const form = ["A", "B", "A", "C"];
  const seq: Step[][] = [];
  for (let i = 0; i < phrasesN; i++) {
    const key = form[i % 4];
    let ph = pool[key];
    if (i >= 4) ph = vary(rng, ph, { A: 2, B: 4, C: 3 }[key] as number);
    seq.push(ph);
  }
  // the last phrase comes home: its last note becomes the tonic, held through the spare steps
  const last = seq[seq.length - 1].slice();
  while (last.length && last[last.length - 1][0] === null) last.pop();
  const length = last[last.length - 1][1];
  const sum = last.reduce((s, [, n]) => s + n, 0);
  last[last.length - 1] = [0, length + extra + (sum < 16 ? 16 - sum : 0)];
  seq[seq.length - 1] = last;
  const melody: Step[] = [];
  for (const ph of seq) for (const [d, n] of ph) melody.push([d === null ? null : degreeToSemis(root, scale, d), n]);
  const have = melody.reduce((s, [, n]) => s + n, 0);
  if (have < total) { const [s, n] = melody[melody.length - 1]; melody[melody.length - 1] = [s, n + total - have]; }
  const bass: Step[] = [];
  const bars = Math.floor(total / 8);
  for (let i = 0; i < bars; i++) {
    const deg = i % 4 === 0 || i % 4 === 3 ? 0 : i % 4 === 1 ? 4 : 3;
    bass.push([degreeToSemis(root, scale, deg) - 12, 8]);
  }
  if (total - 8 * bars) bass.push([root - 12, total - 8 * bars]);
  return [melody, bass];
}

// ----------------------------------------------------------------------------------------- synthesis
const hz = (semis: number): number => 440 * 2 ** (semis / 12);

/** a triangle wave with a gentle attack and a slow fade; `slide` bends the pitch down */
export function soft(freq: number, seconds: number, volume = 0.32, decay = 3.0, slide = 0.0): number[] {
  const n = Math.trunc(RATE * seconds);
  const out: number[] = new Array(n);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / n;
    const f = freq ? freq * (1 - slide * t) : 0;
    phase = (phase + f / RATE) % 1;
    const tri = freq ? 4 * Math.abs(phase - 0.5) - 1 : 0;
    const attack = Math.min(1, i / (RATE * 0.02));
    out[i] = tri * volume * attack * Math.exp(-decay * t);
  }
  return out;
}

function voice(steps: Step[], volume: number, decayLong: number, decayShort: number, lift = 0): number[] {
  const out: number[] = [];
  for (const [semis, n] of steps) {
    if (semis === null) { const z = Math.trunc(RATE * n * STEP); for (let i = 0; i < z; i++) out.push(0); }
    else for (const v of soft(hz(semis + lift), n * STEP, volume, n > 1 ? decayLong : decayShort)) out.push(v);
  }
  return out;
}

/** the made-up tune named, melody over a soft low bass */
export function waitTune(name = "ms0", repeats = 1): Float32Array {
  const [melody, bass] = melodyAndBass(name);
  const top = voice(melody, 0.30, 1.6, 2.4), low = voice(bass, 0.16, 0.9, 0.9);
  const n = Math.max(top.length, low.length);
  const one = new Float32Array(n);
  for (let i = 0; i < n; i++) one[i] = (top[i] ?? 0) + (low[i] ?? 0);
  if (repeats === 1) return one;
  const out = new Float32Array(n * repeats);
  for (let r = 0; r < repeats; r++) out.set(one, r * n);
  return out;
}

/** a soft whump: low rumbling noise that darkens as it fades, over a faint low tone that sinks a little */
export function thud(seconds = 0.6, volume = 0.6, seed = 1): number[] {
  const n = Math.trunc(RATE * seconds);
  const out: number[] = new Array(n);
  let phase = 0, lp1 = 0, lp2 = 0, state = seed * 7919 + 17;
  for (let i = 0; i < n; i++) {
    const t = i / n;
    state = Number((BigInt(state) * 1103515245n + 12345n) & 0x7fffffffn);
    const white = (state >> 8) / 0x7fffff - 1.0;
    const k = 0.22 - 0.15 * t;                           // the filter closes: the noise gets duller
    lp1 += k * (white - lp1);
    lp2 += k * (lp1 - lp2);
    const f = 130.0 - 22.0 * t;
    phase = (phase + f / RATE) % 1;
    const tone = (4 * Math.abs(phase - 0.5) - 1) * 0.35;
    const attack = Math.min(1, i / (RATE * 0.012));
    out[i] = (lp2 * 3.2 + tone) * attack * Math.exp(-4.2 * t);
  }
  let peak = 0;
  for (const x of out) peak = Math.max(peak, Math.abs(x));
  peak = peak || 1;
  return out.map((x) => x / peak * volume);
}

/** four short soft whumps, each a little quieter (FLOAT 740 plays its tune four times) */
export function collisionTune(runs = 4): Float32Array {
  const all: number[] = [];
  for (let k = 0; k < runs; k++) for (const v of thud(0.125, 0.6 * (1 - 0.15 * k), k + 1)) all.push(v);
  return Float32Array.from(all);
}

/** a tune file the player extracted from a disk they own, played as written (see the header) */
export function tuneFromBin(bytes: Uint8Array): Float32Array | null {
  const F1 = 76.8, UNIT = 0.00576;
  const all: number[] = [];
  for (let i = 4; i + 1 < bytes.length && bytes[i] < 128; i += 2) {
    const p = bytes[i], d = bytes[i + 1];
    const seconds = d * UNIT;
    if (p === 0) { for (let k = 0, z = Math.trunc(RATE * seconds); k < z; k++) all.push(0); }
    else for (const v of soft(F1 * 2 ** ((p - 1) / 12), seconds, 0.3, 1.2)) all.push(v);
  }
  return all.length ? Float32Array.from(all) : null;
}

export const durationOf = (samples: ArrayLike<number>): number => samples.length / RATE;

// ----------------------------------------------------------------------------------------- playback
export interface AudioOut {
  play(samples: Float32Array, rate: number, loop: boolean): void;
  stop(): void;
  /** called from a key press, so the browser lets the audio start */
  unlock?(): void;
  close?(): void;
}

/** records what would have played; for tests and for a browser without audio */
export class NullOut implements AudioOut {
  played: { samples: Float32Array; loop: boolean }[] = [];
  stopped = 0;
  play(samples: Float32Array, _rate: number, loop: boolean): void { this.played.push({ samples, loop }); }
  stop(): void { this.stopped += 1; }
}

/** the browser's WebAudio; the AudioContext is made on first use (a key press) and every failure is silent */
export class WebAudioOut implements AudioOut {
  private ctx: any = null;
  private src: any = null;
  private context(): any {
    if (!this.ctx) {
      const G = globalThis as any;
      const Ctor = G.AudioContext ?? G.webkitAudioContext;
      if (!Ctor) return null;
      try { this.ctx = new Ctor(); } catch { return null; }
    }
    if (this.ctx.state === "suspended") { try { this.ctx.resume(); } catch { /* silent */ } }
    return this.ctx;
  }
  unlock(): void { this.context(); }
  play(samples: Float32Array, rate: number, loop: boolean): void {
    this.stop();
    const ctx = this.context();
    if (!ctx) return;
    try {
      const buf = ctx.createBuffer(1, samples.length, rate);
      buf.copyToChannel(samples, 0);
      const src = ctx.createBufferSource();
      src.buffer = buf; src.loop = loop;
      src.connect(ctx.destination);
      src.start();
      this.src = src;
    } catch { /* silent */ }
  }
  stop(): void {
    const s = this.src; this.src = null;
    if (s) { try { s.stop(); } catch { /* already ended */ } try { s.disconnect(); } catch { /* ignore */ } }
  }
  close(): void { this.stop(); if (this.ctx) { try { this.ctx.close(); } catch { /* ignore */ } this.ctx = null; } }
}

/** plays the tunes when `enabled()` says so. All failures are silent. */
export class Sound {
  enabled: () => boolean;
  toggle: () => void = () => {};
  tune = "ms0";                                          // the tune file in memory (MS0 until a landmark loads its own)
  private bins = new Map<string, Uint8Array>();
  private cache = new Map<string, Float32Array | null>();
  private collisionSamples: Float32Array | null = null;

  constructor(enabled: () => boolean = () => true, public out: AudioOut = new WebAudioOut()) { this.enabled = enabled; }

  /** the player's own tune files, by path or name ("MS5.BIN", "tunes/TS"); names that are not tunes are ignored */
  loadTuneFiles(files: Map<string, Uint8Array>): number {
    let n = 0;
    for (const [path, bytes] of files) {
      const base = path.replace(/\\/g, "/").split("/").pop() as string;
      const m = /^(ms\d+|ts)(\.bin)?$/i.exec(base);
      if (m && tuneNames().includes(m[1].toLowerCase())) { this.bins.set(m[1].toLowerCase(), bytes); this.cache.delete(m[1].toLowerCase()); n += 1; }
    }
    return n;
  }

  /** load another tune file: "ms5", "ts" ... (an unknown name is ignored) */
  select(name: string): void { if (name in SETTINGS) this.tune = name; }

  /** the samples of the tune in memory: the player's own file when there is one, else the made-up one */
  samplesFor(name: string): Float32Array {
    if (!this.cache.has(name)) {
      const bin = this.bins.get(name);
      this.cache.set(name, (bin && tuneFromBin(bin)) || waitTune(name));
    }
    return this.cache.get(name) as Float32Array;
  }

  /** the tune that plays at "Press SPACE BAR to continue", until stopped */
  waiting(): void { if (this.enabled()) this.out.play(this.samplesFor(this.tune), RATE, true); }
  stop(): void { this.out.stop(); }
  unlock(): void { this.out.unlock?.(); }

  /** start the collision sound; returns how long it lasts (seconds), 0 when silent */
  collision(): number {
    if (!this.enabled()) return 0;
    if (!this.collisionSamples) this.collisionSamples = collisionTune();
    this.out.play(this.collisionSamples, RATE, false);
    return durationOf(this.collisionSamples);
  }
  close(): void { this.out.stop(); this.out.close?.(); }
}
