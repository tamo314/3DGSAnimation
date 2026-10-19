"""キャラのシルエットマスク(アルファ)を5視点ぶん出力する(統計用)。  blender -b <lit_scene.blend> --python scripts/blender/render_char_masks.py -- <out_dir>"""
import os
import sys

import bpy

out = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "experiments/T5/masks")
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.film_transparent = True
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 1440, 1080
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
for o in bpy.data.objects:
    if o.name.startswith("background"):
        o.hide_render = True
for cam in [o for o in bpy.data.objects if o.type == "CAMERA"]:
    sc.camera = cam
    sc.render.filepath = os.path.join(out, cam.name + ".png")
    bpy.ops.render.render(write_still=True)
