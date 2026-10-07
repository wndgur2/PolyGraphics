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
IK, the knee forward) with a foot hinged at the ankle; the cloak is a chain of
three bones off the chest that lags whatever the body does. Every clip is a
pose function of time over those joints and the document's flat tracks are
solved from it, so nothing parts at a joint however far a clip swings it.

Three-quarter from the side means the near (right) shoulder sits a little
behind the far (left) one on screen and a little lower; the far arm hangs
by the chest's line and is drawn under it, the near arm over it. The far
limbs are a step darker and the far foot stands a pixel higher.

Light is from the upper left, as the rest of the repo's: the lit side is the
back and the top, the shade the front and the underside. Every mass carries a
shade band along its front edge and the bigger ones a light along the back.

Built in passes, each one judged on the sheet (scripts/sheet.ts), the motion
meter (scripts/motion.ts) and the inspect page before the next:
  1  a mannequin in three values of one material, idle and walk
  2  the body: shade and light bands, deltoids over the shoulder seams, hair,
     an eye, a brow and a mouth, and a run
  3  the costume: a hood over the face, a cloak off the shoulders in three
     hinged segments with a torn hem, a leather jerkin belted at the waist
     with a pouch, dark cloth under it, bracers, gloves, tall boots, and a
     longsword carried point-down in the near hand. The mannequin stays as
     the `bare` state.
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

# The cloak: off the back of the shoulder line, three segments hinged end to
# end, each a little further back than the last so it hangs in a shallow curve.
CAPE_ROOT = (-7.5, -36.5)
CAPE = [(24.0, 92.0), (22.0, 95.0), (20.0, 98.0)]
RIG.chain("cape", "chest", CAPE_ROOT, CAPE)

RIG.seal()

# ============================================================== 3. the parts
put, on_bone = RIG.put, RIG.on_bone

# ---- materials: each is (base, shade, light); the far side takes the next step down
def ramp(tok): return (f"${tok}", f"${tok}.dark", f"${tok}.light")
def far(tok): return (f"${tok}.dark", f"${tok}.dark2", None)
SKIN, SKIN_F = ramp("skin"), far("skin")
CLOTH, CLOTH_F = ramp("trouser"), far("trouser")
LEATHER, LEATHER_F = ramp("leather"), far("leather")
TUNIC = ramp("tunic")
CLOAK = ramp("cloak")

BARE_SET = {}       # part id -> the fill it has with no clothes on
COSTUME = []        # part ids that are clothes and go away in `bare`
def wear(part, bare_fill):
    """Record what `part` would be painted with no costume on, for the `bare` state."""
    if bare_fill != part["fill"]: BARE_SET[f"{part['id']}.fill"] = bare_fill
    return part
def clothes(part):
    COSTUME.append(part["id"]); return part

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
BOOT_PTS = [(9.0, -4.6), (8.6, -3.4), (18.0, -2.8), (26.0, -2.6), (26.6, 0.0), (26.0, 2.6), (18.0, 3.2), (10.4, 4.6), (9.4, 5.6)]
UPPER_PTS = [(-1.0, -3.6), (2.0, -4.0), (9.0, -3.4), (16.0, -2.9), (21.4, -2.7), (22.0, 0.0), (21.4, 2.7), (16.0, 2.9), (8.0, 3.4), (2.0, 3.9), (-1.0, 3.5)]
FORE_PTS = [(-0.6, -2.8), (3.0, -3.1), (7.0, -2.9), (14.0, -2.2), (19.0, -1.9), (19.6, 0.0), (19.0, 1.9), (14.0, 2.2), (7.0, 2.9), (3.0, 3.1), (-0.6, 2.8)]
BRACER_PTS = [(5.0, -3.4), (14.0, -2.8), (18.6, -2.5), (19.0, 0.0), (18.6, 2.5), (14.0, 2.8), (5.0, 3.4)]
HAND_PTS = [(-0.8, -2.2), (3.0, -2.6), (6.5, -2.4), (9.0, -1.2), (9.2, 0.8), (7.6, 2.4), (3.0, 2.6), (-0.8, 2.0)]

def band(pts, i0, i1, w, side, inset=0.35):
    """A strip `w` deep along the edge pts[i0..i1] of a limb polygon, `inset` off it: side +1 goes toward +across (into a front edge), -1 the other way."""
    edge = pts[i0:i1 + 1]
    outer = [(a, c + side * inset) for a, c in edge]
    inner = [(a, c + side * (inset + w)) for a, c in edge]
    return poly(outer + inner[::-1])

def leg_parts(s, cloth, leather, skin, stroke):
    base, shade, lit = cloth
    lb, ls, ll = leather
    wear(limb(f"thigh_{s}", f"leg_{s}_thigh", poly(THIGH_PTS), base, stroke), skin[0])
    wear(limb(f"thigh_{s}_shade", f"leg_{s}_thigh", band(THIGH_PTS, 0, 4, 2.6, +1), shade, None), skin[1])
    if lit: wear(limb(f"thigh_{s}_lit", f"leg_{s}_thigh", band(THIGH_PTS, 7, 10, 1.5, -1), lit, None), skin[2])
    wear(limb(f"shin_{s}", f"leg_{s}_shin", poly(SHIN_PTS), base, stroke), skin[0])
    wear(limb(f"shin_{s}_shade", f"leg_{s}_shin", band(SHIN_PTS, 0, 4, 1.9, +1), shade, None), skin[1])
    if lit: wear(limb(f"calf_{s}_lit", f"leg_{s}_shin", band(SHIN_PTS, 7, 9, 1.3, -1), lit, None), skin[2])
    wear(limb(f"knee_{s}", f"leg_{s}_shin", circ(3.3), base, None), skin[0])
    # the boot: a tall shaft with its cuff turned over below the knee, over the shin and the foot
    clothes(limb(f"boot_{s}", f"leg_{s}_shin", poly(BOOT_PTS), lb, stroke))
    clothes(limb(f"boot_{s}_shade", f"leg_{s}_shin", band(BOOT_PTS, 0, 3, 1.8, +1, 0.5), ls, None))
    clothes(limb(f"boot_{s}_cuff", f"leg_{s}_shin", poly([(7.6, -5.0), (12.2, -4.2), (12.6, 5.2), (8.0, 6.0)]), ls, INK_HAIR))
    wear(limb(f"foot_{s}", f"foot_{s}", poly(FOOT_PTS), lb, stroke), skin[0])
    wear(limb(f"foot_{s}_shade", f"foot_{s}", poly([(-3.0, 3.6), (-2.8, 5.4), (3.0, 5.6), (11.4, 5.6), (11.6, 4.4), (6.0, 3.4), (1.0, 3.2)]), ls, None), skin[1])
    clothes(limb(f"heel_{s}", f"foot_{s}", poly([(-4.0, 3.2), (-3.4, 6.0), (1.6, 6.0), (1.2, 3.4)]), ls, None))

def arm_parts(s, cloth, leather, skin, stroke):
    base, shade, lit = cloth
    lb, ls, ll = leather
    wear(limb(f"arm_{s}_upper", f"arm_{s}_upper", poly(UPPER_PTS), base, stroke), skin[0])
    wear(limb(f"arm_{s}_upper_shade", f"arm_{s}_upper", band(UPPER_PTS, 0, 4, 2.0, +1), shade, None), skin[1])
    wear(limb(f"shoulder_{s}", f"arm_{s}_upper", ell(3.4, 3.9), base, None, along=1.6), skin[0])             # the deltoid over the seam
    if lit: wear(limb(f"shoulder_{s}_lit", f"arm_{s}_upper", ell(2.0, 2.2), lit, None, along=1.4, across=1.2), skin[2])
    wear(limb(f"arm_{s}_fore", f"arm_{s}_fore", poly(FORE_PTS), base, stroke), skin[0])
    wear(limb(f"arm_{s}_fore_shade", f"arm_{s}_fore", band(FORE_PTS, 0, 4, 1.6, +1), shade, None), skin[1])
    wear(limb(f"elbow_{s}", f"arm_{s}_fore", circ(2.5), base, None), skin[0])
    # the bracer: wrapped leather from under the elbow to the wrist, with its straps
    clothes(limb(f"bracer_{s}", f"arm_{s}_fore", poly(BRACER_PTS), lb, stroke))
    clothes(limb(f"bracer_{s}_shade", f"arm_{s}_fore", band(BRACER_PTS, 0, 2, 1.4, +1, 0.5), ls, None))
    for i, x in enumerate((8.0, 12.5, 17.0)):
        clothes(limb(f"strap_{s}_{i}", f"arm_{s}_fore", rect(0.8, 6.2, 0.3), ls, None, along=x))
    wear(limb(f"hand_{s}", f"hand_{s}", poly(HAND_PTS), ls, stroke), skin[0])
    wear(limb(f"thumb_{s}", f"hand_{s}", ell(2.2, 1.1), ls, None, along=2.6, across=-2.2, rot=-20.0), skin[0])

def cape_parts():
    # Three segments down the back, gathered at the shoulder and widening to a
    # torn hem. Across is +back; the body's side is negative across. The lower
    # segments are drawn first, the upper over them, and a strokeless patch on
    # each lower segment hides the seam. A shade along the body side, a light
    # down the back edge.
    base, shade, lit = CLOAK
    W = [(-6.5, 5.0), (-10.0, 9.0), (-12.0, 12.0), (-14.0, 15.0)]       # (body side, back side) across at each joint, top to hem
    SEG = [
        [(-1.0, W[0][0]), (-1.4, W[0][1]), (24.6, W[1][1]), (24.6, W[1][0])],
        [(-0.6, W[1][0]), (-0.6, W[1][1]), (22.6, W[2][1]), (22.6, W[2][0])],
        [(-0.6, W[2][0]), (-0.6, W[2][1]), (20.4, W[3][1]), (16.0, 10.4), (20.6, 6.6), (14.4, 3.2), (19.8, -1.2), (14.0, -5.6), (19.0, -9.8), (13.2, W[3][0])],
    ]
    for i in (2, 1, 0):
        n, pts = f"cape_{i}", SEG[i]
        clothes(limb(n, n, poly(pts), base, INK_THIN))
        if i > 0:
            a, b = W[i]
            clothes(limb(f"{n}_fold", n, poly([(-3.0, a + 1.2), (-3.0, b - 1.2), (2.6, b - 1.0), (2.6, a + 1.0)]), base, None))
        inner = [pts[0], pts[-1]]
        clothes(limb(f"{n}_shade", n, poly([(a, c + 0.5) for a, c in inner] + [(a, c + 3.4) for a, c in inner][::-1]), shade, None))
        back = [pts[1], pts[2]]
        clothes(limb(f"{n}_lit", n, poly([(a, c - 0.5) for a, c in back] + [(a, c - 2.2) for a, c in back][::-1]), lit, None))

# ---- the cloak and the far side, behind everything
cape_parts()
arm_parts("f", CLOTH_F, LEATHER_F, SKIN_F, INK_HAIR)
leg_parts("f", CLOTH_F, LEATHER_F, SKIN_F, INK_HAIR)

# ---- the trunk: three masses that slide over one another as the spine bends.
# The jerkin covers all three and hangs past the hips in a split skirt.
tb, ts, tl = TUNIC
wear(put("hips", "pelvis", (0.0, 0.0), 0.0,
    poly([(-8.2, -7.0), (8.0, -8.0), (9.6, 0.0), (8.6, 7.0), (3.4, 10.2), (-3.0, 10.4), (-8.6, 7.8), (-9.6, 2.0)]), tb, INK_THIN), SKIN[0])
wear(put("hips_shade", "pelvis", (0.0, 0.0), 0.0,
    poly([(9.0, -0.4), (8.2, 6.6), (3.4, 9.6), (-3.0, 9.8), (-3.0, 7.4), (2.6, 7.2), (6.2, 5.2), (6.6, -0.4)]), ts, None), SKIN[1])
clothes(put("skirt_split", "pelvis", (0.0, 0.0), 0.0, poly([(-0.4, 4.0), (0.6, 4.0), (0.4, 10.3), (-0.6, 10.3)]), "$ink@0.5", None))
wear(put("waist", "spine", (0.0, 0.0), 0.0,
    poly([(-7.0, -19.0), (7.6, -20.0), (8.2, -12.0), (7.8, -4.0), (-7.0, -4.0), (-7.6, -12.0)]), tb, INK_THIN), SKIN[0])
wear(put("waist_shade", "spine", (0.0, 0.0), 0.0,
    poly([(7.2, -19.4), (7.8, -12.0), (7.4, -4.4), (4.4, -4.4), (4.8, -12.0), (4.2, -19.4)]), ts, None), SKIN[1])
wear(put("chest", "chest", (0.0, 0.0), 0.0,
    poly([(-10.0, -36.6), (-6.0, -39.0), (6.0, -40.4), (11.0, -38.0), (12.2, -30.0), (10.4, -22.0), (7.8, -17.0), (-7.2, -17.0), (-9.4, -24.0)]), tb, INK_THIN), SKIN[0])
wear(put("chest_shade", "chest", (0.0, 0.0), 0.0,
    poly([(10.6, -37.2), (11.8, -30.0), (10.0, -22.0), (7.4, -17.4), (4.2, -17.4), (6.8, -22.0), (8.2, -30.0), (7.0, -36.6)]), ts, None), SKIN[1])
wear(put("chest_lit", "chest", (0.0, 0.0), 0.0,
    poly([(-9.4, -35.8), (-5.6, -38.2), (0.0, -39.4), (-1.0, -37.4), (-6.0, -35.8), (-7.8, -30.0), (-8.2, -25.0), (-9.0, -24.4)]), tl, None), SKIN[2])
# the jerkin's seam and lacing down the front, and the belt over the waist with its buckle and the pouch on the near hip
clothes(put("lacing", "chest", (0.0, 0.0), 0.0, poly([(5.6, -36.0), (6.8, -36.0), (5.4, -20.0), (4.2, -20.0)]), "$ink@0.35", None))
for i, y in enumerate((-33.0, -29.0, -25.0)):
    clothes(put(f"lace_{i}", "chest", (5.6 - 0.1 * (y + 33), y), -12.0, rect(3.6, 0.7, 0.3), LEATHER[1], None))
clothes(put("belt", "spine", (0.0, 0.0), 0.0, poly([(-7.4, -7.6), (7.9, -8.4), (8.0, -4.6), (-7.2, -3.8)]), LEATHER[0], INK_HAIR))
clothes(put("belt_shade", "spine", (0.0, 0.0), 0.0, poly([(7.6, -8.2), (7.8, -4.8), (4.0, -4.6), (4.2, -8.0)]), LEATHER[1], None))
clothes(put("buckle", "spine", (2.6, -6.2), -3.0, rect(3.2, 3.4, 0.5), "$brass", INK_HAIR))
clothes(put("buckle_pin", "spine", (2.6, -6.2), -3.0, rect(0.7, 2.4, 0.3), "$brass.dark", None))
clothes(put("pouch", "pelvis", (-6.4, 1.2), 4.0, rect(5.4, 6.0, 1.6), LEATHER[2], INK_HAIR))
clothes(put("pouch_flap", "pelvis", (-6.4, -0.8), 4.0, rect(5.8, 2.6, 0.8), LEATHER[0], INK_HAIR))
clothes(put("pouch_stud", "pelvis", (-6.4, 0.4), 0.0, circ(0.6), "$brass", None))

# the cowl: the hood's skirt, lying over the shoulders and the top of the chest
cb, cs, cl = CLOAK
clothes(put("cowl", "chest", (0.0, 0.0), 0.0,
    poly([(-11.4, -34.6), (-8.0, -40.2), (-1.0, -43.4), (7.0, -42.6), (12.4, -38.0), (11.2, -32.4), (5.0, -34.6), (-3.0, -34.2), (-9.8, -31.4)]), cb, INK_THIN))
clothes(put("cowl_shade", "chest", (0.0, 0.0), 0.0, poly([(12.0, -37.6), (10.8, -32.8), (5.6, -34.4), (5.2, -36.4), (9.0, -36.0)]), cs, None))
clothes(put("cowl_lit", "chest", (0.0, 0.0), 0.0, poly([(-10.6, -34.6), (-7.6, -39.4), (-2.0, -42.2), (-2.6, -40.4), (-6.6, -38.0), (-8.6, -33.6)]), cl, None))

wear(limb("neck", "neck", bar(7.2, 5.4, 5.0, 0.8), SKIN[0], INK_HAIR), SKIN[0])
wear(limb("neck_shade", "neck", ell(1.6, 2.4), SKIN[1], None, along=5.8, across=0.3), SKIN[1])                   # under the jaw

# ---- the head, on its bone: along is up the skull, across is forward
limb("head", "head", ell(7.6, 6.4), SKIN[0], INK_THIN, along=9.0)
limb("jaw", "head", poly([(7.0, -3.6), (2.6, -4.4), (0.6, -2.0), (0.0, 1.6), (1.0, 4.0), (3.4, 5.6), (6.6, 6.4), (8.0, 4.0)]), SKIN[0], INK_THIN)
limb("jaw_shade", "head", poly([(0.5, -1.8), (0.3, 1.6), (1.2, 3.8), (2.6, 3.6), (1.9, 1.5), (2.0, -1.4)]), SKIN[1], None)
limb("brow_lit", "head", ell(2.2, 2.0), SKIN[2], None, along=12.4, across=3.2)
limb("hair", "head", poly([(13.0, 5.9), (15.6, 4.6), (17.0, 1.6), (16.8, -2.4), (15.0, -5.6), (11.4, -7.4), (7.6, -7.2), (5.0, -6.0), (4.6, -4.4),
                           (6.4, -4.8), (9.0, -5.8), (12.0, -5.2), (14.4, -3.0), (15.4, 0.6), (14.6, 3.6), (13.0, 4.8)]), "$hair", INK_HAIR)
limb("hair_lit", "head", ell(1.5, 3.0), "$hair.light", None, along=15.2, across=-1.6, rot=18.0)
limb("ear", "head", ell(2.1, 1.3), SKIN[0], INK_HAIR, along=7.4, across=-4.6)
# the hood, up: a C around the skull open at the face, its lining showing crimson along the opening,
# and the face in its shadow
HOOD_EDGE = [(-2.4, 0.2), (3.0, 2.0), (8.0, 2.2), (11.6, 4.6), (14.0, 8.2)]
HOOD_OUT = [(18.8, 3.6), (19.6, -1.6), (17.2, -7.6), (12.0, -10.6), (5.0, -10.8), (-1.0, -9.0), (-4.0, -5.6), (-4.2, -1.2)]
clothes(limb("hood_shadow", "head", poly([(-1.4, 0.4), (3.2, 2.4), (8.0, 2.6), (11.2, 4.8), (12.6, 7.4), (10.6, 7.0), (8.6, 4.8), (3.6, 4.6), (-0.4, 2.8)]), "$ink@0.4", None))
clothes(limb("hood", "head", poly(HOOD_EDGE + HOOD_OUT), cb, INK_THIN))
clothes(limb("hood_shade", "head", poly([(-3.4, -1.0), (-3.2, -5.0), (-0.6, -8.2), (5.0, -9.8), (5.0, -7.4), (0.6, -6.0), (-1.6, -3.6), (-1.8, -0.8)]), cs, None))
clothes(limb("hood_lit", "head", poly([(14.6, 7.2), (18.0, 3.4), (18.6, -1.2), (16.6, -6.4), (15.2, -5.4), (16.8, -1.2), (16.2, 2.8), (13.4, 6.0)]), cl, None))
clothes(limb("hood_lining", "head", poly(HOOD_EDGE + [(12.6, 8.4), (10.6, 6.0), (7.8, 3.8), (3.0, 3.6), (-1.8, 2.0)]), "$crimson", None))
clothes(limb("hood_lining_dark", "head", poly([(-2.4, 0.2), (3.0, 2.0), (3.0, 3.6), (-1.8, 2.0)]), "$crimson.dark", None))
limb("eye", "head", ell(0.8, 1.5), "$ink", None, along=9.6, across=4.6)
limb("brow", "head", rect(0.9, 3.0, 0.4), "$hair", None, along=11.5, across=5.0, rot=-6.0)
limb("mouth", "head", ell(0.5, 1.3), SKIN[1], None, along=3.4, across=4.8)
limb("nose", "head", poly([(7.6, 5.6), (5.6, 7.8), (4.4, 5.8)]), SKIN[0], INK_HAIR)

# ---- near side, over everything; the sword's grip lies in the fist and the blade runs on past it
def sword_grip():
    b = "hand_n"
    clothes(limb("pommel", b, circ(1.8), "$brass", INK_HAIR, along=-2.2, across=0.4))
    clothes(limb("grip", b, rect(10.0, 2.6, 0.6), LEATHER[1], INK_HAIR, along=3.6, across=0.4))
def sword_blade():
    b = "hand_n"
    clothes(limb("guard", b, poly([(9.4, -5.2), (11.8, -4.6), (11.8, 5.0), (9.4, 5.6)]), "$brass", INK_HAIR, across=0.4))
    clothes(limb("guard_lit", b, rect(1.0, 3.6, 0.3), "$brass.light", None, along=10.2, across=-2.4))
    clothes(limb("blade", b, poly([(11.6, -1.9), (28.0, -1.5), (46.0, -0.9), (51.0, 0.4), (46.0, 1.6), (28.0, 2.1), (11.6, 2.5)]), "$steel", INK_HAIR, across=0.4))
    clothes(limb("blade_lit", b, poly([(12.4, -1.2), (42.0, -0.8), (42.0, 0.2), (12.4, 0.3)]), "$steel.light", None, across=0.4))
    clothes(limb("fuller", b, poly([(14.0, 0.5), (40.0, 0.8), (40.0, 1.4), (14.0, 1.3)]), "$steel.dark", None, across=0.4))
leg_parts("n", CLOTH, LEATHER, SKIN, INK_HAIR)
sword_grip()
arm_parts("n", CLOTH, LEATHER, SKIN, INK_HAIR)
sword_blade()

RIG.check()

variants = {
    "bare": {
        "description": "The mannequin under the clothes: the same body with nothing on it, one material in four values — passes 1 and 2, kept so the figure can be judged as a figure.",
        "set": dict(sorted(BARE_SET.items())),
        "remove": COSTUME,
        "animations": ["idle", "walk", "run"],
    },
}

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

def cape(pose, trail, sway, t, lag=0.1):
    """The cloak: `trail` degrees back at the root (the wind of the walk), and a `sway` that runs down the chain a beat later per segment."""
    for i in range(3):
        pose[f"cape_{i}"] = -trail * (1.0 if i == 0 else 0.45) + sway * cyc(2 * t, -lag * (i + 1))
    return pose

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
    for i in range(3): pose[f"cape_{i}"] = -1.2 * cyc(t, -0.08 * (i + 1)) - 0.6 * breath
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
    cape(pose, 7.0, 4.0, t)
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
    cape(pose, 34.0, 6.0, t, 0.08)
    ankles, pitch = {}, {}
    for s, ph in (("n", 0.0), ("f", 0.5)):
        dx, lift, p = run_step(t + ph)
        ankles[s] = (HIP[s][0] + 3.0 + dx, ground_of(s) - FOOT_H - lift)
        pitch[s] = p
    return plant(pose, ankles, pitch)

animations = {
    "idle": {
        "description": "The breath and the weight: the chest lifts and the shoulders rise on the in-breath, the head nods back a degree, the arms hang and drift, the cloak stirs; the hips settle from foot to foot with the feet planted.",
        "duration": 2.4,
        "tracks": tracks(idle_pose, keyset(16)),
    },
    "walk": {
        "description": "Contact, recoil, passing, high — twice a loop, the far leg half a loop behind the near. Each ankle is solved to the ground: the heel lands toe-up, the foot flattens and slides back under the body, the heel lifts and pushes off, and the leg swings through bent with the toe hanging. The body is lowest on contact and highest passing, leaning four degrees into the walk; the arms swing against the leg on their side, the elbow bending as the arm comes forward; the cloak trails and sways a beat behind each step, further down the hem.",
        "duration": 0.8,
        "cues": {"contact": 0.0, "contact_far": 0.5},
        "tracks": tracks(walk_pose, keyset(16)),
    },
    "run": {
        "description": "A short stance that lands under the body and drives back, then flight: the heel kicks up high behind, the knee drives forward and the foot reaches down for the next step. The body leans thirteen degrees, is highest in the air and lowest mid-stance; the arms pump bent at the elbow, fists closed, against the leg on their side; the cloak streams out behind.",
        "duration": 0.5,
        "cues": {"contact": 0.0, "contact_far": 0.5},
        "tracks": tracks(run_pose, keyset(16)),
    },
}

# ============================================================== 5. the document
DESCRIPTION = (
    "A human figure drawn to proportion: seven and a half heads, one head 16px, standing 120px with the origin at the hips and the soles at +60. "
    "Seen three-quarter from the side, facing +x and mirrored by the engine: the near (right) shoulder a little behind and below the far one, "
    "the far arm hanging by the chest's line and drawn under it, the near arm over it; the far limbs a step darker, the far foot a pixel higher. "
    "A wanderer: the hood up and the face in its shadow with the lining showing crimson at the edge, a cloak off the shoulders in three hinged segments ending in a torn hem, "
    "a leather jerkin laced down the front and belted at the waist with a brass buckle and a pouch on the near hip, dark cloth under it, wrapped bracers, gloves, "
    "tall boots with the cuff turned under the knee, and a longsword carried point-down in the near fist. "
    "Every mass carries a shade along its front edge and the bigger ones a light along the back; lit from the upper left. "
    "Built on a skeleton (scripts/human.py): the pelvis is the root, the spine a shallow S of lumbar, chest, neck and head, each arm hinged at the shoulder, elbow and wrist, "
    "each leg a thigh and shin solved every frame to an ankle on the ground with the foot hinged at the ankle, the cloak a chain of three bones that lags the body. "
    "`bare` is the mannequin underneath. Gameplay radius 14, height 120."
)

doc = {
    "id": "human.char.wanderer",
    "name": "Wanderer",
    "description": DESCRIPTION,
    "tags": ["char", "player"],
    "size": [128, 160],
    "meta": {"radius": 14, "height": 120},
    "parts": RIG.parts,
    "variants": variants,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "human", "assets", "human-char-wanderer.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks, bare sets {len(BARE_SET)} fills and removes {len(COSTUME)} parts")
