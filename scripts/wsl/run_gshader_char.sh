#!/bin/bash
# キャラのNeRF-Synthetic形式データで GaussianShader(公式・無改変)を学習する。
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
name=${1:-char_scene_nerf}; shift
mkdir -p ~/work/data ~/work/out
rm -rf ~/work/data/$name; cp -r /mnt/c/Work/3DGSAnimation-T7/experiments/T7/data/$name ~/work/data/$name
cd ~/ext/GaussianShader
out=~/work/out/gshader_$name
START=$(date +%s)
~/venvs/gshader/bin/python train.py -s ~/work/data/$name --eval -m $out -w --brdf_dim 0 --sh_degree -1 --lambda_predicted_normal 2e-1 --brdf_env 512 "$@" > ~/work/out/gshader_$name.log 2>&1
echo "TRAIN_SECONDS $(( $(date +%s) - START ))"
tail -c 1500 ~/work/out/gshader_$name.log
echo GSHADER_DONE
