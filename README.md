# PolyGraphics

An **AI-legible procedural asset system**: game visuals *and sound* as declarative JSON documents, rendered deterministically against a design-token set. Born from auditing two shape-art games ([docs/reference-analysis.md](docs/reference-analysis.md)) whose visuals were imperative draw code — unreadable, unvariantable, unpreviewable. PolyGraphics inverts that: **an asset is data you can read, diff, patch, validate and render in isolation.**

```bash
npm install
npm run check     # validate + render all + gallery + manifest — the one command you need
open out/gallery.html
```

Working on art? Leave the gallery open and run `npm run watch`: a save rebuilds, and the page reloads itself without losing the tab, the search or the asset you had open.

## The loop

1. Write/edit an asset document in `assets/<id-with-dashes>.json` (or a sound in `sounds/`)
2. `npm run check` — errors come back with suggestions ("unknown color token `$bloood` — did you mean `$blood`?"), or `npm run watch` to have that happen on save
3. Inspect `out/gallery.html` — tabs per category, search across all of them, and a page per asset. Sounds are in the same page under their own heading: cards you can play, a detail view per document, and a "the set" tab that puts every level side by side
4. Iterate

The per-asset page is where a change gets discussed: the render big, at any zoom, on the ground colour it will actually sit on, or flattened to a silhouette — beside the parts in draw order with their ids, token fills and transforms. Naming `fang` beats pointing at a tooth, and **copy brief** puts exactly that on the clipboard for a chat.

Renders are **byte-identical across runs** (seeded scatter, no wall-clock anywhere), so SVG diffs are meaningful and visual regressions are testable.

## Layout

```
tokens/default.json    design tokens: THE source for colors/strokes/alpha/layers/grid,
                       and under `audio`, for pitches/gains/resonances/lengths
themes/*.json          partial token overlays (e.g. ice.json) — restyle everything at once
assets/*.json          asset documents, one per asset, filename = id with dots→dashes
sounds/*.json          sound documents, same naming rule
adapters/phaser|godot  one drop-in file per engine, consuming compiled IR
adapters/webaudio      the same, for sound
src/                   schema (zod) · token resolver · SVG renderer · compiler · gallery · cli
                       sound-schema · sound-compile · sound-render (PCM/WAV/measurement)
scripts/               watch (rebuild on save) · inspect · inspect-sound · compare · adapter tests
dist/assets.json       committed: the bundle consumers import as `polygraphics/assets`
dist/sounds.json       likewise, as `polygraphics/sounds`
out/                   generated, ignored: svg/, compiled/, png/, wav/, gallery.html, manifest.json
baselines/             accepted PNG and WAV bakes; `npm run regress` diffs against these
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

Props: `x` `y` (px) · `rot` (deg) · `scale` (factor) · `opacity`. A part may animate several of them at once but each at most once, which is the guarantee that actually mattered: transform channels never collide, so the `scale.x`-is-also-facing bug class stays structurally impossible while a part can still gather and swell in the same breath. CSS gets one transform and one timing function per rule, so tracks that disagree on key times are sampled onto a shared timeline through each track's own ease; tracks that agree emit exactly what they always did. The gallery plays them as CSS; engine adapters read the same keys as tweens.

**Scope: animations move parts within a body, never the body itself.** A part's `rot` turns it about its own origin, so a whole-asset spin cannot be written as one track per part — and shouldn't be. Whole-body transforms (spin, facing flip, knockback, hit-flash tint) belong to the engine, which already owns them; `ss.proj.boom` therefore declares no spin animation, because the weapon code does `sprite.rotation += spin * dt`. Keep the two layers separate and neither can fight the other.

## Sound document

A sound is the asset document with **time where space was**. The vocabulary is
deliberately the same one, because whoever can author an asset should be able to
author a sound without learning a second system:

| asset | sound |
|---|---|
| `parts`, array order = draw order | `voices`, array order = mix order |
| `shape` primitive | `source` primitive (`osc` / `noise`) |
| `fill` — a token reference, never a raw value | `gain` — likewise, and `freq` from the pitch palette |
| `at: [x, y]` in px | `at: 0.006` in seconds |
| `size` — the canvas | `duration` — the canvas |
| `use` — compose another document | `use` — compose another document |
| `repeat` — seeded scatter across an **area** | `repeat` — seeded scatter across a **span** (grains) |
| `animations.tracks` — `[t, value]` per part per prop | `env` — `[t, value]` per voice per prop |
| `variants` — declarative patches | `variants` — the same, plus `pitch` and `stretch` |

```jsonc
{
  "id": "ss.sfx.hit",
  "description": "…",              // REQUIRED — legibility is the point
  "duration": 0.09,                 // seconds
  "meta": { "minInterval": 45 },    // sim-facing hints (the game's rate limit)
  "jitter": { "freq": [0.82, 1.2] },// rolled per trigger, by the engine
  "voices": [
    {
      "id": "thump",
      "dur": "tick",                              // a length token
      "gain": "soft",                             // a level token
      "source": { "kind": "osc", "wave": "square",
                  "freq": "$tap", "to": "$tap.down" },      // 200 → 100Hz
      "env": [{ "prop": "gain", "keys": [[0, 1], [1, 0]] }]
    },
    {
      "id": "grit",
      "at": 0.004,
      "gain": "faint",
      "filter": { "type": "bandpass", "freq": "$grit", "to": "$grit.down2", "q": "band" },
      "env": [{ "prop": "gain", "keys": [[0, 1], [1, 0.06]] }],
      "repeat": { "of": { "kind": "noise" }, "count": 5, "spread": 0.03,
                  "grain": 0.012, "gainRange": [0.55, 1] }
    }
  ],
  "variants": { "elite": { "description": "…", "pitch": 0.55, "stretch": 1.5 } }
}
```

**Pitch is the palette.** `$tap` is `audio.pitch.tap`; `$tap.down` walks the
`audio.ramps` the way `$blood.dark` walks the color ramps, and `.down2` walks it
twice. A raw number in Hz renders but warns and names the nearest token — the
same deal raw `#hex` gets, for the same reason, and only in the slots that carry
identity: a keyframe or a `to` target is a trajectory and passes silently, the
way an animation track's `y` is plain px while a `fill` must be a token. Gain, Q
and length take a number or a token name, exactly as stroke widths and opacities
do. `themes/*.json` may overlay the `audio` section too, so one overlay restyles
how the roster looks *and* how it sounds.

**The palette is split the way the fiction is.** Half of it is the hive's body —
`$tap` is chitin under a weapon, `$shell` a small one coming apart, `$bone` the
player's own frame, `$grit` shell granulating. The other half is the hive's
*voice*, and it is deliberately the A-minor scale the game's own score is already
written in: `$tonic` `$third` `$fifth` `$seventh` are A5, C5, E5, G5, four of the
six notes the adaptive music plays. An effect therefore cannot clash with the
music, the fanfares are in key by construction, and the whole interface retunes
by editing four numbers.

**`to` is shorthand for the two-key slide** almost every short sound wants —
`{ "freq": "$tap", "to": "$tap.down" }` compiles to exactly the `freq` envelope
you would have written, and nothing downstream knows it existed. Same on a
filter, where it sweeps the cutoff. It is the relationship `ngon` has to `poly`.

**An envelope on a scatter belongs to the gesture, not to each grain.** A dry
crack is bright grains first and dull grains last — one sweep across the whole
scatter, not the same sweep five times. The compiler cuts the envelope into
per-grain windows so the IR stays a flat list of voices and no adapter has to
learn what a bus is.

**Library documents are instruments.** `ss.lib.note` is one note of the flat
square voice; `ss.sfx.levelup` and `ss.sfx.victory` are that document composed
four and six times with a `variant` picking the degree, and `dur` on the use
voice refitting it to a slower step. `ss.lib.knell` is its low sawtooth twin and
`ss.sfx.gameover` walks the same ladder down it. Retune the library and every
figure built on it moves together — the exact `ss.lib.organ` argument, and
`scripts/test-webaudio-adapter.ts` asserts it by retuning the note in memory and
checking that both fanfares follow while the knell-based one does not.

**Whole-sound behaviour belongs to the engine**, the same boundary the visual
side draws at whole-body transforms. A document describes one trigger: rate
limiting is a `meta` hint the game enforces, positional panning is the game's,
and the adaptive score — a scheduler reacting to how hard the game is pressing —
is game logic that may *use* these documents but is not one of them.

### Hearing it

Sounds live in the same gallery the art does — same search, same `#/<id>`
routing, same copy-brief. A sound card carries a waveform and a transport per
take; its detail view carries the voices in mix order, the variants, and the
measurements. Two things are sound-specific:

- **burst ×8** fires the document the way the game will, jitter rolled per
  trigger. It is the only way to judge something that plays hundreds of times in
  a run, and it is why `hit` is authored as the smallest sound in the set.
- **the set** tab sorts every sound by level with its distance from the median.
  Clipping is a per-sound question the cards answer; *does this hold together*
  is a question about the set, and it is answered by looking at the two ends of
  one sorted list.

The gallery links `out/wav/` rather than embedding it — twenty-seven takes of
base64 would add ~3MB to a page that reloads itself on every rebuild — so every
command that writes the gallery writes the bake too.

```bash
npm run check                        # everything, gallery and bake included
npm run wav                          # just the bake, and print what it measures
npx tsx scripts/inspect-sound.ts     # a standalone, self-contained page to send someone
```

That last one is the shareable export: takes embedded, no server, opens
anywhere. Pass ids to narrow it (`… ss.sfx.hit ss.sfx.creak`).

That page exists because the rest of the system leans on rendering something and
looking at it, and **an agent authoring these documents cannot listen**. So the
bake is also the instrument: `npm run check` measures every sound and reports
clipping, near-silence, and any sound sitting more than 9dB off the set's median
level. RMS is measured over the sounding extent rather than the canvas, because
a sound that ends early is shorter, not quieter, and a lint that confuses the two
sends you to raise the gain on the wrong thing.

A document may state, in writing, why it belongs outside that band —
`offBand` — for the cue whose whole job is to sit under the cues it shares a
frame with. The exception then reads as a decision somebody made rather than a
warning everybody learns to scroll past.

It earns its keep immediately: porting the sibling project's set, the lint put
`whoosh` 17dB under the median. Not a transcription slip — the original gave a
noise burst the same gain number it gave its oscillators, and a wide bandpass
throws most of a noise burst away. (Its own `creak` comment says exactly this
about a different sound; the lint is that comment, applied to all of them.)
Structure, consistency and non-regression are the machine's to guarantee; taste
stays with whoever has ears.

### Playing it from a game

```ts
import { play, bake, playBuffer } from "polygraphics/webaudio";
import bundle from "polygraphics/sounds";        // { format, sounds: { "ss.sfx.hit": IR, … } }

play(ctx, sfxBus, bundle.sounds["ss.sfx.hit"]);              // live graph, full jitter
const buf = await bake(ctx, bundle.sounds["ss.sfx.hit"]);    // or render once…
playBuffer(ctx, sfxBus, buf, { rate: 0.82 + Math.random() * 0.38 });   // …and fire cheaply
```

Two levels, mirroring `bakeFlat` / `buildRig` on the visual side: one buffer for
sounds that fire constantly, a live node graph for the ones worth the nodes.
Check `bundle.format` (`polygraphics-sounds@1`) on the way in.

Both paths and the offline WAV are three interpreters of one IR, and
`npx tsx scripts/test-webaudio-adapter.ts` is what keeps them honest — it drives
the adapter against a recording mock context and checks its envelope curves and
its noise, sample for sample, against the renderer's own.

## Output formats

The system has one source of truth and four compiled outputs:

| form | where | who consumes it |
|---|---|---|
| **authoring documents** | `assets/*.json` + `tokens/` + `themes/` | humans and AI agents (the only thing you edit) |
| **compiled IR** | `out/compiled/*.json` (+ per-theme) | **game engines** — tokens resolved to `[r,g,b,a]` floats, variants pre-applied, `use` inlined, `mirrorX`/`repeat` expanded, ngon/star → concrete points. Engine adapters are dumb interpreters; no token/grammar/PRNG logic ships to the game |
| **the bundle** | `dist/assets.json` via `npm run dist` | the same IR as one file keyed by asset id — what a consuming game imports as `polygraphics/assets`. Committed, unlike `out/`, because it is the thing that leaves the repo |
| **previews** | `out/svg/*.svg`, `out/gallery.html` | humans and AI agents (inspect/iterate; CSS animations play in the gallery) |
| **bakes** | `out/png/*.png` (4×) via `npm run png`, `out/wav/*.wav` via `npm run wav` | any engine as plain images or audio files; also the regression baseline |
| **manifest** | `out/manifest.json` | engines/AI index: description, tags, named parts, variants, animations, **derived bounding radius** (art and collision can't silently desync), and per sound its **measured peak, RMS and brightness** |

## Using it from a game

### Install it as a package

The repo is a package. A game depends on it and imports two things — the renderer for its engine, and the art:

```jsonc
// the game's package.json
"dependencies": { "polygraphics": "github:wndgur2/polygraphics" }
```

A git dependency, not a path: CI and deploy builds clone only the consuming repo, so `file:../polygraphics` resolves to nothing there — npm links it to a dangling symlink, says nothing, and the build fails later at `Cannot find module`. The repo is public, so no credentials are involved. `dist/` and the adapter are committed, so there is no build step on install.

The lockfile pins the exact commit, which is what makes a build reproducible; `npm update polygraphics` is how you take new art.

```ts
import { bakeFlat } from "polygraphics/phaser";   // the adapter: zero deps, zero engine imports
import bundle from "polygraphics/assets";         // { format, assets: { "ss.enemy.imp": IR, … } }
```

Nothing is generated into the consuming repo and nothing is copied across repos. To try art before it lands, point the dependency at a branch (`npm i github:wndgur2/polygraphics#my-branch`) or at a local working copy (`npm i file:../polygraphics`) — the latter only for local work, never committed.

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
npm run baseline   # accept current bakes as reference (commit baselines/)
npm run regress    # byte-compare current PNGs and WAVs against baselines; exits 1 on change
```

Because rendering is deterministic, a one-digit token drift (the `ff9b3d` vs `ff9d3c` class of bug) fails regression on exactly the assets that use that token. Sound rides the same rails: every source of randomness is a seeded PRNG carried in the IR and there is no wall clock anywhere, so a bake is byte-identical run to run and a WAV diff means somebody changed the sound.

`npm run check` also lints the palette: a colour token nothing references is reported as dead (drop it or use it), and a theme overriding a token that no longer exists is an error, not a silent no-op.

## Worked example: the Shape Survivors roster

`assets/ss.*` is the full roster of the sibling project, first transcribed 1:1 from its `BootScene.ts`, then re-authored around one sentence of fiction: **the protagonist has lost their pheromone transmitter, and the hive hunts them for the silence.** `npx tsx scripts/compare.ts` builds `out/compare.html` — 39 before/after pairs.

What the system contributed that imperative draw code could not:

- **`ss.lib.organ`** is the premise as a single document. Enemies compose it lit; the eight player characters compose the *same document* with `variant: "dead"` — cracked, unlit, silent. Change that one file and every creature in the game changes together. Verified to diverge correctly in both the Phaser and Godot adapters.
- **Silhouettes carry identity**, so the roster survives the flat-silhouette test: a low six-legged Tracker, a swept-wing Drifter, a lopsided Husk, a split-open Molt, a plated Soldier. In the original, all seven were the same convex blob in different hues.
- **Variants are real states**, not scale × tint: `ss.enemy.brazier#spent` is the destroyed relay, `ss.enemy.boss#enraged` splits the shell open, `ss.pickup.chest#cursed` puts something awake inside.
- **`themes/ice.json`** restyles the entire redesigned roster — chitin to blue-grey, pheromone to a cold signal — without touching a silhouette.
- **The arsenal follows a second rule**: player weapons are hive material with the signal stripped out — chitin, husk bone, molt shell, honed to a cold frost edge, and never magenta. A lash is a Soldier's mandible on a cord; the orbiting drone is a hexagonal plate cut from a Molt; the thrown card is a Drifter's wing on a bone frame. The one place the hive's colour touches the player is `ss.fx.pickup`, the half-second of borrowed voice when a lump of pulp is absorbed.
- **Weapon icons compose their weapons.** `ss.icon.wand/whip/boomerang` `use` `ss.proj.bolt/slash/boom` directly, so the original's five-shapes-authored-twice problem cannot recur; `evolved` is a rim-colour patch, not a second drawing.
- **The game draws nothing of its own any more.** Every icon, terrain prop and creature it once drew in `BootScene.ts` is a document here; what stayed behind is the handful of things that were never art — a runtime-tinted particle, procedural noise canvases, damage digits. It consumes this repo as a package and keeps only the map from its texture keys to these ids.
`sounds/ss.*` is the same project's effect set, ported from the 569-line `switch` in its `AudioSynth.ts` — 18 effects plus the two library instruments they are built from. What the port bought:

- **The score's key reaches the effects.** The music runs an A-minor cycle; the arpeggios in the old code were four hardcoded floats that happened to be C major. They are now `$third $fifth $seventh $third.up` — four notes the music already plays — so a fanfare can never land outside the key it fires in.
- **Two figures, one instrument.** Level-up, victory and game-over were three separate note arrays; they are now `ss.lib.note` and `ss.lib.knell` composed with a degree per voice. The win figure and the loss figure are provably the same instrument in two moods, and retuning either is one file.
- **The dry crack is data.** `creak` was a hand-written grain loop with `Math.random()` in it, which is why it could never be regression-tested; it is a seeded `repeat` voice now, and its bake is byte-identical forever.
- **The set was measured, and one sound was wrong.** See the loudness lint above.
- **Levels come off a five-rung ladder** (`faint soft mid loud peak`) instead of sixteen ad-hoc floats between 0.14 and 0.5, so "make the interface quieter" is one token.

- Gameplay contracts held throughout: ids, body radii and variant slots are unchanged, so the redesign drops into the same code that consumed the faithful port. Three assets carry hard geometry contracts noted in their own descriptions — `ss.proj.ring` (`wave.r / 62`), `ss.proj.ball` (`ballR / 14`) and `ss.proj.aura` (`r / 64`, plus runtime tinting, so it stays neutral white).

## For AI agents

You are the intended primary author. Rules of the road:

1. Read `tokens/default.json` first; author **only** with token references.
2. Every asset gets an honest `description` and tagged category — future sessions (and the manifest) rely on them.
3. Name parts for what they are (`pauldron`, not `rect3`); variants and animations address them by id.
4. Prefer `use` over copying parts between assets; prefer a variant over a near-duplicate asset; prefer a theme over recoloring assets one by one.
5. After every edit: `npm run check`. It either passes or tells you exactly what to fix (with suggestions). Then read the SVG or screenshot the gallery to judge the result visually before declaring it good.
6. Add jitter only via `repeat.seed` — never invent randomness elsewhere; renders must stay diffable. In a sound, per-trigger variation is `jitter`, which the engine rolls and the bake ignores; everything else stays seeded.
7. Sounds follow the same rules one table over: author pitches from `tokens.audio.pitch`, name voices for what they are, prefer `use` over copying, prefer a variant over a near-duplicate. You cannot hear what you wrote — read the measurements `npm run check` prints, and get a human to listen before declaring it good.

## Roadmap (v0.x)

- ~~FX verb catalog~~ → `fx.slash/impact/ring/burst/muzzle` shipped; still to port: ghost (needs entity silhouette at runtime — adapter-level), damage_number (needs a text primitive)
- ~~Engine adapters (Phaser, Godot)~~ → shipped in `adapters/`; next: wire into vamp_surv / godot_test for a live side-by-side
- ~~PNG rasterization + regression~~ → shipped (`png` / `baseline` / `regress`)
- Per-instance motion vectors for `repeat` scatter (true radial bursts instead of uniform scale)
- Part libraries beyond `lib.face` (hands, crowns, telegraph markers); named particle-emitter presets
- Palette lint: flag near-duplicate hex across tokens; gradient support in adapters (currently flat mid-color fallback)
- ~~Sound: schema, offline bake, WebAudio adapter, the SFX set~~ → shipped; 20 documents in `sounds/`. Still to do: re-author the placeholder gestures now that they can be heard side by side, spectrograms and a sounds tab in the gallery, panning, a Godot path (offline WAV rather than a live graph), and the adaptive score's *materials* (the score itself is a scheduler and stays in the game)
