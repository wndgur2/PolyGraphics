# The Feelers — drawing rules

`apps/ss/app.json` holds the rules a lint can check: sizes, the grid, clip and state names, palette roles
and contracts. This page holds the rest — the conventions the roster is drawn to that no lint sees. They
were never written down; they were read back out of the documents, the way a new author would have to,
and they are written here so the next document does not have to guess.

Each rule says what it is, why, and where in the roster it shows. When a document breaks one on purpose,
it says so in its own `description`.

## 1. Light

**Light comes from the upper left.** The lit side of a form is the lighter value of its ramp (`.light`, or
the base token over a `.dark` body). The gloss — one small `$white` or `$silent` ellipse, often at
`@heavy` — sits up and to the left of centre, tilted along the form.

- Why: one light across the whole field is what lets a crowd read as solid things standing on one floor
  rather than stickers. A sprite lit from elsewhere reads as flipped.
- Seen in: the field items (`ss.pickup.breath`, `ss.pickup.hold`, `ss.pickup.burn`), the pulp, the
  chests, every character's head and cloak.
- The exceptions are lights *inside* a thing — a gland lit from the middle out, an ember in a sac — and
  they are written into the description as that.

**Shade goes down and right, as a shape — not a gradient.** A shade is a flat polygon in `.dark` (or the
base token at an alpha) laid over the lower-right of the form (`shade` on the pulp and the record).

**A thing lying flat on the ground carries its own shadow**, a copy of its outline in `$ink@0.4` pushed
down-right by about one unit (`[0.9, 0.8]` on the record and its media). A thing standing up does not:
feelers draws contact shadows for bodies itself, and a baked one would double it.

## 2. Outline

Every sprite is closed in `$ink`. There are two ways to draw that, and which one depends on the category.

| method | how | used by | why |
|---|---|---|---|
| **stroke** | `"stroke": {"color": "$ink", "width": …}` on the part | characters, enemies, pickups, projectiles | the outline follows the part through every animation track without a second part to keep in step |
| **under-shape** | a part filled `$ink` (`*_o`, `outline`), slightly larger than the shape above it | relics, icons, samples, the record's paper | a still drawing on a plate can carry a weighted, uneven outline (heavier on the shadow side) that a uniform stroke cannot |

Don't mix the two on one silhouette. An animated thing uses strokes. A still thing on a plate uses
under-shapes.

## 3. Stroke weight

The widths are tokens (`tokens/base.json` → `strokes`): `hair` 1, `thin` 2, `bold` 3, `heavy` 4.

- **`thin` is the silhouette.** It goes on the outermost parts: a character's cloak and head, an enemy's
  body, every pickup (`ss.pickup.food` set this, and the field items follow it).
- **`hair` is the inside.** It goes on parts inside or in front of the silhouette — a hand over the cloak,
  a rivet, a frost shard on a sac. It separates them without making the sprite busier.
- **`bold` and `heavy` are for large canvases only.** These are bosses drawn at several times an imp's size
  (`ss.enemy.foundress`), where `thin` would vanish at the scale they are seen at.
- **Samples use numbers (`1.1`)** because they are 32px documents shown at up to 56px; their weights are
  tuned per drawing.

Never stroke a gloss, a shade or a vein. Those are paint on the form, not forms.

## 4. Seen from above

The field is an oblique view. A circle lying on the ground is an ellipse at about half height. This covers
tunnel mouths, halos, pools, the record and its media. A slab shows a top face and a sliver of front edge
(`ss.pickup.record#stone`). A body standing on the field is drawn side-on and is not squashed.

## 5. Paint

- **Tokens, never hex.** Shift a hue with a ramp (`.light`, `.dark`, `.dark2`) or an alpha (`@ghost`
  0.15, `@soft` 0.35, `@heavy` 0.7, or a number).
- **Respect palette roles** (`app.json` → `roles`):
  - `$pheromone` and `$pink` are the hive's signal: enemies, the lure, a cursed state.
  - The arsenal is hive material with the signal stripped out (`$husk`, `$bone`, `$chitin`, `$timber`,
    `$frost`).
  - `$gold` means evolved or royal.

  Using `$carapace` purple on a reward reads as an enemy. That is why `ss.pickup.record#plate` is amber
  chitin.
- **Danger is dark and see-through. Yours is bright.** feelers draws hostile telegraphs and projectiles
  dark and translucent, and the player's light and saturated. A document meant for the hive's side should
  not be the brightest thing on screen.
- **Anything the game tints at runtime is drawn near white and neutral.** This covers the pulp, the dust
  and the glow sprites. A hue baked in fights the tint. Use value contrast (`$bone` / `$bone.dark` /
  `$smoke` / `$white`) to carry the detail.

## 6. Readability at the size it is seen

- **Judge it at game scale on the real floor.** `scripts/inspect.ts` shows big, game-scale and silhouette
  views side by side. A detail that disappears at game scale should go.
- **Contrast against the floor** (`scripts/readability.ts`): under `2.5` sinks, under `3.5` is thin.
  When a body comes in low, lift its lit side by one step of the ramp (Scent Burn's drop went from
  `$oxblood` to `$oxblood.light`).
- **Silhouette before colour.** Two things the player has to tell apart must differ in shape, not only
  hue. This matters most for green against red, the pair a red-green colourblind player loses.
  - The pulp tiers are a lump, a budded lump and a crowned lump.
  - The chests are a plain cell, a cell with an eye, and a crowned cell.
- **Keep interior detail single and off-centre.** Two highlights and a crease turn a lump into a face
  (the pulp's description records the draft that did).

## 7. One drawing, many states

When a second version of something is the same object in a different condition, make it a **variant** of
the document, not a new document. Examples are a boss's chest, a richer lump, a page written on stone, an
enraged phase.
- A variant keeps the size, the anchor and the clips in step for free.
- It is listed under the category in `app.json` → `states`.
- Tracks animate base parts only. A part added by a variant holds still; a part it removes leaves its
  tracks with nothing to move, which is allowed.
- If a state needs its own motion, animate a base part it keeps — `set` that part's shape or fill rather
  than adding a new one.

Make a new document when it is a different object (a new enemy, a new item), or when it is drawn by a
different generator.

## 8. Writing a document

- **The `description` is the brief.** It says what the thing is in the world, how it is lit and outlined,
  and why it looks the way it does. Where a draft failed, it says what failed, so the next edit does not
  repeat it.
- **Generated documents name their script** (`Generated by scripts/<name>.py`). Re-run the script rather
  than hand-editing its output; the script is where the geometry is legible.
- **Hand-kept and generated documents share one layout:** one part to a line, as `rig.write_doc` writes
  it. A diff then shows which part moved.
