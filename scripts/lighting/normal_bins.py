"""焼き込み輝度を法線方向ごとに平均する(照明の方向性の目安)。アルベドは平均で薄まる前提。"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import load_bg
w, a, rgb, cl = load_bg.load()
def lin(c): return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
lum = lin(rgb) @ np.array([0.2126, 0.7152, 0.0722])
q = cl.rotations
qw, qx, qy, qz = q.T
Rm = np.empty((len(q), 3, 3), np.float32)
Rm[:,0,0]=1-2*(qy*qy+qz*qz); Rm[:,0,1]=2*(qx*qy-qz*qw); Rm[:,0,2]=2*(qx*qz+qy*qw)
Rm[:,1,0]=2*(qx*qy+qz*qw); Rm[:,1,1]=1-2*(qx*qx+qz*qz); Rm[:,1,2]=2*(qy*qz-qx*qw)
Rm[:,2,0]=2*(qx*qz-qy*qw); Rm[:,2,1]=2*(qy*qz+qx*qw); Rm[:,2,2]=1-2*(qx*qx+qy*qy)
s = np.exp(cl.scales); o = np.argsort(s, 1); r = np.arange(len(s))
smin, smid = s[r, o[:,0]], s[r, o[:,1]]
n_rdf = Rm[r, :, o[:,0]]
n = np.stack([n_rdf[:,0], n_rdf[:,2], -n_rdf[:,1]], 1)
cam = np.array([0.0, -3.5, 1.0]); n[(n*(cam-w)).sum(1) < 0] *= -1
d = np.linalg.norm(w-cam, axis=1)
g = (a>0.6)&(smin/smid<0.3)&(d<10)&(w[:,2]>-0.2)&(w[:,2]<6)
nn, L, ww = n[g], lum[g], w[g]
print("n", g.sum(), "mean lum", L.mean())
# 法線の仰角 (0=垂直面 ... 90=上向き) × 方位 (+Yから+X)
el = np.degrees(np.arcsin(np.clip(nn[:,2], -1, 1)))
az = np.degrees(np.arctan2(nn[:,0], nn[:,1])) % 360
print("normal elevation bins (mean lin lum, count):")
for lo, hi in ((-90,-20),(-20,20),(20,50),(50,75),(75,91)):
    m = (el>=lo)&(el<hi); print(f"  el {lo:4d}..{hi:3d}: {L[m].mean():.3f} ({m.sum()})")
print("vertical walls (|el|<25) by azimuth of normal  [normal pointing to az; 0=+Y(toward arch/sun side), 90=+X, 180=-Y(camera side), 270=-X]")
m0 = np.abs(el) < 25
for lo in range(0, 360, 45):
    m = m0 & (((az-lo) % 360) < 45)
    print(f"  az {lo:3d}..{lo+45:3d}: mean {L[m].mean():.3f} median {np.median(L[m]):.3f}  n={m.sum()}")
