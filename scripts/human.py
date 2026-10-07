"""The Wanderer — a human figure drawn to proportion, on a skeleton.

    python3 scripts/human.py        # rewrites apps/human/assets/human-char-wanderer.json

Seven and a half heads tall, seen three-quarter from the side and facing +x
(the engine mirrors the frame to face left). One head is the unit: H = 16px,
so the body stands 120px on a 192×192 canvas (room for the sword's swing)
with the origin at the hips — the pelvis is the root the whole figure hangs
from, and the ground is the sole line at +60.

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

Every outline is a closed Catmull-Rom curve through a few control points
(`curve`), kinked where a form has a corner — the renderer joins points with
straight lines, and a body drawn from its dozen bends comes out as elbows.
The masses are drawn as muscle: a deltoid over the shoulder, the biceps and
triceps along the upper arm, the forearm fullest under the elbow, the
quadriceps and hamstring on the thigh, the calf high on the shin; the trunk
is one shape from the shoulders to below the waist and one from the waist
over the hips, the seam under the belt.

Light is from the upper left, as the rest of the repo's: the lit side is the
back and the top, the shade the front and the underside. Every mass carries a
shade band along its front edge and the bigger ones a light along the back.

The rest pose is a contrapposto: the weight on the far leg, the near knee
eased, the elbows a little bent, the sword resting point-down and a touch
back, the head a few degrees down.

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
  4  the clips a fight needs: attack, hurt, death and a dodge roll, each a
     pose function shaped in time — an anticipation, a hold, a release that
     arrives fast, a recovery
  5  polish: folds down the cloak, a glint in the eye, an idle with a glance
     in it, the hood-down state, baselines
  8  the parts to the measure: the face in thirds with the eye on the skull's
     midline, a wedge eye under a lid, a tapered brow, a nose with its wing and
     nostril, lips, a chin; the ear from the brow to the nose's base; a neck
     0.45 of a head deep with the sternomastoid and the throat; the trapezius
     and clavicles under the cowl; a fist of four wrapped fingers, ridged
     knuckles and a thumb with its nail
  7  measured: the rig audited against Drillis & Contini and the head-unit
     figure (scripts/human_audit.py) — the hip joints raised to 0.53 of
     stature, the shank and upper arm lengthened, the forearm shortened,
     the shoulders and hips widened; the palette lifted so the body reads
     on its floor; the walk's down and up a beat after contact and passing
  6  precision: every outline a curve, the masses as muscle, a head with a
     brow, a nose, lips and a chin, a fist with fingers, a boot with a heel
     and a toe cap, the trunk in two pieces under the belt, a baldric and a
     brooch, stitching, the contrapposto rest, and the walk with the chest
     turning against the hips and the wrists lagging the arms
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, wrap, keyset, ik2,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== 1. the measure
H = 16.0                 # one head
GROUND = 60.0            # the near sole line
FAR_LIFT = 1.0           # the far foot stands this much higher on screen
THIGH, SHIN = 29.5, 29.0 # Drillis & Contini: thigh 0.245, shank 0.246 of stature; a pixel over the hip-to-sole drop, so a standing knee has somewhere to bend
UPPER, FORE, HAND = 22.3, 17.5, 9.0   # upper arm 0.186, forearm 0.146 of stature; the hand is a fist, three quarters of an open hand
FOOT_H = 5.0             # ankle to sole: 0.039 of stature
# Measured against those standards by scripts/human_audit.py — run it after moving a joint.

# ============================================================== 2. the skeleton
RIG = Rig()
B = RIG.bones
bone = RIG.bone

bone("pelvis", None, (0.0, 0.0), -90.0)
bone("spine", "pelvis", (0.0, -3.0), -86.0, 15.0)                      # lumbar: leans forward going up
bone("chest", "spine", B["spine"].end(), -93.0, 19.0)                   # thorax: leans back — the S
bone("neck", "chest", B["chest"].end(), -76.0, 7.0)                     # forward, as a neck does
bone("head", "neck", B["neck"].end(), -81.0, 8.0)                       # to the skull's centre, a few degrees down

SHOULDER = {"n": (-6.4, -37.0), "f": (6.4, -39.2)}      # 0.818 of stature up, the biacromial width foreshortened to sin 25°
ARM_REST = {"n": (100.0, 86.0, 80.0), "f": (90.0, 76.0, 72.0)}          # upper, fore, hand headings: elbows eased
for s in ("n", "f"):
    u, f, h = ARM_REST[s]
    bone(f"arm_{s}_upper", "chest", SHOULDER[s], u, UPPER)
    bone(f"arm_{s}_fore", f"arm_{s}_upper", B[f"arm_{s}_upper"].end(), f, FORE)
    bone(f"hand_{s}", f"arm_{s}_fore", B[f"arm_{s}_fore"].end(), h, HAND)

HIP = {"n": (-4.0, -3.5), "f": (4.0, -4.5)}            # the greater trochanters: 0.530 of stature up — above the crotch, which is where a torso goes long
# contrapposto: the far leg carries the weight under the hip, the near foot rests a little forward
REST_ANKLE = {"n": (1.5, GROUND - FOOT_H), "f": (1.0, GROUND - FAR_LIFT - FOOT_H)}
REST_PITCH = {"n": 0.0, "f": 0.0}
def ground_of(s): return GROUND - (FAR_LIFT if s == "f" else 0.0)
for s in ("n", "f"):
    a1, a2 = ik2(HIP[s], REST_ANKLE[s], THIGH, SHIN, +1)                 # the knee forward
    bone(f"leg_{s}_thigh", "pelvis", HIP[s], a1, THIGH)
    bone(f"leg_{s}_shin", f"leg_{s}_thigh", B[f"leg_{s}_thigh"].end(), a2, SHIN)
    bone(f"foot_{s}", f"leg_{s}_shin", B[f"leg_{s}_shin"].end(), 0.0, 12.0)

# The cloak: off the back of the shoulder line, three segments hinged end to
# end, each a little further back than the last so it hangs in a shallow curve.
CAPE_ROOT = (-8.0, -37.5)
CAPE = [(24.0, 92.0), (22.0, 95.0), (20.0, 98.0)]
RIG.chain("cape", "chest", CAPE_ROOT, CAPE)

RIG.seal()

# ============================================================== 3. the parts
put, on_bone = RIG.put, RIG.on_bone

def curve(ctrl, per=4, sharp=()):
    """
    A closed Catmull-Rom curve through `ctrl`, `per` points a span. Indices in
    `sharp` are corners: the point is tripled so the curve arrives and leaves it
    straight. Returns the point list (for poly()).
    """
    c = []
    for i, p in enumerate(ctrl):
        c.extend([tuple(p)] * (3 if i in sharp else 1))
    n = len(c); out = []
    for i in range(n):
        p0, p1, p2, p3 = c[(i - 1) % n], c[i], c[(i + 1) % n], c[(i + 2) % n]
        if p1 == p2: continue
        for k in range(per):
            t = k / per; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    return out
def cpoly(ctrl, per=4, sharp=()): return poly(curve(ctrl, per, sharp))

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
    if bare_fill is not None and bare_fill != part["fill"]: BARE_SET[f"{part['id']}.fill"] = bare_fill
    return part
def clothes(part):
    COSTUME.append(part["id"]); return part

def limb(name, bone_name, shape, fill, stroke=INK_HAIR, along=0.0, across=0.0, rot=0.0, opacity=None):
    at, a = on_bone(bone_name, along, across)
    return put(name, bone_name, at, a + rot, shape, fill, stroke, opacity=opacity)

# (along, across) in a bone's frame: along runs down the bone, across is to its
# right-hand side — for a bone pointing down that is the BACK of the limb. The
# light is upper-left, so on a hanging limb the back edge is lit and the front
# edge is in shade; each limb's control points list the front edge first, root
# to tip, then the tip, then the back edge tip to root.
THIGH_C = [(-1.6, -4.4), (5.0, -5.6), (14.0, -5.2), (22.0, -4.2), (28.6, -3.4), (29.6, 0.2), (28.6, 3.6), (22.0, 4.4), (12.0, 5.6), (4.0, 5.8), (-1.6, 4.2)]
SHIN_C = [(-1.2, -3.8), (4.0, -3.7), (12.0, -3.1), (20.0, -2.6), (26.6, -2.4), (27.4, 0.0), (26.6, 2.3), (18.0, 2.9), (9.0, 4.8), (3.0, 4.4), (-1.2, 2.6)]
UPPER_C = [(-1.6, -3.4), (3.0, -4.5), (10.0, -3.7), (17.0, -2.9), (21.6, -2.6), (22.4, 0.0), (21.6, 2.6), (16.0, 3.2), (8.0, 3.9), (2.0, 3.7), (-1.6, 2.8)]
FORE_C = [(-1.2, -3.0), (4.0, -3.5), (10.0, -2.7), (16.0, -2.1), (19.4, -1.9), (20.2, 0.0), (19.4, 1.9), (14.0, 2.3), (6.0, 3.3), (2.0, 3.3), (-1.2, 2.4)]
BRACER_C = [(5.2, -3.5), (11.0, -3.0), (18.8, -2.5), (19.4, 0.0), (18.8, 2.5), (11.0, 3.0), (5.2, 3.6)]
# the fist, closed on the grip: a rounded block with the knuckles toward +along and the thumb over the fingers
FIST_C = [(-0.6, -2.8), (3.0, -3.3), (7.0, -3.1), (9.2, -2.0), (9.8, 0.4), (9.3, 2.4), (6.6, 3.2), (2.4, 3.0), (-0.6, 2.4)]
# the foot: heel, arch, sole, toe cap, instep, ankle — a boot's shape
FOOT_C = [(-3.8, -1.0), (-5.0, 1.6), (-4.4, 6.0), (2.0, 6.3), (12.2, 6.3), (13.8, 4.6), (11.0, 2.0), (5.0, 0.6), (2.0, -1.6)]
BOOT_C = [(9.2, -4.6), (12.0, -3.6), (19.0, -2.9), (26.8, -2.6), (27.6, 0.0), (26.8, 2.6), (18.0, 3.3), (11.0, 5.0), (9.4, 5.8)]

def stretch(ctrl, k):
    """A limb's control points with along scaled by `k` — the polygons were drawn to one length and the measure moved."""
    return [(a * k, c) for a, c in ctrl]
THIGH_C = stretch(THIGH_C, THIGH / 28.5)
SHIN_C, BOOT_C = stretch(SHIN_C, SHIN / 26.5), stretch(BOOT_C, SHIN / 26.5)
UPPER_C = stretch(UPPER_C, UPPER / 21.0)
FORE_C, BRACER_C = stretch(FORE_C, FORE / 19.0), stretch(BRACER_C, FORE / 19.0)
FOOT_C = [(a, c * FOOT_H / 6.0) for a, c in FOOT_C]

def band(ctrl, i0, i1, w, side, inset=0.35, per=4):
    """A strip `w` deep along the edge ctrl[i0..i1] of a limb, `inset` off it: side +1 goes toward +across (into a front edge), -1 the other way."""
    edge = ctrl[i0:i1 + 1]
    outer = [(a, c + side * inset) for a, c in edge]
    inner = [(a, c + side * (inset + w)) for a, c in edge]
    return poly(curve(outer + inner[::-1], per, sharp=(0, len(edge) - 1, len(edge), 2 * len(edge) - 1)))

def leg_parts(s, cloth, leather, skin, stroke):
    base, shade, lit = cloth
    lb, ls, ll = leather
    wear(limb(f"thigh_{s}", f"leg_{s}_thigh", cpoly(THIGH_C), base, stroke), skin[0])
    wear(limb(f"thigh_{s}_shade", f"leg_{s}_thigh", band(THIGH_C, 0, 4, 2.6, +1), shade, None), skin[1])
    if lit: wear(limb(f"thigh_{s}_lit", f"leg_{s}_thigh", band(THIGH_C, 7, 10, 1.5, -1), lit, None), skin[2])
    wear(limb(f"shin_{s}", f"leg_{s}_shin", cpoly(SHIN_C), base, stroke), skin[0])
    wear(limb(f"shin_{s}_shade", f"leg_{s}_shin", band(SHIN_C, 0, 4, 1.9, +1), shade, None), skin[1])
    if lit: wear(limb(f"calf_{s}_lit", f"leg_{s}_shin", band(SHIN_C, 7, 9, 1.3, -1), lit, None), skin[2])
    wear(limb(f"knee_{s}", f"leg_{s}_shin", ell(3.6, 3.3), base, None, along=0.4), skin[0])
    clothes(limb(f"thigh_{s}_seam", f"leg_{s}_thigh", cpoly(stretch([(2.0, -3.4), (14.0, -3.6), (26.0, -2.4), (26.0, -1.9), (14.0, -3.1), (2.0, -2.9)], THIGH / 28.5), sharp=(0, 2, 3, 5)), "$ink@0.22", None))
    clothes(limb(f"knee_{s}_patch", f"leg_{s}_shin", cpoly([(-2.6, -3.0), (2.4, -3.3), (4.6, -0.6), (3.6, 2.6), (-1.6, 3.0), (-3.4, 0.4)]), shade, None, opacity=0.5))
    # the boot: a tall shaft, the cuff turned over below the knee, a strap at the ankle, a heel and a toe cap
    clothes(limb(f"boot_{s}", f"leg_{s}_shin", cpoly(BOOT_C, sharp=(0, 8)), lb, stroke))
    clothes(limb(f"boot_{s}_shade", f"leg_{s}_shin", band(BOOT_C, 0, 3, 1.8, +1, 0.5), ls, None))
    clothes(limb(f"boot_{s}_cuff", f"leg_{s}_shin", cpoly(stretch([(7.6, -5.2), (10.0, -4.6), (12.6, -4.2), (13.0, 0.0), (12.6, 5.4), (10.0, 6.2), (8.0, 6.0), (7.4, 0.0)], SHIN / 26.5), sharp=(0, 2, 4, 6)), ls, INK_HAIR))
    clothes(limb(f"boot_{s}_cuff_lit", f"leg_{s}_shin", rect(1.2, 4.0, 0.4), ll or lb, None, along=8.6 * SHIN / 26.5, across=3.4) if ll else limb(f"boot_{s}_cuff_edge", f"leg_{s}_shin", rect(0.6, 9.0, 0.3), ls, None, along=12.4 * SHIN / 26.5))
    wear(limb(f"foot_{s}", f"foot_{s}", cpoly(FOOT_C, sharp=(2, 3, 4)), lb, stroke), skin[0])
    wear(limb(f"foot_{s}_shade", f"foot_{s}", cpoly([(-3.4, 2.8), (-3.2, 4.7), (2.0, 4.9), (11.6, 4.9), (12.2, 3.8), (7.0, 2.6), (1.0, 2.5)], sharp=(1, 2, 3)), ls, None), skin[1])
    clothes(limb(f"heel_{s}", f"foot_{s}", cpoly([(-4.6, 2.5), (-4.0, 5.1), (1.8, 5.1), (1.4, 3.0)], sharp=(0, 1, 2, 3)), ls, None))
    clothes(limb(f"toecap_{s}", f"foot_{s}", cpoly([(8.6, 1.2), (12.4, 2.2), (13.4, 4.0), (12.0, 4.9), (8.4, 4.9)], sharp=(3, 4)), ls, None))
    clothes(limb(f"boot_{s}_strap", f"foot_{s}", cpoly([(-3.8, -0.2), (2.6, -0.8), (3.2, 1.2), (-3.4, 1.6)], sharp=(0, 1, 2, 3)), ls, None))
    clothes(limb(f"boot_{s}_buckle", f"foot_{s}", rect(1.6, 1.4, 0.3), "$brass", None, along=0.4, across=0.4))

def arm_parts(s, cloth, leather, skin, stroke):
    base, shade, lit = cloth
    lb, ls, ll = leather
    wear(limb(f"arm_{s}_upper", f"arm_{s}_upper", cpoly(UPPER_C), base, stroke), skin[0])
    wear(limb(f"arm_{s}_upper_shade", f"arm_{s}_upper", band(UPPER_C, 0, 4, 2.0, +1), shade, None), skin[1])
    wear(limb(f"shoulder_{s}", f"arm_{s}_upper", cpoly([(-2.2, -3.2), (1.0, -4.6), (5.0, -4.2), (7.0, -1.0), (6.0, 2.6), (2.0, 4.2), (-2.0, 3.4), (-3.0, 0.0)]), base, None), skin[0])   # the deltoid over the seam
    if lit: wear(limb(f"shoulder_{s}_lit", f"arm_{s}_upper", ell(2.4, 2.0), lit, None, along=1.2, across=1.4, rot=-20.0), skin[2])
    wear(limb(f"arm_{s}_fore", f"arm_{s}_fore", cpoly(FORE_C), base, stroke), skin[0])
    wear(limb(f"arm_{s}_fore_shade", f"arm_{s}_fore", band(FORE_C, 0, 4, 1.6, +1), shade, None), skin[1])
    wear(limb(f"elbow_{s}", f"arm_{s}_fore", ell(2.8, 2.6), base, None, along=0.2), skin[0])
    # the bracer: wrapped leather from under the elbow to the wrist, with its straps
    clothes(limb(f"bracer_{s}", f"arm_{s}_fore", cpoly(BRACER_C, sharp=(0, 6)), lb, stroke))
    clothes(limb(f"bracer_{s}_shade", f"arm_{s}_fore", band(BRACER_C, 0, 2, 1.4, +1, 0.5), ls, None))
    for i, x in enumerate((7.4, 11.5, 15.6)):
        clothes(limb(f"strap_{s}_{i}", f"arm_{s}_fore", rect(0.9, 6.4, 0.3), ls, None, along=x))
        clothes(limb(f"strap_{s}_{i}_edge", f"arm_{s}_fore", rect(0.3, 6.4, 0.15), ll or lb, None, along=x - 0.55))
    wear(limb(f"hand_{s}", f"hand_{s}", cpoly(FIST_C), ls, stroke), skin[0])
    # the fingers wrapped round the grip, one band each from the knuckle down, the creases between them
    for i, (a0, a1) in enumerate(((2.2, 4.0), (4.0, 5.8), (5.8, 7.6), (7.6, 9.4))):
        wear(limb(f"finger_{s}_{i}", f"hand_{s}", cpoly([(a0, -2.7), (a1 - 0.2, -2.9 - 0.1 * i), (a1, 0.0), (a1 - 0.2, 2.6), (a0, 2.6)], sharp=(0, 4)), ls, None), skin[0])
        wear(limb(f"crease_{s}_{i}", f"hand_{s}", cpoly([(a0 - 0.2, -2.5), (a0 + 0.2, -2.5), (a0 + 0.2, 2.4), (a0 - 0.2, 2.4)], sharp=(0, 1, 2, 3)), "$ink@0.45", None), "$ink@0.45")
    # the knuckles: a lit ridge across the end of the fist, bumped once a finger
    wear(limb(f"knuckles_{s}", f"hand_{s}", cpoly([(8.2, -2.2), (8.9, -1.6), (8.5, -0.7), (9.1, 0.0), (8.6, 0.8), (9.0, 1.6), (8.3, 2.2), (7.6, 2.0), (7.6, -2.0)]), ll or lb, None), skin[2])
    # the thumb over the first two fingers, its nail at the end
    wear(limb(f"thumb_{s}", f"hand_{s}", cpoly([(0.2, -2.6), (2.4, -3.1), (4.8, -2.7), (5.8, -1.9), (5.2, -1.1), (3.0, -1.3), (0.6, -1.6)]), ls, INK_HAIR), skin[0])
    wear(limb(f"thumb_{s}_nail", f"hand_{s}", ell(0.7, 0.45), ll or lb, None, along=5.0, across=-2.1, rot=-20.0), skin[2])

def cape_parts():
    # Three segments down the back, gathered at the shoulder and widening to a
    # torn hem. Across is +back; the body's side is negative across. The lower
    # segments are drawn first, the upper over them, and a strokeless patch on
    # each lower segment hides the seam. A shade along the body side, a light
    # down the back edge, two folds where the cloth gathers.
    base, shade, lit = CLOAK
    W = [(-6.5, 5.0), (-10.0, 9.2), (-12.0, 12.4), (-14.0, 15.4)]       # (body side, back side) across at each joint, top to hem
    SEG = [
        [(-1.0, W[0][0]), (-1.4, W[0][1]), (12.0, 7.6), (24.6, W[1][1]), (24.6, W[1][0]), (12.0, -8.4)],
        [(-0.6, W[1][0]), (-0.6, W[1][1]), (11.0, 11.2), (22.6, W[2][1]), (22.6, W[2][0]), (11.0, -11.2)],
        [(-0.6, W[2][0]), (-0.6, W[2][1]), (10.0, 14.2), (20.4, W[3][1]), (16.4, 10.6), (20.8, 6.4), (15.0, 3.0), (20.2, -1.4), (14.6, -5.8), (19.4, -10.0), (13.6, W[3][0])],
    ]
    SHARP = [(0, 1, 3, 4), (0, 1, 3, 4), tuple(range(3, 11)) + (0, 1)]
    for i in (2, 1, 0):
        n, pts = f"cape_{i}", SEG[i]
        clothes(limb(n, n, cpoly(pts, sharp=SHARP[i]), base, INK_THIN))
        if i > 0:
            a, b = W[i]
            clothes(limb(f"{n}_fold", n, poly([(-3.0, a + 1.2), (-3.0, b - 1.2), (2.6, b - 1.0), (2.6, a + 1.0)]), base, None))
        inner = [pts[0], pts[-1]]
        clothes(limb(f"{n}_shade", n, poly([(a, c + 0.5) for a, c in inner] + [(a, c + 3.4) for a, c in inner][::-1]), shade, None))
        back = [pts[1], pts[2], pts[3]]
        clothes(limb(f"{n}_lit", n, cpoly([(a, c - 0.5) for a, c in back] + [(a, c - 2.2) for a, c in back][::-1], sharp=(0, 2, 3, 5)), lit, None))
        if i == 0:
            clothes(limb(f"{n}_rim", n, cpoly([(a, c - 0.5) for a, c in back] + [(a, c - 1.1) for a, c in back][::-1], sharp=(0, 2, 3, 5)), "$cloak.light2", None, opacity=0.6))
        (a0, b0), (a1, b1) = W[i], W[i + 1]
        L = CAPE[i][0]
        for k, f in enumerate((0.36, 0.68)):
            c0, c1 = a0 + f * (b0 - a0), a1 + f * (b1 - a1)
            clothes(limb(f"{n}_fold_{k}", n, cpoly([(1.5, c0 - 0.5), (L * 0.5, (c0 + c1) / 2 - 0.9), (L - 1.5, c1 - 0.7), (L - 1.5, c1 + 0.7), (L * 0.5, (c0 + c1) / 2 + 0.5), (1.5, c0 + 0.5)], sharp=(0, 2, 3, 5)), shade, None, opacity=0.55))

# ---- the cloak and the far side, behind everything
cape_parts()
arm_parts("f", CLOTH_F, LEATHER_F, SKIN_F, INK_HAIR)
leg_parts("f", CLOTH_F, LEATHER_F, SKIN_F, INK_HAIR)

# ---- the trunk: two masses, the seam under the belt. The jerkin covers both
# and hangs past the hips in a split skirt. World coordinates at rest; each
# rides its bone from there.
tb, ts, tl = TUNIC
HIPS_C = [(-8.6, -13.0), (0.0, -13.8), (8.8, -13.4), (10.4, -7.0), (9.8, 0.0), (8.2, 4.6), (3.6, 7.0), (-3.0, 7.2), (-8.4, 5.0), (-10.2, -1.0), (-9.6, -8.0)]
wear(put("hips", "pelvis", (0.0, -4.0), 0.0, cpoly(HIPS_C), tb, INK_THIN), SKIN[0])
wear(put("hips_shade", "pelvis", (0.0, -4.0), 0.0, cpoly([(9.4, -7.0), (9.0, 0.0), (7.6, 4.2), (3.6, 6.2), (-3.0, 6.4), (-3.0, 4.0), (2.6, 3.6), (6.0, 1.2), (6.8, -7.0)]), ts, None), SKIN[1])
clothes(put("skirt_split", "pelvis", (0.0, -4.0), 0.0, cpoly([(-0.6, -0.4), (0.8, -0.2), (0.6, 6.9), (-0.8, 6.9)], sharp=(0, 1, 2, 3)), "$ink@0.45", None))
clothes(put("skirt_hem", "pelvis", (0.0, -4.0), 0.0, cpoly([(-8.2, 4.2), (-3.0, 6.4), (3.6, 6.2), (8.0, 3.8), (8.4, 4.9), (3.6, 7.3), (-3.0, 7.5), (-8.6, 5.3)], sharp=(0, 3, 4, 7)), ts, None))
TORSO_C = [(-9.6, -33.4), (-9.8, -27.0), (-8.8, -20.0), (-7.8, -14.0), (-7.6, -9.2), (-4.0, -7.6), (6.0, -7.6), (9.4, -9.4), (9.2, -14.0), (9.8, -18.4), (11.2, -23.0), (12.4, -28.4), (12.2, -35.0), (9.6, -40.2), (3.0, -42.0), (-5.0, -40.8), (-9.4, -37.6)]
wear(put("torso", "chest", (0.0, 0.0), 0.0, cpoly(TORSO_C), tb, INK_THIN), SKIN[0])
wear(put("torso_shade", "chest", (0.0, 0.0), 0.0, cpoly([(11.8, -34.4), (12.0, -28.4), (10.8, -23.0), (9.4, -18.4), (8.8, -14.0), (9.0, -9.6), (5.8, -9.6), (6.0, -14.0), (6.4, -18.4), (7.6, -23.0), (8.6, -28.4), (8.2, -34.4)]), ts, None), SKIN[1])
wear(put("torso_lit", "chest", (0.0, 0.0), 0.0, cpoly([(-9.6, -36.6), (-5.0, -39.6), (1.0, -40.8), (0.0, -38.4), (-5.2, -37.0), (-8.2, -33.4), (-8.6, -27.0), (-7.8, -21.0), (-9.4, -20.0), (-9.6, -27.0)]), tl, None), SKIN[2])
clothes(put("chest_seam", "chest", (0.0, 0.0), 0.0, cpoly([(4.0, -36.6), (8.6, -33.0), (10.6, -27.4), (10.0, -27.0), (8.0, -32.4), (3.6, -36.0)], sharp=(0, 2, 3, 5)), "$ink@0.25", None))
# the jerkin's lacing down the front, its stitched edge, and the baldric across the chest from the near shoulder to the far hip
clothes(put("lacing", "chest", (0.0, 0.0), 0.0, cpoly([(5.6, -36.4), (7.0, -36.4), (5.6, -18.0), (4.2, -18.0)], sharp=(0, 1, 2, 3)), "$ink@0.35", None))
for i, y in enumerate((-33.5, -30.0, -26.5, -23.0)):
    clothes(put(f"lace_{i}", "chest", (6.2 - 0.07 * (y + 33.5), y), -14.0, rect(3.8, 0.7, 0.3), LEATHER[1], None))
for i, (x, y) in enumerate(((-8.6, -31.0), (-8.2, -25.0), (-7.4, -19.0), (-7.0, -13.0), (-6.8, -8.0))):
    clothes(put(f"stitch_{i}", "chest", (x, y), 84.0, rect(1.6, 0.5, 0.2), "$ink@0.35", None))
clothes(put("baldric", "chest", (0.0, 0.0), 0.0, cpoly([(-8.2, -35.0), (-3.6, -36.4), (3.0, -27.0), (8.4, -15.0), (9.0, -9.0), (6.0, -9.0), (5.2, -14.0), (0.0, -25.0), (-5.6, -32.4)], sharp=(0, 1, 4, 5)), LEATHER[0], INK_HAIR))
clothes(put("baldric_edge", "chest", (0.0, 0.0), 0.0, cpoly([(-7.6, -34.6), (-3.6, -35.8), (3.0, -26.6), (8.2, -14.6), (8.6, -9.4), (7.8, -9.4), (7.4, -14.6), (2.2, -26.4), (-4.0, -35.0)], sharp=(0, 1, 4, 5)), LEATHER[2], None))
clothes(put("baldric_stud", "chest", (3.4, -26.4), 0.0, circ(0.8), "$brass", None))
clothes(put("baldric_stud_b", "chest", (7.0, -16.6), 0.0, circ(0.8), "$brass", None))
# the belt over the waist with its buckle, and the pouch on the near hip
clothes(put("belt", "spine", (0.0, -3.0), 0.0, cpoly([(-7.8, -11.0), (0.0, -11.8), (8.2, -11.6), (8.3, -7.4), (0.0, -7.0), (-7.6, -6.8)], sharp=(0, 2, 3, 5)), LEATHER[0], INK_HAIR))
clothes(put("belt_shade", "spine", (0.0, -3.0), 0.0, poly([(7.8, -11.4), (8.0, -7.6), (4.0, -7.4), (4.2, -11.4)]), LEATHER[1], None))
clothes(put("belt_edge", "spine", (0.0, -3.0), 0.0, cpoly([(-7.6, -10.6), (0.0, -11.3), (7.8, -11.1), (7.8, -10.4), (0.0, -10.6), (-7.4, -9.9)], sharp=(0, 2, 3, 5)), LEATHER[2], None))
clothes(put("buckle", "spine", (2.8, -9.3), -3.0, rect(3.4, 3.6, 0.6), "$brass", INK_HAIR))
clothes(put("buckle_in", "spine", (2.8, -9.3), -3.0, rect(1.8, 2.0, 0.3), LEATHER[1], None))
clothes(put("buckle_pin", "spine", (2.8, -9.3), -3.0, rect(0.7, 2.6, 0.3), "$brass.dark", None))
clothes(put("pouch", "pelvis", (-6.6, -2.6), 4.0, cpoly([(-2.8, -2.6), (2.8, -2.6), (3.2, 2.0), (1.6, 3.4), (-1.6, 3.4), (-3.2, 2.0)], sharp=(0, 1)), LEATHER[2], INK_HAIR))
clothes(put("pouch_shade", "pelvis", (-6.6, -2.6), 4.0, cpoly([(1.2, -1.6), (2.6, -1.6), (2.8, 1.8), (1.6, 3.0), (0.6, 3.0)]), LEATHER[0], None))
clothes(put("pouch_flap", "pelvis", (-6.6, -4.6), 4.0, cpoly([(-3.2, -1.4), (3.2, -1.4), (3.2, 0.6), (0.0, 1.6), (-3.2, 0.6)], sharp=(0, 1)), LEATHER[0], INK_HAIR))
clothes(put("pouch_stud", "pelvis", (-6.6, -3.4), 0.0, circ(0.6), "$brass", None))

# the cowl: the hood's skirt, lying over the shoulders and the top of the chest, with the brooch that closes it
cb, cs, cl = CLOAK
clothes(put("cowl", "chest", (0.0, 0.0), 0.0, cpoly([(-11.6, -35.4), (-8.4, -41.0), (-1.0, -44.4), (7.0, -43.6), (12.6, -39.0), (11.8, -33.0), (5.0, -35.0), (-3.0, -34.8), (-9.6, -32.0)]), cb, INK_THIN))
clothes(put("cowl_shade", "chest", (0.0, 0.0), 0.0, cpoly([(12.2, -37.6), (11.2, -32.4), (5.6, -34.0), (5.2, -36.6), (9.0, -36.4)]), cs, None))
clothes(put("cowl_lit", "chest", (0.0, 0.0), 0.0, cpoly([(-10.8, -34.4), (-7.8, -39.2), (-2.0, -42.4), (-2.6, -40.4), (-6.6, -37.8), (-8.6, -33.4)]), cl, None))
clothes(put("cowl_fold", "chest", (0.0, 0.0), 0.0, cpoly([(-4.0, -41.6), (0.0, -38.0), (3.6, -34.4), (3.0, -34.2), (-0.8, -37.6), (-4.6, -41.0)], sharp=(0, 2, 3, 5)), cs, None, opacity=0.6))
clothes(put("brooch", "chest", (-6.4, -38.0), 0.0, circ(2.1), "$brass", INK_HAIR))
clothes(put("brooch_in", "chest", (-6.4, -38.0), 0.0, circ(1.0), "$crimson.dark", None))
clothes(put("brooch_lit", "chest", (-7.1, -38.7), 0.0, circ(0.5), "$brass.light", None))

# the shoulder line under the neck: the trapezius sloping from the skull base out to both
# acromions, the clavicles across the front. Covered by the cowl; the mannequin shows them.
wear(put("trapezius", "chest", (0.0, 0.0), 0.0, cpoly([(-3.4, -43.6), (0.6, -44.6), (7.4, -41.4), (6.2, -39.6), (-2.0, -41.6), (-8.8, -38.4), (-9.4, -37.2)], sharp=(0, 1, 2)), SKIN[1], None, opacity=0.5), SKIN[1])
wear(put("trapezius_lit", "chest", (0.0, 0.0), 0.0, cpoly([(-3.0, -43.0), (0.4, -43.8), (-1.4, -41.6), (-7.0, -38.8)]), SKIN[2], None, opacity=0.7), SKIN[2])
wear(put("clavicle", "chest", (0.0, 0.0), 0.0, cpoly([(1.2, -40.6), (7.0, -39.8), (7.0, -39.2), (1.0, -39.9), (-5.6, -38.8), (-5.6, -39.4)], sharp=(0, 1, 2, 3, 4, 5)), "$ink@0.3", None), "$ink@0.3")
# the neck: 0.45 of a head deep, leaning forward off the shoulders; the sternocleidomastoid runs
# from behind the ear down to the notch of the collarbones, and the throat is in the jaw's shade
wear(limb("neck", "neck", cpoly([(-1.2, -3.4), (3.5, -3.2), (7.6, -3.0), (8.0, 0.0), (7.6, 3.0), (3.5, 3.5), (-1.2, 3.9)]), SKIN[0], INK_HAIR), SKIN[0])
wear(limb("neck_shade", "neck", cpoly([(3.6, -2.2), (7.2, -2.4), (7.6, 2.0), (5.2, 3.0), (3.0, 1.6)]), SKIN[1], None), SKIN[1])        # under the jaw
wear(limb("sternomastoid", "neck", cpoly([(-0.6, 2.4), (2.4, 1.0), (5.4, -0.6), (7.0, -1.4), (7.2, -0.4), (5.6, 0.6), (2.8, 2.2), (-0.4, 3.4)], sharp=(0, 3, 4, 7)), SKIN[2], None, opacity=0.6), SKIN[2])
wear(limb("throat_line", "neck", rect(3.6, 0.5, 0.2), "$ink@0.22", None, along=3.0, across=-2.0, rot=6.0), "$ink@0.22")

# ---- the head, on its bone: along is up the skull, across is forward. One
# profile from the crown round the face to the nape. The face is in thirds:
# the brow a third of the way down from the hairline, the nose's base a third
# above the chin, the eye on the skull's midline (half way from crown to chin),
# the mouth a third of the way from the nose to the chin, the ear between the
# brow and the nose's base, set just behind the skull's mid-depth.
CROWN, CHIN = 16.9, 0.4
EYE_LINE = (CROWN + CHIN) / 2          # 8.65
BROW_LINE, NOSE_BASE, MOUTH_LINE = 11.2, 5.9, 4.1
HEAD_C = [(CROWN, -0.4), (16.0, 4.6), (13.6, 6.0), (BROW_LINE, 6.9), (10.0, 6.2), (8.0, 7.4), (6.6, 8.6), (NOSE_BASE, 7.5), (5.3, 6.2), (4.7, 6.8), (MOUTH_LINE, 6.3), (3.4, 6.7), (2.4, 5.8), (1.3, 6.2), (CHIN, 4.0), (0.6, 0.0), (2.0, -3.4), (4.6, -5.8), (9.0, -7.4), (13.6, -6.3), (16.4, -3.4)]
HEAD_SHARP = (6, 14)
limb("head", "head", cpoly(HEAD_C, sharp=HEAD_SHARP), SKIN[0], INK_THIN)
limb("jaw_shade", "head", cpoly([(0.9, -2.6), (0.8, 1.4), (1.6, 4.4), (3.2, 4.8), (2.8, 1.8), (3.0, -1.8)]), SKIN[1], None)
limb("temple_shade", "head", cpoly([(12.6, 1.0), (11.0, 2.8), (9.4, 2.4), (9.6, 0.6), (11.2, -0.4)]), SKIN[1], None, opacity=0.45)
limb("cheek_lit", "head", cpoly([(8.2, 2.6), (7.4, 5.0), (6.0, 5.4), (5.6, 3.6), (6.8, 2.0)]), SKIN[2], None, opacity=0.55)          # the zygomatic
limb("cheek_shade", "head", cpoly([(5.6, 3.0), (5.0, 5.4), (3.8, 4.8), (3.6, 3.2), (4.6, 2.2)]), SKIN[1], None, opacity=0.5)       # under it
limb("brow_lit", "head", ell(2.2, 1.7), SKIN[2], None, along=13.2, across=3.6, rot=-24.0)
limb("hair", "head", cpoly([(13.6, 5.6), (16.2, 4.0), (17.4, 0.8), (16.8, -3.2), (14.6, -6.2), (10.6, -7.8), (6.8, -7.2), (4.6, -5.4), (5.2, -4.4), (7.4, -5.6), (10.0, -6.0), (13.0, -4.6), (15.0, -1.6), (15.2, 2.0), (14.0, 4.4)], sharp=(0, 7, 8, 14)), "$hair", INK_HAIR)
limb("hair_lit", "head", ell(1.6, 3.2), "$hair.light", None, along=15.4, across=-1.4, rot=22.0)
# the ear: from the brow line to the nose's base, the helix curling at the back, the lobe at the front
limb("ear", "head", cpoly([(11.0, -2.0), (10.6, -3.5), (8.8, -4.2), (7.0, -3.7), (6.0, -2.2), (6.6, -0.7), (8.2, -0.3), (10.2, -0.8)]), SKIN[0], INK_HAIR)
limb("ear_in", "head", cpoly([(10.0, -2.2), (9.6, -3.2), (8.2, -3.4), (7.2, -2.4), (7.6, -1.2), (8.8, -1.0)]), SKIN[1], None)
limb("ear_lobe", "head", ell(0.7, 0.9), SKIN[2], None, along=6.9, across=-1.5, opacity=0.6)
# the hood, up: a C around the skull with a peak over the brow, open at the
# face, its lining showing crimson along the opening, the face in its shadow
HOOD_EDGE = [(-2.8, 0.6), (2.8, 2.4), (8.2, 2.8), (12.0, 5.2), (14.8, 8.8)]
HOOD_OUT = [(18.6, 4.4), (19.8, -1.6), (17.6, -8.0), (11.6, -11.4), (4.4, -11.6), (-1.6, -9.6), (-4.2, -5.4), (-4.4, -1.2)]
clothes(limb("hood_shadow", "head", cpoly([(-1.6, 0.8), (3.2, 2.8), (8.2, 3.2), (11.6, 5.4), (13.2, 8.0), (11.0, 7.6), (8.6, 5.4), (3.4, 5.2), (-0.4, 3.4)]), "$ink@0.42", None))
clothes(limb("hood", "head", cpoly(HOOD_EDGE + HOOD_OUT, sharp=(0, 4, 5)), cb, INK_THIN))
clothes(limb("hood_shade", "head", cpoly([(-3.6, -1.2), (-3.4, -5.0), (-1.0, -8.6), (4.6, -10.4), (4.6, -8.0), (0.2, -6.4), (-1.8, -3.6), (-2.0, -1.0)]), cs, None))
clothes(limb("hood_lit", "head", cpoly([(15.2, 7.6), (18.0, 4.0), (18.8, -1.4), (16.8, -6.8), (15.4, -5.8), (17.0, -1.4), (16.2, 3.0), (13.8, 6.2)]), cl, None))
for k, (a, b) in enumerate((((16.6, 1.0), (10.0, -8.8)), ((13.8, 4.8), (6.2, -7.2)))):
    clothes(limb(f"hood_fold_{k}", "head", cpoly([a, ((a[0] + b[0]) / 2 - 0.8, (a[1] + b[1]) / 2), b, (b[0] + 0.5, b[1] + 0.6), ((a[0] + b[0]) / 2 - 0.1, (a[1] + b[1]) / 2 + 0.5), (a[0] + 0.5, a[1] + 0.5)], sharp=(0, 2, 3, 5)), cs, None, opacity=0.5))
clothes(limb("hood_rim", "head", cpoly([(18.4, 3.4), (19.2, -1.6), (17.2, -7.4), (16.6, -7.0), (18.4, -1.6), (17.6, 3.0)], sharp=(0, 2, 3, 5)), "$cloak.light2", None, opacity=0.7))
clothes(limb("hood_lining", "head", cpoly(HOOD_EDGE + [(13.4, 9.0), (11.0, 6.6), (8.0, 4.4), (2.8, 4.0), (-2.2, 2.4)], sharp=(0, 4, 5, 9)), "$crimson", None))
clothes(limb("hood_lining_dark", "head", cpoly([(-2.8, 0.6), (2.8, 2.4), (2.8, 4.0), (-2.2, 2.4)], sharp=(0, 1, 2, 3)), "$crimson.dark", None))
# the eye on the midline: a wedge pointing forward, the white behind the iris, the lid folded over it, lashes dark;
# the brow a tapered stroke thickest toward the nose
limb("eye_white", "head", cpoly([(EYE_LINE + 0.9, 3.2), (EYE_LINE + 0.6, 5.6), (EYE_LINE - 0.7, 5.4), (EYE_LINE - 0.9, 3.4)]), "$bone", None, opacity=0.9)
limb("eye", "head", ell(0.75, 0.65), "$ink", None, along=EYE_LINE, across=4.9)
limb("eye_glint", "head", circ(0.3), "$white", None, along=EYE_LINE + 0.3, across=4.6, opacity=0.85)
limb("lid", "head", cpoly([(EYE_LINE + 1.4, 2.8), (EYE_LINE + 1.1, 4.4), (EYE_LINE + 0.7, 5.9), (EYE_LINE + 0.2, 5.8), (EYE_LINE + 0.5, 4.6), (EYE_LINE + 0.7, 3.2)], sharp=(0, 2, 3, 5)), SKIN[1], None)
limb("lash", "head", cpoly([(EYE_LINE + 0.8, 3.0), (EYE_LINE + 0.6, 4.6), (EYE_LINE + 0.4, 5.9), (EYE_LINE + 0.1, 5.8), (EYE_LINE + 0.3, 4.6), (EYE_LINE + 0.5, 3.1)], sharp=(0, 2, 3, 5)), "$ink@0.7", None)
limb("brow", "head", cpoly([(BROW_LINE + 0.5, 2.6), (BROW_LINE + 0.8, 4.6), (BROW_LINE + 0.4, 6.7), (BROW_LINE - 0.5, 6.6), (BROW_LINE - 0.2, 4.7), (BROW_LINE - 0.1, 2.9)], sharp=(0, 2, 3, 5)), "$hair", None)
# the nose: the wing (ala) curling back from the tip, the nostril under it, the bridge lit
limb("nose_bridge_lit", "head", cpoly([(10.2, 5.8), (8.4, 6.8), (7.2, 7.6), (7.0, 6.8), (8.2, 6.1), (9.8, 5.3)], sharp=(0, 2, 3, 5)), SKIN[2], None, opacity=0.6)
limb("nose_wing", "head", cpoly([(7.2, 5.2), (6.4, 6.4), (5.6, 6.2), (5.6, 5.0), (6.4, 4.6)]), SKIN[1], None, opacity=0.5)
limb("nostril", "head", ell(0.35, 0.55), "$ink@0.6", None, along=NOSE_BASE - 0.2, across=6.6)
# the mouth: the line between the lips from the corner forward, the upper lip in shade, the lower lip lit
limb("mouth", "head", cpoly([(MOUTH_LINE + 0.25, 4.2), (MOUTH_LINE + 0.15, 5.4), (MOUTH_LINE, 6.5), (MOUTH_LINE - 0.3, 6.4), (MOUTH_LINE - 0.2, 5.4), (MOUTH_LINE - 0.15, 4.3)], sharp=(0, 2, 3, 5)), "$ink@0.65", None)
limb("lip_upper", "head", cpoly([(5.2, 5.6), (4.8, 6.6), (MOUTH_LINE + 0.1, 6.4), (MOUTH_LINE + 0.2, 5.2)]), SKIN[1], None, opacity=0.55)
limb("lip_lower_lit", "head", ell(0.45, 0.8), SKIN[2], None, along=MOUTH_LINE - 0.7, across=6.3)
limb("chin_lit", "head", ell(0.9, 0.7), SKIN[2], None, along=1.6, across=5.4, opacity=0.6)

# ---- near side, over everything; the sword's grip lies in the fist and the blade runs on past it
def sword_grip():
    b = "hand_n"
    clothes(limb("pommel", b, cpoly([(-3.4, -1.2), (-2.6, -2.2), (-1.0, -2.0), (-0.4, -0.2), (-1.0, 1.9), (-2.6, 2.2), (-3.6, 1.2)]), "$brass", INK_HAIR, across=0.4))
    clothes(limb("pommel_lit", b, circ(0.6), "$brass.light", None, along=-2.4, across=-0.5))
    clothes(limb("grip", b, rect(10.0, 2.6, 0.6), LEATHER[1], INK_HAIR, along=3.6, across=0.4))
    for i in range(5):
        clothes(limb(f"grip_wrap_{i}", b, rect(0.5, 2.6, 0.2), LEATHER[2], None, along=-0.4 + 2.0 * i, across=0.4, rot=18.0))
def sword_blade():
    b = "hand_n"
    clothes(limb("guard", b, cpoly([(9.4, -5.6), (10.6, -5.2), (11.9, -4.4), (11.9, 4.8), (10.6, 5.8), (9.4, 6.2), (9.0, 0.4)], sharp=(0, 1, 2, 3, 4, 5)), "$brass", INK_HAIR, across=0.4))
    clothes(limb("guard_lit", b, rect(1.0, 3.8, 0.3), "$brass.light", None, along=10.2, across=-2.6))
    clothes(limb("guard_shade", b, rect(1.0, 3.2, 0.3), "$brass.dark", None, along=11.0, across=3.2))
    clothes(limb("blade", b, cpoly([(11.6, -2.0), (16.0, -1.9), (30.0, -1.6), (44.0, -1.0), (51.4, 0.4), (44.0, 1.8), (30.0, 2.3), (16.0, 2.6), (11.6, 2.7)], sharp=(0, 4, 8)), "$steel", INK_HAIR, across=0.4))
    clothes(limb("blade_lit", b, cpoly([(12.4, -1.3), (30.0, -1.0), (44.0, -0.5), (46.0, 0.2), (44.0, 0.1), (30.0, 0.1), (12.4, 0.2)], sharp=(0, 3, 6)), "$steel.light", None, across=0.4))
    clothes(limb("fuller", b, cpoly([(15.0, 0.6), (30.0, 0.9), (41.0, 1.1), (41.0, 1.6), (30.0, 1.5), (15.0, 1.4)], sharp=(0, 2, 3, 5)), "$steel.dark", None, across=0.4))
    clothes(limb("ricasso", b, rect(2.4, 4.4, 0.3), "$steel.dark", None, along=12.8, across=0.7))
leg_parts("n", CLOTH, LEATHER, SKIN, INK_HAIR)
sword_grip()
arm_parts("n", CLOTH, LEATHER, SKIN, INK_HAIR)
sword_blade()

RIG.check()

HOOD = ["hood_shadow", "hood", "hood_shade", "hood_lit", "hood_rim", "hood_fold_0", "hood_fold_1", "hood_lining", "hood_lining_dark"]
variants = {
    "unhooded": {
        "description": "The hood thrown back: the same figure bareheaded, the hair and the ear showing over the cowl.",
        "remove": HOOD,
    },
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
    look = smooth(0.28, 0.46, t) * (1 - smooth(0.68, 0.86, t))     # a glance up and ahead, mid-loop
    pose = {"body": (1.4 * sway, -1.6 * breath, 1.2 * sway)}
    pose["spine"] = -1.4 * breath
    pose["chest"] = -2.6 * breath - 1.0 * look
    pose["neck"] = 1.6 * breath - 4.0 * look
    pose["head"] = 2.0 * breath - 5.0 * look - 0.8 * sway
    arms(pose, 3.2 * breath - 2.4 * sway, -2.6 * breath, 4.0 * look - 3.0 * breath, "n")
    arms(pose, -3.2 * breath + 2.4 * sway, -2.6 * breath, 0.0, "f")
    for i in range(3): pose[f"cape_{i}"] = -1.8 * cyc(t, -0.1 * (i + 1)) - 0.8 * breath
    return plant(pose, {"n": REST_ANKLE["n"], "f": REST_ANKLE["f"]}, {"n": 0.0, "f": 0.0})

# ---- walk: contact, recoil, passing, high — twice, the far leg half a loop behind
STRIDE = 18.0   # a step of 36px = 0.3 of stature — a relaxed walk; a brisk one is 0.4
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
    # Williams: contact, then DOWN (the recoil, the lowest point, a beat after the heel lands),
    # passing, then UP (the highest, a beat after passing); the head rides a beat behind the hips
    bob = 1.2 - 3.0 * math.sin(2 * math.pi * (t - 0.07)) ** 2
    pose = {"body": (0.6 * cyc(2 * t, 0.1), bob, 4.0 + 1.5 * cyc(2 * t, 0.15))}
    pose["spine"] = -1.0
    pose["chest"] = -2.0 - 1.0 * cyc(2 * t, 0.1)
    pose["neck"] = -1.0 - 1.2 * cyc(2 * t, -0.2)
    pose["head"] = 1.8 * cyc(2 * t, -0.3) - 1.5
    swing = math.cos(2 * math.pi * t)                                # +1: the near arm back, the far arm forward
    lag = math.cos(2 * math.pi * (t - 0.05))                         # the forearm a beat behind the upper arm
    pose["chest"] -= 2.2 * cyc(t, 0.02)                              # the shoulders turn against the hips, once a loop
    arms(pose, 26.0 * swing, -8.0 - 16.0 * (0.5 + 0.5 * lag), -4.0 + 7.0 * cyc(t, -0.12), "n")
    arms(pose, -26.0 * swing, -8.0 - 16.0 * (0.5 - 0.5 * lag), -4.0 - 7.0 * cyc(t, -0.12), "f")
    cape(pose, 7.0, 4.0, t)
    ankles, pitch = {}, {}
    for s, ph in (("n", 0.0), ("f", 0.5)):
        dx, lift, p = step(t + ph)
        ankles[s] = (HIP[s][0] + 1.0 + dx, ground_of(s) - FOOT_H - lift)
        pitch[s] = p
    return plant(pose, ankles, pitch)

# ---- run: a short stance that drives back, a flight, the heel kicking up behind and the knee driving through
RUN_STRIDE = 29.0   # a step of 58px ≈ 0.5 of stature — a run; a sprint is 0.6–0.7
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
        lift = 4.5 * (1 - s) + 19.0 * math.sin(math.pi * s ** 0.85)
        pitch = lerp(34.0, -4.0, smooth(0.15, 1.0, s))
    return dx, lift, pitch

def run_pose(t):
    bob = 2.5 - 7.0 * math.sin(2 * math.pi * (t - 0.2)) ** 2          # highest in flight, lowest mid-stance (the down, a beat after contact); 6% of stature
    pose = {"body": (1.0 * cyc(2 * t, 0.05), bob, 13.0 + 2.5 * cyc(2 * t, 0.15))}
    pose["spine"] = -1.5
    pose["chest"] = -4.0 - 2.0 * cyc(2 * t, 0.1)
    pose["neck"] = -3.0
    pose["head"] = -4.0 + 2.0 * cyc(2 * t, 0.2)
    swing = math.cos(2 * math.pi * t)
    lag = math.cos(2 * math.pi * (t - 0.04))
    pose["chest"] -= 3.0 * cyc(t, 0.02)
    arms(pose, 10.0 + 38.0 * swing, -78.0 - 14.0 * lag, -12.0 + 6.0 * cyc(t, -0.1), "n")
    arms(pose, 10.0 - 38.0 * swing, -78.0 + 14.0 * lag, -12.0 - 6.0 * cyc(t, -0.1), "f")
    cape(pose, 34.0, 6.0, t, 0.08)
    ankles, pitch = {}, {}
    for s, ph in (("n", 0.0), ("f", 0.5)):
        dx, lift, p = run_step(t + ph)
        ankles[s] = (HIP[s][0] + 3.0 + dx, ground_of(s) - FOOT_H - lift)
        pitch[s] = p
    return plant(pose, ankles, pitch)

# ---- the one-shots. Each is a pose function too, shaped in time with smooth():
# an anticipation eased into and held, a release that arrives fast, a recovery
# that settles. Sampled densely so the fast part survives linear keys.
def snap(a, b, t):
    """Like smooth(a, b, t) but arriving fast and settling — an expo-out release."""
    x = max(0.0, min(1.0, (t - a) / (b - a)))
    return 1.0 - (1.0 - x) ** 3

def arm_abs(pose, s, upper, fore, hand):
    pose[f"abs:arm_{s}_upper"] = upper; pose[f"abs:arm_{s}_fore"] = fore; pose[f"abs:hand_{s}"] = hand

def rest_arm(s):
    return ARM_REST[s]

def blend(a, b, k):
    """Three headings lerped, the short way round."""
    return tuple(x + wrap(y - x) * k for x, y in zip(a, b))

# attack: the sword drawn back and up over the near shoulder as the body coils
# onto its back foot, held, then thrown forward and down across the front in a
# lunge, the far foot stepping into it; the follow-through carries the blade
# low before it comes home.
ATK_LIFT = (120.0, 170.0, 300.0)     # upper, fore, hand: on the way up, the blade lifted in front of the chest
ATK_WIND = (190.0, 245.0, 320.0)     # the blade up and forward over the shoulder
ATK_HIT = (45.0, 30.0, 25.0)         # the blade out and level in front
ATK_THROUGH = (75.0, 80.0, 95.0)     # carried down past the hit
FAR_WIND = (40.0, 20.0, 15.0)        # the far arm reaching forward for balance
FAR_HIT = (150.0, 170.0, 175.0)      # flung back
def attack_pose(t):
    lift = smooth(0.0, 0.15, t)
    wind = smooth(0.12, 0.28, t)
    rel = snap(0.40, 0.50, t)
    through = smooth(0.50, 0.66, t)
    home = smooth(0.66, 1.0, t)
    trem = 0.6 * math.sin(2 * math.pi * 9 * t) * smooth(0.26, 0.32, t) * (1 - smooth(0.36, 0.40, t))
    near = blend(rest_arm("n"), ATK_LIFT, lift)
    near = blend(near, ATK_WIND, wind)
    near = blend(near, ATK_HIT, rel)
    near = blend(near, ATK_THROUGH, through)
    near = blend(near, rest_arm("n"), home)
    farv = blend(rest_arm("f"), FAR_WIND, wind)
    farv = blend(farv, FAR_HIT, rel)
    farv = blend(farv, rest_arm("f"), home)
    dx = lerp(lerp(0.0, -3.0, wind), 7.0, rel); dx = lerp(dx, 0.0, home)
    dy = lerp(lerp(0.0, 2.0, wind), 3.5, rel); dy = lerp(dy, 0.0, home)
    th = lerp(lerp(0.0, -7.0, wind), 14.0, rel); th = lerp(th, 0.0, home)
    pose = {"body": (dx, dy, th + trem)}
    pose["chest"] = lerp(lerp(0.0, -5.0, wind), 8.0, rel) * (1 - home)
    pose["neck"] = lerp(lerp(0.0, 3.0, wind), -6.0, rel) * (1 - home)
    pose["head"] = lerp(lerp(0.0, 4.0, wind), -6.0, rel) * (1 - home)
    arm_abs(pose, "n", *[a + trem * 2 for a in near])
    arm_abs(pose, "f", *farv)
    # the cloak lags the lunge: forward as the body coils back, then thrown back and settling
    for i in range(3):
        pose[f"cape_{i}"] = lerp(lerp(0.0, 8.0, smooth(0.08 + 0.05 * i, 0.4, t)), -28.0 + 6.0 * i, snap(0.44 + 0.04 * i, 0.62, t)) * (1 - smooth(0.7 + 0.05 * i, 1.0, t))
    # feet: the near stays; the far steps forward on the release and comes back home
    step_f = lerp(0.0, 11.0, rel) * (1 - home)
    lift_f = 5.0 * math.sin(math.pi * max(0.0, min(1.0, (t - 0.38) / 0.16))) if 0.38 < t < 0.54 else 0.0
    ankles = {"n": REST_ANKLE["n"], "f": (REST_ANKLE["f"][0] + step_f, REST_ANKLE["f"][1] - lift_f)}
    pitch = {"n": lerp(0.0, 22.0, rel) * (1 - home), "f": -8.0 * (lift_f / 5.0)}
    return plant(pose, ankles, pitch)

# hurt: the blow has already landed — the head snaps back, the body is knocked
# off its line, the arms go wide, and it recovers. Laid over the walk or the
# idle by the game, so the feet stay.
def hurt_pose(t):
    hit = 1 - smooth(0.0, 0.08, t) * 0.0          # on from the first frame
    back = snap(0.0, 0.12, t) * (1 - smooth(0.3, 1.0, t))
    pose = {"body": (-4.0 * back, 1.5 * back, -9.0 * back)}
    pose["chest"] = -6.0 * back
    pose["neck"] = -8.0 * back
    pose["head"] = -10.0 * back
    near = blend(rest_arm("n"), (60.0, 40.0, 35.0), back)
    farv = blend(rest_arm("f"), (120.0, 110.0, 105.0), back)
    arm_abs(pose, "n", *near); arm_abs(pose, "f", *farv)
    for i in range(3): pose[f"cape_{i}"] = 14.0 * snap(0.02 + 0.04 * i, 0.2, t) * (1 - smooth(0.35 + 0.05 * i, 1.0, t))
    return plant(pose, {"n": REST_ANKLE["n"], "f": REST_ANKLE["f"]}, {"n": 0.0, "f": 0.0})

# death: caught — the blow lands and holds the body up for a beat — then let
# go: the knees fold, the body comes down onto them, the sword arm drops until
# the point rests on the ground, the head bows, the cloak settles over it.
# Still by 0.85 (the app's oneShot rule samples a frame short).
def death_pose(t):
    t = min(t, 0.85)
    caught = snap(0.0, 0.08, t) * (1 - smooth(0.12, 0.3, t))
    fold = smooth(0.12, 0.5, t)
    down = smooth(0.42, 0.72, t)
    bow = smooth(0.6, 0.85, t)
    dy = 22.0 * fold + 6.0 * down - 1.5 * caught
    th = -6.0 * caught + 16.0 * fold + 18.0 * down
    pose = {"body": (-3.0 * caught + 2.0 * fold, dy, th)}
    pose["spine"] = 6.0 * down
    pose["chest"] = -4.0 * caught + 8.0 * fold + 10.0 * bow
    pose["neck"] = -6.0 * caught + 10.0 * fold + 14.0 * bow
    pose["head"] = -8.0 * caught + 12.0 * fold + 18.0 * bow
    near = blend(rest_arm("n"), (70.0, 50.0, 45.0), caught)
    near = blend(near, (40.0, 60.0, 70.0), fold)       # the arm drops forward, the point reaching for the ground
    near = blend(near, (30.0, 70.0, 80.0), bow)
    farv = blend(rest_arm("f"), (110.0, 100.0, 95.0), caught)
    farv = blend(farv, (60.0, 75.0, 80.0), fold)
    farv = blend(farv, (50.0, 85.0, 90.0), bow)
    arm_abs(pose, "n", *near); arm_abs(pose, "f", *farv)
    for i in range(3): pose[f"cape_{i}"] = 10.0 * caught - (22.0 - 4.0 * i) * fold + (6.0 + 2.0 * i) * bow
    # the feet slide back as the knees come down in front of them
    ankles = {s: (REST_ANKLE[s][0] - 14.0 * fold - 2.0 * down, REST_ANKLE[s][1]) for s in ("n", "f")}
    pitch = {s: 30.0 * fold for s in ("n", "f")}
    return plant(pose, ankles, pitch)

# roll: a forward dodge. The body drops and tucks — knees to the chest, the
# heels up, the sword arm folded in, the head down — turns over once about
# the hips as it goes, and comes up out of it onto its feet.
def abs_legs(pose):
    """The leg bones' world headings under `pose`, as abs: entries."""
    w = RIG.solve(pose)
    return {f"abs:{n}": w[n][2] for s in ("n", "f") for n in (f"leg_{s}_thigh", f"leg_{s}_shin", f"foot_{s}")}
TUCK_LEGS = {"leg_n_thigh": -120.0, "leg_n_shin": 135.0, "foot_n": 20.0, "leg_f_thigh": -110.0, "leg_f_shin": 130.0, "foot_f": 20.0}
def roll_pose(t):
    tuck = smooth(0.0, 0.2, t) * (1 - smooth(0.78, 0.98, t))
    turn = 360.0 * smooth(0.12, 0.84, t)
    drop = 30.0 * smooth(0.0, 0.2, t) * (1 - smooth(0.8, 1.0, t))
    pose = {"body": (0.0, drop, turn)}
    pose["spine"] = 10.0 * tuck
    pose["chest"] = 18.0 * tuck
    pose["neck"] = 22.0 * tuck
    pose["head"] = 24.0 * tuck
    # arms folded in, the sword along the shin; headings relative to the turning body
    for s, (u, f, h) in (("n", (-20.0, -110.0, -20.0)), ("f", (-30.0, -100.0, -20.0))):
        pose[f"arm_{s}_upper"] = u * tuck; pose[f"arm_{s}_fore"] = f * tuck; pose[f"hand_{s}"] = h * tuck
    for i in range(3): pose[f"cape_{i}"] = -(30.0 - 8.0 * i) * tuck
    # legs: planted at rest, tucked in the air, blended by heading
    planted = abs_legs(plant(dict(pose), {"n": REST_ANKLE["n"], "f": REST_ANKLE["f"]}, {"n": 0.0, "f": 0.0}))
    tucked = abs_legs({**pose, **TUCK_LEGS})
    for k in planted:
        pose[k] = planted[k] + wrap(tucked[k] - planted[k]) * tuck
    return pose

animations = {
    "idle": {
        "description": "The breath and the weight: the chest lifts and the shoulders rise on the in-breath, the head nods back a degree, the arms hang and drift and the sword's point with them, the cloak stirs; the hips settle from foot to foot with the feet planted, and mid-loop the head comes up to look ahead.",
        "duration": 2.4,
        "tracks": tracks(idle_pose, keyset(16)),
    },
    "walk": {
        "description": "Contact, recoil, passing, high — twice a loop, the far leg half a loop behind the near. Each ankle is solved to the ground: the heel lands toe-up, the foot flattens and slides back under the body, the heel lifts and pushes off, and the leg swings through bent with the toe hanging. The body is lowest on contact and highest passing, leaning four degrees into the walk; the arms swing against the leg on their side, the elbow bending as the arm comes forward; the cloak trails and sways a beat behind each step, further down the hem.",
        "duration": 1.0,                                               # two steps: 120 steps a minute, the walking cadence
        "cues": {"contact": 0.0, "contact_far": 0.5},
        "tracks": tracks(walk_pose, keyset(20)),
    },
    "run": {
        "description": "A short stance that lands under the body and drives back, then flight: the heel kicks up high behind, the knee drives forward and the foot reaches down for the next step. The body leans thirteen degrees, is highest in the air and lowest mid-stance; the arms pump bent at the elbow, fists closed, against the leg on their side; the cloak streams out behind.",
        "duration": 0.64,                                              # two steps: ~190 a minute, a run's cadence
        "cues": {"contact": 0.0, "contact_far": 0.5},
        "tracks": tracks(run_pose, keyset(20)),
    },
    "attack": {
        "description": "A slash. The sword is drawn back and up over the near shoulder as the body coils onto its back foot and the far arm reaches forward — held, trembling with the load — then thrown forward and down across the front in a lunge, the far foot stepping into it, the cloak flung back; the follow-through carries the blade low before everything comes home. `release` is the frame the blade starts, `contact` where it is level in front.",
        "duration": 0.55,
        "cues": {"windup": 0.0, "release": 0.40, "contact": 0.50},
        "tracks": tracks(attack_pose, keyset(30)),
    },
    "hurt": {
        "description": "Struck: the head snaps back, the body is knocked off its line, the arms go wide and the cloak jumps forward; it recovers over the second half. Arrives on its first frame — a hit has no anticipation — and is laid over the walk or the idle, so the feet stay.",
        "duration": 0.3,
        "tracks": tracks(hurt_pose, keyset(18)) + [
            {"part": p, "prop": "tint", "to": "$white", "keys": [[0, 0.85, "hold"], [0.12, 0.85, "linear"], [0.3, 0, "linear"], [1, 0]]}
            for p in ("hood", "cowl", "torso", "hips", "thigh_n", "shin_n", "arm_n_upper", "cape_0")],
    },
    "death": {
        "description": "The last chapter: caught on the blow — held up by it for a beat — then let go: the knees fold and the body comes down onto them as the feet slide back, the sword arm drops until the point rests on the ground, the head bows and the cloak settles over the back. Still from 0.85.",
        "duration": 1.2,
        "cues": {"down": 0.6},
        "tracks": tracks(death_pose, [i / 20 for i in range(18)] + [0.85, 1.0]),
    },
    "roll": {
        "description": "A forward dodge: the body drops and tucks — knees to the chest, heels up, the sword arm folded in, the head down — turns over once about the hips as it goes, and comes up out of it onto its feet. Played in place; the game carries it forward.",
        "duration": 0.5,
        "tracks": tracks(roll_pose, keyset(30)),
    },
}

# ============================================================== 5. the document
# ============================================================== 5. the document
DESCRIPTION = (
    "A human figure drawn to proportion: seven and a half heads, one head 16px, standing 120px with the origin at the hips and the soles at +60. "
    "Seen three-quarter from the side, facing +x and mirrored by the engine: the near (right) shoulder a little behind and below the far one, "
    "the far arm hanging by the chest's line and drawn under it, the near arm over it; the far limbs a step darker, the far foot a pixel higher. "
    "A wanderer: the hood up and the face in its shadow with the lining showing crimson at the edge, a cloak off the shoulders in three hinged segments ending in a torn hem, "
    "a leather jerkin laced down the front and belted at the waist with a brass buckle and a pouch on the near hip, dark cloth under it, wrapped bracers, gloves, "
    "tall boots with the cuff turned under the knee, and a longsword carried point-down in the near fist. "
    "Every outline is a closed curve through a few control points and the masses are drawn as muscle — deltoid, biceps and triceps, the forearm full under the elbow, quadriceps and hamstring, the calf high — the trunk one shape from the shoulders to under the belt and one over the hips; a head with a brow ridge, a nose, lips and a chin; a fist with its fingers; a boot with a heel, a toe cap and an ankle strap; a baldric across the chest, a brooch closing the cowl, stitching down the jerkin's back. "
    "Every mass carries a shade along its front edge and the bigger ones a light along the back; lit from the upper left. The rest is a contrapposto: the weight on the far leg, the near knee eased, the elbows bent, the head a few degrees down. "
    "Built on a skeleton (scripts/human.py): the pelvis is the root, the spine a shallow S of lumbar, chest, neck and head, each arm hinged at the shoulder, elbow and wrist, "
    "each leg a thigh and shin solved every frame to an ankle on the ground with the foot hinged at the ankle, the cloak a chain of three bones that lags the body. "
    "`bare` is the mannequin underneath. Gameplay radius 14, height 120."
)

doc = {
    "id": "human.char.wanderer",
    "name": "Wanderer",
    "description": DESCRIPTION,
    "tags": ["char", "player"],
    "size": [192, 192],
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
