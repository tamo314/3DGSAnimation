#!/bin/bash
# T11: 部位アップ(寄り画像)を、起点(方位0)→10°刻みの連鎖(±60°)→5°刻みの補間 の順に作る。
# 使い方: zoom_region_pipeline.sh <顔アップのフォルダ> <出力フォルダ> <倍率> "<範囲(英語)>"
faces=$1; O=$2; z=$3; R=$4; mkdir -p "$O"; S="$(dirname "$0")"
bash $S/gen_codex_zoom.sh $faces/face_az+000.png $O/zoom_az+000.png $z "$R"
bash $S/zoomchain_run.sh $faces $O $O/zoom_az+000.png +1 10 60 $z "$R" > $O/runA.out 2>&1 &
bash $S/zoomchain_run.sh $faces $O $O/zoom_az+000.png -1 10 60 $z "$R" > $O/runB.out 2>&1 &
wait
Z() { printf "%s/zoom_az%+04d.png" $O $1; }
gen() { a=$1; b=$2; m=$3; bash $S/gen_codex_zoommid.sh $(Z $a) $a $(Z $b) $b $(Z $m) $m || true; [ -s $(Z $m) ] || bash $S/gen_codex_zoommid.sh $(Z $a) $a $(Z $b) $b $(Z $m) $m; }
(gen 10 20 15 & gen 20 30 25 & gen 30 40 35 & gen 40 50 45 & gen 50 60 55 & gen -20 -10 -15 & gen -30 -20 -25 & gen -40 -30 -35 & gen -50 -40 -45 & gen -60 -50 -55 & wait)
(gen 0 10 5 & gen -10 0 -5 & wait)
echo pipeline done
