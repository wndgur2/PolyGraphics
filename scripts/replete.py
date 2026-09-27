"""The Replete — a honeypot worker the nest filled up and stopped sending anywhere.

    python3 scripts/replete.py        # rewrites apps/ss/assets/ss-enemy-replete.json

The burrow's Husk slot (feelers `replete`: speed 48, radius 13, knockMul
0.85): slower, wider and worth more than a Husk, and not coming for you — it
is in the way. On open ground radius 13 is a statistic; in a 130px passage it
is a fifth of the width. The stage-3 elite lands on it here too, at 1.25×.

The design it had is kept: one round sac would sit in a silhouette the Mite
and the Bulwark already own, so the store is a chain — four swellings of
falling size, pinched between, dragged behind a small front end that still
has legs. The rear half has none because it is not walking, it is being
hauled. Pale shell with the amber it holds showing through. What was missing
was the haul: the loop moved seven pixels at game scale, every part turning
about its own centre. This rebuilds it on the shared rig (scripts/rig.py):

  - the front end is a root bone pivoting at the waist, so it rears up and
    throws itself forward on the haul; the head hangs off it on a neck, and
    each antenna is a two-link elbowed chain (scape and funiculus) that lags
    the head
  - six legs, a femur, a tibia and a tarsus each, solved every frame to a foot
    on the ground (two-bone IK): a tripod steps in the gather and the other in
    the recovery, and the planted feet stay planted while the body rides
  - the four swellings are frames of their own, placed each frame rather than
    swung off one another: dragged beads do not pivot on a rigid chain, they
    are jerked forward one after another and ride up over the floor as they
    go, so each is posed as a lagged surge, a hump and the tilt between its
    neighbours, and the pinches between them ride halfway between the two
    they join. Each bead also scales about its own centre, which is the swell
    running the chain the other way, tail to front — the load working forward

Values: the beads are the light value (husk shell, the honey showing through
in amber, each with the dark stretched tergite plate on its crown that a real
replete's skin is stretched between); the front end is the hive's dark
carapace, and the legs a step darker again so the store reads first.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 compose, invert_apply, poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 56×32, origin at the centre, +x forward, +y down.
SIZE = [56, 32]
GROUND = 9.0
FAR_LIFT = 1.0
WAIST = (6.2, 2.6)  # the front end rears and pitches about the petiole

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, WAIST, 0.0)
NECK = (13.8, 0.2)
bone("head", "body", NECK, -8.0, 3.0)
# The antennae: a long scape up and forward out of the front of the head, and
# the funiculus hinged at its tip, bent forward and down — an ant's elbow.
ANT = {  # side: (root, scape heading, scape len, funiculus heading, funiculus len)
    "near": ((17.4, -1.6), -62.0, 3.6, -4.0, 4.4),
    "far": ((16.6, -2.0), -80.0, 3.4, -20.0, 4.0),
}
for side, (root, h0, l0, h1, l1) in ANT.items():
    b0 = bone(f"{side}_scape", "head", root, h0, l0)
    bone(f"{side}_funic", f"{side}_scape", b0.end(), h1, l1)

# The legs: three a side from the underside of the mesosoma. Femur and tibia
# solved to a foot on the floor, knees up; the tarsus lies along the floor.
LEGS = {  # name: (hip, rest foot x, femur, tibia)
    "far_b": ((8.4, 3.4), 4.6, 3.3, 3.7),
    "far_m": ((10.2, 3.6), 10.4, 3.2, 3.6),
    "far_f": ((12.2, 3.2), 16.0, 3.2, 3.6),
    "near_b": ((9.0, 3.9), 5.2, 3.5, 3.9),
    "near_m": ((10.9, 4.1), 11.6, 3.4, 3.8),
    "near_f": ((12.9, 3.7), 17.4, 3.4, 3.8),
}
TARSUS = 1.7
def ground_of(leg): return GROUND - 0.7 - (FAR_LIFT if leg.startswith("far") else 0.0)
def knee_bend(leg): return 1 if LEGS[leg][1] >= LEGS[leg][0][0] else -1
def tarsus_heading(leg): return 16.0 if knee_bend(leg) > 0 else 164.0
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, knee_bend(leg))
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", RIG.end_of(f"{leg}_femur"), ht, lt)
    bone(f"{leg}_tarsus", f"{leg}_tibia", RIG.end_of(f"{leg}_tibia"), tarsus_heading(leg), TARSUS)

# The store: four beads of falling size from the waist back, each a frame at
# its own centre (zero-length bone, heading 0) posed outright every frame,
# and a pinch between each pair riding halfway between them.
BEADS = [  # (centre x, centre y, rx, ry)
    (0.0, 2.6, 6.6, 6.2),
    (-7.8, 3.4, 5.8, 5.4),
    (-14.2, 4.6, 4.6, 4.2),
    (-19.0, 5.8, 3.4, 3.1),
]
N = len(BEADS)
for k, (x, y, rx, ry) in enumerate(BEADS):
    bone(f"bead_{k}", "body" if k == 0 else f"bead_{k - 1}", (x, y), 0.0)
def pinch_at(k):
    """Where bead k-1 and bead k meet (k ≥ 1): halfway across their overlap."""
    (x0, y0, rx0, _), (x1, y1, rx1, _) = BEADS[k - 1], BEADS[k]
    xa, xb = x0 - rx0, x1 + rx1
    x = (xa + xb) / 2
    u = (x0 - x) / (x0 - x1)
    return (x, lerp(y0, y1, u))
for k in range(1, N):
    bone(f"pinch_{k}", f"bead_{k - 1}", pinch_at(k), 0.0)

RIG.seal()
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
SHELL, HONEY, HONEY_LIT = "$husk", "$chitin.light", "$chitin.light2"
HIDE = 0.01
FRONT, FRONT_LIT, FRONT_SHADE = "$carapace", "$carapace.light", "$carapace.dark"
LEG_NEAR, LEG_NEAR_2, LEG_FAR = "$carapace.dark", "$carapace.dark2", "$dead"

def leg_parts(leg, femur, tibia, tarsus, stroke):
    b = BONES
    at, a = on_bone(f"{leg}_tarsus"); put(f"{leg}_tarsus", f"{leg}_tarsus", at, a, bar(TARSUS, 1.1, 0.6, 0.4), tarsus, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(b[f"{leg}_tibia"].length, 1.3, 0.75), tibia, stroke)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(b[f"{leg}_femur"].length, 1.8, 1.15), femur, stroke)

def antenna(side, fill, stroke):
    _, _, l0, _, l1 = ANT[side]
    at, a = on_bone(f"{side}_scape"); put(f"{side}_scape", f"{side}_scape", at, a, bar(l0, 1.0, 0.8, 0.3), fill, stroke)
    at, a = on_bone(f"{side}_funic"); put(f"{side}_funic", f"{side}_funic", at, a, bar(l1, 0.8, 1.1, 0.4), fill, stroke)

# ---- far side: antenna and legs, the dark value, behind everything
antenna("far", LEG_FAR, None)
for leg in ("far_b", "far_m", "far_f"):
    leg_parts(leg, LEG_FAR, LEG_FAR, LEG_FAR, None)

# ---- the store, tail first so each bead overlaps the one behind it. A
# pinch (the stretched joint membrane) under each pair; the shell with the
# honey showing through most of it, lit from above so the pale rim is a
# crescent on the crown; the stretched tergite plate on the crown, which is
# the thing that says the skin was never meant to be this size; a gloss.
def bead_parts(k):
    x, y, rx, ry = BEADS[k]
    b = f"bead_{k}"
    put(b, b, (x, y), 0.0, ell(rx, ry), SHELL, INK_THIN if k < 2 else INK_HAIR)
    put(f"honey_{k}", b, (x - 0.12 * rx, y + 0.2 * ry), 0.0, ell(rx * 0.78, ry * 0.7), HONEY)
    put(f"honey_lit_{k}", b, (x + 0.1 * rx, y + 0.1 * ry), -10.0, ell(rx * 0.42, ry * 0.36), HONEY_LIT)
    # the tergite: a dark plate stretched over the crown, leaning with the curve
    ang = -100.0  # a little forward of the top
    px, py = x + 0.84 * rx * math.cos(R(ang)), y + 0.84 * ry * math.sin(R(ang))
    put(f"plate_{k}", b, (px, py), ang + 90.0, rect(rx * 0.84, max(0.9, ry * 0.19), max(0.45, ry * 0.095)), "$carapace.dark")
    put(f"gloss_{k}", b, (x - 0.38 * rx, y - 0.5 * ry), -24.0, ell(rx * 0.3, ry * 0.14), "$white@0.55")
    if k == 0:
        # The tear the elite wears: a split down the back of the biggest bead,
        # over the pinch behind it, with the store welling at its lips. Drawn
        # at a hundredth of its size, so only the variant (which sets it to
        # full) shows it.
        tx, ty = x - 0.8 * rx, y + 0.05 * ry
        put("tear", b, (tx, ty), 0.0, poly([(-0.2, -2.6), (0.5, -1.4), (-0.1, -0.4), (0.7, 0.8), (0.1, 1.8), (0.5, 2.8),
                                            (-0.5, 1.9), (-0.8, 0.8), (-0.3, -0.3), (-0.9, -1.4)]), "$ink", scale=HIDE)
        put("tear_ooze", b, (tx - 0.1, ty + 2.9), 0.0, ell(0.9, 1.2), HONEY_LIT, INK_HAIR, scale=HIDE)

for k in reversed(range(N)):
    bead_parts(k)
    if k >= 1:
        # the pinch in front of bead k, under bead k-1 (drawn next)
        px, py = pinch_at(k)
        ry = min(BEADS[k - 1][3], BEADS[k][3])
        put(f"pinch_{k}", f"pinch_{k}", (px, py), 0.0, rect(2.6, ry * 1.25, 1.2), "$husk.dark2", INK_HAIR)

# ---- the front end: petiole node, mesosoma, the organ on its back, head
put("petiole", "body", (6.6, 2.4), 10.0, ell(1.7, 2.2), FRONT, INK_HAIR)
MESO = [(x, y + 1.4) for x, y in [(7.6, 2.0), (7.4, -0.6), (8.6, -2.2), (10.6, -3.2), (12.8, -3.0), (14.4, -1.8), (14.6, 0.4),
        (13.4, 2.2), (10.6, 2.8)]]
put("thorax", "body", (0, 0), 0.0, poly(MESO), FRONT, INK_THIN)
put("thorax_lit", "body", (0, 0), 0.0, poly([(x, y + 1.4) for x, y in [(8.4, -1.6), (10.6, -2.8), (12.8, -2.6), (13.8, -1.6), (12.4, -1.8), (10.4, -1.6)]]), FRONT_LIT)
put("thorax_shade", "body", (0, 0), 0.0, poly([(x, y + 1.4) for x, y in [(8.0, 1.2), (10.8, 2.0), (13.8, 1.4), (13.4, 2.2), (10.6, 2.8), (7.6, 2.0)]]), FRONT_SHADE)
RIG.use("organ", "body", (10.8, -2.6), "ss.lib.organ", scale=[0.46, 0.4])

# the far antenna already drawn; the head over the neck
HEAD_C = (16.4, -0.5)
at, a = on_bone("head", 2.4, -0.2)
put("head", "head", HEAD_C, -8.0, poly([(-3.3, -1.2), (-2.2, -2.7), (0.0, -3.2), (2.2, -2.8), (3.5, -1.2), (3.6, 1.0), (2.4, 2.6),
                                         (0.0, 3.0), (-2.4, 2.4), (-3.4, 0.8)]), FRONT, INK_HAIR)
put("head_lit", "head", (HEAD_C[0] - 0.1, HEAD_C[1] - 1.9), -10.0, ell(2.3, 0.75), FRONT_LIT)
put("mandible", "head", (HEAD_C[0] + 3.4, HEAD_C[1] + 1.8), 18.0,
    poly([(-1.2, -0.8), (0.8, -0.9), (2.4, -0.2), (3.0, 0.8), (1.6, 0.4), (0.2, 0.8), (-1.2, 0.8)]), "$husk.dark", INK_HAIR)
put("eye", "head", (HEAD_C[0] + 1.1, HEAD_C[1] - 0.5), 0.0, ell(1.1, 0.95), "$husk.dark")
put("eye_glint", "head", (HEAD_C[0] + 1.45, HEAD_C[1] - 0.85), 0.0, circ(0.4), "$silent")
antenna("near", FRONT, INK_HAIR)

# ---- near legs over everything
for leg in ("near_b", "near_m", "near_f"):
    leg_parts(leg, LEG_NEAR, LEG_NEAR_2, LEG_NEAR_2, INK_HAIR)

RIG.check()

# ============================================================== motion
def plant_legs(pose, feet):
    world = solve(pose)
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, knee_bend(leg))
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_tarsus"] = tarsus_heading(leg) + pose.get("tarsus", 0.0) * (1 if knee_bend(leg) > 0 else -1)
    return pose

def bump(t, c, w):
    """A smooth pulse centred on `c`, `w` wide either side, wrapping round the loop."""
    d = ((t - c + 0.5) % 1.0) - 0.5
    if abs(d) >= w: return 0.0
    return 0.5 + 0.5 * math.cos(math.pi * d / w)

def frame_of(pose, beads, scales=None):
    """World frames for every bone: the skeleton solved from `pose`, the beads and pinches placed outright."""
    W = dict(solve(pose))
    S = {}
    for k, (dx, dy, dth) in enumerate(beads):
        x, y, _, _ = BEADS[k]
        W[f"bead_{k}"] = (x + dx, y + dy, dth)
        if scales: S[f"bead_{k}"] = scales[k]
    for k in range(1, N):
        (a, b) = beads[k - 1], beads[k]
        px, py = pinch_at(k)
        W[f"pinch_{k}"] = (px + (a[0] + b[0]) / 2, py + (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
    return W, S

def tracks_world(frame_at, ts, extra=None, still=()):
    """Per-part offset tracks from world frames per bone (and a scale per bone, about its origin)."""
    base = {p["id"]: p for p in RIG.parts}
    series = {pid: ([], [], [], []) for pid in RIG.attach}
    for t in ts:
        W, S = frame_at(t)
        for pid, bn in RIG.attach.items():
            p = base[pid]
            at, rot = tuple(p["at"]), p.get("rot", 0.0)
            lx, ly, la = invert_apply(RIG.rest[bn], at, rot)
            s = S.get(bn, 1.0)
            x, y, a = compose(W[bn], (lx * s, ly * s, la))
            sr = series[pid]
            sr[0].append(x - at[0]); sr[1].append(y - at[1]); sr[2].append(wrap(a - rot)); sr[3].append(s)
    ex = {(pid, prop): fn for pid, prop, fn in (extra or [])}
    out = []
    for p in RIG.parts:
        pid = p["id"]
        xs, ys, rs, ss = series[pid]
        for prop, vs in (("x", xs), ("y", ys), ("rot", rs)):
            if prop == "rot" and pid in still: continue
            if max(abs(v) for v in vs) > 0.01:
                out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
        sfn = ex.pop((pid, "scale"), None)
        svals = [sv * (sfn(t) if sfn else 1.0) for sv, t in zip(ss, ts)]
        if max(abs(v - 1.0) for v in svals) > 0.004:
            out.append({"part": pid, "prop": "scale", "keys": [[r2(t), round(v, 3)] for t, v in zip(ts, svals)], "ease": "linear"})
    for (pid, prop), fn in ex.items():
        out.append({"part": pid, "prop": prop, "keys": [[r2(t), round(fn(t), 3)] for t in ts], "ease": "linear"})
    return out

STILL = {"eye", "eye_glint"}

# ---- heave: 2.0s, one haul a loop. The beats:
#   0.00 → 0.30  the gather: the front end rears up and back off the waist,
#                head lifted, while one tripod steps forward
#   0.30 → 0.50  the haul: it throws itself forward and down onto its legs,
#                head dropped, and the waist takes the strain
#   0.34 → 0.80  the store follows: each bead is jerked forward and rides up
#                over the floor a beat after the one in front, further and
#                higher the further back it is — the sway arriving late and
#                large at the tail — and drops back onto the floor
#   0.50 → 0.85  the recovery, the other tripod stepping, and a settle
#   and, the other way down the chain, the swell: each bead fills a little in
#   turn from the tail at 0.08 to the one at the waist at 0.44 — the load
#   working forward, arriving as the haul does
HEAVE = 2.0
STRIDE = 2.2
TRIPOD = {"near_f": 0.65, "far_m": 0.65, "near_b": 0.65, "far_f": 0.15, "near_m": 0.15, "far_b": 0.15}
def step(u):
    """Foot offset along x and its lift at gait phase u: stance slides back, swing (the last 35%) arcs forward."""
    u %= 1.0
    if u < 0.65:
        return lerp(STRIDE, -STRIDE, u / 0.65), 0.0
    v = (u - 0.65) / 0.35
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 2.0 * math.sin(math.pi * v)

def gather(t): return smooth(0.0, 0.3, t) * (1 - smooth(0.3, 0.46, t))
def haul(t): return smooth(0.3, 0.46, t) * (1 - smooth(0.52, 0.86, t))

def front_surge(t):
    """The front end's travel along x: drawn back in the gather, thrown forward in the haul."""
    return -1.5 * gather(t) + 2.4 * haul(t)

LAG = 0.075
GAIN = [1.15, 1.35, 1.55, 1.75]  # how far each bead follows the front's travel
HUMP = [1.0, 1.6, 2.3, 3.0]      # how high it rides up as it is jerked forward
def bead_offsets(t):
    """
    Each bead follows the front end's travel a beat after the one in front of
    it and further: still behind while the front hauls (the chain stretched,
    the pinches drawn out), then jerked forward past it (the chain bunching
    up), riding up over the floor as it goes, and settling back.
    """
    out = []
    for k in range(N):
        u = (t - LAG * (k + 1)) % 1.0
        sx = GAIN[k] * front_surge(u)
        h = bump(t, 0.40 + LAG * (k + 1), 0.15)
        out.append([sx, -HUMP[k] * h, 0.0])
    # tilt: each bead leans along the line between its neighbours' lifts
    for k in range(N):
        ahead = out[k - 1][1] if k > 0 else -0.6 * haul(t)
        behind = out[k + 1][1] if k + 1 < N else out[k][1] * 1.2
        out[k][2] = D(math.atan2(behind - ahead, 12.0)) * 1.6
    return out

def swell(t):
    return [1.0 + 0.075 * bump(t, 0.08 + 0.12 * (N - 1 - k), 0.14) for k in range(N)]

def heave_pose(t):
    g, h = gather(t), haul(t)
    bob = 0.3 * (0.5 - 0.5 * math.cos(4 * math.pi * t))
    pose = {"body": (front_surge(t), -1.8 * g + 1.0 * h + bob, -18.0 * g + 9.0 * h)}
    pose["head"] = 10.0 * g - 12.0 * h
    # the antennae: the elbow opens as the head lifts and trails the haul,
    # each link a beat behind the one it hangs from
    for side, ph in (("near", 0.0), ("far", 0.06)):
        pose[f"{side}_scape"] = 16.0 * gather(t - 0.06 - ph) - 18.0 * haul(t - 0.08 - ph) + 4.0 * cyc(2 * t, ph)
        pose[f"{side}_funic"] = 22.0 * gather(t - 0.12 - ph) - 26.0 * haul(t - 0.14 - ph) + 6.0 * cyc(2 * t, ph - 0.1)
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        dx, lift = step(t + TRIPOD[leg])
        feet[leg] = (fx + dx, ground_of(leg) - lift)
    return plant_legs(pose, feet)

def heave_frame(t):
    return frame_of(heave_pose(t), bead_offsets(t), swell(t))

TS_HEAVE = keyset(40)
def glint_o(t): return 1.0
HEAVE_EXTRA = [("organ", "scale", lambda t: 1.0 + 0.1 * bump(t, 0.46, 0.14))]
for k in range(N):
    HEAVE_EXTRA.append((f"honey_lit_{k}", "opacity", (lambda k: lambda t: 0.85 + 0.15 * bump(t, 0.08 + 0.12 * (N - 1 - k), 0.14))(k)))

# ---- death: 0.46s. A flinch at the front; then the swellings let go from
# the far end inward — each bulges once against its own skin, then goes
# slack and sags onto the floor off the pinch behind it, its gloss going
# off — and the small animal at the front folds its legs and puts its head
# down. Still from 0.85.
GO = [(0.30, 0.54), (0.20, 0.44), (0.10, 0.34), (0.02, 0.24)]  # bead k: (bulge start, slack end)
def let_go(t, k):
    a, b = GO[k]
    m = (a + b) / 2
    bulge = smooth(a, a + (m - a) * 0.6, t) * (1 - smooth(m - 0.02, b, t))
    slack = smooth(m - 0.02, b, t)
    return bulge, slack

def death_pose(t):
    flinch = smooth(0.0, 0.1, t) * (1 - smooth(0.12, 0.34, t))
    fall = smooth(0.3, 0.8, t)
    pose = {"body": (-0.8 * flinch + 0.6 * fall, -1.0 * flinch + 2.6 * fall, -9.0 * flinch + 7.0 * fall)}
    pose["head"] = 10.0 * flinch + 22.0 * fall
    for side in ("near", "far"):
        pose[f"{side}_scape"] = 30.0 * flinch + 26.0 * fall
        pose[f"{side}_funic"] = 24.0 * flinch + 24.0 * fall
    pose["tarsus"] = 30.0 * fall
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx = hip[0] + (fx - hip[0]) * lerp(1.0, 0.45, fall)
        feet[leg] = (hx, ground_of(leg) + 0.6 * fall)
    return plant_legs(pose, feet)

def death_beads(t):
    out, sc = [], []
    for k in range(N):
        bulge, slack = let_go(t, k)
        _, y, _, ry = BEADS[k]
        # slack: shrinks to three quarters and sinks so it still sits on the floor
        s = 1.0 + 0.16 * bulge - 0.26 * slack
        sink = (1.0 - s) * ry  # bottom stays on the floor
        out.append([0.3 * slack * (k - 1.5), -0.5 * bulge + sink + 0.5 * slack, (-6.0 + 3.0 * k) * slack])
        sc.append(s)
    return out, sc

def death_frame(t):
    beads, sc = death_beads(t)
    return frame_of(death_pose(t), beads, sc)

TS_DEATH = sorted(set([round(i / 40, 3) for i in range(35)] + [0.85, 1.0]))
TS_DEATH = [t for t in TS_DEATH if t <= 0.85] + [1.0]
DEATH_EXTRA = [("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.3, 0.8, t)),
               ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.3, 0.6, t))]
for k in range(N):
    a, b = GO[k]
    DEATH_EXTRA.append((f"gloss_{k}", "opacity", (lambda a, b: lambda t: 1.0 - 0.9 * smooth((a + b) / 2, b, t))(a, b)))
    DEATH_EXTRA.append((f"honey_lit_{k}", "opacity", (lambda a, b: lambda t: 1.0 + 0.0 * t - 0.6 * smooth((a + b) / 2, b, t))(a, b)))

animations = {
    "heave": {
        "description": "The haul, and the idle it walks in: the front end rears up and back off the waist with the head lifted, one tripod stepping, then throws itself forward and down onto its legs; the store follows a beat at a time — each bead jerked forward and riding up over the floor after the one in front, further and higher the further back it is, so the sway arrives late and large at the dragged tail — while a swell runs the chain the other way, tail to front, arriving as the haul does. The other tripod steps in the recovery; the antennae trail every move of the head.",
        "duration": HEAVE,
        "tracks": tracks_world(heave_frame, TS_HEAVE, HEAVE_EXTRA, STILL),
    },
    "death": {
        "description": "The larder is opened: a flinch at the front, then the four swellings let go one after another from the far end inward — each bulging once against its own skin, then going slack and sagging onto the floor off the pinch behind it, the gloss going off it — and the small animal at the front folds its legs, drops onto the floor and puts its head down; the organ goes out. Still from 0.85.",
        "duration": 0.46,
        "tracks": tracks_world(death_frame, TS_DEATH, DEATH_EXTRA, STILL),
    },
}

# ============================================================== variants
ELITE_SET = {}
for k in range(N):
    ELITE_SET[f"bead_{k}.fill"] = "$bone.light"
    ELITE_SET[f"honey_{k}.fill"] = "$chitin"
    ELITE_SET[f"honey_lit_{k}.fill"] = "$gold.light"
    ELITE_SET[f"plate_{k}.fill"] = "$carapace"
ELITE_SET["pinch_1.fill"] = "$ink"
ELITE_SET["tear.scale"] = 1
ELITE_SET["tear_ooze.scale"] = 1
ELITE_SET["organ.scale"] = [0.6, 0.52]
variants = {
    "elite": {
        "description": "Filled past what the chain was for: every bead bleached to bone with the store burning white through it, the tergite plates pulled paler still, and the skin over the pinch behind the biggest has torn — a black split down its back with the honey welling out of it.",
        "scale": 1.25,
        "set": ELITE_SET,
    },
}

# ============================================================== document
DESCRIPTION = (
    "A worker the nest filled up and stopped sending anywhere — the honeypot caste, kept as a larder until something needs feeding. "
    "One round sac would sit in a silhouette the Mite and the Bulwark already own, so it is a chain: four swellings of falling size, "
    "pinched between, hauled by a small front end that still has legs. The rear half has none, because that half is not walking, it is "
    "being dragged. Each bead is pale shell with the amber it is holding showing through, lit on the crown, and wears the dark tergite "
    "plate its skin was stretched away from; the front end is the hive's dark carapace with the organ on its back, and the legs a step "
    "darker again, so the store reads first. In a 130px passage a body this long across the floor is not an obstacle you get past. "
    "Built on a skeleton (scripts/replete.py): the front end pivots at the waist and rears and hauls, the head hangs off a neck with "
    "two elbowed antennae that trail it, and six legs are solved every frame to feet on the floor; the beads are dragged, not swung — "
    "each is jerked forward and rides up over the floor a beat after the one in front, further and higher toward the tail, the pinches "
    "riding between them, while a swell runs the chain the other way, tail to front. Drawn facing +x, the game flips it. Gameplay "
    "radius 13. The `death` clip empties it the way it was filled, one swelling at a time from the far end inward, and only then folds "
    "the small animal carrying them."
)

# The drawing sits a unit left of centre: the haul throws the head and the
# antennae forward, and that is where the room is kept.
X0 = -1.0
for p in RIG.parts: p["at"] = [r2(p["at"][0] + X0), p["at"][1]]
SKELETON = RIG.skeleton()
SKELETON["joints"] = {k: [r2(v[0] + X0), v[1]] for k, v in SKELETON["joints"].items()}

doc = {
    "id": "ss.enemy.replete",
    "name": "Replete",
    "description": DESCRIPTION,
    "tags": ["enemy", "replete"],
    "size": SIZE,
    "meta": {"radius": 13},
    "parts": RIG.parts,
    "variants": variants,
    "animations": animations,
    "skeleton": SKELETON,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-replete.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
