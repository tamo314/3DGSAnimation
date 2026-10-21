"""T11: 学習済み3DGS(PLY)を、build_dataset.py と同じカメラ規約で任意の視点・倍率で描く(gstyle環境で実行、公式の描画コードを利用)。
  PYTHONPATH=~/ext/g-style:~/work/t11/shim ~/venvs/gstyle/bin/python render_ply.py --ply P --out DIR --views "az,el,name;..." [--zoom 1] [--target 0,0,0] [--W 1024 --H 1280] [--sh 3]
--zoom はキャラ全身を画面に収める基準(1)からの拡大率、--target は注視点(ワールド、キャラ高さ=2、足裏z=-1。顔の中心はおよそ z=0.8)。背景は白。"""
import argparse, math, os
from types import SimpleNamespace
import numpy as np, torch
from PIL import Image
from gaussian_renderer import render
from scene.cameras import Camera
from scene.gaussian_model import GaussianModel
ap = argparse.ArgumentParser()
ap.add_argument("--ply", required=True); ap.add_argument("--out", required=True); ap.add_argument("--views", required=True)
ap.add_argument("--zoom", type=float, default=1.0); ap.add_argument("--target", default="0,0,0")
ap.add_argument("--W", type=int, default=1024); ap.add_argument("--H", type=int, default=1280)
ap.add_argument("--fig", type=float, default=0.875); ap.add_argument("--sh", type=int, default=3)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
D = 8.0; fx = a.H * a.fig * D / 2.0 * a.zoom
fovx = 2 * math.atan(a.W / 2 / fx); fovy = 2 * math.atan(a.H / 2 / fx)
tgt = np.array([float(x) for x in a.target.split(",")])
g = GaussianModel(a.sh); g.load_ply(a.ply)
pipe = SimpleNamespace(convert_SHs_python=False, compute_cov3D_python=False, debug=False)
bg = torch.ones(3, device="cuda")
for spec in a.views.split(";"):
    az, el, name = spec.split(","); azr, elr = math.radians(float(az)), math.radians(float(el))
    pos = tgt + D * np.array([math.sin(azr) * math.cos(elr), -math.cos(azr) * math.cos(elr), math.sin(elr)])
    fwd = tgt - pos; fwd /= np.linalg.norm(fwd); right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    c2w = np.eye(4); c2w[:3, 0] = right; c2w[:3, 1] = up; c2w[:3, 2] = -fwd; c2w[:3, 3] = pos
    R = c2w[:3, :3] @ np.diag([1.0, -1.0, -1.0]); T = -R.T @ c2w[:3, 3]
    cam = Camera(colmap_id=0, R=R, T=T, FoVx=fovx, FoVy=fovy, image=torch.zeros(3, a.H, a.W), gt_alpha_mask=None, image_name=name, uid=0, data_device="cuda")
    with torch.no_grad():
        im = render(cam, g, pipe, bg)["render"].clamp(0, 1).permute(1, 2, 0).cpu().numpy()
    Image.fromarray((im * 255 + .5).astype(np.uint8)).save(os.path.join(a.out, name + ".png"))
print("done")
