"""【自前実装】G-Styleの出力から「微細な質感(輝度の高周波成分)」だけを取り出し、元のキャラの色に重ねる。
G-Styleそのものは色・絵柄を丸ごと置き換える(顔まで変わる)ので、質感成分だけを使えるかを試す。

  stylized(G-Style出力)の各ガウシアンについて、近傍k個の平均輝度(ベース)に対する比 ratio = L / L_base を詳細層とする。
  新しい色 = 元キャラの最近傍ガウシアンの色 × ratio^strength。ジオメトリ・不透明度は stylized のもの(分割で細かくなっている)を使う。
WSL t7: python scripts/gaussian/style_detail_transfer.py --orig vanilla.ply --styl gstyle.ply --out out.ply --strength 1.0 [--k 16]
"""
import argparse

import numpy as np
from scipy.spatial import cKDTree

C0 = 0.28209479177387814


def load(p):
    b = open(p, "rb").read(20000)
    h = b[: b.index(b"end_header") + 11]
    hh = h.decode().split("\n")
    n = int([l for l in hh if l.startswith("element vertex")][0].split()[-1])
    props = [l.split()[-1] for l in hh if l.startswith("property")]
    dt = np.dtype([(q, "<f4") for q in props])
    return np.fromfile(p, dtype=dt, offset=len(h), count=n), h


ap = argparse.ArgumentParser()
ap.add_argument("--orig", required=True)
ap.add_argument("--styl", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--strength", type=float, default=1.0)
ap.add_argument("--k", type=int, default=16)
ap.add_argument("--clip", default="0.4,2.5")
a = ap.parse_args()

o, _ = load(a.orig)
s, hs = load(a.styl)
Po = np.stack([o["x"], o["y"], o["z"]], 1)
Ps = np.stack([s["x"], s["y"], s["z"]], 1)
rgb_o = 0.5 + C0 * np.stack([o["f_dc_0"], o["f_dc_1"], o["f_dc_2"]], 1)
rgb_s = 0.5 + C0 * np.stack([s["f_dc_0"], s["f_dc_1"], s["f_dc_2"]], 1)
lum = lambda c: 0.299 * c[:, 0] + 0.587 * c[:, 1] + 0.114 * c[:, 2]
L = lum(rgb_s)
_, nn = cKDTree(Ps).query(Ps, k=a.k)
base = L[nn].mean(1)
lo, hi = [float(x) for x in a.clip.split(",")]
ratio = np.clip((L + 0.03) / (base + 0.03), lo, hi)
_, no = cKDTree(Po).query(Ps, k=4)
col = rgb_o[no].mean(1)
new = np.clip(col * (ratio ** a.strength)[:, None], 0.0, 1.5)
f = (new - 0.5) / C0
for i in range(3):
    s[f"f_dc_{i}"] = f[:, i].astype(np.float32)
with open(a.out, "wb") as fo:
    fo.write(hs)
    fo.write(s.tobytes())
print("wrote", a.out, len(s), "ratio p5/p50/p95", np.percentile(ratio, [5, 50, 95]).round(3), "strength", a.strength)
