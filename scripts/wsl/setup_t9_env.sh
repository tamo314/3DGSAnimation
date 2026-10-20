#!/bin/bash
# T9(メッシュ連動ガウシアン層の自前実装)用の venv。描画は gsplat(Apache-2.0)を使い、学習ループは自前で書く
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
PY=$MAMBA_ROOT_PREFIX/envs/t7/bin/python
rm -rf ~/venvs/t9; $PY -m venv ~/venvs/t9
P=~/venvs/t9/bin/pip
$P install -q --upgrade pip wheel "setuptools<75" ninja 2>&1 | tail -1
$P install -q torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128 2>&1 | tail -1
$P install -q -c ~/venvs/constraints.txt "numpy<2" scipy pillow plyfile trimesh opencv-python-headless tqdm lpips rtree 2>&1 | tail -1
$P install -q -c ~/venvs/constraints.txt gsplat 2>&1 | tail -2
~/venvs/t9/bin/python -c "import torch, gsplat; print('t9', torch.__version__, gsplat.__version__)"
echo T9_ENV_DONE
