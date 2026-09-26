"""The Locust — the pan's chaff that crosses the gap in one leap or not at all.

    python3 scripts/locust.py        # rewrites apps/ss/assets/ss-enemy-locust.json

feelers runs it as a hop: 0.3s at 265 (`EnemyType.hopTime`, `hopSpeed`), then
about half a second at almost nothing (`hopRest`, jittered ±20%), the body
lifted off the floor on a 12px arc (`hopLift`) with `ss.fx.shadow` under it.
The `hop` clip is a loop the game plays at its own rate, not seated on the
leap — so it is authored as one whole hop cycle at the game's mean cadence
(0.3 + 0.5 = 0.8s), the leap first: t 0→0.375 is the 0.3s in the air, the rest
is the landing, the stand, and the crouch that loads the next kick. Seated or
not, every stretch of it reads as the one thing a locust does.

It was hand-placed, and it measured 4.5px of travel at game scale: the hind
leg was two rects turned about their own centres, so the knee came apart
instead of bending, and nothing else moved. This rebuilds it on the rig
(scripts/rig.py), the way the Stinger was:

  - the body is a root bone that crouches, launches nose-up, levels and lands
    nose-down into a squash; the head nods after it
  - each leg is a femur and a tibia solved by two-bone IK to a foot — planted
    through the crouch, shoved straight back along the ground on the kick,
    trailing in the air, and set down again on the landing
  - the forewing (tegmen) lifts and the hindwing opens under it as a fan of
    four vanes for the flight, each hinged at the wing root
  - the abdomen (two segments) and the antennae (three each) are chains that
    ride the body's pitch as a wave with a lag down the chain

Side-on facing +x, mirrored by the game. Bile-green: the arsenal's acid
colour as an animal, and the only green on the pan short of the Forerunner.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 52×40, origin at the centre, +x forward, +y down. Feet stand on GROUND.
GROUND = 9.0
FAR_LIFT = 1.0

RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("body", None, (0.0, 0.5), 0.0)
bone("head", "body", (6.4, -1.0), 0.0)

# The abdomen: two segments running back from under the wing, the tip lifting.
bone("abd_0", "body", (-2.4, 0.9), 180.0, 6.4)
bone("abd_1", "abd_0", B["abd_0"].end(), 185.0, 6.6)

# The forewing (tegmen) along the back from its root over the thorax, and the
# hindwing folded under it as four vanes on the same hinge.
WING_ROOT = (0.8, -3.9)
bone("tegmen", "body", WING_ROOT, 175.0, 19.0)
N_VANES = 4
for i in range(N_VANES):
    bone(f"vane_{i}", "body", (WING_ROOT[0] - 0.4, WING_ROOT[1] + 0.3), 176.0, 15.5 - 0.9 * i)

# Antennae: three links each off the top of the face, arching forward.
RIG.chain("ant_n", "head", (10.4, -5.9), [(3.4, -52.0), (3.4, -36.0), (3.2, -20.0)])
RIG.chain("ant_f", "head", (9.6, -6.1), [(3.0, -60.0), (3.0, -46.0), (2.8, -32.0)])

# Legs: (hip, rest foot, femur, tibia, tarsus, knee bend). The hind leg is the
# silhouette — a femur cocked up and back to a knee above the abdomen, the
# tibia dropped from it to the foot. Front and mid legs are small, knees forward.
LEGS = {
    "hind_n": ((-0.8, 1.2), (-5.1, GROUND), 10.6, 13.4, 3.4, -1),
    "mid_n": ((1.8, 3.0), (0.6, GROUND), 4.4, 5.0, 1.8, 1),
    "front_n": ((5.2, 2.8), (8.4, GROUND), 4.0, 4.8, 1.6, 1),
    "hind_f": ((-1.6, 0.4), (-6.6, GROUND - FAR_LIFT), 10.2, 13.0, 3.2, -1),
    "mid_f": ((1.0, 2.0), (-0.8, GROUND - FAR_LIFT), 4.2, 4.8, 1.6, 1),
    "front_f": ((4.4, 1.8), (7.2, GROUND - FAR_LIFT), 3.8, 4.6, 1.5, 1),
}
def tarsus_rest(leg): return 182.0 if leg.startswith("hind") else (8.0 if leg.startswith("front") else 172.0)
for leg, (hip, foot, lf, lt, ls, bend) in LEGS.items():
    hf, ht = ik(hip, foot, lf, lt, bend)
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", B[f"{leg}_femur"].end(), ht, lt)
    bone(f"{leg}_tarsus", f"{leg}_tibia", B[f"{leg}_tibia"].end(), tarsus_rest(leg), ls)

RIG.seal()
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
# Values: pale (pronotum, forewing, the hind femur's outer face), mid (head,
# abdomen, near legs), dark (tibiae, bands, far side). Hairlines on everything
# thin; the three masses — pronotum, head, abdomen — take `thin`.
HAIR_DARK = {"color": "$bile.dark2", "width": "hair"}
# The abdomen sits inside the silhouette under the wing: a dark-bile edge
# separates it from the legs without an ink ring dragging the value down.
EDGE = {"color": "$bile.dark2", "width": "thin"}

def small_leg(leg, femur, tibia, stroke):
    lf, lt, ls = LEGS[leg][2], LEGS[leg][3], LEGS[leg][4]
    at, a = on_bone(f"{leg}_tarsus"); put(f"{leg}_tarsus", f"{leg}_tarsus", at, a, bar(ls, 1.1, 0.8, 0.4), tibia, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(lt, 1.3, 1.0), tibia, stroke)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(lf, 2.0, 1.5), femur, stroke)

# The hind femur: a drumstick, swollen near the hip and drawn to the knee. In
# the femur's frame +x runs hip → knee and +y is the upper edge.
FEMUR = [(-1.2, -1.4), (0.2, -2.3), (3.2, -2.7), (6.6, -2.0), (9.8, -1.1), (11.5, -0.6), (11.9, 0.2),
         (11.3, 0.9), (9.6, 1.2), (6.6, 1.9), (3.2, 2.6), (0.2, 2.4), (-1.2, 1.4)]
def hind_leg(leg, femur_fill, tibia_fill, stroke, marks):
    lf, lt, ls = LEGS[leg][2], LEGS[leg][3], LEGS[leg][4]
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(lt, 1.7, 1.2), tibia_fill, stroke)
    at, a = on_bone(f"{leg}_tarsus"); put(f"{leg}_tarsus", f"{leg}_tarsus", at, a, bar(ls, 1.3, 0.9, 0.5), tibia_fill, stroke)
    k = lf / 10.6
    at, a = on_bone(f"{leg}_femur")
    put(f"{leg}_femur", f"{leg}_femur", at, a, poly([(x * k, y * k) for x, y in FEMUR]), femur_fill, stroke)
    if marks:
        at, a = on_bone(f"{leg}_femur", 4.6 * k, 1.0 * k)
        put(f"{leg}_face", f"{leg}_femur", at, a + 4.0, ell(4.6 * k, 1.2 * k), "$bile.light2")
        # the lower keel of the femur, dark, and the herringbone over the face
        at, a = on_bone(f"{leg}_femur", 5.2 * k, -1.35 * k)
        put(f"{leg}_keel", f"{leg}_femur", at, a, rect(8.4 * k, 0.9, 0.45), "$bile.dark")
        for j, x in enumerate((2.6, 5.0, 7.4)):
            at, a = on_bone(f"{leg}_femur", x * k, 0.5 * k)
            put(f"{leg}_chev_{j}", f"{leg}_femur", at, a + 32.0, rect(0.7, 2.6 - 0.35 * j, 0.35), "$bile.dark@soft")
    # the knee: the dark genicular crescent at the joint
    at, a = on_bone(f"{leg}_tibia")
    put(f"{leg}_knee", f"{leg}_tibia", at, 0.0, circ(1.15 * (lf / 10.6)), "$bile.dark2")

# ---- far side, darkest: antenna, legs
for i in range(3):
    n = f"ant_f_{i}"; at, a = on_bone(n)
    put(n, n, at, a, bar(B[n].length, 0.9 - 0.12 * i, 0.75 - 0.12 * i, 0.4), "$bile.dark2")
hind_leg("hind_f", "$bile", "$bile.dark", None, False)
small_leg("mid_f", "$bile.dark", "$bile.dark", None)
small_leg("front_f", "$bile.dark", "$bile.dark", None)

# ---- abdomen: two ringed segments, tip under the wing
at, a = on_bone("abd_1")
put("abd_1", "abd_1", at, a, poly([(-1.0, -3.0), (2.0, -3.0), (5.0, -2.3), (6.8, -1.2), (7.4, 0.0), (6.8, 1.0),
                                   (4.8, 1.6), (2.0, 2.4), (-1.0, 2.8)]), "$bile.light", EDGE)
at, a = on_bone("abd_0")
put("abd_0", "abd_0", at, a, poly([(-1.8, -2.8), (1.0, -3.6), (4.2, -3.5), (6.8, -3.1), (7.2, 0.0), (6.8, 2.9),
                                   (3.8, 3.3), (0.6, 3.4), (-1.8, 2.6)]), "$bile.light", EDGE)
for j, (bn, x, h) in enumerate((("abd_0", 1.6, 6.0), ("abd_0", 4.4, 5.8), ("abd_1", 0.8, 4.8), ("abd_1", 3.6, 3.6))):
    at, a = on_bone(bn, x, -0.2)
    put(f"ring_{j}", bn, at, a, rect(0.8, h, 0.4), "$bile.dark@soft")
at, a = on_bone("abd_0", 3.0, -2.2)   # the pale belly line (ventral is -y here: the bone points back)
put("belly", "abd_0", at, a, rect(8.0, 1.0, 0.5), "$bile.light@soft")

# ---- hindwing: four vanes folded under the forewing, fanned for the leap
VANE = [(-0.4, -0.5), (3.0, -1.5), (9.0, -1.8), (13.6, -1.2), (15.4, -0.1), (14.2, 0.8), (9.0, 1.2), (3.0, 1.0), (-0.4, 0.5)]
for i in range(N_VANES):
    n = f"vane_{i}"; at, a = on_bone(n)
    L = B[n].length
    put(n, n, at, a, poly([(x * L / 15.4, y) for x, y in VANE]), "$bile.light2" if i % 2 == 0 else "$bile.light", HAIR_DARK)

# ---- forewing: long and narrow, mottled, a pale vein down it
at, a = on_bone("tegmen")
put("tegmen", "tegmen", at, a, poly([(-0.8, -0.9), (2.6, -1.7), (9.0, -1.9), (15.6, -1.6), (18.8, -0.8), (19.6, 0.2),
                                     (18.6, 1.1), (14.0, 1.7), (6.0, 1.9), (1.0, 1.6), (-0.8, 0.9)]), "$bile.light", INK_HAIR)
at, a = on_bone("tegmen", 9.6, 0.4)
put("vein", "tegmen", at, a, rect(16.0, 0.6, 0.3), "$bile.dark@soft")
for j, (x, y, rx) in enumerate(((5.2, -0.9, 1.2), (9.4, -1.1, 1.0), (13.2, -0.8, 1.1), (16.4, -0.5, 0.8))):
    at, a = on_bone("tegmen", x, y)
    put(f"mottle_{j}", "tegmen", at, a, ell(rx, 0.55), "$bile.dark@soft")

# ---- pronotum over the thorax, the organ on its flank, the head in front
put("thorax", "body", (2.4, 2.0), 0.0, ell(4.2, 2.2), "$bile.dark")
PRONOTUM = [(-1.8, -3.4), (-0.6, -4.8), (2.2, -5.4), (5.2, -5.2), (7.2, -4.2), (7.6, -1.0), (7.0, 2.0),
            (4.6, 2.8), (1.4, 3.0), (-0.6, 2.2), (-1.8, -0.4)]
put("pronotum", "body", (0.0, 0.0), 0.0, poly(PRONOTUM), "$bile.light", INK_THIN)
put("sulcus", "body", (3.6, -2.4), 78.0, rect(0.7, 3.6, 0.35), "$bile.dark@soft")
put("pronotum_gloss", "body", (2.8, -4.3), -4.0, ell(2.6, 0.6), "$white@0.3")
RIG.use("organ", "body", (3.2, 0.4), "ss.lib.organ", scale=[0.44, 0.44])

HEAD = [(6.2, -4.2), (7.8, -6.3), (10.2, -6.9), (12.2, -5.8), (13.3, -3.4), (13.6, -0.2), (13.0, 2.4),
        (11.4, 3.6), (9.0, 3.4), (7.0, 2.0), (6.0, -1.0)]
put("head", "head", (0.0, 0.0), 0.0, poly(HEAD), "$bile", INK_THIN)
put("cheek", "head", (9.6, 1.6), -10.0, ell(2.4, 1.2), "$bile.dark@soft")
put("mandible", "head", (12.4, 3.0), 20.0, ell(1.3, 0.9), "$bile.dark2", INK_HAIR)
put("palp", "head", (11.6, 4.4), 76.0, bar(1.6, 0.8, 0.6, 0.3), "$bile.dark2")
put("eye", "head", (10.7, -3.3), -14.0, ell(1.75, 2.2), "$ink")
put("glint", "head", (10.3, -4.3), 0.0, circ(0.55), "$silent")

# ---- near antenna, over the head
for i in range(3):
    n = f"ant_n_{i}"; at, a = on_bone(n)
    put(n, n, at, a, bar(B[n].length, 1.0 - 0.15 * i, 0.85 - 0.15 * i, 0.4), "$bile", HAIR_DARK)

# ---- near legs, over everything
small_leg("mid_n", "$bile.light", "$bile", HAIR_DARK)
small_leg("front_n", "$bile.light", "$bile", HAIR_DARK)
hind_leg("hind_n", "$bile", "$bile.dark", HAIR_DARK, True)

RIG.check()

# ============================================================== motion
def curve(t, keys):
    """A value keyed at times, eased (smoothstep) between keys, held past the ends."""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1: return lerp(v0, v1, smooth(t0, t1, t))
    return keys[-1][1]
def pt(t, keys):
    return (curve(t, [(k, x) for k, x, y in keys]), curve(t, [(k, y) for k, x, y in keys]))

def plant(pose, feet, tarsi=None):
    """Solve every leg's femur and tibia to its foot, against the body as posed."""
    world = solve(pose)
    for leg, (hip, foot, lf, lt, ls, bend) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, bend)
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_tarsus"] = (tarsi or {}).get(leg, tarsus_rest(leg))
    return pose

def chain_set(pose, prefix, deltas):
    for i, d in enumerate(deltas): pose[f"{prefix}_{i}"] = pose.get(f"{prefix}_{i}", 0.0) + d

# ---- hop: one leap cycle, the leap first.
# t (of 0.8s)   0     kick — the hind tibiae snap open, the body is thrown nose-up
#               .07–.3 in the air: legs trailing, forewing up, hindwing fanned
#               .3–.375 legs drawn in, front legs reaching; lands at .375 (0.3s)
#               .375–.55 squash onto the front legs, rebound, wings slam shut
#               .55–.8 stands; antennae working
#               .8–1  the crouch that loads the next kick (continuous with t=0)
PITCH = [(0.0, -6.0), (0.06, -20.0), (0.2, -8.0), (0.33, 6.0), (0.4, 9.0), (0.5, 1.0), (0.62, -1.0), (0.78, 0.0), (1.0, -6.0)]
DY = [(0.0, 1.6), (0.06, -1.8), (0.2, -1.2), (0.33, -0.4), (0.4, 2.0), (0.5, -0.3), (0.62, 0.3), (0.78, 0.0), (1.0, 1.6)]
DX = [(0.0, -1.0), (0.06, 1.2), (0.3, 0.6), (0.4, 0.6), (0.55, 0.0), (0.8, 0.0), (1.0, -1.0)]
def pitch(t): return curve(t % 1.0, PITCH)
HX = LEGS["hind_n"][1][0]
HIND_N = [(0.0, HX, GROUND), (0.06, -19.8, GROUND + 0.4), (0.16, -19.4, 6.4), (0.26, -16.4, 5.0),
          (0.34, HX - 1.6, 7.4), (0.38, HX, GROUND), (1.0, HX, GROUND)]
EXT = [(0.0, 0.0), (0.06, 1.0), (0.2, 1.0), (0.34, 0.0)]
def front_keys(fx, gy):
    return [(0.0, fx, gy), (0.04, fx, gy), (0.14, fx - 2.4, gy - 4.0), (0.28, fx + 3.6, gy - 2.2),
            (0.375, fx, gy), (1.0, fx, gy)]
def mid_keys(fx, gy):
    return [(0.0, fx, gy), (0.05, fx - 0.6, gy), (0.15, fx - 1.2, gy - 3.8), (0.3, fx + 2.2, gy - 1.8),
            (0.39, fx, gy), (1.0, fx, gy)]
OPEN = [(0.0, 0.0), (0.05, 0.0), (0.11, 1.12), (0.16, 1.0), (0.25, 0.9), (0.33, 0.0), (1.0, 0.0)]
TEGMEN = [(0.0, 0.0), (0.04, 0.0), (0.1, 30.0), (0.24, 26.0), (0.33, 4.0), (0.38, -3.0), (0.46, 0.0), (1.0, 0.0)]
ANT_SWEEP = [(0.0, 4.0), (0.05, -6.0), (0.12, -26.0), (0.26, -22.0), (0.36, 10.0), (0.46, 18.0), (0.56, -4.0), (0.66, 2.0), (1.0, 4.0)]

def hop_pose(t):
    p = pitch(t)
    pose = {"body": (curve(t, DX), curve(t, DY), p)}
    # head and abdomen lag the pitch; the abdomen also pumps while it stands
    pose["head"] = 0.5 * (pitch(t - 0.05) - p) + 3.0 * smooth(0.36, 0.42, t) * (1 - smooth(0.42, 0.6, t))
    breathe = smooth(0.5, 0.6, t) * (1 - smooth(0.9, 1.0, t)) * cyc(t * 2.0, 0.1)
    pose["abd_0"] = 0.5 * (pitch(t - 0.05) - p) + 1.5 * breathe
    pose["abd_1"] = 0.7 * (pitch(t - 0.1) - pitch(t - 0.05)) + 3.0 * breathe + 6.0 * curve(t, OPEN)
    # wings
    pose["tegmen"] = curve(t, TEGMEN)
    o = curve(t, OPEN)
    for i in range(N_VANES): pose[f"vane_{i}"] = o * (16.0 + 17.0 * i)
    # antennae: swept back through the air, whipped forward on the landing,
    # then working while it stands — each link a little after the one before
    for side, k in (("ant_n", 1.0), ("ant_f", 0.8)):
        ds = []
        for i in range(3):
            lag = 0.035 * i
            twitch = 7.0 * smooth(0.55, 0.62, t) * (1 - smooth(0.9, 1.0, t)) * cyc(t * 3.0, -0.12 * i + (0.3 if side == "ant_f" else 0.0))
            ds.append(k * (curve((t - lag) % 1.0, ANT_SWEEP) * (0.6 + 0.3 * i) + twitch))
        chain_set(pose, side, ds)
    # feet
    feet = {}
    feet["hind_n"] = pt(t, HIND_N)
    hx, hy = feet["hind_n"]
    feet["hind_f"] = (hx - 1.5, hy - FAR_LIFT)
    for leg in ("front_n", "front_f"):
        fx, gy = LEGS[leg][1]
        feet[leg] = pt(t, front_keys(fx, gy))
    for leg in ("mid_n", "mid_f"):
        fx, gy = LEGS[leg][1]
        feet[leg] = pt(t, mid_keys(fx, gy))
    ext = curve(t, EXT)
    plant(pose, feet)
    tarsi = {}
    for leg in ("hind_n", "hind_f"):
        tarsi[leg] = lerp(tarsus_rest(leg), pose[f"abs:{leg}_tibia"] + 14.0, ext)
    tuck = curve(t, [(0.0, 0.0), (0.06, 0.0), (0.14, 1.0), (0.28, 0.4), (0.37, 0.0)])
    for leg in ("mid_n", "mid_f", "front_n", "front_f"):
        tarsi[leg] = tarsus_rest(leg) + (40.0 if leg.startswith("front") else -30.0) * tuck
    return plant(pose, feet, tarsi)

# ---- death: one kick into nothing, then the hind leg draws up under the body,
# the forewing falls open, the head drops and the antennae lie down over it.
def death_pose(t):
    kick = smooth(0.0, 0.14, t) * (1 - smooth(0.2, 0.5, t))
    fall = smooth(0.2, 0.8, t)
    jolt = math.sin(math.pi * smooth(0.0, 0.25, t))
    pose = {"body": (0.0, -1.2 * jolt + 3.2 * fall, -9.0 * jolt + 7.0 * fall)}
    pose["head"] = 20.0 * fall
    pose["abd_0"] = 5.0 * jolt - 3.0 * fall
    pose["abd_1"] = 8.0 * jolt - 7.0 * fall
    pose["tegmen"] = 10.0 * jolt + 34.0 * fall
    for i in range(N_VANES): pose[f"vane_{i}"] = fall * (14.0 + 10.0 * i) + jolt * 8.0 * i
    for side in ("ant_n", "ant_f"):
        chain_set(pose, side, [-14.0 * jolt + 38.0 * fall, 26.0 * fall, 22.0 * fall])
    feet, tarsi = {}, {}
    hn = LEGS["hind_n"][1]
    folded = (-4.6, 4.6)
    kx = lerp(lerp(hn[0], -19.6, kick), folded[0], fall)
    ky = lerp(lerp(hn[1], GROUND - 0.4, kick), folded[1], fall)
    feet["hind_n"] = (kx, ky)
    feet["hind_f"] = (kx - 1.2, ky - FAR_LIFT)
    for leg in ("mid_n", "mid_f", "front_n", "front_f"):
        (hx, hy), (fx, gy) = LEGS[leg][0], LEGS[leg][1]
        feet[leg] = (lerp(fx, hx + (1.6 if leg.startswith("front") else -0.8), fall), lerp(gy, hy + 4.4, fall) + 3.2 * fall)
        tarsi[leg] = tarsus_rest(leg) + (60.0 if leg.startswith("front") else -50.0) * fall
    plant(pose, feet)
    for leg in ("hind_n", "hind_f"):
        tarsi[leg] = lerp(tarsus_rest(leg), pose[f"abs:{leg}_tibia"] + 14.0, kick) + 40.0 * fall
    return plant(pose, feet, tarsi)

STILL = {"hind_n_knee", "hind_f_knee"}
animations = {}
TS_HOP = keyset(32)
animations["hop"] = {
    "description": "One whole leap cycle at the game's mean cadence (hopTime 0.3 + hopRest 0.5), the leap first: from the crouch the hind tibiae snap open and shove back along the ground and the body is thrown nose-up; in the air (to 0.375) the hind legs trail straight, the forewing lifts and the hindwing fans out under it in four vanes, the antennae sweep back and the small legs tuck; then the legs are drawn in, the front legs reach, and it lands nose-down into a squash with the wings slamming shut and the antennae whipping forward; it stands with the abdomen pumping and the antennae working, and sinks into the crouch that loads the next kick.",
    "duration": 0.8,
    "tracks": RIG.tracks(hop_pose, TS_HOP, still=STILL),
}
TS_DEATH = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "One kick into nothing — the body jolts nose-up and the hind leg shoots straight back — then everything lets go: the hind leg draws up tight under the body, the forewing falls open over a half-spread hindwing, the head drops, the antennae lie down over the face, the small legs curl and the body settles; the organ flares and goes out. Still from 0.85.",
    "duration": 0.4,
    "tracks": RIG.tracks(death_pose, TS_DEATH, [
        ("organ", "scale", lambda t: 1.0 + 0.4 * math.sin(math.pi * smooth(0.0, 0.35, t)) - 0.15 * smooth(0.35, 0.8, t)),
        ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.25, 0.8, t)),
    ], still=STILL),
}

# ============================================================== document
DESCRIPTION = (
    "The pan's fast chaff, and the one body in the game that moves by leaping: the game runs it as 0.3s at 265 and half a second at almost "
    "nothing (EnemyType.hopSpeed), drawn as height with `ss.fx.shadow` under it. So the silhouette is the leg — a hind femur like a drumstick "
    "cocked up and back to a dark knee above the abdomen, the tibia dropped from it to the ground — in front of it a saddle of a pronotum and a "
    "tall head with a big eye, and a long forewing laid along the back. Bile-green, the arsenal's acid colour turned into an animal, and nothing "
    "else on the pan is green but the Forerunner, which is a boss and four times the size. Drawn side-on facing +x, mirrored by the game. "
    "Built on a skeleton (scripts/locust.py): the legs are solved every frame to a foot, the hindwing is four vanes on one hinge, and the "
    "abdomen and antennae are chains that ride the body's pitch with a lag. The `hop` clip is one whole leap cycle at the game's mean cadence "
    "(0.3s up, 0.5s down), the leap first — kick, flight with the hindwing fanned, a nose-down landing into a squash, the stand, and the crouch "
    "that loads the next kick; the game plays it at its own rate rather than seated on each hop, and every stretch of it reads as the one "
    "thing a locust does. Gameplay radius 7. No `elite` variant: a Locust is never the sturdiest thing on its stage. The `death` clip kicks "
    "once into nothing and then draws the leg up under the body while the wing falls open."
)

doc = {
    "id": "ss.enemy.locust",
    "name": "Locust",
    "description": DESCRIPTION,
    "tags": ["enemy", "locust"],
    "size": [52, 40],
    "meta": {"radius": 7},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-locust.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
