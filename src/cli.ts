/**
 * PolyGraphics CLI.
 *   npm run check      validate + render all + gallery + manifest (the AI entry point)
 *   npm run validate   schema + token lints only
 *   npm run render     out/svg/*.svg + out/manifest.json   (--theme <name>)
 *   npm run gallery    out/gallery.html
 *   npm run wav        out/wav/*.wav — the sound bake, and what `regress` hashes
 *   npm run dist       dist/assets.json + dist/sounds.json — the bundles consumers import
 */
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, basename } from "node:path";
import { AssetSchema, type Asset } from "./schema.js";
import { applyVariant, derivedRadius, renderSVG, type Issue, type Registry } from "./render.js";
import { applyTheme, type Theme, type Tokens } from "./tokens.js";
import { buildGallery } from "./gallery.js";
import { compileAsset } from "./compile.js";
import { SoundSchema, type Sound } from "./sound-schema.js";
import { compileSound, type SoundRegistry } from "./sound-compile.js";
import { describe, renderPCM, SAMPLE_RATE, toWav } from "./sound-render.js";

const ROOT = new URL("..", import.meta.url).pathname;
const dir = (...p: string[]) => join(ROOT, ...p);

/**
 * Stamped into dist/assets.json so a consumer can refuse a bundle it doesn't
 * understand instead of failing later as a wrong-looking sprite. Bump it when
 * the IR shape changes in a way that would break one.
 */
const BUNDLE_FORMAT = "polygraphics-bundle@1";
const SOUND_FORMAT = "polygraphics-sounds@1";

function readJson(path: string): unknown {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    fail(`${path}: not valid JSON — ${(e as Error).message}`);
  }
}

function fail(msg: string): never {
  console.error(`✖ ${msg}`);
  process.exit(1);
}

function loadAll(): { reg: Registry; sreg: SoundRegistry; themes: Theme[]; issues: Issue[] } {
  const issues: Issue[] = [];
  const tokens = readJson(dir("tokens", "default.json")) as Tokens;
  for (const key of ["grid", "colors", "ramps", "strokes", "alpha", "layers"])
    if (!(key in (tokens as object))) fail(`tokens/default.json: missing "${key}"`);

  const themes: Theme[] = [];
  try {
    for (const f of readdirSync(dir("themes")).filter((f) => f.endsWith(".json")))
      themes.push(readJson(dir("themes", f)) as Theme);
  } catch { /* themes/ is optional */ }

  const assets = new Map<string, Asset>();
  const files = readdirSync(dir("assets")).filter((f) => f.endsWith(".json"));
  if (files.length === 0) fail("assets/: no .json asset documents found");
  for (const f of files) {
    const raw = readJson(dir("assets", f));
    const parsed = AssetSchema.safeParse(raw);
    if (!parsed.success) {
      for (const iss of parsed.error.issues)
        issues.push({ level: "error", where: `assets/${f}`, msg: `${iss.path.join(".") || "(root)"}: ${iss.message}` });
      continue;
    }
    const a = parsed.data;
    if (assets.has(a.id)) issues.push({ level: "error", where: `assets/${f}`, msg: `duplicate asset id "${a.id}"` });
    const expectFile = a.id.replace(/\./g, "-") + ".json";
    if (basename(f) !== expectFile)
      issues.push({ level: "warn", where: `assets/${f}`, msg: `file name should match id: "${expectFile}"` });
    if (a.size[0] % tokens.grid || a.size[1] % tokens.grid)
      issues.push({ level: "warn", where: a.id, msg: `size ${a.size[0]}×${a.size[1]} is not a multiple of grid ${tokens.grid}` });
    assets.set(a.id, a);
  }

  // sounds/ is optional: a repo may be all art and no audio, and that is not an error.
  const sounds = new Map<string, Sound>();
  let soundFiles: string[] = [];
  try {
    soundFiles = readdirSync(dir("sounds")).filter((f) => f.endsWith(".json"));
  } catch { /* no sounds/ */ }
  for (const f of soundFiles) {
    const raw = readJson(dir("sounds", f));
    const parsed = SoundSchema.safeParse(raw);
    if (!parsed.success) {
      for (const iss of parsed.error.issues)
        issues.push({ level: "error", where: `sounds/${f}`, msg: `${iss.path.join(".") || "(root)"}: ${iss.message}` });
      continue;
    }
    const sd = parsed.data;
    if (sounds.has(sd.id)) issues.push({ level: "error", where: `sounds/${f}`, msg: `duplicate sound id "${sd.id}"` });
    const expectFile = sd.id.replace(/\./g, "-") + ".json";
    if (basename(f) !== expectFile)
      issues.push({ level: "warn", where: `sounds/${f}`, msg: `file name should match id: "${expectFile}"` });
    if (sounds.size === 0 && !tokens.audio)
      issues.push({ level: "error", where: "tokens/default.json", msg: "sounds/ has documents but tokens has no `audio` section" });
    sounds.set(sd.id, sd);
  }

  return { reg: { assets, tokens }, sreg: { sounds, tokens }, themes, issues };
}

/**
 * Palette lint: a color token nothing references is drift waiting to happen.
 * Scans raw asset text for `$name` refs (themes may only override, never introduce).
 */
function lintPalette(tokens: Tokens, issues: Issue[]): void {
  const used = new Set<string>();
  for (const f of readdirSync(dir("assets")).filter((f) => f.endsWith(".json")))
    for (const m of readFileSync(dir("assets", f), "utf8").matchAll(/\$([a-z][a-z0-9_-]*)/gi))
      used.add(m[1]);
  for (const name of Object.keys(tokens.colors))
    if (!used.has(name))
      issues.push({ level: "warn", where: "tokens/default.json", msg: `color token "$${name}" is unused — drop it or use it` });
  for (const theme of readdirSync(dir("themes")).filter((f) => f.endsWith(".json"))) {
    const t = readJson(dir("themes", theme)) as Theme;
    for (const name of Object.keys(t.colors ?? {}))
      if (!(name in tokens.colors))
        issues.push({ level: "error", where: `themes/${theme}`, msg: `overrides unknown color token "$${name}"` });
    for (const name of Object.keys(t.audio?.pitch ?? {}))
      if (!(name in (tokens.audio?.pitch ?? {})))
        issues.push({ level: "error", where: `themes/${theme}`, msg: `overrides unknown pitch token "$${name}"` });
  }

  // Same rule one table over: a pitch nothing plays is drift waiting to happen.
  if (tokens.audio) {
    const heard = new Set<string>();
    let files: string[] = [];
    try { files = readdirSync(dir("sounds")).filter((f) => f.endsWith(".json")); } catch { /* none */ }
    for (const f of files)
      for (const m of readFileSync(dir("sounds", f), "utf8").matchAll(/\$([a-z][a-z0-9_-]*)/gi)) heard.add(m[1]);
    if (files.length)
      for (const name of Object.keys(tokens.audio.pitch))
        if (!heard.has(name))
          issues.push({ level: "warn", where: "tokens/default.json", msg: `pitch token "$${name}" is unused — drop it or use it` });
  }
}

/**
 * What `describe()` is for: the author of these documents cannot hear them, so
 * the properties an ear would catch are asserted instead. Clipping and silence
 * are absolute; loudness consistency is relative, because the bug that actually
 * happens is one sound sitting 20dB off the rest of the set.
 */
function lintSounds(sreg: SoundRegistry, issues: Issue[]): void {
  // Declaring a `root` says "this is an instrument, play me". One nobody plays
  // is drift waiting to happen — the same rule as an unused palette token, one
  // table over, and the same reason: it will be retuned by somebody who thinks
  // something depends on it, or left behind by somebody who thinks nothing does.
  const played = new Set<string>();
  for (const sd of sreg.sounds.values()) for (const v of sd.voices) if ("use" in v) played.add(v.use);
  for (const sd of sreg.sounds.values())
    if (sd.root !== undefined && !played.has(sd.id))
      issues.push({ level: "warn", where: sd.id, msg: "declares a `root` but nothing composes it — an instrument nobody plays" });

  const levels: { id: string; rmsDb: number }[] = [];
  for (const sound of sreg.sounds.values()) {
    const { ir, issues: cissues } = compileSound(sound, sreg);
    issues.push(...cissues);
    if (cissues.some((i) => i.level === "error")) continue;
    for (const variant of [undefined, ...Object.keys(ir.variants)]) {
      const where = variant ? `${ir.id}#${variant}` : ir.id;
      const d = describe(renderPCM(ir, { variant }));
      if (d.clipped)
        issues.push({ level: "warn", where, msg: `clips on ${d.clipped} samples — lower a voice gain` });
      if (d.peak < 0.01)
        issues.push({ level: "warn", where, msg: `renders essentially silent (peak ${d.peakDb}dBFS)` });
      // Library documents are material, not sounds the game triggers; they are
      // still checked for clipping, but they have no business setting the level
      // the triggered set is compared against. Nor does a document that has
      // said in writing why it sits outside it.
      if (!variant && sound.tags[0] !== "lib" && !sound.offBand) levels.push({ id: ir.id, rmsDb: d.rmsDb });
    }
  }
  if (levels.length < 3) return; // a median of two says nothing
  const sorted = [...levels].sort((a, b) => a.rmsDb - b.rmsDb);
  const median = sorted[Math.floor(sorted.length / 2)].rmsDb;
  for (const l of levels)
    if (Math.abs(l.rmsDb - median) > 9)
      issues.push({
        level: "warn",
        where: l.id,
        msg: `${Math.round(l.rmsDb - median)}dB from the set median (${median}dBFS) — it will stand out`,
      });
}

/** Render everything once (all variants, all themes) purely to harvest issues. */
function dryRun(reg: Registry, themes: Theme[], issues: Issue[]): void {
  for (const asset of reg.assets.values()) {
    issues.push(...renderSVG(asset, reg).issues);
    for (const [v, patch] of Object.entries(asset.variants ?? {})) {
      issues.push(...renderSVG(asset, reg, { variant: v }).issues);
      // A state against the clips it says it is drawn for. Neither of the two
      // passes around this one covers that combination, so a pairing could name
      // a part its own variant had removed and nothing would say so until the
      // gallery drew it.
      for (const anim of patch.animations ?? [])
        issues.push(...renderSVG(asset, reg, { variant: v, animation: anim }).issues);
    }
    for (const anim of Object.keys(asset.animations ?? {}))
      issues.push(...renderSVG(asset, reg, { animation: anim }).issues);
  }
  for (const theme of themes) {
    const treg = { assets: reg.assets, tokens: applyTheme(reg.tokens, theme) };
    for (const asset of reg.assets.values()) issues.push(...renderSVG(asset, treg).issues);
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

function writeRenders(reg: Registry, themeName?: string): number {
  const sub = themeName ? join("out", "svg", `theme-${themeName}`) : join("out", "svg");
  mkdirSync(dir(sub), { recursive: true });
  let n = 0;
  for (const asset of reg.assets.values()) {
    const fileId = asset.id.replace(/\./g, "-");
    writeFileSync(dir(sub, `${fileId}.svg`), renderSVG(asset, reg).svg);
    n++;
    for (const v of Object.keys(asset.variants ?? {})) {
      writeFileSync(dir(sub, `${fileId}--${v}.svg`), renderSVG(asset, reg, { variant: v }).svg);
      n++;
    }
  }
  return n;
}

function writeCompiled(reg: Registry, themeName?: string): number {
  const sub = themeName ? join("out", "compiled", `theme-${themeName}`) : join("out", "compiled");
  mkdirSync(dir(sub), { recursive: true });
  let n = 0;
  for (const asset of reg.assets.values()) {
    const { ir } = compileAsset(asset, reg);
    writeFileSync(dir(sub, `${asset.id.replace(/\./g, "-")}.json`), JSON.stringify(ir));
    n++;
  }
  return n;
}

function writeSoundIR(sreg: SoundRegistry): number {
  if (sreg.sounds.size === 0) return 0;
  mkdirSync(dir("out", "sounds"), { recursive: true });
  let n = 0;
  for (const sound of sreg.sounds.values()) {
    const { ir } = compileSound(sound, sreg);
    writeFileSync(dir("out", "sounds", `${sound.id.replace(/\./g, "-")}.json`), JSON.stringify(ir));
    n++;
  }
  return n;
}

/** Every sound, every variant, baked — keyed the way the PNG bake is. */
function renderAllWavs(sreg: SoundRegistry): Map<string, { wav: Buffer; d: ReturnType<typeof describe> }> {
  const out = new Map<string, { wav: Buffer; d: ReturnType<typeof describe> }>();
  for (const sound of sreg.sounds.values()) {
    const { ir } = compileSound(sound, sreg);
    const fileId = sound.id.replace(/\./g, "-");
    for (const variant of [undefined, ...Object.keys(ir.variants)]) {
      const pcm = renderPCM(ir, { variant });
      out.set(`${fileId}${variant ? `--${variant}` : ""}.wav`, { wav: toWav(pcm), d: describe(pcm) });
    }
  }
  return out;
}

function writeManifest(reg: Registry, sreg: SoundRegistry): void {
  const entries = [...reg.assets.values()].map((a) => ({
    id: a.id,
    file: `svg/${a.id.replace(/\./g, "-")}.svg`,
    name: a.name,
    description: a.description,
    tags: a.tags,
    size: a.size,
    anchor: a.anchor ?? [0.5, 0.5],
    meta: { ...a.meta, radius: derivedRadius(a, reg) },
    parts: a.parts.map((p) => p.id),
    variants: Object.keys(a.variants ?? {}),
    animations: Object.keys(a.animations ?? {}),
  }));
  // Sounds carry their measurements: an index an agent can read is the closest
  // thing to listening it has.
  const sounds = [...sreg.sounds.values()].map((sd) => {
    const { ir } = compileSound(sd, sreg);
    return {
      id: sd.id,
      file: `wav/${sd.id.replace(/\./g, "-")}.wav`,
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
  writeFileSync(dir("out", "manifest.json"), JSON.stringify({ generated: "polygraphics v0", entries, sounds }, null, 2));
}

// ------------------------------------------------------------------ main

const [cmd = "check", ...rest] = process.argv.slice(2);
const themeFlag = rest.includes("--theme") ? rest[rest.indexOf("--theme") + 1] : undefined;

const { reg, sreg, themes, issues } = loadAll();

if (cmd === "validate" || cmd === "check") {
  dryRun(reg, themes, issues);
  lintPalette(reg.tokens, issues);
  lintSounds(sreg, issues);
}

// variant-applied documents also get schema-checked during dryRun via applyVariant
void applyVariant;

const { errors, warns } = report(issues);

if (cmd === "validate") {
  console.log(`\n${reg.assets.size} assets, ${sreg.sounds.size} sounds, ${themes.length} themes — ${errors} errors, ${warns} warnings`);
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
      const theme = themes.find((t) => t.name === themeFlag) ?? fail(`unknown theme "${themeFlag}"`);
      n = writeRenders({ assets: reg.assets, tokens: applyTheme(reg.tokens, theme) }, themeFlag);
    } else {
      n = writeRenders(reg);
      for (const t of themes) writeRenders({ assets: reg.assets, tokens: applyTheme(reg.tokens, t) }, t.name);
    }
    console.log(`✓ rendered ${n} svg files → out/svg`);
  }
  const c = writeCompiled(reg);
  for (const t of themes) writeCompiled({ assets: reg.assets, tokens: applyTheme(reg.tokens, t) }, t.name);
  const sc = writeSoundIR(sreg);
  writeManifest(reg, sreg);
  console.log(`✓ compiled ${c} IR files → out/compiled${sc ? `, ${sc} sound IR → out/sounds` : ""}, manifest → out/manifest.json`);
}

if (cmd === "gallery" || cmd === "check") {
  mkdirSync(dir("out"), { recursive: true });
  // The gallery links the bake rather than embedding it, so writing one means
  // writing the other; `npm run gallery` alone must not leave dead play buttons.
  if (sreg.sounds.size) {
    mkdirSync(dir("out", "wav"), { recursive: true });
    for (const [name, { wav }] of renderAllWavs(sreg)) writeFileSync(dir("out", "wav", name), wav);
  }
  const galleryIssues: Issue[] = [];
  writeFileSync(dir("out", "gallery.html"), buildGallery(reg, sreg, themes, galleryIssues));
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
 * `name`, `description` and `tags` are the authoring layer: they make an asset
 * legible in the gallery, the manifest and the document itself, which is the
 * premise of the whole repo. No engine adapter declares them (see `IRAsset`),
 * no consumer reads them, and they are 12% of what a game downloads.
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
        .filter(([k]) => k !== "name" && k !== "description" && k !== "tags")
        .map(([k, v]) => [k, stripProse(v)]),
    );
  return value;
}

if (cmd === "dist" || cmd === "check") {
  mkdirSync(dir("dist"), { recursive: true });
  // Sorted and timestamp-free, so the same documents always produce the same
  // bytes; one line per asset, so a committed re-bundle diffs as the handful of
  // assets that actually changed rather than as one 300KB line.
  const rows = [...reg.assets.values()]
    .sort((a, b) => a.id.localeCompare(b.id))
    .map((a) => `${JSON.stringify(a.id)}:${JSON.stringify(stripProse(compileAsset(a, reg).ir))}`);
  writeFileSync(
    dir("dist", "assets.json"),
    `{"format":${JSON.stringify(BUNDLE_FORMAT)},"assets":{\n${rows.join(",\n")}\n}}\n`,
  );
  console.log(`✓ ${rows.length} assets → dist/assets.json (${BUNDLE_FORMAT})`);

  if (sreg.sounds.size) {
    const srows = [...sreg.sounds.values()]
      .sort((a, b) => a.id.localeCompare(b.id))
      .map((sd) => `${JSON.stringify(sd.id)}:${JSON.stringify(stripProse(compileSound(sd, sreg).ir))}`);
    writeFileSync(
      dir("dist", "sounds.json"),
      `{"format":${JSON.stringify(SOUND_FORMAT)},"sounds":{\n${srows.join(",\n")}\n}}\n`,
    );
    console.log(`✓ ${srows.length} sounds → dist/sounds.json (${SOUND_FORMAT})`);
  }
}

if (cmd === "wav" || cmd === "check") {
  if (sreg.sounds.size) {
    const wavs = renderAllWavs(sreg);
    mkdirSync(dir("out", "wav"), { recursive: true });
    for (const [name, { wav }] of wavs) writeFileSync(dir("out", "wav", name), wav);
    console.log(`✓ baked ${wavs.size} wav files → out/wav (${SAMPLE_RATE}Hz mono)`);
    if (cmd === "wav")
      for (const [name, { d }] of wavs)
        console.log(`  ${name.padEnd(28)} ${d.duration}s  peak ${String(d.peakDb).padStart(6)}dB  rms ${String(d.rmsDb).padStart(6)}dB  ${String(d.attackMs).padStart(6)}ms atk  ${d.brightness}Hz zc`);
  } else if (cmd === "wav") {
    console.log("no sounds/ documents to bake");
  }
}

// ---- png / baseline / regress (rasterization is optional tooling, deps loaded lazily)

async function renderAllPngs(): Promise<Map<string, Buffer>> {
  const { Resvg } = await import("@resvg/resvg-js");
  const pngs = new Map<string, Buffer>();
  for (const asset of reg.assets.values()) {
    const fileId = asset.id.replace(/\./g, "-");
    const variants: (string | undefined)[] = [undefined, ...Object.keys(asset.variants ?? {})];
    for (const v of variants) {
      const { svg } = renderSVG(asset, reg, { variant: v });
      const scale = 4;
      const png = new Resvg(svg, { fitTo: { mode: "zoom", value: scale } }).render().asPng();
      pngs.set(`${fileId}${v ? `--${v}` : ""}.png`, Buffer.from(png));
    }
  }
  return pngs;
}

if (cmd === "png" || cmd === "baseline" || cmd === "regress") {
  const pngs = await renderAllPngs();
  // Sound rides the same rails: a bake is bytes, and bytes compare.
  if (cmd !== "png")
    for (const [name, { wav }] of renderAllWavs(sreg)) pngs.set(join("sounds", name), wav);
  if (cmd === "png" || cmd === "baseline") {
    const sub = cmd === "png" ? join("out", "png") : "baselines";
    mkdirSync(dir(sub), { recursive: true });
    mkdirSync(dir(sub, "sounds"), { recursive: true });
    for (const [name, buf] of pngs) writeFileSync(dir(sub, name), buf);
    console.log(`✓ ${pngs.size} baked files → ${sub}/`);
    if (cmd === "baseline") console.log("  baselines updated — future `npm run regress` compares against these");
  } else {
    let pass = 0, changed = 0, missing = 0;
    for (const [name, buf] of pngs) {
      let base: Buffer;
      try {
        base = readFileSync(dir("baselines", name));
      } catch {
        console.log(`? ${name}: no baseline (run \`npm run baseline\` to accept)`);
        missing++;
        continue;
      }
      if (base.equals(buf)) pass++;
      else {
        console.log(`✖ ${name}: differs from baseline`);
        changed++;
      }
    }
    console.log(`\nregression: ${pass} unchanged, ${changed} changed, ${missing} new`);
    if (changed) process.exit(1);
  }
}

if (cmd === "check")
  console.log(`\n✓ ${reg.assets.size} assets, ${sreg.sounds.size} sounds, ${themes.length} themes, ${warns} warnings, 0 errors`);

if (!["check", "validate", "render", "compile", "gallery", "dist", "wav", "png", "baseline", "regress"].includes(cmd))
  fail(`unknown command "${cmd}"`);
