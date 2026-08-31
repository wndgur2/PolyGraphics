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
import { renderPCM, describe, toWav, SAMPLE_RATE } from "../src/sound-render.js";
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

console.log(`\n${failures === 0 ? "✓ all checks passed" : `✖ ${failures} failed`}`);
process.exit(failures ? 1 : 0);
