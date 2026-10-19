"""背景スプラットから太陽の向きを2通りで測る。
 (a) 写った太陽: 非常に明るい(白飽和)スプラット塊の重心の向き。
 (b) 焼き込み陰影: 各スプラットの法線(最小スケール軸)と輝度のランバート回帰 L = A + B*max(0, n.l) を方位・仰角でグリッド探索。
座標: 世界座標(X右・Y前=アーチ方向・Z上)。方位は +Y から +X へ測る(T5a と同じ)。
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import load_bg

w, a, rgb, cl = load_bg.load()
lum = rgb @ np.array([0.2126, 0.7152, 0.0722])

def az_el(v):
    v = v / np.linalg.norm(v)
    return np.degrees(np.arctan2(v[0], v[1])), np.degrees(np.arcsin(v[2]))

def to_vec(az, el):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.sin(az)*np.cos(el), np.cos(az)*np.cos(el), np.sin(el)])

# ---- (a) 太陽の塊 ----
res = {}
sky = (a > 0.5) & (rgb.min(1) > 0.93) & (w[:, 2] > 1.0)
print("saturated bright splats", sky.sum())
if sky.sum():
    pts = w[sky]
    # 距離別に粗く塊を探す: 方向ヒストグラム(視点=キャラ頭付近)
    eye = np.array([0.4, 0.0, 1.0])
    d = pts - eye
    dist = np.linalg.norm(d, axis=1)
    print("dist percentiles", np.percentile(dist, [5, 25, 50, 75, 95]).round(1))
    azs = np.degrees(np.arctan2(d[:, 0], d[:, 1])); els = np.degrees(np.arcsin(d[:, 2]/dist))
    H, xe, ye = np.histogram2d(azs, els, bins=[np.arange(-180, 181, 3), np.arange(-10, 91, 3)])
    i, j = np.unravel_index(H.argmax(), H.shape)
    print("peak dir az %.0f..%.0f el %.0f..%.0f count %d" % (xe[i], xe[i+1], ye[j], ye[j+1], H[i, j]))
    m = (np.abs(azs - (xe[i]+1.5)) < 12) & (np.abs(els - (ye[j]+1.5)) < 12)
    # 重み付き重心の方向(各点の中心方向の円平均)
    u = d[m] / dist[m, None]
    c = u.mean(0)
    print("sun blob dir from character head: az %.1f el %.1f (n=%d)" % (*az_el(c), m.sum()))
    res["sun_blob"] = {"az": az_el(c)[0], "el": az_el(c)[1], "n": int(m.sum())}

# ---- (b) 陰影回帰 ----
q = cl.rotations  # wxyz (RDF)
qw, qx, qy, qz = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
Rm = np.empty((len(q), 3, 3), np.float32)
Rm[:, 0, 0] = 1-2*(qy*qy+qz*qz); Rm[:, 0, 1] = 2*(qx*qy-qz*qw); Rm[:, 0, 2] = 2*(qx*qz+qy*qw)
Rm[:, 1, 0] = 2*(qx*qy+qz*qw); Rm[:, 1, 1] = 1-2*(qx*qx+qz*qz); Rm[:, 1, 2] = 2*(qy*qz-qx*qw)
Rm[:, 2, 0] = 2*(qx*qz-qy*qw); Rm[:, 2, 1] = 2*(qy*qz+qx*qw); Rm[:, 2, 2] = 1-2*(qx*qx+qy*qy)
s = np.exp(cl.scales)
order = np.argsort(s, axis=1)
imin = order[:, 0]
smin, smid = s[np.arange(len(s)), order[:, 0]], s[np.arange(len(s)), order[:, 1]]
n_rdf = Rm[np.arange(len(q)), :, imin]            # 最小スケール軸(列)
n = np.stack([n_rdf[:, 0], n_rdf[:, 2], -n_rdf[:, 1]], 1)   # RDF -> 世界
cam = np.array([0.0, -3.5, 1.0])
flip = (n * (cam - w)).sum(1) < 0
n[flip] *= -1
dist = np.linalg.norm(w - cam, axis=1)
good = (a > 0.6) & (smin/smid < 0.35) & (dist < 12) & (w[:, 2] > -0.3) & (w[:, 2] < 8)
print("normal samples", good.sum())
nn, LL = n[good], lum[good]

def fit(nn, LL, label, nzmax=1.0):
    mk = np.abs(nn[:, 2]) <= nzmax
    nn, LL = nn[mk], LL[mk]
    best = None
    var = LL.var() * len(LL)
    for az in range(0, 360, 5):
        for el in range(0, 91, 5):
            l = to_vec(az, el)
            x = np.maximum(nn @ l, 0)
            X = np.stack([np.ones_like(x), x], 1)
            coef, r, *_ = np.linalg.lstsq(X, LL, rcond=None)
            sse = ((X @ coef - LL)**2).sum()
            if best is None or sse < best[0]:
                best = (sse, az, el, coef)
    r2 = 1 - best[0]/var
    print(f"{label}: az {best[1]} el {best[2]}  A {best[3][0]:.3f} B {best[3][1]:.3f}  R2 {r2:.3f}  n={len(LL)}")
    return best[1], best[2], r2

rng = np.random.default_rng(0)
sel = rng.choice(len(nn), min(len(nn), 200000), replace=False)
res["lambert_all"] = fit(nn[sel], LL[sel], "all normals")
res["lambert_walls"] = fit(nn[sel], LL[sel], "walls (|nz|<0.6)", 0.6)
# 近距離のみ・遠距離のみ
for lab, lo, hi in (("near<5m", 0, 5), ("mid5-12m", 5, 12)):
    mk = (dist[good] >= lo) & (dist[good] < hi)
    idx = np.where(mk)[0]
    idx = rng.choice(idx, min(len(idx), 120000), replace=False)
    res["lambert_" + lab] = fit(nn[idx], LL[idx], lab, 0.7)
json.dump({k: v for k, v in res.items()}, open(os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "T5", "sun_measure.json"), "w"), default=lambda o: float(o), indent=1)
