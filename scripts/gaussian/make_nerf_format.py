"""render_char_dataset.py の出力(views.json + images/*.png)を NeRF-Synthetic 形式(transforms_{train,test}.json)に変換する。
GaussianShader(Inria 3DGS系)の Blender データセット読み込み用。物体中心を原点にずらす(座標の平行移動のみ)。
  python scripts/gaussian/make_nerf_format.py experiments/T7/data/char_scene experiments/T7/data/char_scene_nerf [--test-every 8]
"""
import argparse
import json
import math
import os
import shutil

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--test-every", type=int, default=8)
a = ap.parse_args()

v = json.load(open(os.path.join(a.src, "views.json")))
tz = v["target"][2]
fovx = 2 * math.atan(0.5 * v["size"] / v["fx"])
for split in ("train", "test"):
    os.makedirs(os.path.join(a.dst, split), exist_ok=True)
frames = {"train": [], "test": []}
for i, vw in enumerate(v["views"]):
    split = "test" if i % a.test_every == 0 else "train"
    c2w = vw["c2w_blender"]
    c2w[2][3] -= tz
    stem = os.path.splitext(vw["name"])[0]
    shutil.copy(os.path.join(a.src, "images", vw["name"]), os.path.join(a.dst, split, vw["name"]))
    frames[split].append({"file_path": f"./{split}/{stem}", "transform_matrix": c2w})
for split in ("train", "test"):
    json.dump({"camera_angle_x": fovx, "frames": frames[split]}, open(os.path.join(a.dst, f"transforms_{split}.json"), "w"), indent=1)
print("train", len(frames["train"]), "test", len(frames["test"]), "fovx", fovx)
