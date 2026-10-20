#!/bin/bash
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
cd ~/ext/GaussianShader
~/venvs/gshader/bin/python render.py -m ~/work/out/gshader_char_scene_nerf --brdf_dim 0 --sh_degree -1 --brdf_mode envmap --brdf_env 512 -r 2 2>&1 | tail -c 600
find ~/work/out/gshader_char_scene_nerf -maxdepth 3 -type d | head -20
