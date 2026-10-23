"""T11: 超解像した窓画像から、(RGBA化+カメラ厳密計算した)views JSON を作る。
  python make_sr_views.py BASE_VIEWS.json OUT.json FACE_RGBA_DIR OUT_RGBA_DIR PFX x0 y0 w SR_DIR [SR_DIR2 ...]
窓画像の寄りカメラ: 倍率 = 顔アップの倍率 * 1122/w、注視点のずれ = 窓中心の顔アップ上のずれ(sx,sy。弱透視)。
アルファは顔アップのアルファを同じ窓で切り出して拡大して使う(窓画像は顔アップと画素が重なるため)。"""
import sys, json, glob, re, os
import numpy as np
from PIL import Image
base, out, frgba, orgba, pfx = sys.argv[1:6]; x0, y0, w = map(int, sys.argv[6:9]); srdirs = sys.argv[9:]
h = round(w * 1402 / 1122); os.makedirs(orgba, exist_ok=True)
views = json.load(open(base)); face0 = next(v for v in views if v.get("name") == "c10_az+000")
z0, tz0, sx0, sy0 = face0["zoom"], face0["tz"], face0["sx"], face0["sy"]
D, fx = 8.0, 1120 * 8.0 / 2; kw = D / (fx * z0) * 1024 / 1122      # 顔アップ画像1px(1122基準)あたりのワールド長
cx, cy = x0 + w / 2 - 561, y0 + h / 2 - 701
n = 0
for sd in srdirs:
    for f in sorted(glob.glob(f"{sd}/sr_*_az*.png")):
        az = int(re.search(r"az([+-]\d+)", f).group(1))
        a = Image.open(f"{frgba}/face_az{az:+04d}.png").getchannel("A").crop((x0, y0, x0 + w, y0 + h)).resize((1122, 1402), Image.BICUBIC)
        im = Image.open(f).convert("RGB").resize((1122, 1402), Image.LANCZOS); im.putalpha(a)
        nm = f"{pfx}_az{az:+04d}"; im.save(f"{orgba}/{nm}.png")
        views.append({"file": f"{orgba}/{nm}.png".replace(chr(92), "/"), "az": az, "name": nm, "zoom": z0 * 1122 / w,
                      "tz": tz0, "sx": sx0 + cx * kw, "sy": sy0 - cy * kw}); n += 1
json.dump(views, open(out, "w"), indent=1); print("added", n, "total", len(views), "last", views[-1])
