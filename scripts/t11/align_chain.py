"""T11: 連鎖生成した顔アップ(枠・倍率が揃っている)の位置合わせ。全視点で共通の「注視点(ワールドxyz)とカメラ距離」と、視点ごとの方位ずれだけを推定する(t9環境)。
独立生成の顔アップでは視点ごとに倍率・ずれを推定したが(align_closeups.py)、連鎖生成は同じ枠を保つので共通にして拘束を強める。
  gs_wsl.sh align_chain.py --params P --views VIEWS_JSON(file,az,nameのリスト) --out ALIGNED_JSON [--sh 3]
出力は VIEWS_JSON と同形式。zoom/tz/sx/sy は共通注視点を各方位のカメラの右/上方向に投影して表したもの(build_dataset.pyが読める形)。"""
import argparse, json, math
import numpy as np, torch, torch.nn.functional as F
from PIL import Image
from gsplat import rasterization
ap = argparse.ArgumentParser()
ap.add_argument("--params", required=True); ap.add_argument("--views", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--W", type=int, default=1024); ap.add_argument("--H", type=int, default=1280); ap.add_argument("--fig", type=float, default=0.875)
ap.add_argument("--res", type=int, default=4); ap.add_argument("--blur", type=float, default=2.0); ap.add_argument("--sh", type=int, default=3)
ap.add_argument("--iters", type=int, default=400)
a = ap.parse_args(); dev = "cuda"
P = {k: v.to(dev) for k, v in torch.load(a.params).items()}
D = 8.0; w, h = a.W // a.res, a.H // a.res; fx0 = a.H * a.fig * D / 2.0 / a.res
CV = torch.diag(torch.tensor([1., -1., -1., 1.], device=dev))
def blur(x, s):
    k = int(s * 3) * 2 + 1; g = torch.exp(-(torch.arange(k, device=dev) - k // 2) ** 2 / (2 * s * s)); g = g / g.sum()
    x = F.conv2d(F.pad(x, (k // 2, k // 2, 0, 0), mode="replicate"), g.view(1, 1, 1, k).expand(3, 1, 1, k), groups=3)
    return F.conv2d(F.pad(x, (0, 0, k // 2, k // 2), mode="replicate"), g.view(1, 1, k, 1).expand(3, 1, k, 1), groups=3)
def cam(az_deg, tgt, dist):
    az = torch.as_tensor(az_deg, device=dev, dtype=torch.float32) * math.pi / 180; z0 = torch.zeros((), device=dev)
    c = torch.stack([torch.sin(az), -torch.cos(az), z0]); fwd = -c
    right = torch.cross(fwd, torch.tensor([0., 0., 1.], device=dev), dim=0); right = right / right.norm(); up = torch.cross(right, fwd, dim=0)
    pos = tgt + dist * c; c2w = torch.eye(4, device=dev); c2w[:3, 0] = right; c2w[:3, 1] = up; c2w[:3, 2] = -fwd; c2w[:3, 3] = pos
    return c2w, right, up
def render(az_deg, tgt, dist):
    c2w, _, _ = cam(az_deg, tgt, dist); vm = torch.linalg.inv(c2w @ CV)[None]
    K = torch.tensor([[[fx0, 0, w / 2], [0, fx0, h / 2], [0, 0, 1]]], device=dev)
    img, _, _ = rasterization(P["means"], F.normalize(P["quats"], dim=-1), torch.exp(P["scales"]), torch.sigmoid(P["opacities"]), torch.cat([P["sh0"], P["shN"]], 1), vm, K, w, h, sh_degree=a.sh, backgrounds=torch.ones(1, 3, device=dev), packed=False)
    return img.permute(0, 3, 1, 2)
views = json.load(open(a.views)); n = len(views)
tg = []
for v in views:
    im = Image.open(v["file"]).convert("RGBA").resize((w, h), Image.LANCZOS); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    tg.append(blur(torch.from_numpy(np.array(bg.convert("RGB"))).float().div(255).permute(2, 0, 1)[None].to(dev), a.blur))
q = torch.tensor([math.log(3.0), 0.0, 0.0, 0.6], device=dev, requires_grad=True)      # log zoom, tx, ty, tz (共通)
daz = torch.zeros(n, device=dev, requires_grad=True)                                   # 視点ごとの方位ずれ(単位: 5度)
opt = torch.optim.Adam([{"params": [q], "lr": 0.01}, {"params": [daz], "lr": 0.02}])
for it in range(a.iters):
    for g in opt.param_groups: g["lr"] *= 0.9965
    tot = 0
    for i in torch.randperm(n)[:6].tolist():
        r = render(float(views[i]["az"]) + daz[i] * 5.0, q[1:4], D / torch.exp(q[0]))
        loss = (blur(r, a.blur) - tg[i]).abs().mean() / 6; loss.backward(); tot += loss.item()
    opt.step(); opt.zero_grad()
    if it % 50 == 0: print(it, round(tot, 4), "zoom %.2f t=(%.3f,%.3f,%.3f)" % (math.exp(q[0].item()), *q[1:4].tolist()), flush=True)
out = []
with torch.no_grad():
    zoom = math.exp(q[0].item()); tgt = q[1:4]
    for i, v in enumerate(views):
        az = float(v["az"]) + daz[i].item() * 5.0; c2w, right, up = cam(torch.tensor(az, device=dev), tgt, D / zoom)
        base = torch.tensor([0., 0., tgt[2].item()], device=dev); d = tgt - base
        r = dict(v); r["az"] = az; r["zoom"] = zoom; r["tz"] = tgt[2].item(); r["sx"] = float((d * right).sum()); r["sy"] = float((d * up).sum()) - 0.0
        # sy は up 方向への成分。tz(高さ)は base に含めてあるので、水平成分だけを up 方向に投影し直す
        r["sy"] = float((torch.stack([tgt[0], tgt[1], torch.zeros((), device=dev)]) * up).sum())
        rr = render(az, tgt, D / zoom); r["align_loss"] = float((blur(rr, a.blur) - tg[i]).abs().mean()); out.append(r)
        print(v["name"], "az %.1f" % az, "loss %.4f" % r["align_loss"], flush=True)
json.dump(out, open(a.out, "w"), indent=1)
