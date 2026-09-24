/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §More references.
 *
 * Reference C: a daylight pixel-art forest — a bright sky, blue-green depth, foliage in shaded
 * clumps, a ruin, a floating island hung with leaves, a tree boss with saplings, a slash, damage
 * numbers and a HUD. What it adds over pixel-scene.ts:
 *
 *   daylight depth   the fog is the sky's own pale cyan, so distance brightens instead of darkening
 *   clump()          foliage as cluster shading: one ramp, one light direction, no hand-placed leaves
 *   pixels()         the hero is authored AT the pixel scale, as rows over a legend — the answer to
 *                    the Dot failure in pixel-look.ts, not a vector document squeezed down
 *   text3x5()        damage numbers and HUD labels in a bitmap font that is itself `pixels`
 *
 *   npx tsx scripts/spikes/forest-scene.ts   → out/spikes/forest.png (1440×810)
 */
import { mulberry32 } from "../../src/prng.js";
import { atDepth, branchTree, brush, clump, d, finish, frameSvg, pixels, rampHex, rasterFonts, text3x5, textWidth3x5, writeOut, type P } from "./kit.js";

const NW = 480, NH = 270, UP = 3, GROUND = 206;

// the palette: seven base colours, each a five-step hue-shifted ramp (darkest first)
const SKY = "#7fcdef", HAZE = "#c4ecf5";
const leaf = rampHex("#4f9e3a"), lime = rampHex("#b9d83a"), bark = rampHex("#a8742e"), stone = rampHex("#7f8fa0");
const soil = rampHex("#34404a"), wood = rampHex("#8a5a34"), blood = rampHex("#d83040"), cloud = ["#b8dcef", "#d4ebf6", "#eaf6fb", "#ffffff", "#ffffff"];
const INK = "#15141c";

const bg: string[] = [], fg: string[] = [], glow: string[] = [];

// ---------------------------------------------------------------- sky, clouds, the far wood

["#6cc2ec", "#7ecbef", "#92d4f1", "#a8ddf3", "#bde6f5", HAZE].forEach((c, i) => bg.push(`<rect y="${i * 26}" width="${NW}" height="${NH}" fill="${c}"/>`));
bg.push(clump(46, 26, 34, 1, cloud), clump(96, 14, 26, 2, cloud), clump(16, 48, 20, 3, cloud), clump(175, 30, 18, 4, cloud));

/** A wood at one depth: straight trunks under clumped crowns, every colour taken at that depth. */
function wood_(depth: number, seed: number, y0: number, count: number, rMin: number, rMax: number): string {
  const rng = mulberry32(seed);
  const crown = leaf.map((c) => atDepth(c, HAZE, depth));
  const trunk = atDepth(bark[1], HAZE, depth);
  let s = "";
  for (let i = 0; i < count; i++) {
    const x = Math.round((i + rng() * 0.8) * (NW / count)), r = rMin + rng() * (rMax - rMin), top = y0 + rng() * 30;
    s += `<rect x="${x - 2}" y="${Math.round(top)}" width="${4 + Math.round(r / 10)}" height="${GROUND - top}" fill="${trunk}"/>`;
    s += clump(x, top, r, seed * 100 + i, crown);
  }
  return s;
}
bg.push(wood_(0.8, 5, 70, 7, 26, 40));
// one giant far tree, the kind the reference lets tower over the whole frame
bg.push(`<rect x="286" y="40" width="26" height="170" fill="${atDepth(bark[1], HAZE, 0.72)}"/>`, clump(300, 52, 58, 9, leaf.map((c) => atDepth(c, HAZE, 0.72))));
bg.push(wood_(0.5, 6, 100, 6, 22, 34));

// ---------------------------------------------------------------- the ruin: two arches of mossy stone

function arch(x: number, w: number, h: number, depth: number): string {
  const st = stone.map((c) => atDepth(c, HAZE, depth)), mo = leaf.map((c) => atDepth(c, HAZE, depth));
  const top = GROUND - h;
  let s = `<rect x="${x}" y="${top}" width="10" height="${h}" fill="${st[1]}"/><rect x="${x + w - 10}" y="${top}" width="10" height="${h}" fill="${st[1]}"/>`;
  s += `<rect x="${x}" y="${top}" width="3" height="${h}" fill="${st[3]}"/><rect x="${x + w - 10}" y="${top}" width="3" height="${h}" fill="${st[3]}"/>`;
  // the arch itself: a thick ring's upper half, lit on the left
  const r = w / 2 - 5, cx = x + w / 2, cy = top + 4;
  s += `<path d="M${cx - r - 5} ${cy} A${r + 5} ${r + 5} 0 0 1 ${cx + r + 5} ${cy} L${cx + r - 4} ${cy} A${r - 4} ${r - 4} 0 0 0 ${cx - r + 4} ${cy} Z" transform="translate(0 0)" fill="${st[2]}"/>`;
  for (let k = 0; k < 7; k++) {
    const a = Math.PI + (k / 6) * Math.PI;
    s += `<rect x="${Math.round(cx + Math.cos(a) * r)}" y="${Math.round(cy + Math.sin(a) * r)}" width="2" height="2" fill="${st[0]}"/>`;
  }
  s += clump(x + 5, top - 2, 7, x, mo) + clump(cx - 6, cy - r - 4, 8, x + 1, mo);
  return s;
}
bg.push(arch(118, 62, 74, 0.32), arch(176, 44, 54, 0.32));
bg.push(`<rect x="100" y="${GROUND - 34}" width="12" height="34" fill="${atDepth(stone[1], HAZE, 0.32)}"/><path d="M100 ${GROUND - 34} L112 ${GROUND - 40} L112 ${GROUND - 34} Z" fill="${atDepth(stone[2], HAZE, 0.32)}"/>`);

// the big tree on the left and the bushes along the back of the ground
bg.push(`<path d="${d(brush([[48, GROUND], [52, 150], [44, 100], [52, 70]], [[0, 14], [1, 7]]))}" fill="${bark[1]}"/>`);
bg.push(clump(40, 58, 46, 11, leaf), clump(88, 76, 30, 12, leaf));
for (let i = 0; i < 9; i++) bg.push(clump(20 + i * 54, GROUND - 8, 16 + (i % 3) * 4, 20 + i, leaf.map((c) => atDepth(c, HAZE, 0.15))));

// ---------------------------------------------------------------- the rock overhead, hung with leaves

{
  const edge: P[] = [];
  for (let x = 212; x <= NW + 4; x += 12) edge.push([x, 30 + Math.sin(x * 0.07) * 6 + ((x * 7) % 5)]);
  const rock: P[] = [[212, -4], [NW + 4, -4], ...edge.slice().reverse()];
  bg.push(`<path d="${d(rock)}" fill="${soil[1]}"/>`);
  bg.push(`<path d="${d(edge.map(([x, y]) => [x, y - 4] as P).concat(edge.slice().reverse()))}" fill="${soil[0]}"/>`);
  bg.push(pixels(["..aa..a..aa..", ".aabaaabaaba.", "abbbbbbbbbbba"], { a: soil[2], b: soil[3] }, 300, 4, 1));
  const rng = mulberry32(31);
  edge.forEach(([x, y], i) => {
    if (i === 0) return;
    for (let k = 0; k < 3; k++) {
      const lx = x - 12 + k * 4 + Math.round(rng() * 3), len = 4 + Math.round(rng() * 7);
      bg.push(`<rect x="${lx}" y="${Math.round(y - 2)}" width="3" height="${len}" fill="${lime[1]}"/><rect x="${lx}" y="${Math.round(y - 2)}" width="1" height="${len - 1}" fill="${lime[3]}"/>`);
      bg.push(`<rect x="${lx + 1}" y="${Math.round(y - 2) + len}" width="1" height="2" fill="${lime[4]}"/>`);
    }
    bg.push(`<rect x="${x - 12}" y="${Math.round(y) - 3}" width="12" height="3" fill="${leaf[2]}"/>`);
  });
}

// ---------------------------------------------------------------- ground, ledge, island

function earth(x0: number, x1: number, top: number, bottom: number, seed: number, fence = false): string {
  const rng = mulberry32(seed);
  // v2: the ground's body on the ramp's base step — v1 used the dark step, and the probe put the frame's
  // lows at L 0.24 against the reference's 0.37
  let s = `<rect x="${x0}" y="${top}" width="${x1 - x0}" height="${bottom - top}" fill="${soil[2]}"/>`;
  for (let i = 0; i < (x1 - x0) / 6; i++)
    s += `<rect x="${x0 + Math.round(rng() * (x1 - x0))}" y="${top + 8 + Math.round(rng() * (bottom - top - 8))}" width="${2 + Math.round(rng() * 3)}" height="2" fill="${soil[rng() < 0.5 ? 1 : 3]}"/>`;
  s += `<rect x="${x0}" y="${top}" width="${x1 - x0}" height="5" fill="${leaf[2]}"/><rect x="${x0}" y="${top}" width="${x1 - x0}" height="1" fill="${leaf[4]}"/><rect x="${x0}" y="${top + 5}" width="${x1 - x0}" height="2" fill="${leaf[0]}"/>`;
  for (let x = x0; x < x1; x += 3) {
    const h = 1 + Math.round(rng() * 3);
    s += `<rect x="${x}" y="${top - h}" width="1" height="${h}" fill="${leaf[rng() < 0.4 ? 4 : 3]}"/>`;
    if (rng() < 0.3) s += `<rect x="${x + 1}" y="${top + 5}" width="1" height="${2 + Math.round(rng() * 4)}" fill="${leaf[1]}"/>`;
  }
  if (fence)
    for (let x = x0 + 16; x < x1 - 6; x += 11) {
      s += `<rect x="${x}" y="${top - 13}" width="3" height="13" fill="${wood[1]}"/><rect x="${x}" y="${top - 13}" width="1" height="13" fill="${wood[3]}"/>`;
      s += `<rect x="${x - 8}" y="${top - 10}" width="11" height="2" fill="${wood[2]}"/>`;
    }
  return s;
}
fg.push(earth(-2, NW + 2, GROUND, NH, 41));
fg.push(earth(-2, 118, 116, GROUND + 4, 42, true));
fg.push(pixels([".b.", "bwb", ".b."], { b: "#6a8ef0", w: "#e8f0ff" }, 30, 110), pixels([".b.", "bwb", ".b."], { b: "#6a8ef0", w: "#e8f0ff" }, 72, 111));
// the floating island: a grassy top over a tapering underside
{
  const under: P[] = [[190, 132], [338, 132], [326, 146], [300, 154], [262, 158], [228, 152], [202, 144]];
  fg.push(`<path d="${d(under)}" fill="${soil[2]}"/>`, earth(190, 338, 128, 134, 43));
  fg.push(clump(256, 116, 9, 44, blood) + `<rect x="255" y="124" width="2" height="5" fill="${leaf[1]}"/>`);
  fg.push(pixels(["..k..k..", ".kWkkWk.", "..kkkk.."], { k: INK, W: "#fff4e0" }, 252, 113));
}

// ---------------------------------------------------------------- the tree boss and its saplings

{
  const x = 400, top = 128;
  const trunk: P[] = [[x - 26, GROUND], [x - 20, top + 20], [x - 12, top + 4], [x + 12, top + 4], [x + 22, top + 22], [x + 28, GROUND]];
  fg.push(clump(x, top - 8, 34, 51, leaf), clump(x - 24, top + 6, 18, 52, leaf), clump(x + 26, top + 4, 20, 53, leaf));
  fg.push(`<path d="${d(trunk)}" fill="${bark[2]}"/>`);
  for (let k = 0; k < 6; k++) fg.push(`<rect x="${x - 18 + k * 7}" y="${top + 10}" width="2" height="${GROUND - top - 12}" fill="${bark[1]}"/>`);
  fg.push(`<rect x="${x - 20}" y="${top + 10}" width="4" height="${GROUND - top - 10}" fill="${bark[3]}"/>`);
  // the face: two sockets and a mouth cut into the bark, eyes lit from inside
  fg.push(pixels([
    "..kkk.....kkk..",
    ".kkkkk...kkkkk.",
    ".kkykk...kkykk.",
    "..kkk.....kkk..",
    "......bbb......",
    ".....bbbbb.....",
    "...kkkkkkkkk...",
    "....kkkkkkk....",
  ], { k: bark[0], y: "#ffe070", b: bark[3] }, x - 15, top + 22, 2));
  glow.push(`<rect x="${x - 9}" y="${top + 26}" width="2" height="2" fill="#ffe070"/><rect x="${x + 7}" y="${top + 26}" width="2" height="2" fill="#ffe070"/>`);
  // roots for feet, and arms as bare branches
  for (const [rx, dir] of [[x - 24, -1], [x + 26, 1]] as [number, number][])
    fg.push(`<path d="${d(brush([[rx, GROUND - 14], [rx + dir * 10, GROUND - 4], [rx + dir * 16, GROUND]], [[0, 7], [1, 2]]))}" fill="${bark[1]}"/>`);
  for (const b of branchTree({ at: [x - 20, top + 30], angle: Math.PI * 1.1, len: 16, width: 5, depth: 2, seed: 54, twist: 0.5 }))
    fg.push(`<path d="${d(b.pts)}" fill="${bark[2]}"/>`);
}
function sapling(x: number, h: number, seed: number, flip: boolean): string {
  let s = "";
  for (const b of branchTree({ at: [x, GROUND], angle: -Math.PI / 2, len: h, width: 6, depth: 2, seed, twist: 0.35, spread: 0.9, kids: [2, 2] }))
    s += `<path d="${d(b.pts)}" fill="${b.depth === 2 ? bark[2] : bark[3]}"/>`;
  s += clump(x + (flip ? -3 : 3), GROUND - h - 6, 7, seed + 1, lime);
  s += pixels(["k.k", "..."], { k: INK }, x - 1, GROUND - h + 4);
  return s;
}
fg.push(sapling(342, 22, 61, false), sapling(360, 28, 62, true), sapling(452, 24, 63, false), sapling(468, 18, 64, true));

// ---------------------------------------------------------------- the hero, authored at the pixel scale

const HERO = [
  "....wwwww.....",
  "...wWWwwww....",
  "..wWwwwwwws...",
  "..wwkkwkkws...",
  "..wwkkwkkws...",
  "..swwwwwwss...",
  "...sww.wws....",
  "....rrrrr.RR..",
  "...rrRRRrrRRR.",
  "..bbbbbbbR..R.",
  ".wbbbbbbb.....",
  "..bbbbbbbw....",
  "..bb...bb.....",
  ".bbb...bbb....",
];
const heroSvg = pixels(HERO, { w: "#e8e0cc", W: "#fffaf0", s: "#a89c86", k: INK, r: blood[2], R: blood[0], b: "#2c2838" }, 214, GROUND - HERO.length - 6);

// the slash: one brush swept under and round the hero, all of it emissive
{
  const cx = 262, cy = 166, r = 40;
  const arc: P[] = [178, 150, 120, 90, 60, 30, 5, -25].map((a) => [cx + Math.cos((a * Math.PI) / 180) * r, cy + Math.sin((a * Math.PI) / 180) * r * 0.78] as P);
  const s = `<path d="${d(brush(arc, [[0, 0.5], [0.35, 11], [0.7, 7], [1, 0.5]]))}" fill="#dff4ff"/><path d="${d(brush(arc, [[0, 0.3], [0.35, 5], [0.7, 3], [1, 0.3]]))}" fill="#ffffff"/>`;
  glow.push(s);
  // hit marks across the saplings: thin red cuts
  for (const [x0, y0, x1, y1] of [[318, 150, 356, 196], [330, 196, 364, 154], [300, 170, 350, 178]])
    glow.push(`<path d="${d(brush([[x0, y0], [x1, y1]], [[0, 0.3], [0.5, 2.4], [1, 0.3]]))}" fill="${blood[3]}"/>`);
}
fg.push(text3x5("18", 286, 110, "#ffffff", { outline: INK }), text3x5("20", 276, 120, "#ffffff", { outline: INK }));

// ---------------------------------------------------------------- HUD, on the same grid

const hud: string[] = [];
{
  hud.push(`<circle cx="22" cy="248" r="16" fill="${INK}"/><circle cx="22" cy="248" r="14" fill="#3a3448"/>`);
  hud.push(pixels(HERO.slice(0, 7), { w: "#e8e0cc", W: "#fffaf0", s: "#a89c86", k: INK }, 16, 239));
  hud.push(`<rect x="4" y="262" width="22" height="7" fill="${INK}"/>`, text3x5("SPACE", 5, 263, "#ffffff"));
  ["A", "S", "D"].forEach((k, i) => {
    const x = 44 + i * 20;
    hud.push(`<rect x="${x}" y="228" width="17" height="17" fill="${INK}"/><rect x="${x + 1}" y="229" width="15" height="15" fill="#4a1c1c"/>`);
    hud.push(clump(x + 8, 238, 6, 70 + i, rampHex("#e8602a")));
    hud.push(`<rect x="${x + 5}" y="224" width="7" height="7" fill="${INK}"/>`, text3x5(k, x + 7, 225, "#ffffff"));
  });
  hud.push(`<rect x="40" y="250" width="100" height="9" fill="${INK}"/><rect x="41" y="251" width="59" height="7" fill="#b048d8"/><rect x="41" y="251" width="59" height="1" fill="#e0a0ff"/>`);
  const label = "60/100";
  hud.push(text3x5(label, 90 - Math.floor(textWidth3x5(label) / 2), 252, "#ffffff", { outline: INK }));
  // minimap: rooms as outlines, the player a green cell, the boss red
  hud.push(`<rect x="398" y="226" width="78" height="40" fill="${INK}"/><rect x="399" y="227" width="76" height="38" fill="#1e2530"/>`);
  for (const [x, y, w, h] of [[404, 250, 30, 8], [434, 244, 12, 14], [446, 250, 24, 8], [414, 236, 14, 8]])
    hud.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="none" stroke="#6a7a8a" stroke-width="1"/>`);
  hud.push(`<rect x="438" y="250" width="3" height="3" fill="#40e060"/><rect x="452" y="252" width="3" height="3" fill="#e84040"/><rect x="459" y="252" width="3" height="3" fill="#e84040"/>`);
  hud.push(`<circle cx="385" cy="244" r="3" fill="#f0b030"/>`, text3x5("0", 377, 242, "#ffffff"), `<path d="M385 252 L388 255 L385 258 L382 255 Z" fill="#b060f0"/>`, text3x5("0", 377, 253, "#ffffff"));
}

// ---------------------------------------------------------------- compose

const frame = rasterFonts(frameSvg(NW, NH, [...bg, ...fg, ...glow, heroSvg, ...hud]));
const glowImg = rasterFonts(frameSvg(NW, NH, glow));
const png = finish(frame, glowImg, { up: UP, bloom: { tight: 3, wide: 12, tightGain: 0.5, wideGain: 0.25 }, vignette: 0.12 });
console.log(`✓ ${writeOut("forest.png", png)} ${NW * UP}×${NH * UP} from a ${NW}×${NH} frame`);
