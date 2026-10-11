"""Build the two set files: ape_kaisen_school.blend and ape_kaisen_hospital.blend.

Run:  python3 build_sets.py      (needs the `bpy` module, Blender 5.x)
Both files are self-contained (textures and fonts packed) and set up for EEVEE.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from ak import characters as CH  # noqa: E402
from ak import hospital as HO  # noqa: E402
from ak import motion as MO  # noqa: E402
from ak import render as R  # noqa: E402
from ak import school as S  # noqa: E402
from ak import util as U  # noqa: E402


def add_camera(scene, name, loc, aim, lens):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = U.look_rotation(loc, aim).to_euler()
    cam.data.lens = lens
    cam.data.clip_end = 4000
    return cam


def finish(scene, path, exposure):
    R.setup(scene, preview=False, res=(1920, 1080), samples=64)
    R.compositor(scene, bloom=0.9, threshold=1.0)
    scene.view_settings.exposure = exposure
    scene.frame_start, scene.frame_end = 1, 250
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("saved", path, round(os.path.getsize(path) / 1e6, 1), "MB")


def fresh_file():
    """New empty file; drop module caches that point at datablocks of the previous file."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    from ak import cast as C, decals as D, kit as K, mats as M, texgen as T
    M._cache.clear()
    C._T.clear()
    C._POLE_ANGLE.clear()
    K.reset()
    T.reset()
    D.reset()


def school():
    fresh_file()
    scene = bpy.context.scene
    scene.name = "School"
    out = S.build_school(scene)
    m = out["marks"]
    rz, hz = m["roof_z"], m["hall_floor_z"]
    cams = [
        add_camera(scene, "Cam_Yard", (10, -36, 1.4), (2, 0, 13.0), 20),
        add_camera(scene, "Cam_Street_Pole", (20.5, -46.5, 1.6), (15, -40.95, 10.5), 26),
        add_camera(scene, "Cam_Rooftop", (-15, -3.5, rz + 1.5), (16, 2.5, rz + 2.4), 26),
        add_camera(scene, "Cam_Hallway", (-21.5, 4.6, hz + 1.1), (10, 4.0, hz + 1.6), 24),
        add_camera(scene, "Cam_Clubroom", (-16.8, -5.2, 7.55 + 1.6), tuple(m["club_desk"]), 22),
    ]
    scene.camera = cams[0]
    finish(scene, os.path.join(HERE, "ape_kaisen_school.blend"), exposure=1.3)


def hospital():
    fresh_file()
    scene = bpy.context.scene
    scene.name = "Hospital"
    h = HO.build_hospital(scene)
    cast = U.collection("Cast", scene.collection)
    gp = MO.Actor(CH.make("Grandpa", U.collection("Grandpa", cast)), (0, 0), 0.0)
    pelvis = HO.lay_in_bed(gp, 1)
    HO.grandpa_hands(gp, 1, pelvis)
    yuji = MO.Actor(CH.make("Yuji", U.collection("Yuji", cast)), (HO.STOOL.x, HO.STOOL.y),
                    yaw=math.radians(180), ground=HO.STOOL_TOP)
    yuji.planted = {"L": False, "R": False}
    yuji.body_to(1, height=MO.H_SIT, pitch=0.12)
    yuji.hand_to(1, "R", Vector((HO.BED_C.x + 0.1, HO.BED_C.y - HO.BED_W / 2 + 0.1, HO.MATTRESS_TOP + MO.WRIST)),
                 plant=1.0, rot=MO.plant_rotation("R", yuji.yaw), settle=False)
    yuji.fingers(1, "R", "flat")
    yuji.hand_to(1, "L", yuji.local(0.22, 0.12, 0.08, height=MO.H_SIT), pose="relaxed", settle=False)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    x0, x1, y0, y1 = h["bed"]
    HO.drape_blanket(U.collection("Hospital"), [gp.ape.body], (x0 + 0.08, pelvis.x + 0.2), (y0 - 0.05, y1 + 0.05),
                     HO.MATTRESS_TOP + 0.02)
    cams = [
        add_camera(scene, "Cam_Wide", (-2.3, -1.9, 1.55), (0.6, 0.6, 0.75), 22),
        add_camera(scene, "Cam_Bedside", (0.35, -1.55, 1.3), (1.15, 0.15, 0.8), 32),
        add_camera(scene, "Cam_Monitor", (1.2, -0.5, 1.5), (2.0, 0.7, 1.55), 50),
    ]
    scene.camera = cams[0]
    finish(scene, os.path.join(HERE, "ape_kaisen_hospital.blend"), exposure=0.6)


def props():
    """Every prop of the new kit (and the user's re-textured models) laid out on a studio floor,
    each marked as an asset so they show up in Blender's Asset Browser."""
    fresh_file()
    scene = bpy.context.scene
    scene.name = "Props"
    from ak import assets as A, assets_hosp as AH, kit as K, refassets as RA
    libs = [("School & Street", A), ("Hospital", AH), ("Your models", RA)]
    root = U.collection("Props", scene.collection)
    y = 0.0
    for title, lib in libs:
        col = U.collection(title, root)
        x, row_d = 0.0, 0.0
        label = U.text_object("Label_" + title, title, col, size=0.6, align="LEFT")
        label.location = (-1.0, y - 1.2, 0.01)
        for name in lib.BUILDERS:
            me = lib.get(name)
            lo = Vector(tuple(min(v.co[i] for v in me.vertices) for i in range(3)))
            hi = Vector(tuple(max(v.co[i] for v in me.vertices) for i in range(3)))
            size = hi - lo
            if x + size.x > 40.0:
                x, y, row_d = 0.0, y + row_d + 1.5, 0.0
            ob = K.place(me, col, (x - lo.x, y - lo.y, -min(0.0, lo.z)), name=name)
            ob.asset_mark()
            ob.asset_data.description = f"Ape Kaisen prop: {name}"
            tag = U.text_object("Tag_" + name, name, col, size=0.12, align="LEFT")
            tag.location = (x, y - 0.35, 0.01)
            x += size.x + 0.8
            row_d = max(row_d, size.y)
        y += row_d + 4.0
    ground = bpy.data.meshes.new("StudioFloor")
    ground.from_pydata([(-10, -10, 0), (60, -10, 0), (60, y + 10, 0), (-10, y + 10, 0)], [], [(0, 1, 2, 3)])
    gob = bpy.data.objects.new("StudioFloor", ground)
    root.objects.link(gob)
    ground.materials.append(U.principled("StudioFloor", (0.32, 0.33, 0.35), rough=0.8))
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.75, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = world
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy, sun.data.angle = 3.5, math.radians(3)
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    root.objects.link(sun)
    add_camera(scene, "Cam_Overview", (20, -18, 22), (20, y * 0.4, 0), 24)
    scene.camera = scene.objects["Cam_Overview"]
    finish(scene, os.path.join(HERE, "ape_kaisen_props.blend"), exposure=0.0)


if __name__ == "__main__":
    which = sys.argv[1:] or ["school", "hospital", "props"]
    if "school" in which:
        school()
    if "hospital" in which:
        hospital()
    if "props" in which:
        props()
