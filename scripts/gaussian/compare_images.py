"""ラベル付きの横並び比較画像を作る(必要ならクロップ・拡大)。
  python scripts/gaussian/compare_images.py out.jpg --crop x0,y0,x1,y1 [--scale 2] label1=path1 label2=path2 ...
"""
import argparse

from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--crop", default=None)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--height", type=int, default=0, help="各画像の高さに揃える(0=そのまま)")
ap.add_argument("items", nargs="+", help="label=path")
a = ap.parse_args()

ims = []
for it in a.items:
    label, path = it.split("=", 1)
    im = Image.open(path).convert("RGB")
    if a.crop:
        x0, y0, x1, y1 = [int(v) for v in a.crop.split(",")]
        im = im.crop((x0, y0, x1, y1))
    if a.scale != 1.0:
        im = im.resize((int(im.width * a.scale), int(im.height * a.scale)), Image.LANCZOS)
    if a.height:
        im = im.resize((int(im.width * a.height / im.height), a.height), Image.LANCZOS)
    ims.append((label, im))
pad, lh = 6, 26
W = sum(i.width for _, i in ims) + pad * (len(ims) + 1)
H = max(i.height for _, i in ims) + lh + pad * 2
canvas = Image.new("RGB", (W, H), (24, 24, 24))
d = ImageDraw.Draw(canvas)
x = pad
for label, im in ims:
    canvas.paste(im, (x, lh + pad))
    d.text((x + 4, 6), label, fill=(235, 235, 235))
    x += im.width + pad
canvas.save(a.out, quality=92)
print("saved", a.out, canvas.size)
