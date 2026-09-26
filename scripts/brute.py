"""The Bulwark — the wall the hive walks at you when a Tracker's call is answered.

    python3 scripts/brute.py        # rewrites apps/ss/assets/ss-enemy-brute.json

The Plains' tank (feelers: `hp: 90`, `speed: 42`, `knockMul: 0.35` — "Barely
moves. Nothing you own moves it either."). It has no verb but arriving, so the
whole drawing is weight: a low plated shell as wide as the thing is tall, four
short columns of legs under it, and a pair of shearing mandibles out in front.
The shell stays the slab of orange chitin it always was — big, bright and
almost featureless on purpose, a tank has to read as mass across the screen —
but it is built now: three plates that overlap front over back, a pale dorsal
shield on top, a crest along the spine, a heavy skirt round the bottom.

It was hand-placed and its loop moved five pixels at game scale: two legs
rocked about their own centres and the shell bobbed a little. This rebuilds it
on the shared rig (scripts/rig.py):

  - the body is a root bone that sits back, lurches forward, drops and pitches;
    the head hangs off it under the brow of the shell, and each mandible is
    hinged at a socket on the head
  - four legs, each a femur and a tibia solved every frame to a clawed foot on
    the ground (two-bone IK), so a planted foot stays planted while the shell
    rolls over it and a lifted one comes down exactly where it lands

The stomp is a four-beat walk, the way the heaviest animals walk — one foot off
the ground at a time, three always under it. The near feet are the big ones:
the knee comes up high, the foot hangs, and it slams down; the shell drops
onto it, rebounds, and the weight lurches forward onto a front foot or settles
back onto a hind one. The far feet take the off-beats, smaller and a step
darker.

Colour: the chitin family it had, in three values — the flank `$chitin.dark`,
the lit shell `$chitin`, the dorsal shield `$chitin.light` — over a
`$chitin.dark2` skirt, with the legs the dark carapace purple they were. The
organs are the only bright thing on it.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 52×48, origin at the centre, +x forward, +y down.
SIZE = [52, 48]
GROUND = 16.6
FAR_LIFT = 1.4
BODY_PIVOT = (-5.0, 4.0)

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, BODY_PIVOT, 0.0)
# The head sits low under the brow of the shell and reaches forward; the two
# mandibles are hinged at sockets on its front, one over the other.
HEAD_ROOT = (6.6, 2.8)
bone("head", "body", HEAD_ROOT, 8.0, 5.0)
MAND_UP_ROOT = (13.0, 1.0)
MAND_DN_ROOT = (13.0, 5.4)
bone("mandible_up", "head", MAND_UP_ROOT, -6.0, 8.0)
bone("mandible_dn", "head", MAND_DN_ROOT, 6.0, 8.0)

# The legs: short heavy columns out from under the skirt. Front knees fold
# forward, hind knees back — a thing this heavy stands in its legs like a
# table in its frame.
LEGS = {  # name: (hip, rest foot x, femur, tibia)
    "far_b": ((-15.2, 2.6), -16.4, 5.8, 6.4),
    "far_f": ((-0.6, 2.6), 1.0, 5.8, 6.4),
    "near_b": ((-13.0, 4.2), -14.4, 6.0, 6.8),
    "near_f": ((1.6, 4.2), 3.2, 6.0, 6.8),
}
def ground_of(leg): return GROUND - (FAR_LIFT if leg.startswith("far") else 0.0)
def knee_bend(leg): return 1 if leg.endswith("_f") else -1
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, knee_bend(leg))
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", RIG.end_of(f"{leg}_femur"), ht, lt)
    bone(f"{leg}_foot", f"{leg}_tibia", RIG.end_of(f"{leg}_tibia"), 0.0, 3.0)

RIG.seal()
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
# ---- the shell's outline: a superellipse, steep and high at the front (the
# brow over the head) and long and low behind; the lower edge a shallow keel.
SHELL_C = (-4.4, 5.0)
SHELL_AF, SHELL_AB, SHELL_B, SHELL_N = 12.4, 16.8, 18.6, 2.4
def top(u, shrink=0.0):
    """A point on the shell's upper edge, u from 0 (front) to 1 (back), `shrink` in from the rim."""
    th = math.pi * u
    c, s_ = math.cos(th), math.sin(th)
    a = (SHELL_AF if c >= 0 else SHELL_AB) - shrink
    x = SHELL_C[0] + a * math.copysign(abs(c) ** (2 / SHELL_N), c)
    y = SHELL_C[1] - (SHELL_B - shrink) * abs(s_) ** (2 / SHELL_N)
    return (x, y)
def keel(u, lift=0.0):
    """The lower edge, front (u=0) to back (u=1): a shallow curve, lowest mid-body."""
    x = lerp(SHELL_C[0] + SHELL_AF, SHELL_C[0] - SHELL_AB, u)
    return (x, SHELL_C[1] + 2.4 * math.sin(math.pi * u) ** 0.8 - lift)
def band(u0, u1, s0, s1, n=14):
    """The strip of the shell's rim between u0 and u1, from `s0` in to `s1` in."""
    return [top(lerp(u0, u1, i / n), s0) for i in range(n + 1)] + [top(lerp(u1, u0, i / n), s1) for i in range(n + 1)]
def seam_line(u, w, bow=1.6, n=10):
    """A plate's edge from the crest down to the skirt, bowing forward — the front plate laps over the one behind."""
    x0, y0 = top(u, 0.2)
    x1, _ = keel(u)
    y1 = keel(u)[1] - 2.2
    out, back = [], []
    for i in range(n + 1):
        k = i / n
        x = lerp(x0, x1, k) + bow * math.sin(math.pi * k)
        y = lerp(y0, y1, k)
        h = w * (0.55 + 0.45 * math.sin(math.pi * k))
        out.append((x + h / 2, y)); back.append((x - h / 2, y))
    return out + back[::-1]

def leg_parts(leg, femur, tibia, foot, knee, stroke):
    b = BONES
    # The foot: a broad pad with three claws on the front, lying along +x.
    at, a = on_bone(f"{leg}_foot", -1.2)
    put(f"{leg}_claw", f"{leg}_foot", at, a,
        poly([(-1.2, -1.6), (2.2, -1.6), (3.8, -0.6), (5.4, 0.2), (3.6, 0.5), (4.4, 1.2), (2.4, 1.2), (2.6, 1.8),
              (0.0, 1.8), (-1.8, 1.4), (-2.2, -0.4)]), foot, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(b[f"{leg}_tibia"].length, 4.4, 3.8, 0.8), tibia, stroke)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(b[f"{leg}_femur"].length, 5.6, 4.8, 0.8), femur, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_knee", f"{leg}_tibia", at, 0.0, circ(2.5), knee)

# ---- far side, a step darker: legs behind everything
for leg in ("far_b", "far_f"):
    leg_parts(leg, "$carapace", "$carapace", "$husk.dark", "$carapace", INK_HAIR)

# ---- the head, under the brow: a squat capsule, the maw in front, the two
# mandibles hinged either side of it
at, a = on_bone("head", 2.8, 0.2)
put("head", "head", at, a, ell(6.0, 4.6), "$carapace.light", INK_HAIR)
at, a = on_bone("head", 2.2, 2.4)
put("head_shade", "head", at, a, ell(4.4, 1.6), "$carapace")
at, a = on_bone("head", 6.6, 0.8)
put("maw", "head", at, a, poly([(-1.8, -2.4), (1.2, -1.8), (2.4, 0.0), (1.2, 1.8), (-1.8, 2.4), (-0.6, 0.0)]), "$ink")
MAND = [(-1.4, 1.4), (-1.0, -1.2), (1.4, -1.9), (4.4, -1.9), (6.8, -0.8), (8.4, 1.2), (8.8, 2.6), (7.4, 1.6), (5.8, 0.8),
        (4.8, 1.4), (4.0, 0.6), (2.2, 0.9), (0.6, 1.8)]
MAND = [(x * 0.92, y * 0.92) for x, y in MAND]
def flip(pts): return [(x, -y) for x, y in pts]
at, a = on_bone("mandible_dn")
put("mandible_dn", "mandible_dn", at, a, poly(flip(MAND)), "$husk.dark", INK_HAIR)
at, a = on_bone("mandible_up")
put("mandible_up", "mandible_up", at, a, poly(MAND), "$husk", INK_HAIR)
at, a = on_bone("mandible_up", 3.6, -1.2)
put("mandible_gloss", "mandible_up", at, a, ell(2.2, 0.5), "$white@0.35")
at, a = on_bone("head", 4.6, -2.6)
put("eye", "head", at, 0.0, circ(1.0), "$ink")
put("eye_glint", "head", (at[0] + 0.35, at[1] - 0.35), 0.0, circ(0.36), "$white")

# ---- the elite's crown: spines standing up off the crest, drawn behind the
# shell so only the points show over it. Hidden unless marked.
SPINES = []
for i in range(6):
    u = 0.26 + 0.1 * i
    x, y = top(u, 1.0)
    x2, y2 = top(u + 0.03, 1.0)
    tipx, tipy = top(u + 0.015, -4.2 + 0.6 * abs(i - 2.5))
    SPINES += [(x, y), (tipx - 0.8, tipy), (x2, y2)]
SPINE_AT = top(0.5, 2.0)
put("spines", "body", SPINE_AT, 0.0, poly([(x - SPINE_AT[0], y - SPINE_AT[1]) for x, y in SPINES]), "$husk", INK_HAIR, opacity=0)

# ---- the shell
SHELL = [top(i / 32) for i in range(33)] + [keel(1 - i / 10) for i in range(1, 10)]
put("shell", "body", (0, 0), 0.0, poly(SHELL), "$chitin.dark", INK_THIN)
# The lit shell: everything above a line that runs just under the middle of
# the flank, rising to the brow — the upper two thirds of the mass in light.
def lit_floor(u):
    x = lerp(SHELL_C[0] + SHELL_AF - 0.6, SHELL_C[0] - SHELL_AB + 0.6, u)
    return (x, 4.2 - 0.4 * math.sin(math.pi * u) - 1.8 * (1 - u))
LIT = [top(i / 28, 0.7) for i in range(29)] + [lit_floor(1 - i / 12) for i in range(1, 12)]
put("shell_lit", "body", (0, 0), 0.0, poly(LIT), "$chitin")
# The skirt: the heavy rim the legs come out from under.
SKIRT = [keel(i / 14, 2.6) for i in range(15)] + [keel(1 - i / 14) for i in range(15)]
put("skirt", "body", (0, 0), 0.0, poly(SKIRT), "$chitin.dark")
for i, u in enumerate((0.12, 0.3, 0.5, 0.7, 0.88)):
    x, y = keel(u, 1.3)
    put(f"stud_{i}", "body", (x, y), 0.0, ell(1.3, 0.8), "$chitin.dark2")
# The dorsal shield: the pale plate over the top of the back.
PLATE = band(0.28, 0.76, 1.4, 9.2, 16)
put("plate", "body", (0, 0), 0.0, poly(PLATE), "$chitin.light")
# The brow: the front plate, laid over the head, its lower lip in shade.
BROW = band(0.02, 0.3, 0.9, 5.2, 12)
put("brow", "body", (0, 0), 0.0, poly(BROW), "$chitin.light@0.55")
# The plates' edges, front over back.
put("seam_a", "body", (0, 0), 0.0, poly(seam_line(0.3, 1.3, 1.8)), "$chitin.dark2")
put("seam_b", "body", (0, 0), 0.0, poly(seam_line(0.74, 1.2, 1.4)), "$chitin.dark2")
# The crest along the spine, and a few bosses on the plates — stone, not shell.
put("ridge", "body", (0, 0), 0.0, poly(band(0.3, 0.72, 0.5, 2.0, 16)), "$husk")
for i, (u, s, r) in enumerate(((0.18, 5.8, 1.3), (0.52, 9.4, 1.5), (0.86, 4.6, 1.2))):
    x, y = top(u, s)
    put(f"boss_{i}", "body", (x, y + 0.4), 0.0, ell(r, r * 0.7), "$chitin.dark")
    put(f"boss_{i}_lit", "body", (x - 0.2, y), 0.0, ell(r * 0.8, r * 0.5), "$chitin.light")
put("gloss", "body", (-3.0, -10.8), -6.0, ell(5.2, 1.0), "$white@0.3")
# The organs: the kill order broadcast from the back, one on the shield and
# one low on the rear plate; the elite's third stands on the brow.
RIG.use("organ", "body", (-5.8, -7.4), "ss.lib.organ", scale=[0.7, 0.62])
RIG.use("organ_rear", "body", (-16.4, -1.6), "ss.lib.organ", scale=[0.48, 0.44])
RIG.use("organ_top", "body", (2.4, -8.6), "ss.lib.organ", scale=[0.46, 0.42], opacity=0)

# ---- near side: the legs over the skirt
for leg in ("near_b", "near_f"):
    leg_parts(leg, "$carapace.light", "$carapace.light", "$husk", "$carapace.light", INK_HAIR)

RIG.check()

# ============================================================== motion
def plant_legs(pose, feet, rolls=None):
    world = solve(pose)
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, knee_bend(leg))
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_foot"] = (rolls or {}).get(leg, 0.0)
    return pose

# ---- stomp: 1.3s, a four-beat walk. Each foot's impact time in the loop;
# the near feet on the beats, the far ones between.
STOMP = 1.3
IMPACT = {"near_f": 0.0, "far_b": 0.25, "near_b": 0.5, "far_f": 0.75}
SWING = 0.34      # of the loop a foot is off the ground, ending at its impact
STRIDE = 3.0      # half a step, px either side of the rest foot
LIFT = {"near_f": 8.4, "near_b": 5.6, "far_f": 3.0, "far_b": 2.4}
WEIGHT = {"near_f": 1.0, "near_b": 0.9, "far_f": 0.45, "far_b": 0.4}

def since(t, t0):
    """Loop time since `t0`, in [0, 1)."""
    return (t - t0) % 1.0

def swing_phase(t, leg):
    """0 → 1 through the leg's swing, or None while it is planted."""
    d = since(t, IMPACT[leg] - SWING)
    return d / SWING if d < SWING else None

def foot(t, leg):
    """Foot x offset, lift and toe roll: pushed back through the stance; in the swing the knee comes up
    fast, the foot hangs at the top, then slams down onto its mark."""
    v = swing_phase(t, leg)
    if v is None:
        d = since(t, IMPACT[leg])  # 0 at the impact → 1 - SWING at lift-off
        return lerp(STRIDE, -STRIDE, d / (1 - SWING)), 0.0, 0.0
    x = lerp(-STRIDE, STRIDE, smooth(0.05, 0.8, v))
    up = smooth(0.0, 0.4, v) * (1 - smooth(0.66, 1.0, v) ** 1.6)
    roll = 24.0 * math.sin(math.pi * smooth(0.0, 0.7, v)) * (1 if leg.endswith("_b") else 0.6)
    return x, LIFT[leg] * up, roll

def lifted(t, leg):
    v = swing_phase(t, leg)
    return 0.0 if v is None else math.sin(math.pi * v) ** 0.7

def impact(t, leg):
    """The shock of a foot landing: the shell drops onto it fast, recovers slower, overshoots a little."""
    d = since(t, IMPACT[leg])
    if d > 0.34: return 0.0
    if d < 0.035: return smooth(0.0, 0.035, d)
    e = d - 0.035
    return math.exp(-e / 0.08) * math.cos(math.pi * e / 0.24) * (1 - smooth(0.26, 0.34, d))

def stomp_pose(t):
    dx = dy = dth = 0.0
    for leg in LEGS:
        w, lam, imp = WEIGHT[leg], lifted(t, leg), impact(t, leg)
        front = leg.endswith("_f")
        # A front foot lifted puts the weight back on the hind legs (nose up);
        # landing, the mass pitches and lurches forward onto it. A hind foot
        # the other way round, and softer.
        dth += w * ((-5.0 * lam + 5.0 * imp) if front else (2.2 * lam - 2.6 * imp))
        dx += w * ((-2.2 * lam + 2.6 * imp) if front else (0.8 * lam - 1.2 * imp))
        dy += w * ((-0.9 * lam if front else 0.3 * lam) + 2.0 * imp)
    pose = {"body": (dx, dy - 0.4, dth)}
    # The head rides the shell's drop a beat late, and the mandibles shear
    # once a step: they part as a near foot comes up and snap shut on it.
    lag = impact((t - 0.05) % 1.0, "near_f") + impact((t - 0.05) % 1.0, "near_b")
    pose["head"] = 5.0 * lag - 2.0 * (lifted(t, "near_f") + lifted(t, "near_b"))
    part = max(lifted(t, "near_f"), lifted(t, "near_b"))
    snap = impact(t, "near_f") + impact(t, "near_b")
    pose["mandible_up"] = -34.0 * part + 5.0 * snap
    pose["mandible_dn"] = 30.0 * part - 5.0 * snap
    feet, rolls = {}, {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        x, lift, roll = foot(t, leg)
        feet[leg] = (fx + x, ground_of(leg) - lift)
        rolls[leg] = roll
    return plant_legs(pose, feet, rolls)

def organ_pulse(ph):
    """The organs pulse in turn, and bounce on the landings a beat behind the shell."""
    return lambda t: 1.0 + 0.1 * cyc(t, ph) + 0.08 * (impact((t - 0.08) % 1.0, "near_f") + impact((t - 0.08) % 1.0, "near_b"))

# ---- death: 0.5s. The mass comes down: one jolt up, then the kill order stops
# broadcasting rear organ first; the mandibles fly wide and lock there, the
# crown of spines (on the elite) drops back, and the shell settles onto legs
# that buckle and splay under it. Still from 0.85.
DEATH_BODY = (1.4, 6.8, 5.0)
def death_pose(t):
    jolt = math.sin(math.pi * smooth(0.0, 0.18, t))
    fall = smooth(0.12, 0.72, t)
    land = math.sin(math.pi * smooth(0.62, 0.84, t)) * 0.8  # a last bounce as it lands
    pose = {"body": (lerp(0.0, DEATH_BODY[0], fall) - 0.6 * jolt,
                     lerp(0.0, DEATH_BODY[1], fall) - 1.6 * jolt - land,
                     lerp(0.0, DEATH_BODY[2], fall) - 3.0 * jolt)}
    pose["head"] = -8.0 * jolt + 12.0 * smooth(0.3, 0.8, t)
    wide = smooth(0.04, 0.26, t)
    pose["mandible_up"] = -46.0 * wide + 6.0 * math.sin(math.pi * smooth(0.26, 0.42, t))
    pose["mandible_dn"] = 22.0 * wide - 6.0 * math.sin(math.pi * smooth(0.26, 0.42, t))
    feet, rolls = {}, {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        out = 3.4 if leg.endswith("_f") else -3.0
        feet[leg] = (fx + out * fall, ground_of(leg))
        rolls[leg] = (-14.0 if leg.endswith("_f") else 10.0) * fall
    return plant_legs(pose, feet, rolls)

animations = {}
TS_STOMP = sorted(set(keyset(52) + [0.035, 0.285, 0.535, 0.785]))
STILL = [f"{l}_knee" for l in LEGS]
animations["stomp"] = {
    "description": "The walk and the idle, slow and four-beat, three feet always under it: each foot pushes back through a long stance while the shell rolls over it, then the knee comes up high, the foot hangs and slams down onto its mark; the near feet take the beats and the far ones the off-beats. On every landing the shell drops onto the foot and rebounds, and the mass shifts onto it — lurching and pitching forward onto a front foot, sitting back onto a hind one; the head nods after the drop, the mandibles part as a near foot rises and snap shut as it lands, and the organs pulse in turn and bounce a beat behind the shell.",
    "duration": STOMP,
    "tracks": RIG.tracks(stomp_pose, TS_STOMP, [("organ", "scale", organ_pulse(0.0)), ("organ_rear", "scale", organ_pulse(0.5)),
                                                  ("organ_top", "scale", organ_pulse(0.25))], still=STILL),
}
TS_DEATH = [0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The mass comes down: one jolt up with the mandibles flying wide, and they lock there; the three organs stop broadcasting one after another from the rear forward, the crown of spines (on the elite) drops back flat, and the plated shell settles onto legs that buckle and splay under it, bouncing once as it lands. Still from 0.85.",
    "duration": 0.5,
    "tracks": RIG.tracks(death_pose, TS_DEATH, [
        ("organ_rear", "opacity", lambda t: 1.0 - 0.9 * smooth(0.04, 0.3, t)),
        ("organ", "opacity", lambda t: 1.0 - 0.9 * smooth(0.16, 0.46, t)),
        ("organ_top", "opacity", lambda t: 1.0 - 0.9 * smooth(0.28, 0.6, t)),
        ("spines", "scale", lambda t: 1.0 - 0.3 * smooth(0.2, 0.6, t)),
        ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.2, 0.6, t)),
    ], still=STILL),
}

# ============================================================== variants
VARIANTS = {
    "elite": {
        "description": "A war caste: bleached plates, a spined crest and a third organ on the brow. When this one broadcasts, the level turns around.",
        "scale": 1.25,
        "set": {
            "plate.fill": "$husk",
            "brow.fill": "$husk@0.7",
            "ridge.fill": "$bone.light",
            "boss_0_lit.fill": "$husk.light",
            "boss_1_lit.fill": "$husk.light",
            "boss_2_lit.fill": "$husk.light",
            "organ.scale": [0.86, 0.76],
            "spines.opacity": 1,
            "organ_top.opacity": 1,
        },
    },
}

DESCRIPTION = (
    "The caste that gets sent when a Tracker's call is answered, and the Plains' wall: \"Barely moves. Nothing you own moves it either.\" "
    "Seen side-on facing +x and mirrored by the game. One heavy plated shell as wide as the thing is tall — steep and high over the head, "
    "long and low behind — in the orange chitin it always wore, big, bright and almost featureless on purpose, because a tank has to read "
    "as mass from across the screen: three values (the flank `$chitin.dark`, the lit shell `$chitin`, a pale dorsal shield), plates lapping "
    "front over back, a husk crest along the spine, a few stone bosses and a heavy studded skirt. Under the brow a squat purple head with "
    "two shearing mandibles hinged at its maw, and four short columns of legs with clawed feet. A pair of organs broadcast the kill order, "
    "one on the shield and one on the rear plate. Built on a skeleton (scripts/brute.py): the legs are solved every frame to feet on the "
    "ground, so a planted foot stays planted while the shell rolls over it. `stomp` is the walk and idle, four-beat and slow: each foot "
    "comes up high and slams down, the shell drops onto it and the mass shifts onto that leg. Gameplay radius 16. `elite` is the war caste "
    "— bleached plates, a spined crest and a third organ. The `death` clip is mass arriving on the ground: the kill order stops broadcasting "
    "rear organ first, the mandibles fly wide and lock, and the shell settles onto buckled legs."
)

# The drawing sits a little back in its canvas: the mandibles reach forward
# and that is where the room is kept.
X0, Y0 = 0.0, 0.0
for p in RIG.parts: p["at"] = [r2(p["at"][0] + X0), r2(p["at"][1] + Y0)]
SKELETON = RIG.skeleton()
SKELETON["joints"] = {k: [r2(v[0] + X0), r2(v[1] + Y0)] for k, v in SKELETON["joints"].items()}

doc = {
    "id": "ss.enemy.brute",
    "name": "Bulwark",
    "description": DESCRIPTION,
    "tags": ["enemy", "tank"],
    "size": SIZE,
    "meta": {"radius": 16},
    "parts": RIG.parts,
    "variants": VARIANTS,
    "animations": animations,
    "skeleton": SKELETON,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-brute.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
