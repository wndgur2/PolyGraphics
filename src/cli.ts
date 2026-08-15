/**
 * PolyGraphics CLI.
 *   npm run check      validate + render all + gallery + manifest (the AI entry point)
 *   npm run validate   schema + token lints only
 *   npm run render     out/svg/*.svg + out/manifest.json   (--theme <name>)
 *   npm run gallery    out/gallery.html
 */
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, basename } from "node:path";
import { AssetSchema, type Asset } from "./schema.js";
import { applyVariant, derivedRadius, renderSVG, type Issue, type Registry } from "./render.js";
import { applyTheme, type Theme, type Tokens } from "./tokens.js";
import { buildGallery } from "./gallery.js";
import { compileAsset } from "./compile.js";

const ROOT = new URL("..", import.meta.url).pathname;
const dir = (...p: string[]) => join(ROOT, ...p);

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

function loadAll(): { reg: Registry; themes: Theme[]; issues: Issue[] } {
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
  return { reg: { assets, tokens }, themes, issues };
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
  }
}

/** Render everything once (all variants, all themes) purely to harvest issues. */
function dryRun(reg: Registry, themes: Theme[], issues: Issue[]): void {
  for (const asset of reg.assets.values()) {
    issues.push(...renderSVG(asset, reg).issues);
    for (const v of Object.keys(asset.variants ?? {}))
      issues.push(...renderSVG(asset, reg, { variant: v }).issues);
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

function writeManifest(reg: Registry): void {
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
  writeFileSync(dir("out", "manifest.json"), JSON.stringify({ generated: "polygraphics v0", entries }, null, 2));
}

// ------------------------------------------------------------------ main

const [cmd = "check", ...rest] = process.argv.slice(2);
const themeFlag = rest.includes("--theme") ? rest[rest.indexOf("--theme") + 1] : undefined;

const { reg, themes, issues } = loadAll();

if (cmd === "validate" || cmd === "check") {
  dryRun(reg, themes, issues);
  lintPalette(reg.tokens, issues);
}

// variant-applied documents also get schema-checked during dryRun via applyVariant
void applyVariant;

const { errors, warns } = report(issues);

if (cmd === "validate") {
  console.log(`\n${reg.assets.size} assets, ${themes.length} themes — ${errors} errors, ${warns} warnings`);
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
  writeManifest(reg);
  console.log(`✓ compiled ${c} IR files → out/compiled, manifest → out/manifest.json`);
}

if (cmd === "gallery" || cmd === "check") {
  mkdirSync(dir("out"), { recursive: true });
  const galleryIssues: Issue[] = [];
  writeFileSync(dir("out", "gallery.html"), buildGallery(reg, themes, galleryIssues));
  console.log(`✓ gallery → out/gallery.html`);
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
  if (cmd === "png" || cmd === "baseline") {
    const sub = cmd === "png" ? join("out", "png") : "baselines";
    mkdirSync(dir(sub), { recursive: true });
    for (const [name, buf] of pngs) writeFileSync(dir(sub, name), buf);
    console.log(`✓ ${pngs.size} png files → ${sub}/ (4× scale)`);
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
  console.log(`\n✓ ${reg.assets.size} assets, ${themes.length} themes, ${warns} warnings, 0 errors`);

if (!["check", "validate", "render", "compile", "gallery", "png", "baseline", "regress"].includes(cmd))
  fail(`unknown command "${cmd}"`);
