#!/bin/bash
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
export CC=$CUDA_HOME/bin/x86_64-conda-linux-gnu-gcc CXX=$CUDA_HOME/bin/x86_64-conda-linux-gnu-g++
export NVCC_PREPEND_FLAGS="-ccbin $CXX -include cfloat -include cstdint"
export PATH=$HOME/venvs/t9/bin:$PATH
python - <<PY
import torch, time
from gsplat import rasterization
dev="cuda"
N=1000
means=torch.randn(N,3,device=dev)*0.3; quats=torch.nn.functional.normalize(torch.randn(N,4,device=dev),dim=-1)
scales=torch.full((N,3),0.05,device=dev); op=torch.rand(N,device=dev); col=torch.rand(N,3,device=dev)
K=torch.tensor([[500.,0,128],[0,500.,128],[0,0,1]],device=dev)[None]
vm=torch.eye(4,device=dev)[None]; vm[0,2,3]=2.0
t=time.time()
img,alpha,info=rasterization(means,quats,scales,op,col,vm,K,256,256)
torch.cuda.synchronize(); print("ok",img.shape,alpha.shape,time.time()-t)
img.sum().backward() if img.requires_grad else None
PY
