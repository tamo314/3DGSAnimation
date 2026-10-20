#!/bin/bash
# WSL2(Ubuntu)にユーザー領域だけで CUDA 12.8 ツールチェーン + cmake + ninja を入れる(sudo不要・システムを汚さない)
set -e
mkdir -p ~/.local/bin
if [ ! -x ~/.local/bin/micromamba ]; then
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C ~/.local bin/micromamba
fi
export MAMBA_ROOT_PREFIX=~/mamba
~/.local/bin/micromamba create -y -n t7 -c nvidia/label/cuda-12.8.1 -c conda-forge \
   python=3.10 cuda-toolkit=12.8 cmake ninja git-lfs 2>&1 | tail -5
~/.local/bin/micromamba run -n t7 nvcc --version
