"""The Scolopend — the burrow's second boss, a centipede that goes through walls.

    python3 scripts/scolopend.py        # rewrites apps/ss/assets/ss-enemy-scolopend.json

It was drawn on the Courser's hand-kept rig: eleven plates on a curve, a fringe
of two-link legs, forcipules and antennae, every part turned about its own
centre. The plates bobbed in place instead of carrying a wave, the legs ticked
a few degrees, and the loop measured 6px of travel at game scale; its amber
plates sat among a black head and maroon-to-black tail, so on the burrow's
near-black floor the whole body averaged 2.39 contrast. And its `submerge` and
`surface` tracks were absolute values written as offsets, so both opened on a
pose nothing else ends on. This rebuilds it on the rig (scripts/rig.py):

  - a spine: a root at the middle of the body, a chain of plates forward to
    the head and a chain back to the ultimate legs, every link a bone hanging
    off the last. A clip lays each plate at a heading and the chain carries the
    rest, so a wave put in at the head travels down the body and nothing can
    part at a joint
  - legs: every plate carries a pair, each a femur and a tibia solved every
    frame to a foot (two-bone IK) — a foot pushes back along its plate while it
    is down and swings forward drawn in while it is up, and the pairs run a
    metachronal wave head to tail, left and right in antiphase
  - the head leads: forcipules as a base and a curved fang with a venom bead,
    antennae as three-link whips, two ocellus clusters (`eye_a`, `eye_b`), and
    the hive's organ on the head shield

Seen from above along its travel axis, and turned by the game (feelers
`EnemyType.turns`, `faceOffset: 18.6`): the rest pose's travel axis sits 18.6
degrees above +x and stays there, because that offset belongs to the pairing
of this document with the type. Amber plates banded maroon at every rear
margin — the Scolopendra's own pattern and the family this slot always had —
with a maroon head and first plate, and legs a step darker than the plates so
the body reads first. Contrast on the burrow's floor is carried by the amber.

The clips, and the contracts the game holds them to (EnemySystem, mode 1 → 2
→ surface): `crawl` is the idle and the walk (played at the rate the body is
covering ground); its first frame is the rest pose. `coil` opens on the rest
pose and is held on its last frame; `strike` and `submerge` both open on
exactly that frame, because either may be what the game plays when the brace
lets go (a burrowing body plays `submerge` — the dive is its release). The
dive's last frame is what the body wears for the whole crossing, so it is a
streamlined centipede, not a hole. `surface` opens on the dive's last frame
and ends on the rest pose, which is also where `strike` ends.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== layout
# Canvas 128×96 (grown from 120×88 so the lunge and the death curl clear the
# edge), origin at the centre, +y down. The travel axis runs AX degrees (world,
# +y down, so negative is up the screen) — the game's faceOffset. Each plate's rest heading bends a little off it along the body:
# the tail is laid lower and the head lifted, the curve the original drew.
SIZE = (128, 96)
AX = -18.6
N = 11            # trunk plates, seg_0 behind the head … seg_10 at the tail
L = 6.4           # plate pitch along the spine
ARC = 0.8         # degrees of bend per plate: the head end flatter, the tail steeper (tail low and behind)
HW = [5.6, 6.2, 6.6, 6.9, 7.0, 7.0, 7.0, 6.8, 6.5, 6.0, 5.2]   # plate half-widths
ROOT = 6          # the spine's root sits at joint J6, the front of seg_6

# The crawl's body wave: one wavelength along the trunk, amplitude growing
# toward the tail, travelling head to tail once a loop. The rest pose is the
# crawl's first frame, so the drawing already lies in that S.
CRAWL = 0.9
KB = 1.0 / N
def wave_amp(i): return 8.0 + 8.0 * i / (N - 1)
def wave(i, t): return wave_amp(i) * math.sin(2 * math.pi * (t - i * KB))
HEAD_AMP, HEAD_LEAD = 7.0, 0.07

def arc_heading(i): return AX + TILT - ARC * (i - 5)     # forward heading of plate i, before the wave
def unit(h): return (math.cos(R(h)), math.sin(R(h)))
def chord(tilt):
    """The heading from the tail joint to the neck, for a given tilt of the whole curve."""
    x = y = 0.0
    for i in range(N):
        c, s = unit(AX + tilt - ARC * (i - 5) + wave(i, 0.0)); x += c; y += s
    return D(math.atan2(y, x))
# Tilt the curve so the chord from tail to neck lies exactly on AX: that
# chord is the axis the game's faceOffset turns onto the heading.
TILT = AX - chord(0.0)
REST_H = [arc_heading(i) + wave(i, 0.0) for i in range(N)]
HEAD_REST = arc_heading(0) - 3.5 + HEAD_AMP * math.sin(2 * math.pi * HEAD_LEAD)

# Joints J0 (neck) … J11 (tail), walked back from the neck along the rest
# headings, then shifted so the whole animal — antennae to ultimate legs —
# sits centred on the canvas.
J = [(0.0, 0.0)]
for i in range(N):
    c, s = unit(REST_H[i])
    J.append((J[-1][0] - L * c, J[-1][1] - L * s))
HEAD_LEN = 9.0
front = (J[0][0] + (HEAD_LEN + 13.0) * unit(HEAD_REST)[0], J[0][1] + (HEAD_LEN + 13.0) * unit(HEAD_REST)[1])
back = (J[-1][0] - 13.0 * unit(REST_H[-1])[0], J[-1][1] - 13.0 * unit(REST_H[-1])[1])
SHIFT = (-(front[0] + back[0]) / 2 - 2.5, -(front[1] + back[1]) / 2 - 2.0)
J = [(x + SHIFT[0], y + SHIFT[1]) for x, y in J]

# ============================================================== skeleton
RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("trunk", None, J[ROOT], REST_H[5], 0.0)
# Forward chain: seg_5 … seg_0, each a bone from its rear joint to its front.
parent = "trunk"
for i in range(ROOT - 1, -1, -1):
    bone(f"s{i}", parent, J[i + 1], REST_H[i], L); parent = f"s{i}"
bone("head", "s0", J[0], HEAD_REST, HEAD_LEN)
# Back chain: seg_6 … seg_10, each a bone from its front joint to its rear.
parent = "trunk"
for i in range(ROOT, N):
    bone(f"s{i}", parent, J[i], REST_H[i] + 180.0, L); parent = f"s{i}"

def fwd_of(i):
    """A plate's rest forward heading."""
    return REST_H[i]
def seg_centre_rest(i):
    return ((J[i][0] + J[i + 1][0]) / 2, (J[i][1] + J[i + 1][1]) / 2)
def local_to_world(origin, heading, along, across):
    c, s = unit(heading)
    return (origin[0] + along * c - across * s, origin[1] + along * s + across * c)

# The head: its bone runs from the neck forward; the shield's centre, the
# forcipules' bases and the antennae's roots are points on it.
def head_pt(along, across): return local_to_world(J[0], HEAD_REST, along, across)
SIDES = (("l", -1), ("r", 1))     # the animal's left is -across (up the screen at rest)

# Antennae: three links from the front of the shield, splayed forward and out.
ANT = [6.2, 5.6, 5.0]
ANT_SPLAY, ANT_BEND = 42.0, 6.0
for sd, sg in SIDES:
    p = head_pt(8.9, sg * 1.3)
    h = HEAD_REST + sg * ANT_SPLAY
    for k, Lk in enumerate(ANT):
        b = bone(f"ant_{sd}{k}", "head" if k == 0 else f"ant_{sd}{k - 1}", p, h, Lk)
        p = b.end(); h += sg * ANT_BEND

# Forcipules: a base out and forward from under the shield, and a fang that
# curls back in so the pair meet in front of the head.
FC0, FC1 = 4.0, 6.0
for sd, sg in SIDES:
    b0 = bone(f"fc_{sd}0", "head", head_pt(6.4, sg * 3.6), HEAD_REST + sg * 50.0, FC0)
    bone(f"fc_{sd}1", f"fc_{sd}0", b0.end(), HEAD_REST - sg * 40.0, FC1)

# Ultimate legs: the long trailing pair off the last plate.
ULT = [7.6, 7.2]
for sd, sg in SIDES:
    back_h = REST_H[N - 1] + 180.0
    p = local_to_world(J[N], REST_H[N - 1], 0.6, sg * 2.8)
    b0 = bone(f"ult_{sd}0", f"s{N - 1}", p, back_h - sg * 16.0, ULT[0])
    bone(f"ult_{sd}1", f"ult_{sd}0", b0.end(), back_h - sg * 6.0, ULT[1])

# Legs: a pair per plate. Hip under the plate's edge, foot out past it — the
# front pairs raked forward and the rear trailing — and the knee on the
# forward side, so from above each leg is an arch out and back to the ground.
FEMUR, TIBIA = 4.4, 5.4
def rake(i): return lerp(3.0, -3.6, i / (N - 1))
def hip_local(i, sg): return (0.4, sg * HW[i] * 0.78)
def foot_rest_local(i, sg): return (rake(i) - 1.2, sg * (HW[i] + 4.6))
LEGCYC = 2                        # steps per crawl loop
KL = 0.16                         # leg-to-leg lag down the body
DUTY = 0.58
STRIDE, TUCK = 2.8, 2.6
def leg_phase(i, sg): return -i * KL + (0.0 if sg < 0 else 0.5)
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
for i in range(N):
    for sd, sg in SIDES:
        c = seg_centre_rest(i)
        hip = local_to_world(c, fwd_of(i), *hip_local(i, sg))
        foot = local_to_world(c, fwd_of(i), *crawl_foot(i, sg, 0.0))
        # the knee on the forward side of the hip→foot line
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
PLATE_FILL = ["$ember.dark", "$chitin", "$chitin", "$chitin", "$chitin", "$chitin",
              "$chitin", "$chitin", "$chitin", "$chitin", "$ember.dark"]
BAND_FILL = "$oxblood"
FEMUR_FILL, TIBIA_FILL = "$ember.dark", "$timber"

def plate_shape(hw):
    return poly([(3.5, -hw * 0.78), (3.95, -hw * 0.3), (3.95, hw * 0.3), (3.5, hw * 0.78), (2.2, hw * 0.97),
                 (-1.0, hw), (-3.5, hw * 0.9), (-3.9, hw * 0.55), (-3.9, -hw * 0.55), (-3.5, -hw * 0.9),
                 (-1.0, -hw), (2.2, -hw * 0.97)])
def band_shape(hw):
    return poly([(-2.5, -hw * 0.93), (-2.1, -hw * 0.5), (-2.1, hw * 0.5), (-2.5, hw * 0.93),
                 (-3.5, hw * 0.9), (-3.9, hw * 0.55), (-3.9, -hw * 0.55), (-3.5, -hw * 0.9)])

# ---- ultimate legs, under everything at the tail
for sd, sg in SIDES:
    at, a = on_bone(f"ult_{sd}0"); put(f"ult_{sd}0", f"ult_{sd}0", at, a, bar(ULT[0], 2.4, 1.9), "$ember.dark", INK_HAIR)
    at, a = on_bone(f"ult_{sd}1"); put(f"ult_{sd}1", f"ult_{sd}1", at, a, bar(ULT[1], 1.8, 0.5), "$oxblood", INK_HAIR)

# ---- legs, rear pairs first so the front ones lie over them
for i in range(N - 1, -1, -1):
    for sd, sg in SIDES:
        at, a = on_bone(f"leg_{i}{sd}_t"); put(f"leg_{i}{sd}_t", f"leg_{i}{sd}_t", at, a, bar(TIBIA, 1.7, 0.7), TIBIA_FILL, INK_HAIR)
        at, a = on_bone(f"leg_{i}{sd}_f"); put(f"leg_{i}{sd}_f", f"leg_{i}{sd}_f", at, a, bar(FEMUR, 2.4, 1.9), FEMUR_FILL, INK_HAIR)

# ---- antennae, then the forcipules over them — the fangs are the read — all
# with their roots under the shield
for sd, sg in SIDES:
    for k, Lk in enumerate(ANT):
        at, a = on_bone(f"ant_{sd}{k}")
        put(f"ant_{sd}{k}", f"ant_{sd}{k}", at, a, bar(Lk, *[(1.8, 1.5), (1.5, 1.1), (1.1, 0.6)][k]),
            ["$spore.dark", "$spore.dark", "$spore.dark2"][k], INK_HAIR)
def sickle(Lf, c, w0=1.25, bend=0.055):
    """A fang along +x, `Lf` long, curving toward `c` (±1) and tapering to a point."""
    xs = [Lf * k / 6 for k in range(7)]
    mid = [c * bend * x * x for x in xs]
    half = [w0 * (1 - x / Lf) + 0.12 for x in xs]
    outer = [(x, m - c * h) for x, m, h in zip(xs, mid, half)]
    inner = [(x, m + c * h) for x, m, h in zip(xs, mid, half)]
    return poly([(-0.5, -c * w0 * 0.8)] + outer[:-1] + [(Lf + 0.2, mid[-1] + c * 0.2)] + inner[::-1][1:] + [(-0.5, c * w0 * 0.8)])
for sd, sg in SIDES:
    at, a = on_bone(f"fc_{sd}0"); put(f"fc_{sd}0", f"fc_{sd}0", at, a, bar(FC0, 3.4, 2.6), "$oxblood", INK_HAIR)
    at, a = on_bone(f"fc_{sd}1")
    c = -sg  # the fang curls toward the midline
    put(f"fc_{sd}1", f"fc_{sd}1", at, a, sickle(FC1, c), "$bone", INK_HAIR)
    at, a = on_bone(f"fc_{sd}1", FC1 - 0.5, c * 0.055 * (FC1 - 0.5) ** 2)
    put(f"venom_{sd}", f"fc_{sd}1", at, 0.0, circ(1.05), "$spore.light")

# ---- the trunk, tail plate first so each plate's rear margin lies over the next
for i in range(N - 1, -1, -1):
    c = seg_centre_rest(i)
    h = fwd_of(i)
    put(f"seg_{i}", f"s{i}", c, h, plate_shape(HW[i]), PLATE_FILL[i], INK_HAIR)
    put(f"band_{i}", f"s{i}", c, h, band_shape(HW[i]), BAND_FILL)
    put(f"gloss_{i}", f"s{i}", local_to_world(c, h, 1.2, -HW[i] * 0.2), h, ell(1.2, HW[i] * 0.64), "$white@0.3")

# ---- the head shield: maroon, the organ on its crown, the ocelli at its
# front corners
HEAD_SHAPE = poly([(-1.6, -4.6), (1.2, -6.0), (4.6, -6.2), (7.4, -5.0), (8.9, -2.6), (9.3, 0.0),
                   (8.9, 2.6), (7.4, 5.0), (4.6, 6.2), (1.2, 6.0), (-1.6, 4.6), (-2.2, 0.0)])
put("head", "head", J[0], HEAD_REST, HEAD_SHAPE, "$oxblood", INK_THIN)
put("head_gloss", "head", head_pt(5.0, -2.8), HEAD_REST, ell(2.6, 1.3), "$white@0.2")
use("organ", "head", head_pt(3.4, 0.0), "ss.lib.organ", scale=0.62)
for sd, sg in SIDES:
    put(f"eye_{'a' if sg < 0 else 'b'}", "head", head_pt(7.0, sg * 4.3), HEAD_REST + sg * 20, ell(1.05, 0.8), "$dead")

RIG.check()
HEAD_GROUP = ["head", "head_gloss", "organ", "eye_a", "eye_b"]

# ============================================================== posing
# A pose is asked for as plain numbers and turned into the rig's pose here:
#   seg      eleven heading deltas off the rest (degrees)
#   head     the head's heading delta off the rest
#   trunk    (along, across) travel of the root, in the axis frame
#   feet     fn(i, sg) -> (along, across) foot in its plate's frame
#   ant      fn(sd, k) -> delta, fc: fn(sd, k) -> delta, ult: fn(sd, k) -> delta
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
        nx, ny = w["head"][0], w["head"][1]
        ex, ey = nx - J[0][0], ny - J[0][1]
        n_ = axis_vec(0.0, 1.0)
        off = ex * n_[0] + ey * n_[1]
        dx -= keep_head_on_axis * off * n_[0]; dy -= keep_head_on_axis * off * n_[1]
        pose["body"] = (dx, dy, 0.0)
    for sd, sg in SIDES:
        for k in range(3):
            if ant: pose[f"ant_{sd}{k}"] = ant(sd, sg, k)
        for k in range(2):
            if fc: pose[f"fc_{sd}{k}"] = fc(sd, sg, k)
            if ult: pose[f"ult_{sd}{k}"] = ult(sd, sg, k)
    world = solve(pose)
    for i in range(N):
        bx, by, ba = world[f"s{i}"]
        if i < ROOT:
            fwd = ba; c = (bx + L / 2 * math.cos(R(ba)), by + L / 2 * math.sin(R(ba)))
        else:
            fwd = ba - 180.0; c = (bx + L / 2 * math.cos(R(ba)), by + L / 2 * math.sin(R(ba)))
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
        # the pair working in antiphase, each a whip: the tip a beat behind the root
        ph = 0.0 if sg < 0 else 0.5
        return [12.0, 9.0, 11.0][k] * cyc(t, ph - 0.12 * k)
    return f
def fc_crawl(t):
    def f(sd, sg, k):
        # the fangs working open and shut twice a loop, the tips lagging the bases
        return sg * [5.0, 12.0][k] * (0.5 + 0.5 * cyc(2 * t, 0.1 - 0.08 * k))
    return f
def ult_crawl(t):
    def f(sd, sg, k):
        # riding the tail's wave, a beat later, and the tips later still
        return [14.0, 16.0][k] * math.sin(2 * math.pi * (t - (N + 0.8 + k * 1.2) * KB))
    return f
def crawl_seg(t): return [wave(i, t) - wave(i, 0.0) for i in range(N)]
def crawl_head(t):
    return HEAD_AMP * (math.sin(2 * math.pi * (t + HEAD_LEAD)) - math.sin(2 * math.pi * HEAD_LEAD))
def zeroed(fn_t, t):
    """A whip's crawl deltas less their value at t=0, so the crawl's first frame is the drawn rest pose."""
    f, f0 = fn_t(t), fn_t(0.0)
    return lambda sd, sg, k: f(sd, sg, k) - f0(sd, sg, k)
def crawl_pose(t):
    surge = 0.7 * (cyc(2 * t, 0.0) - cyc(0.0, 0.0))
    return build(crawl_seg(t), crawl_head(t), (surge, 0.0),
                 lambda i, sg: crawl_foot(i, sg, t), zeroed(ant_crawl, t), zeroed(fc_crawl, t), zeroed(ult_crawl, t))

REST_FEET = lambda i, sg: crawl_foot(i, sg, 0.0)

# ---- the coiled pose: the trunk thrown into an S behind a head held on the
# line, drawn back down it, reared (the head shield swells), the forcipules
# wide, the antennae laid back, the legs braced wide and the ultimate legs
# lifted apart
COIL_S = [36.0 * math.cos(2 * math.pi * (i + 0.4) / 9.4) for i in range(N)]
AIM_HEAD = AX - HEAD_REST     # the head turned exactly onto the line it will run
def coil_feet(g):
    def f(i, sg):
        a, c = REST_FEET(i, sg)
        return (lerp(a, rake(i) * 0.4 - 0.8, g), c + sg * 2.2 * g)
    return f
# The fangs: a pair of deltas (base, fang), + turning each side outward.
FC_OPEN = (16.0, 34.0)
FC_SHUT = (-6.0, -14.0)
def coil_bits(g, shiver=0.0):
    ant = lambda sd, sg, k: -sg * [26.0, 12.0, 8.0][k] * g + shiver * (1 if k % 2 else -1) * 3.0
    fc = lambda sd, sg, k: sg * FC_OPEN[k] * g
    ult = lambda sd, sg, k: (-sg * 22.0 * g if k == 0 else -sg * 10.0 * g)
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
    ant = lambda sd, sg, k: lerp(-sg * [26.0, 12.0, 8.0][k] * max(g, 0.0) * (1 - snap) + sg * [-30.0, -14.0, -10.0][k] * snap, 0.0, back)
    fc = lambda sd, sg, k: lerp(lerp(sg * FC_OPEN[k], sg * FC_SHUT[k], snap), 0.0, back)
    ult = lambda sd, sg, k: lerp((-sg * 22.0 if k == 0 else -sg * 10.0), (sg * 8.0 if k == 0 else sg * 14.0), smooth(0.05, 0.4, t)) * (1 - back)
    seg = [COIL_S[i] * g for i in range(N)]
    # the feet: from the braced stance, thrown back as it lunges, home at the end
    def feet(i, sg):
        a0, c0 = coil_feet(1.0)(i, sg)
        a1, c1 = REST_FEET(i, sg)
        mid = (rake(i) - 3.0, c1 - sg * 1.0)
        u = smooth(0.0, 0.3, t); v = smooth(0.35, 1.0, t)
        a = lerp(lerp(a0, mid[0], u), a1, v); c = lerp(lerp(c0, mid[1], u), c1, v)
        return (a, c)
    return build(seg, AIM_HEAD * g, (lunge, 0.0), feet, ant, fc, ult,
                 keep_head_on_axis=max(0.0, min(1.0, abs(g))))

# ---- the dive pose, held through the whole crossing: the trunk laid straight
# down the line, every leg folded back flat along its plate, the antennae laid
# back over the shield, the fangs shut, the ultimate legs together
def dive_feet(i, sg):
    return (-5.2, sg * (HW[i] * 0.95 + 1.2))
DIVE_ANT = lambda sd, sg, k: -sg * [44.0, 10.0, 4.0][k]
DIVE_FC = lambda sd, sg, k: sg * FC_SHUT[k]
DIVE_ULT = lambda sd, sg, k: (sg * 12.0 if k == 0 else sg * 4.0)
DIVE_SEG = [(AX - REST_H[i]) * 0.9 for i in range(N)]    # laid nearly straight down the line
DIVE_HEAD = AX - HEAD_REST

def lerp_fn(f0, f1, u):
    return lambda sd, sg, k: lerp(f0(sd, sg, k), f1(sd, sg, k), u(sd, sg, k) if callable(u) else u)

def submerge_pose(t):
    # every plate goes from the coil to the dive as the wave reaches it, and
    # overshoots — the crawl's own wave spent once and hard
    seg = []
    for i in range(N):
        u = smooth(0.04 + 0.055 * i, 0.3 + 0.055 * i, t)
        kick = 18.0 * math.sin(math.pi * u) * math.cos(math.pi * i / 3.2)
        seg.append(lerp(COIL_S[i], DIVE_SEG[i], u) + kick)
    uh = smooth(0.0, 0.3, t)
    head = lerp(AIM_HEAD, DIVE_HEAD, uh) - 10.0 * math.sin(math.pi * uh)
    drive = lerp(-4.4, 2.0, smooth(0.0, 0.35, t))
    def feet(i, sg):
        u = smooth(0.06 + 0.06 * i, 0.26 + 0.06 * i, t)
        a0, c0 = coil_feet(1.0)(i, sg); a1, c1 = dive_feet(i, sg)
        return (lerp(a0, a1, u), lerp(c0, c1, u))
    ant0, fc0, ult0 = coil_bits(1.0)
    ua = smooth(0.0, 0.3, t)
    uu = smooth(0.5, 1.0, t)
    return build(seg, head, (drive, 0.0), feet, lerp_fn(ant0, DIVE_ANT, ua), lerp_fn(fc0, DIVE_FC, smooth(0.0, 0.2, t)),
                 lerp_fn(ult0, DIVE_ULT, uu), keep_head_on_axis=1.0 - smooth(0.0, 0.5, t))
def dive_pose():
    return submerge_pose(1.0)

# ---- surface: from the dive, the head rears first and the wave runs out of
# the body behind it; each pair of legs throws itself wide as its plate
# clears, the fangs open on the way up, and it settles on the rest pose
def surface_pose(t):
    seg = []
    for i in range(N):
        u = smooth(0.08 + 0.05 * i, 0.4 + 0.05 * i, t)
        kick = -14.0 * math.sin(math.pi * u) * math.cos(math.pi * i / 3.2)
        seg.append(lerp(DIVE_SEG[i], 0.0, u) + kick)
    uh = smooth(0.0, 0.5, t)
    head = lerp(DIVE_HEAD, 0.0, uh) + 12.0 * math.sin(math.pi * uh)
    rise = lerp(2.0, 0.0, smooth(0.0, 0.6, t))
    def feet(i, sg):
        u = smooth(0.1 + 0.05 * i, 0.45 + 0.05 * i, t)
        a0, c0 = dive_feet(i, sg); a1, c1 = REST_FEET(i, sg)
        wide = 3.2 * math.sin(math.pi * u)
        return (lerp(a0, a1, u) + 1.2 * math.sin(math.pi * u), lerp(c0, c1, u) + sg * wide)
    ua = smooth(0.0, 0.7, t)
    fc_open = lambda sd, sg, k: lerp(DIVE_FC(sd, sg, k), 0.0, smooth(0.0, 0.8, t)) + sg * FC_OPEN[k] * 1.1 * math.sin(math.pi * smooth(0.05, 0.8, t))
    ant = lambda sd, sg, k: lerp(DIVE_ANT(sd, sg, k), 0.0, ua) + sg * [16.0, 8.0, 10.0][k] * math.sin(math.pi * ua)
    ult = lambda sd, sg, k: lerp(DIVE_ULT(sd, sg, k), 0.0, smooth(0.45, 1.0, t)) - sg * 14.0 * math.sin(math.pi * smooth(0.45, 1.0, t))
    return build(seg, head, (rise, 0.0), feet, ant, fc_open, ult)

# ---- death: the fangs close on empty air, then a slack runs head to tail —
# each plate curling as it passes, its legs folding in — until the ultimate
# legs give last. Still from 0.85.
# A curl is a bend, not a turn: the heading changes steadily down the body,
# the front plates turning one way and the rear the other about the root.
DEATH_CURL = [-7.5 * (i - 5.0) for i in range(N)]
def death_pose(t):
    t = min(t, 0.85)
    jerk = math.sin(math.pi * smooth(0.0, 0.22, t))
    seg = []
    for i in range(N):
        u = smooth(0.16 + 0.042 * i, 0.38 + 0.042 * i, t)
        seg.append(lerp(0.0, DEATH_CURL[i], u) + 8.0 * math.sin(math.pi * u))
    head = -10.0 * jerk + lerp(0.0, DEATH_CURL[0] + 16.0, smooth(0.12, 0.4, t))
    def feet(i, sg):
        u = smooth(0.2 + 0.04 * i, 0.4 + 0.04 * i, t)
        a, c = REST_FEET(i, sg)
        return (lerp(a, -2.4, u), lerp(c, sg * (HW[i] * 0.8 + 1.6), u))
    snap = smooth(0.0, 0.14, t)
    fc = lambda sd, sg, k: sg * FC_OPEN[k] * 0.8 * jerk + sg * FC_SHUT[k] * 1.2 * snap
    ant = lambda sd, sg, k: sg * [18.0, 10.0, 12.0][k] * jerk - sg * [30.0, 20.0, 16.0][k] * smooth(0.3, 0.6, t)
    ult = lambda sd, sg, k: sg * 16.0 * math.sin(math.pi * smooth(0.55, 0.85, t)) - [16.0, 24.0][k] * smooth(0.6, 0.85, t)
    return build(seg, head, (lerp(0.0, -1.5, smooth(0.2, 0.7, t)), 0.0), feet, ant, fc, ult)

# ============================================================== clips
tracks = RIG.tracks
def head_scale(fn): return [(p, "scale", fn) for p in HEAD_GROUP if p != "organ"] + [("organ", "scale", fn)]
def plate_scale(fn_i):
    return [(f"seg_{i}", "scale", (lambda i: lambda t: fn_i(i, t))(i)) for i in range(N)] + \
           [(f"band_{i}", "scale", (lambda i: lambda t: fn_i(i, t))(i)) for i in range(N)]
def glow(fn): return [("venom_l", "scale", fn), ("venom_r", "scale", fn)]

# The coil's rear: the shield swells toward the camera and the plates
# fatten as the body piles into itself, most at the tail.
REAR = 0.14
def coil_rear(t): return 1.0 + REAR * wind(t)
def coil_fat(i, t): return 1.0 + (0.03 + 0.05 * i / (N - 1)) * wind(t)
def strike_g(t):
    g = lerp(1.0, -0.32, smooth(0.0, 0.34, t)); return lerp(g, 0.0, smooth(0.34, 1.0, t))
def strike_rear(t): return 1.0 + REAR * max(0.0, strike_g(t)) - 0.04 * math.sin(math.pi * smooth(0.1, 0.6, t))
def strike_fat(i, t): return 1.0 + (0.03 + 0.05 * i / (N - 1)) * max(0.0, strike_g(t))
DIVE_SINK = 0.88
def sub_rear(t): return lerp(1.0 + REAR, DIVE_SINK, smooth(0.0, 0.32, t))
def sub_fat(i, t):
    u = smooth(0.04 + 0.055 * i, 0.3 + 0.055 * i, t)
    return lerp(1.0 + 0.03 + 0.05 * i / (N - 1), 0.95, u)
def surf_rear(t):
    u = smooth(0.0, 0.5, t)
    return lerp(DIVE_SINK, 1.0, u) + 0.16 * math.sin(math.pi * u)
def surf_fat(i, t):
    u = smooth(0.08 + 0.05 * i, 0.4 + 0.05 * i, t)
    return lerp(0.95, 1.0, u) + 0.05 * math.sin(math.pi * u)
def death_rear(t):
    t = min(t, 0.85); return 1.0 + 0.08 * math.sin(math.pi * smooth(0.0, 0.22, t)) - 0.06 * smooth(0.3, 0.7, t)
def death_fat(i, t):
    t = min(t, 0.85); u = smooth(0.16 + 0.042 * i, 0.38 + 0.042 * i, t)
    return 1.0 - 0.07 * u

animations = {}
TS_CRAWL = keyset(36)
animations["crawl"] = {
    "description": "The walk, and the idle the game plays at whatever pace it is covering: a bend travels down the trunk head to tail once a loop, the head leading it; under it every pair of legs steps twice — each foot pushing back along its plate while it is down and swinging forward drawn in while it is up — in a metachronal wave running head to tail, left and right in antiphase; the antennae work in turn, each a whip with the tip a beat behind; the forcipules flex; the ultimate legs ride the tail a beat later. The first frame is the rest pose.",
    "duration": CRAWL,
    "tracks": tracks(crawl_pose, TS_CRAWL, glow(lambda t: 1.0 + 0.12 * (0.5 + 0.5 * cyc(2 * t, 0.25)) - 0.12 * (0.5 + 0.5 * cyc(0.0, 0.25)))),
}
TS_COIL = keyset(30)
animations["coil"] = {
    "description": "Winding up, from the rest pose. The trunk throws itself into an S behind a head held on the line it has chosen and drawn back down it; the head rears (the shield swells toward you) and the plates fatten as the body piles into itself, most at the tail; the forcipules open wide, the antennae lay back, the legs brace out and the ultimate legs lift apart. Wound rather than eased — a fast first draw, a slow creep with a shiver in it, a last snatch — and held on the final frame, because the release is the dash. The game stretches it to the brace.",
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
    "description": "The wave that carries this body carries it one last time and nothing comes back: the head jerks up and the forcipules close on empty air, then a slack runs head to tail — each plate curling as it passes and sinking, its two legs folding in under it — until the ultimate legs at the far end give last; the body lies in a curl, the organ and the venom gone dim. Still from 0.85.",
    "duration": 0.7,
    "tracks": tracks(death_pose, TS_DEATH, head_scale(death_rear) + plate_scale(death_fat)
                     + [("organ", "opacity", lambda t: 1.0 - 0.7 * smooth(0.3, 0.8, min(t, 0.85))),
                        ("venom_l", "opacity", lambda t: 1.0 - 0.75 * smooth(0.2, 0.7, min(t, 0.85))),
                        ("venom_r", "opacity", lambda t: 1.0 - 0.75 * smooth(0.2, 0.7, min(t, 0.85)))]),
}
TS_SUB = keyset(20)
animations["submerge"] = {
    "description": "Going into the earth, and the release a burrowing body plays in place of `strike` — so it opens on the coil's last frame exactly. The head drives down (the shield sinks away from you) and the body follows it in as the crawl's own wave spent once and hard, head to tail: each plate throws the S out as the wave reaches it and lies straight down the line, its legs folding back flat along it, the antennae laying back over the shield and the fangs shutting. The last frame is what the body wears for the whole crossing — a centipede streamlined for the earth, sunk a little, legs stowed — and is exactly where `surface` begins.",
    "duration": 0.34,
    "tracks": tracks(submerge_pose, TS_SUB, head_scale(sub_rear) + plate_scale(sub_fat) + glow(lambda t: lerp(1.45, 1.0, smooth(0.0, 0.4, t)))),
}
TS_SURF = keyset(18)
animations["surface"] = {
    "description": "Coming back out, and the reverse of `submerge` in shape rather than in frames: from the dive's last frame the head rears first (the shield swells up toward you and settles), and the wave runs out of the body behind it; each pair of legs throws itself wide as its plate clears, the forcipules open on the way up and the antennae flare, the ultimate legs last. Ends on the rest pose. Played where the ground bulges.",
    "duration": 0.3,
    "tracks": tracks(surface_pose, TS_SURF, head_scale(surf_rear) + plate_scale(surf_fat)),
}

# ============================================================== states
LEG_IDS = [f"leg_{i}{sd}_{j}" for i in range(N) for sd, _ in SIDES for j in ("f", "t")]
ENRAGED_PLATES = ["$oxblood", "$ember.dark", "$chitin", "$chitin", "$chitin.light", "$chitin.light",
                  "$chitin.light", "$chitin", "$chitin", "$ember.dark", "$oxblood"]
enraged_set = {}
for i, f in enumerate(ENRAGED_PLATES): enraged_set[f"seg_{i}.fill"] = f
for i in range(N): enraged_set[f"band_{i}.fill"] = "$coral.dark"
for lid in LEG_IDS: enraged_set[f"{lid}.fill"] = "$bone.dark" if lid.endswith("_f") else "$bone.dark2"
enraged_set.update({
    "ult_l0.fill": "$bone.dark", "ult_r0.fill": "$bone.dark", "ult_l1.fill": "$bone", "ult_r1.fill": "$bone",
    "head.fill": "$dead", "head_gloss.fill": "$white@0.12",
    "fc_l0.fill": "$bone", "fc_r0.fill": "$bone", "fc_l1.fill": "$white", "fc_r1.fill": "$white",
    "venom_l.fill": "$white", "venom_r.fill": "$white",
    "organ.scale": 0.72,
})
FINAL_PLATES = ["$sand", "$sand.light", "$sand", "$sand.light", "$sand", "$sand.light",
                "$sand", "$sand.light", "$sand", "$sand.light", "$sand"]
final_set = {}
for i, f in enumerate(FINAL_PLATES): final_set[f"seg_{i}.fill"] = f
for i in range(N): final_set[f"band_{i}.fill"] = "$ember"
for i in range(N): final_set[f"gloss_{i}.fill"] = "$white@0.08"
for lid in LEG_IDS: final_set[f"{lid}.fill"] = "$sand.dark" if lid.endswith("_f") else "$soil.light"
final_set.update({
    "ult_l0.fill": "$sand.dark", "ult_r0.fill": "$sand.dark", "ult_l1.fill": "$soil.light", "ult_r1.fill": "$soil.light",
    "ant_l0.fill": "$sand.light", "ant_r0.fill": "$sand.light", "ant_l1.fill": "$sand", "ant_r1.fill": "$sand",
    "ant_l2.fill": "$sand", "ant_r2.fill": "$sand",
    "head.fill": "$sand.dark", "head_gloss.fill": "$white@0.08",
    "fc_l0.fill": "$bone", "fc_r0.fill": "$bone", "fc_l1.fill": "$bone.light", "fc_r1.fill": "$bone.light",
    "venom_l.fill": "$venom.light", "venom_r.fill": "$venom.light",
})
variants = {
    "enraged": {
        "description": "Phase two: the body goes hot from the middle out — the plates at the centre flare to the lightest amber and the margins burn crimson — the fringe of legs bleaches to bone, the head blackens, and the venom at the claw tips stops being a highlight and starts being the brightest thing on the creature.",
        "scale": 1.08,
        "set": enraged_set,
    },
    "final": {
        "description": "Phase three: it has been living in the earth for the last third of the fight and the earth is all over it. The plates have gone the colour of the ground, dulled and caked, the legs and the antennae with them, and the only things on the body still the colour of an animal are the two venom claws and the light coming up between the plates — every rear margin a seam of ember — which is the read: it is not brighter, it is buried, and what you can still see of it is the part that kills you.",
        "scale": 1.1,
        "set": final_set,
    },
}

# ============================================================== document
DESCRIPTION = (
    "What an ant nest is actually afraid of, and it was already down here before you were. A centipede seen from above along its travel axis "
    "and turned by the game rather than mirrored; the rest pose's axis sits 18.6 degrees above +x, which is the `faceOffset` the game pairs with "
    "this document. Eleven amber plates, each banded maroon at its rear margin, under a maroon head shield carrying the hive's organ and two "
    "ocellus clusters; forcipules — a bone base and a curled fang with a venom bead — meeting in front of it; three-link antennae; a pair of "
    "tapered, jointed legs to every plate, a step darker than the plates so the body reads first, raked forward at the head and trailing at the "
    "tail; and the long ultimate legs trailing behind. "
    "Built on a skeleton (scripts/scolopend.py): the spine is a chain rooted mid-body, so a bend put in at the head travels down it and nothing "
    "parts at a joint; every leg is a femur and a tibia solved each frame to a foot. `crawl` is a body wave head to tail over a metachronal wave "
    "of the legs, and its first frame is the rest pose. `coil` and `strike` are the windup and its release: the trunk throws itself into an S "
    "behind a head held on the line, rears and fattens, and `strike` opens on exactly `coil`'s last frame and settles on the rest pose. "
    "Slimmer than the Courser at radius 40: the burrow's narrowest doorway is 130px. Gameplay radius 40. The `death` clip runs the crawl's own "
    "wave head to tail one last time and lets nothing come back: the forcipules close on empty air first, and every plate curls and sinks as "
    "the slack reaches it.\n\n"
    "`submerge` and `surface` are the pair the game's burrowing dash needs. For this body the dive *is* the release (EnemySystem plays it "
    "where another body would play `strike`), so it too opens on the coil's last frame; its last frame is held for the whole crossing, so it "
    "is a streamlined centipede with its legs stowed, and `surface` opens exactly there. They are written as one shape each rather than as one "
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
