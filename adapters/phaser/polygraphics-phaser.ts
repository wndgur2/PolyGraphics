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

export interface IRAnimTrack {
  part: string;
  prop: "x" | "y" | "rot" | "scale" | "opacity";
  keys: [number, number][];
  ease?: "linear" | "sine" | "backOut";
}

export interface IRAnim { duration: number; tracks: IRAnimTrack[]; description?: string }

export interface IRAsset {
  format: string;
  id: string;
  size: [number, number];
  anchor: [number, number];
  meta: Record<string, number>;
  nodes: IRNode[];
  variants: Record<string, { scale: number; nodes: IRNode[] }>;
  animations: Record<string, IRAnim>;
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
    if (fill) {
      g.fillStyle(colorInt(fill), fill[3] * alpha);
      g.fillPoints(pts, true);
    }
    if (stroke) {
      g.lineStyle(stroke.width * avgScale(m), colorInt(stroke.color), stroke.color[3] * alpha);
      g.strokePoints(pts, true);
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
  baseX: number; baseY: number; baseRot: number;
  baseSX: number; baseSY: number; baseAlpha: number;
  sign: number; // -1 for mirrored copies: x/rot offsets flip so both sides stay symmetric
}

const EASE_FN: Record<string, (t: number) => number> = {
  linear: (t) => t,
  sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * t),
  backOut: (t) => { const c = 1.70158; const u = t - 1; return 1 + (c + 1) * u * u * u + c * u * u; },
};

function evalTrack(track: IRAnimTrack, progress: number): number {
  const keys = track.keys;
  if (progress <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (progress <= keys[i][0]) {
      const [t0, v0] = keys[i - 1];
      const [t1, v1] = keys[i];
      const span = t1 - t0 || 1;
      const f = EASE_FN[track.ease ?? "sine"]((progress - t0) / span);
      return v0 + (v1 - v0) * f;
    }
  }
  return keys[keys.length - 1][1];
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
 * on first use) and a keyframe player driving x/y/rot/scale/opacity offsets.
 */
export function buildRig(scene: SceneLike, ir: IRAsset, opts: RigOptions = {}): Rig {
  const { nodes, vScale } = nodesOf(ir, opts.variant);
  const res = opts.resolution ?? 2;
  const prefix = opts.keyPrefix ?? `pg:${ir.id}${opts.variant ? `#${opts.variant}` : ""}`;

  const container = scene.add.container(0, 0);
  const parts = new Map<string, PartHandle[]>();

  nodes.forEach((node, i) => {
    // bake the node subtree in local space (identity transform), then let the
    // Image carry at/rot/scale — that keeps parts animatable.
    const local: IRNode = { ...node, at: [0, 0], rot: 0, scale: [Math.abs(node.scale[0]), Math.abs(node.scale[1])], opacity: 1 };
    const box = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
    nodeBounds(local, IDENT, box);
    if (box.minX > box.maxX) return; // empty node
    const w = Math.max(1, Math.ceil((box.maxX - box.minX) * res));
    const h = Math.max(1, Math.ceil((box.maxY - box.minY) * res));
    const key = `${prefix}/${node.id}#${i}`;
    if (!opts.hasTexture?.(key)) {
      const g = scene.add.graphics();
      drawNode(g, local, [res, 0, 0, res, -box.minX * res, -box.minY * res], 1);
      g.generateTexture(key, w, h);
      g.destroy();
    }

    const sign = node.scale[0] < 0 ? -1 : 1;
    const img = scene.add.image(node.at[0] * vScale, node.at[1] * vScale, key);
    img.setOrigin((-box.minX * res) / w, (-box.minY * res) / h);
    const sx = (sign * vScale) / res;
    const sy = vScale / res;
    img.setScale(sx, sy);
    img.rotation = (sign * node.rot * Math.PI) / 180;
    img.alpha = node.opacity;
    container.add(img);

    const handle: PartHandle = {
      img,
      baseX: node.at[0] * vScale, baseY: node.at[1] * vScale,
      baseRot: (sign * node.rot * Math.PI) / 180,
      baseSX: sx, baseSY: sy, baseAlpha: node.opacity,
      sign,
    };
    parts.set(node.id, [...(parts.get(node.id) ?? []), handle]);
  });

  let current: IRAnim | null = null;
  let loop = true;
  let onComplete: (() => void) | undefined;
  let t = 0;

  function applyProgress(progress: number): void {
    if (!current) return;
    for (const track of current.tracks) {
      const handles = parts.get(track.part);
      if (!handles) continue;
      const v = evalTrack(track, progress);
      for (const hd of handles) {
        switch (track.prop) {
          case "x": hd.img.x = hd.baseX + v * vScale * hd.sign; break;
          case "y": hd.img.y = hd.baseY + v * vScale; break;
          case "rot": hd.img.rotation = hd.baseRot + (v * Math.PI * hd.sign) / 180; break;
          case "scale": hd.img.setScale(hd.baseSX * v, hd.baseSY * v); break;
          case "opacity": hd.img.alpha = hd.baseAlpha * v; break;
        }
      }
    }
  }

  return {
    container,
    parts,
    play(name, o = {}) {
      const anim = ir.animations[name];
      if (!anim) throw new Error(`polygraphics: asset "${ir.id}" has no animation "${name}"`);
      current = anim;
      loop = o.loop ?? true;
      onComplete = o.onComplete;
      t = 0;
      applyProgress(0);
    },
    stop() {
      current = null;
      for (const handles of parts.values())
        for (const hd of handles) {
          hd.img.x = hd.baseX; hd.img.y = hd.baseY; hd.img.rotation = hd.baseRot;
          hd.img.setScale(hd.baseSX, hd.baseSY); hd.img.alpha = hd.baseAlpha;
        }
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

// ---------------------------------------------------------------- spritesheet

/**
 * Applies an animation's tracks to a copy of the node list at `progress` (0..1).
 * Offsets are additive over each node's authored transform, matching buildRig,
 * and mirrored copies (which share their id) get x and rot negated so a pair
 * stays symmetric.
 */
function poseNodes(nodes: IRNode[], anim: IRAnim, progress: number): IRNode[] {
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
        case "opacity": n.opacity *= v; break;
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

  return { key, frames, cell: [cellW, cellH], texture: [cols * cellW, rows * cellH] };
}
