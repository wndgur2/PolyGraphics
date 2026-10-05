"""The base: the camp by the lander that every expedition set out from.

    python3 scripts/base.py

Writes every `ss.base.*` document. feelers draws the out-of-run screens as
this place (its docs/hub-map-plan.md): the chosen writer walks the camp and
walks up to things — the shelf of paper is the collection, the jelly vat is
EVOLUTION, the field bench is BUILD, the edges lead out to the grounds.

The camp is what the records draw, and only that:

  the lander     the settlers' hull, which will not fly again (X001), half
                 sunk in its own drift, with the scratches on its skin and
                 the plate that says "do not come" (T041)
  the frame      Arin's frame with a canvas over it, put up on the first day,
                 and its tank (A001). Under the canvas is where the camp
                 sleeps between expeditions
  the shelf      the seven boxes of paper (A055)
  the line       pages pegged out on a cord, the ones not filed yet
  the bench      the instrument's own table: the vials and the syringe the
                 level-up draws from
  the vat        the jelly the expedition trades in — gold is jelly's (D14)
  the hearth     a ring of stones with glowing caps in it, where a camp
                 elsewhere would keep a fire. An expedition does not glow and
                 lights nothing (guide §7.2): the only light in the camp is
                 the hive's, borrowed — the cap Sol carried in a dead emitter,
                 planted and spread. The same caps go in jars for lamps
  the lockers    one per writer, with the one thing their log kept
  the marks      the cut spires to the south, ringed inside like trees
                 (T010, A030); a salt cairn on the north-west road; the board
                 the routes are pinned on; boot prints worn out along them

Colour follows ownership (guide §7): what the expedition brought is cold —
steel, slate, frost — on warm ground; paper is bone; jelly is gold; the
fungus is the world's teal; pink is the hive's signal, and appears only as
the crystal buds the frame and the hull grow (A055), a few, because pink is
spent sparingly. Drawn the way the field's props are: a dark ink line round
each mass, two or three flat values, one light, a soft shadow on the ground.

Flat, not graded: the Phaser adapter draws a gradient as its middle stop, so
a value change is a band clipped out of the mass (`shaded`), and a glow is a
few rings stacked thin (`halo`). The game lays its own light over the jars
and the hearth; the rings are what the drawing carries on its own.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import r2, poly, ell, circ, rect, write_doc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "apps", "ss", "assets")

INK_THIN = {"color": "$ink", "width": "thin"}
INK_HAIR = {"color": "$ink", "width": "hair"}


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


def halo(id, x, y, rx, ry, a=0.4, token="$spore", n=6):
    """Light on the ground or in the air round a cap: `n` rings stacked thin, densest at the middle."""
    return [P(id if i == 0 else f"{id}_{i}", ell(rx * (1 - i / n), ry * (1 - i / n)), f"{token}@{r2(a / n)}", at=(x, y)) for i in range(n)]


def halo_ids(id, n=6):
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


def doc(id, name, description, size, parts, animations=None, tags=None):
    ids = [p["id"] for p in parts]
    assert len(ids) == len(set(ids)), f"{id}: duplicate part ids {[i for i in ids if ids.count(i) > 1]}"
    d = {
        "id": id,
        "name": name,
        "description": description,
        "tags": tags or ["base"],
        "size": list(size),
        "parts": parts,
        "animations": animations or {},
    }
    write_doc(d, os.path.join(OUT, id.replace(".", "-") + ".json"))
    return d


def loop(description, duration, tracks):
    return {"description": description, "duration": duration, "tracks": tracks}


def track(part, prop, keys):
    return {"part": part, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in keys]}


def glow_tracks(id, lo, hi, n=6, phase=0.0):
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


# ============================================================== the lander
def lander():
    hull = [
        (-128, -46), (100, -46),
        (122, -42), (140, -32), (152, -16), (156, 0), (152, 16), (140, 30), (122, 40), (100, 44),
        (-128, 44), (-134, 32), (-137, 0), (-134, -32),
    ]
    bell = [(-120, -12), (-148, -22), (-160, -18), (-160, 18), (-148, 24), (-120, 12)]
    drift_top = [(-172, 60), (-160, 46), (-140, 38), (-116, 43), (-86, 39), (-56, 45), (-24, 43), (6, 47), (36, 41), (70, 44), (104, 40), (132, 45), (158, 43), (172, 58)]
    drift_foot = [(172, 62), (140, 67), (100, 63), (60, 69), (20, 65), (-20, 69), (-60, 64), (-100, 68), (-140, 63), (-172, 66)]
    ramp = [(-62, 38), (-22, 38), (-16, 58), (-68, 58)]
    parts = [
        shadow("shadow", 0, 52, 168, 20, "0.42"),
        # The engines, dead, behind the hull: two bells flaring west, soot at the mouths.
        *shaded("bell_top", moved(bell, (0, -22)), "$smoke.dark", [(-161, -142, "$coal")], axis=0),
        P("bell_top_mouth", ell(4.5, 18), "$coal.dark", at=(-157, -22), stroke=INK_HAIR),
        P("bell_top_lit", R(2, 26, 1), "$steel@0.45", at=(-150, -22)),
        *shaded("bell_low", moved(bell, (0, 14)), "$smoke.dark", [(-161, -142, "$coal")], axis=0),
        P("bell_low_mouth", ell(4.5, 18), "$coal.dark", at=(-157, 14), stroke=INK_HAIR),
        # The hull: a drum on its side, lit from above, its belly in shadow.
        *shaded("hull", hull, "$smoke", [(-47, -29, "$steel"), (-29, -22, "$steel.dark"), (18, 45, "$smoke.dark")], stroke=None),
        P("crown_lit", R(196, 5, 2.5), "$steel.light", at=(-22, -40)),
        P("specular", R(120, 2, 1), "$white@0.4", at=(-34, -42)),
        *shaded("collar", rr(12, 92, 3, (-121, -1)), "$slate", [(-48, -30, "$slate.light"), (18, 46, "$slate.dark")], stroke=INK_HAIR),
        *[P(f"collar_rivet_{i}", circ(1.3), "$slate.dark2", at=(-121, y)) for i, y in enumerate([-36, -18, 0, 18, 36])],
        # Panel seams, and the rust the ground has drawn down each one.
        *[P(f"seam_{i}", R(1.6, 86, 0.6), "$ink@0.35", at=(x, -1)) for i, x in enumerate([-84, -6, 58])],
        P("seam_low", R(236, 1.4, 0.6), "$ink@0.25", at=(-12, 10)),
        *rust("rust_a", -84, -6, 5, 40),
        *rust("rust_b", 58, -2, 4.6, 34),
        *rust("rust_c", 72, -6, 3.6, 22, 0.55),
        # Soot up the belly from the engines.
        P("scorch", poly([(-128, 4), (-80, 16), (-36, 30), (4, 44), (-128, 44)]), "$coal@0.35"),
        P("scorch_deep", poly([(-128, 16), (-96, 24), (-66, 36), (-50, 44), (-128, 44)]), "$coal@0.35"),
        # The settlers' stripe round the nose: cold, like everything people brought.
        P("stripe", R(9, 84, 1), "$frost.dark@0.7", at=(106, -1)),
        P("stripe_lit", R(9, 12, 1), "$frost@0.5", at=(106, -38)),
        # The port, dead: no light behind it.
        P("port_rim", circ(11), "$slate", at=(130, -8), stroke=INK_THIN),
        P("port", circ(7.5), "$coal", at=(130, -8)),
        P("port_glint", ell(3, 1.6), "$frost@0.45", at=(127, -11), rot=-30),
        # The hatch, open. Somebody keeps a jar of caps inside: the hull's
        # dark has a little teal in the bottom of it.
        *shaded("hatch_frame", rr(54, 66, 12, (-42, 6)), "$slate", [(-28, -16, "$slate.light"), (26, 40, "$slate.dark")]),
        P("hatch_dark", R(44, 56, 9), "$coal", at=(-42, 8)),
        *halo("hatch_glow", -42, 27, 20, 11, 0.6),
        P("hatch_sill", R(46, 6, 2), "$smoke.dark", at=(-42, 35), stroke=INK_HAIR),
        P("door", poly([(0, -28), (14, -32), (17, 24), (0, 32)]), "$steel.dark", at=(-14, 6), stroke=INK_THIN),
        P("door_lit", poly([(2, -24), (6, -25), (7, 20), (2, 23)]), "$steel@0.85", at=(-14, 6)),
        P("door_bolt", circ(1.8), "$slate.dark", at=(-6, 2)),
        # What the settlers scratched into the skin (X001): a count, in fives.
        *tally("tally", 4, -16, 3, 2),
        *tally("tally_b", 4, 2, 2, 3, 9),
        # The plate (T041): riveted on, one line cut into it.
        *shaded("plate", rr(30, 18, 2, (84, -16)), "$steel.light", [(-11, -6, "$steel")]),
        P("plate_line", R(20, 1.6, 0.5), "$ink@0.65", at=(84, -16)),
        *[P(f"rivet_{i}", circ(1.3), "$slate", at=(84 + dx, -16 + dy)) for i, (dx, dy) in enumerate([(-12, -6), (12, -6), (-12, 6), (12, 6)])],
        # A stub of mast on the crown, snapped, its cable hanging.
        P("mast", R(4, 20, 1.5), "$steel.dark", at=(30, -55), stroke=INK_HAIR, rot=10),
        P("mast_cap", R(9, 3, 1), "$steel", at=(32, -65), rot=10),
        band("cable", [(33, -62), (38, -54), (42, -47), (44, -40)], 1.1, "$coal"),
        # Grit settled on top, and the hive starting on it: buds at the collar (A055).
        P("grit_a", ell(26, 2.6), "$sand@0.7", at=(-66, -45)),
        P("grit_b", ell(16, 2.2), "$sand@0.6", at=(44, -46)),
        *bud("bud_a", -112, -45, 1.1, 0.5),
        *bud("bud_b", -100, -46, 0.75, -0.3),
        # Its own drift: the hull is half in the ground, and the drift thins
        # out into the field at its foot.
        P("drift_skirt", poly(drift_top + [(p[0], p[1] + 5) for p in drift_foot]), "$sand@0.4"),
        P("drift", poly(drift_top + drift_foot), "$sand"),
        band("drift_lit", drift_top[1:-1], 2.2, "$sand.light@0.6"),
        # Things on the drift: the ramp out of the hatch, a leg that broke on
        # the way down, another folded under.
        *shaded("ramp", ramp, "$steel.dark", [(51, 59, "$slate.dark")]),
        *[P(f"tread_{i}", R(40 + i * 3, 1.2, 0.4), "$ink@0.4", at=(-42, 43 + i * 5)) for i in range(3)],
        P("strut", poly([(0, 0), (6, 0), (26, 22), (40, 24), (40, 30), (22, 30), (0, 6)]), "$slate", at=(112, 32), stroke=INK_THIN),
        P("strut_lit", poly([(1, 1), (4, 1), (22, 20), (19, 21)]), "$slate.light", at=(112, 32)),
        P("strut_foot", R(18, 5, 2), "$slate.dark", at=(148, 62), stroke=INK_HAIR),
        P("leg_folded", R(30, 5, 2), "$slate.dark", at=(-96, 47), rot=10, stroke=INK_HAIR),
    ]
    return doc(
        "ss.base.lander",
        "The lander",
        "The settlers' hull, lying where it came down in 2650 and would not fly again (X001: \"The lander will not fly again. We live here.\"). "
        "Every expedition since camped in its lee. A drum on its side, lit from above, with two dead engine bells flaring at one end and a "
        "rounded nose at the other, half sunk in the drift it has gathered. The hatch is open and a ramp runs down from it; somebody keeps a "
        "jar of caps in the hull, so its dark has a little teal in the bottom of it. There is a dead port, a leg that broke on the way down, "
        "a snapped mast with its cable hanging, and a cold stripe round the nose. Rust runs down the seams, which is the ground reaching up, "
        "and soot runs up the belly from the engines. Beside the hatch is the settlers' count, scratched into the skin in fives. Near the "
        "nose is the riveted plate with one line cut in it, the same word as the ruin's stones and Eden's iron (T041). Two pink buds are "
        "pushing out at the engine collar: the hive reclaiming the camp, the way the crystal grew on Arin's frame (A055).",
        (344, 160),
        parts,
    )


# ============================================================== the frame
def frame():
    pole = lambda id, x, y, h, fill: P(id, R(5, h, 1.5), fill, at=(x, y), stroke=INK_HAIR)
    sag = [(96, -14), (64, -8), (32, -5), (0, -4), (-32, -5), (-64, -8), (-96, -14)]
    parts = [
        shadow("shadow", 0, 56, 104, 14, "0.4"),
        # The floor under the canvas: a ground sheet with a cold border.
        P("mat", poly([(-80, 28), (78, 28), (90, 60), (-92, 60)]), "$slate.dark", stroke=INK_HAIR),
        P("mat_inner", poly([(-72, 31), (70, 31), (80, 56), (-82, 56)]), "$slate.dark2"),
        P("mat_stripe", poly([(-76, 33), (74, 33), (75, 35), (-77, 35)]), "$frost.dark@0.45"),
        # The back wall: canvas let down from the back bar to the ground.
        pole("pole_bl", -78, -6, 52, "$slate"),
        pole("pole_br", 78, -6, 52, "$slate"),
        *shaded("wall", [(-76, -32), (76, -32), (78, 28), (-78, 28)], "$slate", [(12, 29, "$slate.dark")], stroke=INK_HAIR),
        P("wall_fold_a", R(1.4, 56, 0.5), "$ink@0.25", at=(-26, -2)),
        P("wall_fold_b", R(1.4, 56, 0.5), "$ink@0.25", at=(30, -2)),
        # Pages pinned to the wall, and a cord between them.
        band("wall_cord", [(-62, 2), (-44, 5), (-26, 6), (-6, 5)], 0.9, "$bone.dark@0.8"),
        P("note_a", R(11, 14, 0.8), "$bone", at=(-54, 11), rot=-5, stroke=INK_HAIR),
        P("note_a_ln", R(7, 1, 0.3), "$slate.dark@0.6", at=(-54, 8), rot=-5),
        P("note_a_ln2", R(6, 1, 0.3), "$slate.dark@0.5", at=(-54, 11), rot=-5),
        P("note_b", R(10, 13, 0.8), "$husk", at=(-36, 12), rot=6, stroke=INK_HAIR),
        P("note_b_ln", R(6, 1, 0.3), "$slate.dark@0.5", at=(-36, 10), rot=6),
        P("note_c", R(12, 9, 0.8), "$bone", at=(-17, 11), rot=-2, stroke=INK_HAIR),
        P("note_c_ln", R(8, 1, 0.3), "$slate.dark@0.5", at=(-17, 10), rot=-2),
        # Where the camp sleeps: a bedroll laid out with a folded pillow, one
        # still rolled, a mug, a stack of pages to read by.
        *shaded("blanket", [(-6, 36), (56, 36), (62, 54), (-10, 54)], "$slate.light", [(48, 55, "$slate")], stroke=INK_HAIR),
        P("blanket_fold", poly([(30, 36), (56, 36), (60, 46), (38, 44)]), "$slate.light2@0.9", stroke=INK_HAIR),
        P("pillow", R(16, 8, 3), "$bone.dark", at=(2, 40), rot=-4, stroke=INK_HAIR),
        P("roll", R(34, 11, 5.5), "$slate.light", at=(-50, 44), stroke=INK_HAIR),
        P("roll_shade", R(30, 4, 2), "$slate", at=(-50, 47)),
        P("roll_end", ell(3.4, 5.5), "$slate", at=(-34, 44), stroke=INK_HAIR),
        P("roll_strap", R(2.2, 12, 0.6), "$steel.dark", at=(-54, 44)),
        P("mug", R(6, 7, 1.4), "$steel", at=(70, 46), stroke=INK_HAIR),
        P("mug_rim", ell(3, 1), "$coal", at=(70, 42.6)),
        P("stack", R(14, 5, 0.8), "$bone", at=(-74, 52), rot=-6, stroke=INK_HAIR),
        P("stack_top", R(12, 4, 0.8), "$husk", at=(-73, 49), rot=4, stroke=INK_HAIR),
        # The light in there, off the hung jar.
        *halo("inside_glow", 0, 22, 66, 30, 0.22),
        # The canvas, seen from above: back bar high, front edge sagging
        # between the front poles.
        *shaded("roof", [(-84, -46), (84, -46)] + sag, "$slate.light", [(-47, -35, "$slate"), (-12, 0, "$slate.light2")]),
        band("hem", sag, 3.2, "$slate.dark"),
        P("roof_seam_a", poly([(-30, -46), (-28, -46), (-33, -5), (-35, -5)]), "$slate.dark@0.5"),
        P("roof_seam_b", poly([(28, -46), (30, -46), (35, -5), (33, -5)]), "$slate.dark@0.5"),
        P("roof_lit", poly([(-70, -32), (-38, -32), (-40, -16), (-74, -18)]), "$white@0.12"),
        P("patch", R(16, 12, 1), "$bone.dark", at=(56, -28), rot=8, stroke=INK_HAIR),
        P("patch_stitch", R(12, 1, 0.3), "$ink@0.5", at=(56, -28), rot=8),
        P("roof_grit", ell(18, 2.4), "$sand@0.5", at=(-8, -38)),
        P("roof_page", R(9, 11, 0.6), "$bone", at=(-52, -32), rot=-24, stroke=INK_HAIR),
        # The front poles, and their ropes out to the pegs.
        pole("pole_fl", -94, 22, 72, "$steel.dark"),
        pole("pole_fr", 94, 22, 72, "$steel.dark"),
        band("rope_l", [(-95, -12), (-102, 20), (-108, 56)], 1.1, "$bone.dark@0.85"),
        band("rope_r", [(95, -12), (102, 20), (108, 56)], 1.1, "$bone.dark@0.85"),
        P("peg_l", R(3, 7, 1), "$steel.dark", at=(-108, 57), stroke=INK_HAIR),
        P("peg_r", R(3, 7, 1), "$steel.dark", at=(108, 57), stroke=INK_HAIR),
        # The jar hung from the middle of the front edge.
        P("jar_cord", R(1.2, 9, 0.4), "$bone.dark", at=(0, 1)),
        *halo("jar_glow", 0, 13, 15, 13, 0.5),
        P("jar", R(11, 13, 3.4), "$frost.dark@0.3", at=(0, 12), stroke=INK_HAIR),
        *cap("jar_cap_a", -1.6, 14, 3),
        *cap("jar_cap_b", 2.4, 10.5, 2.3),
        P("jar_lid", R(12, 3, 1), "$steel", at=(0, 5.4), stroke=INK_HAIR),
        P("jar_shine", R(1.6, 8, 0.8), "$white@0.35", at=(-3.8, 12)),
        # The crystal the frame grew (A055), at the front-left joint.
        *bud("bud", -96, -10, 0.9, 0.5),
    ]
    anims = {
        "breathe": loop(
            "the wind gets under the canvas and the hem lifts; the jar's caps brighten and dim",
            3.6,
            [
                track("hem", "y", [(0, 0), (0.45, -1.6), (0.7, -0.5), (1, 0)]),
                track("roof_lit", "opacity", [(0, 1), (0.45, 0.6), (1, 1)]),
                track("roof_page", "rot", [(0, -24), (0.4, -16), (0.6, -27), (1, -24)]),
                track("note_b", "rot", [(0, 6), (0.3, 12), (0.55, 3), (1, 6)]),
                track("jar_cap_a_lit", "opacity", [(0, 0.7), (0.5, 1), (1, 0.7)]),
                track("jar_cap_b_lit", "opacity", [(0, 1), (0.5, 0.7), (1, 1)]),
                *glow_tracks("jar_glow", 0.75, 1),
                *glow_tracks("inside_glow", 0.8, 1),
            ],
        )
    }
    return doc(
        "ss.base.frame",
        "The frame",
        "Arin's frame, put up on the first day (A001: \"Base frame and water tank up.\"), with a canvas over it: where the camp sleeps "
        "between expeditions. Four poles; the canvas is let down from the back bar to the ground for a wall, and stretched forward over the "
        "front poles, sagging between them, with guy ropes out to pegs. Pages are pinned to the wall on a cord, a bone patch is stitched on "
        "the roof, and a loose page has blown up onto it. Underneath on a ground sheet are a bedroll laid out with a folded pillow, one still "
        "rolled, a mug and a stack of pages to read by. A jar of glowing caps hangs from the middle of the front edge, and its light is the "
        "only light in there. At the front-left joint is the crystal the frame grew, which by day 471 came off one-handed (A055). The hem "
        "lifts in the wind and the jar's caps breathe (`breathe`).",
        (224, 140),
        parts,
        anims,
    )


# ============================================================== the tank
def tank():
    parts = [
        shadow("shadow", 0, 27, 24, 6),
        P("leg_l", R(4, 10, 1), "$slate", at=(-12, 22), stroke=INK_HAIR),
        P("leg_r", R(4, 10, 1), "$slate", at=(12, 22), stroke=INK_HAIR),
        *shaded("body", rr(36, 44, 6, (0, -2)), "$steel", [(6, 19, "$steel.dark")], axis=0),
        P("body_lit", R(4, 36, 2), "$steel.light", at=(-11, -2)),
        P("cap", ell(18, 5), "$steel.light", at=(0, -24), stroke=INK_THIN),
        P("cap_lid", ell(7, 2.2), "$slate", at=(0, -25)),
        P("band_a", R(37, 3, 1), "$slate", at=(0, -12)),
        P("band_b", R(37, 3, 1), "$slate", at=(0, 10)),
        # The gauge: a strip of glass with the water standing in it.
        P("gauge", R(5, 26, 2), "$frost.dark@0.5", at=(-3, 0), stroke=INK_HAIR),
        P("gauge_water", R(3, 14, 1.5), "$aqua@0.75", at=(-3, 5)),
        P("tap", R(7, 3, 1), "$slate.dark", at=(20, 14), stroke=INK_HAIR),
        P("drip", ell(1.1, 1.6), "$aqua@0.8", at=(22, 17)),
        P("puddle", ell(5.5, 1.8), "$aqua@0.3", at=(21, 27)),
    ]
    anims = {
        "drip": loop(
            "a drop gathers at the tap, falls, and the puddle takes it",
            2.4,
            [
                track("drip", "y", [(0, 0), (0.7, 0), (0.86, 9), (0.87, 0), (1, 0)]),
                track("drip", "opacity", [(0, 0), (0.5, 1), (0.85, 1), (0.87, 0), (1, 0)]),
                track("puddle", "scale", [(0, 1), (0.86, 1), (0.9, 1.18), (1, 1)]),
            ],
        )
    }
    return doc(
        "ss.base.tank",
        "The tank",
        "The water tank Arin put up beside the frame on the first day (A001). A steel drum on two legs with slate bands, a glass gauge with "
        "the water standing in it, and a tap that drips into a small puddle (`drip`). It is cold, like everything the expedition carried in.",
        (56, 62),
        parts,
        anims,
    )


# ============================================================== the shelf: seven boxes of paper
def shelf():
    parts = [shadow("shadow", 0, 30, 60, 8)]
    # Seven boxes (A055): three on the ground, three on those, one on top.
    boxes = [(-34, 16), (0, 18), (34, 16), (-18, -4), (16, -3), (46, -1), (-2, -24)]
    pages = [(-1, -1), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1), (1, -1)]
    for i, (x, y) in enumerate(boxes):
        w = 34 if i < 3 else 30 if i < 6 else 28
        parts += [
            *shaded(f"box_{i}", rr(w, 20, 2, (x, y)), "$slate", [(y + 4, y + 11, "$slate.dark")]),
            P(f"box_{i}_face", R(w - 8, 8, 1.5), "$slate.light@0.45", at=(x, y)),
            P(f"box_{i}_lid", R(w + 2, 5, 1.5), "$slate.light", at=(x, y - 9), stroke=INK_HAIR),
            P(f"box_{i}_corner", R(4, 18, 1), "$steel@0.8", at=(x - w / 2 + 3, y)),
        ]
        # Paper standing proud of every lid, a different lie in each box.
        dx, dr = pages[i]
        parts += [
            P(f"box_{i}_page", R(w * 0.5, 7, 0.6), "$bone", at=(x + dx * 3, y - 13), rot=dr * 7, stroke=INK_HAIR),
            P(f"box_{i}_page2", R(w * 0.35, 6, 0.6), "$husk", at=(x - dx * 4 + 4, y - 12), rot=-dr * 5),
            P(f"box_{i}_line", R(w * 0.3, 1, 0.3), "$slate.dark@0.55", at=(x + dx * 3, y - 14), rot=dr * 7),
        ]
    parts += [
        # The cord round the top box.
        P("cord", R(30, 1.6, 0.5), "$bone.dark", at=(-2, -22)),
        # Loose pages that did not make it into a box.
        P("loose_a", R(12, 8, 0.8), "$bone", at=(-54, 30), rot=-14, stroke=INK_HAIR),
        P("loose_a_ln", R(7, 1, 0.3), "$slate.dark@0.5", at=(-54, 29), rot=-14),
        P("loose_b", R(10, 7, 0.8), "$husk", at=(54, 29), rot=10, stroke=INK_HAIR),
    ]
    anims = {
        "stir": loop(
            "the wind lifts the pages standing proud of the lids, one box after another",
            3.2,
            [track(f"box_{i}_page", "rot", [(0, pages[i][1] * 7), (0.12 * i + 0.1, pages[i][1] * 7 + 5), (min(0.95, 0.12 * i + 0.3), pages[i][1] * 7), (1, pages[i][1] * 7)]) for i in range(7)]
            + [track("loose_b", "rot", [(0, 10), (0.4, 18), (0.6, 8), (1, 10)])],
        )
    }
    return doc(
        "ss.base.shelf",
        "The shelf",
        "The seven boxes of paper (A055: \"Base inventory: the frame, the tank, seven boxes of paper, the saw.\"), stacked three, three and one "
        "in cold slate crates with paper standing proud of every lid, cord round the top box, and loose pages that never got in. This is the "
        "ninth expedition's shelf (guide §3.3, §12.1), where the pages the player picks up are filed. feelers opens the COLLECTION here. "
        "The pages stir in the wind (`stir`).",
        (132, 78),
        parts,
        anims,
    )


# ============================================================== the line: pages pegged out
def line():
    def cord_y(x):
        t = (x + 54) / 108
        return -16 + 12 * 4 * t * (1 - t)

    xs = [-38, -22, -6, 10, 26, 42]
    tilt = lambda i: (i % 3 - 1) * 4
    parts = [
        shadow("shadow", 0, 24, 60, 5, "0.3"),
        P("stake_l", R(3.4, 44, 1), "$steel", at=(-56, 2), stroke=INK_HAIR),
        P("stake_r", R(3.4, 44, 1), "$steel", at=(56, 2), stroke=INK_HAIR),
        band("cord", [(x, cord_y(x)) for x in range(-54, 55, 6)], 1.1, "$bone.dark"),
    ]
    fills = ["$bone", "$husk", "$bone", "$bone.dark", "$husk", "$bone"]
    for i, x in enumerate(xs):
        y = cord_y(x)
        w, h = (10, 13) if i % 2 == 0 else (11, 11)
        parts += [
            P(f"page_{i}", R(w, h, 0.6), fills[i], at=(x, y + h / 2 + 0.5), rot=tilt(i), stroke=INK_HAIR),
            P(f"page_{i}_ln", R(w - 4, 0.9, 0.3), "$slate.dark@0.55", at=(x, y + h / 2 - 1), rot=tilt(i)),
            P(f"page_{i}_ln2", R(w - 5, 0.9, 0.3), "$slate.dark@0.4", at=(x, y + h / 2 + 2), rot=tilt(i)),
            P(f"peg_{i}", R(2, 3.6, 0.6), "$steel.light", at=(x, y)),
        ]
    parts += [
        P("fallen", R(10, 7, 0.6), "$bone", at=(18, 25), rot=12, stroke=INK_HAIR),
        P("fallen_ln", R(6, 0.9, 0.3), "$slate.dark@0.5", at=(18, 24.5), rot=12),
    ]
    swing = lambda i: [(0, tilt(i)), (0.08 + i * 0.1, tilt(i) + 9), (0.3 + i * 0.1, tilt(i) - 3), (1, tilt(i))]
    anims = {
        "stir": loop(
            "the wind goes down the line and the pages swing on their pegs, one after another",
            2.8,
            [track(f"page_{i}{s}", "rot", swing(i)) for i in range(len(xs)) for s in ("", "_ln", "_ln2")],
        )
    }
    doc(
        "ss.base.line",
        "The line",
        "A cord between two steel stakes with pages pegged out on it: the ones not filed into the seven boxes yet (A055), hung where the wind "
        "can read them. Six pages in bone and husk, each written on, and one that came off the line and lies in the dirt under it. The pages "
        "swing on their pegs, one after another down the line (`stir`).",
        (128, 64),
        parts,
        anims,
    )


# ============================================================== the vat
def vat():
    parts = [
        shadow("shadow", 0, 34, 26, 6),
        P("stand", R(40, 8, 2), "$slate", at=(0, 30), stroke=INK_THIN),
        P("stand_lit", R(30, 2, 1), "$slate.light", at=(0, 28)),
        # The glass, drawn behind the jelly so the colour is the jelly's.
        P("glass", R(40, 46, 9), "$frost.dark@0.32", at=(0, 3), stroke=INK_THIN),
        *shaded("jelly", rr(36, 30, 8, (0, 10)), "$gold", [(-6, 0, "$gold.light"), (16, 26, "$chitin")], stroke=None),
        P("meniscus", ell(17, 2.6), "$gold.light2", at=(0, -4)),
        P("caustic", ell(6, 2), "$gold.light2@0.8", at=(-7, 8)),
        P("bubble_a", circ(1.6), "$gold.light2@0.9", at=(8, 12)),
        P("bubble_b", circ(1.1), "$gold.light2@0.8", at=(5, 18)),
        P("glass_lit", R(4, 34, 2), "$white@0.45", at=(-14, 2)),
        *shaded("lid", rr(44, 7, 2.5, (0, -21)), "$steel", [(-25, -22, "$steel.light")]),
        P("clamp_l", R(4, 12, 1), "$steel.dark", at=(-21, -16), stroke=INK_HAIR),
        P("clamp_r", R(4, 12, 1), "$steel.dark", at=(21, -16), stroke=INK_HAIR),
        # The ladle hooked over the rim, and the drop that got away.
        P("ladle", R(3, 24, 1.2), "$steel.light", at=(14, -25), rot=18, stroke=INK_HAIR),
        P("ladle_bowl", ell(4.4, 3), "$steel", at=(17.5, -36), stroke=INK_HAIR),
        P("drop", ell(2, 3), "$gold", at=(-19.5, 14), stroke=INK_HAIR),
        P("drop_lit", circ(0.7), "$gold.light2", at=(-20.2, 13)),
    ]
    anims = {
        "settle": loop(
            "the jelly settles: the light moves on it and a bubble rises",
            4.0,
            [
                track("caustic", "x", [(0, 0), (0.5, 6), (1, 0)]),
                track("meniscus", "scale", [(0, 1), (0.5, 0.94), (1, 1)]),
                track("bubble_a", "y", [(0, 0), (0.8, -14), (0.81, 0), (1, 0)]),
                track("bubble_a", "opacity", [(0, 1), (0.78, 1), (0.8, 0), (0.85, 0), (1, 1)]),
            ],
        )
    }
    return doc(
        "ss.base.vat",
        "The jelly vat",
        "The jelly the expedition trades in, kept in a glass vat on a slate stand under a clamped steel lid. The glass is drawn behind the "
        "jelly so the colour is the jelly's: gold, because gold is jelly's (feelers D14), going to chitin in the deep, with light moving on "
        "the surface and a bubble rising (`settle`). A ladle is hooked over the rim and a drop has run down the side. The guide's meta shop "
        "is \"to evolve on jelly\" (§12.1), so feelers opens EVOLUTION here.",
        (60, 84),
        parts,
        anims,
    )


# ============================================================== the bench
def bench():
    vials = ["$venom", "$ember", "$frost", "$bile", "$aqua", "$orchid"]
    parts = [
        shadow("shadow", 0, 26, 54, 7),
        # A field table on crossed legs, with a crate under it.
        *shaded("under_crate", rr(26, 14, 1.5, (-4, 18)), "$slate", [(20, 26, "$slate.dark")], stroke=INK_HAIR),
        P("under_crate_lid", R(27, 3, 1), "$slate.light", at=(-4, 11.5)),
        P("leg_a", R(4, 30, 1.5), "$slate", at=(-34, 12), rot=18, stroke=INK_HAIR),
        P("leg_b", R(4, 30, 1.5), "$slate", at=(-34, 12), rot=-18, stroke=INK_HAIR),
        P("leg_c", R(4, 30, 1.5), "$slate", at=(34, 12), rot=18, stroke=INK_HAIR),
        P("leg_d", R(4, 30, 1.5), "$slate", at=(34, 12), rot=-18, stroke=INK_HAIR),
        P("top", R(100, 9, 2.5), "$steel", at=(0, -4), stroke=INK_THIN),
        P("top_lit", R(84, 2, 1), "$steel.light", at=(-4, -7)),
        P("top_edge", R(100, 3, 1.5), "$steel.dark", at=(0, 0)),
        # The rack of samples the level-up draws from.
        P("rack", R(44, 14, 2), "$slate", at=(-20, -14), stroke=INK_THIN),
    ]
    for i, c in enumerate(vials):
        x = -38 + i * 7.2
        parts += [
            P(f"vial_{i}", R(5, 15, 2), "$frost.dark@0.4", at=(x, -19), stroke=INK_HAIR),
            P(f"vial_{i}_fill", R(4, 8, 1.5), c, at=(x, -16)),
            P(f"vial_{i}_lit", R(1, 6, 0.4), "$white@0.45", at=(x - 1.2, -18)),
            P(f"vial_{i}_cap", R(5, 3, 1), "$steel.light", at=(x, -27)),
        ]
    parts += [
        # The syringe, lying where the last dose was drawn.
        P("barrel", R(26, 6, 2), "$frost@0.45", at=(18, -11), rot=-6, stroke=INK_HAIR),
        P("barrel_fill", R(12, 4, 1.5), "$venom@0.8", at=(13, -10.4), rot=-6),
        P("plunger", R(10, 3, 1), "$steel.light", at=(36, -13), rot=-6, stroke=INK_HAIR),
        P("needle", R(8, 1.2, 0.4), "$steel.light", at=(1, -9), rot=-6),
        # The instrument: a box with a dial, its face the instrument's blue.
        P("box", R(20, 14, 2), "$slate.dark", at=(40, -15), stroke=INK_THIN),
        P("dial", circ(4.4), "$frost@0.7", at=(40, -15), stroke=INK_HAIR),
        P("needle_dial", R(4, 0.9, 0.3), "$ink", at=(41.5, -16), rot=-35),
        # A notebook page under the rack.
        P("note", R(14, 10, 0.8), "$bone", at=(-44, -6), rot=-8, stroke=INK_HAIR),
        P("note_ln", R(9, 0.9, 0.3), "$slate.dark@0.5", at=(-44, -7), rot=-8),
    ]
    anims = {
        "read": loop(
            "the dial's needle wanders and settles: the instrument reading the air",
            3.0,
            [track("needle_dial", "rot", [(0, -35), (0.3, -20), (0.55, -42), (0.75, -30), (1, -35)])],
        )
    }
    return doc(
        "ss.base.bench",
        "The bench",
        "The instrument's own table: a field bench on crossed legs with a crate under it. On it is a rack of six vials in the colours the "
        "level-up's samples come in, the syringe lying where the last dose was drawn, a notebook page, and a slate box whose dial is the "
        "instrument's blue. The needle wanders, reading the air (`read`). feelers opens BUILD here, where the order samples are drawn in "
        "is planned.",
        (120, 64),
        parts,
        anims,
    )


# ============================================================== the hearth
def hearth():
    cx, cy, rx, ry = 0, 4, 27, 13
    stones = []
    for i in range(12):
        a = 2 * math.pi * i / 12 + 0.15
        stones.append((i, cx + rx * math.cos(a), cy + ry * math.sin(a), 5.2 + 0.8 * ((i * 7) % 3), math.sin(a) > 0))

    def stone(i, x, y, r):
        k = [(-1, 0.55), (-0.62, -0.5), (0.1, -0.72), (0.86, -0.3), (1, 0.4), (0.3, 0.7), (-0.6, 0.72)]
        jag = [(px * r * (1 + 0.08 * ((i + j) % 3 - 1)), py * r * 0.7) for j, (px, py) in enumerate(k)]
        return [
            P(f"stone_{i}", poly(jag), "$smoke" if i % 3 else "$smoke.dark", at=(x, y), stroke=INK_HAIR),
            P(f"stone_{i}_lit", ell(r * 0.45, r * 0.18), "$smoke.light@0.8", at=(x - r * 0.2, y - r * 0.32)),
        ]

    caps = [
        ("c0", -12, -2, 4.2), ("c1", -3, -5, 5.4), ("c2", 8, -3, 4.6), ("c3", 15, 2, 3.2),
        ("c4", -16, 5, 3.0), ("c5", -6, 4, 4.0), ("c6", 5, 6, 3.6), ("c7", 12, 8, 2.4),
    ]
    parts = [
        # The light the caps lay on the ground round the ring.
        *halo("spill", 0, 6, 44, 24, 0.36),
        P("bed", ell(24, 11), "$soil", at=(cx, cy)),
        P("bed_lit", ell(18, 6), "$soil.light@0.8", at=(cx, cy + 3)),
    ]
    parts += [p for i, x, y, r, front in stones if not front for p in stone(i, x, y, r)]
    parts += halo("halo", 0, -2, 26, 18, 0.5)
    parts += [p for cid, x, y, r in caps for p in cap(cid, x, y, r)]
    parts += [p for i, x, y, r, front in stones if front for p in stone(i, x, y, r)]
    # Two mugs left by the ring, and spores going up off the caps.
    parts += [
        P("mug_a", R(5.4, 6.4, 1.3), "$steel", at=(33, 18), stroke=INK_HAIR),
        P("mug_a_lit", R(1.2, 4.4, 0.4), "$steel.light", at=(31.6, 18.4)),
        P("mug_a_rim", ell(2.7, 0.9), "$coal", at=(33, 15)),
        P("mug_b", R(5.4, 6.4, 1.3), "$steel", at=(-34, 17), rot=-8, stroke=INK_HAIR),
        P("mug_b_lit", R(1.2, 4.4, 0.4), "$steel.light", at=(-35.4, 17.2), rot=-8),
        P("mug_b_rim", ell(2.7, 0.9), "$coal", at=(-34.4, 13.8), rot=-8),
    ]
    motes = [("m0", -8, -8), ("m1", 4, -10), ("m2", 12, -6), ("m3", -2, -12)]
    parts += [P(mid, circ(0.9), "$spore.light2@0.9", at=(x, y)) for mid, x, y in motes]
    tracks = [*glow_tracks("halo", 0.7, 1), *glow_tracks("spill", 0.8, 1)]
    tracks += [track(f"{cid}_lit", "opacity", [(0, 0.6 if i % 2 else 1), (0.5, 1 if i % 2 else 0.6), (1, 0.6 if i % 2 else 1)]) for i, (cid, *_r) in enumerate(caps)]
    for i, (mid, _x, _y) in enumerate(motes):
        tracks += rising(mid, i / len(motes), 12)
    doc(
        "ss.base.hearth",
        "The hearth",
        "Where a camp elsewhere would keep a fire. An expedition does not glow and lights nothing (feelers guide §7.2), so this camp sits "
        "round the hive's light instead: a ring of stones round a bed of dug earth, and in the bed the glowing caps, grown from the one Sol "
        "carried in an emitter that never worked. They are the warm thing in a cold camp and they are not the camp's. Two steel mugs have "
        "been left by the ring. The caps brighten and dim, slower than breathing, and spores go up off them (`breathe`).",
        (92, 60),
        parts,
        {"breathe": loop("the caps brighten and dim, slower than breathing, and spores go up off them", 4.0, tracks)},
    )


# ============================================================== the board
def board():
    parts = [
        shadow("shadow", 0, 30, 20, 4, "0.4"),
        P("leg_back", R(3, 40, 1), "$slate.dark", at=(0, 6), stroke=INK_HAIR),
        P("leg_l", R(3.4, 46, 1), "$steel.dark", at=(-12, 8), rot=12, stroke=INK_HAIR),
        P("leg_r", R(3.4, 46, 1), "$steel.dark", at=(12, 8), rot=-12, stroke=INK_HAIR),
        P("ledge", R(42, 3, 1), "$steel", at=(0, 8), stroke=INK_HAIR),
        *shaded("board", rr(46, 34, 2, (0, -11)), "$slate", [(0, 7, "$slate.dark")]),
        P("sheet", R(40, 28, 0.8), "$bone", at=(0, -11), rot=-1.5, stroke=INK_HAIR),
        # The ground drawn round the camp: a ridge line, the pan's edge, the pit.
        band("contour_a", [(-17, -21), (-10, -19), (-4, -22), (4, -20)], 0.8, "$sand.dark@0.55"),
        band("contour_b", [(6, -4), (12, -6), (18, -3)], 0.8, "$sand.dark@0.55"),
        P("pit_mark", {"kind": "ring", "r": 2.6, "width": 0.8}, "$slate.dark@0.6", at=(-14, -6)),
        # The camp in the middle, and the four ways out of it, pinned.
        P("camp", R(3, 3, 0.4), "$ink@0.75", at=(0, -11)),
        band("route_s", [(0, -11), (1, -6), (0, -1)], 0.7, "$slate.dark@0.6"),
        band("route_ne", [(0, -11), (6, -16), (12, -20)], 0.7, "$slate.dark@0.6"),
        band("route_nw", [(0, -11), (-6, -15), (-13, -19)], 0.7, "$slate.dark@0.6"),
        band("route_w", [(0, -11), (-7, -9), (-14, -6)], 0.7, "$slate.dark@0.6"),
        P("pin_s", circ(1.5), "$frost", at=(0, -1), stroke=INK_HAIR),
        P("pin_ne", circ(1.5), "$frost", at=(12, -20), stroke=INK_HAIR),
        P("pin_nw", circ(1.5), "$frost", at=(-13, -19), stroke=INK_HAIR),
        P("pin_w", circ(1.5), "$frost", at=(-14, -6), stroke=INK_HAIR),
        P("note", R(10, 8, 0.6), "$husk", at=(15, -2), rot=8, stroke=INK_HAIR),
        P("chalk", R(8, 2, 0.8), "$bone", at=(-12, 6.5)),
    ]
    doc(
        "ss.base.board",
        "The board",
        "A slate board on an easel with a sheet pinned to it: the ground round the camp drawn by hand, the camp a square in the middle, and "
        "four routes out of it, each to a cold pin — south to the plains, north-east to the burrow, north-west to the pan, west to the pit. "
        "A note is tucked in one corner and a stub of chalk lies on the ledge.",
        (56, 72),
        parts,
    )


# ============================================================== the lamps
def lamp_jar(prefix, x, y):
    return [
        *halo(f"{prefix}_glow", x, y, 12, 12, 0.36),
        P(f"{prefix}_jar", R(14, 16, 4), "$frost.dark@0.3", at=(x, y), stroke=INK_THIN),
        *cap(f"{prefix}_cap_a", x - 2, y + 3, 3.6),
        *cap(f"{prefix}_cap_b", x + 3, y - 1, 2.8),
        *cap(f"{prefix}_cap_c", x - 1.4, y - 4, 2.2),
        P(f"{prefix}_lid", R(15, 3.4, 1.2), "$steel", at=(x, y - 9), stroke=INK_HAIR),
        P(f"{prefix}_glass_lit", R(2, 10, 1), "$white@0.35", at=(x - 5, y)),
    ]


def breathe_tracks(prefix):
    def k(a, b):
        return [(0, a), (0.5, b), (1, a)]
    return [
        *glow_tracks(f"{prefix}_glow", 0.7, 1),
        track(f"{prefix}_cap_a_lit", "opacity", k(0.7, 1)),
        track(f"{prefix}_cap_b_lit", "opacity", k(1, 0.65)),
        track(f"{prefix}_cap_c_lit", "opacity", k(0.75, 1)),
    ]


def lamps():
    standing = [
        shadow("shadow", -2, 20, 11, 2.5),
        P("pole", R(3, 36, 1), "$steel.dark", at=(-9, 2), stroke=INK_HAIR),
        P("pole_lit", R(1, 30, 0.4), "$steel", at=(-9.6, 2)),
        P("foot", R(12, 3, 1), "$slate", at=(-9, 20), stroke=INK_HAIR),
        P("arm", R(16, 2.4, 1), "$steel.dark", at=(-2, -15), stroke=INK_HAIR),
        P("hook", R(1.2, 4, 0.4), "$steel.dark", at=(5, -12.5)),
        *lamp_jar("jar", 5, 0),
    ]
    doc(
        "ss.base.lamp",
        "Fungus lamp",
        "The camp's light, and it is not the camp's. Glowing caps are shut in a jar and hung off a steel pole. An expedition does not "
        "glow (feelers guide §7.2), so it lives by borrowed fungus — the cap Sol carried in an emitter that never worked, grown on. The caps "
        "breathe (`breathe`), and feelers lays a soft teal pool of light under the jar.",
        (32, 46),
        standing,
        {"breathe": loop("the caps in the jar brighten and dim, slower than breathing", 3.2, breathe_tracks("jar"))},
    )
    hanging = [
        P("cord", R(1.4, 12, 0.5), "$bone.dark", at=(0, -14)),
        *lamp_jar("jar", 0, 0),
    ]
    doc(
        "ss.base.lamp-hang",
        "Fungus lamp, hung",
        "The same jar of glowing caps as `ss.base.lamp`, hung on a cord instead of a pole. It breathes (`breathe`) and sways a little on "
        "its cord.",
        (28, 40),
        hanging,
        {
            "breathe": loop(
                "the caps brighten and dim, and the jar sways on its cord",
                3.2,
                breathe_tracks("jar")
                + [track(p["id"], "x", [(0, 0), (0.5, 1.4), (1, 0)]) for p in hanging if p["id"].startswith("jar_") and not p["id"].endswith("_lit")],
            )
        },
    )
    jar = [
        shadow("shadow", 0, 7, 6, 2, "0.4"),
        *halo("glow", 0, 0, 9, 8, 0.36),
        P("jar", R(10, 12, 3), "$frost.dark@0.3", at=(0, 1), stroke=INK_HAIR),
        *cap("cap_a", -1.4, 3, 2.6),
        *cap("cap_b", 2, 0, 2),
        P("lid", R(11, 2.6, 1), "$steel", at=(0, -5.4), stroke=INK_HAIR),
        P("glass_lit", R(1.4, 7, 0.6), "$white@0.35", at=(-3.4, 1)),
    ]
    doc(
        "ss.base.jar",
        "Path jar",
        "A small jar of glowing caps set down on the ground, one of a row along each path out of the camp, so the way back in can be found "
        "in the dark. It breathes like the lamps (`breathe`).",
        (20, 20),
        jar,
        {"breathe": loop("the caps brighten and dim", 3.6, [*glow_tracks("glow", 0.7, 1), track("cap_a_lit", "opacity", [(0, 0.7), (0.5, 1), (1, 0.7)])])},
    )


# ============================================================== the lockers and the keeps
def locker():
    parts = [
        shadow("shadow", 0, 10, 16, 3.5),
        *shaded("box", rr(30, 16, 2, (0, 2)), "$slate", [(5, 11, "$slate.dark")]),
        P("lid", R(32, 5, 1.5), "$slate.light", at=(0, -6), stroke=INK_HAIR),
        P("latch", R(5, 5, 1), "$steel", at=(0, 2), stroke=INK_HAIR),
        P("stripe", R(30, 2, 0.5), "$frost.dark@0.5", at=(0, 7)),
    ]
    doc(
        "ss.base.locker",
        "Locker",
        "One writer's footlocker, in the cold slate everything of the expedition's is: a box, a lid, a latch, a frost stripe. A row of eight "
        "stands along the camp's fence, one per writer in the order the expeditions came. On each lid is the one thing that writer's log "
        "kept (`ss.base.keep-*`). In feelers you take up a writer's body at their locker.",
        (36, 24),
        parts,
    )


KEEPS = {
    "arin": (
        "Arin's cartridges",
        "Arin's emitter was the prototype, and its forty cartridges dried on day 388 (feelers character plan §1.3). Five of the spent tubes stand in a "
        "slate clip: frost glass, empty.",
        lambda: [
            P("clip", R(18, 5, 1.5), "$slate", at=(0, 4), stroke=INK_HAIR),
            *[P(f"tube_{i}", R(3, 11, 1.2), "$frost.dark@0.45", at=(-6 + i * 3, -2), stroke=INK_HAIR) for i in range(5)],
            *[P(f"tube_{i}_cap", R(3, 2, 0.6), "$steel", at=(-6 + i * 3, -8)) for i in range(5)],
        ],
    ),
    "sol": (
        "Sol's cap",
        "Sol's emitter never worked from the first day, and Sol carried a fungus cap in it instead. Here is the cap, dull and teal, with no "
        "light in it any more — the ones in the camp's jars and its hearth were grown from it.",
        lambda: [
            P("stem", R(3, 7, 1), "$husk.dark", at=(0, 3), stroke=INK_HAIR),
            P("cap", ell(8, 4.6), "$spore.dark", at=(0, -2), stroke=INK_THIN),
            P("cap_shade", ell(8, 2), "$spore.dark2@0.8", at=(0, 0.5)),
            P("spot", circ(1.3), "$spore@0.6", at=(-3, -3)),
        ],
    ),
    "haram": (
        "Haram's husk",
        "Haram put a moulted husk into the second-model emitter. It is a hollow, segmented shell in husk white.",
        lambda: [
            P("husk", ell(9, 5), "$husk", at=(0, 0), stroke=INK_THIN),
            *[P(f"seg_{i}", R(1.2, 7, 0.4), "$husk.dark", at=(-5 + i * 3.4, 0)) for i in range(4)],
            P("mouth", ell(2.6, 2.2), "$coal", at=(8, 0)),
            P("lit", ell(4, 1.2), "$white@0.4", at=(-2, -3)),
        ],
    ),
    "mina": (
        "Mina's piece of wall",
        "A palm-sized piece of the burrow's wall, and it is warm (M041). It is a chunk of rust earth in strata, with a seam of the wall's own pull through "
        "it.",
        lambda: [
            P("chunk", poly([(-8, 4), (-7, -3), (-2, -6), (5, -5), (8, 0), (6, 5), (-2, 6)]), "$rust.light", stroke=INK_THIN),
            P("stratum_a", poly([(-7, 0), (7, -2), (7, 0), (-7, 2)]), "$sand@0.8"),
            P("stratum_b", poly([(-6, 3), (6, 2), (5, 4), (-5, 5)]), "$rust@0.9"),
            P("warm", circ(2), "$ember@0.35", at=(1, -2)),
        ],
    ),
    "kano": (
        "Kano's road stake",
        "Kano walked the swarm's road for 330 days. This is a marker stake from it, notched once for every ten days, with a cold strip of cloth "
        "tied on.",
        lambda: [
            P("stake", R(4, 18, 1), "$smoke.light", at=(0, -1), stroke=INK_HAIR),
            *[P(f"notch_{i}", R(4, 0.9, 0.2), "$ink@0.55", at=(0, -7 + i * 2.2)) for i in range(6)],
            P("cloth", poly([(2, -7), (9, -6), (8, -3), (2, -4)]), "$frost.dark", stroke=INK_HAIR),
        ],
    ),
    "eden": (
        "Eden's jelly",
        "Eden put a finger of royal jelly into the emitter. It is a small jar with that finger of gold in it.",
        lambda: [
            P("jar", R(10, 13, 3), "$frost.dark@0.35", at=(0, 0), stroke=INK_THIN),
            P("jelly", R(8, 6, 2), "$gold", at=(0, 3)),
            P("shine", circ(1), "$gold.light2", at=(-2, 2)),
            P("lid", R(11, 3, 1), "$steel", at=(0, -7), stroke=INK_HAIR),
        ],
    ),
    "rowan": (
        "Rowan's bowl",
        "A stone bowl from the ruins, with the old pheromone dried in it. Rowan's tubes turned to stone. The film in the bowl is pink, because it "
        "is the hive's signal.",
        lambda: [
            P("bowl", poly([(-9, -2), (9, -2), (6, 5), (-6, 5)]), "$smoke", stroke=INK_THIN),
            P("rim", ell(9, 2.4), "$smoke.light", at=(0, -2), stroke=INK_HAIR),
            P("film", ell(6.4, 1.4), "$pheromone@0.75", at=(0, -1.8)),
            P("chip", poly([(5, 1), (8, 0), (7, 3)]), "$smoke.dark"),
        ],
    ),
    "teo": (
        "Teo's bundle",
        "Teo had nothing to put in the emitter but paper. This is a bundle of pages tied with cord, the edges uneven.",
        lambda: [
            P("pages", R(16, 10, 1), "$bone", at=(0, 0), stroke=INK_THIN),
            P("page_top", R(14, 8, 1), "$husk", at=(1, -2), rot=-5, stroke=INK_HAIR),
            P("cord_v", R(1.6, 11, 0.4), "$bone.dark2", at=(-2, -1)),
            P("cord_h", R(17, 1.6, 0.4), "$bone.dark2", at=(0, 0)),
            *[P(f"line_{i}", R(8, 0.8, 0.3), "$slate.dark@0.5", at=(3, -4 + i * 1.8), rot=-5) for i in range(3)],
        ],
    ),
}


def keeps():
    for key, (name, desc, draw) in KEEPS.items():
        doc(
            f"ss.base.keep-{key}",
            name,
            desc + " It sits on its writer's locker (`ss.base.locker`).",
            (24, 22),
            draw(),
        )


# ============================================================== the marks
def stump():
    parts = [
        shadow("shadow", 0, 11, 15, 4),
        *shaded("trunk", [(-11, -4), (11, -4), (13, 9), (-13, 9)], "$pheromone.dark", [(4, 10, "$pheromone.dark2")]),
        P("trunk_lit", poly([(-9, -3), (-5, -3), (-6, 8), (-11, 8)]), "$pheromone@0.55"),
        P("face", ell(11.5, 4.2), "$husk.dark", at=(0, -4), stroke=INK_THIN),
        *[P(f"ring_{i}", ell(9.4 - i * 2.3, 3.4 - i * 0.82), "$pheromone.dark@0.45" if i % 2 == 0 else "$husk.dark", at=(0, -4)) for i in range(4)],
        P("heart", ell(1.4, 0.6), "$pheromone@0.85", at=(0, -4)),
        P("saw_mark", R(18, 0.9, 0.3), "$ink@0.35", at=(1, -3.4), rot=-4),
    ]
    doc(
        "ss.base.stump",
        "Cut spire",
        "A pheromone spire cut off flat. The face has gone pale where the signal ran out of it, and it is ringed like a tree, one ring per "
        "passing of the vermin (A030), with a little pink left at the heart and the saw's line across it. Three of these stand by the camp's "
        "south path, the cut spires the records found south of base (T010). In feelers they mark the way out to the Plains.",
        (32, 28),
        parts,
    )


def cairn():
    def slab(id, pts, top_fill, face_fill):
        cx = sum(x for x, _ in pts) / len(pts)
        return [
            P(f"{id}_under", poly([(cx + (x - cx) * 1.08, y + 1.2) for x, y in pts]), "$ink"),
            P(id, poly(pts), face_fill),
            P(f"{id}_top", poly([(pts[0][0] + 2, pts[1][1] + 1.6), pts[1], pts[2], (pts[3][0] - 2, pts[2][1] + 1.6)]), top_fill),
        ]

    parts = [
        shadow("shadow", 0, 20, 15, 4),
        *slab("slab_a", [(-13, 18), (-11, 11), (10, 10), (13, 18)], "$husk", "$husk.dark"),
        *slab("slab_b", [(-10, 11), (-8, 4), (8, 3), (10, 10)], "$husk", "$husk.dark"),
        *slab("slab_c", [(-7, 4), (-5, -2), (6, -2), (7, 3)], "$silent", "$husk"),
        P("glare", poly([(-3, -1), (2, -1.6), (3, 0.6), (-2, 1)]), "$white@0.8"),
        P("crack", R(8, 0.9, 0.3), "$husk.dark2", at=(-2, 15)),
        P("stake", R(2.6, 26, 0.8), "$smoke.light", at=(2, -12), stroke=INK_HAIR),
        P("flag", poly([(3, -24), (14, -21), (12, -18), (15, -15), (3, -16)]), "$frost.dark", stroke=INK_HAIR),
    ]
    anims = {
        "flutter": loop(
            "the strip of cloth on the stake flaps in the wind off the pan",
            1.4,
            [track("flag", "scale", [(0, 1), (0.3, 0.86), (0.6, 1.06), (1, 1)]), track("flag", "y", [(0, 0), (0.3, 0.6), (0.6, -0.4), (1, 0)])],
        )
    }
    doc(
        "ss.base.cairn",
        "Salt cairn",
        "Three slabs of the pan's salt plate stacked by the north-west road, drawn the way the pan's own plates are (`ss.terrain.saltplate`), "
        "with a stake driven into them and a cold strip of cloth flapping on it (`flutter`). In feelers this is the way out to the Salt Pan.",
        (32, 52),
        parts,
        anims,
    )


def prints():
    steps = []
    for i in range(4):
        x = -21 + i * 14
        y = -4 if i % 2 else 4
        steps += [
            P(f"sole_{i}", ell(3.2, 1.8), "$soil@0.8", at=(x + 1.6, y), rot=4),
            P(f"heel_{i}", ell(1.7, 1.5), "$soil@0.8", at=(x - 3.2, y), rot=4),
        ]
    doc(
        "ss.base.prints",
        "Boot prints",
        "Four steps of boot prints going one way, worn into the ground on the roads out of the camp. The expedition's, so they are the only "
        "tracks in the field with a heel.",
        (56, 20),
        steps,
    )


# ============================================================== the clutter
def clutter():
    doc(
        "ss.base.plate",
        "Hull plate",
        "A panel of the lander's skin stuck upright in the dirt as a windbreak. It is riveted, bent at one corner, and rust has run down "
        "from its rivets. The camp is walled with these and with crates.",
        (48, 40),
        [
            shadow("shadow", 0, 15, 22, 4),
            *shaded("plate", [(-20, 14), (-19, -12), (-8, -16), (18, -14), (20, 14)], "$smoke", [(-17, -6, "$steel"), (6, 15, "$smoke.dark")]),
            P("plate_lit", poly([(-17, 12), (-16, -10), (-9, -13), (-9, 12)]), "$steel.light@0.35"),
            P("bend", poly([(12, -14), (18, -14), (20, -4)]), "$smoke.dark", stroke=INK_HAIR),
            *[P(f"rivet_{i}", circ(1.2), "$slate", at=(-14 + i * 9, -8)) for i in range(4)],
            *rust("rust", 5, -8, 3, 18),
            P("foot_dirt", poly([(-21, 14), (-12, 10), (12, 11), (21, 14)]), "$sand@0.7"),
        ],
    )
    doc(
        "ss.base.crate",
        "Crate",
        "A cold slate crate with a steel corner and a frost stencil stripe. The expedition's stores came in these, and the camp's fence is "
        "built from them.",
        (30, 26),
        [
            shadow("shadow", 0, 11, 14, 3.5),
            *shaded("box", rr(24, 18, 2, (0, 1)), "$slate", [(4, 11, "$slate.dark")]),
            P("lid", R(26, 5, 1.5), "$slate.light", at=(0, -8), stroke=INK_HAIR),
            P("face", R(18, 6, 1.5), "$slate.light@0.4", at=(0, 1)),
            P("corner", R(3, 16, 1), "$steel@0.8", at=(-9.5, 1)),
            P("stencil", R(10, 2, 0.5), "$frost.dark@0.6", at=(2, 1)),
        ],
    )
    doc(
        "ss.base.bedroll",
        "Bedroll",
        "A rolled sleeping bag in cold slate, strapped and set down by a crate. Somebody sleeps in this camp between expeditions.",
        (44, 20),
        [
            shadow("shadow", 0, 7, 20, 3),
            P("roll", R(38, 13, 6.5), "$slate.light", at=(0, 0), stroke=INK_THIN),
            P("roll_shade", R(34, 5, 2.5), "$slate", at=(-1, 3.5)),
            P("end", ell(4, 6.5), "$slate", at=(17, 0), stroke=INK_HAIR),
            P("end_spiral", ell(2, 3.4), "$slate.dark", at=(17, 0)),
            P("strap_a", R(2.4, 14, 0.6), "$steel.dark", at=(-8, 0)),
            P("strap_b", R(2.4, 14, 0.6), "$steel.dark", at=(6, 0)),
        ],
    )
    doc(
        "ss.base.saw",
        "The saw",
        "The saw from the base inventory (A055). It cut the spire whose rings gave the vermin's passings away (A030), and it lies by the "
        "stumps it made.",
        (38, 16),
        [
            shadow("shadow", 0, 6, 16, 2.5),
            P("blade", poly([(-16, -2), (10, -4), (10, 3), (-16, 3)]), "$steel.light", stroke=INK_THIN),
            *[P(f"tooth_{i}", poly([(0, 0), (1.6, 2.2), (3.2, 0)]), "$steel", at=(-15 + i * 3.4, 3)) for i in range(7)],
            P("handle", R(10, 8, 2.5), "$smoke", at=(14, -1), stroke=INK_THIN),
            P("grip", R(5, 3.4, 1.2), "$coal", at=(14, -1)),
        ],
    )


if __name__ == "__main__":
    lander()
    frame()
    tank()
    shelf()
    line()
    vat()
    bench()
    hearth()
    board()
    lamps()
    locker()
    keeps()
    stump()
    cairn()
    prints()
    clutter()
    print("wrote the base")
