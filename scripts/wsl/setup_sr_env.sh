#!/bin/bash
# T8: 超解像用のvenv。torch 2.8.0+cu128 は既存の gstyle 環境のものを .pth で共有し(再ダウンロード不要)、spandrel だけ新しく入れる。gstyle 環境自体は変更しない
set -e
export PATH=$HOME/.local/bin:$PATH
rm -rf ~/venvs/sr
uv venv ~/venvs/sr --python 3.10
echo "$HOME/venvs/gstyle/lib/python3.10/site-packages" > ~/venvs/sr/lib/python3.10/site-packages/gstyle_share.pth
uv pip install --python ~/venvs/sr/bin/python spandrel
~/venvs/sr/bin/python -c "import torch, spandrel, cv2; print(torch.__version__, torch.cuda.is_available(), spandrel.__version__, cv2.__version__)"
