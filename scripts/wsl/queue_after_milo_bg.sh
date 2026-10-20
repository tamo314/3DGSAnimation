#!/bin/bash
while ! grep -q MILO_DONE /mnt/c/Work/3DGSAnimation-T7/experiments/T7/data/milo_bg.log; do sleep 30; done
bash /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/run_frosting_char.sh
