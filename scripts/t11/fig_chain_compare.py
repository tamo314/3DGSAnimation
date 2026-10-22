"""T11: 連鎖生成(c8)と独立生成(c4)の中間視点の描画を並べた比較図を作る。python fig_chain_compare.py OUT.jpg --cols a+015,a+025,... [--ref chain10_rgba の名目方位と対応する列は 'a+030=c10_az+030' 形式]"""
import sys, os
from PIL import Image, ImageDraw
R = "experiments/T11/render"; rows = [("c4 independent", "n_c4_sh3"), ("c8 chain, aligned az", "n_c8_aligned"), ("c8 chain, nominal az", "n_c8_nominal"), ("c9 no pose", "n_c9_nopose"), ("c9 dense", "n_c9_dense"), ("c10 no pose+dense", "n_c10")]
cols = sys.argv[2].split(","); out = sys.argv[1]; s = 0.36; w, h = int(1024 * s), int(1280 * s); lw = 120
sheet = Image.new("RGB", (lw + w * len(cols), 18 + h * len(rows)), "white"); d = ImageDraw.Draw(sheet)
for j, c in enumerate(cols): d.text((lw + j * w + 4, 3), c, fill="black")
for i, (lab, dr) in enumerate(rows):
    d.text((4, 18 + i * h + 4), lab, fill="black")
    for j, c in enumerate(cols):
        im = Image.open(f"{R}/{dr}/{c}.png").convert("RGB").resize((w, h), Image.LANCZOS); sheet.paste(im, (lw + j * w, 18 + i * h))
sheet.save(out, quality=90)
