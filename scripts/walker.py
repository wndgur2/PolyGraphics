"""The walkers' rig — one script, one self-contained document per playable character.

    python3 scripts/walker.py            # rewrites apps/ss/assets/ss-char-arin.json
    python3 scripts/walker.py <out.json> # or somewhere else, to look at

Skeleton first, parts second, motion last — docs/character-rig-guide.md says why
and in what order. Everything below is derived from the SKELETON block: a facing,
a shoulder line, a hip line, the head, the feet, and the points the kit hangs
from. A part is placed by naming the joint it hangs from plus a length and an
angle, never by a coordinate typed on its own; a clip turns joints, and the
part's x/y follow from the turn.

Why a script and not a `use`: an animation only addresses the document's own
parts, and a `use` part is one node whose insides no track can reach — a shared
body composed by `use` could breathe but never walk. The roster's walks agree
with each other because they came out of one script; this is that script for
the eight survivors. The antenna and the organ stay `use` parts, moved whole.

First sketch: Arin only. The other seven are the same skeleton with a row of
parameters each — see the game's docs/character-redesign-plan.md, section 3.2.
"""
import json, math, sys

R = lambda d: math.radians(d)
def r2(x): return round(x, 2)
def add(a, b): return (a[0] + b[0], a[1] + b[1])

# ============================================================== 1. skeleton and pose
# Canvas 32×32, origin at the centre, +x right, +y down. The body faces the
# viewer's FRONT-RIGHT (a three-quarter view from a little above), so the near
# side is the right side of the picture and the far side is the left. The engine
# mirrors the whole frame to walk left.
SKELETON = {
    # the shoulder line: far shoulder up and left, near shoulder down and right,
    # tilted about 6° because the near side is closer to the camera
    "shoulder_far":  (-5.6, -4.4),
    "shoulder_near": (6.2, -3.2),
    # the hip line, under the coat, less tilted than the shoulders
    "hip_far":  (-2.0, 11.0),
    "hip_near": (3.6, 12.0),
    # the head: centre and the tilt of the helmet's long axis (leaning back a touch)
    "head": (2.0, -8.0), "head_tilt": -10,
    # where each foot meets the ground
    "foot_far": (-1.9, 12.7), "foot_near": (3.6, 13.1),
    # the kit: the emitter box behind the far shoulder, and the two feelers rooted in its lid
    "pack": (-6.0, -3.6),
    "feeler_root": (-5.4, -5.9), "feeler_far_root": (-6.8, -5.5),
}
S = SKELETON
# the pose: the coat leans a little into the walk, the arms hang a few degrees off
# vertical (the near one forward, the far one out from the body)
POSE = {"coat_lean": 2, "arm_hang": -4, "arm_far_hang": 10, "visor_turn": -5}

# proportions, in px: the head is a third of the height
HEAD_R = (5.3, 5.8)
UPPER = {"arm_len": 7.6, "arm_w": 3.0, "arm_far_len": 7.0, "arm_far_w": 2.6, "hand_r": (1.7, 1.9), "hand_far_r": (1.4, 1.6)}

hair = {"color": "$ink", "width": "hair"}
thin = {"color": "$ink", "width": "thin"}

def hang(joint, length, angle):
    """The centre of a link of `length` hanging from `joint`, turned `angle` degrees off straight down."""
    return (joint[0] - length / 2 * math.sin(R(angle)), joint[1] + length / 2 * math.cos(R(angle)))

def below(joint, dist, angle):
    """A point `dist` down the same hanging line."""
    return (joint[0] - dist * math.sin(R(angle)), joint[1] + dist * math.cos(R(angle)))

# ============================================================== 2. masses, from the joints
# the head: an egg on the shoulder line, a little forward, overlapping the shoulders
head = {"id": "head", "at": [*S["head"]], "rot": S["head_tilt"], "shape": {"kind": "ellipse", "rx": HEAD_R[0], "ry": HEAD_R[1]}, "fill": "$frost.light2", "stroke": thin}
# the visor: a band on the front-right of the helmet — 60% of its width, turned toward the viewer
visor = {"id": "visor", "at": [r2(S["head"][0] + 1.6), r2(S["head"][1] + 1.2)], "rot": POSE["visor_turn"], "shape": {"kind": "rect", "w": 6.6, "h": 2.6, "corner": 1.3}, "fill": "$ink"}

# the coat: one bell from the shoulder line (inset a little from the joints) to a
# rounded hem past the hips. The single mass of the body.
sf, sn = S["shoulder_far"], S["shoulder_near"]
cloak = {"id": "cloak", "at": [0, 0], "rot": POSE["coat_lean"] - 2, "shape": {"kind": "poly", "points": [
    [r2(sf[0] + 0.8), r2(sf[1] - 0.2)], [r2(sn[0] - 0.8), r2(sn[1] - 0.2)],
    [7.5, 1.6], [7.7, 6.0], [6.8, 10.6], [4.4, 11.9], [0.2, 12.3], [-4.2, 11.9], [-6.8, 10.6], [-7.6, 6.0], [-7.2, 1.2]]},
    "fill": "$frost", "stroke": thin}
# the mantle over the shoulders: its top edge IS the shoulder line, its hem falls in two lobes
cape = {"id": "cape", "at": [0, 0], "shape": {"kind": "poly", "points": [
    [r2(sf[0]), r2(sf[1] - 0.2)], [r2(sn[0]), r2(sn[1] - 0.2)], [7.3, 0.9], [3.4, 2.4], [0.2, 1.3], [-3.4, 2.2], [-7.0, 0.2]]},
    "fill": "$frost.light"}
# the dead organ, worn as the mantle's clasp — the same place on all eight
organ = {"id": "organ", "at": [1.0, 1.0], "use": "ss.lib.organ", "variant": "dead", "scale": 0.72}

# the feet, on their ground points
foot = {"id": "foot", "at": [*S["foot_near"]], "shape": {"kind": "rect", "w": 4.8, "h": 2.7, "corner": 1.2}, "fill": "$slate.dark"}
foot_far = {"id": "foot_far", "at": [*S["foot_far"]], "shape": {"kind": "rect", "w": 4.2, "h": 2.4, "corner": 1.1}, "fill": "$slate"}

# the arms: a sleeve and a hand each, hanging from the ENDS of the shoulder line.
# Near arm at the right flank, half over the coat's outline; far arm at the left
# flank behind the coat, a sliver of sleeve and hand past the edge.
a_c = hang(sn, UPPER["arm_len"], POSE["arm_hang"])
arm = {"id": "arm", "at": [r2(a_c[0]), r2(a_c[1])], "rot": POSE["arm_hang"], "shape": {"kind": "rect", "w": UPPER["arm_w"], "h": UPPER["arm_len"], "corner": 1.4}, "fill": "$frost", "stroke": hair}
h_c = below(sn, UPPER["arm_len"] + 0.9, POSE["arm_hang"])
hand = {"id": "hand", "at": [r2(h_c[0]), r2(h_c[1])], "shape": {"kind": "ellipse", "rx": UPPER["hand_r"][0], "ry": UPPER["hand_r"][1]}, "fill": "$slate.dark", "stroke": hair}
af_c = hang(sf, UPPER["arm_far_len"], POSE["arm_far_hang"])
arm_far = {"id": "arm_far", "at": [r2(af_c[0]), r2(af_c[1])], "rot": POSE["arm_far_hang"], "shape": {"kind": "rect", "w": UPPER["arm_far_w"], "h": UPPER["arm_far_len"], "corner": 1.2}, "fill": "$frost.dark"}
hf_c = below(sf, UPPER["arm_far_len"] + 0.9, POSE["arm_far_hang"])
hand_far = {"id": "hand_far", "at": [r2(hf_c[0]), r2(hf_c[1])], "shape": {"kind": "ellipse", "rx": UPPER["hand_far_r"][0], "ry": UPPER["hand_far_r"][1]}, "fill": "$slate"}

# the kit: the emitter behind the far shoulder, the feelers rising from its lid,
# long, thin and swept back past the helmet as the crown of the silhouette
pack = {"id": "pack", "at": [*S["pack"]], "shape": {"kind": "rect", "w": 5.0, "h": 5.2, "corner": 1.0}, "fill": "$slate.light", "stroke": hair}
feeler = {"id": "feeler", "at": [*S["feeler_root"]], "rot": -40, "scale": [0.55, 0.85], "use": "ss.lib.antenna", "variant": "dead"}
feeler_far = {"id": "feeler_far", "at": [*S["feeler_far_root"]], "rot": -54, "scale": [0.55, 0.85], "use": "ss.lib.antenna", "variant": "dead"}

# ============================================================== 3. Arin's own
rack = {"id": "rack", "at": [r2(S["pack"][0] - 3.3), r2(S["pack"][1] + 0.8)], "shape": {"kind": "rect", "w": 2.2, "h": 4.0, "corner": 0.5}, "fill": "$steel.light", "stroke": hair}

# ============================================================== 4. depth = draw order
# far to near, for a body facing front-right: feelers and the pack behind the far
# shoulder, the far arm, the feet under the hem, the coat, the mantle and its
# clasp, the near arm, the head over the shoulders.
parts = [feeler_far, feeler, pack, rack, arm_far, hand_far, foot_far, foot, cloak, cape, organ, arm, hand, head, visor]

# ============================================================== 5. motion: turn joints
N = 12
TS = [i / N for i in range(N + 1)]
def track(part, prop, vals, ease="linear"):
    return {"part": part, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(TS, vals)], "ease": ease}
def key3(part, prop, a, b):
    return {"part": part, "prop": prop, "keys": [[0, a], [0.5, b], [1, a]]}

def swing(joint, centre, theta):
    """A part hanging from `joint`, turned by theta about it: the x/y its centre sweeps, and the rot."""
    dx, dy = centre[0] - joint[0], centre[1] - joint[1]
    c, sn_ = math.cos(R(theta)), math.sin(R(theta))
    return (dx * c - dy * sn_ - dx, dx * sn_ + dy * c - dy, theta)

def walk(stride=2.6, lift=1.2, bob=1.4, sway=3.0, arm_swing=14):
    """Contact, passing, contact, passing. The head carries the bob (1–2px at 32),
    the feet swing ±stride and lift on the forward swing, the hem sways, each
    arm turns about its shoulder against the foot on its side, the feelers lag."""
    tr = []
    up = [-bob * (0.5 - 0.5 * math.cos(4 * math.pi * t)) for t in TS]  # highest at the passing poses
    for pid in ["head", "visor", "pack", "rack", "feeler", "feeler_far"]:
        tr.append(track(pid, "y", up))
    for pid in ["cloak", "cape", "organ"]:
        tr.append(track(pid, "y", [u * 0.6 for u in up]))
    def foot_tracks(pid, phase):
        xs = [stride * math.sin(2 * math.pi * (t + phase)) for t in TS]
        ys = [-lift * max(0.0, math.cos(2 * math.pi * (t + phase))) ** 1.5 for t in TS]
        tr.append(track(pid, "x", xs)); tr.append(track(pid, "y", ys))
    foot_tracks("foot", 0.0)
    foot_tracks("foot_far", 0.5)
    tr.append(track("cloak", "rot", [sway * math.sin(2 * math.pi * t) for t in TS]))
    def arm_tracks(joint, pieces, sign):
        cols = {pid: ([], [], []) for pid, _ in pieces}
        for t, u in zip(TS, up):
            th = sign * arm_swing * math.sin(2 * math.pi * t)
            for pid, centre in pieces:
                dx, dy, rot = swing(joint, centre, th)
                cols[pid][0].append(dx); cols[pid][1].append(dy + u * 0.6); cols[pid][2].append(rot)
        for pid, (xs, ys, rs) in cols.items():
            tr.extend([track(pid, "x", xs), track(pid, "y", ys), track(pid, "rot", rs)])
    arm_tracks(sn, [("arm", a_c), ("hand", h_c)], +1)       # back while the near foot is forward
    arm_tracks(sf, [("arm_far", af_c), ("hand_far", hf_c)], -1)
    tr.append(track("head", "rot", [2.5 * math.sin(4 * math.pi * t + 0.8) for t in TS]))
    tr.append(track("feeler", "rot", [-8 * math.sin(4 * math.pi * t - 0.9) for t in TS]))
    tr.append(track("feeler_far", "rot", [7 * math.sin(4 * math.pi * t - 0.9) for t in TS]))
    return {"description": "contact and passing, twice: the helmet carries the bob, the feet swing under the hem and lift on the swing, the hem sways, the arms turn about their shoulders against the foot on their side, and the dead feelers lag behind the box they are rooted in",
            "duration": 0.56, "tracks": tr}

def idle():
    tr = [key3(p, "y", 0, -1.0) for p in ["head", "visor", "pack", "rack", "feeler", "feeler_far"]]
    tr += [key3(p, "y", 0, -0.5) for p in ["cloak", "cape", "organ", "arm", "hand", "arm_far", "hand_far"]]
    tr.append({"part": "feeler", "prop": "rot", "keys": [[0, 0], [0.35, 12], [0.7, -8], [1, 0]]})
    tr.append({"part": "feeler_far", "prop": "rot", "keys": [[0, 0], [0.4, -10], [0.75, 7], [1, 0]]})
    return {"description": "the body breathes under the coat; the dead feelers keep sweeping for a signal that never comes", "duration": 1.15, "tracks": tr}

doc = {
    "id": "ss.char.arin",
    "name": "Arin",
    "description": "The first expedition, on the day the last cartridge went in (A047), drawn the way small characters in well-made games are drawn: one mass and a big head, on a skeleton laid down first (docs/character-rig-guide.md). The body faces the viewer's front-right, so a shoulder line runs from the far shoulder, up and left, to the near one, down and right, and everything hangs from it: the programme's sealed coat — a bell of cold frost chitin-cloth to a rounded hem — with a lighter mantle whose top edge is that line, the dead organ worn as its clasp, `ss.lib.organ#dead`, in the same place on all eight; the near (right) arm at the right flank, half over the coat's outline; the far (left) arm at the left flank behind the coat, a sliver of sleeve and hand past the edge. The head is a helmet a third of the height, a pale egg with one dark visor band turned toward the viewer and no face, overlapping the shoulders the way a top-down head does. Behind the far shoulder sits the prototype emitter, the biggest box any of the eight carries, with its cartridge rack beside it, and out of its lid rise the two dead feelers, swept back past the helmet as the crown of the silhouette — the feature the game is named for. Two feet under the hem. What the log has already measured shows in one place: the hands, gone dark and hard, the saw does not mark them (A052) — the Molt's slate, the first of the body to lose its blood. Three values: the palest helmet, the frost coat with a lighter mantle, dark feet, hands, visor and organ — the brightest cold thing on either floor. Fifteen parts on a 32px canvas, flat token fills. Gameplay radius 11. Second sketch of the roster redesign — see the game's docs/character-redesign-plan.md.",
    "tags": ["char"],
    "size": [32, 32],
    "meta": {"radius": 11},
    "parts": parts,
    "animations": {"idle": idle(), "walk": walk()},
}
out = sys.argv[1] if len(sys.argv) > 1 else "/home/user/PolyGraphics/apps/ss/assets/ss-char-arin.json"
json.dump(doc, open(out, "w"), indent=2)
print("wrote", out, "parts:", len(parts), "walk tracks:", len(doc["animations"]["walk"]["tracks"]))
