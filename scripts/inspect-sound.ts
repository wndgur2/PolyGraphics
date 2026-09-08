/**
 * The listening loop, which is the half of the design loop an agent cannot run.
 *
 *   npx tsx scripts/inspect-sound.ts [id …]   → open out/sound-inspect.html
 *
 * Per sound and per variant: the bake embedded so it plays with no server, the
 * waveform to look at, the measurements that stand in for ears, and — the one
 * that actually decides a sound like `hit` — a burst button that fires it the
 * way the game will, jitter rolled per trigger, so you can hear whether a
 * hundred of them in a row read as a swarm or as a machine gun.
 */
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { SoundSchema, type Sound } from "../src/sound-schema.js";
import { compileSound, type SoundRegistry } from "../src/sound-compile.js";
import { describe, renderPCM, toWav, waveformSvg } from "../src/sound-render.js";
import type { Tokens } from "../src/tokens.js";

const ROOT = new URL("..", import.meta.url).pathname;
const dir = (...p: string[]) => join(ROOT, ...p);

const tokens = JSON.parse(readFileSync(dir("tokens", "default.json"), "utf8")) as Tokens;
const sounds = new Map<string, Sound>();
for (const f of readdirSync(dir("sounds")).filter((f) => f.endsWith(".json"))) {
  const sd = SoundSchema.parse(JSON.parse(readFileSync(dir("sounds", f), "utf8")));
  sounds.set(sd.id, sd);
}
const sreg: SoundRegistry = { sounds, tokens };

const want = process.argv.slice(2);
const picked = want.length ? want.map((id) => sounds.get(id) ?? fail(`unknown sound "${id}"`)) : [...sounds.values()];

function fail(msg: string): never {
  console.error(`✖ ${msg} — have: ${[...sounds.keys()].join(", ")}`);
  process.exit(1);
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function take(sound: Sound, variant?: string): string {
  const { ir } = compileSound(sound, sreg);
  const pcm = renderPCM(ir, { variant });
  const d = describe(pcm);
  const uri = `data:audio/wav;base64,${toWav(pcm).toString("base64")}`;
  const jitter = ir.jitter?.freq ?? [1, 1];
  const label = variant ? `#${variant}` : "base";
  const voices = (variant ? ir.variants[variant].voices : ir.voices).length;
  return `<div class="take">
  <h3>${esc(label)} <small>${voices} voices · ${d.duration}s</small></h3>
  ${variant ? `<p class="desc">${esc(sound.variants![variant].description)}</p>` : ""}
  <div class="wave">${waveformSvg(pcm)}<span class="norm">peak-normalized</span></div>
  <div class="row">
    <button data-src="${uri}" data-lo="${jitter[0]}" data-hi="${jitter[1]}" data-n="1">play</button>
    <button data-src="${uri}" data-lo="${jitter[0]}" data-hi="${jitter[1]}" data-n="8">burst ×8</button>
    <audio controls preload="none" src="${uri}"></audio>
  </div>
  <table>
    <tr><th>peak</th><td>${d.peakDb} dBFS</td><th>rms</th><td>${d.rmsDb} dBFS</td>
        <th>brightness</th><td>${d.brightness} zc/s</td><th>clipped</th><td>${d.clipped}</td></tr>
  </table>
</div>`;
}

/**
 * The set at a glance. With one sound a table is noise; with twenty it is the
 * only view that answers the question the lint asks — does this hold together —
 * and it sorts by level so the outlier is the top row or the bottom one.
 */
function overview(): string {
  const rows = picked
    .map((sd) => {
      const { ir } = compileSound(sd, sreg);
      return { sd, d: describe(renderPCM(ir)) };
    })
    .sort((a, b) => b.d.rmsDb - a.d.rmsDb);
  const triggered = rows.filter((r) => r.sd.tags[0] !== "lib").map((r) => r.d.rmsDb).sort((a, b) => a - b);
  const median = triggered.length ? triggered[Math.floor(triggered.length / 2)] : 0;
  return `<table class="set">
  <tr><th>sound</th><th>family</th><th>dur</th><th>peak</th><th>rms</th><th>vs median</th><th>brightness</th></tr>
  ${rows
    .map(({ sd, d }) => {
      const off = sd.tags[0] === "lib" ? "—" : `${d.rmsDb - median > 0 ? "+" : ""}${Math.round(d.rmsDb - median)}dB`;
      const far = sd.tags[0] !== "lib" && Math.abs(d.rmsDb - median) > 9;
      return `<tr${far ? ' class="far"' : ""}>
      <td><a href="#${esc(sd.id)}">${esc(sd.id)}</a></td><td class="dim">${esc(sd.tags[1] ?? sd.tags[0])}</td>
      <td class="num">${d.duration}s</td><td class="num">${d.peakDb}</td><td class="num">${d.rmsDb}</td>
      <td class="num">${off}</td><td class="num dim">${d.brightness}</td></tr>`;
    })
    .join("")}
</table>
<p class="dim">median of the triggered set: ${median} dBFS · library documents are material and sit outside it</p>`;
}

const body = picked
  .sort((a, b) => (a.tags[1] ?? "").localeCompare(b.tags[1] ?? "") || a.id.localeCompare(b.id))
  .map(
    (sound) => `<section id="${esc(sound.id)}">
  <h2>${esc(sound.name)} <code>${esc(sound.id)}</code></h2>
  <p class="desc">${esc(sound.description)}</p>
  <p class="tags">${sound.tags.map((t) => `<span>${esc(t)}</span>`).join("")}${
    sound.meta ? Object.entries(sound.meta).map(([k, v]) => `<span>${esc(k)} ${v}</span>`).join("") : ""
  }</p>
  ${[undefined, ...Object.keys(sound.variants ?? {})].map((v) => take(sound, v)).join("")}
  <details><summary>document</summary><pre>${esc(JSON.stringify(sound, null, 2))}</pre></details>
</section>`,
  )
  .join("");

const html = `<!doctype html><meta charset="utf-8"><title>PolyGraphics — sound inspect</title>
<style>
  :root { color-scheme: dark }
  body { background:#10121a; color:#e6e1d3; font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; margin:0; padding:32px; }
  h1 { font-size:18px; letter-spacing:.08em; text-transform:uppercase; color:#9aa4b2; margin:0 0 24px }
  section { border:1px solid #2a2a34; border-radius:8px; padding:20px; margin-bottom:24px; background:#161822 }
  h2 { margin:0 0 6px; font-size:16px } h2 code { color:#58e8d8; font-size:13px; font-weight:400 }
  h3 { margin:18px 0 6px; font-size:13px; color:#e87ad0 } h3 small { color:#55555f; font-weight:400 }
  .desc { color:#9aa4b2; margin:0 0 10px; max-width:70ch }
  .tags span { display:inline-block; border:1px solid #3a4a5c; border-radius:4px; padding:1px 7px; margin-right:6px; color:#9aa4b2; font-size:12px }
  .take { border-top:1px solid #2a2a34; padding-top:8px }
  .wave { background:#0b0d14; border-radius:4px; padding:6px 0; margin:8px 0; position:relative }
  .norm { position:absolute; right:8px; top:6px; color:#3a4a5c; font-size:11px }
  .wave svg { display:block; width:100%; height:auto }
  .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap }
  button { background:#2a2a34; color:#e6e1d3; border:1px solid #3a4a5c; border-radius:4px; padding:5px 14px; cursor:pointer; font:inherit }
  button:hover { background:#3a4a5c }
  audio { height:32px }
  table { border-collapse:collapse; margin-top:10px; font-size:12px }
  th { color:#55555f; font-weight:400; text-align:left; padding:2px 6px 2px 0 }
  td { color:#bce05a; padding:2px 20px 2px 0 }
  pre { background:#0b0d14; padding:12px; border-radius:4px; overflow:auto; font-size:12px; color:#9aa4b2 }
  summary { cursor:pointer; color:#55555f; margin-top:12px }
  table.set { width:100%; margin-bottom:28px; font-size:12px }
  table.set th { border-bottom:1px solid #2a2a34; padding-bottom:4px }
  table.set td { padding:3px 20px 3px 0; color:#e6e1d3 }
  table.set td.num { color:#bce05a; text-align:right; padding-right:24px }
  table.set td.dim, p.dim { color:#55555f }
  table.set tr.far td { color:#ff9b3d }
  table.set a { color:#58e8d8; text-decoration:none } table.set a:hover { text-decoration:underline }
</style>
<h1>sound inspect</h1>
${picked.length > 1 ? overview() : ""}
${body}
<script>
// The buffer path from the adapter, in miniature: one decoded buffer, replayed
// with a jittered rate. Firing it eight times is the only way to judge whether
// a sound that plays hundreds of times a run wears out.
const ctx = new (window.AudioContext || window.webkitAudioContext)();
const cache = new Map();
async function buffer(src) {
  if (!cache.has(src)) cache.set(src, ctx.decodeAudioData(await (await fetch(src)).arrayBuffer()));
  return cache.get(src);
}
document.addEventListener('click', async (e) => {
  const b = e.target.closest('button[data-src]');
  if (!b) return;
  await ctx.resume();
  const buf = await buffer(b.dataset.src);
  const lo = +b.dataset.lo, hi = +b.dataset.hi, n = +b.dataset.n;
  for (let i = 0; i < n; i++) {
    const s = ctx.createBufferSource();
    s.buffer = buf;
    s.playbackRate.value = lo + Math.random() * (hi - lo);
    s.connect(ctx.destination);
    s.start(ctx.currentTime + i * 0.07);
  }
});
</script>`;

mkdirSync(dir("out"), { recursive: true });
writeFileSync(dir("out", "sound-inspect.html"), html);
console.log(`✓ ${picked.length} sounds → out/sound-inspect.html`);
