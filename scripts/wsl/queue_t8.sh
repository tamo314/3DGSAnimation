#!/bin/bash
# T8: 学習→評価をGPUを占有しすぎないよう順番に実行する
S=/mnt/c/Work/3DGSAnimation-T8/scripts/wsl
bash $S/run_t8_train.sh ring1024 B_ring1024_sh0 0 && bash $S/run_t8_eval.sh B_ring1024_sh0 0 1.0 --save 3 > ~/work/t8/out/B_eval.log 2>&1
bash $S/run_t8_train.sh hq2048 D_hq2048_sh0 0 && bash $S/run_t8_eval.sh D_hq2048_sh0 0 1.0 --save 3 > ~/work/t8/out/D_eval.log 2>&1
bash $S/run_t8_train.sh hq2048 E_hq2048_sh3_dense 3 --densify_grad_threshold 0.0001 && bash $S/run_t8_eval.sh E_hq2048_sh3_dense 3 1.0 --save 3 > ~/work/t8/out/E_eval.log 2>&1
echo QUEUE_DONE
