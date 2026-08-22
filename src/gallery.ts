/**
 * Builds out/gallery.html — a workbench, not a contact sheet.
 *
 * Three things it has to do. Browse: tabs per category and a search that
 * reaches across them, because one 19,000px scroll was not a way to find
 * anything. Inspect: a detail view per asset with its parts, variants,
 * animations and the file it lives in, so a change can be discussed by part id
 * rather than by pointing. Stay open: the page watches its own timestamp and
 * reloads itself, keeping the tab, the search and the open asset, so the loop
 * is edit → `npm run check` → look, without ever touching the browser.
 *
 * The detail view moves the card's existing SVG into a bigger stage rather
 * than rendering a second copy — same file size, and no duplicate element ids
 * for the animation CSS to collide on.
 */
import type { Asset, Part } from "./schema.js";
import { renderSVG, type Issue, type Registry } from "./render.js";
import { applyTheme, resolveColor, type Theme, type Tokens } from "./tokens.js";

const CATEGORY_ORDER = [
  "ss-char", "ss-enemy", "ss-proj", "ss-fx", "ss-pickup", "ss-terrain", "ss-env", "ss-icon", "ss-lib",
  "char", "enemy", "boss", "weapon", "icon", "pickup", "fx", "tile", "env", "lib",
];

function displayScale(asset: Asset, variantScale = 1): number {
  const m = Math.max(asset.size[0], asset.size[1]) * variantScale;
  return m <= 32 ? 3 : m <= 48 ? 2.5 : m <= 80 ? 1.75 : 1.25;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

const slug = (id: string) => id.replace(/\./g, "-");
const fileOf = (a: Asset) => `assets/${slug(a.id)}.json`;

let uidCounter = 0;
function cell(asset: Asset, reg: Registry, issues: Issue[], caption: string, opts: { variant?: string; animation?: string } = {}): string {
  const vs = opts.variant ? (asset.variants?.[opts.variant]?.scale ?? 1) : 1;
  const r = renderSVG(asset, reg, { ...opts, displayScale: displayScale(asset, vs), uid: `u${uidCounter++}` });
  issues.push(...r.issues);
  return `<figure class="cell"><div class="stage">${r.svg}</div><figcaption>${esc(caption)}</figcaption></figure>`;
}

/** One line per part, in draw order — the vocabulary a change gets described in. */
function partRow(p: Part): string {
  const bits: string[] = [];
  if ("shape" in p) {
    const s = p.shape;
    const dims =
      s.kind === "circle" ? `r ${s.r}`
      : s.kind === "ellipse" ? `${s.rx}×${s.ry}`
      : s.kind === "rect" ? `${s.w}×${s.h}${s.corner ? ` r${s.corner}` : ""}`
      : s.kind === "ngon" ? `${s.sides}-gon r${s.r}`
      : s.kind === "star" ? `${s.points}★ ${s.r}/${s.r2}`
      : s.kind === "poly" ? `${s.points.length} pts`
      : s.kind === "ring" ? `r${s.r} w${s.width}${s.from !== undefined ? ` ${s.from}→${s.to}°` : ""}`
      : `r${s.r} ${s.from}→${s.to}°`;
    bits.push(`${s.kind} ${dims}`);
  } else if ("use" in p) {
    bits.push(`use ${p.use}${p.variant ? `#${p.variant}` : ""}`);
  } else {
    bits.push(`repeat ×${p.repeat.count} ${p.repeat.of.kind}`);
  }
  const paint = "fill" in p && p.fill ? (typeof p.fill === "string" ? p.fill : "gradient") : "";
  const xf: string[] = [];
  if (p.at) xf.push(`at ${p.at[0]},${p.at[1]}`);
  if (p.rot) xf.push(`rot ${p.rot}°`);
  if (p.scale) xf.push(`scale ${Array.isArray(p.scale) ? p.scale.join("×") : p.scale}`);
  if (p.mirrorX) xf.push("mirrorX");
  if (p.opacity !== undefined) xf.push(`opacity ${p.opacity}`);
  const stroke = "stroke" in p && p.stroke ? `stroke ${p.stroke.color} ${p.stroke.width}` : "";
  return `<tr>
  <td><code class="pid">${esc(p.id)}</code></td>
  <td>${esc(bits.join(""))}</td>
  <td>${paint ? `<code class="tok">${esc(paint)}</code>` : ""}${stroke ? ` <span class="dim">${esc(stroke)}</span>` : ""}</td>
  <td class="dim">${esc(xf.join(" · "))}</td>
</tr>`;
}

/** Everything about one asset that a conversation about changing it would need. */
function detailBlock(asset: Asset, reg: Registry): string {
  const variants = Object.entries(asset.variants ?? {});
  const anims = Object.entries(asset.animations ?? {});
  const radius = asset.meta?.radius;

  const facts = ([
    ["id", `<code>${esc(asset.id)}</code>`],
    ["file", `<code>${esc(fileOf(asset))}</code>`, "wide"],
    ["size", `${asset.size[0]}×${asset.size[1]}`],
    ["anchor", (asset.anchor ?? [0.5, 0.5]).join(", ")],
    ["parts", String(asset.parts.length)],
    ...(radius !== undefined ? [["radius", String(radius)] as [string, string]] : []),
    ...(asset.seed !== undefined ? [["seed", String(asset.seed)] as [string, string]] : []),
  ] as [string, string, string?][])
    .map(([k, v, cls]) => `<div${cls ? ` class="${cls}"` : ""}><span class="dim">${k}</span>${v}</div>`)
    .join("");

  const variantHtml = variants.length
    ? `<h4>variants</h4>${variants
        .map(([name, v]) => {
          const changes: string[] = [];
          if (v.scale) changes.push(`scale ${v.scale}`);
          if (v.set) changes.push(...Object.entries(v.set).map(([k, val]) => `${k} = ${JSON.stringify(val)}`));
          if (v.add?.length) changes.push(`+${v.add.length} part${v.add.length > 1 ? "s" : ""}: ${v.add.map((p) => p.id).join(", ")}`);
          if (v.remove?.length) changes.push(`−${v.remove.join(", ")}`);
          return `<div class="sub-item"><code>#${esc(name)}</code><p>${esc(v.description)}</p><ul>${changes
            .map((c) => `<li><code>${esc(c)}</code></li>`)
            .join("")}</ul></div>`;
        })
        .join("")}`
    : "";

  const animHtml = anims.length
    ? `<h4>animations</h4>${anims
        .map(([name, a]) => {
          const tracks = a.tracks.map((t) => `${t.part}.${t.prop}`).join(", ");
          return `<div class="sub-item"><code>▸ ${esc(name)}</code> <span class="dim">${a.duration}s · ${a.tracks.length} tracks</span>
${a.description ? `<p>${esc(a.description)}</p>` : ""}<ul><li><code>${esc(tracks)}</code></li></ul></div>`;
        })
        .join("")}`
    : "";

  // What you paste into a chat to ask for a change. Keeps ids exact, so a
  // reply can name a part instead of describing where it is on screen.
  const brief = [
    `${asset.id} — ${asset.name} (${fileOf(asset)})`,
    asset.description,
    `size ${asset.size[0]}×${asset.size[1]}${radius !== undefined ? `, radius ${radius}` : ""}`,
    `parts: ${asset.parts.map((p) => p.id).join(", ")}`,
    ...(variants.length ? [`variants: ${variants.map(([n]) => n).join(", ")}`] : []),
    ...(anims.length ? [`animations: ${anims.map(([n]) => n).join(", ")}`] : []),
  ].join("\n");

  return `<section class="detail" id="d-${slug(asset.id)}" hidden>
  <div class="detail-head">
    <button class="back" data-back>← ${esc(asset.tags[0])}</button>
    <h2>${esc(asset.name)}</h2>
    <code class="big-id">${esc(asset.id)}</code>
    <div class="spacer"></div>
    <button data-copy="${esc(asset.id)}">copy id</button>
    <button data-copy="${esc(fileOf(asset))}">copy path</button>
    <button data-copy="${esc(brief)}" class="primary">copy brief</button>
  </div>
  <div class="detail-body">
    <div class="viewer">
      <div class="viewer-stage" data-stage></div>
      <div class="viewer-controls">
        <label>zoom <input type="range" min="1" max="6" step="0.5" value="2" data-zoom></label>
        <label><input type="checkbox" data-silhouette> silhouette</label>
        <span class="bgs">bg
          <button data-bg="checker" class="on"></button>
          <button data-bg="ground" style="background:#1a1420"></button>
          <button data-bg="ink" style="background:#10121a"></button>
          <button data-bg="light" style="background:#e6e1d3"></button>
        </span>
      </div>
      <p class="hint dim">Silhouette is the flat-shape test: if two assets are the same in black, colour is doing work shape should be doing.</p>
    </div>
    <div class="facts">
      <p class="desc big">${esc(asset.description)}</p>
      <div class="factgrid">${facts}</div>
      <div class="tags">${asset.tags.map((t) => `<span>${esc(t)}</span>`).join("")}</div>
      <h4>parts <span class="dim">draw order</span></h4>
      <table class="parts"><tbody>${asset.parts.map(partRow).join("")}</tbody></table>
      ${variantHtml}
      ${animHtml}
    </div>
  </div>
</section>`;
}

function assetCard(asset: Asset, reg: Registry, issues: Issue[]): string {
  const firstAnim = Object.keys(asset.animations ?? {})[0];
  const cells: string[] = [cell(asset, reg, issues, firstAnim ? `base · ▸ ${firstAnim}` : "base", { animation: firstAnim })];
  for (const v of Object.keys(asset.variants ?? {}))
    cells.push(cell(asset, reg, issues, `#${v}`, { variant: v, animation: firstAnim }));
  const anims = Object.keys(asset.animations ?? {});
  const meta: string[] = [`${asset.size[0]}×${asset.size[1]}`];
  if (anims.length) meta.push(`anim: ${anims.join(", ")}`);
  const hay = `${asset.id} ${asset.name} ${asset.description} ${asset.tags.join(" ")} ${asset.parts.map((p) => p.id).join(" ")}`;
  return `<article class="card" id="c-${slug(asset.id)}" data-id="${esc(asset.id)}" data-cat="${esc(asset.tags[0])}" data-hay="${esc(hay.toLowerCase())}">
  <header><h3>${esc(asset.name)}</h3><code>${esc(asset.id)}</code></header>
  <p class="desc">${esc(asset.description)}</p>
  <div class="tags">${asset.tags.map((t) => `<span>${esc(t)}</span>`).join("")}<span class="dim">${meta.join(" · ")}</span></div>
  <div class="row" data-row>${cells.join("")}</div>
  <a class="open" href="#/${esc(asset.id)}">open ↗</a>
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
  for (const a of reg.assets.values()) byCat.set(a.tags[0], [...(byCat.get(a.tags[0]) ?? []), a]);
  const rank = (c: string) => {
    const i = CATEGORY_ORDER.indexOf(c);
    return i < 0 ? 999 : i;
  };
  const cats = [...byCat.keys()].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));

  const panels = cats
    .map(
      (cat) =>
        `<section class="panel" data-panel="${esc(cat)}" hidden><div class="grid">${byCat
          .get(cat)!
          .map((a) => assetCard(a, reg, issues))
          .join("\n")}</div></section>`,
    )
    .join("\n");

  const details = [...reg.assets.values()].map((a) => detailBlock(a, reg)).join("\n");

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

  const tabs = [
    `<button data-tab="tokens">tokens</button>`,
    ...cats.map((c) => `<button data-tab="${esc(c)}">${esc(c)} <i>${byCat.get(c)!.length}</i></button>`),
    `<button data-tab="themes">themes</button>`,
  ].join("");

  return `<!doctype html>
<meta charset="utf-8">
<title>PolyGraphics gallery</title>
<style>
  :root { color-scheme: dark; --bg:#0d0f14; --panel:#151824; --line:#232838; --dim:#5b6575; --mut:#9aa4b2; --acc:#8fd0ff; }
  * { box-sizing: border-box; margin: 0; }
  body { background:var(--bg); color:#e6ecf5; font: 14px/1.5 system-ui, sans-serif; padding-bottom: 80px; }
  h1 { font-size: 18px; } h3 { font-size: 14px; }
  h4 { font-size: 12px; color:var(--mut); margin: 16px 0 6px; text-transform: uppercase; letter-spacing:.08em; }
  code { color:var(--acc); font: 12px ui-monospace, monospace; }
  .dim { color:var(--dim); }
  button { font: inherit; color:inherit; background:#1e2432; border:1px solid var(--line); border-radius:6px; padding:3px 10px; cursor:pointer; }
  button:hover { border-color:#3a4a63; background:#273047; }
  button.primary { background:#1d3652; border-color:#2f5c86; }

  header.top { position: sticky; top:0; z-index:20; background:rgba(13,15,20,.94); backdrop-filter: blur(8px); border-bottom:1px solid var(--line); padding: 10px 20px 0; }
  .titlerow { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
  .titlerow .sub { color:var(--mut); font-size:12px; }
  .spacer { flex:1; }
  #q { background:#11141d; border:1px solid var(--line); border-radius:6px; padding:5px 10px; color:inherit; width:280px; font:inherit; }
  #live { font-size:11px; color:var(--dim); display:flex; align-items:center; gap:5px; }
  #live b { width:7px; height:7px; border-radius:50%; background:#2f9e5f; display:inline-block; }
  nav.tabs { display:flex; gap:4px; overflow-x:auto; padding-bottom:8px; }
  nav.tabs button { white-space:nowrap; border-radius:6px 6px 0 0; border-bottom-color:transparent; }
  nav.tabs button.on { background:#273047; border-color:#3a4a63; color:#fff; }
  nav.tabs i { color:var(--dim); font-style:normal; font-size:11px; }

  main { padding: 18px 20px; }
  .grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(300px,1fr)); gap:14px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; position:relative; }
  .card header { display:flex; justify-content:space-between; align-items:baseline; gap:8px; margin-bottom:4px; }
  .card h3 { font-size:14px; }
  .card .open { position:absolute; top:10px; right:10px; font-size:11px; color:var(--dim); text-decoration:none; opacity:0; }
  .card:hover .open { opacity:1; color:var(--acc); }
  .desc { color:var(--mut); font-size:12px; margin-bottom:8px; }
  .desc.big { font-size:13px; margin-bottom:12px; }
  .tags { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }
  .tags span { background:#1e2432; border-radius:99px; padding:1px 8px; font-size:11px; color:#c7d2e0; }
  .tags .dim { background:none; }
  .row, .strip { display:flex; gap:10px; flex-wrap:wrap; align-items:flex-end; }
  .strip { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; margin:8px 0 20px; }
  .cell { display:flex; flex-direction:column; align-items:center; gap:4px; }
  .stage { background: repeating-conic-gradient(#181c28 0% 25%, #141824 0% 50%) 0 0/16px 16px; border-radius:6px; padding:8px; display:flex; align-items:center; justify-content:center; }
  figcaption { font-size:11px; color:var(--dim); }

  .detail-head { display:flex; align-items:center; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
  .detail-head h2 { font-size:18px; }
  .big-id { font-size:13px; }
  .detail-body { display:grid; grid-template-columns: minmax(320px, 460px) 1fr; gap:24px; align-items:start; }
  .viewer { position:sticky; top:104px; }
  .viewer-stage { border:1px solid var(--line); border-radius:10px; padding:24px; min-height:240px; display:flex; align-items:center; justify-content:center;
    background: repeating-conic-gradient(#181c28 0% 25%, #141824 0% 50%) 0 0/16px 16px; }
  .viewer-stage.bg-ground { background:#1a1420; } .viewer-stage.bg-ink { background:#10121a; } .viewer-stage.bg-light { background:#e6e1d3; }
  .viewer-stage.sil svg { filter: brightness(0) saturate(0); }
  .viewer-stage.sil.bg-ink svg, .viewer-stage.sil.bg-ground svg { filter: brightness(0) invert(1); }
  .viewer-stage .stage { background:none; padding:0; }
  .viewer-stage .row { gap:20px; justify-content:center; }
  .viewer-controls { display:flex; align-items:center; gap:14px; margin-top:10px; font-size:12px; color:var(--mut); flex-wrap:wrap; }
  .viewer-controls label { display:flex; align-items:center; gap:6px; }
  .bgs { display:flex; align-items:center; gap:4px; }
  .bgs button { width:18px; height:18px; padding:0; border-radius:4px; background: repeating-conic-gradient(#181c28 0% 25%, #141824 0% 50%) 0 0/8px 8px; }
  .bgs button.on { outline:2px solid var(--acc); outline-offset:1px; }
  .hint { font-size:11px; margin-top:8px; max-width:44ch; }
  .factgrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:6px 14px; margin-bottom:12px; font-size:12px; }
  .factgrid > div { display:flex; gap:8px; justify-content:space-between; border-bottom:1px dotted #222736; padding-bottom:3px; }
  .factgrid > div.wide { grid-column: 1 / -1; }
  table.parts { width:100%; border-collapse:collapse; font-size:12px; }
  table.parts td { padding:4px 8px 4px 0; border-bottom:1px solid #1b2030; vertical-align:top; }
  table.parts tr:hover { background:#171b28; }
  .pid { color:#ffd93b; } .tok { color:#7ae87a; }
  .sub-item { border-left:2px solid var(--line); padding:2px 0 2px 10px; margin-bottom:10px; }
  .sub-item p { color:var(--mut); font-size:12px; }
  .sub-item ul { margin:4px 0 0 0; padding-left:16px; }
  .sub-item li { font-size:11px; color:var(--dim); }

  .swatches { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px; margin-bottom:16px; }
  .swatch { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px; }
  .chips { display:flex; height:34px; border-radius:6px; overflow:hidden; margin-bottom:6px; }
  .chips i { flex:1; } .chips i.main { flex:2.2; }
  .swatch .dim, .tok span { font-size:11px; }
  .swatch code { display:block; }
  .tokrow { display:flex; gap:12px; flex-wrap:wrap; }
  .tok { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px 14px; min-width:130px; }
  .tok > div { display:flex; justify-content:space-between; gap:16px; }
  .empty { color:var(--dim); padding:40px 0; }
  @media (max-width: 900px) { .detail-body { grid-template-columns:1fr; } .viewer { position:static; } }
</style>

<header class="top">
  <div class="titlerow">
    <h1>PolyGraphics</h1>
    <span class="sub">${reg.assets.size} assets · ${cats.length} categories</span>
    <div class="spacer"></div>
    <input id="q" type="search" placeholder="search id, name, description, part…  ( / )">
    <span id="live"><b></b> live</span>
  </div>
  <nav class="tabs">${tabs}</nav>
</header>

<main>
  <section class="panel" data-panel="tokens" hidden>${swatches(reg.tokens)}</section>
  ${panels}
  <section class="panel" data-panel="themes" hidden>${themeSections}</section>
  <section class="panel" data-panel="__search" hidden><div class="grid" id="results"></div><p class="empty" id="noresults" hidden>nothing matches.</p></section>
  ${details}
</main>

<script>
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const panels = $$('.panel'), tabs = $$('nav.tabs button'), details = $$('.detail');
  const q = $('#q'), results = $('#results');
  const firstTab = tabs[1]?.dataset.tab || 'tokens';

  const show = (name) => {
    panels.forEach(p => p.hidden = p.dataset.panel !== name);
    tabs.forEach(t => t.classList.toggle('on', t.dataset.tab === name));
    if (name !== '__search') sessionStorage.tab = name;
  };

  // ---- detail routing: #/<asset id>
  let openId = null;
  const closeDetail = () => {
    if (!openId) return;
    const d = $('#d-' + openId.replace(/\\./g, '-'));
    const card = $('#c-' + openId.replace(/\\./g, '-'));
    const row = $('[data-stage]', d).firstElementChild;
    if (row && card) card.appendChild(row);      // put the art back where it lives
    d.hidden = true;
    openId = null;
  };
  const openDetail = (id) => {
    const d = $('#d-' + id.replace(/\\./g, '-'));
    if (!d) return false;
    closeDetail();
    panels.forEach(p => p.hidden = true);
    // Move (not clone) the card's row in: one copy in the DOM means the
    // animation CSS keeps its unique ids.
    const card = $('#c-' + id.replace(/\\./g, '-'));
    const stage = $('[data-stage]', d);
    if (card) stage.appendChild($('[data-row]', card));
    applyZoom(d);
    d.hidden = false;
    openId = id;
    tabs.forEach(t => t.classList.toggle('on', t.dataset.tab === card?.dataset.cat));
    window.scrollTo(0, 0);
    return true;
  };
  const applyZoom = (d) => {
    const row = $('[data-stage] > *', d);
    if (row) row.style.zoom = $('[data-zoom]', d).value;
  };

  const route = () => {
    const m = location.hash.match(/^#\\/(.+)$/);
    if (m && openDetail(decodeURIComponent(m[1]))) return;
    closeDetail();
    if (q.value.trim()) return runSearch();
    restoreCards();
    show(sessionStorage.tab && $('[data-panel="' + CSS.escape(sessionStorage.tab) + '"]') ? sessionStorage.tab : firstTab);
  };

  tabs.forEach(t => t.onclick = () => {
    q.value = ''; sessionStorage.search = ''; restoreCards();
    if (location.hash) { history.replaceState(null, '', location.pathname); closeDetail(); }
    show(t.dataset.tab);
  });
  $$('[data-back]').forEach(b => b.onclick = () => { history.replaceState(null, '', location.pathname); route(); });

  // ---- search across every category
  // Cards are moved into the results grid rather than cloned, for the same
  // reason the detail view moves them: two copies of one SVG means two
  // elements answering to the same animation id. Moving means we owe every
  // card a way home, so each grid remembers the order it started in.
  const cards = $$('.card');
  const homes = new Map();
  $$('.panel[data-panel] .grid').forEach(g => { if (g.id !== 'results') homes.set(g, [...g.children]); });
  const restoreCards = () => {
    for (const [g, kids] of homes) if (g.children.length !== kids.length) g.replaceChildren(...kids);
  };

  function runSearch() {
    const term = q.value.trim().toLowerCase();
    sessionStorage.search = q.value;
    if (!term) { restoreCards(); route(); return; }
    if (location.hash) { history.replaceState(null, '', location.pathname); closeDetail(); }
    const hits = cards.filter(c => c.dataset.hay.includes(term));
    results.replaceChildren(...hits.map(c => c));   // moves the real cards in
    $('#noresults').hidden = hits.length > 0;
    panels.forEach(p => p.hidden = p.dataset.panel !== '__search');
    tabs.forEach(t => t.classList.remove('on'));
  }
  let t0; q.oninput = () => { clearTimeout(t0); t0 = setTimeout(runSearch, 120); };
  if (sessionStorage.search) q.value = sessionStorage.search;

  // ---- viewer controls
  $$('.detail').forEach(d => {
    $('[data-zoom]', d).oninput = () => applyZoom(d);
    const stage = $('[data-stage]', d);
    $('[data-silhouette]', d).onchange = (e) => stage.classList.toggle('sil', e.target.checked);
    $$('[data-bg]', d).forEach(b => b.onclick = () => {
      $$('[data-bg]', d).forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      stage.className = 'viewer-stage' + (b.dataset.bg === 'checker' ? '' : ' bg-' + b.dataset.bg) +
        (stage.classList.contains('sil') ? ' sil' : '');
    });
  });

  // ---- copy buttons
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-copy]');
    if (!b) return;
    await navigator.clipboard.writeText(b.dataset.copy);
    const was = b.textContent; b.textContent = 'copied ✓';
    setTimeout(() => b.textContent = was, 1200);
  });

  // ---- keyboard: / focuses search, Esc clears/closes
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && e.target !== q) { e.preventDefault(); q.focus(); q.select(); }
    if (e.key === 'Escape') {
      if (document.activeElement === q && q.value) { q.value = ''; runSearch(); }
      else if (location.hash) { history.replaceState(null, '', location.pathname); route(); }
    }
  });

  window.addEventListener('hashchange', route);
  // Restore where you were, then hand scrolling back.
  route();
  if (sessionStorage.scroll && !location.hash) window.scrollTo(0, +sessionStorage.scroll);
  addEventListener('scroll', () => sessionStorage.scroll = window.scrollY, { passive: true });

  // ---- reload when the file is rebuilt, keeping tab/search/open asset
  let stamp = null;
  setInterval(async () => {
    try {
      const r = await fetch(location.pathname, { method: 'HEAD', cache: 'no-store' });
      const lm = r.headers.get('last-modified') || r.headers.get('etag');
      if (stamp && lm && lm !== stamp) location.reload();
      stamp = lm;
    } catch {}
  }, 1000);
})();
</script>
`;
}
