"""The walkers' rig — one script, one self-contained document per playable character.

    python3 scripts/walker.py            # rewrites apps/ss/assets/ss-char-arin.json
    python3 scripts/walker.py <out.json> # or somewhere else, to look at

Why a script and not a `use`: an animation only addresses the document's own
parts, and a `use` part is one node whose insides no track can reach — a shared
body composed by `use` could breathe but never walk. The roster's walks agree
with each other because they came out of one script; this is that script for
the eight survivors. The antenna and the organ stay `use` parts, moved whole,
as the eight shells did.

The body is built the way small characters in well-made games are built, and
for the reasons they give (see the game's docs/character-redesign-plan.md §2.5):
one mass for the body — a sealed cloak-coat, so there are no arms to draw a
thousand times — a helmet that is a third of the height and overlaps the
shoulders the way a top-down head does, two feet under the hem, and the two
dead feelers rising behind the helmet as the crown of the silhouette. Three
values: light helmet, mid cloak, dark feet/visor/organ. Second sketch; the
first stood the body up as a stick figure of tubes and read as nothing.
"""
import json, math, sys

R = lambda d: math.radians(d)
def r2(x): return round(x, 2)

N = 12
TS = [i / N for i in range(N + 1)]
def track(part, prop, vals, ease="linear"):
    return {"part": part, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(TS, vals)], "ease": ease}
def key3(part, prop, a, b):  # a simple there-and-back, sine eased
    return {"part": part, "prop": prop, "keys": [[0, a], [0.5, b], [1, a]]}

hair = {"color": "$ink", "width": "hair"}
thin = {"color": "$ink", "width": "thin"}

# ---------------------------------------------------------------- the body (shared by the eight)
HEAD_AT = (2.0, -8.0)
head = {"id": "head", "at": list(HEAD_AT), "rot": -10, "shape": {"kind": "ellipse", "rx": 5.3, "ry": 5.8}, "fill": "$frost.light2", "stroke": thin}
visor = {"id": "visor", "at": [4.4, -6.6], "rot": -6, "shape": {"kind": "rect", "w": 5.4, "h": 2.6, "corner": 1.3}, "fill": "$ink"}
# the cloak: one bell from the shoulders (under the helmet) to the hem, leaning a little into +x
cloak = {"id": "cloak", "at": [0, 0], "shape": {"kind": "poly",
         "points": [[-4.4, -4.8], [5.0, -4.8], [7.4, 1.4], [7.6, 6.0], [6.8, 10.6], [4.4, 11.9], [0.2, 12.3], [-4.2, 11.9], [-6.8, 10.6], [-7.6, 6.0], [-7.4, 1.6]]},
         "fill": "$frost", "stroke": thin}
cape = {"id": "cape", "at": [0, 0], "shape": {"kind": "poly",
        "points": [[-4.6, -4.8], [5.2, -4.8], [7.0, 0.2], [3.4, 2.0], [0.2, 0.9], [-3.4, 2.1], [-7.0, 0.4]]}, "fill": "$frost.light"}
organ = {"id": "organ", "at": [2.0, 1.0], "use": "ss.lib.organ", "variant": "dead", "scale": 0.72}
foot = {"id": "foot", "at": [3.6, 13.1], "shape": {"kind": "rect", "w": 4.8, "h": 2.7, "corner": 1.2}, "fill": "$slate.dark"}
foot_far = {"id": "foot_far", "at": [-1.9, 12.7], "shape": {"kind": "rect", "w": 4.2, "h": 2.4, "corner": 1.1}, "fill": "$slate"}
# the emitter: a box behind the neck, the feelers rooted in its lid
pack = {"id": "pack", "at": [-6.0, -3.6], "shape": {"kind": "rect", "w": 5.0, "h": 5.2, "corner": 1.0}, "fill": "$slate.light", "stroke": hair}
feeler = {"id": "feeler", "at": [-5.4, -5.9], "rot": -40, "scale": [0.55, 0.85], "use": "ss.lib.antenna", "variant": "dead"}
feeler_far = {"id": "feeler_far", "at": [-6.8, -5.5], "rot": -54, "scale": [0.55, 0.85], "use": "ss.lib.antenna", "variant": "dead"}

# ---------------------------------------------------------------- Arin's own
rack = {"id": "rack", "at": [-9.3, -2.8], "shape": {"kind": "rect", "w": 2.2, "h": 4.0, "corner": 0.5}, "fill": "$steel.light", "stroke": hair}
hand = {"id": "hand", "at": [7.5, 6.4], "shape": {"kind": "rect", "w": 2.8, "h": 3.6, "corner": 1.2}, "fill": "$slate.dark", "stroke": hair}
hand_far = {"id": "hand_far", "at": [-7.4, 6.0], "shape": {"kind": "rect", "w": 2.5, "h": 3.2, "corner": 1.1}, "fill": "$slate"}

parts = [feeler_far, feeler, pack, rack, foot_far, foot, hand_far, cloak, cape, organ, hand, head, visor]

# ---------------------------------------------------------------- clips
def walk(stride=2.6, lift=1.2, bob=1.4, sway=3.0):
    """Contact, passing, contact, passing — the head carries the bob (1–2px at 32), the feet
    swing ±stride and lift on the swing, the hem sways, the feelers lag a beat."""
    tr = []
    up = [-bob * (0.5 - 0.5 * math.cos(4 * math.pi * t)) for t in TS]       # highest at the passing poses
    for pid in ["head", "visor", "pack", "rack", "feeler", "feeler_far"]:
        tr.append(track(pid, "y", up))
    for pid in ["cloak", "cape", "organ", "hand", "hand_far"]:
        tr.append(track(pid, "y", [u * 0.6 for u in up]))
    def foot_tracks(pid, phase):
        xs = [stride * math.sin(2 * math.pi * (t + phase)) for t in TS]
        ys = [-lift * max(0.0, math.cos(2 * math.pi * (t + phase))) ** 1.5 for t in TS]
        tr.append(track(pid, "x", xs)); tr.append(track(pid, "y", ys))
    foot_tracks("foot", 0.0)
    foot_tracks("foot_far", 0.5)
    tr.append(track("cloak", "rot", [sway * math.sin(2 * math.pi * t) for t in TS]))
    tr.append(track("hand", "x", [-1.2 * math.sin(2 * math.pi * t) for t in TS]))
    tr.append(track("hand_far", "x", [1.0 * math.sin(2 * math.pi * t) for t in TS]))
    tr.append(track("head", "rot", [2.5 * math.sin(4 * math.pi * t + 0.8) for t in TS]))
    tr.append(track("feeler", "rot", [-8 * math.sin(4 * math.pi * t - 0.9) for t in TS]))
    tr.append(track("feeler_far", "rot", [7 * math.sin(4 * math.pi * t - 0.9) for t in TS]))
    return {"description": "contact and passing, twice: the helmet carries the bob, the feet swing under the hem and lift on the swing, the hem sways, the hands show at the cloak's edge a beat behind, and the dead feelers lag behind the box they are rooted in",
            "duration": 0.56, "tracks": tr}

def idle():
    tr = [key3(p, "y", 0, -1.0) for p in ["head", "visor", "pack", "rack", "feeler", "feeler_far"]]
    tr += [key3(p, "y", 0, -0.5) for p in ["cloak", "cape", "organ", "hand", "hand_far"]]
    tr.append({"part": "feeler", "prop": "rot", "keys": [[0, 0], [0.35, 12], [0.7, -8], [1, 0]]})
    tr.append({"part": "feeler_far", "prop": "rot", "keys": [[0, 0], [0.4, -10], [0.75, 7], [1, 0]]})
    return {"description": "the body breathes under the cloak; the dead feelers keep sweeping for a signal that never comes", "duration": 1.15, "tracks": tr}

doc = {
    "id": "ss.char.arin",
    "name": "Arin",
    "description": "The first expedition, on the day the last cartridge went in (A047), drawn the way small characters in well-made games are drawn: one mass and a big head. The mass is the programme's sealed coat — a bell of cold frost chitin-cloth from the shoulders to the hem, no arms to see — with a lighter cape over the shoulders and the dead organ worn on the chest, `ss.lib.organ#dead`, in the same place on all eight. The head is a helmet a third of the height, a pale dome with one dark visor band and no face, overlapping the shoulders the way a top-down head does. Behind the neck sits the prototype emitter, the biggest box any of the eight carries, with its cartridge rack beside it, and out of its lid rise the two dead feelers, swept back past the helmet as the crown of the silhouette — the feature the game is named for. Two feet under the hem. What the log has already measured shows in one place: the hands at the coat's edge, gone dark and hard, the saw does not mark them (A052) — the Molt's slate, the first of the body to lose its blood. Three values: the palest helmet, the frost cloak with a lighter mantle, dark feet, hands, visor and organ — the brightest cold thing on either floor. Thirteen parts on a 32px canvas, flat token fills. Gameplay radius 11. Second sketch of the roster redesign — see the game's docs/character-redesign-plan.md.",
    "tags": ["char"],
    "size": [32, 32],
    "meta": {"radius": 11},
    "parts": parts,
    "animations": {"idle": idle(), "walk": walk()},
}
out = sys.argv[1] if len(sys.argv) > 1 else "/home/user/PolyGraphics/apps/ss/assets/ss-char-arin.json"
json.dump(doc, open(out, "w"), indent=2)
print("wrote", out, "parts:", len(parts), "walk tracks:", len(doc["animations"]["walk"]["tracks"]))
