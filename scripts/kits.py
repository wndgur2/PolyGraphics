"""The effect kits of the motion plan (feelers docs/motion-vfx-plan.md §4.4, §8).

    python3 scripts/kits.py        # rewrites the documents below

One script for the small effects the arsenal shares, so they share a grammar:

- the player's marks are cold and do not glow (brand guide §7.2), so every kit
  sits on ink — the first part is the same shape in `$ink`, a little larger —
  and what lifts it off a pale floor is the dark under it, not light;
- they let go in held steps (`hold` keys), not a smooth fade — the stepped
  rhythm of the baked clips;
- pink is the hive's: the lure's pod may carry it, its burst may not.

`ss.fx.cut`, `ss.fx.smear` and `ss.fx.impact` were drawn by hand in P1 and are
left as they are; this script draws the ones P3 asks for, and adds clips to
two projectiles that had none.
"""
import json, math, os

ROOT = os.path.join(os.path.dirname(__file__), "..", "apps", "ss", "assets")
r2 = lambda x: round(x, 2)

def write(doc):
    path = os.path.join(ROOT, doc["id"].replace(".", "-") + ".json")
    with open(path, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("wrote", os.path.relpath(path), len(doc["parts"]), "parts")

def load(id_):
    with open(os.path.join(ROOT, id_.replace(".", "-") + ".json")) as f:
        return json.load(f)

# a stepped let-go: full, then two held values, then gone
def steps(start=0.55, mid=0.8, a=1.0):
    return [[0, a, "hold"], [start, a * 0.6, "hold"], [mid, a * 0.3, "hold"], [1, 0]]

def ring(id_, r, w, fill, frm=None, to=None):
    shape = {"kind": "ring", "r": r, "width": w}
    if frm is not None: shape.update({"from": frm, "to": to})
    return {"id": id_, "shape": shape, "fill": fill}

def circ(id_, r, fill, at=(0, 0)):
    return {"id": id_, "at": [r2(at[0]), r2(at[1])], "shape": {"kind": "circle", "r": r}, "fill": fill}

def poly(id_, pts, fill, at=(0, 0), rot=None):
    p = {"id": id_, "at": [r2(at[0]), r2(at[1])], "shape": {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in pts]}, "fill": fill}
    if rot is not None: p["rot"] = rot
    return p

def blob(n, r, wobble, seed):
    """A closed irregular outline: n points round a circle, each pushed in or out."""
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + wobble * math.sin(seed + i * 2.399) * math.cos(seed * 0.7 + i * 1.3)
        out.append((r * k * math.cos(a), r * k * math.sin(a)))
    return out

# ============================================================== Spore: the burst
def spore_burst():
    R = 30  # the authored reach: the game scales by blast radius / 30, as it does fx.blast
    parts = [
        circ("ink", 9, "$ink"),
        circ("flash", 8, "$silent"),
        ring("ink_wave", R * 0.7, 6.5, "$ink"),
        ring("wave", R * 0.7, 4.0, "$frost.light"),
        ring("wave_far", R * 0.95, 2.2, "$frost"),
    ]
    puffs = []
    for i in range(8):
        a = 2 * math.pi * (i + 0.3 * (i % 2)) / 8
        d = R * (0.38 + 0.19 * ((i * 5) % 4))  # four distances, scattered round the ring
        parts.append(circ(f"spore_{i}", 3.2 - 0.5 * (i % 3), "$ochre" if i % 2 else "$husk", (math.cos(a) * d * 0.35, math.sin(a) * d * 0.35)))
        puffs.append((f"spore_{i}", math.cos(a) * d, math.sin(a) * d))
    chips = []
    for i, (a, fill) in enumerate(((0.6, "$husk.dark"), (2.3, "$ochre"), (3.9, "$husk.dark"), (5.2, "$ochre"))):
        parts.append(poly(f"chip_{i}", [(0, -1.8), (2.6, 0.4), (-1.2, 1.6)], fill, (math.cos(a) * 4, math.sin(a) * 4), rot=int(math.degrees(a))))
        chips.append((f"chip_{i}", math.cos(a) * R * 0.95, math.sin(a) * R * 0.95))
    tr = [
        # the impact frame: one white frame, then the core holds and goes in steps
        {"part": "flash", "prop": "scale", "keys": [[0, 1.6, "hold"], [0.08, 1.0, "quadOut"], [0.4, 0.6]]},
        {"part": "flash", "prop": "opacity", "keys": steps(0.3, 0.5)},
        {"part": "ink", "prop": "scale", "keys": [[0, 1.7, "hold"], [0.08, 1.1, "quadOut"], [0.4, 0.7]]},
        {"part": "ink", "prop": "opacity", "keys": steps(0.3, 0.5, 0.9)},
        # the wave: out fast, thinning
        {"part": "wave", "prop": "scale", "keys": [[0, 0.25, "expoOut"], [0.55, 1.0, "sine"], [1, 1.08]]},
        {"part": "ink_wave", "prop": "scale", "keys": [[0, 0.25, "expoOut"], [0.55, 1.0, "sine"], [1, 1.08]]},
        {"part": "wave", "prop": "opacity", "keys": steps(0.45, 0.7)},
        {"part": "ink_wave", "prop": "opacity", "keys": steps(0.45, 0.7, 0.85)},
        {"part": "wave_far", "prop": "scale", "keys": [[0, 0.2, "expoOut"], [0.7, 1.0, "sine"], [1, 1.05]]},
        {"part": "wave_far", "prop": "opacity", "keys": [[0, 0, "hold"], [0.1, 0.9, "hold"], [0.6, 0.5, "hold"], [0.85, 0.2, "hold"], [1, 0]]},
    ]
    for pid, x, y in puffs:
        tr += [{"part": pid, "prop": "x", "keys": [[0, x * 0.35, "expoOut"], [1, x]]},
               {"part": pid, "prop": "y", "keys": [[0, y * 0.35, "expoOut"], [1, y - 3]]},
               {"part": pid, "prop": "scale", "keys": [[0, 0.6, "quadOut"], [0.5, 1.3, "sine"], [1, 1.6]]},
               {"part": pid, "prop": "opacity", "keys": steps(0.6, 0.85)}]
    for pid, x, y in chips:
        tr += [{"part": pid, "prop": "x", "keys": [[0, 0, "expoOut"], [1, x]]},
               {"part": pid, "prop": "y", "keys": [[0, 0, "expoOut"], [0.6, y - 4, "quadIn"], [1, y + 2]]},
               {"part": pid, "prop": "rot", "keys": [[0, 0, "linear"], [1, 260]]},
               {"part": pid, "prop": "opacity", "keys": steps(0.7, 0.9)}]
    write({
        "id": "ss.fx.spore-burst", "name": "Spore burst",
        "description": "What a tripped Spore lure lets go of: a white frame and a cold core, a wave out to the blast's edge, eight puffs of spore in the husk's ochre and four flakes of the case thrown clear. The pod that called the swarm is pink; what comes out of it is not — the hive's colour is the call, and the call is over. Everything sits on ink and goes in held steps. Authored so the wave reaches r=30 at full: the game scales it by the blast radius over 30, the way it scales fx.blast.",
        "tags": ["fx", "blast", "kit"], "size": [80, 80], "meta": {"authoredR": R},
        "parts": parts,
        "animations": {"play": {"description": "a white frame; the wave goes out and thins; the spores billow and drift up; the flakes fly and drop — 0.36s, held steps throughout", "duration": 0.36, "cues": {"impact": 0.0}, "tracks": tr}},
    })

# ============================================================== Spore: the ground it leaves
def scorch():
    parts = [poly("burn", blob(14, 13, 0.18, 1.7), "$ink@heavy"),
             poly("rim", blob(14, 13, 0.18, 1.7), "$ochre.dark@soft", rot=8),
             poly("core", blob(10, 6.5, 0.25, 4.1), "$ink"),
             circ("fleck_a", 1.4, "$ochre@soft", (8, -5)), circ("fleck_b", 1.1, "$husk@soft", (-9, 3)), circ("fleck_c", 0.9, "$ochre@soft", (3, 9))]
    # the rim is the burn's outline, a hair larger, under it
    parts[1]["scale"] = 1.12
    parts = [parts[1], parts[0]] + parts[2:]
    write({
        "id": "ss.fx.scorch", "name": "Scorch",
        "description": "Where a Spore went off: a dark burn with an ochre rim and a few flecks of spore still on it. Ground, not light — it says something happened here and does not say it loudly. No clip: the game sets it down at the blast's size and lets it go in held steps over three quarters of a second, so a field of them stays a field rather than a pattern.",
        "tags": ["fx", "decal", "kit"], "size": [32, 32], "meta": {"authoredR": 13},
        "parts": parts,
    })

# ============================================================== Spit: a droplet
def droplet():
    drop = lambda L, w: [(-L * 0.5, 0), (-L * 0.1, -w / 2), (L * 0.3, -w * 0.42), (L * 0.5, 0), (L * 0.3, w * 0.42), (-L * 0.1, w / 2)]
    parts = [poly("ink", drop(9.4, 5.6), "$ink"), poly("body", drop(8, 4.4), "$bile"), circ("glint", 0.9, "$bile.light2", (1.6, -0.8))]
    tr = []
    for pid in ("ink", "body", "glint"):
        tr += [{"part": pid, "prop": "scaleX", "keys": [[0, 1.3, "quadOut"], [0.5, 1.0, "sine"], [1, 0.7]]},
               {"part": pid, "prop": "scaleY", "keys": [[0, 0.8, "quadOut"], [0.5, 1.0, "sine"], [1, 0.7]]},
               {"part": pid, "prop": "opacity", "keys": steps(0.5, 0.75)}]
    write({
        "id": "ss.fx.droplet", "name": "Droplet",
        "description": "One drop of Spit's acid off the glob or the mouth, pointing +x (the game turns it to where it is flying): stretched on the way out, round as it slows, gone in held steps. The bile of the weapon's own tile, on ink, with one bright point — the acid is the colour, not a glow.",
        "tags": ["fx", "kit"], "size": [16, 12],
        "parts": parts,
        "animations": {"play": {"description": "stretched, rounding, shrinking, gone — 0.22s", "duration": 0.22, "tracks": tr}},
    })

# ============================================================== Chirp, Spore: a ring
def shock():
    R = 30
    parts = [ring("ink", R, 6, "$ink"), ring("edge", R, 3.4, "$silent"), ring("trail", R * 0.82, 1.6, "$frost.light")]
    tr = [
        {"part": "ink", "prop": "scale", "keys": [[0, 0.2, "expoOut"], [1, 1]]},
        {"part": "edge", "prop": "scale", "keys": [[0, 0.2, "expoOut"], [1, 1]]},
        {"part": "trail", "prop": "scale", "keys": [[0, 0.2, "expoOut"], [1, 1]]},
        {"part": "ink", "prop": "opacity", "keys": steps(0.5, 0.75, 0.8)},
        {"part": "edge", "prop": "opacity", "keys": steps(0.5, 0.75)},
        {"part": "trail", "prop": "opacity", "keys": [[0, 0.8, "hold"], [0.4, 0.4, "hold"], [0.7, 0, "hold"], [1, 0]]},
    ]
    write({
        "id": "ss.fx.shock", "name": "Shock ring",
        "description": "A small ring thrown out from a point — a staff striking the ground, a pod landing, an awakening — white on ink, a thinner frost ring inside it. Out fast and let go in held steps. White so the game can tint it to the weapon (a multiply on white is the colour), and authored at r=30 so it scales by radius over 30.",
        "tags": ["fx", "kit"], "size": [72, 72], "meta": {"authoredR": R},
        "parts": parts,
        "animations": {"play": {"description": "out from the point, thinning, gone in held steps — 0.24s", "duration": 0.24, "cues": {"impact": 0.0}, "tracks": tr}},
    })

# ============================================================== Vine: the ground before it breaks
def crack():
    arms = []
    for i, (a, L) in enumerate(((10, 11), (95, 8), (170, 12), (250, 9), (320, 7))):
        ra = math.radians(a)
        mid = (math.cos(ra) * L * 0.5 + math.sin(ra) * 1.2, math.sin(ra) * L * 0.5 - math.cos(ra) * 1.2)
        end = (math.cos(ra) * L, math.sin(ra) * L)
        w = 1.4
        arms.append(poly(f"arm_{i}", [(0, -w), mid, end, (mid[0] + w * 0.6, mid[1] + w * 0.6), (0, w)], "$ink"))
    # a patch of turned earth a step lighter than the floor, so the ink cracks
    # read on it, and a lifted clod at the middle, not a disc
    parts = [poly("heave", blob(12, 11, 0.15, 2.2), "$rust"), *arms, poly("lip", blob(7, 2.8, 0.3, 0.9), "$rust.light", (0, 0))]
    tr = [{"part": p["id"], "prop": "scale", "keys": [[0, 0.3, "expoOut"], [0.5, 1.0, "hold"], [1, 1.0]]} for p in parts]
    tr.append({"part": "lip", "prop": "y", "keys": [[0, 0, "quadOut"], [0.5, -1.2, "hold"], [1, -1.2]]})
    write({
        "id": "ss.fx.crack", "name": "Ground crack",
        "description": "The ground about to give: a heave of earth and five dark cracks running out from a lifted lip — the Vine's tell, set down where a vine is about to come up. It is the field's warning in the field's own material, so it is fair to whatever stands there and reads as soil, not as an interface. Opens fast, then holds until the vine breaks through.",
        "tags": ["fx", "decal", "kit"], "size": [32, 32],
        "parts": parts,
        "animations": {"open": {"description": "the cracks run out and the lip lifts, then hold — 0.12s", "duration": 0.12, "cues": {"open": 0.5}, "tracks": tr}},
    })

# ============================================================== Vine, Thicket: a leaf
def leaf():
    pts = [(-4, 0), (-1.5, -2.2), (2.5, -1.6), (4.2, 0), (2.5, 1.6), (-1.5, 2.2)]
    parts = [poly("ink", [(x * 1.2, y * 1.25) for x, y in pts], "$ink"), poly("blade", pts, "$moss.light"), poly("vein", [(-3.6, -0.2), (3.8, -0.1), (3.8, 0.2), (-3.6, 0.3)], "$moss")]
    tr = []
    for p in parts:
        tr += [{"part": p["id"], "prop": "rot", "keys": [[0, 0, "sine"], [0.5, 140, "sine"], [1, 250]]},
               {"part": p["id"], "prop": "scaleY", "keys": [[0, 1, "sine"], [0.25, 0.3, "sine"], [0.5, 1, "sine"], [0.75, 0.3, "sine"], [1, 1]]},
               {"part": p["id"], "prop": "opacity", "keys": steps(0.6, 0.85)}]
    write({
        "id": "ss.fx.leaf", "name": "Leaf",
        "description": "One leaf off a vine going back into the ground, or off a thicket's swing: turning over as it falls (the flip is in the frames, so the game can fling it as a particle that cannot rotate), the moss of the vine on ink.",
        "tags": ["fx", "kit"], "size": [16, 16],
        "parts": parts,
        "animations": {"fall": {"description": "turning over twice as it drops, gone in held steps — 0.6s", "duration": 0.6, "tracks": tr}},
    })

# ============================================================== Mandible: a blur to spin with
def boom_spin():
    d = load("ss.proj.boom")
    if not any(p["id"] == "blur" for p in d["parts"]):
        # under the jaws: the disc the jaws sweep at speed
        d["parts"].insert(0, {"id": "blur", "shape": {"kind": "circle", "r": 8.6}, "fill": "$chitin@ghost"})
        d["parts"].insert(1, {"id": "blur_rim", "shape": {"kind": "ring", "r": 8.2, "width": 1.6}, "fill": "$chitin.light@soft"})
    jaws = [p["id"] for p in d["parts"] if p["id"] not in ("blur", "blur_rim")]
    tr = [{"part": "blur", "prop": "opacity", "keys": [[0, 0, "hold"], [0.5, 1, "hold"], [1, 1]]},
          {"part": "blur_rim", "prop": "opacity", "keys": [[0, 0, "hold"], [0.5, 1, "hold"], [1, 1]]}]
    tr += [{"part": pid, "prop": "opacity", "keys": [[0, 1, "hold"], [0.5, 0.35, "hold"], [1, 0.35]]} for pid in jaws]
    d.setdefault("animations", {})["spin"] = {
        "description": "two frames that alternate while the game turns the sprite: the jaws sharp, then the jaws faint inside the disc they sweep — a blur in frames, since a bake cannot blur. Played fast while it flies and held on the sharp frame at the top of its throw, where it all but stops.",
        "duration": 0.1, "tracks": tr}
    write(d)

# ============================================================== Broodling: a grub that crawls and bites
def chip_clips():
    d = load("ss.proj.chip")
    ids = [p["id"] for p in d["parts"]]
    tr = []
    for pid in ids:
        tr.append({"part": pid, "prop": "scaleX", "keys": [[0, 1, "sine"], [0.5, 1.18, "sine"], [1, 1]]})
        tr.append({"part": pid, "prop": "scaleY", "keys": [[0, 1, "sine"], [0.5, 0.86, "sine"], [1, 1]]})
    if "seg" in ids:
        tr.append({"part": "seg", "prop": "x", "keys": [[0, 0, "sine"], [0.5, -0.8, "sine"], [1, 0]]})
    bite = []
    for pid in ids:
        bite.append({"part": pid, "prop": "x", "keys": [[0, 0, "quadOut"], [0.3, -1.4, "hold"], [0.4, -1.4, "expoOut"], [0.55, 2.2, "quadOut"], [1, 0]]})
        bite.append({"part": pid, "prop": "scaleX", "keys": [[0, 1, "quadOut"], [0.3, 0.8, "hold"], [0.4, 0.8, "expoOut"], [0.55, 1.3, "quadOut"], [1, 1]]})
    d.setdefault("animations", {})
    d["animations"]["crawl"] = {"description": "the grub inches: stretched, gathered, stretched — the game turns it toward what it is after", "duration": 0.24, "cues": {"contact": 0.5}, "tracks": tr}
    d["animations"]["bite"] = {"description": "draws back and holds, lunges, recoils — the evolved grub's three bites are this three times", "duration": 0.3, "cues": {"bite": 0.55}, "tracks": bite}
    v = d.get("variants", {}).get("evolved")
    if v is not None:
        v["animations"] = ["crawl", "bite"]
    write(d)

if __name__ == "__main__":
    spore_burst(); scorch(); droplet(); shock(); crack(); leaf(); boom_spin(); chip_clips()
