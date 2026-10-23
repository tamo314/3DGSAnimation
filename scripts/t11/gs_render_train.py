"""T11: 学習済み3DGSを、学習データの各視点(補正後の姿勢)で描き直す(t9環境)。描き直し往復(生成AIで細部を描き直して再学習)の入力用。
  gs_wsl.sh gs_render_train.py --params P --data DATA --poses poses.json --out DIR [--only face_] [--sh 3] [--split train]"""
import argparse, json, math, os
import numpy as np, torch, torch.nn.functional as F
from PIL import Image
from gsplat import rasterization
ap = argparse.ArgumentParser()
ap.add_argument("--params", required=True); ap.add_argument("--data", required=True); ap.add_argument("--poses", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--only", default=""); ap.add_argument("--sh", type=int, default=3); ap.add_argument("--split", default="train"); ap.add_argument("--ss", type=int, default=1)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); dev = "cuda"
P = {k: v.to(dev) for k, v in torch.load(a.params).items()}
pose = json.load(open(a.poses))["train"]
j = json.load(open(os.path.join(a.data, f"transforms_{a.split}.json")))
im0 = Image.open(os.path.join(a.data, j["frames"][0]["file_path"] + ".png")); W, H = im0.size; fx = W / 2 / math.tan(j["camera_angle_x"] / 2)
CV = torch.diag(torch.tensor([1., -1., -1., 1.], device=dev))
def rotz(t): c, s = math.cos(t), math.sin(t); return torch.tensor([[c, -s, 0], [s, c, 0], [0, 0, 1]], device=dev, dtype=torch.float32)
def rotvec(v):
    v = torch.tensor(v, device=dev, dtype=torch.float32); th = v.norm().clamp_min(1e-8); k = v / th
    Kx = torch.tensor([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]], device=dev); return torch.eye(3, device=dev) + torch.sin(th) * Kx + (1 - torch.cos(th)) * Kx @ Kx
K = torch.tensor([[[fx * a.ss, 0, W * a.ss / 2], [0, fx * a.ss, H * a.ss / 2], [0, 0, 1]]], device=dev, dtype=torch.float32)
for f in j["frames"]:
    name = os.path.basename(f["file_path"])
    if a.only and a.only not in name: continue
    c2w = torch.tensor(f["transform_matrix"], device=dev, dtype=torch.float32); p = pose.get(name)
    if p:
        Rz = torch.eye(4, device=dev); Rz[:3, :3] = rotz(math.radians(p["d_az_deg"])); dl = torch.eye(4, device=dev); dl[:3, :3] = rotvec(p["rot"]); dl[:3, 3] = torch.tensor(p["trans"], device=dev)
        c2w = Rz @ c2w @ dl
    vm = torch.linalg.inv(c2w @ CV)[None]; Kf = K.clone(); Kf[:, 0, 0] *= f.get("focal_mult", 1.0); Kf[:, 1, 1] *= f.get("focal_mult", 1.0)
    with torch.no_grad():
        img, _, _ = rasterization(P["means"], F.normalize(P["quats"], dim=-1), torch.exp(P["scales"]), torch.sigmoid(P["opacities"]), torch.cat([P["sh0"], P["shN"]], 1), vm, Kf, W * a.ss, H * a.ss, sh_degree=a.sh, backgrounds=torch.ones(1, 3, device=dev), packed=False)
    im = img[0].clamp(0, 1).permute(2, 0, 1)[None]
    if a.ss > 1: im = F.interpolate(im, size=(H, W), mode="area")
    Image.fromarray((im[0].permute(1, 2, 0).cpu().numpy() * 255 + .5).astype(np.uint8)).save(os.path.join(a.out, name + ".png"))
print("done")
