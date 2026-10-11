"""Render settings and the compositor (bloom, vignette) shared by every scene."""

import bpy


def compositor(scene, bloom=0.9, threshold=1.0, vignette=0.35):
    if not hasattr(scene, "compositing_node_group"):          # Blender 4.x: the scene's own node tree
        return _compositor_4x(scene, bloom, threshold, vignette)
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
        engines = {e.identifier for e in r.bl_rna.properties["engine"].enum_items}
        r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"   # 4.2-4.5 vs 5.x
        ee = scene.eevee
        for attr, val in (("taa_render_samples", samples or 64), ("use_raytracing", True),
                          ("use_shadows", True), ("shadow_ray_count", 2), ("shadow_step_count", 8),
                          ("use_fast_gi", True), ("fast_gi_method", "GLOBAL_ILLUMINATION"),
                          ("volumetric_tile_size", "4"), ("volumetric_samples", 96), ("use_volume_custom_range", True),
                          ("volumetric_start", 0.1), ("volumetric_end", 120.0),
                          ("use_volumetric_shadows", True), ("volumetric_shadow_samples", 32)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except (TypeError, ValueError):
                    pass


def _compositor_4x(scene, bloom, threshold, vignette):
    scene.use_nodes = True
    nt = scene.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    rl = N("CompositorNodeRLayers")
    rl.scene = scene
    glare = N("CompositorNodeGlare")
    glare.glare_type = "BLOOM"
    for name, val in (("Threshold", threshold), ("Strength", bloom), ("Size", 0.7)):
        if name in glare.inputs:
            glare.inputs[name].default_value = val
    mask = N("CompositorNodeEllipseMask")
    if "Size" in mask.inputs:
        mask.inputs["Size"].default_value = (1.2, 1.05)
    else:
        mask.mask_width, mask.mask_height = 1.2, 1.05
    blur = N("CompositorNodeBlur")
    blur.filter_type = "GAUSS"
    blur.size_x = blur.size_y = 220
    amount = N("CompositorNodeMapRange")
    amount.inputs["To Min"].default_value = 1.0 - vignette
    amount.inputs["To Max"].default_value = 1.0
    mul = N("CompositorNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 1.0
    comp = N("CompositorNodeComposite")
    L(rl.outputs["Image"], glare.inputs["Image"])
    L(mask.outputs["Mask"], blur.inputs["Image"])
    L(blur.outputs["Image"], amount.inputs["Value"])
    L(glare.outputs["Image"], mul.inputs[1])
    L(amount.outputs["Value"], mul.inputs[2])
    L(mul.outputs["Image"], comp.inputs["Image"])
    scene.render.use_compositing = True
    return nt


def viewport_camera(clip_end=5000.0):
    """Every 3D view of the saved file looks through the scene camera with textures showing
    (Solid mode), so the file opens on the shot instead of an empty-looking default view."""
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces.active
                sp.region_3d.view_perspective = "CAMERA"
                sp.shading.color_type = "TEXTURE"
                sp.clip_end = clip_end
