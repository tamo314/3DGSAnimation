#!/bin/bash
# T8: 出力側の超解像(3DGSの描画をSRで2倍)を評価するための、4096²の正解(元テクスチャ)。評価視点のうち 顔(12)・拡大の顔(12)・寄り(5) だけを描く。
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Work/3DGSAnimation-T8
export BLENDER_USER_EXTENSIONS="$LOCALAPPDATA/3DGSAnimation/blender-ext"
"$B" --factory-startup -b --python scripts/blender/render_hq_master.py -- --out experiments/T8/master4k --size 4096 --only-test --only-types face
"$B" --factory-startup -b --python scripts/blender/render_hq_master.py -- --out experiments/T8/master4k_zoom --size 4096 --preset zoom --only-types zoomface
"$B" --factory-startup -b --python scripts/blender/render_hq_master.py -- --out experiments/T8/master4k_close --size 4096 --preset close --only-test
echo GT4K_DONE
