"""The Stinger — a scorpion that holds a line on you, and shows it.

    python3 scripts/stinger.py        # rewrites apps/ss/assets/ss-enemy-stinger.json

The pan's long gun: it stands at 440, holds still for 1.2s with a line drawn
from it to where you will be, and puts a bolt down exactly that line
(feelers: `EnemyType.aimTime`, `aimAnim: 'aim'`, `fireAnim: 'sting'`). So the
drawing has one job the rest of the roster does not — the tail is the gun, and
the gun has to be seen being loaded.

It was hand-placed, and it moved about a pixel. The tail swayed five degrees
per joint *about each segment's own centre*, so the joints came apart instead
of bending and the tip travelled nothing; the legs were six upright sticks
that swung four degrees; the body never moved at all. At game scale the loop
measured 3px of travel at its furthest point (scripts/motion.ts), against the
Courser's 19. This rebuilds it on a rig so the motion can be as big as it
needs to be without anything parting:

  - a skeleton: the body is a root bone that bobs and pitches; the tail is a
    chain of five segments and a telson, each hanging from the end of the last
    (forward kinematics); each claw is a two-bone arm, a hand and a finger that
    hinges; each leg is a femur and a tibia solved to a foot on the ground
    (two-bone inverse kinematics), so a planted foot stays planted while the
    body rides over it
  - every clip is a pose function of time over those joints, and the parts'
    tracks are solved from it — offsets and turns both, as the adapters pose
    them (offset in the parent frame, turn about the part's own origin)

Seen side-on facing +x and mirrored by the game, which is the one view where a
scorpion's tail is its silhouette. Pale husk, the arsenal's own material, so on
the pan's mid-brown sand it is the lightest thing on the floor; the vesicle is
ember because the bolt it throws is (`ss.enemy.sting`), and a shooter is the
colour of what it fires.
"""
import json, math, os

R = math.radians
D = math.degrees
def r2(x): return round(x + 0.0, 2)
def lerp(a, b, t): return a + (b - a) * t
def smooth(a, b, t):
    x = max(0.0, min(1.0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)
def cyc(t, ph=0.0): return math.sin(2 * math.pi * (t + ph))
def cyc_c(t, ph=0.0): return math.cos(2 * math.pi * (t + ph))
def wrap(a): return (a + 180.0) % 360.0 - 180.0

# ============================================================== rig
# Canvas 72×56, origin at the centre, +x forward, +y down. The ground the feet
# stand on is GROUND; everything is placed from the joints below.
GROUND = 12.0
BODY_PIVOT = (-2.0, -1.0)  # the root bone turns and bobs about here

class Bone:
    """A rest transform in the asset's frame: where the bone starts and the way it points."""
    def __init__(self, name, parent, at, heading, length=0.0):
        self.name, self.parent, self.at, self.heading, self.length = name, parent, at, heading, length

BONES = {}
def bone(name, parent, at, heading, length=0.0):
    BONES[name] = Bone(name, parent, at, heading, length)
    return BONES[name]
def end_of(b):
    return (b.at[0] + b.length * math.cos(R(b.heading)), b.at[1] + b.length * math.sin(R(b.heading)))

bone("body", None, BODY_PIVOT, 0.0)

# The tail: five metasomal segments and the telson, curling back, up and over
# the back so the vesicle rides above the carapace with the sting cocked
# forward and down. Headings are world degrees at rest (+y down, so a rising
# heading turns clockwise on screen — the way this tail curls).
TAIL_ROOT = (-13.2, -2.6)
TAIL = [  # (length, rest heading, width at root, width at tip)
    (5.0, 200.0, 5.0, 4.8),
    (5.0, 236.0, 4.8, 4.6),
    (5.0, 268.0, 4.6, 4.4),
    (5.2, 298.0, 4.4, 4.2),
    (5.6, 326.0, 4.2, 4.2),
]
TELSON_REST = 18.0
p, parent = TAIL_ROOT, "body"
for i, (L, h, _, _) in enumerate(TAIL):
    b = bone(f"tail_{i}", parent, p, h, L)
    p, parent = end_of(b), b.name
bone("telson", parent, p, TELSON_REST, 6.0)

# The claws: a shoulder under the front of the carapace, an arm of two bones
# (femur up and forward, patella down and forward), the hand, and the movable
# finger hinged at the hand's tip. The far claw is the same arm a little higher
# and further back, drawn behind the body.
def claw(side, shoulder, h1, h2, hh):
    bone(f"{side}_humerus", "body", shoulder, h1, 5.4)
    bone(f"{side}_forearm", f"{side}_humerus", end_of(BONES[f"{side}_humerus"]), h2, 4.6)
    bone(f"{side}_hand", f"{side}_forearm", end_of(BONES[f"{side}_forearm"]), hh, 5.4)
    hand = BONES[f"{side}_hand"]
    c, s = math.cos(R(hand.heading)), math.sin(R(hand.heading))
    hinge = (hand.at[0] + 5.4 * c - 1.4 * s, hand.at[1] + 5.4 * s + 1.4 * c)
    bone(f"{side}_finger", f"{side}_hand", hinge, hand.heading + 6.0, 5.4)
claw("near", (10.4, 1.2), -36.0, 20.0, -2.0)
claw("far", (8.8, -1.4), -52.0, 8.0, -12.0)

# The legs: three a side, hips along the underside of the body. Each is a
# femur and a tibia solved every frame to a foot on the ground, the knee bent
# up — a scorpion stands in its legs like a table in a frame, knees above the
# body line — and a short tarsus off the foot. Foot x at rest; the far side is
# set back a little and stands a touch higher, since it is further away.
LEGS = {  # name: (hip, rest foot x, femur length, tibia length)
    "near_f": ((5.0, 2.4), 12.6, 5.0, 9.6),
    "near_m": ((0.6, 2.9), 3.8, 4.8, 9.4),
    "near_b": ((-4.4, 2.8), -11.4, 5.0, 9.8),
    "far_f": ((4.2, 1.2), 10.4, 4.6, 8.8),
    "far_m": ((-0.2, 1.6), 1.8, 4.4, 8.6),
    "far_b": ((-5.0, 1.4), -12.2, 4.6, 9.0),
}
FAR_LIFT = 1.4  # the far feet stand this much higher on screen
def ground_of(leg): return GROUND - (FAR_LIFT if leg.startswith("far") else 0.0)
for leg, (hip, fx, lf, lt) in LEGS.items():
    bone(f"{leg}_femur", "body", hip, -90.0, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", end_of(BONES[f"{leg}_femur"]), 90.0, lt)
    bone(f"{leg}_tarsus", f"{leg}_tibia", end_of(BONES[f"{leg}_tibia"]), 90.0, 2.4)

def ik(hip, foot, lf, lt, bend):
    """Femur and tibia headings (world degrees) putting the foot at `foot`, knee on the `bend` side."""
    dx, dy = foot[0] - hip[0], foot[1] - hip[1]
    d = max(1e-3, min(lf + lt - 1e-3, math.hypot(dx, dy)))
    base = math.atan2(dy, dx)
    a = math.acos(max(-1.0, min(1.0, (lf * lf + d * d - lt * lt) / (2 * lf * d))))
    th_f = base - bend * a
    kx, ky = hip[0] + lf * math.cos(th_f), hip[1] + lf * math.sin(th_f)
    th_t = math.atan2(foot[1] - ky, foot[0] - kx)
    return D(th_f), D(th_t)

def knee_bend(leg):
    """Which way the knee folds so it rises above the hip: forward legs fold back, rear legs forward."""
    return 1 if LEGS[leg][1] >= LEGS[leg][0][0] else -1

# Re-seat the legs at rest on their IK solution, so the drawing is the pose.
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, knee_bend(leg))
    BONES[f"{leg}_femur"].heading = hf
    BONES[f"{leg}_tibia"].at = end_of(BONES[f"{leg}_femur"])
    BONES[f"{leg}_tibia"].heading = ht
    BONES[f"{leg}_tarsus"].at = end_of(BONES[f"{leg}_tibia"])
    BONES[f"{leg}_tarsus"].heading = 90.0 + (18.0 if fx >= hip[0] else -18.0)

# ---- forward kinematics
def compose(parent_xf, local):
    (px, py, pa), (lx, ly, la) = parent_xf, local
    c, s = math.cos(R(pa)), math.sin(R(pa))
    return (px + lx * c - ly * s, py + lx * s + ly * c, pa + la)
def invert_apply(xf, pt, ang):
    """`pt, ang` given in the world, expressed in frame `xf`."""
    x, y, a = xf
    c, s = math.cos(R(a)), math.sin(R(a))
    dx, dy = pt[0] - x, pt[1] - y
    return (dx * c + dy * s, -dx * s + dy * c, ang - a)
REST = {n: (b.at[0], b.at[1], b.heading) for n, b in BONES.items()}
LOCAL = {}
for n, b in BONES.items():
    LOCAL[n] = REST[n] if b.parent is None else invert_apply(REST[b.parent], b.at, b.heading)

def solve(pose):
    """
    World transforms of every bone for `pose`: a dict of
      body: (dx, dy, dtheta)       — the root's travel and pitch about BODY_PIVOT
      <bone>: dtheta               — a turn about the bone's own start
      abs:<bone>: heading          — the bone's world heading outright (IK)
    """
    out = {}
    def xf(n):
        if n in out: return out[n]
        b = BONES[n]
        if b.parent is None:
            dx, dy, dth = pose.get("body", (0.0, 0.0, 0.0))
            out[n] = (b.at[0] + dx, b.at[1] + dy, b.heading + dth)
        else:
            px, py, pa = compose(xf(b.parent), (LOCAL[n][0], LOCAL[n][1], 0.0))
            a = pa + LOCAL[n][2] + pose.get(n, 0.0)
            if f"abs:{n}" in pose: a = pose[f"abs:{n}"]
            out[n] = (px, py, a)
        return out[n]
    for n in BONES: xf(n)
    return out

# ============================================================== parts
def poly(pts): return {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in pts]}
def ell(rx, ry): return {"kind": "ellipse", "rx": r2(rx), "ry": r2(ry)}
def circ(r): return {"kind": "circle", "r": r2(r)}
def rect(w, h, corner=None): return {"kind": "rect", "w": r2(w), "h": r2(h), "corner": r2(corner if corner is not None else min(w, h) / 2)}
INK_THIN = {"color": "$ink", "width": "thin"}
# The game's adapters draw a stroke centred on the edge and over the fill, where
# the gallery's SVG lays it under — so in play half of every outline eats into
# the shape it rims. On the big masses that is a firmer edge; on a 4px tail
# segment or a claw finger it is most of the part. Those take the hairline.
INK_HAIR = {"color": "$ink", "width": "hair"}

parts = []
ATTACH = {}  # part id -> bone it rides
def put(id, bone_name, at, rot, shape, fill, stroke=None, opacity=None, scale=None):
    """A part placed in the world at rest, riding `bone_name` from then on."""
    p = {"id": id, "at": [r2(at[0]), r2(at[1])]}
    if abs(rot) > 1e-6: p["rot"] = r2(rot)
    if scale is not None: p["scale"] = scale
    if opacity is not None: p["opacity"] = opacity
    p["shape"] = shape
    p["fill"] = fill
    if stroke: p["stroke"] = stroke
    parts.append(p)
    ATTACH[id] = bone_name
def on_bone(bone_name, along=0.0, across=0.0):
    """A point in the bone's rest frame, and the bone's heading, in the world."""
    x, y, a = REST[bone_name]
    c, s = math.cos(R(a)), math.sin(R(a))
    return (x + along * c - across * s, y + along * s + across * c), a

def bar(L, w0, w1, over=0.6):
    """A limb segment from 0 to L along +x, `w0` wide at the root and `w1` at the tip, ends rounded off."""
    return poly([(-over, -w0 * 0.36), (0.0, -w0 / 2), (L, -w1 / 2), (L + over, -w1 * 0.36),
                 (L + over, w1 * 0.36), (L, w1 / 2), (0.0, w0 / 2), (-over, w0 * 0.36)])

def leg_parts(leg, femur, tibia, tarsus, knee, stroke=None):
    b = BONES
    at, a = on_bone(f"{leg}_tarsus"); put(f"{leg}_tarsus", f"{leg}_tarsus", at, a, bar(2.4, 1.2, 0.7, 0.4), tarsus, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(b[f"{leg}_tibia"].length, 1.9, 1.1), tibia, stroke)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(b[f"{leg}_femur"].length, 2.3, 2.0), femur, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_knee", f"{leg}_tibia", at, 0.0, circ(1.25), knee)

def claw_parts(side, arm, hand, finger, stroke):
    b = BONES
    at, a = on_bone(f"{side}_humerus"); put(f"{side}_humerus", f"{side}_humerus", at, a, bar(5.4, 2.4, 2.2), arm)
    at, a = on_bone(f"{side}_forearm"); put(f"{side}_forearm", f"{side}_forearm", at, a, bar(4.6, 2.4, 2.8), arm)
    # The movable finger under the hand, so its root tucks in behind the palm.
    at, a = on_bone(f"{side}_finger")
    put(f"{side}_finger", f"{side}_finger", at, a,
        poly([(-0.8, -0.9), (1.6, -1.0), (3.6, -1.1), (5.6, -1.8), (5.0, -0.6), (3.4, 0.5), (1.2, 1.0), (-0.8, 1.0)]), finger, stroke)
    # The hand: a swollen palm and the fixed finger in one outline — the chela.
    at, a = on_bone(f"{side}_hand")
    put(f"{side}_hand", f"{side}_hand", at, a,
        poly([(-0.4, -1.6), (1.0, -3.0), (3.4, -3.5), (5.6, -2.9), (8.2, -2.1), (10.4, -0.8), (11.2, 0.6),
              (10.0, 0.1), (7.6, -0.6), (5.9, -0.3), (5.4, 1.2), (4.6, 2.6), (2.6, 3.2), (0.6, 2.6), (-0.4, 1.4)]), hand, stroke)
    at, a = on_bone(f"{side}_hand", 3.0, -1.5)
    put(f"{side}_hand_gloss", f"{side}_hand", at, a, ell(1.9, 0.7), "$white@0.22")

# ---- far side: legs, then the claw, both a step darker than the near side
for leg in ("far_b", "far_m", "far_f"):
    leg_parts(leg, "$husk.dark", "$husk.dark", "$husk.dark", "$husk")
claw_parts("far", "$husk.dark", "$husk", "$husk.dark", INK_HAIR)

# ---- the tail, behind the body: segments darkening toward the root, a dark
# joint between each pair, a pale keel along the outside of the curl
TAIL_FILL = ["$husk.dark", "$husk", "$husk", "$husk.light", "$husk.light"]
for i, (L, h, w0, w1) in enumerate(TAIL):
    n = f"tail_{i}"
    at, a = on_bone(n)
    put(n, n, at, a, poly([(-0.8, -w0 * 0.42), (0.2, -w0 / 2), (L * 0.7, -w1 / 2 - 0.3), (L + 0.8, -w1 * 0.44),
                             (L + 0.8, w1 * 0.44), (L * 0.7, w1 / 2 + 0.3), (0.2, w0 / 2), (-0.8, w0 * 0.42)]),
        TAIL_FILL[i], INK_HAIR)
    at, a = on_bone(n, L * 0.45, -w0 * 0.22)
    put(f"{n}_keel", n, at, a, rect(L * 0.7, 0.8, 0.4), "$husk.light2@soft")
    at, a = on_bone(n, L + 0.2)
    put(f"{n}_joint", n, at, a, rect(0.9, w1 * 0.8, 0.45), "$husk.dark")
# The telson: an ember vesicle — the charge — and the aculeus, a bone hook
# curling in toward the ventral side, which is the inside of the curl.
at, a = on_bone("telson", 2.8)
put("glow", "telson", at, a, circ(5.2), "$ember@ghost")
put("vesicle", "telson", at, a, ell(3.6, 2.7), "$ember.dark", INK_HAIR)
at, a = on_bone("telson", 3.2, -0.9)
put("vesicle_core", "telson", at, a, ell(1.8, 1.1), "$ember")
at, a = on_bone("telson", 5.6)
ACULEUS = [(-0.6, -1.6), (1.8, -1.2), (3.6, -0.2), (4.8, 1.4), (5.2, 3.0), (4.2, 1.8), (2.6, 1.0), (0.6, 1.2), (-0.6, 1.4)]
put("aculeus", "telson", at, a, poly(ACULEUS), "$bone.light", INK_HAIR)

# ---- the body: mesosoma (seven plates, the tail's root under the last) and
# the carapace in front, low and wide, with the median eyes on a mound
MESO = [(-14.4, -1.2), (-13.0, -4.4), (-8.0, -6.2), (-2.0, -6.6), (3.2, -6.0), (5.4, -3.8),
        (5.6, 1.6), (2.0, 3.6), (-6.0, 3.8), (-12.0, 2.6), (-14.6, 1.0)]
put("meso", "body", (0, 0), 0, poly(MESO), "$husk", INK_THIN)
put("meso_side", "body", (-4.0, 1.8), 0, ell(9.6, 1.6), "$husk.dark@soft")
for i, x in enumerate((-11.4, -8.4, -5.4, -2.4, 0.6, 3.4)):
    top = -3.8 - 2.6 * math.sin(math.pi * (x + 14.4) / 20.0)
    put(f"plate_{i}", "body", (x, top + 3.4), 8.0, rect(0.8, 7.4, 0.4), "$husk.dark")
put("meso_gloss", "body", (-4.6, -4.8), -3.0, ell(7.4, 1.1), "$white@soft")
# The hive's organ on the back, where every body in the hive wears it.
parts.append({"id": "organ", "at": [-4.6, -4.2], "scale": [0.52, 0.44], "use": "ss.lib.organ"}); ATTACH["organ"] = "body"
CARA = [(3.0, -5.4), (7.0, -6.2), (11.0, -5.2), (13.8, -2.8), (14.4, -0.4), (13.2, 1.6), (9.0, 2.8), (3.8, 2.6)]
put("carapace", "body", (0, 0), 0, poly(CARA), "$husk.light", INK_THIN)
put("carapace_gloss", "body", (8.2, -4.2), -6.0, ell(3.6, 0.9), "$white@0.3")
put("eye_mound", "body", (9.6, -5.8), 0, ell(1.9, 1.1), "$husk")
put("eye", "body", (9.9, -6.2), 0, circ(0.9), "$ink")
put("eye_glint", "body", (10.2, -6.5), 0, circ(0.35), "$white")
put("chelicera", "body", (14.4, 0.6), 0, ell(1.4, 1.1), "$husk.dark", INK_HAIR)

# ---- near side: the claw, then the legs over everything
claw_parts("near", "$husk.dark", "$husk.light", "$husk", INK_HAIR)
for leg in ("near_b", "near_m", "near_f"):
    leg_parts(leg, "$husk", "$husk.dark", "$husk.dark", "$husk.light2", INK_HAIR)

ids = [p["id"] for p in parts]
assert len(ids) == len(set(ids)), "duplicate part ids"
BASE = {p["id"]: p for p in parts}

# ============================================================== motion
def posed_parts(pose):
    """Every part's (x, y, rot) under `pose`, as the adapters would pose it."""
    world = solve(pose)
    out = {}
    for pid, bn in ATTACH.items():
        p = BASE[pid]
        at, rot = tuple(p["at"]), p.get("rot", 0.0)
        lx, ly, la = invert_apply(REST[bn], at, rot)
        out[pid] = compose(world[bn], (lx, ly, la))
    return out
REST_PARTS = posed_parts({})

def keyset(n): return [i / n for i in range(n + 1)]
def tracks(pose_at, ts, extra=None):
    """Solve `pose_at(t)` at every `t` to per-part x/y/rot offset tracks (linear between keys)."""
    series = {pid: ([], [], []) for pid in ATTACH}
    for t in ts:
        now = posed_parts(pose_at(t))
        for pid, (x, y, a) in now.items():
            bx, by, ba = REST_PARTS[pid]
            series[pid][0].append(x - bx); series[pid][1].append(y - by); series[pid][2].append(wrap(a - ba))
    out = []
    for pid in ids:
        xs, ys, rs = series[pid]
        for prop, vs in (("x", xs), ("y", ys), ("rot", rs)):
            if max(abs(v) for v in vs) > 0.01:
                out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
    for pid, prop, fn in (extra or []):
        out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(fn(t))] for t in ts], "ease": "linear"})
    return out

def plant_legs(pose, feet):
    """Solve every leg's femur and tibia to put its foot at `feet[leg]`, against the body as posed."""
    world = solve(pose)
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, knee_bend(leg))
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_tarsus"] = BONES[f"{leg}_tarsus"].heading + pose.get("tarsus", 0.0)
    return pose

def rest_feet(dx=0.0, lift=None):
    return {leg: (fx + dx, ground_of(leg) - (lift or {}).get(leg, 0.0)) for leg, (hip, fx, lf, lt) in LEGS.items()}

def tail_pose(pose, deltas):
    for i, d in enumerate(deltas[:-1]): pose[f"tail_{i}"] = pose.get(f"tail_{i}", 0.0) + d
    pose["telson"] = pose.get("telson", 0.0) + deltas[-1]
    return pose

def telson_heading(pose):
    return solve(pose)["telson"][2]

# The aimed pose, which the shot leaves from: the tail raised and opened out
# so the vesicle stands high over the carapace, and the telson turned until the
# line from the vesicle to the hook's point runs along +x — the line the game
# draws. Solved rather than guessed, so it stays level whatever the rest pose.
ACULEUS_TIP = (5.6 + 5.2, 3.0)  # the hook's point, in the telson's frame
VESICLE_AT = 2.8
ACULEUS_TIP_DIR = D(math.atan2(ACULEUS_TIP[1], ACULEUS_TIP[0] - VESICLE_AT))  # vesicle → point

def reach(body, tip, direction):
    """
    Tail deltas (five segments and the telson) that put the hook's point at
    `tip` with the vesicle-to-point line along `direction`, for the body posed
    at `body`. The telson's heading follows from the direction outright; the
    five segments are found by a small coordinate descent that prefers the
    rest curl and an even bend over the chain, so a pose is asked for as a
    place and a bearing rather than as six angles.
    """
    th = direction - ACULEUS_TIP_DIR
    c, s_ = math.cos(R(th)), math.sin(R(th))
    goal = (tip[0] - (ACULEUS_TIP[0] * c - ACULEUS_TIP[1] * s_), tip[1] - (ACULEUS_TIP[0] * s_ + ACULEUS_TIP[1] * c))
    def cost(ds):
        pose = {"body": body}
        tail_pose(pose, list(ds) + [0.0])
        x, y, _ = solve(pose)["telson"]
        smooth_ = sum((ds[i] - ds[i + 1]) ** 2 for i in range(4))
        return (x - goal[0]) ** 2 + (y - goal[1]) ** 2 + 0.0004 * sum(d * d for d in ds) + 0.0008 * smooth_
    ds, step_ = [0.0] * 5, 16.0
    best = cost(ds)
    while step_ > 0.01:
        moved = False
        for i in range(5):
            for sgn in (1, -1):
                trial = ds[:]; trial[i] += sgn * step_
                c2 = cost(trial)
                if c2 < best: ds, best, moved = trial, c2, True
        if not moved: step_ /= 2
    pose = {"body": body}
    tail_pose(pose, ds + [0.0])
    tel = th - solve(pose)["telson"][2]
    return ds + [wrap(tel)]

def tail_set(pose, deltas):
    for i, d in enumerate(deltas[:5]): pose[f"tail_{i}"] = d
    pose["telson"] = deltas[5]
    return pose

def mix(a, b, t): return [lerp(x, y, t) for x, y in zip(a, b)]

# The four places the tail is asked to be, as a point and a bearing for the
# hook, each against the body as it is posed there.
AIM_BODY = (-0.6, 1.0, -3.0)
TAIL_AIMED = reach(AIM_BODY, (11.0, -23.0), 0.0)    # high over the head, the hook level on the line
COIL_BODY = (0.0, 1.6, 0.0)
TAIL_COILED = reach(COIL_BODY, (-6.0, -13.0), 70.0)  # wound in and back over the plates
STRIKE_BODY = (2.0, 0.6, 4.0)
TAIL_STRUCK = reach(STRIKE_BODY, (24.0, -5.0), 26.0)  # thrown down the line in front of the claws
def headings(body_th, hs):
    """Tail deltas that lay the segments and the telson along world headings `hs`."""
    rest = [BONES[f"tail_{i}"].heading for i in range(5)] + [BONES["telson"].heading]
    out, acc = [], body_th
    for h, r in zip(hs, rest):
        d = wrap(h - r - acc)
        out.append(d); acc += d
    return out
DEATH_BODY = (0.0, 4.2, -2.0)
# Down on the sand behind, and only the last joints still curled up off it —
# the way a dead scorpion's tail lies.
TAIL_DEAD = headings(DEATH_BODY[2], [152.0, 172.0, 200.0, 236.0, 272.0, 318.0])
def aimed():
    return tail_set({"body": AIM_BODY}, TAIL_AIMED)

# ---- prowl: the walk, and what it is doing standing at 440
PROWL = 0.6
TRIPOD = {"near_f": 0.0, "near_b": 0.0, "far_m": 0.0, "near_m": 0.5, "far_f": 0.5, "far_b": 0.5}
STRIDE = 3.4  # half a step, px either side of the rest foot
def step(t, ph):
    """Foot offset along x and its lift, for a leg at phase `ph`: stance pushes back, swing arcs forward."""
    u = (t + ph) % 1.0
    if u < 0.55:  # stance: planted, sliding back under the body
        return lerp(STRIDE, -STRIDE, u / 0.55), 0.0
    v = (u - 0.55) / 0.45  # swing: up and forward
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 3.2 * math.sin(math.pi * v)
def prowl_pose(t):
    # Two bobs a loop, one per tripod, and a pitch that lags them.
    bob = 0.9 * (0.5 - 0.5 * math.cos(4 * math.pi * t))
    pose = {"body": (0.5 * cyc(t, 0.1), bob, 1.6 * cyc(2 * t, 0.2))}
    # The tail rides it as a wave running out from the root: each joint the
    # same swing a little later, so the vesicle traces a figure rather than a
    # line, and gets there last.
    tail_pose(pose, [7.0 * cyc(t, -0.12 * i) for i in range(5)] + [9.0 * cyc(t, -0.66)])
    # The claws carried forward and a little apart, swinging against the step,
    # the fingers working.
    for side, ph in (("near", 0.0), ("far", 0.5)):
        pose[f"{side}_humerus"] = 8.0 * cyc(t, ph)
        pose[f"{side}_forearm"] = -5.0 * cyc(t, ph + 0.1)
        pose[f"{side}_finger"] = 14.0 * (0.5 + 0.5 * cyc(2 * t, ph))
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        dx, lift = step(t, TRIPOD[leg])
        feet[leg] = (fx + dx, ground_of(leg) - lift)
    return plant_legs(pose, feet)

# ---- aim: 1.2s, stretched by the game to the hold, and the shot leaves on
# the last frame. Four beats: the crouch (body down, claws in, the tail coiled
# tighter — gathering), the raise (the tail climbs and opens to the aimed
# pose), the lock (held on the line, trembling with the load) and still.
def aim_pose(t):
    crouch = smooth(0.0, 0.22, t)
    rise = smooth(0.2, 0.62, t)
    shiver = math.sin(2 * math.pi * 7 * t) * smooth(0.6, 0.72, t) * (1 - smooth(0.9, 1.0, t))
    body = [lerp(lerp(0.0, c, crouch), a, rise) for c, a in zip(COIL_BODY, AIM_BODY)]
    pose = {"body": tuple(body)}
    tail = mix(mix([0.0] * 6, TAIL_COILED, crouch), TAIL_AIMED, rise)
    tail_set(pose, [d + 1.4 * shiver * (1 if i % 2 else -1) for i, d in enumerate(tail)])
    for side in ("near", "far"):
        pose[f"{side}_humerus"] = lerp(0.0, 16.0, crouch) - 10.0 * rise
        pose[f"{side}_forearm"] = lerp(0.0, -22.0, crouch) + 8.0 * rise
        pose[f"{side}_finger"] = 26.0 * smooth(0.1, 0.4, t)
    return plant_legs(pose, rest_feet())

# ---- sting: 0.3s from the aimed pose. The tail whips forward over the head
# and down the line, the body thrown after it, then the recoil back past rest
# and settling into the walk's first frame.
def sting_pose(t):
    walk = prowl_pose(0.0)
    strike = smooth(0.0, 0.22, t)
    back = smooth(0.26, 0.62, t)
    settle = smooth(0.62, 1.0, t)
    pose = {}
    walk_tail = [walk.get(f"tail_{i}", 0.0) for i in range(5)] + [walk.get("telson", 0.0)]
    recoil = [d * 1.25 for d in TAIL_COILED]
    tail = mix(TAIL_AIMED, TAIL_STRUCK, strike)
    tail = mix(tail, recoil, back)
    tail_set(pose, mix(tail, walk_tail, settle))
    body = [lerp(a, b, strike) for a, b in zip(AIM_BODY, STRIKE_BODY)]
    body = [lerp(x, y, back) for x, y in zip(body, (-0.8, 0.4, -1.5))]
    pose["body"] = tuple(lerp(x, y, settle) for x, y in zip(body, walk["body"]))
    for side in ("near", "far"):
        for part, a0, a1 in (("humerus", 6.0, -10.0), ("forearm", -14.0, 10.0), ("finger", 26.0, 0.0)):
            n = f"{side}_{part}"
            pose[n] = lerp(lerp(a0, a1, strike), walk[n], settle)
    # The feet go from where the aim planted them to where the walk's first
    # frame has them, in the settle — a shuffle, not a slide.
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        dx, lift = step(0.0, TRIPOD[leg])
        feet[leg] = (fx + dx * settle, ground_of(leg) - lift * settle)
    return plant_legs(pose, feet)

# ---- death: one strike into nothing, then the tail falls out flat behind,
# the legs fold up under it and the body settles onto the sand. Still by 0.85.
def death_pose(t):
    jab = math.sin(math.pi * smooth(0.0, 0.3, t))
    fall = smooth(0.25, 0.8, t)
    pose = {"body": (0.0, lerp(0.0, DEATH_BODY[1], fall) - 0.8 * jab, lerp(0.0, DEATH_BODY[2], fall) + 3.0 * jab)}
    jab_tail = [d * 0.6 for d in TAIL_STRUCK]
    tail_set(pose, mix(mix([0.0] * 6, jab_tail, jab), TAIL_DEAD, fall))
    for side in ("near", "far"):
        pose[f"{side}_humerus"] = 36.0 * fall
        pose[f"{side}_forearm"] = 18.0 * fall
        pose[f"{side}_finger"] = 30.0 * fall
    # The legs curl: each foot drawn in under its hip and up off the floor.
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx = hip[0] + (fx - hip[0]) * lerp(1.0, 0.35, fall)
        feet[leg] = (hx, lerp(ground_of(leg), ground_of(leg) + 1.0, fall))
    return plant_legs(pose, feet)

def glow(scale_fn): return [("glow", "scale", scale_fn), ("vesicle_core", "scale", lambda t: 0.8 + 0.2 * scale_fn(t))]

animations = {}
TS_PROWL = keyset(12)
animations["prowl"] = {
    "description": "The walk, and its idle at the standoff: six legs in two tripods, each foot planted while the body rides over it and lifted on the way forward; the body bobs once a step and pitches after it; the tail rides the step as a wave from the root out, so the vesicle arrives last; the claws swing against the stride with the fingers working.",
    "duration": PROWL,
    "tracks": tracks(prowl_pose, TS_PROWL, glow(lambda t: 1.0 + 0.12 * cyc(t, -0.66))),
}
TS_AIM = keyset(24)
animations["aim"] = {
    "description": "The hold, played once over it (EnemyType.aimTime): it crouches and coils — claws drawn in and opened, the tail wound tighter — then the tail climbs and opens until the vesicle stands high over the head and the hook points along +x, exactly the line the game draws; it holds there trembling with the load, the vesicle burning brighter the whole way, and is still on the last frame, which is the frame the shot leaves.",
    "duration": 1.2,
    "tracks": tracks(aim_pose, TS_AIM, glow(lambda t: 1.0 + 0.9 * smooth(0.15, 1.0, t)) + [("vesicle", "scale", lambda t: 1.0 + 0.16 * smooth(0.3, 1.0, t))]),
}
TS_STING = keyset(15)
animations["sting"] = {
    "description": "The shot, from the aimed pose: the tail whips forward over the head and down the line with the body thrown after it and the claws flung wide, the glow spending itself; then the recoil back past the curl and a settle onto the walk's first frame, so the walk picks up without a cut.",
    "duration": 0.3,
    "tracks": tracks(sting_pose, TS_STING, glow(lambda t: 1.9 - 1.1 * smooth(0.0, 0.3, t) + 0.2 * smooth(0.3, 1.0, t)) + [("vesicle", "scale", lambda t: 1.16 - 0.24 * smooth(0.0, 0.2, t) + 0.08 * smooth(0.2, 0.8, t))]),
}
TS_DEATH = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "It strikes once into nothing, then everything lets go: the tail falls back to lie out flat behind, the claws drop open, the legs curl in under it and the body settles onto the sand; the vesicle and the organ go out. Still from 0.85.",
    "duration": 0.5,
    "tracks": tracks(death_pose, TS_DEATH, [("glow", "opacity", lambda t: 1.0 - smooth(0.1, 0.7, t)),
                                             ("vesicle_core", "opacity", lambda t: 1.0 - 0.9 * smooth(0.2, 0.8, t)),
                                             ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.2, 0.8, t))]),
}

# ============================================================== document
skeleton_joints, bones = {}, []
for n, b in BONES.items():
    skeleton_joints[n] = b.at
    if b.parent is not None: bones.append([b.parent, n])
    if b.length > 0 and not any(c.parent == n for c in BONES.values()):
        skeleton_joints[f"{n}_end"] = end_of(b); bones.append([n, f"{n}_end"])

DESCRIPTION = (
    "A scorpion, the other turn of the Lance's slot and the furthest thing from you on the pan. Seen side-on facing +x and mirrored by the game: "
    "a low plated body in pale husk with a wide carapace in front, two big chelae carried forward, six legs standing in a frame with their knees "
    "above the body line, and a five-jointed tail curling back, up and over to an ember vesicle and a bone hook — the arch of the tail is the "
    "silhouette, and the vesicle is ember because the bolt it throws is (`ss.enemy.sting`). "
    "Built on a skeleton (scripts/stinger.py): the tail is a chain of segments each hanging off the last, the claws are two-bone arms with a "
    "hinged finger, and the legs are solved every frame to a foot on the ground, so a planted foot stays planted while the body rides over it. "
    "`prowl` is the walk and the idle at the standoff; the game plays `aim` once over its 1.2s hold (EnemyType.aimTime) — a crouch and a coil, "
    "then the tail climbs until the hook points along +x, exactly the line the game draws, and holds there trembling — and `sting` once at the "
    "shot, the tail whipping down the line and recoiling onto the walk's first frame. No `elite` variant: a squad body is never marked. "
    "Gameplay radius 13. The `death` clip strikes once into nothing and then lets the tail fall out flat behind."
)

doc = {
    "id": "ss.enemy.stinger",
    "name": "Stinger",
    "description": DESCRIPTION,
    "tags": ["enemy"],
    "size": [72, 56],
    "meta": {"radius": 13},
    "parts": parts,
    "animations": animations,
    "skeleton": {"joints": {k: [r2(v[0]), r2(v[1])] for k, v in skeleton_joints.items()}, "bones": bones},
}

# ============================================================== the house format
def one(v): return json.dumps(v, ensure_ascii=False)
def write(doc, path):
    L = ["{"]
    for k in ("id", "name", "description", "tags", "size", "meta"):
        L.append(f'  "{k}": {one(doc[k])},')
    L.append('  "parts": [')
    L.append(",\n".join(f"    {one(p)}" for p in doc["parts"]))
    L.append("  ],")
    L.append('  "skeleton": {')
    L.append('    "joints": {')
    L.append(",\n".join(f"      {one(k)}: {one(v)}" for k, v in doc["skeleton"]["joints"].items()))
    L.append("    },")
    L.append(f'    "bones": {one(doc["skeleton"]["bones"])}')
    L.append("  },")
    L.append('  "animations": {')
    anims = []
    for name, a in doc["animations"].items():
        body = [f'    {one(name)}: {{', f'      "description": {one(a["description"])},', f'      "duration": {one(a["duration"])},', '      "tracks": [']
        body.append(",\n".join(f"        {one(t)}" for t in a["tracks"]))
        body.append("      ]")
        body.append("    }")
        anims.append("\n".join(body))
    L.append(",\n".join(anims))
    L.append("  }")
    L.append("}")
    open(path, "w").write("\n".join(L) + "\n")

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-stinger.json")
    write(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(parts)} parts, {len(animations)} clips, {n_tracks} tracks")
