/**
 * SPIKE — not system code. Evidence for docs/graphics-capability-plan.md, §Decision 3.
 *
 * An agent authoring here cannot see, which is why the sound side measures loudness and the art side
 * measures contrast against the floor. A *look* can be measured the same way, coarsely: the value
 * structure and the colour budget of a frame, in OKLCH, compared against a reference frame. This does
 * not say whether a picture is good. It says whether it is in the same register — bright and grey
 * with one saturated accent, or dark with emissive highlights — which is the part of "make it look
 * like this" a number can hold.
 *
 *   npx tsx scripts/spikes/style-probe.ts a.png b.jpg …
 *
 * Reads PNG or JPEG through resvg (an <image> in an SVG), so it needs no decoder of its own, and an
 * SVG — a document's own render — directly.
 * Black letterbox rows are dropped before measuring, so a frame is measured, not its bars.
 */
import { readFileSync } from "node:fs";
import { Resvg } from "@resvg/resvg-js";
import { oklab } from "./pixel.js";

/** Pixel size from the file header: PNG's IHDR, or the first SOFn marker of a JPEG. */
function sizeOf(buf: Buffer): [number, number] {
  if (buf[0] === 0x89) return [buf.readUInt32BE(16), buf.readUInt32BE(20)];
  let i = 2;
  while (i < buf.length) {
    const marker = buf[i + 1], len = buf.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc)
      return [buf.readUInt16BE(i + 7), buf.readUInt16BE(i + 5)];
    i += 2 + len;
  }
  throw new Error("no SOF marker");
}

function load(path: string): { w: number; h: number; px: Uint8Array } {
  const buf = readFileSync(path);
  if (path.endsWith(".svg")) {
    const r = new Resvg(buf.toString("utf8"), { fitTo: { mode: "zoom", value: 2 } }).render();
    return { w: r.width, h: r.height, px: new Uint8Array(r.pixels) };
  }
  const mime = buf[0] === 0x89 ? "image/png" : "image/jpeg";
  const [w, h] = sizeOf(buf);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${w}" height="${h}"><image width="${w}" height="${h}" xlink:href="data:${mime};base64,${buf.toString("base64")}"/></svg>`;
  const r = new Resvg(svg).render();
  return { w: r.width, h: r.height, px: new Uint8Array(r.pixels) };
}

function probe(path: string) {
  const { w, h, px } = load(path);
  const rowDark = (y: number) => {
    let s = 0;
    for (let x = 0; x < w; x++) s += px[(y * w + x) * 4] + px[(y * w + x) * 4 + 1] + px[(y * w + x) * 4 + 2];
    return s / (w * 3) < 6;
  };
  let y0 = 0, y1 = h - 1;
  while (y0 < h && rowDark(y0)) y0++;
  while (y1 > y0 && rowDark(y1)) y1--;
  const Ls: number[] = [], Cs: number[] = [];
  const hueBins = new Array(12).fill(0);
  for (let y = y0; y <= y1; y += 2)
    for (let x = 0; x < w; x += 2) {
      const i = (y * w + x) * 4;
      const [L, a, b] = oklab([px[i], px[i + 1], px[i + 2]]);
      const C = Math.hypot(a, b);
      Ls.push(L);
      Cs.push(C);
      if (C > 0.08) hueBins[Math.floor((((Math.atan2(b, a) * 180) / Math.PI + 360) % 360) / 30)]++;
    }
  const sorted = [...Ls].sort((p, q) => p - q);
  const q = (k: number) => sorted[Math.floor(k * (sorted.length - 1))];
  const mean = (v: number[]) => v.reduce((s, x) => s + x, 0) / v.length;
  const accent = Cs.filter((c) => c > 0.08).length / Cs.length;
  const glow = Ls.filter((L, i) => L > 0.75 && Cs[i] > 0.1).length / Ls.length;
  const names = ["red", "orange", "yellow", "lime", "green", "teal", "cyan", "azure", "blue", "violet", "purple", "magenta"];
  const top = hueBins.map((n, i) => [n, names[i]] as [number, string]).sort((p, q) => q[0] - p[0]).filter(([n]) => n > 0).slice(0, 2).map(([, n]) => n);
  return { L: mean(Ls), p10: q(0.1), p90: q(0.9), C: mean(Cs), accent, glow, top };
}

const rows = process.argv.slice(2).map((p) => ({ p, ...probe(p) }));
const pct = (x: number) => `${(100 * x).toFixed(1)}%`.padStart(6);
console.log("frame".padEnd(28), "L̄     L p10–p90    C̄      accent  bright-accent  hues");
for (const r of rows)
  console.log(
    r.p.split("/").pop()!.slice(0, 27).padEnd(28),
    r.L.toFixed(2), " ", `${r.p10.toFixed(2)}–${r.p90.toFixed(2)}`.padEnd(11), " ", r.C.toFixed(3), " ", pct(r.accent), "  ", pct(r.glow), "      ", r.top.join(", "),
  );
