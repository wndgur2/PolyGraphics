/**
 * What `check` holds the library to, beyond the schema: the palette, the
 * namespace, the grid, and what an ear would catch in a sound. Each lint reads
 * an owner and appends to `issues`; none of them names an app. The rules an
 * app states in its manifest live one module over, in rules.ts, once they
 * exist.
 */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { allSounds, ownerOf, owners, slug, ROOT, type Library, type Owner } from "./apps.js";
import { levelOf } from "./app-schema.js";
import type { Asset, Part } from "./schema.js";
import type { Issue } from "./render.js";
import { compileSound } from "./sound-compile.js";
import { describe, renderPCM } from "./sound-render.js";

const dir = (...p: string[]) => join(ROOT, ...p);

/** Every `$name` reference in an owner's documents, read off the raw text so nothing has to render. */
function refsIn(o: Owner, kind: "assets" | "sounds"): Set<string> {
  const used = new Set<string>();
  const d = dir(o.dir, kind);
  if (!existsSync(d)) return used;
  for (const f of readdirSync(d).filter((f) => f.endsWith(".json")))
    for (const m of readFileSync(join(d, f), "utf8").matchAll(/\$([a-z][a-z0-9_-]*)/gi)) used.add(m[1]);
  return used;
}

/**
 * Palette lint: a color token nothing references is drift waiting to happen.
 * An app's own tokens are held against the app's own documents; the base
 * tokens against the whole library, since they are everybody's. Themes may
 * only override, never introduce.
 */
export function lintPalette(lib: Library, issues: Issue[]): void {
  const usedAnywhere = new Set<string>();
  const heardAnywhere = new Set<string>();
  for (const o of owners(lib)) {
    const used = refsIn(o, "assets");
    for (const u of used) usedAnywhere.add(u);
    for (const name of Object.keys(o.own.colors ?? {}))
      if (!used.has(name))
        issues.push({ level: "warn", where: `${o.dir}/tokens.json`, msg: `color token "$${name}" is unused in ${o.id} — drop it or use it` });
    for (const theme of o.themes) {
      const where = `${o.dir}/themes/${theme.name}.json`;
      for (const name of Object.keys(theme.colors ?? {}))
        if (!(name in o.tokens.colors)) issues.push({ level: "error", where, msg: `overrides unknown color token "$${name}"` });
      for (const name of Object.keys(theme.audio?.pitch ?? {}))
        if (!(name in (o.tokens.audio?.pitch ?? {}))) issues.push({ level: "error", where, msg: `overrides unknown pitch token "$${name}"` });
    }
    // Same rule one table over: a pitch nothing plays is drift waiting to happen.
    const heard = refsIn(o, "sounds");
    for (const h of heard) heardAnywhere.add(h);
    if (o.sounds.size)
      for (const name of Object.keys(o.own.audio?.pitch ?? {}))
        if (!heard.has(name))
          issues.push({ level: "warn", where: `${o.dir}/tokens.json`, msg: `pitch token "$${name}" is unused in ${o.id} — drop it or use it` });
  }
  for (const name of Object.keys(lib.base.colors))
    if (!usedAnywhere.has(name))
      issues.push({ level: "warn", where: "tokens/base.json", msg: `color token "$${name}" is unused by every app — drop it or use it` });
  if (allSounds(lib).length)
    for (const name of Object.keys(lib.base.audio?.pitch ?? {}))
      if (!heardAnywhere.has(name))
        issues.push({ level: "warn", where: "tokens/base.json", msg: `pitch token "$${name}" is unused by every app — drop it or use it` });
}

/** A document's parts, and the parts its variants add — everything that can compose. */
function partsOf(a: Asset): Part[] {
  return [...a.parts, ...Object.values(a.variants ?? {}).flatMap((v) => v.add ?? [])];
}

/** Every document this one composes: `use` parts, and `use` set by a variant patch. */
function usesOf(a: Asset): string[] {
  const out = partsOf(a).flatMap((p) => ("use" in p ? [p.use] : []));
  for (const v of Object.values(a.variants ?? {}))
    for (const [k, val] of Object.entries(v.set ?? {})) if (k.endsWith(".use") && typeof val === "string") out.push(val);
  return out;
}

/**
 * Namespace = directory = bundle. A document's id starts with its owner's id,
 * its category is one the manifest lists, it composes only its own app's
 * documents and core's, and a core document paints with base tokens only —
 * because core knows no app, and an app reaching into another app's documents
 * is the coupling the prefix exists to prevent.
 */
export function lintNamespace(lib: Library, o: Owner, issues: Issue[]): void {
  const level = o.manifest ? levelOf(o.manifest, "namespace") : "error";
  for (const a of o.assets.values()) {
    if (a.why?.namespace) continue;
    if (a.id.split(".")[0] !== o.id)
      issues.push({ level, where: `${o.dir}/assets/${slug(a.id)}.json`, msg: `id "${a.id}" must start with "${o.id}." — namespace = directory = bundle` });
    const cats = o.manifest?.categories;
    if (cats && !cats.includes(a.tags[0]))
      issues.push({ level, where: a.id, msg: `tags[0] "${a.tags[0]}" is not a category of ${o.id} — categories are ${cats.join(", ")}` });
  }
  for (const sd of o.sounds.values())
    if (sd.id.split(".")[0] !== o.id)
      issues.push({ level, where: `${o.dir}/sounds/${slug(sd.id)}.json`, msg: `id "${sd.id}" must start with "${o.id}." — namespace = directory = bundle` });
  for (const a of o.assets.values())
    for (const id of usesOf(a)) {
      if (o.reg.assets.has(id)) continue;
      const other = ownerOf(lib, id);
      if (other && other !== o)
        issues.push({ level: "error", where: a.id, msg: `uses ${id}, which is ${other.id}'s — an app composes its own documents and core's` });
    }
  if (o === lib.core)
    for (const a of o.assets.values())
      for (const m of JSON.stringify(a).matchAll(/\$([a-z][a-z0-9_-]*)/gi))
        if (!(m[1] in lib.base.colors))
          issues.push({ level: "error", where: a.id, msg: `paints $${m[1]} — core documents use base tokens only` });
}

/** The one grid rule the loader used to apply everywhere; an app's rules refine it. */
export function lintGrid(o: Owner, issues: Issue[]): void {
  for (const a of o.assets.values())
    if (a.size[0] % o.tokens.grid || a.size[1] % o.tokens.grid)
      issues.push({ level: "warn", where: a.id, msg: `size ${a.size[0]}×${a.size[1]} is not a multiple of grid ${o.tokens.grid}` });
}

/**
 * What `describe()` is for: the author of these documents cannot hear them, so
 * the properties an ear would catch are asserted instead. Clipping and silence
 * are absolute; loudness consistency is relative, because the bug that actually
 * happens is one sound sitting 20dB off the rest of the set.
 */
export function lintSounds(o: Owner, issues: Issue[]): void {
  const sreg = o.sreg;
  const L = sreg.tokens.audio?.loudness ?? {};
  const anchor = L.anchor ?? -26, band = L.band ?? 4, phoneLoss = L.phoneLoss ?? 6;

  // Declaring a `root` says "this is an instrument, play me". One nobody plays
  // is drift waiting to happen — the same rule as an unused palette token, one
  // table over, and the same reason: it will be retuned by somebody who thinks
  // something depends on it, or left behind by somebody who thinks nothing does.
  const played = new Set<string>();
  for (const sd of sreg.sounds.values())
    for (const v of sd.voices) {
      if ("use" in v) played.add(v.use);
      if ("phrase" in v) played.add(v.phrase.use);
    }
  for (const sd of o.sounds.values())
    if (sd.root !== undefined && !played.has(sd.id))
      issues.push({ level: "warn", where: sd.id, msg: "declares a `root` but nothing composes it — an instrument nobody plays" });

  // A square or sawtooth with no filter is every harmonic to Nyquist: the one
  // timbre this set has had, in two waveforms. Read off the document, not the
  // bake, because the fix is a line in the document. `why` on the voice is the
  // way to keep one on purpose.
  for (const sd of o.sounds.values())
    for (const v of sd.voices) {
      const src = "source" in v ? v.source : "repeat" in v ? v.repeat.of : undefined;
      if (src?.kind === "osc" && (src.wave === "square" || src.wave === "sawtooth") && !("filter" in v && v.filter) && !v.why)
        issues.push({ level: "warn", where: `${sd.id}(${v.id})`, msg: `unfiltered ${src.wave} — every harmonic to Nyquist; add a lowpass, or say \`why\`` });
    }

  const unplaced = new Set<string>();
  for (const sound of o.sounds.values()) {
    const { ir, issues: cissues } = compileSound(sound, sreg);
    issues.push(...cissues);
    const family = sound.tags[1] ?? sound.tags[0];
    const lib = sound.tags[0] === "lib";
    for (const variant of [undefined, ...Object.keys(ir.variants)]) {
      const pcm = renderPCM(ir, { variant });
      const d = describe(pcm);
      const where = variant ? `${ir.id}#${variant}` : ir.id;
      if (d.clipped) issues.push({ level: "warn", where, msg: `clips on ${d.clipped} samples — lower a voice gain` });
      else if (d.truePeakDb > -1)
        issues.push({ level: "warn", where, msg: `true peak ${d.truePeakDb}dBTP — clips between the samples; lower a voice gain` });
      if (d.peak < 0.02) issues.push({ level: "warn", where, msg: `renders essentially silent (peak ${d.peakDb}dBFS)` });
      // 1.5ms is the renderer's declick. A sound that reaches its peak inside
      // it has no onset of its own; an impact is allowed that, nothing else is.
      if (family !== "impact" && d.attackMs <= 1.6)
        issues.push({ level: "warn", where, msg: `attack is the declick (${d.attackMs}ms) — write one: \`adsr.attack\` in seconds` });
      if (!lib && d.phoneLossDb > phoneLoss)
        issues.push({ level: "warn", where, msg: `loses ${d.phoneLossDb}dB on a phone — the low end is carrying this; give it a mid layer` });
      // Library documents are material, not sounds the game triggers; they are
      // checked for clipping and onset, but they have no business setting the
      // level of the set. Variants are not a second sound, so only the base
      // take is held to the family band.
      if (variant || lib || sound.offBand) continue;
      const offset = L[family];
      if (offset === undefined) unplaced.add(family);
      const target = anchor + (offset ?? 0);
      const diff = d.loudnessDb - target;
      if (Math.abs(diff) > band)
        issues.push({
          level: "warn",
          where,
          msg: `${d.loudnessDb}dB K-weighted; "${family}" sits at ${target} ±${band} — ${Math.round(Math.abs(diff))}dB ${diff > 0 ? "over" : "under"}`,
        });
    }
  }
  for (const f of unplaced)
    issues.push({ level: "warn", where: `${o.dir}/tokens.json`, msg: `no audio.loudness offset for family "${f}" — held to the anchor` });
}

