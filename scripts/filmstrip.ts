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
import { mkdirSync, writeFileSync } from "node:fs";
import { Resvg } from "@resvg/resvg-js";
import type { Anim, Asset, Part } from "../src/schema.js";
import { renderSVG } from "../src/render.js";
import { poseAsset } from "../src/anim.js";
import { loadLibrary, ownerOf } from "../src/apps.js";

const root = new URL("..", import.meta.url);
const lib = loadLibrary();

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

const owner = ownerOf(lib, id);
const asset = owner?.assets.get(id);
if (!owner || !asset) throw new Error(`unknown asset ${id}`);
const reg = owner.reg;
const tokens = owner.tokens;
const anim = asset.animations?.[clip];
if (!anim) throw new Error(`${id} has no animation "${clip}"`);

/** The document posed at t, read through the same clip code the renderer and adapters use. */
function poseAt(t: number) {
  return poseAsset(asset!, anim!, t, reg.tokens.alpha);
}

const [w, h] = asset.size;
const vScale = variant ? (asset.variants?.[variant]?.scale ?? 1) : 1;
const cellW = w * vScale * scale;
const cellH = h * vScale * scale;
const cells: string[] = [];
for (let f = 0; f < frames; f++) {
  // the same sampling bakeSheet uses: a frame short of the end, so what you are
  // looking at is what the engine will actually show
  const pose = poseAt(f / frames);
  const { svg, issues } = renderSVG(pose.asset, reg, { variant, displayScale: scale, uid: `f${f}`, tints: pose.tints });
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
