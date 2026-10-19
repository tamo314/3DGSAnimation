"""統合シーン(T4)を組む: 背景3DGS(KIRI) + キャラメッシュ + 太陽 + 5視点カメラ。

Blender内(Blender MCPの execute_code)でも、ヘッドレス(blender -b --python ... -- ...)でも動く。
  import build_integration as bi; bi.build(); bi.render_all()

座標: 世界座標はキャラの足元が原点、X右・Y前方(アーチ方向)・Z上、地面 z=0。キャラは -Y(カメラ側)を向く。
縮尺: WORLD_SCALE を1か所変えれば、背景とカメラ位置が連動して変わる(キャラは常に実寸1.2m)。
  1.0  : World Labs推定のメートル換算そのまま(アーチ高さ約10m。キャラ1.2mは相対的に小さい)
  1/3  : 仮案(アーチ高さ約3.2m)
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spike_common as sc  # noqa: E402

REPO = sc.REPO

# ---- 調整用の定数 -------------------------------------------------------------------------
WORLD_SCALE = 1.0                # 背景(とカメラ位置)の縮尺。ユーザー確定: 生成時の縮尺のまま(1.0)。1か所だけ変えればよい
BG_VARIANT = "full_res"         # full_res(192万, KIRI描画では500kより鮮明で針状ノイズが少ない) / 500k
CHAR_SPOT_METRIC = (0.0, 3.5)    # キャラ位置 = 元カメラの前方 (x右, y前) メートル(縮尺前の世界)。camera_pathsの原点と一致させる
CHAR_YAW_DEG = 0.0               # キャラの向き(0 = -Y向き=カメラ側のまま)
CHAR_POS = (0.4, 0.0)            # キャラの足元(世界座標 x, y, m)。小道の砂色の帯の中央付近(analyze_ground.py の測定)。背景・カメラは世界固定
CHAR_GROUND_Z = 0.13             # その位置の背景の地面高さ(m)。キャラ位置の地面は z=0 でなく約0.1〜0.2m高い(analyze_ground.py)
RENDER_SIZE = (1440, 1080)
KIRI_SH = 0                      # 背景はSH0

ASSET_CANDIDATES = [os.path.join(REPO, "assets", "generated"), r"C:/Work/3DGSAnimation/assets/generated"]


def asset(*parts):
    for root in ASSET_CANDIDATES:
        p = os.path.join(root, *parts)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(os.path.join(*parts))


def load_world_meta():
    with open(asset("background", "world_meta.json"), encoding="utf-8") as f:
        return json.load(f)


def load_lighting():
    for p in (asset_safe("background", "lighting_estimate.json"),):
        if p:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return None


def asset_safe(*parts):
    try:
        return asset(*parts)
    except FileNotFoundError:
        return None


# ---- 背景 -------------------------------------------------------------------------------
def import_background(meta=None, scale=None):
    """背景PLY(RDF, SPZ座標)を取り込み、Blender世界座標(キャラ足元が原点)に置く。"""
    meta = meta or load_world_meta()
    S = WORLD_SCALE if scale is None else scale
    k0 = meta["coordinates"]["metric_scale_factor"]
    eye_h = meta["coordinates"]["ground_plane_offset"]
    name = {"500k": "forest_clearing_500k.ply", "full_res": "forest_clearing_full_res.ply"}[BG_VARIANT]
    ob = sc.kiri_import_ply(asset("background", name), "background")
    # RDF -> Blender: X軸 -90度。メートル換算(k0)と縮尺(S)を掛け、元カメラをキャラ前方(-CHAR_SPOT)・視点高の位置へ。
    ob.rotation_euler = (math.radians(-90.0), 0.0, 0.0)
    ob.scale = (k0 * S,) * 3
    ob.location = (-CHAR_SPOT_METRIC[0] * S, -CHAR_SPOT_METRIC[1] * S, eye_h * S)
    sc.kiri_make_proxy(ob)
    ob.hide_set(True)
    ob.hide_render = True
    return ob


# ---- キャラ -----------------------------------------------------------------------------
def import_character(path=None):
    path = path or asset("character", "normalized", "girl_healer.glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new("character", None)
    bpy.context.scene.collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    root.location = (CHAR_POS[0], CHAR_POS[1], CHAR_GROUND_Z)
    root.rotation_euler = (0, 0, math.radians(CHAR_YAW_DEG))
    return root, new


def world_bbox(objs):
    import mathutils
    pts = []
    for o in objs:
        if o.type == "MESH":
            pts += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    return lo, hi


# ---- ライト・ワールド ---------------------------------------------------------------------
def setup_lights(lighting=None):
    """T5aの光源推定を仮の太陽として置く(本格的なライティング調整は次の段階)。"""
    lighting = lighting or load_lighting()
    rot = (65.8, 0.0, 162.4)
    color = (1.0, 0.834, 0.621)
    angle = 6.0
    if lighting:
        s = lighting["sun"]
        rot = tuple(s["blender_sun_rotation_euler_deg_XYZ"])
        color = tuple(s["color_linear_rgb"])
        angle = s.get("angular_diameter_deg_recommended", 6.0)
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy = 3.0
    ld.color = color
    ld.angle = math.radians(angle)
    sun = bpy.data.objects.new("sun", ld)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = tuple(math.radians(a) for a in rot)
    sun.location = (0, 0, 10)
    # ワールド: 太陽:環境光 = 4 になる強さ(S*sin(el)/(pi*A)=4)。色は日陰の中立〜暖色
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.983, 1.0, 0.963, 1.0)
    bg.inputs["Strength"].default_value = 0.10
    return sun


# ---- カメラ -----------------------------------------------------------------------------
def make_cameras(scale=None, path=None):
    """camera_paths_background.json(元メートル世界)を縮尺Sで縮めてカメラ化する。焦点距離は変えない。"""
    S = WORLD_SCALE if scale is None else scale
    path = path or os.path.join(REPO, "scripts", "background", "camera_paths_background.json")
    spec = json.load(open(path, encoding="utf-8"))
    for c in spec["cameras"]:
        c["position"] = [v * S for v in c["position"]]
        c["target"] = [v * S for v in c["target"]]
    return sc.create_cameras_from_json(spec), spec


# ---- シーン構築 -------------------------------------------------------------------------
def build(scale=None):
    sc.init_gpu()
    sc.enable_kiri()
    sc.clear_scene()
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.images):
        for b in list(blk):
            if b.users == 0:
                blk.remove(b)
    sc.set_render(*RENDER_SIZE)
    bg = import_background(scale=scale)
    root, objs = import_character()
    sun = setup_lights()
    cams, spec = make_cameras(scale)
    sp = sc.kiri_props()
    sp.active_mode = "Render"
    sp.r2_relight = False
    bpy.context.scene.camera = cams["front_wide"]
    lo, hi = world_bbox(objs)
    return {"bg": bg.name, "char_bbox": (lo, hi), "cameras": list(cams)}


def render_all(out_dir, names=None, tag="", comp=True):
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    res = {}
    for ob in bpy.data.objects:
        if ob.type == "CAMERA" and (names is None or ob.name in names):
            bpy.context.scene.camera = ob
            r = sc.kiri_render(os.path.join(out_dir, f"{tag}{ob.name}_"), comp=comp, sh_degree=KIRI_SH)
            res[ob.name] = list(r)
    return res
