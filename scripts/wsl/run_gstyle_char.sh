#!/bin/bash
# キャラのCOLMAPデータで ①素の3DGSを学習(G-Styleリポジトリの train_original.py) → ②G-Style(公式・無改変)でスタイル転写。引数: スタイル画像名(複数可)
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
name=char_scene_black
mkdir -p ~/work/data ~/work/out ~/work/style
rm -rf ~/work/data/$name; cp -r /mnt/c/Work/3DGSAnimation-T7/experiments/T7/data/$name ~/work/data/$name
cp /mnt/c/Work/3DGSAnimation-T7/experiments/T7/data/style/*.png ~/work/style/
cd ~/ext/g-style
out=~/work/out/vanilla_char
if [ ! -f $out/point_cloud/iteration_30000/point_cloud.ply ]; then
  START=$(date +%s)
  ~/venvs/gstyle/bin/python train_original.py -s ~/work/data/$name -m $out --eval > ~/work/out/vanilla_char.log 2>&1
  echo "VANILLA_SECONDS $(( $(date +%s) - START ))"
fi
for s in "$@"; do
  START=$(date +%s)
  rm -rf ~/work/out/gstyle_$s; cp -r $out ~/work/out/gstyle_$s
  ~/venvs/gstyle/bin/python train.py -s ~/work/data/$name -m ~/work/out/gstyle_$s --resolution 1 --starting_iter 30000 --path_style ~/work/style/$s.png > ~/work/out/gstyle_$s.log 2>&1
  echo "GSTYLE_$s SECONDS $(( $(date +%s) - START ))"
  ls ~/work/out/gstyle_$s/point_cloud
done
echo GSTYLE_DONE
