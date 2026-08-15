/**
 * Before/after sheet. `out/before/` holds the PNG baselines captured from the
 * faithful transcription of BootScene.ts; `out/png/` holds the current renders.
 * Because rendering is deterministic, this diff is the honest record of what the
 * redesign changed.
 *
 *   npx tsx scripts/compare.ts
 */
import { readdirSync, existsSync, readFileSync, writeFileSync } from "node:fs";

const root = new URL("..", import.meta.url);
const beforeDir = new URL("out/before/", root);
const afterDir = new URL("out/png/", root);

const b64 = (dir: URL, f: string) => readFileSync(new URL(f, dir)).toString("base64");

const names = readdirSync(beforeDir)
  .filter((f) => f.startsWith("ss-") && f.endsWith(".png") && !f.includes("--"))
  .filter((f) => existsSync(new URL(f, afterDir)))
  .sort();

const rows = names
  .map((f) => {
    const id = f.replace(".png", "");
    return `<div class=pair>
  <div class=col><img src="data:image/png;base64,${b64(beforeDir, f)}"><span>before</span></div>
  <div class=col><img src="data:image/png;base64,${b64(afterDir, f)}"><span>after</span></div>
  <code>${id}</code>
</div>`;
  })
  .join("\n");

writeFileSync(
  new URL("out/compare.html", root),
  `<!doctype html><meta charset=utf-8><title>before / after</title><style>
  body{background:#0b0d12;color:#c7d2e0;font:13px system-ui;padding:22px 26px 60px;margin:0}
  h1{font-size:17px;color:#e6ecf5;margin:0 0 2px}
  .sub{color:#7c8798;font-size:12px;margin:0 0 20px;max-width:74ch;line-height:1.55}
  main{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
  .pair{background:#141824;border:1px solid #232838;border-radius:10px;padding:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:flex-end;justify-content:center}
  .col{display:flex;flex-direction:column;align-items:center;gap:4px}
  .col img{background:#131019;border-radius:6px;padding:6px;max-width:96px;height:auto;image-rendering:auto}
  .col span{font:10px ui-monospace,monospace;color:#5b6575}
  code{width:100%;text-align:center;color:#8fd0ff;font:11px ui-monospace,monospace}
</style>
<h1>Shape Survivors — faithful port vs. redesign</h1>
<p class=sub>Left: the roster transcribed 1:1 from <code>BootScene.ts</code>. Right: the same gameplay slots re-authored around the premise that the protagonist has lost their pheromone transmitter and is being hunted for the silence. Same ids, same body radii, same variant slots — only the documents changed.</p>
<main>${rows}</main>`,
);
console.log(`✓ out/compare.html — ${names.length} pairs`);
