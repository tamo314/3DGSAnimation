"""キャラと周囲の明るさ・色のなじみを数値にする(T6)。
キャラのマスク(render_char_masks.py)内と、その外側の輪(6〜40px)で、線形輝度と R/B 比を比べる。
  python scripts/lighting/char_bg_stats.py [before_dir] [after_dir] [masks_dir]
  before: T4の5視点(<name>_0001_composite.png)、after: T5bの最終(<name>.png)
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
before = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "..", "3DGSAnimation-T4", "experiments", "T4", "headless")
after = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "experiments", "T5", "final")
masks = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "experiments", "T5", "masks")


def lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


print("view | char lin.lum before/after | ring lin.lum before/after | char/ring before -> after | char R/B before -> after | ring R/B")
for n in ["front_wide", "character_medium", "dappled_low", "side_depth", "high_oblique"]:
    m = np.asarray(Image.open(os.path.join(masks, n + ".png")))[..., 3] > 128
    ring = ndi.binary_dilation(m, iterations=40) & ~ndi.binary_dilation(m, iterations=6)
    res = {}
    for tag, p in (("b", os.path.join(before, n + "_0001_composite.png")), ("a", os.path.join(after, n + ".png"))):
        im = lin(np.asarray(Image.open(p).convert("RGB")).astype(float))
        L = im @ [0.2126, 0.7152, 0.0722]
        res[tag] = (L[m].mean(), L[ring].mean(), im[m].mean(0), im[ring].mean(0))
    b, a = res["b"], res["a"]
    print(f"{n:17s} | {b[0]:.3f} / {a[0]:.3f} | {b[1]:.3f} / {a[1]:.3f} | {b[0]/b[1]:.2f} -> {a[0]/a[1]:.2f} | "
          f"{b[2][0]/b[2][2]:.2f} -> {a[2][0]/a[2][2]:.2f} | {a[3][0]/a[3][2]:.2f}")
