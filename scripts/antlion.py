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
  - six short legs, each a femur and a tibia solved every frame to a foot on
    the ground (two-bone IK), knees bowed out, so a planted foot stays planted
    while the body slides over it
  - pale timber, so on the pan's mid-brown sand it is a light thing on a dark
    floor instead of the floor itself; timber bands and a timber head for the
    middle value, dark legs and rust spots for the dark, and two long bone
    sickles with ember tips — the silhouette is mostly jaw

The buried state is the same document with the body taken off: a mound of
pale sand with a dark pit in it, the two ember tips scissoring up out of the
pit, and two rings round the mound breathing against each other — the inner
one swelling and fading while the outer one draws in and brightens.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, cyc_c, wrap, keyset, ik2,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 60×48, origin at the centre, seen from above, +x forward, +y down
# (the "d" side; "u" is its mirror at -y).
W, H = 60, 48
RIG = Rig()
B = RIG.bones
bone = RIG.bone
SIDES = {"u": -1, "d": 1}

bone("thorax", None, (0.0, 0.0), 0.0)
# The head on a short neck, and the jaws hinged at its front corners.
bone("head", "thorax", (3.6, 0.0), 0.0, 5.0)
JAW_HINGE = (10.4, 3.0)
JAW_REST = 22.0  # outward from straight ahead, so the sickles curve back in
JAW_LEN = 13.0
for s, sg in SIDES.items():
    bone(f"jaw_{s}", "head", (JAW_HINGE[0], JAW_HINGE[1] * sg), JAW_REST * sg, JAW_LEN)
# The abdomen: three segments back from the waist, each hanging off the last.
ABD_LINKS = [(5.2, 180.0), (6.4, 180.0), (5.4, 180.0)]
RIG.chain("abd", "thorax", (-2.6, 0.0), ABD_LINKS)

# The legs: hips on the thorax, a femur and a tibia to a foot on the ground,
# and a short claw. Rest foot positions for the "d" side; "u" is the mirror.
LEGS = {  # name: (hip, rest foot, femur, tibia)
    "f": ((2.6, 2.8), (7.8, 9.2), 5.2, 6.4),
    "m": ((0.6, 3.6), (1.4, 11.6), 5.0, 6.4),
    "b": ((-1.4, 3.4), (-6.6, 10.6), 5.4, 6.8),
}
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

CLAW_TURN = {"f": 24.0, "m": 10.0, "b": -18.0}  # the tarsal claw hooks forward on the front legs, back on the rear
for leg, n, s in leg_names():
    hip, foot = hip_of(n, s), foot_of(n, s)
    lf, lt = LEGS[n][2], LEGS[n][3]
    hf, ht = ik2(hip, foot, lf, lt, BEND[leg])
    bone(f"{leg}_femur", "thorax", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", B[f"{leg}_femur"].end(), ht, lt)
    bone(f"{leg}_claw", f"{leg}_tibia", B[f"{leg}_tibia"].end(), ht - CLAW_TURN[n] * SIDES[s], 1.8)

RIG.seal()
solve = RIG.solve
on_bone = RIG.on_bone
put = RIG.put

# ============================================================== parts
# Three values. Light: the abdomen and thorax — pale timber flanks under a
# bleached husk back. Middle: timber bands and the head. Dark: the legs, the
# spots and the bristle. Accents: bone jaws with ember tips, and the organ.
# Only the sack and the head take the thin outline; the thorax, the jaws and
# everything narrower take the hairline (bone on the sand needs no more, and
# every unit of ink is a unit of the body sunk into the floor).
BODY, PALE, BAND, HEAD, HEAD_MARK = "$timber.light2", "$husk", "$husk.dark", "$timber.light2", "$timber.light"
LEG_FEMUR, LEG_TIBIA, LEG_CLAW, LEG_KNEE = "$timber.light", "$timber.light", "$rust.light", "$timber.light2"
BRISTLE = "$timber.light"
# The body's own outline is its darkest timber rather than ink: on the pan's
# mid-brown sand an ink rim round every leg and segment is most of what a
# 50px body's mean comes to, and it pulls the whole larva down to the floor's
# tone. The jaws and the head keep ink — they are the read.
RIM = {"color": "$timber.dark2", "width": "hair"}

# ---- the buried drawing, hidden on the base (every part at opacity 0; the
# `buried` state turns them up and takes the body away). Drawn first: it is
# the floor.
def hidden(p): p["opacity"] = 0; return p
MOUND = (0.0, 0.0)
# Two rings round the mound, the outer one under: they breathe against each
# other in `creep` (see RIPPLE_KEYS).
hidden(put("ripple_b", "thorax", (0.0, 0.0), 0, {"kind": "ring", "r": 15.0, "width": 1.4}, "$sand.light@soft"))
hidden(put("ripple_a", "thorax", (0.0, 0.0), 0, {"kind": "ring", "r": 10.0, "width": 1.6}, "$sand.light@heavy"))
hidden(put("mound_shade", "thorax", (0.9, 1.1), 0, ell(10.0, 8.2), "$sand.dark"))
hidden(put("mound", "thorax", MOUND, 0, ell(9.6, 7.8), "$sand.light"))
hidden(put("mound_lit", "thorax", (-2.0, -2.2), -14, ell(5.8, 3.6), "$sand.light2"))
GRAINS = [(-6.2, -3.4), (6.0, -3.2), (-3.4, 5.4), (4.6, 4.8)]
for i, (gx, gy) in enumerate(GRAINS):
    hidden(put(f"grain_{i}", "thorax", (gx, gy), 0, circ(0.85 if i % 2 else 0.7), "$sand.light2"))
hidden(put("pit", "thorax", (2.4, 0.0), 0, ell(3.6, 3.0), "$sand.dark2"))
# The two tips standing up out of the pit: the last third of each sickle, hooked
# in toward the other, hinged in the pit. Drawn for "d" (+y outward) and mirrored.
SAND_JAW = [(-0.4, -0.9), (1.8, 1.0), (3.8, 1.5), (5.6, 0.9), (6.8, -0.6), (7.2, -2.4), (6.2, -1.4), (4.8, -0.6), (3.0, -0.4), (1.4, -1.1)]
SAND_TIP = [(4.4, 1.25), (5.6, 0.9), (6.8, -0.6), (7.2, -2.4), (6.2, -1.4), (5.0, -0.5), (4.2, -0.1)]
def mirror_y(pts, sg): return [(x, y * sg) for x, y in pts]
SAND_HINGE = (1.8, 1.2)
SAND_OUT = 38.0
for s, sg in SIDES.items():
    at = (SAND_HINGE[0], SAND_HINGE[1] * sg)
    hidden(put(f"sand_jaw_{s}", "thorax", at, SAND_OUT * sg, poly(mirror_y(SAND_JAW, sg)), "$bone.light", INK_HAIR))
    hidden(put(f"sand_tip_{s}", "thorax", at, SAND_OUT * sg, poly(mirror_y(SAND_TIP, sg)), "$ember"))

# ---- legs, under everything: claw, tibia, femur, and a knee over the joint
for leg, n, s in leg_names():
    at, a = on_bone(f"{leg}_claw"); put(f"leg_{leg}_claw", f"{leg}_claw", at, a, bar(1.8, 1.1, 0.5, 0.4), LEG_CLAW, RIM)
    at, a = on_bone(f"{leg}_tibia"); put(f"leg_{leg}_tibia", f"{leg}_tibia", at, a, bar(LEGS[n][3], 2.0, 1.3), LEG_TIBIA, RIM)
    at, a = on_bone(f"{leg}_femur"); put(f"leg_{leg}_femur", f"{leg}_femur", at, a, bar(LEGS[n][2], 2.6, 2.1), LEG_FEMUR, RIM)
    at, a = on_bone(f"{leg}_tibia"); put(f"leg_{leg}_knee", f"{leg}_tibia", at, 0.0, circ(1.2), LEG_KNEE)

# ---- the abdomen, rear segment first (a front segment laps over the one
# behind it). Each segment: a bristle comb along both flanks under it, the
# plate, a band across its back edge, and paired dark spots down the back.
SEGS = [  # bone, centre along the bone, rx, ry
    ("abd_2", 2.8, 6.0, 7.2),
    ("abd_1", 3.2, 7.2, 9.4),
    ("abd_0", 2.2, 5.6, 8.0),
]
def comb(rx, ry, sg, n=4, out=1.6, back=1.4):
    """Bristle along one flank of a segment, about its centre: a comb of short spikes swept back."""
    pts = []
    for i in range(n + 1):
        u = -0.7 + 1.4 * i / n  # along the segment, -1 back .. 1 front
        pts.append((u * rx, sg * ry * math.sqrt(max(0.0, 1 - u * u)) * 0.92))
        if i < n:
            um = u + 0.7 / n
            pts.append((um * rx - back, sg * (ry * math.sqrt(max(0.0, 1 - um * um)) * 0.92 + out)))
    inner = [(x, y * 0.6) for x, y in reversed(pts[::2])]
    return poly(pts + inner)
for bn, c, rx, ry in SEGS:
    at, _ = on_bone(bn, c)
    for s in ("u", "d"):
        put(f"{bn}_comb_{s}", bn, at, 0.0, comb(rx, ry, SIDES[s]), BRISTLE)
SPOT = {"abd_0": 0.34, "abd_1": 0.36, "abd_2": 0.3}
# Two passes: every segment's outline first, then every segment's fill over
# them, so the ink shows only round the outside of the sack and the segments
# are told apart by their bands rather than by a black seam each.
for bn, c, rx, ry in SEGS:
    at, a = on_bone(bn, c)
    put(f"{bn}_rim", bn, at, 0.0, ell(rx, ry), BODY, RIM)
for bn, c, rx, ry in SEGS:
    at, a = on_bone(bn, c)
    put(bn, bn, at, 0.0, ell(rx - 0.1, ry - 0.1), BODY)
    # the pale dorsal field: tan flanks, a bleached back
    put(f"{bn}_pale", bn, (at[0] + 0.5, at[1]), 0.0, ell(rx * 0.8, ry * 0.74), PALE)
for bn, c, rx, ry in SEGS:
    # the band sits across the segment's rear edge, a crescent following the curve
    band_at, _ = on_bone(bn, c + rx * 0.62)
    put(f"{bn}_band", bn, band_at, 0.0,
        poly([(-0.2, -ry * 0.78), (0.9, -ry * 0.5), (1.3, 0.0), (0.9, ry * 0.5), (-0.2, ry * 0.78), (-0.7, ry * 0.4), (-0.9, 0.0), (-0.7, -ry * 0.4)]), BAND)
    for s in ("u", "d"):
        sp, _ = on_bone(bn, c - 0.4, SIDES[s] * ry * SPOT[bn])
        put(f"{bn}_spot_{s}", bn, sp, 0.0, ell(1.2, 0.8), "$rust.light")
at, _ = on_bone("abd_1", 2.6, -4.4)
put("abd_gloss", "abd_1", at, -10.0, ell(3.8, 1.5), "$white@soft")
at, _ = on_bone("abd_2", 2.6, -3.4)
put("abd_gloss_rear", "abd_2", at, -14.0, ell(2.4, 1.0), "$white@soft")
# The hive's organ on the back, where every body in the hive wears it.
at, _ = on_bone("abd_1", 3.4)
RIG.use("organ", "abd_1", at, "ss.lib.organ", scale=[0.62, 0.56])

# ---- the thorax: a pale shield with a darker saddle
put("thorax", "thorax", (0.8, 0.0), 0.0, ell(4.2, 4.8), BODY, RIM)
put("thorax_pale", "thorax", (0.6, 0.0), 0.0, ell(3.2, 3.6), PALE)
put("saddle", "thorax", (0.6, 0.0), 0.0, poly([(1.8, -2.2), (2.6, 0.0), (1.8, 2.2), (-1.2, 1.6), (-2.0, 0), (-1.2, -1.6)]), BAND)
put("thorax_gloss", "thorax", (0.0, -2.8), -10.0, ell(1.8, 0.7), "$white@soft")

# ---- the jaws, under the head: a long sickle of bone curving in, three teeth
# on the inside edge, the last third lit ember. Drawn for the "d" jaw with +y
# outward (the bone's rest heading already turns it out; the blade curls back
# in past the midline's line); the "u" jaw is its mirror.
SICKLE = [(-1.2, -1.4), (-0.4, 1.4), (2.4, 2.2), (5.6, 2.3), (8.6, 1.5), (11.2, -0.6), (13.0, -3.4), (13.2, -4.6),
          (12.0, -3.4), (10.6, -2.0), (9.6, -2.6), (8.8, -1.0), (7.0, -0.6), (6.2, -1.9), (5.2, -0.3), (3.0, -0.3), (1.0, -1.2)]
TIP = [(9.4, 1.0), (11.2, -0.6), (13.0, -3.4), (13.2, -4.6), (12.0, -3.4), (10.6, -2.0), (9.6, -2.6), (9.0, -1.0)]
for s in ("u", "d"):
    sg = SIDES[s]
    at, a = on_bone(f"jaw_{s}")
    put(f"jaw_{s}", f"jaw_{s}", at, a, poly(mirror_y(SICKLE, sg)), "$bone.light", INK_HAIR)
    put(f"tip_{s}", f"jaw_{s}", at, a, poly(mirror_y(TIP, sg)), "$ember")
    at, a = on_bone(f"jaw_{s}", 4.0, 0.6 * sg)
    put(f"jaw_{s}_gloss", f"jaw_{s}", at, a, ell(2.6, 0.5), "$white@0.4")

# ---- the head: a broad flat capsule, wider than long, darker than the body,
# with the eye tubercles standing off its front corners
HEAD_PTS = [(-2.6, -2.8), (-0.8, -4.2), (2.2, -4.8), (4.2, -4.2), (5.0, -2.4), (5.2, 0.0), (5.0, 2.4), (4.2, 4.2), (2.2, 4.8), (-0.8, 4.2), (-2.6, 2.8)]
put("head", "head", (6.0, 0.0), 0.0, poly(HEAD_PTS), HEAD, INK_HAIR)
put("head_mark", "head", (6.6, 0.0), 0.0, poly([(-2.4, 0), (0.0, -1.8), (2.8, -1.0), (3.2, 0.0), (2.8, 1.0), (0.0, 1.8)]), HEAD_MARK)
put("head_gloss", "head", (5.2, -2.8), -8.0, ell(1.8, 0.6), "$white@soft")
for s in ("u", "d"):
    sg = SIDES[s]
    put(f"tubercle_{s}", "head", (9.0, 4.3 * sg), 0.0, ell(1.25, 1.0), HEAD, INK_HAIR)
    put(f"eye_{s}", "head", (9.2, 4.45 * sg), 0.0, circ(0.65), "$ink")

RIG.check()
PARTS = RIG.parts
BUR_ONLY = [p["id"] for p in PARTS if p.get("opacity") == 0]
BODY_PARTS = [p["id"] for p in PARTS if p["id"] not in BUR_ONLY]

# ============================================================== motion
STILL = tuple(pid for pid in [p["id"] for p in PARTS] if pid.endswith("_knee") or pid.startswith("eye_"))

def tracks(pose_at, ts, extra=None, skip=()):
    """Rig.tracks, leaving out the parts named in `skip` (the buried drawing rides no gait)."""
    out = RIG.tracks(pose_at, ts, extra, STILL)
    return [t for t in out if t["part"] not in skip or t["prop"] not in ("x", "y", "rot")]

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
def step(t, ph, stride, tuck, duty=0.58):
    """Foot offset along x and toward the body for a leg at phase `ph`: planted and pushed back, then carried forward."""
    u = (t + ph) % 1.0
    if u < duty:
        return lerp(stride, -stride, u / duty), 0.0
    v = (u - duty) / (1 - duty)
    return lerp(-stride, stride, smooth(0.0, 1.0, v)), tuck * math.sin(math.pi * v)

def gait(t, stride=3.8, tuck=2.2, sway=1.8, yaw=9.0, surge=1.4, wag=16.0, jaw=1.0, head=0.5):
    # The thorax yaws toward the side that is pushing and slides over the
    # tripod on the ground, surging on each push (twice a loop).
    push = cyc(t, 0.0)
    pose = {"body": (surge * cyc(2 * t, 0.15), sway * cyc(t, 0.25), yaw * push)}
    # The abdomen swings after it as a wave: each segment the same turn a
    # little later, the heavy rear last and furthest.
    for i in range(3):
        pose[f"abd_{i}"] = -wag * (0.5 + 0.3 * i) * cyc(t, -0.14 * (i + 1))
    # The head counter-turns to keep the jaws on the line it is walking.
    pose["head"] = -head * yaw * cyc(t, -0.05)
    # The jaws work once a stride: drawn open slowly through most of it, then
    # snapped shut — a trap being set and sprung, over and over.
    u = (t + 0.41) % 1.0
    o = smooth(0.0, 0.62, u) * (1 - smooth(0.7, 0.84, u))
    open_ = jaw * (-6.0 + 30.0 * o)
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
# slow — the `buried` state takes the body off and leaves what that does to the
# sand: the mound shoving forward and swelling on each push of the thing under
# it, the two rings round it breathing against each other, grains rolling off
# its shoulders, and the lit
# tips of the jaws scissoring in the pit.
def creep_pose(t): return gait(t, stride=3.0, tuck=1.4, sway=1.0, yaw=5.0, surge=0.8, wag=8.0, jaw=0.8)

# The rings breathe against each other, once a loop: the inner one swells and
# fades while the outer one draws in and brightens, then back. Keyed at the
# ends and the middle and eased, so the loop has no seam.
RIPPLE_KEYS = {
    ("ripple_a", "scale"): [[0.0, 0.8], [0.5, 1.15], [1.0, 0.8]],
    ("ripple_a", "opacity"): [[0.0, 0.5], [0.5, 0.2], [1.0, 0.5]],
    ("ripple_b", "scale"): [[0.0, 1.1], [0.5, 0.85], [1.0, 1.1]],
    ("ripple_b", "opacity"): [[0.0, 0.22], [0.5, 0.5], [1.0, 0.22]],
}
def creep_ts(): return sorted(set(r2(i / 22) for i in range(23)))
def heave(t):
    """The shove from under: twice a loop, a quick swell and a slower fall."""
    return max(0.0, cyc(2 * t, 0.1)) ** 1.3
def mound_dx(t): return 1.8 * heave(t) - 0.5
def creep_sand_tracks(ts):
    out = []
    def T(pid, prop, fn):
        ks = [[r2(t), r2(fn(t))] for t in ts]
        ks[-1][1] = ks[0][1]  # a loop
        out.append({"part": pid, "prop": prop, "keys": ks, "ease": "linear"})
    for (pid, prop), keys in RIPPLE_KEYS.items():
        out.append({"part": pid, "prop": prop, "keys": keys})
    for pid, amp in (("mound", 0.09), ("mound_shade", 0.1), ("mound_lit", 0.12), ("pit", 0.25)):
        T(pid, "scale", lambda t, amp=amp: 1.0 + amp * heave(t))
        T(pid, "x", lambda t, pid=pid: mound_dx(t) * (1.4 if pid == "pit" else 1.0))
    for i in range(len(GRAINS)):
        for j, prop in enumerate(("x", "y", "opacity")):
            ks = [[r2(t), r2(grain_xy(i, t)[j])] for t in ts]
            ks[-1][1] = ks[0][1]
            out.append({"part": f"grain_{i}", "prop": prop, "keys": ks, "ease": "linear"})
    # The tips: scissoring in the pit, thrown up and open with the heave.
    for s, sg in SIDES.items():
        for pid in (f"sand_jaw_{s}", f"sand_tip_{s}"):
            T(pid, "rot", lambda t, sg=sg: sg * (18.0 * cyc(2 * t, 0.02) + 10.0 * heave(t) - 8.0))
            T(pid, "x", lambda t: mound_dx(t) * 1.4 + 1.2 * heave(t))
    return out
def grain_xy(i, t):
    """A grain rolling down off the mound's shoulder, once a loop at its own time."""
    gx, gy = GRAINS[i]
    u = (t + 0.25 * i) % 1.0
    d = math.hypot(gx, gy)
    ox, oy = gx / d, gy / d
    k = 6.0 * smooth(0.0, 0.7, u)
    return ox * k, oy * k, (smooth(0.0, 0.1, u) * (1 - smooth(0.6, 0.8, u)))

# ---- death: 0.46s. Anticipation: the jaws gape as wide as they go and the body
# rears back on its legs. Release: they snap shut on nothing so hard they cross,
# the body pitched forward after them. Recovery: the jaws fall slack open, the
# body settles askew, the abdomen curls to one side and deflates, the legs curl
# in under it; the lit tips go dark and the organ goes out. Still from 0.85.
def death_pose(t):
    gape = smooth(0.0, 0.18, t)
    snap = smooth(0.18, 0.27, t)
    slack = smooth(0.34, 0.8, t)
    rear = math.sin(math.pi * smooth(0.0, 0.36, t))
    lunge = math.sin(math.pi * smooth(0.18, 0.44, t))
    fall = smooth(0.32, 0.82, t)
    pose = {"body": (-1.8 * rear + 2.2 * lunge + 0.6 * fall, 0.0, -5.0 * rear + 12.0 * fall)}
    jaw = 30.0 * gape - 48.0 * snap + 46.0 * slack
    pose["jaw_u"] = -jaw
    pose["jaw_d"] = jaw
    pose["head"] = 6.0 * rear - 8.0 * lunge + 4.0 * fall
    for i in range(3):
        pose[f"abd_{i}"] = -(12.0 + 6.0 * i) * fall + 5.0 * rear
    pose["claw"] = -40.0 * fall
    feet = {}
    for leg, n, s in leg_names():
        hx, hy = hip_of(n, s)
        fx, fy = foot_of(n, s)
        k = lerp(1.0, 0.5, fall)
        kick = 1.8 * math.sin(math.pi * smooth(0.05, 0.42, t)) * (1 if TRIPOD[leg] == 0 else -1)
        feet[leg] = (hx + (fx - hx) * k + kick, hy + (fy - hy) * k)
    return plant(pose, feet)

animations = {}
TS_CRAWL = keyset(12)
animations["crawl"] = {
    "description": "The walk once it is up: six legs in two tripods, each foot planted and pushed back while the body slides over it, then carried forward tucked in; the thorax surges on every push and yaws toward the pushing side, the three-segment abdomen swinging after it as a wave so the heavy rear arrives last; the head counter-turns to hold the line and once a stride the jaws are drawn slowly open and snapped shut.",
    "duration": 0.6,
    "tracks": tracks(crawl_pose, TS_CRAWL, [("organ", "scale", lambda t: 1.0 + 0.08 * max(0.0, cyc(2 * t, 0.3)))]),
}
TS_CREEP = creep_ts()
animations["creep"] = {
    "description": "Under the sand, which is what the `buried` states play: the mound shoves forward and swells on each push of the thing under it and falls back; two rings breathe round it against each other; grains roll off its shoulders and the two lit jaw tips scissor in the pit. On the base drawing (never shown buried) it is the same crawl, low and slow.",
    "duration": 1.1,
    "tracks": tracks(creep_pose, TS_CREEP, skip=BUR_ONLY) + creep_sand_tracks(TS_CREEP),
}
TS_DEATH = [0, 0.04, 0.08, 0.12, 0.15, 0.18, 0.21, 0.24, 0.27, 0.3, 0.34, 0.38, 0.42, 0.46, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
def fade(a, b, lo=0.0): return lambda t: 1.0 - (1.0 - lo) * smooth(a, b, t)
def deflate(t): return 1.0 - 0.12 * smooth(0.3, 0.82, t)
SACK = [f"{bn}{k}" for bn in ("abd_0", "abd_1", "abd_2") for k in ("_rim", "", "_pale")]
animations["death"] = {
    "description": "It rears back with the jaws gaping as wide as they go, then lunges and snaps them shut on nothing so hard they cross; they fall slack open as it settles flat and askew, the abdomen curling to one side and deflating, the legs drawing in under it with their claws folded; the lit tips go dark and the organ goes out. Still from 0.85.",
    "duration": 0.46,
    "tracks": tracks(death_pose, TS_DEATH,
                     [("tip_u", "opacity", fade(0.3, 0.8, 0.15)), ("tip_d", "opacity", fade(0.3, 0.8, 0.15)),
                      ("organ", "opacity", fade(0.2, 0.8, 0.12))]
                     + [(pid, "scale", deflate) for pid in SACK]),
}

# ============================================================== states
BURIED_SET = {f"{pid}.opacity": 1 for pid in BUR_ONLY}
ELITE_SET = {
    **{f"{bn}.fill": "$husk" for bn, *_ in SEGS},
    **{f"{bn}_rim.fill": "$husk" for bn, *_ in SEGS},
    **{f"{bn}_pale.fill": "$husk.light2" for bn, *_ in SEGS},
    "thorax_pale.fill": "$husk.light2",
    "thorax.fill": "$husk",
    **{f"{bn}_band.fill": "$husk.dark" for bn, *_ in SEGS},
    **{f"{bn}_comb_{s}.fill": "$husk.dark" for bn, *_ in SEGS for s in ("u", "d")},
    **{f"{bn}_spot_{s}.fill": "$timber" for bn, *_ in SEGS for s in ("u", "d")},
    "saddle.fill": "$husk.dark",
    "head.fill": "$timber.light",
    "tubercle_u.fill": "$timber.light",
    "tubercle_d.fill": "$timber.light",
    "jaw_u.fill": "$bone.light2",
    "jaw_d.fill": "$bone.light2",
    "tip_u.fill": "$ember.light",
    "tip_d.fill": "$ember.light",
    "organ.scale": [0.8, 0.72],
}
variants = {
    "elite": {
        "description": "Marked by the hive: the shell bleached to husk with the bands and bristle gone pale, whiter jaws, a brighter, bigger organ and hotter tips.",
        "scale": 1.25,
        "set": ELITE_SET,
    },
    "buried": {
        "description": "Under the sand: the body is gone and what is left is a mound of paler sand with a dark pit in it, the two lit jaw tips scissoring up out of the pit, and two rings round it breathing against each other. The state the game spawns it in (EnemyType.ambush); it plays `creep`.",
        "remove": BODY_PARTS,
        "set": BURIED_SET,
        "animations": ["creep"],
    },
    "elite_buried": {
        "description": "The marked body under the sand — the elite patch and the buried patch written out together, because a variant patches the base and two of them cannot be stacked. A bleached mound and hotter tips.",
        "scale": 1.25,
        "remove": BODY_PARTS,
        "set": {
            **BURIED_SET,
            "mound.fill": "$husk.dark",
            "mound_lit.fill": "$husk",
            "sand_jaw_u.fill": "$bone.light2",
            "sand_jaw_d.fill": "$bone.light2",
            "sand_tip_u.fill": "$ember.light",
            "sand_tip_d.fill": "$ember.light",
        },
        "animations": ["creep"],
    },
}

DESCRIPTION = (
    "The pan's heavy wave body, and the one that hides. An antlion larva seen from above, facing +x and mirrored by the game: a fat "
    "pale-timber sack of three segments, banded and spotted, combed with bristle along both flanks, on a small thorax and six short "
    "dark legs; a flat timber head with the eyes on tubercles at its front corners, and in front of it almost all jaw — two long bone "
    "sickles curving in on each other, toothed on the inside, the last third of each lit ember, because the tips are the only part of it "
    "that shows when it is under. Which it usually is: the game spawns it in the `buried` state (EnemyType.ambush) and swaps to this "
    "drawing when it comes up. `buried` takes the body off and leaves a mound of pale sand with a dark pit, the two lit tips scissoring "
    "up out of it and two rings breathing round it, playing `creep`; `elite_buried` is the elite patch and the buried "
    "patch in one, because a variant is a patch on the base and the game cannot stack two. Built on a skeleton (scripts/antlion.py): the "
    "legs are solved to planted feet, the abdomen is a chain that swings after the body, and each jaw is hinged at the head. Gameplay "
    "radius 11. The `death` clip snaps the jaws once on nothing and lets them fall open; a body killed while buried comes up to play it."
)

doc = {
    "id": "ss.enemy.antlion",
    "name": "Antlion",
    "description": DESCRIPTION,
    "tags": ["enemy", "antlion"],
    "size": [W, H],
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
