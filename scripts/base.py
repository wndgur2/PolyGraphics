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
  the marker     the middle of the camp: the lander's plate (T041), the
                 game's own line, stood up on the snapped mast with a strip
                 of cloth tied on for each of the eight expeditions
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
from draw import *  # noqa: E402,F401,F403
from bits_metal import chain, clamp, hasp, hinge, hook, padlock, sag, wire_coil  # noqa: E402
from bits_cloth import bed, bedroll, flap, pillow, rope_coil, sack, streamer, streamer_tracks  # noqa: E402
from bits_camp import dial, ladle, mug, page, page_stack, saw, stone, stool, tag, tin_stack  # noqa: E402
from bits_keeps import KEEP_PARTS  # noqa: E402
from bits_glass import cartridge, jar, jar_bail_top, jar_fill, syringe, tube_rack, vial  # noqa: E402,F401

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "apps", "ss", "assets")


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


# ============================================================== the lander
def lander():
    hull = [
        (-128, -46), (100, -46),
        (122, -42), (140, -32), (152, -16), (156, 0), (152, 16), (140, 30), (122, 40), (100, 44),
        (-128, 44), (-134, 32), (-137, 0), (-134, -32),
    ]
    bell = [(-120, -12), (-148, -22), (-160, -18), (-160, 18), (-148, 24), (-120, 12)]
    drift_top = [(-170, 56), (-158, 47), (-140, 41), (-118, 44), (-92, 41), (-64, 45), (-34, 43), (-4, 46), (28, 42), (62, 44), (98, 41), (128, 45), (156, 44), (170, 54)]
    drift_foot = [(170, 58), (140, 61), (100, 59), (60, 62), (20, 60), (-20, 62), (-60, 59), (-100, 61), (-140, 58), (-170, 59)]
    ramp = [(-62, 38), (-22, 38), (-16, 58), (-68, 58)]
    in_hatch = lambda x, y: -72 < x < -12
    parts = [
        shadow("shadow", 0, 52, 168, 20, "0.42"),
        # The engines, dead, behind the hull: two bells flaring west, soot at
        # the mouths, a reinforcing band round each.
        *shaded("bell_top", moved(bell, (0, -22)), "$smoke.dark", [(-161, -142, "$coal")], axis=0),
        P("bell_top_band", R(3, 30, 1), "$steel.dark", at=(-136, -22)),
        P("bell_top_mouth", ell(4.5, 18), "$coal.dark", at=(-157, -22), stroke=INK_HAIR),
        P("bell_top_lit", R(2, 26, 1), "$steel@0.45", at=(-150, -22)),
        *shaded("bell_low", moved(bell, (0, 14)), "$smoke.dark", [(-161, -142, "$coal")], axis=0),
        P("bell_low_band", R(3, 30, 1), "$steel.dark", at=(-136, 14)),
        P("bell_low_mouth", ell(4.5, 18), "$coal.dark", at=(-157, 14), stroke=INK_HAIR),
        # The hull: a drum on its side, lit from above, its belly in shadow.
        *shaded("hull", hull, "$smoke", [(-47, -29, "$steel"), (-29, -22, "$steel.dark"), (18, 45, "$smoke.dark")], stroke=None),
        P("crown_lit", R(196, 5, 2.5), "$steel.light", at=(-22, -40)),
        P("specular", R(120, 2, 1), "$white@0.4", at=(-34, -42)),
        # Two panels replaced at some point, a different metal, riveted on.
        P("patch_a", R(20, 16, 1), "$steel.dark", at=(-102, 22), stroke=INK_HAIR),
        *rivet_row("patch_a_rv", -110, 16, -94, 16, 4, 0.7),
        P("patch_b", R(24, 12, 1), "$smoke.light", at=(54, 26), stroke=INK_HAIR),
        *rivet_row("patch_b_rv", 44, 22, 64, 22, 4, 0.7),
        # A dent the ground gave it, coming down.
        P("dent", ell(9, 5), "$smoke.dark", at=(20, 27)),
        P("dent_lit", ell(7, 1.6), "$steel@0.7", at=(18, 31)),
        *shaded("collar", rr(12, 92, 3, (-121, -1)), "$slate", [(-48, -30, "$slate.light"), (18, 46, "$slate.dark")], stroke=INK_HAIR),
        *[p for i, y in enumerate([-36, -18, 0, 18, 36]) for p in bolt(f"collar_bolt_{i}", -121, y, 1.3, "$slate.dark")],
        # Panel seams with their rivets, and the rust the ground has drawn
        # down each one.
        *[P(f"seam_{i}", R(1.6, 86, 0.6), "$ink@0.35", at=(x, -1)) for i, x in enumerate([-96, -6, 62])],
        *[p for i, x in enumerate([-96, -6, 62]) for p in rivet_row(f"seam_{i}_rv", x + 2.6, -38, x + 2.6, 36, 9, 0.7)],
        P("seam_low", R(236, 1.4, 0.6), "$ink@0.25", at=(-12, 10)),
        *rivet_row("seam_low_rv", -116, 13, 96, 13, 22, 0.7, skip=in_hatch),
        *rust("rust_a", -96, -6, 5, 40),
        *rust("rust_b", 62, -2, 4.6, 34),
        # Soot up the belly from the engines, and a smudge round the collar.
        P("scorch", poly([(-128, 4), (-80, 16), (-36, 30), (4, 44), (-128, 44)]), "$coal@0.35"),
        P("scorch_deep", poly([(-128, 16), (-96, 24), (-66, 36), (-50, 44), (-128, 44)]), "$coal@0.35"),
        P("soot", ell(16, 10), "$coal@0.3", at=(-112, -8)),
        # The settlers' stripe round the nose: cold, like everything people brought.
        P("stripe", R(9, 84, 1), "$frost.dark@0.7", at=(106, -1)),
        P("stripe_lit", R(9, 12, 1), "$frost@0.5", at=(106, -38)),
        # The port, dead: no light behind it. Bolted round.
        P("port_rim", circ(11), "$slate", at=(130, -8), stroke=INK_THIN),
        *[P(f"port_bolt_{i}", circ(0.9), "$slate.dark", at=(130 + 8.6 * math.cos(a), -8 + 8.6 * math.sin(a))) for i, a in enumerate([k * math.pi / 3 + 0.5 for k in range(6)])],
        P("port", circ(7), "$coal", at=(130, -8)),
        P("port_glint", ell(3, 1.6), "$frost@0.45", at=(127, -11), rot=-30),
        # The hatch, open, on two hinges. A jar of caps sits on the floor
        # inside: that is where the teal in the hull's dark comes from.
        *shaded("hatch_frame", rr(54, 66, 12, (-42, 6)), "$slate", [(-28, -16, "$slate.light"), (26, 40, "$slate.dark")]),
        P("hatch_dark", R(44, 56, 9), "$coal", at=(-42, 8)),
        *halo("hatch_glow", -40, 27, 20, 11, 0.6),
        *jar("hatch_jar", -34, 29, 7, 8, inner="$spore@0.12", contents=cap("hatch_jar_cap", 0, 1.0, 2.4)),
        P("hatch_cable", poly([(-58, -20), (-56, -20), (-54, 0), (-50, 12), (-52, 12), (-56, 0)]), "$ink@0.7"),
        P("hatch_sill", R(46, 6, 2), "$smoke.dark", at=(-42, 35), stroke=INK_HAIR),
        lit_edge("hatch_sill_lit", -63, -21, 32.6, 0.9, "$smoke.light@0.8"),
        P("door", poly([(0, -28), (14, -32), (17, 24), (0, 32)]), "$steel.dark", at=(-14, 6), stroke=INK_THIN),
        P("door_lit", poly([(2, -24), (6, -25), (7, 20), (2, 23)]), "$steel@0.85", at=(-14, 6)),
        P("door_seal", poly([(12, -27), (14, -28), (16, 22), (14, 23)]), "$ink@0.4", at=(-14, 6)),
        *bolt("door_bolt", -6, 2, 1.8, "$slate.dark"),
        *hinge("hinge_a", -15, -14, vertical=True, length=7, leaf=2.0),
        *hinge("hinge_b", -15, 24, vertical=True, length=7, leaf=2.0),
        # What the settlers scratched into the skin (X001): a count, in fives.
        *tally("tally", 4, -16, 3, 2),
        *tally("tally_b", 4, 2, 2, 3, 9),
        # Where the plate was (T041): it has been taken down and stood in the
        # middle of the camp (`ss.base.marker`). The skin it covered is paler,
        # and the four holes it hung from have bled rust.
        P("plate_scar", R(30, 18, 2), "$steel.light@0.3", at=(84, -16)),
        *[P(f"rivet_hole_{i}", circ(1.3), "$coal", at=(84 + dx, -16 + dy)) for i, (dx, dy) in enumerate([(-12, -6), (12, -6), (-12, 6), (12, 6)])],
        *rust("rust_hole_a", 72, -9, 2.2, 14, 0.6),
        *rust("rust_hole_b", 96, -9, 2.2, 10, 0.5),
        # A few scuffs where hands and packs have gone in and out.
        *scratches("scuff", -2, 24, 22, 10, 4, "$steel@0.4", 11),
        # A stub of mast on the crown, snapped, its cable hanging.
        P("mast", R(4, 20, 1.5), "$steel.dark", at=(30, -55), stroke=INK_HAIR, rot=10),
        P("mast_cap", R(9, 3, 1), "$steel", at=(32, -65), rot=10),
        band("cable", [(33, -62), (38, -54), (42, -47), (44, -40)], 1.1, "$coal"),
        # Grit settled on top, and the hive starting on it: buds at the collar (A055).
        P("grit_a", ell(26, 2.6), "$sand@0.7", at=(-66, -45)),
        P("grit_b", ell(16, 2.2), "$sand@0.6", at=(44, -46)),
        *bud("bud_a", -112, -45, 1.1, 0.5),
        *bud("bud_b", -100, -46, 0.75, -0.3),
        # Its own drift: the hull is half in the ground. Ripples across it
        # where the wind lies, a lit crest, a few stones.
        P("drift_skirt", poly(drift_top + [(p[0], p[1] + 4) for p in drift_foot]), "$sand@0.4"),
        P("drift", poly(drift_top + drift_foot), "$sand"),
        band("drift_lit", drift_top[1:-1], 2, "$sand.light@0.6"),
        band("ripple_a", [(-150, 51), (-130, 50), (-110, 52)], 0.9, "$sand.dark@0.7"),
        band("ripple_b", [(-58, 53), (-38, 52), (-18, 54)], 0.9, "$sand.dark@0.7"),
        band("ripple_c", [(72, 52), (94, 51), (114, 53)], 0.9, "$sand.dark@0.7"),
        P("stone_a", ell(3, 1.8), "$smoke.dark", at=(-128, 55), stroke=INK_HAIR),
        P("stone_b", ell(2.2, 1.4), "$smoke", at=(140, 56), stroke=INK_HAIR),
        # Things on the drift: the ramp out of the hatch, a leg that broke on
        # the way down, another folded under.
        *shaded("ramp", ramp, "$steel.dark", [(51, 59, "$slate.dark")]),
        lit_edge("ramp_lit", -61, -23, 39, 0.9, "$steel@0.9"),
        *[P(f"tread_{i}", R(40 + i * 3, 1.2, 0.4), "$ink@0.4", at=(-42, 43 + i * 5)) for i in range(3)],
        P("strut", poly([(0, 0), (6, 0), (26, 22), (40, 24), (40, 30), (22, 30), (0, 6)]), "$slate", at=(112, 32), stroke=INK_THIN),
        P("strut_lit", poly([(1, 1), (4, 1), (22, 20), (19, 21)]), "$slate.light", at=(112, 32)),
        *bolt("strut_bolt", 116, 35, 1.2, "$slate.dark"),
        P("strut_foot", R(18, 5, 2), "$slate.dark", at=(148, 62), stroke=INK_HAIR),
        P("leg_folded", R(30, 5, 2), "$slate.dark", at=(-96, 47), rot=10, stroke=INK_HAIR),
    ]
    return doc(
        "ss.base.lander",
        "The lander",
        "The settlers' hull, lying where it came down in 2650 and would not fly again (X001: \"The lander will not fly again. We live here.\"). "
        "Every expedition since camped in its lee. A drum on its side, lit from above, with two dead engine bells flaring at one end and a "
        "rounded nose at the other, half sunk in the drift it has gathered, the wind's ripples across it. Its panels are riveted along every "
        "seam; two have been replaced in another metal, and it took a dent coming down. The hatch is open on two hinges and a ramp runs down "
        "from it; a jar of caps sits on the floor inside, so the hull's dark has a little teal in the bottom of it. There is a dead port "
        "bolted round, a leg that broke on the way down, a snapped mast with its cable hanging, and a cold stripe round the nose. Rust runs "
        "down the seams, which is the ground reaching up, and soot runs up the belly from the engines. Beside the hatch is the settlers' "
        "count, scratched into the skin in fives. Near the nose is where the plate was, the one with the same word on it as the ruin's "
        "stones and Eden's iron (T041): a paler patch and four rivet holes bleeding rust, because the plate itself stands in the middle of "
        "the camp now (`ss.base.marker`). Two pink buds are pushing out at the engine collar: the hive reclaiming the camp, the way the "
        "crystal grew on Arin's frame (A055).",
        (344, 160),
        parts,
    )


# ============================================================== the frame
def frame():
    # The two pages the wind moves: each turns about one point, the pin or its middle.
    note_b = page("note_b", -36, 12, rot=6, w=10, h=13, fill="$husk", pin="pin", pivot="pin")
    roof_page = page("roof_page", -52, -32, rot=-24, w=9, h=11, pivot="centre")
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
        *page("note_a", -54, 11, rot=-5, w=11, h=14, pin="pin"),
        *note_b,
        *page("note_c", -17, 11, rot=-2, w=12, h=9, pin="tape", ear=None),
        # Where the camp sleeps: a sleeping bag laid out with a pillow, one
        # still rolled, a mug, a stack of pages to read by.
        *bed("bed", 27, 45, length=64),
        *pillow("pillow", 4.5, 40, rot=-3),
        *bedroll("roll", -52, 50.5),
        *mug("mug", 70, 49.5),
        *page_stack("stack", -74, 50, w=12, h=10, lie=0.5, s=0.9),
        # The canvas, seen from above: back bar high, front edge sagging
        # between the front poles.
        *shaded("roof", [(-84, -46), (84, -46)] + sag, "$slate.light", [(-47, -35, "$slate"), (-12, 0, "$slate.light2")]),
        band("hem", sag, 3.2, "$slate.dark"),
        P("roof_seam_a", poly([(-30, -46), (-28, -46), (-33, -5), (-35, -5)]), "$slate.dark@0.5"),
        P("roof_seam_b", poly([(28, -46), (30, -46), (35, -5), (33, -5)]), "$slate.dark@0.5"),
        P("roof_lit", poly([(-70, -32), (-38, -32), (-40, -16), (-74, -18)]), "$white@0.12"),
        P("crease_a", poly([(-76, -44), (-72, -44), (-50, -10), (-54, -9)]), "$slate@0.3"),
        P("crease_b", poly([(70, -44), (74, -44), (56, -9), (52, -10)]), "$slate@0.3"),
        *[P(f"stitch_{i}", R(3, 0.8, 0.3), "$slate.light2@0.8", at=(x, y - 3.4), rot=math.degrees(math.atan2(dy, 32))) for i, (x, y, dy) in enumerate([(-80, -11, 6), (-48, -6.5, 3), (-16, -4.5, 1), (16, -4.5, -1), (48, -6.5, -3), (80, -11, -6)])],
        P("grommet_l", circ(1.6), "$steel", at=(-91, -14), stroke=INK_HAIR),
        P("grommet_r", circ(1.6), "$steel", at=(91, -14), stroke=INK_HAIR),
        P("patch", R(16, 12, 1), "$bone.dark", at=(56, -28), rot=8, stroke=INK_HAIR),
        P("patch_stitch", R(12, 1, 0.3), "$ink@0.5", at=(56, -28), rot=8),
        P("roof_grit", ell(18, 2.4), "$sand@0.5", at=(-8, -38)),
        *roof_page,
        # The front poles, and their ropes out to the pegs.
        pole("pole_fl", -94, 22, 72, "$steel.dark"),
        pole("pole_fr", 94, 22, 72, "$steel.dark"),
        P("pole_fl_lit", R(1, 64, 0.4), "$steel@0.9", at=(-95.2, 24)),
        P("pole_fr_lit", R(1, 64, 0.4), "$steel@0.9", at=(92.8, 24)),
        *[P(f"lash_{side}_{i}", R(7, 1.4, 0.5), "$bone.dark", at=(sx * 94, -9 + i * 2.2)) for side, sx in (("l", -1), ("r", 1)) for i in range(3)],
        band("rope_l", [(-95, -12), (-102, 20), (-108, 56)], 1.1, "$bone.dark@0.85"),
        band("rope_r", [(95, -12), (102, 20), (108, 56)], 1.1, "$bone.dark@0.85"),
        P("peg_l", R(3, 7, 1), "$steel.dark", at=(-108, 57), stroke=INK_HAIR),
        *rope_coil("coil", -96, 63, loops=3, tail=-1),
        P("peg_r", R(3, 7, 1), "$steel.dark", at=(108, 57), stroke=INK_HAIR),
        # The jar hung from the middle of the front edge.
        P("jar_cord", R(1.2, 12 + jar_bail_top(11, 13)[1] + 4, 0.4), "$bone.dark", at=(0, (12 + jar_bail_top(11, 13)[1] - 4) / 2)),
        *jar(
            "jar", 0, 12, 11, 13, bail=True, inner="$spore@0.12",
            behind=halo("jar_glow", 0, 1, 15, 13, 0.5),
            contents=[*cap("jar_cap_a", -1.6, 2, 3), *cap("jar_cap_b", 2.4, -1.5, 2.3)],
        ),
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
                *[track(q["id"], "rot", [(0, 0), (0.4, 8), (0.6, -3), (1, 0)]) for q in roof_page],
                *[track(q["id"], "rot", [(0, 0), (0.3, 6), (0.55, -3), (1, 0)]) for q in note_b],
                track("jar_cap_a_lit", "opacity", [(0, 0.7), (0.5, 1), (1, 0.7)]),
                track("jar_cap_b_lit", "opacity", [(0, 1), (0.5, 0.7), (1, 1)]),
                *glow_tracks("jar_glow", 0.75, 1),
            ],
        )
    }
    return doc(
        "ss.base.frame",
        "The frame",
        "Arin's frame, put up on the first day (A001: \"Base frame and water tank up.\"), with a canvas over it: where the camp sleeps "
        "between expeditions. Four poles; the canvas is let down from the back bar to the ground for a wall, and stretched forward over the "
        "front poles, sagging between them, with guy ropes out to pegs. Pages are pinned to the wall on a cord, a bone patch is stitched on "
        "the roof, and a loose page has blown up onto it. Underneath on a ground sheet is a sleeping bag laid out, quilted, its top "
        "turned back on its lining and the dent where somebody lay still in it, a pillow at its head; another still rolled and strapped; a "
        "mug and a stack of pages to read by under a stone; a coil of rope by the left peg. A jar of glowing caps hangs from the middle of the front edge, and its light is the "
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
        ao("leg_ao", 0, 19.6, 30, 1.8, 0.45),
        *shaded("body", rr(36, 44, 6, (0, -2)), "$steel", [(6, 19, "$steel.dark")], axis=0),
        P("body_lit", R(4, 36, 2), "$steel.light", at=(-11, -2)),
        # A dent, and rust from the tap down the side.
        P("dent", ell(4, 2.6), "$steel.dark", at=(8, -4)),
        P("dent_lit", ell(3, 0.9), "$steel.light@0.8", at=(7.4, -1.8)),
        *rust("rust_tap", 15, 16, 2, 6, 0.5),
        P("cap", ell(18, 5), "$steel.light", at=(0, -24), stroke=INK_THIN),
        P("cap_lid", ell(7, 2.2), "$slate", at=(0, -25)),
        # The fill valve on top, a wheel on a stem.
        P("valve_stem", R(2, 4, 0.6), "$slate.dark", at=(9, -27)),
        P("valve", {"kind": "ring", "r": 2.8, "width": 1}, "$slate.dark", at=(9, -29.4)),
        P("valve_hub", circ(0.8), "$steel", at=(9, -29.4)),
        P("band_a", R(37, 3, 1), "$slate", at=(0, -12)),
        P("band_b", R(37, 3, 1), "$slate", at=(0, 10)),
        *rivet_row("band_a_rv", -14, -12, 14, -12, 5, 0.6, "$slate.light@0.8"),
        *rivet_row("band_b_rv", -14, 10, 14, 10, 5, 0.6, "$slate.light@0.8"),
        # The gauge: a strip of glass with the water standing in it, ticked.
        P("gauge", R(5, 26, 2), "$frost.dark@0.5", at=(-3, 0), stroke=INK_HAIR),
        P("gauge_water", R(3, 14, 1.5), "$aqua@0.75", at=(-3, 5)),
        P("gauge_surface", R(3, 0.7, 0.3), "$white@0.6", at=(-3, -1.6)),
        *[P(f"gauge_tick_{i}", R(1.6, 0.5, 0.2), "$ink@0.5", at=(0.6, -8 + i * 5)) for i in range(4)],
        # A tin cup on a hook for whoever is thirsty.
        *mug("cup", -21 - 2.8 * 0.85, -2.4 + 5.6 * 0.85, s=0.85, ground=False),
        *hook("hook", -18 - (2.2 + 0.8) * 0.75, -0.83 - 1.8 * 0.85 + 0.95 * 0.85 / 2, 0.75, reach=2.2),
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
        "The water tank Arin put up beside the frame on the first day (A001). A steel drum on two legs with riveted slate bands and a dent, "
        "a fill valve on top, a ticked glass gauge with the water standing in it, a tin cup on a hook, and a tap that drips into a small "
        "puddle and has rusted the side under it (`drip`). It is cold, like everything the expedition carried in.",
        (56, 62),
        parts,
        anims,
    )


# ============================================================== the shelf: seven boxes of paper
def shelf():
    loose_b = page("loose_b", 54, 29, w=10, h=9, rot=10, fill="$husk", lie=0.7, pivot="centre")
    parts = [shadow("shadow", 0, 30, 60, 8)]
    # Seven boxes (A055): three on the ground, three on those, one on top.
    # Each is numbered in the expedition's way — a count of strokes on its
    # face — has steel corners, rope handles on the bottom row, and the
    # shade of the box above lying on its lid. The top one's lid is off
    # its seat: somebody was in it last.
    boxes = [(-34, 16), (0, 18), (34, 16), (-18, -4), (16, -3), (46, -1), (-2, -24)]
    pages = [(-1, -1), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1), (1, -1)]
    for i, (x, y) in enumerate(boxes):
        w = 34 if i < 3 else 30 if i < 6 else 28
        top = i == 6
        if i >= 3:
            parts.append(ao(f"box_{i}_ao", x, y + 11, w - 2, 2.2, 0.45))
        parts += [
            *shaded(f"box_{i}", rr(w, 20, 2, (x, y)), "$slate", [(y + 4, y + 11, "$slate.dark")]),
            P(f"box_{i}_face", R(w - 8, 8, 1.5), "$slate.light@0.45", at=(x, y)),
            P(f"box_{i}_corner", R(4, 18, 1), "$steel@0.8", at=(x - w / 2 + 3, y)),
            P(f"box_{i}_corner_r", R(3, 18, 1), "$steel.dark@0.9", at=(x + w / 2 - 2.5, y)),
            # The count: i + 1 strokes, the fifth across the four.
            *[P(f"box_{i}_n{k}", R(0.9, 4.4, 0.3), "$bone@0.85", at=(x - 4 + (k % 4) * 2.2 + (5 if k >= 5 else 0), y + 0.2)) for k in range(i + 1) if k != 4],
            *([P(f"box_{i}_n4", R(8, 0.9, 0.3), "$bone@0.85", at=(x - 0.7, y + 0.2), rot=-26)] if i >= 4 else []),
        ]
        if i < 3:
            parts += [
                P(f"box_{i}_handle_l", ring_arc(2.4, 0.9, 90, 270), "$bone.dark", at=(x - w / 2 - 0.6, y + 2)),
                P(f"box_{i}_handle_r", ring_arc(2.4, 0.9, -90, 90), "$bone.dark", at=(x + w / 2 + 0.6, y + 2)),
            ]
        lid_y = y - 10.5 if top else y - 9
        parts += [
            P(f"box_{i}_lid", R(w + 2, 5, 1.5), "$slate.light", at=(x + (2 if top else 0), lid_y), rot=-5 if top else 0, stroke=INK_HAIR),
            lit_edge(f"box_{i}_lid_lit", x - w / 2 + 2, x + w / 2 - 2, lid_y - 1.6, 0.8, "$white@0.3"),
        ]
        # Paper standing proud of every lid, a different lie in each box.
        dx, dr = pages[i]
        parts += [
            P(f"box_{i}_page", R(w * 0.5, 7, 0.6), "$bone", at=(x + dx * 3, y - 13), rot=dr * 7, stroke=INK_HAIR),
            P(f"box_{i}_page2", R(w * 0.35, 6, 0.6), "$husk", at=(x - dx * 4 + 4, y - 12), rot=-dr * 5),
            P(f"box_{i}_line", R(w * 0.3, 1, 0.3), "$slate.dark@0.55", at=(x + dx * 3, y - 14), rot=dr * 7),
        ]
    parts += [
        # The cord round the top box, knotted.
        P("cord", R(30, 1.6, 0.5), "$bone.dark", at=(-2, -22)),
        P("cord_knot", circ(1.4), "$bone.dark", at=(8, -22), stroke=INK_HAIR),
        # Loose pages that did not make it into a box, one weighted with a stone.
        *page("loose_a", -54, 30, w=12, h=11, rot=-14, lie=0.7),
        *stone("loose_stone", -53, 30.5, s=0.7),
        *loose_b,
    ]
    anims = {
        "stir": loop(
            "the wind lifts the pages standing proud of the lids, one box after another",
            3.2,
            [track(f"box_{i}_page", "rot", [(0, 0), (0.12 * i + 0.1, 5), (min(0.95, 0.12 * i + 0.3), 0), (1, 0)]) for i in range(7)]
            + [track(q["id"], "rot", [(0, 0), (0.4, 8), (0.6, -2), (1, 0)]) for q in loose_b],
        )
    }
    return doc(
        "ss.base.shelf",
        "The shelf",
        "The seven boxes of paper (A055: \"Base inventory: the frame, the tank, seven boxes of paper, the saw.\"), stacked three, three and one "
        "in cold slate crates with steel corners, each numbered on its face in the expedition's way — a count of strokes, one to seven — and "
        "the bottom row with rope handles. Paper stands proud of every lid; the top box's lid is off its seat and a cord is knotted round "
        "it; loose pages that never got in lie beside, one weighted with a stone. This is the ninth expedition's shelf (guide §3.3, §12.1), "
        "where the pages the player picks up are filed. feelers opens the COLLECTION here. The pages stir in the wind (`stir`).",
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
    hung = []
    for i, x in enumerate(xs):
        y = cord_y(x)
        w, h = (10, 13) if i % 2 == 0 else (11, 11)
        sheet = page(f"page_{i}", x, y + h / 2 + 0.5, rot=tilt(i), w=w, h=h, fill=fills[i], ear=None if i % 3 else "br", seed=i + 2, pivot=(0, -h / 2 - 0.5))
        hung.append(sheet)
        parts += [*sheet, P(f"peg_{i}", R(2, 3.6, 0.6), "$steel.light", at=(x, y), stroke=INK_FINE)]
    parts += page("fallen", 18, 25, w=10, h=9, rot=12, lie=0.7, ear="tl")
    swing = lambda i: [(0, 0), (0.08 + i * 0.1, 9), (0.3 + i * 0.1, -3), (1, 0)]
    anims = {
        "stir": loop(
            "the wind goes down the line and the pages swing on their pegs, one after another",
            2.8,
            [track(q["id"], "rot", swing(i)) for i, sheet in enumerate(hung) for q in sheet],
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
    # A tag on a string off the right clamp: what is in it, written down. It swings about the knot.
    label = tag("tag", 21, -10, rot=-14, s=1.15)
    parts = [
        shadow("shadow", 0, 34, 26, 6),
        # A riveted stand on two feet.
        P("foot_l", R(8, 3, 1), "$slate.dark", at=(-14, 34.5), stroke=INK_HAIR),
        P("foot_r", R(8, 3, 1), "$slate.dark", at=(14, 34.5), stroke=INK_HAIR),
        P("stand", R(40, 8, 2), "$slate", at=(0, 30), stroke=INK_THIN),
        P("stand_lit", R(30, 1.6, 0.8), "$slate.light", at=(0, 27.4)),
        *[p for i, x in enumerate([-14, 0, 14]) for p in bolt(f"stand_bolt_{i}", x, 31, 1, "$slate.dark")],
        ao("stand_ao", 0, 25.6, 34, 1.6, 0.5),
        # The glass, drawn behind the jelly so the colour is the jelly's.
        P("glass", R(40, 46, 9), "$frost.dark@0.32", at=(0, 3), stroke=INK_THIN),
        *shaded("jelly", rr(36, 30, 8, (0, 10)), "$gold", [(-6, 0, "$gold.light"), (16, 26, "$chitin")], stroke=None),
        P("meniscus", ell(17, 2.6), "$gold.light2", at=(0, -4)),
        P("meniscus_edge", ell(17, 2.6), None, at=(0, -4), stroke={"color": "$chitin@0.6", "width": "hair"}),
        P("caustic", ell(6, 2), "$gold.light2@0.8", at=(-7, 8)),
        P("bubble_a", circ(1.6), "$gold.light2@0.9", at=(8, 12)),
        P("bubble_b", circ(1.1), "$gold.light2@0.8", at=(5, 18)),
        P("speck_a", circ(0.7), "$chitin.dark@0.7", at=(-6, 16)),
        P("speck_b", circ(0.6), "$chitin.dark@0.6", at=(10, 20)),
        P("glass_lit", R(4, 34, 2), "$white@0.45", at=(-14, 2)),
        P("glass_lit_b", R(1.6, 10, 0.8), "$white@0.3", at=(14, -6)),
        # The lid, bolted down on the glass's rim, and its two clamps.
        P("rim", R(41, 1.8, 0.6), "$steel.dark", at=(0, -16.6), stroke=INK_FINE),
        *shaded("lid", rr(44, 7, 2.5, (0, -21)), "$steel", [(-25, -22, "$steel.light")]),
        *[p for i, x in enumerate([-15, -5, 5, 15]) for p in bolt(f"lid_bolt_{i}", x, -20.4, 0.9, "$steel.dark")],
        *clamp("clamp_l", -22, -24.5),
        *clamp("clamp_r", 22, -24.5, side="r"),
        # A tag on a cord off the right clamp: what is in it, written down.
        *label,
        # The ladle hooked over the lid's end, and the drop that got away.
        *ladle("ladle", -21.3, -23.8, side="left", s=0.9),
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
                *[track(q["id"], "rot", [(0, 0), (0.5, 6), (1, 0)]) for q in label],
            ],
        )
    }
    return doc(
        "ss.base.vat",
        "The jelly vat",
        "The jelly the expedition trades in, kept in a glass vat on a riveted slate stand under a bolted, clamped steel lid. The glass is "
        "drawn behind the jelly so the colour is the jelly's: gold, because gold is jelly's (feelers D14), going to chitin in the deep, with "
        "light moving on the surface, a bubble rising and a few specks hanging in it (`settle`). A paper tag hangs off a clamp on a cord. "
        "A ladle with gold in its bowl is hooked over the rim and a drop has run down the side. The guide's meta shop is \"to evolve on "
        "jelly\" (§12.1), so feelers opens EVOLUTION here.",
        (60, 84),
        parts,
        anims,
    )


# ============================================================== the bench
def bench():
    vials = ["$venom", "$ember", "$frost", "$bile", "$aqua", "$orchid"]
    parts = [
        shadow("shadow", 0, 26, 54, 7),
        # A field table on crossed legs, a stretcher between them, a crate
        # under it.
        *shaded("under_crate", rr(26, 14, 1.5, (-4, 18)), "$slate", [(20, 26, "$slate.dark")], stroke=INK_HAIR),
        P("under_crate_lid", R(27, 3, 1), "$slate.light", at=(-4, 11.5)),
        P("under_crate_stencil", R(10, 1.6, 0.5), "$frost.dark@0.6", at=(-4, 18)),
        P("stretcher", R(72, 2.4, 1), "$slate.dark", at=(0, 14), stroke=INK_HAIR),
        P("leg_a", R(4, 30, 1.5), "$slate", at=(-34, 12), rot=18, stroke=INK_HAIR),
        P("leg_b", R(4, 30, 1.5), "$slate", at=(-34, 12), rot=-18, stroke=INK_HAIR),
        P("leg_c", R(4, 30, 1.5), "$slate", at=(34, 12), rot=18, stroke=INK_HAIR),
        P("leg_d", R(4, 30, 1.5), "$slate", at=(34, 12), rot=-18, stroke=INK_HAIR),
        *bolt("leg_bolt_l", -34, 12, 1.2, "$steel"),
        *bolt("leg_bolt_r", 34, 12, 1.2, "$steel"),
        P("top", R(100, 9, 2.5), "$steel", at=(0, -4), stroke=INK_THIN),
        lit_edge("top_lit", -46, 42, -7.4, 1.4, "$steel.light"),
        P("top_edge", R(100, 3, 1.5), "$steel.dark", at=(0, 0)),
        *scratches("top_scuff", 6, -4.6, 60, 2.4, 4, "$steel.light@0.6", 5),
        # The rack of samples the level-up draws from: stoppered tubes, and
        # one slot empty — that one is in the syringe.
        *tube_rack("rack", -20, -6.4, fills=(vials[0], vials[1], None, vials[2], vials[3], vials[4], vials[5])),
    ]
    parts += [
        # The instrument: a box with a dial, its face the instrument's blue,
        # ticks round it and two knobs under it.
        P("box", R(20, 14, 2), "$slate.dark", at=(40, -15), stroke=INK_THIN),
        lit_edge("box_lit", 31, 49, -21.4, 0.8, "$slate.light"),
        *dial("dial", 40, -15, s=1.15, face="$frost.light", reading=0.38),
        P("knob_a", circ(1.2), "$steel", at=(34, -10.4), stroke=INK_HAIR),
        P("knob_b", circ(1.2), "$steel", at=(46, -10.4), stroke=INK_HAIR),
        # The syringe, lying where the last dose was drawn, and the drop it left.
        *syringe("syringe", 17, -4.4, rot=-5),
        # A notebook page under the rack, held down with a stone.
        *page("note", -44, -6, w=14, h=10, rot=-8, lie=0.8),
        *stone("note_stone", -41, -6.4, s=0.7),
    ]
    anims = {
        "read": loop(
            "the dial's needle wanders and settles: the instrument reading the air",
            3.0,
            [track("dial_needle", "rot", [(0, 0), (0.3, 15), (0.55, -7), (0.75, 5), (1, 0)])],
        )
    }
    return doc(
        "ss.base.bench",
        "The bench",
        "The instrument's own table: a field bench on bolted crossed legs with a stretcher between them and a stencilled crate under it, "
        "its steel top scuffed. On it is a rack of stoppered sample tubes in the colours the level-up's samples come in, one slot empty: that "
        "dose is in the syringe lying beside it, graduated, its plunger drawn back and a drop at its needle. There is a notebook page held down by a stone, and a slate box whose dial is the instrument's "
        "blue, ticked round, with two knobs. The needle wanders, reading the air (`read`). feelers opens BUILD here, where the order samples "
        "are drawn in is planned.",
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
        under = clip(moved(jag, (x, y)), 1, y + r * 0.18, y + r)
        return [
            P(f"stone_{i}", poly(jag), "$smoke" if i % 3 else "$smoke.dark", at=(x, y), stroke=INK_HAIR),
            *([P(f"stone_{i}_dk", poly(under), "$ink@0.28")] if len(under) >= 3 else []),
            P(f"stone_{i}_lit", ell(r * 0.45, r * 0.18), "$smoke.light@0.8", at=(x - r * 0.2, y - r * 0.32)),
        ]

    caps = [
        ("c0", -12, -2, 4.2), ("c1", -3, -5, 5.4), ("c2", 8, -3, 4.6), ("c3", 15, 2, 3.2),
        ("c4", -16, 5, 3.0), ("c5", -6, 4, 4.0), ("c6", 5, 6, 3.6), ("c7", 12, 8, 2.4),
    ]
    # And three that have got out over the stones: it spreads.
    strays = [("s0", -33, 13, 1.7), ("s1", 35, 6, 1.5), ("s2", 24, -11, 1.4)]
    parts = [
        # The light the caps lay on the ground round the ring.
        *halo("spill", 0, 6, 44, 24, 0.36),
        P("bed", ell(24, 11), "$soil", at=(cx, cy)),
        P("bed_lit", ell(18, 6), "$soil.light@0.8", at=(cx, cy + 3)),
    ]
    parts += [p for i, x, y, r, front in stones if not front for p in stone(i, x, y, r)]
    parts += halo("halo", 0, -2, 26, 18, 0.5)
    for cid, x, y, r in caps:
        parts += cap(cid, x, y, r)
        if r > 4:
            # Speckles on the big ones, the way a cap is marked.
            parts += [
                P(f"{cid}_spot_a", circ(r * 0.12), "$spore.dark", at=(x + r * 0.35, y - r * 0.08)),
                P(f"{cid}_spot_b", circ(r * 0.09), "$spore.dark", at=(x + r * 0.05, y + r * 0.12)),
            ]
    parts += [p for i, x, y, r, front in stones if front for p in stone(i, x, y, r)]
    parts += [p for cid, x, y, r in strays for p in cap(cid, x, y, r)]
    # Two mugs left by the ring, and spores going up off the caps.
    parts += [
        *mug("mug_a", 33, 21.2, s=0.9),
        *mug("mug_b", -34, 20.5, s=0.9, tipped=True, facing="left"),
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
        "round the hive's light instead: a ring of stones round a bed of dug earth, and in the bed the glowing caps, speckled the way caps "
        "are, grown from the one Sol carried in an emitter that never worked — three small ones have already got out over the stones. They "
        "are the warm thing in a cold camp and they are not the camp's. Two steel mugs have been left by the ring. The caps brighten and "
        "dim, slower than breathing, and spores go up off them (`breathe`).",
        (92, 60),
        parts,
        {"breathe": loop("the caps brighten and dim, slower than breathing, and spores go up off them", 4.0, tracks)},
    )


# ============================================================== the marker: the middle of the camp
def marker():
    strips = [
        # (y on the mast, side, length, fill) — eight, one for each expedition.
        (-12, 1, 15, "$frost.dark"), (-6, -1, 13, "$slate.light"), (0, 1, 12, "$frost"), (6, -1, 15, "$frost.dark"),
        (12, 1, 11, "$slate.light"), (18, -1, 13, "$frost"), (24, 1, 14, "$frost.dark"), (30, -1, 10, "$slate.light"),
    ]
    parts = [
        shadow("shadow", 0, 62, 16, 4, "0.4"),
        # The rest of the lander's mast, driven into the ground, its snapped
        # end up; a collar where two lengths of it were joined.
        P("sleeve", R(9, 12, 1.5), "$slate.dark", at=(0, 55), stroke=INK_HAIR),
        lit_edge("sleeve_lit", -3.6, 3.6, 49.6, 0.8, "$slate.light@0.8"),
        *shaded("mast", [(-2.6, -50), (-1, -56), (0.6, -52), (2.6, -57), (2.6, 60), (-2.6, 60)], "$steel.dark", [(-60, 61, "$steel.dark")], stroke=INK_HAIR),
        P("mast_lit", R(1.1, 100, 0.4), "$steel", at=(-1.3, 6)),
        P("joint", R(7, 4, 1), "$steel", at=(0, 40), stroke=INK_HAIR),
        lit_edge("joint_lit", -3, 3, 38.6, 0.7, "$white@0.5"),
        P("snap_lit", poly([(-2.6, -50), (-1, -56), (0.6, -52), (0.6, -50)]), "$steel.light"),
        # The clamps that hold the plate to it, bolted at both ends.
        P("clamp_top", R(46, 3, 1), "$steel.dark", at=(0, -45), stroke=INK_HAIR),
        P("clamp_low", R(46, 3, 1), "$steel.dark", at=(0, -23), stroke=INK_HAIR),
        *[p for i, (x, y) in enumerate([(-22, -45), (22, -45), (-22, -23), (22, -23)]) for p in bolt(f"clamp_bolt_{i}", x, y, 1.1, "$steel")],
        # The plate (T041): bevelled, its top edge catching the hearth's light,
        # the one line cut in it — the same word as the ruin's stones and
        # Eden's iron — scuffed by years of hands.
        *shaded("plate", rr(38, 24, 2, (0, -34)), "$steel.light", [(-27, -22, "$steel")]),
        lit_edge("plate_bevel", -17, 17, -45.2, 1.2, "$white@0.6"),
        P("plate_lit", R(26, 1.6, 0.8), "$white@0.25", at=(-3, -42)),
        P("plate_under", R(36, 1.2, 0.6), "$steel.dark", at=(0, -22.8)),
        *scratches("plate_scuff", 0, -32, 30, 14, 5, "$steel.light2@0.7", 3),
        P("line", R(26, 2, 0.6), "$ink@0.75", at=(0, -35)),
        P("line_lit", R(26, 0.8, 0.3), "$steel.light2@0.8", at=(0, -33.6)),
        *[p for i, (dx, dy) in enumerate([(-16, -9), (16, -9), (-16, 9), (16, 9)]) for p in bolt(f"rivet_{i}", dx, -34 + dy, 1.4, "$slate")],
        *rust("rust_a", -16, -24, 2.4, 16, 0.6),
        *rust("rust_b", 16, -24, 2.4, 11, 0.5),
        P("rust_bloom", ell(3, 2), "$rust@0.35", at=(-16, -25)),
    ]
    # Eight strips of cloth tied down the mast, alternate sides: one for each
    # expedition that set out from here (T045: "eight times, and once in
    # stone"). Each has its knot, a fold of shade under it and a frayed end,
    # and is cut into lengths so the wind can run down it (`streamer`).
    tail = lambda n: [(0, -1.6), (n * 0.55, -2.2), (n, -0.6), (n * 0.8, 0.6), (n, 2.2), (n * 0.5, 1.8), (0, 1.6)]
    fold = lambda n: [(0, 0.6), (n * 0.5, 1.2), (n * 0.95, 2.0), (n * 0.5, 1.9), (0, 1.6)]
    # The crease is the cloth's own colour a step down rather than ink washed
    # over it, so where two lengths overlap it does not darken or crack.
    crease = {"$frost": "$frost.dark", "$frost.dark": "$frost.dark2", "$slate.light": "$slate"}
    for i, (y, side, n, fill) in enumerate(strips):
        parts += [
            *streamer(f"strip_{i}", side * 2.4, y, tail(n), fill, side=side, fold=fold(n), fold_fill=crease[fill]),
            P(f"knot_{i}", R(6.4, 2.6, 1), "$bone.dark", at=(0, y)),
            P(f"knot_{i}_lit", R(4, 0.7, 0.3), "$bone@0.9", at=(-0.6, y - 0.7)),
        ]
    parts += [
        # The hive, starting up it from the foot (A055).
        *bud("bud_a", -4, 50, 0.8, -0.4),
        *bud("bud_b", 3, 46, 0.6, 0.4),
    ]
    # The wind comes down the mast: each strip a little behind the one above
    # it, the longer ones reaching further, every one whipping at its frayed
    # end while its knot holds. A first draft swung each strip whole about its
    # knot, a few degrees each way, and the strips read as feathers — stiff
    # vanes stuck in the mast, tilting — not cloth.
    flap = []
    for i, (y, side, n, _f) in enumerate(strips):
        flap += streamer_tracks(f"strip_{i}", tail(n), side=side, swing=13 + n * 0.6, flick=6 + (i % 3), lag=i * 0.11)
    doc(
        "ss.base.marker",
        "The marker",
        "The middle of the camp: the plate off the lander (T041), stood up on what is left of the lander's mast and driven into the ground, "
        "with the hearth's caps round its foot. The plate is bevelled and riveted on with two bolted clamps, scuffed by years of hands, and "
        "has the one line cut in it — the same word as the ruin's stones and Eden's iron, which every writer was given and wrote down as an "
        "attack. It is the game's own line: do not come. Rust has bled from its lower rivets. Down the mast, below a collar where two lengths "
        "of it were joined, are eight strips of cold cloth knotted on, alternate sides, one for each expedition that set out from here (T045: "
        "\"Read as one log they say do not come, eight times\"); they flap in the wind (`flutter`), a wave running out from each knot to its "
        "frayed end, each strip a little after the one above it — cut into lengths so the cloth bends, not swung whole like a vane. At the foot the hive is starting up it: "
        "two pink buds (A055). feelers stands it in the middle of the base, the stations round it.",
        (64, 136),
        parts,
        {"flutter": loop("the eight strips flap in the wind, a wave running out from each knot to its frayed end, each strip a little after the one above it", 1.6, flap)},
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
        *page("note", 15, -2, w=10, h=8, fill="$husk", rot=8, words=False),
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
    """The lamps' jar: three caps behind glass, the light they lay round it, a screw lid with vents and a bail to hang it by."""
    return jar(
        prefix, x, y, 14, 16, bail=True, vents=3, inner="$spore@0.12",
        behind=halo(f"{prefix}_glow", 0, 0, 12, 12, 0.36),
        contents=[*cap(f"{prefix}_cap_a", -2, 3, 3.6), *cap(f"{prefix}_cap_b", 3, -1, 2.8), *cap(f"{prefix}_cap_c", -1.4, -3.6, 2.2)],
    )


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
        P("leg_l", R(2, 9, 0.6), "$steel.dark", at=(-12.4, 17), rot=28, stroke=INK_HAIR),
        P("leg_r", R(2, 9, 0.6), "$steel.dark", at=(-5.6, 17), rot=-28, stroke=INK_HAIR),
        P("foot", ell(5, 2.4), "$smoke", at=(-9, 20.4), stroke=INK_HAIR),
        P("foot_lit", ell(2.6, 0.8), "$smoke.light@0.8", at=(-10, 19.4)),
        *[P(f"wrap_{i}", R(4.2, 1, 0.4), "$bone.dark", at=(-9, 2 + i * 1.6)) for i in range(3)],
        P("arm", R(16, 2.4, 1), "$steel.dark", at=(-2, -15), stroke=INK_HAIR),
        *lamp_jar("jar", 5, 3.6),
        *hook("hook", 5, jar_bail_top(14, 16)[1] + 0.8 + 3.6, mount="screw", reach=jar_bail_top(14, 16)[1] + 0.8 + 3.6 + 13.8),
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
    hung = lamp_jar("jar", 0, 0)
    top = jar_bail_top(14, 16)[1]
    hanging = [
        P("cord", R(1.4, top + 20, 0.5), "$bone.dark", at=(0, (top - 20) / 2)),
        P("cord_knot", R(2.6, 1.6, 0.6), "$bone.dark", at=(0, top - 0.4), stroke=INK_FINE),
        *hung,
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
                + [track(p["id"], "x", [(0, 0), (0.5, 1.4), (1, 0)]) for p in hung + [hanging[1]]],
            )
        },
    )
    path_jar = [
        shadow("shadow", 0, 7, 6, 2, "0.4"),
        *jar(
            "jar", 0, 1, 10, 12, inner="$spore@0.12",
            behind=halo("glow", 0, -1, 9, 8, 0.36),
            contents=[*cap("cap_a", -1.4, 2, 2.6), *cap("cap_b", 2, -1, 2)],
        ),
    ]
    doc(
        "ss.base.jar",
        "Path jar",
        "A small jar of glowing caps set down on the ground, one of a row along each path out of the camp, so the way back in can be found "
        "in the dark. It breathes like the lamps (`breathe`).",
        (20, 20),
        path_jar,
        {"breathe": loop("the caps brighten and dim", 3.6, [*glow_tracks("glow", 0.7, 1), track("cap_a_lit", "opacity", [(0, 0.7), (0.5, 1), (1, 0.7)])])},
    )


# ============================================================== the lockers and the keeps
def locker():
    parts = [
        shadow("shadow", 0, 10, 16, 3.5),
        *shaded("box", rr(30, 16, 2, (0, 2)), "$slate", [(5, 11, "$slate.dark")]),
        P("stripe", R(30, 2, 0.5), "$frost.dark@0.5", at=(0, 7)),
        *scratches("scuff", 4, 4, 18, 6, 3, "$slate.light@0.7", 9),
        ao("lid_ao", 0, -3.4, 30, 1.4, 0.45),
        *hinge("hinge_a", -9, -8.7, leaf=0, length=5),
        *hinge("hinge_b", 9, -8.7, leaf=0, length=5),
        P("lid", R(32, 5, 1.5), "$slate.light", at=(0, -6), stroke=INK_HAIR),
        lit_edge("lid_lit", -14, 14, -7.6, 0.8, "$white@0.35"),
        *[P(f"corner_{i}", R(3, 3, 0.6), "$steel", at=(x, y)) for i, (x, y) in enumerate([(-14, -6.4), (14, -6.4), (-13.6, 8.6), (13.6, 8.6)])],
        # The hasp down over its staple. No lock in it: whose locker is open is the game's to say, not the drawing's.
        *hasp("hasp", 0, -3.5, locked=False),
        # A grab handle on the lid: the lockers stand shoulder to shoulder, so it is carried from the top.
        P("grip", R(10, 1.6, 0.8), "$steel.dark", at=(0, -8.8), stroke=INK_HAIR),
        P("grip_lit", R(8, 0.6, 0.3), "$steel@0.9", at=(0, -9.2)),
    ]
    doc(
        "ss.base.locker",
        "Locker",
        "One writer's footlocker, in the cold slate everything of the expedition's is: a box with steel corners, a hinged lid with a "
        "grab handle on top, a latch and hasp, a frost stripe, a few scuffs. A row of eight stands at the foot of the frame's beds, one per writer "
        "in the order the expeditions came. On each lid is the one thing that writer's log kept (`ss.base.keep-*`). In feelers you take up "
        "a writer's body at their locker.",
        (36, 24),
        parts,
    )


# The one thing each writer's log kept, drawn in scripts/bits_keeps.py: each rests on its doc's y=+7
# (bits_keeps.FOOT), which feelers sets on the locker's lid.
KEEPS = {
    "arin": (
        "Arin's cartridges",
        "Arin's emitter was the prototype, and its forty cartridges dried on day 388 (feelers character plan §1.3). Five of the spent tubes stand in a "
        "riveted slate clip: frost glass, empty, steel-capped, each with the ring its last charge dried to, one standing proud and askew.",
        KEEP_PARTS["arin"],
    ),
    "sol": (
        "Sol's cap",
        "Sol's emitter never worked from the first day, and Sol carried a fungus cap in it instead. Here is the cap, dull and teal, with no "
        "light in it any more — the ones in the camp's jars and its hearth were grown from it. Its rim has dried wavy and cracked, and the gills "
        "show under it.",
        KEEP_PARTS["sol"],
    ),
    "haram": (
        "Haram's husk",
        "Haram put a moulted husk into the second-model emitter. It is a hollow, segmented shell in husk white, "
        "split down the back where it was shed, with stubs of legs and an empty mouth.",
        KEEP_PARTS["haram"],
    ),
    "mina": (
        "Mina's piece of wall",
        "A palm-sized piece of the burrow's wall, and it is warm (M041). It is a chunk of rust earth in strata, with a seam of the wall's own pull through "
        "it.",
        KEEP_PARTS["mina"],
    ),
    "kano": (
        "Kano's road stake",
        "Kano walked the swarm's road for 330 days. This is a marker stake from it, notched once for every ten days — thirty-three, cut in fives "
        "along its top — split at the head, stained where it stood in the ground, with a cold strip of cloth wound on and knotted.",
        KEEP_PARTS["kano"],
    ),
    "eden": (
        "Eden's jelly",
        "Eden put a finger of royal jelly into the emitter. It is a small jar with a screw lid, and that finger of "
        "gold in it.",
        KEEP_PARTS["eden"],
    ),
    "rowan": (
        "Rowan's bowl",
        "A bowl of the ruins' own stone, carved round its rim and chipped, with the old pheromone dried and crazed in it. Rowan's tubes turned to stone. The film in the bowl is pink, because it "
        "is the hive's signal.",
        KEEP_PARTS["rowan"],
    ),
    "teo": (
        "Teo's bundle",
        "Teo had nothing to put in the emitter but paper. This is a bundle of pages tied with cord, crossed and "
        "knotted, the edges uneven, the top sheet written on.",
        KEEP_PARTS["teo"],
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
        # Cut, the signal has gone out of it: the trunk is the drained
        # spire's mauve, not the field's pink, faceted the way a crystal grows.
        *shaded("trunk", [(-11, -4), (11, -4), (13, 9), (-13, 9)], "$mauve.dark", [(4, 10, "$mauve.dark2")]),
        P("trunk_lit", poly([(-9, -3), (-5, -3), (-6, 8), (-11, 8)]), "$mauve@0.8"),
        P("facet_a", poly([(-1, -3), (0.4, -3), (1, 8), (-0.6, 8)]), "$mauve.dark2@0.7"),
        P("facet_b", poly([(6, -3), (7.2, -3), (8.6, 8), (7.2, 8)]), "$mauve.dark2@0.6"),
        P("chip_a", poly([(-15, 10), (-12, 7), (-10, 10)]), "$mauve", stroke=INK_HAIR),
        P("chip_b", poly([(12, 10), (14, 8), (16, 10.4)]), "$mauve.dark", stroke=INK_HAIR),
        P("face", ell(11.5, 4.2), "$husk.dark", at=(0, -4), stroke=INK_THIN),
        *[P(f"ring_{i}", ell(9.4 - i * 2.3, 3.4 - i * 0.82), "$mauve.dark@0.55" if i % 2 == 0 else "$husk.dark", at=(0, -4)) for i in range(4)],
        P("heart", ell(1.4, 0.6), "$pheromone@0.85", at=(0, -4)),
        P("saw_mark", R(18, 0.9, 0.3), "$ink@0.35", at=(1, -3.4), rot=-4),
        lit_edge("face_lit", -8, 2, -7.6, 0.8, "$white@0.4"),
    ]
    doc(
        "ss.base.stump",
        "Cut spire",
        "A pheromone spire cut off flat. The signal has gone out of it: the trunk is a drained mauve rather than the field's pink, faceted the "
        "way a crystal grows, with chips at its foot. The face is pale and ringed like a tree, one ring per passing of the vermin (A030), "
        "with a little pink left at the heart and the saw's line across it. Three of these stand by the camp's south path, the cut spires "
        "the records found south of base (T010). In feelers they mark the way out to the Plains.",
        (32, 28),
        parts,
    )


# The cairn's strip of cloth, streaming out from the stake (its knot at (3, -20) in the cairn), with its
# two frayed tails; cut so the last cut stays clear of the lower tail's notch.
FLAG = [(0, -4), (11, -1), (9.6, 0.4), (12, 1.6), (9, 3), (12, 5), (0, 4)]
FLAG_FOLD = [(0, 1), (9, 1.4), (9, 2.6), (0, 2.4)]
FLAG_CUTS = (0.0, 0.26, 0.48, 0.68, 1.0)


def cairn():
    def slab(id, pts, top_fill, face_fill):
        cx = sum(x for x, _ in pts) / len(pts)
        top = [(pts[0][0] + 2, pts[1][1] + 1.6), pts[1], pts[2], (pts[3][0] - 2, pts[2][1] + 1.6)]
        return [
            P(f"{id}_under", poly([(cx + (x - cx) * 1.08, y + 1.2) for x, y in pts]), "$ink"),
            P(id, poly(pts), face_fill),
            P(f"{id}_top", poly(top), top_fill),
            band(f"{id}_crust", [pts[1], pts[2]], 0.9, "$white@0.7"),
        ]

    parts = [
        shadow("shadow", 0, 20, 15, 4),
        *slab("slab_a", [(-13, 18), (-11, 11), (10, 10), (13, 18)], "$husk", "$husk.dark"),
        *slab("slab_b", [(-10, 11), (-8, 4), (8, 3), (10, 10)], "$husk", "$husk.dark"),
        *slab("slab_c", [(-7, 4), (-5, -2), (6, -2), (7, 3)], "$silent", "$husk"),
        P("glare", poly([(-3, -1), (2, -1.6), (3, 0.6), (-2, 1)]), "$white@0.8"),
        P("crack", R(8, 0.9, 0.3), "$husk.dark2", at=(-2, 15)),
        P("crack_b", R(5, 0.8, 0.3), "$husk.dark2", at=(4, 7.4), rot=12),
        P("chip", poly([(10, 21), (13, 18.6), (16, 21)]), "$husk.dark", stroke=INK_HAIR),
        P("stake", R(2.6, 26, 0.8), "$smoke.light", at=(2, -12), stroke=INK_HAIR),
        P("binding_a", R(4, 1.2, 0.4), "$bone.dark", at=(2, -4)),
        P("binding_b", R(4, 1.2, 0.4), "$bone.dark", at=(2, -6)),
        *streamer("flag", 3, -20, FLAG, "$frost.dark", fold=FLAG_FOLD, fold_fill="$frost.dark2", cuts=FLAG_CUTS),
    ]
    anims = {
        "flutter": loop(
            "the strip of cloth on the stake flaps in the wind off the pan, a wave running out from the stake to its two frayed tails",
            1.4,
            # Tied along its whole edge, so it barely turns at the stake; out at the tails the pan's wind has it.
            streamer_tracks("flag", FLAG, swing=11, flick=6, gust=4, sag=3, cuts=FLAG_CUTS, lag=0.2),
        )
    }
    doc(
        "ss.base.cairn",
        "Salt cairn",
        "Three slabs of the pan's salt plate stacked by the north-west road, drawn the way the pan's own plates are (`ss.terrain.saltplate`), "
        "salt crusted white along their edges and cracked, a chip fallen at the foot, with a stake bound into them and a frayed strip of cold "
        "cloth flapping on it (`flutter`), cut into lengths so a wave can run out along it to its tails. In feelers this is the way out to the Salt Pan.",
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


# ============================================================== the structures
# Built things the camp has that are not stations: the fence round it, the
# larder, the sample cellar, the lab. Nothing to use in them; they are the
# camp's masses (feelers docs/staging-method.md §4), so their detail sits
# on a third of each and the rest is plate and earth.

def post():
    stake = [(-2, -16), (2, -16), (2, 20), (-2, 20)]
    parts = [
        shadow("shadow", 0, 20, 5.5, 1.6, "0.4"),
        P("dirt", ell(5, 1.6), "$sand@0.6", at=(0, 19.4)),
        *shaded("stake", stake, "$steel.dark", [(0.4, 2.1, "$slate.dark")], stroke=INK_HAIR, axis=0),
        P("stake_lit", R(0.9, 30, 0.4), "$steel@0.9", at=(-1.1, 3)),
        P("cap", R(6, 3, 1), "$steel", at=(0, -16.4), stroke=INK_HAIR),
        lit_edge("cap_lit", -2.4, 2.4, -17.4, 0.7, "$white@0.45"),
        *[P(f"lash_{i}", R(5.2, 0.9, 0.4), "$bone.dark", at=(0, -11 + i * 1.4)) for i in range(3)],
    ]
    doc(
        "ss.base.post",
        "Fence post",
        "A length of steel pipe from the lander driven into the ground, capped, with cord lashed round its top. The camp's fence is a ring "
        "of these with cord run between them (feelers draws the cord, so it can sag and move in the wind), gapped where the roads go out.",
        (12, 44),
        parts,
    )
    cloth = parts + [
        P("cloth", poly([(1.6, -12), (8, -11), (7, -6), (9, -1), (1.6, -3)]), "$frost.dark", stroke=INK_HAIR),
        P("cloth_fold", poly([(1.6, -7), (7, -6.4), (7.6, -5), (1.6, -5.4)]), "$ink@0.25"),
    ]
    doc(
        "ss.base.gatepost",
        "Gate post",
        "A fence post with a strip of cold cloth knotted on: the posts either side of a road out of the camp carry one, so the gap reads as "
        "a way through and not a break.",
        (20, 44),
        cloth,
    )


def larder():
    def arch(rx, top, base, n=14, cx=0):
        return [(cx + rx * math.cos(math.pi * k / n), base - (base - top) * math.sin(math.pi * k / n)) for k in range(n + 1)]

    roof = arch(46, -32, 8)
    end_wall = arch(40, -25, 8)
    parts = [
        shadow("shadow", 0, 36, 60, 8, "0.42"),
        # Dug in: a mound of earth banked up round a half-buried store.
        P("mound", poly([(-62, 34), (-58, 18), (-46, 8), (46, 8), (58, 18), (62, 34)]), "$sand.dark", stroke=INK_HAIR),
        band("mound_lit", [(-58, 18), (-46, 8), (46, 8), (58, 18)], 2, "$sand@0.85"),
        # Its roof is a curl of the lander's skin, corrugated.
        P("roof", poly(roof), "$steel.dark", stroke=INK_THIN),
        *[P(f"rib_{i}", R(1.2, max(1, 40 * math.sqrt(max(0.0, 1 - (x / 46) ** 2)) - 2), 0.4), "$ink@0.25",
            at=(x, 8 - (40 * math.sqrt(max(0.0, 1 - (x / 46) ** 2)) - 2) / 2)) for i, x in enumerate(range(-40, 41, 8))],
        band("roof_lit", [(46 * math.cos(math.pi * k / 10), 8 - 40 * math.sin(math.pi * k / 10)) for k in range(5, 10)], 2, "$steel@0.85"),
        P("roof_grit", ell(16, 2.4), "$sand@0.6", at=(-8, -29)),
        # The end wall, slate, and the door into the dark.
        P("end_wall", poly(end_wall), "$slate.dark"),
        P("doorway", R(18, 26, 3), "$coal", at=(-10, -4)),
        P("door", poly([(-19, -17), (-30, -14), (-30, 10), (-19, 9)]), "$steel", stroke=INK_HAIR),
        P("door_lit", poly([(-21, -15), (-24, -14.4), (-24, 8.4), (-21, 8.6)]), "$steel.light@0.7"),
        *bolt("door_pull", -27, -2, 1, "$slate.dark"),
        P("beam", R(64, 2.4, 1), "$slate", at=(2, -20), stroke=INK_HAIR),
        # What is kept: sacs cut out of things that stopped needing them, hung
        # to cure (the field's Chicken, S005), and the expedition's own tins.
        *[p for i, (x, y) in enumerate([(10, -10), (19, -7), (28, -11)]) for p in [
            P(f"sac_{i}_cord", R(0.8, 5, 0.3), "$bone.dark", at=(x, -17)),
            {"id": f"sac_{i}", "use": "ss.pickup.food", "at": [x, y + 2], "scale": 0.5},
        ]],
        *tin_stack("tin", 34, 28, opened=2),
        *sack("sack", -42, 28),
        *shaded("crate", rr(16, 11, 1.5, (-24, 26)), "$slate", [(28, 32, "$slate.dark")], stroke=INK_HAIR),
        P("step_a", ell(6, 2), "$smoke", at=(-12, 12), stroke=INK_HAIR),
        P("step_b", ell(4, 1.6), "$smoke.dark", at=(-4, 14), stroke=INK_HAIR),
    ]
    doc(
        "ss.base.larder",
        "The larder",
        "The camp's food store, dug in where the ground keeps cool: a half-buried hole banked with earth and roofed with a corrugated curl "
        "of the lander's skin. Under the roof a beam carries the sacs the field gives up, hung on cords to cure — the soft warm things the "
        "records call Chicken (S005), cut out of something that stopped needing them — and by the door are the expedition's own tins, a tied "
        "sack and a crate. The door stands open on the dark. Nothing to do here in feelers; it is part of the west wing, where the camp lives.",
        (128, 92),
        parts,
    )


def cellar():
    vial_cols = ["$venom", "$ember", "$frost", "$bile", "$aqua", "$orchid"]
    parts = [
        shadow("shadow", 0, 38, 26, 6, "0.42"),
        *[P(f"leg_{i}", R(4, 8, 1), "$slate.dark", at=(x, 34), stroke=INK_HAIR) for i, x in enumerate([-19, 19])],
        *shaded("body", rr(48, 60, 4, (0, 2)), "$steel", [(10, 25, "$steel.dark")], axis=0),
        P("body_lit", R(1.4, 50, 0.6), "$steel.light", at=(-21.4, 4)),
        P("top", R(52, 6, 2), "$steel.light", at=(0, -29), stroke=INK_HAIR),
        lit_edge("top_lit", -24, 24, -31.4, 0.8, "$white@0.5"),
        # The door: frosted glass with the samples on racks behind it, the
        # cold creeping in from its corners.
        P("glass", R(32, 40, 3), "$frost.dark@0.6", at=(-3, 3), stroke=INK_HAIR),
        *[P(f"shelf_{i}", R(30, 1.2, 0.4), "$slate.dark", at=(-3, -9 + i * 12)) for i in range(3)],
        *[p for r in range(3) for c in range(5) for p in vial(f"vial_{r}_{c}", -15 + c * 6, -9.6 + r * 12, fill=vial_cols[(r * 2 + c) % 6], muted=0.75, cold=True)],
        P("glass_haze", R(32, 40, 3), "$frost.light@0.25", at=(-3, 3)),
        P("frost_a", poly([(-19, -17), (-10, -17), (-14, -13), (-19, -9)]), "$white@0.55"),
        P("frost_b", poly([(13, 23), (13, 13), (9, 18), (4, 23)]), "$white@0.5"),
        P("frost_c", poly([(13, -17), (8, -17), (13, -12)]), "$white@0.4"),
        # Chained shut: round the cabinet's left side high, across the glass and through the handle; the
        # other end round the right side; a padlock through the two end links.
        *chain("chain", sag((-26, -16), (18.6, 3.6), 2.0, 8) + [(16.8, 12)], first="face", within=(-23.8, 23.8)),
        *chain("chain_b", [(26, 5.5), (18.0, 12)], first="edge", within=(-23.8, 23.8)),
        P("handle", R(2.4, 12, 1), "$steel.light", at=(17, 3), stroke=INK_HAIR),
        *padlock("lock", 17.4, 12, 0.85),
        # The thermometer: its needle well over to the cold.
        *dial("dial", 16, -22, s=0.93, reading=0.12),
        # Ice on the lip, and the cold breathing out at the foot.
        *[P(f"icicle_{i}", poly([(-1, 0), (1, 0), (0, 2.6 + (i % 2) * 1.6)]), "$frost.light@0.85", at=(x, -26)) for i, x in enumerate([-18, -10, -2, 8, 18])],
        P("mist_a", ell(8, 1.6), "$white@0.22", at=(-8, 33)),
        P("mist_b", ell(6, 1.4), "$white@0.18", at=(9, 34)),
    ]
    doc(
        "ss.base.cellar",
        "The sample cellar",
        "Where the samples are kept between expeditions: a squat steel cabinet on legs, frosted glass in its door, and behind the glass racks "
        "of vials in the six colours the level-up's samples come in, muted by the cold. Frost creeps in from the glass's corners and hangs in "
        "icicles off the lip; the thermometer's needle is well over to the cold; a chain and padlock keep it shut; the cold breathes out at "
        "its foot. It stands by the bench, which draws from it. Nothing to do here in feelers; it is part of the east wing.",
        (64, 88),
        parts,
    )


def lab():
    front = [(-70, -22), (50, -22), (50, 50), (-70, 50)]
    side = [(50, -22), (74, -36), (74, 36), (50, 50)]
    roof = [(-80, -20), (56, -20), (82, -40), (-54, -40)]
    parts = [
        shadow("shadow", 0, 54, 86, 10, "0.42"),
        # A shed of the lander's plates: a front, a side going back into the
        # dark, a single slope of corrugated roof.
        *shaded("side", side, "$smoke.dark", [(30, 51, "$coal@0.6")], stroke=INK_THIN),
        *shaded("front", front, "$smoke", [(-23, -14, "$steel@0.8"), (32, 51, "$smoke.dark")], stroke=INK_THIN),
        *[P(f"seam_{i}", R(1.4, 70, 0.5), "$ink@0.3", at=(x, 14)) for i, x in enumerate([-40, -10, 26])],
        *[p for i, x in enumerate([-40, -10, 26]) for p in rivet_row(f"seam_{i}_rv", x + 2.4, -16, x + 2.4, 44, 7, 0.7)],
        P("patch", R(16, 12, 1), "$steel.dark", at=(-56, 30), stroke=INK_HAIR),
        *rust("rust_a", -40, -18, 3, 26),
        *rust("rust_b", 26, -18, 2.6, 18, 0.5),
        P("roof", poly(roof), "$steel.dark", stroke=INK_THIN),
        *[P(f"roof_rib_{i}", poly([(-74 + i * 14, -21), (-72.6 + i * 14, -21), (-46.6 + i * 14, -39), (-48 + i * 14, -39)]), "$ink@0.25") for i in range(10)],
        band("roof_lit", [(-80, -20), (56, -20)], 2.2, "$steel"),
        P("roof_grit", ell(20, 2.4), "$sand@0.55", at=(10, -32)),
        # The window: a jar of caps on the sill inside, so it is lit a little.
        *shaded("window_frame", rr(26, 20, 2, (22, 2)), "$slate", [(8, 13, "$slate.dark")], stroke=INK_HAIR),
        P("window", R(20, 14, 1.5), "$coal", at=(22, 2)),
        *halo("window_glow", 24, 6, 9, 6, 0.6),
        *jar("window_jar", 26, 6, 5, 6, inner="$spore@0.12", contents=cap("window_cap", 0, 0.8, 1.7)),
        P("mullion_v", R(1.2, 14, 0.4), "$slate", at=(22, 2)),
        P("mullion_h", R(20, 1.2, 0.4), "$slate", at=(22, 2)),
        P("window_glint", R(6, 1, 0.4), "$frost@0.5", at=(16, -2), rot=-20),
        P("sill", R(28, 2.6, 1), "$slate.light", at=(22, 13.6), stroke=INK_HAIR),
        # The door, a canvas flap tied back.
        P("doorway", R(22, 38, 2), "$coal", at=(-38, 31)),
        *flap("flap", -49, 12),
        P("step", R(26, 4, 1.5), "$slate.dark", at=(-38, 51), stroke=INK_HAIR),
        # Readings pinned up by the door.
        *[p for i, (x, y, r) in enumerate([(-14, 6, -6), (-4, 4, 5), (-10, 18, 3)])
          for p in page(f"sheet_{i}", x, y, rot=r, w=8, h=10, fill="$bone" if i != 1 else "$husk", pin="pin", ear="br" if i == 2 else None, seed=11 + i)],
        # A mast on the roof for the wind meter (`ss.base.vane`), a cable down the side.
        P("mast", R(2.4, 34, 0.8), "$steel.dark", at=(64, -54), stroke=INK_HAIR),
        band("cable", [(66, -40), (70, -20), (72, 10), (80, 40), (86, 54)], 1.1, "$coal"),
        # By the door: a crate of instruments with a coil of wire on it, and a stool.
        *shaded("crate", rr(18, 11, 1.5, (-62, 46)), "$slate", [(48, 52, "$slate.dark")], stroke=INK_HAIR),
        P("crate_top", poly([(-71, 40.5), (-53, 40.5), (-54, 36.5), (-70, 36.5)]), "$slate.light", stroke=INK_HAIR),
        *wire_coil("coil", -63, 38.6),
        *stool("stool", 4, 51.5),
    ]
    doc(
        "ss.base.lab",
        "The lab",
        "A shed the expedition built out of the lander's plates to work in out of the wind: a riveted front with a patch and rust down its "
        "seams, a side going back into the dark, a single slope of corrugated roof. A jar of caps sits on the sill inside, so its window is "
        "lit a little. Readings are pinned up by the door, which is a canvas flap tied back; a crate of instruments with a coil of wire and "
        "a stool stand outside. A mast on the roof carries the wind meter (`ss.base.vane`), and a cable runs down the side toward the bench. "
        "Nothing to do here in feelers; it is the back of the east wing.",
        (176, 150),
        parts,
    )


def vane():
    # The rotor faces the camp, so its turning reads as turning: three
    # broad blades round a hub, a tail fin behind to keep it into the wind.
    hub = (0, -10)
    blades = []
    for i, a in enumerate([90, 210, 330]):
        t = math.radians(a)
        c, s_ = math.cos(t), math.sin(t)
        pts = [(1.2, -1.2), (6, -2.6), (10, -1.8), (11, 0), (10, 1.4), (6, 2.2), (1.2, 1.2)]
        blades.append(P(f"blade_{i}", poly([(x * c - y * s_, x * s_ + y * c) for x, y in pts]), "$steel.light", at=hub, stroke=INK_HAIR))
    parts = [
        P("pole", R(2, 16, 0.6), "$steel.dark", at=(0, 6), stroke=INK_HAIR),
        P("tail_arm", R(9, 1.4, 0.5), "$steel.dark", at=(5, -9)),
        P("tail", poly([(8, -9), (13, -14), (14, -6)]), "$frost.dark", stroke=INK_HAIR),
        P("body", ell(3.4, 3), "$steel", at=(0, -9.4), stroke=INK_HAIR),
        *blades,
        P("hub", circ(1.8), "$slate.dark", at=hub, stroke=INK_HAIR),
        P("hub_lit", circ(0.6), "$white@0.6", at=(-0.5, -10.5)),
    ]
    doc(
        "ss.base.vane",
        "Wind meter",
        "A three-bladed wind meter on the lab's mast, its rotor facing the camp and a cold tail fin keeping it into the wind; it turns "
        "(`spin`). The only thing in the camp that moves all the time by itself, and it is small.",
        (32, 48),
        parts,
        {"spin": loop("the blades turn in the wind", 1.2, [track(f"blade_{i}", "rot", [(0, 0), (1, 360)]) for i in range(3)])},
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
        "A rolled sleeping bag in cold slate, set down by a crate: its end shows the roll's spiral, the lining between the wraps; two straps are "
        "buckled round it, their tails loose, and a carry loop rides between them. Somebody sleeps in this camp between expeditions.",
        (44, 20),
        [
            *bedroll("roll", 0, 7),
        ],
    )
    doc(
        "ss.base.saw",
        "The saw",
        "The saw from the base inventory (A055). It cut the spire whose rings gave the vermin's passings away (A030), and it lies by the "
        "stumps it made.",
        (38, 16),
        [
            *saw("saw", -0.6, 0, s=0.97),
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
    marker()
    board()
    lamps()
    locker()
    keeps()
    stump()
    cairn()
    prints()
    post()
    larder()
    cellar()
    lab()
    vane()
    clutter()
    print("wrote the base")
