"""What a field record was written on, where it was not paper.

    python3 scripts/record_media.py    # adds the media states to apps/ss/assets/ss-pickup-record.json

Every record in feelers lay on the field as the same sheet of paper, and for
the expeditions' logs that is right: paper is the one thing on the field with
no smell, which is why it survives. The settlers' pages are not paper. They
were cut into the lander's hull, scratched onto chitin plates and carved into
stone — the game says so in each record's `medium` line — and then the page
lying on the floor was a sheet of paper anyway. These are those three objects,
as states of the same document so they lie at the paper's size and in its
oblique view (ellipses at half height, the body's shadow down and right):

  plate   a plate of shed chitin, a shallow shield with its growth ridges,
          rows of short scratches across it where a hand wrote on it
  stone   a slab with a top face and a front edge, three lines carved into it,
          one corner knocked off
  hull    a torn shard of the lander's skin, two rivets still in it, the
          writing scratched bright into the paint, a run of rust

Each keeps the paper's halo, and its soil and grit are laid back over the
object, so they sit on the ground the same way. The paper's own parts go (`remove`), which leaves the `stir` clip with
only the halo to move — a plate does not lift in the wind.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import poly, ell, circ, INK_THIN, INK_HAIR, write_doc
import json

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "apps", "ss", "assets", "ss-pickup-record.json")

KEEP = {"halo"}
# Laid back over the object once it is drawn: the ground is on top of whatever the page is.
GROUND = ("soil", "grit")
SHADOW = (0.9, 0.8)


def part(pid, shape, fill, at=None, stroke=None, rot=None):
    p = {"id": pid}
    if at is not None:
        p["at"] = [round(at[0], 2), round(at[1], 2)]
    if rot is not None:
        p["rot"] = rot
    p["shape"] = shape
    p["fill"] = fill
    if stroke is not None:
        p["stroke"] = stroke
    return p


def shift(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def oval(rx, ry, n=18, wobble=(), start=0.0):
    """An ellipse as a polygon, each point pushed out by its entry in `wobble`."""
    pts = []
    for i in range(n):
        a = start + 2 * math.pi * i / n
        k = 1 + (wobble[i] if i < len(wobble) else 0)
        pts.append((math.cos(a) * rx * k, math.sin(a) * ry * k))
    return pts


def dashes(prefix, rows, fill, h=0.55):
    """Short strokes laid in rows: (y, [(x0, x1), ...]) — writing, at this size."""
    out = []
    for r, (y, runs) in enumerate(rows):
        for c, (x0, x1) in enumerate(runs):
            out.append(part(f"{prefix}_{r}_{c}", poly([(x0, y - h / 2), (x1, y - h / 2 - 0.12), (x1, y + h / 2 - 0.12), (x0, y + h / 2)]), fill))
    return out


# ================================================================ plate
def plate():
    # A wing case: the straight edge along the top is where it met its twin,
    # rounded at the base on the left and drawn to a point on the right.
    body = [(-8.6, -3.6), (-4.0, -4.4), (1.0, -4.8), (5.6, -4.6), (9.6, -3.4), (7.8, -0.6), (4.6, 2.4), (0.6, 4.4),
            (-4.0, 5.0), (-7.6, 3.8), (-9.4, 1.0), (-9.6, -1.8)]
    lit = [(-8.8, -1.6), (-8.4, -3.2), (-4.0, -4.0), (1.0, -4.4), (5.6, -4.2), (8.6, -3.3), (4.6, -2.6), (-0.4, -2.0), (-4.8, -1.0), (-7.6, 0.6)]
    seam = [(-8.6, -3.6), (-4.0, -4.4), (1.0, -4.8), (5.6, -4.6), (9.6, -3.4), (5.6, -3.9), (1.0, -4.1), (-4.0, -3.7), (-8.4, -2.9)]

    # Striae: the grooves that run the length of a wing case, base to tip.
    def stria(pid, pts, fill):
        under = [(x, y + 0.45) for x, y in reversed(pts)]
        return part(pid, poly(pts + under), fill)
    striae = [
        stria("stria_0", [(-8.4, 0.4), (-4.0, -1.2), (1.0, -2.0), (5.6, -2.4), (8.4, -2.6)], "$chitin.dark2@0.75"),
        stria("stria_1", [(-7.6, 2.8), (-3.6, 2.6), (0.8, 1.6), (4.6, 0.0), (7.0, -1.4)], "$chitin.dark2@0.75"),
    ]
    # Words cut into it show pale, the way a scratch on a beetle's back does.
    hand = dashes("mark", [
        (-0.6, [(-6.0, -3.6), (-3.0, -0.6), (0.0, 2.8), (3.6, 5.4)]),
        (1.3, [(-6.4, -3.0), (-2.4, 0.6), (1.4, 4.2)]),
        (3.1, [(-5.0, -2.2), (-1.4, 1.0)]),
    ], "$bone@0.8")
    return {
        "description": (
            "Written on chitin, as most of the settlers' pages were: one wing case of something large, its seam edge "
            "along the top and its grooves running base to tip, and rows of pale scratches where a hand cut the words "
            "into its back."
        ),
        "remove": REMOVE,
        "add": [
            part("m_shadow", poly(shift(body, *SHADOW)), "$ink@0.4"),
            part("m_body", poly(body), "$chitin.dark", stroke=INK_THIN),
            part("m_lit", poly(lit), "$chitin"),
            *striae,
            part("m_seam", poly(seam), "$chitin.light"),
            *hand,
            part("m_gloss", ell(2.2, 0.5), "$white@0.5", at=(-4.6, -2.9), rot=-8),
        ],
    }


# ================================================================ stone
def stone():
    # A slab seen from above and a little in front: a top face, and the front
    # edge under it. One corner (the far right) knocked off.
    top = [(-9.2, -4.2), (5.6, -5.0), (7.4, -3.6), (8.6, 1.6), (-8.4, 2.6)]
    front = [(-8.4, 2.6), (8.6, 1.6), (8.4, 4.4), (-8.2, 5.4)]
    whole = [(-9.2, -4.2), (5.6, -5.0), (7.4, -3.6), (8.6, 1.6), (8.4, 4.4), (-8.2, 5.4), (-8.4, 2.6)]
    chip = [(5.6, -5.0), (7.4, -3.6), (6.0, -3.4)]
    carved = []
    for i, (y, x0, x1) in enumerate([(-2.6, -7.0, 5.2), (-0.6, -7.2, 6.4), (1.2, -7.0, 2.0)]):
        carved.append(part(f"cut_{i}", poly([(x0, y - 0.35), (x1, y - 0.55), (x1, y + 0.15), (x0, y + 0.35)]), "$slate.dark2"))
        carved.append(part(f"cut_{i}_lit", poly([(x0, y + 0.35), (x1, y + 0.15), (x1, y + 0.5), (x0, y + 0.7)]), "$white@0.4"))
    return {
        "description": (
            "Cut into stone, as the settlers' first and last pages were: a slab with a top face and a front edge, three "
            "lines carved across it and a corner knocked off. Heavier than anything else on the field that is not alive."
        ),
        "remove": REMOVE,
        "add": [
            part("m_shadow", poly(shift(whole, *SHADOW)), "$ink@0.4"),
            part("m_body", poly(whole), "$slate", stroke=INK_THIN),
            part("m_top", poly(top), "$slate.light"),
            part("m_front", poly(front), "$slate"),
            part("m_chip", poly(chip), "$white@0.55"),
            part("m_edge", poly([(-8.4, 2.6), (8.6, 1.6), (8.6, 2.1), (-8.4, 3.1)]), "$white@0.35"),
            *carved,
            part("m_pit_0", circ(0.5), "$slate.dark2", at=(-3.2, -3.8)),
            part("m_pit_1", circ(0.35), "$slate.dark2", at=(4.2, 0.9)),
        ],
    }


# ================================================================ hull
def hull():
    shard = [(-9.6, -2.6), (-6.4, -5.2), (-1.8, -4.4), (1.2, -6.0), (5.4, -4.6), (9.2, -5.4), (8.0, -1.0), (9.0, 2.6), (4.4, 4.8), (-2.6, 5.6), (-5.0, 3.6), (-8.8, 4.4), (-7.4, 0.6)]
    lit = [(-8.6, -2.4), (-6.2, -4.4), (-1.8, -3.6), (1.2, -5.2), (5.4, -3.8), (8.2, -4.4), (5.2, -3.0), (1.0, -3.6), (-2.0, -2.6), (-6.0, -3.2)]
    paint = [(-6.0, -1.8), (5.6, -2.6), (6.4, 2.2), (-5.4, 3.2)]
    scratch = dashes("scratch", [
        (-1.0, [(-5.0, -2.4), (-1.8, 1.2), (1.8, 4.8)]),
        (0.8, [(-4.8, -1.0), (-0.4, 2.8), (3.4, 5.4)]),
        (2.4, [(-4.6, -2.2), (-1.4, 0.4)]),
    ], "$white@0.7", h=0.45)
    return {
        "description": (
            "Scratched into the lander's hull, the settlers' first page: a torn shard of its skin, two rivets still in it, "
            "the words cut bright through the paint, rust running from the tear."
        ),
        "remove": REMOVE,
        "add": [
            part("m_shadow", poly(shift(shard, *SHADOW)), "$ink@0.4"),
            part("m_body", poly(shard), "$steel.dark", stroke=INK_THIN),
            part("m_lit", poly(lit), "$steel"),
            part("m_paint", poly(paint), "$verdigris.dark@0.85"),
            *scratch,
            part("m_rust", poly([(4.4, 4.8), (9.0, 2.6), (8.0, -1.0), (6.8, 1.6), (4.0, 3.4)]), "$rust@0.7"),
            part("m_rivet_0", circ(0.6), "$steel.light", at=(-7.6, -2.2), stroke=INK_HAIR),
            part("m_rivet_1", circ(0.6), "$steel.light", at=(7.2, -3.8), stroke=INK_HAIR),
        ],
    }


if __name__ == "__main__":
    doc = json.load(open(PATH))
    REMOVE = [p["id"] for p in doc["parts"] if p["id"] not in KEEP]
    ground = [p for p in doc["parts"] if p["id"] in GROUND]
    doc["variants"] = {"plate": plate(), "stone": stone(), "hull": hull()}
    for v in doc["variants"].values():
        v["add"] += ground
        v["animations"] = ["stir"]
    write_doc(doc, PATH)
    print("wrote", os.path.relpath(PATH))
