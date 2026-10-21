#!/bin/bash
# 使い方: render_wsl.sh <出力名> <iteration> <出力フォルダ名> <render_ply.pyの追加引数...>
source /mnt/c/Work/3DGSAnimation-T11/scripts/wsl/env_t7.sh
name=$1; it=$2; od=$3; shift 3
cd ~/ext/g-style
PYTHONPATH=~/ext/g-style:~/work/t11/shim ~/venvs/gstyle/bin/python /mnt/c/Work/3DGSAnimation-T11/scripts/t11/render_ply.py --ply ~/work/t11/out/$name/point_cloud/iteration_$it/point_cloud.ply --out ~/work/t11/render/$od "$@"
