"""T8: テクスチャ画像を超解像する(WSLの sr 環境。spandrel で公式配布の Real-ESRGAN 重みを安全読み込み)。
  ~/venvs/sr/bin/python sr_texture.py --src basecolor_1.jpg --weights RealESRGAN_x4plus_anime_6B.pth --out out.png --final 8192
x4で超解像 → --final の大きさに面積平均で縮小して保存(例: 4096→x4=16384→8192)。タイルで処理し、境界は重なり部分を捨てて継ぎ目を避ける。
"""
import argparse, time
import numpy as np, torch, cv2
from PIL import Image
from spandrel import ModelLoader

Image.MAX_IMAGE_PIXELS = None
ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--weights", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--final", type=int, default=8192)
ap.add_argument("--tile", type=int, default=384)
ap.add_argument("--pad", type=int, default=24)
ap.add_argument("--fp16", action="store_true")
a = ap.parse_args()

model = ModelLoader().load_from_file(a.weights).cuda().eval()
sc = model.scale
img = np.asarray(Image.open(a.src).convert("RGB"))
H, W, _ = img.shape
out = np.zeros((H * sc, W * sc, 3), np.uint8)
t0 = time.time()
n = 0
with torch.no_grad():
    for y in range(0, H, a.tile):
        for x in range(0, W, a.tile):
            y0, x0 = max(y - a.pad, 0), max(x - a.pad, 0)
            y1, x1 = min(y + a.tile + a.pad, H), min(x + a.tile + a.pad, W)
            t = torch.from_numpy(img[y0:y1, x0:x1]).permute(2, 0, 1)[None].float().cuda() / 255.0
            with torch.autocast("cuda", dtype=torch.float16, enabled=a.fp16):
                o = model(t)
            o = (o.clamp(0, 1)[0].permute(1, 2, 0).float().cpu().numpy() * 255 + 0.5).astype(np.uint8)
            oy, ox = (y - y0) * sc, (x - x0) * sc
            hh, ww = min(a.tile, H - y) * sc, min(a.tile, W - x) * sc
            out[y * sc:y * sc + hh, x * sc:x * sc + ww] = o[oy:oy + hh, ox:ox + ww]
            n += 1
print(f"tiles {n} {time.time() - t0:.1f}s model_scale x{sc}")
if a.final != out.shape[0]:
    out = cv2.resize(out, (a.final, a.final), interpolation=cv2.INTER_AREA)
Image.fromarray(out).save(a.out)
print("saved", a.out, out.shape)
