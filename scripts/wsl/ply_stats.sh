#!/bin/bash
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
cd /mnt/c/Work/3DGSAnimation-T7
run python scripts/gaussian/ply_stats.py "$@"
