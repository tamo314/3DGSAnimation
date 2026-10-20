#!/bin/bash
# MILo背景メッシュの地面・連結成分を測る
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
cd /mnt/c/Work/3DGSAnimation-T7
run python scripts/gaussian/eval_bg_mesh.py --mesh experiments/T7/runs/milo_bg/mesh.ply --collider /mnt/c/Work/3DGSAnimation/assets/generated/background/forest_clearing_collider.glb --out experiments/T7/runs/milo_bg/mesh_eval.json 2>&1 | tail -8
