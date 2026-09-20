/**
 * The library: a shared base, a core of shared documents, and one app per
 * directory under `apps/`.
 *
 * An app is whatever consumes a bundle. It owns its namespace (`<id>.` on every
 * document id), its palette and grid and families (`tokens.json`, laid over
 * `tokens/base.json`), its themes, its documents, its baselines and its bundle.
 * `core/` holds what apps share — library documents that reference base tokens
 * only — and knows no app. Nothing in `src/` names an app: everything a tool
 * knows about one it read from that app's `app.json`.
 *
 * Every registry is per owner: an app's documents see their own and core's,
 * resolved against the app's tokens; core's see core's, against base.
 */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { basename, join } from "node:path";
import { AppManifestSchema, type AppManifest } from "./app-schema.js";
import { AssetSchema, type Asset } from "./schema.js";
import { SoundSchema, type Sound } from "./sound-schema.js";
import type { Issue, Registry } from "./render.js";
import type { SoundRegistry } from "./sound-compile.js";
import { overlayTokens, type Theme, type TokenOverlay, type Tokens } from "./tokens.js";

export const ROOT = new URL("..", import.meta.url).pathname;

/** An app, or core: whoever a document belongs to. */
export interface Owner {
  /** `ss`, `demo`, … or `core`. Also the first segment of every document id it owns. */
  id: string;
  /** Repo-relative: `apps/ss`, or `core`. */
  dir: string;
  /** Core has none. */
  manifest?: AppManifest;
  /** What `tokens.json` lays over base — the app's own palette, for the unused-token lint. */
  own: TokenOverlay;
  /** base ⊕ own: what this owner's documents resolve against. */
  tokens: Tokens;
  themes: Theme[];
  /** Its own documents only. */
  assets: Map<string, Asset>;
  sounds: Map<string, Sound>;
  /** Its documents plus core's, against its tokens — what rendering and composition see. */
  reg: Registry;
  sreg: SoundRegistry;
}

export interface Library {
  base: Tokens;
  core: Owner;
  apps: Owner[];
  /** Everything loading found wrong: bad JSON, schema failures, duplicate ids, a manifest that disagrees with its directory. */
  issues: Issue[];
}

export const slug = (id: string) => id.replace(/\./g, "-");
export const assetPath = (o: Owner, a: Pick<Asset, "id">) => `${o.dir}/assets/${slug(a.id)}.json`;
export const soundPath = (o: Owner, s: Pick<Sound, "id">) => `${o.dir}/sounds/${slug(s.id)}.json`;

function readJson(path: string, issues: Issue[]): unknown {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    issues.push({ level: "error", where: path, msg: `not valid JSON — ${(e as Error).message}` });
    return undefined;
  }
}

function jsonFiles(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => f.endsWith(".json")).sort();
}

function loadDocs<T extends { id: string }>(
  dir: string,
  schema: { safeParse: (raw: unknown) => { success: true; data: T } | { success: false; error: { issues: { path: PropertyKey[]; message: string }[] } } },
  seen: Map<string, string>,
  issues: Issue[],
): Map<string, T> {
  const out = new Map<string, T>();
  for (const f of jsonFiles(join(ROOT, dir))) {
    const where = `${dir}/${f}`;
    const raw = readJson(join(ROOT, dir, f), issues);
    if (raw === undefined) continue;
    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      for (const iss of parsed.error.issues)
        issues.push({ level: "error", where, msg: `${iss.path.join(".") || "(root)"}: ${iss.message}` });
      continue;
    }
    const d = parsed.data;
    // Ids are one namespace across the library: `out/` and `dist/` are flat, and a
    // consumer imports by id. The app prefix is what keeps two apps apart.
    const prior = seen.get(d.id);
    if (prior) issues.push({ level: "error", where, msg: `duplicate id "${d.id}" — also ${prior}` });
    seen.set(d.id, where);
    const expectFile = slug(d.id) + ".json";
    if (basename(f) !== expectFile) issues.push({ level: "warn", where, msg: `file name should match id: "${expectFile}"` });
    out.set(d.id, d);
  }
  return out;
}

function loadThemes(dir: string, issues: Issue[]): Theme[] {
  const themes: Theme[] = [];
  for (const f of jsonFiles(join(ROOT, dir))) {
    const raw = readJson(join(ROOT, dir, f), issues) as Theme | undefined;
    if (!raw) continue;
    if (typeof raw.name !== "string") {
      issues.push({ level: "error", where: `${dir}/${f}`, msg: "a theme needs a `name`" });
      continue;
    }
    themes.push(raw);
  }
  return themes;
}

function loadOwner(id: string, dir: string, base: Tokens, core: Owner | undefined, seen: Map<string, string>, issues: Issue[]): Owner {
  let manifest: AppManifest | undefined;
  if (core) {
    const mpath = join(ROOT, dir, "app.json");
    const raw = existsSync(mpath) ? readJson(mpath, issues) : undefined;
    if (raw === undefined) {
      if (!existsSync(mpath)) issues.push({ level: "error", where: `${dir}/app.json`, msg: "an app needs a manifest — see docs/app-design-systems-plan.md" });
    } else {
      const parsed = AppManifestSchema.safeParse(raw);
      if (!parsed.success)
        for (const iss of parsed.error.issues)
          issues.push({ level: "error", where: `${dir}/app.json`, msg: `${iss.path.join(".") || "(root)"}: ${iss.message}` });
      else {
        manifest = parsed.data;
        if (manifest.id !== id)
          issues.push({ level: "error", where: `${dir}/app.json`, msg: `id "${manifest.id}" must be the directory's name "${id}" — namespace = directory = bundle` });
      }
    }
  }
  const tpath = join(ROOT, dir, "tokens.json");
  const own = (existsSync(tpath) ? (readJson(tpath, issues) as TokenOverlay | undefined) : undefined) ?? {};
  const tokens = overlayTokens(base, own);
  const themes = loadThemes(`${dir}/themes`, issues);
  const assets = loadDocs<Asset>(`${dir}/assets`, AssetSchema, seen, issues);
  const sounds = loadDocs<Sound>(`${dir}/sounds`, SoundSchema, seen, issues);
  if (sounds.size && !tokens.audio)
    issues.push({ level: "error", where: `${dir}/sounds`, msg: "has documents but the tokens have no `audio` section" });
  const reg: Registry = { assets: new Map([...(core?.assets ?? []), ...assets]), tokens };
  const sreg: SoundRegistry = { sounds: new Map([...(core?.sounds ?? []), ...sounds]), tokens };
  return { id, dir, manifest, own, tokens, themes, assets, sounds, reg, sreg };
}

export function loadLibrary(): Library {
  const issues: Issue[] = [];
  const basePath = join(ROOT, "tokens", "base.json");
  let baseRaw: unknown;
  try {
    baseRaw = JSON.parse(readFileSync(basePath, "utf8"));
  } catch (e) {
    throw new Error(`tokens/base.json: ${(e as Error).message}`);
  }
  for (const key of ["grid", "colors", "ramps", "strokes", "alpha", "layers"])
    if (!(key in (baseRaw as object))) throw new Error(`tokens/base.json: missing "${key}"`);
  const base = baseRaw as Tokens;

  const seen = new Map<string, string>();
  const core = loadOwner("core", "core", base, undefined, seen, issues);
  const appsDir = join(ROOT, "apps");
  const ids = existsSync(appsDir) ? readdirSync(appsDir, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name).sort() : [];
  const apps = ids.map((id) => loadOwner(id, `apps/${id}`, base, core, seen, issues));
  if (apps.length === 0 && core.assets.size === 0) issues.push({ level: "error", where: "apps/", msg: "no apps and no core documents — nothing to render" });
  return { base, core, apps, issues };
}

/** Every owner with something to render: the apps, and core if it holds anything. */
export function owners(lib: Library): Owner[] {
  return lib.core.assets.size || lib.core.sounds.size ? [lib.core, ...lib.apps] : lib.apps;
}

/**
 * Whose a document is. By the id's first segment once every id carries one;
 * by lookup meanwhile, so a document whose id predates the namespace still
 * has an owner.
 */
export function ownerOf(lib: Library, id: string): Owner | undefined {
  for (const o of owners(lib)) if (o.assets.has(id) || o.sounds.has(id)) return o;
  const prefix = id.split(".")[0];
  if (prefix === "core") return lib.core;
  return lib.apps.find((a) => a.id === prefix);
}

/** An app by id, or by the `--app <id>` flag in an argv. */
export function appNamed(lib: Library, id: string | undefined): Owner | undefined {
  if (!id) return undefined;
  return id === "core" ? lib.core : lib.apps.find((a) => a.id === id);
}

export function appFlag(argv: string[]): string | undefined {
  const i = argv.indexOf("--app");
  return i >= 0 ? argv[i + 1] : undefined;
}

/** Every asset in the library with its owner, apps first in directory order, core last. */
export function allAssets(lib: Library): [Owner, Asset][] {
  const out: [Owner, Asset][] = [];
  for (const o of owners(lib)) for (const a of o.assets.values()) out.push([o, a]);
  return out;
}

export function allSounds(lib: Library): [Owner, Sound][] {
  const out: [Owner, Sound][] = [];
  for (const o of owners(lib)) for (const s of o.sounds.values()) out.push([o, s]);
  return out;
}

/** A theme by name, across the apps; `--theme <name>` names one. */
export function themeNamed(lib: Library, name: string): { owner: Owner; theme: Theme } | undefined {
  for (const o of owners(lib)) for (const t of o.themes) if (t.name === name) return { owner: o, theme: t };
  return undefined;
}
