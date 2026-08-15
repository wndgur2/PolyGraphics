/**
 * Smoke test for the Phaser adapter: drives bakeFlat/buildRig with a recording
 * mock scene and asserts texture keys, draw streams, determinism, and animation.
 * Run: npx tsx scripts/test-phaser-adapter.ts
 */
import { readFileSync } from "node:fs";
import {
  bakeFlat, buildRig,
  type GraphicsLike, type ImageLike, type IRAsset, type SceneLike,
} from "../adapters/phaser/polygraphics-phaser.js";

const load = (f: string): IRAsset =>
  JSON.parse(readFileSync(new URL(`../out/compiled/${f}.json`, import.meta.url), "utf8"));

interface Recorded { cmds: unknown[][]; textures: Map<string, [number, number]> }

function mockScene(): { scene: SceneLike; rec: Recorded; images: (ImageLike & { key: string })[] } {
  const rec: Recorded = { cmds: [], textures: new Map() };
  const images: (ImageLike & { key: string })[] = [];
  const graphics = (): GraphicsLike => ({
    fillStyle: (c, a) => rec.cmds.push(["fillStyle", c, +(a ?? 1).toFixed(4)]),
    lineStyle: (w, c, a) => rec.cmds.push(["lineStyle", +w.toFixed(2), c, +(a ?? 1).toFixed(4)]),
    fillPoints: (p) => rec.cmds.push(["fillPoints", p.length, +p[0].x.toFixed(2), +p[0].y.toFixed(2)]),
    strokePoints: (p) => rec.cmds.push(["strokePoints", p.length]),
    generateTexture: (key, w, h) => { rec.cmds.push(["generateTexture", key, w, h]); rec.textures.set(key, [w, h]); },
    destroy: () => {},
  });
  const scene: SceneLike = {
    add: {
      graphics,
      image: (x, y, key) => {
        const img = {
          key, x, y, rotation: 0, alpha: 1, scaleX: 1, scaleY: 1, originX: 0, originY: 0,
          setOrigin(ox: number, oy: number) { this.originX = ox; this.originY = oy; return this; },
          setScale(sx: number, sy: number) { this.scaleX = sx; this.scaleY = sy; return this; },
        };
        images.push(img as never);
        return img as never;
      },
      container: () => {
        const children: unknown[] = [];
        return { children, add: (c: unknown) => children.push(c) };
      },
    },
  };
  return { scene, rec, images };
}

let failures = 0;
function check(name: string, cond: boolean, detail = ""): void {
  console.log(`${cond ? "✓" : "✖"} ${name}${cond || !detail ? "" : ` — ${detail}`}`);
  if (!cond) failures++;
}

// ---------------- bakeFlat
{
  const imp = load("enemy-imp");
  const { scene, rec } = mockScene();
  const key = bakeFlat(scene, imp);
  check("bakeFlat returns namespaced key", key === "pg:enemy.imp");
  check("bakeFlat texture is canvas-sized 32×32", String(rec.textures.get(key)) === "32,32");
  const fills = rec.cmds.filter((c) => c[0] === "fillPoints").length;
  check("bakeFlat draws every node (9 nodes → ≥9 fills)", fills >= 9, `got ${fills}`);

  const { scene: s2, rec: r2 } = mockScene();
  bakeFlat(s2, imp);
  check("bakeFlat is deterministic (identical command streams)", JSON.stringify(rec.cmds) === JSON.stringify(r2.cmds));

  const { scene: s3, rec: r3 } = mockScene();
  const ekey = bakeFlat(s3, imp, { variant: "elite" });
  const [ew, eh] = r3.textures.get(ekey)!;
  check("variant bake scales canvas (32×1.25=40)", ew === 40 && eh === 40, `got ${ew}×${eh}`);
  const eliteFills = r3.cmds.filter((c) => c[0] === "fillPoints").length;
  check("elite bake has extra part (third_eye)", eliteFills === fills + 1, `${fills} → ${eliteFills}`);
}

// ---------------- buildRig + animation
{
  const imp = load("enemy-imp");
  const { scene, images } = mockScene();
  const rig = buildRig(scene, imp);
  check("rig makes one image per IR node (9)", images.length === 9, `got ${images.length}`);
  check("rig part map has mirrored pairs", rig.parts.get("eye")!.length === 2 && rig.parts.get("horn")!.length === 2);
  const [eyeL, eyeR] = rig.parts.get("eye")!;
  check("mirrored eyes sit symmetric", eyeL.img.x === -eyeR.img.x && eyeL.img.y === eyeR.img.y, `${eyeL.img.x} vs ${eyeR.img.x}`);

  const bodyY0 = rig.parts.get("body")![0].img.y;
  rig.play("idle");
  rig.tick(0.55); // half of 1.1s duration → peak of the bob (-1)
  const bodyY1 = rig.parts.get("body")![0].img.y;
  check("idle anim moves body up at half-cycle", Math.abs(bodyY1 - (bodyY0 - 1)) < 1e-6, `y ${bodyY0} → ${bodyY1}`);

  const [tail] = rig.parts.get("tail")!;
  const rotAtPeak = tail.img.rotation;
  check("tail wag rotates (rot ≈ +10° at peak)", Math.abs(rotAtPeak - (10 * Math.PI) / 180) < 1e-6, `got ${rotAtPeak}`);
  rig.stop();
  check("stop() restores base transform", rig.parts.get("body")![0].img.y === bodyY0 && tail.img.rotation === (0 * Math.PI) / 180 + tail.baseRot);
}

// ---------------- fx one-shot
{
  const impact = load("fx-impact");
  const { scene } = mockScene();
  const rig = buildRig(scene, impact);
  let done = false;
  rig.play("play", { loop: false, onComplete: () => { done = true; } });
  rig.tick(0.5); // past 0.3s duration
  const flash = rig.parts.get("flash")![0];
  check("one-shot fx completes and fires onComplete", done);
  check("fx ends at final key (flash opacity → 0)", Math.abs(flash.img.alpha) < 1e-6, `alpha ${flash.img.alpha}`);
}

// ---------------- every compiled asset bakes without throwing
{
  const files = ["boss-hex", "char-dot", "enemy-grunt", "fx-slash", "fx-ring", "fx-burst", "fx-muzzle", "icon-boomerang", "pickup-chest", "tile-ground", "weapon-boomerang", "lib-face"];
  let ok = true;
  for (const f of files) {
    try {
      const ir = load(f);
      const { scene } = mockScene();
      bakeFlat(scene, ir);
      for (const v of Object.keys(ir.variants)) bakeFlat(scene, ir, { variant: v });
      buildRig(scene, ir);
    } catch (e) {
      ok = false;
      console.log(`  ✖ ${f}: ${(e as Error).message}`);
    }
  }
  check("all 12 remaining assets bake + rig cleanly", ok);
}

console.log(failures ? `\n${failures} FAILED` : "\nALL PASS");
process.exit(failures ? 1 : 0);
