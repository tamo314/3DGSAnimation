"""T8: マスター描画(RGBA 2048²)から、3DGS学習用のCOLMAPデータセット(黒背景に合成したRGB)を作る。
  python scripts/gaussian/make_hq_dataset.py --master experiments/T8/master --out experiments/T8/data/hq2048 --types ring,upper,face,lower --size 2048
- split=train の視点だけを書く(testは評価専用で学習に使わない)。--split all で全部。
- 合成は直線アルファ→乗算済み(rgb*alpha)にしてから縮小する(縮小しても縁に暗い/明るいハローが出ない)。背景は黒(3DGSの既定背景と一致)。
- sparse/0 に text と bin を書く。points3D.ply はマスターの表面サンプル(灰色)。
"""
import argparse
import json
import math
import os
import shutil
import struct
import sys

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--master", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--types", default="ring,upper,face,lower")
ap.add_argument("--size", type=int, default=2048)
ap.add_argument("--sizes", default=None, help="マルチスケール学習用: 例 2048,1024,512。各視点を各解像度で別カメラ・別画像として書く(縮小表示時の折り返し対策)")
ap.add_argument("--split", default="train", choices=["train", "all"])
ap.add_argument("--max-views", type=int, default=0)
a = ap.parse_args()

# --master は複数指定可(カンマ区切り)。種類名(type)が重ならないものを結合する。points3D.plyは先頭のものを使う
masters = a.master.split(",")
metas = [json.load(open(os.path.join(m, "views.json"))) for m in masters]
meta = metas[0]
types = a.types.split(",")
views = []
for m, mt in zip(masters, metas):
    assert mt["size"] == meta["size"] and abs(mt["fx"] - meta["fx"]) < 1e-6
    views += [dict(v, master=m) for v in mt["views"] if v["type"] in types and (a.split == "all" or v["split"] == "train")]
if a.max_views:
    views = views[: a.max_views]
S0 = meta["size"]
sizes = [int(x) for x in a.sizes.split(",")] if a.sizes else [a.size]
fxs = [meta["fx"] * z / S0 for z in sizes]
sfx = lambda z: "" if len(sizes) == 1 else f"_s{z}"
os.makedirs(os.path.join(a.out, "images"), exist_ok=True)
sp = os.path.join(a.out, "sparse", "0")
os.makedirs(sp, exist_ok=True)


def premult(path, size):
    im = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255.0
    rgb = im[..., :3] * im[..., 3:4]
    if size != im.shape[0]:
        t = Image.fromarray((rgb * 255 + 0.5).astype(np.uint8)).resize((size, size), Image.BOX if S0 % size == 0 else Image.LANCZOS)
        return np.asarray(t)
    return (rgb * 255 + 0.5).astype(np.uint8)


for v in views:
    for z in sizes:
        Image.fromarray(premult(os.path.join(v["master"], "images", v["name"]), z)).save(os.path.join(a.out, "images", v["name"][:-4] + sfx(z) + ".png"))


def rotmat_to_quat(m):
    t = np.trace(m)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [(m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s]
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s]
    return np.array(q) / np.linalg.norm(q)


with open(os.path.join(sp, "cameras.txt"), "w") as f:
    f.write("# Camera list\n")
    for ci, (z, fx) in enumerate(zip(sizes, fxs)):
        f.write(f"{ci + 1} PINHOLE {z} {z} {fx:.6f} {fx:.6f} {z / 2:.6f} {z / 2:.6f}\n")
with open(os.path.join(sp, "images.txt"), "w") as f:
    f.write("# Image list\n")
    flip = np.diag([1.0, -1.0, -1.0])
    iid = 0
    for v in views:
      for ci, z in enumerate(sizes):
        iid += 1
        c2w = np.array(v["c2w_blender"])
        R = (c2w[:3, :3] @ flip).T
        t = -R @ c2w[:3, 3]
        q = rotmat_to_quat(R)
        f.write(f"{iid} {q[0]:.9f} {q[1]:.9f} {q[2]:.9f} {q[3]:.9f} {t[0]:.9f} {t[1]:.9f} {t[2]:.9f} {ci + 1} {v['name'][:-4] + sfx(z)}.png\n\n")
# points3D: マスターのply(表面サンプル)をtxtにもコピー
raw = open(os.path.join(masters[0], "points3D.ply"), "rb").read()
hdr_end = raw.index(b"end_header\n") + len(b"end_header\n")
n = int(raw[:hdr_end].split(b"element vertex ")[1].split()[0])
rec = np.frombuffer(raw[hdr_end:], dtype=[("p", "<f4", 3), ("n", "<f4", 3), ("c", "u1", 3)], count=n)
with open(os.path.join(sp, "points3D.txt"), "w") as f:
    f.write("# 3D point list\n")
    for i, p in enumerate(rec["p"]):
        f.write(f"{i + 1} {p[0]:.6f} {p[1]:.6f} {p[2]:.6f} 128 128 128 0.5\n")
shutil.copy(os.path.join(masters[0], "points3D.ply"), os.path.join(a.out, "sparse", "0", "points3D.ply"))
import subprocess
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "write_colmap_bin.py"), sp], check=True)
json.dump({"types": types, "sizes": sizes, "n_views": len(views)}, open(os.path.join(a.out, "dataset_info.json"), "w"))
print("done", a.out, len(views), "views", a.size)
