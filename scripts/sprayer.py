"""The Sprayer — an ant that turns its gaster over its back and empties it down the passage.

    python3 scripts/sprayer.py        # rewrites apps/ss/assets/ss-enemy-sprayer.json

The burrow's Gland slot (feelers `sprayer`: standoff 240, fireInterval 1.7,
shotTex `e_spray`): it holds one chamber's distance and pumps a jet at you.
The posture is the whole silhouette and the whole tell — the gaster carried
high over the back with the acidopore aimed forward, so a body standing at
the far end of a corridor still reads as loaded — and that is kept. What was
missing was the pump: the loop moved under four pixels at game scale.

Its one clip, `charge`, is written the way the Plains Gland's `spit` is: as
the shot cycle, not an idle. The draw, the swell and the bead growing at the
pore are the telegraph, and the jet leaves at CUE. The game does not seat it
yet — the sprayer has no `fireCue`, so today `charge` loops on its own 1.5s
and the shot is on the 1.7s clock — but the clip is authored so that adding
`fireCue: 0.71` to the sprayer in feelers (EnemySystem.cueCycle time-scales
the clip to fireInterval and re-seats it there on every shot) puts the jet
leaving the nozzle on the frame the real spray appears next to.

Which frame that is: bakeSheet samples frame i of an n-frame sheet at i/n,
and Phaser's setProgress(0.71) shows the frame whose progress i/(n-1) is
nearest. At 15 fps (n 23) that is frame 16, baked at 0.696; at 20 fps
(n 30) frame 21 at 0.700; at 24 fps (n 36) frame 25 at 0.694; at 30 fps
(n 45) frame 31 at 0.689. The frame before is at 0.652 / 0.667 / 0.667 /
0.667. So the release is authored inside 0.668–0.686: every frame before the
seated one is the loaded pose with the bead fat on the pore, and the seated
frame is the jet out of the nozzle with the gaster clenched — at any of the
four rates.

Rebuilt on the shared rig (scripts/rig.py):

  - the body is a root bone pivoting at the petiole: it crouches for the
    draw, leans back to aim and is shoved back by the recoil
  - the gaster is a chain off the petiole — three sacs and the nozzle, each
    hanging from the end of the last — so the curl tightens, lifts and is
    thrown back as one arch; each sac sits on a bone of its own at its centre
    and swells about it, the pressure running up the chain toward the nozzle
  - the head hangs off a neck and scans; two elbowed antennae lag it
  - six legs, a femur, a tibia and a tarsus each, solved to feet on the
    floor: a shuffle while it refills, braced wide for the shot

Colour: the teal family it had — the Gland's, because what it pumps out is
teal (`ss.enemy.spray`) — in three values: the gaster mid teal with a lit rim
and a dark underside and bands, the thorax and head a step darker, the legs
the hive's dark carapace. The bright teal is kept for what is charged: the
bead on the pore and the jet.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 compose, invert_apply, poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 36×32, origin at the centre, +x forward, +y down.
SIZE = [36, 32]
GROUND = 8.8
FAR_LIFT = 0.9
PETIOLE = (-4.6, 1.6)

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, PETIOLE, 0.0)
NECK = (3.0, 0.8)
bone("head", "body", NECK, -6.0, 3.0)
ANT = {  # side: (root, scape heading, scape len, funiculus heading, funiculus len)
    "near": ((6.8, -1.6), -58.0, 3.2, -2.0, 3.8),
    "far": ((6.2, -2.0), -76.0, 3.0, -20.0, 3.4),
}
for side, (root, h0, l0, h1, l1) in ANT.items():
    b0 = bone(f"{side}_scape", "head", root, h0, l0)
    bone(f"{side}_funic", f"{side}_scape", b0.end(), h1, l1)

# The gaster: up and back off the petiole, over the top and forward, the
# nozzle pointing down the passage over the head. (length, rest heading)
GASTER = [(4.2, -122.0), (5.0, -76.0), (4.4, -14.0)]
NOZZLE_LEN = 3.2
NOZZLE_HEADING = 12.0
GAS = RIG.chain("gas", "body", PETIOLE, GASTER)
bone("nozzle", GAS[-1], RIG.end_of(GAS[-1]), NOZZLE_HEADING, NOZZLE_LEN)
# the sacs, one on each gaster link at its middle, a little off the line to
# the outside of the curl (up/back), so the arch is fat on its outside
SAC = [(3.8, 3.4), (4.8, 4.4), (3.9, 3.4)]  # (along-radius, across-radius)
SAC_OUT = [-0.4, -0.6, -0.4]
for k, (L, h) in enumerate(GASTER):
    at, a = RIG.on_bone(f"gas_{k}", L * 0.5, SAC_OUT[k])
    bone(f"sac_{k}", f"gas_{k}", at, a, 0.0)

LEGS = {  # name: (hip, rest foot x, femur, tibia)
    "far_b": ((-2.6, 2.8), -5.6, 2.9, 3.3),
    "far_m": ((-0.8, 3.0), -0.2, 2.8, 3.2),
    "far_f": ((1.0, 2.8), 4.2, 2.8, 3.2),
    "near_b": ((-2.0, 3.4), -5.0, 3.0, 3.4),
    "near_m": ((-0.2, 3.6), 0.6, 2.9, 3.3),
    "near_f": ((1.6, 3.4), 5.0, 2.9, 3.3),
}
TARSUS = 1.4
def ground_of(leg): return GROUND - 0.7 - (FAR_LIFT if leg.startswith("far") else 0.0)
def knee_bend(leg): return 1 if LEGS[leg][1] >= LEGS[leg][0][0] else -1
def tarsus_heading(leg): return 16.0 if knee_bend(leg) > 0 else 164.0
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, knee_bend(leg))
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", RIG.end_of(f"{leg}_femur"), ht, lt)
    bone(f"{leg}_tarsus", f"{leg}_tibia", RIG.end_of(f"{leg}_tibia"), tarsus_heading(leg), TARSUS)

RIG.seal()
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
SAC_MID, SAC_DARK, SAC_LIT, SAC_GLEAM = "$spore.dark", "$spore.dark2", "$spore@0.7", "$spore.light2@0.8"
FRONT, FRONT_LIT, FRONT_SHADE = "$spore.dark", "$spore@0.5", "$spore.dark2"
LEG_NEAR, LEG_NEAR_2, LEG_FAR = "$spore.dark2", "$spore.dark2", "$carapace.dark2"
HIDE = 0.01

def leg_parts(leg, femur, tibia, tarsus, stroke):
    b = BONES
    at, a = on_bone(f"{leg}_tarsus"); put(f"{leg}_tarsus", f"{leg}_tarsus", at, a, bar(TARSUS, 1.0, 0.6, 0.4), tarsus, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(b[f"{leg}_tibia"].length, 1.15, 0.7), tibia, stroke)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(b[f"{leg}_femur"].length, 1.6, 1.0), femur, stroke)

def antenna(side, fill, stroke):
    _, _, l0, _, l1 = ANT[side]
    at, a = on_bone(f"{side}_scape"); put(f"{side}_scape", f"{side}_scape", at, a, bar(l0, 0.95, 0.75, 0.3), fill, stroke)
    at, a = on_bone(f"{side}_funic"); put(f"{side}_funic", f"{side}_funic", at, a, bar(l1, 0.75, 1.05, 0.4), fill, stroke)

# ---- far side, behind everything
antenna("far", LEG_FAR, None)
for leg in ("far_b", "far_m", "far_f"):
    leg_parts(leg, LEG_FAR, LEG_FAR, LEG_FAR, None)

# ---- the gaster: root sac first, so each overlaps the one before it along
# the arch; each sac is the mid teal body with its dark underside (the inside
# of the curl), a lit rim on the outside, a dark tergite band across it, and
# a gleam — then the nozzle, a tapered spout with a pale ring at the pore.
def sac_parts(k):
    b = f"sac_{k}"
    (x, y), a = on_bone(b)
    ra, rc = SAC[k]
    put(f"gas_{k}", b, (x, y), a, ell(ra, rc), SAC_MID, INK_HAIR)
    # lit from above whichever way the sac leans: the dark underside toward
    # the floor, the lit rim toward the ceiling
    def lean(dx, dy): return (x + dx, y + dy)
    put(f"belly_{k}", b, lean(0.2, rc * 0.46), a, ell(ra * 0.8, rc * 0.5), SAC_DARK)
    put(f"rim_{k}", b, lean(-0.2, -rc * 0.42), a, ell(ra * 0.78, rc * 0.4), SAC_LIT)
    at, _ = on_bone(b, ra * 0.42, 0.0)
    put(f"band_{k}", b, at, a + 90.0, rect(rc * 1.7, 0.8, 0.4), "$spore.dark2@0.8")
    put(f"gleam_{k}", b, lean(-ra * 0.3, -rc * 0.52), a, ell(ra * 0.34, rc * 0.14), SAC_GLEAM)

for k in range(3):
    sac_parts(k)
at, a = on_bone("nozzle")
L = NOZZLE_LEN
put("nozzle", "nozzle", at, a, poly([(-1.8, -2.4), (0.4, -2.1), (L - 0.6, -1.0), (L + 0.4, -0.7), (L + 0.7, 0.0),
                                     (L + 0.4, 0.7), (L - 0.6, 1.0), (0.4, 2.1), (-1.8, 2.4)]), SAC_MID, INK_HAIR)
at, _ = on_bone("nozzle", 0.8, 0.9)
put("nozzle_shade", "nozzle", at, a, poly([(-2.2, -0.2), (1.8, -0.3), (2.0, 0.3), (-2.2, 1.3)]), SAC_DARK)
at, _ = on_bone("nozzle", L + 0.45)
put("pore", "nozzle", at, a, ell(0.45, 0.75), "$spore.light")
# The bead on the pore (the telegraph), the jet (the shot leaving) and the
# flash, all drawn at a hundredth of their size and grown by the clip.
at, _ = on_bone("nozzle", L + 2.0)
put("drip", "nozzle", at, 0.0, circ(1.7), "$spore.light", INK_HAIR, scale=HIDE)
at, _ = on_bone("nozzle", L + 1.5, -0.6)
put("drip_glint", "nozzle", at, 0.0, circ(0.5), "$silent", scale=HIDE)
at, _ = on_bone("nozzle", L + 0.8)
JET = [(0.0, 0.0), (2.0, -0.7), (5.0, -1.2), (6.8, -1.9), (8.2, -1.7), (9.0, -0.8), (9.2, 0.0), (9.0, 0.8), (8.2, 1.7),
       (6.8, 1.9), (5.0, 1.2), (2.0, 0.7)]
put("jet", "nozzle", at, a, poly(JET), "$spore.light", INK_HAIR, scale=HIDE)
at, _ = on_bone("nozzle", L + 5.4)
put("jet_core", "nozzle", at, a, ell(2.6, 0.8), "$spore.light2", scale=HIDE)
at, _ = on_bone("nozzle", L + 1.2)
put("flash", "nozzle", at, a, poly([(-1.6, 0.0), (-0.3, -1.0), (0.2, -2.8), (0.9, -0.9), (3.4, 0.0), (0.9, 0.9), (0.2, 2.8), (-0.3, 1.0)]),
    "$silent", scale=HIDE)

# ---- the body: petiole node, mesosoma, the organ, the head
put("petiole", "body", (-4.4, 1.8), 20.0, ell(1.5, 2.0), FRONT, INK_HAIR)
MESO = [(-3.6, 2.8), (-3.8, 0.0), (-2.6, -1.8), (-0.4, -2.8), (2.0, -2.4), (3.6, -0.8), (3.8, 1.4), (2.6, 3.2), (-0.6, 3.8)]
put("thorax", "body", (0, 0), 0.0, poly(MESO), FRONT, INK_HAIR)
put("thorax_shade", "body", (0, 0), 0.0, poly([(-3.4, 1.8), (-0.6, 2.6), (2.6, 2.2), (3.7, 1.0), (2.6, 3.2), (-0.6, 3.8), (-3.6, 2.8)]), FRONT_SHADE)
put("thorax_lit", "body", (0, 0), 0.0, poly([(-2.8, -1.2), (-0.6, -2.4), (1.8, -2.0), (3.0, -0.8), (1.6, -1.2), (-0.6, -1.2)]), FRONT_LIT)
RIG.use("organ", "body", (0.2, -2.9), "ss.lib.organ", scale=[0.44, 0.38])

HEAD_C = (6.2, 0.6)
put("head", "head", HEAD_C, -6.0, poly([(-3.1, -1.1), (-2.0, -2.6), (0.0, -3.1), (2.1, -2.7), (3.3, -1.1), (3.4, 0.9), (2.3, 2.5),
                                         (0.0, 2.9), (-2.3, 2.3), (-3.2, 0.8)]), FRONT, INK_HAIR)
put("head_lit", "head", (HEAD_C[0] - 0.1, HEAD_C[1] - 1.8), -8.0, ell(2.1, 0.7), FRONT_LIT)
put("mandible", "head", (HEAD_C[0] + 3.2, HEAD_C[1] + 1.7), 16.0,
    poly([(-1.1, -0.8), (0.8, -0.9), (2.2, -0.2), (2.7, 0.8), (1.4, 0.4), (0.2, 0.8), (-1.1, 0.8)]), "$husk.dark", INK_HAIR)
put("eye", "head", (HEAD_C[0] + 1.1, HEAD_C[1] - 0.5), 0.0, ell(1.05, 0.9), "$ink")
put("eye_glint", "head", (HEAD_C[0] + 1.4, HEAD_C[1] - 0.85), 0.0, circ(0.36), "$silent")
antenna("near", FRONT, INK_HAIR)

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

def tracks_world(frame_at, ts, extra=None, still=(), shift=None, pin=None):
    """
    Per-part offset tracks from world frames per bone, with a scale per bone
    applied about the bone's origin (offsets and size), plus `extra` (part,
    prop, fn) tracks — a scale fn multiplies the bone's — and `shift`, per-part
    world (dx, dy) added on top.
    """
    base = {p["id"]: p for p in RIG.parts}
    series = {pid: ([], [], [], []) for pid in RIG.attach}
    for t in ts:
        W, S = frame_at(t)
        for pid, bn in RIG.attach.items():
            p = base[pid]
            at, rot = tuple(p["at"]), p.get("rot", 0.0)
            lx, ly, la = invert_apply(RIG.rest[bn], at, rot)
            s = S.get(bn, 1.0)
            frame = (pin[pid](t, W) if pin and pid in pin else None) or W[bn]
            x, y, a = compose(frame, (lx * s, ly * s, la))
            if shift and pid in shift:
                dx, dy = shift[pid](t, W)
                x, y = x + dx, y + dy
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
                out.append({"part": pid, "prop": prop, "keys": [[round(t, 4), r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
        sfn = ex.pop((pid, "scale"), None)
        svals = [sv * (sfn(t) if sfn else 1.0) for sv, t in zip(ss, ts)]
        if max(abs(v - 1.0) for v in svals) > 0.004:
            out.append({"part": pid, "prop": "scale", "keys": [[round(t, 4), round(v, 3)] for t, v in zip(ts, svals)], "ease": "linear"})
    for (pid, prop), fn in ex.items():
        out.append({"part": pid, "prop": prop, "keys": [[round(t, 4), round(fn(t), 3)] for t in ts], "ease": "linear"})
    return out

STILL = {"eye", "eye_glint", "drip", "drip_glint"}

# ---- charge: 1.5s, the shot cycle. The beats (CUE 0.71, see the docstring):
#   0.74 → 0.26  the recoil settling and the refill: it scans the passage and
#                shuffles to hold its distance, the gaster riding the steps
#   0.24 → 0.40  the draw: it crouches and the curl tightens over its back,
#                the sacs drawn in
#   0.40 → 0.665 the build: the sacs swell in three throbs, harder each time,
#                running up the chain toward the nozzle; the arch opens and
#                lifts until the nozzle points down the passage; the body
#                leans back and braces wide; the bead grows fat and bright on
#                the pore — the telegraph
#   0.668 → 0.686 the release: the sacs clench, the bead goes and the jet
#                squirts out of the nozzle full length, the pore flashing
#   0.686 → 0.76 the jet leaves down the line; the kick throws the arch back
#                and the body back onto its haunches; a last drop wells up
#                on the pore and runs off
CHARGE = 1.5
CUE = 0.71
REL0, REL1 = 0.668, 0.686

def draw(t): return smooth(0.24, 0.38, t) * (1 - smooth(0.40, 0.54, t))

def fill(t):
    if t < 0.40 or t >= REL1: return 0.0
    if t >= REL0: return 1.0 - smooth(REL0, REL1, t)
    u = smooth(0.40, 0.66, t)
    beat = 0.12 * math.sin(2 * math.pi * 3 * smooth(0.40, 0.64, t)) * (1 - smooth(0.60, 0.66, t))
    return max(0.0, min(1.0, u + beat * u))

def spent(t):
    if t < REL0: return 0.0
    return smooth(REL0, REL1, t) * (1 - smooth(0.74, 0.96, t))

def kick(t):
    """The recoil: 1 at the release, then a damped swing back through rest."""
    if t < REL0: return 0.0
    if t < REL1: return smooth(REL0, REL1, t)
    d = (t - REL1) / 0.26
    if d > 1.0: return 0.0
    return math.exp(-3.2 * d) * math.cos(math.pi * 1.5 * d) * (1 - smooth(0.8, 1.0, d))

def aim(t):
    """The arch opened and the nozzle levelled down the passage: through the build, held past the release."""
    return smooth(0.40, 0.62, t) * (1 - smooth(0.70, 0.9, t))

def brace(t): return smooth(0.36, 0.48, t) * (1 - smooth(0.76, 0.9, t))
def walk_amount(t): return (1 - smooth(0.16, 0.26, t)) if t < 0.5 else smooth(0.78, 0.9, t)

STRIDE = 1.4
TRIPOD = {"near_f": 0.0, "far_m": 0.0, "near_b": 0.0, "far_f": 0.5, "near_m": 0.5, "far_b": 0.5}
def step(u):
    u %= 1.0
    if u < 0.55:
        return lerp(STRIDE, -STRIDE, u / 0.55), 0.0
    v = (u - 0.55) / 0.45
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 1.5 * math.sin(math.pi * v)

def charge_pose(t):
    d, f, k, b, w = draw(t), fill(t), kick(t), brace(t), walk_amount(t)
    # the shuffle: two steps a cycle, a bob on each
    ph = 2.0 * ((t + 0.2) % 1.0)
    bob = 0.5 * w * (0.5 - 0.5 * math.cos(2 * math.pi * ph))
    pose = {"body": (-0.6 * d - 1.6 * k + 0.3 * w * cyc(ph / 2.0),
                     1.4 * d - 0.6 * aim(t) + 0.8 * max(0.0, k) + bob,
                     3.0 * d - 6.0 * aim(t) - 5.0 * k + 1.0 * w * cyc(ph))}
    # the gaster: a wave from the root out while it walks; curled tight in
    # the draw; opened and lifted to aim in the build (the nozzle along +x);
    # thrown back by the kick, the tip last
    sway = [3.0 * w * cyc(ph / 2.0, -0.12 * i) for i in range(4)]
    tight = [10.0, 12.0, 10.0, 0.0]
    level = [-8.0, -6.0, -4.0, 8.0]
    thrown = [-8.0, -10.0, -14.0, -22.0]
    a = aim(t)
    for i, n in enumerate(GAS + ["nozzle"]):
        kl = kick(t - 0.014 * (i + 1))
        pose[n] = sway[i] + tight[i] * d + level[i] * a + thrown[i] * kl + (2.0 * i) * spent(t)
    # the head scans the passage while it refills, and looks down the line for the shot
    pose["head"] = w * 7.0 * math.sin(2 * math.pi * (t + 0.1)) + 4.0 * d - 6.0 * f + 8.0 * k
    for side, ph2 in (("near", 0.0), ("far", 0.08)):
        pose[f"{side}_scape"] = 12.0 * w * cyc(t, ph2 - 0.1) + 14.0 * d - 10.0 * f - 20.0 * kick(t - 0.03)
        pose[f"{side}_funic"] = 16.0 * w * cyc(t, ph2 - 0.2) + 10.0 * d - 12.0 * f - 26.0 * kick(t - 0.06)
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        gx, lift = step(ph + TRIPOD[leg])
        spread = 1.3 if leg.endswith("_f") else (-1.3 if leg.endswith("_b") else 0.0)
        x = lerp(fx + gx * w, fx + spread, b)
        feet[leg] = (x, ground_of(leg) - lift * w)
    return plant_legs(pose, feet)

def sac_scale(t, k):
    """Sac k's size: drawn in, then the throbs running up the chain toward the nozzle, the clench, a wobble."""
    lag = 0.02 * k
    return (1.0 - 0.1 * draw(t) + 0.2 * fill(t - lag) + 0.02 * k * fill(t - lag)
            - 0.16 * spent(t) + 0.06 * max(0.0, -kick(t - lag)))

def charge_frame(t):
    W = dict(solve(charge_pose(t)))
    S = {f"sac_{k}": sac_scale(t, k) for k in range(3)}
    return W, S

def drip_grow(t):
    """The bead on the pore: from 0.46, full by 0.64; gone in the release (it is the jet's head now)."""
    if t < 0.46: return after_drip(t)
    if t < REL0: return smooth(0.46, 0.64, t)
    return max(0.0, 1.0 - smooth(REL0, REL0 + 0.01, t))

def after_drip(t):
    """The last drop after the shot: wells on the pore 0.76–0.86 and runs off by 0.97."""
    if t < 0.5: t += 1.0
    return 0.55 * smooth(0.76, 0.86, t) * (1 - smooth(0.93, 0.98, t))

def drip_fall(t, W):
    """The after-drop falls off the pore in the world's down, not the nozzle's."""
    u = t + 1.0 if t < 0.5 else t
    f = smooth(0.86, 0.97, u)
    return (0.3 * f, 7.0 * f * f)

def jet_len(t):
    if t < REL0 or t > 0.78: return 0.0
    return smooth(REL0, REL1, t) * (1 - 0.35 * smooth(0.70, 0.76, t)) * (1 - smooth(0.755, 0.78, t))

RELEASED = solve(charge_pose(REL1))["nozzle"]
def jet_frame(t, W):
    """Once it is out, the jet is its own thing: the nozzle's frame as it was at the release, carried on down that line."""
    if t < REL1: return None
    x, y, a = RELEASED
    d = 7.0 * smooth(REL1, 0.76, t)
    return (x + d * math.cos(R(a)), y + d * math.sin(R(a)), a)

def flash_on(t):
    if t < REL0: return 0.0
    return smooth(REL0, REL1 - 0.004, t) * (1 - smooth(0.71, 0.74, t))

def hidden(v): return max(HIDE, v) / HIDE

CHARGE_EXTRA = [
    ("drip", "scale", lambda t: hidden(drip_grow(t))),
    ("drip_glint", "scale", lambda t: hidden(drip_grow(t))),
    ("drip", "opacity", lambda t: 0.7 + 0.3 * smooth(0.5, 0.64, t) if t < 0.7 else 1.0),
    ("jet", "scale", lambda t: hidden(jet_len(t))),
    ("jet_core", "scale", lambda t: hidden(jet_len(t))),
    ("jet", "opacity", lambda t: 1.0 - 0.6 * smooth(0.73, 0.78, t)),
    ("flash", "scale", lambda t: hidden(flash_on(t) * (0.9 + 0.4 * smooth(REL0, 0.72, t)))),
    ("flash", "opacity", flash_on),
    ("pore", "scale", lambda t: 1.0 + 0.25 * fill(t) + 0.3 * flash_on(t)),
    ("organ", "scale", lambda t: 1.0 + 0.1 * fill(t)),
] + [(f"rim_{k}", "opacity", (lambda k: lambda t: 0.85 + 0.15 * fill(t - 0.02 * k))(k)) for k in range(3)]
CHARGE_SHIFT = {"drip": drip_fall, "drip_glint": drip_fall}
CHARGE_PIN = {"jet": jet_frame, "jet_core": jet_frame}

TS_CHARGE = sorted(set([round(i / 90, 4) for i in range(91)] +
                       [0.64, 0.66, REL0, 0.672, 0.676, 0.68, 0.684, REL1, 0.69, 0.694, 0.698, 0.702, 0.71]))

# ---- death: 0.46s. The pressure goes out at the spout and works back down
# the arc: a last squirt from the nozzle, the sacs deflating nozzle-first, the
# raised gaster — the whole tell — sinking back onto the body it was carried
# over, one last bead running off the end, and the legs folding under a head
# already on the floor. Still from 0.85.
def death_pose(t):
    jerk = smooth(0.0, 0.08, t) * (1 - smooth(0.1, 0.3, t))
    fall = smooth(0.2, 0.8, t)
    pose = {"body": (-0.8 * jerk + 0.4 * fall, -0.6 * jerk + 2.6 * fall, -4.0 * jerk + 6.0 * fall)}
    sink = [-22.0, -16.0, -10.0, 16.0]  # the arch lies back and down over the back
    for i, n in enumerate(GAS + ["nozzle"]):
        pose[n] = -10.0 * jerk * (1 if i < 3 else 2) + sink[i] * smooth(0.2 + 0.08 * (3 - i), 0.62 + 0.06 * (3 - i), t)
    pose["head"] = 6.0 * jerk + 24.0 * fall
    for side in ("near", "far"):
        pose[f"{side}_scape"] = -24.0 * jerk + 30.0 * fall
        pose[f"{side}_funic"] = -20.0 * jerk + 26.0 * fall
    pose["tarsus"] = 30.0 * fall
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx = hip[0] + (fx - hip[0]) * lerp(1.0, 0.45, fall)
        feet[leg] = (hx, ground_of(leg) + 0.5 * fall)
    return plant_legs(pose, feet)

def death_sac(t, k):
    # nozzle-first: sac 2 goes first, sac 0 last
    a = 0.14 + 0.12 * (2 - k)
    return 1.0 + 0.1 * smooth(0.0, 0.1, t) * (1 - smooth(a - 0.04, a + 0.1, t)) - 0.28 * smooth(a, a + 0.26, t)

def death_frame(t):
    W = dict(solve(death_pose(t)))
    S = {f"sac_{k}": death_sac(t, k) for k in range(3)}
    return W, S

def death_drip(t):
    return 0.7 * smooth(0.04, 0.2, t) * (1 - smooth(0.66, 0.8, t))
def death_drip_fall(t, W):
    f = smooth(0.34, 0.66, t)
    return (0.2 * f, 6.0 * f * f)

TS_DEATH = [0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.24, 0.28, 0.32, 0.36, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
DEATH_EXTRA = [
    ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.3, 0.8, t)),
    ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.3, 0.6, t)),
    ("jet", "scale", lambda t: hidden(0.55 * smooth(0.0, 0.06, t) * (1 - smooth(0.12, 0.22, t)))),
    ("jet", "opacity", lambda t: 1.0 - 0.5 * smooth(0.1, 0.22, t)),
    ("drip", "scale", lambda t: hidden(death_drip(t))),
    ("drip_glint", "scale", lambda t: hidden(death_drip(t))),
    ("pore", "scale", lambda t: 1.0 + 0.3 * smooth(0.0, 0.06, t) - 0.5 * smooth(0.2, 0.5, t)),
] + [(f"gleam_{k}", "opacity", (lambda k: lambda t: 1.0 - 0.85 * smooth(0.14 + 0.12 * (2 - k), 0.44 + 0.12 * (2 - k), t))(k)) for k in range(3)] \
  + [(f"rim_{k}", "opacity", (lambda k: lambda t: 1.0 - 0.6 * smooth(0.14 + 0.12 * (2 - k), 0.44 + 0.12 * (2 - k), t))(k)) for k in range(3)]
DEATH_SHIFT = {"drip": death_drip_fall, "drip_glint": death_drip_fall}

animations = {
    "charge": {
        "description": "The shot cycle, authored at the cadence a Gland's is (the clip is the whole shot; with `fireCue: 0.71` the game time-scales it to fireInterval and re-seats it at the cue on every shot, and the jet is out of the nozzle on the frame that seats to at 15, 20, 24 or 30 fps). It scans the passage and shuffles while the sac refills; from 0.24 it crouches and the curl over its back tightens, the sacs drawn in; from 0.40 the sacs swell in three throbs running up the chain toward the nozzle, the arch opens and lifts until the nozzle points down the passage, it leans back and braces wide, and a bead grows fat and bright on the pore — the telegraph; at 0.668–0.686 the sacs clench and the jet squirts out of the nozzle full length with the pore flashing; then the jet leaves down the line, the kick throws the arch and the body back, a last drop wells up on the pore and runs off, and it scans again.",
        "duration": CHARGE,
        "tracks": tracks_world(charge_frame, TS_CHARGE, CHARGE_EXTRA, STILL, CHARGE_SHIFT, CHARGE_PIN),
    },
    "death": {
        "description": "It vents: a last squirt from the nozzle, then the pressure goes out at the spout and works back down the arc — the sacs deflating nozzle-first, their gleam going off — and the raised gaster, the whole tell, sinks back onto the body it was carried over; one last bead runs off the end and falls, and the legs fold under a head already on the floor. Still from 0.85.",
        "duration": 0.46,
        "tracks": tracks_world(death_frame, TS_DEATH, DEATH_EXTRA, STILL, DEATH_SHIFT),
    },
}

# ============================================================== document
DESCRIPTION = (
    "The burrow's ranged caste: it turns its own gaster over its back and points the acidopore down the passage. That posture is the "
    "entire silhouette and the entire tell — a sac carried high with a spout aimed forward, so a body holding still at the far end of a "
    "corridor still reads as loaded. Teal for the same reason the Gland is: what it pumps out is `ss.enemy.spray`, and a shooter should "
    "be the colour of what it throws. Drawn in three values: the gaster mid teal with a lit rim, a dark underside and dark bands, the "
    "thorax and head a step darker with the organ on the back, the legs the hive's dark carapace; the bright teal is kept for what is "
    "charged — the bead on the pore and the jet. Built on a skeleton (scripts/sprayer.py): the gaster is a chain of three sacs and a "
    "nozzle off the petiole, each sac swelling about its own centre, so the curl tightens, lifts to aim and is thrown back as one arch; "
    "the head scans on a neck with two elbowed antennae trailing it, and six legs are solved to feet on the floor. Its one loop, `charge`, "
    "is the shot cycle, written like the Gland's: the draw, the swell and the bead growing on the pore are the telegraph, and the jet "
    "leaves the nozzle at 0.668–0.686, which is the frame a `fireCue` of 0.71 seats to (EnemySystem.cueCycle). No `elite` variant on "
    "purpose — the marking only lands on wave-table bodies, and this one arrives in squads. Drawn facing +x, the game flips it. Gameplay "
    "radius 10. The `death` clip vents it: a last squirt, the sacs going nozzle-first, and the raised gaster — the whole tell — sinking "
    "onto the body it was carried over."
)

doc = {
    "id": "ss.enemy.sprayer",
    "name": "Sprayer",
    "description": DESCRIPTION,
    "tags": ["enemy", "sprayer"],
    "size": SIZE,
    "meta": {"radius": 10},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-sprayer.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
