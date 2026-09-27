"""The Trapjaw — a trap-jaw ant, jaws cocked open, walking into range.

    python3 scripts/trapjaw.py        # rewrites apps/ss/assets/ss-enemy-trapjaw.json

The burrow's charger, in the Lance's slot. feelers runs it as a dash
(`EnemyType` `trapjaw`: `windup` 0.7s, `dashSpeed` 760 for 0.34s,
`windupCommits`): it walks into range, braces and commits to a line, and goes.
It has no `windupAnim` on purpose — the game says the brace with the yellow
wash (`flashFill`) — so the one clip it has besides the death, `latch`, is
looped through all of it: the walk, the brace and the dash. That makes the
latch itself the standing tell: the jaws are held cocked open against their
catch the whole time the body is alive, the trigger hairs out between them,
and the V strains and shivers. That concept is the original's and stays; what
it lacked was size — it measured 4px at game scale, a V that shivered two
degrees on a body that never moved.

Rebuilt on the shared rig (`rig.py`):

  - the mesosoma is the root bone: it bobs and pitches with each tripod's push;
    the head is a bone off the neck that counter-nods, the petiole and gaster a
    chain off the waist that swings after the body
  - each mandible is a bone hinged in its socket at the front of the head; the
    latch is a *load*: once a stride both jaws are hauled wider against the
    catch, shiver there at the top of the strain and ease back to cocked —
    never a swing, never shut
  - the trigger hairs are two little bones between the jaws that quiver ahead
    of everything; the antennae are elbowed — a long scape back over the head
    and a two-link funiculus that taps forward
  - six legs, each a femur and a tibia solved to a planted foot (two-bone IK)
    with a tarsus off it, in two alternating tripods; tapered, knees shown and
    darker than the body so the body reads first

Seen side-on facing +x, flipped by the game (it neither turns nor rotates).
Amber-brown chitin with the jaws pale bone — the jaws are the animal and the
largest light mass on it — and ember only on their tips and the trigger hairs,
the part that is cocked.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 56×40, origin at the centre, +x forward, +y down. Feet on GROUND.
W, H = 56, 40
GROUND = 10.5
FAR_LIFT = 1.2

RIG = Rig()
B = RIG.bones
bone = RIG.bone

BODY = (-1.0, 0.0)
bone("body", None, BODY, 0.0)
NECK = (3.4, -1.2)
bone("head", "body", NECK, -14.0, 9.0)
WAIST = (-5.6, 0.2)
bone("petiole", "body", WAIST, 172.0, 2.6)
bone("gaster", "petiole", B["petiole"].end(), 176.0, 1.0)

# Head frame helper: a point given along/across the head bone at rest.
def head_pt(along, across):
    return RIG.on_bone("head", along, across)[0] if RIG.rest else (
        NECK[0] + along * math.cos(R(-14.0)) - across * math.sin(R(-14.0)),
        NECK[1] + along * math.sin(R(-14.0)) + across * math.cos(R(-14.0)))

# Mandibles: hinged in sockets at the front corners of the head, cocked open
# into a V up and down (the gape opens up and down, not across: seen side-on a
# horizontal gape is one blade and no V). Headings are world degrees at rest.
JAW_L = 10.6
HINGE = {"u": head_pt(9.6, -1.6), "d": head_pt(9.8, 1.4)}
JAW_REST = {"u": -58.0, "d": 48.0}
for s in ("u", "d"):
    bone(f"jaw_{s}", "head", HINGE[s], JAW_REST[s], JAW_L)
# The trigger hairs between them, pointing out ahead.
TRIG = {"u": (head_pt(10.2, -0.5), -16.0), "d": (head_pt(10.2, 0.4), 10.0)}
for s, (at, h) in TRIG.items():
    bone(f"trig_{s}", "head", at, h, 3.6)
# Antennae: an elbowed scape back over the head from the frons, then the
# funiculus out forward in two links. The far one sits a little behind.
ANT = {"n": (head_pt(7.6, -2.2), -166.0, [(4.4, -26.0), (4.2, -4.0)]),
       "f": (head_pt(7.2, -2.6), -158.0, [(4.2, -40.0), (4.0, -18.0)])}
for s, (at, h, links) in ANT.items():
    bone(f"scape_{s}", "head", at, h, 6.4)
    RIG.chain(f"fun_{s}", f"scape_{s}", B[f"scape_{s}"].end(), links)

# Legs off the underside of the mesosoma.
LEGS = {  # name: (hip, rest foot x, femur, tibia, tarsus)
    "f": ((1.6, 1.6), 9.0, 4.6, 5.0, 2.4),
    "m": ((-1.4, 1.9), 1.4, 4.2, 4.6, 2.4),
    "b": ((-4.2, 1.7), -10.4, 5.0, 5.6, 2.6),
}
FAR_DX = -0.8
def hip_rest(s, n):
    (hx, hy) = LEGS[n][0]
    return (hx + (FAR_DX if s == "f" else 0.0), hy - (0.9 if s == "f" else 0.0))
def foot_rest(s, n):
    return (LEGS[n][1] + (FAR_DX if s == "f" else 0.0), GROUND - (FAR_LIFT if s == "f" else 0.0))
def bend(s, n):
    return 1 if foot_rest(s, n)[0] >= hip_rest(s, n)[0] else -1
LEG_IDS = [(s, n) for s in ("f", "n") for n in ("b", "m", "f")]
def tarsus_h(s, n, tib_h):
    return 90.0 + (26.0 if n == "f" else -26.0 if n == "b" else 8.0)
for s, n in LEG_IDS:
    hip, fx, lf, lt, ls = hip_rest(s, n), *LEGS[n][1:]
    foot = foot_rest(s, n)
    # the tibia ends above the foot by the tarsus: solve to the ankle
    th = tarsus_h(s, n, 0.0)
    ankle = (foot[0] - ls * math.cos(R(th)), foot[1] - ls * math.sin(R(th)))
    hf, ht = ik(hip, ankle, lf, lt, bend(s, n))
    bone(f"{s}{n}_femur", "body", hip, hf, lf)
    bone(f"{s}{n}_tibia", f"{s}{n}_femur", B[f"{s}{n}_femur"].end(), ht, lt)
    bone(f"{s}{n}_tarsus", f"{s}{n}_tibia", B[f"{s}{n}_tibia"].end(), th, ls)

RIG.seal()
solve, put, on_bone = RIG.solve, RIG.put, RIG.on_bone

# ============================================================== parts
def rel(pts, o): return [(x - o[0], y - o[1]) for x, y in pts]
def head_poly(pts):
    """Points given along/across the head bone, returned in the world."""
    return [head_pt(a, c) for a, c in pts]

# The masses are rimmed in the darkest chitin rather than ink: the burrow's
# floor is nearly ink already, so an ink rim only thins the body into it; a
# dark amber one still draws head over thorax over waist, and keeps the
# silhouette its full size. The jaws, the part that has to cut out of
# everything, keep the ink.
RIM = {"color": "$chitin.dark2", "width": "thin"}
RIM_HAIR = {"color": "$chitin.dark2", "width": "hair"}

# ---- far side: legs, antenna
def leg_parts(s, n, femur, tibia, stroke):
    for seg, w0, w1, over in (("tarsus", 0.9, 0.55, 0.3), ("tibia", 1.35, 0.85, 0.45), ("femur", 1.8, 1.25, 0.5)):
        nm = f"{s}{n}_{seg}"
        at, a = on_bone(nm)
        put(f"leg_{nm}", nm, at, a, bar(B[nm].length, w0, w1, over), tibia if seg != "femur" else femur, stroke)
for n in ("b", "m", "f"):
    leg_parts("f", n, "$chitin.dark2", "$rust.light", None)

def antenna(s, fill):
    at, a = on_bone(f"scape_{s}")
    put(f"scape_{s}", f"scape_{s}", at, a, bar(B[f"scape_{s}"].length, 1.0, 0.8, 0.4), fill)
    for i in range(2):
        nm = f"fun_{s}_{i}"
        at, a = on_bone(nm)
        put(nm, nm, at, a, bar(B[nm].length, 0.85 - 0.15 * i, 0.7 - 0.2 * i, 0.35), fill)
antenna("f", "$chitin.dark2")

# ---- the far jaw first (the lower one sits behind the head's underside), so
# both hinge into sockets the head covers
TOOTH = 0.9
def mandible(s):
    sg = 1 if s == "u" else -1   # which local side is the inside of the V
    L = JAW_L
    # a long straight blade, a little swollen at the base, the tip bent in
    blade = [(-1.2, -sg * 1.0), (1.0, -sg * 1.25), (L - 2.6, -sg * 0.9), (L - 0.6, -sg * 0.3), (L + 0.6, sg * 1.2),
             (L + 0.2, sg * 2.2), (L - 1.2, sg * 1.2), (L - 2.4, sg * 0.9), (1.0, sg * 1.15), (-1.2, sg * 1.0)]
    tip = [(L - 2.6, -sg * 0.9), (L - 0.6, -sg * 0.3), (L + 0.6, sg * 1.2), (L + 0.2, sg * 2.2), (L - 1.2, sg * 1.2),
           (L - 2.2, sg * 0.95), (L - 2.8, -sg * 0.1)]
    return [(x, y) for x, y in blade], tip
for s, fill in (("d", "$bone"), ("u", "$bone.light")):
    at, a = on_bone(f"jaw_{s}")
    bl, tp = mandible(s)
    put(f"jaw_{s}", f"jaw_{s}", at, a, poly(bl), fill, INK_HAIR)
    put(f"jaw_{s}_tip", f"jaw_{s}", at, a, poly(tp), "$ember")

# ---- the trigger hairs, then the body back to front
for s in ("u", "d"):
    at, a = on_bone(f"trig_{s}")
    put(f"trig_{s}", f"trig_{s}", at, a, bar(B[f"trig_{s}"].length, 0.75, 0.45, 0.3), "$ember.light")

# Gaster: an oval, a band where the plates meet, a gloss.
at, a = on_bone("gaster")
GC = (at[0] - 5.6, at[1] + 0.8)
put("gaster", "gaster", GC, -8.0, ell(6.6, 5.0), "$chitin.dark", RIM)
put("gaster_band", "gaster", (GC[0] + 2.4, GC[1] + 0.4), -8.0, ell(0.8, 4.4), "$chitin.dark2@soft")
put("gaster_gloss", "gaster", (GC[0] - 0.4, GC[1] - 2.6), -12.0, ell(4.2, 1.4), "$chitin")
# Petiole: the waist, with the tall pointed node an Odontomachus carries.
PC = on_bone("petiole", 1.3)[0]
put("petiole", "petiole", PC, 0.0, poly(rel([(PC[0] + 2.0, PC[1] + 0.2), (PC[0] + 1.0, PC[1] - 1.4), (PC[0] + 0.1, PC[1] - 4.6),
                                          (PC[0] - 0.7, PC[1] - 1.6), (PC[0] - 2.0, PC[1] - 0.2), (PC[0] - 1.6, PC[1] + 1.3),
                                          (PC[0] + 1.6, PC[1] + 1.3)], PC)), "$chitin.dark", RIM_HAIR)
# Mesosoma: pronotum hump in front, the back sloping down to the waist.
MESO = [(4.2, -1.8), (3.0, -3.4), (0.4, -3.7), (-2.4, -2.6), (-4.4, -2.2), (-6.0, -0.8), (-6.0, 1.0),
        (-3.6, 2.3), (0.8, 2.4), (3.6, 1.6), (4.6, 0.0)]
put("meso", "body", BODY, 0.0, poly(rel(MESO, BODY)), "$chitin.dark", RIM)
put("meso_gloss", "body", (0.6, -2.7), -6.0, ell(2.6, 0.7), "$chitin")
RIG.use("organ", "body", (-2.6, -3.3), "ss.lib.organ", scale=0.42)

# Head: long, the rear pinched into the neck, the front deep where the jaws
# seat; the temple lines back from the eye.
HEAD = [(-0.8, -1.2), (0.6, -2.6), (3.4, -3.0), (7.0, -2.9), (9.6, -2.4), (10.6, -1.0),
        (10.6, 1.2), (9.2, 2.6), (5.6, 2.8), (2.4, 2.4), (0.2, 1.6), (-0.8, 0.6)]
put("head", "head", NECK, 0.0, poly(rel(head_poly(HEAD), NECK)), "$chitin.dark", RIM)
g, _ = on_bone("head", 5.2, -1.8)
put("head_gloss", "head", g, -14.0, ell(3.4, 0.7), "$chitin")
e, _ = on_bone("head", 7.4, -0.6)
put("eye", "head", e, -14.0, ell(1.3, 1.1), "$ink")
put("socket", "head", on_bone("head", 9.9, 0.0)[0], -14.0, ell(1.2, 2.2), "$chitin.dark2")

# ---- near side: antenna, legs
antenna("n", "$chitin.dark")
for n in ("b", "m", "f"):
    leg_parts("n", n, "$chitin.dark2", "$chitin.dark2", INK_HAIR)

RIG.check()
STILL = {"eye", "organ", "socket"}

# ============================================================== motion
tracks = RIG.tracks

def plant(pose, feet):
    world = solve(pose)
    for s, n in LEG_IDS:
        hip, fx, lf, lt, ls = hip_rest(s, n), *LEGS[n][1:]
        hx, hy, _ = world[f"{s}{n}_femur"]
        th = tarsus_h(s, n, 0.0)
        fxy = feet[(s, n)]
        ankle = (fxy[0] - ls * math.cos(R(th)), fxy[1] - ls * math.sin(R(th)))
        hf, ht = ik((hx, hy), ankle, lf, lt, bend(s, n))
        pose[f"abs:{s}{n}_femur"] = hf
        pose[f"abs:{s}{n}_tibia"] = ht
        pose[f"abs:{s}{n}_tarsus"] = th
    return pose

TRIPOD = {("n", "f"): 0.0, ("f", "m"): 0.0, ("n", "b"): 0.0, ("f", "f"): 0.5, ("n", "m"): 0.5, ("f", "b"): 0.5}
STRIDE = 3.2
def step(t, ph):
    u = (t + ph) % 1.0
    if u < 0.55:
        return lerp(STRIDE, -STRIDE, u / 0.55), 0.0
    v = (u - 0.55) / 0.45
    return lerp(-STRIDE, STRIDE, smooth(0.0, 1.0, v)), 3.0 * math.sin(math.pi * v)

# ---- latch: the idle, the walk, the brace and the dash all loop it. One
# stride of two tripods, and once a stride the load: both jaws hauled wider
# against the catch, shivering at the top of it, eased back to cocked.
def load(t):
    """0 at cocked, 1 at the top of the strain."""
    return smooth(0.05, 0.4, t) * (1 - smooth(0.62, 0.95, t))
def shiver(t):
    return math.sin(2 * math.pi * 9 * t) * smooth(0.25, 0.4, t) * (1 - smooth(0.6, 0.72, t))
def latch_pose(t):
    bob = 0.7 * (0.5 - 0.5 * math.cos(4 * math.pi * t))
    k = load(t)
    # the body sits back into the load, the head lifts with it
    pose = {"body": (0.9 * cyc(2 * t, 0.1) - 1.4 * k, -bob + 0.6 * k, 1.8 * cyc(2 * t, 0.2) - 3.0 * k)}
    pose["head"] = -1.8 * cyc(2 * t, 0.05) - 7.0 * k
    for s, sg in (("u", -1), ("d", 1)):
        pose[f"jaw_{s}"] = sg * (18.0 * k + 2.6 * shiver(t))
        pose[f"trig_{s}"] = 14.0 * math.sin(2 * math.pi * 6 * t + (0.0 if s == "u" else 1.9)) + sg * 6.0 * k
    # the gaster swings after the step
    pose["petiole"] = 4.0 * cyc(2 * t, -0.05)
    pose["gaster"] = 7.0 * cyc(2 * t, -0.15) + 3.0 * k
    # the antennae tap forward, the funiculus whipping after the scape
    for s, ph in (("n", 0.0), ("f", 0.35)):
        pose[f"scape_{s}"] = 10.0 * cyc(t, ph)
        pose[f"fun_{s}_0"] = 14.0 * cyc(2 * t, ph - 0.1)
        pose[f"fun_{s}_1"] = 18.0 * cyc(2 * t, ph - 0.22)
    feet = {}
    for s, n in LEG_IDS:
        dx, lift = step(t, TRIPOD[(s, n)])
        fx, fy = foot_rest(s, n)
        feet[(s, n)] = (fx + dx, fy - lift)
    return plant(pose, feet)

# ---- death: 0.42s. The latch fires once on nothing — a last haul wider,
# then both jaws slam shut, and the snap throws the body back off its feet the
# way it throws a live one; then it falls, the jaws drop open slack and hang,
# the gaster swings down, the head drops and the legs draw in. Still by 0.85.
def death_pose(t):
    cock = smooth(0.0, 0.1, t) * (1 - smooth(0.1, 0.15, t))
    snap = smooth(0.1, 0.16, t)
    slack = smooth(0.3, 0.75, t)
    thrown = math.sin(math.pi * smooth(0.12, 0.5, t))
    fall = smooth(0.35, 0.8, t)
    pose = {"body": (-2.6 * thrown, -2.4 * thrown + 2.4 * fall, -12.0 * thrown + 7.0 * fall)}
    pose["head"] = -4.0 * cock + 8.0 * thrown + 16.0 * fall
    for s, sg in (("u", -1), ("d", 1)):
        shut = -sg * (abs(JAW_REST[s]) + 2.0)                # all the way across
        hang = -sg * (abs(JAW_REST[s]) - (18.0 if s == "u" else 34.0))
        pose[f"jaw_{s}"] = sg * 10.0 * cock + lerp(lerp(0.0, shut, snap), hang, slack)
        pose[f"trig_{s}"] = sg * 30.0 * snap + 20.0 * fall
    pose["petiole"] = 10.0 * thrown - 10.0 * fall
    pose["gaster"] = 8.0 * thrown - 16.0 * fall
    for s in ("n", "f"):
        pose[f"scape_{s}"] = -20.0 * thrown + 34.0 * fall
        pose[f"fun_{s}_0"] = 20.0 * fall
        pose[f"fun_{s}_1"] = 26.0 * fall
    world = solve(pose)
    feet = {}
    for s, n in LEG_IDS:
        fx, fy = foot_rest(s, n)
        hx, hy, _ = world[f"{s}{n}_femur"]
        kick = (2.0 if TRIPOD[(s, n)] == 0 else -2.0) * thrown
        feet[(s, n)] = (lerp(fx + kick, hx + (fx - hx) * 0.5, fall), lerp(fy - 1.4 * thrown, hy + 4.2, fall))
    return plant(pose, feet)

animations = {}
animations["latch"] = {
    "description": "Not a swing — a hold, and the standing tell: looped through the walk, the brace and the dash. The jaws are held cocked open against their catch the whole time; once a stride the body sits back and both jaws are hauled wider against it, shiver at the top of the strain and ease back to cocked, never shut. Under it the body walks into range on two alternating tripods, each foot planted while the body rides over it; the gaster swings after the step, the antennae tap forward and the ember trigger hairs quiver out ahead of everything.",
    "duration": 0.55,
    "tracks": tracks(latch_pose, keyset(22), still=STILL),
}
DEATH_TS = [0, 0.05, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]
animations["death"] = {
    "description": "The jaws are the animal, so they go last and first: a last haul wider, then they snap shut on nothing — the latch firing with no target in it — and the snap throws the body back off its feet the way it throws a live one. Then it falls: the jaws drop open slack and hang for good, the ember tips and the trigger hairs dim, the gaster swings down, the head drops and the legs draw in; the organ goes out. Still from 0.85.",
    "duration": 0.42,
    "tracks": tracks(death_pose, DEATH_TS, [
        ("jaw_u_tip", "opacity", lambda t: 1.0 - 0.6 * smooth(0.3, 0.8, t)),
        ("jaw_d_tip", "opacity", lambda t: 1.0 - 0.6 * smooth(0.3, 0.8, t)),
        ("trig_u", "opacity", lambda t: 1.0 - 0.7 * smooth(0.2, 0.7, t)),
        ("trig_d", "opacity", lambda t: 1.0 - 0.7 * smooth(0.2, 0.7, t)),
        ("organ", "opacity", lambda t: 1.0 - 0.85 * smooth(0.25, 0.8, t)),
    ], still=STILL),
}

# ============================================================== document
DESCRIPTION = (
    "The burrow's charger, and the jaws are what throws it: a trap-jaw ant. Drawn from the side facing +x and flipped by the game; the gape opens up "
    "and down rather than across, the way the Soldier's mandibles already do, because a horizontal gape seen side-on is one blade and no V at all. "
    "Almost all of it is jaw: two long straight pale-bone mandibles with hooked ember tips, cocked open into a wide V from sockets at the front of a "
    "long head, the ember trigger hairs out between them — the silhouette is an open mouth travelling. Behind the head a humped mesosoma, the "
    "Odontomachus petiole with its tall pointed node, and an oval gaster, all amber-brown chitin; elbowed antennae; six tapered legs darker than the body. "
    "Built on a skeleton (scripts/trapjaw.py): the mesosoma is the root, the head a bone off the neck, each mandible a bone hinged in its socket, the "
    "gaster a chain off the waist, the legs solved every frame to planted feet. The game has no windup clip for it (the brace is the yellow wash), so "
    "`latch` is looped through the walk, the brace and the dash, and it is the standing tell: the jaws are loaded against their catch, and once a "
    "stride hauled wider and shivering there, never swinging, while the body walks into range. The only ember is the two tips and the trigger hairs "
    "between them: the bright part is the part that is cocked. No `elite` variant on purpose — the marking only lands on wave-table bodies, and this "
    "one arrives in squads. Gameplay radius 10. The `death` clip fires the latch one more time into nothing — the snap throws it back — and then lets "
    "the jaws hang open for good."
)

doc = {
    "id": "ss.enemy.trapjaw",
    "name": "Trapjaw",
    "description": DESCRIPTION,
    "tags": ["enemy", "trapjaw"],
    "size": [W, H],
    "meta": {"radius": 10},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-trapjaw.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
