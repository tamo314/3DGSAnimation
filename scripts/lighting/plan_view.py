"""背景スプラットの真上からの地図(色・輝度)を作る。焼き込まれた影の向きを見るため。"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import load_bg

w, a, rgb, cl = load_bg.load()
print(len(w), w.min(0).round(1), w.max(0).round(1))
res = 0.02
x0, x1, y0, y1 = -6, 8, -6, 14
W, H = int((x1-x0)/res), int((y1-y0)/res)
out = os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "T5")
os.makedirs(out, exist_ok=True)

def raster(mask, name, mode="ground"):
    ww, rr = w[mask], rgb[mask]
    ix = ((ww[:,0]-x0)/res).astype(int); iy = ((y1-ww[:,1])/res).astype(int)
    ok = (ix>=0)&(ix<W)&(iy>=0)&(iy<H)
    ix, iy, ww, rr = ix[ok], iy[ok], ww[ok], rr[ok]
    # 各ピクセルで最も高い(または最も低い)zのスプラットを採る
    order = np.argsort(ww[:,2] if mode=="top" else -ww[:,2])
    img = np.zeros((H, W, 3), np.float32); seen = np.zeros((H,W), bool)
    # 後ろから書けば先頭が優先
    idx = order[::-1]
    img[iy[idx], ix[idx]] = rr[idx]
    Image.fromarray((img*255).astype(np.uint8)).save(os.path.join(out, name))

m = (a > 0.3)
raster(m & (w[:,2] > -0.3) & (w[:,2] < 0.6), "plan_ground.png", "ground")
raster(m, "plan_top.png", "top")
