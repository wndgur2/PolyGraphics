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
import { overlayTokens } from "../src/tokens.js";
import type { Issue } from "../src/render.js";
import type { Asset } from "../src/schema.js";

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
function owner(id: string, assets: Asset[], categories: string[] | undefined, core?: Owner): Owner {
  const tokens = overlayTokens(base, { colors: { blood: "#d63756" } });
  const own = new Map(assets.map((a) => [a.id, a]));
  return {
    id, dir: id === "core" ? "core" : `apps/${id}`,
    manifest: categories ? { id, name: id, premise: "a fixture premise", categories } : undefined,
    own: {}, tokens, themes: [], assets: own, sounds: new Map(),
    reg: { assets: new Map([...(core?.assets ?? []), ...own]), tokens },
    sreg: { sounds: new Map(), tokens },
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

// ---- the real one
const realIssues: Issue[] = [];
for (const o of owners(real)) lintNamespace(real, o, realIssues);
console.log("\nthe real library");
check("the namespace lints are quiet on every app", realIssues.length === 0, realIssues.map((i) => `${i.where}: ${i.msg}`).join(" | "));

console.log(failed ? `\n✖ ${failed} failed` : "\n✓ lints hold");
process.exit(failed ? 1 : 0);
