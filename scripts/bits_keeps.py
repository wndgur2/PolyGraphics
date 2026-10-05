"""The keeps: on each writer's locker lid, the one thing that writer's log kept (`ss.base.keep-<name>`).

    from bits_keeps import KEEP_PARTS
    parts = KEEP_PARTS["sol"]()        # the parts of ss.base.keep-sol

Each keep is its own 24 x 22 document. It is drawn about the document's
centre, and it rests on the lid line at y = FOOT (+7): set the document on its
locker so that line falls on the lid's top (the lid top is at about y = -8.5
in `ss.base.locker`, so the keep's centre goes at the locker's (0, -15.5)).
Everything stays inside x in [-12, 12], y in [-11, 11], with a soft shadow
at the foot; only Kano's cloth hangs below the line, over the lid's edge.

Kept, not new: each is handled and a little worn and set down on purpose —
one cartridge not pushed home, a crack dried into the cap, a chip off the
bowl, a dog-eared top page, a stake whose foot is stained to where it stood
in the ground.

Colour keeps to the camp's: what the expedition brought is cold, paper is
bone, jelly is gold, the fungus teal (here dull, with no light left in it),
the ruins' stone carapace, and the one pink is the dried film in Rowan's bowl.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw import *  # noqa: E402,F401,F403

FOOT = 7.0


# ---------------------------------------------------------------- geometry

def _arc(cx, cy, rx, ry, a0=0.0, a1=360.0, n=32):
    """Points round an ellipse from a0 to a1 degrees (0 is +x, 90 is down)."""
    pts = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    if abs(a1 - a0) >= 360:
        pts.pop()
    return pts


def _area(pts):
    return 0.5 * sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))


def _edge(pts, inside, cross):
    out = []
    for i in range(len(pts)):
        cur, prev = pts[i], pts[i - 1]
        if inside(cur):
            if not inside(prev):
                out.append(cross(prev, cur))
            out.append(cur)
        elif inside(prev):
            out.append(cross(prev, cur))
    return out


def _line_cross(a, b):
    def cross(p, q):
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p, q, a, b
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return cross


def _cut(subject, clipper):
    """The part of polygon `subject` inside the convex polygon `clipper`."""
    sgn = 1 if _area(clipper) > 0 else -1
    out = list(subject)
    for i in range(len(clipper)):
        if len(out) < 3:
            return []
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inside = lambda p, a=a, b=b: sgn * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) >= 0
        out = _edge(out, inside, _line_cross(a, b))
    return out if len(out) >= 3 else []


def _half(pts, nx, ny, d):
    """The part of polygon `pts` where nx*x + ny*y <= d."""
    a = (d * nx, d * ny)
    b = (a[0] - ny, a[1] + nx)
    out = _edge(pts, lambda p: nx * p[0] + ny * p[1] <= d, _line_cross(a, b))
    return out if len(out) >= 3 else []


def _strip(pts, w0, w1=None):
    """A polyline thickened into a polygon, `w0` wide at its start and `w1` at its end."""
    w1 = w0 if w1 is None else w1
    top, bot = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        w = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        top.append((x - dy / L * w, y + dx / L * w))
        bot.append((x + dy / L * w, y - dx / L * w))
    return top + bot[::-1]


def _turn(pts, deg, about=(0.0, 0.0)):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    ox, oy = about
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in pts]


def _poly(id, pts, fill, **kw):
    return P(id, poly(pts), fill, **kw)


def _clipped(id, subject, clipper, fill, **kw):
    c = _cut(subject, clipper)
    return [P(id, poly(c), fill, **kw)] if c else []


def _ink(w):
    return {"color": "$ink", "width": w}


def _deepen(parts, k):
    """Parts drawn about y = 0, stretched `k` times in y (unrotated parts only)."""
    out = []
    for p in parts:
        q = dict(p)
        sh = dict(p["shape"])
        if "at" in q:
            q["at"] = [q["at"][0], r2(q["at"][1] * k)]
        if sh["kind"] == "poly":
            sh["points"] = [[x, r2(y * k)] for x, y in sh["points"]]
        elif sh["kind"] == "rect":
            sh["h"] = r2(sh["h"] * k)
        elif sh["kind"] == "ellipse":
            sh["ry"] = r2(sh["ry"] * k)
        q["shape"] = sh
        out.append(q)
    return out


def _frayed(pts, w0, w1, teeth=((0.42, 0.55), (0.14, 0.22), (-0.12, 0.65), (-0.4, 0.3))):
    """A strip of cloth or cord along `pts` whose far end is frayed into uneven threads."""
    body = _strip(pts, w0, w1)
    h = len(body) // 2
    (ax, ay), (ex, ey) = pts[-2], pts[-1]
    L = math.hypot(ex - ax, ey - ay) or 1
    ux, uy = (ex - ax) / L, (ey - ay) / L
    px, py = -uy, ux
    tips = []
    for j, (off, ln) in enumerate(teeth):
        tips.append((ex + px * off * w1 + ux * ln, ey + py * off * w1 + uy * ln))
        if j < len(teeth) - 1:
            mid = (off + teeth[j + 1][0]) / 2
            tips.append((ex + px * mid * w1 - ux * 0.08, ey + py * mid * w1 - uy * 0.08))
    return body[:h] + tips + body[h:]


# ---------------------------------------------------------------- arin

def keep_arin():
    """Five spent emitter cartridges standing in a slate clip.

    Frost glass, empty — you see through them — each with a steel cap and a
    pale dried ring where the last of it stood. The fourth was not pushed
    home and stands proud and a little askew. The clip is a slate plate with
    a rounded socket cut for each tube and a finger between each pair,
    riveted at the ends. Foot (the clip's base) on FOOT.
    """
    xs = [-6.4, -3.2, 0.0, 3.2, 6.4]
    lift = [0.0, 0.0, 0.0, -0.8, 0.0]
    lean = [0.0, -1.2, 0.0, 3.0, 0.8]
    ring = [2.2, 0.4, 1.6, -0.6, 3.0]
    parts = [shadow("shadow", 0.4, 7.0, 10.8, 1.5, "0.42")]
    for i, x in enumerate(xs):
        t = f"t{i}"
        r = ring[i]
        tube = [
            P(t, R(2.8, 11, 1.3), "$frost.dark@0.45", stroke=INK_FINE),
            P(f"{t}_film", R(2.0, 5.3 - r, 0.8), "$bone.dark@0.16", at=(0, (r + 5.3) / 2)),
            P(f"{t}_ring", ell(1.12, 0.36), None, at=(0, r), stroke={"color": "$bone.dark@0.9", "width": 0.38}),
            P(f"{t}_far", R(0.45, 8.4, 0.22), "$frost@0.4", at=(0.8, 0.2)),
            P(f"{t}_lit", R(0.6, 8.6, 0.3), "$white@0.55", at=(-0.7, -0.4)),
            P(f"{t}_cap", R(3.3, 2.5, 0.8), "$steel", at=(0, -6.3), stroke=INK_FINE),
            P(f"{t}_cap_dk", R(0.9, 1.9, 0.35), "$steel.dark", at=(1.0, -6.2)),
            P(f"{t}_cap_lit", R(0.8, 1.6, 0.35), "$steel.light", at=(-0.9, -6.5)),
            P(f"{t}_crimp", R(3.0, 0.55, 0.2), "$steel.dark", at=(0, -4.95)),
        ]
        parts += placed(tube, (x, -0.7 + lift[i]), 1, lean[i])
    top = []
    for k in range(73):
        x = -9.0 + 18.0 * k / 72
        y = 1.7
        for c in xs:
            u = (x - c) / 1.35
            if abs(u) < 1:
                y = max(y, 1.7 + 1.0 * (1 - u * u) ** 0.6)
        top.append((x, y))
    clip_pts = [(-9.4, 2.3)] + top + [(9.4, 2.3), (9.4, 6.2), (8.6, 7.0), (-8.6, 7.0), (-9.4, 6.2)]
    parts += [
        *shaded("clip", clip_pts, "$slate", [(0, 2.45, "$slate.light"), (5.7, 7.2, "$slate.dark")], stroke=INK_HAIR),
        P("clip_rv_l", circ(0.55), "$slate.dark2", at=(-8.0, 4.4)),
        P("clip_rv_r", circ(0.55), "$slate.dark2", at=(8.0, 4.4)),
        P("clip_rv_l_lit", circ(0.22), "$slate.light@0.9", at=(-8.2, 4.2)),
        P("clip_rv_r_lit", circ(0.22), "$slate.light@0.9", at=(7.8, 4.2)),
        *scratches("scuff", 2.0, 4.6, 9, 1.2, 2, "$slate.light@0.65", 4),
    ]
    return parts


# ---------------------------------------------------------------- sol

def keep_sol():
    """The fungus cap Sol carried in a dead emitter: dull teal, no light in it any more.

    The camp's caps (`cap()` in draw.py) in the same build — a dome over a
    band of gills, a pale stem — but $spore.dark rather than $spore, dried:
    the rim gone wavy, a crack run up from it, dirt still on the foot.
    """
    rim = -0.4
    wob = lambda a: 1 + 0.035 * math.sin(math.radians(a) * 5 + 0.6)
    dome = []
    for k in range(29):
        a = 180 + 180 * k / 28
        dome.append((7.7 * wob(a) * math.cos(math.radians(a)), rim + 5.9 * wob(a) * math.sin(math.radians(a))))
    lip = _arc(0, rim, 7.7, 1.0, 0, 180, 16)
    # A V where the crack meets the rim.
    lip = [p for p in lip if not (2.6 < p[0] < 4.0)]
    k = next(i for i, p in enumerate(lip) if p[0] < 2.6)
    lip[k:k] = [(4.0, rim + 0.72), (3.35, rim - 0.5), (2.6, rim + 0.85)]
    cap_pts = dome + lip
    gills = _arc(0, rim + 0.2, 7.1, 2.7, 0, 180, 20)
    stem = [(-1.5, rim + 1.4), (1.3, rim + 1.4), (1.7, 3.6), (2.3, 5.6), (2.0, 6.7), (1.2, 7.05), (-1.6, 7.05), (-2.3, 6.5), (-2.2, 5.4), (-1.6, 3.6)]
    parts = [
        shadow("shadow", 0.6, 7.0, 6.4, 1.3, "0.45"),
        P("gills", poly(gills), "$spore.dark2", stroke=INK_HAIR),
    ]
    for i, a in enumerate(range(12, 180, 12)):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        p0 = (2.0 * ca, rim + 0.2 + 0.9 * sa)
        p1 = (6.8 * ca, rim + 0.2 + 2.55 * sa)
        parts.append(_poly(f"gill_{i}", _strip([p0, p1], 0.18, 0.36), "$ink@0.45"))
    cap_dk = _half(cap_pts, -0.45, -0.9, 0.2)
    cap_dust = _half(cap_pts, 0.55, 0.85, -4.2)
    parts += [
        *shaded("stem", stem, "$husk.dark", [(5.6, 7.2, "$sand@0.9")], stroke=INK_HAIR),
        _poly("stem_dk", _half(stem, -1, 0, -0.4), "$husk.dark2@0.7"),
        P("stem_lit", R(0.7, 3.6, 0.35), "$husk@0.9", at=(-1.0, 3.0), rot=-4),
        P("stem_dirt", R(1.2, 0.5, 0.25), "$soil@0.5", at=(0.6, 6.0)),
        # The cap: dull teal, dusty where the light lies on it, shaded under.
        P("cap", poly(cap_pts), "$spore.dark"),
        P("cap_dk", poly(cap_dk), "$spore.dark2@0.75"),
        P("cap_dust", poly(cap_dust), "$husk@0.2"),
        P("cap_lit", ell(2.2, 0.8), "$white@0.22", at=(-3.0, -4.3), rot=-24),
        P("spot_a", circ(0.75), "$spore.dark2@0.85", at=(-2.0, -3.4)),
        P("spot_b", circ(0.55), "$spore.dark2@0.85", at=(1.1, -4.6)),
        P("spot_c", circ(0.6), "$spore.dark2@0.8", at=(-5.0, -1.6)),
        P("spot_d", circ(0.45), "$spore.dark2@0.8", at=(5.2, -2.4)),
        # The crack, dried open from the rim, its lit lip on the left.
        _poly("crack_lip", _strip([(2.75, rim - 0.2), (2.35, -1.8), (2.95, -2.9), (2.0, -4.0), (2.3, -4.9)], 0.3, 0.12), "$husk@0.35"),
        _poly("crack", _strip([(3.35, rim - 0.4), (2.95, -1.8), (3.55, -2.9), (2.6, -4.0), (2.85, -4.9)], 0.6, 0.15), "$ink@0.8"),
        P("cap_rim", poly(cap_pts), None, stroke=INK_HAIR),
    ]
    return parts


# ---------------------------------------------------------------- haram

def keep_haram():
    """A moulted husk lying on its belly, head to the right.

    A hollow, segmented shell in husk white: five telescoped rings of abdomen
    tapering to the tail, the thorax split open along its back where it was
    shed (the dark of the hollow inside, the far flap curled up, the near
    edge catching the light), the head with an empty eye, a snapped antenna
    and an empty mouth, and stubs of legs under it, the far ones darker.
    """
    dy = 0.6
    segs = [(-8.7, 2.0, 1.4, 1.1), (-7.1, 2.4, 1.7, 1.8), (-5.2, 2.7, 1.9, 2.4), (-3.1, 2.9, 2.0, 2.8), (-1.0, 3.0, 2.0, 3.0)]
    thorax = (2.0, 2.6, 3.0, 3.4)
    head = (6.3, 3.2, 2.4, 2.4)
    far_legs = [[(1.4, 4.8), (0.5, 5.6), (0.1, 6.1)], [(3.6, 4.8), (4.4, 5.5), (4.5, 6.0)], [(6.2, 4.6), (7.4, 5.2), (7.9, 5.7)]]
    near_legs = [[(0.6, 4.8), (-0.3, 5.9), (-0.9, 6.4)], [(2.8, 5.0), (3.2, 5.9), (3.0, 6.4)], [(5.0, 4.6), (6.1, 5.7), (6.7, 6.3)]]
    near_legs = [[(x, y + dy) for x, y in leg] for leg in near_legs]
    parts = [shadow("shadow", -0.4, 7.0, 10.2, 1.5, "0.42")]
    for i, leg in enumerate(far_legs):
        pts = [(x + 0.5, y - 0.3 + dy) for x, y in leg]
        parts.append(_poly(f"leg_far_{i}", _strip(pts, 1.0, 0.8), "$husk.dark2", stroke=INK_FINE))
    # Contour pass: the whole body's ink edge, under its fills.
    body = [(f"seg_{i}", s) for i, s in enumerate(segs)] + [("thorax", thorax), ("head", head)]
    for id, (x, y, rx, ry) in body:
        parts.append(P(f"{id}_k", ell(rx, ry), "$ink", at=(x, y + dy), stroke=_ink(2.0)))
    for i, leg in enumerate(near_legs):
        parts.append(_poly(f"leg_{i}_k", _strip(leg, 1.05, 0.85), "$ink", stroke=_ink(1.6)))
    flap = [(0.0, 1.15), (0.7, 0.25), (1.3, 0.5), (2.1, -0.2), (2.8, 0.2), (3.5, 0.0), (4.4, 0.8), (3.5, 0.85), (2.2, 0.75), (0.9, 1.0)]
    flap = [(x, y + dy) for x, y in flap]
    parts.append(P("flap_k", poly(flap), "$ink", stroke=_ink(1.4)))
    for i, leg in enumerate(near_legs):
        parts.append(_poly(f"leg_{i}", _strip(leg, 1.05, 0.85), "$husk.dark"))
        x, y = leg[-1]
        parts.append(P(f"leg_{i}_end", ell(0.34, 0.22), "$coal", at=(x, y - 0.1)))
    # The rings of the abdomen, tail first, each lapping over the one behind.
    for id, (x, y, rx, ry) in body[:5]:
        pts = _arc(x, y + dy, rx, ry, n=28)
        parts += shaded(id, pts, "$husk", [(y + dy + ry * 0.3, y + dy + ry + 1, "$husk.dark")], stroke=INK_FINE)
        parts.append(P(f"{id}_lit", ell(rx * 0.5, 0.35), "$white@0.5", at=(x - rx * 0.15, y + dy - ry * 0.68)))
    x, y, rx, ry = thorax
    parts += shaded("thorax", _arc(x, y + dy, rx, ry, n=32), "$husk", [(y + dy + ry * 0.35, y + dy + ry + 1, "$husk.dark")], stroke=INK_FINE)
    x, y, rx, ry = head
    parts += shaded("head", _arc(x, y + dy, rx, ry, n=28), "$husk", [(y + dy + ry * 0.3, y + dy + ry + 1, "$husk.dark")], stroke=INK_FINE)
    split = [(-0.6, 1.45), (0.6, 0.85), (2.2, 0.65), (3.8, 0.8), (5.2, 1.4), (3.8, 1.55), (2.2, 1.6), (0.6, 1.6)]
    parts += [
        # The split down the back, where it came out: the far flap curled up
        # past the line of the back, the dark of the hollow, the near edge lit.
        P("flap", poly(flap), "$husk.dark"),
        P("flap_in", poly([(0.9, 1.0 + dy), (2.2, 0.75 + dy), (3.5, 0.85 + dy), (3.3, 0.55 + dy), (2.2, 0.4 + dy), (1.0, 0.7 + dy)]), "$husk.dark2"),
        P("split", poly([(x, y + dy) for x, y in split]), "$coal"),
        _poly("split_lip", _strip([(-0.3, 1.6 + dy), (0.8, 1.8 + dy), (2.2, 1.82 + dy), (3.7, 1.76 + dy), (4.8, 1.55 + dy)], 0.45, 0.25), "$white@0.75"),
        _poly("split_head", _strip([(5.1, 1.25 + dy), (6.0, 1.3 + dy), (7.0, 1.9 + dy)], 0.35, 0.12), "$ink@0.7"),
        _poly("split_tail", _strip([(-0.5, 1.3 + dy), (-1.6, 1.0 + dy)], 0.3, 0.1), "$ink@0.55"),
        # The head: an empty eye, an antenna snapped short, the open mouth.
        P("eye", ell(0.95, 0.85), "$husk.dark@0.7", at=(6.6, 2.6 + dy), stroke={"color": "$husk.dark2", "width": 0.3}),
        P("eye_lit", circ(0.28), "$white@0.7", at=(6.35, 2.35 + dy)),
        _poly("antenna", _strip([(7.4, 1.8 + dy), (8.3, 1.0 + dy), (9.2, 0.8 + dy)], 0.6, 0.45), "$husk.dark", stroke=INK_FINE),
        P("mouth", ell(0.85, 1.15), "$coal", at=(8.0, 4.1 + dy), stroke={"color": "$husk.dark2", "width": 0.35}),
        _poly("mandible", [(8.2, 5.0 + dy), (9.3, 5.0 + dy), (9.0, 5.5 + dy), (8.3, 5.6 + dy)], "$husk.dark", stroke=INK_FINE),
    ]
    return parts


# ---------------------------------------------------------------- mina

def keep_mina():
    """A palm-sized chunk of the burrow's wall, warm.

    Faceted: a lit broken top, the front face showing the wall's strata in
    rust earth, the right face turned into shade with the strata bending
    round onto it. A dark seam — the wall's pull — runs down through every
    layer, a vein of its own stuff with fibres off it; the warmth is an
    ember tint laid low and wide about it, clipped to the stone (no light
    leaves it). Two crumbs have come off it onto the lid.
    """
    out = [(-7.4, 7.0), (-7.9, 3.6), (-6.6, -0.2), (-3.4, -3.0), (1.0, -3.9), (5.2, -2.8), (7.6, 0.4), (7.8, 4.6), (6.0, 7.0)]
    top = [(-6.6, -0.2), (-3.4, -3.0), (1.0, -3.9), (5.2, -2.8), (4.4, -0.8), (0.2, 0.2), (-3.8, 0.8)]
    right = [(5.2, -2.8), (7.6, 0.4), (7.8, 4.6), (6.0, 7.0), (4.7, 6.8), (4.4, -0.8)]
    front = [(-7.4, 7.0), (-7.9, 3.6), (-6.6, -0.2), (-3.8, 0.8), (0.2, 0.2), (4.4, -0.8), (4.7, 6.8), (6.0, 7.0)]
    sl = math.tan(math.radians(-6))
    sr = math.tan(math.radians(24))

    def layer(y0, h, face):
        if face == "front":
            yl, yr = y0 - sl * 9, y0 + sl * 9
            return [(-9, yl - h / 2), (9, yr - h / 2), (9, yr + h / 2), (-9, yl + h / 2)]
        yb = y0 + sl * 4.5
        yl, yr = yb, yb + sr * 4.5
        return [(4.5, yl - h / 2), (9.0, yr - h / 2), (9.0, yr + h / 2), (4.5, yl + h / 2)]

    strata = [(1.5, 0.9, "$rust"), (2.9, 1.4, "$sand@0.9"), (4.25, 0.5, "$rust.dark@0.85"), (5.4, 1.1, "$rust.light2@0.6"), (6.6, 0.5, "$rust@0.8")]
    parts = [
        shadow("shadow", 0.2, 7.0, 9.0, 1.5, "0.45"),
        P("crumb_a", poly([(-0.8, 0.3), (-0.2, -0.5), (0.7, -0.2), (0.6, 0.4)]), "$rust.light", at=(-9.3, 6.6), stroke=INK_FINE),
        P("crumb_b", poly([(-0.5, 0.25), (0.0, -0.35), (0.5, 0.2)]), "$rust", at=(9.2, 6.8), stroke=INK_FINE),
        P("front", poly(front), "$rust.light"),
    ]
    for i, (y0, h, fill) in enumerate(strata):
        parts += _clipped(f"stratum_{i}", front, layer(y0, h, "front"), fill)
    parts.append(P("right", poly(right), "$rust.light"))
    for i, (y0, h, fill) in enumerate(strata):
        parts += _clipped(f"stratum_r{i}", right, layer(y0, h, "right"), fill)
    parts += [
        P("right_dk", poly(right), "$ink@0.3"),
        P("top", poly(top), "$rust.light2"),
        _poly("top_ridge", _strip([(-6.4, -0.1), (-3.8, 0.75), (0.2, 0.15), (4.4, -0.85)], 0.45), "$rust.light2@0.9"),
        P("top_lit", poly([(-5.4, -0.6), (-3.2, -2.5), (-0.6, -3.1), (-2.6, -1.6)]), "$white@0.14"),
        P("pit_a", ell(0.45, 0.25), "$rust@0.7", at=(2.4, -2.4)),
        P("pit_b", ell(0.35, 0.2), "$rust@0.7", at=(-2.4, -1.0)),
        P("pit_c", ell(0.3, 0.3), "$rust.dark@0.6", at=(-5.0, 3.8)),
    ]
    seam = [(-1.0, -3.75), (-0.7, -2.2), (0.0, -0.6), (0.9, 0.9), (1.4, 2.5), (1.2, 4.0), (1.7, 5.6), (2.3, 7.0)]
    parts += _clipped("warm", _strip(seam, 6.5, 8.0), out, "$ember@0.13")
    parts += _clipped("warm_in", _strip(seam, 3.0, 3.6), out, "$ember@0.1")
    parts += [
        _poly("seam_lip", _strip([(x - 0.5, y) for x, y in seam[1:]], 0.28, 0.32), "$rust.light2@0.6"),
        _poly("seam", _strip(seam, 0.8, 1.1), "$soil"),
        _poly("seam_vein", _strip([(x + 0.05, y) for x, y in seam[2:6]], 0.22, 0.18), "$rust@0.9"),
        _poly("seam_fibre_a", _strip([(1.4, 2.5), (2.4, 2.1), (3.4, 2.25)], 0.35, 0.12), "$soil@0.9"),
        _poly("seam_fibre_b", _strip([(1.2, 4.0), (0.2, 4.5), (-0.8, 4.4)], 0.32, 0.1), "$soil@0.9"),
        _poly("seam_fibre_c", _strip([(-0.7, -2.2), (-1.8, -1.9)], 0.28, 0.1), "$soil@0.8"),
        P("chunk_rim", poly(out), None, stroke=INK_HAIR),
    ]
    return parts


# ---------------------------------------------------------------- kano

def keep_kano():
    """Kano's road marker stake, lying on the lid, head to the left.

    A squared stake of weathered wood, lit along its top face, grain on its
    front. The notches are nicks cut into the top edge in a dense run of
    groups — 33, one for every ten of 330 days: six fives and three. A strip
    of cold cloth is wound twice round below the head and knotted, its two
    frayed tails hanging over the lid's edge. The point is splintered and
    worn and stained up to where it stood in the ground. Its far end lies a
    little further back on the lid, so it runs slightly uphill to the right.
    """
    L0, L1, tip = -10.7, 6.0, 10.9
    nx = []
    x = -6.7
    for g in (5, 5, 5, 5, 5, 5, 3):
        for k in range(g):
            nx.append(x)
            x += 0.3
        x += 0.42
    ytop = lambda x: -1.9 + 0.15 * (x - L0) / (L1 - L0) + 0.05 * math.sin(x * 1.3)
    ya = lambda x: -0.7 + 0.1 * (x - L0) / (L1 - L0)
    edge = [(L0 + 0.4, -2.05), (L0 + 1.2, ytop(L0 + 1.2)), (L0 + 2.2, ytop(L0 + 2.2))]
    for xn in nx:
        edge += [(xn - 0.14, ytop(xn - 0.14)), (xn, ytop(xn) + 0.55), (xn + 0.14, ytop(xn + 0.14))]
    edge += [(L1, ytop(L1))]
    point = [(tip - 0.35, 0.2), (tip, 0.5), (tip - 0.45, 0.95), (9.4, 0.95), (8.8, 1.45), (8.0, 1.15), (7.1, 1.75)]
    bottom = [(L1, 1.82)] + [(x, 1.82 + 0.05 * math.sin(x * 1.9)) for x in (3.0, 0.0, -3.0, -6.0, -9.0)]
    head = [(L0 + 0.5, 2.0), (L0 - 0.05, 1.7), (L0 - 0.25, 0.4), (L0 - 0.15, -1.5)]
    shaft = edge + point + bottom + head
    topf = edge + [(tip - 0.35, 0.2), (L1, ya(L1)), (L0 - 0.2, ya(L0)), (L0 - 0.15, -1.5)]
    stain = [(3.6, -3.0), (12.0, -3.0), (12.0, 3.0), (4.8, 3.0)]
    notches = []
    for i, xn in enumerate(nx):
        yt = ytop(xn)
        notches.append(P(f"notch_{i}", poly([(xn - 0.12, yt + 0.3), (xn + 0.12, yt + 0.3), (xn + 0.03, ya(xn) + 0.15), (xn - 0.05, ya(xn) + 0.15)]), "$ink@0.45"))
    local = [
        P("stake_k", poly(shaft), "$ink", stroke=_ink(2.0)),
        P("stake", poly(shaft), "$smoke.light"),
        *_clipped("stake_dk", shaft, [(-12, 1.05), (12, 1.05), (12, 3), (-12, 3)], "$smoke"),
        P("top", poly(topf), "$smoke.light2"),
        lit_edge("top_lit", L0 + 0.5, -9.4, -1.6, 0.4, "$white@0.3"),
        lit_edge("top_lit_b", -7.2, -6.9, -1.5, 0.4, "$white@0.3"),
        P("weather", ell(3.2, 0.9), "$smoke@0.35", at=(-6.0, 0.6)),
        _poly("grain_a", _strip([(-9.6, 0.15), (-5.0, 0.0), (-0.6, 0.2)], 0.24, 0.1), "$smoke@0.9"),
        _poly("grain_b", _strip([(-6.4, 0.8), (-1.0, 0.65), (4.0, 0.8)], 0.24, 0.1), "$smoke@0.9"),
        _poly("grain_c", _strip([(-2.4, 1.35), (2.5, 1.25), (6.6, 1.4)], 0.2, 0.08), "$smoke.dark@0.6"),
        P("knot", ell(0.6, 0.35), "$smoke.dark", at=(-2.8, 0.9)),
        P("knot_ring", ell(0.95, 0.55), None, at=(-2.8, 0.9), stroke={"color": "$smoke@0.9", "width": 0.2}),
        _poly("head_split", _strip([(L0 - 0.2, 0.15), (L0 + 1.4, 0.3), (L0 + 2.4, 0.2)], 0.38, 0.08), "$ink@0.7"),
        *notches,
        # Stained up to where it stood in the ground.
        *_clipped("stain", shaft, stain, "$sand@0.65"),
        *_clipped("stain_deep", shaft, [(7.4, -3), (12, -3), (12, 3), (8.2, 3)], "$soil@0.3"),
        _poly("stain_line", _strip([(3.8, -1.7), (4.3, 0.1), (4.8, 1.75)], 0.35), "$soil@0.45"),
        P("splinter", poly([(7.4, 1.3), (10.0, 1.6), (7.8, 1.68)]), "$smoke.light", stroke=INK_FINE),
        # The cloth, wound twice round below the head.
        P("wrap_a", poly([(-9.25, -2.3), (-8.35, -2.35), (-7.95, 2.3), (-8.85, 2.35)]), "$frost.dark", stroke=INK_HAIR),
        P("wrap_b", poly([(-8.45, -2.25), (-7.55, -2.2), (-7.4, 2.25), (-8.25, 2.3)]), "$frost.dark", stroke=INK_HAIR),
        P("wrap_a_lit", poly([(-9.1, -2.05), (-8.45, -2.1), (-8.35, -0.85), (-9.0, -0.85)]), "$frost@0.65"),
        P("wrap_b_lit", poly([(-8.3, -2.0), (-7.7, -1.95), (-7.65, -0.8), (-8.2, -0.8)]), "$frost@0.55"),
        P("wrap_crease", poly([(-8.2, -0.6), (-8.05, -0.6), (-7.85, 2.0), (-8.0, 2.0)]), "$frost.dark2@0.8"),
    ]
    rot, at, deep = -2.5, (0.0, 4.75), 1.12
    parts = [shadow("shadow", 0.0, 7.0, 11.0, 1.45, "0.42")]
    parts += placed(_deepen(local, deep), at, 1, rot)
    # The knot under it and the tails hanging over the lid's edge.
    kx, ky = _turn([(-8.2, 2.1 * deep)], rot)[0]
    kx, ky = kx + at[0], ky + at[1]
    tail_a = [(kx - 0.2, ky + 0.2), (kx - 0.55, ky + 1.1), (kx - 0.6, ky + 1.8), (kx - 0.95, ky + 2.35)]
    tail_b = [(kx + 0.3, ky + 0.2), (kx + 0.95, ky + 0.95), (kx + 1.3, ky + 1.6), (kx + 1.25, ky + 2.0)]
    parts += [
        # Each tail is drawn about the knot, so it can sway from there.
        P("tail_b", poly(moved(_frayed(tail_b, 1.35, 1.1), (-kx, -ky))), "$frost.dark2", at=(kx, ky), stroke=INK_HAIR),
        P("tail_a", poly(moved(_frayed(tail_a, 1.55, 1.3), (-kx, -ky))), "$frost.dark", at=(kx, ky), stroke=INK_HAIR),
        P("tail_a_lit", poly(moved(_strip([(p[0] - 0.35, p[1]) for p in tail_a[:3]], 0.35, 0.2), (-kx, -ky))), "$frost@0.55", at=(kx, ky)),
        P("bow_a", ell(0.85, 0.55), "$frost.dark", at=(kx - 0.55, ky - 0.05), rot=-25, stroke=INK_HAIR),
        P("bow_b", ell(0.8, 0.5), "$frost.dark", at=(kx + 0.55, ky + 0.05), rot=30, stroke=INK_HAIR),
        P("knot_cloth", ell(0.55, 0.5), "$frost.dark2", at=(kx, ky + 0.05), stroke=INK_FINE),
        P("knot_lit", ell(0.4, 0.2), "$frost@0.7", at=(kx - 0.7, ky - 0.25), rot=-25),
    ]
    return parts


# ---------------------------------------------------------------- eden

def keep_eden():
    """A small glass jar with a finger of royal jelly in the bottom.

    Frost glass on a thick base, a short threaded neck under a steel screw
    lid knurled round its side. In the bottom, the jelly: gold, its surface
    lighter, going to chitin in the shade and the deep. The lid has been off
    and is screwed back on not quite square.
    """
    jelly = rr(8.8, 3.8, 1.9, (0, 4.95))
    parts = [
        shadow("shadow", 0.4, 7.0, 6.6, 1.4, "0.45"),
        P("neck_k", R(7.2, 2.2, 0.5), "$ink", at=(0, -3.4), stroke=_ink(2.0)),
        P("glass_k", R(10.4, 9.8, 2.9), "$ink", at=(0, 2.1), stroke=_ink(2.0)),
        P("neck", R(7.2, 2.2, 0.5), "$frost.dark@0.6", at=(0, -3.4)),
        P("thread", R(7.0, 0.42, 0.2), "$frost@0.75", at=(0, -3.55), rot=-5),
        P("thread_b", R(5.0, 0.36, 0.18), "$frost@0.5", at=(-0.6, -2.95), rot=-5),
        P("glass", R(10.4, 9.8, 2.9), "$frost.dark@0.5", at=(0, 2.1)),
        P("glass_back", R(8.0, 7.4, 2.0), "$frost.dark2@0.3", at=(0.3, 1.7)),
        *shaded("jelly", jelly, "$gold", [(5.6, 7.0, "$chitin")], stroke=None),
        *_clipped("jelly_dk", jelly, [(2.9, 2), (5, 2), (5, 7), (2.4, 7)], "$chitin@0.75"),
        P("surface", ell(4.3, 0.72), "$gold.light2", at=(0, 3.2)),
        P("surface_edge", ell(4.3, 0.72), None, at=(0, 3.2), stroke={"color": "$chitin@0.55", "width": 0.3}),
        P("caustic", ell(1.4, 0.42), "$gold.light2@0.85", at=(-1.9, 5.3)),
        P("base", R(8.6, 0.9, 0.4), "$frost@0.3", at=(0, 6.45)),
        P("shine", R(1.1, 6.8, 0.55), "$white@0.5", at=(-3.9, 1.6)),
        P("shine_b", R(0.6, 2.2, 0.3), "$white@0.3", at=(3.9, 0.2)),
        P("shoulder_lit", R(3.0, 0.45, 0.22), "$white@0.4", at=(-1.6, -2.15)),
    ]
    # The lid, screwed down not quite square.
    lid = [
        *shaded("lid", rr(8.8, 3.0, 0.8), "$steel", [(-1.6, -0.7, "$steel.light"), (0.8, 1.6, "$steel.dark")], stroke=INK_HAIR),
        *[P(f"knurl_{i}", R(0.32, 1.5, 0.12), "$steel.dark@0.75", at=(-3.3 + i * 1.1, 0.2)) for i in range(7)],
        P("lid_scratch", R(2.2, 0.3, 0.15), "$steel.light@0.8", at=(1.6, -0.2), rot=-14),
    ]
    parts += placed(lid, (0.1, -5.25), 1, -2.5)
    return parts


# ---------------------------------------------------------------- rowan

def keep_rowan():
    """A stone bowl from the ruins, with the old pheromone dried in it.

    The ruins' stone ($carapace, as `ss.terrain.ruins` and the tablet are),
    a carved zigzag band under the rim between two grooves, a chip out of
    the rim at the back right showing the paler stone, a foot ring. Inside,
    the rim's shadow on the near wall and, pooled in the bottom, the dried
    film — pink, $pheromone, the one keep that carries it — crazed with
    cracks, with the ring of an older, higher level round it.
    """
    cx, cy, rx, ry = 0.0, -1.5, 8.6, 2.7
    a0, a1 = 298.0, 331.0
    rim_pt = lambda a: (cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))
    angle = lambda p: math.degrees(math.atan2((p[1] - cy) / ry, (p[0] - cx) / rx)) % 360
    # The chip: a jagged bite out of the back of the rim.
    bite = []
    for t, d in [(0.0, 0.0), (0.1, 0.5), (0.27, 0.36), (0.45, 0.78), (0.62, 0.58), (0.8, 0.7), (1.0, 0.0)]:
        x, y = rim_pt(a0 + (a1 - a0) * t)
        bite.append((x - 0.2 * d, y + 0.85 * d))
    full = _arc(cx, cy, rx, ry, n=72)
    rim_out = [p for p in full if angle(p) < a0] + bite + [p for p in full if angle(p) > a1]
    front = _arc(cx, cy, rx, ry, 0, 180, 40)
    wall = front[::-1] + [(-8.5, 0.6), (-7.7, 2.9), (-6.1, 4.8), (-4.9, 5.6), (-5.0, 6.3), (-4.7, 7.0), (4.7, 7.0), (5.0, 6.3), (4.9, 5.6), (6.1, 4.8), (7.7, 2.9), (8.5, 0.6)]
    inner = _arc(cx, cy + 0.15, 7.2, 2.0, n=48)
    lit_in = _cut(_arc(cx + 1.4, cy + 0.45, 6.6, 1.8, n=48), inner)
    parts = [
        shadow("shadow", 0.6, 7.0, 8.4, 1.5, "0.45"),
        P("wall", poly(wall), "$carapace", stroke=INK_HAIR),
        *_clipped("wall_lit", wall, [(-9, -2), (-5.6, -2), (-4.4, 8), (-9, 8)], "$carapace.light@0.55"),
        *_clipped("wall_dk", wall, [(3.4, -2), (9, -2), (9, 8), (1.6, 8)], "$carapace.dark@0.9"),
        *_clipped("foot", wall, [(-6, 5.75), (6, 5.75), (6, 7.2), (-6, 7.2)], "$carapace.dark2"),
    ]

    def band_y(a, off):
        return (cx + rx * math.cos(math.radians(a)) * (1 - 0.02 * off), cy + ry * math.sin(math.radians(a)) + off)

    groove_a = [band_y(a, 0.75) for a in range(14, 167, 8)]
    groove_b = [band_y(a, 2.5) for a in range(16, 165, 8)]
    zig = [band_y(a, 1.0 if i % 2 == 0 else 2.25) for i, a in enumerate(range(16, 165, 6))]
    parts += [
        _poly("groove_a", _strip(groove_a, 0.32), "$carapace.dark2"),
        _poly("zig", _strip(zig, 0.3), "$carapace.dark2@0.9"),
        _poly("groove_b", _strip(groove_b, 0.32), "$carapace.dark2"),
        _poly("groove_b_lit", _strip([(x, y + 0.32) for x, y in groove_b[:9]], 0.2), "$carapace.light@0.7"),
        P("pit_a", circ(0.32), "$carapace.dark2@0.9", at=(-3.4, 4.4)),
        P("pit_b", circ(0.24), "$carapace.dark2@0.9", at=(2.6, 5.0)),
        P("pit_c", circ(0.28), "$carapace.dark2@0.8", at=(-6.2, 2.8)),
        # The rim, chipped at the back right, and the bowl's inside.
        P("rim", poly(rim_out), "$carapace.light", stroke=INK_HAIR),
    ]
    # The break, the fresh stone paler, sloping from the bite into the bowl.
    sink = [0.0, 0.55, 0.6, 0.7, 0.65, 0.5, 0.0]
    face = bite + [(x + 0.15, y + d) for (x, y), d in zip(bite[::-1], sink[::-1])]
    rim_lit = [(cx + (rx - 0.55) * math.cos(math.radians(a)), cy + (ry - 0.32) * math.sin(math.radians(a))) for a in range(196, 256, 6)]
    parts += [
        _poly("rim_lit", _strip(rim_lit, 0.25, 0.4), "$white@0.3"),
        P("inside", poly(inner), "$carapace.dark2", stroke={"color": "$ink@0.6", "width": 0.45}),
        P("inside_lit", poly(lit_in), "$carapace.dark"),
        P("chip", poly(face), "$carapace.light2", stroke={"color": "$ink@0.55", "width": 0.3}),
        # The film: pooled in the bottom, dried and crazed, and the ring of
        # where it once stood higher.
        P("tide", ell(5.7, 1.45), None, at=(0.5, -1.15), stroke={"color": "$pheromone@0.45", "width": 0.35}),
        P("film", ell(4.5, 1.05), "$pheromone@0.85", at=(0.6, -0.95)),
        P("film_edge", ell(4.5, 1.05), None, at=(0.6, -0.95), stroke={"color": "$pheromone.dark@0.7", "width": 0.3}),
        P("film_lit", ell(1.6, 0.3), "$pheromone.light@0.8", at=(-0.9, -1.4)),
        _poly("craze_a", _strip([(-1.6, -0.3), (-0.6, -1.1), (0.4, -1.3)], 0.2), "$carapace.dark2@0.8"),
        _poly("craze_b", _strip([(1.2, -0.25), (2.0, -1.0), (3.3, -1.3)], 0.2), "$carapace.dark2@0.8"),
        _poly("craze_c", _strip([(-0.6, -1.1), (-1.2, -1.75)], 0.18), "$carapace.dark2@0.7"),
        _poly("craze_d", _strip([(2.0, -1.0), (2.6, -0.2)], 0.18), "$carapace.dark2@0.7"),
    ]
    return parts


# ---------------------------------------------------------------- teo

def keep_teo():
    """Teo's bundle: pages squared up, tied with cord, lying on the lid.

    Seen from above and in front: the top sheet (dog-eared, ruled with
    strokes of writing — no text) on the stack, sheets under it showing at
    the back, the page edges of the stack in front uneven, a cord across and
    a cord down the front, crossing in a square knot with two frayed ends.
    """
    ty0, ty1 = -4.6, 3.0
    top = [(-8.3, ty0), (8.0, ty0), (8.4, ty1), (-8.6, ty1)]
    edges = [(-0.3, 0.2, "$bone.dark"), (0.4, -0.5, "$husk"), (-0.6, 0.1, "$bone"), (0.2, 0.6, "$husk.dark"), (-0.2, -0.3, "$bone.dark"), (0.5, 0.3, "$husk"), (0.0, -0.2, "$bone.dark")]
    h = (FOOT - ty1) / len(edges)
    parts = [shadow("shadow", 0.2, 7.0, 10.0, 1.5, "0.45")]
    under_a = [(-7.6, ty0 - 0.7), (8.4, ty0 - 0.4), (8.9, ty1 - 1.0), (-7.2, ty1 - 1.4)]
    under_b = [(-8.9, ty0 + 0.3), (6.2, ty0 + 0.1), (6.4, ty1), (-9.0, ty1)]
    for id, pts in (("under_a", under_a), ("under_b", under_b), ("top", top)):
        parts.append(P(f"{id}_k", poly(pts), "$ink", stroke=_ink(2.0)))
    for i, (dl, dr, fill) in enumerate(edges):
        y = ty1 + h * (i + 0.5)
        parts.append(P(f"edge_{i}_k", R(17.0 + dr - dl, h + 0.02, 0.2), "$ink", at=(-0.1 + (dl + dr) / 2, y), stroke=_ink(2.0)))
    parts += [
        P("under_a", poly(under_a), "$husk.dark"),
        P("under_b", poly(under_b), "$bone.dark"),
    ]
    for i, (dl, dr, fill) in enumerate(edges):
        y = ty1 + h * (i + 0.5)
        parts.append(P(f"edge_{i}", R(17.0 + dr - dl, h + 0.02, 0.2), fill, at=(-0.1 + (dl + dr) / 2, y)))
        if i:
            parts.append(P(f"edge_{i}_ln", R(16.4, 0.16, 0.08), "$ink@0.3", at=(-0.1, y - h / 2)))
    parts += [
        P("edges_dk", R(17.4, 1.5, 0.4), "$ink@0.2", at=(0, FOOT - 0.75)),
        P("top", poly(top), "$bone"),
        P("top_dk", poly([(-8.5, 1.6), (8.35, 1.6), (8.4, ty1), (-8.6, ty1)]), "$bone.dark@0.45"),
        lit_edge("top_lit", -7.6, 2.0, ty0 + 0.45, 0.5, "$white@0.55"),
        P("dog_ear", poly([(6.0, ty0), (8.0, ty0), (8.1, ty0 + 1.6)]), "$husk.dark", stroke=INK_FINE),
        P("dog_ear_fold", poly([(6.0, ty0), (8.1, ty0 + 1.6), (6.5, ty0 + 1.1)]), "$bone.light@0.9", stroke=INK_FINE),
    ]
    lines = [(-3.3, [(-7.0, -3.6), (-3.0, 0.6), (1.2, 4.6)]),
             (-2.0, [(-7.0, -4.4), (-3.8, -0.6), (0.0, 5.6)]),
             (-0.7, [(-7.0, -5.2), (-4.6, 1.8), (2.4, 4.0)]),
             (0.6, [(-7.0, -2.4), (-1.8, 3.4)]),
             (1.9, [(-7.0, -4.8), (-4.2, -1.0)])]
    for i, (y, words) in enumerate(lines):
        for j, (x0, x1) in enumerate(words):
            parts.append(P(f"ln_{i}_{j}", R(x1 - x0, 0.45, 0.2), "$slate.dark@0.55", at=((x0 + x1) / 2, y + 0.012 * (x0 + x1))))
    kx, ky = -1.6, -0.9
    cord_h = [(-8.9, -0.6), (-4.0, -0.82), (kx, ky), (3.0, -0.95), (8.7, -1.1)]
    cord_v = [(-1.3, ty0 - 0.3), (kx, ky), (-1.9, ty1), (-1.9, 5.0), (-1.85, FOOT + 0.2)]
    end_a = [(kx + 0.5, ky + 0.3), (kx + 1.5, ky + 1.0), (kx + 2.8, ky + 1.25)]
    end_b = [(kx - 0.4, ky + 0.4), (kx - 1.1, ky + 1.5), (kx - 1.25, ky + 2.5)]
    fine = ((0.4, 0.35), (0.0, 0.15), (-0.4, 0.4))
    parts += [
        _poly("cord_h", _strip(cord_h, 0.95), "$bone.dark2", stroke=INK_FINE),
        _poly("cord_v", _strip(cord_v, 0.95), "$bone.dark2", stroke=INK_FINE),
        P("cord_v_pinch", R(2.6, 0.5, 0.25), "$ink@0.3", at=(-1.9, ty1 + 0.25)),
        _poly("cord_h_lit", _strip([(-8.4, -0.85), (-4.0, -1.05), (-2.8, -1.1)], 0.25), "$bone@0.6"),
        P("end_a", poly(_frayed(end_a, 0.7, 0.55, fine)), "$bone.dark2", stroke=INK_FINE),
        P("end_b", poly(_frayed(end_b, 0.7, 0.55, fine)), "$bone.dark2", stroke=INK_FINE),
        P("loop_a", ell(0.95, 0.6), "$bone.dark2", at=(kx - 0.55, ky - 0.15), rot=-35, stroke=INK_FINE),
        P("loop_b", ell(0.95, 0.6), "$bone.dark2", at=(kx + 0.55, ky + 0.1), rot=35, stroke=INK_FINE),
        P("loop_a_lit", ell(0.45, 0.2), "$bone@0.65", at=(kx - 0.75, ky - 0.4), rot=-35),
        P("knot_lit", ell(0.35, 0.18), "$bone@0.55", at=(kx + 0.35, ky - 0.15), rot=35),
    ]
    return parts


KEEP_PARTS = {
    "arin": keep_arin,
    "sol": keep_sol,
    "haram": keep_haram,
    "mina": keep_mina,
    "kano": keep_kano,
    "eden": keep_eden,
    "rowan": keep_rowan,
    "teo": keep_teo,
}
