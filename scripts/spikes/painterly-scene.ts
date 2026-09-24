/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §Looks and §Decision 2.
 *
 * The question: is the renderer this repo already bakes through (resvg) able to produce a frame
 * in the register of the first reference — soft light, watercolour edges, a calligraphic shape
 * with holes in it, a flock, paper — if the grammar could say those things? The helpers below are
 * named for the primitives the plan proposes, so each maps to a line of it:
 *
 *   blob()          `blob`   — a seeded, smooth, closed organic curve (clouds, stones, splats)
 *   brush()         `brush`  — a spine plus a width profile: a calligraphic stroke as a filled shape
 *   evenodd subpaths `path` with `fillRule: "evenodd"` — the holes a brush loop cuts in a wing
 *   scatterAlong()  `repeat.along` — seeded scatter distributed along a curve rather than a box
 *   MATERIAL filters `material` — soft (blur), watercolour (ragged edge + darkened rim + granulation)
 *   mix-blend-mode  `blend` — screen for light, multiply for paper
 *   the last four layers — the app's `look`: paper grain, wash blotches, vignette, letterbox
 *
 * Everything is seeded; two runs write the same bytes, which the script checks.
 *
 *   npx tsx scripts/spikes/painterly-scene.ts   → out/spikes/painterly.png (+ .svg)
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { Resvg } from "@resvg/resvg-js";
import { mulberry32 } from "../../src/prng.js";
import { ROOT } from "../../src/apps.js";

const W = 1280, H = 720, BAR = 48;
type P = [number, number];
const f = (n: number) => (Math.round(n * 10) / 10).toString();

// ---------------------------------------------------------------- curves

/** Catmull-Rom through the points, sampled densely — the spine a `brush` or `along` walks. */
function spline(pts: P[], samples: number, closed = false): P[] {
  const out: P[] = [];
  const n = pts.length;
  const at = (i: number) => (closed ? pts[(i + n) % n] : pts[Math.max(0, Math.min(n - 1, i))]);
  const segs = closed ? n : n - 1;
  for (let s = 0; s < segs; s++) {
    const [p0, p1, p2, p3] = [at(s - 1), at(s), at(s + 1), at(s + 2)];
    const k = Math.ceil(samples / segs);
    for (let j = 0; j < k; j++) {
      const t = j / k, t2 = t * t, t3 = t2 * t;
      const c = (a: number, b: number, c_: number, d: number) =>
        0.5 * (2 * b + (-a + c_) * t + (2 * a - 5 * b + 4 * c_ - d) * t2 + (-a + 3 * b - 3 * c_ + d) * t3);
      out.push([c(p0[0], p1[0], p2[0], p3[0]), c(p0[1], p1[1], p2[1], p3[1])]);
    }
  }
  if (!closed) out.push(pts[n - 1]);
  return out;
}

const d = (pts: P[], close = true) => `M${pts.map(([x, y]) => `${f(x)} ${f(y)}`).join(" L")}${close ? " Z" : ""}`;

/** `blob`: a closed curve round an ellipse, each control point pushed in or out by a seeded amount. */
function blob(cx: number, cy: number, rx: number, ry: number, seed: number, jitter = 0.22, n = 11): string {
  const rng = mulberry32(seed);
  const pts: P[] = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const k = 1 + (rng() - 0.5) * 2 * jitter;
    pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
  }
  return d(spline(pts, n * 8, true));
}

/** `brush`: a spine and a width profile [[t, w], …]; the outline is the spine offset both ways. */
function brush(spine: P[], widths: [number, number][]): P[] {
  const s = spline(spine, 120);
  const w = (t: number) => {
    for (let i = 1; i < widths.length; i++)
      if (t <= widths[i][0]) {
        const [t0, w0] = widths[i - 1], [t1, w1] = widths[i];
        const u = (t - t0) / (t1 - t0 || 1);
        return w0 + (w1 - w0) * (0.5 - 0.5 * Math.cos(Math.PI * u));
      }
    return widths[widths.length - 1][1];
  };
  const left: P[] = [], right: P[] = [];
  s.forEach((p, i) => {
    const a = s[Math.max(0, i - 1)], b = s[Math.min(s.length - 1, i + 1)];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    const [nx, ny] = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
    const half = w(i / (s.length - 1)) / 2;
    left.push([p[0] + nx * half, p[1] + ny * half]);
    right.push([p[0] - nx * half, p[1] - ny * half]);
  });
  return [...left, ...right.reverse()];
}

/** `repeat.along`: `count` marks spread normally about a curve, denser in its middle. */
function scatterAlong(spine: P[], count: number, spread: number, size: [number, number], seed: number, fills: string[]): string {
  const rng = mulberry32(seed);
  const s = spline(spine, 200);
  const gauss = () => (rng() + rng() + rng() - 1.5) / 1.5;
  let out = "";
  for (let i = 0; i < count; i++) {
    const t = Math.min(0.999, Math.max(0, 0.5 + gauss() * 0.55));
    const k = Math.floor(t * (s.length - 1));
    const [x, y] = s[k];
    const taper = 1 - Math.abs(t - 0.5) * 1.2;
    const ox = gauss() * spread * taper, oy = gauss() * spread * taper;
    const sz = size[0] + rng() * (size[1] - size[0]) * taper;
    const rot = Math.round(rng() * 180);
    const fill = fills[Math.floor(rng() * fills.length)];
    out += `<rect x="${f(-sz / 2)}" y="${f(-sz / 3)}" width="${f(sz)}" height="${f(sz * 0.66)}" transform="translate(${f(x + ox)} ${f(y + oy)}) rotate(${rot})" fill="${fill}"/>`;
  }
  return out;
}

// ---------------------------------------------------------------- materials (filters)

const defs = `
<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="9"/></filter>
<filter id="softer" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="22"/></filter>
<filter id="cloud" x="-30%" y="-30%" width="160%" height="160%">
  <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="3" seed="11" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="38" xChannelSelector="R" yChannelSelector="G" result="d"/>
  <feGaussianBlur in="d" stdDeviation="7"/>
</filter>
<filter id="watercolor" x="-10%" y="-10%" width="120%" height="120%">
  <feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="3" seed="5" result="edgeNoise"/>
  <feDisplacementMap in="SourceGraphic" in2="edgeNoise" scale="7" xChannelSelector="R" yChannelSelector="G" result="ragged"/>
  <feMorphology in="ragged" operator="erode" radius="2.5" result="inner"/>
  <feComposite in="ragged" in2="inner" operator="out" result="rimMask"/>
  <feGaussianBlur in="rimMask" stdDeviation="1.2" result="rimSoft"/>
  <feFlood flood-color="#5a1f14" flood-opacity="0.35"/>
  <feComposite in2="rimSoft" operator="in" result="rim"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.6" numOctaves="2" seed="9" result="grain"/>
  <feColorMatrix in="grain" type="matrix" values="0 0 0 0 0.25  0 0 0 0 0.12  0 0 0 0 0.08  0.9 0 0 0 -0.35" result="grainTint"/>
  <feComposite in="grainTint" in2="ragged" operator="in" result="gran"/>
  <feMerge><feMergeNode in="ragged"/><feMergeNode in="gran"/><feMergeNode in="rim"/></feMerge>
</filter>
<filter id="stone" x="-5%" y="-5%" width="110%" height="110%">
  <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="2" seed="21" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="2.5" xChannelSelector="R" yChannelSelector="G" result="r"/>
  <feMorphology in="r" operator="erode" radius="1.5" result="inner"/>
  <feComposite in="r" in2="inner" operator="out" result="rimMask"/>
  <feFlood flood-color="#8c8a80" flood-opacity="0.45"/>
  <feComposite in2="rimMask" operator="in" result="rim"/>
  <feMerge><feMergeNode in="r"/><feMergeNode in="rim"/></feMerge>
</filter>
<filter id="paper" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="3"/>
  <feColorMatrix type="matrix" values="0 0 0 0 0.42  0 0 0 0 0.36  0 0 0 0 0.3  0 0 -1.4 0 0.62"/>
</filter>
<filter id="wash" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.0045" numOctaves="4" seed="8"/>
  <feColorMatrix type="matrix" values="0 0 0 0 0.62  0 0 0 0 0.52  0 0 0 0 0.42  1.3 0 0 0 -0.55"/>
</filter>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ddd4c2"/><stop offset="1" stop-color="#d8cfbb"/></linearGradient>
<linearGradient id="shaft" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fffdf6" stop-opacity="0.95"/><stop offset="0.55" stop-color="#fffaf0" stop-opacity="0.45"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<radialGradient id="warm" cx="0.1" cy="0" r="0.8"><stop offset="0" stop-color="#fff4da" stop-opacity="0.45"/><stop offset="1" stop-color="#fff4da" stop-opacity="0"/></radialGradient>
<radialGradient id="haze" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ff7f9a" stop-opacity="0.85"/><stop offset="0.6" stop-color="#ffa8b8" stop-opacity="0.4"/><stop offset="1" stop-color="#ffc4cc" stop-opacity="0"/></radialGradient>
<radialGradient id="vignette" cx="0.5" cy="0.5" r="0.75"><stop offset="0.55" stop-color="#6b5446" stop-opacity="0"/><stop offset="1" stop-color="#6b5446" stop-opacity="0.28"/></radialGradient>
<linearGradient id="wing" gradientUnits="userSpaceOnUse" x1="590" y1="0" x2="1230" y2="0">
  <stop offset="0" stop-color="#94662c"/><stop offset="0.35" stop-color="#b8662c"/><stop offset="0.7" stop-color="#d4452e"/><stop offset="1" stop-color="#e2596c"/>
</linearGradient>
<linearGradient id="block" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dcdcd3"/><stop offset="1" stop-color="#d2d3cb"/></linearGradient>
<linearGradient id="ledge" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bb938a"/><stop offset="1" stop-color="#a47a73"/></linearGradient>
<linearGradient id="pillar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#e9e8e1"/><stop offset="0.6" stop-color="#dcdbd3"/><stop offset="1" stop-color="#c9c8bf"/></linearGradient>
`;

// ---------------------------------------------------------------- the frame

const layers: string[] = [];
const L = (s: string) => layers.push(s);

// sky and the warm corner the light comes from
L(`<rect width="${W}" height="${H}" fill="url(#sky)"/>`);
L(`<rect width="${W}" height="${H}" fill="url(#warm)" style="mix-blend-mode:screen"/>`);

// high faint clouds
L(`<g filter="url(#softer)" opacity="0.8"><path d="${blob(1010, 110, 320, 60, 41, 0.3)}" fill="#f6f2ea"/><path d="${blob(420, 60, 260, 40, 42, 0.3)}" fill="#f4efe6"/></g>`);

// light shafts: long quads fanned from one point off the top-left corner, screened and blurred
{
  const src: P = [-180, -320];
  let s = "";
  [[37, 30, 150], [44, 18, 90], [52, 40, 210], [60, 14, 70], [67, 26, 130]].forEach(([deg, w0, w1]) => {
    const a = (deg * Math.PI) / 180, len = 1700;
    const ux = Math.cos(a), uy = Math.sin(a), nx = -uy, ny = ux;
    const q: P[] = [
      [src[0] + nx * w0, src[1] + ny * w0], [src[0] + ux * len + nx * w1, src[1] + uy * len + ny * w1],
      [src[0] + ux * len - nx * w1, src[1] + uy * len - ny * w1], [src[0] - nx * w0, src[1] - ny * w0],
    ];
    s += `<path d="${d(q)}" fill="url(#shaft)" transform="rotate(0)"/>`;
  });
  L(`<g filter="url(#soft)" style="mix-blend-mode:screen">${s}</g>`);
}

// the cloud bank the ruin stands in: a shaded underside first, then the lit mass over it
{
  const bank: [number, number, number, number, number][] = [
    [470, 560, 150, 95, 1], [600, 500, 170, 120, 2], [360, 610, 140, 80, 3], [760, 560, 150, 90, 4],
    [1120, 470, 220, 110, 5], [980, 520, 150, 90, 6], [300, 470, 90, 60, 7],
  ];
  L(`<g filter="url(#cloud)" opacity="0.9">${bank.map(([x, y, rx, ry, s]) => `<path d="${blob(x + 10, y + 22, rx, ry * 0.9, s + 100)}" fill="#cfc6b6"/>`).join("")}</g>`);
  L(`<g filter="url(#cloud)">${bank.map(([x, y, rx, ry, s]) => `<path d="${blob(x, y, rx, ry, s)}" fill="#fbf9f4"/>`).join("")}</g>`);
}

// pillars and the base block: flat stone, a hard-edged ruin in a soft world
function pillar(x: number, top: number, w: number, broken: boolean, seed: number): string {
  const rng = mulberry32(seed);
  const base = 510;
  let s = `<rect x="${f(x - w / 2)}" y="${f(top)}" width="${f(w)}" height="${f(base - top)}" fill="url(#pillar)"/>`;
  for (let y = top + 14; y < base - 6; y += 16 + Math.floor(rng() * 14))
    s += `<rect x="${f(x - w / 2 - 2.5)}" y="${f(y)}" width="${f(w + 5)}" height="4" rx="2" fill="#d0cfc6"/>`;
  s += `<ellipse cx="${f(x)}" cy="${f(base - 8)}" rx="${f(w * 0.9)}" ry="6" fill="#cfcec5"/>`;
  if (broken) {
    const cut = 6 + rng() * 10;
    s += `<path d="M${f(x - w / 2 - 1)} ${f(top - 1)} L${f(x + w / 2 + 1)} ${f(top + cut)} L${f(x + w / 2 + 1)} ${f(top - 8)} L${f(x - w / 2 - 1)} ${f(top - 8)} Z" fill="#eee8da"/>`;
  } else {
    s += `<path d="M${f(x - w * 0.7)} ${f(top)} L${f(x)} ${f(top - w * 1.4)} L${f(x + w * 0.7)} ${f(top)} Z" fill="#e4e3db"/>`;
    s += `<circle cx="${f(x)}" cy="${f(top - w * 1.5)}" r="${f(w * 0.35)}" fill="#dddcd4"/>`;
  }
  return s;
}
const backPillars: [number, number, number, boolean][] = [
  [560, 380, 14, true], [640, 330, 16, false], [720, 300, 18, true], [820, 350, 14, false], [930, 285, 20, false],
  [1030, 360, 14, true], [1110, 300, 18, false], [1200, 340, 16, true], [1255, 390, 12, false],
];
L(`<g filter="url(#stone)">${backPillars.map(([x, t, w, b], i) => pillar(x, t, w, b, i + 1)).join("")}</g>`);

// the wing: one brush for the body, loops of brush over it cut out by even-odd, a bird's head at the root
{
  const body = brush(
    [[596, 404], [680, 396], [790, 372], [900, 318], [1010, 262], [1120, 222], [1236, 196]],
    [[0, 10], [0.06, 50], [0.22, 118], [0.45, 124], [0.7, 84], [0.9, 46], [1, 6]],
  );
  const sweep = brush(
    [[700, 360], [800, 300], [920, 236], [1040, 190], [1150, 168], [1250, 162]],
    [[0, 4], [0.2, 46], [0.5, 60], [0.8, 34], [1, 3]],
  );
  // feathers standing off the leading edge, each its own tapered stroke
  const feathers: P[][] = [];
  for (const [x, y, len, deg] of [[760, 330, 70, -70], [850, 280, 90, -62], [950, 230, 96, -55], [1050, 190, 80, -40], [1140, 168, 70, -28]]) {
    const a = (deg * Math.PI) / 180;
    feathers.push(brush([[x, y], [x + Math.cos(a) * len * 0.5 + 8, y + Math.sin(a) * len * 0.5], [x + Math.cos(a) * len + 22, y + Math.sin(a) * len]], [[0, 26], [0.6, 12], [1, 0.5]]));
  }
  const loop = (cx: number, cy: number, r: number, w: number, turn: number): P[] => {
    const sp: P[] = [];
    for (let i = 0; i <= 10; i++) {
      const a = turn + (i / 10) * Math.PI * 1.7;
      const rr = r * (0.55 + 0.45 * (i / 10));
      sp.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr * 0.72]);
    }
    return brush(sp, [[0, 2], [0.4, w], [1, 3]]);
  };
  const holes = [
    loop(760, 380, 42, 14, 0.4), loop(880, 318, 54, 16, 2.1), loop(1010, 262, 50, 13, 4.0), loop(1130, 228, 36, 10, 1.2),
    brush([[690, 420], [760, 432], [860, 418]], [[0, 1], [0.5, 9], [1, 1]]),
    brush([[930, 356], [1010, 330], [1100, 296]], [[0, 1], [0.5, 8], [1, 1]]),
  ];
  const drops = [blob(830, 400, 13, 7, 61, 0.15, 7), blob(975, 312, 9, 6, 62, 0.15, 7), blob(1070, 290, 12, 5, 63, 0.15, 7)];
  const head = brush([[560, 402], [578, 396], [600, 400]], [[0, 0.5], [0.4, 12], [1, 20]]);
  const wingPath = [d(body), ...holes.map((h) => d(h)), ...drops, d(head)].join(" ");
  const upper = `<path d="${d(sweep)}"/>` + feathers.map((q) => `<path d="${d(q)}"/>`).join("");
  // streaks off the tip, and loose flakes
  let streaks = "";
  [[[1150, 205], [1210, 170], [1280, 150]], [[1140, 236], [1220, 232], [1280, 226]], [[1100, 250], [1180, 268], [1270, 292]],
    [[1180, 196], [1230, 150], [1270, 110]]].forEach((sp) => (streaks += `<path d="${d(brush(sp as P[], [[0, 10], [0.5, 6], [1, 0.5]]))}"/>`));
  const rng = mulberry32(77);
  let flakes = "";
  for (let i = 0; i < 16; i++) {
    const x = 1060 + rng() * 220, y = 120 + rng() * 260, r = 3 + rng() * 7, a = Math.round(rng() * 180);
    flakes += `<path d="${d(brush([[-r, 0], [0, -r * 0.2], [r, 0]], [[0, 0.5], [0.5, r * 0.7], [1, 0.5]]))}" transform="translate(${f(x)} ${f(y)}) rotate(${a})"/>`;
  }
  L(`<g filter="url(#watercolor)" fill="url(#wing)">${upper}<path fill-rule="evenodd" d="${wingPath}"/>${streaks}${flakes}</g>`);
  L(`<circle cx="572" cy="398" r="2.2" fill="#3a2016"/>`);
}

// the base block, in front of the wing's root: courses, the arch, the two dials
{
  let s = `<rect x="500" y="505" width="800" height="230" fill="url(#block)"/>`;
  s += `<rect x="492" y="498" width="816" height="16" fill="#e2e1d9"/>`;
  for (const y of [548, 596, 640]) s += `<rect x="500" y="${y}" width="800" height="2.5" fill="#c4c3ba"/>`;
  for (const x of [590, 700, 1090, 1210]) s += `<rect x="${x}" y="514" width="2.5" height="160" fill="#c8c7be"/>`;
  s += `<circle cx="900" cy="700" r="92" fill="#cbccc3"/><circle cx="900" cy="700" r="70" fill="#e4e2d8"/><circle cx="900" cy="700" r="46" fill="#f7f1e6"/>`;
  s += `<circle cx="640" cy="610" r="24" fill="#d8d6cd"/><path d="M640 586 A24 24 0 1 1 616 610 L628 610 A12 12 0 1 0 640 598 Z" fill="#b8854a"/>`;
  s += `<circle cx="1160" cy="610" r="24" fill="#d8d6cd"/><path d="M1160 586 A24 24 0 1 1 1136 610 L1148 610 A12 12 0 1 0 1160 598 Z" fill="#e0707e"/>`;
  L(`<g filter="url(#stone)">${s}</g>`);
}

// cloud wrapping the foot of the ruin, in front of it: the block stands *in* the weather
{
  const front: [number, number, number, number, number][] = [[520, 690, 150, 70, 201], [700, 710, 130, 50, 202], [1250, 560, 110, 90, 203]];
  L(`<g filter="url(#cloud)" opacity="0.85">${front.map(([x, y, rx, ry, s]) => `<path d="${blob(x, y, rx, ry, s)}" fill="#faf7f1"/>`).join("")}</g>`);
}

// two pillars stand in front of the wing, so it sits among the ruin rather than on it
L(`<g filter="url(#stone)">${pillar(990, 330, 16, false, 31)}${pillar(1170, 360, 12, true, 32)}</g>`);

// the flock
L(scatterAlong([[70, 470], [110, 300], [200, 190], [340, 170], [430, 230]], 320, 34, [1.4, 4.2], 13, ["#3b2e29", "#4a3a33", "#6d5244", "#2f2622"]));
// three red birds
for (const [x, y, s] of [[168, 118, 1], [150, 560, 0.8], [52, 452, 0.7]] as [number, number, number][])
  L(`<path d="M${x - 8 * s} ${y - 3 * s} Q${x - 3 * s} ${y - 1 * s} ${x} ${y + 3 * s} Q${x + 3 * s} ${y - 2 * s} ${x + 9 * s} ${y - 5 * s} Q${x + 3 * s} ${y + 1 * s} ${x} ${y + 6 * s} Q${x - 2 * s} ${y + 1 * s} ${x - 8 * s} ${y - 3 * s} Z" fill="#d23b3b"/>`);

// the ledge and the one small figure on it
L(`<g filter="url(#stone)"><rect x="30" y="646" width="310" height="80" fill="url(#ledge)"/><rect x="30" y="640" width="310" height="9" fill="#c9a49b"/></g>`);
L(`<g filter="url(#watercolor)"><path d="${blob(206, 622, 15, 13, 91, 0.2, 9)}" fill="#5a3d52"/><path d="${d(brush([[200, 612], [214, 606], [232, 614], [244, 626]], [[0, 12], [0.5, 9], [1, 1]]))}" fill="#7d5a7d"/><circle cx="198" cy="612" r="5" fill="#e8d8cc"/></g>`);

// the pink haze the right side stands in
L(`<ellipse cx="1190" cy="610" rx="420" ry="300" fill="url(#haze)" style="mix-blend-mode:screen"/>`);
L(`<circle cx="1160" cy="610" r="60" fill="url(#haze)" style="mix-blend-mode:screen"/>`);

// look: paper, wash, vignette, letterbox
L(`<rect width="${W}" height="${H}" filter="url(#wash)" opacity="0.5" style="mix-blend-mode:multiply"/>`);
L(`<rect width="${W}" height="${H}" filter="url(#paper)" opacity="0.55" style="mix-blend-mode:multiply"/>`);
L(`<rect width="${W}" height="${H}" fill="url(#vignette)" style="mix-blend-mode:multiply"/>`);
L(`<rect width="${W}" height="${BAR}" fill="#000"/><rect y="${H - BAR}" width="${W}" height="${BAR}" fill="#000"/>`);

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><defs>${defs}</defs>\n${layers.join("\n")}\n</svg>`;

const outDir = `${ROOT}out/spikes`;
mkdirSync(outDir, { recursive: true });
writeFileSync(`${outDir}/painterly.svg`, svg);
const t0 = performance.now();
const png = new Resvg(svg).render().asPng();
const ms = performance.now() - t0;
const again = new Resvg(svg).render().asPng();
writeFileSync(`${outDir}/painterly.png`, png);
console.log(
  `✓ painterly.png ${W}×${H}: ${(svg.length / 1024).toFixed(0)}KB of SVG, rendered in ${ms.toFixed(0)}ms, ` +
    `${Buffer.compare(Buffer.from(png), Buffer.from(again)) === 0 ? "byte-identical on a second render" : "NOT DETERMINISTIC"}`,
);
