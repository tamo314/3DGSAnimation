"""T9: 同じ変形(deform.py)をTripoの元メッシュ(テクスチャ付き)に適用し、T8と同じ照明・カメラで描画する(変形後の正解)。
  blender --factory-startup -b --python scripts/t9/render_pose_ref.py -- --master <T8 master> --out <dir> --poses rest,lean,head --views 0000_ring.png,0064_ring.png [--size 1024] [--samples 128]
出力: <out>/<pose>_<view名>.png(RGBA、直線アルファ)
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "blender"))
import bpy  # noqa: E402
import mathutils  # noqa: E402
import numpy as np  # noqa: E402

import deform  # noqa: E402
import lighting  # noqa: E402
import spike_common as sc  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--master", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--poses", default="rest,lean,head")
ap.add_argument("--views", default="0000_ring.png")
ap.add_argument("--size", type=int, default=1024)
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--glb", default=r"C:/Work/3DGSAnimation/assets/generated/character/normalized/girl_healer.glb")
a = ap.parse_args(argv)
a.out = os.path.abspath(a.out)
os.makedirs(a.out, exist_ok=True)

meta = json.load(open(os.path.join(a.master, "views.json")))
views = {v["name"]: v for v in meta["views"]}
sc.init_gpu()
sc.clear_scene()
sc.set_render(a.size, a.size, engine="CYCLES", samples=a.samples)
scene = bpy.context.scene
scene.render.film_transparent = True
scene.render.filter_size = 1.0
scene.cycles.samples = a.samples
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPENIMAGEDENOISE"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type != "CPU"
scene.cycles.device = "GPU"

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=a.glb)
meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
lighting.setup(lighting.load_config())
rest = []
for o in meshes:
    n = len(o.data.vertices)
    v = np.empty(n * 3, dtype=np.float64)
    o.data.vertices.foreach_get("co", v)
    v = v.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    rest.append((o, v.copy(), mw))

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = meta["lens"]
cam_data.sensor_width = 36.0
cam_data.sensor_fit = "HORIZONTAL"
cam_data.clip_start = 0.01
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

for pname in a.poses.split(","):
    for o, v, mw in rest:
        w = v @ mw[:3, :3].T + mw[:3, 3]                       # ローカル→世界
        w2 = deform.pose(w, pname)
        loc = (w2 - mw[:3, 3]) @ np.linalg.inv(mw[:3, :3]).T   # 世界→ローカル
        o.data.vertices.foreach_set("co", loc.astype(np.float32).ravel())
        o.data.update()
    bpy.context.view_layer.update()
    for vn in a.views.split(","):
        cam.matrix_world = mathutils.Matrix(np.array(views[vn]["c2w_blender"]))
        bpy.context.view_layer.update()
        scene.render.filepath = os.path.join(a.out, f"{pname}_{vn}")
        bpy.ops.render.render(write_still=True)
        print("T9 rendered", pname, vn, flush=True)
print("T9_REF_DONE")
