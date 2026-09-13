# Sound System Design: from an SFX baker to an instrument layer

*2026-09-01. Answers one question: is an instrument layer premature, and if it isn't, what has to change underneath it.*

*Status: phases 0–3 of the migration below have landed. Phase 4 (`phrase`) has not.*

The question is not whether `use` can compose documents — it already does, and the README already calls
`ss.lib.note` and `ss.lib.knell` instruments. The question is whether the model *under* `use` can carry an
instrument at all.

Short answer: the instrument is not premature. Twelve of twenty-one documents already hand-write the same one,
and the roadmap's next sound item — the adaptive score's *materials* — is blocked on it. But `root` plus a pitch
at the call site is only half the change. The other half is that **envelopes have no absolute time**, and an
instrument whose attack stretches with its note length is not an instrument.

---

## What the model was built for

Every decision in `sound-schema.ts` / `sound-render.ts` assumes one trigger, sub-second, fixed length, decaying
to nothing:

- `duration` is a required scalar canvas.
- A voice's `dur` defaults to "the rest of the sound".
- Envelope keys are `[0..1, value]`, sampled at `u = i / n` (`sound-render.ts:145`) — proportional to the voice's
  own span, with no absolute anchor anywhere in the schema, the IR, or the renderer.
- `repeat` is frozen at compile time so the bake stays byte-identical forever.

That is a good one-shot SFX system and it works: 21 documents, 28 baked takes, 28 of 28 green against
`baselines/sounds/`. Nothing below argues it was wrong. It argues that the shipped set is already paying for one
of those assumptions, and that the next thing on the roadmap asks the model for something it structurally
cannot say.

---

## Findings

### 1. The `use` voice implements half of the document's own stated model

`sound-schema.ts:136` states the model in its own words:

> *Where a visual variant has one `scale`, a sound has two — a thing can get bigger by dropping in pitch or by
> taking longer, and they are not the same edit.*

Both scales went to variants. The call site got one of them.

| Set at the call site | visual `use` part | sound `use` voice |
|---|---|---|
| position | `at [x,y]` ✅ | `at t` ✅ |
| scale in the document's own axis | `scale` ✅ | `dur` (time only) ⚠️ |
| **scale in frequency (pitch)** | — | **absent** ❌ |
| orientation | `rot`, `mirrorX` ✅ | — (time has no such axis) |
| level | `opacity` ✅ | `gain` ✅ |
| sub-variant | `variant` ✅ | `variant` ✅ |

`compile.ts:189-204` hangs the composed asset under a node carrying all five of a use part's transforms.
`sound-compile.ts:318-350` folds three of a use voice's, and none of them is pitch.

The consequence is measurable:

- **visual** — 58 of 137 assets compose (102 of 1112 parts)
- **sound** — 3 of 21 documents compose, and all three are fanfares (14 of 36 voices)

Composition on the sound side is confined to the one category where the library happened to pre-declare the
pitches that were needed. To play `ss.lib.note` at a pitch nobody anticipated you have to edit the instrument,
so the two library documents carry 6 degree variants between them — and the same variant name means a different
interval in each (`ss.lib.note#fifth` is a third above its `$third` root; `ss.lib.knell#fifth` sits below its
`$seventh.down` root). The names describe the token they set, not the degree they land on, because there is
nothing else for them to describe.

### 2. Envelopes have no absolute time, and the set already pays for it

`u = i / n` means an envelope is a shape over a span, never a duration. Play a voice twice as long and its
attack is twice as long. For a decay-only gesture that is harmless, which is why it has not hurt yet.

It has hurt once, and it is in the shipped set. `ss.sfx.chime` is the only document with an attack, and it has
two voices of different lengths that want the same one:

| voice | gain keys | dur | attack |
|---|---|---|---|
| `call` | `[[0,0], [0.017,1], [1,0]]` | 0.7s | 11.9ms |
| `answer` | `[[0,0], [0.013,0.8], [1,0]]` | 0.95s | 12.35ms |

Someone solved `0.012 / dur` by hand, twice, and wrote the quotient into the document. That is the model
fighting the author — and it is exactly the arithmetic an instrument played at four different lengths would
force on every use site.

A score plays notes at lengths the score chooses. Until an envelope can hold a real 12ms attack across those
lengths, there are no score materials to ship.

### 3. The instrument already exists; it just has no name

Across the corpus:

- 17 of 19 oscillator voices carry the identical gain envelope `[[0,1],[1,0]]` with the default `exp` ease.
- 12 of 21 documents *are* one oscillator voice with a glide and that decay — `elite-die`, `enemy-die`, `food`,
  `hurt`, `move`, `pickup`, `rattle`, `select`, `shoot`, `whip`, and both library documents. They differ only in
  `wave`, `freq`, `to`, `gain`, `dur`.

"A decaying blip" has been written out by hand twelve times. Naming it is not a new abstraction; it is
recognising one already in the repository.

The two exceptions are chime's two voices — which is finding 2 restated. The one document that reaches for
something an instrument would carry is the one document the model cannot factor out.

### 4. Two live defects in the composition path

Both confirmed by compiling probe documents against the real registry.

**(a) A `use` voice's `env` and `filter` are silently discarded.** `UseVoiceSchema` spreads `voiceBase`, so the
schema accepts both; the use branch at `sound-compile.ts:318` reads neither. A document that puts a fade on a
composed voice compiles clean, bakes unchanged, and reports nothing. Either honour them as overrides or reject
them in the schema — the present third state is the only bad option.

**(b) Raw Hz in `to` never warns.** `source.freq: 900` warns (`raw 900Hz — prefer a token like $tonic`);
`source.to: 900` does not, because `withGlides` calls `hz(..., warnRaw = false)` (`sound-compile.ts:239`). Eight
of the set's thirteen glides end on a raw number (`900`, `1400`, `55`, `40`, `60`, `1500`, `380`, `700`). A theme
that retunes `$swarm` still leaves burst gliding to 900Hz. This is the same hole the palette lint closes for
colour, one table over.

### 5. An ordering hazard the next feature will trip

`compileSound` runs `scaleVoices(compileVoices(...), pitch, stretch)`: envelopes and `repeat` grains are expanded
first, and the scalars are multiplied over the result afterwards. That is fine while every envelope is
proportional, because scaling a proportional shape is a no-op on its keys. It stops being fine the moment any
key is anchored to a real duration — the scalar would rescale an absolute time.

No shipped document hits this (nothing has both an attack and a `stretch` variant), so it is latent, not live.
It is listed because it decides the order of the migration below: the pipeline has to be fixed *before*
absolute time exists, not after.

---

## The redesign

Three separations, in dependency order. Each one compiles away; the IR stays a flat list of voices, so all three
adapters and the offline renderer are untouched.

```
tokens/default.json     audio.pitch / gain / q / dur / ramps          exists
        │
        ▼  resolve
instrument              a document + `root`: the pitch it is written at        NEW capability
        │
        ▼  use { pitch, dur, gain, env?, filter? }
figure                  phrase: notes[] + step — a sequence, unrolled          NEW voice kind
        │
        ▼
sound document          voices[] = source | use | phrase | repeat      exists, still one trigger
        │
        ▼  compileSound
IR                      flat voice list                                exists, UNCHANGED
        │
        ▼
bake / adapters         WAV, WebAudio, Phaser, Godot                   exists, UNCHANGED
```

### Separation 1 — material from note

A document declares `root`, the pitch it is written at. A `use` voice declares `pitch`, the pitch to play it at.
The compiler divides one by the other and hands the ratio to `scaleVoices`, which already multiplies every
`source.freq`, every `filter.freq`, and every freq/cutoff keyframe, and already leaves noise alone. Polyphonic
instruments transpose correctly for free.

`pitch` takes the same `PitchSchema` a source's `freq` does — `"$fifth"`, `"$tap.down2"`, a raw number that
warns. It must be an absolute pitch and not a ratio: `"pitch": 1.26` is precisely the bare number this
repository lints everywhere else, while `"pitch": "$fifth"` reuses `hz()` and inherits its typo suggestions and
its raw-value warning.

Declaring `root` is what makes a document an instrument. That is the whole of the "instrument layer" — a
capability, not a file kind.

The six degree variants disappear, and the pitch moves to the call site, where the melody already is.

### Separation 2 — absolute time from proportional time

The repo-idiomatic form is a shorthand that compiles to the keys you would have written, in the same
relationship `to` has to a `freq` track and `ngon` has to `poly`:

```json
"env": [{ "prop": "gain", "adsr": { "attack": 0.012, "decay": 0.09, "sustain": 0.3, "release": 0.05 } }]
```

Expanded to `[0..1, value]` keys once the voice's final duration is known, so nothing downstream learns it
exists. Chime stops doing division by hand; an instrument keeps its attack at every length it is played at.

This is what forces the pipeline change from finding 5. `compileVoices` currently resolves a voice and lets
`scaleVoices` multiply the result. It has to thread the pitch and stretch multipliers *down* the recursion
instead, so a voice's final Hz and final seconds are known before its envelope is expanded. That restructure
pays three times: `adsr` becomes expressible, the use-site `pitch` of separation 1 falls out as one more link in
the multiplier chain, and the latent hazard is closed rather than deferred.

It is the only structural change in this document, and it is the reason "add `root` and ship it" is the wrong
plan. Doing separation 1 alone builds instruments on a model that will mis-stretch the first one that needs an
attack.

### Separation 3 — figure from sound

```json
{ "id": "climb", "phrase": {
    "use": "ss.lib.note", "step": 0.13, "dur": 0.16,
    "notes": ["$third", "$fifth", "$seventh", "$third.up", "$seventh", "$third.up"] } }
```

`repeat` scatters in time; `phrase` sequences in it. Both are deterministic, both unroll at compile time, both
leave the IR flat. `ss.sfx.victory` becomes one voice instead of six, and its tempo becomes one number instead
of twelve hand-added offsets.

This is the first construct on the sound side with no twin on the visual side. That is defensible — time carries
an ordering that space does not — but it should be written into the schema header as a deliberate asymmetry
rather than left to be discovered as an accident.

---

## What we deliberately do not build

**A scale / degree abstraction in tokens.** Four pitch tokens tuned to the score's own key is a stated choice,
not an oversight, and a theme can already retune all four. Degrees pay off when there is more than one
composition surface to keep in agreement; that is a question for after separation 3, not before it.

**An `instruments/` directory.** The strongest property of the current design is that a library document is the
same type as a sound: `ss.lib.note` appears in the gallery, bakes to a WAV somebody can listen to, and gets
clip-checked like everything else. A second document kind would fork the loader, the gallery, the bake and the
lint to buy a filename. `lib.face` is just an asset for the same reason.

**Sustain and note-off in the IR.** The tempting version of "score materials" gives an IR voice an unbounded
length that the engine releases. It must be refused: the moment a voice has no length, `renderPCM` cannot bake
it, and the guarantee that *what you hear in the bake is what an engine plays* dies with it. That guarantee is
worth more than runtime-arbitrary note lengths. An instrument is played at a length chosen at the call site, at
compile time, and a score picks from materials baked at the lengths it declares. This is a real limitation and
is recorded here as an accepted cost, not an oversight.

---

## Migration

Each phase names the invariant it must hold. `baselines/sounds/` (28 takes, currently green) is what enforces
them, and it is why this order is safe.

| # | Change | Invariant |
|---|---|---|
| 0 | Fix finding 4a and 4b | 28/28 wav baselines unchanged |
| 1 | Thread pitch/stretch down `compileVoices`; delete the post-hoc `scaleVoices` pass | 27/28 unchanged; `hit#elite` rebaselined (below) |
| 2 | `root` + use-site `pitch`; delete 6 degree variants; rewrite the 3 fanfares | 28/28 unchanged — the same Hz by a different route |
| 3 | `adsr` + `attackMs` in `describe()`; re-author chime | **wav changes here**, deliberately: `chime` only, by 0.1dB peak |
| 4 | `phrase`; rewrite levelup / victory / gameover | unchanged |

Phase 2 removes six takes along with the six degree variants they were bakes of, so the set goes from 28 to 22.
Phase 3's one intended change is `ss.sfx.chime`: its two voices asked for a 12ms attack as `0.017` and `0.013`,
and now both ask for `0.012` in seconds, which lands the peak 0.07ms and 0.04ms from where it used to be. Peak
moves by 0.1dB, RMS and brightness not at all. Somebody should still listen to it.

Phases 0 through 2 are all but sound-neutral: they change how a document is written, not what it renders to.
Phase 1 has one exception, and it is worth recording rather than rebaselining quietly. Threading the scales
means a value is rounded once, at the end, where the old two-pass order rounded it twice. Three noise grains in
`ss.sfx.hit#elite` — the only shipped document that puts a `repeat` under a `stretch` — therefore land up to
0.1ms from where they used to, and its bake is one byte-diff. Peak and RMS are unchanged to a tenth of a dB,
the grains are the same seeds through the same filter, and the new value is the more accurate of the two.

Phase 3 is the first one that changes a sound on purpose, and the first that needs ears.

Unrelated but worth noting before anyone runs `npm run regress` and reads the result as damage: the *visual*
baselines are stale (45 changed, 127 new), while all 28 sound baselines pass. That is pre-existing drift on the
art side and is not caused by anything here.

---

## What the lint has to learn

The rule this repository already runs on is that the author cannot perceive the artifact, so anything that
matters gets measured instead — `describe()` stands in for ears, and `offBand` turns an exception into a
recorded decision. A new layer has to arrive with the measurement that guards it, or it arrives unguarded.

For the instrument layer that measurement is **attack time**, because it is the one property that must survive
being played at four lengths and the one thing `describe()` cannot currently see. Peak, RMS, brightness and
clipping say nothing about it. Time-to-90%-of-peak is about ten lines and needs no FFT.

Three lints follow from the layer itself:

- a document `use`d with `pitch` that declares no `root` — **error**, it has no idea what it was written at
- a document that declares `root` and that nothing composes — **warning**, the same rule as an unused palette
  token, one table over
- an instrument whose measured attack differs across its use sites — **warning**, which is the whole point of
  separation 2 and the only way to notice it regressing
