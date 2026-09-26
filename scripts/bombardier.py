"""The Bombardier — a beetle with a mortar on its back, and the shot is its breathing.

    python3 scripts/bombardier.py        # rewrites apps/ss/assets/ss-enemy-bombardier.json

Artillery in the Lance's slot by turns: it stands at 330 and lobs a shell over
your head onto the ground you were about to stand on (feelers: `fireInterval:
3.4`, `fireCue: 0.62`, `shotTex: 'e_shell'`). Its one loop IS the shot: the
game plays `pump` as the idle, time-scales it to exactly the fire interval and
re-seats it at `fireCue` on every shot (EnemySystem.cueCycle), so the sac
swelling before 0.62 is the telegraph — it comes before the shadow does — and
the kick at 0.62 is the shell leaving.

It was hand-placed and it moved three and a half pixels: the sac scaled, the
barrel slid two units and the legs turned about their own centres. This
rebuilds it on the shared rig (scripts/rig.py):

  - the body is a root bone that walks, squats into the brace and is shoved
    back and down by the recoil; the head hangs off it on a neck and the
    antennae are two-link chains that lag the head
  - the mortar is a chamber (the sac) at the rear and a barrel on a trunnion
    bone off it, so the barrel elevates as the sac fills and slides back along
    its own axis on the kick
  - six legs, a femur and a tibia each solved to a foot on the ground (two-bone
    IK); a tripod walk while the sac refills, a shuffle into a braced stance
    for the shot, and back out of it

Colour: rust and coal, the family it had, but in the real insect's order —
the head, pronotum and legs are the warm light value, the elytra the coal
wedge, the chamber ember because what it lobs is (`ss.enemy.shell`).
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 48×48, origin at the centre, +x forward, +y down.
SIZE = [48, 48]
GROUND = 10.6
FAR_LIFT = 1.0
BODY_PIVOT = (-1.0, 1.6)

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, BODY_PIVOT, 0.0)
bone("head", "body", (6.6, 1.4), 16.0, 3.0)
# The antennae: two links each off the front of the head, the near one lower.
for side, root, h0, h1 in (("near", (9.4, -0.6), -44.0, -18.0), ("far", (8.8, -1.4), -62.0, -34.0)):
    b0 = bone(f"{side}_ant_0", "head", root, h0, 3.4)
    bone(f"{side}_ant_1", f"{side}_ant_0", b0.end(), h1, 3.2)
# The mortar: the chamber rides the rear of the body on its own bone (so it
# can swell and burst without moving anything else), and the barrel turns on a
# trunnion at the chamber's centre, pointing up and forward over the head.
CHAMBER_AT = (-9.4, -3.0)
BARREL_HEADING = -47.0
BARREL_LEN = 13.4
bone("chamber", "body", CHAMBER_AT, 0.0, 0.0)
bone("barrel", "chamber", CHAMBER_AT, BARREL_HEADING, BARREL_LEN)

# The legs: three a side under the body, each a femur and a tibia solved to a
# foot on the ground with the knee thrown up and out, and a tarsus.
LEGS = {  # name: (hip, rest foot x, femur, tibia)
    "far_b": ((-5.8, 2.6), -10.6, 4.4, 5.4),
    "far_m": ((-1.2, 3.0), 0.2, 4.0, 5.0),
    "far_f": ((3.2, 2.8), 8.2, 4.0, 5.0),
    "near_b": ((-5.0, 3.8), -10.0, 4.6, 5.8),
    "near_m": ((-0.4, 4.2), 1.6, 4.2, 5.4),
    "near_f": ((4.0, 3.8), 9.8, 4.2, 5.4),
}
def ground_of(leg): return GROUND - (FAR_LIFT if leg.startswith("far") else 0.0)
def knee_bend(leg): return 1 if leg.endswith("_f") or leg.endswith("_m") else -1
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, knee_bend(leg))
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", RIG.end_of(f"{leg}_femur"), ht, lt)
    bone(f"{leg}_tarsus", f"{leg}_tibia", RIG.end_of(f"{leg}_tibia"), 0.0 if knee_bend(leg) > 0 else 180.0, 1.8)

RIG.seal()
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
# The palette, by value. WARM is the head, pronotum and near legs; the coal
# wedge and the dark legs are the dark value; the chamber is the light one.
WARM, WARM_SHADE = "$rust", "$rust.dark"
LEG_LIGHT, LEG_MID, LEG_DARK = "$rust", "$rust.dark", "$dead"
def leg_parts(leg, femur, tibia, tarsus, stroke):
    b = BONES
    at, a = on_bone(f"{leg}_tarsus"); put(f"{leg}_tarsus", f"{leg}_tarsus", at, a, bar(1.8, 1.0, 0.6, 0.4), tarsus, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(b[f"{leg}_tibia"].length, 1.5, 0.9), tibia, stroke)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(b[f"{leg}_femur"].length, 2.2, 1.6), femur, stroke)

# ---- far side: antenna and legs, a step darker, behind everything
at, a = on_bone("far_ant_0"); put("far_ant_0", "far_ant_0", at, a, bar(3.4, 0.9, 0.7, 0.3), LEG_MID)
at, a = on_bone("far_ant_1"); put("far_ant_1", "far_ant_1", at, a, bar(3.2, 0.7, 0.9, 0.3), LEG_MID)
for leg in ("far_b", "far_m", "far_f"):
    leg_parts(leg, LEG_MID, LEG_DARK, LEG_DARK, None)

# ---- the mortar's glow, behind the body so it haloes the rear
put("chamber_glow", "chamber", CHAMBER_AT, 0.0, circ(6.4), "$ember@ghost")

# ---- the barrel, behind the chamber and the elytra: a coal tube with a rust
# band and an ember lip. Its origin is the trunnion, so it turns about it.
at, a = on_bone("barrel")
put("barrel", "barrel", at, a, poly([(-1.0, -1.6), (BARREL_LEN - 1.0, -1.7), (BARREL_LEN, -2.0), (BARREL_LEN + 0.6, -2.0),
                                      (BARREL_LEN + 0.6, 2.0), (BARREL_LEN, 2.0), (BARREL_LEN - 1.0, 1.7), (-1.0, 1.6)]), "$coal", INK_THIN)
at, a = on_bone("barrel", 5.2)
put("barrel_band", "barrel", at, a, rect(1.6, 3.8, 0.5), "$rust.light")
at, a = on_bone("barrel", 9.4)
put("barrel_band_2", "barrel", at, a, rect(1.0, 3.6, 0.4), "$rust")
at, a = on_bone("barrel", 6.0, -0.9)
put("barrel_gloss", "barrel", at, a, rect(8.0, 0.6, 0.3), "$white@0.25")
at, a = on_bone("barrel", BARREL_LEN + 0.6)
put("muzzle", "barrel", at, a, ell(0.9, 2.0), "$ember", INK_HAIR)
# The flash and the smoke are drawn at a twentieth of their size and grown by
# their clips' scale tracks (which multiply), so the still drawing has neither.
HIDE = 0.01
at, a = on_bone("barrel", BARREL_LEN + 3.4)
put("flash", "barrel", at, a, poly([(-2.6, 0.0), (-0.6, -1.8), (0.4, -3.6), (1.2, -1.4), (3.8, 0.0), (1.2, 1.4), (0.4, 3.6), (-0.6, 1.8)]),
    "$gold.light@heavy", scale=HIDE)
at, a = on_bone("barrel", BARREL_LEN + 4.4)
put("puff", "barrel", at, a, circ(2.6), "$husk@soft", scale=HIDE)

# ---- the body: abdomen underneath, the coal elytra in a wedge over it
ABDOMEN = [(-11.4, 0.4), (-10.2, 3.2), (-5.6, 4.8), (1.0, 4.8), (5.2, 3.6), (5.4, 0.6), (-10.6, -0.6)]
put("abdomen", "body", (0, 0), 0, poly(ABDOMEN), WARM_SHADE, INK_HAIR)
for i, x in enumerate((-7.8, -4.6, -1.4, 1.8)):
    put(f"sternite_{i}", "body", (x, 3.9), 10.0, rect(0.6, 1.8, 0.3), "$rust.dark")
# The elytra: low at the rear and rising to the shoulders, so the body is a
# wedge with the tube on it. The seam along the top, a sheen on the shoulder.
ELYTRA = [(-12.4, 1.0), (-12.8, -1.4), (-11.4, -4.2), (-7.6, -6.4), (-2.4, -7.2), (2.4, -6.6), (5.4, -4.6),
          (6.2, -1.6), (5.6, 1.4), (1.0, 2.6), (-5.0, 2.8), (-10.4, 2.2)]
put("elytra", "body", (0, 0), 0, poly(ELYTRA), "$coal", INK_THIN)
put("elytra_sheen", "body", (0, 0), 0,
    poly([(-11.2, -3.6), (-7.4, -5.8), (-2.4, -6.6), (2.2, -6.0), (4.8, -4.4), (2.6, -4.6), (-2.4, -5.2), (-7.0, -4.6), (-10.4, -2.6)]),
    "$coal.light")
put("elytra_seam", "body", (0, 0), 0,
    poly([(-12.2, 0.4), (-5.0, 1.4), (1.0, 1.2), (5.6, 0.0), (5.6, 1.4), (1.0, 2.6), (-5.0, 2.8), (-10.4, 2.2)]), "$rust")
for i, (x, y, rot) in enumerate(((-6.6, -2.6, -8.0), (-1.4, -3.2, 2.0))):
    put(f"stria_{i}", "body", (x, y), rot, ell(3.8, 0.35), "$ink")
put("gloss", "body", (-3.4, -5.6), -6.0, ell(3.2, 0.7), "$white@0.4")
# The hive's organ on the elytra, in front of the mortar.
RIG.use("organ", "body", (-2.0, -2.2), "ss.lib.organ", scale=[0.5, 0.42])

# ---- the chamber, over the rear of the elytra: the sac that swells
put("chamber", "chamber", CHAMBER_AT, 0.0, circ(3.9), "$ember.dark", INK_THIN)
put("chamber_core", "chamber", (CHAMBER_AT[0] + 0.3, CHAMBER_AT[1] - 0.4), 0.0, circ(2.1), "$ember")
put("chamber_hot", "chamber", (CHAMBER_AT[0] - 0.6, CHAMBER_AT[1] - 1.4), 0.0, circ(0.8), "$gold.light")
# The burst, for the death: nothing until it goes off.
put("burst", "chamber", CHAMBER_AT, 0.0, poly([(-5.0, 0.0), (-1.6, -1.6), (0.0, -5.0), (1.6, -1.6), (5.0, 0.0), (1.6, 1.6), (0.0, 5.0), (-1.6, 1.6)]),
    "$gold.light@heavy", scale=HIDE)

# ---- the pronotum and the head: the warm light value
PRONOTUM = [(4.2, -4.6), (7.2, -5.0), (9.0, -3.2), (9.4, 0.2), (8.4, 3.2), (5.2, 3.6), (4.0, 0.0)]
put("pronotum", "body", (0, 0), 0, poly(PRONOTUM), WARM, INK_THIN)
put("pronotum_shade", "body", (0, 0), 0, poly([(4.4, 1.2), (9.2, 1.0), (8.4, 3.2), (5.2, 3.6)]), WARM_SHADE)
put("pronotum_gloss", "body", (6.8, -3.4), -14.0, ell(1.6, 0.5), "$white@0.45")
at, a = on_bone("head", 2.4, 0.2)
put("head", "head", at, 0.0, ell(3.1, 2.7), WARM, INK_HAIR)
at, a = on_bone("head", 4.4, 1.6)
put("mandible", "head", at, 20.0, poly([(-0.8, -0.7), (1.2, -0.5), (2.2, 0.6), (0.6, 0.6), (-0.8, 0.8)]), "$rust", INK_HAIR)
at, a = on_bone("head", 3.0, -0.6)
put("eye", "head", at, 0.0, circ(1.0), "$ink")
put("eye_glint", "head", (at[0] + 0.35, at[1] - 0.35), 0.0, circ(0.32), "$white")

# ---- near side: antenna and legs over everything
at, a = on_bone("near_ant_0"); put("near_ant_0", "near_ant_0", at, a, bar(3.4, 1.0, 0.8, 0.3), LEG_LIGHT, INK_HAIR)
at, a = on_bone("near_ant_1"); put("near_ant_1", "near_ant_1", at, a, bar(3.2, 0.8, 1.0, 0.3), LEG_LIGHT, INK_HAIR)
for leg in ("near_b", "near_m", "near_f"):
    leg_parts(leg, LEG_LIGHT, LEG_MID, LEG_MID, INK_HAIR)

RIG.check()

# ============================================================== motion
def plant_legs(pose, feet):
    world = solve(pose)
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, knee_bend(leg))
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_tarsus"] = BONES[f"{leg}_tarsus"].heading
    return pose

def rest_feet():
    return {leg: (fx, ground_of(leg)) for leg, (hip, fx, lf, lt) in LEGS.items()}

# ---- pump: 3.4s, and the shot at CUE. The phases of one cycle:
#   0.70 → 0.60   the sac refills: slow at first, then pumping harder and
#                 faster — the telegraph, which is most of the cycle
#   0.46 → 0.56   it stops walking and braces: the feet shuffle into a wide
#                 stance, the body squats and tips back, the barrel rises
#   0.60          the kick — the frame the game seats the cycle to when the
#                 shell leaves (cueCycle): barrel slammed back down its own
#                 axis, the body shoved back and down onto its legs, the sac
#                 spent, a flash at the muzzle
#   0.62 → 0.80   recovery: the body rocks forward past rest and settles, the
#                 barrel runs back out, smoke drifts off the muzzle
#   0.80 → 0.46   walking again (a tripod gait) while the sac refills
# The kick lands at 0.600 rather than 0.62 on purpose: Phaser seats a
# 48-frame sheet at the frame whose progress (i/47) is nearest 0.62, which is
# frame 29, and bakeSheet samples frame i at i/48 — so that frame shows the clip
# at 0.604. A kick that started at 0.62 would be seated one frame early, on the
# fullest swell instead of the shot.
PUMP = 3.4
CUE = 0.62
KICK = 0.600
REFILL = 0.70

def swell(t):
    """0 when spent, 1 at the fullest, just before the kick."""
    u = ((t - REFILL) % 1.0) / ((KICK - REFILL) % 1.0)
    if u > 1.0: return 0.0
    base = u ** 1.8
    # The pump: throbs that come faster and harder as it fills.
    beat = math.sin(2 * math.pi * (3.0 * u + 3.0 * u * u)) * 0.12 * u
    return max(0.0, base + beat)

def spent(t):
    """The sac emptying at the kick: 1 at the kick, holding briefly, 0 by the refill."""
    if KICK <= t < REFILL:
        return 1.0 - smooth(KICK + 0.03, REFILL, t)
    return 0.0

def kick(t):
    """The recoil impulse: slams to 1 at the kick, then a damped swing back through rest."""
    if t < KICK - 0.004: return 0.0
    if t < KICK + 0.012: return smooth(KICK - 0.004, KICK + 0.012, t)
    d = (t - KICK - 0.012) / 0.2
    if d > 1.0: return 0.0
    return math.exp(-3.2 * d) * math.cos(math.pi * 1.5 * d) * (1 - smooth(0.8, 1.0, d))

def brace(t):
    return smooth(0.44, 0.56, t) * (1 - smooth(0.76, 0.88, t))

# The walk: a tripod gait whose phase only advances while it is walking, so
# the feet stop where they are in the brace and pick up from there after it.
STRIDE = 2.3
TRIPOD = {"near_f": 0.0, "near_b": 0.0, "far_m": 0.0, "near_m": 0.5, "far_f": 0.5, "far_b": 0.5}
STEPS = 4  # stride cycles per loop
_N = 2000
_w = [1.0 - brace((i + 0.5) / _N) for i in range(_N)]
_cum = [0.0]
for v in _w: _cum.append(_cum[-1] + v)
def gait_phase(t):
    i = min(_N, max(0, int(round(t * _N))))
    return STEPS * _cum[i] / _cum[-1]

def step(u):
    u %= 1.0
    if u < 0.55:
        return lerp(STRIDE, -STRIDE, u / 0.55), 0.0
    v = (u - 0.55) / 0.45
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 2.0 * math.sin(math.pi * v)

def pump_pose(t):
    s, k, b = swell(t), kick(t), brace(t)
    ph = gait_phase(t)
    walk = 1.0 - b
    # Body: a bob per tripod while walking; squats and tips back into the
    # brace as the sac fills; shoved back and down by the kick.
    bob = 0.6 * walk * (0.5 - 0.5 * math.cos(4 * math.pi * ph))
    sway = 0.6 * walk * math.sin(2 * math.pi * ph)
    pitch_walk = 1.4 * walk * math.sin(4 * math.pi * ph + 0.8)
    dx = sway - 1.2 * b * s - 2.4 * k
    dy = bob + 1.4 * b * s + 2.0 * max(0.0, k) - 0.6 * max(0.0, -k)
    dth = pitch_walk - 7.0 * b * s - 9.0 * k
    pose = {"body": (dx, dy, dth)}
    # The barrel: carried low while it reloads, and climbing as the sac fills
    # until it stands at its steepest for the shot — the aim is the swell made
    # visible — then thrown up by the kick and let down again.
    pose["barrel"] = 16.0 - 30.0 * s - 6.0 * k
    # The head: nods with the step, ducks into the brace, snaps on the kick.
    pose["head"] = 5.0 * walk * math.sin(4 * math.pi * ph - 0.6) + 6.0 * b * s + 14.0 * k
    # The antennae: a wave lagging the head, flung back by the kick.
    for side, ph0 in (("near", 0.0), ("far", 0.18)):
        pose[f"{side}_ant_0"] = 10.0 * math.sin(2 * math.pi * (2 * ph - ph0)) * walk - 8.0 * b * s - 26.0 * k
        pose[f"{side}_ant_1"] = 14.0 * math.sin(2 * math.pi * (2 * ph - ph0 - 0.15)) * walk - 6.0 * b * s - 30.0 * kick(t - 0.012)
    # The feet: the gait while walking, spread into the braced stance for the
    # shot (front feet forward, rear feet back — the stance of a thing about to
    # be pushed).
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        gx, lift = step(ph + TRIPOD[leg])
        spread = 1.4 if leg.endswith("_f") else (-1.4 if leg.endswith("_b") else 0.0)
        x = lerp(fx + gx, fx + spread, b)
        feet[leg] = (x, ground_of(leg) - lift * walk)
    return plant_legs(pose, feet)

def barrel_slide(t):
    """How far the barrel is driven back down its own axis: the recoil."""
    k = kick(t)
    return -3.2 * max(0.0, k) + 0.6 * max(0.0, -k)

# ---- death: 0.46s. The chamber goes first — one flare and it bursts — then
# the barrel falls back over the abdomen, the body sags on legs that fold,
# the head drops, and the organ goes out. Still from 0.85.
def death_pose(t):
    flare = smooth(0.0, 0.16, t)
    pop = smooth(0.16, 0.24, t)
    fall = smooth(0.2, 0.8, t)
    jolt = math.sin(math.pi * smooth(0.16, 0.4, t))
    pose = {"body": (-1.2 * jolt, lerp(0.0, 3.4, fall) - 0.6 * flare * (1 - pop), lerp(0.0, 4.0, fall) - 6.0 * jolt)}
    pose["barrel"] = -8.0 * flare * (1 - pop) - 74.0 * smooth(0.2, 0.62, t) + 6.0 * math.sin(math.pi * smooth(0.55, 0.8, t))
    pose["head"] = 22.0 * smooth(0.3, 0.8, t)
    for side in ("near", "far"):
        pose[f"{side}_ant_0"] = -20.0 * jolt + 40.0 * fall
        pose[f"{side}_ant_1"] = 30.0 * fall
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        out = (fx - hip[0]) * 0.35 * fall
        feet[leg] = (fx + out, ground_of(leg))
    return plant_legs(pose, feet)

def with_slide(tracks, ts, fn, parts=("barrel", "barrel_band", "barrel_band_2", "barrel_gloss", "muzzle", "flash", "puff")):
    """Add a slide of `fn(t)` along the barrel's posed axis to the barrel parts' x/y tracks."""
    world = [solve(pump_pose(t))["barrel"][2] for t in ts]
    by = {(tr["part"], tr["prop"]): tr for tr in tracks}
    for p in parts:
        for prop, trig in (("x", math.cos), ("y", math.sin)):
            tr = by.get((p, prop))
            if tr is None:
                tr = {"part": p, "prop": prop, "keys": [[r2(t), 0.0] for t in ts], "ease": "linear"}
                tracks.append(tr); by[(p, prop)] = tr
            for key, t, h in zip(tr["keys"], ts, world):
                key[1] = r2(key[1] + fn(t) * trig(R(h)))
    return tracks

animations = {}
# Keys: dense round the kick so the slam is one frame wide and the swing back
# is drawn, even across the cycle elsewhere.
TS_PUMP = sorted(set([i / 60 for i in range(61)] + [KICK - 0.004, KICK, 0.604, 0.608, KICK + 0.012, 0.62, 0.625, 0.63, 0.635, 0.64, 0.645, 0.65, 0.66, 0.67, 0.68]))
TS_PUMP = [round(t, 4) for t in TS_PUMP]
def glow_s(t): return 0.7 + 0.75 * swell(t) - 0.35 * spent(t)
def flash_on(t):
    if t < KICK - 0.004: return 0.0
    return smooth(KICK - 0.004, KICK + 0.004, t) * (1 - smooth(KICK + 0.035, KICK + 0.1, t))
def puff_on(t):
    if t < KICK: return 0.0
    return smooth(KICK, KICK + 0.02, t) * (1 - smooth(KICK + 0.08, KICK + 0.3, t))
PUMP_EXTRA = [
    ("chamber", "scale", lambda t: 0.8 + 0.52 * swell(t) - 0.1 * spent(t)),
    ("chamber_core", "scale", lambda t: 0.55 + 0.95 * swell(t) - 0.2 * spent(t)),
    ("chamber_hot", "opacity", lambda t: 0.2 + 0.8 * swell(t) ** 2),
    ("chamber_glow", "scale", glow_s),
    ("chamber_glow", "opacity", lambda t: 0.5 + 0.5 * swell(t)),
    ("flash", "opacity", flash_on),
    ("flash", "scale", lambda t: (1.3 + 0.7 * smooth(KICK, KICK + 0.06, t)) / HIDE),
    ("puff", "opacity", puff_on),
    ("puff", "scale", lambda t: (0.5 + 1.2 * smooth(KICK, KICK + 0.3, t)) / HIDE),
    ("muzzle", "scale", lambda t: 1.0 + 0.3 * swell(t) + 0.4 * flash_on(t)),
    ("organ", "scale", lambda t: 1.0 + 0.1 * swell(t)),
]
animations["pump"] = {
    "description": "The shot, on the game's cadence (3.4s = fireInterval; the game re-seats it at fireCue 0.62 on every shot): from 0.70 the sac refills, slowly and then pumping in harder, faster throbs while its glow builds — the telegraph; it walks on a tripod gait while it fills, then from 0.46 stops, shuffles its feet wide and squats, tipping back so the barrel rises. At 0.60 — the frame the game seats to at the shot — the kick: the barrel slams back down its own axis with a flash at the muzzle, the body is shoved back and down onto its braced legs, the sac is spent, the antennae are flung back; then it rocks forward past rest and settles while smoke drifts off the muzzle, and walks on.",
    "duration": PUMP,
    "tracks": with_slide(RIG.tracks(pump_pose, TS_PUMP, PUMP_EXTRA, still=("chamber", "chamber_core", "chamber_hot", "chamber_glow")), TS_PUMP, barrel_slide),
}
TS_DEATH = [0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.24, 0.28, 0.32, 0.36, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The chamber goes first: one flare — the sac and its glow blowing up — and it bursts, the flash going off on nothing; the barrel falls back over the abdomen, the body sags onto legs that splay and fold, the head drops, the antennae droop, and the organ and the chamber go out. Still from 0.85.",
    "duration": 0.46,
    "tracks": RIG.tracks(death_pose, TS_DEATH, [
        ("chamber", "scale", lambda t: 0.84 + 0.5 * smooth(0.0, 0.16, t) - 0.7 * smooth(0.16, 0.26, t)),
        ("chamber_core", "scale", lambda t: 0.6 + 0.9 * smooth(0.0, 0.16, t) - 1.2 * smooth(0.16, 0.24, t)),
        ("chamber_core", "opacity", lambda t: 1.0 - smooth(0.16, 0.3, t)),
        ("chamber", "opacity", lambda t: 1.0 - 0.45 * smooth(0.2, 0.6, t)),
        ("chamber_hot", "opacity", lambda t: 0.2 + 0.8 * smooth(0.0, 0.14, t) - smooth(0.16, 0.22, t)),
        ("chamber_glow", "scale", lambda t: 0.7 + 1.2 * smooth(0.0, 0.18, t) - 0.9 * smooth(0.2, 0.5, t)),
        ("chamber_glow", "opacity", lambda t: 0.5 + 0.5 * smooth(0.0, 0.16, t) - smooth(0.2, 0.55, t)),
        ("burst", "opacity", lambda t: smooth(0.14, 0.18, t) * (1 - smooth(0.26, 0.42, t))),
        ("burst", "scale", lambda t: (0.4 + 1.1 * smooth(0.14, 0.34, t)) / HIDE),
        ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.2, 0.75, t)),
        ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.25, 0.6, t)),
    ], still=("chamber", "chamber_core", "chamber_hot", "chamber_glow", "burst")),
}

# ============================================================== document
DESCRIPTION = (
    "Artillery, in the Lance's slot by turns. A bombardier beetle seen side-on: a warm chitin head, pronotum and legs, coal elytra in a "
    "low wedge rising to the shoulders, and over the back a mortar — a round chamber at the rear, ember and glowing, with a coal barrel off "
    "it pointing up and forward over the head, so the whole silhouette is a wedge with a tube on it. That is the read at a squad's distance "
    "and it is nothing like the Sprayer's raised sac, which is the other body that fires over its own head. Ember, because what it lobs is "
    "`ss.enemy.shell`. Built on a skeleton (scripts/bombardier.py): the barrel turns on a trunnion at the chamber, the head and antennae hang "
    "off the body, and six legs are solved every frame to feet on the ground. The one clip is `pump`, authored at the game's own 3.4s cadence "
    "(EnemyType.fireInterval, re-seated at fireCue 0.62 on every shot): the sac refills in harder and faster throbs while it walks, it braces and "
    "tips back, and at the cue the barrel slams back with a muzzle flash and the body is shoved down onto its legs — the cycle is the shot, the "
    "way a Gland's is. No `elite` variant: a squad body is never marked. Drawn facing +x, mirrored by the game. Gameplay radius 12. The `death` "
    "clip bursts the chamber first."
)

Y0 = 2.0
for p in RIG.parts: p["at"] = [p["at"][0], r2(p["at"][1] + Y0)]
SKELETON = RIG.skeleton()
SKELETON["joints"] = {k: [v[0], r2(v[1] + Y0)] for k, v in SKELETON["joints"].items()}

doc = {
    "id": "ss.enemy.bombardier",
    "name": "Bombardier",
    "description": DESCRIPTION,
    "tags": ["enemy", "bombardier"],
    "size": SIZE,
    "meta": {"radius": 12},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": SKELETON,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-bombardier.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
