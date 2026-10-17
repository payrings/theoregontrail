// Just enough of Node for the command line, so the project builds with TypeScript alone.
// (With @types/node installed this file is redundant and can be deleted.)
declare const process: { argv: string[]; env: Record<string, string | undefined>; exit(code?: number): never; stdout: { write(s: string): void }; stderr: { write(s: string): void } };
declare const console: { log(...a: unknown[]): void; error(...a: unknown[]): void };
declare module "node:crypto" {
  export function createHash(alg: string): { update(s: string): { digest(enc: string): string } };
}
declare module "node:fs" {
  export function writeFileSync(path: string, data: string): void;
  export function readFileSync(path: string, enc: string): string;
  export function existsSync(path: string): boolean;
}
