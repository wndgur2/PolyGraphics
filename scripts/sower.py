"""The Sower — a wasp that carries its young to you and lets them go.

    python3 scripts/sower.py        # rewrites apps/ss/assets/ss-enemy-sower.json

The Gland's other turn on the pan: it stands off at 380 and every 3.6s lets
one of the ticks it carries go (feelers: `EnemyType.shotTex: 'e_tick'`,
`shotTurn`) — and the tick, not the wasp, does the hunting. So nothing on it
points; the read is a body *carrying* live cargo, and the cargo is the threat.

It was hand-placed and it moved about three pixels at game scale: six legs
swinging a few degrees about their own centres under a body that never went
anywhere, and the young tucked behind the abdomen where nobody could see them.
This rebuilds it on the rig (scripts/rig.py) as what the clip was always
called — a *drift*, a loaded wasp labouring through the air:

  - a skeleton: the thorax is the root and carries the head (a neck that
    nods), the wings (hinged at the shoulder), six dangling legs (femur, tibia,
    tarsus, each hanging off the last), the elbowed antennae, and the waist —
    a petiole, the gaster hung off it, the ovipositor off the gaster's tip and
    the three young off the gaster's belly, so the whole back half swings as a
    chain behind the thorax
  - `drift` is two heavy wing-beats a loop: every downstroke lifts the body,
    and everything that hangs off it — gaster, ovipositor, the young, the legs,
    the antennae — answers late, a wave running out from the thorax

Seen side-on facing +x and mirrored by the game. Pale arcane, lighter than
the old body, so it stands off the pan's mid-brown sand (it sank at 1.44);
banded in orchid, and the young (`use: ss.enemy.tick`, the very shot it
fires) ride in a row under the belly in plain sight.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, cyc_c, keyset,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 64×48, origin at the centre, +x forward, +y down.
RIG = Rig()
B = RIG.bones
bone = RIG.bone

THORAX = (4.0, -2.0)
bone("thorax", None, THORAX, 0.0)
bone("head", "thorax", (9.2, -2.6), 0.0, 3.0)
# The waist and what hangs off it: petiole, gaster, ovipositor.
PETIOLE = (-0.6, -0.4)
bone("petiole", "thorax", PETIOLE, 164.0, 4.2)
bone("gaster", "petiole", B["petiole"].end(), 172.0, 16.0)
bone("ovi", "gaster", B["gaster"].end(), 150.0, 8.0)
# The young, each hanging off a point on the gaster's belly.
TICKS = {  # name: (distance along the gaster, its hold on the belly)
    "tick_a": (3.4, (-5.2, 5.4)),
    "tick_b": (8.2, (-10.2, 6.0)),
    "tick_c": (12.6, (-14.8, 5.4)),
}
for n, (along, at) in TICKS.items():
    bone(n, "gaster", at, 90.0, 1.0)
# Wings from the shoulder, laid back and up.
WING_ROOT = (3.2, -6.6)
WING_FAR_ROOT = (4.6, -7.0)
WING_REST, WING_FAR_REST = 196.0, 204.0
bone("wing", "thorax", WING_ROOT, WING_REST, 17.0)
bone("wing_far", "thorax", WING_FAR_ROOT, WING_FAR_REST, 15.0)
# Antennae: an elbowed scape and a long flagellum, off the top of the head.
bone("ant_0", "head", (12.4, -5.6), -64.0, 3.8)
bone("ant_1", "ant_0", B["ant_0"].end(), -8.0, 7.2)
bone("antf_0", "head", (11.4, -5.8), -76.0, 3.4)
bone("antf_1", "antf_0", B["antf_0"].end(), -24.0, 6.4)
# Legs: hips under the thorax, hanging in flight — the fore pair reaching
# forward, the hind pair trailing, each a femur, a tibia and a tarsus.
LEGS = {  # name: (hip, femur heading, tibia heading, tarsus heading, femur, tibia, tarsus)
    "f": ((7.6, 1.6), 64.0, 112.0, 70.0, 4.0, 4.4, 2.4),
    "m": ((4.6, 2.4), 86.0, 128.0, 100.0, 4.4, 5.0, 2.6),
    "b": ((1.8, 2.0), 112.0, 150.0, 170.0, 5.0, 6.2, 3.0),
}
FAR_OFF = (1.4, -1.2)  # the far legs start a little behind and above
for side in ("near", "far"):
    for leg, (hip, hf, ht, hs, lf, lt, ls) in LEGS.items():
        n = f"{side}_{leg}"
        h = hip if side == "near" else (hip[0] + FAR_OFF[0], hip[1] + FAR_OFF[1])
        d = 0.0 if side == "near" else -8.0
        bone(f"{n}_femur", "thorax", h, hf + d, lf)
        bone(f"{n}_tibia", f"{n}_femur", B[f"{n}_femur"].end(), ht + d, lt)
        bone(f"{n}_tarsus", f"{n}_tibia", B[f"{n}_tibia"].end(), hs + d, ls)
RIG.seal()
put, on_bone = RIG.put, RIG.on_bone

def wpoly(at, pts):
    """A polygon given in world coordinates, as a shape about `at`."""
    return poly([(x - at[0], y - at[1]) for x, y in pts])

def along(name, a, c=0.0):
    return on_bone(name, a, c)[0]

# ============================================================== parts
# Three values: the pale lit body (arcane.light / light2), the mid bands and
# shadow side (orchid, arcane), the darks — legs, eye, ovipositor sheath.
HAIR_DARK = {"color": "$arcane.dark2", "width": "hair"}

def leg_parts(n, femur, tibia, tarsus, stroke):
    for seg, fill, w0, w1 in (("tarsus", tarsus, 0.9, 0.6), ("tibia", tibia, 1.2, 1.0), ("femur", femur, 1.6, 1.3)):
        at, a = on_bone(f"{n}_{seg}")
        put(f"{n}_{seg}", f"{n}_{seg}", at, a, bar(B[f"{n}_{seg}"].length, w0, w1, 0.5), fill, stroke)

def wing(id, bn, fill, vein, stroke):
    L = B[bn].length
    at, a = on_bone(bn)
    put(id, bn, at, a, poly([(-0.6, -0.6), (2.4, -2.1), (7.0, -2.9), (L * 0.78, -2.6), (L - 0.4, -1.4), (L + 0.4, 0.2),
                             (L - 1.0, 1.4), (L * 0.6, 2.0), (3.0, 1.5), (-0.6, 0.6)]), fill, stroke)
    at2, _ = on_bone(bn, L * 0.46, -0.9)
    put(f"{id}_vein", bn, at2, a, rect(L * 0.78, 0.5, 0.25), vein)
    at3, _ = on_bone(bn, 3.0, 0.2)
    put(f"{id}_stigma", bn, at3, a, ell(1.6, 0.8), vein)

# ---- far side: wing, legs, antenna — a step darker, behind everything
wing("wing_far", "wing_far", "$heather@0.4", "$arcane.dark@soft", {"color": "$silent@soft", "width": "hair"})
for leg in ("b", "m", "f"):
    leg_parts(f"far_{leg}", "$arcane.light", "$arcane.light", "$arcane", None)
for i, w in ((0, 1.1), (1, 0.8)):
    at, a = on_bone(f"antf_{i}")
    put(f"antf_{i}", f"antf_{i}", at, a, bar(B[f"antf_{i}"].length, w, w * 0.8, 0.4), "$arcane")

# ---- the ovipositor: a bone blade under a dark sheath, trailing from the tip
at, a = on_bone("ovi")
put("ovipositor", "ovi", at, a, poly([(-1.0, -1.1), (3.0, -0.9), (8.0, -0.3), (9.4, 0.3), (7.6, 0.6), (3.0, 1.0), (-1.0, 1.2)]),
    "$bone", INK_HAIR)
put("ovi_sheath", "ovi", at, a, poly([(-1.0, -1.1), (3.2, -0.8), (4.2, 0.0), (3.2, 0.9), (-1.0, 1.2)]), "$arcane.dark2")

# ---- the gaster: a teardrop off the waist, lit on top, orchid bands
G0 = B["gaster"].at
GASTER = [(-4.2, -0.4), (-5.4, -3.2), (-8.2, -4.8), (-12.0, -4.8), (-16.0, -3.6), (-19.6, -1.2), (-21.6, 1.4),
          (-21.2, 3.2), (-18.0, 4.8), (-13.0, 6.2), (-8.4, 6.2), (-5.2, 4.4), (-4.0, 1.8)]
put("gaster", "gaster", G0, 0.0, wpoly(G0, GASTER), "$arcane.light2", INK_HAIR)
put("gaster_shade", "gaster", G0, 0.0, wpoly(G0, [(-4.6, 2.8), (-8.4, 5.6), (-13.0, 5.6), (-18.0, 4.2), (-20.8, 2.4),
                                                    (-18.0, 3.0), (-13.0, 3.6), (-8.0, 3.4)]), "$arcane.light")
for i, (x, top, bot) in enumerate(((-7.6, -4.6, 6.0), (-11.6, -4.8, 6.1), (-15.6, -3.8, 5.0), (-19.0, -1.8, 3.6))):
    put(f"band_{i}", "gaster", (x, (top + bot) / 2), 10.0, rect(1.3, bot - top - 0.4, 0.65), "$orchid.light")
put("gaster_gloss", "gaster", (-11.8, -2.4), -5.0, ell(7.4, 1.9), "$white@0.45")

# ---- the young, riding under the belly in a row, heads forward, holding on
for n, s, r in (("tick_c", 0.68, -24.0), ("tick_b", 0.72, -14.0), ("tick_a", 0.68, -6.0)):
    at = B[n].at
    RIG.use(n, n, (at[0], at[1] + 2.0), "ss.enemy.tick", scale=[s, s], rot=r)

# ---- the waist, the thorax, the organ on its back
P0 = B["petiole"].at
put("petiole", "petiole", P0, 0.0, wpoly(P0, [(0.4, -1.2), (-1.8, -0.6), (-3.4, 0.2), (-3.4, 1.4), (-1.8, 1.2), (0.4, 0.8)]),
    "$arcane.light", INK_HAIR)
THX = [(-0.8, -1.6), (0.4, -4.8), (3.4, -7.2), (7.0, -7.0), (9.6, -4.6), (10.2, -1.4), (9.0, 1.6), (5.6, 3.2), (1.6, 2.8), (-0.6, 0.8)]
put("thorax", "thorax", THORAX, 0.0, wpoly(THORAX, THX), "$arcane.light2", INK_HAIR)
put("thorax_shade", "thorax", THORAX, 0.0, wpoly(THORAX, [(0.4, 0.8), (3.0, 0.4), (6.4, 0.6), (9.4, -0.4), (9.0, 1.6),
                                                          (5.6, 3.0), (1.6, 2.6)]), "$arcane.light")
put("scutum", "thorax", (5.4, -4.4), -8.0, ell(3.8, 1.8), "$white@0.45")
RIG.use("organ", "thorax", (4.2, -3.6), "ss.lib.organ", scale=[0.48, 0.42])

# ---- the head: a round capsule with a big compound eye, jaws under it
HEAD = (12.6, -2.2)
put("head", "head", HEAD, 0.0, wpoly(HEAD, [(9.4, -3.6), (11.0, -6.0), (13.8, -6.4), (16.0, -4.6), (16.8, -1.6),
                                          (16.0, 1.2), (13.6, 2.4), (10.8, 1.8), (9.2, -0.6)]), "$arcane.light2", INK_HAIR)
put("head_gloss", "head", (14.2, -4.8), 20.0, ell(1.6, 0.9), "$white@0.45")
put("eye", "head", (12.8, -2.4), 8.0, ell(2.0, 2.9), "$ink")
put("eye_glint", "head", (12.3, -3.8), 0.0, circ(0.6), "$silent")
put("clypeus", "head", (15.6, 0.0), 0.0, ell(1.1, 1.2), "$orchid")
put("mandible", "head", (15.2, 1.2), 0.0, wpoly((15.2, 1.2), [(14.2, 0.8), (16.6, 1.0), (18.0, 2.2), (16.4, 2.8), (14.6, 2.2)]),
    "$arcane.dark2")
for i, w in ((0, 1.2), (1, 0.9)):
    at, a = on_bone(f"ant_{i}")
    put(f"ant_{i}", f"ant_{i}", at, a, bar(B[f"ant_{i}"].length, w, w * 0.8, 0.4), "$arcane")

# ---- near legs over the body, the near wing over everything
for leg in ("b", "m", "f"):
    leg_parts(f"near_{leg}", "$arcane.light2", "$arcane.light", "$arcane", INK_HAIR)
wing("wing", "wing", "$silent@0.45", "$arcane.dark@soft", {"color": "$silent@heavy", "width": "hair"})

RIG.check()

# ============================================================== motion
tracks = RIG.tracks
LEG_NAMES = [f"{s}_{l}" for s in ("near", "far") for l in ("f", "m", "b")]
LEG_PH = {"near_f": 0.0, "near_m": 0.12, "near_b": 0.24, "far_f": 0.5, "far_m": 0.62, "far_b": 0.74}

def beat(t):
    """The wing's stroke, two a loop: -1 at the top of the upstroke, +1 at the bottom of the downstroke."""
    return -cyc_c(2 * t)

def drift_pose(t):
    # Every downstroke lifts the body — the rise lags the stroke a little —
    # and a once-a-loop pitch rocks it nose-down and back as it labours on.
    lift = -cyc_c(2 * t, -0.08)  # +1 lowest, -1 highest
    pose = {"body": (0.9 * cyc(t, 0.1), 1.9 * lift, 3.0 * cyc(t, 0.0))}
    pose["wing"] = 42.0 * beat(t) - 6.0
    pose["wing_far"] = 38.0 * beat(t - 0.03) - 6.0
    pose["head"] = -3.0 * cyc(t, -0.05)
    # The back half as a wave out from the waist: the petiole, then the gaster
    # a beat later, the ovipositor later still.
    pose["petiole"] = 5.0 * cyc(t, -0.14)
    pose["gaster"] = 9.0 * cyc(t, -0.22)
    pose["ovi"] = 16.0 * cyc(t, -0.36)
    for i, n in enumerate(("tick_a", "tick_b", "tick_c")):
        pose[n] = 14.0 * cyc(t, -0.3 - 0.08 * i)
    # The legs hang and paddle, each joint after the one above it.
    for n in LEG_NAMES:
        ph = LEG_PH[n]
        hind = 1.4 if n.endswith("_b") else 1.0
        pose[f"{n}_femur"] = 16.0 * hind * cyc(t, ph)
        pose[f"{n}_tibia"] = 20.0 * hind * cyc(t, ph - 0.12)
        pose[f"{n}_tarsus"] = 24.0 * cyc(t, ph - 0.24)
    pose["ant_0"] = 8.0 * cyc(t, -0.18)
    pose["ant_1"] = 14.0 * cyc(t, -0.32)
    pose["antf_0"] = 8.0 * cyc(t, -0.22)
    pose["antf_1"] = 14.0 * cyc(t, -0.36)
    return pose

# ---- death: a last stroke, then it drops — wings fold down the back, the
# body falls and rolls nose-down, the legs curl in, the young let go and
# scatter off the belly, and the organ goes out. Still from 0.85.
def death_pose(t):
    jolt = math.sin(math.pi * smooth(0.0, 0.22, t))
    fall = smooth(0.12, 0.7, t)
    land = smooth(0.62, 0.8, t)
    pose = {"body": (-1.2 * fall, -2.0 * jolt + 9.0 * fall - 0.8 * math.sin(math.pi * land), -10.0 * jolt + 18.0 * fall)}
    pose["wing"] = -40.0 * jolt + lerp(0.0, 20.0, fall)
    pose["wing_far"] = -36.0 * jolt + lerp(0.0, 18.0, fall)
    pose["head"] = 14.0 * fall
    pose["petiole"] = -6.0 * jolt + 10.0 * fall
    pose["gaster"] = -8.0 * jolt - 14.0 * fall
    pose["ovi"] = 20.0 * jolt - 30.0 * fall
    for n in LEG_NAMES:
        pose[f"{n}_femur"] = -26.0 * fall
        pose[f"{n}_tibia"] = -50.0 * fall
        pose[f"{n}_tarsus"] = -40.0 * fall
    pose["ant_0"] = 18.0 * fall
    pose["ant_1"] = 40.0 * fall
    pose["antf_0"] = 14.0 * fall
    pose["antf_1"] = 34.0 * fall
    return pose

# The young let go on their own: they fall to the sand under where it drops
# and scatter, each its own way, and stay (they are live shots in the game).
SCATTER = {"tick_a": (5.0, 13.0, 50.0), "tick_b": (-2.0, 14.0, -30.0), "tick_c": (-8.0, 12.0, 160.0)}
LET_GO = 0.2
def ticks_free():
    """x/y/rot tracks for the young: riding the body until they let go at LET_GO, then their own fall to the sand."""
    rest = RIG.posed_parts({})
    held = RIG.posed_parts(death_pose(LET_GO))
    def ride(t, n):
        return RIG.posed_parts(death_pose(t))[n] if t < LET_GO else held[n]
    out = []
    for n, (dx, dy, spin) in SCATTER.items():
        def fx(t, n=n, dx=dx):
            return lerp(ride(t, n)[0] - rest[n][0], dx, smooth(LET_GO, 0.62, t))
        def fy(t, n=n, dy=dy):
            u = smooth(LET_GO, 0.62, t)
            return lerp(ride(t, n)[1] - rest[n][1], dy, u) - 3.0 * math.sin(math.pi * u)
        def fr(t, n=n, spin=spin):
            return lerp(ride(t, n)[2] - rest[n][2], spin, smooth(LET_GO, 0.7, t))
        out += [(n, "x", fx), (n, "y", fy), (n, "rot", fr)]
    return out

animations = {}
TS_DRIFT = keyset(24)
animations["drift"] = {
    "description": "The loaded wasp labouring through the air: two heavy wing-beats a loop, the body lifting on each downstroke and rocking nose-down and back once a loop; everything that hangs off it answers late as a wave out from the thorax — the gaster swings on its waist, the ovipositor after it, the three young riding the belly sway after that, and the dangling legs paddle joint by joint.",
    "duration": 0.6,
    "tracks": tracks(drift_pose, TS_DRIFT),
}
TS_DEATH = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
death_tracks = [tr for tr in tracks(death_pose, TS_DEATH) if tr["part"] not in SCATTER]
death_tracks += tracks(lambda t: {}, TS_DEATH, ticks_free() + [
    ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.1, 0.6, t)),
    ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.2, 0.55, t)),
])
animations["death"] = {
    "description": "A last stroke, then it drops: the wings fold down the back, the body falls and rolls nose-down onto the sand, the legs curl in under it and the gaster folds; the three young let go of the belly on the way down and scatter, each its own way. The organ goes out. Still from 0.85.",
    "duration": 0.46,
    "tracks": death_tracks,
}

# ============================================================== document
DESCRIPTION = (
    "The other turn of the Gland's slot: a wasp seen side-on, pale arcane purple banded in orchid, thin at the waist, with a bone ovipositor "
    "trailing from the tip of the gaster and three of its young — `use: ss.enemy.tick`, the very shot it fires — riding in a row under the belly. "
    "The wings are pale washes over the back. It does not aim (EnemyType.shotTurn: what it lets go turns toward the player on its own), so "
    "nothing on it points; the read is a body carrying live cargo, and the cargo is the threat. Purple, because nothing else on the pan is, "
    "and because the tick is; lit pale so it stands off the sand. "
    "Built on a skeleton (scripts/sower.py): the thorax carries the head, the wings, six dangling three-jointed legs and the waist, and the "
    "gaster, the ovipositor and the young hang off the waist as a chain, so the back half swings behind the body rather than beside it. "
    "`drift` is the flight — two heavy wing-beats a loop, the body lifting on each downstroke and everything hanging off it answering late. "
    "No `elite` variant: a squad body is never marked. Drawn facing +x, mirrored by the game. Gameplay radius 11. The `death` clip drops "
    "it to the sand with the wings folded and lets the young go."
)

doc = {
    "id": "ss.enemy.sower",
    "name": "Sower",
    "description": DESCRIPTION,
    "tags": ["enemy", "sower"],
    "size": [64, 48],
    "meta": {"radius": 11},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-sower.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
