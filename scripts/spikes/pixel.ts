/**
 * SPIKE — not system code. The pixel-look pass shared by pixel-look.ts and pixel-scene.ts:
 * OKLCH hue-shifted ramps, the document's closed palette, paint snapping (v2), and the
 * alpha-snap / orphan / selective-outline pass. See pixel-look.ts for what each step is for.
 */
import { Resvg } from "@resvg/resvg-js";
import type { Asset } from "../../src/schema.js";
import type { Tokens } from "../../src/tokens.js";

// ---------------------------------------------------------------- OKLab / OKLCH

export type RGB = [number, number, number];
const toLin = (v: number) => ((v /= 255) <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
const fromLin = (v: number) => 255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055);

export function oklab([r, g, b]: RGB): RGB {
  const [R, G, B] = [toLin(r), toLin(g), toLin(b)];
  const l = Math.cbrt(0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B);
  const m = Math.cbrt(0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B);
  const s = Math.cbrt(0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

export function fromOklab([L, a, b]: RGB): { rgb: RGB; inGamut: boolean } {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const lin = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
  const inGamut = lin.every((v) => v >= -1e-4 && v <= 1 + 1e-4);
  const rgb = lin.map((v) => Math.max(0, Math.min(255, Math.round(fromLin(Math.max(0, Math.min(1, v))))))) as RGB;
  return { rgb, inGamut };
}

const toLch = ([L, a, b]: RGB): RGB => [L, Math.hypot(a, b), ((Math.atan2(b, a) * 180) / Math.PI + 360) % 360];
const fromLch = ([L, C, h]: RGB): RGB => [L, C * Math.cos((h * Math.PI) / 180), C * Math.sin((h * Math.PI) / 180)];

/** Turn hue `h` toward `target` by at most `deg`, the short way round. */
function toward(h: number, target: number, deg: number): number {
  let d = ((target - h + 540) % 360) - 180;
  if (Math.abs(d) < deg) return target;
  return (h + Math.sign(d) * deg + 360) % 360;
}

/** Fit into sRGB by giving up chroma, never lightness or hue. */
export function gamutFit(lch: RGB): RGB {
  let [L, C, h] = lch;
  for (let i = 0; i < 40; i++) {
    const r = fromOklab(fromLch([L, C, h]));
    if (r.inGamut) return r.rgb;
    C *= 0.93;
  }
  return fromOklab(fromLch([L, C, h])).rgb;
}

/**
 * The ramp the plan proposes for tokens: five steps, and the hue moves with the value.
 * Numbers are a first guess, not tuned — the spike only asks whether the idea carries.
 */
export function hueShiftedRamp(hex: string): RGB[] {
  const rgb = hexRgb(hex);
  const [L, C, h] = toLch(oklab(rgb));
  const SHADOW_HUE = 285, LIGHT_HUE = 95; // violet shadows, warm lights
  const step = (dL: number, cMul: number, hueTarget: number, hueDeg: number): RGB =>
    gamutFit([Math.max(0.08, Math.min(0.98, L + dL)), C * cMul, C < 0.02 ? h : toward(h, hueTarget, hueDeg)]);
  return [
    step(-0.24, 0.9, SHADOW_HUE, 28),
    step(-0.12, 1.0, SHADOW_HUE, 14),
    rgb,
    step(+0.1, 0.92, LIGHT_HUE, 10),
    step(+0.2, 0.75, LIGHT_HUE, 18),
  ];
}

export function hexRgb(hex: string): RGB {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// ---------------------------------------------------------------- the document's palette

/** Every colour token a document paints with, following `use` down. */
function tokensUsed(a: Asset, reg: Map<string, Asset>, seen = new Set<string>()): Set<string> {
  const out = new Set<string>();
  if (seen.has(a.id)) return out;
  seen.add(a.id);
  const json = JSON.stringify(a);
  for (const m of json.matchAll(/"\$([a-z][a-z0-9_-]*)/gi)) out.add(m[1]);
  for (const m of json.matchAll(/"use":"([^"]+)"/g)) {
    const t = reg.get(m[1]);
    if (t) for (const x of tokensUsed(t, reg, seen)) out.add(x);
  }
  return out;
}

export function paletteFor(a: Asset, tokens: Tokens, reg: Map<string, Asset>): { colors: RGB[]; lab: RGB[]; family: number[]; names: string[] } {
  const colors: RGB[] = [];
  const family: number[] = [];
  const names: string[] = [];
  for (const name of [...tokensUsed(a, reg)].sort()) {
    const hex = tokens.colors[name];
    if (!hex) continue;
    for (const c of hueShiftedRamp(hex)) {
      colors.push(c);
      family.push(names.length);
    }
    names.push(name);
  }
  return { colors, lab: colors.map(oklab), family, names };
}

// ---------------------------------------------------------------- palette-closed paints (v2)

/**
 * The same palette, applied where the colour is chosen instead of after the fact. Every
 * `$token.ramp` becomes the matching step of that token's hue-shifted ramp, and every gradient
 * becomes hard bands of those steps, so the rasteriser can only ever write palette colours
 * inside a part. Post-quantising has to guess a family per pixel and guesses across families;
 * this never has to guess. Only translucency still mixes, and the pixel pass snaps what it mixes.
 */
const STEP: Record<string, number> = { dark2: 0, dark: 1, "": 2, light: 3, light2: 4 };
const REF = /^\$([a-z][a-z0-9_-]*)(?:\.(light2|light|dark2|dark))?(?:@([a-z0-9_.]+))?$/i;

export function snapRegistry(reg: Map<string, Asset>, tokens: Tokens): { assets: Map<string, Asset>; tokens: Tokens } {
  const colors = { ...tokens.colors };
  const snap = (ref: string): string => {
    const m = REF.exec(ref);
    if (!m || !tokens.colors[m[1]]) return ref;
    const name = `px-${m[1]}-${STEP[m[2] ?? ""]}`;
    const [r, g, b] = hueShiftedRamp(tokens.colors[m[1]])[STEP[m[2] ?? ""]];
    colors[name] = `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
    return `$${name}${m[3] ? `@${m[3]}` : ""}`;
  };
  const paint = (p: unknown): unknown => {
    if (typeof p === "string") return snap(p);
    if (p && typeof p === "object" && "stops" in p) {
      const g = p as { stops: [number, string][] };
      const stops = g.stops.map(([o, c]) => [o, snap(c)] as [number, string]);
      // hard bands: each stop owns the span up to the midpoint with the next
      const hard: [number, string][] = [];
      stops.forEach(([o, c], i) => {
        const lo = i === 0 ? 0 : (stops[i - 1][0] + o) / 2;
        const hi = i === stops.length - 1 ? 1 : (o + stops[i + 1][0]) / 2;
        hard.push([lo, c], [hi, c]);
      });
      return { ...g, stops: hard };
    }
    return p;
  };
  const walk = (parts: Asset["parts"]) => {
    for (const part of parts as Record<string, any>[]) {
      if (part.fill !== undefined) part.fill = paint(part.fill);
      if (part.stroke?.color) part.stroke.color = snap(part.stroke.color);
    }
  };
  const assets = new Map<string, Asset>();
  for (const [id, a] of reg) {
    const c = structuredClone(a);
    walk(c.parts);
    for (const v of Object.values(c.variants ?? {})) walk(v.add ?? []);
    assets.set(id, c);
  }
  return { assets, tokens: { ...tokens, colors } };
}

// ---------------------------------------------------------------- raster helpers

export interface Img { w: number; h: number; px: Uint8Array } // RGBA

export function raster(svg: string, zoom: number): Img {
  const r = new Resvg(svg, { fitTo: { mode: "zoom", value: zoom } }).render();
  return { w: r.width, h: r.height, px: new Uint8Array(r.pixels) };
}

export function pad(img: Img, n: number): Img {
  const w = img.w + 2 * n, h = img.h + 2 * n;
  const px = new Uint8Array(w * h * 4);
  for (let y = 0; y < img.h; y++) px.set(img.px.subarray(y * img.w * 4, (y + 1) * img.w * 4), ((y + n) * w + n) * 4);
  return { w, h, px };
}

export function pixelPass(img: Img, pal: ReturnType<typeof paletteFor>, ink: RGB): { img: Img; used: number; idx: Int32Array } {
  const { w, h } = img;
  const idx = new Int32Array(w * h).fill(-1);
  // 2 + 3: binary alpha, nearest palette entry in OKLab
  for (let i = 0; i < w * h; i++) {
    if (img.px[i * 4 + 3] < 128) continue;
    // un-premultiply is unnecessary here: alpha ≥ 128 pixels are mostly opaque interiors
    const a = img.px[i * 4 + 3] / 255;
    const lab = oklab([img.px[i * 4] / a, img.px[i * 4 + 1] / a, img.px[i * 4 + 2] / a].map((v) => Math.min(255, v)) as RGB);
    let best = 0, bestD = Infinity;
    for (let k = 0; k < pal.lab.length; k++) {
      const q = pal.lab[k];
      const d = (lab[0] - q[0]) ** 2 + (lab[1] - q[1]) ** 2 + (lab[2] - q[2]) ** 2;
      if (d < bestD) { bestD = d; best = k; }
    }
    idx[i] = best;
  }
  // 4: orphans
  const n4 = (i: number) => [i - 1, i + 1, i - w, i + w];
  for (let y = 1; y < h - 1; y++)
    for (let x = 1; x < w - 1; x++) {
      const i = y * w + x;
      if (idx[i] < 0) continue;
      const nb = n4(i).map((j) => idx[j]);
      if (nb.every((v) => v === nb[0]) && nb[0] >= 0 && nb[0] !== idx[i]) idx[i] = nb[0];
    }
  // 5: selective outline, outside the silhouette
  const out = new Uint8Array(w * h * 4);
  const inkLab = oklab(ink);
  const outlineOf = (k: number): RGB => {
    const darkest = pal.lab[pal.family.indexOf(pal.family[k])]; // step 0 of that family
    const m: RGB = [darkest[0] * 0.55 + inkLab[0] * 0.45, darkest[1] * 0.55 + inkLab[1] * 0.45, darkest[2] * 0.55 + inkLab[2] * 0.45];
    return fromOklab(m).rgb;
  };
  const used = new Set<number>();
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      let c: RGB | undefined;
      if (idx[i] >= 0) { c = pal.colors[idx[i]]; used.add(idx[i]); }
      else {
        const nb = [x > 0 ? i - 1 : -1, x < w - 1 ? i + 1 : -1, y > 0 ? i - w : -1, y < h - 1 ? i + w : -1].filter((j) => j >= 0 && idx[j] >= 0);
        if (nb.length) c = outlineOf(idx[nb[0]]);
      }
      if (c) out.set([c[0], c[1], c[2], 255], i * 4);
    }
  return { img: { w, h, px: out }, used: used.size, idx };
}
