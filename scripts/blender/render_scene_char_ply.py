"""T7: T5 の統合シーン(焼き込み背景)で、キャラのメッシュの代わりに「キャラの3DGS(PLY)」を置いて5視点を描画する(ヘッドレス)。
参照研究(MILo / G-Style / GaussianShader …)の出力を、実際の見た目で T5(メッシュ描画)と比べるための評価用。
  blender --factory-startup -b --python scripts/blender/render_scene_char_ply.py -- --char-ply <PLY> --out <dir> --tag m_ [--cams a,b] [--sh 3] [--keep-mesh]
キャラPLYは render_char_dataset.py の世界座標(足元原点・前方 -Y・Z上)。統合シーンの CHAR_POS / CHAR_GROUND_Z に置く。
"""
import argparse
import math
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
ap.add_argument("--char-ply", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--tag", default="")
ap.add_argument("--cams", default=None)
ap.add_argument("--sh", type=int, default=3, help="キャラPLYのSH次数(背景は0)")
ap.add_argument("--keep-mesh", action="store_true", help="キャラのメッシュも描く(深度合成の確認用)")
ap.add_argument("--no-gobo", action="store_true", default=True)
ap.add_argument("--samples", type=int, default=64)
a = ap.parse_args(argv)

cfg = lighting.load_config()
info = bls.build(cfg, bake=True, gobo=False, samples=a.samples)
if not a.keep_mesh:
    for ob in bpy.data.objects:
        if ob.type in ("MESH", "EMPTY") and (ob.name == "character" or (ob.parent and ob.parent.name == "character")):
            ob.hide_render = True
            ob.hide_viewport = True
ch = sc.kiri_import_ply(a.char_ply, "char_gs")
ch.location = (bi.CHAR_POS[0], bi.CHAR_POS[1], bi.CHAR_GROUND_Z)
ch.rotation_euler = (0, 0, math.radians(bi.CHAR_YAW_DEG))
sc.kiri_make_proxy(ch)
ch.hide_set(True)
ch.hide_render = True
sp = sc.kiri_props()
sp.active_mode = "Render"
sp.r2_relight = False
names = a.cams.split(",") if a.cams else None
print("T7 render", bi.render_all(os.path.abspath(a.out), names=names, tag=a.tag, comp=True))
