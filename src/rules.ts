/**
 * The rules an app states in its manifest, evaluated against its documents.
 *
 * Each rule kind is a fixed shape (see app-schema.ts). Evaluating one yields a
 * report: which documents it reaches, which of them break it and how, and
 * which opted out in writing with a `why`. `check` turns the breaks into
 * issues at the level the manifest sets; the gallery draws the whole report,
 * so a designer can see whether the app is one thing and a session can read
 * the rules before it draws. Nothing here names an app.
 */
import { categoryOf, inScope, levelOf, type AppManifest, type Scope } from "./app-schema.js";
import type { Asset } from "./schema.js";
import type { Issue } from "./render.js";
import type { Owner } from "./apps.js";

export interface RuleReport {
  /** The rule kind — also the key a document's `why` uses to opt out. */
  rule: string;
  /** The rule in one sentence, as the manifest states it. */
  what: string;
  level: "warn" | "error";
  /** Every document the rule reaches. */
  scope: string[];
  broken: { id: string; msg: string }[];
  excepted: { id: string; why: string }[];
}

const listOf = (xs: string[]) => xs.join(", ");
const scopeText = (s: Scope) =>
  `${listOf(s.in)}${s.tagged?.length ? ` tagged ${listOf(s.tagged)}` : ""}${s.unless?.length ? ` unless ${listOf(s.unless)}` : ""}`;

/** The moment a track last changes value. */
function lastMove(keys: [number, number][]): { t: number; to: number } {
  let t = 0, to = keys[0][1];
  for (let i = 1; i < keys.length; i++) if (keys[i][1] !== keys[i - 1][1]) { t = keys[i][0]; to = keys[i][1]; }
  return { t, to };
}

function readPath(obj: unknown, path: string): unknown {
  let cur: unknown = obj;
  for (const k of path.split(".")) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[k];
  }
  return cur;
}

/**
 * One report per rule instance. A document reached by a rule either passes,
 * breaks it, or names the rule in its `why` — in which case it is excepted and
 * the reason is what the report carries instead of a break.
 */
export function evaluateRules(o: Owner): RuleReport[] {
  const m = o.manifest;
  if (!m?.rules) return [];
  const r = m.rules;
  const assets = [...o.assets.values()];
  const reports: RuleReport[] = [];

  const report = (rule: string, what: string, docs: Asset[], test: (a: Asset) => string | undefined): void => {
    const rep: RuleReport = { rule, what, level: levelOf(m, rule), scope: docs.map((a) => a.id), broken: [], excepted: [] };
    for (const a of docs) {
      const why = a.why?.[rule];
      if (why) {
        rep.excepted.push({ id: a.id, why });
        continue;
      }
      const msg = test(a);
      if (msg) rep.broken.push({ id: a.id, msg });
    }
    reports.push(rep);
  };
  const inCats = (cats: string[]) => assets.filter((a) => cats.includes(categoryOf(a)));

  if (r.grid) {
    const g = o.tokens.grid;
    report("grid", `canvases in ${listOf(r.grid.applies)} sit on the ${g}px grid`, inCats(r.grid.applies), (a) =>
      a.size[0] % g || a.size[1] % g ? `size ${a.size[0]}×${a.size[1]} is not a multiple of grid ${g}` : undefined,
    );
  }

  for (const [cat, [w, h]] of Object.entries(r.size ?? {}))
    report("size", `${cat} is ${w}×${h}`, inCats([cat]), (a) =>
      a.size[0] !== w || a.size[1] !== h ? `is ${a.size[0]}×${a.size[1]} — ${cat} is ${w}×${h} in ${o.id}` : undefined,
    );

  for (const rule of r.meta ?? [])
    report("meta", `${scopeText(rule)} carry meta.${rule.require.join(", meta.")}`, assets.filter((a) => inScope(a, rule)), (a) => {
      const missing = rule.require.filter((k) => a.meta?.[k] === undefined);
      return missing.length ? `has no meta.${missing.join(", meta.")} — ${scopeText(rule)} carry one` : undefined;
    });

  for (const rule of r.clips ?? [])
    report("clips", `${scopeText(rule)} carry a ${rule.require.join(" and a ")} clip`, assets.filter((a) => inScope(a, rule)), (a) => {
      const missing = rule.require.filter((k) => !a.animations?.[k]);
      return missing.length ? `has no ${missing.join(", ")} clip — ${scopeText(rule)} carry one` : undefined;
    });

  for (const [clip, { settleBy }] of Object.entries(r.oneShot ?? {}))
    report("oneShot", `${clip} is a one-shot: nothing moves after ${settleBy}`, assets.filter((a) => a.animations?.[clip]), (a) => {
      const late = a.animations![clip].tracks
        .map((tr) => ({ tr, ...lastMove(tr.keys) }))
        .filter((x) => x.t > settleBy);
      if (!late.length) return undefined;
      const first = late[0];
      return `${clip}: ${late.length} track${late.length > 1 ? "s" : ""} still move${late.length > 1 ? "" : "s"} after ${settleBy} (${first.tr.part}.${first.tr.prop} to ${first.to} at ${first.t}) — arrive, then hold`;
    });

  for (const [cat, names] of Object.entries(r.states ?? {})) {
    if (names === "*") continue;
    report("states", `${cat} states are ${names.length ? listOf(names) : "none"}`, inCats([cat]), (a) => {
      const odd = Object.keys(a.variants ?? {}).filter((v) => !names.includes(v));
      return odd.length ? `#${odd.join(", #")} is not a state of ${cat} — states are ${names.length ? listOf(names) : "none"}` : undefined;
    });
  }

  for (const [id, promises] of Object.entries(r.contracts ?? {})) {
    const a = o.assets.get(id);
    const what = `${id} keeps ${Object.entries(promises).map(([p, v]) => `${p} ${v}`).join(", ")}`;
    if (!a) {
      reports.push({ rule: "contracts", what, level: levelOf(m, "contracts"), scope: [id], broken: [{ id, msg: `the manifest holds a contract for it, and it does not exist` }], excepted: [] });
      continue;
    }
    report("contracts", what, [a], (doc) => {
      const off = Object.entries(promises).filter(([p, v]) => readPath(doc, p) !== v);
      return off.length ? off.map(([p, v]) => `${p} is ${readPath(doc, p) ?? "missing"}; the game counts on ${v}`).join("; ") : undefined;
    });
  }

  return reports;
}

/** The breaks, as issues at the level the manifest sets. */
export function lintRules(o: Owner, issues: Issue[]): void {
  for (const rep of evaluateRules(o))
    for (const b of rep.broken) issues.push({ level: rep.level, where: b.id, msg: b.msg });
}

/** Which `tokens.layers` entry a document draws on, by the manifest's `layers` rule; first match wins. */
export function layerOf(m: AppManifest | undefined, a: Asset): string | undefined {
  return m?.rules?.layers?.find((rule) => inScope(a, rule))?.layer;
}
