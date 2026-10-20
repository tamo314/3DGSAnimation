"""T7: MILoが背景から抽出したメッシュ(世界座標)の地面と、元の背景の地面の高さ・コライダー利用の可否を測る。
  WSL t7: python scripts/gaussian/eval_bg_mesh.py --mesh <mesh.ply> [--collider <World Labs collider.glb>] [--out <json>]
出力: 頂点数・面数、キャラ位置(0.4,0)半径0.25mの地面高さ(上向き面のz)、x∈[-3,3]×y∈[-1,6]の地面高さの分布と起伏、メッシュ全体の外れ(浮遊三角形の割合)。
"""
import argparse
import json

import numpy as np
import trimesh

ap = argparse.ArgumentParser()
ap.add_argument("--mesh", required=True)
ap.add_argument("--collider", default=None)
ap.add_argument("--meta", default="/mnt/c/Work/3DGSAnimation/assets/generated/background/world_meta.json")
ap.add_argument("--out", default=None)
a = ap.parse_args()
res = {}


def ground_stats(label, m):
    v, f = np.asarray(m.vertices), np.asarray(m.faces)
    tri = v[f]
    c = tri.mean(1)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
    up = n[:, 2] > 0.7
    r = {"verts": int(len(v)), "faces": int(len(f)), "bbox_min": v.min(0).round(2).tolist(), "bbox_max": v.max(0).round(2).tolist(),
         "frac_up_facing": float(up.mean())}
    d = np.hypot(c[:, 0] - 0.4, c[:, 1])
    sel = up & (d < 0.25) & (np.abs(c[:, 2]) < 1.0)
    if sel.sum():
        z = c[sel, 2]
        r["char_foot_ground_z"] = {"n": int(sel.sum()), "p5_p50_p95": np.percentile(z, [5, 50, 95]).round(3).tolist()}
    else:
        r["char_foot_ground_z"] = None
    # 地面の格子(0.5m)ごとの、上向き面の最低zの中央値 → 起伏
    box = up & (np.abs(c[:, 0]) < 3) & (c[:, 1] > -1) & (c[:, 1] < 6) & (c[:, 2] > -0.5) & (c[:, 2] < 1.5)
    gx = np.floor(c[box, 0] / 0.5).astype(int)
    gy = np.floor(c[box, 1] / 0.5).astype(int)
    cells = {}
    for x, y, z in zip(gx, gy, c[box, 2]):
        cells.setdefault((x, y), []).append(z)
    zs = np.array([np.min(v_) for v_ in cells.values()])
    r["ground_grid"] = {"cells": len(zs), "z_p5_p50_p95": np.percentile(zs, [5, 50, 95]).round(3).tolist(),
                        "z_std": float(zs.std())}
    # 浮遊(地面グリッドから高さ1m以上離れた小さな連結成分)はコンポーネント数で簡易評価
    comps = trimesh.graph.connected_components(m.face_adjacency, nodes=np.arange(len(f)), min_len=1)
    sizes = np.array([len(x) for x in comps])
    r["components"] = {"n": int(len(sizes)), "largest_frac": float(sizes.max() / len(f)),
                       "n_tiny(<100 faces)": int((sizes < 100).sum())}
    r["area_m2"] = float(area.sum())
    print(label, json.dumps(r, ensure_ascii=False))
    return r


res["milo"] = ground_stats("milo", trimesh.load(a.mesh, process=False))
if a.collider:
    sc = trimesh.load(a.collider)
    g = sc.to_geometry() if isinstance(sc, trimesh.Scene) else sc
    print("collider raw bbox", g.bounds.round(2).tolist())
    res["collider_raw_bbox"] = g.bounds.round(2).tolist()
    meta = json.load(open(a.meta, encoding="utf-8"))
    k0 = meta["coordinates"]["metric_scale_factor"]
    eye = meta["coordinates"]["ground_plane_offset"]
    v = np.asarray(g.vertices, dtype=np.float64)
    # 背景スプラットと同じ変換(RDF→世界、メートル換算 k0、元カメラを(0,-3.5,eye)へ)。コライダーが同じ座標系の前提
    w = np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1) * k0 + np.array([0.0, -3.5, eye])
    gm = trimesh.Trimesh(w, g.faces, process=False)
    res["collider_world"] = ground_stats("collider(世界座標へ変換)", gm)
if a.out:
    json.dump(res, open(a.out, "w"), indent=1, ensure_ascii=False)
