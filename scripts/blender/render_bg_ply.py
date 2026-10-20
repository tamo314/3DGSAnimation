"""T7: 背景3DGSのPLYを、統合シーンの5視点カメラで描画する(ヘッドレス。キャラなし)。元の背景と、MILoで学習し直した背景を同じ条件で比べるため。
  blender --factory-startup -b --python scripts/blender/render_bg_ply.py -- --out <dir> --tag m_ --bg-ply <MILo PLY> [--sh 3] [--cams a,b]
  blender ... -- --out <dir> --tag o_ --orig          (元の背景)
MILoのPLYは学習データ(Blenderの世界座標)と同じ座標系なので、変換なしで置く。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402

import build_integration as bi  # noqa: E402
import spike_common as sc  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--tag", default="")
ap.add_argument("--bg-ply", default=None)
ap.add_argument("--orig", action="store_true")
ap.add_argument("--sh", type=int, default=0)
ap.add_argument("--cams", default=None)
a = ap.parse_args(argv)

sc.init_gpu()
sc.enable_kiri()
sc.clear_scene()
sc.set_render(*bi.RENDER_SIZE)
if a.orig:
    bi.import_background()
else:
    ob = sc.kiri_import_ply(a.bg_ply, "background_milo")
    sc.kiri_make_proxy(ob)
    ob.hide_set(True)
    ob.hide_render = True
cams, _ = bi.make_cameras()
sp = sc.kiri_props()
sp.active_mode = "Render"
sp.r2_relight = False
names = a.cams.split(",") if a.cams else None
out = os.path.abspath(a.out)
os.makedirs(out, exist_ok=True)
for name, cam in cams.items():
    if names and name not in names:
        continue
    bpy.context.scene.camera = cam
    sc.kiri_render(os.path.join(out, f"{a.tag}{name}_"), comp=False, sh_degree=(bi.KIRI_SH if a.orig else a.sh))
print("T7 render bg", out)
