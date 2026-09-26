"""The Gland — a sac on two legs that spits where you are going to be.

    python3 scripts/spitter.py        # rewrites apps/ss/assets/ss-enemy-spitter.json

The Plains' standoff shooter: it holds the far edge of your reach (feelers:
`standoff: 400`) and puts a teal bolt on your intercept every 2.6s
(`fireInterval: 2.6`, `fireCue: 0.65`, `shotTex: 'e_shot'`). Its one clip is
not an idle, it is the shot: the game plays `spit` as the loop, time-scales it
to exactly the fire interval and re-seats it at `fireCue` on every shot
(EnemySystem.cueCycle). So the draw and the swell before the cue are the
telegraph — the thing a player learns to read — and the bead leaving the lip
has to be on the frame the game seats to, because that is the frame the real
bolt appears next to.

Which frame that is: at the default 15 fps the 2.6s clip is a 39-frame sheet
whose frame i is baked at i/39, and Phaser's setProgress(0.65) picks the frame
whose progress i/38 is nearest, frame 25 — baked at 0.641. The release is
authored to be over by 0.636 and the flash to hold to 0.66, so frame 24 (0.615)
is the loaded sac at its fullest and frame 25 is the bead gone with the lip
flashing. The same window lands on the cue frame at 16 or 18 fps as well.

It was hand-placed and it moved under three pixels at game scale: the sac
scaled a few percent, the snout turned about its own centre and the legs
rocked. This rebuilds it on the shared rig (scripts/rig.py):

  - the body is a root bone that squats, leans back to aim and is shoved back
    by the spit; the sac rides it on a bone of its own, so it can draw in and
    swell (its details scale out from its centre with it); the snout is a
    bone hinged at the collar, so it lifts to aim and kicks on the shot
  - two short legs, a femur and a tibia each solved to a foot on the ground,
    that shuffle while the sac refills and brace wide for the shot

Colour: the teal family it had, in three values — the sac `$spore.dark` over a
`$spore.dark2` underside, the muscle bands and legs dark, the lip pale — with
the bright teal kept for what is charged: the fluid glowing inside the sac,
and the bead, which is the bolt (`ss.enemy.shot`).
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 compose, invert_apply, poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 36×36, origin at the centre, +x forward, +y down.
SIZE = [40, 36]
GROUND = 11.0
FAR_LIFT = 0.8
BODY_PIVOT = (-4.0, 8.0)   # between the feet: the lean turns the mass over them

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, BODY_PIVOT, 0.0)
SAC_C = (-4.6, -0.8)
bone("sac", "body", SAC_C, 0.0, 0.0)
SNOUT_ROOT = (3.4, 1.0)
SNOUT_HEADING = -8.0
SNOUT_LEN = 6.6
bone("snout", "body", SNOUT_ROOT, SNOUT_HEADING, SNOUT_LEN)

LEGS = {  # name: (hip, rest foot x, femur, tibia)
    "far": ((-9.6, 5.8), -10.8, 3.6, 3.8),
    "near": ((-1.6, 6.4), -0.6, 3.8, 4.0),
}
def ground_of(leg): return GROUND - (FAR_LIFT if leg == "far" else 0.0)
KNEE = 1  # knees forward, the way a squatting thing folds
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, KNEE)
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", RIG.end_of(f"{leg}_femur"), ht, lt)
    bone(f"{leg}_foot", f"{leg}_tibia", RIG.end_of(f"{leg}_tibia"), 0.0, 2.0)

RIG.seal()
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
# Values: LIGHT is the sac's lit top and the lip; MID the sac's body; DARK the
# underside, the muscle bands, the legs.
SAC_MID, SAC_DARK, SAC_LIGHT = "$spore.dark", "$spore.dark2", "$spore"
HIDE = 0.01

def leg_parts(leg, femur, tibia, foot, stroke):
    at, a = on_bone(f"{leg}_foot"); put(f"{leg}_foot", f"{leg}_foot", at, a, poly([(-0.6, -0.9), (1.6, -0.5), (2.4, 0.4), (1.8, 0.9), (-0.6, 0.9)]), foot, stroke)
    at, a = on_bone(f"{leg}_tibia"); put(f"{leg}_tibia", f"{leg}_tibia", at, a, bar(BONES[f"{leg}_tibia"].length, 2.0, 1.5), tibia, stroke)
    at, a = on_bone(f"{leg}_femur"); put(f"{leg}_femur", f"{leg}_femur", at, a, bar(BONES[f"{leg}_femur"].length, 2.8, 2.2), femur, stroke)

# ---- the legs, both under the sac: the hips are hidden by it and the
# knees fold out below it; the far one a step darker
leg_parts("far", "$spore.dark2", "$spore.dark2", "$spore.dark2", INK_HAIR)
leg_parts("near", SAC_MID, SAC_MID, SAC_DARK, INK_HAIR)

# ---- the sac: dark underside, lit body offset up, muscle bands, pores, the
# charge glowing inside; it rides its own bone and scales from its centre.
sx, sy = SAC_C
SAC_RX, SAC_RY = 9.2, 8.7
put("sac", "sac", (sx, sy), 0.0, ell(SAC_RX, SAC_RY), SAC_DARK, INK_THIN)
put("sac_lit", "sac", (sx + 0.1, sy - 0.6), 0.0, ell(8.9, 8.1), SAC_MID)
put("charge", "sac", (sx + 2.2, sy + 0.4), 0.0, ell(5.6, 5.0), "$spore.light", opacity=0.35)
# The muscle bands: arcs round the collar that squeeze the sac toward the
# snout — the wall of a gland, and what makes the swell read as a muscle
# working rather than a balloon. Each is a crescent of the circle about the
# snout's root, kept to the part of it that lies inside the sac.
def band(R, w, inset=1.2):
    cx, cy = SNOUT_ROOT[0] - 1.0, SNOUT_ROOT[1]
    angs = [a for a in range(90, 271, 3)
            if ((cx + R * math.cos(R_(a)) - sx) / (SAC_RX - inset)) ** 2 + ((cy + R * math.sin(R_(a)) - sy) / (SAC_RY - inset)) ** 2 < 1.0]
    a0, a1 = min(angs), max(angs)
    outer, inner = [], []
    for i in range(13):
        a = lerp(a0, a1, i / 12)
        h = w * (0.25 + 0.75 * math.sin(math.pi * i / 12))
        outer.append((cx + (R + h / 2) * math.cos(R_(a)) - sx, cy + (R + h / 2) * math.sin(R_(a)) - sy))
        inner.append((cx + (R - h / 2) * math.cos(R_(a)) - sx, cy + (R - h / 2) * math.sin(R_(a)) - sy))
    return poly(outer + inner[::-1])
R_ = math.radians
for i, (Rr, w) in enumerate(((7.4, 1.2), (11.4, 1.1))):
    put(f"band_{i}", "sac", (sx, sy), 0.0, band(Rr, w), "$spore.dark2@0.45")
put("sac_rim", "sac", (sx - 0.4, sy - 3.8), -10.0, ell(7.2, 3.3), "$spore.light@0.6")
put("gleam", "sac", (sx - 2.8, sy - 4.4), -24.0, ell(2.7, 1.4), "$spore.light2@0.8")
for i, (ox, oy, r) in enumerate(((-6.0, 1.8, 0.8), (-3.6, 4.6, 0.7), (-7.0, -2.6, 0.6))):
    put(f"pore_{i}", "sac", (sx + ox, sy + oy), 0.0, circ(r), SAC_DARK)
RIG.use("organ", "sac", (sx - 1.4, sy - 7.6), "ss.lib.organ", scale=[0.52, 0.48])

# The eye, on the front of the sac over the snout.
put("eye", "sac", (sx + 7.0, sy - 3.8), 0.0, circ(1.0), "$ink")
put("eye_glint", "sac", (sx + 7.3, sy - 4.1), 0.0, circ(0.34), "$silent")

# ---- the snout, over the sac: a tapered tube hinged at the collar, pale lip
# ring at the end, the mouth in it; the bead sits on the lip and grows there.
# Drawn over the sac so the swell bulges round its root instead of swallowing
# it, with a dark muscular collar where the two meet.
at, a = on_bone("snout")
L = SNOUT_LEN
put("snout", "snout", at, a, poly([(-1.4, -3.2), (1.8, -3.0), (L - 1.2, -2.0), (L, -2.3), (L + 0.6, -1.6),
                                   (L + 0.6, 1.6), (L, 2.3), (L - 1.2, 2.0), (1.8, 3.0), (-1.4, 3.2)]), SAC_MID, INK_THIN)
at, a = on_bone("snout", L * 0.45, 1.4)
put("snout_shade", "snout", at, a, poly([(-3.6, -0.3), (3.4, -0.5), (3.4, 0.9), (-3.6, 1.6)]), SAC_DARK)
for i, u in enumerate((0.28, 0.58)):
    at, a = on_bone("snout", L * u)
    put(f"snout_ring_{i}", "snout", at, a, rect(0.8, 5.2 - 1.6 * u, 0.4), SAC_DARK)
at, a = on_bone("snout", L * 0.5, -1.6)
put("snout_gloss", "snout", at, a, ell(2.2, 0.45), "$white@0.3")
at, a = on_bone("snout", L + 0.5)
put("lip", "snout", at, a, ell(1.1, 2.5), "$verdigris.light", INK_HAIR)
at, a = on_bone("snout", L + 0.7)
put("mouth", "snout", at, a, ell(0.6, 1.5), "$ink")
at, a = on_bone("snout", -0.2)
put("collar", "snout", at, a, ell(1.6, 3.6), SAC_DARK, INK_HAIR)
at, a = on_bone("snout", -0.6, -1.4)
put("collar_lit", "snout", at, a, ell(0.8, 1.6), SAC_MID)

# ---- the bead and the flash on the lip: the bolt, before it is one
at, a = on_bone("snout", L + 2.2)
put("bead", "snout", at, a, circ(2.1), "$spore", scale=HIDE)
at, a = on_bone("snout", L + 1.7, -0.7)
put("bead_glint", "snout", at, a, circ(0.6), "$silent", scale=HIDE)
at, a = on_bone("snout", L + 2.6)
put("flash", "snout", at, a, poly([(-2.2, 0.0), (-0.4, -1.3), (0.2, -3.4), (1.0, -1.1), (4.2, 0.0), (1.0, 1.1), (0.2, 3.4), (-0.4, 1.3)]),
    "$silent", scale=HIDE)


RIG.check()

# ============================================================== motion
def plant_legs(pose, feet):
    world = solve(pose)
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, KNEE)
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_foot"] = 0.0
    return pose

# ---- spit: 2.6s = fireInterval; the game re-seats it at fireCue 0.65 on
# every shot. The beats of one cycle:
#   0.66 → 0.84   recoil and recovery from the last shot
#   0.84 → 0.20   refilling, slowly, while it shuffles to hold its distance
#   0.20 → 0.36   the draw: it squats and sucks the sac in, snout lowered
#   0.36 → 0.62   the swell: the sac inflates in three throbs, harder each
#                 time, the fluid inside lighting up; it rises and leans back
#                 so the snout lifts to aim, the lip opens and a bead builds
#                 on it — the telegraph
#   0.624 → 0.636 the spit: the sac clenches, the bead leaves, the lip flashes
#                 (on the cue frame, 25 of 39 at 0.641 — see the docstring)
#   0.636 → 0.66  the kick: body shoved back, snout thrown up
PUMP = 2.6
REL0, REL1 = 0.624, 0.636
KICK = 0.641

def draw(t):
    """The inhale before the swell: 0 → 1 over the draw, back to 0 as the swell takes over."""
    return smooth(0.18, 0.34, t) * (1 - smooth(0.36, 0.50, t))

def fill(t):
    """0 when spent, 1 at the fullest, just before the release; throbs on the way."""
    if t < 0.36 or t >= REL1: return 0.0
    if t >= REL0: return 1.0 - smooth(REL0, REL1, t)
    u = smooth(0.36, 0.62, t)
    # Three throbs, each a surge and a small give: the pump behind the swell.
    beat = 0.10 * math.sin(math.pi * 2 * 3 * smooth(0.36, 0.60, t)) * (1 - smooth(0.56, 0.62, t))
    return max(0.0, min(1.0, u + beat * u))

def spent(t):
    """The sac emptied by the spit: 1 just after it, gone by the refill."""
    if t < REL0: return 0.0
    return smooth(REL0, REL1, t) * (1 - smooth(0.70, 0.94, t))

def kick(t):
    """The recoil impulse: 1 at the spit, then a damped swing back through rest."""
    if t < REL0: return 0.0
    if t < REL1: return smooth(REL0, REL1, t)
    d = (t - REL1) / 0.2
    if d > 1.0: return 0.0
    return math.exp(-3.0 * d) * math.cos(math.pi * 1.4 * d) * (1 - smooth(0.8, 1.0, d))

def walk_amount(t):
    """The shuffle runs while the sac refills and stops for the draw."""
    return (1 - smooth(0.12, 0.2, t)) if t < 0.5 else smooth(0.74, 0.86, t)

def sac_scale(t):
    return 1.0 - 0.12 * draw(t) + 0.24 * fill(t) - 0.14 * spent(t) + 0.05 * max(0.0, -kick(t))

STRIDE = 1.3
def step(u):
    u %= 1.0
    if u < 0.5:
        return lerp(STRIDE, -STRIDE, u / 0.5), 0.0
    v = (u - 0.5) / 0.5
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 1.5 * math.sin(math.pi * v)

def brace(t):
    return smooth(0.34, 0.48, t) * (1 - smooth(0.70, 0.84, t))

def spit_pose(t):
    d, f, k, b = draw(t), fill(t), kick(t), brace(t)
    w = walk_amount(t)
    # the shuffle: two steps a cycle, a bob on each
    ph = 4.0 * ((t + 0.16) % 1.0)
    bob = 0.7 * w * (0.5 - 0.5 * math.cos(2 * math.pi * ph))
    dx = 0.5 * w * math.sin(math.pi * ph) - 0.8 * d - 2.4 * k
    dy = 1.6 * d - 1.0 * f + bob + 1.0 * max(0.0, k)
    dth = 3.0 * d - 9.0 * f - 5.0 * k + 1.2 * w * math.sin(math.pi * ph)
    pose = {"body": (dx, dy, dth)}
    # The snout: lowered and drawn in for the inhale, lifted to aim through the
    # swell, thrown up by the spit and let down again.
    pose["snout"] = 10.0 * d - 16.0 * f - 22.0 * k + 6.0 * spent(t)
    # The feet: stepping while it refills; spread wide and planted for the shot.
    feet = {}
    for i, (leg, (hip, fx, lf, lt)) in enumerate(LEGS.items()):
        gx, lift = step(ph / 2.0 + (0.5 if leg == "near" else 0.0))
        spread = 1.2 if leg == "near" else -1.0
        x = lerp(fx + gx * w, fx + spread, b)
        feet[leg] = (x, ground_of(leg) - lift * w)
    return plant_legs(pose, feet)

def snout_slide(t):
    """How far the snout is pulled back into the collar: in for the draw, punched out on the spit."""
    return -1.2 * draw(t) + 0.8 * fill(t) + 1.2 * max(0.0, kick(t)) * (1 - smooth(REL1, 0.7, t))

def bead_grow(t):
    """The bead on the lip: nothing until the swell is well on, full by 0.60; on the spit it
    leaves shrinking (bead_fly carries it off the lip) and is gone by 0.655."""
    if t < 0.42: return 0.0
    if t < REL0: return smooth(0.42, 0.60, t)
    if t < 0.655: return 1.0 - 0.6 * smooth(REL0, 0.655, t)
    return 0.0

def flash_on(t):
    if t < REL0: return 0.0
    return smooth(REL0, REL1 - 0.004, t) * (1 - smooth(0.66, 0.69, t))

# ---- the sac's scale, and its details scaling out from its centre with it
SCALED = {"sac"}
def tracks_scaled(pose_at, ts, s_fn, extra=None, still=()):
    """RIG.tracks, with every part on a SCALED bone scaled about the bone by s_fn(t) — offsets and size."""
    rest = RIG.posed_parts({})
    base = {p["id"]: p for p in RIG.parts}
    series = {pid: ([], [], [], []) for pid in RIG.attach}
    for t in ts:
        pose = pose_at(t)
        world = solve(pose)
        s = s_fn(t)
        for pid, bn in RIG.attach.items():
            p = base[pid]
            lx, ly, la = invert_apply(RIG.rest[bn], tuple(p["at"]), p.get("rot", 0.0))
            k = s if bn in SCALED else 1.0
            x, y, a = compose(world[bn], (lx * k, ly * k, la))
            bx, by, ba = rest[pid]
            sr = series[pid]
            sr[0].append(x - bx); sr[1].append(y - by); sr[2].append(wrap(a - ba)); sr[3].append(k)
    ex = {(pid, prop): fn for pid, prop, fn in (extra or [])}
    out = []
    for p in RIG.parts:
        pid = p["id"]
        xs, ys, rs, ss = series[pid]
        for prop, vs in (("x", xs), ("y", ys), ("rot", rs)):
            if prop == "rot" and pid in still: continue
            if max(abs(v) for v in vs) > 0.01:
                out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
        sfn = ex.pop((pid, "scale"), None)
        svals = [sv * (sfn(t) if sfn else 1.0) for sv, t in zip(ss, ts)]
        if max(abs(v - 1.0) for v in svals) > 0.005:
            out.append({"part": pid, "prop": "scale", "keys": [[r2(t), round(v, 3)] for t, v in zip(ts, svals)], "ease": "linear"})
    for (pid, prop), fn in ex.items():
        out.append({"part": pid, "prop": prop, "keys": [[r2(t), round(fn(t), 3)] for t in ts], "ease": "linear"})
    return out

def with_slide(tracks, ts, pose_at, fn, parts):
    """Add a slide of `fn(t)` along the snout's posed axis to the snout parts' x/y tracks."""
    world = [solve(pose_at(t))["snout"][2] for t in ts]
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

SNOUT_PARTS = ("snout", "snout_shade", "snout_ring_0", "snout_ring_1", "snout_gloss", "lip", "mouth", "bead", "bead_glint", "flash")

def bead_fly(t):
    """Past the lip: the bead's own travel off the snout as it leaves."""
    if t < REL0: return 0.0
    return 5.0 * smooth(REL0, REL1 + 0.01, t)

# Keys: every 1/78 (twice the 39-frame sheet) and dense through the release.
TS_SPIT = sorted(set([round(i / 78, 4) for i in range(79)] + [0.62, REL0, 0.628, 0.632, REL1, KICK, 0.646, 0.652, 0.658, 0.664, 0.67]))
def glow_o(t): return 0.85 + 1.6 * fill(t) ** 1.4
SPIT_EXTRA = [
    ("charge", "opacity", glow_o),
    ("charge", "scale", lambda t: 0.8 + 0.3 * fill(t)),
    ("bead", "scale", lambda t: max(HIDE, bead_grow(t)) / HIDE),
    ("bead_glint", "scale", lambda t: max(HIDE, bead_grow(t)) / HIDE),
    ("flash", "scale", lambda t: max(HIDE, flash_on(t) * (0.9 + 0.4 * smooth(REL0, 0.66, t))) / HIDE),
    ("flash", "opacity", flash_on),
    ("mouth", "scale", lambda t: 0.5 + 0.7 * fill(t) + 0.6 * flash_on(t) - 0.2 * draw(t)),
    ("lip", "scale", lambda t: 1.0 + 0.18 * fill(t) + 0.2 * flash_on(t)),
    ("organ", "scale", lambda t: 1.0 + 0.12 * fill(t)),
]

# The sac's front wall is this far ahead of its centre along the snout: as the
# sac swells or draws in, the snout and its collar are pushed out or pulled in
# with it, so the nozzle stays seated on the wall.
SAC_FRONT = SNOUT_ROOT[0] - SAC_C[0]
def growth(s_fn): return lambda t: (s_fn(t) - 1.0) * SAC_FRONT

def spit_tracks():
    tr = tracks_scaled(spit_pose, TS_SPIT, sac_scale, SPIT_EXTRA)
    tr = with_slide(tr, TS_SPIT, spit_pose, growth(sac_scale), SNOUT_PARTS + ("collar", "collar_lit"))
    tr = with_slide(tr, TS_SPIT, spit_pose, snout_slide, SNOUT_PARTS)
    return with_slide(tr, TS_SPIT, spit_pose, bead_fly, ("bead", "bead_glint"))

# ---- death: 0.44s. The sac goes before the animal: one swell against its
# own wall, a held beat, then it drops to two thirds of itself and pulls the
# spout back in with it; the loaded bead falls out of the lip, the legs fold.
def death_sac(t):
    return 1.0 + 0.22 * smooth(0.0, 0.2, t) - 0.55 * smooth(0.34, 0.66, t)

def death_pose(t):
    swell = smooth(0.0, 0.2, t)
    fall = smooth(0.34, 0.8, t)
    pose = {"body": (0.6 * fall, lerp(0.0, 2.2, fall) - 0.8 * swell * (1 - fall), -6.0 * swell * (1 - fall) + 8.0 * fall)}
    pose["snout"] = -14.0 * swell * (1 - fall) + 34.0 * fall
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        out = 2.6 if leg == "near" else -2.2
        feet[leg] = (fx + out * fall, ground_of(leg))
    return plant_legs(pose, feet)

def death_slide(t): return -3.4 * smooth(0.36, 0.8, t)

def bead_fall_x(t): return 0.0
TS_DEATH = [0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.24, 0.28, 0.32, 0.36, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
DEATH_EXTRA = [
    ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.3, 0.8, t)),
    ("charge", "opacity", lambda t: max(0.0, 0.85 + 1.4 * smooth(0.0, 0.2, t) - 2.2 * smooth(0.3, 0.6, t))),
    ("gleam", "opacity", lambda t: 1.0 - 0.8 * smooth(0.34, 0.7, t)),
    ("sac_rim", "opacity", lambda t: 1.0 - 0.8 * smooth(0.34, 0.7, t)),
    ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.3, 0.6, t)),
    ("bead", "scale", lambda t: (0.8 * smooth(0.0, 0.16, t) * (1 - 0.3 * smooth(0.5, 0.8, t)) + HIDE) / HIDE),
    ("bead_glint", "scale", lambda t: (0.8 * smooth(0.0, 0.16, t) * (1 - smooth(0.4, 0.7, t)) + HIDE) / HIDE),
    ("bead", "opacity", lambda t: 1.0 - 0.5 * smooth(0.6, 0.85, t)),
    ("mouth", "scale", lambda t: 0.5 + 0.8 * smooth(0.0, 0.2, t) - 0.9 * smooth(0.34, 0.7, t)),
]
def death_tracks():
    tr = tracks_scaled(death_pose, TS_DEATH, death_sac, DEATH_EXTRA)
    tr = with_slide(tr, TS_DEATH, death_pose, growth(death_sac), SNOUT_PARTS + ("collar", "collar_lit"))
    tr = with_slide(tr, TS_DEATH, death_pose, death_slide, SNOUT_PARTS)
    # The bead falls out of the lip and lands in front of the feet.
    by = {(x["part"], x["prop"]): x for x in tr}
    for p in ("bead", "bead_glint"):
        ty = by.get((p, "y"))
        tx = by.get((p, "x"))
        for key, t in zip(ty["keys"], TS_DEATH):
            k = smooth(0.4, 0.8, t)
            key[1] = r2(key[1] * (1 - k) + k * (GROUND - 2.0 - RIG.posed_parts({})[p][1]))
        for key, t in zip(tx["keys"], TS_DEATH):
            k = smooth(0.4, 0.8, t)
            key[1] = r2(key[1] * (1 - k) + k * (2.0))
    return tr

animations = {
    "spit": {
        "description": "The shot, on the game's cadence (2.6s = fireInterval; the game re-seats it at fireCue 0.65 on every shot, which lands on frame 25 of the 39-frame sheet, baked at 0.641): it shuffles on its two short legs while the sac refills; from 0.18 it squats and draws the sac in, snout lowered; from 0.36 the sac swells in three throbs, harder each time, the fluid inside lighting up, while it rises and leans back so the snout lifts to aim, the lip opens and a teal bead builds on it — the telegraph; at 0.624–0.636 the sac clenches and the bead goes, so the cue frame is the lip flashing with the bead already out; then the kick — body shoved back, snout thrown up — a wobble of the emptied sac, and the shuffle again.",
        "duration": PUMP,
        "tracks": spit_tracks(),
    },
    "death": {
        "description": "The sac goes before the animal does: it swells once against its own wall with the snout thrown up, holds a beat, then drops to two thirds of itself and pulls its spout back in; the loaded bead falls out of the lip onto the ground in front, the glow and the organ go out, and the two short legs splay and fold. Still from 0.85.",
        "duration": 0.44,
        "tracks": death_tracks(),
    },
}

# ============================================================== document
DESCRIPTION = (
    "Ranged sac that holds the far edge of your reach and spits where you're going to be. A bulbous teal sac with a firing snout on the right "
    "— that read is the Gland and is kept — drawn in three values: the sac mid teal over a dark underside, girdled by three muscle bands that "
    "squeeze it, a muscular collar with the eye on it, and a tapered snout ending in a pale lip; the bright teal is kept for what is charged, "
    "the fluid lighting up inside the sac and the bead on the lip, which is the bolt (`ss.enemy.shot`). A lit organ on its back, because it "
    "is hive; two short legs under it, because a thing that holds a distance has to be able to hold it. Built on a skeleton "
    "(scripts/spitter.py): the sac rides its own bone and scales from its centre, the snout is hinged at the collar, and the legs are solved "
    "to feet on the ground. Its one loop is `spit`, the whole shot authored at the cadence it fires at (fireInterval 2.6s, re-seated at "
    "fireCue 0.65 by EnemySystem.cueCycle): the draw and the swell are the telegraph, and the bead leaves on the cue frame. No `elite` "
    "variant on purpose: a standoff body is never marked. Drawn facing +x, the game flips it. Gameplay radius 11. The `death` clip is the "
    "sac going first: one swell against its own wall, a held beat, then the body drops and pulls its spout back in, and the loaded bead "
    "falls out of the snout."
)

# The drawing sits a unit right of centre: the swell and the lean back push the
# sac out behind, and that is where the room is kept.
X0 = 1.0
for p in RIG.parts: p["at"] = [r2(p["at"][0] + X0), p["at"][1]]
SKELETON = RIG.skeleton()
SKELETON["joints"] = {k: [r2(v[0] + X0), v[1]] for k, v in SKELETON["joints"].items()}

doc = {
    "id": "ss.enemy.spitter",
    "name": "Gland",
    "description": DESCRIPTION,
    "tags": ["enemy", "gland"],
    "size": SIZE,
    "meta": {"radius": 11},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": SKELETON,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-spitter.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
