"""Blender + KIRI 3DGS Render のスパイク用共通関数(ヘッドレス実行前提)。

実行例:
  blender --factory-startup -b --python scripts/blender/spike_kiri.py -- --exp basic --out experiments/spike/out
BLENDER_USER_EXTENSIONS に専用拡張フォルダを指定すること(run_spike.ps1が設定する)。
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
import mathutils

KIRI_MODULE = "bl_ext.user_default.dgs_render_by_kiri_engine"
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def init_gpu():
    """ヘッドレス(-b)でもGPUオフスクリーン描画を使えるようにする(Blender 5.xのgpu.init)。"""
    import gpu
    gpu.init()


def enable_kiri():
    bpy.ops.preferences.addon_enable(module=KIRI_MODULE)
    assert KIRI_MODULE in bpy.context.preferences.addons, "KIRIアドオンを有効化できません"


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def look_at(obj, target, roll_deg=0.0):
    direction = mathutils.Vector(target) - obj.location
    quat = direction.to_track_quat("-Z", "Y")
    if roll_deg:
        quat = quat @ mathutils.Quaternion((0, 0, 1), math.radians(roll_deg))
    obj.rotation_euler = quat.to_euler()


def load_camera_paths(path=None):
    path = path or os.path.join(REPO, "scripts", "gaussian", "camera_paths.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_camera(name, position, target, focal_mm=35.0, sensor_mm=36.0, roll_deg=0.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = focal_mm
    cam_data.sensor_width = sensor_mm
    cam_data.sensor_fit = "HORIZONTAL"
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = position
    look_at(cam, target, roll_deg)
    return cam


def create_cameras_from_json(spec=None):
    """camera_paths.json から5台のカメラを作る。{name: object}"""
    spec = spec or load_camera_paths()
    out = {}
    for c in spec["cameras"]:
        out[c["name"]] = make_camera(c["name"], c["position"], c["target"], c["focal_length_mm"],
                                     spec["render"]["sensor_width_mm"], c.get("roll_deg", 0.0))
    return out


def set_render(width, height, engine="BLENDER_EEVEE", samples=16):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    if engine == "BLENDER_EEVEE" and hasattr(sc.eevee, "taa_render_samples"):
        sc.eevee.taa_render_samples = samples


def make_material(name, color, roughness=0.6, metallic=0.0, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.0
    return mat


def add_mesh(kind, name, location, size, mat, **kw):
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    elif kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=size, location=location, segments=48, ring_count=24)
    elif kind == "plane":
        bpy.ops.mesh.primitive_plane_add(size=size, location=location)
    ob = bpy.context.active_object
    ob.name = name
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = kind == "sphere"
    if "scale" in kw:
        ob.scale = kw["scale"]
    return ob


def add_light(kind, name, location, energy, color=(1, 1, 1), target=None, size=None, spot_deg=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "SUN":
        ld.angle = math.radians(2.0)
    if kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size if size is not None else 0.1
    if kind == "SPOT" and spot_deg:
        ld.spot_size = math.radians(spot_deg)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = location
    if target is not None:
        look_at(ob, target)
    return ob


def set_world(color=(0.05, 0.05, 0.06), strength=1.0):
    w = bpy.data.worlds.new("World") if not bpy.context.scene.world else bpy.context.scene.world
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength


# --- KIRI 3DGS Render ---------------------------------------------------------------------
def kiri_import_ply(path, name=None):
    """PLYを取り込み、KIRIのガウシアンメッシュ(Editモード用)として返す。"""
    before = set(bpy.data.objects)
    res = bpy.ops.sna.dgs_render_import_ply_e0a3a(filepath=os.path.abspath(path))
    assert res == {"FINISHED"}, res
    new = [o for o in bpy.data.objects if o not in before]
    assert len(new) == 1, new
    ob = new[0]
    if name:
        ob.name = name
    return ob


def kiri_make_proxy(ob):
    """ガウシアンメッシュからレンダー用プロキシ(Empty)を作る。"""
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.hide_set(False)
    ob.hide_viewport = False
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    res = bpy.ops.sna.dgs_render_create_proxy_from_mesh_eafbb()
    assert res == {"FINISHED"}, res


def kiri_props():
    return bpy.context.scene.sna_dgs_scene_properties


def kiri_render(out_png, comp=True, sh_degree=3, depth=False):
    """KIRIのAdvanced Render(ガウシアン描画 + ネイティブレンダーとの深度合成)を実行する。"""
    sp = kiri_props()
    sp.r2_color = True
    sp.r2_depth = depth
    sp.r2_comp = comp
    sp.r2_animation = False
    sp.r2_sh_degree = sh_degree
    sp.r2_delete_temp_files = False
    bpy.context.scene.render.filepath = os.path.abspath(out_png)
    res = bpy.ops.sna.dgs_render_advanced_render_147af()
    return res


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="basic")
    ap.add_argument("--out", default=os.path.join(REPO, "experiments", "spike", "out"))
    ap.add_argument("--splats", default=os.path.join(REPO, "experiments", "spike", "splats"))
    ap.add_argument("--camera", default="front_wide")
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--height", type=int, default=720)
    return ap.parse_args(argv)
