"""The prop library, modelled with the kit (chunky, chamfered, painted).

Conventions: metres; floor-standing assets have their origin at the floor centre and face -Y;
wall-mounted assets have their back on the y = 0 plane and stick out toward -Y. get("Name")
returns the finished mesh (built and baked once per file)."""

import math
import random

import bmesh
from mathutils import Matrix, Vector

from . import decals as D
from . import kit as K
from . import mats as M
from . import texgen as T
from .kit import Surf

PI = math.pi

# ----------------------------------------------------------------- palette

DESK_WOOD = Surf("wood", "#DDB983", "#A9794A", rough=0.55, name="DeskWood")
DOOR_WOOD = Surf("wood", "#C99B66", "#8E623A", rough=0.5, name="DoorWood")
DARK_WOOD = Surf("wood", "#7E5233", "#43281A", rough=0.6, name="DarkWood")
FRAME_STEEL = Surf("paint", "#B5BBBF", "#5A5F63", rough=0.4, metal=0.55, chips=0.3, name="FrameSteel")
TRAY_STEEL = Surf("paint", "#8D959B", "#4A4E52", rough=0.5, metal=0.45, chips=0.3, name="TraySteel")
ALU = Surf("metal", "#C9CDD1", rough=0.32, metal=1.0, edge=0.3, name="Alu")
STAINLESS = Surf("metal", "#D3D6D9", rough=0.2, metal=1.0, edge=0.3, name="Stainless")
DARK_METAL = Surf("paint", "#3A3D41", "#1B1C1E", rough=0.45, metal=0.6, chips=0.2, name="DarkMetal")
LOCKER_STEEL = Surf("paint", "#A9B4BA", "#5F686E", rough=0.42, metal=0.5, chips=0.25, name="LockerSteel")
FIRE_RED = Surf("paint", "#C7262B", "#5C1414", rough=0.38, metal=0.3, chips=0.2, name="FireRed")
DOOR_STEEL = Surf("paint", "#5E7B70", "#3B2A20", rough=0.5, metal=0.45, chips=0.6, grime=0.35, name="DoorSteel")
FENCE_GREEN = Surf("paint", "#2E5B3D", "#4A3020", rough=0.45, metal=0.5, chips=0.45, name="FenceGreen")
TANK_PAINT = Surf("paint", "#DCDFDA", "#7A5236", rough=0.5, metal=0.3, chips=0.7, grime=0.4, name="TankPaint")
AC_PAINT = Surf("paint", "#E2E0D6", "#8D8A80", rough=0.5, chips=0.2, grime=0.35, name="ACPaint")
WHITE_PLASTIC = Surf("paint", "#EAE9E3", "#B5B5AE", rough=0.45, edge=0.15, name="WhitePlastic")
BEIGE_PLASTIC = Surf("paint", "#DCD4C0", "#A39A85", rough=0.5, edge=0.15, name="BeigePlastic")
BLACK_PLASTIC = Surf("paint", "#2A2B2D", "#141415", rough=0.5, edge=0.35, name="BlackPlastic")
RUBBER = Surf("rubber", "#232325", rough=0.85, edge=0.1, name="Rubber")
CONCRETE = Surf("stone", "#ADA89D", "#7E796F", rough=0.85, grime=0.3, name="Concrete")
GRANITE = Surf("stone", "#9C9A96", "#6D6B68", rough=0.6, scale=2.0, name="Granite")
CARDBOARD = Surf("paper", "#B88A57", rough=0.85, edge=0.2, name="Cardboard")
TAPE = Surf("paper", "#C9A672", rough=0.4, edge=0.05, name="Tape")
PAPER = Surf("paper", "#F1EEE4", rough=0.8, edge=0.05, name="Paper")
CERAMIC = Surf("ceramic", "#ECEBE6", rough=0.2, edge=0.2, name="Ceramic")
COPPER = Surf("metal", "#B87346", rough=0.35, metal=1.0, name="Copper")
BRASS = Surf("metal", "#C8B88C", rough=0.3, metal=1.0, name="Brass")
LEAF_GREEN = Surf("leaf", "#6E9A3A", "#22401A", rough=0.75, edge=0.0, ao=0.6, var=0.12, sss=0.1, name="Hedge")
CURTAIN_RED = Surf("fabric", "#7B1F25", rough=0.9, sheen=0.4, edge=0.0, ao=0.6, name="CurtainRed")
ORANGE_PAINT = Surf("paint", "#E8742A", "#6E3418", rough=0.45, chips=0.3, name="OrangePaint")
POST_RED = Surf("paint", "#D3242A", "#5A1414", rough=0.35, chips=0.25, name="PostRed")


def glass(name="WindowGlass", tint="#E9F3F6", rough=0.03):
    return Surf("glass", tint, rough=rough, name=name)


def glow(name, color, strength):
    return Surf("glow", color, strength=strength, name=name)


def mat(material):
    return Surf("mat", material=material, name=material.name)


def tile(name, gen, scale, rough=0.7, **kw):
    return Surf("tile", material=T.tile_material(name, gen, rough=rough, **kw), scale=scale, name=name)


def decal(name, gen, *args, rough=0.6, emit=0.0, metal=0.0, alpha_black=False, **kw):
    img = D.image(name, gen, *args, **kw)
    return Surf("decal", material=D.decal_material(name, img, rough=rough, emit=emit, metal=metal,
                                                   alpha_black=alpha_black), name=name)


# ----------------------------------------------------------------- classroom furniture

def school_desk(a):
    """Japanese classroom desk: birch top, open steel book box, round-tube frame."""
    W, D_, H, T_ = 0.66, 0.46, 0.71, 0.032
    a.box((W, D_, T_), (0, 0, H - T_ / 2), DESK_WOOD, bevel=0.008, wobble=0.003, grain=(1, 0, 0))
    tz = H - T_ - 0.115
    a.box((W - 0.09, D_ - 0.07, 0.01), (0, 0.012, tz), TRAY_STEEL, bevel=0.003)
    a.box((W - 0.09, 0.01, 0.11), (0, D_ / 2 - 0.023, tz + 0.055), TRAY_STEEL, bevel=0.003)
    for sx in (-1, 1):
        a.box((0.01, D_ - 0.07, 0.11), (sx * (W / 2 - 0.045), 0.012, tz + 0.055), TRAY_STEEL, bevel=0.003)
    leg_h = H - T_
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.03)
        for sy in (-1, 1):
            y = sy * (D_ / 2 - 0.035)
            a.cyl(0.0145, leg_h - 0.02, (x, y, 0.02 + (leg_h - 0.02) / 2), FRAME_STEEL, bevel=0.004, wobble=0.002)
            a.cyl(0.019, 0.022, (x, y, 0.011), RUBBER, bevel=0.004)
        a.rod((x, -D_ / 2 + 0.035, leg_h - 0.018), (x, D_ / 2 - 0.035, leg_h - 0.018), 0.012, FRAME_STEEL, bevel=0.003)
        a.rod((x, -D_ / 2 + 0.035, 0.15), (x, D_ / 2 - 0.035, 0.15), 0.012, FRAME_STEEL, bevel=0.003)
    a.rod((-W / 2 + 0.03, D_ / 2 - 0.035, 0.15), (W / 2 - 0.03, D_ / 2 - 0.035, 0.15), 0.012, FRAME_STEEL, bevel=0.003)
    hx = W / 2 - 0.03
    a.tube([(hx, -0.08, leg_h - 0.03), (hx + 0.03, -0.08, leg_h - 0.05), (hx + 0.035, -0.08, leg_h - 0.1),
            (hx + 0.055, -0.08, leg_h - 0.075)], 0.0055, FRAME_STEEL)


def school_chair(a):
    """Matching chair: dished plywood seat and backrest on a bent-tube frame."""
    SW, SD, SH, T_ = 0.40, 0.38, 0.43, 0.022
    seat = K.box(a.bm, (SW, SD, T_), (0, 0, SH - T_ / 2))
    for v in seat:
        v.co.z -= 0.012 * (1 - (2 * v.co.x / SW) ** 2)
    a.add(seat, DESK_WOOD, bevel=0.007, wobble=0.002, grain=(1, 0, 0))
    back = K.box(a.bm, (SW - 0.02, 0.018, 0.19), (0, 0, 0))
    for v in back:
        v.co.y += 0.03 * (2 * v.co.x / SW) ** 2
    bmesh.ops.transform(a.bm, matrix=Matrix.Translation((0, SD / 2 + 0.03, SH + 0.31)) @
                        Matrix.Rotation(math.radians(-9), 4, "X"), verts=back)
    a.add(back, DESK_WOOD, bevel=0.006, wobble=0.002, grain=(1, 0, 0))
    for sx in (-1, 1):
        x = sx * (SW / 2 - 0.025)
        a.rod((x, -SD / 2 + 0.03, 0.02), (x, -SD / 2 + 0.03, SH - T_), 0.012, FRAME_STEEL, bevel=0.003, wobble=0.0015)
        a.tube([(x, SD / 2 - 0.02, 0.02), (x, SD / 2 - 0.005, SH - 0.05), (x, SD / 2 + 0.012, SH + 0.1),
                (x, SD / 2 + 0.045, SH + 0.4)], 0.012, FRAME_STEEL, segs=8, wobble=0.0015)
        a.rod((x, -SD / 2 + 0.03, SH - T_ - 0.015), (x, SD / 2 - 0.01, SH - T_ - 0.015), 0.011, FRAME_STEEL, bevel=0.003)
        a.rod((x, -SD / 2 + 0.03, 0.13), (x, SD / 2 - 0.018, 0.13), 0.01, FRAME_STEEL, bevel=0.003)
        for y in (-SD / 2 + 0.03, SD / 2 - 0.02):
            a.cyl(0.016, 0.02, (x, y, 0.01), RUBBER, bevel=0.003)
    a.rod((-SW / 2 + 0.025, -SD / 2 + 0.03, 0.2), (SW / 2 - 0.025, -SD / 2 + 0.03, 0.2), 0.01, FRAME_STEEL, bevel=0.003)


# ----------------------------------------------------------------- windows and doors

WIN_W, WIN_H = 3.4, 2.05


def _win_layout(W=WIN_W, H=WIN_H):
    f = 0.065
    zt = H * 0.74
    sw = (W - 2 * f) / 4 + 0.03
    xs = [-W / 2 + f + sw / 2 + k * (W - 2 * f - sw) / 3 for k in range(4)]
    ys = [-0.018 if k % 2 == 0 else 0.018 for k in range(4)]
    return f, zt, sw, xs, ys


def window4(a, W=WIN_W, H=WIN_H):
    """School window bay: chunky aluminium frame, four sliding sashes, four top lights."""
    f, zt, sw, xs, ys = _win_layout(W, H)
    a.lohi((-W / 2, -0.05, 0), (W / 2, 0.05, f), ALU, bevel=0.008)
    a.lohi((-W / 2, -0.05, H - f), (W / 2, 0.05, H), ALU, bevel=0.008)
    for sx in (-1, 1):
        a.lohi((sx * W / 2 - (f if sx > 0 else 0), -0.05, f), (sx * W / 2 + (0 if sx > 0 else f), 0.05, H - f), ALU,
               bevel=0.008)
    a.lohi((-W / 2 + f, -0.04, zt - 0.03), (W / 2 - f, 0.04, zt + 0.03), ALU, bevel=0.007)
    s = 0.045
    for x, y in zip(xs, ys):
        z0, z1 = f, zt - 0.03
        for lo, hi in (((x - sw / 2, y - 0.014, z0), (x + sw / 2, y + 0.014, z0 + s)),
                       ((x - sw / 2, y - 0.014, z1 - s), (x + sw / 2, y + 0.014, z1)),
                       ((x - sw / 2, y - 0.014, z0 + s), (x - sw / 2 + s, y + 0.014, z1 - s)),
                       ((x + sw / 2 - s, y - 0.014, z0 + s), (x + sw / 2, y + 0.014, z1 - s))):
            a.lohi(lo, hi, ALU, bevel=0.005)
    for k in range(1, 4):
        x = -W / 2 + f + (W - 2 * f) * k / 4
        a.lohi((x - 0.022, -0.035, zt + 0.03), (x + 0.022, 0.035, H - f), ALU, bevel=0.005)
    for k in (0, 2):                                  # crescent latches where the sashes meet
        x = (xs[k] + sw / 2 + xs[k + 1] - sw / 2) / 2
        a.box((0.035, 0.016, 0.022), (x, ys[k] - 0.022, zt * 0.55), BRASS, bevel=0.004)


def window4_glass(a, clear=True, W=WIN_W, H=WIN_H):
    f, zt, sw, xs, ys = _win_layout(W, H)
    g = glass("WindowGlass") if clear else Surf("mat", material=M.dark_glass("WindowGlassDark"), name="WindowGlassDark")
    s = 0.045
    for x, y in zip(xs, ys):
        a.lohi((x - sw / 2 + s * 0.6, y - 0.003, f + s * 0.6), (x + sw / 2 - s * 0.6, y + 0.003, zt - 0.03 - s * 0.6), g)
    for k in range(4):
        x0 = -W / 2 + f + (W - 2 * f) * k / 4 + 0.015
        x1 = -W / 2 + f + (W - 2 * f) * (k + 1) / 4 - 0.015
        a.lohi((x0, -0.003, zt + 0.03), (x1, 0.003, H - f), g)


def class_door_pair(a, W=1.8, H=2.0):
    """Two sliding classroom doors in their tracks (front = -Y, which faces the corridor)."""
    lw = W / 2 + 0.02
    g = glass("DoorGlass")
    pull = DARK_METAL
    for k, (x, y) in enumerate(((-W / 4 - 0.01, -0.012), (W / 4 + 0.01, 0.012))):
        x0, x1 = x - lw / 2, x + lw / 2
        t = 0.038
        st = 0.075
        for lo, hi in (((x0, y - t / 2, 0.0), (x0 + st, y + t / 2, H)), ((x1 - st, y - t / 2, 0.0), (x1, y + t / 2, H)),
                       ((x0 + st, y - t / 2, H - 0.09), (x1 - st, y + t / 2, H)),
                       ((x0 + st, y - t / 2, 0.98), (x1 - st, y + t / 2, 1.08)),
                       ((x0 + st, y - t / 2, 0.0), (x1 - st, y + t / 2, 0.16))):
            a.lohi(lo, hi, DOOR_WOOD, bevel=0.006, wobble=0.002)
        a.lohi((x0 + st, y - 0.008, 0.16), (x1 - st, y + 0.008, 0.98), DOOR_WOOD, bevel=0.003, grain=(0, 0, 1))
        a.lohi((x0 + st, y - 0.004, 1.08), (x1 - st, y + 0.004, H - 0.09), g)
        px = x1 - 0.045 if k == 0 else x0 + 0.045
        for side in (-1, 1):
            a.box((0.032, 0.006, 0.15), (px, y + side * (t / 2 + 0.002), 0.95), pull, bevel=0.003)
    a.lohi((-W / 2 - 0.08, -0.05, H), (W / 2 + 0.08, 0.05, H + 0.07), DARK_WOOD, bevel=0.008)
    a.lohi((-W / 2 - 0.08, -0.04, -0.005), (W / 2 + 0.08, 0.04, 0.012), ALU, bevel=0.004)
    a.lohi((-W / 2 - 0.08, -0.05, 0), (-W / 2, 0.05, H), DARK_WOOD, bevel=0.008)
    a.lohi((W / 2, -0.05, 0), (W / 2 + 0.08, 0.05, H), DARK_WOOD, bevel=0.008)


def steel_door(a, W=1.0, H=2.15, part="all"):
    """Weathered steel door in its frame (rooftop stair hut). Front = -Y (outside).
    part: "frame" or "leaf" builds just that piece (the leaf swings on hinges at x = -W/2)."""
    fw = 0.07
    if part in ("all", "frame"):
        for lo, hi in (((-W / 2 - fw, -0.07, 0), (-W / 2, 0.07, H + fw)), ((W / 2, -0.07, 0), (W / 2 + fw, 0.07, H + fw)),
                       ((-W / 2, -0.07, H), (W / 2, 0.07, H + fw))):
            a.lohi(lo, hi, DOOR_STEEL, bevel=0.01)
    if part == "frame":
        return
    lw, lh = W - 0.02, H - 0.02
    a.lohi((-lw / 2, -0.03, 0.01), (lw / 2, 0.015, lh), DOOR_STEEL, bevel=0.008, wobble=0.002)
    for z0, z1 in ((0.32, 1.0), (1.12, 1.45)):
        a.lohi((-lw / 2 + 0.1, -0.038, z0), (lw / 2 - 0.1, -0.03, z1), DOOR_STEEL, bevel=0.006)
    a.lohi((-0.15, -0.034, 1.55), (0.15, -0.026, 1.95), glass("WiredGlass", "#C9D6D2", 0.15))
    for lo, hi in (((-0.18, -0.04, 1.52), (0.18, -0.03, 1.55)), ((-0.18, -0.04, 1.95), (0.18, -0.03, 1.98)),
                   ((-0.18, -0.04, 1.55), (-0.15, -0.03, 1.95)), ((0.15, -0.04, 1.55), (0.18, -0.03, 1.95))):
        a.lohi(lo, hi, DOOR_STEEL, bevel=0.004)
    a.lohi((-lw / 2 + 0.02, -0.036, 0.03), (lw / 2 - 0.02, -0.03, 0.26), STAINLESS, bevel=0.003)
    hx = lw / 2 - 0.09
    a.cyl(0.035, 0.012, (hx, -0.036, 1.02), STAINLESS, rot=(PI / 2, 0, 0), bevel=0.004)
    a.rod((hx, -0.04, 1.02), (hx, -0.075, 1.02), 0.01, STAINLESS)
    a.rod((hx, -0.075, 1.02), (hx - 0.12, -0.075, 1.0), 0.011, STAINLESS, bevel=0.003)
    for z in (0.25, 1.05, 1.85):
        a.cyl(0.014, 0.12, (-lw / 2 - 0.01, -0.02, z), DARK_METAL, bevel=0.003)


# ----------------------------------------------------------------- corridor furniture

def locker_bank(a, cols=4, rows=3):
    w, h, D_ = 0.3, 0.36, 0.45
    W, H = cols * w, rows * h
    base = 0.08
    a.lohi((-W / 2, -D_ + 0.02, base), (W / 2, 0, base + H), LOCKER_STEEL, bevel=0.006)
    a.lohi((-W / 2 + 0.02, -D_ + 0.04, 0), (W / 2 - 0.02, -0.02, base), DARK_METAL, bevel=0.005)
    a.lohi((-W / 2 - 0.01, -D_ + 0.01, base + H), (W / 2 + 0.01, 0.005, base + H + 0.025), LOCKER_STEEL, bevel=0.006)
    vent = DARK_METAL
    for c in range(cols):
        for r in range(rows):
            x = -W / 2 + w * (c + 0.5)
            z = base + h * (r + 0.5)
            a.box((w - 0.012, 0.016, h - 0.012), (x, -D_ + 0.012, z), LOCKER_STEEL, bevel=0.005, wobble=0.0015)
            for k in range(3):
                a.box((0.13, 0.004, 0.012), (x, -D_ + 0.002, z + h * 0.28 - k * 0.024), vent, bevel=0.002)
            a.box((0.022, 0.012, 0.07), (x + w * 0.33, -D_ + 0.0, z - 0.02), STAINLESS, bevel=0.004)
            a.box((0.06, 0.004, 0.025), (x - w * 0.22, -D_ + 0.002, z - h * 0.32), WHITE_PLASTIC, bevel=0.002)


def notice_board(a, W=1.8, H=0.9, seed=0):
    a.lohi((-W / 2, -0.02, 0), (W / 2, 0, H), tile("Cork", "cork", 0.6, rough=0.9))
    f = 0.03
    for lo, hi in (((-W / 2 - f, -0.035, -f), (W / 2 + f, 0, 0)), ((-W / 2 - f, -0.035, H), (W / 2 + f, 0, H + f)),
                   ((-W / 2 - f, -0.035, 0), (-W / 2, 0, H)), ((W / 2, -0.035, 0), (W / 2 + f, 0, H))):
        a.lohi(lo, hi, ALU, bevel=0.005)
    rnd = random.Random(seed)
    pin_cols = [Surf("paint", c, rough=0.3, edge=0.3, name="Pin" + c[1:]) for c in ("#D23A3A", "#3A6AD2", "#E8C53A")]
    xs = [-W / 2 + 0.25 + k * (W - 0.5) / 3 for k in range(4)]
    for k, x in enumerate(xs):
        pw, ph = 0.26, 0.36
        z = H / 2 + rnd.uniform(-0.12, 0.08)
        ang = rnd.uniform(-0.05, 0.05)
        s = decal(f"Notice{seed}_{k}", "notice", seed * 10 + k, rough=0.85)
        a.plane(pw, ph, (x + rnd.uniform(-0.05, 0.05), -0.0215, z), s, rot=(0, ang, 0))
        for px in (-1, 1):
            a.cyl(0.008, 0.012, (x + px * pw * 0.38, -0.028, z + ph * 0.44), rnd.choice(pin_cols), rot=(PI / 2, 0, 0), segs=8)


def poster(a, idx=0):
    pw, ph = 0.52, 0.73
    a.plane(pw, ph, (0, -0.002, ph / 2), decal(f"Poster{idx}", "poster", idx, rough=0.5))
    for sx in (-1, 1):
        for sz in (0, 1):
            a.box((0.06, 0.002, 0.025), (sx * (pw / 2 - 0.01), -0.003, sz * ph + (0.0 if sz else 0.0)), TAPE,
                  rot=(0, sx * (0.7 if sz else -0.7), 0))


def hydrant_box(a):
    W, H, D_ = 0.78, 1.05, 0.18
    a.lohi((-W / 2, -D_, 0), (W / 2, 0, H), FIRE_RED, bevel=0.012)
    a.lohi((-W / 2 + 0.05, -D_ - 0.006, 0.08), (W / 2 - 0.05, -D_ + 0.002, H - 0.3), STAINLESS, bevel=0.006)
    a.box((0.025, 0.02, 0.14), (W / 2 - 0.1, -D_ - 0.014, 0.45), DARK_METAL, bevel=0.004)
    a.plane(0.5, 0.17, (0, -D_ - 0.0035, H - 0.17),
            decal("HydrantLabel", "plate", "消火栓", 512, 176, (205, 30, 32), (255, 255, 255), 120, (150, 20, 20), rough=0.4))
    a.cyl(0.07, 0.06, (0, -0.06, H + 0.1), FIRE_RED, rot=(PI / 2, 0, 0), segs=16, bevel=0.01)
    a.lathe([(0, 0), (0.05, 0.0), (0.06, 0.03), (0.045, 0.07), (0, 0.08)], glow("AlarmLamp", "#FF2A12", 3.0),
            segs=12, loc=(0, -0.03, H + 0.17), rot=(PI / 2, 0, 0))
    a.lathe([(0, 0), (0.11, 0), (0.12, 0.03), (0.08, 0.07), (0, 0.075)], FIRE_RED, segs=16,
            loc=(0, 0, H + 0.33), rot=(PI / 2, 0, 0), bevel=0.005)


def sink_trough(a, L=3.2):
    D_, H = 0.45, 0.78
    a.lohi((-L / 2, -D_ + 0.03, 0), (L / 2, 0, H - 0.18), CONCRETE, bevel=0.02, wobble=0.004)
    t = 0.012
    z0 = H - 0.2
    for lo, hi in (((-L / 2, -D_, z0), (L / 2, 0, z0 + t)), ((-L / 2, -D_, z0), (L / 2, -D_ + t, H)),
                   ((-L / 2, -t, z0), (L / 2, 0, H + 0.12)),
                   ((-L / 2, -D_, z0), (-L / 2 + t, 0, H)), ((L / 2 - t, -D_, z0), (L / 2, 0, H))):
        a.lohi(lo, hi, STAINLESS, bevel=0.004)
    a.lohi((-L / 2 - 0.01, -D_ - 0.012, H - 0.01), (L / 2 + 0.01, -D_ + 0.02, H + 0.012), STAINLESS, bevel=0.006)
    n = 4
    for k in range(n):
        x = -L / 2 + L * (k + 0.5) / n
        a.rod((x, -0.012, H + 0.08), (x, -0.13, H + 0.08), 0.013, STAINLESS, segs=8)
        a.rod((x, -0.13, H + 0.085), (x, -0.13, H + 0.02), 0.011, STAINLESS, segs=8)
        a.lathe([(0, 0), (0.022, 0), (0.024, 0.012), (0.012, 0.03), (0, 0.032)], STAINLESS, segs=8,
                loc=(x, -0.06, H + 0.095))
        if k % 2 == 0:
            a.box((0.08, 0.05, 0.03), (x + 0.32, -0.08, H - 0.0), Surf("paint", "#F2D23A", rough=0.4, name="Soap"),
                  bevel=0.008)
    a.lohi((-L / 2 + 0.08, -0.004, H + 0.2), (L / 2 - 0.08, 0, H + 0.82),
           mat(M.metal("Mirror", (0.92, 0.93, 0.95), rough=0.02)))
    for lo, hi in (((-L / 2 + 0.06, -0.014, H + 0.18), (L / 2 - 0.06, 0, H + 0.2)),
                   ((-L / 2 + 0.06, -0.014, H + 0.82), (L / 2 - 0.06, 0, H + 0.84))):
        a.lohi(lo, hi, STAINLESS, bevel=0.003)


BIN_KINDS = {"Burnable": ("#2F68B7", "燃えるゴミ", (40, 100, 190)), "Plastic": ("#E5B931", "プラスチック", (200, 150, 20)),
             "Cans": ("#3E9A4E", "缶・ビン", (40, 140, 70))}


def bin_(a, kind="Burnable"):
    col, label, rgb = BIN_KINDS[kind]
    body = Surf("paint", col, rough=0.45, edge=0.2, grime=0.3, name="Bin" + kind)
    a.lathe([(0, 0), (0.15, 0), (0.158, 0.02), (0.175, 0.5), (0.18, 0.52), (0, 0.52)], body, segs=16, bevel=0.004)
    a.lathe([(0, 0.52), (0.19, 0.52), (0.192, 0.545), (0.17, 0.58), (0.09, 0.6), (0, 0.6)], body, segs=16,
            loc=(0, 0, 0), bevel=0.004)
    a.lohi((-0.09, -0.02, 0.6), (0.09, 0.02, 0.63), BLACK_PLASTIC, bevel=0.006)
    a.plane(0.2, 0.08, (0, -0.172, 0.36),
            decal("BinLabel" + kind, "plate", label, 512, 200, (255, 255, 255), rgb, 80, rgb, rough=0.5),
            rot=(0.04, 0, 0))


def umbrella_stand(a):
    W, D_, H = 0.6, 0.25, 0.5
    for x in (-W / 2, W / 2):
        for y in (-D_ / 2, D_ / 2):
            a.rod((x, y, 0), (x, y, H), 0.012, STAINLESS, segs=8)
    for z in (0.08, H):
        a.rod((-W / 2, -D_ / 2, z), (W / 2, -D_ / 2, z), 0.01, STAINLESS)
        a.rod((-W / 2, D_ / 2, z), (W / 2, D_ / 2, z), 0.01, STAINLESS)
        for k in range(5):
            x = -W / 2 + W * k / 4
            a.rod((x, -D_ / 2, z), (x, D_ / 2, z), 0.008, STAINLESS)
    a.lohi((-W / 2, -D_ / 2, 0.0), (W / 2, D_ / 2, 0.02), DARK_METAL, bevel=0.004)
    for k, (x, c) in enumerate(((-0.17, "#B8232C"), (0.05, "#1F3E8A"), (0.2, "#2B2B2E"))):
        cloth = Surf("fabric", c, rough=0.7, edge=0.0, name="Umbrella" + c[1:])
        rot = Matrix.Rotation(-0.12, 4, "X") @ Matrix.Rotation(0.1 * (k - 1), 4, "Y")
        base = Vector((x, 0, 0.02))
        a.lathe([(0, 0.0), (0.012, 0.02), (0.045, 0.23), (0.05, 0.58), (0.03, 0.78), (0.0, 0.82)], cloth, segs=8,
                loc=base, rot=rot)
        tip = base + rot.to_3x3() @ Vector((0, 0, 0.82))
        a.tube([tip, tip + Vector((0, 0, 0.1)), tip + Vector((0.04, 0, 0.13)), tip + Vector((0.06, 0, 0.08))], 0.012,
               BLACK_PLASTIC)


def wall_clock(a):
    r = 0.17
    a.lathe([(0, 0), (r, 0), (r + 0.012, 0.012), (r + 0.01, 0.05), (r - 0.01, 0.055), (r - 0.012, 0.03), (0, 0.03)],
            WHITE_PLASTIC, segs=24, rot=(PI / 2, 0, 0), bevel=0.003)
    a.add(_disc(a, r - 0.012, (0, -0.031, 0)), decal("ClockFace", "clock_face", rough=0.4))
    hands = Surf("paint", "#1A1A1C", rough=0.4, edge=0.0, name="ClockHands")
    for ang, ln, w in ((math.radians(-60), 0.08, 0.012), (math.radians(60), 0.12, 0.008)):
        c = Vector((math.sin(ang), 0, math.cos(ang)))
        a.box((w, 0.004, ln), (c.x * ln / 2 - 0, -0.035, c.z * ln / 2), hands, rot=(0, ang, 0))
    a.cyl(0.012, 0.01, (0, -0.038, 0), hands, rot=(PI / 2, 0, 0), segs=12)


def _disc(a, r, loc, segs=32):
    bm = a.bm
    vs = [bm.verts.new((loc[0] + math.cos(t) * r, loc[1], loc[2] + math.sin(t) * r))
          for t in (2 * PI * k / segs for k in range(segs))]
    bm.faces.new(vs)                 # counter-clockwise in XZ = facing -Y
    return vs


def pa_speaker(a):
    a.lohi((-0.18, -0.13, -0.13), (0.18, 0, 0.13), BEIGE_PLASTIC, bevel=0.015, wobble=0.002)
    a.lohi((-0.15, -0.136, -0.1), (0.15, -0.12, 0.1), Surf("fabric", "#3B3B3A", rough=0.9, edge=0.0, name="Grille"),
           bevel=0.006)
    a.lohi((-0.04, -0.03, 0.13), (0.04, 0, 0.2), BEIGE_PLASTIC, bevel=0.005)


def ceiling_light(a, on=False):
    L = 1.3
    a.lohi((-L / 2, -0.12, -0.07), (L / 2, 0.12, 0), WHITE_PLASTIC, bevel=0.01)
    tube_s = glow("TubeOn", "#F2F6FF", 9.0) if on else Surf("ceramic", "#EEF1F4", rough=0.2, name="TubeOff")
    for y in (-0.055, 0.055):
        a.rod((-L / 2 + 0.06, y, -0.09), (L / 2 - 0.06, y, -0.09), 0.014, tube_s, segs=10)
        for x in (-L / 2 + 0.04, L / 2 - 0.04):
            a.box((0.04, 0.04, 0.035), (x, y, -0.085), WHITE_PLASTIC, bevel=0.005)


def exit_sign(a):
    a.lohi((-0.22, -0.07, -0.12), (0.22, 0, 0.12), WHITE_PLASTIC, bevel=0.01)
    a.plane(0.4, 0.2, (0, -0.0715, 0), decal("ExitSign", "exit_sign", rough=0.3, emit=3.0))


def extinguisher(a):
    a.lohi((-0.15, -0.15, 0), (0.15, 0.15, 0.06), FIRE_RED, bevel=0.012)
    a.lathe([(0, 0.06), (0.075, 0.06), (0.082, 0.08), (0.082, 0.48), (0.07, 0.53), (0.035, 0.56), (0, 0.565)],
            FIRE_RED, segs=16, bevel=0.004)
    a.lohi((-0.02, -0.02, 0.56), (0.02, 0.02, 0.62), DARK_METAL, bevel=0.004)
    a.lohi((-0.07, -0.012, 0.6), (0.05, 0.012, 0.615), DARK_METAL, bevel=0.003)
    a.cyl(0.022, 0.012, (0.0, -0.03, 0.59), WHITE_PLASTIC, rot=(PI / 2, 0, 0), segs=12)
    a.tube([(0.02, 0, 0.6), (0.09, 0.0, 0.58), (0.1, -0.02, 0.4), (0.09, -0.06, 0.25)], 0.012, RUBBER)
    a.plane(0.09, 0.16, (0, -0.0825, 0.3), decal("ExtLabel", "plate", "消火器", 256, 448, (250, 250, 245), (200, 20, 20), 70,
                                                  (200, 20, 20), rough=0.5), rot=(0, 0, 0))


def class_sign(a, text="2年1組", name="ClassSign"):
    a.lohi((-0.012, -0.5, -0.09), (0.012, -0.05, 0.09), WHITE_PLASTIC, bevel=0.005)
    a.rod((0, 0, 0.05), (0, -0.06, 0.05), 0.008, ALU)
    a.rod((0, 0, -0.05), (0, -0.06, -0.05), 0.008, ALU)
    s = decal(name, "plate", text, 512, 192, (247, 247, 243), (25, 25, 30), 112, (70, 70, 70), rough=0.4)
    a.plane(0.43, 0.165, (0.0125, -0.275, 0), s, rot=(0, 0, PI / 2))
    a.plane(0.43, 0.165, (-0.0125, -0.275, 0), s, rot=(0, 0, -PI / 2))


def chalkboard(a, W=3.6, H=1.2):
    a.lohi((-W / 2, -0.02, 0), (W / 2, 0, H), tile("Chalkboard", "chalkboard", 1.6, rough=0.9, nstrength=2.0))
    a.plane(W - 0.05, H - 0.05, (0, -0.0205, H / 2), decal("ChalkWriting", "chalkboard_writing", rough=0.9,
                                                            alpha_black=True))
    for lo, hi in (((-W / 2 - 0.04, -0.04, -0.04), (W / 2 + 0.04, 0, 0)), ((-W / 2 - 0.04, -0.04, H), (W / 2 + 0.04, 0, H + 0.04)),
                   ((-W / 2 - 0.04, -0.04, 0), (-W / 2, 0, H)), ((W / 2, -0.04, 0), (W / 2 + 0.04, 0, H))):
        a.lohi(lo, hi, ALU, bevel=0.006)
    a.lohi((-W / 2, -0.11, -0.06), (W / 2, -0.02, -0.04), ALU, bevel=0.005)
    a.lohi((-W / 2, -0.11, -0.06), (W / 2, -0.1, -0.02), ALU, bevel=0.003)
    rnd = random.Random(3)
    chalk_cols = ["#F4F2EA", "#F4F2EA", "#F2D94A", "#E8735A", "#7FB7E8"]
    for k in range(6):
        c = chalk_cols[k % len(chalk_cols)]
        x = rnd.uniform(-W / 2 + 0.3, W / 2 - 0.3)
        a.rod((x, -0.07, -0.032), (x + 0.07, -0.065, -0.032), 0.0055, Surf("paper", c, rough=0.95, edge=0.0, name="Chalk" + c[1:]),
              segs=6)
    a.box((0.13, 0.05, 0.035), (W / 2 - 0.4, -0.065, -0.022), DARK_WOOD, bevel=0.006)
    a.box((0.13, 0.05, 0.012), (W / 2 - 0.4, -0.065, -0.044 + 0.006 + 0.0), Surf("fabric", "#5A5E66", rough=0.95,
                                                                                name="Eraser"), bevel=0.003)


# ----------------------------------------------------------------- clubroom

def bookshelf(a, W=1.2, D_=0.36, H=2.0):
    t = 0.025
    a.lohi((-W / 2, -D_, 0), (-W / 2 + t, 0, H), DARK_WOOD, bevel=0.006, wobble=0.003, grain=(0, 0, 1))
    a.lohi((W / 2 - t, -D_, 0), (W / 2, 0, H), DARK_WOOD, bevel=0.006, wobble=0.003, grain=(0, 0, 1))
    a.lohi((-W / 2 - 0.015, -D_ - 0.015, H), (W / 2 + 0.015, 0.005, H + 0.035), DARK_WOOD, bevel=0.008)
    a.lohi((-W / 2 + t, -0.012, 0.0), (W / 2 - t, 0, H), DARK_WOOD, grain=(0, 0, 1))
    a.lohi((-W / 2 + t, -D_ + 0.01, 0.0), (W / 2 - t, -0.01, 0.07), DARK_WOOD, bevel=0.004)
    for z in SHELF_Z:
        a.lohi((-W / 2 + t, -D_ + 0.005, z - 0.022), (W / 2 - t, -0.012, z), DARK_WOOD, bevel=0.004, wobble=0.002,
               grain=(1, 0, 0))


SHELF_Z = [0.09, 0.47, 0.85, 1.23, 1.61]           # tops of the shelf boards


BOOK_COLS = ["#7A1E22", "#1E3D6E", "#2F5B32", "#8A6A2A", "#4A2A55", "#2A2A2E", "#B5562C", "#D6CDB5"]


def book_row(a, L=1.1, seed=0):
    rnd = random.Random(seed)
    covers = [Surf("paint", c, rough=0.55, edge=0.35, var=0.15, name="Book" + c[1:]) for c in BOOK_COLS]
    x = -L / 2
    while x < L / 2 - 0.05:
        w = rnd.uniform(0.025, 0.06)
        h = rnd.uniform(0.21, 0.31)
        d = rnd.uniform(0.17, 0.24)
        lean = 0.0
        if x > L / 2 - 0.25 and rnd.random() < 0.5:
            lean = rnd.uniform(0.15, 0.35)
        rot = (0, lean, 0)
        cx = x + w / 2 + (h / 2) * math.sin(lean)
        a.box((w, d, h), (cx, -0.02 - d / 2, h / 2 * math.cos(lean)), rnd.choice(covers), rot=rot, bevel=0.003)
        if rnd.random() < 0.5:
            a.box((w * 0.7, 0.002, 0.03), (cx, -0.02 - d - 0.001, h * 0.78), PAPER, rot=rot)
        x += w + rnd.uniform(0.0, 0.008)
        if lean > 0:
            break
        if rnd.random() < 0.05:
            x += rnd.uniform(0.05, 0.12)


def specimen_jar(a, seed=0):
    rnd = random.Random(seed)
    r = rnd.uniform(0.06, 0.08)
    h = rnd.uniform(0.16, 0.24)
    a.lathe([(0, 0), (r, 0), (r + 0.004, 0.01), (r + 0.004, h - 0.02), (r - 0.012, h), (0, h)], glass("JarGlass", "#D9EBE0", 0.05),
            segs=12)
    liquid = Surf("mat", material=M.glass("JarLiquid", tint=(0.55, 0.62, 0.3), reflect=0.05, rough=0.2), name="JarLiquid")
    a.lathe([(0, 0.006), (r - 0.004, 0.006), (r - 0.004, h * 0.75), (0, h * 0.75)], liquid, segs=12)
    a.blob((r * 0.9, r * 0.7, h * 0.35), (0, 0, h * 0.35), Surf("rubber", "#5A4A3A", rough=0.6, name="Specimen"),
           wobble=r * 0.25, jitter=0.004)
    a.lathe([(0, h - 0.005), (r - 0.006, h - 0.005), (r - 0.002, h + 0.012), (r - 0.012, h + 0.03), (0, h + 0.032)],
            Surf("metal", "#7C756A", rough=0.5, metal=1.0, chips=0.0, name="JarLid"), segs=12)


def cardboard_box(a, size=(0.5, 0.38, 0.32)):
    w, d, h = size
    v = K.box(a.bm, (w, d, h), (0, 0, h / 2))
    for p in v:                                       # slightly bulged, slightly saggy
        if p.co.z > h * 0.9:
            p.co.z -= 0.01
    a.add(v, CARDBOARD, bevel=0.008, wobble=0.006, jitter=0.002)
    a.box((w + 0.004, 0.06, 0.003), (0, 0, h + 0.0005 - 0.008), TAPE, bevel=0.0)
    for sx in (-1, 1):
        a.box((0.003, 0.06, 0.1), (sx * (w / 2 + 0.002), 0, h - 0.06), TAPE)


def curtain_panel(a, W=1.1, H=2.4, folds=7, s=None, seed=0):
    rnd = random.Random(seed)
    s = s or CURTAIN_RED
    pts = []
    n = folds * 6
    for k in range(n + 1):
        x = -W / 2 + W * k / n
        y = 0.045 * math.sin(2 * PI * folds * k / n + rnd.uniform(-0.2, 0.2))
        pts.append((x, y))
    th = 0.012
    outline = [(x, y - th) for x, y in pts] + [(x, y + th) for x, y in reversed(pts)]
    v = K.extrude(a.bm, outline, H, (0, 0, H / 2), None)
    for p in v:                                     # hem flares a little at the bottom
        t = 1 - p.co.z / H
        p.co.y *= 1 + 0.6 * t
        p.co.x *= 1 + 0.05 * t
    a.add(v, s, wobble=0.012, grain=(0, 0, 1))


def magic_circle_paper(a):
    a.plane(0.9, 0.9, (0, 0, 0.0015), decal("MagicCircle", "magic_circle", rough=0.85), rot=(-PI / 2, 0, 0))


# ----------------------------------------------------------------- rooftop

FENCE_H = 2.1


def fence_panel(a, W=2.4):
    p = 0.035
    a.cyl(p, FENCE_H, (-W / 2, 0, FENCE_H / 2), FENCE_GREEN, segs=10, bevel=0.006, wobble=0.004)
    a.lathe([(0, 0), (p + 0.006, 0), (p + 0.004, 0.02), (0.01, 0.045), (0, 0.047)], FENCE_GREEN, segs=10,
            loc=(-W / 2, 0, FENCE_H))
    for z in (0.08, FENCE_H - 0.06):
        a.rod((-W / 2, 0, z), (W / 2, 0, z), 0.022, FENCE_GREEN, segs=8, wobble=0.004)
    a.plane(W, FENCE_H - 0.1, (0, 0, FENCE_H / 2), mat(M.chainlink("ChainLink")))


def fence_post(a):
    p = 0.035
    a.cyl(p, FENCE_H, (0, 0, FENCE_H / 2), FENCE_GREEN, segs=10, bevel=0.006, wobble=0.004)
    a.lathe([(0, 0), (p + 0.006, 0), (p + 0.004, 0.02), (0.01, 0.045), (0, 0.047)], FENCE_GREEN, segs=10,
            loc=(0, 0, FENCE_H))


def cage_lamp(a, on=True):
    a.cyl(0.08, 0.025, (0, -0.012, 0), DARK_METAL, rot=(PI / 2, 0, 0), segs=12, bevel=0.005)
    a.rod((0, -0.02, 0), (0, -0.09, 0), 0.025, DARK_METAL, segs=10)
    a.lathe([(0, 0), (0.06, 0.0), (0.075, 0.06), (0.06, 0.13), (0, 0.15)],
            glow("CageBulb", "#FFD9A0", 14.0) if on else glass("CageGlass", "#F0EEE8", 0.1), segs=12,
            loc=(0, -0.16, -0.02), rot=(PI / 2, 0, 0))
    for k in range(6):
        t = 2 * PI * k / 6
        x, z = math.cos(t) * 0.085, math.sin(t) * 0.085
        a.rod((x, -0.09, z), (x * 0.6, -0.235, z * 0.6), 0.004, DARK_METAL, segs=4)
    a.add(K.tube(a.bm, [(math.cos(t) * 0.085, -0.17, math.sin(t) * 0.085) for t in
                        (2 * PI * k / 12 for k in range(13))], 0.004, 4, cap=False), DARK_METAL)


def water_tank(a):
    R, TH, LEG = 1.25, 2.4, 1.4
    a.lathe([(0, LEG + 0.12), (R - 0.05, LEG + 0.12), (R, LEG + 0.17), (R, LEG + 0.12 + TH - 0.25),
             (R - 0.12, LEG + 0.12 + TH - 0.08), (0.55, LEG + 0.12 + TH + 0.06), (0, LEG + 0.12 + TH + 0.08)],
            TANK_PAINT, segs=28, wobble=0.01)
    for z in (LEG + 0.75, LEG + 1.6):
        a.lathe([(R - 0.01, z - 0.03), (R + 0.025, z - 0.02), (R + 0.025, z + 0.02), (R - 0.01, z + 0.03)],
                TANK_PAINT, segs=28)
    a.cyl(0.32, 0.08, (0.3, 0.2, LEG + 0.12 + TH + 0.1), TANK_PAINT, segs=14, bevel=0.015)
    for sx in (-1, 1):
        for sy in (-1, 1):
            a.box((0.12, 0.12, LEG), (sx * 0.95, sy * 0.95, LEG / 2), FENCE_GREEN, bevel=0.012, wobble=0.005)
            a.box((0.26, 0.26, 0.02), (sx * 0.95, sy * 0.95, 0.01), FENCE_GREEN, bevel=0.005)
    a.lohi((-1.12, -1.12, LEG), (1.12, 1.12, LEG + 0.12), FENCE_GREEN, bevel=0.012)
    for sx in (-1, 1):
        a.rod((sx * 0.95, -0.95, 0.15), (sx * 0.95, 0.95, LEG - 0.1), 0.02, FENCE_GREEN, segs=6)
        a.rod((-0.95, sx * 0.95, 0.15), (0.95, sx * 0.95, LEG - 0.1), 0.02, FENCE_GREEN, segs=6)
    lx = R + 0.18
    for y in (-0.22, 0.22):
        a.rod((lx, y, 0.0), (lx, y, LEG + TH + 0.3), 0.022, DARK_METAL, segs=8, wobble=0.004)
        a.rod((lx, y, LEG + TH * 0.5), (R - 0.02, y, LEG + TH * 0.5), 0.015, DARK_METAL, segs=6)
    for k in range(int((LEG + TH + 0.2) / 0.3)):
        z = 0.25 + k * 0.3
        a.rod((lx, -0.22, z), (lx, 0.22, z), 0.012, DARK_METAL, segs=6)
    a.tube([(-0.5, -0.6, LEG + 0.12), (-0.5, -0.6, 0.6), (-0.5, -1.5, 0.2), (-0.5, -2.0, 0.2)], 0.06, TANK_PAINT, segs=10)


def ac_unit(a):
    W, D_, H = 0.86, 0.32, 0.66
    a.lohi((-W / 2, -D_ / 2, 0.06), (W / 2, D_ / 2, 0.06 + H), AC_PAINT, bevel=0.018, wobble=0.003)
    for sx in (-1, 1):
        a.lohi((sx * W * 0.38 - 0.05, -D_ / 2 - 0.02, 0), (sx * W * 0.38 + 0.05, D_ / 2 + 0.02, 0.06), DARK_METAL, bevel=0.008)
    cx, cz = -0.1, 0.06 + H / 2
    a.cyl(0.25, 0.012, (cx, -D_ / 2 - 0.004, cz), DARK_METAL, rot=(PI / 2, 0, 0), segs=24)
    for k in range(9):
        z = cz - 0.24 + k * 0.06
        hw = math.sqrt(max(0.0, 0.25 ** 2 - (z - cz) ** 2))
        if hw > 0.02:
            a.rod((cx - hw, -D_ / 2 - 0.016, z), (cx + hw, -D_ / 2 - 0.016, z), 0.005, DARK_METAL, segs=4)
    a.cyl(0.04, 0.03, (cx, -D_ / 2 - 0.02, cz), DARK_METAL, rot=(PI / 2, 0, 0), segs=12)
    for k in range(8):
        z = 0.14 + k * 0.065
        a.box((0.006, D_ * 0.8, 0.03), (W / 2 + 0.004, 0, z), AC_PAINT, rot=(0, 0.4, 0))
    a.box((0.1, 0.004, 0.04), (0.3, -D_ / 2 - 0.004, 0.06 + H - 0.08), STAINLESS)
    a.tube([(W / 2 - 0.05, D_ / 2 - 0.05, 0.2), (W / 2 + 0.12, D_ / 2 - 0.05, 0.2), (W / 2 + 0.15, D_ / 2 - 0.05, 0.05)],
           0.025, RUBBER, segs=8)


def roof_vent(a):
    a.cyl(0.13, 0.04, (0, 0, 0.02), CONCRETE, segs=12, bevel=0.01)
    a.cyl(0.08, 0.8, (0, 0, 0.42), TANK_PAINT, segs=12, bevel=0.006, wobble=0.004)
    a.lathe([(0, 0.0), (0.16, 0.0), (0.22, 0.04), (0.16, 0.11), (0, 0.13)], TANK_PAINT, segs=14,
            loc=(0, 0, 0.86), bevel=0.006)
    for k in range(4):
        t = 2 * PI * k / 4
        a.rod((math.cos(t) * 0.07, math.sin(t) * 0.07, 0.82), (math.cos(t) * 0.17, math.sin(t) * 0.17, 0.88),
              0.008, TANK_PAINT, segs=4)


def downpipe(a, h=14.8):
    s = Surf("paint", "#9AA09E", "#5B5047", rough=0.45, metal=0.3, chips=0.4, grime=0.3, name="Downpipe")
    a.lathe([(0, 0), (0.12, 0), (0.12, 0.12), (0.06, 0.25), (0.06, 0.3), (0, 0.3)], s, segs=10, loc=(0, -0.12, h - 0.3))
    a.cyl(0.055, h - 0.4, (0, -0.12, (h - 0.4) / 2 + 0.1), s, segs=10, bevel=0.004, wobble=0.004)
    a.tube([(0, -0.12, 0.12), (0, -0.12, 0.02), (0, -0.3, -0.03)], 0.055, s, segs=10)
    for k in range(int(h / 2.0)):
        z = 1.2 + k * 2.0
        a.cyl(0.07, 0.04, (0, -0.12, z), s, segs=10, bevel=0.005)
        a.box((0.02, 0.1, 0.03), (0, -0.05, z), s, bevel=0.004)


# ----------------------------------------------------------------- grounds and street

def gate_post(a):
    a.box((0.9, 0.9, 2.6), (0, 0, 1.3), GRANITE, bevel=0.025, wobble=0.004)
    a.box((1.02, 1.02, 0.14), (0, 0, 2.67), GRANITE, bevel=0.03, wobble=0.004)
    a.box((0.98, 0.98, 0.12), (0, 0, 0.06), GRANITE, bevel=0.02)


def name_plate(a):
    a.box((0.34, 0.03, 1.3), (0, -0.015, 0.65), DARK_WOOD, bevel=0.01)
    a.plane(0.3, 1.25, (0, -0.031, 0.65),
            decal("SchoolName", "vplate", "杉沢第三高等学校", rough=0.35, metal=0.7))


def rolling_gate(a, L=4.0, H=1.6):
    s = Surf("metal", "#B9BDC0", rough=0.4, metal=1.0, name="GateSteel")
    for z in (0.12, H - 0.05):
        a.rod((-L / 2, 0, z), (L / 2, 0, z), 0.03, s, segs=8, bevel=0.004)
    n = int(L / 0.18)
    for k in range(n + 1):
        x = -L / 2 + L * k / n
        a.rod((x, 0, 0.12), (x, 0, H - 0.05), 0.012, s, segs=6)
    for k in range(4):
        x0 = -L / 2 + L * k / 4
        a.rod((x0, 0, 0.12), (x0 + L / 4, 0, H - 0.05), 0.015, s, segs=6)
    for x in (-L / 2 + 0.2, L / 2 - 0.2):
        a.cyl(0.07, 0.04, (x, 0, 0.07), RUBBER, rot=(PI / 2, 0, 0), segs=12, bevel=0.008)


def hedge(a, size=(2.0, 0.8, 0.9), seed=0):
    rnd = random.Random(seed)
    w, d, h = size
    a.blob((w, d, h), (0, 0, h / 2), LEAF_GREEN, subdiv=3, wobble=0.12, jitter=0.03, wfreq=2.2)
    for k in range(3):
        a.blob((w * 0.35, d * 0.8, h * 0.45), (rnd.uniform(-w / 3, w / 3), rnd.uniform(-0.05, 0.05), h * 0.82),
               LEAF_GREEN, subdiv=2, wobble=0.06, jitter=0.02)


def utility_pole(a, H=11.0, transformer=False):
    con = Surf("stone", "#9E9B94", "#6E6B66", rough=0.8, grime=0.3, name="PoleConcrete")
    a.lathe([(0, 0), (0.2, 0), (0.19, 0.5), (0.13, H - 0.03), (0.125, H), (0, H)], con, segs=12, wobble=0.01)
    hw = DARK_METAL
    for k, z in enumerate((H - 0.6, H - 1.5)):
        a.box((2.0, 0.1, 0.1), (0, -0.2, z), hw, bevel=0.01)
        a.rod((0, -0.12, z - 0.5), (0.7, -0.2, z - 0.04), 0.015, hw, segs=6)
        for dx in (-0.85, -0.3, 0.3, 0.85):
            a.lathe([(0, 0), (0.05, 0), (0.06, 0.04), (0.035, 0.07), (0.055, 0.1), (0.03, 0.14), (0.02, 0.18), (0, 0.18)],
                    CERAMIC, segs=10, loc=(dx, -0.2, z + 0.05))
    for k in range(10):
        z = 2.2 + k * 0.55
        a.rod((0, 0, z), ((-1) ** k * 0.32, 0.0, z), 0.012, hw, segs=6)
    a.box((0.22, 0.02, 0.5), (0, -0.165, 2.0), Surf("paint", "#E8D22E", "#2A2A2A", rough=0.5, name="PolePlate"), bevel=0.004)
    if transformer:
        a.lathe([(0, 0), (0.33, 0), (0.35, 0.05), (0.35, 0.85), (0.3, 0.92), (0, 0.95)],
                Surf("paint", "#8E9494", "#5A5048", rough=0.5, metal=0.4, chips=0.4, name="Transformer"),
                segs=16, loc=(0, -0.55, H - 3.4))
        a.box((0.5, 0.35, 0.08), (0, -0.3, H - 3.45), hw, bevel=0.01)
        for dx in (-0.12, 0.12):
            a.lathe([(0, 0), (0.035, 0), (0.04, 0.06), (0.02, 0.12), (0, 0.12)], CERAMIC, segs=8, loc=(dx, -0.55, H - 2.45))


def street_lamp(a, H=6.5):
    pole = Surf("paint", "#6E7377", "#3A3A3A", rough=0.45, metal=0.5, chips=0.3, name="LampPole")
    a.lathe([(0, 0), (0.12, 0), (0.12, 0.25), (0.075, 0.35), (0.055, H), (0, H + 0.02)], pole, segs=10, wobble=0.01)
    a.tube([(0, 0, H - 0.1), (0, -0.4, H + 0.15), (0, -1.2, H + 0.25), (0, -1.6, H + 0.22)], 0.04, pole, segs=8)
    a.box((0.32, 0.55, 0.12), (0, -1.7, H + 0.18), pole, bevel=0.03)
    a.plane(0.26, 0.45, (0, -1.7, H + 0.115), glow("StreetLampGlow", "#FFC98A", 25.0), rot=(PI / 2, 0, 0))


def vending_machine(a, seed=0):
    W, D_, H = 1.0, 0.75, 1.83
    body = Surf("paint", ("#E9E9E6", "#C8282E")[seed % 2], "#55575A", rough=0.35, chips=0.25, grime=0.3,
                name=f"VendBody{seed % 2}")
    a.lohi((-W / 2, -D_, 0.05), (W / 2, 0, H), body, bevel=0.02, wobble=0.002)
    a.lohi((-W / 2 + 0.02, -D_ + 0.03, 0), (W / 2 - 0.02, -0.03, 0.05), DARK_METAL, bevel=0.006)
    a.plane(W - 0.16, 1.05, (-0.04, -D_ - 0.004, 1.2), decal(f"VendFront{seed}", "vending_front", seed, rough=0.2, emit=2.2))
    a.lohi((-W / 2 + 0.06, -D_ - 0.01, 0.58), (W / 2 - 0.06, -D_ + 0.005, 0.66), DARK_METAL, bevel=0.005)
    a.lohi((-W / 2 + 0.1, -D_ - 0.03, 0.15), (W / 2 - 0.25, -D_ + 0.01, 0.42), DARK_METAL, bevel=0.012)
    a.lohi((-W / 2 + 0.13, -D_ - 0.031, 0.19), (W / 2 - 0.28, -D_ - 0.02, 0.38), Surf("paint", "#0E0E10", rough=0.3,
                                                                                         name="Slot"))
    a.lohi((W / 2 - 0.2, -D_ - 0.02, 0.7), (W / 2 - 0.07, -D_ + 0.01, 1.05), Surf("paint", "#9AA0A6", "#55575A", rough=0.4,
                                                                                     metal=0.6, name="CoinPanel"),
           bevel=0.008)
    a.box((0.05, 0.012, 0.012), (W / 2 - 0.135, -D_ - 0.026, 0.95), DARK_METAL)


def traffic_mirror(a):
    a.cyl(0.04, 3.0, (0, 0, 1.5), ORANGE_PAINT, segs=10, bevel=0.005, wobble=0.004)
    a.rod((0, 0, 2.9), (0, -0.25, 2.9), 0.025, ORANGE_PAINT, segs=8)
    a.lathe([(0, 0), (0.42, 0), (0.45, 0.03), (0.44, 0.07), (0.4, 0.06), (0, 0.04)], ORANGE_PAINT, segs=20,
            loc=(0, -0.28, 2.9), rot=(PI / 2, 0, 0))
    a.lathe([(0, 0.06), (0.4, 0.06), (0.33, 0.1), (0.0, 0.13)], mat(M.metal("Mirror", (0.92, 0.93, 0.95), rough=0.02)),
            segs=20, loc=(0, -0.28, 2.9), rot=(PI / 2, 0, 0))


def post_box(a):
    a.lathe([(0, 0), (0.22, 0), (0.22, 0.12), (0.2, 0.15), (0.2, 1.2), (0.24, 1.25), (0.22, 1.32), (0, 1.38)],
            POST_RED, segs=16, wobble=0.004, bevel=0.004)
    a.lohi((-0.12, -0.215, 1.0), (0.12, -0.19, 1.04), DARK_METAL, bevel=0.004)
    a.plane(0.16, 0.2, (0, -0.205, 0.75), decal("PostLabel", "plate", "〒", 256, 320, (250, 250, 250), (200, 20, 20), 180,
                                                 (200, 20, 20), rough=0.4), rot=(0.0, 0, 0))


HOUSE_STYLES = [
    {"wall": ("siding", "#C9C0AE"), "roof": "#4C5157", "w": 8.5, "d": 7.0, "h": 5.8, "trim": "#5A4A3A"},
    {"wall": ("plaster", "#D8CDB6"), "roof": "#5D4A3E", "w": 9.5, "d": 7.5, "h": 6.0, "trim": "#3E3A36"},
    {"wall": ("siding", "#AFB7B3"), "roof": "#3E4652", "w": 7.5, "d": 7.0, "h": 5.6, "trim": "#4A3C30"},
]


def house(a, style=0, seed=0):
    st = HOUSE_STYLES[style]
    rnd = random.Random(seed)
    w, d, h = st["w"], st["d"], st["h"]
    gen, col = st["wall"]
    wall = tile(f"HouseWall{style}", gen, 2.0, rough=0.85, **({"base": col} if gen != "siding" else {"base": col}))
    roof = tile(f"HouseRoof{style}", "kawara", 2.0, rough=0.55, base=st["roof"], nstrength=5.0)
    trim = Surf("wood", st["trim"], rough=0.6, name=f"HouseTrim{style}")
    a.lohi((-w / 2, -d / 2, 0.0), (w / 2, d / 2, h), wall, bevel=0.03)
    a.lohi((-w / 2 - 0.05, -d / 2 - 0.05, -0.1), (w / 2 + 0.05, d / 2 + 0.05, 0.35),
           tile("HouseBase", "painted_concrete", 2.0, base="#8F8A80", dark="#6E6A62"), bevel=0.02)
    a.lohi((-w / 2 - 0.08, -d / 2 - 0.08, h * 0.5 - 0.08), (w / 2 + 0.08, d / 2 + 0.08, h * 0.5 + 0.02), trim, bevel=0.01)
    # gable roof (ridge along X) with overhang
    ov, rh = 0.6, 2.1
    prof = [(-d / 2 - ov, h - 0.15), (d / 2 + ov, h - 0.15), (d / 2 + ov, h - 0.05), (0, h + rh), (-d / 2 - ov, h - 0.05)]
    v = K.extrude(a.bm, [(y, z) for y, z in prof], w + 2 * ov * 0.7, (0, 0, 0), None)
    bmesh.ops.transform(a.bm, matrix=Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))), verts=v)
    a.add(v, roof, bevel=0.03)
    gz = h + 0.0
    tri = [(-d / 2, gz), (d / 2, gz), (0, gz + rh - 0.3)]
    for sx in (-1, 1):
        v = K.extrude(a.bm, tri, 0.05, (0, 0, 0), None)
        bmesh.ops.transform(a.bm, matrix=Matrix.Translation((sx * (w / 2 - 0.02), 0, 0)) @
                            Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))), verts=v)
        a.add(v, wall)
    lit_s = glow("HouseWindowLit", "#FFC98A", 4.0)
    dark_s = Surf("mat", material=M.dark_glass("WindowGlassDark"), name="WindowGlassDark")
    for fl in (0, 1):
        z0 = 0.9 + fl * h * 0.5
        nwin = rnd.randint(2, 3)
        for k in range(nwin):
            x = -w / 2 + w * (k + 0.5) / nwin + rnd.uniform(-0.3, 0.3)
            ww, wh = rnd.choice(((1.2, 1.1), (1.6, 1.1), (0.8, 0.9)))
            lit = rnd.random() < 0.45
            y = -d / 2
            for lo, hi in (((x - ww / 2 - 0.06, y - 0.06, z0 - 0.06), (x + ww / 2 + 0.06, y + 0.02, z0)),
                           ((x - ww / 2 - 0.06, y - 0.06, z0 + wh), (x + ww / 2 + 0.06, y + 0.02, z0 + wh + 0.06)),
                           ((x - ww / 2 - 0.06, y - 0.06, z0), (x - ww / 2, y + 0.02, z0 + wh)),
                           ((x + ww / 2, y - 0.06, z0), (x + ww / 2 + 0.06, y + 0.02, z0 + wh)),
                           ((x - 0.025, y - 0.05, z0), (x + 0.025, y + 0.01, z0 + wh))):
                a.lohi(lo, hi, ALU, bevel=0.008)
            a.lohi((x - ww / 2, y - 0.02, z0), (x + ww / 2, y - 0.005, z0 + wh), lit_s if lit else dark_s)
            if fl == 1 and rnd.random() < 0.5:     # balcony
                a.lohi((x - ww / 2 - 0.3, y - 0.9, z0 - 0.2), (x + ww / 2 + 0.3, y, z0 - 0.08), CONCRETE, bevel=0.02)
                for kk in range(int((ww + 0.6) / 0.12) + 1):
                    xx = x - ww / 2 - 0.3 + kk * 0.12
                    a.rod((xx, y - 0.88, z0 - 0.08), (xx, y - 0.88, z0 + 0.8), 0.012, ALU, segs=6)
                a.rod((x - ww / 2 - 0.3, y - 0.88, z0 + 0.8), (x + ww / 2 + 0.3, y - 0.88, z0 + 0.8), 0.025, ALU, segs=8)
    dx = rnd.uniform(-w / 3, w / 3)
    a.lohi((dx - 0.5, -d / 2 - 0.05, 0.35), (dx + 0.5, -d / 2 + 0.02, 2.4), Surf("wood", "#5C3A22", "#2E1C10", rough=0.5,
                                                                                  name="HouseDoor"), bevel=0.01)
    a.lohi((dx - 0.75, -d / 2 - 1.0, 2.5), (dx + 0.75, -d / 2, 2.6), CONCRETE, bevel=0.02)
    a.lathe([(0, 0), (0.08, 0), (0.09, 0.1), (0, 0.12)], glow("PorchLamp", "#FFD7A0", 10.0), segs=8,
            loc=(dx + 0.7, -d / 2 - 0.05, 2.1), rot=(PI / 2, 0, 0))
    # boundary wall with a gap for the gate
    bw = tile("BlockWall", "block_wall", 1.6, rough=0.85)
    for x0, x1 in ((-w / 2 - 0.5, dx - 0.9), (dx + 0.9, w / 2 + 0.5)):
        a.lohi((x0, -d / 2 - 2.3, 0), (x1, -d / 2 - 2.1, 1.3), bw, bevel=0.015)


BUILDERS = {
    "SchoolDesk": (school_desk, {}),
    "SchoolChair": (school_chair, {}),
    "Window4": (window4, {}),
    "Window4GlassClear": (lambda a: window4_glass(a, True), {}),
    "Window4GlassDark": (lambda a: window4_glass(a, False), {}),
    "ClassDoorPair": (class_door_pair, {}),
    "SteelDoor": (steel_door, {}),
    "SteelDoorFrame": (lambda a: steel_door(a, part="frame"), {}),
    "SteelDoorLeaf": (lambda a: steel_door(a, part="leaf"), {}),
    "LockerBank": (locker_bank, {}),
    "NoticeBoard0": (lambda a: notice_board(a, seed=0), {}),
    "NoticeBoard1": (lambda a: notice_board(a, seed=1), {}),
    "HydrantBox": (hydrant_box, {}),
    "SinkTrough": (sink_trough, {}),
    "BinBurnable": (lambda a: bin_(a, "Burnable"), {}),
    "BinPlastic": (lambda a: bin_(a, "Plastic"), {}),
    "BinCans": (lambda a: bin_(a, "Cans"), {}),
    "UmbrellaStand": (umbrella_stand, {}),
    "WallClock": (wall_clock, {}),
    "PASpeaker": (pa_speaker, {}),
    "CeilingLight": (lambda a: ceiling_light(a, False), {}),
    "CeilingLightOn": (lambda a: ceiling_light(a, True), {}),
    "ExitSign": (exit_sign, {}),
    "Extinguisher": (extinguisher, {}),
    "Chalkboard": (chalkboard, {}),
    "Bookshelf": (bookshelf, {}),
    "BookRowA": (lambda a: book_row(a, seed=1), {}),
    "BookRowB": (lambda a: book_row(a, seed=2), {}),
    "BookRowC": (lambda a: book_row(a, seed=3), {}),
    "SpecimenJarA": (lambda a: specimen_jar(a, 1), {}),
    "SpecimenJarB": (lambda a: specimen_jar(a, 2), {}),
    "CardboardBox": (cardboard_box, {}),
    "CardboardBoxSmall": (lambda a: cardboard_box(a, (0.4, 0.3, 0.25)), {}),
    "CurtainRed": (curtain_panel, {}),
    "MagicCirclePaper": (magic_circle_paper, {}),
    "FencePanel": (fence_panel, {}),
    "FencePost": (fence_post, {}),
    "CageLamp": (cage_lamp, {}),
    "WaterTank": (water_tank, {}),
    "ACUnit": (ac_unit, {}),
    "RoofVent": (roof_vent, {}),
    "Downpipe": (downpipe, {}),
    "GatePost": (gate_post, {}),
    "NamePlate": (name_plate, {}),
    "RollingGate": (rolling_gate, {}),
    "HedgeA": (lambda a: hedge(a, (2.0, 0.8, 0.9), 1), {"shading": "flat"}),
    "HedgeB": (lambda a: hedge(a, (1.6, 0.9, 1.0), 2), {"shading": "flat"}),
    "UtilityPole": (utility_pole, {}),
    "UtilityPoleT": (lambda a: utility_pole(a, transformer=True), {}),
    "StreetLamp": (street_lamp, {}),
    "VendingMachine0": (lambda a: vending_machine(a, 0), {}),
    "VendingMachine1": (lambda a: vending_machine(a, 1), {}),
    "TrafficMirror": (traffic_mirror, {}),
    "PostBox": (post_box, {}),
    "HouseA": (lambda a: house(a, 0, 1), {"max_res": 2048}),
    "HouseB": (lambda a: house(a, 1, 2), {"max_res": 2048}),
    "HouseC": (lambda a: house(a, 2, 3), {"max_res": 2048}),
}
for _k in range(4):
    BUILDERS[f"Poster{_k}"] = ((lambda k: (lambda a: poster(a, k)))(_k), {})
for _k in range(6):
    BUILDERS[f"ClassSign{_k + 1}"] = ((lambda k: (lambda a: class_sign(a, f"2年{k}組", f"ClassSign{k}")))(_k + 1), {})
BUILDERS["ClubSign"] = (lambda a: class_sign(a, "オカルト研究会", "ClubSignPlate"), {})


def register(name, fn, **kw):
    BUILDERS[name] = (fn, kw)


def get(name):
    fn, kw = BUILDERS[name]
    return K.asset(name, fn, **kw)
