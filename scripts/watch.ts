/**
 * Rebuilds on save, so the loop is edit → look.
 *
 *   npm run watch      (pair it with the gallery open; the page reloads itself)
 *
 * The page polls its own timestamp, so nothing has to talk to the browser —
 * this only has to make the file newer than it was.
 */
import { spawn } from "node:child_process";
import { watch } from "node:fs";

const ROOT = new URL("..", import.meta.url).pathname;
const DIRS = ["assets", "sounds", "tokens", "themes"];
/** Long enough to swallow an editor's write-truncate-write, short enough to feel instant. */
const SETTLE_MS = 120;

let timer: NodeJS.Timeout | undefined;
let running = false;
let queued = false;

function build(): void {
  if (running) {
    queued = true;
    return;
  }
  running = true;
  const t = Date.now();
  const child = spawn("npx", ["tsx", `${ROOT}src/cli.ts`, "check"], { cwd: ROOT, stdio: "inherit" });
  child.on("exit", (code) => {
    running = false;
    console.log(code === 0 ? `  ↻ ${Date.now() - t}ms — the open gallery reloads itself\n` : `  ✖ build failed (${code})\n`);
    if (queued) {
      queued = false;
      build();
    }
  });
}

for (const d of DIRS) {
  try {
    watch(`${ROOT}${d}`, { recursive: true }, (_e, file) => {
      if (file && !file.endsWith(".json")) return;
      clearTimeout(timer);
      timer = setTimeout(build, SETTLE_MS);
    });
  } catch {
    console.warn(`(not watching ${d}/ — missing)`);
  }
}

console.log(`watching ${DIRS.join(", ")} — ctrl-c to stop`);
build();
