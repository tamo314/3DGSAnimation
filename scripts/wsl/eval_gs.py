"""T8: 学習済み3DGS(PLY)を、マスターの評価視点(split=test)で描画して正解(Blender描画)と比べる。WSLの gstyle 環境で実行。
  PYTHONPATH=~/ext/g-style ~/venvs/gstyle/bin/python eval_gs.py --ply <point_cloud.ply> --master <master dir> --out <dir> [--sh 3] [--scale 1.0] [--types ring,face]
公式3DGS系コード(GaussianModel / rasterizer)は無改変のまま import して使い、指標とエッジ解析は自前。
指標(全てROI=正解の被写体(α>0.5)を25px箱で膨張した領域、黒背景合成の乗算済みRGBで測る):
 PSNR / SSIM / LPIPS(vgg) / 輪郭帯PSNR(正解の輝度・αの勾配が強い画素の周囲) / ベタ面PSNR(勾配が極小かつ内部) /
 鮮鋭度比(輪郭帯での描画の勾配強度÷正解) / ベタ面ノイズ比(ベタ面のラプラシアン分散 描画÷正解) / シルエットIoUと縁帯のα誤差
"""
import argparse
import json
import math
import os
from types import SimpleNamespace

import cv2
import lpips
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from gaussian_renderer import render
from scene.cameras import Camera
from scene.gaussian_model import GaussianModel

ap = argparse.ArgumentParser()
ap.add_argument("--ply", required=True)
ap.add_argument("--master", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--sh", type=int, default=0)
ap.add_argument("--scale", type=float, default=1.0, help="描画解像度の倍率(マスター基準。0.5なら1024²。GTは面積平均で縮小)")
ap.add_argument("--types", default="ring,upper,face,lower")
ap.add_argument("--split", default="test")
ap.add_argument("--save", type=int, default=2, help="種類ごとに保存する画像枚数")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

meta = json.load(open(os.path.join(a.master, "views.json")))
S0 = meta["size"]
S = int(round(S0 * a.scale))
fx = meta["fx"]
fov = 2 * math.atan(S0 / (2 * fx))
views = [v for v in meta["views"] if v["type"] in a.types.split(",") and v["split"] == a.split and os.path.exists(os.path.join(a.master, "images", v["name"]))]

g = GaussianModel(a.sh)
g.load_ply(a.ply)
if a.sh > 0:
    # G-Styleリポジトリの load_ply は f_rest(SH2次以上)を読まない(SH0専用の改変)ため、PLYから自前で読んで差し込む
    from plyfile import PlyData
    el = PlyData.read(a.ply).elements[0]
    names = sorted([p.name for p in el.properties if p.name.startswith("f_rest_")], key=lambda x: int(x.split("_")[-1]))
    assert len(names) == 3 * (a.sh + 1) ** 2 - 3, len(names)
    fr = np.stack([np.asarray(el[n]) for n in names], axis=1).reshape(len(el.data), 3, (a.sh + 1) ** 2 - 1)
    g._features_rest = torch.nn.Parameter(torch.tensor(fr, dtype=torch.float, device="cuda").transpose(1, 2).contiguous())
pipe = SimpleNamespace(convert_SHs_python=False, compute_cov3D_python=False, debug=False)
n_g = int(g.get_xyz.shape[0])
sc_ = g.get_scaling.detach().max(1).values.cpu().numpy()
op_ = g.get_opacity.detach().cpu().numpy().ravel()
gstat = {"n_gaussians": n_g, "ply_mb": os.path.getsize(a.ply) / 1e6, "scale_max_median_mm": float(np.median(sc_) * 1000),
         "scale_max_p10_mm": float(np.percentile(sc_, 10) * 1000), "scale_max_p90_mm": float(np.percentile(sc_, 90) * 1000),
         "opacity_median": float(np.median(op_)), "opacity_lt_0.1_frac": float((op_ < 0.1).mean())}
print("GSTAT", json.dumps(gstat))

lp = lpips.LPIPS(net="vgg").cuda().eval()


def ssim_map(x, y, win=11, sigma=1.5):
    c = torch.arange(win, dtype=torch.float32, device=x.device) - win // 2
    k = torch.exp(-(c ** 2) / (2 * sigma ** 2))
    k = k / k.sum()
    k2 = (k[:, None] * k[None, :])[None, None].repeat(3, 1, 1, 1)
    f = lambda t: F.conv2d(t, k2, padding=win // 2, groups=3)
    mx, my = f(x), f(y)
    sxx, syy, sxy = f(x * x) - mx ** 2, f(y * y) - my ** 2, f(x * y) - mx * my
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    return (((2 * mx * my + C1) * (2 * sxy + C2)) / ((mx ** 2 + my ** 2 + C1) * (sxx + syy + C2))).mean(1)[0]


def lum(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def grad_mag(l):
    gx = cv2.Sobel(l, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(l, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    return np.sqrt(gx ** 2 + gy ** 2)


def lap_var(l, mask):
    lp_ = cv2.Laplacian(l, cv2.CV_32F, ksize=3)
    return float((lp_[mask] ** 2).mean()) if mask.any() else float("nan")


def psnr(x, y, m):
    mse = float(((x - y) ** 2)[m].mean()) if m.any() else float("nan")
    return -10 * math.log10(max(mse, 1e-10))


def load_gt(v):
    im = np.asarray(Image.open(os.path.join(a.master, "images", v["name"])).convert("RGBA")).astype(np.float32) / 255.0
    rgb = im[..., :3] * im[..., 3:4]
    al = im[..., 3]
    if S != S0:
        rgb = cv2.resize(rgb, (S, S), interpolation=cv2.INTER_AREA)
        al = cv2.resize(al, (S, S), interpolation=cv2.INTER_AREA)
    return rgb, al


rows = []
saved = {}
for v in views:
    gt, gal = load_gt(v)
    c2w = np.array(v["c2w_blender"])
    R = c2w[:3, :3] @ np.diag([1.0, -1.0, -1.0])        # COLMAP規約のカメラ→世界回転(Inria系のR)
    T = -R.T @ c2w[:3, 3]
    img = torch.from_numpy(gt).permute(2, 0, 1).contiguous()
    cam = Camera(colmap_id=v["k"], R=R, T=T, FoVx=fov, FoVy=fov, image=img, gt_alpha_mask=None, image_name=v["name"], uid=v["k"], data_device="cuda")
    with torch.no_grad():
        outs = []
        for bgv in (0.0, 1.0):
            bg = torch.full((3,), bgv, device="cuda")
            outs.append(render(cam, g, pipe, bg)["render"].clamp(0, 1))
    rb, rw = outs
    ral = (1 - (rw - rb).mean(0)).clamp(0, 1).cpu().numpy()
    rgb = rb.permute(1, 2, 0).cpu().numpy()
    fg = gal > 0.5
    roi = cv2.dilate(fg.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    lg = lum(gt)
    gm = np.maximum(grad_mag(lg), grad_mag(gal))
    edge = (cv2.dilate((gm > 0.05).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & roi
    interior = cv2.erode((gal > 0.99).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    flat = interior & (cv2.dilate(gm, np.ones((9, 9), np.uint8)) < 0.01)
    lr = lum(rgb)
    gr = np.maximum(grad_mag(lr), grad_mag(ral))
    y0, y1 = np.where(roi.any(1))[0][[0, -1]]
    x0, x1 = np.where(roi.any(0))[0][[0, -1]]
    crop = lambda t: t[y0:y1 + 1, x0:x1 + 1]
    tg = torch.from_numpy(crop(gt)).permute(2, 0, 1)[None].contiguous().cuda()
    tr = torch.from_numpy(crop(rgb)).permute(2, 0, 1)[None].contiguous().cuda()
    with torch.no_grad():
        sm = ssim_map(tr, tg).cpu().numpy()
        lpv = float(lp(tr * 2 - 1, tg * 2 - 1).mean())
    roic = crop(roi)
    sil_g, sil_r = gal > 0.5, ral > 0.5
    band = (cv2.dilate(sil_g.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(int) - cv2.erode(sil_g.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(int)) > 0
    row = {
        "name": v["name"], "type": v["type"],
        "psnr_roi": psnr(rgb, gt, roi), "psnr_full": psnr(rgb, gt, np.ones_like(roi)),
        "ssim_roi": float(sm[roic].mean()), "lpips": lpv,
        "psnr_edge": psnr(rgb, gt, edge), "psnr_flat": psnr(rgb, gt, flat),
        "sharp_ratio_edge": float(gr[edge].mean() / max(gm[edge].mean(), 1e-6)),
        "flat_noise_ratio": lap_var(lr, flat) / max(lap_var(lg, flat), 1e-12),
        "flat_px": int(flat.sum()), "edge_px": int(edge.sum()),
        "sil_iou": float((sil_g & sil_r).sum() / max((sil_g | sil_r).sum(), 1)),
        "alpha_err_band": float(np.abs(ral - gal)[band].mean()) if band.any() else float("nan"),
        "fg_frac": float(fg.mean()),
    }
    rows.append(row)
    if saved.get(v["type"], 0) < a.save:
        saved[v["type"]] = saved.get(v["type"], 0) + 1
        stem = v["name"][:-4]
        for nm, arr in (("render", rgb), ("gt", gt), ("alpha", ral), ("alpha_gt", gal)):
            arr = arr if arr.ndim == 3 else arr
            Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(a.out, f"{stem}_{nm}.png"))
    print(v["name"], {k: (round(x, 3) if isinstance(x, float) else x) for k, x in row.items() if k not in ("name", "type")}, flush=True)

summary = {}
for t in sorted({r["type"] for r in rows}) + ["all"]:
    rs = [r for r in rows if t == "all" or r["type"] == t]
    summary[t] = {k: float(np.nanmean([r[k] for r in rs])) for k in rs[0] if k not in ("name", "type")}
    summary[t]["n_views"] = len(rs)
json.dump({"ply": a.ply, "scale": a.scale, "size": S, "sh": a.sh, "gaussians": gstat, "summary": summary, "views": rows},
          open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
print("SUMMARY", json.dumps(summary, indent=1))
