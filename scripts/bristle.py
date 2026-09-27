"""The Bristle — a silverfish out of the wall seams.

    python3 scripts/bristle.py        # rewrites apps/ss/assets/ss-enemy-bristle.json

The burrow's fast chaff, in the Flitter's slot. feelers runs it on the seams
(`EnemyType.wallHug` 90, `wallHugSpeedMul` 2): within 90px of a wall it rides
along it at twice its walk, and the skitter is played at that same ×2
(`e.sprite.anims.timeScale = wallHugSpeedMul` while hugging) — the clip rate is
tied to the seam, not to `animTracksSpeed`, which it does not carry. It is
`turnsMirrored`: mirrored for the side and rotated for the rest of its
heading, so the drawing lies along the seam it is running. That makes +x the
travel axis outright — the head and the tail stay on y = 0 at rest.

It was drawn on a skeleton already, and it moved (11px at game scale); what it
lacked was drawing and a death. Rebuilt on the shared rig (`rig.py`):

  - the spine is a chain of six segments running back from the neck — three
    thoracic, three abdominal — each carrying a pale tergite over a darker
    pleuron, so the plates overlap front over back the way a silverfish's
    scales do and the body reads as light over dark rather than as a stack of
    white beads
  - the three caudal filaments stay fused into one plume (five thin rods off a
    small body is an asterisk at this size), now a two-bone chain off the last
    segment with the three prongs cut into its end, so the flick runs out it
  - six short legs on the thorax only, each a femur and a tibia solved to a
    planted foot (two-bone IK) in two alternating tripods, knees up, darker
    than the plates so the body reads first
  - the antennae are three-link chains that whip with a lag down their length

52 parts came down to 35: the nine tergites were two ellipses each, the fan
three stacked copies, and three stray rods and two hairs trailed off it.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 48×28, origin at the centre, +x forward (the travel axis), +y down.
W, H = 48, 28
GROUND = 5.0          # the near feet
FAR_LIFT = 0.9        # the far feet stand this much higher on screen
NECK = (7.4, 0.0)

RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("body", None, NECK, 0.0)
bone("head", "body", NECK, 0.0, 4.8)
# The spine, neck to tail: pro-, meso-, metathorax, then three abdominal
# segments (each standing for three of the animal's, which at this size is
# what can be seen).
SEG_L = [3.3, 3.2, 3.1, 3.0, 2.9, 2.7]
SPINE = RIG.chain("sp", "body", NECK, [(L, 180.0) for L in SEG_L])
TAIL_END = RIG.end_of(SPINE[-1])
PLUME = RIG.chain("pl", SPINE[-1], TAIL_END, [(4.0, 180.0), (5.4, 180.0)])
# Antennae off the front of the head, raked forward and up; the far one a
# little higher and behind the head.
ANT_ROOT = {"n": (11.2, -1.3), "f": (10.8, -1.7)}
ANT_LINKS = {"n": [(3.4, -24.0), (3.3, -10.0), (3.2, 2.0)],
             "f": [(3.2, -38.0), (3.1, -24.0), (3.0, -12.0)]}
for s in ("f", "n"):
    RIG.chain(f"ant_{s}", "head", ANT_ROOT[s], ANT_LINKS[s])
bone("palp", "head", (11.0, 1.2), 62.0, 2.6)

# Legs on the thorax only, one pair per thoracic segment. Each hip rides its
# segment; the femur and tibia are solved to the foot.
LEGS = {  # name: (segment, along the segment, rest foot x, femur, tibia)
    "f": (SPINE[0], 1.4, 8.4, 2.7, 3.0),
    "m": (SPINE[1], 1.5, 3.4, 2.8, 3.1),
    "b": (SPINE[2], 1.6, -2.6, 2.9, 3.2),
}
HIP_DROP = {"n": 1.7, "f": 0.9}   # hip below the spine line, near and far
FAR_DX = -0.5
def hip_rest(side, n):
    seg, along, fx, lf, lt = LEGS[n]
    b = B[seg]
    return (b.at[0] - along + (FAR_DX if side == "f" else 0.0), HIP_DROP[side])
def foot_rest(side, n):
    return (LEGS[n][2] + (FAR_DX if side == "f" else 0.0), GROUND - (FAR_LIFT if side == "f" else 0.0))
def bend(side, n):
    """The knee up: forward feet fold the knee back over the hip, rear feet forward."""
    return 1 if foot_rest(side, n)[0] >= hip_rest(side, n)[0] else -1
LEG_IDS = [(s, n) for s in ("f", "n") for n in ("b", "m", "f")]
for s, n in LEG_IDS:
    seg, along, fx, lf, lt = LEGS[n]
    hip, foot = hip_rest(s, n), foot_rest(s, n)
    hf, ht = ik(hip, foot, lf, lt, bend(s, n))
    bone(f"{s}{n}_femur", seg, hip, hf, lf)
    bone(f"{s}{n}_tibia", f"{s}{n}_femur", B[f"{s}{n}_femur"].end(), ht, lt)

RIG.seal()
solve, put, on_bone = RIG.solve, RIG.put, RIG.on_bone

# ============================================================== parts
def rel(pts, o): return [(x - o[0], y - o[1]) for x, y in pts]

# The body's side profile: how far the back rises above the spine line and
# the belly falls below it, at x. Long and low — a silverfish.
TOP = [(-11.6, 1.0), (-8.0, 1.5), (-4.0, 2.0), (0.0, 2.35), (4.0, 2.45), (8.0, 2.3)]
BELLY = [(-11.6, 0.75), (-8.0, 1.1), (-4.0, 1.5), (0.0, 1.8), (8.0, 1.8)]
def table(tb, x):
    if x <= tb[0][0]: return tb[0][1]
    for (x0, y0), (x1, y1) in zip(tb, tb[1:]):
        if x <= x1: return lerp(y0, y1, (x - x0) / (x1 - x0))
    return tb[-1][1]
def top(x): return table(TOP, x)
def belly(x): return table(BELLY, x)
def plate(xf, xb, frac):
    """A plate from xf back to xb (xb < xf), overlapping the next one behind by 1.0: the upper `frac` of the side or all of it."""
    xe = xb - 1.0
    xs = [lerp(xf + 0.2, xe, k / 4) for k in range(5)]
    up = [(x, -top(x)) for x in xs]
    lo = [(x, -top(x) + frac * (top(x) + belly(x))) for x in xs]
    # The rear edge swept back at the top, the way scales lie: the back of
    # each plate is a chevron over the one behind, not a vertical cut.
    mid_y = (up[-1][1] + lo[-1][1]) / 2
    lo = [(x + 0.9 * frac * k / 4, y) for k, (x, y) in enumerate(lo)]
    return up + [(xe - 0.35, lerp(up[-1][1], mid_y, 0.5))] + [(xe + 0.2, mid_y + 0.3 * frac)] + lo[::-1]

# The plates and the plume are rimmed in dark steel rather than ink: on a
# floor as dark as the burrow's an ink rim is the floor's own colour and only
# shows where plate lies over plate, and there a black line on every segment
# is a zebra, not a silverfish. The legs, the thin parts, keep the ink.
RIM = {"color": "$steel.dark2", "width": "hair"}

# ---- far side first: legs, then the far antenna
def leg_parts(s, n, femur, tibia, stroke):
    at, a = on_bone(f"{s}{n}_tibia"); put(f"leg_{s}{n}_tibia", f"{s}{n}_tibia", at, a, bar(B[f"{s}{n}_tibia"].length, 0.95, 0.5, 0.3), tibia, stroke)
    at, a = on_bone(f"{s}{n}_femur"); put(f"leg_{s}{n}_femur", f"{s}{n}_femur", at, a, bar(B[f"{s}{n}_femur"].length, 1.3, 0.95, 0.45), femur, stroke)
for n in ("b", "m", "f"):
    leg_parts("f", n, "$steel.dark2", "$slate", None)
for i in range(3):
    nm = f"ant_f_{i}"
    at, a = on_bone(nm)
    put(nm, nm, at, a, bar(B[nm].length, 0.75 - 0.15 * i, 0.6 - 0.15 * i, 0.3), "$steel.dark2")

# ---- the plume: base wedge, then the three prongs in one outline
at, a = on_bone("pl_0")
put("plume_0", "pl_0", at, 0.0, poly(rel([(TAIL_END[0] + 0.6, -0.8), (TAIL_END[0] - 2.0, -0.95), (TAIL_END[0] - 4.6, -1.25),
                                          (TAIL_END[0] - 4.6, 1.25), (TAIL_END[0] - 2.0, 0.95), (TAIL_END[0] + 0.6, 0.8)], at)),
    "$steel.light", RIM)
at1, _ = on_bone("pl_1")
x0 = at1[0]
PRONGS = [(x0 + 0.5, -1.2), (x0 - 2.6, -2.2), (x0 - 6.0, -3.9), (x0 - 6.3, -3.5), (x0 - 3.2, -1.3),   # the upper cercus
          (x0 - 3.0, -0.45), (x0 - 7.4, -0.2), (x0 - 7.4, 0.2), (x0 - 3.0, 0.45),                      # the median filament
          (x0 - 3.2, 1.3), (x0 - 6.3, 3.5), (x0 - 6.0, 3.9), (x0 - 2.6, 2.2), (x0 + 0.5, 1.2)]       # the lower cercus
put("plume_1", "pl_1", at1, 0.0, poly(rel(PRONGS, at1)), "$silent.dark", RIM)
put("plume_core", "pl_0", at, 0.0, poly(rel([(TAIL_END[0] + 0.4, -0.3), (x0 + 0.6, -0.5), (x0 - 0.6, 0.0), (x0 + 0.6, 0.5), (TAIL_END[0] + 0.4, 0.3)], at)),
    "$silent")

# ---- the body, tail first so each plate lies over the one behind it
PLATE_IDS = []
for i in reversed(range(len(SPINE))):
    b = B[SPINE[i]]
    xf, xb = b.at[0], b.end()[0]
    at = (xf, 0.0)
    put(f"pleura_{i}", SPINE[i], at, 0.0, poly(rel(plate(xf, xb, 1.0), at)), "$steel", RIM)
    put(f"terg_{i}", SPINE[i], at, 0.0, poly(rel(plate(xf, xb, 0.58), at)), "$silent")
    PLATE_IDS.append(i)
# A sheen along the thorax, and the hive's organ it stole, on its back.
at, _ = on_bone(SPINE[1], 0.9)
put("sheen", SPINE[1], (at[0], -1.55), -2.0, ell(3.0, 0.42), "$white@heavy")
at, _ = on_bone(SPINE[2], 1.4)
RIG.use("organ", SPINE[2], (at[0], -2.2), "ss.lib.organ", scale=0.3)

# ---- the head: a low rounded capsule, the eye, a palp, the near antenna
HEAD = [(6.6, -2.3), (8.6, -2.35), (10.4, -1.9), (11.8, -0.9), (12.5, 0.2), (12.0, 1.1), (10.4, 1.7), (8.2, 1.9), (6.6, 1.8)]
put("head", "head", NECK, 0.0, poly(rel(HEAD, NECK)), "$silent", RIM)
put("brow", "head", (9.0, -1.45), -6.0, ell(2.0, 0.5), "$white")
put("eye", "head", (10.3, -0.55), -14.0, ell(0.95, 0.8), "$ink")
at, a = on_bone("palp")
put("palp", "palp", at, a, bar(B["palp"].length, 0.8, 0.5, 0.3), "$steel.dark2")
for i in range(3):
    nm = f"ant_n_{i}"
    at, a = on_bone(nm)
    put(nm, nm, at, a, bar(B[nm].length, 1.0 - 0.15 * i, 0.8 - 0.15 * i, 0.3), "$steel.dark")

# ---- near legs over everything
for n in ("b", "m", "f"):
    leg_parts("n", n, "$steel.dark", "$steel.dark2", None)

RIG.check()
STILL = {"eye", "organ"}

# ============================================================== motion
tracks = RIG.tracks

def plant(pose, feet):
    world = solve(pose)
    for s, n in LEG_IDS:
        seg, along, fx, lf, lt = LEGS[n]
        hx, hy, _ = world[f"{s}{n}_femur"]
        hf, ht = ik((hx, hy), feet[(s, n)], lf, lt, bend(s, n))
        pose[f"abs:{s}{n}_femur"] = hf
        pose[f"abs:{s}{n}_tibia"] = ht
    return pose

# ---- skitter: the idle and the run, one stride of two tripods a loop. On a
# seam the game plays it at ×2, so the same drawing is the sprint.
TRIPOD = {("n", "f"): 0.0, ("f", "m"): 0.0, ("n", "b"): 0.0, ("f", "f"): 0.5, ("n", "m"): 0.5, ("f", "b"): 0.5}
STRIDE = 2.3
def step(t, ph):
    u = (t + ph) % 1.0
    if u < 0.5:
        return lerp(STRIDE, -STRIDE, u / 0.5), 0.0
    v = (u - 0.5) / 0.5
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 2.2 * math.sin(math.pi * v)
SPINE_AMP = [1.5, 2.0, 2.8, 3.8, 5.0, 6.0]
def skitter_pose(t):
    # Two pushes a loop: a bob and a surge off each tripod, the nose pitching after them.
    bob = 0.45 * (0.5 - 0.5 * math.cos(4 * math.pi * t))
    pose = {"body": (0.8 * cyc(2 * t, 0.1), -bob, 1.4 * cyc(2 * t, 0.18))}
    pose["head"] = -2.5 * cyc(2 * t, 0.1)
    # The wave from the neck back, later and larger down the chain; the plume
    # takes the most of it and gets there last.
    for i, sp in enumerate(SPINE):
        pose[sp] = SPINE_AMP[i] * cyc(t, -0.06 * i)
    pose["pl_0"] = 11.0 * cyc(t, -0.4)
    pose["pl_1"] = 15.0 * cyc(t, -0.52)
    for s, ph in (("n", 0.0), ("f", 0.3)):
        for i in range(3):
            pose[f"ant_{s}_{i}"] = (7.0 + 5.0 * i) * cyc(2 * t, ph - 0.12 * i)
    pose["palp"] = 18.0 * cyc(2 * t, 0.25)
    feet = {}
    for s, n in LEG_IDS:
        dx, lift = step(t, TRIPOD[(s, n)])
        fx, fy = foot_rest(s, n)
        feet[(s, n)] = (fx + dx, fy - lift)
    return plant(pose, feet)

# ---- death: 0.34s. A jolt that arches the back and throws the plume up, then
# a curl that runs neck to tail — the head tucking, each segment folding a
# little after the one before, the plume swung down and under — the legs
# kicking once and drawn in, the antennae and palp dropping. It settles on its
# side of the curl by 0.85 and holds.
def death_pose(t):
    jolt = math.sin(math.pi * smooth(0.0, 0.26, t))
    curl = [smooth(0.14 + 0.05 * i, 0.62 + 0.03 * i, t) for i in range(len(SPINE))]
    settle = smooth(0.62, 0.85, t)
    pose = {"body": (-0.8 * jolt, -1.0 * jolt + 0.6 * smooth(0.2, 0.75, t), -3.0 * jolt + 3.0 * smooth(0.2, 0.8, t))}
    pose["head"] = -8.0 * jolt + 22.0 * smooth(0.12, 0.6, t) - 4.0 * settle
    for i, sp in enumerate(SPINE):
        pose[sp] = 2.0 * jolt - (3.0 + 0.4 * i) * curl[i] * (1.15 - 0.15 * settle)
    pose["pl_0"] = 12.0 * jolt - 2.0 * smooth(0.3, 0.8, t)
    pose["pl_1"] = 10.0 * jolt + 6.0 * smooth(0.35, 0.85, t)
    for s in ("n", "f"):
        for i in range(3):
            pose[f"ant_{s}_{i}"] = -8.0 * jolt + (22.0 - 4.0 * i) * smooth(0.2, 0.8, t)
    pose["palp"] = 40.0 * smooth(0.2, 0.7, t)
    kick = math.sin(math.pi * smooth(0.0, 0.3, t))
    fold = smooth(0.25, 0.8, t)
    world = solve(pose)
    feet = {}
    for s, n in LEG_IDS:
        fx, fy = foot_rest(s, n)
        fx += (1.6 if TRIPOD[(s, n)] == 0 else -1.6) * kick
        hx, hy, _ = world[f"{s}{n}_femur"]
        # drawn in: the foot halfway to the hip and tucked up under the plates
        feet[(s, n)] = (lerp(fx, hx + 0.4, fold * 0.7), lerp(fy, hy + 2.2, fold))
    return plant(pose, feet)

animations = {}
animations["skitter"] = {
    "description": "The fastest gait on the roster, and the body does most of it — the idle, and on a seam the game plays it at twice the rate. Six short legs in two alternating tripods, each foot planted while the body rides over it and snatched forward; the body bobs and surges off each push and the nose pitches after it; a wave runs the spine from the neck back, later and larger down the chain, and the plume takes the most of it and flicks last; the antennae whip with a lag down their links and the palp works. Sampled twelve times and interpolated straight, so the run never stops at a key.",
    "duration": 0.34,
    "tracks": tracks(skitter_pose, keyset(12), still=STILL),
}
DEATH_TS = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The one body down here that is not hive, so it dies like an insect and not like a light going out: a jolt arches the back and throws the plume up, then a curl runs neck to tail — the head tucks, each plate folds a beat after the one before, the plume swings down and under — while the legs kick once and draw in under the plates and the antennae and palp drop. The stolen signal on its back goes out. Still from 0.85.",
    "duration": 0.34,
    "tracks": tracks(death_pose, DEATH_TS, [
        ("organ", "opacity", lambda t: 1.0 - 0.9 * smooth(0.2, 0.8, t)),
        ("organ", "scale", lambda t: 1.0 - 0.5 * smooth(0.2, 0.8, t)),
        ("eye", "scale", lambda t: 1.0 - 0.35 * smooth(0.3, 0.8, t)),
    ], still=STILL),
}

# ============================================================== states
elite_set = {f"terg_{i}.fill": "$white" for i in range(4)}
elite_set.update({f"terg_{i}.fill": "$silent" for i in range(4, 6)})
elite_set.update({
    "pleura_0.fill": "$steel.light", "pleura_1.fill": "$steel.light", "pleura_2.fill": "$steel.light",
    "head.fill": "$silent", "brow.fill": "$white",
    "plume_0.fill": "$silent.dark", "plume_1.fill": "$silent", "plume_core.fill": "$white",
    "plume_1.scale": [1.0, 1.2],
    "organ.scale": 0.42,
})
variants = {
    "elite": {
        "description": "Marked: the plates bleach past bone, the plume opens wider and brighter than the body dragging it, and the signal it stole off the trail is burning on its own back.",
        "scale": 1.25,
        "set": elite_set,
    },
}

# ============================================================== document
DESCRIPTION = (
    "The burrow's fast chaff — a silverfish out of the wall seams, running the nest's trails and stealing off them, the one thing down here that does not "
    "belong to the hive. Drawn from the side, along +x, and both mirrored and rotated by the game (EnemyType.turnsMirrored): the mirror picks the side it "
    "faces and the rotation carries the rest of its heading, so it lies along the seam it is running and still stands on its feet. The rest pose's travel "
    "axis is +x itself — head and tail level on y = 0 — so it needs no faceOffset. Long and low, because that is what a silverfish is: a flat body of six "
    "overlapping plates, pale tergites over steel pleura, tapering from a rounded head to a plume — the three caudal filaments fused into one outline with "
    "the three prongs cut into its end, since five thin rods off a small body is an asterisk at the size this is seen at. The silhouette is a comet: long "
    "antennae forward, the plume trailing, six short dark legs on the thorax. "
    "Built on a skeleton (scripts/bristle.py): the spine is a chain of six segments off the neck, the plume two more off the tail, the antennae chains of "
    "three; every leg hip rides the segment it grows from and the leg is solved to a planted foot. `skitter` is the idle and the run, and the game plays "
    "it at twice the rate on a seam (wallHugSpeedMul), so the wall shows in the legs as well as in the ground covered. Cool silver against a roster of "
    "warm bone and amber so it never competes with the Replete or the Porter's brood, and the palest body on it — the quickest thing on screen must not be "
    "the hardest to see. Gameplay radius 7. The `death` clip is the only one in the roster that is not a light going out: it dies like an insect — a jolt, "
    "a curl running neck to tail, the legs drawn in under the plates."
)

doc = {
    "id": "ss.enemy.bristle",
    "name": "Bristle",
    "description": DESCRIPTION,
    "tags": ["enemy", "bristle"],
    "size": [W, H],
    "meta": {"radius": 7},
    "parts": RIG.parts,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-bristle.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
