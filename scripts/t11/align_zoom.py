"""T11: (部位アップ用) 方位は名目値に固定し、倍率・注視点の高さ・左右のずれだけを、粗い3DGS(c9など)に合わせて推定する(t9環境)。元: align_closeups.py
T11: 顔アップ画像のカメラ(方位・倍率・注視点の高さ・画像内のずれ)を、全身だけで学習した粗い3DGSに合わせて推定する(t9環境)。
鮮明な顔アップとぼやけた描画を比べるので、両方を同じ強さでぼかして比較する。倍率・注視点高さは格子探索→勾配法で詰める。
  gs_wsl.sh align_closeups.py --params P --views VIEWS_JSON(zoom/tz/azの名目値入り、fileはRGBA) --out ALIGNED_JSON
出力は VIEWS_JSON と同形式で、az(補正後)・zoom・tz・shift を埋めたもの。"""
import argparse, json, math, os
import numpy as np, torch, torch.nn.functional as F
from PIL import Image
from gsplat import rasterization
ap = argparse.ArgumentParser()
ap.add_argument("--params", required=True); ap.add_argument("--views", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--zoom_grid", default="5.5,6.5,7.5,8.5,9.5"); ap.add_argument("--tz_grid", default="0.60,0.70,0.80,0.90"); ap.add_argument("--W", type=int, default=1024); ap.add_argument("--H", type=int, default=1280); ap.add_argument("--fig", type=float, default=0.875)
ap.add_argument("--res", type=int, default=4, help="比較解像度の縮小率"); ap.add_argument("--blur", type=float, default=2.0)
a = ap.parse_args(); dev = "cuda"
P = {k: v.to(dev) for k, v in torch.load(a.params).items()}
D = 8.0; w, h = a.W // a.res, a.H // a.res; fx0 = a.H * a.fig * D / 2.0 / a.res
CV = torch.diag(torch.tensor([1., -1., -1., 1.], device=dev))
def blur(x, s):
    k = int(s * 3) * 2 + 1; g = torch.exp(-(torch.arange(k, device=dev) - k // 2) ** 2 / (2 * s * s)); g = g / g.sum()
    x = F.conv2d(F.pad(x, (k // 2, k // 2, 0, 0), mode="replicate"), g.view(1, 1, 1, k).expand(3, 1, 1, k), groups=3)
    return F.conv2d(F.pad(x, (0, 0, k // 2, k // 2), mode="replicate"), g.view(1, 1, k, 1).expand(3, 1, k, 1), groups=3)
def render(az_deg, tz, zoom, sx, sy):
    """zoom は焦点距離ではなくカメラ距離(D/zoom)で表す(gsplatはKへの勾配を返さないため)。sx,sy: 注視点を画面の右/上へずらす量(ワールド単位)。"""
    az = az_deg * math.pi / 180; z0 = torch.zeros((), device=dev); dist = D / zoom
    c = torch.stack([torch.sin(az), -torch.cos(az), z0]); fwd0 = -c
    right = torch.cross(fwd0, torch.tensor([0., 0., 1.], device=dev), dim=0); right = right / right.norm(); up = torch.cross(right, fwd0, dim=0)
    tgt = torch.stack([z0, z0, tz]) + right * sx + up * sy; pos = tgt + dist * c
    c2w = torch.eye(4, device=dev); c2w[:3, 0] = right; c2w[:3, 1] = up; c2w[:3, 2] = -fwd0; c2w[:3, 3] = pos
    vm = torch.linalg.inv(c2w @ CV)[None]; f = fx0
    K = torch.tensor([[[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]]], device=dev)
    img, _, _ = rasterization(P["means"], F.normalize(P["quats"], dim=-1), torch.exp(P["scales"]), torch.sigmoid(P["opacities"]), torch.cat([P["sh0"], P["shN"]], 1), vm, K, w, h, sh_degree=3, backgrounds=torch.ones(1, 3, device=dev), packed=False)
    return img.permute(0, 3, 1, 2)
views = json.load(open(a.views)); out = []
for v in views:
    im = Image.open(v["file"]).convert("RGBA").resize((w, h), Image.LANCZOS); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    tgt = blur(torch.from_numpy(np.asarray(bg.convert("RGB"))).float().div(255).permute(2, 0, 1)[None].to(dev), a.blur)
    best = None
    for zoom in [float(x) for x in a.zoom_grid.split(",")]:
        for tz in [float(x) for x in a.tz_grid.split(",")]:
            with torch.no_grad():
                l = (blur(render(torch.tensor(float(v["az"]), device=dev), torch.tensor(tz, device=dev), torch.tensor(zoom, device=dev), torch.zeros((), device=dev), torch.zeros((), device=dev)), a.blur) - tgt).abs().mean().item()
            if best is None or l < best[0]: best = (l, zoom, tz)
    l0, zoom, tz = best
    q = torch.tensor([0.0, math.log(zoom), tz, 0.0, 0.0], device=dev, requires_grad=True)   # daz(deg), log zoom, tz, du, dv
    opt = torch.optim.Adam([q], lr=0.02)
    for it in range(250):
        lr = 0.02 if it < 150 else 0.005
        for g in opt.param_groups: g["lr"] = lr
        r = render(q[0] * 0 + float(v["az"]), q[2], torch.exp(q[1]), q[3], q[4] * 0)
        loss = (blur(r, a.blur) - tgt).abs().mean(); opt.zero_grad(); loss.backward(); opt.step()
    r = dict(v); r["az"] = float(v["az"]); r["zoom"] = math.exp(q[1].item()); r["tz"] = q[2].item(); r["sx"], r["sy"] = q[3].item(), 0.0
    r["align_loss"] = [l0, loss.item()]; out.append(r)
    print(v["name"], "az", round(r["az"], 1), "zoom %.2f tz %.2f sx %.3f sy %.3f loss %.4f→%.4f" % (r["zoom"], r["tz"], q[3].item(), q[4].item(), l0, loss.item()), flush=True)
json.dump(out, open(a.out, "w"), indent=1)
