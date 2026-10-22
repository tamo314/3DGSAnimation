#!/bin/bash
# T11: 連鎖生成の実行。出力フォルダに 0°の画像(face_az+000.png)を置いてから、指定方向へ順に生成する。
# 使い方: chain_run.sh <出力フォルダ> <方向(+1 か -1)> <刻み(度)> <最終方位(絶対値)>
out=$1; sgn=$2; step=$3; last=$4
prev="$out/face_az+000.png"; prevaz=0; az=$((sgn * step))
while [ $((az * sgn)) -le $last ]; do
  name=$(printf "face_az%+04d" $az)
  for try in 1 2; do
    [ -f "$out/$name.png" ] || bash "$(dirname "$0")/gen_codex_chain.sh" $az "$prev" $prevaz "$out"
    [ -f "$out/$name.png" ] && break
  done
  [ -f "$out/$name.png" ] || { echo "FAILED at $az"; exit 1; }
  prev="$out/$name.png"; prevaz=$az; az=$((az + sgn * step))
done
echo "chain $sgn done"
