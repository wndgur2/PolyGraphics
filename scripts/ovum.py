"""The Ovum — what the Matriarch lays, sitting on the floor until it hatches.

    python3 scripts/ovum.py           # rewrites apps/ss/assets/ss-enemy-ovum.json

feelers draws it (EnemySystem `dressEgg`, EGG_TEX 'e_ovum') in place of the
body that is going to stand up out of it, sized to that body (EGG_R 11 is this
shell's own radius, 10.5 by 12.5: keep it), for the `broodHatch` window. It
loops `rock` — faster the shorter the fight has made the window, and faster
again in the last 0.45s (`eggShake`) — and when the young stands up the shell
stays behind and plays its own `death`, which is the break, whether the body
hatched or was killed inside it.

The same egg as the seven in the Matriarch's chamber (scripts/matriarch.py):
a pale yellowed shell, her pink showing through its lower half, and a curled
grub in the pink, here carrying a lit organ, because what she lays now is
marked. It stands on a smear of jelly. Two pieces already — a cup and a cap
meeting along a zigzag crack round the upper third — and that is where it
opens.

On the rig (scripts/rig.py): the egg is a root that rocks about the point it
stands on and hops off the jelly; the cap is hinged at one end of the crack
so it lifts like a lid; the grub turns inside on its own bone; three shards
of shell ride the egg hidden until the break throws them.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import (Rig, R, D, r2, lerp, smooth, cyc, wrap, keyset, compose, invert_apply,
                 poly, ell, circ, INK_THIN, INK_HAIR, write_doc)

# ============================================================== rig
# Canvas 40×48, origin at the centre, seen side-on, standing on the floor near y = 11.
RIG = Rig()
bone = RIG.bone
BASE_PT = (0.0, 11.4)       # where the shell touches the jelly: what it rocks on
CENTRE = (0.0, -1.0)        # the shell's centre
SH_RX, SH_RY = 10.5, 12.5   # EGG_R in feelers reads this shell as radius 11
HINGE = (-9.9, -5.3)        # the left end of the crack: the cap lifts from here

bone("egg", None, BASE_PT, -90.0, 24.0)
bone("floor", None, (0.0, 10.6), 0.0)
bone("cap", "egg", HINGE, 0.0, 19.8)
bone("grub", "egg", (0.4, 2.4), 0.0, 4.0)
RIG.seal()
put = RIG.put

# ============================================================== parts
def shell_pt(th, s=1.0):
    return (CENTRE[0] + SH_RX * s * math.cos(R(th)), CENTRE[1] + SH_RY * s * math.sin(R(th)))
def local(pts, c): return [(x - c[0], y - c[1]) for x, y in pts]
# the crack: a zigzag across the shell a third of the way down, from the left
# end (the hinge) to the right
CRACK = [(-9.87, -5.28), (-7.2, -7.4), (-4.6, -5.4), (-1.8, -7.9), (1.0, -5.6), (3.9, -7.6), (6.6, -5.5), (9.87, -5.28)]
def crack_th(x, y): return D(math.atan2((y - CENTRE[1]) / SH_RY, (x - CENTRE[0]) / SH_RX))
TH_L, TH_R = crack_th(*CRACK[0]), crack_th(*CRACK[-1])      # ≈ -154, -26
CUP = [shell_pt(TH_R + (TH_L + 360.0 - TH_R) * i / 28) for i in range(29)] + list(CRACK[1:-1])
CAP = [shell_pt(TH_L + (TH_R - TH_L) * i / 20) for i in range(21)] + list(reversed(CRACK[1:-1]))

put("jelly", "floor", (0.0, 10.6), 0.0, ell(13.5, 4.2), "$pheromone.dark@soft")
put("jelly_sheen", "floor", (-4.2, 9.7), 0.0, ell(4.6, 1.2), "$pheromone.light@ghost")
# three shards of the rim, drawn under the shell so they are hidden until the break throws them
SHARDS = {"shard_a": ((-6.0, -6.0), [(-1.8, -1.2), (1.6, -1.6), (0.6, 1.4)], -20.0),
          "shard_b": ((1.0, -6.6), [(-1.4, -1.4), (1.8, -0.8), (-0.2, 1.6)], 10.0),
          "shard_c": ((7.2, -5.6), [(-1.6, -1.0), (1.4, -1.4), (0.8, 1.6)], 30.0)}
for sid, (at, pts, rot) in SHARDS.items():
    put(sid, "egg", at, rot, poly(pts), "$ochre.light2", INK_HAIR)
put("cup", "egg", CENTRE, 0.0, poly(local(CUP, CENTRE)), "$ochre.light2", INK_THIN)
# the dark inside of the cup above the crack: under the cap, so it shows only
# when the cap lifts or goes
HOLLOW_C = (0.0, -7.6)
HOLLOW = list(CRACK) + [(9.0, -8.4), (5.0, -10.0), (0.0, -10.4), (-5.0, -10.0), (-9.0, -8.4)]
put("hollow", "egg", HOLLOW_C, 0.0, poly(local(HOLLOW, HOLLOW_C)), "$pheromone.dark2")
# her pink through the lower half of the shell, and the grub curled in it
put("albumen", "egg", (-0.4, 2.2), 0.0, ell(7.6, 7.8), "$pheromone.light@heavy")
put("embryo", "grub", (0.4, 2.4), -20.0, {"kind": "ring", "r": 4.1, "width": 2.8, "from": 40, "to": 290}, "$pheromone.dark")
put("embryo_head", "grub", (4.1, 0.6), 0.0, circ(1.9), "$pheromone.dark")
RIG.use("organ", "grub", (-3.0, 3.8), "ss.lib.organ", scale=[0.4, 0.4])
put("shade", "egg", CENTRE, 0.0, {"kind": "ring", "r": 9.3, "width": 2.0, "from": 20, "to": 160}, "$pheromone.light@soft")
CAP_C = (0.0, -9.2)   # the cap's own middle: it turns about this when it tumbles
put("cap", "cap", CAP_C, 0.0, poly(local(CAP, CAP_C)), "$ochre.light2", INK_THIN)
put("gloss", "cap", CAP_C, 0.0, poly(local([(-6.4, -7.6), (-5.2, -10.4), (-2.6, -11.8), (-3.4, -9.6), (-5.0, -7.9)], CAP_C)), "$white@soft")
RIG.check()

# ============================================================== motion
# A pose is the rig's (`body` moves the egg about the point it stands on), plus
# `k`: the shell's swell about its centre, which carries every part on the
# egg out from it and scales it.
def posed(pose, k=1.0):
    world = RIG.solve(pose)
    out = {}
    for p in RIG.parts:
        pid = p["id"]; bn = RIG.attach[pid]
        at, rot = tuple(p["at"]), p.get("rot", 0.0)
        sc = 1.0
        if bn != "floor":
            at = (CENTRE[0] + (at[0] - CENTRE[0]) * k, CENTRE[1] + (at[1] - CENTRE[1]) * k)
            sc = k
        # a bone's own frame is swollen with it: a child bone's start moves out too
        lx, ly, la = invert_apply(RIG.rest[bn], at, rot)
        x, y, a = compose(world[bn], (lx, ly, la))
        if bn in ("cap", "grub"):
            # the bone's start rides the swell like everything else
            bx, by, _ = RIG.rest[bn]
            ox, oy = CENTRE[0] + (bx - CENTRE[0]) * k - bx, CENTRE[1] + (by - CENTRE[1]) * k - by
            wx, wy, wa = world["egg"]
            c_, s_ = math.cos(R(wa + 90.0)), math.sin(R(wa + 90.0))
            x, y = x + ox * c_ - oy * s_, y + ox * s_ + oy * c_
        out[pid] = (x, y, a, sc)
    return out

REST = posed({})
STILL = {"embryo_head", "organ", "jelly", "jelly_sheen", "shade"}

def tracks(state_at, ts, scales=None, extra=None):
    series = {p["id"]: ([], [], [], []) for p in RIG.parts}
    for t in ts:
        pose, k = state_at(t)
        now = posed(pose, k)
        for pid, (x, y, a, sc) in now.items():
            bx, by, ba, bs = REST[pid]
            if scales and pid in scales: sc *= scales[pid](t)
            for arr, v in zip(series[pid], (x - bx, y - by, wrap(a - ba), sc / bs)):
                arr.append(v)
    out = []
    for p in RIG.parts:
        pid = p["id"]
        xs, ys, rs, ss = series[pid]
        for prop, vs, rv in (("x", xs, 0.0), ("y", ys, 0.0), ("rot", rs, 0.0), ("scale", ss, 1.0)):
            if prop == "rot" and pid in STILL: continue
            if max(abs(v - rv) for v in vs) > {"scale": 0.004, "rot": 0.2}.get(prop, 0.02):
                out.append({"part": pid, "prop": prop, "keys": [[r2(t), round(v, 3) if prop == "scale" else r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
    for pid, prop, fn in (extra or []):
        out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(fn(t))] for t in ts], "ease": "linear"})
    return out

def keyed(keys, t):
    """Smooth-stepped value through (time, value) keys."""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1: return lerp(v0, v1, smooth(t0, t1, t))
    return keys[-1][1]

# ============================================================== rock (1.0s loop)
# Something inside kicks: the egg is thrown up off the jelly and over to one
# side, rocks back and forth on the point it stands on, dying away, and
# settles; the cap lifts on its hinge with the kick and the crack gapes pink,
# then claps shut; the grub turns over inside a beat after, the organ in it
# swelling; the jelly squashes out as it lands. Then a held breath of a pulse
# until the next kick. The game plays it faster as the window runs out.
ROCK = [(0.0, 0.0), (0.09, 17.0), (0.22, -14.0), (0.35, 9.0), (0.47, -5.0), (0.58, 2.0), (0.68, 0.0), (1.0, 0.0)]
HOP = [(0.0, 0.0), (0.05, -3.2), (0.12, 0.4), (0.18, 0.0), (1.0, 0.0)]
SWELL = [(0.0, 1.0), (0.04, 1.07), (0.14, 0.96), (0.26, 1.02), (0.4, 1.0), (0.78, 1.0), (0.88, 1.03), (1.0, 1.0)]
LID = [(0.0, 0.0), (0.06, -22.0), (0.16, 4.0), (0.24, -9.0), (0.32, 0.0), (1.0, 0.0)]
TURN = [(0.0, 0.0), (0.12, 0.0), (0.26, -48.0), (0.42, 22.0), (0.58, -10.0), (0.72, 0.0), (1.0, 0.0)]
def rock_state(t):
    pose = {"body": (0.0, keyed(HOP, t), keyed(ROCK, t)), "cap": keyed(LID, t), "grub": keyed(TURN, t)}
    return pose, keyed(SWELL, t)
ROCK_SCALES = {"organ": lambda t: keyed([(0.0, 1.0), (0.18, 1.0), (0.3, 1.45), (0.55, 0.95), (0.8, 1.0), (1.0, 1.0)], t),
               "jelly": lambda t: keyed([(0.0, 1.0), (0.05, 0.96), (0.14, 1.1), (0.3, 0.98), (0.45, 1.0), (1.0, 1.0)], t)}
ROCK_EXTRA = [("albumen", "opacity", lambda t: keyed([(0.0, 1.0), (0.1, 0.7), (0.3, 1.0), (1.0, 1.0)], t)),
]

# ============================================================== death (0.45s)
# The break. The egg swells and shudders (0-0.2); then the cap kicks off along
# the crack — up and over on its hinge and away, tumbling to lie on the floor
# beside it — three shards burst out of the rim, and what was inside is gone:
# the pink, the grub and its organ; the dark of the empty cup shows where they
# were. The cup rocks once and sags; the jelly spreads under it. Still from 0.85.
def death_state(t):
    shud = math.sin(2 * math.pi * 3.0 * smooth(0.0, 0.2, t)) * (1 - smooth(0.16, 0.24, t))
    kick = smooth(0.18, 0.34, t)
    sway = math.sin(math.pi * smooth(0.22, 0.62, t))
    settle = smooth(0.5, 0.85, t)
    pose = {"body": (0.0, -1.0 * kick * (1 - settle) + 0.8 * settle, 5.0 * shud - 9.0 * sway + 3.0 * settle)}
    pose["cap"] = -4.0 * smooth(0.0, 0.18, t) - 20.0 * kick
    pose["grub"] = -30.0 * kick
    k = 1.0 + 0.08 * smooth(0.0, 0.18, t) * (1 - kick) - 0.08 * settle
    return pose, k

# the cap's flight, laid over its hinge motion: up and to the right, turning
# over, and down to lie on its side on the floor
CAP_DX = [(0.0, 0.0), (0.2, 0.0), (0.45, 4.0), (0.85, 7.5), (1.0, 7.5)]
CAP_DY = [(0.0, 0.0), (0.2, 0.0), (0.4, -3.0), (0.62, 0.5), (0.85, 11.0), (1.0, 11.0)]
CAP_ROT = [(0.0, 0.0), (0.2, 0.0), (0.5, 60.0), (0.85, 104.0), (1.0, 104.0)]
SHARD_FLY = {"shard_a": (-9.5, -8.0, -150.0), "shard_b": (1.5, -9.5, 200.0), "shard_c": (9.0, -7.0, 170.0)}
def appear_fade(t): return keyed([(0.0, 0.0), (0.2, 0.0), (0.24, 1.0), (0.55, 1.0), (0.75, 0.0), (1.0, 0.0)], t)
def gone(t0, t1): return lambda t: 1.0 - smooth(t0, t1, t)

def death_tracks():
    ts = [i / 36 for i in range(31)] + [0.85, 0.9, 1.0]
    base = tracks(death_state, ts, {"organ": lambda t: 1.0 + 0.7 * math.sin(math.pi * smooth(0.1, 0.34, t)),
                                    "jelly": lambda t: 1.0 + 0.36 * smooth(0.2, 0.8, t)},
                  [("albumen", "opacity", lambda t: 1.0 - 0.85 * smooth(0.22, 0.42, t)),
                   ("embryo", "opacity", gone(0.2, 0.32)), ("embryo_head", "opacity", gone(0.2, 0.32)),
                   ("organ", "opacity", gone(0.24, 0.36)),
                   ("shade", "opacity", lambda t: 1.0 - 0.7 * smooth(0.2, 0.5, t)),
                   ("jelly_sheen", "opacity", lambda t: 1.0 - smooth(0.3, 0.85, t)),
                   ("gloss", "opacity", lambda t: 1.0 - smooth(0.25, 0.6, t))]
                  + [(sid, "opacity", appear_fade) for sid in SHARDS])
    # the cap's flight and the shards', added onto what the rig gave them
    by = {(tr["part"], tr["prop"]): tr for tr in base}
    def add(pid, prop, fn):
        tr = by.get((pid, prop))
        if tr is None:
            tr = {"part": pid, "prop": prop, "keys": [[r2(t), 0.0] for t in ts], "ease": "linear"}
            base.append(tr); by[(pid, prop)] = tr
        for kv in tr["keys"]: kv[1] = r2(kv[1] + fn(kv[0]))
    for pid in ("cap", "gloss"):
        add(pid, "x", lambda t: keyed(CAP_DX, t))
        add(pid, "y", lambda t: keyed(CAP_DY, t))
        add(pid, "rot", lambda t: keyed(CAP_ROT, t))
    for sid, (fx, fy, fr) in SHARD_FLY.items():
        add(sid, "x", lambda t, fx=fx: fx * smooth(0.2, 0.7, t))
        add(sid, "y", lambda t, fy=fy: fy * math.sin(math.pi * 0.8 * smooth(0.2, 0.75, t)) + 10.0 * smooth(0.45, 0.8, t))
        add(sid, "rot", lambda t, fr=fr: fr * smooth(0.2, 0.75, t))
    return base

animations = {
    "rock": {
        "description": "something inside kicks: the egg is thrown up off its jelly and over, rocks back and forth on the point it stands on, dying away, and settles — the cap lifting on its hinge with the kick so the crack gapes dark, then clapping shut — while the grub turns over inside a beat later and the organ in it swells; the jelly squashes out as it lands; then a held pulse until the next kick. The game plays it faster as the hatch window runs out.",
        "duration": 1.0,
        "tracks": tracks(rock_state, keyset(30), ROCK_SCALES, ROCK_EXTRA),
    },
    "death": {
        "description": "the break: the egg swells and shudders, then the cap kicks off along the crack — up and over on its hinge and away, tumbling to lie on its side on the floor — three shards burst out of the rim, and what was inside is gone, the pink, the grub and its organ, the dark of the empty cup showing where they were; the cup rocks once and sags and the jelly spreads under it. Still from 0.85.",
        "duration": 0.45,
        "tracks": death_tracks(),
    },
}

# ============================================================== document
DESCRIPTION = (
    "What the Matriarch lays: one of the eggs in her brood chamber, put down on the floor — the same egg, drawn the same way, bigger. A "
    "single rigid egg standing in a smear of jelly: a pale, yellowed shell (`$ochre.light2`) with her pink showing through its lower half "
    "and the thing inside showing with it — a curled grub, already carrying a lit organ, because what she lays now is marked. Pale rather "
    "than her pink so it reads as an egg on a floor and against her, not as one more pink body. It is two pieces already — a cup and a cap, "
    "meeting along a zigzag crack round the upper third — and that is where it opens. The game draws it in place of the young for the "
    "hatch window, sized to what is coming out, so a Bulwark's egg is visibly bigger than a Replete's; the shell is 10.5 by 12.5, which "
    "the game reads as radius 11. Idle (`rock`) is something inside kicking: the egg thrown up off the jelly, rocking on its point and "
    "settling, the cap lifting on its hinge so the crack gapes, the grub turning over — the one thing on the field that says 'about to', "
    "and the game plays it faster as the window runs out. `death` is the hatch or the kill, the same break either way: the cap kicks off "
    "along the crack and tumbles to the floor, shards burst from the rim, what was inside is gone, the empty cup shows dark, sags, and "
    "the jelly spreads. Built on a skeleton (scripts/ovum.py): the egg rocks about the point it stands on, the cap is hinged at one end "
    "of the crack, the grub turns on its own bone."
)

doc = {
    "id": "ss.enemy.ovum",
    "name": "Ovum",
    "description": DESCRIPTION,
    "tags": ["enemy", "brood"],
    "size": [40, 48],
    "meta": {"radius": 11},
    "parts": RIG.parts,
    "animations": animations,
    "skeleton": RIG.skeleton(),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "apps", "ss", "assets", "ss-enemy-ovum.json")
    write_doc(doc, out)
    n_tracks = sum(len(a["tracks"]) for a in animations.values())
    print(f"wrote {os.path.relpath(out)}: {len(RIG.parts)} parts, {len(animations)} clips, {n_tracks} tracks")
