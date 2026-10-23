"""T11: 生成多視点画像から3DGSを学習する(自前実装、gsplatのラスタライザを使用)。公式の3DGS学習コードとの違い:
  * 視点ごとのカメラ姿勢の補正(方位・カメラ座標系の回転/平行移動)を一緒に最適化する。生成画像の方位は名目値で、実際はずれているため。
  * 初期点は、シルエット(アルファ)から作るビジュアルハル。
  * アルファ(シルエット)の損失を足し、背景に浮く点を抑える。
  python gs_train.py --data DATA(build_dataset.pyの出力) --out OUT --iters 15000 [--pose_lr 1e-3] [--no_pose]
出力: OUT/point_cloud.ply(標準3DGS形式)、OUT/poses.json(補正後の方位など)、OUT/metrics.json、OUT/render_*.png
"""
import argparse, json, math, os, time
import numpy as np, torch, torch.nn.functional as F
from PIL import Image
from gsplat import rasterization
from gsplat.strategy import DefaultStrategy

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--iters", type=int, default=15000); ap.add_argument("--sh", type=int, default=3)
ap.add_argument("--pose_lr", type=float, default=1e-3); ap.add_argument("--no_pose", action="store_true")
ap.add_argument("--pose_prefix", default="", help="指定すると、名前がこの接頭辞で始まる視点だけ姿勢(方位・平行移動=倍率とずれ)を学習する(例 z_=部位アップ)")
ap.add_argument("--pose_start", type=int, default=500)
ap.add_argument("--lam_ssim", type=float, default=0.2); ap.add_argument("--lam_alpha", type=float, default=0.1)
ap.add_argument("--init_pts", type=int, default=60000); ap.add_argument("--hull_dilate", type=int, default=30)
ap.add_argument("--warp", action="store_true", help="視点ごとの画像ずらし(低解像の変位場)を学習。生成画像どうしの細部のずれを吸収して、平均化によるぼけを減らす")
ap.add_argument("--affine", default="", help="名前がこの接頭辞(カンマ区切り)で始まる視点について、画像の拡大率とずれ(2D)を視点ごとに学習する。弱透視の寄り画像の倍率・位置合わせ用")
ap.add_argument("--warp_grid", type=int, default=16); ap.add_argument("--warp_px", type=float, default=12.0, help="変位の上限(px)"); ap.add_argument("--warp_lr", type=float, default=2e-3)
ap.add_argument("--warp_reg", type=float, default=0.002, help="変位の大きさ・粗さへの罰則の重み"); ap.add_argument("--warp_start", type=int, default=1500)
ap.add_argument("--grow_grad2d", type=float, default=0.0002); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--eval_pose_iters", type=int, default=300)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True); dev = "cuda"; torch.manual_seed(a.seed); np.random.seed(a.seed)
D = 8.0

def load_split(sp):
    p = os.path.join(a.data, f"transforms_{sp}.json"); j = json.load(open(p)); fr = j["frames"]
    imgs, c2w, names, zooms, fms = [], [], [], [], []
    for f in fr:
        im = np.asarray(Image.open(os.path.join(a.data, f["file_path"] + ".png")).convert("RGBA")).astype(np.float32) / 255
        imgs.append(im); c2w.append(np.array(f["transform_matrix"], np.float32)); names.append(os.path.basename(f["file_path"])); fms.append(f.get("focal_mult", 1.0)); zooms.append(0.0 if f.get("closeup") else 1.0)
    return j["camera_angle_x"], imgs, c2w, names, zooms, fms
fovx, tr_img, tr_c2w, tr_names, tr_zoom, tr_fm = load_split("train"); _, te_img, te_c2w, te_names, te_zoom, te_fm = load_split("test")
H, W = tr_img[0].shape[:2]; fx = W / 2 / math.tan(fovx / 2)
def Kmat(zoom, p=None):
    """視点ごとの内部パラメータ。zoom: (n,)名目倍率。p: 補正(n,10)の 7=log倍率, 8,9=画像中心のずれ(幅/高さ比)。"""
    n = len(zoom); f = fx * torch.as_tensor(zoom, device=dev, dtype=torch.float32).reshape(n);   # zoom=焦点距離の倍率(frame の focal_mult。--tele で作ったデータ以外は1)。倍率の学習はKに勾配が来ないので使わない
    cx = torch.full((n,), W / 2, device=dev); cy = torch.full((n,), H / 2, device=dev)
    if p is not None: f = f * torch.exp(p[:, 7]); cx = cx + p[:, 8] * W; cy = cy + p[:, 9] * H
    Km = torch.zeros(n, 3, 3, device=dev); Km[:, 0, 0] = f; Km[:, 1, 1] = f; Km[:, 0, 2] = cx; Km[:, 1, 2] = cy; Km[:, 2, 2] = 1
    return Km
K = Kmat([1.0])[0]
def to_t(imgs):
    x = torch.from_numpy(np.stack(imgs)).to(dev)
    rgb, al = x[..., :3], x[..., 3:]
    return rgb * al + (1 - al), al[..., 0]                       # 白背景に合成したRGB, アルファ
tr_rgb, tr_al = to_t(tr_img)
te_rgb, te_al = to_t(te_img) if te_img else (None, None)
N = len(tr_img); print("train", N, "test", len(te_img), "size", W, H)

def rotz(t):
    c, s = torch.cos(t), torch.sin(t); z, o = torch.zeros_like(t), torch.ones_like(t)
    return torch.stack([torch.stack([c, -s, z], -1), torch.stack([s, c, z], -1), torch.stack([z, z, o], -1)], -2)
def rotvec(v):                                                    # 小回転(ロドリゲス)
    th = v.norm(dim=-1, keepdim=True).clamp_min(1e-8); k = v / th
    Kx = torch.zeros(*v.shape[:-1], 3, 3, device=v.device)
    Kx[..., 0, 1], Kx[..., 0, 2], Kx[..., 1, 0], Kx[..., 1, 2], Kx[..., 2, 0], Kx[..., 2, 1] = -k[..., 2], k[..., 1], k[..., 2], -k[..., 0], -k[..., 1], k[..., 0]
    I = torch.eye(3, device=v.device); th = th[..., None]
    return I + torch.sin(th) * Kx + (1 - torch.cos(th)) * (Kx @ Kx)
CV = torch.diag(torch.tensor([1., -1., -1., 1.], device=dev))     # OpenGL(Blender)→OpenCVのカメラ軸
def viewmat(c2w_gl, p=None):
    """c2w_gl: (N,4,4)。p: 補正 (N,7) = [δ方位, 回転(3), 平行移動(3)]。w2c(OpenCV)を返す。"""
    c2w = c2w_gl.clone()
    if p is not None:
        Rz = torch.eye(4, device=dev).repeat(len(c2w), 1, 1); Rz[:, :3, :3] = rotz(p[:, 0])           # ワールドの鉛直軸まわりに、中心を保って回す
        dl = torch.eye(4, device=dev).repeat(len(c2w), 1, 1); dl[:, :3, :3] = rotvec(p[:, 1:4]); dl[:, :3, 3] = p[:, 4:7]
        c2w = Rz @ c2w @ dl
    return torch.linalg.inv(c2w @ CV)
c2w0 = torch.from_numpy(np.stack(tr_c2w)).to(dev)
pose = torch.zeros(N, 10, device=dev, requires_grad=not a.no_pose)
zoom_tr = torch.tensor(tr_fm, device=dev)
full_idx = [i for i in range(N) if tr_zoom[i] == 1.0]   # tr_zoom: 1=全身, 0=顔アップ(ハルの初期化に使わない)

# --- ビジュアルハルで初期点 ---
def init_points():
    import cv2
    vm = viewmat(c2w0)
    m = (tr_al > 0.5).cpu().numpy().astype(np.uint8)
    dil = [torch.from_numpy(cv2.dilate(x, np.ones((a.hull_dilate * 2 + 1,) * 2, np.uint8))).to(dev) for x in m]
    pts = torch.rand(2_000_000, 3, device=dev) * torch.tensor([1.6, 1.6, 2.2], device=dev) + torch.tensor([-0.8, -0.8, -1.1], device=dev)
    keep = torch.zeros(len(pts), device=dev); col = torch.zeros(len(pts), 3, device=dev)
    for i in full_idx:
        pc = (vm[i, :3, :3] @ pts.T).T + vm[i, :3, 3]; uv = (K @ pc.T).T; u = uv[:, 0] / uv[:, 2]; v = uv[:, 1] / uv[:, 2]
        ok = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
        ui, vi = u.long().clamp(0, W - 1), v.long().clamp(0, H - 1)
        keep += (ok & (dil[i][vi, ui] > 0)).float()
        col += tr_rgb[i][vi, ui] * ok[:, None]
    sel = keep >= len(full_idx) - 1
    pts, col = pts[sel], (col[sel] / len(full_idx))
    idx = torch.randperm(len(pts), device=dev)[:a.init_pts]
    print("hull points", int(sel.sum()), "→", len(idx))
    return pts[idx], col[idx].clamp(0.02, 0.98)
means0, col0 = init_points()
n0 = len(means0)
from scipy.spatial import cKDTree
d, _ = cKDTree(means0.cpu().numpy()).query(means0.cpu().numpy(), k=4); avg = torch.from_numpy(d[:, 1:].mean(1)).float().to(dev).clamp_min(1e-4)
SH0 = 0.28209479177387814
params = torch.nn.ParameterDict({
    "means": torch.nn.Parameter(means0), "scales": torch.nn.Parameter(torch.log(avg)[:, None].repeat(1, 3)),
    "quats": torch.nn.Parameter(F.normalize(torch.randn(n0, 4, device=dev), dim=-1)),
    "opacities": torch.nn.Parameter(torch.logit(torch.full((n0,), 0.3, device=dev))),
    "sh0": torch.nn.Parameter(((col0 - 0.5) / SH0)[:, None, :]),
    "shN": torch.nn.Parameter(torch.zeros(n0, (a.sh + 1) ** 2 - 1, 3, device=dev))}).to(dev)
scene_scale = 1.0
lrs = {"means": 1.6e-4 * scene_scale, "scales": 5e-3, "quats": 1e-3, "opacities": 5e-2, "sh0": 2.5e-3, "shN": 2.5e-3 / 20}
opts = {k: torch.optim.Adam([{"params": params[k], "lr": lrs[k]}], eps=1e-15) for k in params}
strat = DefaultStrategy(verbose=False, refine_stop_iter=min(a.iters - 1000, 15000), reset_every=3000, grow_grad2d=a.grow_grad2d); state = strat.initialize_state(scene_scale=scene_scale)
pose_opt = torch.optim.Adam([pose], lr=a.pose_lr) if not a.no_pose else None
gw_, gh_ = a.warp_grid, int(round(a.warp_grid * H / W))
flow = torch.zeros(N, 2, gh_, gw_, device=dev, requires_grad=a.warp)                    # 視点ごとの変位場(tanhで±warp_pxに制限)
aff = torch.zeros(N, 3, device=dev, requires_grad=bool(a.affine))                      # 視点ごと: log拡大率, 右ずれ, 下ずれ(正規化座標)
aff_mask = torch.tensor([1.0 if (a.affine and any(n.startswith(q) for q in a.affine.split(","))) else 0.0 for n in tr_names], device=dev)
_groups = ([{"params": [flow], "lr": a.warp_lr}] if a.warp else []) + ([{"params": [aff], "lr": a.warp_lr * 0.5}] if a.affine else [])
warp_opt = torch.optim.Adam(_groups) if _groups else None
_base = F.affine_grid(torch.eye(2, 3, device=dev)[None], (1, 3, H, W), align_corners=False)
def warp_img(x, i):                                                                      # x: (1,H,W,C)。描画を視点iの変位場でずらす
    d = torch.tanh(flow[i:i + 1]) * a.warp_px; d = F.interpolate(d, size=(H, W), mode="bicubic", align_corners=False).permute(0, 2, 3, 1)
    q = aff[i] * aff_mask[i]; g = _base * torch.exp(q[0]) + q[1:3] + d * torch.tensor([2 / W, 2 / H], device=dev)
    return F.grid_sample(x.permute(0, 3, 1, 2), g, mode="bilinear", padding_mode="border", align_corners=False).permute(0, 2, 3, 1)
def flow_reg(i):
    f = torch.tanh(flow[i:i + 1]) * a.warp_px
    return f.abs().mean() + 4 * ((f[..., 1:, :] - f[..., :-1, :]).abs().mean() + (f[..., 1:] - f[..., :-1]).abs().mean())
pose_mask = torch.tensor([1.0 if n.startswith(a.pose_prefix) else 0.0 for n in tr_names], device=dev)   # 姿勢を学習する視点(接頭辞なしなら全部)
plr_mult = torch.tensor([1, 1, 1, 1, 3, 3, 3, 0, 0, 0], device=dev)   # gsplatはKへの勾配を返さないので倍率・中心ずれは使わず、カメラ平行移動で表す
sched_m = lambda it: 0.01 ** min(it / a.iters, 1.0)

def render(vm, Ks, w, h, sh_deg, bg=1.0):
    img, al, info = rasterization(params["means"], F.normalize(params["quats"], dim=-1), torch.exp(params["scales"]), torch.sigmoid(params["opacities"]),
                                  torch.cat([params["sh0"], params["shN"]], 1), vm, Ks, w, h, sh_degree=sh_deg,
                                  backgrounds=torch.full((len(vm), 3), bg, device=dev), packed=False)
    return img, al[..., 0], info

def ssim(x, y, ws=11):
    g = torch.exp(-(torch.arange(ws, device=dev) - ws // 2) ** 2 / (2 * 1.5 ** 2)); g = (g / g.sum()); w2 = (g[:, None] * g[None]).expand(3, 1, ws, ws)
    x, y = x.permute(0, 3, 1, 2), y.permute(0, 3, 1, 2)
    mu1, mu2 = F.conv2d(x, w2, padding=ws // 2, groups=3), F.conv2d(y, w2, padding=ws // 2, groups=3)
    s11, s22, s12 = F.conv2d(x * x, w2, padding=ws // 2, groups=3) - mu1 ** 2, F.conv2d(y * y, w2, padding=ws // 2, groups=3) - mu2 ** 2, F.conv2d(x * y, w2, padding=ws // 2, groups=3) - mu1 * mu2
    return (((2 * mu1 * mu2 + 0.01 ** 2) * (2 * s12 + 0.03 ** 2)) / ((mu1 ** 2 + mu2 ** 2 + 0.01 ** 2) * (s11 + s22 + 0.03 ** 2))).mean()

t0 = time.time(); order = []
for it in range(1, a.iters + 1):
    if not order: order = list(np.random.permutation(N))
    i = order.pop()
    for g in opts["means"].param_groups: g["lr"] = lrs["means"] * sched_m(it)
    p = pose[i:i + 1] * pose_mask[i] if (pose_opt is not None and it > a.pose_start) else None
    vm = viewmat(c2w0[i:i + 1], p)
    sh_deg = min(it // 1000, a.sh)
    img, al, info = render(vm, Kmat(zoom_tr[i:i + 1], p), W, H, sh_deg)
    strat.step_pre_backward(params, opts, state, it, info)
    use_w = warp_opt is not None and it > a.warp_start
    img_l = warp_img(img, i) if use_w else img                                          # 損失用(勾配のための densification 統計は未ワープのinfoから)
    l1 = (img_l - tr_rgb[i:i + 1]).abs().mean()
    loss = (1 - a.lam_ssim) * l1 + a.lam_ssim * (1 - ssim(img_l, tr_rgb[i:i + 1])) + a.lam_alpha * (al - tr_al[i:i + 1]).abs().mean()
    if use_w and a.warp: loss = loss + a.warp_reg * flow_reg(i)
    loss.backward()
    if use_w: warp_opt.step(); warp_opt.zero_grad(set_to_none=True)
    strat.step_post_backward(params, opts, state, it, info, packed=False)
    for o in opts.values(): o.step(); o.zero_grad(set_to_none=True)
    if pose_opt is not None and it > a.pose_start:
        for g in pose_opt.param_groups: g["lr"] = a.pose_lr * (0.1 ** (it / a.iters))
        pose.grad.mul_(plr_mult); pose_opt.step(); pose_opt.zero_grad(set_to_none=True)
    if it % 1000 == 0 or it == 1:
        print(f"it {it} loss {loss.item():.4f} l1 {l1.item():.4f} n {len(params['means'])} {time.time() - t0:.0f}s", flush=True)

# --- 保存 ---
@torch.no_grad()
def save_ply(path):
    from plyfile import PlyData, PlyElement
    n = len(params["means"]); f_dc = params["sh0"].reshape(n, 3).cpu().numpy(); f_rest = params["shN"].transpose(1, 2).reshape(n, -1).cpu().numpy()
    attrs = ["x", "y", "z", "nx", "ny", "nz"] + [f"f_dc_{i}" for i in range(3)] + [f"f_rest_{i}" for i in range(f_rest.shape[1])] + ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    data = np.concatenate([params["means"].cpu().numpy(), np.zeros((n, 3)), f_dc, f_rest, params["opacities"][:, None].cpu().numpy(), params["scales"].cpu().numpy(), F.normalize(params["quats"], dim=-1).cpu().numpy()], 1).astype(np.float32)
    el = np.empty(n, dtype=[(k, "f4") for k in attrs]);
    for k, c in zip(attrs, data.T): el[k] = c
    PlyData([PlyElement.describe(el, "vertex")]).write(path)
save_ply(os.path.join(a.out, "point_cloud.ply"))
torch.save({k: v.detach().cpu() for k, v in params.items()}, os.path.join(a.out, "params.pt"))
pose = pose * pose_mask[:, None]
c2w_ref = viewmat(c2w0, pose.detach() if pose_opt is not None else None)
poses = {tr_names[k]: {"d_az_deg": float(math.degrees(pose[k, 0].item())), "rot": pose[k, 1:4].tolist(), "trans": pose[k, 4:7].tolist(), "zoom_mult": float(math.exp(pose[k, 7].item())), "shift": pose[k, 8:10].tolist()} for k in range(N)}
affs = {tr_names[k]: {"scale": float(math.exp(aff[k, 0].item() * aff_mask[k].item())), "shift": [aff[k, 1].item() * aff_mask[k].item(), aff[k, 2].item() * aff_mask[k].item()]} for k in range(N) if aff_mask[k] > 0}
json.dump({"train": poses, "affine": affs}, open(os.path.join(a.out, "poses.json"), "w"), indent=1)

@torch.no_grad()
def psnr(x, y): return float(-10 * torch.log10(((x - y) ** 2).mean()))
metrics = {"n_gauss": len(params["means"]), "iters": a.iters, "train_sec": time.time() - t0}
with torch.no_grad():
    tp = []
    for i in range(N):
        pi = pose[i:i + 1] if pose_opt is not None else None
        img, _, _ = render(viewmat(c2w0[i:i + 1], pi), Kmat(zoom_tr[i:i + 1], pi), W, H, a.sh)
        tp.append(psnr(img, tr_rgb[i:i + 1]))
    metrics["train_psnr"] = float(np.mean(tp))
# 保留視点: 姿勢だけを最適化してから評価
if te_rgb is not None:
    c2wt = torch.from_numpy(np.stack(te_c2w)).to(dev); ptest = torch.zeros(len(te_img), 10, device=dev, requires_grad=True); zoom_te = torch.tensor(te_fm, device=dev)
    po = torch.optim.Adam([ptest], lr=3e-3)
    for _ in range(a.eval_pose_iters):
        loss = sum((render(viewmat(c2wt[k:k + 1], ptest[k:k + 1]), Kmat(zoom_te[k:k + 1], ptest[k:k + 1]), W, H, a.sh)[0] - te_rgb[k:k + 1]).abs().mean() for k in range(len(te_img)))
        po.zero_grad(); loss.backward(); po.step()
    metrics["test"] = {}
    with torch.no_grad():
        for k, nm in enumerate(te_names):
            img, _, _ = render(viewmat(c2wt[k:k + 1], ptest[k:k + 1]), Kmat(zoom_te[k:k + 1], ptest[k:k + 1]), W, H, a.sh)
            metrics["test"][nm] = {"psnr": psnr(img, te_rgb[k:k + 1]), "ssim": float(ssim(img, te_rgb[k:k + 1])), "est_d_az_deg": float(math.degrees(ptest[k, 0].item())), "est_zoom_mult": float(math.exp(ptest[k, 7].item()))}
            both = torch.cat([te_rgb[k], img[0]], 1).cpu().numpy(); Image.fromarray((both * 255 + .5).astype(np.uint8)).save(os.path.join(a.out, f"test_{nm}.png"))
json.dump(metrics, open(os.path.join(a.out, "metrics.json"), "w"), indent=1); print(json.dumps(metrics, indent=1))
