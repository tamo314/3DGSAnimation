"""描画スパイク用の合成ガウシアンPLYを作る(座標はBlender世界座標、単位m、SH0のみ)。

  python scripts/gaussian/make_test_splats.py <出力フォルダ>

出力:
  ground.ply   地面(z=0)の市松模様。-3<x<3, -3<y<6
  wall.ply     奥の壁(y=3, 面は-Y向き)の縞模様
  ballA.ply    半径0.4の球(橙)。メッシュの立方体の「後ろ」に置く想定
  ballB.ply    半径0.3の球(青)。立方体の「前」に置く想定
  ballC.ply    半径0.4の球(緑)。メッシュの床の上に浮かせて影を落とす想定
  all.ply      全部まとめたもの(単一オブジェクトでの動作確認用)
各ガウシアンは面に沿った薄い楕円体(法線方向のスケールが小さい)。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import spzply as sp  # noqa: E402

C0 = 0.28209479177387814


def quat_from_z_to(n):
    """z軸を単位ベクトルnへ回すクォータニオン(w,x,y,z)。"""
    z = np.array([0.0, 0.0, 1.0])
    n = n / np.linalg.norm(n)
    d = float(np.dot(z, n))
    if d > 0.999999:
        return np.array([1.0, 0, 0, 0])
    if d < -0.999999:
        return np.array([0.0, 1, 0, 0])
    a = np.cross(z, n)
    q = np.array([1 + d, *a])
    return q / np.linalg.norm(q)


def make_cloud(pos, normals, rgb, size, thickness=0.12, alpha=0.97):
    n = len(pos)
    rot = np.array([quat_from_z_to(v) for v in normals], dtype=np.float32)
    s = np.log(np.stack([np.full(n, size), np.full(n, size), np.full(n, size * thickness)], axis=1))
    a = np.log(alpha / (1 - alpha))
    return sp.Cloud(
        positions=np.asarray(pos, np.float32),
        scales=s.astype(np.float32),
        rotations=rot,
        alphas=np.full(n, a, np.float32),
        colors=((np.asarray(rgb, np.float32) - 0.5) / C0).astype(np.float32),
        sh=np.zeros((n, 0, 3), np.float32),
        coord="BLENDER",
    )


def plane(x0, x1, y0, y1, z, step, color_fn, normal=(0, 0, 1), jitter=0.0, seed=0):
    rng = np.random.default_rng(seed)
    xs = np.arange(x0, x1, step) + step / 2
    ys = np.arange(y0, y1, step) + step / 2
    gx, gy = np.meshgrid(xs, ys)
    pos = np.stack([gx.ravel(), gy.ravel(), np.full(gx.size, z)], axis=1)
    pos[:, :2] += rng.uniform(-jitter, jitter, (len(pos), 2))
    return pos, np.tile(normal, (len(pos), 1)), np.array([color_fn(p) for p in pos])


def ground():
    def col(p):
        k = (int(np.floor(p[0] / 0.5)) + int(np.floor(p[1] / 0.5))) % 2
        return (0.35, 0.62, 0.25) if k else (0.78, 0.74, 0.35)
    pos, nrm, rgb = plane(-3, 3, -3, 6, 0.0, 0.06, col, jitter=0.01)
    return make_cloud(pos, nrm, rgb, size=0.045)


def wall():
    # 壁(y=3)は xz 平面。x,z を2軸にして並べる
    step = 0.06
    xs = np.arange(-2, 2, step) + step / 2
    zs = np.arange(0, 2.5, step) + step / 2
    gx, gz = np.meshgrid(xs, zs)
    pos = np.stack([gx.ravel(), np.full(gx.size, 3.0), gz.ravel()], axis=1)
    rgb = np.array([(0.85, 0.2, 0.2) if int(np.floor(p[0] / 0.4)) % 2 else (0.2, 0.3, 0.85) for p in pos])
    nrm = np.tile((0.0, -1.0, 0.0), (len(pos), 1))
    return make_cloud(pos, nrm, rgb, size=0.045)


def sphere(center, r, rgb, n=4000, seed=1):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    pos = np.asarray(center) + r * v
    shade = 0.75 + 0.25 * v[:, 2:3]  # 上ほど少し明るい(焼き込みの陰影)
    return make_cloud(pos, v, np.asarray(rgb) * shade, size=r * 0.12)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    parts = {
        "ground": ground(),
        "wall": wall(),
        "ballA": sphere((0.0, 1.8, 0.5), 0.4, (1.0, 0.55, 0.1), seed=1),
        "ballB": sphere((0.55, -0.7, 0.35), 0.3, (0.2, 0.45, 1.0), seed=2),
        "ballC": sphere((2.2, 0.0, 0.9), 0.4, (0.2, 0.9, 0.35), seed=3),
    }
    for name, cl in parts.items():
        sp.write_ply(cl, os.path.join(out_dir, name + ".ply"))
        print(name, cl.n)
    cat = lambda f: np.concatenate([getattr(c, f) for c in parts.values()])  # noqa: E731
    allc = sp.Cloud(cat("positions"), cat("scales"), cat("rotations"), cat("alphas"), cat("colors"),
                    np.zeros((sum(c.n for c in parts.values()), 0, 3), np.float32), "BLENDER")
    sp.write_ply(allc, os.path.join(out_dir, "all.ply"))
    print("all", allc.n)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "experiments/spike/splats")
