"""参照画像(前・左・背面)と、正規化後モデルのレンダリングを並べた比較画像を作る。
python -I scripts/character/make_compare.py <ref_dir> <inspect_dir> <out.png>
Blender規約: 前=az000(カメラ-Y)、キャラの左側面=az090(+X)、背面=az180(+Y)
"""
import sys
from PIL import Image

ref_dir, d, out = sys.argv[1:4]
rows = [("girl1.png", "view_az000.png"), ("girl2.png", "view_az090.png"), ("girl4.png", "view_az180.png")]
H = 900
tiles = []
for r, m in rows:
    a = Image.open(f"{ref_dir}/{r}").convert("RGB")
    tiles.append(a.resize((int(a.width * H / a.height), H)))
    tiles.append(Image.open(f"{d}/{m}").convert("RGB").resize((H, H)))
s = Image.new("RGB", (sum(t.width for t in tiles), H))
x = 0
for t in tiles:
    s.paste(t, (x, 0))
    x += t.width
s.thumbnail((3000, 800))
s.save(out)
