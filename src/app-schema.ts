/**
 * The app manifest: `apps/<id>/app.json`.
 *
 * An app is whatever consumes a bundle — one game, one launcher, one screen.
 * It owns a namespace, a palette, a grid, a list of categories, the floor its
 * art is judged on and the scale it is seen at, a clip and state vocabulary,
 * its sound families and its key. It does not own the grammar: the schema, the
 * shapes, the renderer and the adapters are the repo's, and an app narrows them
 * and never extends them.
 *
 * `rules` is where a convention stops being a README sentence. Every rule kind
 * here is a fixed shape that `check` reads; a new *kind* of rule is a PR to
 * `cli.ts`, a new *instance* is a line in a manifest. There is no expression
 * language: `in` matches the category (`tags[0]`), `tagged` and `unless` match
 * the other tags, `require` names keys, `forbid` names a role. A document opts
 * out of a rule in writing — `"why": { "<rule>": "…" }` on the document — the
 * way a sound says `offBand` and a voice says `why` it keeps a raw sawtooth.
 */
import { z } from "zod";
import type { Asset } from "./schema.js";

const appId = z.string().regex(/^[a-z][a-z0-9]*$/, "app ids are short lowercase words, e.g. \"ss\"");
const category = z.string().regex(/^[a-z][a-z0-9]*$/, "categories are lowercase words");
const assetId = z.string().regex(/^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$/);

/** Which documents a rule reaches: a category, narrowed by tags. */
const ScopeFields = {
  in: z.array(category).min(1),
  tagged: z.array(z.string()).optional(), // every one of these tags is present
  unless: z.array(z.string()).optional(), // none of these tags is present
};
export const ScopeSchema = z.strictObject(ScopeFields);
export type Scope = z.infer<typeof ScopeSchema>;

export const RulesSchema = z.strictObject({
  /** Categories whose canvases must sit on the grid. Everything else is placed, not tiled. */
  grid: z.strictObject({ applies: z.array(category) }).optional(),
  /** The one canvas size a category is drawn at. */
  size: z.record(category, z.tuple([z.number().positive(), z.number().positive()])).optional(),
  /** `meta` keys a document must carry — the sim-facing numbers a body owes the game. */
  meta: z.array(z.strictObject({ ...ScopeFields, require: z.array(z.string()).min(1) })).optional(),
  /** Clips a document must carry — `death` on every body, so a consumer never needs a table. */
  clips: z.array(z.strictObject({ ...ScopeFields, require: z.array(z.string()).min(1) })).optional(),
  /** Clips that are one-shots: nothing moves after `settleBy`, because the bake samples a frame short. */
  oneShot: z.record(z.string(), z.strictObject({ settleBy: z.number().min(0).max(1) })).optional(),
  /** The variant vocabulary per category. `"*"` says a category's states are its callers' business. */
  states: z.record(category, z.union([z.array(z.string()), z.literal("*")])).optional(),
  /** Named sets of colour tokens with a meaning — the palette as decisions. */
  roles: z.record(z.string(), z.array(z.string())).optional(),
  /** A role a category may not paint with, through everything it composes. */
  paint: z
    .array(z.strictObject({ ...ScopeFields, forbid: z.string(), except: z.array(assetId).optional() }))
    .optional(),
  /** A named part whose colour must stay apart across a category, in ΔE2000. */
  distinct: z.array(z.strictObject({ ...ScopeFields, part: z.string(), minDeltaE: z.number().positive() })).optional(),
  /** Numbers a document promised the game: `"meta.radius": 62` is the divisor the game uses. */
  contracts: z.record(assetId, z.record(z.string(), z.number())).optional(),
  /** Which `tokens.layers` entry a category draws on; first match wins. */
  layers: z.array(z.strictObject({ ...ScopeFields, layer: z.string() })).optional(),
  /** How hard each rule is. Default is a warning; the app decides its own errors. */
  levels: z.record(z.string(), z.enum(["warn", "error"])).optional(),
});
export type Rules = z.infer<typeof RulesSchema>;

export const AppManifestSchema = z.strictObject({
  id: appId,
  name: z.string().min(1),
  /** The sentence the rules serve. The gallery puts it above the palette. */
  premise: z.string().min(8),
  engines: z.array(z.enum(["phaser", "godot", "web"])).optional(),
  /** Tab order, and the closed set `tags[0]` must come from. */
  categories: z.array(category).min(1),
  reference: z
    .strictObject({
      /** The floors art is judged on, by name: `readability` and the gallery's ground button read these. */
      ground: z.record(z.string(), assetId).optional(),
      /** Screen px per authored px — what "game scale" means for this app. */
      scale: z.number().positive().optional(),
      /** `readability` thresholds: below `sinks` a body is lost in the floor, below `thin` it is marginal. */
      contrast: z.strictObject({ sinks: z.number().positive(), thin: z.number().positive() }).optional(),
    })
    .optional(),
  rules: RulesSchema.optional(),
  audio: z
    .strictObject({
      /** The pitch tokens a fanfare may play — the score's own degrees. */
      key: z.array(z.string()).optional(),
      /** Family tab order in the gallery; offsets live in `tokens.audio.loudness`. */
      families: z.array(z.string()).optional(),
    })
    .optional(),
});
export type AppManifest = z.infer<typeof AppManifestSchema>;

/** The category an asset document says it is in: `tags[0]`. */
export const categoryOf = (a: Pick<Asset, "tags">): string => a.tags[0];

/** Does a scoped rule reach this document? */
export function inScope(a: Pick<Asset, "tags">, scope: Scope): boolean {
  if (!scope.in.includes(categoryOf(a))) return false;
  const tags = new Set(a.tags.slice(1));
  if (scope.tagged?.some((t) => !tags.has(t))) return false;
  if (scope.unless?.some((t) => tags.has(t))) return false;
  return true;
}

/** How a manifest states a rule's strength; a rule it does not name is a warning. */
export function levelOf(m: AppManifest, rule: string): "warn" | "error" {
  return m.rules?.levels?.[rule] ?? "warn";
}
