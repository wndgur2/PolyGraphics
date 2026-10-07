"""The burrow's floor — the chamber floors between the walls, authored here at last.

    python3 scripts/burrow_ground.py     # rewrites apps/ss/assets/ss-env-burrow.json

feelers drew this one in BootScene (`makeBurrowGround`): a flat fill, five
gouges and nine squares of grit, and on the chamber floors the five gouges
were the only thing there was, so the eye counted them and saw the grid. It
is the same soil — how far under the Plains' warm dirt the nest is dug, a
purple-black the hive's magenta still has somewhere to go on — with the floor
drawn: what a tunnel floor is made of and what walks on it.

Large, medium, small: broad damp patches and a dry one first, then the
scoring — short curved gouges where the earth was cut out, each a dark cut
under a lit lip, the way the walls are scored — then root threads coming
through from the field above, scrape marks where something was dragged,
grit from the digging, crumbs of shed husk, and grain over all of it. No
pink: the burrow's signal is the bodies in it.

Built like the Plains' and the Pit's tiles: flat values, nested washes for a
soft patch, seeded grain, hand-listed marks, tiling on a torus (a part whose
bounds cross an edge is emitted again 128px over). Everything is listed or
seeded, so the tile is pixel-stable, and the value is held to the old fill's
(#15131c) so the burrow's roster reads against it as it did.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import r2, ell, circ, one

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-env-burrow.json")
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


def put(pid, at, shape, fill, rot=None):
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
            parts.append(p)


def grain(pid, of, count, seed, fill, scale):
    parts.append({"id": pid, "repeat": {"of": of, "count": count, "area": [T, T], "seed": seed,
                                        "jitterRot": True, "scaleRange": scale}, "fill": fill})


def arc(r, w, frm, to): return {"kind": "ring", "r": r2(r), "width": r2(w), "from": r2(frm), "to": r2(to)}
def sq(s): return {"kind": "rect", "w": r2(s), "h": r2(s)}
def box(w, h): return {"kind": "rect", "w": r2(w), "h": r2(h)}


def thread(pid, pts, width, fill):
    """A root thread through `pts`, as one polygon about its own middle."""
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
    put(pid, (cx, cy), {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in top + bot[::-1]]}, fill)


# ------------------------------------------------------------------ the soil
# `$dead` is a step lighter than the old fill; the wash under everything brings it back to it.
parts.append({"id": "base", "shape": {"kind": "rect", "w": T, "h": T}, "fill": "$dead"})
parts.append({"id": "base_wash", "shape": {"kind": "rect", "w": T, "h": T}, "fill": "$ink@0.5"})
# Damp: broad patches where water came through, darker, in nested washes.
for i, (x, y, rx, ry, rot) in enumerate([(-30, 20, 36, 22, 14), (40, -34, 30, 18, -24)]):
    for k, f in enumerate((1.0, 0.66, 0.4)):
        put(f"damp{i}_{k}", (x, y), ell(rx * f, ry * f), "$ink@0.1", rot)
# Dry: one patch packed hard and a touch paler, with the cold purple of the walls in it.
for i, (x, y, rx, ry, rot) in enumerate([(26, 30, 30, 16, -10)]):
    put(f"dry{i}", (x, y), ell(rx, ry), "$carapace@0.07", rot)

# ------------------------------------------------------------------ grain
grain("grit_dark", sq(1), 200, 5101, "$ink@0.35", [0.6, 1.3])
grain("grit_pale", sq(1), 170, 5102, "$dusk@0.16", [0.6, 1.25])
grain("grit_cold", sq(1.2), 70, 5103, "$carapace.light@0.1", [0.6, 1.3])
grain("grit_warm", sq(1.2), 30, 5104, "$rust@0.22", [0.6, 1.2])

# ------------------------------------------------------------------ the digging
# Gouges where the tunnel was cut: a dark curved cut, and the lip above it lit
# from overhead the way the walls' scoring is. Four, off any grid.
for i, (x, y, r, a0, a1) in enumerate([(-40, -36, 20, 200, 275), (46, 6, 16, 10, 80), (-6, 46, 22, 150, 212), (14, -14, 12, 60, 130)]):
    put(f"gouge{i}", (x, y), arc(r, 2.6, a0, a1), "$ink@0.7")
    put(f"gouge{i}_lip", (x, y - 1.4), arc(r, 1.1, a0 + 4, a1 - 4), "$dusk@0.28")
# Scrape marks: three short parallel claws where something was dragged in.
for i, (x, y, rot) in enumerate([(-50, 8, -30), (34, 50, 20)]):
    for k in range(3):
        put(f"scrape{i}_{k}", (x + k * 2.6, y + k * 0.4), box(1.1, 7), "$ink@0.5", rot)
        put(f"scrape{i}_{k}_lip", (x + k * 2.6 - 0.6, y + k * 0.4 - 0.6), box(0.6, 6.4), "$dusk@0.16", rot)

# Roots: the field's grass comes through from above, pale threads that fork.
thread("root0", [(-62, -10), (-50, -4), (-40, 2), (-34, 12), (-30, 24)], 1.0, "$carapace.light@0.22")
thread("root0b", [(-40, 2), (-32, -2), (-24, -1)], 0.8, "$carapace.light@0.18")
thread("root1", [(20, -60), (28, -50), (26, -40), (34, -30)], 0.9, "$carapace.light@0.2")
thread("root2", [(50, 20), (56, 30), (62, 34)], 0.8, "$carapace.light@0.17")
# Hair roots off them.
for i, (x, y, rot) in enumerate([(-46, 6, 40), (-30, 16, -60), (30, -46, 30)]):
    put(f"hair{i}", (x, y), box(0.6, 4), "$carapace.light@0.16", rot)

# Grit from the digging — pale grains lying where they fell — and crumbs of shed husk.
for i, (x, y, s) in enumerate([(12, 46, 2), (70, 36, 3), (40, 96, 2), (112, 62, 2), (92, 112, 3)]):
    put(f"grit{i}", (x - 64, y - 64), sq(s), "$dusk@0.35")
for i, (x, y, s, rot) in enumerate([(-20, -52, 2.4, 20), (56, -12, 2.0, 70), (-56, 40, 2.2, 10), (6, 10, 1.8, 45)]):
    put(f"crumb{i}", (x, y), box(s * 1.6, s), "$husk@0.2", rot)
# Rust where old scent dried, as on the field above.
for i, (x, y) in enumerate([(34, 14), (120, 34), (56, 120), (80, 82)]):
    put(f"fleck{i}", (x - 64, y - 64), sq(2.4), "$rust@0.7")
# Pebbles turned up by the digging, each with the dark under it and a catch of light.
for i, (x, y, rx, ry, rot) in enumerate([(-10, -30, 2.2, 1.5, 15), (44, 44, 1.9, 1.3, -25), (-52, 56, 2.4, 1.6, 30), (60, -54, 1.7, 1.2, 0)]):
    put(f"stone{i}_sh", (x + 0.6, y + 0.8), ell(rx, ry), "$ink@0.5", rot)
    put(f"stone{i}", (x, y), ell(rx, ry), "$carapace.dark@0.7", rot)
    put(f"stone{i}_lit", (x - rx * 0.3, y - ry * 0.35), circ(min(rx, ry) * 0.3), "$dusk@0.3")

doc = {
    "id": "ss.env.burrow",
    "name": "Burrow ground",
    "description": "Feelers' 128px floor for the Burrow's chambers: the soil the nest is dug in, a purple-black a step under the Plains' warm dirt, held to the value feelers drew it at so the burrow's roster reads against it as it did. On it, large to small: damp patches and a dry one in nested washes, four gouges where the tunnel was cut (a dark cut under a lip lit from overhead, the way the walls are scored), scrape marks where something was dragged in, the field's roots coming through from above as pale forking threads, grit and pebbles turned up by the digging, crumbs of shed husk, the rust of old scent, and seeded grain over all of it. No pink: the burrow's signal is the bodies in it. Tiles on a torus. Generated by scripts/burrow_ground.py.",
    "tags": ["env", "tile"],
    "size": [T, T],
    "parts": parts,
}
L = ["{"] + [f'  "{k}": {one(doc[k])},' for k in ("id", "name", "description", "tags", "size")]
L += ['  "parts": [', ",\n".join(f"    {one(p)}" for p in parts), "  ]", "}"]
open(OUT, "w").write("\n".join(L) + "\n")
print(f"{len(parts)} parts -> {os.path.relpath(OUT)}")
