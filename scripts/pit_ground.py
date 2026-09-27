"""The Pit's floor — Feelers' fourth stage has a ground of its own now.

    python3 scripts/pit_ground.py     # rewrites apps/ss/assets/ss-env-pit.json

The Pit used to be the other three grounds in 1800px zones; it is one place
now (feelers `docs/pit-v2-plan.md` §4): the burrow's lattice dug thin, open to
the sky, with sand blown down into it. So the floor is between the burrow's and
the pan's — packed earth, redder and harder than the plains' dirt, with the
pan's sand lying on it in drifts rather than covering it — and mid-toned on
purpose: all three stages' bodies walk on it, and the dark plains roster and
the mid-brown pan roster both have to stand off it.

What says "pit" is what lies on the earth: sand pooled faintly in its low places,
short claw-scored scars where something dug and was dug after (a dark cut under
a lit lip, the burrow's gouge made small), crumbs of shed chitin, and the
plains' rust flecks where scent dried, so the three read as one world.

Built like the pan's tile: a flat base, broad mottles in nested washes (the
bake flattens gradients, so three stacked ellipses stand in for one), then
seeded grain passes, then hand-listed marks. It tiles on a torus: every placed
part whose bounds cross an edge is emitted again 128px over. Every coordinate
is hand-listed or seeded, so the tile is pixel-stable.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import r2, ell, one

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-env-pit.json")
T = 128
HALF = T / 2

parts = []


def bound(shape):
    k = shape["kind"]
    if k == "ellipse": return max(shape["rx"], shape["ry"])
    if k == "circle": return shape["r"]
    if k == "ring": return shape["r"] + shape["width"]
    if k == "rect": return math.hypot(shape["w"], shape["h"]) / 2
    raise ValueError(k)


def put(pid, at, shape, fill, rot=None):
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
            parts.append(p)


def grain(pid, of, count, seed, fill, scale):
    parts.append({"id": pid, "repeat": {"of": of, "count": count, "area": [T, T], "seed": seed,
                                        "jitterRot": True, "scaleRange": scale}, "fill": fill})


def arc(r, w, frm, to): return {"kind": "ring", "r": r2(r), "width": r2(w), "from": r2(frm), "to": r2(to)}
def sq(s): return {"kind": "rect", "w": r2(s), "h": r2(s)}


# ------------------------------------------------------------------ the earth
parts.append({"id": "base", "shape": {"kind": "rect", "w": T, "h": T}, "fill": "$sand.dark"})
# Hardpan: broad redder patches where the earth is packed and bare.
for i, (x, y, rx, ry, rot) in enumerate([(-30, -34, 40, 26, 24), (38, 22, 46, 28, -32), (-44, 44, 30, 20, 8)]):
    for k, f in enumerate((1.0, 0.72, 0.46)):
        put(f"pan{i}_{k}", (x, y), ell(rx * f, ry * f), "$rust@0.07", rot)
# Darker packed spots — the plains' soil showing through.
for i, (x, y, rx, ry, rot) in enumerate([(26, -40, 22, 14, -12), (-8, 18, 18, 11, 40)]):
    for k, f in enumerate((1.0, 0.66)):
        put(f"pack{i}_{k}", (x, y), ell(rx * f, ry * f), "$soil@0.09", rot)

# ------------------------------------------------------------------ the sand on it
# Drifts pooled in the low places: two broad, faint lenses rather than many
# small ones. The game shuffles this tile into a 1024px field in patches, so
# every lens drawn here is laid a dozen times over at random offsets, and small
# bright lenses laid that often read as leaf litter, not as sand.
for i, (x, y, rx, ry, rot) in enumerate([(8, -12, 44, 22, -13), (-36, 44, 34, 16, -13)]):
    for k, f in enumerate((1.0, 0.62)):
        put(f"drift{i}_{k}", (x, y), ell(rx * f, ry * f), "$sand@0.1", rot)

grain("grit_dark", sq(1), 150, 7101, "$soil@0.28", [0.65, 1.3])
grain("grit_pale", sq(1), 140, 7102, "$sand.light@0.26", [0.65, 1.25])
grain("grit_warm", sq(1.3), 80, 7103, "$chitin@0.11", [0.6, 1.2])
grain("grit_shade", sq(1.4), 70, 7104, "$rust.dark@0.16", [0.6, 1.3])
grain("glint", sq(1), 20, 7105, "$husk@0.34", [0.6, 1.1])

# ------------------------------------------------------------------ what dug here
# Claw scars: short curved cuts, each a dark groove under a lit lip.
for i, (x, y, r, a0, a1) in enumerate([(-22, -52, 14, 200, 262), (46, -12, 11, 20, 84), (-52, 22, 12, 290, 350),
                                       (12, 38, 16, 150, 206), (-6, -20, 9, 60, 118)]):
    put(f"scar{i}", (x, y), arc(r, 2.4, a0, a1), "$soil@0.42")
    put(f"scar{i}_lip", (x, y - 1.3), arc(r, 1.1, a0 + 4, a1 - 4), "$sand.light@0.16")
# Shed chitin, and the plains' rust where old scent dried.
for i, (x, y, s, rot) in enumerate([(-36, -16, 2.6, 20), (20, -26, 2.0, 70), (58, 30, 2.4, 10), (-18, 56, 2.2, 45),
                                    (40, -58, 1.8, 30), (-58, -50, 2.0, 80)]):
    put(f"crumb{i}", (x, y), {"kind": "rect", "w": r2(s * 1.6), "h": r2(s)}, "$chitin@0.34", rot)
for i, (x, y) in enumerate([(-28, 30), (52, -30), (6, -58), (-60, 60)]):
    put(f"fleck{i}", (x, y), sq(1.8), "$rust@0.5")

doc = {
    "id": "ss.env.pit",
    "name": "Pit ground (SS)",
    "description": "Feelers' 128px floor for the Pit: packed red-brown earth between the burrow's and the pan's, with sand blown down onto it in drifts, claw-scored scars, shed chitin and the plains' rust flecks. Mid-toned so all three stages' rosters stand off it. Tiles on a torus. Generated by scripts/pit_ground.py.",
    "tags": ["env", "tile"],
    "size": [T, T],
    "parts": parts,
}
L = ["{"] + [f'  "{k}": {one(doc[k])},' for k in ("id", "name", "description", "tags", "size")]
L += ['  "parts": [', ",\n".join(f"    {one(p)}" for p in parts), "  ]", "}"]
open(OUT, "w").write("\n".join(L) + "\n")
print(f"{len(parts)} parts -> {os.path.relpath(OUT)}")
