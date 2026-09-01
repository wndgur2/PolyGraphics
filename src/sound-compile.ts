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
 *   implicit spans   → concrete `at` / `dur` seconds
 *
 * Unlike the visual side, the offline renderer consumes this IR too rather than
 * re-walking the document. Whatever you hear in the bake is what an engine
 * plays, by construction.
 */
import type { EnvTrack, Filter, Sound, Source, Voice } from "./sound-schema.js";
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

function compileSource(
  src: Source,
  ownerId: string,
  voiceId: string,
  a: AudioTokens,
  issues: Issue[],
  where: string,
): IRSource {
  if (src.kind === "noise") return { kind: "noise", seed: src.seed ?? hashSeed(`${ownerId}:${voiceId}`) };
  return { kind: "osc", wave: src.wave, freq: hz(src.freq, a, issues, where) };
}

function compileFilter(f: Filter, a: AudioTokens, issues: Issue[], where: string): IRFilter {
  return { type: f.type, freq: hz(f.freq, a, issues, where), q: level(f.q, a.q, "q", 1, issues, where) };
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
      keys: [[0, hz(from, a, issues, where, false)], [1, hz(to, a, issues, where)]],
      ease: "exp",
    });
  };
  const src = voice.source;
  if (src && src.kind === "osc" && src.to !== undefined) add("freq", src.freq, src.to);
  if (voice.filter?.to !== undefined) add("cutoff", voice.filter.freq, voice.filter.to);
  return out;
}

/**
 * Envelope tracks. `gain` keys are plain factors; `freq`/`cutoff` keys resolve
 * as pitches, so a slide is written as the two pitches it moves between.
 * One track per prop, for the same reason the visual side allows one per
 * channel: two tracks fighting over one value is a bug with no useful meaning.
 */
function compileEnv(env: EnvTrack[] | undefined, a: AudioTokens, issues: Issue[], where: string): IREnvTrack[] {
  const out: IREnvTrack[] = [];
  const seen = new Set<string>();
  for (const track of env ?? []) {
    if (seen.has(track.prop)) {
      issues.push({ level: "error", where, msg: `two "${track.prop}" env tracks on one voice` });
      continue;
    }
    seen.add(track.prop);
    const keys = track.keys.map(([t, v]) => {
      if (track.prop === "gain") {
        if (typeof v !== "number") {
          issues.push({ level: "error", where, msg: `gain env keys are numbers 0..1, got "${v}"` });
          return [t, 0] as [number, number];
        }
        if (v < 0 || v > 1) issues.push({ level: "error", where, msg: `gain env key ${v} is outside 0..1` });
        return [r4(t), v] as [number, number];
      }
      return [r4(t), hz(v, a, issues, where, false)] as [number, number];
    });
    const sorted = keys.every((k, i) => i === 0 || k[0] >= keys[i - 1][0]);
    if (!sorted) issues.push({ level: "error", where, msg: `${track.prop} env keys are out of time order` });
    out.push({ prop: track.prop, keys, ease: track.ease ?? "exp" });
  }
  return out;
}

/** `pitch` / `stretch`: the two ways a sound gets bigger, applied to resolved IR. */
function scaleVoices(voices: IRVoice[], pitch: number, stretch: number): IRVoice[] {
  if (pitch === 1 && stretch === 1) return voices;
  return voices.map((v) => ({
    ...v,
    at: r4(v.at * stretch),
    dur: r4(v.dur * stretch),
    source: v.source.kind === "osc" ? { ...v.source, freq: r4(v.source.freq * pitch) } : { ...v.source },
    ...(v.filter ? { filter: { ...v.filter, freq: r4(v.filter.freq * pitch) } } : {}),
    env: v.env.map((t) => ({
      ...t,
      keys: t.keys.map(([k, val]) => [k, t.prop === "gain" ? val : r4(val * pitch)] as [number, number]),
    })),
  }));
}

function compileVoices(
  voices: Voice[],
  owner: { id: string; duration: number },
  reg: SoundRegistry,
  issues: Issue[],
  whereBase: string,
  useStack: string[],
  offset: number,
  gainMul: number,
  idPrefix: string,
): IRVoice[] {
  const a = audioTokens(reg.tokens, issues, whereBase);
  const out: IRVoice[] = [];

  for (const voice of voices) {
    const where = `${whereBase}(${voice.id})`;
    const at = r4(offset + (voice.at ?? 0));
    const gain = gainMul * level(voice.gain, a.gain, "gain", 1, issues, where);
    const span = level(voice.dur, a.dur, "dur", owner.duration - (voice.at ?? 0), issues, where);
    const id = idPrefix + voice.id;

    if ("use" in voice) {
      const target = reg.sounds.get(voice.use);
      if (!target) {
        issues.push({ level: "error", where, msg: `use: unknown sound "${voice.use}"` });
        continue;
      }
      if (useStack.includes(voice.use) || useStack.length >= 4) {
        issues.push({ level: "error", where, msg: `use: cycle or depth > 4 via "${voice.use}"` });
        continue;
      }
      const resolved = voice.variant ? applySoundVariant(target, voice.variant, issues) : target;
      // A composed document keeps its own timeline; `dur` on the use voice fits
      // it to a different one, which is what `scale` does for a composed asset.
      const fit = voice.dur === undefined ? 1 : level(voice.dur, a.dur, "dur", target.duration, issues, where) / target.duration;
      const vdef = voice.variant ? target.variants?.[voice.variant] : undefined;
      // Compile at the origin so the variant's scalars land before the offset does.
      const child = scaleVoices(
        compileVoices(
          resolved.voices,
          { id: target.id, duration: target.duration },
          reg,
          issues,
          voice.use,
          [...useStack, voice.use],
          0,
          gain * level(target.gain, a.gain, "gain", 1, issues, voice.use),
          `${id}.`,
        ),
        vdef?.pitch ?? 1,
        (vdef?.stretch ?? 1) * fit,
      );
      for (const c of child) c.at = r4(c.at + at);
      out.push(...child);
      continue;
    }

    if ("repeat" in voice) {
      const { of, count, spread, grain, seed, pitchRange, gainRange } = voice.repeat;
      const rng = mulberry32(seed ?? hashSeed(`${owner.id}:${voice.id}`));
      const glen = level(grain, a.dur, "dur", 0.02, issues, where);
      const filter = voice.filter && compileFilter(voice.filter, a, issues, where);
      const env = withGlides({ source: of, filter: voice.filter }, compileEnv(voice.env, a, issues, where), a, issues, where);
      const gesture = spread + glen; // the whole scatter's span, which the envelope describes
      for (let i = 0; i < count; i++) {
        const src = compileSource(of, owner.id, `${voice.id}_${i}`, a, issues, where);
        const t = rng() * spread;
        const pitchMul = pitchRange ? pitchRange[0] + rng() * (pitchRange[1] - pitchRange[0]) : 1;
        const gainMulI = gainRange ? gainRange[0] + rng() * (gainRange[1] - gainRange[0]) : 1;
        if (src.kind === "osc" && pitchMul !== 1) src.freq = r4(src.freq * pitchMul);
        out.push({
          id: `${id}.g${i}`,
          at: r4(at + t),
          dur: r4(glen),
          gain: r4(gain * gainMulI),
          source: src,
          ...(filter ? { filter: { ...filter } } : {}),
          env: sliceEnv(env, t / gesture, (t + glen) / gesture),
        });
      }
      continue;
    }

    out.push({
      id,
      at,
      dur: r4(span),
      gain: r4(gain),
      source: compileSource(voice.source, owner.id, voice.id, a, issues, where),
      ...(voice.filter ? { filter: compileFilter(voice.filter, a, issues, where) } : {}),
      env: withGlides(voice, compileEnv(voice.env, a, issues, where), a, issues, where),
    });
  }
  return out;
}

export function compileSound(sound: Sound, reg: SoundRegistry): { ir: IRSound; issues: Issue[] } {
  const issues: Issue[] = [];
  const a = audioTokens(reg.tokens, issues, sound.id);
  const owner = { id: sound.id, duration: sound.duration };
  const gain = level(sound.gain, a.gain, "gain", 1, issues, sound.id);
  const voices = compileVoices(sound.voices, owner, reg, issues, sound.id, [], 0, 1, "");

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
      voices: scaleVoices(
        compileVoices(applied.voices, owner, reg, issues, `${sound.id}#${vname}`, [], 0, 1, ""),
        v.pitch ?? 1,
        stretch,
      ),
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
