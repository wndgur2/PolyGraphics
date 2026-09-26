"""The Mite — the hive's first responder, and the body on screen by the hundred.

    python3 scripts/imp.py        # rewrites apps/ss/assets/ss-enemy-imp.json

feelers calls it the Mite (`imp`, Vermis ferrugo): fast, weak, a melee chaser
that arrives by the hundred, and — on the Salt Pan — the thing a Hurler throws
(`shotSpawn: 'imp'`, drawn in flight as `e_imp`). The Hurler and the app icon
both compose this document (`use: ss.enemy.imp`), so its rest pose is drawn
about the same box as the old one (the dome a little behind the
anchor, two feelers up).

It was an orange ball with a beak, three stubs under it and two sticks on
top, and its scuttle measured 3.2px at game scale (scripts/motion.ts): the
stubs swung a few degrees, the ball bobbed half a pixel. This rebuilds it on
the rig (scripts/rig.py) as what the name says, a mite:

  - one domed body (the idiosoma) lit on top under a paler dorsal shield,
    shaded underneath, a groove round the rear; a darker capitulum in front
    carrying an eye, a dark maw and a pair of pale hooked fangs, each hinged
    so the maw works; the organ on the dome
  - six short thick legs, three a side, each a femur and a tibia solved by
    two-bone IK to a planted foot, so the body rides over its feet; the front
    pair of a mite are its feelers, carried up off the head — two-link whips
    that sweep and lag down their length
  - `scuttle` is an alternating tripod, each foot one step a loop: the body
    bobs on every step and pitches after it, the head nods a beat late, both
    feelers sweep forward and back together (the far one a beat behind) so
    the silhouette's two antennae really travel, and the fangs work twice

Chitin amber, the colour it always was, in three values: the lit shield
(chitin.light), the body and near feeler (chitin), the shade, the head and
the near legs (chitin.dark), the far legs and feeler a step darker. Kept small
in parts (every Mite is a sprite in a crowd) and fat in shape, so the
silhouette — a dome on stubs with two feelers up — survives at 1.2× and when
a Hurler throws it.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 36×36 (the old 32 with room for the feelers' sweep and the roll), origin at the centre, +x forward, +y down; the feet stand on
# GROUND, the far feet a touch higher (further away).
W, H = 36, 36
GROUND = 10.4
FAR_LIFT = 1.0

RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("body", None, (-1.0, 0.6), 0.0)
bone("head", "body", (5.0, 0.8), 0.0, 4.0)
# The fangs (chelicerae): hinged at the front of the capitulum, over and under
# the maw, hooking toward each other.
bone("fang", "head", (9.6, 0.4), -4.0, 3.2)
bone("fang_low", "head", (9.4, 2.8), 8.0, 3.0)
# The feelers — a mite's first pair of legs, carried up off the head as
# antennae: two links each, the near one forward, the far one more upright.
RIG.chain("feeler", "head", (7.4, -2.6), [(4.6, -70.0), (4.8, -40.0)])
RIG.chain("feeler_far", "head", (5.4, -3.2), [(4.4, -122.0), (4.8, -104.0)])

# Legs: (hip, rest foot x, femur, tibia). Short and thick — a compact body
# stands on stubs, not stilts: femur and tibia together are under the body's
# own half-height, and the knee rides just outside the belly.
LEGS = {
    "near_f": ((3.2, 3.2), 7.0, 3.2, 4.2),
    "near_m": ((-0.6, 3.8), -1.4, 3.0, 4.0),
    "near_b": ((-4.6, 3.4), -8.8, 3.2, 4.2),
    "far_f": ((4.4, 2.2), 8.4, 3.0, 4.0),
    "far_m": ((0.8, 2.8), 0.4, 2.8, 3.8),
    "far_b": ((-3.4, 2.4), -7.2, 3.0, 4.0),
}
def ground_of(leg): return GROUND - (FAR_LIFT if leg.startswith("far") else 0.0)
def knee_bend(leg):
    """The knee folds out the way the leg splays: forward and up in front, back and up behind."""
    return 1 if LEGS[leg][1] >= LEGS[leg][0][0] else -1
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, knee_bend(leg))
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", B[f"{leg}_femur"].end(), ht, lt)

RIG.seal()
put, on_bone = RIG.put, RIG.on_bone

def wpoly(at, pts):
    """A polygon given in world coordinates, as a shape about `at`."""
    return poly([(x - at[0], y - at[1]) for x, y in pts])

def egg(cx, cy, front, back, top, bot, n=22, a0=0.0, a1=360.0, e=2.4):
    """Points round an egg: a different radius each way, so the dome can be high and the belly flat."""
    pts = []
    for i in range(n + (0 if a1 - a0 >= 360 else 1)):
        a = R(a0 + (a1 - a0) * i / n)
        c, s = math.cos(a), math.sin(a)
        rx = front if c >= 0 else back
        ry = bot if s >= 0 else top
        # a squarer superellipse than an ellipse: a mite is a sack, not a bead
        x = rx * math.copysign(abs(c) ** (2 / e), c)
        y = ry * math.copysign(abs(s) ** (2 / e), s)
        pts.append((cx + x, cy + y))
    return pts

# ============================================================== parts
BODY_C = (-1.6, -0.6)
FRONT, BACK, TOP, BOT = 7.6, 8.8, 7.4, 6.0

def leg_parts(leg, femur, tibia, stroke):
    at, a = on_bone(f"{leg}_tibia")
    put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(B[f"{leg}_tibia"].length, 2.0, 0.9, 0.5), tibia, stroke)
    at, a = on_bone(f"{leg}_femur")
    put(f"{leg}_femur", f"{leg}_femur", at, a, bar(B[f"{leg}_femur"].length, 2.6, 2.1, 0.8), femur, stroke)

def feeler_parts(prefix, fill, stroke, w=1.0):
    for i, (w0, w1) in enumerate(((1.8 * w, 1.4 * w), (1.4 * w, 0.8 * w))):
        n = f"{prefix}_{i}"
        at, a = on_bone(n)
        put(n, n, at, a, bar(B[n].length, w0, w1, 0.6), fill, stroke)

# ---- far side, behind the body: legs and feeler, a step darker
for leg in ("far_b", "far_m", "far_f"):
    leg_parts(leg, "$chitin.dark", "$chitin.dark", None)
feeler_parts("feeler_far", "$chitin.dark", None, 0.95)

# ---- the body: a domed sack, lit shield on top, shade under, a groove behind
put("body", "body", BODY_C, 0.0, wpoly(BODY_C, egg(*BODY_C, FRONT, BACK, TOP, BOT)), "$chitin", INK_THIN)
belly = egg(BODY_C[0], BODY_C[1], FRONT - 0.2, BACK - 0.2, TOP, BOT - 0.2, n=14, a0=10.0, a1=170.0)
belly += [(BODY_C[0] - 6.8, BODY_C[1] + 3.2), (BODY_C[0] - 2.0, BODY_C[1] + 4.0), (BODY_C[0] + 3.6, BODY_C[1] + 3.4)]
put("belly", "body", BODY_C, 0.0, wpoly(BODY_C, belly), "$chitin.dark")
# The dorsal shield: the upper front of the dome, its hind edge a curve.
shield = egg(BODY_C[0] + 0.3, BODY_C[1] - 0.1, FRONT - 1.2, BACK - 2.0, TOP - 1.0, BOT, n=16, a0=190.0, a1=344.0)
shield += [(BODY_C[0] + 5.4, BODY_C[1] + 0.2), (BODY_C[0] + 1.0, BODY_C[1] + 0.8), (BODY_C[0] - 4.2, BODY_C[1] - 0.2)]
put("shield", "body", BODY_C, 0.0, wpoly(BODY_C, shield), "$chitin.light")
# A groove round the rear, following the dome: the sack is segmented behind.
a0, a1, inset = 124.0, 212.0, 2.6
outer = egg(BODY_C[0], BODY_C[1], FRONT, BACK - inset, TOP - inset * 0.7, BOT - inset * 0.7, n=10, a0=a0, a1=a1)
inner = egg(BODY_C[0], BODY_C[1], FRONT, BACK - inset - 1.0, TOP - inset * 0.7 - 0.8, BOT - inset * 0.7 - 0.8, n=10, a0=a0, a1=a1)
put("groove", "body", BODY_C, 0.0, wpoly(BODY_C, outer + inner[::-1]), "$chitin.dark")
put("gloss", "body", (-0.6, -6.0), -4.0, ell(4.2, 1.2), "$white@0.35")
RIG.use("organ", "body", (-3.8, -3.4), "ss.lib.organ", scale=[0.62, 0.54])

# ---- the capitulum: a darker hood in front, the eye on it, the maw and fangs
HEAD_C = (8.2, 0.7)
put("maw", "head", HEAD_C, 0.0, wpoly(HEAD_C, [(8.6, 0.2), (10.8, 0.2), (11.6, 1.6), (10.8, 3.2), (8.6, 3.0)]), "$ink")
HOOD = [(4.4, -2.6), (6.4, -3.8), (8.8, -3.4), (10.6, -1.8), (10.8, 0.2), (9.2, 1.0), (9.0, 2.6), (10.0, 3.6),
        (8.4, 4.6), (5.8, 4.4), (4.2, 2.8)]
put("head", "head", HEAD_C, 0.0, wpoly(HEAD_C, HOOD), "$chitin", INK_HAIR)
put("eye", "head", (8.2, -1.2), 0.0, circ(1.35), "$ink")
put("eye_glint", "head", (7.8, -1.7), 0.0, circ(0.5), "$white")
FANG = [(-0.6, -0.8), (1.2, -0.9), (2.6, -0.4), (3.4, 0.8), (3.0, 1.3), (2.2, 0.4), (1.0, 0.6), (-0.6, 0.7)]
at, a = on_bone("fang")
put("fang", "fang", at, a, poly(FANG), "$husk", INK_HAIR)
at, a = on_bone("fang_low")
put("fang_low", "fang_low", at, a, poly([(x, -y) for x, y in FANG]), "$husk.dark", INK_HAIR)

# ---- near side, over everything: the feeler, then the legs
feeler_parts("feeler", "$chitin.light", INK_HAIR)
for leg in ("near_b", "near_m", "near_f"):
    leg_parts(leg, "$chitin.light", "$chitin", INK_HAIR)

RIG.check()

# ============================================================== motion
TRIPOD = {"near_f": 0.0, "far_m": 0.0, "near_b": 0.0, "far_f": 0.5, "near_m": 0.5, "far_b": 0.5}

def plant_legs(pose, feet):
    """Solve every leg to put its foot at `feet[leg]`, against the body as posed."""
    world = RIG.solve(pose)
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, knee_bend(leg))
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
    return pose

STRIDE = 2.6   # half a step, px either side of the rest foot
LIFT = 3.0
DUTY = 0.5     # a scuttle: as long in the air as on the ground
def step(t, ph):
    """Foot offset along x and its lift: stance pushes back, swing arcs forward."""
    u = (t + ph) % 1.0
    if u < DUTY:
        return lerp(STRIDE, -STRIDE, u / DUTY), 0.0
    v = (u - DUTY) / (1 - DUTY)
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), LIFT * math.sin(math.pi * v)

FA = (24.0, 30.0, 22.0, 28.0)   # feeler sweep: near root, near tip, far root, far tip
ROCK = (1.0, 5.0)               # the once-a-loop rock: surge px, pitch degrees
BOB = 1.6
FP = 0.5                        # the feelers and the rock peak as the tripods swap
def scuttle_pose(t):
    # A bob on every step (two a loop), the pitch after it, and a surge that
    # rolls the body forward over the tripod on the ground.
    bob = BOB * (0.5 - 0.5 * math.cos(4 * math.pi * (t - 0.06)))
    # and once a loop the whole body rocks back and forward on its legs, nose
    # rising as it gathers and dipping as it throws itself on, which carries
    # the feelers through their sweep.
    rock = cyc(t, FP - 0.05)
    pose = {"body": (0.7 * cyc(2 * t, 0.15) + ROCK[0] * rock, bob - 0.9, 3.0 * cyc(2 * t, -0.05) + ROCK[1] * rock)}
    pose["head"] = -6.0 * cyc(2 * t, -0.18)
    # The feelers sweep together, forward-and-down then back-and-up once a
    # loop, the far one a beat behind, the tip a beat behind the root.
    pose["feeler_0"] = FA[0] * cyc(t, FP)
    pose["feeler_1"] = FA[1] * cyc(t, FP - 0.12)
    pose["feeler_far_0"] = FA[2] * cyc(t, FP - 0.06)
    pose["feeler_far_1"] = FA[3] * cyc(t, FP - 0.18)
    bite = 0.5 + 0.5 * cyc(2 * t, 0.1)
    pose["fang"] = -22.0 * bite
    pose["fang_low"] = 20.0 * bite
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        dx, lift = step(t, TRIPOD[leg])
        feet[leg] = (fx + dx, ground_of(leg) - lift)
    return plant_legs(pose, feet)

# ---- death: one kick — it jolts up nose-first with the legs thrown out and
# the fangs gaping — then it goes over backwards onto its back, lands on the
# dome with a small bounce, and the legs curl up in the air; the feelers go
# limp and the organ flares and goes out. Still from 0.85.
FLIP = -180.0
def death_pose(t):
    jolt = math.sin(math.pi * smooth(0.0, 0.26, t))
    roll = smooth(0.12, 0.66, t)
    land = math.sin(math.pi * smooth(0.62, 0.84, t))
    # Rolling over, the dome's top ends up on the ground: the body centre drops
    # so the (upside-down) dome rests on GROUND.
    pose = {"body": (-0.6 * roll, -1.6 * jolt - 1.0 * math.sin(math.pi * roll) + 2.0 * roll - 0.6 * land,
                     -14.0 * jolt + FLIP * roll)}
    pose["head"] = 6.0 * jolt + 14.0 * roll
    gape = smooth(0.0, 0.2, t)
    pose["fang"] = -34.0 * gape + 12.0 * roll
    pose["fang_low"] = 30.0 * gape - 10.0 * roll
    # The feelers: thrown up on the kick, then they fold forward under the
    # chin and curl up over the belly like the legs, the way a dead mite's do.
    fold = smooth(0.06, 0.42, t)
    pose["feeler_0"] = 10.0 * jolt + 100.0 * fold
    pose["feeler_1"] = 14.0 * jolt + 40.0 * fold
    pose["feeler_far_0"] = 8.0 * jolt + 112.0 * fold
    pose["feeler_far_1"] = 12.0 * jolt + 36.0 * fold
    # The legs: kicked straight out on the jolt, then curled in toward the
    # belly — femur up against the body, tibia folded back on it. FK here,
    # joint angles in the body's frame, so the fold survives the roll.
    for leg, (hip, fx, lf, lt) in LEGS.items():
        side = 1.0 if fx > hip[0] else -1.0
        kick = -18.0 * side * jolt
        pose[f"{leg}_femur"] = kick + 38.0 * side * roll
        pose[f"{leg}_tibia"] = -8.0 * side * jolt + 62.0 * side * roll + 10.0 * side * land
    return pose

animations = {}
TS_SCUTTLE = keyset(24)
animations["scuttle"] = {
    "description": "An alternating tripod, each foot one step a loop: each foot planted while the body rides over it and lifted on the way forward; the body bobs on every step and pitches after it, the head nodding a beat late; both feelers sweep forward and back together, the far one a beat behind and each tip lagging its root; the fangs work twice a loop.",
    "duration": 0.5,
    "tracks": RIG.tracks(scuttle_pose, TS_SCUTTLE, [("organ", "scale", lambda t: 1.0 + 0.1 * cyc(2 * t, -0.1))],
                         still=("eye", "eye_glint")),
}
TS_DEATH = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "One kick: it jolts up nose-first with the legs thrown out and the fangs gaping, then goes over backwards onto its back and lands on the dome with a small bounce — the legs curl up in the air, the feelers fold under the chin and curl up over the belly, the maw stays open — and the organ flares and goes out. Still from 0.85.",
    "duration": 0.34,
    "tracks": RIG.tracks(death_pose, TS_DEATH, [
        ("organ", "scale", lambda t: 1.0 + 0.6 * math.sin(math.pi * smooth(0.0, 0.36, t)) - 0.3 * smooth(0.36, 0.85, t)),
        ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.25, 0.8, t)),
        ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.2, 0.6, t)),
    ], still=("eye", "eye_glint")),
}

# ============================================================== states
# The marking the old document carried — bleached shell, heavier maw, brighter
# organ — rewritten against the new parts: the whole shell bleaches, the legs
# go to the husk's dark so they still sit under the body, the fangs grow.
variants = {
    "elite": {
        "description": "Marked by the hive: bleached shell, a heavier maw and a brighter organ.",
        "scale": 1.25,
        "set": {
            "body.fill": "$husk.dark",
            "shield.fill": "$husk",
            "belly.fill": "$husk.dark2",
            "groove.fill": "$husk.dark2",
            "head.fill": "$husk.dark",
            "feeler_0.fill": "$husk",
            "feeler_1.fill": "$husk",
            "feeler_far_0.fill": "$husk.dark",
            "feeler_far_1.fill": "$husk.dark",
            **{f"near_{l}_femur.fill": "$husk.dark" for l in "fmb"},
            **{f"near_{l}_tibia.fill": "$husk.dark2" for l in "fmb"},
            **{f"far_{l}_{s}.fill": "$husk.dark2" for l in "fmb" for s in ("femur", "tibia")},
            "fang.fill": "$bone.light",
            "fang_low.fill": "$bone",
            "fang.scale": [1.3, 1.3],
            "fang_low.scale": [1.3, 1.3],
            "maw.scale": [1.15, 1.15],
            "organ.scale": [0.78, 0.68],
        },
    },
}

DESCRIPTION = (
    "The hive's first responder — the one that found you, and the body on screen by the hundred; feelers calls it the Mite, and on the "
    "Salt Pan it is also what a Hurler throws (`shotSpawn: 'imp'`). A mite seen side-on, facing +x and mirrored by the game: one domed "
    "chitin-amber sack lit under a paler dorsal shield and shaded underneath, a lit organ on the dome, a darker capitulum in front with an "
    "eye, a dark maw and two pale hooked fangs, six short thick legs and — a mite's front pair — two feelers carried up off the head. The "
    "silhouette is a dome on stubs with two feelers up, kept fat and few-parted so it survives at 1.2× in a crowd. Built on a skeleton "
    "(scripts/imp.py): the legs are solved every frame to planted feet, the feelers are two-link whips, the fangs are hinged either side of "
    "the maw. `scuttle` is an alternating tripod with the body bobbing and pitching over it and both feelers sweeping forward and back. "
    "Gameplay slot unchanged (fast, weak melee chaser); body radius still 8.5. `elite` is the bleached, heavy-jawed marking. The `death` "
    "clip is one kick, then it goes over onto its back with its legs curled in the air and the organ going out."
)

doc = {
    "id": "ss.enemy.imp",
    "name": "Tracker",
    "description": DESCRIPTION,
    "tags": ["enemy", "tracker"],
    "size": [W, H],
    "meta": {"radius": 8.5},
    "parts": RIG.parts,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-imp.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
