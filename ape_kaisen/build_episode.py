"""Build the animated episode: ape_kaisen_ep1.blend.

Each part (location) is built in its own clean file first, then the parts are appended as
scenes into the episode file, followed by an "Edit" scene that strings them together in the
Video Sequencer (with title and subtitles).

Run:  python3 build_episode.py [hospital] [school]      (default: all)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

import build_sets as BS  # noqa: E402
from ak import episode as E  # noqa: E402
from ak import render as R  # noqa: E402

PARTS_DIR = os.path.join(HERE, "parts")
PARTS = {
    "hospital": ("Hospital", E.hospital_part, 0.6),
    "school": ("School", E.school_part, 1.3),
}


def build_part(key):
    name, fn, exposure = PARTS[key]
    BS.fresh_file()
    scene = bpy.context.scene
    scene.name = name
    scene.view_settings.exposure = exposure          # before the animation: flashes key around it
    fn(scene)
    R.setup(scene, preview=False, res=(1920, 1080), samples=64)
    R.compositor(scene, bloom=0.9, threshold=1.0)
    os.makedirs(PARTS_DIR, exist_ok=True)
    path = os.path.join(PARTS_DIR, f"ep1_{key}.blend")
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("saved", path, round(os.path.getsize(path) / 1e6, 1), "MB")
    return path


# The cut: (scene, first frame, last frame) in story order; "TITLE" is the title card.
EDIT = [
    ("School", 1, 252),
    ("TITLE", 0, 72),
    ("Hospital", 1, 600),
    ("School", 253, 1440),
]
SUBS = [   # (scene, first, last, speaker, line) in each scene's own frames
    ("School", 31, 76, "GOJO (phone)", "Megumi~ That special-grade cursed object is at Sugisawa High. Go get it."),
    ("School", 78, 108, "MEGUMI", "...Tonight? Fine."),
    ("Hospital", 20, 74, "YUJI", "Gramps, the nurse says you're not eating."),
    ("Hospital", 82, 128, "GRANDPA", "Shut up. Go to your club."),
    ("Hospital", 143, 207, "GRANDPA", "Yuji... you're strong."),
    ("Hospital", 215, 287, "GRANDPA", "So help people. Don't die alone like me."),
    ("School", 261, 302, "SASAKI", "It's real. An actual cursed object."),
    ("School", 303, 326, "IGUCHI", "Should we really open it...?"),
    ("School", 640, 674, "", "AAAAAH!!"),
    ("School", 961, 996, "SASAKI", "HELP!!"),
    ("School", 987, 1008, "MEGUMI", "Divine Dogs!"),
    ("School", 1199, 1224, "MEGUMI", "Don't! That thing is poison!"),
    ("School", 1335, 1378, "SUKUNA", "Hahahaha...!"),
]


def _set(obj, **kw):
    for k, v in kw.items():
        if hasattr(obj, k):
            try:
                setattr(obj, k, v)
            except (TypeError, ValueError, AttributeError):
                pass


def text_strip(sed, name, text, channel, start, length, size, y, color=(1, 1, 1, 1), box=False):
    t = sed.strips.new_effect(name=name, type="TEXT", channel=channel, frame_start=start, length=length)
    t.text = text
    _set(t, font_size=size, color=color, use_shadow=True, shadow_color=(0, 0, 0, 0.9), location=(0.5, y),
         alignment_x="CENTER", anchor_x="CENTER", anchor_y="BOTTOM", use_box=box, box_color=(0, 0, 0, 0.55),
         box_margin=0.012)
    return t


def assemble():
    """ape_kaisen_ep1.blend: both parts as scenes + the Edit scene that plays the episode."""
    BS.fresh_file()
    edit = bpy.context.scene
    edit.name = "Edit"
    for key, (name, _, _) in PARTS.items():
        path = os.path.join(PARTS_DIR, f"ep1_{key}.blend")
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.scenes = [name]
    edit.render.resolution_x, edit.render.resolution_y, edit.render.fps = 1920, 1080, 24
    sed = edit.sequence_editor_create()
    start = 1
    where = {}
    for i, (name, a, b) in enumerate(EDIT):
        if name == "TITLE":
            n = b - a
            c = sed.strips.new_effect(name="Black", type="COLOR", channel=1, frame_start=start, length=n)
            c.color = (0.0, 0.0, 0.0)
            text_strip(sed, "Title", "APE KAISEN", 3, start + 6, n - 10, 150, 0.5, color=(0.95, 0.15, 0.2, 1))
            text_strip(sed, "Subtitle", "Episode 1  -  Ryomen Sukuna", 4, start + 18, n - 22, 52, 0.36)
            start += n
            continue
        sc = bpy.data.scenes[name]
        st = sed.strips.new_scene(name=f"{name}_{i}", scene=sc, channel=1, frame_start=start - (a - sc.frame_start))
        st.frame_offset_start = a - sc.frame_start
        st.frame_offset_end = max(0, sc.frame_end - b)
        where.setdefault(name, []).append((a, b, start))
        start += b - a + 1
    for k, (name, f0, f1, who, line) in enumerate(SUBS):
        for a, b, e in where.get(name, []):
            if a <= f0 <= b:
                t0 = e + (f0 - a)
                text = f"{who}:  {line}" if who else line
                text_strip(sed, f"Sub{k:02d}", text, 5 + k % 2, t0, f1 - f0, 40, 0.06, box=True)
    edit.frame_start, edit.frame_end = 1, start - 1
    ims = edit.render.image_settings
    _set(ims, media_type="VIDEO")
    _set(ims, file_format="FFMPEG")
    _set(edit.render.ffmpeg, format="MPEG4", codec="H264", constant_rate_factor="HIGH")
    edit.render.filepath = "//render/ape_kaisen_ep1.mp4"
    path = os.path.join(HERE, "ape_kaisen_ep1.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("saved", path, round(os.path.getsize(path) / 1e6, 1), "MB,", edit.frame_end, "frames")


if __name__ == "__main__":
    keys = [k for k in sys.argv[1:] if k in PARTS]
    if not sys.argv[1:]:
        keys = list(PARTS)
    for k in keys:
        build_part(k)
    if not sys.argv[1:] or "assemble" in sys.argv[1:]:
        assemble()
