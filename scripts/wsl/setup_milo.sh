#!/bin/bash
# WSL2(Ubuntu) に MILo の公式コードを動かす環境を作る(torch 2.8 + cu128、RTX 5060 Ti = sm_120 向け)。
# 公式の想定は torch 2.3.1 + CUDA 11.8。Blackwell は cu128 以降が必要なので版を上げてビルドを試す。
# 公式コードは ~/ext/MILo にあり、プロジェクトには取り込まない。ビルドが通らない箇所は docs/07-milo.md に記録する。
set -x
export MAMBA_ROOT_PREFIX=~/mamba
MM=~/.local/bin/micromamba
run() { $MM run -n t7 "$@"; }
cd ~/ext/MILo
git submodule update --init submodules/nvdiffrast 2>&1 | tail -2

$MM install -y -n t7 -c conda-forge gmp cgal mpfr boost-cpp libboost-devel eigen 2>&1 | tail -3
run pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128 2>&1 | tail -2
run pip install -r requirements.txt 2>&1 | tail -3
run python -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability())"
