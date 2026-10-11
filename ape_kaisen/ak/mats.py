"""Procedural materials for the sets (no image files needed; all work in Cycles and EEVEE)."""

import bpy

from . import util as U

_cache = {}


class G:
    """Tiny node-graph helper: g.n(type, **inputs) / g.l(out, in)."""

    def __init__(self, nt):
        self.nt = nt

    def n(self, kind, props=None, **inputs):
        node = self.nt.nodes.new(kind)
        for k, v in (props or {}).items():
            setattr(node, k, v)
        for k, v in inputs.items():
            node.inputs[k.replace("_", " ")].default_value = v
        return node

    def l(self, out, inp):
        self.nt.links.new(out, inp)


def cached(fn):
    def wrap(name, *a, **k):
        if name not in _cache:
            _cache[name] = fn(name, *a, **k)
        return _cache[name]
    return wrap


def _bsdf(g, out, color=None, rough=0.6, metal=0.0, spec=0.5):
    b = g.n("ShaderNodeBsdfPrincipled", Roughness=rough, Metallic=metal)
    b.inputs["Specular IOR Level"].default_value = spec
    if color is not None:
        b.inputs["Base Color"].default_value = (*color, 1)
    g.l(b.outputs[0], out.inputs[0])
    return b


def _ramp(g, stops):
    r = g.n("ShaderNodeValToRGB")
    cr = r.color_ramp
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, col in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    return r


@cached
def concrete(name, base=(0.62, 0.6, 0.55), dark=(0.38, 0.36, 0.33), scale=1.0, streaks=0.6, rough=0.88):
    """Painted concrete with blotchy variation, rain streaks running down, and fine bump."""
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    blotch = g.n("ShaderNodeTexNoise", Scale=1.2 * scale, Detail=6.0, Roughness=0.6)
    g.l(tc.outputs["Object"], blotch.inputs["Vector"])
    stretch = g.n("ShaderNodeMapping", Scale=(3.0 * scale, 3.0 * scale, 0.25 * scale))
    g.l(tc.outputs["Object"], stretch.inputs["Vector"])
    streak = g.n("ShaderNodeTexNoise", Scale=2.5, Detail=4.0)
    g.l(stretch.outputs[0], streak.inputs["Vector"])
    mixf = g.n("ShaderNodeMath", {"operation": "MULTIPLY_ADD"})
    g.l(streak.outputs["Fac"], mixf.inputs[0])
    mixf.inputs[1].default_value = streaks
    g.l(blotch.outputs["Fac"], mixf.inputs[2])
    ramp = _ramp(g, [(0.45, dark), (0.75, base), (1.0, tuple(min(1, c * 1.06) for c in base))])
    g.l(mixf.outputs[0], ramp.inputs["Fac"])
    b = _bsdf(g, out, rough=rough)
    g.l(ramp.outputs["Color"], b.inputs["Base Color"])
    fine = g.n("ShaderNodeTexNoise", Scale=40.0 * scale, Detail=8.0)
    g.l(tc.outputs["Object"], fine.inputs["Vector"])
    bump = g.n("ShaderNodeBump", Strength=0.12, Distance=0.02)
    g.l(fine.outputs["Fac"], bump.inputs["Height"])
    g.l(bump.outputs["Normal"], b.inputs["Normal"])
    mat.diffuse_color = (*base, 1)
    return mat


@cached
def tiles(name, a=(0.55, 0.6, 0.55), b=(0.5, 0.55, 0.5), mortar=(0.3, 0.32, 0.3), size=0.6, rough=0.25, bump=0.3):
    """Floor tiles (glossy linoleum / stone) using object-space XY."""
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    brick = g.n("ShaderNodeTexBrick", {"offset": 0.0, "squash": 1.0},
                Scale=1.0 / size, Mortar_Size=0.012, Bias=0.0, Brick_Width=1.0, Row_Height=1.0)
    brick.inputs["Color1"].default_value = (*a, 1)
    brick.inputs["Color2"].default_value = (*b, 1)
    brick.inputs["Mortar"].default_value = (*mortar, 1)
    g.l(tc.outputs["Object"], brick.inputs["Vector"])
    dirt = g.n("ShaderNodeTexNoise", Scale=0.8, Detail=5.0)
    g.l(tc.outputs["Object"], dirt.inputs["Vector"])
    shade = g.n("ShaderNodeMix", {"data_type": "RGBA", "blend_type": "MULTIPLY"}, Factor=0.35)
    g.l(brick.outputs["Color"], shade.inputs[6])
    g.l(dirt.outputs["Color"], shade.inputs[7])
    bs = _bsdf(g, out, rough=rough)
    g.l(shade.outputs[2], bs.inputs["Base Color"])
    rr = g.n("ShaderNodeMapRange", To_Min=rough, To_Max=rough + 0.3)
    g.l(dirt.outputs["Fac"], rr.inputs["Value"])
    g.l(rr.outputs["Result"], bs.inputs["Roughness"])
    bm = g.n("ShaderNodeBump", Strength=bump, Distance=0.01, props={"invert": True})
    g.l(brick.outputs["Fac"], bm.inputs["Height"])
    g.l(bm.outputs["Normal"], bs.inputs["Normal"])
    mat.diffuse_color = (*a, 1)
    return mat


@cached
def metal(name, color=(0.6, 0.62, 0.65), rough=0.4, metallic=1.0):
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    nz = g.n("ShaderNodeTexNoise", Scale=6.0, Detail=6.0)
    g.l(tc.outputs["Object"], nz.inputs["Vector"])
    rr = g.n("ShaderNodeMapRange", To_Min=rough * 0.8, To_Max=rough * 1.3)
    g.l(nz.outputs["Fac"], rr.inputs["Value"])
    b = _bsdf(g, out, color=color, metal=metallic)
    g.l(rr.outputs["Result"], b.inputs["Roughness"])
    mat.diffuse_color = (*color, 1)
    return mat


@cached
def paint(name, color, rough=0.5, metallic=0.0):
    mat, nt, out = U.new_material(name)
    g = G(nt)
    _bsdf(g, out, color=color, rough=rough, metal=metallic)
    mat.diffuse_color = (*color, 1)
    return mat


@cached
def wood(name, light=(0.55, 0.36, 0.2), dark=(0.33, 0.2, 0.1), scale=3.0, rough=0.5):
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    mp = g.n("ShaderNodeMapping", Scale=(1.0, 8.0, 1.0))
    g.l(tc.outputs["Object"], mp.inputs["Vector"])
    wave = g.n("ShaderNodeTexWave", {"wave_type": "BANDS", "bands_direction": "X"},
               Scale=scale, Distortion=6.0, Detail=3.0)
    g.l(mp.outputs[0], wave.inputs["Vector"])
    ramp = _ramp(g, [(0.0, dark), (1.0, light)])
    g.l(wave.outputs["Fac"], ramp.inputs["Fac"])
    b = _bsdf(g, out, rough=rough)
    g.l(ramp.outputs["Color"], b.inputs["Base Color"])
    mat.diffuse_color = (*light, 1)
    return mat


@cached
def glass(name, tint=(0.8, 0.9, 0.95), reflect=0.12, rough=0.03):
    """Thin window glass: mostly see-through (lets sun/moonlight in), with a reflection layer."""
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tr = g.n("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (*tint, 1)
    gl = g.n("ShaderNodeBsdfGlossy", Roughness=rough)
    fres = g.n("ShaderNodeLayerWeight", Blend=0.3)
    fac = g.n("ShaderNodeMath", {"operation": "MULTIPLY_ADD"})
    g.l(fres.outputs["Fresnel"], fac.inputs[0])
    fac.inputs[1].default_value = 0.6
    fac.inputs[2].default_value = reflect
    mix = g.n("ShaderNodeMixShader")
    g.l(fac.outputs[0], mix.inputs["Fac"])
    g.l(tr.outputs[0], mix.inputs[1])
    g.l(gl.outputs[0], mix.inputs[2])
    g.l(mix.outputs[0], out.inputs[0])
    _transparent_settings(mat)
    mat.diffuse_color = (*tint, 0.3)
    return mat


@cached
def dark_glass(name, color=(0.012, 0.015, 0.02), rough=0.14):
    """Opaque glass for windows we never look through (soft reflections so the city doesn't
    mirror in every pane)."""
    mat, nt, out = U.new_material(name)
    g = G(nt)
    _bsdf(g, out, color=color, rough=rough, spec=0.35)
    return mat


def _transparent_settings(mat):
    for attr, val in (("surface_render_method", "DITHERED"), ("use_transparent_shadow", True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val)


@cached
def fake_interior(name, dark=(0.012, 0.012, 0.016), lit=(1.0, 0.82, 0.55), lit_fraction=0.08, cell=(4.0, 12.0, 3.6),
                  strength=2.5):
    """Dark rooms behind windows; a random few per building are lit (one value per window bay)."""
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    cellm = g.n("ShaderNodeMapping", Scale=(1 / cell[0], 1 / cell[1], 1 / cell[2]))
    g.l(tc.outputs["Object"], cellm.inputs["Vector"])
    fl = g.n("ShaderNodeVectorMath", {"operation": "FLOOR"})
    g.l(cellm.outputs[0], fl.inputs[0])
    wn = g.n("ShaderNodeTexWhiteNoise", {"noise_dimensions": "3D"})
    g.l(fl.outputs[0], wn.inputs["Vector"])
    gt = g.n("ShaderNodeMath", {"operation": "GREATER_THAN"})
    g.l(wn.outputs["Value"], gt.inputs[0])
    gt.inputs[1].default_value = 1 - lit_fraction
    em = g.n("ShaderNodeEmission", Strength=strength)
    em.inputs["Color"].default_value = (*lit, 1)
    d = g.n("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (*dark, 1)
    mix = g.n("ShaderNodeMixShader")
    g.l(gt.outputs[0], mix.inputs["Fac"])
    g.l(d.outputs[0], mix.inputs[1])
    g.l(em.outputs[0], mix.inputs[2])
    g.l(mix.outputs[0], out.inputs[0])
    return mat


@cached
def chainlink(name, color=(0.12, 0.3, 0.16), cell=0.06, wire=0.12):
    """Green chain-link fence: diamond wire pattern cut out with transparency."""
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    sep = g.n("ShaderNodeSeparateXYZ")
    g.l(tc.outputs["Object"], sep.inputs[0])
    # diagonal coordinates along the fence plane: use (x + y) as "along" so it works for both fence directions
    along = g.n("ShaderNodeMath", {"operation": "ADD"})
    g.l(sep.outputs["X"], along.inputs[0])
    g.l(sep.outputs["Y"], along.inputs[1])
    masks = []
    for sign in (1, -1):
        d = g.n("ShaderNodeMath", {"operation": "MULTIPLY_ADD"})
        g.l(sep.outputs["Z"], d.inputs[0])
        d.inputs[1].default_value = sign
        g.l(along.outputs[0], d.inputs[2])
        sc = g.n("ShaderNodeMath", {"operation": "DIVIDE"})
        g.l(d.outputs[0], sc.inputs[0])
        sc.inputs[1].default_value = cell
        fr = g.n("ShaderNodeMath", {"operation": "PINGPONG"})
        g.l(sc.outputs[0], fr.inputs[0])
        fr.inputs[1].default_value = 0.5
        lt = g.n("ShaderNodeMath", {"operation": "LESS_THAN"})
        g.l(fr.outputs[0], lt.inputs[0])
        lt.inputs[1].default_value = wire * 0.5
        masks.append(lt)
    mx = g.n("ShaderNodeMath", {"operation": "MAXIMUM"})
    g.l(masks[0].outputs[0], mx.inputs[0])
    g.l(masks[1].outputs[0], mx.inputs[1])
    b = g.n("ShaderNodeBsdfPrincipled", Roughness=0.45, Metallic=0.3)
    b.inputs["Base Color"].default_value = (*color, 1)
    tr = g.n("ShaderNodeBsdfTransparent")
    mix = g.n("ShaderNodeMixShader")
    g.l(mx.outputs[0], mix.inputs["Fac"])
    g.l(tr.outputs[0], mix.inputs[1])
    g.l(b.outputs[0], mix.inputs[2])
    g.l(mix.outputs[0], out.inputs[0])
    _transparent_settings(mat)
    mat.diffuse_color = (*color, 1)
    return mat


@cached
def ground(name, a=(0.36, 0.3, 0.22), b=(0.25, 0.21, 0.16), scale=0.15, rough=0.95):
    """Packed dirt / gravel ground."""
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    big = g.n("ShaderNodeTexNoise", Scale=scale, Detail=8.0, Roughness=0.65)
    g.l(tc.outputs["Object"], big.inputs["Vector"])
    ramp = _ramp(g, [(0.35, b), (0.65, a)])
    g.l(big.outputs["Fac"], ramp.inputs["Fac"])
    grit = g.n("ShaderNodeTexVoronoi", Scale=scale * 300)
    g.l(tc.outputs["Object"], grit.inputs["Vector"])
    shade = g.n("ShaderNodeMix", {"data_type": "RGBA", "blend_type": "MULTIPLY"}, Factor=0.25)
    g.l(ramp.outputs["Color"], shade.inputs[6])
    g.l(grit.outputs["Color"], shade.inputs[7])
    bs = _bsdf(g, out, rough=rough)
    g.l(shade.outputs[2], bs.inputs["Base Color"])
    bm = g.n("ShaderNodeBump", Strength=0.35, Distance=0.02)
    g.l(grit.outputs["Distance"], bm.inputs["Height"])
    g.l(bm.outputs["Normal"], bs.inputs["Normal"])
    mat.diffuse_color = (*a, 1)
    return mat


@cached
def asphalt(name, color=(0.06, 0.06, 0.065), rough=0.75):
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    nz = g.n("ShaderNodeTexNoise", Scale=0.3, Detail=6.0)
    g.l(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = _ramp(g, [(0.3, tuple(c * 0.7 for c in color)), (0.7, tuple(c * 1.4 for c in color))])
    g.l(nz.outputs["Fac"], ramp.inputs["Fac"])
    grit = g.n("ShaderNodeTexVoronoi", Scale=120.0)
    g.l(tc.outputs["Object"], grit.inputs["Vector"])
    bs = _bsdf(g, out, rough=rough)
    g.l(ramp.outputs["Color"], bs.inputs["Base Color"])
    rr = g.n("ShaderNodeMapRange", To_Min=rough - 0.35, To_Max=rough)
    g.l(nz.outputs["Fac"], rr.inputs["Value"])
    g.l(rr.outputs["Result"], bs.inputs["Roughness"])
    bm = g.n("ShaderNodeBump", Strength=0.25, Distance=0.01)
    g.l(grit.outputs["Distance"], bm.inputs["Height"])
    g.l(bm.outputs["Normal"], bs.inputs["Normal"])
    return mat


@cached
def foliage(name, a=(0.05, 0.13, 0.05), b=(0.12, 0.24, 0.07)):
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    nz = g.n("ShaderNodeTexNoise", Scale=3.0, Detail=4.0)
    g.l(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = _ramp(g, [(0.35, a), (0.7, b)])
    g.l(nz.outputs["Fac"], ramp.inputs["Fac"])
    bs = _bsdf(g, out, rough=0.7)
    g.l(ramp.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Subsurface Weight"].default_value = 0.0
    vor = g.n("ShaderNodeTexVoronoi", Scale=14.0)
    g.l(tc.outputs["Object"], vor.inputs["Vector"])
    bm = g.n("ShaderNodeBump", Strength=0.6, Distance=0.05)
    g.l(vor.outputs["Distance"], bm.inputs["Height"])
    g.l(bm.outputs["Normal"], bs.inputs["Normal"])
    mat.diffuse_color = (*b, 1)
    return mat


@cached
def city_windows(name, wall=(0.03, 0.032, 0.04), lit=(1.0, 0.72, 0.45), frac=0.22, strength=1.4):
    """Distant buildings: grid of windows, a random share lit."""
    mat, nt, out = U.new_material(name)
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    sep = g.n("ShaderNodeSeparateXYZ")
    g.l(tc.outputs["Object"], sep.inputs[0])
    along = g.n("ShaderNodeMath", {"operation": "ADD"})
    g.l(sep.outputs["X"], along.inputs[0])
    g.l(sep.outputs["Y"], along.inputs[1])
    comb = g.n("ShaderNodeCombineXYZ")
    sx = g.n("ShaderNodeMath", {"operation": "DIVIDE"})
    g.l(along.outputs[0], sx.inputs[0])
    sx.inputs[1].default_value = 3.0
    sz = g.n("ShaderNodeMath", {"operation": "DIVIDE"})
    g.l(sep.outputs["Z"], sz.inputs[0])
    sz.inputs[1].default_value = 3.2
    g.l(sx.outputs[0], comb.inputs["X"])
    g.l(sz.outputs[0], comb.inputs["Y"])
    obj_rand = g.n("ShaderNodeObjectInfo")
    g.l(obj_rand.outputs["Random"], comb.inputs["Z"])
    cellf = g.n("ShaderNodeVectorMath", {"operation": "FLOOR"})
    g.l(comb.outputs[0], cellf.inputs[0])
    frac_v = g.n("ShaderNodeVectorMath", {"operation": "FRACTION"})
    g.l(comb.outputs[0], frac_v.inputs[0])
    wn = g.n("ShaderNodeTexWhiteNoise", {"noise_dimensions": "3D"})
    g.l(cellf.outputs[0], wn.inputs["Vector"])
    lit_cell = g.n("ShaderNodeMath", {"operation": "GREATER_THAN"})
    g.l(wn.outputs["Value"], lit_cell.inputs[0])
    lit_cell.inputs[1].default_value = 1 - frac
    sepf = g.n("ShaderNodeSeparateXYZ")
    g.l(frac_v.outputs[0], sepf.inputs[0])
    inx = g.n("ShaderNodeMath", {"operation": "COMPARE"})
    g.l(sepf.outputs["X"], inx.inputs[0])
    inx.inputs[1].default_value = 0.5
    inx.inputs[2].default_value = 0.32
    iny = g.n("ShaderNodeMath", {"operation": "COMPARE"})
    g.l(sepf.outputs["Y"], iny.inputs[0])
    iny.inputs[1].default_value = 0.5
    iny.inputs[2].default_value = 0.28
    win = g.n("ShaderNodeMath", {"operation": "MULTIPLY"})
    g.l(inx.outputs[0], win.inputs[0])
    g.l(iny.outputs[0], win.inputs[1])
    on = g.n("ShaderNodeMath", {"operation": "MULTIPLY"})
    g.l(win.outputs[0], on.inputs[0])
    g.l(lit_cell.outputs[0], on.inputs[1])
    tint = g.n("ShaderNodeMix", {"data_type": "RGBA"})
    g.l(wn.outputs["Color"], tint.inputs["Factor"])
    tint.inputs[6].default_value = (*lit, 1)
    tint.inputs[7].default_value = (0.75, 0.85, 1.0, 1)
    em = g.n("ShaderNodeEmission", Strength=strength)
    g.l(tint.outputs[2], em.inputs["Color"])
    d = g.n("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (*wall, 1)
    mix = g.n("ShaderNodeMixShader")
    g.l(on.outputs[0], mix.inputs["Fac"])
    g.l(d.outputs[0], mix.inputs[1])
    g.l(em.outputs[0], mix.inputs[2])
    g.l(mix.outputs[0], out.inputs[0])
    return mat


@cached
def glow(name, color, strength=5.0):
    return U.emission(name, color, strength)


def night_sky(world, zenith=(0.005, 0.008, 0.022), horizon=(0.035, 0.05, 0.09), stars=1.0, strength=1.6,
              glow_color=(0.06, 0.05, 0.07)):
    """Gradient night sky with a horizon glow (city light) and stars."""
    if world.node_tree is None:
        world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    g = G(nt)
    out = g.n("ShaderNodeOutputWorld")
    tc = g.n("ShaderNodeTexCoord")
    sep = g.n("ShaderNodeSeparateXYZ")
    g.l(tc.outputs["Generated"], sep.inputs[0])
    up = g.n("ShaderNodeMapRange", From_Min=0.0, From_Max=0.55)
    g.l(sep.outputs["Z"], up.inputs["Value"])
    ramp = _ramp(g, [(0.0, glow_color), (0.12, horizon), (1.0, zenith)])
    g.l(up.outputs["Result"], ramp.inputs["Fac"])
    vor = g.n("ShaderNodeTexVoronoi", {"feature": "F1"}, Scale=420.0, Randomness=1.0)
    g.l(tc.outputs["Generated"], vor.inputs["Vector"])
    star = g.n("ShaderNodeMapRange", From_Min=0.0, From_Max=0.045, To_Min=1.0, To_Max=0.0)
    g.l(vor.outputs["Distance"], star.inputs["Value"])
    bright = g.n("ShaderNodeMath", {"operation": "POWER"})
    g.l(star.outputs["Result"], bright.inputs[0])
    bright.inputs[1].default_value = 6.0
    twinkle = g.n("ShaderNodeMath", {"operation": "MULTIPLY"})
    g.l(bright.outputs[0], twinkle.inputs[0])
    g.l(vor.outputs["Color"], twinkle.inputs[1])
    high = g.n("ShaderNodeMath", {"operation": "MULTIPLY"})
    g.l(twinkle.outputs[0], high.inputs[0])
    g.l(up.outputs["Result"], high.inputs[1])
    amount = g.n("ShaderNodeMath", {"operation": "MULTIPLY"})
    g.l(high.outputs[0], amount.inputs[0])
    amount.inputs[1].default_value = 0.6 * stars
    add = g.n("ShaderNodeMix", {"data_type": "RGBA", "blend_type": "ADD"}, Factor=1.0)
    g.l(ramp.outputs["Color"], add.inputs[6])
    g.l(amount.outputs[0], add.inputs[7])
    bg = g.n("ShaderNodeBackground", Strength=strength)
    g.l(add.outputs[2], bg.inputs["Color"])
    g.l(bg.outputs[0], out.inputs["Surface"])
    return world
