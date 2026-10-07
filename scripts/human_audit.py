"""Measure the Wanderer's rig against the standard proportions, landmark by landmark.

    python3 scripts/human_audit.py

A figure that is a few percent off reads as wrong long before anyone can say
why — a torso a head-fraction too long, a forearm that reaches past the
crotch — so the rig is measured rather than eyeballed. Two standards:

  - Drillis & Contini (1966): mean adult segment lengths as fractions of
    stature, the set biomechanics uses (hip height 0.530, knee 0.285,
    shoulder 0.818, elbow 0.630, wrist 0.485, fingertip 0.377, upper arm
    0.186, forearm 0.146, hand 0.108, thigh 0.245, shank 0.246, foot length
    0.152, foot height 0.039, biacromial width 0.259, hip width 0.191,
    chest depth 0.174, head+neck 0.182)
  - the academic head-unit figure (Loomis): 7.5 heads for the average adult,
    8 for the ideal; chin at 1, nipples at 2, navel at 3, crotch at 4 (of 8),
    knees at 6, shoulders 2⅓ heads wide, hips 1.5

A row is flagged when it is more than 3% of stature off the standard — about
the threshold at which a proportion is noticed on a figure this size.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import human  # noqa: E402 — builds the rig at import; writes nothing

H = human.H
height = human.GROUND - (human.GROUND - 7.5 * H)   # 120: the figure's stature by construction
top = human.GROUND - 7.5 * H
rest = human.RIG.rest
B = human.B

def y_of(bone, at_end=False):
    b = B[bone]
    return b.end()[1] if at_end else b.at[1]
def up(y): return human.GROUND - y          # height above the sole line

rows = []
def row(name, actual, standard, unit="px"):
    rows.append((name, actual, standard, unit))

# heights above the ground, as fractions of stature
hip = (B["leg_n_thigh"].at[1] + B["leg_f_thigh"].at[1]) / 2
knee = (B["leg_n_shin"].at[1] + B["leg_f_shin"].at[1]) / 2
shoulder = (B["arm_n_upper"].at[1] + B["arm_f_upper"].at[1]) / 2
elbow = (B["arm_n_fore"].at[1] + B["arm_f_fore"].at[1]) / 2
wrist = (B["hand_n"].at[1] + B["hand_f"].at[1]) / 2
fingertip = (B["hand_n"].end()[1] + B["hand_f"].end()[1]) / 2 + 1.0
row("hip joint height / stature", up(hip) / height, 0.530, "")
row("knee height / stature", up(knee) / height, 0.285, "")
row("shoulder height / stature", up(shoulder) / height, 0.818, "")
row("elbow height / stature", up(elbow) / height, 0.630, "")
row("wrist height / stature", up(wrist) / height, 0.485, "")
row("fingertip height / stature", up(fingertip) / height, 0.377, "")
# segment lengths
row("upper arm / stature", human.UPPER / height, 0.186, "")
row("forearm / stature", human.FORE / height, 0.146, "")
row("thigh / stature", human.THIGH / height, 0.245, "")
row("shank (knee→ankle) / stature", human.SHIN / height, 0.246, "")
row("foot height / stature", human.FOOT_H / height, 0.039, "")
foot_len = max(a for a, c in human.FOOT_C) - min(a for a, c in human.FOOT_C)
row("foot length / stature", foot_len / height, 0.152, "")
# widths, projected: the shoulder line on screen is the biacromial width times sin(turn)
TURN = math.radians(25)
sn, sf = human.SHOULDER["n"], human.SHOULDER["f"]
row("shoulder line on screen (biacromial·sin25°)", math.hypot(sf[0] - sn[0], sf[1] - sn[1]), 0.259 * height * math.sin(TURN))
hn, hf = human.HIP["n"], human.HIP["f"]
row("hip joints on screen (hip width·sin25°)", math.hypot(hf[0] - hn[0], hf[1] - hn[1]), 0.191 * height * math.sin(TURN))
torso_x = [x for x, y in human.TORSO_C if -32 < y < -24]
row("chest depth on screen", max(torso_x) - min(torso_x), 0.174 * height)
# head units: where the landmarks fall in heads from the top
head_top = top
chin = B["head"].at[1] + B["head"].length - 7.6 + 0.6  # the skull's bottom control point, roughly: head bone end is the centre
row("head height (crown − chin) in heads", abs(human.HEAD_C[0][0] - human.HEAD_C[12][0]) / H, 1.0, "H")
row("shoulder line, heads from top", (shoulder - top) / H, 1.4, "H")
row("navel (belt) , heads from top", (-12.0 - top) / H, 3.0 * 7.5 / 8, "H")
row("crotch, heads from top", (hip + 5.0 - top) / H, 3.75, "H")
row("knee, heads from top", (knee - top) / H, 5.5, "H")

print(f"stature {height:.0f}px = 7.5 H, H = {H:.0f}px, ground {human.GROUND:+.0f}, hip joints at y {hip:+.1f}\n")
print(f"{'landmark':50s} {'rig':>8s} {'standard':>9s}  {'off':>6s}")
print("─" * 80)
bad = 0
for name, a, s, unit in rows:
    if unit == "":
        off = (a - s) * 100
        flag = "▲" if abs(a - s) > 0.03 else " "
        print(f"{name:50s} {a:8.3f} {s:9.3f}  {off:+5.1f}% {flag}")
    else:
        off = a - s
        tol = 0.03 * height if unit == "px" else 0.25
        flag = "▲" if abs(off) > tol else " "
        print(f"{name:50s} {a:7.2f}{unit} {s:8.2f}{unit}  {off:+5.1f}{unit} {flag}")
    bad += flag == "▲"
print(f"\n{bad} of {len(rows)} landmarks more than the tolerance off")
