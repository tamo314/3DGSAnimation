# WSL の t7 環境(micromamba)で CUDA 12.8 / sm_120 向けにビルド・実行するための環境変数。 source して使う
export MAMBA_ROOT_PREFIX=~/mamba
export CUDA_HOME=$MAMBA_ROOT_PREFIX/envs/t7
export PATH=$CUDA_HOME/bin:$PATH
export CPATH=$CUDA_HOME/targets/x86_64-linux/include:$CUDA_HOME/include:$CPATH
export LIBRARY_PATH=$CUDA_HOME/targets/x86_64-linux/lib:$CUDA_HOME/lib:$LIBRARY_PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib:$CUDA_HOME/targets/x86_64-linux/lib:$LD_LIBRARY_PATH
export TORCH_CUDA_ARCH_LIST="12.0"
export MAX_JOBS=8
run() { ~/.local/bin/micromamba run -n t7 "$@"; }
export NVCC_PREPEND_FLAGS="-include cfloat -include cstdint"   # 公式ソースを書き換えず、新しいCUDAで要る標準ヘッダを前置する
export CMAKE_POLICY_VERSION_MINIMUM=3.5
export LIBRARY_PATH=/usr/lib/wsl/lib:$LIBRARY_PATH   # libcuda(WSL)
