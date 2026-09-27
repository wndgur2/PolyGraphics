"""The Pit's card on Feelers' map select.

    python3 scripts/pit_card.py       # rewrites apps/ss/assets/ss-env-stage-pit.json

The fourth stage is one place of its own (feelers `docs/pit-v2-plan.md`): the
burrow's lattice dug thin and open to the sky, a packed red-brown floor with
sand blown down onto it (`ss.env.pit`), obstacles gathered on the lattice's
bare corners, and sand funnels in the wide chambers. The card says that in one
picture: the funnel in the middle, `use: ss.terrain.funnel` so the card's pit
is the run's pit; a ridge of earth and two lumps of it round the chamber, in
the burrow's inks and the run's two passes; and on the corners where no wall
stands, the three stages' obstacles side by side — which is the stage: every
ground's things, fallen into one hole.

Authored 3:2 like the other three cards (384×256), weight through the middle,
props free to run off the flanks. Every ink here is one of the other three
cards' inks; every repeat has its own seed.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import R, r2, lerp, poly, ell, circ, rect, one

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-env-stage-pit.json")
W, H = 384, 256
FUNNEL_AT, FUNNEL_SCALE = (0.0, 4.0), 0.58

parts = []
def put(pid, at, shape, fill, **kw):
    p = {"id": pid}
    if at is not None: p["at"] = [r2(at[0]), r2(at[1])]
    if kw.get("rot"): p["rot"] = r2(kw["rot"])
    kw.pop("rot", None)
    p["shape"] = shape
    p["fill"] = fill
    p.update({k: v for k, v in kw.items() if v is not None})
    parts.append(p)
def scatter(pid, at, of, count, area, seed, fill, scale_range, jitter=True, rot=None):
    p = {"id": pid, "at": [r2(at[0]), r2(at[1])]}
    if rot: p["rot"] = rot
    rep = {"of": of, "count": count, "area": area, "seed": seed, "scaleRange": scale_range}
    if jitter: rep["jitterRot"] = True
    p["repeat"] = rep
    p["fill"] = fill
    parts.append(p)
def prop(pid, at, asset, scale, rot=None):
    p = {"id": pid, "at": [r2(at[0]), r2(at[1])], "use": asset, "scale": scale}
    if rot: p["rot"] = rot
    parts.append(p)
def shift(pts, dx, dy): return [(x + dx, y + dy) for x, y in pts]

# ============================================================== the floor (ss.env.pit)
put("base", None, rect(W, H, 0), "$sand.dark")
for name, at, rx, ry, rot in [("hard_w", (-120, -60), 120, 70, 24), ("hard_e", (130, 70), 130, 64, -32),
                              ("hard_s", (-60, 110), 90, 40, 8)]:
    for k, f in enumerate((1.0, 0.72, 0.46)):
        put(f"{name}_{k}", at, ell(rx * f, ry * f), "$rust@0.07", rot=rot)
for name, at, rx, ry in [("drift_n", (40, -96), 110, 34), ("drift_w", (-150, 20), 60, 26), ("drift_e", (150, -20), 70, 24),
                         ("drift_s", (60, 110), 100, 30)]:
    for k, f in enumerate((1.0, 0.74, 0.5)):
        put(f"{name}_{k}", at, ell(rx * f, ry * f), "$sand@0.22", rot=-13)
    put(f"{name}_lit", (at[0] - 3, at[1] - 4), ell(rx * 0.9, ry * 0.55), "$chitin@0.06", rot=-13)
scatter("grain_dark", (0, 0), ell(4, 3), 160, [400, 272], 7601, "$soil@0.22", [0.35, 1.4])
scatter("grain_pale", (0, 0), ell(4, 3), 130, [400, 272], 7602, "$sand.light@0.2", [0.35, 1.4])
scatter("grain_warm", (0, 0), ell(4, 3), 80, [400, 272], 7603, "$chitin@0.1", [0.4, 1.4])
for i, (x, y, r, a0, a1) in enumerate([(-96, -18, 26, 200, 262), (104, 24, 22, 20, 84), (-30, 96, 28, 150, 206),
                                       (70, -60, 18, 290, 350)]):
    put(f"scar_{i}", (x, y), {"kind": "ring", "r": r, "width": 4, "from": a0, "to": a1}, "$soil@0.42")
    put(f"scar_{i}_lip", (x, y - 2), {"kind": "ring", "r": r, "width": 2, "from": a0 + 4, "to": a1 - 4},
        "$sand.light@0.16")
scatter("flecks", (0, 0), rect(3, 3, 0), 18, [380, 250], 7615, "$rust", [0.55, 1.4], jitter=False)
parts[-1]["repeat"]["of"].pop("corner")

# ============================================================== earth: a ridge and two lumps
# The lattice dug thin: a partition running off the top-right with its corner
# mass, and a lone lump on the bottom-left — everything a contour first, then
# every fill, so no mass outlines the one beside it (the run's two passes).
EARTH = [("ridge", (150, -96), rect(150, 30, 15), -22), ("ridge_end", (84, -70), circ(24), 0),
         ("ridge_far", (214, -122), circ(30), 0), ("lump", (-170, 104), circ(34), 0),
         ("lump_lobe", (-140, 118), circ(20), 0)]
def grow(shape, d):
    s = dict(shape)
    if s["kind"] == "circle": s["r"] = r2(s["r"] + d)
    else: s["w"], s["h"], s["corner"] = r2(s["w"] + 2 * d), r2(s["h"] + 2 * d), r2(s["corner"] + d)
    return s
for eid, at, shape, rot in EARTH:
    put(f"rim_{eid}", at, grow(shape, 4), "$ink.dark", rot=rot)
for eid, at, shape, rot in EARTH:
    put(f"earth_{eid}", at, shape, "$carapace.dark", rot=rot)
FACES = [((120, -84), 5.5, 3.7, 20, "$ink@0.3"), ((166, -102), 6.2, 4.2, 127, "$carapace@0.16"),
         ((196, -118), 3.8, 2.6, 35, "$carapace.dark2@0.5"), ((84, -72), 5.0, 3.2, 95, "$ink@0.3"),
         ((-170, 98), 5.6, 3.6, 70, "$carapace@0.16"), ((-158, 112), 4.6, 3.0, 300, "$ink@0.3"),
         ((-138, 118), 3.4, 2.2, 40, "$carapace.dark2@0.5")]
for i, (at, rx, ry, rot, fill) in enumerate(FACES):
    put(f"earth_face_{i}", at, ell(rx, ry), fill, rot=rot)

# ============================================================== bare corners, and what stands on them
# West: the flats' spires and boulder leaning together.
prop("spire_wa", (-150, -70), "ss.terrain.spire", 1.15)
prop("spire_wb", (-124, -52), "ss.terrain.spire", 0.78)
prop("boulder_w", (-172, -38), "ss.terrain.boulder", 0.9)
# East: the pan's plate on edge, a ribcage, the Mason's shard.
prop("saltplate_e", (150, 74), "ss.terrain.saltplate", 1.0)
prop("ribcage_e", (112, 106), "ss.terrain.ribcage", 0.72)
prop("chitin_e", (182, 104), "ss.terrain.chitin", 0.8)
# And the floor's own litter.
prop("fungi_n", (38, -104), "ss.terrain.fungi", 0.62)
prop("glass_s", (-84, 112), "ss.terrain.glass", 0.7)
prop("fissure_w", (-110, 40), "ss.terrain.fissure", 0.8, rot=62)

scatter("glints", (0, 0), rect(3, 3, 0), 40, [400, 272], 7621, "$silent@0.5", [0.45, 1.3], jitter=False)
parts[-1]["repeat"]["of"].pop("corner")

# ============================================================== the pit
prop("funnel", FUNNEL_AT, "ss.terrain.funnel", FUNNEL_SCALE)

for p in parts:
    s = p.get("shape")
    if s and s.get("kind") == "rect" and s.get("corner") == 0: s.pop("corner")

doc = {
    "id": "ss.env.stage-pit",
    "name": "Pit stage card (SS)",
    "description": (
        "The picture on the Pit card (개미지옥) in Feelers' map select: the fourth stage, the one that never ends, "
        "drawn once from the camera's own height like the other three.\n\n"
        "The Pit is one place of its own: the burrow's lattice dug thin and open to the sky, on a packed red-brown "
        "floor with sand blown down onto it (ss.env.pit's inks, drifts on the pan's -13 degrees, claw scars, rust "
        "flecks). In the middle, `use: ss.terrain.funnel`: the run's own pit, dug in a wide chamber. Round it, a "
        "partition of earth with its corner mass and a lone lump, $carapace.dark on its $ink.dark contour in the "
        "run's two passes; and on the corners no wall reaches, the three stages' obstacles gathered side by side — "
        "the flats' spires and boulder, the pan's salt plate and ribcage, the Mason's chitin shard — which is the "
        "stage in one sentence: every ground's things, fallen into one hole.\n\n"
        "Every ink is one the other three cards use. Authored 3:2 like them: the card fits it to the strip's width "
        "and crops it vertically, so the pit sits on the middle band and the flanks run off the left and right edges."
    ),
    "tags": ["env", "card", "stage"],
    "size": [W, H],
    "parts": parts,
}
L = ["{"]
for k in ("id", "name", "description", "tags", "size"):
    L.append(f'  "{k}": {one(doc[k])},')
L.append('  "parts": [')
L.append(",\n".join(f"    {one(p)}" for p in doc["parts"]))
L.append("  ]")
L.append("}")
open(OUT, "w").write("\n".join(L) + "\n")
print(f"wrote {os.path.relpath(OUT)}: {len(parts)} parts")
