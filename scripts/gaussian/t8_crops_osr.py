"""T8: 出力側超解像の比較図。列: 3DGS 2048描画をbicubic 2倍 / 同・超解像2倍 / 3DGSを4096で直接描画 / 4096正解(Blender)。
  python t8_crops_osr.py --out fig.jpg --root experiments/T8/osr_G/zoomface --gt experiments/T8/master4k_zoom/images --crop 0000_zoomface:x,y,size ... (座標は4096基準)"""
import argparse, os
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True); ap.add_argument("--root", required=True); ap.add_argument("--gt", required=True)
ap.add_argument("--crop", action="append", required=True); ap.add_argument("--cell", type=int, default=440)
a = ap.parse_args()
rows = []
for c in a.crop:
    name, box = c.split(":"); x, y, s = [int(t) for t in box.split(",")]
    cols = [("bicubic x2", f"bicubic2x/{name}.png"), ("SR x2 (from 2048)", f"sr2x/{name}.png"), ("3DGS native 4096", f"s2/{name}.png"), ("GT 4096", None)]
    row = []
    for lab, rel in cols:
        im = Image.open(os.path.join(a.root, rel) if rel else os.path.join(a.gt, f"{name}.png")).convert("RGB")
        im = im.crop((x, y, x + s, y + s)).resize((a.cell, a.cell), Image.LANCZOS)
        ImageDraw.Draw(im).rectangle([0, 0, 190, 18], fill=(0, 0, 0)); ImageDraw.Draw(im).text((4, 3), f"{lab} {name}", fill=(255, 255, 255))
        row.append(im)
    rows.append(row)
out = Image.new("RGB", (a.cell * 4, a.cell * len(rows)))
for j, r in enumerate(rows):
    for i, t in enumerate(r):
        out.paste(t, (i * a.cell, j * a.cell))
out.save(a.out, quality=92); print(a.out, out.size)
