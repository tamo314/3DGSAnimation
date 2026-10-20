"""Frosting(公式・無改変)の train.py を、粗い段階(coarse SuGaR)を学習済みチェックポイントで置き換えて実行する薄いラッパー。
粗い段階は約1時間かかるので、土台メッシュ抽出・精錬のパラメータだけを変えて何度も試すために使う。公式コードは書き換えない。
  python frosting_shim.py <coarseチェックポイント.pt> <train.py に渡す引数...>
"""
import os
import runpy
import sys

sys.path.insert(0, os.getcwd())  # 公式リポジトリ(カレント)を import できるようにする
import frosting_trainers.coarse_density_and_dn_consistency as m

ckpt = sys.argv[1]
m.coarse_training_with_density_regularization_and_dn_consistency = lambda args: ckpt
sys.argv = ["train.py"] + sys.argv[2:]
runpy.run_path("train.py", run_name="__main__")
