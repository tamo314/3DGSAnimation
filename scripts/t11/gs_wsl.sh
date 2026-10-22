#!/bin/bash
# T11: t9環境(gsplat)で任意のPythonスクリプトを実行する。 例: bash gs_wsl.sh gs_train.py --data ... --out ...
source /mnt/c/Work/3DGSAnimation-T11/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
export PATH=$HOME/venvs/t9/bin:$PATH
s=$1; shift
python /mnt/c/Work/3DGSAnimation-T11/scripts/t11/$s "$@"
