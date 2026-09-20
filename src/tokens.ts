/**
 * Design tokens: the single source for every color, stroke width, alpha and layer.
 * Assets never contain raw values — they contain token references.
 *
 * Color reference grammar (a string):
 *   "$blood"          → colors.blood
 *   "$blood.light"    → lighten by ramps.light          (.light2 = twice)
 *   "$blood.dark"     → darken  by ramps.dark           (.dark2  = twice)
 *   "$blood@soft"     → alpha from alpha tokens
 *   "$blood.dark@0.4" → literal alpha
 * Raw "#rrggbb" is accepted but reported as a lint warning — prefer tokens.
 *
 * Sound documents resolve against the same file's `audio` section, with a
 * deliberately parallel grammar:
 *   "$tap"            → audio.pitch.tap, in Hz
 *   "$tap.down"       → multiplied by audio.ramps.down   (.up2 / .down2 = twice)
 * Gain, Q and duration take a number or a token name, exactly as stroke widths
 * and opacities do. A theme may overlay any of it, so one overlay file can
 * restyle how the roster looks *and* how it sounds.
 */

export interface AudioTokens {
  /** The palette: named pitches in Hz. Sound's answer to `colors`. */
  pitch: Record<string, number>;
  /** Frequency multipliers for the `.up` / `.down` suffixes (octaves by default). */
  ramps: Record<string, number>;
  /** Named output levels, 0..1 — sound's answer to `alpha`. */
  gain: Record<string, number>;
  /** Named filter resonances — sound's answer to `strokes`. */
  q: Record<string, number>;
  /** Named lengths in seconds. */
  dur: Record<string, number>;
  /**
   * Where each family of triggered sound should sit, in dB K-weighted:
   * `anchor` is the level the set is held around, every other key is a
   * family's offset from it (`tags[1]`), `band` the tolerance either side,
   * and `phoneLoss` how much a sound may lose through a small speaker before
   * the lint says its low end is carrying it. Sound's answer to `layers` —
   * an order between things that share a frame.
   */
  loudness?: Record<string, number>;
}

export interface Tokens {
  grid: number;
  colors: Record<string, string>;
  ramps: Record<string, number>;
  strokes: Record<string, number>;
  alpha: Record<string, number>;
  layers: Record<string, number>;
  audio?: AudioTokens;
}

/**
 * A partial token set laid over another. Tokens resolve base ⊕ app ⊕ theme:
 * `tokens/base.json` is what is physics rather than identity (ramps, stroke
 * widths, alpha, the structural greys, the audio ladders), `apps/<id>/tokens.json`
 * is the app's palette, grid, layers and loudness families over it, and a
 * theme is an overlay over that. The same merge does all three steps.
 */
export interface TokenOverlay {
  grid?: number;
  colors?: Record<string, string>;
  ramps?: Record<string, number>;
  strokes?: Record<string, number>;
  alpha?: Record<string, number>;
  layers?: Record<string, number>;
  audio?: Partial<AudioTokens>;
}

export interface Theme extends TokenOverlay {
  name: string;
  description?: string;
}

export function overlayTokens(base: Tokens, over?: TokenOverlay): Tokens {
  if (!over) return base;
  return {
    grid: over.grid ?? base.grid,
    colors: { ...base.colors, ...over.colors },
    ramps: { ...base.ramps, ...over.ramps },
    strokes: { ...base.strokes, ...over.strokes },
    alpha: { ...base.alpha, ...over.alpha },
    layers: { ...base.layers, ...over.layers },
    audio: base.audio && {
      pitch: { ...base.audio.pitch, ...over.audio?.pitch },
      ramps: { ...base.audio.ramps, ...over.audio?.ramps },
      gain: { ...base.audio.gain, ...over.audio?.gain },
      q: { ...base.audio.q, ...over.audio?.q },
      dur: { ...base.audio.dur, ...over.audio?.dur },
      loudness: { ...base.audio.loudness, ...over.audio?.loudness },
    },
  };
}

/** A theme may only override what the app resolves — it never introduces a token. A theme's grid is ignored. */
export function applyTheme(base: Tokens, theme?: Theme): Tokens {
  if (!theme) return base;
  return overlayTokens(base, { ...theme, grid: undefined });
}

export type Resolved<T> =
  | { ok: true; value: T; warn?: string }
  | { ok: false; error: string; suggestions?: string[] };

const COLOR_REF = /^\$([a-z][a-z0-9_-]*)(?:\.(light2|light|dark2|dark))?(?:@([a-z0-9_.]+))?$/i;
const HEX = /^#([0-9a-f]{6})$/i;

function hexToRgb(hex: string): [number, number, number] {
  const m = HEX.exec(hex)!;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function mix(c: number, toward: number, f: number): number {
  return Math.round(c + (toward - c) * f);
}

function rgbCss(rgb: [number, number, number], a: number): string {
  const [r, g, b] = rgb;
  if (a >= 1) return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
  return `rgba(${r},${g},${b},${+a.toFixed(3)})`;
}

function levenshtein(a: string, b: string): number {
  const dp = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return dp[a.length][b.length];
}

export function suggest(name: string, candidates: string[]): string[] {
  return candidates
    .map((c) => ({ c, d: levenshtein(name, c) }))
    .sort((x, y) => x.d - y.d)
    .slice(0, 3)
    .map((x) => x.c);
}

/** Resolve a color reference to [r, g, b, a] floats 0..1 — the engine-neutral form. */
export function resolveColorRgba(ref: string, t: Tokens): Resolved<[number, number, number, number]> {
  const r = resolveParts(ref, t);
  if (!r.ok) return r;
  const [rr, gg, bb] = r.value.rgb;
  const f = (n: number) => Math.round((n / 255) * 10000) / 10000;
  return { ok: true, value: [f(rr), f(gg), f(bb), r.value.a], warn: r.warn };
}

/** Resolve a color reference to a CSS color. */
export function resolveColor(ref: string, t: Tokens): Resolved<string> {
  const r = resolveParts(ref, t);
  if (!r.ok) return r;
  return { ok: true, value: rgbCss(r.value.rgb, r.value.a), warn: r.warn };
}

function resolveParts(ref: string, t: Tokens): Resolved<{ rgb: [number, number, number]; a: number }> {
  if (HEX.test(ref)) {
    return { ok: true, value: { rgb: hexToRgb(ref), a: 1 }, warn: `raw hex "${ref}" — prefer a token like $${nearestColor(ref, t)}` };
  }
  const m = COLOR_REF.exec(ref);
  if (!m) return { ok: false, error: `bad color ref "${ref}" — expected "$name", "$name.light|dark(2)", optional "@alpha"` };
  const [, name, ramp, alphaRef] = m;
  const hex = t.colors[name];
  if (!hex) return { ok: false, error: `unknown color token "$${name}"`, suggestions: suggest(name, Object.keys(t.colors)).map((s) => `$${s}`) };
  let rgb = hexToRgb(hex);
  if (ramp) {
    const twice = ramp.endsWith("2");
    const key = twice ? ramp.slice(0, -1) : ramp;
    const f = t.ramps[key];
    if (f === undefined) return { ok: false, error: `unknown ramp "${key}" (tokens.ramps)`, suggestions: Object.keys(t.ramps) };
    const toward = key === "light" ? 255 : 0;
    for (let i = 0; i < (twice ? 2 : 1); i++) rgb = [mix(rgb[0], toward, f), mix(rgb[1], toward, f), mix(rgb[2], toward, f)];
  }
  let a = 1;
  if (alphaRef !== undefined) {
    if (alphaRef in t.alpha) a = t.alpha[alphaRef];
    else if (!Number.isNaN(parseFloat(alphaRef))) a = parseFloat(alphaRef);
    else return { ok: false, error: `unknown alpha token "@${alphaRef}"`, suggestions: Object.keys(t.alpha) };
    if (a < 0 || a > 1) return { ok: false, error: `alpha out of range in "${ref}"` };
  }
  return { ok: true, value: { rgb, a } };
}

function nearestColor(hex: string, t: Tokens): string {
  const [r, g, b] = hexToRgb(hex);
  let best = "ink", bestD = Infinity;
  for (const [name, h] of Object.entries(t.colors)) {
    const [r2, g2, b2] = hexToRgb(h);
    const d = (r - r2) ** 2 + (g - g2) ** 2 + (b - b2) ** 2;
    if (d < bestD) { bestD = d; best = name; }
  }
  return best;
}

/** Resolve a stroke-width or opacity reference: a plain number, or a token name string. */
export function resolveNumber(
  ref: string | number,
  table: Record<string, number>,
  kind: string,
): Resolved<number> {
  if (typeof ref === "number") return { ok: true, value: ref };
  const name = ref.startsWith("$") ? ref.slice(1) : ref;
  if (name in table) return { ok: true, value: table[name] };
  return { ok: false, error: `unknown ${kind} token "${ref}"`, suggestions: suggest(name, Object.keys(table)) };
}

const PITCH_REF = /^\$([a-z][a-z0-9_-]*)(?:\.([a-z][a-z0-9]*?)(2)?)?$/i;

/**
 * Resolve a pitch reference to Hz. Same shape as a color reference, one table
 * over: `$tap` is the palette entry, `$tap.down` walks a ramp, `$tap.down2`
 * walks it twice. A raw number renders but warns — identity should come from
 * the palette, exactly as it does for color.
 */
export function resolvePitch(ref: string | number, a: AudioTokens): Resolved<number> {
  if (typeof ref === "number") {
    if (!(ref > 0)) return { ok: false, error: `pitch must be positive Hz, got ${ref}` };
    return { ok: true, value: ref, warn: `raw ${ref}Hz — prefer a token like $${nearestPitch(ref, a)}` };
  }
  const m = PITCH_REF.exec(ref);
  if (!m) return { ok: false, error: `bad pitch ref "${ref}" — expected "$name" or "$name.up|down(2)"` };
  const [, name, ramp, twice] = m;
  const base = a.pitch[name];
  if (base === undefined)
    return { ok: false, error: `unknown pitch token "$${name}"`, suggestions: suggest(name, Object.keys(a.pitch)).map((s) => `$${s}`) };
  let hz = base;
  if (ramp) {
    const f = a.ramps[ramp];
    if (f === undefined) return { ok: false, error: `unknown audio ramp "${ramp}"`, suggestions: Object.keys(a.ramps) };
    hz *= twice ? f * f : f;
  }
  return { ok: true, value: Math.round(hz * 100) / 100 };
}

function nearestPitch(hz: number, a: AudioTokens): string {
  let best = "", bestD = Infinity;
  for (const [name, v] of Object.entries(a.pitch)) {
    // Compared in octaves: 100Hz is as far from 200 as 1000 is from 2000.
    const d = Math.abs(Math.log2(hz / v));
    if (d < bestD) { bestD = d; best = name; }
  }
  return best || "?";
}

// ---------------------------------------------------------------- measuring colour

/** A colour reference as 0–255 sRGB, for measuring rather than painting. */
export function resolveRgb255(ref: string, t: Tokens): [number, number, number] | undefined {
  const r = resolveColorRgba(ref, t);
  if (!r.ok) return undefined;
  return [r.value[0] * 255, r.value[1] * 255, r.value[2] * 255];
}

function labOf([r, g, b]: [number, number, number]): [number, number, number] {
  const lin = (v: number) => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const [R, G, B] = [lin(r), lin(g), lin(b)];
  // sRGB → XYZ (D65), then CIE L*a*b* against the D65 white.
  const X = (R * 0.4124564 + G * 0.3575761 + B * 0.1804375) / 0.95047;
  const Y = R * 0.2126729 + G * 0.7151522 + B * 0.072175;
  const Z = (R * 0.0193339 + G * 0.119192 + B * 0.9503041) / 1.08883;
  const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : (841 / 108) * t + 4 / 29);
  const [fx, fy, fz] = [f(X), f(Y), f(Z)];
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

/**
 * CIEDE2000 between two sRGB colours: how far apart two colours *look*, on a
 * scale where 1 is about the smallest difference an eye catches and 13 is
 * "these are different colours" for a rim you have to tell apart at a glance.
 * Used by the `distinct` rule, and by nothing that paints — a render never
 * depends on a perceptual model.
 */
export function deltaE2000(c1: [number, number, number], c2: [number, number, number]): number {
  const [L1, a1, b1] = labOf(c1), [L2, a2, b2] = labOf(c2);
  const rad = Math.PI / 180, deg = 180 / Math.PI;
  const C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2);
  const Cbar = (C1 + C2) / 2;
  const G = 0.5 * (1 - Math.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7)));
  const a1p = a1 * (1 + G), a2p = a2 * (1 + G);
  const C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2);
  const hue = (a: number, b: number) => {
    if (a === 0 && b === 0) return 0;
    const d = Math.atan2(b, a) * deg;
    return d < 0 ? d + 360 : d;
  };
  const h1p = hue(a1p, b1), h2p = hue(a2p, b2);
  const dLp = L2 - L1, dCp = C2p - C1p;
  let dhp = 0;
  if (C1p * C2p !== 0) {
    dhp = h2p - h1p;
    if (dhp > 180) dhp -= 360;
    else if (dhp < -180) dhp += 360;
  }
  const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp / 2) * rad);
  const Lbp = (L1 + L2) / 2, Cbp = (C1p + C2p) / 2;
  let hbp = h1p + h2p;
  if (C1p * C2p !== 0) {
    if (Math.abs(h1p - h2p) <= 180) hbp = (h1p + h2p) / 2;
    else hbp = h1p + h2p < 360 ? (h1p + h2p + 360) / 2 : (h1p + h2p - 360) / 2;
  }
  const T =
    1 - 0.17 * Math.cos((hbp - 30) * rad) + 0.24 * Math.cos(2 * hbp * rad) + 0.32 * Math.cos((3 * hbp + 6) * rad) - 0.2 * Math.cos((4 * hbp - 63) * rad);
  const dTheta = 30 * Math.exp(-(((hbp - 275) / 25) ** 2));
  const RC = 2 * Math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7));
  const SL = 1 + (0.015 * (Lbp - 50) ** 2) / Math.sqrt(20 + (Lbp - 50) ** 2);
  const SC = 1 + 0.045 * Cbp;
  const SH = 1 + 0.015 * Cbp * T;
  const RT = -Math.sin(2 * dTheta * rad) * RC;
  return Math.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH));
}
