/**
 * Pixels without a browser: an RGBA image in a typed array, a PNG decoder that needs only an inflate
 * function (the browser's DecompressionStream, or Node's zlib), and the paste operations the canvas needs.
 * Keeping this free of the DOM lets the same drawing code run in Node, where its frames are compared
 * with the Python rebuild's pixel for pixel.
 */
export interface Img { w: number; h: number; data: Uint8ClampedArray }   // RGBA, 4 bytes a pixel

export function newImage(w: number, h: number, rgb: [number, number, number] = [0, 0, 0]): Img {
  const data = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < w * h; i++) { data[i * 4] = rgb[0]; data[i * 4 + 1] = rgb[1]; data[i * 4 + 2] = rgb[2]; data[i * 4 + 3] = 255; }
  return { w, h, data };
}

export type Inflate = (compressed: Uint8Array) => Promise<Uint8Array>;

/** the browser's inflate (zlib streams are what a PNG holds) */
export const browserInflate: Inflate = async (bytes) => {
  const ds = new (globalThis as any).DecompressionStream("deflate");
  const w = ds.writable.getWriter();
  w.write(bytes); w.close();
  return new Uint8Array(await new (globalThis as any).Response(ds.readable).arrayBuffer());
};

/** an 8-bit, non-interlaced PNG of colour type 0, 2, 3, 4 or 6 */
export async function decodePng(bytes: Uint8Array, inflate: Inflate): Promise<Img> {
  const sig = [137, 80, 78, 71, 13, 10, 26, 10];
  for (let i = 0; i < 8; i++) if (bytes[i] !== sig[i]) throw new Error("not a PNG file");
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let pos = 8, w = 0, h = 0, depth = 0, ctype = 0, interlace = 0;
  const idat: Uint8Array[] = [];
  let palette: Uint8Array | null = null, trns: Uint8Array | null = null;
  while (pos + 8 <= bytes.length) {
    const len = dv.getUint32(pos);
    const type = String.fromCharCode(bytes[pos + 4], bytes[pos + 5], bytes[pos + 6], bytes[pos + 7]);
    const body = bytes.subarray(pos + 8, pos + 8 + len);
    if (type === "IHDR") { w = dv.getUint32(pos + 8); h = dv.getUint32(pos + 12); depth = bytes[pos + 16]; ctype = bytes[pos + 17]; interlace = bytes[pos + 20]; }
    else if (type === "PLTE") palette = body;
    else if (type === "tRNS") trns = body;
    else if (type === "IDAT") idat.push(body);
    else if (type === "IEND") break;
    pos += 12 + len;
  }
  if (depth !== 8 || interlace !== 0) throw new Error(`unsupported PNG (depth ${depth}, interlace ${interlace})`);
  const channels = ({ 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 } as Record<number, number>)[ctype];
  if (!channels) throw new Error(`unsupported PNG colour type ${ctype}`);
  let total = 0; for (const c of idat) total += c.length;
  const joined = new Uint8Array(total); let o = 0; for (const c of idat) { joined.set(c, o); o += c.length; }
  const raw = await inflate(joined);
  const stride = w * channels;
  const out = new Uint8ClampedArray(w * h * 4);
  const prev = new Uint8Array(stride), cur = new Uint8Array(stride);
  let p = 0;
  for (let y = 0; y < h; y++) {
    const f = raw[p++];
    for (let i = 0; i < stride; i++) {
      const x = raw[p++];
      const a = i >= channels ? cur[i - channels] : 0, b = prev[i], c = i >= channels ? prev[i - channels] : 0;
      let v: number;
      switch (f) {
        case 0: v = x; break;
        case 1: v = x + a; break;
        case 2: v = x + b; break;
        case 3: v = x + ((a + b) >> 1); break;
        default: { const pa = Math.abs(b - c), pb = Math.abs(a - c), pc = Math.abs(a + b - 2 * c); v = x + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c); }
      }
      cur[i] = v & 255;
    }
    for (let x = 0; x < w; x++) {
      const q = (y * w + x) * 4;
      if (ctype === 6) { out[q] = cur[x * 4]; out[q + 1] = cur[x * 4 + 1]; out[q + 2] = cur[x * 4 + 2]; out[q + 3] = cur[x * 4 + 3]; }
      else if (ctype === 2) { out[q] = cur[x * 3]; out[q + 1] = cur[x * 3 + 1]; out[q + 2] = cur[x * 3 + 2]; out[q + 3] = 255; }
      else if (ctype === 0) { out[q] = out[q + 1] = out[q + 2] = cur[x]; out[q + 3] = 255; }
      else if (ctype === 4) { out[q] = out[q + 1] = out[q + 2] = cur[x * 2]; out[q + 3] = cur[x * 2 + 1]; }
      else { const k = cur[x]; out[q] = palette![k * 3]; out[q + 1] = palette![k * 3 + 1]; out[q + 2] = palette![k * 3 + 2]; out[q + 3] = trns && k < trns.length ? trns[k] : 255; }
    }
    prev.set(cur);
  }
  return { w, h, data: out };
}

/** PIL's exact 8-bit blend: (a*src + (255-a)*dst) / 255, rounded */
const div255 = (v: number): number => { const t = v + 128; return ((t >> 8) + t) >> 8; };

/** paste *src* at (x, y); with `masked` its own alpha is the mask (PIL's `paste(im, pos, im)`), otherwise alpha is dropped */
export function paste(dst: Img, src: Img, x: number, y: number, masked: boolean): void {
  for (let r = 0; r < src.h; r++) {
    const Y = y + r;
    if (Y < 0 || Y >= dst.h) continue;
    for (let c = 0; c < src.w; c++) {
      const X = x + c;
      if (X < 0 || X >= dst.w) continue;
      const s = (r * src.w + c) * 4, d = (Y * dst.w + X) * 4;
      if (!masked) { dst.data[d] = src.data[s]; dst.data[d + 1] = src.data[s + 1]; dst.data[d + 2] = src.data[s + 2]; dst.data[d + 3] = 255; continue; }
      const a = src.data[s + 3];
      if (a === 255) { dst.data[d] = src.data[s]; dst.data[d + 1] = src.data[s + 1]; dst.data[d + 2] = src.data[s + 2]; }
      else if (a > 0) for (let k = 0; k < 3; k++) dst.data[d + k] = div255(a * src.data[s + k] + (255 - a) * dst.data[d + k]);
    }
  }
}

export function fillRect(dst: Img, x1: number, y1: number, x2: number, y2: number, rgb: readonly number[]): void {
  for (let y = Math.max(0, y1); y < Math.min(dst.h, y2); y++)
    for (let x = Math.max(0, x1); x < Math.min(dst.w, x2); x++) {
      const d = (y * dst.w + x) * 4; dst.data[d] = rgb[0]; dst.data[d + 1] = rgb[1]; dst.data[d + 2] = rgb[2]; dst.data[d + 3] = 255;
    }
}

export function crop(src: Img, x1: number, y1: number, x2: number, y2: number): Img {
  const w = Math.max(0, x2 - x1), h = Math.max(0, y2 - y1);
  const out = { w, h, data: new Uint8ClampedArray(w * h * 4) };
  for (let r = 0; r < h; r++) for (let c = 0; c < w; c++) {
    const X = x1 + c, Y = y1 + r;
    const d = (r * w + c) * 4;
    if (X >= 0 && X < src.w && Y >= 0 && Y < src.h) { const s = (Y * src.w + X) * 4; for (let k = 0; k < 4; k++) out.data[d + k] = src.data[s + k]; }
    else out.data[d + 3] = 255;
  }
  return out;
}

export function copyImage(a: Img): Img { return { w: a.w, h: a.h, data: a.data.slice() }; }
