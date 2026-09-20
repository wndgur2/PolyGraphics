/**
 * PolyGraphics CLI.
 *   npm run check      validate + render all + gallery + manifest (the AI entry point)
 *   npm run validate   schema + token lints only
 *   npm run render     out/svg/*.svg + out/manifest.json   (--theme <name>)
 *   npm run gallery    out/gallery.html
 *   npm run wav        out/wav/*.wav — the sound bake, and what `regress` hashes
 *   npm run dist       dist/assets.json + dist/sounds.json — the bundles consumers import
 *   npm run png        out/png/*.png at 4x   (--only <asset id>, --size <px>)
 *
 * Documents live per app under apps/<id>/ (and shared ones under core/); the
 * loader in apps.ts knows which is whose. Everything written to out/ is flat,
 * because ids are unique across the library by construction.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { allAssets, allSounds, appFlag, appNamed, loadLibrary, owners, slug, themeNamed, ROOT, type Library, type Owner } from "./apps.js";
import { lintNamespace, lintPalette, lintSounds, lintVoice } from "./lint.js";
import { layerOf, lintRules } from "./rules.js";
import { applyVariant, derivedRadius, renderSVG, type Issue } from "./render.js";
import { applyTheme, type Tokens } from "./tokens.js";
import { buildGallery } from "./gallery.js";
import { compileAsset } from "./compile.js";
import { compileSound, type SoundRegistry } from "./sound-compile.js";
import { describe, renderPCM, SAMPLE_RATE, spectrogram, spectrogramRGBA, toWav } from "./sound-render.js";

const dir = (...p: string[]) => join(ROOT, ...p);

/**
 * Stamped into dist/assets.json so a consumer can refuse a bundle it doesn't
 * understand instead of failing later as a wrong-looking sprite. Bump it when
 * the IR shape changes in a way that would break one.
 */
const BUNDLE_FORMAT = "polygraphics-bundle@1";
const SOUND_FORMAT = "polygraphics-sounds@1";

function fail(msg: string): never {
  console.error(`✖ ${msg}`);
  process.exit(1);
}

/** Render everything once (all variants, all themes) purely to harvest issues. */
function dryRun(o: Owner, issues: Issue[]): void {
  for (const asset of o.assets.values()) {
    issues.push(...renderSVG(asset, o.reg).issues);
    for (const [v, patch] of Object.entries(asset.variants ?? {})) {
      issues.push(...renderSVG(asset, o.reg, { variant: v }).issues);
      // A state against the clips it says it is drawn for. Neither of the two
      // passes around this one covers that combination, so a pairing could name
      // a part its own variant had removed and nothing would say so until the
      // gallery drew it.
      for (const anim of patch.animations ?? [])
        issues.push(...renderSVG(asset, o.reg, { variant: v, animation: anim }).issues);
    }
    for (const anim of Object.keys(asset.animations ?? {}))
      issues.push(...renderSVG(asset, o.reg, { animation: anim }).issues);
  }
  for (const theme of o.themes) {
    const treg = { assets: o.reg.assets, tokens: applyTheme(o.tokens, theme) };
    for (const asset of o.assets.values()) issues.push(...renderSVG(asset, treg).issues);
  }
}

function report(issues: Issue[]): { errors: number; warns: number } {
  const seen = new Set<string>();
  let errors = 0, warns = 0;
  for (const i of issues) {
    const key = `${i.level}|${i.where}|${i.msg}`;
    if (seen.has(key)) continue;
    seen.add(key);
    if (i.level === "error") errors++;
    else warns++;
    console.log(`${i.level === "error" ? "✖" : "▲"} ${i.where}: ${i.msg}`);
  }
  return { errors, warns };
}

function writeRenders(o: Owner, tokens: Tokens = o.tokens, themeName?: string): number {
  const sub = themeName ? join("out", "svg", `theme-${themeName}`) : join("out", "svg");
  mkdirSync(dir(sub), { recursive: true });
  const reg = { assets: o.reg.assets, tokens };
  let n = 0;
  for (const asset of o.assets.values()) {
    const fileId = slug(asset.id);
    writeFileSync(dir(sub, `${fileId}.svg`), renderSVG(asset, reg).svg);
    n++;
    for (const v of Object.keys(asset.variants ?? {})) {
      writeFileSync(dir(sub, `${fileId}--${v}.svg`), renderSVG(asset, reg, { variant: v }).svg);
      n++;
    }
  }
  return n;
}

function writeCompiled(o: Owner, tokens: Tokens = o.tokens, themeName?: string): number {
  const sub = themeName ? join("out", "compiled", `theme-${themeName}`) : join("out", "compiled");
  mkdirSync(dir(sub), { recursive: true });
  const reg = { assets: o.reg.assets, tokens };
  let n = 0;
  for (const asset of o.assets.values()) {
    const { ir } = compileAsset(asset, reg);
    writeFileSync(dir(sub, `${slug(asset.id)}.json`), JSON.stringify(ir));
    n++;
  }
  return n;
}

function writeSoundIR(o: Owner): number {
  if (o.sounds.size === 0) return 0;
  mkdirSync(dir("out", "sounds"), { recursive: true });
  let n = 0;
  for (const sound of o.sounds.values()) {
    const { ir } = compileSound(sound, o.sreg);
    writeFileSync(dir("out", "sounds", `${slug(sound.id)}.json`), JSON.stringify(ir));
    n++;
  }
  return n;
}

/** Every sound, every variant, baked — keyed the way the PNG bake is. */
type Take = { wav: Buffer; d: ReturnType<typeof describe>; pcm: Float32Array };
function renderAllWavs(sreg: SoundRegistry, sounds = sreg.sounds): Map<string, Take> {
  const out = new Map<string, Take>();
  for (const sound of sounds.values()) {
    const { ir } = compileSound(sound, sreg);
    const fileId = slug(sound.id);
    for (const variant of [undefined, ...Object.keys(ir.variants)]) {
      const pcm = renderPCM(ir, { variant });
      out.set(`${fileId}${variant ? `--${variant}` : ""}.wav`, { wav: toWav(pcm), d: describe(pcm), pcm });
    }
  }
  return out;
}

function renderLibraryWavs(lib: Library): Map<string, Take> {
  const out = new Map<string, Take>();
  for (const o of owners(lib)) for (const [k, v] of renderAllWavs(o.sreg, o.sounds)) out.set(k, v);
  return out;
}

/**
 * One spectrogram per take, beside the WAV. The gallery draws it under the
 * waveform and the manifest points at it: the one picture that shows whether
 * a voice is a comb or a wash, and whether its top half is empty.
 */
async function writeSpectrograms(takes: Map<string, Take>): Promise<number> {
  const { PNG } = await import("pngjs");
  mkdirSync(dir("out", "spec"), { recursive: true });
  for (const [name, { pcm }] of takes) {
    const s = spectrogram(pcm);
    const png = new PNG({ width: s.width, height: s.height });
    png.data = Buffer.from(spectrogramRGBA(s));
    writeFileSync(dir("out", "spec", name.replace(/\.wav$/, ".png")), PNG.sync.write(png));
  }
  return takes.size;
}

function writeManifest(lib: Library): void {
  const entries = allAssets(lib).map(([o, a]) => {
    // What a document draws over, by its app's `layers` rule: the name, and
    // the depth `tokens.layers` gives it. The first thing that reads the
    // layer table — a game may set a rig's depth from it, or not; that is
    // the game's decision.
    const layer = layerOf(o.manifest, a);
    return {
      id: a.id,
      app: o.id,
      file: `svg/${slug(a.id)}.svg`,
      name: a.name,
      description: a.description,
      tags: a.tags,
      size: a.size,
      anchor: a.anchor ?? [0.5, 0.5],
      meta: { ...a.meta, radius: derivedRadius(a, o.reg) },
      ...(layer ? { layer, depth: o.tokens.layers[layer] } : {}),
      parts: a.parts.map((p) => p.id),
      variants: Object.keys(a.variants ?? {}),
      animations: Object.keys(a.animations ?? {}),
    };
  });
  // Sounds carry their measurements: an index an agent can read is the closest
  // thing to listening it has.
  const sounds = allSounds(lib).map(([o, sd]) => {
    const { ir } = compileSound(sd, o.sreg);
    return {
      id: sd.id,
      app: o.id,
      file: `wav/${slug(sd.id)}.wav`,
      spec: `spec/${slug(sd.id)}.png`,
      name: sd.name,
      description: sd.description,
      tags: sd.tags,
      duration: sd.duration,
      meta: { ...sd.meta },
      voices: sd.voices.map((v) => v.id),
      variants: Object.keys(sd.variants ?? {}),
      measured: describe(renderPCM(ir)),
    };
  });
  // Each app's premise, voice and reference floors ride at the top, so an
  // agent that reads the manifest before it draws reads how to draw first.
  const apps = Object.fromEntries(
    lib.apps
      .filter((o) => o.manifest)
      .map((o) => [o.id, { name: o.manifest!.name, premise: o.manifest!.premise, voice: o.manifest!.voice, instructions: o.manifest!.instructions, reference: o.manifest!.reference }]),
  );
  writeFileSync(dir("out", "manifest.json"), JSON.stringify({ generated: "polygraphics v0", apps, entries, sounds }, null, 2));
}

// ------------------------------------------------------------------ main

const [cmd = "check", ...rest] = process.argv.slice(2);
const themeFlag = rest.includes("--theme") ? rest[rest.indexOf("--theme") + 1] : undefined;
const onlyFlag = rest.includes("--only") ? rest[rest.indexOf("--only") + 1] : undefined;
const sizeFlag = rest.includes("--size") ? Number(rest[rest.indexOf("--size") + 1]) : undefined;
if (sizeFlag !== undefined && !Number.isFinite(sizeFlag)) fail("--size takes a pixel width, e.g. --size 512");
/** `--app <id>` narrows a bake — png, baseline, regress — to one app. Checks and bundles always cover the library. */
const appOnly = appFlag(rest);

const lib = loadLibrary();
const { issues } = lib;
const all = owners(lib);
const nAssets = allAssets(lib).length;
const nSounds = allSounds(lib).length;
const nThemes = all.reduce((n, o) => n + o.themes.length, 0);

if (cmd === "validate" || cmd === "check") {
  for (const o of all) {
    lintNamespace(lib, o, issues);
    lintVoice(o, issues);
    lintRules(o, issues);
    dryRun(o, issues);
    lintSounds(o, issues);
  }
  lintPalette(lib, issues);
}

// variant-applied documents also get schema-checked during dryRun via applyVariant
void applyVariant;

const { errors, warns } = report(issues);

if (cmd === "validate") {
  console.log(`\n${nAssets} assets, ${nSounds} sounds, ${nThemes} themes, ${lib.apps.length} apps — ${errors} errors, ${warns} warnings`);
  process.exit(errors ? 1 : 0);
}

if (errors) {
  console.log(`\n✖ ${errors} errors — fix them, then re-run. Nothing written.`);
  process.exit(1);
}

if (cmd === "render" || cmd === "compile" || cmd === "check") {
  mkdirSync(dir("out"), { recursive: true });
  if (cmd !== "compile") {
    let n = 0;
    if (themeFlag) {
      const t = themeNamed(lib, themeFlag) ?? fail(`unknown theme "${themeFlag}"`);
      n = writeRenders(t.owner, applyTheme(t.owner.tokens, t.theme), themeFlag);
    } else {
      for (const o of all) {
        n += writeRenders(o);
        for (const t of o.themes) writeRenders(o, applyTheme(o.tokens, t), t.name);
      }
    }
    console.log(`✓ rendered ${n} svg files → out/svg`);
  }
  let c = 0, sc = 0;
  for (const o of all) {
    c += writeCompiled(o);
    for (const t of o.themes) writeCompiled(o, applyTheme(o.tokens, t), t.name);
    sc += writeSoundIR(o);
  }
  writeManifest(lib);
  console.log(`✓ compiled ${c} IR files → out/compiled${sc ? `, ${sc} sound IR → out/sounds` : ""}, manifest → out/manifest.json`);
}

if (cmd === "gallery" || cmd === "check") {
  mkdirSync(dir("out"), { recursive: true });
  // The gallery links the bake rather than embedding it, so writing one means
  // writing the other; `npm run gallery` alone must not leave dead play buttons.
  if (nSounds) {
    mkdirSync(dir("out", "wav"), { recursive: true });
    for (const [name, { wav }] of renderLibraryWavs(lib)) writeFileSync(dir("out", "wav", name), wav);
  }
  const galleryIssues: Issue[] = [];
  writeFileSync(dir("out", "gallery.html"), buildGallery(lib, galleryIssues));
  console.log(`✓ gallery → out/gallery.html`);
}

/**
 * The published artifact: every asset's IR in one file, keyed by asset id.
 *
 * `out/` is a scratch directory a consumer never reads — this is the one thing
 * that leaves the repo, so it is committed rather than ignored, and a game
 * imports it as `polygraphics/assets` instead of running a script that writes
 * into its own source tree.
 *
 * Keyed by canonical id (`ss.icon.mine`), never by any game's texture key:
 * what a consumer calls its textures is the consumer's business, and it maps
 * them on its own side.
 */
/**
 * Prose is for whoever reads the documents — it never leaves with them.
 *
 * `name`, `description`, `tags` and `why` are the authoring layer: they make
 * an asset legible in the gallery, the manifest and the document itself, which
 * is the premise of the whole repo. No engine adapter declares them (see
 * `IRAsset`), no consumer reads them, and they are 12% of what a game downloads.
 *
 * Keeping them out of the bundle also keeps a boundary honest. A description
 * that ships is a description someone will write against the game reading it —
 * naming a weapon the way that game's UI names it — and then this repo owes an
 * edit every time the game renames something it merely draws.
 */
function stripProse(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stripProse);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([k]) => k !== "name" && k !== "description" && k !== "tags" && k !== "why")
        .map(([k, v]) => [k, stripProse(v)]),
    );
  return value;
}

/**
 * Sorted and timestamp-free, so the same documents always produce the same
 * bytes; one line per document, so a committed re-bundle diffs as the handful
 * that actually changed rather than as one 300KB line.
 */
function writeBundle(path: string, format: string, key: "assets" | "sounds", rows: [string, unknown][]): number {
  const lines = rows.sort(([a], [b]) => a.localeCompare(b)).map(([id, ir]) => `${JSON.stringify(id)}:${JSON.stringify(stripProse(ir))}`);
  writeFileSync(dir(path), `{"format":${JSON.stringify(format)},"${key}":{\n${lines.join(",\n")}\n}}\n`);
  return lines.length;
}

if (cmd === "dist" || cmd === "check") {
  // One bundle per app — `polygraphics/apps/<id>/assets` — because an app
  // imports its own art and nobody else's. The union at dist/assets.json is
  // what today's consumer imports and keeps building until it has moved;
  // dropping it is a change the game makes first.
  const assetRows = (o: Owner): [string, unknown][] => [...o.assets.values()].map((a) => [a.id, compileAsset(a, o.reg).ir]);
  const soundRows = (o: Owner): [string, unknown][] => [...o.sounds.values()].map((sd) => [sd.id, compileSound(sd, o.sreg).ir]);
  const written: string[] = [];
  for (const o of all) {
    mkdirSync(dir("dist", o.id), { recursive: true });
    const n = writeBundle(`dist/${o.id}/assets.json`, BUNDLE_FORMAT, "assets", assetRows(o));
    written.push(`dist/${o.id}/assets.json (${n})`);
    if (o.sounds.size) written.push(`dist/${o.id}/sounds.json (${writeBundle(`dist/${o.id}/sounds.json`, SOUND_FORMAT, "sounds", soundRows(o))})`);
  }
  const n = writeBundle("dist/assets.json", BUNDLE_FORMAT, "assets", all.flatMap(assetRows));
  console.log(`✓ ${n} assets → dist/assets.json, the union (${BUNDLE_FORMAT})`);
  if (nSounds) console.log(`✓ ${writeBundle("dist/sounds.json", SOUND_FORMAT, "sounds", all.flatMap(soundRows))} sounds → dist/sounds.json, the union (${SOUND_FORMAT})`);
  console.log(`✓ per app: ${written.join(", ")}`);
}

if (cmd === "wav" || cmd === "check") {
  if (nSounds) {
    const wavs = renderLibraryWavs(lib);
    mkdirSync(dir("out", "wav"), { recursive: true });
    for (const [name, { wav }] of wavs) writeFileSync(dir("out", "wav", name), wav);
    const specs = await writeSpectrograms(wavs);
    console.log(`✓ baked ${wavs.size} wav files → out/wav (${SAMPLE_RATE}Hz mono), ${specs} spectrograms → out/spec`);
    if (cmd === "wav")
      for (const [name, { d }] of wavs)
        console.log(
          `  ${name.padEnd(28)} ${String(d.duration).padStart(5)}s  loud ${String(d.loudnessDb).padStart(6)}dB  rms ${String(d.rmsDb).padStart(6)}dB  peak ${String(d.truePeakDb).padStart(6)}dBTP  atk ${String(d.attackMs).padStart(6)}ms  phone -${String(d.phoneLossDb).padStart(4)}dB  ${String(d.centroidHz).padStart(5)}Hz`,
        );
  } else if (cmd === "wav") {
    console.log("no sound documents to bake");
  }
}

// ---- png / baseline / regress (rasterization is optional tooling, deps loaded lazily)

/**
 * `only` bakes a single document (and its variants) instead of the library, and
 * `size` bakes it to an exact pixel width rather than the fixed 4x — which is
 * what an app icon needs, since a launcher asks for 512 and 192 and not for
 * "four times whatever the document was authored at". Both are `png` only: the
 * baselines are a hash of the whole library at one scale, so neither flag is
 * ever in a position to move them.
 *
 * Bakes are keyed by owner, because each owner keeps its own baselines.
 */
async function renderAllPngs(opts: { only?: string; size?: number } = {}): Promise<Map<Owner, Map<string, Buffer>>> {
  const { Resvg } = await import("@resvg/resvg-js");
  const out = new Map<Owner, Map<string, Buffer>>();
  if (opts.only && !allAssets(lib).some(([, a]) => a.id === opts.only)) fail(`--only "${opts.only}": no such asset`);
  for (const o of baked) {
    const pngs = new Map<string, Buffer>();
    for (const asset of o.assets.values()) {
      if (opts.only && asset.id !== opts.only) continue;
      const fileId = slug(asset.id);
      const variants: (string | undefined)[] = [undefined, ...Object.keys(asset.variants ?? {})];
      for (const v of variants) {
        const { svg } = renderSVG(asset, o.reg, { variant: v });
        const scale = 4;
        const fitTo = opts.size ? { mode: "width" as const, value: opts.size } : { mode: "zoom" as const, value: scale };
        const png = new Resvg(svg, { fitTo }).render().asPng();
        pngs.set(`${fileId}${v ? `--${v}` : ""}.png`, Buffer.from(png));
      }
    }
    out.set(o, pngs);
  }
  return out;
}

const baked: Owner[] = appOnly ? [appNamed(lib, appOnly) ?? fail(`--app "${appOnly}": no such app — apps are ${lib.apps.map((a) => a.id).join(", ")}`)] : all;

if (cmd === "png" || cmd === "baseline" || cmd === "regress") {
  const bakes = await renderAllPngs(cmd === "png" ? { only: onlyFlag, size: sizeFlag } : {});
  // Sound rides the same rails: a bake is bytes, and bytes compare.
  if (cmd !== "png")
    for (const o of baked) for (const [name, { wav }] of renderAllWavs(o.sreg, o.sounds)) bakes.get(o)!.set(join("sounds", name), wav);
  if (cmd === "png") {
    mkdirSync(dir("out", "png"), { recursive: true });
    let n = 0;
    for (const pngs of bakes.values()) for (const [name, buf] of pngs) { writeFileSync(dir("out", "png", name), buf); n++; }
    console.log(`✓ ${n} baked files → out/png/`);
  } else if (cmd === "baseline") {
    let n = 0;
    for (const [o, files] of bakes) {
      const sub = join(o.dir, "baselines");
      mkdirSync(dir(sub, "sounds"), { recursive: true });
      for (const [name, buf] of files) { writeFileSync(dir(sub, name), buf); n++; }
    }
    console.log(`✓ ${n} baked files → apps/<id>/baselines/`);
    console.log("  baselines updated — future `npm run regress` compares against these");
  } else {
    let pass = 0, changed = 0, missing = 0;
    for (const [o, files] of bakes)
      for (const [name, buf] of files) {
        let base: Buffer;
        try {
          base = readFileSync(dir(o.dir, "baselines", name));
        } catch {
          console.log(`? ${o.id}: ${name}: no baseline (run \`npm run baseline\` to accept)`);
          missing++;
          continue;
        }
        if (base.equals(buf)) pass++;
        else {
          console.log(`✖ ${o.id}: ${name}: differs from baseline`);
          changed++;
        }
      }
    console.log(`\nregression${appOnly ? ` (${appOnly})` : ""}: ${pass} unchanged, ${changed} changed, ${missing} new`);
    if (changed) process.exit(1);
  }
}

if (cmd === "check")
  console.log(`\n✓ ${nAssets} assets, ${nSounds} sounds, ${nThemes} themes, ${lib.apps.length} apps, ${warns} warnings, 0 errors`);

if (!["check", "validate", "render", "compile", "gallery", "dist", "wav", "png", "baseline", "regress"].includes(cmd))
  fail(`unknown command "${cmd}"`);
