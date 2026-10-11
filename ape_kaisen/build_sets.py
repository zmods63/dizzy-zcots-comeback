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
    from ak import cast as C, mats as M
    M._cache.clear()
    C._T.clear()
    C._POLE_ANGLE.clear()


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


if __name__ == "__main__":
    which = sys.argv[1:] or ["school", "hospital"]
    if "school" in which:
        school()
    if "hospital" in which:
        hospital()
