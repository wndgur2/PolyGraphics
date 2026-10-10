"""Playmore's documents: the big-head creature, its skins, the accessories that sit on it, the chip and the role cards.

    python3 scripts/playmore.py        # rewrites apps/playmore/assets/*.json

The creature is one round head-and-body blob on four stubby legs, front-facing,
outlined in `$ink` (#2b2233). It replaces the hand-coded canvas avatar in the
Playmore repo (`packages/stage/src/avatar.ts`), whose 100-unit drawing every
number here is ported from at 0.9 scale (`T()` below), so the two read as the
same character.

The contract the consumer is written against, and so the one thing here that
must not drift:

  * `playmore.char.body` is 96x96, anchor [0.5, 0.5]: the origin is the canvas
    centre, the head's centre sits at (0, 2), the feet stand on y = 44
    (`meta.footY`), and there is headroom above the head for a hat.
  * Two sockets, both riding the `head` part: `head` at (0, -28), the top of
    the head where a hat sits, and `face` at (0, 0), the middle of the eye line
    where glasses and masks sit.
  * Every accessory is its own document, 80x56, anchor [0.5, 0.5], drawn at the
    body's scale with its origin AT the socket it names. Placing the
    accessory's origin on `socketAt(body, name)` at the same scale is the whole
    of attaching it.

Flat fills only: the Phaser adapter draws a gradient as its middle stop, so
value changes are separate shapes (the belly shade is a crescent clipped out of
the head, not a gradient).
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "apps", "playmore", "assets")

# ---------------------------------------------------------------- small helpers


def r2(x):
    return round(x + 0.0, 2)


def T(x, y):
    """The temporary avatar's 100-unit frame (head centre at 50,48) → body space (head centre at 0,2)."""
    return ((x - 50) * 0.9, (y - 48) * 0.9 + 2)


def poly(pts):
    return {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in pts]}


def ell(rx, ry):
    return {"kind": "ellipse", "rx": r2(rx), "ry": r2(ry)}


def circ(r):
    return {"kind": "circle", "r": r2(r)}


def rect(w, h, c=None):
    s = {"kind": "rect", "w": r2(w), "h": r2(h)}
    if c:
        s["corner"] = r2(c)
    return s


def ring(r, w, a0=None, a1=None):
    s = {"kind": "ring", "r": r2(r), "width": r2(w)}
    if a0 is not None:
        s["from"], s["to"] = a0, a1
    return s


def star(points, r, r2_, rot=None):
    s = {"kind": "star", "points": points, "r": r2(r), "r2": r2(r2_)}
    if rot:
        s["rot"] = rot
    return s


OUTLINE = {"color": "$ink", "width": "outline"}  # 6 laid under the fill → a 3-unit rim
LINE = {"color": "$ink", "width": "line"}  # 3 → 1.5 rim, for the small bits


def P(id, shape, fill=None, at=(0, 0), stroke=None, opacity=None, rot=None, mirror=False, scale=None):
    p = {"id": id}
    if tuple(at) != (0, 0):
        p["at"] = [r2(at[0]), r2(at[1])]
    if rot:
        p["rot"] = r2(rot)
    if scale is not None:
        p["scale"] = scale
    if opacity is not None:
        p["opacity"] = opacity
    if mirror:
        p["mirrorX"] = True
    p["shape"] = shape
    if fill is not None:
        p["fill"] = fill
    if stroke:
        p["stroke"] = stroke
    return p


def U(id, asset, at=(0, 0), scale=None, variant=None, opacity=None, rot=None):
    p = {"id": id}
    if tuple(at) != (0, 0):
        p["at"] = [r2(at[0]), r2(at[1])]
    if rot:
        p["rot"] = r2(rot)
    if scale is not None:
        p["scale"] = scale
    if opacity is not None:
        p["opacity"] = opacity
    p["use"] = asset
    if variant:
        p["variant"] = variant
    return p


def ellipse_pts(cx, cy, rx, ry, n=48, a0=0.0, a1=360.0):
    out = []
    for k in range(n + 1 if (a1 - a0) < 360 else n):
        a = math.radians(a0 + (a1 - a0) * k / n)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def clip_convex(subject, clipper):
    """Sutherland–Hodgman: `subject` clipped to the convex polygon `clipper` (both lists of points)."""

    def side(a, b, p):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

    # orientation of the clipper
    area = sum(clipper[i - 1][0] * clipper[i][1] - clipper[i][0] * clipper[i - 1][1] for i in range(len(clipper)))
    sgn = 1 if area > 0 else -1
    out = list(subject)
    for i in range(len(clipper)):
        a, b = clipper[i - 1], clipper[i]
        inp, out = out, []
        if not inp:
            break
        for j in range(len(inp)):
            cur, prev = inp[j], inp[j - 1]
            cin, pin = sgn * side(a, b, cur) >= 0, sgn * side(a, b, prev) >= 0
            if cin:
                if not pin:
                    out.append(cross(prev, cur, a, b))
                out.append(cur)
            elif pin:
                out.append(cross(prev, cur, a, b))
    return out


def cross(p, q, a, b):
    x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
    x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def star_pts(cx, cy, r, ri, points=5, rot=0.0):
    out = []
    for i in range(points * 2):
        a = math.radians(rot - 90 + i * 180 / points)
        rr = r if i % 2 == 0 else ri
        out.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return out


def heart_pts(cx, cy, s, n=40):
    """A heart `s` units across, centred on (cx, cy), point down."""
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        out.append((cx + x * s / 34, cy + (y + 2) * s / 34))
    return out


def track(part, prop, keys):
    return {"part": part, "prop": prop, "keys": keys}


def one(v):
    return json.dumps(v, ensure_ascii=False)


def write_doc(doc):
    """One part, one track, one set-entry to a line — the house layout."""
    L = ["{"]
    for k in ("id", "name", "description", "tags", "size", "anchor", "meta", "why"):
        if k in doc:
            L.append(f'  "{k}": {one(doc[k])},')
    L.append('  "parts": [')
    L.append(",\n".join(f"    {one(p)}" for p in doc["parts"]))
    tail = []
    if doc.get("variants"):
        vs = []
        for name, v in doc["variants"].items():
            body = [f"    {one(name)}: {{", f'      "description": {one(v["description"])}']
            for k in ("scale", "animations", "remove"):
                if k in v:
                    body[-1] += ","
                    body.append(f'      "{k}": {one(v[k])}')
            if v.get("add"):
                body[-1] += ","
                body.append('      "add": [')
                body.append(",\n".join(f"        {one(p)}" for p in v["add"]))
                body.append("      ]")
            if v.get("set"):
                body[-1] += ","
                body.append('      "set": {')
                body.append(",\n".join(f"        {one(k)}: {one(val)}" for k, val in v["set"].items()))
                body.append("      }")
            body.append("    }")
            vs.append("\n".join(body))
        tail.append('  "variants": {\n' + ",\n".join(vs) + "\n  }")
    if doc.get("animations"):
        anims = []
        for name, a in doc["animations"].items():
            body = [f"    {one(name)}: {{", f'      "description": {one(a["description"])},', f'      "duration": {one(a["duration"])},']
            if a.get("cues"):
                body.append(f'      "cues": {one(a["cues"])},')
            body.append('      "tracks": [')
            body.append(",\n".join(f"        {one(t)}" for t in a["tracks"]))
            body.append("      ]")
            body.append("    }")
            anims.append("\n".join(body))
        tail.append('  "animations": {\n' + ",\n".join(anims) + "\n  }")
    if doc.get("skeleton"):
        sk = doc["skeleton"]
        s = ['  "skeleton": {', '    "joints": {']
        s.append(",\n".join(f"      {one(k)}: {one(v)}" for k, v in sk["joints"].items()))
        s.append("    },")
        s.append(f'    "bones": {one(sk["bones"])}' + ("," if sk.get("sockets") else ""))
        if sk.get("sockets"):
            s.append('    "sockets": {')
            s.append(",\n".join(f"      {one(k)}: {one(v)}" for k, v in sk["sockets"].items()))
            s.append("    }")
        s.append("  }")
        tail.append("\n".join(s))
    L[-1] += "\n  ]" + ("," if tail else "")
    L.append(",\n".join(tail)) if tail else None
    L.append("}")
    path = os.path.join(OUT, doc["id"].replace(".", "-") + ".json")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    return path


# ---------------------------------------------------------------- the creature's numbers

HEAD_C = (0.0, 2.0)  # head centre in body space
HEAD_RX, HEAD_RY = 34.0, 30.0
HEAD_TOP = (0.0, HEAD_C[1] - HEAD_RY)  # (0, -28): the `head` socket
EYE_LINE = (0.0, 0.0)  # the `face` socket
FOOT_Y = 44.0

# Skins: base fill, shade (back legs, belly), and a pattern on the head.
SKINS = {
    "peach": dict(desc="Warm peach, the default skin."),
    "sky": dict(desc="Pale sky blue."),
    "mint": dict(desc="Soft mint green."),
    "lemon": dict(desc="Butter yellow."),
    "lilac": dict(desc="Light lilac."),
    "coral": dict(desc="Salmon coral."),
    "cocoa": dict(desc="Milk-chocolate brown."),
    "snow": dict(desc="Near-white with a cool grey shade."),
    "spots": dict(desc="Cream with dark-brown spots, like a cow or a dalmatian.", pattern="spots", ink="$spots-mark"),
    "stripes": dict(desc="Marigold with slanted orange tiger stripes.", pattern="stripes", ink="$stripes-mark"),
    "stars": dict(desc="Periwinkle blue scattered with yellow stars.", pattern="stars", ink="$stars-mark"),
    "night": dict(desc="Midnight navy scattered with pale stars — the night sky.", pattern="stars", ink="$night-mark"),
}

HEAD_PTS = ellipse_pts(HEAD_C[0], HEAD_C[1], HEAD_RX, HEAD_RY, n=64)


def rel(p):
    """Body space → the head's own frame (the `head`/`face` parts sit at HEAD_C)."""
    return (p[0] - HEAD_C[0], p[1] - HEAD_C[1])


def head_clip(pts):
    return [rel(p) for p in clip_convex(pts, HEAD_PTS)]


def pattern_parts(kind, ink):
    parts = []
    if kind == "spots":
        for i, (x, y, r) in enumerate([(-19, -13, 6.2), (20, -18, 5), (27, -5, 5), (-24, 20, 4.6), (5, -22, 3.8), (12, 24, 3.2), (-30, 2, 3)]):
            pts = head_clip(ellipse_pts(x, y, r, r * 0.92, n=20))
            parts.append(P(f"spot_{i + 1}", poly(pts), ink))
    elif kind == "stripes":
        # slanted bands, 6 units thick at the temp art's 18-unit pitch, clipped to the head
        for i, x in enumerate([-34, -18, -2, 14, 30]):
            top, bot = (x + 6, -32), (x - 6, 36)
            dx, dy = bot[0] - top[0], bot[1] - top[1]
            L = math.hypot(dx, dy)
            nx, ny = -dy / L * 2.8, dx / L * 2.8
            band = [(top[0] + nx, top[1] + ny), (bot[0] + nx, bot[1] + ny), (bot[0] - nx, bot[1] - ny), (top[0] - nx, top[1] - ny)]
            pts = head_clip(band)
            if len(pts) >= 3:
                parts.append(P(f"stripe_{i + 1}", poly(pts), ink))
    elif kind == "stars":
        for i, (x, y, r, rot) in enumerate([(-21, -15, 5, -8), (19, -19, 4, 10), (28.5, -1, 3.6, -14), (-28, 6, 3.4, 12), (1, -23, 3.4, 0), (22, 20, 3, 6), (-14, 23, 2.6, -10)]):
            pts = head_clip(star_pts(x, y, r, r * 0.48, rot=rot))
            parts.append(P(f"star_{i + 1}", poly(pts), ink))
    return parts


# belly shade: the temp art's ellipse(50,78,40,14) at 45%, clipped to the head
BELLY = head_clip(ellipse_pts(*T(50, 78), 36, 12.6, n=48))


def lib_skin():
    variants = {}
    for name, s in SKINS.items():
        v = {"description": s["desc"]}
        if name != "peach":
            v["set"] = {"blob.fill": f"${name}", "belly.fill": f"${name}-shade@0.45"}
        if s.get("pattern"):
            v["add"] = pattern_parts(s["pattern"], s["ink"])
        variants[name] = v
    # the pattern draws over the blob; the belly shade has to stay on top of it
    for name, v in variants.items():
        if v.get("add"):
            v["remove"] = ["belly"]
            v["add"] = v["add"] + [P("belly", poly(BELLY), f"${name}-shade@0.45")]
            v["set"] = {"blob.fill": f"${name}"}
    return {
        "id": "playmore.lib.skin",
        "name": "Skin",
        "description": "The creature's head-and-body blob in its own frame (origin = the blob's centre): one big ellipse in the skin colour with the thick ink rim, the skin's pattern clipped inside it, and a flat crescent of the shade colour across the bottom. A variant per skin, named exactly as the body's. Composed by `playmore.char.body` as its `head` part; not meant to be drawn on its own.",
        "tags": ["lib", "creature"],
        "size": [76, 68],
        "parts": [
            P("blob", ell(HEAD_RX, HEAD_RY), "$peach", stroke=OUTLINE),
            P("belly", poly(BELLY), "$peach-shade@0.45"),
        ],
        "variants": variants,
    }


def body():
    hc = HEAD_C
    legs = [
        # id, x, centre y, h, fill — back legs inner, darker, shorter; front legs outer, lighter, standing on footY
        ("leg_bl", -15.3, 32, 20, "$peach-shade"),
        ("leg_br", 15.3, 32, 20, "$peach-shade"),
        ("leg_fl", -23.4, 33, 22, "$peach"),
        ("leg_fr", 23.4, 33, 22, "$peach"),
    ]
    parts = [P(i, rect(9, h, 4.5), f, at=(x, y), stroke=OUTLINE) for i, x, y, h, f in legs]
    # The face is drawn on the body rather than composed, so a clip can reach the eyes (blink,
    # squint) and the mouth (a bigger smile). Every part above the legs is "head" and follows it.
    ex, ey = 11.7, EYE_LINE[1]
    mouth = (0.0, T(50, 55)[1])  # (0, 8.3)
    face = [
        # id, at, shape, fill
        ("blush_l", (-19.8, 10), ell(5.4, 3.2), "$blush@0.45"),
        ("blush_r", (19.8, 10), ell(5.4, 3.2), "$blush@0.45"),
        ("eye_l", (-ex, ey), ell(3.6, 4.5), "$ink"),
        ("eye_r", (ex, ey), ell(3.6, 4.5), "$ink"),
        ("glint_l", (-ex + 1.2, ey - 1.6), circ(1.3), "$white"),
        ("glint_r", (ex + 1.2, ey - 1.6), circ(1.3), "$white"),
        ("mouth", mouth, ring(5.4, 3, 36, 144), "$ink"),
    ]
    parts.append(U("head", "playmore.lib.skin", at=hc))
    parts += [P(i, s, f, at=at) for i, at, s, f in face]
    variants = {}
    for name, s in SKINS.items():
        v = {"description": s["desc"] + (" Same as the base." if name == "peach" else "")}
        if name != "peach":
            v["set"] = {
                "head.variant": name,
                "leg_bl.fill": f"${name}-shade",
                "leg_br.fill": f"${name}-shade",
                "leg_fl.fill": f"${name}",
                "leg_fr.fill": f"${name}",
            }
        variants[name] = v

    # Each face part rides the head: it moves with the head's centre, and when the head squashes
    # about its centre the part is carried to where the squash puts its spot on the head.
    rest = {"head": (0.0, 0.0)}
    for i, at, _, _ in face:
        rest[i] = (at[0] - hc[0], at[1] - hc[1])

    def head_tracks(keys):
        """keys: [(t, dx, dy, sx, sy)] for the head → x/y on every head part, scaleX/scaleY on the head."""
        out = []
        for pid, (px, py) in rest.items():
            xs = [[t, r2(dx + px * (sx - 1))] for t, dx, dy, sx, sy in keys]
            ys = [[t, r2(dy + py * (sy - 1))] for t, dx, dy, sx, sy in keys]
            if any(v for _, v in xs):
                out.append(track(pid, "x", xs))
            out.append(track(pid, "y", ys))
        if any(sx != 1 or sy != 1 for _, _, _, sx, sy in keys):
            out.append(track("head", "scaleX", [[t, sx] for t, _, _, sx, _ in keys]))
            out.append(track("head", "scaleY", [[t, sy] for t, _, _, _, sy in keys]))
        return out

    # idle: two slow breaths (rise and stretch tall, settle wide) and one blink, across 3.2s
    idle = head_tracks([(0, 0, 0, 1.02, 0.98), (0.25, 0, -1.4, 0.995, 1.01), (0.5, 0, 0, 1.02, 0.98), (0.75, 0, -1.4, 0.995, 1.01), (1, 0, 0, 1.02, 0.98)])
    blink = [[0, 1], [0.62, 1], [0.645, 0.12], [0.67, 0.12], [0.7, 1], [1, 1]]
    idle += [track("eye_l", "scaleY", blink), track("eye_r", "scaleY", blink)]
    gl = [[0, 1, "hold"], [0.62, 1, "hold"], [0.64, 0, "hold"], [0.69, 1], [1, 1]]
    idle += [track("glint_l", "opacity", gl), track("glint_r", "opacity", gl)]

    # walk: diagonal pairs step in turn (front-left with back-right); the head bobs on each step
    # and sways toward the foot that is down
    lift = -3.2
    walk = [
        track("leg_fl", "y", [[0, 0], [0.25, lift], [0.5, 0], [1, 0]]),
        track("leg_br", "y", [[0, 0], [0.25, lift], [0.5, 0], [1, 0]]),
        track("leg_fr", "y", [[0, 0], [0.5, 0], [0.75, lift], [1, 0]]),
        track("leg_bl", "y", [[0, 0], [0.5, 0], [0.75, lift], [1, 0]]),
    ]
    walk += head_tracks([(0, 0, 0.6, 1, 1), (0.25, 1.3, -1.6, 1, 1), (0.5, 0, 0.6, 1, 1), (0.75, -1.3, -1.6, 1, 1), (1, 0, 0.6, 1, 1)])

    # cheer: crouch, spring up squinting with a big smile and the front feet kicked out, land
    # with a squash, settle
    cheer = head_tracks([(0, 0, 0, 1, 1), (0.14, 0, 3.2, 1.09, 0.9), (0.3, 0, -6, 0.95, 1.07), (0.42, 0, -11, 0.97, 1.04),
                         (0.7, 0, 1.5, 1.07, 0.93), (0.82, 0, 0, 1, 1), (1, 0, 0, 1, 1)])
    ly = [[0, 0], [0.14, 0], [0.42, -9], [0.7, 0], [1, 0]]
    for leg in ("leg_bl", "leg_br", "leg_fl", "leg_fr"):
        cheer.append(track(leg, "y", ly))
    cheer.append(track("leg_fl", "rot", [[0, 0], [0.14, 0], [0.42, 14], [0.7, 0], [1, 0]]))
    cheer.append(track("leg_fr", "rot", [[0, 0], [0.14, 0], [0.42, -14], [0.7, 0], [1, 0]]))
    squint = [[0, 0.5], [1, 0.5]]
    cheer += [track("eye_l", "scaleY", squint), track("eye_r", "scaleY", squint)]
    cheer += [track("glint_l", "opacity", [[0, 0], [1, 0]]), track("glint_r", "opacity", [[0, 0], [1, 0]])]
    cheer.append(track("mouth", "scale", [[0, 1.45], [1, 1.45]]))
    cheer += [track("blush_l", "scale", [[0, 1.2], [1, 1.2]]), track("blush_r", "scale", [[0, 1.2], [1, 1.2]])]

    return {
        "id": "playmore.char.body",
        "name": "Creature",
        "description": "The player character: a chunky big-head creature, front-facing — one round head-and-body blob with the face on it (two dark eyes with white glints, pink blush, a small smile) standing on four stubby legs, the back pair inner and a shade darker, all outlined in thick `$ink`. 96x96, origin at the canvas centre; the head's centre is (0, 2), the feet stand on y = 44 (`meta.footY`), and the space above the head is headroom for a hat. Skins are variants (base = `peach`). Accessories are separate documents placed at two sockets that ride the head through every clip: `head` (0, -28), the top of the head, for hats, bows and headbands; `face` (0, 0), the middle of the eye line, for glasses, shades and masks.",
        "tags": ["char", "player"],
        "size": [96, 96],
        "anchor": [0.5, 0.5],
        "meta": {"footY": FOOT_Y},
        "parts": parts,
        "variants": variants,
        "animations": {
            "idle": {"description": "Standing: two slow breaths (the head rises a little and stretches tall, then settles wide) and one blink.", "duration": 3.2, "tracks": idle},
            "walk": {"description": "Walking on the spot, facing the viewer: the legs step in diagonal pairs, the head bobs on every step and sways side to side.", "duration": 0.6, "tracks": walk},
            "cheer": {"description": "Happy hop: crouch, spring up squinting with a big smile and the front feet kicked out, land with a squash, settle. Loops; the cues name the takeoff, the top of the hop and the landing.", "duration": 0.8, "cues": {"takeoff": 0.14, "peak": 0.42, "land": 0.7}, "tracks": cheer},
        },
        "skeleton": {
            "joints": {
                "head_centre": [hc[0], hc[1]],
                "head_top": [HEAD_TOP[0], HEAD_TOP[1]],
                "eye_line": [EYE_LINE[0], EYE_LINE[1]],
                "hip_bl": [-15.3, 22], "foot_bl": [-15.3, 42],
                "hip_br": [15.3, 22], "foot_br": [15.3, 42],
                "hip_fl": [-23.4, 22], "foot_fl": [-23.4, FOOT_Y],
                "hip_fr": [23.4, 22], "foot_fr": [23.4, FOOT_Y],
            },
            "bones": [["head_centre", "head_top"], ["head_centre", "eye_line"],
                      ["hip_bl", "foot_bl"], ["hip_br", "foot_br"], ["hip_fl", "foot_fl"], ["hip_fr", "foot_fr"]],
            "sockets": {
                "head": {"joint": "head_top", "part": "head"},
                "face": {"joint": "eye_line", "part": "head"},
            },
        },
    }


# ---------------------------------------------------------------- accessories
#
# Every accessory: 80x56, anchor [0.5, 0.5], origin = the socket point, body scale.
# `H(x, y)` and `F(x, y)` take a point in the temp art's 100-unit frame to the
# head socket's frame and the face socket's frame respectively.


def H(x, y):
    bx, by = T(x, y)
    return (bx - HEAD_TOP[0], by - HEAD_TOP[1])


def F(x, y):
    bx, by = T(x, y)
    return (bx - EYE_LINE[0], by - EYE_LINE[1])


ACC_SIZE = [80, 56]


def acc(name, title, socket, desc, parts):
    return {
        "id": f"playmore.acc.{name}",
        "name": title,
        "description": f"{desc} Socket: `{socket}` — place this document's origin on the body's `{socket}` socket at the body's scale.",
        "tags": ["acc", socket],
        "size": ACC_SIZE,
        "anchor": [0.5, 0.5],
        "parts": parts,
    }


def half_dome(cx, cy, rx, ry, n=28):
    return ellipse_pts(cx, cy, rx, ry, n=n, a0=180, a1=360)


def accessories():
    docs = []
    # cap: a red dome sitting on the crown of the head, peak out to the right, a button on top
    cx, cy = H(50, 22)
    dome = half_dome(cx, cy, 23.4, 12.6)
    docs.append(acc("cap", "Cap", "head", "Red baseball cap: a dome over the top of the head with a seam and a button, and a darker peak sticking out to the right.", [
        P("crown", poly(dome), "$cap", stroke=OUTLINE),
        P("seam", rect(1.6, 10.5, 0.8), "$cap-dark", at=(cx + 1, cy - 6)),
        P("panel_shine", poly(clip_convex(ellipse_pts(cx - 10, cy - 7.5, 5.5, 3.2, n=16), dome)), "$white@0.35"),
        P("button", circ(2), "$cap-dark", at=(cx, cy - 12.6), stroke=LINE),
        P("peak", ell(16.2, 4.2), "$cap-dark", at=(cx + 18, cy + 0.4), rot=-6, stroke=OUTLINE),
    ]))
    # beanie: a blue knit dome with a ribbed cuff and a white pompom, pulled down a little lower than the cap
    cx, cy = H(50, 22)
    cy += 3
    dome = half_dome(cx, cy, 25.2, 16.2)
    ribs = []
    for i, x in enumerate([-15, -7.5, 0, 7.5, 15]):
        rib = [(x - 0.9, cy - 20), (x + 0.9, cy - 20), (x + 0.9, cy), (x - 0.9, cy)]
        pts = clip_convex(rib, ellipse_pts(cx, cy, 22.5, 13.5, n=40))
        if len(pts) >= 3:
            ribs.append(P(f"rib_{i + 1}", poly(pts), "$beanie-dark@0.55"))
    docs.append(acc("beanie", "Beanie", "head", "Blue knit beanie pulled over the top of the head: a dome with knit ribs, a darker turned-up cuff, and a white pompom on top.", [
        P("dome", poly(dome), "$beanie", stroke=OUTLINE),
        *ribs,
        P("cuff", rect(50.4, 8.6, 4), "$beanie-dark", at=(cx, cy + 0.6), stroke=OUTLINE),
        P("pompom", circ(5.6), "$white", at=(cx, cy - 16.2 - 3.6), stroke=OUTLINE),
        P("pompom_shade", poly(clip_convex(ellipse_pts(cx + 1.6, cy - 19.8 + 2, 4.6, 3.6, n=20), ellipse_pts(cx, cy - 19.8, 5.6, 5.6, n=24))), "$snow-shade@0.7"),
    ]))
    # crown: the temp art's five-point outline, with balls on the tips and three jewels on the band
    pts = [H(*p) for p in [(30, 22), (30, 4), (40, 14), (50, 0), (60, 14), (70, 4), (70, 22)]]
    band_y = H(50, 18)[1]
    docs.append(acc("crown", "Crown", "head", "Gold crown standing on top of the head: three points with a ball on each tip and three jewels — red, blue, red — on the band.", [
        P("crown", poly(pts), "$gold", stroke=OUTLINE),
        P("band", poly([(pts[0][0], band_y - 2.6), (pts[-1][0], band_y - 2.6), pts[-1], pts[0]]), "$gold-dark"),
        P("tip_l", circ(2.2), "$gold", at=pts[1], stroke=LINE),
        P("tip_m", circ(2.4), "$gold", at=pts[3], stroke=LINE),
        P("tip_r", circ(2.2), "$gold", at=pts[5], stroke=LINE),
        P("jewel_l", circ(1.9), "$cap", at=(-10, band_y + 0.6)),
        P("jewel_m", {"kind": "ngon", "sides": 4, "r": 2.6}, "$beanie", at=(0, band_y + 0.6)),
        P("jewel_r", circ(1.9), "$cap", at=(10, band_y + 0.6)),
        P("shine", rect(1.4, 4.4, 0.7), "$white@0.5", at=(-14.6, band_y - 6.2)),
    ]))
    # ribbon: a pink bow on the right of the crown of the head
    k = H(62, 18)
    left = [k, (k[0] - 10.8, k[1] - 8.4), (k[0] - 12.6, k[1] - 3), (k[0] - 12.6, k[1] + 3), (k[0] - 10.8, k[1] + 8.4)]
    right = [(2 * k[0] - x, y) for x, y in left]
    docs.append(acc("ribbon", "Ribbon", "head", "Pink bow tied on the right side of the top of the head: two rounded loops with a darker fold in each and a knot in the middle.", [
        P("loop_l", poly(left), "$ribbon", stroke=OUTLINE),
        P("loop_r", poly(right), "$ribbon", stroke=OUTLINE),
        P("fold_l", poly([(k[0] - 2, k[1]), (k[0] - 9, k[1] - 3.5), (k[0] - 9, k[1] + 3.5)]), "$ribbon-dark@0.7"),
        P("fold_r", poly([(k[0] + 2, k[1]), (k[0] + 9, k[1] - 3.5), (k[0] + 9, k[1] + 3.5)]), "$ribbon-dark@0.7"),
        P("knot", ell(3.8, 4.4), "$ribbon-dark", at=k, stroke=OUTLINE),
    ]))
    # headband: a teal band across the forehead's upper curve, clipped to the head so its ends wrap the sides
    c = (0.0, 19.0)
    rx, ry, t = 40.0, 10.0, 3.6
    outer = ellipse_pts(c[0], c[1], rx + t, ry + t, n=48, a0=180, a1=360)
    inner = ellipse_pts(c[0], c[1], rx - t, ry - t, n=48, a0=180, a1=360)
    head = ellipse_pts(0, HEAD_RY, HEAD_RX + 0.6, HEAD_RY + 0.6, n=64)
    band = clip_convex(outer + inner[::-1], head)
    shine = ellipse_pts(c[0], c[1], rx + 0.8, ry + 0.8, n=16, a0=232, a1=262) + ellipse_pts(c[0], c[1], rx + 2.4, ry + 2.4, n=16, a0=262, a1=232)
    docs.append(acc("headband", "Headband", "head", "Teal sports headband around the upper forehead, curving over the head and wrapping round both sides, with a pale shine along its upper edge.", [
        P("band", poly(band), "$headband", stroke=OUTLINE),
        P("shine", poly(shine), "$white@0.45"),
    ]))
    # flower: five pink petals and a yellow centre, tucked on the right of the head
    fc = H(70, 16)
    petals = [P(f"petal_{i + 1}", circ(4.8), "$flower", at=(fc[0] + 5.6 * math.cos(math.radians(-90 + 72 * i)), fc[1] + 5.6 * math.sin(math.radians(-90 + 72 * i))), stroke=OUTLINE) for i in range(5)]
    leaf = [(fc[0] - 4, fc[1] + 4), (fc[0] - 13, fc[1] + 4.5), (fc[0] - 9, fc[1] + 9.5)]
    docs.append(acc("flower", "Flower", "head", "A pink five-petal flower with a yellow centre and one green leaf, tucked on the right of the top of the head.", [
        P("leaf", poly(leaf), "$leaf", stroke=OUTLINE),
        *petals,
        P("centre", circ(3.8), "$gold", at=fc, stroke=LINE),
    ]))
    # glasses: two round ink frames across the eyes with a bridge, faint lenses and glints
    ex = 11.7
    docs.append(acc("glasses", "Glasses", "face", "Round glasses: two thin ink frames around the eyes joined by a bridge, with faint lenses and a glint on each so the eyes still show through.", [
        P("lens", circ(7.4), "$white@0.22", at=(-ex, 0), mirror=True),
        P("glint", rect(1.4, 4.6, 0.7), "$white@0.75", at=(-ex - 3.6, -2.4), rot=30, mirror=True),
        P("rim", ring(8.1, 2.8), "$ink", at=(-ex, 0), mirror=True),
        P("bridge", rect(7.6, 2.6, 1.2), "$ink", at=(0, -0.8)),
        P("arm", rect(5.2, 2.4, 1.2), "$ink", at=(-ex - 10.2, -1.2), mirror=True),
    ]))
    # shades: two dark rounded lenses over the eyes, a bridge, a pale streak on each
    lx = F(36.5, 46)[0]
    docs.append(acc("shades", "Shades", "face", "Sunglasses: two near-black rounded lenses that cover the eyes completely, a bridge between them, and a pale streak of reflection across each.", [
        P("arm", rect(6, 2.6, 1.2), "$ink", at=(lx - 11.5, -1.6), mirror=True),
        P("lens", rect(19, 11, 4.6), "$shades", at=(lx, 0.2), stroke=OUTLINE, mirror=True),
        P("bridge", rect(6.4, 2.6, 1.2), "$ink", at=(0, -1.8)),
        P("glare", poly([(lx - 6.5, -3), (lx - 3.5, -3), (lx - 6.5, 3.5), (lx - 9.5, 3.5)]), "$white@0.55", mirror=True),
    ]))
    # mask: a white face mask over the mouth, two pleats, straps up to the sides of the head
    mc = F(50, 61)
    docs.append(acc("mask", "Mask", "face", "White face mask over the mouth and chin: a soft rounded panel with two grey pleats, straps running up to the sides of the head. Leaves the eyes and the outer edges of the blush showing.", [
        P("strap", poly([(-14, 10.2), (-31.2, 5.2), (-31.2, 7.8), (-14, 12.8)]), "$ink", mirror=True),
        P("panel", rect(28.8, 16.2, 6.3), "$white", at=mc, stroke=OUTLINE),
        P("pleat_top", rect(18, 1.4, 0.7), "$snow-shade", at=(mc[0], mc[1] - 2.4)),
        P("pleat_bottom", rect(18, 1.4, 0.7), "$snow-shade", at=(mc[0], mc[1] + 2.4)),
    ]))
    return docs


# ---------------------------------------------------------------- chip


def chip():
    notches = [P(f"notch_{i + 1}", rect(4.4, 5.4, 1.2), "$white", at=(17.4 * math.cos(math.radians(a)), 17.4 * math.sin(math.radians(a))), rot=a + 90) for i, a in enumerate(range(-90, 270, 60))]
    return {
        "id": "playmore.ui.chip",
        "name": "Chip",
        "description": "A betting chip for 신뢰 베팅: a gold coin with a thick ink rim, six white edge marks like a casino chip, a darker inner ring, and a star struck in the middle. 48x48, origin at the centre; meant to be baked flat and stamped many times.",
        "tags": ["ui", "chip"],
        "size": [48, 48],
        "anchor": [0.5, 0.5],
        "parts": [
            P("coin", circ(20), "$gold", stroke=OUTLINE),
            *notches,
            P("face", circ(13), "$gold"),
            P("inner_ring", ring(13, 2.4), "$gold-dark"),
            P("star", star(5, 7, 3.2), "$gold-dark"),
            P("shine", ring(16.6, 1.8, 200, 250), "$white@0.6"),
        ],
    }


# ---------------------------------------------------------------- role cards
#
# 72x96 cards, origin at the centre. The creature (`playmore.char.body` at 0.62)
# stands in the middle in a skin and a prop that says the role at a glance; the
# card's colour says it again from across the table.

CARD = [72, 96]
CS = 0.62  # creature scale on a card
CB = (0, 10)  # where the creature's origin lands on the card


def on_card(p):
    """Body space → card space."""
    return (CB[0] + p[0] * CS, CB[1] + p[1] * CS)


def card(name, title, role_ko, desc, bg, panel, skin, extra_back, extra_front, accs=()):
    parts = [
        P("card", rect(66, 90, 9), bg, stroke=OUTLINE),
        P("panel", rect(56, 80, 6), panel),
        *extra_back,
        U("creature", "playmore.char.body", at=CB, scale=CS, variant=skin),
    ]
    for aid, sock in accs:
        parts.append(U(aid, f"playmore.acc.{aid}", at=on_card(HEAD_TOP if sock == "head" else EYE_LINE), scale=CS))
    parts += extra_front
    return {
        "id": f"playmore.card.{name}",
        "name": title,
        "description": f"Role card for {role_ko}: {desc} 72x96, origin at the centre.",
        "tags": ["card", "role"],
        "size": CARD,
        "anchor": [0.5, 0.5],
        "parts": parts,
    }


def cards():
    out = []
    ht = on_card(HEAD_TOP)
    eye = on_card(EYE_LINE)
    # mafia: a pale creature in shades and a black fedora with a red band, on a dark card
    brim_y = ht[1] + 3.5
    fedora = [
        P("fedora_crown", poly([(-11, brim_y), (-9.5, brim_y - 11), (-3, brim_y - 13), (0, brim_y - 10.5), (3, brim_y - 13), (9.5, brim_y - 11), (11, brim_y)]), "$coal", stroke=LINE),
        P("fedora_band", rect(21, 3.4, 0.5), "$cap", at=(0, brim_y - 2)),
        P("fedora_brim", ell(19, 3.6), "$coal", at=(0, brim_y + 0.6), stroke=LINE),
    ]
    out.append(card("mafia", "Mafia", "마피아 (mafia)", "a pale creature in black shades and a black fedora with a red band, on a midnight panel with a red border.", "$mafia", "$night", "snow", [], fedora, accs=[("shades", "face")]))
    # attention: a lemon creature shouting into a megaphone, sound waves and sparkles, under a spotlight
    mx, my = on_card((14, 10))
    mega = [
        P("megaphone", poly([(mx - 2, my - 3), (mx + 12, my - 9), (mx + 12, my + 9), (mx - 2, my + 3)]), "$cap", stroke=LINE),
        P("megaphone_bell", ell(2.4, 9), "$cap-dark", at=(mx + 12, my), stroke=LINE),
        P("megaphone_grip", rect(3, 6, 1), "$coal", at=(mx + 3, my + 5.2)),
        P("wave_1", ring(5, 1.8, -40, 40), "$ink", at=(mx + 13, my)),
        P("wave_2", ring(9, 1.8, -40, 40), "$ink", at=(mx + 13, my)),
        P("sparkle_l", star(4, 5, 1.6), "$white", at=(-22, -30)),
        P("sparkle_r", star(4, 3.6, 1.2), "$white", at=(20, -34)),
    ]
    beam = [P("spotlight", poly([(-6, -40), (6, -40), (26, 38), (-26, 38)]), "$white@0.3")]
    out.append(card("attention", "Attention", "관종 (attention seeker)", "a lemon creature on a purple stage under a spotlight, shouting into a red megaphone with sound waves coming out, sparkles above.", "$ribbon", "$attention", "lemon", beam, mega))
    # doctor: a white nurse cap with a red cross, a big pale cross behind, on a mint card
    cap_y = ht[1] + 1
    nurse = [
        P("nurse_cap", poly([(-12, cap_y + 2), (-10, cap_y - 8), (10, cap_y - 8), (12, cap_y + 2)]), "$white", stroke=LINE),
        P("cross_v", rect(2.6, 7.4, 0.4), "$cap", at=(0, cap_y - 3)),
        P("cross_h", rect(7.4, 2.6, 0.4), "$cap", at=(0, cap_y - 3)),
    ]
    big_cross = [P("emblem", poly([(-6, -28), (6, -28), (6, -15), (19, -15), (19, -3), (6, -3), (6, 10), (-6, 10), (-6, -3), (-19, -3), (-19, -15), (-6, -15)]), "$cap", stroke=LINE)]
    out.append(card("doctor", "Doctor", "의사 (doctor)", "a snow-white creature in a white nurse cap with a red cross, a big red cross behind it, on a mint card.", "$mint-shade", "$doctor", "snow", big_cross, nurse))
    # police: a navy peaked cap with a gold star badge, on a blue card
    pc_y = ht[1] + 2
    police = [
        P("police_top", poly([(-13, pc_y - 2), (-15, pc_y - 10), (15, pc_y - 10), (13, pc_y - 2)]), "$police", stroke=LINE),
        P("police_band", rect(26, 3.6, 0.6), "$coal", at=(0, pc_y - 1), stroke=LINE),
        P("police_peak", poly([(-12, pc_y + 1), (12, pc_y + 1), (8, pc_y + 4.5), (-8, pc_y + 4.5)]), "$coal", stroke=LINE),
        P("badge", star(5, 3.6, 1.7), "$gold", at=(0, pc_y - 6)),
    ]
    out.append(card("police", "Police", "경찰 (police)", "a sky-blue creature in a navy police cap with a gold star badge, on a blue card.", "$beanie-dark", "$police-light", "sky", [], police))
    # lover: a coral creature in a blush of hearts
    hearts = [
        P("heart_big", poly(heart_pts(19, -28, 15)), "$cap", stroke=LINE),
        P("heart_small", poly(heart_pts(-20, -24, 10)), "$ribbon", stroke=LINE),
        P("heart_tiny", poly(heart_pts(-10, -36, 6)), "$white", stroke=LINE),
    ]
    out.append(card("lover", "Lover", "연인 (lover)", "a coral creature with hearts floating up around it, on a pink card.", "$ribbon-dark", "$lover", "coral", [], hearts))
    # citizen: the plain creature, just themselves, with a little sprout on the head
    sp = (ht[0], ht[1] + 0.5)
    sprout = [
        P("stem", rect(1.6, 7, 0.8), "$leaf-dark", at=(sp[0], sp[1] - 3.5)),
        P("leaf_l", ell(4.2, 2.2), "$leaf", at=(sp[0] - 3.6, sp[1] - 7.4), rot=-25, stroke=LINE),
        P("leaf_r", ell(4.2, 2.2), "$leaf", at=(sp[0] + 3.6, sp[1] - 7.4), rot=25, stroke=LINE),
    ]
    out.append(card("citizen", "Citizen", "시민 (citizen)", "the plain peach creature with a little green sprout on its head — nobody special, and proud of it — on a warm cream card.", "$lemon-shade", "$citizen", None, [], sprout))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    docs = [lib_skin(), body(), *accessories(), chip(), *cards()]
    for d in docs:
        print(os.path.relpath(write_doc(d), ROOT))


if __name__ == "__main__":
    main()
