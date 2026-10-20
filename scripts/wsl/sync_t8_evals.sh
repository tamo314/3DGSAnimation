#!/bin/bash
# WSL内の評価結果(metrics.jsonと画像)を Windows 側 experiments/T8/evals/ に同期する
dst=/mnt/c/Work/3DGSAnimation-T8/experiments/T8/evals
mkdir -p $dst
for d in $HOME/work/t8/eval/*; do
  n=$(basename $d)
  mkdir -p $dst/$n
  cp $d/* $dst/$n/
done
ls $dst
