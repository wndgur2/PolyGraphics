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
  mir    a hump: the coat rises over the piece of wall carried on the back, the
         head low and forward — the hauler
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
    "coat": "bell", "cloak_sx": 1.0, "hem": 0.0, "coat_fill": None, "cape": True, "cape_fill": None,
    "head": "egg", "head_r": (5.3, 5.8), "head_fill": None, "visor_w": 6.6, "visor_h": 2.6,
    "arm_len": 7.6, "arm_w": 3.0, "arm_fill": None, "arm_far_len": 7.0, "arm_far_w": 2.6,
    "hand_r": (1.7, 1.9), "hand_far_r": (1.4, 1.6), "hand_fill": "$slate.dark", "hand_far_fill": "$slate",
    "legs": False, "foot_w": 4.8, "foot_h": 2.7, "foot_far_w": 4.2, "foot_far_h": 2.4,
    "pack": False, "pack_w": 4.2, "pack_h": 4.4, "pack_fill": "$slate.light", "feelers": False,
    "walk": {"duration": 0.56, "stride": 2.6, "lift": 1.2, "bob": 1.4, "sway": 3.0, "arm_swing": 14, "lurch": 0.0, "leg_swing": 22},
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
    if kind == "hump":      # a bell whose back rises over the load, and whose front rounds over a gut
        return [[sn[0] + 0.4, sn[1] - 0.6], [sf[0] - 0.6, sf[1] - 0.2], [7.8, 1.6], [9.0, 5.8], [8.0, 10.2 + hem], [4.4, 11.9 + hem], [0.2, 12.3 + hem], [-4.2, 11.9 + hem], [-7.0, 10.6 + hem], [-8.6, 6.0], [-9.8, 0.4], [-9.6, -4.4], [-7.6, -7.2]]
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
    sn, sf = S["shoulder_near"], S["shoulder_far"]
    sx = C["cloak_sx"]
    T = C["tint"]
    for key, delta in (("coat_fill", 0), ("cape_fill", 1), ("head_fill", 2), ("arm_fill", 0)):
        if C[key] is None: C[key] = shade(T, delta)
    C["arm_far_fill"] = shade(T, -1); C["leg_fill"] = shade(T, 0); C["leg_far_fill"] = shade(T, -1)

    heads = head_parts(C["head"], S, C, P)
    cloak = {"id": "cloak", "at": [0, 0], "rot": P["coat_lean"] - 2, "shape": poly([(x * sx, y) for x, y in coat_points(C["coat"], sn, sf, C["hem"])]), "fill": C["coat_fill"], "stroke": thin}
    cape = {"id": "cape", "at": [0, 0], "shape": poly(cape_points(sn, sf, sx)), "fill": C["cape_fill"]} if C["cape"] else None
    organ = {"id": "organ", "at": [1.0, 1.0], "use": "ss.lib.organ", "variant": "dead", "scale": 0.72}
    foot = P_("foot", S["foot_near"], rect(C["foot_w"], C["foot_h"], 1.2), "$slate.dark")
    foot_far = P_("foot_far", S["foot_far"], rect(C["foot_far_w"], C["foot_far_h"], 1.1), "$slate")
    legs = []
    if C["legs"]:
        for pid, hip, ft, w, fill in (("leg_far", S["hip_far"], S["foot_far"], 2.6, C["leg_far_fill"]), ("leg", S["hip_near"], S["foot_near"], 3.0, C["leg_fill"])):
            L = math.hypot(ft[0] - hip[0], ft[1] - hip[1]); ang = -math.degrees(math.atan2(ft[0] - hip[0], ft[1] - hip[1]))
            legs.append(P_(pid, hang(hip, L, ang), rect(w, L + 1.0, 1.2), fill, rot=ang, stroke=hair if pid == "leg" else None))
    a_c = hang(sn, C["arm_len"], P["arm_hang"]); h_c = below(sn, C["arm_len"] + 0.9, P["arm_hang"])
    arm = P_("arm", a_c, rect(C["arm_w"], C["arm_len"], 1.4), C["arm_fill"], rot=P["arm_hang"], stroke=hair)
    hand = P_("hand", h_c, ell(*C["hand_r"]), C["hand_fill"], stroke=hair)
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
        + [cloak] + layers["over_coat"] + ([cape] if cape else []) + [organ] + layers["over_cape"] + [arm, hand] + layers["in_hand"] + heads + layers["over_head"]
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
    body_group = ["cloak", "organ"] + (["cape"] if cape else [])
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
        tr.append(track("head", "rot", [2.5 * math.sin(4 * math.pi * t + 0.8) for t in TS]))
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

    return {"id": f"ss.char.{name}", "name": name.capitalize(), "description": row["description"], "tags": ["char"], "size": [32, 32], "meta": {"radius": 11},
            "parts": parts, "skeleton": skeleton, "animations": {"idle": idle(), "walk": walk()}}

# ============================================================== 5. the eight
SHARED = " Drawn from one skeleton and one facing (docs/character-rig-guide.md) by scripts/walker.py, with its own primary shape; the dead organ is worn as the clasp of the coat in the same place on all eight; flat token fills; radius 11."

CHARACTERS = {
    "arin": {
        "tint": ("frost", 0), "pack": True, "pack_w": 5.0, "pack_h": 5.2, "feelers": True,
        "extras": lambda c: [
            ("behind", P_("rack", (c["S"]["pack"][0] - 3.3, c["S"]["pack"][1] + 0.8), rect(2.2, 4.0), "$steel.light", stroke=hair), "head"),
        ],
        "idle_desc": "the body breathes under the coat; the dead feelers keep sweeping for a signal that never comes",
        "description": "A circle. The first expedition, on the day the last cartridge went in (A047): the bell coat, the egg helmet, and the prototype emitter — the biggest box any of the eight carries, its cartridge rack beside it, and the two dead feelers rising from its lid, swept back past the helmet as the crown of the silhouette. Arin is the only one of the eight with feelers: the antennae were the prototype's design (A004), and every mark after it vents through a tube — and they are the lash. Grown long and thin into two whips that trail back past the helmet and crack forward, the weapon is the feelers themselves, which is what the game is named for. The hands have gone dark and hard — the saw does not mark them (A052), the Molt's slate, the first of the body to lose its blood." + SHARED,
    },
    "sol": {
        "tint": ("lichen", 0), "coat": "jacket_belly", "cloak_sx": 0.9, "legs": True, "cape": False,
        "head": "bare", "head_r": (4.6, 5.0),
        "skeleton": {"hip_near": (-2.2, 6.4), "hip_far": (3.2, 5.8), "foot_near": (-1.8, 13.4), "foot_far": (4.0, 12.8), "head": (2.6, -8.4)},
        "pose": {"coat_lean": 10, "arm_hang": 14, "arm_far_hang": -16}, "arm_w": 2.6, "arm_far_w": 2.2, "hand_r": (1.5, 1.7), "foot_w": 4.2, "foot_h": 2.2, "foot_far_w": 3.8, "foot_far_h": 2.0,
        "walk": {"duration": 0.44, "bob": 1.8, "arm_swing": 22, "leg_swing": 26, "sway": 1.5}, "idle": {"duration": 1.0},
        "extras": lambda c: [
            ("behind", P_("scarf", (-5.0, -4.0), poly([(0.4, -1.2), (-4.2, -3.0), (-8.8, -2.6), (-4.6, -0.2), (-0.2, 1.4)]), "$husk", rot=8, stroke=hair), "scarf"),
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
        "tint": ("ochre", 0), "coat": "slab", "head": "box", "head_r": (5.4, 5.0), "visor_w": 7.4, "cape": False,
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
    "mir": {
        "tint": ("timber", 2), "coat": "hump", "cloak_sx": 1.02,
        "skeleton": {"head": (3.6, -5.6), "head_tilt": -4, "shoulder_near": (-4.0, -2.0), "shoulder_far": (6.0, -3.6), "foot_near": (-2.8, 13.1), "foot_far": (4.6, 12.5), "hip_near": (-2.8, 12.0), "hip_far": (4.4, 11.2)},
        "head_r": (5.0, 5.4), "pose": {"coat_lean": 7, "arm_hang": 10, "arm_far_hang": -4},
        "walk": {"duration": 0.62, "bob": 0.0, "lift": 0.8, "sway": 1.4, "arm_swing": 8},
        "extras": lambda c: [
            ("over_coat", P_("wall", (-7.4, -6.6), poly([(-2.4, -2.0), (2.4, -2.6), (2.8, 2.0), (-2.2, 2.4)]), "$rust", rot=-14, stroke=hair), "body"),
            ("over_coat", P_("wall_crack", (-7.4, -6.4), rect(3.0, 0.6, 0.2), "$rust.dark", rot=22), "body"),
            ("over_cape", P_("cord", (0.2, -0.6), rect(1.1, 9.4, 0.4), "$bone", rot=-32), "body"),
            ("over_coat", P_("hump_shade", (-7.6, 1.2), ell(2.2, 5.0), shade(c["T"], -1), rot=-10), "body"),
        ],
        "walk_desc": "the haul: no bounce at all, short flat steps, the load riding still on the back",
        "description": "A hump. The burrow, walked from the inside down to the queen: the coat rises over the piece of its wall carried on the back where the emitter used to be, warm half a month on, chewing inside it at night (M038, M042), corded across the chest, the rust of it showing at the top of the hump. The head sits low and forward with almost no neck, the stance is wide, and the walk has no bounce in it — the Porter's haul, twenty-nine levels of it (M035)." + SHARED,
    },
    "kano": {
        "tint": ("silent", 0), "coat": "column", "cloak_sx": 1.0, "hem": 0.0, "head": "hood", "head_r": (4.8, 6.0), "visor_w": 5.8,
        "skeleton": {"head": (1.8, -7.3), "shoulder_near": (-4.2, -3.2), "shoulder_far": (5.0, -4.4), "foot_near": (-1.4, 14.0), "foot_far": (3.2, 13.4), "hip_near": (-1.6, 12.6), "hip_far": (3.0, 12.0)},
        "pose": {"coat_lean": 4, "arm_hang": 4, "arm_far_hang": -4}, "arm_far_len": 7.4, "foot_h": 2.4, "foot_far_h": 2.2,
        "walk": {"duration": 0.72, "stride": 2.2, "lift": 0.5, "bob": 0.5, "arm_swing": 7, "sway": 4.6}, "idle": {"duration": 1.6},
        "extras": lambda c: [
            ("behind", P_("staff", (c["hand_far"][0] + 2.2, c["hand_far"][1] - 7.4), rect(1.6, 20.0, 0.6), "$timber", rot=3, stroke=hair), "arm_far"),
            ("behind", P_("staff_cap", (c["hand_far"][0] + 2.7, c["hand_far"][1] - 17.4), circ(1.4), "$steel.light", stroke=hair), "arm_far"),
            ("feet_over", P_("gaiter", (c["foot"][0], c["foot"][1] - 0.9), rect(4.8, 1.0, 0.3), "$steel"), "foot"),
            ("feet_over", P_("gaiter_far", (c["foot_far"][0], c["foot_far"][1] - 0.8), rect(4.2, 0.9, 0.3), "$steel"), "foot_far"),
        ],
        "walk_desc": "a glide: the long coat carries the walk, the feet barely leave the ground under it, the hem sways wide and the staff is planted with the far hand — no bounce, no hurry",
        "idle_desc": "standing on the staff, the hood dipping with the breath",
        "description": "A column. The patrols, and the rules that came out of them: do not stop (K033). A narrow coat, long to the boots, under a peaked hood-helmet, and a staff in the far hand taller than the head — the twelfth emitter was dropped where it broke, as the rules say (K030, K033), so nothing rides on the back. Gaitered boots, and a walk that is the coat's: a slow glide with the staff planted, no bounce and no hurry — the one who does not stop does not rush either." + SHARED,
    },
    "eden": {
        "tint": ("sage", 0), "coat": "round", "head": "brim", "head_r": (5.0, 5.4),
        "skeleton": {"head": (2.2, -7.2), "shoulder_near": (-5.2, -2.6), "shoulder_far": (6.0, -3.8)},
        "pack": True, "pack_w": 3.8, "pack_h": 4.0, "pose": {"coat_lean": 1, "arm_hang": 8, "arm_far_hang": -10},
        "walk": {"duration": 0.62, "bob": 1.0, "sway": 3.6, "arm_swing": 10}, "idle": {"duration": 1.7},
        "extras": lambda c: [
            ("over_cape", P_("throat", (6.2, -0.2), ell(3.6, 2.5), "$spore", rot=-12, stroke=hair), "body"),
            ("over_head", P_("mandible", (c["head"][0] + 4.6, c["head"][1] + 4.2), poly([(-1.4, -1.6), (1.6, -0.6), (3.6, 1.4), (2.2, 2.2), (0.2, 0.8), (-1.6, 0.2)]), "$chitin", stroke=hair), "head"),
            ("over_head", P_("mandible_far", (c["head"][0] + 1.2, c["head"][1] + 4.6), poly([(-2.6, -0.4), (0.4, -1.4), (2.4, 0.6), (1.2, 1.8), (-1.2, 1.2)]), "$chitin.dark", stroke=hair), "head"),
        ],
        "walk_desc": "an unhurried walk, the hem swinging wide, the brim steady",
        "idle_desc": "the slowest breath of the eight: six years of standing still and watching",
        "description": "A mushroom. The long station: a round coat under the wide flat brim on the helmet, the shape of six years beside the fungi (E009) and of the Gland's dome to come. A fingertip of royal jelly in place of the last cartridge (E093), and the throat under the helmet has begun to swell teal — the queen's smell on its way out as spit. A pair of amber mandibles at the jaw, under the brim. The slowest breath of the eight." + SHARED,
    },
    "rowan": {
        "tint": ("heather", 0), "coat": "wedge", "hem": -0.6, "head_r": (5.2, 5.4),
        "skeleton": {"head": (2.4, -6.8), "shoulder_near": (-6.0, -2.2), "shoulder_far": (6.4, -3.8), "foot_near": (-3.0, 13.0), "foot_far": (5.0, 12.4), "hip_near": (-3.0, 12.0), "hip_far": (4.8, 11.2)},
        "arm_len": 8.2, "arm_w": 5.0, "arm_fill": "$carapace.light", "hand_r": (3.3, 3.5), "hand_fill": "$carapace.light", "foot_w": 5.6, "foot_h": 2.9, "foot_far_w": 5.0, "foot_far_h": 2.6,
        "pack": True, "pack_w": 4.4, "pack_h": 4.4, "pack_fill": "$sand", "pose": {"coat_lean": 0, "arm_hang": 12, "arm_far_hang": -8},
        "walk": {"duration": 0.7, "bob": 0.8, "arm_swing": 7, "sway": 1.6, "lurch": 1.0},
        "extras": lambda c: [
            ("over_cape", P_("shoulder_stone", (c["sn"][0] + 0.6, c["sn"][1] + 0.4), poly([(-3.6, -1.4), (0.6, -2.8), (3.8, -0.6), (2.6, 2.4), (-2.8, 2.2)]), "$sand", stroke=hair), "body"),
            ("in_hand", P_("claw_a", (c["hand"][0] + 2.8, c["hand"][1] + 1.8), poly([(-1.2, -1.2), (1.2, -0.4), (3.2, 2.0), (1.6, 2.2), (-0.4, 0.6)]), "$carapace.dark", stroke=hair), "arm"),
            ("in_hand", P_("claw_b", (c["hand"][0] + 0.8, c["hand"][1] + 3.2), poly([(-1.0, -1.4), (0.8, -0.8), (1.6, 2.4), (0.0, 2.4), (-1.2, 0.2)]), "$carapace.dark", stroke=hair), "arm"),
            ("in_hand", P_("claw_c", (c["hand"][0] - 1.8, c["hand"][1] + 2.8), poly([(0.8, -1.4), (-0.8, -0.6), (-2.2, 1.8), (-0.6, 2.0), (0.6, 0.4)]), "$carapace.dark", stroke=hair), "arm"),
            ("over_coat", P_("chisel", (6.6, 8.4), rect(1.2, 4.6, 0.3), "$steel", rot=16, stroke=hair), "body"),
        ],
        "walk_desc": "a heavy, planted walk: low bob, the big arm barely swinging, the whole wedge of a body leaning into each step",
        "description": "A wedge. The ruins, and who built them: broad and low, widest at the hem, the last of the eight to be moved by anything. The whole near arm is plated in carapace, the colour of the Soldier, ending in a fist the size of the head — since the stone bowl the right arm is stronger (R015), and the little finger folded to fit the grooves does not straighten (R053). A stone sits on that shoulder, and the emitter on the back has turned to stone from the inside (R048), warm at the ruin's temperature. A chisel at the coat." + SHARED,
    },
    "teo": {
        "tint": ("frost", 2), "coat": "small", "cloak_sx": 0.92, "head": "mask", "head_r": (4.6, 5.0),
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
