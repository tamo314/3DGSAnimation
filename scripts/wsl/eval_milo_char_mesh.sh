#!/bin/bash
# MILoがキャラから抽出したメッシュを、Tripoの正解メッシュと比較する(Chamfer)
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
cd /mnt/c/Work/3DGSAnimation-T7
run python scripts/gaussian/eval_mesh_chamfer.py --glb /mnt/c/Work/3DGSAnimation/assets/generated/character/normalized/girl_healer.glb --mesh experiments/T7/runs/milo_char/mesh.ply 2>&1 | tail -6
