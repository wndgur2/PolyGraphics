/**
 * The clip model: eases, squash, tint, cues and sockets, read the same way by
 * the renderer (src/anim.ts) and the Phaser adapter (its own copy, since it is
 * one drop-in file).
 *
 * The parity check is the reason this exists. The eases used to be written five
 * times and one copy had drifted; now there are two, and this samples every
 * ease and every track of every compiled document through both and fails on the
 * first value that differs.
 *
 * Run: npx tsx scripts/test-anim.ts   (after `npm run compile` or `npm run check`)
 */
import { readdirSync, readFileSync } from "node:fs";
import { EASE_FN, poseAsset, trackValue, type EaseName } from "../src/anim.js";
import { compileAsset } from "../src/compile.js";
import { renderSVG } from "../src/render.js";
import { loadLibrary, ownerOf } from "../src/apps.js";
import type { Asset } from "../src/schema.js";
import { AssetSchema } from "../src/schema.js";
import {
  buildRig, cueFrame, cueTime, poseNodes, socketAt, trackValue as adapterValue,
  type IRAsset, type ImageLike, type SceneLike,
} from "../adapters/phaser/polygraphics-phaser.js";

let failures = 0;
function check(name: string, cond: boolean, detail = ""): void {
  console.log(`${cond ? "✓" : "✖"} ${name}${cond || !detail ? "" : ` — ${detail}`}`);
  if (!cond) failures++;
}
const near = (a: number, b: number, eps = 1e-9) => Math.abs(a - b) <= eps;

// ---------------- parity: every compiled track, both readers
{
  const dir = new URL("../out/compiled/", import.meta.url);
  let tracks = 0;
  let worst = "";
  for (const f of readdirSync(dir).filter((n) => n.endsWith(".json"))) {
    const ir = JSON.parse(readFileSync(new URL(f, dir), "utf8")) as IRAsset;
    for (const [name, anim] of Object.entries(ir.animations ?? {}))
      for (const tr of anim.tracks) {
        tracks++;
        for (let i = 0; i <= 64 && !worst; i++) {
          const t = i / 64;
          const a = trackValue(tr as never, t);
          const b = adapterValue(tr, t);
          if (!near(a, b)) worst = `${ir.id} ${name} ${tr.part}.${tr.prop} @${t}: ${a} vs ${b}`;
        }
      }
  }
  check(`renderer and adapter read all ${tracks} library tracks identically`, tracks > 1000 && !worst, worst);

  const names = Object.keys(EASE_FN) as EaseName[];
  let bad = "";
  for (const e of names)
    for (let i = 0; i <= 100; i++) {
      const tr = { part: "p", prop: "x" as const, keys: [[0, 0], [1, 1]] as [number, number][], ease: e };
      const a = trackValue(tr, i / 100);
      const b = adapterValue(tr, i / 100);
      if (!near(a, b)) bad ||= `${e} @${i / 100}`;
    }
  check(`all ${names.length} eases agree between the two readers`, !bad, bad);
  check("every ease starts at 0 and lands on 1", names.every((e) => near(EASE_FN[e](0), 0, 1e-3) && EASE_FN[e](1) === 1));
}

// ---------------- per-key ease and hold
{
  const tr = {
    part: "p",
    prop: "y" as const,
    keys: [[0, 0, "hold"], [0.5, 10], [1, 20, "linear"]] as never,
    ease: "linear" as const,
  };
  check("hold keeps the value until the next key", trackValue(tr, 0.49) === 0 && trackValue(tr, 0.5) === 10);
  check("a key without an ease uses the track's", near(trackValue(tr, 0.75), 15));
  const tr2 = { part: "p", prop: "y" as const, keys: [[0, 0, "quadIn"], [1, 1]] as never };
  check("a key's ease shapes the segment leaving it", near(trackValue(tr2, 0.5), 0.25));
}

// ---------------- a test body through compile, renderer and adapter
const lib = loadLibrary();
const owner = ownerOf(lib, "ss.char.arin")!;
const doc: Asset = AssetSchema.parse({
  id: "ss.test.squash",
  name: "Squash test",
  description: "A body with a squash, a tint, cues and sockets — test-anim.ts only.",
  tags: ["test"],
  size: [32, 32],
  parts: [
    { id: "body", shape: { kind: "rect", w: 10, h: 10 }, fill: "$steel", at: [0, 4] },
    { id: "arm", shape: { kind: "rect", w: 2, h: 8 }, fill: "$steel", at: [6, 0], rot: 30 },
  ],
  skeleton: {
    joints: { hand: [6, 4], chest: [0, 0] },
    sockets: { hand: { joint: "hand", part: "arm" }, chest: { joint: "chest" } },
  },
  animations: {
    cast: {
      duration: 0.5,
      cues: { windup: 0.2, release: 0.42 },
      tracks: [
        { part: "body", prop: "scaleX", keys: [[0, 1], [0.4, 1.2, "hold"], [0.6, 0.9], [1, 1]], ease: "quadOut" },
        { part: "body", prop: "scaleY", keys: [[0, 1], [0.4, 0.8], [1, 1]] },
        { part: "body", prop: "tint", to: "$bone", keys: [[0, 0], [0.42, 1, "hold"], [0.5, 0], [1, 0]] },
        { part: "arm", prop: "y", keys: [[0, 0], [0.5, -4], [1, 0]] },
      ],
    },
    bad: {
      duration: 0.5,
      tracks: [
        { part: "body", prop: "scale", keys: [[0, 1], [1, 2]] },
        { part: "body", prop: "scaleX", keys: [[0, 1], [1, 2]] },
        { part: "arm", prop: "tint", keys: [[0, 0], [1, 1]] },
      ],
    },
  },
});
const reg = { ...owner.reg, assets: new Map([...owner.reg.assets, [doc.id, doc]]) };

{
  const { svg, issues } = renderSVG(doc, reg, { animation: "cast" });
  check("a squash, a tint and cues render without issues", issues.length === 0, JSON.stringify(issues));
  check("the squash goes inside the part's own turn", svg.includes('class="as-ss-test-squash-body"'));
  check("the tint is a flooded silhouette over the part", svg.includes("feFlood") && svg.includes('class="tw-ss-test-squash-body"'));
  const bad = renderSVG(doc, reg, { animation: "bad" }).issues.map((i) => i.msg).join(" | ");
  check("scale and a squash on one part is an error", bad.includes('animates "scale" and a squash'));
  check("a tint with no colour is an error", bad.includes('has no "to" colour'));

  const plain = renderSVG(doc, reg, {}).svg;
  const posed = poseAsset(doc, doc.animations!.cast, 0.42, reg.tokens.alpha);
  const still = renderSVG(posed.asset, reg, { tints: posed.tints }).svg;
  check("a posed frame carries its tint to the still render", posed.tints.body?.amount === 1 && still.includes("feFlood") && !plain.includes("feFlood"));
}

{
  const { ir, issues } = compileAsset(doc, reg);
  check("compiles", issues.filter((i) => i.level === "error").length === 0, JSON.stringify(issues));
  const tint = ir.animations.cast.tracks.find((t) => t.prop === "tint")!;
  check("a tint's colour is resolved in the IR", Array.isArray(tint.to) && tint.to.length === 4);
  check("sockets reach the IR", ir.sockets?.hand?.part === "arm" && ir.sockets?.chest?.at[0] === 0);

  const pir = ir as unknown as IRAsset;
  check("cueTime is seconds into the clip", near(cueTime(pir, "cast", "release")!, 0.21));
  check("cueFrame is the first frame past the cue", cueFrame(0.42, 10) === 5 && cueFrame(0.4, 10) === 4 && cueFrame(0.99, 10) === 9);

  const rest = socketAt(pir, "hand")!;
  const up = socketAt(pir, "hand", { animation: "cast", progress: 0.5 })!;
  check("a socket rests at its joint", near(rest.x, 6) && near(rest.y, 4));
  check("a socket rides its part through the clip", near(up.x, 6) && near(up.y, 0), JSON.stringify(up));
  check("a socket on no part stays put", near(socketAt(pir, "chest", { animation: "cast", progress: 0.5 })!.y, 0));

  const at = poseNodes(pir.nodes, pir.animations.cast, 0.42);
  const body = at.find((n) => n.id === "body")!;
  check("poseNodes squashes along the node's axes", near(body.scale[0], 1.2) && body.scale[1] < 1, JSON.stringify(body.scale));
  const fill = (body.draws[0] as { fill: number[] }).fill;
  const bone = tint.to!;
  check("poseNodes mixes a tinted node to the tint colour", fill.slice(0, 3).every((c, i) => near(c, bone[i], 1e-6)));

  // rig: a squash and a tint cover, from a mock scene
  const images: (ImageLike & { key: string; scaleX: number; scaleY: number; tint?: number })[] = [];
  const scene: SceneLike = {
    add: {
      graphics: () => ({ fillStyle() {}, lineStyle() {}, fillPoints() {}, strokePoints() {}, generateTexture() {}, destroy() {} }),
      image: (x, y, key) => {
        const img = {
          key, x, y, rotation: 0, alpha: 1, scaleX: 1, scaleY: 1, tint: undefined as number | undefined,
          setOrigin() { return this; },
          setScale(sx: number, sy: number) { this.scaleX = sx; this.scaleY = sy; return this; },
          setTint(c: number) { this.tint = c; return this; },
        };
        images.push(img);
        return img as never;
      },
      container: () => ({ add() {} }),
    },
  };
  const rig = buildRig(scene, pir, { resolution: 2 });
  const [img, cover] = rig.parts.get("body")!.map((h) => [h.img, h.cover])[0] as [typeof images[0], typeof images[0]];
  check("a tinted part gets a white cover", !!cover && cover.key.endsWith("~white") && cover.alpha === 0);
  rig.play("cast", { loop: false });
  rig.tick(0.21);
  check("the rig squashes the part", near(img.scaleX, 0.6) && img.scaleY < 0.5, `${img.scaleX}×${img.scaleY}`);
  check("the rig shows the cover at the tint amount", near(cover.alpha, 1) && cover.tint !== undefined);
  rig.tick(0.2);
  check("the cover goes when the tint does", near(cover.alpha, 0));
}

// ---------------- layers: a cast over a walk
{
  const base: Asset = AssetSchema.parse({
    ...doc,
    id: "ss.test.layers",
    animations: {
      walk: { duration: 1, tracks: [{ part: "arm", prop: "x", keys: [[0, 2], [1, 2]], ease: "linear" }, { part: "body", prop: "y", keys: [[0, 1], [1, 1]], ease: "linear" }] },
      cast: { duration: 0.5, cues: { release: 0.5 }, tracks: [{ part: "arm", prop: "x", keys: [[0, 10], [1, 10]], ease: "linear" }] },
    },
    skeleton: undefined,
  });
  const reg2 = { ...reg, assets: new Map([...reg.assets, [base.id, base]]) };
  const ir = compileAsset(base, reg2).ir as unknown as IRAsset;
  const imgs: Record<string, ImageLike> = {};
  const scene: SceneLike = {
    add: {
      graphics: () => ({ fillStyle() {}, lineStyle() {}, fillPoints() {}, strokePoints() {}, generateTexture() {}, destroy() {} }),
      image: (x, y, key) => (imgs[key] = { x, y, rotation: 0, alpha: 1, setOrigin() { return this; }, setScale() { return this; } } as ImageLike),
      container: () => ({ add() {} }),
    },
  };
  const rig = buildRig(scene, ir, { resolution: 1 });
  const arm = rig.parts.get("arm")![0].img;
  const body = rig.parts.get("body")![0].img;
  const restX = rig.parts.get("arm")![0].baseX;
  rig.play("walk");
  rig.tick(0.1);
  check("the base layer plays", near(arm.x, restX + 2));
  const cues: string[] = [];
  let ended = false;
  rig.play("cast", { layer: "upper", loop: false, fadeIn: 0.1, onCue: (c) => cues.push(c), onComplete: () => (ended = true) });
  rig.tick(0.05);
  check("a layer fades in over the one under it", near(arm.x, restX + 6), `${arm.x - restX}`);
  rig.tick(0.1);
  check("a higher layer takes the props it animates", near(arm.x, restX + 10));
  check("and leaves the rest to the layer under it", near(body.y, rig.parts.get("body")![0].baseY + 1));
  check("what a layer is playing", rig.playing("upper") === "cast" && rig.playing() === "walk");
  rig.tick(0.2);
  check("a cue fires as the playhead passes it", cues.join() === "release", cues.join());
  rig.tick(0.2);
  check("a one-shot layer ends and lets go", ended && rig.playing("upper") === null && near(arm.x, restX + 2), `${arm.x - restX}`);
  rig.stop();
  check("stop puts every part back to rest", near(arm.x, restX) && near(body.y, rig.parts.get("body")![0].baseY));
}

console.log(failures ? `\n${failures} FAILED` : "\nALL PASS");
process.exit(failures ? 1 : 0);
