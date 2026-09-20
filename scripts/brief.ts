/**
 * The design brief for one app, as text: what a session reads before it
 * draws, and what you paste into a chat to ask for a document in this app's
 * voice. The premise and the voice, then the palette by role, the reference
 * floors, the rules check holds the art to (with how many hold), the
 * exemplars with the first lines of their descriptions, and how to judge it.
 *
 *   npm run brief -- --app ss
 *   npx tsx scripts/brief.ts --app demo
 */
import { appFlag, appNamed, loadLibrary } from "../src/apps.js";
import { evaluateRules, scopeText } from "../src/rules.js";

const lib = loadLibrary();
const argv = process.argv.slice(2);
const app = appNamed(lib, appFlag(argv)) ?? lib.apps[0];
if (!app?.manifest) {
  console.error(`✖ no app${appFlag(argv) ? ` "${appFlag(argv)}"` : ""} — apps are ${lib.apps.map((a) => a.id).join(", ")}`);
  process.exit(1);
}
const m = app.manifest;
const v = m.voice ?? {};
const out: string[] = [];
const section = (title: string, items?: string[]) => {
  if (!items?.length) return;
  out.push(`## ${title}`);
  for (const i of items) out.push(`- ${i}`);
  out.push("");
};

out.push(`# ${m.name} (${app.id}) — design brief`, "", m.premise, "");
if (v.world) out.push(v.world, "");
section("Form", v.form);
section("Material and colour", v.material);
section("Light", v.light);
section("Motion", v.motion);
section("Scale", v.scale);
section("Sound", v.sound);
section("Never", v.never);

// How each category is built — considered whether or not it shows.
for (const ins of m.instructions ?? []) {
  out.push(`## Instructions · ${scopeText(ins)}`);
  for (const w of ins.what) out.push(`- ${w}`);
  if (ins.study?.length) out.push(`- study: ${ins.study.join(", ")}`);
  out.push("");
}

const roles = m.rules?.roles ?? {};
const swatch = (n: string) => `$${n} ${app.tokens.colors[n] ?? "?"}`;
const placed = new Set(Object.values(roles).flat());
const rest = Object.keys(app.tokens.colors).filter((n) => !placed.has(n));
out.push("## Palette");
for (const [role, names] of Object.entries(roles)) out.push(`- ${role}: ${names.map(swatch).join(", ")}`);
if (rest.length) out.push(`- ${placed.size ? "the rest" : "colours"}: ${rest.map(swatch).join(", ")}`);
out.push(`- grid ${app.tokens.grid}px · strokes ${Object.entries(app.tokens.strokes).map(([k, w]) => `${k} ${w}`).join(", ")} · alpha ${Object.entries(app.tokens.alpha).map(([k, a]) => `${k} ${a}`).join(", ")}`);
if (app.tokens.audio && Object.keys(app.tokens.audio.pitch).length)
  out.push(`- pitch: ${Object.entries(app.tokens.audio.pitch).map(([k, hz]) => `$${k} ${hz}Hz`).join(", ")}`);
out.push("");

if (m.reference) {
  out.push("## Reference");
  for (const [name, id] of Object.entries(m.reference.ground ?? {})) out.push(`- floor "${name}": ${id}`);
  if (m.reference.scale) out.push(`- game scale ${m.reference.scale}× (screen px per authored px)`);
  if (m.reference.contrast) out.push(`- contrast against the floor: below ${m.reference.contrast.sinks} sinks, below ${m.reference.contrast.thin} is thin`);
  out.push("");
}

const reports = evaluateRules(app);
if (reports.length) {
  out.push("## Rules check holds the art to");
  for (const r of reports) {
    const holds = r.scope.length - r.broken.length - r.excepted.length;
    const tail = [r.excepted.length ? `${r.excepted.length} excepted` : "", r.broken.length ? `${r.broken.length} broken` : ""].filter(Boolean).join(", ");
    out.push(`- ${r.rule}: ${r.what} (${holds} of ${r.scope.length} hold${tail ? `, ${tail}` : ""}${r.level === "error" ? "; an error" : ""})`);
  }
  out.push("");
}

if (v.study?.length) {
  out.push("## Study first");
  for (const id of v.study) {
    const d = app.reg.assets.get(id) ?? app.sreg.sounds.get(id);
    const head = d ? d.description.replace(/\s+/g, " ").slice(0, 220) : "(missing)";
    out.push(`- ${id} — ${head}${d && d.description.length > 220 ? "…" : ""}`);
  }
  out.push("");
}
section("How to judge it", v.judge);
console.log(out.join("\n").trimEnd());
