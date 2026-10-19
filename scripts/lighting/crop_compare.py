"""同じ領域を複数のレンダーから切り出して横に並べる。 python crop_compare.py out.png x0 y0 x1 y1 scale label=path ..."""
import sys
from PIL import Image, ImageDraw
dst = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); sc = float(sys.argv[6])
tiles = []
for it in sys.argv[7:]:
    lab, p = it.split("=", 1)
    im = Image.open(p).convert("RGB").crop((x0, y0, x1, y1))
    im = im.resize((int(im.width*sc), int(im.height*sc)), Image.LANCZOS)
    ImageDraw.Draw(im).text((6, 4), lab, fill=(255, 255, 0))
    tiles.append(im)
W = sum(t.width for t in tiles); H = max(t.height for t in tiles)
sheet = Image.new("RGB", (W, H)); x = 0
for t in tiles:
    sheet.paste(t, (x, 0)); x += t.width
sheet.save(dst)
