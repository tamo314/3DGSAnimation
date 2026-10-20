#!/bin/bash
# MILo のCUDA拡張をビルドする(torch 2.8 / cu128 / sm_120)。公式コードは無改変。失敗はログに残す。
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
cd ~/ext/MILo
ln -sfn $CUDA_HOME/targets/x86_64-linux/lib $CUDA_HOME/lib64 2>/dev/null
for m in diff-gaussian-rasterization_ms diff-gaussian-rasterization diff-gaussian-rasterization_gof simple-knn fused-ssim; do
  echo "=== build $m"
  run pip install --no-build-isolation submodules/$m 2>&1 | grep -E "error|Error|Successfully" | head -8
done
echo "=== build tetra_triangulation"
cd submodules/tetra_triangulation
run cmake . 2>&1 | tail -3
run make -j8 2>&1 | grep -E "error|Error|Built target|\*\*\*" | head
run pip install --no-build-isolation -e . 2>&1 | grep -E "error|Successfully"
echo BUILD_DONE
