"""Grandpa's hospital room at sunset (its own scene: warm low sun through venetian blinds)."""

import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import mats as M
from . import util as U

# Room: x -2.6..2.6, y -2.2..2.2, floor z 0, ceiling 2.8. Window in the +Y wall.
RX, RY, RZ = 2.6, 2.2, 2.8
BED_C = Vector((0.75, 0.15, 0.0))       # bed centre on the floor; head end at +X
BED_L, BED_W, MATTRESS_TOP = 2.05, 0.95, 0.62
STOOL = Vector((0.55, -0.85, 0.0))
STOOL_TOP = 0.46
SUN_DIR = Vector((-0.35, -1.0, -0.16)).normalized()     # sunlight travels in through the window


def build_room(col):
    from .school import Buckets
    B = Buckets("Hosp", col)
    wall = M.paint("HospWall", (0.78, 0.8, 0.72), rough=0.85)
    wains = M.paint("HospWainscot", (0.55, 0.66, 0.62), rough=0.6)
    B.box("Floor", M.tiles("HospFloor", a=(0.62, 0.6, 0.55), b=(0.58, 0.56, 0.51), mortar=(0.42, 0.4, 0.37),
                           size=0.45, rough=0.22, bump=0.2), (-RX, -RY, -0.02), (RX, RY, 0.002))
    B.box("Ceiling", M.paint("HospCeiling", (0.85, 0.85, 0.83), rough=0.9), (-RX, -RY, RZ), (RX, RY, RZ + 0.05))
    win_x0, win_x1, win_z0, win_z1 = -1.5, 1.1, 0.85, 2.3
    for (lo, hi) in (((-RX - 0.1, -RY - 0.1, 0), (-RX, RY + 0.1, RZ)), ((RX, -RY - 0.1, 0), (RX + 0.1, RY + 0.1, RZ)),
                     ((-RX, -RY - 0.1, 0), (RX, -RY, RZ)),
                     ((-RX, RY, 0), (win_x0, RY + 0.12, RZ)), ((win_x1, RY, 0), (RX, RY + 0.12, RZ)),
                     ((win_x0, RY, 0), (win_x1, RY + 0.12, win_z0)), ((win_x0, RY, win_z1), (win_x1, RY + 0.12, RZ))):
        B.box("Walls", wall, lo, hi)
    for (lo, hi) in (((-RX, -RY, 0), (-RX + 0.012, RY, 1.0)), ((RX - 0.012, -RY, 0), (RX, RY, 1.0)),
                     ((-RX, -RY, 0), (RX, -RY + 0.012, 1.0))):
        B.box("Wainscot", wains, lo, hi)
    B.box("Skirting", M.paint("HospSkirt", (0.3, 0.33, 0.32), rough=0.5), (-RX, -RY, 0), (RX, -RY + 0.02, 0.09))
    alu = M.metal("Alu", (0.62, 0.64, 0.66), rough=0.35)
    for (lo, hi) in (((win_x0, RY - 0.02, win_z0 - 0.05), (win_x1, RY + 0.05, win_z0)),
                     ((win_x0, RY - 0.02, win_z1), (win_x1, RY + 0.05, win_z1 + 0.05)),
                     ((win_x0 - 0.05, RY - 0.02, win_z0), (win_x0, RY + 0.05, win_z1)),
                     ((win_x1, RY - 0.02, win_z0), (win_x1 + 0.05, RY + 0.05, win_z1)),
                     (((win_x0 + win_x1) / 2 - 0.025, RY - 0.02, win_z0), ((win_x0 + win_x1) / 2 + 0.025, RY + 0.05, win_z1))):
        B.box("WinFrame", alu, lo, hi)
    B.box("Sill", M.paint("Sill", (0.85, 0.84, 0.8), rough=0.4), (win_x0 - 0.1, RY - 0.18, win_z0 - 0.06), (win_x1 + 0.1, RY, win_z0))
    B.box("Glass", M.glass("WindowGlass"), (win_x0, RY + 0.03, win_z0), (win_x1, RY + 0.04, win_z1), no_shadow=True)
    # venetian blinds, slats tilted half open: they stripe the sunlight across the room
    slat_m = M.paint("Blinds", (0.85, 0.83, 0.78), rough=0.45)
    bm = B.bm("Blinds", slat_m)
    # blinds pulled two thirds down; slats nearly flat so the low sun streams through in stripes
    n = 22
    blind_low = win_z0 + 0.42
    for k in range(n):
        z = win_z1 - 0.03 - k * (win_z1 - blind_low) / n
        r = U.bm_box(bm, (win_x1 - win_x0 - 0.02, 0.05, 0.003), ((win_x0 + win_x1) / 2, RY - 0.06, z))
        bmesh.ops.rotate(bm, verts=r, cent=((win_x0 + win_x1) / 2, RY - 0.06, z),
                         matrix=Matrix.Rotation(math.radians(-14), 3, "X"))
    B.box("Blinds", slat_m, (win_x0 + 0.01, RY - 0.09, blind_low - 0.03), (win_x1 - 0.01, RY - 0.03, blind_low))
    for x in (win_x0 + 0.15, win_x1 - 0.15):
        U.bm_cone_between(B.bm("Cords", M.paint("Cord", (0.8, 0.8, 0.78), rough=0.6)), (x, RY - 0.07, win_z0), (x, RY - 0.07, win_z1), 0.002, 0.002, segs=4)
    curtain = M.paint("HospCurtain", (0.62, 0.72, 0.62), rough=0.9)
    for xc in (win_x0 - 0.35, win_x1 + 0.35):
        bm = B.bm("Curtains", curtain, smooth=True)
        for k in range(9):
            x = xc - 0.32 + k * 0.08
            U.bm_cyl(bm, 0.045, 0.045, 2.35, segs=8, loc=(x, RY - 0.14 + 0.025 * math.sin(k * 2.1), 1.22))
    B.box("CurtainRail", alu, (win_x0 - 0.75, RY - 0.17, 2.42), (win_x1 + 0.75, RY - 0.12, 2.45))
    # door, clock, picture, ceiling lamp
    B.box("Door", M.wood("HospDoor", light=(0.66, 0.55, 0.42), dark=(0.52, 0.42, 0.3), scale=4.0), (-2.2, -RY - 0.02, 0), (-1.15, -RY + 0.02, 2.1))
    B.box("DoorFrame", alu, (-2.26, -RY - 0.03, 0), (-1.09, -RY + 0.04, 2.16))
    B.box("Door", M.wood("HospDoor"), (-2.2, -RY + 0.025, 0), (-1.15, -RY + 0.03, 2.1))
    B.box("Handle", M.metal("HandleSteel", (0.7, 0.7, 0.72), rough=0.2), (-1.35, -RY + 0.03, 0.95), (-1.25, -RY + 0.07, 0.98))
    white = M.paint("WhitePlastic", (0.88, 0.88, 0.85), rough=0.4)
    U.bm_cyl(B.bm("Clock", white, smooth=True), 0.16, 0.16, 0.04, segs=32, loc=(-RX + 0.02, -0.6, 2.2),
             rot=Euler((0, math.radians(90), 0)).to_quaternion())
    B.box("Picture", M.wood("Frame", light=(0.35, 0.22, 0.12), dark=(0.22, 0.13, 0.07)), (-RX, 0.2, 1.4), (-RX + 0.03, 1.1, 2.0))
    B.box("PictureArt", M.paint("PictureArt", (0.35, 0.55, 0.65), rough=0.6), (-RX + 0.031, 0.25, 1.45), (-RX + 0.033, 1.05, 1.95))
    B.box("Lamp", white, (-0.6, -0.4, RZ - 0.06), (0.6, 0.4, RZ))
    return B


def build_bed(B):
    bed_frame = M.metal("BedFrame", (0.78, 0.79, 0.8), rough=0.3)
    x0, x1 = BED_C.x - BED_L / 2, BED_C.x + BED_L / 2
    y0, y1 = BED_C.y - BED_W / 2, BED_C.y + BED_W / 2
    for x in (x0 + 0.05, x1 - 0.05):
        for y in (y0 + 0.05, y1 - 0.05):
            U.bm_cyl(B.bm("BedFrame", bed_frame, smooth=True), 0.025, 0.025, 0.42, segs=10, loc=(x, y, 0.27))
            U.bm_cyl(B.bm("Wheels", M.paint("Rubber", (0.04, 0.04, 0.04), rough=0.7), smooth=True), 0.045, 0.045, 0.03,
                     segs=12, loc=(x, y, 0.05), rot=Euler((math.radians(90), 0, 0)).to_quaternion())
    B.box("BedFrame", bed_frame, (x0, y0, 0.44), (x1, y1, 0.48))
    B.box("Headboard", M.paint("Headboard", (0.62, 0.7, 0.75), rough=0.4), (x1 - 0.03, y0, 0.48), (x1 + 0.03, y1, 1.15), bevel=0.02)
    B.box("Headboard", M.paint("Headboard"), (x0 - 0.03, y0, 0.48), (x0 + 0.03, y1, 0.85), bevel=0.02)
    B.box("Mattress", M.paint("Sheet", (0.9, 0.9, 0.88), rough=0.85), (x0 + 0.04, y0 + 0.02, 0.48), (x1 - 0.04, y1 - 0.02, MATTRESS_TOP), bevel=0.04)
    for y in (y0 - 0.02, y1 + 0.02):
        for k in range(5):
            x = x0 + 0.5 + k * 0.25
            U.bm_cyl(B.bm("Rails", bed_frame, smooth=True), 0.012, 0.012, 0.32, segs=8, loc=(x, y, MATTRESS_TOP + 0.08))
        U.bm_cone_between(B.bm("Rails", bed_frame, smooth=True), (x0 + 0.45, y, MATTRESS_TOP + 0.24), (x0 + 1.55, y, MATTRESS_TOP + 0.24), 0.018, 0.018, segs=10)
    bm = B.bm("Pillow", M.paint("Pillow", (0.94, 0.94, 0.92), rough=0.8), smooth=True)
    U.bm_sphere(bm, 1.0, loc=(x1 - 0.32, BED_C.y, MATTRESS_TOP + 0.07), scale=(0.24, 0.36, 0.08), segs=20, rings=10)
    return x0, x1, y0, y1


def build_equipment(B, col):
    steel = M.metal("IVSteel", (0.75, 0.76, 0.77), rough=0.25)
    pole = Vector((BED_C.x + 0.85, BED_C.y + 0.85, 0))
    U.bm_cyl(B.bm("IV", steel, smooth=True), 0.014, 0.014, 2.0, segs=10, loc=pole + Vector((0, 0, 1.0)))
    for k in range(5):
        a = 2 * math.pi * k / 5
        U.bm_cone_between(B.bm("IV", steel, smooth=True), pole + Vector((0, 0, 0.08)),
                          pole + Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.03)), 0.012, 0.012, segs=6)
    U.bm_cone_between(B.bm("IV", steel, smooth=True), pole + Vector((-0.12, 0, 1.95)), pole + Vector((0.12, 0, 1.95)), 0.008, 0.008, segs=6)
    bag = M.glass("IVBag", tint=(0.92, 0.95, 0.98), reflect=0.25, rough=0.15)
    U.bm_sphere(B.bm("IVBag", bag, smooth=True, no_shadow=True), 1.0, loc=pole + Vector((0.12, 0, 1.75)), scale=(0.07, 0.03, 0.12), segs=14, rings=8)
    # bedside table with flowers and a glass of water
    t = Vector((BED_C.x + 0.55, BED_C.y - 0.9, 0))
    wood = M.wood("TableWood", light=(0.62, 0.46, 0.3), dark=(0.48, 0.34, 0.2), scale=5.0)
    B.box("Table", wood, (t.x - 0.25, t.y - 0.22, 0), (t.x + 0.25, t.y + 0.22, 0.7), bevel=0.01)
    U.bm_cyl(B.bm("Vase", M.glass("VaseGlass", tint=(0.7, 0.85, 0.95), reflect=0.3), smooth=True, no_shadow=True),
             0.045, 0.035, 0.2, segs=16, loc=t + Vector((-0.1, 0.05, 0.8)))
    rnd = random.Random(9)
    for k in range(7):
        top = t + Vector((-0.1 + rnd.uniform(-0.06, 0.06), 0.05 + rnd.uniform(-0.06, 0.06), 0.98 + rnd.uniform(0, 0.12)))
        U.bm_cone_between(B.bm("Stems", M.paint("Stem", (0.12, 0.35, 0.1), rough=0.6)), t + Vector((-0.1, 0.05, 0.75)), top, 0.004, 0.003, segs=5)
        U.bm_ico(B.bm(f"Petals{k % 3}", M.paint(f"Petal{k % 3}", ((0.95, 0.85, 0.2), (0.95, 0.4, 0.5), (0.95, 0.95, 0.9))[k % 3], rough=0.6), smooth=True),
                 0.035, loc=top, scale=(1, 1, 0.6), subdiv=2)
    U.bm_cyl(B.bm("WaterGlass", M.glass("Tumbler", tint=(0.9, 0.95, 1.0), reflect=0.3), smooth=True, no_shadow=True),
             0.032, 0.028, 0.1, segs=16, loc=t + Vector((0.12, -0.05, 0.75)))
    # heart monitor on an arm next to the bed head
    mon = Vector((BED_C.x + 1.25, BED_C.y + 0.55, 1.55))
    B.box("Monitor", M.paint("MonitorBody", (0.82, 0.83, 0.8), rough=0.4), mon - Vector((0.06, 0.2, 0.15)), mon + Vector((0.06, 0.2, 0.15)), bevel=0.015)
    U.bm_cone_between(B.bm("Monitor", M.paint("MonitorBody")), mon + Vector((0.06, 0, -0.1)), Vector((RX, mon.y, mon.z - 0.1)), 0.02, 0.02, segs=8)
    B.box("Screen", M.paint("ScreenBlack", (0.01, 0.015, 0.012), rough=0.15), mon + Vector((-0.062, -0.17, -0.12)), mon + Vector((-0.06, 0.17, 0.12)))
    return mon


def ecg_trace(col, mon):
    """The green trace on the monitor: a sweeping heartbeat line. Object property 'sweep' (cycles,
    animate linearly) moves the bright head; 'flat' 0..1 flattens the line."""
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
    n, width = 900, 0.005           # dense enough that the narrow QRS spike is never skipped
    beats = 3
    pts = []
    for i in range(n + 1):
        u = i / n
        p = (u * beats) % 1.0
        y = (0.62 * math.exp(-((p - 0.42) / 0.016) ** 2) - 0.2 * math.exp(-((p - 0.39) / 0.014) ** 2)
             - 0.16 * math.exp(-((p - 0.452) / 0.014) ** 2) + 0.09 * math.exp(-((p - 0.25) / 0.03) ** 2)
             + 0.14 * math.exp(-((p - 0.66) / 0.05) ** 2))
        pts.append((u, y))
    rows = []
    for u, y in pts:
        pos = mon + Vector((-0.064, -0.16 + 0.32 * u, -0.03 + y * 0.12))
        rows.append((bm.verts.new(pos - Vector((0, 0, width))), bm.verts.new(pos + Vector((0, 0, width))), u))
    for (a1, a2, ua), (b1, b2, ub) in zip(rows, rows[1:]):
        f = bm.faces.new((a1, b1, b2, a2))
        for loop, uv in zip(f.loops, ((ua, 0), (ub, 0), (ub, 1), (ua, 1))):
            loop[uvl].uv = uv
    ob = U.mesh_object("ECG_Trace", bm, col, mats=[mat])
    ob["sweep"] = 0.0
    flat = ob.shape_key_add(name="Basis")
    sk = ob.shape_key_add(name="Flat")
    for kv, v in zip(sk.data, ob.data.vertices):
        kv.co = Vector((v.co.x, v.co.y, mon.z - 0.03 + (v.co.z - mon.z + 0.03) * 0.0 + (width if (v.index % 2) else -width)))
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


def build_hospital(scene):
    root = U.collection("Hospital", scene.collection)
    B = build_room(root)
    x0, x1, y0, y1 = build_bed(B)
    mon = build_equipment(B, root)
    objs = B.finish()
    ecg = ecg_trace(root, mon)
    stool_m = M.metal("StoolSteel", (0.5, 0.52, 0.55), rough=0.35)
    bm = bmesh.new()
    U.bm_cyl(bm, 0.19, 0.19, 0.05, segs=24, loc=STOOL + Vector((0, 0, STOOL_TOP - 0.025)))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        U.bm_cone_between(bm, STOOL + Vector((math.cos(a) * 0.13, math.sin(a) * 0.13, STOOL_TOP - 0.05)),
                          STOOL + Vector((math.cos(a) * 0.18, math.sin(a) * 0.18, 0)), 0.015, 0.015, segs=8)
    U.mesh_object("Stool", bm, root, mats=[stool_m], smooth=True)
    # outside: a skyline under the setting sun
    bm = bmesh.new()
    rnd = random.Random(2)
    for k in range(40):
        x = -60 + k * 3.2 + rnd.uniform(-1, 1)
        h = rnd.uniform(4, 18)
        U.bm_box(bm, (rnd.uniform(2, 4), 3, h), (x, 45 + rnd.uniform(0, 20), h / 2 - 8))
    U.mesh_object("Skyline", bm, root, mats=[M.paint("SkylineDusk", (0.08, 0.05, 0.09), rough=1.0)])
    sun_disc = U.mesh_object("SunDisc", _disc(), root, mats=[U.emission("SunDiscMat", (1.0, 0.55, 0.2), 25.0)])
    sun_disc.location = -SUN_DIR * 140
    sun_disc.rotation_euler = SUN_DIR.to_track_quat("Z", "Y").to_euler()
    sun_disc.scale = (4, 4, 4)
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
    return {"ecg": ecg, "monitor": mon, "bed": (x0, x1, y0, y1), "objs": objs}


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
    """Hands folded on his chest, on top of the blanket (elbows sink into the mattress)."""
    for s, dy in (("L", -0.07), ("R", 0.07)):
        p = Vector((pelvis.x + 0.24, pelvis.y + dy, pelvis.z + 0.155))
        actor.hand_to(f, s, p, pose="relaxed", settle=False)


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
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    ob = U.mesh_object(name, bm, col, mats=[M.paint("BlanketMat", (0.55, 0.68, 0.82), rough=0.9)], smooth=True)
    ob.modifiers.new("Thick", "SOLIDIFY").thickness = 0.02
    sm = ob.modifiers.new("Soft", "SMOOTH")
    sm.factor, sm.iterations = 0.8, 6
    return ob
