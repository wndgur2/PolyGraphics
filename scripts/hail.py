"""Hail — the pan's first arrival, a mass that wears the ring it throws.

    python3 scripts/hail.py        # rewrites apps/ss/assets/ss-enemy-hail.json

It stands off at 340 and every 2.6s sheds a ring of twelve stones — sixteen
from 70% — thrown all round at once (feelers: `shotFan: 2π`, `volleyAnim:
'burst'`, `aimTime: 0.45`). So the drawing's one idea is that the ring is the
body's own edge: twelve steel stones stuck round the rim of a slate mass, and
the lumpy outline is the attack.

It was hand-placed and it moved seven pixels at game scale: the stones crept
one place round per cycle and nothing else happened — eight legs that were
bars about their own centres, a mass that never breathed. This rebuilds it on
the rig (scripts/rig.py):

  - a skeleton: the mass is the root, and each of the eight legs is a femur
    and a tibia solved every frame to a foot on the ground (two-bone IK), the
    knee thrown out to the side, so a planted foot stays planted while the
    mass sways over it
  - the ring is not on bones: each stone is placed by where it is round the
    rim (its angle), and its size, its tilt and how far out it stands are
    functions of that angle — so a stone that creeps one place round takes on
    exactly the look of the one that was there, and the loop is seamless
  - `churn` is the walk and the idle: an alternating tetrapod gait twice a
    loop, the mass swaying and heaving over the planted feet, the ring creeping
    one place round with a swell running round it twice — the stones rising
    off the rim and settling as it passes, the way a ring about to leave does

Seen from above, facing +x, symmetric about the x axis. The game mirrors it
(it has neither `turns` nor `turnsMirrored`; `facePrey` and `beginAim` flip it
toward you), and a drawing symmetric about the x axis mirrors into the same
body turned round — so the pit and its three eyes face you, whichever side you
are on. Lit from the upper left: every stone keeps its highlight and its shade
where the light puts them however it turns, so the ring reads as stones on a
dome rather than as a cog.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

SIZE = 108
RIG = Rig()
B = RIG.bones
bone = RIG.bone
bone("body", None, (0.0, 0.0), 0.0)

# ============================================================== legs
# Eight legs, four a side, symmetric about the x axis. A leg's hip is on the
# mass under the ring; its foot comes out just past the stones; the knee is
# thrown to the front on the fore pairs and to the back on the hind pairs, so
# the silhouette between the stones is a row of short elbows. Short and thick:
# the thing is a heavy dome that shuffles, and a first draw with femurs as long
# as the mass's radius read as a spider standing over a ball rather than a
# ball walking.
LEG_ANGLES = {"1": 26.0, "2": 70.0, "3": 112.0, "4": 152.0}
HIP_R, FOOT_R = 18.0, 38.5
FEMUR, TIBIA = 12.5, 10.5
SIDES = {"r": 1, "l": -1}  # r: +y (the right side of a body facing +x, seen from above)
def leg_angle(side, n): return SIDES[side] * LEG_ANGLES[n]
def polar(a, r): return (r * math.cos(R(a)), r * math.sin(R(a)))
def hip_of(side, n): return polar(leg_angle(side, n), HIP_R)
def foot_rest(side, n):
    a = leg_angle(side, n)
    return polar(a, FOOT_R)
def bend_of(side, n):
    """The knee's side: out toward the front on the fore pairs, toward the back on the hind."""
    front = 1 if n in ("1", "2") else -1
    return front * SIDES[side]

LEGS = [(s, n) for n in ("4", "3", "2", "1") for s in ("r", "l")]
for side, n in LEGS:
    h = hip_of(side, n)
    hf, ht = ik(h, foot_rest(side, n), FEMUR, TIBIA, bend_of(side, n))
    f = bone(f"leg_{side}{n}_femur", "body", h, hf, FEMUR)
    t = bone(f"leg_{side}{n}_tibia", f.name, f.end(), ht, TIBIA)
RIG.seal()
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
HAIR_SLATE = {"color": "$slate.dark2", "width": "hair"}
EDGE = {"color": "$slate.dark2", "width": "thin"}  # the masses' edge: the darkest slate rather than ink
parts_order = []  # (kind, id) so the ring can be slotted in between the rig's parts

def leg_parts(side, n):
    L = f"leg_{side}{n}"
    at, a = on_bone(f"{L}_tibia")
    put(f"{L}_tibia", f"{L}_tibia", at, a, bar(TIBIA, 4.6, 3.6, 0.8), "$slate.light", HAIR_SLATE)
    # A blunt pad at the tibia's tip: it stands on the sand rather than spears it.
    at, a = on_bone(f"{L}_tibia", TIBIA + 0.4)
    put(f"{L}_foot", f"{L}_tibia", at, a, ell(2.2, 2.4),
        "$slate.dark2")
    at, a = on_bone(f"{L}_femur")
    put(f"{L}_femur", f"{L}_femur", at, a, bar(FEMUR, 5.8, 5.0, 1.0), "$slate.light", HAIR_SLATE)
    at, a = on_bone(f"{L}_femur", FEMUR * 0.45, -0.9 * SIDES[side])
    put(f"{L}_femur_lit", f"{L}_femur", at, a, rect(FEMUR * 0.6, 1.1, 0.55), "$steel@soft")
    at, a = on_bone(f"{L}_tibia")
    put(f"{L}_knee", f"{L}_tibia", at, 0.0, circ(2.6), "$steel", HAIR_SLATE)

for side, n in LEGS:
    leg_parts(side, n)

# ---- the mass: a low dome, slate under a crust of rime, lit from the upper left
MASS_R = 24.0
put("mass", "body", (0, 0), 0, circ(MASS_R), "$steel", EDGE)
put("mass_shade", "body", (0, 0), 0,
    poly([polar(a, MASS_R - 0.3) for a in range(-30, 151, 12)] +
         [(polar(a, MASS_R - 7.0)[0] + 3.0, polar(a, MASS_R - 7.0)[1] + 3.0) for a in range(150, -31, -12)]), "$steel.dark")
put("mass_light", "body", (-4.0, -5.0), -30.0, ell(16.0, 12.5), "$steel.light")
put("mass_gloss", "body", (-9.0, -10.0), -35.0, ell(6.0, 3.2), "$silent@heavy")
put("rime", "body", (-2.0, -2.0), 0, None, "$frost.light@soft")
RIG.parts[-1].pop("shape")
RIG.parts[-1]["repeat"] = {"of": {"kind": "circle", "r": 1.5}, "count": 16, "area": [36, 36], "seed": 21, "scaleRange": [0.6, 1.4]}
put("crack_a", "body", (0, 0), 0, poly([(-15.0, -5.0), (-6.0, -2.0), (-1.0, -9.0), (1.5, -15.0), (0.0, -8.5), (-5.0, 0.0), (-14.0, -3.0)]), "$ink@heavy", opacity=0)
put("crack_b", "body", (0, 0), 0, poly([(3.0, 4.0), (10.0, 9.0), (17.0, 8.5), (16.0, 10.0), (10.0, 11.0), (2.0, 6.0)]), "$ink@heavy", opacity=0)
put("crack_c", "body", (0, 0), 0, poly([(-9.0, 11.0), (-4.0, 15.0), (-5.0, 19.0), (-6.0, 16.0), (-10.0, 13.0)]), "$ink@heavy", opacity=0)
N_BODY = len(RIG.parts)  # the ring goes on after this

# ---- the face: a pit at +x with three frost eyes in it, a brow of slate over it
put("brow", "body", (13.0, 0.0), 0, ell(10.0, 9.2), "$slate.light", HAIR_SLATE)
put("pit", "body", (15.0, 0.0), 0, ell(7.4, 7.0), "$ink")
for n, (x, y, r) in {"a": (13.6, -3.2, 2.4), "b": (17.4, 0.0, 2.8), "c": (13.6, 3.2, 2.4)}.items():
    put(f"eye_{n}", "body", (x, y), 0, circ(r), "$frost")
    put(f"eye_{n}_core", "body", (x - 0.4 * r, y - 0.4 * r), 0, circ(r * 0.42), "$silent")
RIG.use("organ", "body", (-4.0, 0.0), "ss.lib.organ", scale=[1.5, 1.2])
RIG.check()

# ============================================================== the ring
# Twelve stones round the rim. Everything about a stone is a function of the
# angle it is at (so the ring can creep and stay seamless): its size swells
# three times round, it stands a touch further out where it is bigger, and it
# is tilted by a wobble of the angle so the twelve are not twelve copies.
N_STONES = 12
RING_R = 28.0
def stone_size(a): return 1.0 + 0.13 * math.cos(R(3 * a))
def stone_r(a): return RING_R + 1.4 * math.cos(R(3 * a))
def stone_tilt(a): return a + 22.0 * math.sin(R(5 * a))
STONE = [(7.4, 0), (6.0, 40), (7.2, 82), (6.3, 128), (7.6, 170), (6.1, 212), (7.0, 258), (6.5, 304)]  # (radius, bearing)
STONE_PTS = [polar(b, r) for r, b in STONE]
# The light's marks, fixed to the world rather than to the stone: a frost face
# up-left and a shade down-right, both inside the smallest outline.
FACE = poly([(-4.4, -1.2), (-2.6, -4.2), (0.6, -4.6), (0.2, -1.6), (-2.8, 0.4)])
SHADE = poly([polar(a, 5.4) for a in range(-10, 111, 20)] + [(polar(a, 3.0)[0] + 0.8, polar(a, 3.0)[1] + 0.8) for a in range(110, -11, -20)])
FACE_AT, SHADE_AT = (0.0, 0.0), (0.0, 0.0)
STONE_A0 = [15.0 + 30.0 * k for k in range(N_STONES)]

def stone_parts():
    out = []
    for k, a in enumerate(STONE_A0):
        s = stone_size(a)
        x, y = polar(a, stone_r(a))
        out.append({"id": f"stone_{k}", "at": [r2(x), r2(y)], "rot": r2(stone_tilt(a)), "scale": r2(s), "shape": poly(STONE_PTS),
                    "fill": "$steel.light2", "stroke": EDGE})
        out.append({"id": f"stone_{k}_shade", "at": [r2(x), r2(y)], "scale": r2(s), "shape": SHADE, "fill": "$steel"})
        out.append({"id": f"stone_{k}_face", "at": [r2(x), r2(y)], "scale": r2(s), "shape": FACE, "fill": "$frost.light"})
    return out

def ring_tracks(pose_at, ts, state):
    """
    Tracks for the stones: `state(k, a0, t)` gives a stone's (angle, radial
    offset, scale multiplier, opacity) on the mass, and the mass's own pose
    carries it into the world.
    """
    series = {}
    for t in ts:
        bx, by, bth = RIG.solve(pose_at(t))["body"]
        for k, a0 in enumerate(STONE_A0):
            a, dr, sm, op = state(k, a0, t)
            lx, ly = polar(a, stone_r(a) + dr)
            c, s = math.cos(R(bth)), math.sin(R(bth))
            wx, wy = bx + lx * c - ly * s, by + lx * s + ly * c
            x0, y0 = polar(a0, stone_r(a0))
            sc = stone_size(a) * sm / stone_size(a0)
            rot = wrap(stone_tilt(a) + bth - stone_tilt(a0))
            series.setdefault(k, []).append((t, wx - x0, wy - y0, rot, bth, sc, op))
    out = []
    for k, rows in series.items():
        def tr(pid, prop, i):
            vs = [row[i] for row in rows]
            if prop in ("scale", "opacity"):
                if max(abs(v - 1.0) for v in vs) < 0.005: return None
            elif max(abs(v) for v in vs) < 0.01: return None
            return {"part": pid, "prop": prop, "keys": [[r2(row[0]), r2(row[i])] for row in rows], "ease": "linear"}
        for pid, props in ((f"stone_{k}", (("x", 1), ("y", 2), ("rot", 3), ("scale", 5), ("opacity", 6))),
                           (f"stone_{k}_shade", (("x", 1), ("y", 2), ("rot", 4), ("scale", 5), ("opacity", 6))),
                           (f"stone_{k}_face", (("x", 1), ("y", 2), ("rot", 4), ("scale", 5), ("opacity", 6)))):
            for prop, i in props:
                t_ = tr(pid, prop, i)
                if t_: out.append(t_)
    return out

# ============================================================== motion
def plant(pose, feet):
    world = RIG.solve(pose)
    for side, n in LEGS:
        L = f"leg_{side}{n}"
        hx, hy, _ = world[f"{L}_femur"]
        hf, ht = ik((hx, hy), feet[(side, n)], FEMUR, TIBIA, bend_of(side, n))
        pose[f"abs:{L}_femur"] = hf
        pose[f"abs:{L}_tibia"] = ht
    return pose

def feet_at(fn):
    return {(s, n): fn(s, n) for s, n in LEGS}

# ---- churn: the walk and the idle
# Alternating tetrapods (fore-right, second-left, third-right, hind-left and
# the mirror), two steps a loop; the mass sways toward the planted set, heaves
# at each footfall and turns a little after the sway.
TETRA = {("r", "1"): 0.0, ("l", "2"): 0.0, ("r", "3"): 0.0, ("l", "4"): 0.0,
         ("l", "1"): 0.5, ("r", "2"): 0.5, ("l", "3"): 0.5, ("r", "4"): 0.5}
STRIDE = 4.2
def step(u):
    """Foot travel along x and how far it is drawn in, for a leg at phase `u` of its step."""
    u %= 1.0
    if u < 0.6:
        return lerp(STRIDE, -STRIDE, u / 0.6), 0.0
    v = (u - 0.6) / 0.4
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 4.5 * math.sin(math.pi * v)

def churn_body(t):
    return (1.2 * cyc(4 * t, 0.1), 2.6 * cyc(2 * t, 0.0), 4.5 * cyc(2 * t, -0.18))

def churn_pose(t):
    pose = {"body": churn_body(t)}
    def foot(s, n):
        dx, draw = step(2 * t + TETRA[(s, n)])
        fx, fy = foot_rest(s, n)
        a = R(leg_angle(s, n))
        return (fx + dx - draw * math.cos(a), fy - draw * math.sin(a))
    return plant(pose, feet_at(foot))

def heave_churn(t): return 1.0 + 0.035 * cyc_c(4 * t, 0.5)
SWELL = 3.6
def churn_ring(k, a0, t):
    a = a0 + 30.0 * t  # one place round a loop
    dr = SWELL * math.sin(R(2 * a) - 2 * math.pi * 2 * t)  # two swells running round, twice a loop
    return a, dr, 1.0 + 0.05 * math.sin(R(2 * a) - 2 * math.pi * 2 * t), 1.0

# ---- burst: the ring goes (the game fires on the clip's first frame, so the
# gather is short): the mass clenches and the stones draw in, then every stone
# is thrown out and gone, the mass rebounds past rest; and a new ring rises out
# of the rim, small, and swells back into place.
GATHER, THROW, GONE, REGROW = 0.14, 0.3, 0.42, 0.9
def burst_pose(t):
    g = smooth(0.0, GATHER, t) * (1 - smooth(GATHER, THROW, t))
    kick = smooth(GATHER, THROW, t) * (1 - smooth(THROW, 0.8, t))
    pose = {"body": (0.0, 0.0, 0.0)}
    def foot(s, n):
        fx, fy = foot_rest(s, n)
        a = R(leg_angle(s, n))
        r = -3.0 * g + 3.6 * kick
        return (fx + r * math.cos(a), fy + r * math.sin(a))
    return plant(pose, feet_at(foot))
def heave_burst(t):
    return 1.0 - 0.07 * smooth(0.0, GATHER, t) + 0.15 * smooth(GATHER, THROW, t) - 0.08 * smooth(THROW, 0.62, t) - 0.0 * t
def burst_ring(k, a0, t):
    g = smooth(0.0, GATHER, t)
    out = smooth(GATHER, GONE, t)
    grow = smooth(GONE, REGROW, t)
    if t < GONE:
        dr = -3.2 * g * (1 - out) + 13.0 * out
        sm = 1.0 - 0.1 * g + 0.25 * out
        op = 1.0 - smooth(THROW - 0.04, GONE, t)
    else:
        dr = lerp(-7.0, 0.0, grow) + 1.2 * math.sin(math.pi * smooth(0.62, 1.0, t))  # up out of the rim, a touch past, home
        sm = lerp(0.3, 1.0, grow) + 0.08 * math.sin(math.pi * smooth(0.6, 1.0, t))
        op = smooth(GONE, GONE + 0.14, t)
    return a0, dr, sm, op

# ---- death: a flinch, then every stone thrown at once and gone — the last
# thing it does is the thing it did — while the mass cracks and sinks, the legs
# fold in and the eyes go out one by one. Still from 0.8.
def death_pose(t):
    flinch = math.sin(math.pi * smooth(0.0, 0.18, t))
    fold = smooth(0.2, 0.8, t)
    pose = {"body": (-0.8 * flinch, 0.0, -4.0 * flinch + 6.0 * fold)}
    def foot(s, n):
        fx, fy = foot_rest(s, n)
        a = leg_angle(s, n)
        kick = (3.0 if TETRA[(s, n)] == 0 else -3.0) * flinch
        r = lerp(FOOT_R, HIP_R + 9.0, fold)
        a2 = a + SIDES[s] * (8.0 * fold) + kick
        return polar(a2, r)
    return plant(pose, feet_at(foot))
def heave_death(t): return 1.0 - 0.05 * math.sin(math.pi * smooth(0.0, 0.18, t)) - 0.12 * smooth(0.2, 0.8, t)
def death_ring(k, a0, t):
    g = math.sin(math.pi * smooth(0.0, 0.18, t))
    out = smooth(0.14, 0.55, t)
    # Thrown, and dropped: they land in a loose ring round it, dulled, and lie there.
    return a0, -2.4 * g + 13.5 * out, 1.0 + 0.12 * math.sin(math.pi * out) - 0.1 * out, 1.0 - 0.5 * smooth(0.3, 0.7, t)

MASS_PARTS = ("mass", "mass_shade", "mass_light", "mass_gloss", "rime", "crack_a", "crack_b", "crack_c")
def heave_extra(fn):
    return [(p, "scale", fn) for p in MASS_PARTS]

def clip_tracks(pose_at, ts, ring, heave, extra=()):
    return RIG.tracks(pose_at, ts, heave_extra(heave) + list(extra), still={"leg_" + s + n + "_knee" for s, n in LEGS}) + ring_tracks(pose_at, ts, ring)

animations = {}
TS_CHURN = keyset(52)
animations["churn"] = {
    "description": "The walk and the idle at the standoff, authored at the game's 2.6s cadence: eight legs in two alternating sets of four, each foot planted while the mass sways and turns over it and drawn in on the way forward, two steps a loop; the mass heaves at each footfall; the ring creeps one place round the rim — seamlessly, since each stone takes on the size and tilt of the place it comes to — with two swells running round it twice a loop, the stones rising off the rim as one passes; the eyes pulse out of step.",
    "duration": 2.6,
    "tracks": clip_tracks(churn_pose, TS_CHURN, churn_ring, heave_churn, [
        ("eye_a", "scale", lambda t: 1.0 + 0.1 * cyc(2 * t, 0.0)),
        ("eye_b", "scale", lambda t: 1.0 + 0.1 * cyc(2 * t, 0.33)),
        ("eye_c", "scale", lambda t: 1.0 + 0.1 * cyc(2 * t, 0.66)),
        ("organ", "scale", lambda t: 1.0 + 0.06 * cyc(t, 0.2)),
    ]),
}
TS_DEATH = [i / 40 for i in range(41)]
animations["death"] = {
    "description": "It flinches, then every stone leaves the ring at once — the last thing it does is the thing it did — and they fall dulled in a loose ring round it on the sand, while the mass dims, sinks and turns a little, the legs fold in under it, the eyes go out one by one and the organ flares and dims. Still from 0.8.",
    "duration": 0.8,
    "tracks": clip_tracks(death_pose, TS_DEATH, death_ring, heave_death, [
        ("mass_light", "opacity", lambda t: 1.0 - 0.6 * smooth(0.2, 0.75, t)),
        ("mass_gloss", "opacity", lambda t: 1.0 - smooth(0.2, 0.6, t)),
        ("eye_a", "opacity", lambda t: 1.0 - 0.85 * smooth(0.2, 0.4, t)),
        ("eye_c", "opacity", lambda t: 1.0 - 0.85 * smooth(0.35, 0.55, t)),
        ("eye_b", "opacity", lambda t: 1.0 - 0.85 * smooth(0.5, 0.75, t)),
        ("eye_a_core", "opacity", lambda t: 1.0 - smooth(0.2, 0.35, t)),
        ("eye_c_core", "opacity", lambda t: 1.0 - smooth(0.35, 0.5, t)),
        ("eye_b_core", "opacity", lambda t: 1.0 - smooth(0.5, 0.7, t)),
        ("organ", "scale", lambda t: 1.0 + 0.35 * math.sin(math.pi * smooth(0.1, 0.6, t)) - 0.15 * smooth(0.5, 0.8, t)),
        ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.4, 0.8, t)),
    ]),
}
TS_BURST = [i / 44 for i in range(45)]
animations["burst"] = {
    "description": "The ring goes, authored at the 0.55s the game holds the clip for (the stones leave on its first frame, so the gather is short): the mass clenches and the ring draws in, the legs braced; then every stone is thrown straight out and gone, the mass rebounding past rest and the legs splayed; and a new ring rises out of the rim, small, and swells back into place with a settle — which is what makes this a throw and not the death.",
    "duration": 0.55,
    "tracks": clip_tracks(burst_pose, TS_BURST, burst_ring, heave_burst, [
        ("organ", "scale", lambda t: 1.0 - 0.1 * smooth(0.0, GATHER, t) + 0.4 * smooth(GATHER, THROW, t) - 0.3 * smooth(THROW, 0.8, t)),
        ("eye_a", "scale", lambda t: 1.0 + 0.3 * math.sin(math.pi * smooth(GATHER, 0.6, t))),
        ("eye_b", "scale", lambda t: 1.0 + 0.3 * math.sin(math.pi * smooth(GATHER, 0.6, t))),
        ("eye_c", "scale", lambda t: 1.0 + 0.3 * math.sin(math.pi * smooth(GATHER, 0.6, t))),
    ]),
}

# ============================================================== states
STONES = range(N_STONES)
variants = {
    "enraged": {
        "description": "Halfway: the mass darkened and cracked open along three seams, the cold showing through them, the eyes gone ember, every stone lit from within — frost through and through. It stops standing off here and comes at you, still hailing.",
        "set": {
            "mass.fill": "$slate",
            "mass_shade.fill": "$slate.dark",
            "mass_light.fill": "$slate.light",
            "crack_a.opacity": 1, "crack_b.opacity": 1, "crack_c.opacity": 1,
            "crack_a.fill": "$frost.light@heavy", "crack_b.fill": "$frost.light@heavy", "crack_c.fill": "$frost.light@heavy",
            "eye_a.fill": "$ember", "eye_b.fill": "$ember", "eye_c.fill": "$ember",
            "eye_a_core.fill": "$ember.light2", "eye_b_core.fill": "$ember.light2", "eye_c_core.fill": "$ember.light2",
            "organ.scale": [1.9, 1.5],
            "rime.fill": "$frost@heavy",
            **{f"stone_{k}.fill": "$frost.light" for k in STONES},
            **{f"stone_{k}_shade.fill": "$frost" for k in STONES},
            **{f"stone_{k}_face.fill": "$silent" for k in STONES},
        },
    },
    "final": {
        "description": "Phase three: the eyes are out and the mass under the ring has gone hollow and dark, lit only along the seams it split on. The stones are the one thing left whole — bleached to bone — which is the one thing the fight kept: it has stopped noticing you and it has not stopped throwing, and the ring it throws now spins.",
        "set": {
            "eye_a.fill": "$dead", "eye_b.fill": "$dead", "eye_c.fill": "$dead",
            "eye_a_core.fill": "$ink", "eye_b_core.fill": "$ink", "eye_c_core.fill": "$ink",
            "mass.fill": "$slate.dark",
            "mass_shade.fill": "$slate.dark2",
            "mass_light.fill": "$slate",
            "mass_gloss.opacity": 0,
            "crack_a.opacity": 1, "crack_b.opacity": 1, "crack_c.opacity": 1,
            "crack_a.fill": "$ember@heavy", "crack_b.fill": "$ember@heavy", "crack_c.fill": "$ember@heavy",
            "rime.fill": "$frost@ghost",
            "organ.scale": [2.3, 1.9],
            **{f"stone_{k}.fill": "$bone" for k in STONES},
            **{f"stone_{k}_shade.fill": "$bone.dark" for k in STONES},
            **{f"stone_{k}_face.fill": "$white" for k in STONES},
        },
    },
}

# ============================================================== document
parts = RIG.parts[:N_BODY] + stone_parts() + RIG.parts[N_BODY:]
DESCRIPTION = (
    "The pan's first arrival: it has noticed you, and says so in every direction at once. A boss seen from above, facing +x: a low slate "
    "dome crusted with rime on eight thick legs, knees thrown out between the stones, and twelve steel stones stuck round its rim, each lit "
    "with a frost face — the ring it throws (EnemyType.shotFan, a full turn of `ss.enemy.hailstone`) drawn as the body's own edge, so the "
    "lumpy outline is the attack. A pit at +x with three frost eyes in it under a slate brow, and the organ large in the middle. "
    "Built on a skeleton (scripts/hail.py): the legs are solved every frame to a foot on the ground, so the mass sways over planted feet; "
    "each stone's size, tilt and stand-off are functions of where it is round the rim, so the ring can creep and stay seamless. "
    "`churn` is the walk and the idle, authored at the game's 2.6s cadence: two steps of an alternating tetrapod gait, the mass heaving, the "
    "ring creeping one place round with two swells running round it. `burst` is the throw (`volleyAnim`): a short clench, every stone thrown "
    "out and gone, a new ring rising out of the rim. `enraged` cracks and darkens the mass, turns the eyes ember and lights the stones frost; "
    "`final` puts the eyes out, hollows the mass to seams of ember and bleaches the stones to bone. Symmetric about the x axis, so the game's "
    "mirror is the same body turned round. Gameplay radius 40. The `death` clip throws every stone at once and lets them lie round it where they fall."
)
doc = {
    "id": "ss.enemy.hail",
    "name": "Hail",
    "description": DESCRIPTION,
    "tags": ["enemy", "boss"],
    "size": [SIZE, SIZE],
    "meta": {"radius": 40},
    "parts": parts,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-hail.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(parts)} parts, {len(animations)} clips, {n_tracks} tracks")
