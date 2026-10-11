"""Hospital room props (same kit and conventions as assets.py)."""

import math
import random

import bmesh
from mathutils import Matrix, Vector

from . import assets as A
from . import kit as K
from . import mats as M
from .assets import (ALU, BLACK_PLASTIC, CERAMIC, DARK_METAL, DARK_WOOD, PAPER, RUBBER, STAINLESS, WHITE_PLASTIC,
                     decal, glass, glow, mat, tile)
from .kit import Surf

PI = math.pi

BED_WHITE = Surf("paint", "#E6E8E6", "#9AA0A2", rough=0.38, metal=0.35, chips=0.2, name="BedSteel")
BED_PANEL = Surf("paint", "#A9C3CF", "#6E8792", rough=0.4, edge=0.25, name="BedPanel")
SHEET = Surf("fabric", "#F1F1EC", rough=0.9, sheen=0.3, edge=0.0, ao=0.5, name="Sheet")
PILLOW = Surf("fabric", "#F6F6F2", rough=0.9, sheen=0.3, edge=0.0, ao=0.55, name="Pillow")
LAMINATE = Surf("wood", "#D9C29B", "#B39466", rough=0.45, name="Laminate")
VINYL = Surf("fabric", "#3F5E7A", rough=0.55, sheen=0.1, edge=0.15, name="Vinyl")
STEM = Surf("paint", "#3E7A2E", "#22401A", rough=0.6, edge=0.0, name="Stem")
CURTAIN_GREEN = Surf("fabric", "#9DB8A2", rough=0.9, sheen=0.35, edge=0.0, ao=0.6, name="CurtainGreen")
PRIVACY = Surf("fabric", "#B9D2DE", rough=0.9, sheen=0.35, edge=0.0, ao=0.6, name="PrivacyCurtain")
BLIND = Surf("paint", "#E9E6DC", "#A8A396", rough=0.4, metal=0.2, edge=0.2, name="Blind")

BED_L, BED_W, MATTRESS_TOP = 2.05, 0.95, 0.62


def hospital_bed(a):
    """Bed along X (head end +X), origin at the floor centre."""
    L, W = BED_L, BED_W
    x0, x1, y0, y1 = -L / 2, L / 2, -W / 2, W / 2
    deck = 0.46
    for lo, hi in (((x0 + 0.05, y0, deck - 0.06), (x1 - 0.05, y0 + 0.05, deck)),
                   ((x0 + 0.05, y1 - 0.05, deck - 0.06), (x1 - 0.05, y1, deck))):
        a.lohi(lo, hi, BED_WHITE, bevel=0.008)
    a.lohi((x0 + 0.08, y0 + 0.05, deck - 0.02), (x1 - 0.08, y1 - 0.05, deck), BED_WHITE, bevel=0.004)
    for x in (x0 + 0.12, 0.0, x1 - 0.12):
        a.lohi((x - 0.03, y0 + 0.05, deck - 0.05), (x + 0.03, y1 - 0.05, deck - 0.02), BED_WHITE, bevel=0.004)
    a.lohi((x0 + 0.3, -0.05, 0.2), (x1 - 0.3, 0.05, 0.28), BED_WHITE, bevel=0.012)
    for x in (x0 + 0.08, x1 - 0.08):
        a.lohi((x - 0.04, -0.05, 0.12), (x + 0.04, 0.05, deck - 0.05), BED_WHITE, bevel=0.01)
        a.lohi((x - 0.05, y0 + 0.03, 0.12), (x + 0.05, y1 - 0.03, 0.2), BED_WHITE, bevel=0.012)
        for y in (y0 + 0.07, y1 - 0.07):
            a.cyl(0.022, 0.05, (x, y, 0.15), DARK_METAL, segs=10, bevel=0.004)
            a.lohi((x - 0.015, y - 0.03, 0.06), (x + 0.015, y + 0.03, 0.13), DARK_METAL, bevel=0.004)
            a.cyl(0.05, 0.035, (x - 0.02, y, 0.05), RUBBER, rot=(PI / 2, 0, 0), segs=14, bevel=0.006)
    # mattress, sheet tucked in, pillow
    a.box((L - 0.1, W - 0.05, MATTRESS_TOP - deck), (0, 0, (deck + MATTRESS_TOP) / 2), SHEET, bevel=0.045, seg=3,
          wobble=0.01)
    a.blob((0.5, 0.72, 0.16), (x1 - 0.32, 0, MATTRESS_TOP + 0.06), PILLOW, subdiv=3, wobble=0.012)
    # head and foot boards: moulded panels with rounded tops
    for x, top in ((x1 - 0.02, 1.15), (x0 + 0.02, 0.88)):
        prof = [(y, z) for (y, z) in K.rounded_rect(W + 0.04, top - 0.3, 0.09, 4)]
        v = K.extrude(a.bm, prof, 0.05, (0, 0, 0), None)
        bmesh.ops.transform(a.bm, matrix=Matrix.Translation((x, 0, 0.3 + (top - 0.3) / 2)) @
                            Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))), verts=v)
        a.add(v, BED_PANEL, bevel=0.012, wobble=0.003)
        a.lohi((x - 0.03, -W * 0.3, top - 0.13), (x + 0.03, W * 0.3, top - 0.07), BED_WHITE, bevel=0.008)
    # side rails (head half), both sides
    for y in (y0 - 0.025, y1 + 0.025):
        for x in (x0 + 0.95, x1 - 0.2):
            a.rod((x, y, MATTRESS_TOP - 0.06), (x, y, MATTRESS_TOP + 0.26), 0.016, BED_WHITE, segs=8)
        for z in (MATTRESS_TOP + 0.1, MATTRESS_TOP + 0.26):
            a.rod((x0 + 0.95, y, z), (x1 - 0.2, y, z), 0.016, BED_WHITE, segs=8, bevel=0.003)
        for k in range(1, 6):
            x = x0 + 0.95 + (x1 - 0.2 - x0 - 0.95) * k / 6
            a.rod((x, y, MATTRESS_TOP + 0.1), (x, y, MATTRESS_TOP + 0.26), 0.009, BED_WHITE, segs=6)
    # nurse-call handset hanging on the rail
    hy = y0 - 0.04
    a.box((0.05, 0.03, 0.13), (x0 + 1.3, hy, MATTRESS_TOP + 0.13), WHITE_PLASTIC, bevel=0.01)
    a.cyl(0.012, 0.006, (x0 + 1.3, hy - 0.016, MATTRESS_TOP + 0.16), Surf("paint", "#D8342E", rough=0.4, name="CallButton"),
          rot=(PI / 2, 0, 0), segs=10)
    a.tube([(x0 + 1.3, hy, MATTRESS_TOP + 0.2), (x0 + 1.32, hy, MATTRESS_TOP + 0.27), (x0 + 1.35, hy + 0.01, MATTRESS_TOP + 0.27)],
           0.004, WHITE_PLASTIC, segs=4)


def iv_stand(a):
    for k in range(5):
        t = 2 * PI * k / 5
        p = Vector((math.cos(t) * 0.3, math.sin(t) * 0.3, 0.06))
        a.rod((0, 0, 0.1), p, 0.014, STAINLESS, segs=6)
        a.cyl(0.03, 0.03, p - Vector((0, 0, 0.03)), RUBBER, rot=(PI / 2, 0, t), segs=10, bevel=0.005)
    a.lathe([(0, 0.06), (0.04, 0.06), (0.045, 0.12), (0.02, 0.16), (0, 0.16)], STAINLESS, segs=10)
    a.cyl(0.013, 1.9, (0, 0, 1.08), STAINLESS, segs=8)
    a.lathe([(0, 0), (0.02, 0), (0.022, 0.08), (0, 0.09)], DARK_METAL, segs=8, loc=(0, 0, 1.2))
    for sx in (-1, 1):
        a.tube([(0, 0, 2.0), (sx * 0.1, 0, 2.02), (sx * 0.14, 0, 1.98), (sx * 0.13, 0, 1.94)], 0.007, STAINLESS, segs=6)
    a.lathe([(0, 2.04), (0.025, 2.03), (0, 2.06)], STAINLESS, segs=8)
    bag = glass("IVBag", "#EEF4F6", 0.25)
    v = K.blob(a.bm, (0.13, 0.04, 0.22), (0.12, 0, 1.78), None, subdiv=2)
    a.add(v, bag)
    a.lathe([(0, 0), (0.012, 0.0), (0.012, 0.05), (0, 0.06)], bag, segs=8, loc=(0.12, 0, 1.62))
    a.tube([(0.12, 0, 1.62), (0.13, 0, 1.3), (0.2, -0.05, 0.95), (0.35, -0.2, 0.75), (0.6, -0.35, 0.68)], 0.003,
           glass("IVLine", "#F2F6F7", 0.2), segs=4, cap=False)


def vitals_monitor(a):
    """Monitor centred on its origin, screen facing -Y, arm reaching back to a wall plate."""
    W, D_, H = 0.4, 0.12, 0.32
    a.lohi((-W / 2, -D_ / 2, -H / 2), (W / 2, D_ / 2, H / 2), WHITE_PLASTIC, bevel=0.02, wobble=0.002)
    a.lohi((-W / 2 + 0.025, -D_ / 2 - 0.004, -H / 2 + 0.03), (W / 2 - 0.025, -D_ / 2 + 0.01, H / 2 - 0.025),
           BLACK_PLASTIC, bevel=0.006)
    a.plane(W - 0.07, H - 0.075, (0, -D_ / 2 - 0.0045, 0.002), decal("ECGBezel", "ecg_bezel", rough=0.15, emit=0.6))
    for k in range(4):
        a.cyl(0.009, 0.01, (-W / 2 + 0.05 + k * 0.04, -D_ / 2 - 0.004, -H / 2 + 0.016), Surf("paint", ("#3FB65A", "#E8C53A", "#3A7AD2", "#D8342E")[k],
                                                                                       rough=0.4, name=f"Btn{k}"),
              rot=(PI / 2, 0, 0), segs=8)
    a.tube([(-0.08, 0, H / 2), (-0.08, 0, H / 2 + 0.05), (0.08, 0, H / 2 + 0.05), (0.08, 0, H / 2)], 0.012, WHITE_PLASTIC,
           segs=6)
    a.lohi((-0.05, D_ / 2, -0.05), (0.05, D_ / 2 + 0.03, 0.05), DARK_METAL, bevel=0.006)
    a.rod((0, D_ / 2 + 0.03, -0.0), (0, 0.3, -0.06), 0.022, STAINLESS, segs=10)
    a.cyl(0.03, 0.06, (0, 0.3, -0.06), DARK_METAL, segs=10, bevel=0.006)
    a.rod((0, 0.3, -0.08), (0, 0.6, -0.1), 0.022, STAINLESS, segs=10)
    a.lohi((-0.08, 0.6, -0.2), (0.08, 0.63, 0.0), WHITE_PLASTIC, bevel=0.01)


def bedside_cabinet(a):
    W, D_, H = 0.5, 0.44, 0.72
    a.lohi((-W / 2, -D_ / 2, 0.08), (W / 2, D_ / 2, H - 0.03), WHITE_PLASTIC, bevel=0.012, wobble=0.002)
    a.lohi((-W / 2 - 0.01, -D_ / 2 - 0.01, H - 0.03), (W / 2 + 0.01, D_ / 2 + 0.01, H), LAMINATE, bevel=0.01, grain=(1, 0, 0))
    a.lohi((-W / 2 + 0.02, -D_ / 2 - 0.012, H - 0.17), (W / 2 - 0.02, -D_ / 2 + 0.002, H - 0.05), LAMINATE, bevel=0.006,
           grain=(1, 0, 0))
    a.lohi((-W / 2 + 0.02, -D_ / 2 - 0.012, 0.11), (W / 2 - 0.02, -D_ / 2 + 0.002, H - 0.2), LAMINATE, bevel=0.006,
           grain=(0, 0, 1))
    for z, w in ((H - 0.11, 0.16), (H - 0.32, 0.1)):
        a.rod((-w / 2, -D_ / 2 - 0.03, z), (w / 2, -D_ / 2 - 0.03, z), 0.008, STAINLESS, segs=6)
        for sx in (-1, 1):
            a.rod((sx * w / 2, -D_ / 2 - 0.03, z), (sx * w / 2, -D_ / 2, z), 0.007, STAINLESS, segs=6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            a.cyl(0.03, 0.025, (sx * (W / 2 - 0.05), sy * (D_ / 2 - 0.05), 0.035), RUBBER, rot=(PI / 2, 0, 0), segs=10,
                  bevel=0.005)
            a.lohi((sx * (W / 2 - 0.05) - 0.012, sy * (D_ / 2 - 0.05) - 0.012, 0.05),
                   (sx * (W / 2 - 0.05) + 0.012, sy * (D_ / 2 - 0.05) + 0.012, 0.085), DARK_METAL, bevel=0.003)


def flower_vase(a, seed=4):
    rnd = random.Random(seed)
    a.lathe([(0, 0), (0.042, 0), (0.048, 0.03), (0.05, 0.12), (0.034, 0.19), (0.04, 0.215), (0.036, 0.22), (0, 0.006)],
            glass("VaseGlass", "#CFE6EF", 0.04), segs=14)
    a.lathe([(0, 0.006), (0.044, 0.006), (0.046, 0.11), (0, 0.11)], Surf("mat", material=M.glass("VaseWater", tint=(0.85, 0.93, 0.9), reflect=0.05),
                                                                         name="VaseWater"), segs=14)
    petals = [Surf("paint", c, rough=0.6, edge=0.05, sss=0.2, var=0.1, name="Petal" + c[1:]) for c in
              ("#F2D23A", "#F07A92", "#F6F2EA", "#E8553A")]
    centre = Surf("paint", "#7A4A1A", rough=0.7, edge=0.0, name="FlowerCentre")
    for k in range(7):
        ang = 2 * PI * k / 7 + rnd.uniform(-0.3, 0.3)
        r = rnd.uniform(0.04, 0.11)
        top = Vector((math.cos(ang) * r, math.sin(ang) * r, rnd.uniform(0.34, 0.46)))
        mid = Vector((top.x * 0.4, top.y * 0.4, 0.22))
        a.tube([(0, 0, 0.03), mid, top], 0.0035, STEM, segs=5)
        if k % 2 == 0:                    # tulip: a closed cup of petals
            a.lathe([(0, 0), (0.02, 0.01), (0.03, 0.035), (0.026, 0.06), (0.0, 0.065)], rnd.choice(petals[:2] + petals[3:]),
                    segs=6, loc=top, rot=(rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 0), wobble=0.004)
        else:                             # daisy: a disc with a ring of petals
            a.cyl(0.012, 0.01, top, centre, segs=8, bevel=0.003)
            for p in range(8):
                t = 2 * PI * p / 8
                a.box((0.03, 0.012, 0.004), top + Vector((math.cos(t) * 0.025, math.sin(t) * 0.025, -0.002)), petals[2],
                      rot=(0, 0.25, t), bevel=0.0)
        if rnd.random() < 0.6:
            leaf_at = mid.lerp(top, 0.3)
            a.box((0.05, 0.015, 0.004), leaf_at + Vector((0.02, 0, 0)), STEM, rot=(0, -0.5, ang))


def water_glass(a):
    a.lathe([(0, 0), (0.028, 0), (0.033, 0.1), (0.031, 0.1), (0.026, 0.005), (0, 0.005)], glass("Tumbler", "#EAF3F6", 0.03),
            segs=14)
    a.lathe([(0, 0.006), (0.026, 0.006), (0.03, 0.07), (0, 0.07)], Surf("mat", material=M.glass("TumblerWater", tint=(0.9, 0.96, 1.0), reflect=0.05),
                                                                         name="TumblerWater"), segs=14)


STOOL_TOP = 0.46


def stool(a):
    a.lathe([(0, STOOL_TOP - 0.06), (0.17, STOOL_TOP - 0.06), (0.19, STOOL_TOP - 0.04), (0.19, STOOL_TOP - 0.015),
             (0.17, STOOL_TOP), (0, STOOL_TOP + 0.004)], VINYL, segs=20, wobble=0.003)
    a.lathe([(0.15, STOOL_TOP - 0.085), (0.17, STOOL_TOP - 0.085), (0.17, STOOL_TOP - 0.06), (0.15, STOOL_TOP - 0.06)],
            STAINLESS, segs=20)
    for k in range(4):
        t = PI / 4 + k * PI / 2
        top = Vector((math.cos(t) * 0.14, math.sin(t) * 0.14, STOOL_TOP - 0.07))
        bot = Vector((math.cos(t) * 0.19, math.sin(t) * 0.19, 0.02))
        a.rod(top, bot, 0.013, STAINLESS, segs=8, bevel=0.003)
        a.cyl(0.018, 0.02, bot - Vector((0, 0, 0.01)), RUBBER, segs=8, bevel=0.004)
    ring = [Vector((math.cos(t) * 0.175, math.sin(t) * 0.175, 0.17)) for t in (2 * PI * k / 16 for k in range(17))]
    a.tube(ring, 0.008, STAINLESS, segs=6, cap=False)


def painting_frame(a):
    W, H = 0.9, 0.6
    f = 0.05
    for lo, hi in (((-W / 2 - f, -0.035, -f), (W / 2 + f, 0, 0)), ((-W / 2 - f, -0.035, H), (W / 2 + f, 0, H + f)),
                   ((-W / 2 - f, -0.035, 0), (-W / 2, 0, H)), ((W / 2, -0.035, 0), (W / 2 + f, 0, H))):
        a.lohi(lo, hi, DARK_WOOD, bevel=0.01)
    a.lohi((-W / 2, -0.012, 0), (W / 2, 0, H), PAPER)
    a.plane(W - 0.04, H - 0.04, (0, -0.0125, H / 2), decal("Painting", "painting", rough=0.7))


def hosp_door(a, W=1.05, H=2.1):
    a.lohi((-W / 2, -0.03, 0.0), (W / 2, 0.01, H), Surf("wood", "#CBB08A", "#A88C64", rough=0.5, name="HospDoorWood"),
           bevel=0.008, grain=(0, 0, 1))
    a.lohi((-0.08, -0.034, 1.0), (0.08, -0.026, 1.85), glass("DoorGlass"))
    for lo, hi in (((-0.1, -0.04, 0.98), (0.1, -0.026, 1.0)), ((-0.1, -0.04, 1.85), (0.1, -0.026, 1.87)),
                   ((-0.1, -0.04, 1.0), (-0.08, -0.026, 1.85)), ((0.08, -0.04, 1.0), (0.1, -0.026, 1.85))):
        a.lohi(lo, hi, STAINLESS, bevel=0.003)
    a.rod((W / 2 - 0.1, -0.075, 0.75), (W / 2 - 0.1, -0.075, 1.25), 0.014, STAINLESS, segs=8)
    for z in (0.78, 1.22):
        a.rod((W / 2 - 0.1, -0.075, z), (W / 2 - 0.1, -0.03, z), 0.01, STAINLESS, segs=6)
    a.lohi((-W / 2 + 0.02, -0.036, 0.02), (W / 2 - 0.02, -0.03, 0.22), STAINLESS, bevel=0.003)
    fw = 0.06
    for lo, hi in (((-W / 2 - fw, -0.05, 0), (-W / 2, 0.06, H + fw)), ((W / 2, -0.05, 0), (W / 2 + fw, 0.06, H + fw)),
                   ((-W / 2, -0.05, H), (W / 2, 0.06, H + fw))):
        a.lohi(lo, hi, ALU, bevel=0.006)


def ceiling_panel(a, on=False):
    a.lohi((-0.62, -0.32, -0.04), (0.62, 0.32, 0), WHITE_PLASTIC, bevel=0.01)
    a.lohi((-0.57, -0.27, -0.045), (0.57, 0.27, -0.035), glow("PanelOn", "#F4F7FF", 6.0) if on else
           Surf("ceramic", "#F2F2EE", rough=0.3, name="Diffuser"))


def bed_head_panel(a, L=1.8):
    """Wall rail behind the bed head: gas outlets, nurse call, reading light, sockets (front -Y)."""
    a.lohi((-L / 2, -0.09, 0.0), (L / 2, 0, 0.22), Surf("paint", "#DCE3E2", "#9AA3A2", rough=0.4, name="HeadPanel"),
           bevel=0.015, wobble=0.002)
    a.lohi((-L / 2, -0.1, 0.08), (L / 2, -0.088, 0.1), ALU, bevel=0.003)
    for k, c in enumerate(("#3FA34D", "#E8C53A", "#2A2A2E")):
        x = -0.55 + k * 0.14
        a.cyl(0.035, 0.03, (x, -0.1, 0.16), Surf("paint", c, rough=0.35, name=f"Gas{k}"), rot=(PI / 2, 0, 0), segs=12,
              bevel=0.005)
        a.cyl(0.015, 0.02, (x, -0.12, 0.16), STAINLESS, rot=(PI / 2, 0, 0), segs=10)
    a.lohi((0.1, -0.1, 0.12), (0.26, -0.09, 0.2), WHITE_PLASTIC, bevel=0.005)
    a.cyl(0.02, 0.01, (0.18, -0.105, 0.16), Surf("paint", "#D8342E", rough=0.4, name="CallButton"), rot=(PI / 2, 0, 0),
          segs=10)
    for x in (0.4, 0.55):
        a.lohi((x - 0.05, -0.098, 0.03), (x + 0.05, -0.09, 0.07), WHITE_PLASTIC, bevel=0.003)
    a.tube([(0.75, -0.06, 0.22), (0.75, -0.2, 0.4), (0.72, -0.35, 0.45)], 0.012, STAINLESS, segs=6)
    a.lathe([(0, 0), (0.05, 0.0), (0.07, 0.06), (0, 0.065)], WHITE_PLASTIC, segs=12, loc=(0.71, -0.38, 0.43),
            rot=(PI * 0.75, 0, 0))


def blinds(a, W=2.58, H=1.4, low=0.42, n=22):
    """Venetian blinds hanging from the top of a window W wide, slats ending `low` above the sill."""
    a.lohi((-W / 2, -0.05, H - 0.05), (W / 2, 0.0, H), BLIND, bevel=0.008)
    for k in range(n):
        z = H - 0.08 - k * (H - 0.08 - low) / n
        a.box((W - 0.02, 0.05, 0.004), (0, -0.025, z), BLIND, rot=(math.radians(-14), 0, 0))
    a.lohi((-W / 2 + 0.01, -0.045, low - 0.03), (W / 2 - 0.01, -0.005, low), BLIND, bevel=0.006)
    for x in (-W / 2 + 0.15, W / 2 - 0.15):
        a.rod((x, -0.028, low - 0.02), (x, -0.028, H - 0.05), 0.0018, PAPER, segs=4)
    a.tube([(W / 2 - 0.08, -0.05, H - 0.05), (W / 2 - 0.08, -0.06, low + 0.3)], 0.002, PAPER, segs=4)
    a.lathe([(0, 0), (0.01, 0.0), (0.008, 0.04), (0, 0.045)], WHITE_PLASTIC, segs=6, loc=(W / 2 - 0.08, -0.06, low + 0.26))


def hosp_window(a, W=2.6, H=1.45):
    f = 0.06
    for lo, hi in (((-W / 2 - f, -0.05, -f), (W / 2 + f, 0.05, 0)), ((-W / 2 - f, -0.05, H), (W / 2 + f, 0.05, H + f)),
                   ((-W / 2 - f, -0.05, 0), (-W / 2, 0.05, H)), ((W / 2, -0.05, 0), (W / 2 + f, 0.05, H)),
                   ((-0.03, -0.04, 0), (0.03, 0.04, H))):
        a.lohi(lo, hi, ALU, bevel=0.008)
    for x0, x1 in ((-W / 2, -0.03), (0.03, W / 2)):
        a.lohi((x0, -0.003, 0), (x1, 0.003, H), glass("WindowGlass"))
    a.box((0.03, 0.02, 0.05), (-0.06, -0.05, H * 0.45), A.BRASS, bevel=0.004)
    a.lohi((-W / 2 - 0.12, -0.2, -f - 0.04), (W / 2 + 0.12, 0.0, -f), Surf("stone", "#E2DDD2", "#B8B2A6", rough=0.4,
                                                                             scale=2.0, name="Sill"), bevel=0.01)


def privacy_curtain(a):
    """Ceiling track around the bed with the curtain bunched at the foot corner."""
    x0, x1, y0, y1 = -1.25, 1.35, -0.75, 0.75
    z = 2.75
    pts = [(x1, y0, z), (x0, y0, z), (x0, y1, z)]          # the curtain is bunched at the far foot corner
    a.tube([Vector(p) for p in pts], 0.018, ALU, segs=6)
    for p in pts:
        a.rod(p, (p[0], p[1], 2.8), 0.008, ALU, segs=4)
    a.add(K.extrude(a.bm, _wave_outline(0.85, 10, 0.06, 0.01), 2.0, (0, 0, 0), None), PRIVACY, wobble=0.02,
          grain=(0, 0, 1))
    # the extrude sits at the origin: move that part into the corner, hanging from the track
    part = [f for f in a.bm.faces if f[a.l_part] == a.parts - 1]
    vs = {vv for f in part for vv in f.verts}
    bmesh.ops.transform(a.bm, matrix=Matrix.Translation((x0 + 0.05, y1 - 0.45, z - 1.03)) @
                        Matrix.Rotation(PI / 2, 4, "Z"), verts=list(vs))
    for k in range(10):
        a.cyl(0.012, 0.03, (x0 + 0.02, y1 - 0.06 - k * 0.085, z - 0.025), ALU, segs=6)


def _wave_outline(W, folds, amp, th):
    pts = []
    n = folds * 6
    for k in range(n + 1):
        x = -W / 2 + W * k / n
        pts.append((x, amp * math.sin(2 * PI * folds * k / n)))
    return [(x, y - th) for x, y in pts] + [(x, y + th) for x, y in reversed(pts)]


def overbed_table(a):
    a.lohi((-0.42, -0.2, 0.78), (0.42, 0.2, 0.81), LAMINATE, bevel=0.01, grain=(1, 0, 0))
    a.lohi((0.3, -0.04, 0.12), (0.36, 0.04, 0.78), BED_WHITE, bevel=0.008)
    a.lohi((0.26, -0.3, 0.06), (0.4, 0.3, 0.12), BED_WHITE, bevel=0.01)
    for y in (-0.27, 0.27):
        a.lohi((-0.3, y - 0.03, 0.06), (0.4, y + 0.03, 0.1), BED_WHITE, bevel=0.008)
        for x in (-0.28, 0.37):
            a.cyl(0.028, 0.022, (x, y, 0.03), RUBBER, rot=(PI / 2, 0, 0), segs=10, bevel=0.004)


def sanitizer(a):
    a.lohi((-0.06, -0.09, 0.0), (0.06, 0, 0.22), WHITE_PLASTIC, bevel=0.012)
    a.lohi((-0.045, -0.095, 0.05), (0.045, -0.088, 0.16), glass("SanitizerWindow", "#CFE3EA", 0.1))
    a.lohi((-0.03, -0.1, -0.02), (0.03, -0.06, 0.02), BLACK_PLASTIC, bevel=0.006)


def hosp_sink(a):
    a.lohi((-0.28, -0.42, 0.78), (0.28, 0, 0.86), CERAMIC, bevel=0.03, wobble=0.003)
    a.lathe([(0.0, 0.0), (0.16, 0.0), (0.2, 0.06), (0, 0.065)], Surf("ceramic", "#D9D8D2", rough=0.15, name="Basin"),
            segs=16, loc=(0, -0.22, 0.8))
    a.rod((0, -0.04, 0.86), (0, -0.04, 1.0), 0.016, STAINLESS, segs=8)
    a.tube([(0, -0.04, 1.0), (0, -0.12, 1.02), (0, -0.2, 0.96)], 0.012, STAINLESS, segs=8)
    a.rod((0, -0.04, 0.95), (0.1, -0.06, 0.97), 0.008, STAINLESS, segs=6)
    a.lohi((-0.3, -0.006, 1.1), (0.3, 0, 1.75), mat(M.metal("Mirror", (0.92, 0.93, 0.95), rough=0.02)))
    a.lohi((-0.05, -0.12, 0.3), (0.05, -0.04, 0.78), CERAMIC, bevel=0.02)


BUILDERS = {
    "HospitalBed": (hospital_bed, {}),
    "IVStand": (iv_stand, {}),
    "VitalsMonitor": (vitals_monitor, {}),
    "BedsideCabinet": (bedside_cabinet, {}),
    "FlowerVase": (flower_vase, {}),
    "WaterGlass": (water_glass, {}),
    "Stool": (stool, {}),
    "PaintingFrame": (painting_frame, {}),
    "HospDoor": (hosp_door, {}),
    "CeilingPanel": (lambda a: ceiling_panel(a, False), {}),
    "BedHeadPanel": (bed_head_panel, {}),
    "Blinds": (blinds, {}),
    "HospWindow": (hosp_window, {}),
    "CurtainGreen": (lambda a: A.curtain_panel(a, W=0.75, H=2.3, folds=6, s=CURTAIN_GREEN, seed=3), {}),
    "PrivacyCurtain": (privacy_curtain, {}),
    "OverbedTable": (overbed_table, {}),
    "Sanitizer": (sanitizer, {}),
    "HospSink": (hosp_sink, {}),
}


def get(name):
    fn, kw = BUILDERS[name]
    return K.asset(name, fn, **kw)
