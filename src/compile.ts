/**
 * Compiler: asset document → engine-neutral IR (intermediate representation).
 *
 * The IR is what game engines import. Everything authoring-time is resolved away:
 *   - token references  → concrete [r, g, b, a] floats
 *   - variants          → pre-applied full node lists
 *   - `use` composition → inlined child trees
 *   - `mirrorX`         → expanded to a second node (at.x/rot/scale.x negated)
 *   - seeded `repeat`   → expanded to concrete child instances (engines need no PRNG)
 *   - ngon/star         → concrete polygon points
 * Adapters are therefore dumb interpreters: walk nodes, draw ops, tween tracks.
 */
import type { Anim, Asset, Paint, Part, Shape } from "./schema.js";
import { applyVariant, derivedRadius, type Issue, type Registry } from "./render.js";
import { resolveColorRgba, resolveNumber, type Tokens } from "./tokens.js";
import { mulberry32, hashSeed } from "./prng.js";

export type Rgba = [number, number, number, number];

export type IRDraw =
  | { op: "disc"; r: number; fill?: Rgba; gradient?: IRGradient; stroke?: IRStroke }
  | { op: "ellipse"; rx: number; ry: number; fill?: Rgba; gradient?: IRGradient; stroke?: IRStroke }
  | { op: "rect"; w: number; h: number; corner: number; fill?: Rgba; gradient?: IRGradient; stroke?: IRStroke }
  | { op: "polygon"; points: [number, number][]; fill?: Rgba; gradient?: IRGradient; stroke?: IRStroke }
  | { op: "ringarc"; r: number; width: number; from: number; to: number; fill?: Rgba }
  | { op: "wedge"; r: number; from: number; to: number; fill?: Rgba; gradient?: IRGradient; stroke?: IRStroke };

export interface IRGradient {
  type: "linear" | "radial";
  from: [number, number];
  to: [number, number];
  stops: [number, Rgba][];
}

export interface IRStroke {
  color: Rgba;
  width: number;
}

export interface IRNode {
  id: string;
  at: [number, number];
  rot: number; // degrees
  scale: [number, number];
  opacity: number;
  draws: IRDraw[];
  children: IRNode[];
}

export interface IRAsset {
  format: "polygraphics-ir";
  version: 1;
  id: string;
  name: string;
  description: string;
  tags: string[];
  size: [number, number];
  anchor: [number, number];
  meta: Record<string, number>;
  nodes: IRNode[];
  variants: Record<string, { description: string; scale: number; nodes: IRNode[] }>;
  animations: Record<string, Anim>;
}

function rgba(ref: string, t: Tokens, issues: Issue[], where: string): Rgba {
  const r = resolveColorRgba(ref, t);
  if (!r.ok) {
    issues.push({ level: "error", where, msg: r.error });
    return [1, 0, 1, 1];
  }
  return r.value;
}

function midStop(stops: [number, Rgba][]): Rgba {
  const [r1, g1, b1, a1] = stops[0][1];
  const [r2, g2, b2, a2] = stops[stops.length - 1][1];
  const f = (a: number, b: number) => Math.round(((a + b) / 2) * 10000) / 10000;
  return [f(r1, r2), f(g1, g2), f(b1, b2), f(a1, a2)];
}

function compilePaint(
  paint: Paint | undefined,
  t: Tokens,
  issues: Issue[],
  where: string,
): { fill?: Rgba; gradient?: IRGradient } {
  if (paint === undefined) return {};
  if (typeof paint === "string") return { fill: rgba(paint, t, issues, where) };
  const stops = paint.stops.map(([off, ref]) => [off, rgba(ref, t, issues, where)] as [number, Rgba]);
  const gradient: IRGradient = {
    type: paint.gradient,
    from: paint.from ?? (paint.gradient === "linear" ? [0.5, 0] : [0.5, 0.5]),
    to: paint.to ?? [0.5, 1],
    stops,
  };
  return { fill: midStop(stops), gradient }; // fill = flat fallback for engines without gradients
}

function compileStroke(part: Part, t: Tokens, issues: Issue[], where: string): IRStroke | undefined {
  if (!("stroke" in part) || !part.stroke) return undefined;
  const w = resolveNumber(part.stroke.width, t.strokes, "stroke");
  if (!w.ok) issues.push({ level: "error", where, msg: w.error });
  return { color: rgba(part.stroke.color, t, issues, where), width: w.ok ? w.value : 1 };
}

function ngonPts(sides: number, r: number, rot = 0): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < sides; i++) {
    const a = ((-90 + rot + (360 / sides) * i) * Math.PI) / 180;
    out.push([round2(r * Math.cos(a)), round2(r * Math.sin(a))]);
  }
  return out;
}

function starPts(points: number, r: number, r2: number, rot = 0): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < points * 2; i++) {
    const rad = i % 2 === 0 ? r : r2;
    const a = ((-90 + rot + (180 / points) * i) * Math.PI) / 180;
    out.push([round2(rad * Math.cos(a)), round2(rad * Math.sin(a))]);
  }
  return out;
}

const round2 = (n: number) => Math.round(n * 100) / 100;

function compileShapeDraw(
  shape: Shape,
  paint: { fill?: Rgba; gradient?: IRGradient },
  stroke: IRStroke | undefined,
  issues: Issue[],
  where: string,
): IRDraw {
  switch (shape.kind) {
    case "circle":
      return { op: "disc", r: shape.r, ...paint, stroke };
    case "ellipse":
      return { op: "ellipse", rx: shape.rx, ry: shape.ry, ...paint, stroke };
    case "rect":
      return { op: "rect", w: shape.w, h: shape.h, corner: shape.corner ?? 0, ...paint, stroke };
    case "ngon":
      return { op: "polygon", points: ngonPts(shape.sides, shape.r, shape.rot), ...paint, stroke };
    case "star":
      return { op: "polygon", points: starPts(shape.points, shape.r, shape.r2, shape.rot), ...paint, stroke };
    case "poly":
      return { op: "polygon", points: shape.points.map(([x, y]) => [round2(x), round2(y)] as [number, number]), ...paint, stroke };
    case "ring":
      if (!paint.fill) issues.push({ level: "error", where, msg: "ring needs `fill` (used as its stroke color)" });
      return { op: "ringarc", r: shape.r, width: shape.width, from: shape.from ?? 0, to: shape.to ?? 360, fill: paint.fill };
    case "wedge":
      return { op: "wedge", r: shape.r, from: shape.from, to: shape.to, ...paint, stroke };
  }
}

function baseNode(part: Part, t: Tokens, issues: Issue[], where: string): IRNode {
  let opacity = 1;
  if (part.opacity !== undefined) {
    const o = resolveNumber(part.opacity, t.alpha, "alpha");
    if (!o.ok) issues.push({ level: "error", where, msg: o.error });
    else opacity = o.value;
  }
  const scale: [number, number] =
    part.scale === undefined ? [1, 1] : typeof part.scale === "number" ? [part.scale, part.scale] : part.scale;
  return { id: part.id, at: part.at ?? [0, 0], rot: part.rot ?? 0, scale, opacity, draws: [], children: [] };
}

function mirrored(n: IRNode): IRNode {
  return {
    ...structuredClone(n),
    at: [-n.at[0], n.at[1]],
    rot: -n.rot,
    scale: [-n.scale[0], n.scale[1]],
  };
}

function compileParts(
  parts: Part[],
  ownerId: string,
  reg: Registry,
  issues: Issue[],
  whereBase: string,
  useStack: string[],
): IRNode[] {
  const nodes: IRNode[] = [];
  for (const part of parts) {
    const where = `${whereBase}(${part.id})`;
    const node = baseNode(part, reg.tokens, issues, where);

    if ("use" in part) {
      const target = reg.assets.get(part.use);
      if (!target) {
        issues.push({ level: "error", where, msg: `use: unknown asset "${part.use}"` });
        continue;
      }
      if (useStack.includes(part.use) || useStack.length >= 4) {
        issues.push({ level: "error", where, msg: `use: cycle or depth > 4 via "${part.use}"` });
        continue;
      }
      const resolved = part.variant ? applyVariant(target, part.variant, issues) : target;
      if (part.variant) {
        const vs = target.variants?.[part.variant]?.scale ?? 1;
        node.scale = [node.scale[0] * vs, node.scale[1] * vs];
      }
      node.children = compileParts(resolved.parts, target.id, reg, issues, part.use, [...useStack, part.use]);
    } else if ("repeat" in part) {
      const { of, count, area, seed, jitterRot, scaleRange } = part.repeat;
      const rng = mulberry32(seed ?? hashSeed(`${ownerId}:${part.id}`));
      const paint = compilePaint(part.fill, reg.tokens, issues, where);
      const stroke = compileStroke(part, reg.tokens, issues, where);
      const draw = compileShapeDraw(of, paint, stroke, issues, where);
      for (let i = 0; i < count; i++) {
        const x = round2((rng() - 0.5) * area[0]);
        const y = round2((rng() - 0.5) * area[1]);
        const rot = jitterRot ? Math.round(rng() * 360) : 0;
        const s = scaleRange ? round2(scaleRange[0] + rng() * (scaleRange[1] - scaleRange[0])) : 1;
        node.children.push({ id: `s${i}`, at: [x, y], rot, scale: [s, s], opacity: 1, draws: [structuredClone(draw)], children: [] });
      }
    } else {
      const paint = compilePaint(part.fill, reg.tokens, issues, where);
      const stroke = compileStroke(part, reg.tokens, issues, where);
      node.draws.push(compileShapeDraw(part.shape, paint, stroke, issues, where));
    }

    nodes.push(node);
    if (part.mirrorX) nodes.push(mirrored(node));
  }
  return nodes;
}

export function compileAsset(asset: Asset, reg: Registry): { ir: IRAsset; issues: Issue[] } {
  const issues: Issue[] = [];
  const nodes = compileParts(asset.parts, asset.id, reg, issues, asset.id, []);

  const variants: IRAsset["variants"] = {};
  for (const [vname, v] of Object.entries(asset.variants ?? {})) {
    const applied = applyVariant(asset, vname, issues);
    variants[vname] = {
      description: v.description,
      scale: v.scale ?? 1,
      nodes: compileParts(applied.parts, asset.id, reg, issues, `${asset.id}#${vname}`, []),
    };
  }

  const ir: IRAsset = {
    format: "polygraphics-ir",
    version: 1,
    id: asset.id,
    name: asset.name,
    description: asset.description,
    tags: asset.tags,
    size: asset.size,
    anchor: asset.anchor ?? [0.5, 0.5],
    meta: { ...asset.meta, radius: derivedRadius(asset, reg) },
    nodes,
    variants,
    animations: asset.animations ?? {},
  };
  return { ir, issues };
}
