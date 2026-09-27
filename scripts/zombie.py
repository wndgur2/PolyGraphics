"""The Husk — a drone that ran out of scent, walked again by a graft.

    python3 scripts/zombie.py        # rewrites apps/ss/assets/ss-enemy-zombie.json

The flats' slow heavy chaser (feelers `zombie`: speed 56, radius 11, hp 14),
arriving in dozens from the second wave on. So the drawing's job is a
silhouette and a rhythm, not detail: tall and pale where the Tracker is low and
amber, and a gait that is visibly wrong — lopsided, not merely slow.

It was hand-placed, and its shamble moved six pixels at game scale: rects
turned a few degrees about their own centres, a torso that swayed in place.
This rebuilds it on the shared rig (scripts/rig.py):

  - a pelvis root that rides the gait, a spine of two bones (waist and a
    hunched chest), a neck and a head that hangs forward off it, a jaw hinged
    under the head and a snapped feeler stub on top
  - two arms off the front of the hunch: the near one long, hanging in front of
    the belly (clear of the graft) past the knee and
    swinging a beat behind the body; the far one short and withered, crooked
    forward at chest height
  - two legs solved every frame to a foot on the ground (two-bone IK). The
    near leg walks; the far leg is the stiff one — the pelvis is hiked over it
    so it can swing through straight with its toe dragging, and the body
    vaults over it when it is planted. That is the limp.

The game mirrors it to face its heading (EnemySystem `faceSide`) and plays the
clip at a fixed rate — `zombie` has no `animTracksSpeed` — so the feet cannot
be matched to its 56 px/s and are not trying to be: at 1.1s a loop the body
covers ~62px of floor a cycle, far more than any stride this canvas can draw.
The drag reads as a drag at any speed; that is the point of drawing a limp.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 32×36, origin at the centre, +x forward, +y down.
SIZE = [32, 36]
GROUND = 14.6
PELVIS = (-1.2, 2.6)

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, PELVIS, 0.0)
# Waist straight up, the chest bent forward over it — the hunch.
bone("spine", "body", PELVIS, -80.0, 6.0)
bone("chest", "spine", RIG.end_of("spine"), -58.0, 6.6)
bone("neck", "chest", RIG.end_of("chest"), 18.0, 3.2)
bone("head", "neck", RIG.end_of("neck"), 50.0, 6.6)
HEAD_AT = RIG.end_of("neck")
def head_pt(along, across):
    """A point in the head's rest frame (along the skull, down-forward; across, + is the underside)."""
    h = R(BONES["head"].heading)
    return (HEAD_AT[0] + along * math.cos(h) - across * math.sin(h), HEAD_AT[1] + along * math.sin(h) + across * math.cos(h))
bone("jaw", "head", head_pt(3.8, 1.9), 62.0, 4.2)
bone("feeler", "head", head_pt(0.8, -2.8), -128.0, 4.4)

# The arms, hung off the shoulder at the top of the chest.
# The shoulder is on the front of the hunch, under the neck, so the long arm
# hangs in front of the belly — clear of the graft, and a line of its own in
# the silhouette rather than a stripe across the torso.
SHOULDER = (4.3, -7.2)
ARMS = {  # side: (shoulder, [(length, heading)...]) upper, fore, claw
    "far": ((3.2, -7.8), [(4.6, 92.0), (4.0, 14.0), (2.2, 52.0)]),
    "near": (SHOULDER, [(6.6, 92.0), (7.0, 86.0), (2.6, 70.0)]),
}
for side, (sh, links) in ARMS.items():
    p, parent = sh, "chest"
    for seg, (L, h) in zip(("upper", "fore", "claw"), links):
        b = bone(f"{side}_{seg}", parent, p, h, L)
        p, parent = b.end(), b.name

# The legs. The near leg is a working leg with a bent knee; the far leg is
# the stiff one, its rest nearly straight.
LEGS = {  # leg: (hip, rest foot x, thigh, shin)
    "far": ((-2.4, 2.4), -3.2, 6.1, 6.2),
    "near": ((-0.4, 3.2), 1.0, 6.2, 6.3),
}
for leg, (hip, fx, l1, l2) in LEGS.items():
    h1, h2 = ik(hip, (fx, GROUND), l1, l2, 1)
    bone(f"{leg}_thigh", "body", hip, h1, l1)
    bone(f"{leg}_shin", f"{leg}_thigh", RIG.end_of(f"{leg}_thigh"), h2, l2)
    bone(f"{leg}_foot", f"{leg}_shin", RIG.end_of(f"{leg}_shin"), 0.0, 2.8)

RIG.seal()
solve = RIG.solve
put, on_bone, use = RIG.put, RIG.on_bone, RIG.use

# ============================================================== parts
# Three values of bleached bone: the head and shoulders the lightest thing,
# the torso the body tone, the far limbs two steps down. The graft is the
# hive's own dark carapace, which is why it reads as something added.
FAR, NEAR, BODY, LIT = "$husk.dark", "$husk", "$husk", "$husk.light"
SEAM = "$husk.dark2"

def seg(id, bone_name, w0, w1, fill, stroke=INK_HAIR):
    at, a = on_bone(bone_name)
    return put(id, bone_name, at, a, bar(BONES[bone_name].length, w0, w1), fill, stroke)

def foot(id, bone_name, fill, stroke=INK_HAIR):
    at, a = on_bone(bone_name)
    # A clawed foot: heel under the ankle, two toes forward.
    return put(id, bone_name, at, a, poly([(-1.2, -0.8), (0.6, -1.3), (2.4, -0.9), (3.6, 0.2), (2.6, 0.5), (3.2, 1.1),
                                          (1.2, 1.1), (-1.0, 1.0), (-1.5, 0.2)]), fill, stroke)

def arm(side, fill, lit):
    w = (2.8, 2.4, 2.0) if side == "near" else (2.4, 2.0, 1.7)
    seg(f"arm_{side}_upper", f"{side}_upper", w[0], w[1] * 0.95, fill)
    seg(f"arm_{side}_fore", f"{side}_fore", w[1], w[2], fill)
    at, a = on_bone(f"{side}_claw")
    L = BONES[f"{side}_claw"].length
    # A hooked claw, not a hand: the drone's own tarsus.
    put(f"arm_{side}_claw", f"{side}_claw", at, a,
        poly([(-0.6, -1.1), (L * 0.6, -1.2), (L + 1.0, -0.2), (L + 1.4, 1.2), (L + 0.4, 0.6), (L * 0.5, 0.9), (-0.6, 0.9)]), lit, INK_HAIR)

# ---- far side: the stiff leg and the short arm, behind everything
seg("leg_far_thigh", "far_thigh", 3.4, 2.8, FAR)
seg("leg_far_shin", "far_shin", 2.8, 2.2, FAR)
foot("leg_far_foot", "far_foot", FAR)
arm("far", FAR, NEAR)

# ---- the torso: the waist, the hunched chest over it, the crack down the
# front, two ribs showing through, the graft and its organ
at, a = on_bone("spine")
put("waist", "spine", at, 0.0, poly([(-3.4, 1.8), (-3.8, -1.4), (-3.0, -5.2), (2.2, -6.6), (3.6, -3.2), (3.4, 0.6), (2.2, 2.6), (-1.6, 3.2)]),
    FAR, INK_THIN)
at, a = on_bone("chest")
CHEST_AT = at
put("torso", "chest", at, 0.0,
    poly([(-3.8, 0.8), (-4.4, -3.2), (-3.4, -6.8), (-0.8, -9.2), (2.6, -10.4), (5.4, -9.6), (6.4, -7.2), (5.8, -4.4),
          (4.6, -1.4), (3.2, 1.6), (0.2, 2.6)]), LIT, INK_THIN)
# The back in shade, the chest in the light: the mid value down the spine.
put("torso_shade", "chest", at, 0.0, poly([(-3.8, 0.6), (-4.3, -3.2), (-3.3, -6.6), (-0.8, -9.0), (0.2, -8.2), (-1.4, -5.6), (-2.0, -2.2), (-1.4, 1.4)]),
    NEAR)
# A rib showing through the belly, under the graft.
put("rib", "chest", (at[0] - 1.8, at[1] + 1.2), -10.0, rect(3.8, 0.9, 0.45), FAR)
CRACK = [(0.0, 0.0), (1.2, -1.8), (0.6, -3.4), (2.0, -5.2), (1.6, -6.6), (2.4, -5.0), (1.2, -3.4), (1.8, -1.8), (0.6, 0.4)]
# The crack runs from under the graft down the belly to the waist.
put("crack", "chest", (at[0] - 0.4, at[1] + 3.2), 0.0, poly(CRACK), SEAM)
GRAFT_AT = (at[0] + 0.1, at[1] - 3.4)
put("graft", "chest", GRAFT_AT, 14.0, {"kind": "ngon", "sides": 6, "r": 3.7}, "$carapace.dark", INK_HAIR)
use("organ", "chest", GRAFT_AT, "ss.lib.organ", scale=0.6, variant="faint")
# The second graft (elite): fresh, fully lit, in the hump of the back.
GRAFT2_AT = (at[0] - 2.0, at[1] - 7.6)
put("graft2", "chest", GRAFT2_AT, 20.0, {"kind": "ngon", "sides": 6, "r": 2.7}, "$carapace.dark", INK_HAIR, opacity=0)
use("organ2", "chest", GRAFT2_AT, "ss.lib.organ", scale=0.42, opacity=0)

# ---- the head: a drone's head capsule hung forward, the empty eye socket,
# a pinprick of the old signal in it, the jaw slack under it, and one feeler
# snapped to a stub
at, a = on_bone("feeler")
put("feeler", "feeler", at, a, poly([(-0.4, -0.7), (2.4, -0.6), (4.2, 0.0), (5.0, 1.4), (4.0, 1.0), (2.4, 0.6), (-0.4, 0.7)]), NEAR, INK_HAIR)
# The mandible hangs open under the snout on its own hinge.
at, a = on_bone("jaw")
put("jaw", "jaw", at, a, poly([(-0.8, -0.9), (1.6, -1.1), (3.6, -0.4), (4.4, 0.9), (3.0, 0.4), (1.2, 1.0), (-0.8, 0.9)]), NEAR, INK_HAIR)
# The head capsule: a drone's, long and wedge-shaped — a rounded crown at the
# neck tapering to the snout — hung face-down, so it reads as a skull and not
# as an eye.
at, a = on_bone("head")
HEAD = [(x * 1.2, y * 1.2) for x, y in [(-1.4, -0.4), (-0.6, -2.2), (1.4, -2.9), (3.8, -2.4), (5.8, -1.3), (6.6, 0.0), (6.0, 1.3), (3.8, 2.1), (1.2, 2.3), (-0.8, 1.4)]]
put("head", "head", at, a, poly(HEAD), LIT, INK_THIN)
put("head_shade", "head", at, a, poly([(x * 1.2, y * 1.2) for x, y in [(-0.8, 1.4), (1.2, 2.3), (3.8, 2.1), (6.0, 1.3), (6.3, 0.6), (3.8, 1.2), (1.0, 1.2), (-1.0, 0.6)]]), NEAR)
at, a = on_bone("head", 2.1, -1.1)
put("socket", "head", at, a, ell(1.8, 1.25), "$ink")
at, a = on_bone("head", 2.4, -1.0)
put("eye", "head", at, a, circ(0.55), "$pheromone@heavy")

# ---- near side: the working leg, then the long arm over the torso
seg("leg_thigh", "near_thigh", 3.8, 3.0, NEAR)
seg("leg_shin", "near_shin", 3.0, 2.3, NEAR)
foot("leg_foot", "near_foot", NEAR)
arm("near", NEAR, LIT)

RIG.check()

# ============================================================== motion
def plant_legs(pose, feet, bends=None, toes=None):
    """Solve both legs to put each foot at `feet[leg]`; `toes[leg]` tips the foot (degrees, + is toe down)."""
    world = solve(pose)
    for leg, (hip, fx, l1, l2) in LEGS.items():
        hx, hy, _ = world[f"{leg}_thigh"]
        h1, h2 = ik((hx, hy), feet[leg], l1, l2, (bends or {}).get(leg, 1))
        pose[f"abs:{leg}_thigh"] = h1
        pose[f"abs:{leg}_shin"] = h2
        pose[f"abs:{leg}_foot"] = (toes or {}).get(leg, 0.0)
    return pose

def hip_world(leg, pose):
    return solve(pose)[f"{leg}_thigh"][:2]

# ---- shamble: 1.1s, one limp. The near leg's stance is the long, heavy part
# of the loop and the stiff leg's is the short one, which is what makes the
# rhythm lopsided rather than a slow walk.
STRIDE = 4.2       # half a step, px either side of the rest foot
NEAR_SWING = (0.0, 0.40)   # the near leg is in the air here; the stiff leg carries
FAR_SWING = (0.46, 0.96)   # the stiff leg drags through here; the near leg carries

def foot_track(t, swing, lift):
    """Foot offset along x and lift for a leg that swings over `swing` and is planted the rest of the loop."""
    a, b = swing
    u = t % 1.0
    if a <= u < b:
        v = (u - a) / (b - a)
        return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), lift * math.sin(math.pi * v)
    # stance: slides back at one speed from +STRIDE at b to -STRIDE at a (+1)
    span = 1.0 - (b - a)
    v = ((u - b) % 1.0) / span
    return lerp(STRIDE, -STRIDE, v), 0.0

def bump(t, a, b):
    """0 → 1 → 0 across [a, b], wrapping."""
    u = (t - a) % 1.0
    w = (b - a) % 1.0
    return math.sin(math.pi * u / w) ** 2 if u < w else 0.0

def shamble_pose(t):
    ndx, nlift = foot_track(t, NEAR_SWING, 2.4)
    fdx, flift = foot_track(t, FAR_SWING, 0.25)
    # The lurch: when the near foot comes down, the body drops onto it and
    # pitches forward; while the stiff leg swings through, the hip hikes to
    # clear it and the body leans back; when the stiff leg is planted, the
    # body vaults up over it.
    drop = bump(t, 0.38, 0.66)
    hike = bump(t, 0.60, 0.98)
    vault = bump(t, 0.02, 0.36)
    dy = 3.2 * drop - 1.4 * hike - 1.0 * vault
    dx = 1.6 * cyc(t, 0.05)
    lean = 7.0 * drop - 6.0 * hike
    pose = {"body": (dx, dy, lean)}
    pose["spine"] = 5.0 * drop - 2.0 * vault
    pose["chest"] = 16.0 * drop - 7.0 * hike + 2.0 * vault
    lean += pose["spine"] + pose["chest"]
    # The head is carried, not held: it swings on after the chest, a beat late.
    pose["neck"] = -4.0 * bump(t, 0.46, 0.8) + 3.0 * bump(t, 0.9, 0.3)
    pose["head"] = 28.0 * bump(t, 0.5, 0.86) - 12.0 * bump(t, 0.92, 0.36)
    pose["jaw"] = 8.0 + 16.0 * bump(t, 0.54, 0.9)
    pose["feeler"] = -18.0 * bump(t, 0.56, 0.95) + 12.0 * bump(t, 0.02, 0.4)
    # The long arm hangs and is swung by the body, so it runs a beat behind
    # it; the forearm and the claw a beat behind that.
    pose["near_upper"] = -0.85 * lean + 24.0 * cyc(t, -0.12)
    pose["near_fore"] = 22.0 * cyc(t, -0.26)
    pose["near_claw"] = 26.0 * cyc(t, -0.4)
    # The short arm twitches: a jerk up on the lurch.
    pose["far_upper"] = -14.0 * bump(t, 0.4, 0.62) + 4.0 * cyc(t, 0.3)
    pose["far_fore"] = -10.0 * bump(t, 0.44, 0.7)
    pose["far_claw"] = 16.0 * bump(t, 0.46, 0.74)
    feet = {"near": (LEGS["near"][1] + ndx, GROUND - nlift), "far": (LEGS["far"][1] + fdx, GROUND - flift)}
    # The stiff leg never folds: while it drags, its knee is held nearly
    # straight by solving it with the knee thrown the other way, so a short
    # reach reads as a locked joint rather than a bend.
    toes = {"near": 16.0 * math.sin(math.pi * max(0.0, min(1.0, (t % 1.0) / 0.4))) - 6.0 * bump(t, 0.25, 0.45),
            "far": 8.0 * bump(t, FAR_SWING[0], FAR_SWING[1])}
    return plant_legs(pose, feet, toes=toes)

# ---- death: 0.46s. The grafts let go of a body that was already nobody:
# it jerks upright as both organs flare, then the knees go, the frame folds
# forward over them, the head drops and the long arm sprawls onto the floor.
# Still from 0.85.
WRIST_REST = (RIG.end_of("near_fore")[0] - SHOULDER[0], RIG.end_of("near_fore")[1] - SHOULDER[1])
DEATH_TS = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
def death_pose(t):
    jerk = math.sin(math.pi * smooth(0.0, 0.3, t))
    fall = smooth(0.18, 0.72, t)
    settle = math.sin(math.pi * smooth(0.62, 0.85, t)) * 0.5
    pose = {"body": (lerp(0.0, -1.6, fall), -0.3 * jerk + lerp(0.0, 7.0, fall) - settle, -4.0 * jerk + 16.0 * fall)}
    pose["spine"] = -4.0 * jerk + 10.0 * fall
    pose["chest"] = -6.0 * jerk + 16.0 * fall
    pose["neck"] = -8.0 * jerk + 6.0 * fall
    pose["head"] = -16.0 * jerk + 10.0 * fall
    pose["jaw"] = 8.0 + 30.0 * jerk + 10.0 * fall
    pose["feeler"] = 20.0 * jerk - 30.0 * fall
    # The long arm is flung up with the jerk and then thrown out along the
    # floor in front, the claw last to land — set as world headings, since
    # it is falling, not being carried.
    # The wrist is steered (two-bone IK off the shoulder as it falls): flung
    # out ahead with the jerk, then laid on the floor in front, so the arm
    # lands rather than sweeping through the ground.
    sx, sy, _ = solve(pose)["near_upper"]
    lay = smooth(0.3, 0.8, t)
    rel = mix(WRIST_REST, (8.6, 1.4), jerk)
    wrist = mix((sx + rel[0], sy + rel[1]), (10.2, GROUND - 1.7), lay)
    h1, h2 = ik((sx, sy), wrist, BONES["near_upper"].length, BONES["near_fore"].length, -1)
    pose["abs:near_upper"], pose["abs:near_fore"] = h1, h2
    pose["abs:near_claw"] = lerp(lerp(BONES["near_claw"].heading, -30.0, jerk), 8.0, smooth(0.3, 0.6, t))
    pose["far_upper"] = -40.0 * jerk + 30.0 * fall
    pose["far_fore"] = -20.0 * jerk + 20.0 * fall
    pose["far_claw"] = 20.0 * fall
    feet = {"near": (LEGS["near"][1] + 0.8 * fall, GROUND), "far": (LEGS["far"][1] - 1.4 * fall, GROUND)}
    return plant_legs(pose, feet, toes={"near": 10.0 * fall, "far": -6.0 * fall})

tracks = RIG.tracks
ROUND = ("socket", "eye", "graft", "graft2", "organ", "organ2")

animations = {}
animations["shamble"] = {
    "description": "The limp: the near leg walks and the far leg is stiff. The body drops heavily onto the near foot and pitches forward over it, then hikes its hip and leans back to swing the stiff leg through straight, toe dragging, and vaults up over it when it lands — a lopsided two-beat, heavy then hitched. The head swings on a beat after the chest and the jaw flops open on the lurch; the long arm hangs and is swung by the body a beat behind it, forearm and claw later still; the short arm jerks up on the lurch; the feeler stub nods after the head.",
    "duration": 1.1,
    "tracks": tracks(shamble_pose, keyset(22), still=ROUND),
}
animations["death"] = {
    "description": "The two grafts stop walking it: it jerks upright with the head thrown back and the jaw wide as both organs flare, then they go out, the crack down the chest opens wider, the knees give, and the frame folds forward over them — head dropping, the long arm flung out and then laid along the floor in front, the short one falling open. Still from 0.85.",
    "duration": 0.46,
    "tracks": tracks(death_pose, DEATH_TS, [
        ("organ", "scale", lambda t: 1.0 + 0.7 * math.sin(math.pi * smooth(0.0, 0.34, t))),
        ("organ", "opacity", lambda t: 1.0 - smooth(0.2, 0.6, t)),
        ("organ2", "scale", lambda t: 1.0 + 0.8 * math.sin(math.pi * smooth(0.0, 0.3, t))),
        ("organ2", "opacity", lambda t: 1.0 - smooth(0.16, 0.5, t)),
        ("graft2", "opacity", lambda t: 1.0 - 0.5 * smooth(0.3, 0.8, t)),
        ("eye", "opacity", lambda t: 1.0 - smooth(0.1, 0.5, t)),
        ("crack", "scale", lambda t: 1.0 + 0.35 * smooth(0.12, 0.5, t)),
    ], still=ROUND),
}

# ============================================================== states
VARIANTS = {
    "elite": {
        "description": "The hive doubled down: a fresh fully lit graft in the hump of the back beside the dying one in the chest.",
        "scale": 1.25,
        "set": {
            "graft2.opacity": 1,
            "organ2.opacity": 1,
        },
    },
}

DESCRIPTION = (
    "A drone that ran out of scent and stopped being anybody — the hive grafted an organ onto its chest and it walks again. Seen side-on "
    "facing +x and mirrored by the game: a tall hunched frame of bleached bone, the chest bent forward over the waist, a drone's head capsule "
    "hung out in front of the shoulders with an empty eye socket, a slack jaw and one feeler snapped to a stub. One arm long, hanging in front "
    "of the belly past the knee with a hooked claw; the other short and withered, crooked forward at chest height. A dark hexagonal graft in the chest carries "
    "a faint organ, and a crack runs down the front. Tall and pale where the Tracker is low and amber: at a glance you are reading height "
    "and value, not detail. Built on a skeleton (scripts/zombie.py): a pelvis that rides the gait, a two-bone spine, a hanging head, two "
    "chained arms and two legs solved every frame to a foot on the floor. The `shamble` is a limp — one leg walks, the other is stiff, so "
    "the body drops onto the good leg, hikes its hip to swing the stiff one through with its toe dragging and vaults over it — and the "
    "long arm swings a beat behind all of it. Gameplay radius 11. `elite` is the hive doubling down: a second, fully lit graft in the hump "
    "of the back. The `death` clip is the grafts letting go of a body that was already nobody: both organs flare and go out, the crack down "
    "the chest opens, and the frame folds forward over its knees."
)

# The drawing was laid out about the pelvis; the long arm and the head reach
# further forward than the back does behind, so the whole body sits a unit
# back on the canvas to centre its reach (offsets are relative, so the clips
# are unchanged).
SHIFT_X = -1.0
for p in RIG.parts: p["at"][0] = r2(p["at"][0] + SHIFT_X)
SKELETON = RIG.skeleton()
for k, v in SKELETON["joints"].items(): v[0] = r2(v[0] + SHIFT_X)

doc = {
    "id": "ss.enemy.zombie",
    "name": "Husk",
    "description": DESCRIPTION,
    "tags": ["enemy", "shambler"],
    "size": SIZE,
    "meta": {"radius": 11},
    "parts": RIG.parts,
    "variants": VARIANTS,
    "animations": animations,
    "skeleton": SKELETON,
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-zombie.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
