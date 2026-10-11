"""Story props: Sukuna's finger and the sealed box it comes in."""

import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from . import mats as M
from . import util as U


def finger_material():
    """Dried, leathery, dark red-brown skin; its veins can glow (value node 'VeinGlow')."""
    mat, nt, out = U.new_material("CursedFinger")
    g = M.G(nt)
    tc = g.n("ShaderNodeTexCoord")
    wrinkle_map = g.n("ShaderNodeMapping", Scale=(60.0, 60.0, 18.0))
    g.l(tc.outputs["Object"], wrinkle_map.inputs["Vector"])
    wrinkle = g.n("ShaderNodeTexWave", {"wave_type": "BANDS", "bands_direction": "Z"}, Scale=1.0, Distortion=4.0, Detail=4.0)
    g.l(wrinkle_map.outputs[0], wrinkle.inputs["Vector"])
    blotch = g.n("ShaderNodeTexNoise", Scale=40.0, Detail=6.0)
    g.l(tc.outputs["Object"], blotch.inputs["Vector"])
    ramp = M._ramp(g, [(0.3, (0.05, 0.012, 0.01)), (0.55, (0.16, 0.05, 0.035)), (0.8, (0.24, 0.1, 0.07))])
    g.l(blotch.outputs["Fac"], ramp.inputs["Fac"])
    b = g.n("ShaderNodeBsdfPrincipled", Roughness=0.62)
    g.l(ramp.outputs["Color"], b.inputs["Base Color"])
    bump = g.n("ShaderNodeBump", Strength=0.6, Distance=0.002)
    g.l(wrinkle.outputs["Fac"], bump.inputs["Height"])
    g.l(bump.outputs["Normal"], b.inputs["Normal"])
    veins = g.n("ShaderNodeTexVoronoi", {"feature": "DISTANCE_TO_EDGE"}, Scale=55.0)
    g.l(tc.outputs["Object"], veins.inputs["Vector"])
    vmask = g.n("ShaderNodeMapRange", From_Min=0.0, From_Max=0.05, To_Min=1.0, To_Max=0.0)
    g.l(veins.outputs["Distance"], vmask.inputs["Value"])
    glow = g.n("ShaderNodeValue")
    glow.name = "VeinGlow"
    glow.outputs[0].default_value = 0.0
    strength = g.n("ShaderNodeMath", {"operation": "MULTIPLY"})
    g.l(vmask.outputs["Result"], strength.inputs[0])
    g.l(glow.outputs[0], strength.inputs[1])
    b.inputs["Emission Color"].default_value = (1.0, 0.04, 0.015, 1)
    g.l(strength.outputs[0], b.inputs["Emission Strength"])
    g.l(b.outputs[0], out.inputs[0])
    return mat


def make_finger(col, length=0.13):
    """A long mummified finger lying along +Y from its origin (the cut end)."""
    bm = bmesh.new()
    pts, radii = [], []
    n = 22
    for i in range(n + 1):
        t = i / n
        y = t * length
        x = 0.004 * math.sin(t * 5.0)
        z = -0.01 * math.sin(t * math.pi * 0.8)          # slight natural curl
        knuckle = 0.0028 * (math.exp(-((t - 0.36) / 0.045) ** 2) + math.exp(-((t - 0.66) / 0.04) ** 2))
        r = 0.0125 * (1 - 0.28 * t) + knuckle
        if t > 0.9:
            r *= math.sqrt(max(0.0, (1 - t) / 0.1)) * 0.9 + 0.1
        pts.append(Vector((x, y, z)))
        radii.append(r if i < n else 0.0)
    U.bm_tube(bm, pts, radii, segs=14, scale_y=[0.85] * len(pts))
    finger = U.mesh_object("CursedFinger", bm, col, mats=[finger_material()], smooth=True)
    sub = finger.modifiers.new("Smooth", "SUBSURF")
    sub.levels = sub.render_levels = 1
    # the long black nail on the tip
    bm = bmesh.new()
    tip = pts[-3]
    nail = U.bm_sphere(bm, 1.0, segs=12, rings=8)
    for v in nail:
        v.co = Vector((v.co.x * 0.009, v.co.y * 0.016, v.co.z * 0.0025)) + tip + Vector((0, 0.004, 0.0085))
    nail_ob = U.mesh_object("CursedFingerNail", bm, col, mats=[M.paint("Nail", (0.01, 0.008, 0.008), rough=0.25)], smooth=True)
    U.parent_keep(nail_ob, finger)
    return finger


def talisman_material():
    """Aged yellow paper with red brush strokes; 'Burn' (0..1) eats it away with glowing edges."""
    mat, nt, out = U.new_material("Talisman")
    g = M.G(nt)
    tc = g.n("ShaderNodeTexCoord")
    sep = g.n("ShaderNodeSeparateXYZ")
    g.l(tc.outputs["UV"], sep.inputs[0])
    # red brush symbols: wobbly horizontal strokes stacked down the strip, plus a circle
    strokes_map = g.n("ShaderNodeMapping", Scale=(1.0, 9.0, 1.0))
    g.l(tc.outputs["UV"], strokes_map.inputs["Vector"])
    wave = g.n("ShaderNodeTexWave", {"wave_type": "BANDS", "bands_direction": "Y"}, Scale=1.0, Distortion=3.0, Detail=2.0)
    g.l(strokes_map.outputs[0], wave.inputs["Vector"])
    ink = g.n("ShaderNodeMapRange", From_Min=0.82, From_Max=0.9, To_Min=0.0, To_Max=1.0)
    g.l(wave.outputs["Fac"], ink.inputs["Value"])
    center = g.n("ShaderNodeMath", {"operation": "COMPARE"})
    g.l(sep.outputs["X"], center.inputs[0])
    center.inputs[1].default_value = 0.5
    center.inputs[2].default_value = 0.3
    ink_c = g.n("ShaderNodeMath", {"operation": "MULTIPLY"})
    g.l(ink.outputs["Result"], ink_c.inputs[0])
    g.l(center.outputs[0], ink_c.inputs[1])
    paper_noise = g.n("ShaderNodeTexNoise", Scale=30.0, Detail=5.0)
    g.l(tc.outputs["Object"], paper_noise.inputs["Vector"])
    paper = M._ramp(g, [(0.3, (0.62, 0.5, 0.25)), (0.7, (0.86, 0.76, 0.48))])
    g.l(paper_noise.outputs["Fac"], paper.inputs["Fac"])
    col = g.n("ShaderNodeMix", {"data_type": "RGBA"})
    g.l(ink_c.outputs[0], col.inputs["Factor"])
    g.l(paper.outputs["Color"], col.inputs[6])
    col.inputs[7].default_value = (0.45, 0.02, 0.02, 1)
    b = g.n("ShaderNodeBsdfPrincipled", Roughness=0.8)
    g.l(col.outputs[2], b.inputs["Base Color"])
    # burning: noise vs threshold; just past the edge glows orange, beyond it the paper is gone
    attr = g.n("ShaderNodeAttribute", {"attribute_type": "OBJECT", "attribute_name": "burn"})
    burn_noise = g.n("ShaderNodeTexNoise", Scale=9.0, Detail=4.0)
    g.l(tc.outputs["Object"], burn_noise.inputs["Vector"])
    gone = g.n("ShaderNodeMath", {"operation": "LESS_THAN"})
    g.l(burn_noise.outputs["Fac"], gone.inputs[0])
    g.l(attr.outputs["Fac"], gone.inputs[1])
    edge_d = g.n("ShaderNodeMath", {"operation": "SUBTRACT"})
    g.l(burn_noise.outputs["Fac"], edge_d.inputs[0])
    g.l(attr.outputs["Fac"], edge_d.inputs[1])
    edge = g.n("ShaderNodeMapRange", From_Min=0.0, From_Max=0.06, To_Min=25.0, To_Max=0.0)
    g.l(edge_d.outputs[0], edge.inputs["Value"])
    b.inputs["Emission Color"].default_value = (1.0, 0.35, 0.05, 1)
    g.l(edge.outputs["Result"], b.inputs["Emission Strength"])
    char = g.n("ShaderNodeMapRange", From_Min=0.0, From_Max=0.12, To_Min=1.0, To_Max=0.0)
    g.l(edge_d.outputs[0], char.inputs["Value"])
    col2 = g.n("ShaderNodeMix", {"data_type": "RGBA"})
    g.l(char.outputs["Result"], col2.inputs["Factor"])
    g.l(col.outputs[2], col2.inputs[6])
    col2.inputs[7].default_value = (0.02, 0.012, 0.008, 1)
    g.l(col2.outputs[2], b.inputs["Base Color"])
    tr = g.n("ShaderNodeBsdfTransparent")
    mix = g.n("ShaderNodeMixShader")
    g.l(gone.outputs[0], mix.inputs["Fac"])
    g.l(b.outputs[0], mix.inputs[1])
    g.l(tr.outputs[0], mix.inputs[2])
    g.l(mix.outputs[0], out.inputs[0])
    M._transparent_settings(mat)
    return mat


def _strip(bm, uv_layer, path, width):
    """A paper strip following a polyline, with UVs (u across 0..1, v along)."""
    rows = []
    total = sum((b - a).length for a, b in zip(path, path[1:]))
    acc = 0.0
    for i, p in enumerate(path):
        if i:
            acc += (p - path[i - 1]).length
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        n = Vector((0, 0, 1)) if abs(t.z) < 0.7 else Vector((1, 0, 0))
        side = t.cross(n).normalized() * (width / 2)
        rows.append((bm.verts.new(p - side), bm.verts.new(p + side), acc / total))
    for (a1, a2, va), (b1, b2, vb) in zip(rows, rows[1:]):
        f = bm.faces.new((a1, a2, b2, b1))
        for loop, uv in zip(f.loops, ((0, va * 4), (1, va * 4), (1, vb * 4), (0, vb * 4))):
            loop[uv_layer].uv = uv


BOX_W, BOX_D, BOX_H, LID_H = 0.30, 0.18, 0.11, 0.03


def _box_parts():
    from .kit import Surf
    wood = Surf("wood", "#6E4B2D", "#2F1D0E", rough=0.7, grime=0.45, scale=1.6, name="OldBoxWood")
    brass = Surf("metal", "#8A7346", rough=0.5, metal=1.0, edge=0.35, grime=0.4, name="OldBrass")
    return wood, brass


def _box_body(a):
    wood, brass = _box_parts()
    w, d, hb = BOX_W, BOX_D, BOX_H - LID_H
    a.box((w, d, hb), (0, 0, hb / 2), wood, bevel=0.005, wobble=0.0015, grain=(1, 0, 0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 + 0.001), sy * (d / 2 + 0.001)
            a.box((0.004, 0.03, 0.03), (x, y - sy * 0.012, 0.016), brass, bevel=0.001)
            a.box((0.03, 0.004, 0.03), (x - sx * 0.012, y, 0.016), brass, bevel=0.001)
    a.box((0.03, 0.006, 0.022), (0, -d / 2 - 0.002, hb - 0.012), brass, bevel=0.002)


def _box_lid(a):
    wood, brass = _box_parts()
    w, d = BOX_W + 0.008, BOX_D + 0.008
    a.box((w, d, LID_H), (0, 0, LID_H / 2), wood, bevel=0.006, wobble=0.0015, grain=(1, 0, 0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            a.box((0.035, 0.035, 0.004), (sx * (w / 2 - 0.016), sy * (d / 2 - 0.016), LID_H + 0.001), brass,
                  bevel=0.001)


def make_box(col):
    """Old wooden box (origin at its base centre) with two talisman strips sealing the lid.
    Returns (box, lid, seals): animate seals['burn'] 0 -> 1 and lift/flip the lid."""
    from . import kit as K
    w, d, h, lid_h = BOX_W, BOX_D, BOX_H, LID_H
    box = K.place(K.asset("SealedBoxBody", _box_body), col, (0, 0, 0), name="SealedBox")
    lid = K.place(K.asset("SealedBoxLid", _box_lid), col, (0, 0, h - lid_h), name="SealedBoxLid")
    U.parent_keep(lid, box)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    top = h + 0.0015
    for ang in (math.radians(28), math.radians(-28)):
        r = Matrix.Rotation(ang, 3, "Z")
        ext = abs(w / 2 * math.cos(ang)) + abs(d / 2 * math.sin(ang))
        path = [r @ Vector((-ext - 0.003, 0, top - 0.06)), r @ Vector((-ext - 0.003, 0, top)),
                r @ Vector((-ext * 0.5, 0, top)), r @ Vector((0, 0, top)), r @ Vector((ext * 0.5, 0, top)),
                r @ Vector((ext + 0.003, 0, top)), r @ Vector((ext + 0.003, 0, top - 0.06))]
        _strip(bm, uv, path, 0.045)
    seals = U.mesh_object("Talismans", bm, col, mats=[talisman_material()])
    seals["burn"] = 0.0
    U.parent_keep(seals, lid)
    return box, lid, seals
