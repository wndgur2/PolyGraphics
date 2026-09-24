"""The Courser — a wolf-spider hound that runs a ring round you and fences it.

    python3 scripts/courser.py        # rewrites apps/ss/assets/ss-enemy-courser.json

The field's second boss, redrawn for a new verb. It used to be a ringed worm
that braced and crossed 495px at you — the Lance's machine at a boss's size —
and the burrow's second boss was a centipede running the same machine, drawn
on this document's own rig. Two maps, one fight, two segmented lines. The game
now has it stop, read the air for where you are going, and *run a ring* around
that place with its own reek laid behind it (feelers: `EnemyType.corralInterval`).
So the body is built for that, and for nothing a line could do:

  - a runner: eight long legs, splayed, the one eight-legged body in the hive —
    every other thing here has six or none, and a spider is the silhouette a
    hound has in this world
  - a line-layer: the abdomen ends in spinnerets, and the hive's organ
    (`ss.lib.organ`) rides there rather than on the head — the thing that
    lays the fence is the thing that says who it is
  - a reader: two big eyes over a row of four, and pedipalps that drum while
    it reads, because the read is the tell

Seen from above along +x, and turned by the game rather than mirrored (it
runs a circle; there is no up to keep). Crimson because this slot always was:
the fence is drawn in `$blood` too, so what the body is and what it leaves on
the floor are the same colour.

Skeleton first: each leg is a hip on the carapace, a knee and a foot, and every
part of a leg hangs off those three. A clip turns hips and knees and the parts
are solved from them (forward kinematics), so a leg can never come apart at
the knee however far a clip swings it. The body's own masses — carapace,
abdomen, the abdomen's pattern, the organ — are placed off the pedicel, and the
abdomen swings about it.
"""
import json, math, os

R = math.radians
def r2(x): return round(x + 0.0, 2)

# ============================================================== skeleton
# Canvas 120×104, origin at the centre, +x forward, +y down (the "d" side).
PEDICEL = (-1.5, 0.0)
THORAX = (9.0, 0.0)
ABDOMEN = (-17.0, 0.0)
SPINNERET = (-36.0, 0.0)
# Hip, knee, ankle and foot for the up-side legs; the down side is the mirror.
# I is the front pair, IV the rear. IV is the longest, as in the animal, and I
# and II reach forward — a spider's front half is the half that finds things.
# From above a leg is an arch: the femur goes out to the knee, which is the
# widest point of it, and the rest turns forward or back from there.
LEGS = {
    "1": ((15.0, -6.5), (23.0, -23.0), (36.0, -30.0), (47.0, -31.5)),
    "2": ((11.0, -9.2), (12.5, -28.5), (22.5, -40.0), (29.0, -46.0)),
    "3": ((6.0, -9.8), (-3.5, -28.5), (-14.0, -39.5), (-21.0, -45.0)),
    "4": ((1.5, -8.2), (-10.0, -25.0), (-28.0, -33.0), (-41.0, -35.5)),
}
def mirror(p): return (p[0], -p[1])
def leg_joints(side, n):
    return tuple(LEGS[n]) if side == "u" else tuple(mirror(j) for j in LEGS[n])
SIDES = ("u", "d")
NS = ("1", "2", "3", "4")
# Tetrapod gait: I and III on one side step with II and IV on the other.
GROUP = {("u", "1"): 0, ("d", "2"): 0, ("u", "3"): 0, ("d", "4"): 0,
         ("d", "1"): 0.5, ("u", "2"): 0.5, ("d", "3"): 0.5, ("u", "4"): 0.5}

def ang(a, b): return math.atan2(b[1] - a[1], b[0] - a[0])
def dist(a, b): return math.hypot(b[0] - a[0], b[1] - a[1])
def rot_of(theta):
    """A rect's long axis is its +y; this is the `rot` that lays it along `theta`."""
    return math.degrees(math.atan2(-math.cos(theta), math.sin(theta)))

# ============================================================== parts
def P(id, at, shape, fill, rot=None, stroke=None, scale=None, opacity=None):
    p = {"id": id, "at": [r2(at[0]), r2(at[1])]}
    if rot is not None: p["rot"] = r2(rot)
    if scale is not None: p["scale"] = scale
    if opacity is not None: p["opacity"] = opacity
    p["shape"] = shape
    p["fill"] = fill
    if stroke: p["stroke"] = stroke
    return p
rect = lambda w, h, corner=None: {"kind": "rect", "w": r2(w), "h": r2(h), "corner": r2(corner if corner is not None else min(w, h) / 2)}
ell = lambda rx, ry: {"kind": "ellipse", "rx": r2(rx), "ry": r2(ry)}
circ = lambda r: {"kind": "circle", "r": r2(r)}
poly = lambda pts: {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in pts]}
INK_BOLD = {"color": "$ink", "width": "bold"}
INK_THIN = {"color": "$ink", "width": "thin"}

FEMUR_W = {"1": 3.9, "2": 3.8, "3": 3.8, "4": 4.2}
TIBIA_W = {"1": 3.0, "2": 2.9, "3": 2.9, "4": 3.2}
TARSUS_W = 2.1

def leg_parts(side, n, a_f=None, a_t=None, a_s=None):
    """A leg's parts with its femur, tibia and tarsus laid along `a_f`, `a_t`, `a_s` (world radians)."""
    h, k, a, f = leg_joints(side, n)
    lf, lt, ls = dist(h, k), dist(k, a), dist(a, f)
    a_f = ang(h, k) if a_f is None else a_f
    a_t = ang(k, a) if a_t is None else a_t
    a_s = ang(a, f) if a_s is None else a_s
    k2 = (h[0] + lf * math.cos(a_f), h[1] + lf * math.sin(a_f))
    a2 = (k2[0] + lt * math.cos(a_t), k2[1] + lt * math.sin(a_t))
    mid = lambda p, l, th: (p[0] + l / 2 * math.cos(th), p[1] + l / 2 * math.sin(th))
    return {
        f"leg_{side}{n}_femur": (mid(h, lf, a_f), rot_of(a_f)),
        f"leg_{side}{n}_knee": (k2, 0.0),
        f"leg_{side}{n}_tibia": (mid(k2, lt, a_t), rot_of(a_t)),
        f"leg_{side}{n}_tarsus": (mid(a2, ls, a_s), rot_of(a_s)),
    }

parts = []
# Legs first: seen from above they are under everything. The rear pair first,
# so the front legs cross over them where they meet at the hips.
for n in ("4", "3", "2", "1"):
    for side in SIDES:
        h, k, a, f = leg_joints(side, n)
        lp = leg_parts(side, n)
        (sc, srot), (tc, trot), (fc, frot) = (lp[f"leg_{side}{n}_{x}"] for x in ("tarsus", "tibia", "femur"))
        parts.append(P(f"leg_{side}{n}_tarsus", sc, rect(TARSUS_W, dist(a, f) + 1.0), "$blood.dark", rot=srot))
        parts.append(P(f"leg_{side}{n}_tibia", tc, rect(TIBIA_W[n], dist(k, a) + 1.4), "$blood", rot=trot))
        parts.append(P(f"leg_{side}{n}_femur", fc, rect(FEMUR_W[n], dist(h, k) + 1.6), "$blood.dark", rot=frot))
        parts.append(P(f"leg_{side}{n}_knee", k, circ(1.9), "$blood.light"))

ax, ay = ABDOMEN
# The abdomen: a fringe of hair under a smooth body, and the pattern on top.
def fur_outline(rx, ry, n=36, seed=11):
    """
    The abdomen's hair, as its silhouette: tufts round an ellipse at uneven
    lengths, longer and swept back toward the spinnerets — a thing that runs
    wears its hair the way it runs. Seeded so it is the same hair forever;
    uneven because a ring of even points is a cog, and a cog is a machine.
    """
    rnd = __import__("random").Random(seed)
    pts = []
    for i in range(n * 2):
        a = math.pi * i / n
        c, sn = math.cos(a), math.sin(a)
        if i % 2 == 0:
            pts.append((rx * c, ry * sn))
            continue
        back = max(0.0, -c)
        k = 1.08 + 0.08 * rnd.random() + 0.1 * back
        x, y = rx * k * c, ry * k * sn
        # Swept: the tip trails toward -x, most at the flanks.
        x -= 2.2 * abs(sn) * (0.6 + 0.4 * rnd.random())
        pts.append((x, y))
    return poly(pts)
parts.append(P("fur", ABDOMEN, fur_outline(19.8, 16.4), "$blood.dark", stroke=INK_BOLD))
parts.append(P("spinneret_u", (SPINNERET[0] + 0.6, -2.0), ell(2.6, 1.4), "$blood.dark2", rot=-12))
parts.append(P("spinneret_d", (SPINNERET[0] + 0.6, 2.0), ell(2.6, 1.4), "$blood.dark2", rot=12))
parts.append(P("abdomen", ABDOMEN, ell(19.4, 16.0), "$blood.light"))
# The heart mark, lanceolate, down the front half — the wolf spider's own
# pattern — and three chevrons down the back half, pointing the way it runs.
parts.append(P("heart", (-14.5, 0), poly([(10.0, 0), (5.0, -3.2), (-4.5, -2.4), (-10.0, 0), (-4.5, 2.4), (5.0, 3.2)]), "$blood.dark2"))
def chevron(w):
    return poly([(3.0, 0), (-1.0, -w), (-3.4, -w + 0.5), (0.5, 0), (-3.4, w - 0.5), (-1.0, w)])
for i, (x, w) in enumerate(((-26.0, 10.0), (-30.5, 8.0), (-34.5, 5.2))):
    parts.append(P(f"chevron_{i}", (x, 0), chevron(w), "$blood.dark2"))
for i, (x, y) in enumerate(((-9.5, 7.2), (-16.5, 8.6))):
    parts.append(P(f"spot_u{i}", (x, -y), circ(1.5), "$husk"))
    parts.append(P(f"spot_d{i}", (x, y), circ(1.5), "$husk"))
parts.append(P("gloss", (-12.5, -7.5), ell(8.5, 3.4), "$white@0.14", rot=-12))
# The organ, at the spinnerets: where the reek comes out is where it says who it is.
parts.append({"id": "organ", "at": [r2(SPINNERET[0] - 1.8), 0.0], "rot": 90, "use": "ss.lib.organ", "scale": 1.3})
# The waist.
parts.append(P("pedicel", PEDICEL, ell(3.4, 3.0), "$blood.dark2"))
# The carapace: dark, with a pale stripe down the middle and a groove in it.
parts.append(P("thorax", THORAX, ell(12.5, 10.5), "$blood", stroke=INK_BOLD))
parts.append(P("stripe", (7.5, 0), rect(17.0, 4.4, 2.2), "$husk"))
parts.append(P("fovea", (4.5, 0), rect(3.8, 1.3, 0.6), "$blood.dark2"))
# The fangs and their bases, under the eyes.
for side, s in (("u", -1), ("d", 1)):
    parts.append(P(f"chelicera_{side}", (22.0, s * 2.5), ell(3.3, 2.3), "$blood.dark2", stroke=INK_THIN))
    parts.append(P(f"fang_{side}", (25.3, s * 1.6), rect(1.4, 3.6, 0.7), "$husk", rot=s * -28))
# The palps: two short feelers that drum while it reads.
for side, s in (("u", -1), ("d", 1)):
    b0, b1, b2 = (19.5, s * 5.2), (25.5, s * 8.8), (31.0, s * 8.0)
    parts.append(P(f"palp_{side}", ((b0[0] + b1[0]) / 2, (b0[1] + b1[1]) / 2), rect(2.4, dist(b0, b1) + 1.0), "$blood.dark", rot=rot_of(ang(b0, b1))))
    parts.append(P(f"palp_{side}_tip", ((b1[0] + b2[0]) / 2, (b1[1] + b2[1]) / 2), rect(2.2, dist(b1, b2) + 0.8), "$dead", rot=rot_of(ang(b1, b2))))
# The eyes: two big ones over a row of four small. Only the big pair are named
# `eye_*`, which is what the game lights at night.
for side, s in (("u", -1), ("d", 1)):
    parts.append(P(f"eye_{side}", (15.8, s * 3.7), ell(2.5, 2.3), "$dead", stroke=INK_THIN))
    parts.append(P(f"eye_{side}_glint", (16.4, s * 3.7 - 0.7), circ(0.85), "$pink.light"))
for i, y in enumerate((-3.9, -1.3, 1.3, 3.9)):
    parts.append(P(f"ocellus_{i}", (19.9, y), circ(0.85), "$dead"))

ids = [p["id"] for p in parts]
assert len(ids) == len(set(ids)), "duplicate part ids"
BASE = {p["id"]: p for p in parts}

# ============================================================== motion
N_KEYS = 12
TS = [i / N_KEYS for i in range(N_KEYS + 1)]
def keys(vals, ts=TS): return [[r2(t), r2(v)] for t, v in zip(ts, vals)]
def track(part, prop, vals, ts=TS, ease="linear"):
    return {"part": part, "prop": prop, "keys": keys(vals, ts), "ease": ease}

def curl_sign(side, n):
    """The way a knee turns to bring its foot in toward the body's midline."""
    h, k, a, f = leg_joints(side, n)
    c = math.cos(ang(k, f))
    s = 1 if c >= 0 else -1
    return s if side == "u" else -s
def fwd_sign(side):
    """The way a hip turns to swing its leg forward (toward +x)."""
    return 1 if side == "u" else -1

def leg_tracks(pose, ts=TS):
    """
    `pose(side, n, t) -> (swing_deg, flex_deg[, ankle_deg])`: the hip's swing
    forward, the knee's curl in and the ankle's (half the knee's unless given),
    at clip time t. Solved to the parts as offsets from the rest pose —
    positions and rotations both — so a leg keeps its knee and its ankle.
    """
    out = []
    for n in NS:
        for side in SIDES:
            h, k, a, f = leg_joints(side, n)
            af0, at0, as0 = ang(h, k), ang(k, a), ang(a, f)
            base = leg_parts(side, n)
            series = {pid: ([], [], []) for pid in base}
            cs = curl_sign(side, n)
            for t in ts:
                got = pose(side, n, t)
                sw, fl = got[0], got[1]
                fa = got[2] if len(got) > 2 else fl * 0.5
                af = af0 + R(sw) * fwd_sign(side)
                at = at0 + R(sw) * fwd_sign(side) + R(fl) * cs
                as_ = as0 + R(sw) * fwd_sign(side) + R(fl + fa) * cs
                now = leg_parts(side, n, af, at, as_)
                for pid, ((cx, cy), rot) in now.items():
                    (bx, by), brot = base[pid]
                    dr = (rot - brot + 180) % 360 - 180
                    series[pid][0].append(cx - bx)
                    series[pid][1].append(cy - by)
                    series[pid][2].append(dr)
            for pid, (xs, ys, rs) in series.items():
                if max(map(abs, xs)) > 0.005: out.append(track(pid, "x", xs, ts))
                if max(map(abs, ys)) > 0.005: out.append(track(pid, "y", ys, ts))
                if "knee" not in pid and max(map(abs, rs)) > 0.005: out.append(track(pid, "rot", rs, ts))
    return out

ABDOMEN_PARTS = ["fur", "spinneret_u", "spinneret_d", "abdomen", "heart", "chevron_0", "chevron_1", "chevron_2",
                 "spot_u0", "spot_d0", "spot_u1", "spot_d1", "gloss", "organ"]
def pivot_of(pid):
    """Where a part turns and scales from: its own origin, which every abdomen part sits on."""
    return tuple(BASE[pid]["at"])
def abdomen_tracks(theta_deg, ts=TS, scale=None):
    """The abdomen swinging `theta_deg(t)` about the pedicel, optionally breathing `scale(t)`."""
    out = []
    for pid in ABDOMEN_PARTS:
        c = pivot_of(pid)
        xs, ys, rs = [], [], []
        for t in ts:
            th = R(theta_deg(t))
            dx, dy = c[0] - PEDICEL[0], c[1] - PEDICEL[1]
            if scale is not None:
                k = scale(t)
                dx, dy = dx * k, dy * k
            nx = PEDICEL[0] + dx * math.cos(th) - dy * math.sin(th)
            ny = PEDICEL[1] + dx * math.sin(th) + dy * math.cos(th)
            xs.append(nx - c[0]); ys.append(ny - c[1]); rs.append(theta_deg(t))
        if max(map(abs, xs)) > 0.005: out.append(track(pid, "x", xs, ts))
        if max(map(abs, ys)) > 0.005: out.append(track(pid, "y", ys, ts))
        if pid not in ("spot_u0", "spot_d0", "spot_u1", "spot_d1") and max(map(abs, rs)) > 0.005:
            out.append(track(pid, "rot", rs, ts))
        if scale is not None and pid not in ("organ",):
            out.append(track(pid, "scale", [scale(t) for t in ts], ts))
    return out

def palp_tracks(rot_deg, ts=TS):
    """Both palps turned `rot_deg(side, t)` about their roots on the face."""
    out = []
    for side, s in (("u", -1), ("d", 1)):
        root = (19.5, s * 5.2)
        for pid in (f"palp_{side}", f"palp_{side}_tip"):
            c = tuple(BASE[pid]["at"])
            xs, ys, rs = [], [], []
            for t in ts:
                th = R(rot_deg(side, t))
                dx, dy = c[0] - root[0], c[1] - root[1]
                xs.append(root[0] + dx * math.cos(th) - dy * math.sin(th) - c[0])
                ys.append(root[1] + dx * math.sin(th) + dy * math.cos(th) - c[1])
                rs.append(rot_deg(side, t))
            out += [track(pid, "x", xs, ts), track(pid, "y", ys, ts), track(pid, "rot", rs, ts)]
    return out

def cyc(t, phase=0.0): return math.sin(2 * math.pi * (t + phase))
def cyc_c(t, phase=0.0): return math.cos(2 * math.pi * (t + phase))

def gait(amp, flex, amp_by_leg=None, lean=None):
    def pose(side, n, t):
        ph = GROUP[(side, n)]
        a = amp * (amp_by_leg or {}).get(n, 1.0)
        # Forward while it recovers, back while it pushes; the knee curls only
        # on the recovery, which is the foot off the floor. `lean` is where each
        # pair sits for the whole cycle — a runner's legs are not a walker's.
        return (lean or {}).get(n, 0.0) + a * cyc(t, ph), flex * max(0.0, cyc_c(t, ph))
    return pose

animations = {}

# ---- trot: the walk, and the idle the game plays at whatever pace it is walking
TROT = 0.62
animations["trot"] = {
    "description": "The walk: eight legs in two alternating sets of four, the abdomen swinging a little behind the stride, the palps working and the organ breathing. The game runs it at the pace the body is actually covering, so standing winded after a lap it is a slow shift of weight.",
    "duration": TROT,
    "tracks": leg_tracks(gait(11.0, 10.0, {"2": 0.75, "3": 0.75}))
    + abdomen_tracks(lambda t: 3.0 * cyc(t, 0.25))
    + palp_tracks(lambda side, t: 7.0 * cyc(t, 0.0 if side == "u" else 0.5))
    + [track("organ", "scale", [1.0 + 0.07 * (0.5 + 0.5 * cyc(t)) for t in TS])],
}

# ---- run: the gallop it runs the ring at
RUN = 0.3
def run_abdomen(t): return 5.0 * cyc(2 * t)
animations["run"] = {
    "description": "Running the ring: the same two sets of four at full reach, knees snatching in on every recovery, the abdomen low and trailing, the palps swept back out of the way and the organ at the spinnerets burning — the line is coming out of it. Looped for as long as the lap lasts.",
    "duration": RUN,
    "tracks": leg_tracks(gait(15.0, 16.0, {"2": 0.7, "3": 0.7, "4": 0.85}, {"1": 4.0, "3": -4.0, "4": -8.0}))
    + abdomen_tracks(run_abdomen)
    + palp_tracks(lambda side, t: (-1 if side == "u" else 1) * -22.0 + 4.0 * cyc(t, 0 if side == "u" else 0.5))
    + [track("organ", "scale", [1.28 + 0.14 * (0.5 + 0.5 * cyc(2 * t)) for t in TS]),
       track("gloss", "opacity", [0.6 + 0.4 * (0.5 + 0.5 * cyc(t)) for t in TS])],
}

# ---- read: the tell. Held still, reading the air, then gathering to go.
READ_TS = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
def smoothstep(a, b, t):
    x = max(0.0, min(1.0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)
def read_pose(side, n, t):
    up = smoothstep(0.0, 0.3, t)
    gather = smoothstep(0.6, 1.0, t)
    if n == "1":
        # The front pair lifted and spread — a spider feeling the air with the
        # legs it hunts with — and brought back down onto the mark to go.
        return 22.0 * up * (1 - gather) + 3.0 * gather, -18.0 * up * (1 - gather) + 10.0 * gather
    # The rest settle in: knees in, weight down, ready to throw.
    return -4.0 * gather, 6.0 * up + 10.0 * gather
animations["read"] = {
    "description": "The tell, held still while the game draws the ring: the front legs lift and spread to feel the air, the palps drum fast, the abdomen sinks and the organ at the spinnerets swells — the reek being drawn up to be laid — and on the last beat the legs gather under it to throw the body onto the ring. Played once, stretched to the read; the run picks up from its last frame.",
    "duration": 0.8,
    "tracks": leg_tracks(read_pose, READ_TS)
    + abdomen_tracks(lambda t: 0.0, READ_TS, scale=lambda t: 1.0 - 0.05 * smoothstep(0.0, 0.3, t) + 0.09 * smoothstep(0.55, 1.0, t))
    + palp_tracks(lambda side, t: 14.0 * math.sin(2 * math.pi * 3.5 * t + (0 if side == "u" else math.pi)) * (1 - smoothstep(0.75, 1.0, t)), READ_TS)
    + [track("organ", "scale", [1.0 + 0.45 * smoothstep(0.2, 1.0, t) for t in READ_TS], READ_TS),
       track("eye_u_glint", "scale", [1.0 + 0.6 * smoothstep(0.0, 0.25, t) for t in READ_TS], READ_TS),
       track("eye_d_glint", "scale", [1.0 + 0.6 * smoothstep(0.0, 0.25, t) for t in READ_TS], READ_TS)],
}

# ---- death: the curl
DEATH_TS = [0, 0.08, 0.16, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 1.0]
def death_pose(side, n, t):
    c = smoothstep(0.0, 0.7, t)
    kick = math.sin(math.pi * min(1.0, t / 0.16)) * (1 if n in ("1", "3") else -1)
    # Every leg folding in over the body — the curl a spider dies in — with one
    # last kick out of step before it goes.
    return -18.0 * c + 8.0 * kick * (1 - c), 70.0 * c
animations["death"] = {
    "description": "It dies the way a spider does: one kick out of step, then every leg folds in over the body at the knee and stays folded; the abdomen shrinks, the organ at the spinnerets goes out and the eyes lose their light.",
    "duration": 0.9,
    "tracks": leg_tracks(death_pose, DEATH_TS)
    + abdomen_tracks(lambda t: 6.0 * smoothstep(0.1, 0.6, t), DEATH_TS, scale=lambda t: 1.0 - 0.14 * smoothstep(0.1, 0.8, t))
    + [track("organ", "opacity", [1.0 - 0.85 * smoothstep(0.05, 0.6, t) for t in DEATH_TS], DEATH_TS),
       track("eye_u_glint", "opacity", [1.0 - smoothstep(0.1, 0.5, t) for t in DEATH_TS], DEATH_TS),
       track("eye_d_glint", "opacity", [1.0 - smoothstep(0.1, 0.5, t) for t in DEATH_TS], DEATH_TS),
       track("thorax", "scale", [1.0 - 0.06 * smoothstep(0.1, 0.8, t) for t in DEATH_TS], DEATH_TS)],
}

# ============================================================== states
variants = {
    "enraged": {
        "description": "Phase two, where the ring starts closing all the way round: the value structure turns over. The carapace and the abdomen go dark and the hair stands off the abdomen in a black ruff, while the pattern that was the darkest thing on it — the heart mark and the chevrons — burns, and so do the knees and the stripe. The organ at the spinnerets is bigger: there is more of the line coming.",
        "scale": 1.06,
        "set": {
            "abdomen.fill": "$blood.dark2",
            "fur.fill": "$dead",
            "fur.scale": [1.16, 1.14],
            "heart.fill": "$coral.light",
            "chevron_0.fill": "$coral",
            "chevron_1.fill": "$coral",
            "chevron_2.fill": "$coral",
            "spot_u0.fill": "$white@heavy",
            "spot_d0.fill": "$white@heavy",
            "spot_u1.fill": "$white@heavy",
            "spot_d1.fill": "$white@heavy",
            "thorax.fill": "$blood.dark2",
            "stripe.fill": "$coral.light",
            "eye_u_glint.fill": "$coral.light",
            "eye_d_glint.fill": "$coral.light",
            "organ.scale": 1.55,
            **{f"leg_{s}{n}_knee.fill": "$coral" for s in SIDES for n in NS},
            **{f"leg_{s}{n}_femur.fill": "$blood.dark2" for s in SIDES for n in NS},
            **{f"leg_{s}{n}_tibia.fill": "$blood.dark2" for s in SIDES for n in NS},
        },
    },
    "final": {
        "description": "Phase three, the ring that draws in: it has laid more line than it had in it. The hair is gone, the abdomen has emptied to a pale shrunken bag with the pattern burnt out of it, and it is running on six legs — one gone from each side, out of step with each other, so the gait it runs the last rings on is a limp. Only the organ at the spinnerets is bigger, and white: the last of the reek, and all it has left.",
        "scale": 1.04,
        "set": {
            "fur.opacity": 0,
            "abdomen.fill": "$husk.dark",
            "abdomen.scale": [0.88, 0.82],
            "heart.fill": "$blood.dark2@soft",
            "chevron_0.fill": "$blood.dark2@soft",
            "chevron_1.fill": "$blood.dark2@soft",
            "chevron_2.fill": "$blood.dark2@soft",
            "spot_u0.opacity": 0,
            "spot_d0.opacity": 0,
            "spot_u1.opacity": 0,
            "spot_d1.opacity": 0,
            "gloss.opacity": 0,
            "thorax.fill": "$blood.dark2",
            "stripe.fill": "$husk.dark",
            "eye_d_glint.opacity": 0,
            "organ.scale": 1.75,
            "organ.variant": "faint",
            **{f"leg_u2_{p}.opacity": 0 for p in ("femur", "knee", "tibia", "tarsus")},
            **{f"leg_d4_{p}.opacity": 0 for p in ("femur", "knee", "tibia", "tarsus")},
        },
    },
}

# ============================================================== document
skeleton_joints = {"pedicel": PEDICEL, "thorax": THORAX, "abdomen": ABDOMEN, "spinneret": SPINNERET}
bones = [["thorax", "pedicel"], ["pedicel", "abdomen"], ["abdomen", "spinneret"]]
for n in NS:
    for side in SIDES:
        h, k, a, f = leg_joints(side, n)
        skeleton_joints[f"hip_{side}{n}"] = h
        skeleton_joints[f"knee_{side}{n}"] = k
        skeleton_joints[f"ankle_{side}{n}"] = a
        skeleton_joints[f"foot_{side}{n}"] = f
        bones += [["thorax", f"hip_{side}{n}"], [f"hip_{side}{n}", f"knee_{side}{n}"],
                  [f"knee_{side}{n}", f"ankle_{side}{n}"], [f"ankle_{side}{n}", f"foot_{side}{n}"]]

DESCRIPTION = (
    "The field's second arrival, the hive's hound: a wolf spider in crimson, and the one body in the hive with eight legs. "
    "It does not cross at you. It stops, reads the air for where you are going, and runs a ring round that place with its own reek laid "
    "on the floor behind it — the game draws that fence in this document's own `$blood` (feelers: `EnemyType.corralInterval`) — "
    "so it is drawn to be a runner, a reader and a line-layer, and nothing a line could be. "
    "Seen from above along +x and turned by the game rather than mirrored, since a thing that runs circles has no up to keep: "
    "eight long legs splayed round a small dark carapace with a pale stripe, a big round abdomen fringed with hair and marked with a heart "
    "and three chevrons pointing the way it runs, two big eyes over a row of four, fangs, and palps that drum. "
    "The hive's organ rides the spinnerets rather than the head — the thing that lays the fence is the thing that says who it is. "
    "The legs are built on a skeleton of hips, knees and feet and every clip turns those, so no swing can part a leg at the knee. "
    "`trot` is the walk and the idle, `read` the tell (front legs up, palps drumming, the organ swelling, then the gather to go), "
    "`run` the gallop it runs the ring at, looped for the length of the lap. "
    "`enraged` turns the value structure over — dark body, burning pattern, the hair standing; `final` has run itself out: bald, the "
    "abdomen emptied pale, a leg gone from each side and the organ white. Gameplay radius 40. The `death` clip is the curl."
)

doc = {
    "id": "ss.enemy.courser",
    "name": "Courser",
    "description": DESCRIPTION,
    "tags": ["enemy", "boss"],
    "size": [120, 104],
    "meta": {"radius": 40},
    "parts": parts,
    "variants": variants,
    "animations": animations,
    "skeleton": {"joints": {k: [r2(v[0]), r2(v[1])] for k, v in skeleton_joints.items()}, "bones": bones},
}

# ============================================================== the house format
def one(v): return json.dumps(v, ensure_ascii=False)
def write(doc, path):
    L = ["{"]
    L.append(f'  "id": {one(doc["id"])},')
    L.append(f'  "name": {one(doc["name"])},')
    L.append(f'  "description": {one(doc["description"])},')
    L.append(f'  "tags": {one(doc["tags"])},')
    L.append(f'  "size": {one(doc["size"])},')
    L.append(f'  "meta": {one(doc["meta"])},')
    L.append('  "parts": [')
    L.append(",\n".join(f"    {one(p)}" for p in doc["parts"]))
    L.append("  ],")
    L.append('  "variants": {')
    vs = []
    for name, v in doc["variants"].items():
        body = [f'    {one(name)}: {{', f'      "description": {one(v["description"])},']
        if "scale" in v: body.append(f'      "scale": {one(v["scale"])},')
        body.append('      "set": {')
        body.append(",\n".join(f"        {one(k)}: {one(val)}" for k, val in v["set"].items()))
        body.append("      }")
        body.append("    }")
        vs.append("\n".join(body))
    L.append(",\n".join(vs))
    L.append("  },")
    L.append('  "skeleton": {')
    L.append('    "joints": {')
    L.append(",\n".join(f"      {one(k)}: {one(v)}" for k, v in doc["skeleton"]["joints"].items()))
    L.append("    },")
    L.append(f'    "bones": {one(doc["skeleton"]["bones"])}')
    L.append("  },")
    L.append('  "animations": {')
    anims = []
    for name, a in doc["animations"].items():
        body = [f'    {one(name)}: {{', f'      "description": {one(a["description"])},', f'      "duration": {one(a["duration"])},', '      "tracks": [']
        body.append(",\n".join(f"        {one(t)}" for t in a["tracks"]))
        body.append("      ]")
        body.append("    }")
        anims.append("\n".join(body))
    L.append(",\n".join(anims))
    L.append("  }")
    L.append("}")
    open(path, "w").write("\n".join(L) + "\n")

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-courser.json")
    write(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(parts)} parts, {len(animations)} clips, {n_tracks} tracks")
