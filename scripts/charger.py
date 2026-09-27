"""The Lance — a bow and a barb, two animals that only work together.

    python3 scripts/charger.py        # rewrites apps/ss/assets/ss-enemy-charger.json

feelers runs it as a lobber (`EnemyType` `charger`): it walks into range
(`walk`, the idle ANIMATED_KEYS loops), braces for `windup` 0.75s playing
`coil` once stretched to it (`e_charger_coil`, held on its last frame), and on
the release comes apart — the sprite swaps to the `loosed` texture (the barb
alone, static, lobbed on an arc), while the bow is dropped where it stood as a
husk playing the `spent` variant's `strike` once (`e_charger_spent`) and fading
over 1.4s. The barb lands and plays the `planted` variant's `fuse` once,
stretched to its jittered `fuseTime` (`e_charger_planted`), then goes off. The
`death` clip plays when the pair is shot down on the approach — the only time
it can be; the loosed barb has 1000 hp.

Baked sheets sample frames at f/N and never reach t = 1, so every one-shot here
reaches its last pose by ~0.88 and holds it: the coil's held frame is the pose
the spent bow's first frame opens on, and the fuse's peak is on the frame the
blast replaces.

It was hand-placed, and it measured 2.8px of travel on the walk at game scale:
legs were sticks turned about their own centres (knees came apart, nothing was
planted), the prods swung two degrees, the body never moved, and the barb lay
over the bow's head so the pair had no face. Rebuilt on the rig (scripts/rig.py):

  - the stock is the root bone; it yaws and surges with a tripod gait
  - six legs, each a femur and tibia solved by two-bone IK to a planted foot
  - each prod-limb is a chain of four bones from a shoulder knuckle, so a bend
    runs down it as a wave and the tip carries the whole of it
  - the barb is one bone lying in the groove; it slides along it, and its sac
    swells about its own centre with the two side plates carried apart faster
    than they grow, so the lit seam down its back opens as it fills

Seen from above, facing +x, mirrored by the game (it never rotates).

The canvas grew from 60×52 to 72×60: the drawn-back barb hangs its sac off
the end of the stock at the top of the coil, and the prod tips sweep near the
old top and bottom edges on the draw and the throw. Contrast on the Plains
floor is held at or above the original's 3.16 by keeping the big masses light
— the stock `$carapace.light2`, both prods `$husk`, the barb's plates
`$verdigris.light` — since the hairline ink on six legs and eight prod links
pulls the mean down.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, wrap, keyset, ik2 as ik, compose,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 72×60, origin at the centre, +x forward, +y down (the "d" side). The
# "u" side is drawn and the "d" side is its mirror.
RIG = Rig()
B = RIG.bones
bone = RIG.bone
SIDES = (("u", -1), ("d", 1))

bone("body", None, (0.0, 0.0), 0.0)
bone("head", "body", (11.0, 0.0), 0.0, 8.0)
bone("barb", "body", (-4.0, 0.0), 0.0, 1.0)

# The prod-limbs: four links from a knuckle on each shoulder, thrown out
# sideways, sweeping a little back and then kicked forward at the tip — the
# recurve a bow limb has, and the carriage a beetle's antenna has.
SHOULDER = (6.0, 6.2)
PROD = [(5.4, 100.0), (5.0, 92.0), (4.6, 79.0), (4.2, 58.0)]  # (length, heading off +x toward the side)
PROD_W = [3.8, 3.1, 2.4, 1.6, 0.35]  # width at each joint, root to tip
N_PROD = len(PROD)
for sd, s in SIDES:
    RIG.chain(f"prod_{sd}", "body", (SHOULDER[0], SHOULDER[1] * s), [(L, h * s) for L, h in PROD])
    # palps: two short feelers off the nose
    RIG.chain(f"palp_{sd}", "head", (18.4, 1.7 * s), [(2.4, 30.0 * s), (2.1, 12.0 * s)])

# Legs: (hip, rest foot, femur, tibia, tarsus) on the u side.
LEG_U = {
    "f": ((3.6, -4.4), (11.6, -11.6), 5.6, 6.4, 2.0),
    "m": ((-4.2, -5.4), (-3.6, -15.4), 5.8, 6.6, 2.0),
    "b": ((-11.4, -5.0), (-18.6, -12.6), 5.8, 6.6, 2.2),
}
LEGS = {}
for n, (hip, foot, lf, lt, ls) in LEG_U.items():
    for sd, s in SIDES:
        LEGS[f"{n}_{sd}"] = ((hip[0], abs(hip[1]) * s), (foot[0], abs(foot[1]) * s), lf, lt, ls)

def bend_of(leg):
    """The knee bows away from the midline."""
    hip, foot, lf, lt, _ = LEGS[leg]
    s = 1 if leg.endswith("_d") else -1
    best, pick = None, 1
    for b in (1, -1):
        h1, _ = ik(hip, foot, lf, lt, b)
        ky = hip[1] + lf * math.sin(R(h1))
        if best is None or ky * s > best: best, pick = ky * s, b
    return pick
BEND = {leg: bend_of(leg) for leg in LEGS}
TARSUS_TURN = {"f": 18.0, "m": 0.0, "b": -16.0}
def tarsus_heading(leg, tibia_h):
    s = 1 if leg.endswith("_d") else -1
    return tibia_h - s * TARSUS_TURN[leg[0]]

for leg, (hip, foot, lf, lt, ls) in LEGS.items():
    hf, ht = ik(hip, foot, lf, lt, BEND[leg])
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", B[f"{leg}_femur"].end(), ht, lt)
    bone(f"{leg}_tarsus", f"{leg}_tibia", B[f"{leg}_tibia"].end(), tarsus_heading(leg, ht), ls)

RIG.seal()
solve = RIG.solve
put = RIG.put

# ============================================================== parts
# Two animals, two families. The bow: a lavender stock (`$carapace`, light on
# top, banded darker) with its bone parts — head and prod-limbs — in pale
# `$husk`. The barb: plated in muted greens (`$verdigris` plates over a `$moss`
# membrane) with the one loud thing on the sprite, the gold core, showing down
# the seam between its plates. Two lit organs: the bow's on its head, the
# barb's on its neck.

# ---- legs, under everything
for n in ("b", "m", "f"):
    for sd, s in SIDES:
        leg = f"{n}_{sd}"
        lf, lt, ls = LEGS[leg][2], LEGS[leg][3], LEGS[leg][4]
        at, a = RIG.on_bone(f"{leg}_tarsus"); put(f"leg_{leg}_tarsus", f"{leg}_tarsus", at, a, bar(ls, 1.1, 0.6, 0.4), "$carapace.light", INK_HAIR)
        at, a = RIG.on_bone(f"{leg}_tibia"); put(f"leg_{leg}_tibia", f"{leg}_tibia", at, a, bar(lt, 1.6, 1.1), "$carapace.light", INK_HAIR)
        at, a = RIG.on_bone(f"{leg}_femur"); put(f"leg_{leg}_femur", f"{leg}_femur", at, a, bar(lf, 2.3, 1.7), "$carapace.light2", INK_HAIR)
        at, a = RIG.on_bone(f"{leg}_tibia"); put(f"leg_{leg}_knee", f"{leg}_tibia", at, 0.0, circ(0.9), "$carapace.light2")

# ---- palps, under the head
for sd, s in SIDES:
    for i in range(2):
        nm = f"palp_{sd}_{i}"; at, a = RIG.on_bone(nm)
        put(nm, nm, at, a, bar(B[nm].length, 0.9 - 0.2 * i, 0.6 - 0.2 * i, 0.4), "$husk.dark", INK_HAIR)

# ---- the prod-limbs, roots tucked under the shoulders
for sd, s in SIDES:
    fill = "$husk"
    for i in range(N_PROD):
        nm = f"prod_{sd}_{i}"; at, a = RIG.on_bone(nm)
        L = B[nm].length
        shape = bar(L, PROD_W[i], PROD_W[i + 1], 0.7 if i < N_PROD - 1 else 0.2)
        put(nm, nm, at, a, shape, fill, INK_HAIR)
    # a dark vein down the trailing edge of the two middle links
    for i in (1, 2):
        nm = f"prod_{sd}_{i}"
        at, a = RIG.on_bone(nm, B[nm].length * 0.5, -0.55 * PROD_W[i + 1] * 0.5 * (1 if sd == "u" else -1) * -1)
        put(f"vein_{sd}_{i}", nm, at, a, rect(B[nm].length * 0.8, 0.55, 0.27), "$husk.dark2")

# ---- the stock: thorax and abdomen in one outline, the shoulders swelling
# where the prods mount, tapering to a point behind
STOCK_HW = [(11.8, 3.0), (9.6, 5.0), (6.8, 7.6), (3.6, 7.3), (1.0, 6.0), (-1.8, 6.6), (-7.0, 7.0),
            (-12.5, 6.5), (-17.5, 5.2), (-21.5, 3.4), (-24.0, 1.6), (-25.0, 0.0)]
def half_outline(tbl):
    top = [(x, -w) for x, w in tbl]
    bot = [(x, w) for x, w in reversed(tbl) if w > 0]
    return top + bot
put("stock", "body", (0.0, 0.0), 0.0, poly(half_outline(STOCK_HW)), "$carapace.light2", INK_THIN)
def stock_hw(x):
    for (x0, w0), (x1, w1) in zip(STOCK_HW, STOCK_HW[1:]):
        if x1 <= x <= x0: return lerp(w1, w0, (x - x1) / (x0 - x1))
    return 0.0
# the abdomen's segments, dark bands across it; the waist between thorax and abdomen
for i, x in enumerate((1.0, -6.0, -11.5, -16.5, -20.6)):
    hw = stock_hw(x) - 0.5
    put(f"band_{i}", "body", (x, 0.0), 0.0, poly([(0.55, -hw), (-0.55, -hw * 0.98), (-0.9, 0.0), (-0.55, hw * 0.98), (0.55, hw), (0.2, 0.0)]), "$carapace.light")
put("stock_shine", "body", (-8.0, -4.6), -2.0, ell(10.0, 1.2), "$dusk.light")
put("thorax_shine", "body", (5.0, -5.0), -12.0, ell(2.6, 1.0), "$dusk.light")
put("stock_shade", "body", (-8.0, 5.0), 2.0, ell(11.0, 1.2), "$carapace.light")
# the knuckles the prods hang from
for sd, s in SIDES:
    put(f"knuckle_{sd}", "body", (SHOULDER[0] + 0.2, SHOULDER[1] * s * 1.02), 0.0, ell(2.3, 1.9), "$husk.dark" if sd == "d" else "$husk", INK_HAIR)
# the groove the barb lies in, down the middle of the stock
GROOVE = [(9.8, 1.2), (8.6, 2.5), (0.0, 2.9), (-12.0, 2.9), (-19.5, 2.2), (-21.8, 0.9), (-22.4, 0.0)]
put("groove", "body", (0.0, 0.0), 0.0, poly(half_outline(GROOVE)), "$carapace")

# ---- the bow's head, at the leading end, and its organ
HEAD = [(19.6, 0.0), (19.0, -2.3), (17.2, -3.9), (14.4, -4.5), (11.8, -3.8), (10.4, -2.0), (10.0, 0.0)]
put("head", "head", (0.0, 0.0), 0.0, poly(half_outline(HEAD)), "$husk", INK_THIN)
put("head_shade", "head", (14.6, 2.6), 4.0, ell(3.6, 1.0), "$husk.dark")
put("head_shine", "head", (16.0, -2.3), -12.0, ell(2.2, 0.8), "$white@soft")
for sd, s in SIDES:
    put(f"eye_{sd}", "head", (16.9, 2.9 * s), -18.0 * s, ell(1.2, 0.85), "$ink")
RIG.use("organ", "head", (13.8, 0.0), "ss.lib.organ", scale=0.44)

# ---- the barb, in the groove: the point laid under the sac with its rear
# buried, the sac a membrane with two plates over it and the core lit between
# them, the barb's organ on its neck ahead of the core
SC = (-9.0, 0.0)           # the sac's centre, which it swells about
SAC_RX_B, SAC_RX_F, SAC_RY = 8.8, 8.4, 5.3
def sac_hw(u):
    """Half-width of the sac at x offset `u` from its centre."""
    rx = SAC_RX_F if u > 0 else SAC_RX_B
    q = max(0.0, 1 - (u / rx) ** 2)
    return SAC_RY * math.sqrt(q) * (1 - 0.18 * max(0.0, u / rx) ** 2)
def sac_outline(n=18):
    us = [-SAC_RX_B + (SAC_RX_B + SAC_RX_F) * i / n for i in range(n + 1)]
    return [(u, -sac_hw(u)) for u in us] + [(u, sac_hw(u)) for u in reversed(us)][1:-1]
POINT = [(-4.8, -1.6), (2.6, -1.9), (2.0, -3.5), (4.6, -2.4), (7.6, -1.2), (10.8, 0.0),
         (7.6, 1.2), (4.6, 2.4), (2.0, 3.5), (2.6, 1.9), (-4.8, 1.6)]
put("barb_point", "barb", (0.0, 0.0), 0.0, poly(POINT), "$verdigris.dark", INK_HAIR)
put("barb_ridge", "barb", (5.6, 0.0), 0.0, rect(6.4, 0.7, 0.35), "$moss")
put("barb_sac", "barb", SC, 0.0, poly(sac_outline()), "$verdigris.dark", INK_THIN)
put("barb_core", "barb", (SC[0] + 0.6, 0.0), 0.0, ell(5.0, 3.3),
    {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$gold.light"], [0.45, "$gold"], [1, "$ember@0.15"]]})
def plate(sgn):
    """A side plate over the sac: its outer edge is the sac's rim, its inner edge a lens round the seam."""
    us = [-SAC_RX_B * 0.92 + (SAC_RX_B * 0.92 + SAC_RX_F * 0.9) * i / 16 for i in range(17)]
    outer = [(u, sgn * (sac_hw(u) - 0.15)) for u in us]
    def seam(u):
        rx = SAC_RX_F if u > 0 else SAC_RX_B
        return 1.75 * math.sqrt(max(0.0, 1 - (u / (rx * 0.92)) ** 2))
    inner = [(u, sgn * seam(u)) for u in reversed(us)]
    return outer + inner
for sd, s in SIDES:
    pc = (SC[0], 2.6 * s)  # the plate's own origin, which it is carried out from the sac's centre by
    pts = [(x, y - pc[1]) for x, y in plate(s)]
    put(f"barb_plate_{sd}", "barb", pc, 0.0, poly(pts), "$verdigris.light" if sd == "u" else "$verdigris", INK_HAIR)
    put(f"barb_plate_{sd}_shine", "barb", (SC[0] - 1.0, 3.2 * s), 0.0, ell(4.4, 0.7), "$husk@soft" if sd == "u" else "$verdigris.light")
RIG.use("barb_organ", "barb", (1.4, 0.0), "ss.lib.organ", scale=0.4)

RIG.check()
BASE = {p["id"]: p for p in RIG.parts}
BARB_PARTS = [p["id"] for p in RIG.parts if RIG.attach[p["id"]] == "barb"]
BOW_PARTS = [p["id"] for p in RIG.parts if RIG.attach[p["id"]] != "barb"]

# ============================================================== swelling
# The sac swells about SC; the plates are carried out from it faster than they
# grow (the seam opens), and the point and the organ are pushed forward so they
# stay proud of the thing swallowing them.
PLATE_IDS = {f"barb_plate_{sd}" for sd, _ in SIDES} | {f"barb_plate_{sd}_shine" for sd, _ in SIDES}
PUSHED = {"barb_point": 1.0, "barb_ridge": 1.0, "barb_organ": 1.0}
SPREAD = 1.7
def barb_local(pt):
    x, y, a = RIG.rest["barb"]
    return (pt[0] - x, pt[1] - y)
SC_LOCAL = barb_local(SC)

def tracks(pose_at, ts, swell_at=None, scales=None, extra=None, still=()):
    """Rig.tracks, plus the barb's swell: `swell_at(t)` is (sac factor, core factor)."""
    rest = RIG.posed_parts({})
    series = {pid: ([], [], [], []) for pid in RIG.attach}
    for t in ts:
        pose = pose_at(t)
        world = solve(pose)
        now = RIG.posed_parts(pose)
        k, kc = swell_at(t) if swell_at else (1.0, 1.0)
        bx_, by_, ba_ = world["barb"]
        cx, cy, _ = compose(world["barb"], (*SC_LOCAL, 0.0))
        for pid, (x, y, a) in now.items():
            sc = 1.0
            if RIG.attach[pid] == "barb":
                if pid in PLATE_IDS:
                    kp = 1.0 + SPREAD * (k - 1.0)
                    x, y = cx + kp * (x - cx), cy + kp * (y - cy)
                    sc = k
                elif pid == "barb_sac":
                    sc = k
                elif pid == "barb_core":
                    x, y = cx + k * (x - cx), cy + k * (y - cy)
                    sc = kc
                elif pid in PUSHED:
                    push = (k - 1.0) * SAC_RX_F * PUSHED[pid]
                    x += push * math.cos(R(ba_)); y += push * math.sin(R(ba_))
            sc *= ((scales or {}).get(pid, lambda t: 1.0))(t)
            rx, ry, ra = rest[pid]
            for arr, v in zip(series[pid], (x - rx, y - ry, wrap(a - ra), sc)):
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

# ============================================================== pose helpers
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

LOAD = [14.0, 18.0, 22.0, 27.0]   # per-link bend under a full draw, degrees, toward the back
def prods(pose, load, extra=(0.0, 0.0, 0.0, 0.0)):
    """Bend both prod-limbs back by `load` (1 = full draw; negative throws them forward), plus `extra` (+ = forward)."""
    for sd, s in SIDES:
        # u limbs point -y: turning toward -x (back) is a negative turn; d is the mirror
        chain_set(pose, f"prod_{sd}", [s * (load * L - e) for L, e in zip(LOAD, extra)])

def barb_slide(pose, dx):
    """Slide the barb along the groove by `dx` — a turn-free move, so it is written as the barb's own offset."""
    pose["_barb_dx"] = pose.get("_barb_dx", 0.0) + dx

# Rig.solve has no translation for a child bone, so the barb's slide rides on
# top of the solved pose: a wrapper that moves the barb bone along its heading.
_solve = RIG.solve
def solve_slide(pose):
    out = _solve(pose)
    dx = pose.get("_barb_dx", 0.0)
    if dx:
        x, y, a = out["barb"]
        out["barb"] = (x + dx * math.cos(R(a)), y + dx * math.sin(R(a)), a)
    return out
RIG.solve = solve_slide
solve = solve_slide

def rest_feet():
    return {leg: LEGS[leg][1] for leg in LEGS}

# ============================================================== walk
# A tripod: f_u, m_d, b_u step together, then f_d, m_u, b_d. The stock yaws to
# the pushing side and surges on each push. Over it, once a loop, the pair
# breathes against its own tension: the prods bend back a little from the root
# out (the bend arriving at the tips last) and the barb rides the draw back
# down its groove, then both ease forward again. The organs pulse out of phase.
STRIDE = 3.4
SWING_OUT = 2.4
TRIPOD = {"f_u": 0.0, "m_d": 0.0, "b_u": 0.0, "f_d": 0.5, "m_u": 0.5, "b_d": 0.5}
YAW = 4.0
def foot_at(leg, t, dx=0.0, out=0.0):
    hip, (fx, fy), *_ = LEGS[leg]
    s = 1 if leg.endswith("_d") else -1
    ph = (t + TRIPOD[leg]) % 1.0
    if ph < 0.5:
        u = ph / 0.5
        return (fx + dx + STRIDE * (1 - 2 * u), fy + s * out)
    v = (ph - 0.5) / 0.5
    e = smooth(0.0, 1.0, v)
    return (fx + dx - STRIDE + 2 * STRIDE * e, fy + s * (out + SWING_OUT * math.sin(math.pi * v)))

def breath(t): return cyc(t, 0.0)
def walk_pose(t):
    yaw = YAW * cyc(t, 0.25)
    pose = {"body": (0.9 * cyc(2 * t, 0.1), -0.7 * cyc(t, 0.25), yaw)}
    pose["head"] = -0.7 * YAW * cyc(t - 0.07, 0.25)
    for sd, s in SIDES:
        # the wave down each limb: the same breath, later at each joint, deeper toward the tip
        chain_set(pose, f"prod_{sd}", [s * (0.55 + 0.1 * i) * LOAD[i] * 0.55 * breath(t - 0.07 * i) - 0.5 * yaw * (i == 0) for i in range(N_PROD)])
        chain_set(pose, f"palp_{sd}", [s * 16.0 * cyc(2 * t, 0.2 + (0.5 if sd == "d" else 0.0)), s * 20.0 * cyc(2 * t, 0.1 + (0.5 if sd == "d" else 0.0))])
    barb_slide(pose, -1.6 * (0.5 + 0.5 * breath(t - 0.1)))
    feet = {leg: foot_at(leg, t) for leg in LEGS}
    return plant(pose, feet)
def walk_swell(t): return (1.0 + 0.05 * breath(t - 0.1), 1.0 + 0.14 * breath(t - 0.15))

# ============================================================== coil
# Wound rather than eased: a fast first draw, a slow creep against the load, a
# give, a last snatch — then held, trembling, and still from 0.88.
def coil_load(t):
    if t < 0.16: return 0.55 * smooth(0.0, 0.16, t)
    if t < 0.56: return 0.55 + 0.30 * smooth(0.16, 0.56, t)
    if t < 0.66: return 0.85 - 0.08 * smooth(0.56, 0.66, t)
    return 0.77 + 0.23 * smooth(0.66, 0.76, t)
def tremble(t): return math.sin(2 * math.pi * 11 * t) * smooth(0.72, 0.78, t) * (1 - smooth(0.8, 0.88, t))
BRACE_BACK = 1.8      # the stock settles back against the draw
BRACE_OUT = 2.6       # the stance opens this much wider
DRAW = 9.6            # how far the barb hauls back down the groove
def coil_pose(t):
    L = coil_load(t)
    tr = tremble(t)
    pose = {"body": (-BRACE_BACK * L, 0.0, 0.0)}
    pose["head"] = 0.0
    prods(pose, L + 0.06 * tr)
    for sd, s in SIDES:
        chain_set(pose, f"palp_{sd}", [s * 34.0 * L, s * 20.0 * L])
    barb_slide(pose, -DRAW * L + 0.35 * tr)
    feet = {}
    for leg, (hip, (fx, fy), *_) in LEGS.items():
        s = 1 if leg.endswith("_d") else -1
        feet[leg] = (fx - 1.2 * L, fy + s * BRACE_OUT * L)
    return plant(pose, feet)
def coil_swell(t):
    L = coil_load(t)
    return (1.0 + 0.12 * L, 1.0 + 0.5 * L + 0.05 * tremble(t))

# ============================================================== strike
# The release, opening on the coil's held pose. The prods unwind through rest
# and past it (the tips thrown forward), rebound, and settle fallen open past
# rest, slack; the stock kicks back on the recoil and the feet slip; the barb —
# in the base body — leaves the string and lunges a full length forward. Under
# `spent` the barb is not there and what plays is the bow unwinding onto
# nothing. Settled by 0.8.
SLACK = [3.0, 4.0, 8.0, 14.0]   # the fallen-open prods, degrees forward per link
LUNGE = 14.0
def strike_load(t):
    ks = [(0.0, 1.0), (0.12, -0.95), (0.3, 0.34), (0.47, -0.14), (0.64, 0.0), (1.0, 0.0)]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1: return lerp(v0, v1, smooth(t0, t1, t))
    return 0.0
def strike_pose(t):
    L = strike_load(t)
    kick = math.sin(math.pi * smooth(0.02, 0.4, t))
    settle = smooth(0.35, 0.8, t)
    pose = {"body": (lerp(-BRACE_BACK, 0.0, smooth(0.1, 0.62, t)) - 3.6 * kick, 0.0, 2.5 * math.sin(2 * math.pi * smooth(0.05, 0.6, t)) * (1 - settle))}
    pose["head"] = -6.0 * kick + 4.0 * settle
    prods(pose, L, [v * settle for v in SLACK])
    for sd, s in SIDES:
        chain_set(pose, f"palp_{sd}", [s * (34.0 * max(L, 0.0) - 20.0 * kick + 10.0 * settle), s * (20.0 * max(L, 0.0) - 16.0 * kick + 14.0 * settle)])
    fly = smooth(0.0, 0.16, t)
    barb_slide(pose, lerp(-DRAW, LUNGE, fly) + 1.6 * math.sin(math.pi * smooth(0.12, 0.45, t)))
    feet = {}
    for leg, (hip, (fx, fy), *_) in LEGS.items():
        s = 1 if leg.endswith("_d") else -1
        out = lerp(BRACE_OUT, 1.2, smooth(0.2, 0.8, t))
        back = -1.2 * (1 - smooth(0.0, 0.3, t)) - 1.6 * kick * (1 - smooth(0.3, 0.7, t))
        feet[leg] = (fx + back, fy + s * out)
    return plant(pose, feet)
def strike_swell(t): return (1.12 - 0.12 * smooth(0.0, 0.2, t), 1.5 - 0.2 * smooth(0.1, 0.5, t))

# ============================================================== fuse
# Landed, and filling: four pumps, each leaving the sac bigger than the last
# let it settle back to — a ratchet, pressure going in — peaking on the last
# baked frame at three quarters again its own size. The seam between the plates
# opens on every intake and the core runs ahead of the sac, dimming as it
# draws and coming back brighter. The barb shudders harder as it fills.
def keyed(ks, t):
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1: return lerp(v0, v1, smooth(t0, t1, t))
    return ks[-1][1]
FUSE_SAC = [(0.0, 1.0), (0.1, 1.2), (0.19, 1.1), (0.31, 1.4), (0.4, 1.28), (0.52, 1.6), (0.61, 1.46), (0.74, 1.82), (0.88, 1.94), (1.0, 1.94)]
FUSE_CORE = [(0.0, 1.3), (0.08, 1.6), (0.17, 1.38), (0.28, 1.9), (0.38, 1.62), (0.49, 2.2), (0.59, 1.9), (0.71, 2.5), (0.86, 2.7), (1.0, 2.7)]
FUSE_DIM = [(0.0, 1.0), (0.1, 0.72), (0.19, 1.0), (0.31, 0.68), (0.4, 1.0), (0.52, 0.64), (0.61, 1.0), (0.74, 0.6), (0.86, 1.0), (1.0, 1.0)]
def fuse_shake(t): return (0.25 + 0.9 * smooth(0.0, 0.85, t)) * (1 - smooth(0.9, 0.95, t))
def fuse_pose(t):
    a = fuse_shake(t)
    pose = {"body": (0.0, 0.0, 0.0)}
    pose["barb"] = 2.2 * a * math.sin(2 * math.pi * 7.0 * t)
    barb_slide(pose, 0.8 * a * math.sin(2 * math.pi * 9.0 * t + 1.0))
    return plant(pose, rest_feet())
def fuse_swell(t): return (keyed(FUSE_SAC, t), keyed(FUSE_CORE, t))

# ============================================================== death
# The pair goes together, still coupled. A spasm first — the prods snatch back
# as if to draw and the core flares — then the load comes off by unbending:
# each limb straightens and swings wide rather than throwing, the legs curl in
# under the stock, the head turns aside, the sac slumps and the core drains out
# of the seam where it lay. The organs flare and go out. Still from 0.85.
UNBEND = [22.0, -6.0, -12.0, -22.0]  # straightens each limb and swings it forward/out
def death_parts(t): return smooth(0.0, 0.12, t), smooth(0.1, 0.5, t), smooth(0.4, 0.82, t)
def death_pose(t):
    a, rel, settle = death_parts(t)
    jolt = math.sin(math.pi * smooth(0.0, 0.3, t))
    pose = {"body": (1.0 * jolt - 1.2 * settle, 0.4 * settle, -3.0 * jolt + 7.0 * settle)}
    pose["head"] = 6.0 * jolt - 16.0 * settle
    prods(pose, 0.55 * a * (1 - rel), [u * rel + 5.0 * settle * (i + 1) / N_PROD for i, u in enumerate(UNBEND)])
    for sd, s in SIDES:
        chain_set(pose, f"palp_{sd}", [s * (30.0 * a * (1 - rel) + 40.0 * settle), s * 30.0 * settle])
    pose["barb"] = 9.0 * settle
    barb_slide(pose, -2.0 * a * (1 - rel) - 1.6 * settle)
    feet = {}
    for leg, (hip, foot, lf, lt, ls) in LEGS.items():
        sgn = 1 if leg.endswith("_d") else -1
        bx, by = foot
        splay = (bx + (bx - hip[0]) * 0.1, by + sgn * 1.2)
        curled = (hip[0] + (bx - hip[0]) * 0.4 + (1.4 if leg[0] == "f" else -1.0), hip[1] + (by - hip[1]) * 0.5)
        p = (lerp(bx, splay[0], a), lerp(by, splay[1], a))
        feet[leg] = (lerp(p[0], curled[0], settle), lerp(p[1], curled[1], settle))
    return plant(pose, feet)
def death_swell(t):
    a, rel, settle = death_parts(t)
    return (1.0 + 0.1 * a * (1 - rel) - 0.16 * settle, 1.0 + 0.6 * a * (1 - rel) - 0.6 * settle)

# ============================================================== clips
STILL = {"barb_core", "barb_organ", "organ", "eye_u", "eye_d"} | {f"leg_{l}_knee" for l in LEGS}
def organ_pulse(ph, amt=0.1): return lambda t: 1.0 + amt * cyc(t, ph)
TS_DEATH = [0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.24, 0.28, 0.32, 0.36, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]

animations = {}
animations["walk"] = {
    "description": "Carrying it into range. Six legs on an alternating tripod, each foot planted and pushed back under the stock then swung forward on an outward arc, the stock yawing to the pushing side and surging on each push. Over it, once a loop, the pair breathes against its own tension: both prod-limbs bend back from the root out — the bend arriving at the tips last — and the barb rides the draw a little way back down its groove, its sac and core swelling with it; then both ease forward again. A loaded bow is never slack. The palps work, and the two organs pulse out of phase, because they are two animals.",
    "duration": 0.7,
    "tracks": tracks(walk_pose, keyset(28), walk_swell,
                     {"organ": organ_pulse(0.1), "barb_organ": organ_pulse(0.6)}, still=STILL),
}
animations["fuse"] = {
    "description": "Landed, and filling. Four pumps, each leaving the sac bigger than the last let it settle back to — a ratchet rather than a pulse, pressure going in rather than a light blinking — peaking at three quarters again its own size by 0.88 and held there, because baked sheets never draw t = 1 and the frame after the last is the blast. The two plates are carried apart faster than they grow, so the lit seam down its back opens on every intake; the core runs ahead of the sac the whole way, dimming as it draws and coming back brighter. The point is pushed out as the sac swallows its root, and the barb shudders harder the fuller it gets. Its duration is the game's fuse: feelers stretches playback to the jittered `fuseTime`. Only ever baked under `planted`.",
    "duration": 0.45,
    "tracks": tracks(fuse_pose, keyset(30), fuse_swell,
                     {"barb_organ": lambda t: 1.0 + 0.18 * keyed(FUSE_SAC, t) - 0.18 + 0.1 * math.sin(2 * math.pi * 4 * t)},
                     [("barb_core", "opacity", lambda t: keyed(FUSE_DIM, t))], still=STILL),
}
animations["coil"] = {
    "description": "The windup, played once and stretched by the game to the telegraph (`windup` 0.75s), held on its last frame because the release is the throw. The barb hauls back down the groove — near half its length, until its sac hangs off the end of the stock — while both prod-limbs bend back under the load from the root out, the tips drawn back and in, and its core swells and brightens: the load is the tell, drawn, where the game used to flash the sprite yellow. All six feet dig in and the stance opens wider while the stock settles back against the draw; the palps fold. Wound rather than eased: a fast first draw, a slow creep against the load, a give, a last snatch, a tremble — and still from 0.88.",
    "duration": 0.55,
    "tracks": tracks(coil_pose, keyset(33), coil_swell,
                     {"organ": lambda t: 1.0 + 0.16 * coil_load(t), "barb_organ": lambda t: 1.0 + 0.22 * coil_load(t)}, still=STILL),
}
animations["strike"] = {
    "description": "The release, opening exactly on the coil's held pose. The prod-limbs unwind through rest and past it — tips thrown forward — rebound, and settle fallen open past rest, slack; the stock kicks back on the recoil with its feet slipping, and the head snaps. The barb does not come back: it has left the string, lunges a full length forward and holds there. Baked from `spent` (`e_charger_spent`), where the barb is not drawn and what plays is a bow unwinding onto nothing; settled by 0.8, so the husk the game leaves fading is the bow lying open.",
    "duration": 0.3,
    "tracks": tracks(strike_pose, keyset(24), strike_swell,
                     {"organ": lambda t: 1.16 - 0.3 * smooth(0.05, 0.6, t), "barb_organ": lambda t: 1.22 - 0.12 * smooth(0.1, 0.5, t)}, still=STILL),
}
animations["death"] = {
    "description": "The two animals go together, still coupled, and what you see is the load coming off. A spasm — the prods snatch back as if to draw, the core flares — and then each limb unbends, straightening and swinging wide rather than throwing; the legs curl in under the stock, the head turns aside, the barb slumps askew in its groove with its plates closing and its core draining out of the seam; both organs flare and go out. Still from 0.85.",
    "duration": 0.46,
    "tracks": tracks(death_pose, TS_DEATH, death_swell,
                     {"organ": lambda t: 1.0 + 0.6 * math.sin(math.pi * smooth(0.0, 0.3, t)) - 0.5 * smooth(0.3, 0.82, t),
                      "barb_organ": lambda t: 1.0 + 0.5 * math.sin(math.pi * smooth(0.05, 0.35, t)) - 0.5 * smooth(0.35, 0.82, t)},
                     [("organ", "opacity", lambda t: 1.0 - smooth(0.3, 0.84, t)),
                      ("barb_organ", "opacity", lambda t: 1.0 - smooth(0.34, 0.84, t)),
                      ("barb_core", "opacity", lambda t: 1.0 - 0.95 * smooth(0.2, 0.8, t))], still=STILL),
}

# ============================================================== variants
# The barb alone is recentred on its own middle: the canvas is sized for the
# pair, and left where it lay in the groove it would fly and land a third of a
# body off its own hitbox.
def extent(pid):
    p = BASE[pid]
    xs = [p["at"][0] + x for x, _ in p["shape"]["points"]] if p.get("shape", {}).get("kind") == "poly" else [p["at"][0]]
    return min(xs), max(xs)
lo = min(extent("barb_sac")[0], extent("barb_point")[0])
hi = max(extent("barb_sac")[1], extent("barb_point")[1])
RECENTRE = r2(-(lo + hi) / 2)
def shifted(pid):
    p = dict(BASE[pid]); p["at"] = [r2(p["at"][0] + RECENTRE), p["at"][1]]
    return p

variants = {
    "loosed": {
        "description": "The barb alone, in flight — a static texture (`e_charger_loosed`) the game swaps the sprite to on the release and lobs on an arc. Everything the bow was is gone from it, because the bow did not come; that is the whole point of there being two animals. The core is still swollen from the draw. Recentred on its own middle: the canvas is sized for a pair, and left where it lay in the groove it would fly a third of a body off its own hitbox.",
        "animations": [],
        "remove": BOW_PARTS,
        "set": dict([(f"{pid}.at", shifted(pid)["at"]) for pid in BARB_PARTS] + [("barb_core.scale", 1.3)]),
    },
    "planted": {
        "description": "The barb after it has landed and before it goes off: the same parts it flew as, recentred the same way, lying in a scorch it put there arriving — a dark burn with a pale ring of ash round it, so it reads on the Plains' dark floor. Plays `fuse` (`e_charger_planted`), stretched to the fuse it drew; the half-second it holds this is the half-second the player has to not be here. The barb's parts are re-added over the scorch (variant `add` draws on top), so it lies in the burn rather than under it.",
        "animations": ["fuse"],
        "remove": BOW_PARTS + BARB_PARTS,
        "add": [
            {"id": "scorch_ash", "at": [0.0, 0.8], "shape": ell(19.0, 12.0), "fill": "$husk.dark2@ghost"},
            {"id": "scorch", "at": [0.0, 0.8], "shape": ell(16.5, 10.0), "fill": "$dead@heavy"},
            {"id": "scorch_burn", "at": [-1.0, 0.5], "shape": ell(12.0, 7.0), "fill": "$rust@soft"},
            {"id": "scorch_core", "at": [-2.0, 0.3], "shape": ell(7.5, 4.6), "fill": "$dead@soft"},
        ] + [shifted(pid) for pid in BARB_PARTS],
    },
    "spent": {
        "description": "The bow after it has let go, left lying where it loosed — the husk the game drops at the release, which plays `strike` once (`e_charger_spent`) and fades. Its first frame is the coil's held pose with no barb in the groove; what plays is the bow unwinding onto nothing and settling with its prod-limbs fallen open past rest, the stock drained and the scent organ down to `faint`. Drawn so the field keeps a record of where a volley came from.",
        "animations": ["strike"],
        "remove": BARB_PARTS,
        "set": {"stock.fill": "$carapace", "groove.fill": "$dead", "stock_shine.fill": "$carapace.light", "organ.variant": "faint"},
    },
}

# ============================================================== document
DESCRIPTION = (
    "Two animals that are useless apart. Seen from above, facing +x, mirrored by the game. The bow-caste is a crossbow laid flat and made an "
    "insect: a long lavender stock running the way it travels — banded abdomen behind, shoulders swelling where the prod mounts — a pale head "
    "at the leading end with two palps and its own lit organ, six legs, and two pale prod-limbs thrown out sideways from knuckles on the "
    "shoulders, sweeping a little back and kicked forward at the tip the way a bow limb recurves and a beetle carries its antennae. It has "
    "nothing to hurt anything with. The barb-caste lies in the groove down the middle of that stock: a dark point laid under a plated sac, rear "
    "buried, the barb's organ on its neck ahead of the core, and the core — gold, the one loud thing on the sprite — showing down the lit seam "
    "between its two green plates. One winds, the other lands, and both are spent in the same second, which is why the hive only ever sends them "
    "in volleys. Two lit organs on one sprite is the tell that it is two creatures. "
    "There is no string: the load is drawn in the body. The windup (`coil`) hauls the barb back down the groove while both limbs bend back under "
    "it and the core swells; on the release the game swaps the sprite to `loosed` (the barb alone, in flight) and drops the bow as `spent`, "
    "unwinding onto nothing; the barb lands as `planted` and fills (`fuse`) until it goes off. Nothing points down the line it is about to "
    "take: the sprite only ever flips. Built on a skeleton (scripts/charger.py): legs solved to planted feet, each prod-limb a four-bone chain, "
    "the barb one bone sliding in the groove with a sac that swells about its centre. Gameplay radius 16. The `death` clip is the pair dying "
    "still coupled — the limbs unbending rather than releasing, the barb's core draining where it lay."
)

doc = {
    "id": "ss.enemy.charger",
    "name": "Bow and barb",
    "description": DESCRIPTION,
    "tags": ["enemy", "duo"],
    "size": [72, 60],
    "meta": {"radius": 16},
    "parts": RIG.parts,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-charger.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks, recentre {RECENTRE}")
