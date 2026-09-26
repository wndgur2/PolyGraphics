"""The Blister — an oil beetle that comes inside your reach and empties itself.

    python3 scripts/blister.py        # rewrites apps/ss/assets/ss-enemy-blister.json

feelers runs it as a stand-off shooter at 190 — well inside a maxed arsenal —
that every 2.4s throws four `e_droplet` in a 0.6 rad fan (`EnemyType.shotCount`,
`shotFan`). It has no fire clip: `scurry` is the one loop it plays, closing,
backing and strafing alike, so the loop carries the one thing the body is for.
The body is built around what it throws. It is drawn as an oil beetle (Meloe),
the blister beetle whose wing cases are two short flaps over a swollen,
segmented abdomen. So the silhouette is the sac: black plates over a red
membrane that shows between them and round the rim, four coral glands along its
flanks (what the fan is made of), the hive's organ riding on top. The two black
elytra stand open in a V over the front of it, because it is always about to
spray. A red head; black pronotum, legs and beaded antennae.

It was hand-placed, and it measured 4.5px of travel at game scale: the legs were
rects turned about their own centres, so knees came apart, and the sac only
slid half a pixel. Contrast on the pan was 1.55. The brief's 2.5 is out of reach
for a red-and-black body on this floor: the contrast is of *mean* luminance, red
carries its brightness in the channel luminance weights least, and a coral or
pink sac lands at the sand's own luminance (a pink-sac build measured 1.06-1.46,
and even a sac with every black part removed tops out near 2.1). Going darker
than the floor is the side that works, so the body is black with the red kept to
what matters (1.68).
It is rebuilt on the rig (scripts/rig.py):

  - the body is a root bone that yaws and surges with the tripod gait
  - six legs, each a femur and tibia solved by two-bone IK to a foot on the
    ground, planted through the stance and swung forward on an outward arc
  - the sac is two bones that wag against the body's yaw with a lag, and it
    *swells*: everything riding the sac is carried out radially from its
    centre (`tracks` below), the plates faster than they grow, so the red
    seams open on every pump, and the sac collapses when it dies
  - the glands pulse in a wave from front to back; the antennae are chains
    that whip with a lag down each link

Seen from above facing +x, mirrored by the game (it is not a `turns` body).
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, wrap, keyset, ik2 as ik, compose,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 44×40, origin at the centre, +x forward, +y down (the "d" side). The
# "u" side is drawn and the "d" side is its mirror.
RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("body", None, (3.0, 0.0), 0.0)
bone("head", "body", (8.2, 0.0), 0.0, 4.0)
bone("sac_0", "body", (1.0, 0.0), 180.0, 7.5)
bone("sac_1", "sac_0", B["sac_0"].end(), 180.0, 6.0)

SIDES = (("u", -1), ("d", 1))
for sd, s in SIDES:
    # the elytron: a short flap from the shoulder, standing out in the V
    bone(f"elytron_{sd}", "body", (4.4, 1.2 * s), 180.0 - 28.0 * s, 7.6)
    # the mandible, hinged at the side of the mouth
    bone(f"mand_{sd}", "head", (12.2, 1.1 * s), -14.0 * s, 2.8)  # pointing forward and in
    # the antenna: three links off the front of the head, bowed outward
    RIG.chain(f"ant_{sd}", "head", (11.6, 1.7 * s), [(2.6, 26.0 * s), (2.6, 36.0 * s), (2.5, 48.0 * s), (2.4, 60.0 * s)])

N_ANT = 4
# Legs: (hip, rest foot, femur, tibia, tarsus) on the u side. Long, as a meloid's are.
LEG_U = {
    "f": ((6.0, -1.8), (12.4, -9.2), 5.4, 6.0, 2.2),
    "m": ((3.4, -2.4), (4.4, -12.2), 5.6, 6.6, 2.2),
    "b": ((1.2, -2.2), (-2.6, -11.4), 5.8, 7.2, 2.4),
}
LEGS = {}
for n, (hip, foot, lf, lt, ls) in LEG_U.items():
    for sd, s in SIDES:
        LEGS[f"{n}_{sd}"] = ((hip[0], abs(hip[1]) * s), (foot[0], abs(foot[1]) * s), lf, lt, ls)

def bend_of(leg):
    """The knee bows away from the midline, and for the mid pair forward."""
    hip, foot, lf, lt, _ = LEGS[leg]
    s = 1 if leg.endswith("_d") else -1
    best, pick = None, 1
    for b in (1, -1):
        h1, _ = ik(hip, foot, lf, lt, b)
        kx, ky = hip[0] + lf * math.cos(R(h1)), hip[1] + lf * math.sin(R(h1))
        score = ky * s + (0.8 * kx if leg.startswith("m") else 0.0)
        if best is None or score > best: best, pick = score, b
    return pick
BEND = {leg: bend_of(leg) for leg in LEGS}
TARSUS_TURN = {"f": 16.0, "m": 0.0, "b": -14.0}  # tarsus off the tibia, turned toward the way the leg points
def tarsus_heading(leg, tibia_h):
    s = 1 if leg.endswith("_d") else -1
    return tibia_h - s * TARSUS_TURN[leg[0]] * (1 if leg[0] != "m" else 0)

for leg, (hip, foot, lf, lt, ls) in LEGS.items():
    hf, ht = ik(hip, foot, lf, lt, BEND[leg])
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", B[f"{leg}_femur"].end(), ht, lt)
    bone(f"{leg}_tarsus", f"{leg}_tibia", B[f"{leg}_tibia"].end(), tarsus_heading(leg, ht), ls)

RIG.seal()
solve = RIG.solve
put = RIG.put

# ============================================================== parts
# A black beetle with red where it matters. Values: darkest (the elytra, the
# pronotum, the tibiae), dark (the sac's plates, femora, antennae), and the red:
# the membrane between the plates, the glands, the head. It is darker than the
# pan's floor on purpose (see the module docstring on contrast).
HAIR_BLOOD = {"color": "$blood.dark", "width": "hair"}

# ---- legs, under everything; rear pair first
for n in ("b", "m", "f"):
    for sd, s in SIDES:
        leg = f"{n}_{sd}"
        lf, lt, ls = LEGS[leg][2], LEGS[leg][3], LEGS[leg][4]
        at, a = RIG.on_bone(f"{leg}_tarsus"); put(f"leg_{leg}_tarsus", f"{leg}_tarsus", at, a, bar(ls, 0.8, 0.55, 0.4), "$dead")
        at, a = RIG.on_bone(f"{leg}_tibia"); put(f"leg_{leg}_tibia", f"{leg}_tibia", at, a, bar(lt, 1.1, 0.85), "$dead", INK_HAIR)
        at, a = RIG.on_bone(f"{leg}_femur"); put(f"leg_{leg}_femur", f"{leg}_femur", at, a, bar(lf, 1.7, 1.2), "$coal", INK_HAIR)
        at, a = RIG.on_bone(f"{leg}_tibia"); put(f"leg_{leg}_knee", f"{leg}_tibia", at, 0.0, circ(0.75), "$blood")

# ---- antennae: beaded, under the head
for sd, s in SIDES:
    for i in range(N_ANT):
        nm = f"ant_{sd}_{i}"; at, a = RIG.on_bone(nm)
        put(nm, nm, at, a, bar(B[nm].length, 0.95 - 0.08 * i, 0.7 - 0.08 * i, 0.5), "$coal", INK_HAIR)

# ---- the sac. Under it all, the red membrane in two halves (front on sac_0,
# rear on sac_1, overlapping so the wag bends it); over it, five black plates
# with red showing between them and round the rim. When the sac swells the
# plates are carried apart faster than they grow, so the red opens up.
SAC_C, SAC_RX, SAC_RY = (-6.6, 0.0), 10.6, 9.2
def sac_hw(x):
    u = (x - SAC_C[0]) / SAC_RX
    return SAC_RY * math.sqrt(max(0.0, 1 - u * u))
def sac_outline(x0, x1, n=14):
    """The sac's rim between x1 (rear) and x0 (front), closed across at the cut ends."""
    xs = [x1 + (x0 - x1) * i / n for i in range(n + 1)]
    top = [(x, -sac_hw(x)) for x in xs]
    return top + [(x, sac_hw(x)) for x in reversed(xs)]
def local(pts, c): return [(x - c[0], y - c[1]) for x, y in pts]
MEM = {"membrane_1": ("sac_1", (-12.6, 0.0), -17.2, -7.6), "membrane_0": ("sac_0", (-3.8, 0.0), -10.0, 3.9)}
for mid, (bn, c, x1, x0) in MEM.items():
    put(mid, bn, c, 0.0, poly(local(sac_outline(x0, x1), c)), "$blood", INK_THIN)

def tergite(w, hh, bow):
    """A plate across the sac: an arc bowed backward, tapering at its ends."""
    n, fr, bk = 8, [], []
    for i in range(n + 1):
        y = -hh + 2 * hh * i / n
        q = (y / hh) ** 2
        half = w / 2 * (1 - 0.45 * q * q)
        x = -bow * (1 - q)
        fr.append((x + half, y)); bk.append((x - half, y))
    return poly(fr + list(reversed(bk)))
# (id, bone, centre x, width)
PLATES = [("plate_4", "sac_1", -15.0, 2.3), ("plate_3", "sac_1", -12.2, 2.7),
          ("plate_2", "sac_0", -9.1, 3.0), ("plate_1", "sac_0", -5.7, 3.1), ("plate_0", "sac_0", -2.3, 3.0)]
for pid, bn, x, w in PLATES:
    put(pid, bn, (x, 0.0), 0.0, tergite(w, sac_hw(x) * 0.86, 0.9), "$coal", INK_HAIR)
# the glands: four blisters along the flanks, what the fan is made of
GLANDS = {"gland_uf": ("sac_0", (-4.2, -8.0), 1.9), "gland_ub": ("sac_0", (-9.0, -7.9), 1.7),
          "gland_df": ("sac_0", (-4.2, 8.0), 1.9), "gland_db": ("sac_0", (-9.0, 7.9), 1.7)}
for gid, (bn, c, r) in GLANDS.items():
    put(gid, bn, c, 0.0, circ(r), "$coral", HAIR_BLOOD)
    put(f"{gid}_shine", bn, (c[0] + 0.5, c[1] - 0.5), 0.0, circ(r * 0.36), "$coral.light2")
RIG.use("organ", "sac_0", (-7.4, 0.0), "ss.lib.organ", scale=0.5)

# ---- the elytra, two short flaps standing open in a V over the front of the sac
ELYTRON = [(-0.6, -1.0), (1.5, -2.2), (4.6, -2.6), (7.2, -2.0), (8.2, -0.6), (7.8, 0.9), (5.8, 1.8), (2.4, 1.8), (-0.6, 1.0)]
for sd, s in SIDES:
    at, a = RIG.on_bone(f"elytron_{sd}")
    put(f"elytron_{sd}", f"elytron_{sd}", at, a, poly([(x, y * -s) for x, y in ELYTRON]), "$dead", {"color": "$blood.dark", "width": "hair"})
    at, a = RIG.on_bone(f"elytron_{sd}", 4.0, 0.7 * s)
    put(f"elytron_{sd}_sheen", f"elytron_{sd}", at, a, ell(2.6, 0.45), "$coal")

# ---- pronotum and head
put("pronotum", "body", (6.0, 0.0), 0.0, poly([(2.6, -1.3), (1.9, -2.6), (0.0, -2.9), (-2.0, -2.4), (-2.6, 0.0),
                                                (-2.0, 2.4), (0.0, 2.9), (1.9, 2.6), (2.6, 1.3)]), "$dead", INK_THIN)
put("pronotum_sheen", "body", (5.6, -1.3), -8.0, ell(1.5, 0.45), "$coal")
for sd, s in SIDES:
    at, a = RIG.on_bone(f"mand_{sd}")
    k = -s  # local +y is toward the midline on the u side
    put(f"mand_{sd}", f"mand_{sd}", at, a, poly([(-0.4, -0.7 * k), (1.3, -0.8 * k), (2.6, -0.2 * k), (3.0, 0.5 * k),
                                                 (2.2, 0.4 * k), (1.2, 0.5 * k), (-0.4, 0.6 * k)]), "$ink")
put("head", "head", (10.3, 0.0), 0.0, poly([(2.6, -1.2), (2.0, -2.6), (0.0, -3.1), (-2.0, -2.4), (-2.4, 0.0),
                                            (-2.0, 2.4), (0.0, 3.1), (2.0, 2.6), (2.6, 1.2)]), "$blood", INK_THIN)
put("head_shine", "head", (9.9, -1.3), -10.0, ell(1.1, 0.45), "$blood.light")
for sd, s in SIDES:
    put(f"eye_{sd}", "head", (11.1, 2.1 * s), 0.0, ell(0.95, 0.75), "$ink")

RIG.check()
BASE = {p["id"]: p for p in RIG.parts}

# ============================================================== swelling
# Parts riding a sac bone are carried out from that bone's swell centre by the
# swell factor, and the plates themselves (and the organ) scale by it.
SWELL_CENTRE = {"sac_0": (-5.4, 0.0), "sac_1": (-12.6, 0.0)}  # rest world points
def swell_local(bn):
    x, y, a = RIG.rest[bn]
    c, sn = math.cos(R(a)), math.sin(R(a))
    dx, dy = SWELL_CENTRE[bn][0] - x, SWELL_CENTRE[bn][1] - y
    return (dx * c + dy * sn, -dx * sn + dy * c)
SWELL_LOCAL = {bn: swell_local(bn) for bn in SWELL_CENTRE}
PLATE_IDS = {pid for pid, *_ in PLATES}
SHELLS = PLATE_IDS | set(MEM)
SPREAD = 1.8  # the sac's parts are carried out this many times faster than it swells
def spread(k): return 1.0 + SPREAD * (k - 1.0)

def tracks(pose_at, swell_at, ts, scales=None, extra=None, still=()):
    """Rig.tracks, plus the sac's swell: `swell_at(t)` is {sac bone: factor}."""
    rest = RIG.posed_parts({})
    series = {pid: ([], [], [], []) for pid in RIG.attach}
    for t in ts:
        pose = pose_at(t)
        world = solve(pose)
        now = RIG.posed_parts(pose)
        sw = swell_at(t)
        for pid, (x, y, a) in now.items():
            bn = RIG.attach[pid]
            k = sw.get(bn, 1.0)
            if bn in SWELL_LOCAL:
                kp = spread(k)
                cx, cy, _ = compose(world[bn], (*SWELL_LOCAL[bn], 0.0))
                x, y = cx + kp * (x - cx), cy + kp * (y - cy)
            bx, by, ba = rest[pid]
            own = k if pid in PLATE_IDS else (spread(k) if pid in MEM else 1.0)
            sc = own * ((scales or {}).get(pid, lambda t: 1.0))(t)
            for arr, v in zip(series[pid], (x - bx, y - by, wrap(a - ba), sc)):
                arr.append(v)
    out = []
    for p in RIG.parts:
        pid = p["id"]
        xs, ys, rs, ss = series[pid]
        for prop, vs, rest_v in (("x", xs, 0.0), ("y", ys, 0.0), ("rot", rs, 0.0), ("scale", ss, 1.0)):
            if prop == "rot" and pid in still: continue
            if max(abs(v - rest_v) for v in vs) > 0.005:
                out.append({"part": pid, "prop": prop, "keys": [[r2(t), round(v, 3) if prop == "scale" else r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
    for pid, prop, fn in (extra or []):
        out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(fn(t))] for t in ts], "ease": "linear"})
    return out

def plant(pose, feet):
    world = solve(pose)
    for leg, (hip, foot, lf, lt, ls) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, BEND[leg])
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_tarsus"] = tarsus_heading(leg, ht)
    return pose

def chain_set(pose, prefix, deltas):
    for i, d in enumerate(deltas): pose[f"{prefix}_{i}"] = pose.get(f"{prefix}_{i}", 0.0) + d

# ============================================================== scurry
# A tripod: f_u, m_d, b_u step together, then f_d, m_u, b_d. Each foot is
# planted for half the cycle and slides back under the body as it pushes, then
# swings forward on an outward arc. The body yaws toward the side whose tripod
# is pushing and surges on each push; the sac wags against it a beat later,
# pumps on every step, and the glands swell in a wave from front to back.
STRIDE = 5.0   # half the foot's travel along x
SWING_OUT = 4.8
TRIPOD = {"f_u": 0.0, "m_d": 0.0, "b_u": 0.0, "f_d": 0.5, "m_u": 0.5, "b_d": 0.5}
YAW = 11.0

def foot_at(leg, t):
    hip, (fx, fy), *_ = LEGS[leg]
    ph = (t + TRIPOD[leg]) % 1.0
    s = 1 if leg.endswith("_d") else -1
    if ph < 0.5:
        u = ph / 0.5
        return (fx + STRIDE * (1 - 2 * u), fy)
    v = (ph - 0.5) / 0.5
    e = smooth(0.0, 1.0, v)
    return (fx - STRIDE + 2 * STRIDE * e, fy + s * SWING_OUT * math.sin(math.pi * v))

def scurry_pose(t):
    yaw = YAW * cyc(t, 0.25)
    pose = {"body": (1.0 * cyc(2 * t, 0.1), -0.9 * cyc(t, 0.25), yaw)}
    pose["head"] = -0.6 * YAW * cyc(t - 0.08, 0.25)
    pose["sac_0"] = -0.9 * YAW * cyc(t - 0.1, 0.25)
    pose["sac_1"] = -1.8 * YAW * cyc(t - 0.2, 0.25)
    for sd, s in SIDES:
        pose[f"elytron_{sd}"] = s * 6.0 * cyc(2 * t, 0.05)
        pose[f"mand_{sd}"] = s * 10.0 * max(0.0, cyc(2 * t, 0.3))
        # the antennae tap by turns, once a cycle each: one swept forward and in
        # while the other is thrown wide, the whip travelling out along the links
        chain_set(pose, f"ant_{sd}", [s * (9.0 + 3.0 * i) * cyc(t - 0.06 * i, 0.25 if sd == "u" else 0.75) - 0.4 * yaw for i in range(N_ANT)])
    feet = {leg: foot_at(leg, t) for leg in LEGS}
    return plant(pose, feet)

def scurry_swell(t):
    k = 0.07 * cyc(2 * t, -0.05)
    return {"sac_0": 1.0 + k, "sac_1": 1.0 + 1.2 * 0.07 * cyc(2 * t, -0.15)}

def gland_pulse(front, lag):
    return lambda t: 1.0 + (0.34 if front else 0.28) * max(0.0, cyc(2 * t - lag, 0.0))

SCURRY_SCALES = {"gland_uf": gland_pulse(True, 0.0), "gland_df": gland_pulse(True, 0.0),
                 "gland_ub": gland_pulse(False, 0.16), "gland_db": gland_pulse(False, 0.16)}

# ============================================================== death
# Anticipation: the sac swells tight and the elytra clamp down on it, the legs
# brace. Release: the four glands burst outward, the sac collapses, the elytra
# fly open, the body is thrown forward. Settle: the legs curl in, the antennae
# lie back, the organ flares and goes out. Still from 0.85.
def death_parts(t):
    a = smooth(0.0, 0.16, t)
    burst = smooth(0.14, 0.3, t)
    settle = smooth(0.28, 0.82, t)
    return a, burst, settle

def death_pose(t):
    a, burst, settle = death_parts(t)
    jolt = math.sin(math.pi * smooth(0.14, 0.45, t))
    pose = {"body": (-1.0 * a * (1 - burst) + 1.2 * jolt - 0.2 * settle, 0.4 * settle, 3.0 * jolt + 9.0 * settle)}
    pose["head"] = -4.0 * a * (1 - burst) + 10.0 * settle
    pose["sac_0"] = 6.0 * jolt - 4.0 * settle
    pose["sac_1"] = -8.0 * jolt + 10.0 * settle
    for sd, s in SIDES:
        pose[f"elytron_{sd}"] = s * (8.0 * a * (1 - burst) - 40.0 * burst + 8.0 * settle)
        pose[f"mand_{sd}"] = s * (22.0 * a * (1 - burst) - 16.0 * settle)
        chain_set(pose, f"ant_{sd}", [s * (-10.0 * jolt + 36.0 * settle), s * 22.0 * settle, s * 18.0 * settle, s * 14.0 * settle])
    feet = {}
    for leg, (hip, foot, lf, lt, ls) in LEGS.items():
        sgn = 1 if leg.endswith("_d") else -1
        bx, by = foot
        splay = (bx + (bx - hip[0]) * 0.12, by + sgn * 1.4)
        braced = (lerp(bx, bx - (bx - hip[0]) * 0.1, a), by)
        curled = (hip[0] + (bx - hip[0]) * 0.35 + (1.2 if leg[0] == "f" else -1.0), hip[1] + (by - hip[1]) * 0.55)
        p = (lerp(braced[0], splay[0], burst), lerp(braced[1], splay[1], burst))
        feet[leg] = (lerp(p[0], curled[0], settle), lerp(p[1], curled[1], settle))
    return plant(pose, feet)

def death_swell(t):
    a, burst, settle = death_parts(t)
    k = 1.0 + 0.14 * a * (1 - burst) - 0.09 * burst - 0.04 * settle
    return {"sac_0": k, "sac_1": k - 0.04 * settle}

def gland_burst(t):
    a, burst, settle = death_parts(t)
    return 1.0 + 0.45 * a + 1.6 * burst
def gland_fade(t): return 1.0 - smooth(0.2, 0.46, t)

DEATH_SCALES = {g: gland_burst for g in GLANDS}
DEATH_SCALES.update({f"{g}_shine": gland_burst for g in GLANDS})
DEATH_EXTRA = [(g, "opacity", gland_fade) for g in GLANDS] + [(f"{g}_shine", "opacity", gland_fade) for g in GLANDS] + [
    ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.3, 0.82, t)),
]
DEATH_SCALES["organ"] = lambda t: 1.0 + 0.45 * math.sin(math.pi * smooth(0.1, 0.45, t)) - 0.2 * smooth(0.45, 0.82, t)

STILL = set(GLANDS) | {f"{g}_shine" for g in GLANDS} | {"eye_u", "eye_d", "organ"} | {f"leg_{l}_knee" for l in LEGS}
animations = {}
animations["scurry"] = {
    "description": "A quick tripod scurry: each foot planted and pushed back under the body, then swung forward on an outward arc, three at a time; the body yaws toward the pushing side and surges on each push; the swollen sac wags against it a beat later and pumps on every step, the four glands along its flanks swelling in a wave from front to back; the open elytra flutter, the mandibles work and the beaded antennae whip with a lag down each link.",
    "duration": 0.42,
    "tracks": tracks(scurry_pose, scurry_swell, keyset(24), SCURRY_SCALES, still=STILL),
}
TS_DEATH = [0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.24, 0.28, 0.32, 0.36, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The sac swells tight and the elytra clamp down on it while the legs brace; then the four glands burst outward and vanish, the sac collapses between them, the elytra fly open and the body is thrown forward; it settles with the legs curled in, the antennae lying back, the sac slack and askew; the organ flares and goes out. Still from 0.85.",
    "duration": 0.4,
    "tracks": tracks(death_pose, death_swell, TS_DEATH, DEATH_SCALES, DEATH_EXTRA, still=STILL),
}

# ============================================================== document
DESCRIPTION = (
    "A blister beetle, in the Gland's slot by turns, and the one shooter on the pan that comes inside your reach (standoff 190) and empties "
    "itself in a fan. Drawn as the oil beetle, the blister beetle whose wing cases are two short flaps over a swollen abdomen, because "
    "what it throws is the body. Seen from above, facing +x: a swollen sac of five black plates over a blood-red membrane that shows "
    "between them and round the rim, four coral glands swelling along its flanks (what the fan is made of) and the hive's organ riding "
    "on it; two short black elytra standing open in a V over the front of it, because it is always about to spray; a black pronotum, a "
    "blood-red head with black eyes and mandibles, long black legs with red knees and beaded antennae. Red-and-black, the warning colours "
    "the real animal wears, and nothing else on the pan is red. Darker than the pan's floor on purpose: a red-and-black body cannot be "
    "lighter than it. `ss.enemy.droplet` is what it throws, four at a time. Built on a skeleton (scripts/blister.py): six legs solved to "
    "planted feet in a tripod gait, a two-bone sac that wags against the body and swells about its centre (the plates part as it fills, "
    "so the red opens up), antennae as lagged chains. No `elite` variant: a squad body is never marked. Mirrored by the game. Gameplay "
    "radius 10. The `death` clip swells the sac tight, bursts the four glands outward, flings the elytra open and lets the sac collapse."
)

doc = {
    "id": "ss.enemy.blister",
    "name": "Blister",
    "description": DESCRIPTION,
    "tags": ["enemy", "blister"],
    "size": [44, 40],
    "meta": {"radius": 10},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-blister.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
