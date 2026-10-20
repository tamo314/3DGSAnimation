#!/bin/bash
# 参照研究の公式リポジトリを WSL の ~/ext に取得する(プロジェクト本体には取り込まない)。サブモジュールのSSH URLはHTTPSに読み替える
mkdir -p ~/ext && cd ~/ext
git config --global url."https://github.com/".insteadOf git@github.com:
for r in Anttwo/MILo Anttwo/Frosting AronKovacs/g-style ethanweber/toon3d Asparagus15/GaussianShader; do
  n=$(basename $r)
  [ -d $n/.git ] || { rm -rf $n; git clone --recursive https://github.com/$r $n 2>&1 | tail -1; }
done
