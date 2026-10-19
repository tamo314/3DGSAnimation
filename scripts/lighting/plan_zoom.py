import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import load_bg
w, a, rgb, cl = load_bg.load()
res = 0.01
x0, x1, y0, y1 = [float(v) for v in sys.argv[1:5]]
zlo, zhi = float(sys.argv[5]), float(sys.argv[6])
name = sys.argv[7]
W, H = int((x1-x0)/res), int((y1-y0)/res)
m = (a>0.3)&(w[:,2]>zlo)&(w[:,2]<zhi)&(w[:,0]>x0)&(w[:,0]<x1)&(w[:,1]>y0)&(w[:,1]<y1)
ww, rr = w[m], rgb[m]
# スプラットサイズ(ガウシアンの大きさ)で点を広げる: 平均スケール(m)
sc = np.exp(cl.scales).mean(1)[m] * 1.68
rad = np.clip((sc/res).astype(int), 1, 6)
img = np.zeros((H,W,3), np.float32); zb = np.full((H,W), -1e9, np.float32)
ix = ((ww[:,0]-x0)/res).astype(int); iy = ((y1-ww[:,1])/res).astype(int)
for r in range(1,7):
    s = rad==r
    for dx in range(-r, r+1):
        for dy in range(-r, r+1):
            if dx*dx+dy*dy>r*r: continue
            jx, jy = ix[s]+dx, iy[s]+dy
            ok = (jx>=0)&(jx<W)&(jy>=0)&(jy<H)
            img[jy[ok], jx[ok]] = rr[s][ok]
Image.fromarray((img*255).astype(np.uint8)).save(name)
print(m.sum(), W, H)
