"""T5b: 背景に焼き込まれた光に合わせてキャラ側のライト(太陽+空のグラデーション環境光)を作る。

物理量の対応(Eevee, 白の拡散面, Standard変換): 水平面の画素値(線形) = S*sin(el)/pi (太陽) + A (ワールド強さ1の一様環境光でA=1)。
 -> 太陽 S = horizontal_irradiance * pi / sin(el)。環境光はグラデーションを積分して上向き水平面の値が horizontal_irradiance になるよう強さを決める。
 horizontal_irradiance の太陽:環境光 ≒ 0.71:0.29 は、背景の小道の日向/日陰の焼き込み色の比(約3.4:1)から較正した(scripts/lighting/calibrate_light.py)。
方位は +Y(アーチ方向)から +X へ測る。太陽ライトの回転: Z回転 = 180 + az, X回転 = 90 - el (ライトは -Z 方向を向く)。
"""
from __future__ import annotations

import json
import math
import os

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "..", "lighting", "lighting_config.json")


def load_config(path=None):
    with open(path or CONFIG, encoding="utf-8") as f:
        return json.load(f)


def sun_vector(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))


def _ramp(z, cfg):
    """方向のz(-1..1)に対する環境色(線形RGB)。天頂-水平-天底の区分線形。"""
    a = cfg["ambient"]
    top, hor, bot = (np.array(a[k]) for k in ("zenith_rgb", "horizon_rgb", "nadir_rgb"))
    if z >= 0:
        t = min(1.0, z / 0.6)          # 仰角約37°で天頂色に達する
        return hor * (1 - t) + top * t
    t = min(1.0, -z / 0.6)
    return hor * (1 - t) + bot * t


def ambient_up_irradiance_unit(cfg):
    """ワールド強さ1のとき、上向き水平白面の画素値(線形RGB)。cos重み付き半球積分/pi。"""
    ths = np.linspace(0, math.pi / 2, 400)
    vals = np.array([_ramp(math.cos(t), cfg) * math.cos(t) * math.sin(t) for t in ths])
    return 2 * np.trapezoid(vals, ths, axis=0)


def setup(cfg=None, name="sun"):
    cfg = cfg or load_config()
    s = cfg["sun"]
    el = s["elevation_deg"]
    sun_s = s["horizontal_irradiance"] * math.pi / math.sin(math.radians(el))
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy = sun_s
    ld.color = tuple(s["color_linear_rgb"])
    ld.angle = math.radians(s["angle_deg"])
    sun = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(90 - el), 0.0, math.radians(180 + s["azimuth_deg"]))
    sun.location = (0, 0, 10)

    # 環境光: 空のグラデーション(天頂=青み、水平=緑がかった暖色、天底=砂の照り返し)
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        if n.type not in ("OUTPUT_WORLD",):
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")       # z(-1..1) -> 0..1
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -1.0, 1.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "LINEAR"
    # 位置は z=-0.6,0,+0.6 を 0.2,0.5,0.8 に対応
    e = ramp.color_ramp.elements
    e[0].position, e[1].position = 0.2, 0.8
    e[0].color = (*cfg["ambient"]["nadir_rgb"], 1)
    e[1].color = (*cfg["ambient"]["zenith_rgb"], 1)
    mid = e.new(0.5)
    mid.color = (*cfg["ambient"]["horizon_rgb"], 1)
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    f = cfg.get("fill")
    if f:
        ldf = bpy.data.lights.new("fill", "SUN")
        ldf.energy = f["front_vertical_irradiance"] * math.pi / math.cos(math.radians(f["elevation_deg"]))
        ldf.color = tuple(f["color_linear_rgb"])
        ldf.angle = math.radians(f["angle_deg"])
        ldf.use_shadow = False
        fo = bpy.data.objects.new("fill", ldf)
        bpy.context.scene.collection.objects.link(fo)
        fo.rotation_euler = (math.radians(90 - f["elevation_deg"]), 0.0, math.radians(180 + f["azimuth_deg"]))
        fo.location = (0, 0, 10)
    unit = ambient_up_irradiance_unit(cfg)
    lum = unit @ np.array([0.2126, 0.7152, 0.0722])
    bg.inputs["Strength"].default_value = cfg["ambient"]["horizontal_irradiance"] / lum
    return sun, bg


# ---- 樹冠の木漏れ日(ゴボ) -------------------------------------------------------------
def add_canopy_gobo(cfg, litmap_path, char_center, ground_z, dist=1.5, half=(1.15, 1.25), px=0.01, floor=0.0, name="canopy_gobo"):
    """太陽とキャラの間に、カメラには映らず影だけ落とす板を置く。
    板の不透明度 = 1 - 日向度(g)。g は板上の点から太陽方向の線を地面まで下ろした点で、背景の焼き込み輝度から作った日向度マップ
    (build_litmap.py)を引く。= 背景の地面に焼き込まれた木漏れ日の模様を、キャラの体にも同じ太陽方向で落とす。"""
    d = np.load(litmap_path)
    lit, x0, y1, res = d["lit"], float(d["x0"]), float(d["y1"]), float(d["res"])
    s = cfg["sun"]
    az, el = math.radians(s["azimuth_deg"]), math.radians(s["elevation_deg"])
    l = np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])
    u = np.array([math.cos(az), -math.sin(az), 0.0])
    v = np.cross(l, u)
    if v[2] < 0:
        v = -v
    c = np.asarray(char_center, float) + l * dist
    nu, nv = int(2 * half[0] / px), int(2 * half[1] / px)
    ss = (np.arange(nu) + 0.5) * px - half[0]
    tt = (np.arange(nv) + 0.5) * px - half[1]
    S, T = np.meshgrid(ss, tt)
    q = c[None, None, :] + S[..., None] * u[None, None, :] + T[..., None] * v[None, None, :]
    g = q - l[None, None, :] * ((q[..., 2] - ground_z) / l[2])[..., None]
    fx = (g[..., 0] - x0) / res - 0.5
    fy = (y1 - g[..., 1]) / res - 0.5
    ix = np.clip(np.floor(fx).astype(int), 0, lit.shape[1] - 2)
    iy = np.clip(np.floor(fy).astype(int), 0, lit.shape[0] - 2)
    wx = np.clip(fx - ix, 0, 1)
    wy = np.clip(fy - iy, 0, 1)
    val = (lit[iy, ix] * (1 - wx) * (1 - wy) + lit[iy, ix + 1] * wx * (1 - wy)
           + lit[iy + 1, ix] * (1 - wx) * wy + lit[iy + 1, ix + 1] * wx * wy)
    val = floor + (1 - floor) * val
    opacity = 1.0 - val
    img = bpy.data.images.new(name + "_tex", nu, nv, alpha=True, float_buffer=False)
    rgba = np.zeros((nv, nu, 4), np.float32)
    rgba[..., 3] = opacity
    img.pixels.foreach_set(rgba.ravel())
    img.colorspace_settings.name = "Non-Color"
    img.pack()
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    tex.extension = "CLIP"
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    for attr, val_ in (("surface_render_method", "DITHERED"), ("use_transparent_shadow", True)):
        if hasattr(mat, attr):
            setattr(mat, attr, val_)
    me = bpy.data.meshes.new(name)
    hw, hh = half
    verts = [tuple(c + (-hw) * u + (-hh) * v), tuple(c + hw * u + (-hh) * v), tuple(c + hw * u + hh * v), tuple(c + (-hw) * u + hh * v)]
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, co in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = co
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
        if hasattr(ob, attr):
            setattr(ob, attr, False)
    ob.visible_shadow = True
    return ob, float(val.mean())
