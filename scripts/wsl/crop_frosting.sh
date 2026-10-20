#!/bin/bash
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
cd /mnt/c/Work/3DGSAnimation-T7
D=experiments/T7/runs/frosting_char
run python scripts/gaussian/crop_ply.py $D/frosting_gaussians.ply $D/frosting_char_crop.ply --near experiments/T7/runs/vanilla_char/gaussians.ply --dist 0.02
run python - <<PY
import numpy as np, trimesh
m=trimesh.load("$D/shell_base_mesh.ply",process=False)
v=np.asarray(m.vertices); f=np.asarray(m.faces)
keep=(abs(v[:,0])<0.6)&(abs(v[:,1])<0.6)&(v[:,2]>-0.1)&(v[:,2]<1.3)
fk=keep[f].all(1)
sub=trimesh.Trimesh(v,f[fk],process=False); sub.remove_unreferenced_vertices()
sub.export("$D/shell_base_mesh_crop.ply"); print("crop mesh verts",len(sub.vertices),"faces",len(sub.faces))
PY
run python scripts/gaussian/eval_mesh_chamfer.py --glb /mnt/c/Work/3DGSAnimation/assets/generated/character/normalized/girl_healer.glb --mesh $D/shell_base_mesh_crop.ply 2>&1 | tail -5
run python scripts/gaussian/ply_stats.py $D/frosting_char_crop.ply
