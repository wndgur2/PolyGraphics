"""The camp's everyday things: a mug, a tin, a page, a tag, a dial, a stool, a ladle, the saw, a stone.

    from bits_camp import mug, tin, tin_stack, page, page_stack, tag, dial, stool, ladle, saw, stone

Each helper draws its thing at its natural size in the camp about its own
origin (said in its docstring: its foot where it stands on something, its
centre where it lies flat or turns, its tie or hook where it hangs) and sets it
down with `placed()`. Every id is built from `prefix`. Cold is the
expedition's (steel, slate, frost), paper is bone, jelly is gold; writing is
ruled strokes, never letters. Light from the upper left: a lit edge on the
left or top of each mass, its shade lower right, a dark contact where it rests.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw import *  # noqa: E402,F401,F403

_LV = {"dark2": -2, "dark": -1, "": 0, "light": 1, "light2": 2}
_NM = {v: k for k, v in _LV.items()}


def tone(fill, d):
    """`fill` stepped `d` along its ramp, alpha kept: tone("$steel", 1) is "$steel.light", tone("$frost.dark@0.5", 1) is "$frost@0.5"."""
    col, _, a = fill.partition("@")
    name, _, lv = col.partition(".")
    n = max(-2, min(2, _LV[lv] + d))
    return name + ("." + _NM[n] if n else "") + ("@" + a if a else "")


def alpha(fill, a):
    return fill.partition("@")[0] + f"@{a}"


def arc_pts(cx, cy, rx, ry, a0, a1, n=12):
    """Points along an ellipse from a0 to a1 degrees (0 is +x, 90 is down, as the renderer turns)."""
    out = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def oval(cx, cy, rx, ry=None, n=16):
    """A closed ellipse as points, so it can share an origin with other parts (a swinging tag)."""
    return arc_pts(cx, cy, rx, ry if ry is not None else rx, 0, 360 - 360 / n, n - 1)


def turned(pts, a, about=(0, 0)):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    ox, oy = about
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in pts]


def cyl_pts(rx, ry, top, bot, n=12):
    """The silhouette of an upright cylinder: the back of its top ellipse (centre y `top`) and the front of its bottom one (`bot`)."""
    return arc_pts(0, bot, rx, ry, 0, 180, n) + arc_pts(0, top, rx, ry, 180, 360, n)


def front_arc(cy, rx, ry, a0=172, a1=8, n=14):
    """The near half of an ellipse, left to right: where a bead, a label edge or a ruled stroke runs round a cylinder."""
    return arc_pts(0, cy, rx, ry, a0, a1, n)


def crescent(cx, cy, rx, ry, a0, a1, t, n=8):
    """A sliver along an ellipse from a0 to a1 degrees, `t` thick at its middle and nothing at its ends."""
    outer = arc_pts(cx, cy, rx, ry, a0, a1, n)
    inner = []
    for k in range(n, -1, -1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        f = math.sin(math.pi * k / n) * t
        inner.append((cx + (rx - f) * math.cos(a), cy + (ry - f * ry / rx) * math.sin(a)))
    return outer + inner


def dent(id, x, y, fill, r=0.9):
    """A dent pressed into a lit metal surface: its upper-left wall turned from the light, its lower-right wall catching it."""
    return [
        P(id, poly(crescent(x, y, r, r * 0.8, 150, 300, r * 0.42)), alpha(tone(fill, -1), 0.85)),
        P(f"{id}_lit", poly(crescent(x, y, r, r * 0.8, -20, 120, r * 0.32)), "$white@0.4"),
    ]


def _shape_pts(shape):
    k = shape["kind"]
    if k == "poly":
        return [tuple(q) for q in shape["points"]]
    if k == "ellipse":
        return oval(0, 0, shape["rx"], shape["ry"], 14)
    if k == "circle":
        return oval(0, 0, shape["r"], shape["r"], 12)
    if k == "rect":
        return rr(shape["w"], shape["h"], shape["corner"], (0, 0), 3)
    raise ValueError(f"cannot pivot a {k}")


def pivoted(parts, pivot=(0, 0)):
    """The same drawing with every part's `at` moved to `pivot` and its shape carried round to match (as a polygon), so one `rot`
    track given to every part turns the whole thing about that point without it coming apart. Rings cannot be carried."""
    out = []
    for p in parts:
        q = dict(p)
        at = p.get("at", (0, 0))
        sc = p.get("scale", 1)
        sx, sy = (sc, sc) if not isinstance(sc, (list, tuple)) else sc
        pts = [(x * sx, y * sy) for x, y in _shape_pts(p["shape"])]
        pts = moved(turned(pts, p.get("rot", 0)), (at[0] - pivot[0], at[1] - pivot[1]))
        q["shape"] = poly(pts)
        q["at"] = [r2(pivot[0]), r2(pivot[1])]
        q.pop("rot", None)
        q.pop("scale", None)
        out.append(q)
    return out


def squashed(parts, k):
    """The same drawing foreshortened to `k` of its height about y=0 (as polygons): a page or a stack lying on the ground, seen
    at the camp's slant (k ~0.5-0.7). Use on parts already `placed` at the origin, then `placed` again to set them down."""
    out = []
    for p in parts:
        q = dict(p)
        at = p.get("at", (0, 0))
        sc = p.get("scale", 1)
        sx, sy = (sc, sc) if not isinstance(sc, (list, tuple)) else sc
        pts = moved(turned([(x * sx, y * sy) for x, y in _shape_pts(p["shape"])], p.get("rot", 0)), at)
        q["shape"] = poly([(x - at[0], y * k - at[1] * k) for x, y in pts])
        q["at"] = [r2(at[0]), r2(at[1] * k)]
        q.pop("rot", None)
        q.pop("scale", None)
        out.append(q)
    return out


def inked(p, stroke=INK_FINE):
    q = dict(p)
    q["stroke"] = stroke
    return q


def _lcg(seed):
    s = seed
    while True:
        s = (s * 1103515245 + 12345) % 2147483648
        yield s / 2147483648


# ================================================================ mug
def mug(prefix, x, y, s=1.0, rot=0.0, handle="right", fill="$steel", rim=None, mark="dent", tipped=False, facing="left", ground=True):
    """A steel camp mug, 6 across and 7 tall (8.3 with the handle). Origin: the middle of its foot, where it stands.

    handle: "right" | "left" (standing). fill: "$steel" bare, or an enamel ("$frost.dark", "$slate.light").
    rim: the rolled rim's colour (default a step lighter than steel). mark: "dent" | "chip" | None.
    tipped: lying on its side, its mouth to `facing` ("left" | "right"), handle up; 9.6 long, 7.9 high with the handle.
    ground: its contact shadow (False for a mug hung on a hook by its handle; the top of the handle is at (±2.8, -5.6)).
    """
    p = prefix
    rim = rim or ("$steel.light" if fill.startswith("$steel") else "$steel")
    if tipped:
        return placed(_mug_tipped(p, fill, rim, mark, facing), (x, y), s, rot)
    parts = _mug_standing(p, fill, rim, mark, handle)
    if not ground:
        parts = [q for q in parts if q["id"] != f"{p}_shadow"]
    return placed(parts, (x, y), s, rot)


def _mug_standing(p, fill, rim, mark, handle):
    lt, dk = tone(fill, 1), tone(fill, -1)
    rx, ry = 3.0, 1.05
    top, bot = -7 + ry, -ry
    k = 1 if handle == "right" else -1
    hx = k * 2.8
    a0, a1 = (-90, 90) if k > 0 else (90, 270)
    parts = [
        shadow(f"{p}_shadow", 0.9, -0.35, 3.9, 1.15, "0.38"),
        # The handle: a strap bent into a ring, its ends hidden under the body.
        P(f"{p}_handle_ink", ring_arc(1.8, 1.65, a0, a1), "$ink", at=(hx, -3.75)),
        P(f"{p}_handle", ring_arc(1.8, 0.95, a0, a1), fill, at=(hx, -3.75)),
        *shaded(f"{p}_body", cyl_pts(rx, ry, top, bot), fill, [(-2.5, -1.45, lt), (1.25, 3.2, dk)], stroke=INK_FINE, axis=0),
        P(f"{p}_lit", R(0.55, 3.9, 0.27), "$white@0.5", at=(-2.0, -3.15)),
        # The foot's rolled edge catching a little light along the front.
        band(f"{p}_foot", front_arc(bot - 0.45, rx - 0.25, ry, 150, 60, 8), 0.3, "$white@0.22"),
    ]
    if mark == "dent":
        parts += dent(f"{p}_dent", 0.7, -2.6, fill)
    # The rolled rim, and the dark inside.
    parts += [
        P(f"{p}_rim", ell(rx, ry), rim, at=(0, top), stroke=INK_FINE),
        P(f"{p}_inside", ell(rx - 0.55, ry - 0.33), "$coal", at=(0, top + 0.07)),
        P(f"{p}_rim_lit", ell(0.95, 0.2), "$white@0.6", at=(-1.55, top - 0.8), rot=-16),
    ]
    if mark == "chip":
        # A chip off the enamel at the lip, the dark steel under it showing.
        parts += [
            P(f"{p}_chip", poly([(-0.7, -0.15), (0.45, -0.3), (0.8, 0.35), (0.1, 0.95), (-0.55, 0.55)]), "$coal", at=(-1.25, top + ry + 0.25)),
            P(f"{p}_chip_b", circ(0.28), "$coal", at=(1.1, -1.7)),
        ]
    return parts


def _mug_tipped(p, fill, rim, mark, facing):
    lt, dk = tone(fill, 1), tone(fill, -1)
    k = -1 if facing == "left" else 1
    R_, ex, cy = 2.95, 1.55, -2.95
    xm, xb = k * 3.2, -k * 3.3
    if k < 0:
        pts = arc_pts(xm, cy, ex, R_, 90, 270) + arc_pts(xb, cy, ex, R_, 270, 450)
    else:
        pts = arc_pts(xb, cy, ex, R_, 90, 270) + arc_pts(xm, cy, ex, R_, 270, 450)
    parts = [
        shadow(f"{p}_shadow", 0.6, -0.25, 5.4, 1.1, "0.38"),
        P(f"{p}_handle_ink", ring_arc(1.7, 1.65, 180, 360), "$ink", at=(-k * 0.4, cy - R_ + 0.5)),
        P(f"{p}_handle", ring_arc(1.7, 0.95, 180, 360), fill, at=(-k * 0.4, cy - R_ + 0.5)),
        *shaded(f"{p}_body", pts, fill, [(cy - R_ - 0.1, cy - R_ + 1.15, lt), (cy + R_ - 1.6, cy + R_ + 0.1, dk)], stroke=INK_FINE),
        P(f"{p}_lit", R(4.4, 0.5, 0.25), "$white@0.45", at=(-k * 0.2, cy - R_ + 1.25)),
    ]
    if mark == "dent":
        parts += dent(f"{p}_dent", -k * 0.9, cy + 0.5, fill)
    parts += [
        P(f"{p}_rim", ell(ex, R_), rim, at=(xm, cy), stroke=INK_FINE),
        P(f"{p}_inside", ell(ex - 0.5, R_ - 0.55), "$coal", at=(xm + k * 0.12, cy + 0.05)),
        P(f"{p}_rim_lit", ell(0.24, 0.85), "$white@0.55", at=(xm - ex * 0.68, cy - R_ * 0.55), rot=28),
    ]
    if mark == "chip":
        parts += [P(f"{p}_chip", poly([(-0.6, -0.5), (0.3, -0.7), (0.7, 0.1), (0.1, 0.7), (-0.5, 0.4)]), "$coal", at=(xm + k * 0.6, cy + R_ - 0.6))]
    return parts


# ================================================================ tin
def tin(prefix, x, y, s=1.0, rot=0.0, label="$bone", fill="$steel", opened=False, contents="$chitin.dark", stripe="$frost.dark@0.7"):
    """A food tin, 7 across and 8 tall (12.7 with its lid bent back). Origin: the middle of its foot.

    label: the paper band ("$bone", "$husk"; None for a bare tin). stripe: a cold band at the label's top (None to leave it off).
    opened: the lid cut round and bent back, standing up behind, the food showing (`contents`).
    """
    p = prefix
    lt, dk = tone(fill, 1), tone(fill, -1)
    rx, ry = 3.5, 1.2
    top, bot = -8 + ry, -ry
    parts = [shadow(f"{p}_shadow", 1.0, -0.35, 4.5, 1.3, "0.38")]
    if opened:
        # The lid, cut round and levered up on the uncut bit at the back: we
        # see its underside, its rings, and the ragged edge the opener left.
        lid = [(x_ + (0.18 if i % 2 else -0.12) * (y_ < top - 3.6), y_ + (0.3 if i % 2 else 0) * (y_ < top - 3.6))
               for i, (x_, y_) in enumerate(oval(0.5, top - 3.3, 3.3, 2.6, 22))]
        lid = turned(lid, 8, (0, top - ry))
        parts += [
            P(f"{p}_lid", poly(lid), tone(fill, 0), stroke=INK_FINE),
            P(f"{p}_lid_lit", poly(turned(arc_pts(0.5, top - 3.3, 2.75, 2.05, 160, 250, 6) + arc_pts(0.5, top - 3.3, 2.2, 1.6, 250, 160, 6), 8, (0, top - ry))), "$white@0.4"),
            P(f"{p}_lid_ring", ell(1.9, 1.45), None, at=turned([(0.65, top - 3.2)], 8, (0, top - ry))[0], rot=8, stroke={"color": dk, "width": 0.35}),
        ]
    parts += [
        *shaded(f"{p}_body", cyl_pts(rx, ry, top, bot), fill, [(-2.95, -1.95, lt), (1.45, 3.6, dk)], stroke=INK_FINE, axis=0),
        P(f"{p}_lit", R(0.6, 4.8, 0.3), "$white@0.45", at=(-2.4, -2.9)),
        # The side seam, and the beads rolled round the body to stiffen it.
        P(f"{p}_seam", R(0.3, 5.2, 0.15), "$ink@0.22", at=(-0.75, -2.85)),
        band(f"{p}_bead_a", front_arc(top + 0.75, rx, ry), 0.32, "$ink@0.32"),
        band(f"{p}_bead_a_lit", front_arc(top + 1.08, rx, ry), 0.3, "$white@0.3"),
        band(f"{p}_bead_b", front_arc(bot - 0.85, rx, ry), 0.32, "$ink@0.32"),
        band(f"{p}_bead_b_lit", front_arc(bot - 0.52, rx, ry), 0.3, "$white@0.3"),
    ]
    if label:
        yt, yb = top + 1.45, bot - 1.25
        lab = arc_pts(0, yt, rx, ry, 180, 0, 14) + arc_pts(0, yb, rx, ry, 0, 180, 14)
        parts += shaded(f"{p}_label", lab, label, [(1.5, 3.6, alpha(tone(label, -1), 0.75))], stroke=None, axis=0)
        if stripe:
            parts.append(P(f"{p}_label_stripe", poly(arc_pts(0, yt, rx, ry, 180, 0, 14) + arc_pts(0, yt + 0.55, rx, ry, 0, 180, 14)), stripe))
        parts += [
            band(f"{p}_label_ln", front_arc(yt + 1.25, rx, ry, 150, 82, 6), 0.42, "$slate.dark@0.6"),
            band(f"{p}_label_ln2", front_arc(yt + 2.0, rx, ry, 146, 108, 4), 0.42, "$slate.dark@0.5"),
            band(f"{p}_label_edge", front_arc(yb, rx, ry, 176, 4, 14), 0.25, "$ink@0.3"),
        ]
    if opened:
        parts += [
            P(f"{p}_rim", ell(rx, ry), lt, at=(0, top), stroke=INK_FINE),
            P(f"{p}_inside", ell(rx - 0.45, ry - 0.28), "$coal", at=(0, top + 0.05)),
            P(f"{p}_food", ell(rx - 0.8, ry - 0.45), contents, at=(0.1, top + 0.22)),
            P(f"{p}_food_lit", ell(0.9, 0.22), tone(contents, 1), at=(-0.6, top + 0.05)),
        ]
    else:
        parts += [
            P(f"{p}_rim", ell(rx, ry), lt, at=(0, top), stroke=INK_FINE),
            P(f"{p}_lid", ell(rx - 0.6, ry - 0.3), dk, at=(0, top + 0.03)),
            P(f"{p}_lid_face", ell(rx - 0.8, ry - 0.42), fill, at=(0.22, top + 0.1)),
            P(f"{p}_lid_ring", ell(1.75, 0.48), None, at=(0.2, top + 0.1), stroke={"color": dk, "width": 0.3}),
        ]
    parts.append(P(f"{p}_rim_lit", ell(1.0, 0.2), "$white@0.6", at=(-1.85, top - 0.88), rot=-14))
    return placed(parts, (x, y), s, rot)


def tin_stack(prefix, x, y, s=1.0, rot=0.0, rows=(2, 1), labels=("$bone", "$husk"), opened=None, lean=(0, -2, 3, -4, 2)):
    """Tins stacked on one another's lids, bottom row first: rows=(2, 1) is three in a pyramid (14.4 × 13.6), (1, 1) a column of two.
    Origin: the middle of the bottom row's feet. opened: the index of a tin (counting from the bottom left) whose lid is bent back.
    Each tin is `{prefix}_{i}`; `lean` tilts them a few degrees each, about their feet."""
    parts, i = [], 0
    for r, n in enumerate(rows):
        fy = -r * 5.6
        for j in range(n):
            fx = (j - (n - 1) / 2) * 7.3 + (0.4 if r % 2 else 0)
            if r > 0:
                # The dark where this tin's foot sits on the lids below.
                parts.append(P(f"{prefix}_{i}_ao", ell(3.7, 1.05), "$ink@0.32", at=(fx + 0.7, fy - 0.6)))
            t = tin(f"{prefix}_{i}", fx, fy, 1.0, lean[i % len(lean)], label=labels[i % len(labels)], opened=(i == opened))
            if r > 0:
                t = [q for q in t if not q["id"].endswith("_shadow")]
            parts += t
            i += 1
    return placed(parts, (x, y), s, rot)


# ================================================================ paper
def _rule(p, w, h, top, lines, ink, seed, ear_box, words=True, th=0.55, sp=1.85):
    """Writing as ruled strokes: a short head line, body lines ragged at the right, the last one short; words are breaks in the stroke."""
    out = []
    mx = max(1.2, w * 0.13)
    x0 = -w / 2 + mx
    full = w - 2 * mx
    rnd = _lcg(seed)
    for i in range(lines):
        yy = top + i * sp
        u = next(rnd)
        if i == 0 and lines > 2:
            L = full * (0.38 + 0.18 * u)
        elif i == lines - 1 and lines > 1:
            L = full * (0.3 + 0.25 * u)
        else:
            L = full * (0.72 + 0.28 * u)
        if ear_box and yy > ear_box[1] - th:
            L = min(L, ear_box[0] - x0 - 0.5)
        if L < 0.8:
            continue
        segs, at = [], 0.0
        while words and L - at > 0.9:
            n = 1.4 + 2.4 * next(rnd)
            if L - at - n < 1.0:
                n = L - at
            segs.append((at, n))
            at += n + 0.75
        if not segs:
            segs = [(0.0, L)]
        a = 0.62 if i else 0.72
        for j, (a0, n) in enumerate(segs):
            out.append(P(f"{p}_ln{i}_{j}", R(n, th if i else th + 0.1, th / 2), alpha(ink, a), at=(x0 + a0 + n / 2, yy)))
    return out


def page(prefix, x, y, s=1.0, rot=0.0, w=11.0, h=14.0, fill="$bone", lines=None, ear="br", pin=None, ink="$slate.dark", words=True, seed=3, lift=True, pin_fill="$steel.light", pivot=None, lie=1.0):
    """A sheet of paper, `w` × `h` (11 × 14), turned `rot`. Origin: its centre.

    fill: "$bone" | "$husk". lines: how many ruled strokes (None fits as many as the sheet holds; 0 for a blank sheet).
    ear: the dog-eared corner, "br" | "bl" | "tr" | "tl" | None. pin: "pin" (a tack at the top) | "tape" (a strip across the top) | None.
    words: break the strokes into words (False for one stroke a line, for a sheet under ~8 across). lift: its little shadow.
    pivot: for a page that sways — "pin" (the tack, or the top middle without one), "centre", or a point in the page's own frame.
    Every part then sits at that point (as polygons), so the same `rot` track on each turns the whole sheet about it:
        [track(q["id"], "rot", keys) for q in page("note", ..., pivot="pin")]
    lie: a page lying on the ground at the camp's slant, foreshortened to `lie` of its height after it is turned (0.6 or so).
    """
    p = prefix
    ink_line = INK_FINE
    hw, hh = w / 2, h / 2
    corners = {"tl": (-hw, -hh), "tr": (hw, -hh), "br": (hw, hh), "bl": (-hw, hh)}
    order = ["tl", "tr", "br", "bl"]
    d = min(w, h) * 0.24
    pts, flap = [], None
    for k, name in enumerate(order):
        c = corners[name]
        if name != ear:
            pts.append(c)
            continue
        a, b = corners[order[k - 1]], corners[order[(k + 1) % 4]]
        u = lambda q: ((q[0] - c[0]) / math.hypot(q[0] - c[0], q[1] - c[1]), (q[1] - c[1]) / math.hypot(q[0] - c[0], q[1] - c[1]))
        ua, ub = u(a), u(b)
        p1 = (c[0] + d * ua[0], c[1] + d * ua[1])
        p2 = (c[0] + d * ub[0], c[1] + d * ub[1])
        pts += [p1, p2]
        flap = [p1, p2, (p1[0] + p2[0] - c[0], p1[1] + p2[1] - c[1])]
    parts = []
    if lift:
        parts.append(P(f"{p}_shadow", poly(moved(pts, (0.45, 0.65))), "$ink@0.3"))
    shade = alpha(tone(fill, -1), 0.3)
    parts += shaded(f"{p}", pts, fill, [(hh - h * 0.14, hh + 1, shade)], stroke=ink_line)
    sp = 1.85 if h >= 9 else 1.5
    top = -hh + max(1.7, h * 0.15) + (0.9 if pin else 0)
    if lines is None:
        lines = max(1, int((hh - max(1.4, h * 0.1) - top) / sp) + 1)
    # Keep the writing clear of a dog-ear at the bottom right.
    ear_box = (hw - d, hh - d) if ear == "br" else None
    parts += _rule(p, w, h, top, lines, ink, seed, ear_box, words and w >= 7)
    if flap:
        cx = sum(q[0] for q in flap) / 3
        cy = sum(q[1] for q in flap) / 3
        sx = -0.35 if cx > 0 else 0.35
        sy = -0.35 if cy > 0 else 0.35
        parts += [
            P(f"{p}_ear_shadow", poly(moved(flap, (sx, sy))), "$ink@0.18"),
            P(f"{p}_ear", poly(flap), tone(fill, -1), stroke=INK_FINE),
        ]
    if pin == "pin":
        parts += [
            P(f"{p}_pin_shadow", circ(0.8), "$ink@0.35", at=(0.45, -hh + 1.55)),
            P(f"{p}_pin", circ(0.85), pin_fill, at=(0, -hh + 1.2), stroke=INK_FINE),
            P(f"{p}_pin_lit", circ(0.3), "$white@0.7", at=(-0.25, -hh + 0.95)),
        ]
    elif pin == "tape":
        tape = [(-2.6, -1.0), (-0.9, -1.15), (0.8, -0.95), (2.6, -1.1), (2.25, -0.5), (2.65, 0.05), (2.3, 0.55), (2.6, 1.05),
                (0.9, 0.95), (-0.8, 1.1), (-2.6, 0.95), (-2.25, 0.4), (-2.65, -0.15), (-2.3, -0.6)]
        parts += [
            P(f"{p}_tape", poly(tape), "$frost.light@0.45", at=(0, -hh + 0.1), rot=-5),
            P(f"{p}_tape_lit", R(4.4, 0.35, 0.17), "$white@0.4", at=(0, -hh - 0.55), rot=-5),
        ]
    pv = None if pivot is None else ({"pin": (0, -hh + 1.2), "centre": (0, 0)}[pivot] if isinstance(pivot, str) else pivot)
    if lie != 1:
        parts = squashed(placed(parts, (0, 0), 1.0, rot), lie)
        if pv is not None:
            q = turned([pv], rot)[0]
            parts = pivoted(parts, (q[0], q[1] * lie))
        return placed(parts, (x, y), s)
    if pv is not None:
        parts = pivoted(parts, pv)
    return placed(parts, (x, y), s, rot)


def page_stack(prefix, x, y, s=1.0, rot=0.0, n=3, w=11.0, h=13.0, fills=("$husk", "$bone", "$bone"), weight=True, seed=5, lie=1.0):
    """A few sheets squared up roughly, each a little off the last, the top one written on and a stone on it to keep the wind off.
    About (w+4) × (h+2) (15 × 15). Origin: the centre of the top sheet. Sheets are `{prefix}_s{i}` (bottom first); the stone is `{prefix}_stone`.
    lie: foreshorten the sheets (not the stone) to lie on the ground at the camp's slant, e.g. 0.5 for 15 × 8."""
    offs = [(-1.5, 1.2, -8), (1.3, 0.6, 5.5), (-0.4, 0.3, -3), (0.8, 0.5, 3)]
    parts = []
    for i in range(n):
        dx, dy, r = offs[i % len(offs)] if i < n - 1 else (0, 0, -1)
        last = i == n - 1
        sheet = page(f"{prefix}_s{i}", dx, dy, 1.0, r, w, h, fills[i % len(fills)], None if last else 0,
                     ear="tl" if i == 0 and n > 1 else None, seed=seed + i, lift=(i == 0))
        if i:
            # The sheet under shows its edge as a thin dark line where this one lies on it.
            parts.append(P(f"{prefix}_s{i}_ao", R(w, h, 0.6), "$ink@0.22", at=(dx + 0.3, dy + 0.35), rot=r))
        parts += sheet
    if lie != 1:
        parts = squashed(placed(parts, (0, 0), 1.0, rot), lie)
        rot = 0
    if weight:
        a = math.radians(rot)
        sx, sy = w * 0.2, -h * 0.12
        parts += stone(f"{prefix}_stone", sx * math.cos(a) - sy * math.sin(a), (sx * math.sin(a) + sy * math.cos(a)) * lie + 1.6 * (1 - lie), 1.0, 0)
    return placed(parts, (x, y), s, rot)


def tag(prefix, x, y, s=1.0, rot=0.0, w=5.5, h=7.5, cord=4.5, fill="$bone", lines=2, string="$bone.dark"):
    """A paper tag on its string: clipped corners, a steel grommet round the hole, the string looped through and knotted,
    a couple of ruled strokes. Origin: where the string is tied on; the tag hangs below it (w × cord+h, 5.5 × 12).

    Every part is centred on the tie, so the same `rot` track on each of them swings the whole tag about it:
        [track(q["id"], "rot", keys) for q in tag("tag", ...)]
    """
    p = prefix
    t = cord - 1.3            # the tag's top edge
    c = w * 0.27
    hw = w / 2
    body = [(-hw, t + c), (-hw + c, t), (hw - c, t), (hw, t + c), (hw, t + h), (-hw, t + h)]
    ey = t + 1.35              # the eyelet
    parts = [
        band(f"{p}_string", [(0, 0), (0.25, (t - 0.8) * 0.5), (0, t - 0.75)], 0.55, string),
        *shaded(f"{p}_body", body, fill, [(hw * 0.45, hw + 1, alpha(tone(fill, -1), 0.6))], stroke=INK_FINE, axis=0),
        P(f"{p}_grommet", poly(oval(0, ey, 1.05)), "$steel", stroke=INK_FINE),
        P(f"{p}_grommet_lit", poly(arc_pts(0, ey, 0.85, 0.85, 190, 280, 4) + [(0, ey)]), "$white@0.5"),
        P(f"{p}_hole", poly(oval(0, ey, 0.48, n=10)), "$coal"),
        # The string's loop: down over the top edge into the hole, knotted above.
        band(f"{p}_loop", [(0, t - 0.75), (0.05, t + 0.2), (0, ey)], 0.5, string),
        P(f"{p}_knot", poly(oval(0, t - 0.75, 0.55, 0.45, 8)), string),
        band(f"{p}_tail", [(0.2, t - 0.6), (0.9, t - 0.1), (1.2, t + 0.6)], 0.4, string),
    ]
    for i in range(lines):
        L = (w - 2.2) * (0.85 if i == 0 else 0.55 - 0.1 * (i - 1))
        y0 = ey + 2.0 + i * 1.5
        parts.append(P(f"{p}_ln{i}", poly(rr(L, 0.5, 0.25, (-hw + 1.1 + L / 2, y0), 2)), "$slate.dark@0.6"))
    return placed(parts, (x, y), s, rot)


# ================================================================ dial
def dial(prefix, x, y, s=1.0, rot=0.0, reading=0.3, face="$bone", cold=(0.0, 0.3), cold_fill="$frost", bezel="$steel", ticks=9, needle="$ink"):
    """A round gauge, r 4.5. Origin: its centre, which is also the needle's pivot.

    reading: 0..1 over the scale's 270 degrees (0 lower left, 0.5 straight up, 1 lower right).
    face: "$bone" | "$frost.light" | ... cold: the (from, to) of the scale painted `cold_fill` (None for none).
    `{prefix}_needle` sits at the centre pointing along its own +x, turned to the reading: a `rot` track on it
    (offsets in degrees from where it rests; 270 degrees is the whole scale) swings it about the centre.
    """
    p = prefix
    deg = lambda r: 135 + 270 * r
    parts = [
        P(f"{p}_bezel", circ(4.5), bezel, stroke=INK_FINE),
        P(f"{p}_bezel_lit", ring_arc(3.95, 0.75, 195, 290), "$white@0.5"),
        P(f"{p}_bezel_dk", ring_arc(3.95, 0.75, 10, 110), tone(bezel, -1)),
        P(f"{p}_face", circ(3.45), face, stroke={"color": "$ink@0.6", "width": 0.35}),
        # The glass sits in the bezel: its rim shades the face along the top left.
        P(f"{p}_face_shade", ring_arc(3.05, 0.6, 170, 300), "$ink@0.16"),
    ]
    if cold:
        parts.append(P(f"{p}_cold", ring_arc(2.62, 1.05, deg(cold[0]), deg(cold[1])), cold_fill))
    for i in range(ticks):
        a = math.radians(deg(i / (ticks - 1)))
        major = i in (0, ticks - 1, (ticks - 1) // 2)
        r0, r1, tw = (2.05 if major else 2.4), 3.05, (0.42 if major else 0.3)
        c, s_ = math.cos(a), math.sin(a)
        nx, ny = -s_ * tw / 2, c * tw / 2
        parts.append(P(f"{p}_tick_{i}", poly([(r0 * c + nx, r0 * s_ + ny), (r1 * c + nx, r1 * s_ + ny), (r1 * c - nx, r1 * s_ - ny), (r0 * c - nx, r0 * s_ - ny)]), "$ink@0.8"))
    parts += [
        # Needle: a tapered blade from the hub, with a short counterweight tail behind it.
        P(f"{p}_needle", poly([(-1.1, -0.2), (-0.95, -0.34), (-0.5, -0.34), (-0.2, -0.24), (3.05, 0), (-0.2, 0.24), (-0.5, 0.34), (-0.95, 0.34), (-1.1, 0.2)]), needle, rot=deg(reading)),
        P(f"{p}_hub", circ(0.68), tone(bezel, -1), stroke={"color": "$ink", "width": 0.3}),
        P(f"{p}_hub_lit", circ(0.24), "$white@0.6", at=(-0.2, -0.2)),
        P(f"{p}_glint", ring_arc(2.55, 0.5, 205, 248), "$white@0.55"),
    ]
    return placed(parts, (x, y), s, rot)


# ================================================================ stool
def stool(prefix, x, y, s=1.0, rot=0.0, seat="$slate.light", frame="$steel"):
    """A three-legged camp stool seen three-quarters on, 12 across and 10 tall: a round canvas seat on a steel rim, three splayed legs
    (two in front, one behind), a ring brace round them halfway down, rubber feet. Origin: the middle of the ground under it."""
    p = prefix
    sy, srx, sry = -8.9, 6.0, 2.3          # the seat's top ellipse
    gy, grx, gry = -1.0, 5.6, 1.6          # the ellipse the feet stand on
    by, brx, bry = -4.6, 4.3, 1.45         # the brace
    top = lambda a: (3.2 * math.cos(math.radians(a)), sy + 1.2 + 1.0 * math.sin(math.radians(a)))
    foot = lambda a: (grx * math.cos(math.radians(a)), gy + gry * math.sin(math.radians(a)))
    legs = {"back": 268, "left": 140, "right": 40}
    dk = tone(frame, -1)

    def leg(name, fill):
        a = legs[name]
        t, f = top(a), foot(a)
        return [
            inked(band(f"{p}_leg_{name}", [t, f], 1.05, fill)),
            P(f"{p}_foot_{name}", ell(0.75, 0.42), "$coal", at=(f[0], f[1] - 0.05), stroke=INK_FINE),
        ]

    parts = [
        shadow(f"{p}_shadow", 0.9, -0.6, 6.6, 1.9, "0.36"),
        *leg("back", dk),
        inked(band(f"{p}_brace_back", arc_pts(0, by, brx, bry, 190, 350, 10), 0.6, dk)),
        *leg("left", frame),
        *leg("right", dk),
        P(f"{p}_leg_left_lit", poly([top(140), foot(140), (foot(140)[0] + 0.4, foot(140)[1]), (top(140)[0] + 0.35, top(140)[1])]), "$white@0.4"),
        inked(band(f"{p}_brace", arc_pts(0, by, brx, bry, 10, 170, 12), 0.6, frame)),
        # The seat: the steel rim's edge, the canvas stretched in it, its sag shaded.
        P(f"{p}_rim", poly(arc_pts(0, sy, srx, sry, 0, 180, 14) + arc_pts(0, sy + 1.1, srx, sry, 180, 0, 14)), dk, stroke=INK_FINE),
        P(f"{p}_top", ell(srx, sry), frame, at=(0, sy), stroke=INK_FINE),
        P(f"{p}_canvas", ell(srx - 0.6, sry - 0.36), seat, at=(0.05, sy + 0.05)),
        P(f"{p}_canvas_sag", ell(srx - 2.0, sry - 0.95), alpha(tone(seat, -1), 0.45), at=(0.7, sy + 0.35)),
        P(f"{p}_rim_lit", poly(arc_pts(0, sy, srx - 0.15, sry - 0.1, 175, 250, 6) + arc_pts(0, sy, srx - 0.55, sry - 0.38, 250, 175, 6)), "$white@0.5"),
    ]
    return placed(parts, (x, y), s, rot)


# ================================================================ ladle
def ladle(prefix, x, y, s=1.0, rot=0.0, length=15.0, side="right", gold="$gold"):
    """A steel ladle hung by its hooked handle over a rim, the bowl at the bottom tipped out with a little jelly pooled in its low side.
    Origin: the inside of the hook, i.e. the rim it hangs on. side: which side of the rim the ladle hangs ("right": the vessel is to the
    left). About 9 × (length + 5): 9 × 20. gold: the jelly's colour (None for an empty bowl). Ids: `{prefix}_handle`, `{prefix}_bowl`,
    `{prefix}_gold`."""
    p = prefix
    k = 1 if side == "right" else -1
    r = 1.25
    hook = [(-k * r, 1.3), (-k * r, 0)] + [(k * r * math.cos(math.radians(a)), -r * math.sin(math.radians(a))) for a in (150, 120, 90, 60, 30)]
    hook += [(k * r, 0), (k * r * 1.05, length * 0.5), (k * 1.45, length)]
    C = (k * 4.35, length + 1.25)             # the bowl's rim, centre
    tilt = k * 26
    bowl = turned(arc_pts(C[0], C[1], 3.0, 2.9, 0, 180, 12) + arc_pts(C[0], C[1], 3.0, 1.2, 180, 360, 12), tilt, C)
    rim_in = turned(oval(C[0], C[1], 2.45, 0.85, 16), tilt, C)
    parts = [P(f"{p}_handle", poly(_strip(hook, 1.05)), "$steel", stroke=INK_FINE)]
    straight = [(k * r - 0.3, 0.8), (k * r * 1.05 - 0.3, length * 0.5), (k * 1.45 - 0.3, length - 0.6)]
    parts += [
        band(f"{p}_handle_lit", straight, 0.3, "$white@0.45"),
        *shaded(f"{p}_bowl", bowl, "$steel", [(C[0] - 3.2, C[0] - 1.9, "$steel.light"), (C[0] + 1.0, C[0] + 3.5, "$steel.dark")], stroke=INK_FINE, axis=0),
        P(f"{p}_bowl_lip", poly(turned(oval(C[0], C[1], 3.0, 1.2, 18), tilt, C)), "$steel.light", stroke=INK_FINE),
        P(f"{p}_bowl_in", poly(rim_in), "$steel.dark2"),
    ]
    if gold:
        # Jelly lies level whichever way the bowl hangs: a flat pool in its low side.
        low = turned([(C[0] - k * 0.15, C[1] + 0.3)], tilt, C)[0]
        parts += [
            P(f"{p}_gold", ell(1.55, 0.55), gold, at=low),
            P(f"{p}_gold_lit", ell(0.55, 0.16), tone(gold, 2), at=(low[0] - 0.4, low[1] - 0.15)),
        ]
    parts.append(P(f"{p}_bowl_lit", poly(turned(arc_pts(C[0], C[1], 2.8, 1.02, 185, 250, 5) + arc_pts(C[0], C[1], 2.45, 0.8, 250, 185, 5), tilt, C)), "$white@0.55"))
    return placed(parts, (x, y), s, rot)


def _strip(pts, w):
    """A polyline as a closed strip `w` wide (the same as `band`, as points)."""
    return band("_", pts, w, None)["shape"]["points"]


# ================================================================ saw
def saw(prefix, x, y, s=1.0, rot=0.0, teeth=13, handle="$slate", hole="$soil"):
    """The expedition's saw lying on the ground: a tapered blade with set teeth, a hang hole at the tip, scratches and a fleck of
    rust, a closed handle with its grip hole and two screws. 38 × 14 (the doc's 38 × 16 with its shadow). Origin: its centre.
    hole: what shows through the grip and the hang hole (the ground under it)."""
    p = prefix
    tx, hx = -18.5, 7.5          # the tip and the heel
    edge = 3.0                   # the tooth line
    back = lambda xx: -1.2 + (xx - tx) / (hx - tx) * (-4.9 + 1.2)
    pitch = (hx - 0.6 - tx) / teeth
    zig = []
    for i in range(teeth):
        a = hx - 0.6 - i * pitch
        zig += [(a, edge), (a - 0.72 * pitch, edge + 1.55)]
    blade = [(tx, back(tx)), (hx, back(hx)), (hx, edge)] + zig + [(tx + 0.15, edge), (tx - 0.25, edge - 1.2)]
    # The handle: a horn swept back over the hand at the top, a toe forward under it, closed round the grip.
    hp = [(5.2, -4.8), (6.6, -6.3), (10.5, -6.8), (14.6, -7.1), (18.4, -7.9), (19.6, -7.2), (19.0, -5.4),
          (19.8, -2.2), (20.0, 2.4), (18.9, 5.6), (16.6, 7.0), (11.8, 7.1), (8.6, 6.9), (7.8, 5.6), (8.4, 4.4),
          (7.6, 2.6), (5.6, 2.4), (5.0, -2.0)]
    grip = turned(rr(4.0, 7.4, 1.9, (13.6, 0.1), 3), -16, (13.6, 0.1))
    parts = [
        P(f"{p}_shadow", poly(moved(blade, (0.7, 0.9))), "$ink@0.38"),
        P(f"{p}_shadow_h", poly(moved(hp, (0.8, 1.0))), "$ink@0.38"),
        P(f"{p}_blade", poly(blade), "$steel", stroke=INK_HAIR),
        # The back catches the light; the edge above the teeth is in the blade's own shade.
        P(f"{p}_blade_lit", poly([(tx + 0.3, back(tx) + 0.35), (hx, back(hx) + 0.35), (hx, back(hx) + 1.35), (tx + 0.3, back(tx) + 1.2)]), "$steel.light"),
        P(f"{p}_blade_dk", poly([(tx + 0.1, edge - 1.2), (hx, edge - 1.4), (hx, edge), (tx + 0.15, edge)]), "$steel.dark@0.55"),
    ]
    # Set: every other tooth bent away from the light.
    for i in range(1, teeth, 2):
        a = hx - 0.6 - i * pitch
        parts.append(P(f"{p}_set_{i}", poly([(a, edge), (a - 0.72 * pitch, edge + 1.55), (a - pitch, edge)]), "$steel.dark"))
    parts += [
        P(f"{p}_hang", circ(0.75), hole, at=(-15.6, 0.3), stroke=INK_FINE),
        *scratches(f"{p}_scratch", -3.0, 0.2, 16, 3.0, 4, "$steel.light@0.6", 4),
        P(f"{p}_rust", poly([(-0.9, -0.3), (0.2, -0.75), (1.1, -0.2), (0.6, 0.55), (-0.5, 0.5)]), "$rust@0.85", at=(-11.6, 1.1)),
        P(f"{p}_rust_b", circ(0.38), "$rust@0.7", at=(-10.2, 1.7)),
        # The handle, closed round the grip, clamping the heel.
        *shaded(f"{p}_handle", hp, handle, [(-8, -4.9, tone(handle, 1)), (3.6, 8, tone(handle, -1))], stroke=INK_HAIR),
        P(f"{p}_handle_lit", poly([(6.0, -4.9), (6.9, -5.9), (14.6, -6.6), (18.2, -7.3), (18.4, -6.7), (14.6, -5.9), (7.3, -5.2), (6.5, -4.3)]), "$white@0.3"),
        P(f"{p}_grip", poly(grip), hole, stroke=INK_FINE),
    ]
    for i, (sx, sy_) in enumerate([(8.4, -2.7), (8.7, 1.7)]):
        parts += [
            P(f"{p}_screw_{i}", circ(0.95), "$steel", at=(sx, sy_), stroke=INK_FINE),
            P(f"{p}_screw_{i}_slot", R(1.3, 0.32, 0.16), "$ink@0.7", at=(sx, sy_), rot=35 + i * 40),
            P(f"{p}_screw_{i}_lit", circ(0.3), "$white@0.6", at=(sx - 0.38, sy_ - 0.38)),
        ]
    return placed(parts, (x, y), s, rot)


# ================================================================ stone
def stone(prefix, x, y, s=1.0, rot=0.0, fill="$smoke"):
    """A small stone used as a paperweight, 6 × 4: a lit top, a front face and a darker facet to the right. Origin: the middle of its foot."""
    p = prefix
    out = [(-3.0, -0.8), (-2.5, -2.6), (-0.9, -3.8), (1.4, -3.75), (2.8, -2.5), (3.05, -0.8), (2.0, 0), (-1.8, 0)]
    topf = [(-2.5, -2.6), (-0.9, -3.8), (1.4, -3.75), (1.9, -2.55), (-0.5, -2.1)]
    side = [(1.9, -2.55), (1.4, -3.75), (2.8, -2.5), (3.05, -0.8), (2.0, 0), (1.25, -1.3)]
    return placed([
        shadow(f"{prefix}_shadow", 0.9, -0.12, 3.2, 0.8, "0.4"),
        P(f"{p}", poly(out), fill),
        P(f"{p}_top", poly(topf), tone(fill, 1)),
        P(f"{p}_side", poly(side), tone(fill, -1)),
        P(f"{p}_lit", ell(1.0, 0.32), "$white@0.5", at=(-0.8, -3.1), rot=-12),
        P(f"{p}_rim", poly(out), None, stroke=INK_FINE),
    ], (x, y), s, rot)
