/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §The rasteriser is not the ceiling.
 *
 * Every effect the two references are built from, as the smallest SVG that uses it, rendered by the
 * resvg this repo already bakes through — each beside a control without the effect, so a feature
 * resvg silently ignored would show up as no difference. Each is rendered twice to check the bytes
 * agree. `crispEdges` also reports how many partially covered pixels a circle has with it on.
 *
 *   npx tsx scripts/spikes/resvg-probe.ts
 */
import { Resvg } from "@resvg/resvg-js";
const W = 64;
const wrap = (defs: string, body: string) => `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${W}" viewBox="0 0 ${W} ${W}"><defs>${defs}</defs><rect width="64" height="64" fill="#808080"/>${body}</svg>`;
const base = `<circle cx="32" cy="32" r="18" fill="#d63756"/>`;
const cases = {
  "path cubic + evenodd hole": [wrap("", `<path fill-rule="evenodd" d="M10 32 C10 5 54 5 54 32 C54 59 10 59 10 32 Z M24 32 a8 8 0 1 0 16 0 a8 8 0 1 0 -16 0 Z" fill="#d63756"/>`), wrap("", `<path d="M10 32 C10 5 54 5 54 32 C54 59 10 59 10 32 Z" fill="#d63756"/>`)],
  "feGaussianBlur": [wrap(`<filter id="f"><feGaussianBlur stdDeviation="4"/></filter>`, `<g filter="url(#f)">${base}</g>`), wrap("", base)],
  "feTurbulence+feDisplacementMap": [wrap(`<filter id="f"><feTurbulence type="fractalNoise" baseFrequency="0.15" numOctaves="3" seed="7"/><feDisplacementMap in="SourceGraphic" scale="8" xChannelSelector="R" yChannelSelector="G"/></filter>`, `<g filter="url(#f)">${base}</g>`), wrap("", base)],
  "mix-blend-mode screen": [wrap("", `${base}<rect x="20" y="0" width="12" height="64" fill="#ffd93b" style="mix-blend-mode:screen"/>`), wrap("", `${base}<rect x="20" y="0" width="12" height="64" fill="#ffd93b"/>`)],
  "mix-blend-mode multiply": [wrap("", `${base}<rect x="20" y="0" width="12" height="64" fill="#8fd0ff" style="mix-blend-mode:multiply"/>`), wrap("", `${base}<rect x="20" y="0" width="12" height="64" fill="#8fd0ff"/>`)],
  "mask (gradient luminance)": [wrap(`<linearGradient id="g"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient><mask id="m"><rect width="64" height="64" fill="url(#g)"/></mask>`, `<g mask="url(#m)">${base}</g>`), wrap("", base)],
  "clipPath": [wrap(`<clipPath id="c"><circle cx="32" cy="32" r="18"/></clipPath>`, `${base}<g clip-path="url(#c)"><rect x="0" y="32" width="64" height="32" fill="#191521"/></g>`), wrap("", `${base}<rect x="0" y="32" width="64" height="32" fill="#191521"/>`)],
  "pattern fill": [wrap(`<pattern id="p" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="2" height="2" fill="#191521"/></pattern>`, `<circle cx="32" cy="32" r="18" fill="url(#p)"/>`), wrap("", `<circle cx="32" cy="32" r="18" fill="#191521"/>`)],
  "feMorphology dilate (outline)": [wrap(`<filter id="f"><feMorphology in="SourceAlpha" operator="dilate" radius="2" result="d"/><feFlood flood-color="#10121a"/><feComposite in2="d" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>`, `<g filter="url(#f)">${base}</g>`), wrap("", base)],
  "feColorMatrix": [wrap(`<filter id="f"><feColorMatrix type="saturate" values="0.2"/></filter>`, `<g filter="url(#f)">${base}</g>`), wrap("", base)],
  "feDiffuseLighting (bump)": [wrap(`<filter id="f"><feGaussianBlur in="SourceAlpha" stdDeviation="3" result="h"/><feDiffuseLighting in="h" surfaceScale="4" lighting-color="#fff" result="l"><feDistantLight azimuth="225" elevation="45"/></feDiffuseLighting><feComposite in="l" in2="SourceGraphic" operator="arithmetic" k1="1"/></filter>`, `<g filter="url(#f)">${base}</g>`), wrap("", base)],
  "shape-rendering crispEdges": [wrap("", `<circle cx="32" cy="32" r="18" fill="#d63756" shape-rendering="crispEdges"/>`), wrap("", base)],
  "feDropShadow": [wrap(`<filter id="f"><feDropShadow dx="3" dy="3" stdDeviation="2" flood-color="#000"/></filter>`, `<g filter="url(#f)">${base}</g>`), wrap("", base)],
};
const px = (svg: string) => new Uint8Array(new Resvg(svg).render().pixels);
const results: [string, string][] = [];
for (const [name, [withF, ctl]] of Object.entries(cases)) {
  let a: Uint8Array | undefined, b: Uint8Array | undefined, err: string | undefined;
  try { a = px(withF); b = px(ctl); } catch (e) { err = (e as Error).message; }
  if (err || !a || !b) { results.push([name, "ERROR " + err]); continue; }
  let diff = 0; for (let i = 0; i < a.length; i++) diff += Math.abs(a[i] - b[i]);
  // partially covered pixels, for the crispEdges case
  let partial = 0; for (let i = 0; i < a.length; i += 4) { const r = a[i]; if (r !== 0x80 && r !== 0xd6) partial++; }
  // determinism: render twice
  const again = px(withF); const same = again.length === a.length && again.every((v, i) => v === a![i]);
  results.push([name, `mean|Δ|=${(diff / a.length).toFixed(2)} ${same ? "deterministic" : "NONDETERMINISTIC"}${name.includes("crisp") ? ` partially-covered pixels=${partial}` : ""}`]);
}
for (const [n, r] of results) console.log(n.padEnd(34), r);
// the same count for the anti-aliased control circle
const c = px(cases["shape-rendering crispEdges"][1]); let p = 0; for (let i = 0; i < c.length; i += 4) { const r = c[i]; if (r !== 0x80 && r !== 0xd6) p++; } console.log("control circle, anti-aliased: partially-covered pixels =", p);
