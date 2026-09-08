/**
 * The listening loop, which is the half of the design loop an agent cannot run.
 *
 *   npx tsx scripts/inspect-sound.ts [--against baselines|<dir>] [id …]   → open out/sound-inspect.html
 *
 * Per sound and per variant: the bake embedded so it plays with no server, the
 * waveform and the spectrogram to look at, the measurements that stand in for
 * ears, and — the one that actually decides a sound like `hit` — a burst button
 * that fires it the way the game will, jitter rolled per trigger, so you can
 * hear whether a hundred of them in a row read as a swarm or as a machine gun.
 *
 * `--against baselines` puts the accepted take from `baselines/sounds/` beside
 * each current one, with one transport for both and an A/B button that plays
 * them back to back, so a re-author is judged against what it replaces at the
 * same level. The numbers beside it say what moved. `docs/listening.md` says
 * what to ask of the person holding the headphones.
 */
import { existsSync, readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { PNG } from "pngjs";
import { SoundSchema, type Sound } from "../src/sound-schema.js";
import { compileSound, type SoundRegistry } from "../src/sound-compile.js";
import {
  describe,
  fromWav,
  renderPCM,
  spectrogram,
  spectrogramRGBA,
  toWav,
  waveformSvg,
  type Descriptors,
} from "../src/sound-render.js";
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

const argv = process.argv.slice(2);
let against: string | undefined;
const want: string[] = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === "--against") {
    const a = argv[++i] ?? fail("--against needs a directory, e.g. `--against baselines`");
    against = a === "baselines" ? dir("baselines", "sounds") : resolve(a);
    if (!existsSync(against)) fail(`--against: no such directory "${against}"`);
  } else want.push(argv[i]);
}
const picked = want.length ? want.map((id) => sounds.get(id) ?? fail(`unknown sound "${id}"`)) : [...sounds.values()];

function fail(msg: string): never {
  console.error(`✖ ${msg} — have: ${[...sounds.keys()].join(", ")}`);
  process.exit(1);
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const slug = (id: string) => id.replace(/\./g, "-");
const wavUri = (pcm: Float32Array) => `data:audio/wav;base64,${toWav(pcm).toString("base64")}`;

function specUri(pcm: Float32Array): string {
  const s = spectrogram(pcm);
  const png = new PNG({ width: s.width, height: s.height });
  png.data = Buffer.from(spectrogramRGBA(s));
  return `data:image/png;base64,${PNG.sync.write(png).toString("base64")}`;
}

/** Waveform over spectrogram, on one time axis — the same pair the gallery draws. */
function picture(pcm: Float32Array): string {
  return `<div class="wave">${waveformSvg(pcm)}<img class="spec" src="${specUri(pcm)}" alt=""><span class="norm">peak-normalized</span></div>`;
}

/** The numbers, and beside each one how far it moved from the accepted take. */
function measures(d: Descriptors, before?: Descriptors): string {
  const cell = (k: keyof Descriptors, unit: string) => {
    const v = d[k], b = before?.[k];
    const moved = b !== undefined && v !== b ? ` <small>${v - b > 0 ? "+" : ""}${Math.round((v - b) * 10) / 10}</small>` : "";
    return `<th>${k === "peakDb" ? "peak" : k === "rmsDb" ? "rms" : k === "attackMs" ? "attack" : k}</th><td>${v}${unit ? ` ${unit}` : ""}${moved}</td>`;
  };
  return `<table><tr>${cell("peakDb", "dBFS")}${cell("rmsDb", "dBFS")}${cell("attackMs", "ms")}${cell("brightness", "zc/s")}${cell("clipped", "")}</tr></table>`;
}

function transport(uri: string, jitter: [number, number], label = "play"): string {
  return `<button data-src="${uri}" data-lo="${jitter[0]}" data-hi="${jitter[1]}" data-n="1">${label}</button>
    <button data-src="${uri}" data-lo="${jitter[0]}" data-hi="${jitter[1]}" data-n="8">burst ×8</button>`;
}

function take(sound: Sound, variant?: string): string {
  const { ir } = compileSound(sound, sreg);
  const pcm = renderPCM(ir, { variant });
  const d = describe(pcm);
  const wav = toWav(pcm);
  const uri = `data:audio/wav;base64,${wav.toString("base64")}`;
  const jitter = ir.jitter?.freq ?? [1, 1];
  const label = variant ? `#${variant}` : "base";
  const voices = (variant ? ir.variants[variant].voices : ir.voices).length;

  // The accepted take, if there is one to hold this against.
  let before = "";
  let bd: Descriptors | undefined;
  if (against) {
    const file = `${slug(sound.id)}${variant ? `--${variant}` : ""}.wav`;
    const path = join(against, file);
    const shown = relative(ROOT, path);
    if (!existsSync(path)) before = `<p class="same">no accepted take at <code>${esc(shown)}</code> — this one is new</p>`;
    else if (readFileSync(path).equals(wav)) before = `<p class="same">byte-identical to <code>${esc(shown)}</code></p>`;
    else {
      const b = fromWav(readFileSync(path)).pcm;
      bd = describe(b);
      const buri = wavUri(b);
      before = `<div class="before">
  <h4>before <small>${esc(shown)}</small></h4>
  ${picture(b)}
  <div class="row">${transport(buri, jitter, "play before")}<button data-ab="${buri}" data-b="${uri}" title="the accepted take, then this one">A/B</button></div>
  </div>`;
    }
  }

  return `<div class="take">
  <h3>${esc(label)} <small>${voices} voices · ${d.duration}s</small></h3>
  ${variant ? `<p class="desc">${esc(sound.variants![variant].description)}</p>` : ""}
  ${picture(pcm)}
  <div class="row">
    ${transport(uri, jitter)}
    <audio controls preload="none" src="${uri}"></audio>
  </div>
  ${measures(d, bd)}
  ${before}
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
  <tr><th>sound</th><th>family</th><th>dur</th><th>peak</th><th>rms</th><th>vs median</th><th>attack</th><th>brightness</th></tr>
  ${rows
    .map(({ sd, d }) => {
      const off = sd.tags[0] === "lib" ? "—" : `${d.rmsDb - median > 0 ? "+" : ""}${Math.round(d.rmsDb - median)}dB`;
      const far = sd.tags[0] !== "lib" && Math.abs(d.rmsDb - median) > 9;
      return `<tr${far ? ' class="far"' : ""}>
      <td><a href="#${esc(sd.id)}">${esc(sd.id)}</a></td><td class="dim">${esc(sd.tags[1] ?? sd.tags[0])}</td>
      <td class="num">${d.duration}s</td><td class="num">${d.peakDb}</td><td class="num">${d.rmsDb}</td>
      <td class="num">${off}</td><td class="num dim">${d.attackMs}ms</td><td class="num dim">${d.brightness}</td></tr>`;
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
  h4 { margin:0 0 6px; font-size:12px; color:#9aa4b2; text-transform:uppercase; letter-spacing:.06em } h4 small { color:#55555f; text-transform:none; letter-spacing:0; margin-left:8px }
  .desc { color:#9aa4b2; margin:0 0 10px; max-width:70ch }
  .tags span { display:inline-block; border:1px solid #3a4a5c; border-radius:4px; padding:1px 7px; margin-right:6px; color:#9aa4b2; font-size:12px }
  .take { border-top:1px solid #2a2a34; padding-top:8px }
  .wave { background:#0b0d14; border-radius:4px; padding:6px 0; margin:8px 0; position:relative }
  .norm { position:absolute; right:8px; top:6px; color:#3a4a5c; font-size:11px }
  .wave svg { display:block; width:100%; height:auto }
  .spec { display:block; width:100%; height:80px; image-rendering:pixelated; border-top:1px solid #2a2a34; margin-top:6px }
  .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap }
  button { background:#2a2a34; color:#e6e1d3; border:1px solid #3a4a5c; border-radius:4px; padding:5px 14px; cursor:pointer; font:inherit }
  button:hover { background:#3a4a5c }
  audio { height:32px }
  table { border-collapse:collapse; margin-top:10px; font-size:12px }
  th { color:#55555f; font-weight:400; text-align:left; padding:2px 6px 2px 0 }
  td { color:#bce05a; padding:2px 20px 2px 0 } td small { color:#ff9b3d; margin-left:4px }
  .before { border-left:2px solid #3a4a5c; padding-left:12px; margin-top:12px }
  .same { color:#55555f; font-size:12px; margin:8px 0 0 } .same code { color:#9aa4b2 }
  pre { background:#0b0d14; padding:12px; border-radius:4px; overflow:auto; font-size:12px; color:#9aa4b2 }
  summary { cursor:pointer; color:#55555f; margin-top:12px }
  table.set { width:100%; margin-bottom:28px; font-size:12px }
  table.set th { border-bottom:1px solid #2a2a34; padding-bottom:4px }
  table.set td { padding:3px 20px 3px 0; color:#e6e1d3 }
  table.set td.num { color:#bce05a; text-align:right; padding-right:24px }
  table.set td.dim, p.dim { color:#55555f }
  table.set tr.far td { color:#ff9b3d }
  table.set a { color:#58e8d8; text-decoration:none } table.set a:hover { text-decoration:underline }
  #phone { position:fixed; top:20px; right:28px; background:#161822; border:1px dashed #3a4a5c; border-radius:6px; padding:6px 12px; cursor:pointer; user-select:none; font-size:12px; color:#9aa4b2 }
  #phone.on { border-style:solid; border-color:#58e8d8; color:#58e8d8 }
</style>
<h1>sound inspect${against ? ` <small style="color:#55555f;text-transform:none;letter-spacing:0">against ${esc(relative(ROOT, against))}</small>` : ""}</h1>
<label id="phone" title="Play everything through what a phone speaker keeps — a 250Hz highpass and an 8kHz lowpass"><input type="checkbox" hidden> phone</label>
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
// The phone: what a small speaker keeps, in the way of every transport.
const phoneEl = document.getElementById('phone');
let phone = sessionStorage.phone === '1';
phoneEl.classList.toggle('on', phone);
phoneEl.onclick = (e) => { e.preventDefault(); phone = !phone; sessionStorage.phone = phone ? '1' : ''; phoneEl.classList.toggle('on', phone); };
let chain = null;
function output() {
  if (!phone) return ctx.destination;
  if (!chain) {
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 250; hp.Q.value = 0.707;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 8000; lp.Q.value = 0.707;
    hp.connect(lp); lp.connect(ctx.destination); chain = hp;
  }
  return chain;
}
function fire(buf, at, rate = 1) {
  const s = ctx.createBufferSource();
  s.buffer = buf;
  s.playbackRate.value = rate;
  s.connect(output());
  s.start(at);
}
document.addEventListener('click', async (e) => {
  const b = e.target.closest('button[data-src]');
  if (!b) return;
  await ctx.resume();
  const buf = await buffer(b.dataset.src);
  const lo = +b.dataset.lo, hi = +b.dataset.hi, n = +b.dataset.n;
  for (let i = 0; i < n; i++) fire(buf, ctx.currentTime + i * (buf.duration < 0.12 ? 0.07 : buf.duration * 0.75), lo + Math.random() * (hi - lo));
});
// A/B: the accepted take, a beat of silence, then this one. Same level, same
// rate, no jitter — the only thing that differs is the document.
document.addEventListener('click', async (e) => {
  const b = e.target.closest('button[data-ab]');
  if (!b) return;
  await ctx.resume();
  const [a, bb] = await Promise.all([buffer(b.dataset.ab), buffer(b.dataset.b)]);
  const t = ctx.currentTime;
  fire(a, t);
  fire(bb, t + a.duration + 0.3);
});
</script>`;

mkdirSync(dir("out"), { recursive: true });
writeFileSync(dir("out", "sound-inspect.html"), html);
console.log(`✓ ${picked.length} sounds → out/sound-inspect.html${against ? ` (against ${relative(ROOT, against)})` : ""}`);
