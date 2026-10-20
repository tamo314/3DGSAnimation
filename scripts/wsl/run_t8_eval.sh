#!/bin/bash
# T8: 学習済みPLYを評価視点で評価する。使い方: [MASTER=master|master_zoom|master_lower] run_t8_eval.sh <出力名またはPLY> <sh_degree> <scale> [追加のeval_gs引数...]
# 結果: ~/work/t8/eval/<出力名>_<MASTER>_s<scale>/
name=$1; sh=$2; scale=$3; shift 3
M=${MASTER:-master}
ply=~/work/t8/out/$name/point_cloud/iteration_30000/point_cloud.ply
[ -f $ply ] || ply=$name
tag=$(basename $(dirname $(dirname $(dirname $ply))))
PYTHONPATH=~/ext/g-style ~/venvs/gstyle/bin/python /mnt/c/Work/3DGSAnimation-T8/scripts/wsl/eval_gs.py --ply $ply \
  --master /mnt/c/Work/3DGSAnimation-T8/experiments/T8/$M --out ~/work/t8/eval/${tag}_${M}_s$scale --sh $sh --scale $scale "$@"
