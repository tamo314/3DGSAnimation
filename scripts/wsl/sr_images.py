"""T8: ディレクトリ内のPNGを超解像して2倍にする(sr 環境)。x4モデルで4倍→面積平均で半分(=2倍)。
  ~/venvs/sr/bin/python sr_images.py --weights W --src DIR --out DIR2 [--factor 2]"""
import argparse, os, numpy as np, torch, cv2
from PIL import Image
from spandrel import ModelLoader
ap = argparse.ArgumentParser(); ap.add_argument("--weights", required=True); ap.add_argument("--src", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--factor", type=int, default=2); ap.add_argument("--tile", type=int, default=512); ap.add_argument("--pad", type=int, default=24)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
model = ModelLoader().load_from_file(a.weights).cuda().eval(); sc = model.scale
for f in sorted(os.listdir(a.src)):
    if not f.endswith(".png"): continue
    img = np.asarray(Image.open(os.path.join(a.src, f)).convert("RGB")).copy(); H, W, _ = img.shape
    out = np.zeros((H * sc, W * sc, 3), np.uint8)
    with torch.no_grad():
        for y in range(0, H, a.tile):
            for x in range(0, W, a.tile):
                y0, x0, y1, x1 = max(y - a.pad, 0), max(x - a.pad, 0), min(y + a.tile + a.pad, H), min(x + a.tile + a.pad, W)
                t = torch.from_numpy(img[y0:y1, x0:x1]).permute(2, 0, 1)[None].float().cuda() / 255.0
                with torch.autocast("cuda", dtype=torch.float16):
                    o = model(t)
                o = (o.clamp(0, 1)[0].permute(1, 2, 0).float().cpu().numpy() * 255 + 0.5).astype(np.uint8)
                hh, ww = min(a.tile, H - y) * sc, min(a.tile, W - x) * sc
                out[y * sc:y * sc + hh, x * sc:x * sc + ww] = o[(y - y0) * sc:(y - y0) * sc + hh, (x - x0) * sc:(x - x0) * sc + ww]
    out = cv2.resize(out, (W * a.factor, H * a.factor), interpolation=cv2.INTER_AREA)
    Image.fromarray(out).save(os.path.join(a.out, f))
print("done", a.src, "->", a.out)
