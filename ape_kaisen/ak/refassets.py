"""The user's own game assets (bench, candle, fall trees, hay bale) brought into the sets and
re-textured with the kit painters (their original texture files were not part of the upload;
the meshes are used as they are, only scaled from game units to metres)."""

import math
import os

import bpy
from mathutils import Matrix, Vector

from . import kit as K
from .kit import Surf

REF_DIR = os.path.join(K.ROOT, "assets", "ref")

BENCH_WOOD = Surf("wood", "#B98A5A", "#7A5634", rough=0.6, grime=0.3, name="BenchWood")
BENCH_METAL = Surf("paint", "#3B4A40", "#5A3A26", rough=0.45, metal=0.5, chips=0.5, grime=0.3, name="BenchMetal")
WAX = Surf("wax", "#F1E8D2", "#CDB58A", rough=0.45, sss=0.35, edge=0.1, ao=0.5, name="Wax")
WICK = Surf("paint", "#1C1712", "#0A0806", rough=0.8, edge=0.0, name="Wick")
BARK = Surf("bark", "#6B4A33", "#2E1E14", rough=0.85, edge=0.1, ao=0.6, name="Bark")
HAY = Surf("hay", "#E2C46E", "#9C7A34", rough=0.85, edge=0.15, ao=0.55, name="Hay")
LEAVES = {
    "red": Surf("leaf", "#F08A3C", "#8E2A16", rough=0.7, edge=0.0, ao=0.55, var=0.12, sss=0.15, name="LeavesRed"),
    "gold": Surf("leaf", "#F4C24A", "#A2561A", rough=0.7, edge=0.0, ao=0.55, var=0.12, sss=0.15, name="LeavesGold"),
    "green": Surf("leaf", "#86B04A", "#2C4D1E", rough=0.7, edge=0.0, ao=0.55, var=0.12, sss=0.15, name="LeavesGreen"),
}


def _import(fname):
    """[(object name, mesh copy in world space)] from a .blend or .fbx, leaving nothing else behind."""
    path = os.path.join(REF_DIR, fname)
    before = {k: set(getattr(bpy.data, k)) for k in ("objects", "meshes", "materials", "images", "collections")}
    if fname.endswith(".blend"):
        with bpy.data.libraries.load(path) as (src, dst):
            dst.objects = list(src.objects)
        objs = [o for o in dst.objects if o is not None]
        for o in objs:
            bpy.context.scene.collection.objects.link(o)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
        objs = [o for o in bpy.data.objects if o not in before["objects"]]
    bpy.context.view_layer.update()
    out = []
    for o in objs:
        if o.type == "MESH":
            me = o.data.copy()
            me.transform(o.matrix_world)
            out.append((o.name, me))
    keep = {me for _, me in out}
    for o in objs:
        bpy.data.objects.remove(o)
    for kind in ("meshes", "materials", "images", "collections"):
        coll = getattr(bpy.data, kind)
        for idb in list(coll):
            if idb not in before[kind] and idb not in keep:
                coll.remove(idb)
    return out


def _bounds(me):
    co = [v.co for v in me.vertices]
    return (Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co))),
            Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co))))


def _ground(me, height):
    """Matrix that scales a model to `height` metres and puts its base centre on the origin."""
    lo, hi = _bounds(me)
    s = height / (hi.z - lo.z)
    c = (lo + hi) / 2
    return Matrix.Scale(s, 4) @ Matrix.Translation((-c.x, -c.y, -lo.z)), s


def bench(a):
    meshes = dict(_import("bench.blend"))
    me = meshes["Bench"]
    m, s = _ground(me, 0.45)                       # 8 game units long -> 2.4 m, seat at 45 cm
    top = 0.45 - 0.3 * s * 1.0                     # the planks are the top 0.3 units
    a.add_mesh(me, m, lambda c, n: BENCH_WOOD if c.z > top - 0.004 else BENCH_METAL)
    for _, other in meshes.items():
        bpy.data.meshes.remove(other)


def candle(a, height=0.15):
    (_, me), = _import("Candle.fbx")
    m, s = _ground(me, height)
    lo, hi = _bounds(me)
    top_z = height

    def pick(c, n):
        r = math.hypot(c.x, c.y)
        return WICK if (c.z > top_z * 0.9 and r < height * 0.06) else WAX
    a.add_mesh(me, m, pick)
    bpy.data.meshes.remove(me)


def fall_tree(a, which="A", leaves="red", height=8.5):
    meshes = _import(f"FallTree_{which}.fbx")
    trunk = next(me for n, me in meshes if not n.startswith("Leaves"))
    lo = Vector((min(_bounds(me)[0][i] for _, me in meshes) for i in range(3)))
    hi = Vector((max(_bounds(me)[1][i] for _, me in meshes) for i in range(3)))
    tlo, thi = _bounds(trunk)
    s = height / (hi.z - lo.z)
    c = (tlo + thi) / 2                              # centre on the trunk base, not the canopy
    base = Vector((c.x, c.y, lo.z))
    m = Matrix.Scale(s, 4) @ Matrix.Translation(-base)
    leaf = LEAVES[leaves]
    for n, me in meshes:
        a.add_mesh(me, m, (lambda c_, n_: leaf) if n.startswith("Leaves") else (lambda c_, n_: BARK))
        bpy.data.meshes.remove(me)


def hay_bale(a):
    (_, me), = _import("HayBale.fbx")
    m, s = _ground(me, 0.55)
    a.add_mesh(me, m, lambda c, n: HAY)
    bpy.data.meshes.remove(me)


BUILDERS = {
    "RefBench": (bench, {}),
    "RefCandle": (candle, {}),
    "RefCandleTall": (lambda a: candle(a, 0.22), {}),
    "FallTreeA": (lambda a: fall_tree(a, "A", "red"), {"max_res": 2048, "shading": "weighted_sharp"}),
    "FallTreeA_Gold": (lambda a: fall_tree(a, "A", "gold", 7.5), {"max_res": 2048, "shading": "weighted_sharp"}),
    "FallTreeB": (lambda a: fall_tree(a, "B", "gold", 9.0), {"max_res": 2048, "shading": "weighted_sharp"}),
    "FallTreeB_Green": (lambda a: fall_tree(a, "B", "green", 8.0), {"max_res": 2048, "shading": "weighted_sharp"}),
    "RefHayBale": (hay_bale, {}),
}


def get(name):
    fn, kw = BUILDERS[name]
    return K.asset(name, fn, **kw)
