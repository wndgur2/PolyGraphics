"""The great feeler at the base's edges — detail on the silhouette, in each segment's own frame.

    python3 scripts/antenna.py     # rewrites apps/ss/assets/ss-env-antenna.json in place

`ss.env.antenna` was eleven flat segments of `$dead`, and at the base it stood
at the edge of the camp as a dark mass with no inside: the one enormous thing
in the scene, and the one with nothing drawn on it. It stays a silhouette and
stays unlit (an antenna only ever receives, guide §7.2), but a silhouette can
have form: a joint ring where one segment sits in the next, a band a shade
lighter down the side that faces the camp's light, and setae — the short stiff
hairs an insect's antenna carries — along the outer edge. All of it is dark on
dark, a few values apart, the way the hearth's light would find the edges of a
thing standing just outside it. The base draws an additive sheen copy of the
rig over it, which is what lifts these edges into view.

Every segment is a rig part with its own rotation track in the three clips,
so what is added to a segment is placed at the segment's own origin with its
geometry in the segment's frame, and given the segment's tracks verbatim: the
joint, the band and the hairs turn with the segment they are on. Idempotent —
parts and tracks this script added are stripped before it adds them again — so
the hand-drawn segments and their clips are the source and stay so.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import r2, write_doc  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "ss", "assets", "ss-env-antenna.json")
ADDED = ("_joint", "_band", "_seta")

doc = json.load(open(PATH))
segs = [p for p in doc["parts"] if not p["id"].endswith(ADDED) and "_seta" not in p["id"]]
for a in doc["animations"].values():
    a["tracks"] = [t for t in a["tracks"] if not (t["part"].endswith(ADDED) or "_seta" in t["part"])]


def along(pts, i, j, t):
    return (pts[i][0] + (pts[j][0] - pts[i][0]) * t, pts[i][1] + (pts[j][1] - pts[i][1]) * t)


def inset(pts, k):
    """The polygon's left side (its first seven points, root to tip) pulled in toward the right side by `k`."""
    left, right = pts[:7], pts[7:][::-1]
    out = []
    for (lx, ly), (rx, ry) in zip(left, right):
        dx, dy = rx - lx, ry - ly
        n = math.hypot(dx, dy) or 1
        out.append((lx + dx / n * k, ly + dy / n * k))
    return out


new_parts = []
for s in segs:
    pts = [tuple(p) for p in s["shape"]["points"]]
    at = s.get("at", [0, 0])
    sid = s["id"]
    left, right = pts[:7], pts[7:][::-1]
    # The band: a strip just inside the left (camp-facing) edge, a shade lighter, fading before the tip.
    outer = inset(pts, 1.6)[:6]
    inner = inset(pts, 7.5)[:6]
    band = outer + inner[::-1]
    new_parts.append({"id": f"{sid}_band", "at": at, "shape": {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in band]}, "fill": "$dead.light2@0.5"})
    # The joint: a dark ring across the root of the segment, where it sits in the one below.
    lx, ly = left[0]
    rx, ry = right[0]
    cx, cy = (lx + rx) / 2, (ly + ry) / 2
    w = math.hypot(rx - lx, ry - ly)
    ang = math.degrees(math.atan2(ry - ly, rx - lx))
    new_parts.append({"id": f"{sid}_joint", "at": [r2(cx), r2(cy)], "rot": r2(ang),
                      "shape": {"kind": "ellipse", "rx": r2(w * 0.5), "ry": r2(max(2.0, w * 0.085))}, "fill": "$ink@0.7"})
    # Setae: three stiff hairs off the outer (right) edge, leaning toward the tip.
    for k, t in enumerate((0.25, 0.55, 0.82)):
        i = int(t * 6)
        bx, by = along(right, i, i + 1, t * 6 - i)
        nx, ny = along(right, i, i + 1, min(1, t * 6 - i + 0.3))
        dx, dy = nx - bx, ny - by
        n = math.hypot(dx, dy) or 1
        dx, dy = dx / n, dy / n
        ox, oy = dy, -dx  # outward normal (right side, away from the left edge)
        if (ox * (bx - cx) + oy * (by - cy)) < 0: ox, oy = -ox, -oy
        L = 7 + k * 1.5
        tip = (bx + ox * L * 0.8 + dx * L * 0.6, by + oy * L * 0.8 + dy * L * 0.6)
        base_a = (bx + dx * 1.2, by + dy * 1.2)
        base_b = (bx - dx * 1.2, by - dy * 1.2)
        new_parts.append({"id": f"{sid}_seta{k}", "at": at, "shape": {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in (base_a, tip, base_b)]}, "fill": "$dead.light@0.75"})
    for a in doc["animations"].values():
        for t in a["tracks"]:
            if t["part"] == sid:
                for np_ in new_parts:
                    if np_["id"].startswith(sid + "_") and not any(x["part"] == np_["id"] for x in a["tracks"]):
                        a["tracks"].append({**t, "part": np_["id"]})

# Draw order: segments root to tip as before, each segment's details right after it, so the
# next segment's root covers the joint ring of the one it sits on only where it should.
parts = []
for s in segs:
    parts.append(s)
    parts += [p for p in new_parts if p["id"].startswith(s["id"] + "_")]
doc["parts"] = parts
if "Generated by scripts/antenna.py" not in doc["description"]:
    doc["description"] += (" Its segments carry a joint ring where each sits in the next, a band a shade lighter down the side that faces "
                           "the camp, and three setae off the outer edge, all dark on dark and placed in the segment's own frame with the "
                           "segment's tracks, so they turn with it. Detail by scripts/antenna.py over the hand-drawn segments.")
write_doc(doc, PATH)
print(f"{len(parts)} parts, {sum(len(a['tracks']) for a in doc['animations'].values())} tracks -> {os.path.relpath(PATH)}")
