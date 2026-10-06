"""Cowboy's smear (`ss.fx.smear`), the kit the whip's full turn is drawn from.

    python3 scripts/smear.py        # rewrites apps/ss/assets/ss-fx-smear.json

The game does not stamp this document. A turn's trail has to fade smoothly
along its length and stop exactly where the lash has been, and an adapter
draws a gradient as its flat mid-colour, so feelers draws the sector itself
(WeaponSystem `drawSmear`) from what this document holds:

- `meta` — the shape, in document units at `authoredR` (the reach: the rim's
  outer edge): `inner` (the lash starts clear of the body; the fill runs in
  to the centre, under it), `trail` (degrees
  of tail behind the lead), `fillAlpha`, `rimLead`/`rimTail` (the rim's width
  at the lead and at the end of the tail), `inkPad` (ink showing either side
  of the rim and the lash), `lashInner`/`lashTip` (the lash's width at the
  body and at the rim);
- the colours, off the first part of each family: `fill_00`, `ink_rim_00`,
  `rim_00` (the rim at the lead), `rim_tail_00` (the rim at the end of the
  tail), `ink_lash`, `lash`.

The parts themselves are the same drawing in fine slices, so the gallery shows
what the game draws. Both follow one taper, at k = 0 on the lead and 1 where
the trail ends (the game's trail is never longer than the ground the lash has
crossed, so early in a turn k runs over less than `trail`): fill alpha `fillAlpha·(1-k)²`, rim and ink alpha `1-k²`,
rim width from `rimLead` to `rimTail` and colour from `rim` to `rim_tail`,
both straight along k.
"""
import json, math, os

PATH = os.path.join(os.path.dirname(__file__), "..", "apps", "ss", "assets", "ss-fx-smear.json")

R = 56
META = {
    "authoredR": R,
    "inner": 9,
    "trail": 120,
    "fillAlpha": 0.3,
    "rimLead": 3,
    "rimTail": 0.8,
    "inkPad": 1.1,
    "lashInner": 1,
    "lashTip": 2.4,
}
SLICES = 20  # the gallery's picture only; the game's trail is continuous

r2 = lambda x: round(x, 2)


def slice_(r, a0, a1):
    """A slice of the disc as a polygon (degrees, anticlockwise is negative)."""
    n = max(1, math.ceil(abs(a1 - a0) / 3))
    arc = [(r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    return [[r2(x), r2(y)] for x, y in [(0, 0)] + arc]


def tapered(r1, a0, a1, w0, w1):
    """A slice of the rim, its outer edge on r1, its width w0 at a0 going to w1 at a1."""
    n =max(1, math.ceil(abs(a1 - a0) / 3))
    outer, inner = [], []
    for i in range(n + 1):
        f = i / n
        a = math.radians(a0 + (a1 - a0) * f)
        w = w0 + (w1 - w0) * f
        outer.append((r1 * math.cos(a), r1 * math.sin(a)))
        inner.append(((r1 - w) * math.cos(a), (r1 - w) * math.sin(a)))
    return [[r2(x), r2(y)] for x, y in outer + inner[::-1]]


def part(id_, pts, fill):
    return {"id": id_, "shape": {"kind": "poly", "points": pts}, "fill": fill}


def alpha(token, a):
    return f"{token}@{round(a, 3)}" if a < 0.999 else token


m = META
step = m["trail"] / SLICES
pad = m["inkPad"]
fills, inks, tails, rims = [], [], [], []
for i in range(SLICES):
    k0, k1 = i / SLICES, (i + 1) / SLICES
    km = (k0 + k1) / 2
    a0, a1 = -i * step, -(i + 1) * step
    w = lambda k: m["rimLead"] + (m["rimTail"] - m["rimLead"]) * k
    edge = 1 - km * km
    fills.append(part(f"fill_{i:02d}", slice_(R - pad, a0, a1), alpha("$frost.light", m["fillAlpha"] * (1 - km) ** 2)))
    inks.append(part(f"ink_rim_{i:02d}", tapered(R, a0, a1, w(k0) + 2 * pad, w(k1) + 2 * pad), alpha("$ink", edge)))
    # The rim's colour runs from `rim` to `rim_tail` along k: the tail colour
    # under, the lead colour over it fading out.
    tails.append(part(f"rim_tail_{i:02d}", tapered(R - pad, a0, a1, w(k0), w(k1)), alpha("$frost", edge)))
    rims.append(part(f"rim_{i:02d}", tapered(R - pad, a0, a1, w(k0), w(k1)), alpha("$silent", edge * (1 - km))))

li, lt = m["lashInner"] / 2, m["lashTip"] / 2
lash = [
    part("ink_lash", [[m["inner"], -(li + pad)], [R, -(lt + pad)], [R, lt + pad], [m["inner"], li + pad]], "$ink"),
    part("lash", [[m["inner"] + pad, -li], [R - pad, -lt], [R - pad, lt], [m["inner"] + pad, li]], "$silent"),
]

doc = {
    "id": "ss.fx.smear",
    "name": "Smear",
    "description": (
        "The ground a whirled feeler sweeps — Cowboy's turn (ss.char.arin `cast_evo`). Its reach is the drawing's: "
        "the lash runs from the body out to the rim, the rim's outer edge sits on `authoredR`, and a cold fill covers "
        "everything between, because the turn cuts the whole disc and not a ring at its edge. The lead is at 0° and the "
        "tail trails back anticlockwise, fading smoothly to nothing along its length and with no edge round the body — the one kit that does not let go in held steps, "
        "since a stepped tail on a disc this size reads as bands rather than speed. The game draws it itself from "
        "`meta` and the colours of the first slice of each family (scripts/smear.py says which), continuous along the "
        "trail and only over ground the lash has crossed; these parts are the same drawing in slices, for the gallery."
    ),
    "tags": ["fx", "melee", "kit"],
    "size": [128, 128],
    "meta": m,
    "parts": fills + inks + tails + rims + lash,
}

with open(PATH, "w") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("wrote", os.path.relpath(PATH), len(doc["parts"]), "parts")
