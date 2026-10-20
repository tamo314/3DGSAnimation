"""T7: 背景3DGS(World Labs forest_clearing, full_res)をKIRIで多視点に描画し、COLMAPテキスト形式のデータセットを作る(ヘッドレス)。
背景の元写真(多視点)はないので、生成物の3DGSを描画し直した画像を「教師画像」とする(自己蒸留)。MILo で面(メッシュ)・法線の取れる3DGSにするための入力。
カメラは元カメラ(0,-3.5,視点高)の周りの自由空間(T4/T5 で破綻なく描画できた範囲)で、パノラマ側(+Y方向)を向くよう乱数で散らす。
  blender --factory-startup -b --python scripts/blender/render_bg_dataset.py -- --out experiments/T7/data/bg_scene --views 160 --width 1024 --height 768
出力: images/*.png(RGB)、sparse/0/{cameras,images,points3D}.txt、points3D.ply、views.json
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lighting"))
import bpy  # noqa: E402
import mathutils  # noqa: E402
import numpy as np  # noqa: E402

import build_integration as bi  # noqa: E402
import spike_common as sc  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--views", type=int, default=160)
ap.add_argument("--width", type=int, default=1024)
ap.add_argument("--height", type=int, default=768)
ap.add_argument("--lens", type=float, default=25.0)
ap.add_argument("--points", type=int, default=300000)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--box", default="-2.0,2.0,-5.0,-1.5,0.4,2.6", help="カメラ位置の範囲 xmin,xmax,ymin,ymax,zmin,zmax")
ap.add_argument("--yaw", type=float, default=55.0, help="+Y方向からの左右の振れ(±deg)")
ap.add_argument("--pitch", default="-15,25")
a = ap.parse_args(argv)

out = os.path.abspath(a.out)
os.makedirs(os.path.join(out, "images"), exist_ok=True)
os.makedirs(os.path.join(out, "sparse", "0"), exist_ok=True)

sc.init_gpu()
sc.enable_kiri()
sc.clear_scene()
sc.set_render(a.width, a.height)
bpy.context.scene.render.film_transparent = False
bg = bi.import_background()
sp = sc.kiri_props()
sp.active_mode = "Render"
sp.r2_relight = False

rng = np.random.default_rng(a.seed)
bx = [float(x) for x in a.box.split(",")]
p0, p1 = [float(x) for x in a.pitch.split(",")]
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = a.lens
cam_data.sensor_width = 36.0
cam_data.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
fx = a.lens / 36.0 * a.width

views = []
for i in range(a.views):
    pos = np.array([rng.uniform(bx[0], bx[1]), rng.uniform(bx[2], bx[3]), rng.uniform(bx[4], bx[5])])
    yaw = math.radians(rng.uniform(-a.yaw, a.yaw))
    pitch = math.radians(rng.uniform(p0, p1))
    d = np.array([math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
    cam.location = mathutils.Vector(pos)
    cam.rotation_euler = mathutils.Vector(d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    name = f"{i:04d}.png"
    base = os.path.join(out, "images", f"{i:04d}_")
    sc.kiri_render(base, comp=False, sh_degree=bi.KIRI_SH)
    # KIRIは <base>*.png を出力する。名前を揃える
    produced = [f for f in os.listdir(os.path.join(out, "images")) if f.startswith(f"{i:04d}_")]
    if produced:
        os.replace(os.path.join(out, "images", produced[0]), os.path.join(out, "images", name))
    views.append({"name": name, "c2w_blender": np.array(cam.matrix_world).tolist()})
    if i % 20 == 0:
        print("T7 rendered", i, "/", a.views, produced)


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


# 初期点群: 背景スプラットの中心(不透明なもの)から抽出(世界座標)
import load_bg  # noqa: E402

w, alpha, rgb, _ = load_bg.load("full_res")
sel = np.where(alpha > 0.5)[0]
sel = rng.choice(sel, size=min(a.points, len(sel)), replace=False)
pts, cols = w[sel], (rgb[sel] * 255).astype(np.uint8)

sp0 = os.path.join(out, "sparse", "0")
with open(os.path.join(sp0, "cameras.txt"), "w") as f:
    f.write("# Camera list with one line of data per camera:\n# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
    f.write(f"1 PINHOLE {a.width} {a.height} {fx:.6f} {fx:.6f} {a.width / 2:.6f} {a.height / 2:.6f}\n")
with open(os.path.join(sp0, "images.txt"), "w") as f:
    f.write("# Image list with two lines of data per image:\n#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
    flipyz = np.diag([1.0, -1.0, -1.0])
    for i, vw in enumerate(views):
        c2w = np.array(vw["c2w_blender"])
        Rw2c = (c2w[:3, :3] @ flipyz).T
        t = -Rw2c @ c2w[:3, 3]
        q = rotmat_to_quat(Rw2c)
        f.write(f"{i + 1} {q[0]:.9f} {q[1]:.9f} {q[2]:.9f} {q[3]:.9f} {t[0]:.9f} {t[1]:.9f} {t[2]:.9f} 1 {vw['name']}\n\n")
with open(os.path.join(sp0, "points3D.txt"), "w") as f:
    f.write("# 3D point list with one line of data per point:\n#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
    for i, (p, c) in enumerate(zip(pts, cols)):
        f.write(f"{i + 1} {p[0]:.6f} {p[1]:.6f} {p[2]:.6f} {c[0]} {c[1]} {c[2]} 0.5\n")
with open(os.path.join(sp0, "points3D.ply"), "wb") as f:
    header = ("ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\n"
              "property float nx\nproperty float ny\nproperty float nz\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n" % len(pts))
    f.write(header.encode())
    rec = np.zeros(len(pts), dtype=[("p", "<f4", 3), ("n", "<f4", 3), ("c", "u1", 3)])
    rec["p"] = pts
    rec["c"] = cols
    f.write(rec.tobytes())
with open(os.path.join(out, "views.json"), "w") as f:
    json.dump({"width": a.width, "height": a.height, "fx": fx, "lens": a.lens, "views": views}, f)
print("T7 done", out)
