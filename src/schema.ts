/**
 * The asset document schema. An asset is pure data: named parts made of shape
 * primitives, painted with token references, plus declarative variants and
 * animations. The renderer interprets it; nothing here is imperative.
 *
 * Coordinate system: origin at the asset's anchor, +x right, +y down, units px.
 * Part order = draw order (later parts draw on top).
 */
import { z } from "zod";

export const Vec2 = z.tuple([z.number(), z.number()]);

const partId = z.string().regex(/^[a-z][a-z0-9_]*$/, "part ids are snake_case");
const assetId = z
  .string()
  .regex(/^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$/, 'asset ids are dotted and app-first, e.g. "demo.enemy.imp"');

export const ShapeSchema = z.discriminatedUnion("kind", [
  z.strictObject({ kind: z.literal("circle"), r: z.number().positive() }),
  z.strictObject({ kind: z.literal("ellipse"), rx: z.number().positive(), ry: z.number().positive() }),
  // rect is centered on its position; corner = corner radius
  z.strictObject({ kind: z.literal("rect"), w: z.number().positive(), h: z.number().positive(), corner: z.number().min(0).optional() }),
  // regular n-gon, first vertex points up (rot in degrees rotates it)
  z.strictObject({ kind: z.literal("ngon"), sides: z.number().int().min(3).max(24), r: z.number().positive(), rot: z.number().optional() }),
  z.strictObject({ kind: z.literal("star"), points: z.number().int().min(3).max(24), r: z.number().positive(), r2: z.number().positive(), rot: z.number().optional() }),
  // arbitrary polygon — concave and asymmetric silhouettes welcome
  z.strictObject({ kind: z.literal("poly"), points: z.array(Vec2).min(3) }),
  // ring/arc: painted with the part's `fill` as its stroke color; from/to in degrees (0 = +x, clockwise)
  z.strictObject({ kind: z.literal("ring"), r: z.number().positive(), width: z.number().positive(), from: z.number().optional(), to: z.number().optional() }),
  // pie slice from center; from/to in degrees
  z.strictObject({ kind: z.literal("wedge"), r: z.number().positive(), from: z.number(), to: z.number() }),
]);
export type Shape = z.infer<typeof ShapeSchema>;

export const GradientSchema = z.strictObject({
  gradient: z.enum(["linear", "radial"]),
  // in shape bounding-box coords, 0..1; linear defaults to top→bottom
  from: Vec2.optional(),
  to: Vec2.optional(),
  stops: z.array(z.tuple([z.number().min(0).max(1), z.string()])).min(2),
});
export type Gradient = z.infer<typeof GradientSchema>;

export const PaintSchema = z.union([z.string(), GradientSchema]);
export type Paint = z.infer<typeof PaintSchema>;

const StrokeSchema = z.strictObject({
  color: z.string(),
  width: z.union([z.number().positive(), z.string()]), // number or stroke token name ("thin")
});

const partBase = {
  id: partId,
  at: Vec2.optional(), // position of the part's local origin, default [0,0]
  rot: z.number().optional(), // degrees
  scale: z.union([z.number().positive(), Vec2]).optional(),
  mirrorX: z.boolean().optional(), // also draw a copy mirrored across the anchor's vertical axis
  opacity: z.union([z.number().min(0).max(1), z.string()]).optional(), // number or alpha token name
};

export const ShapePartSchema = z.strictObject({
  ...partBase,
  shape: ShapeSchema,
  fill: PaintSchema.optional(),
  stroke: StrokeSchema.optional(),
});

// Compose another asset by id (shared parts, single-source icons). Renders that
// asset's parts in this part's local frame. `variant` picks one of the used
// asset's variants, so one library document can appear in several states.
export const UsePartSchema = z.strictObject({
  ...partBase,
  use: assetId,
  variant: z.string().optional(),
});

// Deterministic scatter: `count` copies of a shape uniformly jittered inside
// `area` (centered on the part), seeded — same seed, same scatter, forever.
export const RepeatPartSchema = z.strictObject({
  ...partBase,
  repeat: z.strictObject({
    of: ShapeSchema,
    count: z.number().int().min(1).max(256),
    area: Vec2,
    seed: z.number().int().optional(), // falls back to hash(assetId:partId)
    jitterRot: z.boolean().optional(),
    scaleRange: z.tuple([z.number().positive(), z.number().positive()]).optional(),
  }),
  fill: PaintSchema.optional(),
  stroke: StrokeSchema.optional(),
});

export const PartSchema = z.union([ShapePartSchema, UsePartSchema, RepeatPartSchema]);
export type Part = z.infer<typeof PartSchema>;
export type ShapePart = z.infer<typeof ShapePartSchema>;
export type UsePart = z.infer<typeof UsePartSchema>;
export type RepeatPart = z.infer<typeof RepeatPartSchema>;

/**
 * How a segment between two keys is shaped (see src/anim.ts). `hold` is a step:
 * the value waits at its key until the next one, then arrives all at once —
 * the held pose a stepped clip (an anticipation, a smear) is drawn from.
 */
export const EaseSchema = z.enum(["linear", "sine", "backOut", "hold", "quadIn", "quadOut", "expoOut"]);

const cueName = z.string().regex(/^[a-z][a-z0-9_]*$/, "cue names are snake_case");

export const AnimSchema = z.strictObject({
  description: z.string().optional(),
  duration: z.number().positive(), // seconds; loops
  tracks: z
    .array(
      z.strictObject({
        part: partId,
        // scaleX/scaleY squash and stretch a part about its own origin; `tint` is
        // how far (0..1) the part is covered by `to`, its silhouette in that colour
        prop: z.enum(["x", "y", "rot", "scale", "scaleX", "scaleY", "opacity", "tint"]),
        // keyframes: [t 0..1, value, ease?]; px for x/y, degrees for rot, factor for
        // scale, 0..1 for opacity and tint. A key's ease shapes the segment leaving it.
        keys: z
          .array(z.union([z.tuple([z.number().min(0).max(1), z.number()]), z.tuple([z.number().min(0).max(1), z.number(), EaseSchema])]))
          .min(2),
        ease: EaseSchema.optional(), // default sine
        to: z.string().optional(), // colour token, for `tint` only
      }),
    )
    .min(1),
  /**
   * Named moments in the clip, as 0..1 of its length: `release` is when the
   * weapon leaves the body, `contact` when a foot lands. A consumer times what
   * the clip is for — the projectile, the dust — off these rather than off a
   * number it keeps itself, which is how `meta.layCue` drifted from the lay.
   */
  cues: z.record(cueName, z.number().min(0).max(1)).optional(),
});
export type Anim = z.infer<typeof AnimSchema>;

// A variant is a declarative patch: scale, per-part property overrides
// ("<partId>.<path>": value), added parts, removed parts.
export const VariantSchema = z.strictObject({
  description: z.string(),
  scale: z.number().positive().optional(),
  set: z.record(z.string(), z.unknown()).optional(),
  add: z.array(PartSchema).optional(),
  remove: z.array(partId).optional(),
  /**
   * The clips this state is drawn to be played with, in the order they happen.
   * `[]` means it is a still — a state that plays nothing.
   *
   * A state and a clip are separate axes and most pairings between them are
   * nonsense, but which pairings are not was only ever written down in the
   * consuming game. So the gallery guessed, and guessed wrong in both
   * directions: it played a Lance's fill on the whole bow-and-barb, a pose
   * nothing bakes, and drew the spent bow still when its entire purpose is to
   * unwind. Omit it and the gallery goes back to guessing, which is right for
   * a variant that is a recolour; state it and the document says what it means.
   *
   * Names are checked against this document's own animations.
   */
  animations: z.array(z.string()).optional(),
});
export type Variant = z.infer<typeof VariantSchema>;

/**
 * The internal skeleton a body was drawn on: named joints in the asset's own
 * coordinates, and the bones between them. Not drawn in a bake — it is the
 * scaffold the parts were placed from (a part hangs from a joint plus a length
 * and an angle), kept in the document so a change can be asked for by joint
 * name ("shoulder_near a pixel lower") and the gallery can show it over the
 * drawing. See docs/character-rig-guide.md.
 */
const jointName = z.string().regex(/^[a-z][a-z0-9_]*$/, "joint names are snake_case");
export const SkeletonSchema = z.strictObject({
  joints: z.record(jointName, Vec2),
  bones: z.array(z.tuple([jointName, jointName])).optional(),
  /**
   * The points a consumer attaches things to — where a projectile leaves the
   * body, where a spark sits. Unlike the rest of the skeleton these do reach
   * the bake: each names a joint for where it is at rest and, optionally, the
   * part it rides, so that when a clip swings that part the socket swings with
   * it (`socketAt` in the adapter). Names are the game's to read, so they say
   * what the point is for (`mouth`, `feeler_tip`), not where it is.
   */
  sockets: z.record(jointName, z.strictObject({ joint: jointName, part: partId.optional() })).optional(),
});
export type Skeleton = z.infer<typeof SkeletonSchema>;

export const AssetSchema = z.strictObject({
  id: assetId,
  name: z.string().min(1),
  description: z.string().min(8), // required: this is what makes the asset legible
  tags: z.array(z.string()).min(1),
  size: Vec2, // canvas [w, h] in px
  anchor: Vec2.optional(), // normalized, default [0.5, 0.5]
  seed: z.number().int().optional(),
  meta: z.record(z.string(), z.number()).optional(), // sim-facing hints (radius, …)
  parts: z.array(PartSchema).min(1),
  variants: z.record(z.string(), VariantSchema).optional(),
  animations: z.record(z.string(), AnimSchema).optional(),
  /**
   * Why this document steps outside one of its app's rules, keyed by the
   * rule's name (`size`, `grid`, `distinct`, …). A rule a document names here
   * is not applied to it, and the gallery lists the exception with its reason.
   * The exception then reads as a decision somebody made rather than a warning
   * everybody learns to scroll past — `offBand` on a sound, generalised.
   */
  why: z.record(z.string(), z.string().min(1)).optional(),
  skeleton: SkeletonSchema.optional(),
});
export type Asset = z.infer<typeof AssetSchema>;
