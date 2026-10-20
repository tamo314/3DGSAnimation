#!/bin/bash
# Frostingのキャラ出力(ガウシアン層・土台メッシュ)を、Tripoの正解メッシュと比べる
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
cd /mnt/c/Work/3DGSAnimation-T7
GLB=/mnt/c/Work/3DGSAnimation/assets/generated/character/normalized/girl_healer.glb
D=experiments/T7/runs/frosting_char
run python - <<PY
import numpy as np, trimesh
m=trimesh.load("$D/shell_base_mesh.ply",process=False)
print("shell mesh bbox", m.bounds.round(3).tolist(), "verts", len(m.vertices), "faces", len(m.faces))
b=open("$D/frosting_gaussians.ply","rb").read(4000)
h=b[:b.index(b"end_header")+11]
names=[l.split()[-1] for l in h.decode().split("\n") if l.startswith("property")]
v=np.fromfile("$D/frosting_gaussians.ply",dtype=np.dtype([(q,"<f4") for q in names]),offset=len(h),count=1000000)
P=np.stack([v["x"],v["y"],v["z"]],1)
print("gauss bbox",P.min(0).round(3).tolist(),P.max(0).round(3).tolist())
print("opacity mean",float((1/(1+np.exp(-v["opacity"]))).mean()),"scale median",float(np.median(np.exp(v["scale_0"]))))
PY
run python scripts/gaussian/eval_mesh_chamfer.py --glb $GLB --mesh $D/shell_base_mesh.ply 2>&1 | tail -5
run python scripts/gaussian/eval_normals.py --glb $GLB --ply frosting=$D/frosting_gaussians.ply --out $D/normals_eval.json 2>&1 | tail -12
