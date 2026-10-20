"""T8: 元テクスチャと超解像テクスチャについて、「正解」と「3DGSの描画」を並べる。列: 正解(元) / 3DGS(元) / 正解(SR) / 3DGS(SR) [/ 3DGS(SR+寄り) ...]
  python t8_crops_sr.py --out fig.jpg --orig-gt DIR --orig-r DIR --sr-gt DIR --sr-r DIR [--extra ラベル=DIR ...] --crop 0008_face:x,y,size ..."""
import argparse, os
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True); ap.add_argument("--orig-gt", required=True); ap.add_argument("--orig-r", required=True)
ap.add_argument("--sr-gt", required=True); ap.add_argument("--sr-r", required=True); ap.add_argument("--extra", nargs="*", default=[])
ap.add_argument("--crop", action="append", required=True); ap.add_argument("--cell", type=int, default=480)
a = ap.parse_args()
rows = []
for c in a.crop:
    name, box = c.split(":"); x, y, s = [int(t) for t in box.split(",")]
    cols = [("GT orig", os.path.join(a.orig_gt, f"{name}_gt.png")), ("3DGS orig", os.path.join(a.orig_r, f"{name}_render.png")),
            ("GT SR", os.path.join(a.sr_gt, f"{name}_gt.png")), ("3DGS SR", os.path.join(a.sr_r, f"{name}_render.png"))]
    for e in a.extra:
        lab, d = e.split("=", 1); cols.append((lab, os.path.join(d, f"{name}_render.png")))
    row = []
    for lab, p in cols:
        im = Image.open(p).convert("RGB").crop((x, y, x + s, y + s)).resize((a.cell, a.cell), Image.LANCZOS)
        ImageDraw.Draw(im).rectangle([0, 0, 160, 18], fill=(0, 0, 0)); ImageDraw.Draw(im).text((4, 3), f"{lab} {name}", fill=(255, 255, 255))
        row.append(im)
    rows.append(row)
out = Image.new("RGB", (a.cell * len(rows[0]), a.cell * len(rows)))
for j, r in enumerate(rows):
    for i, t in enumerate(r):
        out.paste(t, (i * a.cell, j * a.cell))
out.save(a.out, quality=92); print(a.out, out.size)
