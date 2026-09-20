"""The walkers' rig — one script, one self-contained document per playable character.

    python3 scripts/walker.py            # rewrites apps/ss/assets/ss-char-arin.json
    python3 scripts/walker.py <out.json> # or somewhere else, to look at

Why a script and not a `use`: an animation only addresses the document's own
parts, and a `use` part is one node whose insides no track can reach — a shared
body composed by `use` could breathe but never walk. The roster's walks agree
with each other because they came out of one script of two-link legs and hinged
chains; this is that script for the eight survivors. Two-link limbs hinged at hip
and shoulder are posed the way the adapters pose them (rot about the part's own
origin, plus the x/y its offset from the joint sweeps), sampled onto 13 linear
keys like the roster's clips. The antenna and the organ stay `use` parts, moved
whole, as the eight shells did.

First sketch: Arin only. The other seven are the same rig with a row of
parameters each — see the game's docs/character-redesign-plan.md, section 3.2.
"""

import json, math, sys

R = lambda d: math.radians(d)
def rot(v, deg):
    c, s = math.cos(R(deg)), math.sin(R(deg))
    return (v[0]*c - v[1]*s, v[0]*s + v[1]*c)
def add(a, b): return (a[0]+b[0], a[1]+b[1])
def sub(a, b): return (a[0]-b[0], a[1]-b[1])
def r2(x): return round(x, 2)

N = 12  # 13 keys, t = i/12
TS = [i / N for i in range(N + 1)]

# ---------------------------------------------------------------- the rig
# Facing +x, +y down, origin at canvas centre. Hips and shoulders are the joints.
HIP_N, HIP_F = (2.9, 4.3), (-1.5, 4.0)
SHO_N, SHO_F = (4.3, -4.2), (-3.7, -4.4)
THIGH, SHIN = 5.0, 5.2
UARM, FARM = 5.2, 5.0

def limb_chain(joint, l1, l2, w1, w2, fill, stroke, ids, tapered_foot=False):
    """Base-pose parts for a two-link limb hanging straight down from `joint`."""
    c1 = add(joint, (0, l1 / 2))
    knee = add(joint, (0, l1))
    c2 = add(knee, (0, l2 / 2))
    p1 = {"id": ids[0], "at": [r2(c1[0]), r2(c1[1])], "shape": {"kind": "rect", "w": w1, "h": l1, "corner": r2(w1/2.4)}, "fill": fill}
    if tapered_foot:
        hw = w2 / 2
        p2 = {"id": ids[1], "at": [r2(c2[0]), r2(c2[1])],
              "shape": {"kind": "poly", "points": [[-hw, -l2/2], [hw, -l2/2], [hw, l2/2 - 1.6], [hw + 1.6, l2/2], [-hw, l2/2]]}, "fill": fill}
    else:
        p2 = {"id": ids[1], "at": [r2(c2[0]), r2(c2[1])], "shape": {"kind": "rect", "w": w2, "h": l2, "corner": r2(w2/2.4)}, "fill": fill}
    if stroke:
        p1["stroke"] = stroke; p2["stroke"] = stroke
    return p1, p2, (c1, knee, c2)

def chain_deltas(joint, c1, knee0, c2, th, ka, extra=None, extra0=None):
    """Deltas (dx, dy, rot) for link 1 (rot th about joint) and link 2 (rot th+ka about the swept knee).
    `extra` = a third rigid piece on link 2 (a hand)."""
    c1n = add(joint, rot(sub(c1, joint), th))
    knee = add(joint, rot(sub(knee0, joint), th))
    c2n = add(knee, rot(sub(c2, knee0), th + ka))
    out = [(sub(c1n, c1), th), (sub(c2n, c2), th + ka)]
    if extra0 is not None:
        en = add(knee, rot(sub(extra0, knee0), th + ka))
        out.append((sub(en, extra0), th + ka))
    return out

def track(part, prop, vals, ease="linear"):
    return {"part": part, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(TS, vals)], "ease": ease}

# ---------------------------------------------------------------- base parts
frost_near = "$frost"; frost_far = "$frost.dark"
hair = {"color": "$ink", "width": "hair"}; thin = {"color": "$ink", "width": "thin"}

lf1, lf2, (lf_c1, lf_knee, lf_c2) = limb_chain(HIP_F, THIGH, SHIN, 3.5, 3.1, frost_far, None, ("leg_far_thigh", "leg_far_shin"), tapered_foot=True)
ln1, ln2, (ln_c1, ln_knee, ln_c2) = limb_chain(HIP_N, THIGH, SHIN, 3.9, 3.5, frost_near, hair, ("leg_thigh", "leg_shin"), tapered_foot=True)
af1, af2, (af_c1, af_elb, af_c2) = limb_chain(SHO_F, UARM, FARM, 3.0, 2.7, frost_far, None, ("arm_far_upper", "arm_far_fore"))
an1, an2, (an_c1, an_elb, an_c2) = limb_chain(SHO_N, UARM, FARM, 3.3, 3.0, frost_near, hair, ("arm_upper", "arm_fore"))

HAND_N0 = add(an_elb, (0, FARM + 0.9)); HAND_F0 = add(af_elb, (0, FARM + 0.8))

torso = {"id": "torso", "at": [0.4, -0.6], "shape": {"kind": "poly",
         "points": [[5.2, -5.4], [-4.6, -5.6], [-6.0, -0.4], [-4.8, 4.8], [4.6, 5.0], [6.2, -0.2]]},
         "fill": "$frost", "stroke": thin}
belt = {"id": "belt", "at": [0.5, 3.2], "shape": {"kind": "rect", "w": 10.6, "h": 1.4, "corner": 0.4}, "fill": "$slate"}
pack = {"id": "pack", "at": [-6.9, -0.6], "shape": {"kind": "rect", "w": 4.4, "h": 8.6, "corner": 1.0}, "fill": "$slate", "stroke": hair}
head = {"id": "head", "at": [1.6, -10.1], "shape": {"kind": "ellipse", "rx": 4.6, "ry": 4.3}, "fill": "$frost.light", "stroke": thin}
visor = {"id": "visor", "at": [3.9, -10.3], "shape": {"kind": "rect", "w": 4.0, "h": 1.8, "corner": 0.7}, "fill": "$ink"}
organ = {"id": "organ", "at": [0.5, -2.6], "use": "ss.lib.organ", "variant": "dead", "scale": 0.62}
feeler_far = {"id": "feeler_far", "at": [-7.9, -4.2], "rot": -50, "scale": [0.6, 0.78], "use": "ss.lib.antenna", "variant": "dead"}
feeler = {"id": "feeler", "at": [-5.8, -4.4], "rot": -24, "scale": [0.6, 0.78], "use": "ss.lib.antenna", "variant": "dead"}

# ---------------------------------------------------------------- Arin's own
rack = {"id": "rack", "at": [-9.9, 0.9], "shape": {"kind": "rect", "w": 2.2, "h": 5.4, "corner": 0.5}, "fill": "$steel.light", "stroke": hair}
strap = {"id": "strap", "at": [-1.4, -2.4], "rot": 28, "shape": {"kind": "rect", "w": 1.3, "h": 10.8, "corner": 0.4}, "fill": "$slate"}
hand_far = {"id": "hand_far", "at": [r2(HAND_F0[0]), r2(HAND_F0[1])], "shape": {"kind": "ellipse", "rx": 1.5, "ry": 1.7}, "fill": "$slate.dark"}
hand = {"id": "hand", "at": [r2(HAND_N0[0]), r2(HAND_N0[1])], "shape": {"kind": "ellipse", "rx": 1.8, "ry": 2.0}, "fill": "$slate.dark", "stroke": hair}

parts = [feeler_far, pack, rack, af1, af2, hand_far, lf1, lf2, ln1, ln2, torso, strap, belt, organ, head, visor, an1, an2, hand, feeler]

# ---------------------------------------------------------------- clips
def walk(A_leg=24, K_knee=34, A_arm=17, E_elb=22, bob=1.2, stride_phase=0.0):
    tracks = []
    bobs = [-bob * (0.5 - 0.5 * math.cos(4 * math.pi * t)) for t in TS]
    def leg(joint, c1, knee0, c2, ids, phase):
        d1x, d1y, d1r, d2x, d2y, d2r = [], [], [], [], [], []
        for t, b in zip(TS, bobs):
            th = -A_leg * math.sin(2 * math.pi * (t + phase))
            ka = K_knee * (0.5 + 0.5 * math.cos(2 * math.pi * (t + phase))) ** 2
            (d1, r1), (d2, r2_) = chain_deltas(joint, c1, knee0, c2, th, ka)
            d1x.append(d1[0]); d1y.append(d1[1] + b * 0.5); d1r.append(r1)
            d2x.append(d2[0]); d2y.append(d2[1] + b * 0.5); d2r.append(r2_)
        tracks.extend([track(ids[0], "x", d1x), track(ids[0], "y", d1y), track(ids[0], "rot", d1r),
                       track(ids[1], "x", d2x), track(ids[1], "y", d2y), track(ids[1], "rot", d2r)])
    def arm(joint, c1, elb0, c2, hand0, ids, phase):
        cols = [[] for _ in range(9)]
        for t, b in zip(TS, bobs):
            th = A_arm * math.sin(2 * math.pi * (t + phase))
            ka = -E_elb * (0.55 + 0.45 * math.sin(2 * math.pi * (t + phase)))
            (d1, r1), (d2, r2_), (d3, r3) = chain_deltas(joint, c1, elb0, c2, th, ka, True, hand0)
            for col, v in zip(cols, [d1[0], d1[1] + b, r1, d2[0], d2[1] + b, r2_, d3[0], d3[1] + b, r3]): col.append(v)
        for i, pid in enumerate(ids):
            tracks.extend([track(pid, "x", cols[3*i]), track(pid, "y", cols[3*i+1]), track(pid, "rot", cols[3*i+2])])
    leg(HIP_N, ln_c1, ln_knee, ln_c2, ("leg_thigh", "leg_shin"), stride_phase)
    leg(HIP_F, lf_c1, lf_knee, lf_c2, ("leg_far_thigh", "leg_far_shin"), stride_phase + 0.5)
    arm(SHO_N, an_c1, an_elb, an_c2, HAND_N0, ("arm_upper", "arm_fore", "hand"), stride_phase + 0.5)
    arm(SHO_F, af_c1, af_elb, af_c2, HAND_F0, ("arm_far_upper", "arm_far_fore", "hand_far"), stride_phase)
    for pid in ["torso", "strap", "belt", "head", "visor", "organ", "pack", "rack", "feeler", "feeler_far"]:
        tracks.append(track(pid, "y", bobs))
    tracks.append(track("head", "rot", [3 * math.sin(4 * math.pi * t) for t in TS]))
    tracks.append(track("feeler", "rot", [-7 * math.sin(4 * math.pi * t + 0.6) for t in TS]))
    tracks.append(track("feeler_far", "rot", [6 * math.sin(4 * math.pi * t + 0.6) for t in TS]))
    return {"description": "a walk: two-link legs hinged at the hip with the knee folding through the forward swing, arms opposite, the body rising as each leg passes under it, and the dead feelers lagging a beat behind the pack they are rooted in",
            "duration": 0.6, "tracks": tracks}

def idle():
    bob = [[0, 0], [0.5, -1.0], [1, 0]]
    tracks = [{"part": p, "prop": "y", "keys": bob} for p in ["torso", "strap", "belt", "head", "visor", "organ", "pack", "rack", "arm_upper", "arm_fore", "hand", "arm_far_upper", "arm_far_fore", "hand_far", "feeler", "feeler_far"]]
    tracks.append({"part": "feeler", "prop": "rot", "keys": [[0, 0], [0.35, 13], [0.7, -9], [1, 0]]})
    tracks.append({"part": "feeler_far", "prop": "rot", "keys": [[0, 0], [0.4, -11], [0.75, 8], [1, 0]]})
    return {"description": "the body breathes; the dead feelers keep sweeping for a signal that never comes", "duration": 1.15, "tracks": tracks}

doc = {
    "id": "ss.char.arin",
    "name": "Arin",
    "description": "The first expedition, on the day the last cartridge went in (A047). A walker in the programme's issue suit — cold frost chitin-cloth, a helmet with one dark visor slit and no face — wearing the prototype emitter: the biggest box any of the eight carries, strapped to the back with its cartridge rack beside it, and two dead feelers rooted in its lid, sweeping a band with nothing on it. The dead organ is the emitter's bulb, worn on the harness strap across the chest, `ss.lib.organ#dead`, in the same place on all eight. What the log has already measured shows in one place: the hands. Dark and hard, and the saw does not mark them (A052) — the Molt's slate, the first of the body to lose its blood. Drawn at the roster's own density, not above it: twenty parts on a 32px canvas, three and a half heads tall, flat token fills, and nothing on it that would vanish at game scale. Gameplay radius 11. First sketch of the roster redesign — see the game's docs/character-redesign-plan.md.",
    "tags": ["char"],
    "size": [32, 32],
    "meta": {"radius": 11},
    "parts": parts,
    "animations": {"idle": idle(), "walk": walk()},
}
out = sys.argv[1] if len(sys.argv) > 1 else "/home/user/PolyGraphics/apps/ss/assets/ss-char-arin.json"
json.dump(doc, open(out, "w"), indent=2)
print("wrote", out, "parts:", len(parts), "walk tracks:", len(doc["animations"]["walk"]["tracks"]))
