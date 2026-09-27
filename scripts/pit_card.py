"""The Pit's card on Feelers' map select.

    python3 scripts/pit_card.py       # rewrites apps/ss/assets/ss-env-stage-pit.json

The fourth stage is the other three in one run — plains, burrow and salt pan
laid in 1800px zones — with sand funnels dug into it (feelers
`docs/pit-plan.md` §3, §7). The card says that in one picture: the funnel in
the middle, `use: ss.terrain.funnel` so the card's pit is the run's pit, and the
three grounds in patches round its rim, each in its own card's inks and with
its own props, meeting at the seams the run decorates (§3.3: `fissure` where
sand meets plains, `rubble` where the burrow meets anything).

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

# ============================================================== the pan: the ground the pit is dug in
put("base", None, rect(W, H, 0), "$sand")
parts[-1]["shape"].pop("corner")
put("glare", None, rect(W, H, 0), "$sand.light2@0.45")
parts[-1]["shape"].pop("corner")
for name, at, rx, ry, fill in [("swell_n", (70, -104), 150, 70, "$sand.light2@0.09"),
                               ("swell_s", (40, 118), 160, 72, "$sand.light2@0.09"),
                               ("shade_e", (172, 40), 110, 90, "$rust.dark@0.06")]:
    for k, f in enumerate((1.0, 0.7, 0.45)):
        put(f"{name}_{k}", at, ell(rx * f, ry * f), fill, rot=-13)
scatter("grain_bed", (0, 0), ell(6, 4), 150, [400, 272], 6601, "$sand.dark@0.16", [0.35, 1.5])
scatter("grain_pale", (0, 0), ell(5, 4), 120, [400, 272], 6602, "$husk@0.10", [0.35, 1.5])
scatter("grain_warm", (0, 0), ell(5, 3), 90, [400, 272], 6603, "$chitin@0.10", [0.4, 1.5])
# Wind ripples on the pan's own -13 degrees, where the pan shows.
for i, (x, y, rx) in enumerate([(-30, -112, 90), (60, -84, 70), (150, 34, 60), (132, 92, 80), (40, 122, 96),
                                (-70, 116, 70), (176, -8, 40)]):
    put(f"ripple_{i}_lee", (x, y), ell(rx, 8), "$sand.dark@0.2", rot=-13)
    put(f"ripple_{i}_lit", (x, y - 1.5), ell(rx * 0.82, 3.6), "$chitin@0.12", rot=-13)
# Salt bloom where the crust still shows through.
BLOOMS = [(128, 64, 1.0), (-12, 118, 0.8), (174, 114, 0.7)]
BLOOM = [(43.2, -6.0), (40.0, 12.2), (20.3, 28.6), (-11.8, 23.1), (-35.1, 13.7), (-56.6, -4.2), (-35.8, -23.1),
         (-2.0, -23.2), (28.9, -23.0)]
for i, (x, y, s) in enumerate(BLOOMS):
    put(f"bloom_{i}", (x, y), poly([(px * s * 0.8, py * s * 0.8) for px, py in BLOOM]), "$husk@0.18")
    put(f"bloom_{i}_core", (x, y), poly([(px * s * 0.5, py * s * 0.5) for px, py in BLOOM]), "$husk@0.16")
# Cracks in the crust, each a dark cut under a pale lip.
CRACKS = [[(104, 118), (126, 112), (150, 118), (170, 110)], [(150, 50), (164, 38), (186, 34)],
          [(18, 112), (40, 120), (62, 114)]]
for c, pts in enumerate(CRACKS):
    for j in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[j], pts[j + 1]
        L = math.hypot(x1 - x0, y1 - y0)
        a = math.degrees(math.atan2(y1 - y0, x1 - x0))
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        put(f"crack_{c}_{j}_lip", (mx, my - 1.5), rect(L, 2, 1), "$husk@0.22", rot=a)
        put(f"crack_{c}_{j}", (mx, my), rect(L, 2, 1), "$ink@0.32", rot=a)

# ============================================================== the plains, west
PLAINS = [(-200, -140), (-96, -140), (-104, -112), (-126, -84), (-118, -52), (-134, -22), (-126, 12), (-142, 44),
          (-130, 78), (-112, 104), (-120, 140), (-200, 140)]
put("plains_fringe", None, poly(shift(PLAINS, 7, 3)), "$soil@0.35")
put("plains", None, poly(PLAINS), "$soil")
for k, f in enumerate((1.0, 0.68, 0.42)):
    put(f"plains_rise_{k}", (-176, -40), ell(60 * f, 90 * f), "$soil.light@0.08")
scatter("plains_grain_lit", (-164, 0), ell(7, 5), 40, [70, 272], 4111, "$soil.light@0.10", [0.35, 1.4])
scatter("plains_grain_dark", (-164, 0), ell(6, 4), 36, [70, 272], 4112, "$ink@0.16", [0.4, 1.5])
scatter("plains_flecks", (-164, 0), rect(3, 3, 0), 16, [70, 264], 4115, "$rust", [0.55, 1.5], jitter=False)
scatter("plains_specks", (-164, 0), rect(2, 2, 0), 22, [70, 264], 4116, "$rust.dark@heavy", [0.6, 1.5], jitter=False)
for r in parts[-2:]:
    r["repeat"]["of"].pop("corner")
put("plains_pit_0", (-176, 62), circ(5), "$ink@heavy")
put("plains_pit_1", (-150, -96), circ(3.5), "$ink@heavy")
# A scent trail still bleeding along the ground — and running over the lip
# into the funnel, which is this stage's sentence: whatever goes in stays in.
scatter("trail_chips", (-122, -18), rect(3, 3, 0), 26, [120, 18], 4211, "$pheromone@0.5", [0.45, 1.6], rot=12)
parts[-1]["repeat"]["of"].pop("corner")

# ============================================================== the burrow, north-east
BURROW = [(78, -140), (200, -140), (200, 10), (172, 2), (146, -8), (120, -26), (104, -52), (96, -84), (84, -110)]
put("burrow_fringe", None, poly(shift(BURROW, -6, 5)), "$dead.dark@0.4")
put("burrow", None, poly(BURROW), "$dead.dark")
scatter("burrow_grain", (150, -70), ell(9, 6), 26, [100, 130], 5111, "$carapace@0.07", [0.4, 1.6])
scatter("burrow_dark", (150, -70), ell(8, 5), 22, [100, 130], 5112, "$ink@0.22", [0.4, 1.5])
put("gouge_cut", (150, -44), {"kind": "ring", "r": 30, "width": 5, "from": 200, "to": 300}, "$ink@0.55")
put("gouge_lip", (150, -47), {"kind": "ring", "r": 30, "width": 2.5, "from": 208, "to": 292}, "$carapace.dark2@0.35")
scatter("burrow_grit", (150, -70), rect(4, 4, 0), 14, [100, 130], 5113, "$carapace.dark@0.7", [0.5, 1.4], jitter=False)
scatter("burrow_shell", (150, -70), rect(4, 3, 0), 8, [100, 130], 5117, "$husk@0.45", [0.5, 1.5])
for r in parts[-2:]:
    r["repeat"]["of"].pop("corner")
# Earth left standing: every contour first, then every fill, so no mass
# outlines the one beside it — the run's own two passes.
EARTH = [("h0", (152, -122), rect(132, 54, 27), -7), ("h1", (206, -60), rect(48, 110, 24), 4),
         ("n0", (104, -118), circ(24), 0), ("n1", (190, -110), circ(30), 0), ("n2", (196, -6), circ(24), 0)]
def grow(shape, d):
    s = dict(shape)
    if s["kind"] == "circle": s["r"] = r2(s["r"] + d)
    else: s["w"], s["h"], s["corner"] = r2(s["w"] + 2 * d), r2(s["h"] + 2 * d), r2(s["corner"] + d)
    return s
for eid, at, shape, rot in EARTH:
    put(f"rim_{eid}", at, grow(shape, 4), "$ink.dark", rot=rot)
for eid, at, shape, rot in EARTH:
    put(f"earth_{eid}", at, shape, "$carapace.dark", rot=rot)
FACES = [((128, -128), 5.5, 3.7, 20, "$ink@0.3"), ((166, -114), 6.2, 4.2, 127, "$carapace@0.16"),
         ((188, -128), 3.8, 2.6, 35, "$carapace.dark2@0.5"), ((104, -114), 5.0, 3.2, 95, "$ink@0.3"),
         ((200, -84), 5.6, 3.6, 70, "$carapace@0.16"), ((196, -44), 4.6, 3.0, 300, "$ink@0.3"),
         ((190, -2), 5.0, 3.4, 150, "$carapace@0.16"), ((142, -104), 3.6, 2.4, 250, "$carapace.dark2@0.5"),
         ((206, -22), 3.4, 2.2, 40, "$carapace.dark2@0.5")]
for i, (at, rx, ry, rot, fill) in enumerate(FACES):
    put(f"earth_face_{i}", at, ell(rx, ry), fill, rot=rot)

# ============================================================== the seams (§3.3)
prop("seam_fissure_n", (-118, -64), "ss.terrain.fissure", 0.9, rot=78)
prop("seam_fissure_s", (-132, 60), "ss.terrain.fissure", 0.85, rot=62)
prop("seam_rubble_a", (100, -40), "ss.terrain.rubble", 0.9)
prop("seam_rubble_b", (150, 4), "ss.terrain.rubble", 0.8)

# ============================================================== props round the rim
# plains: a thicket of spires where the trail crystallised, a boulder, a vent
prop("spire_wa", (-162, -58), "ss.terrain.spire", 1.2)
prop("spire_wb", (-134, -40), "ss.terrain.spire", 0.82)
prop("spire_wc", (-178, -26), "ss.terrain.spire", 0.7)
prop("boulder_w", (-164, 52), "ss.terrain.boulder", 1.0)
prop("vent_w", (-150, 104), "ss.terrain.vent", 0.85)
# burrow: fungi on the chamber floor
prop("fungi_ne", (150, -54), "ss.terrain.fungi", 0.85)
prop("fungi_nn", (116, -76), "ss.terrain.fungi", 0.62)
# pan: a heaved plate, fused glass, a ribcage half in the drift
prop("saltplate_e", (156, 66), "ss.terrain.saltplate", 1.05)
prop("saltplate_s", (112, 106), "ss.terrain.saltplate", 0.72)
prop("glass_se", (178, 108), "ss.terrain.glass", 0.8)
prop("ribcage_s", (-72, 116), "ss.terrain.ribcage", 0.72)

scatter("glints", (0, 0), rect(3, 3, 0), 50, [400, 272], 6621, "$silent@0.55", [0.45, 1.3], jitter=False)
parts[-1]["repeat"]["of"].pop("corner")

# ============================================================== the pit
prop("funnel", FUNNEL_AT, "ss.terrain.funnel", FUNNEL_SCALE)
# the trail does not stop at the lip: a last few chips going down the slope
scatter("trail_in", (-74, -9), rect(3, 3, 0), 9, [44, 10], 4212, "$pheromone@0.4", [0.4, 1.2], rot=8)
parts[-1]["repeat"]["of"].pop("corner")

for p in parts:
    s = p.get("shape")
    if s and s.get("kind") == "rect" and s.get("corner") == 0: s.pop("corner")

doc = {
    "id": "ss.env.stage-pit",
    "name": "Pit stage card (SS)",
    "description": (
        "The picture on the Pit card (개미지옥) in Feelers' map select: the fourth stage, the one that never ends, "
        "drawn once from the camera's own height like the other three.\n\n"
        "The Pit is the other three stages in one run — plains, burrow and salt pan laid in 1800px zones, with sand "
        "funnels dug into the desert — so the card is all three round one hole. In the middle, `use: "
        "ss.terrain.funnel`: the run's own pit, the lip spilling pale sand onto whatever it was dug in, the slope "
        "stepping down to the throat with its tongues of sand running in and the antlion's jaws just showing. "
        "Round its rim the grounds lie in patches, each in its own card's inks and with its own props: the plains "
        "west ($soil, a thicket of spires, a boulder, a vent), with a pink scent trail running over the lip and into "
        "the funnel, which is the stage's one sentence; the burrow north-east ($dead.dark under $carapace.dark "
        "earth on its $ink.dark contour, drawn in the run's two passes, fungi on the chamber floor); and the pan "
        "everywhere else, the floor the pit is dug in, with its ripples on -13 degrees, salt bloom, cracks, plates "
        "heaved on edge, fused glass and a ribcage half in the drift. The patches meet at the seams the run "
        "decorates (feelers docs/pit-plan.md §3.3): a `fissure` where sand meets plains, `rubble` where the burrow "
        "meets anything.\n\n"
        "Every ink is one the other three cards use. Authored 3:2 like them: the card fits it to the strip's width "
        "and crops it vertically, so the pit sits on the middle band and the patches run off the left and right "
        "edges, where the frame is the only thing that cuts them."
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
