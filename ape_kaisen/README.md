# Ape Kaisen

Jujutsu Kaisen episode 1 remade with Gorilla Tag apes, built entirely in Blender.

## The .blend files

Saved with **Blender 4.5 LTS**, so they open in Blender 4.5 and every newer version (files saved
with a newer Blender than yours open empty with an "expect loss of data" warning).

Every file opens looking through its camera in Solid mode with the textures showing (instant to
load). Press **Z → Rendered** in the 3D view to see the real lighting.

`ape_kaisen_ep1.blend` is the animated episode. It opens on the **School** scene (the night: press
play, cameras switch at the timeline markers). **Hospital** is the sunset scene. **Edit** is the
whole episode cut together in the Video Sequencer with the title card, subtitles and sound: switch
to it (scene dropdown, top right) and render the animation to get the MP4.

| File | What's in it |
| --- | --- |
| `ape_kaisen_school.blend` | Sugisawa High No. 3 at night: building, 2F hallway, 3F occult club room, rooftop, schoolyard, street, houses, city and moon. Cameras: `Cam_Yard`, `Cam_Street_Pole`, `Cam_Rooftop`, `Cam_Hallway`, `Cam_Clubroom`. |
| `ape_kaisen_hospital.blend` | Grandpa's hospital room at sunset, with Grandpa in bed and Yuji on the stool. Cameras: `Cam_Wide`, `Cam_Bedside`, `Cam_Monitor`. |
| `ape_kaisen_ep1.blend` | The animated episode 1 (see above). |
| `ape_kaisen_props.blend` | Every prop on one studio floor, each marked as an asset (open the Asset Browser to drag them into other files). |

All textures are packed into the files, and the files are set up for EEVEE.

## How the models are made

The props follow the style of the reference game assets (bench, hay bale, fall trees, candle):

* chunky shapes with a chamfer on every hard edge, so edges catch the light;
* nothing is perfectly straight: every part gets a slight hand-made wobble;
* one painted base-colour map and one normal map per prop, baked from procedural "painters"
  (wood grain, chipped paint, brushed metal, fabric weave, wax, bark, leaves) with ambient
  occlusion and edge highlights painted in.

Walls, floors, roofs and roads use tileable painted textures (concrete, plaster, floor tiles,
acoustic ceiling boards, wood planks, roof pavers, asphalt, pavers, dirt, grass, roof tiles,
block walls). Signs, notices, posters, the vending machines, the chalkboard and the magic circle
are printed images with real Japanese text.

The user's own models (`assets/ref/`: bench, candle, two fall trees, hay bale) are used in the
sets: benches on the roof and in the yard, candles on the club-room table, fall trees around the
school. Their original texture files weren't included, so they are re-textured with the same
painters; drop the original textures in and relink them if you prefer those.

## Rebuilding

```
python3 build_sets.py                 # school, hospital and props
python3 build_sets.py school          # just one
```

Needs the `bpy` module (`pip install bpy==4.5.*`, Blender 4.5 as a Python module, so the files open
in Blender 4.5 and newer). `python3 build_episode.py` builds the episode. Baked textures are cached in
`assets/baked/` (keyed on each prop's geometry and paint settings), so a rebuild only re-bakes
props that changed.

Code: `ak/kit.py` (modelling + baking kit), `ak/assets.py` / `ak/assets_hosp.py` (prop library),
`ak/refassets.py` (the user's models), `ak/texgen.py` (tileable textures), `ak/decals.py`
(printed images), `ak/school.py` / `ak/hospital.py` (the sets), `ak/cast.py` /
`ak/characters.py` / `ak/motion.py` (apes and their hand-walking animation).
