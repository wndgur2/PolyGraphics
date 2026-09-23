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
         plant is laid on the body in three turns with the body showing between
         them, a thorn out past each shoulder, the legs come out from under the
         lowest turn, and she stands up — head over the shoulders with a neck
         under it, which nobody else here has, on the slimmest arms in the set.
         A helmet cut to a profile with a lamp and a slit on it and nothing
         between them, the piece of burrow wall at the hip — the one who left
         the emitter in the burrow, and the one the weapon is still holding
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
    "head": "egg", "head_r": (5.3, 5.8), "head_fill": None, "visor_w": 6.6, "visor_h": 2.6,
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

def stem(pts, w0, w1, off=0.0):
    """A centreline swept by a taper and closed into one polygon. `ss.proj.vine`
    draws its plants this way — the shape *is* the path the thing grew along —
    and a plant grown on a body has to be the same plant. It draws a lock of
    hair too: hair and cord are one problem, a line whose width changes.

    `off` slides the whole centreline sideways before the sweep, which is how the
    arsenal lights a stem: the lit edge is the same centreline pushed most of a
    half-width off it, so light cannot slide off a cord however hard it bends.
    Call `stem` twice with the same points — once wide and dark, once narrow and
    offset — and the two agree by construction rather than by hand.

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
        x, y = x + nx * off, y + ny * off
        w = (w0 + (w1 - w0) * i / n) / 2
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
    if kind == "wrap":      # not a garment: the plant itself, lying on the body and ending in leaf points
        # Cloth hangs, plants cling, and the silhouette is where the difference
        # lives. A coat leaves the shoulder and swings clear of the body, so the
        # outline belongs to the coat and the body inside it could be anybody's.
        # This one is the body — chest, waist, hip, stopping at the hip line with
        # the legs carrying on out from under it, which no other walker does —
        # and the plant is laid over it in bands that follow it round (the row's
        # `band_*` parts). A leafy hem was tried on a solid piece first and read
        # as a torn tunic, because a ragged edge on one closed shape is damage;
        # what reads as *wrapped* is seeing the body between the turns.
        return top + [[4.6, -1.0], [3.9, 3.0], [4.7, 6.0], [2.6, 7.6], [-0.2, 7.9],
                      [-2.9, 7.5], [-4.5, 6.0], [-3.9, 3.0], [-4.7, -0.8]]
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
                P_("lamp", (h[0] + 2.1, h[1] - 2.5), circ(1.15), "$silent", stroke=hair),
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

# Mina's runner, written once: the fill and its lit edge are the same centreline,
# the second one offset (see `stem`), so light cannot come off the cord where the
# cord bends. One wind rather than two bands — `ss.proj.vine-snare` argues the
# same about a body this weapon is holding, and Mina is the body it never lets
# go of. Out from under the load at the near shoulder, once round the waist just
# below the clasp, then down over the hip and off the hem, on its way back to the
# floor it comes up out of in a run.
# The turns the plant takes round her: over the near shoulder, across the ribs to
# the far hip, and once round the waist under it. Both are `stem()` sweeps, same
# as the arsenal's own plants, and the gaps between them are the point — a body
# you can see between the turns is wrapped, a body you cannot is dressed.
BAND_A = [(-2.6, -1.6), (-0.4, 0.8), (1.8, 3.2), (3.9, 5.6)]
BAND_B = [(-3.6, 3.8), (-0.4, 4.8), (3.0, 4.3)]
# The lowest turn does not close: it comes round the hip and carries on off the
# far side as a free tail, tapering out. `ss.proj.vine-snare` ends the same way,
# and it is the one thing here allowed past the outline — leaves were drawn at
# the shoulder and at the hip and read as pauldrons and luggage tags, and the
# arsenal's plants have no leaves on purpose (`ss.proj.vine`: a leafy stem is a
# picture of a plant, not of this weapon).
BAND_C = [(-3.2, 6.6), (-0.6, 7.4), (2.4, 7.0), (4.6, 7.6), (6.4, 9.6)]

WALL_BIND = [(-1.9, 5.8), (-2.0, 6.9), (-2.0, 8.0)]

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
        "sex": "f", "tint": ("timber", 2), "coat": "wrap", "cloak_sx": 1.0, 
        "cape": False, "organ": False, "legs": True,
        # Standing up. The head was at -8.2 with the helmet down over the shoulder
        # line, which is the rig's default (the guide's §2: the head covers the
        # shoulders) and on a small body it is a stoop — no neck, chin on the
        # chest. Here the head goes up to -10.2, the shoulder line comes up and
        # levels off, the line of action goes vertical, and the gap that opens
        # between helmet and shoulders is filled by a neck, which is the whole
        # difference between a figure that stands and one that hunches.
        # The feet come onto one line. A runway walk puts one foot almost directly
        # in front of the other, and at this size that is the single cheapest
        # thing that separates a model's walk from a march: the two contact
        # points were 3.8 apart and are 2.8 now, so the legs angle in from the
        # hips instead of running parallel.
        "skeleton": {"head": (0.9, -9.8), "head_tilt": -6, "shoulder_near": (-4.4, -3.0), "shoulder_far": (5.0, -4.0),
                     "hip_near": (-2.0, 6.2), "hip_far": (2.8, 5.8), "foot_near": (-1.1, 12.8), "foot_far": (2.1, 12.2)},
        "head": "lamp", "head_r": (4.1, 4.5), "visor_w": 4.2, "visor_h": 1.7, "head_fill": "$husk", "pose": {"coat_lean": 0, "arm_hang": 6, "arm_far_hang": -5, "visor_turn": -6},
        "arm_len": 7.4, "arm_w": 1.8, "arm_far_len": 6.6, "arm_far_w": 1.5, "hand_r": (1.15, 1.3), "hand_far_r": (1.0, 1.15), "hand_fill": "$timber", "hand_far_fill": "$timber.dark",
        # A walk that will not be hurried: the longest stride and the slowest beat
        # of the eight, the smallest bob, the arms nearly still, and the head all
        # but stopped (`head_nod` 0.5 against the rig's 2.5). Carriage is mostly
        # what a body does *not* do — every dial that says effort comes down and
        # the one that says reach goes up.
        # …but not *pinned*. The runway guides are blunt about it: arms held stiff
        # against the sides read as tension from the back of the room, and what
        # reads as poise is a relaxed pendulum. So the arms came back up from 6
        # to 10 after they were taken down to 6, which was a mistake made in the
        # name of stillness.
        "walk": {"duration": 0.78, "stride": 2.6, "lift": 0.7, "bob": 0.45, "sway": 2.0, "arm_swing": 10, "leg_swing": 25, "head_nod": 0.5},
        "idle": {"duration": 1.7},
        "extras": lambda c: [
            # Two leaves off the wrap's shoulder, breaking the outline where a
            # coat would have a smooth cap. One reads as a shoulder, two read as
            # a plant.
            ("over_coat", P_("band_a", (0, 0), stem(BAND_A, 1.9, 1.6), "$moss"), "body"),
            ("over_coat", P_("band_a_lit", (0, 0), stem(BAND_A, 0.8, 0.6, off=-0.58), "$moss.light2"), "body"),
            ("over_coat", P_("band_b", (0, 0), stem(BAND_B, 1.8, 1.5), "$moss"), "body"),
            ("over_coat", P_("band_b_lit", (0, 0), stem(BAND_B, 0.7, 0.6, off=-0.52), "$moss.light2"), "body"),
            ("over_coat", P_("band_c", (0, 0), stem(BAND_C, 1.9, 0.5), "$moss"), "body"),
            ("over_coat", P_("band_c_lit", (0, 0), stem(BAND_C, 0.7, 0.2, off=-0.55), "$moss.light2"), "body"),
            # The runner, and it is the weapon. The wrap is the plant that has
            # grown over her and is drawn in the pale `$moss.light2`; this is the
            # live one, at the arsenal's own value with its lit edge and its barb,
            # so the two never read as one thing. Round the waist, over the hip
            # and off the wrap's edge, on its way back to the floor.
            ("over_cape", P_("wall", (-2.6, 8.4), poly([(-1.5, -1.4), (1.5, -1.6), (1.6, 1.5), (-1.4, 1.6)]), "$rust", rot=-12, stroke=hair), "body"),
            # Zyra carries her silhouette on pointed shapes off the shoulders and
            # hips, and a thorn is the one pointed shape this arsenal already owns
            # (`ss.proj.vine-snare`'s barbs). Both go on the *outline*: a barb in
            # the middle of a torso is a decal, a barb on the edge is a plant that
            # could catch on you. They sit above the shoulder line, which is the
            # one band of the near side the sleeve does not cover.
            ("over_cape", P_("thorn", (-3.9, -4.1), poly([(-1.0, 1.0), (1.0, 0.8), (-0.1, -2.0)]), "$blood.dark2", rot=-38), "body"),
            ("over_cape", P_("thorn_far", (5.2, -3.0), poly([(-0.9, 0.9), (0.9, 0.7), (0.0, -1.8)]), "$blood.dark2", rot=42), "body"),
            # The neck. Nothing else on the eight has one, and nothing else on
            # the eight stands up straight either; the two are the same fact.
            ("in_hand", P_("neck", (0.0, -3.9), rect(2.4, 3.2, 0.7), shade(c["T"], -1)), "body"),
        ],
        "walk_desc": "carriage: the longest stride and the slowest beat of the eight, legs swinging from the hip under the lowest turn, and almost nothing above the waist — the smallest bob in the set, the arms barely moving, and the head carried rather than nodded (`head_nod` 0.5 against the rig's 2.5). It is a walk made of what the body does not do. Twenty-nine levels taught her not to bounce what she carries (M035), and the gait it left her is one that will not be hurried",
        "idle_desc": "the slowest breath of the eight bar Eden's: the body rises under the turns and the tail off the hip does not move",
        "description": "A stem, and the one of the eight not wearing a coat. **The plant is on her instead of cloth**, which is a silhouette decision before it is a costume one: a coat leaves the shoulder and swings clear of the body, so its outline belongs to the coat and the body inside it could be anybody\'s, while a plant clings and the outline stays hers. So the torso is the body — chest, waist, hip, stopping at the hip line — and `ss.proj.vine` is laid over it in three turns that follow it round, each one dark with its own lit edge, with the body showing in the gaps. The gaps are the whole reading: a body you can see between the turns is wrapped, a body you cannot is dressed. The legs come out from under the lowest turn, which nobody else here does, that turn does not close but carries on off the far hip as a free tail tapering out the way `ss.proj.vine-snare` ends, and a `$blood.dark2` thorn comes out past each shoulder. **Zyra is the reference for those**: her silhouette is carried on pointed shapes off the shoulders and hips, and a thorn is the one pointed shape this arsenal already owns. Both sit on the outline rather than inside it — a barb in the middle of a torso is a decal, a barb on the edge is a plant that could catch on you. There are no leaves: the arsenal\'s plants have none on purpose (a leafy stem is a picture of a plant, not of this weapon), and at four pixels a leaf drawn at the shoulder is a pauldron and at the hip a luggage tag — both were drawn before this was settled. **And she stands, and walks like it.** The rig\'s default puts the helmet down over the shoulder line, which on a body this size is a stoop with the chin on the chest; here the head sits back over the shoulders with a neck under it — the only neck in the set, and most of the difference between a figure that stands and one that hunches — the smallest head of the eight on the longest legs, and the visor slit raised so the gaze is level rather than down. The walk is the same argument in motion, and it is a runway walk: the two contact points come onto one line, 2.8 apart rather than 3.8, so the legs angle in from the hips instead of running parallel — at this size that is the single cheapest thing separating a model\'s walk from a march. The longest stride and slowest beat in the set, the smallest bob, and the head all but stopped (`head_nod` 0.5 against the rig\'s 2.5). Carriage is mostly what a body does *not* do. The arms are the exception and they were got wrong once: taken down to almost nothing in the name of stillness, where every runway guide says the opposite — arms held stiff against the sides read as tension from the back of the room, and what reads as poise is a relaxed pendulum. They are back up, on the slimmest sleeves in the set. Bare arms and bare hands on the warm ramp, because a glove on a body wrapped in plant is a costume again. **What she took in place of the emitter is what grew.** The piece of burrow wall hangs at the near hip, palm-sized — the record\'s own word (M038) — still warm half a month on with something chewing inside it (M042), and the turns run out of it: the vines that come up out of the ground in a run come up out of what this one carries (M041: she buried the piece behind base, and by morning there was a hole going down). The weapon holds what it catches, and this is the body it never let go of. **She is also the one with no clasp and no mantle**: M042 has her going back down with the wall *in place of the emitter*, so the dead organ the other seven wear is not on her — it stayed where it burned out beside the queen (M031). The helmet is the `lamp` kind and the one head in the set that is not an egg with something stuck on it: a profile cut in at the front and let out into a nape at the back, a visor slit, and the one light the eight carry clipped against the rim above it, with nothing joining the two — a bar down the middle between them is a Corinthian nose guard before it is a bracket (M005: the burrow is where the compass stopped). Three turns of `$moss` on `$timber.light2` cost her some floor: 3.2 : 1 against `ss.env.ground`, beside Sol\'s 3.0. 22 parts, one over the set\'s previous high, and the legs and the neck are three of them." + SHARED,
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
