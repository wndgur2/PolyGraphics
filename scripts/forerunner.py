"""The Forerunner — a tiger beetle that runs blind and stops to look.

    python3 scripts/forerunner.py        # rewrites apps/ss/assets/ss-enemy-forerunner.json

The pan's second boss. The game runs it as a sprint and a rest (feelers:
`EnemyType.hopSpeed` 300 for 0.4s, `hopRest` 0.6s) and it fires a fan of glass
only in the rest (`fireAnim: 'spit'`); it is turned by the game rather than
mirrored (`turns: true`), so it is drawn from above facing +x, like the Courser.

It was hand-placed: six two-rect legs swung about their own centres, a flat
ellipse body in dull moss with no bob, and a mean colour that sat at 1.18
against the pan's sand. This rebuilds it on the shared rig (`rig.py`):

  - a skeleton: the body is a root bone that surges, sways and yaws with each
    tripod's push; the head is a bone on it that counter-turns; each antenna
    is a chain of three that streams and whips with a lag down its length; the
    mandibles are hinged bones; each leg is a femur and a tibia solved every
    frame to a foot on the ground (two-bone IK) with the tarsus off the foot,
    so a planted foot stays planted while the world slides under it
  - the drawing a tiger beetle actually has: a head wider than the pronotum
    with two huge bulging eyes, a white labrum, sickle mandibles that cross,
    a narrow barrel pronotum, long parallel elytra with cream lunules, and
    legs as long as the body
  - tarnished verdigris over moss darks — still the pan's one green besides the
    Locust, lifted to the colour a tiger beetle actually is, which is also
    what gets it off the sand

The elytra are bones hinged at the shoulder and the hind wings lie folded back
under them at rest, so `enraged` and the death can open them.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, INK_BOLD, write_doc)

# ============================================================== rig
# Canvas 128×88, origin at the centre, +x forward, +y down ("d" side), "u" is -y.
RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("body", None, (-4.0, 0.0), 0.0)
bone("head", "body", (17.0, 0.0), 0.0, 12.0)
HINGE = {"u": (5.6, -1.4), "d": (5.6, 1.4)}
for s in ("u", "d"):
    bone(f"ely_{s}", "body", HINGE[s], 180.0, 46.0)
    bone(f"wing_{s}", "body", (2.0, -3.0 if s == "u" else 3.0), 180.0, 30.0)

# Mandibles: hinged at the front corners of the head, sickles that cross.
MAND = {"u": ((29.0, -3.2), -12.0), "d": ((29.0, 3.2), 12.0)}
for s, (at, h) in MAND.items():
    bone(f"mand_{s}", "head", at, h, 14.0)

# Antennae: three links from between the eye and the mandible, forward and out.
ANT = [(6.0, 38.0), (6.5, 30.0), (6.5, 22.0)]  # (length, degrees off the axis)
for s, sg in (("u", -1), ("d", 1)):
    p, parent = (28.0, sg * 5.0), "head"
    for i, (L, off) in enumerate(ANT):
        b = bone(f"ant_{s}_{i}", parent, p, sg * off, L)
        p, parent = b.end(), b.name

# Legs: hip (coxa), femur and tibia solved to a foot, and a tarsus off it.
# Front pair forward and out, the middle pair straight out, the hind pair —
# the longest — trailing back: a tiger beetle is mostly leg.
LEGS = {  # name: (hip, rest foot, femur, tibia, tarsus, tarsus heading off the tibia)
    "f": ((11.5, 4.6), (27.0, 21.0), 10.5, 13.0, 8.0, -24.0),
    "m": ((6.5, 5.6), (5.0, 29.0), 12.0, 15.0, 9.0, 22.0),
    "h": ((2.0, 5.4), (-21.0, 24.5), 14.0, 18.5, 12.0, 14.0),
}
SIDES = {"u": -1, "d": 1}
def leg_spec(s, n):
    hip, foot, lf, lt, ls, toff = LEGS[n]
    sg = SIDES[s]
    return (hip[0], sg * hip[1]), (foot[0], sg * foot[1]), lf, lt, ls, toff * sg
def bend_of(s, n):
    """The IK bend that puts the knee outboard of the hip→foot line (away from the midline)."""
    hip, foot, lf, lt, _, _ = leg_spec(s, n)
    best = None
    for b in (1, -1):
        hf, _ = ik2(hip, foot, lf, lt, b)
        ky = hip[1] + lf * math.sin(R(hf))
        if best is None or abs(ky) > best[0]: best = (abs(ky), b)
    return best[1]
LEG_IDS = [(s, n) for n in ("h", "m", "f") for s in ("u", "d")]
for s, n in LEG_IDS:
    hip, foot, lf, lt, ls, toff = leg_spec(s, n)
    hf, ht = ik2(hip, foot, lf, lt, bend_of(s, n))
    bone(f"{s}{n}_femur", "body", hip, hf, lf)
    bone(f"{s}{n}_tibia", f"{s}{n}_femur", B[f"{s}{n}_femur"].end(), ht, lt)
    bone(f"{s}{n}_tarsus", f"{s}{n}_tibia", B[f"{s}{n}_tibia"].end(), ht + toff, ls)

RIG.seal()
solve = RIG.solve
put, use, on_bone = RIG.put, RIG.use, RIG.on_bone

# ============================================================== parts
def mirror_pts(pts): return [(x, -y) for x, y in pts]
def rel(pts, origin): return [(x - origin[0], y - origin[1]) for x, y in pts]

# ---- legs, under everything: dark moss femora, darker tibiae, near-black tarsi
for s, n in LEG_IDS:
    L = B
    at, a = on_bone(f"{s}{n}_tarsus"); put(f"leg_{s}{n}_tarsus", f"{s}{n}_tarsus", at, a, bar(L[f"{s}{n}_tarsus"].length, 1.4, 0.9, 0.4), "$verdigris.dark2", INK_HAIR)
    at, a = on_bone(f"{s}{n}_tibia"); put(f"leg_{s}{n}_tibia", f"{s}{n}_tibia", at, a, bar(L[f"{s}{n}_tibia"].length, 2.0, 1.4), "$verdigris.dark", INK_HAIR)
    at, a = on_bone(f"{s}{n}_femur"); put(f"leg_{s}{n}_femur", f"{s}{n}_femur", at, a, bar(L[f"{s}{n}_femur"].length, 3.0, 2.2), "$verdigris", INK_HAIR)
    at, a = on_bone(f"{s}{n}_tibia"); put(f"leg_{s}{n}_knee", f"{s}{n}_tibia", at, 0.0, circ(1.4), "$verdigris.light")

# ---- hind wings, folded back under the elytra at rest; enraged and the death
# swing them out from under
WING = [(0, 0), (-6, -2.6), (-16, -5.4), (-26, -6.4), (-32, -5.2), (-34, -2.6), (-30, 0.2), (-18, 1.6), (-6, 1.4)]
for s in ("u", "d"):
    pts = WING if s == "u" else mirror_pts(WING)
    at, a = on_bone(f"wing_{s}")
    put(f"hindwing_{s}", f"wing_{s}", at, 0.0, poly(pts), "$husk@soft", INK_HAIR)
    vein = [(-2, -0.4), (-20, -4.2), (-30, -4.0), (-20, -3.2), (-2, 0.4)]
    put(f"hindvein_{s}", f"wing_{s}", at, 0.0, poly(vein if s == "u" else mirror_pts(vein)), "$moss.dark@soft")

# ---- the abdomen, under the elytra (seen when they open, and in `final`)
put("abdomen", "body", (-17.0, 0.0), 0.0, ell(23.0, 11.5), "$moss.dark", INK_THIN)
for i, x in enumerate((-4.0, -11.0, -18.0, -25.0, -32.0)):
    w = 11.5 * math.sqrt(max(0.0, 1 - ((x + 17.0) / 23.0) ** 2))
    put(f"segment_{i}", "body", (x, 0.0), 0.0, rect(1.1, 2 * w - 1.0, 0.5), "$ink@soft")

# ---- the elytra: each a bone hinged at the shoulder
ELY_U = [(6.4, -0.3), (5.8, -6.5), (4.6, -10.6), (2.6, -13.0), (-2.0, -14.0), (-12.0, -14.4), (-22.0, -14.0),
         (-30.0, -12.4), (-36.0, -9.4), (-40.0, -5.6), (-42.0, -2.2), (-42.0, -0.3)]
# Cream lunules: a humeral comma, a marginal spot, the middle band hooking in
# from the margin, a disc spot, and the apical crescent — the campestris marks.
MAC_U = {
    "humeral": [(3.8, -12.6), (0.4, -13.8), (-3.6, -13.6), (-4.4, -11.8), (-2.0, -11.2), (0.6, -10.8), (2.4, -9.0), (3.6, -9.8)],
    "margin": [(-7.4, -14.0), (-11.8, -14.2), (-12.4, -11.8), (-9.6, -11.0), (-7.0, -11.8)],
    "band": [(-15.4, -14.2), (-21.0, -14.0), (-20.6, -10.8), (-17.4, -8.4), (-15.6, -4.6), (-12.0, -4.0), (-11.8, -7.0),
             (-14.6, -9.6), (-15.8, -11.8)],
    "disc": [(-24.0, -9.0), (-27.8, -9.4), (-29.2, -7.0), (-27.6, -4.6), (-24.2, -4.8), (-22.8, -6.8)],
    "apical": [(-31.4, -12.4), (-35.8, -9.8), (-39.6, -6.0), (-41.4, -2.4), (-39.6, -0.9), (-37.2, -4.4), (-34.0, -8.0),
               (-30.2, -10.6)],
}
SPOT_IDS = []
for s in ("u", "d"):
    f = (lambda p: p) if s == "u" else mirror_pts
    hinge = HINGE[s]
    at, a = on_bone(f"ely_{s}")
    put(f"elytron_{s}", f"ely_{s}", hinge, 0.0, poly(rel(f(ELY_U), hinge)), "$verdigris", INK_THIN)
    sheen = [(4.2, -9.4), (-4.0, -12.0), (-20.0, -12.2), (-33.0, -9.4), (-31.0, -6.6), (-18.0, -7.4), (-4.0, -7.6)]
    put(f"sheen_{s}", f"ely_{s}", hinge, 0.0, poly(rel(f(sheen), hinge)), "$verdigris.light")
    for name, pts in MAC_U.items():
        pid = f"spot_{s}_{name}"
        SPOT_IDS.append(pid)
        put(pid, f"ely_{s}", hinge, 0.0, poly(rel(f(pts), hinge)), "$husk")
put("suture", "body", (-17.8, 0.0), 0.0, rect(48.0, 1.3, 0.6), "$moss.dark2")
put("scutellum", "body", (6.2, 0.0), 0.0, poly([(1.6, 0), (-1.8, -1.6), (-3.2, 0), (-1.8, 1.6)]), "$verdigris.dark")
# The hive's organ rides the suture, on the back, where every body wears it.
use("organ", "body", (-11.0, 0.0), "ss.lib.organ", scale=[1.25, 1.1])

# ---- pronotum: a narrow barrel, two grooves across it
PRONO = [(17.6, -4.2), (16.0, -6.2), (12.0, -7.0), (8.0, -6.6), (6.2, -5.0), (6.2, 5.0), (8.0, 6.6), (12.0, 7.0), (16.0, 6.2), (17.6, 4.2)]
put("pronotum", "body", (0.0, 0.0), 0.0, poly(PRONO), "$verdigris", INK_THIN)
put("pronotum_sheen", "body", (12.6, -3.2), -4.0, ell(3.8, 1.5), "$verdigris.light")
put("groove_f", "body", (15.6, 0.0), 0.0, rect(0.8, 8.4, 0.4), "$moss.dark2")
put("groove_b", "body", (8.4, 0.0), 0.0, rect(0.8, 9.0, 0.4), "$moss.dark2")

# ---- head: wider than the pronotum, the eyes bulging off its sides
HEAD = [(16.6, -4.0), (18.8, -6.4), (22.0, -7.2), (25.6, -6.6), (28.4, -5.0), (30.0, -3.0), (30.4, 0.0),
        (30.0, 3.0), (28.4, 5.0), (25.6, 6.6), (22.0, 7.2), (18.8, 6.4), (16.6, 4.0)]
put("head", "head", (0.0, 0.0), 0.0, poly(HEAD), "$verdigris", INK_THIN)
put("head_sheen", "head", (22.6, -1.8), 0.0, ell(3.4, 1.4), "$verdigris.light")
put("vertex", "head", (21.0, 0.0), 0.0, rect(5.0, 1.0, 0.5), "$moss.dark2")
for s, sg in (("u", -1), ("d", 1)):
    put(f"eye_{s}", "head", (22.4, sg * 7.6), 0.0, ell(3.9, 3.3), "$steel.light", INK_THIN)
    put(f"eye_{s}_core", "head", (23.4, sg * 8.2), 0.0, ell(1.5, 1.3), "$ink")
    put(f"eye_{s}_glint", "head", (21.6, sg * 6.6), 0.0, circ(0.8), "$white")
# The labrum, white, between the mandibles — the tiger beetle's own tell.
put("labrum", "head", (30.8, 0.0), 0.0, ell(1.9, 3.6), "$bone", INK_HAIR)

# ---- mandibles: husk sickles with teeth on the inner edge, crossing at rest
SICKLE = [(-0.6, -1.7), (3.0, -2.0), (7.0, -2.2), (11.0, -1.6), (14.4, 0.2), (16.6, 2.8), (17.4, 5.2),
          (16.0, 4.0), (14.2, 2.2), (12.6, 1.6), (11.8, 2.9), (10.8, 1.3), (8.6, 1.1), (7.8, 2.6), (6.8, 1.0),
          (3.0, 1.3), (-0.6, 1.7)]
SICKLE_TIP = [(14.4, 0.2), (16.6, 2.8), (17.4, 5.2), (16.0, 4.0), (14.2, 2.2), (13.4, 1.8)]
for s, sg in (("u", -1), ("d", 1)):
    at, a = on_bone(f"mand_{s}")
    f = (lambda p: p) if s == "u" else mirror_pts
    put(f"jaw_{s}", f"mand_{s}", at, a, poly(f(SICKLE)), "$husk", INK_HAIR)
    put(f"jaw_{s}_tip", f"mand_{s}", at, a, poly(f(SICKLE_TIP)), "$moss.dark2")

# ---- antennae: three links a side, dark
ANT_W = [(1.5, 1.2), (1.2, 1.0), (1.0, 0.7)]
for s in ("u", "d"):
    for i, (w0, w1) in enumerate(ANT_W):
        n = f"ant_{s}_{i}"
        at, a = on_bone(n)
        put(n, n, at, a, bar(B[n].length, w0, w1, 0.4), "$dead" if i else "$moss.dark", INK_HAIR if i == 0 else None)

# ---- the glass glint at the mouth, folded to nothing until the spit
put("spit_glow", "head", (38.0, 0.0), 0.0, circ(7.0), "$aqua@soft", scale=0.05)
put("spit_core", "head", (36.0, 0.0), 0.0, ell(3.2, 2.2), "$aqua", scale=0.05)

RIG.check()
STILL = {"spit_glow", "spit_core"} | {f"leg_{s}{n}_knee" for s, n in LEG_IDS} | {f"eye_{s}_glint" for s in "ud"}

# ============================================================== motion
tracks = RIG.tracks

def plant(pose, feet, curl=None):
    """Solve each leg's femur and tibia to put its foot at `feet[leg]`, against the body as posed."""
    world = solve(pose)
    for s, n in LEG_IDS:
        hip, foot, lf, lt, ls, toff = leg_spec(s, n)
        hx, hy, _ = world[f"{s}{n}_femur"]
        hf, ht = ik2((hx, hy), feet[(s, n)], lf, lt, bend_of(s, n))
        pose[f"abs:{s}{n}_femur"] = hf
        pose[f"abs:{s}{n}_tibia"] = ht
        pose[f"abs:{s}{n}_tarsus"] = ht + toff + (curl or {}).get((s, n), 0.0)
    return pose

def rest_foot(s, n): return leg_spec(s, n)[1]

# ---- sprint: the idle, looped. Alternating tripods (front and hind of one
# side with the middle of the other), duty factor a half: a foot planted
# slides back as the ground passes under, then is snatched forward pulled in
# toward the body (the lift, seen from above) with the tarsus curled.
TRIPOD = {("u", "f"): 0.0, ("d", "m"): 0.0, ("u", "h"): 0.0, ("d", "f"): 0.5, ("u", "m"): 0.5, ("d", "h"): 0.5}
STRIDE = {"f": 10.5, "m": 11.5, "h": 13.5}
def sprint_foot(s, n, t):
    u = (t + TRIPOD[(s, n)]) % 1.0
    S = STRIDE[n]
    fx, fy = rest_foot(s, n)
    if u < 0.5:  # stance: planted, the world sliding it back
        return (fx + lerp(S, -S, u / 0.5), fy), 0.0
    v = (u - 0.5) / 0.5
    k = smooth(0.0, 1.0, v)
    lift = math.sin(math.pi * v)
    # Pulled in toward the midline while off the ground.
    return (fx + lerp(-S, S, k), fy * (1 - 0.3 * lift)), lift

def sprint_pose(t):
    # Each tripod's push throws the body a little to the other side and yaws
    # it: two surges, two sways a loop.
    pose = {"body": (1.8 * cyc(2 * t, 0.2), 1.6 * cyc(t, 0.1), 7.0 * cyc(t, 0.1))}
    pose["head"] = -4.0 * cyc(t, 0.0)
    # Antennae streamed back and whipping, a wave running out each one.
    for s, sg in (("u", -1), ("d", 1)):
        base = sg * -26.0
        for i in range(3):
            pose[f"ant_{s}_{i}"] = (base if i == 0 else sg * -10.0) + 12.0 * cyc(2 * t, -0.14 * i + (0 if s == "u" else 0.25))
        pose[f"mand_{s}"] = sg * 12.0 * (0.5 + 0.5 * cyc(2 * t, 0.3))  # (sg × + opens)
    feet, curl = {}, {}
    for s, n in LEG_IDS:
        f, lift = sprint_foot(s, n, t)
        feet[(s, n)] = f
        # the tarsus trails a little behind the swing
        curl[(s, n)] = -SIDES[s] * 34.0 * lift * (1 if n != "h" else -1)
    return plant(pose, feet, curl)

# ---- spit: 0.3s, played at the moment the fan leaves (the rest's shot). A
# snap back of the head with the jaws thrown wide (the gather), the head
# driven forward with the glass flaring at the mouth (the release), then the
# jaws closing and a settle onto the sprint's first frame. The legs are
# braced: every foot planted where the sprint's first frame has it.
def spit_pose(t):
    gather = smooth(0.0, 0.22, t)
    throw = smooth(0.2, 0.36, t)
    settle = smooth(0.45, 1.0, t)
    walk = sprint_pose(0.0)
    g = gather * (1 - throw)
    bx = -4.0 * g + 5.0 * throw * (1 - settle)
    body = (lerp(bx, walk["body"][0], settle), lerp(0.6 * g, walk["body"][1], settle), lerp(0.0, walk["body"][2], settle))
    pose = {"body": body, "head": lerp(0.0, walk["head"], settle)}
    for s, sg in (("u", -1), ("d", 1)):
        open_ = 48.0 * gather * (1 - 0.3 * throw) * (1 - settle)
        pose[f"mand_{s}"] = lerp(sg * open_, walk[f"mand_{s}"], settle)
        for i in range(3):
            fly = sg * (-14.0 * gather + 30.0 * throw) * (1 - settle) if i == 0 else sg * 10.0 * throw * (1 - settle)
            pose[f"ant_{s}_{i}"] = lerp(fly, walk[f"ant_{s}_{i}"], settle)
    feet = {(s, n): sprint_foot(s, n, 0.0)[0] for s, n in LEG_IDS}
    return plant(pose, feet)
# The glint is folded to 0.05 at rest, so these are multiples of that.
SPIT_EXTRA = [("spit_glow", "scale", lambda t: max(1.0, 20.0 * smooth(0.18, 0.34, t) * (1 - smooth(0.5, 0.95, t)))),
              ("spit_core", "scale", lambda t: max(1.0, 17.0 * smooth(0.2, 0.32, t) * (1 - smooth(0.4, 0.75, t))))]

# ---- death: 0.8s. The jaws snap once and fall wide, the legs kick out of
# step and then splay and curl in, the elytra part and the hind wings slide
# out under them, the antennae drop back; the eyes and the organ go out. Still
# from 0.85.
def death_pose(t):
    snap = math.sin(math.pi * smooth(0.0, 0.2, t))
    fall = smooth(0.15, 0.8, t)
    kick = math.sin(math.pi * smooth(0.0, 0.3, t))
    pose = {"body": (-1.5 * kick, 0.0, 6.0 * fall), "head": -10.0 * fall}
    for s, sg in (("u", -1), ("d", 1)):
        pose[f"mand_{s}"] = sg * (-8.0 * snap + 30.0 * fall)
        # (a u-side bone points back along 180°, so turning it outboard is +)
        pose[f"ely_{s}"] = -sg * 7.0 * fall
        pose[f"wing_{s}"] = -sg * 24.0 * smooth(0.2, 0.75, t)
        for i in range(3):
            pose[f"ant_{s}_{i}"] = sg * (-50.0 * fall if i == 0 else 16.0 * fall)
    feet, curl = {}, {}
    for s, n in LEG_IDS:
        fx, fy = rest_foot(s, n)
        hip = leg_spec(s, n)[0]
        k = TRIPOD[(s, n)]
        # One kick out of step: the first tripod flung forward, the second back.
        dx = (8.0 if k == 0 else -8.0) * kick * (1 - fall)
        # Then drawn in: each foot halfway to its hip, the tarsus curled under.
        fx2 = lerp(fx + dx, hip[0] + (fx - hip[0]) * 0.62, fall)
        fy2 = lerp(fy, hip[1] + (fy - hip[1]) * 0.62, fall)
        feet[(s, n)] = (fx2, fy2)
        curl[(s, n)] = -SIDES[s] * 70.0 * fall * (1 if n != "h" else -1)
    return plant(pose, feet, curl)

animations = {}
animations["sprint"] = {
    "description": "The idle, and the run it covers 120px in: six long legs in two alternating tripods, each foot planted while the ground slides back under it and snatched forward drawn in toward the body; the body surges and sways off each push and yaws with the stride, the head counter-turns, the antennae stream back and whip with a lag down their length and the jaws work.",
    "duration": 0.36,
    "tracks": tracks(sprint_pose, keyset(12), still=STILL),
}
animations["spit"] = {
    "description": "Played once in the rest as the glass fan leaves: the head snaps back with the jaws thrown wide, then drives forward as an aqua glint flares at the mouth, and the jaws close and it settles onto the sprint's first frame, every foot braced where that frame has it.",
    "duration": 0.3,
    "tracks": tracks(spit_pose, keyset(15), SPIT_EXTRA, still=STILL),
}
DEATH_TS = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The jaws snap once and fall wide, the legs kick out of step and then draw in and curl, the elytra part and the pale hind wings slide out from under them, the head droops, the antennae fall back, the eyes dim and the organ goes out. Still from 0.85.",
    "duration": 0.8,
    "tracks": tracks(death_pose, DEATH_TS, [
        ("eye_u", "opacity", lambda t: 1.0 - 0.55 * smooth(0.2, 0.7, t)),
        ("eye_d", "opacity", lambda t: 1.0 - 0.55 * smooth(0.2, 0.7, t)),
        ("eye_u_glint", "opacity", lambda t: 1.0 - smooth(0.1, 0.5, t)),
        ("eye_d_glint", "opacity", lambda t: 1.0 - smooth(0.1, 0.5, t)),
        ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.2, 0.8, t)),
    ], still=STILL),
}

# ============================================================== states
def posed_set(pose, ids):
    """`at`/`rot` patches that put parts where `pose` has them — a state drawn as a pose."""
    now = RIG.posed_parts(pose)
    base = {p["id"]: p for p in RIG.parts}
    out = {}
    for pid in ids:
        x, y, a = now[pid]
        out[f"{pid}.at"] = [r2(x), r2(y)]
        out[f"{pid}.rot"] = r2(wrap(a))
    return out
ELY_PARTS = {s: [f"elytron_{s}", f"sheen_{s}"] + [p for p in SPOT_IDS if p.startswith(f"spot_{s}_")] for s in "ud"}
OPEN = {"ely_u": 9.0, "ely_d": -9.0, "wing_u": 40.0, "wing_d": -40.0}
enraged_set = {}
enraged_set.update(posed_set(OPEN, ELY_PARTS["u"] + ELY_PARTS["d"] + ["hindwing_u", "hindwing_d", "hindvein_u", "hindvein_d"]))
enraged_set.update({
    "jaw_u.fill": "$bone.light", "jaw_d.fill": "$bone.light",
    "jaw_u.scale": 1.15, "jaw_d.scale": 1.15, "jaw_u_tip.scale": 1.15, "jaw_d_tip.scale": 1.15,
    "jaw_u_tip.fill": "$ember.dark", "jaw_d_tip.fill": "$ember.dark",
    "eye_u.fill": "$ember", "eye_d.fill": "$ember",
    "hindwing_u.fill": "$venom@heavy", "hindwing_d.fill": "$venom@heavy",
    "organ.scale": [1.6, 1.4],
    **{f"{p}.fill": "$ember" for p in SPOT_IDS},
})
final_set = {
    **{f"{p}.opacity": 0 for p in ELY_PARTS["u"] + ELY_PARTS["d"]},
    **posed_set({"wing_u": 22.0, "wing_d": -22.0}, ["hindwing_u", "hindwing_d", "hindvein_u", "hindvein_d"]),
    "hindwing_u.fill": "$smoke@soft", "hindwing_d.fill": "$smoke@soft",
    "abdomen.fill": "$husk.dark",
    "suture.opacity": 0, "scutellum.fill": "$moss.dark2",
    "eye_u.fill": "$dead", "eye_d.fill": "$dead", "eye_u_glint.opacity": 0, "eye_d_glint.opacity": 0,
    "pronotum.fill": "$moss.dark", "pronotum_sheen.fill": "$verdigris.dark", "head.fill": "$moss",
    "ant_u_1.fill": "$dead", "ant_u_2.fill": "$dead", "ant_d_1.fill": "$dead", "ant_d_2.fill": "$dead",
    "jaw_u.fill": "$white", "jaw_d.fill": "$white",
    "jaw_u.scale": 1.3, "jaw_d.scale": 1.3, "jaw_u_tip.scale": 1.3, "jaw_d_tip.scale": 1.3,
    "organ.scale": [2.0, 1.7],
}
variants = {
    "enraged": {
        "description": "Halfway: the elytra lifted and parted at the shoulder to show the venom hind wings under them, the lunules and eyes gone ember, the jaws longer and bone-white with burning tips. It sprints harder and the fan is five.",
        "set": enraged_set,
    },
    "final": {
        "description": "Phase three: the elytra are gone rather than lifted, and the wings they were hiding have nothing left in them — smoke, spread over a bare husk abdomen. The eyes are out — it was only ever blind between stops, and now it is blind in them too. What is left is the running and the jaws, longer and white.",
        "set": final_set,
    },
}

# ============================================================== document
DESCRIPTION = (
    "The pan's second arrival, the one that comes for you: a tiger beetle, the fastest thing on legs, which runs so fast it goes blind and has to "
    "stop to see — the game runs it as a sprint and a rest (EnemyType.hopSpeed) and it fires only in the rest. Seen from above along +x and turned "
    "by the game rather than mirrored, like the Courser: long parallel elytra in tarnished verdigris with cream lunules (the humeral comma, the middle "
    "band, the apical crescent), a narrow barrel pronotum, a head wider than it with two huge pale steel eyes bulging off its sides and a white labrum, "
    "six legs as long as the body, and jaws — two toothed husk sickles that cross, the read at any distance, and the mouth the glass fan leaves "
    "from (`ss.enemy.glassbolt`; the `spit` clip flares an aqua glint there). Green, the pan's one green besides the Locust, which is chaff — "
    "a tarnished metallic green over moss darks: `$verdigris`, the pan's own dulled cut of green, so it sits in the pan's earth palette rather than glowing out of it (a first rebuild in mint `$sage` was the loudest thing on the sand). "
    "Built on a skeleton (scripts/forerunner.py): the legs are solved every frame to a foot on the ground, the antennae are chains, the mandibles "
    "and the elytra are hinged bones and the hind wings lie folded under the elytra. `sprint` is the idle and the run — two alternating tripods, "
    "the body surging and yawing off each push; `spit` the shot, a snap back and a drive forward with the jaws wide. `enraged` lifts and parts "
    "the elytra to show venom-green hind wings, lights the lunules ember and lengthens the jaws; `final` has lost the elytra. Gameplay radius 42. "
    "The `death` clip kicks once out of step, then the legs draw in and curl while the elytra part and the wings slide out."
)

doc = {
    "id": "ss.enemy.forerunner",
    "name": "Forerunner",
    "description": DESCRIPTION,
    "tags": ["enemy", "boss"],
    "size": [128, 88],
    "meta": {"radius": 42},
    "parts": RIG.parts,
    "variants": variants,
    "skeleton": RIG.skeleton(),
    "animations": animations,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-forerunner.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
