"""The Antlion — the pan's heavy body, and the one that hides.

    python3 scripts/antlion.py        # rewrites apps/ss/assets/ss-enemy-antlion.json

The Husk's slot on the Salt Pan: slow, heavy and in the way, except that it is
under the sand until you are 130px from it (feelers: `EnemyType.ambush`), and
the only warning it gives is the ripple over it. So the document is two
drawings: the grub that comes up, and the mound it is under.

It was hand-placed and it moved like a photograph. Six stubs swung four
degrees about their own centres, the jaws turned on their own middles, the
body never moved at all: the crawl measured 5px of travel at game scale
(scripts/motion.ts) and the buried `creep` 1.4 — the one warning the player
gets, and nobody could see it. It was also the colour of the floor it lies on
(contrast 1.00 against `ss.env.pan`). This rebuilds it on the shared rig
(scripts/rig.py):

  - a skeleton seen from above: the thorax is the root bone, which surges,
    sways and yaws on the step; the abdomen is a chain of three segments
    hanging off it (FK), so the heavy sack swings after the body as a wave;
    the head is a bone of its own that counter-turns, and each jaw is a bone
    hinged at the head's front corner
  - six legs, each a femur and a tibia solved every frame to a foot on the
    ground (two-bone IK), knees bowed out, so a planted foot stays planted
    while the body slides over it and the stride is what moves
  - pale timber, so on the pan's mid-brown sand it is a light thing on a dark
    floor instead of the floor itself; rust bands and dark legs for the dark
    value, bone jaws and ember tips as the accents

The buried state is the same document with the body taken off: a mound of
pale sand with a dark pit in it, two sickle tips working up out of the pit,
and a ripple running out from under the mound in rings — crest and trough,
so it reads on the sand whether the sand is lit or not.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, cyc_c, wrap, keyset, ik2,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc,
                 compose, invert_apply)

# ============================================================== rig
# Canvas 56×44, origin at the centre, seen from above, +x forward, +y down
# (the "d" side; "u" is -y).
RIG = Rig()
B = RIG.bones
bone = RIG.bone

THORAX = (2.0, 0.0)
bone("thorax", None, THORAX, 0.0)
# The head on a short neck, and the jaws hinged at its front corners.
bone("head", "thorax", (5.4, 0.0), 0.0, 4.6)
JAW_HINGE = (10.0, 2.3)
JAW_REST = 12.0  # outward from straight ahead
JAW_LEN = 11.0
bone("jaw_u", "head", (JAW_HINGE[0], -JAW_HINGE[1]), -JAW_REST, JAW_LEN)
bone("jaw_d", "head", JAW_HINGE, JAW_REST, JAW_LEN)
# The abdomen: three segments back from the waist, each hanging off the last.
ABD = [(-0.6, 6.4), (None, 6.6), (None, 4.6)]
RIG.chain("abd", "thorax", (-0.6, 0.0), [(6.4, 180.0), (6.6, 180.0), (4.6, 180.0)])

# The legs: hips on the thorax, a femur and a tibia to a foot on the ground,
# and a short claw. Rest foot positions for the "d" side; "u" is the mirror.
LEGS = {  # name: (hip, rest foot, femur, tibia)
    "f": ((4.4, 3.0), (10.6, 9.6), 5.6, 6.2),
    "m": ((2.2, 3.8), (2.8, 12.6), 5.4, 6.4),
    "b": ((0.0, 3.8), (-7.2, 13.0), 6.2, 7.6),
}
SIDES = {"u": -1, "d": 1}
def leg_names():
    for n in ("b", "m", "f"):
        for s in ("u", "d"):
            yield f"{n}_{s}", n, s
def hip_of(n, s): return (LEGS[n][0][0], LEGS[n][0][1] * SIDES[s])
def foot_of(n, s): return (LEGS[n][1][0], LEGS[n][1][1] * SIDES[s])

def bend_of(n, s):
    """The knee bows away from the midline: whichever IK solution puts it further out."""
    hip, foot = hip_of(n, s), foot_of(n, s)
    lf, lt = LEGS[n][2], LEGS[n][3]
    best = None
    for b in (1, -1):
        hf, _ = ik2(hip, foot, lf, lt, b)
        ky = hip[1] + lf * math.sin(R(hf))
        if best is None or abs(ky) > best[0]: best = (abs(ky), b)
    return best[1]
BEND = {f"{n}_{s}": bend_of(n, s) for _, n, s in leg_names()}

for leg, n, s in leg_names():
    hip, foot = hip_of(n, s), foot_of(n, s)
    lf, lt = LEGS[n][2], LEGS[n][3]
    hf, ht = ik2(hip, foot, lf, lt, BEND[leg])
    bone(f"{leg}_femur", "thorax", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", B[f"{leg}_femur"].end(), ht, lt)
    bone(f"{leg}_claw", f"{leg}_tibia", B[f"{leg}_tibia"].end(), ht + 28.0 * SIDES[s] * (1 if n != "f" else -1), 1.8)

RIG.seal()
solve = RIG.solve
on_bone = RIG.on_bone
put = RIG.put

# ============================================================== parts
# Values: pale timber for the body (the light), timber for the bands and the
# head (the middle), and dark timber / rust for the legs, the bristles and the
# joints (the dark). Bone jaws and ember tips are the accents. The masses —
# segments, thorax, head — take the thin outline; everything narrower than
# three units takes the hairline.
LEG_FEMUR, LEG_TIBIA, LEG_CLAW, LEG_KNEE = "$timber.dark", "$timber.dark", "$rust", "$timber"
BODY, BODY_LIGHT, BAND, HEAD = "$timber.light2", "$husk", "$timber", "$timber"

# ---- the buried drawing, hidden on the base (every part at opacity 0; the
# `buried` state turns them up and takes the body away). Drawn first: it is
# the floor.
def hidden(p): p["opacity"] = 0; return p
RIPPLE_R = 10.0
for k in ("b", "a"):
    hidden(put(f"ripple_{k}_trough", "thorax", (0.4, 0.5), 0, {"kind": "ring", "r": RIPPLE_R, "width": 1.5}, "$sand.dark"))
    hidden(put(f"ripple_{k}", "thorax", (0.0, 0.0), 0, {"kind": "ring", "r": RIPPLE_R, "width": 1.3}, "$sand.light2"))
hidden(put("mound_shade", "thorax", (1.0, 1.1), 0, ell(9.6, 8.0), "$sand.dark"))
hidden(put("mound", "thorax", (0.0, 0.0), 0, ell(9.2, 7.6), "$sand.light"))
hidden(put("mound_lit", "thorax", (-1.8, -1.9), -14, ell(5.6, 3.6), "$sand.light2"))
GRAINS = [(-5.6, -3.4), (5.8, -2.6), (-3.0, 4.8), (4.2, 4.4)]
for i, (gx, gy) in enumerate(GRAINS):
    hidden(put(f"grain_{i}", "thorax", (gx, gy), 0, circ(0.8 if i % 2 else 0.65), "$sand.light2"))
hidden(put("pit", "thorax", (2.2, 0.0), 0, ell(3.4, 2.8), "$sand.dark2"))
# The two sickle tips standing up out of the pit, hinged in it.
SAND_JAW = poly([(-0.6, -0.9), (1.6, -1.2), (3.6, -1.0), (5.2, -0.1), (5.9, 1.4), (4.6, 0.6), (3.0, 0.4), (1.2, 0.8), (-0.6, 0.9)])
SAND_TIP = poly([(3.3, -1.0), (4.6, -0.7), (5.4, 0.0), (6.2, 1.9), (4.8, 0.7), (3.4, 0.35)])
for s, sg in (("u", -1), ("d", 1)):
    at = (1.8, 1.0 * sg)
    hidden(put(f"sand_jaw_{s}", "thorax", at, -34 * sg, {**SAND_JAW, "points": [[x, y * -sg] for x, y in SAND_JAW["points"]]}, "$husk", INK_HAIR))
    hidden(put(f"sand_tip_{s}", "thorax", at, -34 * sg, {**SAND_TIP, "points": [[x, y * -sg] for x, y in SAND_TIP["points"]]}, "$ember"))

# ---- legs, under everything: claw, tibia, femur, and a knee over the joint
for leg, n, s in leg_names():
    at, a = on_bone(f"{leg}_claw"); put(f"leg_{leg}_claw", f"{leg}_claw", at, a, bar(1.8, 1.0, 0.5, 0.4), LEG_CLAW, INK_HAIR)
    at, a = on_bone(f"{leg}_tibia"); put(f"leg_{leg}_tibia", f"{leg}_tibia", at, a, bar(LEGS[n][3], 1.9, 1.2), LEG_TIBIA, INK_HAIR)
    at, a = on_bone(f"{leg}_femur"); put(f"leg_{leg}_femur", f"{leg}_femur", at, a, bar(LEGS[n][2], 2.4, 2.0), LEG_FEMUR, INK_HAIR)
    at, a = on_bone(f"{leg}_tibia"); put(f"leg_{leg}_knee", f"{leg}_tibia", at, 0.0, circ(1.15), LEG_KNEE)

# ---- the abdomen, rear segment first (a front segment laps over the one
# behind it). Each segment: a bristle fringe along both flanks under it, the
# plate, a band across its front, and paired dark spots down the back.
SEGS = [  # bone, centre along the bone, rx, ry
    ("abd_2", 1.6, 4.8, 6.4),
    ("abd_1", 3.0, 6.0, 9.2),
    ("abd_0", 3.2, 5.6, 8.4),
]
def fringe(rx, ry, sg, n=4, out=2.0, back=1.6):
    """Tufts of bristle along one flank of a segment, about its centre: a comb of spikes swept back."""
    pts = []
    for i in range(n + 1):
        u = -0.75 + 1.5 * i / n  # along the segment, -1 back .. 1 front
        pts.append((u * rx, sg * ry * math.sqrt(max(0.0, 1 - u * u)) * 0.9))
        if i < n:
            um = u + 0.75 / n
            pts.append((um * rx - back, sg * (ry * math.sqrt(max(0.0, 1 - um * um)) * 0.9 + out)))
    inner = [(x, y * 0.5) for x, y in reversed(pts[::2])]
    return poly(pts + inner)
for bn, c, rx, ry in SEGS:
    at, _ = on_bone(bn, c)
    for s in ("u", "d"):
        put(f"{bn}_fringe_{s}", bn, at, 0.0, fringe(rx, ry, SIDES[s]), "$timber.dark2")
for bn, c, rx, ry in SEGS:
    at, a = on_bone(bn, c)
    put(bn, bn, at, 0.0, ell(rx, ry), BODY, INK_THIN)
    band_at, _ = on_bone(bn, c - rx * 0.45)
    put(f"{bn}_band", bn, band_at, 0.0, ell(1.3, ry * 0.86), BAND)
    for s in ("u", "d"):
        sp, _ = on_bone(bn, c + 0.4, SIDES[s] * ry * 0.34)
        put(f"{bn}_spot_{s}", bn, sp, 0.0, ell(1.3, 0.9), "$rust")
at, _ = on_bone("abd_1", 3.2, -3.6)
put("abd_gloss", "abd_1", at, -8.0, ell(3.6, 1.6), "$white@soft")
at, _ = on_bone("abd_0", 2.8, -3.4)
put("abd_gloss_front", "abd_0", at, -6.0, ell(2.4, 1.1), "$white@soft")
# The hive's organ on the back, where every body in the hive wears it.
at, _ = on_bone("abd_1", 3.0)
RIG.use("organ", "abd_1", at, "ss.lib.organ", scale=[0.62, 0.56])

# ---- the thorax: a pale shield with a dark saddle
put("thorax", "thorax", (2.6, 0.0), 0.0, ell(4.4, 5.2), BODY, INK_THIN)
put("saddle", "thorax", (2.2, 0.0), 0.0, poly([(0.6, -2.6), (2.2, -1.2), (2.2, 1.2), (0.6, 2.6), (-1.4, 1.6), (-1.0, 0), (-1.4, -1.6)]), BAND)
put("thorax_gloss", "thorax", (1.6, -2.8), -10.0, ell(1.8, 0.8), "$white@soft")

# ---- the jaws, under the head: a long sickle of bone curving in, three teeth
# on the inside edge, the last third lit ember. Drawn for the "d" jaw with +y
# outward; the "u" jaw is its mirror.
SICKLE = [(-1.0, -1.1), (0.0, 1.3), (2.8, 2.1), (5.8, 2.2), (8.4, 1.4), (10.2, -0.3), (11.2, -2.6),
          (10.6, -2.3), (9.2, -1.1), (8.2, -1.9), (7.4, -0.5), (5.6, -0.2), (4.8, -1.5), (4.0, 0.1), (2.0, 0.0), (0.2, -1.2)]
TIP = [(8.4, 1.4), (10.2, -0.3), (11.2, -2.6), (10.6, -2.3), (9.2, -1.1), (8.2, -1.9), (7.8, -0.4), (8.0, 0.8)]
def mirror_y(pts, sg): return [(x, y * sg) for x, y in pts]
for s in ("u", "d"):
    sg = SIDES[s]
    at, a = on_bone(f"jaw_{s}")
    put(f"jaw_{s}", f"jaw_{s}", at, a, poly(mirror_y(SICKLE, sg)), "$husk", INK_HAIR)
    put(f"tip_{s}", f"jaw_{s}", at, a, poly(mirror_y(TIP, sg)), "$ember")

# ---- the head: a broad flat capsule, darker than the body, with the eye
# tubercles standing off its sides
HEAD_PTS = [(-2.8, -2.6), (-0.6, -3.8), (2.6, -3.9), (4.6, -2.9), (5.2, 0.0), (4.6, 2.9), (2.6, 3.9), (-0.6, 3.8), (-2.8, 2.6)]
put("head", "head", (6.4, 0.0), 0.0, poly(HEAD_PTS), HEAD, INK_THIN)
put("head_mark", "head", (7.4, 0.0), 0.0, poly([(-2.2, 0), (0.2, -1.6), (2.6, -0.8), (2.6, 0.8), (0.2, 1.6)]), "$timber.dark")
put("head_gloss", "head", (6.2, -2.4), -8.0, ell(1.8, 0.6), "$white@soft")
for s in ("u", "d"):
    sg = SIDES[s]
    put(f"tubercle_{s}", "head", (8.4, 3.9 * sg), 0.0, ell(1.5, 1.2), "$timber.dark", INK_HAIR)
    put(f"eye_{s}", "head", (8.6, 4.1 * sg), 0.0, circ(0.8), "$ink")

RIG.check()
PARTS = RIG.parts
BUR_ONLY = ["ripple_b_trough", "ripple_b", "ripple_a_trough", "ripple_a", "mound_shade", "mound", "mound_lit",
            *[f"grain_{i}" for i in range(len(GRAINS))], "pit", "sand_jaw_u", "sand_tip_u", "sand_jaw_d", "sand_tip_d"]
BODY_PARTS = [p["id"] for p in PARTS if p["id"] not in BUR_ONLY]

# ============================================================== motion
def tracks(pose_at, ts, extra=None, still=(), skip=()):
    """Rig.tracks, leaving out the parts named in `skip` (the buried drawing rides no gait)."""
    out = RIG.tracks(pose_at, ts, extra, still)
    return [t for t in out if t["part"] not in skip or t["prop"] not in ("x", "y", "rot")]

ROUND = tuple(p["id"] for p in PARTS if p["shape"].get("kind") in ("circle", "ring")) if False else ()
STILL = tuple(pid for pid in [p["id"] for p in PARTS] if pid.endswith("_knee") or pid.startswith("eye_"))

def plant(pose, feet):
    """Solve each leg's femur and tibia to put its foot at `feet[leg]`, against the body as posed."""
    world = solve(pose)
    for leg, n, s in leg_names():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik2((hx, hy), feet[leg], LEGS[n][2], LEGS[n][3], BEND[leg])
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_claw"] = ht + (B[f"{leg}_claw"].heading - B[f"{leg}_tibia"].heading) + pose.get("claw", 0.0) * SIDES[s]
    return pose

# Tripods: front and back of one side with the middle of the other.
TRIPOD = {"f_u": 0.0, "b_u": 0.0, "m_d": 0.0, "f_d": 0.5, "b_d": 0.5, "m_u": 0.5}
def step(t, ph, stride, tuck, duty=0.6):
    """Foot offset along x and toward the body for a leg at phase `ph`: planted and pushed back, then carried forward."""
    u = (t + ph) % 1.0
    if u < duty:
        return lerp(stride, -stride, u / duty), 0.0
    v = (u - duty) / (1 - duty)
    return lerp(-stride, stride, smooth(0.0, 1.0, v)), tuck * math.sin(math.pi * v)

def gait(t, stride=3.6, tuck=1.8, sway=1.0, yaw=5.0, surge=0.8, wag=9.0, jaw=1.0):
    # The thorax yaws toward the side that is pushing and slides over the
    # tripod on the ground, surging on each push (twice a loop).
    push = cyc(t, 0.0)
    pose = {"body": (surge * cyc(2 * t, 0.15), sway * cyc(t, 0.25), yaw * push)}
    # The abdomen swings after it as a wave: each segment the same turn a
    # little later, the heavy rear last and furthest.
    for i in range(3):
        pose[f"abd_{i}"] = -wag * (0.55 + 0.25 * i) * cyc(t, -0.14 * (i + 1))
    # The head counter-turns to keep the jaws on the line it is walking.
    pose["head"] = -0.7 * yaw * cyc(t, -0.05)
    # The jaws work: wide on the push of each tripod, snapped shut between.
    open_ = jaw * (10.0 + 12.0 * max(0.0, cyc(2 * t, 0.1)) ** 0.7 - 6.0 * max(0.0, -cyc(2 * t, 0.1)))
    pose["jaw_u"] = -open_
    pose["jaw_d"] = open_
    feet = {}
    for leg, n, s in leg_names():
        dx, tk = step(t, TRIPOD[leg], stride * (0.85 if n == "m" else 1.0), tuck)
        fx, fy = foot_of(n, s)
        feet[leg] = (fx + dx, fy - SIDES[s] * tk)
    return plant(pose, feet)

# ---- crawl: the walk, and what it does once it is up (0.6s)
def crawl_pose(t): return gait(t)

# ---- creep: under the sand (1.1s). The body under the mound crawls low and
# slow; the `buried` state takes the body off and leaves what that does to the
# sand: the mound heaving forward on each push, two rings of ripple running out
# from under it, grains rolling off its shoulders, and the lit tips of the jaws
# working in the pit.
def creep_pose(t): return gait(t, stride=2.6, tuck=1.2, sway=0.7, yaw=3.5, surge=0.6, wag=6.0, jaw=0.7)

def ring_phase(t, off):
    return (t + off) % 1.0
RING_S0, RING_S1 = 0.62, 1.62
def ring_scale(t, off):
    u = ring_phase(t, off)
    return lerp(RING_S0, RING_S1, u ** 0.85)
def ring_alpha(t, off):
    u = ring_phase(t, off)
    return smooth(0.0, 0.12, u) * (1 - smooth(0.62, 0.96, u))
def creep_ts():
    # Even keys, plus a pair either side of each ring's wrap so the reset
    # happens while the ring is out, not across a whole key.
    ts = set(r2(i / 22) for i in range(23))
    for off in (0.0, 0.5):
        w = (1.0 - off) % 1.0
        for d in (-0.01, 0.0):
            v = r2(w + d)
            if 0.0 <= v <= 1.0: ts.add(v)
    return sorted(ts)
def ring_track(pid, prop, off, fn, ts):
    keys = []
    for t in ts:
        w = (1.0 - off) % 1.0
        # at the wrap instant the ring is reborn small; just before it, out and gone
        u_t = t if abs(t - w) > 1e-6 else t + 1e-4
        keys.append([r2(t), r2(fn(u_t, off))])
    # the first and last keys agree (a loop)
    keys[-1][1] = keys[0][1]
    return {"part": pid, "prop": prop, "keys": keys, "ease": "linear"}
def creep_extra_tracks(ts):
    out = []
    for k, off in (("a", 0.0), ("b", 0.5)):
        for pid in (f"ripple_{k}_trough", f"ripple_{k}"):
            out.append(ring_track(pid, "scale", off, ring_scale, ts))
            out.append(ring_track(pid, "opacity", off, ring_alpha, ts))
    return out
def heave(t):
    """The mound's push: twice a loop, forward and up (bigger), with the fall after."""
    return max(0.0, cyc(2 * t, 0.1)) ** 1.5
def creep_extra(ts):
    ex = []
    ex.append(("mound", "scale", lambda t: 1.0 + 0.07 * heave(t)))
    ex.append(("mound_shade", "scale", lambda t: 1.0 + 0.08 * heave(t)))
    ex.append(("mound_lit", "scale", lambda t: 1.0 + 0.1 * heave(t)))
    ex.append(("pit", "scale", lambda t: 1.0 + 0.18 * heave(t)))
    return ex
def grain_xy(i, t):
    """A grain rolling down off the mound's shoulder, once a loop at its own time; back up under the sand unseen."""
    gx, gy = GRAINS[i]
    u = (t + 0.25 * i) % 1.0
    d = math.hypot(gx, gy)
    ox, oy = gx / d, gy / d
    k = 5.0 * smooth(0.0, 0.7, u)
    return ox * k, oy * k, (smooth(0.0, 0.1, u) * (1 - smooth(0.6, 0.8, u)))
def creep_sand_tracks(ts):
    out = []
    mx = lambda t: 1.6 * heave(t) - 0.4
    for pid in ("mound", "mound_shade", "mound_lit", "pit"):
        out.append({"part": pid, "prop": "x", "keys": [[r2(t), r2(mx(t) * (1.4 if pid == "pit" else 1.0))] for t in ts], "ease": "linear"})
    for i in range(len(GRAINS)):
        for j, prop in enumerate(("x", "y", "opacity")):
            ks = [[r2(t), r2(grain_xy(i, t)[j])] for t in ts]
            ks[-1][1] = ks[0][1]
            out.append({"part": f"grain_{i}", "prop": prop, "keys": ks, "ease": "linear"})
    # The tips: scissoring in the pit, rising with the heave.
    for s, sg in (("u", -1), ("d", 1)):
        ang = lambda t, sg=sg: sg * (14.0 * cyc(2 * t, 0.1) - 6.0 * heave(t))
        for pid in (f"sand_jaw_{s}", f"sand_tip_{s}"):
            out.append({"part": pid, "prop": "rot", "keys": [[r2(t), r2(ang(t))] for t in ts], "ease": "linear"})
            out.append({"part": pid, "prop": "x", "keys": [[r2(t), r2(mx(t) * 1.4 + 0.8 * heave(t))] for t in ts], "ease": "linear"})
    return out

# ---- death: 0.46s. The jaws gape (anticipation), snap shut on nothing so hard
# they cross, and fall slack open; the body rears back and then settles flat,
# the abdomen curls to one side and deflates, the legs curl in under it, the
# lit tips go dark and the organ goes out. Still from 0.85.
def death_pose(t):
    gape = smooth(0.0, 0.16, t)
    snap = smooth(0.16, 0.26, t)
    slack = smooth(0.34, 0.8, t)
    rear = math.sin(math.pi * smooth(0.0, 0.34, t))
    fall = smooth(0.3, 0.82, t)
    pose = {"body": (-1.4 * rear + 0.6 * fall, 0.0, -4.0 * rear + 8.0 * fall)}
    jaw = 26.0 * gape - 40.0 * snap + 44.0 * slack
    pose["jaw_u"] = -jaw
    pose["jaw_d"] = jaw
    pose["head"] = 6.0 * rear - 4.0 * fall
    for i in range(3):
        pose[f"abd_{i}"] = -(10.0 + 5.0 * i) * fall + 4.0 * rear
    pose["claw"] = -40.0 * fall
    feet = {}
    for leg, n, s in leg_names():
        hx, hy = hip_of(n, s)
        fx, fy = foot_of(n, s)
        k = lerp(1.0, 0.45, fall)
        kick = 1.6 * math.sin(math.pi * smooth(0.05, 0.4, t)) * (1 if TRIPOD[leg] == 0 else -1)
        feet[leg] = (hx + (fx - hx) * k + kick, hy + (fy - hy) * k)
    return plant(pose, feet)

ts_loop = keyset(12)
animations = {}
animations["crawl"] = {
    "description": "The walk once it is up: six legs in two tripods, each foot planted and pushed back while the body slides over it, then carried forward tucked in; the thorax surges on every push and yaws toward the pushing side, the three-segment abdomen swinging after it as a wave so the heavy rear arrives last; the head counter-turns to hold the line and the jaws gape on each push and snap shut between.",
    "duration": 0.6,
    "tracks": tracks(crawl_pose, ts_loop, [("organ", "scale", lambda t: 1.0 + 0.08 * max(0.0, cyc(2 * t, 0.3)))], STILL),
}
TS_CREEP = creep_ts()
animations["creep"] = {
    "description": "Under the sand, which is what the `buried` states play: the mound heaves forward on each push of the thing under it and falls back, two rings of ripple — a lit crest over a dark trough — run out from under it one after the other and die away, grains roll off its shoulders, and the two lit jaw tips scissor in the pit. On the base drawing (never shown buried) it is the same crawl, low and slow.",
    "duration": 1.1,
    "tracks": tracks(creep_pose, TS_CREEP, creep_extra(TS_CREEP), STILL, skip=BUR_ONLY)
    + creep_extra_tracks(TS_CREEP) + creep_sand_tracks(TS_CREEP),
}
TS_DEATH = [0, 0.04, 0.08, 0.12, 0.16, 0.19, 0.22, 0.26, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
def fade(a, b, lo=0.0): return lambda t: 1.0 - (1.0 - lo) * smooth(a, b, t)
def deflate(t): return 1.0 - 0.1 * smooth(0.3, 0.82, t)
animations["death"] = {
    "description": "The jaws gape and snap shut once on nothing so hard they cross, then fall slack open; the body rears back and settles flat and askew, the abdomen curling to one side and deflating, the legs drawing in under it with their claws folded; the lit tips go dark and the organ goes out. Still from 0.85.",
    "duration": 0.46,
    "tracks": tracks(death_pose, TS_DEATH,
                     [("tip_u", "opacity", fade(0.3, 0.8, 0.15)), ("tip_d", "opacity", fade(0.3, 0.8, 0.15)),
                      ("organ", "opacity", fade(0.2, 0.8, 0.12))]
                     + [(bn, "scale", deflate) for bn in ("abd_0", "abd_1", "abd_2")], STILL),
}

# ============================================================== states
BURIED_SET = {
    **{f"{pid}.opacity": 1 for pid in BUR_ONLY},
}
variants = {
    "elite": {
        "description": "Marked by the hive: the shell bleached to bone with the bands gone pale, bone jaws, a brighter, bigger organ and hotter tips.",
        "scale": 1.25,
        "set": {
            **{f"{bn}.fill": "$husk" for bn, *_ in SEGS},
            **{f"{bn}_band.fill": "$husk.dark" for bn, *_ in SEGS},
            **{f"{bn}_spot_{s}.fill": "$timber.dark" for bn, *_ in SEGS for s in ("u", "d")},
            "thorax.fill": "$husk",
            "saddle.fill": "$husk.dark",
            "head.fill": "$timber.light",
            "jaw_u.fill": "$bone.light",
            "jaw_d.fill": "$bone.light",
            "tip_u.fill": "$ember.light",
            "tip_d.fill": "$ember.light",
            "organ.scale": [0.8, 0.72],
        },
    },
    "buried": {
        "description": "Under the sand: the body is gone and what is left is a mound of paler sand with a dark pit in it, the two lit jaw tips working up out of the pit and rings of ripple — a lit crest over a dark trough — running out from under it. The state the game spawns it in (EnemyType.ambush); it plays `creep`.",
        "remove": BODY_PARTS,
        "set": BURIED_SET,
        "animations": ["creep"],
    },
    "elite_buried": {
        "description": "The marked body under the sand — the elite patch and the buried patch written out together, because a variant patches the base and two of them cannot be stacked. A paler, bleached mound and hotter tips.",
        "scale": 1.25,
        "remove": BODY_PARTS,
        "set": {
            **BURIED_SET,
            "mound.fill": "$husk.dark",
            "mound_lit.fill": "$husk",
            "sand_jaw_u.fill": "$bone.light",
            "sand_jaw_d.fill": "$bone.light",
            "sand_tip_u.fill": "$ember.light",
            "sand_tip_d.fill": "$ember.light",
        },
        "animations": ["creep"],
    },
}

DESCRIPTION = (
    "The pan's heavy wave body, and the one that hides. An antlion larva seen from above, facing +x and mirrored by the game: a fat "
    "pale-timber sack of three segments banded and spotted in rust, fringed with dark bristle along both flanks, on a small thorax and "
    "six legs; a flat dark head with the eyes on tubercles at its sides, and in front of it almost all jaw — two long bone sickles "
    "curving in on each other, toothed on the inside, the last third of each lit ember, because the tips are the only part of it that "
    "shows when it is under. Which it usually is: the game spawns it in the `buried` state (EnemyType.ambush) and swaps to this drawing "
    "when it comes up. `buried` takes the body off and leaves a mound of pale sand with a dark pit, the two lit tips working up out of "
    "it and rings of ripple running out from under it, playing `creep`; `elite_buried` is the elite patch and the buried patch in one, "
    "because a variant is a patch on the base and the game cannot stack two. Built on a skeleton (scripts/antlion.py): the legs are "
    "solved to planted feet, the abdomen is a chain that swings after the body, and each jaw is hinged at the head. Gameplay radius 11. "
    "The `death` clip snaps the jaws once on nothing and lets them fall open; a body killed while buried comes up to play it."
)

doc = {
    "id": "ss.enemy.antlion",
    "name": "Antlion",
    "description": DESCRIPTION,
    "tags": ["enemy", "antlion"],
    "size": [56, 44],
    "meta": {"radius": 11},
    "parts": PARTS,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-antlion.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(PARTS)} parts, {len(animations)} clips, {n_tracks} tracks")
