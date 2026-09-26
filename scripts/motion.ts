/**
 * How much a clip actually moves, measured in the pixels the player sees.
 *
 * A track's keys say how far a part travels in document units; what reaches
 * the screen is that, at game scale, after the silhouette around it has
 * swallowed whatever moved inside it. A tail that sways five degrees about its
 * own root moves its tip a pixel, and a pixel at 1.2× is nothing — which is how
 * a roster ends up with walks nobody can see. This poses each clip the way
 * `sheet.ts` does, rasterises every frame at the scale the game draws it, and
 * reports three numbers per clip:
 *
 *   swept   — share of the silhouette that is not covered in *every* frame
 *             (union minus intersection over union): how much of the body moves
 *   tip     — the furthest any silhouette edge travels across the loop, in
 *             screen pixels (Hausdorff distance between the two most different
 *             frames' outlines)
 *   flicker — mean share of the silhouette that changes frame to frame
 *
 * `tip` is the one to judge by. `swept` runs high on anything with thin legs —
 * a two-pixel leg that moves a pixel has half its area swept — so a clip can
 * sweep 30% and still read as standing still. Calibrated on the roster: the
 * loops that read in play (Courser 19, Forerunner 20, 색세기 23) are well past
 * 8px; the Salt Pan's walks measured 3–5, and those are the ones nobody sees.
 * Under 4 is marked invisible, under 8 faint.
 *
 *   npx tsx scripts/motion.ts ss.enemy.stinger [ss.enemy.courser …] [--anim prowl] [--zoom 1.2] [--frames 16]
 *   npx tsx scripts/motion.ts --match ss.enemy.      # every document whose id starts so, first clip each
 *   npx tsx scripts/motion.ts ss.enemy.stinger --all # every clip of it, not only the first
 */
import { Resvg } from "@resvg/resvg-js";
import type { Asset, Anim } from "../src/schema.js";
import { renderSVG } from "../src/render.js";
import { loadLibrary, ownerOf, owners, type Owner } from "../src/apps.js";

const EASE: Record<string, (t: number) => number> = {
  linear: (t) => t,
  sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * t),
  backOut: (t) => { const c = 1.70158; const u = t - 1; return 1 + (c + 1) * u * u * u + c * u * u; },
};
function evalTrack(tr: Anim["tracks"][number], p: number): number {
  const keys = tr.keys;
  if (p <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) if (p <= keys[i][0]) {
    const [t0, v0] = keys[i - 1]; const [t1, v1] = keys[i];
    return v0 + (v1 - v0) * (EASE[tr.ease ?? "sine"] ?? EASE.sine)((p - t0) / ((t1 - t0) || 1));
  }
  return keys[keys.length - 1][1];
}
function posed(owner: Owner, a: Asset, anim: Anim, p: number): Asset {
  const parts = structuredClone(a.parts);
  for (const tr of anim.tracks) {
    const v = evalTrack(tr, p);
    for (const part of parts) {
      if (part.id !== tr.part) continue;
      const at = part.at ?? [0, 0];
      switch (tr.prop) {
        case "x": part.at = [at[0] + v, at[1]]; break;
        case "y": part.at = [at[0], at[1] + v]; break;
        case "rot": part.rot = (part.rot ?? 0) + v; break;
        case "scale": { const s = part.scale ?? 1; part.scale = typeof s === "number" ? s * v : [s[0] * v, s[1] * v]; break; }
        case "opacity": { const o = typeof part.opacity === "number" ? part.opacity : part.opacity === undefined ? 1 : owner.tokens.alpha[part.opacity] ?? 1; part.opacity = Math.max(0, Math.min(1, o * v)); break; }
      }
    }
  }
  return { ...a, parts };
}

const args = process.argv.slice(2);
const flag = (n: string) => (args.includes(n) ? args[args.indexOf(n) + 1] : undefined);
const animFlag = flag("--anim");
const zoom = Number(flag("--zoom") ?? 1.2);
const frames = Number(flag("--frames") ?? 16);
const match = flag("--match");
const lib = loadLibrary();
let ids = args.filter((x, i) => !x.startsWith("--") && !["--anim", "--zoom", "--frames", "--match"].includes(args[i - 1]));
if (match) for (const o of owners(lib)) for (const id of o.assets.keys()) if (id.startsWith(match)) ids.push(id);

function mask(svg: string): { m: Uint8Array; w: number; h: number } {
  const r = new Resvg(svg, { fitTo: { mode: "zoom", value: zoom } }).render();
  const m = new Uint8Array(r.width * r.height);
  const px = r.pixels;
  for (let i = 0; i < m.length; i++) m[i] = px[i * 4 + 3] > 96 ? 1 : 0;
  return { m, w: r.width, h: r.height };
}
function edge(m: Uint8Array, w: number, h: number): [number, number][] {
  const out: [number, number][] = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (!m[i]) continue;
    if (x === 0 || y === 0 || x === w - 1 || y === h - 1 || !m[i - 1] || !m[i + 1] || !m[i - w] || !m[i + w]) out.push([x, y]);
  }
  return out;
}
function directed(a: [number, number][], b: [number, number][]): number {
  let worst = 0;
  for (const [ax, ay] of a) {
    let best = Infinity;
    for (const [bx, by] of b) { const d = (ax - bx) ** 2 + (ay - by) ** 2; if (d < best) best = d; if (best === 0) break; }
    if (best > worst) worst = best;
  }
  return Math.sqrt(worst);
}

console.log(`zoom ${zoom} · ${frames} frames per clip\n`);
console.log("id".padEnd(28), "clip".padEnd(10), "dur".padStart(5), "swept".padStart(7), "tip px".padStart(7), "flicker".padStart(8), " verdict");
for (const id of ids) {
  const o = ownerOf(lib, id);
  const a = o?.assets.get(id);
  if (!o || !a) { console.log("unknown", id); continue; }
  const all = Object.keys(a.animations ?? {});
  const names = animFlag ? [animFlag] : args.includes("--all") ? all : all.slice(0, 1);
  for (const name of names) {
    const anim = a.animations?.[name];
    if (!anim) { console.log(id.padEnd(28), "(no clip)"); continue; }
    const ms = [] as Uint8Array[]; let w = 0, h = 0;
    for (let f = 0; f < frames; f++) { const r = mask(renderSVG(posed(o, a, anim, f / frames), o.reg, {}).svg); ms.push(r.m); w = r.w; h = r.h; }
    let uni = 0, inter = 0;
    for (let i = 0; i < w * h; i++) { let s = 0; for (const m of ms) s += m[i]; if (s) uni++; if (s === frames) inter++; }
    let flick = 0;
    for (let f = 0; f < frames; f++) { const A = ms[f], B = ms[(f + 1) % frames]; let d = 0, u = 0; for (let i = 0; i < w * h; i++) { if (A[i] !== B[i]) d++; if (A[i] || B[i]) u++; } flick += d / (u || 1); }
    flick /= frames;
    // tip: the pair of frames most different in coverage, then outline distance between them
    let fa = 0, fb = 0, most = -1;
    for (let i = 0; i < frames; i++) for (let j = i + 1; j < frames; j++) { let d = 0; for (let k = 0; k < w * h; k++) if (ms[i][k] !== ms[j][k]) d++; if (d > most) { most = d; fa = i; fb = j; } }
    const ea = edge(ms[fa], w, h), eb = edge(ms[fb], w, h);
    const tip = Math.max(directed(ea, eb), directed(eb, ea));
    const swept = (uni - inter) / (uni || 1);
    const verdict = tip < 4 ? "✖ invisible" : tip < 8 ? "▲ faint" : "✓";
    console.log(id.padEnd(28), name.padEnd(10), anim.duration.toFixed(2).padStart(5), `${(swept * 100).toFixed(1)}%`.padStart(7), tip.toFixed(1).padStart(7), `${(flick * 100).toFixed(1)}%`.padStart(8), " " + verdict);
  }
}
