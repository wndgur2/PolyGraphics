/**
 * Contact sheet for the animation loop. `inspect.ts` shows an asset big, at
 * game scale and as a silhouette; this adds the thing that page cannot show —
 * the clip itself, posed frame by frame the way the engine adapters pose it
 * (offsets added in the parent frame, rotation about the part's own origin),
 * so a leg hinged at the hip and a ball on a chain can be checked without
 * waiting on a browser. Also prints the rendered bounds against the canvas,
 * because a feeler that leaves the frame is invisible in the SVG and a hard
 * edge in the bake.
 *
 *   npx tsx scripts/sheet.ts ss.char.dot [ss.char.tri …] [--anim walk] [--frames 8]
 *
 * Writes out/sheet/<id>--<anim>.png: the base render at 8×, the silhouette,
 * two game-scale copies, then the frames at 4×.
 */
import { writeFileSync, mkdirSync } from "node:fs";
import { Resvg } from "@resvg/resvg-js";
import type { Asset, Anim } from "../src/schema.js";
import { renderSVG } from "../src/render.js";
import { poseAsset, type PoseTint } from "../src/anim.js";
import { loadLibrary, ownerOf, type Owner } from "../src/apps.js";

const root = new URL("..", import.meta.url).pathname;
const outDir = root + "out/sheet";
mkdirSync(outDir, { recursive: true });
const lib = loadLibrary();
for (const i of lib.issues) if (i.level === "error") console.log("✖", i.where, i.msg);

/** The document posed at `p`, read through the same clip code the renderer and adapters use. */
function posed(owner: Owner, a: Asset, anim: Anim, p: number): { asset: Asset; tints: Record<string, PoseTint> } {
  return poseAsset(a, anim, p, owner.tokens.alpha);
}

const args = process.argv.slice(2);
const animFlag = args.includes("--anim") ? args[args.indexOf("--anim") + 1] : undefined;
const frames = args.includes("--frames") ? Number(args[args.indexOf("--frames") + 1]) : 8;
const ids = args.filter((x, i) => !x.startsWith("--") && args[i - 1] !== "--anim" && args[i - 1] !== "--frames");
function png(svg: string, zoom: number, ground: string): { buf: Buffer; w: number; h: number } {
  const r = new Resvg(svg, { fitTo: { mode: "zoom", value: zoom }, background: ground }).render();
  return { buf: Buffer.from(r.asPng()), w: r.width, h: r.height };
}

for (const id of ids) {
  const o = ownerOf(lib, id);
  const a = o?.assets.get(id);
  if (!o || !a) { console.log("unknown", id); continue; }
  const reg = o.reg;
  const animName = animFlag ?? Object.keys(a.animations ?? {})[0];
  const anim = animName ? a.animations?.[animName] : undefined;
  const [w, h] = a.size;
  // compose a single SVG sheet: big base | frames row | silhouette | game scale
  const cellBig = 8, cellFrame = 4;
  const bigW = w * cellBig, bigH = h * cellBig;
  const items: string[] = [];
  let x = 0;
  const strip = (svg: string, sx: number, sy: number, s: number, extra = "") =>
    `<g transform="translate(${sx},${sy}) scale(${s})"${extra}>${svg.replace(/<svg[^>]*>/, "").replace("</svg>", "")}</g>`;
  const base = renderSVG(a, reg, {}).svg;
  for (const iss of renderSVG(a, reg, { animation: animName }).issues) console.log(`${iss.level} ${iss.where}: ${iss.msg}`);
  const ax = (a.anchor ?? [0.5, 0.5])[0] * w, ay = (a.anchor ?? [0.5, 0.5])[1] * h;
  items.push(strip(base, x + ax * cellBig, ay * cellBig, cellBig));
  x += bigW + 8;
  // silhouette
  items.push(`<rect x="${x}" y="0" width="${bigW / 2}" height="${bigH / 2}" fill="#000"/>`);
  items.push(strip(base, x + ax * cellBig / 2, ay * cellBig / 2, cellBig / 2, ` style="filter:brightness(0) invert(1)"`));
  // game scale (1.35x like inspect) under it
  items.push(strip(base, x + ax * 1.35 + 4, bigH / 2 + 8 + ay * 1.35, 1.35));
  items.push(strip(base, x + 60 + ax * 2, bigH / 2 + 8 + ay * 2, 2));
  x += bigW / 2 + 8;
  let totalH = bigH;
  if (anim) {
    let fx = 0;
    for (let f = 0; f < frames; f++) {
      const p = f / frames;
      const svg = ((q) => renderSVG(q.asset, reg, { tints: q.tints }))(posed(o, a, anim, p)).svg;
      items.push(strip(svg, x + fx + ax * cellFrame, ay * cellFrame, cellFrame));
      items.push(`<text x="${x + fx + 2}" y="${h * cellFrame + 12}" fill="#8fa" font-size="10" font-family="monospace">${p.toFixed(2)}</text>`);
      fx += w * cellFrame + 4;
    }
    totalH = Math.max(totalH, h * cellFrame + 16);
    x += fx;
  }
  const sheet = `<svg xmlns="http://www.w3.org/2000/svg" width="${x}" height="${totalH}"><g style="paint-order:stroke" stroke-linejoin="round" stroke-linecap="round">${items.join("")}</g></svg>`;
  // bounds of the base pose against the canvas — the edge a feeler must not cross
  const probe = new Resvg(base, { fitTo: { mode: "zoom", value: 4 } }).render();
  const px = probe.pixels, pw = probe.width, ph = probe.height;
  let minX = pw, minY = ph, maxX = -1, maxY = -1;
  for (let y = 0; y < ph; y++) for (let x = 0; x < pw; x++) if (px[(y * pw + x) * 4 + 3] > 40) { if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y; }
  const bl = minX / 4 - ax, bt = minY / 4 - ay, br = (maxX + 1) / 4 - ax, bb = (maxY + 1) / 4 - ay;
  const touches = [bl <= -ax + 0.3 && "left", bt <= -ay + 0.3 && "top", br >= w - ax - 0.3 && "right", bb >= h - ay - 0.3 && "bottom"].filter(Boolean);
  console.log(`  bounds x ${bl.toFixed(1)}..${br.toFixed(1)} y ${bt.toFixed(1)}..${bb.toFixed(1)} on ${w}×${h}${touches.length ? ` — ▲ touches ${touches.join(", ")}` : ""}`);
  const out = png(sheet, 1, o.tokens.colors.soil ?? "#131019");
  const file = `${outDir}/${id.replace(/\./g, "-")}${animName ? "--" + animName : ""}.png`;
  writeFileSync(file, out.buf);
  console.log(`✓ ${file} ${out.w}×${out.h}${animName ? ` anim=${animName}` : ""}`);
}
