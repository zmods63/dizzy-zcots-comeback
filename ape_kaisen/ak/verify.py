"""Measure animation quality frame by frame from the evaluated (IK-solved) rigs:
arm extension, palm contact, and support. Used by the build to catch bad poses."""

import bpy

from . import motion as MO


def check(actor, frames, label=None, ground=None):
    """Returns a dict of worst-case numbers over `frames` for one actor."""
    ape = actor.ape
    arm = ape.arm
    sc = arm.scale[0]
    scene = bpy.context.scene
    worst_ext, worst_palm, frames_bad = 0.0, 0.0, []
    for f in frames:
        scene.frame_set(f)
        mw = arm.matrix_world
        for s in "LR":
            sh = mw @ arm.pose.bones[f"upperarm.{s}"].head
            wr = mw @ arm.pose.bones[f"lowerarm.{s}"].tail
            ext = (wr - sh).length / (MO.ARM_LENGTH * sc)
            worst_ext = max(worst_ext, ext)
            plant = arm.pose.bones[f"hand.{s}"].constraints["Plant"].influence
            if plant > 0.99 and ground is not None:
                target = ape.hand[s].matrix_world.translation
                g = ground(target) if callable(ground) else ground
                palm_gap = abs(target.z - (g + MO.WRIST * sc))
                worst_palm = max(worst_palm, palm_gap)
            if ext > MO.MAX_REACH / MO.ARM_LENGTH + 0.01:
                frames_bad.append((f, s, round(ext, 3)))
    return {"label": label or ape.tag, "max_arm_extension": round(worst_ext, 3),
            "max_palm_gap_m": round(worst_palm, 4), "overextended_frames": frames_bad[:10]}
