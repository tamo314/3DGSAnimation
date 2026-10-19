"""TripoのGLBをシーン配置用に正規化する（Blender内で実行）。

- 前方向を -Y（Blender標準の前方）に回転（Tripo出力は +X を向いている）
- 足元の中心を原点、足裏を Z=0 に
- 身長を --height に合わせてスケール（適用済み）
- 出力: GLB と .blend

blender -b --python scripts/character/normalize_character.py -- <in.glb> <out_dir> [height_m] [name]
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
src = Path(argv[0]).resolve()
out = Path(argv[1]).resolve()
height = float(argv[2]) if len(argv) > 2 else 1.2
name = argv[3] if len(argv) > 3 else "girl_healer"
out.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
obj.name = name
obj.data.name = name
# 親Emptyなどがあれば外す（今回はメッシュ単体）
obj.parent = None
obj.rotation_mode = "XYZ"
obj.rotation_euler = Euler((0, 0, math.radians(-90)))  # +X向き → -Y向き
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

me = obj.data
zs = [v.co.z for v in me.vertices]
zmin, zmax = min(zs), max(zs)
scale = height / (zmax - zmin)
foot = [v.co for v in me.vertices if v.co.z < zmin + (zmax - zmin) * 0.03]
cx = sum(p.x for p in foot) / len(foot)
cy = sum(p.y for p in foot) / len(foot)
for v in me.vertices:
    v.co = Vector(((v.co.x - cx) * scale, (v.co.y - cy) * scale, (v.co.z - zmin) * scale))
me.update()
obj.location = (0, 0, 0)

bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
print("bbox min", [min(p[i] for p in bb) for i in range(3)], "max", [max(p[i] for p in bb) for i in range(3)])
bpy.ops.wm.save_as_mainfile(filepath=str(out / f"{name}.blend"))
bpy.ops.export_scene.gltf(filepath=str(out / f"{name}.glb"), export_format="GLB", use_selection=False)
print("saved", out)
