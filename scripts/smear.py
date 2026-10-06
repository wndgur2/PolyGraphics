"""Cowboy's smear (`ss.fx.smear`), the kit the whip's swing is drawn from.

    python3 scripts/smear.py        # rewrites apps/ss/assets/ss-fx-smear.json

The game does not stamp this document. Where the rope is at each moment is
gameplay — feelers `game/whipSwing.ts`, which the hits are tested against —
and the trail has to fade smoothly, which an adapter (drawing a gradient as
its flat mid-colour) cannot, so feelers draws the swing itself (WeaponSystem
`drawSwing`) from what this document holds:

- `meta` — in document units at `authoredR` (the reach: where the tip runs):
  `trail` (how long the trail lingers, as a share of a swing), `fillAlpha`
  (the swept ground, newest and at the tip), `rimLead`/`rimTail` (the tip's
  path, its width at the tip now and at the oldest), `inkPad` (ink showing
  either side of a line), `lashInner`/`lashTip` (the rope's width at the hand
  and at the tip);
- the colours, off the first part of each family: `fill_00`, `ink_rim_00`,
  `rim_00` (the tip's path, newest), `rim_tail_00` (oldest), `ink_lash`,
  `lash`.

The parts are one moment of a forehand swing, drawn by the same rules, so the
gallery shows what the game draws: the rope curling back from the hand, the
ground it has just swept behind it, the tip's path along the reach. At k = 0
now and 1 at the oldest of the trail: fill alpha `fillAlpha·(1-k)²`, heavier
out towards the tip (`0.25 + 0.75·u`, u along the rope); the tip's path alpha
`1-k²`, its width from `rimLead` to `rimTail` and colour from `rim` to
`rim_tail`, both straight along k.

The swing below is a copy of whipSwing.ts for this picture only; the game's
is the one that counts.
"""
import json, math, os

PATH = os.path.join(os.path.dirname(__file__), "..", "apps", "ss", "assets", "ss-fx-smear.json")

R = 56
META = {
    "authoredR": R,
    "trail": 0.4,
    "fillAlpha": 0.32,
    "rimLead": 2.6,
    "rimTail": 0.7,
    "inkPad": 1.1,
    "lashInner": 2.6,
    "lashTip": 0.9,
}

# feelers game/whipSwing.ts, for the picture
SPAN, LAG, CURL_POW, HAND = math.pi * 0.8, math.pi / 4, 2, 0.16
NOW = 0.8          # the moment drawn: most of the way round, the rope still curled
STEPS, POINTS = 8, 9


def swing_angle(u, t):
    hand = LAG + SPAN * (1 - math.cos(math.pi * t)) / 2
    return hand - LAG * u ** CURL_POW


BASE = -(SPAN + LAG)  # facing 0°, forehand: round from behind, the hand ending on the facing


def rope(u, t):
    rho = R * (HAND + u * (1 - HAND))
    a = BASE + swing_angle(u, t)
    return rho * math.cos(a), rho * math.sin(a)


r2 = lambda x: round(x, 2)
pts = lambda ps: [[r2(x), r2(y)] for x, y in ps]


def part(id_, ps, fill):
    return {"id": id_, "shape": {"kind": "poly", "points": pts(ps)}, "fill": fill}


def alpha(token, a):
    return f"{token}@{round(a, 3)}" if a < 0.999 else token


m = META
times = [max(0, NOW - m["trail"] * k / STEPS) for k in range(STEPS + 1)]
grid = [[rope(j / (POINTS - 1), t) for j in range(POINTS)] for t in times]
pad = m["inkPad"]

fills = []
for k in range(STEPS):
    kk = (k + 0.5) / STEPS
    for j in range(POINTS - 1):
        u = (j + 0.5) / (POINTS - 1)
        a = m["fillAlpha"] * (1 - kk) ** 2 * (0.25 + 0.75 * u)
        quad = [grid[k][j], grid[k][j + 1], grid[k + 1][j + 1], grid[k + 1][j]]
        fills.append(part(f"fill_{k * (POINTS - 1) + j:02d}", quad, alpha("$frost.light", a)))


def tip_slice(k, outer, w0, w1):
    a0 = math.atan2(grid[k][-1][1], grid[k][-1][0])
    a1 = math.atan2(grid[k + 1][-1][1], grid[k + 1][-1][0])
    n = 4
    o, i = [], []
    for s in range(n + 1):
        f = s / n
        a = a0 + (a1 - a0) * f
        w = w0 + (w1 - w0) * f
        o.append((outer * math.cos(a), outer * math.sin(a)))
        i.append(((outer - w) * math.cos(a), (outer - w) * math.sin(a)))
    return o + i[::-1]


inks, tails, rims = [], [], []
w = lambda k: m["rimLead"] + (m["rimTail"] - m["rimLead"]) * k
for k in range(STEPS):
    k0, k1 = k / STEPS, (k + 1) / STEPS
    km = (k0 + k1) / 2
    edge = 1 - km * km
    inks.append(part(f"ink_rim_{k:02d}", tip_slice(k, R, w(k0) + 2 * pad, w(k1) + 2 * pad), alpha("$ink", edge)))
    # The colour runs from `rim` to `rim_tail` along k: the tail colour under,
    # the lead colour over it fading out.
    tails.append(part(f"rim_tail_{k:02d}", tip_slice(k, R - pad, w(k0), w(k1)), alpha("$frost", edge)))
    rims.append(part(f"rim_{k:02d}", tip_slice(k, R - pad, w(k0), w(k1)), alpha("$silent", edge * (1 - km))))


def ribbon(w0, w1):
    line = grid[0]
    left, right = [], []
    for j, (x, y) in enumerate(line):
        ax, ay = line[max(0, j - 1)]
        bx, by = line[min(len(line) - 1, j + 1)]
        nx, ny = -(by - ay), bx - ax
        d = math.hypot(nx, ny) or 1
        h = (w0 + (w1 - w0) * j / (len(line) - 1)) / 2
        left.append((x + nx / d * h, y + ny / d * h))
        right.append((x - nx / d * h, y - ny / d * h))
    return left + right[::-1]


lash = [
    part("ink_lash", ribbon(m["lashInner"] + 2 * pad, m["lashTip"] + 2 * pad), "$ink"),
    part("lash", ribbon(m["lashInner"], m["lashTip"]), "$silent"),
]

doc = {
    "id": "ss.fx.smear",
    "name": "Smear",
    "description": (
        "A whirled feeler's swing — Cowboy (ss.char.arin `cast_evo`): round from behind to the facing, the rope curled "
        "back behind the hand the whole way, no crack and no straightening; where the hand stops it stops, still "
        "bent, and fades. Drawn at one moment of a forehand: the "
        "rope, thick at the hand and fine at the tip, on ink; the ground it has just swept, a cold fill fading "
        "smoothly behind it and heavier towards the tip, where it sweeps furthest; and the tip's path on `authoredR`, "
        "the reach, fading the same way. The one kit that does not let go in held steps, since a stepped trail on "
        "a sweep this size reads as bands rather than speed. The game draws it itself from `meta` and the colours "
        "of the first part of each family (scripts/smear.py says which), wherever its swing puts the rope."
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
