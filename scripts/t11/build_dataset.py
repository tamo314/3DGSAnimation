"""T11: 切り抜き済みRGBA画像 + 名目の方位角 から、3DGS学習用のNeRF-synthetic形式データを作る。
  python -I build_dataset.py VIEWS_JSON OUT_DIR [--hold name1,name2] [--W 1024 --H 1280]
VIEWS_JSON: [{"file": "path.png", "az": 方位角deg(0=正面, +=カメラがキャラの左へ回る), "el": 仰角deg}, ...]
"zoom"(と注視点のz "tz")を持つ項目は顔アップ等で、正規化せずに使う(fxはzoom倍)。
各画像を「頭頂〜足裏の高さ・足元の左右中心」で正規化して同じ位置・大きさに揃える
(生成画像はカメラ距離・位置が視点ごとにばらつくため。キャラの高さ=ワールドの2.0、足裏z=-1)。
カメラは中心(0,0,0)を向く弱透視(距離8)。仰角が0でない画像は高さの正規化が正確でない(足元基準)。"""
import argparse, json, math, os
import numpy as np
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("views"); ap.add_argument("out")
ap.add_argument("--hold", default=""); ap.add_argument("--W", type=int, default=1024); ap.add_argument("--H", type=int, default=1280)
ap.add_argument("--fig", type=float, default=0.875, help="キャラ高さが画像高さに占める割合")
ap.add_argument("--tele", action="store_true", help="顔アップをカメラ距離ではなく焦点距離の倍率で表す(弱透視。frame に focal_mult を入れる)")
a = ap.parse_args()
W, H = a.W, a.H; D = 8.0
fig_px = H * a.fig; fx = fig_px * D / 2.0
fovx = 2 * math.atan(W / 2 / fx)
hold = set(a.hold.split(",")) if a.hold else set()
for sp in ("train", "test"): os.makedirs(os.path.join(a.out, sp), exist_ok=True)
frames = {"train": [], "test": []}
def lookat_c2w(az, el, tz=0.0, dist=D, sx=0.0, sy=0.0):
    az, el = math.radians(az), math.radians(el)
    c = np.array([math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)]); fwd = -c
    right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    tgt = np.array([0, 0, tz]) + right * sx + up * sy; pos = tgt + dist * c
    c2w = np.eye(4); c2w[:3, 0] = right; c2w[:3, 1] = up; c2w[:3, 2] = -fwd; c2w[:3, 3] = pos
    return c2w
for v in json.load(open(a.views)):
    im = Image.open(v["file"]).convert("RGBA"); al = np.asarray(im)[:, :, 3]
    if "zoom" in v:                       # 顔アップ等: 正規化せず、キャンバスに合わせて拡縮するだけ。カメラ距離=D/zoom、注視点=(0,0,tz)+画面内ずれ(sx,sy)
        out = im.resize((W, H), Image.LANCZOS)
        name = v["name"]; sp = "test" if name in hold else "train"; out.save(os.path.join(a.out, sp, name + ".png"))
        c = lookat_c2w(v["az"], v.get("el", 0), v.get("tz", 0.0), D if a.tele else D / v["zoom"], v.get("sx", 0.0), v.get("sy", 0.0))
        fr = {"file_path": f"{sp}/{name}", "transform_matrix": c.tolist(), "closeup": True}
        if a.tele: fr["focal_mult"] = v["zoom"]
        frames[sp].append(fr); continue
    ys = np.where((al > 127).any(axis=1))[0]; yt, yb = ys[0], ys[-1]
    hgt = yb - yt; s = fig_px / hgt
    rows = np.arange(int(yb - 0.22 * hgt), int(yb - 0.03 * hgt))
    xs = np.where((al[rows] > 127).any(axis=0))[0]; cx = (xs[0] + xs[-1]) / 2
    # 出力座標 u = s*(x - cx) + W/2, y' = s*(y - yb) + (H + fig_px)/2
    ty = (H + fig_px) / 2 - s * yb
    M = np.array([[s, 0, W / 2 - s * cx], [0, s, ty], [0, 0, 1]])
    Mi = np.linalg.inv(M)
    out = im.transform((W, H), Image.AFFINE, tuple(Mi[:2].reshape(-1)), resample=Image.BICUBIC)
    name = os.path.splitext(os.path.basename(v["file"]))[0] if "name" not in v else v["name"]
    sp = "test" if name in hold else "train"
    out.save(os.path.join(a.out, sp, name + ".png"))
    c = lookat_c2w(v["az"], v.get("el", 0))
    frames[sp].append({"file_path": f"{sp}/{name}", "transform_matrix": c.tolist()})
for sp in frames:
    json.dump({"camera_angle_x": fovx, "frames": frames[sp]}, open(os.path.join(a.out, f"transforms_{sp}.json"), "w"), indent=1)
print({k: len(v) for k, v in frames.items()}, "fovx", fovx)
