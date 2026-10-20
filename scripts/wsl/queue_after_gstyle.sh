#!/bin/bash
# GPU学習は同時に1本まで。G-Style の終了を待って、背景データで MILo を流す
while ! grep -q GSTYLE_DONE /mnt/c/Work/3DGSAnimation-T7/experiments/T7/data/gstyle_char.log; do sleep 30; done
IMP=outdoor bash /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/run_milo.sh bg_scene_rgb --data_device cpu
