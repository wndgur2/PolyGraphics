/**
 * Deterministic SVG renderer: interprets asset documents against a token set.
 * Same asset + same tokens + same seed → byte-identical SVG (diffable output).
 */
import type { Track } from "./anim.js";
import type { Anim, Asset, Gradient, Paint, Part, RepeatPart, Shape, ShapePart, UsePart } from "./schema.js";
import { PartSchema } from "./schema.js";
import { mulberry32, hashSeed } from "./prng.js";
import { needsSampling, trackValue, type PoseTint } from "./anim.js";
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
  skeleton?: boolean; // draw the document's skeleton over the parts (gallery / inspect use; never a bake)
  /** Still tints to lay over parts, from `poseAsset` — a posed frame's `tint` tracks. */
  tints?: Record<string, PoseTint>;
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

  // A state may name the clips it is drawn to be played with, and a name that
  // does not exist is a pairing nothing will ever draw — the sort of thing that
  // survives a rename silently and then reads as a state that forgot to move.
  for (const aname of v.animations ?? [])
    if (!base.animations?.[aname])
      issues.push({ level: "error", where, msg: `animations: no animation "${aname}"` });

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
  /** Part ids whose clip squashes them, so the scale goes inside the part's own rotation. */
  squashed: Set<string>;
  /** Part ids covered by a tint: the colour, and either a still amount or "animated". */
  tinted: Map<string, { color: string; amount: number | "animated" }>;
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
function partTransform(part: Part, split = false): { place: string; whole: string; rot?: string; scale?: string } {
  const [x, y] = part.at ?? [0, 0];
  const rot = part.rot ? `rotate(${fmt(part.rot)})` : "";
  let scale = "";
  if (part.scale !== undefined) {
    const [sx, sy] = typeof part.scale === "number" ? [part.scale, part.scale] : part.scale;
    scale = `scale(${fmt(sx)},${fmt(sy)})`;
  }
  const attr = (t: string) => (t ? ` transform="${t}"` : "");
  return {
    place: x !== 0 || y !== 0 ? ` transform="translate(${fmt(x)},${fmt(y)})"` : "",
    whole: attr([rot, scale].filter(Boolean).join(" ")),
    ...(split ? { rot: attr(rot), scale: attr(scale) } : {}),
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
  const content = renderPartContent(part, ctx, where, owner);
  const top = ctx.useStack.length === 0;
  const { place, ...pose } = partTransform(part, top && ctx.squashed.has(part.id));
  // Turned and sized first, then offset by the animation, then placed: the
  // order the adapters pose a node in. Uniform scale commutes with rotation, so
  // an animated scale reads the same on either side of the static one; a
  // squash does not, so it goes inside the part's own turn (`as-`), the way an
  // engine image stretches along its own axes.
  let inner: string;
  if (pose.scale !== undefined) {
    const sized = pose.scale ? `<g${pose.scale}>${content}</g>` : content;
    const squash = `<g class="as-${ctx.uid}-${part.id}">${sized}</g>`;
    inner = pose.rot ? `<g${pose.rot}>${squash}</g>` : squash;
  } else inner = pose.whole ? `<g${pose.whole}>${content}</g>` : content;
  const tint = top ? ctx.tinted.get(part.id) : undefined;
  if (tint) {
    // A tint is the part's silhouette in one colour, laid over it: flood the
    // colour and keep it only where the part has paint. Over an opaque part,
    // the cover at `amount` is the fill mixed that far toward the colour.
    const fid = `tint-${ctx.uid}-${part.id}`;
    ctx.defs.push(
      `<filter id="${fid}" filterUnits="userSpaceOnUse" x="-1000" y="-1000" width="2000" height="2000"><feFlood flood-color="${tint.color}"/><feComposite in2="SourceGraphic" operator="in"/></filter>`,
    );
    const cover = tint.amount === "animated" ? ` class="tw-${ctx.uid}-${part.id}"` : ` opacity="${fmt(tint.amount)}"`;
    inner += `<g filter="url(#${fid})"${cover}>${inner}</g>`;
  }
  let body = inner;
  if (ctx.animated.has(part.id) && top) body = `<g class="aw-${ctx.uid}-${part.id}">${body}</g>`;
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

const SQUASH = new Set(["scaleX", "scaleY"]);

/**
 * The times a set of tracks has to be sampled at to become one CSS timeline.
 * Tracks CSS can ease itself between their own keys need only the key times;
 * a per-key ease, or one CSS has no curve for, is sampled through each segment
 * and drawn linear between samples — a `hold` gets a sample a hair before the
 * next key, so it steps instead of sliding.
 */
function sampleTimes(tracks: Track[]): number[] {
  const set = new Set<number>(tracks.flatMap((tr) => tr.keys.map((k) => k[0])));
  for (const tr of tracks) {
    if (!needsSampling(tr)) continue;
    for (let i = 1; i < tr.keys.length; i++) {
      const t0 = tr.keys[i - 1][0];
      const t1 = tr.keys[i][0];
      if (t1 <= t0) continue;
      for (let k = 1; k < 12; k++) set.add(Math.round((t0 + ((t1 - t0) * k) / 12) * 1e4) / 1e4);
      set.add(Math.round((t1 - 1e-4) * 1e4) / 1e4);
    }
  }
  return [...set].sort((a, b) => a - b);
}

/** One @keyframes rule and its class, running on the tracks' own ease when they all agree on it. */
function cssRule(
  cls: string,
  name: string,
  tracks: Track[],
  duration: number,
  decls: (t: number) => string[],
): string {
  const times = sampleTimes(tracks);
  const kf = times.map((t) => `${fmt(t * 100)}% { ${decls(t).join("; ")} }`).join(" ");
  // Whose ease the rule runs on. One track, or several agreeing on both ease
  // and key times, and the browser re-eases between the same points the
  // author stated — identical to what a single track used to emit. Anything
  // else is already sampled with each track's own ease above, so the rule
  // goes linear between those samples rather than easing them twice.
  const first = tracks[0];
  const uniform =
    !tracks.some(needsSampling) &&
    tracks.every((tr) => (tr.ease ?? "sine") === (first.ease ?? "sine")) &&
    tracks.every((tr) => tr.keys.length === times.length);
  const timing = uniform ? EASE[first.ease ?? "sine"] : EASE.linear;
  return `@keyframes ${name} { ${kf} } .${cls} { animation: ${name} ${fmt(duration)}s ${timing} infinite; }\n`;
}

/**
 * `base` is the un-patched part list, and it is what decides whether a track
 * pointing at a missing part is a mistake.
 *
 * A track naming a part the document does not have is an error: it is a typo or
 * a rename that got away. A track naming a part a *variant* removed is not — a
 * state that takes half the body off is expected to leave some of the clip with
 * nothing to move, and that is how a Lance's release plays on its spent bow: the
 * rib and tendon tracks run, and the four barb tracks have nothing to answer to
 * because the barb is away being an enemy.
 */
function animCss(anim: Anim, animName: string, ctx: Ctx, where: string, parts: Part[], base: Part[]): string {
  let css = "";
  const perPart = new Map<string, typeof anim.tracks>();
  for (const tr of anim.tracks) {
    if (!parts.some((p) => p.id === tr.part)) {
      if (!base.some((p) => p.id === tr.part))
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
    const x = byProp.get("x");
    const y = byProp.get("y");
    const rot = byProp.get("rot");
    const scale = byProp.get("scale");
    const sx = byProp.get("scaleX");
    const sy = byProp.get("scaleY");
    const opacity = byProp.get("opacity");
    const tint = byProp.get("tint");

    // `scale` turns with the part either side of its rotation; a squash only
    // means anything along the part's own axes, so the two do not mix.
    if (scale && (sx || sy))
      ctx.issues.push({
        level: "error",
        where,
        msg: `animation "${animName}": part "${pid}" animates "scale" and a squash ("scaleX"/"scaleY") — use the squash pair alone`,
      });

    const moving = [x, y, rot, opacity, sx || sy ? undefined : scale].filter((t): t is Track => !!t);
    if (moving.length) {
      ctx.animated.add(pid);
      css += cssRule(`aw-${ctx.uid}-${pid}`, `kf-${ctx.uid}-${pid}`, moving, anim.duration, (t) => {
        const tf: string[] = [];
        if (x || y) tf.push(`translate(${fmt(x ? trackValue(x, t) : 0)}px, ${fmt(y ? trackValue(y, t) : 0)}px)`);
        if (rot) tf.push(`rotate(${fmt(trackValue(rot, t))}deg)`);
        if (scale && !(sx || sy)) tf.push(`scale(${fmt(trackValue(scale, t))})`);
        const decls: string[] = [];
        if (tf.length) decls.push(`transform: ${tf.join(" ")}`);
        if (opacity) decls.push(`opacity: ${fmt(trackValue(opacity, t))}`);
        return decls;
      });
    }
    if (sx || sy) {
      ctx.squashed.add(pid);
      const pair = [sx, sy].filter((t): t is Track => !!t);
      css += cssRule(`as-${ctx.uid}-${pid}`, `kfs-${ctx.uid}-${pid}`, pair, anim.duration, (t) => [
        `transform: scale(${fmt(sx ? trackValue(sx, t) : 1)}, ${fmt(sy ? trackValue(sy, t) : 1)})`,
      ]);
    }
    if (tint) {
      const color = tintColor(tint, ctx, `${where} animation "${animName}"`);
      if (color) {
        ctx.tinted.set(pid, { color, amount: "animated" });
        css += cssRule(`tw-${ctx.uid}-${pid}`, `kft-${ctx.uid}-${pid}`, [tint], anim.duration, (t) => [
          `opacity: ${fmt(Math.max(0, Math.min(1, trackValue(tint, t))))}`,
        ]);
      }
    }
    for (const tr of tracks)
      if (tr.to !== undefined && tr.prop !== "tint")
        ctx.issues.push({ level: "error", where, msg: `animation "${animName}": "${pid}.${tr.prop}" has a "to" colour, which only a tint track reads` });
  }
  if (anim.cues)
    for (const [name, t] of Object.entries(anim.cues))
      if (t >= 1)
        ctx.issues.push({
          level: "warn",
          where,
          msg: `animation "${animName}": cue "${name}" sits at t=1, which is the clip's first frame again — put it at the moment itself`,
        });
  return css;
}

/** A tint track's colour, resolved, or an issue saying why not. */
function tintColor(tr: Track, ctx: Ctx, where: string): string | undefined {
  if (tr.to === undefined) {
    ctx.issues.push({ level: "error", where, msg: `"${tr.part}.tint" has no "to" colour to tint toward` });
    return undefined;
  }
  const c = resolveColor(tr.to, ctx.reg.tokens);
  if (!c.ok) {
    ctx.issues.push({ level: "error", where, msg: `"${tr.part}.tint" to: ${c.error}` });
    return undefined;
  }
  return c.value;
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
  const ctx: Ctx = { reg, issues, defs: [], uid, animated: new Set(), squashed: new Set(), tinted: new Map(), useStack: [] };
  for (const [pid, tint] of Object.entries(opts.tints ?? {})) {
    const c = resolveColor(tint.color, reg.tokens);
    if (c.ok) ctx.tinted.set(pid, { color: c.value, amount: tint.amount });
    else issues.push({ level: "error", where: asset.id, msg: `tint on "${pid}": ${c.error}` });
  }

  const where = opts.variant ? `${asset.id}#${opts.variant}` : asset.id;
  let css = "";
  if (opts.animation) {
    const anim = asset.animations?.[opts.animation];
    if (!anim) issues.push({ level: "error", where, msg: `unknown animation "${opts.animation}"` });
    else css = animCss(anim, opts.animation, ctx, where, asset.parts, assetIn.parts);
  }

  const dup = new Set<string>();
  for (const p of asset.parts) {
    if (dup.has(p.id)) issues.push({ level: "error", where, msg: `duplicate part id "${p.id}"` });
    dup.add(p.id);
  }

  const body = asset.parts.map((p, i) => renderPart(p, ctx, `${where}.parts[${i}](${p.id})`, asset)).join("\n    ");

  // The skeleton is checked whenever the document is rendered and drawn only
  // when asked: a bone naming a joint that is not there is a rig that drifted
  // from its own scaffold, which is the thing this block exists to catch.
  let bones = "";
  if (asset.skeleton) {
    const j = asset.skeleton.joints;
    for (const [a, b] of asset.skeleton.bones ?? [])
      for (const n of [a, b]) if (!j[n]) issues.push({ level: "error", where, msg: `skeleton: bone names no joint "${n}"` });
    for (const [name, sock] of Object.entries(asset.skeleton.sockets ?? {})) {
      if (!j[sock.joint]) issues.push({ level: "error", where, msg: `skeleton: socket "${name}" names no joint "${sock.joint}"` });
      if (sock.part && !assetIn.parts.some((p) => p.id === sock.part))
        issues.push({ level: "error", where, msg: `skeleton: socket "${name}" rides no part "${sock.part}"` });
    }
    if (opts.skeleton) bones = skeletonOverlay(asset.skeleton, uid);
  }

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
    bones,
    `</svg>`,
  ]
    .filter(Boolean)
    .join("\n");

  return { svg, issues };
}

// ---------------------------------------------------------------- skeleton overlay

/**
 * Joints as dots, bones as lines, every joint named — in the asset's own
 * coordinates, over the drawing. Deliberately not in the palette: this is
 * scaffolding to judge a pose by, not art, and it must read on any fill.
 */
function skeletonOverlay(sk: NonNullable<Asset["skeleton"]>, uid: string): string {
  const J = sk.joints;
  const lines = (sk.bones ?? [])
    .filter(([a, b]) => J[a] && J[b])
    .map(([a, b]) => `<line x1="${fmt(J[a][0])}" y1="${fmt(J[a][1])}" x2="${fmt(J[b][0])}" y2="${fmt(J[b][1])}"/>`);
  const dots = Object.entries(J).map(([n, [x, y]]) => `<circle cx="${fmt(x)}" cy="${fmt(y)}" r="0.55"><title>${n}</title></circle>`);
  // A label sits on the side of the picture its joint is on, so the names of
  // the near side and the far side fan out instead of piling into the middle;
  // joints that share a column are stepped down by their order in the table.
  const seen = new Map<string, number>();
  const labels = Object.entries(J).map(([n, [x, y]]) => {
    const col = fmt(Math.round(x / 3));
    const k = seen.get(col) ?? 0;
    seen.set(col, k + 1);
    const right = x >= 0;
    return `<text x="${fmt(x + (right ? 0.9 : -0.9))}" y="${fmt(y - 0.5 + k * 0.4)}" text-anchor="${right ? "start" : "end"}">${n}</text>`;
  });
  return [
    `  <g class="skeleton" id="${uid}-skeleton" fill="none" stroke="#ff3fa0" stroke-width="0.3" stroke-linecap="round" opacity="0.95">`,
    `    ${lines.join("")}`,
    `    <g fill="#ff3fa0" stroke="none">${dots.join("")}</g>`,
    `    <g fill="#ffffff" stroke="#000000" stroke-width="0.22" paint-order="stroke" font-family="ui-monospace, monospace" font-size="1.15">${labels.join("")}</g>`,
    `  </g>`,
  ].join("\n");
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
