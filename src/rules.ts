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
import type { Sound } from "./sound-schema.js";
import type { Issue, Registry } from "./render.js";
import type { Owner } from "./apps.js";
import { deltaE2000, resolveRgb255 } from "./tokens.js";

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

const TOKEN_REF = /\$([a-z][a-z0-9_-]*)/gi;

/** The colour tokens a value names, wherever they sit in it. */
function tokensIn(value: unknown): string[] {
  return [...JSON.stringify(value ?? null).matchAll(TOKEN_REF)].map((m) => m[1]);
}

/**
 * Every colour token a document paints with, through everything it composes:
 * its own parts and every one of its states, and for each `use`, the used
 * document's base parts plus the one state the use names. The map remembers
 * where each token was found, so a break can say "through ss.proj.mine".
 *
 * Read off the documents rather than the compiled IR, because the sentence a
 * paint rule enforces is about what the document *says* — `$pink` is the
 * violation, not a particular RGBA.
 */
export function paintsOf(a: Asset, reg: Registry, depth = 0, out = new Map<string, string>(), variant?: string): Map<string, string> {
  const note = (names: string[]) => {
    for (const n of names) if (!out.has(n)) out.set(n, a.id);
  };
  const part = (p: Asset["parts"][number]) => {
    if ("fill" in p) note(tokensIn(p.fill));
    if ("stroke" in p) note(tokensIn(p.stroke));
  };
  for (const p of a.parts) part(p);
  // The document itself is drawn in every state it declares; a composed one only in the state the use names.
  const states = depth === 0 ? Object.values(a.variants ?? {}) : variant && a.variants?.[variant] ? [a.variants[variant]] : [];
  for (const v of states) {
    for (const p of v.add ?? []) part(p);
    note(tokensIn(v.set));
  }
  if (depth >= 4) return out;
  const uses: [string, string | undefined][] = [];
  for (const p of [...a.parts, ...states.flatMap((v) => v.add ?? [])]) if ("use" in p) uses.push([p.use, p.variant]);
  for (const v of states)
    for (const [k, val] of Object.entries(v.set ?? {})) if (k.endsWith(".use") && typeof val === "string") uses.push([val, undefined]);
  for (const [id, v] of uses) {
    const t = reg.assets.get(id);
    if (t) paintsOf(t, reg, depth + 1, out, v);
  }
  return out;
}

/** The pitch tokens a sound's figures name: phrase notes and the pitch on a use voice. */
function notesOf(sd: Sound): string[] {
  const out: string[] = [];
  for (const v of sd.voices) {
    if ("phrase" in v) for (const n of v.phrase.notes) if (typeof n === "string") out.push(n);
    if ("use" in v && typeof v.pitch === "string") out.push(v.pitch);
  }
  return out;
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

  for (const rule of r.paint ?? []) {
    const names = new Set(r.roles?.[rule.forbid] ?? []);
    const except = new Set(rule.except ?? []);
    const docs = assets.filter((a) => inScope(a, rule));
    const rep: RuleReport = {
      rule: "paint",
      what: `${scopeText(rule)} never paint with ${rule.forbid} (${listOf([...names].map((n) => `$${n}`))})${rule.because ? ` — ${rule.because}` : ""}`,
      level: levelOf(m, "paint"),
      scope: docs.map((a) => a.id),
      broken: [],
      excepted: [],
    };
    for (const a of docs) {
      if (a.why?.paint) { rep.excepted.push({ id: a.id, why: a.why.paint }); continue; }
      if (except.has(a.id)) { rep.excepted.push({ id: a.id, why: "excepted by the manifest" }); continue; }
      const painted = paintsOf(a, o.reg);
      const hit = [...painted].filter(([n]) => names.has(n));
      if (hit.length)
        rep.broken.push({
          id: a.id,
          msg: `paints ${hit.map(([n, via]) => `$${n}${via !== a.id ? ` (through ${via})` : ""}`).join(", ")} — ${rule.forbid} is ${listOf([...names].map((n) => `$${n}`))}${rule.because ? `, and ${rule.because}` : ""}`,
        });
    }
    reports.push(rep);
  }

  for (const rule of r.distinct ?? []) {
    const docs = assets.filter((a) => inScope(a, rule));
    const rep: RuleReport = {
      rule: "distinct",
      what: `${scopeText(rule)}: the ${rule.part} of each is at least ΔE ${rule.minDeltaE} from every other's`,
      level: levelOf(m, "distinct"),
      scope: docs.map((a) => a.id),
      broken: [],
      excepted: [],
    };
    const colours: { a: Asset; ref: string; rgb: [number, number, number] }[] = [];
    for (const a of docs) {
      if (a.why?.distinct) { rep.excepted.push({ id: a.id, why: a.why.distinct }); continue; }
      const p = a.parts.find((x) => x.id === rule.part);
      if (!p) { rep.broken.push({ id: a.id, msg: `has no part "${rule.part}" to keep distinct` }); continue; }
      const ref = "fill" in p && typeof p.fill === "string" ? p.fill : undefined;
      const rgb = ref ? resolveRgb255(ref, o.tokens) : undefined;
      if (!ref || !rgb) { rep.broken.push({ id: a.id, msg: `${rule.part} has no token fill to measure` }); continue; }
      colours.push({ a, ref, rgb });
    }
    for (let i = 0; i < colours.length; i++)
      for (let j = i + 1; j < colours.length; j++) {
        const d = deltaE2000(colours[i].rgb, colours[j].rgb);
        if (d < rule.minDeltaE)
          rep.broken.push({
            id: colours[i].a.id,
            msg: `${rule.part} ${colours[i].ref} vs ${colours[j].a.id} ${colours[j].ref}: ΔE ${d.toFixed(1)} < ${rule.minDeltaE}`,
          });
      }
    reports.push(rep);
  }

  if (m.audio?.key && m.audio.inKey?.length) {
    const key = new Set(m.audio.key);
    const families = new Set(m.audio.inKey);
    const docs = [...o.sounds.values()].filter((sd) => families.has(sd.tags[1] ?? sd.tags[0]));
    const rep: RuleReport = {
      rule: "key",
      what: `${listOf(m.audio.inKey)} play only the key: ${listOf(m.audio.key.map((k) => `$${k}`))}`,
      level: levelOf(m, "key"),
      scope: docs.map((sd) => sd.id),
      broken: [],
      excepted: [],
    };
    for (const sd of docs) {
      const off = notesOf(sd).filter((n) => !key.has(n.replace(/^\$/, "").split(".")[0]));
      if (off.length) rep.broken.push({ id: sd.id, msg: `plays ${listOf([...new Set(off)])} — ${sd.tags[1] ?? sd.tags[0]} stays in the key: ${listOf(m.audio.key.map((k) => `$${k}`))}` });
    }
    reports.push(rep);
  }

  return reports;
}

/** The breaks, as issues at the level the manifest sets. */
export function lintRules(o: Owner, issues: Issue[]): void {
  for (const rep of evaluateRules(o))
    for (const b of rep.broken) issues.push({ level: rep.level, where: b.id, msg: b.msg });
  for (const rule of o.manifest?.rules?.layers ?? [])
    if (!(rule.layer in o.tokens.layers))
      issues.push({ level: "error", where: `${o.dir}/app.json`, msg: `rules.layers names "${rule.layer}", and tokens.layers has no such layer — layers are ${Object.keys(o.tokens.layers).join(", ") || "none"}` });
}

/** Which `tokens.layers` entry a document draws on, by the manifest's `layers` rule; first match wins. */
export function layerOf(m: AppManifest | undefined, a: Asset): string | undefined {
  return m?.rules?.layers?.find((rule) => inScope(a, rule))?.layer;
}
