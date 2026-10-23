#!/bin/bash
# T11: 部位アップの連鎖。 使い方: zoomchain_run.sh <顔アップのフォルダ(face_az+NNN.png)> <出力フォルダ> <起点の部位アップ(az0)> <±1> <刻み> <最後の方位> <倍率> "<範囲>"
faces=$1; out=$2; start=$3; dir=$4; step=$5; last=$6; z=$7; region=$8
mkdir -p "$out"; prev=$start; az=0
while true; do
  az=$((az + dir * step)); [ ${az#-} -gt $last ] && break
  f=$(printf "%s/face_az%+04d.png" "$faces" $az); o=$(printf "%s/zoom_az%+04d.png" "$out" $az)
  bash "$(dirname "$0")/gen_codex_zoomchain.sh" "$f" "$prev" "$o" "$z" "$region" || true
  if [ ! -s "$o" ]; then bash "$(dirname "$0")/gen_codex_zoomchain.sh" "$f" "$prev" "$o" "$z" "$region"; fi
  if [ ! -s "$o" ]; then echo "FAILED at $az"; exit 1; fi
  prev=$o
done
echo "chain $dir done"
