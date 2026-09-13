# Sound quality: from a faithful port to a set worth hearing

*2026-09-09. The plan for making the sound set good, in the order the repository can afford it. Builds on
[`sound-system-design.md`](sound-system-design.md) (PR #39) and reads the four open PRs as of today.*

*Status: phases 0–3 landed 2026-09-09 (#39, #51, #52, #53, and the idioms PR). Phase 4 — the re-author, one family per PR with a listening record — is next, and is the first phase that needs ears.*

The shipped set is a faithful port of the game's placeholder `switch` (PR #32). That was the right first move:
21 documents, 28 takes, byte-identical bakes, a lint, a gallery. Nothing below argues with it. It argues that the
port carried the placeholders' *sound* along with their structure, and that the tooling built to author them
cannot yet tell the difference.

---

## Where the set stands

Measured over the current bake — `renderPCM` plus a 4096-point Hann STFT, reproducible from the IR. `low` is
the share of energy below 250Hz, roughly where a laptop speaker stops and a phone speaker never started.
`attack` is time to 90% of peak.

| take | dur | attack | low | centroid | rms |
|---|---|---|---|---|---|
| `hit` | 0.09s | 1.3ms | 59% | 527Hz | −27.3 |
| `hit#elite` | 0.135s | 1.3ms | 70% | 283Hz | −26.6 |
| `shoot` | 0.06s | 1.3ms | 0% | 1237Hz | −25.3 |
| `enemy-die` | 0.10s | 3.1ms | 53% | 615Hz | −29.9 |
| `elite-die` | 0.35s | 4.8ms | 62% | 511Hz | −20.9 |
| `hurt` | 0.22s | 1.4ms | 77% | 330Hz | −21.2 |
| `pickup` | 0.07s | 1.3ms | 0% | 1782Hz | −25.1 |
| `select` | 0.08s | 1.3ms | 0% | 1010Hz | −21.9 |
| `move` | 0.035s | 1.3ms | 0% | 764Hz | −29.4 |
| `levelup` | 0.40s | 1.3ms | 0% | 1381Hz | −22.9 |
| `curse` | 0.76s | 6.8ms | 76% | 316Hz | −22.2 |
| `whoosh` | 0.90s | 270ms | 1% | 2044Hz | −28.1 |
| `stomp` (PR #44) | 0.75s | 9.7ms | **100%** | 86Hz | −18.1 |

Median of the triggered set: −24.5dBFS RMS. Four things the numbers say:

**1. Every pitched voice is a raw oscillator.** 0 of the 17 square and sawtooth voices in the set carries a
filter; the five filters that exist all sit on noise. A band-limited square is still a square — every harmonic
to Nyquist at 1/n — and a set made entirely of them has one timbre in two waveforms. This is the "chiptune
buzz" ceiling, and no amount of re-tuning pitches gets under it.

**2. Nothing has an onset.** 15 of 28 takes reach 90% of peak inside 1.5ms, which is the renderer's own declick
fade (`sound-render.ts:23`) and not anything an author wrote. Only `chime` (12.5ms) and `whoosh` (270ms)
arrive rather than start. An interface note that begins with a 1.5ms linear ramp into a square wave begins with
a click; the click is the note's identity, and it is the same click on all of them.

**3. The low end carries what the player's speaker cannot play.** `hit` puts 59% of its energy below 250Hz,
`elite-die` 62%, `curse` 76%, `hurt` 77%, and PR #44's `stomp` 100%. The game is a web game; its bus is a
laptop or a phone. Bake each take through a 250Hz highpass and measure what is left: `hit` loses 3.4dB,
`curse` 5.8, `hurt` 6.3, `hit#elite` 7.5 — and `stomp` loses 17dB, which is the footfall becoming the dust
without the foot. `describe()` cannot see any of this: `brightness` is zero crossings per second
(`sound-render.ts:216`), and `hit` reports 533 of them while most of its energy sits where the speaker rolls
off.

**4. One decay shape.** 17 of 19 oscillator voices use `[[0,1],[1,0]]` with the default `exp` ease. The ramp
floor is `EPS = 1e-4` (`sound-compile.ts:72`), so that key pair is a fixed −80dB slope across whatever span it
is given: every decay in the set is the same decay, only shorter or longer. The measured −60dB tail lands at
50–75% of the stated duration on all of them, which is the same fact from the other end.

And two things the numbers cannot say, which the PRs do:

**5. Nobody has listened.** PR #32 says the set needs ears. PR #39 ends "somebody with ears should listen to
`chime`". PR #44 ships `stomp` with an RMS figure where a verdict would go. The gallery has a waveform and a
transport: no spectrogram, no before/after, no way to hear what a phone hears. The listening half of the loop
does not exist yet, and until it does every re-author is a guess with numbers attached.

**6. The seam drops what the documents offer.** `hit#elite` is authored and never played — the game's `play(id)`
takes no variant. `hurt`, the player's own frame and the lowest, loudest sound in the set, is what the menus
play for *refused*. `levelup` is what the shop plays for *bought*. Every death that is not small is `eliteDie`,
bosses included. The set has 19 mapped ids and the game has more moments than that, so it reuses the wrong one.

---

## The open PRs, read for this plan

| PR | what it is | what this plan does with it |
|---|---|---|
| #39 instrument layer (merged) | `root` / use-site `pitch`, `adsr`, scales threaded down the recursion, `attackMs`; phase 4 (`phrase`) designed but not built | **Prerequisite.** Everything below that authors an onset needs `adsr`; everything that plays a note needs `root`. Reviewed and merged as is: typecheck clean, 41 adapter checks, 22 baselines byte-identical. `chime` still needs a listen — it is first on the phase 1 list. `phrase` lands in phase 3 below. |
| #44 footprint / `stomp` (merged) | the first sound authored as a gesture rather than ported: slam, mass, grit in three layers; +6.4dB over the set median on purpose | Two things. It is inaudible on a phone (finding 3) — a 20–30ms mid-band crack at `$grit` under the slam fixes that without touching the mass, and lands as phase 0's one document change. And its level is *right*, which is the argument for family bands over a single median (phase 2): a `field` sound should sit above an `impact` sound, and the lint should know that rather than be told per document. |
| #42 tunnel, #45 relics (merged), #48 relic batch | visual | Not sound. |

---

## What "good" means here

A sound is good when it reads as the thing it is for, on the device the game is played on, the first time and
the three-hundredth — and when it sits in the set, so that a hit under a fanfare under the score is three
things and not a smear. The repository can check the second half by machine and only measure *proxies* for the
first. So the plan is two things interleaved: make the machine measure more of what an ear would catch, and
make the human's listening cheap enough that it happens on every change.

The rule from the README stands: structure, consistency and non-regression are the machine's; taste stays with
whoever has ears. What changes is that the machine gets better instruments and the ears get a page to use them
on.

Family targets, for the lint to hold and the re-author to aim at. Loudness is K-weighted (phase 2), in dB
relative to the set anchor; `low` is the ceiling on energy below 250Hz; `attack` is authored, not the declick.

| family | loudness | attack | low ≤ | layers | fires |
|---|---|---|---|---|---|
| `impact` (hit) | −3 | ≤3ms | 45% | transient · body · tail | hundreds/run |
| `weapon` (shoot, whip) | −2 | ≤3ms | 30% | transient · body | constantly |
| `creature` (die) | 0 | ≤5ms | 55% | body · tail | often |
| `player` (hurt, daze, wound) | +3 | ≤5ms | 60% | transient · body · tail | rarely, must land |
| `pickup` | −2 | 3–6ms | 10% | onset · ring | often |
| `interface` (move, select, …) | −4 | 3–8ms | 5% | onset · ring | on input |
| `fanfare` | +2 | 4–10ms | 10% | phrase of an instrument | once |
| `world` (burst, curse, creak, whoosh) | 0 ± 3 | varies | 60% | as the gesture needs | occasionally |
| `field` (stomp, …) | +6 | ≤12ms | 85% **with a mid layer** | slam · mass · crack · debris | events |

These are starting numbers. They live in `tokens/default.json` under `audio.loudness` so that a theme can
move them and a listening session can correct them in one place; they are not a spec to argue a document into.

---

## The plan

Seven phases, in dependency order. Each names what it needs, what it gives, and the invariant the sound
baselines enforce. `baselines/sounds/` is what makes any of this checkable, and it is why the order is safe:
the phases that change *how a document is written* hold every bake byte-identical, and the phase that changes
*what a document sounds like* is the one phase that is allowed to move them — deliberately, one family per PR,
with a listening record attached.

### Phase 0 — Land the prerequisites

- Merge PR #39. Done; `chime`'s two voices now peak on the same instant, the change is 0.1dB of peak, and it
  is the one thing in that PR nobody has checked by ear.
- PR #44 merged as is. The mid-band crack for `stomp` (a `repeat` of a few grains, bandpass `$grit`, inside the
  first 30ms, at `faint`) is its own small PR: the one document change in phase 0, and the first rebaseline
  made on purpose.
- Re-pin feelers to `main` afterwards (squash creates a new SHA — the note in the feelers pipeline memory).

*Invariant: 23/23 baselines after #39 and #44; `stomp` rebaselined once, for the crack.*

### Phase 1 — Hear it

The listening half of the loop. No document changes; no bake changes.

- **Spectrogram per take.** 1024-point Hann, hop 256, log-frequency 60Hz–16kHz, 80dB range, fixed palette →
  `out/spec/<take>.png` via `pngjs` (already a dependency). Deterministic like the WAV. The gallery card shows
  it beside the waveform; the detail view shows it large. A spectrogram is the one picture that shows findings
  1–4 at a glance — the harmonic comb of an unfiltered square, the missing onset, the empty top half of `stomp`.
- **Before/after.** `scripts/inspect-sound.ts --against baselines` embeds the accepted take from
  `baselines/sounds/` beside the current one, per take, with one transport for both so the comparison is at the
  same level. A re-author PR ships this page; the reviewer opens it, not the diff.
- **The phone.** A toggle on every transport, gallery and inspect page alike, that routes playback through a
  2nd-order highpass at 250Hz and a lowpass at 8kHz. Somebody on headphones hears what the player hears. The
  `burst ×8` button keeps working through it — the phone is where repetition fatigue is worst.
- **The set tab** gains the spectral column from phase 2 as it arrives; until then it gets the spectrogram
  thumbnail.
- **A listening protocol**, written down as `docs/listening.md` and short enough to follow: for each changed
  take, on which device, four answers — *reads as* (one phrase), *sits with* (which family peer it is now too
  close to, if any), *wears* (does burst ×8 read as many or as a machine), *fix* (what, in the document's own
  vocabulary: a voice id and a direction). The answers go in the PR body. This is the "get a human to listen"
  rule from the README turned into something a session can act on the next morning.

*Needs: nothing. Gives: the ability to judge phases 4–6. Invariant: 100% of baselines unchanged.*

### Phase 2 — Measure what ears hear

`describe()` grows, and so does the lint. Measurement only; nothing in the bake moves.

New descriptors, all deterministic and all without an FFT except the centroid:

- `loudness` — K-weighted level over the sounding extent (ITU-R BS.1770 pre-filter and RLB weighting: two
  biquads, computed for 44.1kHz by the `Biquad` class already in the renderer). RMS says how much signal there
  is; this says how loud it is. A 35ms tick and a 0.9s swell can share an RMS and be 10dB apart to an ear.
- `truePeak` — peak after 4× oversampling. A 16-bit bake that measures −0.3dBFS can clip in the DAC, and
  `playbackRate` on the buffer path resamples again.
- `centroid` and `bands` — spectral centroid in Hz, and the low / mid / high energy split at 250Hz and 2kHz.
  `brightness` stays for continuity and stops being the number anyone reads.
- `phone` — `loudness` after the phase 1 phone filter. The number the player actually gets.
- `attackMs` (from PR #39) and `tail` — the −60dB point relative to peak, in seconds.

New lints, replacing the single ±9dB median band (`cli.ts:171`):

- **Family band.** Each triggered take is compared against `audio.loudness.anchor + audio.loudness[family]`
  with ±4dB tolerance, where family is `tags[1]`. `offBand` keeps its meaning and becomes rare: it is for the
  document that is off *its family's* band, not off the set's.
- **Phone survival.** `loudness − phone > 6dB` warns: *"loses 17dB on a phone — the low end is carrying this;
  give it a mid layer"*. This is finding 3 as a rule. Today it names `stomp`, `hit#elite`, `hurt` and
  `curse`, in that order, which is the right list.
- **True peak** above −1dBTP warns.
- **Unauthored onset.** A non-`impact` take whose `attackMs` equals the declick window warns: *"attack is the
  declick — write one"*. This is finding 2 as a rule.
- **Raw oscillator.** A square or sawtooth voice with no `filter` warns, in the document not the bake:
  *"unfiltered square — every harmonic to Nyquist; add a lowpass or say why"*. This is finding 1 as a rule. A
  voice silences it with a `why` string, the same way `offBand` records a decision instead of a warning to
  scroll past.

The manifest carries every new number, so the index an agent reads before authoring says what a phone hears.

*Needs: phase 1's filter definition (shared). Gives: the worklist for phase 4 — the lint will fire on most of
the set, and that list is the plan's second half made concrete. Invariant: 100% of baselines unchanged.
Warnings are expected and are the point.*

### Phase 3 — Say more with a document

Four idioms, all in the relationship `to` has to a `freq` track and `ngon` has to `poly`: each compiles to
voices the IR already knows, so the renderer and all three adapters are untouched and the bundle format stays
`polygraphics-sounds@1`. The game's own score code — the best-sounding synthesis in either repository — is
built from exactly these four things and nothing else.

- **`unison`** on an oscillator source: `{ "count": 2, "detune": 7 }` compiles to `count` copies spread
  symmetrically by ±cents, each at `gain / √count`. Width. The pad and the brass in `AudioSynth.ts` are
  detuned pairs; nothing in `sounds/` can be, today.
- **`echo`** on any voice: `{ "time": 0.42, "feedback": 0.32, "taps": 5 }` compiles to the voice repeated at
  `at + k·time` with gain × `feedback^k`, cut at the canvas with a warning. Space, flattened. The pluck's
  feedback delay is a bus effect in the game; here it is more voices, deterministic, bakeable, and PR #39's
  refusal to put a bus in the IR is honoured rather than argued with. Capped (`taps ≤ 8`, and a tap under
  −40dB is dropped), because voices are what an engine pays for.
- **`phrase`** — PR #39's phase 4, as designed: `{ "use", "step", "dur", "notes": [...] }` unrolls to `use`
  voices. `levelup`, `victory` and `gameover` become one voice each, and a fanfare's tempo becomes one number.
- **`takes`** on a document: `"takes": 3` compiles the document three times with the take index folded into
  every `repeat` and noise seed and a fixed fraction of the document's own `jitter` range, and emits takes 2
  and 3 as variants named `take-2`, `take-3`. The engine round-robins. This is the answer to finding 5's
  *wears* question for the hot path: on the buffer path, `hit` today is one buffer with a rate roll, and a rate
  roll moves the filter and the length along with the pitch — the same grain pattern three hundred times,
  slightly transposed. Three seeded alternates are three buffers and a counter, and every one of them is a
  baseline.
- `meta` hints, no schema change since `meta` is already an open record: `polyphony` (how many of this may
  sound at once), `duck` (dB the score should drop while this plays). The game reads them the way it reads
  `minInterval` now.

*Needs: phase 0 (`adsr`, `root`). Gives: the vocabulary phase 4 authors in, and phase 6 needs. Invariant: every
shipped take byte-identical, because no shipped document uses the new words until phase 4 — with the one
exception that the three fanfares are rewritten on `phrase` and must bake identically, which is the test.
`scripts/test-webaudio-adapter.ts` gains a check per idiom. Landed as designed; the fanfares baked
byte-identical on `phrase`, and the suite is at 69 checks.*

### Phase 4 — Re-author the set

The quality work. Everything before it is what makes it checkable. One family per PR, ordered by how often the
game fires it, so the most-heard sounds are fixed first and the listening budget is spent where it counts.

Five rules join the README's "for AI agents" list, and phase 2's lint holds them:

8. A square or sawtooth voice carries a `filter`, or a `why`.
9. An impact is three layers: a transient (noise grains, under 20ms), a body (the pitch), a tail (what is
   left after). An interface sound is two: an onset and a ring. One raw voice is a placeholder.
10. An onset is written in seconds (`adsr.attack`). The declick is the engine's, not the author's.
11. Nothing outside `field` puts more than its family's ceiling below 250Hz; nothing in `field` ships without a
    mid-band layer. If the player cannot hear it on a phone, the sound is not there.
12. A decay to 0 is an −80dB slope. For a tail that lasts, end the key on a level and let the declick take it —
    or write a `sustain`.

Direction per family — a brief, not a spec. Ears revise it.

| family | what changes |
|---|---|
| `impact` | `hit` stays the smallest sound in the set but stops being sub-only: the thump goes through a lowpass that opens for 20ms and closes, the grit gets brighter and shorter, and it ships with `takes: 3`. Its phone number is the acceptance test. `hit#elite` gets played (phase 5). |
| `weapon` | `shoot` gains a 6ms noise tick at `$gust` in front of the chirp — a thing leaving a tube has a breath. `whip` gains swept bandpass air over the sawtooth, because a lash is mostly air. Both `takes: 3`. |
| `creature` | `enemy-die` becomes a chirp coming apart into two or three grains rather than a pitch fading. `elite-die` keeps its fall and gains a mid crack and a grit tail. A `boss-die` document exists (phase 5) instead of the elite one standing in. |
| `player` | `hurt` keeps the claim that nothing sits lower, and stops being *only* low: a `unison` sawtooth pair at `$bone` under a lowpass sweep, a noise slam ahead of it, a 4ms attack. The phone hears the slam and the sweep; the headphones hear the frame. |
| `pickup` | `pickup` and `food` get a 3ms onset and a second voice a fifth above at `hush`, so they sparkle rather than beep. |
| `interface` | `select` and `move` move to triangle or filtered square with a 4ms onset; `select` gets `unison: 2` for a little width. `chime` is already the best-authored document in the set and moves last, if at all. |
| `fanfare` | `ss.lib.note` gets a lowpass at `$tonic.up` and a 4ms `adsr` attack, and the three fanfares are `phrase`s of it. `victory` gets one `echo` tap at `hush`. `ss.lib.knell` gets the same treatment an octave down. |
| `world` | `burst` and `curse` gain filters and a shared onset. `creak` and `whoosh` are already gestures and stay. `stomp` gets its crack (phase 0). |

Each PR ships: the before/after inspect page, the listening record from `docs/listening.md`, the rebaselined
takes named one by one with their new numbers, and no visual baseline changes. A re-author that the listening
record does not endorse does not merge; the record is what the PR is *for*.

*Needs: phases 1–3. Gives: the set. Invariant: baselines change on purpose, one family at a time, each change
named. The visual baselines stay untouched throughout.*

### Phase 5 — Fill the seam

The game plays what exists, so the documents come first and the wiring second.

New documents, each with the family it belongs to, so the phase 2 band applies from the first bake:

- `interface`: `deny`, `back`, `open`, `close`, `buy`, `toggle`. The menus stop playing `hurt` for refusal and
  `levelup` for purchase.
- `creature`: `boss-die`; `spawn` (a hatch or a summon — feelers #91, and the broodling that already lays).
- `player`: `daze` (feelers #74) and `wound` (#75) — the two states the body already shows and does not say.
- `terrain`: `web` (#82, being slowed) and `tunnel` (#81, going in and it caving behind you). `stomp` is
  already `field`.
- `pickup`: `relic` — a find, distinct from a chest opening. Today it is `burst`.

And in feelers (issue #102's first half, effects rather than instruments):

- `play(id, { variant, pan, gain })`; `bakeAll` bakes every variant a mapped id has; elites play `hit#elite`;
  takes round-robin by a counter, jitter on top.
- Pan from world x. An adapter-only change — `playBuffer` and `play` grow a `pan` option that inserts a
  `StereoPannerNode` — and no IR change, because where a sound comes from is the engine's to know, the same
  way a whole-body transform is. The README roadmap's "panning" item closes here, on the engine side.
- A safety limiter on the master (`DynamicsCompressorNode`, threshold high, fast release) so five hits under a
  fanfare under the score do not clip the destination. PolyGraphics guarantees no *take* clips; the mix is the
  game's.
- The score ducks by `meta.duck` while a fanfare plays.

*Needs: phase 4's vocabulary (the new documents should be authored to rule 9, not ported). Gives: the game
playing the right sound at the right moment. Invariant: new baselines only.*

### Phase 6 — Score materials

Issue #102's second half, and the README roadmap's last sound item. The scheduler stays in `AudioSynth.ts` —
it is game state made audible. What moves is what it plays: the pad, the brass, the thump and the pluck, which
are today the four best-sounding things in either repository and the four least legible.

- `ss.inst.pad`, `ss.inst.brass`, `ss.inst.thump`, `ss.inst.pluck`, each with a `root`. The pad is a
  `unison` triangle pair under a low-Q lowpass with an `adsr` attack in seconds; the brass is a `unison`
  sawtooth stack under a cutoff sweep across the bar; the thump is a sine with `to` and a 12ms attack and is
  expressible today; the pluck is a sine with an `echo`.
- PR #39's accepted cost stands: no note-off, no unbounded voice. The score plays materials at lengths the
  documents declare — the bar lengths are `9.0`, `7.5`, `6.0` and `4.6` seconds across four intensity buckets,
  and the four chords are four `pitch`es — and crossfades at bar boundaries as it does now.
- Long takes are a baseline problem: sixteen pad takes at up to twelve seconds is seventeen megabytes of WAV in
  git. `regress` learns a hash-only baseline (`baselines/sounds/<take>.sha256`) for takes over three seconds;
  the WAV stays in `out/`, and the shortest length of each material keeps a real WAV so it is still a take
  somebody can listen to.
- The pad's per-bar cutoff wander (`Math.random() * 160` in the game) either becomes a `jitter` roll or is
  dropped. Ears decide; the listening protocol has a row for it.

*Needs: phases 1 and 3, and phase 4's ears for calibration. Gives: `AudioSynth.ts` down to a scheduler, and a
score that retunes with the same four tokens the effects do. Invariant: the effect baselines do not move; the
material baselines are new.*

### Deferred — the `@2` format

Some things do need the IR to change, and every one of them breaks the bundle guard in feelers. They are
batched, and the batch happens only if phase 4's listening record says the set cannot get there without them:

- **`drive`** on a voice — a tanh waveshaper. Brass and `hurt` are the documents that would ask.
- **`noise.color`** — pink or brown. A lowpass on white already covers the brown that `stomp` wanted; pink is
  the one shape a biquad cannot make, and nothing has asked for it.
- **A second filter** per voice, or a `highpass` pre-stage, so a low body can be cleaned without a `use`.
- **Stereo width** in the document (distinct from pan, which is the engine's). A `unison` pair panned apart.

One bump, `polygraphics-sounds@2`, with the renderer, the adapter and the feelers seam updated together.

---

## What we deliberately do not build

- **Samples.** The repository synthesizes. A recorded impact would be the one thing in it nobody can read.
- **Bus effects in the IR** — reverb, delay lines, compression as nodes. `echo` flattens the one that matters
  into voices; the rest is the engine's mix, and PR #39's boundary holds.
- **Note-off.** Recorded as an accepted cost in PR #39; still accepted. A material is played at a length
  chosen at compile time.
- **A mixer in PolyGraphics.** Levels between families are hints in tokens and `meta`; the game holds the
  faders, the ducking and the limiter.
- **A gallery editor.** The document is the editor. The gallery gets better at *showing*, not at *changing*.

---

## Why this order

Hearing and measuring come before authoring, because authoring without either is how the placeholders got
ported in the first place. Idioms come before the re-author so the set is written once, in the vocabulary it
will keep, rather than written in the old one and rewritten. The seam comes after the documents because the
game can only play what exists. The score comes last because it is the largest, the least certain, and the
one thing whose current form actually sounds good — it is the least urgent to move and the most expensive to
get wrong.

Phases 1 and 2 are independent of each other and of PR #39 and can start today. Phase 3 can start the day #39
merges. Phase 4 should not start before 1 and 2 exist, whatever the temptation; a re-author that cannot be
heard or measured is another port.

---

## Definition of done

Measured, and checked by `npm run check`:

- every triggered take inside its family band, with no more than two `offBand` exceptions in the set
- no triggered take loses more than 6dB through the phone filter
- every square and sawtooth voice filtered or explained; every non-impact onset authored
- `hit`, `shoot`, `enemy-die` and `pickup` ship three takes each

Heard, and recorded in the PRs:

- one listening session per family, on headphones and on a phone, with the four answers written down
- burst ×8 of each hot-path document answers *wears* with "many", not "machine"

Wired:

- feelers plays variants, takes and pan; `hurt` is no longer a refusal and `levelup` is no longer a receipt
- the score's four materials come from documents, and `AudioSynth.ts` is a scheduler and a mixer

Roughly: 21 documents become 36, 28 takes become 60 plus the materials, and the README's last sound roadmap
item — *re-author the placeholder gestures, spectrograms, panning, the score's materials* — closes.

---

## Checks, per phase

```bash
npm run check                               # lint, bake, gallery — the one command
npm run regress                             # byte-compare against baselines/sounds
npx tsx scripts/test-webaudio-adapter.ts    # renderer and adapter agree
npx tsx scripts/inspect-sound.ts --against baselines ss.sfx.hit   # phase 1: the page a reviewer opens
```
