"""Keep the saved .blend files small.

Before saving: images with the same pixels are merged into one (the ape textures come in with
every copy of the template), datablocks nothing uses are dropped, and big opaque textures that
were generated in Blender (packed as PNG) are re-stored as high-quality JPEG."""

import hashlib
import os
import re
import tempfile

import bpy
import numpy as np

JPEG_QUALITY = 95
MIN_PNG_BYTES = 256 * 1024
NORMAL_MAPS = re.compile(r"(^|_)ApeN\b")     # generated normal maps that may go to JPEG
_TMP = []


def _tmpdir():
    if not _TMP:
        _TMP.append(tempfile.mkdtemp(prefix="ak_pack_"))
    return _TMP[0]


def _pixels(img):
    w, h = img.size
    px = np.empty(w * h * img.channels, np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, img.channels)


def packed_mb():
    return sum(i.packed_file.size for i in bpy.data.images if i.packed_file) / 1e6


def _rank(img):
    """Which copy of a duplicate to keep: JPEG over PNG, then plain names over .001 copies."""
    pf = img.packed_file
    jpeg = pf is not None and bytes(pf.data[:2]) == b"\xff\xd8"
    return (not jpeg, bool(re.search(r"\.\d{3}$", img.name)), img.name)


def merge_duplicates():
    groups = {}
    for img in list(bpy.data.images):
        if img.type != "IMAGE" or 0 in img.size[:]:
            continue
        key = (tuple(img.size), img.colorspace_settings.name, img.alpha_mode,
               hashlib.sha1(_pixels(img).tobytes()).hexdigest())
        groups.setdefault(key, []).append(img)
        img.buffers_free()
    merged = 0
    for imgs in groups.values():
        if len(imgs) < 2:
            continue
        imgs.sort(key=_rank)
        for dup in imgs[1:]:
            dup.user_remap(imgs[0])
            bpy.data.images.remove(dup)
            merged += 1
    return merged


def _is_png(img):
    pf = img.packed_file
    return pf is not None and bytes(pf.data[:4]) == b"\x89PNG"


def _to_jpeg(img):
    from PIL import Image
    px = _pixels(img)
    if px.shape[2] == 4 and px[..., 3].min() < 1.0:
        return False                       # real alpha: stays PNG
    name = img.name
    path = os.path.join(_tmpdir(), re.sub(r"[^\w.-]", "_", name) + ".jpg")
    rgb = (np.clip(px[::-1, :, :3], 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(rgb).save(path, format="JPEG", quality=JPEG_QUALITY, subsampling=0)
    new = bpy.data.images.load(path)
    new.colorspace_settings.name = img.colorspace_settings.name
    new.pack()
    img.user_remap(new)
    bpy.data.images.remove(img)
    new.name = name
    new.filepath_raw = f"//textures/{os.path.basename(path)}"
    return True


def generated_to_jpeg():
    n = 0
    for img in list(bpy.data.images):
        if not _is_png(img) or img.packed_file.size < MIN_PNG_BYTES:
            continue
        cs = img.colorspace_settings.name
        if cs == "sRGB" or (cs == "Non-Color" and NORMAL_MAPS.search(img.name)):
            n += _to_jpeg(img)
    return n


def slim():
    """Merge duplicate images, purge unused data, store big generated textures as JPEG."""
    before = packed_mb()
    merged = merge_duplicates()
    purged = bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    jpeg = generated_to_jpeg()
    print(f"slim: merged {merged} duplicate images, purged {purged} unused datablocks, "
          f"{jpeg} textures to JPEG; packed images {before:.1f} -> {packed_mb():.1f} MB")
