"""The Burr — the pan's body that is ranged by dying.

    python3 scripts/burr.py        # rewrites apps/ss/assets/ss-enemy-burr.json

The Rattle's slot on the Salt Pan, and the one wave body there that shoots, in
the only way a body that arrives a hundred at a time can afford to: when it is
killed within 230px of you it throws five of its spines outward in a ring
(feelers: `EnemyType.deathShots`, `deathShotTex: 'e_spine'`; an elite sheds
eight). So it is drawn as the thing it sheds — a chitin ball carrying five big
spines, evenly round it, the ones that leave, with four smaller ones between —
and its death is the shot: the five kick out along their own roots.

It was hand-placed, and its walk measured 3.6px at game scale
(scripts/motion.ts): six stubs swinging about their own centres, and the ball
never moving at all; its spines' rotation tracks were written as absolute
angles into a relative channel, so every spine stood at double its turn. This
rebuilds it on the shared rig (scripts/rig.py):

  - a skeleton seen from above: the ball is the root bone, which surges, sways
    and yaws on the step; every spine is a bone of its own rooted in the ball's
    rim, so it can bristle about its root; the head is a bone that nods ahead of
    the ball, and each mandible is hinged at the head's front
  - six legs, each a femur and a tibia solved every frame to a foot on the
    ground (two-bone IK), so a planted foot stays planted while the ball rides
    over it
  - the spines ripple in a wave that runs round the ring once a stride, so the
    ball reads as trundling rather than gliding

Chitin amber, lit from the upper left with a dark crescent on the lower right
(the three values: lit cap, body, shade), the spines pale husk with dark
collars like the one it throws (`ss.enemy.spine`).
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, cyc_c, wrap, keyset, ik2,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 44×44, origin at the centre, seen from above, +x forward, +y down
# (the "d" side; "u" is its mirror at -y).
W, H = 44, 44
RIG = Rig()
B = RIG.bones
bone = RIG.bone
SIDES = {"u": -1, "d": 1}

BALL_R = 8.2
bone("ball", None, (0.0, 0.0), 0.0)
# The head, a short bone off the front of the ball, and the mandibles hinged
# at its front corners.
bone("head", "ball", (6.6, 0.0), 0.0, 3.4)
MAND_HINGE = (11.0, 1.5)
MAND_REST = 26.0
for s, sg in SIDES.items():
    bone(f"mand_{s}", "head", (MAND_HINGE[0], MAND_HINGE[1] * sg), MAND_REST * sg, 3.4)

# The spines: five big ones evenly round the ball (the five it sheds), and a
# smaller one between each pair except in front, where the head is. Each is a
# bone rooted just inside the ball's rim and pointing straight out.
SPINE_ROOT = 7.0
PRIMARY = [36.0 + 72.0 * k for k in range(5)]        # 36 108 180 252 324
SECONDARY = [72.0 + 72.0 * k for k in range(4)]      # 72 144 216 288
SPINES = []  # (name, angle, length, primary)
for k, a in enumerate(PRIMARY):
    SPINES.append((f"spine_{k}", a, 10.2, True))
for k, a in enumerate(SECONDARY):
    SPINES.append((f"spur_{k}", a, 6.6, False))
SPINES.sort(key=lambda s: s[1])
for name, a, L, _ in SPINES:
    bone(name, "ball", (SPINE_ROOT * math.cos(R(a)), SPINE_ROOT * math.sin(R(a))), a, L)

# The legs: hips under the ball, a femur and a tibia to a foot on the ground,
# and a short claw. Rest foot positions for the "d" side; "u" is the mirror.
LEGS = {  # name: (hip, rest foot, femur, tibia)
    "f": ((3.6, 3.4), (8.2, 9.4), 5.0, 5.8),
    "m": ((0.4, 4.2), (1.0, 11.2), 5.0, 5.8),
    "b": ((-3.2, 3.6), (-7.4, 9.6), 5.0, 5.8),
}
def leg_names():
    for n in ("b", "m", "f"):
        for s in ("u", "d"):
            yield f"{n}_{s}", n, s
def hip_of(n, s): return (LEGS[n][0][0], LEGS[n][0][1] * SIDES[s])
def foot_of(n, s): return (LEGS[n][1][0], LEGS[n][1][1] * SIDES[s])
def bend_of(n, s):
    """The knee bows away from the midline: whichever IK solution puts it further out."""
    hip, foot = hip_of(n, s), foot_of(n, s)
    best = None
    for b in (1, -1):
        hf, _ = ik2(hip, foot, LEGS[n][2], LEGS[n][3], b)
        ky = hip[1] + LEGS[n][2] * math.sin(R(hf))
        if best is None or abs(ky) > best[0]: best = (abs(ky), b)
    return best[1]
BEND = {f"{n}_{s}": bend_of(n, s) for _, n, s in leg_names()}
CLAW_TURN = {"f": 24.0, "m": 8.0, "b": -20.0}
for leg, n, s in leg_names():
    hf, ht = ik2(hip_of(n, s), foot_of(n, s), LEGS[n][2], LEGS[n][3], BEND[leg])
    bone(f"{leg}_femur", "ball", hip_of(n, s), hf, LEGS[n][2])
    bone(f"{leg}_tibia", f"{leg}_femur", B[f"{leg}_femur"].end(), ht, LEGS[n][3])
    bone(f"{leg}_claw", f"{leg}_tibia", B[f"{leg}_tibia"].end(), ht - CLAW_TURN[n] * SIDES[s], 1.6)

RIG.seal()
solve = RIG.solve
on_bone = RIG.on_bone
put = RIG.put

# ============================================================== parts
# Three values on the ball: a lit cap (chitin.light), the body (chitin) and a
# shade crescent on the lower right (chitin.dark). Dark legs and collars; pale
# husk spines, the lightest thing on it, because they are what it throws. The
# ball and the head take the thin outline; spines and legs the hairline.
BALL, BALL_LIT, BALL_SHADE, PIT = "$chitin.light", "$chitin.light2", "$chitin", "$chitin.dark"
SPINE, SPUR, COLLAR = "$husk.light", "$husk", "$chitin.dark"
LEG, LEG_CLAW, LEG_KNEE = "$chitin", "$chitin.dark", "$chitin.light"

# ---- legs, under everything
for leg, n, s in leg_names():
    at, a = on_bone(f"{leg}_claw"); put(f"leg_{leg}_claw", f"{leg}_claw", at, a, bar(1.6, 1.0, 0.5, 0.4), LEG_CLAW, INK_HAIR)
    at, a = on_bone(f"{leg}_tibia"); put(f"leg_{leg}_tibia", f"{leg}_tibia", at, a, bar(LEGS[n][3], 1.8, 1.2), LEG, INK_HAIR)
    at, a = on_bone(f"{leg}_femur"); put(f"leg_{leg}_femur", f"{leg}_femur", at, a, bar(LEGS[n][2], 2.3, 1.9), LEG, INK_HAIR)
    at, a = on_bone(f"{leg}_tibia"); put(f"leg_{leg}_knee", f"{leg}_tibia", at, 0.0, circ(1.05), LEG_KNEE)

# ---- the spines, rooted under the ball's rim: a spike of husk, a keel of
# light down its length, and a dark collar where it leaves the ball — the
# drawing of `ss.enemy.spine`, which is what one of these becomes.
def spike(L, w):
    return poly([(-0.6, -w * 0.42), (0.0, -w / 2), (L * 0.55, -w * 0.3), (L - 0.8, -w * 0.12), (L + 0.4, 0.0),
                 (L - 0.8, w * 0.12), (L * 0.55, w * 0.3), (0.0, w / 2), (-0.6, w * 0.42)])
for name, a, L, prim in SPINES:
    at, ang = on_bone(name)
    put(name, name, at, ang, spike(L, 3.4 if prim else 2.6), SPINE if prim else SPUR)
    if prim:
        kat, _ = on_bone(name, L * 0.42, -0.35)
        put(f"{name}_keel", name, kat, ang, rect(L * 0.5, 0.6, 0.3), "$white@0.55")
    cat, _ = on_bone(name, BALL_R - SPINE_ROOT + 0.5)
    put(f"{name}_collar", name, cat, ang, ell(0.9, 1.5 if prim else 1.2), COLLAR)

# ---- the ball: shade, body, lit cap, sockets, the organ on the back
put("ball", "ball", (0.0, 0.0), 0.0, circ(BALL_R), BALL_SHADE, INK_THIN)
put("ball_body", "ball", (-1.0, -1.0), 0.0, circ(BALL_R - 1.3), BALL)
put("ball_lit", "ball", (-2.4, -2.6), -30.0, ell(4.2, 3.2), BALL_LIT)
put("ball_gloss", "ball", (-3.4, -4.2), -30.0, ell(1.8, 0.8), "$white@soft")
# the sockets the small hooks sit in, a ring round the organ
for k in range(6):
    a = R(k * 60.0 + 30.0)
    put(f"socket_{k}", "ball", (-0.6 + 4.6 * math.cos(a), 0.0 + 4.2 * math.sin(a)), 0.0, circ(0.7), PIT)
RIG.use("organ", "ball", (-0.6, 0.0), "ss.lib.organ", scale=[0.56, 0.52])

# ---- the head: a small dark capsule with the mandibles under its front and
# the eyes at its sides
for s, sg in SIDES.items():
    at, a = on_bone(f"mand_{s}")
    put(f"mand_{s}", f"mand_{s}", at, a,
        poly([(-0.6, -0.9 * sg), (1.6, -0.9 * sg), (3.2, -0.2 * sg), (4.2, 1.4 * sg), (3.0, 0.9 * sg), (1.4, 0.8 * sg), (-0.6, 0.9 * sg)]),
        "$bone.light", INK_HAIR)
put("head", "head", (9.0, 0.0), 0.0, ell(3.0, 3.3), "$chitin", INK_HAIR)
put("head_lit", "head", (8.6, -1.2), -20.0, ell(1.6, 0.9), "$chitin.light")
for s, sg in SIDES.items():
    put(f"eye_{s}", "head", (10.2, 2.0 * sg), 0.0, circ(0.75), "$ink")

RIG.check()
PARTS = RIG.parts

# ============================================================== motion
STILL = tuple(p["id"] for p in PARTS if p["id"].endswith("_knee") or p["id"].startswith("eye_") or p["id"].startswith("socket_"))
def tracks(pose_at, ts, extra=None):
    return RIG.tracks(pose_at, ts, extra, STILL)

def plant(pose, feet):
    world = solve(pose)
    for leg, n, s in leg_names():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik2((hx, hy), feet[leg], LEGS[n][2], LEGS[n][3], BEND[leg])
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_claw"] = ht + (B[f"{leg}_claw"].heading - B[f"{leg}_tibia"].heading) + pose.get("claw", 0.0) * SIDES[s]
    return pose

TRIPOD = {"f_u": 0.0, "b_u": 0.0, "m_d": 0.0, "f_d": 0.5, "b_d": 0.5, "m_u": 0.5}
def step(t, ph, stride, tuck, duty=0.55):
    u = (t + ph) % 1.0
    if u < duty:
        return lerp(stride, -stride, u / duty), 0.0
    v = (u - duty) / (1 - duty)
    return lerp(-stride, stride, smooth(0.0, 1.0, v)), tuck * math.sin(math.pi * v)

# ---- trundle (0.62s): the walk and the idle. The ball surges on each push and
# rocks toward the pushing side; the spines ripple in a wave that runs round
# the ring once a stride — each one laid back and raised in turn, the primaries
# furthest — so the ball reads as rolling along under them; the head nods
# ahead of the ball and the mandibles work.
WAVE = 16.0
def trundle_pose(t):
    pose = {"ball": (1.3 * cyc(2 * t, 0.1), 1.4 * cyc(t, 0.25), 7.0 * cyc(t, 0.0))}
    for name, a, L, prim in SPINES:
        # a wave running round the ring (the phase is the spine's bearing), the
        # spine laid back toward the rear on the crest
        lag = a / 360.0
        back = 1 if 0 < a < 180 else -1   # which way "back" is for this side
        amp = WAVE if prim else WAVE * 0.7
        pose[name] = back * amp * cyc(t, -lag)
    pose["head"] = -4.0 * cyc(t, -0.08)
    m = 10.0 * max(0.0, cyc(2 * t, 0.3)) - 6.0
    pose["mand_u"] = -m
    pose["mand_d"] = m
    feet = {}
    for leg, n, s in leg_names():
        dx, tk = step(t, TRIPOD[leg], 3.0 * (0.85 if n == "m" else 1.0), 1.8)
        fx, fy = foot_of(n, s)
        feet[leg] = (fx + dx, fy - SIDES[s] * tk)
    return plant(pose, feet)
def trundle_extra():
    squash = lambda t: 1.0 + 0.05 * cyc(2 * t, 0.35)
    return [(pid, "scale", squash) for pid in ("ball", "ball_body", "ball_lit")]

# ---- death (0.42s). The game throws its five spines the moment it is killed,
# so the clip's release is at the start, and what it draws is the shot:
# anticipation — the ball clenches, every spine drawn in and bristling straight
# out; release — the five big spines kick out along their own roots and are
# gone, the ball bursting after them and the small spurs flung flat; recovery —
# the ball sags, the legs fold in under it, the head drops and the organ goes
# out. Still from 0.85.
FIRE = 0.14
def death_pose(t):
    clench = smooth(0.0, FIRE, t) * (1 - smooth(FIRE, FIRE + 0.08, t))
    burst = math.sin(math.pi * smooth(FIRE, 0.42, t))
    fall = smooth(0.3, 0.82, t)
    pose = {"ball": (-0.8 * clench + 0.6 * fall, 0.0, 8.0 * fall - 3.0 * burst)}
    for name, a, L, prim in SPINES:
        back = 1 if 0 < a < 180 else -1
        if prim:
            pose[name] = 0.0
        else:
            pose[name] = back * (38.0 * smooth(FIRE, 0.3, t) - 8.0 * fall)
    pose["head"] = -6.0 * clench + 10.0 * fall
    m = 18.0 * clench - 10.0 * smooth(FIRE, 0.3, t) + 30.0 * fall
    pose["mand_u"] = -m
    pose["mand_d"] = m
    pose["claw"] = -40.0 * fall
    feet = {}
    for leg, n, s in leg_names():
        hx, hy = hip_of(n, s)
        fx, fy = foot_of(n, s)
        k = lerp(1.0, 0.45, fall) + 0.12 * burst
        feet[leg] = (hx + (fx - hx) * k, hy + (fy - hy) * k)
    return plant(pose, feet)
LAUNCH = 5.0
def launch(t):
    """How far a primary spine has left its root: drawn in on the clench, then out and away."""
    return -1.4 * smooth(0.0, FIRE, t) * (1 - smooth(FIRE, FIRE + 0.04, t)) + LAUNCH * smooth(FIRE, 0.42, t)
def death_extra():
    ex = []
    for name, a, L, prim in SPINES:
        if not prim: continue
        c, s_ = math.cos(R(a)), math.sin(R(a))
        for pid in (name, f"{name}_keel", f"{name}_collar"):
            ex.append((pid, "opacity", lambda t: 1.0 - smooth(FIRE + 0.1, 0.5, t)))
        # the out-along-the-root travel is added on top of the rig's pose below
    ex.append(("ball", "scale", lambda t: 1.0 - 0.07 * smooth(0.0, FIRE, t) + 0.13 * math.sin(math.pi * smooth(FIRE, 0.4, t)) - 0.1 * smooth(0.35, 0.82, t)))
    for pid in ("ball_body", "ball_lit"):
        ex.append((pid, "scale", lambda t: 1.0 - 0.07 * smooth(0.0, FIRE, t) + 0.13 * math.sin(math.pi * smooth(FIRE, 0.4, t)) - 0.1 * smooth(0.35, 0.82, t)))
    ex.append(("organ", "opacity", lambda t: 1.0 - 0.88 * smooth(0.2, 0.8, t)))
    return ex
def death_tracks(ts):
    out = tracks(death_pose, ts, death_extra())
    # The launch: each primary spine (and its keel and collar) slides out along
    # its own bearing. The rig moves them with the ball; this rides on top.
    by = {(tr["part"], tr["prop"]): tr for tr in out}
    for name, a, L, prim in SPINES:
        if not prim: continue
        c, s_ = math.cos(R(a)), math.sin(R(a))
        for pid in (name, f"{name}_keel", f"{name}_collar"):
            for prop, k in (("x", c), ("y", s_)):
                tr = by.get((pid, prop))
                if tr is None:
                    tr = {"part": pid, "prop": prop, "keys": [[r2(t), 0.0] for t in ts], "ease": "linear"}
                    out.append(tr); by[(pid, prop)] = tr
                tr["keys"] = [[kt, r2(v + k * launch(kt))] for kt, v in tr["keys"]]
    return out

animations = {}
TS_TRUNDLE = keyset(12)
animations["trundle"] = {
    "description": "The walk and the idle: six legs in two tripods, each foot planted while the ball rides over it and carried forward tucked in; the ball surges on each push and rocks toward the pushing side, squashing a little on the step; the spines ripple in a wave that runs round the ring once a stride, each laid back and raised in turn, so it reads as rolling along under them; the head nods ahead of the ball and the mandibles work.",
    "duration": 0.62,
    "tracks": tracks(trundle_pose, TS_TRUNDLE, trundle_extra()),
}
TS_DEATH = [0, 0.04, 0.08, 0.11, 0.14, 0.17, 0.2, 0.24, 0.28, 0.32, 0.36, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The shot, drawn: the ball clenches with every spine drawn in and bristling straight out, then the five big spines kick out along their own roots and are gone — the five the game throws in a ring — as the ball bursts after them and the small spurs are flung flat; then it sags, the legs fold in under it, the head drops and the organ goes out. Still from 0.85.",
    "duration": 0.42,
    "tracks": death_tracks(TS_DEATH),
}

# ============================================================== states
variants = {
    "elite": {
        "description": "Marked by the hive: the ball bleached to husk, every spine long and bone-white — the spurs grown to match the five, because a marked burr sheds eight — and a brighter, bigger organ.",
        "scale": 1.25,
        "set": {
            "ball.fill": "$husk.dark",
            "ball_body.fill": "$husk",
            "ball_lit.fill": "$husk.light2",
            "head.fill": "$husk.dark",
            "head_lit.fill": "$husk",
            **{f"{n}.fill": "$bone.light" for n, a, L, p in SPINES},
            **{f"{n}.scale": 1.12 for n, a, L, p in SPINES if p},
            **{f"{n}_keel.scale": 1.12 for n, a, L, p in SPINES if p},
            **{f"{n}.scale": 1.45 for n, a, L, p in SPINES if not p},
            "organ.scale": [0.74, 0.68],
        },
    },
}

DESCRIPTION = (
    "The pan's mid-tier wave body, and the one that is ranged by dying: the game throws five of its spines outward in a ring when it is "
    "killed within reach of the player (EnemyType.deathShots, `ss.enemy.spine`). So it is drawn as the thing it sheds — a chitin ball, "
    "lit on the upper left and shaded on the lower right, carrying five big pale husk spines evenly round it (the five that leave) with a "
    "smaller spur between each pair, a lit organ in a ring of sockets on the back, a small dark head at +x with bone mandibles, and six "
    "legs under. The silhouette is a star, and nothing else in the roster is one. Seen from above, facing +x, mirrored by the game. Built on "
    "a skeleton (scripts/burr.py): the legs are solved to planted feet and every spine is a bone rooted in the ball's rim, so `trundle` "
    "ripples them in a wave running round the ring while the ball rides the step. Gameplay radius 10. `elite` is the bleached, heavier "
    "version the stage-6 marking wears, every spine long and bone-white. The `death` clip is the mechanic drawn: the ball clenches, the "
    "five big spines kick out along their own roots and are gone, and the ball sags under the spurs."
)

doc = {
    "id": "ss.enemy.burr",
    "name": "Burr",
    "description": DESCRIPTION,
    "tags": ["enemy", "burr"],
    "size": [W, H],
    "meta": {"radius": 10},
    "parts": PARTS,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-burr.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(PARTS)} parts, {len(animations)} clips, {n_tracks} tracks")
