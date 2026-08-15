/** Builds out/gallery.html — every asset, variant, animation and theme on one page. */
import type { Asset } from "./schema.js";
import { renderSVG, type Issue, type Registry } from "./render.js";
import { applyTheme, resolveColor, type Theme, type Tokens } from "./tokens.js";

const CATEGORY_ORDER = [
  "char", "enemy", "boss", "weapon", "icon", "pickup", "fx", "tile", "env", "lib",
  "ss-char", "ss-enemy", "ss-pickup", "ss-proj", "ss-terrain", "ss-icon", "ss-env", "ss-lib",
];

function displayScale(asset: Asset, variantScale = 1): number {
  const m = Math.max(asset.size[0], asset.size[1]) * variantScale;
  return m <= 32 ? 3 : m <= 48 ? 2.5 : m <= 80 ? 1.75 : 1.25;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

let uidCounter = 0;
function cell(asset: Asset, reg: Registry, issues: Issue[], caption: string, opts: { variant?: string; animation?: string } = {}): string {
  const vs = opts.variant ? (asset.variants?.[opts.variant]?.scale ?? 1) : 1;
  const r = renderSVG(asset, reg, { ...opts, displayScale: displayScale(asset, vs), uid: `u${uidCounter++}` });
  issues.push(...r.issues);
  return `<figure class="cell"><div class="stage">${r.svg}</div><figcaption>${esc(caption)}</figcaption></figure>`;
}

function assetCard(asset: Asset, reg: Registry, issues: Issue[]): string {
  const firstAnim = Object.keys(asset.animations ?? {})[0];
  const cells: string[] = [cell(asset, reg, issues, firstAnim ? `base · ▸ ${firstAnim}` : "base", { animation: firstAnim })];
  for (const v of Object.keys(asset.variants ?? {}))
    cells.push(cell(asset, reg, issues, `#${v}`, { variant: v, animation: firstAnim }));
  const anims = Object.keys(asset.animations ?? {});
  const meta: string[] = [`${asset.size[0]}×${asset.size[1]}`];
  if (anims.length) meta.push(`anim: ${anims.join(", ")}`);
  return `<article class="card">
  <header><h3>${esc(asset.name)}</h3><code>${esc(asset.id)}</code></header>
  <p class="desc">${esc(asset.description)}</p>
  <div class="tags">${asset.tags.map((t) => `<span>${esc(t)}</span>`).join("")}<span class="dim">${meta.join(" · ")}</span></div>
  <div class="row">${cells.join("")}</div>
</article>`;
}

function swatches(tokens: Tokens): string {
  const rows = Object.entries(tokens.colors)
    .map(([name, hex]) => {
      const light = resolveColor(`$${name}.light`, tokens);
      const dark = resolveColor(`$${name}.dark`, tokens);
      return `<div class="swatch">
  <div class="chips"><i style="background:${light.ok ? light.value : "#000"}"></i><i class="main" style="background:${hex}"></i><i style="background:${dark.ok ? dark.value : "#000"}"></i></div>
  <code>$${esc(name)}</code><span class="dim">${esc(hex)}</span>
</div>`;
    })
    .join("");
  const table = (title: string, obj: Record<string, number>) =>
    `<div class="tok"><h4>${title}</h4>${Object.entries(obj)
      .map(([k, v]) => `<div><code>${esc(k)}</code><span>${v}</span></div>`)
      .join("")}</div>`;
  return `<div class="swatches">${rows}</div>
<div class="tokrow">${table("strokes", tokens.strokes)}${table("alpha", tokens.alpha)}${table("layers", tokens.layers)}<div class="tok"><h4>grid</h4><div><code>unit</code><span>${tokens.grid}px</span></div></div></div>`;
}

export function buildGallery(reg: Registry, themes: Theme[], issues: Issue[]): string {
  const byCat = new Map<string, Asset[]>();
  for (const a of reg.assets.values()) {
    const cat = a.tags[0];
    byCat.set(cat, [...(byCat.get(cat) ?? []), a]);
  }
  const cats = [...byCat.keys()].sort(
    (a, b) => (CATEGORY_ORDER.indexOf(a) + 99) % 99 - (CATEGORY_ORDER.indexOf(b) + 99) % 99,
  );
  const sections = cats
    .map(
      (cat) =>
        `<h2>${esc(cat)}</h2>\n<div class="grid">${byCat
          .get(cat)!
          .map((a) => assetCard(a, reg, issues))
          .join("\n")}</div>`,
    )
    .join("\n");

  const themeSections = themes
    .map((theme) => {
      const treg: Registry = { assets: reg.assets, tokens: applyTheme(reg.tokens, theme) };
      const cellsHtml = [...reg.assets.values()]
        .filter((a) => a.tags[0] !== "lib")
        .map((a) => cell(a, treg, issues, a.name))
        .join("");
      return `<h3>theme: ${esc(theme.name)}</h3><p class="desc">${esc(theme.description ?? "")}</p><div class="strip">${cellsHtml}</div>`;
    })
    .join("\n");

  return `<!doctype html>
<meta charset="utf-8">
<title>PolyGraphics gallery</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; }
  body { background:#0d0f14; color:#e6ecf5; font: 14px/1.5 system-ui, sans-serif; padding: 32px 40px 80px; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  h2 { margin: 36px 0 12px; font-size: 16px; text-transform: uppercase; letter-spacing: .12em; color:#8fd0ff; }
  h3 { font-size: 14px; }
  h4 { font-size: 12px; color:#9aa4b2; margin-bottom: 6px; }
  .sub { color:#9aa4b2; margin-bottom: 24px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
  .card { background:#151824; border: 1px solid #232838; border-radius: 10px; padding: 14px; }
  .card header { display:flex; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 4px; }
  .card h3 { font-size: 14px; }
  code { color:#8fd0ff; font: 12px ui-monospace, monospace; }
  .desc { color:#9aa4b2; font-size: 12px; margin-bottom: 8px; }
  .tags { display:flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
  .tags span { background:#1e2432; border-radius: 99px; padding: 1px 8px; font-size: 11px; color:#c7d2e0; }
  .tags .dim { background: none; color:#5b6575; }
  .row, .strip { display:flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
  .strip { background:#151824; border:1px solid #232838; border-radius: 10px; padding: 14px; margin: 8px 0 20px; }
  .cell { display:flex; flex-direction: column; align-items: center; gap: 4px; }
  .stage { background: repeating-conic-gradient(#181c28 0% 25%, #141824 0% 50%) 0 0/16px 16px; border-radius: 6px; padding: 8px; display:flex; align-items:center; justify-content:center; }
  figcaption { font-size: 11px; color:#5b6575; }
  .swatches { display:grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin-bottom: 16px; }
  .swatch { background:#151824; border:1px solid #232838; border-radius: 8px; padding: 10px; }
  .chips { display:flex; height: 34px; border-radius: 6px; overflow:hidden; margin-bottom: 6px; }
  .chips i { flex:1; } .chips i.main { flex: 2.2; }
  .swatch .dim, .tok span { color:#5b6575; font-size: 11px; }
  .swatch code { display:block; }
  .tokrow { display:flex; gap: 12px; flex-wrap: wrap; }
  .tok { background:#151824; border:1px solid #232838; border-radius: 8px; padding: 10px 14px; min-width: 130px; }
  .tok > div { display:flex; justify-content: space-between; gap: 16px; }
</style>
<h1>PolyGraphics</h1>
<p class="sub">declarative assets · design tokens · deterministic render — ${reg.assets.size} assets</p>
<h2>tokens</h2>
${swatches(reg.tokens)}
${sections}
<h2>themes</h2>
${themeSections}
`;
}
