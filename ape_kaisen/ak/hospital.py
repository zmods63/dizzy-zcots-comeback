"""Grandpa's hospital room at sunset (its own scene: warm low sun through venetian blinds).

Room shell from chamfered blocks with tileable textures; furniture and equipment from the
hospital prop library (assets_hosp.py)."""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import assets as A
from . import assets_hosp as H
from . import kit as K
from . import mats as M
from . import util as U

PI = math.pi

# Room: x -2.6..2.6, y -2.2..2.2, floor z 0, ceiling 2.8. Window in the +Y wall.
RX, RY, RZ = 2.6, 2.2, 2.8
BED_C = Vector((0.75, 0.15, 0.0))       # bed centre on the floor; head end at +X
BED_L, BED_W, MATTRESS_TOP = H.BED_L, H.BED_W, H.MATTRESS_TOP
STOOL = Vector((0.55, -0.85, 0.0))
STOOL_TOP = H.STOOL_TOP
SUN_DIR = Vector((0.35, -1.0, -0.45)).normalized()      # low evening sun (22 deg) slanting in onto the bed
WIN_X0, WIN_X1, WIN_Z0, WIN_Z1 = -1.5, 1.1, 0.85, 2.3


def put(name, col, loc, rot=0.0, scale=1.0, lib=H):
    return K.place(lib.get(name), col, loc, rot, scale)


def build_room(col):
    floor_s = A.tile("HospFloor", "floor_tiles", 0.9, rough=0.25, a="#C9C2B2", b="#BFB8A7", grout="#8F887A",
                     gap=0.004, scuff=0.3, speck=0.02)
    wall_s = A.tile("HospWall", "plaster", 2.0, rough=0.85, base="#D3D9CC", seed=12)
    wains_s = A.tile("HospWainscot", "plaster", 2.0, rough=0.6, base="#93B3A8", seed=13, var=0.04)
    ceil_s = A.tile("HospCeiling", "acoustic_ceiling", 1.2, rough=0.95)
    skirt_s = A.mat(M.paint("HospSkirt", (0.3, 0.33, 0.32), rough=0.5))
    rail_s = A.mat(M.metal("CurtainRail", (0.7, 0.71, 0.72), rough=0.3))
    a = K.Asset("HospShell")
    a.lohi((-RX, -RY, -0.02), (RX, RY, 0.002), floor_s)
    a.lohi((-RX, -RY, RZ), (RX, RY, RZ + 0.05), ceil_s)
    x0, x1, z0, z1 = WIN_X0 - 0.06, WIN_X1 + 0.06, WIN_Z0 - 0.06, WIN_Z1 + 0.06
    for (lo, hi) in (((-RX - 0.1, -RY - 0.1, 0), (-RX, RY + 0.1, RZ)), ((RX, -RY - 0.1, 0), (RX + 0.1, RY + 0.1, RZ)),
                     ((-RX, -RY - 0.1, 0), (RX, -RY, RZ)),
                     ((-RX, RY, 0), (x0, RY + 0.15, RZ)), ((x1, RY, 0), (RX, RY + 0.15, RZ)),
                     ((x0, RY, 0), (x1, RY + 0.15, z0)), ((x0, RY, z1), (x1, RY + 0.15, RZ))):
        a.lohi(lo, hi, wall_s, bevel=0.01)
    for (lo, hi) in (((-RX, -RY, 0), (-RX + 0.012, RY, 1.0)), ((RX - 0.012, -RY, 0), (RX, RY, 1.0)),
                     ((-RX, -RY, 0), (RX, -RY + 0.012, 1.0)), ((-RX, RY - 0.012, 0), (x0, RY, 1.0)),
                     ((x1, RY - 0.012, 0), (RX, RY, 1.0)), ((x0, RY - 0.012, 0), (x1, RY, z0 - 0.04))):
        a.lohi(lo, hi, wains_s)
    for (lo, hi) in (((-RX, -RY, 0), (RX, -RY + 0.02, 0.09)), ((-RX, -RY, 0), (-RX + 0.02, RY, 0.09)),
                     ((RX - 0.02, -RY, 0), (RX, RY, 0.09)), ((-RX, RY - 0.02, 0), (RX, RY, 0.09))):
        a.lohi(lo, hi, skirt_s, bevel=0.004)
    # chair rail where the two paints meet
    for (lo, hi) in (((-RX, -RY, 0.99), (-RX + 0.025, RY, 1.03)), ((RX - 0.025, -RY, 0.99), (RX, RY, 1.03)),
                     ((-RX, -RY, 0.99), (RX, -RY + 0.025, 1.03))):
        a.lohi(lo, hi, A.mat(M.paint("ChairRail", (0.75, 0.74, 0.7), rough=0.4)), bevel=0.006)
    a.lohi((WIN_X0 - 0.75, RY - 0.17, 2.42), (WIN_X1 + 0.75, RY - 0.12, 2.45), rail_s, bevel=0.005)
    return K.place(a.build(), col, (0, 0, 0))


def build_furniture(col):
    props = U.collection("Hosp_Props", col)
    put("HospWindow", props, ((WIN_X0 + WIN_X1) / 2, RY + 0.07, WIN_Z0))
    put("Blinds", props, ((WIN_X0 + WIN_X1) / 2, RY - 0.02, WIN_Z0))
    for xc in (WIN_X0 - 0.4, WIN_X1 + 0.4):
        put("CurtainGreen", props, (xc, RY - 0.145, 0.1), PI)
    put("HospitalBed", props, BED_C)
    put("PrivacyCurtain", props, BED_C)
    put("IVStand", props, (BED_C.x + 0.85, BED_C.y + 0.85, 0))
    mon = Vector((BED_C.x + 1.25, BED_C.y + 0.55, 1.55))
    put("VitalsMonitor", props, mon, -PI / 2)
    t = Vector((BED_C.x + 0.55, BED_C.y - 0.9, 0))
    put("BedsideCabinet", props, t)
    put("FlowerVase", props, t + Vector((-0.1, 0.05, 0.72)))
    put("WaterGlass", props, t + Vector((0.12, -0.05, 0.72)))
    put("Stool", props, STOOL, 0.3)
    put("OverbedTable", props, (BED_C.x - 0.75, BED_C.y + 0.45, 0), PI / 2)
    put("WallClock", props, (-RX, -0.6, 2.2), PI / 2, lib=A)
    put("PaintingFrame", props, (-RX, 0.65, 1.4), PI / 2)
    put("HospDoor", props, (-1.675, -RY, 0), PI)
    put("Sanitizer", props, (-0.95, -RY, 1.15), PI)
    put("HospSink", props, (-RX, -1.45, 0), PI / 2)
    put("CeilingPanel", props, (0.0, 0.0, RZ))
    put("BedHeadPanel", props, (RX, BED_C.y, 1.25), -PI / 2)
    return mon


def ecg_trace(col, mon):
    """The green trace on the monitor: a sweeping heartbeat line. Object property 'sweep' (cycles,
    animate linearly) moves the bright head; shape key 'Flat' flattens the line."""
    mat, nt, out = U.new_material("ECG")
    g = M.G(nt)
    tc = g.n("ShaderNodeTexCoord")
    sep = g.n("ShaderNodeSeparateXYZ")
    g.l(tc.outputs["UV"], sep.inputs[0])
    sweep = g.n("ShaderNodeAttribute", {"attribute_type": "OBJECT", "attribute_name": "sweep"})
    behind = g.n("ShaderNodeMath", {"operation": "SUBTRACT"})
    g.l(sweep.outputs["Fac"], behind.inputs[0])
    g.l(sep.outputs["X"], behind.inputs[1])
    wrapped = g.n("ShaderNodeMath", {"operation": "FRACT"})
    g.l(behind.outputs[0], wrapped.inputs[0])
    fade = g.n("ShaderNodeMapRange", From_Min=0.0, From_Max=0.8, To_Min=6.0, To_Max=0.15)
    g.l(wrapped.outputs[0], fade.inputs["Value"])
    em = g.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.2, 1.0, 0.4, 1)
    g.l(fade.outputs["Result"], em.inputs["Strength"])
    g.l(em.outputs[0], out.inputs[0])
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    n, width = 900, 0.004           # dense enough that the narrow QRS spike is never skipped
    beats = 3
    rows = []
    for i in range(n + 1):
        u = i / n
        p = (u * beats) % 1.0
        y = (0.62 * math.exp(-((p - 0.42) / 0.016) ** 2) - 0.2 * math.exp(-((p - 0.39) / 0.014) ** 2)
             - 0.16 * math.exp(-((p - 0.452) / 0.014) ** 2) + 0.09 * math.exp(-((p - 0.25) / 0.03) ** 2)
             + 0.14 * math.exp(-((p - 0.66) / 0.05) ** 2))
        pos = mon + Vector((-0.066, 0.15 - 0.25 * u, -0.02 + y * 0.11))     # sweeps left to right on screen
        rows.append((bm.verts.new(pos - Vector((0, 0, width))), bm.verts.new(pos + Vector((0, 0, width))), u))
    for (a1, a2, ua), (b1, b2, ub) in zip(rows, rows[1:]):
        f = bm.faces.new((a1, b1, b2, a2))
        for loop, uv in zip(f.loops, ((ua, 0), (ub, 0), (ub, 1), (ua, 1))):
            loop[uvl].uv = uv
    ob = U.mesh_object("ECG_Trace", bm, col, mats=[mat])
    ob["sweep"] = 0.0
    ob.shape_key_add(name="Basis")
    sk = ob.shape_key_add(name="Flat")
    sk.value = 0.0          # new keys start at full strength in Blender 5.x
    for kv, v in zip(sk.data, ob.data.vertices):
        kv.co = Vector((v.co.x, v.co.y, mon.z - 0.02 + (width if (v.index % 2) else -width)))
    ob.visible_shadow = False
    return ob


def sunset_sky(world):
    if world.node_tree is None:
        world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    g = M.G(nt)
    out = g.n("ShaderNodeOutputWorld")
    tc = g.n("ShaderNodeTexCoord")
    sep = g.n("ShaderNodeSeparateXYZ")
    g.l(tc.outputs["Generated"], sep.inputs[0])
    up = g.n("ShaderNodeMapRange", From_Min=-0.05, From_Max=0.6)
    g.l(sep.outputs["Z"], up.inputs["Value"])
    ramp = M._ramp(g, [(0.0, (1.0, 0.35, 0.08)), (0.12, (0.95, 0.42, 0.25)), (0.4, (0.45, 0.25, 0.45)), (1.0, (0.12, 0.12, 0.3))])
    g.l(up.outputs["Result"], ramp.inputs["Fac"])
    bg = g.n("ShaderNodeBackground", Strength=1.6)
    g.l(ramp.outputs["Color"], bg.inputs["Color"])
    g.l(bg.outputs[0], out.inputs["Surface"])


def skyline(col):
    """Rooftops outside the window: chamfered blocks with lit windows, silhouetted by the sunset."""
    rnd = random.Random(2)
    a = K.Asset("HospSkyline", shading="weighted")
    body = A.mat(M.paint("SkylineDusk", (0.07, 0.045, 0.08), rough=1.0))
    lit = A.mat(M.glow("SkylineWindow", (1.0, 0.7, 0.4), 3.0))
    for k in range(40):
        x = -60 + k * 3.2 + rnd.uniform(-1, 1)
        h = rnd.uniform(4, 18)
        w = rnd.uniform(2, 4)
        y = 45 + rnd.uniform(0, 20)
        a.lohi((x - w / 2, y - 1.5, -8), (x + w / 2, y + 1.5, h - 8), body, bevel=0.15)
        for _ in range(rnd.randint(0, 4)):
            wx = x + rnd.uniform(-w / 2 + 0.3, w / 2 - 0.6)
            wz = rnd.uniform(-6, h - 9)
            a.lohi((wx, y - 1.52, wz), (wx + 0.35, y - 1.5, wz + 0.5), lit)
    return K.place(a.build(), col, (0, 0, 0))


def build_hospital(scene):
    root = U.collection("Hospital", scene.collection)
    build_room(root)
    mon = build_furniture(root)
    ecg = ecg_trace(root, mon)
    skyline(root)
    sun_disc = U.mesh_object("SunDisc", _disc(), root, mats=[U.emission("SunDiscMat", (1.0, 0.55, 0.2), 25.0)])
    sun_disc.location = -SUN_DIR * 140
    sun_disc.rotation_euler = SUN_DIR.to_track_quat("Z", "Y").to_euler()
    sun_disc.scale = (4, 4, 4)
    sun_disc.visible_shadow = False      # it sits right on the sun's line: must not shadow the sunlight
    world = bpy.data.worlds.new("SunsetSky")
    sunset_sky(world)
    scene.world = world
    sun = bpy.data.lights.new("Sunset", "SUN")
    sun.energy, sun.color, sun.angle = 6.0, (1.0, 0.52, 0.22), math.radians(1.2)
    so = bpy.data.objects.new("Sunset", sun)
    root.objects.link(so)
    so.rotation_euler = SUN_DIR.to_track_quat("-Z", "Y").to_euler()
    fill = bpy.data.lights.new("RoomFill", "AREA")
    fill.energy, fill.color, fill.size = 60, (0.55, 0.6, 0.85), 2.5
    fo = bpy.data.objects.new("RoomFill", fill)
    root.objects.link(fo)
    fo.location = (-1.5, -1.5, 2.6)
    fo.rotation_euler = U.look_rotation(fo.location, (0.5, 0.3, 0.6)).to_euler()
    x0, x1 = BED_C.x - BED_L / 2, BED_C.x + BED_L / 2
    y0, y1 = BED_C.y - BED_W / 2, BED_C.y + BED_W / 2
    return {"ecg": ecg, "monitor": mon, "bed": (x0, x1, y0, y1)}


def _disc():
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=48, radius=1.0)
    return bm


def lay_in_bed(actor, f, head_toward=Vector((1, 0, 0))):
    """Grandpa on his back on the mattress, head on the pillow (rig origin at the pelvis)."""
    z_axis = Vector(head_toward).normalized()          # rig up -> toward the pillow
    y_axis = Vector((0, 0, -1))                        # rig back (+Y) -> down into the mattress
    x_axis = y_axis.cross(z_axis)
    m = Matrix((x_axis, y_axis, z_axis)).transposed()
    arm = actor.ape.arm
    # pelvis placed so the head (0.56 up the rig) lands on the pillow and the back (rig +Y 0.177)
    # rests 1.7 cm into the mattress
    arm.location = Vector((BED_C.x + BED_L / 2 - 0.32 - 0.56, BED_C.y, MATTRESS_TOP + 0.16))
    arm.rotation_euler = m.to_euler()
    arm.keyframe_insert("location", frame=f)
    arm.keyframe_insert("rotation_euler", frame=f)
    return arm.location.copy()


def grandpa_hands(actor, f, pelvis):
    """Hands folded flat on his chest (palms down, fingers across toward the other side),
    elbows resting on the mattress beside him."""
    from .motion import plant_rotation
    for s, dy, across in (("L", -0.06, 1.0), ("R", 0.06, -1.0)):
        p = Vector((pelvis.x + 0.24, pelvis.y + dy, pelvis.z + 0.135))
        rot = plant_rotation(s, 0.0, normal=Vector((0, 0, 1)), along=Vector((0.35, across, 0)))
        actor.hand_to(f, s, p, pose="relaxed", plant=1.0, rot=rot, settle=False)


def drape_blanket(col, body_objs, x_range, y_range, top_z, name="Blanket"):
    """A blanket that falls onto whatever is in the bed (ray-cast against the given meshes)."""
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for ob in body_objs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(verts)
        verts += [ev.matrix_world @ v.co for v in me.vertices]
        polys += [tuple(base + i for i in p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
    bvh = BVHTree.FromPolygons(verts, polys) if polys else None
    nx, ny = 46, 26
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = x_range[0] + (x_range[1] - x_range[0]) * i / nx
            y = y_range[0] + (y_range[1] - y_range[0]) * j / ny
            z = top_z
            if bvh:
                hit = bvh.ray_cast(Vector((x, y, top_z + 2.0)), Vector((0, 0, -1)))[0]
                if hit is not None:
                    z = max(z, hit.z + 0.03)
            edge = min(j, ny - j) / ny
            if edge < 0.12:                    # the sides hang over the mattress edges
                z -= (0.12 - edge) * 2.2
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop, (u, v) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uvl].uv = (u / nx * (x_range[1] - x_range[0]) / 0.6, v / ny * (y_range[1] - y_range[0]) / 0.6)
    mat = A.tile("Blanket", "fabric_curtain", 0.6, rough=0.9, base="#8EA9C4", seed=4).material
    ob = U.mesh_object(name, bm, col, mats=[mat], smooth=True)
    ob.modifiers.new("Thick", "SOLIDIFY").thickness = 0.02
    sm = ob.modifiers.new("Soft", "SMOOTH")
    sm.factor, sm.iterations = 0.8, 6
    return ob
