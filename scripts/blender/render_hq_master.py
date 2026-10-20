"""T8: キャラを高品質(Cycles)・高解像度で多視点描画する「マスター」データを作る(ヘッドレス、再開可能)。
  blender --factory-startup -b --python scripts/blender/render_hq_master.py -- --out experiments/T8/master --size 2048
視点は種類別(ring=全身 / upper=上半身 / face=顔のアップ / lower=腰から下)。全体を通し番号 k とし、k%8==0 を評価用(test)にする。
出力: images/<k:04d>_<type>.png (RGBA, 直線アルファ)、views.json(カメラ・種類・split)、points3D.ply(表面サンプル)
座標は T7 と同じ(Blender世界座標、足元原点、前方 -Y)。照明は T5 の太陽+空+照り返し(lighting_config.json)。
"""
import argparse
import json
import math
import os
import sys
import time

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
ap.add_argument("--size", type=int, default=2048)
ap.add_argument("--engine", default="CYCLES", choices=["CYCLES", "BLENDER_EEVEE"])
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--filter", type=float, default=1.0, help="ピクセルフィルタ幅(Blender既定1.5。小さいほど鮮明)")
ap.add_argument("--lens", type=float, default=50.0)
ap.add_argument("--limit", type=int, default=0, help="先頭からこの枚数だけ描く(0=全部)")
ap.add_argument("--glb", default=None)
ap.add_argument("--types-json", default=None, help='種類定義を上書き: [["name", n, r, z, el_min, el_max], ...]')
ap.add_argument("--all-test", action="store_true", help="全視点をtestにする(学習に使わない拡大評価用)")
ap.add_argument("--points", type=int, default=150000)
a = ap.parse_args(argv)

# 種類ごとの視点: 距離r[m]、注視点z[m]、仰角範囲[deg]、枚数。ringだけ全周を等面積に近く覆う
TYPES = [
    ("ring", dict(n=128, r=2.1, z=0.60, el=(-15, 75))),
    ("upper", dict(n=64, r=1.2, z=0.85, el=(-10, 60))),
    ("face", dict(n=48, r=0.70, z=0.98, el=(-15, 50))),
    ("lower", dict(n=48, r=1.0, z=0.30, el=(-10, 55))),
]

if a.types_json:
    TYPES = [(n, dict(n=c, r=r, z=z, el=(e0, e1))) for n, c, r, z, e0, e1 in json.loads(a.types_json)]

out = os.path.abspath(a.out)
os.makedirs(os.path.join(out, "images"), exist_ok=True)

sc.init_gpu()
sc.clear_scene()
sc.set_render(a.size, a.size, engine=a.engine, samples=a.samples)
scene = bpy.context.scene
scene.render.film_transparent = True
scene.render.filter_size = a.filter
if a.engine == "CYCLES":
    scene.cycles.samples = a.samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type != "CPU"
    scene.cycles.device = "GPU"

glb = a.glb or r"C:/Work/3DGSAnimation/assets/generated/character/normalized/girl_healer.glb"
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
new = [o for o in bpy.data.objects if o not in before]
lighting.setup(lighting.load_config())

dg = bpy.context.evaluated_depsgraph_get()
verts, tris, off = [], [], 0
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
verts, tris = np.concatenate(verts), np.concatenate(tris)
bmin, bmax = verts.min(0), verts.max(0)
print("T8 mesh bbox", bmin, bmax, "tris", len(tris))

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = a.lens
cam_data.sensor_width = 36.0
cam_data.sensor_fit = "HORIZONTAL"
cam_data.clip_start = 0.01
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
fx = a.lens / 36.0 * a.size

# 視点列: 各種類を黄金角で並べ、全体のk番号は種類をインターリーブして(8個に1個がtestになるよう)決める
phi = (1 + 5 ** 0.5) / 2
per_type = {}
for ti, (tname, p) in enumerate(TYPES):
    smin, smax = math.sin(math.radians(p["el"][0])), math.sin(math.radians(p["el"][1]))
    lst = []
    for i in range(p["n"]):
        s = smin + (smax - smin) * (i + 0.5) / p["n"]
        el = math.asin(s)
        az = (2 * math.pi * (i / phi + 0.13 * ti)) % (2 * math.pi)
        lst.append((tname, p, az, el))
    per_type[tname] = lst
# 比率を保ったインターリーブ
order, ptr = [], {k: 0 for k in per_type}
total = sum(len(v) for v in per_type.values())
for k in range(total):
    best = min((t for t in per_type if ptr[t] < len(per_type[t])), key=lambda t: (ptr[t] + 0.5) / len(per_type[t]))
    order.append(per_type[best][ptr[best]])
    ptr[best] += 1

views = []
t0 = time.time()
for k, (tname, p, az, el) in enumerate(order):
    target = np.array([0.0, 0.0, p["z"]])
    pos = target + p["r"] * np.array([math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)])
    cam.location = mathutils.Vector(pos)
    cam.rotation_euler = (mathutils.Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    name = f"{k:04d}_{tname}.png"
    path = os.path.join(out, "images", name)
    if not os.path.exists(path) and (a.limit == 0 or k < a.limit):
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if k % 8 == 0:
            print(f"T8 rendered {k}/{total} elapsed {time.time() - t0:.0f}s", flush=True)
    views.append({"k": k, "name": name, "type": tname, "split": "test" if (a.all_test or k % 8 == 0) else "train",
                  "c2w_blender": np.array(cam.matrix_world).tolist(), "radius": p["r"],
                  "azimuth_deg": math.degrees(az), "elevation_deg": math.degrees(el)})

rng = np.random.default_rng(0)
p0, p1, p2 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
idx = rng.choice(len(tris), size=a.points, p=area / area.sum())
u, w = rng.random(a.points), rng.random(a.points)
fl = u + w > 1
u[fl], w[fl] = 1 - u[fl], 1 - w[fl]
pts = p0[idx] + (p1[idx] - p0[idx]) * u[:, None] + (p2[idx] - p0[idx]) * w[:, None]
with open(os.path.join(out, "points3D.ply"), "wb") as f:
    f.write(("ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\n"
             "property float nx\nproperty float ny\nproperty float nz\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n" % len(pts)).encode())
    rec = np.zeros(len(pts), dtype=[("p", "<f4", 3), ("n", "<f4", 3), ("c", "u1", 3)])
    rec["p"], rec["c"] = pts, 128
    f.write(rec.tobytes())
with open(os.path.join(out, "views.json"), "w") as f:
    json.dump({"size": a.size, "fx": fx, "lens": a.lens, "engine": a.engine, "samples": a.samples, "filter": a.filter,
               "bbox_min": bmin.tolist(), "bbox_max": bmax.tolist(), "tris": int(len(tris)), "views": views}, f)
print("T8 done", out, f"{time.time() - t0:.0f}s")
