/**
 * PolyGraphics → Phaser adapter. Drop this single file into a Phaser 3/4 project.
 *
 * Consumes compiled IR (out/compiled/*.json). Two integration modes:
 *
 *   bakeFlat(scene, ir, {variant})  → one generated texture key.
 *     Zero pipeline change: use the key like any sprite texture. For hot-path
 *     objects (projectiles, pickups, enemies-by-the-hundred). No per-part anim.
 *
 *   buildRig(scene, ir, {variant})  → Container of per-part Images + a data-driven
 *     animation player. For characters/bosses where parts move. Call rig.tick(dt)
 *     from your update loop; rig.play("idle").
 *
 * The adapter uses structural typing (no Phaser import) so it compiles anywhere;
 * pass your real Scene. All geometry is polygonized CPU-side, so the only
 * Graphics APIs needed are fillStyle/lineStyle/fillPoints/strokePoints/generateTexture.
 * Gradients render as their flat mid-color (IR carries the full gradient if you
 * want to do better later). Deterministic: same IR in, same command stream out.
 */

// ---------------------------------------------------------------- IR types (mirror of src/compile.ts)

export type Rgba = [number, number, number, number];

export interface IRStroke { color: Rgba; width: number }

export type IRDraw =
  | { op: "disc"; r: number; fill?: Rgba; stroke?: IRStroke }
  | { op: "ellipse"; rx: number; ry: number; fill?: Rgba; stroke?: IRStroke }
  | { op: "rect"; w: number; h: number; corner: number; fill?: Rgba; stroke?: IRStroke }
  | { op: "polygon"; points: [number, number][]; fill?: Rgba; stroke?: IRStroke }
  | { op: "ringarc"; r: number; width: number; from: number; to: number; fill?: Rgba }
  | { op: "wedge"; r: number; from: number; to: number; fill?: Rgba; stroke?: IRStroke };

export interface IRNode {
  id: string;
  at: [number, number];
  rot: number;
  scale: [number, number];
  opacity: number;
  draws: IRDraw[];
  children: IRNode[];
}

export type IREase = "linear" | "sine" | "backOut" | "hold" | "quadIn" | "quadOut" | "expoOut";

export interface IRAnimTrack {
  part: string;
  /** scaleX/scaleY squash about the part's own axes; tint covers it `v` of the way in `to` */
  prop: "x" | "y" | "rot" | "scale" | "scaleX" | "scaleY" | "opacity" | "tint";
  /** [t 0..1, value, ease?] — a key's ease shapes the segment leaving it */
  keys: ([number, number] | [number, number, IREase])[];
  ease?: IREase;
  to?: Rgba;
}

export interface IRAnim {
  duration: number;
  tracks: IRAnimTrack[];
  description?: string;
  /** named moments, 0..1 of the clip: `release`, `contact`… (see cueTime / SheetResult.cues) */
  cues?: Record<string, number>;
}

/** An attachment point: where it is at rest (asset space), and the part it rides. */
export interface IRSocket { at: [number, number]; part?: string }

export interface IRAsset {
  format: string;
  id: string;
  size: [number, number];
  anchor: [number, number];
  meta: Record<string, number>;
  nodes: IRNode[];
  variants: Record<string, { scale: number; nodes: IRNode[] }>;
  animations: Record<string, IRAnim>;
  sockets?: Record<string, IRSocket>;
}

// ---------------------------------------------------------------- structural Phaser types

export interface GraphicsLike {
  fillStyle(color: number, alpha?: number): unknown;
  lineStyle(width: number, color: number, alpha?: number): unknown;
  fillPoints(points: { x: number; y: number }[], closeShape?: boolean): unknown;
  strokePoints(points: { x: number; y: number }[], closeShape?: boolean): unknown;
  generateTexture(key: string, width: number, height: number): unknown;
  destroy(): void;
}

export interface ImageLike {
  x: number; y: number; rotation: number; alpha: number;
  setOrigin(x: number, y: number): unknown;
  setScale(x: number, y: number): unknown;
  /** Only needed for clips with `tint` tracks: the cover is a white silhouette tinted to the colour. */
  setTint?(color: number): unknown;
}

export interface ContainerLike { add(child: unknown): unknown }

/** A generated texture, so frames can be carved out of a sheet after baking. */
export interface TextureLike {
  add(name: string | number, sourceIndex: number, x: number, y: number, width: number, height: number): unknown;
}

/** Extra surface `bakeSheet` needs beyond plain drawing. */
export interface SheetSceneLike extends SceneLike {
  textures: { get(key: string): TextureLike };
  anims: { create(config: unknown): unknown; exists(key: string): boolean };
}

export interface SceneLike {
  add: {
    graphics(): GraphicsLike;
    image(x: number, y: number, key: string): ImageLike;
    container(x: number, y: number): ContainerLike;
  };
}

// ---------------------------------------------------------------- small math

type Mat = [number, number, number, number, number, number]; // [a b c d e f]
const IDENT: Mat = [1, 0, 0, 1, 0, 0];

function mul(m: Mat, n: Mat): Mat {
  return [
    m[0] * n[0] + m[2] * n[1],
    m[1] * n[0] + m[3] * n[1],
    m[0] * n[2] + m[2] * n[3],
    m[1] * n[2] + m[3] * n[3],
    m[0] * n[4] + m[2] * n[5] + m[4],
    m[1] * n[4] + m[3] * n[5] + m[5],
  ];
}

function trs(at: [number, number], rotDeg: number, scale: [number, number]): Mat {
  const r = (rotDeg * Math.PI) / 180;
  const cos = Math.cos(r), sin = Math.sin(r);
  return [cos * scale[0], sin * scale[0], -sin * scale[1], cos * scale[1], at[0], at[1]];
}

function invert(m: Mat): Mat {
  const det = m[0] * m[3] - m[1] * m[2] || 1e-9;
  const a = m[3] / det, b = -m[1] / det, c = -m[2] / det, d = m[0] / det;
  return [a, b, c, d, -(a * m[4] + c * m[5]), -(b * m[4] + d * m[5])];
}

function apply(m: Mat, x: number, y: number): { x: number; y: number } {
  return { x: m[0] * x + m[2] * y + m[4], y: m[1] * x + m[3] * y + m[5] };
}

function avgScale(m: Mat): number {
  return (Math.hypot(m[0], m[1]) + Math.hypot(m[2], m[3])) / 2;
}

function colorInt(c: Rgba): number {
  const f = (v: number) => Math.round(v * 255);
  return (f(c[0]) << 16) | (f(c[1]) << 8) | f(c[2]);
}

// ---------------------------------------------------------------- polygonization

const SEGS = 48;

function arcPts(r: number, fromDeg: number, toDeg: number, segs: number): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i <= segs; i++) {
    const a = ((fromDeg + ((toDeg - fromDeg) * i) / segs) * Math.PI) / 180;
    out.push([r * Math.cos(a), r * Math.sin(a)]);
  }
  return out;
}

function ellipsePts(rx: number, ry: number): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < SEGS; i++) {
    const a = (i / SEGS) * Math.PI * 2;
    out.push([rx * Math.cos(a), ry * Math.sin(a)]);
  }
  return out;
}

function roundedRectPts(w: number, h: number, corner: number): [number, number][] {
  const c = Math.min(corner, w / 2, h / 2);
  if (c <= 0)
    return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]];
  const out: [number, number][] = [];
  const centers: [number, number, number][] = [
    [w / 2 - c, -h / 2 + c, -90],
    [w / 2 - c, h / 2 - c, 0],
    [-w / 2 + c, h / 2 - c, 90],
    [-w / 2 + c, -h / 2 + c, 180],
  ];
  for (const [cx, cy, start] of centers)
    for (const [px, py] of arcPts(c, start, start + 90, 6)) out.push([cx + px, cy + py]);
  return out;
}

/** Every draw op as one or more closed fillable loops (in local space). */
function polygonize(draw: IRDraw): [number, number][] {
  switch (draw.op) {
    case "disc": return ellipsePts(draw.r, draw.r);
    case "ellipse": return ellipsePts(draw.rx, draw.ry);
    case "rect": return roundedRectPts(draw.w, draw.h, draw.corner);
    case "polygon": return draw.points;
    case "wedge": return [[0, 0], ...arcPts(draw.r, draw.from, draw.to, 24)];
    case "ringarc": {
      const span = Math.min(Math.abs(draw.to - draw.from), 360);
      const segs = Math.max(12, Math.round((span / 360) * SEGS));
      const outer = arcPts(draw.r + draw.width / 2, draw.from, draw.to, segs);
      const inner = arcPts(draw.r - draw.width / 2, draw.to, draw.from, segs);
      return [...outer, ...inner];
    }
  }
}

// ---------------------------------------------------------------- bake

function drawNode(g: GraphicsLike, node: IRNode, parent: Mat, parentAlpha: number): void {
  const m = mul(parent, trs(node.at, node.rot, node.scale));
  const alpha = parentAlpha * node.opacity;
  for (const d of node.draws) {
    const pts = polygonize(d).map(([x, y]) => apply(m, x, y));
    const fill = d.fill;
    const stroke = "stroke" in d ? d.stroke : undefined;
    // Stroke first, fill over it: the reference renderer lays every outline
    // under its own fill (`paint-order: stroke`), so only the outer half of it
    // shows. Drawn the other way round the inner half eats into the shape —
    // twice the outline the gallery showed, and on a limb a few pixels wide
    // most of the limb.
    if (stroke) {
      g.lineStyle(stroke.width * avgScale(m), colorInt(stroke.color), stroke.color[3] * alpha);
      g.strokePoints(pts, true);
    }
    if (fill) {
      g.fillStyle(colorInt(fill), fill[3] * alpha);
      g.fillPoints(pts, true);
    }
  }
  for (const c of node.children) drawNode(g, c, m, alpha);
}

function nodesOf(ir: IRAsset, variant?: string): { nodes: IRNode[]; vScale: number } {
  if (!variant) return { nodes: ir.nodes, vScale: 1 };
  const v = ir.variants[variant];
  if (!v) throw new Error(`polygraphics: asset "${ir.id}" has no variant "${variant}"`);
  return { nodes: v.nodes, vScale: v.scale };
}

export interface BakeOptions { variant?: string; key?: string; resolution?: number }

/**
 * Bake the whole asset (or a variant) into a single texture. Returns the key.
 * Texture size = size × variantScale × resolution; set the sprite's origin to
 * the IR anchor and scale by 1/resolution.
 */
export function bakeFlat(scene: SceneLike, ir: IRAsset, opts: BakeOptions = {}): string {
  const { nodes, vScale } = nodesOf(ir, opts.variant);
  const res = (opts.resolution ?? 1) * vScale;
  const key = opts.key ?? `pg:${ir.id}${opts.variant ? `#${opts.variant}` : ""}`;
  const w = Math.ceil(ir.size[0] * res);
  const h = Math.ceil(ir.size[1] * res);
  const root: Mat = [res, 0, 0, res, ir.size[0] * res * ir.anchor[0], ir.size[1] * res * ir.anchor[1]];
  const g = scene.add.graphics();
  for (const n of nodes) drawNode(g, n, root, 1);
  g.generateTexture(key, w, h);
  g.destroy();
  return key;
}

// ---------------------------------------------------------------- draw

export interface DrawOptions {
  /** Where the document's origin lands, in the Graphics' own space. */
  x?: number;
  y?: number;
  /** World units per authored unit — the number a bake would have to be scaled by. */
  scale?: number;
  /** Radians about that origin (Phaser's own convention, not the IR's degrees). */
  rotation?: number;
  variant?: string;
  /** A clip to pose before drawing, and how far through it (0..1). */
  animation?: string;
  progress?: number;
  /** Multiplied into every part's own opacity. */
  alpha?: number;
}

/**
 * Draw an asset straight into a Graphics the caller owns — the path `bakeFlat`
 * takes, stopping one step short of the texture.
 *
 * This is the level between a flat bake and a rig, and it is here for the one
 * thing neither does: an effect whose size is not known until it happens. A
 * bake is a picture at one resolution, so a burst drawn at eleven times the
 * size it was baked at is eleven times the blur; a rig has the same pixels
 * plus a display object per part. Here the document is re-solved every frame
 * at the size it is actually drawn, so it is as sharp at r=400 as at r=30 and
 * costs one Graphics per effect.
 *
 * Hot-path objects still want `bakeFlat`: a texture is drawn by the GPU from a
 * quad, and this is geometry every frame. One expanding burst is worth it; two
 * hundred projectiles are not.
 *
 * The caller clears and redraws — a Graphics holds a display list, not a canvas.
 */
export function drawAsset(g: GraphicsLike, ir: IRAsset, opts: DrawOptions = {}): void {
  const { nodes, vScale } = nodesOf(ir, opts.variant);
  let posed = nodes;
  if (opts.animation) {
    const anim = ir.animations[opts.animation];
    if (!anim) throw new Error(`polygraphics: asset "${ir.id}" has no animation "${opts.animation}"`);
    posed = poseNodes(nodes, anim, opts.progress ?? 0);
  }
  const deg = ((opts.rotation ?? 0) * 180) / Math.PI;
  const root = trs([opts.x ?? 0, opts.y ?? 0], deg, [(opts.scale ?? 1) * vScale, (opts.scale ?? 1) * vScale]);
  for (const n of posed) drawNode(g, n, root, opts.alpha ?? 1);
}

// ---------------------------------------------------------------- rig

function nodeBounds(node: IRNode, parent: Mat, box: { minX: number; minY: number; maxX: number; maxY: number }): void {
  const m = mul(parent, trs(node.at, node.rot, node.scale));
  for (const d of node.draws) {
    const margin = ("stroke" in d && d.stroke ? d.stroke.width * avgScale(m) : 0) / 2 + 1;
    for (const [x, y] of polygonize(d)) {
      const p = apply(m, x, y);
      box.minX = Math.min(box.minX, p.x - margin);
      box.minY = Math.min(box.minY, p.y - margin);
      box.maxX = Math.max(box.maxX, p.x + margin);
      box.maxY = Math.max(box.maxY, p.y + margin);
    }
  }
  for (const c of node.children) nodeBounds(c, m, box);
}

interface PartHandle {
  img: ImageLike;
  /** the tint cover, for a part some clip tints */
  cover?: ImageLike;
  baseX: number; baseY: number; baseRot: number;
  baseSX: number; baseSY: number; baseAlpha: number;
  sign: number; // -1 for mirrored copies: x/rot offsets flip so both sides stay symmetric
}

/**
 * The eases, and a track's value at a point in the clip. A copy of src/anim.ts
 * (this file stays one drop-in with no imports); scripts/test-phaser-adapter.ts
 * samples every ease and every track in the library through both and fails on
 * the first value that differs.
 */
const EASE_FN: Record<IREase, (t: number) => number> = {
  linear: (t) => t,
  sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * t),
  backOut: (t) => { const c = 1.70158; const u = t - 1; return 1 + (c + 1) * u * u * u + c * u * u; },
  hold: (t) => (t >= 1 ? 1 : 0),
  quadIn: (t) => t * t,
  quadOut: (t) => 1 - (1 - t) * (1 - t),
  expoOut: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
};

/** A track's value at `progress` (0..1 through the clip). */
export function trackValue(track: IRAnimTrack, progress: number): number {
  const keys = track.keys;
  if (progress <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1] = keys[i];
    if (progress <= t1) {
      const [t0, v0] = keys[i - 1];
      const span = t1 - t0;
      if (span <= 0) return v1;
      const ease = keys[i - 1][2] ?? track.ease ?? "sine";
      return v0 + (v1 - v0) * EASE_FN[ease]((progress - t0) / span);
    }
  }
  return keys[keys.length - 1][1];
}

const evalTrack = trackValue;

/** A cue's time in seconds into the clip, or undefined when the clip has no such cue. */
export function cueTime(ir: IRAsset, animation: string, cue: string): number | undefined {
  const anim = ir.animations[animation];
  const t = anim?.cues?.[cue];
  return anim && t !== undefined ? t * anim.duration : undefined;
}

/**
 * The frame of an n-frame sheet on which a cue has happened. Frame f shows the
 * clip at f/n (see bakeSheet), so this is the first frame at or past the cue.
 */
export function cueFrame(t: number, frames: number): number {
  return Math.min(frames - 1, Math.max(0, Math.ceil(t * frames - 1e-9)));
}

/** Mix a colour `f` of the way toward another, keeping its own alpha. */
function mixRgba(c: Rgba, to: Rgba, f: number): Rgba {
  return [c[0] + (to[0] - c[0]) * f, c[1] + (to[1] - c[1]) * f, c[2] + (to[2] - c[2]) * f, c[3]];
}

/** A node subtree repainted: every fill and stroke mapped through `paint`. */
function repaint(node: IRNode, paint: (c: Rgba) => Rgba): IRNode {
  return {
    ...node,
    draws: node.draws.map((d) => {
      const out = { ...d } as IRDraw & { fill?: Rgba; stroke?: IRStroke };
      if (out.fill) out.fill = paint(out.fill);
      if ("stroke" in d && d.stroke) out.stroke = { ...d.stroke, color: paint(d.stroke.color) };
      return out as IRDraw;
    }),
    children: node.children.map((c) => repaint(c, paint)),
  };
}

export interface Rig {
  container: ContainerLike;
  parts: Map<string, PartHandle[]>;
  play(anim: string, opts?: { loop?: boolean; onComplete?: () => void }): void;
  stop(): void;
  /** advance the animation clock; call from your scene's update with dt in seconds */
  tick(dtSec: number): void;
}

export interface RigOptions {
  variant?: string;
  resolution?: number;
  keyPrefix?: string;
  /**
   * Optional probe so a rig rebuilt on a re-entered scene reuses the part
   * textures it baked last time instead of regenerating them under the same
   * keys. Pass `(k) => scene.textures.exists(k)`.
   */
  hasTexture?: (key: string) => boolean;
}

/**
 * Build a Container with one Image per top-level IR node (per-part textures baked
 * on first use) and a keyframe player driving x/y/rot/scale/squash/opacity
 * offsets. A part some clip tints gets a second Image over it — its silhouette
 * baked white, tinted to the clip's colour, shown at the tint's amount.
 */
export function buildRig(scene: SceneLike, ir: IRAsset, opts: RigOptions = {}): Rig {
  const { nodes, vScale } = nodesOf(ir, opts.variant);
  const res = opts.resolution ?? 2;
  const prefix = opts.keyPrefix ?? `pg:${ir.id}${opts.variant ? `#${opts.variant}` : ""}`;

  const container = scene.add.container(0, 0);
  const parts = new Map<string, PartHandle[]>();
  const tinted = new Set<string>();
  for (const anim of Object.values(ir.animations))
    for (const tr of anim.tracks) if (tr.prop === "tint") tinted.add(tr.part);

  nodes.forEach((node, i) => {
    // bake the node subtree in local space (identity transform), then let the
    // Image carry at/rot/scale — that keeps parts animatable.
    const local: IRNode = { ...node, at: [0, 0], rot: 0, scale: [Math.abs(node.scale[0]), Math.abs(node.scale[1])], opacity: 1 };
    const box = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
    nodeBounds(local, IDENT, box);
    if (box.minX > box.maxX) return; // empty node
    const w = Math.max(1, Math.ceil((box.maxX - box.minX) * res));
    const h = Math.max(1, Math.ceil((box.maxY - box.minY) * res));
    const origin: Mat = [res, 0, 0, res, -box.minX * res, -box.minY * res];
    const bake = (key: string, n: IRNode) => {
      if (opts.hasTexture?.(key)) return;
      const g = scene.add.graphics();
      drawNode(g, n, origin, 1);
      g.generateTexture(key, w, h);
      g.destroy();
    };
    const key = `${prefix}/${node.id}#${i}`;
    bake(key, local);

    const sign = node.scale[0] < 0 ? -1 : 1;
    const place = (img: ImageLike) => {
      img.setOrigin((-box.minX * res) / w, (-box.minY * res) / h);
      img.setScale((sign * vScale) / res, vScale / res);
      img.x = node.at[0] * vScale;
      img.y = node.at[1] * vScale;
      img.rotation = (sign * node.rot * Math.PI) / 180;
      return img;
    };
    const img = place(scene.add.image(node.at[0] * vScale, node.at[1] * vScale, key));
    img.alpha = node.opacity;
    container.add(img);

    let cover: ImageLike | undefined;
    if (tinted.has(node.id)) {
      const ckey = `${key}~white`;
      bake(ckey, repaint(local, (c) => [1, 1, 1, c[3]]));
      cover = place(scene.add.image(node.at[0] * vScale, node.at[1] * vScale, ckey));
      cover.alpha = 0;
      container.add(cover);
    }

    const handle: PartHandle = {
      img,
      cover,
      baseX: node.at[0] * vScale, baseY: node.at[1] * vScale,
      baseRot: (sign * node.rot * Math.PI) / 180,
      baseSX: (sign * vScale) / res, baseSY: vScale / res, baseAlpha: node.opacity,
      sign,
    };
    parts.set(node.id, [...(parts.get(node.id) ?? []), handle]);
  });

  let current: IRAnim | null = null;
  let loop = true;
  let onComplete: (() => void) | undefined;
  let t = 0;

  function pose(hd: PartHandle, p: PartPose): void {
    hd.img.x = hd.baseX + p.dx * vScale * hd.sign;
    hd.img.y = hd.baseY + p.dy * vScale;
    hd.img.rotation = hd.baseRot + (p.drot * Math.PI * hd.sign) / 180;
    hd.img.setScale(hd.baseSX * p.s * p.sx, hd.baseSY * p.s * p.sy);
    hd.img.alpha = hd.baseAlpha * p.alpha;
    if (hd.cover) {
      hd.cover.x = hd.img.x; hd.cover.y = hd.img.y; hd.cover.rotation = hd.img.rotation;
      hd.cover.setScale(hd.baseSX * p.s * p.sx, hd.baseSY * p.s * p.sy);
      hd.cover.alpha = hd.img.alpha * p.tint;
      if (p.tintTo) hd.cover.setTint?.(colorInt(p.tintTo));
    }
  }

  function rest(): void {
    for (const handles of parts.values()) for (const hd of handles) pose(hd, restPose());
  }

  function applyProgress(progress: number): void {
    if (!current) return;
    // Every part the clip touches is posed from rest each frame, so two tracks
    // on one part (a squash and a turn) compose instead of the last one winning.
    const posed = new Map<string, PartPose>();
    for (const track of current.tracks) {
      if (!parts.has(track.part)) continue;
      let p = posed.get(track.part);
      if (!p) posed.set(track.part, (p = restPose()));
      foldTrack(p, track, evalTrack(track, progress));
    }
    for (const [id, p] of posed) for (const hd of parts.get(id)!) pose(hd, p);
  }

  return {
    container,
    parts,
    play(name, o = {}) {
      const anim = ir.animations[name];
      if (!anim) throw new Error(`polygraphics: asset "${ir.id}" has no animation "${name}"`);
      // a part the last clip moved and this one does not goes back to rest
      rest();
      current = anim;
      loop = o.loop ?? true;
      onComplete = o.onComplete;
      t = 0;
      applyProgress(0);
    },
    stop() {
      current = null;
      rest();
    },
    tick(dt) {
      if (!current) return;
      t += dt;
      if (t >= current.duration) {
        if (loop) t %= current.duration;
        else {
          applyProgress(1);
          current = null;
          onComplete?.();
          return;
        }
      }
      applyProgress(t / current.duration);
    },
  };
}

/** One part's offsets from its authored transform, at one moment of a clip. */
interface PartPose { dx: number; dy: number; drot: number; s: number; sx: number; sy: number; alpha: number; tint: number; tintTo?: Rgba }

function restPose(): PartPose {
  return { dx: 0, dy: 0, drot: 0, s: 1, sx: 1, sy: 1, alpha: 1, tint: 0 };
}

function foldTrack(p: PartPose, track: IRAnimTrack, v: number): void {
  switch (track.prop) {
    case "x": p.dx = v; break;
    case "y": p.dy = v; break;
    case "rot": p.drot = v; break;
    case "scale": p.s = v; break;
    case "scaleX": p.sx = v; break;
    case "scaleY": p.sy = v; break;
    case "opacity": p.alpha = v; break;
    case "tint": p.tint = Math.max(0, Math.min(1, v)); p.tintTo = track.to; break;
  }
}

// ---------------------------------------------------------------- spritesheet

/**
 * Applies an animation's tracks to a copy of the node list at `progress` (0..1).
 * Offsets are additive over each node's authored transform, matching buildRig,
 * and mirrored copies (which share their id) get x and rot negated so a pair
 * stays symmetric. A squash scales along the node's own axes; a tint mixes its
 * colours toward the tint's.
 *
 * Exported so a consumer can ask where a part is on a frame of a baked sheet
 * without drawing it: `bakeSheet` poses frame f of n at progress f / n.
 */
export function poseNodes(nodes: IRNode[], anim: IRAnim, progress: number): IRNode[] {
  const out = nodes.map((n) => structuredClone(n));
  for (const track of anim.tracks) {
    const v = evalTrack(track, progress);
    for (const n of out) {
      if (n.id !== track.part) continue;
      const sign = n.scale[0] < 0 ? -1 : 1;
      switch (track.prop) {
        case "x": n.at = [n.at[0] + v * sign, n.at[1]]; break;
        case "y": n.at = [n.at[0], n.at[1] + v]; break;
        case "rot": n.rot += v * sign; break;
        case "scale": n.scale = [n.scale[0] * v, n.scale[1] * v]; break;
        case "scaleX": n.scale = [n.scale[0] * v, n.scale[1]]; break;
        case "scaleY": n.scale = [n.scale[0], n.scale[1] * v]; break;
        case "opacity": n.opacity *= v; break;
        case "tint": {
          // the colour mixed toward the tint: what the rig's cover shows over an opaque part
          const f = Math.max(0, Math.min(1, v));
          const to = track.to;
          if (to && f > 0) Object.assign(n, repaint(n, (c) => mixRgba(c, to, f)));
          break;
        }
      }
    }
  }
  return out;
}

export interface SheetOptions {
  /** animation name on the asset */
  animation: string;
  key?: string;
  variant?: string;
  /** sample rate and playback rate; frames = duration × fps */
  fps?: number;
  maxFrames?: number;
  /** frames wrap into a grid rather than one long row, so old GPUs cope */
  maxWidth?: number;
  resolution?: number;
  /** Phaser repeat: -1 loops forever (default), 0 plays once */
  repeat?: number;
}

export interface SheetResult {
  key: string;
  frames: number;
  /** each of the clip's cues as the frame it has happened on (cueFrame) */
  cues: Record<string, number>;
  cell: [number, number];
  texture: [number, number];
}

/**
 * Renders an animation to a spritesheet texture and registers a matching Phaser
 * animation under the same key. The sprite stays ONE quad, so pooled actors keep
 * batching — this is the path for anything there are many of, or anything whose
 * system already assumes a plain Sprite. Use buildRig instead when instances are
 * few and continuous motion matters more than draw calls.
 */
export function bakeSheet(scene: SheetSceneLike, ir: IRAsset, opts: SheetOptions): SheetResult {
  const anim = ir.animations[opts.animation];
  if (!anim) throw new Error(`polygraphics: asset "${ir.id}" has no animation "${opts.animation}"`);
  const { nodes, vScale } = nodesOf(ir, opts.variant);

  const fps = opts.fps ?? 15;
  const res = (opts.resolution ?? 1) * vScale;
  const frames = Math.max(2, Math.min(opts.maxFrames ?? 48, Math.round(anim.duration * fps)));
  const cellW = Math.ceil(ir.size[0] * res);
  const cellH = Math.ceil(ir.size[1] * res);
  // Wrap into a grid only when a single row would exceed the width floor, and
  // never allocate more columns than there are frames to put in them.
  const cols = Math.max(1, Math.min(frames, Math.floor((opts.maxWidth ?? 2048) / cellW)));
  const rows = Math.ceil(frames / cols);
  const key = opts.key ?? `pg:${ir.id}:${opts.animation}`;

  const g = scene.add.graphics();
  for (let f = 0; f < frames; f++) {
    const col = f % cols;
    const row = Math.floor(f / cols);
    const root: Mat = [res, 0, 0, res, col * cellW + cellW * ir.anchor[0], row * cellH + cellH * ir.anchor[1]];
    // progress stops short of 1 so the last frame flows back into the first
    for (const n of poseNodes(nodes, anim, f / frames)) drawNode(g, n, root, 1);
  }
  g.generateTexture(key, cols * cellW, rows * cellH);
  g.destroy();

  const tex = scene.textures.get(key);
  for (let f = 0; f < frames; f++) {
    tex.add(f, 0, (f % cols) * cellW, Math.floor(f / cols) * cellH, cellW, cellH);
  }

  if (!scene.anims.exists(key)) {
    scene.anims.create({
      key,
      frames: Array.from({ length: frames }, (_, f) => ({ key, frame: f })),
      frameRate: fps,
      repeat: opts.repeat ?? -1,
    });
  }

  const cues: Record<string, number> = {};
  for (const [name, ct] of Object.entries(anim.cues ?? {})) cues[name] = cueFrame(ct, frames);
  return { key, frames, cues, cell: [cellW, cellH], texture: [cols * cellW, rows * cellH] };
}

// ---------------------------------------------------------------- sockets

export interface SocketOptions {
  variant?: string;
  /** a clip to pose the socket's part in, and how far through it (0..1) */
  animation?: string;
  progress?: number;
}

/**
 * Where a socket is, in the asset's own space (origin at the anchor, variant
 * scale applied) — multiply by the sprite's scale and flip x for a sprite
 * facing left. A socket that rides a part goes where the clip takes that part
 * at `progress`: the same pose `bakeSheet` draws, so a projectile spawned at
 * the socket on a cue frame leaves from the hand the frame shows.
 * Undefined when the asset has no such socket.
 */
export function socketAt(ir: IRAsset, name: string, opts: SocketOptions = {}): { x: number; y: number } | undefined {
  const sock = ir.sockets?.[name];
  if (!sock) return undefined;
  const { nodes, vScale } = nodesOf(ir, opts.variant);
  let { x, y } = { x: sock.at[0], y: sock.at[1] };
  const anim = opts.animation ? ir.animations[opts.animation] : undefined;
  if (opts.animation && !anim) throw new Error(`polygraphics: asset "${ir.id}" has no animation "${opts.animation}"`);
  if (sock.part && anim) {
    const node = nodes.find((n) => n.id === sock.part && n.scale[0] >= 0) ?? nodes.find((n) => n.id === sock.part);
    if (node) {
      const posed = poseNodes([node], anim, opts.progress ?? 0)[0];
      const rest = trs(node.at, node.rot, node.scale);
      const now = trs(posed.at, posed.rot, posed.scale);
      ({ x, y } = apply(mul(now, invert(rest)), x, y));
    }
  }
  return { x: x * vScale, y: y * vScale };
}

// ---------------------------------------------------------------- octants

export interface OctantOptions {
  key?: string;
  variant?: string;
  /** how many evenly spaced headings to author; 8 is the classic choice */
  directions?: number;
  resolution?: number;
  maxWidth?: number;
}

export interface OctantResult { key: string; directions: number; cell: [number, number] }

/**
 * Bakes the asset once per heading into a spritesheet, so a projectile can face
 * where it is going by picking a frame instead of by `setRotation`. Rotating a
 * finished sprite turns its highlights and its baked contour with it, which
 * reads wrong the moment the art implies a fixed light; a pre-authored heading
 * keeps the shading upright.
 *
 * Frame n is the heading n × 360/directions, measured clockwise from +x — the
 * same convention as `Math.atan2(vy, vx)`. Use `octantFrame` to pick one.
 */
export function bakeOctants(scene: SheetSceneLike, ir: IRAsset, opts: OctantOptions = {}): OctantResult {
  const { nodes, vScale } = nodesOf(ir, opts.variant);
  const directions = opts.directions ?? 8;
  const res = (opts.resolution ?? 1) * vScale;
  // a heading of 45° puts the diagonal of the artwork across the cell
  const diag = Math.ceil(Math.hypot(ir.size[0], ir.size[1]) * res);
  const cols = Math.max(1, Math.min(directions, Math.floor((opts.maxWidth ?? 2048) / diag)));
  const rows = Math.ceil(directions / cols);
  const key = opts.key ?? `pg:${ir.id}:oct`;

  const g = scene.add.graphics();
  for (let d = 0; d < directions; d++) {
    const col = d % cols;
    const row = Math.floor(d / cols);
    const a = ((d * 360) / directions) * (Math.PI / 180);
    const cos = Math.cos(a), sin = Math.sin(a);
    // rotate about the cell centre, which is where the asset's anchor lands
    const root: Mat = [cos * res, sin * res, -sin * res, cos * res, col * diag + diag / 2, row * diag + diag / 2];
    for (const n of nodes) drawNode(g, n, root, 1);
  }
  g.generateTexture(key, cols * diag, rows * diag);
  g.destroy();

  const tex = scene.textures.get(key);
  for (let d = 0; d < directions; d++) {
    tex.add(d, 0, (d % cols) * diag, Math.floor(d / cols) * diag, diag, diag);
  }
  return { key, directions, cell: [diag, diag] };
}

/** Frame index for a heading in radians (as returned by Math.atan2(vy, vx)). */
export function octantFrame(angleRad: number, directions = 8): number {
  const step = (Math.PI * 2) / directions;
  return ((Math.round(angleRad / step) % directions) + directions) % directions;
}
