#!/bin/bash
# Frostingの実行(train_full_pipeline.py または frosting_shim.py)が終わるまで最大9分待ち、進捗を表示する
for i in $(seq 1 54); do
  if ! pgrep -f "train_full_pipeline|frosting_shim" >/dev/null; then echo FINISHED; break; fi
  sleep 10
done
date
find ~/ext/Frosting/output -newer /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/frosting_shim.py -type f | head
LOG=${1:-/mnt/c/Work/3DGSAnimation-T7/experiments/T7/data/frosting_char2.log}
tr '\r' '\n' < "$LOG" | tail -2 | cut -c1-200
