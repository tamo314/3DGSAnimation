"""T7: 背景3DGSの法線(最小スケール軸)の質を、ランバート回帰 L = A + B*max(0, n·l) の当てはまり(R²)と太陽方向の安定性で比べる。
T5(measure_sun.py)で元の背景は R² 0.02〜0.11・方位が不安定だった。MILoで学習し直した背景(世界座標のPLY)で改善するかを測る。
  python scripts/lighting/lambert_compare.py --orig  --milo experiments/T7/runs/milo_bg/gaussians.ply [--out experiments/T7/runs/lambert_compare.json]
座標: 世界座標(X右・Y前=アーチ方向・Z上)。方位は +Y から +X へ。
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "gaussian"))

C0 = 0.28209479177387814
ap = argparse.ArgumentParser()
ap.add_argument("--orig", action="store_true")
ap.add_argument("--milo", default=None)
ap.add_argument("--out", default=None)
a = ap.parse_args()


def quat_R(q):
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3), np.float32)
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - z * w); R[:, 0, 2] = 2 * (x * z + y * w)
    R[:, 1, 0] = 2 * (x * y + z * w); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - x * w)
    R[:, 2, 0] = 2 * (x * z - y * w); R[:, 2, 1] = 2 * (y * z + x * w); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def from_original():
    import load_bg
    w, alpha, rgb, cl = load_bg.load()
    R = quat_R(cl.rotations.astype(np.float64))
    s = np.exp(cl.scales)
    imin = np.argmin(s, axis=1)
    n_rdf = R[np.arange(len(R)), :, imin]
    n = np.stack([n_rdf[:, 0], n_rdf[:, 2], -n_rdf[:, 1]], 1)          # RDF -> 世界
    return w, alpha, rgb, n, s


def from_world_ply(p):
    b = open(p, "rb").read(20000)
    h = b[: b.index(b"end_header") + 11]
    hh = h.decode().split("\n")
    n_ = int([l for l in hh if l.startswith("element vertex")][0].split()[-1])
    props = [l.split()[-1] for l in hh if l.startswith("property")]
    v = np.fromfile(p, dtype=np.dtype([(q, "<f4") for q in props]), offset=len(h), count=n_)
    w = np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float64)
    alpha = 1 / (1 + np.exp(-v["opacity"].astype(np.float64)))
    rgb = np.clip(0.5 + C0 * np.stack([v["f_dc_0"], v["f_dc_1"], v["f_dc_2"]], 1), 0, 1)
    R = quat_R(np.stack([v["rot_0"], v["rot_1"], v["rot_2"], v["rot_3"]], 1).astype(np.float64))
    s = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1).astype(np.float64))
    imin = np.argmin(s, axis=1)
    n = R[np.arange(len(R)), :, imin]
    return w, alpha, rgb, n, s


def to_vec(az, el):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)])


def analyse(label, w, alpha, rgb, n, s):
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    cam = np.array([0.0, -3.5, 1.0])
    n = n.copy()
    n[(n * (cam - w)).sum(1) < 0] *= -1
    ss = np.sort(s, axis=1)
    dist = np.linalg.norm(w - cam, axis=1)
    good = (alpha > 0.6) & (ss[:, 0] / ss[:, 1] < 0.35) & (dist < 12) & (w[:, 2] > -0.3) & (w[:, 2] < 8)
    nn, LL, dd = n[good], lum[good], dist[good]
    rng = np.random.default_rng(0)
    out = {"n_samples": int(good.sum())}

    def fit(idx, tag, nzmax=1.0):
        mk = np.abs(nn[idx, 2]) <= nzmax
        N, L = nn[idx][mk], LL[idx][mk]
        var = L.var() * len(L)
        best = None
        for az in range(0, 360, 5):
            for el in range(0, 91, 5):
                x = np.maximum(N @ to_vec(az, el), 0)
                X = np.stack([np.ones_like(x), x], 1)
                coef = np.linalg.lstsq(X, L, rcond=None)[0]
                sse = ((X @ coef - L) ** 2).sum()
                if best is None or sse < best[0]:
                    best = (sse, az, el)
        out[tag] = {"az": best[1], "el": best[2], "R2": float(1 - best[0] / var), "n": int(len(L))}
        print(label, tag, out[tag])

    allidx = rng.choice(len(nn), min(len(nn), 150000), replace=False)
    fit(allidx, "all")
    fit(allidx, "walls(|nz|<0.6)", 0.6)
    for tag, lo, hi in (("near<5m", 0, 5), ("mid5-12m", 5, 12)):
        idx = np.where((dd >= lo) & (dd < hi))[0]
        idx = rng.choice(idx, min(len(idx), 100000), replace=False)
        fit(idx, tag, 0.7)
    return out


res = {}
if a.orig:
    res["original"] = analyse("original", *from_original())
if a.milo:
    res["milo"] = analyse("milo", *from_world_ply(a.milo))
if a.out:
    json.dump(res, open(a.out, "w"), indent=1)
