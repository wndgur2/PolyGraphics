/**
 * Deterministic offline renderer: sound IR → PCM → WAV.
 *
 * Same IR + same sample rate → byte-identical samples, which is what makes a
 * sound regression-testable at all. Every source of randomness is a seeded
 * PRNG carried in the IR; there is no wall clock and no Math.random anywhere.
 *
 * The bake is also the measurement instrument. An agent authoring these
 * documents cannot listen to them, so `describe()` returns the numbers that
 * stand in for ears — peak, RMS, and how bright the result is — and the CLI
 * lints the set for clipping and for one sound sitting far off the others.
 */
import { sampleKeys, type IREnvTrack, type IRSound, type IRVoice } from "./sound-compile.js";
import { mulberry32 } from "./prng.js";

export const SAMPLE_RATE = 44100;

/**
 * Fade applied to both ends of every voice. A waveform that starts or stops
 * mid-cycle is a step edge, and a step edge is a click — audible, and loud in
 * the spectrum. This is an engine-level detail, never something to author.
 */
const DECLICK_S = 0.0015;

// ---------------------------------------------------------------- envelopes

const sampleTrack = (t: IREnvTrack, u: number): number => sampleKeys(t.keys, t.ease, u);

function track(voice: IRVoice, prop: IREnvTrack["prop"]): IREnvTrack | undefined {
  return voice.env.find((t) => t.prop === prop);
}

// ---------------------------------------------------------------- oscillators

/**
 * PolyBLEP: rounds the discontinuity of a saw/square over one sample so the
 * harmonics above Nyquist fold away instead of back into the audible band. The
 * browser's OscillatorNode is band-limited too, so the bake and the live voice
 * agree; a naive stairstep here would make the WAV a different sound.
 */
function blep(t: number, dt: number): number {
  if (t < dt) {
    const x = t / dt;
    return x + x - x * x - 1;
  }
  if (t > 1 - dt) {
    const x = (t - 1) / dt;
    return x * x + x + x + 1;
  }
  return 0;
}

function osc(wave: string, phase: number, dt: number): number {
  switch (wave) {
    case "sine":
      return Math.sin(2 * Math.PI * phase);
    case "sawtooth":
      return 2 * phase - 1 - blep(phase, dt);
    case "square":
      return (phase < 0.5 ? 1 : -1) + blep(phase, dt) - blep((phase + 0.5) % 1, dt);
    default:
      // Triangle: harmonics fall off as 1/n², so the naive form's aliases are
      // already ~30dB down at audible pitches — not worth integrating a square.
      return phase < 0.5 ? 4 * phase - 1 : 3 - 4 * phase;
  }
}

// ---------------------------------------------------------------- filter

/**
 * RBJ biquad, direct form I — the same formulas WebAudio's BiquadFilterNode
 * uses, so a swept bandpass here matches a swept bandpass there. Coefficients
 * are recomputed per sample only while a `cutoff` track is actually moving.
 */
class Biquad {
  private b0 = 1; private b1 = 0; private b2 = 0; private a1 = 0; private a2 = 0;
  private x1 = 0; private x2 = 0; private y1 = 0; private y2 = 0;

  constructor(private type: string, private sr: number) {}

  set(freq: number, q: number): void {
    const w0 = (2 * Math.PI * Math.min(Math.max(freq, 10), this.sr * 0.45)) / this.sr;
    const cos = Math.cos(w0);
    const alpha = Math.sin(w0) / (2 * Math.max(q, 1e-4));
    let b0: number, b1: number, b2: number;
    const a0 = 1 + alpha;
    if (this.type === "lowpass") {
      b0 = (1 - cos) / 2; b1 = 1 - cos; b2 = b0;
    } else if (this.type === "highpass") {
      b0 = (1 + cos) / 2; b1 = -(1 + cos); b2 = b0;
    } else {
      b0 = alpha; b1 = 0; b2 = -alpha; // bandpass, constant 0dB peak gain
    }
    this.b0 = b0 / a0; this.b1 = b1 / a0; this.b2 = b2 / a0;
    this.a1 = (-2 * cos) / a0; this.a2 = (1 - alpha) / a0;
  }

  step(x: number): number {
    const y = this.b0 * x + this.b1 * this.x1 + this.b2 * this.x2 - this.a1 * this.y1 - this.a2 * this.y2;
    this.x2 = this.x1; this.x1 = x;
    this.y2 = this.y1; this.y1 = y;
    return y;
  }
}

// ---------------------------------------------------------------- render

export interface RenderSoundOptions {
  sampleRate?: number;
  variant?: string;
}

/** IR → mono float samples in [-1, 1]. */
export function renderPCM(ir: IRSound, opts: RenderSoundOptions = {}): Float32Array {
  const sr = opts.sampleRate ?? SAMPLE_RATE;
  const sel = opts.variant ? ir.variants[opts.variant] : undefined;
  if (opts.variant && !sel) throw new Error(`${ir.id}: unknown variant "${opts.variant}"`);
  const voices = sel ? sel.voices : ir.voices;
  const duration = sel ? sel.duration : ir.duration;
  const out = new Float32Array(Math.ceil(duration * sr));

  for (const v of voices) renderVoice(v, out, sr, ir.gain);

  for (let i = 0; i < out.length; i++) out[i] = Math.max(-1, Math.min(1, out[i]));
  return out;
}

function renderVoice(v: IRVoice, out: Float32Array, sr: number, master: number): void {
  const start = Math.round(v.at * sr);
  const n = Math.round(v.dur * sr);
  if (n <= 0 || start >= out.length) return;

  const gainT = track(v, "gain");
  const freqT = track(v, "freq");
  const cutT = track(v, "cutoff");
  const noise = v.source.kind === "noise" ? mulberry32(v.source.seed) : null;
  const baseFreq = v.source.kind === "osc" ? v.source.freq : 0;
  const filter = v.filter ? new Biquad(v.filter.type, sr) : null;
  if (filter && v.filter && !cutT) filter.set(v.filter.freq, v.filter.q);

  const fade = Math.max(1, Math.min(Math.floor(n / 2), Math.round(DECLICK_S * sr)));
  let phase = 0;

  for (let i = 0; i < n; i++) {
    const idx = start + i;
    if (idx >= out.length) break;
    const u = i / n;

    let s: number;
    if (noise) {
      s = noise() * 2 - 1;
    } else {
      const f = freqT ? sampleTrack(freqT, u) : baseFreq;
      const dt = f / sr;
      s = osc((v.source as { wave: string }).wave, phase, dt);
      phase += dt;
      if (phase >= 1) phase -= Math.floor(phase);
    }

    if (filter && v.filter) {
      if (cutT) filter.set(sampleTrack(cutT, u), v.filter.q);
      s = filter.step(s);
    }

    let g = v.gain * master * (gainT ? sampleTrack(gainT, u) : 1);
    if (i < fade) g *= i / fade;
    else if (i >= n - fade) g *= (n - i) / fade;

    out[idx] += s * g;
  }
}

// ---------------------------------------------------------------- measurement

export interface Descriptors {
  duration: number;
  peak: number;
  rms: number;
  peakDb: number;
  rmsDb: number;
  /** Zero crossings per second — a cheap brightness proxy, no FFT needed. */
  brightness: number;
  /**
   * Milliseconds from the first sounding sample to 90% of peak — how fast the
   * sound arrives.
   *
   * The other four numbers say how loud a document is and roughly how bright.
   * None of them can see the one property an instrument has to hold constant
   * while it is played at four different lengths, which is exactly the property
   * an envelope written in fractions of a span cannot hold. Measured from the
   * onset rather than from t=0, so a voice that starts late reads as fast, not
   * as slow.
   */
  attackMs: number;
  clipped: number;
}

const db = (x: number) => (x <= 0 ? -Infinity : Math.round(20 * Math.log10(x) * 10) / 10);

export function describe(pcm: Float32Array, sr = SAMPLE_RATE): Descriptors {
  let peak = 0, cross = 0, clipped = 0;
  for (let i = 0; i < pcm.length; i++) {
    const a = Math.abs(pcm[i]);
    if (a > peak) peak = a;
    if (a >= 0.999) clipped++;
    if (i > 0 && (pcm[i] >= 0) !== (pcm[i - 1] >= 0)) cross++;
  }

  /**
   * RMS is measured over the sounding extent, not over the canvas. A sound
   * that ends early is not quieter than one that doesn't — it is shorter — and
   * a set-level loudness comparison that cannot tell those apart sends you to
   * raise the gain on the wrong sound.
   */
  const floor = peak * 0.01; // -40dB relative
  let first = 0, last = pcm.length - 1;
  while (first < pcm.length && Math.abs(pcm[first]) < floor) first++;
  while (last > first && Math.abs(pcm[last]) < floor) last--;
  let sum = 0;
  for (let i = first; i <= last; i++) sum += pcm[i] * pcm[i];
  const rms = Math.sqrt(sum / Math.max(1, last - first + 1));

  let rise = first;
  while (rise <= last && Math.abs(pcm[rise]) < peak * 0.9) rise++;
  return {
    duration: Math.round((pcm.length / sr) * 10000) / 10000,
    peak: Math.round(peak * 10000) / 10000,
    rms: Math.round(rms * 10000) / 10000,
    peakDb: db(peak),
    rmsDb: db(rms),
    brightness: Math.round((cross / (pcm.length / sr)) * 10) / 10,
    attackMs: Math.round(((rise - first) / sr) * 10000) / 10,
    clipped,
  };
}

// ---------------------------------------------------------------- wav

/** 16-bit mono PCM WAV — the bake, and the thing `regress` hashes. */
export function toWav(pcm: Float32Array, sr = SAMPLE_RATE): Buffer {
  const bytes = pcm.length * 2;
  const buf = Buffer.alloc(44 + bytes);
  buf.write("RIFF", 0);
  buf.writeUInt32LE(36 + bytes, 4);
  buf.write("WAVE", 8);
  buf.write("fmt ", 12);
  buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20); // PCM
  buf.writeUInt16LE(1, 22); // mono
  buf.writeUInt32LE(sr, 24);
  buf.writeUInt32LE(sr * 2, 28);
  buf.writeUInt16LE(2, 32);
  buf.writeUInt16LE(16, 34);
  buf.write("data", 36);
  buf.writeUInt32LE(bytes, 40);
  for (let i = 0; i < pcm.length; i++) {
    const s = Math.max(-1, Math.min(1, pcm[i]));
    buf.writeInt16LE(Math.round(s < 0 ? s * 32768 : s * 32767), 44 + i * 2);
  }
  return buf;
}

/**
 * Min/max envelope as an SVG path — the waveform you look at when you can't
 * listen. Peak-normalized on purpose: the question a waveform answers is what
 * shape the sound has, and at -14dBFS the true-scale drawing of a hit is a
 * flat line with a smudge on it. Absolute level is in the numbers beside it.
 */
export function waveformSvg(pcm: Float32Array, w = 640, h = 120): string {
  const step = Math.max(1, Math.floor(pcm.length / w));
  let peak = 0;
  for (let i = 0; i < pcm.length; i++) peak = Math.max(peak, Math.abs(pcm[i]));
  const norm = peak > 0 ? 1 / peak : 1;
  const top: string[] = [], bottom: string[] = [];
  for (let x = 0; x < w; x++) {
    let lo = 0, hi = 0;
    for (let i = x * step; i < Math.min((x + 1) * step, pcm.length); i++) {
      if (pcm[i] < lo) lo = pcm[i];
      if (pcm[i] > hi) hi = pcm[i];
    }
    const y = (v: number) => Math.round(((1 - v * norm) * h) / 2 * 100) / 100;
    top.push(`${x},${y(hi)}`);
    bottom.unshift(`${x},${y(lo)}`);
  }
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">`,
    `<line x1="0" y1="${h / 2}" x2="${w}" y2="${h / 2}" stroke="#3a4a5c" stroke-width="1"/>`,
    `<polygon points="${top.join(" ")} ${bottom.join(" ")}" fill="#58e8d8"/>`,
    `</svg>`,
  ].join("");
}
