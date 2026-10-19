"""T5b: 統合シーン(T4)にライティングを施して組む。
 - 太陽(背景の焼き込み影の方向)と空グラデーション環境光(lighting.py)
 - 樹冠ゴボ(キャラへの木漏れ日, lighting.add_canopy_gobo)
 - キャラの影・接触AOを背景スプラット色へ焼き込み(shadow_bake.py。キャッシュあり)
KIRIのRelightは使わず、背景は焼き込み色のまま描く。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "gaussian"))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import build_integration as bi  # noqa: E402
import lighting  # noqa: E402
import shadow_bake  # noqa: E402
import spike_common as sc  # noqa: E402
import spzply  # noqa: E402

REPO = bi.REPO
EXP = os.path.join(REPO, "experiments", "T5")
LITMAP = os.path.join(EXP, "litmap.npz")


def baked_background_ply(objs, cfg, force=False, **kw):
    """キャラ影を焼き込んだ背景PLYのパスを返す(設定ごとにキャッシュ)。"""
    orig = bi.asset("background", "forest_clearing_full_res.ply")
    key = hashlib.md5(json.dumps([cfg["sun"], kw, bi.CHAR_POS, bi.CHAR_GROUND_Z, bi.CHAR_YAW_DEG, bi.WORLD_SCALE],
                                 sort_keys=True).encode()).hexdigest()[:10]
    out = os.path.join(EXP, "bake", f"forest_clearing_full_res_charshadow_{key}.ply")
    if os.path.exists(out) and not force:
        print("bake: cached", out)
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    meta = bi.load_world_meta()
    k0 = meta["coordinates"]["metric_scale_factor"]
    eye = meta["coordinates"]["ground_plane_offset"]
    S = bi.WORLD_SCALE
    cl = spzply.read_ply(orig, "RDF")
    p = cl.positions
    w = np.stack([p[:, 0], p[:, 2], -p[:, 1]], 1) * k0 * S + np.array(
        [-bi.CHAR_SPOT_METRIC[0], -bi.CHAR_SPOT_METRIC[1], eye]) * S
    alpha = 1 / (1 + np.exp(-np.clip(cl.alphas, -30, 30)))
    sun = cfg["sun"]
    sv = lighting.sun_vector(sun["azimuth_deg"], sun["elevation_deg"])
    stats = shadow_bake.bake(cl, w, alpha, objs, sv, sun_angle_deg=sun["angle_deg"], char_xy=bi.CHAR_POS,
                             ground_z=bi.CHAR_GROUND_Z, **kw)
    spzply.write_ply(cl, out)
    json.dump(stats, open(out + ".json", "w"), indent=1)
    return out


def build(cfg, bake=True, gobo=True, gobo_floor=None, bake_kw=None, samples=64):
    sc.init_gpu()
    sc.enable_kiri()
    sc.clear_scene()
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.images):
        for b in list(blk):
            if b.users == 0:
                blk.remove(b)
    sc.set_render(*bi.RENDER_SIZE, samples=samples)
    root, objs = bi.import_character()
    sun, bg_node = lighting.setup(cfg)
    info = {}
    if gobo:
        center = (bi.CHAR_POS[0], bi.CHAR_POS[1], bi.CHAR_GROUND_Z + 0.65)
        ob, mean_lit = lighting.add_canopy_gobo(cfg, LITMAP, center, bi.CHAR_GROUND_Z, floor=cfg.get("canopy_gobo", {}).get("floor", 0.0) if gobo_floor is None else gobo_floor)
        info["gobo_mean_transmission"] = mean_lit
    real_asset = bi.asset
    if bake:
        path = baked_background_ply(objs, cfg, **(bake_kw or {}))
        bi.asset = lambda *parts: path if parts[-1] == "forest_clearing_full_res.ply" else real_asset(*parts)
    bg = bi.import_background()
    bi.asset = real_asset
    cams, spec = bi.make_cameras()
    sp = sc.kiri_props()
    sp.active_mode = "Render"
    sp.r2_relight = False
    bpy.context.scene.camera = cams["front_wide"]
    info["cameras"] = list(cams)
    return info
