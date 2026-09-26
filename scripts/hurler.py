"""The Hurler — a rhinoceros beetle that throws the hive at you, one body at a time.

    python3 scripts/hurler.py        # rewrites apps/ss/assets/ss-enemy-hurler.json

The pan's heavy, in the Bulwark's slot: where the Bulwark is a wall, this is a
catapult. It walks in slowly with a live Mite held up over its own back and,
every seven seconds, heaves it at you (feelers: `fireInterval: 7`,
`fireAnim: 'heave'`, `shotSpawn: 'imp'` — the game lobs a live Mite and stands
it up where it lands). So the load is the silhouette: nothing else in the game
carries something above itself, and the thing it carries is what it throws.

It was hand-placed, and its walk moved four pixels at game scale: legs turned
about their own centres, arms that rocked a few degrees, a dome that never
went anywhere. This rebuilds it on the shared rig (scripts/rig.py):

  - the body is a root bone that bobs, pitches and lurches forward on every
    footfall; the head hangs off it on a neck bone so it can nod after the
    step and drop in the death
  - the front legs are the arms — a humerus, a forearm and a claw, chained
    off the shoulders on the pronotum — and the load rides the near claw, so
    anything the arms do the load does, a beat later down the chain
  - the four walking legs are a femur and a tibia solved every frame to a
    foot on the ground (two-bone IK), so a planted foot stays planted while
    the dome rolls over it

Colour: the dome was `$carapace`, and on the pan's sunlit sand that sat at the
floor's own tone (contrast 1.01). The family stays purple, moved up the ramp to
`$mauve` (a dusty rose-grey, the pan's dulled cut of the old carapace purple —
a first rebuild in pastel `$heather` was the loudest thing on the sand) in
three values: the dome `$mauve.light2` with its lower flank in `$mauve`, the
pronotum and head `$mauve.light`, and the far limbs, belly and seams
`$mauve.dark`/`dark2` — light on top where the sun is. It measures 1.92 against the
pan, with the orange Mite it carries counted in.

The heave's arc is a lob, not a punch (the game's shot has `shotArc: 70`): the
game launches the real Mite from the body on the clip's first frame, so the
held one is gathered back, whipped up and let go by 0.26 (0.18s), rising and
fading roughly where the game's Mite is climbing through at that moment.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 84×76, origin at the centre, +x forward, +y down.
SIZE = [84, 76]
GROUND = 19.0
FAR_LIFT = 1.2
BODY_PIVOT = (-3.0, 4.0)

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, BODY_PIVOT, 0.0)
# The head hangs off the front of the pronotum on a short neck and reaches
# forward; the horn and the mandibles ride it.
bone("head", "body", (9.6, 2.4), 12.0, 5.0)

# The arms: the front pair of legs, raised. A shoulder on the pronotum, a
# humerus up and back, a forearm up, and a claw that closes over the load.
ARMS = {  # side: (shoulder, elbow, wrist, claw heading) — the load held overhead between them
    "near": ((8.4, -3.6), (11.6, -12.0), (6.4, -18.6), -128.0),
    "far": ((5.8, -5.4), (-6.4, -11.0), (-5.8, -21.0), -24.0),
}
CLAW = 5.0
def _heading(a, b): return D(math.atan2(b[1] - a[1], b[0] - a[0]))
def _len(a, b): return math.hypot(b[0] - a[0], b[1] - a[1])
for side, (sh, el, wr, h3) in ARMS.items():
    bone(f"{side}_humerus", "body", sh, _heading(sh, el), _len(sh, el))
    bone(f"{side}_forearm", f"{side}_humerus", el, _heading(el, wr), _len(el, wr))
    bone(f"{side}_claw", f"{side}_forearm", wr, h3, CLAW)

# The walking legs: mid and hind a side, hips under the dome, knees thrown
# outward — the mid leg's forward, the hind leg's back — the stance of a
# thing too heavy to stand in its legs any other way.
LEGS = {  # name: (hip, rest foot x, femur, tibia)
    "far_h": ((-11.4, 6.6), -16.4, 6.0, 9.4),
    "far_m": ((-0.4, 7.0), 5.4, 5.8, 9.2),
    "near_h": ((-10.6, 8.0), -19.2, 6.6, 10.2),
    "near_m": ((1.6, 8.4), 9.8, 6.4, 10.0),
}
def ground_of(leg): return GROUND - (FAR_LIFT if leg.startswith("far") else 0.0)
def knee_bend(leg): return 1 if leg.endswith("_m") else -1
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, knee_bend(leg))
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", RIG.end_of(f"{leg}_femur"), ht, lt)
    bone(f"{leg}_foot", f"{leg}_tibia", RIG.end_of(f"{leg}_tibia"), 0.0 if leg.endswith("_m") else 180.0, 2.6)

RIG.seal()
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
def leg_parts(leg, femur, tibia, foot, stroke):
    b = BONES
    at, a = on_bone(f"{leg}_foot"); put(f"{leg}_foot", f"{leg}_foot", at, a, bar(2.6, 1.8, 1.0, 0.5), foot, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(b[f"{leg}_tibia"].length, 2.8, 1.8), tibia, stroke)
    # A tooth on the outside of the tibia — a digging beetle's leg.
    at, a = on_bone(f"{leg}_tibia", b[f"{leg}_tibia"].length * 0.55, 1.3 * (1 if leg.endswith("_m") else -1))
    put(f"{leg}_spur", f"{leg}_tibia", at, a, ell(1.4, 0.7), tibia)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(b[f"{leg}_femur"].length, 3.6, 2.8), femur, stroke)

CLAW_SHAPE = poly([(-0.8, -1.5), (2.0, -2.1), (4.4, -3.2), (6.6, -1.8), (4.8, -1.3), (3.4, 0.0),
                   (4.8, 1.3), (6.6, 1.8), (4.4, 3.2), (2.0, 2.1), (-0.8, 1.5)])
def arm_parts(side, humerus, forearm, claw, stroke):
    at, a = on_bone(f"{side}_humerus"); put(f"{side}_humerus", f"{side}_humerus", at, a, bar(BONES[f"{side}_humerus"].length, 3.8, 3.0), humerus, stroke)
    at, a = on_bone(f"{side}_forearm"); put(f"{side}_forearm", f"{side}_forearm", at, a, bar(BONES[f"{side}_forearm"].length, 3.0, 2.4), forearm, stroke)
    at, a = on_bone(f"{side}_forearm"); put(f"{side}_elbow", f"{side}_forearm", at, 0.0, circ(1.7), claw)
    at, a = on_bone(f"{side}_claw"); put(f"{side}_claw", f"{side}_claw", at, a, CLAW_SHAPE, claw, stroke)

# ---- far side, a step darker: legs, then the arm behind everything
for leg in ("far_h", "far_m"):
    leg_parts(leg, "$mauve.dark", "$mauve.dark2", "$mauve.dark2", INK_HAIR)
arm_parts("far", "$mauve.dark", "$mauve.dark2", "$mauve", INK_HAIR)

# ---- the body: belly, the dome of the elytra, the pronotum, the head
BELLY = [(-20.0, 3.0), (-17.0, 7.6), (-8.0, 10.0), (2.0, 9.8), (8.6, 7.0), (6.0, 2.0), (-18.0, 1.0)]
put("belly", "body", (0, 0), 0, poly(BELLY), "$mauve.dark", INK_HAIR)
for i, x in enumerate((-14.6, -9.4, -4.2, 1.0)):
    put(f"sternite_{i}", "body", (x, 8.4 - 0.1 * abs(x + 5)), 12.0, rect(0.9, 3.2, 0.45), "$mauve.dark2")
# The dome: high and round, a superellipse over a shallow keel — the beetle's
# whole back is its two elytra, closed, and it is the biggest light thing on
# the floor.
DOME_C, DOME_A, DOME_B, DOME_N = (-8.4, 2.4), 15.2, 16.4, 2.5
def dome_top(u, shrink=0.0):
    """A point on the dome's upper edge, u from 0 (front) to 1 (back), `shrink` in from the rim."""
    th = math.pi * u
    c, s_ = math.cos(th), math.sin(th)
    x = DOME_C[0] + (DOME_A - shrink) * math.copysign(abs(c) ** (2 / DOME_N), c)
    y = DOME_C[1] - (DOME_B - shrink) * abs(s_) ** (2 / DOME_N)
    return (x, y)
def dome_keel(u):
    """The lower edge, front (u=0) to back (u=1): a shallow curve that tucks up at both ends."""
    x = lerp(DOME_C[0] + DOME_A, DOME_C[0] - DOME_A, u)
    return (x, DOME_C[1] + 3.2 * math.sin(math.pi * u) ** 0.7)
DOME = [dome_top(i / 20) for i in range(21)] + [dome_keel(1 - i / 8) for i in range(1, 8)]
put("elytron", "body", (0, 0), 0, poly(DOME), "$mauve.light2", INK_THIN)
# The lower flank of the near elytron in shade: the mid value, under the light.
SHADE = [dome_top(1 - i / 10 * 0.14) for i in range(11)]
SHADE = [(x, max(y, -1.4)) for x, y in SHADE]
SHADE = [(DOME_C[0] - DOME_A + 0.2, -0.6)] + [(lerp(DOME_C[0] - DOME_A + 1.0, DOME_C[0] + DOME_A - 1.0, i / 10), -0.6 + 1.2 * math.sin(math.pi * i / 10)) for i in range(11)] + \
        [(DOME_C[0] + DOME_A - 0.2, -0.2)] + [dome_keel(i / 8) for i in range(9)]
put("elytron_shade", "body", (0, 0), 0, poly(SHADE), "$mauve")
# The split between the two elytra runs over the crown; three striae follow
# the curve of the shell down its side.
SEAM = [dome_top(0.12 + 0.8 * i / 12, 0.6) for i in range(13)] + [dome_top(0.92 - 0.8 * i / 12, 2.0) for i in range(13)]
put("seam", "body", (0, 0), 0, poly(SEAM), "$mauve.dark2")
for i, sh in enumerate((5.0, 8.4)):
    STRIA = [dome_top(0.2 + 0.66 * j / 10, sh) for j in range(11)] + [dome_top(0.86 - 0.66 * j / 10, sh + 0.8) for j in range(11)]
    put(f"stria_{i}", "body", (0, 0), 0, poly(STRIA), "$mauve")
put("gloss", "body", (-11.0, -9.4), -10.0, ell(6.0, 1.4), "$white@0.35")
# The hive's organ, set into the top of the dome under the load.
RIG.use("organ", "body", (-7.2, -5.2), "ss.lib.organ", scale=[0.72, 0.6])
# The pronotum: a shield over the shoulders, the arms coming out of its top.
PRONOTUM = [(3.0, -7.0), (7.2, -8.8), (11.2, -7.4), (13.4, -3.2), (13.0, 1.8), (10.4, 5.4), (5.6, 6.0), (3.0, 1.0)]
put("pronotum", "body", (0, 0), 0, poly(PRONOTUM), "$mauve.light", INK_THIN)
put("pronotum_rim", "body", (0, 0), 0, poly([(4.0, 3.2), (10.4, 3.8), (12.8, 0.8), (13.0, 1.8), (10.4, 5.4), (5.6, 6.0)]), "$mauve.dark")
put("pronotum_gloss", "body", (8.2, -6.2), -18.0, ell(2.8, 0.8), "$white@0.3")
# The head, low and forward, with the horn curving up off it.
at, a = on_bone("head", 2.6, 0.4)
put("head", "head", at, 0.0, ell(4.4, 3.8), "$mauve.light", INK_HAIR)
at, a = on_bone("head", 5.0, 3.2)
put("mandible", "head", at, 18.0, poly([(-1.2, -1.0), (1.6, -0.8), (3.2, 0.6), (1.0, 0.8), (-1.2, 1.2)]), "$carapace.dark", INK_HAIR)
# The horn: rooted on the snout, sweeping forward and up to a point that
# curls back. Its origin is its root, so a larger horn grows out of the head.
HORN_ROOT, _ = on_bone("head", 4.4, -1.8)
HORN = [(-2.6, 0.6), (-1.4, -2.4), (1.2, -6.4), (3.8, -10.4), (5.0, -14.0), (4.2, -15.4),
        (3.6, -12.8), (1.6, -9.4), (-0.4, -6.8), (-2.0, -4.6), (-3.2, -1.8)]
put("horn", "head", HORN_ROOT, 0.0, poly(HORN), "$husk", INK_HAIR)
put("horn_shade", "head", HORN_ROOT, 0.0, poly([(-3.0, -1.4), (-1.8, -4.4), (-0.2, -6.8), (1.8, -9.6), (1.2, -8.2), (-1.0, -5.6), (-2.2, -3.4)]), "$husk.dark")
at, a = on_bone("head", 3.4, -0.8)
put("eye", "head", at, 0.0, circ(1.25), "$ink")
put("eye_glint", "head", (at[0] + 0.4, at[1] - 0.4), 0.0, circ(0.42), "$white")

# ---- near side: the legs over the belly
for leg in ("near_h", "near_m"):
    leg_parts(leg, "$mauve", "$mauve", "$mauve", INK_HAIR)

# ---- the load: a live Mite held up over the back in the claws, riding the
# near claw. The far claw is behind it, the near claw closes over its front.
LOAD_AT = (0.0, -24.0)
LOAD_ROT = -14.0
LOAD_SCALE = 0.62
RIG.use("load", "near_claw", LOAD_AT, "ss.enemy.imp", scale=[LOAD_SCALE, LOAD_SCALE], rot=LOAD_ROT)
arm_parts("near", "$mauve", "$mauve.dark", "$mauve.light", INK_HAIR)

RIG.check()

# ============================================================== motion
def plant_legs(pose, feet):
    world = solve(pose)
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, knee_bend(leg))
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_foot"] = BONES[f"{leg}_foot"].heading + pose.get("foot", {}).get(leg, 0.0)
    pose.pop("foot", None)
    return pose

def rest_feet():
    return {leg: (fx, ground_of(leg)) for leg, (hip, fx, lf, lt) in LEGS.items()}

def arms(pose, h, f, c, far_lag=0.0, far_h=None):
    """Both arms at humerus/forearm/claw deltas; the far arm a touch behind.
    `far_h` overrides the far humerus: it starts pointing back over the dome,
    so the swing that lays the near arm forward only stands the far one up."""
    for side in ("near", "far"):
        k = 1.0 if side == "near" else 1.0 - far_lag
        pose[f"{side}_humerus"] = h * k if side == "near" or far_h is None else far_h
        pose[f"{side}_forearm"] = f * k
        pose[f"{side}_claw"] = c * k
    return pose

# ---- plod: the walk and the idle. Two steps a loop, diagonal pairs.
PLOD = 1.1
PAIR = {"near_m": 0.0, "far_h": 0.0, "near_h": 0.5, "far_m": 0.5}
STRIDE = 4.2
def step(t, ph):
    """Foot offset along x and its lift: planted and pushed back for most of the loop, a short heavy swing."""
    u = (t + ph) % 1.0
    if u < 0.62:
        return lerp(STRIDE, -STRIDE, u / 0.62), 0.0
    v = (u - 0.62) / 0.38
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 3.6 * math.sin(math.pi * v)

def plod_pose(t):
    # Each footfall (t = 0 and 0.5, as a pair lands) drops the dome onto it;
    # it rides up over the planted pair and falls onto the next. The pitch
    # rocks nose-down onto each landing, the weight lurches forward after it.
    fall = 0.5 + 0.5 * math.cos(4 * math.pi * (t - 0.06))
    bob = 2.2 * fall - 0.6
    pitch = 3.2 * math.sin(4 * math.pi * (t - 0.02))
    lurch = 1.0 * math.sin(4 * math.pi * (t + 0.12))
    pose = {"body": (lurch, bob, pitch)}
    pose["head"] = 7.0 * math.sin(4 * math.pi * (t - 0.12))
    # The arms carry the load as a spring does: the bob runs up them a beat
    # late at each joint, so the Mite rises when the dome falls and teeters
    # forward and back once a loop.
    sway = 7.0 * cyc(t, -0.1)
    h = sway + 5.0 * math.sin(4 * math.pi * (t - 0.14))
    f = 1.2 * sway + 9.0 * math.sin(4 * math.pi * (t - 0.22))
    c = 12.0 * math.sin(4 * math.pi * (t - 0.3))
    arms(pose, h, f, c, far_lag=0.15)
    feet, rolls = {}, {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        dx, lift = step(t, PAIR[leg])
        feet[leg] = (fx + dx, ground_of(leg) - lift)
        rolls[leg] = (-30.0 if leg.endswith("_m") else 30.0) * (lift / 3.6)
    pose["foot"] = rolls
    return plant_legs(pose, feet)

# ---- heave: 0.7s, played once when the shot is fired. The game spawns the
# thrown Mite on the clip's first frame, so the windup is a short, hard
# gather (0–0.16), the throw lands the release at the top of the swing by
# 0.3, and most of the clip is the follow-through and the reload.
H_WIND, H_REL, H_OVER = 0.14, 0.26, 0.40
WIND_BODY = (-2.4, 2.0, -9.0)
THROW_BODY = (2.0, -1.2, 6.0)
OVER_BODY = (2.6, 2.2, 11.0)
WIND_ARM = (-20.0, -18.0, -16.0)
THROW_ARM = (32.0, 14.0, 12.0)
OVER_ARM = (80.0, 36.0, 26.0)

def heave_body_arm(t):
    """Body (dx, dy, dth) and arm (h, f, c) deltas at heave time t."""
    rest_b, rest_a = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    if t <= H_WIND:
        k = smooth(0.0, H_WIND, t)
        return mix(rest_b, WIND_BODY, k), mix(rest_a, WIND_ARM, k)
    if t <= H_REL:
        k = smooth(H_WIND, H_REL, t)
        # The forearm and claw lag the humerus through the throw — a whip.
        arm = [lerp(WIND_ARM[0], THROW_ARM[0], k),
               lerp(WIND_ARM[1], THROW_ARM[1], k ** 1.5),
               lerp(WIND_ARM[2], THROW_ARM[2], k ** 2.0)]
        return mix(WIND_BODY, THROW_BODY, k), arm
    if t <= H_OVER:
        k = smooth(H_REL, H_OVER, t)
        return mix(THROW_BODY, OVER_BODY, k), mix(THROW_ARM, OVER_ARM, k)
    # Recovery: back up past rest by a little and settle.
    k = smooth(H_OVER, 0.9, t)
    back = math.sin(math.pi * smooth(H_OVER + 0.18, 1.0, t)) * (1 - smooth(0.9, 1.0, t))
    body = mix(OVER_BODY, rest_b, k)
    body = [body[0] - 0.8 * back, body[1], body[2] - 3.0 * back]
    arm = mix(OVER_ARM, rest_a, k)
    arm = [arm[0] - 8.0 * back, arm[1] - 6.0 * back, arm[2] - 10.0 * back]
    return body, arm

def heave_pose(t):
    body, arm = heave_body_arm(t)
    pose = {"body": tuple(body)}
    pose["head"] = -8.0 * smooth(0.0, H_WIND, t) * (1 - smooth(H_WIND, H_REL, t)) + 10.0 * smooth(H_WIND, H_OVER, t) * (1 - smooth(H_OVER, 0.95, t))
    arms(pose, *arm, far_lag=0.08)
    # The feet stay planted and brace: the hind pair takes the windup, the
    # front pair the throw — the forward foot slides a little on the sand.
    feet = rest_feet()
    slide = 1.6 * smooth(H_WIND, H_OVER, t) * (1 - smooth(0.6, 1.0, t))
    feet["near_m"] = (feet["near_m"][0] + slide, feet["near_m"][1])
    return plant_legs(pose, feet)

# ---- death: 0.52s. The arms drop forward and let the load go; it rolls off
# them onto the sand in front and dims. The dome sags onto legs that fold
# under it, the head and horn go down, the organ goes out. Still from 0.85.
DEATH_BODY = (1.0, 7.0, 5.0)
def death_pose(t):
    jolt = math.sin(math.pi * smooth(0.0, 0.2, t))
    fall = smooth(0.12, 0.8, t)
    pose = {"body": (lerp(0.0, DEATH_BODY[0], fall) - 0.8 * jolt, lerp(0.0, DEATH_BODY[1], fall) - 1.2 * jolt,
                     lerp(0.0, DEATH_BODY[2], fall) - 5.0 * jolt)}
    pose["head"] = 26.0 * smooth(0.25, 0.8, t)
    drop = smooth(0.05, 0.55, t)
    arms(pose, -10.0 * jolt + 92.0 * drop, 24.0 * drop, 36.0 * smooth(0.1, 0.6, t), far_lag=0.1, far_h=-10.0 * jolt + 150.0 * smooth(0.1, 0.65, t))
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        out = 1.0 if leg.endswith("_m") else -1.0
        feet[leg] = (fx + out * 2.4 * fall, ground_of(leg))
    return plant_legs(pose, feet)

# ---- the load's own path. It rides the near claw while it is held; once let
# go it is the load's own: in the heave it flies on up and forward and is
# gone (the game's Mite is already in the air), and a new one climbs into the
# claws; in the death it rolls off the dropped arms onto the sand.
LOAD_REST = RIG.posed_parts({})["load"]
def load_world(pose_fn, t):
    return RIG.posed_parts(pose_fn(t))["load"]

def heave_load(t):
    """(x, y, rot, scale, opacity) of the load as offsets from rest (scale and opacity as multipliers)."""
    if t <= H_REL:
        x, y, a = load_world(heave_pose, t)
        return x - LOAD_REST[0], y - LOAD_REST[1], wrap(a - LOAD_REST[2]), 1.0, 1.0
    # Flight: the velocity it left the claw with, carried on, turning end over end.
    x0, y0, a0 = load_world(heave_pose, H_REL)
    x1, y1, a1 = load_world(heave_pose, H_REL - 0.03)
    vx, vy = (x0 - x1) / 0.03, (y0 - y1) / 0.03
    dt = t - H_REL
    if dt <= 0.10:
        x, y = x0 + vx * dt * 0.4, y0 + vy * dt * 0.4
        fade = 1.0 - smooth(0.0, 0.10, dt)
        grow = 1.0 - 0.3 * smooth(0.0, 0.10, dt)
        return x - LOAD_REST[0], y - LOAD_REST[1], wrap(a0 + 260.0 * dt - LOAD_REST[2]), grow, fade
    # The new one: climbs into the claws from behind the head and is held by 0.9.
    x, y, a = load_world(heave_pose, t)
    k = smooth(0.62, 0.9, t)
    return x - LOAD_REST[0], y - LOAD_REST[1] + 5.0 * (1 - k), wrap(a - LOAD_REST[2]), lerp(0.35, 1.0, k) if t >= 0.62 else 0.35, k

GROUND_LOAD = (29.0, GROUND - 4.6)
def death_load(t):
    let_go = 0.34
    if t <= let_go:
        x, y, a = load_world(death_pose, t)
        return x - LOAD_REST[0], y - LOAD_REST[1], wrap(a - LOAD_REST[2]), 1.0, 1.0
    x0, y0, a0 = load_world(death_pose, let_go)
    k = smooth(let_go, 0.78, t)
    hop = 3.0 * math.sin(math.pi * smooth(let_go, 0.62, t)) * (1 - smooth(0.62, 0.78, t))
    x = lerp(x0, GROUND_LOAD[0], k)
    y = lerp(y0, GROUND_LOAD[1], k ** 1.6) - hop
    a = a0 + 150.0 * k
    return x - LOAD_REST[0], y - LOAD_REST[1], wrap(a - LOAD_REST[2]), 1.0, 1.0 - 0.45 * smooth(0.55, 0.85, t)

def with_load(tr, fn, ts):
    """Replace the load's rig-solved tracks with its own path `fn`."""
    tr = [x for x in tr if x["part"] != "load"]
    vals = [fn(t) for t in ts]
    for i, prop in enumerate(("x", "y", "rot", "scale", "opacity")):
        vs = [v[i] for v in vals]
        base = 1.0 if prop in ("scale", "opacity") else 0.0
        if max(abs(v - base) for v in vs) > 0.01:
            tr.append({"part": "load", "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
    return tr

animations = {}
TS_PLOD = keyset(22)
animations["plod"] = {
    "description": "The walk and the idle: a heavy four-legged step in diagonal pairs, each foot planted and pushed back while the dome rolls over it and lifted only for a short swing; the dome drops onto every footfall and pitches onto it, the weight lurching forward after, the head nodding a beat late; the arms carry the Mite like a spring, the bob running up them joint by joint so the load rises as the dome falls and teeters forward and back.",
    "duration": PLOD,
    "tracks": RIG.tracks(plod_pose, TS_PLOD, [("organ", "scale", lambda t: 1.0 + 0.08 * cyc(t, 0.2))], still=("near_elbow", "far_elbow")),
}
TS_HEAVE = sorted(set(keyset(28) + [H_WIND, H_REL, H_OVER]))
animations["heave"] = {
    "description": "The throw, played once as the shot leaves (the game spawns the Mite on the first frame): a hard gather — the dome rocks back and squats, the arms wind the load further back over it — then the arms whip forward, humerus first and the claws last, and let the load go at the top of the swing; it flies on and is gone while the arms follow through down past the head and the dome pitches onto its front feet; then everything swings back past rest, settles, and a new Mite climbs into the claws.",
    "duration": 0.7,
    "tracks": with_load(RIG.tracks(heave_pose, TS_HEAVE, [("organ", "scale", lambda t: 1.0 + 0.3 * smooth(0.0, H_WIND, t) * (1 - smooth(H_REL, 0.6, t)))],
                                   still=("near_elbow", "far_elbow")), heave_load, TS_HEAVE),
}
TS_DEATH = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.34, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "One jolt back, then it lets go: the arms drop forward past the head and the load rolls off them onto the sand in front, where it dims; the dome sags onto legs that splay and fold under it, the head and horn go down into the sand, and the organ goes out. Still from 0.85.",
    "duration": 0.52,
    "tracks": with_load(RIG.tracks(death_pose, TS_DEATH, [("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.15, 0.75, t)),
                                                         ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.2, 0.6, t))],
                                   still=("near_elbow", "far_elbow")), death_load, TS_DEATH),
}

# ============================================================== variants
VARIANTS = {
    "elite": {
        "description": "Marked by the hive: the dome bleached to husk with bone striae, a longer bone horn, bone claws, and a brighter, bigger organ.",
        "scale": 1.25,
        "set": {
            "elytron.fill": "$husk",
            "elytron_shade.fill": "$husk.dark",
            "stria_0.fill": "$husk.dark",
            "stria_1.fill": "$husk.dark",
            "seam.fill": "$carapace",
            "pronotum.fill": "$husk.dark",
            "pronotum_rim.fill": "$carapace.light",
            "head.fill": "$husk.dark",
            "horn.fill": "$bone.light",
            "horn_shade.fill": "$bone",
            "horn.scale": [1.3, 1.3],
            "horn_shade.scale": [1.3, 1.3],
            "near_claw.fill": "$bone.light",
            "far_claw.fill": "$bone",
            "organ.scale": [0.96, 0.8],
        },
    },
}

DESCRIPTION = (
    "The pan's heavy: the Bulwark's slot, and where the Bulwark is a wall this is a catapult. A rhinoceros beetle seen side-on — a high "
    "dusty mauve dome of closed elytra split along the top, a pronotum shield, a low head with a bone horn curving up off it — walking on four "
    "legs, because the front pair are arms: they reach up and back over its own body and hold a live Mite (`use: ss.enemy.imp`, at 0.62) "
    "above the dome. The load is the silhouette: nothing else in the game carries something above itself, and the thing it carries is "
    "what it throws (EnemyType.shotSpawn — the game lobs a live Mite and stands it up where it lands). "
    "Built on a skeleton (scripts/hurler.py): the arms are chains of humerus, forearm and claw with the load riding the near claw, and "
    "the legs are solved every frame to a foot on the ground, so the dome rolls over planted feet. `plod` is the walk and idle; `heave` "
    "is the throw, played once as the shot leaves — a short hard gather, the arms whipping forward and letting go at the top of the "
    "swing, a long follow-through, and a new Mite climbing into the claws by the end. Drawn facing +x, mirrored by the game. Gameplay "
    "radius 16. `elite` is the bleached, bigger-horned version the late marking wears. The `death` clip drops the arms forward and rolls "
    "the load off them onto the ground, where it dims."
)

# The drawing sits a little low in its canvas: the heave throws the load up
# and forward, and that is where the room is kept.
Y0 = 5.0
for p in RIG.parts: p["at"] = [p["at"][0], r2(p["at"][1] + Y0)]
SKELETON = RIG.skeleton()
SKELETON["joints"] = {k: [v[0], r2(v[1] + Y0)] for k, v in SKELETON["joints"].items()}

doc = {
    "id": "ss.enemy.hurler",
    "name": "Hurler",
    "description": DESCRIPTION,
    "tags": ["enemy", "hurler"],
    "size": SIZE,
    "meta": {"radius": 16},
    "parts": RIG.parts,
    "variants": VARIANTS,
    "animations": animations,
    "skeleton": SKELETON,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-hurler.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
