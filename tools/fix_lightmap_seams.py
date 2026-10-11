"""Fix dark lines/seams in Unity baked lighting for a .blend map.

Usage (back up the .blend first):
    blender -b Assets/Resources/Models/Maps/XmasLAR.blend --python tools/fix_lightmap_seams.py

What it does to every mesh object:
  1. Merges duplicate vertices and removes degenerate/loose geometry.
  2. Recalculates normals so they all face outward (flipped faces bake black).
  3. Builds a clean, non-overlapping second UV channel ("Lightmap") with
     margins between islands. Unity reads the 2nd UV channel as UV2 (lightmap UVs).
Then saves the .blend in place.
"""
import math

import bmesh
import bpy

MERGE_DISTANCE = 0.0001
ISLAND_MARGIN = 0.02
LIGHTMAP_UV_NAME = "Lightmap"


def clean_mesh(obj):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DISTANCE)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=MERGE_DISTANCE)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def build_lightmap_uvs(obj):
    me = obj.data
    if len(me.uv_layers) == 0:
        me.uv_layers.new(name="UVMap")
    if len(me.uv_layers) < 2:
        me.uv_layers.new(name=LIGHTMAP_UV_NAME)
    lm = me.uv_layers[1]
    me.uv_layers.active = lm

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(66),
        island_margin=ISLAND_MARGIN,
        area_weight=0.0,
        correct_aspect=True,
        scale_to_bounds=False,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

    # Keep the texture UVs as the render/active channel.
    me.uv_layers.active = me.uv_layers[0]
    me.uv_layers[0].active_render = True


def main():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    done = set()
    for obj in meshes:
        if obj.data in done:
            continue  # shared mesh data, already processed
        done.add(obj.data)
        clean_mesh(obj)
        build_lightmap_uvs(obj)
        print(f"fixed: {obj.name}")

    bpy.ops.wm.save_mainfile()
    print(f"Done. Processed {len(done)} mesh(es).")


main()
