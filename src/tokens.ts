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
 */

export interface Tokens {
  grid: number;
  colors: Record<string, string>;
  ramps: Record<string, number>;
  strokes: Record<string, number>;
  alpha: Record<string, number>;
  layers: Record<string, number>;
}

export interface Theme {
  name: string;
  description?: string;
  colors?: Record<string, string>;
  ramps?: Record<string, number>;
  strokes?: Record<string, number>;
  alpha?: Record<string, number>;
  layers?: Record<string, number>;
}

export function applyTheme(base: Tokens, theme?: Theme): Tokens {
  if (!theme) return base;
  return {
    grid: base.grid,
    colors: { ...base.colors, ...theme.colors },
    ramps: { ...base.ramps, ...theme.ramps },
    strokes: { ...base.strokes, ...theme.strokes },
    alpha: { ...base.alpha, ...theme.alpha },
    layers: { ...base.layers, ...theme.layers },
  };
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
