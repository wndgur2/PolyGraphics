/**
 * Bundles the compiled IR that Feelers consumes into one JSON keyed by the
 * game's own texture keys, so the game imports a single generated file and the
 * key mapping lives in exactly one place.
 *
 *   npx tsx scripts/bundle-for-feelers.ts <dest.json>
 */
import { readFileSync, writeFileSync } from "node:fs";

const root = new URL("..", import.meta.url);
const dest = process.argv[2];
if (!dest) {
  console.error("usage: tsx scripts/bundle-for-feelers.ts <dest.json>");
  process.exit(1);
}

/** game texture key -> PolyGraphics asset id. Weapon icons also emit `<key>_evo`. */
const MAP: Record<string, string> = {
  ch_dot: "ss.char.dot",
  ch_tri: "ss.char.tri",
  ch_blok: "ss.char.blok",
  ch_hourglass: "ss.char.hourglass",
  ch_prism: "ss.char.prism",
  ch_egg: "ss.char.egg",
  ch_donut: "ss.char.donut",
  ch_hex: "ss.char.hex",

  e_imp: "ss.enemy.imp",
  e_bat: "ss.enemy.bat",
  e_zombie: "ss.enemy.zombie",
  e_skeleton: "ss.enemy.skeleton",
  e_brute: "ss.enemy.brute",
  e_boss: "ss.enemy.boss",
  e_brazier: "ss.enemy.brazier",

  gem: "ss.pickup.gem",
  food: "ss.pickup.food",
  coin: "ss.pickup.coin",
  chest: "ss.pickup.chest",

  slash: "ss.proj.slash",
  p_bolt: "ss.proj.bolt",
  p_boom: "ss.proj.boom",
  p_mine: "ss.proj.mine",
  p_drone: "ss.proj.drone",
  p_ball: "ss.proj.ball",
  p_card: "ss.proj.card",
  ring: "ss.proj.ring",
  aura: "ss.proj.aura",
  scanline: "ss.proj.scanline",

  ground: "ss.env.ground",
  menu_bg: "ss.env.menu",
  menu_antenna: "ss.env.antenna",
  t_spire: "ss.terrain.spire",
  t_boulder: "ss.terrain.boulder",
  t_fungi: "ss.terrain.fungi",
  arrow: "ss.terrain.arrow",

  i_whip: "ss.icon.whip",
  i_wand: "ss.icon.wand",
  i_boomerang: "ss.icon.boomerang",
  i_might: "ss.icon.might",
  i_magnet: "ss.icon.magnet",
};

/** Icon keys whose `evolved` variant should bake as `<key>_evo`. */
const EVO = ["i_whip", "i_wand", "i_boomerang"];

const bundle: Record<string, unknown> = {};
for (const [key, id] of Object.entries(MAP)) {
  const file = new URL(`out/compiled/${id.replace(/\./g, "-")}.json`, root);
  bundle[key] = JSON.parse(readFileSync(file, "utf8"));
}

writeFileSync(
  dest,
  JSON.stringify({ generated: "polygraphics bundle for feelers", evo: EVO, textures: bundle }, null, 0) + "\n",
);
console.log(`✓ ${Object.keys(bundle).length} textures (+${EVO.length} evolved variants) → ${dest}`);
