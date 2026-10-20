"""T8: 出力側の超解像の評価(gstyle 環境)。4096²の正解に対し、(a)2048描画をbicubic 2倍 (b)2048描画を超解像2倍 (c)3DGSを4096で直接描画 を比べる。
  python compare_sr.py --gt DIR(4096正解PNG, RGBA) --dirs bicubic=DIR sr=DIR native=DIR --out json
指標: PSNR / LPIPS(vgg) / 輪郭帯の鮮鋭度比(描画の勾配強度/正解) / 高周波比(ラプラシアン分散 描画/正解)。ROI=正解被写体を膨張した領域。"""
import argparse, json, os, math
import cv2, lpips, numpy as np, torch
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("--gt", nargs="+", required=True); ap.add_argument("--dirs", nargs="+", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
lp = lpips.LPIPS(net="vgg").cuda().eval()
def lum(x): return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
def grad(l): return np.sqrt((cv2.Sobel(l, cv2.CV_32F, 1, 0, ksize=3) / 8) ** 2 + (cv2.Sobel(l, cv2.CV_32F, 0, 1, ksize=3) / 8) ** 2)
labels = [d.split("=", 1) for d in a.dirs]
res = {lab: [] for lab, _ in labels}
for gdir in a.gt:
    for f in sorted(os.listdir(os.path.join(gdir, "images"))):
        im = np.asarray(Image.open(os.path.join(gdir, "images", f)).convert("RGBA")).astype(np.float32) / 255
        gt, al = im[..., :3] * im[..., 3:4], im[..., 3]
        roi = cv2.dilate((al > 0.5).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
        gl, gg = lum(gt), grad(lum(gt))
        edge = (cv2.dilate((gg > 0.05).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & roi
        inner = cv2.erode((al > 0.99).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        lap_g = float((cv2.Laplacian(gl, cv2.CV_32F, ksize=3)[inner] ** 2).mean())
        for lab, d in labels:
            p = os.path.join(d, f)
            if not os.path.exists(p): continue
            r = np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255
            assert r.shape == gt.shape, (p, r.shape, gt.shape)
            mse = float(((r - gt) ** 2)[roi].mean())
            t = lambda x: torch.from_numpy(x).permute(2, 0, 1)[None].contiguous().cuda() * 2 - 1
            ys, xs = np.where(roi); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            with torch.no_grad():   # VRAMを節約するため 1024px のタイルに分けて平均(学習と同居しても落ちない)
                tv = []
                for ty in range(y0, y1, 1024):
                    for tx in range(x0, x1, 1024):
                        a_, b_ = r[ty:min(ty + 1024, y1), tx:min(tx + 1024, x1)], gt[ty:min(ty + 1024, y1), tx:min(tx + 1024, x1)]
                        if min(a_.shape[:2]) >= 64: tv.append(float(lp(t(a_), t(b_)).mean()))
                lv = float(np.mean(tv))
            rl = lum(r)
            res[lab].append({"name": f, "psnr": -10 * math.log10(max(mse, 1e-10)), "lpips": lv,
                             "sharp_edge": float(grad(rl)[edge].mean() / max(gg[edge].mean(), 1e-6)),
                             "hf_ratio": float((cv2.Laplacian(rl, cv2.CV_32F, ksize=3)[inner] ** 2).mean() / max(lap_g, 1e-12))})
summary = {lab: {k: float(np.mean([x[k] for x in rows])) for k in ("psnr", "lpips", "sharp_edge", "hf_ratio")} | {"n": len(rows)} for lab, rows in res.items()}
json.dump({"summary": summary, "views": res}, open(a.out, "w"), indent=1)
for lab, s in summary.items(): print(lab, {k: round(v, 4) for k, v in s.items()})
