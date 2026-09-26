"""The Molt (feelers `skeleton`, the Rattle) — a shed shell still walking.

    python3 scripts/skeleton.py        # rewrites apps/ss/assets/ss-enemy-skeleton.json

The flats' armoured walker (feelers `skeleton`: speed 72, radius 10, hp 24,
power 10 — "Old chitin still walking. Hits harder than what's left of it
suggests"), arriving in crowds after the Husks. Nobody is inside it: it is the
exuvia a drone climbed out of — the empty case a cicada leaves on a stalk,
split down the front — and the hive's signal rattles around in it and walks it.

It was hand-placed as a cluster of grey plates: two slabs, a bar of ink between
them and a lid, on two posts, and its rattle moved 3.6px at game scale. Nothing
in it said insect, or shell, or walking. So the drawing now says each of those
once, at a size that survives 1.2×:

  - an insect's case: a hooded head capsule jutting forward with the empty
    socket of an eye, a big segmented back half, a narrow lit front plate,
    raptorial forelegs folded under the hood with hooked tips (the cicada
    nymph's digging arms — which is where the hitting comes from), and two
    jointed hind legs with hooked tarsi that walk it
  - a split: the two halves hang off one hinge under the hood and part along
    the front in a lens, and the lens is where the light is — the faint organ
    and its glow sit in the dark inside, framed by the halves
  - a rattle: the halves are loose, so every footfall claps them shut and they
    bounce, twice, before they hang open again

Built on the shared rig (scripts/rig.py): a pelvis root, a spine bone for the
case, the two halves as bones off the hinge, a hood on the spine, forelegs on
the front half, and hind legs solved every frame to a foot on the floor. The
game mirrors it to face its heading (EnemySystem `faceSide`) and plays the clip
at a fixed rate (no `animTracksSpeed`).
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 32×36 (grown from 32×32 for the step and the drop), origin at the centre, +x forward, +y down.
SIZE = [32, 36]
GROUND = 13.4
PELVIS = (-1.2, 4.6)
HINGE = (1.6, -7.2)

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, PELVIS, 0.0)
# The case stands up off the pelvis, leaning a little into the walk.
bone("spine", "body", PELVIS, math.degrees(math.atan2(HINGE[1] - PELVIS[1], HINGE[0] - PELVIS[0])),
     math.hypot(HINGE[0] - PELVIS[0], HINGE[1] - PELVIS[1]))
# The two halves hang off the hinge under the hood.
bone("back", "spine", HINGE, 98.0, 12.0)
bone("front", "spine", HINGE, 78.0, 12.0)
# The hood sits on the top of the case, over the hinge.
bone("hood", "spine", (0.4, -8.4), 0.0, 7.0)

# Raptorial forelegs, off the front plate, held the way a mantis holds them:
# a toothed femur up and forward, the tibia folded down in front of it,
# ending in a hook turned back — the grab, and the silhouette's front edge.
FORE = {  # side: (shoulder, femur heading, femur len, tibia heading, tibia len)
    "far": ((3.6, -1.8), -36.0, 5.0, 96.0, 4.4),
    "near": ((4.4, -0.6), -30.0, 5.4, 102.0, 4.8),
}
for side, (sh, hf, lf, ht, lt) in FORE.items():
    b = bone(f"{side}_femur", "front", sh, hf, lf)
    bone(f"{side}_tibia", f"{side}_femur", b.end(), ht, lt)

# The hind legs: thigh, shin and a tarsus, solved to a foot on the floor with
# the knee thrown forward.
LEGS = {  # leg: (hip, rest foot x, thigh, shin)
    "far": ((-2.2, 4.4), -3.4, 4.6, 5.0),
    "near": ((-0.4, 5.0), 1.4, 4.6, 5.0),
}
KNEE = 1  # knee forward of the hip-foot line
for leg, (hip, fx, l1, l2) in LEGS.items():
    h1, h2 = ik(hip, (fx, GROUND), l1, l2, KNEE)
    bone(f"{leg}_thigh", "body", hip, h1, l1)
    bone(f"{leg}_shin", f"{leg}_thigh", RIG.end_of(f"{leg}_thigh"), h2, l2)
    bone(f"{leg}_foot", f"{leg}_shin", RIG.end_of(f"{leg}_shin"), 0.0, 2.4)

RIG.seal()
solve = RIG.solve
put, on_bone, use = RIG.put, RIG.on_bone, RIG.use

# ============================================================== parts
# Cold grey where the Husk is warm bone. Three values: the front plate and
# hood the lightest, the back half the body tone, the far limbs and the
# sutures a step down; the inside of the case is ink.
LIT, BODY, SHADE, FAR = "$steel.light2", "$steel", "$steel.dark", "$slate.light"
HOOD = "$steel.light"

def rel(pts, origin):
    """World points as offsets from `origin` — a part whose origin is its hinge turns about the hinge."""
    return [(x - origin[0], y - origin[1]) for x, y in pts]

def seg(id, bone_name, w0, w1, fill, stroke=INK_HAIR):
    at, a = on_bone(bone_name)
    return put(id, bone_name, at, a, bar(BONES[bone_name].length, w0, w1), fill, stroke)

def hind_leg(leg, thigh, shin):
    seg(f"{leg}_thigh", f"{leg}_thigh", 2.6, 1.9, thigh)
    # The shin: thin, with a spur at the heel.
    at, a = on_bone(f"{leg}_shin")
    L = BONES[f"{leg}_shin"].length
    put(f"{leg}_shin", f"{leg}_shin", at, a,
        poly([(-0.6, -0.8), (0.0, -1.0), (L, -0.6), (L + 0.5, -0.4), (L + 1.3, -1.3), (L + 0.9, 0.2), (L + 0.4, 0.6), (0.0, 0.9), (-0.6, 0.7)]),
        shin, INK_HAIR)
    # The tarsus: a thin foot with a hooked claw forward.
    at, a = on_bone(f"{leg}_foot")
    put(f"{leg}_foot", f"{leg}_foot", at, a,
        poly([(-0.6, -0.6), (1.8, -0.5), (2.8, -0.2), (3.4, 0.6), (2.8, 0.9), (2.4, 0.4), (-0.4, 0.6)]), shin, INK_HAIR)

def foreleg(side, femur, tibia):
    at, a = on_bone(f"{side}_femur")
    L = BONES[f"{side}_femur"].length
    # A swollen femur with a row of teeth on the inside.
    put(f"{side}_femur", f"{side}_femur", at, a,
        poly([(-0.6, -0.9), (L * 0.4, -1.4), (L, -0.8), (L + 0.6, 0.0), (L, 0.9), (L * 0.75, 1.5), (L * 0.6, 1.0),
              (L * 0.45, 1.6), (L * 0.3, 1.0), (-0.6, 0.9)]), femur, INK_HAIR)
    at, a = on_bone(f"{side}_tibia")
    L = BONES[f"{side}_tibia"].length
    # The tibia: a blade folded down and back under the femur, ending in a
    # hook that curls forward — the grab.
    put(f"{side}_tibia", f"{side}_tibia", at, a,
        poly([(-0.5, -0.8), (L * 0.5, -0.8), (L, -0.6), (L + 1.0, 0.2), (L + 0.9, 1.8), (L + 0.2, 0.9),
              (L * 0.7, 0.6), (L * 0.55, 1.2), (L * 0.4, 0.6), (-0.5, 0.7)]), tibia, INK_HAIR)

# ---- far side, behind everything
hind_leg("far", FAR, FAR)
foreleg("far", FAR, FAR)

# ---- the inside of the case: dark, the glow, the faint organ in the split
INSIDE = [(1.6, -7.6), (3.6, -5.0), (4.2, -1.0), (3.6, 3.0), (1.8, 6.4), (-0.4, 3.2), (-1.0, -1.0), (-0.4, -5.0)]
put("inside", "spine", HINGE, 0.0, poly(rel(INSIDE, HINGE)), "$ink")
SPLIT = (1.6, -0.8)
put("gap_glow", "spine", SPLIT, 0.0, ell(2.0, 4.6), "$pheromone@soft")
use("organ", "spine", SPLIT, "ss.lib.organ", scale=[0.56, 0.72], variant="faint")
use("organ_bright", "spine", SPLIT, "ss.lib.organ", scale=[0.6, 0.8], opacity=0)

# ---- the back half: the big blank case, segmented, trailing. Its front
# edge bows back at the middle, which is half of the lens.
BACK = [(1.6, -7.6), (-1.0, -9.4), (-4.6, -8.8), (-7.2, -5.6), (-8.2, -1.4), (-7.6, 2.8), (-5.6, 5.8), (-2.4, 7.2),
        (0.6, 6.8), (1.5, 5.2), (0.4, 2.2), (0.0, -1.0), (0.4, -4.2), (1.2, -6.4)]
put("shell_back", "back", HINGE, 0.0, poly(rel(BACK, HINGE)), BODY, INK_THIN)
BACK_SHADE = [(-8.0, -0.6), (-7.6, 2.8), (-5.6, 5.8), (-2.4, 7.2), (0.6, 6.8), (1.5, 5.2), (0.8, 3.6), (-2.2, 5.0), (-5.2, 4.2), (-7.0, 1.6)]
put("back_shade", "back", HINGE, 0.0, poly(rel(BACK_SHADE, HINGE)), SHADE)
# Three sutures across the back: the segments of the abdomen, bowed.
SUTURES = [
    [(-6.8, -5.2), (-4.0, -4.4), (-1.2, -4.0), (0.2, -4.2), (0.2, -3.4), (-1.2, -3.2), (-4.0, -3.6), (-7.0, -4.4)],
    [(-7.8, -1.6), (-4.4, -0.6), (-1.2, -0.2), (0.0, -0.4), (0.0, 0.4), (-1.2, 0.6), (-4.4, 0.2), (-7.8, -0.8)],
    [(-7.0, 2.4), (-4.2, 3.2), (-1.2, 3.4), (0.4, 2.8), (0.6, 3.6), (-1.2, 4.2), (-4.2, 4.0), (-6.6, 3.2)],
]
for i, pts in enumerate(SUTURES):
    put(f"suture_{'abc'[i]}", "back", HINGE, 0.0, poly(rel(pts, HINGE)), FAR)

# ---- the front plate: narrow, lit, leading; its inner edge bows forward,
# which is the other half of the lens
FRONT = [(1.9, -6.6), (3.8, -6.8), (5.4, -4.6), (5.8, -1.0), (5.2, 2.6), (3.6, 5.6), (2.0, 6.2), (1.7, 5.0), (2.8, 2.0),
         (3.2, -1.0), (2.8, -4.2)]
put("shell_front", "front", HINGE, 0.0, poly(rel(FRONT, HINGE)), LIT, INK_THIN)
FRONT_RIM = [(2.9, -4.2), (3.3, -1.0), (2.9, 2.0), (2.0, 4.8), (2.6, 4.9), (3.7, 2.0), (4.1, -1.0), (3.6, -4.4)]
put("front_rim", "front", HINGE, 0.0, poly(rel(FRONT_RIM, HINGE)), BODY)

# ---- the hood: the head capsule, empty, jutting out over the split; the
# socket of the eye the drone looked out of, and a pinprick of the signal
# showing through it
HOOD_PTS = [(-2.8, -8.2), (-2.6, -10.6), (-0.6, -12.4), (2.6, -13.0), (5.6, -12.2), (8.0, -10.2), (9.0, -8.0), (8.4, -6.6),
            (6.8, -7.0), (5.4, -6.2), (3.4, -6.8), (0.4, -7.4)]
HOOD_AT = BONES["hood"].at
put("hood", "hood", HOOD_AT, 0.0, poly(rel(HOOD_PTS, HOOD_AT)), HOOD, INK_THIN)
HOOD_SHADE = [(-2.8, -8.2), (0.4, -7.4), (3.4, -6.8), (5.4, -6.2), (6.8, -7.0), (8.4, -6.6), (8.8, -7.4), (6.8, -8.0),
              (5.2, -7.4), (3.0, -8.0), (0.0, -8.6), (-2.6, -9.2)]
put("hood_shade", "hood", HOOD_AT, 0.0, poly(rel(HOOD_SHADE, HOOD_AT)), BODY)
put("socket", "hood", (5.4, -9.8), -12.0, ell(1.6, 1.15), "$ink")
put("eye", "hood", (5.7, -9.8), 0.0, circ(0.5), "$pheromone@heavy")

# ---- near side: the foreleg over the plate, the walking leg over the case
foreleg("near", SHADE, BODY)
hind_leg("near", SHADE, SHADE)

RIG.check()

# ============================================================== motion
def plant_legs(pose, feet, toes=None):
    world = solve(pose)
    for leg, (hip, fx, l1, l2) in LEGS.items():
        hx, hy, _ = world[f"{leg}_thigh"]
        h1, h2 = ik((hx, hy), feet[leg], l1, l2, KNEE)
        pose[f"abs:{leg}_thigh"] = h1
        pose[f"abs:{leg}_shin"] = h2
        pose[f"abs:{leg}_foot"] = (toes or {}).get(leg, 0.0)
    return pose

def bump(t, a, b):
    """0 → 1 → 0 across [a, b], wrapping."""
    u = (t - a) % 1.0
    w = (b - a) % 1.0
    return math.sin(math.pi * u / w) ** 2 if u < w else 0.0

def clack(t, at, period=0.14, decay=0.3):
    """The halves after a footfall at `at`: clapped shut, then bouncing — a damped wave, zero before the fall."""
    u = (t - at) % 1.0
    if u > decay: return 0.0
    env = (1.0 - u / decay) ** 2
    return -env * math.cos(2 * math.pi * u / period)

# ---- rattle: 1.4s, two steps. Each leg swings through while the case rides
# up over the other, and each footfall drops the case onto it, claps the
# halves shut and lets them bounce open. The hood nods after the drop, the
# forelegs dangle a beat behind, and the light swells as the lens opens.
STRIDE = 3.2
SWING = {"near": (0.0, 0.34), "far": (0.5, 0.84)}
LANDS = (0.34, 0.84)

def foot_track(t, swing, lift):
    a, b = swing
    u = t % 1.0
    if a <= u < b:
        v = (u - a) / (b - a)
        return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), lift * math.sin(math.pi * v)
    span = 1.0 - (b - a)
    v = ((u - b) % 1.0) / span
    return lerp(STRIDE, -STRIDE, v), 0.0

def opening(t):
    """How far the halves hang apart, in degrees each: open while the case is up, clapped and bouncing at each footfall."""
    up = bump(t, 0.06, 0.34) + bump(t, 0.56, 0.84)
    return 3.0 + 5.0 * up + 5.0 * (clack(t, LANDS[0]) + clack(t, LANDS[1]))

def rattle_pose(t):
    nd, nl = foot_track(t, SWING["near"], 2.4)
    fd, fl = foot_track(t, SWING["far"], 2.4)
    rise = bump(t, 0.04, 0.34) + bump(t, 0.54, 0.84)
    drop = bump(t, 0.32, 0.5) + bump(t, 0.82, 1.0)
    # Up over the stepping leg, down hard on the landing; it rocks toward the
    # leg it is standing on, and pitches forward on each drop.
    dy = -1.8 * rise + 1.6 * drop
    dx = 0.8 * cyc(2 * t, 0.1)
    pitch = 4.0 * drop - 2.0 * rise + 2.0 * cyc(t, 0.2)
    pose = {"body": (dx, dy, pitch)}
    o = opening(t)
    pose["back"] = o
    pose["front"] = -o
    # The hood nods the way it is going, a beat after the drop.
    pose["hood"] = 7.0 * (bump(t, 0.38, 0.62) + bump(t, 0.88, 0.12)) - 3.0 * rise
    # The forelegs hang loose off the plate: swung by the case a beat late,
    # the hooks flicking on each landing.
    for side, lag in (("near", 0.0), ("far", 0.08)):
        pose[f"{side}_femur"] = 14.0 * cyc(2 * t, -0.18 - lag) + o
        pose[f"{side}_tibia"] = 18.0 * cyc(2 * t, -0.32 - lag) - 10.0 * (bump(t, 0.36, 0.54) + bump(t, 0.86, 0.04))
    feet = {"near": (LEGS["near"][1] + nd, GROUND - nl), "far": (LEGS["far"][1] + fd, GROUND - fl)}
    toes = {"near": 20.0 * math.sin(math.pi * min(1.0, (t % 1.0) / 0.34)) if (t % 1.0) < 0.34 else 0.0,
            "far": 20.0 * math.sin(math.pi * (t - 0.5) / 0.34) if 0.5 <= (t % 1.0) < 0.84 else 0.0}
    return plant_legs(pose, feet, toes=toes)

# ---- death: 0.42s. Nobody was inside, so nothing dies: the signal flares and
# goes out and the shell stops being held. It claps shut and draws up once
# (the flare), then the halves swing apart off the hinge, the hood tips
# forward off the top, the knees go and the open case drops onto the floor,
# the halves bouncing once. Still from 0.85.
DEATH_TS = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
def death_pose(t):
    flare = math.sin(math.pi * smooth(0.0, 0.26, t))
    go = smooth(0.14, 0.62, t)
    bounce = math.sin(math.pi * smooth(0.6, 0.85, t))
    pose = {"body": (lerp(0.0, -0.6, go), -1.2 * flare + 5.2 * go - 0.8 * bounce, -3.0 * flare + 8.0 * go)}
    pose["back"] = -2.0 * flare + 38.0 * go - 6.0 * bounce
    pose["front"] = 2.0 * flare - 44.0 * go + 8.0 * bounce
    pose["hood"] = -8.0 * flare + 34.0 * go - 5.0 * bounce
    for side in ("near", "far"):
        pose[f"{side}_femur"] = -16.0 * flare + 50.0 * go
        pose[f"{side}_tibia"] = 20.0 * flare - 30.0 * go
    feet = {"near": (LEGS["near"][1] + 2.4 * go, GROUND), "far": (LEGS["far"][1] - 2.0 * go, GROUND)}
    return plant_legs(pose, feet, toes={"near": 16.0 * go, "far": -10.0 * go})

tracks = RIG.tracks
ROUND = ("socket", "eye", "gap_glow", "organ", "organ_bright")

RATTLE_TS = keyset(42)
animations = {}
animations["rattle"] = {
    "description": "Two steps a loop on legs nobody is driving: each leg swings through while the case rides up over the other, and each footfall drops the case onto it — the loose halves clap shut on the hinge and bounce open twice, the light in the split swelling as they part; the hood nods the way it is going a beat after the drop, and the hooked forelegs dangle off the front plate a beat behind, flicking on each landing.",
    "duration": 1.4,
    "tracks": tracks(rattle_pose, RATTLE_TS, [
        ("gap_glow", "scale", lambda t: 0.85 + 0.05 * opening(t)),
        ("organ", "scale", lambda t: 0.95 + 0.012 * opening(t)),
    ], still=ROUND),
}
animations["death"] = {
    "description": "Nobody was inside, so nothing dies — the signal flares once (the halves clapped shut, the case drawn up, the split blazing) and goes out, and the shell stops being held: the halves swing wide apart off the hinge, the hood tips forward off the top, the knees give and the open case drops onto the floor, the halves bouncing once. Still from 0.85.",
    "duration": 0.42,
    "tracks": tracks(death_pose, DEATH_TS, [
        ("gap_glow", "scale", lambda t: 1.0 + 1.0 * math.sin(math.pi * smooth(0.0, 0.3, t)) - 0.6 * smooth(0.3, 0.6, t)),
        ("gap_glow", "opacity", lambda t: 1.0 - smooth(0.2, 0.55, t)),
        ("organ", "scale", lambda t: 1.0 + 0.5 * math.sin(math.pi * smooth(0.0, 0.28, t))),
        ("organ", "opacity", lambda t: 1.0 - smooth(0.2, 0.5, t)),
        ("organ_bright", "opacity", lambda t: 1.0 - smooth(0.12, 0.4, t)),
        ("eye", "opacity", lambda t: 1.0 - smooth(0.12, 0.45, t)),
    ], still=ROUND),
}

# ============================================================== states
def posed_set(pose, ids):
    """`at`/`rot` patches that put parts where `pose` has them — a state drawn as a pose."""
    now = RIG.posed_parts(pose)
    out = {}
    for pid in ids:
        x, y, a = now[pid]
        out[f"{pid}.at"] = [r2(x), r2(y)]
        out[f"{pid}.rot"] = r2(wrap(a))
    return out

HALF_PARTS = ["shell_back", "back_shade", "suture_a", "suture_b", "suture_c", "shell_front", "front_rim",
              "near_femur", "near_tibia", "far_femur", "far_tibia"]
ELITE_SET = posed_set({"back": 8.0, "front": -8.0}, HALF_PARTS)
ELITE_SET.update({
    "gap_glow.scale": [1.6, 1.15],
    "gap_glow.fill": "$pheromone@heavy",
    "organ.opacity": 0,
    "organ_bright.opacity": 1,
    "eye.fill": "$pheromone.light",
})

VARIANTS = {
    "elite": {
        "description": "The shell answered louder than it should have — the halves forced wide apart on the hinge, the split blazing, and the signal inside no longer faint.",
        "scale": 1.3,
        "set": ELITE_SET,
    },
}

DESCRIPTION = (
    "Nobody is inside. The shed case of a drone — the exuvia a cicada leaves on a stalk — split down the front and held upright only by "
    "the signal rattling around in it. Seen side-on facing +x and mirrored by the game: a hooded head capsule jutting forward with the empty "
    "socket of an eye, a big segmented back half trailing, a narrow lit front plate leading, raptorial forelegs folded under the hood with "
    "hooked tips, and two jointed hind legs with hooked feet. The two halves hang off one hinge under the hood and part along the front in "
    "a lens, and the lens is where the light is: the dark inside, a glow, and a faint organ framed by the halves. Cold pale grey where the "
    "Husk is warm bone. Built on a skeleton (scripts/skeleton.py): a pelvis, the case on it, the halves off the hinge, the hood, the "
    "forelegs on the front plate and the hind legs solved every frame to a foot on the floor. The `rattle` is its walk: two steps a loop, "
    "the case riding up over each leg and dropping onto it, and every footfall claps the loose halves shut so they bounce open again. "
    "Gameplay radius 10. `elite` is the shell answering louder: the halves forced wide, the split blazing, the organ fully lit. The "
    "`death` clip is the only honest one in the roster: nothing dies, the signal just stops, and the shell it was rattling around in "
    "swings open along the seam and drops."
)

SHIFT_X = 0.0
doc = {
    "id": "ss.enemy.skeleton",
    "name": "Molt",
    "description": DESCRIPTION,
    "tags": ["enemy", "shell"],
    "size": SIZE,
    "meta": {"radius": 10},
    "parts": RIG.parts,
    "variants": VARIANTS,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-skeleton.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
