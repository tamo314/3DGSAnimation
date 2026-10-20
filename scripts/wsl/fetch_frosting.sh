#!/bin/bash
# Frostingの出力をプロジェクト側へコピーする
o=~/ext/Frosting/output
d=/mnt/c/Work/3DGSAnimation-T7/experiments/T7/runs/frosting_char
mkdir -p $d
ls -laR $o | grep -v "^total" | grep -E "ply|obj|png|pt|mtl|:$" | cut -c1-200
cp $o/refined_frosting_ply/char_scene_black/*.ply $d/frosting_gaussians.ply
cp $o/coarse_shell/char_scene_black/*.ply $d/shell_base_mesh.ply
ls -la $d
