"""The Flitter — the hive's scout, a pale pair of wings with a trail behind it.

    python3 scripts/bat.py        # rewrites apps/ss/assets/ss-enemy-bat.json

feelers calls it the Flitter (`bat`, Vermis acetum): fast, frail, and it does
not chase — it reads your heading and cuts across it. It is side-on, facing
+x and mirrored by the game (no `turns`), so the drawing is a flier seen from
the side, and its one loop, `flit`, is the whole of what it does.

It was two pale ellipses on each side of a dark ellipse, turned a little about
their own centres, and it measured 7.1px at game scale (scripts/motion.ts):
the wings had a root and a tip but swung a few degrees, and the body only
rocked. This rebuilds it on the rig (scripts/rig.py):

  - a skeleton: the thorax is the root, the head rides it on a neck, the
    abdomen hangs off its back as a two-link chain with the sting on the end
    and the trail (`ss.lib.wisp`) riding the sting, so the whole back half
    trails the body's motion as a wave
  - each wing is a root and a tip hinged at the shoulder and at a wrist, like
    a bat's hand: the membrane between them is two shapes that meet at the
    joint, so the wing can bend in the middle of a stroke without coming
    apart
  - `flit` is one full stroke: the wings flung up over the back and driven
    down past the belly, the tip lagging the root on the way down and the way
    up (the wrist leads, the membrane follows); every downstroke lifts the
    body, which pitches after it, the abdomen swings after that and the trail
    swings last

The wings carry the read, as they always did — a wide pale shape against the
Mite's compact amber blob — and now they sweep through most of a right angle
every beat. Husk membranes over a small dark-amber body, the far wing in the
cool grey it was (steel), the organ underneath.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, cyc_c, wrap, keyset,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 44×40 (the old 36×28 with room for the stroke and the trail), origin at the centre,
# +x forward, +y down.
W, H = 44, 40

RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("body", None, (2.0, 3.6), 0.0)
bone("head", "body", (6.4, 3.4), 0.0, 3.0)
# The abdomen: two links off the back of the thorax, drooping a little, the
# sting on the second.
bone("abd_0", "body", (-1.4, 4.2), 174.0, 4.4)
bone("abd_1", "abd_0", B["abd_0"].end(), 170.0, 4.2)
# The wings: shoulder high on the thorax, laid back and a little up; the
# wrist halfway, the tip carrying on a touch flatter. The far wing sits lower
# and flatter, so it shows under the near one.
SHOULDER, SHOULDER_FAR = (1.8, 0.6), (3.0, 1.4)
bone("wing", "body", SHOULDER, 194.0, 8.0)
bone("wing_tip", "wing", B["wing"].end(), 186.0, 11.4)
bone("wing_far", "body", SHOULDER_FAR, 182.0, 7.4)
bone("wing_far_tip", "wing_far", B["wing_far"].end(), 176.0, 10.4)

RIG.seal()
put, on_bone = RIG.put, RIG.on_bone

def wpoly(at, pts):
    """A polygon given in world coordinates, as a shape about `at`."""
    return poly([(x - at[0], y - at[1]) for x, y in pts])

# ============================================================== parts
# Wing shapes in the bone's frame (+x out along the bone). The root is the
# broad inner membrane, the tip the long blade; they overlap at the wrist.
# The root is the broad inner sail, its leading edge along the bone and its
# trailing edge falling back to the body; the tip is the long blade on from
# the wrist. They overlap at the wrist.
WING_ROOT = [(-0.8, -0.9), (1.0, -1.6), (4.4, -1.8), (7.4, -1.5), (8.2, -0.4), (8.0, 1.2), (6.4, 2.0),
             (4.0, 2.6), (1.4, 2.8), (-0.6, 1.8)]
def wing_tip_shape(L):
    return [(-1.4, -0.6), (-0.8, -1.5), (0.6, -1.8), (L * 0.55, -1.6), (L - 1.2, -1.0), (L + 0.6, 0.2), (L - 0.8, 1.0),
            (L * 0.62, 1.6), (L * 0.3, 2.2), (1.0, 2.4), (-0.8, 1.6), (-1.4, 0.6)]

CHORD = 1.55  # how deep the membrane is across the bone
def wing_parts(pre, root_bone, tip_bone, fill, vein, stroke):
    at, a = on_bone(root_bone)
    k = B[root_bone].length / 7.0
    put(f"{pre}_root", root_bone, at, a, poly([(x * k, y * CHORD) for x, y in WING_ROOT]), fill, stroke)
    at, a = on_bone(tip_bone)
    put(f"{pre}_tip", tip_bone, at, a, poly([(x, y * CHORD) for x, y in wing_tip_shape(B[tip_bone].length)]), fill, stroke)
    if vein:
        # the leading vein, down the root and on along the tip
        at, a = on_bone(root_bone, B[root_bone].length * 0.57, -1.2)
        put("vein", root_bone, at, a, rect(B[root_bone].length * 1.2, 0.8, 0.4), vein)
        at, a = on_bone(tip_bone, B[tip_bone].length * 0.45, -0.9)
        put("vein_tip", tip_bone, at, a, rect(B[tip_bone].length * 0.9, 0.7, 0.35), vein)

# The abdomen and the sting sit inside the silhouette: a dark-amber hairline
# separates them without an ink ring dragging the whole body's value down.
EDGE = {"color": "$chitin.dark2", "width": "hair"}

# ---- behind everything: the trail, the far wing
at, a = on_bone("abd_1", B["abd_1"].length + 2.8, -0.6)
RIG.use("wisp", "abd_1", at, "ss.lib.wisp", scale=0.58, rot=-104.0)
wing_parts("wing_far", "wing_far", "wing_far_tip", "$steel", None, None)

# ---- the abdomen and the sting
at, a = on_bone("abd_1")
put("sting", "abd_1", on_bone("abd_1", B["abd_1"].length - 0.4)[0], a,
    poly([(-0.6, -1.6), (2.4, -0.6), (4.2, 0.1), (2.4, 0.7), (-0.6, 1.6)]), "$husk")
put("abdomen_end", "abd_1", at, a, poly([(-1.0, -2.8), (2.0, -2.6), (4.2, -1.7), (4.8, 0.0), (4.2, 1.6), (2.0, 2.5), (-1.0, 2.8)]),
    "$chitin.dark", EDGE)
at, a = on_bone("abd_0")
put("abdomen", "abd_0", at, a, poly([(-1.4, -3.6), (1.6, -3.7), (4.2, -3.3), (5.2, -1.4), (5.2, 1.6), (4.2, 3.4), (1.6, 3.8), (-1.4, 3.6)]),
    "$chitin.dark", EDGE)
at, a = on_bone("abd_0", 2.2, 1.9)
put("band", "abd_0", at, a, ell(2.4, 1.1), "$chitin")

# ---- the thorax: a round dark body, lit on top, the organ underneath
BODY_C = (2.6, 3.8)
put("body", "body", BODY_C, 0.0, ell(4.8, 4.2), "$chitin.dark", INK_HAIR)
put("belly", "body", (2.8, 6.0), 0.0, ell(3.8, 1.7), "$chitin.dark2")
put("shine", "body", (2.4, 1.6), -6.0, ell(3.2, 1.4), "$chitin")
RIG.use("organ", "body", (2.4, 7.4), "ss.lib.organ", scale=[0.5, 0.42])

# ---- the head: a small capsule, a big eye, the pale snout
HEAD_C = (8.2, 3.4)
put("snout", "head", (10.4, 4.2), 0.0, poly([(-0.6, -1.6), (2.4, -0.8), (4.4, 0.4), (2.4, 1.2), (-0.6, 1.8)]), "$husk.dark")
put("head", "head", HEAD_C, 0.0, ell(2.8, 2.6), "$chitin.dark", INK_HAIR)
put("eye", "head", (9.0, 2.6), 0.0, circ(1.4), "$ink")
put("eye_glint", "head", (8.6, 2.1), 0.0, circ(0.5), "$white")

# ---- the near wing over everything
wing_parts("wing", "wing", "wing_tip", "$husk", "$steel", INK_HAIR)

RIG.check()

# ============================================================== motion
UP, DOWN = 56.0, -58.0     # the root's stroke either side of rest (+ is up)
def stroke(t):
    """-1 at the bottom of the downstroke, +1 at the top; the downstroke is the quicker half."""
    u = t % 1.0
    # top at t=0, driven down to the bottom by 0.42, recovered up by 1.0
    if u < 0.42:
        return 1.0 - 2.0 * smooth(0.0, 0.42, u)
    return -1.0 + 2.0 * smooth(0.42, 1.0, u)
def root_angle(s): return lerp(DOWN, UP, 0.5 + 0.5 * s)

def flit_pose(t):
    s = stroke(t)
    # The downstroke lifts: the body is highest a beat after the bottom of it,
    # and pitches nose-up after that.
    lift = stroke(t - 0.16)
    pose = {"body": (0.5 * cyc(t, 0.2), 1.8 * lift, 5.0 * stroke(t - 0.26))}
    pose["head"] = -4.0 * stroke(t - 0.34)
    # The wing: the root drives, the tip lags behind it (bent down on the
    # upstroke, bent up on the downstroke) so the membrane cups the air.
    pose["wing"] = root_angle(s)
    pose["wing_tip"] = 26.0 * stroke(t - 0.12) - 26.0 * s
    pose["wing_far"] = root_angle(stroke(t - 0.04)) * 0.9
    pose["wing_far_tip"] = 22.0 * stroke(t - 0.16) - 22.0 * stroke(t - 0.04)
    # The back half answers late, a wave out to the sting.
    pose["abd_0"] = -8.0 * stroke(t - 0.3)
    pose["abd_1"] = -12.0 * stroke(t - 0.42)
    return pose

# ---- death: the beat fails. One last snap of both wings up (the anticipation),
# then they fold down off the shoulder as it drops and pitches nose-down, the
# abdomen curls under, the trail scatters and thins, the organ goes out.
# Still from 0.85.
def death_pose(t):
    snap = math.sin(math.pi * smooth(0.0, 0.24, t))
    fall = smooth(0.18, 0.78, t)
    land = math.sin(math.pi * smooth(0.66, 0.85, t))
    pose = {"body": (-0.8 * fall, -1.6 * snap + 3.6 * fall - 0.7 * land, -8.0 * snap + 26.0 * fall)}
    pose["head"] = 10.0 * fall
    pose["wing"] = 30.0 * snap - 62.0 * fall
    pose["wing_tip"] = -14.0 * snap - 30.0 * fall
    pose["wing_far"] = 26.0 * snap - 52.0 * fall
    pose["wing_far_tip"] = -12.0 * snap - 26.0 * fall
    pose["abd_0"] = 10.0 * snap - 22.0 * fall
    pose["abd_1"] = 14.0 * snap - 30.0 * fall
    return pose

animations = {}
TS_FLIT = keyset(24)
animations["flit"] = {
    "description": "One full stroke: the wings flung up over the back and driven down past the belly, the tip lagging the root so the membrane cups on the way down and trails on the way up; every downstroke lifts the body, which pitches after it, the abdomen swings after that and the trail on the sting swings last and flickers.",
    "duration": 0.26,
    "tracks": RIG.tracks(flit_pose, TS_FLIT, [("wisp", "opacity", lambda t: 0.85 + 0.15 * cyc(t, -0.3))],
                         still=("eye", "eye_glint")),
}
TS_DEATH = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The beat fails: one last snap of both wings up against the back, then they fold down off the shoulder as the body drops and pitches nose-down, the abdomen curls under and the sting and snout hang; the trail it was leaving scatters and thins, and the organ underneath goes out. Still from 0.85.",
    "duration": 0.32,
    "tracks": RIG.tracks(death_pose, TS_DEATH, [
        ("wisp", "scale", lambda t: 1.0 + 0.8 * smooth(0.1, 0.7, t)),
        ("wisp", "opacity", lambda t: 1.0 - smooth(0.1, 0.75, t)),
        ("organ", "scale", lambda t: 1.0 + 0.4 * math.sin(math.pi * smooth(0.0, 0.3, t)) - 0.3 * smooth(0.3, 0.85, t)),
        ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.2, 0.8, t)),
        ("eye_glint", "opacity", lambda t: 1.0 - smooth(0.2, 0.6, t)),
    ], still=("eye", "eye_glint")),
}

# ============================================================== states
variants = {
    "elite": {
        "description": "A marked scout: brighter membranes, a heavier sting and a fatter trail.",
        "scale": 1.25,
        "set": {
            "wing_root.fill": "$bone.light",
            "wing_tip.fill": "$bone.light",
            "wing_far_root.fill": "$husk.dark",
            "wing_far_tip.fill": "$husk.dark",
            "sting.fill": "$bone.light",
            "sting.scale": [1.4, 1.3],
            "wisp.scale": 0.72,
            "organ.scale": [0.62, 0.52],
        },
    },
}

DESCRIPTION = (
    "Released from a vent to sweep for you; feelers calls it the Flitter, and it reads your heading and cuts across it rather than "
    "chasing. Seen side-on, facing +x and mirrored by the game: two pale wings over a small dark-amber body — a round thorax lit on top, "
    "a small head with a big eye and a pale snout, a banded abdomen trailing to a pale sting — with the organ underneath and, off the "
    "sting, the trail (`ss.lib.wisp`) that tells the ground castes where you were. The wings carry the whole read — a wide pale shape "
    "against the Tracker's compact blob. Built on a skeleton (scripts/bat.py): each wing is a root and a tip hinged at the shoulder and "
    "at a wrist, the abdomen is a two-link chain off the thorax with the sting and the trail riding its end. `flit` is one full stroke: "
    "the wings flung up over the back and driven down past the belly with the tip lagging the root, the body lifting on the downstroke "
    "and the back half answering late. Gameplay radius 7. `elite` is the marked scout: brighter membranes, a heavier sting, a fatter "
    "trail. The `death` clip is the beat failing: one last snap up, then the wings fold down off the shoulder as it drops nose-down, the "
    "trail scatters and the organ goes out."
)

doc = {
    "id": "ss.enemy.bat",
    "name": "Drifter",
    "description": DESCRIPTION,
    "tags": ["enemy", "flier"],
    "size": [W, H],
    "meta": {"radius": 7},
    "parts": RIG.parts,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-bat.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
