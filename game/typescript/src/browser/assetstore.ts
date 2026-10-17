/**
 * The player's own files (pictures, tunes, the dialogue document) are chosen from their computer and kept
 * only in this browser, in IndexedDB, so the folder need not be picked again on the next visit. Nothing is
 * uploaded and nothing from the folder is part of this program.
 */
const G = globalThis as any;
const DB = "oregon-trail-assets", STORE = "files", KEY = "all";

function open(): Promise<any> {
  return new Promise((resolve, reject) => {
    const req = G.indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function saveFiles(files: Map<string, Uint8Array>): Promise<boolean> {
  try {
    const db = await open();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put([...files], KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    return true;
  } catch { return false; }
}

export async function loadFiles(): Promise<Map<string, Uint8Array> | null> {
  try {
    const db = await open();
    const rows: [string, Uint8Array][] | undefined = await new Promise((resolve, reject) => {
      const req = db.transaction(STORE).objectStore(STORE).get(KEY);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return rows && rows.length ? new Map(rows) : null;
  } catch { return null; }
}

export async function forgetFiles(): Promise<void> {
  try {
    const db = await open();
    await new Promise<void>((resolve) => { const tx = db.transaction(STORE, "readwrite"); tx.objectStore(STORE).delete(KEY); tx.oncomplete = () => resolve(); tx.onerror = () => resolve(); });
  } catch { /* nothing to forget */ }
}

/** read the chosen File objects into a path -> bytes map; a folder's files carry their relative path */
export async function readChosen(list: any[]): Promise<Map<string, Uint8Array>> {
  const out = new Map<string, Uint8Array>();
  for (const f of list) {
    const path: string = f.webkitRelativePath || f.name;
    out.set(path, new Uint8Array(await f.arrayBuffer()));
  }
  return out;
}
