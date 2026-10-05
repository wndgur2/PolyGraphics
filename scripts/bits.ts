/**
 * The small-things loop (docs/small-things.md): run a spec script that writes
 * specimen cards, draw every card at several scales side by side, one PNG.
 *
 *   npx tsx scripts/bits.ts scripts/bits_metal_spec.py            # → out/bits/bits_metal_spec.png
 *   npx tsx scripts/bits.ts my_spec.py --scales 1.2,2.4,8 --out /tmp/metal.png
 *   npx tsx scripts/bits.ts --json some/dir                        # cards already written
 *
 * The spec is run as `python3 <spec.py> <dir>` and writes `ss.bits.*` cards
 * there with `specimen.card()`. Each card is validated and drawn against the
 * ss app's tokens and documents (so a card may `use` a real one), then laid
 * out at every scale on the app's soil colour.
 *
 * The scales are the point. A camp prop is seen at about 2.4 device pixels
 * per unit on a hi-DPI desktop (feelers' WORLD_ZOOM 1.2 × DPR 2) and 1.2 on a
 * plain one, so those two say whether a thing still *reads*; 8 says whether it
 * is *made* — whether a shackle goes into its lock, whether a chain's links
 * interlock. A thing has to pass all three.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { Resvg } from "@resvg/resvg-js";
import { AssetSchema, type Asset } from "../src/schema.js";
import { renderSVG } from "../src/render.js";
import { loadLibrary } from "../src/apps.js";

const root = new URL("..", import.meta.url).pathname;
const args = process.argv.slice(2);
const flag = (name: string) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined);
const scales = (flag("--scales") ?? "1.2,2.4,8").split(",").map(Number);
const spec = args.find((a, i) => !a.startsWith("--") && !["--scales", "--out", "--json"].includes(args[i - 1]));
let dir = flag("--json");
if (!dir) {
  if (!spec) {
    console.error("usage: npx tsx scripts/bits.ts <spec.py> [--scales 1.2,2.4,8] [--out file.png]  |  --json <dir>");
    process.exit(1);
  }
  dir = mkdtempSync(join(tmpdir(), "bits-"));
  execFileSync("python3", [spec, dir], { stdio: "inherit" });
}
const name = spec ? basename(spec).replace(/\.py$/, "") : basename(dir);
const out = flag("--out") ?? join(root, "out", "bits", `${name}.png`);

const lib = loadLibrary();
const ss = lib.apps.find((o) => o.id === "ss");
if (!ss) throw new Error("no ss app");

const MAX_W = 1600, GAP = 18, PAD = 6, CAPTION = 16;
const cells: { w: number; h: number; svg: string }[] = [];
let bad = 0;
for (const f of readdirSync(dir).filter((f) => f.endsWith(".json")).sort()) {
  const parsed = AssetSchema.safeParse(JSON.parse(readFileSync(join(dir, f), "utf8")));
  if (!parsed.success) {
    bad++;
    console.log(`✖ ${f}: ${parsed.error.issues.slice(0, 4).map((i) => `${i.path.join(".")} ${i.message}`).join("; ")}`);
    continue;
  }
  const a = parsed.data as Asset;
  const { svg, issues } = renderSVG(a, ss.reg);
  for (const i of issues) console.log(`${i.level === "error" ? "✖" : "▲"} ${f}: ${i.where}: ${i.msg}`);
  const [w, h] = a.size;
  const inner = svg.replace(/^[\s\S]*?<svg[^>]*>/, "").replace(/<\/svg>\s*$/, "");
  const tall = Math.max(...scales) * h;
  let x = PAD;
  const pieces: string[] = [];
  for (const k of scales) {
    // Each copy sits on the cell's floor, so a thing's foot lines up across the scales.
    pieces.push(`<g transform="translate(${x + (w * k) / 2},${PAD + tall - (h * k) / 2}) scale(${k})">${inner}</g>`);
    x += w * k + 14;
  }
  const cw = x - 14 + PAD;
  const label = `${a.id.replace("ss.bits.", "")} ${w}×${h} @ ${scales.join("/")}`;
  pieces.push(`<text x="${PAD}" y="${PAD + tall + 12}" fill="#bbb" font-size="11" font-family="monospace">${label}</text>`);
  pieces.push(`<rect x="0.5" y="0.5" width="${cw - 1}" height="${tall + PAD * 2 + CAPTION - 1}" fill="none" stroke="#ffffff22" stroke-dasharray="3 3"/>`);
  cells.push({ w: cw, h: tall + PAD * 2 + CAPTION, svg: pieces.join("") });
}

// Flow the cards into rows, bottoms aligned.
const rows: { y: number; h: number; items: { x: number; c: (typeof cells)[number] }[] }[] = [];
let row = { y: GAP, h: 0, items: [] as { x: number; c: (typeof cells)[number] }[] };
let cx = GAP;
for (const c of cells) {
  if (row.items.length && cx + c.w > MAX_W - GAP) {
    rows.push(row);
    row = { y: row.y + row.h + GAP, h: 0, items: [] };
    cx = GAP;
  }
  row.items.push({ x: cx, c });
  row.h = Math.max(row.h, c.h);
  cx += c.w + GAP;
}
if (row.items.length) rows.push(row);
const W = Math.min(MAX_W, Math.max(...rows.map((r) => Math.max(...r.items.map((i) => i.x + i.c.w)))) + GAP);
const H = rows.length ? rows[rows.length - 1].y + rows[rows.length - 1].h + GAP : GAP * 2;
const body = rows.flatMap((r) => r.items.map((i) => `<g transform="translate(${i.x},${r.y + r.h - i.c.h})">${i.c.svg}</g>`)).join("");
const sheet = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><g style="paint-order:stroke" stroke-linejoin="round" stroke-linecap="round">${body}</g></svg>`;
const ground = (ss.tokens.colors as Record<string, unknown>).soil;
const png = new Resvg(sheet, { background: typeof ground === "string" ? ground : "#1a1512" }).render();
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, png.asPng());
console.log(`✓ ${out} ${png.width}×${png.height}, ${cells.length} cards`);
process.exit(bad ? 1 : 0);
