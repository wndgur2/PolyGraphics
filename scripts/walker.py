"""The walkers' rig — one script, one self-contained document per playable character.

    python3 scripts/walker.py            # rewrites apps/ss/assets/ss-char-<name>.json, all eight
    python3 scripts/walker.py arin sol   # only these

Skeleton first, parts second, motion last — docs/character-rig-guide.md says why
and in what order. One facing and one hinge grammar are shared; everything else
is allowed to differ, because eight people who share a coat, a helmet and two
feelers are one person eight times. Each character therefore has its own
PRIMARY SHAPE — the thing you would draw to mean them in one stroke — and the
body is built to that shape from its own skeleton row:

  arin   a circle: the bell coat, the egg helmet, and the prototype emitter with
         its two feelers — the only one of the eight that has feelers, because
         the antennae were the prototype's design (A004); the later marks vent
         through a tube (H013, K030)
  sol    a triangle, leaning: a short jacket over long legs, bare head, a scarf
         flying back, the helmet at the hip — the runner
  haram  a square: a slab body with squared shoulders, bone pauldrons and a
         chest plate, a box helmet, the survey on the back — the wall
  mir    a stem (and she is Mina — the id is the handle the game pins, the name
         is `display`): the one of the eight who is not wearing a coat. The
         plant is laid on the body in three turns that hang and pinch the way a
         cord does round a barrel — two cords and, at the hip, a wide one that
         reads as a garment and hides where the body ends and the legs start.
         A thorn off each end of the top turn, the far side of her in shadow
         behind them, and she stands up — head over the shoulders with a neck
         under it, which nobody else here has, on the slimmest arms in the set.
         A helmet cut to a profile with a lamp and a slit on it and nothing
         between them, the piece of burrow wall at the hip — the one who left
         the emitter in the burrow, and the one the weapon is still holding:
         the free end of the cord is tied over her near ankle and trails off
         along the floor behind her, the snare's tail. A celadon suit, the
         whitest helmet, and the one lamp of the eight lit
  kano   a column: a narrow long coat, a peaked hood, a staff taller than the
         head — the one who does not stop
  eden   a mushroom: a round coat under a wide hat brim, the throat swelling
         teal — the one who sat six years beside the fungi
  rowan  a wedge: broad and low, one whole arm plated in carapace, the emitter
         turned to stone on the back — the wall's builder
  teo    small: the smallest body under the biggest load, a satchel of pages
         wider than the shoulders, goggles and a filter — the carrier

A part is placed by naming the joint it hangs from plus a length and an angle;
a clip turns joints. The skeleton goes into each document by joint name. The
antenna and the organ stay `use` parts, moved whole.
"""
import json, math, sys

R = lambda d: math.radians(d)
def r2(x): return round(x, 2)

# Two outline weights and one rule for which is which, because a body whose
# sleeve is outlined at half the weight of the coat it hangs on reads as a
# sleeve drawn by somebody else. **`thin` is the silhouette, `hair` is
# everything laid on top of it.** The coat, the helmet and the near arm and
# hand are the line the eye traces round the body — the near sleeve is half
# inside the coat's outline and half outside it (docs/character-rig-guide.md
# §2), so it is silhouette and takes the same weight. Packs, stakes, jars,
# loads and lamp rings sit inside that line and take `hair`. Parts dark enough
# to be their own edge — the feet, the visor, the far arm behind the body —
# take none at all.
hair = {"color": "$ink", "width": "hair"}
thin = {"color": "$ink", "width": "thin"}

# ============================================================== 1. the shared facing and joints
# Canvas 32×32, origin at the centre, +x right, +y down. Every body faces the
# viewer's FRONT-RIGHT. A body facing you has its right hand on your left, so the
# RIGHT shoulder is the near one, low and on the LEFT of the picture, the LEFT
# shoulder the far one, high and on the RIGHT. The engine mirrors the frame to walk left.
BASE_SKELETON = {
    "shoulder_near": (-4.8, -3.0), "shoulder_far": (5.6, -4.4),
    "hip_near": (-2.0, 12.0), "hip_far": (3.4, 11.2),
    "head": (2.0, -8.0), "head_tilt": -10,
    "foot_near": (-1.6, 13.1), "foot_far": (3.6, 12.5),
    "pack": (-6.0, -3.6),
    "feeler_root": (-5.4, -5.9), "feeler_far_root": (-6.8, -5.5),
}
BASE_POSE = {"coat_lean": 2, "arm_hang": 6, "arm_far_hang": -8, "visor_turn": -5}
BASE = {
    # the suit's colour: a cold-family token and a level. The coat is the tint, the
    # mantle one step lighter, the far arm one darker, the helmet two lighter —
    # cold on a warm field is what makes the player the one thing found at a glance
    "tint": ("frost", 0),
    # "f" or "m": a woman's shoulder line is narrower and the coat draws in at the
    # waist, a man's shoulders and chest are broader — with the feet to match.
    # Hair, where it shows, is each row's own part (a tail, a braid, a lock, a beard).
    "sex": "m",
    # `organ` is the premise worn on the body: `ss.lib.organ` with `variant:
    # "dead"`, the same document every creature in the hive wears lit, cracked
    # and silent on the coat of whoever is being hunted for the silence. It is
    # on by default and should stay on — a walker without one has to say in its
    # own description where theirs went.
    "coat": "bell", "cloak_sx": 1.0, "hem": 0.0, "coat_fill": None, "cape": True, "cape_fill": None, "organ": True,
    "head": "egg", "head_r": (5.3, 5.8), "head_fill": None, "visor_w": 6.6, "visor_h": 2.6, "lamp_fill": "$silent",
    "arm_len": 7.6, "arm_w": 3.0, "arm_fill": None, "arm_far_len": 7.0, "arm_far_w": 2.6,
    "hand_r": (1.7, 1.9), "hand_far_r": (1.4, 1.6), "hand_fill": "$slate.dark", "hand_far_fill": "$slate",
    "legs": False, "foot_w": 4.8, "foot_h": 2.7, "foot_far_w": 4.2, "foot_far_h": 2.4,
    "pack": False, "pack_w": 4.2, "pack_h": 4.4, "pack_fill": "$slate.light", "feelers": False,
    # `head_nod` is the head's own twitch about its centre, twice a stride. It is
    # what makes a walk look busy or unbothered, and it is the cheapest dial in
    # here: at 2.5 the head is working, at half a degree it is carried.
    "walk": {"duration": 0.56, "stride": 2.6, "lift": 1.2, "bob": 1.4, "sway": 3.0, "arm_swing": 14, "lurch": 0.0, "leg_swing": 22, "head_nod": 2.5},
    "idle": {"duration": 1.15, "feelers": "sweep", "march": False},
}

# ============================================================== 1a. Mina's canon
# Mina is the one body in this file that is not wearing a coat, so her outline is
# a figure rather than a garment's, and a figure has to be written down or it
# drifts every time somebody nudges a point. Twelve rounds of review landed on
# the numbers below and they are re-derived here rather than left where the
# nudges put them: everything from her shoulder line down is a function of four
# widths and five heights, so changing the figure is changing one number instead
# of hunting through a row. They live this high up because the coat table reads
# them.
#
# Heights first. The body is 28.4 tall, head top to sole, and the head is a third
# of that — the guide's ratio, and the one proportion here that is not hers. It
# was a statue's 0.31 for a while, which at the size the game shows her is a pin
# on a stick; the head is the brightest thing on her and the first thing found.
M_TOP, M_SOLE = -14.4, 14.0
M_HEAD_R = (4.3, 4.7)
M_SHOULDER_Y, M_CHEST_Y, M_WAIST_Y, M_HIP_Y, M_HEM_Y = -3.1, -0.8, 3.4, 6.6, 9.4
# Widths at those heights. Shoulders wider than the head; the chest in under the
# deltoid; the waist the narrowest thing on her. An earlier body went *out*
# below its own shoulder line — 7.0 across the shoulders and 9.3 across the
# chest — and a torso that does that is a loose top rather than a body, whatever
# is drawn over it.
M_SHOULDER, M_CHEST, M_WAIST = 7.8, 7.0, 5.4
# The hip and the thigh are **not** symmetric about that centre line, and this is
# the difference between a figure and a snowman. In a three-quarter view the
# widest part of a hip is behind the body; the front of a pelvis is close to
# flat. Flaring it evenly puts a bulge on the front where there is nothing to
# make one — which is what it did — so the two levels carry a back distance and
# a front distance instead of one width. The front line then runs long and
# almost straight from the chest, through the waist, down to the thigh, and the
# whole of the flare is on the back. That is the S, and the S is the point.
M_HIP_B, M_HIP_F = 4.25, 3.15       # hip, from the centre line: 7.4 across
M_THIGH_B, M_THIGH_F = 3.55, 2.95   # thigh: 6.5 across
# The body does not stop at the hip. It used to, and the join showed: a torso
# ending on a hem line with two bare legs starting under it is an upper half and
# a lower half, drawn separately and meeting in public. It runs on to
# `M_HEM_Y` in the thigh now, and the lowest turn is wide enough to sit over
# that edge — the seam happens *inside* the plant, so what the eye gets is body,
# then a wrapped band where a skirt would be, then leg.
# The centre line of a body facing front-right sits a touch right of the canvas.
M_CX = 0.15
M_L = lambda w: M_CX - w / 2        # the back (screen-left) edge at a symmetric width
M_R = lambda w: M_CX + w / 2        # the front (screen-right) edge
M_BK = lambda d: M_CX - d           # a back edge given as a distance
M_FR = lambda d: M_CX + d           # a front edge given as a distance

def shade(tint, delta):
    """A token in the tint's family, `delta` steps lighter (+) or darker (-) than its base, clamped to the ramp."""
    base, level = tint
    lv = max(-2, min(2, level + delta))
    return f"${base}" + {-2: ".dark2", -1: ".dark", 0: "", 1: ".light", 2: ".light2"}[lv]

def hang(joint, length, angle):
    return (joint[0] - length / 2 * math.sin(R(angle)), joint[1] + length / 2 * math.cos(R(angle)))
def below(joint, dist, angle):
    return (joint[0] - dist * math.sin(R(angle)), joint[1] + dist * math.cos(R(angle)))
N = 12
TS = [i / N for i in range(N + 1)]
def track(part, prop, vals, ease="linear"):
    return {"part": part, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(TS, vals)], "ease": ease}
def key3(part, prop, a, b):
    return {"part": part, "prop": prop, "keys": [[0, a], [0.5, b], [1, a]]}
def swing(joint, centre, theta):
    dx, dy = centre[0] - joint[0], centre[1] - joint[1]
    c, s = math.cos(R(theta)), math.sin(R(theta))
    return (dx * c - dy * s - dx, dx * s + dy * c - dy, theta)

def P_(id, at, shape, fill, rot=None, stroke=None):
    p = {"id": id, "at": [r2(at[0]), r2(at[1])], "shape": shape, "fill": fill}
    if rot is not None: p["rot"] = rot
    if stroke: p["stroke"] = stroke
    return p
rect = lambda w, h, corner=0.5: {"kind": "rect", "w": w, "h": h, "corner": corner}
ell = lambda rx, ry: {"kind": "ellipse", "rx": rx, "ry": ry}
circ = lambda r: {"kind": "circle", "r": r}

poly = lambda pts: {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in pts]}

def stem(pts, w0, w1, rail=0.0, bulge=0.0):
    """A centreline swept by a taper and closed into one polygon. `ss.proj.vine`
    draws its plants this way — the shape *is* the path the thing grew along —
    and a plant grown on a body has to be the same plant. It draws a lock of
    hair too: hair and cord are one problem, a line whose width changes.

    `rail` is how the arsenal lights a stem: it draws that fraction of the width
    as a strip hugging the *outer* edge instead of the whole band, so calling
    `stem` twice with the same points — once plain and dark, once with a rail and
    light — gives a cord and a highlight that share an edge by construction. The
    strip is measured against the width **at each point**, which is the whole
    reason it is a parameter and not a second centreline pushed sideways: a
    constant sideways push is sized for the band's middle, and anywhere the band
    pinches or tapers below that the highlight walks off the cord and hangs in
    the air beside it as a pale fan. That was drawn, on the skirt's tail.

    `bulge` swells the width in the middle of the run and pinches it at both
    ends, on top of the taper. It is foreshortening, and it is what makes a cord
    read as going *round* something rather than lying flat across it: the part
    facing you is seen at its full width, and the part turning away past the
    side of the body is seen edge-on and gets thin. Without it a band on a torso
    is a stripe painted on a board, however hard the centreline curves.

    There is no fiddlehead here, and that was tried: a curl needs an enclosed
    hole wider than the 1px ink that rings it, which at 32x32 puts the curl at a
    quarter of the body — and at anything smaller it fills in and reads as a
    fist on the end of a limb. The plant's growing end lives at 56x56 in
    `ss.proj.vine`; on a body it is a taper to a point."""
    pts = list(pts)
    n = len(pts) - 1
    def normal(i):
        (ax, ay), (bx, by) = pts[max(0, i - 1)], pts[min(n, i + 1)]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1.0
        return (-dy / L, dx / L)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        nx, ny = normal(i)
        t = i / n
        w = (w0 + (w1 - w0) * t) / 2 * (1 + bulge * math.sin(math.pi * t))
        if rail:
            x, y = x - nx * w * (1 - rail), y - ny * w * (1 - rail)
            w *= rail
        left.append((x + nx * w, y + ny * w)); right.append((x - nx * w, y - ny * w))
    return poly(left + right[::-1])

# ============================================================== 2. the coats — the primary shape of the body
def coat_points(kind, sn, sf, hem):
    top = [[sn[0] + 0.6, sn[1] - 0.2], [sf[0] - 0.6, sf[1] - 0.2]]
    if kind == "bell":      # a bell to a rounded hem
        return top + [[7.5, 1.6], [7.7, 6.0], [6.8, 10.6 + hem], [4.4, 11.9 + hem], [0.2, 12.3 + hem], [-4.2, 11.9 + hem], [-6.8, 10.6 + hem], [-7.6, 6.0], [-7.2, 1.2]]
    if kind == "jacket":    # short, to the hips; the legs show under it
        return top + [[7.2, 1.2], [6.9, 6.6 + hem], [4.0, 7.4 + hem], [-3.8, 7.4 + hem], [-6.4, 6.6 + hem], [-6.9, 1.0]]
    if kind == "jacket_belly":  # the same jacket over a belly grown into a sac
        return top + [[7.4, 0.8], [9.4, 3.8], [9.2, 7.0], [6.4, 8.6 + hem], [1.0, 9.0 + hem], [-3.8, 8.2 + hem], [-6.4, 6.8 + hem], [-6.9, 1.0]]
    if kind == "slab":      # squared shoulders, straight sides, a flat hem
        return [[sn[0] - 1.6, sn[1] - 0.6], [sf[0] + 1.8, sf[1] - 0.6], [8.6, 0.6], [8.8, 10.8 + hem], [6.8, 12.2 + hem], [-6.4, 12.2 + hem], [-8.6, 10.8 + hem], [-8.4, 0.4]]
    if kind == "wrap":      # not a garment: the body, with the plant laid over it in turns
        # Cloth hangs, plants cling, and the silhouette is where the difference
        # lives. A coat leaves the shoulder and swings clear of the body, so the
        # outline belongs to the coat and the body inside it could be anybody's.
        # This one *is* the body — §1a's canon, shoulder to hem — and the plant
        # goes over it as three turns with the body showing in the gaps (the
        # row's `band_*`). A closed piece with a leafy hem was tried first and
        # read as a torn tunic: a ragged edge on one shape is damage, and what
        # reads as wrapped is seeing the body between the turns. It stops at the
        # hip and the legs carry on out from under it, which no other walker does.
        return top + [[M_R(M_CHEST), M_CHEST_Y], [M_R(M_WAIST), M_WAIST_Y], [M_FR(M_HIP_F), M_HIP_Y],
                      [M_FR(M_THIGH_F), M_HEM_Y - 0.4], [M_CX + 0.2, M_HEM_Y], [M_BK(M_THIGH_B), M_HEM_Y - 0.5],
                      [M_BK(M_HIP_B), M_HIP_Y], [M_L(M_WAIST), M_WAIST_Y], [M_L(M_CHEST), M_CHEST_Y]]
    if kind == "column":    # narrow and long
        return top + [[6.4, 1.6], [6.6, 7.0], [6.0, 12.6 + hem], [3.8, 13.4 + hem], [-3.4, 13.4 + hem], [-5.6, 12.6 + hem], [-6.2, 7.0], [-6.0, 1.2]]
    if kind == "round":     # wide and soft, the hem tucked in
        return top + [[8.2, 2.4], [8.6, 7.2], [7.0, 11.0 + hem], [3.6, 12.2 + hem], [-3.4, 12.2 + hem], [-6.8, 11.0 + hem], [-8.6, 7.2], [-8.2, 2.2]]
    if kind == "wedge":     # broad and low, widest at the hem
        return top + [[8.0, 1.6], [9.4, 7.0], [9.0, 11.2 + hem], [5.0, 12.2 + hem], [-4.8, 12.2 + hem], [-8.8, 11.2 + hem], [-9.4, 7.0], [-7.8, 1.4]]
    if kind == "small":     # a short bell for a short body
        return top + [[6.6, 1.4], [6.8, 5.4], [6.0, 9.4 + hem], [3.8, 10.6 + hem], [0.2, 11.0 + hem], [-3.6, 10.6 + hem], [-5.8, 9.4 + hem], [-6.6, 5.4], [-6.2, 1.0]]
    raise KeyError(kind)

def cape_points(sn, sf, sx):
    pts = [[sn[0], sn[1] - 0.2], [sf[0], sf[1] - 0.2], [7.3, 0.9], [3.4, 2.4], [0.2, 1.3], [-3.4, 2.2], [-7.0, 0.2]]
    return [[x * sx, y] for x, y in pts]

def dome_points(rx, ry, n=32):
    """A helmet's outline: the head ellipse with the front-lower quarter cut in
    over the visor and the back-lower quarter let out into a nape. Both are
    smooth functions of the angle rather than moved corners, because a corner
    moved by hand on a 9px head is a facet and reads as a gem — and `n` is 24
    for the same reason, since the renderer draws a polygon with straight
    edges and nothing rounds them for you. Both numbers are small on purpose:
    at 0.26 the front cut pulled the shell in behind its own visor."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n - math.pi / 2
        c, s_ = math.cos(a), math.sin(a)
        front, back = max(0.0, c) * max(0.0, s_), max(0.0, -c) * max(0.0, s_)
        r = 1.0 - 0.10 * front + 0.15 * back
        pts.append((rx * r * c, ry * r * s_))
    return pts

# ============================================================== 3. the heads — the second shape
def head_parts(kind, S, C, P):
    h = S["head"]; rx, ry = C["head_r"]; tilt = S["head_tilt"]
    visor = P_("visor", (h[0] + 1.6, h[1] + 1.2), rect(C["visor_w"], C["visor_h"], 1.3), "$ink", rot=P["visor_turn"])
    if kind == "egg":
        return [P_("head", h, ell(rx, ry), C["head_fill"], rot=tilt, stroke=thin), visor]
    if kind == "bare":      # skin, hair over it, and a mouth — no helmet
        return [P_("head", h, ell(rx, ry), "$skin", rot=tilt, stroke=thin),
                P_("hair", (h[0] - 1.4, h[1] - ry * 0.55), ell(rx * 0.86, ry * 0.42), "$slate.dark", rot=-16),
                P_("mouth", (h[0] + 2.2, h[1] + 2.6), ell(2.4, 1.5), "$ink", rot=-8),
                P_("drip", (h[0] + 4.4, h[1] + 3.8), circ(0.7), "$bile")]
    if kind == "box":       # the survey's squared-off helmet
        return [P_("head", h, rect(rx * 2, ry * 2, 3.2), C["head_fill"], rot=tilt + 4, stroke=thin),
                P_("visor", (h[0] + 1.4, h[1] + 1.4), rect(C["visor_w"], C["visor_h"], 1.0), "$ink", rot=P["visor_turn"])]
    if kind == "hood":      # a peaked hood-helmet
        return [P_("head", h, poly([(-4.6, 3.2), (-5.0, -2.0), (-2.6, -6.0), (1.6, -7.0), (5.0, -3.2), (5.2, 3.2)]), C["head_fill"], rot=tilt + 6, stroke=thin),
                P_("visor", (h[0] + 1.4, h[1] + 1.0), rect(C["visor_w"], C["visor_h"], 1.3), "$ink", rot=P["visor_turn"])]
    if kind == "brim":      # the egg helmet under a wide flat brim
        return [P_("head", h, ell(rx, ry), C["head_fill"], rot=tilt, stroke=thin), visor,
                P_("brim", (h[0] + 0.4, h[1] - 2.4), ell(rx + 3.6, 1.7), "$husk", rot=-8, stroke=hair)]
    if kind == "lamp":      # a caving helmet: a dome, a lamp and a visor slit — and nothing joining them
        # Three marks, no fourth. There was a mount bridging the lamp down to the
        # visor, and a bar running down the centre of a helmet between the eyes is
        # a Corinthian nose guard before it is a lamp bracket — one vertical line
        # in that one place carries a whole other helmet with it. The lamp sits
        # against the rim on its own instead, which is also the truth of the
        # object: it is clipped on, not built in.
        #
        # For whoever moves these next: at a big zoom a round light over a dark
        # bar reads as an eye over a mouth. That reading was chased out once — the
        # visor redrawn as a wrapped pane and the lamp as a lit strip along its
        # rim, which does not do it — and this arrangement was picked over it
        # anyway. So it is a choice, not an oversight; if you set out to fix it,
        # change the *shapes* of the two marks rather than where they sit,
        # because every placement of a disc and a bar on an oval is a face. What
        # is not on the table is a third mark between them.
        #
        # The dome is a profile rather than an ellipse, and in the same number of
        # parts: an ellipse has no front and no back, so three of the eight were
        # wearing the same egg and telling them apart came down to what was stuck
        # on it. This one cuts in over the visor at the front and lets out into a
        # nape at the back, in units of the head radius so it scales with
        # `head_r`. The visor is a slit rather than the roster's full band: the
        # one who went down twenty-nine levels wanted the light, not the view.
        return [P_("head", h, poly(dome_points(rx, ry)), C["head_fill"], rot=tilt, stroke=thin),
                P_("lamp", (h[0] + 2.1, h[1] - 2.5), circ(1.15), C["lamp_fill"], stroke=hair),
                P_("visor", (h[0] + 1.3, h[1] + 0.9), rect(C["visor_w"], C["visor_h"], 0.9), "$ink", rot=P["visor_turn"])]
    if kind == "mask":      # goggles and a filter can — the most sealed head
        return [P_("head", h, ell(rx, ry), C["head_fill"], rot=tilt, stroke=thin),
                P_("goggle", (h[0] + 2.4, h[1] + 0.6), circ(2.6), "$slate.dark", stroke=hair),
                P_("goggle_glass", (h[0] + 2.4, h[1] + 0.6), circ(1.7), "$ink"),
                P_("filter", (h[0] + 3.4, h[1] + 4.0), circ(1.6), "$slate", stroke=hair)]
    raise KeyError(kind)

# ============================================================== 4. one body, from its row
def build(name, row):
    S = dict(BASE_SKELETON); S.update(row.get("skeleton", {}))
    P = dict(BASE_POSE); P.update(row.get("pose", {}))
    C = dict(BASE); C.update({k: v for k, v in row.items() if k not in ("skeleton", "pose", "extras", "walk", "idle", "description")})
    W = dict(BASE["walk"]); W.update(row.get("walk", {}))
    I = dict(BASE["idle"]); I.update(row.get("idle", {}))
    if C["sex"] == "f":
        S["shoulder_near"] = (S["shoulder_near"][0] + 0.6, S["shoulder_near"][1]); S["shoulder_far"] = (S["shoulder_far"][0] - 0.6, S["shoulder_far"][1])
        for k in ("foot_w", "foot_h", "foot_far_w", "foot_far_h"): C[k] = round(C[k] * 0.88, 2)
    else:
        S["shoulder_near"] = (S["shoulder_near"][0] - 0.4, S["shoulder_near"][1]); S["shoulder_far"] = (S["shoulder_far"][0] + 0.4, S["shoulder_far"][1])
    sn, sf = S["shoulder_near"], S["shoulder_far"]
    sx = C["cloak_sx"]
    T = C["tint"]
    for key, delta in (("coat_fill", 0), ("cape_fill", 1), ("head_fill", 2), ("arm_fill", 0)):
        if C[key] is None: C[key] = shade(T, delta)
    C["arm_far_fill"] = shade(T, -1); C["leg_fill"] = shade(T, 0); C["leg_far_fill"] = shade(T, -1)

    heads = head_parts(C["head"], S, C, P)
    def figure(x, y):  # the waist drawn in on a woman, the chest let out on a man
        # `wrap` states its own waist and hip in §1a, so the shared narrowing
        # would take them in a second time.
        if C["coat"] == "wrap": return x
        if C["sex"] == "f" and 2.5 < y < 8.5: return x * 0.92
        if C["sex"] == "m" and y < 2.0: return x * 1.04
        return x
    cloak = {"id": "cloak", "at": [0, 0], "rot": P["coat_lean"] - 2, "shape": poly([(figure(x, y) * sx, y) for x, y in coat_points(C["coat"], sn, sf, C["hem"])]), "fill": C["coat_fill"], "stroke": thin}
    cape = {"id": "cape", "at": [0, 0], "shape": poly(cape_points(sn, sf, sx)), "fill": C["cape_fill"]} if C["cape"] else None
    organ = {"id": "organ", "at": [1.0, 1.0], "use": "ss.lib.organ", "variant": "dead", "scale": 0.72} if C["organ"] else None
    foot = P_("foot", S["foot_near"], rect(C["foot_w"], C["foot_h"], 1.2), "$slate.dark")
    foot_far = P_("foot_far", S["foot_far"], rect(C["foot_far_w"], C["foot_far_h"], 1.1), "$slate")
    legs = []
    if C["legs"]:
        for pid, hip, ft, w, fill in (("leg_far", S["hip_far"], S["foot_far"], 2.6, C["leg_far_fill"]), ("leg", S["hip_near"], S["foot_near"], 3.0, C["leg_fill"])):
            L = math.hypot(ft[0] - hip[0], ft[1] - hip[1]); ang = -math.degrees(math.atan2(ft[0] - hip[0], ft[1] - hip[1]))
            legs.append(P_(pid, hang(hip, L, ang), rect(w, L + 1.0, 1.2), fill, rot=ang, stroke=thin if pid == "leg" else None))
    a_c = hang(sn, C["arm_len"], P["arm_hang"]); h_c = below(sn, C["arm_len"] + 0.9, P["arm_hang"])
    arm = P_("arm", a_c, rect(C["arm_w"], C["arm_len"], 1.4), C["arm_fill"], rot=P["arm_hang"], stroke=thin)
    hand = P_("hand", h_c, ell(*C["hand_r"]), C["hand_fill"], stroke=thin)
    af_c = hang(sf, C["arm_far_len"], P["arm_far_hang"]); hf_c = below(sf, C["arm_far_len"] + 0.9, P["arm_far_hang"])
    arm_far = P_("arm_far", af_c, rect(C["arm_far_w"], C["arm_far_len"], 1.2), C["arm_far_fill"], rot=P["arm_far_hang"])
    hand_far = P_("hand_far", hf_c, ell(*C["hand_far_r"]), C["hand_far_fill"])
    pack = P_("pack", S["pack"], rect(C["pack_w"], C["pack_h"], 1.0), C["pack_fill"], stroke=hair) if C["pack"] else None
    feelers = []
    if C["feelers"]:
        # whips: long, thin, trailing back past the helmet — the lash is what these are for
        feelers = [{"id": "feeler_far", "at": [*S["feeler_far_root"]], "rot": -64, "scale": [0.5, 0.86], "use": "ss.lib.antenna", "variant": "dead"},
                   {"id": "feeler", "at": [*S["feeler_root"]], "rot": -58, "scale": [0.5, 0.95], "use": "ss.lib.antenna", "variant": "dead"}]

    ctx = {"S": S, "P": P, "C": C, "T": T, "sn": sn, "sf": sf, "hand": h_c, "hand_far": hf_c, "head": S["head"], "foot": S["foot_near"], "foot_far": S["foot_far"]}
    layers = {k: [] for k in ("behind", "feet_over", "over_coat", "over_cape", "in_hand", "over_head")}
    follow = {}
    for layer, part, fol in row.get("extras", lambda c: [])(ctx):
        layers[layer].append(part); follow[part["id"]] = fol

    # depth = draw order, far to near for a body facing front-right
    parts = feelers + ([pack] if pack else []) + layers["behind"] + [arm_far, hand_far] + legs + [foot_far, foot] + layers["feet_over"] \
        + [cloak] + layers["over_coat"] + ([cape] if cape else []) + ([organ] if organ else []) + layers["over_cape"] + [arm, hand] + layers["in_hand"] + heads + layers["over_head"]
    ids = [p["id"] for p in parts]
    assert len(ids) == len(set(ids)), ids

    neck = ((sn[0] + sf[0]) / 2, (sn[1] + sf[1]) / 2)
    pelvis = ((S["hip_near"][0] + S["hip_far"][0]) / 2, (S["hip_near"][1] + S["hip_far"][1]) / 2)
    joints = {"head": S["head"], "neck": neck, "pelvis": pelvis, "shoulder_near": sn, "shoulder_far": sf, "hand_near": h_c, "hand_far": hf_c,
              "hip_near": S["hip_near"], "hip_far": S["hip_far"], "foot_near": S["foot_near"], "foot_far": S["foot_far"]}
    bones = [["shoulder_near", "shoulder_far"], ["neck", "head"], ["neck", "pelvis"], ["hip_near", "hip_far"], ["shoulder_near", "hand_near"], ["shoulder_far", "hand_far"], ["hip_near", "foot_near"], ["hip_far", "foot_far"]]
    if pack:
        joints["pack"] = S["pack"]; bones.append(["neck", "pack"])
        if C["feelers"]:
            joints["feeler_root"] = S["feeler_root"]; joints["feeler_far_root"] = S["feeler_far_root"]
            bones += [["pack", "feeler_root"], ["pack", "feeler_far_root"]]
    skeleton = {"joints": {k: [r2(v[0]), r2(v[1])] for k, v in joints.items()}, "bones": bones}

    head_group = [p["id"] for p in heads] + (["pack"] if pack else []) + [p["id"] for p in feelers]
    body_group = ["cloak"] + (["organ"] if organ else []) + (["cape"] if cape else [])
    for pid, fol in follow.items():
        if fol == "head": head_group.append(pid)
        elif fol == "body": body_group.append(pid)
    arm_pieces = [("arm", a_c), ("hand", h_c)] + [(p["id"], tuple(p["at"])) for L in layers.values() for p in L if follow[p["id"]] in ("arm", "flutter_arm")]
    arm_far_pieces = [("arm_far", af_c), ("hand_far", hf_c)] + [(p["id"], tuple(p["at"])) for L in layers.values() for p in L if follow[p["id"]] == "arm_far"]
    foot_followers = {"foot": [p["id"] for L in layers.values() for p in L if follow[p["id"]] == "foot"],
                      "foot_far": [p["id"] for L in layers.values() for p in L if follow[p["id"]] == "foot_far"]}

    def gait(w):
        tr = []
        up = [-w["bob"] * (0.5 - 0.5 * math.cos(4 * math.pi * t)) for t in TS]
        for pid in head_group: tr.append(track(pid, "y", up))
        for pid in body_group: tr.append(track(pid, "y", [u * 0.6 for u in up]))
        if C["legs"]:
            for leg, hip, ft, phase in (("leg", S["hip_near"], "foot", 0.0), ("leg_far", S["hip_far"], "foot_far", 0.5)):
                lc = next(p for p in legs if p["id"] == leg); lcen = tuple(lc["at"]); fcen = S["foot_near"] if ft == "foot" else S["foot_far"]
                cols = {leg: ([], [], []), ft: ([], [], [])}
                for t in TS:
                    th = -w["leg_swing"] * math.sin(2 * math.pi * (t + phase))
                    for pid, cen in ((leg, lcen), (ft, fcen)):
                        dx, dy, rot = swing(hip, cen, th)
                        cols[pid][0].append(dx); cols[pid][1].append(dy); cols[pid][2].append(rot if pid == leg else 0.0)
                for pid, (xs, ys, rs) in cols.items():
                    tr.extend([track(pid, "x", xs), track(pid, "y", ys)] + ([track(pid, "rot", rs)] if pid == leg else []))
                    for f in foot_followers.get(pid, []): tr.extend([track(f, "x", xs), track(f, "y", ys)])
        else:
            def foot_tracks(pid, phase):
                xs = [w["stride"] * math.sin(2 * math.pi * (t + phase)) for t in TS]
                ys = [-w["lift"] * max(0.0, math.cos(2 * math.pi * (t + phase))) ** 1.5 for t in TS]
                for p in [pid] + foot_followers[pid]:
                    tr.append(track(p, "x", xs)); tr.append(track(p, "y", ys))
            foot_tracks("foot", 0.0); foot_tracks("foot_far", 0.5)
        tr.append(track("cloak", "rot", [w["sway"] * math.sin(2 * math.pi * t) + w["lurch"] * math.sin(4 * math.pi * t + 1.2) for t in TS]))
        def arm_tracks(joint, pieces, sign):
            cols = {pid: ([], [], []) for pid, _ in pieces}
            for t, u in zip(TS, up):
                th = sign * w["arm_swing"] * math.sin(2 * math.pi * t)
                for pid, centre in pieces:
                    dx, dy, rot = swing(joint, centre, th)
                    cols[pid][0].append(dx); cols[pid][1].append(dy + u * 0.6); cols[pid][2].append(rot)
            for pid, (xs, ys, rs) in cols.items():
                tr.extend([track(pid, "x", xs), track(pid, "y", ys), track(pid, "rot", rs)])
        arm_tracks(sn, arm_pieces, +1); arm_tracks(sf, arm_far_pieces, -1)
        tr.append(track("head", "rot", [w["head_nod"] * math.sin(4 * math.pi * t + 0.8) for t in TS]))
        for pid, fol in follow.items():
            if fol == "scarf": tr.append(track(pid, "rot", [-9 * (0.5 - 0.5 * math.cos(4 * math.pi * t)) for t in TS]))
        if C["feelers"] and I["feelers"] != "still":
            tr.append(track("feeler", "rot", [-8 * math.sin(4 * math.pi * t - 0.9) for t in TS]))
            tr.append(track("feeler_far", "rot", [7 * math.sin(4 * math.pi * t - 0.9) for t in TS]))
        return tr

    def walk():
        return {"description": row.get("walk_desc", "contact and passing, twice: the head carries the bob, the feet swing under the hem and lift on the swing, the hem sways, the arms turn about their shoulders against the foot on their side"),
                "duration": W["duration"], "tracks": gait(W)}
    def idle():
        if I["march"]:
            m = dict(W); m.update({"stride": 1.1, "lift": 0.8, "bob": 0.6, "sway": 1.2, "arm_swing": 6, "lurch": 0, "leg_swing": 8})
            return {"description": "never still: a march on the spot — do not stop (K033)", "duration": I["duration"], "tracks": gait(m)}
        tr = [key3(p, "y", 0, -1.0) for p in head_group]
        tr += [key3(p, "y", 0, -0.5) for p in body_group + [pid for pid, _ in arm_pieces] + [pid for pid, _ in arm_far_pieces]]
        if C["feelers"] and I["feelers"] == "sweep":
            tr.append({"part": "feeler", "prop": "rot", "keys": [[0, 0], [0.35, 12], [0.7, -8], [1, 0]]})
            tr.append({"part": "feeler_far", "prop": "rot", "keys": [[0, 0], [0.4, -10], [0.75, 7], [1, 0]]})
        for pid, fol in follow.items():
            if fol == "flutter_arm": tr.append({"part": pid, "prop": "rot", "keys": [[0, 0], [0.3, 6], [0.7, -6], [1, 0]]})
            if fol == "scarf": tr.append({"part": pid, "prop": "rot", "keys": [[0, 0], [0.5, -5], [1, 0]]})
        return {"description": row.get("idle_desc", "the body breathes under the coat"), "duration": I["duration"], "tracks": tr}

    # The row key is the document's id, and an id is a handle the consumer pins:
    # `feelers/src/pg/textures.ts` throws at build time on an id the pinned bundle
    # has not got, so a walker who is renamed keeps the id she was published under
    # and says her name in `display`. Eden answering to `ss.char.star` in the game
    # is the same bargain one repo over.
    return {"id": f"ss.char.{name}", "name": row.get("display", name.capitalize()), "description": row["description"], "tags": ["char"], "size": [32, 32], "meta": {"radius": 11},
            "parts": parts, "skeleton": skeleton, "animations": {"idle": idle(), "walk": walk()}}

# ============================================================== 5. the eight
SHARED = " Drawn from one skeleton and one facing (docs/character-rig-guide.md) by scripts/walker.py, with its own primary shape; the dead organ is worn as the clasp of the coat, in the same place on everyone still carrying one; flat token fills; radius 11."

def wrap(x0, y0, x1, y1, sag, n=17, skew=0.5):
    """One turn of a cord across the front of a body. It enters and leaves at the
    outline and hangs between, and the hang is a *curve*: `stem` joins points
    with straight lines, so an arc drawn from four or five of them comes out as
    a corner, and three corners down a torso is a ribcage. Seventeen, because the
    cosine below crowds them at the two ends and leaves the middle to fend for
    itself. It
    sags rather than arches because the camera looks down on her — the front of
    the cord is nearer than its sides, and nearer is lower on the screen.

    `skew` is where along the span that nearest point falls. At 0.5 the hang is
    symmetric, which is the cord on a body facing square on; she is not, she is
    three-quarters onto her front-right, so the surface nearest the camera is
    past the middle of the span towards the front and the sag goes with it.
    Symmetric arcs down a three-quarter body are the tell that they were drawn
    on the picture rather than round the thing in it.

    The ends of `y0`..`y1` are not level either. A cord wound round a body is a
    helix: it crosses the front, goes round the back, and comes back to the
    front one pitch lower, so every crossing you can see runs *downhill*, by
    about half the gap to the next turn — the back of the turn spends the other
    half. Level ends are three separate hoops, and hoops at even spacing are
    stripes.

    And the run across is a **cosine, not a straight line**, which is the single
    thing that decides whether a band looks wound or printed. Take the helix
    round a cylinder of radius r, `x = r sin t`, `y = pitch * t`, and look at it
    from the front: at the two edges, where `t` is a quarter turn either side,
    `dx/dt` is zero and `dy/dt` is not. **The projected cord arrives at the
    outline going straight down.** It does not run into the edge at a slant and
    stop — it turns, and the last of it you see is vertical, which is the whole
    picture of something going round the back. Spread `x` evenly instead and
    every crossing meets the outline at a slant: a chevron laid on the front,
    three of them a pattern printed on the surface. Everything else here — the
    sag, the pinch, the descent — was already right while this was linear, and
    it still read flat, because this is the one that says *round*.

    (The sag is the same cylinder's other half: depth is `r cos t`, which is the
    `sin(pi*t)` below, so the hang is not a fudge — it is how far the front of
    the cord is towards the camera, dropped on screen because the camera is
    above. The two come from one model and that is why they agree.)"""
    return [(x0 + (x1 - x0) * (1 - math.cos(math.pi * t)) / 2,
             y0 + (y1 - y0) * t + sag * math.sin(math.pi * (0.5 * t / skew if t < skew else 0.5 + 0.5 * (t - skew) / (1 - skew))))
            for t in (i / (n - 1) for i in range(n))]

# ONE cord wound round the body of §1a — not three, and the difference is the
# whole of whether it looks wound or painted on. It was three: three arcs at the
# chest, the waist and the hip, each entering and leaving level, each sagging by
# the same symmetric amount, evenly spaced down the torso. Three hoops at even
# spacing are a stripe pattern, and the eye reads a stripe pattern as printed on
# the surface — the cord had never gone anywhere, so nothing said it had gone
# *round*.
#
# What makes it one cord is that the three crossings agree about a helix they are
# all part of. Three things carry that, and none of them is drawing more:
#
#   the descent — one turn drops `M_PITCH` down the body, so the crossing you can
#     see drops half of it and the hidden half behind her spends the rest. Read
#     down the near edge and the cord leaves the front at one height and comes
#     back at the next one, which is the only evidence there is that the back of
#     the turn exists at all.
#   the pinch — `bulge`, taken far enough to matter. The cord is seen at full
#     width where it faces you and edge-on where it turns past the outline, so it
#     must *end* at a fraction of its middle. It used to end at 1.3 of a 1.7
#     middle, which is a blunt stub against the outline: cut off, not gone round.
#   the skew — the sag hangs past the middle of the span, because she is three-
#     quarters onto her front-right and that is where the surface nearest the
#     camera is. Symmetric arcs are the tell that the arc was fitted to the
#     silhouette rather than laid on the body inside it.
#
# The top turn reaches out onto the near sleeve. That is where its thorn goes,
# and it makes the turn Zyra's spiked arm-vine as well; it can stay on `body`
# because it sits a unit below the shoulder joint, where the arm's swing
# displaces it by a fifth of a pixel.
M_PITCH = 3.6            # one full turn of the cord, measured down the body
_HALF = M_PITCH / 2      # ...so this much of it is the crossing you can see
BAND_A = wrap(M_L(M_SHOULDER) - 1.7, M_CHEST_Y - 2.0, M_R(M_CHEST) + 0.15, M_CHEST_Y - 2.0 + _HALF, 2.2, skew=0.6)
# The waist is the narrowest and shallowest part of her, so this turn sags least:
# the sag is the cord's hang round the *depth* of the body, and the depth follows
# the width. The chest and the hip are both deeper than the waist and both hang
# further, which is the third thing keeping the three from reading as parallel.
BAND_B = wrap(M_L(M_WAIST) - 0.35, M_WAIST_Y - 1.65, M_R(M_WAIST) + 0.35, M_WAIST_Y - 1.65 + _HALF, 1.5, skew=0.6)
# The lowest turn is the one that reads as a garment. A cord wound many times in
# one place is a band, so this one is swept three times the width of the others
# and laid across the hip, where it covers the edge the body ends on: the join
# between torso and leg is underneath it, which is the whole point — a seam that
# happens inside the plant is not a seam anybody sees. It used to carry on off
# the far hip as a free tail; the free end is at her ankle now (`RUNNER` below),
# so this turn pinches out at the outline like the two above it. There are no
# leaves anywhere on her — the arsenal's plants have none
# on purpose (`ss.proj.vine`: a leafy stem is a picture of a plant, not of this
# weapon), and at four pixels a leaf is a pauldron at the shoulder and a luggage
# tag at the hip. Both were drawn.
#
# It is on the same helix but it does not drop the full half-pitch: it is many
# turns lying side by side in one place, so what you see is the face of a band
# and a band's face tilts by a third of what one cord's crossing would. Its entry
# stays exactly where it was — that end is what covers the join — and the tilt is
# spent on the exit. And it hangs deepest of the three: the hip is the deepest
# part of her.
BAND_C = wrap(M_BK(M_HIP_B) + 0.15, M_HIP_Y + 0.7, M_FR(M_HIP_F) - 0.15, M_HIP_Y + 0.7 + M_PITCH / 3, 1.6, skew=0.58)

def spline(ctrl, n=21):
    """A Catmull-Rom curve through `ctrl`, sampled at `n` points — for a cord
    that lies where it fell rather than round anything, so `wrap` has no say."""
    ctrl = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for i in range(n):
        u = i / (n - 1) * (len(ctrl) - 3); k = min(int(u), len(ctrl) - 4); t = u - k
        p0, p1, p2, p3 = ctrl[k:k + 4]
        out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    return out
# The free end of the cord, and the one piece of her that reaches past her own
# outline. The weapon *holds* what it catches, and `ss.proj.vine-snare` is what
# a held body wears: a turn round the feet and the tail still trailing off where
# the rest of the plant is. She is the body it never let go of (M042), so she
# wears that too — one turn over the near ankle and the rest along the ground
# *behind* her, towards the burrow she walked out of: the wall's pull, and her
# walking against it (M035). It is also the silhouette she was missing. Seven
# coats are blobs with one thing sticking out of each; a figure with nothing
# off it is a stick among them, and this is her one thing.
#
# It was tried off the back of the hip first, as a train, and read as a tail —
# a line out of the rump that lifts at the end is an animal's, whatever it is
# painted. At the ankle it cannot be one: it starts at a foot, lies flat on the
# floor, and carries the snare's barb, which no tail does. It rides the near
# foot (`follow` "foot"), so in the walk the whole length slides with the step:
# that is what dragging something looks like.
RUNNER_ROOT = (-1.2, 11.9)
RUNNER = spline([(0.2, 11.2), RUNNER_ROOT, (-3.2, 12.8), (-5.4, 14.1), (-8.6, 14.3), (-11.8, 13.7), (-14.6, 14.1)], 29)
def rooted(part, root):
    """Re-express a polygon drawn in canvas coordinates about `root`, so a part
    built by `stem` can hang from a joint and be moved by one."""
    for q in part["shape"]["points"]:
        q[0] = r2(q[0] - root[0]); q[1] = r2(q[1] - root[1])
    part["at"] = [r2(root[0]), r2(root[1])]
    return part
# The far side of her turns away from the light and until recently did not know
# it: one flat fill edge to edge, which gives the turns a board to lie on. This
# is the step down the suit's ramp that the far arm and far leg already take, run
# down the body's far edge and pinched out top and bottom.
TORSO_SHADE = [(M_R(M_SHOULDER) - 1.0, M_SHOULDER_Y - 0.3), (M_R(M_CHEST) - 0.4, M_CHEST_Y),
               (M_R(M_WAIST) - 0.3, M_WAIST_Y - 0.2), (M_FR(M_HIP_F) - 0.3, M_HIP_Y),
               (M_FR(M_THIGH_F) - 0.5, M_HEM_Y - 0.6)]

CHARACTERS = {
    "arin": {
        "sex": "f", "tint": ("frost", 0), "pack": True, "pack_w": 5.0, "pack_h": 5.2, "feelers": True,
        "extras": lambda c: [
            ("behind", P_("rack", (c["S"]["pack"][0] - 3.3, c["S"]["pack"][1] + 0.8), rect(2.2, 4.0), "$steel.light", stroke=hair), "head"),
        ],
        "idle_desc": "the body breathes under the coat; the dead feelers keep sweeping for a signal that never comes",
        "description": "A circle. The first expedition, on the day the last cartridge went in (A047): the bell coat, the egg helmet, and the prototype emitter — the biggest box any of the eight carries, its cartridge rack beside it, and the two dead feelers rising from its lid, swept back past the helmet as the crown of the silhouette. Arin is the only one of the eight with feelers: the antennae were the prototype's design (A004), and every mark after it vents through a tube — and they are the lash. Grown long and thin into two whips that trail back past the helmet and crack forward, the weapon is the feelers themselves, which is what the game is named for. The hands have gone dark and hard — the saw does not mark them (A052), the Molt's slate, the first of the body to lose its blood." + SHARED,
    },
    "sol": {
        "sex": "f", "tint": ("lichen", 0), "coat": "jacket_belly", "cloak_sx": 0.9, "legs": True, "cape": False,
        "head": "bare", "head_r": (4.6, 5.0),
        "skeleton": {"hip_near": (-2.2, 6.4), "hip_far": (3.2, 5.8), "foot_near": (-1.8, 13.4), "foot_far": (4.0, 12.8), "head": (2.6, -8.4)},
        "pose": {"coat_lean": 10, "arm_hang": 14, "arm_far_hang": -16}, "arm_w": 2.6, "arm_far_w": 2.2, "hand_r": (1.5, 1.7), "foot_w": 4.2, "foot_h": 2.2, "foot_far_w": 3.8, "foot_far_h": 2.0,
        "walk": {"duration": 0.44, "bob": 1.8, "arm_swing": 22, "leg_swing": 26, "sway": 1.5}, "idle": {"duration": 1.0},
        "extras": lambda c: [
            ("behind", P_("scarf", (-5.0, -4.0), poly([(0.4, -1.2), (-4.2, -3.0), (-8.8, -2.6), (-4.6, -0.2), (-0.2, 1.4)]), "$husk", rot=8, stroke=hair), "scarf"),
            ("in_hand", P_("tail", (c["head"][0] - 6.0, c["head"][1] - 1.6), poly([(2.0, -1.2), (0.4, -2.6), (-5.4, -3.0), (-7.2, -1.2), (-3.0, 0.4), (1.6, 1.4)]), "$slate.dark", rot=-10, stroke=hair), "scarf"),
            ("over_coat", P_("helmet_hung", (-5.2, 5.0), ell(2.5, 2.2), "$frost.light2", stroke=hair), "body"),
            ("over_coat", P_("helmet_hung_visor", (-4.4, 5.3), rect(2.2, 0.9, 0.4), "$ink"), "body"),
            ("over_coat", P_("belly_sheen", (6.4, 5.2), ell(2.0, 1.4), shade(c["T"], 1), rot=-20), "body"),
            ("over_coat", P_("pouch", (-1.4, 5.6), rect(3.0, 3.0, 0.8), "$timber", stroke=hair), "body"),
            ("over_coat", P_("cap", (-1.0, 3.5), circ(1.3), "$pink"), "body"),
        ],
        "walk_desc": "a run: long legs swinging from the hips, the body pitched forward, the arms high, the scarf lifting on every stride",
        "idle_desc": "breathing hard, the scarf settling",
        "description": "A triangle, leaning. The scout sent out alone: a short jacket over long legs, the body pitched ten degrees into the run, the arms swinging high, a scarf flying back from the neck. The one bare head of the eight — the helmet came off on day two (S002) and hangs from the hip now, found and not put on (S009). The issued emitter was dead on day one and was never carried (S004); a pouch of fungi with a pink cap showing is what gets Sol past the swarm (S003). Faster than they are (S009), and short of health for it." + SHARED,
    },
    "haram": {
        "sex": "m", "tint": ("ochre", 0), "coat": "slab", "head": "box", "head_r": (5.4, 5.0), "visor_w": 7.4, "cape": False,
        "skeleton": {"shoulder_near": (-6.2, -3.4), "shoulder_far": (7.0, -4.6), "head": (1.6, -8.6), "foot_near": (-2.6, 13.2), "foot_far": (4.4, 12.6)},
        "pose": {"coat_lean": 3, "arm_hang": 4, "arm_far_hang": -6}, "arm_w": 3.6, "arm_far_w": 3.2, "foot_w": 5.4, "foot_h": 2.8, "foot_far_w": 4.8, "foot_far_h": 2.6,
        "pack": True, "pack_w": 4.4, "pack_h": 4.6, "skeleton_pack": None,
        "walk": {"duration": 0.7, "bob": 0.9, "lurch": 2.4, "arm_swing": 9, "sway": 2.0},
        "extras": lambda c: [
            ("behind", P_("stake_a", (-9.4, -9.0), rect(1.2, 9.4, 0.3), "$timber", rot=-26), "head"),
            ("behind", P_("stake_b", (-8.0, -9.8), rect(1.2, 8.8, 0.3), "$timber.dark", rot=-16), "head"),
            ("over_coat", P_("pauldron", (c["sn"][0] + 0.8, c["sn"][1] + 0.2), ell(3.8, 2.3), "$husk", rot=-10, stroke=hair), "body"),
            ("over_cape", P_("pod", (c["sf"][0] + 0.6, c["sf"][1] - 1.2), circ(2.0), "$pink", stroke=hair), "body"),
        ],
        "walk_desc": "a heavy lurching walk: low bob, the slab of a body rocking on each step — the Husk's shamble at low amplitude",
        "description": "A square. The survey: a slab of a body with squared shoulders, the widest of the eight, under a box of a helmet. The husk shell scraped into the mark II emitter (H027) is coming through as bone: one bleached pauldron over the near shoulder. On the back, the benchmark stakes (H001); on the far shoulder, the one pink spore pod the lure grows from. Four kilos up on the same ration, pulse thirty-eight (H043): armour, a lurch in the walk, and slower for it." + SHARED,
    },
    # The id stays `mir`: the game pins this bundle and throws at build time on an
    # id it has not got, so the name moves in `display` and the handle does not.
    "mir": {
        "display": "Mina",
        # The player's colour, which she was the one walker not wearing. In
        # `timber` under a `$husk` helmet she was a pale warm body with a bone
        # head, and that is what the Husk, the Zombie and the Skeleton are — in a
        # crowd she read as one of them. `celadon` is `$spore` taken halfway to
        # `$steel`, the recipe `lichen`, `ochre`, `sage` and `heather` were made
        # by; the vine's own green is `sage` and Eden wears it, so she has the
        # step from it towards the cold, the hue the eight had left open between
        # Arin's sky and Eden's sage. A level up, because a figure has less area
        # than a coat to be found by and has to make it up in value.
        "sex": "f", "tint": ("celadon", 1), "coat": "wrap", "cloak_sx": 1.0,
        # No coat, so no mantle either; no clasp, because M042 has her going back
        # down with the piece of wall *in place of the emitter* and the dead organ
        # the other seven wear stayed where it burned out beside the queen (M031).
        # She is the one bare chest of the eight and the one with legs.
        "cape": False, "organ": False, "legs": True,
        # The skeleton is §1a's canon, not a set of nudged points. The head sits
        # a third of the body's height at the top of it and 0.6 ahead of the
        # shoulder midpoint — under the guide's 1–3, because that range assumes
        # the default posture where the helmet comes down over the shoulders, and
        # that posture on a body this size is a stoop with no neck and the chin on
        # the chest. The two contact points are 3.2 apart, near enough one line:
        # a runway walk puts one foot almost in front of the other, and at this
        # size that is the cheapest thing separating a model's walk from a march.
        "skeleton": {"head": (0.9, M_TOP + M_HEAD_R[1]), "head_tilt": -6,
                     "shoulder_near": (M_L(M_SHOULDER) - 1.2, M_SHOULDER_Y), "shoulder_far": (M_R(M_SHOULDER) + 1.2, M_SHOULDER_Y - 1.0),
                     "hip_near": (M_BK(M_HIP_B) + 2.0, M_HIP_Y + 0.2), "hip_far": (M_FR(M_HIP_F) - 0.6, M_HIP_Y - 0.2),
                     "foot_near": (-1.1, M_SOLE - 1.2), "foot_far": (2.1, M_SOLE - 1.8)},
        # The `lamp` helmet: a dome cut to a profile, a visor slit, and the one
        # light the eight carry clipped against the rim above it — with nothing
        # joining the two, because a bar down the middle between them is a
        # Corinthian nose guard before it is a bracket. The shell is `$silent`,
        # the brightest thing on her and the thing an eye finds her by, and the
        # lamp is *on*: in the shell's own white it was an eyeball, lit it is a
        # light.
        "head": "lamp", "head_r": M_HEAD_R, "visor_w": 4.2, "visor_h": 1.7, "lamp_fill": "$gold.light", "head_fill": "$silent",
        "pose": {"coat_lean": 0, "arm_hang": 4, "arm_far_hang": -2, "visor_turn": -6},
        # The slimmest limbs in the set, and bare: a glove on a body wrapped in
        # plant is a costume again, so the hands come off `$slate.dark` onto
        # `$skin`. The waist is inside the near sleeve, so daylight opens
        # between arm and body — not a gap to close, the thing that says the
        # waist is narrower than the reach.
        "arm_len": 7.0, "arm_w": 1.8, "arm_far_len": 6.3, "arm_far_w": 1.5,
        "hand_r": (1.15, 1.3), "hand_far_r": (1.0, 1.15), "hand_fill": "$skin", "hand_far_fill": "$skin.dark",
        # Carriage, and it is made by taking motion away, not adding it: the
        # longest stride and slowest beat of the eight, the smallest bob, and the
        # head carried rather than nodded (`head_nod` 0.5 against the rig's 2.5).
        # The arms are the exception and were got wrong once — taken down to
        # almost nothing in the name of stillness, where every runway guide says
        # arms held stiff against the sides read as tension from the back of the
        # room and poise is a relaxed pendulum.
        "walk": {"duration": 0.78, "stride": 2.6, "lift": 0.7, "bob": 0.45, "sway": 2.0, "arm_swing": 10, "leg_swing": 25, "head_nod": 0.5},
        "idle": {"duration": 1.7},
        "extras": lambda c: [
            ("over_coat", P_("torso_shade", (0, 0), stem(TORSO_SHADE, 0.6, 0.6, bulge=1.9), shade(c["T"], -1)), "body"),
            # Each turn is `$moss` with a `$sage` lit edge: sage is the coil's own
            # colour on the weapon's slot (`ss.icon.vine`), which the card shows
            # beside her. The edge was `$moss.light2`, which is a grey, and the
            # plant sank into the body it was on.
            ("over_coat", P_("band_b", (0, 0), stem(BAND_B, 0.72, 0.60, bulge=1.6), "$moss"), "body"),
            ("over_coat", P_("band_b_lit", (0, 0), stem(BAND_B, 0.72, 0.60, rail=0.4, bulge=1.6), "$sage"), "body"),
            ("over_coat", P_("band_c", (0, 0), stem(BAND_C, 2.4, 2.4, bulge=0.5), "$moss"), "body"),
            # The band's own numbers, with a rail instead of a fill — so the
            # highlight stays on the band wherever it pinches, which is where the
            # old fixed offset came off it and hung in the air as a pale fan.
            ("over_coat", P_("band_c_lit", (0, 0), stem(BAND_C, 2.4, 2.4, rail=0.36, bulge=0.5), "$sage"), "body"),
            # The snare's tail (`RUNNER`), with the snare's barb on it.
            ("feet_over", rooted(P_("runner", (0, 0), stem(RUNNER, 1.7, 0.3), "$moss"), RUNNER_ROOT), "foot"),
            ("feet_over", rooted(P_("runner_lit", (0, 0), stem(RUNNER, 1.7, 0.3, rail=0.45), "$sage"), RUNNER_ROOT), "foot"),
            ("feet_over", P_("runner_thorn", (RUNNER[17][0], RUNNER[17][1] - 0.5), poly([(-0.8, 0.5), (0.8, 0.5), (0.1, -1.7)]), "$blood.dark", rot=-24), "foot"),
            # Palm-sized, which is the record's own word for it (M038) — the slab
            # it used to be was drawn before anybody read the page. It hangs at the
            # near hip with something chewing inside it (M042), and the turns are
            # what came out. `$rust.light`: in `$rust` it was a hole in her hip.
            ("over_cape", P_("wall", (M_L(M_WAIST) - 0.35, M_WAIST_Y + 2.2), poly([(-1.5, -1.4), (1.5, -1.6), (1.6, 1.5), (-1.4, 1.6)]), "$rust.light", rot=-12, stroke=hair), "body"),
            # The neck. Nothing else on the eight has one, and nothing else here
            # stands up straight either; the two are the same fact.
            ("in_hand", P_("neck", (0.0, M_SHOULDER_Y - 0.8), rect(2.4, 3.2, 0.7), shade(c["T"], -1)), "body"),
            # The top turn crosses the near sleeve, so it is drawn after it, and
            # both thorns are rooted in its two ends. They were planted on the
            # shoulder line first, where no cord runs, so they grew out of *her* —
            # a thorn out of a shoulder is a thing that has happened to the body,
            # and what is true here is that the plant is on it. `$blood.dark`, a
            # step up from the weapon's `.dark2` barbs: those sit on the floor
            # under a lit plant, these stand off her outline on the dark field,
            # and a step down they were not there at all.
            ("in_hand", P_("band_a", (0, 0), stem(BAND_A, 0.72, 0.59, bulge=1.6), "$moss"), "body"),
            ("in_hand", P_("band_a_lit", (0, 0), stem(BAND_A, 0.72, 0.59, rail=0.4, bulge=1.6), "$sage"), "body"),
            ("in_hand", P_("thorn", (M_L(M_SHOULDER) - 2.2, M_SHOULDER_Y - 0.3), poly([(-0.9, 1.0), (0.9, 0.8), (-0.1, -1.9)]), "$blood.dark", rot=-44), "body"),
            ("in_hand", P_("thorn_far", (M_R(M_CHEST) + 0.75, M_CHEST_Y - 0.8), poly([(-0.9, 0.9), (0.9, 0.7), (0.0, -1.8)]), "$blood.dark", rot=46), "body"),
        ],
        "walk_desc": "carriage, and a runway walk: the two contact points on one line so the legs angle in from the hips, the longest stride and slowest beat of the eight, legs swinging under the lowest turn, the smallest bob in the set, and the head carried rather than nodded, while the vine tied to the near ankle drags along the floor with each step. It is a walk made of what the body does not do — except the arms, which keep a relaxed pendulum, because stiff arms against the sides are tension and not poise. Twenty-nine levels taught her not to bounce what she carries (M035)",
        "idle_desc": "the slowest breath of the eight bar Eden's: the body rises under the turns and the vine on the floor does not move",
        "description": "A stem, and the one of the eight not wearing a coat. **The plant is on her instead of cloth**, which is a silhouette decision before it is a costume one: a coat leaves the shoulder and swings clear of the body, so its outline belongs to the coat and the body inside it could be anybody\'s, while a plant clings and the outline stays hers. So the torso is the body, and the body is written down — `scripts/walker.py` \u00a71a — 7.8 across the shoulders, 7.0 at the chest, 5.4 at the waist, 7.4 at the hip — and the hip **off centre**, 4.25 of it behind the body\'s line and 3.15 in front, because in a three-quarter view the widest part of a hip is behind and the front of a pelvis is near flat. Flared evenly it put a bulge on the front where there is nothing to make one. The front line now runs long and almost straight from chest to thigh and the whole of the flare is on the back, which is the S and the point of it, and it does **not** stop at the hip: a torso ending on a hem line with two bare legs starting under it is an upper half and a lower half, drawn separately and meeting in public. It runs on into the thigh, and the lowest turn is swept wide enough to lie across that edge, so the join happens *inside* the plant. What the eye gets is body, then a wrapped band where a skirt would be, then leg — and that band is the one thing on her that reads as clothing, which is what a cord wound many times in one place is. Out at the deltoid, in under it, in again to the waist, and out at the hip behind only: a torso that goes *out* below its own shoulder line is a loose top rather than a body, whatever is drawn over it, and this one used to. The waist ends up inside the near sleeve and a little daylight opens between arm and body, which is not a gap to close — it is the thing that says the waist is narrower than the reach. **Over it, one length of `ss.proj.vine` wound three times** — at chest, waist and hip, two crossings and the wide band, each dark with its own lit edge and the body showing in the gaps. The gaps are half the reading and the rest is that the three agree about a helix they are all part of, because they are drawn as one: a cord on a cylinder, `x = r sin t` and `y = pitch t`, seen from the front. So the run across is a **cosine**, which puts `dx/dt` at zero where the cord meets the outline — it arrives there going *straight down* and turns out of sight, instead of hitting the edge at a slant and stopping, which is a chevron laid on the front. Each crossing runs **downhill** by half the gap to the next turn, the hidden half behind her spending the rest; each **swells and pinches**, full width facing you and edge-on past the side, so it ends at a third of its middle rather than three quarters of it; and each **hangs** by that same cylinder's depth, `r cos t`, which is why the waist — the thinnest and shallowest part of her — sags least while the chest and the hip sag more, and why the hang falls past the middle of the span, she being three-quarters onto her front-right and that being where her surface comes nearest the camera. Each of those four was wrong once. The cosine was the last of them and the largest: with the other three right and the run still spread evenly, three turns read as printed on the surface. Behind them the far side of the torso is a step down the suit's ramp, the same step the far arm and far leg take, because one flat fill edge to edge gives the turns a board to lie on. The lowest turn pinches out at the outline like the two above it, and a `$blood.dark` thorn comes off each end of the top turn — **rooted in the cord, not in her**. A thorn out of a shoulder is something that has happened to the body; what is true here is that the plant is on it. The top turn reaches onto the near sleeve to carry one of them, which makes it Zyra\'s spiked arm-vine arrived at from the other end. There are no leaves anywhere: the arsenal\'s plants have none on purpose, and at four pixels a leaf is a pauldron at the shoulder and a luggage tag at the hip. **And she stands, and walks like it.** The rig\'s default puts the helmet down over the shoulder line, which on a body this size is a stoop with the chin on the chest; the head sits back over the shoulders with a neck under it — the only neck in the set, and most of the difference between a figure that stands and one that hunches — the smallest head of the eight on the longest legs, the visor slit raised so the gaze is level. The walk is the same argument in motion: two contact points on one line, the longest stride and slowest beat in the set, the smallest bob, the head all but stopped. Carriage is mostly what a body does *not* do. **What she took in place of the emitter is what grew.** The piece of burrow wall hangs at the near hip, palm-sized — the record\'s own word (M038) — still warm half a month on with something chewing inside it (M042), and the turns came out of it: the vines that come up out of the ground in a run come up out of what this one carries (M041). The weapon holds what it catches, and this is the body it never let go of. **And the cord is not finished with her.** Its free end is tied once over the near ankle and lies along the floor behind her — `ss.proj.vine-snare` is what a held body wears, a turn round the feet and the tail still trailing off where the rest of the plant is, barb and all — trailing back towards the burrow, which is the pull of the wall she walks against (M035). It rides the near foot, so in the walk the whole length slides with the step, which is what dragging something looks like. It is also the silhouette she lacked: seven coats with one thing off each, and a figure with nothing off it was a stick among them. Off the back of the hip it was a tail; at the ankle, flat on the floor with a barb on it, it is not. **She is also the one with no clasp and no mantle**: M042 has her going back down with the wall *in place of the emitter*, so the dead organ the other seven wear stayed where it burned out beside the queen (M031). The helmet is the `lamp` kind and the one head in the set that is not an egg with something stuck on it: a profile cut in at the front and let out into a nape at the back, a visor slit, and the one light the eight carry clipped against the rim above it with nothing joining the two — a bar down the middle is a Corinthian nose guard before it is a bracket (M005). **And she wears the player\'s colour.** In `timber` under a `$husk` helmet she was the one warm walker of the eight, and a pale warm body with a bone head is what the Husk, the Zombie and the Skeleton are: in a crowd she read as one of them. The suit is `celadon` now — `$spore` halfway to `$steel`, the recipe the other suits were made by, in the hue the eight had left open between Arin\'s sky and Eden\'s sage (the vine\'s own green is Eden\'s) — the helmet `$silent`, the brightest thing on her, and the lamp on it lit, `$gold.light`: in the shell\'s white it was an eyeball. The turns take their lit edge in `$sage`, the coil\'s colour on the weapon\'s slot beside her on the card. 26 parts, and 4.3 : 1 against `ss.env.ground` (3.2 in timber), 1.9 on `ss.env.pan` (1.4)." + SHARED,
    },
    "kano": {
        "sex": "m", "tint": ("silent", 0), "coat": "column", "cloak_sx": 1.0, "hem": 0.0, "head": "hood", "head_r": (4.8, 6.0), "visor_w": 5.8,
        "skeleton": {"head": (1.8, -7.3), "shoulder_near": (-4.2, -3.2), "shoulder_far": (5.0, -4.4), "foot_near": (-1.4, 14.0), "foot_far": (3.2, 13.4), "hip_near": (-1.6, 12.6), "hip_far": (3.0, 12.0)},
        "pose": {"coat_lean": 4, "arm_hang": 4, "arm_far_hang": -4}, "arm_far_len": 7.4, "foot_h": 2.4, "foot_far_h": 2.2,
        "walk": {"duration": 0.72, "stride": 2.2, "lift": 0.5, "bob": 0.5, "arm_swing": 7, "sway": 4.6}, "idle": {"duration": 1.6},
        "extras": lambda c: [
            ("behind", P_("staff", (c["hand_far"][0] + 2.2, c["hand_far"][1] - 7.4), rect(1.6, 20.0, 0.6), "$timber", rot=3, stroke=hair), "arm_far"),
            ("behind", P_("staff_cap", (c["hand_far"][0] + 2.7, c["hand_far"][1] - 17.4), circ(1.4), "$steel.light", stroke=hair), "arm_far"),
            ("over_head", P_("beard", (c["head"][0] + 2.4, c["head"][1] + 5.2), poly([(-2.6, -1.4), (2.6, -1.4), (1.4, 1.6), (0.2, 3.2), (-1.2, 1.6)]), "$steel", rot=-4, stroke=hair), "head"),
            ("feet_over", P_("gaiter", (c["foot"][0], c["foot"][1] - 0.9), rect(4.8, 1.0, 0.3), "$steel"), "foot"),
            ("feet_over", P_("gaiter_far", (c["foot_far"][0], c["foot_far"][1] - 0.8), rect(4.2, 0.9, 0.3), "$steel"), "foot_far"),
        ],
        "walk_desc": "a glide: the long coat carries the walk, the feet barely leave the ground under it, the hem sways wide and the staff is planted with the far hand — no bounce, no hurry",
        "idle_desc": "standing on the staff, the hood dipping with the breath",
        "description": "A column. The patrols, and the rules that came out of them: do not stop (K033). A narrow coat, long to the boots, under a peaked hood-helmet, and a staff in the far hand taller than the head — the twelfth emitter was dropped where it broke, as the rules say (K030, K033), so nothing rides on the back. Gaitered boots, and a walk that is the coat's: a slow glide with the staff planted, no bounce and no hurry — the one who does not stop does not rush either." + SHARED,
    },
    "eden": {
        "sex": "f", "tint": ("sage", 0), "coat": "round", "head": "brim", "head_r": (5.0, 5.4),
        "skeleton": {"head": (2.2, -7.2), "shoulder_near": (-5.2, -2.6), "shoulder_far": (6.0, -3.8)},
        "pack": True, "pack_w": 3.8, "pack_h": 4.0, "pose": {"coat_lean": 1, "arm_hang": 8, "arm_far_hang": -10},
        "walk": {"duration": 0.62, "bob": 1.0, "sway": 3.6, "arm_swing": 10}, "idle": {"duration": 1.7},
        "extras": lambda c: [
            ("in_hand", P_("lock", (c["head"][0] - 4.6, c["head"][1] + 3.6), ell(1.5, 3.6), "$husk.dark", rot=10, stroke=hair), "head"),
            ("in_hand", P_("lock_back", (c["head"][0] - 1.6, c["head"][1] + 4.4), ell(1.3, 3.0), "$husk.dark", rot=-6), "head"),
            ("over_coat", P_("jar", (5.6, 7.6), rect(3.0, 3.8, 0.9), "$silent", stroke=hair), "body"),
            ("over_coat", P_("jar_lid", (5.6, 5.5), rect(3.4, 1.2, 0.4), "$slate", stroke=hair), "body"),
        ],
        "walk_desc": "an unhurried walk, the hem swinging wide, the brim steady",
        "idle_desc": "the slowest breath of the eight: six years of standing still and watching",
        "description": "A mushroom. The long station: a round coat under the wide flat brim on the helmet, the shape of six years beside the fungi (E009) and of the Gland's dome to come. A fingertip of royal jelly in place of the last cartridge (E093), carried in the one specimen jar at the coat front — the collector's jar, the brightest thing on the body. Two locks of hair under the brim. Nothing of the Gland shows yet: the body is still within its own range. The slowest breath of the eight." + SHARED,
    },
    "rowan": {
        "sex": "m", "tint": ("heather", 0), "coat": "wedge", "hem": -0.6, "head_r": (5.2, 5.4),
        "skeleton": {"head": (2.2, -8.0), "head_tilt": -4, "shoulder_near": (-6.0, -2.2), "shoulder_far": (6.4, -3.8), "foot_near": (-3.0, 13.0), "foot_far": (5.0, 12.4), "hip_near": (-3.0, 12.0), "hip_far": (4.8, 11.2)},
        "arm_len": 8.2, "arm_w": 4.2, "arm_fill": "$carapace.light", "hand_r": (3.2, 3.4), "hand_fill": "$carapace.light", "foot_w": 5.6, "foot_h": 2.9, "foot_far_w": 5.0, "foot_far_h": 2.6,
        "pose": {"coat_lean": 0, "arm_hang": 12, "arm_far_hang": -8},
        "walk": {"duration": 0.7, "bob": 0.8, "arm_swing": 7, "sway": 1.6, "lurch": 1.0},
        "extras": lambda c: [
            ("in_hand", P_("knuckles", (c["hand"][0] + 0.4, c["hand"][1] - 0.8), rect(4.0, 1.5, 0.5), "$carapace.dark", rot=-6), "arm"),
            ("over_head", P_("visor_bar", (c["head"][0] + 1.8, c["head"][1] + 3.6), rect(1.7, 3.2, 0.4), "$ink", rot=-5), "head"),
            ("over_coat", P_("chisel", (6.6, 8.4), rect(1.2, 4.6, 0.3), "$steel", rot=16, stroke=hair), "body"),
        ],
        "walk_desc": "a heavy, planted walk: low bob, the big arm barely swinging, the whole wedge of a body leaning into each step",
        "description": "A wedge. The ruins, and who built them: broad and low, widest at the hem, the last of the eight to be moved by anything. The near arm is sleeved in carapace plate, the colour of the Soldier, and ends in a gauntlet the size of the head with a ridge of knuckles across it — since the stone bowl the right arm is stronger (R015), and the little finger folded to fit the grooves does not straighten (R053). The emitter has turned to stone from the inside (R048), warm at the ruin's temperature, and is worn as the clasp like the others'. A T-slit visor on the helmet, and a chisel at the coat." + SHARED,
    },
    "teo": {
        "sex": "f", "tint": ("frost", 2), "coat": "small", "cloak_sx": 0.92, "head": "mask", "head_r": (4.6, 5.0),
        "skeleton": {"head": (2.0, -6.6), "shoulder_near": (-4.0, -2.2), "shoulder_far": (4.8, -3.4), "hip_near": (-1.6, 10.6), "hip_far": (3.0, 10.0), "foot_near": (-1.4, 12.0), "foot_far": (3.2, 11.5), "pack": (-5.0, -2.6)},
        "arm_len": 6.4, "arm_w": 2.6, "arm_far_len": 6.0, "arm_far_w": 2.2, "hand_r": (1.5, 1.6), "hand_fill": "$chitin", "hand_far_fill": "$chitin.dark",
        "foot_w": 4.0, "foot_h": 2.3, "foot_far_w": 3.6, "foot_far_h": 2.1, "pack": True, "pack_w": 3.4, "pack_h": 3.6,
        "pose": {"coat_lean": 3, "arm_hang": 8, "arm_far_hang": -8},
        "walk": {"duration": 0.44, "stride": 1.9, "bob": 1.0, "lift": 0.9, "arm_swing": 12, "sway": 2.4}, "idle": {"duration": 1.0},
        "extras": lambda c: [
            ("behind", P_("satchel", (-8.2, 4.0), rect(8.4, 7.2, 1.0), "$bone", rot=-4, stroke=hair), "body"),
            ("behind", P_("satchel_flap", (-8.4, 1.2), rect(8.4, 2.0, 0.6), "$bone.dark", rot=-4), "body"),
            ("behind", P_("pages", (-9.6, 0.0), poly([(-2.2, 1.0), (2.0, 0.4), (2.4, -3.2), (-1.6, -2.6)]), "$silent", rot=-10), "body"),
            ("behind", P_("bloom", (c["S"]["pack"][0] + 0.4, c["S"]["pack"][1] - 2.4), circ(1.3), "$pink"), "head"),
            ("in_hand", P_("braid", (c["head"][0] - 4.6, c["head"][1] + 4.4), rect(1.7, 6.6, 0.8), "$rust", rot=16, stroke=hair), "head"),
            ("in_hand", P_("braid_tie", (c["head"][0] - 5.6, c["head"][1] + 7.6), circ(0.9), "$slate"), "head"),
            ("in_hand", P_("page", (c["hand"][0] + 1.2, c["hand"][1] - 0.8), rect(2.8, 3.4, 0.2), "$silent", rot=-18, stroke=hair), "flutter_arm"),
        ],
        "walk_desc": "quick short steps under the load — a carrier's scuttle",
        "idle_desc": "the page in the hand flutters; the load sits",
        "description": "Small, under the biggest load. The archive: the smallest body of the eight, its coat short, and on its back a satchel of pages wider than its shoulders with the sheets showing at the flap (T034) — ninety-eight picked up one at a time — and one page in the hand. The head is the most sealed of the eight, goggles and a filter can at the jaw: the helmet stays on and the filter interval was halved (T006). The hands are amber and leave wet iron on paper, which is why a mite carries a page off (T003); a flower mite has bloomed pink in the emitter's tube (T017). One more projectile, less on each." + SHARED,
    },
}

if __name__ == "__main__":
    for name in (sys.argv[1:] or list(CHARACTERS)):
        doc = build(name, CHARACTERS[name])
        out = f"/home/user/PolyGraphics/apps/ss/assets/ss-char-{name}.json"
        json.dump(doc, open(out, "w"), indent=2)
        print(f"wrote {out}: {len(doc['parts'])} parts, walk {len(doc['animations']['walk']['tracks'])} tracks")
