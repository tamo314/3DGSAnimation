"""各3DGS(PLY)のガウシアンの法線が、正解メッシュ(Tripo GLB)の面法線とどれだけ合うかを測る。
法線の候補: (a) 最小スケール軸(T5で不安定だった従来の推定) (b) PLYに学習済み法線がある場合(GaussianShader)はそれ。
符号は不定なので |cos| で評価(角度 = acos|n·n_gt|)。位置は正解メッシュ表面への最近点で対応づける。
WSLの t7 環境で実行: python scripts/gaussian/eval_normals.py --glb <GLB> --ply name=path[,shift_z] ...
"""
import argparse
import json

import numpy as np
import trimesh
from plyfile import PlyData
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument("--glb", required=True)
ap.add_argument("--out", default=None)
ap.add_argument("--ply", nargs="+", required=True, help="name=path[:shift_z]  (shift_z: PLY座標に足すz。GaussianShaderのNeRF形式は物体中心を原点に動かしている)")
ap.add_argument("--n-surface", type=int, default=600000)
a = ap.parse_args()

sc = trimesh.load(a.glb)
m = sc.dump(concatenate=True) if isinstance(sc, trimesh.Scene) else sc
# glTF(Y上) -> Blender(Z上, 前方-Y): (x, y, z) -> (x, -z, y)
T = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)
V = m.vertices @ T.T
mesh = trimesh.Trimesh(V, m.faces, process=False)
print("GT mesh bbox", mesh.bounds.tolist(), "faces", len(mesh.faces))
pts, fid = trimesh.sample.sample_surface(mesh, a.n_surface)
nrm = mesh.face_normals[fid]
tree = cKDTree(pts)


def quat_to_R(q):
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - w * z); R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y); R[:, 2, 1] = 2 * (y * z + w * x); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


res = {}
for spec in a.ply:
    name, rest = spec.split("=", 1)
    path, _, sz = rest.partition(":")
    shift = float(sz) if sz else 0.0
    v = PlyData.read(path)["vertex"]
    xyz = np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float64) + np.array([0, 0, shift])
    op = 1 / (1 + np.exp(-v["opacity"].astype(np.float64))) if "opacity" in v.data.dtype.names else np.ones(len(xyz))
    sc3 = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1).astype(np.float64))
    rot = np.stack([v["rot_0"], v["rot_1"], v["rot_2"], v["rot_3"]], 1).astype(np.float64)
    R = quat_to_R(rot)
    ax = np.argmin(sc3, axis=1)
    n_min = R[np.arange(len(R)), :, ax]
    srt = np.sort(sc3, axis=1)
    flat = srt[:, 0] / np.maximum(srt[:, 1], 1e-12)          # 0に近いほど薄い円盤
    d, idx = tree.query(xyz)
    sel = (op > 0.3) & (d < 0.02)                              # 表面から2cm以内の不透明ガウシアンだけ評価
    out = {"n_gaussians": int(len(xyz)), "n_eval": int(sel.sum()), "median_surface_dist_mm": float(np.median(d[sel]) * 1000)}

    def stats(n, tag, mask):
        c = np.abs(np.sum(n[mask] * nrm[idx[mask]], axis=1)).clip(0, 1)
        ang = np.degrees(np.arccos(c))
        out[tag] = {"median_deg": float(np.median(ang)), "mean_deg": float(ang.mean()), "frac_lt_30": float((ang < 30).mean()), "frac_lt_15": float((ang < 15).mean())}

    stats(n_min, "min_scale_axis", sel)
    stats(n_min, "min_scale_axis_flat(<0.3)", sel & (flat < 0.3))
    if "nx2" in v.data.dtype.names:
        n1 = np.stack([v["nx"], v["ny"], v["nz"]], 1).astype(np.float64)
        n2 = np.stack([v["nx2"], v["ny2"], v["nz2"]], 1).astype(np.float64)
        for tag, n in (("learned_normal(nx)", n1), ("learned_normal(nx2)", n2)):
            nn = np.linalg.norm(n, axis=1)
            if np.median(nn[sel]) > 1e-3:
                stats(n / np.maximum(nn[:, None], 1e-12), tag, sel)
    out["flatness_median(smin/smid)"] = float(np.median(flat[sel]))
    res[name] = out
    print(name, json.dumps(out, ensure_ascii=False))
if a.out:
    json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)
