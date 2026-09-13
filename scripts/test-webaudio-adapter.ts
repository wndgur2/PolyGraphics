/**
 * End-to-end test for the sound path: document → IR → offline PCM → WebAudio.
 *
 * The offline renderer and the adapter are two interpreters of one IR, and the
 * claim worth testing is that they agree — that the WAV in out/wav is what a
 * browser plays rather than a cousin of it. So the adapter is driven against a
 * recording mock context and its graph is checked against the renderer's own
 * numbers, not just against itself.
 *
 * Run: npx tsx scripts/test-webaudio-adapter.ts
 */
import { readdirSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { play, bake, rollJitter, type IRSound } from "../adapters/webaudio/polygraphics-webaudio.js";
import { compileSound, type SoundRegistry } from "../src/sound-compile.js";
import { renderPCM, describe, fromWav, spectrogram, toWav, SAMPLE_RATE } from "../src/sound-render.js";
import { SoundSchema } from "../src/sound-schema.js";
import { mulberry32 } from "../src/prng.js";
import type { Tokens } from "../src/tokens.js";

const root = (p: string) => new URL(`../${p}`, import.meta.url);
const readJson = (p: string) => JSON.parse(readFileSync(root(p), "utf8"));

let failures = 0;
function check(name: string, cond: boolean, detail = ""): void {
  console.log(`${cond ? "  ok  " : "  FAIL"} ${name}${detail ? ` — ${detail}` : ""}`);
  if (!cond) failures++;
}
const close = (a: number, b: number, eps = 1e-4) => Math.abs(a - b) <= eps;
const r = (n: number) => Math.round(n * 10000) / 10000;

// ---------------------------------------------------------------- mock context

interface Op { op: string; [k: string]: unknown }

function mockContext(sampleRate = SAMPLE_RATE) {
  const ops: Op[] = [];
  const buffers: Float32Array[] = [];
  const param = (owner: string, name: string) => ({
    value: 0,
    setValueAtTime(v: number, t: number) { ops.push({ op: "setValue", owner, name, v: +v.toFixed(4), t: +t.toFixed(5) }); return this; },
    setValueCurveAtTime(c: Float32Array, t: number, d: number) {
      ops.push({ op: "curve", owner, name, n: c.length, first: +c[0].toFixed(6), last: +c[c.length - 1].toFixed(6), max: +Math.max(...c).toFixed(6), t: +t.toFixed(5), d: +d.toFixed(5), curve: c });
      return this;
    },
  });
  const node = (kind: string) => ({ kind, connect(to: { kind?: string }) { ops.push({ op: "connect", from: kind, to: to.kind ?? "dest" }); } });
  const ctx = {
    sampleRate,
    currentTime: 0,
    destination: { kind: "dest" } as never,
    createGain: () => ({ ...node("gain"), gain: param("gain", "gain") }),
    createBiquadFilter: () => ({ ...node("biquad"), type: "", Q: param("biquad", "Q"), frequency: param("biquad", "frequency") }),
    createOscillator: () => {
      const o = { ...node("osc"), type: "", frequency: param("osc", "frequency"), start: (t: number) => ops.push({ op: "start", kind: "osc", t: +t.toFixed(5) }), stop: (t: number) => ops.push({ op: "stop", kind: "osc", t: +t.toFixed(5) }) };
      return o;
    },
    createBufferSource: () => ({ ...node("noise"), buffer: null as unknown, playbackRate: { value: 1 }, start: (t: number) => ops.push({ op: "start", kind: "noise", t: +t.toFixed(5) }), stop: (t: number) => ops.push({ op: "stop", kind: "noise", t: +t.toFixed(5) }) }),
    createBuffer: (_ch: number, frames: number, sr: number) => {
      const data = new Float32Array(frames);
      buffers.push(data);
      return { length: frames, sampleRate: sr, getChannelData: () => data };
    },
  };
  return { ctx: ctx as never as BaseAudioContext, ops, buffers };
}

const opsKey = (ops: Op[]) =>
  createHash("sha256").update(JSON.stringify(ops.map(({ curve, ...o }) => (void curve, o)))).digest("hex").slice(0, 16);

// ---------------------------------------------------------------- fixture

const tokens = readJson("tokens/default.json") as Tokens;
const all = new Map<string, ReturnType<typeof SoundSchema.parse>>();
for (const f of readdirSync(new URL("../sounds", import.meta.url)).filter((f) => f.endsWith(".json"))) {
  const sd = SoundSchema.parse(readJson(`sounds/${f}`));
  all.set(sd.id, sd);
}
const sreg: SoundRegistry = { sounds: all, tokens };
const doc = all.get("ss.sfx.hit")!;
const { ir, issues } = compileSound(doc, sreg);

console.log(`\n${doc.id} — ${doc.voices.length} authored voices`);
check("compiles without errors", issues.filter((i) => i.level === "error").length === 0, issues.map((i) => i.msg).join("; "));
check("repeat expanded to concrete grains", ir.voices.length === 6, `${ir.voices.length} IR voices`);
check("variant pre-applied", !!ir.variants.elite && ir.variants.elite.voices.length === 6);
check(
  "variant pitch reached every frequency",
  close((ir.variants.elite.voices[0].source as { freq: number }).freq, 200 * 0.55, 0.01),
  `${(ir.variants.elite.voices[0].source as { freq: number }).freq}Hz`,
);
check("variant stretch reached the duration", close(ir.variants.elite.duration, 0.135));

// ---------------------------------------------------------------- offline render

console.log("\noffline render");
const pcm = renderPCM(ir);
const d = describe(pcm);
check("renders the full canvas", pcm.length === Math.ceil(ir.duration * SAMPLE_RATE), `${pcm.length} samples`);
check("audible", d.peak > 0.05, `peak ${d.peakDb}dBFS`);
check("does not clip", d.clipped === 0);
check("starts and ends at silence (declick)", Math.abs(pcm[0]) < 1e-3 && Math.abs(pcm[pcm.length - 1]) < 1e-3);

const hashA = createHash("sha256").update(toWav(renderPCM(ir))).digest("hex");
const hashB = createHash("sha256").update(toWav(renderPCM(ir))).digest("hex");
check("byte-identical across runs", hashA === hashB, hashA.slice(0, 16));

const elite = describe(renderPCM(ir, { variant: "elite" }));
check("elite is longer", elite.duration > d.duration, `${elite.duration}s vs ${d.duration}s`);
check("elite is darker", elite.brightness < d.brightness, `${elite.brightness}Hz vs ${d.brightness}Hz zero-crossings`);

// ---------------------------------------------------------------- adapter graph

console.log("\nwebaudio adapter");
const irJson = JSON.parse(JSON.stringify(ir)) as IRSound; // what a game actually imports
const m = mockContext();
play(m.ctx, m.ctx.destination, irJson, { rng: mulberry32(1) });

const oscs = m.ops.filter((o) => o.op === "start" && o.kind === "osc");
const noises = m.ops.filter((o) => o.op === "start" && o.kind === "noise");
check("one node per IR voice", oscs.length + noises.length === ir.voices.length, `${oscs.length} osc + ${noises.length} noise`);
check("grains start at their IR times", noises.every((o) => ir.voices.some((v) => close(v.at, o.t as number, 1e-4))));
check("filters built for the grains", m.ops.filter((o) => o.op === "curve" && o.owner === "biquad").length === 5);

const gainCurves = m.ops.filter((o) => o.op === "curve" && o.owner === "gain");
check("every voice gets a gain curve", gainCurves.length === ir.voices.length);
check("gain curves start and end at zero (declick)", gainCurves.every((o) => o.first === 0 && o.last === 0));

/**
 * The claim under test: the adapter's gain curve and the renderer's envelope
 * are the same shape, declick and all. A square oscillator swings to ±1, so
 * rendering the thump alone offline makes its peak sample *be* the peak gain —
 * one number the two paths compute independently and must agree on.
 */
const thumpPeak = describe(renderPCM({ ...ir, voices: [ir.voices[0]], variants: {} })).peak;
const thump = gainCurves.find((o) => close(o.d as number, 0.045));
check(
  "adapter gain curve matches the renderer's envelope",
  !!thump && close(thump.max as number, thumpPeak, 0.02),
  `curve ${thump?.max} vs rendered ${thumpPeak}`,
);

/**
 * Frequencies arrive multiplied by this trigger's jitter roll — the same roll,
 * because play() was handed the same seeded rng.
 */
const roll = rollJitter(irJson, mulberry32(1));
const freqCurve = m.ops.find((o) => o.op === "curve" && o.owner === "osc");
check(
  "thump slides 200 → 100Hz, scaled by this play's jitter",
  !!freqCurve && close(freqCurve.first as number, 200 * roll.freq, 0.5) && close(freqCurve.last as number, 100 * roll.freq, 0.5),
  `${freqCurve?.first} → ${freqCurve?.last} (×${roll.freq.toFixed(3)})`,
);

// The real risk in two interpreters: the noise diverging. Same seed, same PRNG,
// same samples — checked against the renderer's own generator, not the adapter's.
const grain = ir.voices.find((v) => v.source.kind === "noise")!;
const rng = mulberry32((grain.source as { seed: number }).seed);
const expected = Array.from({ length: 8 }, () => rng() * 2 - 1);
const got = m.buffers[0].slice(0, 8);
check("noise matches the offline renderer sample-for-sample", expected.every((v, i) => close(v, got[i], 1e-6)), `${got[0].toFixed(6)}…`);

// ---------------------------------------------------------------- determinism & options

const m2 = mockContext();
play(m2.ctx, m2.ctx.destination, irJson, { rng: mulberry32(1) });
check("same rng → same graph", opsKey(m.ops) === opsKey(m2.ops), opsKey(m.ops));

const m3 = mockContext();
play(m3.ctx, m3.ctx.destination, irJson, { rng: mulberry32(9) });
check("different rng → different pitch (jitter is alive)", opsKey(m.ops) !== opsKey(m3.ops));

check("jitter stays inside the authored range", roll.freq >= 0.82 && roll.freq <= 1.2, `×${roll.freq.toFixed(3)}`);

const m4 = mockContext();
play(m4.ctx, m4.ctx.destination, irJson, { variant: "elite", rng: mulberry32(1) });
const eliteFreq = m4.ops.find((o) => o.op === "curve" && o.owner === "osc");
check("variant reaches the adapter", !!eliteFreq && (eliteFreq.first as number) < 130, `${eliteFreq?.first}Hz`);

let threw = false;
try { play(m4.ctx, m4.ctx.destination, irJson, { variant: "nope" }); } catch { threw = true; }
check("unknown variant fails loudly", threw);

let bakeRefused = false;
try { await bake(m.ctx, irJson); } catch { bakeRefused = true; }
check("bake() says so when OfflineAudioContext is absent", bakeRefused);

// ---------------------------------------------------------------- the set

console.log(`\nthe set — ${all.size} documents`);
const compiled = [...all.values()].map((sd) => ({ sd, ...compileSound(sd, sreg) }));
check("every document compiles", compiled.every((c) => !c.issues.some((i) => i.level === "error")));

const measured = compiled.map((c) => ({ id: c.ir.id, tags: c.sd.tags, offBand: c.sd.offBand, d: describe(renderPCM(c.ir)) }));
check("nothing clips", measured.every((m) => m.d.clipped === 0));
check("nothing is silent", measured.every((m) => m.d.peak > 0.02), measured.filter((m) => m.d.peak <= 0.02).map((m) => m.id).join(", "));

const triggered = measured.filter((m) => m.tags[0] !== "lib" && !m.offBand).map((m) => m.d.rmsDb).sort((a, b) => a - b);
const median = triggered[Math.floor(triggered.length / 2)];
check(
  "the triggered set holds together within 9dB of its median",
  triggered.every((r) => Math.abs(r - median) <= 9),
  `${triggered[0]}…${triggered[triggered.length - 1]}dBFS, median ${median}`,
);

/**
 * The claim `use` exists to make: one library document is the instrument, and
 * every fanfare built on it moves when it does. Retune the note in memory and
 * the compiled pitches of level-up and victory have to follow — otherwise they
 * are four copies of a number wearing a composition's clothes.
 */
const FANFARES = ["ss.sfx.levelup", "ss.sfx.victory"];
const before = FANFARES.map((id) => compileSound(all.get(id)!, sreg).ir.voices.map((v) => (v.source as { freq: number }).freq));
const lib = structuredClone(all.get("ss.lib.note")!);
(lib.voices[0] as { source: { freq: string } }).source.freq = "$third.up";
const retuned: SoundRegistry = { sounds: new Map(all).set(lib.id, lib), tokens };
const after = FANFARES.map((id) => compileSound(all.get(id)!, retuned).ir.voices.map((v) => (v.source as { freq: number }).freq));
check(
  "retuning ss.lib.note moves every fanfare built on it",
  FANFARES.every((_, i) => before[i][0] !== after[i][0] && after[i][0] === 1046.5),
  `${before[0][0]} → ${after[0][0]}Hz`,
);
check(
  "…and leaves documents that do not compose it alone",
  compileSound(all.get("ss.sfx.gameover")!, retuned).ir.voices[0].source.kind === "osc" &&
    (compileSound(all.get("ss.sfx.gameover")!, retuned).ir.voices[0].source as { freq: number }).freq === 392,
);

const victory = compileSound(all.get("ss.sfx.victory")!, sreg).ir;
check("a use voice's `dur` refits the composed document", victory.voices.every((v) => close(v.dur, 0.16)), `${victory.voices[0].dur}s`);

/**
 * The claim `root` exists to make: a library document is written at one pitch
 * and played at another, so the degree lives at the call site with the melody
 * instead of as a variant inside the instrument. The four rungs of the level-up
 * figure have to come out as the four scale tokens themselves.
 */
const freqs = (id: string) =>
  compileSound(all.get(id)!, sreg).ir.voices.map((v) => (v.source as { freq: number }).freq);
check(
  "playing an instrument at a pitch transposes it to exactly that pitch",
  JSON.stringify(freqs("ss.sfx.levelup")) === JSON.stringify([523.25, 659.25, 784, 1046.5]),
  freqs("ss.sfx.levelup").join(", "),
);
check(
  "…and the same instrument walks the other way down for the loss figure",
  JSON.stringify(freqs("ss.sfx.gameover")) === JSON.stringify([392, 329.63, 261.63, 196]),
  freqs("ss.sfx.gameover").join(", "),
);
check(
  "an instrument played at its own root is the instrument unchanged",
  freqs("ss.sfx.levelup")[0] === freqs("ss.lib.note")[0],
  `${freqs("ss.sfx.levelup")[0]} vs ${freqs("ss.lib.note")[0]}Hz`,
);

// A document with no `root` has not said what pitch it is written at, so there
// is nothing to measure a requested pitch against. Guessing one would make every
// figure built on it quietly wrong; saying so is the whole value of the field.
/**
 * The claim `adsr` exists to make: an attack written in seconds is that many
 * seconds at every length the voice is played at. Two voices three times apart,
 * one envelope — the compiled keys have to put the peak at the same instant,
 * which means the two normalized positions have to differ. That difference is
 * the division `ss.sfx.chime` used to do by hand.
 */
const struck = SoundSchema.parse({
  id: "test.struck",
  name: "Struck",
  description: "One attack, written once, at two different lengths.",
  tags: ["sfx"],
  duration: 1,
  voices: [
    { id: "short", dur: 0.3, source: { kind: "osc", wave: "sine", freq: "$tonic" }, env: [{ prop: "gain", adsr: { attack: 0.012 } }] },
    { id: "long", dur: 0.9, source: { kind: "osc", wave: "sine", freq: "$tonic" }, env: [{ prop: "gain", adsr: { attack: 0.012 } }] },
  ],
});
const struckVoices = compileSound(struck, { sounds: new Map(all).set(struck.id, struck), tokens }).ir.voices;
const peakAt = (v: (typeof struckVoices)[number]) => v.env[0].keys[1][0] * v.dur;
check(
  "an adsr attack is the same seconds however long the voice is",
  struckVoices.every((v) => close(peakAt(v), 0.012, 1e-3)),
  struckVoices.map((v) => `${v.dur}s → ${r(peakAt(v))}s`).join(", "),
);
check(
  "…which it can only be by landing on different fractions of each span",
  struckVoices[0].env[0].keys[1][0] !== struckVoices[1].env[0].keys[1][0],
  struckVoices.map((v) => v.env[0].keys[1][0]).join(" vs "),
);

const chime = compileSound(all.get("ss.sfx.chime")!, sreg).ir.voices;
check(
  "chime's two voices now peak at the same instant, not at the same fraction",
  close(peakAt(chime[0]), peakAt(chime[1]), 1e-3),
  chime.map((v) => `${v.id} ${r(peakAt(v))}s`).join(", "),
);

// An envelope longer than the voice it is written on is compressed rather than
// truncated — a hurried version of the shape, not the shape with its tail cut.
const crammed = SoundSchema.parse({
  id: "test.crammed",
  name: "Crammed",
  description: "An envelope that does not fit the voice it is written on.",
  tags: ["sfx"],
  duration: 0.1,
  voices: [{ id: "v", dur: 0.05, source: { kind: "osc", wave: "sine", freq: "$tonic" }, env: [{ prop: "gain", adsr: { attack: 0.04, decay: 0.04, release: 0.04 } }] }],
});
const crammedOut = compileSound(crammed, { sounds: new Map(all).set(crammed.id, crammed), tokens });
check(
  "an adsr too long for its voice is compressed, and says so",
  crammedOut.issues.some((i) => i.level === "warn" && i.msg.includes("compressed to fit")) &&
    crammedOut.ir.voices[0].env[0].keys.every((k) => k[0] <= 1),
  crammedOut.issues.map((i) => i.msg).join("; ") || "no issue raised",
);

const rootless = structuredClone(all.get("ss.sfx.select")!);
const caller = SoundSchema.parse({
  id: "test.caller",
  name: "Caller",
  description: "Plays a document that never said what pitch it was written at.",
  tags: ["sfx"],
  duration: 0.2,
  voices: [{ id: "n", use: rootless.id, pitch: "$fifth" }],
});
const rootlessIssues = compileSound(caller, {
  sounds: new Map(all).set(caller.id, caller),
  tokens,
}).issues;
check(
  "playing a document that declares no `root` is an error, not a guess",
  rootlessIssues.some((i) => i.level === "error" && i.msg.includes("no `root`")),
  rootlessIssues.map((i) => i.msg).join("; ") || "no issue raised",
);

/**
 * The two pictures and the one reader that the listening loop leans on.
 * Neither is a baseline — but a spectrogram that drew differently run to run
 * would make "look at the spectrogram" a worse instruction than it already
 * is, and a WAV that did not read back as itself would make `--against`
 * compare a take to a cousin of it.
 */
const spec1 = spectrogram(pcm), spec2 = spectrogram(pcm);
check("spectrogram is the same picture every run", Buffer.from(spec1.data).equals(Buffer.from(spec2.data)));
check("spectrogram is 320 columns by 96 rows", spec1.width === 320 && spec1.height === 96, `${spec1.width}×${spec1.height}`);
check("spectrogram peaks at 255", Math.max(...spec1.data) === 255);
const tiny = spectrogram(pcm.subarray(0, 100));
check("a take shorter than 320 samples gets one column per sample", tiny.width === 100, `${tiny.width}`);
const back = fromWav(toWav(pcm));
check(
  "a bake reads back as itself",
  back.sampleRate === SAMPLE_RATE && back.pcm.length === pcm.length && back.pcm.every((v, i) => Math.abs(v - pcm[i]) <= 1 / 32767),
  `${back.pcm.length} samples at ${back.sampleRate}Hz`,
);

/**
 * The measurements the lint holds the set on. Each is checked on a signal
 * whose answer is known, so a wrong coefficient is a failed check rather
 * than a set quietly held to the wrong number.
 */
const sine = (hz: number, secs = 0.5, amp = 1): Float32Array => {
  const out = new Float32Array(Math.round(secs * SAMPLE_RATE));
  for (let i = 0; i < out.length; i++) out[i] = amp * Math.sin((2 * Math.PI * hz * i) / SAMPLE_RATE);
  return out;
};
const ref = describe(sine(1000));
check("K-weighting is flat at 1kHz — a full-scale sine reads -3dB, as RMS does", Math.abs(ref.loudnessDb - ref.rmsDb) < 0.3 && Math.abs(ref.rmsDb + 3) < 0.2, `${ref.loudnessDb} vs ${ref.rmsDb}`);
const high = describe(sine(8000));
check("…and lifts the top by about 4dB", high.loudnessDb - high.rmsDb > 3 && high.loudnessDb - high.rmsDb < 4.5, `+${r(high.loudnessDb - high.rmsDb)}`);
check("centroid of a 1kHz sine is 1kHz", Math.abs(ref.centroidHz - 1000) < 30, `${ref.centroidHz}Hz`);
check("bands sum to one", Math.abs(ref.bands.low + ref.bands.mid + ref.bands.high - 1) < 0.01 && ref.bands.mid > 0.98, JSON.stringify(ref.bands));
const low = describe(sine(80));
check("a low sine loses everything on the phone", low.phoneLossDb > 15 && low.bands.low > 0.95, `-${low.phoneLossDb}dB, ${low.bands.low} low`);
check("a 1kHz sine loses nothing on the phone", ref.phoneLossDb < 0.5, `-${ref.phoneLossDb}dB`);
// A sine at a quarter of the sample rate sampled off its peaks: every sample
// is ±0.707 while the wave itself reaches 1. The sample peak lies; the true
// peak does not.
const between = new Float32Array(4410);
for (let i = 0; i < between.length; i++) between[i] = Math.sin(Math.PI / 2 * i + Math.PI / 4);
const tp = describe(between);
check("true peak sees between the samples", tp.peakDb < -2.9 && tp.truePeakDb > -0.5, `sample ${tp.peakDb}dBFS, true ${tp.truePeakDb}dBTP`);
const stompD = describe(renderPCM(compileSound(all.get("ss.sfx.stomp")!, sreg).ir));
const shootD = describe(renderPCM(compileSound(all.get("ss.sfx.shoot")!, sreg).ir));
check("stomp loses far more on a phone than shoot", stompD.phoneLossDb > shootD.phoneLossDb + 5, `stomp -${stompD.phoneLossDb} vs shoot -${shootD.phoneLossDb}`);
check("tail is inside the take and after the attack", ref.tailS <= 0.5 && ref.tailS > ref.attackMs / 1000, `${ref.tailS}s`);

/**
 * The four idioms. Each compiles to voices the IR already knows, so the claim
 * to check is that the voices are the ones the author would have written by
 * hand — and, for `phrase`, that the three fanfares came out exactly as they
 * were when they were hand-written, which the baselines also enforce.
 */
const probeDoc = (id: string, voices: unknown[], extra: Record<string, unknown> = {}) =>
  SoundSchema.parse({ id, name: id, description: `A probe document for ${id}.`, tags: ["sfx", "probe"], duration: 1, voices, ...extra });
const probe = (sd: ReturnType<typeof SoundSchema.parse>) => compileSound(sd, { sounds: new Map(all).set(sd.id, sd), tokens });

const wide = probe(probeDoc("test.wide", [{ id: "pad", source: { kind: "osc", wave: "triangle", freq: "$tonic", to: "$tonic.up", unison: { count: 2, detune: 7 } }, gain: "mid" }]));
const uf = wide.ir.voices.map((v) => (v.source as { freq: number }).freq);
check("unison is the voice twice, spread either side of its pitch", wide.ir.voices.length === 2 && uf[0] < 880 && uf[1] > 880 && close(uf[1] / uf[0], Math.pow(2, 14 / 1200), 1e-4), uf.join(", "));
check("…each at 1/√2 of the level", wide.ir.voices.every((v) => close(v.gain, 0.28 / Math.SQRT2)), `${wide.ir.voices[0].gain}`);
const glides = wide.ir.voices.map((v) => v.env.find((t) => t.prop === "freq")!.keys[1][1]);
check("…and a glide detunes with each copy", glides[0] < 1760 && glides[1] > 1760, glides.join(", "));

const room = probe(probeDoc("test.room", [{ id: "pluck", at: 0.1, dur: 0.2, source: { kind: "osc", wave: "sine", freq: "$tonic" }, echo: { time: 0.25, feedback: 0.5 } }]));
const taps = room.ir.voices;
check("echo is the voice again at each multiple of time", taps.length === 4 && taps.map((v) => v.at).join() === "0.1,0.35,0.6,0.85", taps.map((v) => v.at).join(", "));
check("…each tap feedback times quieter", close(taps[1].gain, 0.5) && close(taps[2].gain, 0.25) && close(taps[3].gain, 0.125), taps.map((v) => v.gain).join(", "));
check("…cut at the canvas rather than run past it", taps[3].dur === 0.15 && !room.issues.some((i) => i.msg.includes("cut short")), `${taps[3].dur}s`);
const far = probe(probeDoc("test.far", [{ id: "pluck", dur: 0.2, source: { kind: "osc", wave: "sine", freq: "$tonic" }, echo: { time: 0.6, feedback: 0.9, taps: 3 } }]));
check("a tap that would start past the canvas is dropped, and said so", far.ir.voices.length === 2 && far.issues.some((i) => i.level === "warn" && i.msg.includes("dropped")), far.issues.map((i) => i.msg).join("; "));

const byHand = [0, 0.09, 0.18, 0.27];
const climb = compileSound(all.get("ss.sfx.levelup")!, sreg).ir;
check("a phrase unrolls to the use voices somebody would have written", climb.voices.length === 4 && climb.voices.map((v) => v.at).join() === byHand.join() && freqs("ss.sfx.levelup").join() === "523.25,659.25,784,1046.5", climb.voices.map((v) => `${v.id}@${v.at}`).join(", "));
const rest = probe(probeDoc("test.rest", [{ id: "f", phrase: { use: "ss.lib.note", step: 0.1, notes: ["$third", null, "$fifth"] } }]));
check("null in a phrase is a rest", rest.ir.voices.length === 2 && rest.ir.voices[1].at === 0.2, rest.ir.voices.map((v) => v.at).join(", "));

const alts = probe(probeDoc("test.alts", [{ id: "grit", filter: { type: "bandpass", freq: "$grit", q: "band" }, repeat: { of: { kind: "noise" }, count: 3, spread: 0.05, grain: 0.01 } }], { takes: 3, jitter: { freq: [0.9, 1.1] } }));
const t2 = alts.ir.variants["take-2"], t3 = alts.ir.variants["take-3"];
check("takes are variants take-2… of the same length", !!t2 && !!t3 && t2.duration === 1 && Object.keys(alts.ir.variants).length === 2, Object.keys(alts.ir.variants).join(", "));
const seeds = (vs: typeof t2.voices) => vs.map((v) => (v.source as { seed: number }).seed).join();
check("…with every scatter reseeded", seeds(alts.ir.voices) !== seeds(t2.voices) && seeds(t2.voices) !== seeds(t3.voices) && alts.ir.voices.map((v) => v.at).join() !== t2.voices.map((v) => v.at).join());
const plain = probe(probeDoc("test.alts", [{ id: "grit", filter: { type: "bandpass", freq: "$grit", q: "band" }, repeat: { of: { kind: "noise" }, count: 3, spread: 0.05, grain: 0.01 } }]));
check("…and the base take exactly what it was without takes", JSON.stringify(plain.ir.voices) === JSON.stringify(alts.ir.voices));
const jt = probe(probeDoc("test.jt", [{ id: "t", source: { kind: "osc", wave: "sine", freq: "$tonic" } }], { takes: 2, jitter: { freq: [0.9, 1.1] } }));
const jf = (jt.ir.variants["take-2"].voices[0].source as { freq: number }).freq;
check("…and its jitter rolled once, inside the range, and frozen", jf !== 880 && jf >= 880 * 0.9 && jf <= 880 * 1.1 && jf === (probe(probeDoc("test.jt", [{ id: "t", source: { kind: "osc", wave: "sine", freq: "$tonic" } }], { takes: 2, jitter: { freq: [0.9, 1.1] } })).ir.variants["take-2"].voices[0].source as { freq: number }).freq, `${jf}Hz`);
const still = probe(probeDoc("test.still", [{ id: "t", source: { kind: "osc", wave: "sine", freq: "$tonic" } }], { takes: 2 }));
check("a take with nothing to vary says so", still.issues.some((i) => i.level === "warn" && i.msg.includes("identical to the base")), still.issues.map((i) => i.msg).join("; ") || "no issue raised");

console.log(`\n${failures === 0 ? "✓ all checks passed" : `✖ ${failures} failed`}`);
process.exit(failures ? 1 : 0);
