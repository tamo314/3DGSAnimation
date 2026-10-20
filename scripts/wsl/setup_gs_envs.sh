#!/bin/bash
# GaussianShader / G-Style 用の venv を作り、各公式の diff-gaussian-rasterization / simple-knn をビルドする(同名パッケージの衝突を避けるためプロジェクトごとに分ける)
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
PY=$MAMBA_ROOT_PREFIX/envs/t7/bin/python
MM=~/.local/bin/micromamba
$MM env remove -y -n gshader >/dev/null 2>&1; $MM env remove -y -n gstyle >/dev/null 2>&1
mkdir -p ~/venvs
echo "torch==2.8.0
torchvision==0.23.0" > ~/venvs/constraints.txt
# G-Style の submodule(公式がHTTPSで公開しているInria側リポジトリ)を取得
cd ~/ext/g-style && mkdir -p submodules && cd submodules
[ -d diff-gaussian-rasterization ] || git clone --recursive https://github.com/graphdeco-inria/diff-gaussian-rasterization 2>&1 | tail -1
[ -d simple-knn ] || git clone https://gitlab.inria.fr/bkerbl/simple-knn.git 2>&1 | tail -1
for e in gshader gstyle; do
  rm -rf ~/venvs/$e; $PY -m venv ~/venvs/$e
  ~/venvs/$e/bin/pip install -q --upgrade pip wheel "setuptools<75" 2>&1 | tail -1
  ~/venvs/$e/bin/pip install -q torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128 2>&1 | tail -1
  ~/venvs/$e/bin/pip install -q -c ~/venvs/constraints.txt plyfile tqdm "numpy<2" pillow scipy lpips opencv-python-headless 2>&1 | tail -1
done
~/venvs/gshader/bin/pip install -q -c ~/venvs/constraints.txt ~/ext/MILo/submodules/nvdiffrast 2>&1 | tail -1
~/venvs/gstyle/bin/pip install -q -c ~/venvs/constraints.txt open_clip_torch 2>&1 | tail -1
build() { # venv repo
  for m in diff-gaussian-rasterization simple-knn; do
    echo "=== $1 build $2/submodules/$m"
    (cd ~/ext/$2 && ~/venvs/$1/bin/pip install --no-build-isolation submodules/$m 2>&1 | grep -E "error|Successfully")
  done
}
build gshader GaussianShader
build gstyle g-style
for e in gshader gstyle; do ~/venvs/$e/bin/python -c "import torch;print('$e', torch.__version__, torch.cuda.is_available())"; done
echo GS_ENVS_DONE
