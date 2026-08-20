# PolyGraphics

An **AI-legible procedural asset system**: game visuals as declarative JSON documents, rendered deterministically against a design-token set. Born from auditing two shape-art games ([docs/reference-analysis.md](docs/reference-analysis.md)) whose visuals were imperative draw code — unreadable, unvariantable, unpreviewable. PolyGraphics inverts that: **an asset is data you can read, diff, patch, validate and render in isolation.**

```bash
npm install
npm run check     # validate + render all + gallery + manifest — the one command you need
open out/gallery.html
```

## The loop

1. Write/edit an asset document in `assets/<id-with-dashes>.json`
2. `npm run check` — errors come back with suggestions ("unknown color token `$bloood` — did you mean `$blood`?")
3. Inspect `out/gallery.html` (every asset, variant, animation, theme) or `out/svg/*.svg`
4. Iterate

Renders are **byte-identical across runs** (seeded scatter, no wall-clock anywhere), so SVG diffs are meaningful and visual regressions are testable.

## Layout

```
tokens/default.json    design tokens: THE source for colors/strokes/alpha/layers/grid
themes/*.json          partial token overlays (e.g. ice.json) — restyle everything at once
assets/*.json          asset documents, one per asset, filename = id with dots→dashes
adapters/phaser|godot  one drop-in file per engine, consuming compiled IR
src/                   schema (zod) · token resolver · SVG renderer · compiler · gallery · cli
scripts/               inspect (design loop) · compare (before/after) · adapter tests
dist/assets.json       committed: the bundle consumers import as `polygraphics/assets`
out/                   generated, ignored: svg/, compiled/, png/, gallery.html, manifest.json
baselines/             accepted PNG renders; `npm run regress` diffs against these
docs/                  reference-analysis.md — why this exists
```

## Design loop

```bash
npx tsx scripts/inspect.ts ss.enemy.imp ss.enemy.bat --anim   # open out/inspect.html
```

Renders each asset **big** (judge the form), **at true game scale on the real ground color** (judge whether it survives the size it is actually seen at), and **as a flat silhouette** (if two enemies are indistinguishable in black, colour is doing work that shape should be doing). This is the loop the Shape Survivors redesign was built in — it caught a chaser that read as facing backwards, two antennae that overlapped into one, and two creatures that were the same cream colour.

## Asset document

```jsonc
{
  "id": "enemy.imp",                  // dotted, category-first
  "name": "Imp",
  "description": "Small aggressive melee chaser: …",   // REQUIRED — legibility is the point
  "tags": ["enemy", "melee", "small"],// tags[0] = gallery category
  "size": [32, 32],                   // canvas px (multiple of grid, else warning)
  "anchor": [0.5, 0.5],               // optional; origin of the coordinate system
  "meta": { "radius": 9 },            // optional sim-facing hints; manifest adds derived radius
  "parts": [ … ],                     // NAMED parts, array order = draw order
  "variants": { "elite": … },         // declarative patches
  "animations": { "idle": … }         // keyframe tracks per part
}
```

**Coordinates:** origin at the anchor, +x right, +y down, px. Parts place themselves with `at`.

### Parts

Every part has an `id` (snake_case — variants and animations address parts by id), and optionally `at`, `rot` (deg), `scale`, `opacity`, `mirrorX` (draw a second copy mirrored across the vertical axis — build symmetric features once). A part is one of:

| form | keys | meaning |
|---|---|---|
| shape part | `shape`, `fill?`, `stroke?` | draw a primitive |
| use part | `use: "lib.face"`, `variant?` | compose another asset document in place (shared parts, single-source icons; cycle-guarded, depth ≤ 4). `variant` picks a state of the used document, so one library part can appear in several conditions across the roster |
| repeat part | `repeat: { of, count, area, seed?, jitterRot?, scaleRange? }`, `fill?` | deterministic seeded scatter (pebbles, specks) |

### Shapes

`circle {r}` · `ellipse {rx, ry}` · `rect {w, h, corner?}` (centered) · `ngon {sides, r, rot?}` (regular, first vertex up) · `star {points, r, r2, rot?}` · `poly {points: [[x,y],…]}` (arbitrary — concave/asymmetric silhouettes are the reason this exists) · `ring {r, width, from?, to?}` (arc; painted with `fill` as its stroke color) · `wedge {r, from, to}` (pie slice; angles in degrees, 0 = +x).

### Paint = token references, not values

```
"$blood"           colors.blood
"$blood.light"     lightened by ramps.light   (.light2 / .dark / .dark2)
"$blood@soft"      alpha from alpha tokens    ("$blood.dark@0.4" = literal alpha)
{ "gradient": "linear"|"radial", "from"?, "to"?, "stops": [[0,"$soul.light"],[1,"$soul.dark"]] }
```

Stroke widths and opacities likewise take token names (`"width": "thin"`, `"opacity": "soft"`). Raw `#hex` renders but warns with the nearest token. **A theme is just a token overlay** — `themes/ice.json` swaps warm hues for cold and every asset restyles coherently, silhouettes untouched.

### Variants — patches, not redraws

```jsonc
"elite": {
  "description": "Arcane recolor + third eye + 1.25× scale.",
  "scale": 1.25,                                  // canvas grows too; nothing clips
  "set": { "body.fill": "$arcane", "rim.stroke.color": "$gold" },  // "<partId>.<path>": value
  "add": [ { "id": "third_eye", … } ],
  "remove": [ "tail" ]
}
```

Patched parts are re-validated, so a variant can never silently produce an invalid part. This replaces both games' entire variant vocabulary (scale × tint) with real thematic restyling.

### Animations — data, not code

```jsonc
"idle": {
  "duration": 1.6,                                 // seconds, loops
  "tracks": [
    { "part": "body", "prop": "y",   "keys": [[0,0],[0.5,-1.4],[1,0]] },          // ease default: sine
    { "part": "tail", "prop": "rot", "keys": [[0,-8],[0.5,10],[1,-8]] },
    { "part": "plate","prop": "rot", "keys": [[0,0],[1,360]], "ease": "linear" }  // seamless spin
  ]
}
```

Props: `x` `y` (px) · `rot` (deg) · `scale` (factor) · `opacity`. One animated prop per part per animation (transform channels never collide — the `scale.x`-is-also-facing bug class is structurally impossible). The gallery plays them as CSS; engine adapters read the same keys as tweens.

**Scope: animations move parts within a body, never the body itself.** A part's `rot` turns it about its own origin, so a whole-asset spin cannot be written as one track per part — and shouldn't be. Whole-body transforms (spin, facing flip, knockback, hit-flash tint) belong to the engine, which already owns them; `ss.proj.boom` therefore declares no spin animation, because the weapon code does `sprite.rotation += spin * dt`. Keep the two layers separate and neither can fight the other.

## Output formats

The system has one source of truth and four compiled outputs:

| form | where | who consumes it |
|---|---|---|
| **authoring documents** | `assets/*.json` + `tokens/` + `themes/` | humans and AI agents (the only thing you edit) |
| **compiled IR** | `out/compiled/*.json` (+ per-theme) | **game engines** — tokens resolved to `[r,g,b,a]` floats, variants pre-applied, `use` inlined, `mirrorX`/`repeat` expanded, ngon/star → concrete points. Engine adapters are dumb interpreters; no token/grammar/PRNG logic ships to the game |
| **the bundle** | `dist/assets.json` via `npm run dist` | the same IR as one file keyed by asset id — what a consuming game imports as `polygraphics/assets`. Committed, unlike `out/`, because it is the thing that leaves the repo |
| **previews** | `out/svg/*.svg`, `out/gallery.html` | humans and AI agents (inspect/iterate; CSS animations play in the gallery) |
| **bakes** | `out/png/*.png` (4×) via `npm run png` | any engine as plain images; also the regression baseline |
| **manifest** | `out/manifest.json` | engines/AI index: description, tags, named parts, variants, animations, **derived bounding radius** (art and collision can't silently desync) |

## Using it from a game

### Install it as a package

The repo is a package. A game depends on it and imports two things — the renderer for its engine, and the art:

```jsonc
// the game's package.json
"dependencies": { "polygraphics": "file:../polygraphics" }
```

```ts
import { bakeFlat } from "polygraphics/phaser";   // the adapter: zero deps, zero engine imports
import bundle from "polygraphics/assets";         // { format, assets: { "ss.enemy.imp": IR, … } }
```

Nothing is generated into the consuming repo and nothing is copied across repos. Pointing the dependency at a working copy (`npm i file:../polygraphics-worktrees/my-branch`) is how you try art before it lands; `npm update polygraphics` is how you pick it up after.

Assets are keyed by their canonical id, never by any game's texture key — what a game calls its textures is the game's business, so the mapping lives on the consuming side:

```ts
const MAP = { e_imp: "ss.enemy.imp", i_frost: "ss.icon.frost" };   // in the game
```

Check `bundle.format` (`polygraphics-bundle@1`) on the way in: a mismatch means the IR changed shape, and failing loudly beats every sprite coming out subtly wrong.

### What actually changes in the game

The render pipeline does **not** change — Phaser still renders sprites, Godot still renders nodes. What changes is one seam: **asset instantiation** (the hand-written `BootScene` blocks / `_build_gfx()` match-arms are replaced by an adapter call). Three integration levels, per entity:

**Level 0 — PNGs only.** Load `out/png/*.png` like any art. Zero code change anywhere; whole-sprite motion only.

**Level 1 — flat bake (Phaser).** One generated texture per asset; existing sprite pipeline untouched. For hot-path objects (projectiles, pickups, massed enemies):

```ts
import { bakeFlat } from "polygraphics/phaser";             // 1 file, no deps
const key = bakeFlat(this, impIR);                          // in BootScene.preload/create
this.add.sprite(x, y, key);                                 // exactly as before
const eliteKey = bakeFlat(this, impIR, { variant: "elite" });
```

**Level 2 — rig (per-part animation).** A Container of per-part Images plus a data-driven keyframe player. For characters/bosses where parts move:

```ts
import { buildRig } from "polygraphics/phaser";
const rig = buildRig(this, impIR);        // rig.container, rig.parts
rig.play("idle");
// in update(): rig.tick(dt)
```

**Godot** mirrors the same two levels with one file (`adapters/godot/polygraphics.gd`):

```gdscript
var ir  := PolyGraphics.load_ir("res://pg/enemy-imp.json")
var rig := PolyGraphics.build(ir, "elite")    # Node2D tree; parts addressable by meta pg_id
add_child(rig)
PolyGraphics.play(rig, ir, "idle")            # Tweens driven by the same keyframe data
```

Both adapters are verified: the Phaser one by a mock-scene smoke test (`npx tsx scripts/test-phaser-adapter.ts`), the Godot one headlessly in the real engine (`godot --headless -s scripts/test_godot_adapter.gd`).

## Visual regression

```bash
npm run baseline   # accept current renders as reference (commit baselines/)
npm run regress    # byte-compare current PNGs against baselines; exits 1 on change
```

Because rendering is deterministic, a one-digit token drift (the `ff9b3d` vs `ff9d3c` class of bug) fails regression on exactly the assets that use that token.

`npm run check` also lints the palette: a colour token nothing references is reported as dead (drop it or use it), and a theme overriding a token that no longer exists is an error, not a silent no-op.

## Worked example: the Shape Survivors roster

`assets/ss.*` is the full roster of the sibling project, first transcribed 1:1 from its `BootScene.ts`, then re-authored around one sentence of fiction: **the protagonist has lost their pheromone transmitter, and the hive hunts them for the silence.** `npx tsx scripts/compare.ts` builds `out/compare.html` — 39 before/after pairs.

What the system contributed that imperative draw code could not:

- **`ss.lib.organ`** is the premise as a single document. Enemies compose it lit; the eight player characters compose the *same document* with `variant: "dead"` — cracked, unlit, silent. Change that one file and every creature in the game changes together. Verified to diverge correctly in both the Phaser and Godot adapters.
- **Silhouettes carry identity**, so the roster survives the flat-silhouette test: a low six-legged Tracker, a swept-wing Drifter, a lopsided Husk, a split-open Molt, a plated Soldier. In the original, all seven were the same convex blob in different hues.
- **Variants are real states**, not scale × tint: `ss.enemy.brazier#spent` is the destroyed relay, `ss.enemy.boss#enraged` splits the shell open, `ss.pickup.chest#cursed` puts something awake inside.
- **`themes/ice.json`** restyles the entire redesigned roster — chitin to blue-grey, pheromone to a cold signal — without touching a silhouette.
- **The arsenal follows a second rule**: player weapons are hive material with the signal stripped out — chitin, husk bone, molt shell, honed to a cold frost edge, and never magenta. A lash is a Soldier's mandible on a cord; the orbiting drone is a hexagonal plate cut from a Molt; the thrown card is a Drifter's wing on a bone frame. The one place the hive's colour touches the player is `ss.fx.pickup`, the half-second of borrowed voice when a scent crystal is absorbed.
- **Weapon icons compose their weapons.** `ss.icon.wand/whip/boomerang` `use` `ss.proj.bolt/slash/boom` directly, so the original's five-shapes-authored-twice problem cannot recur; `evolved` is a rim-colour patch, not a second drawing.
- **The game draws nothing of its own any more.** Every icon, terrain prop and creature it once drew in `BootScene.ts` is a document here; what stayed behind is the handful of things that were never art — a runtime-tinted particle, procedural noise canvases, damage digits. It consumes this repo as a package and keeps only the map from its texture keys to these ids.
- Gameplay contracts held throughout: ids, body radii and variant slots are unchanged, so the redesign drops into the same code that consumed the faithful port. Three assets carry hard geometry contracts noted in their own descriptions — `ss.proj.ring` (`wave.r / 62`), `ss.proj.ball` (`ballR / 14`) and `ss.proj.aura` (`r / 64`, plus runtime tinting, so it stays neutral white).

## For AI agents

You are the intended primary author. Rules of the road:

1. Read `tokens/default.json` first; author **only** with token references.
2. Every asset gets an honest `description` and tagged category — future sessions (and the manifest) rely on them.
3. Name parts for what they are (`pauldron`, not `rect3`); variants and animations address them by id.
4. Prefer `use` over copying parts between assets; prefer a variant over a near-duplicate asset; prefer a theme over recoloring assets one by one.
5. After every edit: `npm run check`. It either passes or tells you exactly what to fix (with suggestions). Then read the SVG or screenshot the gallery to judge the result visually before declaring it good.
6. Add jitter only via `repeat.seed` — never invent randomness elsewhere; renders must stay diffable.

## Roadmap (v0.x)

- ~~FX verb catalog~~ → `fx.slash/impact/ring/burst/muzzle` shipped; still to port: ghost (needs entity silhouette at runtime — adapter-level), damage_number (needs a text primitive)
- ~~Engine adapters (Phaser, Godot)~~ → shipped in `adapters/`; next: wire into vamp_surv / godot_test for a live side-by-side
- ~~PNG rasterization + regression~~ → shipped (`png` / `baseline` / `regress`)
- Per-instance motion vectors for `repeat` scatter (true radial bursts instead of uniform scale)
- Part libraries beyond `lib.face` (hands, crowns, telegraph markers); named particle-emitter presets
- Palette lint: flag near-duplicate hex across tokens; gradient support in adapters (currently flat mid-color fallback)
