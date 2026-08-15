/** Bake every ported Shape Survivors IR through the Phaser adapter (mock scene). */
import { readFileSync, readdirSync } from "node:fs";
import { bakeFlat, buildRig, type IRAsset, type SceneLike } from "../adapters/phaser/polygraphics-phaser.js";

const dir = new URL("../out/compiled/", import.meta.url);
const mock = (): SceneLike => ({
  add: {
    graphics: () => ({ fillStyle() {}, lineStyle() {}, fillPoints() {}, strokePoints() {}, generateTexture() {}, destroy() {} }),
    image: (x, y) => ({ x, y, rotation: 0, alpha: 1, setOrigin() { return this; }, setScale() { return this; } }),
    container: () => ({ add() {} }),
  },
});

let n = 0, fail = 0;
for (const f of readdirSync(dir).filter((f) => f.startsWith("ss-") && f.endsWith(".json"))) {
  const ir: IRAsset = JSON.parse(readFileSync(new URL(f, dir), "utf8"));
  try {
    bakeFlat(mock(), ir);
    for (const v of Object.keys(ir.variants)) bakeFlat(mock(), ir, { variant: v });
    buildRig(mock(), ir);
    n++;
  } catch (e) {
    fail++;
    console.log("FAIL", f, (e as Error).message);
  }
}
console.log(`${n} SS assets bake+rig through the Phaser adapter, ${fail} failures`);
process.exit(fail ? 1 : 0);
