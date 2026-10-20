#!/bin/bash
# T8(超解像): S1=SRテクスチャ(Gと同じ視点)、G2=元テクスチャ+寄り視点、S2=SRテクスチャ+寄り視点。いずれもSH3・既定密度
S=/mnt/c/Work/3DGSAnimation-T8/scripts/wsl
bash $S/run_t8_train.sh sr_hq2048 S1_sr_hq2048_sh3 3 && bash $S/eval_t8_sr.sh S1_sr_hq2048_sh3 3 _sr8k
bash $S/run_t8_train.sh orig_hq2048_close G2_orig_close_sh3 3 && bash $S/eval_t8_sr.sh G2_orig_close_sh3 3 ""
bash $S/run_t8_train.sh sr_hq2048_close S2_sr_close_sh3 3 && bash $S/eval_t8_sr.sh S2_sr_close_sh3 3 _sr8k
# 追加: 既存のG(元テクスチャ、寄り視点なし)も寄り視点で評価
bash $S/eval_t8_sr.sh G_hq2048_sh3 3 ""
echo QUEUE_D_DONE
