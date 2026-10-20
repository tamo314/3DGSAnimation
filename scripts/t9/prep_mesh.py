"""T9: Tripo メッシュ(GLB)を Blender 世界座標(足元原点・前方-Y・Z上)にそろえ、ガウシアンを結びつける用に簡略化して保存する。
頂点色は元テクスチャから取り、簡略化後の頂点へ最近傍で写す(ガウシアンの初期色に使う)。
  python scripts/t9/prep_mesh.py --glb <GLB> --out experiments/T9/mesh_60k.npz --faces 60000
出力 npz: verts(M,3) faces(T,3) vcolor(M,3 0..1)
"""
import argparse

import fast_simplification
import numpy as np
import trimesh
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument("--glb", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--faces", type=int, default=60000)
a = ap.parse_args()

sc = trimesh.load(a.glb)
m = sc.to_geometry() if isinstance(sc, trimesh.Scene) else sc
T = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)  # glTF(Y上) -> Blender(Z上、前方-Y)
V = np.asarray(m.vertices, dtype=np.float64) @ T.T
F = np.asarray(m.faces)
vc = np.asarray(m.visual.to_color().vertex_colors)[:, :3].astype(np.float32) / 255.0
print("original verts", len(V), "faces", len(F), "bbox", V.min(0).round(3), V.max(0).round(3))
ratio = 1.0 - a.faces / len(F)
Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=ratio)
print("simplified verts", len(Vs), "faces", len(Fs))
_, nn = cKDTree(V).query(Vs, k=1)
vcs = vc[nn]
np.savez_compressed(a.out, verts=Vs.astype(np.float32), faces=Fs.astype(np.int32), vcolor=vcs.astype(np.float32))
e = trimesh.Trimesh(Vs, Fs, process=False)
print("surface area m2", round(float(e.area), 3), "edge mean mm", round(float(np.linalg.norm(Vs[Fs[:, 0]] - Vs[Fs[:, 1]], axis=1).mean() * 1000), 2),
      "watertight", e.is_watertight)
# 元メッシュまでの距離(簡略化の誤差)
from trimesh.proximity import ProximityQuery
P, _ = trimesh.sample.sample_surface(e, 100000)
d = cKDTree(V).query(P)[0] * 1000
print("simplified->original vertex dist mm: median %.2f p95 %.2f max %.2f" % (np.median(d), np.percentile(d, 95), d.max()))
