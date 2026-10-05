"""Drawing helpers for the hand-built documents: the camp's (`base.py`) and the small things in it (`bits_*.py`).

    from draw import *

Flat, not graded: the Phaser adapter draws a gradient as its middle stop, so
a value change is a band clipped out of the mass (`shaded`), and a glow is a
few rings stacked thin (`halo`). Every helper returns parts (or a list of
them) with ids built from the prefix it is given, so a document can hold many
of the same thing.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import r2, poly, ell, circ, rect  # noqa: E402,F401

INK_THIN = {"color": "$ink", "width": "thin"}
INK_HAIR = {"color": "$ink", "width": "hair"}
# For the small things — a padlock, a vial, a buckle — where a whole unit of
# ink would eat the thing it outlines.
INK_FINE = {"color": "$ink", "width": 0.6}


def P(id, shape, fill, at=(0, 0), stroke=None, opacity=None, rot=None, scale=None):
    p = {"id": id}
    if at != (0, 0):
        p["at"] = [r2(at[0]), r2(at[1])]
    if rot:
        p["rot"] = r2(rot)
    if scale is not None:
        p["scale"] = scale
    if opacity is not None:
        p["opacity"] = opacity
    p["shape"] = shape
    if fill is not None:
        p["fill"] = fill
    if stroke:
        p["stroke"] = stroke
    return p


def R(w, h, c=1.0):
    return rect(w, h, c)


# ---------------------------------------------------------------- flat shading

def clip(pts, axis, lo, hi):
    """The part of polygon `pts` with lo <= coordinate <= hi on `axis` (0 is x, 1 is y)."""
    def edge(pts, inside, at):
        out = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur, at))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur, at))
        return out

    def cross(p, q, v):
        t = (v - p[axis]) / (q[axis] - p[axis])
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    pts = edge(pts, lambda p: p[axis] >= lo, lo)
    return edge(pts, lambda p: p[axis] <= hi, hi) if pts else pts


def rr(w, h, c, at=(0, 0), n=4):
    """A rounded rectangle as points, centred on `at`, so it can be cut into bands."""
    x0, y0 = at
    hw, hh = w / 2, h / 2
    c = min(c, hw, hh)
    pts = []
    for cx, cy, a0 in [(hw - c, -hh + c, -90), (hw - c, hh - c, 0), (-hw + c, hh - c, 90), (-hw + c, -hh + c, 180)]:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((x0 + cx + c * math.cos(a), y0 + cy + c * math.sin(a)))
    return pts


def shaded(id, pts, base, cuts, stroke=INK_THIN, axis=1):
    """A mass in flat values: `base` over all of it, each (lo, hi, fill) of `cuts` over that band of it, then its ink line."""
    out = [P(id, poly(pts), base)]
    for i, (lo, hi, fill) in enumerate(cuts):
        c = clip(pts, axis, lo, hi)
        if len(c) >= 3:
            out.append(P(f"{id}_v{i}", poly(c), fill))
    if stroke:
        out.append(P(f"{id}_rim", poly(pts), None, stroke=stroke))
    return out


def moved(pts, at):
    return [(x + at[0], y + at[1]) for x, y in pts]


def halo(id, x, y, rx, ry, a=0.4, token="$spore", n=10):
    """Light on the ground or in the air round a cap: `n` rings stacked thin, densest at the middle."""
    return [P(id if i == 0 else f"{id}_{i}", ell(rx * (1 - i / n), ry * (1 - i / n)), f"{token}@{r2(a / n)}", at=(x, y)) for i in range(n)]


def halo_ids(id, n=10):
    return [id] + [f"{id}_{i}" for i in range(1, n)]


def shadow(id, x, y, rx, ry, a="0.45"):
    return P(id, ell(rx, ry), f"$ink@{a}", at=(x, y))


def band(id, pts, width, fill, opacity=None):
    """A line of `width` through `pts`, as a polygon: a cord, a crack, a seam."""
    top, bot = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n * width / 2, dx / n * width / 2
        top.append((x + nx, y + ny))
        bot.append((x - nx, y - ny))
    return P(id, poly(top + bot[::-1]), fill, opacity=opacity)


def bud(prefix, x, y, s=1.0, lean=0.0):
    """A pheromone crystal pushing out of a joint (A055): two shards, pink, small."""
    k = s
    return [
        P(f"{prefix}_a", poly([(-2.2 * k, 0), (-0.6 * k + lean, -7 * k), (1.4 * k, 0)]), "$pheromone", at=(x, y), stroke=INK_HAIR),
        P(f"{prefix}_b", poly([(0.6 * k, 0), (3.2 * k + lean, -4.6 * k), (4.2 * k, 0)]), "$pheromone.dark", at=(x, y), stroke=INK_HAIR),
        P(f"{prefix}_lit", poly([(-1.4 * k, -0.6 * k), (-0.7 * k + lean, -5.6 * k), (-0.2 * k, -0.6 * k)]), "$pink.light", at=(x, y)),
    ]


def cap(prefix, x, y, r):
    """One glowing cap: a pale stem, a teal head with its shade under and its light on top."""
    return [
        P(f"{prefix}_stem", R(r * 0.55, r * 1.1, r * 0.25), "$husk.dark", at=(x, y + r * 0.55), stroke=INK_HAIR),
        P(f"{prefix}_head", ell(r, r * 0.62), "$spore", at=(x, y), stroke=INK_HAIR),
        P(f"{prefix}_under", ell(r * 0.92, r * 0.26), "$spore.dark", at=(x, y + r * 0.34)),
        P(f"{prefix}_lit", ell(r * 0.42, r * 0.2), "$spore.light2", at=(x - r * 0.32, y - r * 0.22)),
    ]


def rust(id, x, y, w, h, a=0.65):
    """Rust run down from a seam or a rivet: dense where it starts, thin where it gives out."""
    pts = moved([(-w / 2, 0), (w / 2, 0), (w * 0.7, h * 0.6), (0, h), (-w * 0.7, h * 0.55)], (x, y))
    return shaded(id, pts, f"$rust@{a}", [(y + h * 0.55, y + h + 1, f"$rust@{r2(a * 0.45)}")], stroke=None)


def loop(description, duration, tracks):
    return {"description": description, "duration": duration, "tracks": tracks}


def track(part, prop, keys):
    return {"part": part, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in keys]}


def glow_tracks(id, lo, hi, n=10, phase=0.0):
    """A stacked halo brightening and dimming: every ring's opacity, together."""
    a, b = (lo, hi) if phase < 0.5 else (hi, lo)
    return [track(r, "opacity", [(0, a), (0.5, b), (1, a)]) for r in halo_ids(id, n)]


def rising(part, phase, rise):
    """A mote going up `rise` over the loop and starting again at the bottom, `phase` of the way through at t=0."""
    if phase <= 0:
        return [track(part, "y", [(0, 0), (1, -rise)]), track(part, "opacity", [(0, 1), (0.7, 0.6), (1, 0)])]
    cut = 1 - phase
    return [
        track(part, "y", [(0, -rise * phase), (cut, -rise), (cut + 0.01, 0), (1, -rise * phase)]),
        track(part, "opacity", [(0, 1 - phase), (cut, 0), (cut + 0.01, 1), (1, 1 - phase)]),
    ]


def tally(prefix, x0, y, groups, last=0, h=11.0):
    """Strokes cut in fives — four down and one across — the way a count is kept on a wall."""
    parts = []
    x = x0
    for g in range(groups):
        for i in range(4):
            parts.append(P(f"{prefix}_{g}_{i}", R(1.3, h - (i % 2), 0.4), "$bone.dark@0.85", at=(x + i * 3, y + (i % 2) * 0.5), rot=(i % 3) - 1))
        parts.append(P(f"{prefix}_{g}_x", R(15, 1.3, 0.4), "$bone.dark@0.85", at=(x + 4.5, y), rot=-24))
        x += 17
    for i in range(last):
        parts.append(P(f"{prefix}_end_{i}", R(1.3, h, 0.4), "$bone.dark@0.85", at=(x + i * 3, y)))
    return parts


# ---------------------------------------------------------------- detail
# The prop pass (feelers docs/staging-method.md §9): every mass gets one lit
# edge where the light from the upper left catches it, a dark seam where it
# meets the ground or the thing on it, and its small things — bolts, rivets,
# scratches — gathered on a third of it, not spread over all of it.

def lit_edge(id, x0, x1, y, w=1.0, fill="$white@0.35"):
    """A highlight along a top edge, from x0 to x1 at y."""
    return P(id, R(abs(x1 - x0), w, w / 2), fill, at=((x0 + x1) / 2, y))


def ao(id, x, y, w, h=1.6, a=0.35):
    """The dark where one thing rests on another."""
    return P(id, R(w, h, h / 2), f"$ink@{a}", at=(x, y))


def bolt(id, x, y, r=1.3, fill="$slate"):
    """A bolt head: the disc, and the catch of light on its upper left."""
    return [
        P(id, circ(r), fill, at=(x, y), stroke=INK_HAIR),
        P(f"{id}_lit", circ(r * 0.42), "$white@0.55", at=(x - r * 0.32, y - r * 0.32)),
    ]


def rivet_row(prefix, x0, y0, x1, y1, n, r=0.8, fill="$slate.dark@0.75", skip=None):
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        if skip and skip(x, y):
            continue
        out.append(P(f"{prefix}_{i}", circ(r), fill, at=(x, y)))
    return out


def scratches(prefix, x, y, w, h, n, fill="$steel.light@0.55", seed=7):
    """Short scuffs in a box, placed by a fixed little generator so the drawing never changes under you."""
    out, s = [], seed
    for i in range(n):
        s = (s * 1103515245 + 12345) % 2147483648
        u = s / 2147483648
        s = (s * 1103515245 + 12345) % 2147483648
        v = s / 2147483648
        s = (s * 1103515245 + 12345) % 2147483648
        a = (s / 2147483648 - 0.5) * 50
        out.append(P(f"{prefix}_{i}", R(2.4 + 3 * u, 0.6, 0.3), fill, at=(x + (u - 0.5) * w, y + (v - 0.5) * h), rot=a))
    return out


def ring_arc(r, width, a, b):
    return {"kind": "ring", "r": r2(r), "width": r2(width), "from": a, "to": b}


def placed(parts, at=(0, 0), s=1.0, rot=0.0):
    """A small thing drawn about its own origin, set down at `at`, `s` times its size and turned `rot` degrees as one piece."""
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for p in parts:
        q = dict(p)
        x, y = p.get("at", (0, 0))
        x, y = x * s, y * s
        q["at"] = [r2(at[0] + x * ca - y * sa), r2(at[1] + x * sa + y * ca)]
        if q["at"] == [0, 0]:
            del q["at"]
        if rot or p.get("rot"):
            q["rot"] = r2(p.get("rot", 0) + rot)
        if s != 1:
            k = p.get("scale", 1)
            q["scale"] = [r2(k[0] * s), r2(k[1] * s)] if isinstance(k, (list, tuple)) else r2(k * s)
        out.append(q)
    return out

