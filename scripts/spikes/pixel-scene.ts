/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §Looks and
 * §Scenes, against the second reference: a dark pixel-art frame with depth, light and a HUD.
 *
 * What it tries, each a line of the plan:
 *
 *   native resolution    the whole frame is drawn at 480×270 with anti-aliasing off, then scaled ×3
 *                        nearest-neighbour — the pixel grid is the scene's, not each sprite's
 *   depth → atmosphere   every background layer gets its colours from ONE number, its depth: mixed in
 *                        OKLab toward the fog colour and stripped of chroma as it recedes
 *   tiles                the ground is one 16×16 tile document stamped along a row
 *   existing documents   the player (`ss.figure.dot`) and the boss (`ss.enemy.boss`) are the repo's own
 *                        documents through the pixel pass of pixel-look.ts, unedited
 *   emission             light belongs to a TOKEN: any pixel painted from `$pheromone`, `$pink`,
 *                        `$ember` or `$arcane` feeds the bloom — nobody marks the boss's organs by hand
 *   mixed resolution     bloom is computed AFTER the upscale, so glow is smooth over hard pixels,
 *                        which is how the reference reads
 *
 *   npx tsx scripts/spikes/pixel-scene.ts   → out/spikes/pixel-scene.png (1440×810) + pixel-scene-native.png
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { PNG } from "pngjs";
import { renderSVG } from "../../src/render.js";
import { loadLibrary, ownerOf, ROOT } from "../../src/apps.js";
import { mulberry32 } from "../../src/prng.js";
import { fromOklab, hexRgb, hueShiftedRamp, oklab, pad, paletteFor, pixelPass, raster, snapRegistry, type Img, type RGB } from "./pixel.js";

const NW = 480, NH = 270, UP = 3;
const GROUND = 222;
const lib = loadLibrary();
const ss = lib.apps.find((a) => a.id === "ss")!;
const T = ss.reg.tokens.colors;
const hex = ([r, g, b]: RGB) => `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
const ramp = (token: string, step: number) => hex(hueShiftedRamp(T[token])[step]);

// ---------------------------------------------------------------- depth → atmosphere

const FOG = hexRgb("#4e3fa8"); // v2: a saturated violet — v1 was #5b4f8f and stripped chroma with depth
/** A layer's colour from its base colour and its depth (0 = the play plane, 1 = the horizon). */
function atDepth(base: string, depth: number): string {
  const a = oklab(hexRgb(base)), b = oklab(FOG);
  const k = Math.min(1, depth * 0.85);
  const L = a[0] + (b[0] - a[0]) * k;
  const chroma = 1; // v1 was 1 - 0.6 × depth: the style probe put the frame at half the reference's chroma
  return hex(fromOklab([L, (a[1] + (b[1] - a[1]) * k) * chroma, (a[2] + (b[2] - a[2]) * k) * chroma]).rgb);
}

// ---------------------------------------------------------------- background, at native resolution

const bg: string[] = [];
// sky in hard bands — a pixel game's gradient is a staircase
const sky = ["#150e30", "#1d1545", "#281d5c", "#342673", "#41308a"];
sky.forEach((c, i) => bg.push(`<rect y="${i * 34}" width="${NW}" height="${NH - i * 34}" fill="${c}"/>`));
bg.push(`<circle cx="392" cy="46" r="17" fill="#cfc6ef"/><circle cx="386" cy="42" r="15" fill="#e4dcfb"/>`);

/** A silhouette layer: towers, spires and a ragged top edge, every colour taken at `depth`. */
function skyline(depth: number, seed: number, base: string, minH: number, maxH: number, step: [number, number]): string {
  const rng = mulberry32(seed);
  const fill = atDepth(base, depth), rim = atDepth(T.heather, Math.min(1, depth + 0.1));
  let s = "", x = -10;
  while (x < NW + 10) {
    const w = step[0] + Math.floor(rng() * (step[1] - step[0]));
    const h = minH + Math.floor(rng() * (maxH - minH));
    const top = GROUND - h;
    s += `<rect x="${x}" y="${top}" width="${w}" height="${h + 60}" fill="${fill}"/>`;
    if (rng() < 0.5) s += `<polygon points="${x},${top} ${x + w / 2},${top - w * 0.9} ${x + w},${top}" fill="${fill}"/>`;
    s += `<rect x="${x}" y="${top}" width="1" height="${h}" fill="${rim}"/>`; // moonlit edge
    if (rng() < 0.35) s += `<rect x="${x + Math.floor(w / 2) - 1}" y="${top + 8}" width="2" height="3" fill="${atDepth(T.ember, depth)}"/>`;
    x += w + Math.floor(rng() * 6);
  }
  return s;
}
bg.push(skyline(0.9, 1, T.dead, 70, 150, [14, 30]));
bg.push(skyline(0.55, 2, T.dead, 40, 110, [18, 40]));

// mid layer: a stand of dead trunks and hanging roots
{
  const rng = mulberry32(3);
  const trunk = atDepth(T.dead, 0.3), dark = atDepth(T.dead, 0.1);
  let s = "";
  for (let i = 0; i < 7; i++) {
    const x = 10 + i * 70 + Math.floor(rng() * 30), w = 8 + Math.floor(rng() * 8);
    s += `<rect x="${x}" y="0" width="${w}" height="${GROUND}" fill="${trunk}"/><rect x="${x + w - 2}" y="0" width="2" height="${GROUND}" fill="${dark}"/>`;
    for (let r = 0; r < 3; r++) {
      const rx = x + Math.floor(rng() * w), len = 20 + Math.floor(rng() * 50);
      s += `<rect x="${rx}" y="0" width="1" height="${len}" fill="${trunk}"/>`;
    }
  }
  bg.push(s);
}

// the ground: one 16×16 tile, stamped along a row
function tile(x: number, y: number, seed: number, surface: boolean): string {
  const rng = mulberry32(seed);
  const top = ramp("moss", 2), topLit = ramp("moss", 3), soil = ramp("dead", 2), soilLit = ramp("rust", 1), soilDark = ramp("dead", 0);
  let s = `<rect x="${x}" y="${y}" width="16" height="16" fill="${soil}"/>`;
  if (surface) {
    s += `<rect x="${x}" y="${y}" width="16" height="4" fill="${top}"/><rect x="${x}" y="${y}" width="16" height="1" fill="${topLit}"/>`;
    for (let i = 0; i < 4; i++) s += `<rect x="${x + Math.floor(rng() * 15)}" y="${y - 1 - Math.floor(rng() * 2)}" width="1" height="2" fill="${topLit}"/>`;
  }
  s += `<rect x="${x + 2 + Math.floor(rng() * 6)}" y="${y + 8}" width="5" height="3" fill="${soilLit}"/><rect x="${x}" y="${y + 15}" width="16" height="1" fill="${soilDark}"/>`;
  return s;
}
{
  let s = "";
  for (let x = 0, i = 0; x < NW; x += 16, i++) for (let y = GROUND; y < NH; y += 16) s += tile(x, y, 100 + i + y, y === GROUND);
  bg.push(s);
}

// two lanterns hanging into the frame
const emissiveSvg: string[] = [];
for (const [x, len] of [[70, 46], [262, 30]]) {
  bg.push(`<rect x="${x}" y="0" width="1" height="${len}" fill="${ramp("steel", 0)}"/><rect x="${x - 4}" y="${len}" width="9" height="11" fill="${ramp("coal", 1)}"/>`);
  const flame = `<rect x="${x - 2}" y="${len + 2}" width="5" height="7" fill="${ramp("ember", 2)}"/><rect x="${x - 1}" y="${len + 4}" width="3" height="4" fill="${ramp("gold", 4)}"/>`;
  bg.push(flame);
  emissiveSvg.push(flame);
}

// the arcane burst at the player's feet: tongues of flame in the $arcane ramp, all of it emissive
{
  const rng = mulberry32(9);
  let s = "";
  for (let i = 0; i < 9; i++) {
    const cx = 112 + i * 7 + Math.floor(rng() * 4), h = 10 + Math.floor(rng() * 26), w = 5 + Math.floor(rng() * 5);
    const tongue = (hh: number, ww: number, c: string) =>
      `<polygon points="${cx - ww},${GROUND} ${cx - ww / 3},${GROUND - hh * 0.6} ${cx + 1},${GROUND - hh} ${cx + ww / 2},${GROUND - hh * 0.55} ${cx + ww},${GROUND}" fill="${c}"/>`;
    s += tongue(h, w, ramp("arcane", 1)) + tongue(h * 0.7, w * 0.6, ramp("arcane", 3)) + tongue(h * 0.35, w * 0.3, ramp("arcane", 4));
  }
  emissiveSvg.push(s);
}

const svgOf = (body: string[]) =>
  `<svg xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges" width="${NW}" height="${NH}" viewBox="0 0 ${NW} ${NH}">${body.join("")}</svg>`;

// ---------------------------------------------------------------- the repo's own documents, pixel-passed

function sprite(id: string): { img: Img; emissive: Img } {
  const asset = ss.assets.get(id)!;
  const snapped = snapRegistry(ss.reg.assets, ss.reg.tokens);
  const { svg } = renderSVG(snapped.assets.get(id)!, snapped);
  const pal = paletteFor(asset, ss.reg.tokens, ss.reg.assets);
  const { img, idx } = pixelPass(pad(raster(svg.replace("<svg ", '<svg shape-rendering="crispEdges" '), 1), 1), pal, hexRgb(T.ink));
  const EMITS = new Set(["pheromone", "pink", "ember", "arcane", "spore"]);
  const emissive: Img = { w: img.w, h: img.h, px: new Uint8Array(img.px.length) };
  for (let i = 0; i < idx.length; i++)
    if (idx[i] >= 0 && EMITS.has(pal.names[pal.family[idx[i]]])) emissive.px.set(img.px.subarray(i * 4, i * 4 + 4), i * 4);
  return { img, emissive };
}

/** Straight-alpha over, at integer pixel positions — sprites never land between pixels. */
function over(dst: Img, src: Img, ox: number, oy: number): void {
  for (let y = 0; y < src.h; y++)
    for (let x = 0; x < src.w; x++) {
      const si = (y * src.w + x) * 4;
      if (src.px[si + 3] === 0) continue;
      const dx = ox + x, dy = oy + y;
      if (dx < 0 || dy < 0 || dx >= dst.w || dy >= dst.h) continue;
      dst.px.set(src.px.subarray(si, si + 4), (dy * dst.w + dx) * 4);
    }
}

const frame = raster(svgOf(bg), 1);
const glow = raster(svgOf([`<rect width="${NW}" height="${NH}" fill="none"/>`, ...emissiveSvg]), 1);
const player = sprite("ss.figure.dot");
const boss = sprite("ss.enemy.boss");
over(frame, player.img, 96, GROUND - player.img.h + 1);
over(glow, player.emissive, 96, GROUND - player.img.h + 1);
over(frame, boss.img, 318, 52);
over(glow, boss.emissive, 318, 52);
over(frame, raster(svgOf(emissiveSvg), 1), 0, 0);

// HUD, drawn on the same pixel grid: a framed boss bar and the player's bar
{
  const hud = [
    `<rect x="140" y="8" width="200" height="11" fill="${T.ink}"/>`,
    `<rect x="141" y="9" width="198" height="9" fill="${ramp("gold", 0)}"/><rect x="142" y="10" width="196" height="7" fill="${T.ink}"/>`,
    `<rect x="143" y="11" width="150" height="5" fill="${ramp("arcane", 2)}"/><rect x="143" y="11" width="150" height="1" fill="${ramp("arcane", 4)}"/>`,
    `<polygon points="136,13 140,9 144,13 140,17" fill="${ramp("gold", 3)}"/><polygon points="336,13 340,9 344,13 340,17" fill="${ramp("gold", 3)}"/>`,
    `<rect x="8" y="252" width="84" height="9" fill="${T.ink}"/><rect x="9" y="253" width="60" height="7" fill="${ramp("blood", 2)}"/><rect x="9" y="253" width="60" height="1" fill="${ramp("blood", 4)}"/>`,
    `<rect x="8" y="232" width="17" height="17" fill="${T.ink}"/><rect x="9" y="233" width="15" height="15" fill="${ramp("slate", 1)}"/>`,
  ];
  over(frame, raster(svgOf([`<rect width="${NW}" height="${NH}" fill="none"/>`, ...hud]), 1), 0, 0);
}

// ---------------------------------------------------------------- upscale, then light

function upscale(img: Img, k: number): Float32Array {
  const W = img.w * k, H = img.h * k, out = new Float32Array(W * H * 3);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const si = (Math.floor(y / k) * img.w + Math.floor(x / k)) * 4, di = (y * W + x) * 3;
      const a = img.px[si + 3] / 255;
      for (let c = 0; c < 3; c++) out[di + c] = (img.px[si + c] / 255) * (a > 0 ? 1 : 0);
    }
  return out;
}

/** Three box passes each way ≈ a Gaussian; cheap and separable. */
function blur(buf: Float32Array, W: number, H: number, r: number): Float32Array {
  let a: Float32Array = buf, b: Float32Array = new Float32Array(buf.length);
  const pass = (src: Float32Array, dst: Float32Array, horiz: boolean) => {
    const n = horiz ? W : H, m = horiz ? H : W;
    for (let j = 0; j < m; j++)
      for (let c = 0; c < 3; c++) {
        let acc = 0;
        const idx = (i: number) => (horiz ? (j * W + i) * 3 + c : (i * W + j) * 3 + c);
        for (let i = -r; i <= r; i++) acc += src[idx(Math.max(0, Math.min(n - 1, i)))];
        for (let i = 0; i < n; i++) {
          dst[idx(i)] = acc / (2 * r + 1);
          acc += src[idx(Math.min(n - 1, i + r + 1))] - src[idx(Math.max(0, i - r))];
        }
      }
  };
  for (let k = 0; k < 3; k++) {
    pass(a, b, true); [a, b] = [b, a];
    pass(a, b, false); [a, b] = [b, a];
  }
  return a;
}

const W = NW * UP, H = NH * UP;
const base = upscale(frame, UP);
const em = upscale(glow, UP);
const tight = blur(em, W, H, 4), wide = blur(em, W, H, 16);
const png = new PNG({ width: W, height: H });
for (let y = 0; y < H; y++)
  for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 3;
    const dx = x / W - 0.5, dy = y / H - 0.5;
    const vig = 1 - 0.55 * Math.min(1, (dx * dx + dy * dy) * 2.2);
    for (let c = 0; c < 3; c++) {
      const v = (base[i + c] + tight[i + c] * 0.9 + wide[i + c] * 0.7) * vig;
      png.data[(y * W + x) * 4 + c] = Math.round(255 * Math.min(1, v));
    }
    png.data[(y * W + x) * 4 + 3] = 255;
  }

const outDir = `${ROOT}out/spikes`;
mkdirSync(outDir, { recursive: true });
writeFileSync(`${outDir}/pixel-scene.png`, PNG.sync.write(png));
const native = new PNG({ width: NW, height: NH });
native.data.set(frame.px);
writeFileSync(`${outDir}/pixel-scene-native.png`, PNG.sync.write(native));
console.log(`✓ pixel-scene.png ${W}×${H} from a ${NW}×${NH} frame; ss.figure.dot ${player.img.w}×${player.img.h}, ss.enemy.boss ${boss.img.w}×${boss.img.h}`);
