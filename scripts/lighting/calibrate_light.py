"""小道の砂スプラット(日向/日陰)の焼き込み色から、太陽と環境光の相対強さ・色を較正する。
水平面(拡散, 同じアルベド)に対し  I_lit = rho*(E_sun*sin(el) + E_amb),  I_shade = rho*E_amb  (線形RGB)。
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import load_bg
w, a, rgb, cl = load_bg.load()

def lin(c):
    return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)

lum = lin(rgb) @ np.array([0.2126, 0.7152, 0.0722])
sand = (rgb[:, 0] > rgb[:, 2]*1.15) & (rgb[:, 0] >= rgb[:, 1]*0.98)
reg = (a > 0.5) & sand & (w[:, 2] > -0.3) & (w[:, 2] < 0.4) & (np.abs(w[:, 0]-0.6) < 3.0) & (w[:, 1] > -5.5) & (w[:, 1] < 1.5)
L = lum[reg]; C = lin(rgb[reg])
print("sand samples", reg.sum(), "lum pct", np.percentile(L, [5, 25, 50, 75, 90, 97]).round(3))
order = np.argsort(L)
n = len(L)
shade = C[order[int(n*0.15):int(n*0.45)]].mean(0)
lit = C[order[int(n*0.90):int(n*0.98)]].mean(0)
print("shade lin RGB", shade.round(4), " lit lin RGB", lit.round(4))
direct = lit - shade
print("direct (lit-shade)", direct.round(4), "ratio direct/shade lum", (direct@[0.2126,0.7152,0.0722]) / (shade@[0.2126,0.7152,0.0722]))
def cct_rgb(v):
    return v / v.max()
print("direct color norm", cct_rgb(direct).round(3), "shade color norm", cct_rgb(shade).round(3))
# キャラ足元付近(半径1m)の焼き込みの日向率
near = (np.hypot(w[:, 0]-0.4, w[:, 1]) < 1.0) & (a > 0.5) & (w[:, 2] > -0.3) & (w[:, 2] < 0.5)
print("near-char lum pct", np.percentile(lum[near], [10, 50, 90]).round(3), "frac lit(>%.2f)" % (lit@[0.2126,0.7152,0.0722]*0.7), (lum[near] > lit@[0.2126,0.7152,0.0722]*0.7).mean())
json.dump({"shade_lin": shade.tolist(), "lit_lin": lit.tolist(), "direct_lin": direct.tolist()},
          open(os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "T5", "calib.json"), "w"), indent=1)
