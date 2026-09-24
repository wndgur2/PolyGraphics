/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §More references.
 *
 * Reference E: a three-quarter top-down pixel-art canyon — ochre sand, a cliff of strata, gnarled
 * dead trees, a tree grown into a throne with something seated in it, a glowing totem, a hero on a
 * selection ring, and a HUD with a round minimap. This is the view `ss` is drawn in, which is why it
 * matters most here. What it adds:
 *
 *   branchTree()    every tree is the same generator with a different seed; twist near 1 is dead wood
 *   one seed, two   the bark highlight is the same tree grown again from the same seed, thinner —
 *     widths        width never touches the rng, so the second growth lands on the first
 *   shadows as a    a three-quarter view needs every standing thing to lay a shadow on the ground:
 *     ramp step     the same outlines sheared and squashed, filled with the ground's DARK STEP rather
 *                   than a translucent black, so the frame stays palette-closed (plan §Looks, pixel)
 *   coloured light  the totem lights the sand cyan through the lightmap, over a warm ambient
 *
 *   npx tsx scripts/spikes/canyon-scene.ts   → out/spikes/canyon.png (1440×810)
 */
import { mulberry32 } from "../../src/prng.js";
import { blob, branchTree, brush, d, finish, frameSvg, pixels, rampHex, rasterFonts, text3x5, textWidth3x5, writeOut, type Light, type P } from "./kit.js";

const NW = 480, NH = 270, UP = 3;
// v3: sand #c09052 → #ae8c58. v1 measured C̄ 0.074, accent 46% against 0.060 and 27%; v2 (#a98c5e) matched
// C̄ but put the whole floor just under the accent threshold, and the share fell to 1%
const sand = rampHex("#ae8c58"), cliff = rampHex("#8a5a32"), bark = rampHex("#5a3a26"), dry = rampHex("#a89040");
const flesh = rampHex("#8a4a3a"), slate = rampHex("#3a4450"), CYAN = "#50ffd8", INK = "#140e0c";

const ground: string[] = [], shadows: string[] = [], standing: string[] = [], glow: string[] = [], hud: string[] = [];
const lights: Light[] = [];

// ---------------------------------------------------------------- sand

ground.push(`<rect width="${NW}" height="${NH}" fill="${sand[2]}"/>`);
{
  const rng = mulberry32(7);
  // broad patches first — wind-scoured light, damp dark — then grain, cracks, tufts, pebbles
  for (let i = 0; i < 14; i++) ground.push(`<path d="${blob(rng() * NW, 60 + rng() * 220, 30 + rng() * 40, 10 + rng() * 14, 100 + i, 0.3)}" fill="${sand[rng() < 0.5 ? 3 : 1]}"/>`);
  for (let i = 0; i < 1400; i++) ground.push(`<rect x="${Math.floor(rng() * NW)}" y="${Math.floor(rng() * NH)}" width="1" height="1" fill="${sand[[1, 3, 0, 4][Math.floor(rng() * 4)]]}"/>`);
  for (let i = 0; i < 9; i++) {
    let x = rng() * NW, y = 80 + rng() * 190;
    const pts: P[] = [[x, y]];
    for (let k = 0; k < 5; k++) { x += 4 + rng() * 8; y += (rng() - 0.5) * 6; pts.push([x, y]); }
    ground.push(`<path d="${d(brush(pts, [[0, 1.2], [1, 0.4]]))}" fill="${sand[0]}"/>`);
  }
  for (let i = 0; i < 40; i++) {
    const x = Math.floor(rng() * NW), y = 70 + Math.floor(rng() * 200);
    ground.push(pixels(["d.d.d", ".dDd.", "..d.."], { d: dry[1], D: dry[3] }, x, y));
  }
  for (let i = 0; i < 30; i++) ground.push(pixels([".pp", "pPp", ".p."], { p: sand[0], P: sand[4] }, Math.floor(rng() * NW), 70 + Math.floor(rng() * 200)));
}

// ---------------------------------------------------------------- the cliff: strata, a lit lip, a shadow at its foot

{
  const lip: P[] = [[-4, 58], [60, 50], [120, 40], [180, 26], [240, 18], [300, 6], [330, -4]];
  const foot: P[] = lip.map(([x, y]) => [x - 6, y + 34 + ((x * 13) % 7)] as P);
  const face = [...lip, ...foot.slice().reverse()];
  standing.push(`<path d="${d(face)}" fill="${cliff[2]}"/>`);
  const rng = mulberry32(11);
  // strata run with the lip; cracks cut down through them
  for (let k = 1; k < 6; k++)
    standing.push(`<path d="${d(brush(lip.map(([x, y]) => [x - k, y + k * 5.5 + ((x * (k + 3)) % 3)] as P), [[0, 1.4], [1, 1.4]]))}" fill="${cliff[k % 2 ? 0 : 2]}"/>`);
  for (let x = 4; x < 320; x += 14 + Math.floor(rng() * 20)) {
    const y0 = 58 - (x / 330) * 62;
    standing.push(`<path d="${d(brush([[x, y0 + 3], [x + 2, y0 + 14], [x - 1, y0 + 28]], [[0, 1.2], [1, 0.6]]))}" fill="${cliff[0]}"/>`);
  }
  standing.push(`<path d="${d([[-4, -4], [330, -4], ...lip.slice().reverse()])}" fill="${sand[3]}"/>`);
  standing.push(`<path d="${d(brush(lip, [[0, 3], [1, 3]]))}" fill="${cliff[3]}"/>`);
  shadows.push(`<path d="${d(brush(foot, [[0, 6], [1, 4]]))}" fill="${sand[0]}"/>`);
}

// ---------------------------------------------------------------- trees, each laying its shadow

function tree(x: number, y: number, h: number, seed: number, depth = 4): void {
  const o = { at: [x, y] as P, angle: -Math.PI / 2 + (mulberry32(seed)() - 0.5) * 0.3, len: h, width: h / 3.4, depth, seed, twist: 0.95, spread: 0.75, shrink: 0.7 };
  const limbs = branchTree(o);
  const lit = branchTree({ ...o, width: o.width * 0.35 });
  // the shadow: the same outlines sheared down-left and squashed onto the ground plane
  shadows.push(`<g transform="matrix(1 0 0.9 -0.42 ${-0.9 * y} ${y * 1.42})">${limbs.map((b) => `<path d="${d(b.pts)}"/>`).join("")}</g>`.replace("<g ", `<g fill="${sand[1]}" `));
  standing.push(limbs.map((b) => `<path d="${d(b.pts)}" fill="${bark[b.depth >= depth - 1 ? 1 : 2]}"/>`).join(""));
  standing.push(`<g transform="translate(-1 0)">${lit.map((b) => `<path d="${d(b.pts)}" fill="${bark[3]}"/>`).join("")}</g>`);
  // a knot of roots at the foot
  for (const dir of [-1, 1]) standing.push(`<path d="${d(brush([[x, y - 3], [x + dir * 7, y], [x + dir * 12, y + 2]], [[0, 5], [1, 1]]))}" fill="${bark[1]}"/>`);
}
tree(70, 196, 46, 21);
tree(196, 120, 40, 22);
tree(452, 262, 44, 23);
tree(24, 262, 30, 24, 3);
tree(300, 96, 30, 25, 3);

// ---------------------------------------------------------------- the throne: a tree grown round a seat

{
  const x = 384, y = 158;
  tree(x - 30, y + 2, 64, 31);
  tree(x + 30, y, 58, 32);
  standing.push(`<path d="${d([[x - 30, y + 4], [x - 26, y - 40], [x - 10, y - 58], [x + 12, y - 58], [x + 28, y - 40], [x + 32, y + 4]])}" fill="${bark[1]}"/>`);
  standing.push(`<path d="${d([[x - 18, y - 2], [x - 16, y - 40], [x + 16, y - 40], [x + 20, y - 2]])}" fill="${bark[0]}"/>`);
  // the seated figure: horned, arms on the armrests, legs hanging
  const s = flesh;
  standing.push(`<path d="${d(brush([[x, y - 44], [x, y - 20]], [[0, 12], [1, 16]]))}" fill="${s[1]}"/>`);
  standing.push(`<path d="${blob(x, y - 50, 7, 6, 33, 0.1)}" fill="${s[2]}"/>`, pixels(["y.y"], { y: "#ffd040" }, x - 1, y - 51));
  glow.push(pixels(["y.y"], { y: "#ffd040" }, x - 1, y - 51));
  for (const dir of [-1, 1]) {
    standing.push(`<path d="${d(brush([[x + dir * 4, y - 55], [x + dir * 10, y - 62], [x + dir * 9, y - 70]], [[0, 3], [1, 0.5]]))}" fill="${bark[4]}"/>`);
    standing.push(`<path d="${d(brush([[x + dir * 7, y - 40], [x + dir * 16, y - 30], [x + dir * 20, y - 20]], [[0, 5], [1, 4]]))}" fill="${s[1]}"/>`);
    standing.push(`<path d="${d(brush([[x + dir * 5, y - 20], [x + dir * 8, y - 6], [x + dir * 7, y + 6]], [[0, 7], [1, 4]]))}" fill="${s[0]}"/>`);
  }
  standing.push(`<path d="${d(brush([[x - 3, y - 42], [x - 2, y - 28]], [[0, 2], [1, 1]]))}" fill="${s[3]}"/>`);
}

// ---------------------------------------------------------------- the totem: carved stone, a beam, cyan light

{
  const x = 100, top = 120, bottom = 234;
  shadows.push(`<path d="${d([[x - 6, bottom], [x + 6, bottom], [x - 40, bottom + 16], [x - 52, bottom + 16]])}" fill="${sand[1]}"/>`);
  standing.push(`<rect x="${x - 6}" y="${top}" width="12" height="${bottom - top}" fill="${slate[1]}"/><rect x="${x - 6}" y="${top}" width="2" height="${bottom - top}" fill="${slate[3]}"/>`);
  standing.push(`<rect x="${x - 8}" y="${top - 6}" width="16" height="7" fill="${slate[2]}"/><rect x="${x - 8}" y="${bottom - 8}" width="16" height="8" fill="${slate[0]}"/>`);
  const runes = pixels(["c.c", ".c.", "c.c", "...", "ccc", "c..", "...", ".c.", "ccc", ".c."], { c: CYAN }, x - 1, top + 14);
  const beam = `<rect x="${x - 2}" y="${top + 34}" width="4" height="${bottom - top - 48}" fill="#2ad8b0"/><rect x="${x - 1}" y="${top + 34}" width="2" height="${bottom - top - 48}" fill="#c8fff0"/>`;
  standing.push(runes, beam);
  glow.push(runes, beam);
  lights.push({ at: [x, top + 60], r: 70, color: CYAN, power: 0.55 });
}

// ---------------------------------------------------------------- a stump, fireflies, the hero on its ring

standing.push(`<path d="${blob(210, 250, 12, 6, 41, 0.15)}" fill="${bark[1]}"/><path d="${blob(210, 246, 10, 4, 42, 0.1)}" fill="${bark[3]}"/><path d="${blob(210, 246, 5, 2, 43, 0.1)}" fill="${bark[2]}"/>`);
{
  const rng = mulberry32(51);
  for (let i = 0; i < 7; i++) {
    const x = 150 + Math.floor(rng() * 160), y = 90 + Math.floor(rng() * 110);
    glow.push(`<rect x="${x}" y="${y}" width="1" height="1" fill="#fff080"/>`);
    lights.push({ at: [x, y], r: 10, color: "#ffe080", power: 0.25 });
  }
}
const HERO = [
  "...ggg...",
  "..gGGgg..",
  ".gGggggg.",
  ".gsSSsgg.",
  ".gsksksg.",
  "..sSSSs..",
  ".ggbbbgg.",
  "gGgbbbggg",
  "gGgbbbgg.",
  ".gbbbbbg.",
  "..bb.bb..",
  "..BB.BB..",
];
{
  const x = 226, y = 146;
  const ring = `<ellipse cx="${x + 4}" cy="${y + 13}" rx="10" ry="4" fill="none" stroke="#3a8cff" stroke-width="1"/>`;
  glow.push(ring);
  shadows.push(`<ellipse cx="${x + 3}" cy="${y + 13}" rx="5" ry="2" fill="${sand[1]}"/>`);
  standing.push(ring, pixels(HERO, { g: "#3e7a4a", G: "#6cb06a", s: "#c89878", S: "#e0b890", k: INK, b: "#4a3a30", B: "#2a1e18" }, x, y));
  lights.push({ at: [x + 4, y + 13], r: 18, color: "#3a8cff", power: 0.35 });
}

// ---------------------------------------------------------------- HUD

{
  hud.push(text3x5("TOOLTIP", 5, 5, "#f0e8d8", { outline: INK }));
  const title = "RUINS OF OLD BARAHUT 2/2";
  hud.push(text3x5(title, NW - 5 - textWidth3x5(title), 5, "#f0e8d8", { outline: INK }));
  // round minimap
  hud.push(`<circle cx="446" cy="42" r="24" fill="${INK}" opacity="0.85"/><circle cx="446" cy="42" r="24" fill="none" stroke="#7a8a94" stroke-width="1"/>`);
  hud.push(`<path d="M430 36 L446 30 L456 44 L444 54 L432 48 Z" fill="none" stroke="#5a6a74" stroke-width="1"/>`);
  hud.push(`<rect x="444" y="40" width="3" height="3" fill="#50c8ff"/><rect x="434" y="46" width="2" height="2" fill="#e84040"/><rect x="452" y="34" width="2" height="2" fill="#40e080"/>`);
  // side icons
  for (const y of [110, 130]) hud.push(`<circle cx="10" cy="${y}" r="6" fill="${INK}"/><circle cx="10" cy="${y}" r="5" fill="#2a3a30"/><rect x="9" y="${y - 3}" width="2" height="6" fill="#e0a040"/>`);
  // the portrait in a diamond, bars, skills, a lock, the level
  hud.push(`<path d="M24 222 L42 240 L24 258 L6 240 Z" fill="${INK}"/><path d="M24 225 L39 240 L24 255 L9 240 Z" fill="#3a4a3a"/>`);
  hud.push(pixels(HERO.slice(0, 6), { g: "#3e7a4a", G: "#6cb06a", s: "#c89878", S: "#e0b890", k: INK }, 20, 235));
  hud.push(`<rect x="44" y="228" width="90" height="6" fill="${INK}"/><rect x="45" y="229" width="86" height="4" fill="#48c060"/>`);
  hud.push(text3x5("416/429", 70, 222, "#f0e8d8", { outline: INK }));
  hud.push(`<rect x="44" y="235" width="90" height="4" fill="${INK}"/><rect x="45" y="236" width="70" height="2" fill="#3a8cff"/>`);
  [["#3a6ad8", "#a0c8ff"], ["#d86a2a", "#ffd080"], ["#2a2a34", "#8a8a9a"]].forEach(([a, b], i) => {
    const x = 48 + i * 20;
    hud.push(`<rect x="${x}" y="243" width="17" height="17" fill="${INK}"/><rect x="${x + 1}" y="244" width="15" height="15" fill="${a}"/><rect x="${x + 4}" y="247" width="9" height="9" fill="${b}"/>`);
  });
  hud.push(pixels(["..www..", ".w...w.", ".w...w.", "wwwwwww", "wwwkwww", "wwwkwww", "wwwwwww"], { w: "#b8b8c0", k: INK }, 113, 248));
  hud.push(`<path d="M136 243 L145 252 L136 261 L127 252 Z" fill="${INK}"/><path d="M136 245 L143 252 L136 259 L129 252 Z" fill="#2a4a6a"/>`, text3x5("11", 133, 250, "#ffffff"));
}

// ---------------------------------------------------------------- compose: warm ambient, cyan and blue lights

const frame = rasterFonts(frameSvg(NW, NH, [...ground, ...shadows, ...standing, ...glow, ...hud]));
const glowImg = rasterFonts(frameSvg(NW, NH, glow));
const png = finish(frame, glowImg, {
  up: UP, ambient: "#d2c4ac", lights,
  bloom: { tight: 3, wide: 14, tightGain: 0.8, wideGain: 0.55 }, vignette: 0.5,
});
console.log(`✓ ${writeOut("canyon.png", png)} ${NW * UP}×${NH * UP}, ${lights.length} lights`);
