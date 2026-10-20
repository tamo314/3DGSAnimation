"""T8: 正解(GT)と各モデルの描画を同じ切り出しで並べる比較図を作る。
  python t8_crops.py --out fig.jpg --evals B=evals/B_..._s1.0 D=evals/D_..._s1.0 --crop 0008_face:500,400,800 --crop 0000_ring:600,150,300 [--zoom 2]
--crop は <画像名>:x,y,size。GT列(黒背景)は最初の評価ディレクトリの *_gt.png を使う。--gray で黒背景をグレーに(アルファがあるときのみ)。
"""
import argparse, os
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--evals", nargs="+", required=True, help="ラベル=ディレクトリ")
ap.add_argument("--crop", action="append", required=True)
ap.add_argument("--nearest", action="store_true", help="拡大に最近傍を使う(縮小描画のジャギー確認用)")
ap.add_argument("--cell", type=int, default=480, help="1セルの表示サイズ(px)")
a = ap.parse_args()
evs = [e.split("=", 1) for e in a.evals]
rows = []
for c in a.crop:
    name, box = c.split(":")
    x, y, s = [int(t) for t in box.split(",")]
    cells = []
    gt = Image.open(os.path.join(evs[0][1], f"{name}_gt.png")).convert("RGB")
    cells.append(("GT", gt))
    for lab, d in evs:
        cells.append((lab, Image.open(os.path.join(d, f"{name}_render.png")).convert("RGB")))
    row = []
    for lab, im in cells:
        sc = im.size[0] / gt.size[0]    # 縮小描画のとき座標を合わせる
        b = (int(x * sc), int(y * sc), int((x + s) * sc), int((y + s) * sc))
        t = im.crop(b).resize((a.cell, a.cell), Image.NEAREST if (sc < 1 or a.nearest) else Image.LANCZOS)
        ImageDraw.Draw(t).rectangle([0, 0, 150, 22], fill=(0, 0, 0))
        ImageDraw.Draw(t).text((4, 4), f"{lab} {name}", fill=(255, 255, 255))
        row.append(t)
    rows.append(row)
W = a.cell * len(rows[0]); H = a.cell * len(rows)
out = Image.new("RGB", (W, H))
for j, row in enumerate(rows):
    for i, t in enumerate(row):
        out.paste(t, (i * a.cell, j * a.cell))
out.save(a.out, quality=92)
print(a.out, out.size)
