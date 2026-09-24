/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §More references.
 *
 * Reference F: a mobile action game's practice dungeon — a painted blue-violet forest at full
 * resolution, a tree of lightning, a crimson canopy, bioluminescent grass, a heroine with a sword too
 * big for her, a pixel-art slime, orange damage numbers and a Korean HUD. What it adds:
 *
 *   depth → blur     depth now does a fourth job: far layers are blurred (depth of field), which is
 *                    most of what makes a painted background read as painted
 *   bolt()           lightning as seeded midpoint displacement, drawn as three strokes of one path
 *   mixed resolution the slime is drawn at 72×54 on a hard grid and scaled ×4 into a 1280×720
 *                    painted frame — pixel sprite over painted ground, which is what the reference is
 *   vector text      Hangul and numbers from font FILES named explicitly, system fonts off; a text
 *                    part whose font is not loaded renders nothing and says nothing, so the plan's
 *                    text primitive must fail when its font is missing
 *
 *   npx tsx scripts/spikes/mystic-scene.ts   → out/spikes/mystic.png (1280×720)
 */
import { existsSync } from "node:fs";
import { mulberry32 } from "../../src/prng.js";
import { atDepth, blend, blob, bolt, branchTree, brush, d, f, finish, frameSvg, mixOk, over, rampHex, rasterFonts, scaleNearest, writeOut, type P } from "./kit.js";
import type { Img } from "./pixel.js";

const W = 1280, H = 720, FLOOR = 520;
const FONTS = ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"];
for (const file of FONTS) if (!existsSync(file)) throw new Error(`font ${file} is missing — a text part without its font renders nothing, so this refuses to`);

const HAZE = "#6f95e6", NIGHT = "#141c44";
const crimson = rampHex("#8e2c68"), teal = rampHex("#2e6a8a"), rock = rampHex("#2a3450");
const layers: string[] = [], glow: string[] = [];
const L = (s: string) => layers.push(s);

const defs = `
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${NIGHT}"/><stop offset="0.45" stop-color="#2c4494"/><stop offset="0.75" stop-color="#5a82d8"/><stop offset="1" stop-color="#3a5aa8"/></linearGradient>
<radialGradient id="shine" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#b8d4ff" stop-opacity="0.8"/><stop offset="1" stop-color="#b8d4ff" stop-opacity="0"/></radialGradient>
<filter id="dof1" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="5"/></filter>
<filter id="dof2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2"/></filter>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="7"/></filter>
<filter id="haze" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>
<filter id="leafy" x="-10%" y="-10%" width="120%" height="120%">
  <feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves="2" seed="4" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="14" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<radialGradient id="skin" cx="0.4" cy="0.35" r="0.6"><stop offset="0" stop-color="#ffe6da"/><stop offset="1" stop-color="#f0b8a8"/></radialGradient>
<linearGradient id="blade" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb0c0"/><stop offset="0.5" stop-color="#d83a5a"/><stop offset="1" stop-color="#7a1030"/></linearGradient>
<linearGradient id="dmg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd070"/><stop offset="1" stop-color="#ff5a2a"/></linearGradient>
`;

// ---------------------------------------------------------------- sky, light behind the trees, three depths of wood

L(`<rect width="${W}" height="${H}" fill="url(#sky)"/>`);
L(`<ellipse cx="760" cy="330" rx="420" ry="260" fill="url(#shine)"/><ellipse cx="200" cy="260" rx="260" ry="200" fill="url(#shine)" opacity="0.6"/>`);

/** A wood at a depth: trunks and leafy crowns, coloured toward the haze AND blurred by the same number. */
function wood(depth: number, seed: number, n: number, base: string, crown: string, blurId: string, yTop: number): string {
  const rng = mulberry32(seed);
  const tc = atDepth(base, HAZE, depth), cc = atDepth(crown, HAZE, depth);
  let s = "";
  for (let i = 0; i < n; i++) {
    const x = (i + rng() * 0.8) * (W / n), w = 14 + rng() * 26 * (1 - depth), top = yTop + rng() * 80;
    s += `<path d="${d(brush([[x, FLOOR + 20], [x + (rng() - 0.5) * 30, (FLOOR + top) / 2], [x + (rng() - 0.5) * 40, top]], [[0, w * 1.4], [1, w * 0.6]]))}" fill="${tc}"/>`;
    for (let k = 0; k < 3; k++) s += `<path d="${blob(x + (rng() - 0.5) * 120, top - rng() * 60, 70 + rng() * 60, 40 + rng() * 30, seed * 50 + i * 3 + k, 0.35)}" fill="${cc}"/>`;
  }
  return `<g filter="url(#${blurId})"><g filter="url(#leafy)">${s}</g></g>`;
}
L(wood(0.85, 1, 7, "#223070", "#2a3c88", "dof1", 60));
L(wood(0.55, 2, 6, "#1a2458", "#243a7a", "dof2", 90));

// right edge: tall near trunks hung with strands of light
{
  const rng = mulberry32(8);
  for (const [x, w] of [[1150, 70], [1250, 90]] as [number, number][]) {
    L(`<path d="${d(brush([[x, H], [x - 10, 300], [x + 14, 0]], [[0, w * 1.2], [1, w]]))}" fill="${mixOk(NIGHT, "#1e2e66", 0.6)}"/>`);
    for (let s = 0; s < 5; s++) {
      const sx = x - w / 2 + rng() * w, sy = 40 + rng() * 200, len = 80 + rng() * 160;
      let strand = "";
      for (let k = 0; k < len; k += 9) strand += `<circle cx="${f(sx + Math.sin(k * 0.05) * 4)}" cy="${f(sy + k)}" r="${f(1.4 + rng() * 1.6)}" fill="#bfe6ff"/>`;
      glow.push(strand);
      L(strand);
    }
  }
}

// ---------------------------------------------------------------- the crimson tree

{
  const x = 660, top = 150;
  L(`<path d="${d(brush([[x - 10, FLOOR + 10], [x + 10, 380], [x - 6, 280], [x + 4, top + 60]], [[0, 44], [1, 16]]))}" fill="${mixOk(crimson[0], NIGHT, 0.5)}"/>`);
  for (const b of branchTree({ at: [x + 4, top + 80], angle: -Math.PI / 2, len: 70, width: 14, depth: 3, seed: 12, twist: 0.5, spread: 0.9 }))
    L(`<path d="${d(b.pts)}" fill="${mixOk(crimson[0], NIGHT, 0.5)}"/>`);
  const rng = mulberry32(13);
  let crown = "";
  for (const [tone, n, rMin, rMax, lift] of [[0, 9, 60, 90, 0], [1, 10, 40, 70, -12], [2, 9, 26, 46, -26], [3, 6, 14, 26, -38]] as [number, number, number, number, number][])
    for (let i = 0; i < n; i++) {
      const a = rng() * Math.PI * 2, k = Math.sqrt(rng()) * 130;
      crown += `<path d="${blob(x + Math.cos(a) * k * 1.25 + (tone * 6), top + 40 + Math.sin(a) * k * 0.6 + lift, rMin + rng() * (rMax - rMin), (rMin + rng() * (rMax - rMin)) * 0.7, 200 + tone * 20 + i, 0.3)}" fill="${crimson[tone]}"/>`;
    }
  L(`<g filter="url(#dof2)"><g filter="url(#leafy)">${crown}</g></g>`);
}

// ---------------------------------------------------------------- the lightning tree

{
  const base: P = [210, FLOOR - 10];
  let strokes = "";
  const tips: P[] = [[90, 70], [200, 40], [320, 90], [60, 190], [380, 200], [140, 120]];
  tips.forEach((tip, i) => {
    for (const ch of bolt(base, tip, 300 + i, { jag: 0.16, forks: 2, depth: 6 })) {
      const w = [7, 3.5, 2][ch.gen];
      const p = d(ch.pts, false);
      strokes += `<path d="${p}" fill="none" stroke="#9a6aff" stroke-width="${w * 2.2}" stroke-opacity="0.35"/>`;
      strokes += `<path d="${p}" fill="none" stroke="#d8c8ff" stroke-width="${w}"/>`;
      strokes += `<path d="${p}" fill="none" stroke="#ffffff" stroke-width="${Math.max(0.8, w * 0.35)}"/>`;
    }
  });
  const g = `<g stroke-linecap="round" stroke-linejoin="round">${strokes}</g>`;
  L(g);
  glow.push(g);
}

// ---------------------------------------------------------------- the floor: blue grass, rocks, glowing caps

{
  L(`<rect y="${FLOOR - 20}" width="${W}" height="${H - FLOOR + 20}" fill="${mixOk(teal[0], NIGHT, 0.4)}"/>`);
  const rng = mulberry32(21);
  let rocks = "";
  for (const [x, y, rx, ry] of [[80, 640, 90, 50], [470, 690, 110, 45], [980, 660, 120, 55], [1210, 610, 80, 60], [330, 560, 50, 26]])
    rocks += `<path d="${blob(x, y, rx, ry, x, 0.2)}" fill="${rock[1]}"/><path d="${blob(x - rx * 0.15, y - ry * 0.35, rx * 0.7, ry * 0.4, x + 1, 0.2)}" fill="${rock[3]}"/>`;
  L(rocks);
  // grass: a few thousand blades, each a tapered stroke, darker and denser toward the camera
  let grass = "";
  for (let i = 0; i < 2600; i++) {
    const y = FLOOR - 16 + Math.pow(rng(), 0.7) * (H - FLOOR + 30), x = rng() * W;
    const near = (y - FLOOR) / (H - FLOOR), h = 14 + near * 34 + rng() * 14, lean = (rng() - 0.5) * 18;
    const tone = teal[Math.min(4, Math.floor(rng() * 3) + (near < 0.3 ? 2 : 0))];
    grass += `<path d="${d(brush([[x, y], [x + lean * 0.4, y - h * 0.55], [x + lean, y - h]], [[0, 3 + near * 3], [1, 0.3]]))}" fill="${tone}"/>`;
  }
  L(grass);
  // bioluminescence: caps and spores, all emissive
  let spores = "";
  for (let i = 0; i < 90; i++) {
    const x = rng() * W, y = FLOOR - 40 + rng() * (H - FLOOR + 40), r = 1 + rng() * 2.6;
    spores += `<circle cx="${f(x)}" cy="${f(y)}" r="${f(r)}" fill="${rng() < 0.7 ? "#a8f4ff" : "#e8ffff"}"/>`;
  }
  for (let i = 0; i < 40; i++) spores += `<circle cx="${f(rng() * W)}" cy="${f(80 + rng() * 420)}" r="${f(0.8 + rng() * 1.4)}" fill="#cfe8ff"/>`;
  L(spores);
  glow.push(spores);
}

// ---------------------------------------------------------------- the heroine

{
  const x = 380, y = 560;
  L(`<ellipse cx="${x}" cy="${y + 8}" rx="60" ry="14" fill="#0a1030" opacity="0.55" filter="url(#haze)"/>`);
  // the sword first: raised behind her, up and to the left
  L(`<path d="${d(brush([[x - 20, y - 150], [x - 90, y - 230], [x - 150, y - 280], [x - 190, y - 300]], [[0, 22], [0.4, 30], [0.85, 22], [1, 2]]))}" fill="url(#blade)"/>`);
  L(`<path d="${d(brush([[x - 24, y - 156], [x - 90, y - 236], [x - 150, y - 284]], [[0, 3], [1, 1]]))}" fill="#ffe0e8"/>`);
  L(`<path d="${d(brush([[x - 8, y - 140], [x - 30, y - 162]], [[0, 12], [1, 12]]))}" fill="#e8c060"/><path d="${d(brush([[x - 40, y - 150], [x - 2, y - 176]], [[0, 7], [1, 7]]))}" fill="#c89838"/>`);
  // legs, skirt, body, arms
  for (const [hx, fx] of [[-10, -34], [10, 28]]) {
    L(`<path d="${d(brush([[x + hx, y - 100], [x + (hx + fx) / 2, y - 50], [x + fx, y - 4]], [[0, 16], [1, 11]]))}" fill="#fff4f6"/>`);
    L(`<path d="${blob(x + fx + 4, y - 2, 13, 7, x + fx, 0.1)}" fill="#e05a8a"/>`);
  }
  L(`<path d="${d([[x - 30, y - 104], [x + 30, y - 104], [x + 44, y - 72], [x - 44, y - 72]])}" fill="#ff8ab8"/><path d="${d([[x - 44, y - 72], [x + 44, y - 72], [x + 40, y - 66], [x - 40, y - 66]])}" fill="#ffffff"/>`);
  L(`<path d="${d(brush([[x, y - 104], [x - 2, y - 150]], [[0, 38], [1, 30]]))}" fill="#ffd8e8"/><path d="${d(brush([[x - 14, y - 146], [x + 14, y - 146]], [[0, 6], [1, 6]]))}" fill="#ff6aa0"/>`);
  L(`<path d="${d(brush([[x - 14, y - 144], [x - 22, y - 156], [x - 20, y - 166]], [[0, 10], [1, 8]]))}" fill="url(#skin)"/>`);
  L(`<path d="${d(brush([[x + 14, y - 144], [x + 34, y - 130], [x + 48, y - 118]], [[0, 10], [1, 8]]))}" fill="url(#skin)"/>`);
  // head, hair, ears
  const hx = x - 4, hy = y - 182;
  L(`<path d="${d(brush([[hx - 10, hy - 4], [hx - 42, hy + 30], [hx - 50, hy + 80], [hx - 40, hy + 110]], [[0, 20], [0.5, 22], [1, 4]]))}" fill="#e83a78"/>`);
  L(`<path d="${d(brush([[hx + 12, hy - 4], [hx + 40, hy + 26], [hx + 46, hy + 70], [hx + 38, hy + 100]], [[0, 18], [0.5, 20], [1, 4]]))}" fill="#e83a78"/>`);
  L(`<circle cx="${hx}" cy="${hy}" r="24" fill="url(#skin)"/>`);
  L(`<path d="${d(brush([[hx - 26, hy - 2], [hx - 10, hy - 26], [hx + 14, hy - 24], [hx + 28, hy - 2]], [[0, 10], [0.5, 22], [1, 10]]))}" fill="#ff5a92"/>`);
  for (const [ex, lean] of [[-10, -12], [12, 10]]) {
    L(`<path d="${d(brush([[hx + ex, hy - 30], [hx + ex + lean * 0.6, hy - 60], [hx + ex + lean, hy - 84]], [[0, 12], [0.5, 14], [1, 3]]))}" fill="#fff6fa"/>`);
    L(`<path d="${d(brush([[hx + ex, hy - 36], [hx + ex + lean * 0.6, hy - 60], [hx + ex + lean, hy - 78]], [[0, 5], [0.5, 6], [1, 1]]))}" fill="#ffb0cc"/>`);
  }
  L(`<ellipse cx="${hx - 8}" cy="${hy + 4}" rx="3" ry="4" fill="#4a1a3a"/><ellipse cx="${hx + 8}" cy="${hy + 4}" rx="3" ry="4" fill="#4a1a3a"/>`);
  // her little hp bar
  L(`<rect x="${x - 40}" y="${y - 300}" width="80" height="6" fill="#0a1030"/><rect x="${x - 39}" y="${y - 299}" width="78" height="4" fill="#40e060"/>`);
}

// ---------------------------------------------------------------- the slime: pixel art at 72×54, placed at ×4

function slimeSprite(): Img {
  const sw = 72, sh = 54;
  const body = [[4, 52], [2, 40], [8, 26], [20, 16], [32, 12], [44, 13], [56, 18], [66, 30], [70, 42], [68, 52]] as P[];
  const s = [
    `<path d="${d(body)}" fill="#2a70d8"/>`,
    `<path d="${d(body.map(([x, y]) => [x * 0.9 + 3, y * 0.86 + 2] as P))}" fill="#3e92f0"/>`,
    `<path d="${d(body.map(([x, y]) => [x * 0.7 + 6, y * 0.66 + 4] as P))}" fill="#5cb2ff"/>`,
    `<path d="${d(brush([[34, 14], [38, 6], [44, 3], [48, 6], [44, 9]], [[0, 6], [1, 2]]))}" fill="#5cb2ff"/>`,
    `<path d="${d(brush([[36, 12], [40, 6], [44, 5]], [[0, 2], [1, 1]]))}" fill="#bfe6ff"/>`,
    `<rect x="16" y="20" width="7" height="3" fill="#e0f4ff"/><rect x="14" y="23" width="3" height="4" fill="#e0f4ff"/>`,
    `<path d="M24 34 Q27 31 30 34" fill="none" stroke="#123a80" stroke-width="1.5"/><path d="M42 34 Q45 31 48 34" fill="none" stroke="#123a80" stroke-width="1.5"/>`,
    `<path d="M32 40 Q36 44 40 40" fill="none" stroke="#123a80" stroke-width="1.5"/>`,
    `<path d="${d(body)}" fill="none" stroke="#123a80" stroke-width="1.2"/>`,
  ];
  return rasterFonts(frameSvg(sw, sh, s, true));
}

// ---------------------------------------------------------------- text and HUD

const hud: string[] = [];
const T = (x: number, y: number, size: number, fill: string, text: string, stroke = "#1a0a18", sw = 5, anchor = "start") =>
  `<text x="${x}" y="${y}" font-family="WenQuanYi Zen Hei" font-size="${size}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" paint-order="stroke" stroke-linejoin="round" text-anchor="${anchor}">${text}</text>`;
const N = (x: number, y: number, size: number, text: string) =>
  `<text x="${x}" y="${y}" font-family="DejaVu Sans" font-weight="bold" font-size="${size}" fill="url(#dmg)" stroke="#5a1408" stroke-width="${size / 7}" paint-order="stroke" stroke-linejoin="round" text-anchor="middle" transform="skewX(-8)">${text}</text>`;
hud.push(T(40, 58, 30, "#ffffff", "연습 던전"));
hud.push(N(700, 70, 58, "4,368"), N(940, 205, 50, "1092"));
hud.push(`<path d="M1040 22 L1070 22 L1060 42 L1070 62 L1040 62 L1050 42 Z" fill="#f0a030" stroke="#5a2a08" stroke-width="3"/>`);
hud.push(T(1182, 40, 22, "#ffffff", "남은 시간", "#1a0a18", 5, "end"), T(1182, 70, 24, "#ffffff", "00 : 24 초", "#1a0a18", 5, "end"));
hud.push(`<rect x="1196" y="14" width="68" height="68" rx="6" fill="#1e1a24" stroke="#000" stroke-width="3"/><path d="M1216 40 A18 18 0 1 1 1222 64" fill="none" stroke="#f0c020" stroke-width="8"/><path d="M1206 40 L1216 26 L1226 40 Z" fill="#f0c020"/>`);
[["#ff7ab0", "11"], ["#ff6a2a", "11"], ["#ffa040", "8"], ["#ff4a8a", "4"]].forEach(([c, lv], i) => {
  const x = 22 + i * 98, y = 598;
  hud.push(`<rect x="${x}" y="${y}" width="90" height="90" rx="4" fill="#20121a" stroke="#000" stroke-width="3"/>`);
  hud.push(`<g filter="url(#haze)"><circle cx="${x + 45}" cy="${y + 48}" r="30" fill="${c}"/></g><circle cx="${x + 45}" cy="${y + 48}" r="14" fill="#fff4e0"/>`);
  hud.push(T(x + 6, y + 24, 20, "#ffffff", lv, "#000", 4));
});
hud.push(`<rect x="22" y="694" width="386" height="12" fill="#0a0a14"/><rect x="24" y="696" width="300" height="8" fill="#40c0e0"/>`);

// ---------------------------------------------------------------- compose

const frame = rasterFonts(frameSvg(W, H, layers, false, defs), 1, FONTS);
const slime = slimeSprite();
const big = scaleNearest(slime, 4);
// its shadow on the painted ground, then the sprite, then the HUD over everything
blend(frame, rasterFonts(frameSvg(W, H, [`<ellipse cx="900" cy="${FLOOR + 132}" rx="130" ry="20" fill="#08102a" opacity="0.6" filter="url(#haze)"/>`], false, defs)), 0, 0);
over(frame, big, 900 - big.w / 2, FLOOR + 140 - big.h);
blend(frame, rasterFonts(frameSvg(W, H, hud, false, defs), 1, FONTS), 0, 0);
const glowImg = rasterFonts(frameSvg(W, H, glow, false, defs));
const png = finish(frame, glowImg, { up: 1, bloom: { tight: 4, wide: 18, tightGain: 0.7, wideGain: 0.6 }, vignette: 0.35 });
console.log(`✓ ${writeOut("mystic.png", png)} ${W}×${H}; slime ${slime.w}×${slime.h} → ×4`);
