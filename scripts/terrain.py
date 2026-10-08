"""The field's props — what stands on the Plains, in the burrow's chambers and in the ruins.

    python3 scripts/terrain.py     # rewrites thirteen apps/ss/assets/ss-terrain-*.json

These were ports of feelers' first procedural draws: a triangle for a spire, an
ellipse with three dots for a boulder, a grey rectangle for a pillar. Beside the
base's props (`base.py`) they were the least drawn things in the game, and they
are the first things a run stands next to. They are drawn here the way the
camp's things are (feelers `docs/staging-method.md` §8): one big form, a few
middle forms, small detail gathered on a third of it; light from the upper
left with a lit edge on the top-left corner of every mass; the dark where a
thing meets the ground; wear that says what happened to it; a broken
silhouette.

Every document keeps its size, its anchor and its shadow where the old one
had them, because feelers fits the collider to the drawing's footprint
(`data/terrain.ts`), and a prop that grew would stop a body short of its face.

Colour follows ownership (guide §7): the spire, the vent's breath, the ruins'
core and the chitin are the hive's — pink is the signal and amber the hive's
material; the boulder, the pillar, the arch and the slab are stone, cut or
weathered, in slate and smoke; the fungi are the world's teal; the husk is bone
that ran out of scent. Flat values only: the bake flattens gradients, so a
round thing is three bands and a glow is a few rings.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import r2, poly, ell, circ, rect, write_doc  # noqa: E402
from draw import P, R, clip, shaded, shadow, band, halo, lit_edge, ao, INK_THIN, INK_HAIR  # noqa: E402

# The ink line a prop is closed with when it is drawn over the fills, the way
# `shaded` and the spire's shards draw it. Over the fills the whole width
# shows, where a body's `thin` stroke under its own parts shows only its outer
# half — so the same token drew props twice as heavy as the bodies beside them,
# and feelers scatters them at up to 2.3x on top of that. `hair` drawn over is
# the `thin` a body shows.
RIM = INK_HAIR

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets")


def doc(id, name, description, size, parts, animations=None, tags=("terrain",)):
    ids = [p["id"] for p in parts]
    assert len(ids) == len(set(ids)), f"{id}: duplicate part ids {[i for i in ids if ids.count(i) > 1]}"
    d = {"id": id, "name": name, "description": description, "tags": list(tags), "size": list(size),
         "parts": parts, "animations": animations or {}}
    write_doc(d, os.path.join(OUT, id.replace(".", "-") + ".json"))
    print(f"{id}: {len(parts)} parts")


def cut(id, pts, lo, hi, fill, axis=1):
    """The band of polygon `pts` between lo and hi on `axis`, as one part — a face of a mass."""
    c = clip(pts, axis, lo, hi)
    return P(id, poly(c), fill) if len(c) >= 3 else None


def facet(id, pts, left_fill, right_fill, split=0.0):
    """A crystal shard split down a vertical line: the lit face to the left of it, the shade to the right."""
    out = []
    l = clip(pts, 0, -1e9, split)
    r = clip(pts, 0, split, 1e9)
    if len(l) >= 3: out.append(P(f"{id}_lit", poly(l), left_fill))
    if len(r) >= 3: out.append(P(f"{id}_shade", poly(r), right_fill))
    return out


def lump(cx, cy, rx, ry, seed, n=14, rough=0.14):
    """An irregular rounded outline — a stone — as points, bumped by a fixed little generator."""
    s = seed
    pts = []
    for i in range(n):
        s = (s * 1103515245 + 12345) % 2147483648
        k = 1 + (s / 2147483648 - 0.5) * 2 * rough
        a = 2 * math.pi * i / n
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    return pts


def crack(id, pts, w=0.9, fill="$ink@0.55", lip=None, lip_at=(-0.6, -0.6)):
    out = []
    if lip:
        out.append(band(f"{id}_lip", [(x + lip_at[0], y + lip_at[1]) for x, y in pts], w, lip))
    out.append(band(id, pts, w, fill))
    return out


def pebble(id, x, y, rx, ry, fill="$slate.light", rot=0.0):
    return [
        P(f"{id}_sh", ell(rx, ry * 0.8), "$ink@0.4", at=(x + 0.6, y + 0.8), rot=rot),
        P(id, ell(rx, ry), fill, at=(x, y), rot=rot, stroke=INK_HAIR),
        P(f"{id}_lit", circ(min(rx, ry) * 0.32), "$white@0.4", at=(x - rx * 0.3, y - ry * 0.35)),
    ]


# ================================================================== the Plains
def spire():
    """Crystallised pheromone trail: three shards, faceted, the big one lit down its left face."""
    def shard(id, apex, base_l, base_r, lit, mid, dark, edge=True):
        pts = [apex, base_r, base_l]
        # Facets: the left face lit, the right in shade; a third, darker sliver on the far right.
        split = apex[0] + (base_r[0] - apex[0]) * 0.08
        out = [P(f"{id}_body", poly(pts), mid)]
        out += facet(id, pts, lit, dark, split)
        far = clip(pts, 0, apex[0] + (base_r[0] - apex[0]) * 0.62, 1e9)
        if len(far) >= 3: out.append(P(f"{id}_far", poly(far), "$ink@0.22"))
        # A pale catch of light down the lit edge, which is what says glass rather than paint.
        if edge:
            out.append(band(f"{id}_edge", [(apex[0] + (base_l[0] - apex[0]) * 0.12, apex[1] + (base_l[1] - apex[1]) * 0.12),
                                           (apex[0] + (base_l[0] - apex[0]) * 0.8, apex[1] + (base_l[1] - apex[1]) * 0.8)], 0.9, "$white@0.5"))
        out.append(P(f"{id}_rim", poly(pts), None, stroke=RIM))
        return out

    parts = [
        shadow("shadow", 0, 20, 15, 4.5),
        # The hive's light on the ground round a live spire: faint, in rings.
        *halo("glow", 0, 18, 15, 4.2, 0.16, "$pheromone", 4),
        *shard("left", (-11, 1), (-16, 19), (-6, 19), "$pheromone.light", "$pheromone.dark", "$pheromone.dark2"),
        *shard("right", (11, -5), (6, 19), (17, 19), "$pheromone.light", "$pheromone.dark", "$pheromone.dark2"),
        *shard("main", (0, -21), (-9, 19), (9, 19), "$pheromone.light", "$pheromone", "$pheromone.dark"),
        # A smaller crystal budding off the big one's foot, and chips of it on the ground.
        *shard("bud", (-6, 8), (-9, 19), (-3, 19), "$pheromone.light2", "$pheromone.light", "$pheromone", edge=False),
        P("chip_a", poly([(12, 20), (14, 17.6), (16.4, 20)]), "$pheromone.dark", stroke=INK_HAIR),
        P("chip_b", poly([(-16, 20.4), (-14.2, 18.4), (-12, 20.4)]), "$pheromone.dark2", stroke=INK_HAIR),
        # The signal, lit from inside near the tip: the one part of a spire that glows.
        P("core", poly([(0, -15), (2, -5), (-2, -5)]), "$pheromone.light2@0.85"),
        P("core_hot", poly([(0, -13), (0.9, -8), (-0.9, -8)]), "$white@0.6"),
        # Where the shards meet the ground, the dark under them.
        ao("foot_ao", 0, 18.6, 24, 1.8, 0.3),
    ]
    doc(
        "ss.terrain.spire",
        "Pheromone spire",
        "A crystallised pheromone trail on the Plains (data/terrain.ts `spire`): three shards grown out of the dirt, each faceted — "
        "the left face lit, the right in shade, a darker sliver on the far right and a pale catch of light down the lit edge, which "
        "is what says glass rather than paint. A smaller crystal buds off the big one's foot and chips of it lie at the base. The "
        "signal glows near the tip of the big shard, lit from inside, and lays a faint pink on the ground in rings: the hive's light, "
        "and the one part of a spire that shines. The cut spires at the camp (`ss.base.stump`) are this with the signal gone out of them. "
        "Shadow and footprint where the old document had them. Closed in a `hair` line drawn over its fills, which shows as heavy as a body's `thin` (docs/ss-art-rules.md §3). Generated by scripts/terrain.py.",
        (36, 46), parts,
    )


def boulder():
    """A weathered stone with lichen on its lit side and the hive's spores grown into its pits."""
    body = lump(0, 0, 19, 14.5, 41, 16, 0.1)
    parts = [
        shadow("shadow", 0, 14, 19, 4.5),
        *shaded("body", body, "$slate.light", [(-20, -6, "$slate.light2"), (6, 20, "$slate.dark")], stroke=RIM),
        # A second, lower band of shade at the foot, and the dark where it meets the ground.
        cut("foot", body, 10, 20, "$slate.dark2@0.7"),
        ao("foot_ao", 0, 14.2, 30, 1.8, 0.32),
        # Lit edge along the top-left shoulder.
        band("shoulder", [(-14, -8), (-8, -12), (0, -13.4)], 1.0, "$white@0.35"),
        # Cracks: one long, one short, each with a lit lip.
        *crack("crack_a", [(-12, 2), (-6, 5), (-2, 11)], 0.9, "$ink@0.5", "$steel@0.25"),
        *crack("crack_b", [(8, -9), (11, -4)], 0.8, "$ink@0.45", "$steel@0.2"),
        # Lichen on the lit side, the world's teal gone grey-green on stone.
        P("lichen_a", poly(lump(-9, -6, 5.5, 3.2, 7, 10, 0.3)), "$verdigris@0.55"),
        P("lichen_b", poly(lump(2, -10, 3.4, 1.8, 11, 8, 0.3)), "$verdigris@0.45"),
        # Spore pits: a dark socket, the spore glowing in it, and the glow on the stone round it.
        *[p for i, (x, y, r) in enumerate([(-9, 3, 2.6), (6, 5, 2.2), (1, -7, 1.8)]) for p in [
            P(f"pit{i}", circ(r * 1.25), "$ink@0.7", at=(x, y + 0.3)),
            P(f"pit{i}_glow", circ(r * 1.9), "$spore@0.14", at=(x, y)),
            P(f"spore{i}", circ(r), "$spore.dark", at=(x, y)),
            P(f"spore{i}_lit", circ(r * 0.38), "$spore.light2@0.9", at=(x - r * 0.3, y - r * 0.3)),
        ]],
        # A pebble split off it, lying at the foot.
        *pebble("pebble", 16, 12, 2.6, 1.7, "$slate.light", -15),
    ]
    doc(
        "ss.terrain.boulder",
        "Spore boulder",
        "A weathered stone on the Plains (data/terrain.ts `boulder`), in three values with the light on its top-left shoulder and a "
        "lit edge along it, the shade and the dark of the ground at its foot. Two cracks with a lit lip, lichen on the lit side "
        "(the world's teal gone grey-green on stone), and three pits the hive's spores have grown into — a dark socket, the spore in "
        "it, its glow on the stone round it: the hive's light, which is why they are the brightest thing on the rock. A pebble split "
        "off it lies at the foot. Shadow and footprint where the old document had them. Closed in a `hair` line drawn over its fills, which shows as heavy as a body's `thin` (docs/ss-art-rules.md §3). Generated by scripts/terrain.py.",
        (44, 38), parts,
    )


def vent():
    """A fumarole mound breathing the hive's scent: a crusted rim, a throat lit from below, three wisps."""
    rim = lump(0, 6, 14, 6.5, 23, 18, 0.08)
    parts = [
        *shaded("rim", rim, "$smoke.dark", [(0.5, 20, "$smoke.dark2")], stroke=RIM),
        P("mound", poly(lump(0, 5.6, 11.5, 4.6, 29, 16, 0.06)), "$smoke"),
        P("mound_lit", poly(clip(lump(0, 5.6, 11.5, 4.6, 29, 16, 0.06), 1, -20, 5)), "$smoke.light@0.5"),
        lit_edge("rim_lit", -9, -1, 1.6, 0.9, "$white@0.3"),
        # The crust is cracked round the throat, and the cracks glow where the breath comes up.
        *[band(f"vein{i}", [(x0, y0), (x1, y1)], 0.8, "$pheromone@0.4") for i, (x0, y0, x1, y1) in enumerate(
            [(-6, 4, -11, 7), (6, 3, 11, 5), (-3, 7, -6, 10.5), (4, 7, 7, 10)])],
        P("throat_o", ell(6.6, 2.9), "$ink", at=(0, 5)),
        P("throat", ell(6, 2.5), "$ink", at=(0, 5)),
        # Lit from below: the signal, deep in the throat.
        P("ember", ell(3.8, 1.5), "$pheromone@0.5", at=(0, 5.3)),
        P("ember_hot", ell(1.8, 0.7), "$pheromone.light2@0.85", at=(0.4, 5.4)),
        # The breath: three wisps rising and thinning, each a soft pair.
        *[p for i, (x, y, r, a) in enumerate([(0, -1, 3.4, 0.5), (-3, -6, 2.6, 0.32), (2, -10, 2.2, 0.18)]) for p in [
            P(f"wisp{i}_soft", circ(r * 1.5), f"$pheromone@{r2(a * 0.35)}", at=(x, y)),
            P(f"wisp{i}", circ(r), f"$pheromone@{a}", at=(x, y)),
        ]],
        # Scent dried on the rim where the breath settles.
        P("stain", ell(4, 1.4), "$pheromone@0.18", at=(-5, 9.5), rot=-12),
    ]
    doc(
        "ss.terrain.vent",
        "Scent vent",
        "A fumarole mound on the Plains (data/terrain.ts `vent`), breathing the hive's scent: a crusted rim in two values with a "
        "lit edge on its top-left, the mound lit on top, and the throat dark with the signal glowing deep in it — lit from below, "
        "the exception the rules allow a light inside a thing. The crust is cracked round the throat and the cracks glow where the "
        "breath comes up; three wisps rise and thin, each a soft pair so the breath is smoke and not three dots; scent has dried on "
        "the rim where it settles. feelers pulses its alpha. Rim where the old document had it. Closed in a `hair` line drawn over its fills, which shows as heavy as a body's `thin` (docs/ss-art-rules.md §3). Generated by scripts/terrain.py.",
        (30, 26), parts,
    )


def fungi():
    """Three caps of the hive's fungus, lit on top, speckled, gilled underneath, a glow on the ground."""
    def shroom(prefix, x, y, rx, ry, stem_h, lean=0.0):
        cap = ell(rx, ry)
        return [
            # Stem: pale, with a line of shade down its right and a frill where the cap sits.
            P(f"{prefix}_stem", R(3, stem_h, 1.2), "$steel.light", at=(x + lean, y + stem_h / 2), stroke=INK_HAIR),
            P(f"{prefix}_stem_shade", R(1.1, stem_h - 1, 0.5), "$steel.dark@0.5", at=(x + lean + 0.9, y + stem_h / 2 + 0.5)),
            P(f"{prefix}_frill", ell(rx * 0.55, ry * 0.32), "$steel.light2", at=(x, y + ry * 0.55)),
            P(f"{prefix}_gills", ell(rx * 0.55, ry * 0.32), None, at=(x, y + ry * 0.55), stroke=INK_HAIR),
            # Cap: the teal, lit on its upper left, dark along its underside, outlined.
            P(f"{prefix}_cap", cap, "$spore.dark", at=(x, y), stroke=INK_THIN),
            P(f"{prefix}_cap_lit", ell(rx * 0.78, ry * 0.62), "$spore@0.55", at=(x - rx * 0.12, y - ry * 0.22)),
            P(f"{prefix}_cap_under", poly(clip([(x + rx * math.cos(a * math.pi / 8), y + ry * math.sin(a * math.pi / 8)) for a in range(16)], 1, y + ry * 0.45, y + ry + 1)), "$spore.dark2@0.8"),
            P(f"{prefix}_shine", ell(rx * 0.26, ry * 0.2), "$spore.light2", at=(x - rx * 0.36, y - ry * 0.34)),
            # Speckles on the cap, where the light hits.
            *[P(f"{prefix}_fleck{i}", circ(0.55), "$silent@0.75", at=(x + dx * rx, y + dy * ry)) for i, (dx, dy) in enumerate([(0.3, -0.35), (0.55, 0.05), (-0.1, 0.25), (0.05, -0.5)])],
        ]

    parts = [
        # The hive's light on the ground under the cluster.
        *halo("glow", 0, 11, 15, 4.5, 0.24, "$spore", 5),
        ao("ao", 0, 11.6, 18, 1.6, 0.3),
        *shroom("s3", 0, 6, 4.5, 2.93, 6, 0.4),
        *shroom("s1", -8, 1, 7, 4.55, 6, -0.6),
        *shroom("s2", 7, -1, 5.5, 3.58, 6, 0.5),
        # A sprout coming up beside them, and a cap that fell.
        P("sprout", R(1.6, 3.2, 0.7), "$steel.light", at=(12.5, 10.4), stroke=INK_HAIR),
        P("sprout_cap", ell(2, 1.3), "$spore.dark", at=(12.5, 8.8), stroke=INK_HAIR),
        P("fallen", ell(2.4, 1.2), "$spore.dark2", at=(-13, 11), rot=20, stroke=INK_HAIR),
    ]
    doc(
        "ss.terrain.fungi",
        "Glow fungi",
        "Three caps of the hive's fungus on the Plains (data/terrain.ts `fungi`), the same caps the camp's hearth burns "
        "(`ss.base.hearth`). Each cap is the world's teal lit on its upper left, dark along the underside, with a gloss and a few "
        "pale speckles where the light hits; the stem is pale with shade down its right and a frill where it meets the cap. Their "
        "light lies on the ground under them in rings — the hive's light, borrowed by nothing here. A sprout comes up beside them "
        "and a cap has fallen. feelers pulses its alpha. Caps where the old document had them. Generated by scripts/terrain.py.",
        (34, 28), parts,
    )


# ================================================================== the ruins' cut stone
def pillar():
    """A broken column: drums, flutes, the snapped top, the lit left edge."""
    shaft = [(-9, -15), (9, -15), (10, 21), (-10, 21)]
    top = [(-9, -15), (-5, -19), (-1, -16), (3, -21), (6, -17), (9, -15)]
    parts = [
        shadow("shadow", 0, 21, 12, 3.5),
        *shaded("shaft", shaft, "$smoke.light", [(-20, 30, "$smoke.light")], stroke=None),
        # Lit left third, shade right third: a round shaft in three bands across.
        cut("shaft_lit", shaft, -10, -3.5, "$smoke.light2", axis=0),
        cut("shaft_shade", shaft, 4, 10, "$smoke.dark", axis=0),
        cut("shaft_dark", shaft, 7.5, 10, "$smoke.dark2@0.8", axis=0),
        # Flutes: hair lines down the shaft, darker as they turn away.
        *[band(f"flute{i}", [(x, -14), (x + 0.6, 20)], 0.7, f"$ink@{a}") for i, (x, a) in enumerate([(-6, 0.18), (-2, 0.22), (2, 0.3), (6, 0.4)])],
        # Drum joints: two seams, each a dark line with the lit lip of the drum above it.
        *[p for i, y in enumerate([-3, 9]) for p in [band(f"joint{i}", [(-9.6, y), (9.6, y + 0.4)], 1.0, "$ink@0.7"),
                                                     band(f"joint{i}_lip", [(-9.4, y - 1.2), (9.4, y - 0.8)], 0.7, "$white@0.22")]],
        # The snapped top: a jagged break, its fresh faces paler.
        P("break", poly(top + [(9, -15), (-9, -15)]), "$smoke.light2", stroke=INK_HAIR),
        P("break_shade", poly([(3, -21), (6, -17), (9, -15), (3, -15)]), "$smoke.dark@0.6"),
        # A base block, chipped, and the rubble of what fell.
        P("plinth", R(24, 5, 1), "$smoke.light", at=(0, 20.5), stroke=INK_THIN),
        cut("plinth_shade", [(-12, 18), (12, 18), (12, 23), (-12, 23)], 20.8, 23, "$smoke.dark"),
        lit_edge("plinth_lit", -11, 10, 18.4, 0.8, "$white@0.3"),
        ao("foot_ao", 0, 18.2, 19, 1.4, 0.35),
        *crack("crack", [(-7, 2), (-4, 5), (-5, 8)], 0.8, "$ink@0.5", "$white@0.18"),
        P("chip", poly([(12, 23.4), (14, 20.8), (15, 23.4)]), "$smoke", stroke=INK_HAIR),
        P("chip_b", poly([(-15, 23), (-13.6, 21.2), (-12, 23)]), "$smoke.dark", stroke=INK_HAIR),
        P("lichen", poly([(-9.5, 12), (-6, 11), (-4, 14), (-6, 17), (-9.5, 16)]), "$verdigris@0.5"),
        P("rim", poly([(-9, -15)] + top[1:] + [(10, 21), (-10, 21)]), None, stroke=RIM),
    ]
    doc(
        "ss.terrain.pillar",
        "Broken pillar",
        "A broken column of cut stone in the ruins (data/terrain.ts `pillar`): a round shaft in three bands across, lit down its "
        "left third and dark down its right, fluted with hair lines that darken as they turn away; two drum joints, each a dark seam "
        "under the lit lip of the drum above; the top snapped jagged with its fresh faces paler; a chipped plinth with a lit top edge "
        "and the dark of the ground under it, a crack, lichen on the shade side, and chips of what fell. Masonry is the $smoke ramp: "
        "cut, not grown. Footprint where the old document had it. Closed in a `hair` line drawn over its fills, which shows as heavy as a body's `thin` (docs/ss-art-rules.md §3). Generated by scripts/terrain.py.",
        (30, 46), parts,
    )


def arch():
    """A gateway with its keystone gone: two jambs in courses, the broken springers, rubble at the foot."""
    def jamb(prefix, x, mirror):
        s = -1 if mirror else 1
        body = [(x - 7, -8), (x + 7, -8), (x + 8, 23), (x - 8, 23)]
        parts = [
            P(f"{prefix}_body", poly(body), "$smoke.light", stroke=INK_THIN),
            cut(f"{prefix}_lit", body, x - 8, x - 3, "$smoke.light2", axis=0),
            cut(f"{prefix}_shade", body, x + 3, x + 8, "$smoke.dark", axis=0),
            # Courses: the blocks it was laid in, seams staggered.
            *[band(f"{prefix}_course{i}", [(x - 7.6, y), (x + 7.6, y)], 0.8, "$ink@0.55") for i, y in enumerate([0, 8, 16])],
            *[band(f"{prefix}_jointv{i}", [(x + dx, y0), (x + dx, y0 + 8)], 0.7, "$ink@0.4") for i, (dx, y0) in enumerate([(2, -8), (-3, 0), (3, 8), (-2, 16)])],
            *[band(f"{prefix}_lip{i}", [(x - 7, y - 1.1), (x + 7, y - 1.1)], 0.6, "$white@0.2") for i, y in enumerate([0, 8, 16])],
            # The springer: the first stones of the arch, broken off where it used to close.
            P(f"{prefix}_springer", poly([(x - 7 * s, -8), (x + 7 * s, -8), (x + 9 * s, -14), (x + 2 * s, -19), (x - 5 * s, -17), (x - 8 * s, -12)]), "$smoke.light2", stroke=INK_THIN),
            P(f"{prefix}_springer_break", poly([(x + 9 * s, -14), (x + 2 * s, -19), (x + 5 * s, -15)]), "$smoke.dark@0.6"),
            ao(f"{prefix}_ao", x, 22.4, 15, 1.4, 0.35),
        ]
        return [p for p in parts if p]

    parts = [
        shadow("shadow", 0, 22, 26, 5),
        *jamb("l", -17, False),
        *jamb("r", 17, True),
        # What fell between them: the keystone's pieces, and rubble.
        P("keystone", poly([(-5, 24), (-2, 17), (5, 18), (7, 24)]), "$smoke.light", stroke=INK_HAIR),
        P("keystone_top", poly([(-2, 17), (5, 18), (4, 20), (-3, 19.5)]), "$smoke.light2"),
        *pebble("rub_a", 10, 24.5, 2.4, 1.5, "$smoke.light", 10),
        *pebble("rub_b", -11, 25, 1.8, 1.2, "$smoke", -20),
        *crack("crack", [(-19, 4), (-16, 7), (-17, 11)], 0.8, "$ink@0.5", "$white@0.18"),
        P("lichen", poly([(14, 10), (18, 9), (20, 13), (17, 16), (13, 14)]), "$verdigris@0.45"),
    ]
    doc(
        "ss.terrain.arch",
        "Broken arch",
        "A standing gateway in the ruins with its keystone gone (data/terrain.ts `arch`): two jambs laid in courses with the seams "
        "staggered, each lit down its outer third and dark down the inner, the first stones of the arch still on them, broken off "
        "where it used to close, their fresh faces in shade. The keystone lies between them in pieces with rubble round it; a crack "
        "and lichen on the stone. Masonry is the $smoke ramp: cut, not grown. Footprint where the old document had it. "
        "Generated by scripts/terrain.py.",
        (52, 50), parts,
    )


def slab():
    """A toppled block lying on the ground: a lit top face, a dark front edge, seams, a chipped corner."""
    top = [(-22, -11), (20, -13), (23, 4), (-20, 6)]
    front = [(-20, 6), (23, 4), (23, 10), (-20, 12)]
    parts = [
        shadow("shadow", 0, 10, 23, 4),
        P("front", poly(front), "$smoke.dark", stroke=INK_THIN),
        P("front_dark", poly([(0, 5), (23, 4), (23, 10), (0, 11)]), "$smoke.dark2@0.7"),
        P("top", poly(top), "$smoke.light", stroke=INK_THIN),
        cut("top_lit", top, -22, -6, "$smoke.light2", axis=0),
        lit_edge("edge_lit", -21, 19, -11.6, 0.9, "$white@0.35"),
        # Seams: two block joints across, each a dark line under a lit lip.
        *[p for i, x in enumerate([-8, 9]) for p in [band(f"seam{i}", [(x, -12), (x + 1, 5)], 0.9, "$ink@0.6"),
                                                     band(f"seam{i}_lip", [(x - 1.1, -12), (x - 0.1, 5)], 0.6, "$white@0.18")]],
        # A chipped corner: the break pale, the chip fallen beside.
        P("chip_break", poly([(20, -13), (23, 4), (18, -4)]), "$smoke.light2"),
        P("chip_break_shade", poly([(23, 4), (18, -4), (20, 1)]), "$smoke.dark@0.6"),
        P("chip", poly([(24, 12), (26, 9), (28, 12.5)]), "$smoke.light", stroke=INK_HAIR),
        *crack("crack", [(-14, -4), (-10, -1), (-11, 4)], 0.8, "$ink@0.5", "$white@0.18"),
        P("lichen", poly([(2, -8), (6, -9), (8, -5), (4, -2), (0, -4)]), "$verdigris@0.45"),
        ao("ao", 0, 11.6, 42, 1.6, 0.35),
    ]
    doc(
        "ss.terrain.slab",
        "Toppled slab",
        "A toppled wall block in the ruins, lying on the ground (data/terrain.ts `slab`): the top face lit, paler still on its "
        "left, with a lit edge along the top; the front edge dark and darker to the right; two block seams cut through it, each a "
        "dark line under a lit lip; a corner chipped off with the break pale and the chip fallen beside, a crack, lichen, and the "
        "dark of the ground along its foot. Masonry is the $smoke ramp. Footprint where the old document had it. "
        "Generated by scripts/terrain.py.",
        (48, 30), parts,
    )


def rubble():
    """Five chips of cut stone lying as they fell, each with a top and a shadow."""
    parts = [
        ao("dust", 0, 7.5, 22, 2.2, 0.22),
        *pebble("chip_a", -7, 1, 4.4, 3.2, "$smoke.light", -14),
        P("chip_a_top", poly([(-10, -0.6), (-6, -2.6), (-3.4, -0.2), (-7.4, 1.4)]), "$smoke.light2"),
        *pebble("chip_b", 5, 2, 3.6, 2.6, "$smoke.light", 18),
        P("chip_b_top", poly([(2.4, 0.4), (6, -1), (8, 1.2), (4.6, 2.4)]), "$smoke.light2"),
        P("chip_a_shade", poly([(-3.4, -0.2), (-2.8, 2.6), (-6, 4), (-7.4, 1.4)]), "$smoke.dark@0.55"),
        P("chip_b_shade", poly([(8, 1.2), (8.4, 3.6), (5.6, 4.6), (4.6, 2.4)]), "$smoke.dark@0.55"),
        *pebble("chip_c", 0, 6.5, 2.4, 1.6, "$smoke", 0),
        *pebble("chip_d", -11, 6, 1.6, 1.1, "$smoke", 30),
        *pebble("chip_e", 10, -3, 1.9, 1.3, "$smoke.light", -25),
        # One with the cut face still on it: a seam and a flake of lichen.
        band("chip_a_seam", [(-8.6, -1.2), (-5.2, 0.6)], 0.6, "$ink@0.45"),
        P("lichen", poly([(4.4, 0), (6.6, -0.6), (7.2, 1.2), (5.4, 1.8)]), "$verdigris@0.45"),
    ]
    doc(
        "ss.terrain.rubble",
        "Rubble",
        "Five chips of the same cut masonry as the pillar and the slab, lying as they fell (data/terrain.ts `rubble`, the map's "
        "lone stones): each has a lit top face, a catch of light on its upper left and a shadow under it; one keeps a seam of the "
        "block it came off and a flake of lichen; dust lies under the pile. Generated by scripts/terrain.py.",
        (26, 20), parts,
    )


def ruins():
    """A sunken stone ring humming with old scent: the bowl, the core, three standing stones."""
    def stone(prefix, x, y, w, h, lean=0.0):
        body = [(x - w / 2 + lean, y - h / 2), (x + w / 2 + lean, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)]
        return [p for p in [
            P(f"{prefix}", poly(body), "$carapace", stroke=INK_THIN),
            cut(f"{prefix}_lit", body, x - w / 2 - 1, x - w / 6, "$carapace.light", axis=0),
            cut(f"{prefix}_shade", body, x + w / 6, x + w / 2 + 1, "$carapace.dark", axis=0),
            band(f"{prefix}_seam", [(x - w / 2 + 0.4, y - 1), (x + w / 2 - 0.4, y + 0.6)], 0.7, "$ink@0.5"),
            # The top face, seen from above and a little to the front: pale, with a dark front edge.
            P(f"{prefix}_cap", poly([(x - w / 2 + lean, y - h / 2), (x + w / 2 + lean, y - h / 2), (x + w / 2 + lean - 0.6, y - h / 2 + 2.2), (x - w / 2 + lean + 0.6, y - h / 2 + 2.2)]), "$carapace.light2"),
            band(f"{prefix}_cap_edge", [(x - w / 2 + lean + 0.6, y - h / 2 + 2.4), (x + w / 2 + lean - 0.6, y - h / 2 + 2.4)], 0.7, "$ink@0.5"),
            # A chip out of one corner, and a crack from it.
            P(f"{prefix}_chip", poly([(x + w / 2 + lean, y - h / 2), (x + w / 2 + lean - 2.6, y - h / 2), (x + w / 2 + lean - 0.4, y - h / 2 + 3.2)]), "$carapace.dark2"),
            band(f"{prefix}_crack", [(x + w / 2 + lean - 1.2, y - h / 2 + 3), (x + w / 4, y - 2)], 0.6, "$ink@0.45"),
            # The hive's signal has got into one seam of its own stone, faintly.
            band(f"{prefix}_vein", [(x - 1, y + 2), (x + 1, y + h / 2 - 1.5)], 0.5, "$pheromone@0.3"),
            ao(f"{prefix}_ao", x, y + h / 2 - 0.6, w + 2, 1.4, 0.35),
        ] if p]

    parts = [
        shadow("shadow", 0, 14, 31, 10, "0.55"),
        # The ring: a raised lip of grown carapace, lit on the far side where the light crosses it.
        P("ring", ell(28, 12), "$carapace.dark", at=(0, 12), stroke=INK_THIN),
        P("ring_lit", ell(27, 11), None, at=(0, 12), stroke={"color": "$carapace.light", "width": 1.2}),
        P("ring_in", ell(22, 8.4), "$carapace.dark2", at=(0, 12)),
        # Cracks across the lip where it has split.
        *[band(f"split{i}", [(x0, y0), (x1, y1)], 0.7, "$ink@0.5") for i, (x0, y0, x1, y1) in enumerate([(-24, 8, -20, 11), (18, 16, 22, 19), (6, 2, 8, 5)])],
        # The bowl, dark, and the core glowing in it with its light in rings up the bowl.
        P("bowl", ell(15, 5.5), "$coal", at=(0, 12)),
        P("bowl_dark", ell(13, 4.4), "$ink@0.6", at=(0, 12.4)),
        *halo("core_glow", 0, 12, 13, 4.6, 0.5, "$pheromone", 5),
        P("core", ell(7, 2.5), "$pheromone@0.85", at=(0, 12)),
        P("core_hot", ell(3.4, 1.1), "$pheromone.light2@0.9", at=(-0.6, 11.7)),
        # Three standing stones round the rim, leaning, seamed, lit on the left.
        *stone("stone_l", -22.5, 0, 7, 20, -1.2),
        *stone("stone_r", 22, -3, 8, 22, 1.0),
        *stone("stone_t", -0.5, -12, 7, 16, 0.6),
        # What fell off them.
        P("chip_a", poly([(-28, 11), (-26, 8.4), (-24, 11.4)]), "$carapace", stroke=INK_HAIR),
        P("chip_b", poly([(26, 10.4), (28.2, 8), (30, 11)]), "$carapace.dark", stroke=INK_HAIR),
        P("lichen", poly([(20, -8), (24, -9), (25.6, -5), (23, -2.6), (19.4, -4)]), "$verdigris@0.45"),
    ]
    doc(
        "ss.terrain.ruins",
        "Scent ruins",
        "A sunken stone ring in the Plains that still hums with old scent (data/terrain.ts `ruins`): a raised lip of the hive's "
        "own grown carapace, lit along its far edge and split in three places, a dark bowl inside it and the signal glowing at the "
        "bottom with its light in rings up the bowl — the hive's light, lit from inside. Three standing stones lean round the rim, "
        "each lit down its left, seamed, with a lit top edge, the signal in a vein of its seam and the dark of the ground at its foot; "
        "chips of them lie where they fell, and lichen has got onto the tallest. Footprint and stones where the old document had them. "
        "Generated by scripts/terrain.py.",
        (68, 52), parts,
    )


# ================================================================== grown and shed
def chitin():
    """A broken slab of hive carapace, ridged amber, leaning out of the ground."""
    plate = [(-22, -13), (16, -15), (23, 6), (-8, 15), (-20, 8)]
    parts = [
        shadow("shadow", 0, 12, 20, 4.5),
        *shaded("plate", plate, "$chitin.dark", [(-15, -4, "$chitin"), (6, 15, "$chitin.dark2")], stroke=RIM),
        # Ridges running the long way, each a dark groove with a lit crest above it.
        *[p for i, (x0, y0, x1, y1) in enumerate([(-18, -5, 18, -8), (-16, 1, 20, -2), (-13, 7, 21, 4)]) for p in [
            band(f"ridge{i}", [(x0, y0), (x1, y1)], 1.0, "$chitin.dark2@0.9"),
            band(f"ridge{i}_crest", [(x0 + 0.4, y0 - 1.3), (x1 - 0.4, y1 - 1.3)], 0.7, "$chitin.light@0.7"),
        ]],
        # The light on its upper-left corner, and through it: a paler patch where the plate is thin.
        lit_edge("edge_lit", -20, 12, -13.2, 0.9, "$white@0.35"),
        P("thin", poly([(-6, -10), (4, -11), (6, -5), (-3, -3)]), "$chitin.light@0.35"),
        # The broken edge: jagged, pale where it snapped, with a crumb beside.
        P("break", poly([(16, -15), (23, 6), (21, 2), (20, -6), (17.5, -10)]), "$chitin.light@0.6"),
        P("crumb", poly([(24, 10), (26, 7.6), (28, 10.6)]), "$chitin.dark", stroke=INK_HAIR),
        *crack("crack", [(-14, 4), (-10, 8), (-11, 12)], 0.8, "$ink@0.5", "$chitin.light@0.3"),
        # Where it comes out of the dirt.
        ao("ao", -5, 13.4, 28, 2.0, 0.4),
    ]
    doc(
        "ss.terrain.chitin",
        "Chitin slab",
        "A broken slab of hive carapace leaning out of the ground (data/terrain.ts `chitin`, the Mason Gland's masonry): ridged "
        "amber in three values, lit on its upper left with a lit edge there and a paler patch where the plate is thin enough for "
        "light to come through; three ridges run the long way, each a dark groove under a lit crest; the broken edge is jagged and "
        "pale where it snapped, a crumb of it beside, a crack near the foot, and the dark of the dirt it comes out of. The hive's "
        "material with no signal in it. Footprint where the old document had it. Closed in a `hair` line drawn over its fills, which shows as heavy as a body's `thin` (docs/ss-art-rules.md §3). Generated by scripts/terrain.py.",
        (48, 31), parts,
    )


def husk():
    """The bleached dome of something that ran out of scent: a half-shell of ribs, holed, lit on the left."""
    def arcp(cx, cy, rx, ry, a0, a1, n=14):
        return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]

    dome = arcp(0, 9, 21, 19, 180, 360) + [(21, 9), (-21, 9)]
    parts = [
        shadow("shadow", 0, 11, 21, 4, "0.45"),
        P("dome", poly(dome), "$husk", stroke=INK_THIN),
        # Lit on the left, in shade on the right, dark along the ground.
        P("dome_lit", poly(arcp(0, 9, 19, 17, 190, 262) + [(0, 9), (-19, 9)]), "$silent@0.6"),
        P("dome_shade", poly(arcp(0, 9, 19, 17, 290, 360) + [(19, 9), (0, 9)]), "$husk.dark"),
        P("dome_dark", poly(arcp(0, 9, 19, 17, 330, 360) + [(19, 9), (12, 9)]), "$husk.dark2@0.7"),
        # Ribs: the shell's segments, each a dark seam under a lit crest.
        *[p for i, r in enumerate([15, 9.5, 4.5]) for p in [
            P(f"rib{i}", {"kind": "ring", "r": r2(r), "width": 1.1, "from": 190, "to": 350}, "$bone.dark", at=(0, 9)),
            P(f"rib{i}_crest", {"kind": "ring", "r": r2(r + 1.1), "width": 0.6, "from": 196, "to": 300}, "$white@0.3", at=(0, 9)),
        ]],
        # A hole punched in the shell, dark inside, and the crack running from it.
        P("hole_lip", poly([(3.6, -6.2), (6, -9.6), (10.8, -9.2), (13.6, -5), (12.2, -0.4), (8, 1.6), (4.4, -0.6)]), "$husk.dark2"),
        P("hole", poly([(5, -6), (7, -8.4), (10.4, -8), (12.4, -4.2), (11.2, -1), (8, 0.2), (5.2, -1.8)]), "$ink@0.85"),
        P("hole_far", poly([(9.6, -1.2), (11.6, -2.6), (12.4, -4.2), (11, -1.2)]), "$husk.dark@0.6"),
        P("hole_chip", poly([(14.2, -6.4), (16, -8.2), (16.8, -5.6)]), "$husk.dark", stroke=INK_HAIR),
        *crack("crack", [(12, -3), (15, 1), (14, 6)], 0.8, "$ink@0.5", "$white@0.25"),
        # The broken edge where the rest of it went, and shards of it on the ground.
        P("break", poly([(-21, 9), (-18, 4), (-15, 7), (-12, 3), (-9, 9)]), "$husk.dark2", stroke=INK_HAIR),
        P("shard_a", poly([(-26, 12), (-23, 9.4), (-20.6, 12.4)]), "$husk.dark", stroke=INK_HAIR),
        P("shard_b", poly([(22, 12.4), (24, 10), (26.4, 12.8)]), "$husk", stroke=INK_HAIR),
        ao("ao", 0, 10.4, 38, 1.8, 0.35),
        # A tide of dust blown against its shade side.
        P("drift", ell(7, 1.6), "$soil@0.35", at=(14, 10.6)),
    ]
    doc(
        "ss.terrain.husk",
        "Bleached husk",
        "The bleached dome of something that ran out of scent, half-sunk in a burrow chamber (data/terrain.ts `husk`): a half-shell "
        "of nested ribs, lit on its left and in shade on its right with the dark of the ground along its foot, each rib a dark seam "
        "under a lit crest; a hole punched in the shell with the dark inside and a crack running from it; the edge broken where the "
        "rest of it went, shards of it on the ground, and dust blown against its shade side. Bone with the signal gone out of it. "
        "Footprint where the old document had it. Generated by scripts/terrain.py.",
        (46, 30), parts,
    )


# ================================================================== the pan's crust
def fissure():
    """A crack in the salt crust: the dark cut, a crust lip lit along its top and shaded along its bottom, a fork, salt grains."""
    top = [(-30, -2), (-18, -5), (-6, -1), (4, -6), (14, -2), (26, -4), (31, 0)]
    bot = [(24, 3), (12, 2), (4, 6), (-6, 3), (-18, 5), (-29, 2)]
    cut = top + bot
    parts = [
        # The crust round it has lifted: a pale rim a step wider than the cut, in shade on the far (lower) side.
        P("rim", poly([(x * 1.04, y * 1.5 - 0.4) for x, y in cut]), "$husk.dark@0.5"),
        P("rim_shade", poly([(x, y) for x, y in bot] + [(x, y + 2.2) for x, y in bot[::-1]]), "$sand.dark@0.55"),
        P("dark", poly(cut), "$ink@heavy"),
        # The lit lip along the top edge, where the salt dried on it.
        P("edge_top", poly([(x, y - 1) for x, y in top] + [(x, y + 0.8) for x, y in top[::-1]]), "$husk.dark@soft"),
        band("edge_crust", [(x, y - 1.3) for x, y in top], 0.7, "$silent@0.4"),
        P("throat", poly([(-16, -2), (-6, 0), (4, -3), (12, 0), (20, -2), (13, 1), (4, 3), (-6, 1.5)]), "$ink"),
        # A fork off it, and a hairline crack running on past the end.
        P("fork", poly([(-6, -1), (-2, -6), (2, -7.4), (-1, -4), (-4, 0.5)]), "$ink@0.7"),
        band("hair_a", [(31, 0), (34, -1.4), (36, -1)], 0.6, "$ink@0.5"),
        band("hair_b", [(-29, 2), (-33, 3.4), (-35, 3)], 0.6, "$ink@0.5"),
        # Salt grains along the lip, and a few flakes of crust that fell into the cut.
        {"id": "salt", "repeat": {"of": {"kind": "rect", "w": 1.6, "h": 1.6}, "count": 6, "area": [56, 6], "seed": 13}, "fill": "$husk.dark@heavy"},
        {"id": "salt_lit", "repeat": {"of": {"kind": "rect", "w": 1.1, "h": 1.1}, "count": 5, "area": [50, 4], "seed": 14}, "fill": "$silent@0.6"},
        P("flake_a", poly([(-10, 1), (-8.4, -0.6), (-7, 1.4)]), "$husk.dark@0.7"),
        P("flake_b", poly([(16, 0.4), (18, -1), (19, 1)]), "$husk.dark@0.6"),
    ]
    doc(
        "ss.terrain.fissure",
        "Salt fissure",
        "A crack in the Salt Pan's crust (data/terrain.ts `fissure`, decor): the crust round it has lifted into a pale rim, lit along "
        "the top lip where the salt dried on it and in shade along the far side, an ink throat down the middle, a fork off it and "
        "hairline cracks running on past both ends, flakes of crust fallen into the cut and salt grains along the lip. Drawn under "
        "the actors and never collided with. The ground is dry, and this says so. Footprint where the old document had it. "
        "Generated by scripts/terrain.py.",
        (64, 16), parts,
    )


def glass():
    """Sand fused to glass where something hot went off: the scorch, a sand rim, the pool in facets, glints, shards."""
    pool = [(-15, 1), (-10, -6), (-1, -8), (9, -6), (15, 0), (11, 6), (2, 8), (-8, 6)]
    parts = [
        P("scorch", ell(17, 9), "$ink@soft", at=(0, 1)),
        P("soot", ell(13, 6.5), "$ink@0.3", at=(1, 1.5)),
        # The sand round the pool fused and pushed up into a rim, lit on its top left.
        P("rim", poly([(x * 1.12, y * 1.14 + 0.3) for x, y in pool]), "$sand.dark", stroke=INK_HAIR),
        P("rim_lit", poly(clip([(x * 1.12, y * 1.14 + 0.3) for x, y in pool], 1, -20, -2)), "$sand.light@0.5"),
        P("pool", poly(pool), "$aqua.dark@heavy", stroke=INK_HAIR),
        # Facets: the pool cooled in plates, each a slightly different depth of the same cold colour.
        P("facet_a", poly([(-15, 1), (-10, -6), (-3, -3), (-6, 4)]), "$aqua.dark2@0.5"),
        P("facet_b", poly([(9, -6), (15, 0), (8, 3), (4, -4)]), "$aqua.dark2@0.6"),
        P("facet_c", poly([(2, 8), (-8, 6), (-4, 2), (5, 3)]), "$aqua.dark@0.5"),
        P("sheen", poly([(-9, 0), (-5, -4), (3, -5), (8, -2), (4, 2), (-3, 3)]), "$aqua@soft"),
        P("sheen_hot", poly([(-6, -1), (-3, -3.4), (2, -3.6), (3, -2), (-1, 0.4)]), "$aqua.light@0.5"),
        # Bubbles caught in it as it cooled.
        *[P(f"bubble{i}", circ(r), "$aqua.light@0.5", at=(x, y)) for i, (x, y, r) in enumerate([(-7, 3, 0.7), (7, -3, 0.6), (1, 5, 0.5)])],
        P("glint", circ(1.6), "$silent", at=(-3, -3)),
        P("glint2", circ(1.0), "$silent@heavy", at=(6, 1)),
        {"id": "shards", "repeat": {"of": {"kind": "poly", "points": [[-1.4, 0.8], [0, -1.6], [1.4, 0.8]]}, "count": 5, "area": [30, 14], "seed": 29, "jitterRot": True}, "fill": "$aqua.light@heavy"},
        # The dark where the rim meets the sand.
        ao("ao", 0, 9.4, 26, 1.4, 0.3),
    ]
    doc(
        "ss.terrain.glass",
        "Fused glass",
        "Sand fused to glass on the Salt Pan where something hot went off (data/terrain.ts `glass`, decor): the scorch and its soot, "
        "the sand round it pushed up into a rim lit on its top left, and the pool itself cooled in plates — facets of the same cold "
        "aqua at different depths under a sheen, bubbles caught in it, two glints and a scatter of shards. feelers pulses it the way "
        "it pulses the vents, so the glint reads as the light catching. The pan's one cold colour, and the one the Forerunner's bolt "
        "is cut from. Footprint where the old document had it. Generated by scripts/terrain.py.",
        (36, 24), parts,
    )


if __name__ == "__main__":
    spire(); boulder(); vent(); fungi()
    pillar(); arch(); slab(); rubble(); ruins()
    chitin(); husk()
    fissure(); glass()
