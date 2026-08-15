/**
 * Field-readability lint. A sprite that a player has to pick out of a crowd at
 * minute 13 is judged by its contrast against the floor, not by how nice it
 * looks alone — so measure that, per asset, the same way every time.
 *
 *   npx tsx scripts/readability.ts            # all in-world ss.* assets
 *   npx tsx scripts/readability.ts ss.enemy.imp ss.char.dot
 *
 * Reports, against the mean colour of the ground tile:
 *   contrast  WCAG-style ratio of mean sprite luminance vs mean ground luminance
 *   bright%   share of opaque pixels above 0.18 luminance — the focal points
 *   cover%    share of the canvas the sprite actually fills
 */
import { readdirSync, readFileSync } from "node:fs";
import { Resvg } from "@resvg/resvg-js";
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

/** sRGB → relative luminance, per WCAG. */
function luminance(r: number, g: number, b: number): number {
  const f = (v: number): number => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}

const contrast = (a: number, b: number): number => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);

interface Stats { mean: [number, number, number]; lum: number; bright: number; cover: number }

function measure(id: string): Stats | null {
  const asset = assets.get(id);
  if (!asset) return null;
  const { svg } = renderSVG(asset, reg);
  const png = new Resvg(svg, { fitTo: { mode: "zoom", value: 2 } }).render();
  const { pixels, width, height } = { pixels: png.asPng(), width: png.width, height: png.height };
  // decode via resvg's raw RGBA buffer instead of the PNG bytes
  const raw = new Resvg(svg, { fitTo: { mode: "zoom", value: 2 } }).render().pixels;
  void pixels;
  let r = 0, g = 0, b = 0, n = 0, bright = 0;
  for (let i = 0; i < raw.length; i += 4) {
    const a = raw[i + 3];
    if (a < 128) continue;
    r += raw[i]; g += raw[i + 1]; b += raw[i + 2];
    if (luminance(raw[i], raw[i + 1], raw[i + 2]) > 0.18) bright++;
    n++;
  }
  if (!n) return null;
  const mean: [number, number, number] = [r / n, g / n, b / n];
  return {
    mean,
    lum: luminance(mean[0], mean[1], mean[2]),
    bright: bright / n,
    cover: n / (width * height),
  };
}

const ground = measure("ss.env.ground");
if (!ground) throw new Error("ss.env.ground failed to render");

const ids = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const targets = ids.length
  ? ids
  : [...assets.keys()].filter((id) => /^ss\.(char|enemy|pickup)\./.test(id)).sort();

console.log(`ground mean rgb(${ground.mean.map((v) => Math.round(v)).join(",")}) luminance ${ground.lum.toFixed(4)}\n`);
console.log("asset                 contrast  bright%  cover%   mean");
console.log("─".repeat(64));

const rows: { id: string; c: number }[] = [];
for (const id of targets) {
  const s = measure(id);
  if (!s) { console.log(`${id.padEnd(21)} — no opaque pixels`); continue; }
  const c = contrast(s.lum, ground.lum);
  rows.push({ id, c });
  const flag = c < 2.5 ? "  ← sinks into the floor" : c < 3.5 ? "  ← thin" : "";
  console.log(
    `${id.padEnd(21)} ${c.toFixed(2).padStart(7)}  ${(s.bright * 100).toFixed(0).padStart(6)}%  ` +
      `${(s.cover * 100).toFixed(0).padStart(5)}%   rgb(${s.mean.map((v) => Math.round(v)).join(",")})${flag}`,
  );
}

const weak = rows.filter((r) => r.c < 2.5);
console.log(
  `\n${rows.length} assets · median contrast ${rows.map((r) => r.c).sort((a, b) => a - b)[Math.floor(rows.length / 2)].toFixed(2)}` +
    ` · ${weak.length} below 2.5`,
);
if (weak.length) console.log(`weak: ${weak.map((r) => r.id).join(", ")}`);
