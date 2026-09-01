/**
 * The sound document schema — the asset document with time where space was.
 *
 * A sound is pure data: named voices made of source primitives, leveled with
 * token references, plus declarative variants and envelopes. The renderer
 * interprets it; nothing here is imperative. The parallel to `schema.ts` is
 * deliberate and load-bearing — whoever can author an asset can author a sound:
 *
 *   parts → voices      (array order = mix order)
 *   shape → source      (osc / noise: the primitive that makes a waveform)
 *   fill  → gain        (a token reference, never a bare level, for identity)
 *   at [x,y] → at t     (a voice places itself in the sound's timeline)
 *   repeat (scatter in space) → repeat (scatter in time — grains)
 *   use (compose a document) → use (compose a document)
 *   animations → env    (keyframe tracks; the same [t, value] pairs)
 *
 * Coordinate system: origin at t=0, +t forward, units seconds.
 */
import { z } from "zod";

const voiceId = z.string().regex(/^[a-z][a-z0-9_]*$/, "voice ids are snake_case");
const soundId = z
  .string()
  .regex(/^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$/, 'sound ids are dotted, e.g. "sfx.hit"');

/** Hz, or a pitch token reference ("$tap", "$tap.down2"). */
export const PitchSchema = z.union([z.number().positive(), z.string()]);
/** A number, or the name of a token in the matching table. */
export const LevelSchema = z.union([z.number(), z.string()]);

export const SourceSchema = z.discriminatedUnion("kind", [
  // A bare oscillator. Band-limited (PolyBLEP offline, PeriodicWave in the
  // browser), so a square at 200Hz is a square, not a stairstep of aliases.
  //
  // `to` is a glide target: shorthand for the two-key `freq` envelope that
  // almost every short sound wants, and nothing more — it compiles to exactly
  // that track, so adapters never learn it exists. Same relationship `ngon` has
  // to `poly` on the visual side.
  z.strictObject({
    kind: z.literal("osc"),
    wave: z.enum(["sine", "square", "sawtooth", "triangle"]),
    freq: PitchSchema,
    to: PitchSchema.optional(),
  }),
  // Broadband noise — air, smoke, anything that isn't a pitch. Seeded, because
  // a sound that renders differently every time cannot be regression-tested.
  z.strictObject({
    kind: z.literal("noise"),
    seed: z.number().int().optional(), // falls back to hash(soundId:voiceId)
  }),
]);
export type Source = z.infer<typeof SourceSchema>;

/**
 * One biquad on this voice. `freq` is the corner/center; an `env` track named
 * `cutoff` sweeps it. Q takes a number or a token name, exactly as a stroke
 * width does.
 */
export const FilterSchema = z.strictObject({
  type: z.enum(["lowpass", "highpass", "bandpass"]),
  freq: PitchSchema,
  to: PitchSchema.optional(), // sweep target; shorthand for a `cutoff` track
  q: LevelSchema.optional(),
});
export type Filter = z.infer<typeof FilterSchema>;

/**
 * A keyframe track, structurally identical to an animation track: [t 0..1,
 * value] pairs over the voice's own span.
 *
 * `gain` values are factors 0..1 of the voice's level (opacity's twin);
 * `freq` and `cutoff` values are Hz or pitch refs, so a slide reads as the two
 * pitches it actually moves between rather than as a ratio. A raw number is
 * fine here and does not warn — a keyframe is a trajectory, the same way an
 * animation track's `y` is plain px while a `fill` must be a token.
 *
 * Default ease is `exp`, not `sine`: pitch and loudness are perceived
 * logarithmically, so an exponential ramp is the one that sounds linear.
 */
export const EnvTrackSchema = z.strictObject({
  prop: z.enum(["gain", "freq", "cutoff"]),
  // The value is a plain number or a pitch ref; which one is legal depends on
  // `prop`, so the compiler checks it and says so in the prop's own words
  // rather than the schema rejecting a perfectly good `[1, 0]` gain key.
  keys: z.array(z.tuple([z.number().min(0).max(1), z.union([z.number(), z.string()])])).min(2),
  ease: z.enum(["linear", "exp", "sine"]).optional(),
});
export type EnvTrack = z.infer<typeof EnvTrackSchema>;

/** What every voice does, whatever it is made of: place itself, and set its level. */
const voiceBase = {
  id: voiceId,
  at: z.number().min(0).optional(), // start, seconds from t=0; default 0
  dur: LevelSchema.optional(), // seconds or a dur token; default = the rest of the sound
  gain: LevelSchema.optional(), // 0..1 or a gain token name; default 1
};

/**
 * Shaping belongs to a voice that owns a waveform. A `use` voice does not: the
 * document it composes brings its own envelopes, and a track written here would
 * have to be sliced across every voice inside it — which is a bus, and the IR
 * has none. Leaving these off `use` makes that a schema error at the point of
 * writing rather than a track the compiler drops without a word.
 */
const shaping = {
  env: z.array(EnvTrackSchema).optional(),
  filter: FilterSchema.optional(),
};

export const SourceVoiceSchema = z.strictObject({ ...voiceBase, ...shaping, source: SourceSchema });

/**
 * Compose another sound document in place, offset by this voice's `at` and
 * scaled by its `gain`. The whole point of `ss.lib.*`: one document holds what
 * the hive's chitin sounds like, and every creature sound composes it.
 */
export const UseVoiceSchema = z.strictObject({
  ...voiceBase,
  use: soundId,
  variant: z.string().optional(),
});

/**
 * Deterministic scatter in time: `count` short grains of `of`, jittered across
 * `spread` seconds, seeded — the exact twin of a `repeat` part, which scatters
 * shapes across an area. This is what a dry crack is: a handful of grains that
 * arrive and stop, not a tone with an envelope on it.
 */
export const RepeatVoiceSchema = z.strictObject({
  ...voiceBase,
  ...shaping,
  repeat: z.strictObject({
    of: SourceSchema,
    count: z.number().int().min(1).max(256),
    spread: z.number().positive(), // seconds the grains land within
    grain: LevelSchema, // each grain's length: seconds or a dur token
    seed: z.number().int().optional(),
    pitchRange: z.tuple([z.number().positive(), z.number().positive()]).optional(), // multipliers
    gainRange: z.tuple([z.number().positive(), z.number().positive()]).optional(),
  }),
});

export const VoiceSchema = z.union([SourceVoiceSchema, UseVoiceSchema, RepeatVoiceSchema]);
export type Voice = z.infer<typeof VoiceSchema>;
export type SourceVoice = z.infer<typeof SourceVoiceSchema>;
export type UseVoice = z.infer<typeof UseVoiceSchema>;
export type RepeatVoice = z.infer<typeof RepeatVoiceSchema>;

/**
 * A variant is a declarative patch, same grammar as a visual variant. Where a
 * visual variant has one `scale`, a sound has two — a thing can get bigger by
 * dropping in pitch or by taking longer, and they are not the same edit.
 */
export const SoundVariantSchema = z.strictObject({
  description: z.string(),
  pitch: z.number().positive().optional(), // multiplies every freq and cutoff
  stretch: z.number().positive().optional(), // multiplies every duration and start
  set: z.record(z.string(), z.unknown()).optional(), // "<voiceId>.<path>": value
  add: z.array(VoiceSchema).optional(),
  remove: z.array(voiceId).optional(),
});
export type SoundVariant = z.infer<typeof SoundVariantSchema>;

/**
 * Per-play variation. Deliberately *not* the seeded scatter above: `repeat` is
 * frozen at compile time so the bake is byte-identical forever, while this is
 * rolled by the engine on every trigger, because two hits in a row landing on
 * exactly the same pitch is the sound of a machine. The offline render uses the
 * nominal values, which is what keeps regression meaningful.
 */
export const JitterSchema = z.strictObject({
  freq: z.tuple([z.number().positive(), z.number().positive()]).optional(),
  gain: z.tuple([z.number().positive(), z.number().positive()]).optional(),
});

export const SoundSchema = z.strictObject({
  id: soundId,
  name: z.string().min(1),
  description: z.string().min(8), // required: legibility is the whole premise
  tags: z.array(z.string()).min(1), // tags[0] = gallery category
  duration: z.number().positive(), // seconds — the canvas
  gain: LevelSchema.optional(), // master for this document; default 1
  jitter: JitterSchema.optional(),
  meta: z.record(z.string(), z.number()).optional(), // sim-facing hints (minInterval, …)
  /**
   * Why this document sits outside the set's level band, if it does.
   *
   * The loudness lint compares every triggered sound against the set median
   * and complains past 9dB, which is right almost always and wrong for a cue
   * whose whole job is to be under the cues it shares a frame with. Writing
   * the reason down turns the exception into a decision somebody made, rather
   * than a warning everybody learns to scroll past.
   */
  offBand: z.string().min(8).optional(),
  voices: z.array(VoiceSchema).min(1),
  variants: z.record(z.string(), SoundVariantSchema).optional(),
});
export type Sound = z.infer<typeof SoundSchema>;
