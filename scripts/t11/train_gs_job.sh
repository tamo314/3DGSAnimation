#!/bin/bash
# T11: データを~/work/t11/dataにコピーして gs_train.py を実行し、結果を experiments/T11/runs/<name> に戻す。
# 使い方: train_gs_job.sh <データ名> <run名> [gs_train.pyの追加引数...]
data=$1; name=$2; shift 2
mkdir -p ~/work/t11/data ~/work/t11/out; rm -rf ~/work/t11/data/$data; cp -r /mnt/c/Work/3DGSAnimation-T11/experiments/T11/data/$data ~/work/t11/data/$data
bash /mnt/c/Work/3DGSAnimation-T11/scripts/t11/gs_wsl.sh gs_train.py --data ~/work/t11/data/$data --out ~/work/t11/out/$name "$@" > ~/work/t11/out/$name.log 2>&1
mkdir -p /mnt/c/Work/3DGSAnimation-T11/experiments/T11/runs; rm -rf /mnt/c/Work/3DGSAnimation-T11/experiments/T11/runs/$name
cp -r ~/work/t11/out/$name /mnt/c/Work/3DGSAnimation-T11/experiments/T11/runs/$name; cp ~/work/t11/out/$name.log /mnt/c/Work/3DGSAnimation-T11/experiments/T11/runs/$name/train.log
tail -25 ~/work/t11/out/$name.log
