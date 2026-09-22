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
 *   bright%   share of opaque pixels above 0.18 luminance — the focal points
 *   cover%    share of the canvas the sprite actually fills
 *
 * A badge is judged differently, because it is not on a floor: a relic sits on
 * a plate every other relic also wears, and what a player has to pick it out of
 * is the other badges. So each category the manifest names a plate for under
 * `reference.plate` is measured against that plate, pixel against the pixel
 * directly under it, and reported as:
 *   lit%      share of the canvas clearing `contrast.badge` against the plate
 *   peak      the best any one pixel of the object manages
 *   cover%    share of the canvas the object fills with the plate lifted off
 */
import { Resvg } from "@resvg/resvg-js";
import { renderSVG } from "../src/render.js";
import { appFlag, appNamed, loadLibrary, ownerOf } from "../src/apps.js";
import { categoryOf } from "../src/app-schema.js";
import type { Asset } from "../src/schema.js";

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

/** The raw RGBA of an SVG, at the zoom every measurement here uses. */
function rasterize(svg: string): { px: Uint8Array; w: number; h: number } {
  const out = new Resvg(svg, { fitTo: { mode: "zoom", value: 2 } }).render();
  return { px: out.pixels, w: out.width, h: out.height };
}

interface Badge { lit: number; peak: number; cover: number }

/**
 * A plated badge against its own plate.
 *
 * Measured per pixel rather than mean against mean, which is what the floor
 * measurement above can afford and this one cannot: a plate is not one colour.
 * The relic plate bleeds an old light out of its middle, so the same dark brown
 * that reads at the corner is gone over the glow, and only "this pixel against
 * the pixel under it" catches that.
 *
 * The object is the `glyph` variant — the state a plated category already
 * declares so a collection can show an unmet entry as a silhouette — and the
 * plate is exactly what that variant removes, composed the way this document
 * composes it, variant and all. So nothing here has to know how a plate is put
 * together; it only has to know that lifting it off is what `glyph` means.
 */
function measureBadge(id: string, plateId: string): Badge | string {
  const asset = assets.get(id);
  if (!asset) return "no such document";
  const removed = asset.variants?.glyph?.remove ?? [];
  if (!removed.length) return "has no glyph variant, so the plate cannot be lifted off to measure it";
  const under = asset.parts.filter((p) => removed.includes(p.id));
  if (!under.some((p) => "use" in p && p.use === plateId)) return `its glyph variant lifts off no part using ${plateId}`;
  const object = rasterize(renderSVG(asset, reg, { variant: "glyph" }).svg);
  const plate = rasterize(renderSVG({ ...asset, parts: under, variants: undefined } as Asset, reg).svg);
  if (object.w !== plate.w || object.h !== plate.h) return "the glyph variant is not the size of its own plate";
  let lit = 0, peak = 0, n = 0;
  for (let i = 0; i < object.px.length; i += 4) {
    if (object.px[i + 3] < 128) continue;
    n++;
    // Against the plate where it is, not where it averages.
    const c = contrast(
      luminance(object.px[i], object.px[i + 1], object.px[i + 2]),
      luminance(plate.px[i], plate.px[i + 1], plate.px[i + 2]),
    );
    if (c >= badgeFloor) lit++;
    if (c > peak) peak = c;
  }
  const area = object.w * object.h;
  return { lit: lit / area, peak, cover: n / area };
}

// Which floor to judge against. The field's is the default because most of the
// roster stands on it, but a body is only readable on the ground it spawns on:
// the pan's household never sees `ss.env.ground`, and the pan's floor is the
// bright one, so measuring it there is the only measurement that means anything.
//   npx tsx scripts/readability.ts --ground ss.env.pan ss.enemy.antlion
const sinks = ref?.contrast?.sinks ?? 2.5, thin = ref?.contrast?.thin ?? 3.5;
// A badge's two: the ratio one of its pixels has to clear against the plate
// under it to count as read at all, and how much of the badge has to clear it.
// 3:1 is WCAG's floor for a graphic that carries meaning; the share is what
// keeps a document from passing on a single bright speck.
const badgeFloor = ref?.contrast?.badge ?? 3, badgeLit = ref?.contrast?.badgeLit ?? 0.04;

// The bodies the floor has to carry: what stands on it and what is picked up off it.
const BODIES = new Set(["char", "enemy", "pickup"]);
// And the categories that are read on a plate instead of a floor, which the
// manifest names. Both sets are judged in one run: a badge and a body are two
// readings of the same question and there is no reason to ask them apart.
const PLATES = new Map(Object.entries(ref?.plate ?? {}));
const bare = (cat: string) => (cat.startsWith(`${app.id}-`) ? cat.slice(app.id.length + 1) : cat);
const judged = (a: { tags: string[] }): boolean => BODIES.has(bare(categoryOf(a))) || PLATES.has(bare(categoryOf(a)));
const targets = positional.length
  ? positional
  : [...app.assets.values()].filter(judged).map((a) => a.id).sort();
/** The plate a document is read on, if it is read on one. */
const plateOf = (id: string): string | undefined => {
  const a = assets.get(id);
  return a ? PLATES.get(bare(categoryOf(a))) : undefined;
};
const bodies = targets.filter((id) => !plateOf(id));
const badges = targets.filter((id) => plateOf(id));

if (bodies.length) {
  const groundId = gi >= 0 ? argv[gi + 1] : Object.values(ref?.ground ?? {})[0];
  if (!groundId) throw new Error(`${app.id} names no reference.ground in its manifest — pass --ground <id>`);
  const ground = measure(groundId);
  if (!ground) throw new Error(`${groundId} failed to render`);

  console.log(`${groundId} mean rgb(${ground.mean.map((v) => Math.round(v)).join(",")}) luminance ${ground.lum.toFixed(4)}\n`);
  console.log("asset                 contrast  bright%  cover%   mean");
  console.log("─".repeat(64));

  const rows: { id: string; c: number }[] = [];
  for (const id of bodies) {
    const s = measure(id);
    if (!s) { console.log(`${id.padEnd(21)} — no opaque pixels`); continue; }
    const c = contrast(s.lum, ground.lum);
    rows.push({ id, c });
    const flag = c < sinks ? "  ← sinks into the floor" : c < thin ? "  ← thin" : "";
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
}

if (badges.length) {
  console.log(`${bodies.length ? "\n" : ""}badges on their plate — a pixel reads at ${badgeFloor}:1, a badge reads at ${(badgeLit * 100).toFixed(0)}% of its canvas lit\n`);
  console.log("badge                          lit%    peak  cover%");
  console.log("─".repeat(64));

  const rows: { id: string; lit: number }[] = [];
  for (const id of badges) {
    const b = measureBadge(id, plateOf(id)!);
    if (typeof b === "string") { console.log(`${id.padEnd(30)} — ${b}`); continue; }
    rows.push({ id, lit: b.lit });
    // Two ways to be unreadable, and they want different fixes: nothing on the
    // badge clears the plate at all, or something does but there is too little
    // of it. The first is a colour that has to move, the second is an area.
    const flag = b.peak < badgeFloor ? "  ← lost on the plate" : b.lit < badgeLit ? "  ← too little of it reads" : "";
    console.log(
      `${id.padEnd(30)} ${(b.lit * 100).toFixed(1).padStart(5)}%  ${b.peak.toFixed(2).padStart(6)}  ` +
        `${(b.cover * 100).toFixed(0).padStart(5)}%${flag}`,
    );
  }

  const dim = rows.filter((r) => r.lit < badgeLit);
  console.log(
    `\n${rows.length} badges · median ${(rows.map((r) => r.lit).sort((a, b) => a - b)[Math.floor(rows.length / 2)] * 100).toFixed(1)}% lit` +
      ` · ${dim.length} below ${(badgeLit * 100).toFixed(0)}%`,
  );
  if (dim.length) console.log(`dim: ${dim.map((r) => r.id).join(", ")}`);
}
