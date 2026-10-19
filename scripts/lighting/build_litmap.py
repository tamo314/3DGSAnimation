"""キャラ周辺の地面の「日向度」マップ(焼き込み輝度から)を作る。  python scripts/lighting/build_litmap.py
- 出力 experiments/T5/litmap.npz: lit(H,W) 0..1, x0,y0,res, ground_z(H,W), 参考の可視化png
- 日向度 = 局所の輝度コントラストから。r = L / (近傍の下位10%輝度) とし、日向の砂は日陰の約3.4倍(calibrate_light.py)なので (r-1)/2.4 を 0..1 に切る。
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(__file__))
import load_bg

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "T5")
x0, x1, y0, y1, res = -2.0, 3.0, -5.5, 1.5, 0.02
SAND_SHADE = 0.122   # 日陰の砂の線形輝度(calibrate_light.py の shade)
W, H = int((x1-x0)/res), int((y1-y0)/res)

def lin(c): return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)

def main():
    w, a, rgb, cl = load_bg.load()
    lum = lin(rgb) @ np.array([0.2126, 0.7152, 0.0722])
    m = (a > 0.4) & (w[:, 0] > x0) & (w[:, 0] < x1) & (w[:, 1] > y0) & (w[:, 1] < y1) & (w[:, 2] > -0.3) & (w[:, 2] < 0.5)
    ww, ll = w[m], lum[m]
    ix = ((ww[:, 0]-x0)/res).astype(int); iy = ((y1-ww[:, 1])/res).astype(int)
    # 各セルで最も低いzのスプラット(地面)の輝度。セルを3x3に広げて穴を減らす
    zmin = np.full((H, W), 1e9, np.float32); lm = np.zeros((H, W), np.float32); cr = np.zeros((H, W, 3), np.float32)
    rgbm = lin(rgb[m])
    order = np.argsort(-ww[:, 2])      # 高い順に書く -> 最後に低いものが残る
    sx = np.exp(cl.scales[m]).max(1) * 1.68
    rad = np.clip((sx/res/2).astype(int), 0, 3)
    for r in range(4):
        s = order[rad[order] == r]
        for dx in range(-r, r+1):
            for dy in range(-r, r+1):
                if dx*dx+dy*dy > r*r: continue
                jx, jy = ix[s]+dx, iy[s]+dy
                ok = (jx >= 0) & (jx < W) & (jy >= 0) & (jy < H)
                lm[jy[ok], jx[ok]] = ll[s][ok]; cr[jy[ok], jx[ok]] = rgbm[s][ok]; zmin[jy[ok], jx[ok]] = ww[s][ok][:, 2]
    have = zmin < 1e8
    print("coverage", have.mean())
    idx = ndi.distance_transform_edt(~have, return_distances=False, return_indices=True)
    lm = lm[tuple(idx)]; zg = zmin[tuple(idx)]; cr = cr[tuple(idx)]
    lm = ndi.gaussian_filter(lm, 1.0)
    p10 = ndi.percentile_filter(lm, 10, size=31)          # 約0.6m窓
    r = lm / np.maximum(p10, 1e-3)
    lit_local = np.clip((r - 1.0) / 2.4, 0, 1)
    # 砂色(小道)は絶対輝度から: 日陰の砂の輝度 SAND_SHADE に対する倍率。砂以外(苔・石)は局所コントラストで、下限0.3
    cs = ndi.gaussian_filter(cr, (1, 1, 0))
    sand = (cs[..., 0] > cs[..., 2] * 1.5) & (cs[..., 0] >= cs[..., 1] * 0.98)
    lit_sand = np.clip((lm / SAND_SHADE - 1.0) / 2.4, 0, 1)
    lit = np.where(sand, lit_sand, np.maximum(lit_local, 0.3))
    lit = ndi.gaussian_filter(lit, 1.0)
    print("sand cells", sand.mean(), "lit fraction >0.5:", (lit > 0.5).mean(), "mean", lit.mean())
    np.savez_compressed(os.path.join(OUT, "litmap.npz"), lit=lit.astype(np.float32), ground_z=ndi.gaussian_filter(zg, 2).astype(np.float32),
                        x0=x0, y1=y1, res=res)
    Image.fromarray((lit*255).astype(np.uint8)).save(os.path.join(OUT, "litmap.png"))
    Image.fromarray((np.clip(lm/0.6, 0, 1)**0.45*255).astype(np.uint8)).save(os.path.join(OUT, "litmap_lum.png"))

main()
