"""
Fix the mesh problems that cause dark lines / dark patches in baked lightmaps
(Unity's lightmapper or Bakery).

HOW TO RUN
  1. Open XmasLAR.blend in Blender.
  2. Click the "Scripting" tab at the top of the window.
  3. In the text editor in the middle: Text > Open > pick this file.
  4. Click the Run Script button (the play icon). A big map can take a minute.
  5. The report shows up in the text editor when it's done. The fixed file is
     saved over XmasLAR.blend, and a backup of the original is saved next to it
     first (XmasLAR_before_lightmap_fix.blend).

THEN IN UNITY
  Click XmasLAR in the Project window -> Inspector -> Model tab ->
  untick "Generate Lightmap UVs" -> Apply -> bake your lighting again.
  That makes Unity use the clean lightmap UVs this script builds.

WHAT IT CHANGES, on every mesh in the scene
  - Mirror / Array / Solidify modifiers get applied. Their copies reuse the same
    UVs, so the copies fight over the same lightmap pixels.
  - Vertices sitting on top of each other get welded. Edges that were split for
    hard shading are marked sharp, so the shading looks the same as before.
  - Zero-area faces and exact duplicate faces get deleted.
  - Faces pointing the opposite way from the rest of their piece get flipped.
    Double-sided faces (two faces back to back) are left alone.
  - A clean lightmap UV map (the 2nd UV map) gets built with no overlaps and
    with padding between pieces. Your texture UVs (the 1st UV map) aren't touched.
"""

import bpy
import bmesh
import math
import os

WELD_DISTANCE = 0.0001    # vertices closer than this (metres) get merged
LIGHTMAP_MARGIN = 0.02    # gap between lightmap UV pieces, as a fraction of the UV square
LIGHTMAP_UV_NAME = "Lightmap"
REPORT_NAME = "Lightmap fix report"

# Modifiers whose copies reuse the same UVs, which makes lightmap UVs overlap.
OVERLAPPING_MODIFIERS = {"MIRROR", "ARRAY", "SOLIDIFY"}
# Modifiers that can also overlap but aren't safe to apply blindly; only reported.
WARN_MODIFIERS = {"NODES", "PARTICLE_INSTANCE"}

lines = []


def log(text=""):
    print(text)
    lines.append(text)


def count(n, word, plural=None):
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def unhide_all(view_layer, objects):
    """Make every collection and mesh visible and selectable so operators can run on them."""
    saved_cols = []

    def walk(layer_col):
        for child in layer_col.children:
            col = child.collection
            saved_cols.append((child, child.hide_viewport, col.hide_viewport, col.hide_select))
            child.hide_viewport = False
            col.hide_viewport = False
            col.hide_select = False
            walk(child)

    walk(view_layer.layer_collection)
    saved_objs = [(ob, ob.hide_get(), ob.hide_viewport, ob.hide_select) for ob in objects]
    for ob in objects:
        ob.hide_viewport = False
        ob.hide_select = False
        ob.hide_set(False)
    return saved_cols, saved_objs


def restore_visibility(saved):
    saved_cols, saved_objs = saved
    for ob, hidden, hide_viewport, hide_select in saved_objs:
        ob.hide_set(hidden)
        ob.hide_viewport = hide_viewport
        ob.hide_select = hide_select
    for layer_col, lc_hide, col_hide, col_select in reversed(saved_cols):
        layer_col.hide_viewport = lc_hide
        layer_col.collection.hide_viewport = col_hide
        layer_col.collection.hide_select = col_select


def make_active(view_layer, ob):
    for other in view_layer.objects.selected:
        other.select_set(False)
    ob.select_set(True)
    view_layer.objects.active = ob


def apply_overlapping_modifiers(ob):
    mods = list(ob.modifiers)
    for m in mods:
        if m.type in WARN_MODIFIERS:
            log(f"  {ob.name}: has a {m.type} modifier '{m.name}'. "
                f"If this object still gets dark lines, apply that modifier by hand.")
    last = max((i for i, m in enumerate(mods) if m.type in OVERLAPPING_MODIFIERS), default=-1)
    if last < 0:
        return
    # Apply everything up to the last overlapping modifier, in stack order, so the
    # result is exactly what Unity was already importing.
    to_apply = mods[: last + 1]
    if any(m.type == "ARMATURE" for m in to_apply):
        log(f"  {ob.name}: left its modifiers alone (there's an Armature in the stack)")
        return
    if ob.data.users - ob.data.use_fake_user > 1:
        ob.data = ob.data.copy()  # applying needs a mesh this object doesn't share
    with bpy.context.temp_override(object=ob, active_object=ob,
                                   selected_objects=[ob], selected_editable_objects=[ob]):
        for name, kind in [(m.name, m.type) for m in to_apply]:
            try:
                bpy.ops.object.modifier_apply(modifier=name)
            except RuntimeError as err:
                log(f"  {ob.name}: couldn't apply {kind} modifier '{name}': {err}")
                return
            log(f"  {ob.name}: applied {kind} modifier '{name}'")


def find_twin_faces(bm):
    """Faces at exactly the same spot: same-facing copies (they z-fight) and
    back-to-back pairs (a double-sided surface)."""
    bm.normal_update()
    by_position = {}
    duplicates = []
    double_sided = set()
    for f in bm.faces:
        key = frozenset((round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4)) for v in f.verts)
        twin = by_position.get(key)
        if twin is None:
            by_position[key] = f
        elif f.normal.dot(twin.normal) > 0:
            duplicates.append(f)
        else:
            double_sided.update((f, twin))
    return duplicates, double_sided


def delete_faces(bm, faces):
    if not faces:
        return
    orphans = {v for f in faces for v in f.verts}
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")
    orphans = [v for v in orphans if v.is_valid and not v.link_faces]
    if orphans:
        bmesh.ops.delete(bm, geom=orphans, context="VERTS")


def clean_mesh(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    stats = {}

    # 1. Exact duplicate faces.
    duplicates, _ = find_twin_faces(bm)
    delete_faces(bm, duplicates)
    stats["duplicates"] = len(duplicates)

    # 2. Weld vertices sitting on top of each other. Never weld the front and back
    #    of a double-sided surface together: their normals would cancel out and the
    #    surface would go black.
    bm.normal_update()
    targetmap = bmesh.ops.find_doubles(bm, verts=bm.verts[:], dist=WELD_DISTANCE)["targetmap"]
    targetmap = {v: t for v, t in targetmap.items() if v.normal.dot(t.normal) > -0.5}
    stats["welded"] = len(targetmap)
    if targetmap:
        def to(v):
            return targetmap.get(v, v)

        split_edges = set()
        for e in bm.edges:
            if e.is_boundary:
                a, b = to(e.verts[0]), to(e.verts[1])
                if a != b:
                    split_edges.add((a, b))
        bmesh.ops.weld_verts(bm, targetmap=targetmap)
        # An edge that was split before was a hard edge; keep it hard.
        for a, b in split_edges:
            if a.is_valid and b.is_valid:
                e = bm.edges.get((a, b))
                if e is not None and not e.is_boundary:
                    e.smooth = False

    # 3. Zero-area faces.
    before = len(bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=WELD_DISTANCE, edges=bm.edges[:])
    stats["degenerate"] = before - len(bm.faces)

    # Welding can turn near-copies into exact copies, so look again.
    duplicates, double_sided = find_twin_faces(bm)
    delete_faces(bm, duplicates)
    stats["duplicates"] += len(duplicates)
    stats["double_sided"] = len(double_sided) // 2

    # 4. Flip faces that point the opposite way from the rest of their piece. The
    #    piece keeps whichever way most of its faces already point, so an inside-out
    #    room stays inside-out.
    bm.normal_update()
    original = {f: f.normal.copy() for f in bm.faces}
    visited = set(double_sided)
    flipped = 0
    for start in bm.faces:
        if start in visited:
            continue
        island = [start]
        visited.add(start)
        i = 0
        while i < len(island):
            for e in island[i].edges:
                for g in e.link_faces:
                    if g not in visited:
                        visited.add(g)
                        island.append(g)
            i += 1
        bmesh.ops.recalc_face_normals(bm, faces=island)
        for f in island:
            f.normal_update()
        changed = sum(1 for f in island if f.normal.dot(original[f]) < 0)
        if changed * 2 > len(island):
            bmesh.ops.reverse_faces(bm, faces=island)
            flipped += len(island) - changed
        else:
            flipped += changed
    stats["flipped"] = flipped

    bm.to_mesh(me)
    bm.free()
    me.update()
    return stats


def uv_used_by_materials(ob, name):
    for slot in ob.material_slots:
        mat = slot.material
        if mat is None or mat.node_tree is None:
            continue
        for node in mat.node_tree.nodes:
            if getattr(node, "uv_map", None) == name:
                return True
            if node.type == "ATTRIBUTE" and node.attribute_name == name:
                return True
    return False


def build_lightmap_uvs(view_layer, ob):
    """Unity reads the 2nd UV map as lightmap UVs, so that's where these go."""
    me = ob.data
    uvs = me.uv_layers
    if len(uvs) == 0:
        uvs.new(name="UVMap")
    if len(uvs) == 1:
        layer = uvs.new(name=LIGHTMAP_UV_NAME)
    else:
        layer = uvs[1]
        if uv_used_by_materials(ob, layer.name):
            # A material samples this map: keep its data under its name in a new
            # slot, and turn the 2nd slot into the lightmap map.
            data = [0.0] * (len(me.loops) * 2)
            layer.data.foreach_get("uv", data)
            old_name = layer.name
            layer.name = LIGHTMAP_UV_NAME
            uvs.new(name=old_name).data.foreach_set("uv", data)
            layer = uvs[1]
            log(f"  {ob.name}: moved UV map '{old_name}' (used by a material) "
                f"to slot {len(uvs)} to make room for the lightmap UVs")
    uvs.active = layer

    make_active(view_layer, ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.reveal(select=False)
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=LIGHTMAP_MARGIN,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    try:
        bpy.ops.uv.pack_islands(rotate=True, margin=LIGHTMAP_MARGIN,
                                margin_method="FRACTION", shape_method="AABB")
    except TypeError:  # older Blender without those options
        bpy.ops.uv.pack_islands(rotate=True, margin=LIGHTMAP_MARGIN)
    bpy.ops.object.mode_set(mode="OBJECT")

    uvs.active = uvs[0]
    uvs[0].active_render = True


def main():
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    active = view_layer.objects.active
    if active is not None and active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    path = bpy.data.filepath
    if path:
        # Number the backups so running this twice never overwrites the original.
        root, ext = os.path.splitext(path)
        backup = root + "_before_lightmap_fix" + ext
        n = 2
        while os.path.exists(backup):
            backup = f"{root}_before_lightmap_fix_{n}{ext}"
            n += 1
        bpy.ops.wm.save_as_mainfile(filepath=backup, copy=True)
        log(f"Backup of the original: {backup}")
    else:
        log("This file has never been saved, so no backup was made.")

    objects = []
    for ob in scene.objects:
        if ob.type != "MESH":
            continue
        if ob.library or ob.data.library:
            log(f"  skipped {ob.name}: it's linked from another .blend file")
            continue
        if view_layer.objects.get(ob.name) is None:
            log(f"  skipped {ob.name}: its collection is unchecked (excluded) in the outliner")
            continue
        objects.append(ob)

    selected = list(view_layer.objects.selected)
    saved = unhide_all(view_layer, objects)
    totals = dict(welded=0, degenerate=0, duplicates=0, double_sided=0, flipped=0)
    unwrapped = 0
    try:
        log("")
        log("Modifiers")
        for ob in objects:
            apply_overlapping_modifiers(ob)

        log("")
        log("Mesh cleanup")
        done = set()
        for ob in objects:
            me = ob.data
            if me.as_pointer() in done or len(me.polygons) == 0:
                continue
            done.add(me.as_pointer())
            stats = clean_mesh(me)
            for k, v in stats.items():
                totals[k] += v
            parts = []
            if stats["welded"]:
                parts.append(f"welded {count(stats['welded'], 'vertex', 'vertices')}")
            if stats["degenerate"]:
                parts.append(f"removed {count(stats['degenerate'], 'zero-area face')}")
            if stats["duplicates"]:
                parts.append(f"removed {count(stats['duplicates'], 'duplicate face')}")
            if stats["flipped"]:
                parts.append(f"flipped {count(stats['flipped'], 'backwards face')}")
            if stats["double_sided"]:
                parts.append(f"kept {count(stats['double_sided'], 'double-sided face')} as is")
            if parts:
                log(f"  {ob.name}: " + ", ".join(parts))

        log("")
        log("Lightmap UVs")
        done = set()
        for ob in objects:
            me = ob.data
            if me.as_pointer() in done or len(me.polygons) == 0:
                continue
            done.add(me.as_pointer())
            build_lightmap_uvs(view_layer, ob)
            unwrapped += 1
        log(f"  built clean lightmap UVs for {unwrapped} meshes")
    finally:
        active_now = view_layer.objects.active
        if active_now is not None and active_now.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        restore_visibility(saved)
        for ob in view_layer.objects.selected:
            ob.select_set(False)
        for ob in selected:
            if ob.name in view_layer.objects:
                ob.select_set(True)
        if active is not None and active.name in view_layer.objects:
            view_layer.objects.active = active

    log("")
    log("Totals")
    log(f"  vertices welded:          {totals['welded']}")
    log(f"  zero-area faces removed:  {totals['degenerate']}")
    log(f"  duplicate faces removed:  {totals['duplicates']}")
    log(f"  backwards faces flipped:  {totals['flipped']}")
    log(f"  meshes with new lightmap UVs: {unwrapped}")
    log("")
    log("Next, in Unity: click XmasLAR in the Project window -> Inspector -> Model tab ->")
    log("untick 'Generate Lightmap UVs' -> Apply -> bake your lighting again.")
    if path:
        log("")
        log(f"Saved: {path}")

    text = bpy.data.texts.get(REPORT_NAME) or bpy.data.texts.new(REPORT_NAME)
    text.clear()
    text.write("\n".join(lines) + "\n")
    if path:
        bpy.ops.wm.save_mainfile()
    space = getattr(bpy.context, "space_data", None)
    if space is not None and space.type == "TEXT_EDITOR":
        space.text = text


main()
