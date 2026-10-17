/**
 * Time for the real-time scenes (hunt, raft, collision sound). The default clock is the backend's: a
 * browser backend sleeps with setTimeout and reads the performance clock; a scripted backend may give
 * `now()` and `sleep()` of its own (a fake clock that sleep advances), so the hunt and the raft play
 * out deterministically and at once in a test. A text UI with no backend never waits.
 */
export interface Clock { now(): number; sleep(seconds: number): Promise<void> }

const perf = (): number => (globalThis as any).performance.now() / 1000;

export function clockOf(ui: any): Clock {
  const b = ui?.backend;
  return {
    now: () => (b && typeof b.now === "function" ? b.now() : perf()),
    sleep: (s: number) => (b && typeof b.sleep === "function" ? b.sleep(s) : ui && typeof ui.sleep === "function" ? Promise.resolve(ui.sleep(s)) : Promise.resolve()),
  };
}
