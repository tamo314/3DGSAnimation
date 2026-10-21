"""T11: 画像のキャラを切り抜いてRGBAにする(rembg isnet-anime)。
  python -I matte.py IN_DIR OUT_DIR [--model isnet-anime]
床の影・ぼかし背景に引かれないよう、アルファは閾値後に最大連結成分だけ残す。"""
import argparse, os, sys
import numpy as np
from PIL import Image
from rembg import new_session, remove
from scipy import ndimage as ndi
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--model", default="isnet-anime")
a = ap.parse_args(); os.makedirs(a.dst, exist_ok=True)
sess = new_session(a.model)
for f in sorted(os.listdir(a.src)):
    if not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")): continue
    im = Image.open(os.path.join(a.src, f)).convert("RGB")
    m = np.asarray(remove(im, session=sess, only_mask=True)).astype(np.float32) / 255
    lab, n = ndi.label(m > 0.5)
    if n > 1:
        sizes = ndi.sum(np.ones_like(m), lab, range(1, n + 1)); keep = np.argmax(sizes) + 1
        big = ndi.binary_dilation(lab == keep, iterations=6)
        m = m * big
    rgba = np.dstack([np.asarray(im), (m * 255 + .5).astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").save(os.path.join(a.dst, os.path.splitext(f)[0] + ".png"))
    print(f, "alpha>0.5 frac", float((m > .5).mean()))
