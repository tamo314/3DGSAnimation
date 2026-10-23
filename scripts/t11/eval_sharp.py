"""T11: 学習視点の描画が元画像に比べてどれだけ鮮明か。顔まわりで、元画像の勾配が強い上位10%の画素における(描画の勾配の平均)/(元画像の勾配の平均)。1に近いほど鮮明。
  python eval_sharp.py DATA_DIR RENDER_DIR [--box x0,y0,x1,y1]   RENDER_DIR: gs_render_train.py の出力(<name>.png)"""
import sys, os, glob
import numpy as np
from PIL import Image
data, rd = sys.argv[1], sys.argv[2]; box = (220, 260, 700, 700)
if "--box" in sys.argv: box = tuple(int(x) for x in sys.argv[sys.argv.index("--box") + 1].split(","))
def src(n):
    im = Image.open(f"{data}/train/{n}.png").convert("RGBA"); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); return bg.convert("RGB")
def gm(im):
    g = np.asarray(im.convert("L"), dtype=np.float32); return np.sqrt(np.diff(g, axis=1)[:-1] ** 2 + np.diff(g, axis=0)[:, :-1] ** 2)
rs, rs2 = [], []
for f in sorted(glob.glob(rd + "/c10_az*.png")):
    n = os.path.basename(f)[:-4]; a = src(n).crop(box); b = Image.open(f).convert("RGB").crop(box); ga, gb = gm(a), gm(b); m = ga > np.percentile(ga, 90)
    rs.append(gb[m].mean() / ga[m].mean()); rs2.append(gb[gb > np.percentile(gb, 90)].mean() / ga[m].mean())   # 2つめ: 位置合わせに依らない(描画自身の上位10%同士)
print(f"{rd}: views {len(rs)} edge ratio(元画像の輪郭位置) {np.mean(rs):.3f} (min {np.min(rs):.3f}), 位置に依らない {np.mean(rs2):.3f}")
