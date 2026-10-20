#!/bin/bash
# キャラのCOLMAPデータで Gaussian Frosting(公式・無改変)の全パイプラインを流す(単体物体向けの推奨値: cleaning_quantile 0 / connected_components_vis_th 0.5)
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
export PATH=$HOME/venvs/frosting/bin:$PATH   # train_full_pipeline.py は子プロセスを PATH 上の python で起動する
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1   # torch>=2.6 の既定(weights_only)で公式チェックポイントが読めない。コードは書き換えず環境変数で戻す
name=char_scene_black
mkdir -p ~/work/data ~/work/out
rm -rf ~/work/data/$name; cp -r /mnt/c/Work/3DGSAnimation-T7/experiments/T7/data/$name ~/work/data/$name
cd ~/ext/Frosting
START=$(date +%s)
~/venvs/frosting/bin/python train_full_pipeline.py -s ~/work/data/$name -r dn_consistency --gaussians_in_frosting 1_000_000 --low_poly True --refinement_time short \
   --cleaning_quantile 0.0 --connected_components_vis_th 0.5 --use_occlusion_culling False --export_obj True "$@" > ~/work/out/frosting_char.log 2>&1
echo "FROSTING_SECONDS $(( $(date +%s) - START ))"
tail -c 1200 ~/work/out/frosting_char.log
echo FROSTING_DONE
