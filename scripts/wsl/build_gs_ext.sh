#!/bin/bash
# GaussianShader / G-Style の拡張を、conda側のgcc(glibcがCUDAと整合)を -ccbin にしてビルドする
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
build() {
  for m in diff-gaussian-rasterization simple-knn; do
    echo "=== $1 build $2/submodules/$m"
    (cd ~/ext/$2 && ~/venvs/$1/bin/pip install --no-build-isolation --force-reinstall --no-deps submodules/$m 2>&1 | grep -E " error|Successfully" | head -3 | cut -c1-200)
  done
}
build gshader GaussianShader
build gstyle g-style
echo GS_BUILD_DONE
