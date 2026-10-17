/** The two files the original keeps on disk (the top ten and the tombstones), kept in the browser's localStorage. */
import type { Storage } from "../files.js";

const PREFIX = "oregon-trail:";

function toBase64(b: Uint8Array): string { let s = ""; for (const x of b) s += String.fromCharCode(x); return (globalThis as any).btoa(s); }
function fromBase64(t: string): Uint8Array { const s: string = (globalThis as any).atob(t); const out = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i); return out; }

export class LocalStorageStorage implements Storage {
  private mem = new Map<string, Uint8Array>();          // used when the browser refuses storage
  private ls(): any { try { return (globalThis as any).localStorage ?? null; } catch { return null; } }
  read(name: string): Uint8Array | null {
    const ls = this.ls();
    try { const t = ls?.getItem(PREFIX + name); if (t) return fromBase64(t); } catch { /* fall through to memory */ }
    const m = this.mem.get(name);
    return m ? m.slice() : null;
  }
  write(name: string, data: Uint8Array): void {
    this.mem.set(name, data.slice());
    try { this.ls()?.setItem(PREFIX + name, toBase64(data)); } catch { /* the copy in memory still serves this session */ }
  }
  /** forget everything this game has saved */
  clear(): void {
    this.mem.clear();
    const ls = this.ls();
    try { for (const k of Object.keys(ls ?? {})) if (k.startsWith(PREFIX)) ls.removeItem(k); } catch { /* ignore */ }
  }
}
