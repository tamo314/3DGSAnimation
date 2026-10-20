"""T9: メッシュの三角形に結びつけたガウシアン層(自前実装)。
各ガウシアンは「どの三角形に属すか(face)」「三角形内の重心座標(bary)」「法線方向のずれ(h)」「三角形の局所座標での回転・大きさ」を持つ。
メッシュ頂点が動くと、位置・向き・大きさが三角形に追従する(アニメーション用)。描画は gsplat(Apache-2.0)、学習ループ・モデルは自前。
参考にした考え方: Gaussian Frosting(メッシュに結びついたガウシアン層)。コードは参照していない。
"""
import json
import math
import os

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

C0 = 0.28209479177387814


# ---- 回転 ---------------------------------------------------------------------------------
def quat_mul(a, b):
    aw, ax, ay, az = a.unbind(-1)
    bw, bx, by, bz = b.unbind(-1)
    return torch.stack([aw * bw - ax * bx - ay * by - az * bz,
                        aw * bx + ax * bw + ay * bz - az * by,
                        aw * by - ax * bz + ay * bw + az * bx,
                        aw * bz + ax * by - ay * bx + az * bw], -1)


def mat_to_quat(R):
    """(N,3,3) -> (N,4) wxyz。最大成分の分岐で数値安定にする。"""
    m00, m01, m02 = R[:, 0, 0], R[:, 0, 1], R[:, 0, 2]
    m10, m11, m12 = R[:, 1, 0], R[:, 1, 1], R[:, 1, 2]
    m20, m21, m22 = R[:, 2, 0], R[:, 2, 1], R[:, 2, 2]
    q_abs = torch.sqrt(torch.clamp(torch.stack([1 + m00 + m11 + m22, 1 + m00 - m11 - m22, 1 - m00 + m11 - m22, 1 - m00 - m11 + m22], -1), min=0)) / 2
    cands = torch.stack([
        torch.stack([q_abs[:, 0] ** 2, m21 - m12, m02 - m20, m10 - m01], -1),
        torch.stack([m21 - m12, q_abs[:, 1] ** 2, m10 + m01, m02 + m20], -1),
        torch.stack([m02 - m20, m10 + m01, q_abs[:, 2] ** 2, m12 + m21], -1),
        torch.stack([m10 - m01, m20 + m02, m21 + m12, q_abs[:, 3] ** 2], -1)], 1)
    cands = cands / (2 * q_abs.clamp(min=0.1)[..., None])
    idx = q_abs.argmax(-1)
    q = cands[torch.arange(len(R)), idx]
    q = F.normalize(q, dim=-1)
    return torch.where(q[:, :1] < 0, -q, q)


# ---- カメラ(T8の views.json。Blenderのc2w → COLMAP規約のビュー行列) ---------------------------
def view_matrix(c2w_blender):
    c2w = np.array(c2w_blender, dtype=np.float64)
    Rc = c2w[:3, :3] @ np.diag([1.0, -1.0, -1.0])
    C = c2w[:3, 3]
    w2c = np.eye(4)
    w2c[:3, :3] = Rc.T
    w2c[:3, 3] = -Rc.T @ C
    return torch.tensor(w2c, dtype=torch.float32)


def intrinsics(fx, size):
    return torch.tensor([[fx, 0, size / 2], [0, fx, size / 2], [0, 0, 1]], dtype=torch.float32)


# ---- 画像の指標 -----------------------------------------------------------------------------
def ssim_loss_map(x, y, win=11, sigma=1.5):
    """x,y: (1,3,H,W)。SSIMの平均マップ(1に近いほど似ている)。"""
    c = torch.arange(win, dtype=torch.float32, device=x.device) - win // 2
    k = torch.exp(-(c ** 2) / (2 * sigma ** 2))
    k = k / k.sum()
    k2 = (k[:, None] * k[None, :])[None, None].repeat(3, 1, 1, 1)
    f = lambda t: F.conv2d(t, k2, padding=win // 2, groups=3)
    mx, my = f(x), f(y)
    sxx, syy, sxy = f(x * x) - mx ** 2, f(y * y) - my ** 2, f(x * y) - mx * my
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    return ((2 * mx * my + C1) * (2 * sxy + C2)) / ((mx ** 2 + my ** 2 + C1) * (sxx + syy + C2))


# ---- モデル ---------------------------------------------------------------------------------
class MeshGaussians(nn.Module):
    """メッシュ(頂点V・三角形Fc)に結びつけたガウシアン層。"""

    def __init__(self, V, Fc, vcolor, n_gaussians=300000, seed=0, device="cuda"):
        super().__init__()
        g = torch.Generator().manual_seed(seed)
        self.device = device
        V = torch.as_tensor(V, dtype=torch.float32)
        Fc = torch.as_tensor(Fc, dtype=torch.long)
        self.register_buffer("V0", V.to(device))            # 基準姿勢の頂点
        self.register_buffer("Fc", Fc.to(device))
        area = self._areas(self.V0)
        self.register_buffer("area0", area)
        # 面積に比例して各三角形のガウシアン数を決める(最低1個)
        a_target = float(area.sum()) / n_gaussians
        counts = torch.clamp(torch.round(area.cpu() / a_target).long(), min=1)
        face = torch.repeat_interleave(torch.arange(len(Fc)), counts)
        G = len(face)
        r1, r2 = torch.rand(G, generator=g), torch.rand(G, generator=g)
        s = torch.sqrt(r1)
        bary = torch.stack([1 - s, s * (1 - r2), s * r2], -1)
        self.register_buffer("face", face.to(device))
        self.register_buffer("bary", bary.to(device))
        self.n = G
        spacing = math.sqrt(float(area.sum()) / G)
        self.spacing = spacing
        sf = torch.sqrt(area.cpu())[face]                    # 三角形の大きさ(スケールの基準)
        init_s = torch.stack([torch.full((G,), 0.8 * spacing), torch.full((G,), 0.8 * spacing), torch.full((G,), 0.25 * spacing)], -1)
        self.h = nn.Parameter(torch.zeros(G, device=device))                        # 法線方向のずれ(m)
        self.log_s = nn.Parameter(torch.log(init_s / sf[:, None]).to(device))       # 三角形の大きさに対する対数スケール
        self.q_local = nn.Parameter(torch.tensor([1.0, 0, 0, 0], device=device).repeat(G, 1))
        vc = torch.as_tensor(vcolor, dtype=torch.float32)[Fc][face]                 # (G,3,3)
        c0 = (vc * bary[..., None]).sum(1)
        self.sh0 = nn.Parameter(((c0 - 0.5) / C0).to(device))                       # SH0(視点によらない色)
        self.logit_op = nn.Parameter(torch.full((G,), 0.0, device=device))
        self.register_buffer("log_s_cap", torch.log(3.0 * spacing / sf).to(device))   # 1個あたりの最大スケール(絶対値で3×間隔)を相対値に直したもの

    def _areas(self, V):
        tri = V[self.Fc]
        return 0.5 * torch.linalg.norm(torch.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0], dim=-1), dim=-1)

    def frames(self, V):
        """三角形ごとの法線n、回転クォータニオンq(局所軸→世界)、大きさsf。"""
        tri = V[self.Fc]
        e0, e1 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
        nrm = torch.cross(e0, e1, dim=-1)
        area = 0.5 * torch.linalg.norm(nrm, dim=-1)
        n = F.normalize(nrm, dim=-1)
        t1 = F.normalize(e0, dim=-1)
        t2 = torch.cross(n, t1, dim=-1)
        R = torch.stack([t1, t2, n], -1)                     # 列が局所x,y,z軸
        return n, mat_to_quat(R), torch.sqrt(area)

    def gaussians(self, V=None):
        """(means, quats, scales, opacities, sh0) を返す。Vを与えると変形後の姿勢になる。"""
        V = self.V0 if V is None else V
        n, qf, sf = self.frames(V)
        tri = V[self.Fc][self.face]                          # (G,3,3)
        means = (tri * self.bary[..., None]).sum(1) + self.h[:, None] * n[self.face]
        q = quat_mul(qf[self.face], F.normalize(self.q_local, dim=-1))
        scales = torch.exp(torch.minimum(self.log_s, self.log_s_cap[:, None])) * sf[self.face][:, None]
        return means, q, scales, torch.sigmoid(self.logit_op), self.sh0

    def render(self, viewmat, K, size, V=None, bg=0.0):
        from gsplat import rasterization
        means, q, scales, op, sh0 = self.gaussians(V)
        out, alpha, info = rasterization(means, q, scales, op, sh0[:, None, :], viewmat[None].to(self.device), K[None].to(self.device), size, size,
                                         sh_degree=0, backgrounds=torch.full((1, 3), float(bg), device=self.device), packed=False)
        return out[0].clamp(0, 1), alpha[0, ..., 0], info

    def export_ply(self, path, V=None):
        """標準の3DGS形式(PLY、SH0)で書き出す。Unity等の既存ビューアで開ける。"""
        means, q, scales, op, sh0 = [t.detach().cpu().numpy() for t in self.gaussians(V)]
        G = len(means)
        names = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2", "opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
        arr = np.zeros((G, len(names)), dtype=np.float32)
        arr[:, 0:3] = means
        arr[:, 6:9] = sh0
        arr[:, 9] = np.log(np.clip(op, 1e-6, 1 - 1e-6) / (1 - np.clip(op, 1e-6, 1 - 1e-6)))
        arr[:, 10:13] = np.log(scales)
        arr[:, 13:17] = q
        head = "ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % G + "".join("property float %s\n" % n for n in names) + "end_header\n"
        with open(path, "wb") as f:
            f.write(head.encode())
            f.write(arr.tobytes())
