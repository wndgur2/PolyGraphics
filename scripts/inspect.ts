/**
 * Design-loop inspector: renders chosen assets big (to judge form) and at true
 * game scale on the real ground color (to judge whether it survives the size it
 * will actually be seen at), plus a silhouette column — if two enemies are
 * indistinguishable in black, color is doing the work again.
 *
 *   npx tsx scripts/inspect.ts ss.enemy.imp ss.enemy.bat --anim
 */
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { AssetSchema, type Asset } from "../src/schema.js";
import { renderSVG, type Registry } from "../src/render.js";
import type { Tokens } from "../src/tokens.js";

const root = new URL("..", import.meta.url);
const tokens = JSON.parse(readFileSync(new URL("tokens/default.json", root), "utf8")) as Tokens;
const assets = new Map<string, Asset>();
for (const f of readdirSync(new URL("assets/", root)).filter((f) => f.endsWith(".json"))) {
  const parsed = AssetSchema.safeParse(JSON.parse(readFileSync(new URL(`assets/${f}`, root), "utf8")));
  if (parsed.success) assets.set(parsed.data.id, parsed.data);
}
const reg: Registry = { assets, tokens };

const args = process.argv.slice(2);
const withAnim = args.includes("--anim");
const ids = args.filter((a) => !a.startsWith("--"));
const targets = ids.length ? ids : [...assets.keys()].filter((id) => id.startsWith("ss."));

const GROUND = tokens.colors.soil ?? "#131019";

function svgOf(a: Asset, scale: number, variant?: string, anim?: string, uid?: string): string {
  const { svg, issues } = renderSVG(a, reg, { variant, animation: anim, displayScale: scale, uid });
  for (const i of issues) console.log(`${i.level === "error" ? "✖" : "▲"} ${i.where}: ${i.msg}`);
  return svg;
}

let uid = 0;
const rows = targets
  .map((id) => {
    const a = assets.get(id);
    if (!a) return `<p style="color:#ff6b6b">unknown asset ${id}</p>`;
    const anim = withAnim ? Object.keys(a.animations ?? {})[0] : undefined;
    const variants = [undefined, ...Object.keys(a.variants ?? {})];
    const big = variants
      .map((v) => `<figure><div class=stage>${svgOf(a, 6, v, anim, `i${uid++}`)}</div><figcaption>${v ?? "base"}</figcaption></figure>`)
      .join("");
    const gameScale = `<figure><div class="stage tiny">${svgOf(a, 1.35, undefined, anim, `i${uid++}`)}</div><figcaption>game 1.35×</figcaption></figure>`;
    const silo = `<figure><div class="stage silo">${svgOf(a, 3, undefined, undefined, `i${uid++}`)}</div><figcaption>silhouette</figcaption></figure>`;
    return `<section>
  <h2>${a.name} <code>${a.id}</code>${anim ? ` <em>▸ ${anim}</em>` : ""}</h2>
  <p>${a.description}</p>
  <div class=row>${big}${gameScale}${silo}</div>
</section>`;
  })
  .join("\n");

writeFileSync(
  new URL("out/inspect.html", root),
  `<!doctype html><meta charset=utf-8><title>inspect</title><style>
  body{background:#0b0d12;color:#c7d2e0;font:13px/1.5 system-ui;padding:24px 32px 60px;margin:0}
  section{border-top:1px solid #232838;padding:18px 0}
  h2{font-size:15px;margin:0 0 2px;display:flex;gap:10px;align-items:baseline}
  code{color:#8fd0ff;font:11px ui-monospace,monospace} em{color:#5b6575;font-style:normal;font-size:11px}
  p{color:#7c8798;font-size:12px;max-width:70ch;margin:0 0 12px}
  .row{display:flex;gap:16px;align-items:flex-end;flex-wrap:wrap}
  figure{margin:0;display:flex;flex-direction:column;align-items:center;gap:5px}
  .stage{background:${GROUND};padding:10px;border-radius:8px;display:flex;align-items:center;justify-content:center}
  .stage.tiny{padding:6px} .stage.silo svg{filter:brightness(0) invert(1) contrast(2)}
  .stage.silo{background:#000}
  figcaption{font-size:10px;color:#5b6575;font-family:ui-monospace,monospace}
</style>
<h1 style="font-size:16px;color:#e6ecf5;margin:0 0 6px">inspect — ${targets.length} assets</h1>
${rows}`,
);
console.log(`✓ out/inspect.html — ${targets.length} assets`);
