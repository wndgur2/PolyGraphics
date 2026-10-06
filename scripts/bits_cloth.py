"""Cloth: the expedition's soft things — a rolled bedroll, a sleeping bag laid out, a pillow (or a folded jacket),
a sack of stores, a coil of cord, a canvas door flap tied back, a strip of cloth knotted on and blowing.

    from bits_cloth import bedroll, bed, pillow, sack, rope_coil, flap, streamer, streamer_tracks

Cloth is the expedition's own, so it is cold — slate, steel, frost — with bone
for cord and stitching, and it reads through its folds, seams and stitches.
Each helper draws one thing at its natural size in the camp about its own
origin (given in its docstring) and sets it down with `placed()`; every id is
built from `prefix`. Light from the upper left: one lit edge per mass, shade
lower right, a dark line where it rests.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw import *  # noqa: E402,F401,F403

# The cloths. `base` is the mass, `lit` the side the light finds, `shade` the
# side it doesn't, `deep` a seam or a crease; `lining` and `bind` are the inside
# of a bag and the tape round its edge.
SLATE = {"base": "$slate.light", "lit": "$slate.light2", "shade": "$slate", "deep": "$slate.dark",
         "lining": "$frost.dark", "lining_lit": "$frost", "lining_shade": "$frost.dark2", "bind": "$steel"}
# Canvas: the stores' sacks — the expedition's, a step lighter than its bedding.
CANVAS = {"base": "$steel.dark", "lit": "$steel", "shade": "$slate", "deep": "$slate.dark",
          "lining": "$slate.light", "lining_lit": "$slate.light2", "lining_shade": "$slate", "bind": "$slate.dark"}
# Husk: cloth that is not the expedition's (woven from the field's own fibre). Warm — use only for that.
HUSK = {"base": "$husk.dark", "lit": "$husk", "shade": "$husk.dark2", "deep": "$sand",
        "lining": "$husk", "lining_lit": "$husk.light", "lining_shade": "$husk.dark", "bind": "$sand.light"}
PALETTES = {"slate": SLATE, "canvas": CANVAS, "husk": HUSK}

CORD = "$bone.dark"
CORD_LIT = "$bone"
STITCH = "$bone@0.8"
LIGHT = (-0.55, -0.83)  # the way the light comes from (up and a little left), as a direction


def _pal(p):
    return PALETTES[p] if isinstance(p, str) else p


# ---------------------------------------------------------------- geometry

def _lerp(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def _on_ell(cx, cy, rx, ry, a):
    a = math.radians(a)
    return (cx + rx * math.cos(a), cy + ry * math.sin(a))


def _arc(cx, cy, rx, ry, a0, a1, n=16):
    """Points along an ellipse from a0 to a1 degrees (0 is +x, turning clockwise on screen)."""
    return [_on_ell(cx, cy, rx, ry, a0 + (a1 - a0) * k / n) for k in range(n + 1)]


def _quad(p0, p1, p2, n=10):
    out = []
    for k in range(n + 1):
        t = k / n
        a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t * t
        out.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    return out


def _spline(pts, n=6, closed=True):
    """A Catmull-Rom curve through `pts`."""
    out, m = [], len(pts)
    for i in range(m if closed else m - 1):
        p0 = pts[(i - 1) % m] if closed else pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[(i + 1) % m]
        p3 = pts[(i + 2) % m] if closed else pts[min(i + 2, m - 1)]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * (2 * p1[j] + (p2[j] - p0[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (3 * p1[j] - p0[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


def _keep(pts, f):
    """The part of polygon `pts` where f(p) >= 0 (f linear)."""
    out = []
    for i in range(len(pts)):
        cur, prev = pts[i], pts[i - 1]
        fc, fp = f(cur), f(prev)
        if fc >= 0:
            if fp < 0:
                out.append(_lerp(prev, cur, fp / (fp - fc)))
            out.append(cur)
        elif fp >= 0:
            out.append(_lerp(prev, cur, fp / (fp - fc)))
    return out


def _band_of(pts, d, lo, hi):
    """The part of polygon `pts` whose projection on direction `d` lies in [lo, hi]."""
    n = math.hypot(*d)
    dx, dy = d[0] / n, d[1] / n
    pts = _keep(pts, lambda p: p[0] * dx + p[1] * dy - lo)
    return _keep(pts, lambda p: hi - (p[0] * dx + p[1] * dy)) if pts else pts


def _lit_cuts(id, pts, cuts, d=LIGHT):
    """Flat value bands across a mass along the light: each (lo, hi, fill) is the strip whose projection on `d` is in [lo, hi]."""
    out = []
    for i, (lo, hi, fill) in enumerate(cuts):
        c = _band_of(pts, d, lo, hi)
        if len(c) >= 3:
            out.append(P(f"{id}_v{i}", poly(c), fill))
    return out


def _proj(pts, d=LIGHT):
    n = math.hypot(*d)
    v = [(x * d[0] + y * d[1]) / n for x, y in pts]
    return min(v), max(v)


def _extrude(pts, th):
    """A convex-ish outline and itself `th` lower, as one outline: a flat thing seen from above with its front edge showing."""
    i0 = min(range(len(pts)), key=lambda i: (pts[i][0], pts[i][1]))
    i1 = max(range(len(pts)), key=lambda i: (pts[i][0], -pts[i][1]))
    ring = pts[i0:] + pts[:i0]
    j = (i1 - i0) % len(pts)
    a, b = ring[:j + 1], ring[j:] + ring[:1]
    lower, upper = (a, b) if sum(p[1] for p in a) / len(a) > sum(p[1] for p in b) / len(b) else (b, a)
    if lower[0] != ring[0]:
        lower, upper = lower[::-1], upper[::-1]
    # lower runs left -> right; drop it by th and close over the upper chain right -> left
    if lower[0][0] > lower[-1][0]:
        lower = lower[::-1]
    if upper[0][0] < upper[-1][0]:
        upper = upper[::-1]
    return [(x, y + th) for x, y in lower] + upper


def _taper(id, pts, w0, w1, fill, opacity=None):
    """A line through `pts` that narrows from w0 to w1: a crease, a cord's end."""
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + math.dist(pts[i - 1], pts[i]))
    total = acc[-1] or 1
    top, bot = [], []
    for i, (x, y) in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        w = w0 + (w1 - w0) * acc[i] / total
        nx, ny = -dy / n * w / 2, dx / n * w / 2
        top.append((x + nx, y + ny))
        bot.append((x - nx, y - ny))
    return P(id, poly(top + bot[::-1]), fill, opacity=opacity)


def _spindle(id, pts, w, fill, opacity=None):
    """A line through `pts` that swells to `w` in the middle and comes to nothing at both ends: a soft fold."""
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + math.dist(pts[i - 1], pts[i]))
    total = acc[-1] or 1
    top, bot = [], []
    for i, (x, y) in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        ww = max(0.08, w * max(0.0, math.sin(math.pi * acc[i] / total)) ** 0.8)
        nx, ny = -dy / n * ww / 2, dx / n * ww / 2
        top.append((x + nx, y + ny))
        bot.append((x - nx, y - ny))
    return P(id, poly(top + bot[::-1]), fill, opacity=opacity)


def _cord(id, pts, w, fill=CORD, lit=CORD_LIT, edge="$ink@0.85", pivot=None):
    """A cord or a strap: an ink edge under it, the cord, and a thread of light along its upper-left side.
    With `pivot`, the parts are placed there (their points relative to it), so a `rot` track swings them about it."""
    out = [band(f"{id}_edge", pts, w + 0.7, edge), band(id, pts, w, fill)]
    if lit:
        off = [(x - 0.16 * w, y - 0.22 * w) for x, y in pts]
        out.append(band(f"{id}_lit", off, w * 0.34, lit))
    if pivot:
        for q in out:
            q["shape"] = poly([(x - pivot[0], y - pivot[1]) for x, y in q["shape"]["points"]])
            q["at"] = [r2(pivot[0]), r2(pivot[1])]
    return out


def _stitches(prefix, pts, n, size=1.1, fill=STITCH, w=0.45):
    """`n` short stitches evenly along a polyline, each lying along it."""
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + math.dist(pts[i - 1], pts[i]))
    out = []
    for k in range(n):
        d = acc[-1] * (k + 0.5) / n
        i = next(i for i in range(1, len(pts)) if acc[i] >= d)
        t = (d - acc[i - 1]) / ((acc[i] - acc[i - 1]) or 1)
        p = _lerp(pts[i - 1], pts[i], t)
        ang = math.degrees(math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0]))
        out.append(P(f"{prefix}_{k}", R(size, w, w / 2), fill, at=p, rot=ang))
    return out


def _mirror(parts):
    """The same parts mirrored left for right (for a thing drawn about x = 0)."""
    out = []
    for p in parts:
        q = dict(p)
        if "at" in q:
            q["at"] = [-q["at"][0], q["at"][1]]
        if "rot" in q:
            q["rot"] = -q["rot"]
        sh = dict(q["shape"])
        if sh["kind"] == "poly":
            sh["points"] = [[-x, y] for x, y in sh["points"]][::-1]
        elif sh["kind"] == "ring" and ("from" in sh or "to" in sh):
            a, b = sh.get("from", 0), sh.get("to", 360)
            sh["from"], sh["to"] = 180 - b, 180 - a
        q["shape"] = sh
        out.append(q)
    return out


# ================================================================ the bedroll

def bedroll(prefix, x, y, s=1.0, rot=0.0, length=38.0, r=6.5, cloth="slate", strap="$slate.dark", loop=True):
    """A sleeping bag rolled up and strapped, lying on its side, its end turned to us on the left showing the roll's spiral.

    Origin: on the ground under the middle of the roll. At s=1 it spans x -19..19, y -16.6..2 (the roll is
    38 x 13; the carry loop rises 3.6 above it, a strap tail lies on the ground in front). `length`/`r` size
    the roll, `cloth` is a palette name, `strap` the webbing colour, `loop` the bone carry loop between the straps.
    Parts: `<prefix>_loop` (+ `_edge`, `_lit`), `<prefix>_tail_a`/`_tail_b` (+ `_edge`, `_lit`), `<prefix>_end_spiral`.
    """
    p = _pal(cloth)
    L = length
    e = r * 0.62                       # the end, foreshortened: as tall as the roll, this deep
    cy = -r
    xl, xr = -L / 2 + e, L / 2 - e     # near (left) and far (right) end centres
    span = xr - xl
    pitch = span / 6
    seam_xs = [xl + pitch * k for k in (1, 2, 3, 4, 5)]
    strap_xs = [xl + pitch * 1.5, xl + pitch * 4.5]

    def pinch(xx):
        d = sum(0.3 * math.exp(-((xx - sx) / 1.5) ** 2) for sx in seam_xs)
        d += sum(1.0 * math.exp(-((xx - sx) / 1.8) ** 2) for sx in strap_xs)
        return d

    n = int(span / 0.5)
    top = [(xl + span * k / n, cy - r + pinch(xl + span * k / n)) for k in range(n + 1)]
    body = top + _arc(xr, cy, e, r, -90, 90, 14)[1:] + [(xl, 0.0)] + _arc(xl, cy, e, r, 90, 270, 14)[1:-1]

    parts = [
        shadow(f"{prefix}_shadow", 1.5, 0.6, L / 2 + 1.5, 2.6, "0.42"),
        ao(f"{prefix}_ao", 0.6, -0.1, L - 3, 1.8, 0.5),
    ]
    # The roll: lit along its top, shaded under, darkest where it rests.
    parts += shaded(f"{prefix}_roll", body, p["base"], [
        (cy - r - 1, cy - r * 0.42, p["lit"]),
        (cy + r * 0.34, cy + r * 0.78, p["shade"]),
        (cy + r * 0.78, 1, p["deep"]),
    ], stroke=None)
    parts.append(P(f"{prefix}_roll_far", poly(clip(body, 0, xr + e * 0.5, xr + e + 1)), f"{p['deep']}@0.35"))
    # Quilting round the roll: a stitched-down line in each valley, the next puff catching the light beside it.
    for i, sx in enumerate(seam_xs):
        k = (r - 0.35) / r
        arc = _arc(sx, cy, e * k, r - 0.35, -90, 88, 14)
        parts.append(band(f"{prefix}_seam_{i}_lit", [(px + 0.6, py) for px, py in arc[2:-1]], 0.5, f"{p['lit']}@0.7"))
        parts.append(band(f"{prefix}_seam_{i}", arc, 0.5, f"{p['deep']}@0.8"))
    # The outer edge of the roll lapping over, low on its front.
    lap_a = 38
    ly = cy + r * math.sin(math.radians(lap_a))
    lx0, lx1 = xl + e * math.cos(math.radians(lap_a)), xr + e * math.cos(math.radians(lap_a))
    parts += [
        P(f"{prefix}_lap_shade", R(lx1 - lx0, 0.8, 0.4), f"{p['deep']}@0.9", at=((lx0 + lx1) / 2, ly + 0.45)),
        P(f"{prefix}_lap", R(lx1 - lx0, 0.45, 0.2), f"{p['lit']}@0.8", at=((lx0 + lx1) / 2, ly - 0.1)),
    ]
    parts.append(P(f"{prefix}_roll_rim", poly(body), None, stroke=INK_HAIR))
    # The straps, sunk into the roll where they cinch it, each with its buckle and a loose tail.
    sk = (r - 0.55) / r
    for j, sx in enumerate(strap_xs):
        tag = "ab"[j]
        rx, ry = e * sk, r - 0.55
        # a band round a cylinder: the same arc either side of the strap's middle
        sp = _arc(sx - 1.1, cy, rx, ry, -90, 90, 18) + _arc(sx + 1.1, cy, rx, ry, 90, -90, 18)
        sp = clip(sp, 1, cy - r + 0.75, 0.2)
        parts.append(P(f"{prefix}_strap_{tag}", poly(sp), strap))
        parts.append(P(f"{prefix}_strap_{tag}_lit", poly(clip(_arc(sx - 1.1, cy, rx, ry, -90, -40, 6) + _arc(sx - 0.3, cy, rx, ry, -40, -90, 6), 1, cy - r + 0.75, 0)), f"{p['lit']}@0.3"))
        ab = 14
        bp = _on_ell(sx, cy, rx, ry, ab)
        tan = math.degrees(math.atan2(ry * math.cos(math.radians(ab)), -rx * math.sin(math.radians(ab))))
        # The tail goes on through the buckle, peels off the roll and drops to the ground.
        if j == 0:
            tail = [bp, _on_ell(sx, cy, rx + 0.25, ry + 0.25, 36), _on_ell(sx, cy, rx + 1.0, ry + 0.6, 56),
                    (sx + rx * 0.55 + 1.6, 0.3), (sx + rx * 0.55 + 3.6, 1.0)]
        else:
            tail = [bp, _on_ell(sx, cy, rx + 0.25, ry + 0.25, 34), (sx + rx * 0.7 + 1.9, cy + ry * 0.62)]
        tail = _spline(tail, 4, closed=False)
        parts += _cord(f"{prefix}_tail_{tag}", tail, 1.7, p["shade"], lit=p["base"], edge="$ink@0.8")
        parts += [
            P(f"{prefix}_buckle_{tag}", R(2.0, 3.1, 0.5), "$steel", at=bp, rot=tan, stroke=INK_FINE),
            P(f"{prefix}_buckle_{tag}_bar", R(0.7, 2.0, 0.3), strap, at=bp, rot=tan),
            P(f"{prefix}_buckle_{tag}_lit", circ(0.38), "$white@0.7", at=(bp[0] - 0.45, bp[1] - 0.95)),
        ]
    # The end: the roll's spiral, each wrap shell outside and lining in, the outer wrap ending where it laps.
    parts.append(P(f"{prefix}_end", ell(e, r), p["base"], at=(xl, cy), stroke=INK_HAIR))
    turns, n = 2.3, 110
    spiral = []
    for k in range(n + 1):
        t = k / n
        a = math.radians(lap_a - 360 * turns * (1 - t))
        rho = 0.18 + 0.82 * t
        ox, oy = 0.5 * (1 - t), -0.6 * (1 - t)
        spiral.append((xl + ox + e * rho * math.cos(a), cy + oy + r * rho * math.sin(a)))
    lining = []
    for k in range(n + 1):
        t = k / n
        a = math.radians(lap_a - 360 * turns * (1 - t))
        rho = 0.18 + 0.82 * t - 0.085
        ox, oy = 0.5 * (1 - t), -0.6 * (1 - t)
        lining.append((xl + ox + e * rho * math.cos(a), cy + oy + r * rho * math.sin(a)))
    parts += [
        P(f"{prefix}_end_shade", poly(_arc(xl, cy, e, r, -60, 120, 16)), f"{p['shade']}@0.45"),
        _taper(f"{prefix}_end_lining", lining[6:], 0.5, 0.8, p["lining"]),
        _taper(f"{prefix}_end_spiral", spiral, 0.45, 0.7, p["deep"]),
        P(f"{prefix}_end_core", ell(e * 0.17, r * 0.15), "$ink@0.8", at=(xl + 0.45, cy - 0.5)),
        P(f"{prefix}_end_rim", ell(e, r), None, at=(xl, cy), stroke=INK_HAIR),
    ]
    # The carry loop, bone cord, from one strap over the top to the other.
    if loop:
        a, b = strap_xs
        ty = cy - r + 1.0
        parts += _cord(f"{prefix}_loop", _quad((a + 0.4, ty), ((a + b) / 2, ty - 7.6), (b - 0.4, ty), 14), 1.0)
    return placed(parts, (x, y), s, rot)


# ================================================================ the bed

def bed(prefix, x, y, s=1.0, rot=0.0, length=62.0, depth=18.0, turned=True, dent=True, cloth="slate"):
    """A sleeping bag laid out on the ground, seen three-quarters from above, the head to the left.

    Quilted in channels across its length, bound round the edge, the top turned back at the head showing the
    lighter lining (the zip pull where the opening stops), soft folds, and the long dent where somebody lay.
    Origin: the centre. At s=1 it spans x -length/2..length/2, y -depth/2..depth/2 (the near edge's
    thickness included). `turned`: the top turned back at the head; `dent`: slept in. `cloth`: palette name.
    With `turned`, the opening at the head (`<prefix>_open`) runs from the head to about 0.25..0.33 of the
    length — that is where a pillow goes (for length 62, centre it about 9 right of the head end and 4 up).
    Parts: `<prefix>_flap` + `_flap_lining` (the turned-back top), `<prefix>_dent`.
    """
    p = _pal(cloth)
    L, D = length, depth
    th = 2.6                 # the bag's thickness, showing along its near edge
    H = D - th               # the top, foreshortened
    ins = 2.6                # the far edge looks this much shorter at each end

    def pt(u, v):
        t = v / H
        x0, x1 = -L / 2 + ins * (1 - t), L / 2 - ins * (1 - t)
        return (x0 + (x1 - x0) * u / L, -D / 2 + v)

    nch = max(3, round(L / 7.6))
    pitch = L / nch
    chans = [pitch * k for k in range(1, nch)]

    def outline_uv(u0, v0, u1, v1, cu, cv, puff):
        """A rounded rectangle in the bag's own (u, v), its long edges puffed out between the channels."""
        pts = []

        def corner(cx, cy, a0):
            for k in range(6):
                a = math.radians(a0 + 90 * k / 5)
                pts.append((cx + cu * math.cos(a), cy + cv * math.sin(a)))

        corner(u1 - cu, v0 + cv, -90)
        corner(u1 - cu, v1 - cv, 0)
        m = int((u1 - u0 - 2 * cu) / 0.8)
        for k in range(1, m):
            u = u1 - cu - (u1 - u0 - 2 * cu) * k / m
            pts.append((u, v1 + puff * abs(math.sin(math.pi * u / pitch))))
        corner(u0 + cu, v1 - cv, 90)
        corner(u0 + cu, v0 + cv, 180)
        for k in range(1, m):
            u = u0 + cu + (u1 - u0 - 2 * cu) * k / m
            pts.append((u, v0 - puff * 0.6 * abs(math.sin(math.pi * u / pitch))))
        return pts

    out_uv = outline_uv(0, 0, L, H, 4.2, 2.6, 0.5)
    in_uv = outline_uv(1.2, 0.9, L - 1.2, H - 0.9, 3.4, 1.9, 0.45)
    top = [pt(*q) for q in out_uv]
    inner = [pt(*q) for q in in_uv]
    sil = _extrude(top, th)

    parts = [
        P(f"{prefix}_ao", poly([(a + 0.8, b + 0.9) for a, b in sil]), "$ink@0.35"),
        P(f"{prefix}_side", poly(sil), p["shade"]),
    ]
    # The channels carry on down the near edge.
    for i, u in enumerate(chans):
        a, b = pt(u, H), pt(u, H)
        parts.append(P(f"{prefix}_side_seam_{i}", poly([(a[0] - 0.25, a[1]), (a[0] + 0.25, a[1]), (b[0] + 0.25, b[1] + th), (b[0] - 0.25, b[1] + th)]), f"{p['deep']}@0.8"))
    parts += [
        P(f"{prefix}_bind", poly(top), p["bind"]),
        P(f"{prefix}_top", poly(inner), p["base"]),
    ]
    # Quilted channels across the bag: each a puff, lit on its left, falling into shade before the next seam.
    for i, u in enumerate(chans):
        sh = [pt(u - 2.2, 1.0), pt(u, 1.0), pt(u, H - 1.0), pt(u - 2.2, H - 1.0)]
        parts += [
            P(f"{prefix}_chan_{i}_shade", poly(sh), f"{p['shade']}@0.4"),
            band(f"{prefix}_chan_{i}_lit", [pt(u + 0.75, 1.3), pt(u + 0.75, H - 1.3)], 0.6, f"{p['lit']}@0.75"),
            band(f"{prefix}_chan_{i}", [pt(u, 0.9), pt(u, H - 0.9)], 0.55, f"{p['deep']}@0.85"),
        ]
    # Where somebody lay: a long shallow hollow the shape of them, shoulders to feet, dark on its far
    # (upper-left) wall and lit on its near one.
    if dent:
        body = [(0.16, 0.0), (0.2, 0.2), (0.3, 0.27), (0.42, 0.21), (0.56, 0.25), (0.7, 0.17), (0.84, 0.13), (0.9, 0.0),
                (0.84, -0.12), (0.7, -0.16), (0.56, -0.23), (0.42, -0.19), (0.3, -0.25), (0.2, -0.19)]
        hollow = [pt(L * a, H * (0.5 + b)) for a, b in _spline(body, 4)]
        core = [pt(L * (0.5 + (a - 0.5) * 0.7) - 0.6, H * (0.47 + b * 0.55)) for a, b in _spline(body, 4)]
        parts += [
            P(f"{prefix}_dent_lit", poly([(a + 0.7, b + 0.7) for a, b in hollow]), f"{p['lit']}@0.2"),
            P(f"{prefix}_dent", poly(hollow), f"{p['shade']}@0.38"),
            P(f"{prefix}_dent_deep", poly(core), f"{p['shade']}@0.25"),
        ]
    # Soft folds: one pulled out from where the opening stops, one across the foot.
    uA = L * 0.47
    for i, (a, c, b, w) in enumerate([((uA + 1.5, H - 1.2), (uA + 5, H * 0.72), (uA + 10, H * 0.62), 1.3),
                                      ((L - 2.5, H * 0.18), (L - 5.0, H * 0.45), (L - 8.5, H * 0.8), 1.2)]):
        crv = _quad(pt(*a), pt(*c), pt(*b), 12)
        parts += [
            _spindle(f"{prefix}_fold_{i}_lit", [(q[0] - 0.9, q[1] - 0.2) for q in crv], w * 0.8, f"{p['lit']}@0.6"),
            _spindle(f"{prefix}_fold_{i}", crv, w, f"{p['shade']}@0.6"),
        ]
    # The top turned back at the head, thrown open from the near side: the head of the bag shows the lining
    # of its under half, and the turned-back top lies across it lining up, its bound edge still bound.
    if turned:
        f0, f1 = L * 0.25, L * 0.33            # the fold, at the far and near edges
        e0, e1 = f0 + L * 0.09, f1 + L * 0.12  # the turned-back top's bound edge
        fold = [pt(f0, 0.5), pt(f1, H)]
        edge = [pt(e0 - 1.2, -0.2), pt(e0 + 0.8, 0.9)] + _quad(pt(e0 + 1.0, 2.0), pt((e0 + e1) / 2 + 2.2, H * 0.5), pt(e1 + 0.6, H - 1.6), 10) + [pt(e1 - 0.4, H + 0.3)]
        band_out = [fold[0]] + edge + [fold[1]]
        band_in = [_lerp(fold[0], fold[1], 0.06)] + [(q[0] - 1.4, q[1]) for q in edge[1:-1]] + [_lerp(fold[1], fold[0], 0.06)]
        open_uv = _keep(in_uv, lambda q: (f1 - f0) * (q[1] - 0.5) - H * (q[0] - f0) + 0.0)
        if len(open_uv) >= 3:
            parts.append(P(f"{prefix}_open", poly([pt(*q) for q in open_uv]), p["lining_shade"]))
        # the under half is quilted too
        for i, u in enumerate(c for c in chans if c < f0):
            parts.append(band(f"{prefix}_open_chan_{i}", [pt(u, 1.2), pt(u, H - 1.2)], 0.5, "$ink@0.22"))
        parts += [
            # the head and the far side throw their shade into the opening
            band(f"{prefix}_open_shade", [pt(1.6, H - 1.5), pt(1.4, 1.6), pt(f0 + 0.5, 1.4)], 2.0, "$ink@0.28"),
            # the turned-back top throws its shade on the top beside it
            band(f"{prefix}_flap_cast", [(a + 1.0, b + 0.5) for a, b in edge[2:-1]], 1.6, "$ink@0.3"),
            P(f"{prefix}_flap", poly(band_out), p["bind"]),
            P(f"{prefix}_flap_lining", poly(band_in), p["lining"]),
            # a channel seam shows on the lining too
            band(f"{prefix}_flap_seam", [_lerp(fold[0], edge[1], 0.55), _lerp(fold[1], edge[-2], 0.5)], 0.45, f"{p['lining_shade']}@0.8"),
            # the fold: a soft roll, lit along its top, a dark crease where it leaves the opening
            band(f"{prefix}_fold_lit", [(fold[0][0] + 0.9, fold[0][1] + 0.6), (fold[1][0] + 0.8, fold[1][1] - 0.4)], 1.3, "$white@0.28"),
            band(f"{prefix}_fold", fold, 0.5, "$ink@0.6"),
            band(f"{prefix}_flap_rim", edge, 0.6, "$ink"),
        ]
        uA = e1 + 0.8
        # The zip pull, where the opening stops.
        zp = pt(uA + 0.8, H + 0.6)
        parts += [
            P(f"{prefix}_zip", R(1.4, 2.6, 0.5), "$steel.light", at=zp, stroke=INK_FINE),
            P(f"{prefix}_zip_tab", R(0.8, 1.8, 0.4), "$steel.dark", at=(zp[0] + 0.2, zp[1] + 1.8), rot=-10),
        ]
    parts.append(P(f"{prefix}_rim", poly(sil), None, stroke=INK_HAIR))
    return placed(parts, (x, y), s, rot)


# ================================================================ the pillow

def pillow(prefix, x, y, s=1.0, rot=0.0, w=16.0, h=8.0, kind="pillow", dent=True):
    """A small pillow (or, kind="jacket", a jacket folded for one) lying at the head of a bed, seen from above.

    Origin: the centre. At s=1 it spans x -w/2..w/2, y -h/2..h/2 (+0.7 of contact shade lower right). The
    pillow: puffed between its four pinched corners, its seam round the edge stitched in bone, a dent where the
    head goes (`dent`). The jacket: folded, collar turned down at the left with its fleece showing, the zip
    down it, a pocket flap, the hem at the right with a bone drawcord toggle hanging over the edge.
    """
    if kind == "jacket":
        return _jacket(prefix, x, y, s, rot, w, h)
    th = 1.7
    hw, hh = w / 2, (h - th) / 2
    oy = -th / 2
    cs = [(-hw + 0.9, oy - hh), (hw - 0.6, oy - hh + 0.2), (hw, oy + hh), (-hw + 0.3, oy + hh - 0.1)]
    bows = [(0, -0.9), (0.9, 0), (0, 0.9), (-0.9, 0)]
    top = []
    for i in range(4):
        a, b = cs[i], cs[(i + 1) % 4]
        mid = _lerp(a, b, 0.5)
        c = (mid[0] + 2 * bows[i][0], mid[1] + 2 * bows[i][1])
        top += _quad(a, c, b, 10)[:-1]
    sil = _extrude(top, th)
    lo, hi = _proj(top)
    parts = [
        P(f"{prefix}_ao", poly([(a + 0.6, b + 0.7) for a, b in sil]), "$ink@0.35"),
        P(f"{prefix}_side", poly(sil), "$steel.dark"),
        P(f"{prefix}_top", poly(top), "$steel"),
        *_lit_cuts(f"{prefix}_top", top, [(hi - (hi - lo) * 0.28, hi + 1, "$steel.light")]),
        *_lit_cuts(f"{prefix}_top_sh", top, [(lo - 1, lo + (hi - lo) * 0.22, "$steel.dark@0.55")]),
    ]
    # The seam round the edge, where top meets bottom: stitched, bone.
    front = _quad(cs[3], (0, oy + hh + 1.8), cs[2], 12)
    parts += _stitches(f"{prefix}_stitch", front, 7, 0.9, "$bone@0.75", 0.4)
    # The corners pinched into ears, with the creases they pull in.
    for i, (cx, cy) in enumerate(cs):
        inx, iny = (-cx * 0.22, (oy - cy) * 0.5)
        parts.append(_taper(f"{prefix}_ear_{i}", [(cx, cy), (cx + inx, cy + iny)], 0.9, 0.1, "$slate.light@0.55"))
    if dent:
        parts += [
            P(f"{prefix}_dent_lit", ell(w * 0.22, hh * 0.42), "$steel.light", at=(1.1, oy + 0.7)),
            P(f"{prefix}_dent", ell(w * 0.22, hh * 0.42), "$steel.dark@0.8", at=(0.3, oy + 0.2)),
        ]
    parts.append(P(f"{prefix}_rim", poly(sil), None, stroke=INK_HAIR))
    return placed(parts, (x, y), s, rot)


def _jacket(prefix, x, y, s, rot, w, h):
    th = 1.8
    hw, hh = w / 2, (h - th) / 2
    oy = -th / 2
    top = rr(w, h - th, 1.6, (0, oy), 3)
    top = [(a + 0.25 * math.sin(b * 1.7), b) for a, b in top]     # soft, not boxed
    sil = _extrude(top, th)
    lo, hi = _proj(top)
    nk = (-hw + 2.9, oy - 0.2)      # the neck
    parts = [
        P(f"{prefix}_ao", poly([(a + 0.6, b + 0.7) for a, b in sil]), "$ink@0.35"),
        P(f"{prefix}_side", poly(sil), "$slate.dark"),
        # the layers it is folded in, showing along the near edge
        band(f"{prefix}_layers", [(-hw + 1.2, oy + hh + th * 0.5), (hw - 1.2, oy + hh + th * 0.5)], 0.4, "$ink@0.5"),
        P(f"{prefix}_top", poly(top), "$slate"),
        *_lit_cuts(f"{prefix}_top", top, [(hi - (hi - lo) * 0.3, hi + 1, "$slate.light")]),
        # the hem at the far end, with its drawcord
        P(f"{prefix}_hem", poly(clip(top, 0, hw - 2.2, hw + 1)), "$slate.dark"),
        band(f"{prefix}_hem_seam", [(hw - 2.2, oy - hh + 0.6), (hw - 2.2, oy + hh - 0.4)], 0.4, "$slate.light@0.6"),
        # a pocket flap on the near panel
        P(f"{prefix}_pocket", R(3.6, 1.3, 0.4), "$slate.dark", at=(1.6, oy + hh * 0.5), rot=-3),
        P(f"{prefix}_pocket_lit", R(3.0, 0.4, 0.2), "$slate.light@0.8", at=(1.5, oy + hh * 0.5 - 0.75), rot=-3),
        # the zip, from the neck down the middle
        band(f"{prefix}_zip", [(nk[0] + 1.5, nk[1] + 0.05), (hw - 2.3, nk[1] + 0.25)], 0.55, "$slate.dark2"),
        # the collar turned down round the neck, open toward the zip, its fleece showing inside
        P(f"{prefix}_fleece", poly(_arc(nk[0] + 0.3, nk[1], 1.7, hh * 0.7, 40, 320, 14)), "$steel.light"),
        P(f"{prefix}_fleece_sh", poly(_arc(nk[0] + 0.1, nk[1] - 0.2, 1.3, hh * 0.52, 110, 250, 8)), "$steel.dark"),
        P(f"{prefix}_collar", poly(_arc(nk[0], nk[1], 2.6, hh * 0.98, 48, 312, 16) + _arc(nk[0] + 0.35, nk[1], 1.6, hh * 0.62, 318, 42, 14)), "$slate.dark", stroke=INK_FINE),
        P(f"{prefix}_collar_lit", poly(_arc(nk[0], nk[1], 2.6, hh * 0.98, 200, 290, 8) + _arc(nk[0] + 0.1, nk[1] - 0.1, 2.0, hh * 0.78, 290, 200, 8)), "$slate@0.9"),
        P(f"{prefix}_zip_pull", R(1.5, 0.9, 0.3), "$steel.light", at=(nk[0] + 2.4, nk[1] + 0.1), stroke=INK_FINE),
        P(f"{prefix}_rim", poly(sil), None, stroke=INK_HAIR),
        # the drawcord's toggle and its loop, over the near edge
        *_cord(f"{prefix}_cord", _quad((hw - 1.4, oy + hh - 0.2), (hw - 0.6, oy + hh + 2.4), (hw - 2.6, oy + hh + 1.6), 8), 0.55, lit=None),
        P(f"{prefix}_toggle", R(1.0, 1.5, 0.45), CORD, at=(hw - 1.4, oy + hh + 0.3), stroke=INK_FINE),
    ]
    return placed(parts, (x, y), s, rot)


# ================================================================ the sack

def sack(prefix, x, y, s=1.0, rot=0.0, cloth="canvas", fill=1.0):
    """A slumped sack of stores: neck cinched with a bone cord tied off, two tails, folds running down from the
    neck, a side seam, a stitched patch, its weight settled on the ground.

    Origin: on the ground under the middle of it. At s=1 (fill=1) it spans x -8..8.7, y -15..0.6.
    `cloth`: palette name — "canvas" (the expedition's, the default) or "husk" (cloth that is not theirs).
    `fill`: how full, 0.5..1; emptier slumps lower and wider.
    Parts: `<prefix>_tail_a`/`_tail_b` (+ `_edge`, `_lit`), placed at the knot so a `rot` track swings them about it.
    """
    p = _pal(cloth)
    f = max(0.4, min(1.0, fill))
    hy = 11.5 * (0.55 + 0.45 * f)      # height of the neck
    wb = 7.6 + (1 - f) * 2.4          # half-width of the belly
    nx = 1.4 + (1 - f) * 0.8          # the neck leans right as it slumps
    ctrl = [
        (-wb + 1.2, 0.0), (-wb - 0.2, -hy * 0.2), (-wb + 0.2, -hy * 0.5), (-wb * 0.62, -hy * 0.8),
        (nx - 1.5, -hy + 0.2), (nx - 1.2, -hy - 0.4),
        (nx - 2.1, -hy - 1.7), (nx - 1.7, -hy - 3.0), (nx - 0.8, -hy - 2.5), (nx - 0.1, -hy - 3.5), (nx + 0.8, -hy - 2.7),
        (nx + 1.7, -hy - 3.3), (nx + 2.4, -hy - 2.2), (nx + 2.3, -hy - 1.1),
        (nx + 1.5, -hy - 0.4), (nx + 1.9, -hy + 0.3),
        (wb * 0.75, -hy * 0.72), (wb + 0.9, -hy * 0.36), (wb + 0.8, -hy * 0.08), (wb - 0.6, 0.0),
    ]
    body = _spline(ctrl, 4)
    body = [(a, min(b, 0.0)) for a, b in body]
    lo, hi = _proj(body)
    neck = (nx + 0.2, -hy - 0.1)
    parts = [
        shadow(f"{prefix}_shadow", 1.0, 0.5, wb + 2.5, 2.2, "0.42"),
        ao(f"{prefix}_ao", 0.2, -0.2, wb * 1.7, 1.6, 0.5),
        P(f"{prefix}_body", poly(body), p["base"]),
        *_lit_cuts(f"{prefix}_body", body, [
            (hi - (hi - lo) * 0.3, hi + 1, p["lit"]),
            (lo - 1, lo + (hi - lo) * 0.3, p["shade"]),
        ]),
        # its weight on the ground: the belly spread and dark where it sits
        P(f"{prefix}_base", poly(clip(body, 1, -1.6, 0.5)), f"{p['deep']}@0.7"),
    ]
    # Folds running down from the cinched neck, each a dark crease with its lit ridge on the left.
    folds = [((-0.9, 0.5), (-wb * 0.62, -hy * 0.36), 1.1), ((-0.2, 0.9), (-wb * 0.2, -hy * 0.22), 0.9),
             ((0.9, 0.9), (wb * 0.32, -hy * 0.3), 1.0), ((1.6, 0.4), (wb * 0.72, -hy * 0.52), 1.0)]
    for i, ((ax, ay), (bx, by), w) in enumerate(folds):
        a = (neck[0] + ax, neck[1] + ay)
        mid = _lerp(a, (bx, by), 0.5)
        crv = _quad(a, (mid[0] - 0.5 * (1 if bx < 0 else -1), mid[1] - 0.6), (bx, by), 8)
        parts += [
            _taper(f"{prefix}_fold_{i}_lit", [(q[0] - 0.75, q[1] + 0.1) for q in crv], w * 0.8, 0.1, f"{p['lit']}@0.8"),
            _taper(f"{prefix}_fold_{i}", crv, w, 0.1, f"{p['deep']}@0.75"),
        ]
    # The side seam, down its left front, stitched.
    seam = _quad((neck[0] - 1.6, neck[1] + 1.2), (-wb * 0.62, -hy * 0.55), (-wb * 0.58, -0.6), 10)
    parts.append(band(f"{prefix}_seam", seam, 0.5, f"{p['deep']}@0.8"))
    parts += _stitches(f"{prefix}_seam_st", [(a + 0.55, b) for a, b in seam], 5, 0.9, STITCH, 0.4)
    # A patch stitched over a tear, low on the lit side.
    pc, pw, ph, pr = (-wb * 0.3, -hy * 0.27), 4.0, 3.3, -9
    corners = [(-pw / 2, -ph / 2), (pw / 2, -ph / 2), (pw / 2, ph / 2), (-pw / 2, ph / 2)]
    ca, sa = math.cos(math.radians(pr)), math.sin(math.radians(pr))
    pc_pts = [(pc[0] + u * ca - v * sa, pc[1] + u * sa + v * ca) for u, v in corners]
    parts.append(P(f"{prefix}_patch", R(pw, ph, 0.4), p["shade"], at=pc, rot=pr, stroke=INK_FINE))
    parts.append(P(f"{prefix}_patch_lit", R(pw - 1.0, 0.6, 0.3), f"{p['base']}@0.8", at=(pc[0] - 0.1, pc[1] - ph / 2 + 0.75), rot=pr))
    for j in range(4):
        a, b = pc_pts[j], pc_pts[(j + 1) % 4]
        inset = [_lerp(a, b, 0.12), _lerp(a, b, 0.88)]
        c = _lerp(_lerp(pc_pts[0], pc_pts[2], 0.5), _lerp(a, b, 0.5), 0.72)
        off = (c[0] - _lerp(a, b, 0.5)[0], c[1] - _lerp(a, b, 0.5)[1])
        inset = [(q[0] + off[0], q[1] + off[1]) for q in inset]
        parts += _stitches(f"{prefix}_patch_st{j}", inset, 3 if j % 2 == 0 else 2, 0.7, "$bone@0.85", 0.4)
    parts.append(P(f"{prefix}_rim", poly(body), None, stroke=INK_HAIR))
    # The cord round the neck, knotted on the front, its two tails hanging.
    k = (neck[0] + 0.5, neck[1] + 0.2)
    parts += _cord(f"{prefix}_tie", [(neck[0] - 1.9, neck[1] - 0.4), (neck[0], neck[1] + 0.4), (neck[0] + 2.0, neck[1] - 0.2)], 1.1)
    parts += _cord(f"{prefix}_tail_a", _quad(k, (k[0] - 1.5, k[1] + 1.6), (k[0] - 1.1, k[1] + 3.9), 8), 0.75, pivot=k)
    parts += _cord(f"{prefix}_tail_b", _quad(k, (k[0] + 1.2, k[1] + 1.1), (k[0] + 2.3, k[1] + 2.7), 8), 0.75, pivot=k)
    parts += [
        P(f"{prefix}_knot", circ(0.95), CORD, at=k, stroke=INK_FINE),
        P(f"{prefix}_knot_lit", circ(0.35), CORD_LIT, at=(k[0] - 0.3, k[1] - 0.35)),
    ]
    return placed(parts, (x, y), s, rot)


# ================================================================ the coil of cord

def rope_coil(prefix, x, y, s=1.0, rot=0.0, loops=3, tail=1, cord=CORD):
    """A coil of bone cord lying on the ground, seen from above: `loops` (2..4) loops piled a little off true,
    each lit along its top, and the free end run out to one side (`tail` +1 right, -1 left, 0 none).

    Origin: the middle of the coil on the ground. At s=1 (loops=3, tail=1) it spans x -8.2..16.4, y -5.8..4.3
    (the coil alone is 16 x 10; the free end adds 8 to the side it runs to).
    Parts: `<prefix>_end` (+ `_edge`, `_lit`) the free end.
    """
    loops = max(2, min(4, loops))
    w = 1.25
    parts = [shadow(f"{prefix}_shadow", 0.6, 0.6, 8.6, 3.8, "0.4")]
    last = None
    for i in range(loops):
        cx, cy = 0.45 * i - 0.35 * (i % 2), -0.95 * i
        rx, ry = 7.2 - 0.55 * i, 3.3 - 0.22 * i
        ring_pts = _arc(cx, cy, rx, ry, -10, 352, 40)
        parts += [band(f"{prefix}_loop_{i}_edge", ring_pts, w + 0.75, "$ink@0.85"), band(f"{prefix}_loop_{i}", ring_pts, w, cord)]
        # the light along the top of the cord, strongest on the left
        parts.append(band(f"{prefix}_loop_{i}_lit", _arc(cx - 0.15, cy - 0.3, rx, ry, 120, 300, 14), w * 0.36, CORD_LIT))
        parts.append(band(f"{prefix}_loop_{i}_shade", _arc(cx + 0.15, cy + 0.32, rx, ry, -40, 70, 10), w * 0.35, "$ink@0.3"))
        last = (cx, cy, rx, ry)
    if tail:
        cx, cy, rx, ry = last
        sgn = 1 if tail > 0 else -1
        a0 = 25 if sgn > 0 else 155
        p0 = _on_ell(cx, cy, rx, ry, a0)
        pts = _spline([p0, (p0[0] + sgn * 3.0, p0[1] + 1.8), (p0[0] + sgn * 6.5, p0[1] + 1.6), (p0[0] + sgn * 9.5, p0[1] + 2.6)], 4, closed=False)
        parts += _cord(f"{prefix}_end", pts, w, cord)
        # the end whipped with a twist of thread so it does not fray
        e = pts[-1]
        ang = math.degrees(math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0]))
        parts.append(P(f"{prefix}_whip", R(1.6, w + 0.5, 0.4), "$steel.dark", at=(e[0] - sgn * 0.6, e[1] - 0.2), rot=ang, stroke=INK_FINE))
    return placed(parts, (x, y), s, rot)


# ================================================================ the door flap

def flap(prefix, x, y, s=1.0, rot=0.0, w=11.0, h=38.0, tie=0.47, side="left", cloth="slate"):
    """A canvas door flap tied back to the jamb: hung from the lintel, gathered at the tie into folds that
    fan out above and below it, its free edge turning to show its inside, the bone cord knotted round it.

    Origin: the top of the jamb it is tied back to (the doorway's top-left corner for side="left"; for
    "right" it is mirrored and hangs to the left of the origin). At s=1 it spans x -1.3..w+0.4 (the cleat
    on the jamb is the -1.3), y -0.5..h+1.4. `tie` is how far down the tie is (0..1).
    Parts: `<prefix>_tail_a`/`_tail_b` (+ `_edge`, `_lit`), the tie's ends, placed at the knot so a `rot`
    track swings them about it.
    """
    p = _pal(cloth)
    lx = 0.85 if side == "right" else -0.85   # lit ridges stay on the left whichever way it is tied
    ty = h * tie
    tx = w * 0.32                      # the tie's outer side
    bw = w * 0.52                      # how far the hem reaches out on the ground
    # The flap: down the jamb, along the hem (three soft scallops where the folds come down), up its free
    # edge to the tie, and out and up to the lintel.
    hem = []
    for k in range(13):
        t = k / 12
        hem.append((bw * t, h - 0.6 * abs(math.sin(math.pi * t * 3)) + 0.6))
    free_lo = _quad((bw, h + 0.4), (tx + 1.6, h * 0.72 + ty * 0.28), (tx, ty + 0.6), 10)
    free_hi = _quad((tx, ty - 0.6), (w * 0.62, ty * 0.45), (w, 0), 12)
    outline = [(0, 0)] + [(0, h + 0.6)] + hem[1:] + free_lo[1:] + free_hi + [(w, 0)]
    # The inside of the flap, turned out along its free edge above the tie.
    turn = free_hi + [(q[0] - 1.4 * (1 - abs(2 * i / (len(free_hi) - 1) - 1) ** 2) - 0.5, q[1] + 0.3) for i, q in reversed(list(enumerate(free_hi)))]
    parts = [
        ao(f"{prefix}_ao", bw / 2, h + 0.6, bw + 1.5, 1.6, 0.45),
        P(f"{prefix}_cloth", poly(outline), p["base"]),
        P(f"{prefix}_inside", poly(turn), p["shade"]),
    ]
    # Folds gathered at the tie: above it they run in from the lintel, below it they fan out to the hem.
    # Each is a trough of shade with its ridge lit on the left.
    tops = [w * 0.22, w * 0.48, w * 0.74]
    for i, u in enumerate(tops):
        a, b = (u, 1.6), (tx * (0.2 + 0.3 * i), ty - 0.8)
        crv = _quad(a, ((a[0] + b[0]) / 2 + 0.6, (a[1] + b[1]) / 2), b, 8)
        parts += [
            _taper(f"{prefix}_ufold_{i}_lit", [(q[0] + lx, q[1]) for q in crv], 0.5, 0.9, f"{p['lit']}@0.85"),
            _taper(f"{prefix}_ufold_{i}", crv, 0.4, 1.1, f"{p['deep']}@0.6"),
        ]
    for i, u in enumerate([0.3, 0.58, 0.86]):
        a, b = (tx * (0.35 + 0.25 * i) - max(0.0, lx) * 0.5, ty + 1.0), (bw * u - max(0.0, lx) * 1.3, h - 0.2)
        crv = _quad(a, ((a[0] + b[0]) / 2 - 0.3, (a[1] + b[1]) / 2), b, 10)
        parts += [
            _taper(f"{prefix}_lfold_{i}_lit", [(q[0] + lx * 1.05, q[1]) for q in crv], 0.6, 1.2, f"{p['lit']}@0.85"),
            _taper(f"{prefix}_lfold_{i}", crv, 0.5, 1.4, f"{p['deep']}@0.55"),
        ]
    # Shade down the jamb side, a hem along the bottom, the batten it hangs from.
    parts += [
        P(f"{prefix}_jamb_shade", poly([(0, 1.2), (1.2, 1.2), (1.1, h), (0, h)]), f"{p['deep']}@0.45"),
        band(f"{prefix}_hem", hem[:-1], 1.0, f"{p['shade']}@0.9"),
        *_stitches(f"{prefix}_hem_st", [(q[0], q[1] - 1.1) for q in hem[1:-1]], 4, 0.8, STITCH, 0.35),
        P(f"{prefix}_rim", poly(outline), None, stroke=INK_HAIR),
        P(f"{prefix}_batten", R(w + 1.2, 1.6, 0.6), "$steel.dark", at=(w / 2 - 0.2, 0.3), stroke=INK_FINE),
        P(f"{prefix}_batten_lit", R(w - 0.6, 0.45, 0.2), "$steel@0.9", at=(w / 2 - 0.4, -0.05)),
    ]
    # The tie: round the gathered flap and back to a cleat on the jamb, knotted at the front, two tails.
    kx, ky = tx * 0.6, ty + 0.3
    parts += [P(f"{prefix}_cleat", R(1.4, 3.0, 0.5), "$steel", at=(-0.6, ty), stroke=INK_FINE)]
    parts += _cord(f"{prefix}_tie", [(-0.8, ty - 0.6), (tx * 0.4, ty + 0.35), (tx + 0.5, ty - 0.1)], 1.15)
    parts += _cord(f"{prefix}_tail_a", _quad((kx, ky), (kx - 0.6, ky + 2.2), (kx - 0.2, ky + 4.6), 8), 0.8, pivot=(kx, ky))
    parts += _cord(f"{prefix}_tail_b", _quad((kx, ky), (kx + 1.2, ky + 1.6), (kx + 1.9, ky + 3.4), 8), 0.8, pivot=(kx, ky))
    parts += [
        P(f"{prefix}_knot", circ(0.95), CORD, at=(kx, ky), stroke=INK_FINE),
        P(f"{prefix}_knot_lit", circ(0.35), CORD_LIT, at=(kx + lx * 0.35, ky - 0.35)),
    ]
    if side == "right":
        parts = _mirror(parts)
    return placed(parts, (x, y), s, rot)


def _slab(pts, x0, x1):
    """The part of a polygon between x = x0 and x = x1 (Sutherland–Hodgman against the two sides)."""
    def cut(pts, keep, at):
        out = []
        for i, q in enumerate(pts):
            p = pts[i - 1]
            if keep(q):
                if not keep(p):
                    out.append(_lerp(p, q, (at - p[0]) / (q[0] - p[0])))
                out.append(q)
            elif keep(p):
                out.append(_lerp(p, q, (at - p[0]) / (q[0] - p[0])))
        return out

    return cut(cut(pts, lambda q: q[0] >= x0, x0), lambda q: q[0] <= x1, x1)


# Where a streamer is cut along its length, as fractions: the last length is the longest, so the cut
# before it falls short of a frayed tip's notch and no length carries a sliver of the notch's gap.
STREAMER_CUTS = (0.0, 0.26, 0.5, 0.72, 1.0)


def streamer(prefix, x, y, outline, fill, side=1, fold=None, fold_fill="$ink@0.28", over=0.6, cuts=STREAMER_CUTS):
    """A strip of cloth knotted on at (x, y) and blowing out from it, cut into four lengths so a clip can
    run a wave down it (`streamer_tracks`) instead of swinging it whole like a board.

    `outline` is the strip drawn streaming out along +x from its knot at (0, 0), x the distance along it
    and y across it; the tip, frayed or not, is its far end. `side=-1` blows it out to the left instead.
    `fold` is a crease of shade along it, in the same frame.

    Each length is drawn twice: once with the ink line round it, and again over all of those without, a
    little longer at both ends than the cut, so where two lengths meet the line between them is painted
    out and the strip reads as one piece of cloth at any bend the clip puts in it. Give the crease a
    solid colour (the cloth's own `.dark`) and it overlaps the same way; a wash (`@` an opacity) is cut
    at the joins exactly instead, since an overlap would darken into a band — but two washes that only
    meet leave a hairline of light between them, which is why the solid colour is the better choice.
    `cuts` are where it is cut, as fractions of its length (`STREAMER_CUTS`); keep the last cut, plus
    `over`, short of any notch in the tip. Pass the same `cuts` to `streamer_tracks`.
    Parts: `<prefix>_<k>_ink`, `<prefix>_<k>`, `<prefix>_<k>_fold` for k = 0..3, root to tip, each with
    its origin at the root of its length.
    """
    n = max(q[0] for q in outline)
    xs = [n * c for c in cuts]
    solid = "@" not in fold_fill
    ink, cloth, crease = [], [], []
    for k in range(len(xs) - 1):
        x0, x1 = xs[k], xs[k + 1]
        lo, hi = (x0 - over if k else x0), (x1 + over if k < len(xs) - 2 else x1)
        seg = [(side * (q[0] - x0), q[1]) for q in _slab(outline, lo, hi)]
        at = (x + side * x0, y)
        ink.append(P(f"{prefix}_{k}_ink", poly(seg), fill, at=at, stroke=INK_HAIR))
        cloth.append(P(f"{prefix}_{k}", poly(seg), fill, at=at))
        if fold:
            f = _slab(fold, *((lo, hi) if solid else (x0, x1)))
            if len(f) >= 3:
                crease.append(P(f"{prefix}_{k}_fold", poly([(side * (q[0] - x0), q[1]) for q in f]), fold_fill, at=at))
    return ink + cloth + crease


def streamer_tracks(prefix, outline, side=1, flaps=2, flicker=3, swing=14.0, flick=6.0, gust=5.0, sag=4.0,
                    twist=0.18, lag=0.0, wave=0.9, keys=25, fold=True, cuts=STREAMER_CUTS, root=0.25, bunch=0.0,
                    shade=0.0, shade_to=None, upright=False, tip_turn=0.6):
    """The wind in a `streamer`: a wave that leaves the knot and runs out to the tip, so the root barely
    moves and the frayed end whips, with the whole strip lifting and sagging a little once a loop.

    Each length's angle is laid end to end from the knot (each length starts where the one before it
    ends), so the strip stays joined however far it bends; the tracks are that chain sampled `keys` times
    through the loop and read back linearly. `flaps` and `flicker` are how many times the main wave and a
    quicker one on top of it run through a loop (whole numbers, so it loops); `swing` and `flick` their
    reach in degrees at the tip, `gust` the slow lift, `sag` how far the strip droops on average, `wave`
    how much of a wavelength fits along the strip. `twist` narrows the outer lengths as the wave passes
    through them, the cloth turning edge-on. `lag` (0..1 of a flap) is how far behind the wind this strip
    is, so a row of them does not flap in step.

    For a flag hoisted along its whole edge rather than knotted at a point, `root=0` keeps the hoist
    from turning off the pole (the main wave's reach grows from nothing there instead of from a quarter),
    `bunch` shortens each length as a crest passes through it (the cloth gathering, taken into the chain
    so the lengths stay joined), and `shade` tints each length toward `shade_to` as it turns down and
    away from the light — the dark folds running out along it are what reads as a flag at a few pixels.

    `upright` is for a flag that is taller than it is long. Turning a tall length to follow the wave
    swings its top and bottom edges the opposite ways, and between two lengths at a bend that opens a
    crack wider than the overlap can cover, and the cloth reads as boards hinged together. A flag seen
    side on does not do that: its cross-sections stay upright and ride up and down the wave, closing up
    in x as the cloth slopes. So with `upright` the lengths only travel along the chain and never turn,
    except the last (the tails, past the notch), which turns `tip_turn` of the way. Cut it in thin
    slabs for this (a pixel or less), so the steps between them are too small to see.
    """
    n = max(q[0] for q in outline)
    xs = [n * c for c in cuts]
    segs = len(xs) - 1
    tau = 2 * math.pi
    samples = []
    for j in range(keys):
        t = j / (keys - 1)
        px, py, pose = 0.0, 0.0, []
        for k in range(segs):
            u = (xs[k] + xs[k + 1]) / 2 / n
            ph = tau * (flaps * t - u * wave - lag)
            wav = math.sin(ph)
            a = (sag * u
                 + swing * (root + (1 - root) * u) * wav
                 + flick * u * math.sin(tau * (flicker * t - u * wave * 1.6 - lag * 1.3))
                 + gust * u * math.sin(tau * (t - lag * 0.5)))
            sy = 1 - twist * u * (0.5 + 0.5 * math.cos(ph))
            sx = 1 - bunch * (0.5 + 0.5 * math.cos(ph))
            dark = shade * (0.4 + 0.6 * u) * max(0.0, wav)
            pose.append((px - xs[k], py, a, sy, sx, dark))
            L = (xs[k + 1] - xs[k]) * sx
            px += L * math.cos(math.radians(a))
            py += L * math.sin(math.radians(a))
        samples.append((t, pose))
    tracks = []
    for k in range(segs):
        ids = [f"{prefix}_{k}_ink", f"{prefix}_{k}"] + ([f"{prefix}_{k}_fold"] if fold else [])
        last = k == segs - 1
        props = [("x", lambda p: side * p[0]), ("y", lambda p: p[1])]
        if not upright:
            props.append(("rot", lambda p: side * p[2]))
        elif last and tip_turn:
            props.append(("rot", lambda p: side * p[2] * tip_turn))
        # a squash pair, not a squash and a `scale`: the renderer takes one or the other
        props += ([("scaleY", lambda p: p[3])] if twist else []) + ([("scaleX", lambda p: p[4])] if bunch else [])
        for prop, val in props:
            if k == 0 and prop in ("x", "y"):
                continue  # the root length is knotted on: it turns, it does not travel
            ks = [[r2(t), r2(val(pose[k]))] for t, pose in samples]
            for pid in ids:
                tracks.append({"part": pid, "prop": prop, "keys": ks, "ease": "linear"})
        if shade and shade_to:
            ks = [[r2(t), r2(pose[k][5])] for t, pose in samples]
            tracks.append({"part": f"{prefix}_{k}", "prop": "tint", "keys": ks, "ease": "linear", "to": shade_to})
    return tracks
