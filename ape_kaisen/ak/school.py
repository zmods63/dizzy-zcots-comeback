"""The school map: building, 2F hallway, 3F occult clubroom, rooftop, yard, street and
city at night. Returns named landmarks for the animation and cameras."""

import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from . import mats as M
from . import util as U

# Building footprint and floors (metres). Front (yard side) faces -Y, the moon is in the north (+Y).
X0, X1, Y0, Y1 = -24.0, 24.0, -6.0, 6.0
FH, NF, SLAB, BAY = 3.6, 4, 0.35, 4.0
WALL = 0.25
SILL, WIN_H = 0.8, 2.05
ROOF_Z = NF * FH + SLAB                 # top of the roof slab
HALL_FLOOR = 1                          # 2F hallway runs along the north side
HALL_Y = 2.9                            # corridor wall (classroom side)
CLUB_FLOOR = 2                          # 3F occult club room, south-west corner
CLUB_X = X0 + 2 * BAY                   # club room spans the two west bays


def floor_z(f):
    return f * FH + SLAB


class Buckets:
    """Collect geometry per material and emit one object per bucket."""

    def __init__(self, prefix, col):
        self.prefix, self.col = prefix, col
        self.bms, self.mats, self.opts = {}, {}, {}

    def bm(self, key, mat, **opts):
        if key not in self.bms:
            self.bms[key] = bmesh.new()
            self.mats[key] = mat
            self.opts[key] = opts
        return self.bms[key]

    def box(self, key, mat, lo, hi, **opts):
        lo, hi = Vector(lo), Vector(hi)
        U.bm_box(self.bm(key, mat, **opts), hi - lo, (lo + hi) / 2)

    def finish(self):
        out = {}
        for key, bm in self.bms.items():
            opts = self.opts[key]
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0005)
            ob = U.mesh_object(f"{self.prefix}_{key}", bm, self.col, mats=[self.mats[key]],
                               smooth=opts.get("smooth", False))
            if opts.get("bevel"):
                b = ob.modifiers.new("Bevel", "BEVEL")
                b.width = opts["bevel"]
                b.segments = 2
                b.limit_method = "ANGLE"
                b.harden_normals = False
                ob.data.shade_smooth()
                if hasattr(ob.data, "set_sharp_from_angle"):
                    ob.data.set_sharp_from_angle(angle=math.radians(35))
            if opts.get("no_shadow"):
                ob.visible_shadow = False
            out[key] = ob
        self.bms.clear()
        return out


# ----------------------------------------------------------------- building

def _window(B, x_lo, x_hi, z_lo, z_hi, y_face, outward, clear):
    """Aluminium sliding-sash window in an opening, glass set back from the facade."""
    alu = M.metal("Alu", (0.62, 0.64, 0.66), rough=0.35)
    f = 0.055
    yo, yi = y_face + outward * 0.02, y_face - outward * 0.09
    ylo, yhi = min(yo, yi), max(yo, yi)
    B.box("Frames", alu, (x_lo, ylo, z_lo), (x_hi, yhi, z_lo + f))
    B.box("Frames", alu, (x_lo, ylo, z_hi - f), (x_hi, yhi, z_hi))
    B.box("Frames", alu, (x_lo, ylo, z_lo), (x_lo + f, yhi, z_hi))
    B.box("Frames", alu, (x_hi - f, ylo, z_lo), (x_hi, yhi, z_hi))
    w = x_hi - x_lo
    for k in (1, 2, 3):
        xm = x_lo + w * k / 4
        B.box("Frames", alu, (xm - f * 0.5, ylo, z_lo), (xm + f * 0.5, yhi, z_hi))
    zt = z_lo + (z_hi - z_lo) * 0.74
    B.box("Frames", alu, (x_lo, ylo, zt - f * 0.4), (x_hi, yhi, zt + f * 0.4))
    yg = y_face - outward * 0.05
    if clear:
        B.box("GlassClear", M.glass("WindowGlass"), (x_lo, yg - 0.004, z_lo), (x_hi, yg + 0.004, z_hi), no_shadow=True)
    else:
        B.box("GlassDark", M.dark_glass("WindowGlassDark"), (x_lo, yg - 0.004, z_lo), (x_hi, yg + 0.004, z_hi))
        yr = y_face - outward * (3.2 if outward < 0 else 2.0)   # north rooms are corridors: stay north of the club room
        B.box("Rooms", M.fake_interior("Rooms"), (x_lo, yr - 0.01, z_lo - 0.4), (x_hi, yr + 0.01, z_hi + 0.4))


def build_building(col):
    B = Buckets("School", col)
    wall = M.concrete("SchoolWall", base=(0.72, 0.7, 0.64), dark=(0.42, 0.4, 0.36))
    band = M.concrete("SchoolBand", base=(0.8, 0.79, 0.75), dark=(0.5, 0.49, 0.46), streaks=0.8)
    ncol = int((X1 - X0) / BAY) + 1
    cols_x = [X0 + i * BAY for i in range(ncol)]

    for f in range(NF + 1):            # slabs incl. the roof, sticking out as horizontal bands
        z = f * FH
        B.box("Bands", band, (X0 - 0.22, Y0 - 0.22, z), (X1 + 0.22, Y1 + 0.22, z + SLAB), bevel=0.02)

    for f in range(NF):
        z0, z1 = floor_z(f), (f + 1) * FH
        for side, y_face, outward in (("S", Y0, -1), ("N", Y1, 1)):
            yin = y_face - outward * WALL
            ylo, yhi = min(y_face, yin), max(y_face, yin)
            B.box("Walls", wall, (X0, ylo, z0), (X1, yhi, z0 + SILL), bevel=0.012)
            B.box("Walls", wall, (X0, ylo, z0 + SILL + WIN_H), (X1, yhi, z1), bevel=0.012)
            for x in cols_x:                      # columns sticking out of the facade
                yo = y_face + outward * 0.16
                B.box("Walls", wall, (x - 0.3, min(yo, yin), z0), (x + 0.3, max(yo, yin), z1), bevel=0.02)
            for i in range(ncol - 1):
                xa, xb = cols_x[i] + 0.3, cols_x[i + 1] - 0.3
                entrance = side == "S" and f == 0 and -4.0 <= xa <= 4.0
                clear = (side == "N" and f == HALL_FLOOR) or (side == "S" and f == CLUB_FLOOR and xb <= CLUB_X)
                if entrance:
                    _entrance_bay(B, xa, xb, z0, y_face)
                    continue
                _window(B, xa, xb, z0 + SILL, z0 + SILL + WIN_H, y_face, outward, clear)
                B.box("Walls", band, (xa, min(y_face, y_face + outward * 0.12), z0 + SILL - 0.06),
                      (xb, max(y_face, y_face + outward * 0.12), z0 + SILL), bevel=0.01)
        for x in (X0, X1):                        # end walls
            B.box("Walls", wall, (x - WALL / 2, Y0, z0), (x + WALL / 2, Y1, z1), bevel=0.012)

    # entrance canopy
    B.box("Bands", band, (-5.5, Y0 - 3.2, 3.15), (5.5, Y0, 3.45), bevel=0.02)
    for x in (-5.0, 5.0):
        B.box("Walls", wall, (x - 0.15, Y0 - 3.0, 0.0), (x + 0.15, Y0 - 2.7, 3.15), bevel=0.02)
    B.box("Bands", M.concrete("Plinth", base=(0.5, 0.5, 0.48), dark=(0.32, 0.32, 0.3)),
          (X0 - 0.3, Y0 - 3.4, -0.2), (X1 + 0.3, Y0 + 0.3, 0.12), bevel=0.02)
    return B.finish()


def _entrance_bay(B, xa, xb, z0, y_face):
    alu = M.metal("Alu", (0.62, 0.64, 0.66), rough=0.35)
    top = z0 + 2.7
    B.box("Walls", M.concrete("SchoolWall"), (xa, y_face - 0.0, top), (xb, y_face + WALL, z0 + SILL + WIN_H))
    for k in range(5):
        x = xa + (xb - xa) * k / 4
        B.box("Frames", alu, (x - 0.04, y_face - 0.05, 0.12), (x + 0.04, y_face + 0.05, top))
    B.box("Frames", alu, (xa, y_face - 0.05, top - 0.08), (xb, y_face + 0.05, top))
    B.box("GlassDark", M.dark_glass("WindowGlassDark"), (xa, y_face - 0.01, 0.12), (xb, y_face + 0.01, top))
    B.box("Rooms", M.fake_interior("Lobby", lit_fraction=1.0, lit=(0.45, 0.6, 0.55), strength=0.6),
          (xa, y_face + 3.0, 0.0), (xb, y_face + 3.02, 3.4))


# ----------------------------------------------------------------- 2F hallway

def build_hallway(col):
    B = Buckets("Hall", col)
    z0, z1 = floor_z(HALL_FLOOR), (HALL_FLOOR + 1) * FH
    xa, xb = X0 + WALL / 2, X1 - WALL / 2
    yb = Y1 - WALL
    B.box("Floor", M.tiles("HallFloor", a=(0.42, 0.47, 0.44), b=(0.39, 0.44, 0.41), mortar=(0.25, 0.27, 0.26),
                           size=0.5, rough=0.18), (xa, HALL_Y, z0 - 0.02), (xb, yb, z0 + 0.003))
    B.box("Ceiling", M.paint("Ceiling", (0.78, 0.78, 0.76), rough=0.9), (xa, HALL_Y - 0.2, z1 - 0.02), (xb, yb, z1))
    wallp = M.paint("HallWall", (0.78, 0.75, 0.66), rough=0.85)
    wains = M.paint("HallWainscot", (0.36, 0.45, 0.42), rough=0.6)
    doors = [-22.0, -14.0, -6.0, 2.0, 10.0, 18.0]
    edges = [xa] + [x for d in doors for x in (d - 0.9, d + 0.9)] + [xb]
    for i in range(0, len(edges), 2):
        lo, hi = edges[i], edges[i + 1]
        B.box("Walls", wallp, (lo, HALL_Y - 0.15, z0), (hi, HALL_Y, z1))
        B.box("Wainscot", wains, (lo, HALL_Y - 0.0, z0), (hi, HALL_Y + 0.015, z0 + 1.0))
    wood = M.wood("DoorWood", light=(0.62, 0.45, 0.28), dark=(0.45, 0.3, 0.17))
    for d in doors:
        B.box("Walls", wallp, (d - 0.9, HALL_Y - 0.15, z0 + 2.2), (d + 0.9, HALL_Y, z1))
        B.box("Doors", wood, (d - 0.9, HALL_Y - 0.11, z0), (d + 0.02, HALL_Y - 0.06, z0 + 2.2))
        B.box("DoorGlass", M.dark_glass("DoorGlass", color=(0.01, 0.012, 0.015)),
              (d - 0.7, HALL_Y - 0.065, z0 + 1.2), (d - 0.2, HALL_Y - 0.03, z0 + 1.9))
        B.box("Signs", M.paint("ClassSign", (0.85, 0.85, 0.82), rough=0.6),
              (d - 0.012, HALL_Y + 0.0, z0 + 2.35), (d + 0.012, HALL_Y + 0.45, z0 + 2.62))
    # fluorescent fixtures every bay, all off but one that flickers later
    for x in [X0 + BAY * (i + 0.5) for i in range(12)]:
        B.box("Fixtures", M.paint("FixtureBody", (0.85, 0.85, 0.83), rough=0.5),
              (x - 0.65, (HALL_Y + yb) / 2 - 0.12, z1 - 0.12), (x + 0.65, (HALL_Y + yb) / 2 + 0.12, z1 - 0.02))
        B.box("Tubes", M.paint("TubeOff", (0.9, 0.92, 0.95), rough=0.2),
              (x - 0.6, (HALL_Y + yb) / 2 - 0.05, z1 - 0.14), (x + 0.6, (HALL_Y + yb) / 2 + 0.05, z1 - 0.12))
    # notice boards between doors, fire extinguisher box, exit sign at the far end
    for x in (-18.0, -10.0, 6.0, 14.0):
        B.box("Boards", M.paint("Cork", (0.48, 0.34, 0.2), rough=0.95), (x - 1.0, HALL_Y, z0 + 1.2), (x + 1.0, HALL_Y + 0.03, z0 + 2.1))
        rnd = random.Random(int(x * 10))
        for k in range(5):
            px, pz = x + rnd.uniform(-0.8, 0.6), z0 + rnd.uniform(1.3, 1.75)
            B.box("Papers", M.paint("Paper", (0.85, 0.84, 0.78), rough=0.9),
                  (px, HALL_Y + 0.031, pz), (px + rnd.uniform(0.2, 0.3), HALL_Y + 0.036, pz + rnd.uniform(0.25, 0.35)))
    B.box("Exit", M.glow("ExitGreen", (0.1, 1.0, 0.35), 6.0), (xb - 0.04, 3.9, z1 - 0.55), (xb - 0.02, 4.9, z1 - 0.3))
    hallway_details(B, col, z0, z1, xa, xb, yb, doors)
    objs = B.finish()
    light = bpy.data.lights.new("ExitLight", "POINT")
    light.energy, light.color, light.shadow_soft_size = 15, (0.2, 1.0, 0.45), 0.3
    lo = bpy.data.objects.new("ExitLight", light)
    col.objects.link(lo)
    lo.location = (xb - 0.4, 4.4, z1 - 0.6)
    return objs


def hallway_details(B, col, z0, z1, xa, xb, yb, doors):
    """Everything a real Japanese school corridor has."""
    rnd = random.Random(77)
    mid_y = (HALL_Y + yb) / 2
    beam = M.concrete("CeilingBeam", base=(0.74, 0.73, 0.7), dark=(0.5, 0.49, 0.46), streaks=0.2)
    for i in range(13):
        x = X0 + BAY * i
        B.box("Beams", beam, (x - 0.2, HALL_Y - 0.15, z1 - 0.45), (x + 0.2, yb, z1), bevel=0.01)
    skirt = M.paint("Skirting", (0.16, 0.17, 0.17), rough=0.5)
    B.box("Skirting", skirt, (xa, HALL_Y, z0), (xb, HALL_Y + 0.025, z0 + 0.1))
    B.box("Skirting", skirt, (xa, yb - 0.025, z0), (xb, yb, z0 + 0.1))
    steel = M.metal("Fixtures", (0.7, 0.71, 0.72), rough=0.3)
    white = M.paint("WhitePlastic", (0.85, 0.85, 0.82), rough=0.4)
    for i in range(12):
        x = X0 + BAY * (i + 0.5)
        U.bm_cyl(B.bm("Sprinklers", steel, smooth=True), 0.025, 0.012, 0.05, segs=10, loc=(x + 1.0, mid_y + 0.6, z1 - 0.045))
        U.bm_cyl(B.bm("Detectors", white, smooth=True), 0.06, 0.055, 0.035, segs=16, loc=(x - 1.0, mid_y - 0.5, z1 - 0.02))
    U.bm_cone_between(B.bm("Conduit", M.paint("Conduit", (0.8, 0.8, 0.78), rough=0.4), smooth=True),
                      (xa, HALL_Y + 0.05, z1 - 0.62), (xb, HALL_Y + 0.05, z1 - 0.62), 0.022, 0.022, segs=8)
    for x in (-18.0, -2.0, 14.0):                        # PA speakers
        B.box("Speakers", white, (x - 0.18, HALL_Y, z1 - 0.95), (x + 0.18, HALL_Y + 0.12, z1 - 0.7), bevel=0.01)
        B.box("SpeakerGrill", M.paint("Grill", (0.1, 0.1, 0.1), rough=0.6),
              (x - 0.14, HALL_Y + 0.121, z1 - 0.92), (x + 0.14, HALL_Y + 0.123, z1 - 0.74))
    trim = M.wood("DoorTrim", light=(0.5, 0.36, 0.22), dark=(0.36, 0.25, 0.14))
    plate = M.paint("Plate", (0.92, 0.92, 0.9), rough=0.4)
    for k, d in enumerate(doors):
        B.box("Trim", trim, (d - 0.97, HALL_Y, z0), (d - 0.9, HALL_Y + 0.04, z0 + 2.27))
        B.box("Trim", trim, (d + 0.9, HALL_Y, z0), (d + 0.97, HALL_Y + 0.04, z0 + 2.27))
        B.box("Trim", trim, (d - 0.97, HALL_Y, z0 + 2.2), (d + 0.97, HALL_Y + 0.04, z0 + 2.27))
        B.box("Pulls", M.metal("PullSteel", (0.35, 0.35, 0.36), rough=0.35), (d - 0.12, HALL_Y - 0.05, z0 + 0.95), (d - 0.04, HALL_Y - 0.045, z0 + 1.1))
        B.box("Switches", plate, (d + 1.1, HALL_Y, z0 + 1.2), (d + 1.18, HALL_Y + 0.012, z0 + 1.32))
        B.box("Switches", plate, (d + 1.1, HALL_Y, z0 + 0.25), (d + 1.18, HALL_Y + 0.012, z0 + 0.35))
        for side in (1, -1):        # readable from both ends of the corridor
            sign = U.text_object(f"ClassSign{k}{'E' if side > 0 else 'W'}", f"2-{k + 1}", col, size=0.16,
                                 mat=M.paint("SignText", (0.08, 0.08, 0.1), rough=0.6), extrude=0.001)
            sign.location = (d + side * 0.0135, HALL_Y + 0.225, z0 + 2.485)
            sign.rotation_euler = (math.radians(90), 0, math.radians(90 * side))
    # wall clock above the middle door, alarm bell, hydrant cabinet
    cx = doors[2]
    U.bm_cyl(B.bm("Clock", white, smooth=True), 0.17, 0.17, 0.05, segs=32, loc=(cx, HALL_Y + 0.03, z0 + 2.75),
             rot=Euler((math.radians(90), 0, 0)).to_quaternion())
    U.bm_cyl(B.bm("ClockFace", M.paint("ClockFace", (0.95, 0.95, 0.92), rough=0.3), smooth=True), 0.15, 0.15, 0.002,
             segs=32, loc=(cx, HALL_Y + 0.056, z0 + 2.75), rot=Euler((math.radians(90), 0, 0)).to_quaternion())
    for ang, ln in ((math.radians(60), 0.08), (math.radians(-20), 0.12)):
        hb = B.bm("ClockHands", M.paint("Black", (0.02, 0.02, 0.02), rough=0.5))
        tip = Vector((cx + math.sin(ang) * ln, HALL_Y + 0.06, z0 + 2.75 + math.cos(ang) * ln))
        U.bm_cone_between(hb, (cx, HALL_Y + 0.06, z0 + 2.75), tip, 0.006, 0.004, segs=6)
    red = M.paint("FireRed", (0.6, 0.03, 0.03), rough=0.4)
    B.box("Hydrant", red, (-2.6, HALL_Y, z0 + 0.25), (-1.6, HALL_Y + 0.18, z0 + 1.45), bevel=0.01)
    B.box("HydrantDoor", M.metal("HydrantSteel", (0.75, 0.75, 0.76), rough=0.25), (-2.5, HALL_Y + 0.181, z0 + 0.35), (-1.7, HALL_Y + 0.185, z0 + 1.0))
    U.bm_cyl(B.bm("Bell", red, smooth=True), 0.1, 0.1, 0.06, segs=20, loc=(-2.1, HALL_Y + 0.03, z0 + 1.75),
             rot=Euler((math.radians(90), 0, 0)).to_quaternion())
    U.bm_sphere(B.bm("AlarmLamp", M.glow("AlarmLamp", (1.0, 0.05, 0.02), 3.0)), 0.045, loc=(-2.1, HALL_Y + 0.05, z0 + 1.6), segs=12, rings=8)
    # hand-washing trough with faucets, bins and an umbrella stand
    sx0, sx1 = 4.4, 7.6
    stain = M.metal("Stainless", (0.75, 0.76, 0.77), rough=0.18)
    B.box("Sink", stain, (sx0, HALL_Y, z0 + 0.72), (sx1, HALL_Y + 0.45, z0 + 0.78), bevel=0.01)
    B.box("Sink", stain, (sx0, HALL_Y + 0.42, z0 + 0.55), (sx1, HALL_Y + 0.45, z0 + 0.78))
    B.box("SinkBase", M.concrete("SinkBase", base=(0.55, 0.55, 0.52), dark=(0.35, 0.35, 0.33)),
          (sx0, HALL_Y, z0), (sx1, HALL_Y + 0.4, z0 + 0.72), bevel=0.01)
    for k in range(4):
        x = sx0 + 0.4 + k * 0.8
        U.bm_cone_between(B.bm("Faucets", stain, smooth=True), (x, HALL_Y + 0.02, z0 + 0.95), (x, HALL_Y + 0.18, z0 + 0.95), 0.015, 0.015, segs=8)
        U.bm_cone_between(B.bm("Faucets", stain, smooth=True), (x, HALL_Y + 0.18, z0 + 0.95), (x, HALL_Y + 0.18, z0 + 0.88), 0.012, 0.01, segs=8)
    B.box("Mirror", M.metal("Mirror", (0.9, 0.9, 0.92), rough=0.02), (sx0 + 0.1, HALL_Y, z0 + 1.15), (sx1 - 0.1, HALL_Y + 0.01, z0 + 1.75))
    for k, colr in enumerate(((0.12, 0.25, 0.55), (0.15, 0.45, 0.18), (0.6, 0.45, 0.08))):
        x = sx1 + 0.4 + k * 0.42
        U.bm_cyl(B.bm(f"Bin{k}", M.paint(f"Bin{k}", colr, rough=0.45), smooth=True), 0.17, 0.15, 0.55, segs=16,
                 loc=(x, HALL_Y + 0.22, z0 + 0.275))
    U.bm_cyl(B.bm("Umbrella", M.metal("UmbrellaStand", (0.4, 0.42, 0.45), rough=0.4), smooth=True), 0.16, 0.16, 0.5,
             segs=16, loc=(doors[1] + 1.45, HALL_Y + 0.22, z0 + 0.25))
    for k, colr in enumerate(((0.75, 0.1, 0.12), (0.1, 0.2, 0.6))):
        U.bm_cone_between(B.bm("Umbrellas", M.paint(f"UmbrellaCloth{k}", colr, rough=0.6), smooth=True),
                          (doors[1] + 1.43 + k * 0.05, HALL_Y + 0.2, z0 + 0.1), (doors[1] + 1.4 + k * 0.1, HALL_Y + 0.3, z0 + 0.9),
                          0.035, 0.012, segs=8)
    # posters: coloured sheets with a big title band and text rows
    for k, x in enumerate((-11.5, -3.6, 11.0, 20.0)):
        base = rnd.choice(((0.85, 0.75, 0.3), (0.3, 0.6, 0.85), (0.85, 0.4, 0.35), (0.5, 0.75, 0.45)))
        B.box("Posters", M.paint(f"Poster{k}", base, rough=0.6), (x - 0.3, HALL_Y, z0 + 1.35), (x + 0.3, HALL_Y + 0.006, z0 + 2.15))
        B.box("PosterInk", M.paint("PosterInk", (0.1, 0.1, 0.12), rough=0.6), (x - 0.25, HALL_Y + 0.007, z0 + 1.95), (x + 0.25, HALL_Y + 0.009, z0 + 2.08))
        for r in range(5):
            B.box("PosterInk", M.paint("PosterInk"), (x - 0.25, HALL_Y + 0.007, z0 + 1.45 + r * 0.08),
                  (x - 0.25 + rnd.uniform(0.25, 0.5), HALL_Y + 0.009, z0 + 1.48 + r * 0.08))
    # crescent latches on the hallway windows
    for i in range(12):
        x = X0 + BAY * i + 0.3 + 1.7
        B.box("Latches", M.metal("Latch", (0.75, 0.72, 0.6), rough=0.3), (x - 0.04, yb - 0.08, z0 + 1.8), (x + 0.04, yb - 0.05, z0 + 1.86))
    moon_shafts(col, z0, yb)


def moon_shafts(col, z0, yb):
    """Fake god rays: faint emissive slabs from each hallway window along the moonlight, plus dust."""
    d = Vector((0.18, 1.0, math.tan(math.radians(24)))).normalized()   # toward the moon
    mat, nt, out = U.new_material("MoonShaft")
    g = M.G(nt)
    tc = g.n("ShaderNodeTexCoord")
    nz = g.n("ShaderNodeTexNoise", Scale=1.6, Detail=3.0)
    g.l(tc.outputs["Object"], nz.inputs["Vector"])
    fade = g.n("ShaderNodeMapRange", From_Min=0.35, From_Max=0.75, To_Min=0.015, To_Max=0.09)
    g.l(nz.outputs["Fac"], fade.inputs["Value"])
    em = g.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.55, 0.68, 1.0, 1)
    g.l(fade.outputs["Result"], em.inputs["Strength"])
    tr = g.n("ShaderNodeBsdfTransparent")
    add = g.n("ShaderNodeAddShader")
    g.l(tr.outputs[0], add.inputs[0])
    g.l(em.outputs[0], add.inputs[1])
    g.l(add.outputs[0], out.inputs[0])
    M._transparent_settings(mat)
    bm = bmesh.new()
    zw0, zw1 = z0 + SILL, z0 + SILL + WIN_H
    for i in range(12):
        xa = X0 + BAY * i + 0.35
        xb = xa + BAY - 0.7
        quad = []
        for (x, z) in ((xa, zw0), (xb, zw0), (xb, zw1), (xa, zw1)):
            p = Vector((x, yb - 0.1, z))
            t = min((p.z - z0) / max(-(-d).z, 1e-3), (p.y - HALL_Y) / max(d.y, 1e-3))
            quad.append((p, p - d * t))
        v = [bm.verts.new(a) for a, _ in quad] + [bm.verts.new(b) for _, b in quad]
        for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
            bm.faces.new((v[a], v[b], v[b + 4], v[a + 4]))
    ob = U.mesh_object("MoonShafts", bm, col, mats=[mat])
    ob.visible_shadow = False
    for attr in ("visible_diffuse", "visible_glossy"):
        setattr(ob, attr, False)
    # dust motes drifting slowly through the light
    rnd = random.Random(5)
    dust_m = U.emission("DustMote", (0.75, 0.82, 1.0), 2.5)
    bm = bmesh.new()
    for _ in range(320):
        p = Vector((rnd.uniform(X0 + 1, X1 - 1), rnd.uniform(HALL_Y + 0.2, yb - 0.2), z0 + rnd.uniform(0.2, 3.0)))
        U.bm_ico(bm, rnd.uniform(0.0025, 0.005), loc=p, subdiv=1)
    dust = U.mesh_object("DustMotes", bm, col, mats=[dust_m])
    dust.visible_shadow = False
    dust.location = (0, 0, 0)
    dust.keyframe_insert("location", frame=1)
    dust.location = (0.6, -0.15, -0.35)
    dust.keyframe_insert("location", frame=2900)
    U.set_interpolation(dust, "LINEAR")


# ----------------------------------------------------------------- 3F occult club room

def build_clubroom(col):
    B = Buckets("Club", col)
    z0, z1 = floor_z(CLUB_FLOOR), (CLUB_FLOOR + 1) * FH
    xa, xb = X0 + WALL / 2, CLUB_X - 0.1
    ya, yb = Y0 + WALL, HALL_Y
    B.box("Floor", M.wood("ClubFloor", light=(0.42, 0.3, 0.2), dark=(0.28, 0.19, 0.12), scale=6.0),
          (xa, ya, z0 - 0.02), (xb, yb, z0 + 0.003))
    B.box("Ceiling", M.paint("Ceiling", (0.78, 0.78, 0.76), rough=0.9), (xa, ya, z1 - 0.02), (xb, yb, z1))
    wallp = M.paint("ClubWall", (0.7, 0.66, 0.58), rough=0.85)
    B.box("Walls", wallp, (xb, ya, z0), (xb + 0.15, yb, z1))
    B.box("Walls", wallp, (xa, yb, z0), (xb, yb + 0.15, z1))
    # chalkboard with the club's name on the east wall
    B.box("Board", M.paint("Chalkboard", (0.05, 0.12, 0.08), rough=0.85), (xb - 0.03, -3.5, z0 + 0.9), (xb, 1.5, z0 + 2.2))
    B.box("BoardFrame", M.wood("DoorWood"), (xb - 0.05, -3.6, z0 + 0.85), (xb - 0.02, 1.6, z0 + 0.9))
    # desks pushed together in the middle, chairs around
    desk_top = M.wood("DeskTop", light=(0.66, 0.5, 0.32), dark=(0.5, 0.36, 0.22), scale=2.0)
    steel = M.metal("DeskSteel", (0.45, 0.47, 0.5), rough=0.45)
    cx, cy = (xa + xb) / 2, (ya + yb) / 2 - 0.4
    for dx in (-0.65, 0.65):
        for dy in (-0.45, 0.45):
            x, y = cx + dx, cy + dy
            B.box("Desks", desk_top, (x - 0.6, y - 0.4, z0 + 0.7), (x + 0.6, y + 0.4, z0 + 0.74))
            for lx in (-0.52, 0.52):
                for ly in (-0.33, 0.33):
                    B.box("DeskLegs", steel, (x + lx - 0.02, y + ly - 0.02, z0), (x + lx + 0.02, y + ly + 0.02, z0 + 0.7))
            ch = y + (0.95 if dy > 0 else -0.95)
            B.box("Chairs", desk_top, (x - 0.22, ch - 0.2, z0 + 0.42), (x + 0.22, ch + 0.2, z0 + 0.45))
            back = ch + (0.2 if dy > 0 else -0.2)
            B.box("Chairs", desk_top, (x - 0.22, back - 0.015, z0 + 0.5), (x + 0.22, back + 0.015, z0 + 0.85))
            for lx in (-0.18, 0.18):
                for ly in (-0.16, 0.16):
                    B.box("DeskLegs", steel, (x + lx - 0.015, ch + ly - 0.015, z0), (x + lx + 0.015, ch + ly + 0.015, z0 + 0.42))
    # bookshelves with books and jars on the west wall
    shelf = M.wood("Shelf", light=(0.36, 0.24, 0.14), dark=(0.24, 0.15, 0.08))
    rnd = random.Random(4)
    book_cols = [(0.35, 0.05, 0.05), (0.08, 0.15, 0.3), (0.12, 0.25, 0.1), (0.4, 0.3, 0.1), (0.15, 0.08, 0.2)]
    for y_lo in (-4.8, -1.0):
        y_hi = y_lo + 2.6
        B.box("Shelves", shelf, (xa, y_lo, z0), (xa + 0.4, y_lo + 0.04, z0 + 2.2))
        B.box("Shelves", shelf, (xa, y_hi - 0.04, z0), (xa + 0.4, y_hi, z0 + 2.2))
        for k in range(5):
            zs = z0 + 0.05 + k * 0.5
            B.box("Shelves", shelf, (xa, y_lo, zs), (xa + 0.4, y_hi, zs + 0.03))
            y = y_lo + 0.08
            while y < y_hi - 0.15 and k < 4:
                w = rnd.uniform(0.04, 0.09)
                h = rnd.uniform(0.25, 0.4)
                ckey = rnd.randrange(len(book_cols))
                B.box(f"Books{ckey}", M.paint(f"Book{ckey}", book_cols[ckey], rough=0.7),
                      (xa + 0.06, y, zs + 0.03), (xa + 0.34, y + w, zs + 0.03 + h))
                y += w + rnd.uniform(0.0, 0.02)
                if rnd.random() < 0.08:
                    U.bm_cyl(B.bm("Jars", M.glass("JarGlass", tint=(0.7, 0.85, 0.75), reflect=0.2), no_shadow=True),
                             0.07, 0.07, 0.2, segs=12, loc=(xa + 0.2, y + 0.1, zs + 0.13))
                    y += 0.2
    # curtains half drawn over the south windows
    cloth = M.paint("Curtain", (0.32, 0.03, 0.04), rough=0.9)
    for xc in (xa + 0.6, CLUB_X - 0.9, X0 + BAY + 0.1):
        bm = B.bm("Curtains", cloth, smooth=True)
        for k in range(10):
            x = xc - 0.45 + k * 0.1
            U.bm_cyl(bm, 0.06, 0.06, 2.5, segs=8, loc=(x, ya + 0.2 + 0.03 * math.sin(k * 1.7), z0 + 2.0),
                     rot=None)
    # a few candles for the ritual atmosphere
    wax = M.paint("Wax", (0.85, 0.8, 0.68), rough=0.6)
    flame = M.glow("CandleFlame", (1.0, 0.55, 0.15), 18.0)
    candles = []
    for ang in range(0, 360, 72):
        a = math.radians(ang + 20)
        p = Vector((cx + math.cos(a) * 0.55, cy + math.sin(a) * 0.35, z0 + 0.74))
        U.bm_cyl(B.bm("Candles", wax), 0.025, 0.025, 0.12, segs=10, loc=p + Vector((0, 0, 0.06)))
        U.bm_sphere(B.bm("Flames", flame), 0.012, loc=p + Vector((0, 0, 0.145)), scale=(1, 1, 2.0), segs=8, rings=6)
        candles.append(p + Vector((0, 0, 0.16)))
    objs = B.finish()
    for i, p in enumerate(candles):
        ld = bpy.data.lights.new(f"Candle{i}", "POINT")
        ld.energy, ld.color, ld.shadow_soft_size = 4.0, (1.0, 0.55, 0.2), 0.02
        lo = bpy.data.objects.new(f"Candle{i}", ld)
        col.objects.link(lo)
        lo.location = p + Vector((0, 0, 0.03))
    objs["desk_center"] = Vector((cx, cy, z0 + 0.74))
    return objs


# ----------------------------------------------------------------- rooftop

PENT = (14.0, 22.0, -1.0, 5.0)      # penthouse footprint x0, x1, y0, y1


def build_roof(col):
    B = Buckets("Roof", col)
    z = ROOF_Z
    B.box("Deck", M.tiles("RoofDeck", a=(0.42, 0.43, 0.42), b=(0.39, 0.4, 0.39), mortar=(0.25, 0.25, 0.25),
                          size=1.0, rough=0.8, bump=0.6), (X0 - 0.2, Y0 - 0.2, z - 0.01), (X1 + 0.2, Y1 + 0.2, z + 0.004))
    par = M.concrete("Parapet", base=(0.7, 0.69, 0.65), dark=(0.4, 0.39, 0.36))
    ph = 0.7
    for (lo, hi) in (((X0 - 0.22, Y0 - 0.22), (X1 + 0.22, Y0 + 0.03)), ((X0 - 0.22, Y1 - 0.03), (X1 + 0.22, Y1 + 0.22)),
                     ((X0 - 0.22, Y0 - 0.22), (X0 + 0.03, Y1 + 0.22)), ((X1 - 0.03, Y0 - 0.22), (X1 + 0.22, Y1 + 0.22))):
        B.box("Parapet", par, (*lo, z), (*hi, z + ph), bevel=0.02)
    # chain-link fence on top of the parapet
    green = M.paint("FenceGreen", (0.07, 0.18, 0.1), rough=0.45, metallic=0.4)
    fz0, fz1 = z + ph, z + ph + 2.1
    link = M.chainlink("ChainLink")
    for (a, b) in (((X0 - 0.1, Y0 - 0.1), (X1 + 0.1, Y0 - 0.1)), ((X0 - 0.1, Y1 + 0.1), (X1 + 0.1, Y1 + 0.1)),
                   ((X0 - 0.1, Y0 - 0.1), (X0 - 0.1, Y1 + 0.1)), ((X1 + 0.1, Y0 - 0.1), (X1 + 0.1, Y1 + 0.1))):
        a, b = Vector((*a, 0)), Vector((*b, 0))
        d = b - a
        n = max(1, int(d.length / 2.4))
        for k in range(n + 1):
            p = a + d * (k / n)
            U.bm_cyl(B.bm("FencePosts", green, smooth=True), 0.035, 0.035, fz1 - fz0, segs=10,
                     loc=(p.x, p.y, (fz0 + fz1) / 2))
        for zz in (fz0 + 0.05, fz1 - 0.03):
            U.bm_cone_between(B.bm("FencePosts", green, smooth=True), (a.x, a.y, zz), (b.x, b.y, zz), 0.025, 0.025, segs=8)
        bm = B.bm("Fence", link, no_shadow=False)
        v = [bm.verts.new((a.x, a.y, fz0)), bm.verts.new((b.x, b.y, fz0)), bm.verts.new((b.x, b.y, fz1)),
             bm.verts.new((a.x, a.y, fz1))]
        bm.faces.new(v)
    # stairwell penthouse with its steel door and lamp
    px0, px1, py0, py1 = PENT
    pz1 = z + 3.3
    pw = M.concrete("Penthouse", base=(0.7, 0.69, 0.64), dark=(0.42, 0.41, 0.38))
    door_y = 2.0
    B.box("Pent", pw, (px0, py0, z), (px1, py1, z + 0.02))
    B.box("Pent", pw, (px0, py0, z), (px1, py0 + 0.25, pz1), bevel=0.015)
    B.box("Pent", pw, (px0, py1 - 0.25, z), (px1, py1, pz1), bevel=0.015)
    B.box("Pent", pw, (px1 - 0.25, py0, z), (px1, py1, pz1), bevel=0.015)
    B.box("Pent", pw, (px0, py0, z), (px0 + 0.25, door_y - 0.6, pz1), bevel=0.015)
    B.box("Pent", pw, (px0, door_y + 0.6, z), (px0 + 0.25, py1, pz1), bevel=0.015)
    B.box("Pent", pw, (px0, door_y - 0.6, z + 2.2), (px0 + 0.25, door_y + 0.6, pz1), bevel=0.015)
    B.box("PentRoof", M.concrete("SchoolBand"), (px0 - 0.15, py0 - 0.15, pz1), (px1 + 0.15, py1 + 0.15, pz1 + 0.25), bevel=0.02)
    B.box("Door", M.metal("DoorSteel", (0.32, 0.38, 0.35), rough=0.5, metallic=0.6),
          (px0 + 0.05, door_y - 0.5, z), (px0 + 0.1, door_y + 0.5, z + 2.15))
    B.box("Door", M.metal("DoorSteel"), (px0 - 0.0, door_y + 0.32, z + 1.0), (px0 + 0.05, door_y + 0.42, z + 1.05))
    B.box("Lamp", M.glow("DoorLamp", (1.0, 0.82, 0.55), 12.0), (px0 - 0.12, door_y - 0.12, z + 2.45), (px0, door_y + 0.12, z + 2.6))
    # water tower on the penthouse roof
    tz = pz1 + 0.25
    steel = M.metal("TankSteel", (0.55, 0.57, 0.58), rough=0.45)
    tc = Vector(((px0 + px1) / 2 + 1.0, (py0 + py1) / 2, 0))
    for dx in (-1.0, 1.0):
        for dy in (-1.0, 1.0):
            B.box("Tower", steel, (tc.x + dx - 0.06, tc.y + dy - 0.06, tz), (tc.x + dx + 0.06, tc.y + dy + 0.06, tz + 1.4))
    B.box("Tower", steel, (tc.x - 1.15, tc.y - 1.15, tz + 1.3), (tc.x + 1.15, tc.y + 1.15, tz + 1.42))
    U.bm_cyl(B.bm("Tank", M.paint("TankPaint", (0.78, 0.8, 0.8), rough=0.4), smooth=True),
             1.25, 1.25, 2.2, segs=40, loc=(tc.x, tc.y, tz + 1.42 + 1.1))
    U.bm_cyl(B.bm("Tank", M.paint("TankPaint"), smooth=True), 1.27, 0.2, 0.5, segs=40, loc=(tc.x, tc.y, tz + 2.52 + 1.1 - 0.0))
    # AC units, vents and a pipe run
    unit = M.paint("ACUnit", (0.75, 0.76, 0.74), rough=0.55)
    fan = M.paint("ACFan", (0.06, 0.06, 0.07), rough=0.6)
    for x in (-18.0, -16.6, -15.2):
        B.box("AC", unit, (x - 0.6, Y1 - 1.3, z), (x + 0.6, Y1 - 0.6, z + 0.9), bevel=0.02)
        U.bm_cyl(B.bm("ACFan", fan), 0.3, 0.3, 0.02, segs=24, loc=(x, Y1 - 0.95, z + 0.91))
    for p in ((-6.0, 4.6), (2.0, -4.8), (9.0, 4.8)):
        U.bm_cyl(B.bm("Vents", steel, smooth=True), 0.09, 0.09, 0.8, segs=12, loc=(p[0], p[1], z + 0.4))
        U.bm_cyl(B.bm("Vents", steel, smooth=True), 0.22, 0.05, 0.16, segs=12, loc=(p[0], p[1], z + 0.88))
    U.bm_cone_between(B.bm("Pipes", steel, smooth=True), (-20, Y1 - 0.4, z + 0.25), (12, Y1 - 0.4, z + 0.25), 0.08, 0.08, segs=12)
    objs = B.finish()
    ld = bpy.data.lights.new("DoorLampLight", "POINT")
    ld.energy, ld.color, ld.shadow_soft_size = 120, (1.0, 0.78, 0.5), 0.1
    lo = bpy.data.objects.new("DoorLampLight", ld)
    col.objects.link(lo)
    lo.location = (px0 - 0.4, door_y, z + 2.4)
    return objs


# ----------------------------------------------------------------- grounds, street, city

def tree(bm_trunk, bm_leaves, base, height, spread, rnd):
    U.bm_cyl(bm_trunk, 0.16 * height / 7, 0.08 * height / 7, height * 0.55, segs=8,
             loc=base + Vector((0, 0, height * 0.275)))
    for k in range(rnd.randint(5, 8)):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.0, spread * 0.55)
        c = base + Vector((math.cos(a) * r, math.sin(a) * r, height * rnd.uniform(0.55, 0.92)))
        s = spread * rnd.uniform(0.4, 0.62)
        U.bm_ico(bm_leaves, s, loc=c, scale=(1, 1, rnd.uniform(0.7, 0.95)), subdiv=2)


def build_grounds(col):
    B = Buckets("Grounds", col)
    rnd = random.Random(12)
    B.box("Yard", M.ground("Yard"), (-60, -40, -0.05), (60, 30, 0.0))
    B.box("Outside", M.ground("Outside", a=(0.12, 0.15, 0.08), b=(0.08, 0.1, 0.06), scale=0.05),
          (-700, -700, -0.12), (700, 700, -0.07))
    B.box("Path", M.tiles("PathStone", a=(0.5, 0.49, 0.46), b=(0.46, 0.45, 0.42), mortar=(0.3, 0.3, 0.28),
                          size=0.8, rough=0.8), (-2.5, -40, 0.0), (2.5, Y0 - 3.4, 0.02))
    wallc = M.concrete("Perimeter", base=(0.55, 0.54, 0.5), dark=(0.33, 0.32, 0.3))
    for (lo, hi) in (((-60, -40.15), (-4.6, -39.85)), ((4.6, -40.15), (60, -39.85)), ((-60.15, -40), (-59.85, 30)),
                     ((59.85, -40), (60.15, 30)), ((-60, 29.85), (60, 30.15))):
        B.box("Wall", wallc, (*lo, 0), (*hi, 2.0), bevel=0.015)
        B.box("Wall", wallc, (lo[0] - 0.05, lo[1] - 0.05, 2.0), (hi[0] + 0.05, hi[1] + 0.05, 2.1), bevel=0.015)
    for x in (-4.6, 4.6):
        B.box("Wall", wallc, (x - 0.45, -40.45, 0), (x + 0.45, -39.55, 2.7), bevel=0.02)
    B.box("Plate", M.paint("NamePlate", (0.12, 0.12, 0.12), rough=0.4), (4.25, -40.47, 1.2), (4.95, -40.45, 2.4))
    rail = M.metal("GateSteel", (0.5, 0.52, 0.55), rough=0.35)
    for k in range(14):                      # rolled-back gate
        x = 5.2 + k * 0.28
        B.box("Gate", rail, (x - 0.02, -40.7, 0.05), (x + 0.02, -40.62, 1.6))
    B.box("Gate", rail, (5.1, -40.72, 1.55), (9.0, -40.6, 1.62))
    B.box("Gate", rail, (5.1, -40.72, 0.05), (9.0, -40.6, 0.12))
    # hedges in front of the building
    for x in range(-22, 23, 4):
        if abs(x) < 6:
            continue
        U.bm_ico(B.bm("Hedges", M.foliage("Hedge"), smooth=True), 1.0, loc=(x, Y0 - 1.0, 0.45), scale=(2.1, 0.7, 0.6), subdiv=2)
    trunk_m = M.paint("Bark", (0.16, 0.11, 0.08), rough=0.9)
    leaf_m = M.foliage("Leaves")
    spots = [(x, -36.0) for x in range(-55, 56, 11) if abs(x) > 8]
    spots += [(rnd.uniform(-58, 58), rnd.uniform(12, 28)) for _ in range(26)]
    spots += [(rnd.choice((-1, 1)) * rnd.uniform(30, 58), rnd.uniform(-30, 10)) for _ in range(10)]
    for (x, y) in spots:
        h = rnd.uniform(6.0, 10.0) if y > 10 else rnd.uniform(5.0, 7.0)
        tree(B.bm("Trunks", trunk_m), B.bm("Leaves", leaf_m, smooth=True), Vector((x, y, 0)), h, h * 0.45, rnd)
    objs = B.finish()
    # displaced foliage reads as clumps of leaves instead of balls
    tex = bpy.data.textures.new("LeafClumps", "VORONOI")
    tex.noise_scale = 0.9
    for key in ("Leaves", "Hedges"):
        m = objs[key].modifiers.new("Clumps", "DISPLACE")
        m.texture = tex
        m.strength = 0.6 if key == "Leaves" else 0.3
        m.texture_coords = "GLOBAL"
    name = U.text_object("GateName", "SUGISAWA\nHIGH SCHOOL No.3", col, size=0.062,
                         mat=M.paint("Brass", (0.75, 0.6, 0.3), rough=0.3, metallic=1.0), extrude=0.004)
    name.location = (4.6, -40.476, 1.85)
    name.rotation_euler = (math.radians(90), 0, 0)
    return objs


POLES_X = [-75.0, -45.0, -15.0, 15.0, 45.0, 75.0]
POLE_Y = -40.95                  # on the school-side sidewalk, against the wall
POLE_H = 11.0


def build_street(col):
    B = Buckets("Street", col)
    B.box("Road", M.asphalt("Asphalt"), (-400, -50.0, 0.0), (400, -42.0, 0.03))
    walk = M.tiles("Sidewalk", a=(0.42, 0.41, 0.39), b=(0.38, 0.37, 0.35), mortar=(0.22, 0.22, 0.21), size=0.3, rough=0.85)
    B.box("Walk", walk, (-400, -42.0, 0.0), (400, -40.2, 0.15))
    B.box("Walk", walk, (-400, -52.0, 0.0), (400, -50.0, 0.15))
    curb = M.concrete("Curb", base=(0.6, 0.6, 0.58), dark=(0.4, 0.4, 0.38))
    for y in (-42.0, -50.0):
        B.box("Curb", curb, (-400, y - 0.1, 0.0), (400, y + 0.1, 0.17))
    line = M.paint("RoadLine", (0.85, 0.85, 0.8), rough=0.6)
    for y in (-42.35, -49.65):
        B.box("Lines", line, (-400, y - 0.06, 0.03), (400, y + 0.06, 0.034))
    for x in range(-400, 400, 6):
        B.box("Lines", line, (x, -46.06, 0.03), (x + 3, -45.94, 0.034))
    # utility poles with cross-arms, insulators, a transformer, and sagging wires
    pole_m = M.concrete("PoleConcrete", base=(0.55, 0.55, 0.53), dark=(0.35, 0.35, 0.33), streaks=1.2)
    dark = M.metal("PoleHardware", (0.2, 0.2, 0.21), rough=0.5)
    insul = M.paint("Insulator", (0.75, 0.75, 0.72), rough=0.3)
    tops = []
    for x in POLES_X:
        U.bm_cyl(B.bm("Poles", pole_m, smooth=True), 0.19, 0.13, POLE_H, segs=16, loc=(x, POLE_Y, POLE_H / 2))
        for k, zz in enumerate((POLE_H - 0.6, POLE_H - 1.5)):
            B.box("Arms", dark, (x - 1.0, POLE_Y - 0.07, zz - 0.06), (x + 1.0, POLE_Y + 0.07, zz + 0.06))
            for dx in (-0.85, -0.3, 0.3, 0.85):
                U.bm_cyl(B.bm("Insulators", insul, smooth=True), 0.05, 0.04, 0.16, segs=10, loc=(x + dx, POLE_Y, zz + 0.14))
        if x in (-15.0, 45.0):
            U.bm_cyl(B.bm("Transformers", M.metal("Transformer", (0.45, 0.47, 0.47), rough=0.45), smooth=True),
                     0.32, 0.32, 0.9, segs=16, loc=(x, POLE_Y + 0.45, POLE_H - 3.0))
        U.bm_cyl(B.bm("Poles", pole_m, smooth=True), 0.14, 0.14, 0.06, segs=16, loc=(x, POLE_Y, POLE_H + 0.03))
        tops.append(Vector((x, POLE_Y, POLE_H)))
    wire_m = M.paint("Wire", (0.02, 0.02, 0.02), rough=0.5)
    wire_bm = B.bm("Wires", wire_m, smooth=True)
    for a, b in zip(POLES_X, POLES_X[1:]):
        for zz in (POLE_H - 0.6 + 0.22, POLE_H - 1.5 + 0.22):
            for dx in (-0.85, -0.3, 0.3, 0.85):
                pts = []
                for k in range(13):
                    t = k / 12
                    x = a + dx + (b - a) * t
                    pts.append(Vector((x, POLE_Y, zz - 0.55 * 4 * t * (1 - t))))
                U.bm_tube(wire_bm, pts, [0.012] * len(pts), segs=5, cap=False)
    # street lamps on the school side
    lamp_m = M.glow("StreetLampGlow", (1.0, 0.75, 0.45), 25.0)
    lamps = []
    for x in (-50.0, -25.0, 0.0, 25.0, 50.0):    # street lamps on the far side of the road
        x = x + 8.0
        U.bm_cyl(B.bm("LampPoles", dark, smooth=True), 0.07, 0.05, 6.5, segs=10, loc=(x, -50.9, 3.25))
        U.bm_cone_between(B.bm("LampPoles", dark, smooth=True), (x, -50.9, 6.4), (x, -49.3, 6.6), 0.04, 0.04, segs=8)
        B.box("LampHeads", lamp_m, (x - 0.25, -49.5, 6.45), (x + 0.25, -49.0, 6.55))
        lamps.append(Vector((x, -49.25, 6.35)))
    # houses across the street
    rnd = random.Random(31)
    house_wall = M.concrete("HouseWall", base=(0.6, 0.57, 0.5), dark=(0.36, 0.34, 0.3))
    roof_m = M.paint("HouseRoof", (0.12, 0.13, 0.16), rough=0.6)
    x = -120.0
    while x < 120:
        w, d, h = rnd.uniform(7, 11), rnd.uniform(7, 10), rnd.uniform(5.5, 7.5)
        y = -56.0 - d / 2 - rnd.uniform(0, 3)
        B.box("Houses", house_wall, (x, y - d / 2, 0), (x + w, y + d / 2, h), bevel=0.02)
        bm = B.bm("HouseRoofs", roof_m)
        r = U.bm_box(bm, (w + 0.6, d + 0.6, 0.15), (x + w / 2, y, h + 1.2))
        for v in r:
            if v.co.z > h + 1.2:
                v.co.y = y + (v.co.y - y) * 0.05
                v.co.z += 1.0
        for k in range(rnd.randint(1, 3)):
            wx = x + rnd.uniform(1, w - 2)
            wz = rnd.choice((1.2, 3.8))
            lit = rnd.random() < 0.55
            B.box("HouseWinLit" if lit else "HouseWinDark",
                  M.glow("HouseWindowLit", (1.0, 0.72, 0.42), 4.0) if lit else M.dark_glass("WindowGlassDark"),
                  (wx, y + d / 2, wz), (wx + 1.2, y + d / 2 + 0.03, wz + 1.1))
        x += w + rnd.uniform(1.5, 4.0)
    objs = B.finish()
    for i, p in enumerate(lamps):
        ld = bpy.data.lights.new(f"StreetLamp{i}", "SPOT")
        ld.energy, ld.color, ld.spot_size, ld.spot_blend, ld.shadow_soft_size = 900, (1.0, 0.72, 0.42), math.radians(110), 0.6, 0.15
        lo = bpy.data.objects.new(f"StreetLamp{i}", ld)
        col.objects.link(lo)
        lo.location = p
    objs["pole_tops"] = tops
    return objs


def build_city(col):
    B = Buckets("City", col)
    rnd = random.Random(8)
    winmat = M.city_windows("CityWindows")
    for _ in range(220):
        a = rnd.uniform(math.radians(150), math.radians(390))       # everywhere but straight north
        r = rnd.uniform(260, 650)
        c = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        w, d = rnd.uniform(14, 34), rnd.uniform(14, 34)
        h = rnd.uniform(10, 24) if r < 380 else rnd.uniform(18, 70)
        B.box("Blocks", winmat, (c.x - w / 2, c.y - d / 2, 0), (c.x + w / 2, c.y + d / 2, h))
        if h > 55:
            B.box("Beacons", M.glow("Beacon", (1.0, 0.05, 0.02), 30.0), (c.x - 0.4, c.y - 0.4, h), (c.x + 0.4, c.y + 0.4, h + 0.8))
    # mountains to the north
    bm = B.bm("Mountains", M.paint("Mountain", (0.012, 0.016, 0.022), rough=1.0))
    grid = bmesh.ops.create_grid(bm, x_segments=60, y_segments=12, size=1.0)
    for v in grid["verts"]:
        x = v.co.x * 900
        y = 520 + (v.co.y + 1) * 170
        ridge = 70 + 60 * math.sin(x * 0.006) + 35 * math.sin(x * 0.017 + 1.3) + 18 * math.sin(x * 0.041)
        v.co = Vector((x, y, max(0.0, ridge * (1 - abs(v.co.y)) ** 0.7)))
    return B.finish()


def build_sky(col, scene):
    world = bpy.data.worlds.new("NightSky")
    M.night_sky(world)
    scene.world = world
    # moon: north, about 24 degrees up
    direction = Vector((0.18, 1.0, math.tan(math.radians(24)))).normalized()
    moon_mat, nt, out = U.new_material("Moon")
    g = M.G(nt)
    tc = g.n("ShaderNodeTexCoord")
    nz = g.n("ShaderNodeTexNoise", Scale=2.2, Detail=6.0)
    g.l(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = M._ramp(g, [(0.4, (0.62, 0.62, 0.66)), (0.62, (1.0, 0.98, 0.92))])
    g.l(nz.outputs["Fac"], ramp.inputs["Fac"])
    em = g.n("ShaderNodeEmission", Strength=6.0)
    g.l(ramp.outputs["Color"], em.inputs["Color"])
    g.l(em.outputs[0], out.inputs[0])
    bm = bmesh.new()
    U.bm_sphere(bm, 1.0, segs=48, rings=24)
    moon = U.mesh_object("Moon", bm, col, mats=[moon_mat], smooth=True)
    moon.location = direction * 1200
    moon.scale = (42, 42, 42)
    moon.visible_shadow = False
    sun = bpy.data.lights.new("Moonlight", "SUN")
    sun.energy, sun.color, sun.angle = 1.6, (0.62, 0.72, 1.0), math.radians(0.6)
    so = bpy.data.objects.new("Moonlight", sun)
    col.objects.link(so)
    so.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    return {"moon": moon, "moonlight": so, "moon_dir": direction}


def build_school(scene):
    root = U.collection("School", scene.collection)
    out = {}
    out.update(build_building(U.collection("School_Building", root)))
    out["hall"] = build_hallway(U.collection("School_Hallway", root))
    out["club"] = build_clubroom(U.collection("School_Clubroom", root))
    out["roof"] = build_roof(U.collection("School_Roof", root))
    out["grounds"] = build_grounds(U.collection("School_Grounds", root))
    out["street"] = build_street(U.collection("Street", root))
    out["city"] = build_city(U.collection("City", root))
    out["sky"] = build_sky(U.collection("Sky", root), scene)
    out["marks"] = {
        "roof_z": ROOF_Z,
        "hall_floor_z": floor_z(HALL_FLOOR),
        "hall_y": (HALL_Y + Y1 - WALL) / 2,
        "club_desk": out["club"]["desk_center"],
        "pole_tops": out["street"]["pole_tops"],
        "penthouse_door": Vector((PENT[0] - 0.6, 2.0, ROOF_Z)),
    }
    return out
