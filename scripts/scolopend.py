"""The Scolopend — the burrow's second boss, a centipede that goes through walls.

    python3 scripts/scolopend.py        # rewrites apps/ss/assets/ss-enemy-scolopend.json

Built on the rig (scripts/rig.py), and drawn as a stylised animal rather than a
realistic one. The first rig build was a faithful Scolopendra — eleven flat
plates in hard maroon stripes, twenty-two thin two-link legs and three-link
whip antennae — and it read as a skittering fringe: correct, and creepy. This
one keeps the skeleton, the clips and every hand-off between them, and
changes the drawing and the gait:

  - a spine: a root at the middle of the body, a chain of ten plates forward to
    the head and back to the tail prongs, every link a bone hanging off the
    last. A clip lays each plate at a heading and the chain carries the rest, so
    a wave put in at the head travels down the body and nothing can part at a
    joint
  - plates: rounded, overlapping pill-shaped tergites — an armoured train
    more than a ribbon — with a thin darker seam at each rear margin instead of
    a stripe, and a soft sheen
  - legs: five pairs, on every other plate, short and chunky (about a plate's
    half-width), blunt, a step darker than the plates but close to them. Each is
    a femur and a tibia solved every frame to a foot (two-bone IK); they step
    once a loop in a slow metachronal wave, a trundle rather than a scuttle
  - the head leads: a round shield with two readable eyes (`eye_a`, `eye_b`)
    and the hive's organ, short thick two-link antennae that sway, small blunt
    bone fangs with a venom bead that still snap in the strike, and two short
    tail prongs behind

Seen from above along its travel axis, and turned by the game (feelers
`EnemyType.turns`, `faceOffset: 18.6`): the rest pose's travel axis — the
chord from the tail joint to the neck — sits exactly 18.6 degrees above +x.
Amber plates with oxblood seams and an oxblood head: the amber-to-maroon family
this slot always had, carried on the plates so the body reads on the burrow's
near-black floor.

The clips, and the contracts the game holds them to (EnemySystem, mode 1 → 2
→ surface): `crawl` is the idle and the walk (played at the rate the body is
covering ground); its first frame is the rest pose. `coil` opens on the rest
pose and is held on its last frame; `strike` and `submerge` both open on
exactly that frame, because either may be what the game plays when the brace
lets go (a burrowing body plays `submerge` — the dive is its release). The
dive's last frame is what the body wears for the whole crossing, so it is a
streamlined body, not a hole. `surface` opens on the dive's last frame and
ends on the rest pose, which is also where `strike` ends.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, lerp, smooth, cyc, keyset, ik2,
                 poly, ell, circ, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== layout
# Canvas 128×96, origin at the centre, +y down. The travel axis runs AX
# degrees (world, +y down, so negative is up the screen) — the game's
# faceOffset. Each plate's rest heading bends a little off it along the body:
# the tail is laid lower and the head lifted.
SIZE = (128, 96)
AX = -18.6
N = 10            # trunk plates, seg_0 behind the head … seg_9 at the tail
L = 7.0           # plate pitch along the spine (the trunk is as long as before)
MID = (N - 1) / 2
ARC = 0.9         # degrees of bend per plate: the head end flatter, the tail steeper
HW = [6.6, 7.2, 7.6, 7.8, 7.8, 7.7, 7.5, 7.1, 6.5, 5.7]   # plate half-widths
ROOT = N // 2     # the spine's root sits at joint J5, the front of seg_5

# The crawl's body wave: one wavelength along the trunk, amplitude growing
# toward the tail, travelling head to tail once a loop. The rest pose is the
# crawl's first frame, so the drawing already lies in that S.
CRAWL = 0.9
KB = 1.0 / N
def wave_amp(i): return 9.0 + 8.0 * i / (N - 1)
def wave(i, t): return wave_amp(i) * math.sin(2 * math.pi * (t - i * KB))
HEAD_AMP, HEAD_LEAD = 7.0, 0.07

def unit(h): return (math.cos(R(h)), math.sin(R(h)))
def chord(tilt):
    """The heading from the tail joint to the neck, for a given tilt of the whole curve."""
    x = y = 0.0
    for i in range(N):
        c, s = unit(AX + tilt - ARC * (i - MID) + wave(i, 0.0)); x += c; y += s
    return D(math.atan2(y, x))
# Tilt the curve so the chord from tail to neck lies exactly on AX: that
# chord is the axis the game's faceOffset turns onto the heading.
TILT = AX - chord(0.0)
def arc_heading(i): return AX + TILT - ARC * (i - MID)     # forward heading of plate i, before the wave
REST_H = [arc_heading(i) + wave(i, 0.0) for i in range(N)]
HEAD_REST = arc_heading(0) - 3.5 + HEAD_AMP * math.sin(2 * math.pi * HEAD_LEAD)

# Joints J0 (neck) … J10 (tail), walked back from the neck along the rest
# headings, then shifted so the whole animal sits centred on the canvas.
J = [(0.0, 0.0)]
for i in range(N):
    c, s = unit(REST_H[i])
    J.append((J[-1][0] - L * c, J[-1][1] - L * s))
HEAD_LEN = 11.0
front = (J[0][0] + (HEAD_LEN + 7.0) * unit(HEAD_REST)[0], J[0][1] + (HEAD_LEN + 7.0) * unit(HEAD_REST)[1])
back = (J[-1][0] - 9.0 * unit(REST_H[-1])[0], J[-1][1] - 9.0 * unit(REST_H[-1])[1])
SHIFT = (-(front[0] + back[0]) / 2 - 1.5, -(front[1] + back[1]) / 2 - 2.0)
J = [(x + SHIFT[0], y + SHIFT[1]) for x, y in J]

# ============================================================== skeleton
RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("trunk", None, J[ROOT], REST_H[ROOT - 1], 0.0)
# Forward chain: seg_4 … seg_0, each a bone from its rear joint to its front.
parent = "trunk"
for i in range(ROOT - 1, -1, -1):
    bone(f"s{i}", parent, J[i + 1], REST_H[i], L); parent = f"s{i}"
bone("head", "s0", J[0], HEAD_REST, HEAD_LEN)
# Back chain: seg_5 … seg_9, each a bone from its front joint to its rear.
parent = "trunk"
for i in range(ROOT, N):
    bone(f"s{i}", parent, J[i], REST_H[i] + 180.0, L); parent = f"s{i}"

def fwd_of(i): return REST_H[i]
def seg_centre_rest(i):
    return ((J[i][0] + J[i + 1][0]) / 2, (J[i][1] + J[i + 1][1]) / 2)
def local_to_world(origin, heading, along, across):
    c, s = unit(heading)
    return (origin[0] + along * c - across * s, origin[1] + along * s + across * c)

def head_pt(along, across): return local_to_world(J[0], HEAD_REST, along, across)
SIDES = (("l", -1), ("r", 1))     # the animal's left is -across (up the screen at rest)

# Antennae: two short, thick links from the front of the shield.
ANT = [5.0, 4.4]
ANT_W = [(2.3, 2.0), (2.0, 1.3)]
ANT_SPLAY, ANT_BEND = 34.0, 10.0
for sd, sg in SIDES:
    p = head_pt(9.6, sg * 2.2)
    h = HEAD_REST + sg * ANT_SPLAY
    for k, Lk in enumerate(ANT):
        b = bone(f"ant_{sd}{k}", "head" if k == 0 else f"ant_{sd}{k - 1}", p, h, Lk)
        p = b.end(); h += sg * ANT_BEND

# Forcipules: a short base out from under the shield and a small blunt fang
# turned back in, so the pair close in front of the head.
FC0, FC1 = 3.0, 4.6
for sd, sg in SIDES:
    b0 = bone(f"fc_{sd}0", "head", head_pt(8.6, sg * 3.6), HEAD_REST + sg * 40.0, FC0)
    bone(f"fc_{sd}1", f"fc_{sd}0", b0.end(), HEAD_REST - sg * 42.0, FC1)

# Tail prongs: the ultimate legs, short and blunt, off the last plate.
ULT = [3.8, 3.4]
for sd, sg in SIDES:
    back_h = REST_H[N - 1] + 180.0
    p = local_to_world(J[N], REST_H[N - 1], 1.2, sg * 2.4)
    b0 = bone(f"ult_{sd}0", f"s{N - 1}", p, back_h - sg * 20.0, ULT[0])
    bone(f"ult_{sd}1", f"ult_{sd}0", b0.end(), back_h - sg * 8.0, ULT[1])

# Legs: a pair on every other plate. Hip under the plate's edge, the foot a
# short way past it, the knee on the forward side.
LEG_PLATES = [0, 2, 4, 6, 8]
FEMUR, TIBIA = 3.8, 4.4
def rake(i): return lerp(2.2, -2.6, i / (N - 1))
def hip_local(i, sg): return (0.4, sg * HW[i] * 0.72)
def foot_rest_local(i, sg): return (rake(i) - 1.0, sg * (HW[i] + 4.4))
LEGCYC = 1                        # one step per crawl loop: a trundle
KL = 0.2                          # lag from one pair to the next
DUTY = 0.6
STRIDE, TUCK = 1.7, 1.2
def leg_phase(i, sg): return -LEG_PLATES.index(i) * KL + (0.0 if sg < 0 else 0.5)
def step(u):
    """Foot offset along the plate and inward tuck, at step phase u: stance pushes back, swing comes forward drawn in."""
    u %= 1.0
    if u < DUTY:
        return lerp(STRIDE, -STRIDE, u / DUTY), 0.0
    v = (u - DUTY) / (1 - DUTY)
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), TUCK * math.sin(math.pi * v)
def crawl_foot(i, sg, t):
    a, tuck = step(LEGCYC * t + leg_phase(i, sg))
    fa, fc = foot_rest_local(i, sg)
    return (fa + a, fc - sg * tuck)

BEND = {}
for i in LEG_PLATES:
    for sd, sg in SIDES:
        c = seg_centre_rest(i)
        hip = local_to_world(c, fwd_of(i), *hip_local(i, sg))
        foot = local_to_world(c, fwd_of(i), *crawl_foot(i, sg, 0.0))
        best = None
        for bend in (1, -1):
            h1, h2 = ik2(hip, foot, FEMUR, TIBIA, bend)
            knee = (hip[0] + FEMUR * math.cos(R(h1)), hip[1] + FEMUR * math.sin(R(h1)))
            f = unit(fwd_of(i))
            score = (knee[0] - hip[0]) * f[0] + (knee[1] - hip[1]) * f[1]
            if best is None or score > best[0]: best = (score, bend, h1, h2, knee)
        _, bend, h1, h2, knee = best
        BEND[(i, sd)] = bend
        bone(f"leg_{i}{sd}_f", f"s{i}", hip, h1, FEMUR)
        bone(f"leg_{i}{sd}_t", f"leg_{i}{sd}_f", knee, h2, TIBIA)

RIG.seal()
solve = RIG.solve
put, use, on_bone = RIG.put, RIG.use, RIG.on_bone

# ============================================================== parts
PLATE_FILL = ["$ember.dark"] + ["$chitin"] * (N - 2) + ["$ember.dark"]
SEAM_FILL = "$oxblood"
FEMUR_FILL, TIBIA_FILL = "$ember.dark", "$chitin.dark"

def superellipse(a, b, n=2.6, k=24, taper=0.0, x0=0.0):
    """A rounded box `a` long and `b` wide about (x0, 0), a touch narrower at the front by `taper`."""
    pts = []
    for j in range(k):
        th = 2 * math.pi * j / k
        c, s = math.cos(th), math.sin(th)
        x = a * math.copysign(abs(c) ** (2 / n), c)
        y = b * math.copysign(abs(s) ** (2 / n), s) * (1 - taper * x / a)
        pts.append((x0 + x, y))
    return pts
PLATE_A = 4.5                       # half-length: plates overlap their neighbours by 2 units
def plate_shape(hw): return poly(superellipse(PLATE_A, hw, 2.5, 28, 0.06))
def seam_shape(hw):
    """A thin crescent along the plate's rear margin."""
    rim = [p for p in superellipse(PLATE_A, hw * 0.96, 2.5, 40, 0.06) if p[0] < -PLATE_A * 0.45]
    rim.sort(key=lambda p: p[1])
    inner = [(x + 0.9 * (1 - abs(y) / hw) + 0.25, y) for x, y in reversed(rim)]
    return poly(rim + inner)

# ---- tail prongs, under everything at the tail
for sd, sg in SIDES:
    at, a = on_bone(f"ult_{sd}0"); put(f"ult_{sd}0", f"ult_{sd}0", at, a, bar(ULT[0], 2.8, 2.4, 1.0), "$ember.dark", INK_HAIR)
    at, a = on_bone(f"ult_{sd}1"); put(f"ult_{sd}1", f"ult_{sd}1", at, a, bar(ULT[1], 2.3, 1.5, 1.0), "$oxblood", INK_HAIR)

# ---- legs, rear pairs first so the front ones lie over them
for i in reversed(LEG_PLATES):
    for sd, sg in SIDES:
        at, a = on_bone(f"leg_{i}{sd}_t"); put(f"leg_{i}{sd}_t", f"leg_{i}{sd}_t", at, a, bar(TIBIA, 2.5, 1.8, 1.0), TIBIA_FILL, INK_HAIR)
        at, a = on_bone(f"leg_{i}{sd}_f"); put(f"leg_{i}{sd}_f", f"leg_{i}{sd}_f", at, a, bar(FEMUR, 3.0, 2.7, 0.8), FEMUR_FILL, INK_HAIR)

# ---- antennae, then the fangs over them, all with their roots under the shield
for sd, sg in SIDES:
    for k, Lk in enumerate(ANT):
        at, a = on_bone(f"ant_{sd}{k}")
        put(f"ant_{sd}{k}", f"ant_{sd}{k}", at, a, bar(Lk, *ANT_W[k], 1.0), ["$spore.dark", "$spore.dark2"][k], INK_HAIR)
def fang(Lf, c, w0=1.35, bend=0.07):
    """A small blunt fang along +x, `Lf` long, curving toward `c` (±1), ending in a rounded tip."""
    xs = [Lf * k / 5 for k in range(6)]
    mid = [c * bend * x * x for x in xs]
    half = [w0 * (1 - 0.6 * x / Lf) for x in xs]
    outer = [(x, m - c * h) for x, m, h in zip(xs, mid, half)]
    inner = [(x, m + c * h) for x, m, h in zip(xs, mid, half)]
    tip = [(Lf + 0.45, mid[-1] + c * 0.15)]
    return poly([(-0.5, -c * w0 * 0.8)] + outer + tip + inner[::-1] + [(-0.5, c * w0 * 0.8)])
for sd, sg in SIDES:
    at, a = on_bone(f"fc_{sd}0"); put(f"fc_{sd}0", f"fc_{sd}0", at, a, bar(FC0, 3.2, 2.8), "$oxblood", INK_HAIR)
    at, a = on_bone(f"fc_{sd}1")
    c = -sg  # the fang curls toward the midline
    put(f"fc_{sd}1", f"fc_{sd}1", at, a, fang(FC1, c), "$bone", INK_HAIR)
    at, a = on_bone(f"fc_{sd}1", FC1 - 0.2, c * 0.07 * (FC1 - 0.2) ** 2)
    put(f"venom_{sd}", f"fc_{sd}1", at, 0.0, circ(0.75), "$spore.light")

# ---- the trunk, tail plate first so each plate's rear margin lies over the next
for i in range(N - 1, -1, -1):
    c = seg_centre_rest(i)
    h = fwd_of(i)
    put(f"seg_{i}", f"s{i}", c, h, plate_shape(HW[i]), PLATE_FILL[i], INK_HAIR)
    put(f"band_{i}", f"s{i}", c, h, seam_shape(HW[i]), SEAM_FILL)
    put(f"gloss_{i}", f"s{i}", local_to_world(c, h, 1.1, -HW[i] * 0.28), h, ell(1.4, HW[i] * 0.48), "$white@0.2")

# ---- the head: a round shield, the organ on its crown, two eyes at the front
HEAD_SHAPE = poly(superellipse(6.6, 7.6, 2.3, 32, 0.08, 4.4))
put("head", "head", J[0], HEAD_REST, HEAD_SHAPE, "$oxblood", INK_THIN)
put("head_gloss", "head", head_pt(4.0, -3.6), HEAD_REST - 20, ell(2.8, 1.4), "$white@0.2")
use("organ", "head", head_pt(3.2, 0.0), "ss.lib.organ", scale=0.66)
for sd, sg in SIDES:
    x = "a" if sg < 0 else "b"
    # slanted in toward the midline at the front: a hunter's look, not a doll's
    put(f"eye_{x}", "head", head_pt(7.9, sg * 4.1), HEAD_REST + sg * 28, ell(1.8, 1.15), "$dead", INK_HAIR)
    put(f"glint_{x}", "head", head_pt(8.5, sg * 4.0), HEAD_REST, circ(0.42), "$white@0.8")

RIG.check()
HEAD_GROUP = ["head", "head_gloss", "organ", "eye_a", "eye_b", "glint_a", "glint_b"]

# ============================================================== posing
# A pose is asked for as plain numbers and turned into the rig's pose here:
#   seg      N heading deltas off the rest (degrees)
#   head     the head's heading delta off the rest
#   trunk    (along, across) travel of the root, in the axis frame
#   feet     fn(i, sg) -> (along, across) foot in its plate's frame
#   ant, fc, ult: fn(sd, sg, k) -> delta
def axis_vec(along, across): return local_to_world((0.0, 0.0), AX, along, across)

def build(seg, head=0.0, trunk=(0.0, 0.0), feet=None, ant=None, fc=None, ult=None, keep_head_on_axis=0.0):
    dx, dy = axis_vec(*trunk)
    pose = {"body": (dx, dy, 0.0)}
    for i in range(N):
        pose[f"abs:s{i}"] = REST_H[i] + seg[i] + (180.0 if i >= ROOT else 0.0)
    pose["abs:head"] = HEAD_REST + head
    if keep_head_on_axis:
        # Slide the root across the axis so the neck stays on the line the
        # head is aimed down — a body that bends behind a head that holds.
        w = solve(pose)
        ex, ey = w["head"][0] - J[0][0], w["head"][1] - J[0][1]
        n_ = axis_vec(0.0, 1.0)
        off = ex * n_[0] + ey * n_[1]
        dx -= keep_head_on_axis * off * n_[0]; dy -= keep_head_on_axis * off * n_[1]
        pose["body"] = (dx, dy, 0.0)
    for sd, sg in SIDES:
        for k in range(len(ANT)):
            if ant: pose[f"ant_{sd}{k}"] = ant(sd, sg, k)
        for k in range(2):
            if fc: pose[f"fc_{sd}{k}"] = fc(sd, sg, k)
            if ult: pose[f"ult_{sd}{k}"] = ult(sd, sg, k)
    world = solve(pose)
    for i in LEG_PLATES:
        bx, by, ba = world[f"s{i}"]
        fwd = ba if i < ROOT else ba - 180.0
        c = (bx + L / 2 * math.cos(R(ba)), by + L / 2 * math.sin(R(ba)))
        for sd, sg in SIDES:
            hx, hy, _ = world[f"leg_{i}{sd}_f"]
            fl = feet(i, sg) if feet else crawl_foot(i, sg, 0.0)
            foot = local_to_world(c, fwd, *fl)
            h1, h2 = ik2((hx, hy), foot, FEMUR, TIBIA, BEND[(i, sd)])
            pose[f"abs:leg_{i}{sd}_f"] = h1
            pose[f"abs:leg_{i}{sd}_t"] = h2
    return pose

# ---- crawl
def ant_crawl(t):
    def f(sd, sg, k):
        # a slow sway, the pair in antiphase, the tip a little behind
        ph = 0.0 if sg < 0 else 0.5
        return [9.0, 6.0][k] * cyc(t, ph - 0.1 * k)
    return f
def fc_crawl(t):
    def f(sd, sg, k):
        # the fangs working open and shut once a loop
        return sg * [3.0, 7.0][k] * (0.5 + 0.5 * cyc(t, 0.1 - 0.08 * k))
    return f
def ult_crawl(t):
    def f(sd, sg, k):
        # riding the tail's wave, a beat later
        return [12.0, 8.0][k] * math.sin(2 * math.pi * (t - (N + 0.8 + k * 1.2) * KB))
    return f
def crawl_seg(t): return [wave(i, t) - wave(i, 0.0) for i in range(N)]
def crawl_head(t):
    return HEAD_AMP * (math.sin(2 * math.pi * (t + HEAD_LEAD)) - math.sin(2 * math.pi * HEAD_LEAD))
def zeroed(fn_t, t):
    """An appendage's crawl deltas less their value at t=0, so the crawl's first frame is the drawn rest pose."""
    f, f0 = fn_t(t), fn_t(0.0)
    return lambda sd, sg, k: f(sd, sg, k) - f0(sd, sg, k)
def crawl_pose(t):
    surge = 0.8 * (cyc(t, 0.0) - cyc(0.0, 0.0))
    return build(crawl_seg(t), crawl_head(t), (surge, 0.0),
                 lambda i, sg: crawl_foot(i, sg, t), zeroed(ant_crawl, t), zeroed(fc_crawl, t), zeroed(ult_crawl, t))

REST_FEET = lambda i, sg: crawl_foot(i, sg, 0.0)

# ---- the coiled pose: the trunk thrown into an S behind a head held on the
# line, drawn back down it, reared (the head shield swells), the fangs open,
# the antennae laid back, the legs braced wide and the tail prongs lifted apart
COIL_S = [36.0 * math.cos(2 * math.pi * (i * 11.0 / N + 0.4) / 9.4) for i in range(N)]
AIM_HEAD = AX - HEAD_REST     # the head turned exactly onto the line it will run
def coil_feet(g):
    def f(i, sg):
        a, c = REST_FEET(i, sg)
        return (lerp(a, rake(i) * 0.4 - 0.6, g), c + sg * 1.6 * g)
    return f
# The fangs: a pair of deltas (base, fang), + turning each side outward.
FC_OPEN = (14.0, 32.0)
FC_SHUT = (-5.0, -12.0)
ANT_BACK = (24.0, 10.0)
def coil_bits(g, shiver=0.0):
    ant = lambda sd, sg, k: -sg * ANT_BACK[k] * g + shiver * (1 if k % 2 else -1) * 2.5
    fc = lambda sd, sg, k: sg * FC_OPEN[k] * g
    ult = lambda sd, sg, k: -sg * (18.0 if k == 0 else 8.0) * g
    return ant, fc, ult
def coil_like(g, shiver=0.0, trunk_along=-4.4):
    ant, fc, ult = coil_bits(g, shiver)
    seg = [COIL_S[i] * g for i in range(N)]
    return build(seg, AIM_HEAD * g, (trunk_along * g, 0.0), coil_feet(g), ant, fc, ult,
                 keep_head_on_axis=g)
def wind(t):
    """Wound, not eased: a fast first draw, a slow creep, a last snatch — at 1 by 0.94 and held."""
    return 0.62 * smooth(0.0, 0.26, t) + 0.2 * smooth(0.26, 0.8, t) + 0.18 * smooth(0.8, 0.94, t)
def coil_pose(t):
    shiver = math.sin(2 * math.pi * 9 * t) * smooth(0.3, 0.45, t) * (1 - smooth(0.78, 0.9, t))
    return coil_like(wind(t), shiver)
COILED = coil_like(1.0)

# ---- strike: from the coiled frame the S throws itself straight and a
# little past it, the body lunges down the line with the fangs snapping shut,
# then it settles onto the rest pose
def strike_pose(t):
    g = lerp(1.0, -0.32, smooth(0.0, 0.34, t))
    g = lerp(g, 0.0, smooth(0.34, 1.0, t))
    lunge = lerp(-4.4, 4.2, smooth(0.0, 0.3, t))
    lunge = lerp(lunge, 0.0, smooth(0.36, 1.0, t))
    snap = smooth(0.08, 0.22, t)
    back = smooth(0.4, 1.0, t)
    ant = lambda sd, sg, k: lerp(-sg * ANT_BACK[k] * max(g, 0.0) * (1 - snap) - sg * [28.0, 12.0][k] * snap, 0.0, back)
    fc = lambda sd, sg, k: lerp(lerp(sg * FC_OPEN[k], sg * FC_SHUT[k], snap), 0.0, back)
    ult = lambda sd, sg, k: lerp(-sg * (18.0 if k == 0 else 8.0), sg * (8.0 if k == 0 else 10.0), smooth(0.05, 0.4, t)) * (1 - back)
    seg = [COIL_S[i] * g for i in range(N)]
    # the feet: from the braced stance, thrown back as it lunges, home at the end
    def feet(i, sg):
        a0, c0 = coil_feet(1.0)(i, sg)
        a1, c1 = REST_FEET(i, sg)
        mid = (rake(i) - 2.2, c1 - sg * 0.8)
        u = smooth(0.0, 0.3, t); v = smooth(0.35, 1.0, t)
        return (lerp(lerp(a0, mid[0], u), a1, v), lerp(lerp(c0, mid[1], u), c1, v))
    return build(seg, AIM_HEAD * g, (lunge, 0.0), feet, ant, fc, ult,
                 keep_head_on_axis=max(0.0, min(1.0, abs(g))))

# ---- the dive pose, held through the whole crossing: the trunk laid straight
# down the line, every leg folded back flat along its plate, the antennae laid
# back over the shield, the fangs shut, the tail prongs together
def dive_feet(i, sg):
    return (-3.8, sg * (HW[i] * 0.9 + 0.8))
DIVE_ANT = lambda sd, sg, k: -sg * [40.0, 8.0][k]
DIVE_FC = lambda sd, sg, k: sg * FC_SHUT[k]
DIVE_ULT = lambda sd, sg, k: sg * (12.0 if k == 0 else 4.0)
DIVE_SEG = [(AX - REST_H[i]) * 0.9 for i in range(N)]    # laid nearly straight down the line
DIVE_HEAD = AX - HEAD_REST

def lerp_fn(f0, f1, u):
    return lambda sd, sg, k: lerp(f0(sd, sg, k), f1(sd, sg, k), u)

def submerge_pose(t):
    # every plate goes from the coil to the dive as the wave reaches it, and
    # overshoots — the crawl's own wave spent once and hard
    seg = []
    for i in range(N):
        u = smooth(0.04 + 0.06 * i, 0.3 + 0.06 * i, t)
        kick = 22.0 * math.sin(math.pi * u) * math.cos(math.pi * i * 11.0 / N / 3.2)
        seg.append(lerp(COIL_S[i], DIVE_SEG[i], u) + kick)
    uh = smooth(0.0, 0.3, t)
    head = lerp(AIM_HEAD, DIVE_HEAD, uh) - 10.0 * math.sin(math.pi * uh)
    drive = lerp(-4.4, 2.0, smooth(0.0, 0.35, t))
    def feet(i, sg):
        u = smooth(0.06 + 0.06 * i, 0.26 + 0.06 * i, t)
        a0, c0 = coil_feet(1.0)(i, sg); a1, c1 = dive_feet(i, sg)
        return (lerp(a0, a1, u), lerp(c0, c1, u))
    ant0, fc0, ult0 = coil_bits(1.0)
    return build(seg, head, (drive, 0.0), feet, lerp_fn(ant0, DIVE_ANT, smooth(0.0, 0.3, t)),
                 lerp_fn(fc0, DIVE_FC, smooth(0.0, 0.2, t)), lerp_fn(ult0, DIVE_ULT, smooth(0.5, 1.0, t)),
                 keep_head_on_axis=1.0 - smooth(0.0, 0.5, t))

# ---- surface: from the dive, the head rears first and the wave runs out of
# the body behind it; each pair of legs comes out wide as its plate clears,
# the fangs open on the way up, and it settles on the rest pose
def surface_pose(t):
    seg = []
    for i in range(N):
        u = smooth(0.08 + 0.055 * i, 0.4 + 0.055 * i, t)
        kick = -14.0 * math.sin(math.pi * u) * math.cos(math.pi * i * 11.0 / N / 3.2)
        seg.append(lerp(DIVE_SEG[i], 0.0, u) + kick)
    uh = smooth(0.0, 0.5, t)
    head = lerp(DIVE_HEAD, 0.0, uh) + 12.0 * math.sin(math.pi * uh)
    rise = lerp(2.0, 0.0, smooth(0.0, 0.6, t))
    def feet(i, sg):
        u = smooth(0.1 + 0.05 * i, 0.45 + 0.05 * i, t)
        a0, c0 = dive_feet(i, sg); a1, c1 = REST_FEET(i, sg)
        wide = 2.2 * math.sin(math.pi * u)
        return (lerp(a0, a1, u) + 0.8 * math.sin(math.pi * u), lerp(c0, c1, u) + sg * wide)
    ua = smooth(0.0, 0.7, t)
    fc_open = lambda sd, sg, k: lerp(DIVE_FC(sd, sg, k), 0.0, smooth(0.0, 0.8, t)) + sg * FC_OPEN[k] * 1.1 * math.sin(math.pi * smooth(0.05, 0.8, t))
    ant = lambda sd, sg, k: lerp(DIVE_ANT(sd, sg, k), 0.0, ua) + sg * [14.0, 6.0][k] * math.sin(math.pi * ua)
    ult = lambda sd, sg, k: lerp(DIVE_ULT(sd, sg, k), 0.0, smooth(0.45, 1.0, t)) - sg * 12.0 * math.sin(math.pi * smooth(0.45, 1.0, t))
    return build(seg, head, (rise, 0.0), feet, ant, fc_open, ult)

# ---- death: the fangs close, then the body rolls up from the head back into
# a curl and settles, the legs tucking in under their plates as the curl
# reaches them, the tail prongs last. No thrash. Still from 0.85.
# A curl is a bend, not a turn: the heading changes steadily down the body,
# the front plates turning one way and the rear the other about the root.
DEATH_CURL = [-8.5 * (i - MID) for i in range(N)]
def death_pose(t):
    t = min(t, 0.85)
    seg = []
    for i in range(N):
        u = smooth(0.12 + 0.045 * i, 0.42 + 0.045 * i, t)
        seg.append(lerp(0.0, DEATH_CURL[i], u))
    head = lerp(0.0, DEATH_CURL[0] + 12.0, smooth(0.1, 0.45, t))
    def feet(i, sg):
        u = smooth(0.12 + 0.05 * i, 0.36 + 0.05 * i, t)
        a, c = REST_FEET(i, sg)
        return (lerp(a, -1.0, u), lerp(c, sg * (HW[i] * 0.78), u))
    shut = smooth(0.0, 0.16, t)
    fc = lambda sd, sg, k: sg * FC_SHUT[k] * 1.2 * shut
    ant = lambda sd, sg, k: -sg * [28.0, 16.0][k] * smooth(0.15, 0.55, t)
    ult = lambda sd, sg, k: -[14.0, 18.0][k] * smooth(0.55, 0.85, t)
    return build(seg, head, (lerp(0.0, -1.5, smooth(0.2, 0.7, t)), 0.0), feet, ant, fc, ult)

# ============================================================== clips
tracks = RIG.tracks
def head_scale(fn): return [(p, "scale", fn) for p in HEAD_GROUP]
def plate_scale(fn_i):
    return [(f"seg_{i}", "scale", (lambda i: lambda t: fn_i(i, t))(i)) for i in range(N)] + \
           [(f"band_{i}", "scale", (lambda i: lambda t: fn_i(i, t))(i)) for i in range(N)]
def glow(fn): return [("venom_l", "scale", fn), ("venom_r", "scale", fn)]

# The coil's rear: the shield swells toward the camera and the plates
# fatten as the body piles into itself, most at the tail.
REAR = 0.14
def fat_of(i): return 0.03 + 0.05 * i / (N - 1)
def coil_rear(t): return 1.0 + REAR * wind(t)
def coil_fat(i, t): return 1.0 + fat_of(i) * wind(t)
def strike_g(t):
    g = lerp(1.0, -0.32, smooth(0.0, 0.34, t)); return lerp(g, 0.0, smooth(0.34, 1.0, t))
def strike_rear(t): return 1.0 + REAR * max(0.0, strike_g(t)) - 0.04 * math.sin(math.pi * smooth(0.1, 0.6, t))
def strike_fat(i, t): return 1.0 + fat_of(i) * max(0.0, strike_g(t))
DIVE_SINK = 0.88
def sub_rear(t): return lerp(1.0 + REAR, DIVE_SINK, smooth(0.0, 0.32, t))
def sub_fat(i, t):
    u = smooth(0.04 + 0.06 * i, 0.3 + 0.06 * i, t)
    return lerp(1.0 + fat_of(i), 0.95, u)
def surf_rear(t):
    u = smooth(0.0, 0.5, t)
    return lerp(DIVE_SINK, 1.0, u) + 0.16 * math.sin(math.pi * u)
def surf_fat(i, t):
    u = smooth(0.08 + 0.055 * i, 0.4 + 0.055 * i, t)
    return lerp(0.95, 1.0, u) + 0.05 * math.sin(math.pi * u)
def death_rear(t):
    t = min(t, 0.85); return 1.0 - 0.06 * smooth(0.3, 0.7, t)
def death_fat(i, t):
    t = min(t, 0.85); u = smooth(0.12 + 0.045 * i, 0.42 + 0.045 * i, t)
    return 1.0 - 0.05 * u

animations = {}
TS_CRAWL = keyset(36)
animations["crawl"] = {
    "description": "The walk, and the idle the game plays at whatever pace it is covering: a slow bend travels down the trunk head to tail once a loop, the head leading it; under it the five pairs of short legs step once each — a foot pushing back along its plate while it is down and coming forward tucked in while it is up — in a gentle metachronal wave head to tail, left and right in antiphase, a trundle rather than a scuttle; the antennae sway in turn, the fangs work, and the tail prongs ride the tail a beat later. The first frame is the rest pose.",
    "duration": CRAWL,
    "tracks": tracks(crawl_pose, TS_CRAWL, glow(lambda t: 1.0 + 0.12 * (0.5 + 0.5 * cyc(t, 0.25)) - 0.12 * (0.5 + 0.5 * cyc(0.0, 0.25)))),
}
TS_COIL = keyset(30)
animations["coil"] = {
    "description": "Winding up, from the rest pose. The trunk throws itself into an S behind a head held on the line it has chosen and drawn back down it; the head rears (the shield swells toward you) and the plates fatten as the body piles into itself, most at the tail; the fangs open wide, the antennae lay back, the legs brace out and the tail prongs lift apart. Wound rather than eased — a fast first draw, a slow creep with a shiver in it, a last snatch — and held on the final frame, because the release is the dash. The game stretches it to the brace.",
    "duration": 0.95,
    "tracks": tracks(coil_pose, TS_COIL, head_scale(coil_rear) + plate_scale(coil_fat) + glow(lambda t: 1.0 + 0.45 * wind(t))),
}
TS_STRIKE = keyset(18)
animations["strike"] = {
    "description": "The release. It opens on the coil's last frame exactly: the S throws itself straight and a little past, the body lunges down the line with the fangs snapping shut and the antennae swept back, the legs thrown behind; then it settles onto the rest pose, which is the crawl's first frame. Played once on the dash.",
    "duration": 0.3,
    "tracks": tracks(strike_pose, TS_STRIKE, head_scale(strike_rear) + plate_scale(strike_fat) + glow(lambda t: 1.0 + 0.45 * max(0.0, strike_g(t)) * (1 - smooth(0.1, 0.3, t)))),
}
TS_DEATH = [i / 40 for i in range(35)] + [0.9, 0.95, 1.0]
animations["death"] = {
    "description": "It lets go and rolls up: the fangs close, then the body curls from the head back, each plate settling a little lower as the curl reaches it and its legs tucking in under it, the tail prongs last; it lies curled, the organ and the venom gone dim. No thrash. Still from 0.85.",
    "duration": 0.7,
    "tracks": tracks(death_pose, TS_DEATH, head_scale(death_rear) + plate_scale(death_fat)
                     + [("organ", "opacity", lambda t: 1.0 - 0.7 * smooth(0.3, 0.8, min(t, 0.85))),
                        ("venom_l", "opacity", lambda t: 1.0 - 0.75 * smooth(0.2, 0.7, min(t, 0.85))),
                        ("venom_r", "opacity", lambda t: 1.0 - 0.75 * smooth(0.2, 0.7, min(t, 0.85)))]),
}
TS_SUB = keyset(20)
animations["submerge"] = {
    "description": "Going into the earth, and the release a burrowing body plays in place of `strike` — so it opens on the coil's last frame exactly. The head drives down (the shield sinks away from you) and the body follows it in as the crawl's own wave spent once and hard, head to tail: each plate throws the S out as the wave reaches it and lies straight down the line, its legs folding back flat along it, the antennae laying back over the shield and the fangs shutting. The last frame is what the body wears for the whole crossing — streamlined for the earth, sunk a little, legs stowed — and is exactly where `surface` begins.",
    "duration": 0.34,
    "tracks": tracks(submerge_pose, TS_SUB, head_scale(sub_rear) + plate_scale(sub_fat) + glow(lambda t: lerp(1.45, 1.0, smooth(0.0, 0.4, t)))),
}
TS_SURF = keyset(18)
animations["surface"] = {
    "description": "Coming back out, and the reverse of `submerge` in shape rather than in frames: from the dive's last frame the head rears first (the shield swells up toward you and settles), and the wave runs out of the body behind it; each pair of legs comes out wide as its plate clears, the fangs open on the way up and the antennae flare, the tail prongs last. Ends on the rest pose. Played where the ground bulges.",
    "duration": 0.3,
    "tracks": tracks(surface_pose, TS_SURF, head_scale(surf_rear) + plate_scale(surf_fat)),
}

# ============================================================== states
LEG_IDS = [f"leg_{i}{sd}_{j}" for i in LEG_PLATES for sd, _ in SIDES for j in ("f", "t")]
ENRAGED_PLATES = ["$oxblood", "$ember.dark", "$chitin", "$chitin.light", "$chitin.light",
                  "$chitin.light", "$chitin.light", "$chitin", "$ember.dark", "$oxblood"]
enraged_set = {}
for i, f in enumerate(ENRAGED_PLATES): enraged_set[f"seg_{i}.fill"] = f
for i in range(N): enraged_set[f"band_{i}.fill"] = "$coral.dark"
for lid in LEG_IDS: enraged_set[f"{lid}.fill"] = "$bone.dark" if lid.endswith("_f") else "$bone.dark2"
enraged_set.update({
    "ult_l0.fill": "$bone.dark", "ult_r0.fill": "$bone.dark", "ult_l1.fill": "$bone", "ult_r1.fill": "$bone",
    "head.fill": "$dead", "head_gloss.fill": "$white@0.12",
    "fc_l0.fill": "$bone", "fc_r0.fill": "$bone", "fc_l1.fill": "$white", "fc_r1.fill": "$white",
    "venom_l.fill": "$white", "venom_r.fill": "$white",
    "eye_a.fill": "$ember", "eye_b.fill": "$ember",
    "organ.scale": 0.76,
})
FINAL_PLATES = ["$sand", "$sand.light"] * (N // 2)
final_set = {}
for i, f in enumerate(FINAL_PLATES): final_set[f"seg_{i}.fill"] = f
for i in range(N): final_set[f"band_{i}.fill"] = "$ember"
for i in range(N): final_set[f"gloss_{i}.fill"] = "$white@0.08"
for lid in LEG_IDS: final_set[f"{lid}.fill"] = "$sand.dark" if lid.endswith("_f") else "$soil.light"
final_set.update({
    "ult_l0.fill": "$sand.dark", "ult_r0.fill": "$sand.dark", "ult_l1.fill": "$soil.light", "ult_r1.fill": "$soil.light",
    "ant_l0.fill": "$sand.light", "ant_r0.fill": "$sand.light", "ant_l1.fill": "$sand", "ant_r1.fill": "$sand",
    "head.fill": "$sand.dark", "head_gloss.fill": "$white@0.08",
    "fc_l0.fill": "$bone", "fc_r0.fill": "$bone", "fc_l1.fill": "$bone.light", "fc_r1.fill": "$bone.light",
    "venom_l.fill": "$venom.light", "venom_r.fill": "$venom.light",
})
variants = {
    "enraged": {
        "description": "Phase two: the body goes hot from the middle out — the plates at the centre flare to the lightest amber and the seams burn — the legs bleach to bone, the head blackens with its eyes lit ember, and the venom at the fang tips stops being a highlight and starts being the brightest thing on the creature.",
        "scale": 1.08,
        "set": enraged_set,
    },
    "final": {
        "description": "Phase three: it has been living in the earth for the last third of the fight and the earth is all over it. The plates have gone the colour of the ground, dulled and caked, the legs and the antennae with them, and the only things on the body still the colour of an animal are the two venom fangs and the light coming up between the plates — every rear seam ember — which is the read: it is not brighter, it is buried, and what you can still see of it is the part that kills you.",
        "scale": 1.1,
        "set": final_set,
    },
}

# ============================================================== document
DESCRIPTION = (
    "What an ant nest is actually afraid of, and it was already down here before you were. A centipede seen from above along its travel axis "
    "and turned by the game rather than mirrored; the rest pose's axis sits 18.6 degrees above +x, which is the `faceOffset` the game pairs with "
    "this document. Drawn stylised rather than skittering: ten rounded amber plates overlapping like an armoured train, each with a thin "
    "oxblood seam at its rear margin, under a round oxblood head shield carrying the hive's organ and two readable eyes; small blunt bone "
    "fangs with a venom bead closing in front of it; short thick two-link antennae; five pairs of short, chunky legs on every other plate, a "
    "step darker than the plates; and two short tail prongs behind. "
    "Built on a skeleton (scripts/scolopend.py): the spine is a chain rooted mid-body, so a bend put in at the head travels down it and nothing "
    "parts at a joint; every leg is a femur and a tibia solved each frame to a foot. `crawl` is a slow body wave head to tail over a gentle "
    "metachronal wave of the legs, and its first frame is the rest pose. `coil` and `strike` are the windup and its release: the trunk throws "
    "itself into an S behind a head held on the line, rears and fattens, and `strike` opens on exactly `coil`'s last frame and settles on the "
    "rest pose. Gameplay radius 40. The `death` clip closes the fangs and rolls the body up into a curl from the head back, the legs tucking "
    "in as it goes.\n\n"
    "`submerge` and `surface` are the pair the game's burrowing dash needs. For this body the dive *is* the release (EnemySystem plays it "
    "where another body would play `strike`), so it too opens on the coil's last frame; its last frame is held for the whole crossing, so it "
    "is a streamlined body with its legs stowed, and `surface` opens exactly there. They are written as one shape each rather than as one "
    "clip played backwards, because a reversed dive un-dives — it reads as the ground giving the animal back rather than as the animal coming "
    "up through it."
)

doc = {
    "id": "ss.enemy.scolopend",
    "name": "Scolopend",
    "description": DESCRIPTION,
    "tags": ["enemy", "boss"],
    "size": list(SIZE),
    "meta": {"radius": 40},
    "parts": RIG.parts,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-scolopend.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
