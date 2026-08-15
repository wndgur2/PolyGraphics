# Reference Analysis: Asset-Representation Limits in Shape Survivors & Cellspire

*2026-08-15. Basis for PolyGraphics' design. PolyGraphics' goal: an asset generator / design system that an AI can understand and use.*

Two shipped-quality prototypes with 100% procedural, code-drawn visuals were audited:

- **Shape Survivors** — `~/Projects/vamp_surv`, Phaser 4 + TS, ~5.2k lines. All art baked at boot in `BootScene.ts` (526 lines) via `Graphics → generateTexture()`; runtime is plain sprites.
- **Cellspire** — `~/Projects/godot_test`, Godot 4.7, ~4.5k lines. All art built at `_ready()` as retained node trees (`ColorRect` ×59, `Polygon2D` ×13, `CPUParticles2D` ×8); `main.tscn` is 6 lines, the editor viewport is empty.

Both games independently converge on the same failure modes. That convergence is the strongest evidence for what PolyGraphics must solve.

---

## Shared limits (ranked)

### 1. Visual identity has no serialized representation
The single root cause. An asset exists only as imperative draw code; data carries at most a pointer or a color.

- SS: `EnemyType` has one visual field, `tex: string` (`src/data/enemies.ts:1-14`). The look of `imp` is an *unnamed* `{}` block at `BootScene.ts:176-179`. Adding an enemy with data alone yields a missing-texture box.
- Cellspire: `Enemy.KINDS` carries `color` + `size` only (`enemy.gd:8-26`); silhouette/parts/telegraphs are a hardcoded `match kind:` (`enemy.gd:128-160`). A new kind = a colored rectangle with an eye.

Nothing can be authored, varied, diffed, validated, or even *located* without reading imperative code. This alone makes the current approach illegible to an AI agent.

### 2. No named parts, no composition model
- SS: composition = sequential overdraw baked into one flat quad. The boss is 3 draw calls; its "eyes" are two circles that exist nowhere else (`BootScene.ts:206-211`).
- Cellspire: parts *are* built as nodes, but as anonymous locals — `body`, `scarf`, `wing`, `crown` are unreachable after `_ready()`; only ~5 of ~30 parts survive as fields. Half the entities lack even a `gfx` root, so they can't be flipped/squashed as a unit.

Consequence: "same body, different head", per-part recolor/animation, and themed variants are inexpressible. The entire variant system in both games is **scale × tint** (SS elite: `1.6` + pink tint, `EnemySystem.ts:118-142`; Cellspire elite: `1.3` + gold crown, with `1.3` re-hardcoded at 3 sites).

### 3. No design tokens (palette, depth, alpha, stroke, size)
- SS: 68 distinct `0x` + 23 distinct `'#'` literals, exactly **one** named color in the codebase (`OUTLINE`, file-local). Ten colors dual-encoded as number *and* string — the accent blue has 22 edit sites. Depth is 13 bare integers across 6 files.
- Cellspire: 68 hex literals, 4 disjoint mini-palettes, visible drift: 5 near-identical cyans, `ff9b3d` vs `ff9d3c` (accidental). 9 unnamed `lightened()` magnitudes, 12 unnamed alphas, 15 unnamed z-indices, 3 outline variants, 14 bare shake magnitudes.

Re-theming either game is a couple-hundred-site find-and-replace.

### 4. No isolated preview — the killer for AI iteration
Neither game can render one asset on a neutral background. SS: see the boss = boot, play to 5:00. Cellspire: `--autotest`/`--fxdemo` still require a full live level; the editor viewport is empty. Every visual edit costs a full game round-trip, so a generate → inspect → iterate loop — the core requirement for AI-driven asset work — is impossible.

### 5. Expressiveness ceiling: silhouette monoculture
- SS: every enemy is one of 4 convex primitives (circle/triangle/roundRect/regular n-gon); `poly()` only emits regular convex n-gons. Identity is carried by hue.
- Cellspire: axis-aligned rectangle monoculture (59 `ColorRect`s); 7 enemy rects within 20–26px of each other, visually identical modulo hue.

No concavity, no curves beyond `arc`, no gradients (Cellspire has exactly one), no texture/pattern, no outline system, no rig/frames. Organic form and material differentiation are out of reach.

### 6. FX and presentation fused to simulation
Both games' `damage()` functions interleave hp math, flash, damage numbers, knockback, audio, shake, and death in one body with no event seam (SS `EnemySystem.ts:258-309`; Cellspire `player.gd:484-537`, `enemy.gd:429-452`). Re-skinning feedback means editing combat code. Cellspire has 3 unrelated hit-flash idioms and 3 telegraph idioms; SS has 3 hand-rolled fade loops beside 5 tweens.

### 7. Copy-paste is the authoring mode; constants drift
- SS: 5 weapon shapes each authored **twice** (world texture vs icon) with independently hand-tuned coordinates; `FONT` declared twice; 4 shake-magnitude pairs.
- Cellspire: 59 ColorRect blocks, 8 duplicated particle configs, 5 additive-glow incantations, 5 circle-point loops, 5 squash tweens, ghost silhouettes hand-duplicating `_build_gfx` literals in 3 places.

### 8. Art geometry numerically fused to gameplay
- SS: baked texture sizes appear as bare divisors in simulation (`/62`, `/14`, `/64` in `WeaponSystem.ts`); data `radius` vs bake size are unguarded twins (imp 8/18, boss 38/80). Re-baking silently breaks tuning.
- Cellspire: player width `18` in 3 files; `gfx.scale.x` is simultaneously the facing flag and the squash channel — enemies can *never* squash because facing rewrites scale every frame (`enemy.gd:196`).

### 9. No animation model
Ad-hoc mix of tweens, hand-rolled `t -= dt` fades, and 5 copy-pasted sine bobs. No timeline/keyframe data, no shared easing vocabulary, no state machine. Motion vocabulary: bob, squash, spin, afterimage, stretch-fade.

### 10. Non-reproducible output (Cellspire)
`randf_range` at draw time with global `randomize()` → no screenshot is diffable, no visual regression testing possible. (SS is deterministic by accident — its noise canvas aside.)

---

## What already works — keep these signals

- **Cellspire's `Glob` FX verb catalog** (`glob.gd:269-499`): `slash / thrust / impact / ghost / muzzle / parry_flash / slam_dust / ring / burst / damage_number`, parameterized by `(position, direction, color, reach, strength)`. A *semantic effect vocabulary* — exactly the shape an AI-facing DSL should take.
- **`Biomes.DEFS`** (`biomes.gd:14-59`): proof that a keyed color dict yields a coherent restyle — but its reach stops at terrain (all 20 `pal.*` consumers are terrain/bg; enemies/FX are biome-invariant). Extend the pattern to everything, don't abandon it.
- **`Items.CAT_COLORS` / `RARITY_COLORS`**: the one well-reused semantic palette (category/rarity → color), consumed across 4 files.
- **SS's shallow factories**: `poly()`, `star()`, `face()`, `make()/makeWeapon()` (icon frame + `_evo` twin) — the embryonic form of parameterized asset components.
- **Retained composition over immediate mode**: Cellspire de-facto voted 80+ node constructions vs 1 `_draw()`. Node trees are addressable, diffable, per-part animatable.
- Trauma² screen shake, tween `(target, prop, value, dur, trans, ease)` tuples — portable as data.

## Engine leakage to abstract away

- `ColorRect` (a Control) as world art → top-left origin math at ~30 sites; needs a rect part with explicit pivot.
- `modulate` doing 3 jobs (status tint / hit flash / fade) on one multiply slot → collisions; needs separate composable channels.
- Additive blend + overbright `Color(6,6,6)` as the entire glow system.
- Flat integer z-index / depth values → named layer enum.
- 12-property particle config surface → named emitter presets.
- `Glob` effects self-parenting into `get_tree().current_scene` — precisely what makes an isolated preview impossible; effects need an explicit render target.

---

## Translation: requirements for PolyGraphics

1. **Serialized asset schema.** An asset is a declarative document (name, description/tags, parts, tokens, animation, FX bindings) that a renderer interprets. Diffable, validatable, addressable by name. This inverts limit #1 and is the load-bearing decision.
2. **Design tokens as the only color/size/depth source.** Semantic palette (+ derivation ramps for lighten/darken), named layers, alpha/stroke/size scales on a grid unit. Re-theme = rebind tokens (the `Biomes.DEFS` pattern, universalized).
3. **Part graph with named slots + variants.** Compose assets from named, reusable parts; variants (elite, biome-themed, evolved) as declarative overrides/decorators, not scale×tint. One source of truth per shape — icon and world sprite derived from the same definition (kills SS's authored-twice problem).
4. **Isolated, deterministic render harness.** Render any asset (and any animation frame) to an image on a neutral background, headless, seeded randomness. This is what enables an AI's generate → inspect → iterate loop and visual regression tests.
5. **Richer primitive vocabulary than the games had.** Concave/asymmetric polygons, curves, gradients, patterns, outlines as first-class strokes, emissive/glow as a channel — enough to escape the rect/regular-n-gon monoculture.
6. **Animation and FX as data.** Timeline/keyframe representation; separate channels (base color / tint / flash / opacity / transform) so facing can't stomp squash; a semantic FX verb layer (port `Glob`'s vocabulary) consumed via an event seam, never inlined in simulation.
7. **Sim-facing metadata derived from the asset** (collision radius, anchor, bounds) so art and gameplay numbers can't desync.

The two games prove the ceiling isn't "shapes look cheap" — flat-shaded shape art reads fine. The ceiling is that **the representation is illegible**: no schema, no names, no tokens, no preview. PolyGraphics' job is to make the same visual language *legible and operable* — for AIs first, humans second.
