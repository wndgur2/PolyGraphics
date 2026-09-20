/**
 * The namespace lints, against a deliberately wrong library and against the
 * real one. Each rule has to fire on the fixture that breaks it and on nothing
 * real — a lint that fires on the roster is a rule the roster does not keep,
 * and that is a decision for a manifest, not a test.
 *
 *   npx tsx scripts/test-lints.ts
 */
import { loadLibrary, owners, type Library, type Owner } from "../src/apps.js";
import { lintNamespace } from "../src/lint.js";
import { evaluateRules } from "../src/rules.js";
import type { AppManifest } from "../src/app-schema.js";
import { overlayTokens } from "../src/tokens.js";
import type { Issue } from "../src/render.js";
import type { Asset } from "../src/schema.js";
import type { Sound } from "../src/sound-schema.js";

let failed = 0;
const check = (name: string, ok: boolean, detail = "") => {
  console.log(`  ${ok ? "ok  " : "FAIL"} ${name}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failed++;
};

const doc = (id: string, cat: string, extra: Partial<Asset> = {}): Asset => ({
  id, name: id, description: "a fixture, eight chars", tags: [cat], size: [16, 16],
  parts: [{ id: "body", shape: { kind: "circle", r: 4 }, fill: "$ink" }],
  ...extra,
});

const real = loadLibrary();
const base = real.base;

/** An owner made by hand: enough of one for the lints to read. */
function owner(id: string, assets: Asset[], categories: string[] | undefined, core?: Owner, rules?: AppManifest["rules"], extra: { sounds?: Sound[]; audio?: AppManifest["audio"] } = {}): Owner {
  const tokens = overlayTokens(base, { colors: { blood: "#d63756", bile: "#bce05a", frost: "#8fd0ff" }, audio: { pitch: { third: 523.25, fifth: 659.25, grit: 1100 } } });
  const own = new Map(assets.map((a) => [a.id, a]));
  const sounds = new Map((extra.sounds ?? []).map((sd) => [sd.id, sd]));
  return {
    id, dir: id === "core" ? "core" : `apps/${id}`,
    manifest: categories ? { id, name: id, premise: "a fixture premise", categories, rules, audio: extra.audio } : undefined,
    own: {}, tokens, themes: [], assets: own, sounds,
    reg: { assets: new Map([...(core?.assets ?? []), ...own]), tokens },
    sreg: { sounds, tokens },
  };
}

// ---- the wrong library
const core = owner("core", [doc("core.lib.mark", "lib", { parts: [{ id: "dot", shape: { kind: "circle", r: 2 }, fill: "$blood" }] })], undefined);
const aa = owner("aa", [doc("aa.thing.one", "thing")], ["thing"], core);
const bb = owner(
  "bb",
  [
    doc("bb.thing.two", "thing", { parts: [{ id: "borrowed", use: "aa.thing.one" }] }),
    doc("cc.thing.three", "thing"),
    doc("bb.thing.four", "elsewhere"),
    doc("bb.thing.five", "thing", { variants: { alt: { description: "swaps the part in", set: { "body.use": "aa.thing.one" } } } }),
  ],
  ["thing"],
  core,
);
const wrong: Library = { base, core, apps: [aa, bb], issues: [] };
const issues: Issue[] = [];
for (const o of owners(wrong)) lintNamespace(wrong, o, issues);
const has = (re: RegExp) => issues.some((i) => re.test(`${i.where}: ${i.msg}`));

console.log("the wrong library");
check("a core document painting an app colour is caught", has(/core\.lib\.mark: paints \$blood — core documents use base tokens only/));
check("an id outside its directory's namespace is caught", has(/cc\.thing\.three.*must start with "bb\."/));
check("a category the manifest does not list is caught", has(/bb\.thing\.four: tags\[0\] "elsewhere" is not a category of bb/));
check("composing another app's document is caught", has(/bb\.thing\.two: uses aa\.thing\.one, which is aa's/));
check("…also when a variant patch sets the use", has(/bb\.thing\.five: uses aa\.thing\.one, which is aa's/));
check("a document in its own app, composing its own, passes", !issues.some((i) => /aa\.thing\.one/.test(i.where)));
check("nothing else fires", issues.length === 5, `${issues.length} issues: ${issues.map((i) => i.msg).join(" | ")}`);

// ---- the rules, on an app built to break each one
const clip = (keys: [number, number][]) => ({ duration: 1, tracks: [{ part: "body", prop: "y" as const, keys }] });
const rr = owner(
  "rr",
  [
    doc("rr.body.sits", "body", { size: [18, 18], meta: { radius: 5 }, animations: { death: clip([[0, 0], [0.8, 4], [1, 4]]) } }),  // off the grid
    doc("rr.body.holds", "body", { size: [16, 16], meta: { radius: 5 }, animations: { death: clip([[0, 0], [0.8, 4], [1, 4]]) } }),
    doc("rr.body.late", "body", { size: [16, 16], meta: { radius: 5 }, animations: { death: clip([[0, 0], [1, 4]]) } }),  // still moving at 1
    doc("rr.body.bare", "body", { size: [16, 16] }),                                              // no radius, no death
    doc("rr.body.shot", "body", { size: [16, 16], tags: ["body", "projectile"] }),                 // a shot: exempt
    doc("rr.body.odd", "body", { size: [16, 16], meta: { radius: 5 }, animations: { death: clip([[0, 0], [0.5, 4], [1, 4]]) }, variants: { toxic: { description: "a state nobody listed" } } }),
    doc("rr.icon.big", "icon", { size: [32, 32] }),                                               // icons are 16
    doc("rr.icon.why", "icon", { size: [32, 32], why: { size: "drawn big on purpose, for this test" } }),
    doc("rr.proj.ring", "proj", { meta: { radius: 60 } }),                                        // promised 62
  ],
  ["body", "icon", "proj"],
  undefined,
  {
    grid: { applies: ["body", "icon"] },
    size: { icon: [16, 16] },
    meta: [{ in: ["body"], unless: ["projectile"], require: ["radius"] }],
    clips: [{ in: ["body"], unless: ["projectile"], require: ["death"] }],
    oneShot: { death: { settleBy: 0.85 } },
    states: { body: ["elite"] },
    contracts: { "rr.proj.ring": { "meta.radius": 62 }, "rr.proj.gone": { "meta.radius": 1 } },
    levels: { contracts: "error" },
  },
);
const reports = evaluateRules(rr);
const broke = (rule: string, id: string) => reports.some((r) => r.rule === rule && r.broken.some((b) => b.id === id));
const brokenIds = (rule: string) => reports.filter((r) => r.rule === rule).flatMap((r) => r.broken.map((b) => b.id)).sort().join(" ");
console.log("\nthe rules");
check("grid catches the canvas off it", broke("grid", "rr.body.sits") && brokenIds("grid") === "rr.body.sits", brokenIds("grid"));
check("size catches the icon that is not 16", broke("size", "rr.icon.big") && !broke("size", "rr.icon.why"), brokenIds("size"));
check("…and a why steps a document outside the rule, on the record", reports.some((r) => r.rule === "size" && r.excepted.some((e) => e.id === "rr.icon.why" && /on purpose/.test(e.why))));
check("meta catches the body with no radius, and not the shot", brokenIds("meta") === "rr.body.bare", brokenIds("meta"));
check("clips catches the body with no death, and not the shot", brokenIds("clips") === "rr.body.bare", brokenIds("clips"));
check("oneShot catches the clip still moving at the end, and not the one that holds", brokenIds("oneShot") === "rr.body.late", brokenIds("oneShot"));
check("states catches the state nobody listed", brokenIds("states") === "rr.body.odd", brokenIds("states"));
check("contracts catches the broken promise and the promise to nothing", brokenIds("contracts") === "rr.proj.gone rr.proj.ring", brokenIds("contracts"));
check("…at the level the manifest set", reports.filter((r) => r.rule === "contracts").every((r) => r.level === "error") && reports.find((r) => r.rule === "grid")!.level === "warn");
check("a rule reports how many it reaches", reports.find((r) => r.rule === "grid")!.scope.length === 8);

// ---- paint, distinct and key, on an app built to break each
const painted = (id: string, cat: string, fill: string, extra: Partial<Asset> = {}) =>
  doc(id, cat, { parts: [{ id: "tile", shape: { kind: "rect", w: 8, h: 8 }, fill }], ...extra });
const fanfare = (id: string, notes: string[]): Sound =>
  ({ id, name: id, description: "a fixture fanfare", tags: ["sfx", "fanfare"], duration: 0.5,
     voices: [{ id: "run", phrase: { use: "pp.lib.note", step: 0.1, notes } }] }) as unknown as Sound;
const pp = owner(
  "pp",
  [
    painted("pp.proj.red", "proj", "$blood"),                                                 // paints the banned role
    painted("pp.proj.ok", "proj", "$blood"),                                                  // …but the manifest excepts it
    painted("pp.proj.via", "proj", "$ink", { parts: [{ id: "tile", shape: { kind: "rect", w: 8, h: 8 }, fill: "$ink" }, { id: "load", use: "pp.lib.blob" }] }),  // through what it composes
    painted("pp.proj.state", "proj", "$ink", { variants: { hot: { description: "goes red", set: { "tile.fill": "$blood" } } } }),          // in a state
    painted("pp.proj.clean", "proj", "$frost"),
    painted("pp.lib.blob", "lib", "$blood"),
    painted("pp.icon.a", "icon", "$bile", { tags: ["icon", "weapon"] }),
    painted("pp.icon.b", "icon", "$bile", { tags: ["icon", "weapon"] }),                        // same rim as a
    painted("pp.icon.c", "icon", "$frost", { tags: ["icon", "weapon"] }),
    doc("pp.icon.d", "icon", { tags: ["icon", "weapon"] }),                                    // no tile at all
    painted("pp.icon.e", "icon", "$bile", { tags: ["icon", "weapon"], why: { distinct: "shares the wand's rim until it is redrawn" } }),
  ],
  ["proj", "lib", "icon"],
  undefined,
  {
    roles: { hive: ["blood"] },
    paint: [{ in: ["proj"], forbid: "hive", except: ["pp.proj.ok"], because: "the arsenal is hive material with the signal stripped out" }],
    distinct: [{ in: ["icon"], tagged: ["weapon"], part: "tile", minDeltaE: 13 }],
  },
  { sounds: [fanfare("pp.sfx.win", ["$third", "$fifth", "$third.up"]), fanfare("pp.sfx.lose", ["$third", "$grit"])], audio: { key: ["third", "fifth"], inKey: ["fanfare"] } },
);
const prep = evaluateRules(pp);
const pbroke = (rule: string, id: string) => prep.find((r) => r.rule === rule)!.broken.find((b) => b.id === id);
const pids = (rule: string) => prep.filter((r) => r.rule === rule).flatMap((r) => r.broken.map((b) => b.id)).sort().join(" ");
console.log("\npaint, distinct and key");
check("paint catches the document painting the banned role", !!pbroke("paint", "pp.proj.red") && /paints \$blood — hive is \$blood, and the arsenal/.test(pbroke("paint", "pp.proj.red")!.msg), pbroke("paint", "pp.proj.red")?.msg);
check("…through what it composes, and says through what", /through pp\.lib\.blob/.test(pbroke("paint", "pp.proj.via")?.msg ?? ""), pbroke("paint", "pp.proj.via")?.msg);
check("…and in a state the document declares", !!pbroke("paint", "pp.proj.state"));
check("…not the one the manifest excepts, nor the clean one", pids("paint") === "pp.proj.red pp.proj.state pp.proj.via", pids("paint"));
check("the manifest's exception is on the record", prep.find((r) => r.rule === "paint")!.excepted.some((e) => e.id === "pp.proj.ok"));
check("distinct catches the two rims that are the same colour, once, as a pair", pids("distinct") === "pp.icon.a pp.icon.d" && /vs pp\.icon\.b \$bile: ΔE 0\.0 < 13/.test(pbroke("distinct", "pp.icon.a")!.msg), pids("distinct"));
check("…and the icon with no rim to measure", /has no part "tile"/.test(pbroke("distinct", "pp.icon.d")!.msg));
check("…and a why keeps a document out of the pairing, on the record", prep.find((r) => r.rule === "distinct")!.excepted.some((e) => e.id === "pp.icon.e") && !pbroke("distinct", "pp.icon.e"));
check("key catches the fanfare that leaves the key, and not the one in it", pids("key") === "pp.sfx.lose" && /plays \$grit/.test(pbroke("key", "pp.sfx.lose")!.msg), pids("key"));

// ---- the real one
const realIssues: Issue[] = [];
for (const o of owners(real)) lintNamespace(real, o, realIssues);
console.log("\nthe real library");
check("the namespace lints are quiet on every app", realIssues.length === 0, realIssues.map((i) => `${i.where}: ${i.msg}`).join(" | "));
const realBreaks = owners(real).flatMap((o) => evaluateRules(o).flatMap((r) => r.broken.map((b) => `${o.id} ${r.rule} ${b.id}: ${b.msg}`)));
check("every rule an app states holds over its roster, or is stepped outside in writing", realBreaks.length === 0, realBreaks.join(" | "));

console.log(failed ? `\n✖ ${failed} failed` : "\n✓ lints hold");
process.exit(failed ? 1 : 0);
