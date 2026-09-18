/**
 * Assembles the gallery as a static site, for a host that serves a directory.
 *
 *   npm run site       → site/  (index.html + wav/ + spec/)
 *
 * The gallery is one file that links its bake beside it (`wav/`, `spec/`), so
 * a site is that file renamed to index.html with those two directories copied
 * next to it. Everything else `check` writes — svg, IR, manifest — is scratch
 * a consumer reads through dist/, never through a browser.
 *
 * Vercel runs this on every push (vercel.json), so a pull request gets a
 * preview of the gallery with its documents in it, and main serves the current
 * one.
 */
import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const OUT = join(ROOT, "out");
const SITE = join(ROOT, "site");

if (!existsSync(join(OUT, "gallery.html"))) {
  console.error("out/gallery.html is missing — `npm run site` runs `check` first; run that.");
  process.exit(1);
}
rmSync(SITE, { recursive: true, force: true });
mkdirSync(SITE, { recursive: true });
cpSync(join(OUT, "gallery.html"), join(SITE, "index.html"));
const copied = ["wav", "spec"].filter((d) => existsSync(join(OUT, d)));
for (const d of copied) cpSync(join(OUT, d), join(SITE, d), { recursive: true });
console.log(`✓ site → site/ (index.html${copied.map((d) => ` + ${d}/`).join("")})`);
