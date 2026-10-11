"""Printed and painted images for signs, notices, posters, screens and boards (PIL, cached as
JPEG/PNG in assets/baked/). decal_material() wraps one in a material; kit surfaces of kind
"decal" map each part's face onto the whole image."""

import math
import os
import random

import bpy
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import kit as K
from . import util as U

JP = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
LATIN = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
DECAL_VERSION = 1
_mats = {}


def reset():
    _mats.clear()


def font(size, path=JP):
    return ImageFont.truetype(path, size)


def _paper(w, h, tint=(244, 241, 232), seed=0):
    rng = np.random.default_rng(seed)
    a = np.ones((h, w, 3), np.float32) * np.array(tint, np.float32)
    a += rng.normal(0, 2.5, (h, w, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    a *= (1 - 0.06 * ((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _text_block(d, x, y, w, rows, rng, col=(70, 70, 75), h=9, gap=16):
    for r in range(rows):
        ln = w * (rng.uniform(0.55, 1.0) if r < rows - 1 else rng.uniform(0.2, 0.6))
        cx = x
        while cx < x + ln:
            seg = rng.uniform(18, 60)
            d.rectangle((cx, y + r * gap, min(cx + seg, x + ln), y + r * gap + h), fill=col)
            cx += seg + rng.uniform(4, 9)


# ----------------------------------------------------------------- generators (return PIL.Image)

NOTICE_TITLES = ["お知らせ", "保健だより", "図書室だより", "進路説明会", "部員募集", "生徒会通信", "文化祭のお知らせ", "防災訓練"]


def notice(seed=0):
    rng = random.Random(seed)
    w, h = 512, 724
    im = _paper(w, h, seed=seed)
    d = ImageDraw.Draw(im)
    accent = rng.choice([(200, 40, 40), (30, 80, 170), (30, 120, 60), (210, 120, 20)])
    d.rectangle((30, 30, w - 30, 120), fill=accent)
    d.text((w / 2, 75), rng.choice(NOTICE_TITLES), font=font(56), fill=(255, 255, 255), anchor="mm")
    _text_block(d, 50, 160, w - 100, 6, rng)
    if rng.random() < 0.6:
        d.rectangle((50, 280, w - 50, 470), outline=(60, 60, 60), width=3)
        for k in range(1, 4):
            d.line((50, 280 + k * 47, w - 50, 280 + k * 47), fill=(90, 90, 90), width=2)
        d.line((190, 280, 190, 470), fill=(90, 90, 90), width=2)
        _text_block(d, 60, 295, 110, 4, rng, h=8, gap=47)
        _text_block(d, 205, 295, w - 270, 4, rng, h=8, gap=47)
    else:
        d.ellipse((150, 290, 360, 470), outline=accent, width=6)
        d.text((255, 380), rng.choice(["!", "?", "★"]), font=font(110), fill=accent, anchor="mm")
    _text_block(d, 50, 510, w - 100, 7, rng)
    if rng.random() < 0.5:
        d.ellipse((w - 140, h - 140, w - 60, h - 60), outline=(200, 30, 30), width=5)
        d.text((w - 100, h - 100), "印", font=font(44), fill=(200, 30, 30), anchor="mm")
    return im


POSTERS = [("廊下を走るな", (230, 70, 50), (255, 235, 120)), ("手洗い・うがい", (40, 140, 210), (240, 250, 255)),
           ("あいさつ運動", (60, 170, 90), (250, 255, 235)), ("夢に向かって", (240, 160, 40), (40, 40, 80)),
           ("ゴミは持ち帰ろう", (120, 80, 180), (250, 245, 255)), ("交通安全", (220, 200, 40), (30, 30, 30))]


def poster(idx=0):
    title, bg, fg = POSTERS[idx % len(POSTERS)]
    rng = random.Random(idx + 40)
    w, h = 512, 724
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    for _ in range(14):
        r = rng.uniform(20, 90)
        x, y = rng.uniform(0, w), rng.uniform(220, h)
        c = tuple(int(min(255, v * rng.uniform(0.8, 1.25))) for v in bg)
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    size = min(88, int((w - 70) / max(1, len(title))))
    d.text((w / 2, 130), title, font=font(size), fill=fg, anchor="mm", stroke_width=4, stroke_fill=(30, 30, 30))
    d.rounded_rectangle((60, 420, w - 60, h - 70), radius=30, fill=(255, 255, 255))
    _text_block(d, 90, 460, w - 180, 6, rng, col=(80, 80, 90), gap=26)
    d.text((w / 2, h - 35), "杉沢第三高等学校 生徒会", font=font(26), fill=fg, anchor="mm")
    return im


def plate(text, w=512, h=192, bg=(246, 246, 242), fg=(25, 25, 30), size=110, border=(60, 60, 60)):
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    d.rectangle((6, 6, w - 7, h - 7), outline=border, width=8)
    size = min(size, int((w - 50) / max(1, len(text))))
    d.text((w / 2, h / 2 + 4), text, font=font(size), fill=fg, anchor="mm")
    return im


def vplate(text, w=192, h=800):
    """Cast bronze school-name plate, text running top to bottom."""
    rng = np.random.default_rng(5)
    a = np.ones((h, w, 3), np.float32) * np.array((150, 112, 58), np.float32)
    a *= (0.85 + 0.3 * rng.random((h, w, 1)) ** 4)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rectangle((8, 8, w - 9, h - 9), outline=(95, 68, 30), width=10)
    step = (h - 60) / len(text)
    size = int(min(w - 50, step * 0.92))
    for k, ch in enumerate(text):
        y = 30 + step * (k + 0.5)
        d.text((w / 2 + 3, y + 3), ch, font=font(size), fill=(70, 48, 20), anchor="mm")
        d.text((w / 2, y), ch, font=font(size), fill=(235, 205, 140), anchor="mm")
    return im


def exit_sign():
    w, h = 512, 256
    im = Image.new("RGB", (w, h), (30, 175, 90))
    d = ImageDraw.Draw(im)
    d.rectangle((14, 14, 240, h - 14), fill=(250, 255, 250))
    # running man (pictogram) and the door
    d.rectangle((150, 40, 225, h - 40), fill=(30, 175, 90))
    g = (30, 175, 90)
    d.ellipse((70, 40, 104, 74), fill=g)
    d.line((88, 80, 70, 150), fill=g, width=22)
    d.line((76, 100, 120, 125), fill=g, width=16)
    d.line((80, 100, 45, 85), fill=g, width=16)
    d.line((70, 150, 110, 200), fill=g, width=18)
    d.line((70, 150, 35, 190), fill=g, width=18)
    d.text((375, 95), "非常口", font=font(72), fill=(250, 255, 250), anchor="mm")
    d.text((375, 180), "EXIT", font=font(64, LATIN), fill=(250, 255, 250), anchor="mm")
    return im


def vending_front(seed=0):
    rng = random.Random(seed)
    w, h = 512, 1024
    im = Image.new("RGB", (w, h), (235, 238, 240))
    d = ImageDraw.Draw(im)
    brand = rng.choice([((200, 30, 40), "COLD DRINKS"), ((20, 90, 180), "つめた～い"), ((30, 140, 70), "お茶")])
    d.rectangle((0, 0, w, 120), fill=brand[0])
    d.text((w / 2, 60), brand[1], font=font(60), fill=(255, 255, 255), anchor="mm")
    cols = [(220, 40, 40), (40, 90, 200), (250, 200, 40), (60, 160, 80), (240, 240, 240), (120, 70, 40),
            (250, 120, 30), (30, 30, 30), (180, 60, 160)]
    for r in range(3):
        y0 = 150 + r * 190
        d.rectangle((24, y0 - 10, w - 24, y0 + 165), fill=(250, 250, 252))
        for k in range(6):
            x0 = 40 + k * 75
            c = rng.choice(cols)
            if rng.random() < 0.5:                  # can
                d.rounded_rectangle((x0, y0 + 30, x0 + 52, y0 + 125), radius=8, fill=c)
                d.rectangle((x0 + 6, y0 + 60, x0 + 46, y0 + 90), fill=(255, 255, 255))
            else:                                    # bottle
                d.rounded_rectangle((x0 + 8, y0 + 5, x0 + 44, y0 + 30), radius=6, fill=(230, 230, 230))
                d.rounded_rectangle((x0, y0 + 25, x0 + 52, y0 + 125), radius=12, fill=c)
                d.rectangle((x0, y0 + 60, x0 + 52, y0 + 92), fill=(255, 255, 255))
            d.rectangle((x0 - 2, y0 + 138, x0 + 54, y0 + 160), fill=(30, 30, 30))
            d.text((x0 + 26, y0 + 149), f"{rng.choice([100, 120, 130, 150, 160])}", font=font(18, LATIN),
                   fill=(255, 80, 80), anchor="mm")
    d.rectangle((24, 740, w - 24, 1000), fill=(60, 64, 70))
    d.rectangle((60, 860, w - 60, 960), fill=(20, 20, 22))
    d.rectangle((380, 760, 470, 830), fill=(200, 200, 200))
    return im


def chalkboard_writing():
    w, h = 2048, 640
    im = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(im)
    chalk = (235, 235, 225)
    d.text((80, 60), "オカルト研究会", font=font(150), fill=chalk)
    d.text((100, 250), "今週の活動：呪物の封印について", font=font(64), fill=chalk)
    d.text((100, 340), "・百葉箱の中の箱 → 開けるな！！", font=font(56), fill=(240, 200, 200))
    d.text((100, 420), "・深夜 0時 屋上集合", font=font(56), fill=chalk)
    d.text((100, 500), "・お札は剥がさないこと", font=font(56), fill=(200, 220, 245))
    cx, cy, r = 1650, 330, 230
    pts = [(cx + r * math.sin(a), cy - r * math.cos(a)) for a in (2 * math.pi * k / 5 for k in range(5))]
    d.ellipse((cx - r - 25, cy - r - 25, cx + r + 25, cy + r + 25), outline=chalk, width=10)
    for k in range(5):
        d.line((pts[k], pts[(k + 2) % 5]), fill=chalk, width=10)
    d.line((1250, 560, 1420, 470), fill=chalk, width=8)
    d.text((1180, 560), "呪", font=font(90), fill=(240, 120, 120))
    arr = np.asarray(im).astype(np.float32)
    rng = np.random.default_rng(3)
    arr *= (0.55 + 0.45 * rng.random(arr.shape[:2]))[..., None]           # chalk is grainy
    return Image.fromarray(arr.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))


def magic_circle():
    w = 1024
    im = _paper(w, w, tint=(232, 222, 196), seed=9)
    d = ImageDraw.Draw(im)
    ink = (110, 20, 20)
    c = w / 2
    for r, wd in ((470, 8), (440, 4), (300, 6), (180, 4)):
        d.ellipse((c - r, c - r, c + r, c + r), outline=ink, width=wd)
    for k in range(6):
        a = math.radians(60 * k)
        b = math.radians(60 * k + 120)
        d.line(((c + 440 * math.cos(a), c + 440 * math.sin(a)), (c + 440 * math.cos(b), c + 440 * math.sin(b))),
               fill=ink, width=5)
    runes = "封呪滅魂縛祓鬼宿儺怨"
    for k in range(20):
        a = 2 * math.pi * k / 20
        d.text((c + 370 * math.cos(a), c + 370 * math.sin(a)), runes[k % len(runes)], font=font(46), fill=ink,
               anchor="mm")
    d.text((c, c), "封", font=font(220), fill=ink, anchor="mm")
    return im


def painting():
    w, h = 768, 512
    im = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        d.line((0, y, w, y), fill=(int(120 + 120 * t), int(170 + 50 * t), int(225 - 40 * t)))
    d.polygon([(0, 330), (180, 160), (330, 300), (480, 120), (768, 340), (768, 512), (0, 512)], fill=(80, 110, 140))
    d.polygon([(410, 175), (480, 120), (545, 180), (515, 170), (480, 190), (450, 172)], fill=(245, 245, 250))
    d.polygon([(0, 400), (250, 330), (520, 390), (768, 350), (768, 512), (0, 512)], fill=(90, 140, 70))
    d.ellipse((600, 60, 680, 140), fill=(255, 235, 170))
    for k in range(9):
        x = 40 + k * 85
        d.polygon([(x, 440), (x + 22, 360), (x + 44, 440)], fill=(50, 95, 50))
    return im.filter(ImageFilter.GaussianBlur(1.5))


def clock_face():
    w = 512
    im = Image.new("RGB", (w, w), (248, 248, 244))
    d = ImageDraw.Draw(im)
    c = w / 2
    for k in range(60):
        a = 2 * math.pi * k / 60
        r0 = 225 if k % 5 else 205
        d.line(((c + r0 * math.sin(a), c - r0 * math.cos(a)), (c + 240 * math.sin(a), c - 240 * math.cos(a))),
               fill=(30, 30, 30), width=8 if k % 5 == 0 else 3)
    for k in range(1, 13):
        a = 2 * math.pi * k / 12
        d.text((c + 170 * math.sin(a), c - 170 * math.cos(a)), str(k), font=font(54, LATIN), fill=(30, 30, 30),
               anchor="mm")
    return im


def ecg_bezel():
    w, h = 512, 384
    im = Image.new("RGB", (w, h), (12, 16, 14))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 32):
        d.line((x, 0, x, h), fill=(18, 34, 26), width=1)
    for y in range(0, h, 32):
        d.line((0, y, w, y), fill=(18, 34, 26), width=1)
    d.text((440, 40), "HR", font=font(28, LATIN), fill=(60, 230, 110))
    d.text((440, 90), "72", font=font(56, LATIN), fill=(60, 230, 110))
    d.text((440, 200), "SpO2", font=font(24, LATIN), fill=(80, 200, 240))
    d.text((440, 245), "97", font=font(52, LATIN), fill=(80, 200, 240))
    return im


GENERATORS = {"notice": notice, "poster": poster, "plate": plate, "vplate": vplate, "exit_sign": exit_sign,
              "vending_front": vending_front, "chalkboard_writing": chalkboard_writing,
              "magic_circle": magic_circle, "painting": painting, "clock_face": clock_face, "ecg_bezel": ecg_bezel}


def image(name, gen, *args, **kw):
    """Generate (or load the cached) decal image and pack it."""
    os.makedirs(K.BAKE_DIR, exist_ok=True)
    path = os.path.join(K.BAKE_DIR, f"decal_{name}.jpg")
    stamp = os.path.join(K.BAKE_DIR, f"decal_{name}.json")
    key = f"{DECAL_VERSION}|{gen}|{args}|{sorted(kw.items())}"
    fresh = True
    try:
        import json
        with open(stamp) as fh:
            fresh = json.load(fh).get("key") != key or not os.path.exists(path)
    except (OSError, ValueError):
        pass
    if fresh:
        GENERATORS[gen](*args, **kw).convert("RGB").save(path, quality=92, subsampling=0)
        import json
        with open(stamp, "w") as fh:
            json.dump({"key": key}, fh)
    return K.load_image(path, "sRGB", reload=fresh)


def decal_material(name, img, rough=0.6, emit=0.0, metal=0.0, alpha_black=False):
    """Image on a part's face. emit > 0 makes it glow (screens, lit signs)."""
    if name in _mats:
        return _mats[name]
    mat, nt, out = U.new_material(name)
    g = K.NG(nt)
    b = g.node("ShaderNodeBsdfPrincipled", Roughness=rough, Metallic=metal)
    g.set(out.inputs["Surface"], b.outputs[0])
    t = g.node("ShaderNodeTexImage", {"image": img, "extension": "EXTEND"})
    g.set(b.inputs["Base Color"], t.outputs["Color"])
    if emit:
        g.set(b.inputs["Emission Color"], t.outputs["Color"])
        b.inputs["Emission Strength"].default_value = emit
    if alpha_black:          # chalk / ink on a transparent layer
        bw = g.node("ShaderNodeRGBToBW")
        g.set(bw.inputs["Color"], t.outputs["Color"])
        g.set(b.inputs["Alpha"], g.maprange(bw.outputs["Val"], 0.03, 0.25))
        for attr, val in (("surface_render_method", "DITHERED"),):
            if hasattr(mat, attr):
                setattr(mat, attr, val)
    px = np.zeros(4)
    mat.diffuse_color = (0.8, 0.8, 0.8, 1)
    _mats[name] = mat
    return mat
