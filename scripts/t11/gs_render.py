"""T11: gs_train.py の params.pt を、build_dataset.py と同じカメラ規約で任意の方位・倍率で描く(t9環境)。
  gs_wsl.sh gs_render.py --params P --out DIR --views "az,el,name;..." [--zoom 1 --target 0,0,0 --W 1024 --H 1280 --sh 3]
--target はワールド座標(キャラ高さ=2、足裏z=-1。顔の中心はおよそ z=0.8)。zoom=1で全身が画面高さの87.5%。背景は白。"""
import argparse, math, os
import numpy as np, torch, torch.nn.functional as F
from PIL import Image
from gsplat import rasterization
ap = argparse.ArgumentParser()
ap.add_argument("--params", required=True); ap.add_argument("--out", required=True); ap.add_argument("--views", required=True)
ap.add_argument("--zoom", type=float, default=1.0); ap.add_argument("--target", default="0,0,0")
ap.add_argument("--W", type=int, default=1024); ap.add_argument("--H", type=int, default=1280); ap.add_argument("--fig", type=float, default=0.875)
ap.add_argument("--sh", type=int, default=3); ap.add_argument("--ss", type=int, default=1, help="超サンプリング倍率(縮小して出力)")
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); dev = "cuda"
P = {k: v.to(dev) for k, v in torch.load(a.params).items()}
D = 8.0; Wr, Hr = a.W * a.ss, a.H * a.ss; fx = a.H * a.fig * D / 2.0 * a.ss; Dist = D / a.zoom   # 倍率はカメラ距離で表す(gs_train.pyの顔アップと同じ)
K = torch.tensor([[fx, 0, Wr / 2], [0, fx, Hr / 2], [0, 0, 1]], dtype=torch.float32, device=dev)
tgt = np.array([float(x) for x in a.target.split(",")])
CV = np.diag([1., -1., -1., 1.])
for spec in a.views.split(";"):
    az, el, name = spec.split(","); azr, elr = math.radians(float(az)), math.radians(float(el))
    pos = tgt + Dist * np.array([math.sin(azr) * math.cos(elr), -math.cos(azr) * math.cos(elr), math.sin(elr)])
    fwd = tgt - pos; fwd /= np.linalg.norm(fwd); right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    c2w = np.eye(4); c2w[:3, 0] = right; c2w[:3, 1] = up; c2w[:3, 2] = -fwd; c2w[:3, 3] = pos
    vm = torch.from_numpy(np.linalg.inv(c2w @ CV)).float().to(dev)[None]
    with torch.no_grad():
        img, al, _ = rasterization(P["means"], F.normalize(P["quats"], dim=-1), torch.exp(P["scales"]), torch.sigmoid(P["opacities"]), torch.cat([P["sh0"], P["shN"]], 1),
                                   vm, K[None], Wr, Hr, sh_degree=a.sh, backgrounds=torch.ones(1, 3, device=dev), packed=False)
    im = img[0].clamp(0, 1).permute(2, 0, 1)[None]
    if a.ss > 1: im = F.interpolate(im, size=(a.H, a.W), mode="area")
    Image.fromarray((im[0].permute(1, 2, 0).cpu().numpy() * 255 + .5).astype(np.uint8)).save(os.path.join(a.out, name + ".png"))
print("done")
