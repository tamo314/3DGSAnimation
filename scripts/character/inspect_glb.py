"""GLBを読み込み、サイズ・メッシュ統計を出力し、多方向のレンダリングを保存する（Blender内で実行）。

blender -b --python scripts/character/inspect_glb.py -- <model.glb> <out_dir>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

glb, out = sys.argv[sys.argv.index("--") + 1 :][:2]
out = Path(out).resolve()
out.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
lo = Vector((1e9,) * 3)
hi = Vector((-1e9,) * 3)
tris = 0
for o in meshes:
    tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w))
        hi = Vector(map(max, hi, w))
info = {
    "objects": [(o.name, o.type) for o in bpy.context.scene.objects],
    "mesh_count": len(meshes),
    "triangles": tris,
    "bbox_min": list(lo),
    "bbox_max": list(hi),
    "size": list(hi - lo),
    "materials": [m.name for m in bpy.data.materials],
    "images": [(i.name, list(i.size)) for i in bpy.data.images],
}
(out / "info.json").write_text(json.dumps(info, indent=2))
print(json.dumps(info, indent=2))

# 検査用レンダ: 8方向 + 顔アップ（Eevee）
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = sc.render.resolution_y = 900
sc.render.film_transparent = False
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.57, 0.62, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"

center = (lo + hi) / 2
h = hi.z - lo.z
up = "Z"
# glTFインポート後はBlender座標（Z up, -Y が前方）。高さがZにならない場合に備えて確認
if (hi.y - lo.y) > h * 1.2:
    print("WARNING: Y extent larger than Z; model may not be Z-up")


def shot(name, az_deg, el_deg=5, scale=None, target=None):
    t = target or center
    d = 10
    az, el = math.radians(az_deg), math.radians(el_deg)
    cam.location = t + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * d
    direction = t - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = scale or h * 1.15
    sc.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)


for az in range(0, 360, 45):
    shot(f"view_az{az:03d}", az)
head = Vector((center.x, center.y, hi.z - h * 0.13))
shot("face_front", 0, 0, h * 0.28, head)
shot("face_back", 180, 0, h * 0.28, head)
