"""The Wanderer — a human figure drawn to proportion, on a skeleton.

    python3 scripts/human.py        # rewrites apps/human/assets/human-char-wanderer.json

Seven and a half heads tall, seen three-quarter from the side and facing +x
(the engine mirrors the frame to face left). One head is the unit: H = 16px,
so the body stands 120px on a 128×160 canvas with the origin at the hips —
the pelvis is the root the whole figure hangs from, and the ground is the
sole line at +60.

    top of head   −60    0.0 H
    chin          −44    1.0 H
    shoulder line −37    1.4 H
    nipple line   −28    2.0 H
    waist         −17    2.7 H
    hips / origin   0    3.75 H
    knee          +28    5.5 H
    ankle         +54    7.1 H
    sole          +60    7.5 H

The rig (scripts/rig.py): the pelvis is the root; a lumbar bone, a chest bone,
a neck and a head stack on it in a shallow S; each arm is an upper arm, a
forearm and a hand hinged at the shoulder, the elbow and the wrist; each leg
is a thigh and a shin solved every frame to an ankle on the ground (two-bone
IK, the knee forward) with a foot hinged at the ankle. Every clip is a pose
function of time over those joints and the document's flat tracks are solved
from it, so nothing parts at a joint however far a clip swings it.

Three-quarter from the side means the near (right) shoulder sits a little
behind the far (left) one on screen and a little lower; the far arm hangs
in front of the chest's line and is drawn under it, the near arm over it.
The far limbs are a step darker and the far foot stands a pixel higher.

Light is from the upper left, as the rest of the repo's: the lit side is the
back and the top, the shade the front and the underside.

Built in passes, each one judged on the sheet (scripts/sheet.ts), the motion
meter (scripts/motion.ts) and the inspect page before the next:
  1  a mannequin in three values of one material, idle and walk
  2  the body: a shade along every front edge and a light along the back, the deltoids over the shoulder seams, hair, an eye, a brow and a mouth, and a run
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, wrap, keyset, ik2,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== 1. the measure
H = 16.0                 # one head
GROUND = 60.0            # the near sole line
FAR_LIFT = 1.0           # the far foot stands this much higher on screen
THIGH, SHIN = 28.0, 26.0
UPPER, FORE, HAND = 21.0, 19.0, 9.0
FOOT_H = 6.0             # ankle to sole

# ============================================================== 2. the skeleton
RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("pelvis", None, (0.0, 0.0), -90.0)
bone("spine", "pelvis", (0.0, -3.0), -86.0, 15.0)                      # lumbar: leans forward going up
bone("chest", "spine", B["spine"].end(), -93.0, 19.0)                   # thorax: leans back — the S
bone("neck", "chest", B["chest"].end(), -78.0, 7.0)                     # forward, as a neck does
bone("head", "neck", B["neck"].end(), -84.0, 8.0)                       # to the skull's centre

SHOULDER = {"n": (-5.0, -35.5), "f": (4.6, -37.5)}
ARM_REST = {"n": (97.0, 82.0, 80.0), "f": (92.0, 79.0, 77.0)}           # upper, fore, hand headings
for s in ("n", "f"):
    u, f, h = ARM_REST[s]
    bone(f"arm_{s}_upper", "chest", SHOULDER[s], u, UPPER)
    bone(f"arm_{s}_fore", f"arm_{s}_upper", B[f"arm_{s}_upper"].end(), f, FORE)
    bone(f"hand_{s}", f"arm_{s}_fore", B[f"arm_{s}_fore"].end(), h, HAND)

HIP = {"n": (-2.0, 0.5), "f": (2.0, -0.5)}
REST_ANKLE = {"n": (-2.0, GROUND - FOOT_H), "f": (4.0, GROUND - FAR_LIFT - FOOT_H)}
def ground_of(s): return GROUND - (FAR_LIFT if s == "f" else 0.0)
for s in ("n", "f"):
    a1, a2 = ik2(HIP[s], REST_ANKLE[s], THIGH, SHIN, +1)                 # the knee forward
    bone(f"leg_{s}_thigh", "pelvis", HIP[s], a1, THIGH)
    bone(f"leg_{s}_shin", f"leg_{s}_thigh", B[f"leg_{s}_thigh"].end(), a2, SHIN)
    bone(f"foot_{s}", f"leg_{s}_shin", B[f"leg_{s}_shin"].end(), 0.0, 12.0)

RIG.seal()

# ============================================================== 3. the parts
put, on_bone = RIG.put, RIG.on_bone

NEAR, FAR, LIT, DARK = "$skin", "$skin.dark", "$skin.light", "$skin.dark2"

def limb(name, bone_name, shape, fill, stroke=INK_HAIR, along=0.0, across=0.0, rot=0.0, opacity=None):
    at, a = on_bone(bone_name, along, across)
    return put(name, bone_name, at, a + rot, shape, fill, stroke, opacity=opacity)

# (along, across) in a bone's frame: along runs down the bone, across is to its
# right-hand side — for a bone pointing down that is the BACK of the limb. The
# light is upper-left, so on a hanging limb the back edge is lit and the front
# edge is in shade; each limb polygon lists its front edge first, then its back.
THIGH_PTS = [(-1.0, -4.6), (6.0, -5.2), (16.0, -4.6), (24.0, -3.8), (28.6, -3.4), (29.2, 0.0), (28.6, 3.4), (24.0, 3.8), (14.0, 4.6), (4.0, 5.4), (-1.0, 4.8)]
SHIN_PTS = [(-0.6, -3.6), (0.0, -3.7), (8.0, -3.1), (18.0, -2.4), (26.0, -2.2), (26.6, 0.0), (26.0, 2.2), (18.0, 2.6), (10.0, 3.9), (4.0, 4.3), (0.0, 3.7), (-0.6, 0.0)]
FOOT_PTS = [(-3.6, -0.6), (-4.6, 2.8), (-3.6, 6.0), (3.0, 6.2), (12.0, 6.2), (12.6, 4.6), (9.0, 2.6), (5.0, 1.0), (2.4, -1.2)]
UPPER_PTS = [(-1.0, -3.6), (2.0, -4.0), (9.0, -3.4), (16.0, -2.9), (21.4, -2.7), (22.0, 0.0), (21.4, 2.7), (16.0, 2.9), (8.0, 3.4), (2.0, 3.9), (-1.0, 3.5)]
FORE_PTS = [(-0.6, -2.8), (3.0, -3.1), (7.0, -2.9), (14.0, -2.2), (19.0, -1.9), (19.6, 0.0), (19.0, 1.9), (14.0, 2.2), (7.0, 2.9), (3.0, 3.1), (-0.6, 2.8)]
HAND_PTS = [(-0.8, -2.2), (3.0, -2.6), (6.5, -2.4), (9.0, -1.2), (9.2, 0.8), (7.6, 2.4), (3.0, 2.6), (-0.8, 2.0)]

def band(pts, i0, i1, w, side, inset=0.35):
    """A strip `w` deep along the edge pts[i0..i1] of a limb polygon, `inset` off it: side +1 goes toward +across (into a front edge), -1 the other way."""
    edge = pts[i0:i1 + 1]
    outer = [(a, c + side * inset) for a, c in edge]
    inner = [(a, c + side * (inset + w)) for a, c in edge]
    return poly(outer + inner[::-1])

def leg_parts(s, fill, shade, lit, stroke):
    limb(f"thigh_{s}", f"leg_{s}_thigh", poly(THIGH_PTS), fill, stroke)
    limb(f"thigh_{s}_shade", f"leg_{s}_thigh", band(THIGH_PTS, 0, 4, 2.6, +1), shade, None)
    if lit: limb(f"thigh_{s}_lit", f"leg_{s}_thigh", band(THIGH_PTS, 7, 10, 1.5, -1), lit, None)
    limb(f"shin_{s}", f"leg_{s}_shin", poly(SHIN_PTS), fill, stroke)
    limb(f"shin_{s}_shade", f"leg_{s}_shin", band(SHIN_PTS, 0, 4, 1.9, +1), shade, None)
    if lit: limb(f"calf_{s}_lit", f"leg_{s}_shin", band(SHIN_PTS, 7, 9, 1.3, -1), lit, None)
    limb(f"knee_{s}", f"leg_{s}_shin", circ(3.3), fill, None)
    limb(f"foot_{s}", f"foot_{s}", poly(FOOT_PTS), fill, stroke)
    limb(f"foot_{s}_shade", f"foot_{s}", poly([(-3.0, 3.6), (-2.8, 5.4), (3.0, 5.6), (11.4, 5.6), (11.6, 4.4), (6.0, 3.4), (1.0, 3.2)]), shade, None)

def arm_parts(s, fill, shade, lit, stroke):
    limb(f"arm_{s}_upper", f"arm_{s}_upper", poly(UPPER_PTS), fill, stroke)
    limb(f"arm_{s}_upper_shade", f"arm_{s}_upper", band(UPPER_PTS, 0, 4, 2.0, +1), shade, None)
    limb(f"shoulder_{s}", f"arm_{s}_upper", ell(3.4, 3.9), fill, None, along=1.6)             # the deltoid over the seam
    if lit: limb(f"shoulder_{s}_lit", f"arm_{s}_upper", ell(2.0, 2.2), lit, None, along=1.4, across=1.2)
    limb(f"arm_{s}_fore", f"arm_{s}_fore", poly(FORE_PTS), fill, stroke)
    limb(f"arm_{s}_fore_shade", f"arm_{s}_fore", band(FORE_PTS, 0, 4, 1.6, +1), shade, None)
    limb(f"elbow_{s}", f"arm_{s}_fore", circ(2.5), fill, None)
    limb(f"hand_{s}", f"hand_{s}", poly(HAND_PTS), fill, stroke)
    limb(f"thumb_{s}", f"hand_{s}", ell(2.2, 1.1), fill, None, along=2.6, across=-2.2, rot=-20.0)

# ---- far side, behind everything: a step darker, its shade two
arm_parts("f", FAR, DARK, None, INK_HAIR)
leg_parts("f", FAR, DARK, None, INK_HAIR)

# ---- the trunk: three masses that slide over one another as the spine bends
put("hips", "pelvis", (0.0, 0.0), 0.0,
    poly([(-8.2, -7.0), (8.0, -8.0), (9.6, 0.0), (8.2, 7.0), (3.0, 9.2), (-3.0, 9.2), (-8.4, 7.4), (-9.6, 2.0)]), NEAR, INK_THIN)
put("hips_shade", "pelvis", (0.0, 0.0), 0.0,
    poly([(9.0, -0.4), (7.8, 6.6), (3.0, 8.6), (-3.0, 8.6), (-3.0, 6.6), (2.4, 6.4), (6.0, 5.2), (6.6, -0.4)]), FAR, None)
put("waist", "spine", (0.0, 0.0), 0.0,
    poly([(-7.0, -19.0), (7.6, -20.0), (8.2, -12.0), (7.8, -4.0), (-7.0, -4.0), (-7.6, -12.0)]), NEAR, INK_THIN)
put("waist_shade", "spine", (0.0, 0.0), 0.0,
    poly([(7.2, -19.4), (7.8, -12.0), (7.4, -4.4), (4.4, -4.4), (4.8, -12.0), (4.2, -19.4)]), FAR, None)
put("chest", "chest", (0.0, 0.0), 0.0,
    poly([(-10.0, -36.6), (-6.0, -39.0), (6.0, -40.4), (11.0, -38.0), (12.2, -30.0), (10.4, -22.0), (7.8, -17.0), (-7.2, -17.0), (-9.4, -24.0)]), NEAR, INK_THIN)
put("chest_shade", "chest", (0.0, 0.0), 0.0,
    poly([(10.6, -37.2), (11.8, -30.0), (10.0, -22.0), (7.4, -17.4), (4.2, -17.4), (6.8, -22.0), (8.2, -30.0), (7.0, -36.6)]), FAR, None)
put("chest_lit", "chest", (0.0, 0.0), 0.0,
    poly([(-9.4, -35.8), (-5.6, -38.2), (0.0, -39.4), (-1.0, -37.4), (-6.0, -35.8), (-7.8, -30.0), (-8.2, -25.0), (-9.0, -24.4)]), LIT, None)
limb("neck", "neck", bar(7.2, 5.4, 5.0, 0.8), NEAR, INK_HAIR)
limb("neck_shade", "neck", ell(1.6, 2.4), FAR, None, along=5.8, across=0.3)                   # under the jaw

# ---- the head, on its bone: along is up the skull, across is forward
limb("head", "head", ell(7.6, 6.4), NEAR, INK_THIN, along=9.0)
limb("jaw", "head", poly([(7.0, -3.6), (2.6, -4.4), (0.6, -2.0), (0.0, 1.6), (1.0, 4.0), (3.4, 5.6), (6.6, 6.4), (8.0, 4.0)]), NEAR, INK_THIN)
limb("jaw_shade", "head", poly([(0.5, -1.8), (0.3, 1.6), (1.2, 3.8), (2.6, 3.6), (1.9, 1.5), (2.0, -1.4)]), FAR, None)
limb("brow_lit", "head", ell(2.2, 2.0), LIT, None, along=12.4, across=3.2)
limb("hair", "head", poly([(13.0, 5.9), (15.6, 4.6), (17.0, 1.6), (16.8, -2.4), (15.0, -5.6), (11.4, -7.4), (7.6, -7.2), (5.0, -6.0), (4.6, -4.4),
                           (6.4, -4.8), (9.0, -5.8), (12.0, -5.2), (14.4, -3.0), (15.4, 0.6), (14.6, 3.6), (13.0, 4.8)]), "$hair", INK_HAIR)
limb("hair_lit", "head", ell(1.5, 3.0), "$hair.light", None, along=15.2, across=-1.6, rot=18.0)
limb("ear", "head", ell(2.1, 1.3), NEAR, INK_HAIR, along=7.4, across=-4.6)
limb("eye", "head", ell(0.8, 1.5), "$ink", None, along=9.6, across=3.6)
limb("brow", "head", rect(0.9, 3.4, 0.4), "$hair", None, along=11.6, across=3.8, rot=-6.0)
limb("mouth", "head", ell(0.5, 1.3), DARK, None, along=3.4, across=4.8)
limb("nose", "head", poly([(7.6, 5.6), (5.6, 7.8), (4.4, 5.8)]), NEAR, INK_HAIR)

# ---- near side, over everything
leg_parts("n", NEAR, FAR, LIT, INK_HAIR)
arm_parts("n", NEAR, FAR, LIT, INK_HAIR)

RIG.check()

# ============================================================== 4. motion
tracks = RIG.tracks

def plant(pose, ankles, pitch):
    """Solve each leg's thigh and shin to put its ankle at `ankles[s]`, against the body as posed, the foot at `pitch[s]`."""
    world = RIG.solve(pose)
    for s in ("n", "f"):
        hx, hy, _ = world[f"leg_{s}_thigh"]
        a1, a2 = ik2((hx, hy), ankles[s], THIGH, SHIN, +1)
        pose[f"abs:leg_{s}_thigh"] = a1
        pose[f"abs:leg_{s}_shin"] = a2
        pose[f"abs:foot_{s}"] = pitch[s]
    return pose

def arms(pose, upper, fore, hand, s):
    pose[f"arm_{s}_upper"] = upper
    pose[f"arm_{s}_fore"] = fore
    pose[f"hand_{s}"] = hand

# ---- idle: the breath, and the weight settling from foot to foot
def idle_pose(t):
    breath = 0.5 - 0.5 * math.cos(2 * math.pi * t)                 # in on the first half, out on the second
    sway = cyc(t)
    pose = {"body": (0.7 * sway, -1.1 * breath, 0.8 * sway)}
    pose["spine"] = -1.0 * breath
    pose["chest"] = -2.0 * breath
    pose["neck"] = 1.4 * breath
    pose["head"] = 1.6 * breath - 0.8 * sway
    arms(pose, 2.6 * breath - 2.0 * sway, -2.0 * breath, 0.0, "n")
    arms(pose, -2.6 * breath + 2.0 * sway, -2.0 * breath, 0.0, "f")
    return plant(pose, {"n": REST_ANKLE["n"], "f": REST_ANKLE["f"]}, {"n": 0.0, "f": 0.0})

# ---- walk: contact, recoil, passing, high — twice, the far leg half a loop behind
STRIDE = 15.0
def step(u):
    """The ankle's travel, its lift and the foot's pitch at phase `u` of a step (contact at 0)."""
    u %= 1.0
    if u < 0.6:  # stance: heel down, flat, then the heel comes up as the foot pushes off behind
        s = u / 0.6
        dx = lerp(STRIDE, -STRIDE, s)
        pitch = -12.0 * (1 - smooth(0.0, 0.25, s)) + 24.0 * smooth(0.65, 1.0, s)
        lift = 2.6 * smooth(0.65, 1.0, s)
    else:        # swing: up and forward, the toe hanging, then the heel reaching for the ground
        s = (u - 0.6) / 0.4
        dx = lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, s))
        lift = 2.6 * (1 - s) + 7.0 * math.sin(math.pi * s)
        pitch = lerp(24.0, -12.0, smooth(0.0, 1.0, s))
    return dx, lift, pitch

def walk_pose(t):
    bob = 1.2 - 3.0 * math.sin(2 * math.pi * t) ** 2                 # lowest on contact, highest passing
    pose = {"body": (0.6 * cyc(2 * t, 0.1), bob, 4.0 + 1.5 * cyc(2 * t, 0.15))}
    pose["spine"] = -1.0
    pose["chest"] = -2.0 - 1.0 * cyc(2 * t, 0.1)
    pose["neck"] = -1.0
    pose["head"] = 1.5 * cyc(2 * t, 0.2) - 1.5
    swing = math.cos(2 * math.pi * t)                                # +1: the near arm back, the far arm forward
    arms(pose, 26.0 * swing, -8.0 - 16.0 * (0.5 + 0.5 * swing), -4.0, "n")
    arms(pose, -26.0 * swing, -8.0 - 16.0 * (0.5 - 0.5 * swing), -4.0, "f")
    ankles, pitch = {}, {}
    for s, ph in (("n", 0.0), ("f", 0.5)):
        dx, lift, p = step(t + ph)
        ankles[s] = (HIP[s][0] + 1.0 + dx, ground_of(s) - FOOT_H - lift)
        pitch[s] = p
    return plant(pose, ankles, pitch)

# ---- run: a short stance that drives back, a flight, the heel kicking up behind and the knee driving through
RUN_STRIDE = 22.0
def run_step(u):
    u %= 1.0
    if u < 0.4:  # stance: the foot lands under the body and drives back
        s = u / 0.4
        dx = lerp(RUN_STRIDE * 0.55, -RUN_STRIDE, s)
        pitch = -4.0 * (1 - smooth(0.0, 0.3, s)) + 34.0 * smooth(0.45, 1.0, s)
        lift = 4.5 * smooth(0.5, 1.0, s)
    else:        # flight and swing: the heel comes up high behind, the knee drives forward, the foot reaches down
        s = (u - 0.4) / 0.6
        dx = lerp(-RUN_STRIDE, RUN_STRIDE * 0.55, smooth(0.0, 1.0, s))
        lift = 4.5 * (1 - s) + 17.0 * math.sin(math.pi * s ** 0.85)
        pitch = lerp(34.0, -4.0, smooth(0.15, 1.0, s))
    return dx, lift, pitch

def run_pose(t):
    bob = 2.0 - 5.0 * math.sin(2 * math.pi * (t - 0.2)) ** 2          # highest in flight, lowest mid-stance
    pose = {"body": (1.0 * cyc(2 * t, 0.05), bob, 13.0 + 2.5 * cyc(2 * t, 0.15))}
    pose["spine"] = -1.5
    pose["chest"] = -4.0 - 2.0 * cyc(2 * t, 0.1)
    pose["neck"] = -3.0
    pose["head"] = -4.0 + 2.0 * cyc(2 * t, 0.2)
    swing = math.cos(2 * math.pi * t)
    arms(pose, 10.0 + 38.0 * swing, -78.0 - 14.0 * swing, -12.0, "n")
    arms(pose, 10.0 - 38.0 * swing, -78.0 + 14.0 * swing, -12.0, "f")
    ankles, pitch = {}, {}
    for s, ph in (("n", 0.0), ("f", 0.5)):
        dx, lift, p = run_step(t + ph)
        ankles[s] = (HIP[s][0] + 3.0 + dx, ground_of(s) - FOOT_H - lift)
        pitch[s] = p
    return plant(pose, ankles, pitch)

animations = {
    "idle": {
        "description": "The breath and the weight: the chest lifts and the shoulders rise on the in-breath, the head nods back a degree, the arms hang and drift; the hips settle from foot to foot with the feet planted.",
        "duration": 2.4,
        "tracks": tracks(idle_pose, keyset(16)),
    },
    "walk": {
        "description": "Contact, recoil, passing, high — twice a loop, the far leg half a loop behind the near. Each ankle is solved to the ground: the heel lands toe-up, the foot flattens and slides back under the body, the heel lifts and pushes off, and the leg swings through bent with the toe hanging. The body is lowest on contact and highest passing, leaning four degrees into the walk; the arms swing against the leg on their side, the elbow bending as the arm comes forward.",
        "duration": 0.8,
        "cues": {"contact": 0.0, "contact_far": 0.5},
        "tracks": tracks(walk_pose, keyset(16)),
    },
    "run": {
        "description": "A short stance that lands under the body and drives back, then flight: the heel kicks up high behind, the knee drives forward and the foot reaches down for the next step. The body leans thirteen degrees, is highest in the air and lowest mid-stance; the arms pump bent at the elbow, fists closed, against the leg on their side.",
        "duration": 0.5,
        "cues": {"contact": 0.0, "contact_far": 0.5},
        "tracks": tracks(run_pose, keyset(16)),
    },
}

# ============================================================== 5. the document
DESCRIPTION = (
    "A human figure drawn to proportion: seven and a half heads, one head 16px, standing 120px with the origin at the hips and the soles at +60. "
    "Seen three-quarter from the side, facing +x and mirrored by the engine: the near (right) shoulder a little behind and below the far one, "
    "the far arm hanging in front of the chest's line and drawn under it, the near arm over it; the far limbs a step darker, the far foot a pixel higher. "
    "Pass 2, the body: still one material, now in four values — a shade along the front edge of every mass and a light along the back, the far side a step darker throughout — a three-piece trunk (hips, waist, chest) that slides as the spine bends, "
    "tapered limbs with a quadriceps and a calf, deltoids over the shoulder seams, a skull with a jaw, short hair swept back, one eye, a brow, a nose, a mouth and an ear. Lit from the upper left. "
    "Built on a skeleton (scripts/human.py): the pelvis is the root, the spine a shallow S of lumbar, chest, neck and head, each arm hinged at the shoulder, elbow and wrist, "
    "each leg a thigh and shin solved every frame to an ankle on the ground with the foot hinged at the ankle. "
    "Gameplay radius 14, height 120."
)

doc = {
    "id": "human.char.wanderer",
    "name": "Wanderer",
    "description": DESCRIPTION,
    "tags": ["char", "player"],
    "size": [128, 160],
    "meta": {"radius": 14, "height": 120},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "human", "assets", "human-char-wanderer.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
