#!/bin/bash
# T8(超解像): 1つのモデルを、対応するテクスチャの正解(SFX="" なら元テクスチャ、"_sr8k" なら超解像テクスチャ)で評価する。
# 使い方: eval_t8_sr.sh <出力名> <sh_degree> <SFX>
S=/mnt/c/Work/3DGSAnimation-T8/scripts/wsl
n=$1; sh=$2; sfx=$3
MASTER=master$sfx bash $S/run_t8_eval.sh $n $sh 1.0 --save 3 > /dev/null 2>&1
MASTER=master${sfx}_zoom bash $S/run_t8_eval.sh $n $sh 1.0 --types zoomface,zoomupper --save 3 > /dev/null 2>&1
MASTER=master${sfx}_lower bash $S/run_t8_eval.sh $n $sh 1.0 --types lower --save 3 > /dev/null 2>&1
MASTER=master_close$sfx bash $S/run_t8_eval.sh $n $sh 1.0 --types close --save 4 > /dev/null 2>&1
echo EVAL_SR_DONE $n
