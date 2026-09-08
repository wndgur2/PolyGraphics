/**
 * PolyGraphics → WebAudio adapter. Drop this single file into a web game.
 *
 * Consumes compiled sound IR (out/sounds/*.json, or dist/sounds.json). Two
 * integration modes, mirroring the visual adapter's two:
 *
 *   bake(ctx, ir)                  → one AudioBuffer, rendered once.
 *     Play it with playBuffer(). For hot-path sounds — a hit fires hundreds of
 *     times a run and does not deserve a fresh node graph each time. Per-play
 *     variation survives as a playback-rate roll.
 *
 *   play(ctx, dest, ir)            → a live node graph per trigger.
 *     Every voice, filter and envelope built for real, so the document's full
 *     jitter applies. For the handful of sounds worth the nodes.
 *
 * Zero dependencies and no engine import. Deterministic where it claims to be:
 * noise is filled from the seed carried in the IR with the same PRNG the
 * offline renderer uses, and envelopes are pushed as sampled curves from the
 * same interpolation, so the WAV bake in out/wav is what this plays — not an
 * approximation of it. The only per-play randomness is `ir.jitter`, and you can
 * pass your own rng to make even that reproducible.
 */

// ---------------------------------------------------------------- IR types (mirror of src/sound-compile.ts)

export type IRSource =
  | { kind: "osc"; wave: "sine" | "square" | "sawtooth" | "triangle"; freq: number }
  | { kind: "noise"; seed: number };

export interface IRFilter {
  type: "lowpass" | "highpass" | "bandpass";
  freq: number;
  q: number;
}

export interface IREnvTrack {
  prop: "gain" | "freq" | "cutoff";
  keys: [number, number][];
  ease: "linear" | "exp" | "sine";
}

export interface IRVoice {
  id: string;
  at: number;
  dur: number;
  gain: number;
  source: IRSource;
  filter?: IRFilter;
  env: IREnvTrack[];
}

export interface IRSound {
  format: "polygraphics-sound-ir";
  version: 1;
  id: string;
  duration: number;
  gain: number;
  jitter?: { freq?: [number, number]; gain?: [number, number] };
  meta: Record<string, number>;
  voices: IRVoice[];
  variants: Record<string, { duration: number; voices: IRVoice[] }>;
}

// ---------------------------------------------------------------- shared with the renderer

/** Same declick window the offline renderer applies; a cut waveform is a click. */
const DECLICK_S = 0.0015;
const EPS = 1e-4;

/** mulberry32 — the same PRNG src/prng.ts uses, so noise matches the bake. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Mirror of sampleKeys in src/sound-compile.ts. */
function sampleKeys(keys: [number, number][], ease: IREnvTrack["ease"], u: number): number {
  if (u <= keys[0][0]) return keys[0][1];
  const last = keys[keys.length - 1];
  if (u >= last[0]) return last[1];
  let i = 0;
  while (i < keys.length - 2 && keys[i + 1][0] < u) i++;
  const [t0, v0] = keys[i];
  const [t1, v1] = keys[i + 1];
  const f = t1 === t0 ? 0 : (u - t0) / (t1 - t0);
  if (ease === "linear") return v0 + (v1 - v0) * f;
  if (ease === "sine") return v0 + (v1 - v0) * (1 - Math.cos(Math.PI * f)) / 2;
  const a = Math.max(EPS, v0);
  const b = Math.max(EPS, v1);
  return a * Math.pow(b / a, f);
}

const trackOf = (v: IRVoice, prop: IREnvTrack["prop"]) => v.env.find((t) => t.prop === prop);

/**
 * Envelopes go in as sampled curves rather than as ramp calls.
 *
 * setValueCurveAtTime is the only automation that reproduces an arbitrary ease
 * exactly; a chain of exponentialRampToValueAtTime would quietly re-interpolate
 * every `sine` and `linear` track into an exponential one, and the live sound
 * would drift from the WAV that regression tests are guarding.
 */
function curveLength(dur: number, sampleRate: number): number {
  return Math.max(64, Math.min(8192, Math.ceil((dur * sampleRate) / 8)));
}

function envCurve(v: IRVoice, prop: IREnvTrack["prop"], n: number, scale = 1): Float32Array | null {
  const t = trackOf(v, prop);
  if (!t) return null;
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = sampleKeys(t.keys, t.ease, i / (n - 1)) * scale;
  return out;
}

function gainCurve(v: IRVoice, level: number, n: number): Float32Array {
  const t = trackOf(v, "gain");
  const fadeN = Math.max(1, Math.min(Math.floor(n / 2), Math.round((DECLICK_S / v.dur) * n)));
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    let g = level * (t ? sampleKeys(t.keys, t.ease, i / (n - 1)) : 1);
    if (i < fadeN) g *= i / fadeN;
    else if (i >= n - fadeN) g *= (n - 1 - i) / fadeN;
    out[i] = g;
  }
  return out;
}

// ---------------------------------------------------------------- noise buffers

const noiseCache = new WeakMap<BaseAudioContext, Map<string, AudioBuffer>>();

function noiseBuffer(ctx: BaseAudioContext, seed: number, dur: number): AudioBuffer {
  const frames = Math.max(1, Math.round(dur * ctx.sampleRate));
  const key = `${seed}:${frames}`;
  let cache = noiseCache.get(ctx);
  if (!cache) noiseCache.set(ctx, (cache = new Map()));
  const hit = cache.get(key);
  if (hit) return hit;
  const buf = ctx.createBuffer(1, frames, ctx.sampleRate);
  const data = buf.getChannelData(0);
  const rng = mulberry32(seed);
  for (let i = 0; i < frames; i++) data[i] = rng() * 2 - 1;
  cache.set(key, buf);
  return buf;
}

// ---------------------------------------------------------------- play

export interface PlayOptions {
  variant?: string;
  /** Audio-clock time to start at; defaults to now. */
  when?: number;
  /** Extra level on top of the document's own, e.g. an SFX bus setting. */
  gain?: number;
  /** Supply your own for reproducible jitter (tests, replays). */
  rng?: () => number;
}

export function rollJitter(ir: IRSound, rng: () => number = Math.random): { freq: number; gain: number } {
  const pick = (r?: [number, number]) => (r ? r[0] + rng() * (r[1] - r[0]) : 1);
  return { freq: pick(ir.jitter?.freq), gain: pick(ir.jitter?.gain) };
}

function voicesOf(ir: IRSound, variant?: string): { voices: IRVoice[]; duration: number } {
  if (!variant) return { voices: ir.voices, duration: ir.duration };
  const v = ir.variants[variant];
  if (!v) throw new Error(`${ir.id}: unknown variant "${variant}"`);
  return { voices: v.voices, duration: v.duration };
}

/**
 * WebAudio reads Q in dB for lowpass and highpass and linearly for bandpass —
 * a spec wrinkle, not a choice. The IR is linear throughout, so convert.
 */
function qFor(f: IRFilter): number {
  return f.type === "bandpass" ? f.q : 20 * Math.log10(Math.max(EPS, f.q));
}

function buildVoice(ctx: BaseAudioContext, dest: AudioNode, v: IRVoice, t0: number, master: number, jFreq: number): void {
  const start = t0 + v.at;
  const stop = start + v.dur;
  const n = curveLength(v.dur, ctx.sampleRate);

  const gain = ctx.createGain();
  gain.gain.setValueCurveAtTime(gainCurve(v, v.gain * master, n), start, v.dur);

  let node: AudioNode;
  let stopper: { stop(t: number): void };
  if (v.source.kind === "noise") {
    const src = ctx.createBufferSource();
    src.buffer = noiseBuffer(ctx, v.source.seed, v.dur);
    node = src;
    stopper = src;
    src.start(start);
  } else {
    const osc = ctx.createOscillator();
    osc.type = v.source.wave;
    const freq = envCurve(v, "freq", n, jFreq);
    if (freq) osc.frequency.setValueCurveAtTime(freq, start, v.dur);
    else osc.frequency.setValueAtTime(v.source.freq * jFreq, start);
    node = osc;
    stopper = osc;
    osc.start(start);
  }
  stopper.stop(stop + 0.02);

  if (v.filter) {
    const biquad = ctx.createBiquadFilter();
    biquad.type = v.filter.type;
    biquad.Q.setValueAtTime(qFor(v.filter), start);
    const cut = envCurve(v, "cutoff", n, jFreq);
    if (cut) biquad.frequency.setValueCurveAtTime(cut, start, v.dur);
    else biquad.frequency.setValueAtTime(v.filter.freq * jFreq, start);
    node.connect(biquad);
    biquad.connect(gain);
  } else {
    node.connect(gain);
  }
  gain.connect(dest);
}

/** Build and fire the full node graph for one trigger. */
export function play(ctx: BaseAudioContext, dest: AudioNode, ir: IRSound, opts: PlayOptions = {}): void {
  const { voices } = voicesOf(ir, opts.variant);
  const j = rollJitter(ir, opts.rng);
  const t0 = opts.when ?? ctx.currentTime;
  const master = ir.gain * j.gain * (opts.gain ?? 1);
  for (const v of voices) buildVoice(ctx, dest, v, t0, master, j.freq);
}

// ---------------------------------------------------------------- bake

/**
 * Render a sound to a single buffer, once, offline. The cheap path: a hit that
 * fires three hundred times a run costs one BufferSource per trigger instead of
 * a graph. `ctx` is only read for its sample rate.
 */
export async function bake(ctx: BaseAudioContext, ir: IRSound, variant?: string): Promise<AudioBuffer> {
  const { voices, duration } = voicesOf(ir, variant);
  const OAC = (globalThis as { OfflineAudioContext?: typeof OfflineAudioContext }).OfflineAudioContext;
  if (!OAC) throw new Error("bake() needs OfflineAudioContext — use play() instead");
  const off = new OAC(1, Math.max(1, Math.ceil(duration * ctx.sampleRate)), ctx.sampleRate);
  for (const v of voices) buildVoice(off, off.destination, v, 0, ir.gain, 1);
  return off.startRendering();
}

export interface BufferPlayOptions {
  when?: number;
  gain?: number;
  /** Jitter to apply as a rate roll; pass rollJitter(ir) to reuse the document's. */
  rate?: number;
}

/** Play a baked buffer. Pitch jitter becomes a playback-rate roll. */
export function playBuffer(ctx: BaseAudioContext, dest: AudioNode, buf: AudioBuffer, opts: BufferPlayOptions = {}): void {
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.playbackRate.value = opts.rate ?? 1;
  if (opts.gain !== undefined && opts.gain !== 1) {
    const g = ctx.createGain();
    g.gain.value = opts.gain;
    src.connect(g);
    g.connect(dest);
  } else {
    src.connect(dest);
  }
  src.start(opts.when ?? ctx.currentTime);
}
