"""The Plains' floor — the first ground walked, and the one the base stands on.

    python3 scripts/den_ground.py     # rewrites apps/ss/assets/ss-env-ground.json

The old tile was a flat fill with five black pits and eight flecks on it, and
in the game those pits were the only thing on the floor, so the eye counted
them and saw the 128px grid. This is the same dark iron-red dirt with the dirt
drawn: the value stays where it was (bodies are judged against the floor's
mean, `scripts/readability.ts`, and the roster's contrast must not move), and
what changes is that there is something under the feet at every scale.

Large, medium, small (feelers `docs/staging-method.md` §8): broad mottles of
packed rust and of hollow first, then the things that happen to dirt — dried
mud cracks lit along one lip, the burrow pits made shallow dishes rather than
holes, stones with a shadow, dry stalks where the grass the ambience rustles
with was, crumbs of shed chitin and the rust where old scent dried — and grain
over all of it. The hive's pink is on this ground only as two faint stains,
because the card says so ("A plain the reek never leaves") and because pink is
spent sparingly.

Built like the pit's tile: flat values only (the bake flattens gradients, so a
soft patch is three nested washes), seeded grain, hand-listed marks, and it
tiles on a torus: every placed part whose bounds cross an edge is emitted again
128px over. Everything is listed or seeded, so the tile is pixel-stable.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import r2, ell, circ, one

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-env-ground.json")
T = 128
HALF = T / 2

parts = []


def bound(shape):
    k = shape["kind"]
    if k == "ellipse": return max(shape["rx"], shape["ry"])
    if k == "circle": return shape["r"]
    if k == "ring": return shape["r"] + shape["width"]
    if k == "rect": return math.hypot(shape["w"], shape["h"]) / 2
    if k == "poly": return max(math.hypot(x, y) for x, y in shape["points"])
    raise ValueError(k)


def put(pid, at, shape, fill, rot=None, opacity=None):
    """Place a part, and again on every side its bounds spill over."""
    b = bound(shape)
    x, y = at
    xs = [0] + ([T] if x - b < -HALF else []) + ([-T] if x + b > HALF else [])
    ys = [0] + ([T] if y - b < -HALF else []) + ([-T] if y + b > HALF else [])
    n = 0
    for dx in xs:
        for dy in ys:
            p = {"id": pid if (dx, dy) == (0, 0) else f"{pid}_w{n}"}
            if (dx, dy) != (0, 0): n += 1
            p["at"] = [r2(x + dx), r2(y + dy)]
            if rot: p["rot"] = r2(rot)
            p["shape"] = shape
            p["fill"] = fill
            if opacity is not None: p["opacity"] = opacity
            parts.append(p)


def grain(pid, of, count, seed, fill, scale):
    parts.append({"id": pid, "repeat": {"of": of, "count": count, "area": [T, T], "seed": seed,
                                        "jitterRot": True, "scaleRange": scale}, "fill": fill})


def arc(r, w, frm, to): return {"kind": "ring", "r": r2(r), "width": r2(w), "from": r2(frm), "to": r2(to)}
def sq(s): return {"kind": "rect", "w": r2(s), "h": r2(s)}
def box(w, h): return {"kind": "rect", "w": r2(w), "h": r2(h)}


def crack(pid, pts, width, fill, lip=None):
    """A crack through `pts`: a dark seam as one polygon about its own middle, and the lit lip above it."""
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    local = [(x - cx, y - cy) for x, y in pts]
    top, bot = [], []
    for i, (x, y) in enumerate(local):
        a = local[max(0, i - 1)]
        b = local[min(len(local) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n * width / 2, dx / n * width / 2
        top.append((x + nx, y + ny))
        bot.append((x - nx, y - ny))
    seam = {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in top + bot[::-1]]}
    if lip:
        put(f"{pid}_lip", (cx - 0.7, cy - 0.7), seam, lip)
    put(pid, (cx, cy), seam, fill)


# ------------------------------------------------------------------ the dirt
parts.append({"id": "base", "shape": {"kind": "rect", "w": T, "h": T}, "fill": "$soil"})
# Packed rust: broad patches where the iron in the dirt shows, three washes
# nested so each reads as one soft patch and not a drawn ellipse.
for i, (x, y, rx, ry, rot) in enumerate([(-34, -30, 38, 24, 18), (40, 26, 44, 26, -28), (-40, 46, 28, 18, 6), (22, -50, 26, 15, 40)]):
    for k, f in enumerate((1.0, 0.7, 0.44)):
        put(f"rust{i}_{k}", (x, y), ell(rx * f, ry * f), "$rust@0.05", rot)
# Hollows: where the ground dips and the dark pools.
for i, (x, y, rx, ry, rot) in enumerate([(14, 4, 30, 18, -14)]):
    for k, f in enumerate((1.0, 0.64)):
        put(f"hollow{i}_{k}", (x, y), ell(rx * f, ry * f), "$soil.dark2@0.3", rot)
# Trodden: two paler patches where the top is worn hard and catches the light.
for i, (x, y, rx, ry, rot) in enumerate([(-8, -40, 22, 12, -10), (6, 50, 26, 12, 12)]):
    put(f"worn{i}", (x, y), ell(rx, ry), "$soil.light@0.06", rot)

# ------------------------------------------------------------------ grain
grain("grit_dark", sq(1), 210, 6101, "$ink@0.3", [0.6, 1.3])
grain("grit_pale", sq(1), 200, 6102, "$soil.light2@0.18", [0.6, 1.25])
grain("grit_rust", sq(1.2), 80, 6103, "$rust@0.3", [0.6, 1.2])
grain("grit_cold", sq(1.3), 40, 6104, "$carapace.dark@0.1", [0.6, 1.3])
grain("glint", sq(1), 14, 6105, "$sand@0.2", [0.6, 1.1])

# ------------------------------------------------------------------ what happens to dirt
# Dried mud cracks: a dark seam with the upper-left lip catching the light.
crack("crack0", [(-60, -18), (-46, -12), (-38, -2), (-30, 2), (-26, 12)], 1.3, "$ink@0.42", "$rust.light@0.1")
crack("crack1", [(10, -30), (22, -22), (36, -20), (44, -10)], 1.2, "$ink@0.42", "$rust.light@0.1")
crack("crack2", [(-4, 26), (6, 34), (10, 46), (22, 54)], 1.2, "$ink@0.42", "$rust.light@0.1")
crack("crack3", [(48, 42), (56, 50), (66, 54)], 1.1, "$ink@0.38", "$rust.light@0.09")
crack("crack4", [(-36, -58), (-28, -50), (-26, -40)], 1.1, "$ink@0.38", "$rust.light@0.09")
# A branch off the long one, as cracks fork.
crack("crack0b", [(-38, -2), (-34, -10), (-28, -14)], 1.0, "$ink@0.36", "$rust.light@0.08")

# The burrow pits, where the old tile had them: shallow dishes now. A soft
# rim, the dish, a smaller dark throat, and the far wall lit, because a hole
# in a floor lit from the upper left shows its lower-right inside.
for i, (x, y, r) in enumerate([(-52, -24, 7), (36, 26, 8), (-24, 36, 5)]):
    put(f"pit{i}_rim", (x, y + r * 0.1), ell(r * 1.2, r * 0.9), "$soil.light@0.07")
    put(f"pit{i}_dish", (x, y), ell(r, r * 0.76), "$soil.dark2@0.45")
    put(f"pit{i}", (x, y), ell(r * 0.5, r * 0.38), "$ink@0.4")
    put(f"pit{i}_far", (x + r * 0.2, y + r * 0.26), arc(r * 0.5, 0.8, 20, 110), "$rust.light@0.1")

# Stones: a few, each with the dark under it and one catch of light.
for i, (x, y, rx, ry, rot) in enumerate([(-14, -22, 2.6, 1.8, 20), (58, 8, 2.2, 1.5, -30), (-46, 14, 1.8, 1.3, 50),
                                         (30, 44, 2.4, 1.7, 10), (-2, 58, 1.7, 1.2, -20), (44, -46, 2.0, 1.4, 35),
                                         (-60, 54, 1.6, 1.2, 0)]):
    put(f"stone{i}_sh", (x + 0.7, y + 0.8), ell(rx, ry), "$ink@0.4", rot)
    put(f"stone{i}", (x, y), ell(rx, ry), "$smoke.dark@0.45", rot)
    put(f"stone{i}_lit", (x - rx * 0.3, y - ry * 0.35), circ(min(rx, ry) * 0.3), "$steel@0.2")

# Dry stalks: the grass the field rustles with, gone to straw. Tufts of three
# short leaning blades, dark olive and straw.
def tuft(i, x, y, lean, s=1.0):
    for k, (dx, ang, L, fill) in enumerate([(-1.6, -26, 6.5, "$moss.dark@0.4"), (0.2, 4, 7.5, "$sand.dark@0.36"), (1.7, 22, 5.5, "$moss.dark@0.36")]):
        a = math.radians(ang + lean)
        L = L * s
        put(f"tuft{i}_{k}", (x + dx * s + math.sin(a) * L / 2, y - math.cos(a) * L / 2), box(0.9, L), fill, ang + lean)
    put(f"tuft{i}_root", (x, y + 0.6), ell(2.2 * s, 0.8), "$ink@0.3")


tuft(0, -30, 20, -8)
tuft(1, 46, -20, 12, 0.9)
tuft(2, -8, -58, 4, 0.8)
tuft(3, 20, 60, -14, 1.1)
tuft(4, 60, 58, 6, 0.85)
tuft(5, -58, -44, -4, 0.9)

# Shed chitin, and the rust flecks the old tile had, where it had them.
for i, (x, y, s, rot) in enumerate([(-22, 50, 2.4, 25), (14, -10, 1.9, 70), (54, 30, 2.2, 15), (-40, -34, 2.0, 50), (36, -60, 1.7, 30)]):
    put(f"crumb{i}", (x, y), box(s * 1.6, s), "$chitin@0.2", rot)
for i, (x, y) in enumerate([(-41, -41), (-1, 15), (47, -31), (23, 55)]):
    put(f"fleck{i}", (x, y), sq(3), "$rust@0.9")
for i, (x, y) in enumerate([(-17, -11), (33, 5), (-49, 37), (53, -51)]):
    put(f"speck{i}", (x, y), sq(2), "$rust.dark@heavy")

# Two faint stains where the reek dried: the hive's pink, barely, and only here.
for i, (x, y, rx, ry, rot) in enumerate([(-20, -6, 11, 7, 30), (40, 54, 9, 6, -20)]):
    put(f"stain{i}", (x, y), ell(rx, ry), "$pheromone@0.035", rot)

doc = {
    "id": "ss.env.ground",
    "name": "Hive ground",
    "description": "Feelers' 128px ground tile for the Plains, and the floor the base stands on: dark iron-red dirt, drawn. Warm enough to read as earth rather than void, dark enough that the hive's magenta still has somewhere to go — the value is the old flat tile's, measured, so the roster's contrast against it does not move. On it, large to small: packed rust and hollows in nested washes, dried mud cracks with the upper-left lip lit, three burrow pits as shallow dishes with the far wall lit (a black hole is the one thing on a tile the eye counts, and the game lays the tile over itself in patches, so every big dark mark is laid a dozen times), stones with a shadow, dry stalks where the grass went to straw, shed chitin, the rust flecks where scent dried, two faint pink stains for the reek the card says never leaves, and seeded grain over all of it. Tiles on a torus. Generated by scripts/den_ground.py.",
    "tags": ["env", "tile"],
    "size": [T, T],
    "parts": parts,
}
L = ["{"] + [f'  "{k}": {one(doc[k])},' for k in ("id", "name", "description", "tags", "size")]
L += ['  "parts": [', ",\n".join(f"    {one(p)}" for p in parts), "  ]", "}"]
open(OUT, "w").write("\n".join(L) + "\n")
print(f"{len(parts)} parts -> {os.path.relpath(OUT)}")
