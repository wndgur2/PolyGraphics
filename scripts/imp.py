"""The Mite — the hive's first responder, and the body on screen by the hundred.

    python3 scripts/imp.py        # rewrites apps/ss/assets/ss-enemy-imp.json

feelers calls it the Mite (`imp`, Vermis ferrugo): fast, weak, a melee chaser
that arrives by the hundred, and — on the Salt Pan — the thing a Hurler throws
(`shotSpawn: 'imp'`, drawn in flight as `e_imp`, turned along its arc). The
Hurler and the app icon both compose this document (`use: ss.enemy.imp`), so
its rest pose is drawn about the same box as the old one.

It was an orange ball with a beak, three stubs under it and two sticks on
top, and its scuttle measured 3.2px at game scale (scripts/motion.ts): the
stubs swung a few degrees, the ball bobbed half a pixel. This rebuilds it on
the rig (scripts/rig.py) as what the name says, a mite:

  - one domed body (the idiosoma) lit on top under a paler dorsal shield,
    shaded underneath, two grooves across the rear; a darker capitulum in
    front carrying an eye, a dark maw and a pair of pale hooked fangs, each
    hinged so the maw works; the organ on the dome
  - six short thick legs, three a side, each a femur and a tibia solved by
    two-bone IK to a planted foot, so the body rides over its feet; the front
    pair of a mite are its feelers, carried up off the head — two-link whips
    that sweep and lag down their length
  - `scuttle` is two tripods, one step each a loop: the body bobs on every
    step and pitches after it, the head nods a beat late, the feelers sweep in
    turn — near up while far down — and the fangs work twice a loop

Chitin amber, the colour it always was, in three values: the lit shield
(chitin.light), the body (chitin), the shade and near legs (chitin.dark) with
the far legs and grooves a step darker. Kept small in parts (every Mite is a
sprite in a crowd) and fat in shape, so the silhouette — a dome on stubs with
two feelers up — survives at 1.2× and when a Hurler turns it along its throw.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 36×36, origin at the centre, +x forward, +y down; the feet stand on
# GROUND, the far feet a touch higher (further away).
W, H = 36, 36
GROUND = 11.0
FAR_LIFT = 1.2

RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("body", None, (-1.0, 0.6), 0.0)
bone("head", "body", (5.0, 0.8), 0.0, 4.0)
# The fangs (chelicerae): hinged at the front of the capitulum, over and under
# the maw, hooking toward each other.
bone("fang", "head", (9.8, 0.6), -4.0, 3.2)
bone("fang_low", "head", (9.6, 3.0), 8.0, 3.0)
# The feelers — a mite's first pair of legs, carried up off the head as
# antennae: two links each, the near one forward, the far one more upright.
RIG.chain("feeler", "head", (7.8, -2.6), [(4.6, -78.0), (4.8, -40.0)])
RIG.chain("feeler_far", "head", (6.4, -3.0), [(4.2, -98.0), (4.6, -62.0)])

# Legs: (hip, rest foot x, femur, tibia). Short and thick — a compact body
# stands on stubs, not stilts.
LEGS = {
    "near_f": ((3.4, 3.6), 8.0, 4.2, 5.0),
    "near_m": ((-0.2, 4.4), -1.0, 4.0, 4.8),
    "near_b": ((-4.4, 4.0), -9.0, 4.2, 5.0),
    "far_f": ((4.6, 2.6), 9.6, 4.0, 4.8),
    "far_m": ((1.0, 3.4), 0.6, 3.8, 4.6),
    "far_b": ((-3.2, 3.0), -7.4, 4.0, 4.8),
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

def egg(cx, cy, front, back, top, bot, n=22, a0=0.0, a1=360.0):
    """Points round an egg: a different radius each way, so the dome can be high and the belly flat."""
    pts = []
    for i in range(n + (0 if a1 - a0 >= 360 else 1)):
        a = R(a0 + (a1 - a0) * i / n)
        c, s = math.cos(a), math.sin(a)
        rx = front if c >= 0 else back
        ry = bot if s >= 0 else top
        # a squarer superellipse than an ellipse: a mite is a sack, not a bead
        e = 2.4
        x = rx * math.copysign(abs(c) ** (2 / e), c)
        y = ry * math.copysign(abs(s) ** (2 / e), s)
        pts.append((cx + x, cy + y))
    return pts

# ============================================================== parts
BODY_C = (-1.6, -0.4)
FRONT, BACK, TOP, BOT = 8.0, 9.4, 7.6, 6.8

def leg_parts(leg, femur, tibia, stroke, foot=None):
    at, a = on_bone(f"{leg}_tibia")
    put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(B[f"{leg}_tibia"].length, 1.9, 0.8, 0.5), tibia, stroke)
    at, a = on_bone(f"{leg}_femur")
    put(f"{leg}_femur", f"{leg}_femur", at, a, bar(B[f"{leg}_femur"].length, 2.5, 1.9, 0.7), femur, stroke)

def feeler_parts(prefix, fill, stroke, w=1.0):
    for i, (w0, w1) in enumerate(((1.9 * w, 1.5 * w), (1.5 * w, 0.9 * w))):
        n = f"{prefix}_{i}"
        at, a = on_bone(n)
        put(n, n, at, a, bar(B[n].length, w0, w1, 0.6), fill, stroke)

# ---- far side, behind the body: legs and feeler, a step darker
for leg in ("far_b", "far_m", "far_f"):
    leg_parts(leg, "$chitin.dark", "$chitin.dark", None)
feeler_parts("feeler_far", "$chitin.dark", None, 0.9)

# ---- the body: a domed sack, lit shield on top, shade under, grooves behind
put("body", "body", BODY_C, 0.0, wpoly(BODY_C, egg(*BODY_C, FRONT, BACK, TOP, BOT)), "$chitin", INK_THIN)
belly = [p for p in egg(BODY_C[0], BODY_C[1], FRONT - 0.2, BACK - 0.2, TOP, BOT - 0.2, n=14, a0=14.0, a1=166.0)]
belly += [(BODY_C[0] - 6.6, BODY_C[1] + 4.4), (BODY_C[0] - 2.0, BODY_C[1] + 5.2), (BODY_C[0] + 3.6, BODY_C[1] + 4.6)]
put("belly", "body", BODY_C, 0.0, wpoly(BODY_C, belly), "$chitin.dark")
# The dorsal shield: the upper front of the dome, its hind edge a curve.
shield = egg(BODY_C[0] + 0.2, BODY_C[1] - 0.1, FRONT - 1.0, BACK - 1.6, TOP - 0.9, BOT, n=16, a0=188.0, a1=344.0)
shield += [(BODY_C[0] + 5.8, BODY_C[1] + 0.6), (BODY_C[0] + 1.0, BODY_C[1] + 1.4), (BODY_C[0] - 4.6, BODY_C[1] + 0.4)]
put("shield", "body", BODY_C, 0.0, wpoly(BODY_C, shield), "$chitin.light")
# Two grooves round the rear, following the dome: the sack is segmented behind.
for i, inset in enumerate((2.2, 4.6)):
    a0, a1 = (122.0, 214.0) if i == 0 else (134.0, 204.0)
    outer = egg(BODY_C[0], BODY_C[1], FRONT, BACK - inset, TOP - inset * 0.7, BOT - inset * 0.7, n=10, a0=a0, a1=a1)
    inner = egg(BODY_C[0], BODY_C[1], FRONT, BACK - inset - 0.9, TOP - inset * 0.7 - 0.7, BOT - inset * 0.7 - 0.7, n=10, a0=a0, a1=a1)
    put(f"groove_{i}", "body", BODY_C, 0.0, wpoly(BODY_C, outer + inner[::-1]), "$chitin.dark")
put("gloss", "body", (-1.4, -5.6), -6.0, ell(4.6, 1.4), "$white@0.35")
RIG.use("organ", "body", (-3.6, -3.6), "ss.lib.organ", scale=[0.6, 0.52])

# ---- the capitulum: a darker hood in front, the eye on it, the maw and fangs
HEAD_C = (8.4, 0.9)
put("maw", "head", HEAD_C, 0.0, wpoly(HEAD_C, [(8.8, 0.4), (11.0, 0.4), (11.8, 1.8), (11.0, 3.4), (8.8, 3.2)]), "$ink")
HOOD = [(4.6, -2.4), (6.6, -3.6), (9.0, -3.2), (10.8, -1.6), (11.0, 0.4), (9.4, 1.2), (9.2, 2.8), (10.2, 3.8),
        (8.6, 4.8), (6.0, 4.6), (4.4, 3.0)]
put("head", "head", HEAD_C, 0.0, wpoly(HEAD_C, HOOD), "$chitin.dark", INK_HAIR)
put("head_lit", "head", (7.6, -1.8), -14.0, ell(2.4, 1.0), "$chitin")
put("eye", "head", (8.6, -0.8), 0.0, circ(1.3), "$ink")
put("eye_glint", "head", (8.2, -1.3), 0.0, circ(0.45), "$white")
FANG = [(-0.6, -0.8), (1.2, -0.9), (2.6, -0.4), (3.4, 0.8), (3.0, 1.3), (2.2, 0.4), (1.0, 0.6), (-0.6, 0.7)]
at, a = on_bone("fang")
put("fang", "fang", at, a, poly(FANG), "$husk", INK_HAIR)
at, a = on_bone("fang_low")
put("fang_low", "fang_low", at, a, poly([(x, -y) for x, y in FANG]), "$husk.dark", INK_HAIR)

# ---- near side, over everything: the feeler, then the legs
feeler_parts("feeler", "$chitin.light", INK_HAIR)
for leg in ("near_b", "near_m", "near_f"):
    leg_parts(leg, "$chitin.light", "$chitin.light", INK_HAIR)

RIG.check()

# ============================================================== motion
LEG_NAMES = list(LEGS)
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

STRIDE = 3.0   # half a step, px either side of the rest foot
LIFT = 3.2
DUTY = 0.5     # a scuttle: as long in the air as on the ground
def step(t, ph):
    """Foot offset along x and its lift: stance pushes back, swing arcs forward."""
    u = (t + ph) % 1.0
    if u < DUTY:
        return lerp(STRIDE, -STRIDE, u / DUTY), 0.0
    v = (u - DUTY) / (1 - DUTY)
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), LIFT * math.sin(math.pi * v)

def scuttle_pose(t):
    # A bob on every step (two a loop), the pitch after it, and a surge that
    # rolls the body forward over the tripod on the ground.
    bob = 1.8 * (0.5 - 0.5 * math.cos(4 * math.pi * (t - 0.06)))
    pose = {"body": (0.8 * cyc(2 * t, 0.15), bob - 0.7, 4.5 * cyc(2 * t, -0.05))}
    pose["head"] = -5.0 * cyc(2 * t, -0.18)
    # The feelers sweep in turn, the tip a beat behind the root.
    pose["feeler_0"] = 24.0 * cyc(t, 0.0)
    pose["feeler_1"] = 36.0 * cyc(t, -0.16)
    pose["feeler_far_0"] = 22.0 * cyc(t, 0.5)
    pose["feeler_far_1"] = 34.0 * cyc(t, 0.34)
    bite = 0.5 + 0.5 * cyc(2 * t, 0.1)
    pose["fang"] = -22.0 * bite
    pose["fang_low"] = 20.0 * bite
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        dx, lift = step(t, TRIPOD[leg])
        feet[leg] = (fx + dx, ground_of(leg) - lift)
    return plant_legs(pose, feet)

# ---- death: one kick — it jolts up nose-first with the legs thrown out and
# the fangs gaping — then it goes over onto its back end, the legs curl up
# into the air, the feelers fall back across the dome and the organ flares
# and goes out. Still from 0.85.
def death_pose(t):
    jolt = math.sin(math.pi * smooth(0.0, 0.26, t))
    fall = smooth(0.18, 0.72, t)
    land = math.sin(math.pi * smooth(0.6, 0.85, t))
    pose = {"body": (-1.2 * fall, -2.6 * jolt + 1.6 * fall - 0.5 * land, -12.0 * jolt - 34.0 * fall)}
    pose["head"] = 6.0 * jolt + 16.0 * fall
    gape = smooth(0.0, 0.2, t)
    pose["fang"] = -34.0 * gape + 10.0 * fall
    pose["fang_low"] = 30.0 * gape - 8.0 * fall
    pose["feeler_0"] = 14.0 * jolt - 64.0 * fall
    pose["feeler_1"] = 20.0 * jolt - 40.0 * fall
    pose["feeler_far_0"] = 12.0 * jolt - 50.0 * fall
    pose["feeler_far_1"] = 18.0 * jolt - 40.0 * fall
    # The feet: kicked out and down on the jolt, then drawn up in toward the
    # belly, which is now tipped toward the sky.
    world = RIG.solve(pose)
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        kick = (fx + 1.6 * (1 if fx > hip[0] else -1) * jolt, ground_of(leg) + 0.6 * jolt)
        hx, hy, ha = world[f"{leg}_femur"]
        # curled: a point out from the hip along the body's "down", pulled in
        c, s = math.cos(R(ha)), math.sin(R(ha))
        body_th = pose["body"][2]
        dn = (-math.sin(R(body_th)), math.cos(R(body_th)))  # the body's down
        fw = (math.cos(R(body_th)), math.sin(R(body_th)))
        side = 1.0 if fx > hip[0] else -1.0
        curl = (hx + 3.4 * dn[0] + 2.4 * side * fw[0], hy + 3.4 * dn[1] + 2.4 * side * fw[1] - 1.0)
        feet[leg] = (lerp(kick[0], curl[0], fall), lerp(kick[1], curl[1], fall))
    return plant_legs(pose, feet)

animations = {}
TS_SCUTTLE = keyset(24)
animations["scuttle"] = {
    "description": "Two tripods, one step each a loop: each foot planted while the body rides over it and lifted on the way forward; the body bobs on every step and pitches after it, the head nodding a beat late; the feelers sweep in turn, near up while far down, the tip lagging the root; the fangs work twice a loop.",
    "duration": 0.5,
    "tracks": RIG.tracks(scuttle_pose, TS_SCUTTLE, [("organ", "scale", lambda t: 1.0 + 0.1 * cyc(2 * t, -0.1))],
                         still=("eye", "eye_glint")),
}
TS_DEATH = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "One kick: it jolts up nose-first with the legs thrown out and the fangs gaping, then goes over onto its back end — the legs curl up into the air, the feelers fall back across the dome, the maw hangs open — and the organ on its back flares and goes out. Still from 0.85.",
    "duration": 0.34,
    "tracks": RIG.tracks(death_pose, TS_DEATH, [
        ("organ", "scale", lambda t: 1.0 + 0.7 * math.sin(math.pi * smooth(0.0, 0.4, t)) - 0.35 * smooth(0.4, 0.85, t)),
        ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.25, 0.8, t)),
        ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.2, 0.6, t)),
    ], still=("eye", "eye_glint")),
}

# ============================================================== states
variants = {
    "elite": {
        "description": "Marked by the hive: bleached shell, a heavier maw and a brighter organ.",
        "scale": 1.25,
        "set": {
            "body.fill": "$husk.dark",
            "shield.fill": "$husk",
            "belly.fill": "$husk.dark2",
            "groove_0.fill": "$husk.dark2",
            "groove_1.fill": "$husk.dark2",
            "head.fill": "$husk.dark2",
            "head_lit.fill": "$husk.dark@heavy",
            "fang.fill": "$bone.light",
            "fang_low.fill": "$bone",
            "fang.scale": [1.3, 1.3],
            "fang_low.scale": [1.3, 1.3],
            "maw.scale": [1.15, 1.15],
            "organ.scale": [0.78, 0.66],
        },
    },
}

DESCRIPTION = (
    "The hive's first responder — the one that found you, and the body on screen by the hundred; feelers calls it the Mite, and on the "
    "Salt Pan it is also what a Hurler throws (`shotSpawn: 'imp'`, drawn turned along its arc). A mite seen side-on, facing +x and mirrored "
    "by the game: one domed chitin-amber sack lit under a paler dorsal shield and shaded underneath, a lit organ on the dome, a darker "
    "capitulum in front with an eye, a dark maw and two pale hooked fangs, six short thick legs and — a mite's front pair — two feelers "
    "carried up off the head. The silhouette is a dome on stubs with two feelers up, kept fat and few-parted so it survives at 1.2× in a "
    "crowd. Built on a skeleton (scripts/imp.py): the legs are solved every frame to planted feet, the feelers are two-link whips, the "
    "fangs are hinged either side of the maw. `scuttle` is two tripods a loop with the body bobbing and pitching over them and the feelers "
    "sweeping in turn. Gameplay slot unchanged (fast, weak melee chaser); body radius still 8.5. `elite` is the bleached, heavy-jawed "
    "marking. The `death` clip is one kick and then it goes over onto its back end with its legs curled in the air and the organ going out."
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
