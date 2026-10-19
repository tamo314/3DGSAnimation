"""路面の影の縁の幅（10%-90%）を測り、影の柔らかさの目安にする。

路面（土）の領域で、輝度勾配が大きい点から勾配方向に断面を取り、
片側の低い値(影)→反対側の高い値(日向)の 10-90% 立ち上がり幅をピクセルで返す。
"""
import sys
import numpy as np
from PIL import Image, ImageFilter


def run(path, box, min_contrast=0.35, half=14):
    im = Image.open(path).convert("RGB")
    lum = np.asarray(im.convert("L").filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32) / 255.0
    x0, y0, x1, y1 = box
    gy, gx = np.gradient(lum)
    mag = np.hypot(gx, gy)
    widths = []
    ys, xs = np.mgrid[y0 + half : y1 - half, x0 + half : x1 - half]
    cand = mag[y0 + half : y1 - half, x0 + half : x1 - half]
    thr = np.percentile(cand, 90)
    pts = np.argwhere(cand >= thr)
    rng = np.random.default_rng(0)
    rng.shuffle(pts)
    for py, px in pts[:4000]:
        cy, cx = py + y0 + half, px + x0 + half
        # 局所最大のみ
        if mag[cy, cx] < mag[cy - 1 : cy + 2, cx - 1 : cx + 2].max():
            continue
        g = np.array([gx[cy, cx], gy[cy, cx]])
        n = np.linalg.norm(g)
        if n < 1e-6:
            continue
        g /= n
        t = np.arange(-half, half + 1)
        xs_ = np.clip(np.round(cx + g[0] * t).astype(int), 0, lum.shape[1] - 1)
        ys_ = np.clip(np.round(cy + g[1] * t).astype(int), 0, lum.shape[0] - 1)
        prof = lum[ys_, xs_]
        lo, hi = prof[:4].mean(), prof[-4:].mean()
        if hi - lo < min_contrast * max(hi, 1e-3) or hi / max(lo, 1e-3) < 1.6:
            continue
        # 単調な立ち上がりだけを採用
        d = np.diff(prof)
        if (d < -0.03).sum() > 3:
            continue
        a, b = lo + 0.1 * (hi - lo), lo + 0.9 * (hi - lo)
        ia, ib = np.argmax(prof >= a), np.argmax(prof >= b)
        if ib > ia:
            widths.append(ib - ia)
    return np.array(widths)


if __name__ == "__main__":
    p = sys.argv[1]
    box = tuple(int(v) for v in sys.argv[2:6])
    w = run(p, box)
    if len(w) == 0:
        print("no edges")
    else:
        print(f"n={len(w)} median={np.median(w):.1f}px p25={np.percentile(w,25):.1f} p75={np.percentile(w,75):.1f}")
