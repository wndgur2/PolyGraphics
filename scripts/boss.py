"""The Chorus — the Plains' first boss, the hive saying so as loudly as it can.

    python3 scripts/boss.py        # rewrites apps/ss/assets/ss-enemy-boss.json

The game has it stop and *shout its way round itself*: six organs, one every
0.42s, each one opening a wedge on the floor on the next bearing round
(feelers: `EnemyType.sweepInterval`, `sweepAnim: 'shout'`, played once per
organ and fitted to `sweepStep`). Halfway down it turns `enraged` (every organ
screaming at once, two wedges a step), at a quarter `final` (three wedges, the
voice losing its order). It walks between volleys and is mirrored by the game,
never turned — and it is radial, so the mirror costs it nothing but the sense
the light goes round in, which the floor's wedges set anyway.

It used to be a medallion: a 12-gon disc with pale rings on it that turned,
six small organs on the rim, six spikes that slid a few pixels as the light
went by. At game scale the loop moved 4px and 7% of its outline; it read as a
coin. The concept stays — a seated mass with six organs round the rim firing
in sequence, a crown of six spines between them, a toothed vent in the middle
that has only ever shouted — and the body is rebuilt as a creature:

  - six carapace *segments*, a petal each, round a mouth: every segment is a
    lobe of flesh with a shield-plate on it (a lit face and a shade, a keel down
    the middle) and an organ seated at its outer end. The segment carries its
    organ, so when the organ fires the whole segment swells and pushes out —
    the light travels round, and the body travels with it
  - six spines at the seams, each a two-bone horn (a root and a thorn, hinged)
    that rises out of the seam as the organ beside it fires and lays back along
    the body behind the wave — a power stroke and a slow recovery, the way cilia
    beat, so the crown ripples round like the light does
  - a mouth: an iris of eight fangs hinged in a collar of gum, over a vent with
    the hive's light deep in it. It breathes (the iris opens and shuts twice a
    loop) and it is what the shout is: clench, then throw open
  - the whole mass leans a pixel toward whichever organ is firing, so the
    body's centre itself circles with the sequence

Every part rides a node of a small radial rig (below): a node is a similarity
transform — turn, scale and shift about a joint — composed down the tree, and
each part's x/y/rot/scale track is solved from its node, so a thorn stays on
its root and a root on its seam whatever a clip does to them.

The phases, readable at a glance with the same clips: `enraged` flushes the
flesh, opens a glowing split down every plate's keel and lets the seams burn
through, and turns on a halo round every organ that pulses in unison — the
sequence still runs underneath, but all six are screaming. `final` bleaches the
shell to ash, puts out three of the six (the organ's own `dead` state, the
spine beside each snapped to a stub), and leaves the other three and the vent
the brightest things on it, so the light no longer travels, it stutters.
"""
import cmath, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import R, r2, lerp, smooth, keyset, poly, circ, bar, INK_HAIR, INK_THIN, write_doc

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-enemy-boss.json")

L = "abcdef"                       # six segments / organs, a at +x, going clockwise on screen
SEG = [60.0 * i for i in range(6)]  # segment (organ) bearings
SPN = [a + 30.0 for a in SEG]       # spine bearings — spine k sits in the seam between segments k and k+1
def U(deg): return cmath.exp(1j * R(deg))
def C(p): return complex(p[0], p[1])
def XY(z): return (z.real, z.imag)

# ============================================================== geometry (document units, origin at the centre)
SIZE = 104
ORG_R = 28.2        # organ seat, along a segment
SPINE_R = 25.4      # spine root, in a seam
SP_L0, SP_L1 = 8.6, 9.6   # root and thorn
SPINE_LEAN = 22.0   # rest lean of a spine back against the wave (degrees)
SPINE_CURL = 16.0   # the thorn curls further back than its root
FANG_R = 10.2       # fang hinge radius
FANG_TWIST = 6.0   # the blades are not radial: an iris
FANG_L = 7.4
ORGAN_SCALE = 0.74

def egg(cx, rx, ry, inner=0.5, n=22):
    """A petal along +x: centred at cx, `rx` long, `ry` wide, narrower toward the mouth (the inner end by `inner`)."""
    pts = []
    for i in range(n):
        ph = 2 * math.pi * i / n
        c, s = math.cos(ph), math.sin(ph)
        taper = lerp(inner, 1.0, (1 + c) / 2) ** 0.8
        pts.append((cx + rx * c, ry * s * taper))
    return pts

def rot_pts(pts, deg, off=0j):
    u = U(deg)
    return [XY(C(p) * u + off) for p in pts]

LOBE = egg(19.0, 13.2, 12.6, inner=0.46)
PLATE = egg(19.2, 12.3, 11.5, inner=0.5)
def crescent(outline, side, keep=0.42):
    """The shaded side of a plate: its outline on that side, closed by the same curve pulled most of the way out."""
    half = [p for p in outline if p[1] * side > 0.05]
    half.sort(key=lambda p: p[0])
    back = [(x, y * keep) for x, y in reversed(half)]
    return half + back
KEEL = [(10.5, -0.5), (19.0, -0.9), (27.0, -0.3), (27.0, 0.3), (19.0, 0.7), (10.5, 0.4)]
def half_width(outline, x):
    """The plate's half-width at `x` along it (from its outline's upper side)."""
    best = 0.0
    pts = [p for p in outline if p[1] < 0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if min(x0, x1) <= x <= max(x0, x1) and x1 != x0:
            best = max(best, -lerp(y0, y1, (x - x0) / (x1 - x0)))
    return best
def band(outline, x0, bow=1.6, th=0.9, inset=0.6):
    """A seam across the plate at `x0`, bowed outward — the plate is built in courses."""
    w = half_width(outline, x0) - inset
    n = 9
    front = [(x0 + bow * (1 - (y / w) ** 2), y) for y in (lerp(-w, w, i / (n - 1)) for i in range(n))]
    back = [(x - th * (0.4 + 0.6 * (1 - (y / w) ** 2)), y) for x, y in reversed(front)]
    return front + back
THORN = [(-0.6, -2.4), (2.5, -2.4), (6.0, -1.6), (8.6, -0.5), (SP_L1 + 0.4, 0.35), (8.0, 0.9), (4.0, 2.0), (0.0, 2.4), (-0.6, 1.7)]
FANG = [(-0.3, -2.2), (2.6, -1.7), (5.4, -0.7), (FANG_L, 0.4), (5.2, 0.9), (2.4, 1.8), (-0.3, 2.0)]

# the mass: a star under the segments whose points are the seams, so the seams
# (and the spine roots in them) sit on flesh rather than on nothing
MASS = []
for i in range(6):
    MASS.append(XY(U(SEG[i]) * 19.0))
    MASS.append(XY(U(SEG[i] + 18) * 24.5))
    MASS.append(XY(U(SPN[i]) * 28.6))
    MASS.append(XY(U(SEG[i] + 42) * 24.5))

# ============================================================== the radial rig
# A node is a similarity (m, c): z -> m z + c, in its parent's frame; a part
# rides one node. Nodes: body > seg_x > org_x / cry_x, body > seam_k > sp_k0 >
# sp_k1, body > mouth > glow / fang_j.
PARENT = {"body": None, "mouth": "body", "glow": "mouth"}
for i in range(6):
    PARENT[f"seg_{L[i]}"] = "body"; PARENT[f"org_{L[i]}"] = f"seg_{L[i]}"; PARENT[f"cry_{L[i]}"] = f"seg_{L[i]}"
    PARENT[f"seam_{L[i]}"] = "body"; PARENT[f"sp_{L[i]}0"] = f"seam_{L[i]}"; PARENT[f"sp_{L[i]}1"] = f"sp_{L[i]}0"
for j in range(8): PARENT[f"fang_{j}"] = "mouth"

def about(p, scale=1.0, deg=0.0, shift=0j):
    """Scale and turn about the point `p`, then shift."""
    m = scale * U(deg)
    return (m, p - m * p + shift)
def after(A, B):  # A applied after B
    return (A[0] * B[0], A[0] * B[1] + A[1])
IDENT = (1 + 0j, 0j)

# joints at rest
ORG_AT = [U(SEG[i]) * ORG_R for i in range(6)]
SEG_ROOT = [U(SEG[i]) * 8.0 for i in range(6)]
SP_ROOT = [U(SPN[k]) * SPINE_R for k in range(6)]
SP_H0 = [SPN[k] - SPINE_LEAN for k in range(6)]          # rest heading of the root
SP_H1 = [SPN[k] - SPINE_LEAN - SPINE_CURL for k in range(6)]
SP_KNEE = [SP_ROOT[k] + U(SP_H0[k]) * SP_L0 for k in range(6)]
FANG_AT = [U(45.0 * j + 22.5) * FANG_R for j in range(8)]
FANG_H = [45.0 * j + 22.5 + 180.0 + FANG_TWIST for j in range(8)]

def world(local):
    """World similarity of every node from the local ones (missing = identity)."""
    out = {}
    def w(n):
        if n in out: return out[n]
        loc = local.get(n, IDENT)
        out[n] = loc if PARENT[n] is None else after(w(PARENT[n]), loc)
        return out[n]
    for n in PARENT: w(n)
    return out

# ============================================================== parts
PARTS, RIDE = [], {}
def put(id, node, at, rot, shape, fill, stroke=None, opacity=None, scale=None):
    p = {"id": id}
    if abs(at) > 1e-9: p["at"] = [r2(at.real), r2(at.imag)]
    if abs(rot) > 1e-6: p["rot"] = r2(rot)
    if scale is not None: p["scale"] = scale
    if opacity is not None: p["opacity"] = opacity
    p["shape"] = shape; p["fill"] = fill
    if stroke: p["stroke"] = stroke
    PARTS.append(p); RIDE[id] = node
def use(id, node, at, asset, scale):
    PARTS.append({"id": id, "at": [r2(at.real), r2(at.imag)], "use": asset, "scale": scale}); RIDE[id] = node

SHADE = []  # which side of each segment faces away from the light (top-left)
for i in range(6):
    side = U(SEG[i] + 90)
    SHADE.append(1.0 if side.real + side.imag > 0 else -1.0)

# spines behind everything: they leave the body through the seams
for k in range(6):
    x = L[k]
    put(f"spine_{x}", f"sp_{x}0", SP_ROOT[k], SP_H0[k], bar(SP_L0, 7.6, 4.8, over=0.4), "$husk.dark", INK_HAIR)
    put(f"spine_{x}_tip", f"sp_{x}1", SP_KNEE[k], SP_H1[k], poly(THORN), "$bone", INK_HAIR)
put("mass", "body", 0j, 0.0, poly(MASS), "$chitin.dark2", {"color": "$ink", "width": "thin"})
for k in range(6):
    x = L[k]
    put(f"spine_root_{x}", f"seam_{x}", U(SPN[k]) * 24.6, SPN[k], poly([(-2.0, -3.6), (2.6, -3.0), (3.6, 0), (2.6, 3.0), (-2.0, 3.6)]), "$chitin.dark2")
for i in range(6):
    x, a = L[i], SEG[i]
    s = SHADE[i]
    put(f"lobe_{x}", f"seg_{x}", 0j, a, poly(LOBE), "$chitin.dark", INK_HAIR)
    put(f"plate_{x}", f"seg_{x}", 0j, a, poly(PLATE), "$husk.dark")
    lit = U(225.0 - a) * 1.25  # toward the light (top-left), in the segment's own frame
    put(f"plate_{x}_lit", f"seg_{x}", 0j, a, poly([(19.4 + (px - 19.4) * 0.84 + lit.real, py * 0.8 + lit.imag) for px, py in PLATE]), "$husk")
    put(f"band_{x}", f"seg_{x}", 0j, a, poly(band(PLATE, 14.0) + []), "$husk.dark2")
    put(f"band_{x}2", f"seg_{x}", 0j, a, poly(band(PLATE, 21.5, bow=2.0)), "$husk.dark2")
    put(f"socket_{x}", f"seg_{x}", ORG_AT[i], a, {"kind": "ellipse", "rx": 3.9, "ry": 4.3}, "$husk.dark2")
for i in range(6):
    x = L[i]
    use(f"organ_{x}", f"org_{x}", ORG_AT[i], "ss.lib.organ", ORGAN_SCALE)
    # the scream: a halo round the organ that only the phases turn on (opacity 0
    # here, and a variant sets it), pulsing in unison under the sequence
    put(f"cry_{x}", f"cry_{x}", ORG_AT[i], 0.0, {"kind": "ring", "r": 6.4, "width": 1.8}, "$pheromone.light@heavy", opacity=0)
# the mouth
put("collar", "mouth", 0j, 0.0, {"kind": "ngon", "sides": 12, "r": 12.6}, "$mauve.dark", INK_THIN)
put("gum", "mouth", 0j, 15.0, {"kind": "ngon", "sides": 12, "r": 10.8}, "$mauve")
put("vent", "mouth", 0j, 0.0, circ(8.0), "$dead")
put("vent_glow", "glow", 0j, 0.0, circ(6.6), {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$pheromone.light"], [0.55, "$pheromone@0.55"], [1, "$pheromone@0"]]})
put("throat", "glow", 0j, 0.0, circ(1.9), "$pheromone.light2")
for j in range(8):
    put(f"fang_{j}", f"fang_{j}", FANG_AT[j], FANG_H[j], poly(FANG), "$bone", INK_HAIR)

# ============================================================== motion
def pulse(u, rise=0.045, fall=0.2):
    """0 → 1 → 0 over a cycle position u in [0,1): a quick swell and a longer settle."""
    u %= 1.0
    if u < rise: return smooth(0, rise, u)
    return 1.0 - smooth(rise, fall, u)
def erect(u, rise=0.07, hold=0.14):
    """A spine's stroke over its cycle: up past upright fast, settle, then lay back slowly."""
    u %= 1.0
    if u < rise: return lerp(0.0, 1.15, smooth(0, rise, u))
    if u < hold: return lerp(1.15, 1.0, smooth(rise, hold, u))
    return 1.0 - smooth(hold, 1.0, u)

SPINE_SWING0, SPINE_SWING1 = 44.0, 34.0  # full stroke of root and thorn (degrees)

def pose(state):
    """
    Local node transforms from a state:
      lean       complex   the body's shift
      breath     float     the body's scale about the centre
      fire[i]    0..      segment i's organ swell (and the segment's push)
      push[i]    float     extra outward push of segment i
      turn[i]    float     segment i turned about the centre (degrees)
      spine[k]   0..1+     how far up spine k stands (0.5 = rest geometry)
      reach[k]   float     spine k pushed out along its bearing
      droop[k]   float     extra thorn bend
      gape       0..1+     the iris (0.5 = rest geometry)
      mouth      float     the collar's scale
      glow       float     the light in the vent's scale
      cry        float     the unison halo's scale
    """
    loc = {"body": about(0j, state.get("breath", 1.0), 0.0, state.get("lean", 0j))}
    fire, push, turn = state.get("fire", [0] * 6), state.get("push", [0] * 6), state.get("turn", [0] * 6)
    seg_shift = []
    for i in range(6):
        x = L[i]
        f = fire[i]
        sh = U(SEG[i]) * (2.2 * f + push[i])
        seg_shift.append(sh)
        T = about(SEG_ROOT[i], 1.0 + 0.07 * f, 0.0, sh)
        if turn[i]: T = after(about(0j, 1.0, turn[i]), T)
        loc[f"seg_{x}"] = T
        loc[f"org_{x}"] = about(ORG_AT[i], state.get("organ", [1.0] * 6)[i] + 0.55 * f)
        loc[f"cry_{x}"] = about(ORG_AT[i], state.get("cry", 1.0))
    spine, reach, droop = state.get("spine", [0.5] * 6), state.get("reach", [0] * 6), state.get("droop", [0] * 6)
    for k in range(6):
        x = L[k]
        seam = 0.5 * (seg_shift[k] + seg_shift[(k + 1) % 6])
        loc[f"seam_{x}"] = about(0j, 1.0, 0.0, seam)
        e = spine[k] - 0.5
        loc[f"sp_{x}0"] = about(SP_ROOT[k], 1.0, e * SPINE_SWING0, U(SPN[k]) * (reach[k] + 1.4 * e))
        loc[f"sp_{x}1"] = about(SP_KNEE[k], 1.0, e * SPINE_SWING1 + droop[k])
    loc["mouth"] = about(0j, state.get("mouth", 1.0))
    loc["glow"] = about(0j, state.get("glow", 1.0))
    g = state.get("gape", 0.5) - 0.5
    for j in range(8):
        # the blade swings about its hinge, out of the aperture, and the hinge
        # gives a little outward — an iris, not a clock
        loc[f"fang_{j}"] = about(FANG_AT[j], 1.0 - 0.1 * g, -52.0 * g, U(45.0 * j + 22.5) * 1.6 * g)
    return loc

def tracks(state_at, ts, extra=()):
    rest = world(pose({}))
    rest_inv = {n: None for n in rest}
    series = {p["id"]: ([], [], [], []) for p in PARTS}
    for t in ts:
        W = world(pose(state_at(t)))
        for p in PARTS:
            pid, n = p["id"], RIDE[p["id"]]
            # the part's rest transform is rest[n]; its posed one W[n]. The
            # delta that carries the rest part to the posed one:
            m0, c0 = rest[n]; m1, c1 = W[n]
            dm = m1 / m0                  # turn and scale
            at = complex(*(p.get("at") or [0.0, 0.0]))
            # a point q of the part at rest came from z = (q - c0)/m0; posed it is m1 z + c1
            new_at = m1 * ((at - c0) / m0) + c1
            d = new_at - at
            s = series[pid]
            s[0].append(d.real); s[1].append(d.imag)
            s[2].append(math.degrees(cmath.phase(dm))); s[3].append(abs(dm))
    out = []
    for p in PARTS:
        pid = p["id"]
        xs, ys, rs, ss = series[pid]
        round_part = p.get("shape", {}).get("kind") in ("circle", "ring")
        for prop, vs, zero in (("x", xs, 0.0), ("y", ys, 0.0), ("rot", rs, 0.0), ("scale", ss, 1.0)):
            if prop == "rot" and round_part: continue
            if max(abs(v - zero) for v in vs) > (0.004 if prop == "scale" else 0.01):
                out.append({"part": pid, "prop": prop, "keys": [[r2(t), round(v, 3) if prop == "scale" else r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
    for pid, prop, fn in extra:
        out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(fn(t))] for t in ts], "ease": "linear"})
    return out

# ---------------------------------------------------------------- chorus (2.4s, the idle)
def chorus(t):
    fire = [pulse(t - i / 6.0) for i in range(6)]
    spine = [erect(t - k / 6.0 - 1 / 12.0) for k in range(6)]
    gape = 0.5 - 0.5 * math.cos(2 * math.pi * 2 * t)
    return {
        "lean": U(360.0 * t - 20.0) * 1.1,
        "breath": 1.0 + 0.018 * math.sin(2 * math.pi * 2 * t),
        "fire": fire,
        "push": [0.7 * math.sin(2 * math.pi * (t - i / 6.0) + 0.6) for i in range(6)],
        "spine": spine,
        "gape": 0.2 + 0.7 * gape,
        "mouth": 1.0 + 0.05 * (gape - 0.5),
        "glow": 0.85 + 0.35 * gape,
        "cry": 0.75 + 0.75 * ((4 * t) % 1.0),
    }
def cry_fade(t):
    q = (4 * t) % 1.0
    return smooth(0, 0.08, q) * (1 - q) ** 1.4

# ---------------------------------------------------------------- shout (0.4s, once per organ step)
def shout(t):
    A = smooth(0.0, 0.3, t) * (1 - smooth(0.3, 0.42, t))     # the draw-in
    B = smooth(0.3, 0.42, t) * (1 - smooth(0.46, 1.0, t))    # the burst, and the long settle
    return {
        "breath": 1.0 - 0.035 * A + 0.06 * B,
        "fire": [0.0] * 6,
        "push": [-1.6 * A + 1.8 * B] * 6,
        "spine": [0.5 - 0.62 * A + 0.62 * B] * 6,
        "reach": [1.4 * B] * 6,
        "gape": 0.5 - 0.62 * A + 0.85 * B,
        "mouth": 1.0 - 0.07 * A + 0.1 * B,
        "glow": 0.9 - 0.4 * A + 0.9 * B,
        "organ": [1.0 + 0.14 * B] * 6,
        "cry": 0.8 + 0.9 * smooth(0.3, 0.8, t),
    }
def shout_glow_op(t):
    A = smooth(0.0, 0.3, t) * (1 - smooth(0.3, 0.42, t))
    return 1.0 - 0.55 * A
def shout_cry_op(t):
    return smooth(0.3, 0.4, t) * (1 - smooth(0.45, 0.95, t))

# ---------------------------------------------------------------- death (0.95s, settles by 0.85)
DSEQ = [0.02 + 0.062 * i for i in range(6)]
def death(t):
    t = min(t, 0.85)
    fire, spine = [], []
    flare = smooth(0.42, 0.5, t) * (1 - smooth(0.54, 0.7, t))
    out = smooth(0.54, 0.85, t)
    for i in range(6):
        u = t - DSEQ[i]
        seq = (smooth(0, 0.035, u) * (1 - smooth(0.035, 0.11, u))) if u > 0 else 0.0
        fire.append(max(seq, 1.1 * flare))
        v = t - DSEQ[i] - 0.03
        up = (smooth(0, 0.05, v) if v > 0 else 0.0)
        spine.append(lerp(0.5 + 0.5 * up, -0.35 + 0.18 * (i % 2), out))
    return {
        "breath": 1.0 + 0.04 * flare - 0.05 * out,
        "fire": [f * (1 - out) for f in fire],
        "organ": [1.0 - 0.3 * out] * 6,
        "push": [0.8 * flare - 1.4 * out] * 6,
        "turn": [(3.5 if i % 2 else -3.5) * out for i in range(6)],
        "spine": spine,
        "reach": [2.8 * out] * 6,
        "droop": [-24.0 * out * (1 if k % 2 else 0.6) for k in range(6)],
        "gape": lerp(0.5, 1.3, smooth(0.38, 0.5, t)) * (1 - out) + 0.35 * out,
        "mouth": 1.0 + 0.08 * flare - 0.06 * out,
        "glow": 1.0 + 1.1 * flare - 0.4 * out,
    }
def death_organ_op(t):
    return 1.0 - 0.72 * smooth(0.56, 0.85, min(t, 0.85))
def death_glow_op(t):
    return 1.0 - smooth(0.6, 0.85, min(t, 0.85))

# ============================================================== clips
TS_CHORUS = keyset(36)
TS_SHOUT = keyset(24)
TS_DEATH = [i / 40 for i in range(35)] + [0.9, 0.95, 1.0]

animations = {
    "chorus": {
        "description": "the light travels the ring and the body travels with it: each organ fires in turn and its whole segment swells and pushes out under it; the spine in the seam beyond rises out of the body past upright and then lays back along it behind the wave (a quick stroke and a slow recovery, so the crown ripples round the way the light does); the mass leans a pixel toward whichever organ is firing; the iris of fangs opens and shuts twice over the vent. The halos round the organs pulse in unison here too, but they are dark until a phase lights them",
        "duration": 2.4,
        "tracks": tracks(chorus, TS_CHORUS, [(f"cry_{x}", "opacity", cry_fade) for x in L]),
    },
    "death": {
        "description": "the loudest thing in the hive stops: the light runs the ring once more, faster than it ever did alive, the crown rising behind it; then all six flare at once with the iris thrown wide, and go out together — the segments sag and loosen against each other, the spines fall outward and flat, the fangs slacken half-shut over a vent gone dark. Still by 0.85",
        "duration": 0.95,
        "tracks": tracks(death, TS_DEATH,
                         [(f"organ_{x}", "opacity", death_organ_op) for x in L] + [("vent_glow", "opacity", death_glow_op), ("throat", "opacity", death_glow_op)]),
    },
    "shout": {
        "description": "One shout leaving the vent, played by the game once per organ as the volley goes round (stretched to the 0.42s step). The draw-in: the iris clenches shut, the segments pull in, every spine lays flat and the light in the vent sinks; the burst: the iris is thrown wide past anything the idle does, the light flares, the segments shove out and the whole crown stands up at once; then a long settle back to rest. The organs stay out of it (the sequence is the idle's), save a swell on the burst; in the phases the halos flash with it",
        "duration": 0.4,
        "tracks": tracks(shout, TS_SHOUT,
                         [("vent_glow", "opacity", shout_glow_op)] + [(f"cry_{x}", "opacity", shout_cry_op) for x in L]),
    },
}

# ============================================================== states
ALL = range(6)
enraged_set = {
    "mass.fill": "$pheromone.dark",
    **{f"spine_root_{L[k]}.fill": "$pheromone.dark" for k in ALL},
    **{f"lobe_{L[i]}.fill": "$rust.light" for i in ALL},
    **{f"spine_{L[k]}_tip.scale": 1.25 for k in ALL},
    **{f"band_{L[i]}.fill": "$pheromone.light" for i in ALL},
    **{f"band_{L[i]}2.fill": "$pheromone" for i in ALL},
    **{f"socket_{L[i]}.fill": "$pheromone.dark" for i in ALL},
    **{f"organ_{L[i]}.scale": r2(ORGAN_SCALE * 1.3) for i in ALL},
    **{f"cry_{L[i]}.opacity": 1 for i in ALL},
    **{f"spine_{L[k]}.fill": "$husk" for k in ALL},
    **{f"spine_{L[k]}_tip.fill": "$bone" for k in ALL},
    "collar.fill": "$rust",
    "gum.fill": "$pheromone.dark",
    "vent_glow.fill": {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$white"], [0.5, "$pheromone.light"], [1, "$pheromone@0"]]},
    "vent_glow.scale": 1.35,
    "throat.fill": "$white",
}
DEAD = (1, 3, 5)   # b, d, f burnt out
LIT = (0, 2, 4)
final_set = {
    "mass.fill": "$dead",
    **{f"spine_root_{L[k]}.fill": "$dead.light" for k in ALL},
    **{f"lobe_{L[i]}.fill": "$dead.light" for i in ALL},
    **{f"plate_{L[i]}.fill": "$bone.dark2" for i in ALL},
    **{f"plate_{L[i]}_lit.fill": "$bone.dark" for i in ALL},
    **{f"band_{L[i]}.fill": "$dead" for i in ALL},
    **{f"band_{L[i]}2.fill": "$dead" for i in ALL},
    **{f"spine_{L[k]}.fill": "$bone.dark" for k in ALL},
    **{f"spine_{L[k]}_tip.fill": "$bone" for k in ALL},
    **{f"organ_{L[i]}.variant": "dead" for i in DEAD},
    **{f"organ_{L[i]}.scale": r2(ORGAN_SCALE * 0.8) for i in DEAD},
    **{f"socket_{L[i]}.fill": "$ink" for i in DEAD},
    **{f"lobe_{L[i]}.scale": 0.93 for i in DEAD},
    **{f"plate_{L[i]}.scale": 0.93 for i in DEAD},
    **{f"plate_{L[i]}_lit.scale": 0.93 for i in DEAD},
    **{f"band_{L[i]}.scale": 0.93 for i in DEAD},
    **{f"band_{L[i]}2.scale": 0.93 for i in DEAD},
    **{f"organ_{L[i]}.scale": r2(ORGAN_SCALE * 1.4) for i in LIT},
    **{f"socket_{L[i]}.fill": "$pheromone.dark" for i in LIT},
    **{f"cry_{L[i]}.opacity": 0.7 for i in LIT},
    "collar.fill": "$dead.light",
    "gum.fill": "$bone.dark",
    **{f"fang_{j}.fill": "$bone.light" for j in range(8)},
    "vent.fill": "$ink",
    "vent_glow.fill": {"gradient": "radial", "from": [0.5, 0.5], "stops": [[0, "$white"], [0.6, "$pheromone.light"], [1, "$pheromone@0"]]},
    "vent_glow.scale": 1.6,
    "throat.fill": "$white",
}
variants = {
    "enraged": {
        "description": "Phase two: the shell splits along every seam, the vent burns through, and the sequence collapses into all six organs screaming at once. The flesh flushes, each plate opens down its keel in the hive's light and the seams under the spines burn through; the organs swell and a halo round every one of them pulses in unison over the sequence still running beneath — every organ screaming at once. The vent's light goes white at the core.",
        "scale": 1.1,
        "set": enraged_set,
    },
    "final": {
        "description": "Phase three: the voice loses its order. Three of the six are burnt out — dark, shrunk back into their seats, the spine beside each snapped off to a stub — and the three still lit are carrying the whole ring on their own, so the light no longer travels, it stutters. The shell has gone to ash around a vent that is now the brightest thing on the body.\n\nIt is deliberately not \"enraged, brighter\". The second phase is every organ screaming at once; the third is half of them unable to, which is the only escalation available to a creature that is a sequence.",
        "scale": 1.12,
        "remove": [f"spine_{L[k]}_tip" for k in DEAD],
        "set": final_set,
    },
}

# ============================================================== document
joints = {"centre": [0.0, 0.0]}
bones = []
for i in range(6):
    joints[f"seat_{L[i]}"] = [r2(ORG_AT[i].real), r2(ORG_AT[i].imag)]
    bones.append(["centre", f"seat_{L[i]}"])
for k in range(6):
    x = L[k]
    tip = SP_KNEE[k] + U(SP_H1[k]) * SP_L1
    joints[f"spine_root_{x}"] = [r2(SP_ROOT[k].real), r2(SP_ROOT[k].imag)]
    joints[f"spine_knee_{x}"] = [r2(SP_KNEE[k].real), r2(SP_KNEE[k].imag)]
    joints[f"spine_tip_{x}"] = [r2(tip.real), r2(tip.imag)]
    bones += [["centre", f"spine_root_{x}"], [f"spine_root_{x}", f"spine_knee_{x}"], [f"spine_knee_{x}", f"spine_tip_{x}"]]
for j in range(8):
    joints[f"fang_{j}"] = [r2(FANG_AT[j].real), r2(FANG_AT[j].imag)]
    bones.append(["centre", f"fang_{j}"])

DESCRIPTION = (
    "Not the biggest thing in the hive — the loudest. A seated mass of six carapace segments round a mouth, each carrying an organ at its outer end, "
    "and the six fire in sequence, so the light travels around it like a voice going round a room; that rotation is the whole read. It has no limbs "
    "and does not walk, so the rig is in what it does instead: the segment under the firing organ swells and pushes out, the spine in the next seam "
    "rises out of the body past upright and lays back behind the wave (a two-bone horn, root and thorn), and the whole mass leans toward the light as "
    "it goes, so the sequence runs through the body as well as the light. The middle is an iris of eight fangs in a collar of gum over a vent that "
    "has never eaten anything, only shouted; it breathes open and shut in the idle, and the shout is it clenching and then being thrown wide. "
    "Gameplay slot unchanged (5:00 boss); body radius still ~38.\n\n"
    "Built on a radial rig (scripts/boss.py): every part rides a node — body, segment, organ, seam, spine root, thorn, mouth, fang — each a turn, "
    "scale and shift about its own joint, composed down the tree, and the tracks are solved from those, so a thorn never leaves its root nor a root "
    "its seam however far a clip swings them. The pale plates are the body's value (the floor is near-black); the flesh between them and the gum are "
    "earth and bruise; the hive's pink is only in the organs, the vent and — in the phases — the splits and halos. `shout` is the vent's clip "
    "rather than the organs': the sequence is the idle, and a shout that lit all six would be saying what `enraged` says. The `death` clip ends the "
    "voice the way the body states it: the light runs the ring once more, faster than it ever did alive, and then all six go out in the same beat."
)

doc = {
    "id": "ss.enemy.boss",
    "name": "Chorus",
    "description": DESCRIPTION,
    "tags": ["enemy", "boss"],
    "size": [SIZE, SIZE],
    "meta": {"radius": 38},
    "parts": PARTS,
    "variants": variants,
    "skeleton": {"joints": joints, "bones": bones},
    "animations": animations,
}

if __name__ == "__main__":
    ids = [p["id"] for p in PARTS]
    assert len(ids) == len(set(ids)), "duplicate part ids"
    write_doc(doc, os.path.normpath(OUT))
    print(f"wrote {os.path.normpath(OUT)}: {len(PARTS)} parts, " + ", ".join(f"{k} {len(v['tracks'])} tracks" for k, v in animations.items()))
