"""Glass for the camp: test tubes and the bench's rack, the cellar's vials, the syringe, jars, a spent cartridge.

    from bits_glass import *

Glass is a faint frost tint with whatever is in it showing through, and it is
drawn in the same order every time: the back glass (the tint), the contents
(their own colour, a shade band on the side away from the light, and their
surface), the front glints (a strong narrow one on the left, a thin one on
the right — on a thing lying down, along the top and the bottom), the ink
rim, and last the lip, the cap or the lid. The light is from the upper left.

Every helper draws its thing at its natural size in the camp about its own
origin (said in each docstring) and `placed()` it; every id is built from
`prefix`.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw import *  # noqa: E402,F401,F403

GLASS = "$frost.dark@0.3"
LIP = "$frost.dark@0.75"
BIG = 1e6

_STEP = {"light2": 2, "light": 1, "": 0, "dark": -1, "dark2": -2}
_NAME = {v: k for k, v in _STEP.items()}


def tone(tok, step, alpha=None):
    """`tok` moved `step` stops along its ramp ("$venom", +1 -> "$venom.light"), keeping its alpha unless `alpha` is given."""
    body, _, a = tok.partition("@")
    name, _, ramp = body.partition(".")
    k = max(-2, min(2, _STEP[ramp] + step))
    out = name + ("." + _NAME[k] if k else "")
    a = a if alpha is None else alpha
    return out + (f"@{a}" if a not in ("", None) else "")


def _arc(cx, cy, rx, ry, a0, a1, n):
    """Points on an ellipse from a0 to a1 degrees (y down: 90 is the bottom)."""
    out = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def _tube(w, top, bot, n=8):
    """A round-bottomed tube's outline: straight sides down from `top`, a half-circle bottom whose lowest point is `bot`."""
    r = w / 2
    return [(-r, top)] + _arc(0, bot - r, r, r, 180, 0, n) + [(r, top)]


def _half_width(y, iw, bot):
    """Half the inside width of a round-bottomed tube at height y (its inside bottom at `bot`)."""
    r = iw / 2
    cy = bot - r
    if y <= cy:
        return r
    return math.sqrt(max(0.0, r * r - (y - cy) ** 2))


def _surface(prefix, y, hw, ry, fill, edge=True):
    """A liquid's top seen from a little above: the lit ellipse of it, and the meniscus — the dark line where it meets the front glass."""
    out = [P(f"{prefix}_surface", ell(hw, ry), tone(fill, 1), at=(0, y))]
    if edge and hw > 0.8:
        out.append(band(f"{prefix}_meniscus", _arc(0, y, hw * 0.98, ry, 175, 5, 10), min(0.36, ry * 0.7), tone(fill, -1)))
    return out


# ================================================================ test tube
def test_tube(prefix, x, y, s=1.0, rot=0.0, fill="$venom", level=0.55, cap="cork", label=False, w=4.2, h=13.0, bubble=True):
    """A stoppered test tube standing up. Origin: its foot (the lowest point of the round bottom).

    `fill` the liquid's token, `level` 0..1 of the tube, `cap` "cork" | "steel" | "none",
    `label` a bone band with two ruled strokes on it, `w`/`h` the glass (h without the cap).
    """
    t = 0.55                      # the glass wall
    top = -h
    iw = w - 2 * t
    ibot = -t
    out = [P(f"{prefix}_glass", poly(_tube(w, top, 0)), GLASS)]
    if level > 0:
        inner = _tube(iw, top + 0.3, ibot)
        ys = ibot - level * (h - t - 1.4)
        hw = _half_width(ys, iw, ibot)
        body = clip(inner, 1, ys, BIG)
        out.append(P(f"{prefix}_liquid", poly(body), fill))
        shade = clip(body, 0, iw * 0.14, BIG)
        if len(shade) >= 3:
            out.append(P(f"{prefix}_liquid_shade", poly(shade), tone(fill, -1)))
        out += _surface(prefix, ys, hw, min(0.5, hw * 0.34), fill)
        if bubble and ibot - ys > 4:
            out.append(P(f"{prefix}_bubble", circ(0.34), tone(fill, 2), at=(iw * 0.12, ys + (ibot - ys) * 0.6)))
    # Front glints: a strong narrow one down the left, a short dash where the
    # bottom turns, a thin one high on the right.
    g0, g1 = top + 1.6, -w / 2 - 0.2
    out += [
        P(f"{prefix}_glint", R(0.7, g1 - g0, 0.35), "$white@0.7", at=(-w / 2 + 0.95, (g0 + g1) / 2)),
        P(f"{prefix}_glint_low", R(0.6, 0.9, 0.3), "$white@0.45", at=(-w / 2 + 1.25, -w / 2 + 0.75), rot=-30),
        P(f"{prefix}_glint_b", R(0.35, (g1 - g0) * 0.4, 0.17), "$white@0.3", at=(w / 2 - 0.7, g0 + 0.6 + (g1 - g0) * 0.2)),
    ]
    if label:
        yl, lh = -h * 0.5, 2.8
        out += [
            *shaded(f"{prefix}_label", rr(w, lh, 0.3, (0, yl)), "$bone", [(w * 0.18, BIG, "$bone.dark")], stroke=None, axis=0),
            P(f"{prefix}_label_ln", R(w * 0.5, 0.36, 0.18), "$slate.dark@0.65", at=(-0.35, yl - 0.5)),
            P(f"{prefix}_label_ln2", R(w * 0.32, 0.36, 0.18), "$slate.dark@0.5", at=(-0.7, yl + 0.5)),
        ]
    out.append(P(f"{prefix}_rim", poly(_tube(w, top, 0)), None, stroke=INK_FINE))
    if cap == "cork":
        ct, cb = top - 2.5, top + 0.9
        tw, bw = w * 0.92, w * 0.72
        pts = [(-tw / 2, ct), (tw / 2, ct), (bw / 2, cb), (-bw / 2, cb)]
        out += [
            *shaded(f"{prefix}_cork", pts, "$husk.dark", [(-BIG, -tw * 0.16, "$husk"), (tw * 0.2, BIG, "$husk.dark2")], stroke=INK_FINE, axis=0),
            P(f"{prefix}_cork_top", ell(tw / 2, 0.45), "$husk.light", at=(0, ct), stroke=INK_FINE),
            P(f"{prefix}_cork_pore", circ(0.24), "$husk.dark2", at=(-0.5, ct + 1.3)),
            P(f"{prefix}_cork_pore_b", circ(0.2), "$husk.dark2", at=(0.7, ct + 0.8)),
        ]
    out += [
        P(f"{prefix}_lip", R(w + 0.8, 1.0, 0.5), LIP, at=(0, top + 0.1), stroke=INK_FINE),
        P(f"{prefix}_lip_lit", R(w * 0.45, 0.32, 0.16), "$white@0.6", at=(-w * 0.18, top - 0.12)),
    ]
    if cap == "steel":
        cw, ct, cb = w + 0.9, top - 1.9, top + 1.0
        out += [
            *shaded(f"{prefix}_cap", rr(cw, cb - ct, 0.6, (0, (ct + cb) / 2)), "$steel", [(-BIG, -cw * 0.2, "$steel.light"), (cw * 0.2, BIG, "$steel.dark")], stroke=INK_FINE, axis=0),
            P(f"{prefix}_cap_top", ell(cw / 2 - 0.1, 0.45), "$steel.light", at=(0, ct + 0.1), stroke=INK_FINE),
            P(f"{prefix}_cap_groove", R(cw - 0.5, 0.35, 0.17), "$ink@0.35", at=(0, cb - 0.8)),
        ]
    elif cap == "none":
        out.append(P(f"{prefix}_mouth", ell(iw / 2, 0.36), "$ink@0.55", at=(0, top - 0.05)))
    return placed(out, (x, y), s, rot)


# ================================================================ the bench's rack
RACK_FILLS = ("$venom", "$ember", "$frost", "$bile", "$aqua", "$orchid")


def tube_rack(prefix, x, y, s=1.0, rot=0.0, fills=RACK_FILLS, levels=None, caps=None, tilt=None, w=44.0):
    """The bench's rack of sample tubes. Origin: the middle of its foot, where it stands on the bench.

    A slate rack — a base with dimples, two end posts, a front rail with a hole
    for each tube — with the tubes standing through the rail onto the base.
    `fills` one token per slot (None leaves the slot empty: its hole and
    dimple show), `levels` and `caps` one per slot (defaults vary them), `tilt`
    {slot: degrees} leans a tube in its hole. Each tube is `test_tube`
    `{prefix}_t{i}`.
    """
    n = len(fills)
    hw = w / 2
    post = 2.6
    span = w - 2 * post - 1.2
    pitch = span / n
    xs = [-span / 2 + pitch * (i + 0.5) for i in range(n)]
    levels = levels or [(0.86, 0.44, 0.62, 0.36, 0.9, 0.52, 0.7)[i % 7] for i in range(n)]
    caps = caps or [("steel", "cork", "steel", "steel", "cork", "steel", "cork")[i % 7] for i in range(n)]
    heights = [(13.4, 12.8, 13.4, 13.0, 12.6, 13.4, 13.0)[i % 7] for i in range(n)]
    tilt = tilt or {}
    foot = -2.9
    rail_y = -12.0                  # the middle of the rail's top face
    out = [
        ao(f"{prefix}_ao", 0, 0.1, w - 1, 1.6, 0.45),
        # The base's top face, a dimple under each slot.
        P(f"{prefix}_base_top", R(w, 1.8, 0.6), "$slate.light", at=(0, -3.1), stroke=INK_HAIR),
        *[P(f"{prefix}_dimple_{i}", ell(2.3, 0.45), "$ink@0.4", at=(sx, -3.0)) for i, sx in enumerate(xs)],
        # The end posts the rail stands on.
        *[p for side, sx in (("l", -1), ("r", 1)) for p in [
            P(f"{prefix}_post_{side}", R(post, 8.6, 0.6), "$slate" if side == "l" else "$slate.dark", at=(sx * (hw - post / 2 - 0.4), -6.6), stroke=INK_HAIR),
        ]],
        P(f"{prefix}_post_l_lit", R(0.6, 7.0, 0.3), "$slate.light", at=(-(hw - post / 2 - 0.4) - 0.6, -6.6)),
        # The rail's top face, behind the tubes, a hole for each slot.
        P(f"{prefix}_rail_top", R(w, 1.9, 0.6), "$slate.light", at=(0, rail_y), stroke=INK_HAIR),
        *[P(f"{prefix}_hole_{i}", ell(2.55, 0.6), "$ink@0.65", at=(sx, rail_y + 0.1)) for i, sx in enumerate(xs)],
    ]
    for i, (sx, f) in enumerate(zip(xs, fills)):
        if f is None:
            continue
        out += test_tube(f"{prefix}_t{i}", sx, foot, rot=tilt.get(i, 0.0), fill=f, level=levels[i], cap=caps[i], h=heights[i], bubble=False)
    out += [
        # The rail's front face over the tubes, lit along its top edge.
        *shaded(f"{prefix}_rail", rr(w, 2.6, 0.6, (0, rail_y + 2.2)), "$slate", [(hw - 6, BIG, "$slate.dark")], stroke=INK_HAIR, axis=0),
        lit_edge(f"{prefix}_lit", -hw + 1.2, hw - 7, rail_y + 1.25, 0.6, "$slate.light2@0.7"),
        # The base's front face.
        *shaded(f"{prefix}_base", rr(w, 2.6, 0.6, (0, -1.1)), "$slate.dark", [(hw - 6, BIG, "$slate.dark2")], stroke=INK_HAIR, axis=0),
        lit_edge(f"{prefix}_base_lit", -hw + 1.2, hw - 7, -2.1, 0.5, "$slate.light@0.6"),
    ]
    return placed(out, (x, y), s, rot)


# ================================================================ the cellar's vial
def vial(prefix, x, y, s=1.0, rot=0.0, fill="$venom", level=0.62, muted=1.0, cold=False):
    """A tiny capped sample vial. Origin: its foot (flat bottom, middle).

    `fill` the sample's token, `level` 0..1, `muted` the sample's alpha (the
    cellar's cold: ~0.75 behind its frosted door), `cold` adds rime on the cap
    and along the foot.
    """
    w, h, t = 3.0, 5.6, 0.5
    body = rr(w, h, 0.8, (0, -h / 2))
    c = fill if muted >= 1 else tone(fill, 0, muted)
    out = [P(f"{prefix}_glass", poly(body), "$frost.dark@0.35")]
    if level > 0:
        inner = rr(w - 2 * t, h - 2 * t, 0.5, (0, -h / 2))
        ys = -t - level * (h - 2 * t - 0.6)
        liq = clip(inner, 1, ys, BIG)
        out += [
            P(f"{prefix}_liquid", poly(liq), c),
            P(f"{prefix}_liquid_shade", poly(clip(liq, 0, 0.15, BIG)), tone(c, -1)),
            P(f"{prefix}_surface", R(w - 2 * t, 0.5, 0.25), tone(c, 1), at=(0, ys)),
        ]
    out += [
        P(f"{prefix}_glint", R(0.55, h - 1.8, 0.27), "$white@0.6", at=(-w / 2 + 0.8, -h / 2 - 0.15)),
        P(f"{prefix}_rim", poly(body), None, stroke=INK_FINE),
        P(f"{prefix}_cap", R(w + 0.3, 1.9, 0.5), "$steel", at=(0, -h - 0.6), stroke=INK_FINE),
        P(f"{prefix}_cap_lit", R(w - 0.6, 0.5, 0.25), "$steel.light", at=(-0.2, -h - 1.15)),
        P(f"{prefix}_cap_shade", R(0.9, 1.9, 0.4), "$steel.dark", at=(w / 2 - 0.3, -h - 0.6)),
    ]
    if cold:
        out += [
            P(f"{prefix}_rime", R(w + 0.1, 0.55, 0.27), "$white@0.7", at=(0, -h - 1.45)),
            P(f"{prefix}_rime_foot", R(w - 0.6, 0.5, 0.25), "$frost.light@0.55", at=(0, -0.35)),
        ]
    return placed(out, (x, y), s, rot)


# ================================================================ the syringe
def syringe(prefix, x, y, s=1.0, rot=0.0, fill="$venom", level=0.45, drop=True):
    """A glass syringe lying on a table, needle to the left (-x). Origin: the middle of the barrel.

    Needle, hub, a glass barrel with a graduated scale and the dose in it, the
    rubber seal, the plunger rod out the back to its thumb disc, the finger
    flange. `level` 0..1 is how far the plunger is drawn (the dose runs from
    the nozzle to the seal, and the rod comes out the back as far); `drop` a
    bead of the dose at the needle's tip.
    """
    bl, br, bh = -10.0, 10.0, 5.0
    il, ir = bl + 0.6, br - 0.3
    seal_w = 1.4
    seal_x = il + level * (ir - il - seal_w)        # the seal's left face
    thumb_x = seal_x + seal_w + (ir - il) + 0.6     # the thumb disc's left face
    barrel = rr(br - bl, bh, 1.1, ((bl + br) / 2, 0))
    nozzle = [(bl + 0.3, -1.3), (bl - 1.3, -0.75), (bl - 1.3, 0.75), (bl + 0.3, 1.3)]
    out = [
        # Where it lies on the table.
        P(f"{prefix}_shadow", R(thumb_x - bl + 5, 1.8, 0.9), "$ink@0.28", at=((bl + thumb_x) / 2 - 1, bh / 2 + 0.5)),
        P(f"{prefix}_needle_shadow", R(8.0, 0.6, 0.3), "$ink@0.3", at=(bl - 7.4, 1.0)),
        # The needle and its hub.
        P(f"{prefix}_needle", poly([(bl - 3.4, -0.3), (bl - 11.0, -0.3), (bl - 12.3, 0.3), (bl - 3.4, 0.3)]), "$steel.light", stroke=INK_FINE),
        P(f"{prefix}_hub", poly([(bl - 4.2, -0.85), (bl - 1.5, -1.35), (bl - 1.5, 1.35), (bl - 4.2, 0.85)]), "$steel", stroke=INK_FINE),
        P(f"{prefix}_hub_shade", poly([(bl - 4.2, 0.2), (bl - 1.5, 0.4), (bl - 1.5, 1.35), (bl - 4.2, 0.85)]), "$steel.dark"),
        P(f"{prefix}_hub_lit", R(2.2, 0.35, 0.17), "$steel.light", at=(bl - 2.8, -0.75), rot=-8),
        # The barrel's back glass and the nozzle.
        P(f"{prefix}_nozzle", poly(nozzle), GLASS),
        P(f"{prefix}_barrel", poly(barrel), GLASS),
    ]
    L = seal_x - il
    if L > 0.2:
        liq = rr(L + 0.8, bh - 1.1, 0.6, (L / 2 - 0.4, 0))
        out += [
            P(f"{prefix}_fill", poly(liq), fill, at=(il, 0)),
            P(f"{prefix}_fill_shade", poly(clip(liq, 1, 0.75, BIG)), tone(fill, -1), at=(il, 0)),
        ]
        if L > 4:
            out.append(P(f"{prefix}_bubble", circ(0.5), tone(fill, 2), at=(il + 1.6, -0.8)))
    out += [
        # The plunger: the rod (through the glass, then out the back), the
        # rubber seal on its end, the thumb disc.
        P(f"{prefix}_rod_in", R(thumb_x - seal_x - seal_w + 0.2, 1.6, 0.4), "$steel@0.55", at=((seal_x + seal_w + thumb_x) / 2, 0)),
        P(f"{prefix}_rod", R(thumb_x - br + 0.4, 1.7, 0.4), "$steel.light", at=((br + thumb_x) / 2, 0), stroke=INK_FINE),
        P(f"{prefix}_rod_rib", R(thumb_x - br - 0.6, 0.42, 0.2), "$steel.dark", at=((br + thumb_x) / 2, 0.2)),
        P(f"{prefix}_seal", R(seal_w, bh - 1.0, 0.45), "$coal", at=(seal_x + seal_w / 2, 0)),
        P(f"{prefix}_seal_rib", R(0.35, bh - 1.0, 0.17), "$smoke", at=(seal_x + seal_w / 2, 0)),
    ]
    # The scale printed on the glass: a comb of ticks, long every fifth.
    ticks = [il + 1.1 + k * 1.6 for k in range(11)]
    comb = [(ticks[0] - 0.15, -1.25), (ticks[-1] + 0.15, -1.25)]
    for k, tx in reversed(list(enumerate(ticks))):
        d = 0.75 if k % 5 == 0 else 0.15
        comb += [(tx + 0.15, -0.95), (tx + 0.15, -0.95 + d + 0.4), (tx - 0.15, -0.95 + d + 0.4), (tx - 0.15, -0.95)]
    out += [
        P(f"{prefix}_marks", poly(comb), "$ink@0.5"),
        # Front glints: strong along the top, thin along the bottom.
        P(f"{prefix}_glint", R(ir - il - 3.5, 0.6, 0.3), "$white@0.7", at=((il + ir) / 2 - 0.8, -1.8)),
        P(f"{prefix}_glint_b", R((ir - il) * 0.45, 0.35, 0.17), "$white@0.3", at=((il + ir) / 2 + 2.5, 1.85)),
        P(f"{prefix}_nozzle_rim", poly(nozzle), None, stroke=INK_FINE),
        P(f"{prefix}_barrel_rim", poly(barrel), None, stroke=INK_FINE),
        # The finger flange at the open end, and the thumb disc.
        P(f"{prefix}_flange", R(1.3, 7.6, 0.6), "$steel", at=(br + 0.5, 0), stroke=INK_FINE),
        P(f"{prefix}_flange_lit", R(0.45, 6.0, 0.22), "$steel.light", at=(br + 0.2, -0.3)),
        P(f"{prefix}_thumb", R(1.3, 6.2, 0.6), "$steel", at=(thumb_x + 0.65, 0), stroke=INK_FINE),
        P(f"{prefix}_thumb_lit", R(0.45, 4.8, 0.22), "$steel.light", at=(thumb_x + 0.35, -0.3)),
    ]
    if drop:
        out += [
            P(f"{prefix}_drop", ell(0.75, 0.6), fill, at=(bl - 12.4, 0.75), stroke=INK_FINE),
            P(f"{prefix}_drop_lit", circ(0.22), "$white@0.7", at=(bl - 12.6, 0.55)),
        ]
    return placed(out, (x, y), s, rot)


# ================================================================ jars
def _jar_outline(w, h):
    """A jar's glass, centred: a neck at the top, a rounded shoulder out to the body, rounded bottom corners."""
    nw = w * 0.74
    nh = max(0.9, h * 0.09)
    sh = max(1.0, h * 0.12)
    top = -h / 2
    yn, ys = top + nh, top + nh + sh
    cb = min(w, h) * 0.2
    left = [(-nw / 2 - (w - nw) / 2 * math.sin(a), yn + (ys - yn) * (1 - math.cos(a))) for a in [i * math.pi / 12 for i in range(7)]]
    right = [(-px, py) for px, py in reversed(left)]
    return (
        [(-nw / 2, top)] + left
        + _arc(-w / 2 + cb, h / 2 - cb, cb, cb, 180, 90, 5)
        + _arc(w / 2 - cb, h / 2 - cb, cb, cb, 90, 0, 5)
        + right + [(nw / 2, top)]
    ), nw, yn, ys


def jar(prefix, x, y, w=14.0, h=16.0, contents=(), behind=(), lid="screw", bail=False, vents=0, inner=None, s=1.0, rot=0.0):
    """A glass jar with a lid. Origin: the middle of the glass (the lid sits above it).

    Layered back glass -> `contents` -> front glints and ink rim -> lid ->
    bail. `contents` and `behind` are parts the caller draws about the same
    origin (a jar's middle at 0, 0; its inside floor at about y = h/2 - 1.2):
    `behind` goes under everything (a halo), `contents` between the back and
    front glass, and both are placed, scaled and turned with the jar. `lid`
    "screw" (thread bands) | "cork" | "none"; `bail` a wire bail over the lid
    (for hanging: its top is `jar_bail_top(w, h)`); `vents` holes in a screw
    lid; `inner` a wash inside the glass, e.g. "$spore@0.14" when it holds
    glowing caps.
    """
    k = w / 14
    ink = INK_HAIR if w >= 9 else INK_FINE
    body, nw, yn, ys = _jar_outline(w, h)
    top = -h / 2
    out = list(behind)
    out.append(P(f"{prefix}_glass", poly(body), GLASS))
    if inner:
        ib, *_ = _jar_outline(w - 1.4 * k, h - 1.4 * k)
        out.append(P(f"{prefix}_inner", poly(ib), inner))
    # The thick bottom, seen through the front.
    out.append(P(f"{prefix}_floor", ell(w / 2 - 1.3 * k, max(0.5, 1.0 * k)), "$frost@0.2", at=(0, h / 2 - 1.3 * k)))
    out += list(contents)
    gx = -w / 2 + 2.0 * k
    g0, g1 = ys + 0.6 * k, h / 2 - 3.6 * k
    out += [
        P(f"{prefix}_glint", R(1.3 * k, (g1 - g0) * 0.72, 0.65 * k), "$white@0.5", at=(gx, g0 + (g1 - g0) * 0.36)),
        P(f"{prefix}_glint_dash", R(1.3 * k, (g1 - g0) * 0.12, 0.65 * k), "$white@0.42", at=(gx, g0 + (g1 - g0) * 0.88)),
        band(f"{prefix}_glint_shoulder", [(px + 1.1 * k, py + 0.7 * k) for px, py in _jar_outline(w, h)[0][2:6]], 0.8 * k, "$white@0.4"),
        P(f"{prefix}_glint_b", R(0.6 * k, (g1 - g0) * 0.4, 0.3 * k), "$white@0.24", at=(w / 2 - 1.5 * k, g0 + (g1 - g0) * 0.66)),
        P(f"{prefix}_foot_lit", R(w - 3.4 * k, 0.6 * k, 0.3 * k), "$frost.light@0.35", at=(0, h / 2 - 0.75 * k)),
        P(f"{prefix}_rim", poly(body), None, stroke=ink),
        # The glass lip the lid screws onto.
        P(f"{prefix}_lip", R(nw + 0.6 * k, max(0.6, 0.9 * k), 0.4 * k), "$frost@0.32", at=(0, yn - 0.1 * k), stroke=INK_FINE),
    ]
    if lid == "screw":
        lw, lh = nw + 1.3 * k, max(2.0, 3.4 * k)
        lb = top + 0.5 * k
        lc = lb - lh / 2
        out += [
            *shaded(f"{prefix}_lid", rr(lw, lh, 0.7 * k, (0, lc)), "$steel", [(lw * 0.24, BIG, "$steel.dark")], stroke=ink, axis=0),
            P(f"{prefix}_lid_top", R(lw - 0.9 * k, max(0.5, 0.8 * k), 0.4 * k), "$steel.light", at=(0, lb - lh + 0.75 * k)),
            *[P(f"{prefix}_thread_{i}", R(lw - 0.3 * k, max(0.3, 0.42 * k), 0.2 * k), "$ink@0.32", at=(0, lb - lh * f))
              for i, f in enumerate((0.42, 0.18) if lh >= 2.6 else (0.3,))],
            *[P(f"{prefix}_vent_{i}", circ(0.5 * k), "$slate.dark", at=((i - (vents - 1) / 2) * 3.6 * k, lb - lh + 0.75 * k)) for i in range(vents)],
        ]
    elif lid == "cork":
        tw, bw, ct, cb = nw + 0.8 * k, nw - 0.4 * k, top - 2.6 * k, top + 1.2 * k
        out += [
            *shaded(f"{prefix}_cork", [(-tw / 2, ct), (tw / 2, ct), (bw / 2, cb), (-bw / 2, cb)], "$husk.dark", [(-BIG, -tw * 0.18, "$husk"), (tw * 0.22, BIG, "$husk.dark2")], stroke=ink, axis=0),
            P(f"{prefix}_cork_top", ell(tw / 2, 0.7 * k), "$husk.light", at=(0, ct), stroke=INK_FINE),
        ]
    else:
        out.append(P(f"{prefix}_mouth", ell(nw / 2 - 0.3 * k, 0.6 * k), "$ink@0.5", at=(0, top)))
    if bail:
        r, py = nw / 2 + 1.6 * k, yn
        out += [
            P(f"{prefix}_bail", ring_arc(r, 0.8 * k, 180, 360), "$steel.dark", at=(0, py)),
            P(f"{prefix}_bail_lit", ring_arc(r, 0.35 * k, 200, 245), "$steel.light@0.8", at=(0, py)),
            P(f"{prefix}_collar", R(nw + 0.9 * k, 0.8 * k, 0.4 * k), "$steel.dark", at=(0, py + 0.1 * k)),
            *[P(f"{prefix}_bail_{side}", circ(0.75 * k), "$steel", at=(sx * r, py), stroke=INK_FINE) for side, sx in (("l", -1), ("r", 1))],
        ]
    return placed(out, (x, y), s, rot)


def jar_bail_top(w=14.0, h=16.0):
    """Where a jar's bail peaks, relative to the jar's origin at s=1: hang the hook or the cord here."""
    k = w / 14
    _, nw, yn, _ = _jar_outline(w, h)
    return (0.0, yn - (nw / 2 + 1.6 * k) - 0.4 * k)


def jar_fill(prefix, w=14.0, h=16.0, fill="$gold", level=0.3):
    """Contents for `jar(...)`: a liquid or a jelly standing in a jar of the same w, h — its shade band and its surface. About the jar's origin."""
    k = w / 14
    t = 0.75 * k
    ib, _, _, ys_ = _jar_outline(w - 2 * t, h - 2 * t)
    floor = h / 2 - t
    ys = floor - level * (floor - ys_)
    liq = clip(ib, 1, ys, BIG)
    hw = (w - 2 * t) / 2 * 0.98
    return [
        P(f"{prefix}_liquid", poly(liq), fill),
        P(f"{prefix}_liquid_shade", poly(clip(liq, 0, hw * 0.3, BIG)), tone(fill, -1)),
        *_surface(prefix, ys, hw, max(0.5, 0.9 * k), fill),
        P(f"{prefix}_shine", ell(1.2 * k, 0.5 * k), tone(fill, 2), at=(-hw * 0.4, ys + (floor - ys) * 0.5)),
    ]


# ================================================================ the spent cartridge
def cartridge(prefix, x, y, s=1.0, rot=0.0, residue="$husk.dark", mark=0.38):
    """An emitter cartridge, spent: frost glass between two steel end caps, empty, a dried ring where the compound stood. Origin: its middle.

    `residue` the dried compound's token, `mark` how high the ring stands (0..1 of the glass).
    """
    w, gh, t = 3.0, 8.6, 0.45
    bot, top = gh / 2, -gh / 2
    yr = bot - mark * gh
    iw = w - 2 * t
    out = [
        P(f"{prefix}_glass", R(w, gh, 0.4), GLASS),
        # What is left: the glass stained to where the compound stood, the
        # ring it dried at (with a run down from it), a crust on the floor.
        P(f"{prefix}_stain", R(iw, bot - yr - 0.2, 0.3), tone(residue, 0, 0.16), at=(0, (yr + bot) / 2)),
        band(f"{prefix}_ring_back", _arc(0, yr, iw / 2, 0.38, 185, 355, 6), 0.3, tone(residue, 0, 0.5)),
        band(f"{prefix}_ring", _arc(0, yr, iw / 2, 0.38, 175, 5, 6), 0.5, tone(residue, 0, 0.95)),
        P(f"{prefix}_run", R(0.32, 0.9, 0.16), tone(residue, 0, 0.6), at=(0.35, yr + 0.85)),
        P(f"{prefix}_crust", R(iw, 0.7, 0.3), tone(residue, -1, 0.9), at=(0, bot - 0.45)),
        P(f"{prefix}_glint", R(0.6, gh - 2.0, 0.3), "$white@0.65", at=(-w / 2 + 0.8, -0.2)),
        P(f"{prefix}_glint_b", R(0.32, gh * 0.4, 0.16), "$white@0.3", at=(w / 2 - 0.65, -gh * 0.15)),
        P(f"{prefix}_rim", R(w, gh, 0.4), None, stroke=INK_FINE),
    ]
    for end, cy, sgn in (("top", top - 0.3, -1), ("bot", bot + 0.3, 1)):
        out += [
            *shaded(f"{prefix}_{end}", rr(w + 0.6, 2.0, 0.5, (0, cy)), "$steel", [(-BIG, -0.7, "$steel.light"), (0.8, BIG, "$steel.dark")], stroke=INK_FINE, axis=0),
            P(f"{prefix}_{end}_seam", R(w + 0.2, 0.3, 0.15), "$ink@0.4", at=(0, cy - sgn * 0.45)),
        ]
    out += [
        # The outlet the compound went out of, on top; a contact stud below.
        P(f"{prefix}_outlet", R(1.2, 1.1, 0.3), "$steel.dark", at=(0, top - 1.75), stroke=INK_FINE),
        P(f"{prefix}_stud", R(1.4, 0.7, 0.3), "$steel.dark", at=(0, bot + 1.55), stroke=INK_FINE),
    ]
    return placed(out, (x, y), s, rot)
