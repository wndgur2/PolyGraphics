"""The Warden — the burrow's first boss, a soldier bred as a door.

    python3 scripts/warden.py        # rewrites apps/ss/assets/ss-enemy-warden.json

It holds 300px of chamber and throws a fan of chips of its own door at you
(feelers: `warden` — `standoff: 300`, `shotTex: 'e_plug'`, `volleyAnim:
'volley'`, played once as the bolts leave whenever the phase has put the count
above one; `enraged` at a half, `final` at a quarter, each with its own sheet
of every clip). Mirrored by the game, never turned: drawn side-on facing +x.

It was hand-placed and held still on purpose — a door holds still — and at
game scale it read as a slab: the loop moved 5px and 4.8% of the outline,
three four-link legs pedalling under a wedge nothing else touched. The concept
stays exactly: one straight-edged keystone, tall and flat-faced at the front
and narrowing to nothing behind (the cork silhouette nothing else in the game
has), a bone-rimmed face packed in strata with a toothed front edge, a crest
of nine horns along the back, the teal vent low under the face, three organs
down the flank. What changes is that it is now an animal holding a door up:

  - the keystone is three courses of plate, front over back, on a chain of
    bones — the front course is the body, the middle and tail courses hang
    behind it and flex a beat late, so the wedge breathes and its tail sways
  - the face is the door, and it is two halves hinged at the head's top and
    bottom corners that meet along the middle stratum. In `hold` they part a
    crack on every breath and the vent's light shows in the seam; in `volley`
    the door comes open for real
  - nine horns, each hinged at its root on the course it grows from, bristle
    in a wave running from the face back to the tail
  - six short heavy legs (three near, three far and darker), each a femur and
    a tibia solved every frame to a clawed foot on the ground, so a planted
    foot stays put while the wedge rolls over it; a slow wave gait, back to
    front, the weight surging and pitching onto each foot as it lands

Colour: the packed-earth chitin it was (`$chitin.dark` plates with a lit top
course and a shaded keel), the rust face in a bone rim, horns in husk with a
bone edge, legs the dark carapace purple they were. The vent and the organs
are the only bright things on it. `enraged` turns the slab dark and splits the
face pink along its strata with the horns stood up white; `final` blacks the
door out, knocks its rim and some teeth off, props it open and lets a white
vent through — three states you tell apart from across the chamber.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, mix, smooth, cyc, cyc_c, wrap, keyset, ik2 as ik,
                 poly, ell, circ, rect, bar, INK_THIN, INK_HAIR, INK_BOLD, write_doc)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-enemy-warden.json")

# ============================================================== rig
# Canvas 124×108, origin at the centre, +x forward (the face), +y down.
SIZE = [124, 108]
GROUND = 40.0
FAR_LIFT = 1.8
BODY_PIVOT = (2.0, 6.0)

# ---- the keystone's outline: straight edges, tall at the face, narrowing to
# a blunt point behind; the tail end sags a little so the head is held up.
TOP = [(40.0, -27.0), (14.0, -30.0), (-14.0, -22.0), (-44.0, -7.0)]
BOT = [(40.0, 25.0), (14.0, 27.0), (-14.0, 20.0), (-44.0, 6.0)]
TIP = (-47.5, -0.2)
def sag(x): return max(0.0, -x - 4.0) * 0.16
def _pl(pts, x):
    pts = sorted(pts)
    if x <= pts[0][0]: return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1: return lerp(y0, y1, (x - x0) / (x1 - x0))
    return pts[-1][1]
def y_top(x): return _pl(TOP, x) + sag(x)
def y_bot(x): return _pl(BOT, x) + sag(x)
def mid_y(x): return 0.5 * (y_top(x) + y_bot(x))

RIG = Rig()
BONES = RIG.bones
bone = RIG.bone

bone("body", None, BODY_PIVOT, 0.0)
# The courses behind the front one: the middle hangs off the front's back
# edge, the tail off the middle's. They point backward.
MID_ROOT = (12.0, mid_y(12.0))
TAIL_ROOT = (-15.0, mid_y(-15.0))
bone("mid", "body", MID_ROOT, 180.0 + D(math.atan2(mid_y(-15.0) - mid_y(12.0), 27.0)), 27.0)
bone("tail", "mid", TAIL_ROOT, 180.0 + D(math.atan2(TIP[1] + sag(TIP[0]) - mid_y(-15.0), 32.5)), 32.5)
# The door: two halves hinged at the head's top and bottom back corners.
FACE_X0, FACE_X1 = 33.0, 46.0
FACE_TOP, FACE_BOT, SEAM = -30.0, 27.5, -1.0
HINGE_UP = (34.0, FACE_TOP + 1.5)
HINGE_DN = (34.0, FACE_BOT - 1.5)
bone("jaw_up", "body", HINGE_UP, 90.0, SEAM - HINGE_UP[1])
bone("jaw_dn", "body", HINGE_DN, -90.0, HINGE_DN[1] - SEAM)

# The crest: nine horns, three to a course, each hinged at its root.
HORNS = [  # (x, course bone, rest heading, length, root width)
    (32.0, "body", -96.0, 16.0, 8.6),
    (24.0, "body", -101.0, 17.5, 9.0),
    (16.0, "body", -106.0, 18.0, 9.2),
    (6.0, "mid", -113.0, 17.0, 8.8),
    (-3.0, "mid", -118.0, 16.0, 8.4),
    (-12.0, "mid", -123.0, 14.5, 7.8),
    (-22.0, "tail", -130.0, 13.0, 7.2),
    (-30.5, "tail", -135.0, 11.5, 6.6),
    (-38.5, "tail", -140.0, 10.0, 6.0),
]
for i, (x, parent, h, L, w) in enumerate(HORNS):
    bone(f"horn_{i}", parent, (x, y_top(x) + 2.4), h, L)

# The legs: short heavy columns under the keel. Front and middle knees fold
# forward, the hind knees back — a table standing in its frame.
LEGS = {  # name: (hip, rest foot x, femur, tibia)
    "fb": ((-25.0, y_bot(-25.0) - 5.0), -32.0, 11.0, 13.0),
    "fm": ((-4.0, y_bot(-4.0) - 5.0), -5.0, 10.0, 12.0),
    "ff": ((17.0, y_bot(17.0) - 5.0), 23.0, 9.0, 11.0),
    "nb": ((-21.0, y_bot(-21.0) - 3.0), -28.0, 11.5, 13.5),
    "nm": ((1.0, y_bot(1.0) - 3.0), 2.0, 10.5, 12.5),
    "nf": ((22.0, y_bot(22.0) - 3.0), 29.0, 9.5, 11.5),
}
def ground_of(leg): return GROUND - (FAR_LIFT if leg.startswith("f") else 0.0)
def knee_bend(leg): return -1 if leg.endswith("b") else 1
def course_of(leg):
    x = LEGS[leg][0][0]
    return "body" if x > 12 else ("mid" if x > -15 else "tail")
for leg, (hip, fx, lf, lt) in LEGS.items():
    hf, ht = ik(hip, (fx, ground_of(leg)), lf, lt, knee_bend(leg))
    bone(f"{leg}_femur", course_of(leg), hip, hf, lf)
    bone(f"{leg}_tibia", f"{leg}_femur", RIG.end_of(f"{leg}_femur"), ht, lt)
    bone(f"{leg}_foot", f"{leg}_tibia", RIG.end_of(f"{leg}_tibia"), 0.0, 3.0)

RIG.seal()
solve = RIG.solve
put, on_bone = RIG.put, RIG.on_bone

# ============================================================== parts
def taper(L, w0, wm, w1, um=0.35, over=0.8, n=8):
    """A limb segment along +x that swells to `wm` at `um` of its length and narrows to `w1`, ends rounded."""
    def w(u):
        return lerp(w0, wm, math.sin(0.5 * math.pi * u / um)) if u <= um else lerp(wm, w1, smooth(um, 1.0, u))
    us = [i / n for i in range(n + 1)]
    upper = [(-over, -w0 * 0.3)] + [(u * L, -w(u) / 2) for u in us] + [(L + over, -w1 * 0.3)]
    lower = [(L + over, w1 * 0.3)] + [(u * L, w(u) / 2) for u in reversed(us)] + [(-over, w0 * 0.3)]
    return poly(upper + lower)
def edge(L, w0, wm, w1, um=0.35, t=0.6, a=0.12, b=0.82, side=-1):
    """The lit hairline along one edge of a taper, from `a` to `b` of its length."""
    def w(u):
        return lerp(w0, wm, math.sin(0.5 * math.pi * u / um)) if u <= um else lerp(wm, w1, smooth(um, 1.0, u))
    us = [lerp(a, b, i / 6) for i in range(7)]
    s = side
    return poly([(u * L, s * (w(u) / 2 - 0.15)) for u in us] +
                [(u * L, s * (w(u) / 2 - 0.15 - t * math.sin(math.pi * (u - a) / (b - a)))) for u in reversed(us)])
def local(bone_name, pts):
    """World points into a bone's rest frame (for a part placed at the bone's start)."""
    x, y, a = RIG.rest[bone_name]
    c, s = math.cos(R(a)), math.sin(R(a))
    return [((px - x) * c + (py - y) * s, -(px - x) * s + (py - y) * c) for px, py in pts]
def world_part(id, bone_name, pts, fill, stroke=None, opacity=None):
    """A part drawn in world coordinates at rest, riding `bone_name` (placed at the origin, no turn)."""
    return put(id, bone_name, (0.0, 0.0), 0.0, poly(pts), fill, stroke, opacity)

# ---- legs
def leg_parts(leg, femur, tibia, claw, knee, lit, stroke, k=1.0):
    b = BONES
    Lf, Lt = b[f"{leg}_femur"].length, b[f"{leg}_tibia"].length
    F = (6.0 * k, 6.8 * k, 4.6 * k)
    T = (4.6 * k, 4.9 * k, 2.6 * k)
    at, a = on_bone(f"{leg}_foot", -0.6)
    put(f"{leg}_claw", f"{leg}_foot", at, a,
        poly([(-2.2 * k, -1.3 * k), (1.4, -1.6 * k), (3.6, -1.0 * k), (5.6, 0.4), (6.0, 1.7), (4.6, 1.0), (3.4, 0.9),
              (4.0, 1.9), (1.8, 1.4), (0.0, 1.6 * k), (-1.8, 1.5 * k), (-3.0, 2.0), (-2.6, 0.5)]), claw, stroke)
    at, a = on_bone(f"{leg}_tibia")
    put(f"{leg}_tibia", f"{leg}_tibia", at, a, taper(Lt, *T, um=0.22), tibia, stroke)
    put(f"{leg}_tibia_lit", f"{leg}_tibia", at, a, edge(Lt, *T, um=0.22, t=0.55 * k, side=-knee_bend(leg)), lit)
    at, a = on_bone(f"{leg}_femur")
    put(f"{leg}_femur", f"{leg}_femur", at, a, taper(Lf, *F), femur, stroke)
    put(f"{leg}_femur_lit", f"{leg}_femur", at, a, edge(Lf, *F, t=0.7 * k, side=-knee_bend(leg)), lit)
    at, a = on_bone(f"{leg}_tibia")
    put(f"{leg}_knee", f"{leg}_tibia", at, 0.0, circ(2.5 * k), knee, stroke)
    put(f"{leg}_knee_lit", f"{leg}_tibia", (at[0] - 0.5 * k, at[1] - 0.8 * k), 0.0, circ(0.8 * k), lit)
    at, a = on_bone(f"{leg}_femur")
    put(f"{leg}_coxa", f"{leg}_femur", at, 0.0, ell(3.5 * k, 2.7 * k), tibia, stroke)

for leg in ("fb", "fm", "ff"):
    leg_parts(leg, "$carapace.dark", "$carapace.dark2", "$husk.dark2", "$carapace.dark2", "$carapace@0.8", INK_HAIR, k=0.9)

# ---- the crest, behind the plates so every root is buried in its course
def horn_shape(L, w, bend):
    """A horn along +x from its root: tapering, swept back (−across) toward the tip."""
    n = 7
    fr, bk = [], []
    for i in range(n + 1):
        u = i / n
        c = -bend * u * u
        hw = 0.5 * w * (1 - u) ** 0.85
        fr.append((u * L, c + hw)); bk.append((u * L, c - hw))
    return fr + [(L + 0.6, -bend - 0.1)] + bk[::-1] + [(-1.2, 0.0)]
def horn_edge(L, w, bend):
    n = 6
    out, inn = [], []
    for i in range(n + 1):
        u = 0.08 + 0.82 * i / n
        c = -bend * u * u
        hw = 0.5 * w * (1 - u) ** 0.85
        out.append((u * L, c + hw - 0.2)); inn.append((u * L, c + hw * 0.25))
    return out + inn[::-1]
HORN_FILL = ["$husk.dark", "$husk.dark2"]
for i, (x, parent, h, L, w) in enumerate(HORNS):
    at, a = on_bone(f"horn_{i}")
    bend = 1.4 + 0.12 * L
    put(f"spine_{i}", f"horn_{i}", at, a, poly(horn_shape(L, w, bend)), HORN_FILL[i % 2], INK_HAIR)
    put(f"spine_edge_{i}", f"horn_{i}", at, a, poly(horn_edge(L, w, bend)), "$bone.light")

# ---- the keystone, three courses, tail first so each laps over the one behind
def course(x0, x1, bow, tip=None, n=10):
    """A course of plate from x0 (front, hidden under the next) back to x1, its back edge bowed backward."""
    top = [(lerp(x0, x1, i / n), y_top(lerp(x0, x1, i / n))) for i in range(n + 1)]
    yt, yb = y_top(x1), y_bot(x1)
    if tip is None:
        back = [(x1 - bow * math.sin(math.pi * j / 8), lerp(yt, yb, j / 8)) for j in range(1, 8)]
    else:
        # the blunt point: a half-round from the top edge to the keel
        back = [(x1 - (x1 - tip[0]) * math.sin(math.pi * j / 8), mid_y(x1) - 0.5 * (yb - yt) * math.cos(math.pi * j / 8)) for j in range(1, 8)]
    bot = [(lerp(x1, x0, i / n), y_bot(lerp(x1, x0, i / n))) for i in range(n + 1)]
    return top + back + bot
def band_top(x0, x1, d0, d1, n=10):
    return ([(lerp(x0, x1, i / n), y_top(lerp(x0, x1, i / n)) + d0) for i in range(n + 1)] +
            [(lerp(x1, x0, i / n), y_top(lerp(x1, x0, i / n)) + d1) for i in range(n + 1)])
def band_bot(x0, x1, d0, d1, n=10):
    return ([(lerp(x0, x1, i / n), y_bot(lerp(x0, x1, i / n)) - d0) for i in range(n + 1)] +
            [(lerp(x1, x0, i / n), y_bot(lerp(x1, x0, i / n)) - d1) for i in range(n + 1)])

COURSES = [  # name, bone, front x, back x, bow
    ("course_tail", "tail", -11.0, -44.0, None),
    ("course_mid", "mid", 14.0, -15.0, 3.2),
    ("course_front", "body", 40.0, 12.0, 3.4),
]
RIVETS = []
for name, bn, x0, x1, bow in COURSES:
    pts = course(x0, x1, bow or 0.0, TIP if bow is None else None)
    world_part(name, bn, pts, "$chitin.dark", INK_THIN)
    xe = x1 + (1.5 if bow is None else 0.0)
    # lit top course: the upper third in light, fading to a shade along the keel
    world_part(f"{name}_lit", bn, band_top(x0 - 0.6, xe + 0.8, 0.9, lerp(7.0, 4.0, 0.0 if bn == "body" else 0.5 if bn == "mid" else 1.0)), "$chitin@0.6")
    world_part(f"{name}_shade", bn, band_bot(x0 - 0.6, xe + 0.8, 0.9, lerp(7.0, 3.6, 0.0 if bn == "body" else 0.5 if bn == "mid" else 1.0)), "$chitin.dark2")
    # a stratum across the middle of the plate: the ground it was packed from
    k = 0.0 if bn == "body" else 0.5 if bn == "mid" else 1.0
    world_part(f"{name}_stratum", bn,
               [(lerp(x0 - 0.6, xe + 1.6, i / 10), mid_y(lerp(x0, xe, i / 10)) + 2.0 - 0.7 * math.sin(math.pi * i / 10)) for i in range(11)] +
               [(lerp(xe + 1.6, x0 - 0.6, i / 10), mid_y(lerp(xe, x0, i / 10)) + 3.4 - 0.4 * math.sin(math.pi * i / 10)) for i in range(11)],
               "$chitin.dark2@0.8")
    if bow is not None:
        # rivet pits down the lapped back edge
        for j, v in enumerate((0.22, 0.5, 0.78)):
            y = lerp(y_top(x1), y_bot(x1), v)
            x = x1 - bow * math.sin(math.pi * v) + 2.4
            rid = f"rivet_{name.split('_')[1]}_{j}"
            put(rid, bn, (x, y), 0.0, circ(1.25), "$chitin.dark2")
            put(f"{rid}_lit", bn, (x - 0.35, y - 0.4), 0.0, circ(0.5), "$chitin.light@0.8")
            RIVETS.append(rid)
    if name == "course_mid":
        RIG.use("organ_b", "mid", (-1.0, mid_y(-1.0) - 10.0), "ss.lib.organ", scale=0.74)
    if name == "course_tail":
        RIG.use("organ_c", "tail", (-27.0, mid_y(-27.0) - 5.5), "ss.lib.organ", scale=0.62)
RIG.use("organ_a", "body", (22.0, -17.5), "ss.lib.organ", scale=0.88)

# ---- the vent, low under the face: the glow the plug is thrown from
VENT_AT = (23.5, 15.0)
put("vent_lip", "body", VENT_AT, 0.0, ell(8.0, 6.0), "$chitin.dark2", INK_HAIR)
put("vent", "body", VENT_AT, 0.0, ell(6.4, 4.7), "$dead", INK_BOLD)
put("vent_glow", "body", (VENT_AT[0] + 0.4, VENT_AT[1]), 0.0, circ(4.0),
    {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$spore.light"], [1, "$spore@0.15"]]})

# ---- the maw behind the door: dark, lit teal from inside, only seen when it opens
MAW_AT = (39.5, SEAM)
put("maw", "body", MAW_AT, 0.0, ell(6.6, 13.5), "$dead")
put("maw_glow", "body", (MAW_AT[0] + 1.0, MAW_AT[1]), 0.0, ell(4.6, 9.5),
    {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$spore.light"], [1, "$spore@0.1"]]})

# ---- the door: two halves, each a bone rim round a rust face in strata,
# teeth down the front edge
def half(sign):
    """World outline of one half of the door (sign −1 upper, +1 lower)."""
    if sign < 0:
        return [(FACE_X0, FACE_TOP + 0.8), (FACE_X0 + 2.0, FACE_TOP), (FACE_X1 - 1.6, FACE_TOP - 0.4), (FACE_X1, FACE_TOP + 1.4),
                (FACE_X1, SEAM - 0.2), (FACE_X0, SEAM - 0.2)]
    return [(FACE_X0, SEAM + 0.2), (FACE_X1, SEAM + 0.2), (FACE_X1, FACE_BOT - 1.4), (FACE_X1 - 1.6, FACE_BOT + 0.4),
            (FACE_X0 + 2.0, FACE_BOT), (FACE_X0, FACE_BOT - 0.8)]
def panel(sign):
    i0 = 2.3
    if sign < 0:
        return [(FACE_X0 + i0, FACE_TOP + 2.4), (FACE_X1 - 2.6, FACE_TOP + 2.0), (FACE_X1 - 2.6, SEAM - 1.6), (FACE_X0 + i0, SEAM - 1.6)]
    return [(FACE_X0 + i0, SEAM + 1.6), (FACE_X1 - 2.6, SEAM + 1.6), (FACE_X1 - 2.6, FACE_BOT - 2.0), (FACE_X0 + i0, FACE_BOT - 2.4)]
STRATA = {  # id: (jaw, y centre, height)
    "strata_a": ("jaw_up", -24.0, 2.6), "strata_b": ("jaw_up", -16.5, 3.0), "strata_c": ("jaw_up", -8.5, 2.6),
    "strata_d": ("jaw_dn", 6.0, 2.8), "strata_e": ("jaw_dn", 13.5, 3.2), "strata_f": ("jaw_dn", 20.5, 2.6),
}
GRIT = {"grit_a": ("jaw_up", 38.0, -20.2), "grit_b": ("jaw_up", 40.4, -12.4), "grit_c": ("jaw_up", 37.6, -4.6),
        "grit_d": ("jaw_dn", 40.2, 2.8), "grit_e": ("jaw_dn", 37.8, 9.8), "grit_f": ("jaw_dn", 40.6, 17.2)}
TEETH_Y = {"jaw_up": [-25.5, -18.5, -11.5, -4.6], "jaw_dn": [2.6, 9.5, 16.5, 23.0]}
JAW_PARTS = {"jaw_up": [], "jaw_dn": []}
def jput(jaw, id, pts, fill, stroke=None, opacity=None):
    world_part(id, jaw, pts, fill, stroke, opacity); JAW_PARTS[jaw].append(id)
def jput_at(jaw, id, at, shape, fill, stroke=None, rot=0.0, opacity=None):
    put(id, jaw, at, rot, shape, fill, stroke, opacity); JAW_PARTS[jaw].append(id)
def jput_c(jaw, id, pts, fill, stroke=None, opacity=None):
    """A small loose piece, placed at its own centre so it can spin about itself."""
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    jput_at(jaw, id, (cx, cy), poly([(x - cx, y - cy) for x, y in pts]), fill, stroke, opacity=opacity)
n_tooth = 0
for jaw, sign in (("jaw_up", -1), ("jaw_dn", 1)):
    # teeth first, so their roots sit under the rim
    for y in TEETH_Y[jaw]:
        lean = 0.8 * sign
        jput(jaw, f"tooth_{n_tooth}", [(FACE_X1 - 1.4, y - 2.5), (FACE_X1 + 3.8, y + lean), (FACE_X1 - 1.4, y + 2.5)], "$bone", INK_HAIR)
        n_tooth += 1
    jput(jaw, f"face_rim_{'up' if sign < 0 else 'dn'}", half(sign), "$husk", {"color": "$ink", "width": "bold"})
    jput(jaw, f"face_{'up' if sign < 0 else 'dn'}", panel(sign), "$rust")
    for sid, (j, yc, hgt) in STRATA.items():
        if j != jaw: continue
        jput(jaw, sid, [(FACE_X0 + 2.3, yc - hgt / 2), (FACE_X1 - 2.6, yc - hgt / 2 + 0.4), (FACE_X1 + 0.2, yc + 0.2),
                        (FACE_X1 - 2.6, yc + hgt / 2 + 0.4), (FACE_X0 + 2.3, yc + hgt / 2)], "$rust.dark2")
    for gid, (j, gx, gy) in GRIT.items():
        if j != jaw: continue
        jput_at(jaw, gid, (gx, gy), circ(0.9), "$rust.light")
    # the lit rim along the door's back edge
    y0, y1 = (FACE_TOP + 1.6, SEAM - 1.0) if sign < 0 else (SEAM + 1.0, FACE_BOT - 1.6)
    jput(jaw, f"rim_lit_{'up' if sign < 0 else 'dn'}", [(FACE_X0 + 0.6, y0), (FACE_X0 + 1.5, y0), (FACE_X0 + 1.5, y1), (FACE_X0 + 0.6, y1)], "$bone.light")
# the chipped rim: bone flecks where the door has been knocked
jput_c("jaw_up", "chip_a", [(FACE_X1 - 0.4, -27.4), (FACE_X1 - 3.4, -26.2), (FACE_X1 - 2.8, -23.0), (FACE_X1 + 0.2, -22.4)], "$bone.light")
jput_c("jaw_dn", "chip_b", [(FACE_X1 - 0.2, 10.8), (FACE_X1 - 2.8, 12.0), (FACE_X1 - 2.4, 14.6), (FACE_X1 + 0.2, 15.2)], "$bone")
jput_c("jaw_up", "chip_c", [(FACE_X0 + 3.0, FACE_TOP - 0.2), (FACE_X0 + 6.4, FACE_TOP - 1.6), (FACE_X0 + 7.8, FACE_TOP + 0.6), (FACE_X0 + 4.6, FACE_TOP + 1.8)], "$bone")
# enraged's splits along the strata — present, unlit, in every state
jput("jaw_up", "split_a", [(FACE_X0 + 2.4, -19.5), (38.5, -21.2), (41.0, -19.0), (FACE_X1 + 0.4, -20.6), (FACE_X1 + 0.4, -19.2),
                           (41.0, -17.4), (38.5, -19.6), (FACE_X0 + 2.4, -18.2)], "$white", opacity=0)
jput("jaw_up", "split_c", [(FACE_X0 + 2.4, -4.0), (39.0, -5.6), (42.0, -3.6), (FACE_X1 + 0.4, -4.8), (FACE_X1 + 0.4, -3.4),
                           (42.0, -2.2), (39.0, -4.0), (FACE_X0 + 2.4, -2.8)], "$pheromone.light", opacity=0)
jput("jaw_dn", "split_b", [(FACE_X0 + 2.4, 9.4), (38.0, 8.0), (41.4, 10.4), (FACE_X1 + 0.4, 9.0), (FACE_X1 + 0.4, 10.6),
                           (41.4, 12.0), (38.0, 9.6), (FACE_X0 + 2.4, 10.8)], "$pheromone.light", opacity=0)

# ---- near legs, over the keel
for leg in ("nb", "nm", "nf"):
    leg_parts(leg, "$carapace", "$carapace.dark", "$husk.dark", "$carapace.dark", "$carapace.light@0.85", INK_HAIR)

RIG.check()

# ============================================================== motion
def plant_legs(pose, feet, rolls=None):
    world = solve(pose)
    for leg, (hip, fx, lf, lt) in LEGS.items():
        hx, hy, _ = world[f"{leg}_femur"]
        hf, ht = ik((hx, hy), feet[leg], lf, lt, knee_bend(leg))
        pose[f"abs:{leg}_femur"] = hf
        pose[f"abs:{leg}_tibia"] = ht
        pose[f"abs:{leg}_foot"] = (rolls or {}).get(leg, 0.0)
    return pose
def rest_feet():
    return {leg: (fx, ground_of(leg)) for leg, (hip, fx, lf, lt) in LEGS.items()}

def horns(pose, deltas):
    for i, d in enumerate(deltas): pose[f"horn_{i}"] = pose.get(f"horn_{i}", 0.0) + d
    return pose

# ---- hold: 2.6s, two strides. A slow wave gait, back to front on each side,
# the far side half a stride behind; each foot is planted most of the stride
# and pushed back under the wedge, then lifted and set down ahead.
GAIT = 2          # strides a loop
PHASE = {"nb": 0.0, "nm": 1 / 3, "nf": 2 / 3, "fb": 0.5, "fm": 5 / 6, "ff": 1 / 6}
SWING = 0.3       # of a stride a foot is off the ground (it lands at phase 0)
STRIDE = {"n": 6.2, "f": 5.2}
LIFT = {"nf": 7.0, "nm": 6.0, "nb": 6.4, "ff": 4.8, "fm": 4.2, "fb": 4.4}

def stride_of(t, leg): return (GAIT * t - PHASE[leg]) % 1.0
def foot(t, leg):
    """(dx, lift, roll): planted and sliding back from landing; in the swing the foot comes up, forward and down."""
    u = stride_of(t, leg)
    S = STRIDE[leg[0]]
    if u < 1 - SWING:
        return lerp(S, -S, u / (1 - SWING)), 0.0, 0.0
    v = (u - (1 - SWING)) / SWING
    x = lerp(-S, S, smooth(0.1, 0.85, v))
    up = math.sin(math.pi * smooth(0.0, 0.92, v)) ** 0.8
    roll = 22.0 * math.sin(math.pi * v) * (1 if leg.endswith("b") else -0.8)
    return x, LIFT[leg] * up, roll
def landed(t, leg):
    """The shock of a landing: 1 at touch-down, decaying over a fifth of a stride."""
    u = stride_of(t, leg)
    return math.exp(-u / 0.07) if u < 0.3 else 0.0
def lifted(t, leg):
    u = stride_of(t, leg)
    return math.sin(math.pi * (u - (1 - SWING)) / SWING) if u >= 1 - SWING else 0.0

def breath(t):
    """The door's breath, once a loop: 0 shut, 1 at the crack."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * (t - 0.08))

def hold_pose(t):
    dx = dy = dth = 0.0
    for leg in ("nb", "nm", "nf", "fb", "fm", "ff"):
        w = 1.0 if leg[0] == "n" else 0.55
        lam, imp = lifted(t, leg), landed(t, leg)
        pos = {"f": 1.0, "m": 0.0, "b": -1.0}[leg[1]]
        # A front foot up takes the weight back (nose up); a hind one up tips
        # it forward. Landing, the mass drops onto the foot and surges after it.
        dth += w * (-2.4 * pos * lam + 1.2 * pos * imp)
        dx += w * (0.9 * imp - 0.3 * lam)
        dy += w * (1.3 * imp - 0.5 * lam)
    # and the whole wedge rolls its weight fore and aft once a stride
    dx += 1.3 * cyc(GAIT * t, 0.1)
    dy += -2.3 * cyc(GAIT * t, 0.25)
    dth += 0.8 * cyc(GAIT * t, 0.35)
    pose = {"body": (dx, dy - 0.3, dth)}
    # the courses behind follow the front a beat late: the wedge flexes
    pose["mid"] = 2.2 * cyc(GAIT * t, -0.05) - 0.6 * dth
    pose["tail"] = 6.0 * cyc(GAIT * t, -0.18) - 0.4 * dth
    # the crest bristles in a wave from the face back to the tail, once a stride,
    # each horn standing forward and laying back a little after the one before
    horns(pose, [-9.0 + 22.0 * cyc(GAIT * t, 0.25 - 0.06 * i) for i in range(len(HORNS))])
    # the door breathes: a crack along the seam, the light in it
    b = breath(t)
    pose["jaw_up"] = -3.6 * b
    pose["jaw_dn"] = 3.6 * b
    feet, rolls = {}, {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        x, lift, roll = foot(t, leg)
        feet[leg] = (fx + x, ground_of(leg) - lift)
        rolls[leg] = roll
    return plant_legs(pose, feet, rolls)

def organ_fire(ph, amp=0.28):
    """An organ firing once a loop at `ph`: a fast swell and a slower fall."""
    def f(t):
        d = (t - ph) % 1.0
        return 1.0 + amp * (smooth(0.0, 0.05, d) * math.exp(-max(0.0, d - 0.05) / 0.09))
    return f

# ---- volley: 0.55s, the door coming open on purpose. Brace (the wedge sits
# back on its hind feet, horns laid flat, the vent squeezed, the door clamped),
# open (the halves swing apart on their hinges and the vent flares wide), throw
# (the wedge surges into the opening, nose down, horns thrown forward in a
# wave), close (the door slams, a rebound, and it settles onto its feet).
BRACE_BODY = (-3.6, 2.2, -4.0)
THROW_BODY = (2.6, 0.6, 3.6)
JAW_OPEN = 18.0
def volley_pose(t):
    brace = smooth(0.0, 0.18, t)
    throw = smooth(0.26, 0.4, t)
    settle = smooth(0.42, 0.95, t)
    body = [lerp(lerp(0.0, b, brace), th, throw) for b, th in zip(BRACE_BODY, THROW_BODY)]
    # settle with one small rebound past rest
    reb = math.sin(math.pi * smooth(0.55, 1.0, t)) * 0.6
    body = [lerp(v, 0.0, settle) - (0.6 * reb if k == 0 else 0.0) for k, v in enumerate(body)]
    pose = {"body": tuple(body)}
    # the door: clamps a hair in the brace, opens wide, holds through the throw, slams
    opening = smooth(0.14, 0.3, t) * (1 - smooth(0.5, 0.72, t))
    slam = math.sin(math.pi * smooth(0.72, 0.9, t)) * 2.0
    clamp = 1.5 * brace * (1 - smooth(0.14, 0.2, t))
    pose["jaw_up"] = -JAW_OPEN * opening + clamp + slam
    pose["jaw_dn"] = JAW_OPEN * opening - clamp - slam
    # the courses: the tail tucks under in the brace, whips up in the throw
    pose["mid"] = 3.0 * brace * (1 - throw) - 3.5 * throw * (1 - settle)
    pose["tail"] = 6.0 * brace * (1 - throw) - 5.0 * throw * (1 - settle) + 1.6 * reb
    # horns: laid back in the brace, thrown forward in a wave, and settling
    deltas = []
    for i in range(len(HORNS)):
        lag = 0.022 * i
        back = -20.0 * smooth(0.02 + lag * 0.5, 0.18 + lag * 0.5, t)
        up = 42.0 * smooth(0.26 + lag, 0.4 + lag, t)
        home = smooth(0.46 + lag, 0.92, t)
        wob = 6.0 * math.sin(math.pi * smooth(0.6 + lag, 1.0, t)) * (1 - smooth(0.95, 1.0, t))
        deltas.append((back + up) * (1 - home) - wob)
    horns(pose, deltas)
    # and it settles onto the walk's first frame, so the hand-back has no cut:
    # the feet shuffle from where the brace planted them to where `hold` starts
    home = smooth(0.6, 1.0, t)
    h0 = hold_pose(0.0)
    pose["body"] = tuple(v + home * w for v, w in zip(pose["body"], h0["body"]))
    for k in ["mid", "tail", "jaw_up", "jaw_dn"] + [f"horn_{i}" for i in range(len(HORNS))]:
        pose[k] = pose.get(k, 0.0) + home * h0.get(k, 0.0)
    feet, rolls = {}, {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        x, lift, roll = foot(0.0, leg)
        feet[leg] = (fx + home * x, ground_of(leg) - home * lift)
        rolls[leg] = home * roll
    return plant_legs(pose, feet, rolls)
def volley_vent(t):
    return 1.0 - 0.22 * smooth(0.0, 0.14, t) + 1.0 * smooth(0.14, 0.3, t) - 0.78 * smooth(0.5, 0.85, t)

# ---- death: 0.7s, a door coming down. The vent flares once and burns out;
# the door gapes and hangs; the horns drop flat face-end first; the legs fold
# out from under the wedge and it comes down on its keel, nose first. The
# chips leave the rim. Still from 0.85.
def death_pose(t):
    jolt = math.sin(math.pi * smooth(0.0, 0.16, t))
    fall = smooth(0.14, 0.72, t)
    pose = {"body": (-1.6 * jolt + 1.0 * fall, -1.8 * jolt + 10.5 * fall, -2.0 * jolt + 4.0 * fall)}
    pose["mid"] = -3.0 * jolt - 4.0 * fall
    pose["tail"] = -4.0 * jolt - 6.5 * fall
    gape = smooth(0.04, 0.3, t)
    hang = smooth(0.3, 0.75, t)
    pose["jaw_up"] = -16.0 * gape + 9.0 * hang
    pose["jaw_dn"] = 22.0 * gape - 4.0 * hang
    horns(pose, [-(40.0 - 1.5 * i) * smooth(0.08 + 0.04 * i, 0.4 + 0.04 * i, t) + 8.0 * jolt for i in range(len(HORNS))])
    feet = {}
    for leg, (hip, fx, lf, lt) in LEGS.items():
        out = {"f": 1.0, "m": 0.3, "b": -1.0}[leg[1]]
        feet[leg] = (fx + out * 9.0 * fall, ground_of(leg) - 0.6 * fall)
    rolls = {leg: (18.0 if leg.endswith("b") else -18.0) * fall for leg in LEGS}
    return plant_legs(pose, feet, rolls)

# ============================================================== clips
tracks = RIG.tracks
STILL = [p["id"] for p in RIG.parts if p.get("shape", {}).get("kind") == "circle"] + ["organ_a", "organ_b", "organ_c", "vent", "vent_lip", "maw", "maw_glow"]
animations = {}

TS_HOLD = keyset(40)
b = breath
animations["hold"] = {
    "description": "The door on watch, walking it: six short legs in a slow wave gait, back to front on each side, each foot planted and pushed back under the wedge then lifted and set down ahead, and the keystone rolling its weight onto every foot as it lands. The two courses behind the face flex a beat late so the tail sways; the nine horns bristle in a wave from the face back to the tail once a stride; the door breathes once — the two halves parting a crack on their hinges, the vent's light in the seam and the vent swelling with it — and the three organs fire down the flank in turn.",
    "duration": 2.6,
    "tracks": tracks(hold_pose, TS_HOLD, [
        ("vent", "scale", lambda t: 1.0 + 0.12 * b(t)),
        ("vent_glow", "scale", lambda t: 0.85 + 0.4 * b(t)),
        ("vent_glow", "opacity", lambda t: 0.65 + 0.35 * b(t)),
        ("maw_glow", "opacity", lambda t: 0.5 + 0.5 * b(t)),
        ("organ_a", "scale", organ_fire(0.12)),
        ("organ_b", "scale", organ_fire(0.45)),
        ("organ_c", "scale", organ_fire(0.78)),
    ], still=STILL),
}

TS_DEATH = [i / 30 for i in range(27)] + [0.9, 1.0]
CHIPS = {"chip_a": (6.0, 10.0, 160.0, 0.1), "chip_b": (6.0, 6.0, -140.0, 0.16), "chip_c": (-5.0, 12.0, 200.0, 0.2)}
def chip_fly(dx, dy, rot, t0):
    return [lambda t, d=dx, a=t0: d * smooth(a, a + 0.35, t),
            lambda t, d=dy, a=t0: d * smooth(a, a + 0.35, t) ** 1.6 - 5.0 * math.sin(math.pi * smooth(a, a + 0.35, t)),
            lambda t, r=rot, a=t0: r * smooth(a, a + 0.35, t)]
death_extra = [
    ("vent", "scale", lambda t: 1.0 + 0.5 * math.sin(math.pi * smooth(0.0, 0.2, t)) - 0.3 * smooth(0.2, 0.6, t)),
    ("vent_glow", "scale", lambda t: 1.0 + 0.8 * math.sin(math.pi * smooth(0.0, 0.2, t))),
    ("vent_glow", "opacity", lambda t: 1.0 - smooth(0.12, 0.55, t)),
    ("maw_glow", "opacity", lambda t: 1.0 - smooth(0.1, 0.5, t)),
    ("organ_a", "opacity", lambda t: 1.0 - 0.85 * smooth(0.15, 0.6, t)),
    ("organ_b", "opacity", lambda t: 1.0 - 0.85 * smooth(0.22, 0.7, t)),
    ("organ_c", "opacity", lambda t: 1.0 - 0.85 * smooth(0.3, 0.78, t)),
]
for cid, (dx, dy, rot, t0) in CHIPS.items():
    death_extra += [(cid, "opacity", lambda t, a=t0: 1.0 - smooth(a + 0.2, a + 0.4, t))]
def add_on(trs, ts, part, fns):
    """Add `fns` (prop -> fn(t)) on top of whatever the rig already has `part` doing."""
    fns = dict(fns)
    for tr in trs:
        if tr["part"] == part and tr["prop"] in fns:
            f = fns.pop(tr["prop"])
            tr["keys"] = [[k[0], r2(k[1] + f(k[0]))] for k in tr["keys"]]
    for prop, f in fns.items():
        trs.append({"part": part, "prop": prop, "keys": [[r2(t), r2(f(t))] for t in ts], "ease": "linear"})

death_tracks = tracks(death_pose, TS_DEATH, death_extra, still=STILL)
# chips: their flight added to whatever the jaw does to them
for cid, (dx, dy, rot, t0) in CHIPS.items():
    add_on(death_tracks, TS_DEATH, cid, zip(("x", "y", "rot"), chip_fly(dx, dy, rot, t0)))
# the face slumps stratum into stratum: each band slides down after the one above it
for k, sid in enumerate(sorted(STRATA)):
    add_on(death_tracks, TS_DEATH, sid, {"y": lambda t, k=k: 1.6 * smooth(0.2 + 0.05 * k, 0.55 + 0.04 * k, t)})
animations["death"] = {
    "description": "A door coming down: one jolt, then the vent flares and burns out, the door gapes on its hinges and hangs there, the face slumps stratum into stratum and sheds its three chips, the horns drop flat in a wave from the face back, and the legs fold out from under a wedge nothing is holding up — it comes down on its keel nose first. Still from 0.85.",
    "duration": 0.7,
    "tracks": death_tracks,
}

TS_VOLLEY = keyset(24)
animations["volley"] = {
    "description": "The door coming open on purpose, as the fan leaves (EnemySystem plays it once when a volley carries more than one bolt). Brace: the wedge sits back onto its hind feet, nose up, horns laid flat, the vent squeezed and the door clamped. Open: the two halves swing apart on their hinges and the vent flares to nearly twice its size, the maw lit behind the door. Throw: the wedge surges into the opening nose down with the tail whipping up and the horns thrown forward in a wave from the face back, every organ firing. Close: the door slams, one rebound, and it settles, shuffling its feet onto the first frame of `hold` so the hand-back has no cut.",
    "duration": 0.55,
    "tracks": tracks(volley_pose, TS_VOLLEY, [
        ("vent", "scale", volley_vent),
        ("vent_glow", "scale", lambda t: 0.8 + 1.2 * smooth(0.14, 0.32, t) - 1.0 * smooth(0.5, 0.9, t)),
        ("maw_glow", "scale", lambda t: 1.0 + 0.35 * math.sin(math.pi * smooth(0.2, 0.62, t))),
        # the glows end where `hold` starts them
        ("vent_glow", "opacity", lambda t: lerp(0.65 + 0.35 * b(0.0), 1.0, smooth(0.08, 0.2, t) * (1 - smooth(0.6, 1.0, t)))),
        ("maw_glow", "opacity", lambda t: lerp(0.5 + 0.5 * b(0.0), 1.0, smooth(0.08, 0.2, t) * (1 - smooth(0.6, 1.0, t)))),
        ("organ_a", "scale", lambda t: 1.0 + 0.4 * math.sin(math.pi * smooth(0.24, 0.52, t))),
        ("organ_b", "scale", lambda t: 1.0 + 0.4 * math.sin(math.pi * smooth(0.27, 0.56, t))),
        ("organ_c", "scale", lambda t: 1.0 + 0.4 * math.sin(math.pi * smooth(0.3, 0.6, t))),
    ], still=STILL),
}

# ============================================================== states
def posed_set(pose, ids):
    """`at`/`rot` patches that put parts where `pose` has them — a state drawn as a pose."""
    now = RIG.posed_parts(pose)
    out = {}
    for pid in ids:
        x, y, a = now[pid]
        out[f"{pid}.at"] = [r2(x), r2(y)]
        if abs(wrap(a)) > 0.01: out[f"{pid}.rot"] = r2(wrap(a))
    return out
SPINES = [f"spine_{i}" for i in range(len(HORNS))]
EDGES = [f"spine_edge_{i}" for i in range(len(HORNS))]
COURSE_IDS = [c[0] for c in COURSES]
TEETH = [f"tooth_{i}" for i in range(n_tooth)]

enraged_set = {}
for c in COURSE_IDS:
    enraged_set.update({f"{c}.fill": "$rust", f"{c}_lit.fill": "$rust.light@0.8", f"{c}_shade.fill": "$dead", f"{c}_stratum.fill": "$dead@0.8"})
enraged_set.update({
    "face_up.fill": "$dead", "face_dn.fill": "$dead",
    "face_rim_up.fill": "$bone.light", "face_rim_dn.fill": "$bone.light",
    "strata_a.fill": "$pheromone.dark", "strata_b.fill": "$pheromone", "strata_c.fill": "$pheromone.dark",
    "strata_d.fill": "$pheromone", "strata_e.fill": "$pheromone.dark", "strata_f.fill": "$pheromone",
    "split_a.opacity": 1, "split_b.opacity": 1, "split_c.opacity": 1,
    "vent.fill": "$dead", "vent_glow.fill": "$dead@0", "vent_lip.fill": "$dead",
    "maw_glow.fill": {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$pheromone.light"], [1, "$pheromone@0.1"]]},
    "chip_a.fill": "$white", "chip_b.fill": "$white", "chip_c.fill": "$white",
    "organ_a.scale": 1.02, "organ_b.scale": 0.88, "organ_c.scale": 0.76,
})
for i, s in enumerate(SPINES):
    enraged_set[f"{s}.fill"] = "$bone.light" if i % 2 == 0 else "$white"
    enraged_set[f"{s}.scale"] = 1.18
for e in EDGES:
    enraged_set[f"{e}.fill"] = "$white"
    enraged_set[f"{e}.scale"] = 1.18
for tth in TEETH:
    enraged_set[f"{tth}.fill"] = "$white"

FINAL_OPEN = {"jaw_up": -7.0, "jaw_dn": 7.0}
final_set = {}
for c in COURSE_IDS:
    final_set.update({f"{c}.fill": "$dead", f"{c}_lit.fill": "$dead.light@0.8", f"{c}_shade.fill": "$dead.dark", f"{c}_stratum.fill": "$ink@0.8"})
final_set.update(posed_set(FINAL_OPEN, JAW_PARTS["jaw_up"] + JAW_PARTS["jaw_dn"]))
final_set.update({
    "face_up.fill": "$dead", "face_dn.fill": "$dead",
    "face_rim_up.fill": "$ink", "face_rim_dn.fill": "$ink",
    "rim_lit_up.opacity": 0, "rim_lit_dn.opacity": 0,
    **{f"{s}.fill": "$dead.dark" for s in STRATA},
    **{f"{g}.fill": "$ink" for g in GRIT},
    "chip_a.opacity": 0, "chip_b.opacity": 0, "chip_c.opacity": 0,
    "tooth_1.opacity": 0, "tooth_4.opacity": 0, "tooth_6.opacity": 0,
    **{f"{tth}.fill": "$bone.dark" for tth in TEETH if tth not in ("tooth_1", "tooth_4", "tooth_6")},
    "vent.fill": "$ink", "vent_lip.fill": "$dead",
    "vent_glow.fill": {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$white"], [0.6, "$spore.light@0.8"], [1, "$spore@0.15"]]},
    "vent_glow.scale": 1.9,
    "maw_glow.fill": {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$white"], [1, "$spore.light@0.2"]]},
    "maw_glow.scale": 1.15,
    **{f"{r}.fill": "$bone.dark" for r in RIVETS},
    **{f"{s}.fill": "$bone" for s in SPINES},
    **{f"{e}.fill": "$white" for e in EDGES},
    "organ_a.scale": 1.06, "organ_b.scale": 0.9, "organ_c.scale": 0.74,
})

variants = {
    "enraged": {
        "description": "Phase two: the face splits along the layers it was packed in, and what the door was holding back comes through the gaps — pink, in every stratum and in the seam each time the door breathes. The keystone goes the dark red of a bruise. The vent goes out — it has stopped spraying, because it has stopped keeping its distance — and every horn along the back stands up bone white, the teeth with them.",
        "scale": 1.1,
        "set": enraged_set,
    },
    "final": {
        "description": "Phase three: the door is off. The face it spent its life being has gone to dark strata with the bone rim broken off it, the chips and three of the teeth are missing, and it no longer shuts — the halves hang a hand's width apart on their hinges, and what shows through the gap, and in the vent under it, is white, and much too big for the head it is in. The legs are the only part of it still the colour of a living animal.\n\nNot brighter than `enraged`, which is the face splitting: this is the face being over. A body whose whole identity is \"it was a door\" has one escalation left, and it is that there is no door.",
        "scale": 1.14,
        "set": final_set,
    },
}

# ============================================================== document
DESCRIPTION = (
    "A soldier bred as a door. One tapering keystone — a flat face at the front, narrowing to nothing behind — so the silhouette is a cork, "
    "and nothing else in the game is a straight-edged wedge. The face is the door: two halves in a bone rim, packed in horizontal strata, "
    "teeth down the front edge, hinged at the head's top and bottom corners and meeting along the middle stratum. Under it is the acid vent, "
    "teal because what leaves it glows that colour — `ss.enemy.plug`, a chip of this same door with the acid seeping through it. A crest of "
    "nine horns runs down the back, three to each course of plate; three organs down the flank. Seen side-on facing +x; the game mirrors it. "
    "Built on a skeleton (scripts/warden.py): the keystone is three courses on a chain of bones, front over back, so the wedge flexes and its tail "
    "sways; each horn is hinged at its root; each door half at its hinge; and six short legs (three near, three far and darker) are solved "
    "every frame to a clawed foot on the ground, so a planted foot stays planted while the wedge rolls over it. `hold` is the idle and the walk — "
    "a slow wave gait, the crest bristling in a wave, the door breathing a crack of light along its seam. `volley` is the door coming open on "
    "purpose as the fan leaves: brace, open, throw, close. Gameplay radius 42. The `death` clip brings the door down rather than killing an animal: "
    "it gapes and hangs, the face slumps stratum into stratum and sheds its chips, the horns drop flat face-end first and the legs fold out from "
    "under the wedge."
)

doc = {
    "id": "ss.enemy.warden",
    "name": "Warden",
    "description": DESCRIPTION,
    "tags": ["enemy", "boss"],
    "size": SIZE,
    "meta": {"radius": 42},
    "parts": RIG.parts,
    "variants": variants,
    "skeleton": RIG.skeleton(),
    "animations": animations,
}

# The drawing sits a little back of the canvas centre: the door opens forward.
SHIFT = (-2.5, 0.0)
def shifted(v): return [r2(v[0] + SHIFT[0]), r2(v[1] + SHIFT[1])]
for p in RIG.parts:
    p["at"] = shifted(p["at"])
for v in variants.values():
    for k in list(v["set"]):
        if k.endswith(".at"): v["set"][k] = shifted(v["set"][k])
doc["skeleton"]["joints"] = {k: shifted(j) for k, j in doc["skeleton"]["joints"].items()}

if __name__ == "__main__":
    write_doc(doc, OUT)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(OUT)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks, {os.path.getsize(OUT)//1024} KB")
