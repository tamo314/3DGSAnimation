#!/bin/bash
# T9: t9 venv で任意のコマンドを実行する。 例: bash t9_run.sh python scripts/t9/prep_mesh.py ...
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
export PATH=$HOME/venvs/t9/bin:$PATH
cd /mnt/c/Work/3DGSAnimation-T9
"$@"
