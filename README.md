# PolyGraphics

An **AI-legible procedural asset system**: game visuals *and sound* as declarative JSON documents, rendered deterministically against a design-token set. Born from auditing two shape-art games ([docs/reference-analysis.md](docs/reference-analysis.md)) whose visuals were imperative draw code — unreadable, unvariantable, unpreviewable. PolyGraphics inverts that: **an asset is data you can read, diff, patch, validate and render in isolation.**

```bash
npm install
npm run check     # validate + render all + gallery + manifest — the one command you need
open out/gallery.html
```

Working on art? Leave the gallery open and run `npm run watch`: a save rebuilds, and the page reloads itself without losing the tab, the search or the asset you had open.

The same gallery is hosted: Vercel runs `npm run site` on every push (`vercel.json`), so `main` serves the current library and every pull request gets a preview link of its own — the place to look at a new document from a phone, or to send someone a card.

## The loop

1. Write/edit an asset document in `apps/<app>/assets/<id-with-dashes>.json` (or a sound in `apps/<app>/sounds/`)
2. `npm run check` — errors come back with suggestions ("unknown color token `$bloood` — did you mean `$blood`?"), or `npm run watch` to have that happen on save
3. Inspect `out/gallery.html` — tabs per category, search across all of them, and a page per asset. Sounds are in the same page under their own heading: cards you can play, a detail view per document, and a "the set" tab that puts every level side by side
4. Iterate

The per-asset page is where a change gets discussed: the render big, at any zoom, on the ground colour it will actually sit on, or flattened to a silhouette — beside the parts in draw order with their ids, token fills and transforms. Naming `fang` beats pointing at a tooth, and **copy brief** puts exactly that on the clipboard for a chat.

Renders are **byte-identical across runs** (seeded scatter, no wall-clock anywhere), so SVG diffs are meaningful and visual regressions are testable.

## Layout

```
tokens/base.json          what is physics rather than identity: ramps, stroke widths, alpha, the
                          structural greys, and under `audio` the ladders every app shares
apps/<id>/app.json        the app's manifest: its premise, categories, reference floors, and the
                          RULES its art is held to (see "Apps" below)
apps/<id>/tokens.json     the app's palette, grid, layers, pitch palette and loudness families,
                          laid over base; a theme lays over that
apps/<id>/themes/*.json   partial token overlays (e.g. ice.json) — restyle the app at once
apps/<id>/assets/*.json   asset documents, one per asset, id `<id>.<category>.<name>`,
                          filename = id with dots→dashes
apps/<id>/sounds/*.json   sound documents, same naming rule
apps/<id>/baselines/      accepted PNG and WAV bakes; `npm run regress` diffs against these
core/assets/*.json        shared library documents, base tokens only (none yet)
adapters/phaser|godot     one drop-in file per engine, consuming compiled IR
adapters/webaudio         the same, for sound
src/                      schema (zod) · app-schema · apps (the loader) · token resolver · SVG renderer
                          compiler · lint · rules · gallery · cli · sound-schema/compile/render
scripts/                  watch (rebuild on save) · site (the gallery as a static site) · inspect · filmstrip
                          inspect-sound · readability · compare · adapter and lint tests
dist/<id>/assets.json     committed: the app's bundle, imported as `polygraphics/apps/<id>/assets`
dist/<id>/sounds.json     likewise, as `polygraphics/apps/<id>/sounds`
dist/assets.json          the union of every app, `polygraphics/assets` — what the current consumer imports
out/                      generated, ignored: svg/, compiled/, png/, wav/, gallery.html, manifest.json
site/                     generated, ignored: the gallery as Vercel serves it (index.html + wav/ + spec/)
docs/                     reference-analysis.md — why this exists · app-design-systems-plan.md — one grammar, a convention per app
```

## Apps

An **app** is whatever consumes a bundle: one game, one launcher, one screen. It is a directory under
`apps/`, and the directory is the namespace — every document it holds has an id starting with `<id>.`, and
its bundle is `dist/<id>/`. `apps/ss/` is the Shape Survivors roster; `apps/demo/` is the worked examples
this README draws on, and the template for the next app.

An app owns its **palette** (`tokens.json`, over `tokens/base.json`), its **categories**, the **floor** its
art is judged on and the **scale** it is seen at, its **clip and state vocabulary**, its **sound families**
and its **key**. It does not own the grammar: the schema, the shapes, the renderer and the adapters are the
repo's, and an app narrows them and never extends them — whoever can author for one app can author for the
next.

The manifest is where a convention stops being a README sentence. `apps/ss/app.json` states, as `rules`:

| rule | what it says for `ss` | how `check` holds it |
|---|---|---|
| `grid` | canvases in these categories sit on the 4px grid | a warning on the ones that don't; terrain props and shots are placed, not tiled, so the rule does not reach them |
| `size` | icons, relics, characters and draughts are 32×32 | a warning on any other size |
| `meta` | every enemy body, character and figure carries `meta.radius` (a shot, tagged `projectile`, does not) | a warning on the one that forgot |
| `clips` | every enemy body carries a `death` clip | a warning on the one that forgot |
| `oneShot` | nothing in a `death` moves after `t = 0.85` — arrive, then hold | a warning naming the track still moving |
| `states` | the variant vocabulary per category: `elite`, `enraged`, `final`… on an enemy, `evolved` on an icon, `glyph` on a relic | a warning on a state nobody listed |
| `roles` / `paint` | `hive` is `$pheromone` and `$pink`; projectiles and weapon icons never paint with it, but the lure | a warning naming the token and the document it came through |
| `distinct` | the weapon icons' tiles sit at least ΔE2000 13 apart | a warning naming the pair |
| `contracts` | `ss.proj.ring` keeps `meta.radius` 62, and three more the game divides by | an **error** — the game cannot see a broken one |
| `layers` | which `tokens.layers` depth each category draws on | `out/manifest.json` carries `layer` and `depth` per entry |
| `audio.key` | fanfares play only the score's degrees | a warning on the note outside them |

A document steps outside a rule *in writing*: `"why": { "size": "…" }` on the document, keyed by the rule,
and the rule leaves it alone while the gallery lists the exception with its reason. That is `offBand` on a
sound, generalised — the exception reads as a decision somebody made rather than a warning everybody learns
to scroll past. Rules are warnings unless the manifest's `levels` says `error`; the app decides how hard
its own rules are.

The gallery has a page per app for this: the premise, then every rule with how many documents it holds
over, who breaks it, and who stepped outside it and why; the palette grouped by role; and every sprite
viewable on the floor the manifest names, tiled behind it at the sprite's zoom. The rule kinds are a closed
set with a schema (`src/app-schema.ts`); a new *kind* is a PR to `src/rules.ts` with a lint and a message
that names the fix, a new *instance* is a line in a manifest. `scripts/test-lints.ts` fires every rule on
an app built to break it and checks that each one holds over the roster.

Adding an app is `apps/<id>/app.json`, `apps/<id>/tokens.json` and one document; `npm run check` renders
it, lints it against its own rules and nobody else's, and writes `dist/<id>/assets.json`, with no edit to
`src/` or `scripts/`. The plan this came from, and the decisions still open, are in
[docs/app-design-systems-plan.md](docs/app-design-systems-plan.md).

## Design loop

```bash
npx tsx scripts/inspect.ts ss.enemy.imp ss.enemy.bat --anim   # open out/inspect.html
npx tsx scripts/sheet.ts ss.figure.dot --anim walk            # out/sheet/ss-figure-dot--walk.png
```

Renders each asset **big** (judge the form), **at true game scale on the real ground color** (judge whether it survives the size it is actually seen at), and **as a flat silhouette** (if two enemies are indistinguishable in black, colour is doing work that shape should be doing). This is the loop the Shape Survivors redesign was built in — it caught a chaser that read as facing backwards, two antennae that overlapped into one, and two creatures that were the same cream colour.

A body drawn on a skeleton carries it (`skeleton`: named joints and the bones between them — see `docs/character-rig-guide.md`), and the gallery's detail view has a **skeleton** toggle beside *silhouette* that draws the joints, by name, over the parts; `inspect.ts --skeleton` does the same on the inspect page. It is the scaffold the parts were placed from and never reaches a bake, and it is what a change is asked for in: "`shoulder_near` a pixel lower", not "the sleeve".

`sheet.ts` is the same loop for a clip: one PNG per asset with the base render, the silhouette, two game-scale copies, and then the animation **posed frame by frame the way the engine adapters pose it** — offsets in the parent frame, rotation about the part's own origin — so a leg hinged at the hip or a ball on a chain can be judged without a browser. It also prints the rendered bounds against the canvas, because a feeler that crosses the edge is invisible in the SVG and a hard cut in the bake. It is how the survivors' walk cycles were tuned, and it caught a chain that let go of the hand mid-stride.

`motion.ts` is the number under that picture: it poses a clip the same way, rasterises every frame at the scale the game draws it (1.2 by default), and reports how far the silhouette's furthest edge travels across the loop, in screen pixels. A clip whose keys look busy can still move a pixel on screen — a tail swaying five degrees about each segment's own centre, a leg swinging four — and this is where that shows up before anyone plays it. The walks that read sit at 8px and up; the Salt Pan roster's loops measured 3–5 when the Stinger was rebuilt on a rig (`scripts/stinger.py`) and went to 9.

```bash
npx tsx scripts/motion.ts ss.enemy.stinger ss.enemy.courser --all   # every clip of each
npx tsx scripts/motion.ts --match ss.enemy.                          # the whole roster, first clip each
```

A body that has to move like a body is drawn on a skeleton rather than placed part by part: `scripts/rig.py` holds the bones, forward kinematics, two-bone IK for legs that stay planted, a chain solver that takes a pose as a place and a bearing (the Stinger's aimed hook, the Hurler's throw), and the solve from pose functions to the flat per-part tracks a document carries. Every Salt Pan body has its generator beside it (`scripts/<name>.py` → `apps/ss/assets/ss-enemy-<name>.json`, deterministic, one command each); change the script and rerun it rather than editing the document.

## Asset document

```jsonc
{
  "id": "demo.enemy.imp",             // dotted: app, then category, then name
  "name": "Imp",
  "description": "Small aggressive melee chaser: …",   // REQUIRED — legibility is the point
  "tags": ["enemy", "melee", "small"],// tags[0] = gallery category
  "size": [32, 32],                   // canvas px (multiple of grid, else warning)
  "anchor": [0.5, 0.5],               // optional; origin of the coordinate system
  "meta": { "radius": 9 },            // optional sim-facing hints; manifest adds derived radius
  "parts": [ … ],                     // NAMED parts, array order = draw order
  "variants": { "elite": … },         // declarative patches
  "animations": { "idle": … },        // keyframe tracks per part
  "skeleton": { "joints": { "shoulder_near": [-4.8, -3] }, "bones": [[…]] }  // optional: what the parts hang from (bodies)
}
```

**Coordinates:** origin at the anchor, +x right, +y down, px. Parts place themselves with `at`.

### Parts

Every part has an `id` (snake_case — variants and animations address parts by id), and optionally `at`, `rot` (deg), `scale`, `opacity`, `mirrorX` (draw a second copy mirrored across the vertical axis — build symmetric features once). A part is one of:

| form | keys | meaning |
|---|---|---|
| shape part | `shape`, `fill?`, `stroke?` | draw a primitive |
| use part | `use: "demo.lib.face"`, `variant?` | compose another asset document in place (shared parts, single-source icons; cycle-guarded, depth ≤ 4). `variant` picks a state of the used document, so one library part can appear in several conditions across the roster |
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

Stroke widths and opacities likewise take token names (`"width": "thin"`, `"opacity": "soft"`). A stroke is laid **under its own fill** (`paint-order: stroke`), so only its outer half shows — `thin` (2) is a one-unit rim outside the shape. The SVG renderer and both engine adapters draw it that way; the adapters used to draw it over the fill, which put the other half inside the shape in play and made every outline in the game twice what the gallery showed. Raw `#hex` renders but warns with the nearest token. **A theme is just a token overlay** — `apps/ss/themes/ice.json` swaps warm hues for cold and every asset restyles coherently, silhouettes untouched.

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

**A hinge is not a prop.** The schema turns a part about its own origin, which is the right primitive and the wrong verb for a leg: a femur and a tibia each turned thirty degrees about their own centres stay parallel and drift apart, so the leg comes to pieces instead of folding. A chain turned about one joint is equal `rot` down the chain *plus* the `x`/`y` each link's offset from that joint sweeps — `ss.enemy.trapjaw`'s `latch` is the worked example, and every `death` clip in the roster is built the same way.

**Scope: animations move parts within a body, never the body itself.** A part's `rot` turns it about its own origin, so a whole-asset spin cannot be written as one track per part — and shouldn't be. Whole-body transforms (spin, facing flip, knockback, hit-flash tint) belong to the engine, which already owns them; `ss.proj.boom` therefore declares no spin animation, because the weapon code does `sprite.rotation += spin * dt`. Keep the two layers separate and neither can fight the other.

### `death` — a clip name the roster agrees on

Every `ss.enemy.*` document that is a body carries one — `ss.enemy.shot` is a bolt, not a body, and carries no animation at all — so a consumer can ask for a creature's death without a table mapping creature to clip name. It is a one-shot rather than a loop, and three things follow from that:

- **Nothing moves after `t = 0.85`.** A sheet's last frame is sampled a frame short of the end (`bakeSheet` walks `f / frames`, so the loop closes), and a clip still travelling there is a clip the engine cuts off mid-gesture. Arrive, then hold.
- **The body is the engine's.** A death fades, sinks and stops colliding in the game; what the document owns is the *coming apart* — limbs folding, a shell deflating, a lit organ going out.
- **One grammar, nineteen readings.** The seize (a kick, an organ flaring) through the give (limbs in, jaws hanging, the light going) to the settle. A hive that loses nineteen bodies should not look like nineteen effects — so what differs between them is what each creature *is*: the Gland's sac goes before the animal does, the Trapjaw's latch fires once on nothing, the Chorus runs the light round the ring one last time, and the Bristle — the one body down there that is not hive — dies like an insect rather than like a light going out.

```bash
npx tsx scripts/filmstrip.ts ss.enemy.imp death --frames 8 --scale 4   # → out/strip/…png
```

The gallery plays a clip as CSS, which is the right loop for a loop — you watch it breathe. It is the wrong one for a one-shot: a death is judged on whether frame 3 still reads as the same creature and whether frame 9 has stopped moving, and both questions want the frames side by side and still. `filmstrip` bakes them that way, on the ground colour, sampled exactly where the spritesheet will sample them. `--variant elite` checks the state the game actually spawns.

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
| — | `phrase` — one instrument played at a row of pitches (no visual twin; see below) |
| — | `unison`, `echo`, `takes` — width, space and variety, each compiled to plain voices |

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
do. `apps/<id>/themes/*.json` may overlay the `audio` section too, so one overlay restyles
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

**`adsr` is the one envelope written in seconds.** Keys are fractions of a span,
which is right for a trajectory — a slide between two pitches is the same slide
however long it takes — and wrong for an attack. A struck note reaches its peak
in about ten milliseconds whether it lasts a tenth of a second or two, so an
instrument written with a proportional attack stops being that instrument the
moment somebody plays it longer. `{ "prop": "gain", "adsr": { "attack": 0.012 } }`
is expanded into the keys you would have written once the voice's final length
is known, so the IR never learns it existed. Before it did, `ss.sfx.chime` said
`0.017` in one voice and `0.013` in the other to mean 12ms in both.

**An envelope on a scatter belongs to the gesture, not to each grain.** A dry
crack is bright grains first and dull grains last — one sweep across the whole
scatter, not the same sweep five times. The compiler cuts the envelope into
per-grain windows so the IR stays a flat list of voices and no adapter has to
learn what a bus is.

**Library documents are instruments, and `root` is what says so.** `ss.lib.note`
is one note of the flat square voice, written at `$third` and saying as much;
`ss.sfx.levelup` and `ss.sfx.victory` are that document composed four and six
times with a `pitch` on each use voice picking the degree, and `dur` refitting it
to a slower step. `ss.lib.knell` is its low sawtooth twin and `ss.sfx.gameover`
walks the same ladder down it.

The degree therefore lives at the call site, next to the melody, rather than as a
named variant inside the instrument — a fanfare can reach a note nobody
anticipated without editing the thing that plays it. `pitch` is an absolute
pitch and not a ratio, for the same reason every other slot takes a token:
`"pitch": 1.26` is a bare number nobody can read, and `"pitch": "$fifth"` is the
note it plays. Playing a document that declares no `root` is an error rather
than a guess, and a `root` nothing composes is a warning, exactly as an unused
palette token is.

Retune the library and every figure built on it moves together — the exact
`ss.lib.organ` argument, and `scripts/test-webaudio-adapter.ts` asserts it by
retuning the note in memory and checking that both fanfares follow while the
knell-based one does not.

**Four more things compile away, and the IR never learns they existed.** Each
is the relationship `to` has to a `freq` track: a shorthand for voices you could
have written, so the renderer and all three adapters are untouched and the
bundle stays `polygraphics-sounds@1`.

- **`unison`** on an oscillator: `{ "count": 2, "detune": 7 }` is the voice
  twice, seven cents either side of its pitch, each at 1/√2 of the level.
  Width — what the game's own pad is made of. A glide detunes with each copy;
  a filter stays where it was.
- **`echo`** on any voice: `{ "time": 0.42, "feedback": 0.32 }` is the voice
  again at `time`, `2·time`, `3·time`… each tap a third of the last, until one
  would sit under −40dB or `taps` is reached. Space, flattened into voices —
  the pluck's feedback delay without a bus in the IR. A tap that would start
  past the canvas is dropped and said so; one that runs past it is cut there.
- **`phrase`**: `{ "use": "ss.lib.note", "step": 0.09, "notes": ["$third",
  "$fifth", "$seventh", "$third.up"] }` is the four `use` voices it stands for,
  one every `step`, each at the pitch named; `null` is a rest, `dur` refits
  each note. `ss.sfx.levelup` is that one voice; its tempo is one number. This
  is the one construct with no twin on the visual side — time carries an
  ordering space does not — and the schema header says so.
- **`takes`** on a document: `"takes": 3` bakes it three times, every noise
  and scatter reseeded and its `jitter` rolled once by a seeded rng and
  frozen, as variants `take-2` and `take-3` for the engine to round-robin. A
  `hit` on the buffer path is otherwise one buffer with a rate roll — the same
  grain pattern three hundred times a run, slightly transposed. Each take is
  a baseline like any other. A take that comes out identical to the base is
  told so: nothing in the document was seeded or jittered.

`meta` is an open record of sim-facing numbers, and two more hints ride there
by convention: `polyphony`, how many of this may sound at once, and `duck`,
the dB the score should drop while it plays. The engine reads them the way it
reads `minInterval`.

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
- **the spectrogram** under every waveform — log frequency, 60Hz to 16kHz, an
  octave the same height everywhere — is the picture the waveform cannot draw:
  a pitched voice is a comb, noise is a wash, and an empty top half is what a
  phone will hear of it. `out/spec/*.png`, one per take, and the manifest
  points at them.
- **phone**, a toggle beside the sound tabs, puts a 250Hz highpass and an 8kHz
  lowpass between every transport and the output — roughly what a small
  speaker keeps. Most of what is wrong with a sound in this set is only wrong
  there.

The gallery links `out/wav/` rather than embedding it — twenty-seven takes of
base64 would add ~3MB to a page that reloads itself on every rebuild — so every
command that writes the gallery writes the bake too.

```bash
npm run check                                          # everything, gallery and bake included
npm run wav                                            # just the bake, and print what it measures
npx tsx scripts/inspect-sound.ts                       # a standalone, self-contained page to send someone
npx tsx scripts/inspect-sound.ts --against baselines   # …with every take beside its accepted one
```

The inspect page is the shareable export: takes embedded, no server, opens
anywhere. Pass ids to narrow it (`… ss.sfx.hit ss.sfx.creak`). With
`--against baselines` each take sits beside the WAV in `apps/<id>/baselines/sounds/`
with one transport for both and an **A/B** button that plays them back to
back, so a re-author is judged against what it replaces at the same level,
and the numbers beside it say what moved. That page, and the four questions
in [docs/listening.md](docs/listening.md), are how a change gets listened to.

That page exists because the rest of the system leans on rendering something and
looking at it, and **an agent authoring these documents cannot listen**. So the
bake is also the instrument. `describe()` measures every take, and `npm run
check` lints on what it finds:

- **loudness** — K-weighted (ITU-R BS.1770) level over the sounding extent, not
  the canvas, because a sound that ends early is shorter, not quieter. RMS says
  how much signal there is; this says how loud it is.
- **family bands** — `audio.loudness` in the tokens names an `anchor` and an
  offset per family (`tags[1]`): a `field` sound sits above an `impact` sound
  and the lint knows it, rather than being told per document. Anything more
  than `band` dB off its family's place is flagged. `offBand` is for the one
  document that is off *its family's* band on purpose.
- **the phone** — the loudest 50ms, before and after the same 250Hz–8kHz
  filter the gallery toggle plays through. Past `phoneLoss` dB the low end is
  carrying the sound and a small speaker gets nothing.
- **true peak** — four times oversampled; a bake that reads −0.3dBFS sample by
  sample can pass 0dB in the DAC.
- **attack** — milliseconds from the onset to 90% of peak. Anything but an
  impact that reaches its peak inside the renderer's 1.5ms declick has no onset
  of its own, and is told to write one.
- **unfiltered square or sawtooth** — every harmonic to Nyquist, the one
  timbre this set had in two waveforms. Read off the document; a voice keeps
  one on purpose by saying `why`.
- plus clipping, near-silence, the spectral centroid and the low / mid / high
  split, and the −60dB tail, all in the manifest for an agent to read before
  it writes.

Attack is measured from the onset rather than from t=0, so a voice that starts
late reads as fast rather than as slow; it is the one property an instrument has
to hold while it is played at four different lengths, and the property a
proportional envelope cannot hold.

A document may state, in writing, why it belongs outside its band — `offBand`
— for the cue whose whole job is to sit under the cues it shares a frame with,
and a voice may say `why` it keeps a raw sawtooth. The exception then reads as
a decision somebody made rather than a warning everybody learns to scroll past.

It earns its keep immediately: porting the sibling project's set, the first
version of the lint put `whoosh` 17dB under the median. Not a transcription slip — the original gave a
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
| **authoring documents** | `apps/<id>/assets/*.json` + `app.json` + `tokens.json` + `themes/`, over `tokens/base.json` | humans and AI agents (the only thing you edit) |
| **compiled IR** | `out/compiled/*.json` (+ per-theme) | **game engines** — tokens resolved to `[r,g,b,a]` floats, variants pre-applied, `use` inlined, `mirrorX`/`repeat` expanded, ngon/star → concrete points. Engine adapters are dumb interpreters; no token/grammar/PRNG logic ships to the game |
| **the bundle** | `dist/<id>/assets.json` per app, and `dist/assets.json` the union, via `npm run dist` | the same IR as one file keyed by asset id — what a consuming game imports as `polygraphics/assets`. Committed, unlike `out/`, because it is the thing that leaves the repo |
| **previews** | `out/svg/*.svg`, `out/gallery.html` | humans and AI agents (inspect/iterate; CSS animations play in the gallery) |
| **bakes** | `out/png/*.png` (4×) via `npm run png`, `out/wav/*.wav` via `npm run wav` | any engine as plain images or audio files; also the regression baseline. `npm run png -- --only <id> --size <px>` bakes one document at an exact pixel width instead — for the places outside an engine that want a file at a size they name, a web app manifest's icon plates being the first of them |
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
import { bakeFlat } from "polygraphics/phaser";     // the adapter: zero deps, zero engine imports
import bundle from "polygraphics/apps/ss/assets";   // { format, assets: { "ss.enemy.imp": IR, … } } — one app's art
import all from "polygraphics/assets";              // the union of every app, which is what the game imports today
```

An app imports its own bundle. The union stays until the consumer has switched — and it switches first, then
the union goes; never the other way round.

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

**Level 1½ — drawn live (Phaser).** The document solved as geometry into a `Graphics` every frame, for an effect whose size is not known until it happens — a burst scaled off a radius the run decides. A bake is a picture at one resolution and blurs when it is blown up; this is re-solved at the size it is actually drawn:

```ts
import { drawAsset } from "polygraphics/phaser";
g.clear();
drawAsset(g, burstIR, { x, y, scale: r / 30, rotation, animation: "play", progress: t / 0.36 });
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
npm run baseline   # accept current bakes as reference (commit apps/<id>/baselines/); --app <id> for one app
npm run regress    # byte-compare current PNGs and WAVs against baselines; exits 1 on change
```

Because rendering is deterministic, a one-digit token drift (the `ff9b3d` vs `ff9d3c` class of bug) fails regression on exactly the assets that use that token. Sound rides the same rails: every source of randomness is a seeded PRNG carried in the IR and there is no wall clock anywhere, so a bake is byte-identical run to run and a WAV diff means somebody changed the sound.

`npm run check` also lints the palette: a colour token nothing references is reported as dead (drop it or use it), and a theme overriding a token that no longer exists is an error, not a silent no-op.

## Worked example: the Shape Survivors roster

`apps/ss/assets/` is the full roster of the sibling project, first transcribed 1:1 from its `BootScene.ts`, then re-authored around one sentence of fiction: **the protagonist has lost their pheromone transmitter, and the hive hunts them for the silence.** `npx tsx scripts/compare.ts` builds `out/compare.html` — 39 before/after pairs.

What the system contributed that imperative draw code could not:

- **`ss.lib.organ`** is the premise as a single document. Enemies compose it lit; the eight player characters compose the *same document* with `variant: "dead"` — cracked, unlit, silent. Change that one file and every creature in the game changes together. Verified to diverge correctly in both the Phaser and Godot adapters.
- **Two survivors drawn as people, alongside the shells.** The eight `ss.char.*` shells are the game's characters and are untouched. `ss.figure.dot` and `ss.figure.tri` are a second set, drawn one at a time as the same survivors seen up close: not eight geometric shells but bodies with clothes and a story on them, each its own document rather than a template, with the head authored large in its own document (`ss.lib.dot-head`, `ss.lib.tri-head`; Dot's boot in `ss.lib.dot-boot`) — gradients for the materials, sixty to eighty parts each — and composed in by `use` at a fraction of its size, so a component can be judged at the size it was drawn and still land at the figure's. Dot is a hooded figure in dark leather and wool, no skin showing, with two dead feelers hanging from the crown of the hood to the belt. Tri is what the hive's work costs: a belly grown into a sac that hangs like a drop under a white gown stained with acid, the jaw and throat ballooned into one mass, tumours through the skin, bare swollen feet in sandals, the whole upper body thrown back at the hips to carry it. Both animate through a joint chain from the hips out — a rock of the upper body carries shoulders, arms and head with it, and the knee bend keeps the shin on the thigh — and both were tuned with `scripts/sheet.ts`. They are not wired into the game; that is a separate decision, starting with size (Dot is 47 px tall against the shell's 28 and the game's hit circle of 11).
- **Silhouettes carry identity**, so the roster survives the flat-silhouette test: a low six-legged Tracker, a swept-wing Drifter, a lopsided Husk, a split-open Molt, a plated Soldier. In the original, all seven were the same convex blob in different hues.
- **The Salt Pan's household is eleven bodies, and each is the shape of what it does.** The game's third stage is open ground where most of the roster does not need to reach you, so every document there is drawn around its one verb: a Locust is a hind leg, an Antlion is two jaws standing out of a mound (`buried`, and `elite_buried` because a variant is a patch on the base and the game cannot stack two), a Burr is a star of spines that leave it when it dies, a Hurler carries a Mite over its back (`use: ss.enemy.imp` — the load is the shot), a Bombardier is a wedge with a mortar on it, a Stinger is a tail arched over the body that `aim` straightens along +x, a Blister holds its elytra open, a Sower carries three `ss.enemy.tick` under its abdomen, and the bosses are a ring of stones (Hail), a tiger beetle at full stride (Forerunner) and a hole in the ground with jaws in it (Sinkmaw). Seven shots for seven verbs, and a floor (`ss.env.pan`, on a new `$sand` token) with salt plates, a ribcage, fissures and fused glass to stand on it. All of it generated from a script of two-link legs and hinged chains, which is why the walk cycles agree with each other.
- **The Courser is a wolf spider, because it stopped being a line.** The field's second boss was a ringed worm that braced and crossed at you, and the burrow's second (`ss.enemy.scolopend`) was drawn on the same rig to run the same machine — two maps, one fight, two segmented lines. The game now has it read the air and *run a ring* round where you are going, fencing it with its own reek, so the body is redrawn for that and nothing else: eight long legs (the one eight-legged body in the hive) splayed round a small carapace, a hair-fringed abdomen whose heart mark and chevrons point the way it runs, two big eyes over a row of four, and the hive's organ riding the spinnerets rather than the head — the thing that lays the fence is the thing that says who it is. Built by `scripts/courser.py` on a skeleton of hips, knees, ankles and feet, so every clip turns joints and no swing can part a leg (`trot`, `read`, `run`, `death`, the last the curl a spider dies in; and for its second verb, hunting by vibration, `listen` — every leg flat on the floor, only the front pair tapping — and `pounce`, the lunge onto where it last heard a footstep). The hair is an uneven seeded fringe swept back toward the spinnerets, because an even ring of points is a cog. `enraged` turns the values over — dark body, burning pattern, the hair standing — and `final` has run out: bald, the abdomen emptied pale, a leg gone from each side and the organ white. Against the field floor it sits at 2.9:1, where the worm sat at 2.1.
- **The pan's floor is sand now, and the tile stopped showing.** The first `ss.env.pan` was dark umber under a lattice of salt cracks, which is a fine drawing and a bad tile: the cracks met at the edges and the four black pits repeated, so 128px of it read as a hex grid the moment the game laid it end to end. The rework is the same ground with the sun on it — `$sand` lifted about a stop and a half, and the surface rebuilt as fine sand: five seeded grain passes under wind ripples (shallow arcs banded at -13 degrees, each a wide lee band with the lit face inside it), dune swells in concentric steps because the Phaser bake flattens a gradient, salt bloom where the crust still shows, and two shallow antlion dishes instead of the pits. It tiles on a torus: every part whose bounds cross an edge is emitted again 128px over, so nothing is clipped away at a seam and no grain-free margin frames the tile. Where it stops being brighter is a number, not a taste — `scripts/readability.ts` against `ss.env.pan` rather than the field: past this the pan's own mid-brown roster starts to sit at the floor's tone, and the survivor falls under 3:1 against it.
- **Each stage got a card, and the menu stopped building its own.** `ss.env.stage-den`, `ss.env.stage-burrow` and `ss.env.stage-pan` are the pictures on the game's map-select page. It used to assemble them out of the run's parts at runtime: the field and the pan tiled their floor and stood six props on fixed fractions of the strip, and the burrow ran its real generator into a dynamic texture on every window resize. So the props were placed by fraction and sized by a factor with no bake resolution divided out, which stood a spire off the top of the card and over the name; the floors were 128px tiles shown at 1:1 on a screen rendering at devicePixelRatio 2; and six props on a cycle of two species at six fixed spots is a scatter, which is the one thing the run already gives you. A card is a drawing now — composed, out of each stage's own inks and its own `use: ss.terrain.*` props, so it is still the stage it advertises. The burrow's is the lattice the generator makes, hand-placed: sixteen corners with the outer ranks off the canvas, a doorway cut through each leg of earth, two walls out altogether, and the run's own two-pass draw (every contour, then every fill) so no mass outlines the one beside it. All three are authored 3:2 and the consumer covers its strip with them, so the composition carries its weight off the middle and lets props run off the flanks.
- **Variants are real states**, not scale × tint: `ss.enemy.brazier#spent` is the destroyed relay, `ss.enemy.boss#enraged` splits the shell open, `ss.pickup.chest#cursed` puts something awake inside.
- **`apps/ss/themes/ice.json`** restyles the entire redesigned roster — chitin to blue-grey, pheromone to a cold signal — without touching a silhouette.
- **The arsenal follows a second rule**: player weapons are hive material with the signal stripped out — chitin, husk bone, molt shell, honed to a cold frost edge, and never magenta. A lash is a Soldier's mandible on a cord; the thrown card is a Drifter's wing on a bone frame. Two break it and both break it on purpose, being alive rather than cut from something that was: The one place the hive's colour touches the player is `ss.fx.pickup`, the half-second of borrowed voice when a lump of pulp is absorbed. `ss.proj.mine` is a lure, a pink fruiting body calling the hive to the spot it is about to detonate, and a trap that nothing walks near does nothing — bait in the player's hand rather than the player's voice, which is why it sits on the ground instead of being carried. And `ss.proj.drone` is a brood vent, which the arsenal's own materials cannot draw: bone and chitin are what a body leaves behind, and this one has to look like it is still working.
- **The broodling is a body now, not a plate with a hole in it.** `ss.proj.drone` had been three hexagons inside each other since the day it was recoloured out of a shell plate, which is a pucker the way a bolt head is one — and a shape with no body in it has no animation in it to find, so its whole idle was the middle hexagon revolving. It is drawn out from the closure now: a mound of skin off three harmonics, a socket sunk into it, the everted flesh standing in the socket, ten folds swirling out of the opening and on over the skin, and the gut the grubs come from hanging under it in the same skin shaded rather than in a darker colour. Nothing is centred and nothing is even, because a vent centred in its own mound with even folds around it is a badge. It carries two clips where it carried one: `hum`, the idle, where the pucker works round one fold at a time and the gut fills against it; and `lay`, one grub leaving — the draw in, the closure thrown wide, a pale bead over the lip, the clench behind it, and the next one rising in the throat. `meta.layCue` is what makes that last one a contract rather than a flourish: it is the share of the clip the bead leaves on, so the consumer releases the real grub on that frame and the bead and the grub are never both on screen. The folds are also what keep it from reading as an eye — they stripe the flesh instead of leaving a clean bright disc round a dark dot — and measured against the field's floor the redraw takes it from 2.03 to 2.50, which is exactly the line this app draws under a body and is where it stays: what holds it there is a hair of ink all the way round and a centre that has to be a hole.
- **Weapon icons compose their weapons.** `ss.icon.wand/whip/boomerang` `use` `ss.proj.bolt/slash/boom` directly, so the original's five-shapes-authored-twice problem cannot recur. `evolved` goes gold on the rim, and where the evolution changes what the weapon *does* it also changes the glyph — still composed, never a second drawing: the Lash's crescent closes into one tapered swoosh most of the way round (drawn in the slot, since the slash is a 200° cut and the evolution is the whole turn), Dancing Mandibles two jaw pairs pinwheeling through `ss.fx.gust`, the Vine the thicket it plants, the Spider Hand the widow's arm.
- **A weapon icon's rim is that weapon's own colour.** Lash `$white` (bone, bleached), Glob `$bile` (acid), Mandibles `$chitin` (jaw amber), Lure `$pink` (cap), Broodling `$blood` (vent), Chirp `$frost`, Dung `$timber`, Wing `$arcane`. The rims had drifted — three documents claimed to keep a hand-drawn original's colour, and two of those originals no longer existed — so each now takes a colour that is actually in the art it wraps. The arsenal is deliberately four shades of one material, which fights this: Lash, Mandibles, Pod and Dung are all bone or chitin or timber, and a rim drawn from the dominant colour of each would put four slots within ΔE2000 13 of one another. So two of them take the part of their art that nothing else owns rather than the part there is most of — the jaw's amber over the husk it is mostly drawn in, the muck's unlightened timber, which is the only ramp of it that clears chitin. The worst pair is 20.2, Mandibles against Dung, and it is the arsenal's own palette that sets that ceiling. `$arcane` on the Wing is ahead of its art on purpose: that weapon is being redrawn as a grenade thorn and going purple. `evolved` overrides all eight with `$gold`, the one rim that means a state rather than a weapon. `$pheromone` would be the truer token for a signal, and is the one the scent tokens in that art come from, but it lands 15.3 from the Wing's `$arcane` where `$pink` lands 21.3; the rim takes the cap's colour and the plume keeps the meaning.
- **The Spider Hand's rim is `$arcane.dark`, and an evolution passive wears its weapon's rim.** The Spider Hand used to share the wand's `$bile` (ΔE 0), then wore `$cobalt`, the arms' `$steel` with the grey taken out, until the Four-Leaf Clover that wears the same rim made a third blue on the passive bar beside Stink's `$frost` and the Wing trait's `$aqua.light`. `$arcane.dark` is the Wing blade's violet a step darker: 16.4 from `$arcane`, where the brighter violet tried first for Widow's Grip sat 8.5, and no passive is near it. The eight passives an evolution recipe needs (`ss.icon.cooldown`, `amount`, `speed`, `area`, `might`, `duration`, `maxhp`, `luck`) take their weapon's rim, so a recipe's two halves read as a pair on the slot bar. The glyph is painted in the rim's colour too, as every other passive's already was (`armor`, `movespeed`, `magnet`): a passive is one colour, tile and glyph, and that colour is its weapon's. Scab (`ss.icon.recovery`) follows the same rule with the Shell's `$smoke.light2`. The pale pair was the other collision on the bar: the Lash's `$husk` cream and the Shell's blued `$steel.light` sat ΔE 15.5 apart, so the Lash and Pulse Rate went to `$white` and the Shell and Scab to a neutral grey, 25.8 apart. Three more pairs followed. Feelers left Bloom's `$pink` (ΔE 0) for `$cobalt`, which no other passive wears now. Wing left `$aqua.light`, 9.4 from Stink's `$frost`, for `$spore`. The Vine and Bulk left `$sage`, 16.5 from the Spit's `$bile`, for `$venom.dark`. The closest pair on the passive bar is now 20.6, Plus One against Bulk.
- **The home screen is authored here too.** `ss.app.icon` is the game's installed icon: a Tracker — `use: ss.enemy.imp`, the hive's first responder and the thing on screen by the hundred, so it moves with the Tracker whenever that is redrawn — its organ lit in the middle of a frame washed pink by the hive's scent. Its `maskable` variant pulls the body inside a round mask's safe zone, because a launcher crops what it likes and a feeler tip is the first thing a circle takes off. It is the one asset that leaves as a *plate* rather than as IR: `npm run png -- --only ss.app.icon --size 512` (and 192, and 180), baked into the consumer's `public/icons/`, since a web app manifest wants files at sizes it names.
- **The game draws nothing of its own any more.** Every icon, terrain prop and creature it once drew in `BootScene.ts` is a document here; what stayed behind is the handful of things that were never art — a runtime-tinted particle, procedural noise canvases, damage digits. It consumes this repo as a package and keeps only the map from its texture keys to these ids.
- **One direction was drawn and declined.** `ss.draught.*`, `ss.lib.vial`, `ss.lib.vial-cap` and `ss.char.survivor` are a proposal: the eight playable shapes folded into a single body, with what a run varies moved into a draught drunk on the way in. The game kept its eight shells, so none of it is drawn anywhere. It stays in the repo, described and rendering, because a drawing is the only place an idea like that survives intact — and because nothing asks for those ids, nothing breaks by their staying. The eight `ss.char.*` shells are the live roster; **do not delete them to tidy the survivor up.**
- **Retiring art is two changes, in this order: game first, art second.** Learned the hard way — the eight shells were removed here while the game was still reading them by id, and nothing broke only because the consumer's pin had not moved, which is exactly what hid it. This repo publishes into a lockfile-pinned dependency, so an id that vanishes is live ordnance sitting in the next pin bump, and the pin gets bumped by whoever happens to want unrelated art.

`apps/ss/sounds/` is the same project's effect set, ported from the 569-line `switch` in its `AudioSynth.ts` — 18 effects plus the two library instruments they are built from. What the port bought:

- **The score's key reaches the effects.** The music runs an A-minor cycle; the arpeggios in the old code were four hardcoded floats that happened to be C major. They are now `$third $fifth $seventh $third.up` — four notes the music already plays — so a fanfare can never land outside the key it fires in.
- **Two figures, one instrument.** Level-up, victory and game-over were three separate note arrays; they are now `ss.lib.note` and `ss.lib.knell` composed with a degree per voice. The win figure and the loss figure are provably the same instrument in two moods, and retuning either is one file.
- **The dry crack is data.** `creak` was a hand-written grain loop with `Math.random()` in it, which is why it could never be regression-tested; it is a seeded `repeat` voice now, and its bake is byte-identical forever.
- **The set was measured, and one sound was wrong.** See the loudness lint above.
- **Levels come off a five-rung ladder** (`faint soft mid loud peak`) instead of sixteen ad-hoc floats between 0.14 and 0.5, so "make the interface quieter" is one token.

- Gameplay contracts held throughout: ids, body radii and variant slots are unchanged, so the redesign drops into the same code that consumed the faithful port. Three assets carry hard geometry contracts noted in their own descriptions — `ss.proj.ring` (`wave.r / 62`), `ss.proj.dung` (`r / 14`) and `ss.proj.aura` (`r / 64`, plus runtime tinting, so it stays neutral white). `ss.fx.dung-burst` carries a fourth, `burstR / 30`, which is the contract the barb burst and the spatter already keep.

## For AI agents

You are the intended primary author. Rules of the road:

1. Read the app's `app.json` first — its premise, its rules, its floors — then `tokens/base.json` and the app's `tokens.json`; author **only** with token references, and put a document in the app it belongs to (its id says which).
2. Every asset gets an honest `description` and tagged category — future sessions (and the manifest) rely on them.
3. Name parts for what they are (`pauldron`, not `rect3`); variants and animations address them by id.
4. Prefer `use` over copying parts between assets; prefer a variant over a near-duplicate asset; prefer a theme over recoloring assets one by one.
5. After every edit: `npm run check`. It either passes or tells you exactly what to fix (with suggestions). Then read the SVG or screenshot the gallery to judge the result visually before declaring it good.
6. Add jitter only via `repeat.seed` — never invent randomness elsewhere; renders must stay diffable. In a sound, per-trigger variation is `jitter`, which the engine rolls and the bake ignores; everything else stays seeded.
7. Sounds follow the same rules one table over: author pitches from `tokens.audio.pitch`, name voices for what they are, prefer `use` over copying, prefer a variant over a near-duplicate. You cannot hear what you wrote — read the measurements `npm run check` prints, look at the spectrogram, and get a human to listen before declaring it good. [docs/listening.md](docs/listening.md) says how, and what to ask them.

## Roadmap (v0.x)

- ~~FX verb catalog~~ → `fx.slash/impact/ring/burst/muzzle` shipped; still to port: ghost (needs entity silhouette at runtime — adapter-level), damage_number (needs a text primitive)
- ~~Engine adapters (Phaser, Godot)~~ → shipped in `adapters/`; next: wire into vamp_surv / godot_test for a live side-by-side
- ~~PNG rasterization + regression~~ → shipped (`png` / `baseline` / `regress`)
- Per-instance motion vectors for `repeat` scatter (true radial bursts instead of uniform scale)
- Part libraries beyond `demo.lib.face` (hands, crowns, telegraph markers); named particle-emitter presets. `core/` is where one goes once it paints with base tokens only
- Palette lint: flag near-duplicate hex across tokens; gradient support in adapters (currently flat mid-color fallback)
- ~~App design systems~~ → shipped, phases 0–4 of [docs/app-design-systems-plan.md](docs/app-design-systems-plan.md): `apps/<id>/` per app, a manifest whose rules `check` reads, per-app bundles. Still to do: the second real app (Cellspire is the candidate) with no edit to `src/`; the spider hand's own rim colour; dropping the union bundle once the game imports `polygraphics/apps/ss/assets`
- ~~Sound: schema, offline bake, WebAudio adapter, the SFX set~~ → shipped; 22 documents in `apps/ss/sounds/`. ~~Spectrograms, before/after, a phone to listen through, K-weighted loudness and family bands, `unison` / `echo` / `phrase` / `takes`~~ → shipped, phases 1–3 of [docs/sound-quality-plan.md](docs/sound-quality-plan.md). Still to do, in that plan's order: re-author the placeholder gestures one family at a time with a listening record, fill the seam (new documents, variants and takes played, panning on the engine side), a Godot path (offline WAV rather than a live graph), and the adaptive score's *materials* (the score itself is a scheduler and stays in the game)
