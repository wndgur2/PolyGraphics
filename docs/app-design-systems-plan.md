# App design systems: one grammar, a convention per app

*2026-09-19. The plan for letting each app that draws from this repo state its own design conventions as
data, and for making `npm run check` hold that app's art to them. Reads the repository at #76.*

*Status: phases 0–4 landed 2026-09-19, on the same branch as this plan, one commit per phase. Phase 5 has
not: the second app needs a game, and Cellspire's source is not in the repository. What landed differently
from what is written below, and why:*

- *`audio.gain` sits in `tokens/base.json` beside `alpha`, not in the app's tokens — it is the level ladder
  the README already calls "sound's answer to alpha", and the analogy decided it.*
- *`core/` is empty. Phase 1b meant to seed it with `lib.face`, and the core rule is why it could not: the
  face's blush is `$blood`, an app colour, so the face is the demo's material (`demo.lib.face`). A library
  part whose identity needs an accent is not shared material under this design.*
- *Rule strength is `rules.levels: { "<rule>": "error" }` in the manifest rather than a `level` on each rule,
  since half the rule kinds are records with nowhere to put one.*
- *`readability` read the manifest from phase 1a, because the script was being ported anyway.*
- *The `distinct` rule found the spider hand's tile sitting on the wand's `$bile` exactly (ΔE 0 where 13 is
  the floor); it says so in a `why` until it is given a colour, which is an art decision. The `states` rule
  found the `final` state the six bosses gained on main while this branch was open; the vocabulary lists it.*

The repo is one design system that happens to hold one app's art. 242 of 254 asset documents and 22 of 22
sounds are `ss.*`; the other twelve are the README's worked examples from before there was an app at all. The
conventions that make the Shape Survivors roster hang together — the arsenal is hive material with the signal
stripped out, every enemy body carries a `death`, icons are 32×32, a weapon icon's rim is that weapon's own
colour, the effects are in the score's key — are real, were expensive to find, and are what "unified art"
means here. Most of them exist only as sentences in the README. The tooling knows two of them (the grid and
the loudness families), and knows them globally, as if every app ever drawn here will be a hive game on a
four-pixel grid.

The question is what has to change for a second app to be authored here without inheriting the first one's
palette, categories, floor colour and clip vocabulary — and without the first one's conventions going soft
because every lint now has to hold for both. Short answer: an **app** becomes a unit the loader knows (a
directory with a manifest, its own tokens over a shared base, its own documents, bundle and baselines), and
**conventions** become a section of that manifest that `check` reads. A rule that is not in the manifest is
not a rule; it is a sentence somebody will scroll past.

---

## Where it stands

| | count |
|---|---|
| asset documents | 254, of which 242 are `ss.*` |
| sound documents | 22, all `ss.*` |
| colour tokens | 32, every one referenced by `ss.*`; the twelve other documents use 11 of them |
| themes | 1 (`ice`), applied to every document of every app, shipped to none |
| bundles | 1, `dist/assets.json`, every app in it |
| `check` warnings | 56, of which 19 are `ss.terrain.*` and small shots at sizes the grid does not divide |

Three things are global that are really one app's:

- **The palette.** `tokens/default.json` is the hive's palette with a few structural greys in it. A second app
  would inherit `$pheromone` and `$chitin`, and the unused-token lint (`cli.ts`, `lintPalette`) would never
  notice that app using none of them, because it counts a reference from anywhere as use.
- **The floor, the scale and the categories.** `scripts/readability.ts` judges against `ss.env.ground` by
  default, targets `^ss\.(char|enemy|pickup)\.` and flags below 2.5:1; `scripts/inspect.ts` defaults to `ss.`
  and calls 1.35× "game scale"; `src/gallery.ts` orders tabs with a hand-written `CATEGORY_ORDER` that lists
  both id vocabularies, and its "ground" swatch is `#1a1420` — a hex that is not a token (`$soil` is
  `#1b1210`). `scripts/test-ss-bake.ts` and `compare.ts` filter on `ss-` by name.
- **The namespace.** `ss.` in the id and `ss-` in `tags[0]` encode the app twice, by habit. Nothing checks
  that they agree, nothing stops a document composing across the boundary (none does today — the boundary
  exists in practice and is stated nowhere), and the twelve generic documents use bare categories beside it.

### The conventions, and what holds them

| convention | stated in | held by |
|---|---|---|
| ids are `ss.<category>.<name>`; `tags[0]` is `ss-<category>` | habit | nothing |
| an enemy *body* carries `death`; a shot does not | README | nothing — true today: the 30 bodies have it, the 8 tagged `projectile` do not |
| nothing in a one-shot moves after `t = 0.85` | README | nothing — **4 of 30 `death` clips break it** (`boss` on 21 tracks, `courser`, `matriarch`, `warden`), all to `t = 1` |
| icons, relics and draughts are 32×32 | habit | nothing — 31 of 31, 82 of 82, 8 of 8; characters 8 of 9 |
| bodies carry `meta.radius` | README | nothing — 30 of 30 enemy bodies, 9 of 9 characters, 1 of 5 pickups; which categories must is unwritten |
| the arsenal never paints with the hive's colour, except `ss.fx.pickup` and `ss.proj.mine` | README | nothing — and `ss.icon.magnet` paints `$pink` today, which nobody has ruled on |
| weapon icon rims are distinct — ΔE2000 ≥ 13, worst pair 20.2 | README, #68 | a calculation done by hand once; the repo has no ΔE |
| `ss.proj.ring` keeps `meta.radius` 62; `dung` 14, `aura` 64, `dung-burst` 30 | each document's description | nothing |
| the roster reads on `ss.env.ground` at ≥ 2.5:1; the pan's household on `ss.env.pan` | README | `readability.ts`, with floor, targets and thresholds as constants |
| game scale is 1.35× | `inspect.ts` | a constant |
| canvases sit on a 4px grid | `tokens/default.json` | `check` — with 19 warnings saying it does not apply to terrain props and shots, at a volume that trains everyone to scroll past |
| sounds sit in loudness families, ±4dB | `tokens/default.json` | `check`, with `offBand` to opt out in writing |
| the effects are in the score's key | README | nothing — `$third $fifth $seventh` *are* the key, and nothing stops a fanfare reaching `$grit` |
| `layers`: what draws over what | `tokens/default.json` | nothing reads it; `check` requires it and the gallery prints it |

The last two rows are the two lessons this plan is built on. `layers` is a token table with no reader: it was
put in the tokens because it was the right kind of thing, and it has drifted into decoration — a design
decision the tooling requires you to state and then ignores. The loudness families are the opposite: a table
of numbers (`audio.loudness`), a lint that reads them (`lintSounds`), and a written opt-out on the document
(`offBand`). That pattern is the only one in the repo where a convention has held under edits by sessions
that never read the sentence it came from. Everything below generalises it.

---

## What an app is here

An app is whatever consumes a bundle: one game, one launcher, one screen. It owns a **namespace**, a
**palette** and a **pitch palette**, a **grid**, a list of **categories**, the **floor** its art is judged on
and the **scale** it is seen at, a **clip** and **state** vocabulary, its **sound families** and its **key**.
It does not own the grammar. The schema, the shapes, the token-reference grammar, the renderer, the compiler
and the adapters are the repo's, and an app narrows them and never extends them — otherwise whoever can
author for one app can no longer author for the next, and the premise in the README's first line is gone.

Six rules the design keeps to:

1. **One grammar, many conventions.** A convention forbids and requires. It never adds a primitive, a prop or
   a token kind.
2. **A convention is data `check` reads, or it does not exist.** `layers` is what happens otherwise.
3. **Namespace = directory = bundle.** The id prefix is derived from where the file lives, not typed twice.
4. **Ids never change.** The migration moves files; it renames nothing that a consumer could be pinned to
   (README: *retiring art is two changes, game first*).
5. **The exception is written where it happens**, per document, and names the rule it breaks — `offBand` and
   a voice's `why`, generalised.
6. **Shared material is a small core, and core knows no app.** Core documents reference base tokens only;
   apps `use` core; apps never `use` each other.

---

## The shape

### Layout

```
tokens/base.json                what is physics, not identity: ramps, strokes, alpha, audio.ramps/q/dur,
                                and the structural greys every app starts from (ink, white, bone, steel,
                                slate, smoke, coal)
core/assets/*.json              shared library documents, ids `core.<category>.<name>` — base tokens only
apps/<app>/app.json             the manifest: identity, references, rules (below)
apps/<app>/tokens.json          the app's colours, pitch palette, grid, loudness families — over base
apps/<app>/themes/*.json        overlays over the app's resolved tokens; may override, never introduce
apps/<app>/assets/*.json        documents; id must start with `<app>.`
apps/<app>/sounds/*.json
apps/<app>/baselines/           accepted bakes for this app
dist/<app>/assets.json          the app's bundle, `polygraphics/apps/<app>/assets`
dist/<app>/sounds.json
dist/assets.json                the union, kept until the consumer has moved (phase 4), then dropped
out/                            stays flat: ids are unique by construction, so one svg/, compiled/, wav/
                                and one gallery.html with an app switcher
```

Tokens resolve **base ⊕ app ⊕ theme**. `applyTheme` is already the ⊕; it runs twice. An app may override a
base colour — that is how `$ink` is allowed to be warmer in one app than another — and a theme may override
anything in the app's resolved set, under the rule themes already live by. `grid` moves to the app level: a
four-pixel grid is an app's pixel scale, not a property of drawing.

The alternative was to leave `assets/` flat and derive the app from the id prefix. It costs nothing to move
to and it is what the repo does today by accident. It was declined because a flat directory of five hundred
documents from two games says nothing about either, `ls apps/` should answer "what draws from here", and
per-app baselines and bundles want a place to be. The move is one mechanical PR, and the union bundle proves
it (phase 1).

### The manifest

`apps/ss/app.json`, with the conventions that are true of the roster today. Every rule below is one the data
already keeps, or that the README says it keeps; phase 0 is writing this file and finding out which.

```jsonc
{
  "id": "ss",
  "name": "Shape Survivors",
  "premise": "The protagonist has lost their pheromone transmitter, and the hive hunts them for the silence.",
  "engines": ["phaser"],
  "categories": ["char", "figure", "enemy", "proj", "fx", "pickup", "terrain", "env",
                 "icon", "relic", "curse", "draught", "app", "lib"],      // tab order; tags[0] must be one

  "reference": {
    "ground": { "field": "ss.env.ground", "pan": "ss.env.pan" },        // the floors art is judged on
    "scale": 1.35,                                                       // screen px per authored px
    "contrast": { "sinks": 2.5, "thin": 3.5 }                            // readability.ts, from here
  },

  "rules": {
    "grid":  { "applies": ["char", "icon", "relic", "draught", "curse", "env", "app"] },
    "size":  { "char": [32, 32], "icon": [32, 32], "relic": [32, 32], "draught": [32, 32] },
    "meta":  [{ "in": ["enemy", "char", "figure", "pickup"], "unless": ["projectile"], "require": ["radius"] }],
    "clips": [{ "in": ["enemy"], "unless": ["projectile"], "require": ["death"] }],
    "oneShot": { "death": { "settleBy": 0.85 } },
    "states": {
      "enemy":  ["elite", "enraged", "buried", "elite_buried", "spent", "grub", "loosed", "planted"],
      "proj":   ["evolved", "worn", "muck", "evolved-worn", "evolved-muck"],
      "icon":   ["evolved"],
      "relic":  ["glyph"],
      "curse":  ["glyph"],
      "pickup": ["cursed"],
      "terrain": ["filled"],
      "app":    ["maskable"]
    },
    "roles": {
      "hive":    ["pheromone", "pink", "spore", "orchid"],
      "arsenal": ["husk", "bone", "chitin", "timber", "frost"],
      "evolved": ["gold"]
    },
    "paint":    [{ "in": ["proj", "icon"], "forbid": "hive", "except": ["ss.proj.mine", "ss.icon.mine"] }],
    "distinct": [{ "in": "icon", "part": "rim", "minDeltaE": 13 }],
    "contracts": {
      "ss.proj.ring": { "meta.radius": 62 }, "ss.proj.dung": { "meta.radius": 14 },
      "ss.proj.aura": { "meta.radius": 64 }, "ss.fx.dung-burst": { "meta.radius": 30 }
    },
    "layers": { "env": "bg", "terrain": "ground", "pickup": "pickup", "enemy": "enemy",
                "proj": "fx", "fx": "fx", "char": "player", "figure": "player", "icon": "ui", "relic": "ui" }
  },

  "audio": { "key": ["tonic", "third", "fifth", "seventh"] }
}
```

What is *not* in it, on purpose: the loudness families stay in `tokens.json` under `audio.loudness`, where
they are and where a theme can overlay them. The manifest holds rules about documents; tokens hold named
values documents reference. `premise` is not a rule either — it is the sentence the rules serve, and the
gallery puts it at the top of the app so a new author reads it before the palette.

Every rule kind is a fixed shape with a zod schema in `src/app-schema.ts`. There is no expression language:
`in` / `unless` match `tags`, `require` names keys, `forbid` names a role. A new *kind* of rule is a PR to
`cli.ts`, exactly as the loudness lint was; a new *instance* of a rule is a line in a manifest. A rule may
carry `"level": "error"`; the default is a warning, and the app decides how hard its own rules are.

### What `check` learns

One line per lint: what it reads, what it says, how a document opts out. Opting out is `why` on the asset
document — `"why": { "grid": "a shot is placed, not tiled" }` — keyed by rule name, the way a voice says
`why` it keeps a raw sawtooth. `offBand` on a sound stays as it is.

| lint | reads | says |
|---|---|---|
| namespace | app dir, `id`, `tags[0]`, file name | `id must start with "ss."`; `tags[0] "ss-enemy" is not a category — categories are enemy, proj, …`; file name |
| composition | every `use` | `ss.icon.whip uses demo.fx.slash — an app composes its own documents and core's` |
| core | `core/` documents' token refs | `core.lib.face paints $pheromone — core documents use base tokens only` |
| palette, per app | the app's tokens against the app's documents | `"$name" is unused in ss — drop it or use it`; a theme overriding a token the app does not resolve is an error, as now |
| grid | `rules.grid.applies` | as today, only where the app says it applies — the 19 warnings become one decision in the manifest |
| size | `rules.size` | `ss.char.survivor is 36×36 — char is 32×32 in ss` |
| meta | `rules.meta` | `ss.pickup.chest has no meta.radius — pickup bodies carry one` |
| clips | `rules.clips` | `ss.enemy.lurker has no death clip — enemy bodies carry one` (a shot is exempt by its `projectile` tag) |
| one-shot | `rules.oneShot` | `ss.enemy.boss death: 21 tracks still move after 0.85 (organ_a.scale to 1.0) — arrive, then hold` |
| states | `rules.states` | `ss.enemy.gland#toxic is not a state of enemy — states are elite, enraged, …` |
| contracts | `rules.contracts` | `ss.proj.ring meta.radius is 60; the game divides by 62` |
| paint | `rules.roles`, `rules.paint`, the document *and everything it composes* | `ss.icon.magnet paints $pink (hive) — the arsenal is hive material with the signal stripped out` |
| distinct | `rules.distinct`, ΔE2000 in `tokens.ts` | `icon rims: lash vs pod ΔE 9.8 < 13` |
| readability | `reference.ground`, `reference.contrast` | as `readability.ts` says today, per app, from the manifest |
| key | `audio.key` | `ss.sfx.victory plays $grit — fanfares are in the key: tonic, third, fifth, seventh` |

The paint lint walks token references through `use`, not the compiled IR, because the sentence it enforces
is about what the document *says* — `$pink` is the violation, not a particular RGBA. Where a `use` crosses
into core, core's structural greys are never a role, so nothing composed from core can trip it.

### What the gallery learns

- An **app switcher** across the top; one page, one search, `#/<id>` routing unchanged.
- Category tabs in the manifest's order; `CATEGORY_ORDER` goes.
- The **premise** at the top of each app, then the token page grouped by **role** with the role's sentence,
  so the palette reads as decisions rather than as thirty-two swatches.
- The viewer's **ground** button draws the app's ground document tiled behind the sprite, instead of a hex
  nobody can find. Where a manifest names several floors, one button each. This is the render the README
  already promises ("on the ground colour it will actually sit on"), done with the actual ground.
- A **rules** page per app: every rule, how many documents it holds over, and the exceptions with their
  `why`. This is the page a designer reads to see whether the app is one thing — and the page a session reads
  before it draws.

### What the scripts learn

`inspect`, `sheet`, `filmstrip`, `readability` and `compare` take `--app <id>`, default it from the ids they
are given, and read the floor, the scale and the thresholds from the manifest. `watch.ts` watches `apps/`,
`core/` and `tokens/`. The adapter tests keep `ss` documents as fixtures (`test-webaudio-adapter.ts`,
`test_godot_adapter.gd`) — a fixture is allowed to name a document; a tool is not.

---

## The plan

### Phase 0 — Write it down

`apps/ss/app.json`, and nothing that reads it. Every rule cites the README sentence or the data it comes
from, and the PR description is the list of places the roster already disagrees with itself — the four
`death` clips that move to `t = 1`, the 36×36 `ss.char.survivor`, the nineteen grid warnings that become one
`applies` list, the four pickups without a radius, the magnet icon's `$pink`. Each is a decision: fix the
document, or write the rule the way the roster actually is. Deciding them here, before a lint can nag, is
what keeps phase 2 from landing with forty new warnings.

Also in this phase: `src/app-schema.ts`, the zod shape for the manifest, so the file is validated from the
day it exists even though nothing enforces it. One PR.

### Phase 1 — The loader knows apps

Two PRs, so the first can be proven byte-for-byte.

**1a — the move.** `tokens/default.json` splits into `tokens/base.json` and `apps/ss/tokens.json`; the `ss.*`
documents, sounds, themes and baselines move under `apps/ss/` with `git mv`, the twelve under `apps/demo/` with
their ids untouched for now; `loadAll` becomes `loadApps()` and returns one registry per app plus core; every
script reads its documents through it. Nothing else changes.
**Proof:** `dist/assets.json` and `dist/sounds.json` are byte-identical before and after, `npm run regress`
passes against the moved baselines, `out/gallery.html` differs only in the app switcher.

**1b — the twelve and the core.** The generic documents become `apps/demo/` with the smallest manifest that
validates (a premise, four categories, no rules), because they are the README's examples and an example
should have the shape a new app's document has. Their ids take the `demo.` prefix — the one rename in this
plan, allowed because nothing has ever imported them and the README is the only reader. `lib.face`, used by
`char.dot` alone, becomes `core.lib.face` under `core/`, the first core document, so the demo also shows an
app composing core. The namespace, composition and core lints land here, since they are what make the move
mean something.

### Phase 2 — Rules the check reads, structural

`grid`, `size`, `meta`, `clips`, `oneShot`, `states`, `contracts`, and `why` on the asset schema. All
warnings. No rasterization, so `check` stays as fast as it is. The gallery's rules page lands here, because
a rule with a count beside it is what makes the manifest legible.

Expected on landing, if phase 0 fixed nothing: 0 grid warnings where there were 19; 4 one-shot warnings; 1
size warning; 4 meta warnings; and whatever `states` finds that the vocabulary in the manifest did not (the
fourteen `ss.lib` variant names are the likely surprise — a library document's states are the callers'
vocabulary, and a `lib` rule of `"*"` is probably right). Two rules get promoted to `error` at the end of this phase:
`contracts`, because a broken one is a gameplay bug the game cannot see, and `namespace`, because a wrong
prefix is a document the bundle will put in the wrong app.

### Phase 3 — Rules the check reads, paint

`roles`, `paint`, `distinct` and `key`, with ΔE2000 in `tokens.ts` (forty lines; the same function serves
the palette lint's near-duplicate check the roadmap has wanted). `readability.ts` reads the manifest and
stops knowing the field. The gallery's ground button draws the ground document; the token page groups by
role. This is the phase where "the arsenal is hive material with the signal stripped out" stops being a
sentence and becomes a number `check` prints — the point of the whole plan for the app that exists.

### Phase 4 — Per-app outputs

`dist/<app>/assets.json` and `sounds.json`, `polygraphics/apps/<app>/assets` in `package.json` exports,
`apps` and `core` in `files`, `out/manifest.json` gains an `app` per entry and a `layer` from
`rules.layers` — which gives `layers` its first reader and moves the table to the manifest where the reader
is. `baselines`, `regress` and `png` take `--app`. The union `dist/assets.json` keeps building until the
consuming game has switched its import, in that order (game first, art second), and is dropped in the PR
after the game's pin moves.

### Phase 5 — The second app

The test of everything above is an app that is not `ss`. `apps/demo` is the template; the first real one
is Cellspire, the other game audited in [`reference-analysis.md`](reference-analysis.md), Godot-targeted,
with a palette that is not a hive's. Ten documents, its own manifest, its own floor, and — the definition of
done — **no edit to `src/` or `scripts/`**. If a second app needs a `src/` change to be lint-clean, phase 2
or 3 encoded `ss` rather than a rule, and that is the bug to fix before the app lands.

### Deferred

- **Shipping themes.** A theme has never reached a consumer (`dist` is built with the default tokens only)
  and no game has asked for one. When one does: `dist/<app>/themes/<name>.json`, same IR, and the
  consumer picks a bundle. Not before.
- **Adapters reading `layer`.** The manifest carries it after phase 4; whether a rig sets its depth from it
  is the game's decision, per the boundary the README draws at whole-body transforms.
- **A convention that needs the raster.** `readability` stays a script until it is fast enough to sit in
  `check`; a CI step can run it per app in the meantime.

---

## What we deliberately do not build

- **Per-app schemas or renderers.** One `schema.ts`, one `render.ts`, one IR format. An app can say "no
  gradients" through a rule; it cannot add a shape.
- **App names in `src/`.** No `if (app === "ss")`, anywhere. Everything a tool knows about an app it read
  from that app's manifest. `grep -rn '"ss\.' src scripts` returning only test fixtures is a check.
- **A rules engine.** The manifest is a closed set of rule kinds with a schema. A new kind is a PR, and it
  arrives with a lint and a message that names the fix — as every lint in this repo does.
- **Cross-app composition.** Shared material moves to `core/` on purpose, with base tokens, and gets a
  sentence saying why it is shared. An app reaching into another app's documents is the coupling the id
  prefix exists to prevent.
- **A token editor, a theme designer, a GUI.** The document is the interface; the gallery is where it is
  judged.
- **Migrating the consumers ourselves.** The game changes its import first; only then does the union bundle
  go. The README learned this the hard way and this plan does not re-learn it.

---

## Why this order

- **Manifest before loader.** What the loader has to know is whatever the manifest has to say, and the
  cheapest way to find out what is actually a rule (and what is a habit the roster breaks four times) is to
  write the rules down and count.
- **Loader before lints.** A lint scoped to an app needs the app to exist as a registry, and the palette lint
  is wrong until it does.
- **Structural before paint.** Structural rules are cheap, need no raster, and carry most of the migration's
  risk (the move, the rename, the `why` field). Paint rules are where the judgement is, and they should land
  on a repo that has already stopped moving underneath them.
- **Outputs last.** Nothing a consumer imports changes until phases 1–3 are settled, and the union bundle
  staying byte-identical through them is how we know the move broke nothing.
- **The second app after all of it**, because it is the only honest test, and running it earlier would test
  a system that still has `ss` in its constants.

---

## Definition of done

- A new app is `apps/<id>/app.json`, `tokens.json` and one document. `npm run check` renders it, lints it
  against its own rules and nobody else's, and writes `dist/<id>/assets.json` — with no edit to `src/` or
  `scripts/`.
- Every row of the conventions table above is either a manifest rule with a lint behind it, or is listed in
  the README as prose-only with the reason. There is no third state.
- `grep -rn '"ss\.' src scripts` matches adapter test fixtures and nothing else.
- Every `ss.*` row of `dist/assets.json` is byte-identical to today's through phase 3; baselines pass.
- The gallery shows, per app, the premise, the roles, the rules and their counts, and draws every sprite on
  the floor it will stand on.
- The four `death` clips, the 36×36 character, the four radius-less pickups and the magnet icon's `$pink` are
  each either fixed or carry a `why` — and the rules page says which.

---

## Checks, per phase

| phase | what must be true before it merges |
|---|---|
| 0 | `apps/ss/app.json` validates against `app-schema.ts`; every rule cites its source; the disagreements are listed and decided in the PR |
| 1a | `dist/*.json` byte-identical; `npm run regress` green; `npm run typecheck` clean; the adapter tests pass; `npm run watch` rebuilds on a save under `apps/` |
| 1b | the twelve render under `demo.` and `core.lib.face` composes; namespace / composition / core lints fire on a deliberately wrong fixture and on nothing real |
| 2 | warnings match the phase-0 list exactly (no rule fires on a document phase 0 did not name); `why` silences a rule and the rules page shows it; `contracts` and `namespace` at `error` |
| 3 | the arsenal rule passes on every icon and projectile but the mine and its icon, and `ss.icon.magnet` has been ruled on; rim ΔE reproduces #68's 20.2; `readability --app ss` equals today's output; the gallery ground is the tiled `ss.env.ground` |
| 4 | `polygraphics/apps/ss/assets` imports from a scratch consumer; the union is identical to the concatenation of the app bundles; `regress --app ss` green; the game's import switched before the union goes |
| 5 | Cellspire's first ten documents lint clean under their own manifest, render in the gallery under their own floor, and `git diff --stat src scripts` for the PR is empty |

---

## Decisions to take

1. **Directories per app, or a flat `assets/` with prefixes.** This plan says directories, for the reasons
   under *Layout*. The flat option is cheaper by one mechanical PR and worse forever after.
2. **Rename the twelve to `demo.*`.** Recommended; nothing pins them. The alternative is a manifest field that
   allows a bare prefix, which makes the namespace rule optional on day one.
3. **Which rules go to `error`, and when.** Proposed: `contracts` and `namespace` at the end of phase 2; the
   rest stay warnings until the app has been clean for a while, and the app decides in its own manifest.
4. **Whether `readability` joins `check`.** Not until it is fast; a CI step per app in the meantime.
5. **The second app.** Cellspire is the candidate with a written audit and a different engine. If another
   app is closer, phase 5 is the same plan with a different name.
