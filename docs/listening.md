# Listening

*The half of the loop the machine cannot run. Short on purpose: if it takes longer to read than to do, it
will not get done.*

The author of a sound document cannot hear it. `npm run check` measures what it can — level, peak, attack,
what a phone keeps — and the gallery draws the rest. What neither can say is whether the thing *reads*. That is
what this page is for, and it is meant to be done in five minutes per family, not an afternoon.

## Before you start

```bash
npm run check                                            # the bake, the gallery, the spectrograms
npx tsx scripts/inspect-sound.ts --against baselines     # every take beside its accepted one
open out/sound-inspect.html
```

The inspect page is self-contained: takes embedded, no server. `--against baselines` puts the accepted take
from `baselines/sounds/` beside the current one with a single transport, so the comparison is at the same
level. Pass ids to narrow it (`… ss.sfx.hit ss.sfx.hurt`).

Listen on two things: **headphones**, and then **the phone** — either the actual phone, or the `phone` toggle
on the transport, which puts a 250Hz highpass and an 8kHz lowpass in the way. Most of what is wrong with a
sound in this set is only wrong on the second one.

## For each changed take

Four answers. Write them in the PR under the take's id; one line each is enough.

| | the question | what a useful answer looks like |
|---|---|---|
| **reads as** | What is this, without looking at the name? | *a shell cracking* · *a menu beep* · *nothing, a click* |
| **sits with** | Play it, then its two nearest family peers. Which one is it now too close to, or too far from? | *reads as a second `hit`* · *fine* · *louder than `hurt`, which it should not be* |
| **wears** | Press **burst ×8**. Many of one thing, or a machine? | *many* · *machine — same grain pattern every time* |
| **fix** | If something is wrong, what, in the document's own words? | *`thump`: longer, lower* · *`grit`: too bright, half the count* · *drop the second voice* |

The fourth answer is the one that matters. *"Sounds thin"* sends the next session guessing; *"`body`: add a
lowpass around `$shell`, and the onset is too fast"* is a change somebody can make and bake before you are
back.

## For the set

Once per family PR, on the **set** tab of the gallery: play the loudest and quietest triggered sounds back to
back. If the loudest is not the one the game most needs heard, or the quietest is one the player cannot
afford to miss, say which.

## Recording it

The PR body carries the answers, under a `## Listened` heading, with the device named. A re-author PR without
one is not ready to merge — the listening record is what the PR is *for*. Documents the record does not
endorse go back to the author with the fourth column; documents it does are rebaselined, one by one, with
their new numbers next to the old.

Two takes deserve the first session regardless of what else is in the PR: `ss.sfx.chime`, whose two voices
were re-authored onto one `adsr` in PR #39 and have never been heard since, and `ss.sfx.stomp`, which was the
first sound in the set written as a gesture rather than ported, and the first to get a layer added for the
phone's sake.
