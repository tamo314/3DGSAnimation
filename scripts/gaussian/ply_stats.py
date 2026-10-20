"""3DGS PLYの簡易統計: 個数、位置の範囲、不透明度、スケール。  python scripts/gaussian/ply_stats.py a.ply [b.ply ...]"""
import sys

import numpy as np

for p in sys.argv[1:]:
    b = open(p, "rb").read(20000)
    h = b[: b.index(b"end_header") + 11]
    hh = h.decode().split("\n")
    n = int([l for l in hh if l.startswith("element vertex")][0].split()[-1])
    names = [l.split()[-1] for l in hh if l.startswith("property")]
    v = np.fromfile(p, dtype=np.dtype([(q, "<f4") for q in names]), offset=len(h), count=n)
    P = np.stack([v["x"], v["y"], v["z"]], 1)
    al = 1 / (1 + np.exp(-v["opacity"]))
    print(p.split("/")[-1], "n", n, "bbox", P.min(0).round(2).tolist(), P.max(0).round(2).tolist())
    r = np.linalg.norm(P[:, :2], axis=1)
    print("  opacity>0.5:", int((al > 0.5).sum()), " within |xy|<0.5&z in[-0.1,1.3]:", int(((r < 0.5) & (P[:, 2] > -0.1) & (P[:, 2] < 1.3)).sum()), " alpha>0.5 inside:",
          int(((al > 0.5) & (r < 0.5) & (P[:, 2] > -0.1) & (P[:, 2] < 1.3)).sum()))
