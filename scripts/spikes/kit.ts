/**
 * SPIKE — not system code. The pieces the scene spikes share, each named for the primitive
 * docs/graphics-capability-plan.md proposes, so a scene reads as the documents it would be:
 *
 *   curves       spline · brush · blob · scatterAlong                 (`smooth`, `brush`, `blob`, `repeat.along`)
 *   generators   branchTree · bolt · clump                            (seeded growth: trees, lightning, foliage)
 *   pixels       pixels · text3x5                                     (the `pixels` primitive, and a bitmap font made of it)
 *   colour       hex · rampHex · mixOk · atDepth                      (OKLCH ramps, fog as a hue)
 *   frames       frameSvg · rasterFonts · over · finish               (native frame → upscale → light → bloom → vignette)
 *
 * Everything is seeded; nothing reads the clock or the system's fonts.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { Resvg } from "@resvg/resvg-js";
import { PNG } from "pngjs";
import { mulberry32 } from "../../src/prng.js";
import { ROOT } from "../../src/apps.js";
import { fromOklab, hexRgb, hueShiftedRamp, oklab, type Img, type RGB } from "./pixel.js";

export type P = [number, number];
export const f = (n: number) => (Math.round(n * 10) / 10).toString();

// ---------------------------------------------------------------- curves

/** Catmull-Rom through the points, sampled densely — the spine a `brush` or `along` walks. */
export function spline(pts: P[], samples: number, closed = false): P[] {
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

export const d = (pts: P[], close = true) => `M${pts.map(([x, y]) => `${f(x)} ${f(y)}`).join(" L")}${close ? " Z" : ""}`;

/** `blob`: a closed curve round an ellipse, each control point pushed in or out by a seeded amount. */
export function blob(cx: number, cy: number, rx: number, ry: number, seed: number, jitter = 0.22, n = 11): string {
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
export function brush(spine: P[], widths: [number, number][]): P[] {
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
export function scatterAlong(spine: P[], count: number, spread: number, size: [number, number], seed: number, fills: string[]): string {
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

// ---------------------------------------------------------------- generators

export interface Branch { pts: P[]; depth: number; tip: P }

/**
 * A seeded branching tree: each limb a wandering brush that tapers into two or three children.
 * `twist` is how far a limb wanders off its heading — near 0 a clean sapling, near 1 the knotted
 * dead wood of a desert. Returns outlines trunk-first, so drawing them in order layers correctly.
 */
export function branchTree(o: {
  at: P; angle: number; len: number; width: number; depth: number; seed: number;
  twist?: number; spread?: number; shrink?: number; kids?: [number, number];
}): Branch[] {
  const rng = mulberry32(o.seed);
  const twist = o.twist ?? 0.4, spread = o.spread ?? 0.6, shrink = o.shrink ?? 0.72;
  const [kMin, kMax] = o.kids ?? [2, 3];
  const out: Branch[] = [];
  const grow = (at: P, angle: number, len: number, width: number, depth: number) => {
    const steps = 4;
    const spine: P[] = [at];
    let a = angle, [x, y] = at;
    for (let i = 0; i < steps; i++) {
      a += (rng() - 0.5) * twist;
      x += (Math.cos(a) * len) / steps;
      y += (Math.sin(a) * len) / steps;
      spine.push([x, y]);
    }
    out.push({ pts: brush(spine, [[0, width], [1, Math.max(0.6, width * shrink * 0.8)]]), depth, tip: [x, y] });
    if (depth <= 0) return;
    const n = kMin + Math.floor(rng() * (kMax - kMin + 1));
    for (let k = 0; k < n; k++) {
      const side = n === 1 ? 0 : (k / (n - 1) - 0.5) * 2;
      grow([x, y], a + side * spread + (rng() - 0.5) * spread * 0.5, len * (shrink + (rng() - 0.5) * 0.15), width * shrink, depth - 1);
    }
  };
  grow(o.at, o.angle, o.len, o.width, o.depth);
  return out;
}

/**
 * Lightning: midpoint displacement between two points, forking as it goes. Returns polylines,
 * the main channel first; each carries the generation it forked at, so it can thin with it.
 */
export function bolt(from: P, to: P, seed: number, o: { jag?: number; forks?: number; depth?: number } = {}): { pts: P[]; gen: number }[] {
  const rng = mulberry32(seed);
  const jag = o.jag ?? 0.22, depth = o.depth ?? 6;
  const out: { pts: P[]; gen: number }[] = [];
  const channel = (a: P, b: P, gen: number) => {
    let pts: P[] = [a, b];
    let amp = Math.hypot(b[0] - a[0], b[1] - a[1]) * jag;
    for (let k = 0; k < depth; k++) {
      const next: P[] = [pts[0]];
      for (let i = 1; i < pts.length; i++) {
        const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
        const len = Math.hypot(x1 - x0, y1 - y0) || 1;
        const off = (rng() - 0.5) * amp;
        next.push([(x0 + x1) / 2 + (-(y1 - y0) / len) * off, (y0 + y1) / 2 + ((x1 - x0) / len) * off], pts[i]);
      }
      pts = next;
      amp *= 0.55;
    }
    out.push({ pts, gen });
    if (gen >= 2) return;
    const forks = gen === 0 ? (o.forks ?? 3) : 1;
    for (let k = 0; k < forks; k++) {
      const i = 2 + Math.floor(rng() * (pts.length * 0.7));
      const [sx, sy] = pts[Math.min(i, pts.length - 1)];
      const dir = Math.atan2(b[1] - a[1], b[0] - a[0]) + (rng() - 0.5) * 1.6;
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]) * (0.25 + rng() * 0.3) / (gen + 1);
      channel([sx, sy], [sx + Math.cos(dir) * len, sy + Math.sin(dir) * len], gen + 1);
    }
  };
  channel(from, to, 0);
  return out;
}

/**
 * Pixel foliage: a clump of leaf-balls shaded as one mass. A dark base, a mid layer shifted
 * toward the light, a lit cap, then single-pixel leaf flecks — the cluster shading a pixel
 * artist does by hand, driven by one ramp and a light direction.
 */
export function clump(cx: number, cy: number, r: number, seed: number, ramp: string[], light: P = [-0.6, -0.8]): string {
  const rng = mulberry32(seed);
  const balls: [number, number, number][] = [];
  const n = Math.max(3, Math.round(r / 3.2));
  for (let i = 0; i < n; i++) {
    const a = rng() * Math.PI * 2, k = Math.sqrt(rng()) * r * 0.62;
    balls.push([cx + Math.cos(a) * k, cy + Math.sin(a) * k * 0.8, r * (0.32 + rng() * 0.22)]);
  }
  const layer = (dx: number, dy: number, shrink: number, fill: string) =>
    balls.map(([x, y, br]) => `<circle cx="${f(x + dx)}" cy="${f(y + dy)}" r="${f(Math.max(1, br * shrink))}" fill="${fill}"/>`).join("");
  let s = layer(0, 0, 1, ramp[0]);
  s += layer(light[0] * r * 0.06, light[1] * r * 0.06, 0.82, ramp[1]);
  s += layer(light[0] * r * 0.14, light[1] * r * 0.14, 0.58, ramp[2]);
  s += layer(light[0] * r * 0.22, light[1] * r * 0.22, 0.3, ramp[3]);
  for (let i = 0; i < Math.round(r * 0.9); i++) {
    const a = rng() * Math.PI * 2, k = Math.sqrt(rng()) * r * 0.85;
    const x = Math.round(cx + Math.cos(a) * k), y = Math.round(cy + Math.sin(a) * k * 0.8);
    const lit = Math.cos(a) * light[0] + Math.sin(a) * light[1] > 0.2;
    s += `<rect x="${x}" y="${y}" width="1" height="1" fill="${lit ? ramp[4] : ramp[0]}"/>`;
  }
  return s;
}

// ---------------------------------------------------------------- pixels

/**
 * The `pixels` primitive: rows of characters over a legend of colours; `.` is empty. Emitted as
 * one rect per horizontal run, so a sprite costs its runs and not its pixels. `flip` mirrors it.
 */
export function pixels(rows: string[], legend: Record<string, string>, x: number, y: number, s = 1, flip = false): string {
  let out = "";
  const w = Math.max(...rows.map((r) => r.length));
  rows.forEach((row0, j) => {
    const row = flip ? row0.padEnd(w, ".").split("").reverse().join("") : row0;
    let i = 0;
    while (i < row.length) {
      const c = row[i];
      let k = i + 1;
      while (k < row.length && row[k] === c) k++;
      if (c !== "." && c !== " " && legend[c]) out += `<rect x="${x + i * s}" y="${y + j * s}" width="${(k - i) * s}" height="${s}" fill="${legend[c]}"/>`;
      i = k;
    }
  });
  return out;
}

/** A 3×5 bitmap font, itself `pixels` documents: digits, capitals and the punctuation a HUD uses. */
const GLYPHS: Record<string, string> = {
  "0": "###|#.#|#.#|#.#|###", "1": ".#.|##.|.#.|.#.|###", "2": "###|..#|###|#..|###", "3": "###|..#|.##|..#|###",
  "4": "#.#|#.#|###|..#|..#", "5": "###|#..|###|..#|###", "6": "###|#..|###|#.#|###", "7": "###|..#|.#.|.#.|.#.",
  "8": "###|#.#|###|#.#|###", "9": "###|#.#|###|..#|###",
  A: ".#.|#.#|###|#.#|#.#", B: "##.|#.#|##.|#.#|##.", C: ".##|#..|#..|#..|.##", D: "##.|#.#|#.#|#.#|##.",
  E: "###|#..|##.|#..|###", F: "###|#..|##.|#..|#..", G: ".##|#..|#.#|#.#|.##", H: "#.#|#.#|###|#.#|#.#",
  I: "###|.#.|.#.|.#.|###", J: "..#|..#|..#|#.#|.#.", K: "#.#|#.#|##.|#.#|#.#", L: "#..|#..|#..|#..|###",
  M: "#.#|###|###|#.#|#.#", N: "##.|#.#|#.#|#.#|#.#", O: ".#.|#.#|#.#|#.#|.#.", P: "##.|#.#|##.|#..|#..",
  Q: ".#.|#.#|#.#|##.|.##", R: "##.|#.#|##.|#.#|#.#", S: ".##|#..|.#.|..#|##.", T: "###|.#.|.#.|.#.|.#.",
  U: "#.#|#.#|#.#|#.#|###", V: "#.#|#.#|#.#|#.#|.#.", W: "#.#|#.#|###|###|#.#", X: "#.#|#.#|.#.|#.#|#.#",
  Y: "#.#|#.#|.#.|.#.|.#.", Z: "###|..#|.#.|#..|###",
  "/": "..#|..#|.#.|#..|#..", ",": "...|...|...|.#.|#..", ".": "...|...|...|...|.#.", ":": "...|.#.|...|.#.|...",
  " ": "...|...|...|...|...",
};

/** Text in the 3×5 font at `scale`, with an optional one-cell outline drawn first. */
export function text3x5(str: string, x: number, y: number, color: string, o: { scale?: number; outline?: string } = {}): string {
  const s = o.scale ?? 1;
  const draw = (ox: number, oy: number, c: string) =>
    str.toUpperCase().split("").map((ch, i) => pixels((GLYPHS[ch] ?? GLYPHS[" "]).split("|"), { "#": c }, ox + i * 4 * s, oy, s)).join("");
  let out = "";
  if (o.outline)
    for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) out += draw(x + dx * s, y + dy * s, o.outline);
  return out + draw(x, y, color);
}
export const textWidth3x5 = (str: string, scale = 1) => str.length * 4 * scale - scale;

// ---------------------------------------------------------------- colour

export const hex = ([r, g, b]: RGB) => `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
/** The five hue-shifted steps of one base colour, darkest first — the plan's OKLCH ramp. */
export const rampHex = (base: string) => hueShiftedRamp(base).map(hex);

/** Mix in OKLab: perceptually even, and it does not grey out the middle the way sRGB does. */
export function mixOk(a: string, b: string, t: number): string {
  const A = oklab(hexRgb(a)), B = oklab(hexRgb(b));
  return hex(fromOklab([A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t]).rgb);
}

/** A layer's colour from its depth: mixed toward the fog, keeping the fog's hue — fog is a hue, not a grey. */
export const atDepth = (base: string, fog: string, depth: number, reach = 0.85) => mixOk(base, fog, Math.min(1, depth * reach));

// ---------------------------------------------------------------- frames

export const frameSvg = (w: number, h: number, body: string[], crisp = true, defs = "") =>
  `<svg xmlns="http://www.w3.org/2000/svg"${crisp ? ' shape-rendering="crispEdges"' : ""} width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${defs ? `<defs>${defs}</defs>` : ""}<rect width="${w}" height="${h}" fill="none"/>${body.join("")}</svg>`;

/**
 * Rasterise with fonts named explicitly and system fonts off. A font is a file the document
 * set carries, like a token; a bake that picked up whatever the machine had installed would
 * differ between a laptop and CI, which is the one thing a bake may not do.
 */
export function rasterFonts(svg: string, zoom = 1, fontFiles: string[] = [], family?: string): Img {
  const r = new Resvg(svg, {
    fitTo: { mode: "zoom", value: zoom },
    font: { fontFiles, loadSystemFonts: false, defaultFontFamily: family },
  }).render();
  return { w: r.width, h: r.height, px: new Uint8Array(r.pixels) };
}

/** Straight-alpha over, at integer pixel positions — sprites never land between pixels. */
export function over(dst: Img, src: Img, ox: number, oy: number): void {
  for (let y = 0; y < src.h; y++)
    for (let x = 0; x < src.w; x++) {
      const si = (y * src.w + x) * 4;
      if (src.px[si + 3] === 0) continue;
      const dx = ox + x, dy = oy + y;
      if (dx < 0 || dy < 0 || dx >= dst.w || dy >= dst.h) continue;
      dst.px.set(src.px.subarray(si, si + 4), (dy * dst.w + dx) * 4);
    }
}

/**
 * Premultiplied source-over, for layers that carry partial coverage — anti-aliased text, a soft
 * shadow. `over` is for pixel sprites, whose alpha is 0 or 1 and which must never be mixed.
 */
export function blend(dst: Img, src: Img, ox: number, oy: number): void {
  for (let y = 0; y < src.h; y++)
    for (let x = 0; x < src.w; x++) {
      const si = (y * src.w + x) * 4, a = src.px[si + 3] / 255;
      if (a === 0) continue;
      const dx = ox + x, dy = oy + y;
      if (dx < 0 || dy < 0 || dx >= dst.w || dy >= dst.h) continue;
      const di = (dy * dst.w + dx) * 4;
      for (let c = 0; c < 3; c++) dst.px[di + c] = Math.round(src.px[si + c] + dst.px[di + c] * (1 - a));
      dst.px[di + 3] = Math.round(255 * (a + (dst.px[di + 3] / 255) * (1 - a)));
    }
}

/** A pixel sprite scaled by a whole number, nearest-neighbour, its alpha kept binary. */
export function scaleNearest(img: Img, k: number): Img {
  const out: Img = { w: img.w * k, h: img.h * k, px: new Uint8Array(img.w * k * img.h * k * 4) };
  for (let y = 0; y < out.h; y++)
    for (let x = 0; x < out.w; x++) {
      const si = (Math.floor(y / k) * img.w + Math.floor(x / k)) * 4;
      if (img.px[si + 3] < 128) continue;
      const a = img.px[si + 3] / 255;
      out.px.set([Math.round(img.px[si] / a), Math.round(img.px[si + 1] / a), Math.round(img.px[si + 2] / a), 255], (y * out.w + x) * 4);
    }
  return out;
}

export function upscale(img: Img, k: number): Float32Array {
  const W = img.w * k, H = img.h * k, out = new Float32Array(W * H * 3);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const si = (Math.floor(y / k) * img.w + Math.floor(x / k)) * 4, di = (y * W + x) * 3;
      const a = img.px[si + 3] / 255;
      for (let c = 0; c < 3; c++) out[di + c] = (img.px[si + c] / 255) * (a > 0 ? 1 : 0);
    }
  return out;
}

/**
 * Three box passes each way ≈ a Gaussian; cheap and separable. Works on a copy: the passes
 * ping-pong between two buffers, and handing the caller's in as one of them overwrote the emission
 * map that the second bloom and the emissive test still had to read.
 */
export function blur(buf: Float32Array, W: number, H: number, r: number): Float32Array {
  let a: Float32Array = Float32Array.from(buf), b: Float32Array = new Float32Array(buf.length);
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

/** A point light, in native-frame pixels: colour, reach and strength. */
export interface Light { at: P; r: number; color: string; power: number }

export interface FinishOptions {
  up: number;
  bloom?: { tight: number; wide: number; tightGain: number; wideGain: number };
  vignette?: number;
  /** When set, the frame is lit: ambient × every pixel, plus each light's falloff. Emission is exempt. */
  ambient?: string;
  lights?: Light[];
  /** Grade: raise the black point to this (0–1), the matte look of a frame whose darkest ink is grey. */
  lift?: number;
}

/**
 * The frame after the pixels: scale up by a whole number, light it at the output resolution so
 * falloff is smooth over hard pixels, paint emissive pixels back at full strength (light does
 * not darken a flame), then bloom from the emission map and vignette.
 */
export function finish(frame: Img, glow: Img | undefined, o: FinishOptions): PNG {
  const W = frame.w * o.up, H = frame.h * o.up;
  const base = upscale(frame, o.up);
  const em = glow ? upscale(glow, o.up) : undefined;
  const tight = em && o.bloom ? blur(em, W, H, o.bloom.tight) : undefined;
  const wide = em && o.bloom ? blur(em, W, H, o.bloom.wide) : undefined;
  const amb = o.ambient ? hexRgb(o.ambient).map((v) => v / 255) : undefined;
  const lights = (o.lights ?? []).map((l) => ({ ...l, rgb: hexRgb(l.color).map((v) => v / 255) }));
  const png = new PNG({ width: W, height: H });
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 3;
      const dx = x / W - 0.5, dy = y / H - 0.5;
      const vig = 1 - (o.vignette ?? 0) * Math.min(1, (dx * dx + dy * dy) * 2.2);
      let lit = [1, 1, 1];
      if (amb) {
        lit = [...amb];
        for (const l of lights) {
          const t = Math.hypot(x / o.up - l.at[0], y / o.up - l.at[1]) / l.r;
          if (t >= 1) continue;
          const k = (1 - t) * (1 - t) * l.power;
          for (let c = 0; c < 3; c++) lit[c] += l.rgb[c] * k;
        }
      }
      // only a lit frame needs emission painted back: unlit, the frame already holds it at full strength
      const emissive = amb && em ? em[i] + em[i + 1] + em[i + 2] > 0 : false;
      for (let c = 0; c < 3; c++) {
        let v = emissive ? em![i + c] : base[i + c] * lit[c];
        if (tight) v += tight[i + c] * o.bloom!.tightGain + wide![i + c] * o.bloom!.wideGain;
        const lift = o.lift ?? 0;
        png.data[(y * W + x) * 4 + c] = Math.round(255 * Math.min(1, lift + (1 - lift) * v * vig));
      }
      png.data[(y * W + x) * 4 + 3] = 255;
    }
  return png;
}

export function writeOut(name: string, png: PNG): string {
  const dir = `${ROOT}out/spikes`;
  mkdirSync(dir, { recursive: true });
  const file = `${dir}/${name}`;
  writeFileSync(file, PNG.sync.write(png));
  return file;
}

export function imgToPng(img: Img): PNG {
  const png = new PNG({ width: img.w, height: img.h });
  png.data.set(img.px);
  return png;
}
