"""The Porter — the nest's traffic, carrying, and the grub it carries.

    python3 scripts/porter.py        # rewrites apps/ss/assets/ss-enemy-porter.json

The burrow's Rattle slot, and two bodies in one document. The hauler is a low
dark ant with a pale grub slung the whole length of its back, held by the
grub's head end in its jaws; when the hauler dies the game puts the grub down
alive where it fell (feelers: `dropType: 'instar'`), and that Instar is drawn
from this same document — the `grub` variant, which is the load alone, and
the `creep` clip, which is its crawl (`ANIMATED_CLIPS` names it, because the
document's first clip is the hauler's `haul`). So the grub has to be one
drawing that reads riding and reads crawling, and a `death` that reads for
either half on its own.

It was hand-placed and it barely moved: the haul measured 4.5px at game
scale, the crawl 3.6 — the grub's girth pulsing inside a chain of discs whose
overlap swallowed it. And it sank into the dark floor (contrast 2.39). This
rebuilds it:

  - the hauler is a skeleton (scripts/rig.py): a thorax root that bobs and
    pitches, a gaster hanging off the petiole that swings after it, a head on
    the neck, a mandible hinge, two-bone antennae, and six legs solved every
    frame to a foot on the ground (two-bone IK) in two tripods
  - the grub is not on the hauler's bones, because it has to be drawn twice —
    once riding, once crawling on its own — and one set of tracks has to serve
    both. It is six segments placed by a model of its own (its spine), and
    every one of its parts is written as an offset from where it lies. The
    `grub` variant moves every grub part by the same amount, so it is the
    riding drawing exactly, translated onto its own centre; and offsets
    commute with a translation, so every clip the variant plays is the same
    motion there that it is on the hauler's back
  - riding, the grub is a chain held at the head end: the head end follows the
    jaws, and each segment answers the step a beat later and larger than the
    one before it, so the free tail sways last and furthest
  - crawling, it moves the way a larva does: a contraction runs from the tail
    to the head, each segment lifting, fattening and shoving forward as it
    arrives and planting as it leaves, so a hump travels the length of the
    body and the calipers open on the reach

Seen side-on, facing +x; the game flips it. Brood pale over a dark hauler,
and the grub is drawn big because the silhouette is the cargo.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 compose, invert_apply, poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 44×40, origin at the centre, +x forward, +y down.
GROUND = 9.8
RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("body", None, (-1.6, 0.4), 0.0)       # the thorax: the root bobs and pitches about the petiole end
bone("anchor", None, (0.0, 0.0), 0.0)      # a second root that never moves: the grub's parts ride it,
                                           # and their tracks are written from the grub's own model
bone("gaster", "body", (-4.6, 0.6), 172.0, 10.0)   # hangs back off the petiole
bone("head", "body", (3.6, -0.8), 18.0, 3.0)       # the neck, the head carried low and forward
bone("mand", "head", (8.4, -1.2), -62.0, 4.8)      # the jaw hinge, the mandibles pointing up round the grub's neck
bone("ant_0", "head", (8.0, -1.4), -4.0, 3.2)      # antennae: scape forward, funiculus down to the floor ahead
bone("ant_1", "ant_0", B["ant_0"].end(), 56.0, 4.0)

# Six legs, hips clustered under the thorax the way an ant's are, the feet
# spread fore and aft. Short and jointed: femur and tibia together about the
# body's radius, the knee thrown out forward on the fore and mid pairs and
# back on the hind, the far side a step behind, a touch higher, and darker.
FEMUR, TIBIA, TARSUS = 4.0, 4.8, 1.6
LEGS = {  # name: (hip, rest foot x)
    "far_b": ((-2.8, 1.8), -6.8),
    "far_m": ((-0.2, 2.0), -1.6),
    "far_f": ((2.4, 1.6), 5.0),
    "near_b": ((-2.2, 2.4), -6.0),
    "near_m": ((0.6, 2.8), -0.2),
    "near_f": ((3.2, 2.2), 6.6),
}
FAR_LIFT = 1.2
def ground_of(leg): return GROUND - (FAR_LIFT if leg.startswith("far") else 0.0)
def knee_bend(leg): return 1 if leg.endswith("_f") else -1
for leg, (hip, fx) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), FEMUR, TIBIA, knee_bend(leg))
    f = bone(f"{leg}_femur", "body", hip, hf, FEMUR)
    t = bone(f"{leg}_tibia", f.name, f.end(), ht, TIBIA)
    bone(f"{leg}_tarsus", t.name, t.end(), 90.0 + (16.0 if fx >= hip[0] else -16.0), TARSUS)

RIG.seal()
REST = RIG.rest
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== the grub's spine
# Six segments, head first, draped over the back from the jaws to behind the
# gaster: (centre x, centre y, rx, ry). The head end is lowest and furthest
# forward, where the jaws hold it; the tail droops behind. On the floor the
# same arc is a resting C.
SEGS = [
    (8.0, -6.6, 3.5, 3.3),
    (4.2, -9.0, 4.3, 4.1),
    (-0.2, -10.0, 4.8, 4.6),
    (-4.9, -9.6, 4.8, 4.6),
    (-9.3, -8.0, 4.4, 4.2),
    (-12.9, -5.6, 3.6, 3.4),
]
NSEG = len(SEGS)
def seg_angle(i):
    """A segment's rest heading: along the spine, pointing to the tail (so +y of the segment is its belly... on the up-side)."""
    a = SEGS[max(0, i - 1)]; b = SEGS[min(NSEG - 1, i + 1)]
    return D(math.atan2(b[1] - a[1], b[0] - a[0]))
SEG_REST = [(x, y, seg_angle(i)) for i, (x, y, rx, ry) in enumerate(SEGS)]
LINK = [(math.hypot(SEGS[i + 1][0] - SEGS[i][0], SEGS[i + 1][1] - SEGS[i][1]),
         D(math.atan2(SEGS[i + 1][1] - SEGS[i][1], SEGS[i + 1][0] - SEGS[i][0]))) for i in range(NSEG - 1)]
# The head capsule ahead of the first segment, the calipers ahead of that. The
# capsule rides segment 0 turned by its own nod (index "cap"); the calipers by
# their own hinge ("jaw").
CAPSULE = (11.4, -5.5)
JAW_HINGE = (12.7, -5.0)
GRIP = (10.2, -5.0)   # where the hauler's jaws close round the grub's neck

GRUB_PARTS = {}  # part id -> (frame, local xf, scales with segment?)
def gput(id, frame, at, rot, shape, fill, stroke=None, opacity=None, scale=None, scales=True):
    p = put(id, "anchor", at, rot, shape, fill, stroke, opacity, scale)
    GRUB_PARTS[id] = (frame, at, rot, scales)
    return p
def guse(id, frame, at, asset, scale, scales=True):
    p = RIG.use(id, "anchor", at, asset, scale=scale)
    GRUB_PARTS[id] = (frame, at, 0.0, scales)
    return p

# ============================================================== parts
HAIR_DK = {"color": "$ink", "width": "hair"}

def leg_parts(leg, femur, tibia, knee, stroke):
    at, a = on_bone(f"{leg}_tarsus"); put(f"{leg}_tarsus", f"{leg}_tarsus", at, a, bar(TARSUS, 0.9, 0.5, 0.3), tibia, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(TIBIA, 1.5, 0.8), tibia, stroke)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(FEMUR, 2.1, 1.6), femur, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_knee", f"{leg}_tibia", at, 0.0, circ(0.95), knee)

# ---- far side, behind everything: legs and the far mandible
for leg in ("far_b", "far_m", "far_f"):
    leg_parts(leg, "$sand.dark2", "$sand.dark2", "$sand.dark", None)
at, a = on_bone("mand", 0.0, -0.6)
MAND = poly([(-0.8, -1.1), (1.2, -1.3), (3.2, -1.0), (4.8, -0.2), (5.6, 1.2), (4.2, 0.6), (2.4, 0.9), (0.6, 1.2), (-0.8, 1.0)])
put("mand_far", "mand", at, a - 14.0, MAND, "$sand.dark", HAIR_DK)

# ---- the hauler: gaster, petiole, thorax, head
at, a = on_bone("gaster", 5.4, -0.2)
put("gaster", "gaster", at, a, ell(5.2, 4.2), "$chitin.dark2", INK_THIN)
at, a = on_bone("gaster", 5.2, -2.0)
put("gaster_shade", "gaster", at, a, ell(4.2, 1.8), "$timber.dark2")
for k, s in enumerate((2.6, 5.2, 7.8)):
    at, a = on_bone("gaster", s, 0.0)
    put(f"gaster_band_{k}", "gaster", at, a, rect(0.7, 7.0 - 2.0 * abs(k - 1), 0.35), "$timber.dark2@heavy")
at, a = on_bone("gaster", 5.8, 2.8)
put("gaster_lit", "gaster", at, a, ell(3.4, 0.9), "$chitin.dark")
RIG.use("organ", "gaster", on_bone("gaster", 5.4, -1.0)[0], "ss.lib.organ", scale=0.44)
put("petiole", "body", (-4.4, 0.6), 0, ell(1.5, 1.9), "$timber.dark", HAIR_DK)
THORAX = [(-4.0, 0.2), (-3.4, -1.8), (-1.2, -2.4), (0.6, -3.4), (2.8, -3.2), (4.4, -1.8), (4.8, 0.4),
          (3.6, 2.4), (0.2, 3.0), (-2.8, 2.4)]
put("thorax", "body", (0, 0), 0, poly(THORAX), "$chitin.dark2", INK_THIN)
put("thorax_lit", "body", (1.2, -2.2), -8.0, ell(2.4, 0.8), "$chitin.dark")
put("thorax_shade", "body", (0.2, 1.8), 0, ell(3.0, 0.9), "$timber.dark2")
at, a = on_bone("head", 3.0, 0.2)
put("head", "head", at, a, ell(3.9, 3.3), "$chitin.dark2", INK_THIN)
at, a = on_bone("head", 3.2, 1.6)
put("head_shade", "head", at, a, ell(2.6, 1.1), "$timber.dark2")
at, a = on_bone("head", 5.0, -0.9)
put("eye", "head", at, 0, circ(1.0), "$silent")
at, a = on_bone("head", 4.8, -1.3)
put("eye_glint", "head", at, 0, circ(0.35), "$white")

# ---- near legs, over the body
for leg in ("near_b", "near_m", "near_f"):
    leg_parts(leg, "$timber.dark2", "$sand.dark", "$timber.dark", HAIR_DK)
N_HAULER = len(RIG.parts)

# ---- the grub, over the back: tail first so each segment laps the one behind
GRUB_FILL = ["$husk", "$husk", "$husk", "$husk", "$husk", "$husk.dark"]
for i in reversed(range(NSEG)):
    x, y, rx, ry = SEGS[i]
    ang = SEG_REST[i][2]
    c, s = math.cos(R(ang)), math.sin(R(ang))
    def at_local(u, v): return (x + u * c - v * s, y + u * s + v * c)
    # The segment's +v side is the side a heading toward the tail turns to on
    # screen: with the spine running back (heading near 180) +v is up. The
    # belly (down, -v) takes a shade, the back (+v) a gloss.
    gput(f"grub_{i}", i, (x, y), ang, ell(rx, ry), GRUB_FILL[i], INK_HAIR)
    gput(f"belly_{i}", i, at_local(0.0, -ry * 0.55), ang, ell(rx * 0.72, ry * 0.36), "$husk.dark@heavy")
    gput(f"gloss_{i}", i, at_local(0.4, ry * 0.5), ang, ell(rx * 0.55, ry * 0.2), "$white@heavy")
    if 0 < i < NSEG - 1:
        gput(f"spir_{i}", i, at_local(0.0, -ry * 0.12), 0.0, circ(0.55), "$husk.dark2")
# The grub's own organ, on its flank: it is of the hive too, and it is the
# Instar's when the hauler is gone.
guse("organ_g", 2, (-0.6, -9.2), "ss.lib.organ", scale=0.3)
# Head capsule: hardened, amber, with the one dark ocellus
gput("capsule", "cap", CAPSULE, -20.0, ell(2.8, 2.5), "$chitin.dark", INK_HAIR)
gput("capsule_lit", "cap", (11.0, -6.8), -20.0, ell(1.4, 0.5), "$chitin@soft")
gput("eye_g", "cap", (12.0, -6.3), 0.0, circ(0.7), "$ink")
# The calipers: the one thing a grub that size already owns, and what the
# hauler's jaws are wrapped round.
JAW = poly([(-0.7, -0.9), (1.2, -1.1), (2.8, -0.7), (4.0, 0.4), (4.3, 1.7), (3.3, 0.9), (1.9, 0.6), (0.3, 0.9), (-0.7, 0.7)])
gput("gjaw_dn", "jaw_dn", (JAW_HINGE[0], JAW_HINGE[1] + 0.6), 26.0, JAW, "$chitin.dark2", HAIR_DK)
gput("gjaw_up", "jaw_up", JAW_HINGE, -4.0, JAW, "$chitin.dark", HAIR_DK)

# ---- the hauler's near mandible, over the grub's neck, and the antennae last
at, a = on_bone("mand", 0.0, 0.6)
put("mand", "mand", at, a, MAND, "$timber.dark", HAIR_DK)
at, a = on_bone("ant_0"); put("ant_0", "ant_0", at, a, bar(3.2, 1.1, 0.9, 0.4), "$timber.dark", HAIR_DK)
at, a = on_bone("ant_1"); put("ant_1", "ant_1", at, a, bar(4.0, 0.9, 0.7, 0.4), "$timber.dark", HAIR_DK)
RIG.check()

GRUB_IDS = list(GRUB_PARTS)
HAULER_IDS = [p["id"] for p in RIG.parts if p["id"] not in GRUB_PARTS]

# ============================================================== the grub's model
# A grub pose is the world transform (x, y, heading, girth) of each segment,
# plus the capsule's and the calipers'. Every part of the grub is placed in
# one of those frames at rest and follows it.
FRAMES_REST = {i: (x, y, a, 1.0) for i, (x, y, a) in enumerate(SEG_REST)}
FRAMES_REST["cap"] = (CAPSULE[0], CAPSULE[1], -20.0, 1.0)
FRAMES_REST["jaw_up"] = (JAW_HINGE[0], JAW_HINGE[1], -4.0, 1.0)
FRAMES_REST["jaw_dn"] = (JAW_HINGE[0], JAW_HINGE[1] + 0.6, 26.0, 1.0)
LOCAL = {}
for pid, (frame, at, rot, scales) in GRUB_PARTS.items():
    fx, fy, fa, _ = FRAMES_REST[frame]
    LOCAL[pid] = invert_apply((fx, fy, fa), at, rot)

def grub_frames(segs, cap_nod=0.0, jaw_open=0.0):
    """
    Frames from segment transforms `segs` [(x, y, heading, girth)]: the capsule
    rides segment 0's front end, turned by `cap_nod`; the calipers ride the
    capsule, opened by `jaw_open` degrees each (up turns up, down turns down).
    """
    fr = {i: s for i, s in enumerate(segs)}
    x0, y0, a0, g0 = segs[0]
    rx0, ry0, ra0 = SEG_REST[0]
    d0 = wrap(a0 - ra0)
    # the capsule in segment 0's rest frame, carried by segment 0 and nodded about its neck
    lx, ly, la = invert_apply((rx0, ry0, ra0), CAPSULE, -20.0)
    cx, cy, ca = compose((x0, y0, a0), (lx, ly, la + cap_nod))
    fr["cap"] = (cx, cy, ca, 1.0)
    for name, sgn, rest in (("jaw_up", -1, FRAMES_REST["jaw_up"]), ("jaw_dn", 1, FRAMES_REST["jaw_dn"])):
        jx, jy, ja = invert_apply((CAPSULE[0], CAPSULE[1], -20.0), (rest[0], rest[1]), rest[2])
        wx, wy, wa = compose((cx, cy, ca), (jx, jy, ja + sgn * jaw_open))
        fr[name] = (wx, wy, wa, 1.0)
    return fr

def grub_offsets(fr):
    """Each grub part's (dx, dy, drot, scale) from rest under frames `fr`."""
    out = {}
    for pid, (frame, at, rot, scales) in GRUB_PARTS.items():
        x, y, a, g = fr[frame]
        lx, ly, la = LOCAL[pid]
        k = g if scales else 1.0
        wx, wy, wa = compose((x, y, a), (lx * k, ly * k, la))
        out[pid] = (wx - at[0], wy - at[1], wrap(wa - rot), k)
    return out

def chain(root_dx, root_dy, root_da, bends, girth=None):
    """
    The grub as a chain from its held end: segment 0 moved by (root_dx, root_dy)
    and turned by root_da, then each link turned by root_da plus the running
    sum of `bends` — so a bend near the head carries everything behind it.
    """
    girth = girth or [1.0] * NSEG
    x, y = SEGS[0][0] + root_dx, SEGS[0][1] + root_dy
    pts, acc, link_d = [(x, y)], root_da, []
    for k in range(NSEG - 1):
        acc += bends[k]
        L, h = LINK[k]
        x += L * math.cos(R(h + acc)); y += L * math.sin(R(h + acc))
        pts.append((x, y)); link_d.append(acc)
    segs = []
    for i in range(NSEG):
        if i == 0: d = link_d[0] if link_d else root_da
        elif i == NSEG - 1: d = link_d[-1]
        else: d = 0.5 * (link_d[i - 1] + link_d[i])
        segs.append((pts[i][0], pts[i][1], SEG_REST[i][2] + d, girth[i]))
    return segs

def spine(offsets, girth, follow=0.7):
    """The grub from per-segment (dx, dy) and girths, each segment turned toward the line through its neighbours."""
    pts = [(SEGS[i][0] + offsets[i][0], SEGS[i][1] + offsets[i][1]) for i in range(NSEG)]
    segs = []
    for i in range(NSEG):
        a, b = pts[max(0, i - 1)], pts[min(NSEG - 1, i + 1)]
        h = D(math.atan2(b[1] - a[1], b[0] - a[0]))
        segs.append((pts[i][0], pts[i][1], SEG_REST[i][2] + follow * wrap(h - SEG_REST[i][2]), girth[i]))
    return segs

# ============================================================== motion
def plant_legs(pose, feet):
    world = solve(pose)
    for leg, (hip, fx) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], FEMUR, TIBIA, knee_bend(leg))
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_tarsus"] = B[f"{leg}_tarsus"].heading + pose.get("tarsus", 0.0)
    return pose

def grip_of(pose):
    """Where the jaws hold the grub's neck under `pose`, and how far the head has turned."""
    w = solve(pose)
    hx, hy, ha = w["head"]
    rx, ry, ra = REST["head"]
    lx, ly, _ = invert_apply((rx, ry, ra), GRIP, 0.0)
    gx, gy, _ = compose((hx, hy, ha), (lx, ly, 0.0))
    return gx - GRIP[0], gy - GRIP[1], wrap(ha - ra)

# ---- haul: 0.9s, the idle and the walk. Carrying, not walking: two tripods,
# the body dipping under the load on each step and pitching after it, the
# gaster swinging a beat later; the head stays down, the antennae sweeping
# the floor ahead. The grub is held at the head end and answers each dip a
# beat behind, every segment later and larger than the last, so the free
# tail swings furthest and last — and a slower sway once a loop under that,
# the weight of it shifting from step to step.
HAUL = 0.9
TRIPOD = {"near_f": 0.0, "near_b": 0.0, "far_m": 0.0, "near_m": 0.5, "far_f": 0.5, "far_b": 0.5}
STRIDE = 2.8
def step(t, ph):
    u = (t + ph) % 1.0
    if u < 0.55:
        return lerp(STRIDE, -STRIDE, u / 0.55), 0.0
    v = (u - 0.55) / 0.45
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 3.2 * math.sin(math.pi * v)

def haul_hauler(t):
    dip = 0.5 - 0.5 * math.cos(4 * math.pi * (t - 0.08))      # two dips a loop, one a step
    pose = {"body": (0.8 * cyc(t, 0.1), 2.4 * dip - 0.8, 4.0 * cyc(2 * t, -0.05))}
    pose["gaster"] = 7.0 * cyc(2 * t, -0.2)
    pose["head"] = 4.0 * cyc(2 * t, -0.12) + 2.0
    pose["ant_0"] = 12.0 * cyc(2 * t, -0.25)
    pose["ant_1"] = 16.0 * cyc(2 * t, -0.4)
    feet = {}
    for leg, (hip, fx) in LEGS.items():
        dx, lift = step(t, TRIPOD[leg])
        feet[leg] = (fx + dx, ground_of(leg) - lift)
    return plant_legs(pose, feet)

def haul_grub(t, pose):
    gx, gy, ga = grip_of(pose)
    # The tail lies on the gaster and is thrown up off it: a swing down is
    # stopped short by the body under it, a swing up is not.
    def lie(w): return w if w > 0 else 0.35 * w
    bends = [(3.6 + 3.0 * k) * lie(0.6 * cyc(2 * t, -0.2 - 0.07 * k) + 0.7 * cyc(t, -0.1 - 0.06 * k)) for k in range(NSEG - 1)]
    girth = [1.0 + 0.04 * cyc(2 * t, -0.25 - 0.07 * i) for i in range(NSEG)]
    return grub_frames(chain(gx, gy, 0.6 * ga, bends, girth), cap_nod=-0.4 * ga, jaw_open=2.0 * cyc(2 * t, -0.1))

# ---- creep: 1.15s, the Instar's crawl (and, on the hauler's back, a load
# that will not keep still). A contraction starts at the tail and runs to the
# head: each segment in turn lifts, fattens and slides forward, and plants
# again as the next one goes, so a hump travels the body and the whole of it
# has moved one stride on by the time the head reaches. Written in the body's
# own frame, where a planted segment slides back at the walking rate — the
# game ties the clip's rate to how fast the body actually goes
# (`animTracksSpeed`), so on the floor the planted ones stand still.
CREEP = 1.15
C_STRIDE = 9.0
C_LIFT = 3.6
C_WINDOW = 0.4
C_DELAY = [0.5, 0.4, 0.3, 0.2, 0.1, 0.0]   # tail (5) first, head (0) last
def creep_u(t, i): return (t - C_DELAY[i]) % 1.0
def creep_grub(t, hauler_pose=None):
    offs, girth = [], []
    mean = 0.5 - C_WINDOW / 2
    for i in range(NSEG):
        u = creep_u(t, i)
        moving = u < C_WINDOW
        s = smooth(0.0, C_WINDOW, u) if moving else 1.0
        arc = math.sin(math.pi * u / C_WINDOW) if moving else 0.0
        dx = C_STRIDE * (s - u - mean)
        lift = C_LIFT * arc * (0.55 if i in (0, NSEG - 1) else 1.0)
        offs.append((dx, -lift))
        girth.append(1.0 + 0.13 * arc)
    u0 = creep_u(t, 0)
    reach = math.sin(math.pi * u0 / C_WINDOW) if u0 < C_WINDOW else 0.0
    bite = math.sin(math.pi * min(1.0, max(0.0, (u0 - C_WINDOW) / 0.18))) if u0 >= C_WINDOW else 0.0
    return grub_frames(spine(offs, girth), cap_nod=-10.0 * reach + 6.0 * bite, jaw_open=24.0 * reach - 6.0 * bite)

def creep_hauler(t):
    return plant_legs({}, {leg: (fx, ground_of(leg)) for leg, (hip, fx) in LEGS.items()})

# ---- death: 0.46s, both halves at once. The hauler rears and its jaws spring
# open — it lets go — then its legs fold, the body drops to the floor, the
# gaster slumps and the head goes down; the grub, released, is jolted up,
# writhes once head to tail and goes slack, lying lower and flatter. The
# grub's half is all there is when the Instar dies on its own. Still by 0.85.
def death_hauler(t):
    rear = math.sin(math.pi * smooth(0.0, 0.3, t))
    fall = smooth(0.18, 0.62, t)
    settle = 0.4 * math.sin(math.pi * smooth(0.62, 0.85, t))
    pose = {"body": (0.4 * rear, -1.0 * rear + 4.6 * fall - settle, -5.0 * rear + 6.0 * fall)}
    pose["gaster"] = -6.0 * rear + 14.0 * fall
    pose["head"] = -8.0 * rear + 24.0 * fall
    pose["mand"] = -34.0 * smooth(0.0, 0.22, t) + 10.0 * fall
    pose["ant_0"] = -18.0 * rear + 40.0 * fall
    pose["ant_1"] = 30.0 * fall
    feet = {}
    for leg, (hip, fx) in LEGS.items():
        hx = hip[0] + (fx - hip[0]) * lerp(1.0, 1.5, fall)
        feet[leg] = (hx, ground_of(leg) + 1.2 * fall - 1.2 * rear)
    return plant_legs(pose, feet)

def death_grub(t):
    jolt = math.sin(math.pi * smooth(0.05, 0.35, t))
    slack = smooth(0.3, 0.8, t)
    env = math.sin(math.pi * smooth(0.12, 0.75, t))
    writhe = [16.0 * env * math.sin(2 * math.pi * (1.4 * t - 0.14 * k)) for k in range(NSEG - 1)]
    # Slack: the arch lets go — the held end drops free of the jaws and the
    # tail slides down behind, the body lying out low.
    rest_bends = [0.0, 6.0, 6.0, 4.0, 2.0]
    bends = [w + slack * r for w, r in zip(writhe, rest_bends)]
    root = (0.6 * slack, -2.2 * jolt + 3.4 * slack, -6.0 * jolt - 14.0 * slack)
    girth = [1.0 + 0.1 * jolt - 0.06 * slack for _ in range(NSEG)]
    return grub_frames(chain(root[0], root[1], root[2], bends, girth), cap_nod=10.0 * slack - 8.0 * jolt,
                       jaw_open=28.0 * jolt + 12.0 * slack)

# ---- tracks
def all_tracks(hauler_at, grub_at, ts, extra=None, still=()):
    out = RIG.tracks(hauler_at, ts, extra, still=still)
    series = {pid: ([], [], [], []) for pid in GRUB_IDS}
    for t in ts:
        offs = grub_offsets(grub_at(t))
        for pid, (dx, dy, dr, k) in offs.items():
            s = series[pid]
            s[0].append(dx); s[1].append(dy); s[2].append(dr); s[3].append(k)
    for pid in GRUB_IDS:
        xs, ys, rs, ks = series[pid]
        for prop, vs, rest in (("x", xs, 0.0), ("y", ys, 0.0), ("rot", rs, 0.0), ("scale", ks, 1.0)):
            if prop == "rot" and GRUB_PARTS[pid][2] == 0.0 and pid.startswith(("spir", "eye", "organ")):
                continue  # a round thing's turn only shows as noise
            if max(abs(v - rest) for v in vs) > 0.01:
                out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(v if prop != "scale" else round(v, 3))] for t, v in zip(ts, vs)], "ease": "linear"})
    return out

STILL = {"eye", "eye_glint", "organ"} | {f"{leg}_knee" for leg in LEGS}

animations = {}
TS_HAUL = keyset(18)
def haul_both(t): return haul_hauler(t)
animations["haul"] = {
    "description": "Carrying, not walking — the idle and the walk. Two tripods, each foot planted while the body rides over it and lifted on the way forward; the hauler dips under the load on every step and pitches after it, the gaster swinging a beat later, the head kept down with the antennae sweeping the floor ahead. The grub is held at the head end and answers each dip a beat behind, every segment later and larger than the one before, so the free tail swings furthest and last; under that a slower sway once a loop, the weight shifting from side to side of the stride.",
    "duration": HAUL,
    "tracks": all_tracks(haul_hauler, lambda t: haul_grub(t, haul_hauler(t)), TS_HAUL, still=STILL),
}
TS_CREEP = keyset(24)
animations["creep"] = {
    "description": "The load's crawl — the Instar's walk, played by the `grub` state (feelers `ANIMATED_CLIPS` `e_instar`), its rate tied to how fast the body is actually going (`animTracksSpeed`). A contraction starts at the tail and runs to the head: each segment in turn lifts, fattens and slides forward and plants as the next one goes, so a hump travels the length of the body; when it reaches the head the capsule reaches and the calipers open, then bite shut as it plants. On the hauler's back the hauler stands still under a load that will not.",
    "duration": CREEP,
    "tracks": all_tracks(creep_hauler, creep_grub, TS_CREEP, still=STILL),
}
TS_DEATH = [0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.24, 0.28, 0.32, 0.36, 0.4, 0.44, 0.48, 0.52, 0.56, 0.6, 0.64, 0.68, 0.72, 0.76, 0.8, 0.85, 1.0]
def organ_fade(t0): return lambda t: 1.0 - 0.9 * smooth(t0, 0.82, t)
animations["death"] = {
    "description": "Both halves at once. The hauler rears and its jaws spring open — it lets go — then its legs fold out, the body drops to the floor under the cargo, the gaster slumps and the head goes down; its organ goes out. The grub, released, is jolted up, writhes once head to tail, and goes slack: the held end drops free, the arch lets go and the body lies out low with the calipers fallen open and its own organ going out. That grub's half is all there is to see when the `grub` state dies on its own. Still from 0.85.",
    "duration": 0.46,
    "tracks": all_tracks(death_hauler, death_grub, TS_DEATH,
                         [("organ", "opacity", organ_fade(0.2)), ("organ_g", "opacity", organ_fade(0.35))], still=STILL),
}

# ============================================================== states
# The grub alone, recentred on its own middle: the canvas is sized for the
# pair, and left where it rode the load would crawl a body off its own hitbox.
def grub_extent():
    xs, ys = [], []
    for i, (x, y, rx, ry) in enumerate(SEGS):
        xs += [x - rx, x + rx]; ys += [y - ry, y + ry]
    xs.append(JAW_HINGE[0] + 4.4)
    return min(xs), max(xs), min(ys), max(ys)
lo_x, hi_x, lo_y, hi_y = grub_extent()
SHIFT = (r2(-(lo_x + hi_x) / 2), r2(-(lo_y + hi_y) / 2 + 1.0))
BASE = {p["id"]: p for p in RIG.parts}
def moved(pid): return [r2(BASE[pid]["at"][0] + SHIFT[0]), r2(BASE[pid]["at"][1] + SHIFT[1])]

variants = {
    "elite": {
        "description": "Marked by the hive, and the mark is on the hauler: it goes to silhouette — shell and legs gone black — with one bone plate across the gaster, bone jaws grown heavy round the grub's neck, and a bigger, brighter organ. The grub on its back is the same grub, because what an elite drops is an ordinary Instar (feelers `EnemySystem.dropLoad`: the load takes nothing of its carrier's) and a load drawn marked would be a second elite the player is never given.",
        "scale": 1.25,
        "set": {
            "gaster.fill": "$coal", "thorax.fill": "$coal", "head.fill": "$coal", "petiole.fill": "$coal.dark",
            "gaster_shade.fill": "$dead", "thorax_shade.fill": "$dead", "head_shade.fill": "$dead",
            "gaster_lit.fill": "$coal.light", "thorax_lit.fill": "$coal.light",
            "gaster_band_1.fill": "$dead", "gaster_band_2.fill": "$dead",
            "gaster_band_0.fill": "$bone", "gaster_band_0.scale": [2.6, 1.15],
            **{f"{leg}_{seg}.fill": "$coal.dark" for leg in LEGS for seg in ("femur", "tibia", "tarsus")},
            **{f"{leg}_knee.fill": "$smoke" for leg in LEGS},
            "mand.fill": "$bone.light", "mand_far.fill": "$bone.dark", "mand.scale": [1.2, 1.35], "mand_far.scale": [1.2, 1.35],
            "ant_0.fill": "$smoke", "ant_1.fill": "$smoke",
            "organ.scale": 0.54,
        },
    },
    "grub": {
        "description": "The load, set down and moving on its own — the Instar (feelers `e_instar`, which plays `creep` from this state, and its death). Exactly the grub drawn on the hauler's back, every part of it moved by the same amount onto its own centre, so it is the same drawing and every clip's motion is the same here as there: six pale segments, the organ on its flank, an amber head capsule and the pair of hardened calipers the hauler's jaws were wrapped round — which is the whole of why this is an enemy and not a pickup. Recentred because the canvas is sized for a pair, and left where it rode the load would crawl a body off its own hitbox.",
        "animations": ["creep", "death"],
        "remove": HAULER_IDS,
        "set": {f"{pid}.at": moved(pid) for pid in GRUB_IDS},
    },
}

# ============================================================== document
DESCRIPTION = (
    "The nest's traffic, carrying. A low dark ant under a pale grub slung the whole length of its back, and the silhouette is the cargo — "
    "an amber ant beside the Mite's amber blob would be two creatures competing for one read, so this one is defined by what it holds. It "
    "earns the number it carries in the game: this is the body that barely moves when you hit it, and a creature with its jaws locked round "
    "brood it will not put down is a better account of that than any amount of shell. Seen side-on facing +x; the game flips it. "
    "Built on a skeleton (scripts/porter.py): the hauler's thorax is the root, the gaster hangs off the petiole and swings after it, the head "
    "is carried low on the neck with its jaws closed round the grub's neck, and six short jointed legs — darker than the shell — are solved "
    "every frame to a foot on the floor in two tripods. The grub is its own drawing on its own model: six segments, an amber head capsule, a "
    "pair of hardened calipers and its own organ, and the `grub` state is that drawing alone, moved onto its own centre — the Instar the game "
    "puts down alive where a Porter dies (`dropType: 'instar'`). `haul` is the walk and the idle: the grub, held at the head end, answers "
    "each step a beat behind with the free tail swinging furthest and last. `creep` is the Instar's crawl: a contraction running tail to head, "
    "a hump travelling the body, the calipers opening on the reach. Brood pale over a hauler in dark amber and umber, drawn to read on the "
    "burrow's dark floor. Gameplay radius 10. The `death` clip carries both halves: the hauler letting go and folding under its cargo, and the "
    "grub's writhe and slack — which is all there is once `grub` strips the hauler away."
)

# The drawing is laid out about the hauler's thorax; it goes on the canvas a
# little lower, so the grub's hump has headroom over the back. Offsets are
# unchanged by a translation, so only the rest positions move.
DROP = 2.4
def dropped(p):
    q = dict(p); q["at"] = [p["at"][0], r2(p["at"][1] + DROP)]
    return q
SKEL = RIG.skeleton()
SKEL["joints"] = {k: [v[0], r2(v[1] + DROP)] for k, v in SKEL["joints"].items()}

doc = {
    "id": "ss.enemy.porter",
    "name": "Porter",
    "description": DESCRIPTION,
    "tags": ["enemy", "porter"],
    "size": [44, 40],
    "meta": {"radius": 10},
    "parts": [dropped(p) for p in RIG.parts],
    "variants": variants,
    "animations": animations,
    "skeleton": SKEL,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-porter.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks, grub shift {SHIFT}")
