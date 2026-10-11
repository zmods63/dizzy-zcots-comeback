"""Small helpers shared by every Ape Kaisen module (Blender 5.x API)."""

import contextlib
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

RNG = random.Random(1999)


# ----------------------------------------------------------------- collections

def collection(name, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if col.name not in parent.children:
        parent.children.link(col)
    return col


def link(ob, col):
    if ob.name not in col.objects:
        col.objects.link(ob)
    return ob


# ----------------------------------------------------------------- meshes

def mesh_object(name, bm, col, mats=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    for m in mats or []:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def bm_box(bm, size, loc=(0, 0, 0), rot=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    m = Matrix.Translation(loc) @ (rot.to_matrix().to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*size, 1))
    bmesh.ops.transform(bm, matrix=m, verts=r["verts"])
    return r["verts"]


def bm_cyl(bm, r1, r2, depth, segs=16, loc=(0, 0, 0), rot=None, caps=True):
    r = bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segs,
                              radius1=r1, radius2=r2, depth=depth)
    m = Matrix.Translation(loc) @ (rot.to_matrix().to_4x4() if rot else Matrix())
    bmesh.ops.transform(bm, matrix=m, verts=r["verts"])
    return r["verts"]


def bm_sphere(bm, radius, loc=(0, 0, 0), scale=(1, 1, 1), segs=16, rings=8, rot=None):
    r = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    m = Matrix.Translation(loc) @ (rot.to_matrix().to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*scale, 1))
    bmesh.ops.transform(bm, matrix=m, verts=r["verts"])
    return r["verts"]


def bm_ico(bm, radius, loc=(0, 0, 0), scale=(1, 1, 1), subdiv=2):
    r = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    m = Matrix.Translation(loc) @ Matrix.Diagonal((*scale, 1))
    bmesh.ops.transform(bm, matrix=m, verts=r["verts"])
    return r["verts"]


def bm_cone_between(bm, a, b, r1, r2, segs=8):
    """A cone/cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.to_track_quat("Z", "Y")
    return bm_cyl(bm, r1, r2, d.length, segs=segs, loc=(a + b) / 2, rot=rot)


def bm_plane(bm, w, h, loc=(0, 0, 0), rot=None):
    r = bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    m = Matrix.Translation(loc) @ (rot.to_matrix().to_4x4() if rot else Matrix()) @ Matrix.Diagonal((w, h, 1, 1))
    bmesh.ops.transform(bm, matrix=m, verts=r["verts"])
    return r["verts"]


def bm_tube(bm, pts, radii, segs=8, cap=True, scale_y=None):
    """Tapered tube through pts (radius 0 = pointed tip). scale_y squashes the cross-section."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rings = []
    normal = None
    for i, p in enumerate(pts):
        tan = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if normal is None:
            ref = Vector((0, 0, 1)) if abs(tan.z) < 0.9 else Vector((1, 0, 0))
            normal = (ref - tan * ref.dot(tan)).normalized()
        else:
            normal = (normal - tan * normal.dot(tan)).normalized()
        binorm = tan.cross(normal)
        r = radii[i]
        sy = scale_y[i] if scale_y else 1.0
        if r <= 1e-7:
            rings.append([bm.verts.new(p)])
        else:
            rings.append([bm.verts.new(p + (normal * math.cos(a) * sy + binorm * math.sin(a)) * r)
                          for a in (2 * math.pi * k / segs for k in range(segs))])
    for a, b in zip(rings, rings[1:]):
        if len(a) > 1 and len(b) > 1:
            for k in range(segs):
                bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))
        elif len(a) > 1:
            for k in range(segs):
                bm.faces.new((a[k], a[(k + 1) % segs], b[0]))
        elif len(b) > 1:
            for k in range(segs):
                bm.faces.new((a[0], b[(k + 1) % segs], b[k]))
    if cap and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    return rings


def set_material_index(verts, index):
    faces = {f for v in verts for f in v.link_faces}
    for f in faces:
        f.material_index = index


# ----------------------------------------------------------------- materials

def new_material(name):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    return mat, nt, out


def principled(name, color, rough=0.6, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0,
               coat=0.0, spec=0.5):
    mat, nt, out = new_material(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color[:3], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit[:3], 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
    nt.links.new(b.outputs[0], out.inputs[0])
    mat.diffuse_color = (*color[:3], 1)
    return mat


def emission(name, color, strength=1.0):
    mat, nt, out = new_material(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color[:3], 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    mat.diffuse_color = (*color[:3], 1)
    return mat


def holdout_black(name):
    """Pure black, unlit (good for mouths, pupils, outlines)."""
    return emission(name, (0, 0, 0), 0.0)


# ----------------------------------------------------------------- animation

@contextlib.contextmanager
def new_key_interpolation(kind):
    prefs = bpy.context.preferences.edit
    old = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = kind
    try:
        yield
    finally:
        prefs.keyframe_new_interpolation_type = old


def key(struct, path, frame, value=None, index=-1):
    """Set (optionally) and keyframe struct.path at frame."""
    if value is not None:
        cur = getattr(struct, path)
        if index >= 0:
            cur[index] = value
        elif hasattr(cur, "__len__") and not isinstance(cur, str):
            for i, v in enumerate(value):
                cur[i] = v
        else:
            setattr(struct, path, value)
    struct.keyframe_insert(path, frame=frame, index=index)


def fcurves(idb):
    ad = idb.animation_data
    if ad is None or ad.action is None:
        return []
    act = ad.action
    try:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
        if cb is not None:
            return list(cb.fcurves)
    except Exception:
        pass
    return list(getattr(act, "fcurves", []))


def set_interpolation(idb, kind, path_contains=None, frames=None):
    for fc in fcurves(idb):
        if path_contains and path_contains not in fc.data_path:
            continue
        for kp in fc.keyframe_points:
            if frames is None or int(round(kp.co[0])) in frames:
                kp.interpolation = kind


def set_extrapolation(idb, kind, path_contains=None):
    for fc in fcurves(idb):
        if path_contains is None or path_contains in fc.data_path:
            fc.extrapolation = kind


def visible(ob, frames_on, start=None):
    """Show ob only during the given (first, last) ranges. Keys hide_render + hide_viewport."""
    hidden_from = start if start is not None else 0
    ob.hide_render = True
    ob.hide_viewport = True
    ob.keyframe_insert("hide_render", frame=hidden_from)
    ob.keyframe_insert("hide_viewport", frame=hidden_from)
    for a, b in frames_on:
        ob.hide_render = False
        ob.hide_viewport = False
        ob.keyframe_insert("hide_render", frame=a)
        ob.keyframe_insert("hide_viewport", frame=a)
        ob.hide_render = True
        ob.hide_viewport = True
        ob.keyframe_insert("hide_render", frame=b + 1)
        ob.keyframe_insert("hide_viewport", frame=b + 1)


def look_rotation(src, dst, roll=0.0, track="-Z", up="Y"):
    q = (Vector(dst) - Vector(src)).to_track_quat(track, up)
    if roll:
        q = q @ Quaternion((0, 0, 1), roll)
    return q


def smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ----------------------------------------------------------------- parenting

def parent_to_bone(ob, arm, bone_name):
    """Parent ob to a bone of arm, keeping its current world transform (designed in rest pose)."""
    bone = arm.data.bones[bone_name]
    tail_mat = arm.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))
    # matrix_world is stale until the depsgraph updates, so trust matrix_basis for unparented objects
    world = ob.matrix_world.copy() if ob.parent else ob.matrix_basis.copy()
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone_name
    ob.matrix_parent_inverse = tail_mat.inverted()
    ob.matrix_basis = world


def parent_keep(ob, parent):
    world = ob.matrix_world.copy() if ob.parent else ob.matrix_basis.copy()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    ob.matrix_basis = world


# ----------------------------------------------------------------- images

def image_pixels(img):
    """(H, W, 4) float32, row 0 = bottom (Blender's order)."""
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)


def new_image(name, arr, colorspace="sRGB"):
    """arr: (H, W, 4) float in 0..1, row 0 = bottom. Packed into the .blend."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    img.update()
    img.pack()
    return img


def image_from_array(name, arr, colorspace="sRGB"):
    """arr: (H, W, 4) float in 0..1, row 0 = top."""
    return new_image(name, arr[::-1], colorspace)


def srgb_to_linear(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055).astype(np.float32)


def copy_image(src, name):
    w, h = src.size
    px = np.empty(w * h * 4, np.float32)
    src.pixels.foreach_get(px)
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = src.colorspace_settings.name
    img.pixels.foreach_set(px)
    img.update()
    img.pack()
    return img


# ----------------------------------------------------------------- text

FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_REG = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def font(path=FONT_BOLD):
    for f in bpy.data.fonts:
        if f.filepath == path:
            return f
    f = bpy.data.fonts.load(path)
    f.pack()
    return f


def text_object(name, body, col, size=1.0, mat=None, extrude=0.0, align="CENTER", fnt=None, offset=0.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.font = fnt or font()
    cu.size = size
    cu.extrude = extrude
    cu.offset = offset
    cu.align_x = align
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name, cu)
    if mat:
        cu.materials.append(mat)
    col.objects.link(ob)
    return ob
