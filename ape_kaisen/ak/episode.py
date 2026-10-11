"""Ape Kaisen episode 1, animated. Each location is its own scene with one continuous timeline;
cameras cut on timeline markers (Blender switches the active camera at each marker).

hospital_part(scene): Yuji visits Grandpa at sunset; his last words; the monitor goes flat.
"""

import math
import random

import bpy
from mathutils import Vector

from . import characters as CH
from . import hospital as HO
from . import kit as K
from . import motion as MO
from . import school as S
from . import util as U

FPS = 24
PI = math.pi


# ----------------------------------------------------------------- cameras

def camera(scene, name, loc, aim, lens, col=None):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    (col or scene.collection).objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.clip_end = 4000
    aim_cam(cam, loc, aim)
    return cam


def aim_cam(cam, loc, aim, f=None, roll=0.0):
    cam.location = loc
    cam.rotation_euler = U.look_rotation(loc, aim, roll=roll).to_euler()
    if f is not None:
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)


def drift(cam, f0, f1, loc0, aim0, loc1, aim1, shake=0.0, seed=0):
    """Slow camera move (eased) with optional hand-held wobble, keyed every 2 frames."""
    rnd = random.Random(seed)
    loc0, aim0, loc1, aim1 = Vector(loc0), Vector(aim0), Vector(loc1), Vector(aim1)
    for f in range(f0, f1 + 1, 2):
        t = MO.smooth((f - f0) / max(1, f1 - f0))
        wob = Vector((math.sin(f * 0.21 + seed), math.sin(f * 0.17 + 2 * seed), math.sin(f * 0.13 + 3 * seed))) * shake
        aim_cam(cam, loc0.lerp(loc1, t) + wob, aim0.lerp(aim1, t) + wob * 0.3, f)
        rnd.random()


def cut(scene, f, cam):
    m = scene.timeline_markers.new(cam.name, frame=f)
    m.camera = cam


def key_prop(ob, prop, f, value):
    ob[prop] = value
    ob.keyframe_insert(f'["{prop}"]', frame=f)


# ----------------------------------------------------------------- hospital

HOSP_SHOTS = {            # name: (first frame, last frame)
    "wide": (1, 132),
    "grandpa": (133, 300),
    "yuji": (301, 380),
    "monitor": (381, 476),
    "end": (477, 600),
}


def hospital_part(scene):
    """Shots 3-6. Returns the frame range."""
    h = HO.build_hospital(scene)
    cast_col = U.collection("Cast", scene.collection)
    gp_ape = CH.make("Grandpa", U.collection("Grandpa", cast_col))
    yuji_ape = CH.make("Yuji", U.collection("Yuji", cast_col))
    gp = MO.Actor(gp_ape, (0, 0), 0.0)
    pelvis = HO.lay_in_bed(gp, 1)
    HO.grandpa_hands(gp, 1, pelvis)
    yuji = MO.Actor(yuji_ape, (HO.STOOL.x, HO.STOOL.y), yaw=math.radians(180), ground=HO.STOOL_TOP)
    yuji.planted = {"L": False, "R": False}
    bed_edge = Vector((HO.BED_C.x + 0.1, HO.BED_C.y - HO.BED_W / 2 + 0.1, HO.MATTRESS_TOP + MO.WRIST))
    rest_l = yuji.local(0.22, 0.12, 0.08, height=MO.H_SIT)

    def yuji_seat(f, pitch=0.12, roll=0.0):
        yuji.body_to(f, height=MO.H_SIT, pitch=pitch, roll=roll)

    # Yuji: sitting, right hand on the bed, left hand on his lap (keys go in time order: the
    # Actor remembers where its hands are)
    g0, g1 = HOSP_SHOTS["grandpa"]

    def breathe(fa, fb, pitch=0.12):
        for f in range(fa, fb, 12):
            yuji_seat(f, pitch=pitch + 0.015 * math.sin(f / 24 * 2 * PI * 0.3))

    yuji.hand_to(1, "R", bed_edge, plant=1.0, rot=MO.plant_rotation("R", yuji.yaw), settle=False)
    yuji.fingers(1, "R", "flat")
    yuji.hand_to(1, "L", rest_l, pose="relaxed", settle=False)
    breathe(1, g0 + 44)
    yuji.head(1, 0, -4)
    yuji.talk(22, 70, loud=0.55, seed=1)               # "Gramps, the nurse says you're not eating."
    yuji.head(30, -6, -2)
    yuji.blink(48)
    yuji.head(84, 4, 2, roll=-6)                       # listens to the grumbling
    yuji.blink(110)

    # Grandpa: stares at the ceiling, then turns to Yuji and grumbles
    gp.head(1, 0, 4)
    gp.eyelids(1, 0.35)
    gp.head(62, 0, 4)
    gp.head(78, 28, 0)
    gp.talk(84, 124, loud=0.35, rate=2.8, seed=2)       # "Shut up. Go to your club."
    gp.blink(70)

    # Grandpa's last words, his hand reaching for Yuji
    gp.head(g0 + 4, 30, 2)
    gp.eyelids(g0 + 4, 0.3)
    gp.talk(g0 + 12, g0 + 70, loud=0.32, rate=2.5, seed=3)       # "Yuji... you're strong..."
    hand0 = Vector((pelvis.x + 0.24, pelvis.y - 0.06, pelvis.z + 0.135))
    reach = Vector((pelvis.x + 0.3, HO.BED_C.y - HO.BED_W / 2 - 0.05, HO.MATTRESS_TOP + 0.22))
    gp.hand_to(g0 + 30, "L", hand0, pose="relaxed", plant=1.0,
               rot=MO.plant_rotation("L", 0.0, normal=Vector((0, 0, 1)), along=Vector((0.35, 1.0, 0))), settle=False)
    gp.hand_to(g0 + 52, "L", reach, pose="relaxed", plant=0.0, settle=False)
    gp.talk(g0 + 84, g0 + 150, loud=0.3, rate=2.4, seed=4)      # "...so help people. Don't die alone like me."
    gp.eyelids(g0 + 120, 0.55)
    gp.blink(g0 + 100)
    yuji.head(g0 + 40, -10, 4)
    # Yuji takes the hand
    take = reach + Vector((0.02, -0.04, -0.02))
    yuji.hand_to(g0 + 44, "R", bed_edge, plant=1.0, rot=MO.plant_rotation("R", yuji.yaw), settle=False)
    yuji.hand_to(g0 + 62, "R", take, pose="fist", plant=0.0, settle=False)
    yuji_seat(g0 + 62, pitch=0.2)
    breathe(g0 + 74, HOSP_SHOTS["end"][0], pitch=0.2)

    # Yuji's face
    y0_, y1_ = HOSP_SHOTS["yuji"]
    yuji.eyelids(y0_, 0.0)
    yuji.head(y0_ + 6, -14, 6, roll=4)
    yuji.blink(y0_ + 30)
    yuji.shape(y0_ + 20, "MouthOpen", 0.0)
    yuji.shape(y0_ + 30, "MouthOpen", 0.25)
    yuji.shape(y1_, "MouthOpen", 0.15)

    # the monitor
    ecg = h["ecg"]
    m0, m1 = HOSP_SHOTS["monitor"]
    flat_at = m0 + 52
    sweep, rate = 0.0, 0.4 / FPS          # screen passes per frame (72 bpm)
    for f in range(1, 601):
        if f > m0:
            rate = max(rate * 0.985, 0.18 / FPS)
        sweep += rate
        if f % 3 == 0 or f in (1, 600):
            key_prop(ecg, "sweep", f, sweep)
    U.set_interpolation(ecg, "LINEAR")
    sk = ecg.data.shape_keys.key_blocks["Flat"]
    sk.value = 0.0
    sk.keyframe_insert("value", frame=flat_at - 10)
    sk.value = 1.0
    sk.keyframe_insert("value", frame=flat_at + 6)
    gp.eyelids(flat_at - 6, 1.0)
    gp.head(flat_at + 10, 8, 3)

    # the end: the hand goes limp, Yuji bows his head
    e0, e1 = HOSP_SHOTS["end"]
    limp = Vector((pelvis.x + 0.28, HO.BED_C.y - HO.BED_W / 2 + 0.12, HO.MATTRESS_TOP + MO.WRIST))
    gp.hand_to(e0 + 8, "L", reach + Vector((0, 0.03, -0.05)), pose="relaxed", plant=0.0, settle=False)
    gp.hand_to(e0 + 20, "L", limp, pose="relaxed", plant=1.0,
               rot=MO.plant_rotation("L", 0.0, normal=Vector((0, 0, 1)), along=Vector((0.5, -1.0, 0))), settle=False)
    yuji.hand_to(e0 + 8, "R", take, pose="fist", settle=False)
    yuji_seat(e0 + 8, pitch=0.2)
    yuji.hand_to(e0 + 22, "R", limp + Vector((0.0, -0.06, 0.03)), pose="relaxed", plant=0.0, settle=False)
    yuji_seat(e0 + 40, pitch=0.42)
    yuji.head(e0 + 10, -8, 0)
    yuji.head(e0 + 44, 0, -22)
    yuji.eyelids(e0 + 44, 0.6)
    yuji_seat(e1, pitch=0.44)
    yuji.head(e1, 0, -24)

    # light: the sun sinks during the scene
    sun = bpy.data.objects["Sunset"]
    sun.data.energy = 6.0
    sun.data.keyframe_insert("energy", frame=1)
    sun.data.energy = 3.2
    sun.data.keyframe_insert("energy", frame=600)

    # blanket over Grandpa (draped once, from frame 1)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    x0, x1, y0, y1 = h["bed"]
    HO.drape_blanket(U.collection("Hospital"), [gp_ape.body], (x0 + 0.08, pelvis.x + 0.2), (y0 - 0.05, y1 + 0.05),
                     HO.MATTRESS_TOP + 0.02)

    # cameras
    cams = U.collection("Cameras", scene.collection)
    wide = camera(scene, "Cam_Wide", (-2.3, -1.9, 1.55), (0.6, 0.6, 0.75), 22, cams)
    drift(wide, 1, HOSP_SHOTS["wide"][1], (-2.3, -1.9, 1.55), (0.6, 0.6, 0.75), (-2.05, -1.62, 1.48), (0.65, 0.5, 0.78))
    grand = camera(scene, "Cam_Grandpa", (0.72, -0.62, 1.32), (1.45, 0.15, 0.85), 38, cams)
    drift(grand, g0, g1, (0.72, -0.62, 1.32), (1.45, 0.15, 0.85), (0.8, -0.5, 1.26), (1.45, 0.12, 0.84), shake=0.002, seed=1)
    yc = camera(scene, "Cam_Yuji", (1.3, -0.12, 1.2), (0.55, -0.85, 1.0), 45, cams)
    drift(yc, y0_, y1_, (1.3, -0.12, 1.2), (0.55, -0.85, 1.0), (1.22, -0.2, 1.17), (0.55, -0.85, 1.0), shake=0.002, seed=2)
    mon = camera(scene, "Cam_Monitor", (1.2, -0.5, 1.5), (2.0, 0.7, 1.55), 50, cams)
    drift(mon, m0, m1, (1.25, -0.45, 1.52), (2.0, 0.7, 1.55), (1.45, -0.15, 1.55), (2.0, 0.7, 1.55))
    end = camera(scene, "Cam_End", (-1.6, -1.6, 1.9), (0.7, 0.0, 0.7), 28, cams)
    drift(end, e0, e1, (-1.6, -1.6, 1.9), (0.7, 0.0, 0.7), (-2.2, -2.0, 2.1), (0.6, 0.1, 0.7))
    for name, cam in (("wide", wide), ("grandpa", grand), ("yuji", yc), ("monitor", mon), ("end", end)):
        cut(scene, HOSP_SHOTS[name][0], cam)
    scene.camera = wide
    scene.frame_start, scene.frame_end = 1, HOSP_SHOTS["end"][1]
    return {"actors": {"Grandpa": gp, "Yuji": yuji}, "ecg": ecg}


# ----------------------------------------------------------------- school (night)

SCHOOL_SHOTS = {
    "pole": (1, 132),          # 1: Megumi on the utility pole, on the phone with Gojo
    "drop": (133, 252),        # 2: he drops onto the school wall and into the yard
    "club": (253, 400),        # 8: the senpais open the sealed box in the club room
    "finger": (401, 470),      # 8: ...the finger glows
    "curse": (471, 600),       # 9: a curse climbs the building toward them
    "window": (601, 700),      # 9: its eyes at the club room window
    "street": (701, 784),      # 10: Yuji tears along the sidewalk
    "gate": (785, 868),        # 10: ...hops the curb and gallops through the gate
    "hall": (869, 952),        # 11: the 2F hallway run
    "roof": (953, 1040),       # 12-13: the curse holds Sasaki; Megumi summons the Divine Dogs
    "door": (1041, 1100),      # 14: Yuji bursts out of the stairwell
    "punch": (1101, 1170),     # 14: the punch
    "grab": (1171, 1230),      # 15: Yuji grabs the finger
    "swallow": (1231, 1280),   # 15: ...and swallows it
    "sukuna": (1281, 1440),    # 16: Sukuna
}


def phone_mesh():
    def build(a):
        body = K.Surf("paint", "#1C1D21", "#0B0B0D", rough=0.35, edge=0.4, name="PhoneBody")
        a.box((0.07, 0.012, 0.14), (0, 0, 0), body, bevel=0.006)
        a.plane(0.06, 0.12, (0, -0.0065, 0.002), K.Surf("glow", "#BFD8FF", strength=2.0, name="PhoneScreen"))
    return K.asset("Phone", build)


def hold_prop(me, ape, side, offset=(0, 0, 0), rot=(0, 0, 0), name=None):
    """A prop that follows a hand (parented to its IK target)."""
    ob = K.place(me, ape.col, (0, 0, 0), name=name)
    ob.parent = ape.hand[side]
    ob.location = offset
    ob.rotation_euler = rot
    return ob


def show(objs, ranges):
    """Key visibility: shown only inside the given frame ranges."""
    for ob in objs:
        U.visible(ob, ranges, start=0)


def ape_objs(ape):
    return [ape.body, ape.eyes] + [o for o in ape.col.objects if o.name.endswith("Blindfold")]


def hold(actor, f):
    """Freeze an actor from f until its next key (constant interpolation): for jumps between shots."""
    for idb in (actor.ape.arm, actor.ape.hand["L"], actor.ape.hand["R"]):
        U.set_interpolation(idb, "CONSTANT", frames={f})


def pole_stand(actor, f0, f1, top):
    """Crouched on a pole top: both palms flat on the cap, close together."""
    hands = hands_for(actor, top)
    actor.stand(f0, f1, hands=hands, breathe=0.012)
    return hands


def school_part(scene):
    """The night: shots 1-2 and 7-16."""
    out = S.build_school(scene)
    m = out["marks"]
    cast_col = U.collection("Cast", scene.collection)
    cams = U.collection("Cameras", scene.collection)
    cast = {t: CH.make(t, U.collection(t, cast_col)) for t in ("Megumi", "Yuji", "Sasaki", "Iguchi", "DogWhite", "DogBlack")}
    for t in ("DogWhite", "DogBlack"):
        cast[t].arm.scale = (CH.DOG_SCALE,) * 3
    CH.add_sukuna(cast["Yuji"])
    ctx = {"m": m, "cast": cast, "cams": cams, "scene": scene, "rnd": random.Random(7)}
    megumi_pole(ctx)
    club_room(ctx)
    curse_climb(ctx)
    yuji_dash(ctx)
    rooftop(ctx)
    scene.camera = bpy.data.objects["Cam_Pole"]
    scene.frame_start, scene.frame_end = 1, SCHOOL_SHOTS["sukuna"][1]
    return ctx


# --- shots 1-2: Megumi on the pole --------------------------------------------------

def megumi_pole(ctx):
    scene, cams, cast = ctx["scene"], ctx["cams"], ctx["cast"]
    meg_ape = cast["Megumi"]
    top = Vector((15.0, S.POLE_Y, S.POLE_H))
    meg = MO.Actor(meg_ape, (top.x, top.y), yaw=PI, ground=S.POLE_H)
    ctx["meg"] = meg
    p0, p1 = SCHOOL_SHOTS["pole"]
    pole_stand(meg, p0, p0 + 24, top)
    meg.head(p0, 10, 4)
    meg.head(p0 + 20, -6, -2)
    meg.eyelids(p0, 0.25)
    phone = hold_prop(phone_mesh(), meg_ape, "L", name="Megumi_Phone")
    show([phone], [(p0 + 30, p0 + 107)])
    ear = meg.local(0.17, 0.02, 0.5, height=MO.H_ONE)
    meg.hand_to(p0 + 30, "L", ear, pose="fist")                  # answers the phone: leans onto one hand
    meg.head(p0 + 34, -14, 2, roll=8)
    meg.blink(p0 + 50)
    meg.talk(p0 + 80, p0 + 100, loud=0.4, seed=5)               # "...tonight? Fine."
    meg.eyelids(p0 + 76, 0.4)
    meg.plant_hand(p0 + 112, "L", hands_for(meg, top)["L"])
    meg.head(p0 + 114, 0, -6)
    meg.stand(p0 + 112, p1, hands=hands_for(meg, top))
    d0, d1 = SCHOOL_SHOTS["drop"]
    # straight toward the school so he lands square on the 40 cm wall cap, palms along the wall
    meg.jump(d0, d0 + 46, (15.0, -40.12), apex=0.7, target_ground=2.1, crouch=10, land=10)
    meg.stand(d0 + 46, d0 + 60)
    meg.head(d0 + 48, 18, -10)
    meg.jump(d0 + 60, d0 + 92, (15.6, -37.6), apex=0.45, target_ground=0.0, crouch=6, land=8)
    meg.move(d0 + 92, d1, [(13.5, -30.5), (8.0, -22.0)], gait="gallop", stride=2.1, accel=8, decel=1)
    hold(meg, d1)
    cam = camera(scene, "Cam_Pole", (20.5, -46.5, 1.6), top + Vector((0, 0, 0.4)), 30, cams)
    drift(cam, p0, p1, (20.5, -46.5, 1.6), top + Vector((0, 0, 0.45)), (19.4, -45.8, 2.0), top + Vector((0, 0, 0.42)))
    cut(scene, p0, cam)
    cam2 = camera(scene, "Cam_Drop", (6.5, -49.5, 2.2), (16.5, -40.5, 6.0), 24, cams)
    drift(cam2, d0, d1, (6.5, -49.5, 2.2), (16.5, -40.5, 6.0), (5.0, -48.5, 2.6), (13.0, -33.0, 2.0))
    cut(scene, d0, cam2)


# --- shot 8: the club room ------------------------------------------------------------

def club_room(ctx):
    from . import props as P
    scene, cams, cast, m = ctx["scene"], ctx["cams"], ctx["cast"], ctx["m"]
    desk = Vector(m["club_desk"])
    z0 = desk.z - 0.71
    seat = z0 + 0.43
    c0, c1 = SCHOOL_SHOTS["club"]
    f0, f1 = SCHOOL_SHOTS["finger"]
    w0, w1 = SCHOOL_SHOTS["window"]
    col = U.collection("Club_Story", scene.collection)
    box, lid, seals = P.make_box(col)
    box.location = desk + Vector((0, 0, 0.0015))
    finger = P.make_finger(col)
    finger.parent = box
    finger.location = (-0.06, 0.0, 0.02)
    finger.rotation_euler = (0, 0, -PI / 2)
    ctx["box"], ctx["lid"], ctx["finger"] = box, lid, finger
    top = desk.z
    sas = MO.Actor(cast["Sasaki"], (desk.x - 0.35, desk.y - 0.72), yaw=PI, ground=seat)
    igu = MO.Actor(cast["Iguchi"], (desk.x + 0.4, desk.y + 0.72), yaw=0.0, ground=seat)
    ctx["sas"], ctx["igu"] = sas, igu
    for a, sy in ((sas, -1), (igu, 1)):
        a.planted = {"L": False, "R": False}
        for side, dx in (("L", -0.16), ("R", 0.16)):
            p = Vector((a.pos.x + dx * (1 if sy < 0 else -1), desk.y + sy * 0.36, top + MO.WRIST))
            a.hand_to(c0, side, p, plant=1.0, rot=MO.plant_rotation(side, a.yaw), settle=False)
            a.fingers(c0, side, "flat")
        a.body_to(c0, height=MO.H_SIT, pitch=0.18)
    for f in range(c0, c0 + 48, 12):
        sas.body_to(f, height=MO.H_SIT, pitch=0.18 + 0.02 * math.sin(f * 0.3))
        igu.body_to(f, height=MO.H_SIT, pitch=0.16 + 0.02 * math.sin(f * 0.27 + 1))
    sas.talk(c0 + 10, c0 + 46, loud=0.5, seed=8)          # "It's real. A real cursed object."
    igu.head(c0 + 12, 8, -4)
    igu.talk(c0 + 52, c0 + 70, loud=0.4, seed=9)          # "...should we really open it?"
    sas.head(c0 + 50, -10, -12)
    # Sasaki presses both palms on the lid, the talismans burn away
    lid_top = top + P.BOX_H + MO.WRIST
    on_lid = {"L": Vector((desk.x - 0.08, desk.y - 0.02, lid_top)), "R": Vector((desk.x + 0.08, desk.y - 0.02, lid_top))}
    for side in "LR":
        sas.hand_to(c0 + 80, side, on_lid[side] + Vector((0, -0.12, 0.08)), pose="relaxed", settle=False)
        sas.hand_to(c0 + 92, side, on_lid[side], plant=1.0, rot=MO.plant_rotation(side, sas.yaw), settle=False)
    sas.body_to(c0 + 80, height=MO.H_SIT, pitch=0.3)
    sas.body_to(c0 + 92, height=MO.H_SIT, pitch=0.36)
    key_prop(seals, "burn", c0 + 96, 0.0)
    key_prop(seals, "burn", c0 + 130, 1.05)
    # ...and lifts the lid off
    lid.location = lid.location.copy()
    lid.keyframe_insert("location", frame=c0 + 132)
    lid.keyframe_insert("rotation_euler", frame=c0 + 132)
    lifted = Vector((0.0, -0.2, P.BOX_H + 0.2))
    for side in "LR":
        sas.hand_to(f0 + 6, side, box.location + lifted + Vector((-0.08 if side == "L" else 0.08, 0, 0.03 + MO.WRIST)),
                    pose="flat", settle=False)
    lid.location = lifted
    lid.rotation_euler = (-0.5, 0.0, 0.15)
    lid.keyframe_insert("location", frame=f0 + 6)
    lid.keyframe_insert("rotation_euler", frame=f0 + 6)
    sas.body_to(f0 + 6, height=MO.H_SIT, pitch=0.05)
    # the finger wakes up: veins pulse red, the candles gutter
    glow = finger.data.materials[0].node_tree.nodes["VeinGlow"].outputs[0]
    for f, v in ((f0, 0.0), (f0 + 12, 4.0), (f0 + 22, 0.8), (f0 + 34, 6.0), (f0 + 46, 1.0), (f0 + 58, 8.0)):
        glow.default_value = v
        glow.keyframe_insert("default_value", frame=f)
    igu.body_to(f0 + 20, height=MO.H_SIT, pitch=-0.15)          # leans back
    igu.head(f0 + 20, 0, 10)
    igu.eyelids(f0 + 10, 0.0)
    sas.head(f0 + 14, 0, -18)
    for i, lo in enumerate(o for o in bpy.data.objects if o.name.startswith("Candle") and o.type == "LIGHT"):
        rnd = random.Random(i)
        for f in range(c0, w1 + 1, 3):
            e = 4.0 * (0.85 + 0.3 * rnd.random())
            if f >= f0:
                e *= 0.55 + 0.9 * rnd.random()
            if f >= w0 + 70:
                e = 0.0
            lo.data.energy = e
            lo.data.keyframe_insert("energy", frame=f)
    flames = bpy.data.objects.get("CandleFlames")
    if flames:
        show([flames], [(0, w0 + 69)])
    # the window: they turn and scream
    for a, yaw_h in ((sas, -40), (igu, 35)):
        a.head(w0 + 30, yaw_h, 6)
        a.eyelids(w0 + 30, 0.0)
        a.talk(w0 + 40, w0 + 70, loud=1.0, rate=5.0, seed=10)
    for a in (sas, igu):
        a.body_to(w1, height=MO.H_SIT, pitch=-0.05)
        hold(a, w1)

    cw = camera(scene, "Cam_Club", (desk.x + 2.0, desk.y - 2.1, z0 + 1.6), desk + Vector((0, 0, 0.1)), 28, cams)
    drift(cw, c0, c0 + 79, (desk.x + 2.0, desk.y - 2.1, z0 + 1.6), desk + Vector((0, 0, 0.1)),
          (desk.x + 1.6, desk.y - 1.7, z0 + 1.45), desk + Vector((0, 0, 0.1)))
    cut(scene, c0, cw)
    cb = camera(scene, "Cam_Box", (desk.x + 0.55, desk.y - 0.65, top + 0.42), desk + Vector((0, 0, 0.08)), 45, cams)
    drift(cb, c0 + 80, f1, (desk.x + 0.55, desk.y - 0.65, top + 0.42), desk + Vector((0, 0, 0.08)),
          (desk.x + 0.38, desk.y - 0.45, top + 0.32), desk + Vector((0, 0, 0.05)), shake=0.0015, seed=3)
    cut(scene, c0 + 80, cb)
    cwin = camera(scene, "Cam_ClubWindow", (desk.x + 1.2, desk.y + 1.7, z0 + 1.35), (-20.0, S.Y0, z0 + 1.7), 24, cams)
    drift(cwin, w0, w1, (desk.x + 1.2, desk.y + 1.7, z0 + 1.35), (-20.0, S.Y0, z0 + 1.7),
          (desk.x + 1.0, desk.y + 1.4, z0 + 1.3), (-20.0, S.Y0, z0 + 1.75), shake=0.003, seed=4)
    cut(scene, w0, cwin)
    show(ape_objs(cast["Sasaki"]) + ape_objs(cast["Iguchi"]), [(c0, w1), (SCHOOL_SHOTS["roof"][0], 99999)])


# --- shot 9: the curse ----------------------------------------------------------------

def curse_climb(ctx):
    from . import curse as CU
    scene, cams = ctx["scene"], ctx["cams"]
    k0, k1 = SCHOOL_SHOTS["curse"]
    w0, w1 = SCHOOL_SHOTS["window"]
    col = U.collection("Curse", scene.collection)
    cr = CU.build_curse(col, location=(-20.0, -8.4, 0.0), yaw=PI)
    ctx["curse"] = cr
    root = cr.root
    wall_y = S.Y0 - 0.18
    pulls = 6
    for i in range(pulls + 1):
        f = k0 + round((k1 - k0 - 10) * i / pulls)
        z = 6.4 * MO.smooth(i / pulls)
        root.location = (-20.0, -8.4 + 0.9 * MO.smooth(i / pulls), z)
        root.keyframe_insert("location", frame=f)
        for side, sx in (("L", 1), ("R", -1)):
            reach_up = (i % 2 == 0) == (side == "L")
            tz = z + (4.6 if reach_up else 3.6)
            CU.reach(cr, f, side, (-20.0 - sx * 1.3, wall_y, tz), bend=(0, 0.3, 0.6), grip=0.6 if reach_up else 1.0)
    root.keyframe_insert("location", frame=k1)
    for f in range(k0, w1 + 1, 20):
        CU.mouth(cr, f, 0.15 + 0.25 * ((f // 20) % 2))
    CU.look(cr, k0, (-14.0, -20.0, 2.0))
    CU.look(cr, k1 - 30, (-20.0, S.Y0 + 2.0, 9.0))
    CU.mouth(cr, w0 + 40, 1.0)
    CU.look(cr, w0, (-20.0, S.Y0 + 3.0, 8.4))
    cc = camera(scene, "Cam_Curse", (-13.0, -19.5, 1.4), (-20.0, -6.5, 4.0), 26, cams)
    drift(cc, k0, k1, (-13.0, -19.5, 1.4), (-20.0, -6.5, 4.0), (-14.5, -16.5, 1.6), (-20.0, -6.5, 8.0), shake=0.002, seed=5)
    cut(scene, k0, cc)
    # it waits on the roof for the climax (moved there between shots)
    r0 = SCHOOL_SHOTS["roof"][0]
    root.keyframe_insert("location", frame=w1)
    U.set_interpolation(root, "CONSTANT", frames={w1})
    root.location = (-3.0, 0.6, S.ROOF_Z)
    root.rotation_euler = (0, 0, PI / 2)
    root.keyframe_insert("location", frame=r0 - 1)
    root.keyframe_insert("rotation_euler", frame=r0 - 1)
    root.rotation_euler = (0, 0, PI)
    root.keyframe_insert("rotation_euler", frame=w1)
    U.set_interpolation(root, "CONSTANT", path_contains="rotation", frames={w1})


# --- shots 10-11: Yuji's dash ---------------------------------------------------------

def yuji_dash(ctx):
    scene, cams, cast, m, rnd = ctx["scene"], ctx["cams"], ctx["cast"], ctx["m"], ctx["rnd"]
    yuji_ape = cast["Yuji"]
    s0, s1 = SCHOOL_SHOTS["street"]
    walk_g = 0.15                                     # sidewalk top
    # along the curb side of the sidewalk: clear of the poles and vending machines at the wall
    yuji = MO.Actor(yuji_ape, (34.0, -41.6), yaw=-PI / 2, ground=walk_g)     # running toward -X
    ctx["yuji"] = yuji
    yuji.eyelids(s0, 0.3)
    yuji.move(s0, s1 - 6, [(1.2, -41.6)], gait="gallop", stride=2.4, hop=0.3, accel=6, decel=4)
    yuji.stand(s1 - 6, s1)
    g0, g1 = SCHOOL_SHOTS["gate"]
    yuji.jump(g0, g0 + 18, (0.0, -38.8), apex=0.35, target_ground=0.0, crouch=4, land=5)
    yuji.move(g0 + 18, g1, [(0.0, -26.0), (0.0, -12.0)], gait="gallop", stride=2.4, hop=0.3, accel=4, decel=1)
    hold(yuji, g1)
    h0, h1 = SCHOOL_SHOTS["hall"]
    hz, hy = m["hall_floor_z"], m["hall_y"]
    yuji.pos, yuji.yaw, yuji.ground = Vector((-21.0, hy, 0)), -PI / 2, hz       # (cut) now upstairs
    yuji.hands = {s_: yuji.stand_hand(s_) for s_ in "LR"}
    yuji.stand(h0, h0 + 4)
    yuji.move(h0 + 4, h1, [(13.0, hy)], gait="gallop", stride=2.3, hop=0.3, accel=10, decel=1)
    hold(yuji, h1)
    show(ape_objs(yuji_ape), [(s0, 99999)])
    cs = camera(scene, "Cam_Sidewalk", (14.0, -44.6, 0.9), (20.0, -41.2, 0.6), 22, cams)
    track(scene, cs, yuji_ape, s0, s1, lambda p, t: (Vector((p.x - 4.5 + 2.0 * t, -44.6, 0.85)),
                                                   Vector((p.x, -41.6, 0.55))), shake=0.006, rnd=rnd)
    cut(scene, s0, cs)
    cg = camera(scene, "Cam_Gate", (5.5, -30.0, 1.2), (0.0, -40.0, 0.8), 24, cams)
    track(scene, cg, yuji_ape, g0, g1, lambda p, t: (Vector((3.2, p.y + 7.5 - 3.0 * t, 1.0)), Vector((p.x, p.y, 0.55))),
          shake=0.004, rnd=rnd)
    cut(scene, g0, cg)
    ch = camera(scene, "Cam_HallRun", (-14.0, 3.55, hz + 0.62), (-21.0, hy, hz + 0.45), 22, cams)
    track(scene, ch, yuji_ape, h0, h1, lambda p, t: (Vector((p.x + 7.5 - 6.0 * t ** 1.4, 3.55, hz + 0.62)),
                                                   Vector((p.x, hy, hz + 0.45))), shake=0.01, rnd=rnd)
    cut(scene, h0, ch)


# --- shots 12-16: the rooftop ---------------------------------------------------------

def rooftop(ctx):
    from . import curse as CU
    scene, cams, cast, rnd = ctx["scene"], ctx["cams"], ctx["cast"], ctx["rnd"]
    z = S.ROOF_Z
    cr, meg, yuji, sas, igu = ctx["curse"], ctx["meg"], ctx["yuji"], ctx["sas"], ctx["igu"]
    finger = ctx["finger"]
    r0, r1 = SCHOOL_SHOTS["roof"]
    root = cr.root
    shoulder_z = z + 3.0
    # Sasaki dangles from the curse's right hand; Iguchi lies hurt on the deck
    hold_pt = Vector((-1.6, 0.0, z + 2.4))

    def dangle(f, p, swing=0.0):
        sas.planted = {"L": False, "R": False}
        sas.ground = p.z - 0.62
        sas.pos = Vector((p.x + 0.05, p.y - 0.15, 0))
        sas.yaw = PI / 2
        for side, dx in (("L", 0.07), ("R", -0.07)):
            sas.hands[side] = p + Vector((0, dx, 0.02))
            sas.key_plant(f, side, 0.0)
            sas.key_hand(f, side, sas.hands[side])
            sas.fingers(f, side, "fist")
        sas.key_body(f, Vector((p.x + 0.05, p.y - 0.15, p.z - 0.62)), sas.yaw, 0.15 + swing, swing * 0.5)

    for f in range(r0, SCHOOL_SHOTS["punch"][0] + 22, 6):
        sw = 0.12 * math.sin(f * 0.21)
        p = hold_pt + Vector((0, 0.08 * math.sin(f * 0.13), 0.05 * math.sin(f * 0.21)))
        CU.reach(cr, f, "R", p + Vector((0, 0, 0.25)), bend=(0.4, -0.3, 0.5), grip=1.0)
        dangle(f, p, sw)
    sas.talk(r0 + 10, r0 + 40, loud=0.9, rate=4.5, seed=11)
    igu.pos, igu.yaw, igu.ground = Vector((-0.6, -3.4, 0)), PI * 0.8, z
    igu.planted = {"L": False, "R": False}
    igu.hands = {s_: igu.local(0.3 * (1 if s_ == "L" else -1), 0.25, 0.05, height=MO.H_SIT) for s_ in "LR"}
    for side in "LR":
        igu.hand_to(r0, side, Vector((igu.hands[side].x, igu.hands[side].y, z + MO.WRIST)), plant=1.0,
                    rot=MO.plant_rotation(side, igu.yaw), settle=False)
    igu.body_to(r0, height=MO.H_SIT, pitch=-0.2, roll=0.25)
    igu.eyelids(r0, 0.7)
    igu.body_to(SCHOOL_SHOTS["sukuna"][1], height=MO.H_SIT, pitch=-0.2, roll=0.25)
    for f in range(r0, SCHOOL_SHOTS["sukuna"][1], 40):
        CU.look(cr, f, (5.0, -2.0, z + 0.8) if f < SCHOOL_SHOTS["door"][0] else (12.0, 2.0, z + 1.0))
    # Megumi faces it, summons the Divine Dogs out of his shadow
    meg.pos, meg.yaw, meg.ground = Vector((5.0, -2.4, 0)), MO.yaw_of(Vector((-1.0, 0.4, 0))), z
    meg.hands = {s_: meg.stand_hand(s_) for s_ in "LR"}
    meg.stand(r0, r0 + 30)
    meg.eyelids(r0, 0.3)
    chest = meg.local(0.0, 0.32, 0.36, height=MO.H_SIT)
    meg.hand_to(r0 + 34, "L", chest + MO.left(meg.yaw) * 0.04, pose="open", settle=False)
    meg.hand_to(r0 + 34, "R", chest - MO.left(meg.yaw) * 0.04, pose="open", settle=True)
    meg.talk(r0 + 36, r0 + 52, loud=0.7, seed=12)                     # "Divine Dogs!"
    meg.plant_hand(r0 + 70, "L")
    meg.plant_hand(r0 + 74, "R")
    meg.stand(r0 + 74, SCHOOL_SHOTS["sukuna"][1] - 2)
    shadow = shadow_puddle(scene, Vector((5.0, -2.4, z + 0.006)))
    for f, s_ in ((r0 + 34, 0.0), (r0 + 44, 1.6), (r0 + 70, 1.6), (r0 + 84, 0.0)):
        shadow.scale = (s_, s_, s_)
        shadow.keyframe_insert("scale", frame=f)
    dogs = {}
    for tag, off in (("DogWhite", Vector((-0.3, 0.75, 0))), ("DogBlack", Vector((-0.6, -0.55, 0)))):
        d = MO.Actor(cast[tag], (5.0 + off.x, -2.4 + off.y), yaw=meg.yaw, ground=z - 0.55)    # under the deck
        d.stand(r0 + 40, r0 + 44)
        d.jump(r0 + 44, r0 + 62, (5.0 + off.x - 0.5, -2.4 + off.y), apex=0.25, target_ground=z, crouch=2, land=6)
        d.stand(r0 + 62, SCHOOL_SHOTS["sukuna"][1] - 2, breathe=0.02)
        for f in range(r0 + 64, SCHOOL_SHOTS["sukuna"][1], 18):
            d.shape(f, "MouthOpen", 0.6)
            d.shape(f + 6, "MouthOpen", 0.1)
        dogs[tag] = d
        show(ape_objs(cast[tag]), [(r0 + 41, 99999)])
    show(ape_objs(cast["Megumi"]), [(0, SCHOOL_SHOTS["drop"][1]), (r0, 99999)])

    # the door bursts open, Yuji gallops out
    d0, d1 = SCHOOL_SHOTS["door"]
    hinge = bpy.data.objects["RoofDoorHinge"]
    hinge.rotation_euler = (0, 0, 0)
    hinge.keyframe_insert("rotation_euler", frame=d0 + 6)
    hinge.rotation_euler = (0, 0, math.radians(-112))
    hinge.keyframe_insert("rotation_euler", frame=d0 + 10)
    hinge.rotation_euler = (0, 0, math.radians(-96))
    hinge.keyframe_insert("rotation_euler", frame=d0 + 16)
    yuji.pos, yuji.yaw, yuji.ground = Vector((15.4, 2.0, 0)), PI / 2, z
    yuji.hands = {s_: yuji.stand_hand(s_) for s_ in "LR"}
    yuji.stand(d0, d0 + 6)
    yuji.move(d0 + 6, d1, [(10.0, 1.6), (4.2, 0.8)], gait="gallop", stride=2.2, hop=0.32, accel=3, decel=6)
    yuji.eyelids(d0, 0.35)

    # the punch
    p0, p1 = SCHOOL_SHOTS["punch"]
    yuji.jump(p0, p0 + 24, (-0.4, 0.5), apex=1.3, crouch=6, land=6)
    hit = Vector((-1.9, 0.55, z + 2.7))
    scene.frame_set(p0 + 18)
    body = cast["Yuji"].arm.matrix_world.translation.copy()
    jab = body + Vector((0, 0, 0.33)) + (hit - body).normalized() * 0.66      # full force, elbow still soft
    yuji.hand_to(p0 + 15, "R", body + Vector((0.25, -0.2, 0.3)), pose="fist", settle=False)
    for f in (p0 + 18, p0 + 19, p0 + 20):
        yuji.hand_to(f, "R", jab, pose="fist", settle=False)
    dent = cr.body.data.shape_keys.key_blocks["Dent"]
    for f, v in ((p0 + 17, 0.0), (p0 + 19, 1.0), (p0 + 30, 0.4), (p0 + 46, 0.0)):
        dent.value = v
        dent.keyframe_insert("value", frame=f)
    root.location = (-3.0, 0.6, z)
    root.keyframe_insert("location", frame=p0 + 18)
    root.location = (-3.7, 0.65, z)
    root.keyframe_insert("location", frame=p0 + 24)
    root.location = (-3.5, 0.6, z)
    root.keyframe_insert("location", frame=p0 + 40)
    CU.mouth(cr, p0 + 19, 1.0)
    CU.mouth(cr, p0 + 40, 0.3)
    flash(scene, p0 + 19)
    # Sasaki is dropped, the finger falls out of his grip onto the deck
    drop_from = hold_pt
    land = Vector((-1.2, -0.9, z))
    CU.reach(cr, p0 + 20, "R", hold_pt + Vector((0.2, -0.3, 0.6)), bend=(0.4, -0.3, 0.5), grip=0.0)
    CU.reach(cr, p0 + 34, "R", hold_pt + Vector((-0.4, -0.2, 0.9)), bend=(0.4, -0.3, 0.5), grip=0.2)
    sas.ground = z
    sas.pos = Vector((land.x, land.y, 0))
    sas.key_body(p0 + 22, Vector((drop_from.x, drop_from.y - 0.2, drop_from.z - 0.6)), PI / 2, 0.4, 0.2)
    sas.key_body(p0 + 32, Vector((land.x, land.y, z + MO.H_SIT)), PI / 2 + 0.3, -0.2, 0.3)
    for side in "LR":
        sas.hand_to(p0 + 32, side, sas.local(0.25 * (1 if side == "L" else -1), 0.2, 0.0, height=MO.H_SIT), pose="relaxed",
                    settle=False)
    sas.key_body(SCHOOL_SHOTS["sukuna"][1], Vector((land.x, land.y, z + MO.H_SIT)), PI / 2 + 0.3, -0.2, 0.3)
    sas.eyelids(p0 + 32, 0.8)
    # the finger: lies on the deck after the drop (Sasaki had pocketed it)
    from . import props as P
    finger = P.make_finger(U.collection("Roof_Story", scene.collection))
    finger.name = "CursedFinger_Roof"
    deck_pt = Vector((-0.2, -1.3, z + 0.012))
    finger.location = deck_pt
    finger.rotation_euler = (0, 0, 0.6)
    finger.scale = (1.0, 1.0, 1.0)
    box_finger = ctx["finger"]
    show([box_finger] + list(box_finger.children), [(SCHOOL_SHOTS["club"][0], SCHOOL_SHOTS["window"][1])])
    show([finger] + list(finger.children), [(p0 + 30, SCHOOL_SHOTS["swallow"][0] + 24)])
    finger.keyframe_insert("location", frame=p0 + 30)

    # Yuji grabs it; Megumi yells
    g0, g1 = SCHOOL_SHOTS["grab"]
    yuji.move(g0, g0 + 22, [(0.3, -1.0)], gait="walk", stride=0.9, accel=4, decel=6)
    grab = deck_pt + Vector((0, 0, 0.02))
    yuji.hand_to(g0 + 28, "R", grab + Vector((0, 0, MO.WRIST)), pose="open", settle=True)
    yuji.hand_to(g0 + 34, "R", grab + Vector((0, 0, MO.WRIST)), pose="fist", settle=True)
    meg.talk(g0 + 30, g0 + 50, loud=0.9, rate=5.0, seed=13)          # "Don't! That thing is poison!"
    meg.head(g0 + 30, 0, 6)
    # from the grab on, the finger rides in Yuji's fist
    con = finger.constraints.new("CHILD_OF")
    con.target = cast["Yuji"].hand["R"]
    con.influence = 0.0
    con.keyframe_insert("influence", frame=g0 + 33)
    con.influence = 1.0
    con.keyframe_insert("influence", frame=g0 + 34)
    scene.frame_set(g0 + 34)
    bpy.context.view_layer.update()
    con.inverse_matrix = cast["Yuji"].hand["R"].matrix_world.inverted()

    # the swallow
    w0, w1 = SCHOOL_SHOTS["swallow"]
    mouth = yuji.local(0.02, 0.3, 0.47, height=MO.H_ONE)
    yuji.hand_to(w0 + 8, "R", mouth + Vector((0, 0, -0.08)), pose="fist", settle=True)
    yuji.hand_to(w0 + 16, "R", mouth, pose="fist", settle=True)
    yuji.shape(w0 + 10, "MouthOpen", 0.0)
    yuji.shape(w0 + 16, "MouthOpen", 1.0)
    yuji.shape(w0 + 26, "MouthOpen", 0.0)
    yuji.head(w0 + 18, 0, 14)
    yuji.head(w0 + 30, 0, -8)
    yuji.eyelids(w0 + 22, 1.0)
    yuji.eyelids(w0 + 40, 0.2)
    yuji.plant_hand(w0 + 36, "R")

    # Sukuna
    k0, k1 = SCHOOL_SHOTS["sukuna"]
    reveal = cast["Yuji"].parts["SukunaReveal"].outputs[0]
    iris = cast["Yuji"].parts["IrisGlow"].outputs[0]
    for f, v in ((k0, 0.0), (k0 + 50, 1.0)):
        reveal.default_value = v
        reveal.keyframe_insert("default_value", frame=f)
    for f, v in ((k0 + 20, 0.0), (k0 + 50, 6.0)):
        iris.default_value = v
        iris.keyframe_insert("default_value", frame=f)
    yuji.body_to(k0 + 10, height=MO.H_STAND)
    yuji.body_to(k0 + 50, height=MO.H_STAND + 0.06, pitch=-0.12)
    yuji.head(k0 + 50, 0, 18, roll=-10)
    yuji.eyelids(k0 + 50, 0.15)
    yuji.talk(k0 + 56, k0 + 92, loud=1.0, rate=6.0, seed=14)            # the laugh
    # the curse lunges; one swipe and it falls apart
    root.location = (-3.5, 0.6, z)
    root.keyframe_insert("location", frame=k0 + 92)
    root.location = (-2.0, 0.2, z)
    root.keyframe_insert("location", frame=k0 + 104)
    CU.reach(cr, k0 + 104, "L", yuji.local(0.0, 0.2, 0.5) + Vector((0, 0.3, 0)), bend=(0.2, 0.3, 0.6), grip=0.0)
    CU.mouth(cr, k0 + 104, 1.0)
    yuji.hand_to(k0 + 100, "R", yuji.local(-0.3, 0.15, 0.7), pose="open", settle=True)
    yuji.hand_to(k0 + 106, "R", yuji.local(0.45, 0.55, 0.15), pose="open", settle=True)
    flash(scene, k0 + 107, color=(1.0, 0.25, 0.2))
    curse_col = bpy.data.collections["Curse"]
    show([o for o in curse_col.objects if o.type in ("MESH", "CURVE") and o not in cr.pieces],
         [(SCHOOL_SHOTS["curse"][0], k0 + 106)])
    show(cr.pieces, [(k0 + 107, 99999)])
    for i, pc in enumerate(cr.pieces):
        pc.location = (0, 0, 0)
        pc.rotation_euler = (0, 0, 0)
        pc.keyframe_insert("location", frame=k0 + 107)
        pc.keyframe_insert("rotation_euler", frame=k0 + 107)
        pc.location = ((i - 1) * 0.6, 1.2 + 0.4 * i, -0.4 * i + (0.8 if i == 0 else 0.0))
        pc.rotation_euler = (0.4 * (i - 1), 0.6 * (1 - i), 0.3 * i)
        pc.keyframe_insert("location", frame=k0 + 140)
        pc.keyframe_insert("rotation_euler", frame=k0 + 140)
        pc["dissolve"] = 0.0
        pc.keyframe_insert('["dissolve"]', frame=k0 + 120)
        pc["dissolve"] = 1.0
        pc.keyframe_insert('["dissolve"]', frame=k1)
    yuji.plant_hand(k0 + 118, "R")
    yuji.stand(k0 + 118, k1)
    yuji.head(k0 + 120, -12, 6, roll=6)

    # cameras
    cw = camera(scene, "Cam_Roof", (-12.0, -5.2, z + 2.0), (0.0, 0.0, z + 1.6), 22, cams)
    drift(cw, r0, r0 + 33, (-12.0, -5.2, z + 2.0), (0.0, 0.0, z + 1.6), (-11.0, -4.8, z + 1.9), (0.5, 0.0, z + 1.6))
    cut(scene, r0, cw)
    cm = camera(scene, "Cam_Summon", (7.0, -4.6, z + 0.8), (4.6, -2.0, z + 0.55), 32, cams)
    drift(cm, r0 + 34, r1, (7.0, -4.6, z + 0.8), (4.6, -2.0, z + 0.55), (7.4, -4.9, z + 1.0), (4.2, -1.8, z + 0.5),
          shake=0.002, seed=6)
    cut(scene, r0 + 34, cm)
    cd = camera(scene, "Cam_Door", (9.5, -1.8, z + 0.9), (14.0, 2.0, z + 1.1), 26, cams)
    track(scene, cd, cast["Yuji"], d0, d1, lambda p, t: (Vector((9.5 - 2.5 * t, -1.8, z + 0.9)), Vector((p.x, p.y, z + 0.8))),
          shake=0.004, rnd=rnd)
    cut(scene, d0, cd)
    cp = camera(scene, "Cam_Punch", (-1.0, -6.5, z + 1.6), (-1.6, 0.5, z + 2.0), 24, cams)
    drift(cp, p0, p1, (-1.0, -6.5, z + 1.6), (-1.6, 0.5, z + 2.0), (-1.4, -6.0, z + 1.5), (-1.8, 0.4, z + 1.6),
          shake=0.012, seed=7)
    cut(scene, p0, cp)
    cg = camera(scene, "Cam_Grab", (2.4, -3.6, z + 0.9), (0.0, -1.0, z + 0.4), 30, cams)
    drift(cg, g0, g1, (2.4, -3.6, z + 0.9), (0.0, -1.0, z + 0.4), (2.0, -3.2, z + 0.8), (0.1, -1.1, z + 0.4))
    cut(scene, g0, cg)
    cs = camera(scene, "Cam_Swallow", (1.6, -2.3, z + 0.75), (0.3, -1.0, z + 0.65), 45, cams)
    track(scene, cs, cast["Yuji"], w0, w1, lambda p, t: (Vector((p.x + 1.1, p.y - 1.1, z + 0.78)), p + Vector((0, 0, 0.5))),
          shake=0.002, rnd=rnd)
    cut(scene, w0, cs)
    ck = camera(scene, "Cam_Sukuna", (1.8, -2.6, z + 0.9), (0.3, -1.0, z + 0.8), 40, cams)
    track(scene, ck, cast["Yuji"], k0, k0 + 95,
          lambda p, t: (Vector((p.x + 1.4 - 0.5 * t, p.y - 1.5 + 0.5 * t, z + 0.85)), p + Vector((0, 0, 0.55))),
          shake=0.0015, rnd=rnd)
    cut(scene, k0, ck)
    cx = camera(scene, "Cam_Slice", (4.0, -6.5, z + 2.2), (-2.0, 0.4, z + 1.8), 22, cams)
    drift(cx, k0 + 96, k1, (4.0, -6.5, z + 2.2), (-2.0, 0.4, z + 1.8), (4.8, -7.4, z + 2.6), (-1.5, 0.4, z + 1.6),
          shake=0.004, seed=8)
    cut(scene, k0 + 96, cx)


def shadow_puddle(scene, loc):
    """Megumi's shadow spreading into a pool the dogs come out of."""
    import bmesh
    mat, nt, out = U.new_material("ShadowPool")
    g = K.NG(nt)
    em = g.node("ShaderNodeEmission", Strength=0.0)
    g.set(em.inputs["Color"], (0, 0, 0))
    g.set(out.inputs["Surface"], em.outputs[0])
    bm = bmesh.new()
    rnd = random.Random(3)
    ring = []
    for k in range(40):
        a = 2 * PI * k / 40
        r = 1.0 + 0.18 * math.sin(a * 5 + 1) + 0.1 * rnd.random()
        ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r * 0.8, 0)))
    bm.faces.new(ring)
    ob = U.mesh_object("ShadowPool", bm, scene.collection, mats=[mat])
    ob.location = loc
    ob.scale = (0, 0, 0)
    ob.visible_shadow = False
    return ob


def flash(scene, f, color=(1.0, 0.95, 0.85)):
    """One-frame impact flash: a white-out on the compositor's exposure, with a quick decay."""
    vs = scene.view_settings
    base = vs.exposure
    for ff, v in ((f - 1, base), (f, base + 2.5), (f + 2, base + 0.8), (f + 6, base)):
        vs.exposure = v
        vs.keyframe_insert("exposure", frame=ff)
    vs.exposure = base


def hands_for(actor, top):
    sc = actor.scale
    return {s: Vector((top.x, top.y, top.z + MO.WRIST * sc)) + MO.left(actor.yaw) * (0.07 * (1 if s == "L" else -1))
            for s in "LR"}


def track(scene, cam, ape, f0, f1, place, shake=0.0, rnd=None):
    """Camera that follows a character: place(body position, t) -> (location, aim) per frame."""
    rnd = rnd or random.Random(0)
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        p = ape.arm.matrix_world.translation.copy()
        loc, aim = place(p, (f - f0) / max(1, f1 - f0))
        aim_cam(cam, loc, aim, f)
        if shake:
            cam.rotation_euler.x += rnd.uniform(-shake, shake)
            cam.rotation_euler.z += rnd.uniform(-shake, shake)
            cam.keyframe_insert("rotation_euler", frame=f)
