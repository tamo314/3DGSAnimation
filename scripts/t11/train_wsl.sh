#!/bin/bash
# T11: NeRF-synthetic形式データで素の3DGS(G-Styleリポジトリの train_original.py、無改変)を学習する。
# 使い方: train_wsl.sh <データ名(experiments/T11/data/下)> <出力名> <sh_degree> <iterations> [追加のtrain引数...]
source /mnt/c/Work/3DGSAnimation-T11/scripts/wsl/env_t7.sh
export PYTHONPATH=$HOME/work/t11/shim:$PYTHONPATH
data=$1; name=$2; sh=$3; it=$4; shift 4
mkdir -p ~/work/t11/data ~/work/t11/out
rm -rf ~/work/t11/data/$data; cp -r /mnt/c/Work/3DGSAnimation-T11/experiments/T11/data/$data ~/work/t11/data/$data
cd ~/ext/g-style
out=~/work/t11/out/$name; START=$(date +%s)
~/venvs/gstyle/bin/python train_original.py -s ~/work/t11/data/$data -m $out --resolution 1 --sh_degree $sh --data_device cpu --white_background \
  --iterations $it --test_iterations $it --save_iterations $it "$@" > ~/work/t11/out/$name.log 2>&1
echo "TRAIN_SECONDS $(( $(date +%s) - START ))" | tee -a ~/work/t11/out/$name.log
ls $out/point_cloud/*/
