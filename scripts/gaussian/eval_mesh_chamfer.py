"""抽出メッシュ(PLY)と正解メッシュ(GLB, Blender座標へ変換)の表面間距離(Chamfer、片方向/双方向)を測る。単位 mm。
WSL t7: python scripts/gaussian/eval_mesh_chamfer.py --glb <GLB> --mesh <PLY> [--shift-z 0]
"""
import argparse

import numpy as np
import trimesh
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument("--glb", required=True)
ap.add_argument("--mesh", required=True)
ap.add_argument("--n", type=int, default=400000)
a = ap.parse_args()
T = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)
sc = trimesh.load(a.glb)
g = sc.to_geometry() if isinstance(sc, trimesh.Scene) else sc
gt = trimesh.Trimesh(g.vertices @ T.T, g.faces, process=False)
m = trimesh.load(a.mesh, process=False)
p_gt, _ = trimesh.sample.sample_surface(gt, a.n)
p_m, _ = trimesh.sample.sample_surface(m, a.n)
d_m2gt = cKDTree(p_gt).query(p_m)[0] * 1000
d_gt2m = cKDTree(p_m).query(p_gt)[0] * 1000
print(f"mesh verts {len(m.vertices)} faces {len(m.faces)}  GT faces {len(gt.faces)}")
print(f"mesh->GT  mean {d_m2gt.mean():.2f} mm  median {np.median(d_m2gt):.2f}  p95 {np.percentile(d_m2gt, 95):.2f}")
print(f"GT->mesh  mean {d_gt2m.mean():.2f} mm  median {np.median(d_gt2m):.2f}  p95 {np.percentile(d_gt2m, 95):.2f}  (カバレッジ)")
print(f"Chamfer(mean of both) {(d_m2gt.mean() + d_gt2m.mean()) / 2:.2f} mm")
