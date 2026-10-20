#!/bin/bash
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export PATH=$HOME/venvs/frosting/bin:$PATH
python - <<PY
import torch, numpy as np
ck=torch.load("$HOME/ext/Frosting/output/coarse/char_scene_black/sugarcoarse_3Dgs7000_densityestim02_sdfnorm02/15000.pt",map_location="cpu",weights_only=False)
sd=ck["state_dict"]
print(list(sd.keys())[:12])
P=sd["_points"].numpy()
print("coarse points",P.shape,P.min(0).round(2),P.max(0).round(2))
r=np.linalg.norm(P[:,:2],axis=1)
print("within r<0.5:",(r<0.5).sum(),"of",len(P))
d=sd.get("all_densities")
if d is not None:
    a=1/(1+np.exp(-d.numpy().ravel())); print("alpha mean",a.mean(),">0.5:",(a>0.5).sum())
PY
