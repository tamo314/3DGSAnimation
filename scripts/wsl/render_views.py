"""T8: 3DGS(PLY)を、マスターのカメラで指定倍率に描いて PNG(黒背景RGB)で保存する。gstyle 環境で実行。
  PYTHONPATH=~/ext/g-style ~/venvs/gstyle/bin/python render_views.py --ply P --master M --types face --split test --scales 1,2 --out DIR --sh 3
出力: DIR/s<倍率>/<視点名>.png (倍率1=マスター解像度)。出力側の超解像の評価用。"""
import argparse, json, math, os
from types import SimpleNamespace
import numpy as np, torch
from PIL import Image
from gaussian_renderer import render
from scene.cameras import Camera
from scene.gaussian_model import GaussianModel
ap = argparse.ArgumentParser()
ap.add_argument("--ply", required=True); ap.add_argument("--master", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--types", default="face"); ap.add_argument("--split", default="test"); ap.add_argument("--scales", default="1,2"); ap.add_argument("--sh", type=int, default=3)
a = ap.parse_args()
meta = json.load(open(os.path.join(a.master, "views.json"))); S0 = meta["size"]
fov = 2 * math.atan(S0 / (2 * meta["fx"]))
g = GaussianModel(a.sh); g.load_ply(a.ply)
if a.sh > 0:
    from plyfile import PlyData
    el = PlyData.read(a.ply).elements[0]
    names = sorted([p.name for p in el.properties if p.name.startswith("f_rest_")], key=lambda x: int(x.split("_")[-1]))
    fr = np.stack([np.asarray(el[n]) for n in names], axis=1).reshape(len(el.data), 3, (a.sh + 1) ** 2 - 1)
    g._features_rest = torch.nn.Parameter(torch.tensor(fr, dtype=torch.float, device="cuda").transpose(1, 2).contiguous())
pipe = SimpleNamespace(convert_SHs_python=False, compute_cov3D_python=False, debug=False)
bg = torch.zeros(3, device="cuda")
views = [v for v in meta["views"] if v["type"] in a.types.split(",") and (a.split == "all" or v["split"] == a.split)]
for sc in [float(x) for x in a.scales.split(",")]:
    S = int(round(S0 * sc)); od = os.path.join(a.out, f"s{sc:g}"); os.makedirs(od, exist_ok=True)
    for v in views:
        c2w = np.array(v["c2w_blender"]); R = c2w[:3, :3] @ np.diag([1.0, -1.0, -1.0]); T = -R.T @ c2w[:3, 3]
        cam = Camera(colmap_id=v["k"], R=R, T=T, FoVx=fov, FoVy=fov, image=torch.zeros(3, S, S), gt_alpha_mask=None, image_name=v["name"], uid=v["k"], data_device="cuda")
        with torch.no_grad():
            im = render(cam, g, pipe, bg)["render"].clamp(0, 1).permute(1, 2, 0).cpu().numpy()
        Image.fromarray((im * 255 + 0.5).astype(np.uint8)).save(os.path.join(od, v["name"]))
    print("rendered", len(views), "scale", sc)
