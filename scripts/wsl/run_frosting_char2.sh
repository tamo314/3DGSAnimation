#!/bin/bash
# Frosting 2回目: 粗い段階は1回目の結果を再利用し、前景の範囲(bbox)をキャラ周りに限定して、土台メッシュ抽出と精錬をやり直す
# 1回目は前景範囲が既定(カメラの広がり=数m)で、土台メッシュが背景の外れ値を含んで壊れた(頂点1951、範囲10x14x5m)
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
export PATH=$HOME/venvs/frosting/bin:$PATH
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
name=char_scene_black
cd ~/ext/Frosting
START=$(date +%s)
CK=$HOME/ext/Frosting/output/coarse/$name/sugarcoarse_3Dgs7000_densityestim02_sdfnorm02/15000.pt
python /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/frosting_shim.py $CK \
  -s ~/work/data/$name -c $HOME/ext/Frosting/output/vanilla_gs/$name/ -r dn_consistency \
  --gaussians_in_frosting 1000000 --low_poly True --refinement_time short \
  --cleaning_quantile 0.0 --connected_components_vis_th ${VIS_TH:-0.5} --use_occlusion_culling False --export_obj False \
  --bboxmin=-0.6,-0.6,-0.1 --bboxmax=0.6,0.6,1.3 --center_bbox False "$@"
echo "FROSTING2_SECONDS $(( $(date +%s) - START ))"
echo FROSTING2_DONE
