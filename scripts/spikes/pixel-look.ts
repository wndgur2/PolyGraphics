/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §Looks.
 *
 * Can an existing vector document come out as pixel art without being redrawn?
 * The pass it tries is the one the plan proposes for `look: "pixel"`:
 *
 *   1. rasterise at the authored size, 1 px = 1 px, with anti-aliasing off (resvg `crispEdges`)
 *   2. snap alpha to 0/1 — pixel art has no partial coverage
 *   3. quantise every pixel to a CLOSED palette: the document's own colour tokens, each
 *      expanded into a five-step hue-shifted ramp in OKLCH (shadows walk toward violet,
 *      lights toward yellow — not toward black and white, which is what `ramps` does today)
 *   4. clean orphans: a lone pixel whose four neighbours agree takes their colour
 *   5. selective outline: one pixel outside the silhouette, coloured the darkest step of
 *      whatever it touches, pulled toward `$ink`
 *
 *   npx tsx scripts/spikes/pixel-look.ts ss.figure.dot ss.enemy.boss …   → out/spikes/pixel-<id>.png
 *
 * Each sheet is four panels, scaled ×SCALE with nearest-neighbour: the vector render (what the
 * document is), the naive 1× bake (what shrinking it does), the pixel pass quantising after the
 * render (v1), and the same pass over a render whose paints were snapped to the ramps first (v2).
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { PNG } from "pngjs";
import { renderSVG } from "../../src/render.js";
import { loadLibrary, ownerOf, ROOT } from "../../src/apps.js";
import { hexRgb, pad, paletteFor, pixelPass, raster, snapRegistry, type Img, type RGB } from "./pixel.js";

const SCALE = 6;
const outDir = `${ROOT}out/spikes`;
mkdirSync(outDir, { recursive: true });
const lib = loadLibrary();

// ---------------------------------------------------------------- sheet

function sheet(panels: Img[], scales: number[], bg: RGB, gap = 12): PNG {
  const W = panels.reduce((s, p, i) => s + p.w * scales[i], 0) + gap * (panels.length + 1);
  const H = Math.max(...panels.map((p, i) => p.h * scales[i])) + gap * 2;
  const png = new PNG({ width: W, height: H });
  for (let i = 0; i < W * H; i++) png.data.set([bg[0], bg[1], bg[2], 255], i * 4);
  let ox = gap;
  panels.forEach((p, k) => {
    const s = scales[k];
    const oy = gap + Math.floor((H - 2 * gap - p.h * s) / 2);
    for (let y = 0; y < p.h * s; y++)
      for (let x = 0; x < p.w * s; x++) {
        const si = (Math.floor(y / s) * p.w + Math.floor(x / s)) * 4;
        const a = p.px[si + 3] / 255;
        if (a === 0) continue;
        const di = ((oy + y) * W + ox + x) * 4;
        // resvg pixels are premultiplied
        for (let c = 0; c < 3; c++) png.data[di + c] = Math.round(p.px[si + c] + png.data[di + c] * (1 - a));
      }
    ox += p.w * s + gap;
  });
  return png;
}

const ids = process.argv.slice(2).filter((a) => !a.startsWith("--"));
if (!ids.length) ids.push("ss.figure.dot", "ss.enemy.boss");
for (const id of ids) {
  const owner = ownerOf(lib, id);
  const asset = owner?.assets.get(id);
  if (!owner || !asset) { console.log(`✖ ${id}: no such asset`); continue; }
  const { svg } = renderSVG(asset, owner.reg);
  const crisp = svg.replace("<svg ", '<svg shape-rendering="crispEdges" ');
  const vector = raster(svg, SCALE);
  const naive = pad(raster(svg, 1), 1);
  const pal = paletteFor(asset, owner.reg.tokens, owner.reg.assets);
  const ink = hexRgb(owner.reg.tokens.colors.ink);
  const { img: pixel, used } = pixelPass(pad(raster(crisp, 1), 1), pal, ink);
  // v2: snap at the paint, then the same pixel pass mops up what translucency mixed
  const snapped = snapRegistry(owner.reg.assets, owner.reg.tokens);
  const { svg: svg2 } = renderSVG(snapped.assets.get(id)!, snapped);
  const crisp2 = svg2.replace("<svg ", '<svg shape-rendering="crispEdges" ');
  const { img: pixel2, used: used2 } = pixelPass(pad(raster(crisp2, 1), 1), pal, ink);
  let offPalette = 0, opaque = 0;
  const raw2 = pad(raster(crisp2, 1), 1);
  const palSet = new Set(pal.colors.map((c) => c.join()));
  for (let i = 0; i < raw2.w * raw2.h; i++)
    if (raw2.px[i * 4 + 3] === 255) { opaque++; if (!palSet.has([raw2.px[i * 4], raw2.px[i * 4 + 1], raw2.px[i * 4 + 2]].join())) offPalette++; }
  const bg = hexRgb(owner.reg.tokens.colors.soil ?? "#1b1210");
  const png = sheet([vector, naive, pixel, pixel2], [1, SCALE, SCALE, SCALE], bg);
  const file = `${outDir}/pixel-${id.replace(/\./g, "-")}.png`;
  writeFileSync(file, PNG.sync.write(png));
  console.log(
    `✓ ${id}: ${asset.size.join("×")} px, palette ${pal.colors.length} (${pal.colors.length / 5} tokens × 5 steps); ` +
      `post-quantise uses ${used}, paint-snapped uses ${used2}, ${((100 * offPalette) / opaque).toFixed(1)}% of its opaque pixels needed snapping → ${file}`,
  );
}
