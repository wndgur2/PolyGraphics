"""The Matriarch — the burrow's third boss: a queen who is mostly a brood sac.

    python3 scripts/matriarch.py      # rewrites apps/ss/assets/ss-enemy-matriarch.json

feelers runs her as a slow walker (76) that never attacks: every 7s she plays
`lay` and a clutch of eggs drops out of the seam under her sac on the clip's
beat (EnemySystem `LAY_CUE` 0.62, at `LAY_SEAM` (6.5, 34.5) from her middle,
facing +x), and every 8s she plays `command` — a roar, with pale rings thrown
out of her mouth 0.65 of her radius ahead of her middle — and her young come
at a rush. `swell` is the idle she plays the rest of the time, walking or not.
`enraged` from two thirds of her health, `final` from one third.

She is drawn side-on, facing +x, feet on the ground under her, the way a
termite queen is: a small amber head and thorax at the front with the six legs
under them, and behind them the abdomen, swollen into a brood chamber many
times their size. The chamber is built the way the old drawing built it: dark
plates over a stretched skin, so every gap between them is pressure showing,
pink where the skin is thinnest; a crown of uneven spines standing off the
plates; and the brood seen through the skin of her flank, seven pale eggs
(the same shell, glow and grub as `ss.enemy.ovum`, which is what they become)
with a light at the middle of them. The skin is a dull rose (`$mauve`) — her
family, earthier — and the bright pink is kept for what is alive in her: the
seams, the eggs' glow, the core and the organ.

On the rig (scripts/rig.py): the body is a root the legs are planted from by
two-bone IK; the abdomen is one bone hinged at the waist that pitches, and
everything riding it is placed by the chamber's own swell — the skin scales
about the chamber's centre, the plates are carried out with it and fanned
apart so the seams open, and the spines stand on the plates and flex from
their roots in a wave down the crown. Eggs drift on their own orbits inside;
three nodules — eggs pressing the skin from inside — slide along the belly.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, wrap, keyset, ik2 as ik, compose, invert_apply,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 120×112, origin at the centre, +x forward, +y down; the ground is
# near y = 37.
RIG = Rig()
B = RIG.bones
bone = RIG.bone

WAIST = (13.0, 3.0)
C = (-11.0, -2.0)           # the chamber's centre
RX, RY = 33.0, 29.0         # its half-width and half-height at rest

bone("body", None, WAIST, 0.0)
bone("abd", "body", WAIST, D(math.atan2(C[1] - WAIST[1], C[0] - WAIST[0])), math.hypot(WAIST[0] - C[0], WAIST[1] - C[1]))
bone("thorax", "body", (14.0, 4.0), -8.0, 12.0)
bone("head", "thorax", (26.0, 2.5), 14.0, 12.0)
bone("mand_u", "head", (39.4, 6.2), 2.0, 7.0)
bone("mand_d", "head", (38.6, 10.4), 26.0, 6.5)
N_ANT = 3
RIG.chain("ant_n", "head", (35.5, 0.6), [(5.0, -64.0), (4.6, -40.0), (4.2, -16.0)])
RIG.chain("ant_f", "head", (33.6, 0.2), [(4.6, -80.0), (4.4, -56.0), (4.0, -34.0)])

# Legs, side-on: (hip, foot, femur, tibia, tarsus). The near three are drawn
# over the body, the far three behind it, a little up and forward.
LEG_N = {
    "f": ((24.0, 11.0), (33.5, 33.5), 10.5, 14.5, 4.4),
    "m": ((19.0, 12.5), (16.5, 34.5), 10.0, 13.5, 4.2),
    "b": ((13.5, 12.5), (-6.0, 33.0), 11.0, 15.0, 4.4),
}
LEGS = {}
for n, (hip, foot, lf, lt, ls) in LEG_N.items():
    LEGS[f"{n}_n"] = (hip, foot, lf, lt, ls)
    LEGS[f"{n}_f"] = ((hip[0] + 1.5, hip[1] - 2.0), (foot[0] + 6.0, foot[1] - 2.2), lf, lt, ls)

def bend_of(leg):
    """The knee stands up off the line from hip to foot, as an insect's does side-on."""
    hip, foot, lf, lt, _ = LEGS[leg]
    best, pick = None, 1
    for b in (1, -1):
        h1, _ = ik(hip, foot, lf, lt, b)
        ky = hip[1] + lf * math.sin(R(h1))
        if best is None or ky < best: best, pick = ky, b
    return pick
BEND = {leg: bend_of(leg) for leg in LEGS}
def tarsus_heading(leg, tibia_h):
    """The foot turns off the tibia toward the way the leg reaches: forward for the front two pairs, back for the rear."""
    return tibia_h + (38.0 if leg[0] == "b" else -38.0)

for leg, (hip, foot, lf, lt, ls) in LEGS.items():
    hf, ht = ik(hip, foot, lf, lt, BEND[leg])
    bone(f"{leg}_femur", "body", hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", B[f"{leg}_femur"].end(), ht, lt)
    bone(f"{leg}_tarsus", f"{leg}_tibia", B[f"{leg}_tibia"].end(), tarsus_heading(leg, ht), ls)

RIG.seal()
solve = RIG.solve
put = RIG.put

# ============================================================== the chamber's geometry
def rim(th, k=1.0, s=1.0):
    """The point of the chamber's rim at parametric angle `th` (deg; -90 is the top), at swell k, `s` of the way out."""
    return (C[0] + RX * k * s * math.cos(R(th)), C[1] + RY * k * s * math.sin(R(th)))
def normal(th):
    """The rim's outward normal at `th`, as a heading."""
    return D(math.atan2(RX * math.sin(R(th)), RY * math.cos(R(th))))
def local(pts, c): return [(x - c[0], y - c[1]) for x, y in pts]
def band(th0, th1, s0, s1, n=10):
    """The piece of the rim between angles th0..th1, from `s0` to `s1` of the way out (world points)."""
    ths = [th0 + (th1 - th0) * i / n for i in range(n + 1)]
    return [rim(t, 1.0, s1) for t in ths] + [rim(t, 1.0, s0) for t in reversed(ths)]

# The plates: six across the back of the chamber, from the rear to just behind
# the thorax, over a pink band that shows between them.
PLATE_TH = [-166.0, -141.0, -116.0, -91.0, -66.0, -42.0]
PLATE_HALF = [10.6, 11.0, 11.2, 11.2, 11.0, 10.0]
PLATE_MID = sum(PLATE_TH) / len(PLATE_TH)
# The crown: a spine off every plate, uneven, and three short ones between.
SPINES = [  # (id, angle, length, base half-width)
    ("spine_0", -170.0, 11.0, 3.3), ("spine_1", -151.0, 9.0, 2.8), ("spine_2", -139.0, 15.5, 3.8),
    ("spine_3", -114.0, 13.0, 3.6), ("spine_4", -101.0, 8.5, 2.6), ("spine_5", -89.0, 16.0, 3.9),
    ("spine_6", -64.0, 13.5, 3.6), ("spine_7", -52.0, 8.0, 2.6), ("spine_8", -41.0, 11.0, 3.2),
]
# The brood: seven eggs in the flank window (centre, half-length, tilt).
EGGS = [
    ("brood_0", (-22.5, 3.0), 5.5, -30.0), ("brood_1", (-13.5, -3.0), 5.0, 18.0),
    ("brood_2", (-3.5, 1.5), 5.6, -12.0), ("brood_3", (4.5, 11.0), 4.6, 24.0),
    ("brood_4", (-8.5, 13.0), 5.4, -40.0), ("brood_5", (-20.5, 14.0), 4.4, 10.0),
    ("brood_6", (-29.5, -2.0), 4.2, 40.0),
]
EGG_W = 0.72   # an egg's width against its length, as the Ovum's shell
NODULES = [("nodule_0", 118.0, 4.6), ("nodule_1", 142.0, 5.2), ("nodule_2", 166.0, 4.4)]
VENT_TH = 60.0       # where the laying seam is on the rim, under the chamber
VENT = rim(VENT_TH)  # ≈ (5.5, 23.1)

# ============================================================== palette
# The skin is a dull rose, the plates a greyed plum, the crown bone, the head
# amber; the bright pink is kept for the seams, the eggs' glow, the core and
# the organ. The floor under her is near black, so the body is kept light.
PAL = {
    "skin": "$mauve.light2", "belly": "$mauve", "nodule": "$mauve",
    "window": {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$pheromone.dark2"], [0.62, "$pheromone.dark2@heavy"], [1, "$pheromone.dark2@0"]]},
    "plate": "$dusk", "ridge": "$dusk.light",
    "spine": "$husk", "spine_shade": "$husk.dark",
    "leg_n": ["$carapace.light", "$carapace", "$carapace", "$mauve.dark"], "leg_f": ["$carapace", "$carapace.dark", "$carapace.dark", "$carapace"],
    "thorax": "$chitin.dark2", "pronotum": "$chitin.dark", "head": "$chitin.dark", "brow": "$husk.dark",
}
import json as _json
PAL.update(_json.loads(os.environ.get("MATRIARCH_PAL", "{}")))

# ============================================================== parts
HAIR_WINE = {"color": "$pheromone.dark2", "width": "hair"}

# ---- far legs and far antenna, behind everything
def leg_parts(leg, femur, tibia, tarsus, knee, stroke):
    lf, lt, ls = LEGS[leg][2], LEGS[leg][3], LEGS[leg][4]
    at, a = RIG.on_bone(f"{leg}_tarsus"); put(f"leg_{leg}_tarsus", f"{leg}_tarsus", at, a, bar(ls, 2.3, 1.2, 0.7), tarsus, stroke)
    at, a = RIG.on_bone(f"{leg}_tibia"); put(f"leg_{leg}_tibia", f"{leg}_tibia", at, a, bar(lt, 4.2, 2.4), tibia, stroke)
    at, a = RIG.on_bone(f"{leg}_femur"); put(f"leg_{leg}_femur", f"{leg}_femur", at, a, bar(lf, 6.0, 4.4), femur, stroke)
    at, a = RIG.on_bone(f"{leg}_tibia"); put(f"leg_{leg}_knee", f"{leg}_tibia", at, 0.0, circ(2.3), knee, stroke)

for n in ("b", "m", "f"):
    leg_parts(f"{n}_f", *PAL["leg_f"], INK_HAIR)
for i in range(N_ANT):
    nm = f"ant_f_{i}"; at, a = RIG.on_bone(nm)
    put(nm, nm, at, a, bar(B[nm].length, 1.6 - 0.25 * i, 1.3 - 0.25 * i, 0.6), "$carapace.dark", INK_HAIR)
RIG.bar_tip("feeler_tip_f", f"ant_f_{N_ANT - 1}", 1.3 - 0.25 * (N_ANT - 1), 0.6, "$carapace.dark")

# ---- nodules: eggs pressing the skin out from inside, under the skin
for nid, th, r in NODULES:
    at = rim(th, 1.0, 0.93)
    put(nid, "abd", at, normal(th), ell(r, r * 0.86), PAL["nodule"], INK_THIN)

# ---- the chamber
put("sac", "abd", C, 0.0, ell(RX, RY), PAL["skin"], INK_THIN)
# the underside in shade: the bottom of the chamber, a crescent
BELLY = [rim(t, 1.0, 1.0) for t in range(10, 181, 10)] + [(C[0] - RX * 0.8, C[1] + 6.0), (C[0] - 6.0, C[1] + RY * 0.55), (C[0] + RX * 0.7, C[1] + 8.0)]
put("belly", "abd", C, 0.0, poly(local(BELLY, C)), PAL["belly"])
# the window: the brood seen through the thinnest of her flank
WIN_C, WIN_RX, WIN_RY = (-9.0, 7.0), 23.5, 15.0
put("window", "abd", WIN_C, -8.0, ell(WIN_RX, WIN_RY), PAL["window"], {"color": "$mauve.light", "width": "hair"})
put("core", "abd", (-9.0, 6.5), 0.0, ell(15.0, 10.0),
    {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$pheromone.light@heavy"], [0.45, "$pheromone@soft"], [1, "$pheromone.dark2@0"]]})
def egg_pt(c, tilt, u, v):
    """A point `u` along the egg and `v` across it from its centre `c`, the egg turned `tilt`."""
    return (c[0] + u * math.cos(R(tilt)) - v * math.sin(R(tilt)), c[1] + u * math.sin(R(tilt)) + v * math.cos(R(tilt)))
for eid, c, L, tilt in EGGS:
    # the Ovum's shell, its pink showing through the lower half, and the grub curled in it
    put(eid, "abd", c, tilt, ell(L, L * EGG_W), "$ochre.light2", HAIR_WINE)
    put(f"{eid}_glow", "abd", egg_pt(c, tilt, -0.6, 0.9), tilt, ell(L * 0.7, L * EGG_W * 0.62), "$pheromone.light@heavy")
    put(f"{eid}_grub", "abd", egg_pt(c, tilt, -0.3, 0.5), tilt - 20.0, {"kind": "ring", "r": r2(L * 0.36), "width": r2(L * 0.24), "from": 40, "to": 290}, "$pheromone.dark")
# the seam band: the skin between the plates, thin enough to show pink
put("seams", "abd", C, 0.0, poly(local(band(-178.0, -31.0, 0.66, 0.995, 24), C)), "$pheromone", {"color": "$pheromone.dark", "width": "hair"})
PLATES = []
for i, (th, hw) in enumerate(zip(PLATE_TH, PLATE_HALF)):
    pc = rim(th, 1.0, 0.83)
    pts = band(th - hw, th + hw, 0.68, 1.0, 8)
    put(f"plate_{i}", "abd", pc, 0.0, poly(local(pts, pc)), PAL["plate"], INK_HAIR)
    ridge = band(th - hw * 0.8, th + hw * 0.8, 0.9, 0.975, 6)
    put(f"plate_{i}_ridge", "abd", pc, 0.0, poly(local(ridge, pc)), PAL["ridge"])
    PLATES.append((f"plate_{i}", th))
# the laying seam, closed at rest
put("vent", "abd", VENT, normal(VENT_TH) + 90.0, ell(3.4, 0.9), "$pheromone.dark", {"color": "$ink", "width": "hair"})
put("gloss", "abd", (-24.0, 1.0), -24.0, ell(7.0, 2.4), "$white@0.2")

# ---- the crown
def spine_shape(L, w):
    return poly([(-0.6, -w), (L * 0.42, -w * 0.62), (L, -0.35), (L + 0.6, 0.0), (L, 0.35), (L * 0.42, w * 0.62), (-0.6, w)])
for sid, th, L, w in SPINES:
    root = rim(th, 1.0, 0.95)
    h = normal(th) - 12.0  # raked back a little, the way a crown lies with the grain
    put(sid, "abd", root, h, spine_shape(L, w), PAL["spine"], INK_HAIR)
    put(f"{sid}_shade", "abd", root, h, poly([(L * 0.1, w * 0.72), (L * 0.42, w * 0.5), (L * 0.92, 0.25), (L * 0.5, w * 0.12)]), PAL["spine_shade"])

RIG.use("organ", "abd", rim(-80.0, 1.0, 0.8), "ss.lib.organ", scale=0.95)

# ---- thorax and head
put("thorax", "thorax", (19.5, 5.0), -8.0, ell(10.0, 8.6), PAL["thorax"], INK_THIN)
put("pronotum", "thorax", (19.0, 1.2), -12.0, poly([(-8.0, 1.2), (-6.4, -3.2), (-1.0, -5.0), (5.0, -4.0), (8.6, -0.8), (7.4, 1.6), (0.0, 0.2), (-5.0, 1.8)]), PAL["pronotum"], INK_HAIR)
put("neck", "thorax", (27.5, 5.4), 10.0, ell(3.6, 4.6), "$chitin.dark2", INK_HAIR)
put("head", "head", (33.5, 6.6), 12.0, ell(7.6, 6.6), PAL["head"], INK_THIN)
put("brow", "head", (33.0, 3.0), 10.0, poly([(-6.0, 1.0), (-4.6, -2.2), (0.0, -3.4), (4.8, -2.4), (7.2, 0.2), (5.8, 1.2), (0.0, -0.6), (-4.0, 1.8)]), PAL["brow"], INK_HAIR)
put("eye_b", "head", (37.8, 3.4), 0.0, circ(1.2), "$ink")
put("eye_a", "head", (35.6, 5.0), 0.0, ell(2.2, 1.9), "$ink")
put("maw", "head", (39.4, 8.6), 12.0, ell(2.4, 2.0), "$ink")
MAND = [(-0.8, -1.8), (2.6, -2.4), (6.0, -1.2), (7.6, 0.8), (5.4, 0.4), (3.6, 1.2), (1.8, 0.6), (-0.8, 1.6)]
at, a = RIG.on_bone("mand_d"); put("mand_dn", "mand_d", at, a, poly([(x, -y) for x, y in MAND]), "$husk.dark", INK_HAIR)
at, a = RIG.on_bone("mand_u"); put("mand_up", "mand_u", at, a, poly(MAND), "$husk", INK_HAIR)
for i in range(N_ANT):
    nm = f"ant_n_{i}"; at, a = RIG.on_bone(nm)
    put(nm, nm, at, a, bar(B[nm].length, 1.9 - 0.3 * i, 1.6 - 0.3 * i, 0.6), "$carapace", INK_HAIR)
RIG.bar_tip("feeler_tip_n", f"ant_n_{N_ANT - 1}", 1.6 - 0.3 * (N_ANT - 1), 0.6, "$carapace")

# ---- near legs, over the body
for n in ("b", "m", "f"):
    leg_parts(f"{n}_n", *PAL["leg_n"], INK_HAIR)

RIG.check()
BASE = {p["id"]: p for p in RIG.parts}

# ============================================================== groups on the chamber
# Everything riding `abd` belongs to a group that the chamber's state moves as
# one: a group has an origin (a rest world point) and, at time t, a new origin,
# a turn and a scale about it. `chamber(t)` returns the state the groups read.
SKIN = {"sac", "belly", "window", "core", "seams", "gloss"}
GROUP = {}
ORIGIN = {}
for pid in SKIN: GROUP[pid] = "skin"
ORIGIN["skin"] = C
for i, (pid, th) in enumerate(PLATES):
    GROUP[pid] = GROUP[f"{pid}_ridge"] = pid
    ORIGIN[pid] = rim(th, 1.0, 0.83)
for sid, th, L, w in SPINES:
    GROUP[sid] = GROUP[f"{sid}_shade"] = sid
    ORIGIN[sid] = rim(th, 1.0, 0.95)
for eid, c, L, tilt in EGGS:
    for suf in ("", "_glow", "_grub"): GROUP[eid + suf] = eid
    ORIGIN[eid] = c
for nid, th, r in NODULES:
    GROUP[nid] = nid; ORIGIN[nid] = rim(th, 1.0, 0.93)
GROUP["organ"] = "organ"; ORIGIN["organ"] = rim(-80.0, 1.0, 0.8)
GROUP["vent"] = "vent"; ORIGIN["vent"] = VENT
RIM_TH = {pid: th for pid, th in PLATES}
RIM_TH.update({sid: th for sid, th, *_ in SPINES})
RIM_TH["organ"] = -80.0
RIM_S = {pid: 0.83 for pid, _ in PLATES}
RIM_S.update({sid: 0.95 for sid, *_ in SPINES})
RIM_S["organ"] = 0.8

class Chamber:
    """What the chamber is doing at one instant."""
    def __init__(self, k=1.0, fan=0.0, wave=None, egg=None, nod=None, flex=None, vent=(0.0, 0.0)):
        self.k = k            # swell of the skin about its centre
        self.fan = fan        # how far the plates fan apart (0 = rest; 1 = the seams open about 5 degrees each)
        self.wave = wave or (lambda th: 0.0)   # extra radial push along the rim, by angle (a ripple)
        self.egg = egg or {}  # egg id -> (dx, dy, drot, dscale)
        self.nod = nod or {}  # nodule id -> (dth, scale)
        self.flex = flex or {}  # spine id -> turn about its root
        self.vent = vent      # (open 0..1, drift down)

def group_xf(g, ch):
    """(new origin, turn, scale) of group `g` in rest-world coordinates."""
    ox, oy = ORIGIN[g]
    if g == "skin":
        return (ox, oy), 0.0, ch.k
    if g in RIM_TH:
        th = RIM_TH[g]
        th2 = PLATE_MID + (th - PLATE_MID) * (1.0 + 0.2 * ch.fan)
        push = 1.0 + ch.wave(th2)
        p = rim(th2, ch.k * push, RIM_S[g])
        turn = th2 - th
        if g.startswith("spine"): turn += ch.flex.get(g, 0.0)
        return p, turn, (ch.k if g.startswith("plate") else 1.0)
    if g.startswith("brood"):
        dx, dy, dr, ds = ch.egg.get(g, (0.0, 0.0, 0.0, 1.0))
        return (C[0] + (ox - C[0]) * ch.k + dx, C[1] + (oy - C[1]) * ch.k + dy), dr, ds
    if g.startswith("nodule"):
        th0 = dict((n, t) for n, t, _ in NODULES)[g]
        dth, sc = ch.nod.get(g, (0.0, 1.0))
        th = th0 + dth
        return rim(th, ch.k * (1.0 + ch.wave(th)), 0.93), th - th0, sc
    if g == "vent":
        op, down = ch.vent
        return (C[0] + (ox - C[0]) * ch.k, C[1] + (oy - C[1]) * ch.k + down), 0.0, 1.0
    raise KeyError(g)

def posed(pose, ch, extra_scale=None, t=0.0):
    """Every part's world (x, y, rot, scale) under `pose` and chamber state `ch`."""
    world = solve(pose)
    out = {}
    for p in RIG.parts:
        pid = p["id"]; bn = RIG.attach[pid]
        at, rot = tuple(p["at"]), p.get("rot", 0.0)
        sc = 1.0
        if bn == "abd":
            g = GROUP[pid]
            o = ORIGIN[g]
            (nx, ny), turn, gs = group_xf(g, ch)
            dx, dy = at[0] - o[0], at[1] - o[1]
            c_, s_ = math.cos(R(turn)), math.sin(R(turn))
            at = (nx + gs * (dx * c_ - dy * s_), ny + gs * (dx * s_ + dy * c_))
            rot = rot + turn
            sc = gs
            if pid == "vent": sc = 1.0
        lx, ly, la = invert_apply(RIG.rest[bn], at, rot)
        x, y, a = compose(world[bn], (lx, ly, la))
        if extra_scale and pid in extra_scale: sc *= extra_scale[pid](t)
        out[pid] = (x, y, a, sc)
    return out

REST = posed({}, Chamber())
ROUND = {"sac", "core", "organ", "knee", "eye_a", "eye_b"}
def is_round(pid): return pid in ROUND or pid in RIG.tips or pid.endswith("_knee") or pid.startswith("eye")

def tracks(state_at, ts, scales=None, extra=None):
    """Solve `state_at(t) -> (pose, chamber)` at every t to x/y/rot/scale tracks, plus `extra` (part, prop, fn)."""
    series = {p["id"]: ([], [], [], []) for p in RIG.parts}
    for t in ts:
        pose, ch = state_at(t)
        now = posed(pose, ch, scales, t)
        for pid, (x, y, a, sc) in now.items():
            bx, by, ba, bs = REST[pid]
            for arr, v in zip(series[pid], (x - bx, y - by, wrap(a - ba), sc / bs)):
                arr.append(v)
    out = []
    for p in RIG.parts:
        pid = p["id"]
        xs, ys, rs, ss = series[pid]
        for prop, vs, rv in (("x", xs, 0.0), ("y", ys, 0.0), ("rot", rs, 0.0), ("scale", ss, 1.0)):
            if prop == "rot" and is_round(pid): continue
            if max(abs(v - rv) for v in vs) > {"scale": 0.004, "rot": 0.2}.get(prop, 0.05):
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

FEET = {leg: v[1] for leg, v in LEGS.items()}
SPINE_ORDER = [sid for sid, *_ in SPINES]            # rear to front
SPINE_FRONT = list(reversed(SPINE_ORDER))            # front to rear

def ripple(amp, t, lam=0.55):
    """A bulge running round the rim from the rear toward the vent: radial push by angle."""
    def f(th):
        u = ((th + 180.0) % 360.0) / 360.0
        return amp * max(0.0, math.sin(2 * math.pi * (u / lam - t))) ** 3
    return f

def egg_orbits(t, amp=1.0):
    out = {}
    for i, (eid, c, L, tilt) in enumerate(EGGS):
        ph = i * 0.37
        out[eid] = (amp * 1.8 * math.cos(2 * math.pi * (t + ph)), amp * 1.4 * math.sin(2 * math.pi * (t + ph)),
                    amp * 12.0 * math.sin(2 * math.pi * (t + ph * 1.7)), 1.0)
    return out

# ============================================================== swell (idle, 2.8s)
# The chamber breathes once a cycle: it fills (the skin swells, the plates fan
# and the seams open pink, the crown rises in a wave from the front to the
# rear, the abdomen lifts at the tail) and lets go. The weight comes onto the
# legs a beat late — the body sinks and the knees give. Inside, the eggs drift
# on their orbits and the nodules roll along the belly, a ripple running
# toward the vent. The head nods, the jaws work twice, the antennae sweep, and
# each leg treads once in turn.
def breath(t): return math.sin(2 * math.pi * t)

def tread(t, ph, lift=3.2, width=0.16):
    u = ((t - ph) % 1.0) / width
    return lift * math.sin(math.pi * u) if u < 1.0 else 0.0

TREAD_PH = {"f_n": 0.05, "m_f": 0.22, "b_n": 0.38, "f_f": 0.55, "m_n": 0.7, "b_f": 0.86}

def swell_state(t):
    b = breath(t)
    late = breath(t - 0.1)
    pose = {"body": (0.6 * late, 1.6 * late, -1.2 * breath(t - 0.05))}
    pose["abd"] = 7.5 * breath(t - 0.04)
    pose["thorax"] = 1.5 * breath(t - 0.12)
    pose["head"] = 7.0 * breath(t - 0.2) + 3.0 * math.sin(2 * math.pi * (3 * t))
    jaw = max(0.0, math.sin(2 * math.pi * (2 * t + 0.1)))
    pose["mand_u"] = -16.0 * jaw
    pose["mand_d"] = 18.0 * jaw
    chain_set(pose, "ant_n", [16.0 * breath(t - 0.1 - 0.06 * i) + 6.0 * math.sin(2 * math.pi * (2 * t - 0.1 * i)) for i in range(N_ANT)])
    chain_set(pose, "ant_f", [-12.0 * breath(t - 0.25 - 0.06 * i) + 5.0 * math.sin(2 * math.pi * (2 * t + 0.3 - 0.1 * i)) for i in range(N_ANT)])
    feet = {}
    for leg, (fx, fy) in FEET.items():
        lift = tread(t, TREAD_PH[leg])
        feet[leg] = (fx + 0.5 * lift, fy - lift)
    plant(pose, feet)
    flex = {sid: 19.0 * breath(t - 0.05 - 0.035 * i) for i, sid in enumerate(SPINE_FRONT)}
    nod = {}
    for j, (nid, th, r) in enumerate(NODULES):
        nod[nid] = (-16.0 * math.sin(2 * math.pi * (t - 0.12 * j)), 1.0 + 0.3 * math.sin(2 * math.pi * (t - 0.12 * j - 0.25)))
    ch = Chamber(k=1.0 + 0.075 * b, fan=1.6 * max(0.0, b), wave=ripple(0.05, t), egg=egg_orbits(t), nod=nod, flex=flex)
    return pose, ch

SWELL_SCALES = {
    "core": lambda t: 1.0 + 0.22 * breath(t - 0.05),
    "organ": lambda t: 1.0 + 0.14 * breath(t - 0.08),
}
for eid, *_ in EGGS:
    SWELL_SCALES[f"{eid}_glow"] = (lambda i: (lambda t: 1.0 + 0.2 * math.sin(2 * math.pi * (2 * t + i * 0.19))))(int(eid[-1]))
SWELL_EXTRA = [
    ("core", "opacity", lambda t: 0.8 + 0.2 * breath(t - 0.05)),
    ("seams", "opacity", lambda t: 0.8 + 0.2 * breath(t)),
]

# ============================================================== command (0.9s)
# The call. Draw in (0-0.3): the chamber pulls tight, the crown lies flat,
# the head drops and draws back, the antennae fold. Release (0.3-0.46): she
# rears, the head is thrown up and forward with the jaws gaping, the chamber
# heaves out and the seams flare, and the crown stands up in a wave from the
# front to the rear — the ring the game draws leaving her mouth. Recovery to
# 1.0: everything settles back, the crown last.
def command_parts(t):
    a = smooth(0.0, 0.3, t)
    r = smooth(0.28, 0.44, t)
    back = smooth(0.52, 1.0, t)
    return a, r, back

def command_state(t):
    a, r, back = command_parts(t)
    held = r * (1 - back)
    draw = a * (1 - r)
    pose = {"body": (-2.4 * draw + 2.6 * held, 1.6 * draw - 3.0 * held, 3.0 * draw - 8.0 * held)}
    pose["abd"] = -3.0 * draw + 7.0 * held
    pose["thorax"] = 4.0 * draw - 6.0 * held
    pose["head"] = 14.0 * draw - 26.0 * held
    gape = held + 0.2 * draw
    pose["mand_u"] = -38.0 * gape
    pose["mand_d"] = 40.0 * gape
    chain_set(pose, "ant_n", [42.0 * draw - 40.0 * held, 20.0 * draw - 18.0 * held, 10.0 * draw - 16.0 * held])
    chain_set(pose, "ant_f", [36.0 * draw - 30.0 * held, 18.0 * draw - 18.0 * held, 10.0 * draw - 10.0 * held])
    feet = dict(FEET)
    feet["f_n"] = (FEET["f_n"][0] + 2.0 * held, FEET["f_n"][1] - 3.0 * held * (1 - smooth(0.5, 0.7, t)))
    feet["f_f"] = (FEET["f_f"][0] + 2.0 * held, FEET["f_f"][1] - 2.4 * held * (1 - smooth(0.5, 0.7, t)))
    plant(pose, feet)
    flex = {}
    for i, sid in enumerate(SPINE_FRONT):
        w = smooth(0.3 + 0.025 * i, 0.44 + 0.025 * i, t) * (1 - smooth(0.6 + 0.03 * i, 0.98, t))
        flex[sid] = -18.0 * draw + 26.0 * w
    k = 1.0 - 0.06 * draw + 0.11 * held
    egg = {eid: (0.0, 0.0, 0.0, 1.0 - 0.1 * draw + 0.12 * held) for eid, *_ in EGGS}
    nod = {nid: (0.0, 1.0 - 0.4 * draw + 0.35 * held) for nid, *_ in NODULES}
    ch = Chamber(k=k, fan=-0.8 * draw + 2.6 * held, egg=egg, nod=nod, flex=flex)
    return pose, ch

def command_flare(t):
    a, r, back = command_parts(t)
    return r * (1 - back)
COMMAND_SCALES = {"core": lambda t: 1.0 - 0.2 * smooth(0, 0.3, t) * (1 - smooth(0.28, 0.44, t)) + 0.6 * command_flare(t),
                  "organ": lambda t: 1.0 + 0.4 * command_flare(t)}
for eid, *_ in EGGS:
    COMMAND_SCALES[f"{eid}_glow"] = lambda t: 1.0 + 0.35 * command_flare(t)
COMMAND_EXTRA = [("core", "opacity", lambda t: 0.8 + 0.2 * command_flare(t)),
                 ("seams", "opacity", lambda t: 0.8 + 0.2 * command_flare(t))]

# ============================================================== lay (1.2s)
# LAY_CUE is 0.62: the egg is out of the vent and at (6.5, 34.5) then, and
# the game's own egg takes over from that frame. Anticipation (0-0.28): she
# braces, the chamber fills and the egg nearest the vent, brood_3, is shifted
# down onto it. Contraction (0.28-0.62): a squeeze runs round the chamber from
# the tail toward the vent, the chamber draws in, the abdomen tips its tail
# down and forward, she squats; the vent opens and the egg is pushed through it
# and drops. Recovery (0.62-1.0): the vent closes, the chamber relaxes, the
# rest of the brood settles into the room it left, and the next egg rises into
# its place.
LAY_CUE = 0.62
SEAM_OUT = (6.5, 34.5)
def lay_parts(t):
    a = smooth(0.0, 0.28, t)
    sq = smooth(0.26, 0.6, t)
    back = smooth(0.64, 1.0, t)
    return a, sq, back

def lay_state(t):
    a, sq, back = lay_parts(t)
    brace = a * (1 - back)
    squeeze = sq * (1 - back)
    pose = {"body": (-1.0 * brace, -1.4 * a * (1 - sq) + 3.6 * squeeze, 2.0 * squeeze)}
    pose["abd"] = 4.0 * a * (1 - sq) - 7.0 * squeeze
    pose["thorax"] = -2.0 * squeeze
    pose["head"] = -6.0 * brace + 12.0 * squeeze
    pose["mand_u"] = -10.0 * squeeze
    pose["mand_d"] = 12.0 * squeeze
    chain_set(pose, "ant_n", [-14.0 * brace + 24.0 * squeeze, 12.0 * squeeze, 8.0 * squeeze])
    chain_set(pose, "ant_f", [-10.0 * brace + 18.0 * squeeze, 10.0 * squeeze, 6.0 * squeeze])
    feet = dict(FEET)
    for leg in ("b_n", "b_f"):
        feet[leg] = (FEET[leg][0] - 2.0 * brace, FEET[leg][1])
    plant(pose, feet)
    k = 1.0 + 0.06 * a * (1 - sq) - 0.1 * squeeze
    # the squeeze: a push running round the rim from the tail to the vent
    def wave(th):
        u = ((th + 180.0) % 360.0) / 240.0   # 0 at the tail, 1 at the vent (angle 60)
        front = lerp(-0.3, 1.3, smooth(0.26, 0.6, t))
        return -0.1 * math.exp(-((u - front) / 0.2) ** 2) * (1 - back)
    egg = {}
    for eid, c, L, tilt in EGGS:
        if eid == "brood_3": continue
        # the rest draw together as it goes, then settle into the room it left
        vx, vy = (VENT[0] - c[0]) * 0.12, (VENT[1] - c[1]) * 0.12
        egg[eid] = (vx * sq * (1 - back) + vx * 0.6 * back * (1 - smooth(0.8, 1.0, t)),
                    vy * sq * (1 - back) + vy * 0.6 * back * (1 - smooth(0.8, 1.0, t)),
                    10.0 * math.sin(math.pi * sq), 1.0)
    # brood_3: down onto the vent, through it, out to SEAM_OUT at the cue;
    # hidden from just after the cue (the game's egg is there now), and the
    # next one rises into its place from 0.8.
    (ex, ey), L3 = EGGS[3][1], EGGS[3][2]
    if t <= LAY_CUE:
        u1 = smooth(0.05, 0.36, t)
        u2 = smooth(0.4, LAY_CUE, t)
        # to the vent, then out along the normal and down
        vx, vy = VENT[0] - ex, VENT[1] - 1.5 - ey
        ox, oy = SEAM_OUT[0] - VENT[0] + 0.2, SEAM_OUT[1] - VENT[1] + 2.2
        dx, dy = vx * u1 + ox * u2, vy * u1 + oy * u2
        # the egg rides the body's squat, which the seam's point does not;
        # take that back off so the egg is where the game says at the cue
        dy -= 3.6 * squeeze * u2
        egg["brood_3"] = (dx, dy, 60.0 * u1 + 6.0 * u2, 1.0 - 0.12 * u2)
    else:
        rise = smooth(0.8, 1.0, t)
        egg["brood_3"] = (0.0, 5.0 * (1 - rise), 0.0, 0.35 + 0.65 * rise)
    vent_open = smooth(0.3, 0.46, t) * (1 - smooth(0.62, 0.78, t))
    nod = {nid: (-22.0 * squeeze * (1 - j * 0.2), 1.0 + 0.4 * a * (1 - sq) - 0.3 * squeeze) for j, (nid, *_) in enumerate(NODULES)}
    flex = {sid: -10.0 * squeeze + 8.0 * brace for sid in SPINE_ORDER}
    ch = Chamber(k=k, fan=1.4 * a * (1 - sq) - 0.6 * squeeze, wave=wave, egg=egg, nod=nod, flex=flex, vent=(vent_open, 0.0))
    return pose, ch

def lay_egg_opacity(t):
    if t <= LAY_CUE: return 1.0
    if t < 0.8: return 0.0
    return smooth(0.8, 0.9, t)
LAY_SCALES = {"vent": lambda t: 1.0 + 1.3 * smooth(0.3, 0.46, t) * (1 - smooth(0.62, 0.78, t)),
              "core": lambda t: 1.0 + 0.3 * smooth(0.26, 0.6, t) * (1 - smooth(0.64, 1.0, t)),
              "organ": lambda t: 1.0 + 0.2 * smooth(0.26, 0.6, t) * (1 - smooth(0.64, 1.0, t))}
LAY_EXTRA = [("brood_3", "opacity", lay_egg_opacity), ("brood_3_glow", "opacity", lay_egg_opacity), ("brood_3_grub", "opacity", lay_egg_opacity),
             ("core", "opacity", lambda t: 0.8 + 0.2 * smooth(0.26, 0.6, t) * (1 - smooth(0.64, 1.0, t)))]

# ============================================================== death (0.95s)
# The chamber dies, not the animal. Anticipation (0-0.16): it swells tight,
# the crown stands, the core flares. Release (0.16-0.5): the core burns up
# white and goes out, the brood goes dark, the chamber collapses to two thirds
# of itself and the plates slump apart over it, the tail drops to the floor,
# the legs give and the body comes down, the head sags with the jaws slack.
# Settle to 0.85: the crown comes down over the sac in a wave from the front
# to the rear. Still from 0.85.
def death_parts(t):
    a = smooth(0.0, 0.16, t)
    rel = smooth(0.14, 0.5, t)
    settle = smooth(0.4, 0.85, t)
    return a, rel, settle

def death_state(t):
    a, rel, settle = death_parts(t)
    jolt = math.sin(math.pi * smooth(0.12, 0.4, t))
    pose = {"body": (-1.2 * a * (1 - rel) + 1.0 * jolt, -1.0 * a * (1 - rel) + 6.5 * rel, -3.0 * a * (1 - rel) + 5.0 * rel)}
    pose["abd"] = 4.0 * a * (1 - rel) - 8.0 * rel
    pose["thorax"] = 6.0 * rel
    pose["head"] = -8.0 * a * (1 - rel) + 22.0 * settle + 6.0 * rel
    pose["mand_u"] = -20.0 * rel
    pose["mand_d"] = 26.0 * rel
    chain_set(pose, "ant_n", [-18.0 * a * (1 - rel) + 50.0 * settle, 22.0 * settle, 14.0 * settle])
    chain_set(pose, "ant_f", [-14.0 * a * (1 - rel) + 40.0 * settle, 20.0 * settle, 12.0 * settle])
    feet = {}
    for leg, (fx, fy) in FEET.items():
        hip = LEGS[leg][0]
        splay = 3.5 if leg[0] == "f" else (-3.5 if leg[0] == "b" else 1.0)
        feet[leg] = (fx + splay * rel, fy + 0.4 * rel)
    plant(pose, feet)
    flex = {}
    for i, sid in enumerate(SPINE_FRONT):
        down = smooth(0.4 + 0.04 * i, 0.72 + 0.015 * i, t)
        flex[sid] = 16.0 * a * (1 - rel) - 52.0 * down
    k = 1.0 + 0.09 * a * (1 - rel) - 0.26 * rel
    egg = {eid: ((C[0] - c[0]) * 0.1 * rel, (C[1] + 8.0 - c[1]) * 0.18 * rel, 20.0 * rel * (1 if i % 2 else -1), 1.0 - 0.18 * rel) for i, (eid, c, L, tilt) in enumerate(EGGS)}
    nod = {nid: (8.0 * rel, 1.0 + 0.3 * a * (1 - rel) - 0.5 * rel) for nid, *_ in NODULES}
    ch = Chamber(k=k, fan=2.2 * a * (1 - rel) + 1.0 * rel, egg=egg, nod=nod, flex=flex)
    return pose, ch

def death_core_scale(t):
    a, rel, settle = death_parts(t)
    return 1.0 + 0.8 * a + 0.6 * rel - 1.2 * smooth(0.36, 0.7, t)
DEATH_SCALES = {"core": lambda t: max(0.2, death_core_scale(t)),
                "organ": lambda t: 1.0 + 0.4 * math.sin(math.pi * smooth(0.06, 0.4, t)) - 0.25 * smooth(0.4, 0.85, t)}
DEATH_EXTRA = [("core", "opacity", lambda t: 0.8 + 0.2 * smooth(0, 0.16, t) - 0.95 * smooth(0.36, 0.7, t)),
               ("seams", "opacity", lambda t: 1.0 - 0.7 * smooth(0.3, 0.75, t)),
               ("organ", "opacity", lambda t: 1.0 - 0.8 * smooth(0.35, 0.85, t))]
for eid, *_ in EGGS:
    DEATH_EXTRA.append((f"{eid}_glow", "opacity", lambda t: 1.0 - smooth(0.25, 0.6, t)))
    DEATH_EXTRA.append((f"{eid}_grub", "opacity", lambda t: 1.0 - 0.6 * smooth(0.25, 0.6, t)))
    DEATH_EXTRA.append((eid, "opacity", lambda t: 1.0 - 0.55 * smooth(0.3, 0.7, t)))

# ============================================================== clips
animations = {}
animations["swell"] = {
    "description": "The chamber breathing, and everything on it arriving late: it fills — the skin swells, the plates fan apart and the seams between them open pink, the tail lifts and the crown rises in a wave from the front to the rear — and lets go; the weight comes onto the legs a beat after, so the body sinks and the knees give. Inside, the eggs drift on their own orbits with their glows pulsing, and three nodules — eggs pressing the skin out from inside — roll along the belly toward the vent. The head nods, the jaws work twice, the antennae sweep and each leg treads once in turn. The idle she plays whenever she is not doing one of the other two, walking or standing.",
    "duration": 2.8,
    "tracks": tracks(swell_state, keyset(24), SWELL_SCALES, SWELL_EXTRA),
}
animations["command"] = {
    "description": "The call: she draws in — the chamber tight, the crown flat, the head down and back, the antennae folded — then rears and lets go, the head thrown up and forward with the jaws gaping, the chamber heaving out with the seams and the core flaring, the front feet lifting, and the crown standing up in a wave from the front to the rear, the way the rings the game draws leave her mouth; then everything settles back, the crown last. No damage and no windup — what answers it is the brood, not her.",
    "duration": 0.9,
    "tracks": tracks(command_state, keyset(18), COMMAND_SCALES, COMMAND_EXTRA),
}
animations["lay"] = {
    "description": "One egg leaving through the seam under the chamber: she braces and fills, and the egg nearest the vent is shifted down onto it; a squeeze runs round the chamber from the tail to the vent, the tail tips down, she squats, the vent opens and the egg is pushed through it and drops, out and gone at 0.62 (where the game's egg takes over, at (6.5, 34.5)); then the vent closes, the chamber relaxes, the rest of the brood settles into the room it left and the next egg rises into its place.",
    "duration": 1.2,
    "tracks": tracks(lay_state, keyset(24), LAY_SCALES, LAY_EXTRA),
}
TS_DEATH = [i / 32 for i in range(28)] + [0.85, 0.9, 1.0]
animations["death"] = {
    "description": "The chamber dies, not the animal: it swells tight with the crown standing and the core flaring, then the core burns up white and goes out, the brood goes dark, the chamber collapses to two thirds of itself with the plates slumping apart over it, the tail drops to the floor, the legs give and the body comes down, the head sags with the jaws slack; the crown comes down over the sac in a wave from the front to the rear. Still from 0.85.",
    "duration": 0.95,
    "tracks": tracks(death_state, TS_DEATH, DEATH_SCALES, DEATH_EXTRA),
}

# ============================================================== variants
PLATE_IDS = [pid for pid, _ in PLATES]
SPINE_IDS = [sid for sid, *_ in SPINES]
EGG_IDS = [eid for eid, *_ in EGGS]
def win_grad(mid, edge="$pheromone.dark2"):
    return {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, mid], [0.62, f"{edge}@heavy"], [1, f"{edge}@0"]]}
variants = {
    "enraged": {
        "description": "Phase two: the chamber has gone to term all at once. The plates go dark and the skin under them goes duller, while what is inside burns through — the seams between the plates lit, the window hot at its middle, every egg glowing white-hot at its heart — so the shell reads as splitting along the seams it already had rather than along cracks drawn over it. The crown bleaches and the head darkens.",
        "scale": 1.08,
        "set": {
            "sac.fill": "$mauve.light",
            "belly.fill": "$mauve.dark",
            "window.fill": win_grad("$pheromone.dark"),
            "seams.fill": "$pheromone.light",
            "core.scale": 1.45,
            "thorax.fill": "$chitin.dark2", "head.fill": "$chitin.dark2", "pronotum.fill": "$chitin.dark2",
            "brow.fill": "$husk",
            "organ.scale": 1.15,
            **{f"nodule_{j}.fill": "$mauve.dark" for j in range(len(NODULES))},
            **{f"{pid}.fill": "$carapace" for pid in PLATE_IDS},
            **{f"{pid}_ridge.fill": "$carapace.light" for pid in PLATE_IDS},
            **{f"{eid}_glow.fill": "$pheromone.light2" for eid in EGG_IDS},
            **{f"{eid}_grub.fill": "$white" for eid in EGG_IDS},
            **{f"{sid}.fill": "$husk.light" for sid in SPINE_IDS},
            **{f"{sid}_shade.fill": "$husk" for sid in SPINE_IDS},
        },
    },
    "final": {
        "description": "Phase three: the chamber is spent. She has laid most of what was in her — the window has shrunk to three quarters and three eggs are all that is left in it — and the shell has gone dark and dry over the top of that, so the only things still lit are the seams, the core, the last three eggs and a crown that has nothing left to guard.\n\nDeliberately not brighter than `enraged`. The obvious third step is more white, and a body that is mostly white has stopped being this body: the read has to be that there is *less* of her, which is a darker shell around a smaller, brighter middle rather than a light turned up.",
        "scale": 1.1,
        "set": {
            "sac.fill": "$mauve",
            "belly.fill": "$mauve.dark",
            "window.fill": win_grad("$pheromone.dark2", "$carapace.dark"),
            "window.scale": 0.75,
            "core.scale": 0.85,
            "seams.fill": "$pheromone.light2",
            "gloss.opacity": 0,
            "thorax.fill": "$chitin.dark2", "head.fill": "$chitin.dark2", "pronotum.fill": "$chitin.dark2",
            "brow.fill": "$husk.dark",
            "organ.scale": 1.25,
            **{f"nodule_{j}.opacity": 0 for j in range(len(NODULES))},
            **{f"{pid}.fill": "$carapace.dark" for pid in PLATE_IDS},
            **{f"{pid}_ridge.fill": "$carapace" for pid in PLATE_IDS},
            **{f"{sid}.fill": "$husk.light2" for sid in SPINE_IDS},
            **{f"{sid}_shade.fill": "$husk.light" for sid in SPINE_IDS},
            **{f"{eid}{suf}.opacity": 0 for eid in ("brood_0", "brood_1", "brood_5", "brood_6") for suf in ("", "_glow", "_grub")},
            **{f"{eid}_glow.fill": "$pheromone.light2" for eid in ("brood_2", "brood_3", "brood_4")},
            **{f"{eid}_grub.fill": "$white" for eid in ("brood_2", "brood_3", "brood_4")},
        },
    },
}

# ============================================================== document
DESCRIPTION = (
    "The hive itself, arriving: a queen who is almost all brood chamber. Drawn side-on, facing +x, the way a termite queen is — a small "
    "amber head and thorax at the front with six short dark legs under them, and behind them the abdomen, swollen into a chamber many "
    "times their size, that they drag. The only body on the roster whose inside is the thing you look at.\n\n"
    "The chamber is built rather than drawn: six dark plates over a stretched skin, so every gap between them is pressure showing, pink "
    "where the skin is thinnest; a crown of nine spines at uneven lengths standing off the plates (a ring of even points is a cog, and a "
    "cog cannot flex when the body under it does); and the brood seen through the skin of her flank — seven pale eggs, each the Ovum's "
    "shell with its pink glow and the grub in it, because that is what they become — with a light at the middle of them. Three nodules on "
    "the belly are eggs pressing the skin from inside. The skin is a dull rose (`$mauve`), her family but earthy; the bright pink is kept "
    "for what is alive in her — the seams, the eggs' glow, the core and the organ, which she carries on top of the chamber, the largest "
    "on the roster, because she is what all the others were announcing.\n\n"
    "Built on a skeleton (scripts/matriarch.py): legs solved to planted feet, an abdomen hinged at the waist, and a chamber whose swell "
    "places everything on it — the skin scales about its centre, the plates are carried out and fanned apart so the seams open, the "
    "spines flex from their roots in a wave down the crown, the eggs drift on their own orbits. `swell` is the chamber breathing with "
    "the weight coming onto the legs late; `command` is her calling the brood in — she draws in, rears and lets go, and the crown stands "
    "in a wave the way the rings the game draws leave her mouth; `lay` is one egg squeezed out through the seam under the chamber and "
    "dropped at 0.62 (the game's LAY_CUE, at its LAY_SEAM (6.5, 34.5)). Mirrored by the game. Gameplay radius 46. The `death` clip "
    "kills the chamber, not the animal: the core burns up white, the brood goes dark, the chamber collapses and the crown comes down over it."
)

doc = {
    "id": "ss.enemy.matriarch",
    "name": "Matriarch",
    "description": DESCRIPTION,
    "tags": ["enemy", "boss"],
    "size": [120, 112],
    "meta": {"radius": 46},
    "parts": RIG.parts,
    "variants": RIG.follow_tips(variants),
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-matriarch.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
