/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §More references.
 *
 * Reference D: a dark gothic pixel-art nave — fluted columns, a stone Pietà holding a wasted body,
 * candelabra, a floor of broken flagstones, a penitent with a sword. Almost no colour (the reference
 * measures C̄ 0.010), and the only light is candle flame. What it adds:
 *
 *   lit pixel art    the frame is drawn at full value and then LIT: a dim ambient times every pixel,
 *                    plus each candle's falloff, computed at the output resolution — the plan's
 *                    phase-6 light, done the cheap way (no normal maps), and enough for this frame
 *   emission exempt  flames are painted back at full strength after lighting, then bloom
 *   figures of brush a statue and a body built from tapered strokes: limbs, folds, claws
 *
 *   npx tsx scripts/spikes/cathedral-scene.ts   → out/spikes/cathedral.png (1440×810)
 */
import { mulberry32 } from "../../src/prng.js";
import { brush, d, finish, frameSvg, pixels, rampHex, rasterFonts, writeOut, type Light, type P } from "./kit.js";

const NW = 480, NH = 270, UP = 3, FLOOR = 226;

const stone = rampHex("#6f706a"), wall = rampHex("#3a3b3c"), flesh = rampHex("#9c7462"), gold = rampHex("#c8a040");
const INK = "#0c0c0e", FLAME = "#fff0b0", FLAME2 = "#ffb040";

const bg: string[] = [], fg: string[] = [], glow: string[] = [];
const lights: Light[] = [];

// ---------------------------------------------------------------- the nave: wall, niches, the dark above

bg.push(`<rect width="${NW}" height="${NH}" fill="${wall[1]}"/>`);
{
  const rng = mulberry32(3);
  // courses of stone, each block a shade off its neighbour
  for (let y = 0; y < FLOOR; y += 9)
    for (let x = (y / 9) % 2 ? -8 : 0; x < NW; x += 16) {
      const k = rng();
      bg.push(`<rect x="${x}" y="${y}" width="15" height="8" fill="${k < 0.3 ? wall[0] : k < 0.85 ? wall[1] : wall[2]}"/>`);
    }
  // two tall lancet niches, darker than the wall, with a lit sill
  for (const cx of [210, 300]) {
    bg.push(`<path d="M${cx - 18} 150 L${cx - 18} 60 Q${cx} 20 ${cx + 18} 60 L${cx + 18} 150 Z" fill="${wall[0]}"/>`);
    bg.push(`<path d="M${cx - 12} 150 L${cx - 12} 66 Q${cx} 36 ${cx + 12} 66 L${cx + 12} 150 Z" fill="${INK}"/>`);
    bg.push(`<rect x="${cx - 20}" y="150" width="40" height="3" fill="${wall[3]}"/>`);
  }
  // the carved screen on the left: a lattice of small reliefs
  for (let y = 40; y < 200; y += 12) for (let x = 6; x < 60; x += 10) bg.push(`<rect x="${x}" y="${y}" width="6" height="8" fill="${wall[2]}"/><rect x="${x}" y="${y}" width="6" height="2" fill="${wall[3]}"/>`);
}

// ---------------------------------------------------------------- columns

function column(x: number, w: number, top: number, bottom: number): string {
  let s = `<rect x="${x}" y="${top}" width="${w}" height="${bottom - top}" fill="${stone[1]}"/>`;
  for (let i = 0; i < w; i += 4) s += `<rect x="${x + i}" y="${top}" width="2" height="${bottom - top}" fill="${i < w / 3 ? stone[2] : stone[0]}"/>`;
  s += `<rect x="${x}" y="${top}" width="2" height="${bottom - top}" fill="${stone[3]}"/>`;
  for (let y = top + 26; y < bottom - 10; y += 30) s += `<rect x="${x - 2}" y="${y}" width="${w + 4}" height="4" fill="${stone[1]}"/><rect x="${x - 2}" y="${y}" width="${w + 4}" height="1" fill="${stone[3]}"/>`;
  s += `<rect x="${x - 6}" y="${bottom - 14}" width="${w + 12}" height="14" fill="${stone[1]}"/><rect x="${x - 6}" y="${bottom - 14}" width="${w + 12}" height="2" fill="${stone[3]}"/>`;
  return s;
}
bg.push(column(338, 38, -4, FLOOR), column(96, 30, -4, 40));
// the broken column on the left: a stump on a plinth, its top sheared
bg.push(column(70, 40, 118, FLOOR));
bg.push(`<path d="M68 118 L112 108 L112 124 L68 124 Z" fill="${stone[2]}"/><path d="M68 118 L112 108 L112 111 L68 121 Z" fill="${stone[3]}"/>`);

// ---------------------------------------------------------------- the Pietà

{
  const robe = stone, veil = stone.map((c, i) => stone[Math.min(4, i + 1)]);
  // plinth
  fg.push(`<rect x="146" y="200" width="156" height="26" fill="${stone[0]}"/><rect x="146" y="200" width="156" height="2" fill="${stone[2]}"/>`);
  // the seated mother: a robe falling from the shoulders to a wide lap and down to the plinth
  const body: P[] = [[204, 70], [230, 70], [244, 96], [250, 130], [286, 150], [300, 200], [150, 200], [162, 150], [186, 128], [192, 96]];
  fg.push(`<path d="${d(body)}" fill="${robe[1]}"/>`);
  // folds: long strokes of light and shadow following the drape
  for (const [pts, c, w] of [
    [[[210, 90], [200, 130], [182, 170], [166, 198]], robe[2], 5], [[[228, 92], [236, 130], [262, 160], [284, 198]], robe[0], 5],
    [[[196, 140], [210, 170], [214, 198]], robe[0], 4], [[[240, 150], [246, 176], [252, 198]], robe[2], 4],
    [[[222, 100], [220, 140], [228, 198]], robe[3], 2], [[[180, 150], [172, 180], [160, 198]], robe[3], 2],
  ] as [P[], string, number][])
    fg.push(`<path d="${d(brush(pts, [[0, 1], [0.4, w], [1, w * 0.6]]))}" fill="${c}"/>`);
  // the head under its veil, bowed toward the body
  fg.push(`<path d="${d(brush([[214, 44], [210, 58], [202, 78], [194, 102]], [[0, 14], [0.4, 20], [1, 12]]))}" fill="${veil[1]}"/>`);
  fg.push(`<path d="${d(brush([[216, 50], [214, 60], [212, 70]], [[0, 9], [1, 8]]))}" fill="${robe[3]}"/><rect x="210" y="57" width="5" height="2" fill="${robe[1]}"/><rect x="211" y="64" width="3" height="1" fill="${robe[1]}"/>`);
  fg.push(`<path d="${d(brush([[222, 42], [228, 60], [232, 84], [240, 104]], [[0, 6], [1, 4]]))}" fill="${veil[2]}"/>`);

  // the body across her lap: arched back, the head thrown down to the left, long legs to the floor
  const skin = flesh;
  const torso = brush([[168, 132], [190, 124], [214, 128], [238, 136], [256, 148]], [[0, 16], [0.4, 24], [1, 18]]);
  fg.push(`<path d="${d(torso)}" fill="${skin[1]}"/>`);
  fg.push(`<path d="${d(brush([[176, 126], [198, 120], [222, 124]], [[0, 2], [0.5, 5], [1, 2]]))}" fill="${skin[3]}"/>`);
  for (let k = 0; k < 5; k++) fg.push(`<path d="${d(brush([[194 + k * 8, 124], [196 + k * 8, 136]], [[0, 2], [1, 1]]))}" fill="${skin[0]}"/>`); // ribs
  // head and the horn-like crest hanging back
  fg.push(`<path d="${d(brush([[168, 132], [156, 128], [146, 118], [138, 104]], [[0, 12], [0.5, 10], [1, 3]]))}" fill="${skin[1]}"/>`);
  fg.push(`<path d="${d(brush([[150, 122], [140, 112], [134, 100], [138, 90], [146, 86]], [[0, 5], [1, 1]]))}" fill="${skin[2]}"/>`);
  fg.push(`<path d="${d(brush([[150, 124], [148, 132], [152, 138]], [[0, 5], [1, 1]]))}" fill="${skin[0]}"/>`);
  // arms: one hanging, fingers splayed to claws; one crooked up
  fg.push(`<path d="${d(brush([[176, 138], [170, 156], [166, 176], [170, 188]], [[0, 6], [1, 4]]))}" fill="${skin[1]}"/>`);
  for (const [dx, dy] of [[-6, 12], [-2, 14], [3, 13], [7, 10]])
    fg.push(`<path d="${d(brush([[170, 188], [170 + dx * 0.5, 188 + dy * 0.6], [170 + dx, 188 + dy]], [[0, 2.4], [1, 0.6]]))}" fill="${skin[1]}"/>`);
  fg.push(`<path d="${d(brush([[236, 136], [252, 118], [262, 104], [270, 102]], [[0, 6], [1, 3]]))}" fill="${skin[2]}"/>`);
  for (const [dx, dy] of [[8, -6], [10, -1], [9, 4]])
    fg.push(`<path d="${d(brush([[270, 102], [270 + dx * 0.6, 102 + dy * 0.6], [270 + dx, 102 + dy]], [[0, 2], [1, 0.5]]))}" fill="${skin[2]}"/>`);
  // legs: thigh, knee, shin — bone showing through at the knee
  for (const [hip, knee, foot] of [[[252, 150], [290, 150], [304, 210]], [[250, 156], [278, 170], [276, 214]]] as [P, P, P][]) {
    fg.push(`<path d="${d(brush([hip, [(hip[0] + knee[0]) / 2, (hip[1] + knee[1]) / 2 - 2], knee], [[0, 14], [1, 9]]))}" fill="${skin[1]}"/>`);
    fg.push(`<path d="${d(brush([[hip[0], hip[1] - 3], [(hip[0] + knee[0]) / 2, (hip[1] + knee[1]) / 2 - 5], [knee[0], knee[1] - 3]], [[0, 3], [1, 2]]))}" fill="${skin[3]}"/>`);
    fg.push(`<path d="${d(brush([knee, [(knee[0] + foot[0]) / 2 + 2, (knee[1] + foot[1]) / 2], foot], [[0, 9], [0.5, 6], [1, 5]]))}" fill="${skin[1]}"/>`);
    fg.push(`<rect x="${knee[0] - 2}" y="${knee[1] - 2}" width="4" height="3" fill="${skin[3]}"/>`);
    fg.push(`<path d="${d(brush([foot, [foot[0] + 6, foot[1] + 4], [foot[0] + 11, foot[1] + 6]], [[0, 4], [1, 1]]))}" fill="${skin[0]}"/>`);
  }
  // the mother's hands holding it: pale, at the shoulder and the hip
  fg.push(`<path d="${d(brush([[186, 118], [178, 124], [174, 130]], [[0, 6], [1, 4]]))}" fill="${robe[3]}"/>`, `<path d="${d(brush([[250, 140], [258, 146], [262, 154]], [[0, 6], [1, 4]]))}" fill="${robe[3]}"/>`);
}

// ---------------------------------------------------------------- candelabra, and the candles on the floor

function candle(x: number, y: number, h: number): string {
  glow.push(`<rect x="${x}" y="${y - h - 3}" width="1" height="2" fill="${FLAME}"/><rect x="${x}" y="${y - h - 1}" width="1" height="1" fill="${FLAME2}"/>`);
  lights.push({ at: [x, y - h - 2], r: 34, color: "#ffb866", power: 0.45 });
  return `<rect x="${x - 1}" y="${y - h}" width="2" height="${h}" fill="#d8d0b8"/><rect x="${x - 1}" y="${y - h}" width="1" height="${h}" fill="#f0ead8"/>`;
}
function candelabrum(x: number, h: number, arms: number): string {
  const top = FLOOR - h;
  let s = `<rect x="${x - 1}" y="${top}" width="2" height="${h}" fill="${gold[1]}"/><rect x="${x - 1}" y="${top}" width="1" height="${h}" fill="${gold[3]}"/>`;
  s += `<path d="M${x - 6} ${FLOOR} L${x} ${FLOOR - 7} L${x + 6} ${FLOOR} Z" fill="${gold[1]}"/>`;
  for (let k = 0; k < 3; k++) s += `<rect x="${x - 2}" y="${top + 10 + k * 18}" width="4" height="2" fill="${gold[2]}"/>`;
  if (arms === 1) return s + `<rect x="${x - 3}" y="${top - 2}" width="6" height="2" fill="${gold[2]}"/>` + candle(x, top - 2, 7);
  const span = (arms - 1) * 5;
  s += `<rect x="${x - span / 2 - 1}" y="${top}" width="${span + 2}" height="2" fill="${gold[2]}"/>`;
  for (let k = 0; k < arms; k++) {
    const cx = x - span / 2 + k * 5, lift = k === (arms - 1) / 2 ? 6 : Math.abs(k - (arms - 1) / 2) < 1.5 ? 3 : 0;
    s += `<rect x="${cx}" y="${top - lift}" width="1" height="${lift + 1}" fill="${gold[1]}"/>` + candle(cx, top - lift, 6);
  }
  return s;
}
fg.push(candelabrum(130, 64, 1), candelabrum(152, 48, 1), candelabrum(316, 56, 1), candelabrum(372, 52, 5), candelabrum(468, 70, 1));
// a spear leaning on the broken column, as in the reference
fg.push(`<path d="${d(brush([[66, 222], [80, 150]], [[0, 2], [1, 2]]))}" fill="${wall[3]}"/><path d="M78 150 L84 138 L84 152 Z" fill="${stone[3]}"/>`);

// ---------------------------------------------------------------- the floor: broken flagstones

{
  const rng = mulberry32(17);
  fg.push(`<rect y="${FLOOR}" width="${NW}" height="${NH - FLOOR}" fill="${INK}"/>`);
  for (let i = 0; i < 150; i++) {
    const x = rng() * NW, y = FLOOR - 6 + Math.pow(rng(), 1.6) * 28, w = 5 + rng() * 12, h = 2 + rng() * 5, tilt = (rng() - 0.5) * 4;
    const tone = stone[Math.floor(rng() * 3)];
    const q: P[] = [[x, y + tilt], [x + w, y - tilt], [x + w - 1, y + h], [x + 1, y + h + tilt * 0.5]];
    fg.push(`<path d="${d(q)}" fill="${tone}"/><path d="${d([[x, y + tilt], [x + w, y - tilt], [x + w, y - tilt + 1], [x, y + tilt + 1]])}" fill="${stone[3]}"/>`);
  }
  // candle stubs among the stones, in little clusters
  for (const [cx, n] of [[176, 4], [236, 3], [292, 3], [440, 3]] as [number, number][])
    for (let k = 0; k < n; k++) fg.push(candle(cx + k * 3, FLOOR + (k % 2), 3 + (k % 3)));
  // the sarcophagus lid at the bottom right
  fg.push(`<path d="M320 262 L420 262 L430 250 L330 250 Z" fill="${stone[1]}"/><rect x="320" y="262" width="100" height="10" fill="${stone[0]}"/><path d="M330 250 L430 250 L429 252 L331 252 Z" fill="${stone[3]}"/>`);
}

// ---------------------------------------------------------------- the penitent, authored at the pixel scale

const PENITENT = [
  ".......s.......",
  ".......s.......",
  "......sS.......",
  "......sS.......",
  "......sSs......",
  ".....ssSs......",
  ".....sSSs......",
  ".....sSSs......",
  "....ssSSss.....",
  "....sSSSSs.....",
  "....sSSSSs.....",
  "...ssSSSSss....",
  "...sSSSSSSs....",
  "...sSkkkkSs....",
  "...sSSSSSSs....",
  "..ggsSSSSsgg...",
  ".gGggggggggGg..",
  "rRrrrrrrrrrrRr.",
  "rRrrRrrrrRrrRrr",
  "rRrrRrrrrRrrRhh",
  ".RrrRrrrrRrr.hh",
  ".RrrrrrrrrrR...",
  "..rrrrrrrrrr...",
  "..ddddddddddd..",
  "..dDDDdddDDDd..",
  "..dDDDd.dDDDd..",
  "..dDDd...dDDd..",
  "..dDDd...dDDd..",
  "..dDd.....dDd..",
  "..dDd.....dDd..",
  "..kkk.....kkk..",
  ".kkkk.....kkkk.",
];
{
  const x = 392, y = FLOOR - PENITENT.length;
  fg.push(pixels(PENITENT, { s: "#8a8e96", S: "#c8ccd4", k: INK, g: gold[1], G: gold[3], r: "#8c1c24", R: "#c83038", d: "#2a2430", D: "#403848", h: "#d0b070" }, x, y));
  // the sword: hilt at the hand, blade down to the stones
  fg.push(`<path d="${d(brush([[x + 14, y + 19], [x + 30, y + 30], [x + 44, y + 38]], [[0, 3], [0.2, 4], [1, 1]]))}" fill="#9aa0a8"/>`);
  fg.push(`<path d="${d(brush([[x + 14, y + 18], [x + 30, y + 29], [x + 43, y + 37]], [[0, 1], [1, 0.5]]))}" fill="#e0e4ea"/>`);
}

// ---------------------------------------------------------------- compose: draw at full value, then light it

const frame = rasterFonts(frameSvg(NW, NH, [...bg, ...fg, ...glow]));
const glowImg = rasterFonts(frameSvg(NW, NH, glow));
const png = finish(frame, glowImg, {
  up: UP, ambient: "#74767c", lights, // v2: v1 was #5a5a60, and the probe put the frame at L 0.16 against 0.25
  bloom: { tight: 3, wide: 10, tightGain: 0.9, wideGain: 0.5 }, vignette: 0.3,
  lift: 0.085, // v3: the reference's blacks sit at L 0.21 — a matte grade, not more light
});
console.log(`✓ ${writeOut("cathedral.png", png)} ${NW * UP}×${NH * UP}, ${lights.length} candle lights`);
