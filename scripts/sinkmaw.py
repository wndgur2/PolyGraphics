"""The Sinkmaw — the pan answering you by opening.

    python3 scripts/sinkmaw.py        # rewrites apps/ss/assets/ss-enemy-sinkmaw.json

The pan's last boss is not a body on the ground but a hole in it: an antlion's
pit, seen from above, with the larva's head and jaws in the throat. The game
roots it (`rooted` until enraged), pulls the player toward it (`pull` 95
inside 430) and every 5.5s gulps — the pull x3.2 for 0.7s, with `gulp` played
once over exactly that (feelers: `EnemyType.gulpInterval`, `gulpTime`,
`gulpAnim`). Enraged she "comes off the floor and crawls" at 84: `rooted` is
gated on `e.enraged`, so from then on the idle is played on a body that
walks, and the sprite flips with its travel like any unturned walker.

It was hand-placed and it did not move: the idle scaled the slopes a few
percent inside an opaque disc, so the silhouette never changed (3.6px of
travel at game scale, 0.5% of it moving), and the death faded colours inside
the same disc (0.2%). A hole's outline is a circle, and a circle scaled about
its centre is the same circle — so this one moves the things that cross the
rim:

  - the jaws are long larva mandibles hinged in the throat on a head bone;
    the idle is a real yawn — the head rises, the jaws open and lift out over
    the lip and close again with a twitch — and the gulp is anticipation
    (jaws spread wide over the rim, the lip swelling, the throat dilating)
    then the snap (jaws clap, the whole funnel contracts in a wave down the
    rings) then the rebound
  - sand slides in: grains lie out on the floor around the lip and run down
    over it and down the slopes into the throat on staggered clocks, faster
    as they fall; the rings pulse inward in a wave, phase-lagged down the
    funnel, so the pit reads as swallowing even where the outline cannot
  - six legs on a skeleton, hidden until `enraged`, walking in two tripods
    with their feet planted (two-bone IK) — the crawl `rooted` lets go of

Top-down, lit from the upper left: the inner rings sit off-centre toward the
light so the far wall is the lit one. Never mirrored by design and never
turned: the jaws face +x only so it has a front.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, INK_BOLD, write_doc)

# ============================================================== rig
# Canvas 160×160, origin at the centre (the throat), +x the jaws' front.
RIG = Rig()
B = RIG.bones
bone = RIG.bone
bone("body", None, (0.0, 0.0), 0.0)
bone("ground", None, (0.0, 0.0), 0.0)  # the pit itself: a second root, never posed
bone("head", "body", (-2.0, 0.0), 0.0, 10.0)
JAW = {"u": ((9.0, -5.2), -22.0), "d": ((9.0, 5.2), 22.0)}
for s, (at, h) in JAW.items():
    bone(f"jaw_{s}", "head", at, h, 38.0)

# Six legs round the rim, hips under the lip, knees out and feet on the floor.
LEG_ANGLES = [30.0 + 60.0 * i for i in range(6)]
HIP_R, FOOT_R, FEMUR, TIBIA = 50.0, 72.0, 13.0, 14.0
def polar(r, a): return (r * math.cos(R(a)), r * math.sin(R(a)))
LEG_BEND = 1
for i, a in enumerate(LEG_ANGLES):
    hip, foot = polar(HIP_R, a), polar(FOOT_R, a)
    hf, ht = ik2(hip, foot, FEMUR, TIBIA, LEG_BEND)
    bone(f"leg_{i}_f", "body", hip, hf, FEMUR)
    bone(f"leg_{i}_t", f"leg_{i}_f", B[f"leg_{i}_f"].end(), ht, TIBIA)
RIG.seal()
solve = RIG.solve
put, use, on_bone = RIG.put, RIG.use, RIG.on_bone

# ============================================================== parts
# The shadow a body off the floor casts; folded to nothing while she is a hole.
put("shadow", "ground", (5.0, 9.0), 0.0, circ(60.0), "$ink@soft", scale=0.05)

# ---- legs, under the lip: hidden until she comes off the floor
for i in range(6):
    at, a = on_bone(f"leg_{i}_t"); put(f"leg_{i}_tibia", f"leg_{i}_t", at, a, bar(TIBIA, 4.0, 2.0), "$dead", INK_HAIR, opacity=0)
    at, a = on_bone(f"leg_{i}_f"); put(f"leg_{i}_femur", f"leg_{i}_f", at, a, bar(FEMUR, 5.4, 4.2), "$rust.light", INK_HAIR, opacity=0)

# ---- the pit: a pale lip of thrown sand, then four rings stepping down to a
# dark throat, the inner ones sitting toward the light
put("rim_far", "ground", (0.0, 0.0), 0.0, {"kind": "ring", "r": 56.0, "width": 6.0}, "$sand.light2")
put("slope_a", "ground", (0.0, 0.0), 0.0, circ(53.0), "$sand.light", INK_THIN)
put("slope_b", "ground", (-1.2, -1.4), 0.0, circ(45.0), "$sand")
put("slope_c", "ground", (-2.2, -2.6), 0.0, circ(37.0), "$sand.dark")
put("slope_d", "ground", (-2.8, -3.4), 0.0, circ(29.0), "$sand.dark2")
# Cracks in the slopes, for when she tears loose.
CRACKS = {
    "crack_a": [(-52.0, -8.0), (-38.0, -4.0), (-29.0, -10.0), (-31.0, -8.0), (-38.0, -2.0), (-52.0, -6.0)],
    "crack_b": [(31.0, 31.0), (41.0, 23.0), (49.0, 27.0), (47.0, 28.0), (41.0, 25.0), (32.0, 33.0)],
    "crack_c": [(-21.0, 42.0), (-15.0, 51.0), (-17.0, 51.0), (-23.0, 44.0)],
    "crack_d": [(20.0, -48.0), (14.0, -38.0), (18.0, -30.0), (16.0, -30.0), (12.0, -38.0), (18.0, -48.0)],
}
for cid, pts in CRACKS.items():
    put(cid, "ground", (0.0, 0.0), 0.0, poly(pts), "$ink@heavy", opacity=0)
put("throat_o", "ground", (0.0, 0.0), 0.0, circ(21.0), "$ink")
put("throat", "ground", (0.0, 0.0), 0.0, circ(18.0), "$dead")
put("throat_glow", "ground", (0.0, 0.0), 0.0, circ(11.0), "$ember@soft")

# ---- sand sliding in: grains out on the floor round the lip, each on its own
# clock, running over the lip and down into the throat
GRAINS = []
for i in range(16):
    a = (i * 360.0 / 16) + (13.0 if i % 2 else -9.0) + 5.0 * math.sin(i * 2.1)
    ph = ((i * 7) % 16) / 16.0
    r0 = 70.0 - 3.0 * ((i * 5) % 3)
    GRAINS.append((f"grain_{i}", a, ph, r0))
R_IN = 16.0
def grain_r(r0, u):
    """Radius along a grain's run at life fraction u: slow on the floor, faster as it falls."""
    return lerp(r0, R_IN, u ** 1.6)
def grain_alpha(u): return smooth(0.0, 0.08, u) * (1 - smooth(0.82, 1.0, u))
for gid, a, ph, r0 in GRAINS:
    r = grain_r(r0, ph)
    put(gid, "ground", polar(r, a), a, ell(2.0, 1.2), "$sand.light2", INK_HAIR)

# ---- the larva in the throat: a flat head, the organ on it, two ember eyes
HEAD = [(-7.0, -5.0), (-4.0, -8.0), (4.0, -8.6), (10.0, -7.6), (12.0, -4.0), (12.4, 0.0), (12.0, 4.0), (10.0, 7.6),
        (4.0, 8.6), (-4.0, 8.0), (-7.0, 5.0)]
put("head", "head", (0.0, 0.0), 0.0, poly(HEAD), "$rust.light", INK_THIN)
put("head_plate", "head", (3.0, 0.0), 0.0, ell(6.0, 4.6), "$rust")
use("organ", "head", (1.0, 0.0), "ss.lib.organ", scale=[1.3, 1.1])
for s, sg in (("u", -1), ("d", 1)):
    put(f"eye_{s}", "head", (5.0, sg * 8.6), 0.0, circ(2.6), "$ember", INK_HAIR)
    put(f"eye_{s}_core", "head", (5.6, sg * 8.2), 0.0, circ(1.0), "$gold.light")

# ---- the jaws: long larva sickles with three teeth, hinged in the throat
SICKLE = [(-1.0, -3.2), (10.0, -4.2), (22.0, -4.0), (30.0, -2.2), (35.0, 1.0), (38.0, 5.0), (38.8, 9.4),
          (36.4, 6.6), (33.6, 3.6), (31.0, 2.8), (29.8, 5.4), (28.0, 2.6), (23.0, 2.2), (21.8, 4.8), (20.0, 2.0),
          (14.0, 2.0), (12.8, 4.2), (11.0, 1.8), (5.0, 2.4), (-1.0, 3.2)]
EDGE = [(18.0, -3.4), (29.6, -1.6), (34.4, 1.2), (37.2, 5.0), (37.8, 7.6), (35.4, 3.6), (29.6, 0.0), (19.0, -1.4)]
def mirror_pts(pts): return [(x, -y) for x, y in pts]
for s in ("u", "d"):
    at, a = on_bone(f"jaw_{s}")
    f = (lambda p: p) if s == "u" else mirror_pts
    put(f"jaw_{s}", f"jaw_{s}", at, a, poly(f(SICKLE)), "$husk", INK_THIN)
    put(f"jaw_{s}_edge", f"jaw_{s}", at, a, poly(f(EDGE)), "$bone.light")

RIG.check()
STILL = {f"eye_{s}" for s in "ud"} | {f"eye_{s}_core" for s in "ud"}
JAW_PARTS = ["jaw_u", "jaw_u_edge", "jaw_d", "jaw_d_edge"]
RINGS = ["rim_far", "slope_a", "slope_b", "slope_c", "slope_d"]

# ============================================================== motion
HEAD_PARTS = ["head", "head_plate", "organ", "eye_u", "eye_d", "eye_u_core", "eye_d_core"] + ["jaw_u", "jaw_u_edge", "jaw_d", "jaw_d_edge"]
def tracks(pose_at, ts, extra, still=()):
    """Rig.tracks, with extras on a part/prop the rig already drives folded into it (x/y/rot add, scale/opacity multiply)."""
    out = RIG.tracks(pose_at, ts, [], still)
    have = {(t["part"], t["prop"]): t for t in out}
    for pid, prop, fn in extra:
        if (pid, prop) in have:
            tr = have[(pid, prop)]
            mul = prop in ("scale", "opacity")
            tr["keys"] = [[k[0], r2(k[1] * fn(k[0]) if mul else k[1] + fn(k[0]))] for k in tr["keys"]]
        else:
            tr = {"part": pid, "prop": prop, "keys": [[r2(t), r2(fn(t))] for t in ts], "ease": "linear"}
            out.append(tr); have[(pid, prop)] = tr
    return out
def surge(fn): return [(p, "x", fn) for p in HEAD_PARTS]

def plant(pose, feet):
    world = solve(pose)
    for i in range(6):
        hx, hy, _ = world[f"leg_{i}_f"]
        hf, ht = ik2((hx, hy), feet[i], FEMUR, TIBIA, LEG_BEND)
        pose[f"abs:leg_{i}_f"] = hf
        pose[f"abs:leg_{i}_t"] = ht
    return pose
REST_FEET = [polar(FOOT_R, a) for a in LEG_ANGLES]
# Two tripods of alternate legs round the ring.
def crawl_feet(t, stride=6.0):
    feet = []
    for i, (fx, fy) in enumerate(REST_FEET):
        u = (t * 2 + (0.5 if i % 2 else 0.0)) % 1.0  # two steps a loop: 2.2s is slow for a walk
        if u < 0.6:
            dx = lerp(stride, -stride, u / 0.6)
            pull = 0.0
        else:
            v = (u - 0.6) / 0.4
            dx = lerp(-stride, stride, smooth(0.0, 1.0, v))
            pull = math.sin(math.pi * v)
        k = 1 - 0.12 * pull  # a foot in the air is drawn in toward the body
        feet.append((fx * k + dx, fy * k))
    return feet

def grain_tracks(u_of_t, alpha_of_t=None):
    """Each grain's x/y/opacity from `u_of_t(phase, t)`, its life fraction."""
    out = []
    for gid, a, ph, r0 in GRAINS:
        bx, by = polar(grain_r(r0, ph), a)
        def fx(t, a=a, ph=ph, r0=r0, bx=bx): return polar(grain_r(r0, u_of_t(ph, t)), a)[0] - bx
        def fy(t, a=a, ph=ph, r0=r0, by=by): return polar(grain_r(r0, u_of_t(ph, t)), a)[1] - by
        def fo(t, ph=ph): return (alpha_of_t or (lambda ph, t: grain_alpha(u_of_t(ph, t))))(ph, t)
        out += [(gid, "x", fx), (gid, "y", fy), (gid, "opacity", fo)]
    return out

def jaw_scale(fn): return [(p, "scale", fn) for p in JAW_PARTS]

# ---- yawn: the idle, 2.2s. The pit breathes (a wave down the rings), the sand
# slides in, and once a loop the larva yawns — the head rises, the jaws open
# and lift out over the lip, hold, and shut with a twitch. Enraged, the legs
# walk under it.
def yawn_open(t):
    return smooth(0.08, 0.42, t) * (1 - smooth(0.62, 0.84, t))
def yawn_pose(t):
    o = yawn_open(t)
    twitch = math.sin(math.pi * smooth(0.84, 0.96, t))
    pose = {"body": (0.8 * cyc(2 * t, 0.1), 0.6 * cyc(2 * t, 0.35), 1.2 * cyc(t, 0.2)),
            "head": 0.0}
    # the head bone only turns; its surge is carried by the jaws' own x below
    for s, sg in (("u", -1), ("d", 1)):
        pose[f"jaw_{s}"] = sg * (40.0 * o - 6.0 * twitch) + sg * 3.0 * cyc(t, 0.3) * (1 - o)
    return plant(pose, crawl_feet(t))
def ring_breath(t, i):
    """The funnel breathing, a wave running down the rings (i = 0 at the lip)."""
    return 1.0 + (0.035 + 0.01 * i) * cyc(t, -0.07 * i)
YAWN_EXTRA = (
    [(p, "scale", (lambda t, i=i: ring_breath(t, i))) for i, p in enumerate(RINGS)]
    + [("throat", "scale", lambda t: 1.0 + 0.1 * yawn_open(t) + 0.04 * cyc(t, -0.35)),
       ("throat_o", "scale", lambda t: 1.0 + 0.08 * yawn_open(t) + 0.04 * cyc(t, -0.35)),
       ("throat_glow", "scale", lambda t: 1.0 + 0.35 * yawn_open(t) + 0.08 * cyc(t, -0.4)),
       ("organ", "scale", lambda t: 1.0 + 0.1 * yawn_open(t))]
    + surge(lambda t: 6.0 * yawn_open(t))
    + jaw_scale(lambda t: 1.0 + 0.36 * yawn_open(t))
    + grain_tracks(lambda ph, t: (ph + t) % 1.0)
)

# ---- gulp: 0.7s over the pull's spike. Anticipation to 0.4 — the jaws spread
# wide out over the rim, the lip swells and the throat dilates, the sand holds
# — the snap at 0.4–0.5 — the jaws clap, the funnel contracts in a wave down
# the rings and the sand rushes in — then the rebound past rest and settle.
def g_open(t): return smooth(0.0, 0.38, t) * (1 - smooth(0.38, 0.47, t))
def g_snap(t): return smooth(0.38, 0.47, t) * (1 - smooth(0.5, 0.78, t))
def g_rebound(t): return math.sin(math.pi * smooth(0.5, 1.0, t)) * 0.5 * (1 - smooth(0.8, 1.0, t))
def gulp_pose(t):
    o, sn = g_open(t), g_snap(t)
    pose = {"body": (0.0, 0.0, 0.0)}
    for s, sg in (("u", -1), ("d", 1)):
        pose[f"jaw_{s}"] = sg * (58.0 * o - 14.0 * sn + 6.0 * g_rebound(t))
    return plant(pose, crawl_feet(0.0))
def ring_gulp(t, i):
    lag = 0.025 * i
    swell = smooth(0.0, 0.38, t) * (1 - smooth(0.38 + lag, 0.47 + lag, t))
    squeeze = smooth(0.38 + lag, 0.47 + lag, t) * (1 - smooth(0.52 + lag, 0.82, t))
    return 1.0 + 0.05 * swell - (0.06 + 0.035 * i) * squeeze + 0.02 * g_rebound(t)
def gulp_u(ph, t):
    # Held, then a rush most of the way in on the snap.
    return min(0.999, ph + 0.02 * t + 0.6 * smooth(0.38, 0.62, t) * (1 - ph))
GULP_EXTRA = (
    [(p, "scale", (lambda t, i=i: ring_gulp(t, i))) for i, p in enumerate(RINGS)]
    + [("throat", "scale", lambda t: 1.0 + 0.3 * g_open(t) - 0.25 * g_snap(t)),
       ("throat_o", "scale", lambda t: 1.0 + 0.25 * g_open(t) - 0.2 * g_snap(t)),
       ("throat_glow", "scale", lambda t: 1.0 + 0.45 * g_open(t) + 0.2 * g_snap(t)),
       ("organ", "scale", lambda t: 1.0 + 0.25 * g_open(t) + 0.15 * g_snap(t))]
    + surge(lambda t: 8.0 * g_open(t) - 4.0 * g_snap(t))
    + jaw_scale(lambda t: 1.0 + 0.42 * g_open(t) - 0.06 * g_snap(t))
    + grain_tracks(gulp_u, lambda ph, t: grain_alpha(gulp_u(ph, t)))
)

# ---- death: 0.9s. The jaws clap once, then fall open and lie out flat over
# the lip; the throat closes and its glow goes; the pit fills from the bottom
# up (the dark rings fade into the pale one) and the lip slumps in; the last
# sand runs in and stops; the eyes go dark and the organ flares and goes out.
# Enraged, the legs fold in. Still from 0.85.
def d_clap(t): return math.sin(math.pi * smooth(0.0, 0.18, t))
def d_fall(t): return smooth(0.16, 0.7, t)
def death_pose(t):
    pose = {"body": (0.0, 0.0, 0.0)}
    for s, sg in (("u", -1), ("d", 1)):
        pose[f"jaw_{s}"] = sg * (-10.0 * d_clap(t) + 72.0 * d_fall(t))
    feet = []
    for i, (fx, fy) in enumerate(REST_FEET):
        k = lerp(1.0, 0.8, smooth(0.1, 0.7, t))
        feet.append((fx * k, fy * k))
    return plant(pose, feet)
def death_u(ph, t): return min(0.999, ph + 0.5 * smooth(0.0, 0.8, t) * (1 - ph))
DEATH_EXTRA = (
    [("rim_far", "scale", lambda t: 1.0 - 0.06 * smooth(0.2, 0.8, t)),
     ("slope_a", "scale", lambda t: 1.0 - 0.05 * smooth(0.2, 0.8, t)),
     ("slope_b", "opacity", lambda t: 1.0 - smooth(0.45, 0.8, t)),
     ("slope_c", "opacity", lambda t: 1.0 - smooth(0.3, 0.7, t)),
     ("slope_d", "opacity", lambda t: 1.0 - smooth(0.2, 0.6, t)),
     ("throat", "scale", lambda t: 1.0 - 0.6 * smooth(0.15, 0.7, t)),
     ("throat_o", "scale", lambda t: 1.0 - 0.55 * smooth(0.15, 0.7, t)),
     ("throat_glow", "opacity", lambda t: 1.0 - smooth(0.1, 0.5, t)),
     ("eye_u", "opacity", lambda t: 1.0 - 0.8 * smooth(0.15, 0.55, t)),
     ("eye_d", "opacity", lambda t: 1.0 - 0.8 * smooth(0.15, 0.55, t)),
     ("eye_u_core", "opacity", lambda t: 1.0 - smooth(0.1, 0.45, t)),
     ("eye_d_core", "opacity", lambda t: 1.0 - smooth(0.1, 0.45, t)),
     ("organ", "scale", lambda t: 1.0 + 0.5 * math.sin(math.pi * smooth(0.05, 0.5, t))),
     ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.35, 0.8, t))]
    + jaw_scale(lambda t: 1.0 + 0.15 * d_fall(t))
    + surge(lambda t: -2.0 * smooth(0.2, 0.7, t))
    + grain_tracks(death_u, lambda ph, t: grain_alpha(death_u(ph, t)) * (1 - smooth(0.5, 0.8, t)))
)

animations = {}
animations["yawn"] = {
    "description": "The idle: the pit breathes in a wave running down its rings, the sand on the floor round it slides over the lip and down the slopes into the throat on staggered clocks, faster as it falls, and once a loop the larva yawns — the head rises, the jaws open and lift out over the lip, and shut with a twitch. Enraged, when she has come off the floor, the six legs round the rim walk under it in two tripods with their feet planted.",
    "duration": 2.2,
    "tracks": tracks(yawn_pose, keyset(22), YAWN_EXTRA, still=STILL),
}
animations["gulp"] = {
    "description": "Played once over the pull's 0.7s spike, the tell: the jaws spread wide out over the rim while the lip swells, the throat dilates and the glow flares and the sand on the slopes holds — then the snap, the jaws clapping shut as the whole funnel contracts in a wave down the rings and the sand rushes in — then the rebound past rest and the settle.",
    "duration": 0.7,
    "tracks": tracks(gulp_pose, keyset(21), GULP_EXTRA, still=STILL),
}
DEATH_TS = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The jaws clap once, then fall open and lie out flat over the lip; the throat closes and its glow goes; the pit fills from the bottom up and the lip slumps in; the last of the sand runs in and stops; the eyes go dark and the organ flares and goes out. Enraged, the legs fold in as it fills. Still from 0.85.",
    "duration": 0.9,
    "tracks": tracks(death_pose, DEATH_TS, DEATH_EXTRA, still=STILL),
}

# ============================================================== states
LEGS_ON = {f"leg_{i}_{p}.opacity": 1 for i in range(6) for p in ("femur", "tibia")}
CRACKS_ON = {f"{c}.opacity": 1 for c in CRACKS}
variants = {
    "enraged": {
        "description": "Halfway: she comes off the floor and crawls. Six rust legs out from under the lip, a shadow under her where there was none — a hole casts no shadow — the lip gone rust, the slopes cracked, the throat and the jaw edges ember. The gulps come faster.",
        "set": {
            "shadow.scale": 1,
            **LEGS_ON, **CRACKS_ON,
            "rim_far.fill": "$rust.light",
            "slope_a.fill": "$sand",
            "slope_a.stroke": {"color": "$ink", "width": "bold"},
            "throat_glow.fill": "$ember@heavy", "throat_glow.scale": 1.3,
            "jaw_u_edge.fill": "$ember", "jaw_d_edge.fill": "$ember",
            "eye_u.scale": 1.3, "eye_d.scale": 1.3,
            "organ.scale": [1.6, 1.35],
        },
    },
    "final": {
        "description": "Phase three: the four steps are gone — the slopes have fallen into the throat and the hole runs flat to its own rim, with no grains left sliding because there is no slope left to slide down. This is the drawing of `pullFlat`: out at the edge it now pulls exactly as hard as it does in the middle. Still off the floor, still crawling.",
        "set": {
            "shadow.scale": 1,
            **LEGS_ON, **CRACKS_ON,
            "rim_far.fill": "$ember@heavy",
            "slope_a.fill": "$rust.dark",
            "slope_a.stroke": {"color": "$ink", "width": "bold"},
            "slope_b.fill": "$soil", "slope_c.fill": "$soil", "slope_d.fill": "$soil",
            **{f"{g[0]}.opacity": 0 for g in GRAINS},
            "throat.scale": 1.35, "throat_o.scale": 1.35,
            "throat_glow.fill": "$ember@heavy", "throat_glow.scale": 1.7,
            "eye_u.scale": 1.5, "eye_d.scale": 1.5,
            "jaw_u_edge.fill": "$white", "jaw_d_edge.fill": "$white",
            "organ.scale": [2.0, 1.7],
        },
    },
}

# ============================================================== document
DESCRIPTION = (
    "The pan's last arrival: it answers you by opening. Not a body on the ground but a hole in it, seen from above — an antlion's pit: a pale lip "
    "of thrown sand, four rings stepping down to a dark throat (lit from the upper left, so the far wall is the bright one), grains out on the "
    "floor sliding over the lip and down into it, and in the throat the larva — a flat rust head with the organ lit on it, two ember eyes, and "
    "two long toothed husk jaws hinged in the throat and curving out toward +x. The game pulls the player toward it (EnemyType.pull) and every "
    "5.5s gulps; `gulp` is that beat, played once over it — the jaws spread wide over the rim and the lip swells (the tell), then the snap: the "
    "jaws clap and the funnel contracts in a wave down the rings, and rebounds. The idle `yawn` is the pit breathing, the sand going down, and "
    "the larva yawning its jaws out over the lip once a loop. `enraged` puts six legs out from under the lip, casts a shadow under her, turns "
    "the lip rust, cracks the slopes and lights the jaw edges: she comes off the floor and crawls, and the legs walk in the idle. `final` is "
    "the pit fallen flat. Built on a skeleton (scripts/sinkmaw.py): the jaws hang off a head bone, the legs are solved to planted feet. Never "
    "mirrored by design: the jaws face +x only so it has a front for the codex. Gameplay radius 46. The `death` clip claps the jaws, lays them "
    "out over the lip and fills the pit."
)
doc = {
    "id": "ss.enemy.sinkmaw",
    "name": "Sinkmaw",
    "description": DESCRIPTION,
    "tags": ["enemy", "boss"],
    "size": [160, 160],
    "meta": {"radius": 46},
    "parts": RIG.parts,
    "variants": variants,
    "skeleton": RIG.skeleton(),
    "animations": animations,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-sinkmaw.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
