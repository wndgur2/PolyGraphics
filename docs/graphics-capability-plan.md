# Graphics capability: from shape art to the references' register

*2026-09-24. A design review: what PolyGraphics would have to become to draw frames at the level of two
references attached to the request — a painterly one (two stills from GRIS: a white ruin, a red
calligraphic bird-wing over it, light shafts, a flock) and a pixel-art one (three stills from Skul: The Hero
Slayer: two boss fights and a castle room). Reads the repository at #102. A second round added four more
references — see [More references](#more-references). Nine spikes in `scripts/spikes/` back the claims; they are
evidence, not system code, and nothing in `src/` or `adapters/` changed.*

*Status: proposal. Nothing below has landed. The decisions it needs from a person are at the end.*

**The short answer.** The ceiling is not the rasteriser. resvg — what `npm run png` already bakes through —
does every effect both references are built from, deterministically: curves with holes, blur, noise-displaced
edges, blend modes, masks, clip paths, patterns, morphological outlines, lighting filters, anti-aliasing off.
What holds PolyGraphics at shape art is two layers above it:

1. **The grammar cannot say those things.** Eight primitives with straight edges, one paint per part, no
   grouping but `use`, no blend, no material, and a ramp that walks toward black and white.
2. **The engine contract cannot carry them.** The IR is geometry that three interpreters redraw (SVG, Phaser,
   Godot), and the two engine ones already drop the one rich feature the grammar has: both render a gradient
   as its flat mid-colour, so 102 parts in 29 documents — the figures' heads, the boss — look one way in the
   gallery and another in the game. Every material added under this contract is added three times and
   dropped twice.

So: make the renderer the only interpreter of *appearance* and ship engines baked textures plus the IR's
structure (**bake-first**); extend the grammar in layers — geometry, groups with clip, **materials as tokens**,
hue-shifted ramps and **emission as a token**, a per-app **look** (vector / painterly / pixel), a **scene**
document, motion beyond transform tweens; and give the agent **instruments** for what it cannot see — a style
probe that measures a frame against a reference, and lints each look needs.

The spikes say this reaches the references' *register*: the painterly frame lands within 0.02 of the first
reference's mean value and on its mean chroma, and the pixel frame moved inside the second reference's chroma
range in one measured edit. They also say where it stops: renderer features do not supply composition or
shape design, and running a detailed vector figure through a pixel pass does not make pixel art.

---

## What the references are made of

Decomposed into what each element *technically is*, against what the repository can say today.

**Reference A — painterly.**

| element | what it is | today |
|---|---|---|
| paper and wash | every pixel sits on a fine grain; value drifts in large soft blotches | nothing: no texture, no blend |
| light shafts | long translucent bands, blurred, screened over the sky | nothing: no blur, no blend |
| clouds | soft-edged organic masses, lit on top, a shaded underside, wrapping the ruin's foot | `ellipse` stacks with hard edges |
| the red wing | one calligraphic mass: tapered strokes, loops cut through it as holes, a gradient across it, a ragged watercolour rim, loose flakes off the tip | `poly` (straight edges) + a gradient the engines flatten; no holes, no stroke profile, no edge treatment |
| the ruin | pale flat stone, hairline courses, low contrast | reachable today (`rect`, `ring`, `poly`) |
| the flock | hundreds of specks distributed *along a curve*, thinning at its ends | `repeat` scatters in a box only |
| the haze | a huge radial glow screened over half the frame | gradient yes, blend no |
| framing | letterbox, most of the frame empty | no frame-scale document (the stage cards are 384×256 assets) |

**Reference B — pixel art.**

| element | what it is | today |
|---|---|---|
| sprites | drawn on a low native grid scaled up by a whole number, no anti-aliasing, a closed palette, a dark one-pixel outline | vector with anti-aliasing everywhere; bakes at 4× |
| ramps | shadows walk toward violet and blue, lights toward yellow | `ramps` mix toward `#000` / `#fff` in sRGB: shadows go grey-brown |
| emissive VFX | purple energy drawn in hard pixels, glowing smoothly past them | no emission, no post-processing |
| depth | several parallax layers, far ones lighter, bluer, flatter | no layers, no depth |
| tiles | ground and walls from repeated tiles | no tiling; `ss.env.pan` fakes a torus by emitting every edge-crossing part a second time |
| big bosses | Yggdrasil is a head and two separate hands; the chimera three heads | **exists**: rigs, skeletons, hinge chains, clips |
| motion | pose-to-pose frames and smears | transform tweens only; `bakeSheet` samples tweens into frames |
| HUD | a framed boss bar, portraits, slots, a minimap, Korean and Latin text | no nine-slice, no text primitive (the roadmap already wants one) |

## Where PolyGraphics stands

Measured over `apps/*/assets` at #102.

| | |
|---|---|
| asset documents | 297, 5,242 parts |
| primitives | 8 — `poly` 1,574 · `rect` 1,231 · `ellipse` 784 · `circle` 694 · `ring` 469 · `ngon` 103 · `star` 28 · `wedge` 3 |
| polygons of 16+ points | **458, in 59 documents; the largest has 180** — curves sampled by hand, because there is no curve |
| gradient parts | 102 in 29 documents, flattened to their mid colour by both engine adapters |
| translucent parts | 1,063 in 144 documents (`@alpha` paints, `opacity`) |
| blur, blend, mask, clip, texture | none |
| ramps | `light` / `dark` mix toward white / black in sRGB (`src/tokens.ts`, `mix`) |
| scene, layer, depth | none |
| animation | `x y rot scale opacity`, three eases; 167 clips on 97 documents |
| text | none |

What carries over and should not be touched: named parts, tokens, variants as patches, `use`, seeded
determinism, skeletons and hinge chains, the inspect loop, baselines. Those are the reasons to build these
looks *here* rather than in a paint program, and everything below extends them.

## The rasteriser is not the ceiling

`scripts/spikes/resvg-probe.ts` renders each effect as the smallest SVG that uses it, beside a control without
it, twice. resvg-js 2.6.2, the version in the lockfile:

| effect | applied | byte-identical twice |
|---|---|---|
| cubic path with an even-odd hole | yes | yes |
| `feGaussianBlur` | yes | yes |
| `feTurbulence` → `feDisplacementMap` (ragged edges) | yes | yes |
| `mix-blend-mode: screen` / `multiply` | yes | yes |
| luminance `mask` / `clipPath` / `pattern` | yes | yes |
| `feMorphology` dilate (outlines) | yes | yes |
| `feColorMatrix` | yes | yes |
| `feDiffuseLighting` (bump from alpha) | yes | yes |
| `feDropShadow` | yes | yes |
| `shape-rendering: crispEdges` | yes — a circle with 100 partially covered pixels has 0 | yes |

Two caveats came out on the way:

- **Cost.** The painterly spike's frame — 1280×720, 171KB of SVG, seven filters — renders in 3.4–3.8s. Fine
  for a bake; impossible per frame. The painterly look is bake-only by construction.
- **Browsers are a second implementation.** The gallery inlines SVG. Blur kernels, filter-region resolution
  and colour-interpolation handling are not specified to agree to the pixel between implementations, so for a
  document with a material the gallery has to show the bake — or it disagrees with the game exactly the way it
  disagrees about gradients today.

## Decision 1: bake-first — the renderer is the only interpreter of appearance

Today an adapter receives geometry and draws it: `bakeFlat` polygonises into a `Graphics` at boot, `buildRig`
does the same per top-level part, `drawAsset` every frame. Each rich feature has to be implemented again in
each adapter, and the history so far is that it isn't.

Split the bundle in two:

- **structure** — the IR as it is: node tree, transforms, anchors, `meta`, clips, variants;
- **appearance** — textures baked by the repository's renderer: per asset (flat), per top-level part (rig),
  per frame (sheet), packed into atlases with a manifest of `(id, variant, part | frame) → rect`.

Adapters stop drawing and start placing. `bakeFlat`, `buildRig` and `bakeSheet` keep their signatures and read
from the atlas when the bundle has one, and draw as today when it does not — so `ss` moves when it chooses to.
`drawAsset` stays for the case it exists for, an effect whose size is not known until it happens, and refuses a
document with a material rather than drawing it wrong.

**Where atlases live.** Every document and variant at 2× is 480 textures and 11.7 megapixels — about three
2048² pages before packing waste. They are not committed: the bake is deterministic, so the consumer builds it
(`npx polygraphics atlas --app ss --scale 2`, resvg as its devDependency) from the commit its lockfile pins and
gets the bytes CI would. `dist/` stays JSON.

**What bake-first costs,** stated so nobody discovers it:

- Resolution is chosen at bake time — `bakeScale` per app: 1 for the pixel look, 2 for the others.
- A theme is a second atlas. Themes already compile to separate IR, so nothing that works today stops working.
- **A material ends at a texture's edge.** A rig bakes one texture per top-level part, so a watercolour rim or
  an outline declared on a whole body would outline every part. The rule: a material is declared on a group,
  a group is baked whole, and a group is therefore also the unit a rig can move. For the pixel look this
  settles animation the other way — pixel bodies animate as sheets, frame by frame, which is how pixel art is
  animated anyway.
- **Runtime effects are a closed list** that engines do natively and the gallery reproduces in TypeScript:
  blend mode, tint and flash, alpha, and bloom from an emission map. Each gets a CPU reference and a parity
  test against the adapter, the way `test-webaudio-adapter.ts` holds the audio adapter to the renderer.

## Decision 2: extend the grammar in layers

Each layer compiles away before the IR where it can, the way `ngon` compiles to a polygon today, so an adapter
that still draws live learns nothing new.

### Geometry

- **`poly` gains `smooth: true`** — Catmull-Rom through the points. The cheapest win in the plan: the 458
  hand-sampled polygons become eight-point smooth ones, and an agent writes a curve the way it already writes a
  polygon.
- **`path`** — SVG path data, absolute `M L C Q Z` only, with `fillRule: "nonzero" | "evenodd"`; several
  subpaths make holes. Chosen over a structured node list because every model and every vector tool already
  reads and writes it; relative commands are rejected so a diff still reads as coordinates.
- **`brush`** — a spine and a width profile `[[t, w], …]`, compiled to a filled outline: the tapered stroke
  both references are full of — the wing, feathers, flames, roots. The spike's wing is one body brush, one
  sweep, five feathers, and four brush loops cut out of it by even-odd.
- **`blob`** — a seeded, smooth, closed organic curve (`rx`, `ry`, `jitter`, `seed`): clouds, stones, splats.
- **`repeat.along`** — scatter distributed along a curve with a density profile (the spike's flock is 320
  specks); **`repeat.grid`** — one document stamped on a lattice (tiles, and the pan's torus without emitting
  its edge parts twice).
- **`text`** — a font is a token; for the pixel look, a bitmap font document.

### Groups and clipping

A `group` part — `{ id, group: [parts…], clip?: "<part id>", material?, blend? }`. Today the only way to group
is `use`, which costs a document per group. Clipping is how both references shade: the underside of a cloud,
a band of light across a pillar, a pixel ramp inside a silhouette — draw the shading freely, clip it to the
body. Animations address a group like any part.

### Materials, as tokens

```jsonc
// apps/<id>/tokens.json
"materials": {
  "watercolor": { "ragged": { "scale": 7, "freq": 0.045 }, "rim": { "width": 2.5, "color": "$rust.dark2@soft" }, "grain": 0.35 },
  "cloud":      { "ragged": { "scale": 38, "freq": 0.018 }, "blur": 7 },
  "light":      { "blur": 9, "blend": "screen" },
  "stone":      { "ragged": { "scale": 2.5 }, "rim": { "width": 1.5, "color": "$steel.dark@heavy" } }
}
// a part
{ "id": "wing", "path": { … }, "fill": { "gradient": "linear", … }, "material": "watercolor" }
```

Each field has one compilation into filter primitives — the spike's four filters are these four materials —
and `blend` is `normal | multiply | screen | add | overlay`. A material is a token for the reason a colour is:
"make the watercolour wetter" is one number, a theme can swap `stone` for `ink` without opening a document,
and **a document never contains a filter graph** — the spike's watercolour is eleven filter primitives, which
is exactly the kind of text this repository exists to keep out of documents.

### Colour: hue-shifted ramps, and emission as a token

- A `ramps` entry may be an object in OKLCH — `{ "l": -0.12, "c": 1.0, "hue": [285, 14] }`: move lightness,
  scale chroma, turn the hue toward a target by at most so many degrees. A number keeps today's meaning, so no
  baseline moves until an app opts in. The pixel look depends on it and so does the second reference's whole
  palette: its shadows are violet, not darker.
- `tokens.emission` — `{ "pheromone": 1.2, "arcane": 1.5, "ember": 1 }`. Light belongs to a token: anything
  painted with it writes into the emission map that feeds bloom, and no document marks its glowing parts by
  hand. In the pixel spike the boss's organs glow because they are `$pheromone`; nobody told them to. For `ss`
  that is the premise: the hive's signal is the thing that shines.

### Looks

The app manifest gets a `look`, and the look decides what happens between the vector render and the texture:

```jsonc
"look": { "kind": "vector" }                                                          // today; the default
"look": { "kind": "painterly", "paper": { "grain": 0.55, "wash": 0.5 }, "vignette": 0.28 }
"look": { "kind": "pixel", "scale": 1, "outline": "selective", "translucency": "snap" }
```

**Pixel.** `scripts/spikes/pixel-look.ts` runs the pass on the repository's own documents: snap every paint to
its token's ramp step and every gradient to hard bands, rasterise at 1× with anti-aliasing off, make alpha
binary, clean orphan pixels, and draw a one-pixel outline outside the silhouette in the darkest step of what it
touches, pulled toward `$ink`. What it found:

- **Snap before rasterising, never quantise after.** Quantising the rendered pixels to the nearest palette
  colour has to guess a family per pixel and guesses across them: `ss.enemy.sinkmaw`'s sand rings came out red.
  Snapping at the paint kept every ring in its family. So this is a compiler step, not a filter.
- **After snapping, only translucency leaves the palette.** With anti-aliasing off and gradients banded, a pixel
  can only be off-palette if something translucent was composited over it: 4.3% of opaque pixels on
  `ss.figure.dot`, 26.7% on `ss.enemy.boss`, all under the sixteen translucent paints in its render. The look
  has to say what translucency means — `snap` (the spike) or `dither` — and 1,063 translucent parts say it will
  come up.
- **Mid-size forms convert; detailed small figures do not.** `ss.enemy.boss` (96²) and `ss.enemy.sinkmaw`
  (120²) read as pixel art with no edit. `ss.figure.dot` (40×56) comes out as noise with either quantiser: its
  straps, buckles and mask are sub-pixel, because the document is drawn to be judged at 8×. That is not a
  palette problem and no pass fixes it. A pixel-look document is authored at the pixel scale, which needs a
  **min-feature lint** (a part or stroke under one pixel at the look's scale, by name) and a **`pixels`
  primitive** — rows of characters over a legend of tokens, `{ "legend": { "a": "$moss", "b": "$moss.dark" },
  "rows": ["..ab..", ".abba."] }` — for the places a pixel artist places pixels by hand: a face, a hand, a
  buckle. It is still text, still diffable, still tokens, so a theme on it is a palette swap, the oldest
  recolour in pixel art.

**Painterly.** Materials carry the parts; the look adds the frame-level layers the spike ends with — paper
grain and wash as multiplied noise, a vignette, a letterbox.

### Scenes

A document kind of its own, `apps/<id>/scenes/*.json`, for what the stage cards already are — a composed frame:

```jsonc
{
  "id": "demo.scene.ruin",
  "size": [480, 270],
  "atmosphere": { "fog": "$dusk", "reach": 0.85 },
  "layers": [
    { "id": "far",  "depth": 0.9,  "parts": [ … ] },
    { "id": "mid",  "depth": 0.55, "parts": [ … ] },
    { "id": "play", "depth": 0,    "parts": [ { "id": "ground", "repeat": { "grid": [16, 16], "of": "demo.tile.soil", … } } ] }
  ],
  "post": [ { "bloom": { "tight": 4, "wide": 16 } }, { "vignette": 0.55 }, { "letterbox": 48 } ]
}
```

- **One number per layer does three jobs**: parallax factor for the engine, fog for the compiler (mix in OKLab
  toward `fog` by depth × reach), and draw order. In `scripts/spikes/pixel-scene.ts` the two skylines and the
  trunks take every colour they have from their depth.
- **Fog is a hue, not a grey.** The first version of that spike stripped chroma with depth; the style probe
  (below) put the frame at C̄ 0.039 against the reference's 0.049–0.095, and its accent share at 4.6% against
  12–57%. The second kept chroma and moved the hue toward a saturated violet fog: C̄ 0.068, accent 36.7%, both
  inside the reference's range, value unchanged (L̄ 0.28 → 0.27). One edit, measured before and after — which
  is the loop this whole plan is for.
- **Post runs after the upscale.** The pixel frame is 480×270 on a hard grid; its bloom is computed at
  1440×810 over it. Hard pixels, soft light — how the reference's purple energy reads.
- The engine gets one atlas per layer and the depth; scrolling and the camera stay the engine's, the same
  boundary drawn at whole-body transforms today. A scene is a picture with depth, not a level: no collision,
  no scripting.
- `ss.env.stage-den`, `-burrow` and `-pan` are scenes written as assets, and are the first migration.

### Motion

- **`flipbook` clips** — a list of variants or `pixels` frames with durations: pose-to-pose animation, the
  pixel look's native motion, baked with `bakeSheet`.
- **Colour tracks** — `tint` and `emission` as animatable props (a hit flash, an organ pulsing), on channels
  of their own; the reference analysis's `modulate`-doing-three-jobs lesson, carried forward.
- **`along` tracks** — a part following a path.
- **`emitter` documents** — particle presets: rate, life, a speed cone, curves over life for scale, alpha and
  tint, a sprite that is an asset id, a blend. The gallery previews one by a seeded fixed-step simulation into a
  filmstrip, so it can be seen and baselined; engines map it to their own emitters. The effect-verb catalog in
  [reference-analysis.md](reference-analysis.md) becomes emitters plus clips.

## Decision 3: instruments for what an agent cannot see

The sound side is measured because an agent cannot hear; `readability.ts` exists because it cannot judge
contrast by eye. A look needs the same.

**The style probe.** `scripts/spikes/style-probe.ts` measures a frame in OKLCH, letterbox rows dropped: mean
value and its 10th–90th percentile spread, mean chroma, the share of accent pixels (C > 0.08), the share of
bright saturated ones, and the two dominant hues. On the references and the spikes:

| frame | L̄ | L p10–p90 | C̄ | accent | hues |
|---|---|---|---|---|---|
| reference A, ruin and wing | 0.89 | 0.79–0.96 | 0.027 | 5.2% | orange, red |
| reference A, ruin and flock | 0.89 | 0.88–0.95 | 0.028 | 0.3% | orange, red |
| **painterly spike** | **0.87** | **0.64–0.96** | **0.027** | **9.4%** | **orange, red** |
| `ss.env.stage-den`, for scale | 0.24 | 0.19–0.25 | 0.018 | 3.1% | magenta, cyan |
| reference B, chimera | 0.36 | 0.13–0.64 | 0.095 | 57.3% | violet, blue |
| reference B, castle room | 0.28 | 0.17–0.43 | 0.054 | 25.0% | red, magenta |
| reference B, Yggdrasil | 0.40 | 0.26–0.65 | 0.049 | 12.2% | violet, purple |
| pixel spike, v1 | 0.28 | 0.16–0.40 | 0.039 | 4.6% | violet, purple |
| **pixel spike, v2** | **0.27** | **0.16–0.38** | **0.068** | **36.7%** | **violet, purple** |

It does not say whether a picture is good. It says whether it is in the same register and which knob is off:
the painterly spike is within 0.02 of the reference's value, on its chroma and its hues, with twice the accent
(the wing is too big for this frame) and lows that are too dark (p10 0.64 against 0.79 — the flock and the
figure). As a manifest field — `look.target`, the statistics stored as numbers — `check` reports a scene's
distance from its target the way loudness reports a sound's distance from its family band.

**Lints the looks need.**

| lint | look | catches |
|---|---|---|
| palette closure | pixel | an opaque pixel outside the token ramps, and the translucent part that made it |
| min feature | pixel | a part or stroke under one pixel at the look's scale — the Dot failure |
| orphans | pixel | single pixels left after clean-up |
| effect against its ground | all | light screened onto a ground already near white. The spike's first two tries at the shafts were invisible for this reason: screening white over a sky near 90% can raise it by the remaining 10% at most. What made them read was a darker sky and a tighter blur, not a brighter shaft |
| depth order | scene | a far layer with more contrast than a nearer one |
| emission budget | scene | the share of the frame in the emission map — bloom over a third of it is fog |
| bake parity | all | an adapter's runtime effect against its TypeScript reference, frame by frame |

## More references

A second round brought four more stills, each drawn as a spike the way the first two were. They were chosen by
the requester, not by this plan, which makes them a fair test of it: what did they need that the plan did not
already propose?

| | reference | what it needed that A and B did not |
|---|---|---|
| C | Skul, a daylight forest: bright sky, foliage, a ruin, a floating island hung with leaves, a tree boss, a slash, damage numbers | fog toward a *light* colour; foliage; a small hero; bitmap text |
| D | Blasphemous, a gothic nave: fluted columns, a stone Pietà, candelabra, broken flagstones, a penitent | light from candles only; a near-grey palette; a matte grade |
| E | Children of Morta, a three-quarter desert canyon: strata, dead trees, a throne grown from a tree, a glowing totem, a round minimap | shadows on the ground; many trees from one idea; coloured light |
| F | a mobile practice dungeon: a painted blue forest, a tree of lightning, a pixel slime, orange numbers, a Korean HUD | depth of field; lightning; a pixel sprite in a painted frame; Hangul |

**What each one added.**

- **Fog can brighten** (C). In daylight, distance goes toward the sky's pale cyan, not toward dark; the same
  `atDepth` does it with a different fog colour. Nothing to add but the observation that `fog` is a colour
  token, not a direction.
- **Foliage is cluster shading** (C). `clump()` draws a leaf mass as four offset layers of one ramp and a light
  direction, plus single-pixel flecks: the way a pixel artist shades a bush, as a generator. Every tree, bush
  and cloud in C is one call.
- **A hero written as `pixels` reads where a squeezed vector did not** (C, D, E). The skull, the penitent and
  the wanderer are 9 to 15 pixels wide, authored as rows over a legend, and each reads at a glance — the thing
  `ss.figure.dot` could not do through the pixel pass. It is evidence for the `pixels` primitive, and also its
  cost: every pixel was placed by hand, by an agent, and a boss-sized figure would be a great many of them.
- **Text is two things.** A 3×5 bitmap font that is itself `pixels` documents carries C and E's numbers and
  labels; a vector font carries F's Hangul and its bold numerals. The fonts are *files named explicitly*, with
  system fonts off: a line of Hangul rendered without its font file comes out as 0 pixels instead of 1,145,
  with no error. So a text part whose font is not loaded must fail `check`, and fonts belong in the repository
  (`tokens.fonts`), not on the machine. The spike reads them from `/usr/share/fonts` and refuses to run when one
  is missing.
- **Lit pixel art is cheap and enough** (D, E). The frame is drawn at full value, then multiplied by an ambient
  and each point light's falloff, computed at the output resolution so the falloff is smooth over hard pixels;
  emissive pixels are painted back afterwards, because light does not darken a flame. D has 22 candle lights,
  E a cyan totem, a blue selection ring and fireflies. No normal maps — none of the six references needs them.
  That moves point lights from "later" into the scene phase.
- **Some darkness is a grade, not a lack of light** (D). The first render measured L̄ 0.16 against the
  reference's 0.25. Raising the ambient moved it to 0.18. The reference's *darkest* pixels sit at L 0.21: its
  blacks are lifted, a matte grade. One post step — `lift: 0.085`, raise the black point — put the frame at L̄
  0.28, p10–p90 0.21–0.36 against 0.21–0.35. So the post stack gets `grade` (lift, gain, tint).
- **A three-quarter view needs shadows, and a shadow is a ramp step** (E). Every standing thing lays its own
  outline on the ground, sheared down-left and squashed, filled with the sand's dark step rather than a
  translucent black — so the frame stays palette-closed. This is the view `ss` is drawn in.
- **One generator, many trees** (E). Five dead trees and the two that make the throne are `branchTree` with
  seven seeds, twist near 1. The bark highlight is the same tree grown again from the same seed with a thinner
  width: width never touches the rng, so the second growth lands exactly on the first. Generators like this —
  `tree`, `bolt`, `clump` — are seeded parts that compile to polygons, the way `repeat` compiles to instances.
- **Depth does a fourth job: blur** (F). Painted backgrounds read as painted largely because the far layers are
  soft. The same depth that sets parallax, fog and order sets a blur radius, for looks that are not pixel.
- **Mixed resolution is ordinary** (F). The slime is drawn at 72×54 with anti-aliasing off and placed ×4 into a
  1280×720 painted frame. That is what the reference is, and the pipeline needed nothing new for it but a
  premultiplied blend for the layers that do have soft edges.

**Measured.**

| frame | L̄ | L p10–p90 | C̄ | accent | hues |
|---|---|---|---|---|---|
| reference C | 0.60 | 0.37–0.94 | 0.054 | 22.5% | green, teal |
| forest v1 | 0.56 | 0.24–0.88 | 0.058 | 27.3% | green, azure |
| **forest v2** — ground on the ramp's base step, not its dark one | **0.59** | **0.32–0.88** | **0.058** | **27.3%** | **green, azure** |
| reference D | 0.25 | 0.21–0.35 | 0.010 | 0.0% | red |
| cathedral v1 | 0.16 | 0.08–0.23 | 0.004 | 0.2% | yellow, lime |
| **cathedral v3** — ambient up, then a lifted black | **0.28** | **0.21–0.36** | **0.004** | **0.3%** | **yellow, lime** |
| reference E | 0.41 | 0.26–0.55 | 0.060 | 27.3% | yellow, lime |
| canyon v1 | 0.46 | 0.29–0.59 | 0.074 | 45.6% | yellow, orange |
| **canyon v3** — sand less saturated and darker | **0.43** | **0.27–0.54** | **0.062** | **1.6%** | **yellow, green** |
| reference F | 0.50 | 0.29–0.72 | 0.082 | 47.2% | blue, violet |
| mystic, untuned | 0.46 | 0.23–0.70 | 0.091 | 62.4% | blue, violet |

**The probe broke once, usefully.** On E, bringing mean chroma from 0.074 to the reference's 0.060 took the
accent share from 45.6% to 1.6%. Nothing visible changed that much: the frame is mostly one flat floor, and
its chroma had crossed the probe's single threshold (0.08). The reference's floor is textured, so its chroma is
spread across that line; the spike's is uniform, so all of it moved at once. Matching a mean is not matching a
look. `look.target` should store the distributions — value and chroma histograms, compared with something like
an earth mover's distance — rather than a mean and one threshold, and that same comparison would have said what
was actually wrong: a floor too even, not too grey.

**What it did not change.** Figures are still the weakest element. The Pietà's body reads as an insect, not a
corpse; the heroine in F is a paper doll next to the reference's. The machinery puts a frame in a reference's
register — the four probes above are within 0.04 of the reference's mean value — and it does not draw a
Blasphemous sculpture. That is the same limit the first round found, found again.

**While building these,** the spikes' blur turned out to overwrite its own input — the emission map the second
bloom pass and the emissive test still had to read. Fixed in `kit.ts`; the only number above it moved is the
pixel spike's accent share, from 36.8% to 36.7%.

## The spikes

All nine are deterministic — each drawing spike was rendered twice and compared byte for byte — and the seven
that draw write to `out/spikes/`, which is ignored. `kit.ts` and `pixel.ts` are the pieces they share. The
reference stills are not in the repository; their numbers above are.

| script | asks | answer |
|---|---|---|
| `resvg-probe.ts` | does the renderer we bake through do these effects, reproducibly? | all thirteen, byte-identical twice |
| `painterly-scene.ts` | can a frame in reference A's register be built from `blob`, `brush`, even-odd holes, `repeat.along`, four materials, blend and paper? | yes: 1280×720, 3.4–3.8s, byte-identical twice; probe above |
| `pixel-look.ts [ids…]` | can existing documents become pixel art? quantise after, or snap first? | snap first; mid-size forms yes, detailed small figures no |
| `pixel-scene.ts` | can a frame in reference B's register be built at 480×270 from depth, tiles, the repository's own documents, token emission and post-upscale bloom? | yes, in 2.5s; the figure is its weakest element, for the reason above |
| `style-probe.ts files…` | is a frame in a reference's register, and which knob is off? | the table above |
| `forest-scene.ts` | reference C: daylight depth, clumped foliage, a hero written as `pixels`, bitmap-font numbers | yes; one edit to reach the reference's lows |
| `cathedral-scene.ts` | reference D: pixel art lit by 22 candles over a dim ambient, a lifted-black grade | yes; value matched by the grade, not by more light |
| `canyon-scene.ts` | reference E: three-quarter view, generated trees, sheared shadows in the ground's dark step, coloured light | yes; the probe's accent threshold broke on it |
| `mystic-scene.ts` | reference F: painted HD depth with blur, lightning, a 72×54 pixel slime at ×4, Hangul from font files | yes, untuned: a little dark, a little over-saturated |

## Phases

Ordered by what each unblocks against what it risks. Each ends with something measurable.

0. **Parity: bake-first.** `npm run atlas` — per app, per scale, deterministic, flat / part / sheet textures
   with a rect manifest; adapters read the atlas when there is one; the gallery shows the bake for any document
   with a material. *Done when* the 29 gradient documents reach the Phaser adapter as textures rather than as a
   flat mid colour — the mock-scene test asserts it — and `ss` runs unchanged without an atlas.
1. **Geometry.** `smooth`, `path`, `brush`, `blob`, `repeat.along`, `repeat.grid`, `group` with `clip`, and the
   seeded generators `grow: tree | bolt | clump`. All compile to polygons, so no adapter changes. *Done when*
   the 180-point polygon is redrawn as a smooth one with a tenth of the points and the silhouette overlay cannot
   tell them apart.
2. **Materials and colour.** Material tokens, `blend`, OKLCH ramps as an opt-in, the emission map. *Done when* a
   theme swaps a material without touching a document, and `ss` baselines have not moved.
3. **Looks.** Pixel — paint snapping in the compiler, crisp rasterisation, outline, translucency policy,
   `pixels`, flipbook sheets, the three pixel lints, bitmap fonts as `pixels` documents. Painterly — paper, wash,
   vignette, vector text from vendored font files. *Done when* a pixel
   app's roster passes palette closure and min-feature.
4. **Scenes.** The document kind, depth and atmosphere (fog, and blur for looks that are not pixel), tiles,
   shadows, point lights over an ambient, the post stack with `grade`, a gallery tab, per-layer bakes, the stage
   cards migrated, the style probe as `look.target` comparing distributions.
5. **Runtime motion.** Emitters, `tint` and `emission` tracks, bloom in the adapters, parity tests.
6. **Later.** Nine-slice frames for HUDs; normal-mapped lights. Vector geometry gives exact heights for free,
   but none of the six references needs more than point lights over an ambient, so it waits for a game that does.

The second app the [app design systems plan](app-design-systems-plan.md) is waiting for is where phase 3 gets
decided. Cellspire's audit — facing flips, slam dust, parries — reads as a side-view action game, the kind the
pixel look and the scene document are for.

## Risks and limits

- **Taste is not a feature.** The spikes reach the references' register, not their quality. The wing is a
  competent brush shape and not the one in the reference; the pixel frame has the second reference's value
  structure and palette and none of its cluster work. What the system contributes is a removed ceiling and a
  closed loop — render, probe, edit — not the art direction.
- **Pixel art from vector has a floor.** Mid-size forms convert; small detailed figures have to be authored at
  the pixel scale. The lint and `pixels` make that possible, not automatic.
- **Painterly bakes cost seconds.** `npm run watch` has to bake incrementally, or a save stops being a loop.
- **Determinism is per version.** Run to run is verified; across resvg versions it is not promised. Pin resvg
  exactly and re-baseline on an upgrade, as a regression in `regress` would already force.
- **Filters are not legible, which is why documents never hold them.** A document says `"material":
  "watercolor"`; the compiler owns the eleven primitives.
- **Scenes must not become levels.** The moment a scene holds collision or triggers, it is a game engine
  written in JSON. The boundary is the one this repository already keeps: the document owns the picture, the
  engine owns what happens in it.

## Decisions for a person

1. **Which look first.** Pixel wants native-resolution frames, sheets and closed palettes; painterly wants
   high-resolution bakes and filters. Phases 0–2 serve both; phase 3 is the fork. Recommendation: pixel first if
   the second app is Cellspire; painterly when a game wants it.
2. **Atlases built in the consumer or committed.** Recommendation: built — the bake is deterministic and `dist/`
   stays text.
3. **`path` syntax.** Recommendation: the SVG path-data subset, not a structured node list.
4. **Whether `ss` adopts hue-shifted ramps.** It would move nearly every baseline and change how the roster
   looks. That is an art decision, not a tooling one, and nothing here requires it.
5. **Where style targets come from.** The probe stores numbers, not images, but a target should come from art
   the project owns — its own concept frames — rather than from another studio's screenshots.
