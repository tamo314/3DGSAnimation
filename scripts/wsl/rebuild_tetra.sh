#!/bin/bash
# tetra_triangulation を torch 2.8(新ABI)向けに再ビルドする。公式のFindTorch.cmakeは ABI=0 固定なので、後に効く _RELEASE フラグで上書きする(ソースは無改変)
source /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/env_t7.sh
cd ~/ext/MILo/submodules/tetra_triangulation
run make clean >/dev/null 2>&1
rm -f CMakeCache.txt
run cmake . -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE="-O3 -U_GLIBCXX_USE_CXX11_ABI -D_GLIBCXX_USE_CXX11_ABI=1" 2>&1 | tail -2
run make -j8 2>&1 | grep -E "error|Built target|\*\*\*" | head
run pip install --no-build-isolation --force-reinstall --no-deps -e . 2>&1 | grep -E "error|Successfully"
run python -c "from tetranerf.utils.extension import cpp; print('tetranerf OK')"
