#!/bin/bash
# T8: 高精細多視点データで素の3DGS(G-Styleリポジトリの train_original.py。公式コード無改変)を学習する。
# 使い方: run_t8_train.sh <データ名(experiments/T8/data/下)> <出力名> <sh_degree> [追加のtrain引数...]
source /mnt/c/Work/3DGSAnimation-T8/scripts/wsl/env_t7.sh 2>/dev/null || source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
data=$1; name=$2; sh=$3; shift 3
mkdir -p ~/work/t8/data ~/work/t8/out
[ -d ~/work/t8/data/$data ] || cp -r /mnt/c/Work/3DGSAnimation-T8/experiments/T8/data/$data ~/work/t8/data/$data
cd ~/ext/g-style
out=~/work/t8/out/$name
START=$(date +%s)
~/venvs/gstyle/bin/python train_original.py -s ~/work/t8/data/$data -m $out --resolution 1 --sh_degree $sh --data_device cpu \
  --test_iterations 30000 --save_iterations 7000 30000 "$@" > ~/work/t8/out/$name.log 2>&1
echo "TRAIN_SECONDS $(( $(date +%s) - START ))" | tee -a ~/work/t8/out/$name.log
ls -la $out/point_cloud/iteration_30000/
