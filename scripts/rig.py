"""The rig every body generator in this directory is drawn on.

    from rig import Rig, ik2, poly, ell, circ, rect, bar, smooth, lerp, cyc, keyset, write_doc

A document is flat — parts in draw order, each posed by x/y/rot/scale/opacity
offsets from rest (offset in the parent frame, turn about the part's own
origin, which is how the engine adapters pose them). A body that moves like a
body is not flat: a tail is a chain, a leg is a hip, a knee and a foot. So the
generators build a skeleton here, hang every part off one of its bones, write
each clip as a *pose* — joint angles as functions of time — and let `tracks`
solve the flat offsets from it. Nothing can come apart at a joint, however far
a clip swings it, because every frame is posed from the joints.

The pieces:

  Rig.bone(name, parent, at, heading, length)
      A bone at rest in the asset's frame: where it starts, the way it points
      (world degrees, +y down so a rising heading turns clockwise on screen),
      how long it is. The root (parent None) is the body: a pose moves it with
      `body: (dx, dy, dtheta)`, turning about its own start.
  Rig.seal()
      Call once every bone is placed; freezes the rest pose.
  Rig.solve(pose)
      World (x, y, heading) of every bone. A pose is a dict of
        body: (dx, dy, dtheta)     the root's travel and turn
        <bone>: dtheta             a turn about the bone's own start
        abs:<bone>: heading        the bone's world heading outright (IK)
      and a bone's children ride it.
  Rig.put(id, bone, at, rot, shape, fill, …) / Rig.use(id, bone, at, asset, …)
      A part placed in the world at rest, riding `bone` from then on.
  Rig.on_bone(bone, along, across)
      A point in a bone's rest frame, in the world, and the bone's heading —
      where to put a part so it sits on the bone.
  Rig.tracks(pose_at, ts, extra)
      Solve `pose_at(t)` at every key time to per-part x/y/rot tracks (linear
      between keys, sampled densely enough that linear is the curve), plus any
      `extra` (part, prop, fn(t)) tracks — glows, scales, fades.
  ik2(hip, foot, l1, l2, bend)
      Two-bone inverse kinematics: the headings that put a foot at a point.
  Rig.reach(chain, effector, target, direction, pose)
      Angles for a chain of bones (a tail, a neck, an arm) that put a point on
      its last bone at `target`, the last bone along `direction` — a pose asked
      for as a place and a bearing rather than as angles.

`scripts/stinger.py` is the worked example: a tail on `reach`, legs on `ik2`,
and four clips written as pose functions.
"""
import json, math

R = math.radians
D = math.degrees
def r2(x): return round(x + 0.0, 2)
def lerp(a, b, t): return a + (b - a) * t
def mix(a, b, t): return [lerp(x, y, t) for x, y in zip(a, b)]
def smooth(a, b, t):
    x = max(0.0, min(1.0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)
def cyc(t, ph=0.0): return math.sin(2 * math.pi * (t + ph))
def cyc_c(t, ph=0.0): return math.cos(2 * math.pi * (t + ph))
def wrap(a): return (a + 180.0) % 360.0 - 180.0
def keyset(n): return [i / n for i in range(n + 1)]

# ---------------------------------------------------------------- shapes
def poly(pts): return {"kind": "poly", "points": [[r2(x), r2(y)] for x, y in pts]}
def ell(rx, ry): return {"kind": "ellipse", "rx": r2(rx), "ry": r2(ry)}
def circ(r): return {"kind": "circle", "r": r2(r)}
def rect(w, h, corner=None): return {"kind": "rect", "w": r2(w), "h": r2(h), "corner": r2(corner if corner is not None else min(w, h) / 2)}
def bar(L, w0, w1, over=0.6):
    """A limb segment from 0 to L along +x, `w0` wide at the root and `w1` at the tip, ends rounded off."""
    return poly([(-over, -w0 * 0.36), (0.0, -w0 / 2), (L, -w1 / 2), (L + over, -w1 * 0.36),
                 (L + over, w1 * 0.36), (L, w1 / 2), (0.0, w0 / 2), (-over, w0 * 0.36)])
INK_THIN = {"color": "$ink", "width": "thin"}
INK_HAIR = {"color": "$ink", "width": "hair"}
INK_BOLD = {"color": "$ink", "width": "bold"}

# ---------------------------------------------------------------- frames
def compose(parent_xf, local):
    (px, py, pa), (lx, ly, la) = parent_xf, local
    c, s = math.cos(R(pa)), math.sin(R(pa))
    return (px + lx * c - ly * s, py + lx * s + ly * c, pa + la)
def invert_apply(xf, pt, ang):
    """`pt, ang` given in the world, expressed in frame `xf`."""
    x, y, a = xf
    c, s = math.cos(R(a)), math.sin(R(a))
    dx, dy = pt[0] - x, pt[1] - y
    return (dx * c + dy * s, -dx * s + dy * c, ang - a)

def ik2(hip, foot, l1, l2, bend):
    """Headings (world degrees) of two bones from `hip` putting the far end at `foot`, the joint on the `bend` side (±1)."""
    dx, dy = foot[0] - hip[0], foot[1] - hip[1]
    d = max(1e-3, min(l1 + l2 - 1e-3, math.hypot(dx, dy)))
    base = math.atan2(dy, dx)
    a = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    th1 = base - bend * a
    kx, ky = hip[0] + l1 * math.cos(th1), hip[1] + l1 * math.sin(th1)
    th2 = math.atan2(foot[1] - ky, foot[0] - kx)
    return D(th1), D(th2)

class Bone:
    """A rest transform in the asset's frame: where the bone starts and the way it points."""
    def __init__(self, name, parent, at, heading, length=0.0):
        self.name, self.parent, self.at, self.heading, self.length = name, parent, at, heading, length
    def end(self):
        return (self.at[0] + self.length * math.cos(R(self.heading)), self.at[1] + self.length * math.sin(R(self.heading)))

class Rig:
    def __init__(self):
        self.bones = {}
        self.parts = []
        self.attach = {}  # part id -> bone it rides
        self.rest = None

    # ---- skeleton
    def bone(self, name, parent, at, heading, length=0.0):
        assert self.rest is None, "bones are placed before seal()"
        b = Bone(name, parent, at, heading, length)
        self.bones[name] = b
        return b
    def chain(self, prefix, parent, at, links):
        """Bones `<prefix>_0…` end to end from `at`, one per (length, heading); returns their names."""
        names, p = [], at
        for i, (L, h) in enumerate(links):
            b = self.bone(f"{prefix}_{i}", parent, p, h, L)
            names.append(b.name); p, parent = b.end(), b.name
        return names
    def end_of(self, name): return self.bones[name].end()
    def seal(self):
        self.rest = {n: (b.at[0], b.at[1], b.heading) for n, b in self.bones.items()}
        self.local = {}
        for n, b in self.bones.items():
            self.local[n] = self.rest[n] if b.parent is None else invert_apply(self.rest[b.parent], b.at, b.heading)
    def root(self):
        return next(n for n, b in self.bones.items() if b.parent is None)

    def solve(self, pose):
        out = {}
        root = self.root()
        def xf(n):
            if n in out: return out[n]
            b = self.bones[n]
            if b.parent is None:
                dx, dy, dth = pose.get(n, pose.get("body", (0.0, 0.0, 0.0))) if n == root else (0.0, 0.0, 0.0)
                out[n] = (b.at[0] + dx, b.at[1] + dy, b.heading + dth)
            else:
                px, py, pa = compose(xf(b.parent), (self.local[n][0], self.local[n][1], 0.0))
                a = pa + self.local[n][2] + pose.get(n, 0.0)
                if f"abs:{n}" in pose: a = pose[f"abs:{n}"]
                out[n] = (px, py, a)
            return out[n]
        for n in self.bones: xf(n)
        return out

    # ---- parts
    def on_bone(self, name, along=0.0, across=0.0):
        """A point in the bone's rest frame, and the bone's heading, in the world."""
        x, y, a = self.rest[name] if self.rest else (self.bones[name].at[0], self.bones[name].at[1], self.bones[name].heading)
        c, s = math.cos(R(a)), math.sin(R(a))
        return (x + along * c - across * s, y + along * s + across * c), a
    def put(self, id, bone, at, rot, shape, fill, stroke=None, opacity=None, scale=None):
        """A part placed in the world at rest, riding `bone` from then on."""
        p = {"id": id, "at": [r2(at[0]), r2(at[1])]}
        if abs(rot) > 1e-6: p["rot"] = r2(rot)
        if scale is not None: p["scale"] = scale
        if opacity is not None: p["opacity"] = opacity
        p["shape"] = shape
        p["fill"] = fill
        if stroke: p["stroke"] = stroke
        self.parts.append(p); self.attach[id] = bone
        return p
    def use(self, id, bone, at, asset, scale=None, rot=0.0, variant=None, opacity=None):
        """A library document composed in, riding `bone`."""
        p = {"id": id, "at": [r2(at[0]), r2(at[1])]}
        if abs(rot) > 1e-6: p["rot"] = r2(rot)
        if scale is not None: p["scale"] = scale
        if opacity is not None: p["opacity"] = opacity
        p["use"] = asset
        if variant: p["variant"] = variant
        self.parts.append(p); self.attach[id] = bone
        return p
    def check(self):
        ids = [p["id"] for p in self.parts]
        dup = {i for i in ids if ids.count(i) > 1}
        assert not dup, f"duplicate part ids: {sorted(dup)}"

    # ---- motion
    def posed_parts(self, pose):
        """Every part's (x, y, rot) under `pose`, as the adapters would pose it."""
        world = self.solve(pose)
        base = {p["id"]: p for p in self.parts}
        out = {}
        for pid, bn in self.attach.items():
            p = base[pid]
            at, rot = tuple(p["at"]), p.get("rot", 0.0)
            lx, ly, la = invert_apply(self.rest[bn], at, rot)
            out[pid] = compose(world[bn], (lx, ly, la))
        return out
    def tracks(self, pose_at, ts, extra=None, still=()):
        """
        Solve `pose_at(t)` at every `t` to per-part x/y/rot offset tracks, and
        append `extra` (part, prop, fn) tracks. Parts named in `still` never
        take a `rot` track (a round part whose turn would only show as noise).
        """
        rest = self.posed_parts({})
        series = {pid: ([], [], []) for pid in self.attach}
        for t in ts:
            now = self.posed_parts(pose_at(t))
            for pid, (x, y, a) in now.items():
                bx, by, ba = rest[pid]
                series[pid][0].append(x - bx); series[pid][1].append(y - by); series[pid][2].append(wrap(a - ba))
        out = []
        for p in self.parts:
            pid = p["id"]
            xs, ys, rs = series[pid]
            for prop, vs in (("x", xs), ("y", ys), ("rot", rs)):
                if prop == "rot" and pid in still: continue
                if max(abs(v) for v in vs) > 0.01:
                    out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(v)] for t, v in zip(ts, vs)], "ease": "linear"})
        for pid, prop, fn in (extra or []):
            out.append({"part": pid, "prop": prop, "keys": [[r2(t), r2(fn(t))] for t in ts], "ease": "linear"})
        return out

    def reach(self, chain, effector, target, direction, pose=None, prefer=0.0004, even=0.0008):
        """
        Deltas for the bones in `chain` (root first) that put `effector` — a
        point in the last bone's frame — at `target`, with the last bone's
        heading at `direction` (world degrees; None leaves it free). The last
        bone's delta follows from the direction outright; the rest are found by
        coordinate descent that prefers the rest pose (`prefer`) and an even
        bend down the chain (`even`), so the answer is a curve, not a kink.
        Returns the deltas in chain order; merge them into `pose`.
        """
        pose = dict(pose or {})
        head, last = chain[:-1], chain[-1]
        def place(ds):
            q = dict(pose)
            for n, d in zip(head, ds): q[n] = q.get(n, 0.0) + d
            return q
        def tip_of(q, last_heading):
            x, y, _ = self.solve(q)[last]
            c, s = math.cos(R(last_heading)), math.sin(R(last_heading))
            return (x + effector[0] * c - effector[1] * s, y + effector[0] * s + effector[1] * c)
        def cost(ds):
            q = place(ds)
            w = self.solve(q)
            h = direction if direction is not None else w[last][2]
            tx, ty = tip_of(q, h)
            sm = sum((ds[i] - ds[i + 1]) ** 2 for i in range(len(ds) - 1))
            return (tx - target[0]) ** 2 + (ty - target[1]) ** 2 + prefer * sum(d * d for d in ds) + even * sm
        ds, step = [0.0] * len(head), 16.0
        best = cost(ds)
        while step > 0.01:
            moved = False
            for i in range(len(ds)):
                for sgn in (1, -1):
                    trial = ds[:]; trial[i] += sgn * step
                    c2 = cost(trial)
                    if c2 < best: ds, best, moved = trial, c2, True
            if not moved: step /= 2
        q = place(ds)
        last_d = 0.0
        if direction is not None:
            last_d = wrap(direction - self.solve(q)[last][2])
        return ds + [last_d]

    def skeleton(self):
        joints, bones = {}, []
        for n, b in self.bones.items():
            joints[n] = b.at
            if b.parent is not None: bones.append([b.parent, n])
            if b.length > 0 and not any(c.parent == n for c in self.bones.values()):
                joints[f"{n}_end"] = b.end(); bones.append([n, f"{n}_end"])
        return {"joints": {k: [r2(v[0]), r2(v[1])] for k, v in joints.items()}, "bones": bones}

# ---------------------------------------------------------------- the house format
def one(v): return json.dumps(v, ensure_ascii=False)
def write_doc(doc, path):
    """Write `doc` one part and one track to a line, the way the hand-kept documents are laid out."""
    L = ["{"]
    for k in ("id", "name", "description", "tags", "size", "anchor", "meta", "why"):
        if k in doc: L.append(f'  "{k}": {one(doc[k])},')
    L.append('  "parts": [')
    L.append(",\n".join(f"    {one(p)}" for p in doc["parts"]))
    L.append("  ],")
    if doc.get("variants"):
        L.append('  "variants": {')
        vs = []
        for name, v in doc["variants"].items():
            body = [f'    {one(name)}: {{', f'      "description": {one(v["description"])}']
            rest = [(k, v[k]) for k in ("scale", "animations", "remove", "add") if k in v]
            for k, val in rest: body[-1] += ","; body.append(f'      "{k}": {one(val)}')
            if v.get("set"):
                body[-1] += ","
                body.append('      "set": {')
                body.append(",\n".join(f"        {one(k)}: {one(val)}" for k, val in v["set"].items()))
                body.append("      }")
            body.append("    }")
            vs.append("\n".join(body))
        L.append(",\n".join(vs))
        L.append("  },")
    if doc.get("skeleton"):
        L.append('  "skeleton": {')
        L.append('    "joints": {')
        L.append(",\n".join(f"      {one(k)}: {one(v)}" for k, v in doc["skeleton"]["joints"].items()))
        L.append("    },")
        L.append(f'    "bones": {one(doc["skeleton"]["bones"])}')
        L.append("  },")
    L.append('  "animations": {')
    anims = []
    for name, a in doc["animations"].items():
        body = [f'    {one(name)}: {{', f'      "description": {one(a["description"])},', f'      "duration": {one(a["duration"])},', '      "tracks": [']
        body.append(",\n".join(f"        {one(t)}" for t in a["tracks"]))
        body.append("      ]")
        body.append("    }")
        anims.append("\n".join(body))
    L.append(",\n".join(anims))
    L.append("  }")
    L.append("}")
    open(path, "w").write("\n".join(L) + "\n")
