"""The camp's small iron: padlock, chain, hasp, hinge, clamp, hook, wire coil.

    from bits_metal import padlock, chain, sag, hasp, hinge, clamp, hook, wire_coil, swing_tracks

Everything here is steel the expedition carried in, so it is cold: $steel and
$slate in two or three flat values, lit from the upper left, a fine ink line
round each mass. Each helper draws its thing about its own origin at its
natural size in the camp and returns parts (`placed()` at x, y, s, rot);
`chain` and `sag` take points in the document's own frame instead.

Every part is a polygon whose `at` is the thing's origin, so a `rot` track
on every part of a padlock swings it about the point it hangs from
(`swing_tracks`). A ring (a chain link, a turn of wire) is one polygon that
runs round its outside and back round its hole, so the hole is a real hole
and whatever is behind it shows through; it sits on an ink ring a little
bigger all round. Every other mass carries its ink line on its base part,
where only the outer half shows, so a 2-unit hinge leaf keeps its values.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw import *  # noqa: E402,F401,F403

# The way the light travels: from the upper left, more from above than from
# the side. A face whose outward normal points against it is lit.
LIGHT = (0.55, 0.835)


_LEVEL = {"light2": 2, "light": 1, "": 0, "dark": -1, "dark2": -2}
_NAME = {v: k for k, v in _LEVEL.items()}


def tone(token, k):
    """`token` stepped `k` along its ramp ($slate.light, -1 is $slate), keeping its alpha; clamped at the ends."""
    body, _, alpha = token.partition("@")
    name, _, ramp = body.partition(".")
    lv = max(-2, min(2, _LEVEL[ramp] + k))
    out = name + ("." + _NAME[lv] if lv else "")
    return out + ("@" + alpha if alpha else "")


def _ink(s=1.0, w=0.9):
    """The outline for a small steel thing. It goes on the mass's base part, under its fill, so only its
    outer half shows (0.45 at the default 0.9, none of it eating into a 2-unit leaf or a 1-unit wire).
    It stays that weight on the page however far the thing is scaled down, and thickens by 1.6 once the
    thing is drawn half as big again."""
    page = w if s < 1.5 else w * 1.6
    return {"color": "$ink", "width": r2(page / s)}


# ---------------------------------------------------------------- geometry

def _arc(cx, cy, rx, ry, a0, a1, n):
    """Points on an ellipse from a0 to a1 degrees (y down: 90 is the bottom, 270 the top), ends included."""
    out = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def _oval(cx, cy, rx, ry, n=28, a0=0.0):
    return [(cx + rx * math.cos(math.radians(a0) + 2 * math.pi * k / n), cy + ry * math.sin(math.radians(a0) + 2 * math.pi * k / n)) for k in range(n)]


def _stadium(cx, cy, length, width, ang=0.0, n=7):
    """A bar with round ends, `length` end to end, along `ang` degrees; starts at the far end's tip."""
    r = width / 2
    h = max(length / 2 - r, 0.0)
    pts = _arc(h, 0, r, r, 0, 90, n)[:-1] + _arc(-h, 0, r, r, 90, 270, 2 * n)[:-1] + _arc(h, 0, r, r, 270, 360, n)[:-1]
    return _turn(pts, ang, (cx, cy))


def _turn(pts, ang, at=(0, 0)):
    a = math.radians(ang)
    c, s = math.cos(a), math.sin(a)
    return [(at[0] + x * c - y * s, at[1] + x * s + y * c) for x, y in pts]


def _annulus(outer, inner):
    """One polygon round `outer` and back round `inner`: a ring whose hole shows what is behind it."""
    inner = inner[::-1]
    o = outer[0]
    k = min(range(len(inner)), key=lambda j: (inner[j][0] - o[0]) ** 2 + (inner[j][1] - o[1]) ** 2)
    inner = inner[k:] + inner[:k]
    return outer + [o] + inner + [inner[0]]


def _cut(pts, d, lo, hi, about=(0, 0)):
    """The part of `pts` whose distance along unit direction `d` from `about` lies in [lo, hi]."""
    dx, dy = d
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    loc = [((x - about[0]) * dx + (y - about[1]) * dy, -(x - about[0]) * dy + (y - about[1]) * dx) for x, y in pts]
    c = clip(loc, 0, lo, hi)
    return [(about[0] + u * dx - v * dy, about[1] + u * dy + v * dx) for u, v in c]


def _mass(id, pts, base, bands, stroke):
    """A mass in flat values: `base` (carrying the ink line, outer half showing) under each (pts_or_None, fill) band."""
    out = [P(id, poly(pts), base, stroke=stroke)]
    i = 0
    for b, fill in bands:
        if b and len(b) >= 3:
            out.append(P(f"{id}_v{i}", poly(b), fill))
            i += 1
    return out


def _ring(id, outer, inner, ink_outer, ink_inner, base, bands):
    """A ring with a real hole: an ink ring a little bigger all round (`ink_outer`, `ink_inner` from the
    same maker as `outer`, `inner`), the metal on it, then its flat bands."""
    ring = _annulus(outer, inner)
    out = [P(f"{id}_ink", poly(_annulus(ink_outer, ink_inner)), "$ink")]
    out += _mass(id, ring, base, [(f(ring) if callable(f) else f, fill) for f, fill in bands], None)
    return out


def _mirror(pts, m):
    return [(m * x, y) for x, y in pts]


def _len(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def _at_len(pts, s):
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if s <= seg or i == len(pts) - 2:
            t = 0 if seg == 0 else min(1.0, s / seg)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        s -= seg
    return pts[-1]


def sag(p0, p1, drop, n=10):
    """Points along a chain or cord hung from p0 to p1, sagging `drop` below the straight line at its middle."""
    out = []
    for k in range(n + 1):
        t = k / n
        out.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t + 4 * drop * t * (1 - t)))
    return out


# ================================================================ padlock

def padlock(prefix, x, y, s=1.0, rot=0.0, fill="$steel", shackle="$steel", open=False):
    """A steel padlock, origin where it hangs from: the inside of the shackle's crown. Natural 7 x 10.3
    (x -3.5..3.5, y -1.15..9.15). `open` lifts the shackle out of its toe hole and swings it round on its
    heel (then x -6.05..3.5, y -2.85..9.15). `fill` is the body's steel, `shackle` the hoop's. Every part is
    a polygon placed at the origin, so a `rot` track on all of them swings the lock where it hangs."""
    ink = _ink(s)
    p = prefix
    b = 1.15                      # the shackle's bar
    ai = 1.25                     # half its inside width
    rm, ao_ = ai + b / 2, ai + b  # centre line, outside
    top, H, Wb = 3.55, 5.6, 7.0   # the body
    bot = top + H
    hole_y = top + 0.5            # where the legs go in, on the body's top face

    def hoop(ux, cy, lb, rb):
        """The U of the shackle about x = ux, crown centre at cy; left leg ends at lb, right at rb."""
        pts = [(ux - ao_, lb), (ux - ao_, cy)]
        pts += _arc(ux, cy, ao_, ao_, 180, 360, 14)[1:-1]
        pts += [(ux + ao_, cy), (ux + ao_, rb), (ux + ai, rb), (ux + ai, cy)]
        pts += _arc(ux, cy, ai, ai, 360, 180, 10)[1:-1]
        pts += [(ux - ai, cy), (ux - ai, lb)]
        return pts

    body = rr(Wb, H, 1.1, (0, top + H / 2), 3)
    parts = [
        *_mass(f"{p}_body", body, fill, [
            (clip(body, 0, Wb / 2 - 1.5, 9), tone(fill, -1)),
            (clip(body, 1, bot - 0.8, 99), tone(fill, -1)),
            (clip(body, 1, -9, top + 1.0), tone(fill, 1)),
        ], ink),
        # The edge where the top face turns down into the front catches the light.
        P(f"{p}_lit", poly(rr(4.4, 0.36, 0.18, (-1.0, top + 1.0), 2)), "$white@0.55"),
        # It is laminated, plates riveted in a stack, like the ones in the stores: two seams across the face.
        P(f"{p}_lam_a", poly(rr(Wb - 0.5, 0.24, 0.1, (0, top + 2.35), 1)), "$ink@0.18"),
        P(f"{p}_lam_b", poly(rr(Wb - 0.5, 0.24, 0.1, (0, top + 3.95), 1)), "$ink@0.18"),
        # The holes the legs go into.
        P(f"{p}_hole_heel", poly(_oval(-rm, hole_y, b / 2 + 0.22, 0.36, 16)), "$ink@0.8"),
        P(f"{p}_hole_toe", poly(_oval(rm, hole_y, b / 2 + 0.22, 0.36, 16)), "$ink@0.8"),
    ]
    if open:
        lift = 1.7
        ux, cy = -2 * rm, ai - lift
        u = hoop(ux, cy, hole_y - lift - 0.2, hole_y)
    else:
        ux, cy = 0.0, ai
        u = hoop(ux, cy, hole_y, hole_y)
    parts += _mass(f"{p}_shackle", u, shackle, [(clip(u, 0, ux + rm + 0.05, 99), tone(shackle, -1))], ink)
    # Its shine, down the outside of the left leg and over the crown.
    hl = [(ux - rm - 0.2, cy + (1.6 if not open else 1.2))] + _arc(ux, cy, rm + 0.2, rm + 0.2, 180, 262, 6)
    parts.append(band(f"{p}_shackle_lit", hl, 0.36, "$white@0.6"))
    if open:
        # The toe's free end, with the notch the bolt catches in.
        parts.append(P(f"{p}_notch", poly(rr(0.55, 0.36, 0.1, (ux - rm + 0.3, hole_y - lift - 0.9), 1)), "$ink@0.7"))
    # The keyhole, and the bright lip of steel under it on the right.
    kx, ky = 0.0, top + 2.75
    key = _arc(kx, ky, 0.62, 0.62, 125, 415, 14) + [(kx + 0.4, ky + 1.55), (kx - 0.4, ky + 1.55)]
    parts += [
        P(f"{p}_keyhole", poly(key), "$ink@0.9"),
        P(f"{p}_keyhole_lip", poly(_arc(kx, ky, 0.98, 0.98, 10, 75, 4) + _arc(kx, ky, 0.66, 0.66, 75, 10, 4)), tone(fill, 1)),
    ]
    # Wear: a couple of scuffs low on the lit side, a fleck of rust in the shade.
    parts += [
        P(f"{p}_scuff_a", poly(_turn(rr(1.5, 0.28, 0.14, (0, 0), 1), -18, (-2.1, bot - 1.6))), tone(fill, 1) + "@0.8"),
        P(f"{p}_scuff_b", poly(_turn(rr(0.9, 0.24, 0.12, (0, 0), 1), -8, (-1.3, bot - 1.05))), tone(fill, 1) + "@0.6"),
        P(f"{p}_rust", poly(_oval(2.45, bot - 0.6, 0.45, 0.3, 10)), "$rust@0.85"),
        P(f"{p}_rust_b", poly(_oval(3.0, bot - 1.25, 0.24, 0.2, 8)), "$rust@0.7"),
    ]
    return placed(parts, (x, y), s, rot)


# ================================================================ chain

def chain(prefix, pts, link=5.0, fill="$steel", first="face", shadow=True, within=None):
    """A chain along `pts` (document coordinates, straight or from `sag`), drawn as interlocking links,
    face-on rings and edge-on bars by turns, the bars over the rings with their ends in the rings' holes.
    `link` is a link's outside length (width 0.68 of it, wire 0.19); the first link's hole starts at
    pts[0] and the last one's ends at pts[-1], its end wire just past it. `first` is "face" or "edge"; a
    padlock hangs from an edge-on end link, its origin on that end point. `shadow` lays the chain's
    shadow on the surface behind it (<prefix>_shadow). `within` (x0, x1) cuts the chain off at those x, for
    a chain that goes round the side of the thing it is wrapped on. Each link is <prefix>_<i> with _ink,
    _v0, _v1 (and _drop, the bar's shadow on the rings)."""
    L = link
    W, t = 0.68 * L, 0.19 * L
    pitch = L - 2 * t
    total = _len(pts)
    n = max(1, round(total / pitch))
    knots = [_at_len(pts, total * k / n) for k in range(n + 1)]
    ink = _ink(1.0, 0.8)
    faces, edges = [], []
    for k in range(n):
        a, b = knots[k], knots[k + 1]
        c = math.hypot(b[0] - a[0], b[1] - a[1])
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        face = (k % 2 == 0) == (first == "face")
        id = f"{prefix}_{k}"
        if face:
            st = lambda ln, wd: _stadium(mx, my, ln, wd, ang)
            faces += _ring(
                id, st(c + 2 * t, W), st(c, W - 2 * t), st(c + 2 * t + 0.8, W + 0.8), st(c - 0.5, W - 2 * t - 0.5), fill,
                [(lambda r: _cut(r, LIGHT, -99, -0.28 * W, (mx, my)), tone(fill, 1)),
                 (lambda r: _cut(r, LIGHT, 0.24 * W, 99, (mx, my)), tone(fill, -1))],
            )
        else:
            te = 1.15 * t
            bar = _stadium(mx, my, c + 2 * t, te, ang)
            # The side of the bar the light falls on.
            nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
            if nx * LIGHT[0] + ny * LIGHT[1] > 0:
                nx, ny = -nx, -ny
            edges.append(P(f"{id}_drop", poly([(px + 0.3, py + 0.45) for px, py in bar]), "$ink@0.35"))
            shine = _stadium(mx + nx * te * 0.18, my + ny * te * 0.18, c + 2 * t - te * 1.2, te * 0.26, ang, 4)
            edges += _mass(id, bar, fill, [
                (_cut(bar, (-nx, -ny), te * 0.1, 99, (mx, my)), tone(fill, -1)),
                (shine, "$white@0.55"),
            ], ink)
    out = []
    if shadow:
        out.append(band(f"{prefix}_shadow", [(px + 0.9, py + 1.3) for px, py in pts], W * 0.7, "$ink@0.22"))
    out += faces + edges
    if within:
        cut = []
        for q in out:
            c = clip([tuple(v) for v in q["shape"]["points"]], 0, within[0], within[1])
            if len(c) >= 3:
                cut.append(dict(q, shape=poly(c)))
        out = cut
    return out


# ================================================================ hasp

def hasp(prefix, x, y, s=1.0, rot=0.0, fill="$steel.dark", staple="$steel.dark", locked=True, lock_s=0.66, length=7.4):
    """A locker's hasp, origin on its hinge pin: a leaf screwed to the lid above, the knuckle, the hasp
    plate hanging `length` down over the box with the staple standing out through its slot, and (if
    `locked`) a padlock `lock_s` of its size hung through the staple, its crown behind the staple's front
    bend. The hasp is darker iron than the lock so the two come apart. Natural 5 x 10.5 with no lock
    (x -2.65..2.3, y -2.5..8.0); the lock hangs to y 11.2. The lock's parts are <prefix>_lock_*, all
    placed at its hang point (0, length - 2.25), so a rot track on them swings it on the staple."""
    ink = _ink(s)
    p = prefix
    pw = 3.2
    sy = length - 2.6                    # the slot's middle
    plate = rr(pw, length + 0.4, 1.3, (0, length / 2 - 0.2), 4)
    leaf = rr(4.6, 2.4, 0.5, (0, -1.3), 2)
    knuckle = rr(4.4, 1.6, 0.75, (0, 0), 3)
    parts = [
        # The leaf on the lid, two screws in it.
        *_mass(f"{p}_leaf", leaf, fill, [(clip(leaf, 1, -9, -2.15), tone(fill, 1)), (clip(leaf, 0, 1.6, 9), tone(fill, -1))], ink),
        *[q for i, sx in enumerate((-1.5, 1.5)) for q in _screw(f"{p}_leaf_sc{i}", sx, -1.55, 0.42, s)],
        # The plate, and its shadow on the box.
        P(f"{p}_plate_shadow", poly([(px + 0.5, py + 0.6) for px, py in plate]), "$ink@0.35"),
        *_mass(f"{p}_plate", plate, fill, [
            (clip(plate, 0, pw / 2 - 0.8, 9), tone(fill, -1)),
            (clip(plate, 0, -9, -pw / 2 + 0.45), tone(fill, 1)),
        ], ink),
        # The slot, and the dark of the box through it.
        P(f"{p}_slot", poly(rr(1.4, 2.7, 0.7, (0, sy), 3)), "$ink@0.9"),
        # The knuckle over the plate's head: the outer two turns are the leaf's, the middle the plate's.
        *_mass(f"{p}_knuckle", knuckle, fill, [
            (clip(knuckle, 1, 0.25, 9), tone(fill, -1)),
            (clip(knuckle, 1, -9, -0.35), tone(fill, 1)),
        ], ink),
        P(f"{p}_knuckle_cut_a", poly(rr(0.22, 1.5, 0.1, (-0.75, 0), 1)), "$ink@0.55"),
        P(f"{p}_knuckle_cut_b", poly(rr(0.22, 1.5, 0.1, (0.75, 0), 1)), "$ink@0.55"),
        P(f"{p}_pin", poly(_oval(-2.35, 0, 0.3, 0.5, 10)), tone(fill, 1), stroke=ink),
    ]
    # The staple: the front bend of a loop standing out of the box through the slot, lit on top.
    st = rr(1.0, 1.5, 0.5, (0, sy - 0.2), 3)
    staple_parts = [
        P(f"{p}_staple_shadow", poly([(px + 0.5, py + 0.4) for px, py in st]), "$ink@0.45"),
        *_mass(f"{p}_staple", st, staple, [
            (clip(st, 0, 0.1, 9), tone(staple, -1)),
            (clip(st, 1, -99, sy - 0.55), tone(staple, 2)),
        ], ink),
    ]
    if locked:
        # The padlock hangs from the bottom of the staple's eye, its crown through it.
        parts += padlock(f"{p}_lock", 0, sy + 0.35, lock_s) + staple_parts
    else:
        parts += staple_parts
    return placed(parts, (x, y), s, rot)


def _screw(id, x, y, r, s=1.0):
    """A screw head: the dark disc, its slot, a catch of light up and left."""
    return [
        P(id, poly(_oval(x, y, r, r, 12)), "$slate.dark", stroke=_ink(s, 0.5)),
        P(f"{id}_slot", poly(_turn(rr(r * 1.7, r * 0.42, r * 0.2, (0, 0), 1), -35, (x, y))), "$ink@0.6"),
        P(f"{id}_lit", poly(_oval(x - r * 0.35, y - r * 0.4, r * 0.32, r * 0.25, 8)), "$white@0.5"),
    ]


# ================================================================ hinge

def hinge(prefix, x, y, s=1.0, rot=0.0, vertical=False, length=4.4, leaf=2.0, fill="$steel", screws=True):
    """A small barrel hinge, origin on its pin: two leaves (`leaf` deep; 0 for the knuckle alone) with two
    screws each, and the knuckle between them in three turns with the pin's ends showing. Lying along x
    (a lid's) by default, along y if `vertical` (a door's); the light stays upper left either way.
    Natural, lying: (length + 1.1) x (2 * leaf + 1.2), 5.5 x 5.2 by default (x -2.75..2.75, y -2.6..2.6);
    with leaf=0, 5.5 x 1.6."""
    ink = _ink(s)
    p = prefix
    T = (lambda pts: [(v, u) for u, v in pts]) if vertical else (lambda pts: pts)
    tx = (lambda u, v: (v, u)) if vertical else (lambda u, v: (u, v))
    axis_across = 0 if vertical else 1   # the axis running across the knuckle
    parts = []
    kr = 0.8
    if leaf > 0:
        for side, sg in (("a", -1), ("b", 1)):
            lp = T(rr(length - 0.4, leaf, 0.35, (0, sg * (kr - 0.2 + leaf / 2)), 2))
            # A flat plate: its far edge (the top one's) catches the light, the bottom one's lies in shade.
            edge = sg * (kr - 0.2 + leaf)
            if sg < 0:
                bands = [(clip(lp, axis_across, edge - 1, edge + 0.4), tone(fill, 1))]
            else:
                bands = [(clip(lp, axis_across, edge - 0.4, edge + 1), tone(fill, -1))]
            parts += _mass(f"{p}_leaf_{side}", lp, fill, bands, ink)
            if screws:
                for i, u in enumerate((-length * 0.27, length * 0.27)):
                    sx, sy = tx(u, sg * (kr - 0.2 + leaf * 0.55))
                    parts += _screw(f"{p}_leaf_{side}_sc{i}", sx, sy, min(0.42, leaf * 0.24), s)
        # The knuckle's shadow on the lower (or right-hand) leaf.
        parts.append(P(f"{p}_ao", poly(T(rr(length - 0.6, 0.6, 0.3, (0.2, kr + 0.1), 1))), "$ink@0.35"))
    kn = T(rr(length, 2 * kr, kr * 0.9, (0, 0), 3))
    parts += _mass(f"{p}_knuckle", kn, fill, [
        (clip(kn, axis_across, 0.3, 9), tone(fill, -1)),
        (clip(kn, axis_across, -9, -0.42), tone(fill, 1)),
    ], ink)
    parts += [P(f"{p}_cut_{i}", poly(T(rr(0.22, 2 * kr - 0.1, 0.1, (u, 0), 1))), "$ink@0.55") for i, u in enumerate((-length / 6, length / 6))]
    # The pin's two ends, proud of the knuckle.
    for i, sg in enumerate((-1, 1)):
        parts.append(P(f"{p}_pin_{i}", poly(T(rr(0.6, 1.0, 0.28, (sg * (length / 2 + 0.25), 0), 2))), tone(fill, 1) if sg < 0 else fill, stroke=ink))
    parts.append(P(f"{p}_shine", poly(T(rr(length - 1.2, 0.3, 0.15, (-0.2, -0.32), 1))), "$white@0.55"))
    return placed(parts, (x, y), s, rot)


# ================================================================ clamp

def clamp(prefix, x, y, s=1.0, rot=0.0, side="l", grip=8.6, fill="$steel.dark", nut="$steel"):
    """The vat lid's clamp: a steel strap bent into a C round the lid's edge and the vat's rim under it, a
    screw down through its top arm onto the lid, a wing nut on the screw. Origin at the lid's top outer
    corner; `side` "l" sits on the lid's left edge (the lid off to the right), "r" on its right. `grip` is
    how far below the lid's top the lower arm hooks under (the lid and the rim together). Natural, l:
    x -1.7..4.55, y -4.45..grip + 1.2 (6.25 x 14.25 at the default grip); "r" mirrors x."""
    ink = _ink(s)
    p = prefix
    m = 1 if side == "l" else -1
    W = lambda pts: _mirror(pts, m)
    hx = 2.1                             # the screw's line
    c = W([(3.4, -2.3), (3.4, -1.1), (-0.3, -1.1), (-0.3, grip), (2.2, grip), (2.2, grip + 1.2),
           (-0.9, grip + 1.2), (-1.5, grip + 0.95), (-1.7, grip + 0.5), (-1.7, -1.6), (-1.5, -2.05), (-1.0, -2.3)])
    spine_out = clip(c, 0, -99, -1.1) if m > 0 else clip(c, 0, 1.1, 99)
    parts = [
        # Its shadow: in the gap under the top arm, and (on the left) down the lid's face beside the spine.
        P(f"{p}_ao", poly(W(rr(3.6, 1.1, 0.3, (1.5, -0.55), 1))), "$ink@0.4"),
    ]
    if m > 0:
        parts.append(P(f"{p}_ao_face", poly(rr(0.9, grip - 0.4, 0.4, (0.15, grip / 2), 1)), "$ink@0.3"))
    parts += _mass(f"{p}_strap", c, fill, [
        (clip(c, 1, grip - 0.1, 99), tone(fill, -1)),
        (spine_out, tone(fill, 1) if m > 0 else tone(fill, -1)),
        (clip(c, 1, -99, -1.95), tone(fill, 1)),
    ], ink)
    # The screw, its foot on the lid.
    parts += [
        P(f"{p}_screw", poly(W(rr(0.8, 3.6, 0.2, (hx, -1.9), 1))), "$steel", stroke=ink),
        P(f"{p}_thread", poly(W([(hx - 0.4, -0.85), (hx + 0.4, -0.65), (hx + 0.4, -0.45), (hx - 0.4, -0.65)])), "$ink@0.45"),
        P(f"{p}_foot", poly(W(rr(1.9, 0.55, 0.2, (hx, -0.28), 1))), "$steel.dark", stroke=ink),
    ]
    # The wing nut: a squat nut on the screw with a thin wing flaring up each side, the near (left) one lit.
    hy = -2.85
    wing = [(-0.45, 0.4), (-1.0, 0.25), (-1.9, -0.35), (-2.45, -1.2), (-2.35, -1.6), (-1.95, -1.55), (-1.15, -0.85), (-0.45, -0.45)]
    lw = [(hx + u, hy + v) for u, v in wing]
    rw = [(hx - u, hy + v) for u, v in wing]
    if m < 0:
        lw, rw = [(-x_, y_) for x_, y_ in rw], [(-x_, y_) for x_, y_ in lw]
    nut_pts = W([(hx - 0.85, hy + 0.55), (hx + 0.85, hy + 0.55), (hx + 0.6, hy - 0.55), (hx - 0.6, hy - 0.55)])
    parts += [
        P(f"{p}_tip", poly(W(rr(0.5, 0.9, 0.2, (hx, hy - 0.7), 1))), "$steel.dark", stroke=_ink(s, 0.5)),
        P(f"{p}_wing_a", poly(lw), tone(nut, 1), stroke=ink),
        P(f"{p}_wing_b", poly(rw), tone(nut, -1), stroke=ink),
        P(f"{p}_nut", poly(nut_pts), nut, stroke=ink),
        P(f"{p}_nut_v0", poly(clip(nut_pts, 0, -99, min(x_ for x_, _ in nut_pts) + 0.5)), tone(nut, 1)),
        P(f"{p}_nut_v1", poly(clip(nut_pts, 0, max(x_ for x_, _ in nut_pts) - 0.5, 99)), tone(nut, -1)),
    ]
    return placed(parts, (x, y), s, rot)


# ================================================================ hook

def hook(prefix, x, y, s=1.0, rot=0.0, mount="wall", side="l", fill="$steel.dark", reach=4.0):
    """A steel hook, origin where the hung thing's loop rests.
    mount="wall": in profile off a wall, the way it shows on the tank's side — a plate against the wall
    (its face at x = reach + 0.8), two rivet heads, an arm `reach` long, the end turned up. "l" sticks out
    to the left of a wall on its right, "r" the other way. Natural (l): x -2.15..reach + 0.8, y -3.2..2.8
    (7 x 6 at reach 4).
    mount="screw": a cup hook screwed up into a beam or an arm (its collar at y = -reach), hanging down and
    turned up into a J. Natural: x -2.65..1.85, y -reach - 0.45..1.0 (4.5 x 5.5 at reach 4)."""
    ink = _ink(s)
    p = prefix
    w = 1.0
    parts = []
    if mount == "wall":
        m = 1 if side == "l" else -1
        ri, tip = 1.0, 1.7
        cy = -ri
        pts = [(reach + 0.2, -0.1), (0.0, 0.0)]
        pts += _arc(0, cy, ri, ri, 90, 180, 7)[1:]
        pts += [(-ri, cy - tip)]
        pts += _arc(-ri - w / 2, cy - tip, w / 2, w / 2, 0, -180, 6)[1:-1]
        pts += [(-ri - w - 0.15, cy - tip), (-ri - w, cy)]
        pts += _arc(0, cy, ri + w, ri + w, 180, 90, 9)[1:]
        pts += [(reach + 0.2, w + 0.1)]
        pts = _mirror(pts, m)
        plate = _mirror(rr(0.8, 4.6, 0.3, (reach + 0.4, w / 2), 2), m)
        parts += _mass(f"{p}", pts, fill, [
            (clip(pts, 1, w * 0.55, 99), tone(fill, -1)),
        ], ink)
        # Light along the top of the arm and up the outside of the tip.
        shine = [(reach - 0.3, 0.22), (0.1, 0.25)] + _arc(0, cy, ri + 0.3, ri + 0.3, 90, 170, 4)[1:] + [(-ri - 0.3, cy - tip + 0.3)]
        if m < 0:
            shine = [(reach - 0.3, 0.22), (0.1, 0.25)]
        parts.append(band(f"{p}_lit", _mirror(shine, m), 0.28, "$white@0.5"))
        parts += _mass(f"{p}_plate", plate, "$slate", [(clip(plate, 1, w / 2 + 1.2, 99), "$slate.dark")], ink)
        # The rivet heads stand off the plate's outer face, above and below the arm.
        parts += [P(f"{p}_rivet_{i}", poly(_oval(m * (reach - 0.12), yy, 0.32, 0.42, 10)), "$slate.light", stroke=_ink(s, 0.5)) for i, yy in enumerate((-1.25, w + 1.25))]
    else:
        ri, tip = 0.85, 1.6
        cy = -ri
        shank_top = -reach
        pts = [(-ri - w, shank_top), (-ri - w, cy)]
        pts += _arc(0, cy, ri + w, ri + w, 180, 0, 12)[1:-1]
        pts += [(ri + w, cy), (ri + w, cy - tip)]
        pts += _arc(ri + w / 2, cy - tip, w / 2, w / 2, 0, -180, 6)[1:-1]
        pts += [(ri, cy - tip), (ri, cy)]
        pts += _arc(0, cy, ri, ri, 0, 180, 10)[1:-1]
        pts += [(-ri, cy), (-ri, shank_top)]
        parts += _mass(f"{p}", pts, fill, [
            (clip(pts, 0, 0.2, 99), tone(fill, -1)),
        ], ink)
        parts.append(band(f"{p}_lit", [(-ri - w + 0.3, shank_top + 0.6), (-ri - w + 0.3, cy)] + _arc(0, cy, ri + w - 0.3, ri + w - 0.3, 180, 120, 3)[1:], 0.3, "$white@0.5"))
        # The collar where it screws in.
        parts += [P(f"{p}_collar", poly(_oval(-ri - w / 2, shank_top, 1.3, 0.45, 14)), "$steel", stroke=ink)]
    return placed(parts, (x, y), s, rot)


# ================================================================ wire coil

def wire_coil(prefix, x, y, s=1.0, rot=0.0, fill="$steel", loops=4, tail=True, ties="$bone.dark"):
    """A coil of wire lying on a surface, seen 3/4 from above, origin at the middle of its bottom loop on
    that surface: `loops` turns lying a little out of true on each other, each lit along its top, the
    shadow under it showing through the middle, two ties round the bundle (`ties` a colour, or None) and
    the loose end off the front, over the edge it lies by (`tail` True, False, or a list of points).
    Natural 9.4 x 5.9 for the coil (x -4.9..4.5, y -3.4..2.45 at 4 loops; its shadow reaches x 5.0); the
    default tail runs out to (7.4, 5.3). Ids: <prefix>_<i> for each turn from the bottom (with _ink, _v0,
    _v1, _shine), <prefix>_tail (_ink, _lit, _end), <prefix>_tie_0/1, <prefix>_shadow."""
    p = prefix
    w = 0.85
    rx, ry = 3.4, 1.6
    offs = [(0.0, 0.0), (0.55, -0.4), (-0.45, -0.75), (0.3, -1.1), (-0.2, -1.4), (0.4, -1.7)]
    jit = (0.15, -0.2, 0.25, -0.1, 0.05, -0.15)
    parts = [P(f"{p}_shadow", poly(_oval(0.6, 0.6, rx + 1.0, ry + 0.75, 24)), "$ink@0.4")]
    for i in range(loops):
        cx, cy = offs[i % len(offs)]
        jr = jit[i % len(jit)]
        a0 = 90 + 25 * i  # where the ring's seam goes
        ov = lambda d: _oval(cx, cy, rx + jr + d, ry + jr * 0.5 + d, 36, a0)
        parts += _ring(f"{p}_{i}", ov(w / 2), ov(-w / 2), ov(w / 2 + 0.35), ov(-w / 2 - 0.2), fill, [
            (lambda r: _cut(r, (0, 1), ry * 0.55, 99, (cx, cy)), tone(fill, -1)),
            (lambda r: _cut(r, (0, 1), -99, -ry * 0.5, (cx, cy)), tone(fill, 1)),
        ])
        # The catch of light along the top of the wire, back left.
        parts.append(P(f"{p}_{i}_shine", poly(_arc(cx, cy - 0.1, rx + jr + 0.05, ry + jr * 0.5 + 0.05, 200, 258, 6) + _arc(cx, cy - 0.1, rx + jr - 0.2, ry + jr * 0.5 - 0.2, 258, 200, 6)), "$white@0.5"))
    tx, ty = offs[(loops - 1) % len(offs)]
    tj = jit[(loops - 1) % len(jit)]
    if tail:
        # The loose end, off the top turn's front right and away.
        a = math.radians(35)
        sx, sy = tx + (rx + tj) * math.cos(a), ty + (ry + tj * 0.5) * math.sin(a)
        tp = tail if isinstance(tail, list) else [(sx, sy), (sx + 1.4, sy + 0.45), (5.8, 1.9), (6.7, 3.1), (7.0, 5.0)]
        parts.append(band(f"{p}_tail_ink", tp, w + 0.75, "$ink"))
        parts.append(band(f"{p}_tail", tp, w, fill))
        parts.append(band(f"{p}_tail_lit", [(px - 0.12, py - 0.2) for px, py in tp[1:-1]], 0.26, "$white@0.45"))
        ex, ey = tp[-1]
        parts.append(P(f"{p}_tail_end", poly(_oval(ex, ey, w / 2 - 0.05, 0.3, 8)), tone(fill, 1)))
    if ties:
        # Two short ties round the bundle, front left and back right, across the wire.
        mx = sum(offs[i % len(offs)][0] for i in range(loops)) / loops
        my = sum(offs[i % len(offs)][1] for i in range(loops)) / loops
        for i, ang in enumerate((160, 330)):
            a = math.radians(ang)
            px, py = mx + rx * math.cos(a), my + ry * math.sin(a)
            along = math.degrees(math.atan2(ry * math.sin(a), rx * math.cos(a)))  # across the bundle, out from its middle
            spread = 1.0 + 0.25 * loops
            parts.append(P(f"{p}_tie_{i}", poly(_turn(rr(spread + 0.5, 0.6, 0.25, (0, 0), 1), along, (px, py - 0.25))), ties, stroke=_ink(s, 0.5)))
    return placed(parts, (x, y), s, rot)


# ================================================================ motion

def swing_tracks(parts, deg=5.0, phase=0.0):
    """`rot` tracks that swing every part in `parts` (a padlock, or a hasp's <prefix>_lock_* parts) to and fro
    by `deg` about the point it hangs from: all of a padlock's parts are placed at that point, and a rot
    track turns a part about its own `at`. Put them in a loop() of 1.6-2.4 s."""
    a, b = (deg, -deg) if phase < 0.5 else (-deg, deg)
    return [track(p["id"], "rot", [(0, 0), (0.25, a), (0.75, b), (1, 0)]) for p in parts]
