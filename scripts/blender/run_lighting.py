"""T5b/T6: 統合シーンにライティングを適用して5視点を描画する(ヘッドレス)。
  blender --factory-startup -b --python scripts/blender/run_lighting.py -- --out experiments/T5/out --tag e1_ [--cams front_wide,...] [--shadows ...]
BLENDER_USER_EXTENSIONS に専用拡張フォルダを指すこと(run_lighting.ps1 が設定する)。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402

import build_integration as bi  # noqa: E402
import build_lit_scene as bls  # noqa: E402
import lighting  # noqa: E402
import spike_common as sc  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(bi.REPO, "experiments", "T5", "out"))
ap.add_argument("--tag", default="")
ap.add_argument("--cams", default=None, help="カンマ区切り。省略で5視点すべて")
ap.add_argument("--config", default=None)
ap.add_argument("--set", action="append", default=[], help="KIRIプロパティ name=value (例 r2_shadows=1)")
ap.add_argument("--hook", default=None, help="追加の設定を行うpythonファイル(build後に exec)")
ap.add_argument("--blend", default=None)
ap.add_argument("--no-bake", action="store_true")
ap.add_argument("--no-gobo", action="store_true")
ap.add_argument("--gobo-floor", type=float, default=None)
ap.add_argument("--force-bake", action="store_true")
ap.add_argument("--cull", type=float, default=None, help="キャラ内側/表面から N m 以内の背景スプラットを消す")
ap.add_argument("--samples", type=int, default=64)
a = ap.parse_args(argv)

cfg = lighting.load_config(a.config)
info = bls.build(cfg, bake=not a.no_bake, gobo=not a.no_gobo, gobo_floor=a.gobo_floor, bake_kw={"force": a.force_bake, **({"cull_margin": a.cull} if a.cull is not None else {})}, samples=a.samples)
print("T5 built", info)
sp = sc.kiri_props()
sun = bpy.data.objects["sun"]
for kv in a.set:
    k, v = kv.split("=", 1)
    cur = getattr(sp, k)
    if isinstance(cur, bool):
        val = v not in ("0", "false", "False")
    elif isinstance(cur, int):
        val = int(v)
    elif isinstance(cur, float):
        val = float(v)
    else:
        val = None if v == "None" else v
    setattr(sp, k, val)
    print("T5 set", k, val)
if a.hook:
    exec(compile(open(a.hook, encoding="utf-8").read(), a.hook, "exec"), {"bpy": bpy, "bi": bi, "sc": sc, "sp": sp, "sun": sun, "cfg": cfg})
if a.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
names = a.cams.split(",") if a.cams else None
print("T5 render", bi.render_all(os.path.abspath(a.out), names=names, tag=a.tag))
