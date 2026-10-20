"""T7: キャラ(girl_healer.glb)を多視点で描画し、COLMAPテキスト形式のデータセットを作る(ヘッドレス)。
参照研究(MILo / G-Style / GaussianShader / Frosting)を実行するための入力。実画像のCOLMAPは使わず、Blenderのカメラ姿勢をそのまま書き出す。
  blender --factory-startup -b --python scripts/blender/render_char_dataset.py -- --out experiments/T7/data/char_scene --light scene --views 144 --size 1024
出力: images/*.png(RGBA)、sparse/0/{cameras,images,points3D}.txt、points3D.ply、views.json、char_info.json
座標: Blender世界座標(Z上、キャラ足元原点、前方 -Y)。COLMAPのカメラ規約(+Z前方、+Y下)へ変換して書く。
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import mathutils  # noqa: E402
import numpy as np  # noqa: E402

import lighting  # noqa: E402
import spike_common as sc  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--light", default="scene", choices=["scene", "neutral"], help="scene: T5の太陽+空+フィル / neutral: 一様な環境光のみ")
ap.add_argument("--views", type=int, default=144)
ap.add_argument("--size", type=int, default=1024)
ap.add_argument("--radius", type=float, default=2.1)
ap.add_argument("--lens", type=float, default=50.0)
ap.add_argument("--elev-min", type=float, default=-15.0)
ap.add_argument("--elev-max", type=float, default=75.0)
ap.add_argument("--points", type=int, default=120000)
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--glb", default=None)
a = ap.parse_args(argv)

out = os.path.abspath(a.out)
os.makedirs(os.path.join(out, "images"), exist_ok=True)
os.makedirs(os.path.join(out, "sparse", "0"), exist_ok=True)

sc.init_gpu()
sc.clear_scene()
for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.images):
    for b in list(blk):
        if b.users == 0:
            blk.remove(b)
sc.set_render(a.size, a.size, samples=a.samples)
scene = bpy.context.scene
scene.render.film_transparent = True

# キャラ: 足元原点、-Y向き(統合シーンと同じ向き)。位置は原点に置く
glb = a.glb or r"C:/Work/3DGSAnimation/assets/generated/character/normalized/girl_healer.glb"
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
new = [o for o in bpy.data.objects if o not in before]
root = bpy.data.objects.new("character", None)
scene.collection.objects.link(root)
for o in new:
    if o.parent is None:
        o.parent = root

cfg = lighting.load_config()
if a.light == "scene":
    lighting.setup(cfg)
else:
    w = scene.world or bpy.data.worlds.new("World")
    scene.world = w
    w.use_nodes = True
    bgn = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs["Color"].default_value = (1, 1, 1, 1)
    bgn.inputs["Strength"].default_value = 1.0

dg = bpy.context.evaluated_depsgraph_get()
dg.update()
# メッシュ(全オブジェクト)の頂点と三角形を集めて表面点群を作る
verts, tris = [], []
off = 0
for o in new:
    if o.type != "MESH":
        continue
    eo = o.evaluated_get(dg)
    me = eo.to_mesh()
    me.calc_loop_triangles()
    v = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", v)
    v = v.reshape(-1, 3)
    mw = np.array(eo.matrix_world)
    v = v @ mw[:3, :3].T + mw[:3, 3]
    t = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", t)
    verts.append(v)
    tris.append(t.reshape(-1, 3) + off)
    off += len(v)
    eo.to_mesh_clear()
verts = np.concatenate(verts)
tris = np.concatenate(tris)
bmin, bmax = verts.min(0), verts.max(0)
print("T7 mesh bbox", bmin, bmax, "tris", len(tris))
rng = np.random.default_rng(a.seed)
p0, p1, p2 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
idx = rng.choice(len(tris), size=a.points, p=area / area.sum())
u, v_ = rng.random(a.points), rng.random(a.points)
flip = u + v_ > 1
u[flip], v_[flip] = 1 - u[flip], 1 - v_[flip]
pts = p0[idx] + (p1[idx] - p0[idx]) * u[:, None] + (p2[idx] - p0[idx]) * v_[:, None]

target = np.array([0.0, 0.0, 0.5 * (bmin[2] + bmax[2])])
phi = (1 + 5 ** 0.5) / 2
smin, smax = math.sin(math.radians(a.elev_min)), math.sin(math.radians(a.elev_max))
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = a.lens
cam_data.sensor_width = 36.0
cam_data.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
fx = a.lens / 36.0 * a.size

views = []
for i in range(a.views):
    s = smin + (smax - smin) * (i + 0.5) / a.views     # 仰角のsinを等間隔(球面上の面積均等)
    el = math.asin(s)
    az = (2 * math.pi * i / phi) % (2 * math.pi)
    pos = target + a.radius * np.array([math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)])
    cam.location = mathutils.Vector(pos)
    d = mathutils.Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    name = f"{i:04d}.png"
    scene.render.filepath = os.path.join(out, "images", name)
    bpy.ops.render.render(write_still=True)
    c2w = np.array(cam.matrix_world)
    views.append({"name": name, "c2w_blender": c2w.tolist(), "azimuth_deg": math.degrees(az), "elevation_deg": math.degrees(el)})
    if i % 24 == 0:
        print("T7 rendered", i, "/", a.views)


def rotmat_to_quat(m):
    t = np.trace(m)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [(m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s]
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s]
    return np.array(q) / np.linalg.norm(q)


sp0 = os.path.join(out, "sparse", "0")
with open(os.path.join(sp0, "cameras.txt"), "w") as f:
    f.write("# Camera list with one line of data per camera:\n# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
    f.write(f"1 PINHOLE {a.size} {a.size} {fx:.6f} {fx:.6f} {a.size / 2:.6f} {a.size / 2:.6f}\n")
with open(os.path.join(sp0, "images.txt"), "w") as f:
    f.write("# Image list with two lines of data per image:\n#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
    flipyz = np.diag([1.0, -1.0, -1.0])
    for i, vw in enumerate(views):
        c2w = np.array(vw["c2w_blender"])
        Rw2c = (c2w[:3, :3] @ flipyz).T
        t = -Rw2c @ c2w[:3, 3]
        q = rotmat_to_quat(Rw2c)
        f.write(f"{i + 1} {q[0]:.9f} {q[1]:.9f} {q[2]:.9f} {q[3]:.9f} {t[0]:.9f} {t[1]:.9f} {t[2]:.9f} 1 {vw['name']}\n\n")
gray = 128
with open(os.path.join(sp0, "points3D.txt"), "w") as f:
    f.write("# 3D point list with one line of data per point:\n#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
    for i, p in enumerate(pts):
        f.write(f"{i + 1} {p[0]:.6f} {p[1]:.6f} {p[2]:.6f} {gray} {gray} {gray} 0.5\n")
with open(os.path.join(sp0, "points3D.ply"), "wb") as f:
    header = ("ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\n"
              "property float nx\nproperty float ny\nproperty float nz\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n" % len(pts))
    f.write(header.encode())
    rec = np.zeros(len(pts), dtype=[("p", "<f4", 3), ("n", "<f4", 3), ("c", "u1", 3)])
    rec["p"] = pts
    rec["c"] = gray
    f.write(rec.tobytes())
with open(os.path.join(out, "views.json"), "w") as f:
    json.dump({"size": a.size, "fx": fx, "lens": a.lens, "radius": a.radius, "light": a.light, "target": target.tolist(), "views": views}, f)
with open(os.path.join(out, "char_info.json"), "w") as f:
    json.dump({"bbox_min": bmin.tolist(), "bbox_max": bmax.tolist(), "tris": int(len(tris))}, f)
print("T7 done", out)
