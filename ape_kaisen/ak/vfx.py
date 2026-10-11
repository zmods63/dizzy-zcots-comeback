"""Effects: dust where palms slam down, slash arcs, a cursed glow.

Everything is plain geometry with animated scale/visibility and a material that fades through
the object's colour alpha (Object Info), so it renders the same in EEVEE and Cycles."""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import kit as K
from . import util as U


def _fade_material(name, color, emission=0.0):
    """Translucent material whose opacity is the object's colour alpha (animate ob.color[3])."""
    mat, nt, out = U.new_material(name)
    g = K.NG(nt)
    info = g.node("ShaderNodeObjectInfo")
    b = g.node("ShaderNodeBsdfPrincipled", Roughness=1.0)
    g.set(b.inputs["Base Color"], color)
    g.set(b.inputs["Alpha"], info.outputs["Alpha"])
    if emission:
        g.set(b.inputs["Emission Color"], color)
        b.inputs["Emission Strength"].default_value = emission
    g.set(out.inputs["Surface"], b.outputs[0])
    for attr, val in (("surface_render_method", "DITHERED"), ("use_transparent_shadow", True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val)
    return mat


def _puff_mesh():
    me = bpy.data.meshes.get("DustPuff")
    if me:
        return me
    rnd = random.Random(4)
    bm = bmesh.new()
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.3, 0.3)
        r = rnd.uniform(0.35, 0.6)
        U.bm_ico(bm, rnd.uniform(0.22, 0.35), loc=(math.cos(a) * r, math.sin(a) * r, rnd.uniform(0.05, 0.2)),
                 scale=(1.0, 1.0, 0.6), subdiv=1)
    U.bm_ico(bm, 0.4, loc=(0, 0, 0.15), scale=(1, 1, 0.55), subdiv=1)
    me = bpy.data.meshes.new("DustPuff")
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    return me


def dust(col, impacts, color=(0.42, 0.4, 0.38), life=16, size=0.55, min_strength=0.25):
    """A puff of dust at every hand slam / landing: (frame, world point, strength)."""
    me = _puff_mesh()
    mat = _fade_material("Dust", color)
    if not me.materials:
        me.materials.append(mat)
    rnd = random.Random(9)
    obs = []
    for i, (f, p, s) in enumerate(impacts):
        if s < min_strength:
            continue
        ob = bpy.data.objects.new(f"Dust{i:03d}", me)
        col.objects.link(ob)
        ob.visible_shadow = False
        ob.location = Vector(p) - Vector((0, 0, 0.03))
        ob.rotation_euler = (0, 0, rnd.uniform(0, 2 * math.pi))
        sz = size * min(1.6, s)
        for ff, sc, a in ((f, 0.15, 0.0), (f + 1, 0.35, 0.55), (f + life // 2, 0.8, 0.3), (f + life, 1.0, 0.0)):
            ob.scale = (sz * sc, sz * sc, sz * sc * 0.8)
            ob.keyframe_insert("scale", frame=ff)
            ob.color = (1, 1, 1, a)
            ob.keyframe_insert("color", frame=ff)
        U.visible(ob, [(f, f + life)])
        obs.append(ob)
    return obs


def slash(col, f, center, normal, radius=1.8, color=(1.0, 0.25, 0.2), life=6, name="Slash"):
    """A bright crescent arc that flashes across `center` (Sukuna's cut)."""
    bm = bmesh.new()
    n = 24
    inner, outer = [], []
    for k in range(n + 1):
        t = k / n
        a = math.radians(-70 + 140 * t)
        w = 0.12 * math.sin(math.pi * t)
        inner.append(bm.verts.new((math.cos(a) * (radius - w), math.sin(a) * (radius - w), 0)))
        outer.append(bm.verts.new((math.cos(a) * (radius + w), math.sin(a) * (radius + w), 0)))
    for k in range(n):
        bm.faces.new((inner[k], inner[k + 1], outer[k + 1], outer[k]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(_fade_material("SlashMat", color, emission=25.0))
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.visible_shadow = False
    ob.location = center
    ob.rotation_euler = Vector(normal).to_track_quat("Z", "Y").to_euler()
    for ff, a, sc in ((f, 1.0, 0.6), (f + 2, 1.0, 1.0), (f + life, 0.0, 1.15)):
        ob.color = (1, 1, 1, a)
        ob.keyframe_insert("color", frame=ff)
        ob.scale = (sc, sc, sc)
        ob.keyframe_insert("scale", frame=ff)
    U.visible(ob, [(f, f + life)])
    return ob


def glow_sphere(col, parent, radius, color, frames_values, name="CursedGlow"):
    """A soft glowing halo parented to an object; frames_values: [(frame, opacity)]."""
    bm = bmesh.new()
    U.bm_sphere(bm, radius, segs=16, rings=8)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    mat, nt, out = U.new_material(name + "Mat")
    g = K.NG(nt)
    info = g.node("ShaderNodeObjectInfo")
    lw = g.node("ShaderNodeLayerWeight", Blend=0.5)
    facing = g.math("SUBTRACT", 1.0, lw.outputs["Facing"])
    strength = g.math("MULTIPLY", g.math("POWER", facing, 2.0), g.math("MULTIPLY", info.outputs["Alpha"], 8.0))
    em = g.node("ShaderNodeEmission")
    g.set(em.inputs["Color"], color)
    g.set(em.inputs["Strength"], strength)
    tr = g.node("ShaderNodeBsdfTransparent")
    add = g.node("ShaderNodeAddShader")
    g.set(add.inputs[0], tr.outputs[0])
    g.set(add.inputs[1], em.outputs[0])
    g.set(out.inputs["Surface"], add.outputs[0])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.visible_shadow = False
    ob.parent = parent
    for f, v in frames_values:
        ob.color = (1, 1, 1, v)
        ob.keyframe_insert("color", frame=f)
    return ob
