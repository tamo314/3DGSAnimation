#!/bin/bash
# GPU学習は同時に1本まで。GaussianShader の終了を待って G-Style(素の3DGS学習→2スタイル) を流す
while pgrep -f "GaussianShader/train.py|gshader/bin/python train.py" >/dev/null; do sleep 20; done
bash /mnt/c/Work/3DGSAnimation-T7/scripts/wsl/run_gstyle_char.sh style_forest1 style_moss
