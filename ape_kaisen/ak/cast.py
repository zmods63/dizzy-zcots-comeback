"""The cast: copies of the user's LAR_Ape player model. Every character gets its own
recolored copy of the fur texture (the user's original images are never edited),
its own material, and IK arms for Gorilla Tag-style movement."""

import math
import os

import bpy
import numpy as np
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

from . import util as U

APE_SRC = os.path.join(os.path.dirname(__file__), "..", "assets", "LAR_Ape.blend")

# Rest-pose landmarks of the LAR_Ape model (armature space, metres).
HEAD_CENTER = Vector((0.0, -0.03, 0.56))
EYE_Z = 0.548
EYE_X = 0.039
WRIST_TO_GROUND = 0.045  # wrist height when a hand is pressed flat on the ground (palm touching)
STAND_HEIGHT = 0.56      # armature origin above the ground when standing on both hands

_T = {}


class Ape:
    """Handles for one character."""

    def __init__(self, tag):
        self.tag = tag
        self.arm = None
        self.body = None
        self.eyes = None
        self.hand = {}
        self.pole = {}
        self.parts = {}
        self.col = None
        self.mat = None
        self.eye_mat = None
        self._bvh = None
        self._tris = None

    def pb(self, name):
        return self.arm.pose.bones[name]

    @property
    def shape_body(self):
        return self.body.data.shape_keys.key_blocks

    @property
    def shape_eyes(self):
        return self.eyes.data.shape_keys.key_blocks

    def _ensure_bvh(self):
        if self._bvh is not None:
            return
        dg = bpy.context.evaluated_depsgraph_get()
        ev = self.body.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        to_rig = self.arm.matrix_world.inverted() @ self.body.matrix_world
        verts = [to_rig @ v.co for v in me.vertices]
        uv = me.uv_layers.active.data
        tris, tri_uv = [], []
        for lt in me.loop_triangles:
            tris.append(tuple(lt.vertices))
            tri_uv.append([Vector((*uv[i].uv, 0.0)) for i in lt.loops])
        ev.to_mesh_clear()
        self._bvh = BVHTree.FromPolygons(verts, tris)
        self._tris = (verts, tris, tri_uv)

    def surface(self, x, z):
        """Ray-cast from the front onto the rest-pose body. Returns (point, normal, uv) in rig space."""
        self._ensure_bvh()
        for _ in range(12):   # step inward if the ray slips past the edge of the head
            hit, normal, index, _ = self._bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
            if hit is not None:
                verts, tris, tri_uv = self._tris
                a, b, c = (verts[i] for i in tris[index])
                uv = geometry.barycentric_transform(hit, a, b, c, *tri_uv[index])
                return hit, normal, Vector((uv.x, uv.y))
            x *= 0.9
        raise ValueError(f"no surface at x={x:.3f} z={z:.3f}")


# ----------------------------------------------------------------- template

def load_template():
    if _T:
        return _T
    with bpy.data.libraries.load(APE_SRC, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in ("Armature", "LAR_Ape_LOD0", "LAR_Eyes")]
    objs = {o.name.split(".")[0]: o for o in dst.objects}
    arm, body, eyes = objs["Armature"], objs["LAR_Ape_LOD0"], objs["LAR_Eyes"]
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)

    src_mat = body.material_slots[0].material
    group = next(n for n in src_mat.node_tree.nodes if n.type == "GROUP").node_tree
    imgs = {n.image.name.split(".")[0]: n.image for n in group.nodes if n.type == "TEX_IMAGE"}
    normal_tex = next(n for n in src_mat.node_tree.nodes if n.type == "TEX_IMAGE")
    eye_src = eyes.material_slots[1].material

    _T.update(arm=arm, body=body, eyes=eyes, src_mat=src_mat,
              color_px=U.image_pixels(imgs["ApeColor"]), color_cs=imgs["ApeColor"].colorspace_settings.name,
              mask_px=U.image_pixels(imgs["ApeMask"]), mask_cs=imgs["ApeMask"].colorspace_settings.name,
              normal_img=U.copy_image(normal_tex.image, "AK_ApeN"), eye_src=eye_src)
    calibrate_pole_angle()
    return _T


def fur_texture(tag, tint):
    """Bake the in-game tint into the character's own copy of the fur texture:
    fur (white in the mask) is multiplied by the tint, face/belly/palms keep their gray."""
    t = load_template()
    col = t["color_px"][..., :3]
    msk = t["mask_px"][..., :1]
    if t["color_cs"] == "sRGB":
        col = U.srgb_to_linear(col)
    if t["mask_cs"] == "sRGB":
        msk = U.srgb_to_linear(msk)
    out = col * (msk * np.array(tint, np.float32) + (1 - msk))
    out = U.linear_to_srgb(out)
    rgba = np.concatenate([out, np.ones_like(out[..., :1])], axis=-1)
    return U.new_image(f"{tag}_ApeColor", rgba, "sRGB")


def char_material(tag, tex):
    t = load_template()
    mat = t["src_mat"].copy()
    mat.name = f"{tag}_Fur"
    nt = mat.node_tree
    group = next(n for n in nt.nodes if n.type == "GROUP")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    img = nt.nodes.new("ShaderNodeTexImage")
    img.name = "FurTex"
    img.image = tex
    img.interpolation = "Closest"   # same crisp pixel look as the original material
    img.location = group.location
    nt.nodes.remove(group)
    nt.nodes.active = img           # what Solid mode's Texture colour shows
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    for n in nt.nodes:
        if n.type == "TEX_IMAGE" and n.name != img.name:   # (node wrappers aren't identical objects)
            n.image = t["normal_img"]
    return mat


def eye_material(tag):
    """Copy of the ape's glossy eye shader with an (off by default) glowing iris."""
    t = load_template()
    mat = t["eye_src"].copy()
    mat.name = f"{tag}_Eye"
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type == "TEX_IMAGE":
            nt.nodes.remove(n)      # unused node that pointed at an original image
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    N, L = nt.nodes.new, nt.links.new
    uv = N("ShaderNodeUVMap")
    dist = N("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    dist.inputs[1].default_value = (0.5, 0.5, 0.0)
    iris = N("ShaderNodeMapRange")
    iris.inputs["From Min"].default_value = 0.035
    iris.inputs["From Max"].default_value = 0.12
    iris.inputs["To Min"].default_value = 1.0
    iris.inputs["To Max"].default_value = 0.0
    glow = N("ShaderNodeValue")
    glow.name = "IrisGlow"
    glow.outputs[0].default_value = 0.0
    color = N("ShaderNodeRGB")
    color.name = "IrisColor"
    color.outputs[0].default_value = (1.0, 0.012, 0.004, 1)
    strength = N("ShaderNodeMath")
    strength.operation = "MULTIPLY"
    em = N("ShaderNodeEmission")
    add = N("ShaderNodeAddShader")
    L(uv.outputs["UV"], dist.inputs[0])
    L(dist.outputs["Value"], iris.inputs["Value"])
    L(iris.outputs["Result"], strength.inputs[0])
    L(glow.outputs[0], strength.inputs[1])
    L(color.outputs[0], em.inputs["Color"])
    L(strength.outputs[0], em.inputs["Strength"])
    L(bsdf.outputs[0], add.inputs[0])
    L(em.outputs[0], add.inputs[1])
    L(add.outputs[0], out.inputs["Surface"])
    return mat


# ----------------------------------------------------------------- rig

POLE_OFFSET = Vector((0.25, 0.55, 0.15))   # behind/outside the elbow (x mirrored per side)
_POLE_ANGLE = {}


def rest_arm_points(arm, side):
    b = arm.data.bones
    return (b[f"upperarm.{side}"].head_local.copy(), b[f"lowerarm.{side}"].head_local.copy(),
            b[f"lowerarm.{side}"].tail_local.copy())


def _pole_rest_location(arm, side):
    _, elbow, _ = rest_arm_points(arm, side)
    sx = 1 if side == "L" else -1
    return elbow + Vector((POLE_OFFSET.x * sx, POLE_OFFSET.y, POLE_OFFSET.z))


def calibrate_pole_angle():
    """Find the IK pole angle that keeps the arm in its rest pose when the hand sits at rest."""
    scene = bpy.context.scene
    arm = _T["arm"].copy()
    arm.data = _T["arm"].data.copy()
    scene.collection.objects.link(arm)
    tmp = []
    for side in "LR":
        _, _, wrist = rest_arm_points(arm, side)
        tgt = bpy.data.objects.new("cal_t", None)
        pole = bpy.data.objects.new("cal_p", None)
        scene.collection.objects.link(tgt)
        scene.collection.objects.link(pole)
        tgt.location = wrist
        pole.location = _pole_rest_location(arm, side)
        tmp += [tgt, pole]
        c = arm.pose.bones[f"lowerarm.{side}"].constraints.new("IK")
        c.target, c.pole_target, c.chain_count, c.use_tail = tgt, pole, 2, True
        rest = arm.data.bones[f"lowerarm.{side}"].matrix_local
        best = None
        for deg in range(-180, 180):
            c.pole_angle = math.radians(deg)
            bpy.context.view_layer.update()
            m = arm.pose.bones[f"lowerarm.{side}"].matrix
            err = sum((m.col[i].xyz - rest.col[i].xyz).length for i in range(3))
            if best is None or err < best[0]:
                best = (err, deg)
        _POLE_ANGLE[side] = math.radians(best[1])
    for o in tmp:
        bpy.data.objects.remove(o)
    bpy.data.objects.remove(arm)


def add_ik(ape):
    arm = ape.arm
    for side in "LR":
        _, _, wrist = rest_arm_points(arm, side)
        tgt = bpy.data.objects.new(f"{ape.tag}_Hand.{side}", None)
        tgt.empty_display_type = "SPHERE"
        tgt.empty_display_size = 0.06
        ape.col.objects.link(tgt)
        tgt.location = arm.matrix_world @ wrist
        pole = bpy.data.objects.new(f"{ape.tag}_Pole.{side}", None)
        pole.empty_display_type = "CONE"
        pole.empty_display_size = 0.04
        ape.col.objects.link(pole)
        pole.parent = arm
        pole.location = _pole_rest_location(arm, side)
        c = arm.pose.bones[f"lowerarm.{side}"].constraints.new("IK")
        c.name = "IK"
        c.target = tgt
        c.pole_target = pole
        c.pole_angle = _POLE_ANGLE[side]
        c.chain_count = 2
        c.use_tail = True
        c.use_stretch = False
        # When a hand is on the ground it copies the target's orientation (palm flat, weight on it).
        plant = arm.pose.bones[f"hand.{side}"].constraints.new("COPY_ROTATION")
        plant.name = "Plant"
        plant.target = tgt
        plant.influence = 0.0
        ape.hand[side] = tgt
        ape.pole[side] = pole


# ----------------------------------------------------------------- build

def build_ape(tag, tint, col):
    t = load_template()
    ape = Ape(tag)
    ape.col = col

    arm = t["arm"].copy()
    arm.data = t["arm"].data.copy()
    arm.name = arm.data.name = f"{tag}_Rig"
    col.objects.link(arm)

    ape.mat = char_material(tag, fur_texture(tag, tint))
    body = t["body"].copy()
    body.data = t["body"].data.copy()
    body.name = f"{tag}_Body"
    body.parent = arm
    body.modifiers["Armature"].object = arm
    body.material_slots[0].material = ape.mat
    col.objects.link(body)

    ape.eye_mat = eye_material(tag)
    eyes = t["eyes"].copy()
    eyes.data = t["eyes"].data.copy()
    eyes.name = f"{tag}_Eyes"
    eyes.parent = arm
    eyes.modifiers["Armature"].object = arm   # left empty in the source rig, so eyes ignored head turns
    for slot in eyes.material_slots:
        slot.material = ape.eye_mat
    col.objects.link(eyes)

    ape.arm, ape.body, ape.eyes = arm, body, eyes
    bpy.context.view_layer.update()
    add_ik(ape)
    return ape
