"""T8: 元テクスチャと超解像テクスチャで描いた同じ視点の正解画像を比べ、細部(勾配エネルギー)がどれだけ増えたかを測る。
  python gt_detail.py <orig master dir> <sr master dir> [--types face,close,zoomface]
指標: 被写体内の輝度勾配強度の平均、高周波(ラプラシアン)エネルギー、強い輪郭の画素割合(勾配>0.05)。同じ視点同士の比。"""
import argparse, json, os
import cv2, numpy as np
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("orig"); ap.add_argument("sr"); ap.add_argument("--types", default="face,close,zoomface,zoomupper,upper,ring,lower"); ap.add_argument("--split", default="all")
a = ap.parse_args()
def stats(p):
    im = np.asarray(Image.open(p).convert("RGBA")).astype(np.float32) / 255.0
    rgb, al = im[..., :3] * im[..., 3:4], im[..., 3]
    l = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    gx, gy = cv2.Sobel(l, cv2.CV_32F, 1, 0, ksize=3) / 8, cv2.Sobel(l, cv2.CV_32F, 0, 1, ksize=3) / 8
    g = np.sqrt(gx ** 2 + gy ** 2)
    m = cv2.erode((al > 0.99).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0     # 被写体の内部(シルエット縁を除く)
    lap = cv2.Laplacian(l, cv2.CV_32F, ksize=3)
    return float(g[m].mean()), float((lap[m] ** 2).mean()), float((g[m] > 0.05).mean())
meta = json.load(open(os.path.join(a.orig, "views.json")))
res = {}
for v in meta["views"]:
    if v["type"] not in a.types.split(",") or (a.split == "test" and v["split"] != "test"):
        continue
    po, ps = os.path.join(a.orig, "images", v["name"]), os.path.join(a.sr, "images", v["name"])
    if not (os.path.exists(po) and os.path.exists(ps)):
        continue
    so, ss = stats(po), stats(ps)
    res.setdefault(v["type"], []).append([ss[i] / so[i] for i in range(3)] + list(so) + list(ss))
print("種類 | 枚数 | 勾配 SR/元 | 高周波 SR/元 | 強輪郭割合 SR/元 | 元の勾配 | SRの勾配")
for t, rs in res.items():
    r = np.array(rs)
    print(f"{t} | {len(rs)} | {np.mean(r[:,0]):.2f} | {np.mean(r[:,1]):.2f} | {np.mean(r[:,2]):.2f} | {np.mean(r[:,3]):.4f} | {np.mean(r[:,6]):.4f}")
