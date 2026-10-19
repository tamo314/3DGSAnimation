"""背景PLYを世界座標(キャラ足元原点、縮尺S)に変換し、キャラ位置の地面高さと小道の中心(砂色の分布)を数値で出す。
  python scripts/blender/analyze_ground.py [--scale 1.0]
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gaussian"))
import spzply  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--ply", default=r"C:/Work/3DGSAnimation/assets/generated/background/forest_clearing_500k.ply")
ap.add_argument("--meta", default=r"C:/Work/3DGSAnimation/assets/generated/background/world_meta.json")
ap.add_argument("--spot", type=float, nargs=2, default=[0.0, 3.5])
a = ap.parse_args()
meta = json.load(open(a.meta, encoding="utf-8"))
k0 = meta["coordinates"]["metric_scale_factor"]
eye = meta["coordinates"]["ground_plane_offset"]

cl = spzply.read_ply(a.ply, "RDF")
p = cl.positions
w = np.stack([p[:, 0], p[:, 2], -p[:, 1]], 1) * k0 + np.array([-a.spot[0], -a.spot[1], eye])
alpha = 1 / (1 + np.exp(-cl.alphas))
rgb = np.clip(0.5 + 0.2820948 * cl.colors, 0, 1)
print("splats", len(w), "world bbox", w.min(0).round(1), w.max(0).round(1))

# 1) キャラ足元(半径0.25m)の地面高さ: 低い側の不透明スプラットのz
d = np.hypot(w[:, 0], w[:, 1])
m = (d < 0.25) & (alpha > 0.4) & (np.abs(w[:, 2]) < 1.0)
z = w[m, 2]
print("footprint r<0.25 n=%d  z percentiles 5/25/50/75/95:" % m.sum(), np.percentile(z, [5, 25, 50, 75, 95]).round(3))
# ground = 下側。2cm刻みのヒストグラム
h, e = np.histogram(z, bins=np.arange(-0.5, 1.0, 0.04))
print("z hist:", {round(float(e[i]), 2): int(h[i]) for i in range(len(h)) if h[i]})

# 2) 小道の中心: 地面付近(z -0.15〜0.25)で、y を 0 ±0.5 に絞り、x ごとに砂色の割合
def sandy(c):
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    return (r > g * 1.02) & (r > b * 1.15) & (r > 0.35)  # 茶〜砂。緑(苔・草)は g > r

print("x[m]  n  sand%  meanZ")
for yc in (-1.0, 0.0, 1.0, 2.5):
    print(f"-- y={yc:+.1f} (±0.4)")
    for x0 in np.arange(-2.0, 2.01, 0.25):
        mm = (np.abs(w[:, 1] - yc) < 0.4) & (np.abs(w[:, 0] - x0) < 0.125) & (alpha > 0.4) & (w[:, 2] > -0.3) & (w[:, 2] < 0.3)
        if mm.sum() < 20:
            print(f"{x0:+.2f}  {mm.sum():4d}")
            continue
        print(f"{x0:+.2f}  {mm.sum():4d}  {100*sandy(rgb[mm]).mean():5.0f}   {np.median(w[mm,2]):+.2f}")

# 3) キャラ位置の候補ごとの地面高さ(半径0.2m、不透明スプラットの中央値)と砂色率
print("\n候補位置  地面z  砂色%  n")
for y in (-0.5, 0.0, 0.5, 1.0):
    for x in (-0.25, 0.0, 0.25, 0.5, 0.75, 1.0):
        mm = (np.hypot(w[:, 0] - x, w[:, 1] - y) < 0.2) & (alpha > 0.4) & (np.abs(w[:, 2]) < 1.0)
        if mm.sum() < 20:
            print(f"({x:+.2f},{y:+.2f})  n={mm.sum()}")
            continue
        zz = w[mm, 2]
        print(f"({x:+.2f},{y:+.2f})  {np.median(zz):.3f}  {100*sandy(rgb[mm]).mean():4.0f}  {mm.sum()}")
