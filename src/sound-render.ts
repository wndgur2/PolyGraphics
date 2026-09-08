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

// ---------------------------------------------------------------- weighting

/**
 * A biquad with its coefficients handed in. The `Biquad` above is the IR's
 * filter and speaks the IR's vocabulary; this one is for the measurements,
 * which need shapes no document can ask for — a shelf, a fixed weighting.
 */
class Filt {
  private x1 = 0; private x2 = 0; private y1 = 0; private y2 = 0;
  constructor(private b0: number, private b1: number, private b2: number, private a1: number, private a2: number) {}
  step(x: number): number {
    const y = this.b0 * x + this.b1 * this.x1 + this.b2 * this.x2 - this.a1 * this.y1 - this.a2 * this.y2;
    this.x2 = this.x1; this.x1 = x;
    this.y2 = this.y1; this.y1 = y;
    return y;
  }
}

/** RBJ cookbook coefficients, so a measurement filter is the same shape at any rate. */
function rbj(type: "lowpass" | "highpass" | "highshelf", f0: number, q: number, sr: number, gainDb = 0): Filt {
  const A = Math.pow(10, gainDb / 40);
  const w0 = (2 * Math.PI * f0) / sr;
  const cos = Math.cos(w0), sin = Math.sin(w0);
  const alpha = sin / (2 * q);
  let b0: number, b1: number, b2: number, a0: number, a1: number, a2: number;
  if (type === "highshelf") {
    const s = 2 * Math.sqrt(A) * alpha;
    b0 = A * (A + 1 + (A - 1) * cos + s); b1 = -2 * A * (A - 1 + (A + 1) * cos); b2 = A * (A + 1 + (A - 1) * cos - s);
    a0 = A + 1 - (A - 1) * cos + s; a1 = 2 * (A - 1 - (A + 1) * cos); a2 = A + 1 - (A - 1) * cos - s;
  } else if (type === "highpass") {
    b0 = (1 + cos) / 2; b1 = -(1 + cos); b2 = b0; a0 = 1 + alpha; a1 = -2 * cos; a2 = 1 - alpha;
  } else {
    b0 = (1 - cos) / 2; b1 = 1 - cos; b2 = b0; a0 = 1 + alpha; a1 = -2 * cos; a2 = 1 - alpha;
  }
  return new Filt(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0);
}

function through(pcm: Float32Array, filts: Filt[]): Float32Array {
  const out = new Float32Array(pcm.length);
  for (let i = 0; i < pcm.length; i++) {
    let s = pcm[i];
    for (const f of filts) s = f.step(s);
    out[i] = s;
  }
  return out;
}

/**
 * ITU-R BS.1770 K-weighting: a +4dB shelf above 1.7kHz for the head, and a
 * highpass under 40Hz for what nobody hears. RMS says how much signal there
 * is; this says how loud it is, which is what the set has to hold together
 * on. The shelf is written the way the standard derives it rather than from
 * the cookbook, because the two disagree by half a dB in the octave that
 * matters most; the highpass is the cookbook's and agrees to a hundredth.
 */
function kShelf(sr: number): Filt {
  const G = 3.999843853973347, Q = 0.7071752369554196, f0 = 1681.974450955533;
  const K = Math.tan((Math.PI * f0) / sr);
  const Vh = Math.pow(10, G / 20);
  const Vb = Math.pow(Vh, 0.4996667741545416);
  const a0 = 1 + K / Q + K * K;
  return new Filt((Vh + (Vb * K) / Q + K * K) / a0, (2 * (K * K - Vh)) / a0, (Vh - (Vb * K) / Q + K * K) / a0, (2 * (K * K - 1)) / a0, (1 - K / Q + K * K) / a0);
}
const kWeight = (pcm: Float32Array, sr: number): Float32Array =>
  through(pcm, [kShelf(sr), rbj("highpass", 38.13547087602444, 0.5003270373238773, sr)]);
/**
 * The standard's constant: what the shelf adds at 1kHz, taken back off so a
 * full-scale 1kHz sine reads -3dB the way its RMS does, and a loudness here is
 * comparable to an LKFS figure anywhere else.
 */
const K_OFFSET_DB = 0.691;

/**
 * What a small speaker keeps: nothing under 250Hz, little over 8kHz. The
 * same two filters the gallery's phone toggle puts in the way, so what the
 * lint measures is what the toggle plays.
 */
export const PHONE_LO_HZ = 250;
export const PHONE_HI_HZ = 8000;
const phone = (pcm: Float32Array, sr: number): Float32Array =>
  through(pcm, [rbj("highpass", PHONE_LO_HZ, 0.7071, sr), rbj("lowpass", PHONE_HI_HZ, 0.7071, sr)]);

/** Loudest 50ms anywhere in [from, last]: the instant that reaches the ear. */
function momentary(x: Float32Array, sr: number, from: number, last: number): number {
  const n = Math.min(Math.round(0.05 * sr), last - from + 1);
  if (n <= 0) return 0;
  const hop = Math.max(1, n >> 2);
  let best = 0;
  for (let s = from; s + n - 1 <= last; s += hop) {
    let e = 0;
    for (let i = s; i < s + n; i++) e += x[i] * x[i];
    best = Math.max(best, e / n);
  }
  return Math.sqrt(best);
}

/**
 * Peak between the samples. A bake that reads -0.3dBFS sample by sample can
 * pass 0dB in the DAC, and the buffer path resamples it again on top. Four
 * times oversampled through a windowed sinc, the way the standard does it.
 */
function truePeak(pcm: Float32Array): number {
  const H = 6;
  const taps: number[][] = [];
  for (let p = 1; p < 4; p++) {
    const row: number[] = [];
    for (let k = -H; k < H; k++) {
      const t = k + p / 4;
      const sinc = t === 0 ? 1 : Math.sin(Math.PI * t) / (Math.PI * t);
      row.push(sinc * (0.5 + 0.5 * Math.cos((Math.PI * t) / H)));
    }
    taps.push(row);
  }
  let peak = 0;
  for (let i = 0; i < pcm.length; i++) {
    peak = Math.max(peak, Math.abs(pcm[i]));
    for (const row of taps) {
      let v = 0;
      for (let k = -H; k < H; k++) {
        const j = i - k;
        if (j >= 0 && j < pcm.length) v += pcm[j] * row[k + H];
      }
      peak = Math.max(peak, Math.abs(v));
    }
  }
  return peak;
}

/**
 * Where the energy sits: the spectral centroid, and the share below 250Hz,
 * between there and 2kHz, and above. Averaged power over the sounding extent
 * in 2048-point frames. `brightness` (zero crossings) stays for continuity;
 * this is the number that can see a low fundamental under a bright edge.
 */
function spectrum(pcm: Float32Array, sr: number, from: number, last: number): { centroidHz: number; bands: { low: number; mid: number; high: number } } {
  const n = 2048;
  const re = new Float64Array(n), im = new Float64Array(n);
  const acc = new Float64Array(n / 2);
  const win = new Float64Array(n);
  for (let i = 0; i < n; i++) win[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1));
  for (let s = from; s <= last; s += n / 2) {
    for (let i = 0; i < n; i++) {
      const j = s + i;
      re[i] = (j <= last ? pcm[j] : 0) * win[i];
      im[i] = 0;
    }
    fft(re, im);
    for (let k = 1; k < n / 2; k++) acc[k] += re[k] * re[k] + im[k] * im[k];
  }
  let total = 0, weighted = 0, low = 0, mid = 0, high = 0;
  for (let k = 1; k < n / 2; k++) {
    const f = (k * sr) / n;
    total += acc[k];
    weighted += f * acc[k];
    if (f < PHONE_LO_HZ) low += acc[k];
    else if (f < 2000) mid += acc[k];
    else high += acc[k];
  }
  const r3 = (x: number) => Math.round(x * 1000) / 1000;
  return {
    centroidHz: total > 0 ? Math.round(weighted / total) : 0,
    bands: total > 0 ? { low: r3(low / total), mid: r3(mid / total), high: r3(high / total) } : { low: 0, mid: 0, high: 0 },
  };
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
  /**
   * K-weighted level over the sounding extent, dBFS — how loud, rather than
   * how much. The number the family bands in `audio.loudness` are held on.
   */
  loudnessDb: number;
  /** Loudest 50ms, K-weighted: the instant that reaches the ear. */
  momentaryDb: number;
  /** The same instant through what a phone speaker keeps (250Hz–8kHz). */
  phoneDb: number;
  /** `momentaryDb - phoneDb`: what the phone loses. Past a few dB, the low end is carrying the sound. */
  phoneLossDb: number;
  /** Peak between the samples, four times oversampled, dBTP. */
  truePeakDb: number;
  /** Spectral centroid, Hz. */
  centroidHz: number;
  /** Share of energy below 250Hz, 250Hz–2kHz, and above 2kHz. */
  bands: { low: number; mid: number; high: number };
  /** Seconds from onset to the last sample within 60dB of peak. */
  tailS: number;
}

const db = (x: number) => (x <= 0 ? -Infinity : Math.round(20 * Math.log10(x) * 10) / 10);
const r1 = (x: number) => Math.round(x * 10) / 10;

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

  let tail = last;
  while (tail > first && Math.abs(pcm[tail]) < peak * 0.001) tail--;

  const k = kWeight(pcm, sr);
  let ksum = 0;
  for (let i = first; i <= last; i++) ksum += k[i] * k[i];
  const loud = Math.sqrt(ksum / Math.max(1, last - first + 1));
  const moment = momentary(k, sr, first, last);
  const onPhone = momentary(kWeight(phone(pcm, sr), sr), sr, first, last);
  const { centroidHz, bands } = spectrum(pcm, sr, first, last);
  return {
    duration: Math.round((pcm.length / sr) * 10000) / 10000,
    peak: Math.round(peak * 10000) / 10000,
    rms: Math.round(rms * 10000) / 10000,
    peakDb: db(peak),
    rmsDb: db(rms),
    brightness: Math.round((cross / (pcm.length / sr)) * 10) / 10,
    attackMs: Math.round(((rise - first) / sr) * 10000) / 10,
    clipped,
    loudnessDb: r1(db(loud) - K_OFFSET_DB),
    momentaryDb: r1(db(moment) - K_OFFSET_DB),
    phoneDb: r1(db(onPhone) - K_OFFSET_DB),
    phoneLossDb: moment > 0 && onPhone > 0 ? Math.round((db(moment) - db(onPhone)) * 10) / 10 : 0,
    truePeakDb: db(truePeak(pcm)),
    centroidHz,
    bands,
    tailS: Math.round(((tail - first) / sr) * 10000) / 10000,
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

// ---------------------------------------------------------------- spectrogram

/**
 * The picture that shows what the waveform cannot: whether a voice is a
 * harmonic comb or a wash of noise, where the onset really is, and whether
 * the top half of the picture is empty — which is what a phone hears.
 *
 * Log frequency from 60Hz to 16kHz at twelve rows per octave, so an octave is
 * the same height everywhere and a harmonic series is a ladder with rungs
 * that get closer. 80dB of range, peak-normalized like the waveform, for the
 * same reason: the question is what shape the sound has. One column per
 * 1/320th of the take, whatever its length, so the picture sits under the
 * waveform on the same time axis. Deterministic: same PCM, same picture.
 */
export interface Spectrogram {
  width: number;
  height: number;
  /** Row-major, top row = highest frequency; 0 = -80dB or below, 255 = peak. */
  data: Uint8Array;
}

const SPEC_FFT = 2048;
const SPEC_LO_HZ = 60;
const SPEC_HI_HZ = 16000;
const SPEC_RANGE_DB = 80;

/** In-place iterative radix-2 FFT. `re.length` must be a power of two. */
function fft(re: Float64Array, im: Float64Array): void {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k, b = a + len / 2;
        const vr = re[b] * cr - im[b] * ci;
        const vi = re[b] * ci + im[b] * cr;
        re[b] = re[a] - vr; im[b] = im[a] - vi;
        re[a] += vr; im[a] += vi;
        const t = cr * wr - ci * wi;
        ci = cr * wi + ci * wr;
        cr = t;
      }
    }
  }
}

export function spectrogram(pcm: Float32Array, sr = SAMPLE_RATE, width = 320, rows = 96): Spectrogram {
  const n = SPEC_FFT;
  const cols = Math.max(1, Math.min(width, pcm.length));
  const hop = pcm.length / cols;
  const win = new Float64Array(n);
  for (let i = 0; i < n; i++) win[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1));
  const re = new Float64Array(n), im = new Float64Array(n);
  // Fractional FFT bin per row, bottom row lowest; magnitude is interpolated
  // between the two bins either side so the bottom octaves are not staircases.
  const bins = new Float64Array(rows);
  for (let r = 0; r < rows; r++) bins[r] = (SPEC_LO_HZ * Math.pow(SPEC_HI_HZ / SPEC_LO_HZ, r / (rows - 1)) * n) / sr;

  const mags = new Float64Array(cols * rows);
  let max = 0;
  for (let c = 0; c < cols; c++) {
    const start = Math.round((c + 0.5) * hop) - n / 2;
    for (let i = 0; i < n; i++) {
      const s = start + i;
      re[i] = (s >= 0 && s < pcm.length ? pcm[s] : 0) * win[i];
      im[i] = 0;
    }
    fft(re, im);
    for (let r = 0; r < rows; r++) {
      const b0 = Math.floor(bins[r]);
      const f = bins[r] - b0;
      const m0 = Math.hypot(re[b0], im[b0]);
      const m1 = Math.hypot(re[b0 + 1], im[b0 + 1]);
      const m = m0 + (m1 - m0) * f;
      mags[(rows - 1 - r) * cols + c] = m;
      if (m > max) max = m;
    }
  }

  const data = new Uint8Array(cols * rows);
  if (max > 0)
    for (let i = 0; i < data.length; i++) {
      const db = mags[i] > 0 ? 20 * Math.log10(mags[i] / max) : -Infinity;
      data[i] = Math.round(Math.max(0, 1 + db / SPEC_RANGE_DB) * 255);
    }
  return { width: cols, height: rows, data };
}

/**
 * The spectrogram in the gallery's own inks — ground, then the spore teal the
 * waveform is drawn in, then bone at the peak — as RGBA, ready for a PNG.
 */
export function spectrogramRGBA(s: Spectrogram): Uint8Array {
  const stops: [number, [number, number, number]][] = [
    [0, [11, 13, 18]],
    [0.4, [24, 58, 74]],
    [0.8, [88, 232, 216]],
    [1, [234, 244, 255]],
  ];
  const out = new Uint8Array(s.width * s.height * 4);
  for (let i = 0; i < s.data.length; i++) {
    const v = s.data[i] / 255;
    let k = 0;
    while (k < stops.length - 2 && stops[k + 1][0] < v) k++;
    const [t0, c0] = stops[k], [t1, c1] = stops[k + 1];
    const f = (v - t0) / (t1 - t0);
    out[i * 4] = Math.round(c0[0] + (c1[0] - c0[0]) * f);
    out[i * 4 + 1] = Math.round(c0[1] + (c1[1] - c0[1]) * f);
    out[i * 4 + 2] = Math.round(c0[2] + (c1[2] - c0[2]) * f);
    out[i * 4 + 3] = 255;
  }
  return out;
}

/**
 * The bake, read back. `regress` and the inspect page's `--against` both
 * start from a WAV somebody accepted, and this is the one reader for it:
 * 16-bit mono PCM, the only shape `toWav` writes.
 */
export function fromWav(buf: Buffer): { pcm: Float32Array; sampleRate: number } {
  if (buf.toString("ascii", 0, 4) !== "RIFF" || buf.toString("ascii", 8, 12) !== "WAVE") throw new Error("not a WAV");
  const channels = buf.readUInt16LE(22);
  const sampleRate = buf.readUInt32LE(24);
  const bits = buf.readUInt16LE(34);
  if (channels !== 1 || bits !== 16) throw new Error(`expected 16-bit mono, got ${bits}-bit ×${channels}`);
  // Walk the chunks to the data; a bake from here has it at 44, a WAV from
  // elsewhere may carry a LIST chunk first.
  let off = 12;
  while (off + 8 <= buf.length) {
    const id = buf.toString("ascii", off, off + 4);
    const size = buf.readUInt32LE(off + 4);
    if (id === "data") {
      const n = Math.floor(Math.min(size, buf.length - off - 8) / 2);
      const pcm = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        const v = buf.readInt16LE(off + 8 + i * 2);
        pcm[i] = v < 0 ? v / 32768 : v / 32767;
      }
      return { pcm, sampleRate };
    }
    off += 8 + size + (size & 1);
  }
  throw new Error("WAV has no data chunk");
}
