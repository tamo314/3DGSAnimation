"""焼き込み影から太陽方向を測る(T5b)。

不透明スプラットのボクセル占有を作り、小道の地面スプラットから候補の太陽方向へレイを飛ばして「遮られるか(=影のはず)」を判定する。
焼き込み輝度が「日向 > 影」になっているほど、その方向が実際に焼き込まれた光に近い。指標は日向/影の輝度差の t 統計量。
方位は +Y(アーチ方向)から +X(右)へ。  python scripts/lighting/shadow_test.py [--alpha 0.9 --cnt 12] [--png out.png]
注意: 遮蔽は疎な樹冠を過大/過小に拾うので絶対値は目安。方位・仰角に対する「尾根」の位置だけを使う。
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import load_bg  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "T5")


def to_vec(az, el):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)])


def build(alpha_min=0.9, cnt_min=12, vox=0.25, n_samples=8000, seed=1):
    w, a, rgb, cl = load_bg.load()
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    lo = np.array([-30.0, -30.0, -2.0]); hi = np.array([40.0, 50.0, 30.0])
    shape = ((hi - lo) / vox).astype(int)
    m = (a > alpha_min) & (w[:, 2] > -1) & (w[:, 2] < 30) & ~(rgb.min(1) > 0.9)   # 飽和した光芒・空は遮蔽物にしない
    idx = ((w[m] - lo) / vox).astype(int)
    ok = ((idx >= 0) & (idx < shape)).all(1)
    cnt = np.zeros(shape, np.int16)
    np.add.at(cnt, tuple(idx[ok].T), 1)
    occ = cnt >= cnt_min
    g = (a > 0.5) & (w[:, 2] > -0.3) & (w[:, 2] < 0.5) & (np.abs(w[:, 0]) < 5) & (w[:, 1] > -6) & (w[:, 1] < 2)
    rng = np.random.default_rng(seed)
    gi = rng.choice(np.where(g)[0], n_samples, replace=False)
    return occ, lo, vox, shape, w[gi] + np.array([0, 0, 0.15]), lum[gi]


def shadowed(occ, lo, vox, shape, P, l, maxd=30.0, step=0.25):
    sh = np.zeros(len(P), bool)
    for t in np.arange(0.5, maxd, step):
        ii = ((P + l * t - lo) / vox).astype(int)
        ok = ((ii >= 0) & (ii < shape)).all(1)
        v = np.zeros(len(P), bool)
        v[ok] = occ[tuple(ii[ok].T)]
        sh |= v
    return sh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.9)
    ap.add_argument("--cnt", type=int, default=12)
    ap.add_argument("--png", default=os.path.join(OUT, "sun_direction_test.png"))
    a = ap.parse_args()
    occ, lo, vox, shape, P, L = build(a.alpha, a.cnt)
    azs = np.arange(-60, 121, 6); els = np.arange(10, 61, 5)
    T = np.full((len(els), len(azs)), np.nan)
    F = np.full_like(T, np.nan)
    for i, el in enumerate(els):
        for j, az in enumerate(azs):
            sh = shadowed(occ, lo, vox, shape, P, to_vec(az, el))
            f = sh.mean()
            F[i, j] = f
            if f < 0.05 or f > 0.95:
                continue            # ほぼ全点が影/日向の方向は判定不能
            d = L[~sh].mean() - L[sh].mean()
            T[i, j] = d / np.sqrt(L[~sh].var() / (~sh).sum() + L[sh].var() / sh.sum())
    json.dump({"az": azs.tolist(), "el": els.tolist(), "t": np.nan_to_num(T, nan=-999).tolist(), "shadow_frac": F.tolist()},
              open(os.path.join(OUT, "sun_direction_test.json"), "w"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=130)
    im = ax.pcolormesh(azs, els, np.ma.masked_invalid(T), shading="nearest", cmap="viridis", vmin=-10, vmax=30)
    plt.colorbar(im, ax=ax, label="t (lit - shadow luminance)")
    marks = [("T5a photo estimate", 17.6, 24.2, "w", "o"), ("sun disk in splats", 45.8, 40.3, "r", "^"), ("chosen", 15.0, 26.0, "k", "*")]
    for lab, az, el, c, mk in marks:
        ax.plot(az, el, mk, color=c, ms=11, mec="w" if c == "k" else "k", label=lab)
    ax.set_xlabel("sun azimuth from +Y (arch) toward +X [deg]"); ax.set_ylabel("sun elevation [deg]")
    ax.set_title("Baked-shadow consistency of candidate sun directions (ground splats)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout(); fig.savefig(a.png)
    print("saved", a.png)
    best = np.unravel_index(np.nanargmax(T), T.shape)
    print("best t %.1f at az %d el %d" % (T[best], azs[best[1]], els[best[0]]))


if __name__ == "__main__":
    main()
