#!/bin/bash
# T8: マルチスケール学習(2048/1024/512)の追加検証。Gと同じSH3・既定密度で、縮小表示のジャギー/膨らみが減るかを見る
S=/mnt/c/Work/3DGSAnimation-T8/scripts/wsl
bash $S/run_t8_train.sh hq_ms H_hq_ms_sh3 3 && bash $S/eval_t8_all.sh H_hq_ms_sh3 3
echo QUEUE_C_DONE
