"""Asset kit: chunky, chamfered, hand-made looking props with painted textures.

Matches the style of the reference game assets (bench, hay bale, fall trees, candle):
  * every hard edge gets a chamfer that catches the light,
  * nothing is perfectly straight: each part gets a coherent wobble plus a little jitter,
  * one painted base-colour map and one normal map per asset, baked in Cycles from
    procedural "painters" (wood grain, painted metal with chipped edges, fabric weave, ...)
    with ambient occlusion and edge highlights painted in.

Bakes are cached as JPEGs in assets/baked/ (keyed on geometry + paint settings), so a
rebuild only re-bakes what changed. Each asset is built once per file and placed as
linked duplicates (objects sharing one mesh).

    a = Asset("SchoolDesk")
    a.add(box(a.bm, (0.65, 0.45, 0.025), (0, 0, 0.7)), WOOD, bevel=0.006)
    me = a.build()
    place(me, collection, (x, y, z), yaw)
"""

import hashlib
import json
import math
import os
import random
import zlib

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector, noise

from . import util as U

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAKE_DIR = os.path.join(ROOT, "assets", "baked")
KIT_VERSION = 5
_built = {}
_mats = {}


def reset():
    """Forget meshes/materials of the previous file (call after loading a new file)."""
    _built.clear()
    _mats.clear()


def hexc(h):
    """'#RRGGBB' in sRGB -> linear (r, g, b)."""
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def _col(c):
    if c is None:
        return None
    return hexc(c) if isinstance(c, str) else tuple(c[:3])


# ----------------------------------------------------------------- surfaces

class Surf:
    """How a part is painted for the bake, and how its final material behaves.

    kind: wood | paint | metal | fabric | plaster | stone | wax | paper | rubber | ceramic |
          leaf | bark | hay  (baked)   --   glass | glow | mat  (not baked)
    """
    BAKED = {"wood", "paint", "metal", "fabric", "plaster", "stone", "wax", "paper", "rubber",
             "ceramic", "leaf", "bark", "hay"}

    def __init__(self, kind, color="#808080", color2=None, rough=0.6, metal=0.0, scale=1.0, var=0.07,
                 edge=0.25, ao=0.45, bump=1.0, chips=0.0, grime=0.15, sheen=0.0, sss=0.0,
                 strength=1.0, coat=0.0, material=None, name=None):
        self.kind = kind
        self.color = _col(color)
        self.color2 = _col(color2) if color2 is not None else tuple(c * 0.45 for c in self.color)
        self.rough, self.metal, self.scale, self.var = rough, metal, scale, var
        self.edge, self.ao, self.bump, self.chips, self.grime = edge, ao, bump, chips, grime
        self.sheen, self.sss, self.strength, self.coat = sheen, sss, strength, coat
        self.material = material
        self.name = name or kind

    @property
    def baked(self):
        return self.kind in self.BAKED

    def key(self):
        d = {k: v for k, v in self.__dict__.items() if k != "material"}
        if self.material is not None:
            d["material"] = self.material.name
        return repr(sorted(d.items()))


# ----------------------------------------------------------------- primitives (all return the new verts)

def _matrix(loc=(0, 0, 0), rot=None, scale=None):
    if rot is None:
        r = Matrix()
    elif isinstance(rot, Matrix):
        r = rot.to_4x4()
    elif isinstance(rot, Quaternion):
        r = rot.to_matrix().to_4x4()
    else:
        r = Euler(rot).to_matrix().to_4x4()
    s = Matrix.Diagonal((*(scale or (1, 1, 1)), 1))
    return Matrix.Translation(Vector(loc)) @ r @ s


def box(bm, size, loc=(0, 0, 0), rot=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=_matrix(loc, rot, size), verts=r["verts"])
    return r["verts"]


def box_lohi(bm, lo, hi):
    lo, hi = Vector(lo), Vector(hi)
    return box(bm, hi - lo, (lo + hi) / 2)


def cyl(bm, r, h, segs=8, loc=(0, 0, 0), rot=None, r2=None, caps=True):
    """Prism/cone along local Z, centred on loc."""
    res = bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segs, radius1=r,
                                radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.transform(bm, matrix=_matrix(loc, rot), verts=res["verts"])
    return res["verts"]


def cyl_between(bm, a, b, r, segs=8, r2=None):
    a, b = Vector(a), Vector(b)
    d = b - a
    return cyl(bm, r, d.length, segs, (a + b) / 2, d.to_track_quat("Z", "Y"), r2=r2)


def lathe(bm, prof, segs=12, loc=(0, 0, 0), rot=None, phase=0.0):
    """Revolve a (radius, z) profile (bottom to top) around local Z. r == 0 closes a pole."""
    rings = []
    for r, z in prof:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((math.cos(a) * r, math.sin(a) * r, z))
                          for a in (phase + 2 * math.pi * k / segs for k in range(segs))])
    for a, b in zip(rings, rings[1:]):
        if len(a) > 1 and len(b) > 1:
            for k in range(segs):
                bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))
        elif len(b) > 1:
            for k in range(segs):
                bm.faces.new((a[0], b[(k + 1) % segs], b[k]))
        elif len(a) > 1:
            for k in range(segs):
                bm.faces.new((a[k], a[(k + 1) % segs], b[0]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    verts = [v for ring in rings for v in ring]
    bmesh.ops.transform(bm, matrix=_matrix(loc, rot), verts=verts)
    return verts


def extrude(bm, poly, depth, loc=(0, 0, 0), rot=None):
    """Extrude a CCW 2D outline (x, y) along local Z, centred on loc."""
    bot = [bm.verts.new((x, y, -depth / 2)) for x, y in poly]
    top = [bm.verts.new((x, y, depth / 2)) for x, y in poly]
    n = len(poly)
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for k in range(n):
        bm.faces.new((bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k]))
    verts = bot + top
    bmesh.ops.transform(bm, matrix=_matrix(loc, rot), verts=verts)
    return verts


def tube(bm, pts, r, segs=6, cap=True):
    radii = r if isinstance(r, (list, tuple)) else [r] * len(pts)
    rings = U.bm_tube(bm, pts, radii, segs=segs, cap=cap)
    return [v for ring in rings for v in ring]


def rounded_rect(w, h, r, segs=3):
    """CCW outline of a w x h rectangle with corner radius r (centred)."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                       (w / 2 - r, -h / 2 + r, 270)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


_NOFS = (Vector((13.1, 71.3, 5.7)), Vector((-41.9, 9.4, 33.3)), Vector((7.7, -23.6, -61.2)))


def nvec(p):
    """Deterministic vector noise in about -1..1 (the mathutils vector noise differs from run to run)."""
    return Vector(tuple(noise.noise(p + o) for o in _NOFS))


def _ekey(e):
    """Geometry-based sort key: makes bmesh.ops input order (and so their output) reproducible."""
    c = e.verts[0].co + e.verts[1].co
    return (round(c.x, 5), round(c.y, 5), round(c.z, 5))


def _fkey(f):
    c = f.calc_center_median()
    return (round(c.x, 5), round(c.y, 5), round(c.z, 5), len(f.verts))


def mark_old(bm):
    """Flag every existing vertex; new_verts() then returns only what was created since. (Python
    identity of BMesh elements cannot be trusted across bmesh.ops calls: they may reallocate.)"""
    lay = bm.verts.layers.int.get("_old") or bm.verts.layers.int.new("_old")
    for v in bm.verts:
        v[lay] = 1
    return lay


def new_verts(bm, lay):
    return [v for v in bm.verts if v[lay] == 0]


def blob(bm, size, loc=(0, 0, 0), rot=None, subdiv=2):
    """Lumpy rounded box (hay-bale / hedge / cushion shapes): a cube smoothed toward a sphere."""
    lay = mark_old(bm)
    res = bmesh.ops.create_cube(bm, size=2.0)
    edges = sorted({e for v in res["verts"] for e in v.link_edges}, key=_ekey)
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=subdiv, use_grid_fill=True, smooth=0.0)
    verts = new_verts(bm, lay)
    for v in verts:
        c = v.co
        s = c.normalized()
        v.co = c.lerp(s * 1.25, 0.45)                 # puffed cube, flat-ish faces, round corners
        v.co = Vector((max(-1, min(1, v.co.x)), max(-1, min(1, v.co.y)), max(-1, min(1, v.co.z))))
    bmesh.ops.transform(bm, matrix=_matrix(loc, rot, tuple(x / 2 for x in size)), verts=verts)
    return verts


# ----------------------------------------------------------------- the asset builder

class Asset:
    def __init__(self, name, shading="weighted", density=400, min_res=256, max_res=1024, seed=None):
        self.name = name
        self.shading = shading
        self.density, self.min_res, self.max_res = density, min_res, max_res
        self.bm = bmesh.new()
        lay = self.bm.faces.layers
        self.l_surf = lay.int.new("surf")
        self.l_part = lay.int.new("part")
        self.l_edge = lay.float.new("edge")
        self.l_rand = lay.float.new("prand")
        self.l_grain = lay.float_vector.new("grain")
        self.surfs = []
        self._sid = {}
        self.parts = 0
        self.rnd = random.Random(zlib.crc32(name.encode()) if seed is None else seed)

    def surf_index(self, s):
        if id(s) not in self._sid:
            self._sid[id(s)] = len(self.surfs)
            self.surfs.append(s)
        return self._sid[id(s)]

    def add(self, verts, s, bevel=0.0, seg=1, angle=50.0, wobble=0.0, jitter=0.0, grain=None, rand=None,
            wfreq=None):
        """Tag a freshly built part, chamfer its hard edges, then make it hand-made (wobble/jitter)."""
        bm = self.bm
        sid = self.surf_index(s)
        pid = self.parts
        self.parts += 1
        verts = list(verts)
        faces = {f for v in verts for f in v.link_faces}
        r = self.rnd.random() if rand is None else rand
        lo = Vector((min(v.co.x for v in verts), min(v.co.y for v in verts), min(v.co.z for v in verts)))
        hi = Vector((max(v.co.x for v in verts), max(v.co.y for v in verts), max(v.co.z for v in verts)))
        ext = hi - lo
        if grain is None:
            ax = max(range(3), key=lambda i: ext[i])
            grain = Vector([1.0 if i == ax else 0.0 for i in range(3)])
        grain = Vector(grain).normalized()
        for f in faces:
            f[self.l_surf], f[self.l_part], f[self.l_rand], f[self.l_edge] = sid, pid, r, 0.0
            f[self.l_grain] = grain
        if wobble or jitter:
            # before the bevel: bevel rebuilds the part's faces, so these vertex references would go stale
            size = max(ext.length, 1e-3)
            f1 = wfreq if wfreq else 1.3 / size
            off1 = Vector((self.rnd.uniform(-99, 99) for _ in range(3)))
            off2 = Vector((self.rnd.uniform(-99, 99) for _ in range(3)))
            for v in {v for f in faces for v in f.verts}:
                d = Vector()
                if wobble:
                    d += nvec(v.co * f1 + off1) * wobble
                if jitter:
                    d += nvec(v.co * (9.0 / size) + off2) * jitter
                v.co += d
        if bevel > 0:
            lim = math.radians(angle)
            edges = sorted((e for e in {e for f in faces for e in f.edges}
                            if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim), key=_ekey)
            if edges:
                res = bmesh.ops.bevel(bm, geom=edges, offset=bevel, offset_type="OFFSET", segments=seg,
                                      profile=0.5, affect="EDGES", clamp_overlap=True, loop_slide=True)
                for f in res["faces"]:
                    f[self.l_surf], f[self.l_part], f[self.l_rand], f[self.l_edge] = sid, pid, r, 1.0
                    f[self.l_grain] = grain
                return list(res["faces"])
        return faces

    def add_mesh(self, me, matrix, classify):
        """Append an existing mesh (e.g. an imported model) transformed by `matrix`; classify(centre,
        normal) -> Surf picks each face's surface. Each surface becomes one part (no extra bevel)."""
        tmp = me.copy()
        tmp.transform(matrix)
        for at in [at.name for at in tmp.attributes if not at.name.startswith(".") and at.name not in ("position",)]:
            tmp.attributes.remove(tmp.attributes[at])
        while tmp.uv_layers:
            tmp.uv_layers.remove(tmp.uv_layers[0])
        bm = self.bm
        lay = mark_old(bm)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        groups = {}
        for f in sorted({f for v in new_verts(bm, lay) for f in v.link_faces}, key=_fkey):
            s = classify(f.calc_center_median(), f.normal)
            groups.setdefault(id(s), (s, []))[1].append(f)
        for s, faces in groups.values():
            sid = self.surf_index(s)
            pid = self.parts
            self.parts += 1
            vs = [v.co for f in faces for v in f.verts]
            ext = Vector((max(c[i] for c in vs) - min(c[i] for c in vs) for i in range(3)))
            ax = max(range(3), key=lambda i: ext[i])
            grain = Vector([1.0 if i == ax else 0.0 for i in range(3)])
            r = self.rnd.random()
            for f in faces:
                f[self.l_surf], f[self.l_part], f[self.l_rand], f[self.l_edge] = sid, pid, r, 0.0
                f[self.l_grain] = grain

    # ------------------------------------------------------------- shorthands (add + tag in one call)

    def box(self, size, loc, s, rot=None, **kw):
        return self.add(box(self.bm, size, loc, rot), s, **kw)

    def lohi(self, lo, hi, s, **kw):
        return self.add(box_lohi(self.bm, lo, hi), s, **kw)

    def cyl(self, r, h, loc, s, segs=8, rot=None, r2=None, **kw):
        return self.add(cyl(self.bm, r, h, segs, loc, rot, r2), s, **kw)

    def rod(self, a, b, r, s, segs=8, r2=None, **kw):
        return self.add(cyl_between(self.bm, a, b, r, segs, r2), s, **kw)

    def lathe(self, prof, s, segs=12, loc=(0, 0, 0), rot=None, **kw):
        return self.add(lathe(self.bm, prof, segs, loc, rot), s, **kw)

    def tube(self, pts, r, s, segs=6, cap=True, **kw):
        return self.add(tube(self.bm, pts, r, segs, cap), s, **kw)

    def extrude(self, poly, depth, loc, s, rot=None, **kw):
        return self.add(extrude(self.bm, poly, depth, loc, rot), s, **kw)

    def plane(self, w, h, loc, s, rot=None, **kw):
        """Single quad in the XZ plane facing -Y (rotate for other facings) - decals, labels."""
        bm = self.bm
        vs = [bm.verts.new(p) for p in ((-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2))]
        bm.faces.new(vs)
        bmesh.ops.transform(bm, matrix=_matrix(loc, rot), verts=vs)
        return self.add(vs, s, **kw)

    def blob(self, size, loc, s, rot=None, subdiv=2, **kw):
        return self.add(blob(self.bm, size, loc, rot, subdiv), s, **kw)

    # ------------------------------------------------------------- build

    def build(self):
        """-> mesh with custom normals, UVs and final materials (bakes or loads the textures)."""
        if self.name in _built:
            self.bm.free()
            return _built[self.name]
        bm = self.bm
        bake_faces = [f for f in bm.faces if self.surfs[f[self.l_surf]].baked]
        area = sum(f.calc_area() for f in bake_faces)
        res = int(2 ** math.ceil(math.log2(max(1.0, math.sqrt(max(area, 1e-6)) * self.density))))
        res = max(self.min_res, min(self.max_res, res))
        # canonical element order: bmesh ops leave a memory-address dependent order behind, which
        # would change UVs (and the bake cache key) from run to run
        lay_s = self.l_surf
        for seq, key in ((bm.verts, lambda v: (round(v.co.x, 5), round(v.co.y, 5), round(v.co.z, 5), len(v.link_faces))),
                         (bm.edges, _ekey), (bm.faces, lambda f: (*_fkey(f), f[lay_s]))):
            rank = {e: i for i, e in enumerate(sorted(seq, key=key))}    # BMElemSeq.sort wants a number
            seq.sort(key=lambda e: rank[e])
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        surf = np.zeros(len(me.polygons), np.int32)
        me.attributes["surf"].data.foreach_get("value", surf)
        me.polygons.foreach_set("material_index", surf)
        ob = bpy.data.objects.new("_kit_" + self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        me = self._shade(ob)
        # slots are only ever assigned, never cleared: clearing them zeroes every face's index
        while len(me.materials) < len(self.surfs):
            me.materials.append(None)
        me.polygons.foreach_set("material_index", self._poly_surfs(me))
        key = self._key(me, res)
        if any(s.kind == "tile" for s in self.surfs):
            self._box_uv(me)
        if any(s.kind == "decal" for s in self.surfs):
            self._decal_uv(me)
        if bake_faces:
            # the UV layout is cached next to the textures: Blender versions unwrap differently
            if not self._load_uv(me, key):
                self._unwrap(ob, me, res)
                self._save_uv(me, key)
            imgs = self._load_cache(key) or self._bake(ob, me, res, key)
        else:
            imgs = (None, None)
        for i, s in enumerate(self.surfs):
            me.materials[i] = final_material(self.name, i, s, *imgs)
        for a in ("edge", "part", "prand", "grain", "_old"):
            if a in me.attributes:
                me.attributes.remove(me.attributes[a])
        bpy.data.objects.remove(ob)
        _built[self.name] = me
        return me

    def _shade(self, ob):
        me = ob.data
        if self.shading == "flat":
            me.shade_flat()
            return me
        me.shade_smooth()
        if self.shading == "smooth":
            return me
        wn = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
        wn.keep_sharp, wn.weight, wn.mode = True, 50, "FACE_AREA"
        if self.shading == "weighted_sharp" and hasattr(me, "set_sharp_from_angle"):
            me.set_sharp_from_angle(angle=math.radians(60))
        dg = bpy.context.evaluated_depsgraph_get()
        new = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        ob.modifiers.clear()
        old = ob.data
        ob.data = new
        bpy.data.meshes.remove(old)
        new.name = self.name
        return new

    def _key(self, me, res):
        co = np.zeros(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        h = hashlib.sha1()
        h.update(f"{KIT_VERSION}|{self.name}|{res}|{len(me.polygons)}".encode())
        h.update(np.round(co, 4).tobytes())
        h.update(self._poly_surfs(me).tobytes())          # which surface each face is painted with
        for s in self.surfs:
            h.update(s.key().encode())
        return h.hexdigest()

    def _unwrap(self, ob, me, res):
        vl = bpy.context.view_layer
        for o in list(vl.objects.selected):
            if o is not None:                  # removed objects (e.g. after an FBX import) linger as None
                o.select_set(False)
        vl.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="FACE")
        bm = bmesh.from_edit_mesh(me)
        lay = bm.faces.layers.int.get("surf")
        for elems in (bm.verts, bm.edges, bm.faces):
            for e in elems:
                e.select = False
        for f in bm.faces:
            if self.surfs[f[lay]].baked:
                f.select_set(True)
        bmesh.update_edit_mesh(me)
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), margin_method="FRACTION",
                                 island_margin=6.0 / res, area_weight=0.0, correct_aspect=True,
                                 scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")

    def _box_uv(self, me):
        """World-scale box projection for tiling surfaces: u, v in metres / tile size."""
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        uvl = me.uv_layers.active
        npoly, nloop = len(me.polygons), len(me.loops)
        surf = self._poly_surfs(me)
        tile = np.array([s.kind == "tile" for s in self.surfs])[surf]
        size = np.array([s.scale if s.kind == "tile" else 1.0 for s in self.surfs], np.float32)[surf]
        nrm = np.zeros(npoly * 3, np.float32)
        me.polygons.foreach_get("normal", nrm)
        nrm = nrm.reshape(-1, 3)
        start = np.zeros(npoly, np.int32)
        total = np.zeros(npoly, np.int32)
        me.polygons.foreach_get("loop_start", start)
        me.polygons.foreach_get("loop_total", total)
        lpoly = np.repeat(np.arange(npoly), total)
        vidx = np.zeros(nloop, np.int32)
        me.loops.foreach_get("vertex_index", vidx)
        co = np.zeros(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        p = co.reshape(-1, 3)[vidx]
        n = nrm[lpoly]
        ax = np.argmax(np.abs(n), axis=1)
        sgn = np.sign(n[np.arange(nloop), ax])
        u = np.where(ax == 2, p[:, 0], np.where(ax == 0, -sgn * p[:, 1], sgn * p[:, 0]))
        v = np.where(ax == 2, p[:, 1] * np.where(sgn < 0, -1, 1), p[:, 2])
        uv = np.zeros(nloop * 2, np.float32)
        uvl.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        m = tile[lpoly]
        sz = size[lpoly]
        uv[m, 0] = u[m] / sz[m]
        uv[m, 1] = v[m] / sz[m]
        uvl.data.foreach_set("uv", uv.ravel())

    def _decal_uv(self, me):
        """Each decal part shows the whole image on its front face (viewed upright)."""
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        uvl = me.uv_layers.active
        npoly, nloop = len(me.polygons), len(me.loops)
        surf = self._poly_surfs(me)
        dec = np.array([s.kind == "decal" for s in self.surfs])[surf]
        part = np.zeros(npoly, np.int32)
        me.attributes["part"].data.foreach_get("value", part)
        uv = np.zeros(nloop * 2, np.float32)
        uvl.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        co = np.zeros(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        for pid in np.unique(part[dec]):
            polys = [me.polygons[i] for i in np.nonzero(dec & (part == pid))[0]]
            n = Vector()
            for p in polys:
                n += p.normal * p.area
            big = max(polys, key=lambda p: p.area)
            n = big.normal.copy() if n.length < 1e-9 else n.normalized()
            up = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((0, 1, 0))
            ua = up.cross(n).normalized()
            va = n.cross(ua).normalized()
            loops = [li for p in polys for li in range(p.loop_start, p.loop_start + p.loop_total)]
            pts = np.array([co[me.loops[li].vertex_index] for li in loops])
            u = pts @ np.array(ua)
            v = pts @ np.array(va)
            u = (u - u.min()) / max(1e-9, u.max() - u.min())
            v = (v - v.min()) / max(1e-9, v.max() - v.min())
            uv[loops, 0] = u
            uv[loops, 1] = v
        uvl.data.foreach_set("uv", uv.ravel())

    def _uv_path(self):
        return os.path.join(BAKE_DIR, f"{self.name}_UV.npz")

    @staticmethod
    def _loop_verts(me):
        lv = np.zeros(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", lv)
        return lv

    def _load_uv(self, me, key):
        try:
            d = np.load(self._uv_path())
        except (OSError, ValueError):
            return False
        lv = self._loop_verts(me)
        if str(d["key"]) != key or d["uv"].shape[0] != lv.shape[0] or not np.array_equal(d["lv"], lv):
            return False
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        me.uv_layers.active.data.foreach_set("uv", d["uv"].ravel())
        return True

    def _save_uv(self, me, key):
        uv = np.zeros(len(me.loops) * 2, np.float32)
        me.uv_layers.active.data.foreach_get("uv", uv)
        os.makedirs(BAKE_DIR, exist_ok=True)
        np.savez_compressed(self._uv_path(), key=key, uv=uv.reshape(-1, 2), lv=self._loop_verts(me))

    @staticmethod
    def _poly_surfs(me):
        surf = np.zeros(len(me.polygons), np.int32)
        me.attributes["surf"].data.foreach_get("value", surf)
        return surf

    # ------------------------------------------------------------- bake + cache

    def _paths(self):
        return (os.path.join(BAKE_DIR, f"{self.name}.json"), os.path.join(BAKE_DIR, f"{self.name}_C.jpg"),
                os.path.join(BAKE_DIR, f"{self.name}_N.jpg"))

    def _load_cache(self, key):
        jp, cp, np_ = self._paths()
        try:
            with open(jp) as fh:
                if json.load(fh).get("key") != key:
                    return None
        except (OSError, ValueError):
            return None
        if not (os.path.exists(cp) and os.path.exists(np_)):
            return None
        return load_image(cp, "sRGB"), load_image(np_, "Non-Color")

    def _bake(self, ob, me, res, key):
        sc = bpy.context.scene
        saved = (sc.render.engine, sc.cycles.samples, sc.cycles.use_denoising, sc.render.bake.margin)
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.use_denoising = False
        sc.render.bake.margin = max(4, res // 64)
        sc.render.bake.margin_type = "EXTEND"
        img_c = bpy.data.images.new("_bakeC", res, res, alpha=False, float_buffer=True)
        img_n = bpy.data.images.new("_bakeN", res, res, alpha=False, float_buffer=True)
        img_n.colorspace_settings.name = "Non-Color"
        dummy = bpy.data.images.new("_bakeDummy", 8, 8, alpha=False, float_buffer=True)
        co = np.zeros(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        size = max(float(np.linalg.norm(co.max(0) - co.min(0))), 0.05)
        mats, nodes = [], []
        for s in self.surfs:
            m, n = bake_material(s, size) if s.baked else _dummy_material()
            mats.append(m)
            nodes.append((n, s.baked))
        for i, m in enumerate(mats):
            me.materials[i] = m
        for o in list(bpy.context.view_layer.objects.selected):
            if o is not None:
                o.select_set(False)
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        for img, kind, samples in ((img_c, "EMIT", 16), (img_n, "NORMAL", 4)):
            for n, baked in nodes:
                n.image = img if baked else dummy
                n.id_data.nodes.active = n
            sc.cycles.samples = samples
            if kind == "NORMAL":
                bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=sc.render.bake.margin)
            else:
                bpy.ops.object.bake(type="EMIT", margin=sc.render.bake.margin)
        os.makedirs(BAKE_DIR, exist_ok=True)
        jp, cp, np_ = self._paths()
        save_jpeg(img_c, cp, srgb=True, quality=90)
        save_jpeg(img_n, np_, srgb=False, quality=94)
        with open(jp, "w") as fh:
            json.dump({"key": key, "res": res}, fh)
        for i in range(len(mats)):
            me.materials[i] = None
        for m in mats:
            bpy.data.materials.remove(m)
        for img in (img_c, img_n, dummy):
            bpy.data.images.remove(img)
        (sc.render.engine, sc.cycles.samples, sc.cycles.use_denoising, sc.render.bake.margin) = saved
        print(f"  baked {self.name} {res}px")
        return load_image(cp, "sRGB", reload=True), load_image(np_, "Non-Color", reload=True)


def asset(name, fn, **kw):
    """Build once per file: fn(a) fills a fresh Asset `a`; returns the finished mesh."""
    if name in _built:
        return _built[name]
    a = Asset(name, **kw)
    fn(a)
    return a.build()


def save_jpeg(img, path, srgb=True, quality=90):
    from PIL import Image
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[::-1, :, :3]
    if srgb:
        px = U.linear_to_srgb(px)
    Image.fromarray((np.clip(px, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path, quality=quality, subsampling=0)


def load_image(path, colorspace, reload=False):
    name = os.path.basename(path)
    img = bpy.data.images.get(name)
    if img is not None and reload:
        bpy.data.images.remove(img)
        img = None
    if img is None or img.filepath != path:
        img = bpy.data.images.load(path)
        img.name = name
        img.pack()
    img.colorspace_settings.name = colorspace
    return img


def place(me, col, loc=(0, 0, 0), rot=0.0, scale=1.0, name=None):
    """A linked duplicate of an asset mesh. rot: yaw in radians or an Euler tuple."""
    ob = bpy.data.objects.new(name or me.name, me)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot) if isinstance(rot, (int, float)) else tuple(rot)
    ob.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else tuple(scale)
    col.objects.link(ob)
    return ob


# ----------------------------------------------------------------- node helper

class NG:
    def __init__(self, nt):
        self.nt = nt

    def set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        elif v is not None:
            if hasattr(sock, "default_value"):
                dv = sock.default_value
                if hasattr(dv, "__len__") and not hasattr(v, "__len__"):
                    v = [v] * len(dv)
                elif hasattr(dv, "__len__") and len(v) == 3 and len(dv) == 4:
                    v = (*v, 1.0)
                sock.default_value = v

    def node(self, kind, props=None, **inputs):
        n = self.nt.nodes.new(kind)
        for k, v in (props or {}).items():
            setattr(n, k, v)
        for k, v in inputs.items():
            self.set(n.inputs[k.replace("_", " ")], v)
        return n

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        n = self.node("ShaderNodeMath", {"operation": op, "use_clamp": clamp})
        for i, v in enumerate((a, b, c)):
            self.set(n.inputs[i], v)
        return n.outputs[0]

    def vmath(self, op, a, b=None, c=None, scale=None):
        n = self.node("ShaderNodeVectorMath", {"operation": op})
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        if c is not None:
            self.set(n.inputs[2], c)
        if scale is not None:
            self.set(n.inputs[3], scale)
        return n.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs["Vector"]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", {"data_type": "RGBA", "blend_type": blend, "clamp_result": False})
        self.set(n.inputs[0], fac)
        self.set(n.inputs[6], a)
        self.set(n.inputs[7], b)
        return n.outputs[2]

    def noise(self, vec, scale, detail=2.0, rough=0.5, distortion=0.0):
        n = self.node("ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=rough, Distortion=distortion)
        self.set(n.inputs["Vector"], vec)
        return n.outputs["Fac"]

    def voronoi(self, vec, scale, feature="F1", rnd=1.0):
        n = self.node("ShaderNodeTexVoronoi", {"feature": feature}, Scale=scale, Randomness=rnd)
        self.set(n.inputs["Vector"], vec)
        return n.outputs["Distance"]

    def wave(self, vec, scale, direction="X", distortion=0.0, detail=0.0):
        n = self.node("ShaderNodeTexWave", {"wave_type": "BANDS", "bands_direction": direction},
                      Scale=scale, Distortion=distortion, Detail=detail)
        self.set(n.inputs["Vector"], vec)
        return n.outputs["Fac"]

    def ramp(self, fac, stops):
        n = self.node("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
        cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
        for pos, c in stops[1:-1]:
            cr.elements.new(pos).color = (*c, 1)
        self.set(n.inputs["Fac"], fac)
        return n.outputs["Color"]

    def maprange(self, v, a, b, c=0.0, d=1.0, clamp=True):
        n = self.node("ShaderNodeMapRange", {"clamp": clamp}, From_Min=a, From_Max=b, To_Min=c, To_Max=d)
        self.set(n.inputs["Value"], v)
        return n.outputs["Result"]

    def scale(self, col, f):
        return self.vmath("SCALE", col, scale=f)

    def sep(self, vec):
        n = self.node("ShaderNodeSeparateXYZ")
        self.set(n.inputs[0], vec)
        return n.outputs

    def attr(self, name):
        return self.node("ShaderNodeAttribute", {"attribute_name": name}).outputs


# ----------------------------------------------------------------- painters (bake materials)

def _grain_space(g, P, grain, stretch):
    """Coordinates where features run `stretch` times longer along the grain direction."""
    along = g.vmath("DOT_PRODUCT", P, grain)
    on_axis = g.vmath("SCALE", grain, scale=along)
    across = g.vmath("SUBTRACT", P, on_axis)
    shrunk = g.vmath("SCALE", grain, scale=g.math("DIVIDE", along, stretch))
    return g.vmath("ADD", across, shrunk)


def _paint_wood(g, s, c):
    Q = _grain_space(g, c["P"], c["grain"], 9.0)
    Q = g.vmath("ADD", Q, g.vmath("SCALE", (1.7, 3.1, 0.7), scale=c["prand"]))      # every board differs
    streak = g.noise(Q, 6.0 * s.scale, detail=6.0, rough=0.62, distortion=0.35)
    fiber = g.noise(Q, 34.0 * s.scale, detail=3.0, rough=0.5)
    t = g.math("MULTIPLY_ADD", streak, 0.7, g.math("MULTIPLY", fiber, 0.3))
    col = g.ramp(t, [(0.36, s.color2), (0.5, tuple((a + b) / 2 for a, b in zip(s.color, s.color2))), (0.64, s.color)])
    # thin darker grain lines
    lines = g.noise(_grain_space(g, Q, c["grain"], 4.0), 22.0 * s.scale, detail=2.0, distortion=1.2)
    line = g.maprange(g.math("ABSOLUTE", g.math("SUBTRACT", lines, 0.5)), 0.0, 0.035, 1.0, 0.0)
    col = g.scale(col, g.math("MULTIPLY_ADD", line, -0.22, 1.0))
    h = g.math("ADD", g.math("MULTIPLY_ADD", fiber, 0.6, g.math("MULTIPLY", streak, 0.4)), g.math("MULTIPLY", line, -0.5))
    return col, h


def _paint_paint(g, s, c):
    bl = g.noise(c["P"], 2.2 * s.scale / max(c["size"], 0.2), detail=3.0)
    col = g.scale(s.color, g.math("MULTIPLY_ADD", bl, 0.14, 0.93))
    h = g.math("MULTIPLY", g.noise(c["P"], 140.0 * s.scale, detail=2.0), 0.08)
    if s.chips > 0:
        chip_n = g.noise(c["P"], 26.0 * s.scale, detail=4.0, rough=0.7)
        edge_chip = g.math("MULTIPLY", c["edge"], g.maprange(chip_n, 0.5 - 0.15 * s.chips, 0.56 - 0.15 * s.chips))
        spot = g.maprange(g.noise(c["P"], 9.0 * s.scale, detail=5.0, rough=0.7), 0.8 - 0.06 * s.chips, 0.83 - 0.06 * s.chips)
        m = g.math("MAXIMUM", edge_chip, g.math("MULTIPLY", spot, 0.6 * s.chips))
        col = g.mix(m, col, s.color2)
        h = g.math("MULTIPLY_ADD", m, -0.5, h)
    return col, h


def _paint_metal(g, s, c):
    Q = _grain_space(g, c["P"], c["grain"], 30.0)
    br = g.noise(Q, 55.0 * s.scale, detail=4.0)
    bl = g.noise(c["P"], 3.0 * s.scale, detail=3.0)
    col = g.scale(s.color, g.math("ADD", g.math("MULTIPLY", br, 0.22), g.math("MULTIPLY_ADD", bl, 0.14, 0.75)))
    return col, g.math("MULTIPLY", br, 0.15)


def _paint_fabric(g, s, c):
    P = g.vmath("SCALE", c["P"], scale=s.scale)
    w1 = g.wave(P, 260.0, "X")
    w2 = g.wave(P, 260.0, "Y")
    weave = g.math("MULTIPLY", w1, w2)
    bl = g.noise(c["P"], 3.0 * s.scale, detail=4.0)
    col = g.scale(s.color, g.math("ADD", g.math("MULTIPLY_ADD", bl, 0.18, 0.86), g.math("MULTIPLY", weave, 0.08)))
    return col, g.math("MULTIPLY", weave, 0.5)


def _paint_plaster(g, s, c):
    bl = g.noise(c["P"], 1.6 * s.scale, detail=6.0, rough=0.6)
    col = g.ramp(bl, [(0.35, s.color2), (0.62, s.color)])
    sp = g.voronoi(c["P"], 70.0 * s.scale)
    speck = g.maprange(sp, 0.0, 0.12, 1.0, 0.0)
    col = g.scale(col, g.math("MULTIPLY_ADD", speck, -0.12, 1.0))
    h = g.math("ADD", g.math("MULTIPLY", g.noise(c["P"], 30.0 * s.scale, detail=6.0), 0.6), g.math("MULTIPLY", speck, -0.3))
    return col, h


def _paint_stone(g, s, c):
    col, h = _paint_plaster(g, s, c)
    pits = g.maprange(g.voronoi(c["P"], 24.0 * s.scale), 0.0, 0.08, 1.0, 0.0)
    col = g.scale(col, g.math("MULTIPLY_ADD", pits, -0.25, 1.0))
    return col, g.math("MULTIPLY_ADD", pits, -0.6, h)


def _paint_wax(g, s, c):
    gz = g.sep(c["gen"])["Z"]
    t = g.math("POWER", gz, 0.6)
    col = g.mix(t, s.color2, s.color)
    col = g.scale(col, g.math("MULTIPLY_ADD", g.noise(c["P"], 9.0 * s.scale, detail=3.0), 0.1, 0.95))
    return col, g.math("MULTIPLY", g.noise(c["P"], 16.0 * s.scale, detail=3.0), 0.4)


def _paint_paper(g, s, c):
    n = g.noise(c["P"], 12.0 * s.scale, detail=4.0)
    return g.scale(s.color, g.math("MULTIPLY_ADD", n, 0.07, 0.95)), g.math("MULTIPLY", g.noise(c["P"], 200.0, detail=2.0), 0.1)


def _paint_rubber(g, s, c):
    n = g.noise(c["P"], 18.0 * s.scale, detail=3.0)
    return g.scale(s.color, g.math("MULTIPLY_ADD", n, 0.2, 0.88)), g.math("MULTIPLY", g.noise(c["P"], 90.0, detail=2.0), 0.25)


def _paint_ceramic(g, s, c):
    n = g.noise(c["P"], 4.0 * s.scale, detail=3.0)
    return g.scale(s.color, g.math("MULTIPLY_ADD", n, 0.06, 0.97)), g.math("MULTIPLY", n, 0.03)


def _paint_leaf(g, s, c):
    gz = g.sep(c["gen"])["Z"]
    mott = g.noise(c["P"], 2.6 * s.scale, detail=3.0, rough=0.6)
    t = g.math("ADD", g.math("MULTIPLY", gz, 0.75), g.math("MULTIPLY_ADD", mott, 0.55, -0.15), clamp=True)
    col = g.ramp(t, [(0.0, s.color2), (0.55, tuple((a + b) / 2 for a, b in zip(s.color, s.color2))), (1.0, s.color)])
    return col, g.noise(c["P"], 9.0 * s.scale, detail=2.0)


def _paint_bark(g, s, c):
    Q = _grain_space(g, c["P"], c["grain"], 5.0)
    st = g.noise(Q, 7.0 * s.scale, detail=6.0, rough=0.6)
    crack = g.maprange(g.voronoi(Q, 9.0 * s.scale, feature="DISTANCE_TO_EDGE"), 0.0, 0.07, 1.0, 0.0)
    col = g.ramp(st, [(0.3, s.color2), (0.7, s.color)])
    col = g.scale(col, g.math("MULTIPLY_ADD", crack, -0.45, 1.0))
    return col, g.math("ADD", g.math("MULTIPLY", st, 0.4), g.math("MULTIPLY", crack, -0.7))


def _paint_hay(g, s, c):
    Q = _grain_space(g, c["P"], c["grain"], 14.0)
    strands = g.noise(Q, 40.0 * s.scale, detail=3.0, rough=0.6)
    col = g.ramp(strands, [(0.3, s.color2), (0.7, s.color)])
    col = g.scale(col, g.math("MULTIPLY_ADD", g.noise(c["P"], 3.0, detail=3.0), 0.2, 0.9))
    return col, strands


PAINTERS = {"wood": _paint_wood, "paint": _paint_paint, "metal": _paint_metal, "fabric": _paint_fabric,
            "plaster": _paint_plaster, "stone": _paint_stone, "wax": _paint_wax, "paper": _paint_paper,
            "rubber": _paint_rubber, "ceramic": _paint_ceramic, "leaf": _paint_leaf, "bark": _paint_bark,
            "hay": _paint_hay}


def bake_material(s, size):
    """Emission = painted albedo (with AO, edge highlights, top light, grime); BSDF normal = bump."""
    mat, nt, out = U.new_material("_bake_" + s.name)
    g = NG(nt)
    tc = g.node("ShaderNodeTexCoord")
    geo = g.node("ShaderNodeNewGeometry")
    c = {"P": tc.outputs["Object"], "gen": tc.outputs["Generated"], "N": geo.outputs["Normal"],
         "prand": g.attr("prand")["Fac"], "edge": g.attr("edge")["Fac"], "grain": g.attr("grain")["Vector"],
         "size": size}
    col, h = PAINTERS[s.kind](g, s, c)
    # per-part value shift
    col = g.scale(col, g.math("MULTIPLY_ADD", c["prand"], 2 * s.var, 1 - s.var))
    # cavities
    ao = g.node("ShaderNodeAmbientOcclusion", {"only_local": True, "samples": 8},
                Distance=max(0.03, min(0.45, size * 0.12)))
    col = g.scale(col, g.maprange(ao.outputs["AO"], 0.0, 1.0, 1.0 - s.ao, 1.0))
    # light from above, darker undersides
    nz = g.sep(c["N"])["Z"]
    col = g.scale(col, g.math("MULTIPLY_ADD", nz, 0.07, 1.0))
    # painted edge highlight on the chamfers
    hi = g.vmath("MULTIPLY_ADD", col, (1.35, 1.35, 1.35), (0.03, 0.03, 0.03))
    col = g.mix(g.math("MULTIPLY", c["edge"], s.edge), col, hi)
    # grime creeping up from the bottom
    if s.grime > 0:
        gz = g.sep(c["gen"])["Z"]
        low = g.math("POWER", g.math("SUBTRACT", 1.0, gz, clamp=True), 4.0)
        dirt = g.math("MULTIPLY", low, g.math("MULTIPLY", g.noise(c["P"], 5.0, detail=4.0), 2 * s.grime))
        col = g.scale(col, g.math("SUBTRACT", 1.0, g.math("MINIMUM", dirt, 0.6)))
    em = g.node("ShaderNodeEmission", Strength=1.0)
    g.set(em.inputs["Color"], col)
    bump = g.node("ShaderNodeBump", Strength=min(1.0, 0.35 * s.bump), Distance=0.004)
    g.set(bump.inputs["Height"], h)
    dif = g.node("ShaderNodeBsdfDiffuse")
    g.set(dif.inputs["Normal"], bump.outputs["Normal"])
    add = g.node("ShaderNodeAddShader")
    g.set(add.inputs[0], em.outputs[0])
    g.set(add.inputs[1], dif.outputs[0])
    g.set(out.inputs["Surface"], add.outputs[0])
    tex = g.node("ShaderNodeTexImage")
    return mat, tex


def _dummy_material():
    mat, nt, out = U.new_material("_bake_dummy")
    g = NG(nt)
    em = g.node("ShaderNodeEmission", Color=(0, 0, 0, 1))
    g.set(out.inputs["Surface"], em.outputs[0])
    return mat, g.node("ShaderNodeTexImage")


# ----------------------------------------------------------------- final materials

def final_material(asset, idx, s, img_c, img_n):
    from . import mats as M
    if s.kind == "glass":
        return M.glass(f"{s.name}", tint=s.color, reflect=0.15, rough=s.rough)
    if s.kind == "glow":
        return M.glow(f"{s.name}", s.color, s.strength)
    if s.kind in ("mat", "tile", "decal"):
        return s.material
    name = f"{asset}_{s.name}"
    if (asset, idx) in _mats:
        return _mats[(asset, idx)]
    mat, nt, out = U.new_material(name)
    g = NG(nt)
    b = g.node("ShaderNodeBsdfPrincipled", Roughness=s.rough, Metallic=s.metal)
    g.set(out.inputs["Surface"], b.outputs[0])
    tc = g.node("ShaderNodeTexImage", {"image": img_c})
    g.set(b.inputs["Base Color"], tc.outputs["Color"])
    tn = g.node("ShaderNodeTexImage", {"image": img_n})
    nm = g.node("ShaderNodeNormalMap", Strength=1.0)
    g.set(nm.inputs["Color"], tn.outputs["Color"])
    g.set(b.inputs["Normal"], nm.outputs["Normal"])
    if s.sheen:
        b.inputs["Sheen Weight"].default_value = s.sheen
    if s.sss:
        b.inputs["Subsurface Weight"].default_value = s.sss
        b.inputs["Subsurface Radius"].default_value = (0.1, 0.06, 0.03)
        b.inputs["Subsurface Scale"].default_value = 0.02
    if s.coat:
        b.inputs["Coat Weight"].default_value = s.coat
    mat.diffuse_color = (*s.color, 1)
    mat.roughness = s.rough
    mat.metallic = s.metal
    _mats[(asset, idx)] = mat
    return mat
