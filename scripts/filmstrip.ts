/**
 * Bakes a clip to a PNG filmstrip: one column per sampled frame, left to right,
 * on the ground colour the body is actually seen on.
 *
 * The gallery plays an animation as CSS and `scripts/inspect.ts` embeds it the
 * same way, which is the right loop for a loop — you watch it breathe. It is
 * the wrong loop for a one-shot: a death is judged on whether frame 3 still
 * reads as the same creature and whether frame 9 has stopped moving, and both
 * questions want the frames side by side and still.
 *
 *   npx tsx scripts/filmstrip.ts ss.enemy.imp death            → out/strip/ss.enemy.imp.death.png
 *   npx tsx scripts/filmstrip.ts ss.enemy.imp death --frames 8 --scale 4 --variant elite
 */
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { Resvg } from "@resvg/resvg-js";
import { AssetSchema, type Anim, type Asset, type Part } from "../src/schema.js";
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
const flag = (name: string, fallback: string): string => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const positional = args.filter((a, i) => !a.startsWith("--") && !args[i - 1]?.startsWith("--"));
const id = positional[0];
const clip = positional[1] ?? "death";
const frames = Number(flag("frames", "10"));
const scale = Number(flag("scale", "3"));
const variant = args.includes("--variant") ? flag("variant", "") : undefined;

const asset = assets.get(id);
if (!asset) throw new Error(`unknown asset ${id}`);
const anim = asset.animations?.[clip];
if (!anim) throw new Error(`${id} has no animation "${clip}"`);

/** A track's value at t, linearly between its keys — close enough to judge a pose by. */
function valueAt(track: Anim["tracks"][number], t: number): number {
  const keys = track.keys;
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1] = keys[i];
    if (t > t1) continue;
    const [t0, v0] = keys[i - 1];
    const k = t1 === t0 ? 1 : (t - t0) / (t1 - t0);
    return v0 + (v1 - v0) * k;
  }
  return keys[keys.length - 1][1];
}

/** The document posed at t: every track folded into its part's own transform. */
function poseAt(t: number): Asset {
  const parts: Part[] = asset!.parts.map((p) => ({ ...p }));
  const byId = new Map(parts.map((p) => [p.id, p]));
  for (const track of anim!.tracks) {
    const p = byId.get(track.part);
    if (!p) continue;
    const v = valueAt(track, t);
    const [x, y] = p.at ?? [0, 0];
    switch (track.prop) {
      case "x": p.at = [x + v, y]; break;
      case "y": p.at = [x, y + v]; break;
      case "rot": p.rot = (p.rot ?? 0) + v; break;
      case "scale": {
        const s = p.scale ?? 1;
        p.scale = typeof s === "number" ? Math.max(s * v, 0.0001) : [Math.max(s[0] * v, 0.0001), Math.max(s[1] * v, 0.0001)];
        break;
      }
      case "opacity": {
        const o = p.opacity;
        p.opacity = typeof o === "number" ? o * v : v; // a token opacity is read as 1
        break;
      }
    }
  }
  return { ...asset!, parts };
}

const [w, h] = asset.size;
const vScale = variant ? (asset.variants?.[variant]?.scale ?? 1) : 1;
const cellW = w * vScale * scale;
const cellH = h * vScale * scale;
const cells: string[] = [];
for (let f = 0; f < frames; f++) {
  // the same sampling bakeSheet uses: a frame short of the end, so what you are
  // looking at is what the engine will actually show
  const { svg, issues } = renderSVG(poseAt(f / frames), reg, { variant, displayScale: scale, uid: `f${f}` });
  for (const i of issues) console.log(`${i.level === "error" ? "✖" : "▲"} ${i.where}: ${i.msg}`);
  cells.push(svg.replace("<svg ", `<svg x="${f * cellW}" y="0" `));
}

const ground = tokens.colors.soil ?? "#131019";
const strip = `<svg xmlns="http://www.w3.org/2000/svg" width="${frames * cellW}" height="${cellH}">
<rect width="100%" height="100%" fill="${ground}"/>
${cells.join("\n")}
</svg>`;

mkdirSync(new URL("out/strip/", root), { recursive: true });
const out = new URL(`out/strip/${id}.${clip}${variant ? `.${variant}` : ""}.png`, root);
writeFileSync(out, new Resvg(strip).render().asPng());
console.log(`✓ ${frames} frames → ${out.pathname}`);
