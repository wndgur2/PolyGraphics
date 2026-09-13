/**
 * Compiler: sound document → engine-neutral IR.
 *
 * Same contract as the visual compiler — everything authoring-time is resolved
 * away, so an adapter is a dumb interpreter with no token table, no grammar and
 * no PRNG of its own:
 *   token references → concrete Hz and 0..1 levels
 *   variants         → pre-applied full voice lists
 *   `use` composition→ inlined, with the parent's offset and gain folded in
 *   seeded `repeat`  → expanded to concrete grains
 *   `unison` / `echo`→ expanded to the copies they stand for
 *   `phrase`         → unrolled to the `use` voices it stands for
 *   `takes`          → alternates compiled as variants, reseeded and rolled
 *   implicit spans   → concrete `at` / `dur` seconds
 *
 * Unlike the visual side, the offline renderer consumes this IR too rather than
 * re-walking the document. Whatever you hear in the bake is what an engine
 * plays, by construction.
 */
import type { Adsr, Echo, EnvTrack, Filter, Sound, Source, UseVoice, Voice } from "./sound-schema.js";
import { VoiceSchema } from "./sound-schema.js";
import type { Issue } from "./render.js";
import { resolveNumber, resolvePitch, type AudioTokens, type Tokens } from "./tokens.js";
import { mulberry32, hashSeed } from "./prng.js";

export interface SoundRegistry {
  sounds: Map<string, Sound>;
  tokens: Tokens;
}

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
  at: number; // seconds from t=0
  dur: number; // seconds
  gain: number; // 0..1, parent gains already folded in
  source: IRSource;
  filter?: IRFilter;
  env: IREnvTrack[];
}

export interface IRSound {
  format: "polygraphics-sound-ir";
  version: 1;
  id: string;
  name: string;
  description: string;
  tags: string[];
  duration: number;
  gain: number;
  jitter?: { freq?: [number, number]; gain?: [number, number] };
  meta: Record<string, number>;
  voices: IRVoice[];
  variants: Record<string, { description: string; duration: number; voices: IRVoice[] }>;
}

const r4 = (n: number) => Math.round(n * 10000) / 10000;

/** Exponential ramps cannot reach zero; WebAudio uses the same floor. */
const EPS = 1e-4;

/**
 * Sample a keyframe track at u (0..1). Lives here rather than in the renderer
 * because the compiler needs it too — see `sliceEnv`.
 */
export function sampleKeys(keys: [number, number][], ease: IREnvTrack["ease"], u: number): number {
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

/**
 * Re-express a `repeat` voice's envelope over one grain's slice of it.
 *
 * The envelope on a scatter belongs to the whole gesture, not to each grain:
 * a crack is bright grains first and dull grains last, which is a sweep across
 * the scatter, not the same sweep repeated five times. Grains are separate
 * voices in the IR, so the sweep is cut into per-grain windows here — the
 * compiler doing the work instead of the IR growing a bus node and every
 * adapter having to understand it.
 */
function sliceEnv(env: IREnvTrack[], from: number, to: number): IREnvTrack[] {
  return env.map((t) => {
    const keys: [number, number][] = [[0, r4(sampleKeys(t.keys, t.ease, from))]];
    for (const [k, v] of t.keys)
      if (k > from && k < to) keys.push([r4((k - from) / (to - from)), v]);
    keys.push([1, r4(sampleKeys(t.keys, t.ease, to))]);
    return { prop: t.prop, keys, ease: t.ease };
  });
}

function audioTokens(t: Tokens, issues: Issue[], where: string): AudioTokens {
  if (t.audio) return t.audio;
  issues.push({ level: "error", where, msg: "tokens/default.json has no `audio` section" });
  return { pitch: {}, ramps: {}, gain: {}, q: {}, dur: {} };
}

/**
 * `warnRaw` marks the slots that carry identity — a source's pitch, a filter's
 * corner — where a bare number should be a token, exactly as a `fill` should.
 * Keyframe values are trajectories and pass silently.
 */
function hz(ref: string | number, a: AudioTokens, issues: Issue[], where: string, warnRaw = true): number {
  const p = resolvePitch(ref, a);
  if (!p.ok) {
    issues.push({ level: "error", where, msg: p.error + (p.suggestions?.length ? ` — did you mean ${p.suggestions.join(", ")}?` : "") });
    return 440;
  }
  if (p.warn && warnRaw) issues.push({ level: "warn", where, msg: p.warn });
  return p.value;
}

function level(
  ref: string | number | undefined,
  table: Record<string, number>,
  kind: string,
  fallback: number,
  issues: Issue[],
  where: string,
): number {
  if (ref === undefined) return fallback;
  const n = resolveNumber(ref, table, kind);
  if (!n.ok) {
    issues.push({ level: "error", where, msg: n.error + (n.suggestions?.length ? ` — did you mean ${n.suggestions.join(", ")}?` : "") });
    return fallback;
  }
  return n.value;
}

// ---------------------------------------------------------------- variants

/**
 * Apply a variant's structural half (remove / set / add). The scalar half
 * (`pitch`, `stretch`) waits until the IR, where every frequency and every
 * span is a resolved number and one multiply reaches all of them.
 */
export function applySoundVariant(base: Sound, name: string, issues: Issue[]): Sound {
  const v = base.variants?.[name];
  if (!v) {
    issues.push({ level: "error", where: base.id, msg: `unknown variant "${name}"` });
    return base;
  }
  const where = `${base.id}#${name}`;
  let voices: Voice[] = structuredClone(base.voices);

  for (const rid of v.remove ?? []) {
    if (!voices.some((x) => x.id === rid)) issues.push({ level: "error", where, msg: `remove: no voice "${rid}"` });
    voices = voices.filter((x) => x.id !== rid);
  }
  for (const [path, value] of Object.entries(v.set ?? {})) {
    const [vid, ...rest] = path.split(".");
    const voice = voices.find((x) => x.id === vid) as Record<string, unknown> | undefined;
    if (!voice) {
      issues.push({ level: "error", where, msg: `set "${path}": no voice "${vid}"` });
      continue;
    }
    if (rest.length === 0) {
      issues.push({ level: "error", where, msg: `set "${path}": missing property path` });
      continue;
    }
    let target: Record<string, unknown> = voice;
    for (const key of rest.slice(0, -1)) {
      if (typeof target[key] !== "object" || target[key] === null) target[key] = {};
      target = target[key] as Record<string, unknown>;
    }
    target[rest[rest.length - 1]] = structuredClone(value);
    const check = VoiceSchema.safeParse(voice);
    if (!check.success)
      issues.push({ level: "error", where, msg: `set "${path}" made voice "${vid}" invalid: ${check.error.issues[0]?.message}` });
  }
  for (const added of v.add ?? []) {
    if (voices.some((x) => x.id === added.id)) issues.push({ level: "error", where, msg: `add: duplicate voice id "${added.id}"` });
    voices.push(structuredClone(added));
  }
  return { ...base, voices };
}

// ---------------------------------------------------------------- voices

/**
 * What a voice inherits from wherever it is being compiled.
 *
 * The two scalars are the two ways a sound gets bigger, which the document
 * schema already names: a thing drops in pitch, or it takes longer. They are
 * carried *down* the recursion rather than multiplied over the result, because
 * a voice has to know its final Hz and its final seconds before its envelope is
 * expanded — an envelope anchored to a real duration cannot survive being
 * rescaled after the fact, and `adsr` is exactly such an envelope.
 */
interface Frame {
  offset: number; // seconds, already in the outermost document's timeline
  gain: number; // parents' gains, folded
  pitch: number; // frequency scale
  stretch: number; // time scale
  idPrefix: string;
  useStack: string[];
  /** Outermost canvas, seconds — what an echo tap is cut at. */
  canvas: number;
  /** 0 for the document itself; k for its k-th alternate, which reseeds every scatter. */
  take: number;
}

const rootFrame = (canvas: number, pitch = 1, stretch = 1, take = 0, gain = 1): Frame => ({
  offset: 0,
  gain,
  pitch,
  stretch,
  idPrefix: "",
  useStack: [],
  canvas,
  take,
});

/**
 * Every seed in a document, offset per take. The base take is exactly what it
 * was; an alternate moves every seed — authored or derived — by the same
 * stride, so a document that fixed its scatter on purpose still varies between
 * takes without the author having to write N seeds.
 */
const seedFor = (explicit: number | undefined, key: string, take: number): number => (explicit ?? hashSeed(key)) + take * 7919;

function compileSource(
  src: Source,
  ownerId: string,
  voiceId: string,
  a: AudioTokens,
  pitch: number,
  take: number,
  issues: Issue[],
  where: string,
): IRSource {
  if (src.kind === "noise") return { kind: "noise", seed: seedFor(src.seed, `${ownerId}:${voiceId}`, take) };
  return { kind: "osc", wave: src.wave, freq: r4(hz(src.freq, a, issues, where) * pitch) };
}

/**
 * `unison` → the copies it stands for. Spread evenly across ±detune cents,
 * each at 1/√count so the sum sits where the one voice did. A glide moves
 * with each copy — it is the same pitch trajectory, detuned — while the
 * filter stays put: a resonance is a property of the body, not of the string.
 */
function withUnison(v: IRVoice, count: number, detune: number): IRVoice[] {
  const out: IRVoice[] = [];
  for (let i = 0; i < count; i++) {
    const cents = detune * ((2 * i) / (count - 1) - 1);
    const ratio = Math.pow(2, cents / 1200);
    out.push({
      ...v,
      id: `${v.id}.u${i}`,
      gain: r4(v.gain / Math.sqrt(count)),
      source: v.source.kind === "osc" ? { ...v.source, freq: r4(v.source.freq * ratio) } : { ...v.source },
      env: v.env.map((t) => ({ ...t, keys: t.keys.map(([k, val]) => [k, t.prop === "freq" ? r4(val * ratio) : val] as [number, number]) })),
    });
  }
  return out;
}

/**
 * `echo` → the taps it stands for. Whatever the voice compiled to — one
 * voice, a scatter of grains, a composed document, a phrase — again at
 * `time`, `2·time`…, each tap `feedback` times quieter, until a tap would sit
 * under -40dB or the cap. A tap starting past the canvas is dropped and
 * counted; one running past it is cut there without comment, because a tail
 * that ends where the sound ends is not a mistake.
 */
function withEcho(voices: IRVoice[], echo: Echo | undefined, frame: Frame, issues: Issue[], where: string): IRVoice[] {
  if (!echo) return voices;
  const out = [...voices];
  let dropped = 0;
  for (let k = 1; k <= (echo.taps ?? 8); k++) {
    const g = Math.pow(echo.feedback, k);
    if (g < 0.01) break;
    const shift = k * echo.time * frame.stretch;
    for (const v of voices) {
      const at = r4(v.at + shift);
      if (at >= frame.canvas - 1e-6) {
        dropped++;
        continue;
      }
      out.push({
        ...v,
        id: `${v.id}.e${k}`,
        at,
        dur: r4(Math.min(v.dur, frame.canvas - at)),
        gain: r4(v.gain * g),
        env: v.env.map((t) => ({ ...t, keys: t.keys.map((key) => [...key] as [number, number]) })),
      });
    }
  }
  if (dropped)
    issues.push({
      level: "warn",
      where,
      msg: `echo: ${dropped} tap${dropped > 1 ? "s" : ""} would start past the canvas and ${dropped > 1 ? "are" : "is"} dropped — lengthen the duration or shorten the echo`,
    });
  return out;
}

function compileFilter(f: Filter, a: AudioTokens, pitch: number, issues: Issue[], where: string): IRFilter {
  return {
    type: f.type,
    freq: r4(hz(f.freq, a, issues, where) * pitch),
    q: level(f.q, a.q, "q", 1, issues, where),
  };
}

/**
 * Expand the `to` shorthands into the envelope tracks they stand for. Doing it
 * here means the IR has exactly one way to express a slide, so the renderer and
 * every adapter only ever implement that one.
 */
function withGlides(
  voice: { source?: Source; filter?: Filter },
  env: IREnvTrack[],
  a: AudioTokens,
  pitch: number,
  issues: Issue[],
  where: string,
): IREnvTrack[] {
  const out = [...env];
  const add = (prop: "freq" | "cutoff", from: string | number, to: string | number) => {
    if (out.some((t) => t.prop === prop)) {
      issues.push({ level: "error", where, msg: `\`to\` and a "${prop}" env track say the same thing twice` });
      return;
    }
    out.push({
      prop,
      // `from` was already resolved (and warned about) where it was written, so
      // it passes quietly here. `to` is written nowhere else: it is a pitch on
      // the source, next to `freq`, and it carries identity the same way — a
      // theme that retunes the palette has to move where a slide lands too, or
      // half the gesture stays behind. So it warns on a bare number like every
      // other pitch does; only the keyframes it compiles into are trajectories.
      keys: [
        [0, r4(hz(from, a, issues, where, false) * pitch)],
        [1, r4(hz(to, a, issues, where) * pitch)],
      ],
      ease: "exp",
    });
  };
  const src = voice.source;
  if (src && src.kind === "osc" && src.to !== undefined) add("freq", src.freq, src.to);
  if (voice.filter?.to !== undefined) add("cutoff", voice.filter.freq, voice.filter.to);
  return out;
}

/**
 * `adsr` → the keys it stands for, against the voice's final length.
 *
 * This is why the two scales are carried down the recursion rather than
 * multiplied over the result: `dur` here is already the number of seconds the
 * voice will actually last, so a 12ms attack stays 12ms whether the note was
 * written short, stretched by a variant, or refitted by whoever plays it.
 *
 * Segments that do not fit are compressed rather than truncated — a voice too
 * short for its own envelope should sound like a hurried version of itself, not
 * like a shape with its tail cut off — and the compiler says it did so.
 */
function expandAdsr(adsr: Adsr, dur: number, issues: Issue[], where: string): [number, number][] {
  const peak = adsr.peak ?? 1;
  const sustain = adsr.sustain ?? 0;
  let attack = adsr.attack;
  let release = adsr.release ?? 0;
  let decay = adsr.decay ?? Math.max(0, dur - attack - release);

  const total = attack + decay + release;
  if (total > dur + 1e-9) {
    const fit = dur / total;
    attack *= fit;
    decay *= fit;
    release *= fit;
    issues.push({
      level: "warn",
      where,
      msg: `adsr runs ${r4(total)}s in a ${r4(dur)}s voice — compressed to fit`,
    });
  }

  const at = (t: number): number => r4(Math.min(1, t / dur));
  const raw: [number, number][] = [
    [0, 0],
    [at(attack), peak],
    [at(attack + decay), sustain],
    [at(dur - release), sustain],
    [1, 0],
  ];
  // Collapse keys that land on the same instant, last one winning: with no
  // sustain and no release the middle three all sit at the end, and the shape
  // that survives is the plain decay it was asking for.
  const keys: [number, number][] = [];
  for (const k of raw) {
    if (keys.length && keys[keys.length - 1][0] === k[0]) keys.pop();
    keys.push(k);
  }
  return keys;
}

/**
 * Envelope tracks. `gain` keys are plain factors; `freq`/`cutoff` keys resolve
 * as pitches, so a slide is written as the two pitches it moves between.
 * One track per prop, for the same reason the visual side allows one per
 * channel: two tracks fighting over one value is a bug with no useful meaning.
 */
function compileEnv(
  env: EnvTrack[] | undefined,
  a: AudioTokens,
  pitch: number,
  dur: number,
  issues: Issue[],
  where: string,
): IREnvTrack[] {
  const out: IREnvTrack[] = [];
  const seen = new Set<string>();
  for (const track of env ?? []) {
    if (seen.has(track.prop)) {
      issues.push({ level: "error", where, msg: `two "${track.prop}" env tracks on one voice` });
      continue;
    }
    seen.add(track.prop);
    if ("adsr" in track) {
      out.push({ prop: "gain", keys: expandAdsr(track.adsr, dur, issues, where), ease: track.ease ?? "exp" });
      continue;
    }
    const keys = track.keys.map(([t, v]) => {
      if (track.prop === "gain") {
        if (typeof v !== "number") {
          issues.push({ level: "error", where, msg: `gain env keys are numbers 0..1, got "${v}"` });
          return [t, 0] as [number, number];
        }
        if (v < 0 || v > 1) issues.push({ level: "error", where, msg: `gain env key ${v} is outside 0..1` });
        return [r4(t), v] as [number, number];
      }
      return [r4(t), r4(hz(v, a, issues, where, false) * pitch)] as [number, number];
    });
    const sorted = keys.every((k, i) => i === 0 || k[0] >= keys[i - 1][0]);
    if (!sorted) issues.push({ level: "error", where, msg: `${track.prop} env keys are out of time order` });
    out.push({ prop: track.prop, keys, ease: track.ease ?? "exp" });
  }
  return out;
}

function compileVoices(
  voices: Voice[],
  owner: { id: string; duration: number },
  reg: SoundRegistry,
  issues: Issue[],
  whereBase: string,
  frame: Frame,
): IRVoice[] {
  const a = audioTokens(reg.tokens, issues, whereBase);
  const out: IRVoice[] = [];

  for (const voice of voices) {
    const where = `${whereBase}(${voice.id})`;
    const at = r4(frame.offset + (voice.at ?? 0) * frame.stretch);
    const gain = frame.gain * level(voice.gain, a.gain, "gain", 1, issues, where);
    const own = level("dur" in voice ? voice.dur : undefined, a.dur, "dur", owner.duration - (voice.at ?? 0), issues, where);
    const id = frame.idPrefix + voice.id;

    if ("use" in voice) {
      const target = reg.sounds.get(voice.use);
      if (!target) {
        issues.push({ level: "error", where, msg: `use: unknown sound "${voice.use}"` });
        continue;
      }
      if (frame.useStack.includes(voice.use) || frame.useStack.length >= 4) {
        issues.push({ level: "error", where, msg: `use: cycle or depth > 4 via "${voice.use}"` });
        continue;
      }
      const resolved = voice.variant ? applySoundVariant(target, voice.variant, issues) : target;
      const vdef = voice.variant ? target.variants?.[voice.variant] : undefined;
      // Playing an instrument: the ratio between the pitch asked for and the
      // one the document says it was written at. It multiplies into the frame
      // like any other scale, so every voice inside transposes together and a
      // noise voice is left alone — which is what makes a two-voice instrument
      // stay itself at a different pitch.
      let play = 1;
      if (voice.pitch !== undefined) {
        if (target.root === undefined)
          issues.push({
            level: "error",
            where,
            msg: `use: "${voice.use}" has no \`root\`, so there is no pitch to play it at — give it one`,
          });
        else play = hz(voice.pitch, a, issues, where) / hz(target.root, a, issues, voice.use);
      }
      // A composed document keeps its own timeline; `dur` on the use voice fits
      // it to a different one, which is what `scale` does for a composed asset.
      const fit = voice.dur === undefined ? 1 : own / target.duration;
      const composed = compileVoices(resolved.voices, { id: target.id, duration: target.duration }, reg, issues, voice.use, {
        offset: at,
        gain: gain * level(target.gain, a.gain, "gain", 1, issues, voice.use),
        pitch: frame.pitch * (vdef?.pitch ?? 1) * play,
        stretch: frame.stretch * (vdef?.stretch ?? 1) * fit,
        idPrefix: `${id}.`,
        useStack: [...frame.useStack, voice.use],
        canvas: frame.canvas,
        take: frame.take,
      });
      out.push(...withEcho(composed, voice.echo, frame, issues, where));
      continue;
    }

    if ("phrase" in voice) {
      // Each note is the `use` voice the author would have written, compiled
      // through the same branch, so a phrase can do nothing a row of `use`
      // voices could not — it only stops the author writing the row.
      const { use, variant, step, dur, notes } = voice.phrase;
      const figure: IRVoice[] = [];
      notes.forEach((note, i) => {
        if (note === null) return;
        const n: UseVoice = {
          id: `${voice.id}.n${i}`,
          at: (voice.at ?? 0) + i * step,
          use,
          pitch: note,
          ...(variant !== undefined ? { variant } : {}),
          ...(dur !== undefined ? { dur } : {}),
          ...(voice.gain !== undefined ? { gain: voice.gain } : {}),
        };
        figure.push(...compileVoices([n], owner, reg, issues, whereBase, frame));
      });
      out.push(...withEcho(figure, voice.echo, frame, issues, where));
      continue;
    }

    if ("repeat" in voice) {
      const { of, count, spread, grain, seed, pitchRange, gainRange } = voice.repeat;
      const rng = mulberry32(seedFor(seed, `${owner.id}:${voice.id}`, frame.take));
      const glen = level(grain, a.dur, "dur", 0.02, issues, where);
      // The scatter's own span, which the envelope describes. Kept in the
      // document's units so the per-grain windows below stay ratios, and a
      // stretched gesture slices exactly where an unstretched one does — but an
      // `adsr` on it is expanded against the seconds the gesture really lasts,
      // because that is the point of writing one.
      const gesture = spread + glen;
      const filter = voice.filter && compileFilter(voice.filter, a, frame.pitch, issues, where);
      const env = withGlides(
        { source: of, filter: voice.filter },
        compileEnv(voice.env, a, frame.pitch, gesture * frame.stretch, issues, where),
        a,
        frame.pitch,
        issues,
        where,
      );
      const grains: IRVoice[] = [];
      for (let i = 0; i < count; i++) {
        const src = compileSource(of, owner.id, `${voice.id}_${i}`, a, frame.pitch, frame.take, issues, where);
        const t = rng() * spread;
        const pitchMul = pitchRange ? pitchRange[0] + rng() * (pitchRange[1] - pitchRange[0]) : 1;
        const gainMulI = gainRange ? gainRange[0] + rng() * (gainRange[1] - gainRange[0]) : 1;
        if (src.kind === "osc" && pitchMul !== 1) src.freq = r4(src.freq * pitchMul);
        grains.push({
          id: `${id}.g${i}`,
          at: r4(at + t * frame.stretch),
          dur: r4(glen * frame.stretch),
          gain: r4(gain * gainMulI),
          source: src,
          ...(filter ? { filter: { ...filter } } : {}),
          env: sliceEnv(env, t / gesture, (t + glen) / gesture),
        });
      }
      out.push(...withEcho(grains, voice.echo, frame, issues, where));
      continue;
    }

    const one: IRVoice = {
      id,
      at,
      dur: r4(own * frame.stretch),
      gain: r4(gain),
      source: compileSource(voice.source, owner.id, voice.id, a, frame.pitch, frame.take, issues, where),
      ...(voice.filter ? { filter: compileFilter(voice.filter, a, frame.pitch, issues, where) } : {}),
      env: withGlides(
        voice,
        compileEnv(voice.env, a, frame.pitch, own * frame.stretch, issues, where),
        a,
        frame.pitch,
        issues,
        where,
      ),
    };
    const uni = voice.source.kind === "osc" ? voice.source.unison : undefined;
    out.push(...withEcho(uni ? withUnison(one, uni.count, uni.detune) : [one], voice.echo, frame, issues, where));
  }
  return out;
}

export function compileSound(sound: Sound, reg: SoundRegistry): { ir: IRSound; issues: Issue[] } {
  const issues: Issue[] = [];
  const a = audioTokens(reg.tokens, issues, sound.id);
  const owner = { id: sound.id, duration: sound.duration };
  const gain = level(sound.gain, a.gain, "gain", 1, issues, sound.id);
  const voices = compileVoices(sound.voices, owner, reg, issues, sound.id, rootFrame(sound.duration));

  for (const v of voices)
    if (v.at + v.dur > sound.duration + 1e-6)
      issues.push({
        level: "warn",
        where: sound.id,
        msg: `voice "${v.id}" runs to ${r4(v.at + v.dur)}s, past duration ${sound.duration}s — it will be cut short`,
      });

  const variants: IRSound["variants"] = {};
  for (const [vname, v] of Object.entries(sound.variants ?? {})) {
    const applied = applySoundVariant(sound, vname, issues);
    const stretch = v.stretch ?? 1;
    variants[vname] = {
      description: v.description,
      duration: r4(sound.duration * stretch),
      voices: compileVoices(
        applied.voices,
        owner,
        reg,
        issues,
        `${sound.id}#${vname}`,
        rootFrame(r4(sound.duration * stretch), v.pitch ?? 1, stretch),
      ),
    };
  }

  // Alternates. The document again, every seed moved and its jitter rolled
  // once by a seeded rng and frozen — the engine's per-trigger roll, done at
  // compile time so it can be baked, listened to and held as a baseline.
  const shape = (vs: IRVoice[]) => JSON.stringify(vs.map(({ id: _id, ...rest }) => (void _id, rest)));
  for (let k = 2; k <= (sound.takes ?? 1); k++) {
    const name = `take-${k}`;
    if (variants[name]) {
      issues.push({ level: "error", where: sound.id, msg: `variant "${name}" collides with take ${k} — takes are named take-2…` });
      continue;
    }
    const rng = mulberry32(hashSeed(`${sound.id}:${name}`));
    const roll = (range?: [number, number]) => (range ? r4(range[0] + rng() * (range[1] - range[0])) : 1);
    const pitch = roll(sound.jitter?.freq);
    const level = roll(sound.jitter?.gain);
    const alt = compileVoices(sound.voices, owner, reg, issues, `${sound.id}#${name}`, rootFrame(sound.duration, pitch, 1, k - 1, level));
    if (shape(alt) === shape(voices))
      issues.push({ level: "warn", where: `${sound.id}#${name}`, msg: "identical to the base take — nothing here is seeded or jittered, so takes have nothing to vary" });
    variants[name] = {
      description: `Take ${k} of ${sound.takes}: the same document with every scatter reseeded and its jitter rolled once and frozen.`,
      duration: sound.duration,
      voices: alt,
    };
  }

  const ir: IRSound = {
    format: "polygraphics-sound-ir",
    version: 1,
    id: sound.id,
    name: sound.name,
    description: sound.description,
    tags: sound.tags,
    duration: sound.duration,
    gain: r4(gain),
    ...(sound.jitter ? { jitter: sound.jitter } : {}),
    meta: { ...sound.meta },
    voices,
    variants,
  };
  return { ir, issues };
}
