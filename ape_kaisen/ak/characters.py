"""Who's who in Ape Kaisen. Pure Gorilla Tag style: every character is the user's ape
with its own fur color (a recolored copy of the texture). Gojo keeps his blindfold;
Sukuna's markings, extra eyes and red irises are painted into a face overlay of Yuji's
material and creep in when he takes over."""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFilter

from . import cast as C
from . import util as U

# Average fur color each character should end up with (sRGB hex).
FUR = {
    "Yuji": "#E9808F",      # salmon pink
    "Megumi": "#1D2130",    # near-black navy
    "Gojo": "#E8ECF3",      # white
    "Grandpa": "#8C827A",   # old warm gray
    "Sasaki": "#8C66C4",    # purple
    "Iguchi": "#6F9A4B",    # green
    "DogWhite": "#F0F2F6",  # Megumi's Divine Dogs: two small monkes
    "DogBlack": "#141518",
}
DOG_SCALE = 0.55


def hex_to_linear(h):
    h = h.lstrip("#")
    rgb = np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
    return U.srgb_to_linear(rgb)


def tint_for(color_hex):
    """Tint that makes the masked fur average out to color_hex."""
    t = C.load_template()
    col = t["color_px"][..., :3]
    msk = t["mask_px"][..., 0]
    if t["color_cs"] == "sRGB":
        col = U.srgb_to_linear(col)
    fur_mean = col[msk > 0.9].mean(axis=0)
    return tuple(float(v) for v in hex_to_linear(color_hex) / np.maximum(fur_mean, 1e-4))


def make(tag, col, fur_key=None):
    ape = C.build_ape(tag, tint_for(FUR[fur_key or tag]), col)
    ape.mat.diffuse_color = (*hex_to_linear(FUR[fur_key or tag]), 1.0)     # solid/workbench viewport colour
    return ape


# ----------------------------------------------------------------- Gojo's blindfold

def blindfold(ape):
    bm = bmesh.new()
    segs, rows = 72, [(-0.033, 0.0), (-0.029, 0.003), (0.029, 0.003), (0.033, 0.0)]
    cy, rx, ry_front, ry_back = -0.035, 0.161, 0.136, 0.131
    grid = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        ry = ry_front if math.sin(a) < 0 else ry_back
        d = Vector((math.cos(a), math.sin(a), 0))
        ring = []
        for dz, bulge in rows:
            p = Vector((d.x * (rx + bulge), cy + d.y * (ry + bulge), C.EYE_Z + 0.004 + dz))
            ring.append(bm.verts.new(p))
        grid.append(ring)
    for k in range(segs):
        a, b = grid[k], grid[(k + 1) % segs]
        for r in range(len(rows) - 1):
            bm.faces.new((a[r], b[r], b[r + 1], a[r + 1]))
    ob = U.mesh_object(f"{ape.tag}_Blindfold", bm, ape.col, smooth=True,
                       mats=[U.principled("Gojo_Blindfold_Mat", (0.012, 0.012, 0.016), rough=0.55)])
    ob.modifiers.new("Thick", "SOLIDIFY").thickness = 0.005
    sub = ob.modifiers.new("Smooth", "SUBSURF")
    sub.levels = sub.render_levels = 2
    U.parent_to_bone(ob, ape.arm, "head")
    ape.parts["Blindfold"] = ob
    return ob


# ----------------------------------------------------------------- Sukuna overlay

# Strokes in the face's front view: points (x, z) in rig space, width in metres,
# growth window (when along the takeover each stroke draws itself, inner end first).
SUKUNA_STROKES = []
# The face plate is only about +-0.08 m wide at cheek height, so everything stays inside it.
for _sx in (1, -1):
    SUKUNA_STROKES += [
        ([(_sx * x, z) for x, z in ((0.024, 0.4815), (0.040, 0.4775), (0.058, 0.4785), (0.073, 0.4855))], 0.0058, (0.00, 0.38)),
        ([(_sx * x, z) for x, z in ((0.028, 0.4685), (0.044, 0.4645), (0.060, 0.4655), (0.072, 0.4715))], 0.0050, (0.08, 0.45)),
        ([(_sx * x, z) for x, z in ((0.010, 0.624), (0.030, 0.620), (0.052, 0.611))], 0.0050, (0.25, 0.58)),
    ]
# Second pair of eyes: almond slits under the real eyes that open late in the takeover.
SUKUNA_EYES = [((sx * 0.041, 0.4955), 0.021, 0.0078, (0.62, 0.92)) for sx in (1, -1)]


def _paint_sukuna(ape, res=1024, ss=4):
    """Paint Sukuna's markings into a high-res overlay covering just the face's UV island.
    Returns (overlay image, data image, uv origin, uv size)."""
    strokes = []
    for pts, width, (g0, g1) in SUKUNA_STROKES:
        dense = []
        for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
            for k in range(10):
                t = k / 10
                dense.append((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t))
        dense.append(pts[-1])
        hits = [ape.surface(x, z) for x, z in dense]
        strokes.append((hits, width, g0, g1))
    eyes = []
    for (cx, cz), hw, hh, (g0, g1) in SUKUNA_EYES:
        outline = []
        for k in range(40):
            a = 2 * math.pi * k / 40
            x = math.cos(a)
            y = math.sin(a) * (1 - x * x) ** 0.35        # almond: pointed at the corners
            outline.append((cx + x * hw, cz + y * hh + 0.003 * abs(x) * (1 if cx * x > 0 else -0.4)))
        eyes.append(([ape.surface(x, z) for x, z in outline], ape.surface(cx, cz), g0, g1))

    uvs = [h[2] for s in strokes for h in s[0]] + [h[2] for e in eyes for h in e[0]]
    face_uv = ape.surface(0.0, 0.52)[2]
    stray = [u for u in uvs if (u - face_uv).length > 0.1]
    if stray:
        raise ValueError(f"{len(stray)} Sukuna paint points fall off the face's UV island")
    umin = min(u.x for u in uvs)
    umax = max(u.x for u in uvs)
    vmin = min(u.y for u in uvs)
    vmax = max(u.y for u in uvs)
    size = max(umax - umin, vmax - vmin) * 1.25
    u0 = (umin + umax) / 2 - size / 2
    v0 = (vmin + vmax) / 2 - size / 2
    R = res * ss

    def px(uv):
        return ((uv.x - u0) / size * R, (1 - (uv.y - v0) / size) * R)

    cover = Image.new("L", (R, R), 0)
    growth = Image.new("L", (R, R), 255)
    iris = Image.new("L", (R, R), 0)
    dc, dg, di = ImageDraw.Draw(cover), ImageDraw.Draw(growth), ImageDraw.Draw(iris)

    for hits, width, g0, g1 in strokes:
        lengths = [0.0]
        for a, b in zip(hits, hits[1:]):
            lengths.append(lengths[-1] + (b[0] - a[0]).length)
        total = lengths[-1]
        uv_per_m = sum((b[2] - a[2]).length for a, b in zip(hits, hits[1:])) / total
        for i in range(len(hits) - 1):
            a, b = px(hits[i][2]), px(hits[i + 1][2])
            steps = max(2, int(math.dist(a, b)))
            for k in range(steps):
                t = (lengths[i] + (lengths[i + 1] - lengths[i]) * k / steps) / total
                x = a[0] + (b[0] - a[0]) * k / steps
                y = a[1] + (b[1] - a[1]) * k / steps
                taper = 0.22 + 0.78 * math.sin(math.pi * t) ** 0.55
                r = width * 0.5 * taper * uv_per_m / size * R
                box = (x - r, y - r, x + r, y + r)
                dc.ellipse(box, fill=255)
                dg.ellipse(box, fill=int(255 * (g0 + (g1 - g0) * t)))

    for outline, (center, _, cuv), g0, g1 in eyes:
        cx, cy = px(cuv)
        poly = [px(h[2]) for h in outline]
        dc.polygon(poly, fill=255)
        for k in range(24, 0, -1):          # opens from a slit: outer rings appear last
            s = k / 24
            ring = [(cx + (x - cx), cy + (y - cy) * s) for x, y in poly]
            dg.polygon(ring, fill=int(255 * (g0 + (g1 - g0) * s)))
        span = max(abs(p[0] - cx) for p in poly)
        ir = span * 0.32
        di.ellipse((cx - ir, cy - ir * 1.15, cx + ir, cy + ir * 1.15), fill=255)

    growth = growth.filter(ImageFilter.MinFilter(9))     # bleed values past the edges before downsizing
    cover = cover.resize((res, res), Image.LANCZOS)
    growth = growth.resize((res, res), Image.BOX)
    iris = iris.resize((res, res), Image.LANCZOS)

    a_cov = np.asarray(cover, np.float32) / 255
    a_iris = np.asarray(iris, np.float32) / 255
    ink = np.zeros((res, res, 4), np.float32)
    ink[..., 0] = 0.012 + 0.75 * a_iris          # black ink, red irises inside the extra eyes
    ink[..., 1] = 0.006
    ink[..., 2] = 0.008
    ink[..., 3] = a_cov
    data = np.zeros((res, res, 4), np.float32)
    data[..., 0] = np.asarray(growth, np.float32) / 255
    data[..., 1] = a_iris
    data[..., 3] = 1.0
    overlay = U.image_from_array(f"{ape.tag}_SukunaInk", ink, "sRGB")
    dataimg = U.image_from_array(f"{ape.tag}_SukunaGrowth", data, "Non-Color")
    return overlay, dataimg, (u0, v0), size


def add_sukuna(ape):
    """Wire the overlay into the character's own fur material. Animate the 'SukunaReveal' value 0..1."""
    overlay, dataimg, (u0, v0), size = _paint_sukuna(ape)
    nt = ape.mat.node_tree
    N, L = nt.nodes.new, nt.links.new
    fur = nt.nodes["FurTex"]
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = N("ShaderNodeUVMap")
    mp = N("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-u0 / size, -v0 / size, 0)
    mp.inputs["Scale"].default_value = (1 / size, 1 / size, 1)
    ink = N("ShaderNodeTexImage")
    ink.image = overlay
    ink.extension = "CLIP"
    dat = N("ShaderNodeTexImage")
    dat.image = dataimg
    dat.extension = "CLIP"
    reveal = N("ShaderNodeValue")
    reveal.name = "SukunaReveal"
    reveal.outputs[0].default_value = 0.0
    sep = N("ShaderNodeSeparateColor")
    drawn = N("ShaderNodeMath")
    drawn.operation = "LESS_THAN"                 # growth < reveal
    shown = N("ShaderNodeMath")
    shown.operation = "MULTIPLY"                  # ... times coverage
    mix = N("ShaderNodeMix")
    mix.data_type = "RGBA"
    behind = N("ShaderNodeMath")
    behind.operation = "SUBTRACT"                 # reveal - growth: how long ago this pixel appeared
    front = N("ShaderNodeMapRange")
    front.inputs["From Min"].default_value = 0.0
    front.inputs["From Max"].default_value = 0.07
    front.inputs["To Min"].default_value = 14.0
    front.inputs["To Max"].default_value = 0.0
    iris_glow = N("ShaderNodeMath")
    iris_glow.operation = "MULTIPLY_ADD"          # iris * 5 + front glow
    iris_glow.inputs[1].default_value = 5.0
    glow = N("ShaderNodeMath")
    glow.operation = "MULTIPLY"
    L(uv.outputs["UV"], mp.inputs["Vector"])
    L(mp.outputs["Vector"], ink.inputs["Vector"])
    L(mp.outputs["Vector"], dat.inputs["Vector"])
    L(dat.outputs["Color"], sep.inputs["Color"])
    L(sep.outputs["Red"], drawn.inputs[0])
    L(reveal.outputs[0], drawn.inputs[1])
    L(drawn.outputs[0], shown.inputs[0])
    L(ink.outputs["Alpha"], shown.inputs[1])
    L(shown.outputs[0], mix.inputs["Factor"])
    L(fur.outputs["Color"], mix.inputs[6])
    L(ink.outputs["Color"], mix.inputs[7])
    L(mix.outputs[2], bsdf.inputs["Base Color"])
    L(reveal.outputs[0], behind.inputs[0])
    L(sep.outputs["Red"], behind.inputs[1])
    L(behind.outputs[0], front.inputs["Value"])
    L(sep.outputs["Green"], iris_glow.inputs[0])
    L(front.outputs["Result"], iris_glow.inputs[2])
    L(iris_glow.outputs[0], glow.inputs[0])
    L(shown.outputs[0], glow.inputs[1])
    L(glow.outputs[0], bsdf.inputs["Emission Strength"])
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.05, 0.02, 1)
    ape.parts["SukunaReveal"] = reveal
    ape.parts["IrisGlow"] = ape.eye_mat.node_tree.nodes["IrisGlow"]


# ----------------------------------------------------------------- the cast

def build_cast(col):
    cast = {}
    for tag in ("Yuji", "Megumi", "Gojo", "Grandpa", "Sasaki", "Iguchi", "DogWhite", "DogBlack"):
        cast[tag] = make(tag, U.collection(tag, col))
    for tag in ("DogWhite", "DogBlack"):
        cast[tag].arm.scale = (DOG_SCALE,) * 3
    blindfold(cast["Gojo"])
    add_sukuna(cast["Yuji"])
    return cast
