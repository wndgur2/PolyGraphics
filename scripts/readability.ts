/**
 * Field-readability lint. A sprite that a player has to pick out of a crowd at
 * minute 13 is judged by its contrast against the floor, not by how nice it
 * looks alone — so measure that, per asset, the same way every time.
 *
 *   npx tsx scripts/readability.ts                    # every body of the first app, on its floor
 *   npx tsx scripts/readability.ts --app ss           # …of a named app
 *   npx tsx scripts/readability.ts ss.enemy.imp ss.char.dot
 *   npx tsx scripts/readability.ts --ground ss.env.pan   # judged on the pan's floor
 *
 * Reports, against the mean colour of the ground tile (`--ground <id>`; by
 * default the first floor the app's manifest names under `reference.ground`,
 * with the thresholds `reference.contrast` states):
 *   contrast  WCAG-style ratio of mean sprite luminance vs mean ground luminance
 *             (a body darker than the floor is also shown against the most the
 *             floor allows the dark side — pure black — which on a mid-luminance
 *             floor like the pan's is barely over the threshold)
 *   bright%   share of opaque pixels above 0.18 luminance — the focal points
 *   cover%    share of the canvas the sprite actually fills
 */
import { Resvg } from "@resvg/resvg-js";
import { renderSVG } from "../src/render.js";
import { appFlag, appNamed, loadLibrary, ownerOf } from "../src/apps.js";
import { categoryOf } from "../src/app-schema.js";

const lib = loadLibrary();
const argv = process.argv.slice(2);
const gi = argv.indexOf("--ground");
const ai = argv.indexOf("--app");
const positional = argv.filter((a, i) => !a.startsWith("--") && i !== gi + 1 && i !== ai + 1);
// Which app: named, or the one that owns the first id given, or the first there is.
const app = appNamed(lib, appFlag(argv)) ?? (positional.length ? ownerOf(lib, positional[0]) : undefined) ?? lib.apps[0];
if (!app) throw new Error("no app to judge");
const reg = app.reg;
const assets = reg.assets;
const ref = app.manifest?.reference;

/** sRGB → relative luminance, per WCAG. */
function luminance(r: number, g: number, b: number): number {
  const f = (v: number): number => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}

const contrast = (a: number, b: number): number => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);

interface Stats { mean: [number, number, number]; lum: number; bright: number; cover: number }

function measure(id: string): Stats | null {
  const asset = assets.get(id);
  if (!asset) return null;
  const { svg } = renderSVG(asset, reg);
  const png = new Resvg(svg, { fitTo: { mode: "zoom", value: 2 } }).render();
  const { pixels, width, height } = { pixels: png.asPng(), width: png.width, height: png.height };
  // decode via resvg's raw RGBA buffer instead of the PNG bytes
  const raw = new Resvg(svg, { fitTo: { mode: "zoom", value: 2 } }).render().pixels;
  void pixels;
  let r = 0, g = 0, b = 0, n = 0, bright = 0;
  for (let i = 0; i < raw.length; i += 4) {
    const a = raw[i + 3];
    if (a < 128) continue;
    r += raw[i]; g += raw[i + 1]; b += raw[i + 2];
    if (luminance(raw[i], raw[i + 1], raw[i + 2]) > 0.18) bright++;
    n++;
  }
  if (!n) return null;
  const mean: [number, number, number] = [r / n, g / n, b / n];
  return {
    mean,
    lum: luminance(mean[0], mean[1], mean[2]),
    bright: bright / n,
    cover: n / (width * height),
  };
}

// Which floor to judge against. The field's is the default because most of the
// roster stands on it, but a body is only readable on the ground it spawns on:
// the pan's household never sees `ss.env.ground`, and the pan's floor is the
// bright one, so measuring it there is the only measurement that means anything.
//   npx tsx scripts/readability.ts --ground ss.env.pan ss.enemy.antlion
const groundId = gi >= 0 ? argv[gi + 1] : Object.values(ref?.ground ?? {})[0];
if (!groundId) throw new Error(`${app.id} names no reference.ground in its manifest — pass --ground <id>`);
const ground = measure(groundId);
if (!ground) throw new Error(`${groundId} failed to render`);
const sinks = ref?.contrast?.sinks ?? 2.5, thin = ref?.contrast?.thin ?? 3.5;

// The bodies the floor has to carry: what stands on it and what is picked up off it.
const BODIES = new Set(["char", "enemy", "pickup"]);
const bare = (cat: string) => (cat.startsWith(`${app.id}-`) ? cat.slice(app.id.length + 1) : cat);
const targets = positional.length
  ? positional
  : [...app.assets.values()].filter((a) => BODIES.has(bare(categoryOf(a)))).map((a) => a.id).sort();

// A floor at mid luminance caps the dark side: a body darker than it can reach
// at most the ratio pure black would, and on the pan's sand that is barely
// over `sinks`. Such a body is reported against that cap rather than left to
// read as a failure it cannot fix by going darker — its choice is to go light,
// or to be read by what is bright on it (a sac, a rim, a pair of jaws).
const darkCap = contrast(0, ground.lum);
console.log(
  `${groundId} mean rgb(${ground.mean.map((v) => Math.round(v)).join(",")}) luminance ${ground.lum.toFixed(4)}` +
    ` · a body darker than it tops out at ${darkCap.toFixed(2)}\n`,
);
console.log("asset                 contrast  bright%  cover%   mean");
console.log("─".repeat(64));

const rows: { id: string; c: number; dark: boolean }[] = [];
for (const id of targets) {
  const s = measure(id);
  if (!s) { console.log(`${id.padEnd(21)} — no opaque pixels`); continue; }
  const c = contrast(s.lum, ground.lum);
  const dark = s.lum < ground.lum;
  rows.push({ id, c, dark });
  const capped = dark && darkCap < thin ? ` (dark: ${Math.round((c / darkCap) * 100)}% of the ${darkCap.toFixed(2)} this floor allows)` : "";
  const flag = (c < sinks ? "  ← sinks into the floor" : c < thin ? "  ← thin" : "") + (c < thin ? capped : "");
  console.log(
    `${id.padEnd(21)} ${c.toFixed(2).padStart(7)}  ${(s.bright * 100).toFixed(0).padStart(6)}%  ` +
      `${(s.cover * 100).toFixed(0).padStart(5)}%   rgb(${s.mean.map((v) => Math.round(v)).join(",")})${flag}`,
  );
}

const weak = rows.filter((r) => r.c < sinks);
console.log(
  `\n${rows.length} assets · median contrast ${rows.map((r) => r.c).sort((a, b) => a - b)[Math.floor(rows.length / 2)].toFixed(2)}` +
    ` · ${weak.length} below ${sinks}`,
);
if (weak.length) console.log(`weak: ${weak.map((r) => r.id).join(", ")}`);
const capped = weak.filter((r) => r.dark && darkCap < sinks + 0.5);
if (capped.length)
  console.log(`of which darker than a floor that caps them at ${darkCap.toFixed(2)}: ${capped.map((r) => r.id).join(", ")}`);
