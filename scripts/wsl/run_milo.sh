#!/bin/bash
# キャラの多視点データセットで MILo(公式・無改変)を学習し、メッシュを抽出する。引数: データ名 [追加train引数...]
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
name=${1:-char_scene_black}; shift
mkdir -p ~/work/data ~/work/out
rm -rf ~/work/data/$name; cp -r /mnt/c/Work/3DGSAnimation-T7/experiments/T7/data/$name ~/work/data/$name
cd ~/ext/MILo/milo
out=~/work/out/milo_$name
START=$(date +%s)
run python /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/milo_shim.py train.py -s ~/work/data/$name -m $out --imp_metric ${IMP:-indoor} --rasterizer radegs --log_interval 1000 "$@" 2>&1 | tail -n 400
echo "TRAIN_SECONDS $(( $(date +%s) - START ))"
run python /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/milo_shim.py mesh_extract_sdf.py -s ~/work/data/$name -m $out --rasterizer radegs 2>&1 | tail -n 60
echo "TOTAL_SECONDS $(( $(date +%s) - START ))"
echo MILO_DONE
