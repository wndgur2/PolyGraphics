"""The Pit's sand funnel — an antlion's trap, as a piece of ground.

    python3 scripts/funnel.py        # rewrites apps/ss/assets/ss-terrain-funnel.json

Feelers' fourth stage (개미지옥, Pit) digs these into its desert zones and, rarely,
its plains: a pit 150 world px in radius that drags everything on the ground
toward its middle, and an antlion buried in the middle that bites whatever
stays within 30px of it for a second (feelers `docs/pit-plan.md` §3.4). It is
not a body — it is a hole the ground has, the way `ss.terrain.tunnel` is — so
it is drawn at the size the run sees it, 1:1: a 320 canvas, `meta.radius` 150
the crest of the lip and `meta.throat` 30 the bite.

Top-down, lit from the upper left like the Sinkmaw's pit (that boss is the same
animal grown into a hole the size of a room; this is the one you find in the
sand by the dozen). The slope steps down in five bands from a pale thrown lip
to a throat that is a hole rather than a colour, and the bands between the lip
and the throat sit off-centre toward the light, so the wall on the far side of
the light is the wide lit one and the wall under it is narrow and in shadow.
Each step is doubled by a half-alpha ring so the cone reads as a slope and not
as a target: the Phaser bake flattens a gradient, so the pan's own trick.

What moves is what crosses the slope: tongues of sand sliding down it on
staggered clocks, faster as they fall and each on a slight twist so the
funnel turns as it drains, and three slump lines drawing in from the lip. A
circle scaled about its centre is the same circle, so nothing here relies on
the bands moving to read as a drain.

The antlion is two sickles and nothing else. They are hinged at their roots in
the throat, under a clot of wet sand, and in the drawing they stand just open
and just short of the lip: a thing you notice on the second look. `sense`
lifts them over the lip and spreads them; `bite` claps them shut.

Every clip's first frame is the drawing (every streak and slump at its own
phase), and `bite` ends on it, so any clip can hand to any other without the
sand jumping. The streaks' fades are the only thing a loop's first frame
states that the drawing does not.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import R, r2, lerp, smooth, cyc, poly, ell, circ, write_doc

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-terrain-funnel.json")

RIM, THROAT = 150.0, 30.0
LIGHT = (-0.6, -0.8)  # unit vector toward the light: upper left


def polar(r, a): return (r * math.cos(R(a)), r * math.sin(R(a)))
def r3(x): return round(x + 0.0, 3)
def r4(x): return round(x + 0.0, 4)


parts = []
def put(pid, at, shape, fill, **kw):
    p = {"id": pid}
    if at is not None and (at[0] or at[1]): p["at"] = [r2(at[0]), r2(at[1])]
    if kw.get("rot"): p["rot"] = r2(kw.pop("rot"))
    kw.pop("rot", None)
    p["shape"] = shape
    p["fill"] = fill
    for k, v in kw.items():
        if v is not None: p[k] = v
    parts.append(p)
    return p
def ring(r, w, frm=None, to=None):
    s = {"kind": "ring", "r": r2(r), "width": r2(w)}
    if frm is not None: s["from"], s["to"] = r2(frm), r2(to)
    return s


# ============================================================== the ground it is dug in
# Sand thrown out of the hole and lying on whatever floor the hole is in: two
# thin washes past the lip so the edge is spill, not a cut.
put("spill_far", None, circ(RIM + 9), "$sand@0.22")
put("spill", None, circ(RIM + 5), "$sand@0.4")
# The lip: the crest of thrown sand. Its outer face toward the light is lit,
# the face away from it drops into the ground's own shade.
put("lip", None, circ(RIM + 1), "$sand.light")
put("lip_warm", None, circ(RIM + 1), "$chitin@0.12")
put("lip_lit_wide", None, ring(RIM - 1, 7, 180, 300), "$chitin@0.16")
put("lip_lit", None, ring(RIM - 0.5, 4, 205, 275), "$husk@0.2")
put("lip_shade_wide", None, ring(RIM - 0.5, 6, 0, 120), "$sand.dark@0.3")
put("lip_shade", None, ring(RIM, 3, 20, 100), "$sand.dark@0.4")

# ============================================================== the slope
# Nine translucent discs stacked from the lip down to the throat, each a step
# darker than what it lies on, so the fall is a slope in small steps rather
# than a target in big ones (the Phaser bake flattens a gradient, so the pan's
# own trick). The ones between lip and throat sit toward the light — most in
# the middle of the slope, none at either end, so the lip and the throat stay
# concentric with the pull the game computes. Where the discs crowd, under the
# light, the wall is steep and dark; across from it they spread and it is lit.
BANDS = [142.0, 128.0, 114.0, 100.0, 87.0, 74.0, 62.0, 51.0, 42.0]
def lean(r):
    m = 9.0 * math.sin(math.pi * (r - THROAT) / (RIM - THROAT))
    return (LIGHT[0] * m, LIGHT[1] * m)
# The break of slope: where the lip stops and the fall starts. A hair of ink so
# the hole has an edge you can see from across the screen.
put("brink", lean(BANDS[0]), ring(BANDS[0] + 0.5, 2.0), "$ink@0.22")
for i, r in enumerate(BANDS):
    put(f"band_{i}", lean(r), circ(r), "$sand.dark2@0.16" if i < 5 else "$sand.dark2@0.22")
    if i in (1, 3, 5): put(f"band_{i}_warm", lean(r), circ(r - 4.0), "$rust@0.1")

# Light on the slope: the wall across from the light faces into it, the wall
# under it faces away. Three soft steps each, like the pan's swells.
for k, (r, a) in enumerate([(92.0, 0.06), (70.0, 0.06), (48.0, 0.07)]):
    put(f"wall_lit_{k}", (34.0, 42.0), circ(r), f"$chitin@{a}")
for k, (r, a) in enumerate([(80.0, 0.06), (58.0, 0.06), (38.0, 0.07)]):
    put(f"wall_shade_{k}", (-40.0, -50.0), circ(r), f"$ink@{a}")

# Grain, inside the lip only: a repeat scatters over a square, so two squares a
# quarter turn apart, each small enough that its corners stay under the lip.
put("grain_dark", None, None, "$sand.dark2@0.22")
parts[-1].pop("shape")
parts[-1]["repeat"] = {"of": {"kind": "ellipse", "rx": 3, "ry": 2}, "count": 150, "area": [196, 196], "seed": 7101,
                       "scaleRange": [0.4, 1.4], "jitterRot": True}
put("grain_pale", None, None, "$sand.light@0.3", rot=45)
parts[-1].pop("shape")
parts[-1]["repeat"] = {"of": {"kind": "ellipse", "rx": 2.6, "ry": 1.8}, "count": 130, "area": [196, 196], "seed": 7102,
                       "scaleRange": [0.4, 1.3], "jitterRot": True}
# ...and out on the lip, where a square cannot reach: a ring of grains laid by hand.
for i in range(18):
    a = i * 20.0 + 7.0 * math.sin(i * 2.3)
    r = RIM - 6.0 - 5.0 * ((i * 7) % 3)
    put(f"lip_grain_{i}", polar(r, a), ell(2.4, 1.5), "$sand.dark@0.45" if i % 3 else "$sand.light2@0.6", rot=a + 90)

# ============================================================== slump lines
# Three rings where the sand has let go, drawing in from the lip to the throat.
SLUMPS = [("slump_0", 0.0), ("slump_1", 1 / 3), ("slump_2", 2 / 3)]
SLUMP_R0, SLUMP_R1 = 136.0, 40.0
def slump_r(u): return lerp(SLUMP_R0, SLUMP_R1, u ** 1.25)
def slump_alpha(u): return smooth(0.0, 0.15, u) * (1 - smooth(0.7, 1.0, u))
for sid, ph in SLUMPS:
    put(sid, None, ring(SLUMP_R0, 2.4, 200, 520), "$sand.dark2@0.45", scale=r3(slump_r(ph) / SLUMP_R0))

# ============================================================== streaks
# Tongues of sand sliding in. Each is drawn along +x (the way it slides) with
# its head at its origin, so a streak shrinks toward the front it leads with.
# A lit tongue over its own lee, the lee a little downhill of it.
TONGUE = [(3.4, 0.0), (2.6, -2.4), (0.4, -3.4), (-5.0, -3.3), (-11.0, -2.8), (-17.0, -2.1), (-22.0, -1.5),
          (-25.0, -0.9), (-26.0, 0.0), (-25.0, 1.0), (-22.0, 1.6), (-17.0, 2.2), (-11.0, 2.9), (-5.0, 3.4),
          (0.4, 3.5), (2.6, 2.5)]
TWIST = 22.0  # degrees off the fall line: the sand spirals as it drains
N_STREAK = 16
STREAKS = []
for i in range(N_STREAK):
    a = i * 360.0 / N_STREAK + 9.0 * math.sin(i * 1.7)
    ph = (i * 0.618034) % 1.0
    r0 = 138.0 - 6.0 * ((i * 5) % 3)
    p0 = polar(r0, a)
    d = a + 180.0 + TWIST
    ux, uy = math.cos(R(d)), math.sin(R(d))
    # how far along the heading until the head is at the throat
    b = p0[0] * ux + p0[1] * uy
    c = r0 * r0 - (THROAT + 6.0) ** 2
    L = -b - math.sqrt(max(0.0, b * b - c))
    STREAKS.append({"id": f"streak_{i}", "p0": p0, "u": (ux, uy), "L": L, "ph": ph, "rot": d,
                    "pale": "$chitin@0.3" if i % 2 else "$sand.light@0.55"})
def streak_s(u): return u ** 1.35  # slow on the lip, faster as it falls
def streak_pos(st, u):
    s = streak_s(u) * st["L"]
    return (st["p0"][0] + st["u"][0] * s, st["p0"][1] + st["u"][1] * s)
def streak_scale(u): return lerp(1.0, 0.45, streak_s(u))
def streak_alpha(u): return smooth(0.0, 0.14, u) * (1 - smooth(0.78, 1.0, u))
LEE_OFF = 2.2  # the lee sits this far across the tongue, on its downhill (inner) side
for st in STREAKS:
    base = streak_pos(st, st["ph"])
    sc = r3(streak_scale(st["ph"]))
    # the lee: across the heading, toward the middle of the funnel
    nx, ny = -st["u"][1], st["u"][0]
    if nx * -base[0] + ny * -base[1] < 0: nx, ny = -nx, -ny
    st["lee"] = (nx * LEE_OFF, ny * LEE_OFF)
    put(st["id"] + "_lee", (base[0] + st["lee"][0], base[1] + st["lee"][1]), poly(TONGUE), "$sand.dark2@0.3",
        rot=st["rot"], scale=sc)
    put(st["id"], base, poly(TONGUE), st["pale"], rot=st["rot"], scale=sc)

# ============================================================== the throat
put("throat_lip", None, circ(THROAT + 6.0), "$sand.dark2")
put("throat_rim", None, circ(THROAT + 1.0), "$ink@heavy")
put("throat", (0.0, 0.0), circ(THROAT - 2.0), "$soil")
put("throat_deep", (0.6, 1.0), circ(THROAT - 11.0), "$ink")

# ============================================================== the antlion
# A pair of larva sickles, root at the origin, pointing up the screen, curving
# in at the tip, three teeth on the inside edge. Drawn for the left jaw; the
# right is its mirror.
SICKLE_PTS = [(-2.6, 1.0), (-3.4, -6.0), (-3.2, -12.0), (-2.0, -17.0), (0.2, -20.8), (3.0, -23.2), (6.0, -24.2),
              (7.4, -23.8), (5.0, -22.6), (2.8, -20.4), (1.6, -18.0), (3.2, -16.6), (1.2, -15.8), (0.8, -12.4),
              (2.6, -11.0), (0.8, -10.0), (1.0, -6.4), (2.2, -5.2), (1.0, -4.2), (2.4, 1.0)]
TIP_PTS = [(1.6, -18.0), (0.2, -20.8), (3.0, -23.2), (6.0, -24.2), (7.4, -23.8), (5.0, -22.6), (2.8, -20.4)]
JAW_LEN = 1.35  # the sickle above is 24 long; these are 33, so the tips stand at the throat's edge
SICKLE = [(x * JAW_LEN, y * JAW_LEN) for x, y in SICKLE_PTS]
TIP = [(x * JAW_LEN, y * JAW_LEN) for x, y in TIP_PTS]
def mirror(pts): return [(-x, y) for x, y in pts]
JAW_ROOT = {"l": (-6.0, 9.0), "r": (6.0, 9.0)}
JAW_REST = {"l": -20.0, "r": 20.0}  # a little open: the drawing
JAW_SIGN = {"l": -1.0, "r": 1.0}  # the way each opens
for s in ("l", "r"):
    f = (lambda p: p) if s == "l" else mirror
    put(f"jaw_{s}", JAW_ROOT[s], poly(f(SICKLE)), "$chitin.dark", rot=JAW_REST[s], stroke={"color": "$ink", "width": "hair"})
    put(f"jaw_{s}_tip", JAW_ROOT[s], poly(f(TIP)), "$husk.dark", rot=JAW_REST[s])
# Wet sand clotted over the head and the jaws' roots: all that shows of the animal is what stands out of it.
put("clot", (0.0, 10.0), ell(10.5, 6.0), "$sand.dark2")
put("clot_lit", (1.8, 11.2), ell(6.0, 2.6), "$sand.dark")

# Loose sand heaped on the throat's lip — what a bite throws. Uneven, because
# an even ring of heaps is a clock face.
PUFFS = []
for i, (a, rx, ry) in enumerate([(18.0, 6.0, 3.4), (74.0, 4.2, 2.6), (128.0, 5.4, 3.0), (171.0, 3.6, 2.2),
                                 (226.0, 5.0, 2.8), (291.0, 4.4, 2.6), (333.0, 3.4, 2.2)]):
    r = THROAT + 3.0 + 0.8 * ((i * 3) % 4)
    pid = f"puff_{i}"
    PUFFS.append((pid, a, r))
    put(pid, polar(r, a), ell(rx, ry), "$sand.light2@0.7", rot=a + 90)
# The lit edge of the throat, on the side facing the light: also the dust ring a bite throws off.
put("throat_lit", None, ring(THROAT + 2.5, 2.0, 330, 480), "$sand.light2@0.5")

# ============================================================== motion
def dense(n, extra=()):
    ts = {i / n for i in range(n + 1)} | set(extra)
    return sorted(t for t in ts if 0.0 <= t <= 1.0)

def cycle_keys(ph, n, fn):
    """Keys for a value that runs through a life u = (ph + t) mod 1 once a loop, cut where the life wraps."""
    tw = 1.0 - ph
    ts = dense(n, [tw] if 0 < tw < 1 else [])
    keys = []
    for t in ts:
        if abs(t - tw) < 1e-9 and 0 < tw < 1:
            keys.append([r4(t - 0.001), r3(fn(1.0 - 1e-6))])
            keys.append([r4(t), r3(fn(0.0))])
        else:
            keys.append([r4(t), r3(fn((ph + t) % 1.0))])
    return keys

def flow_tracks(n, alpha_mul=1.0):
    out = []
    for st in STREAKS:
        base = streak_pos(st, st["ph"])
        bs = streak_scale(st["ph"])
        for pid in (st["id"] + "_lee", st["id"]):
            out.append({"part": pid, "prop": "x", "keys": cycle_keys(st["ph"], n, lambda u, st=st, base=base: streak_pos(st, u)[0] - base[0]), "ease": "linear"})
            out.append({"part": pid, "prop": "y", "keys": cycle_keys(st["ph"], n, lambda u, st=st, base=base: streak_pos(st, u)[1] - base[1]), "ease": "linear"})
            out.append({"part": pid, "prop": "scale", "keys": cycle_keys(st["ph"], n, lambda u, bs=bs: streak_scale(u) / bs), "ease": "linear"})
            out.append({"part": pid, "prop": "opacity", "keys": cycle_keys(st["ph"], n, lambda u: min(1.0, streak_alpha(u) * alpha_mul)), "ease": "linear"})
    for sid, ph in SLUMPS:
        bs = slump_r(ph) / SLUMP_R0
        out.append({"part": sid, "prop": "scale", "keys": cycle_keys(ph, n, lambda u, bs=bs: slump_r(u) / SLUMP_R0 / bs), "ease": "linear"})
        out.append({"part": sid, "prop": "opacity", "keys": cycle_keys(ph, n, lambda u: min(1.0, slump_alpha(u) * alpha_mul)), "ease": "linear"})
    return out

def fn_tracks(pid, prop, ts, fn):
    return {"part": pid, "prop": prop, "keys": [[r4(t), r3(fn(t))] for t in ts], "ease": "linear"}

def jaw_tracks(ts, rot_fn, scale_fn, dy_fn=None):
    """`rot_fn(t)` is the opening past rest (positive = wider), the same for both jaws, signed per side."""
    out = []
    for s in ("l", "r"):
        for pid in (f"jaw_{s}", f"jaw_{s}_tip"):
            out.append(fn_tracks(pid, "rot", ts, lambda t, s=s: JAW_SIGN[s] * rot_fn(t)))
            out.append(fn_tracks(pid, "scale", ts, scale_fn))
            if dy_fn: out.append(fn_tracks(pid, "y", ts, dy_fn))
    return out

def streak_hold():
    """The streaks and slumps held on the loops' first frame: a one-shot that starts and ends there."""
    out = []
    for st in STREAKS:
        a0 = r3(streak_alpha(st["ph"]))
        for pid in (st["id"] + "_lee", st["id"]):
            out.append({"part": pid, "prop": "opacity", "keys": [[0, a0], [1, a0]]})
    for sid, ph in SLUMPS:
        a0 = r3(slump_alpha(ph))
        out.append({"part": sid, "prop": "opacity", "keys": [[0, a0], [1, a0]]})
    return out

# ---- idle: the sand going down, slowly. The jaws are still but for a twitch
# once a loop, a few degrees, the one sign anything is down there.
IDLE_T = 3.0
ts_i = dense(30)
def idle_twitch(t): return 3.0 * math.exp(-((t - 0.62) / 0.035) ** 2) - 1.5 * math.exp(-((t - 0.7) / 0.03) ** 2)
idle = flow_tracks(16) + jaw_tracks(ts_i, idle_twitch, lambda t: 1.0)

# ---- sense: something is on the slope. The sand runs two and a half times as
# fast and brighter, the jaws come up out of the clot, stand wide over the
# lip and work — a chatter twice a loop.
SENSE_T = 1.2
ts_s = dense(24)
sense = (flow_tracks(12, alpha_mul=1.0)
         + jaw_tracks(ts_s, lambda t: 22.0 + 5.0 * cyc(t * 2), lambda t: 1.3 + 0.03 * cyc(t * 2, 0.25), lambda t: -3.0))
# the loose sand on the lip trembles and creeps in
for pid, a, r in PUFFS:
    ux, uy = math.cos(R(a)), math.sin(R(a))
    k = (int(pid.split("_")[1]) % 3) / 3.0
    sense.append(fn_tracks(pid, "x", ts_s, lambda t, ux=ux, k=k: -ux * (1.2 + 1.0 * cyc(t * 2, k))))
    sense.append(fn_tracks(pid, "y", ts_s, lambda t, uy=uy, k=k: -uy * (1.2 + 1.0 * cyc(t * 2, k))))

# ---- bite: the jaws wind wide, clap shut past each other, grind, and sink back
# to the drawing. The clap throws the lip's loose sand out and a ring of dust
# off the throat, and the slope gives a shudder from the throat outward.
BITE_T = 0.9
ts_b = dense(36, [0.14, 0.2, 0.24, 0.3, 0.55, 0.6, 0.85])
def bite_open(t):
    if t < 0.14: return lerp(0.0, 30.0, smooth(0.0, 0.14, t))
    if t < 0.2: return lerp(30.0, 32.0, (t - 0.14) / 0.06)
    if t < 0.24: return lerp(32.0, -30.0, smooth(0.2, 0.24, t))         # the clap: tips cross
    if t < 0.3: return lerp(-30.0, -24.0, smooth(0.24, 0.3, t))        # bounce off each other
    if t < 0.5: return -24.0 + 2.0 * math.sin((t - 0.3) * 2 * math.pi / 0.1)  # grind
    return lerp(-24.0, 0.0, smooth(0.5, 0.85, t))
def bite_scale(t):
    if t < 0.2: return lerp(1.0, 1.4, smooth(0.0, 0.2, t))
    if t < 0.5: return lerp(1.4, 1.3, smooth(0.2, 0.3, t))
    return lerp(1.3, 1.0, smooth(0.5, 0.85, t))
def bite_rise(t):
    if t < 0.5: return -4.0 * smooth(0.0, 0.2, t)
    return lerp(-4.0, 0.0, smooth(0.5, 0.85, t))
bite = jaw_tracks(ts_b, bite_open, bite_scale, bite_rise) + streak_hold()
THROW = 40.0
for pid, a, r in PUFFS:
    ux, uy = math.cos(R(a)), math.sin(R(a))
    def out_u(t):
        if t < 0.22: return 0.0
        if t < 0.55: return 1.0 - (1.0 - smooth(0.22, 0.55, t)) ** 2
        return 0.0 if t >= 0.6 else 1.0
    def alpha(t):
        if t < 0.22: return 1.0
        if t < 0.55: return 1.0 - smooth(0.3, 0.55, t)
        if t < 0.6: return 0.0
        return smooth(0.6, 0.85, t)
    bite.append(fn_tracks(pid, "x", ts_b, lambda t, ux=ux: ux * THROW * out_u(t)))
    bite.append(fn_tracks(pid, "y", ts_b, lambda t, uy=uy: uy * THROW * out_u(t)))
    bite.append(fn_tracks(pid, "scale", ts_b, lambda t: 1.0 + 1.4 * (out_u(t) if t < 0.6 else 0.0)))
    bite.append(fn_tracks(pid, "opacity", ts_b, alpha))
def dust_u(t): return smooth(0.22, 0.5, t) if t < 0.55 else 0.0
bite.append(fn_tracks("throat_lit", "scale", ts_b, lambda t: 1.0 + 1.3 * dust_u(t)))
bite.append(fn_tracks("throat_lit", "opacity", ts_b,
                      lambda t: 1.0 if t < 0.22 else (1.0 - smooth(0.26, 0.5, t) if t < 0.55 else smooth(0.6, 0.85, t))))
bite.append(fn_tracks("throat_deep", "scale", ts_b,
                      lambda t: 1.0 + 0.25 * smooth(0.2, 0.26, t) * (1 - smooth(0.3, 0.6, t))))
# the shudder: each band pulled in a little, the throat's first, the lip's last
for i, r in enumerate(reversed(BANDS)):
    idx = len(BANDS) - 1 - i
    t0 = 0.24 + 0.02 * i
    amp = 0.04 * (1.0 - 0.08 * i)
    def sh(t, t0=t0, amp=amp):
        if t < t0: return 1.0
        k = (t - t0) / 0.3
        return 1.0 - amp * math.exp(-3.0 * k) * math.sin(math.pi * min(k, 1.0) * 2.0) if k < 1 else 1.0
    bite.append(fn_tracks(f"band_{idx}", "scale", ts_b, sh))

for tr in bite + idle + sense:
    k = tr["keys"]
    k[0][0] = 0
    k[-1][0] = 1

doc = {
    "id": "ss.terrain.funnel",
    "name": "Sand funnel",
    "description": (
        "The Pit's hazard: an antlion's trap, a funnel of sand 150 world px in radius dug into the desert zones "
        "(and, rarely, the plains) of Feelers' fourth stage. It is not a body and it blocks nothing — it pulls "
        "everything on the ground toward its middle, and whatever stays within 30px of the middle for a second "
        "is bitten by what is buried there (feelers docs/pit-plan.md §3.4). Drawn top-down at the size the run sees "
        "it, 1:1: `meta.radius` is the crest of the lip and `meta.throat` is the bite, so what pulls and what bites "
        "are what you can see.\n\n"
        "Lit from the upper left, like the Sinkmaw's pit — the same animal, one that never grew into a boss. A "
        "pale lip of thrown sand spills onto whatever floor it is dug in (`spill`, `spill_far`), its face toward "
        "the light lit and the face away shaded, and a hair of ink at the brink where the fall starts. Nine "
        "translucent discs step the slope down from the lip to a throat that is a hole rather than a colour, so it "
        "reads as a slope in small steps and not as a target in big ones (the Phaser bake flattens a gradient); the "
        "discs between lip and throat sit toward the light, so the far wall is wide and lit and the wall under the "
        "light is crowded and dark, while the lip and the throat stay concentric with the pull the game computes.\n\n"
        "What moves is what crosses the slope, because a circle scaled about its centre is the same circle: sixteen "
        "tongues of sand (`streak_*`, each a lit tongue over its own lee) sliding in on staggered clocks, faster as "
        "they fall and set 22 degrees off the fall line so the funnel turns as it drains, and three slump lines "
        "(`slump_*`) drawing in from the lip. Each streak's origin is its leading end, so it shrinks toward the "
        "front it slides on.\n\n"
        "The antlion is two sickles and a clot of wet sand. The jaws are hinged at their roots in the throat "
        "(`jaw_l`, `jaw_r`, each with its tip), under `clot`, and in the drawing they stand a little open and "
        "short of the lip, dull husk in the dark: a thing you see on the second look. Seven heaps of loose sand "
        "(`puff_*`) lie on the throat's lip, and `throat_lit` is its lit edge.\n\n"
        "Every clip's first frame is the drawing, with each streak and slump at its own phase, and `bite` ends on "
        "it, so any clip hands to any other without the sand jumping. It is also the biggest sheet in the set: "
        "at the game's 15fps `idle` is 45 frames of 320×320, `sense` 18 and `bite` 14, so it wants baking at 1× "
        "rather than the 2× the tunnel's small mouth needs."
    ),
    "tags": ["terrain", "hazard"],
    "size": [320, 320],
    "meta": {"radius": RIM, "throat": THROAT},
    "parts": parts,
    "animations": {
        "idle": {
            "description": (
                "The funnel draining, slowly: every tongue of sand runs from the lip into the throat once a loop, "
                "each on its own clock and gathering speed as it falls, fading in as it leaves the lip and out as it "
                "goes over the throat's edge, and the three slump lines draw in behind them. Below all of it the "
                "jaws hold still but for one twitch a loop, three degrees, the only sign anything is down there. "
                "Loops."
            ),
            "duration": IDLE_T,
            "tracks": idle,
        },
        "sense": {
            "description": (
                "Something is on the slope. The same drain two and a half times as fast, which is what reads "
                "across a screen; the jaws come up out of the clot a size larger and three pixels higher, stand "
                "wide enough to reach over the throat's lip, and work — open and half-shut twice a loop — while the "
                "loose sand on the lip trembles and creeps in. Loops for as long as whatever tripped it stays inside."
            ),
            "duration": SENSE_T,
            "tracks": sense,
        },
        "bite": {
            "description": (
                "One shot. The jaws wind wide and rise, clap shut past each other on the fifth of a second the game "
                "bites on (t≈0.24), bounce, grind, and sink back into the clot. The clap throws the lip's loose sand "
                "out and a ring of dust off the throat, the throat gulps, and the slope shudders band by band from "
                "the throat out to the lip. The drain holds on its first frame throughout, and the last frame is "
                "`idle` at t=0: nothing moves after t=0.85."
            ),
            "duration": BITE_T,
            "tracks": bite,
        },
    },
}
write_doc(doc, OUT)
print(f"wrote {os.path.relpath(OUT)}: {len(parts)} parts, "
      + ", ".join(f"{k} {len(v['tracks'])} tracks" for k, v in doc["animations"].items()))
