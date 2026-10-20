#!/bin/bash
# T8: 出力側の超解像の評価。使い方: osr_pipeline.sh <出力名(~/work/t8/out下)> <SH> <タグ>
# (1)3DGSを2048と4096で描く (2)2048描画をSRで2倍(Real-ESRGAN anime 6B)・bicubicで2倍 (3)4096の正解と比較
n=$1; sh=$2; tag=$3
R=/mnt/c/Work/3DGSAnimation-T8; E=$R/experiments/T8; W=$HOME/work/t8/sr/weights/RealESRGAN_x4plus_anime_6B.pth
ply=$HOME/work/t8/out/$n/point_cloud/iteration_30000/point_cloud.ply
O=$HOME/work/t8/osr/$tag; rm -rf $O; mkdir -p $O
export PYTHONPATH=$HOME/ext/g-style
declare -A M=( [face]="$E/master face test" [zoomface]="$E/master_zoom zoomface all" [close]="$E/master_close close test" )
for k in face zoomface close; do
  set -- ${M[$k]}
  $HOME/venvs/gstyle/bin/python $R/scripts/wsl/render_views.py --ply $ply --master $1 --types $2 --split $3 --scales 1,2 --sh $sh --out $O/$k > /dev/null 2>&1
  $HOME/venvs/sr/bin/python $R/scripts/wsl/sr_images.py --weights $W --src $O/$k/s1 --out $O/$k/sr2x > /dev/null 2>&1
  $HOME/venvs/gstyle/bin/python - <<PY
import os
from PIL import Image
s="$O/$k/s1"; d="$O/$k/bicubic2x"; os.makedirs(d, exist_ok=True)
for f in os.listdir(s):
    im = Image.open(os.path.join(s, f)); im.resize((im.width * 2, im.height * 2), Image.BICUBIC).save(os.path.join(d, f))
PY
done
# 比較(正解は3つのフォルダ。同名ファイルは視点ごとに別フォルダにまとめて渡す)
for lab in bicubic2x sr2x s2; do
  mkdir -p $O/all/$lab
  for k in face zoomface close; do cp $O/$k/$lab/*.png $O/all/$lab/ 2>/dev/null; done
done
mkdir -p $O/gt/images; for d in master4k master4k_zoom master4k_close; do cp $E/$d/images/*.png $O/gt/images/ 2>/dev/null; done
$HOME/venvs/gstyle/bin/python $R/scripts/wsl/compare_sr.py --gt $O/gt --dirs bicubic2x=$O/all/bicubic2x sr2x=$O/all/sr2x native4096=$O/all/s2 --out $O/summary.json
echo OSR_DONE $tag
