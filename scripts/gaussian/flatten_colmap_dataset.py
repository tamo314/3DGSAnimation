"""RGBA の images/*.png を単色背景に合成したRGB画像にして、COLMAPデータセット(sparse/0 付き)を別フォルダに作る。
Inria系3DGSのCOLMAPリーダーはαを使わないため、背景は黒に合成しておく(既定の背景色=黒と一致)。マスクは masks/ に保存。
  python scripts/gaussian/flatten_colmap_dataset.py experiments/T7/data/char_scene experiments/T7/data/char_scene_black [--bg 0]
"""
import argparse
import os
import shutil

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--bg", type=int, default=0, help="背景の灰色値(0=黒, 255=白)")
a = ap.parse_args()

os.makedirs(os.path.join(a.dst, "images"), exist_ok=True)
os.makedirs(os.path.join(a.dst, "masks"), exist_ok=True)
if os.path.exists(os.path.join(a.dst, "sparse")):
    shutil.rmtree(os.path.join(a.dst, "sparse"))
shutil.copytree(os.path.join(a.src, "sparse"), os.path.join(a.dst, "sparse"))
for f in sorted(os.listdir(os.path.join(a.src, "images"))):
    im = np.asarray(Image.open(os.path.join(a.src, "images", f)).convert("RGBA")).astype(np.float32) / 255.0
    al = im[..., 3:4]
    rgb = im[..., :3] * al + (a.bg / 255.0) * (1 - al)
    Image.fromarray((rgb * 255 + 0.5).astype(np.uint8)).save(os.path.join(a.dst, "images", f))
    Image.fromarray((al[..., 0] * 255 + 0.5).astype(np.uint8)).save(os.path.join(a.dst, "masks", f))
print("done", a.dst)
