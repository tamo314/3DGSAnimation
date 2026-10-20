"""3DGS PLYを、箱(xmin,xmax,ymin,ymax,zmin,zmax)の内側のガウシアンだけに切り出す(キャラ周りの抽出。背景側の外れ値を除く)。
  python scripts/gaussian/crop_ply.py in.ply out.ply [--box -0.6,0.6,-0.6,0.6,-0.1,1.3] [--min-alpha 0.0]
"""
import argparse

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--box", default="-0.6,0.6,-0.6,0.6,-0.1,1.3")
ap.add_argument("--min-alpha", type=float, default=0.0)
ap.add_argument("--near", default=None, help="参照PLY(素の3DGSなど)。そのガウシアンから --dist 以内のものだけ残す(黒背景由来の外れ値を除く)")
ap.add_argument("--dist", type=float, default=0.02)
a = ap.parse_args()
b = open(a.src, "rb").read(20000)
h = b[: b.index(b"end_header") + 11]
hh = h.decode().split("\n")
n = int([l for l in hh if l.startswith("element vertex")][0].split()[-1])
names = [l.split()[-1] for l in hh if l.startswith("property")]
v = np.fromfile(a.src, dtype=np.dtype([(q, "<f4") for q in names]), offset=len(h), count=n)
x0, x1, y0, y1, z0, z1 = [float(t) for t in a.box.split(",")]
al = 1 / (1 + np.exp(-v["opacity"]))
k = (v["x"] > x0) & (v["x"] < x1) & (v["y"] > y0) & (v["y"] < y1) & (v["z"] > z0) & (v["z"] < z1) & (al >= a.min_alpha)
v = v[k]
if a.near:
    from scipy.spatial import cKDTree
    rb = open(a.near, "rb").read(20000)
    rh = rb[: rb.index(b"end_header") + 11]
    rhh = rh.decode().split("\n")
    rn = int([l for l in rhh if l.startswith("element vertex")][0].split()[-1])
    rnames = [l.split()[-1] for l in rhh if l.startswith("property")]
    r = np.fromfile(a.near, dtype=np.dtype([(q, "<f4") for q in rnames]), offset=len(rh), count=rn)
    ra = 1 / (1 + np.exp(-r["opacity"]))
    R = np.stack([r["x"], r["y"], r["z"]], 1)[ra > 0.3]
    d = cKDTree(R).query(np.stack([v["x"], v["y"], v["z"]], 1))[0]
    v = v[d < a.dist]
newh = h.decode().replace(f"element vertex {n}", f"element vertex {len(v)}").encode()
with open(a.dst, "wb") as f:
    f.write(newh)
    f.write(v.tobytes())
print("kept", len(v), "of", n)
