"""The rooftop curse: a lumpy many-eyed monster with a toothy mouth and two long arms.

Rig: everything hangs off `root` (an empty at the base, facing -Y). Arms are NURBS curves
whose points are hooked to empties; `reach()` keys those empties so an arm bends from the
shoulder to any world target. Hands open/grip with a shape key. The body has a 'Dent' shape
key (the punch) and is pre-cut into pieces for when it gets sliced apart."""

import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

from . import mats as M
from . import util as U

HEIGHT = 4.6


def skin_material(name="CurseSkin", cut=False):
    """Pale violet-gray wet skin with dark mottling and veins. 'dissolve' (object attribute)
    0..1 burns it away into black ash with red embers."""
    mat, nt, out = U.new_material(name)
    g = M.G(nt)
    tc = g.n("ShaderNodeTexCoord")
    mott = g.n("ShaderNodeTexNoise", Scale=1.3, Detail=6.0, Roughness=0.6)
    g.l(tc.outputs["Object"], mott.inputs["Vector"])
    ramp = M._ramp(g, [(0.32, (0.08, 0.05, 0.1)), (0.55, (0.32, 0.25, 0.36)), (0.78, (0.55, 0.48, 0.56))])
    g.l(mott.outputs["Fac"], ramp.inputs["Fac"])
    vein = g.n("ShaderNodeTexVoronoi", {"feature": "DISTANCE_TO_EDGE"}, Scale=3.5)
    g.l(tc.outputs["Object"], vein.inputs["Vector"])
    vmask = g.n("ShaderNodeMapRange", From_Min=0.0, From_Max=0.035, To_Min=0.75, To_Max=0.0)
    g.l(vein.outputs["Distance"], vmask.inputs["Value"])
    col = g.n("ShaderNodeMix", {"data_type": "RGBA"})
    g.l(vmask.outputs["Result"], col.inputs["Factor"])
    g.l(ramp.outputs["Color"], col.inputs[6])
    col.inputs[7].default_value = (0.25, 0.02, 0.06, 1)
    b = g.n("ShaderNodeBsdfPrincipled", Roughness=0.34)
    b.inputs["Coat Weight"].default_value = 0.35
    b.inputs["Coat Roughness"].default_value = 0.2
    b.inputs["Subsurface Weight"].default_value = 0.08
    b.inputs["Subsurface Radius"].default_value = (0.5, 0.1, 0.12)
    g.l(col.outputs[2], b.inputs["Base Color"])
    bump_n = g.n("ShaderNodeTexNoise", Scale=14.0, Detail=8.0)
    g.l(tc.outputs["Object"], bump_n.inputs["Vector"])
    bump = g.n("ShaderNodeBump", Strength=0.35, Distance=0.03)
    g.l(bump_n.outputs["Fac"], bump.inputs["Height"])
    g.l(bump.outputs["Normal"], b.inputs["Normal"])
    # dissolve into ash
    attr = g.n("ShaderNodeAttribute", {"attribute_type": "OBJECT", "attribute_name": "dissolve"})
    dn = g.n("ShaderNodeTexNoise", Scale=2.4, Detail=5.0)
    g.l(tc.outputs["Object"], dn.inputs["Vector"])
    gone = g.n("ShaderNodeMath", {"operation": "LESS_THAN"})
    g.l(dn.outputs["Fac"], gone.inputs[0])
    g.l(attr.outputs["Fac"], gone.inputs[1])
    ed = g.n("ShaderNodeMath", {"operation": "SUBTRACT"})
    g.l(dn.outputs["Fac"], ed.inputs[0])
    g.l(attr.outputs["Fac"], ed.inputs[1])
    ember = g.n("ShaderNodeMapRange", From_Min=0.0, From_Max=0.05, To_Min=18.0, To_Max=0.0)
    g.l(ed.outputs[0], ember.inputs["Value"])
    b.inputs["Emission Color"].default_value = (1.0, 0.08, 0.02, 1)
    g.l(ember.outputs["Result"], b.inputs["Emission Strength"])
    tr = g.n("ShaderNodeBsdfTransparent")
    mix = g.n("ShaderNodeMixShader")
    g.l(gone.outputs[0], mix.inputs["Fac"])
    g.l(b.outputs[0], mix.inputs[1])
    g.l(tr.outputs[0], mix.inputs[2])
    g.l(mix.outputs[0], out.inputs[0])
    M._transparent_settings(mat)
    return mat


def flesh_material():
    """Inside of the curse where it's been cut."""
    return M.paint("CurseFlesh", (0.35, 0.02, 0.05), rough=0.3)


class Curse:
    def __init__(self):
        self.root = None
        self.body = None
        self.pieces = []
        self.arms = {}
        self.hands = {}
        self.eyes = []
        self.jaw = None
        self.mouth = None
        self.parts = []


def _metaball_body(col, rnd):
    mb = bpy.data.metaballs.new("CurseMeta")
    mb.resolution = 0.11
    mb.render_resolution = 0.11
    ob = bpy.data.objects.new("CurseMeta", mb)
    col.objects.link(ob)
    blobs = [((0, 0.1, 1.5), 1.55, (1.15, 0.95, 1.0)), ((0, -0.25, 2.85), 1.3, (1.1, 0.95, 0.9)),
             ((0, 0.35, 3.5), 0.95, (1.0, 0.9, 0.8)), ((0, 0.15, 0.55), 1.25, (1.25, 1.1, 0.6))]
    for _ in range(14):
        a = rnd.uniform(0, 2 * math.pi)
        z = rnd.uniform(0.6, 3.6)
        r = 1.15 + 0.25 * math.sin(z)
        blobs.append(((math.cos(a) * r, math.sin(a) * r * 0.85 + 0.1, z), rnd.uniform(0.45, 0.8), (1, 1, 1)))
    for (co, rad, sc) in blobs:
        e = mb.elements.new(type="ELLIPSOID")
        e.co = co
        e.radius = rad
        e.size_x, e.size_y, e.size_z = sc
        e.stiffness = 2.0
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.name = "CurseBody"
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    return me


def _surface_points(me, mw):
    verts = [mw @ v.co for v in me.vertices]
    return BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])


def build_curse(col, location=(0, 0, 0), yaw=0.0):
    rnd = random.Random(66)
    cr = Curse()
    root = bpy.data.objects.new("Curse_Root", None)
    root.empty_display_type = "ARROWS"
    col.objects.link(root)
    cr.root = root

    skin = skin_material()
    me = _metaball_body(col, rnd)
    body = bpy.data.objects.new("Curse_Body", me)
    col.objects.link(body)
    me.materials.append(skin)
    me.shade_smooth()
    body.parent = root
    body["dissolve"] = 0.0
    tex = bpy.data.textures.new("CurseWrithe", "CLOUDS")
    tex.noise_scale = 0.55
    writhe = bpy.data.objects.new("Curse_Writhe", None)
    col.objects.link(writhe)
    writhe.parent = root
    disp = body.modifiers.new("Writhe", "DISPLACE")
    disp.texture = tex
    disp.texture_coords = "OBJECT"
    disp.texture_coords_object = writhe
    disp.strength = 0.22
    disp.mid_level = 0.5
    writhe.location = (0, 0, 0)
    writhe.keyframe_insert("location", frame=1)
    writhe.location = (0.0, 0.0, 9.0)            # slowly crawling bumps over the surface
    writhe.keyframe_insert("location", frame=3000)
    U.set_interpolation(writhe, "LINEAR")
    cr.body = body

    bvh = _surface_points(me, Matrix())

    def on_surface(direction, origin_z):
        d = Vector(direction).normalized()
        o = Vector((0, 0, origin_z)) + d * 6
        hit, normal, _, _ = bvh.ray_cast(o, -d)
        return hit, normal

    # mouth: a dark gash full of teeth across the front of the upper mass
    mouth_c, mouth_n = on_surface((0, -1, -0.05), 2.55)
    mouth_m = M.paint("CurseMouth", (0.06, 0.0, 0.01), rough=0.5)
    bm = bmesh.new()
    U.bm_sphere(bm, 1.0, segs=24, rings=12)
    mouth = U.mesh_object("Curse_Mouth", bm, col, mats=[mouth_m], smooth=True)
    mouth.location = mouth_c - mouth_n * 0.12
    mouth.scale = (0.95, 0.35, 0.28)
    mouth.rotation_euler = mouth_n.to_track_quat("-Y", "Z").to_euler()
    mouth.parent = root
    cr.mouth = mouth
    tooth_m = M.paint("CurseTeeth", (0.78, 0.74, 0.6), rough=0.4)
    jaw = bpy.data.objects.new("Curse_Jaw", None)
    col.objects.link(jaw)
    jaw.location = mouth.location.copy()
    jaw.parent = root
    cr.jaw = jaw
    for row, zoff, down in (("Upper", 0.2, -1), ("Lower", -0.2, 1)):
        bm = bmesh.new()
        for k in range(15):
            t = (k + 0.5) / 15
            ang = math.pi * (0.12 + 0.76 * t)
            x = -math.cos(ang) * 0.85
            depth = math.sin(ang) * 0.22
            base = Vector((x, -depth, zoff * (0.6 + 0.4 * math.sin(ang))))
            length = rnd.uniform(0.12, 0.26) * (0.6 + 0.4 * math.sin(ang))
            U.bm_cone_between(bm, base, base + Vector((rnd.uniform(-0.02, 0.02), -0.02, down * length)),
                              rnd.uniform(0.035, 0.055), 0.002, segs=6)
        teeth = U.mesh_object(f"Curse_Teeth{row}", bm, col, mats=[tooth_m], smooth=True)
        teeth.location = mouth.location
        teeth.rotation_euler = mouth.rotation_euler
        teeth.parent = jaw if row == "Lower" else root
        if row == "Lower":
            teeth.location = Vector((0, 0, 0))
            teeth.rotation_euler = mouth.rotation_euler
        cr.parts.append(teeth)

    # eyes: yellow, bloodshot, different sizes, scattered over the front
    sclera = M.paint("CurseSclera", (0.85, 0.72, 0.28), rough=0.15)
    pupil_m = M.paint("CursePupil", (0.0, 0.0, 0.0), rough=0.1)
    lid_m = M.paint("CurseLid", (0.12, 0.06, 0.12), rough=0.5)
    spots = [((-0.42, -1, 0.42), 3.0, 0.34), ((0.4, -1, 0.5), 3.0, 0.28), ((0.0, -1, 0.85), 3.0, 0.18),
             ((-0.85, -1, 0.15), 2.4, 0.16), ((0.9, -1, 0.05), 2.4, 0.2), ((-0.55, -1, -0.45), 1.6, 0.14),
             ((0.65, -1, -0.35), 1.7, 0.12)]
    for i, (d, oz, r) in enumerate(spots):
        hit, normal = on_surface(d, oz)
        if hit is None:
            continue
        eye = bpy.data.objects.new(f"Curse_Eye{i}", None)
        col.objects.link(eye)
        eye.location = hit - normal * r * 0.35
        eye.rotation_euler = normal.to_track_quat("-Y", "Z").to_euler()
        eye.parent = root
        bm = bmesh.new()
        U.bm_sphere(bm, r, segs=20, rings=12)
        ball = U.mesh_object(f"Curse_EyeBall{i}", bm, col, mats=[sclera], smooth=True)
        ball.parent = eye
        bm = bmesh.new()
        U.bm_sphere(bm, r * 0.42, loc=(0, -r * 0.82, 0), scale=(0.55, 0.45, 1.0), segs=14, rings=8)
        pupil = U.mesh_object(f"Curse_Pupil{i}", bm, col, mats=[pupil_m], smooth=True)
        pupil.parent = eye
        bm = bmesh.new()
        ring = [Vector((math.cos(a) * r * 1.02, -0.0, math.sin(a) * r * 1.02)) for a in (2 * math.pi * k / 24 for k in range(25))]
        U.bm_tube(bm, ring, [r * 0.16] * len(ring), segs=8, cap=False)
        lid = U.mesh_object(f"Curse_Lid{i}", bm, col, mats=[lid_m], smooth=True)
        lid.parent = eye
        cr.eyes.append((eye, pupil))

    # arms: hooked NURBS curves from the shoulders
    for side, sx in (("L", 1), ("R", -1)):
        shoulder = on_surface((sx * 1.0, -0.25, 0.15), 3.0)[0]
        pts = [shoulder + Vector((sx * 0.6 * t, -0.25 * t, -2.2 * t)) for t in (0, 0.2, 0.4, 0.6, 0.8, 1.0)]
        cu = bpy.data.curves.new(f"Curse_Arm{side}", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.2
        cu.bevel_resolution = 5
        cu.resolution_u = 10
        cu.use_fill_caps = True
        sp = cu.splines.new("NURBS")
        sp.points.add(len(pts) - 1)
        for k, p in enumerate(pts):
            sp.points[k].co = (*p, 1.0)
            sp.points[k].radius = 1.15 - 0.85 * (k / (len(pts) - 1)) ** 0.7
        sp.order_u = 4
        sp.use_endpoint_u = True
        arm_ob = bpy.data.objects.new(f"Curse_Arm{side}", cu)
        col.objects.link(arm_ob)
        cu.materials.append(skin)
        arm_ob.parent = root
        hooks = []
        for k, p in enumerate(pts):
            e = bpy.data.objects.new(f"Curse_Arm{side}_{k}", None)
            e.empty_display_size = 0.15
            col.objects.link(e)
            e.location = p
            m = arm_ob.modifiers.new(f"Hook{k}", "HOOK")
            m.object = e
            m.vertex_indices_set([k])
            m.matrix_inverse = Matrix.Translation(p).inverted()
            hooks.append(e)
        cr.arms[side] = {"curve": arm_ob, "hooks": hooks, "shoulder": shoulder}
        cr.hands[side] = _hand(col, side, skin, rnd)
        cr.hands[side].parent = hooks[-1]

    # stubby tentacle roots spreading over the floor
    bm = bmesh.new()
    for k in range(7):
        a = 2 * math.pi * k / 7 + 0.3
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = [d * 1.0 + Vector((0, 0, 0.5)), d * 1.6 + Vector((0, 0, 0.18)), d * 2.2 + Vector((0, 0, 0.06)),
               d * 2.6 + Vector((0.15 * math.sin(k), 0.15 * math.cos(k), 0.04))]
        U.bm_tube(bm, pts, [0.32, 0.2, 0.1, 0.0], segs=10)
    roots = U.mesh_object("Curse_Roots", bm, col, mats=[skin], smooth=True)
    roots.parent = root
    cr.parts.append(roots)

    _dent_key(body, Vector((0.0, -1.3, 2.9)))
    cr.pieces = _slice_pieces(col, body, root, skin)
    root.location = location
    root.rotation_euler = (0, 0, yaw)
    return cr


def _hand(col, side, skin, rnd):
    """Palm and three long clawed fingers along -Z (pointing away from the arm). Shape key 'Grip'."""
    bm = bmesh.new()
    U.bm_sphere(bm, 0.22, scale=(1.0, 0.55, 1.15), segs=16, rings=10)
    fingers = []
    for k, ang in enumerate((-0.45, 0.0, 0.45)):
        base = Vector((math.sin(ang) * 0.16, 0.0, -0.18))
        pts = [base + Vector((math.sin(ang) * 0.12 * t, 0, -0.55 * t)) for t in (0, 0.33, 0.66, 1.0)]
        U.bm_tube(bm, pts, [0.075, 0.06, 0.045, 0.0], segs=8)
        fingers.append(pts)
    ob = U.mesh_object(f"Curse_Hand{side}", bm, col, mats=[skin], smooth=True)
    ob.shape_key_add(name="Basis")
    grip = ob.shape_key_add(name="Grip")
    for v, kv in zip(ob.data.vertices, grip.data):
        if v.co.z < -0.2:
            t = min((-v.co.z - 0.2) / 0.55, 1.0)
            ang = t * 2.4
            r = Matrix.Rotation(-ang, 3, "X")
            kv.co = Vector((v.co.x, 0, -0.2)) + r @ Vector((0, v.co.y, v.co.z + 0.2))
    return ob


def _dent_key(body, point, radius=0.9, depth=0.45):
    body.shape_key_add(name="Basis")
    dent = body.shape_key_add(name="Dent")
    for v, kv in zip(body.data.vertices, dent.data):
        d = (v.co - point).length
        if d < radius:
            w = (1 - d / radius) ** 2
            kv.co = v.co + (Vector((0, 1, 0.15)).normalized() * depth * w)


def _slice_pieces(col, body, root, skin):
    """Three chunks of the body cut along diagonal planes, hidden until the slice."""
    flesh = flesh_material()
    # tilted cuts that never cross inside the body (checked over its +-1.6 m width)
    planes = [(Vector((0, 0, 2.4)), Vector((0.25, 0.0, 1.0)).normalized()),
              (Vector((0, 0, 1.1)), Vector((-0.25, 0.08, 1.0)).normalized())]
    pieces = []
    for idx in range(3):
        bm = bmesh.new()
        bm.from_mesh(body.data)
        for k, (co, no) in enumerate(planes):
            keep_above = (idx == 0 and k == 0) or (idx == 1 and k == 1)
            keep_below = (idx == 1 and k == 0) or (idx == 2 and k == 1)
            if not (keep_above or keep_below):
                continue
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no,
                                         clear_inner=keep_above, clear_outer=keep_below)
            edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                filled = bmesh.ops.holes_fill(bm, edges=edges)
                for f in filled["faces"]:
                    f.material_index = 1
        me = bpy.data.meshes.new(f"Curse_Piece{idx}")
        bm.to_mesh(me)
        bm.free()
        if me.shape_keys:
            pass
        ob = bpy.data.objects.new(f"Curse_Piece{idx}", me)
        col.objects.link(ob)
        me.materials.append(skin)
        me.materials.append(flesh)
        me.shade_smooth()
        ob.parent = root
        ob["dissolve"] = 0.0
        src = body.modifiers["Writhe"]
        disp = ob.modifiers.new("Writhe", "DISPLACE")      # same surface as the body at the cut
        disp.texture, disp.texture_coords = src.texture, src.texture_coords
        disp.texture_coords_object, disp.strength, disp.mid_level = src.texture_coords_object, src.strength, src.mid_level
        ob.hide_render = ob.hide_viewport = True
        pieces.append(ob)
    return pieces


# ----------------------------------------------------------------- animation helpers

def reach(cr, f, side, target, bend=(0, 0, 1.0), grip=None):
    """Key one arm so it bends from the shoulder to a world-space target point."""
    arm = cr.arms[side]
    hooks = arm["hooks"]
    mw = cr.root.matrix_basis.copy()        # the root is unparented; matrix_world can be stale while keying
    sh = mw @ arm["shoulder"]
    tgt = Vector(target)
    mid = (sh + tgt) / 2 + Vector(bend) * ((tgt - sh).length * 0.28)
    n = len(hooks)
    inv = mw.inverted()
    for k, e in enumerate(hooks):
        t = k / (n - 1)
        p = (1 - t) ** 2 * sh + 2 * (1 - t) * t * mid + t ** 2 * tgt
        e.location = p
        e.keyframe_insert("location", frame=f)
    d = (tgt - mid).normalized()
    hooks[-1].rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    hooks[-1].keyframe_insert("rotation_euler", frame=f)
    if grip is not None:
        kb = cr.hands[side].data.shape_keys.key_blocks["Grip"]
        kb.value = grip
        kb.keyframe_insert("value", frame=f)


def mouth(cr, f, open_amount):
    cr.mouth.scale.z = 0.28 + 0.5 * open_amount
    cr.mouth.keyframe_insert("scale", frame=f)
    cr.jaw.rotation_euler.x = 0.0
    loc = cr.mouth.location.copy()
    cr.jaw.location = loc - Vector((0, 0, 0.45 * open_amount))
    cr.jaw.keyframe_insert("location", frame=f)


def look(cr, f, target, spread=0.15):
    """Every eye turns toward a world target (each a bit differently, it's a curse)."""
    rm = cr.root.matrix_basis.copy()
    for i, (eye, pupil) in enumerate(cr.eyes):
        e_world = rm @ eye.matrix_basis.translation
        d = (Vector(target) - e_world).normalized()
        local = (rm.to_3x3().inverted() @ d)
        q = local.to_track_quat("-Y", "Z")
        jitter = Quaternion((0, 0, 1), spread * math.sin(i * 1.7))
        eye.rotation_mode = "QUATERNION"
        eye.rotation_quaternion = q @ jitter
        eye.keyframe_insert("rotation_quaternion", frame=f)
