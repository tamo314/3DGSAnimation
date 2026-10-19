"""T5b: キャラの影(接地影・接触AO)を背景3DGSのスプラット色に焼き込む。

KIRIのライト反応(Relight)は背景全体を再ライトして二重照明になるため使わず、背景の焼き込み色を保ったまま、
キャラのメッシュ(プロキシ)で遮られるスプラットだけを暗くする。Unityでも同じ式をスプラットごと(または影デカール)で再現できる。

  太陽の遮蔽: スプラットから太陽円盤(角径 angle)内の複数方向へレイを飛ばし、キャラメッシュに当たる割合 frac を求める(ソフトな半影)。
  接触AO   : 足元付近のスプラットは上半球の余弦分布レイでキャラへの近さ(遮蔽 ao)を求める。
  暗くする量: 焼き込み色 c = rho*(a + s*lit)。lit = スプラットがどれだけ日向だったか(0..1, 焼き込み輝度から推定)。
              遮蔽後 c' = rho*(a*(1-k_ao*ao) + s*lit*(1-frac)) -> 係数 = (1-k_ao*ao + K*lit*(1-frac)) / (1 + K*lit)。  K=s/a は色ごと(較正値)。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gaussian"))
import spzply  # noqa: E402

C0 = 0.28209479177387814
# 日向/日陰の砂の焼き込み(線形RGB)の比 - 1 = 太陽/環境光(色ごと)。calibrate_light.py の結果 (3.41,3.62,3.20)-1
K_RGB = np.array([2.41, 2.62, 2.20], np.float32)
SAND_SHADE_LUM = 0.122


def srgb2lin(c):
    c = np.maximum(c, 0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.maximum(c, 0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def char_bvh(objs):
    import bpy
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    verts, tris = [], []
    for o in objs:
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        base = len(verts)
        verts += [tuple(o.matrix_world @ v.co) for v in me.vertices]
        tris += [tuple(base + i for i in t.vertices) for t in me.loop_triangles]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, tris)


def _cone_dirs(l, angle_deg, n, rng):
    """太陽円盤内の n 方向(一様)。"""
    l = np.asarray(l, float)
    t = np.cross(l, [0, 0, 1.0]); t /= np.linalg.norm(t)
    b = np.cross(l, t)
    r = np.tan(math.radians(angle_deg) / 2) * np.sqrt(rng.random(n))
    ph = rng.random(n) * 2 * math.pi
    d = l[None] + r[:, None] * (np.cos(ph)[:, None] * t[None] + np.sin(ph)[:, None] * b[None])
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def bake(cl, w, alpha, objs, sun_vec, sun_angle_deg=5.0, region=(-2.5, 3.5, -5.5, 2.0, -0.4, 3.0), n_sun=10, n_ao=16,
         ao_radius=0.9, k_ao=0.85, char_xy=(0.4, 0.0), ground_z=0.13, shadow_only=False, verbose=True, cull_margin=None):
    """cl: spzply.Cloud(RDF, 変更される)。w: 世界座標の位置(N,3)。戻り値: 統計dict。"""
    rng = np.random.default_rng(7)
    bvh = char_bvh(objs)
    rgb = 0.5 + C0 * cl.colors
    lin = srgb2lin(rgb)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    x0, x1, y0, y1, z0, z1 = region
    reg = (alpha > 0.3) & (w[:, 0] > x0) & (w[:, 0] < x1) & (w[:, 1] > y0) & (w[:, 1] < y1) & (w[:, 2] > z0) & (w[:, 2] < z1)
    l = np.asarray(sun_vec, np.float64)
    # 日向度: 砂は絶対輝度、砂以外は領域内の下位25%輝度を日陰基準にして同じ倍率で
    sand = (rgb[:, 0] > rgb[:, 2] * 1.15) & (rgb[:, 0] >= rgb[:, 1] * 0.98)
    ns = reg & ~sand & (np.hypot(w[:, 0] - char_xy[0], w[:, 1] - char_xy[1]) < 3.0) & (w[:, 2] < 0.6)
    ref_ns = float(np.percentile(lum[ns], 25)) if ns.sum() > 100 else 0.07
    ref = np.where(sand, SAND_SHADE_LUM, ref_ns)
    lit = np.clip((lum / np.maximum(ref, 1e-4) - 1.0) / 2.4, 0, 1)
    if verbose:
        print(f"bake: region splats {reg.sum()}, ref_nonsand {ref_ns:.3f}, lit mean {lit[reg].mean():.2f}")
    # 太陽の遮蔽候補: 太陽方向の線がキャラ中心の近く(<0.95m)を通り、太陽側にキャラがあるもの
    cc = np.array([char_xy[0], char_xy[1], ground_z + 0.62])
    d = cc[None] - w
    t_along = d @ l
    perp = np.linalg.norm(d - t_along[:, None] * l[None], axis=1)
    cand = np.where(reg & (t_along > 0) & (perp < 0.95))[0]
    # 接触AO候補: 足元の近く
    near = np.where(reg & (np.hypot(w[:, 0] - char_xy[0], w[:, 1] - char_xy[1]) < ao_radius + 0.4) & (w[:, 2] < ground_z + 0.55))[0]
    if verbose:
        print(f"bake: sun candidates {len(cand)}, ao candidates {len(near)}")
    from mathutils import Vector
    cone = _cone_dirs(l, sun_angle_deg, n_sun, rng)
    frac = np.zeros(len(w), np.float32)
    org_off = 0.03
    for i in cand:
        o = Vector(w[i]) + Vector((0, 0, 0))
        hit = 0
        for dv in cone:
            loc, nrm, idx, dist = bvh.ray_cast(o, Vector(dv))
            if loc is not None:
                hit += 1
        frac[i] = hit / n_sun
    ao = np.zeros(len(w), np.float32)
    # 余弦分布の上半球レイ
    u1, u2 = rng.random(n_ao), rng.random(n_ao)
    r = np.sqrt(u1); ph = 2 * math.pi * u2
    hemi = np.stack([r * np.cos(ph), r * np.sin(ph), np.sqrt(1 - u1)], 1)
    for i in near:
        o = Vector(w[i] + np.array([0, 0, 0.02]))
        s = 0.0
        for dv in hemi:
            loc, nrm, idx, dist = bvh.ray_cast(o, Vector(dv), ao_radius)
            if loc is not None:
                s += 1.0 - dist / ao_radius
        ao[i] = s / n_ao
    # 係数
    K = K_RGB[None]
    fac = (1.0 - k_ao * ao[:, None] + K * lit[:, None] * (1.0 - frac[:, None])) / (1.0 + K * lit[:, None])
    fac = np.where((frac[:, None] > 0) | (ao[:, None] > 0), fac, 1.0)
    changed = np.where(((frac > 0) | (ao > 0)) & reg)[0]
    newlin = lin.copy()
    newlin[changed] = lin[changed] * fac[changed]
    if not shadow_only:
        newrgb = lin2srgb(newlin)
        # 変更したスプラットだけ書き換える(それ以外は元の値のまま。f_dc の精度を保つ)
        cl.colors[changed] = ((newrgb[changed] - 0.5) / C0).astype(np.float32)
    culled = 0
    if cull_margin is not None:
        # キャラのメッシュの内側(または表面から cull_margin 以内)にあるスプラットを消す(プロキシ衝突の掃除)。足元の地面や体に被るゴーストの抑制
        from mathutils import Vector as V
        cc2 = np.array([char_xy[0], char_xy[1]])
        cand2 = np.where(reg & (np.abs(w[:, 0] - cc2[0]) < 0.6) & (np.abs(w[:, 1] - cc2[1]) < 0.6) & (w[:, 2] > ground_z - 0.1) & (w[:, 2] < ground_z + 1.45))[0]
        kill = []
        for i in cand2:
            pt = V(w[i])
            loc, nrm, idx, dist = bvh.find_nearest(pt, cull_margin)
            inside = loc is not None
            if not inside:
                # 上向きレイの交点数の偶奇で内外判定
                n = 0
                o = V(pt)
                for _ in range(8):
                    hl, hn, hi_, hd = bvh.ray_cast(o, V((0, 0, 1)))
                    if hl is None:
                        break
                    n += 1
                    o = hl + V((0, 0, 1e-4))
                inside = (n % 2) == 1
            if inside:
                kill.append(i)
        kill = np.array(kill, int)
        if len(kill):
            cl.alphas[kill] = -30.0
        culled = int(len(kill))
    stats = {"culled": culled, "sun_occluded": int((frac > 0).sum()), "ao_touched": int((ao > 0).sum()), "changed": int(len(changed)),
             "mean_factor_changed": float(fac[changed].mean()) if len(changed) else 1.0, "ref_nonsand": ref_ns}
    if verbose:
        print("bake:", stats)
    return stats
