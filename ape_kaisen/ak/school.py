"""The school map: building, 2F hallway, 3F occult clubroom, rooftop, yard, street and
city at night. Returns named landmarks for the animation and cameras.

Architecture is built from chamfered blocks with tileable painted textures; everything you
can walk up to is a prop from the asset library (assets.py) or one of the user's own models
(refassets.py), placed as linked duplicates."""

import math
import random

import bmesh
import bpy
from mathutils import Vector

from . import assets as A
from . import kit as K
from . import mats as M
from . import refassets as R
from . import util as U
from .kit import Surf

PI = math.pi

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
DOORS = [-22.0, -14.0, -6.0, 2.0, 10.0, 18.0]


def floor_z(f):
    return f * FH + SLAB


# ----------------------------------------------------------------- surfaces

class _S:
    """Architecture surfaces (tileable textures; created on first use in each file)."""

    def __getattr__(self, key):
        spec = _SURF_SPECS[key]
        s = spec() if callable(spec) else spec
        self.__dict__[key] = s
        return s


S = _S()
_SURF_SPECS = {
    "wall": lambda: A.tile("SchoolWall", "painted_concrete", 3.0, rough=0.88, macro=0.08, base="#C9C3B5", dark="#A7A194"),
    "band": lambda: A.tile("SchoolBand", "painted_concrete", 3.0, rough=0.85, base="#DEDAD1", dark="#C0BBB0", seed=21),
    "plinth": lambda: A.tile("Plinth", "painted_concrete", 2.0, rough=0.9, base="#918E87", dark="#706D67", seed=22),
    "hall_floor": lambda: A.tile("HallFloor", "floor_tiles", 1.0, rough=0.22, a="#83918A", b="#76847D",
                                 grout="#4C5551", gap=0.006),
    "hall_wall": lambda: A.tile("HallWall", "plaster", 2.0, rough=0.85, base="#DCD5C5"),
    "wainscot": lambda: A.tile("Wainscot", "plaster", 2.0, rough=0.6, base="#6E8D86", seed=7, var=0.04),
    "ceiling": lambda: A.tile("Ceiling", "acoustic_ceiling", 1.2, rough=0.95),
    "club_floor": lambda: A.tile("ClubFloor", "wood_planks", 2.0, rough=0.5, planks=8),
    "club_wall": lambda: A.tile("ClubWall", "plaster", 2.0, rough=0.85, base="#CDBFA6", seed=9),
    "roof_deck": lambda: A.tile("RoofDeck", "roof_pavers", 1.2, rough=0.85, macro=0.12),
    "yard": lambda: A.tile("Yard", "dirt", 4.0, rough=0.95, macro=0.18),
    "grass": lambda: A.tile("Grass", "grass", 3.0, rough=0.9, macro=0.2),
    "path": lambda: A.tile("PathPavers", "pavers", 2.0, rough=0.85),
    "sidewalk": lambda: A.tile("Sidewalk", "pavers", 1.6, rough=0.85, a="#7F7C76", b="#74716B", seed=31),
    "asphalt": lambda: A.tile("Asphalt", "asphalt", 6.0, rough=0.8, macro=0.15),
    "block_wall": lambda: A.tile("BlockWall", "block_wall", 1.6, rough=0.85),
    "curb": lambda: A.tile("Curb", "painted_concrete", 2.0, rough=0.85, base="#B5B2AA", dark="#8E8B85", seed=33),
    "alu": lambda: A.mat(M.metal("AluArch", (0.66, 0.68, 0.7), rough=0.32)),
    "skirt": lambda: A.mat(M.paint("Skirting", (0.16, 0.17, 0.17), rough=0.5)),
    "white": lambda: A.mat(M.paint("WhiteArch", (0.82, 0.82, 0.8), rough=0.5)),
    "steel": lambda: A.mat(M.metal("SteelArch", (0.62, 0.63, 0.64), rough=0.35)),
    "road_line": lambda: A.mat(M.paint("RoadLine", (0.8, 0.8, 0.76), rough=0.6)),
    "wire": lambda: A.mat(M.paint("Wire", (0.02, 0.02, 0.02), rough=0.5)),
    "dark_glass": lambda: A.mat(M.dark_glass("WindowGlassDark")),
    "glass": lambda: A.mat(M.glass("WindowGlass")),
}


def reset():
    S.__dict__.clear()


def put(name, col, loc, rot=0.0, scale=1.0, lib=A):
    return K.place(lib.get(name), col, loc, rot, scale)


def shell(name, col):
    """An architecture asset: chamfered blocks with tiling textures, placed at the origin."""
    return K.Asset(name, shading="weighted")


def finish_shell(a, col):
    return K.place(a.build(), col, (0, 0, 0))


# ----------------------------------------------------------------- building

def build_building(col):
    a = shell("SchoolShell", col)
    ncol = int((X1 - X0) / BAY) + 1
    cols_x = [X0 + i * BAY for i in range(ncol)]
    for f in range(NF + 1):            # slabs incl. the roof, sticking out as horizontal bands
        z = f * FH
        a.lohi((X0 - 0.22, Y0 - 0.22, z), (X1 + 0.22, Y1 + 0.22, z + SLAB), S.band, bevel=0.035)
    windows = []
    for f in range(NF):
        z0, z1 = floor_z(f), (f + 1) * FH
        for side, y_face, outward in (("S", Y0, -1), ("N", Y1, 1)):
            yin = y_face - outward * WALL
            ylo, yhi = min(y_face, yin), max(y_face, yin)
            a.lohi((X0, ylo, z0), (X1, yhi, z0 + SILL), S.wall, bevel=0.015)
            a.lohi((X0, ylo, z0 + SILL + WIN_H), (X1, yhi, z1), S.wall, bevel=0.015)
            for x in cols_x:                      # columns sticking out of the facade
                yo = y_face + outward * 0.16
                a.lohi((x - 0.3, min(yo, yin), z0), (x + 0.3, max(yo, yin), z1), S.wall, bevel=0.03)
            for i in range(ncol - 1):
                xa, xb = cols_x[i] + 0.3, cols_x[i + 1] - 0.3
                entrance = side == "S" and f == 0 and -4.0 <= xa <= 4.0
                clear = (side == "N" and f == HALL_FLOOR) or (side == "S" and f == CLUB_FLOOR and xb <= CLUB_X)
                if entrance:
                    _entrance_bay(a, xa, xb, z0, y_face)
                    continue
                xc = (xa + xb) / 2
                yw = y_face - outward * 0.1
                windows.append(((xc, yw, z0 + SILL), 0.0 if outward < 0 else PI, clear))
                a.lohi((xa, min(y_face, y_face + outward * 0.14), z0 + SILL - 0.07),
                       (xb, max(y_face, y_face + outward * 0.14), z0 + SILL), S.band, bevel=0.012)
                if not clear:
                    yr = y_face - outward * (3.2 if outward < 0 else 2.0)   # north rooms: stay clear of the club room
                    a.lohi((xa, yr - 0.01, z0 + SILL - 0.4), (xb, yr + 0.01, z0 + SILL + WIN_H + 0.4),
                           A.mat(M.fake_interior("Rooms")))
        for x in (X0, X1):                        # end walls
            a.lohi((x - WALL / 2, Y0, z0), (x + WALL / 2, Y1, z1), S.wall, bevel=0.015)
    # entrance canopy, plinth, clock tower over the entrance
    a.lohi((-5.5, Y0 - 3.2, 3.15), (5.5, Y0, 3.45), S.band, bevel=0.04)
    for x in (-5.0, 5.0):
        a.lohi((x - 0.16, Y0 - 3.05, 0.0), (x + 0.16, Y0 - 2.73, 3.15), S.wall, bevel=0.03)
    a.lohi((X0 - 0.3, Y0 - 3.4, -0.2), (X1 + 0.3, Y0 + 0.3, 0.12), S.plinth, bevel=0.03)
    for k in range(3):                            # entrance steps
        a.lohi((-3.0 - k * 0.3, Y0 - 3.4 - 0.35 * (k + 1), -0.2), (3.0 + k * 0.3, Y0 - 3.4 - 0.35 * k, 0.12 - 0.11 * (k + 1)),
               S.plinth, bevel=0.02)
    tz = ROOF_Z
    a.lohi((-2.6, Y0 - 0.25, tz), (2.6, Y0 + 1.8, tz + 2.6), S.wall, bevel=0.04)
    a.lohi((-2.75, Y0 - 0.4, tz + 2.6), (2.75, Y0 + 1.95, tz + 2.85), S.band, bevel=0.04)
    finish_shell(a, col)
    win_col = U.collection("School_Windows", col)
    for loc, rot, clear in windows:
        put("Window4", win_col, loc, rot)
        put("Window4GlassClear" if clear else "Window4GlassDark", win_col, loc, rot)
    put("WallClock", col, (0, Y0 - 0.25, tz + 1.3), 0.0, 4.0)
    for x in (-20.0, -12.0, 12.0, 20.0):           # in front of columns, clear of the slab bands
        put("Downpipe", col, (x, Y0 - 0.16, 0.0), 0.0)
        put("Downpipe", col, (x, Y1 + 0.16, 0.0), PI)


def _entrance_bay(a, xa, xb, z0, y_face):
    top = z0 + 2.7
    a.lohi((xa, y_face, top), (xb, y_face + WALL, z0 + SILL + WIN_H), S.wall, bevel=0.015)
    for k in range(5):
        x = xa + (xb - xa) * k / 4
        a.lohi((x - 0.045, y_face - 0.06, 0.12), (x + 0.045, y_face + 0.06, top), S.alu, bevel=0.01)
    a.lohi((xa, y_face - 0.06, top - 0.09), (xb, y_face + 0.06, top), S.alu, bevel=0.01)
    a.lohi((xa, y_face - 0.06, 1.0), (xb, y_face + 0.06, 1.06), S.alu, bevel=0.008)
    a.lohi((xa, y_face - 0.01, 0.12), (xb, y_face + 0.01, top), S.dark_glass)
    a.lohi((xa, y_face + 3.0, 0.0), (xb, y_face + 3.02, 3.4),
           A.mat(M.fake_interior("Lobby", lit_fraction=1.0, lit=(0.45, 0.6, 0.55), strength=0.6)))


# ----------------------------------------------------------------- 2F hallway

def build_hallway(col):
    z0, z1 = floor_z(HALL_FLOOR), (HALL_FLOOR + 1) * FH
    xa, xb = X0 + WALL / 2, X1 - WALL / 2
    yb = Y1 - WALL
    mid_y = (HALL_Y + yb) / 2
    a = shell("HallShell", col)
    a.lohi((xa, HALL_Y, z0 - 0.02), (xb, yb, z0 + 0.003), S.hall_floor)
    a.lohi((xa, HALL_Y - 0.2, z1 - 0.02), (xb, yb, z1), S.ceiling)
    edges = [xa] + [x for d in DOORS for x in (d - 0.98, d + 0.98)] + [xb]
    for i in range(0, len(edges), 2):
        lo, hi = edges[i], edges[i + 1]
        a.lohi((lo, HALL_Y - 0.15, z0), (hi, HALL_Y, z1), S.hall_wall, bevel=0.01)
        a.lohi((lo, HALL_Y - 0.0, z0), (hi, HALL_Y + 0.016, z0 + 1.0), S.wainscot, bevel=0.005)
        a.lohi((lo, HALL_Y, z0 + 0.995), (hi, HALL_Y + 0.03, z0 + 1.03), S.band, bevel=0.008)
    for d in DOORS:
        a.lohi((d - 0.98, HALL_Y - 0.15, z0 + 2.07), (d + 0.98, HALL_Y, z1), S.hall_wall, bevel=0.01)
    # window wall: plaster above, wainscot below, a deep sill
    a.lohi((xa, yb - 0.012, z0), (xb, yb, z0 + SILL), S.wainscot)
    a.lohi((xa, yb - 0.012, z0 + SILL + WIN_H), (xb, yb, z1), S.hall_wall)
    a.lohi((xa, yb - 0.06, z0 + SILL - 0.03), (xb, yb, z0 + SILL), S.band, bevel=0.01)
    for i in range(0, len(edges), 2):                 # skirting stops at the door openings
        a.lohi((edges[i], HALL_Y, z0), (edges[i + 1], HALL_Y + 0.025, z0 + 0.1), S.skirt, bevel=0.004)
    a.lohi((xa, yb - 0.025, z0), (xb, yb, z0 + 0.1), S.skirt, bevel=0.004)
    for i in range(13):
        x = X0 + BAY * i
        a.lohi((x - 0.2, HALL_Y - 0.15, z1 - 0.45), (x + 0.2, yb, z1 - 0.01), S.band, bevel=0.02)
        if 0 < i < 12:
            a.lohi((x - 0.3, yb - 0.1, z0), (x + 0.3, yb, z1), S.hall_wall, bevel=0.02)
    for i in range(12):
        x = X0 + BAY * (i + 0.5)
        a.cyl(0.025, 0.05, (x + 1.0, mid_y + 0.6, z1 - 0.045), S.steel, r2=0.012, segs=10)
        a.cyl(0.06, 0.035, (x - 1.0, mid_y - 0.5, z1 - 0.02), S.white, r2=0.055, segs=16, bevel=0.006)
    a.rod((xa, HALL_Y + 0.05, z1 - 0.62), (xb, HALL_Y + 0.05, z1 - 0.62), 0.022, S.white, segs=8)
    finish_shell(a, col)

    props = U.collection("Hall_Props", col)
    for k, d in enumerate(DOORS):
        put("ClassDoorPair", props, (d, HALL_Y - 0.075, z0), PI)
        put(f"ClassSign{k + 1}", props, (d - 1.15, HALL_Y, z0 + 2.45), PI)
    for x in (-20.2, -15.8, -7.8, -4.0, 0.2, 12.2, 15.8, 20.6):
        put("LockerBank", props, (x, HALL_Y, z0), PI)
    for k, x in enumerate((-18.0, -10.0, 14.0)):
        put(f"NoticeBoard{k % 2}", props, (x, HALL_Y, z0 + 1.25), PI)
    for k, x in enumerate((-3.0, 22.7, 8.75, -8.9)):
        put(f"Poster{k}", props, (x, HALL_Y, z0 + 1.38), PI)
    put("HydrantBox", props, (-2.1, HALL_Y, z0 + 0.25), PI)
    put("Extinguisher", props, (-1.35, HALL_Y + 0.2, z0), PI)
    sx0, sx1 = 3.9, 7.1
    put("SinkTrough", props, ((sx0 + sx1) / 2, HALL_Y, z0), PI)
    for k, kind in enumerate(("Burnable", "Plastic", "Cans")):
        put(f"Bin{kind}", props, (7.55 + k * 0.42, HALL_Y + 0.24, z0), PI)
    put("UmbrellaStand", props, (-12.4, HALL_Y + 0.2, z0), PI)
    put("WallClock", props, (DOORS[2], HALL_Y, z0 + 2.75), PI)
    for x in (-18.0, -2.0, 14.0):
        put("PASpeaker", props, (x, HALL_Y, z1 - 0.85), PI)
    lights = U.collection("Hall_Lights", col)
    for i in range(12):
        put("CeilingLight", lights, (X0 + BAY * (i + 0.5), mid_y, z1 - 0.02))
    put("ExitSign", props, (xb, 4.4, z1 - 0.42), -PI / 2)
    light = bpy.data.lights.new("ExitLight", "POINT")
    light.energy, light.color, light.shadow_soft_size = 15, (0.2, 1.0, 0.45), 0.3
    lo = bpy.data.objects.new("ExitLight", light)
    col.objects.link(lo)
    lo.location = (xb - 0.4, 4.4, z1 - 0.6)
    hall_air(col, z0, z1, yb)


def hall_air(col, z0, z1, yb):
    """Moonlight shafts: a thin participating medium filling the corridor (EEVEE/Cycles volume),
    lit by the moon through the windows, plus a few slow dust motes."""
    mat, nt, out = U.new_material("HallAir")
    g = K.NG(nt)
    vol = g.node("ShaderNodeVolumePrincipled", Density=0.02, Anisotropy=0.55)
    vol.inputs["Color"].default_value = (0.8, 0.86, 1.0, 1)
    g.set(out.inputs["Volume"], vol.outputs[0])
    bm = bmesh.new()
    K.box(bm, (X1 - X0 - 0.4, yb - HALL_Y - 0.05, z1 - z0 - 0.05), ((X0 + X1) / 2, (HALL_Y + yb) / 2, (z0 + z1) / 2))
    ob = U.mesh_object("HallAir", bm, col, mats=[mat])
    ob.visible_shadow = False
    rnd = random.Random(5)
    dust_m = U.emission("DustMote", (0.75, 0.82, 1.0), 2.0)
    bm = bmesh.new()
    for _ in range(260):
        p = Vector((rnd.uniform(X0 + 1, X1 - 1), rnd.uniform(HALL_Y + 0.2, yb - 0.2), z0 + rnd.uniform(0.2, 3.0)))
        U.bm_ico(bm, rnd.uniform(0.0025, 0.005), loc=p, subdiv=1)
    dust = U.mesh_object("DustMotes", bm, col, mats=[dust_m])
    dust.visible_shadow = False
    dust.keyframe_insert("location", frame=1)
    dust.location = (0.6, -0.15, -0.35)
    dust.keyframe_insert("location", frame=2900)
    U.set_interpolation(dust, "LINEAR")


# ----------------------------------------------------------------- 3F occult club room

def build_clubroom(col):
    z0, z1 = floor_z(CLUB_FLOOR), (CLUB_FLOOR + 1) * FH
    xa, xb = X0 + WALL / 2, CLUB_X - 0.1
    ya, yb = Y0 + WALL, HALL_Y
    a = shell("ClubShell", col)
    a.lohi((xa, ya, z0 - 0.02), (xb, yb, z0 + 0.003), S.club_floor)
    a.lohi((xa, ya, z1 - 0.02), (xb, yb, z1), S.ceiling)
    a.lohi((xb, ya, z0), (xb + 0.15, yb, z1), S.club_wall, bevel=0.01)
    a.lohi((xa, yb, z0), (xb, yb + 0.15, z1), S.club_wall, bevel=0.01)
    a.lohi((xa, ya, z0), (xa + 0.012, yb, z1), S.club_wall)
    for lo, hi in (((xb - 0.025, ya, z0), (xb, yb, z0 + 0.1)), ((xa, yb - 0.025, z0), (xb, yb, z0 + 0.1))):
        a.lohi(lo, hi, S.skirt, bevel=0.004)
    a.lohi((xa, ya, z0), (xb, ya + 0.012, z0 + SILL), S.club_wall)
    a.lohi((xa, ya, z0 + SILL - 0.03), (xb, ya + 0.06, z0 + SILL), S.band, bevel=0.01)
    a.rod((xa + 0.05, ya + 0.22, z0 + 2.93), (xb - 0.05, ya + 0.22, z0 + 2.93), 0.014, S.steel, segs=8)
    for x in (xa + 0.1, (xa + xb) / 2, xb - 0.1):
        a.lohi((x - 0.015, ya, z0 + 2.92), (x + 0.015, ya + 0.24, z0 + 2.95), S.steel, bevel=0.004)
    finish_shell(a, col)

    props = U.collection("Club_Props", col)
    cx, cy = (xa + xb) / 2, (ya + yb) / 2 - 0.4
    for dx in (-0.33, 0.33):
        for dy in (-0.23, 0.23):
            put("SchoolDesk", props, (cx + dx, cy + dy, z0), 0.0 if dy < 0 else PI)
    for dx, dy, yaw in ((-0.35, -0.75, PI + 0.15), (0.38, -0.78, PI - 0.1), (-0.3, 0.8, 0.2), (0.4, 0.74, -0.15)):
        put("SchoolChair", props, (cx + dx, cy + dy, z0), yaw)
    top = z0 + 0.71
    put("MagicCirclePaper", props, (cx, cy, top), 0.3)
    candles = []
    for k in range(5):
        t = 2 * PI * k / 5 + 0.3
        p = Vector((cx + math.cos(t) * 0.33, cy + math.sin(t) * 0.33, top + 0.002))
        put("RefCandle" if k % 2 else "RefCandleTall", props, p, t, lib=R)
        h = 0.22 if k % 2 == 0 else 0.15
        candles.append(p + Vector((0, 0, h + 0.012)))
    flame_m = M.glow("CandleFlame", (1.0, 0.55, 0.15), 18.0)
    bm = bmesh.new()
    for p in candles:
        U.bm_sphere(bm, 0.009, loc=p + Vector((0, 0, 0.012)), scale=(1, 1, 2.2), segs=8, rings=6)
    fl = U.mesh_object("CandleFlames", bm, props, mats=[flame_m])
    fl.visible_shadow = False
    for i, p in enumerate(candles):
        ld = bpy.data.lights.new(f"Candle{i}", "POINT")
        ld.energy, ld.color, ld.shadow_soft_size = 4.0, (1.0, 0.55, 0.2), 0.02
        lo = bpy.data.objects.new(f"Candle{i}", ld)
        col.objects.link(lo)
        lo.location = p + Vector((0, 0, 0.03))
    # bookshelves along the west wall, full of books and a few jars
    rows = ["BookRowA", "BookRowB", "BookRowC"]
    rnd = random.Random(4)
    for k, y in enumerate((-4.6, -3.35, -1.0, 0.25)):
        base = Vector((xa + 0.012, y, z0))
        put("Bookshelf", props, base, PI / 2)
        for s, z in enumerate(A.SHELF_Z[:-1]):
            if rnd.random() < 0.8:
                put(rnd.choice(rows), props, (base.x, y + rnd.uniform(-0.02, 0.02), z0 + z), PI / 2)
            else:
                for j in range(2):
                    put(rnd.choice(("SpecimenJarA", "SpecimenJarB")), props,
                        (base.x + 0.18, y - 0.3 + j * 0.45, z0 + z), rnd.uniform(0, 6))
        if rnd.random() < 0.7:
            put("CardboardBoxSmall", props, (base.x + 0.2, y, z0 + 2.035), PI / 2 + rnd.uniform(-0.2, 0.2))
    put("Chalkboard", props, (xb, -1.0, z0 + 0.9), -PI / 2)
    put("CardboardBox", props, (xb - 0.4, yb - 0.45, z0), 0.2)
    put("CardboardBox", props, (xb - 0.42, yb - 0.47, z0 + 0.32), -0.15)
    put("CardboardBoxSmall", props, (xb - 1.0, yb - 0.35, z0), 0.5)
    put("WallClock", props, (xa + 0.012, -2.2, z0 + 2.75), PI / 2)
    for xc in (xa + 0.75, X0 + BAY + 0.1, CLUB_X - 0.9):
        put("CurtainRed", props, (xc, ya + 0.22, z0 + 0.5), PI)
    for i in range(2):
        put("CeilingLight", props, (cx + (i - 0.5) * 3.0, cy, z1 - 0.02), PI / 2)
    return {"desk_center": Vector((cx, cy, top))}


# ----------------------------------------------------------------- rooftop

PENT = (14.0, 22.0, -1.0, 5.0)      # penthouse footprint x0, x1, y0, y1


def build_roof(col):
    z = ROOF_Z
    a = shell("RoofShell", col)
    a.lohi((X0 - 0.2, Y0 - 0.2, z - 0.01), (X1 + 0.2, Y1 + 0.2, z + 0.004), S.roof_deck)
    ph = 0.7
    for (lo, hi) in (((X0 - 0.22, Y0 - 0.22), (X1 + 0.22, Y0 + 0.03)), ((X0 - 0.22, Y1 - 0.03), (X1 + 0.22, Y1 + 0.22)),
                     ((X0 - 0.22, Y0 - 0.22), (X0 + 0.03, Y1 + 0.22)), ((X1 - 0.03, Y0 - 0.22), (X1 + 0.22, Y1 + 0.22))):
        a.lohi((*lo, z), (*hi, z + ph), S.wall, bevel=0.03)
        a.lohi((lo[0] - 0.03, lo[1] - 0.03, z + ph), (hi[0] + 0.03, hi[1] + 0.03, z + ph + 0.06), S.band, bevel=0.02)
    px0, px1, py0, py1 = PENT
    pz1 = z + 3.3
    door_y = 2.0
    a.lohi((px0, py0, z), (px1, py0 + 0.25, pz1), S.wall, bevel=0.025)
    a.lohi((px0, py1 - 0.25, z), (px1, py1, pz1), S.wall, bevel=0.025)
    a.lohi((px1 - 0.25, py0, z), (px1, py1, pz1), S.wall, bevel=0.025)
    a.lohi((px0, py0, z), (px0 + 0.25, door_y - 0.57, pz1), S.wall, bevel=0.025)
    a.lohi((px0, door_y + 0.57, z), (px0 + 0.25, py1, pz1), S.wall, bevel=0.025)
    a.lohi((px0, door_y - 0.57, z + 2.22), (px0 + 0.25, door_y + 0.57, pz1), S.wall, bevel=0.015)
    a.lohi((px0 - 0.15, py0 - 0.15, pz1), (px1 + 0.15, py1 + 0.15, pz1 + 0.25), S.band, bevel=0.03)
    a.lohi((px0 + 0.25, py0 + 0.25, z + 0.004), (px1 - 0.25, py1 - 0.25, z + 0.02), S.hall_floor)
    pipe_s = A.mat(M.paint("PipePaint", (0.55, 0.57, 0.56), rough=0.45))
    a.rod((-20, Y1 - 0.45, z + 0.25), (12, Y1 - 0.45, z + 0.25), 0.08, pipe_s, segs=12)
    for x in range(-20, 13, 3):
        a.lohi((x - 0.05, Y1 - 0.6, z), (x + 0.05, Y1 - 0.3, z + 0.18), S.steel, bevel=0.01)
    finish_shell(a, col)

    props = U.collection("Roof_Props", col)
    fz = z + ph + 0.06
    W = 2.4
    for (p0, p1) in (((X0 - 0.1, Y0 - 0.1), (X1 + 0.1, Y0 - 0.1)), ((X1 + 0.1, Y1 + 0.1), (X0 - 0.1, Y1 + 0.1)),
                     ((X0 - 0.1, Y1 + 0.1), (X0 - 0.1, Y0 - 0.1)), ((X1 + 0.1, Y0 - 0.1), (X1 + 0.1, Y1 + 0.1))):
        p0, p1 = Vector((*p0, fz)), Vector((*p1, fz))
        d = p1 - p0
        n = max(1, round(d.length / W))
        yaw = math.atan2(d.y, d.x)
        for k in range(n):
            c = p0 + d * ((k + 0.5) / n)
            put("FencePanel", props, c, yaw, (d.length / n / W, 1.0, 1.0))
        put("FencePost", props, p1, yaw)
    put("SteelDoorFrame", props, (px0 + 0.12, door_y, z), -PI / 2)
    # the leaf hangs on a hinge empty (door-local x = -0.5 -> world +Y side) so it can swing open
    hinge = bpy.data.objects.new("RoofDoorHinge", None)
    hinge.empty_display_size = 0.3
    props.objects.link(hinge)
    hinge.location = (px0 + 0.12 - 0.02, door_y + 0.5, z)
    leaf = put("SteelDoorLeaf", props, (0.02, -0.5, 0.0), -PI / 2)
    leaf.parent = hinge
    put("CageLamp", props, (px0, door_y, z + 2.55), -PI / 2)
    tc = Vector(((px0 + px1) / 2 + 1.0, (py0 + py1) / 2, pz1 + 0.25))
    put("WaterTank", props, tc, 0.4)
    for x in (-18.0, -16.6, -15.2):
        put("ACUnit", props, (x, Y1 - 1.05, z), 0.0)
    for p in ((-6.0, 4.6), (2.0, -4.8), (9.0, 4.8)):
        put("RoofVent", props, (p[0], p[1], z))
    put("RefBench", props, (6.0, -4.6, z), PI / 2, lib=R)
    put("RefBench", props, (px0 - 3.0, py1 + 0.3, z), PI / 2, lib=R)
    ld = bpy.data.lights.new("DoorLampLight", "POINT")
    ld.energy, ld.color, ld.shadow_soft_size = 120, (1.0, 0.78, 0.5), 0.1
    lo = bpy.data.objects.new("DoorLampLight", ld)
    col.objects.link(lo)
    lo.location = (px0 - 0.4, door_y, z + 2.45)


# ----------------------------------------------------------------- grounds, street, city

def build_grounds(col):
    rnd = random.Random(12)
    a = shell("GroundsShell", col)
    a.lohi((-60, -40, -0.05), (60, 30, 0.0), S.yard)
    a.lohi((-700, -700, -0.12), (700, 700, -0.07), S.grass)
    a.lohi((-2.5, -40, 0.0), (2.5, Y0 - 3.4 - 1.05, 0.02), S.path)
    for (lo, hi) in (((-60, -40.15), (-5.05, -39.85)), ((5.05, -40.15), (60, -39.85)), ((-60.15, -40), (-59.85, 30)),
                     ((59.85, -40), (60.15, 30)), ((-60, 29.85), (60, 30.15))):
        a.lohi((*lo, 0), (*hi, 2.0), S.block_wall, bevel=0.015)
        a.lohi((lo[0] - 0.05, lo[1] - 0.05, 2.0), (hi[0] + 0.05, hi[1] + 0.05, 2.1), S.band, bevel=0.015)
    finish_shell(a, col)
    props = U.collection("Grounds_Props", col)
    for x in (-4.6, 4.6):
        put("GatePost", props, (x, -40.0, 0))
    put("NamePlate", props, (4.6, -40.45, 0.9))
    put("RollingGate", props, (7.1, -40.66, 0))
    for x in range(-22, 23, 4):
        if abs(x) < 6:
            continue
        put("HedgeA" if (x // 4) % 2 else "HedgeB", props, (x + rnd.uniform(-0.3, 0.3), Y0 - 1.0, 0), rnd.uniform(-0.1, 0.1))
    trees = U.collection("Trees", col)
    kinds = ["FallTreeA", "FallTreeB", "FallTreeA_Gold", "FallTreeB_Green"]
    spots = [(x, -36.0) for x in range(-55, 56, 11) if abs(x) > 8]
    spots += [(rnd.uniform(-58, 58), rnd.uniform(12, 28)) for _ in range(22)]
    spots += [(rnd.choice((-1, 1)) * rnd.uniform(30, 58), rnd.uniform(-30, 10)) for _ in range(10)]
    for k, (x, y) in enumerate(spots):
        s = rnd.uniform(0.85, 1.15)
        put(kinds[k % len(kinds)], trees, (x, y, 0), rnd.uniform(0, 2 * PI), s, lib=R)
    for x in (-12.0, 12.0):
        put("RefBench", props, (x, Y0 - 3.0, 0.0), PI / 2, lib=R)
    put("PostBox", props, (-6.2, -40.75, 0.15), 0.0)


POLES_X = [-75.0, -45.0, -15.0, 15.0, 45.0, 75.0]
POLE_Y = -40.95                  # on the school-side sidewalk, against the wall
POLE_H = 11.0


def build_street(col):
    a = shell("StreetShell", col)
    a.lohi((-400, -50.0, 0.0), (400, -42.0, 0.03), S.asphalt)
    a.lohi((-400, -42.0, 0.0), (400, -40.2, 0.15), S.sidewalk)
    a.lohi((-400, -52.0, 0.0), (400, -50.0, 0.15), S.sidewalk)
    for y in (-42.0, -50.0):
        a.lohi((-400, y - 0.1, 0.0), (400, y + 0.1, 0.17), S.curb, bevel=0.02)
    for y in (-42.35, -49.65):
        a.lohi((-400, y - 0.06, 0.03), (400, y + 0.06, 0.034), S.road_line)
    for x in range(-400, 400, 6):
        a.lohi((x, -46.06, 0.03), (x + 3, -45.94, 0.034), S.road_line)
    for a_x, b_x in zip(POLES_X, POLES_X[1:]):
        for zz in (POLE_H - 0.6 + 0.23, POLE_H - 1.5 + 0.23):
            for dx in (-0.85, -0.3, 0.3, 0.85):
                pts = []
                for k in range(13):
                    t = k / 12
                    pts.append(Vector((a_x + dx + (b_x - a_x) * t, POLE_Y - 0.2, zz - 0.55 * 4 * t * (1 - t))))
                a.tube(pts, 0.012, S.wire, segs=5, cap=False)
    finish_shell(a, col)
    props = U.collection("Street_Props", col)
    tops = []
    for x in POLES_X:
        put("UtilityPoleT" if x in (-15.0, 45.0) else "UtilityPole", props, (x, POLE_Y, 0))
        tops.append(Vector((x, POLE_Y, POLE_H)))
    lamps = []
    for x in (-50.0, -25.0, 0.0, 25.0, 50.0):
        x = x + 8.0
        put("StreetLamp", props, (x, -50.9, 0.0), PI)
        lamps.append(Vector((x, -50.9 + 1.7, 6.55)))
    for k, x in enumerate((10.4, 11.5)):
        put(f"VendingMachine{k}", props, (x, -40.2, 0.15))
        ld = bpy.data.lights.new(f"VendingLight{k}", "AREA")
        ld.energy, ld.color, ld.size = 40, (0.85, 0.92, 1.0), 0.9
        lo = bpy.data.objects.new(f"VendingLight{k}", ld)
        col.objects.link(lo)
        lo.location = (x, -41.1, 1.2)
        lo.rotation_euler = (math.radians(-90), 0, 0)
    put("TrafficMirror", props, (-5.6, -42.25, 0.15), PI)
    rnd = random.Random(31)
    houses = U.collection("Houses", col)
    x = -120.0
    k = 0
    while x < 120:
        kind = ("HouseA", "HouseB", "HouseC")[k % 3]
        w = A.HOUSE_STYLES[k % 3]["w"]
        y = -59.5 - rnd.uniform(0, 2.5)
        put(kind, houses, (x + w / 2, y, 0), PI + rnd.uniform(-0.03, 0.03))
        x += w + 2.8 + rnd.uniform(1.5, 4.0)
        k += 1
    for i, p in enumerate(lamps):
        ld = bpy.data.lights.new(f"StreetLamp{i}", "SPOT")
        ld.energy, ld.color, ld.spot_size, ld.spot_blend, ld.shadow_soft_size = 900, (1.0, 0.72, 0.42), math.radians(110), 0.6, 0.15
        lo = bpy.data.objects.new(f"StreetLamp{i}", ld)
        col.objects.link(lo)
        lo.location = p
    return {"pole_tops": tops}


def build_city(col):
    """Distant city blocks with lit windows, and mountains to the north."""
    rnd = random.Random(8)
    a = shell("CityShell", col)
    win = A.mat(M.city_windows("CityWindows"))
    beacon = A.mat(M.glow("Beacon", (1.0, 0.05, 0.02), 30.0))
    for _ in range(220):
        ang = rnd.uniform(math.radians(150), math.radians(390))       # everywhere but straight north
        r = rnd.uniform(260, 650)
        c = Vector((math.cos(ang) * r, math.sin(ang) * r, 0))
        w, d = rnd.uniform(14, 34), rnd.uniform(14, 34)
        h = rnd.uniform(10, 24) if r < 380 else rnd.uniform(18, 70)
        a.lohi((c.x - w / 2, c.y - d / 2, 0), (c.x + w / 2, c.y + d / 2, h), win)
        if h > 55:
            a.lohi((c.x - 0.4, c.y - 0.4, h), (c.x + 0.4, c.y + 0.4, h + 0.8), beacon)
    bm = a.bm
    old = K.mark_old(bm)
    bmesh.ops.create_grid(bm, x_segments=60, y_segments=12, size=1.0)
    grid = K.new_verts(bm, old)
    for v in grid:
        x = v.co.x * 900
        y = 520 + (v.co.y + 1) * 170
        ridge = 70 + 60 * math.sin(x * 0.006) + 35 * math.sin(x * 0.017 + 1.3) + 18 * math.sin(x * 0.041)
        v.co = Vector((x, y, max(0.0, ridge * (1 - abs(v.co.y)) ** 0.7)))
    a.add(grid, A.mat(M.paint("Mountain", (0.012, 0.016, 0.022), rough=1.0)))
    finish_shell(a, col)


def build_sky(col, scene):
    world = bpy.data.worlds.new("NightSky")
    M.night_sky(world)
    scene.world = world
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
    reset()
    root = U.collection("School", scene.collection)
    out = {}
    build_building(U.collection("School_Building", root))
    build_hallway(U.collection("School_Hallway", root))
    out["club"] = build_clubroom(U.collection("School_Clubroom", root))
    build_roof(U.collection("School_Roof", root))
    build_grounds(U.collection("School_Grounds", root))
    out["street"] = build_street(U.collection("Street", root))
    build_city(U.collection("City", root))
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
