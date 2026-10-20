#!/bin/bash
# T8: Eの後に、ガウシアン数(予算)とSHの影響を分けて見る追加2本。F=疎(grad閾値0.0005, SH0)、G=SH3のみ(既定密度)
S=/mnt/c/Work/3DGSAnimation-T8/scripts/wsl
while ! grep -q QUEUE_DONE /mnt/c/Work/3DGSAnimation-T8/experiments/T8/queue.log 2>/dev/null; do sleep 30; done
bash $S/run_t8_train.sh hq2048 F_hq2048_sh0_sparse 0 --densify_grad_threshold 0.0005 && bash $S/eval_t8_all.sh F_hq2048_sh0_sparse 0
bash $S/run_t8_train.sh hq2048 G_hq2048_sh3 3 && bash $S/eval_t8_all.sh G_hq2048_sh3 3
echo QUEUE_B_DONE
