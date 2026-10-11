"""Tileable painted textures for architecture (walls, floors, roofs, roads), made with numpy.

Every generator returns (albedo sRGB float HxWx3, height HxW) that tile seamlessly; tile_material()
turns them into base colour + normal JPEGs (cached in assets/baked/) and a material. Surfaces
using them get box-projected UVs in metres / tile size (see kit.Surf kind "tile").
"""

import math
import os

import bpy
import numpy as np

from . import kit as K
from . import util as U

TEX_VERSION = 2
_mats = {}


def reset():
    _mats.clear()


# ----------------------------------------------------------------- tileable noise

def fbm(n, freq, seed, octaves=5, gain=0.5, warp=0.0):
    """Tileable value-noise fBm in 0..1 (n x n); `freq` = cells across the tile at the base octave."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    x = np.arange(n, dtype=np.float32) / n
    for o in range(octaves):
        f = int(freq * 2 ** o)
        if f >= n:
            break
        g = rng.random((f, f)).astype(np.float32)
        out += amp * _interp(g, x, x, f)
        tot += amp
        amp *= gain
    out /= tot
    if warp:
        wx = fbm(n, max(1, freq // 2), seed + 101, 3)
        wy = fbm(n, max(1, freq // 2), seed + 202, 3)
        out = sample(out, (wx - 0.5) * warp, (wy - 0.5) * warp)
    return out


def _interp(g, xs, ys, f):
    fx = xs * f
    fy = ys * f
    x0 = np.floor(fx).astype(int) % f
    y0 = np.floor(fy).astype(int) % f
    tx = fx - np.floor(fx)
    ty = fy - np.floor(fy)
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    x1, y1 = (x0 + 1) % f, (y0 + 1) % f
    a = g[np.ix_(y0, x0)]
    b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]
    d = g[np.ix_(y1, x1)]
    top = a + (b - a) * tx[None, :]
    bot = c + (d - c) * tx[None, :]
    return top + (bot - top) * ty[:, None]


def sample(img, dx, dy):
    """Sample img at (x + dx, y + dy) (offsets in tile units), wrapping."""
    n = img.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    sx = (xx + dx * n) % n
    sy = (yy + dy * n) % n
    x0 = np.floor(sx).astype(int)
    y0 = np.floor(sy).astype(int)
    tx, ty = sx - x0, sy - y0
    x0, y0 = x0 % n, y0 % n                  # float rounding can land exactly on n
    x1, y1 = (x0 + 1) % n, (y0 + 1) % n
    return ((img[y0, x0] * (1 - tx) + img[y0, x1] * tx) * (1 - ty) + (img[y1, x0] * (1 - tx) + img[y1, x1] * tx) * ty)


def stretch_noise(n, fx, fy, seed, octaves=4):
    """Anisotropic tileable noise: fx cells across, fy cells down (grain, streaks)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    xs = np.arange(n, dtype=np.float32) / n
    for o in range(octaves):
        a, b = int(fx * 2 ** o), int(fy * 2 ** o)
        if a >= n or b >= n:
            break
        g = rng.random((b, a)).astype(np.float32)
        out += amp * _interp2(g, xs, a, b)
        tot += amp
        amp *= 0.5
    return out / tot


def _interp2(g, xs, a, b):
    fx, fy = xs * a, xs * b
    x0 = np.floor(fx).astype(int) % a
    y0 = np.floor(fy).astype(int) % b
    tx, ty = fx - np.floor(fx), fy - np.floor(fy)
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x1, y1 = (x0 + 1) % a, (y0 + 1) % b
    A, B, C, D = g[np.ix_(y0, x0)], g[np.ix_(y0, x1)], g[np.ix_(y1, x0)], g[np.ix_(y1, x1)]
    top = A + (B - A) * tx[None, :]
    bot = C + (D - C) * tx[None, :]
    return top + (bot - top) * ty[:, None]


def speckle(n, density, seed, size=1.0):
    """Sparse tileable dots (0..1)."""
    rng = np.random.default_rng(seed)
    m = (rng.random((n, n)) < density).astype(np.float32)
    k = max(1, int(size))
    for _ in range(k):
        m = np.maximum(m, (np.roll(m, 1, 0) + np.roll(m, 1, 1)) * 0.5)
    return m


def blur(img, r=1):
    out = img.copy()
    for _ in range(r):
        out = (out + np.roll(out, 1, 0) + np.roll(out, -1, 0) + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 5
    return out


def hexs(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def lerp_col(a, b, t):
    return a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]


def grid_cells(n, cols, rows, gap, stagger=0.0, seed=0):
    """Tile/plank grid: per-pixel cell id, distance to the cell edge (0..0.5) and a random per cell."""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    gy = yy * rows
    row = np.floor(gy).astype(int)
    rng = np.random.default_rng(seed)
    offs = (rng.random(rows) * stagger if stagger < 0 else (np.arange(rows) % 2) * stagger)
    gx = (xx * cols + offs[row % rows] * 1.0) % cols
    col = np.floor(gx).astype(int)
    fx, fy = gx - col, gy - row
    edge = np.minimum(np.minimum(fx, 1 - fx) / cols * n, np.minimum(fy, 1 - fy) / rows * n) / n   # in tile units
    cid = row * cols + col
    rnd = rng.random(rows * cols + 1)[cid]
    return cid, edge, rnd, fx, fy


# ----------------------------------------------------------------- generators: (albedo sRGB, height)

def painted_concrete(n, base="#B8B2A4", dark="#8D877A", seed=1, streaks=0.5):
    blot = fbm(n, 4, seed, 6, warp=0.3)
    fine = fbm(n, 64, seed + 1, 3)
    st = stretch_noise(n, 24, 2, seed + 2, 3)
    t = np.clip((blot - 0.5) * 1.3 + 0.62 - (st - 0.5) * streaks * 0.6, 0, 1)
    col = lerp_col(hexs(dark), hexs(base), t) * (0.94 + 0.12 * fine[..., None])
    pits = speckle(n, 0.004, seed + 3)
    col *= (1 - 0.25 * pits[..., None])
    h = 0.5 * fine + 0.3 * blot - 0.5 * pits
    return col, h


def plaster(n, base="#D9D2C2", seed=2, var=0.05):
    roll = fbm(n, 8, seed, 5, warp=0.5)
    fine = fbm(n, 96, seed + 1, 2)
    col = hexs(base)[None, None, :] * (1 - var + 2 * var * roll[..., None]) * (0.98 + 0.04 * fine[..., None])
    return col, 0.6 * fine + 0.4 * roll


def floor_tiles(n, a="#7E8C86", b="#73817B", grout="#4A524F", count=2, gap=0.012, seed=3, scuff=0.4, speck=0.0):
    cid, edge, rnd, fx, fy = grid_cells(n, count, count, gap, seed=seed)
    base = lerp_col(hexs(a), hexs(b), rnd)
    mott = fbm(n, 6, seed + 1, 5)
    base *= (0.93 + 0.12 * mott[..., None])
    if speck:
        sp = speckle(n, speck, seed + 4)
        base = base * (1 - 0.35 * sp[..., None]) + 0.3 * sp[..., None] * (speckle(n, 0.5, seed + 5)[..., None])
    sc = fbm(n, 12, seed + 2, 4, warp=0.6)
    base *= (1 - scuff * 0.18 * np.clip((sc - 0.55) * 4, 0, 1)[..., None])
    g = np.clip(edge / gap, 0, 1)
    bevel = np.clip(edge / (gap * 2.5), 0, 1)
    col = lerp_col(hexs(grout), np.array([0, 0, 0], np.float32), np.zeros_like(g))
    col = col * (1 - g[..., None]) + base * g[..., None]
    col *= (0.85 + 0.15 * bevel[..., None])
    h = 0.6 * bevel + 0.03 * mott
    return col, h


def wood_planks(n, light="#A57A4F", dark="#6E4A2C", planks=6, length=1, gap=0.004, seed=4):
    cid, edge, rnd, fx, fy = grid_cells(n, length, planks, gap, stagger=-1.0, seed=seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    grain = stretch_noise(n, 3, 90, seed + 1, 4)
    grain2 = stretch_noise(n, 2, 30, seed + 2, 3)
    t = np.clip((grain - 0.5) * 2.5 + (grain2 - 0.5) * 1.5 + 0.5 + (rnd - 0.5) * 0.6, 0, 1)
    col = lerp_col(hexs(dark), hexs(light), t)
    col *= (0.85 + 0.3 * rnd[..., None])
    lines = np.abs(stretch_noise(n, 4, 140, seed + 3, 2) - 0.5) < 0.02
    col *= (1 - 0.18 * lines[..., None])
    g = np.clip(edge / gap, 0, 1)
    col *= (0.35 + 0.65 * g[..., None])
    h = 0.5 * g + 0.15 * grain - 0.1 * lines
    return col, h


def acoustic_ceiling(n, base="#E3E0D6", count=2, seed=5):
    cid, edge, rnd, fx, fy = grid_cells(n, count, count, 0.004, seed=seed)
    holes = speckle(n, 0.012, seed + 1)
    worms = np.clip((stretch_noise(n, 60, 18, seed + 2, 2) - 0.72) * 6, 0, 1)
    col = hexs(base)[None, None, :] * (0.97 + 0.04 * rnd[..., None]) * (1 - 0.35 * holes[..., None]) * (1 - 0.2 * worms[..., None])
    g = np.clip(edge / 0.004, 0, 1)
    col *= (0.7 + 0.3 * g[..., None])
    return col, 0.5 * g - 0.4 * holes - 0.2 * worms


def roof_pavers(n, a="#8E8C86", b="#7C7A74", count=2, seed=6):
    col, h = floor_tiles(n, a, b, "#4E4C48", count=count, gap=0.008, seed=seed, scuff=0.9)
    stain = fbm(n, 3, seed + 3, 5, warp=0.8)
    moss = np.clip((fbm(n, 10, seed + 4, 4) - 0.62) * 5, 0, 1) * np.clip(0.5 - h, 0, 1) * 2
    col = col * (0.85 + 0.25 * stain[..., None])
    col = col * (1 - moss[..., None]) + hexs("#4E5A2E")[None, None, :] * moss[..., None]
    return col, h


def asphalt(n, base="#2D2E31", seed=7):
    agg = fbm(n, 220, seed, 2)
    big = fbm(n, 4, seed + 1, 5, warp=0.4)
    sp = speckle(n, 0.03, seed + 2)
    col = hexs(base)[None, None, :] * (0.8 + 0.4 * big[..., None]) * (0.85 + 0.3 * agg[..., None])
    col += 0.06 * sp[..., None]
    cr = np.abs(fbm(n, 6, seed + 3, 4, warp=1.0) - 0.5) < 0.006
    col *= (1 - 0.4 * cr[..., None])
    return col, 0.6 * agg + 0.3 * sp - 0.6 * cr


def pavers(n, a="#8B8780", b="#7D7972", seed=8):
    cid, edge, rnd, fx, fy = grid_cells(n, 4, 8, 0.004, stagger=0.5, seed=seed)
    base = lerp_col(hexs(b), hexs(a), rnd) * (0.9 + 0.2 * fbm(n, 30, seed + 1, 3)[..., None])
    g = np.clip(edge / 0.004, 0, 1)
    bev = np.clip(edge / 0.012, 0, 1)
    col = base * (0.4 + 0.6 * g[..., None]) * (0.85 + 0.15 * bev[..., None])
    return col, 0.7 * bev + 0.1 * fbm(n, 60, seed + 2, 2)


def dirt(n, a="#9C8466", b="#7A654C", seed=9):
    big = fbm(n, 4, seed, 6, warp=0.6)
    peb = speckle(n, 0.015, seed + 1, 2)
    fine = fbm(n, 128, seed + 2, 2)
    col = lerp_col(hexs(b), hexs(a), np.clip((big - 0.5) * 2 + 0.5, 0, 1)) * (0.9 + 0.2 * fine[..., None])
    col = col * (1 - 0.3 * peb[..., None]) + 0.15 * peb[..., None] * fine[..., None]
    return col, 0.5 * fine + 0.6 * peb + 0.2 * big


def grass(n, a="#5E7F35", b="#3D5A22", seed=10):
    blades = stretch_noise(n, 160, 40, seed, 3)
    big = fbm(n, 5, seed + 1, 5, warp=0.5)
    t = np.clip((blades - 0.5) * 2 + (big - 0.5) * 1.5 + 0.5, 0, 1)
    col = lerp_col(hexs(b), hexs(a), t)
    return col, blades


def kawara(n, base="#4C5157", seed=11, rows=8, cols=6):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    ridge = 0.5 + 0.5 * np.cos(2 * math.pi * xx * cols)
    fy = (yy * rows) % 1.0
    lap = np.clip(fy * 3, 0, 1) * np.clip((1 - fy) * 12, 0, 1)
    rnd = np.random.default_rng(seed).random(rows * cols * 4)
    cell = (np.floor(yy * rows) * cols + np.floor(xx * cols)).astype(int)
    col = hexs(base)[None, None, :] * (0.75 + 0.35 * ridge[..., None]) * (0.6 + 0.4 * lap[..., None])
    col *= (0.92 + 0.16 * rnd[cell][..., None])
    return col, 0.7 * ridge + 0.4 * lap


def siding(n, base="#C9C0AE", boards=10, seed=12):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    fy = (yy * boards) % 1.0
    shade = 0.75 + 0.25 * fy
    g = fbm(n, 6, seed, 4)
    col = hexs(base)[None, None, :] * shade[..., None] * (0.92 + 0.12 * g[..., None])
    return col, fy


def block_wall(n, base="#A39F95", seed=13):
    cid, edge, rnd, fx, fy = grid_cells(n, 2, 5, 0.006, stagger=0.5, seed=seed)
    col, h = painted_concrete(n, base, "#7D796F", seed + 1, streaks=1.0)
    g = np.clip(edge / 0.006, 0, 1)
    col = col * (0.45 + 0.55 * g[..., None]) * (0.93 + 0.1 * rnd[..., None])
    return col, 0.6 * np.clip(edge / 0.015, 0, 1) + 0.3 * h


def chalkboard(n, base="#24382C", seed=14):
    sm = fbm(n, 3, seed, 5, warp=1.2)
    wipe = stretch_noise(n, 2, 14, seed + 1, 4)
    col = hexs(base)[None, None, :] * (0.9 + 0.2 * wipe[..., None])
    col = col + np.clip(sm - 0.55, 0, 1)[..., None] * 0.25
    return col, 0.05 * sm


def cork(n, seed=15):
    g = speckle(n, 0.25, seed)
    f = fbm(n, 64, seed + 1, 3)
    col = lerp_col(hexs("#7A5634"), hexs("#B08559"), np.clip(f * 0.8 + g * 0.4, 0, 1))
    return col, 0.5 * f + 0.4 * g


def fabric_curtain(n, base="#6B1E22", seed=16):
    folds = stretch_noise(n, 10, 1, seed, 2)
    weave = (np.sin(np.arange(n)[None, :] * 2 * math.pi / 4) * np.sin(np.arange(n)[:, None] * 2 * math.pi / 4)) * 0.5 + 0.5
    col = hexs(base)[None, None, :] * (0.7 + 0.45 * folds[..., None]) * (0.95 + 0.05 * weave[..., None])
    return col, 0.8 * folds + 0.1 * weave


GENERATORS = {
    "painted_concrete": painted_concrete, "plaster": plaster, "floor_tiles": floor_tiles, "wood_planks": wood_planks,
    "acoustic_ceiling": acoustic_ceiling, "roof_pavers": roof_pavers, "asphalt": asphalt, "pavers": pavers,
    "dirt": dirt, "grass": grass, "kawara": kawara, "siding": siding, "block_wall": block_wall,
    "chalkboard": chalkboard, "cork": cork, "fabric_curtain": fabric_curtain,
}


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny, nz = -dx * strength, dy * strength, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack((nx / ln, ny / ln, nz / ln), -1) * 0.5 + 0.5


def tile_material(name, gen, res=1024, rough=0.7, metal=0.0, nstrength=6.0, rough_var=0.0, macro=0.0, **kw):
    """Material with a generated tileable base colour + normal map (cached as JPEGs). macro > 0
    breaks up the repetition on big surfaces with a slow, non-repeating light/dark variation."""
    if name in _mats:
        return _mats[name]
    from PIL import Image
    os.makedirs(K.BAKE_DIR, exist_ok=True)
    key = f"{TEX_VERSION}|{gen}|{res}|{nstrength}|{sorted(kw.items())}"
    jp = os.path.join(K.BAKE_DIR, f"tile_{name}.json")
    cp = os.path.join(K.BAKE_DIR, f"tile_{name}_C.jpg")
    npth = os.path.join(K.BAKE_DIR, f"tile_{name}_N.jpg")
    cached = False
    try:
        import json
        with open(jp) as fh:
            cached = json.load(fh).get("key") == key and os.path.exists(cp) and os.path.exists(npth)
    except (OSError, ValueError):
        pass
    if not cached:
        col, h = GENERATORS[gen](res, **kw)
        nrm = normal_from_height(h.astype(np.float32), nstrength)
        Image.fromarray((np.clip(col, 0, 1) * 255 + 0.5).astype(np.uint8)).save(cp, quality=90, subsampling=0)
        Image.fromarray((np.clip(nrm, 0, 1) * 255 + 0.5).astype(np.uint8)).save(npth, quality=94, subsampling=0)
        import json
        with open(jp, "w") as fh:
            json.dump({"key": key}, fh)
        print(f"  texture {name}")
    img_c = K.load_image(cp, "sRGB", reload=not cached)
    img_n = K.load_image(npth, "Non-Color", reload=not cached)
    mat, nt, out = U.new_material(name)
    g = K.NG(nt)
    b = g.node("ShaderNodeBsdfPrincipled", Roughness=rough, Metallic=metal)
    g.set(out.inputs["Surface"], b.outputs[0])
    tc = g.node("ShaderNodeTexImage", {"image": img_c})
    g.set(b.inputs["Base Color"], tc.outputs["Color"])
    if macro:
        co = g.node("ShaderNodeTexCoord")
        n1 = g.noise(co.outputs["Object"], 0.035, detail=3.0, rough=0.55)
        f = g.maprange(n1, 0.3, 0.7, 1.0 - macro, 1.0 + macro)
        g.set(b.inputs["Base Color"], g.scale(tc.outputs["Color"], f))
    if rough_var:
        r = g.maprange(tc.outputs["Color"], 0.0, 1.0, rough + rough_var, rough - rough_var)
        g.set(b.inputs["Roughness"], r)
    tn = g.node("ShaderNodeTexImage", {"image": img_n})
    nm = g.node("ShaderNodeNormalMap", Strength=1.0)
    g.set(nm.inputs["Color"], tn.outputs["Color"])
    g.set(b.inputs["Normal"], nm.outputs["Normal"])
    px = np.array(Image.open(cp).resize((8, 8))).reshape(-1, 3).mean(0) / 255
    mat.diffuse_color = (*U.srgb_to_linear(px), 1)
    mat.roughness = rough
    _mats[name] = mat
    return mat
