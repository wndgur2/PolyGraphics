/**
 * How a clip is read: the eases, a track's value at a point in the loop, and a
 * document posed at that point.
 *
 * This used to be written five times — the SVG renderer, the Phaser adapter,
 * and the sheet, motion and filmstrip scripts each had their own copy, and the
 * filmstrip's had quietly gone linear. Adding an ease to one of them was a
 * pose the others did not draw. Everything in `src/` and `scripts/` reads it
 * from here now.
 *
 * The engine adapters are the exception, on purpose: each is one drop-in file
 * with no imports (README, "Layout"), so the Phaser adapter carries its own
 * copy and `scripts/test-phaser-adapter.ts` samples every ease and every track
 * in the library through both and fails on the first value that differs.
 *
 * Keys and eases. A key is `[t, value]` or `[t, value, ease]`. The ease on a key
 * shapes the segment that *leaves* it (CSS's rule for `animation-timing-function`
 * on a keyframe), and a key without one uses the track's ease, which defaults to
 * `sine`. `hold` is a step: the value stays put until the next key and arrives
 * all at once — the held pose a stepped clip is drawn from.
 */
import type { Anim, Asset, Part } from "./schema.js";

export type EaseName = "linear" | "sine" | "backOut" | "hold" | "quadIn" | "quadOut" | "expoOut";
export type Track = Anim["tracks"][number];

export const EASE_FN: Record<EaseName, (t: number) => number> = {
  linear: (t) => t,
  sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * t),
  backOut: (t) => {
    const c = 1.70158;
    const u = t - 1;
    return 1 + (c + 1) * u * u * u + c * u * u;
  },
  // the segment's start value right up to the next key; the key itself lands on it
  hold: (t) => (t >= 1 ? 1 : 0),
  quadIn: (t) => t * t,
  quadOut: (t) => 1 - (1 - t) * (1 - t),
  expoOut: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
};

/** The ease shaping the segment that leaves key `i`. */
export function segmentEase(track: Track, i: number): EaseName {
  return (track.keys[i][2] ?? track.ease ?? "sine") as EaseName;
}

/** True when a track can only be drawn by sampling: a per-key ease, or an ease CSS has no curve for. */
export function needsSampling(track: Track): boolean {
  const simple = (e: string | undefined) => e === undefined || e === "linear" || e === "sine" || e === "backOut";
  return !simple(track.ease) || track.keys.some((k) => k[2] !== undefined);
}

/** A track's value at `t` (0..1 through the clip). */
export function trackValue(track: Track, t: number): number {
  const keys = track.keys;
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1] = keys[i];
    if (t <= t1) {
      const [t0, v0] = keys[i - 1];
      const span = t1 - t0;
      if (span <= 0) return v1;
      return v0 + (v1 - v0) * EASE_FN[segmentEase(track, i - 1)]((t - t0) / span);
    }
  }
  return keys[keys.length - 1][1];
}

/** A tint the renderer lays over a posed part: its silhouette in `color`, `amount` of the way. */
export interface PoseTint {
  color: string;
  amount: number;
}

/**
 * The document posed at `t`: every track folded into its part's own transform,
 * the way the adapters pose a node (offsets added in the parent frame, rotation
 * and scale about the part's own origin). Tints are returned beside the
 * document, for `renderSVG`'s `tints` option, because a tint is not a property
 * a part has — it is a second coat over it.
 *
 * `alpha` resolves an opacity token to its number.
 */
export function poseAsset(
  asset: Asset,
  anim: Anim,
  t: number,
  alpha: Record<string, number> = {},
): { asset: Asset; tints: Record<string, PoseTint> } {
  const parts: Part[] = structuredClone(asset.parts);
  const tints: Record<string, PoseTint> = {};
  for (const tr of anim.tracks) {
    const v = trackValue(tr, t);
    for (const part of parts) {
      if (part.id !== tr.part) continue;
      const at = part.at ?? [0, 0];
      const s = part.scale ?? 1;
      const [sx, sy] = typeof s === "number" ? [s, s] : s;
      // a scale of zero is a part that has collapsed, not one the renderer can invert
      const pos = (n: number) => Math.max(n, 0.0001);
      switch (tr.prop) {
        case "x": part.at = [at[0] + v, at[1]]; break;
        case "y": part.at = [at[0], at[1] + v]; break;
        case "rot": part.rot = (part.rot ?? 0) + v; break;
        case "scale": part.scale = typeof s === "number" ? pos(s * v) : [pos(sx * v), pos(sy * v)]; break;
        case "scaleX": part.scale = [pos(sx * v), sy]; break;
        case "scaleY": part.scale = [sx, pos(sy * v)]; break;
        case "opacity": {
          const o = typeof part.opacity === "number" ? part.opacity : part.opacity === undefined ? 1 : alpha[part.opacity] ?? 1;
          part.opacity = Math.max(0, Math.min(1, o * v));
          break;
        }
        case "tint":
          if (tr.to) tints[part.id] = { color: tr.to, amount: Math.max(0, Math.min(1, v)) };
          break;
      }
    }
  }
  return { asset: { ...asset, parts }, tints };
}
