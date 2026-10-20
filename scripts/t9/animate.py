"""T9: 学習済みのメッシュ連動ガウシアン層を、メッシュ変形に追従させて描画する(アニメーションの確認)。
  python scripts/t9/animate.py --run experiments/T9/runs/X --master <T8 master> --mesh experiments/T9/mesh_60k.npz --poses rest,lean,arm_r,wave --out experiments/T9/runs/X/anim
各ポーズで、ガウシアン層(位置・向き・大きさが三角形に追従)と、層を使わずに位置だけ動かした場合(向き・大きさは基準姿勢のまま)を並べて保存する。
"""
import argparse
import json
import os
import sys

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deform  # noqa: E402
from meshgs import MeshGaussians, intrinsics, view_matrix  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True)
ap.add_argument("--master", required=True)
ap.add_argument("--mesh", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--poses", default="rest,lean,arm_r,wave")
ap.add_argument("--scale", type=float, default=0.5)
ap.add_argument("--views", default="ring:0,ring:3", help="描画する視点(種類:番号)。ring/upper/faceの中で名前順の番号")
ap.add_argument("--n", type=int, default=300000)
ap.add_argument("--ref", default=None, help="変形後の正解(render_pose_ref.py の出力フォルダ)。あれば PSNR を測り、並べて保存する")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
dev = "cuda"

meta = json.load(open(os.path.join(a.master, "views.json")))
S0, fx0 = meta["size"], meta["fx"]
S = int(round(S0 * a.scale))
K = intrinsics(fx0 * S / S0, S)
m = np.load(a.mesh)
args = json.load(open(os.path.join(a.run, "metrics.json")))["args"]
model = MeshGaussians(m["verts"], m["faces"], m["vcolor"], n_gaussians=args["n"], seed=args["seed"], device=dev)
model.load_state_dict(torch.load(os.path.join(a.run, "model.pt"), map_location=dev))
model.eval()

sel = []
for spec in a.views.split(","):
    t, i = spec.split(":")
    vs = sorted([v for v in meta["views"] if v["type"] == t and v["split"] == "test"], key=lambda v: v["name"])
    sel.append(vs[int(i) % len(vs)])
print("views", [v["name"] for v in sel])

V0 = m["verts"].astype(np.float64)
rows = []
metrics = []


def load_ref(pname, vname):
    from PIL import Image as _I
    im = np.asarray(_I.open(os.path.join(a.ref, f"{pname}_{vname}")).convert("RGBA")).astype(np.float32) / 255.0
    return torch.from_numpy(im[..., :3] * im[..., 3:4])


def roi_psnr(x, y, ref):
    import cv2
    fg = (ref.max(-1).values > 0.02).cpu().numpy().astype(np.uint8)
    roi = cv2.dilate(fg, np.ones((13, 13), np.uint8)) > 0
    mse = float(((x - y) ** 2).mean(-1).cpu().numpy()[roi].mean())
    return -10 * np.log10(max(mse, 1e-10))


with torch.no_grad():
    for pname in a.poses.split(","):
        Vp = torch.tensor(deform.pose(V0, pname), dtype=torch.float32, device=dev)
        # 比較用: 位置だけ動かす(各ガウシアンを基準姿勢の位置から、所属三角形の重心の移動量で平行移動。向き・大きさは基準姿勢のまま)
        means0, q0, s0, o0, c0 = model.gaussians()
        tri0 = model.V0[model.Fc].mean(1)[model.face]
        tri1 = Vp[model.Fc].mean(1)[model.face]
        from gsplat import rasterization
        cols = []
        for v in sel:
            vm = view_matrix(v["c2w_blender"]).to(dev)
            k_ = K.to(dev)
            img, _, _ = model.render(vm, K, S, V=Vp)
            out, _, _ = rasterization(means0 + (tri1 - tri0), q0, s0, o0, c0[:, None, :], vm[None], k_[None], S, S, sh_degree=0,
                                      backgrounds=torch.zeros(1, 3, device=dev), packed=False)
            tr = out[0].clamp(0, 1)
            if a.ref:
                rf = load_ref(pname, v["name"]).to(dev)
                metrics.append({"pose": pname, "view": v["name"], "psnr_layer": roi_psnr(img, rf, rf), "psnr_translate_only": roi_psnr(tr, rf, rf)})
                cols.append(torch.cat([rf, img, tr], 1))
            else:
                cols.append(torch.cat([img, tr], 1))
        row = torch.cat(cols, 1)
        rows.append(row)
        Image.fromarray((row.cpu().numpy() * 255).astype(np.uint8)).save(os.path.join(a.out, f"pose_{pname}.png"))
        model.export_ply(os.path.join(a.out, f"pose_{pname}.ply"), V=Vp)
sheet = torch.cat(rows, 0)
Image.fromarray((sheet.cpu().numpy() * 255).astype(np.uint8)).save(os.path.join(a.out, "poses_sheet.png"))
if metrics:
    json.dump(metrics, open(os.path.join(a.out, "pose_metrics.json"), "w"), indent=1)
    for mm in metrics:
        print("POSE", mm["pose"], mm["view"], "layer %.2f dB  translate-only %.2f dB" % (mm["psnr_layer"], mm["psnr_translate_only"]))
print("T9_ANIM_DONE", len(rows))
