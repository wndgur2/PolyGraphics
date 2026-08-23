/**
 * Deterministic SVG renderer: interprets asset documents against a token set.
 * Same asset + same tokens + same seed → byte-identical SVG (diffable output).
 */
import type { Anim, Asset, Gradient, Paint, Part, RepeatPart, Shape, ShapePart, UsePart } from "./schema.js";
import { PartSchema } from "./schema.js";
import { mulberry32, hashSeed } from "./prng.js";
import { resolveColor, resolveNumber, suggest, type Tokens } from "./tokens.js";

export interface Issue {
  level: "error" | "warn";
  where: string;
  msg: string;
}

export interface Registry {
  assets: Map<string, Asset>;
  tokens: Tokens;
}

export interface RenderOptions {
  variant?: string;
  animation?: string; // animation name to embed as CSS (gallery use)
  displayScale?: number; // width/height attrs = size * displayScale
  uid?: string; // unique prefix so multiple inline SVGs never collide
}

const FALLBACK = "#ff00ff"; // loud placeholder for unresolvable paints

// ---------------------------------------------------------------- variants

export function applyVariant(base: Asset, variantName: string, issues: Issue[]): Asset {
  const v = base.variants?.[variantName];
  if (!v) {
    issues.push({ level: "error", where: `${base.id}`, msg: `unknown variant "${variantName}"` });
    return base;
  }
  const where = `${base.id}#${variantName}`;
  let parts: Part[] = structuredClone(base.parts);

  for (const rid of v.remove ?? []) {
    if (!parts.some((p) => p.id === rid))
      issues.push({ level: "error", where, msg: `remove: no part "${rid}"` });
    parts = parts.filter((p) => p.id !== rid);
  }
  for (const [path, value] of Object.entries(v.set ?? {})) {
    const [pid, ...rest] = path.split(".");
    const part = parts.find((p) => p.id === pid) as Record<string, unknown> | undefined;
    if (!part) {
      issues.push({
        level: "error",
        where,
        msg: `set "${path}": no part "${pid}"`,
        ...{},
      });
      continue;
    }
    if (rest.length === 0) {
      issues.push({ level: "error", where, msg: `set "${path}": missing property path` });
      continue;
    }
    let target: Record<string, unknown> = part;
    for (const key of rest.slice(0, -1)) {
      if (typeof target[key] !== "object" || target[key] === null) target[key] = {};
      target = target[key] as Record<string, unknown>;
    }
    target[rest[rest.length - 1]] = structuredClone(value);
    const check = PartSchema.safeParse(part);
    if (!check.success)
      issues.push({
        level: "error",
        where,
        msg: `set "${path}" made part "${pid}" invalid: ${check.error.issues[0]?.message}`,
      });
  }
  for (const added of v.add ?? []) {
    if (parts.some((p) => p.id === added.id))
      issues.push({ level: "error", where, msg: `add: duplicate part id "${added.id}"` });
    parts.push(structuredClone(added));
  }
  return { ...base, parts, seed: base.seed };
}

// ---------------------------------------------------------------- shapes

function fmt(n: number): string {
  const r = Math.round(n * 100) / 100;
  return Object.is(r, -0) ? "0" : String(r);
}

function polyPoints(pts: [number, number][]): string {
  return pts.map(([x, y]) => `${fmt(x)},${fmt(y)}`).join(" ");
}

function ngonPts(sides: number, r: number, rot = 0): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < sides; i++) {
    const a = ((-90 + rot + (360 / sides) * i) * Math.PI) / 180;
    out.push([r * Math.cos(a), r * Math.sin(a)]);
  }
  return out;
}

function starPts(points: number, r: number, r2: number, rot = 0): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < points * 2; i++) {
    const rad = i % 2 === 0 ? r : r2;
    const a = ((-90 + rot + (180 / points) * i) * Math.PI) / 180;
    out.push([rad * Math.cos(a), rad * Math.sin(a)]);
  }
  return out;
}

function arcPoint(r: number, deg: number): [number, number] {
  const a = (deg * Math.PI) / 180;
  return [r * Math.cos(a), r * Math.sin(a)];
}

/** Emit one shape element. `paintAttrs` carries fill/stroke attributes. */
function shapeEl(shape: Shape, paintAttrs: string): string {
  switch (shape.kind) {
    case "circle":
      return `<circle r="${fmt(shape.r)}"${paintAttrs}/>`;
    case "ellipse":
      return `<ellipse rx="${fmt(shape.rx)}" ry="${fmt(shape.ry)}"${paintAttrs}/>`;
    case "rect": {
      const rx = shape.corner ? ` rx="${fmt(shape.corner)}"` : "";
      return `<rect x="${fmt(-shape.w / 2)}" y="${fmt(-shape.h / 2)}" width="${fmt(shape.w)}" height="${fmt(shape.h)}"${rx}${paintAttrs}/>`;
    }
    case "ngon":
      return `<polygon points="${polyPoints(ngonPts(shape.sides, shape.r, shape.rot))}"${paintAttrs}/>`;
    case "star":
      return `<polygon points="${polyPoints(starPts(shape.points, shape.r, shape.r2, shape.rot))}"${paintAttrs}/>`;
    case "poly":
      return `<polygon points="${polyPoints(shape.points)}"${paintAttrs}/>`;
    case "wedge": {
      const [x1, y1] = arcPoint(shape.r, shape.from);
      const [x2, y2] = arcPoint(shape.r, shape.to);
      const large = Math.abs(shape.to - shape.from) > 180 ? 1 : 0;
      return `<path d="M0,0 L${fmt(x1)},${fmt(y1)} A${fmt(shape.r)},${fmt(shape.r)} 0 ${large} 1 ${fmt(x2)},${fmt(y2)} Z"${paintAttrs}/>`;
    }
    case "ring":
      throw new Error("ring is handled by ringEl");
  }
}

// ---------------------------------------------------------------- renderer

interface Ctx {
  reg: Registry;
  issues: Issue[];
  defs: string[];
  uid: string;
  animated: Set<string>; // part ids wrapped for animation
  useStack: string[];
}

function paintValue(paint: Paint, ctx: Ctx, where: string, gradId: string): string {
  if (typeof paint === "string") {
    const r = resolveColor(paint, ctx.reg.tokens);
    if (!r.ok) {
      ctx.issues.push({
        level: "error",
        where,
        msg: r.error + (r.suggestions ? ` — did you mean ${r.suggestions.join(", ")}?` : ""),
      });
      return FALLBACK;
    }
    if (r.warn) ctx.issues.push({ level: "warn", where, msg: r.warn });
    return r.value;
  }
  return gradientDef(paint, ctx, where, gradId);
}

function gradientDef(g: Gradient, ctx: Ctx, where: string, gradId: string): string {
  const stops = g.stops
    .map(([off, ref]) => {
      const c = paintValue(ref, ctx, `${where} gradient stop`, gradId);
      return `<stop offset="${fmt(off * 100)}%" stop-color="${c}"/>`;
    })
    .join("");
  if (g.gradient === "linear") {
    const [x1, y1] = g.from ?? [0.5, 0];
    const [x2, y2] = g.to ?? [0.5, 1];
    ctx.defs.push(`<linearGradient id="${gradId}" x1="${fmt(x1)}" y1="${fmt(y1)}" x2="${fmt(x2)}" y2="${fmt(y2)}">${stops}</linearGradient>`);
  } else {
    const [cx, cy] = g.from ?? [0.5, 0.5];
    ctx.defs.push(`<radialGradient id="${gradId}" cx="${fmt(cx)}" cy="${fmt(cy)}" r="0.5">${stops}</radialGradient>`);
  }
  return `url(#${gradId})`;
}

function paintAttrs(part: ShapePart | RepeatPart, ctx: Ctx, where: string): string {
  let s = "";
  s += part.fill !== undefined ? ` fill="${paintValue(part.fill, ctx, where, `g-${ctx.uid}-${part.id}`)}"` : ` fill="none"`;
  if (part.stroke) {
    const c = paintValue(part.stroke.color, ctx, `${where} stroke`, `gs-${ctx.uid}-${part.id}`);
    const w = resolveNumber(part.stroke.width, ctx.reg.tokens.strokes, "stroke");
    if (!w.ok) {
      ctx.issues.push({ level: "error", where, msg: w.error + (w.suggestions ? ` — did you mean ${w.suggestions.join(", ")}?` : "") });
    }
    s += ` stroke="${c}" stroke-width="${fmt(w.ok ? w.value : 1)}"`;
  }
  return s;
}

function ringEl(part: ShapePart, ctx: Ctx, where: string): string {
  const shape = part.shape as Extract<Shape, { kind: "ring" }>;
  const color = part.fill !== undefined ? paintValue(part.fill, ctx, where, `g-${ctx.uid}-${part.id}`) : FALLBACK;
  if (part.fill === undefined)
    ctx.issues.push({ level: "error", where, msg: "ring needs `fill` (used as its stroke color)" });
  const attrs = ` fill="none" stroke="${color}" stroke-width="${fmt(shape.width)}"`;
  if (shape.from === undefined && shape.to === undefined) return `<circle r="${fmt(shape.r)}"${attrs}/>`;
  const from = shape.from ?? 0;
  const to = shape.to ?? 360;
  const [x1, y1] = arcPoint(shape.r, from);
  const [x2, y2] = arcPoint(shape.r, to);
  const large = Math.abs(to - from) > 180 ? 1 : 0;
  return `<path d="M${fmt(x1)},${fmt(y1)} A${fmt(shape.r)},${fmt(shape.r)} 0 ${large} 1 ${fmt(x2)},${fmt(y2)}"${attrs}/>`;
}

/**
 * A part's static transform, split where an animation has to be inserted.
 *
 * `place` is where the part sits in its parent; `pose` is how it is turned and
 * sized about that point. They come apart because an animated offset has to
 * land between them: the engine adapters move a part by adding to its position
 * in the *parent's* frame and rotate it about its own, and an animation class
 * sitting inside the whole transform would instead translate along the part's
 * own rotated axes. A head at -33 degrees and a mouth at 0 would then set off
 * in different directions from the same `x` track — which is a body coming
 * apart in the gallery and holding together in the game.
 */
function partTransform(part: Part): { place: string; pose: string } {
  const [x, y] = part.at ?? [0, 0];
  const t: string[] = [];
  if (part.rot) t.push(`rotate(${fmt(part.rot)})`);
  if (part.scale !== undefined) {
    const [sx, sy] = typeof part.scale === "number" ? [part.scale, part.scale] : part.scale;
    t.push(`scale(${fmt(sx)},${fmt(sy)})`);
  }
  return {
    place: x !== 0 || y !== 0 ? ` transform="translate(${fmt(x)},${fmt(y)})"` : "",
    pose: t.length ? ` transform="${t.join(" ")}"` : "",
  };
}

function renderPartContent(part: Part, ctx: Ctx, where: string, owner: Asset): string {
  if ("use" in part) return renderUse(part, ctx, where);
  if ("repeat" in part) return renderRepeat(part, ctx, where, owner.id);
  if (part.shape.kind === "ring") return ringEl(part, ctx, where);
  return shapeEl(part.shape, paintAttrs(part, ctx, where));
}

function renderUse(part: UsePart, ctx: Ctx, where: string): string {
  const target = ctx.reg.assets.get(part.use);
  if (!target) {
    ctx.issues.push({
      level: "error",
      where,
      msg: `use: unknown asset "${part.use}" — did you mean ${suggest(part.use, [...ctx.reg.assets.keys()]).join(", ")}?`,
    });
    return "";
  }
  if (ctx.useStack.includes(part.use) || ctx.useStack.length >= 4) {
    ctx.issues.push({ level: "error", where, msg: `use: cycle or depth > 4 via "${part.use}"` });
    return "";
  }
  const resolved = part.variant ? applyVariant(target, part.variant, ctx.issues) : target;
  const vScale = part.variant ? (target.variants?.[part.variant]?.scale ?? 1) : 1;
  ctx.useStack.push(part.use);
  const inner = resolved.parts.map((p, i) => renderPart(p, ctx, `${part.use}[${i}]`, resolved)).join("");
  ctx.useStack.pop();
  return vScale === 1 ? `<g>${inner}</g>` : `<g transform="scale(${fmt(vScale)})">${inner}</g>`;
}

function renderRepeat(part: RepeatPart, ctx: Ctx, where: string, ownerId: string): string {
  const { of, count, area, seed, jitterRot, scaleRange } = part.repeat;
  const rng = mulberry32(seed ?? hashSeed(`${ownerId}:${part.id}`));
  const [aw, ah] = area;
  const attrs = paintAttrs(part, ctx, where);
  let out = "";
  for (let i = 0; i < count; i++) {
    const x = (rng() - 0.5) * aw;
    const y = (rng() - 0.5) * ah;
    const r = jitterRot ? Math.round(rng() * 360) : 0;
    const s = scaleRange ? scaleRange[0] + rng() * (scaleRange[1] - scaleRange[0]) : 1;
    const t: string[] = [`translate(${fmt(x)},${fmt(y)})`];
    if (r) t.push(`rotate(${r})`);
    if (s !== 1) t.push(`scale(${fmt(s)})`);
    out += `<g transform="${t.join(" ")}">${shapeEl(of, attrs)}</g>`;
  }
  return out;
}

function renderPart(part: Part, ctx: Ctx, where: string, owner: Asset): string {
  let content = renderPartContent(part, ctx, where, owner);
  const { place, pose } = partTransform(part);
  // Turned and sized first, then offset by the animation, then placed: the
  // order the adapters pose a node in. Uniform scale commutes with rotation, so
  // an animated scale reads the same on either side of the static one.
  let body = pose ? `<g${pose}>${content}</g>` : content;
  if (ctx.animated.has(part.id) && ctx.useStack.length === 0)
    body = `<g class="aw-${ctx.uid}-${part.id}">${body}</g>`;
  let attrs = place;
  if (part.opacity !== undefined) {
    const o = resolveNumber(part.opacity, ctx.reg.tokens.alpha, "alpha");
    if (!o.ok) ctx.issues.push({ level: "error", where, msg: o.error });
    attrs += ` opacity="${fmt(o.ok ? o.value : 1)}"`;
  }
  const el = `<g${attrs}>${body}</g>`;
  if (part.mirrorX) return `${el}<g transform="scale(-1,1)"><g${attrs}>${body}</g></g>`;
  return el;
}

// ---------------------------------------------------------------- animation

const EASE: Record<string, string> = {
  linear: "linear",
  sine: "ease-in-out",
  backOut: "cubic-bezier(0.34,1.56,0.64,1)",
};

/**
 * The same easing the engine adapters use, so a value sampled here and a value
 * posed there agree. Only needed when one part carries tracks that do not share
 * a timeline — see animCss.
 */
const EASE_FN: Record<string, (t: number) => number> = {
  linear: (t) => t,
  sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * t),
  backOut: (t) => {
    const c = 1.70158;
    const u = t - 1;
    return 1 + (c + 1) * u * u * u + c * u * u;
  },
};

/** A track's value at an arbitrary time, interpolated with its own ease. */
function valueAt(tr: Anim["tracks"][number], t: number): number {
  const keys = tr.keys;
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1] = keys[i];
    const [t0, v0] = keys[i - 1];
    if (t <= t1) {
      const span = t1 - t0;
      if (span <= 0) return v1;
      return v0 + (v1 - v0) * EASE_FN[tr.ease ?? "sine"]((t - t0) / span);
    }
  }
  return keys[keys.length - 1][1];
}

function animCss(anim: Anim, animName: string, ctx: Ctx, where: string, parts: Part[]): string {
  let css = "";
  const perPart = new Map<string, typeof anim.tracks>();
  for (const tr of anim.tracks) {
    if (!parts.some((p) => p.id === tr.part)) {
      ctx.issues.push({ level: "error", where, msg: `animation "${animName}": no part "${tr.part}"` });
      continue;
    }
    const list = perPart.get(tr.part) ?? [];
    list.push(tr);
    perPart.set(tr.part, list);
  }
  for (const [pid, tracks] of perPart) {
    // A part may animate several properties at once; it may not animate the
    // same one twice, which is the collision the one-track-per-part rule was
    // really protecting against.
    const byProp = new Map<string, (typeof tracks)[number]>();
    for (const tr of tracks) {
      if (byProp.has(tr.prop)) {
        ctx.issues.push({
          level: "error",
          where,
          msg: `animation "${animName}": part "${pid}" animates "${tr.prop}" more than once`,
        });
        continue;
      }
      byProp.set(tr.prop, tr);
    }
    ctx.animated.add(pid);
    const x = byProp.get("x");
    const y = byProp.get("y");
    const rot = byProp.get("rot");
    const scale = byProp.get("scale");
    const opacity = byProp.get("opacity");

    // CSS gives one transform and one timing function per rule, so several
    // tracks have to become one timeline. Sample every key time any of them
    // states, and read each track at those times through its own ease.
    const times = [...new Set(tracks.flatMap((tr) => tr.keys.map((k) => k[0])))].sort((a, b) => a - b);
    const kf = times
      .map((t) => {
        const tf: string[] = [];
        if (x || y) tf.push(`translate(${fmt(x ? valueAt(x, t) : 0)}px, ${fmt(y ? valueAt(y, t) : 0)}px)`);
        if (rot) tf.push(`rotate(${fmt(valueAt(rot, t))}deg)`);
        if (scale) tf.push(`scale(${fmt(valueAt(scale, t))})`);
        const decls: string[] = [];
        if (tf.length) decls.push(`transform: ${tf.join(" ")}`);
        if (opacity) decls.push(`opacity: ${fmt(valueAt(opacity, t))}`);
        return `${fmt(t * 100)}% { ${decls.join("; ")} }`;
      })
      .join(" ");

    // Whose ease the rule runs on. One track, or several agreeing on both ease
    // and key times, and the browser re-eases between the same points the
    // author stated — identical to what a single track used to emit. Anything
    // else is already sampled with each track's own ease above, so the rule
    // goes linear between those samples rather than easing them twice.
    const first = tracks[0];
    const uniform =
      tracks.every((tr) => (tr.ease ?? "sine") === (first.ease ?? "sine")) &&
      tracks.every((tr) => tr.keys.length === times.length);
    const timing = uniform ? EASE[first.ease ?? "sine"] : EASE.linear;
    css += `@keyframes kf-${ctx.uid}-${pid} { ${kf} } .aw-${ctx.uid}-${pid} { animation: kf-${ctx.uid}-${pid} ${fmt(anim.duration)}s ${timing} infinite; }\n`;
  }
  return css;
}

// ---------------------------------------------------------------- entry

export function renderSVG(
  assetIn: Asset,
  reg: Registry,
  opts: RenderOptions = {},
): { svg: string; issues: Issue[] } {
  const issues: Issue[] = [];
  const asset = opts.variant ? applyVariant(assetIn, opts.variant, issues) : assetIn;
  const uid = opts.uid ?? asset.id.replace(/\./g, "-") + (opts.variant ? `--${opts.variant}` : "");
  const ctx: Ctx = { reg, issues, defs: [], uid, animated: new Set(), useStack: [] };

  const where = opts.variant ? `${asset.id}#${opts.variant}` : asset.id;
  let css = "";
  if (opts.animation) {
    const anim = asset.animations?.[opts.animation];
    if (!anim) issues.push({ level: "error", where, msg: `unknown animation "${opts.animation}"` });
    else css = animCss(anim, opts.animation, ctx, where, asset.parts);
  }

  const dup = new Set<string>();
  for (const p of asset.parts) {
    if (dup.has(p.id)) issues.push({ level: "error", where, msg: `duplicate part id "${p.id}"` });
    dup.add(p.id);
  }

  const body = asset.parts.map((p, i) => renderPart(p, ctx, `${where}.parts[${i}](${p.id})`, asset)).join("\n    ");

  const [w, h] = asset.size;
  const [ax, ay] = asset.anchor ?? [0.5, 0.5];
  const ds = opts.displayScale ?? 1;
  const variantScale = opts.variant ? (assetIn.variants?.[opts.variant]?.scale ?? 1) : 1;
  const scaleWrap = variantScale !== 1;
  // a scaled variant gets a proportionally larger canvas so nothing clips
  const vw = w * variantScale;
  const vh = h * variantScale;

  const svg = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${fmt(-vw * ax)} ${fmt(-vh * ay)} ${fmt(vw)} ${fmt(vh)}" width="${fmt(vw * ds)}" height="${fmt(vh * ds)}">`,
    css ? `  <style>${css}</style>` : "",
    ctx.defs.length ? `  <defs>${ctx.defs.join("")}</defs>` : "",
    `  <g style="paint-order:stroke" stroke-linejoin="round" stroke-linecap="round">`,
    scaleWrap ? `  <g transform="scale(${fmt(variantScale)})">` : "",
    `    ${body}`,
    scaleWrap ? `  </g>` : "",
    `  </g>`,
    `</svg>`,
  ]
    .filter(Boolean)
    .join("\n");

  return { svg, issues };
}

// ---------------------------------------------------------------- derived meta

function shapeRadius(s: Shape): number {
  switch (s.kind) {
    case "circle": return s.r;
    case "ellipse": return Math.max(s.rx, s.ry);
    case "rect": return Math.hypot(s.w, s.h) / 2;
    case "ngon": return s.r;
    case "star": return s.r;
    case "poly": return Math.max(...s.points.map(([x, y]) => Math.hypot(x, y)));
    case "ring": return s.r + s.width / 2;
    case "wedge": return s.r;
  }
}

/** Conservative bounding radius from the anchor — sim-facing, approximate. */
export function derivedRadius(asset: Asset, reg: Registry, depth = 0): number {
  let max = 0;
  for (const part of asset.parts) {
    const [x, y] = part.at ?? [0, 0];
    const dist = Math.hypot(x, y);
    const s = typeof part.scale === "number" ? part.scale : part.scale ? Math.max(...part.scale) : 1;
    let local = 0;
    if ("shape" in part) local = shapeRadius(part.shape);
    else if ("repeat" in part) local = Math.hypot(...part.repeat.area) / 2 + shapeRadius(part.repeat.of);
    else if ("use" in part && depth < 4) {
      const t = reg.assets.get(part.use);
      if (t) local = derivedRadius(t, reg, depth + 1);
    }
    max = Math.max(max, dist + local * s);
  }
  return Math.round(max * 10) / 10;
}
