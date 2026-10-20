"""T9: メッシュ連動ガウシアン層の学習(自前)。T8のマスター描画(views.json + RGBA画像)を教師にする。
メッシュ(頂点・三角形)は固定、学習するのは各ガウシアンの法線方向のずれ・局所の回転・大きさ・色・不透明度だけ。
  python scripts/t9/train.py --master <T8 master dir> --mesh experiments/T9/mesh_60k.npz --out experiments/T9/runs/a --iters 15000 [--n 300000] [--scale 0.5]
出力: model.pt、test_*.png(評価視点の描画)、metrics.json、gaussians.ply(標準3DGS形式)
"""
import argparse
import json
import math
import os
import sys
import time

import cv2
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meshgs import MeshGaussians, intrinsics, ssim_loss_map, view_matrix  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--master", required=True)
ap.add_argument("--mesh", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--iters", type=int, default=15000)
ap.add_argument("--n", type=int, default=300000, help="ガウシアン数(三角形の面積に比例して配る)")
ap.add_argument("--scale", type=float, default=1.0, help="学習・評価の解像度の倍率(マスター基準。0.5なら1024²)")
ap.add_argument("--types", default="ring,upper,face,lower")
ap.add_argument("--lam_ssim", type=float, default=0.2)
ap.add_argument("--lam_off", type=float, default=0.05, help="法線方向のずれの正則化")
ap.add_argument("--lr_h", type=float, default=2e-4)
ap.add_argument("--lr_s", type=float, default=5e-3)
ap.add_argument("--lr_q", type=float, default=2e-3)
ap.add_argument("--lr_c", type=float, default=2.5e-3)
ap.add_argument("--lr_o", type=float, default=2e-2)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--cache", default=os.path.expanduser("~/work/t9cache"), help="縮小済み画像のキャッシュ(WSLの外のドライブからの読み込みが遅いため)")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
torch.manual_seed(a.seed)
dev = "cuda"

meta = json.load(open(os.path.join(a.master, "views.json")))
S0, fx0 = meta["size"], meta["fx"]
S = int(round(S0 * a.scale))
K = intrinsics(fx0 * S / S0, S)
types = a.types.split(",")
views = [v for v in meta["views"] if v["type"] in types and os.path.exists(os.path.join(a.master, "images", v["name"]))]
train_v = [v for v in views if v["split"] != "test"]
test_v = [v for v in views if v["split"] == "test"]
print(f"views train {len(train_v)} test {len(test_v)} size {S}")


def load(v):
    im = np.asarray(Image.open(os.path.join(a.master, "images", v["name"])).convert("RGBA")).astype(np.float32) / 255.0
    rgb = im[..., :3] * im[..., 3:4]                        # 黒背景に合成(直線アルファ乗算)
    if S != S0:
        rgb = cv2.resize(rgb, (S, S), interpolation=cv2.INTER_AREA)
    return torch.from_numpy((rgb * 255 + 0.5).astype(np.uint8))


t0 = time.time()
os.makedirs(a.cache, exist_ok=True)


def load_cached(v):
    p = os.path.join(a.cache, f"s{S}_{v['name'].replace('.png', '.npy')}")
    if os.path.exists(p):
        return torch.from_numpy(np.load(p))
    t = load(v)
    np.save(p, t.numpy())
    return t


train_img = [load_cached(v) for v in train_v]
test_img = [load_cached(v) for v in test_v]
train_vm = [view_matrix(v["c2w_blender"]) for v in train_v]
test_vm = [view_matrix(v["c2w_blender"]) for v in test_v]
print("loaded images in %.0fs" % (time.time() - t0))

m = np.load(a.mesh)
model = MeshGaussians(m["verts"], m["faces"], m["vcolor"], n_gaussians=a.n, seed=a.seed, device=dev)
print("gaussians", model.n, "faces", len(model.Fc), "spacing mm %.2f" % (model.spacing * 1000))

opt = torch.optim.Adam([
    {"params": [model.h], "lr": a.lr_h},
    {"params": [model.log_s], "lr": a.lr_s},
    {"params": [model.q_local], "lr": a.lr_q},
    {"params": [model.sh0], "lr": a.lr_c},
    {"params": [model.logit_op], "lr": a.lr_o}], eps=1e-15)
sched_gamma = 0.01 ** (1.0 / a.iters)                         # 最後に学習率が1/100になる指数減衰


def to_f(img_u8):
    return img_u8.to(dev).float().div(255.0).permute(2, 0, 1)[None]


@torch.no_grad()
def evaluate(save_prefix=None):
    import lpips
    lp = lpips.LPIPS(net="vgg").to(dev).eval()
    rows = []
    for i, v in enumerate(test_v):
        gt = to_f(test_img[i])
        pr, al, _ = model.render(test_vm[i], K, S)
        pr = pr.permute(2, 0, 1)[None]
        fg = (gt.max(1, keepdim=True).values[0, 0] > 0.02).cpu().numpy().astype(np.uint8)
        roi = cv2.dilate(fg, np.ones((int(25 * S / 2048) * 2 + 1,) * 2, np.uint8)) > 0
        y0, y1 = np.where(roi.any(1))[0][[0, -1]]
        x0, x1 = np.where(roi.any(0))[0][[0, -1]]
        mse = float(((pr - gt) ** 2)[0].mean(0).cpu().numpy()[roi].mean())
        cg, cp = gt[..., y0:y1 + 1, x0:x1 + 1], pr[..., y0:y1 + 1, x0:x1 + 1]
        ss = float(ssim_loss_map(cp, cg).mean())
        lv = float(lp(cp * 2 - 1, cg * 2 - 1).mean())
        rows.append({"name": v["name"], "type": v["type"], "psnr": -10 * math.log10(max(mse, 1e-10)), "ssim": ss, "lpips": lv})
        if save_prefix and (i % 6 == 0):
            both = torch.cat([gt, pr], 3)[0].permute(1, 2, 0).cpu().numpy()
            Image.fromarray((both * 255).astype(np.uint8)).save(f"{save_prefix}{v['type']}_{v['name']}")
    out = {"n_views": len(rows), "psnr": float(np.mean([r["psnr"] for r in rows])), "ssim": float(np.mean([r["ssim"] for r in rows])),
           "lpips": float(np.mean([r["lpips"] for r in rows]))}
    for t in types:
        rr = [r for r in rows if r["type"] == t]
        if rr:
            out[t] = {"n": len(rr), "psnr": float(np.mean([r["psnr"] for r in rr])), "ssim": float(np.mean([r["ssim"] for r in rr])),
                      "lpips": float(np.mean([r["lpips"] for r in rr]))}
    return out, rows


t0 = time.time()
order = []
for it in range(1, a.iters + 1):
    if not order:
        order = list(np.random.permutation(len(train_v)))
    i = order.pop()
    gt = to_f(train_img[i])
    pr, al, info = model.render(train_vm[i], K, S)
    pr_ = pr.permute(2, 0, 1)[None]
    l1 = (pr_ - gt).abs().mean()
    ssim = ssim_loss_map(pr_, gt).mean()
    off = ((model.h / (0.5 * model.spacing)) ** 2).mean()
    loss = (1 - a.lam_ssim) * l1 + a.lam_ssim * (1 - ssim) + a.lam_off * off
    opt.zero_grad(set_to_none=True)
    loss.backward()
    opt.step()
    for gp in opt.param_groups:
        gp["lr"] *= sched_gamma
    with torch.no_grad():
        model.logit_op.clamp_(-8, 8)
    if it % 500 == 0 or it == 1:
        el = time.time() - t0
        print(f"it {it} loss {loss.item():.4f} l1 {l1.item():.4f} ssim {ssim.item():.4f} off {off.item():.3f} {it / el:.1f} it/s mem {torch.cuda.max_memory_allocated() / 1e9:.1f}GB "
              f"| scale mm {(torch.exp(model.log_s) * math.sqrt(model.area0.mean())).mean(0).detach().cpu().numpy().round(4) * 1000} op {torch.sigmoid(model.logit_op).mean().item():.3f}", flush=True)

train_sec = time.time() - t0
torch.save({k: v for k, v in model.state_dict().items()}, os.path.join(a.out, "model.pt"))
res, rows = evaluate(os.path.join(a.out, "test_"))
res.update({"train_sec": train_sec, "n_gaussians": model.n, "iters": a.iters, "size": S, "args": vars(a)})
json.dump(res, open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
model.export_ply(os.path.join(a.out, "gaussians.ply"))
print("EVAL", json.dumps({k: res[k] for k in ("psnr", "ssim", "lpips", "n_gaussians", "train_sec")}))
print("T9_TRAIN_DONE")
