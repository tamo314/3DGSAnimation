#!/bin/bash
# MILo背景の出力(PLY・メッシュ)をプロジェクト側へコピーする
o=~/work/out/milo_bg_scene_rgb
d=/mnt/c/Work/3DGSAnimation-T7/experiments/T7/runs/milo_bg
mkdir -p $d
cat $o/time.txt
cp $o/point_cloud/iteration_18000/point_cloud.ply $d/gaussians.ply
cp $o/mesh_learnable_sdf.ply $d/mesh.ply
ls -la $o $d
