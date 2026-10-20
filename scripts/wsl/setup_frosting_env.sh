#!/bin/bash
# Frosting 用の venv(torch 2.8 + pytorch3d をソースからビルド)。公式の想定は torch 2.0.1 + CUDA 11.8 + pytorch3d 0.7.4
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
PY=$MAMBA_ROOT_PREFIX/envs/t7/bin/python
rm -rf ~/venvs/frosting; $PY -m venv ~/venvs/frosting
P=~/venvs/frosting/bin/pip
$P install -q --upgrade pip wheel "setuptools<75" 2>&1 | tail -1
$P install -q torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128 2>&1 | tail -1
$P install -q -c ~/venvs/constraints.txt plyfile tqdm "numpy<2" pillow scipy open3d==0.19.0 rich PyMCubes matplotlib fvcore iopath plotly opencv-python-headless 2>&1 | tail -1
echo "=== pytorch3d build"
FORCE_CUDA=1 $P install --no-build-isolation "git+https://github.com/facebookresearch/pytorch3d.git@stable" 2>&1 | grep -E " error|Successfully|FAILED" | head -5 | cut -c1-200
cd ~/ext/Frosting/gaussian_splatting/submodules
for m in diff-gaussian-rasterization simple-knn; do
  echo "=== frosting build $m"; (cd $m && ls | head -3; $P install --no-build-isolation . 2>&1 | grep -E " error|Successfully" | head -3 | cut -c1-200)
done
$P install -q -c ~/venvs/constraints.txt ~/ext/MILo/submodules/nvdiffrast 2>&1 | tail -1
~/venvs/frosting/bin/python -c "import torch, pytorch3d; print('frosting env', torch.__version__, pytorch3d.__version__)"
echo FROSTING_ENV_DONE
