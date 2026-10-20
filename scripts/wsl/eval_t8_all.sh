#!/bin/bash
# T8: 1つのモデルを全評価セットで評価する。使い方: eval_t8_all.sh <出力名> <sh_degree>
S=/mnt/c/Work/3DGSAnimation-T8/scripts/wsl
n=$1; sh=$2
[ -f ~/work/t8/eval/${n}_master_s1.0/metrics.json ] || MASTER=master bash $S/run_t8_eval.sh $n $sh 1.0 --save 3 > /dev/null 2>&1
MASTER=master_zoom bash $S/run_t8_eval.sh $n $sh 1.0 --types zoomface,zoomupper --save 3 > /dev/null 2>&1
MASTER=master_lower bash $S/run_t8_eval.sh $n $sh 1.0 --types lower --save 3 > /dev/null 2>&1
MASTER=master bash $S/run_t8_eval.sh $n $sh 0.5 --save 2 > /dev/null 2>&1      # 縮小(1024²)で描いたときのジャギー・折り返し
MASTER=master bash $S/run_t8_eval.sh $n $sh 0.25 --save 2 > /dev/null 2>&1     # さらに縮小(512²)
echo EVAL_ALL_DONE $n
