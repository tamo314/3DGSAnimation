"""KIRI 3DGS Render スパイク: 合成ガウシアン+メッシュの遮蔽・影・ライト反応を確認する。

  blender --factory-startup -b --python scripts/blender/spike_kiri.py -- --exp basic
実験名(--exp): basic / light_a / light_b / shadow_mesh2gs / shadow_gs2mesh ...
"""
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402

import spike_common as sc  # noqa: E402


def build_mesh_scene(args, with_light=True, sun_color=(1.0, 1.0, 1.0), sun_energy=3.0):
    sc.clear_scene()
    sc.set_render(args.width, args.height)
    sc.set_world((0.05, 0.05, 0.06), 1.0)
    gray = sc.make_material("gray", (0.6, 0.6, 0.62))
    white = sc.make_material("white", (0.9, 0.9, 0.9))
    purple = sc.make_material("purple", (0.55, 0.25, 0.75))
    cube = sc.add_mesh("cube", "mesh_cube", (0.0, 0.8, 0.5), 1.0, gray)
    floor = sc.add_mesh("plane", "mesh_floor", (2.2, 0.0, 0.02), 1.0, white, scale=(2.0, 3.0, 1.0))
    ball = sc.add_mesh("sphere", "mesh_ball_in_wall", (-1.0, 3.0, 0.6), 0.4, purple)
    sc.add_light("SUN", "sun", (-4.0, -4.0, 6.0), sun_energy, sun_color, target=(0, 0, 0)) if with_light else None
    cam = sc.make_camera("spike_cam", (0.0, -6.0, 1.5), (0.0, 1.0, 0.8), 35.0)
    bpy.context.scene.camera = cam
    return cube, floor, ball


def import_splats(args, names):
    objs = []
    for n in names:
        ob = sc.kiri_import_ply(os.path.join(args.splats, n + ".ply"), n)
        objs.append(ob)
    return objs


def render_native(args, tag):
    bpy.context.scene.render.filepath = os.path.join(args.out, f"{tag}_native.png")
    bpy.ops.render.render(write_still=True)


def run_case(args, tag, relight=False, sun_color=(1.0, 1.0, 1.0), sun_energy=3.0, sun_pos=(-4.0, -4.0, 6.0),
             relight_kwargs=None, shadows=False, shadow_proxy=False, world=None, extra_lights=(), sh_degree=3,
             hide_splats=(), cam=None, names=None, mesh_scene=True, floors=None):
    """合成シーンを組み、ネイティブ単体とKIRI合成の2枚を <tag>_native.png / <tag>.png に出す。"""
    if mesh_scene:
        build_mesh_scene(args, with_light=False)
    else:
        sc.clear_scene()
        sc.set_render(args.width, args.height)
        sc.set_world((0.05, 0.05, 0.06), 1.0)
    if cam is not None:
        c = sc.make_camera("case_cam", cam[0], cam[1], cam[2] if len(cam) > 2 else 35.0)
        bpy.context.scene.camera = c
    for i, (h, col) in enumerate(floors or []):
        m = sc.make_material(f"fl{i}", col)
        sc.add_mesh("plane", f"floor_h{h}", (-1.8 + i * 0.6, -1.0, h), 1.0, m, scale=(0.4, 0.4, 1.0))
    sun = sc.add_light("SUN", "sun", sun_pos, sun_energy, sun_color, target=(0, 0, 0))
    for kind, name, loc, energy, color in extra_lights:
        sc.add_light(kind, name, loc, energy, color, size=0.2)
    if world is not None:
        sc.set_world(*world)
    names = names or ["ground", "wall", "ballA", "ballB", "ballC"]
    objs = import_splats(args, names)
    if "ballA" in names:
        objs[names.index("ballA")].location = (0.45, 1.8, 0.0)  # キューブの右にずらして一部だけ見せる
    for ob in objs:
        sc.kiri_make_proxy(ob)
    sp = sc.kiri_props()
    sp.active_mode = "Render"
    sp.r2_relight = relight
    for k, v in (relight_kwargs or {}).items():
        setattr(sp, k, v)
    if shadows:
        sp.r2_shadows = True
        sp.r2_shadow_light = sun
    if shadow_proxy:
        sp.r2_shadow_proxy = True
    render_native(args, tag)  # ガウシアン無しのネイティブ参照(プロキシはEmptyなので映らない)
    if shadows:
        try:
            print("SPIKE refresh_shadows", bpy.ops.sna.dgs_render_refresh_shadows_16f2b())
        except Exception as e:
            print("SPIKE refresh_shadows failed", repr(e))
    if shadow_proxy:
        print("SPIKE build_shadow_proxies", bpy.ops.sna.dgs_render_build_shadow_proxies_5b787())
    t = time.time()
    res = sc.kiri_render(os.path.join(args.out, tag), comp=True, sh_degree=sh_degree)
    print("SPIKE", tag, res, f"{time.time()-t:.1f}s")


def exp_basic(args):
    run_case(args, "c0_norelight")


def exp_relight(args):
    run_case(args, "c1_relight_white", relight=True, relight_kwargs=dict(r2_relight_strength=1.0))
    run_case(args, "c2_relight_orange", relight=True, sun_color=(1.0, 0.5, 0.2), relight_kwargs=dict(r2_relight_strength=1.0))
    run_case(args, "c3_relight_blue_dim", relight=True, sun_color=(0.3, 0.4, 1.0), sun_energy=1.0,
             relight_kwargs=dict(r2_relight_strength=1.0))


def exp_shadow_m2g(args):
    run_case(args, "c4_shadow_m2g", relight=True, shadows=True, relight_kwargs=dict(r2_relight_strength=1.0))


def exp_shadow_g2m(args):
    run_case(args, "c5_shadow_g2m", relight=True, shadow_proxy=True, relight_kwargs=dict(r2_relight_strength=1.0))


def exp_calib(args):
    for st in (0.1, 0.2, 0.4):
        run_case(args, f"k_strength_{st}", relight=True, relight_kwargs=dict(r2_relight_strength=st))


def exp_shadow_tuned(args):
    kw = dict(r2_relight_strength=0.2)
    run_case(args, "k_shadow_m2g", relight=True, shadows=True, relight_kwargs=kw)
    run_case(args, "k_shadow_both", relight=True, shadows=True, shadow_proxy=True, relight_kwargs=kw)


def exp_pointlight(args):
    kw = dict(r2_relight_strength=0.2)
    # 太陽なし(エネルギー0)、ボールBの左右に点光源を置く
    run_case(args, "k_point_left", relight=True, sun_energy=0.0, relight_kwargs=kw,
             extra_lights=[("POINT", "pl", (-0.6, -1.2, 1.0), 300.0, (1.0, 0.8, 0.6))])
    run_case(args, "k_point_right", relight=True, sun_energy=0.0, relight_kwargs=kw,
             extra_lights=[("POINT", "pl", (1.8, -1.2, 1.0), 300.0, (1.0, 0.8, 0.6))])


def exp_tol(args):
    """メッシュ面が地面ガウシアン(z=0)の上下どの高さにあるとき、どちらが勝つか(深度合成の許容)。"""
    red = (0.9, 0.05, 0.05)
    hs = [-0.05, 0.0, 0.005, 0.02, 0.05, 0.1, 0.2]
    run_case(args, "t_tol", relight=False, mesh_scene=False, names=["ground"], cam=((0.0, -1.0, 6.0), (0.0, -1.0, 0.0), 35.0),
             floors=[(h, red) for h in hs])


def exp_shadow_top(args):
    cam = ((0.5, -3.5, 7.0), (0.8, 0.8, 0.0), 35.0)
    kw = dict(r2_relight_strength=0.2)
    run_case(args, "t_top_noshadow", relight=True, relight_kwargs=kw, cam=cam)
    run_case(args, "t_top_shadow_m2g", relight=True, shadows=True, relight_kwargs=kw, cam=cam)


def exp_lizard(args):
    """公開サンプル(hornedlizard.spz→PLY(RDF))での規模・速度・向きの確認。"""
    import numpy as np
    sys.path.insert(0, os.path.join(sc.REPO, "scripts", "gaussian"))
    import spzply
    path = os.path.join(args.splats, "lizard.ply")
    cl = spzply.read_ply(path, "RDF")
    pos = cl.positions
    core = pos[(np.linalg.norm(pos - np.median(pos, 0), axis=1) < 3.0)]
    c = np.median(core, 0)
    print("SPIKE lizard core center (RDF)", c, "core pts", len(core))
    sc.clear_scene()
    sc.set_render(args.width, args.height)
    sc.set_world((0.05, 0.05, 0.06), 1.0)
    t = time.time()
    ob = sc.kiri_import_ply(path, "lizard")
    print("SPIKE lizard import s", round(time.time() - t, 1))
    ob.rotation_euler = (-1.5707963, 0, 0)  # RDF -> Blender(Z up)
    cb = (c[0], c[2], -c[1])  # 回転後の中心
    sc.kiri_make_proxy(ob)
    # 回転はプロキシ作成後に反映されるか確認するため、プロキシ側にも同じ回転を与える
    px = [o for o in bpy.data.objects if o.name.endswith("Splat_Proxy")][0]
    print("SPIKE proxy", px.name, tuple(px.rotation_euler))
    cam = sc.make_camera("lizard_cam", (cb[0], cb[1] - 4.0, cb[2] + 1.0), cb, 35.0)
    bpy.context.scene.camera = cam
    sc.kiri_props().active_mode = "Render"
    t = time.time()
    res = sc.kiri_render(os.path.join(args.out, "lizard"), comp=False, sh_degree=3)
    print("SPIKE lizard render", res, f"{time.time()-t:.1f}s")


EXPS = {"basic": exp_basic, "relight": exp_relight, "shadow_m2g": exp_shadow_m2g, "shadow_g2m": exp_shadow_g2m,
        "calib": exp_calib, "lizard": exp_lizard, "tol": exp_tol, "shadow_top": exp_shadow_top, "shadow_tuned": exp_shadow_tuned, "pointlight": exp_pointlight}

if __name__ == "__main__":
    args = sc.parse_args()
    args.out = os.path.abspath(args.out)
    os.makedirs(args.out, exist_ok=True)
    sc.init_gpu()
    sc.enable_kiri()
    try:
        EXPS[args.exp](args)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    print("SPIKE done", os.listdir(args.out))
