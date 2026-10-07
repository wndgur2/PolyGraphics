"""The ground behind the pages — what is buried in it.

    python3 scripts/menu_ground.py     # rewrites apps/ss/assets/ss-env-menu.json in place

`ss.env.menu` is packed earth seen from within, under the codex, the shop and
the settings at a dim of 0.55. Its bands and seams are hand-drawn and stay so;
what this adds is what earth that deep holds, drawn into the bands so a page
has something under it besides a gradient: stones with a lit chip, shed
chitin lying along the bedding, root channels threading down, crystals of the
signal grown along the seams it bleeds through, and grain. The middle band
stays the quietest because the page sits there (the document says so), so the
buried things gather at the top and bottom thirds. Idempotent: everything this
adds is prefixed `d_` and stripped before it is added again.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import r2, write_doc  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-env-menu.json")
doc = json.load(open(PATH))
parts = [p for p in doc["parts"] if not p["id"].startswith("d_")]


def ell(id, x, y, rx, ry, fill, rot=None):
    p = {"id": id, "at": [r2(x), r2(y)], "shape": {"kind": "ellipse", "rx": r2(rx), "ry": r2(ry)}, "fill": fill}
    if rot: p["rot"] = r2(rot)
    return p


def box(id, x, y, w, h, fill, rot=None):
    p = {"id": id, "at": [r2(x), r2(y)], "shape": {"kind": "rect", "w": r2(w), "h": r2(h)}, "fill": fill}
    if rot: p["rot"] = r2(rot)
    return p


def thread(id, pts, w, fill):
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    local = [(x - cx, y - cy) for x, y in pts]
    top, bot = [], []
    for i, (x, y) in enumerate(local):
        a = local[max(0, i - 1)]
        b = local[min(len(local) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n * w / 2, dx / n * w / 2
        top.append((x + nx, y + ny))
        bot.append((x - nx, y - ny))
    return {"id": id, "at": [r2(cx), r2(cy)], "shape": {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in top + bot[::-1]]}, "fill": fill}


added = []
# Stones, bedded along the bands: dark, with the dark under them and one chip of light. Top and bottom thirds.
stones = [(-520, -300, 26, 14, 8), (-310, -262, 16, 9, -12), (120, -318, 20, 11, 4), (430, -270, 30, 15, -6), (590, -330, 14, 8, 10),
          (-580, 212, 22, 12, -8), (-260, 300, 30, 16, 5), (60, 318, 18, 10, -14), (330, 236, 24, 13, 9), (560, 300, 16, 9, -4),
          (-470, -170, 12, 7, 0), (480, -150, 14, 8, 12), (-120, 250, 11, 6, -20), (200, 286, 13, 7, 16)]
for i, (x, y, rx, ry, rot) in enumerate(stones):
    added.append(ell(f"d_stone{i}_sh", x + 2, y + 3, rx, ry, "$ink@0.45", rot))
    added.append(ell(f"d_stone{i}", x, y, rx, ry, "$ink@0.55", rot))
    added.append(ell(f"d_stone{i}_face", x - rx * 0.1, y - ry * 0.3, rx * 0.7, ry * 0.5, "$coal@0.5", rot))
    added.append(ell(f"d_stone{i}_lit", x - rx * 0.4, y - ry * 0.45, rx * 0.22, ry * 0.3, "$smoke@0.3", rot))
# Shed chitin lying along the bedding: amber slivers, the hive's material with no signal in it.
chitin = [(-400, -236, 22, 6, -4), (260, -290, 18, 5, 6), (-30, -250, 14, 4, -10), (540, -210, 16, 5, 3),
          (-500, 262, 20, 6, 5), (-150, 300, 16, 5, -6), (420, 320, 24, 7, 2), (180, 240, 12, 4, 12), (-640, -330, 14, 4, -8)]
for i, (x, y, w, h, rot) in enumerate(chitin):
    added.append(box(f"d_chitin{i}_sh", x + 1.5, y + 2, w, h, "$ink@0.4", rot))
    added.append(box(f"d_chitin{i}", x, y, w, h, "$chitin.dark@0.32", rot))
    added.append(box(f"d_chitin{i}_lit", x - w * 0.15, y - h * 0.35, w * 0.6, h * 0.3, "$chitin@0.22", rot))
# Root channels threading down from the top, forking, the old way the signal travels.
roots = [[(-560, -360), (-540, -300), (-548, -240), (-520, -190)], [(-540, -300), (-510, -280), (-490, -250)],
         [(40, -360), (60, -320), (52, -270), (80, -230), (76, -180)], [(52, -270), (20, -250), (10, -220)],
         [(620, -360), (600, -310), (612, -260), (590, -220)],
         [(-300, 180), (-320, 230), (-300, 280), (-330, 340)], [(360, 170), (380, 220), (366, 270), (390, 330)], [(380, 220), (410, 236), (430, 262)]]
for i, pts in enumerate(roots):
    added.append(thread(f"d_root{i}", pts, 2.2 if i % 3 else 3.0, "$timber@0.14"))
    added.append(thread(f"d_root{i}_dark", [(x + 1, y + 1) for x, y in pts], 1.0, "$ink@0.22"))
# Crystals of the signal grown along the seams: small, pink, few.
crystals = [(-450, -214, 1.0), (-180, -200, 0.8), (210, -212, 1.1), (470, -196, 0.7), (-320, 142, 0.8), (90, 150, 1.0), (520, 136, 0.9), (-60, 262, 0.7), (300, 270, 0.9)]
for i, (x, y, s) in enumerate(crystals):
    added.append({"id": f"d_crystal{i}", "at": [r2(x), r2(y)], "shape": {"kind": "poly", "points": [[r2(-3 * s), r2(2 * s)], [r2(0), r2(-5 * s)], [r2(3 * s), r2(2 * s)]]}, "fill": "$pheromone@0.35"})
    added.append({"id": f"d_crystal{i}_lit", "at": [r2(x - 0.8 * s), r2(y - 0.6 * s)], "shape": {"kind": "poly", "points": [[r2(-1.2 * s), r2(1 * s)], [r2(0), r2(-2.6 * s)], [r2(0.6 * s), r2(0.8 * s)]]}, "fill": "$pheromone.light2@0.5"})
# Grain: two passes over the whole ground, under everything added, too fine to read as marks.
grain = [{"id": "d_grain_dark", "repeat": {"of": {"kind": "rect", "w": 1.6, "h": 1.6}, "count": 256, "area": [1280, 720], "seed": 9101, "jitterRot": True, "scaleRange": [0.6, 1.4]}, "fill": "$ink@0.3"},
         {"id": "d_grain_pale", "repeat": {"of": {"kind": "rect", "w": 1.4, "h": 1.4}, "count": 220, "area": [1280, 720], "seed": 9102, "jitterRot": True, "scaleRange": [0.6, 1.3]}, "fill": "$rust.light@0.14"}]

# Order: grain and buried things go in after the bands and before the pools, motes and the press.
idx = next(i for i, p in enumerate(parts) if p["id"] == "pool_a")
doc["parts"] = parts[:idx] + grain + added + parts[idx:]
if "scripts/menu_ground.py" not in doc["description"]:
    doc["description"] += (" What that earth holds is drawn into the bands by scripts/menu_ground.py over the hand-drawn layers: stones with the dark "
                           "under them and one chip of light, shed chitin lying along the bedding, root channels threading down and forking, "
                           "crystals of the signal grown along the seams, and grain — gathered in the top and bottom thirds, so the middle stays quiet under the page.")
write_doc(doc, PATH)
print(f"{len(doc['parts'])} parts -> {os.path.relpath(PATH)}")
