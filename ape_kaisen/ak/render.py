"""Render settings and the compositor (bloom, vignette) shared by every scene."""

import bpy


def compositor(scene, bloom=0.9, threshold=1.0, vignette=0.35):
    ng = bpy.data.node_groups.new(f"{scene.name}_Comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = ng.nodes.new, ng.links.new
    rl = N("CompositorNodeRLayers")
    rl.scene = scene
    glare = N("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Threshold"].default_value = threshold
    glare.inputs["Strength"].default_value = bloom
    glare.inputs["Size"].default_value = 0.7
    mask = N("CompositorNodeEllipseMask")
    mask.inputs["Size"].default_value = (1.2, 1.05)
    blur = N("CompositorNodeBlur")
    for name, val in (("Size", (220, 220)), ("Type", "Gaussian")):
        try:
            blur.inputs[name].default_value = val
        except (KeyError, TypeError):
            pass
    amount = N("ShaderNodeMapRange")
    amount.inputs["To Min"].default_value = 1.0 - vignette
    amount.inputs["To Max"].default_value = 1.0
    mul = N("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    out = N("NodeGroupOutput")
    L(rl.outputs["Image"], glare.inputs["Image"])
    L(mask.outputs["Mask"], blur.inputs["Image"])
    L(blur.outputs["Image"], amount.inputs["Value"])
    L(glare.outputs["Image"], mul.inputs[6])
    L(amount.outputs["Result"], mul.inputs[7])
    L(mul.outputs[2], out.inputs[0])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True
    return ng


def setup(scene, preview=True, res=(1920, 1080), samples=None):
    """preview=True: fast Cycles for checking here. False: the settings saved for the user (EEVEE)."""
    r = scene.render
    r.resolution_x, r.resolution_y = res
    r.fps = 24
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    if preview:
        r.engine = "CYCLES"
        scene.cycles.samples = samples or 16
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.transparent_max_bounces = 12
    else:
        r.engine = "BLENDER_EEVEE"
        ee = scene.eevee
        for attr, val in (("taa_render_samples", samples or 64), ("use_raytracing", True),
                          ("use_shadows", True), ("shadow_ray_count", 2), ("shadow_step_count", 8),
                          ("use_fast_gi", True), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except (TypeError, ValueError):
                    pass
