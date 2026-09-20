"""The walkers' rig — one script, one self-contained document per playable character.

    python3 scripts/walker.py            # rewrites apps/ss/assets/ss-char-<name>.json, all eight
    python3 scripts/walker.py arin sol   # only these

Skeleton first, parts second, motion last — docs/character-rig-guide.md says why
and in what order. Everything is derived from one SKELETON and one POSE: a
facing, a shoulder line, a hip line, the head, the feet, and the points the kit
hangs from. A part is placed by naming the joint it hangs from plus a length
and an angle, never by a coordinate typed on its own; a clip turns joints, and
the part's x/y follow from the turn. The skeleton goes into each document by
joint name, so a change is asked for as "shoulder_near a pixel lower".

Eight characters are one body: each is a row of parameters (a tilt, a width, a
head, a pack, a gait) and a handful of extra parts that say what that
expedition took in place of the emitter and the one change its log measured —
the game's docs/character-redesign-plan.md, section 4, page numbers included.

Why a script and not a `use`: an animation only addresses the document's own
parts, and a `use` part is one node whose insides no track can reach — a shared
body composed by `use` could breathe but never walk. The antenna and the organ
stay `use` parts, moved whole.
"""
import json, math, sys

R = lambda d: math.radians(d)
def r2(x): return round(x, 2)
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def rotv(v, deg):
    c, s = math.cos(R(deg)), math.sin(R(deg))
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)

hair = {"color": "$ink", "width": "hair"}
thin = {"color": "$ink", "width": "thin"}

# ============================================================== 1. skeleton and pose (shared)
# Canvas 32×32, origin at the centre, +x right, +y down. The body faces the
# viewer's FRONT-RIGHT (a three-quarter view from a little above). A body facing
# you has its right hand on your left, so the RIGHT shoulder is the near one,
# low and on the LEFT of the picture, and the LEFT shoulder is the far one,
# high and on the RIGHT, behind the body. The engine mirrors the frame to walk left.
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
    # proportions and paint the eight share unless a row says otherwise
    "head_r": (5.3, 5.8), "head_fill": "$frost.light2", "head_shape": "egg", "visor": True, "visor_w": 6.6, "visor_h": 2.6,
    "cloak_sx": 1.0, "hem": 0.0, "cape_fill": "$frost.light",
    "arm_len": 7.6, "arm_w": 3.0, "arm_far_len": 7.0, "arm_far_w": 2.6,
    "hand_r": (1.7, 1.9), "hand_far_r": (1.4, 1.6), "hand_fill": "$slate.dark", "hand_far_fill": "$slate",
    "foot_w": 4.8, "foot_h": 2.7, "foot_far_w": 4.2, "foot_far_h": 2.4,
    "pack_w": 4.2, "pack_h": 4.4,
    "feeler_rot": -40, "feeler_far_rot": -54, "feeler_scale": (0.55, 0.85), "feeler": True,
    # clips
    "walk": {"duration": 0.56, "stride": 2.6, "lift": 1.2, "bob": 1.4, "sway": 3.0, "arm_swing": 14, "lurch": 0.0},
    "idle": {"duration": 1.15, "feelers": "sweep", "march": False},
}

def hang(joint, length, angle):
    """The centre of a link of `length` hanging from `joint`, turned `angle` degrees off straight down."""
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

# ============================================================== 2. one body, from a row of parameters
def build(name, row):
    S = dict(BASE_SKELETON); S.update(row.get("skeleton", {}))
    P = dict(BASE_POSE); P.update(row.get("pose", {}))
    C = dict(BASE); C.update({k: v for k, v in row.items() if k not in ("skeleton", "pose", "extras", "walk", "idle", "description", "tags")})
    W = dict(BASE["walk"]); W.update(row.get("walk", {}))
    I = dict(BASE["idle"]); I.update(row.get("idle", {}))
    sn, sf = S["shoulder_near"], S["shoulder_far"]
    sx = C["cloak_sx"]

    # --- masses, from the joints
    if C["head_shape"] == "egg":
        head = {"id": "head", "at": [*S["head"]], "rot": S["head_tilt"], "shape": {"kind": "ellipse", "rx": C["head_r"][0], "ry": C["head_r"][1]}, "fill": C["head_fill"], "stroke": thin}
    else:  # a squared-off dome: the survey's helmet
        head = {"id": "head", "at": [*S["head"]], "rot": S["head_tilt"] + 4, "shape": {"kind": "rect", "w": C["head_r"][0] * 2, "h": C["head_r"][1] * 2, "corner": 3.4}, "fill": C["head_fill"], "stroke": thin}
    visor = {"id": "visor", "at": [r2(S["head"][0] + 1.6), r2(S["head"][1] + 1.2)], "rot": P["visor_turn"], "shape": {"kind": "rect", "w": C["visor_w"], "h": C["visor_h"], "corner": 1.3}, "fill": "$ink"}
    hem = C["hem"]
    cloak_pts = [[sn[0] + 0.6, sn[1] - 0.2], [sf[0] - 0.6, sf[1] - 0.2],
                 [7.5, 1.6], [7.7, 6.0], [6.8, 10.6 + hem], [4.4, 11.9 + hem], [0.2, 12.3 + hem], [-4.2, 11.9 + hem], [-6.8, 10.6 + hem], [-7.6, 6.0], [-7.2, 1.2]]
    cloak = {"id": "cloak", "at": [0, 0], "rot": P["coat_lean"] - 2, "shape": {"kind": "poly", "points": [[r2(x * sx), r2(y)] for x, y in cloak_pts]}, "fill": "$frost", "stroke": thin}
    cape_pts = [[sn[0], sn[1] - 0.2], [sf[0], sf[1] - 0.2], [7.3, 0.9], [3.4, 2.4], [0.2, 1.3], [-3.4, 2.2], [-7.0, 0.2]]
    cape = {"id": "cape", "at": [0, 0], "shape": {"kind": "poly", "points": [[r2(x * sx), r2(y)] for x, y in cape_pts]}, "fill": C["cape_fill"]}
    organ = {"id": "organ", "at": [1.0, 1.0], "use": "ss.lib.organ", "variant": "dead", "scale": 0.72}
    foot = {"id": "foot", "at": [*S["foot_near"]], "shape": {"kind": "rect", "w": C["foot_w"], "h": C["foot_h"], "corner": 1.2}, "fill": "$slate.dark"}
    foot_far = {"id": "foot_far", "at": [*S["foot_far"]], "shape": {"kind": "rect", "w": C["foot_far_w"], "h": C["foot_far_h"], "corner": 1.1}, "fill": "$slate"}
    a_c = hang(sn, C["arm_len"], P["arm_hang"]); h_c = below(sn, C["arm_len"] + 0.9, P["arm_hang"])
    arm = {"id": "arm", "at": [r2(a_c[0]), r2(a_c[1])], "rot": P["arm_hang"], "shape": {"kind": "rect", "w": C["arm_w"], "h": C["arm_len"], "corner": 1.4}, "fill": "$frost", "stroke": hair}
    hand = {"id": "hand", "at": [r2(h_c[0]), r2(h_c[1])], "shape": {"kind": "ellipse", "rx": C["hand_r"][0], "ry": C["hand_r"][1]}, "fill": C["hand_fill"], "stroke": hair}
    af_c = hang(sf, C["arm_far_len"], P["arm_far_hang"]); hf_c = below(sf, C["arm_far_len"] + 0.9, P["arm_far_hang"])
    arm_far = {"id": "arm_far", "at": [r2(af_c[0]), r2(af_c[1])], "rot": P["arm_far_hang"], "shape": {"kind": "rect", "w": C["arm_far_w"], "h": C["arm_far_len"], "corner": 1.2}, "fill": "$frost.dark"}
    hand_far = {"id": "hand_far", "at": [r2(hf_c[0]), r2(hf_c[1])], "shape": {"kind": "ellipse", "rx": C["hand_far_r"][0], "ry": C["hand_far_r"][1]}, "fill": C["hand_far_fill"]}
    pack = {"id": "pack", "at": [*S["pack"]], "shape": {"kind": "rect", "w": C["pack_w"], "h": C["pack_h"], "corner": 1.0}, "fill": "$slate.light", "stroke": hair}
    fs = list(C["feeler_scale"])
    feeler = {"id": "feeler", "at": [*S["feeler_root"]], "rot": C["feeler_rot"], "scale": fs, "use": "ss.lib.antenna", "variant": "dead"}
    feeler_far = {"id": "feeler_far", "at": [*S["feeler_far_root"]], "rot": C["feeler_far_rot"], "scale": fs, "use": "ss.lib.antenna", "variant": "dead"}

    ctx = {"S": S, "P": P, "C": C, "sn": sn, "sf": sf, "hand": h_c, "hand_far": hf_c, "head": S["head"], "foot": S["foot_near"], "foot_far": S["foot_far"]}
    layers = {k: [] for k in ("behind", "feet_over", "over_coat", "over_cape", "in_hand", "over_head")}
    follow = {}
    for layer, part, fol in row.get("extras", lambda c: [])(ctx):
        layers[layer].append(part); follow[part["id"]] = fol

    # --- depth = draw order, far to near for a body facing front-right
    parts = [feeler_far] + ([feeler] if C["feeler"] else []) + [pack] + layers["behind"] + [arm_far, hand_far, foot_far, foot] + layers["feet_over"] \
        + [cloak] + layers["over_coat"] + [cape, organ] + layers["over_cape"] + [arm, hand] + layers["in_hand"] + [head] + ([visor] if C["visor"] else []) + layers["over_head"]
    ids = [p["id"] for p in parts]
    assert len(ids) == len(set(ids)), ids

    # --- the skeleton, on the document
    neck = ((sn[0] + sf[0]) / 2, (sn[1] + sf[1]) / 2)
    pelvis = ((S["hip_near"][0] + S["hip_far"][0]) / 2, (S["hip_near"][1] + S["hip_far"][1]) / 2)
    joints = {"head": S["head"], "neck": neck, "pelvis": pelvis, "shoulder_near": sn, "shoulder_far": sf, "hand_near": h_c, "hand_far": hf_c,
              "hip_near": S["hip_near"], "hip_far": S["hip_far"], "foot_near": S["foot_near"], "foot_far": S["foot_far"],
              "pack": S["pack"], "feeler_root": S["feeler_root"], "feeler_far_root": S["feeler_far_root"]}
    bones = [["shoulder_near", "shoulder_far"], ["neck", "head"], ["neck", "pelvis"], ["hip_near", "hip_far"], ["shoulder_near", "hand_near"], ["shoulder_far", "hand_far"],
             ["hip_near", "foot_near"], ["hip_far", "foot_far"], ["neck", "pack"], ["pack", "feeler_root"], ["pack", "feeler_far_root"]]
    skeleton = {"joints": {k: [r2(v[0]), r2(v[1])] for k, v in joints.items()}, "bones": bones}

    # --- groups a clip moves together
    head_group = ["head"] + (["visor"] if C["visor"] else []) + ["pack", "feeler_far"] + (["feeler"] if C["feeler"] else [])
    body_group = ["cloak", "cape", "organ"]
    for pid, fol in follow.items():
        if fol == "head": head_group.append(pid)
        elif fol == "body": body_group.append(pid)
    arm_pieces = [("arm", a_c), ("hand", h_c)] + [(p["id"], tuple(p["at"])) for p in layers["in_hand"] if follow[p["id"]] in ("arm", "flutter_arm")]
    arm_far_pieces = [("arm_far", af_c), ("hand_far", hf_c)] + [(p["id"], tuple(p["at"])) for L in layers.values() for p in L if follow[p["id"]] == "arm_far"]
    foot_followers = {"foot": [p["id"] for L in layers.values() for p in L if follow[p["id"]] == "foot"],
                      "foot_far": [p["id"] for L in layers.values() for p in L if follow[p["id"]] == "foot_far"]}

    def gait(w, march=False):
        tr = []
        up = [-w["bob"] * (0.5 - 0.5 * math.cos(4 * math.pi * t)) for t in TS]
        for pid in head_group: tr.append(track(pid, "y", up))
        for pid in body_group: tr.append(track(pid, "y", [u * 0.6 for u in up]))
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
        if I["feelers"] != "still":
            if C["feeler"]: tr.append(track("feeler", "rot", [-8 * math.sin(4 * math.pi * t - 0.9) for t in TS]))
            tr.append(track("feeler_far", "rot", [7 * math.sin(4 * math.pi * t - 0.9) for t in TS]))
        return tr

    def walk():
        return {"description": "contact and passing, twice: the helmet carries the bob, the feet swing under the hem and lift on the swing, the hem sways, the arms turn about their shoulders against the foot on their side, and the dead feelers lag behind the box they are rooted in",
                "duration": W["duration"], "tracks": gait(W)}
    def idle():
        if I["march"]:
            m = dict(W); m.update({"stride": 1.1, "lift": 0.8, "bob": 0.6, "sway": 1.2, "arm_swing": 6, "lurch": 0})
            return {"description": "never still: a march on the spot — do not stop (K033)", "duration": I["duration"], "tracks": gait(m)}
        tr = [key3(p, "y", 0, -1.0) for p in head_group]
        tr += [key3(p, "y", 0, -0.5) for p in body_group + [pid for pid, _ in arm_pieces] + [pid for pid, _ in arm_far_pieces]]
        if I["feelers"] == "sweep":
            if C["feeler"]: tr.append({"part": "feeler", "prop": "rot", "keys": [[0, 0], [0.35, 12], [0.7, -8], [1, 0]]})
            tr.append({"part": "feeler_far", "prop": "rot", "keys": [[0, 0], [0.4, -10], [0.75, 7], [1, 0]]})
        elif I["feelers"] == "one":  # only the far one is still a feeler
            tr.append({"part": "feeler_far", "prop": "rot", "keys": [[0, 0], [0.4, -10], [0.75, 7], [1, 0]]})
        for pid, fol in follow.items():
            if fol == "flutter_arm": tr.append({"part": pid, "prop": "rot", "keys": [[0, 0], [0.3, 6], [0.7, -6], [1, 0]]})
        desc = {"sweep": "the body breathes under the coat; the dead feelers keep sweeping for a signal that never comes",
                "still": "the body breathes under the coat; the feelers do not move — this emitter never once worked (S004)",
                "one": "the body breathes under the coat; one feeler still sweeps, the other turned to stone in its tube (R048)"}[I["feelers"]]
        return {"description": desc, "duration": I["duration"], "tracks": tr}

    return {
        "id": f"ss.char.{name}", "name": name.capitalize(), "description": row["description"],
        "tags": ["char"], "size": [32, 32], "meta": {"radius": 11},
        "parts": parts, "skeleton": skeleton, "animations": {"idle": idle(), "walk": walk()},
    }

# ============================================================== 3. the eight, one row each
def P_(id, at, shape, fill, rot=None, stroke=None):
    p = {"id": id, "at": [r2(at[0]), r2(at[1])], "shape": shape, "fill": fill}
    if rot is not None: p["rot"] = rot
    if stroke: p["stroke"] = stroke
    return p
rect = lambda w, h, corner=0.5: {"kind": "rect", "w": w, "h": h, "corner": corner}
ell = lambda rx, ry: {"kind": "ellipse", "rx": rx, "ry": ry}
circ = lambda r: {"kind": "circle", "r": r}
poly = lambda pts: {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in pts]}

SHARED = ("The body is the roster's walker — a sealed frost coat as the one mass, a helmet a third of the height that overlaps a shoulder line tilted for a body facing the viewer's front-right, the near arm at the left flank in front of the coat and the far arm behind it, two feet under a rounded hem, the dead organ worn as the mantle's clasp in the same place on all eight, and the emitter behind the far shoulder with its two dead feelers swept back past the helmet as the crown of the silhouette. Drawn from one skeleton (docs/character-rig-guide.md) by scripts/walker.py; flat token fills; radius 11.")

CHARACTERS = {
    "arin": {
        "pack_w": 5.0, "pack_h": 5.2,
        "extras": lambda c: [("behind", P_("rack", (c["S"]["pack"][0] - 3.3, c["S"]["pack"][1] + 0.8), rect(2.2, 4.0), "$steel.light", stroke=hair), "head")],
        "description": "The first expedition, on the day the last cartridge went in (A047). The prototype emitter is the biggest box any of the eight carries, its cartridge rack beside it. What the log has already measured shows in one place: the hands, gone dark and hard, the saw does not mark them (A052) — the Molt's slate, the first of the body to lose its blood. " + SHARED,
    },
    "sol": {
        "head_shape": "egg", "head_r": (4.6, 5.0), "head_fill": "$skin", "visor": False,
        "pose": {"coat_lean": 8}, "cloak_sx": 0.88, "hem": -1.2, "pack_w": 3.6, "pack_h": 3.8,
        "walk": {"duration": 0.46, "stride": 3.0, "bob": 1.6}, "idle": {"feelers": "still"},
        "extras": lambda c: [
            ("over_head", P_("hair", (c["head"][0] - 1.2, c["head"][1] - 3.0), ell(3.9, 2.2), "$slate.dark", rot=-14), "head"),
            ("over_coat", P_("helmet_hung", (-5.4, 8.0), ell(2.5, 2.2), "$frost.light2", stroke=hair), "body"),
            ("over_coat", P_("helmet_hung_visor", (-4.6, 8.3), rect(2.2, 0.9, 0.4), "$ink"), "body"),
            ("over_coat", P_("pouch", (5.6, 7.8), rect(3.0, 3.2, 0.8), "$timber", stroke=hair), "body"),
            ("over_coat", P_("cap", (6.0, 5.7), circ(1.3), "$pink"), "body"),
        ],
        "description": "The scout sent out alone. The helmet came off on day two (S002) and hangs from the hip now, found and not put on (S009); the issued emitter never once worked, so its feelers never move (S004); a pouch of fungi with a pink cap showing is what gets Sol past the swarm (S003). The one bare head of the eight, the body pitched forward and thin — faster than they are (S009), and short of health for it. " + SHARED,
    },
    "haram": {
        "head_shape": "box", "head_r": (5.3, 5.2), "visor_w": 7.2,
        "pose": {"coat_lean": 3}, "cloak_sx": 1.15, "arm_w": 3.4, "arm_far_w": 3.0,
        "walk": {"duration": 0.66, "bob": 1.0, "lurch": 2.2},
        "extras": lambda c: [
            ("behind", P_("stake_a", (-8.6, -9.0), rect(1.0, 9.0, 0.3), "$timber", rot=-26), "head"),
            ("behind", P_("stake_b", (-7.2, -9.6), rect(1.0, 8.4, 0.3), "$timber.dark", rot=-16), "head"),
            ("behind", P_("stake_c", (-9.9, -7.9), rect(1.0, 8.0, 0.3), "$timber", rot=-34), "head"),
            ("behind", P_("tube", (-9.0, 1.5), rect(2.2, 6.4, 1.0), "$bone", stroke=hair), "body"),
            ("over_cape", P_("plate", (c["sn"][0] + 0.6, c["sn"][1] + 0.4), ell(3.2, 1.9), "$husk", rot=-8, stroke=hair), "body"),
        ],
        "description": "The survey. Twenty-six benchmarks went in (H001) and the stakes ride on the back with the map tube, the widest shoulders of the eight under a squared-off helmet. The husk shell scraped into the mark II emitter (H027) is coming through: a plate of bleached bone over the near shoulder, and the walk has the Husk's lurch in it — four kilos up on the same ration, pulse thirty-eight (H043). Armour, and slower for it. " + SHARED,
    },
    "mir": {
        "skeleton": {"head": (3.0, -6.6), "foot_near": (-2.4, 13.1), "foot_far": (4.2, 12.5), "hip_near": (-2.6, 12.0), "hip_far": (4.0, 11.2)},
        "pose": {"coat_lean": 6}, "cloak_sx": 1.08,
        "walk": {"duration": 0.6, "bob": 0.0, "lift": 0.8},
        "extras": lambda c: [
            ("behind", P_("wall", (-3.5, -7.6), poly([(-3.5, -3.0), (3.2, -3.4), (3.6, 2.6), (-3.4, 3.0)]), "$rust", rot=-8, stroke=hair), "head"),
            ("behind", P_("wall_crack", (-3.6, -7.4), rect(3.6, 0.6, 0.2), "$rust.dark", rot=22), "head"),
            ("over_cape", P_("cord", (0.4, -1.0), rect(1.1, 9.0, 0.4), "$bone", rot=-28), "body"),
        ],
        "description": "The burrow, walked from the inside down to the queen. A palm-sized piece of its wall rides on the back where the emitter used to be, warm half a month on, chewing inside it at night (M038, M042), corded across the chest. The body has the nest's posture: head low and forward, a wide stance, and a walk with no bounce in it — the Porter's haul, twenty-nine levels of it (M035). " + SHARED,
    },
    "kano": {
        "feeler_rot": -26, "feeler_far_rot": -70, "feeler_scale": (0.55, 0.76),
        "pose": {"coat_lean": 4}, "cloak_sx": 0.92, "foot_h": 3.4, "foot_far_h": 3.0,
        "walk": {"duration": 0.5, "stride": 3.0}, "idle": {"duration": 0.7, "march": True},
        "extras": lambda c: [
            ("behind", P_("crystal", (-7.8, -8.6), poly([(-1.1, 2.8), (1.1, 2.4), (0.7, -2.6), (-0.8, -3.0)]), "$silent", rot=-22, stroke=hair), "head"),
            ("feet_over", P_("gaiter", (c["foot"][0], c["foot"][1] - 1.0), rect(4.8, 1.0, 0.3), "$steel"), "foot"),
            ("feet_over", P_("gaiter_far", (c["foot_far"][0], c["foot_far"][1] - 0.9), rect(4.2, 0.9, 0.3), "$steel"), "foot_far"),
        ],
        "description": "The patrols, and the rules that came out of them: do not stop (K033). The twelfth emitter has crystal grown out of its tube (K030), and the two feelers stand the widest apart of the eight — the first sign of a body that is becoming two (Lance, Vermis duplex). Narrow coat, tall gaitered boots, the longest stride, and no idle at all: standing still, Kano marches on the spot. " + SHARED,
    },
    "eden": {
        "skeleton": {"head": (2.0, -7.0)},
        "idle": {"duration": 1.6},
        "extras": lambda c: [
            ("over_cape", P_("throat", (5.8, -0.4), ell(3.5, 2.4), "$spore", rot=-12, stroke=hair), "body"),
            ("over_coat", P_("jar", (5.4, 7.6), rect(2.8, 3.6, 0.6), "$silent", stroke=hair), "body"),
            ("over_coat", P_("jar_cap", (5.4, 5.6), rect(3.0, 0.9, 0.3), "$slate"), "body"),
            ("over_coat", P_("seed", (5.4, 8.0), poly([(-0.6, 1.2), (0.7, 1.0), (0.3, -1.3), (-0.4, -1.1)]), "$frost.light2"), "body"),
            ("over_coat", P_("patch", (-3.6, 6.2), rect(2.6, 2.0, 0.5), "$moss", rot=12), "body"),
            ("over_coat", P_("patch_b", (2.2, 10.0), rect(2.2, 1.8, 0.5), "$moss", rot=-8), "body"),
        ],
        "description": "The long station: six years of watching what grows. A fingertip of royal jelly in place of the last cartridge (E093), and the throat under the helmet has begun to swell teal — the Gland's sac, the queen's smell on its way out as spit. The specimen jar on the coat holds number twelve, the seed that came up as two joints of crystal (E140); the coat is patched with moss where six years wore through it. The slowest breath of the eight. " + SHARED,
    },
    "rowan": {
        "feeler": False, "hand_r": (2.7, 2.9), "hand_fill": "$carapace", "arm_w": 3.6,
        "cloak_sx": 1.1, "walk": {"duration": 0.66, "bob": 0.9, "arm_swing": 10}, "idle": {"feelers": "one"},
        "extras": lambda c: [
            ("behind", P_("stone_feeler", (-8.2, -9.4), rect(1.4, 8.6, 0.6), "$sand", rot=-40, stroke=hair), "head"),
            ("in_hand", P_("knuckles", (c["hand"][0], c["hand"][1] + 0.7), rect(2.6, 0.8, 0.3), "$carapace.dark"), "arm"),
            ("over_coat", P_("chisel", (5.9, 8.4), rect(1.2, 4.4, 0.3), "$steel", rot=16, stroke=hair), "body"),
        ],
        "description": "The ruins, and who built them. The near hand is the only big one of the eight and the colour of the Soldier's plate: since the stone bowl, the right arm is stronger (R015) and the little finger folded to fit the grooves does not straighten (R053). One feeler is a rod of warm stone — the emitter's tube turned to stone from the inside (R048) — and only the other still sweeps. A chisel at the coat. Broad, slow, and the last to be moved by anything. " + SHARED,
    },
    "teo": {
        "visor_h": 3.4, "hand_fill": "$chitin", "hand_far_fill": "$chitin.dark",
        "extras": lambda c: [
            ("behind", P_("satchel", (-8.0, 3.2), rect(6.6, 5.2, 0.8), "$bone", stroke=hair), "body"),
            ("behind", P_("satchel_flap", (-8.0, 1.2), rect(6.6, 1.6, 0.5), "$bone.dark"), "body"),
            ("behind", P_("bloom", (c["S"]["feeler_root"][0] + 0.2, c["S"]["feeler_root"][1] - 0.4), circ(1.2), "$pink"), "head"),
            ("in_hand", P_("page", (c["hand"][0] + 1.0, c["hand"][1] - 0.6), rect(2.6, 3.2, 0.2), "$silent", rot=-18, stroke=hair), "flutter_arm"),
            ("over_head", P_("filter", (c["head"][0] + 4.8, c["head"][1] + 2.6), circ(1.4), "$slate", stroke=hair), "head"),
        ],
        "description": "The archive. Ninety-eight pages picked up one at a time (T034), a flat satchel of them on the back, and one in the hand; the hands leave wet iron on paper (the Mite's smell), which is why a mite carries a page off (T003). The helmet stays on with a filter can at the jaw (T006), and a flower mite has bloomed pink in the emitter's tube (T017). One more projectile, less on each. " + SHARED,
    },
}
if __name__ == "__main__":
    wanted = sys.argv[1:] or list(CHARACTERS)
    for name in wanted:
        row = CHARACTERS[name]
        doc = build(name, row)
        out = f"/home/user/PolyGraphics/apps/ss/assets/ss-char-{name}.json"
        json.dump(doc, open(out, "w"), indent=2)
        print(f"wrote {out}: {len(doc['parts'])} parts, walk {len(doc['animations']['walk']['tracks'])} tracks, idle {len(doc['animations']['idle']['tracks'])}")
