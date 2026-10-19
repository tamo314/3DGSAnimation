"""統合シーンをヘッドレスで組み、.blendを保存して5視点を描画する。
  blender --factory-startup -b --python scripts/blender/run_integration.py -- --out experiments/T4/headless --tag h_
BLENDER_USER_EXTENSIONS に専用拡張フォルダを指すこと(run_integration.ps1 が設定する)。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

import build_integration as bi  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(bi.REPO, "experiments", "T4", "headless"))
ap.add_argument("--tag", default="")
ap.add_argument("--scale", type=float, default=None)
ap.add_argument("--blend", default=None, help="保存する.blend(省略で <out>/integration.blend)")
a = ap.parse_args(argv)
out = os.path.abspath(a.out)
os.makedirs(out, exist_ok=True)

info = bi.build(scale=a.scale)
print("T4 built", info)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend or os.path.join(out, "integration.blend")))
print("T4 render", bi.render_all(out, tag=a.tag))
